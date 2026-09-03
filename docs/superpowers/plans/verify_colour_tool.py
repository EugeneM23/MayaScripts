"""Live verification for maya_colour -- the Colour shelf tool.

Sent through the command port into the animator's OPEN scene. It paints a
SANDBOX character of its own -- a little joint chain with a skinned sphere
plus a loose prop parented under the hand, the shape this rig really has --
rather than the animator's own figures. Their colours are theirs.

Everything created is registered by UUID as it is created, each teardown
step is guarded on its own, and the selection and autoKey go back exactly
as found.
"""

import sys

REPO = "C:/!!!Work/MayaScripts/SkeldarAnim"
if REPO in sys.path:
    sys.path.remove(REPO)
sys.path.insert(0, REPO)
for _key in list(sys.modules):
    if _key.split(".")[0] in ("maya_colour", "maya_scenesetup"):
        del sys.modules[_key]

import maya.cmds as cmds

import maya_colour as mc
from maya_scenesetup import colour as colouring

RESULTS = []


def gate(name, ok, detail=""):
    RESULTS.append((name, bool(ok)))
    print("%-4s %-54s %s" % ("PASS" if ok else "FAIL", name, detail))
    return bool(ok)


def named(name):
    return [c for c in colouring.PALETTE if c.name == name][0]


print("module under test:", mc.__file__)

was_selection = cmds.ls(selection=True, long=True) or []
was_autokey = cmds.autoKeyframe(query=True, state=True)
before_taken = colouring.used_colours()
before_materials = colouring.our_materials()
print("colours already worn in this scene: %d, our materials: %d"
      % (len(before_taken), len(before_materials)))

made = []

try:
    cmds.autoKeyframe(state=False)

    # --- a sandbox character, off to one side --------------------------
    root = cmds.ls(cmds.createNode("joint", name="ctRoot"), long=True)[0]
    made += cmds.ls(root, uuid=True)
    cmds.xform(root, worldSpace=True, translation=(900, 0, 0))
    hand = cmds.ls(cmds.createNode("joint", name="ctHand", parent=root),
                   long=True)[0]
    cmds.xform(hand, objectSpace=True, translation=(0, 40, 0))

    body = cmds.polySphere(radius=12, constructionHistory=False)[0]
    body = cmds.ls(cmds.rename(body, "ctBody"), long=True)[0]
    made += cmds.ls(body, uuid=True)
    cmds.xform(body, worldSpace=True, translation=(900, 20, 0))
    cmds.skinCluster(root, hand, body, toSelectedBones=True)

    #  The prop hangs under the hand JOINT, which is how a weapon does --
    #  and is exactly what makes the two target rules need an order. It
    #  carries the weapon marker, because that is what it stands for.
    prop = cmds.polyCube(width=6, height=30, depth=3,
                         constructionHistory=False)[0]
    prop = cmds.ls(cmds.rename(prop, "ctProp"), long=True)[0]
    prop = cmds.ls(cmds.parent(prop, hand)[0], long=True)[0]
    made += cmds.ls(prop, uuid=True)
    cmds.addAttr(prop, longName=mc.weapon_marker(), dataType="string")
    cmds.setAttr(prop + "." + mc.weapon_marker(), "ctProp", type="string")

    #  An UNmarked prop parented in by hand is part of the figure, and
    #  `character_meshes`' DAG walk is there on purpose to catch it.
    extra = cmds.polyCube(width=4, height=4, depth=4,
                          constructionHistory=False)[0]
    extra = cmds.ls(cmds.rename(extra, "ctPack"), long=True)[0]
    extra = cmds.ls(cmds.parent(extra, hand)[0], long=True)[0]
    made += cmds.ls(extra, uuid=True)

    ctrl = cmds.circle(constructionHistory=False, radius=8)[0]
    ctrl = cmds.ls(cmds.rename(ctrl, "ctCtrl"), long=True)[0]
    made += cmds.ls(ctrl, uuid=True)
    print("sandbox:", root, "|", body, "|", prop)

    # --- target resolution, against the real scene --------------------
    body_shapes = mc.without_weapons(colouring.character_meshes(root))
    prop_shapes = colouring.mesh_shapes([prop])
    target = mc.target_for(hand)
    gate("a bone resolves to its whole character",
         target and target.label == "ctRoot"
         and sorted(target.shapes) == sorted(body_shapes),
         str(target.shapes if target else None))
    gate("the marked weapon is NOT part of the character",
         target and not any(s in target.shapes for s in prop_shapes),
         "or painting the sword would repaint the character")
    gate("but an unmarked prop parented in by hand IS",
         target and any("ctPack" in s for s in target.shapes),
         "that DAG walk is in character_meshes on purpose")
    gate("the character's mesh is found through the skinCluster",
         any("ctBody" in s for s in (target.shapes if target else [])),
         "Manny's meshes sit at world level, so a DAG walk finds none")
    gate("it climbs to the topmost joint, not the nearest",
         mc.skeleton_root(hand) == root, str(mc.skeleton_root(hand)))

    prop_target = mc.target_for(prop)
    gate("a mesh under that bone resolves to the MESH, not the character",
         prop_target and prop_target.label == "ctProp"
         and all("ctProp" in s for s in prop_target.shapes),
         "the sword IS the geometry")
    gate("a control curve names nothing at all",
         mc.target_for(ctrl) is None)
    gate("the key never carries a path separator",
         "|" not in target.key and "|" not in prop_target.key,
         "it reaches cmds.shadingNode(name=...)")

    both = mc.targets([hand, prop], connected=None)
    gate("a bone and a prop are two targets",
         sorted(t.label for t in both) == ["ctProp", "ctRoot"],
         str(sorted(t.label for t in both)))
    gate("two bones of one character are one target",
         len(mc.targets([root, hand], connected=None)) == 1)
    gate("a control alone falls back to the connected character",
         [t.label for t in mc.targets([ctrl], connected=root)] == ["ctRoot"])
    gate("nothing selected and nothing connected paints nothing",
         mc.targets([], connected=None) == [])

    # --- painting for real --------------------------------------------
    teal = named("teal")
    print("paint says:", mc.paint(teal.rgb, selection=[hand]))
    worn = colouring.colour_of(body_shapes)
    gate("the character wears the colour asked for",
         worn and colouring.same_colour(worn, teal.rgb),
         str(["%.3f" % c for c in worn] if worn else None))
    material = colouring.material_on(body_shapes)
    gate("through a material of OURS, never somebody else's",
         material and colouring.is_ours(material), str(material))
    gate("and it is a blinn, like every colour this toolset assigns",
         cmds.nodeType(material) == "blinn", cmds.nodeType(material))

    violet = named("violet")
    mc.paint(violet.rgb, selection=[hand])
    gate("recolouring reuses the same material",
         colouring.material_on(body_shapes) == material,
         "replacing it would drop whatever was tuned on it")
    gate("and the colour really changed",
         colouring.same_colour(colouring.colour_of(body_shapes),
                               violet.rgb))

    pink = named("pink")
    mc.paint(pink.rgb, selection=[prop])
    gate("the weapon takes its own colour",
         colouring.same_colour(colouring.colour_of(prop_shapes), pink.rgb),
         str(["%.3f" % c
              for c in (colouring.colour_of(prop_shapes) or (0, 0, 0))]))
    gate("and the character keeps its own",
         colouring.same_colour(colouring.colour_of(body_shapes),
                               violet.rgb),
         "one press, one target")
    gate("they are two different materials of ours",
         colouring.material_on(body_shapes)
         != colouring.material_on(prop_shapes),
         "%s vs %s" % (colouring.material_on(body_shapes),
                       colouring.material_on(prop_shapes)))

    said = mc.paint(teal.rgb, selection=[ctrl], connected=None)
    gate("a control with no connect is refused, not guessed",
         said == mc.NOTHING_TO_PAINT, said)

    free = colouring.free_colour()
    gate("the next free colour skips what is now worn",
         not any(colouring.same_colour(free.rgb, c.rgb)
                 for c in (violet, pink)),
         "next free is " + free.name)
    print("free-colour press:", mc.paint_free(selection=[hand]))
    gate("and painting with it lands that very colour",
         colouring.same_colour(colouring.colour_of(body_shapes), free.rgb))

    # --- the panel, through its own callbacks -------------------------
    win = mc.show_window()
    gate("the window builds", cmds.window(mc.WINDOW, exists=True), str(win))
    gate("the taken line names a colour now worn",
         "pink" in cmds.text(mc.TAKEN, query=True, label=True),
         cmds.text(mc.TAKEN, query=True, label=True))

    cmds.select(hand, replace=True)
    mc._press(teal.rgb)()
    gate("a palette button paints through the panel",
         colouring.same_colour(colouring.colour_of(body_shapes), teal.rgb),
         cmds.text(mc.STATUS, query=True, label=True))
    gate("and names what it painted",
         "ctRoot" in cmds.text(mc.STATUS, query=True, label=True),
         cmds.text(mc.STATUS, query=True, label=True))

    custom = (0.11, 0.62, 0.44)
    cmds.colorSliderGrp(mc.CUSTOM, edit=True, rgbValue=custom)
    mc._press_custom()
    gate("the custom swatch paints too",
         colouring.same_colour(colouring.colour_of(body_shapes), custom),
         cmds.text(mc.STATUS, query=True, label=True))

    mc.refresh()
    gate("refresh never writes to the swatch",
         colouring.same_colour(
             cmds.colorSliderGrp(mc.CUSTOM, query=True, rgbValue=True),
             custom),
         "the lesson maya_scenesetup.window paid for")

    cmds.select(clear=True)
    mc._press(teal.rgb)()
    gate("with nothing selected the panel says what to do",
         "select" in cmds.text(mc.STATUS, query=True, label=True).lower()
         or "ct" in cmds.text(mc.STATUS, query=True, label=True),
         cmds.text(mc.STATUS, query=True, label=True))

finally:
    for uuid in made:
        for path in (cmds.ls(uuid, long=True) or []):
            if cmds.objExists(path):
                try:
                    cmds.delete(path)
                except Exception as exc:
                    print("  cleanup failed for", path, exc)
    #  Our own sandbox materials go with it: they are ours, and with the
    #  geometry gone nothing wears them. Anything the animator's own
    #  characters wear is still assigned and is left alone.
    for material in colouring.our_materials():
        if material in before_materials:
            continue
        if colouring.is_assigned(material):
            continue
        engine = colouring.engine_of(material)
        for node in (material, engine):
            if node and cmds.objExists(node):
                try:
                    cmds.delete(node)
                except Exception as exc:
                    print("  material cleanup failed for", node, exc)
    try:
        cmds.autoKeyframe(state=was_autokey)
    except Exception as exc:
        print("  autoKey restore failed:", exc)
    try:
        alive = [n for n in was_selection if cmds.objExists(n)]
        if alive:
            cmds.select(alive, replace=True)
        else:
            cmds.select(clear=True)
    except Exception as exc:
        print("  selection restore failed:", exc)

gate("the animator's own colours are untouched",
     len(colouring.used_colours()) == len(before_taken),
     "%d before, %d after" % (len(before_taken),
                              len(colouring.used_colours())))
gate("our materials are back to the count we started with",
     len(colouring.our_materials()) == len(before_materials),
     "%d before, %d after" % (len(before_materials),
                              len(colouring.our_materials())))
gate("no sandbox node is left behind",
     not any(cmds.objExists(n) for n in
             ("ctRoot", "ctHand", "ctBody", "ctProp", "ctPack", "ctCtrl")))
gate("autoKey is as we found it",
     cmds.autoKeyframe(query=True, state=True) == was_autokey)

print()
failed = [name for name, ok in RESULTS if not ok]
print("=== %d of %d gates failed ===" % (len(failed), len(RESULTS)))
for name in failed:
    print("  FAILED:", name)
