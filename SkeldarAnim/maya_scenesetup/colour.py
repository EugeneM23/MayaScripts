"""A colour for every character and weapon we put into the scene.

Since 2026-09-01 Add Character can be pressed as many times as the animator
likes, and every press brought the same grey figure: the outliner can tell
two Mannys apart and the eye cannot. So each press now creates one material (SHADER)
and assigns it to every mesh it brought, in the colour the panel's swatch is
showing («нужно добавить опцию выбора цвета для персонажа и оружия которого
мы добавляем в сцену», 2026-09-03).

The asset's own materials are not deleted -- they stay in the scene,
unassigned -- but nothing here offers to put them back. That was the
animator's call, made with the cost stated: «нет, красим всегда».

Two things carry the design.

**Identity by attribute.** The lambert carries `skeldarColour` holding the
owner's key, and every lookup asks for that attribute. Maya uniquifies
`skeldarColour_red` into `...red1` the second time, the animator may rename
anything, and every tool in this repo that identified a node by name has
paid for it. The name still carries the colour, because a readable
Hypershade costs nothing.

**The free colour is read from the scene.** Not from a counter in an
optionVar: a counter is right until the animator opens another file, deletes
a character, or presses Add in a scene somebody else set up, and then it
hands out a colour already on screen. It is what the swatch is filled with
when the window opens and after every press, so the animator can choose a
colour and can also just not bother.
"""

import collections

import maya.cmds as cmds

Colour = collections.namedtuple("Colour", "name rgb")

# The attribute that says a material is ours. Same schema as `mayaWeapon` on
# the weapon geometry and `rigPickerRoot` on the rig manifests.
MARKER = "skeldarColour"

PREFIX = "skeldarColour"

# ONE shader for every model and rig we put into the scene (2026-09-25: «на все
# наши модели и риги нужно настроить единый шейдер, такой чтобы он смотрелся
# хорошо в мае и в каскадере. Сейчас при экспорте в каскадер модель выглядит
# темной»). A phong wearing LOOK, the numbers Cascadeur itself writes into the
# FBX it exports (measured on creep_T-pose_draft (1).fbx, Cascadeur 2024.1: phong,
# DiffuseFactor 1, Specular 0.2, Shininess 20, Reflectivity 0) -- the look
# Cascadeur reads back as its own. Still not a lambert (2026-09-03, «у него лучше
# шейдинг и он блестит»): a lambert is flat, the specular keeps the form. The
# blinn it replaces left its attributes at Maya's defaults and exported
# DiffuseFactor 0.8, SpecularColor 0.5 and ReflectionFactor 0.5 -- the colour at
# 80 % with a reflection Cascadeur has no environment for. A phong's cosinePower IS
# the FBX ShininessExponent, so the numbers land in the file unconverted.
SHADER = "phong"
LOOK = {"diffuse": 1.0, "specularColor": (0.2, 0.2, 0.2), "cosinePower": 20.0,
        "reflectivity": 0.0}

# Mid-bright, one per hue stop. Two requirements the values have to meet, both
# pinned by tests: none is near black -- `character.needs_grey` reads a
# near-black untextured material as an import that lost its textures and
# would grey it out from under us on the FBX path -- and none is Maya's
# default grey, or a coloured character would read as an uncoloured one.
PALETTE = [
    Colour("red", (0.80, 0.25, 0.22)),
    Colour("orange", (0.90, 0.50, 0.18)),
    Colour("amber", (0.88, 0.75, 0.20)),
    Colour("green", (0.35, 0.68, 0.32)),
    Colour("teal", (0.20, 0.70, 0.68)),
    Colour("blue", (0.25, 0.52, 0.85)),
    Colour("violet", (0.60, 0.40, 0.82)),
    Colour("pink", (0.88, 0.48, 0.68)),
]

# A colour written as a float and read back through Maya is not bit-identical.
# An exact compare reports every colour in the scene as still free.
_TOLERANCE = 0.01

CUSTOM = "custom"


# ------------------------------------------------------------------ policy

def same_colour(first, second, tolerance=_TOLERANCE):
    """Whether two RGB triples are the same colour. Pure.

    Anything that is not a triple is never the same as anything -- a caller
    handing over two channels must not silently match a three-channel plug.
    """
    if not first or not second:
        return False
    if len(first) != 3 or len(second) != 3:
        return False
    return all(abs(a - b) <= tolerance for a, b in zip(first, second))


def next_colour(used):
    """The first palette entry not among `used`. Pure.

    A gap counts: a deleted character frees its colour and the next Add takes
    it back rather than walking off the end. With all eight taken it wraps by
    count -- deterministic, so two presses in a full scene still differ from
    each other, and never random.
    """
    taken = list(used or [])
    for entry in PALETTE:
        if not any(same_colour(entry.rgb, rgb) for rgb in taken):
            return entry
    return PALETTE[len(taken) % len(PALETTE)]


def colour_name(rgb):
    """The palette's name for this colour, or "custom". Pure.

    For the status line and the material's name. Nothing is ever FOUND by
    either.
    """
    for entry in PALETTE:
        if same_colour(entry.rgb, rgb):
            return entry.name
    return CUSTOM


def material_name(rgb):
    return "{0}_{1}".format(PREFIX, colour_name(rgb))


def mesh_set(skinned, descendants):
    """The union of the two ways a character's meshes are found. Pure.

    Manny's six meshes sit at WORLD level rather than under the skeleton
    (`character.flatten_wrappers` records why, and the UE4 mannequin is
    flattened to the same shape on purpose), so the DAG walk finds nothing
    at all and the skinCluster is what works. The walk stays in the union
    for unskinned geometry somebody parented into the character by hand.
    """
    found = []
    for shape in list(skinned or []) + list(descendants or []):
        if shape and shape not in found:
            found.append(shape)
    return found


# ------------------------------------------------------------------- scene

def is_ours(material):
    """Whether `material` carries our marker."""
    try:
        return bool(cmds.attributeQuery(MARKER, node=material, exists=True))
    except Exception:
        return False


def our_materials():
    """Every material in the scene that this module made."""
    return [material for material in (cmds.ls(materials=True) or [])
            if is_ours(material)]


def colour_plug(material):
    """The RGB `material` holds, or None."""
    plug = material + ".color"
    if not cmds.objExists(plug):
        return None
    try:
        return tuple(cmds.getAttr(plug)[0])
    except Exception:
        return None


def is_assigned(material):
    """Whether anything in the scene actually wears `material`.

    Replacing a weapon deletes its geometry and leaves the lambert behind,
    as any Maya delete does -- chasing shading nodes is how a tool
    eventually deletes something the animator wanted. So the orphan is left
    alone and simply stops COUNTING: the re-added sword takes its old colour
    back instead of walking down the palette on every press.
    """
    engine = engine_of(material)
    if not engine:
        return False
    return bool(cmds.sets(engine, query=True))


def used_colours():
    """The colours worn in this scene right now, character and weapon alike.

    One scan for both, so a sword added into a red character's hand comes out
    orange. Telling those two apart is half the reason the feature exists.
    """
    found = []
    for material in our_materials():
        rgb = colour_plug(material)
        if rgb and is_assigned(material):
            found.append(rgb)
    return found


def free_colour():
    """The colour the next Add brings."""
    return next_colour(used_colours())


def mesh_shapes(nodes):
    """Every renderable mesh shape at or below `nodes`, in order.

    Intermediate shapes are skipped: a skinned mesh carries an `...Orig`
    shape that no shader has any business reaching.
    """
    found = []
    for node in (cmds.ls(nodes, long=True) or []):
        candidates = []
        if cmds.objectType(node) == "mesh":
            candidates.append(node)
        candidates.extend(cmds.listRelatives(node, allDescendents=True,
                                             type="mesh", fullPath=True) or [])
        for shape in candidates:
            if shape in found:
                continue
            try:
                if cmds.getAttr(shape + ".intermediateObject"):
                    continue
            except Exception:
                pass
            found.append(shape)
    return found


def unambiguous(name):
    """The single node `name` points at, or None if it points at several.

    `cmds.skinCluster(q=True, geometry=True)` answers with SHORT names --
    measured 2026-09-03: `['Hands_1PShape']`, not a path -- which is trap 28
    all over again. Maya hands back the shortest UNIQUE name, so one path is
    what normally comes out; but two Mannys in one scene share every leaf
    name below the top node, and if a name ever does resolve to several
    nodes then picking one would be a guess. The next thing that happens to
    these shapes is a `forceElement`, so a guess here repaints somebody
    else's character. Skipping is the safe direction of failure.
    """
    paths = cmds.ls(name, long=True) or []
    return paths[0] if len(paths) == 1 else None


def skinned_shapes(root):
    """The meshes deformed by any joint under `root`.

    Identity by CONNECTION -- not by name, not by position in the DAG. It is
    the only route that reaches Manny's meshes at all: they sit at world
    level, so nothing about the hierarchy relates them to the skeleton.
    """
    joints = [root] + (cmds.listRelatives(root, allDescendents=True,
                                          type="joint", fullPath=True) or [])
    clusters = []
    for joint in joints:
        for node in (cmds.listConnections(joint, type="skinCluster") or []):
            if node not in clusters:
                clusters.append(node)

    shapes = []
    for cluster in clusters:
        try:
            geometry = cmds.skinCluster(cluster, query=True,
                                        geometry=True) or []
        except Exception:
            continue
        resolved = [path for path in (unambiguous(name) for name in geometry)
                    if path]
        for shape in mesh_shapes(resolved):
            if shape not in shapes:
                shapes.append(shape)
    return shapes


def character_meshes(root):
    """Every mesh belonging to the character at `root`."""
    if not root:
        return []
    return mesh_set(skinned_shapes(root), mesh_shapes([root]))


def shading_engines(shapes):
    """The shading engines `shapes` are assigned to, in order."""
    engines = []
    for shape in shapes or []:
        for engine in (cmds.listSets(object=shape, type=1) or []):
            if engine not in engines:
                engines.append(engine)
    return engines


def surface_shader(engine):
    """The shader plugged into `engine`, or None."""
    shaders = cmds.listConnections(engine + ".surfaceShader", source=True,
                                   destination=False) or []
    return shaders[0] if shaders else None


def material_on(shapes):
    """OUR material already assigned to `shapes`, or None.

    Somebody else's is never returned, and that is the point: recolouring
    Manny's own material would change every other mesh using it, anywhere in
    the scene. Ours goes over the assignment instead.
    """
    for engine in shading_engines(shapes):
        shader = surface_shader(engine)
        if shader and is_ours(shader):
            return shader
    return None


def engine_of(material):
    """The shading engine `material` feeds, or None."""
    engines = cmds.listConnections(material + ".outColor",
                                   type="shadingEngine") or []
    return engines[0] if engines else None


def colour_of(shapes):
    """What OUR material gives `shapes`, or None when there is none.

    This is what a swatch shows. A foreign material reads as nothing rather
    than as its own colour: the swatch is about the colour we assigned, and
    showing somebody else's would make changing it look like a no-op.
    """
    material = material_on(shapes)
    return colour_plug(material) if material else None


def dress(material):
    """LOOK on `material`: the one shader's settings, the colour aside."""
    for attr, value in LOOK.items():
        if isinstance(value, tuple):
            cmds.setAttr(material + "." + attr, *value, type="double3")
        else:
            cmds.setAttr(material + "." + attr, value)


def make_material(rgb, key):
    """A fresh SHADER in `rgb` wearing LOOK, marked as ours, with its shading engine."""
    material = cmds.shadingNode(SHADER, asShader=True,
                                name=material_name(rgb))
    dress(material)
    cmds.setAttr(material + ".color", rgb[0], rgb[1], rgb[2], type="double3")
    cmds.addAttr(material, longName=MARKER, dataType="string")
    cmds.setAttr(material + "." + MARKER, key or "", type="string")

    engine = cmds.sets(renderable=True, noSurfaceShader=True, empty=True,
                       name=material + "SG")
    cmds.connectAttr(material + ".outColor", engine + ".surfaceShader",
                     force=True)
    return material, engine


def paint(shapes, rgb, key):
    """Give `shapes` our material in `rgb`. Returns the material, or None.

    Reuses the one already on them when it is ours, so a recolour is one
    `setAttr` -- replacing the material would drop whatever the animator had
    tuned on it -- and creates and assigns one otherwise. The re-assignment
    on the reuse path is what makes a character converge on a single
    material after being painted in two halves.

    A file coloured before 2026-09-03 carries LAMBERTS, and this reuses them
    rather than upgrading them to blinns: `is_ours` asks for the marker
    attribute and knows nothing about the node type. Recolouring an old
    character therefore keeps it flat, and only a fresh Add brings the
    shine. Swapping the material under an existing assignment is a bigger
    promise than a colour change should make.
    """
    shapes = [shape for shape in (shapes or []) if shape]
    if not shapes:
        return None

    material = material_on(shapes)
    if material:
        cmds.setAttr(material + ".color", rgb[0], rgb[1], rgb[2],
                     type="double3")
        engine = engine_of(material)
        if engine:
            cmds.sets(shapes, edit=True, forceElement=engine)
        return material

    material, engine = make_material(rgb, key)
    cmds.sets(shapes, edit=True, forceElement=engine)
    return material


def paint_fresh(shapes, rgb, key):
    """A NEW material in `rgb` on `shapes`, whatever they wear now.

    For an Add (2026-09-07): the shipped rig file carries the animator's own
    `skeldarColour_red` blinn on its meshes, and `paint` -- which reuses a
    marked material rather than swapping it -- would bring every rig in red
    and ignore the swatch. The asset's material is left in the scene
    unassigned, where `is_assigned` stops counting it; nothing is deleted.
    """
    shapes = [shape for shape in (shapes or []) if shape]
    if not shapes:
        return None
    material, engine = make_material(rgb, key)
    cmds.sets(shapes, edit=True, forceElement=engine)
    return material


def paint_nodes(nodes, rgb, key):
    """`paint_fresh` over whatever `nodes` hold: transforms, shapes or a mix.

    Only Add Character calls this, and an import's nodes are fresh by
    definition -- whatever marked material rides in with the asset is the
    asset's, not this scene's choice.
    """
    return paint_fresh(mesh_shapes(nodes), rgb, key)
