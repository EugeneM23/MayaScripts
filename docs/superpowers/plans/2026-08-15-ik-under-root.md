# IK Under Root Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every IK limb's rig hangs under `root_FK_ctrl` so moving the root control carries the whole character, and FK finger controllers stay visible on an IK arm.

**Architecture:** Three OverRig top groups per IK limb (`_IK_strech_gr`, `_IK_knee`, `_IK_feet`) are re-parented under the root controller with `apply_Parent_in`, which re-bakes their animation into the new local space. The reverse (`apply_Parent_out`) runs automatically before any FK chain that contains them is deleted, so the IK rigs survive a root bake. Separately, the hidden finger anchor hides its shape instead of its transform, because visibility inherits down to the finger controllers parented under it.

**Tech Stack:** Python 2/3-compatible `maya.cmds` + `maya.mel` inside Maya 2027, OverRig v10.2 MEL, stdlib `unittest` under `mayapy`, live verification over the Maya command port.

**Spec:** `docs/superpowers/specs/2026-08-15-ik-under-root-design.md`

## Global Constraints

- Layering rules from `CLAUDE.md` hold: `bodymap.py` and `pickerstate.py` stay stdlib-only, `picker_view.py` never imports `maya.cmds`. This plan touches neither.
- Fiddly logic goes into pure functions taking the scene as data; Maya-touching wrappers stay thin.
- Never call `barn_fast_bake_source_obj_and_delete_knots()` — it is scene-global and destroys the user's own setups.
- Never identify rig nodes by bare name — OverRig suffixes renames on collision. Resolve through manifest sets (`builder.ik_control`, `overrig.set_members`).
- Never `cmds.undo()` inside a bridge script, and never write a literal rest value into a keyed or constrained channel — read the value first and write it back.
- Unit tests run with: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v` (run from `C:\!!!Work\MayaScripts`; do not pipe with `2>&1` in PowerShell).
- Branch is `feature/overrig-picker`. Commit messages end with `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`. Write multi-line messages to a file and use `git commit -F` — here-strings with double quotes break in PowerShell 5.1.
- Live verification runs against the user's open Maya scene (`Manny_Sckeleton.ma`) through the command port on `127.0.0.1:7001`. The user's scene is real work: every script resets from any state and leaves no strays.

## The bridge (needed from Task 2 onward)

The port must be listening. Check with:

```bash
powershell -Command "Get-NetTCPConnection -State Listen -LocalPort 7001"
```

If nothing is listening, ask the user to run this once in Maya (do NOT try to open the port over the port itself):

```python
import maya.cmds as cmds
if not cmds.commandPort(":7001", query=True):
    cmds.commandPort(name=":7001", sourceType="python", echoOutput=False)
```

Create the runner **once**, at `<scratchpad>/runner.py`, replacing `<TARGET>` with the verify script path and `<OUT>` with an output file path. The explicit globals dict is load-bearing: when a file is exec'd through the command port without one, module-level names land in a locals dict that nested functions cannot see, and every helper in the verify script raises `NameError`.

```python
import io
import contextlib
import traceback

TARGET = r"C:\!!!Work\MayaScripts\docs\superpowers\plans\verify_ik_under_root.py"
OUT = r"<OUT>"

buf = io.StringIO()
try:
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        with open(TARGET) as handle:
            source = handle.read()
        exec(compile(source, TARGET, "exec"), {"__name__": "__main__"})
except Exception:
    buf.write("\n" + traceback.format_exc())
with open(OUT, "w") as handle:
    handle.write(buf.getvalue())
```

Send it and wait for the output file (the socket reply is NOT a done signal — poll for the file; a full build plus bakes takes minutes):

```bash
powershell -Command "$sp='<scratchpad>'; Remove-Item \"$sp\out.txt\" -ErrorAction SilentlyContinue; $c=New-Object Net.Sockets.TcpClient('127.0.0.1',7001); $s=$c.GetStream(); $b=[Text.Encoding]::UTF8.GetBytes(\"exec(open(r'$sp\runner.py').read())`n\"); $s.Write($b,0,$b.Length); $s.Flush(); $d=(Get-Date).AddSeconds(540); while(-not (Test-Path \"$sp\out.txt\") -and (Get-Date) -lt $d){Start-Sleep -Milliseconds 500}; $c.Close(); Start-Sleep -Milliseconds 500; if(Test-Path \"$sp\out.txt\"){Get-Content \"$sp\out.txt\"}else{'TIMEOUT'}"
```

Use a tool timeout of 600000 ms for that call.

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `maya_overrig/fkcontrols.py` | FK engine, Switch, bake policy — and now the IK↔root coupling, since it is the only module that knows both FK controller names and limb manifests (`builder` importing FK names would be a cycle) | Modify |
| `tests/test_fkcontrols.py` | Unit tests for the pure resolver | Modify |
| `docs/superpowers/plans/verify_ik_under_root.py` | Live proof in the real scene, grown section by section across Tasks 2–5 | Create |
| `CLAUDE.md` | Working notes a fresh session reads first | Modify (Task 5) |

No new module: the added code is ~70 lines of policy that belongs beside `_limb_anchor` and `switch_limbs`, and splitting it out would need imports in both directions.

---

### Task 1: The pure resolver — which IK limbs ride inside doomed FK nodes

**Files:**
- Modify: `maya_overrig/fkcontrols.py` (add after `dependent_chains`, which ends at line 191)
- Test: `tests/test_fkcontrols.py` (add a test class after `TestDependentChains`, which ends at line 158)

**Interfaces:**
- Consumes: `builder.LIMBS` (tuple of `(name, joints)`), `builder._is_inside(path, container)` — strict DAG-descendant test that requires the `|` separator.
- Produces: `fkcontrols.limbs_riding_inside(limb_members, containers) -> [limb names in LIMBS order]`, used by Task 4.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_fkcontrols.py`, directly after the `TestDependentChains` class:

```python
class TestLimbsRidingInside(unittest.TestCase):
    """The mirror of dependent_chains: an IK limb riding inside an FK chain,
    which is what hanging the IK rigs on the root controller creates."""

    MEMBERS = {
        "arm_l": ["|root_FK_ctrl|upperarm_l_IK_strech_gr",
                  "|root_FK_ctrl|upperarm_l_IK_strech_gr|locator1",
                  "|root_FK_ctrl|hand_l_IK_feet"],
        "arm_r": ["|hand_r_IK_feet", "|upperarm_r_IK_strech_gr"],
        "leg_l": ["|root_FK_ctrl|thigh_l_IK_strech_gr"],
        "leg_r": [],
    }

    def test_finds_limbs_inside_the_container(self):
        found = fkcontrols.limbs_riding_inside(self.MEMBERS,
                                               ["|root_FK_ctrl"])
        self.assertEqual(found, ["arm_l", "leg_l"])

    def test_results_come_back_in_limb_table_order(self):
        members = {"leg_l": ["|root_FK_ctrl|thigh_l_IK_strech_gr"],
                   "arm_l": ["|root_FK_ctrl|hand_l_IK_feet"]}
        self.assertEqual(fkcontrols.limbs_riding_inside(members,
                                                        ["|root_FK_ctrl"]),
                         ["arm_l", "leg_l"])

    def test_world_level_limbs_are_not_riding(self):
        self.assertEqual(
            fkcontrols.limbs_riding_inside({"arm_r": ["|hand_r_IK_feet"]},
                                           ["|root_FK_ctrl"]),
            [])

    def test_separator_matters(self):
        """`|root_FK_ctrl_extra` is a different node, not a container."""
        members = {"arm_l": ["|root_FK_ctrl_extra|hand_l_IK_feet"]}
        self.assertEqual(
            fkcontrols.limbs_riding_inside(members, ["|root_FK_ctrl"]), [])

    def test_a_member_equal_to_the_container_is_not_riding(self):
        members = {"arm_l": ["|root_FK_ctrl"]}
        self.assertEqual(
            fkcontrols.limbs_riding_inside(members, ["|root_FK_ctrl"]), [])

    def test_any_container_counts(self):
        members = {"arm_l": ["|pelvis_FK_ctrl|hand_l_IK_feet"]}
        self.assertEqual(
            fkcontrols.limbs_riding_inside(
                members, ["|root_FK_ctrl", "|pelvis_FK_ctrl"]), ["arm_l"])

    def test_missing_and_empty_members_are_skipped(self):
        self.assertEqual(
            fkcontrols.limbs_riding_inside({"arm_l": None}, ["|root_FK_ctrl"]),
            [])
        self.assertEqual(fkcontrols.limbs_riding_inside({}, ["|root_FK_ctrl"]),
                         [])

    def test_no_containers_finds_nothing(self):
        self.assertEqual(fkcontrols.limbs_riding_inside(self.MEMBERS, []), [])
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
'/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe' -m unittest tests.test_fkcontrols.TestLimbsRidingInside -v
```

Expected: FAIL — `AttributeError: module 'maya_overrig.fkcontrols' has no attribute 'limbs_riding_inside'`.

- [ ] **Step 3: Write the implementation**

Add to `maya_overrig/fkcontrols.py` immediately after `dependent_chains` (before `attach_parent`):

```python
def limbs_riding_inside(limb_members, containers):
    """IK limbs whose recorded nodes sit inside one of the container paths.

    The mirror image of `dependent_chains`: there an FK chain rides inside an
    IK limb, here an IK limb rides inside an FK chain -- which is exactly what
    hanging the IK rigs on the root controller creates. Deleting the container
    would take the whole IK rig with it, unbaked, so the caller lifts these
    limbs to world first.

    Pure -- `limb_members` is a {limb: [long paths]} mapping supplied by the
    caller; results keep LIMBS order.
    """
    found = []
    for limb, _ in builder.LIMBS:
        members = limb_members.get(limb) or []
        if any(builder._is_inside(member, container)
               for member in members for container in containers):
            found.append(limb)
    return found
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
'/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe' -m unittest tests.test_fkcontrols.TestLimbsRidingInside -v
```

Expected: PASS, 8 tests.

- [ ] **Step 5: Run the whole suite — nothing else may break**

```bash
'/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe' -m unittest discover -s tests -t . -v
```

Expected: all tests pass (122 before this task, 130 after).

- [ ] **Step 6: Commit**

```bash
git add maya_overrig/fkcontrols.py tests/test_fkcontrols.py && git commit -F commitmsg.txt
```

with `commitmsg.txt` containing (delete the file after committing):

```
feat(fkcontrols): resolve IK limbs riding inside doomed FK nodes

The mirror of dependent_chains, needed once IK rigs hang on the root
controller: baking the root chain must lift them out rather than delete
four IK rigs unbaked.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
```

---

### Task 2: Fingers stay visible — hide the anchor's shape, not its transform

**Root cause (already established, do not re-investigate):** `fkcontrols._limb_anchor` ends with `cmds.setAttr(loc + ".visibility", 0)` where `loc` is the anchor locator's **transform**. `_parent_in` then makes the finger controllers DAG children of that transform, and Maya inherits visibility down the DAG — so every finger ring on an IK arm is invisible while the picker still resolves and selects it. This hits the hybrid Build too, not just Switch.

**Files:**
- Modify: `maya_overrig/fkcontrols.py` (`_limb_anchor`, lines 1136-1161)
- Create: `docs/superpowers/plans/verify_ik_under_root.py`

**Interfaces:**
- Consumes: `builder.limb_set(limb)`, `builder.ik_control(limb, role)`, `fkcontrols._anchor_in(set_name, mark)`.
- Produces: `fkcontrols._mute_anchor(loc)` — transform visible, shapes hidden; safe on locked/connected attrs. Used by `_limb_anchor` on both the create and the reuse path.

- [ ] **Step 1: Write `_mute_anchor` and use it in `_limb_anchor`**

In `maya_overrig/fkcontrols.py`, add `_mute_anchor` directly above `_limb_anchor`:

```python
def _mute_anchor(loc):
    """Hide the anchor's SHAPE and keep its transform visible.

    Finger controllers are DAG children of this locator and visibility
    inherits down a transform: hiding the transform made every finger ring on
    an IK arm invisible in the viewport while the picker still selected it
    happily. Repairing on every lookup heals scenes rigged by the old code.
    """
    for plug, value in [(loc + ".visibility", 1)] + [
            (shape + ".visibility", 0) for shape in
            cmds.listRelatives(loc, shapes=True, fullPath=True) or []]:
        try:
            cmds.setAttr(plug, value)
        except RuntimeError:
            pass  # connected or locked display attr -- cosmetics, skip
```

In `_limb_anchor`, change the reuse branch from:

```python
    existing = _anchor_in(builder.limb_set(limb), mark)
    if existing:
        return existing
```

to:

```python
    existing = _anchor_in(builder.limb_set(limb), mark)
    if existing:
        _mute_anchor(existing)
        return existing
```

and change the creation line from:

```python
    cmds.setAttr(loc + ".visibility", 0)
```

to:

```python
    _mute_anchor(loc)
```

- [ ] **Step 2: Create the live verification harness with its first section**

Create `docs/superpowers/plans/verify_ik_under_root.py`:

```python
"""Live checks: IK rigs ride the root control, fingers stay visible.

Run inside Maya through the bridge runner (see the plan; the runner's
explicit globals dict is what lets these helpers see module-level names).
Binds explicitly to `root`, resets the scene from ANY state, then walks the
flow with assertions at every step. No cmds.undo -- the whole script is one
command, and undoing reverts a prior chunk. Values are read before they are
written back; autoKey is off throughout.
"""

import sys

REPO = r"C:/!!!Work/MayaScripts"
if REPO not in sys.path:
    sys.path.append(REPO)

for name in [m for m in list(sys.modules) if m.startswith("maya_overrig")]:
    del sys.modules[name]

import maya.cmds as cmds

import maya_overrig
from maya_overrig import bodymap, builder, fkcontrols, overrig

failures = []


def check(label, condition, detail=""):
    print("%-58s %s %s" % (label, "OK" if condition else "FAIL", detail))
    if not condition:
        failures.append(label)


def wpos(node):
    return cmds.xform(node, query=True, worldSpace=True, translation=True)


def dist(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


def is_under(child, parent):
    if not (child and parent and cmds.objExists(child)
            and cmds.objExists(parent)):
        return False
    return cmds.ls(child, long=True)[0].startswith(
        cmds.ls(parent, long=True)[0] + "|")


def visible(node):
    """Effective visibility: the node's flag and every ancestor's."""
    if not cmds.objExists(node):
        return False
    path = cmds.ls(node, long=True)[0]
    while path:
        if not cmds.getAttr(path + ".visibility"):
            return False
        path = path.rsplit("|", 1)[0]
    return True


def wiggle():
    """Settle the DAG -- reads straight after a setAttr return stale mixtures."""
    now = cmds.currentTime(query=True)
    cmds.currentTime(now + 1, edit=True)
    cmds.currentTime(now, edit=True)


def stray_ik_roots():
    return [n.split("|")[-1] for n in
            (cmds.ls("|*_IK_feet", "|*_IK_knee", "|*_IK_strech_gr",
                     long=True) or [])]


def node_count():
    return len([n for n in cmds.ls(long=True)
                if not cmds.objectType(n).startswith("animCurve")])


FINGER_CTRLS = [fkcontrols.controller_name(j) for j in
                ("index_metacarpal_l", "index_01_l", "thumb_01_l",
                 "pinky_metacarpal_r", "middle_02_r")]

auto_key = cmds.autoKeyframe(query=True, state=True)
cmds.autoKeyframe(state=False)

window = maya_overrig.show_picker()
cmds.select("root", replace=True)
window.connect_to_selection()
smap = window._scene_map

# --- reset from ANY state ---------------------------------------------------
if builder.has_build():
    builder.bake_limbs(smap, builder.built_limbs())
if fkcontrols.has_fk():
    fkcontrols.bake_fk(smap)
bones = [smap[b.joint] for b in bodymap.BUTTONS if b.joint in smap
         and cmds.objExists(smap[b.joint])]
constrained = [b for b in bones
               if cmds.listRelatives(b, children=True, type="constraint")]
if constrained:
    print("reset: sweeping %d constrained bones" % len(constrained))
    overrig.fast_bake(constrained)
    overrig.delete_constraint_attributes(constrained)
    for b in constrained:
        for con in cmds.listRelatives(b, children=True, type="constraint",
                                      fullPath=True) or []:
            if cmds.objExists(con):
                cmds.delete(con)
for s in cmds.ls("RigPicker_*", type="objectSet") or []:
    if not overrig.set_members(s):
        cmds.delete(s)
for n in cmds.ls("|*_IK_feet", "|*_IK_knee", "|*_IK_strech_gr",
                 long=True) or []:
    print("reset: deleting stray", n)
    cmds.delete(n)

baseline = node_count()
print("baseline non-anim nodes: %d\n" % baseline)

# --- hybrid build -----------------------------------------------------------
print(fkcontrols.rebuild(smap, fk_limbs=False), "\n")

# --- section 1: fingers are visible on the IK hands -------------------------
for ctrl in FINGER_CTRLS:
    check("finger control exists: " + ctrl, cmds.objExists(ctrl))
    check("FINGER CONTROL IS VISIBLE: " + ctrl, visible(ctrl))

for limb in ("arm_l", "arm_r"):
    anchor = fkcontrols._limb_anchor(smap, limb)
    check("anchor transform is visible: " + limb,
          bool(anchor) and cmds.getAttr(anchor + ".visibility") == 1,
          str(anchor))
    shapes = cmds.listRelatives(anchor, shapes=True, fullPath=True) or []
    check("anchor shape is hidden: " + limb,
          bool(shapes) and all(cmds.getAttr(s + ".visibility") == 0
                               for s in shapes),
          str(shapes))
    check("fingers hang on the anchor: " + limb,
          is_under(fkcontrols.controller_name(
              "index_metacarpal_" + limb[-1]), anchor))

print("\n%s" % ("SECTIONS SO FAR PASS" if not failures
                else "FAILURES: %s" % failures))
cmds.autoKeyframe(state=auto_key)
```

- [ ] **Step 3: Run it through the bridge**

Set up `runner.py` per "The bridge" section above, then send it. Expected: every `finger control exists`, `FINGER CONTROL IS VISIBLE`, `anchor transform is visible`, `anchor shape is hidden` and `fingers hang on the anchor` line reads OK, ending with `SECTIONS SO FAR PASS`.

If a finger control is missing rather than invisible, the build did not complete — read the whole output for the `rebuild` message before changing any code.

- [ ] **Step 4: Run the unit suite — the refactor must not break it**

```bash
'/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe' -m unittest discover -s tests -t . -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add maya_overrig/fkcontrols.py docs/superpowers/plans/verify_ik_under_root.py && git commit -F commitmsg.txt
```

```
fix(fkcontrols): keep FK finger controls visible on an IK arm

_limb_anchor hid the anchor locator's TRANSFORM, and the finger
controllers parented under it inherited the invisibility -- the rings
existed and the picker selected them, but the viewport showed nothing.
Hide the shape instead, and repair existing anchors on lookup so scenes
rigged by the old code heal themselves.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
```

---

### Task 3: Hang the IK limbs on the root controller

**Files:**
- Modify: `maya_overrig/fkcontrols.py` (`_record_fresh` at 483-495, `_parent_out`/`_parent_in` at 1100-1113, `_rehang_riders` at 1164-1178, `rebuild` at 1067-1090, `switch_limbs` at 1195-1236)
- Modify: `docs/superpowers/plans/verify_ik_under_root.py` (append section 2)

**Interfaces:**
- Consumes: `limbs_riding_inside` is NOT used here (Task 4 uses it). Uses `builder.ik_control(limb, role)`, `builder._ensure_limb_set(limb)`, `builder._is_inside`.
- Produces:
  - `fkcontrols.IK_TOP_ROLES = ("base", "pole", "end")`
  - `fkcontrols._record_into(set_name, before) -> [fresh long paths]`
  - `fkcontrols._parent_in(child_ctrl, parent_ctrl, set_name)` and `fkcontrols._parent_out(ctrl, set_name)` — **signature change**: the third argument is now an object-set NAME, not a chain name.
  - `fkcontrols.hang_ik_on_root(limb) -> int` (groups moved; 0 when no root controller exists)
  - `fkcontrols.lift_ik_off_root(limb) -> int` (groups lifted to world) — used by Task 4.

- [ ] **Step 1: Generalise the recording helpers to take a set name**

In `maya_overrig/fkcontrols.py`, replace `_record_fresh` (lines 483-495) with:

```python
def _record_into(set_name, before):
    """Record (and visually mute) everything created since `before`.

    `before` is a UUID snapshot: re-parented nodes must NOT read as fresh,
    or a chain's manifest swallows another chain's controllers.
    """
    fresh = [n for n in builder._fresh_paths(before, builder._scene_nodes())
             if builder._recordable(n)]
    if fresh:
        cmds.sets(fresh, addElement=set_name)
        _hide_rig_machinery(fresh)
    return fresh


def _record_fresh(chain, before):
    """Record everything created since `before` against one FK chain."""
    return _record_into(_ensure_chain_set(chain), before)
```

Then replace `_parent_out` and `_parent_in` (lines 1100-1113) with:

```python
def _parent_out(ctrl, set_name):
    """Lift a nested knot to world through OverRig, animation re-baked."""
    before = builder._scene_nodes()
    cmds.select(ctrl, replace=True)
    mel.eval("apply_Parent_out()")
    _record_into(set_name, before)


def _parent_in(child_ctrl, parent_ctrl, set_name):
    """Hang a knot inside another through OverRig, animation re-baked.

    Selection order is child first, parent last -- verified by experiment.
    """
    before = builder._scene_nodes()
    cmds.select([child_ctrl, parent_ctrl], replace=True)
    mel.eval("apply_Parent_in()")
    _record_into(set_name, before)
```

Update the three existing call sites to pass a set name:

- in `rebuild`, `_parent_in(ctrl, target, chain)` becomes `_parent_in(ctrl, target, _ensure_chain_set(chain))`
- in `_rehang_riders`, `_parent_in(ctrl, target, chain)` becomes `_parent_in(ctrl, target, _ensure_chain_set(chain))`
- in `switch_limbs`, `_parent_out(ctrl, chain)` becomes `_parent_out(ctrl, _ensure_chain_set(chain))`

- [ ] **Step 2: Add the hang and lift functions**

In `maya_overrig/fkcontrols.py`, add directly below `_limb_anchor`:

```python
# The three groups apply_rebike_3_or_more_object_to_IK leaves at world root.
IK_TOP_ROLES = ("base", "pole", "end")


def hang_ik_on_root(limb):
    """Hang a limb's three IK top groups under the root controller.

    All three, machinery included. Measured on a live build: the IK rig is
    anchored in world end to end -- moving the root BONE moved neither the
    controls nor the upperarm bone. Parenting only the two animator controls
    would carry the effector targets while the chain base stayed pinned, and
    the shoulder tears off the body.

    apply_Parent_in re-bakes the animation into the new local space, so
    nothing moves. Fresh nodes go into the LIMB manifest: the coupling lives
    and dies with the IK rig, not with the root chain.

    Returns the number of groups moved. Zero when there is no root controller
    -- IK built by Switch after a full bake stays in world, and the next
    Build re-hangs it.
    """
    root_ctrl = controller_name("root")
    if not cmds.objExists(root_ctrl):
        return 0
    root_path = cmds.ls(root_ctrl, long=True)[0]
    hung = 0
    for role in IK_TOP_ROLES:
        node = builder.ik_control(limb, role)
        if not node or not cmds.objExists(node):
            continue
        if builder._is_inside(cmds.ls(node, long=True)[0], root_path):
            continue  # already there; the operation is idempotent
        _parent_in(node, root_ctrl, builder._ensure_limb_set(limb))
        hung += 1
    return hung


def lift_ik_off_root(limb):
    """Lift a limb's IK top groups back to world, animation re-baked.

    Run before whatever they hang inside is deleted: the rig keeps working
    and only its container dies.
    """
    lifted = 0
    for role in IK_TOP_ROLES:
        node = builder.ik_control(limb, role)
        if not node or not cmds.objExists(node):
            continue
        if not cmds.listRelatives(node, parent=True):
            continue  # already in world
        _parent_out(node, builder._ensure_limb_set(limb))
        lifted += 1
    return lifted
```

- [ ] **Step 3: Call it from the hybrid Build**

In `rebuild`, the hybrid branch currently reads:

```python
            result = builder.build(scene_map,
                                   only=list(builder.DEFAULT_IK))
            messages.append(result.message)
```

Insert the hang immediately after, before the finger block, so the fingers are hung in the limb's final space:

```python
            result = builder.build(scene_map,
                                   only=list(builder.DEFAULT_IK))
            messages.append(result.message)

            # The IK rigs are anchored in world; hang them on the root
            # controller so the root carries the whole character.
            hung_ik = sum(hang_ik_on_root(limb) for limb in result.built)
            if hung_ik:
                messages.append(
                    "{0} IK group(s) on the root control".format(hung_ik))
```

- [ ] **Step 4: Call it from both Switch paths**

In `switch_limbs`, the auto-build branch currently reads:

```python
                builder.build(scene_map, only=[limb])
                done.append(limb + " -> IK (built)")
                continue
```

becomes:

```python
                builder.build(scene_map, only=[limb])
                hang_ik_on_root(limb)
                done.append(limb + " -> IK (built)")
                continue
```

and the FK→IK branch currently reads:

```python
            if is_fk:
                _bake_fk_chains(scene_map, [limb])
                builder.build(scene_map, only=[limb])
                done.append(limb + " -> IK")
                now_ik = True
```

becomes:

```python
            if is_fk:
                _bake_fk_chains(scene_map, [limb])
                builder.build(scene_map, only=[limb])
                hang_ik_on_root(limb)
                done.append(limb + " -> IK")
                now_ik = True
```

- [ ] **Step 5: Append section 2 to the verify script**

In `docs/superpowers/plans/verify_ik_under_root.py`, replace the trailing three lines

```python
print("\n%s" % ("SECTIONS SO FAR PASS" if not failures
                else "FAILURES: %s" % failures))
cmds.autoKeyframe(state=auto_key)
```

with:

```python
# --- section 2: every IK group rides the root control -----------------------
root_ctrl = fkcontrols.controller_name("root")
check("root controller exists", cmds.objExists(root_ctrl))
for limb in builder.DEFAULT_IK:
    for role in fkcontrols.IK_TOP_ROLES:
        node = builder.ik_control(limb, role)
        check("%s %s rides the root control" % (limb, role),
              is_under(node, root_ctrl), str(node))

# The whole character must travel with the root control: bones, IK controls
# and finger rings alike. Read the value first, then put it back.
cmds.currentTime(0)
probes = {"upperarm_l bone": smap["upperarm_l"],
          "hand_l bone": smap["hand_l"],
          "foot_r bone": smap["foot_r"],
          "arm_l IK end": builder.ik_control("arm_l", "end"),
          "leg_r IK pole": builder.ik_control("leg_r", "pole"),
          "index_l ring": fkcontrols.controller_name("index_metacarpal_l")}
before_move = {k: wpos(v) for k, v in probes.items()}
rest = cmds.getAttr(root_ctrl + ".translate")[0]
cmds.setAttr(root_ctrl + ".translateX", rest[0] + 50.0)
wiggle()
after_move = {k: wpos(v) for k, v in probes.items()}
cmds.setAttr(root_ctrl + ".translate", *rest)
wiggle()
for name in sorted(probes):
    moved = dist(after_move[name], before_move[name])
    check("MOVES WITH THE ROOT CONTROL: " + name, abs(moved - 50.0) < 0.5,
          "%.3f cm" % moved)
for name in sorted(probes):
    back = dist(wpos(probes[name]), before_move[name])
    check("returns to rest: " + name, back < 0.01, "%.4f cm" % back)

print("\n%s" % ("SECTIONS SO FAR PASS" if not failures
                else "FAILURES: %s" % failures))
cmds.autoKeyframe(state=auto_key)
```

- [ ] **Step 6: Run the verify script through the bridge**

Send `runner.py` as in "The bridge". Expected: sections 1 and 2 all OK — twelve `rides the root control` lines, then every `MOVES WITH THE ROOT CONTROL` at 50.000 ± 0.5 and every `returns to rest` under 0.01, ending `SECTIONS SO FAR PASS`.

If a bone reads 0.000 while the IK control reads 50.000, the base group did not come along — check that `hang_ik_on_root` moved all three roles and that `builder.ik_control(limb, "base")` resolved.

- [ ] **Step 7: Run the unit suite**

```bash
'/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe' -m unittest discover -s tests -t . -v
```

Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add maya_overrig/fkcontrols.py docs/superpowers/plans/verify_ik_under_root.py && git commit -F commitmsg.txt
```

```
feat(fkcontrols): hang every IK limb on the root control

All three top groups per limb, machinery included: the IK rig is
anchored in world end to end, so carrying only the animator controls
would drag the effector targets while the chain base stayed pinned.
apply_Parent_in re-bakes into the new space, and the coupling nodes are
recorded in the limb manifest so they die with the IK rig.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
```

---

### Task 4: A root bake lifts the IK rigs instead of destroying them

Without this, `Bake+Delete` on the root chain — and the FK-first teardown inside every full `Build` — deletes four IK rigs unbaked, because they are now DAG children of `root_FK_ctrl`.

**Files:**
- Modify: `maya_overrig/fkcontrols.py` (`_bake_fk_chains`, lines 805-855)
- Modify: `docs/superpowers/plans/verify_ik_under_root.py` (append section 3)

**Interfaces:**
- Consumes: `limbs_riding_inside(limb_members, containers)` from Task 1, `lift_ik_off_root(limb)` from Task 3, `builder.limb_set(name)`, `overrig.set_members(set_name)`.
- Produces: no new API — behavioural change inside `_bake_fk_chains`, which every bake path already funnels through (`bake_fk`, `bake_selection`, `rebuild`, `switch_limbs`).

- [ ] **Step 1: Lift riding IK limbs before anything is deleted**

In `_bake_fk_chains`, immediately after

```python
    wanted = [c for c in builder.order_by_nesting(wanted, members_by_chain)
              if members_by_chain.get(c)]
    if not wanted and not legacy:
        return 0, []
```

insert:

```python
    # IK limbs hang on the root controller. Anything about to be deleted that
    # contains one must let it go first: apply_Parent_out re-bakes the rig
    # into world space, so the limb keeps working and only its container
    # dies. Without this a Bake+Delete on root -- and the FK-first teardown
    # inside every full Build -- deletes four IK rigs unbaked.
    doomed_preview = list(legacy)
    for c in wanted:
        doomed_preview.extend(members_by_chain[c])
    limb_members = {name: overrig.set_members(builder.limb_set(name))
                    for name, _ in builder.LIMBS}
    for limb in limbs_riding_inside(limb_members, doomed_preview):
        lift_ik_off_root(limb)
```

This runs before the bake of the chain's own bones, while the IK rigs are still intact.

- [ ] **Step 2: Append section 3 to the verify script**

Replace the trailing

```python
print("\n%s" % ("SECTIONS SO FAR PASS" if not failures
                else "FAILURES: %s" % failures))
cmds.autoKeyframe(state=auto_key)
```

with:

```python
# --- section 3: Bake+Delete on root lifts the IK rigs, does not kill them ---
cmds.currentTime(0)
hand_before = wpos(smap["hand_l"])
foot_before = wpos(smap["foot_r"])
cmds.select(root_ctrl, replace=True)
ik_hit, fk_hit = fkcontrols.bake_targets(smap)
check("root selection resolves to the root chain only",
      (ik_hit, fk_hit) == ([], ["root"]), "%s %s" % (ik_hit, fk_hit))
print(fkcontrols.bake_selection(smap, ik_hit, fk_hit), "\n")
wiggle()

check("root controller is gone", not cmds.objExists(root_ctrl))
check("ALL FOUR IK LIMBS SURVIVED",
      set(builder.built_limbs()) == set(builder.DEFAULT_IK),
      str(builder.built_limbs()))
for limb in builder.DEFAULT_IK:
    node = builder.ik_control(limb, "end")
    check("%s IK end is back in world" % limb,
          bool(node) and not cmds.listRelatives(node, parent=True),
          str(node))
check("hand_l did not drift", dist(wpos(smap["hand_l"]), hand_before) < 0.05,
      "%.4f cm" % dist(wpos(smap["hand_l"]), hand_before))
check("foot_r did not drift", dist(wpos(smap["foot_r"]), foot_before) < 0.05,
      "%.4f cm" % dist(wpos(smap["foot_r"]), foot_before))

# The lifted rig must still DRIVE its bone.
ik_end = builder.ik_control("arm_l", "end")
rest_end = cmds.getAttr(ik_end + ".translate")[0]
cmds.setAttr(ik_end + ".translateY", rest_end[1] - 10.0)
wiggle()
moved_hand = dist(wpos(smap["hand_l"]), hand_before)
cmds.setAttr(ik_end + ".translate", *rest_end)
wiggle()
check("LIFTED IK STILL DRIVES THE HAND", moved_hand > 5.0,
      "%.3f cm" % moved_hand)
check("hand returns to rest after the poke",
      dist(wpos(smap["hand_l"]), hand_before) < 0.05)

print("\n%s" % ("SECTIONS SO FAR PASS" if not failures
                else "FAILURES: %s" % failures))
cmds.autoKeyframe(state=auto_key)
```

- [ ] **Step 3: Run the verify script through the bridge**

Expected: sections 1–3 all OK. `root selection resolves to the root chain only` proves the innermost-owner resolution still separates the root control from the IK groups nested under it; `ALL FOUR IK LIMBS SURVIVED` and `LIFTED IK STILL DRIVES THE HAND` are the point of the task.

- [ ] **Step 4: Run the unit suite**

```bash
'/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe' -m unittest discover -s tests -t . -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add maya_overrig/fkcontrols.py docs/superpowers/plans/verify_ik_under_root.py && git commit -F commitmsg.txt
```

```
feat(fkcontrols): lift riding IK rigs before their container is baked

The IK limbs are DAG children of the root controller now, so baking the
root chain would delete four IK rigs unbaked -- including inside every
full Build, which bakes FK first. _bake_fk_chains lifts them to world
with apply_Parent_out first; they keep working and only the container
dies.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
```

---

### Task 5: Regression sweep and working notes

**Files:**
- Modify: `docs/superpowers/plans/verify_ik_under_root.py` (append section 4)
- Modify: `CLAUDE.md`

**Interfaces:**
- Consumes: everything built in Tasks 1–4. Produces no new API.

- [ ] **Step 1: Append the regression section to the verify script**

Replace the trailing

```python
print("\n%s" % ("SECTIONS SO FAR PASS" if not failures
                else "FAILURES: %s" % failures))
cmds.autoKeyframe(state=auto_key)
```

with:

```python
# --- section 4: regressions the old traps left behind -----------------------
# Rebuild the hybrid rig -- this also exercises the FK-first teardown over
# the lifted IK rigs from section 3.
print(fkcontrols.rebuild(smap, fk_limbs=False), "\n")
root_ctrl = fkcontrols.controller_name("root")
check("rebuild restored the root controller", cmds.objExists(root_ctrl))
check("rebuild re-hung every IK limb",
      all(is_under(builder.ik_control(limb, role), root_ctrl)
          for limb in builder.DEFAULT_IK
          for role in fkcontrols.IK_TOP_ROLES),
      str(builder.built_limbs()))

# Overpull: fingers must stay on the hand even with the rig under root.
cmds.currentTime(0)
ik_hand = builder.ik_control("arm_r", "end")
rest_hm = dist(wpos(smap["hand_r"]), wpos(smap["index_metacarpal_r"]))
rest_up = dist(wpos(smap["upperarm_r"]), wpos(smap["lowerarm_r"]))
rest = cmds.getAttr(ik_hand + ".translate")[0]
cmds.setAttr(ik_hand + ".translate", rest[0], rest[1] - 40, rest[2])
wiggle()
hm = dist(wpos(smap["hand_r"]), wpos(smap["index_metacarpal_r"]))
up = dist(wpos(smap["upperarm_r"]), wpos(smap["lowerarm_r"]))
cmds.setAttr(ik_hand + ".translate", *rest)
wiggle()
check("FINGERS STAY ON THE HAND under a 40cm overpull",
      hm < rest_hm + 2.0, "%.2f cm (rest %.2f, was 33)" % (hm, rest_hm))
check("the limb itself does not stretch", abs(up - rest_up) < 0.5,
      "%.2f vs %.2f" % (up, rest_up))

# Switch there and back: IK -> FK -> IK must end hung on the root again.
done, skipped, message = fkcontrols.switch_limbs(smap, ["arm_l"])
print("\nswitch arm_l to FK:", message)
check("arm_l switched to FK", done == ["arm_l -> FK"], str(done))
check("torso survived the switch",
      all(cmds.objExists(fkcontrols.controller_name(j))
          for j in ("root", "pelvis", "spine_03", "neck_01")))
check("left fingers on the FK hand",
      is_under(fkcontrols.controller_name("index_metacarpal_l"),
               fkcontrols.controller_name("hand_l")))

done, skipped, message = fkcontrols.switch_limbs(smap, ["arm_l"])
print("switch arm_l back to IK:", message)
check("arm_l is IK again", "arm_l" in builder.built_limbs(),
      str(builder.built_limbs()))
check("SWITCHED LIMB IS HUNG ON THE ROOT AGAIN",
      all(is_under(builder.ik_control("arm_l", role), root_ctrl)
          for role in fkcontrols.IK_TOP_ROLES))
check("left fingers visible again",
      visible(fkcontrols.controller_name("index_metacarpal_l")))

# --- full teardown ----------------------------------------------------------
fkcontrols.bake_fk(smap)
if builder.has_build():
    builder.bake_limbs(smap, builder.built_limbs())
now = node_count()
check("scene no dirtier than the baseline", now <= baseline,
      "%d -> %d" % (baseline, now))
check("no strays at the end", not stray_ik_roots(), str(stray_ik_roots()))
check("no rig nodes left on the bones",
      not [b for b in bones
           if cmds.listRelatives(b, children=True, type="constraint")])

cmds.currentTime(0)
cmds.select(clear=True)
cmds.autoKeyframe(state=auto_key)
print("\n%s" % ("IK UNDER ROOT WORKS" if not failures
                else "FAILURES: %s" % failures))
```

- [ ] **Step 2: Run the complete verify script through the bridge**

Expected: every line OK, ending `IK UNDER ROOT WORKS`. This run takes several minutes (two full builds, several bakes) — poll for the output file with the 540-second deadline and a 600000 ms tool timeout, and do not close the socket early.

- [ ] **Step 3: Run the unit suite one final time**

```bash
'/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe' -m unittest discover -s tests -t . -v
```

Expected: all pass.

- [ ] **Step 4: Update `CLAUDE.md`**

Three edits, so a fresh session reads current behaviour:

1. In the "What the tool does today" section, after the paragraph beginning "**Fingers on an IK arm hang on `<limb>_IK_anchor`**", add:

```markdown
**Every IK limb hangs on `root_FK_ctrl`** — all three OverRig top groups
(`_IK_strech_gr`, `_IK_knee`, `_IK_feet`), via `apply_Parent_in`
(`fkcontrols.hang_ik_on_root`), so the root control carries the whole
character. All three, machinery included: the IK rig is anchored in world
end to end (measured — moving the root BONE moved neither the controls nor
the `upperarm` bone), so carrying only the two animator controls drags the
effector targets while the chain base stays pinned and the shoulder tears
off. The coupling nodes are recorded in the LIMB manifest, so they die with
the IK rig. With no root controller in the scene the rig stays in world and
the next Build re-hangs it. The reverse runs automatically:
`_bake_fk_chains` lifts any riding IK limb to world
(`lift_ik_off_root`) before deleting a chain that contains it, so
Bake+Delete on root leaves the IK limbs alive and working — and the
FK-first teardown inside every full Build no longer destroys four IK rigs
unbaked.
```

2. In the "Traps already hit" list, append:

```markdown
15. **Hiding a rig helper's TRANSFORM hides whatever is parented under
   it.** `_limb_anchor` hid the anchor locator's transform, and the finger
   controllers hung on it inherited the invisibility — the rings existed
   and the picker selected them happily, but the viewport showed nothing
   ("переключаешь руку в ИК — ФК контролы пальцев не отображаются"). Hide
   the SHAPE, which is what `_hide_rig_machinery` already does; anchors
   rigged by the old code are repaired on lookup.
16. **A file exec'd over the command port may not see its own module-level
   names.** `exec(open(path).read())` sent as a one-liner runs where
   `globals()` is not `locals()`, so functions defined in the file raise
   `NameError` on module-level imports — reading like a broken import
   rather than a harness bug. The runner must pass an explicit globals
   dict: `exec(compile(src, path, "exec"), {"__name__": "__main__"})`.
```

3. In the "Not built" paragraph, leave the spine IK note as it is — this
   change does not affect it.

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md docs/superpowers/plans/verify_ik_under_root.py && git commit -F commitmsg.txt
```

```
docs: record IK-under-root behaviour and two new traps

Working notes for a fresh session: what hangs where and what the bake
does about it, plus the transform-visibility trap that hid the finger
controls and the command-port exec-globals trap that makes a verify
script look like a broken import.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
```

---

## Self-Review

**Spec coverage.** Decision 1 (all three groups via `apply_Parent_in`) → Task 3 Step 2. Decision 2 (called from `fkcontrols` after each `builder.build`) → Task 3 Steps 3–4, covering the hybrid Build, Switch FK→IK, and the Switch auto-build. Decision 3 (fresh nodes into the limb manifest) → Task 3 Step 1's `_record_into` plus `builder._ensure_limb_set` in `hang_ik_on_root`. Decision 4 (no root controller → skip, rig stays in world) → the `cmds.objExists(root_ctrl)` guard in `hang_ik_on_root`. Decision 5 (lift, don't kill) → Task 4. Decision 6 (Switch IK→FK unchanged) → verified in Task 5's switch-there-and-back section. Decision 7 (selection resolution already correct) → asserted by `root selection resolves to the root chain only` in Task 4 Step 2. Bug fix → Task 2. Verification plan → the unit tests in Task 1 and the four verify sections; every listed live check (hang, visibility, root move, overpull, switch round trip, root bake, full teardown) has a task.

**Placeholders.** None: every step carries the actual code or the actual command.

**Type consistency.** `limbs_riding_inside(limb_members, containers)` is defined in Task 1 and called in Task 4 with `{name: [paths]}` and a list of paths — matching. `_parent_in`/`_parent_out` change signature in Task 3 Step 1 and all three existing call sites are updated in the same step; the new callers in `hang_ik_on_root`/`lift_ik_off_root` pass `builder._ensure_limb_set(limb)`, also a set name. `IK_TOP_ROLES` values match `builder.IK_ROLES` keys (`base`, `pole`, `end`). `hang_ik_on_root` and `lift_ik_off_root` both return `int`.
