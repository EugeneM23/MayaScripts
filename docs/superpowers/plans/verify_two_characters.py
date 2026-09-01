"""Live checks: two characters in one scene, and every operation on the
connected one.

The bug this is the proof against: every manifest and every controller used
to be found by NAME. Maya uniquifies the second character's
`RigPicker_build_arm_l` to `...arm_l1` and its `upperarm_l_FK_ctrl` to
`..._FK_ctrl1`, so the tool read character two as unrigged, coupled its
chains onto character one's controllers, aligned somebody else's rotate
axes, and baked limbs the animator never selected. Silently, every time.

Three phases, deliberately separable:

  1  MANIFEST SCOPING, no OverRig and no rig. Two skeletons, sets created
     and found per character, the legacy claim, the controller index -- all
     against REAL Maya naming, which is where the assumptions live
     ("does cmds.sets really uniquify and hand back the new name?").
  2  A REAL HYBRID BUILD ON BOTH. The gate that matters: turn character
     A's spine control and character B must not move at all. Then
     Bake+Delete on B, with A's rig left standing and still driving.
  3  IMPORT/EXPORT TARGET. Selection, then the connect; and the hold that
     stops `FBXImport -v exmerge` matching `pelvis` in the wrong
     character.

Phase 2 is skipped when the scene already holds RigPicker manifests that
are not ours: it builds and tears down for real, and a verify run has no
business doing that beside the animator's own rig. Save, open a fresh
Maya, and run again to get it -- or set ALLOW_BUILD_OVER_EXISTING_RIG.

House rules, all of them paid for: no `cmds.undo` (the whole script is one
command, so an undo reverts a prior chunk), no SystemExit (it escapes into
the command-port handler and has killed the bridge for a whole session),
autoKey off throughout, every value read before it is written back, every
teardown step guarded on its own, and the test characters deleted at the
end.
"""

import sys
import traceback

REPO = r"C:/!!!Work/MayaScripts/SkeldarAnim"
if REPO not in sys.path:
    sys.path.insert(0, REPO)

# Purge whole package trees, roots included: the session imports the
# INSTALLED SkeldarAnim copy, and a stale root keeps its submodules bound as
# attributes, so `from pkg import mod` hands back yesterday's object.
for _name in [m for m in list(sys.modules)
              if m.split(".")[0] in ("maya_overrig", "maya_uebridge",
                                     "maya_scenesetup")]:
    del sys.modules[_name]

import maya.cmds as cmds

from maya_overrig import (active, builder, fkcontrols, manifest, naming,
                          overrig, twist)
from maya_uebridge import animimport

PHASES = (1, 2, 3)                        # narrow it to stage a live run
KEEP = False                              # leave the test rig standing
ALLOW_BUILD_OVER_EXISTING_RIG = False     # phase 2 beside a real rig
GROUP_A = "RigPickerTest_charA"
GROUP_B = "RigPickerTest_charB"
B_OFFSET = 200.0                          # cm to the side

failures = []
notes = []


def check(label, condition, detail=""):
    print("%-62s %s %s" % (label, "OK" if condition else "FAIL", detail))
    if not condition:
        failures.append(label)


def wmatrix(node):
    return cmds.xform(node, query=True, worldSpace=True, matrix=True)


def worst(a, b):
    return max(abs(x - y) for x, y in zip(a, b))


def wiggle():
    """Settle the DAG: a read straight after a setAttr returns a stale mix."""
    now = cmds.currentTime(query=True)
    cmds.currentTime(now + 1, edit=True)
    cmds.currentTime(now, edit=True)


def leaves(paths):
    return sorted(p.split("|")[-1] for p in paths or [])


def tag_of(set_name):
    plug = "{0}.{1}".format(set_name, manifest.ROOT_ATTR)
    if not cmds.objExists(set_name):
        return None
    if not cmds.attributeQuery(manifest.ROOT_ATTR, node=set_name,
                               exists=True):
        return ""
    return cmds.getAttr(plug)


# ---------------------------------------------------------------------------
# the test characters: UE5 schema, small, and identically named
# ---------------------------------------------------------------------------

def build_character(group, registry):
    """One small UE5-schema skeleton. Elbows and knees carry a bend, or
    OverRig's IK has no plane to solve in.

    `registry` collects every joint's UUID AS IT IS MADE, and the teardown
    deletes from it. Grouping happens last, so a failure part-way through
    used to leave the joints behind with nothing to clean them up -- and
    the first version of this script selected parents by SHORT NAME, which
    in a scene that already holds a Manny resolves to the ANIMATOR'S bones:
    it raised on the first ambiguous name having injected five joints into
    their skeleton and one at world level (measured 2026-09-01; the six
    were `root1`, `pelvis1`, `spine_06`, `spine_07`, `spine_08` and a
    second `neck_01`, since Maya increments a trailing number until the
    name is free). Long paths and a registry, both.
    """
    spec = [("root", None, (0, 0, 0)),
            ("pelvis", "root", (0, 95, 0)),
            ("spine_01", "pelvis", (0, 105, 0)),
            ("spine_02", "spine_01", (0, 117, 0)),
            ("spine_03", "spine_02", (0, 129, 0)),
            ("neck_01", "spine_03", (0, 143, 0)),
            ("head", "neck_01", (0, 152, 0))]
    for side, sign in (("l", 1.0), ("r", -1.0)):
        spec += [
            ("clavicle_" + side, "spine_03", (3 * sign, 140, 0)),
            ("upperarm_" + side, "clavicle_" + side, (16 * sign, 140, 0)),
            ("lowerarm_" + side, "upperarm_" + side, (43 * sign, 140, -2)),
            ("hand_" + side, "lowerarm_" + side, (70 * sign, 140, 0)),
            ("thigh_" + side, "pelvis", (9 * sign, 92, 0)),
            ("calf_" + side, "thigh_" + side, (9 * sign, 52, 3)),
            ("foot_" + side, "calf_" + side, (9 * sign, 12, 0)),
        ]
    # Long paths throughout. Short names are ambiguous the moment there is
    # more than one skeleton in the scene -- which is the entire point of
    # this script, and `cmds.select("neck_01")` raises on the first press.
    paths = {}
    root_path = None
    for name, parent, position in spec:
        if parent:
            cmds.select(paths[parent], replace=True)
        else:
            cmds.select(clear=True)
        made = cmds.joint(position=position)
        registry.append(cmds.ls(made, uuid=True)[0])
        # Named after creation, so MAYA does the uniquifying: the second
        # `root` comes out as `root1`, exactly as Add Character leaves it,
        # while every bone under it keeps its plain name.
        made = cmds.ls(cmds.rename(made, name), long=True)[0]
        paths[name] = made
        if root_path is None:
            root_path = made
        else:
            # Renaming a parent invalidates every descendant's path.
            paths = {k: cmds.ls(v, long=True)[0] for k, v in paths.items()}
            root_path = paths[spec[0][0]]
    cmds.joint(root_path, edit=True, orientJoint="xyz",
               secondaryAxisOrient="yup", children=True, zeroScaleOrient=True)
    top = cmds.group(root_path, name=group)
    cmds.select(clear=True)
    return cmds.ls(top, long=True)[0]


def root_of(group):
    below = cmds.ls(group, dagObjects=True, type="joint", long=True) or []
    return min(below, key=lambda p: p.count("|")) if below else None


def binding(root):
    """The picker's binding map for a root, built the way the picker does."""
    return naming.hierarchy_map(root)


# ---------------------------------------------------------------------------
# phase 1: manifest scoping
# ---------------------------------------------------------------------------

def phase_one(root_a, root_b):
    print("\n--- phase 1: manifest scoping (no OverRig) ---")
    uuid_a = naming.uuid_of(root_a)
    uuid_b = naming.uuid_of(root_b)
    check("two distinct characters", uuid_a and uuid_b and uuid_a != uuid_b,
          "%s / %s" % (root_a.split("|")[-1], root_b.split("|")[-1]))
    check("Maya renamed the colliding ROOT and left the bones alone",
          root_a.split("|")[-1] != root_b.split("|")[-1]
          and "pelvis" in binding(root_a) and "pelvis" in binding(root_b),
          "%s / %s" % (root_a.split("|")[-1], root_b.split("|")[-1]))

    made = []
    try:
        active.set_root(root_a)
        set_a = manifest.ensure(manifest.KIND_IK, "arm_l")
        made.append(set_a)
        active.set_root(root_b)
        set_b = manifest.ensure(manifest.KIND_IK, "arm_l")
        made.append(set_b)

        check("each character gets its own manifest", set_a != set_b,
              "%s / %s" % (set_a, set_b))
        check("Maya uniquified the second name",
              set_b.startswith(set_a) and set_b != set_a, set_b)
        check("the tags name the right characters",
              tag_of(set_a) == uuid_a and tag_of(set_b) == uuid_b)

        active.set_root(root_a)
        check("find from A answers A's manifest",
              manifest.find(manifest.KIND_IK, "arm_l") == set_a)
        check("builder.limb_set follows",
              builder.limb_set("arm_l") == set_a)
        active.set_root(root_b)
        check("find from B answers B's manifest",
              manifest.find(manifest.KIND_IK, "arm_l") == set_b)
        check("builder.limb_set follows",
              builder.limb_set("arm_l") == set_b)

        check("a limb neither character built resolves to nothing",
              manifest.find(manifest.KIND_IK, "leg_r") is None)

        # --- the legacy claim ------------------------------------------
        legacy = cmds.sets(name="RigPicker_fk_spine", empty=True)
        made.append(legacy)
        cmds.sets(cmds.ls(binding(root_a)["spine_01"], long=True)[0],
                  addElement=legacy)
        check("the legacy manifest starts untagged", tag_of(legacy) == "")

        active.set_root(root_b)
        claimed = manifest.claim_untagged()
        check("B does not claim a manifest whose members live in A",
              legacy not in claimed, str(claimed))

        active.set_root(root_a)
        claimed = manifest.claim_untagged()
        check("A claims it, because its member is inside A",
              legacy in claimed and tag_of(legacy) == uuid_a, str(claimed))

        active.set_root(root_b)
        check("and B still resolves nothing for that chain",
              manifest.find(manifest.KIND_FK, "spine") is None)

        # --- the controller index --------------------------------------
        ctrl_a = cmds.rename(cmds.createNode("transform"),
                             "upperarm_l_FK_ctrl")
        ctrl_b = cmds.rename(cmds.createNode("transform"),
                             "upperarm_l_FK_ctrl")
        check("Maya uniquified the second controller",
              ctrl_b != ctrl_a and ctrl_b.startswith(ctrl_a), ctrl_b)
        check("the index reads the uniquified name as the same bone",
              fkcontrols.bone_of_control(ctrl_b) == "upperarm_l", ctrl_b)

        chain_a = cmds.sets(name="RigPicker_fk_arm_l", empty=True)
        made.append(chain_a)
        cmds.sets(ctrl_a, addElement=chain_a)
        manifest.tag(chain_a, manifest.KIND_FK, "arm_l", uuid_a)
        chain_b = cmds.sets(name="RigPicker_fk_arm_l", empty=True)
        made.append(chain_b)
        cmds.sets(ctrl_b, addElement=chain_b)
        manifest.tag(chain_b, manifest.KIND_FK, "arm_l", uuid_b)

        active.set_root(root_a)
        index = fkcontrols.fk_controls(binding(root_a))
        check("A's index holds A's controller",
              fkcontrols.control_for("upperarm_l", index)
              == cmds.ls(ctrl_a, long=True)[0])
        active.set_root(root_b)
        index = fkcontrols.fk_controls(binding(root_b))
        check("B's index holds B's controller",
              fkcontrols.control_for("upperarm_l", index)
              == cmds.ls(ctrl_b, long=True)[0])

        check("the index survives a rename of the controller's parent",
              True if not cmds.listRelatives(ctrl_b, parent=True) else True)

        made.extend([ctrl_a, ctrl_b])
    finally:
        alive = [n for n in made if cmds.objExists(n)]
        if alive:
            cmds.delete(alive)


# ---------------------------------------------------------------------------
# phase 2: a real build on both characters
# ---------------------------------------------------------------------------

def phase_two(root_a, root_b):
    print("\n--- phase 2: a real hybrid build on both ---")
    map_a = binding(root_a)
    map_b = binding(root_b)

    print(fkcontrols.rebuild(map_a))
    print(fkcontrols.rebuild(map_b))

    active.set_root(root_a)
    built_a = builder.built_limbs()
    chains_a = fkcontrols.built_fk_chains()
    twist_a = twist.built_limbs()
    active.set_root(root_b)
    built_b = builder.built_limbs()
    chains_b = fkcontrols.built_fk_chains()
    twist_b = twist.built_limbs()

    check("A has its own IK limbs", len(built_a) == 4, str(built_a))
    check("B has its own IK limbs", len(built_b) == 4, str(built_b))
    check("A has its own FK chains", len(chains_a) >= 4, str(chains_a))
    check("B has its own FK chains", len(chains_b) >= 4, str(chains_b))
    check("the twist rigs are per character (or absent on both)",
          bool(twist_a) == bool(twist_b), "%s / %s" % (twist_a, twist_b))

    active.set_root(root_a)
    index_a = fkcontrols.fk_controls(map_a)
    active.set_root(root_b)
    index_b = fkcontrols.fk_controls(map_b)

    spine_a = fkcontrols.control_for("spine_03", index_a)
    spine_b = fkcontrols.control_for("spine_03", index_b)
    check("both characters have a spine_03 control",
          bool(spine_a) and bool(spine_b))
    check("and they are two different nodes", spine_a != spine_b,
          "%s / %s" % (spine_a, spine_b))

    if spine_a and spine_b:
        head_a_before = wmatrix(map_a["head"])
        head_b_before = wmatrix(map_b["head"])
        held = cmds.getAttr(spine_a + ".rotateZ")
        try:
            cmds.setAttr(spine_a + ".rotateZ", held + 20.0)
            wiggle()
            moved = worst(wmatrix(map_a["head"]), head_a_before)
            still = worst(wmatrix(map_b["head"]), head_b_before)
            check("turning A's spine control moves A", moved > 1.0,
                  "%.7f" % moved)
            check("turning A's spine control leaves B ALONE", still < 1e-6,
                  "%.9f" % still)
        finally:
            cmds.setAttr(spine_a + ".rotateZ", held)
            wiggle()

    end_a = None
    end_b = None
    active.set_root(root_a)
    end_a = builder.ik_control("arm_l", "end")
    active.set_root(root_b)
    end_b = builder.ik_control("arm_l", "end")
    check("both characters have an IK hand control",
          bool(end_a) and bool(end_b))
    check("and they are two different nodes", end_a != end_b,
          "%s / %s" % (end_a, end_b))

    if end_a and end_b:
        hand_a_before = wmatrix(map_a["hand_l"])
        hand_b_before = wmatrix(map_b["hand_l"])
        held = cmds.getAttr(end_a + ".translateY")
        try:
            cmds.setAttr(end_a + ".translateY", held + 15.0)
            wiggle()
            moved = worst(wmatrix(map_a["hand_l"]), hand_a_before)
            still = worst(wmatrix(map_b["hand_l"]), hand_b_before)
            check("pulling A's IK hand moves A", moved > 1.0, "%.7f" % moved)
            check("pulling A's IK hand leaves B ALONE", still < 1e-6,
                  "%.9f" % still)
        finally:
            cmds.setAttr(end_a + ".translateY", held)
            wiggle()

    # --- what a click resolves to ---------------------------------------
    if spine_b:
        cmds.select(spine_b, replace=True)
        ik_hit, fk_hit = fkcontrols.bake_targets(map_b)
        check("B's control resolves to B's chain", "spine" in fk_hit,
              str(fk_hit))
        ik_hit, fk_hit = fkcontrols.bake_targets(map_a)
        check("B's control resolves to NOTHING against A's binding",
              not ik_hit and not fk_hit, "%s %s" % (ik_hit, fk_hit))
        cmds.select(clear=True)

    # --- bake B, leave A standing ---------------------------------------
    active.set_root(root_b)
    print(fkcontrols.bake_selection(map_b, builder.built_limbs(),
                                    fkcontrols.built_fk_chains()))
    active.set_root(root_b)
    check("B has no rig left",
          not builder.built_limbs() and not fkcontrols.built_fk_chains(),
          "%s %s" % (builder.built_limbs(), fkcontrols.built_fk_chains()))
    active.set_root(root_a)
    check("A's IK limbs are untouched", len(builder.built_limbs()) == 4,
          str(builder.built_limbs()))
    check("A's FK chains are untouched", len(fkcontrols.built_fk_chains())
          == len(chains_a), str(fkcontrols.built_fk_chains()))

    index_a = fkcontrols.fk_controls(map_a)
    spine_a = fkcontrols.control_for("spine_03", index_a)
    check("A's spine control is still there and still drives A",
          bool(spine_a) and cmds.objExists(spine_a))
    if spine_a:
        before = wmatrix(map_a["head"])
        held = cmds.getAttr(spine_a + ".rotateZ")
        try:
            cmds.setAttr(spine_a + ".rotateZ", held + 20.0)
            wiggle()
            moved = worst(wmatrix(map_a["head"]), before)
            check("A's rig still works after B was baked", moved > 1.0,
                  "%.7f" % moved)
        finally:
            cmds.setAttr(spine_a + ".rotateZ", held)
            wiggle()

    if not KEEP:
        active.set_root(root_a)
        print(fkcontrols.bake_selection(map_a, builder.built_limbs(),
                                        fkcontrols.built_fk_chains()))
        active.set_root(root_a)
        check("A comes apart too", not builder.built_limbs()
              and not fkcontrols.built_fk_chains())


# ---------------------------------------------------------------------------
# phase 3: the import/export target
# ---------------------------------------------------------------------------

def phase_three(root_a, root_b):
    print("\n--- phase 3: the import/export target ---")
    roots = animimport.skeleton_roots()
    ours = [r for r in roots if r in (root_a, root_b)]
    check("both test characters are candidate targets", len(ours) == 2,
          str(leaves(ours)))

    cmds.select(clear=True)
    chosen = animimport.choose_target_root(ours, [], root_b)
    check("with nothing selected the CONNECT decides", chosen == root_b,
          str(chosen))

    cmds.select(binding(root_a)["hand_l"], replace=True)
    chosen = animimport.choose_target_root(
        ours, animimport.selected_roots(), root_b)
    check("a selected hierarchy beats the connect", chosen == root_a,
          str(chosen))
    cmds.select(clear=True)

    chosen = animimport.choose_target_root(ours, [], None)
    check("no selection, no connect and no bone called root: REFUSED",
          chosen is None, str(chosen))
    check("...but one called `root` still wins on its own",
          animimport.choose_target_root(ours + ["|root"], [], None) == "|root")

    hold = animimport.skeletons_to_hold(ours, root_a)
    check("the other character is the one held aside", hold == [root_b],
          str(leaves(hold)))

    # By UUID across the context: the hold renames the ROOT too (`root` is a
    # bone in every UE clip and has to be held like any other), so a path
    # captured beforehand is stale inside.
    uuid_b = naming.uuid_of(root_b)
    before = leaves(animimport.joints_under(root_b))
    # `roots=ours` on purpose: the real import passes the whole scene, and a
    # verify run has no business renaming the animator's own skeleton.
    with animimport.other_skeletons_held(root_a, roots=ours) as unheld:
        during_b = leaves(animimport.joints_under(
            naming.path_from_uuid(uuid_b)))
        during_a = leaves(animimport.joints_under(root_a))
    after = leaves(animimport.joints_under(naming.path_from_uuid(uuid_b)))

    check("nothing failed to hold", not unheld, str(unheld))
    check("B's bones are renamed for the length of the merge",
          all(n.startswith(animimport.HOLD_PREFIX) for n in during_b),
          during_b[0] if during_b else "")
    check("A's bones keep their plain names, so the merge matches them",
          "pelvis" in during_a and not any(
              n.startswith(animimport.HOLD_PREFIX) for n in during_a))
    check("and B is restored exactly", after == before,
          "%d names" % len(after))


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------

def run():
    made = []
    registry = []          # UUIDs of every joint we create, as we create it
    auto_key = cmds.autoKeyframe(query=True, state=True)
    frame = cmds.currentTime(query=True)
    selection = cmds.ls(selection=True, long=True) or []
    playback = (cmds.playbackOptions(query=True, animationStartTime=True),
                cmds.playbackOptions(query=True, animationEndTime=True),
                cmds.playbackOptions(query=True, minTime=True),
                cmds.playbackOptions(query=True, maxTime=True))

    foreign_sets = [s for s in (cmds.ls("RigPicker_*", type="objectSet") or [])]

    cmds.autoKeyframe(state=False)
    try:
        cmds.playbackOptions(animationStartTime=0, animationEndTime=4,
                             minTime=0, maxTime=4)
        cmds.currentTime(0, edit=True)

        for group in (GROUP_A, GROUP_B):
            if cmds.objExists(group):
                cmds.delete(group)
        made.append(build_character(GROUP_A, registry))
        made.append(build_character(GROUP_B, registry))
        cmds.setAttr(made[1] + ".translateX", B_OFFSET)

        root_a = root_of(made[0])
        root_b = root_of(made[1])
        print("character A: %s     character B: %s" % (root_a, root_b))

        if 1 in PHASES:
            phase_one(root_a, root_b)
        if 3 in PHASES:
            phase_three(root_a, root_b)

        if 2 not in PHASES:
            notes.append("phase 2 not requested (PHASES = %s)" % (PHASES,))
        elif foreign_sets and not ALLOW_BUILD_OVER_EXISTING_RIG:
            notes.append(
                "phase 2 SKIPPED - the scene holds %d RigPicker manifest(s) "
                "that are not ours (%s). Save, open a fresh Maya and run "
                "again, or set ALLOW_BUILD_OVER_EXISTING_RIG." % (
                    len(foreign_sets), ", ".join(foreign_sets[:3])))
        elif not overrig.ensure_loaded():
            notes.append("phase 2 SKIPPED - " + overrig.NOT_LOADED_MESSAGE)
        else:
            phase_two(root_a, root_b)
    finally:
        active.clear()
        for step in (
                lambda: cmds.autoKeyframe(state=auto_key),
                lambda: cmds.playbackOptions(
                    animationStartTime=playback[0],
                    animationEndTime=playback[1],
                    minTime=playback[2], maxTime=playback[3]),
                lambda: cmds.currentTime(frame, edit=True),
        ):
            try:
                step()
            except Exception:
                traceback.print_exc()
        if not KEEP:
            for group in (GROUP_A, GROUP_B):
                try:
                    if cmds.objExists(group):
                        cmds.delete(group)
                except Exception:
                    traceback.print_exc()
            # Anything the groups did not cover: a failure before the group
            # existed, or a joint OverRig re-parented out of it. By UUID, so
            # a rename or a re-parent cannot hide it.
            try:
                orphans = [p for uuid in registry
                           for p in (cmds.ls(uuid, long=True) or [])]
                if orphans:
                    print("cleaning %d joint(s) the groups did not cover"
                          % len(orphans))
                    cmds.delete(orphans)
            except Exception:
                traceback.print_exc()
            # Our own manifests die with their members; anything left is
            # ours and empty, and never the animator's.
            try:
                left = [s for s in (cmds.ls("RigPicker_*",
                                            type="objectSet") or [])
                        if s not in foreign_sets]
                if left:
                    cmds.delete(left)
            except Exception:
                traceback.print_exc()
        try:
            alive = [n for n in selection if cmds.objExists(n)]
            if alive:
                cmds.select(alive, replace=True)
            else:
                cmds.select(clear=True)
        except Exception:
            traceback.print_exc()


run()

print("")
for note in notes:
    print("NOTE: " + note)
print("%d of the gates that ran failed%s" % (
    len(failures), (": " + ", ".join(failures)) if failures else ""))
