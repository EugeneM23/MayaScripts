"""Live proof for the per-character / per-weapon colour (2026-09-03).

Run through the command-port bridge in the animator's OPEN scene. Four
phases, and the split is the point:

  1. A SANDBOX -- one throwaway joint, one skinned sphere, one bare sphere --
     proves the mechanism on its own: intermediate shapes skipped, the
     skinCluster route reaching a mesh that is NOT under the joint (Manny's
     shape), reuse-versus-create, and an orphaned material giving its colour
     back. It needs no import, no OverRig and no rig on anything.
  2. Two real Add Character presses prove the integration: different
     colours, different materials, every mesh painted, one recoloured while
     the other does not move.
  3. The weapon, on the character phase 2 imported, proves the shared
     palette -- a sword in a red character's hand comes out something else.
  4. The PANEL, which no unit test can reach: a `cmds` window needs a live
     Maya. Driven against the throwaway character, never the animator's --
     repainting theirs would mean restoring a shading assignment
     afterwards, and this design deliberately has no machinery for that.

Everything this script creates is registered BY UUID as it is created and
deleted from that registry (trap 47): a `finally` that deletes a group
cannot clean up a failure that happened before the group existed. The frame,
the selection and autoKey are put back.

Bridge hygiene (CLAUDE.md): no cmds.file(new), no cmds.undo, no literal
writes into animated channels. This script only creates and deletes its own
nodes.
"""

import sys

REPO = "C:/!!!Work/MayaScripts/SkeldarAnim"

# Note 9: the session imports the INSTALLED SkeldarAnim copy. Prove the
# repo's code, not yesterday's build.
if REPO not in sys.path:
    sys.path.insert(0, REPO)
for name in list(sys.modules):
    if name.split(".")[0] in ("maya_overrig", "maya_uebridge",
                              "maya_scenesetup"):
        del sys.modules[name]

import maya.cmds as cmds  # noqa: E402

from maya_overrig import builder  # noqa: E402
from maya_scenesetup import (attach, catalog, character,  # noqa: E402
                             colour, skeleton)

FAILURES = []
CREATED = []          # uuids, registered as they are created (trap 47)


def gate(label, ok, detail=""):
    print("{0} {1}{2}".format("PASS" if ok else "FAIL", label,
                              " - " + str(detail) if detail else ""))
    if not ok:
        FAILURES.append(label)


def scene_uuids():
    return set(cmds.ls(cmds.ls(), uuid=True))  # trap 8: the bulk uuid form


def register_new():
    """Remember everything the scene has grown since we started, by UUID.

    A delta rather than a list of what each call returned: `skinCluster`
    conjures up tweak/groupId/groupParts nodes nobody named, an `.ma` import
    brings its own furniture, and `paint` makes a shading engine. Anything
    missed here is debris left in the animator's scene.
    """
    for uuid in scene_uuids() - BEFORE:
        if uuid not in CREATED:
            CREATED.append(uuid)


def distance(first, second):
    if not first or not second:
        return -1.0
    return max(abs(a - b) for a, b in zip(first, second))


FRAME = cmds.currentTime(query=True)
SELECTION = cmds.ls(selection=True, long=True) or []
AUTOKEY = cmds.autoKeyframe(query=True, state=True)
WINDOW_WAS_OPEN = cmds.window("mayaSceneSetupWindow", exists=True)
BEFORE = scene_uuids()

try:
    cmds.autoKeyframe(state=False)

    # ================================================== phase 1: the sandbox

    joint = cmds.ls(cmds.createNode("joint", name="rpColourJoint"),
                    long=True)[0]

    skinned = cmds.polySphere(name="rpColourSkinned",
                              constructionHistory=False)
    skinned = cmds.ls(skinned[0], long=True)[0]
    bare = cmds.polySphere(name="rpColourBare", constructionHistory=False)
    bare = cmds.ls(bare[0], long=True)[0]

    # Deliberately NOT parented under the joint: that is Manny's shape --
    # the meshes sit at world level and only the skinCluster relates them to
    # the skeleton. A DAG-only implementation scores zero on gate 2.
    cmds.skinCluster(joint, skinned, toSelectedBones=True)
    register_new()

    shapes = colour.mesh_shapes([skinned])
    orig = [s for s in (cmds.listRelatives(skinned, shapes=True,
                                           fullPath=True) or [])
            if cmds.getAttr(s + ".intermediateObject")]
    gate("1 the Orig shape is skipped",
         len(shapes) == 1 and bool(orig) and shapes[0] not in orig,
         "{0} renderable, {1} intermediate".format(len(shapes), len(orig)))

    found = colour.skinned_shapes(joint)
    gate("2 the skinCluster reaches a mesh outside the skeleton",
         found == shapes,
         "{0} through the skin, {1} under the joint".format(
             len(found), len(colour.mesh_shapes([joint]))))

    gate("3 character_meshes is that same mesh",
         colour.character_meshes(joint) == shapes,
         colour.character_meshes(joint))

    RED = colour.PALETTE[0].rgb
    BLUE = colour.PALETTE[5].rgb

    before_materials = set(colour.our_materials())
    material = colour.paint(shapes, RED, "sandbox")
    register_new()
    gate("4 a material is created and marked",
         bool(material) and colour.is_ours(material), material)
    gate("5 the colour reads back exactly",
         distance(colour.colour_of(shapes), RED) < 1e-6,
         "{0:.9f}".format(distance(colour.colour_of(shapes), RED)))

    again = colour.paint(shapes, BLUE, "sandbox")
    gate("6 a recolour reuses the material, never a second one",
         again == material
         and len(set(colour.our_materials()) - before_materials) == 1,
         "{0} vs {1}".format(again, material))
    gate("7 the recolour landed",
         distance(colour.colour_of(shapes), BLUE) < 1e-6,
         "{0:.9f}".format(distance(colour.colour_of(shapes), BLUE)))

    bare_shapes = colour.mesh_shapes([bare])
    gate("8 a foreign material is never claimed",
         colour.material_on(bare_shapes) is None
         and colour.colour_of(bare_shapes) is None,
         colour.material_on(bare_shapes))

    used = colour.used_colours()
    gate("9 the painted colour counts as used",
         any(colour.same_colour(rgb, BLUE) for rgb in used),
         "{0} colours in use".format(len(used)))
    gate("10 the free colour is not one already worn",
         not any(colour.same_colour(colour.free_colour().rgb, rgb)
                 for rgb in used),
         colour.free_colour().name)

    # The orphan rule: deleting the geometry leaves the lambert behind (as
    # any Maya delete does), and it must stop COUNTING -- or a re-added
    # sword would walk down the palette on every press.
    cmds.delete(skinned)
    gate("11 an unassigned material gives its colour back",
         not colour.is_assigned(material)
         and not any(colour.same_colour(rgb, BLUE)
                     for rgb in colour.used_colours()),
         "{0} colours still in use".format(len(colour.used_colours())))

    # ============================================ phase 2: two real characters

    MANNY = catalog.default_character()
    roots_before = builder.character_roots()


    def arrived_meshes(before):
        """The RENDERABLE meshes an import brought.

        Manny's "6 meshes" are six mesh SHAPES and only TWO of them are
        renderable -- `Hands_1P` and `Skin_3p`, each carrying its own
        `...Orig` intermediate from the skinCluster and the blendshape
        history (measured 2026-09-03). So the gates below count what is on
        screen, not what `ls -type mesh` answers, or a correct
        implementation fails them.
        """
        fresh = [shape for shape in (cmds.ls(type="mesh", long=True) or [])
                 if shape not in before]
        return [shape for shape in fresh
                if not cmds.getAttr(shape + ".intermediateObject")]


    shapes_before = set(cmds.ls(type="mesh", long=True) or [])
    first_message = character.add_character(MANNY)
    root_a = [r for r in builder.character_roots() if r not in roots_before]
    root_a = root_a[0] if root_a else None
    renderable_a = arrived_meshes(shapes_before)
    register_new()

    meshes_a = colour.character_meshes(root_a)
    colour_a = colour.colour_of(meshes_a)
    gate("12 the recolour path reaches exactly what the press painted",
         bool(root_a) and bool(colour_a) and bool(renderable_a)
         and sorted(meshes_a) == sorted(renderable_a),
         "{0} through the skin, {1} renderable in the import, {2}".format(
             len(meshes_a), len(renderable_a), colour.colour_name(colour_a)))
    gate("13 the press names the colour",
         colour.colour_name(colour_a) in first_message, first_message)

    material_a = colour.material_on(meshes_a)
    painted_a = [shape for shape in renderable_a
                 if colour.material_on([shape]) == material_a]
    gate("14 every mesh the import brought wears it",
         bool(renderable_a) and len(painted_a) == len(renderable_a),
         "{0} of {1}".format(len(painted_a), len(renderable_a)))

    roots_mid = builder.character_roots()
    shapes_mid = set(cmds.ls(type="mesh", long=True) or [])
    second_message = character.add_character(MANNY)
    root_b = [r for r in builder.character_roots() if r not in roots_mid]
    root_b = root_b[0] if root_b else None
    renderable_b = arrived_meshes(shapes_mid)
    register_new()

    meshes_b = colour.character_meshes(root_b)
    colour_b = colour.colour_of(meshes_b)
    material_b = colour.material_on(meshes_b)
    gate("15 the second character is painted too, and says so",
         bool(root_b) and bool(colour_b)
         and sorted(meshes_b) == sorted(renderable_b)
         and colour.colour_name(colour_b) in second_message,
         second_message)
    gate("16 THE POINT: the two colours differ",
         distance(colour_a, colour_b) > 0.1,
         "{0} vs {1}, delta {2:.6f}".format(colour.colour_name(colour_a),
                                            colour.colour_name(colour_b),
                                            distance(colour_a, colour_b)))
    gate("17 and they are two different materials",
         bool(material_a) and material_a != material_b,
         "{0} vs {1}".format(material_a, material_b))
    gate("18 the meshes are found through the skin, not the DAG",
         len(colour.mesh_shapes([root_b])) < len(meshes_b),
         "{0} under the root, {1} through the skin".format(
             len(colour.mesh_shapes([root_b])), len(meshes_b)))

    # The live recolour, which is what the swatch does.
    AMBER = colour.PALETTE[2].rgb
    colour.paint(meshes_b, AMBER, "verify")
    moved = distance(colour.colour_of(meshes_b), AMBER)
    stayed = distance(colour.colour_of(meshes_a), colour_a)
    gate("19 a recolour lands on the character it was asked for",
         moved < 1e-6, "{0:.9f}".format(moved))
    gate("20 and the other character does not move",
         stayed < 1e-9, "{0:.9f}".format(stayed))

    gate("21 the asset's own materials are still in the scene",
         bool(cmds.ls("*M_Manny*", materials=True)
              or [m for m in (cmds.ls(materials=True) or [])
                  if not colour.is_ours(m)]),
         "{0} foreign materials".format(
             len([m for m in (cmds.ls(materials=True) or [])
                  if not colour.is_ours(m)])))

    # ==================================================== phase 3: the weapon

    sword = catalog.by_key("LongSword_02")
    missing = catalog.missing(sword)
    if missing:
        print("SKIPPED the weapon gates - file not on disk: " + missing)
    else:
        bone = skeleton.resolve_bone(root_b, sword.bone)
        hand = attach.parent_bone(bone) if bone else None
        if not hand:
            print("SKIPPED the weapon gates - no weapon_r on this character")
        else:
            weapon, _note = attach.attach(sword, hand, bone)
            register_new()
            weapon_shapes = colour.mesh_shapes([weapon])
            colour_w = colour.colour_of(weapon_shapes)
            gate("22 the weapon arrives painted",
                 bool(colour_w) and bool(weapon_shapes),
                 "{0} mesh(es), {1}".format(len(weapon_shapes),
                                            colour.colour_name(colour_w)))
            gate("23 one palette: the sword differs from the hand holding it",
                 distance(colour_w, colour.colour_of(meshes_b)) > 0.1,
                 "{0} vs {1}".format(colour.colour_name(colour_w),
                                     colour.colour_name(
                                         colour.colour_of(meshes_b))))
            attach.detach(hand, bone)

    # ================================================== phase 4: the panel

    # The swatch is the animator's half of the feature and the only part a
    # unit test cannot reach: a `cmds` window needs a live Maya. Driven
    # against the THROWAWAY character, never the animator's -- repainting
    # theirs would mean restoring a shading assignment afterwards, which is
    # exactly the "put the original look back" machinery this design does
    # not have.
    from maya_scenesetup import window as panel  # noqa: E402

    theirs = [r for r in builder.character_roots()
              if r not in (root_a, root_b)]
    theirs_meshes = colour.character_meshes(theirs[0]) if theirs else []
    theirs_before = colour.colour_of(theirs_meshes)

    cmds.select(root_b)          # `current_root` resolves through selection
    panel.show_window()
    gate("25 the window carries both swatches",
         cmds.colorSliderGrp(panel._CHARACTER_COLOUR, exists=True)
         and cmds.colorSliderGrp(panel._WEAPON_COLOUR, exists=True))

    shown = panel._swatch(panel._CHARACTER_COLOUR)
    gate("26 the swatch shows the connected character's own colour",
         distance(shown, colour.colour_of(meshes_b)) < 1e-6,
         "{0:.9f} from {1}".format(
             distance(shown, colour.colour_of(meshes_b)),
             colour.colour_name(colour.colour_of(meshes_b))))

    VIOLET = colour.PALETTE[6].rgb
    cmds.colorSliderGrp(panel._CHARACTER_COLOUR, edit=True, rgbValue=VIOLET)
    panel.character_colour_changed()
    register_new()
    landed = distance(colour.colour_of(colour.character_meshes(root_b)),
                      VIOLET)
    gate("27 the swatch repaints the connected character", landed < 1e-6,
         "{0:.9f}".format(landed))

    gate("28 and never reaches the animator's own character",
         colour.colour_of(theirs_meshes) is None and theirs_before is None,
         "{0} mesh(es), still {1}".format(
             len(theirs_meshes), colour.colour_of(theirs_meshes)))

finally:
    # ------------------------------------------------------------- teardown
    # From the registry, not from a group: a failure before the group exists
    # leaves debris nothing can find (trap 47). Deepest first, so a child is
    # gone before its parent is asked for.
    leftovers = []
    for uuid in CREATED:
        leftovers.extend(cmds.ls(uuid, long=True) or [])
    for node in sorted(set(leftovers), key=lambda p: -p.count("|")):
        if cmds.objExists(node):
            try:
                cmds.delete(node)
            except Exception:
                pass  # died with a parent already

    # Our own materials go too -- this run made them, and leaving coloured
    # lamberts in the animator's Hypershade is not "left as found". Only the
    # ones that arrived DURING the run: a scene where the animator has
    # already used the feature must keep its colours.
    register_new()
    for material in colour.our_materials():
        uuid = (cmds.ls(material, uuid=True) or [None])[0]
        if uuid not in CREATED:
            continue
        engine = colour.engine_of(material)
        for node in [material] + ([engine] if engine else []):
            if node and cmds.objExists(node):
                try:
                    cmds.delete(node)
                except Exception:
                    pass

    # Closed only if this run opened it: a panel the animator already had up
    # is theirs, and `show_window` has replaced it in place either way.
    if not WINDOW_WAS_OPEN and cmds.window("mayaSceneSetupWindow",
                                           exists=True):
        try:
            cmds.deleteUI("mayaSceneSetupWindow")
        except Exception:
            pass

    cmds.currentTime(FRAME)
    cmds.autoKeyframe(state=AUTOKEY)
    try:
        alive = [node for node in SELECTION if cmds.objExists(node)]
        cmds.select(alive) if alive else cmds.select(clear=True)
    except Exception:
        pass

    leftover = scene_uuids() - BEFORE
    stray, excused = [], []
    for uuid in sorted(leftover):
        for node in cmds.ls(uuid, long=True) or []:
            kind = cmds.objectType(node)
            inherited = cmds.nodeType(node, inherited=True) or []
            if "dagNode" in inherited or kind == "script":
                stray.append("{0} ({1})".format(node, kind))
            else:
                excused.append(kind)
    gate("24 the scene is left as it was found", not stray,
         "stray: {0}; non-DAG singletons excused: {1}".format(
             stray or "none", sorted(set(excused)) or "none"))

    print("")
    print("{0} of {1} gates failed".format(len(FAILURES), 28))
    for label in FAILURES:
        print("  FAILED: " + label)
