# Pose Library — original curves and layers: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** An animation card keeps the source's own curves, layer by layer, and pastes them back exactly — keys, tangents, breakdowns, infinity, layers with their settings — onto the same rig model (or the card's objects), beside today's bone retarget.

**Architecture:** A pure module (`curvedata`) holds the file's rules, the layer pairing and Connect's arithmetic. `keys` grows the scene half of layers: the stack, a layer's record and plugs, a RAW key writer (values of the layer curve itself, not final values) and the layer maker. `curvecapture` reads a card's curves at Save (wired into `animcapture.build_clip`); `store` writes and reads `curves.json.gz`; `curveapply` pastes them (dispatched from `animapply` when the options say `paste_as="curves"`); the window grows a **Paste as** row and a layer checklist.

**Tech Stack:** Maya 2027 Python 3 (`maya.cmds`, `maya.api.OpenMaya(Anim)`), PySide6 6.8.3, stdlib `unittest` under mayapy, `gzip`/`json`.

**Spec:** `docs/superpowers/specs/2026-10-28-pose-library-curves-and-layers-design.md` — read it first; every rule there is a requirement. It extends `2026-10-03-pose-library-animation-design.md` (read its «What an animation card is», «Apply — the options», «The paste modes», «Objects»).

## Global Constraints

- Work ONLY in the worktree `C:/!!!Work/MayaScripts-poselib-curves`, branch `feature/poselib-curves` (cut from `main` at b4a91cd). Never edit, stage or commit in `C:/!!!Work/MayaScripts` itself: other sessions commit and push `main` there, a push to `main` releases the plugin, and that tree holds their uncommitted edits. The branch is merged into `main` once the plan is done. Stage ONLY your task's files by name (`git add <file> ...`), never `git add -A` / `.`; never `git stash`, `reset` or `checkout -- <file>` on files that are not yours.
- Never edit the INSTALLED copy `C:/Users/MY PC/Documents/maya/scripts/SkeldarAnim` — it updates from a release.
- Tests from the repo root, PowerShell: `$env:QT_QPA_PLATFORM='offscreen'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_poselib_curvedata -v` (one module) or `... -m unittest discover -s tests -t .` (all). Never `2>&1` on mayapy; never system `python` (a hanging Store stub).
- A mayapy STANDALONE session (`maya.standalone.initialize`) runs with a scratch prefs folder set in the same PowerShell call: `$env:MAYA_APP_DIR = "$env:TEMP\skeldar_curves_<task>"`. Never connect to port 7001 (the animator's Maya).
- Purity (subprocess-pinned): `curvedata.py`, `store.py`, `look.py`, `animdata.py` import the stdlib only — `store` and `look` import NO sibling (so `store` checks the curves file's outer shape itself; `curvedata.check` runs in the press).
- Faking `maya.cmds` in a test: rebind the MODULE ATTRIBUTE (`keys.cmds = fake`) and put it back in `tearDown` / `addCleanup` (CLAUDE.md «Running tests»).
- Status lines and comments in English; the animator's quotes stay Russian. A docstring per function saying what and why, as the surrounding `maya_poselib` code does.
- Commit after each task with a message file: write it to `$env:TEMP\skeldar_msg.txt`, then `git commit -F $env:TEMP\skeldar_msg.txt`. Subject `feat(poselib): ...` / `test(poselib): ...` / `docs(poselib): ...`; last line `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

---

## File structure

| file | responsibility | task |
|---|---|---|
| `docs/superpowers/plans/probe_poselib_raw_layer_keys.py` (new) | mayapy: how a raw layer-curve value is keyed, measured | 1 |
| `SkeldarAnim/maya_poselib/curvedata.py` (new) | pure: layer records, the file check, the header block, the picks, layer pairing, Connect | 2 |
| `SkeldarAnim/maya_poselib/keys.py` | `layer_stack`, `layer_record`, `layer_plugs`, `existing_layers`, `write_raw`, `make_layer` | 3 |
| `SkeldarAnim/maya_poselib/store.py` | `CURVES_FILE`, `write/replace(curves=)`, `read_curves` | 4 |
| `SkeldarAnim/maya_poselib/animdata.py` | `Options.paste_as`, `Options.layers`, `PASTE_AS` | 5 |
| `SkeldarAnim/maya_poselib/curvecapture.py` (new) | Save: which nodes, each channel's curve per layer, the layers used | 6 |
| `SkeldarAnim/maya_poselib/animcapture.py` | `Clip`, `build_clip`, layered objects curves, the header's `curves` block | 6 |
| `SkeldarAnim/maya_poselib/curveapply.py` (new) | Paste: matching targets, channels, layers found or made, raw keys, Connect, the line | 7 |
| `SkeldarAnim/maya_poselib/animapply.py` | dispatch to `curveapply` (`apply`, `apply_onto`, `drop_floor`, `_press_objects`, `Blend.start`) | 7 |
| `SkeldarAnim/maya_poselib/look.py` | the details line of a card with curves | 8 |
| `SkeldarAnim/maya_poselib/window.py` | Paste as row, layer checklist, greying, options, Save / Update / paste with curves | 8 |
| `tests/test_poselib_curvedata.py`, `tests/test_poselib_curvecapture.py`, `tests/test_poselib_curveapply.py` (new); `tests/test_poselib_keys.py`, `test_poselib_store.py`, `test_poselib_animdata.py`, `test_poselib_animcapture.py`, `test_poselib_animapply.py`, `test_poselib_look.py`, `test_poselib_window.py` (extended) | unit tests | each |
| `docs/superpowers/plans/verify_poselib_curves.py` (new) | mayapy standalone, end to end | 9 |
| `CLAUDE.md`, the spec | the section, the measured facts | 10 |

## Shared data shapes (every task uses these names)

```python
# curvedata - a card LAYER record (header `curves.layers`, bottom to top, base first)
{"name": "AnimLayer1",            # leaf, no namespace; the base is always curvedata.BASE
 "base": False, "override": False, "weight": 1.0, "mute": False,
 "rotation": "component" | "quaternion", "scale": "multiply" | "additive"}

# a CURVE (the objects card's, from animcapture._copied) + infinity
{"keys": [[t, v, inType, outType, inAngle, inWeight, outAngle, outWeight], ...],
 "weighted": bool, "breakdown": [t, ...], "pre": "constant", "post": "cycle"}
{"static": v}

# anim.json gains
"curves": {"layers": [LAYER, ...], "nodes": n}

# curves.json.gz (character cards only)
{"version": 1, "nodes": [{"name": "FKWrist_R", "attrs": {"rotateZ": {"BaseAnimation": CURVE,
                                                                     "AnimLayer1": CURVE}}}]}

# an objects card's channel that sat in layers: today's sampled CURVE + its layers
{"keys": [...sampled...], "weighted": False, "breakdown": [], "layers": {"BaseAnimation": CURVE, ...}}

# animdata.Options gains (defaults keep today's paste)
paste_as="retarget" | "curves", layers=None | ("BaseAnimation", "AnimLayer1", ...)

# animcapture.Clip
Clip(header, frames, curves, note)     # curves: the curves.json.gz dict or None
```

---

### Task 1: Measure how a raw layer-curve value is keyed

`setKeyframe -value v -animLayer L` takes a FINAL value (Maya writes `v - below` onto an additive layer). Original curves need the layer curve's OWN value. This probe measures the road `keys.write_raw` will take and the spellings later tasks rely on. Nothing in the plugin changes.

**Files:**
- Create: `docs/superpowers/plans/probe_poselib_raw_layer_keys.py`

**Interfaces:**
- Produces: the measured facts Task 3 copies into `keys.py`'s docstring — (a) `setKeyframe <curve node> -time t -value v` writes `v` raw on a base, additive, override and quaternion layer curve, in UI units; (b) it replaces the value of a key standing at `t`; (c) fixed tangent angles and weights set after it hold; (d) the spelling `animLayer -q -attribute` answers plugs in; (e) the enums of `rotationAccumulationMode` / `scaleAccumulationMode`.

- [ ] **Step 1: Write the probe**

```python
"""Probe (2026-10-28): how a RAW layer-curve value is keyed - the road `keys.write_raw` takes.
mayapy STANDALONE, scratch MAYA_APP_DIR:

    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' probe_poselib_raw_layer_keys.py [out]

A locator keyed on the base (tx 0/10/20, ry 0/45/90 at 0/10/20), three layers above it: AddL
(additive, component), OverL (override) and QuatL (additive, quaternion). On each layer and the
base, for tx and ry: the plug added, the layer's curve made by one key through the plug when it
has none (`setKeyframe -animLayer`, value 999 - a value no raw key holds), then raw values written
on the CURVE NODE (`setKeyframe <curve> -time -value`) and read back off it (`keyframe -q -vc`).
Then: the composite with only AddL on is base + raw; fixed angles / weights set after the keys
hold; the plug spelling `animLayer -q -attribute` answers; the accumulation enums. Every gate
prints PASS/FAIL, the run ends SUMMARY x/y.
"""

import io
import sys

import maya.standalone
maya.standalone.initialize(name="python")

import maya.cmds as cmds  # noqa: E402

OUT = io.open(sys.argv[1], "w", encoding="utf-8") if len(sys.argv) > 1 else None
RESULTS = []


def say(*parts):
    line = " ".join(str(p) for p in parts)
    print(line)
    if OUT is not None:
        OUT.write(line + "\n")
        OUT.flush()


def gate(name, ok, value=""):
    RESULTS.append(bool(ok))
    say("%s %s %s" % ("PASS" if ok else "FAIL", name, value))


def curve_of(plug, layer):
    found = cmds.animLayer(layer, query=True, findCurveForPlug=plug)
    if isinstance(found, str):
        found = [found]
    return found[0] if found else None


def keys_of(curve):
    flat = cmds.keyframe(curve, query=True, timeChange=True, valueChange=True) or []
    return list(zip(flat[0::2], flat[1::2]))


def has(pairs, t, v):
    return any(abs(pt - t) < 1e-6 and abs(pv - v) < 1e-6 for pt, pv in pairs)


try:
    cmds.currentUnit(time="ntsc", angle="degree", linear="centimeter")
    loc = cmds.spaceLocator(name="probe")[0]
    for t, tx, ry in ((0, 0.0, 0.0), (10, 10.0, 45.0), (20, 20.0, 90.0)):
        cmds.setKeyframe(loc, attribute="translateX", time=t, value=tx)
        cmds.setKeyframe(loc, attribute="rotateY", time=t, value=ry)
    add = cmds.animLayer("AddL")
    over = cmds.animLayer("OverL", override=True)
    quat = cmds.animLayer("QuatL")
    cmds.setAttr(quat + ".rotationAccumulationMode", 1)
    base = cmds.animLayer(query=True, root=True)
    raw = {"translateX": [(0.0, 1.5), (5.0, -2.0), (20.0, 3.25)],
           "rotateY": [(0.0, 12.5), (5.0, -30.0), (20.0, 7.0)]}
    for layer in (add, over, quat, base):
        for attr, wanted in raw.items():
            plug = loc + "." + attr
            if layer != base:
                cmds.animLayer(layer, edit=True, attribute=plug)
            curve = curve_of(plug, layer)
            if curve is None:
                cmds.setKeyframe(plug, time=wanted[0][0], value=999.0, animLayer=layer)
                curve = curve_of(plug, layer)
            gate("%s %s: a curve" % (layer, attr), curve is not None, curve)
            for t, v in wanted:
                cmds.setKeyframe(curve, time=t, value=v)
            pairs = keys_of(curve)
            gate("%s %s: every raw value back off the curve" % (layer, attr),
                 all(has(pairs, t, v) for t, v in wanted), pairs)
            gate("%s %s: the 999 creating key overwritten" % (layer, attr),
                 not any(abs(pv - 999.0) < 1e-6 for _pt, pv in pairs), pairs)
    # the composite: AddL alone on top of the base is base + raw (tx at 5: base 5 + raw -2)
    for layer in (over, quat):
        cmds.animLayer(layer, edit=True, mute=True)
    cmds.currentTime(5, update=True)
    shown = cmds.getAttr(loc + ".translateX")
    base_at = cmds.keyframe(curve_of(loc + ".translateX", base), query=True, eval=True, time=(5, 5))[0]
    gate("AddL tx at 5 shows the base under it plus the raw key", abs(shown - (base_at - 2.0)) < 1e-6,
         (shown, base_at))
    # tangents after the keys
    tx_add = curve_of(loc + ".translateX", add)
    cmds.keyTangent(tx_add, edit=True, weightedTangents=True)
    cmds.keyTangent(tx_add, edit=True, time=(5, 5), inAngle=20.0, outAngle=-10.0, inWeight=2.0,
                    outWeight=3.0, lock=False, weightLock=False)
    angles = cmds.keyTangent(tx_add, query=True, time=(5, 5), inAngle=True, outAngle=True)
    weights = cmds.keyTangent(tx_add, query=True, time=(5, 5), inWeight=True, outWeight=True)
    gate("fixed angles hold on a layer curve", abs(angles[0] - 20) < 1e-4 and abs(angles[1] + 10) < 1e-4,
         angles)
    gate("weights hold on a layer curve", abs(weights[0] - 2) < 1e-4 and abs(weights[1] - 3) < 1e-4,
         weights)
    say("animLayer -q -attribute on AddL:", cmds.animLayer(add, query=True, attribute=True))
    say("rotationAccumulationMode:", cmds.attributeQuery("rotationAccumulationMode", node=add,
                                                         listEnum=True))
    say("scaleAccumulationMode:", cmds.attributeQuery("scaleAccumulationMode", node=add, listEnum=True))
    say("scaleAccumulationMode of a new layer:", cmds.getAttr(add + ".scaleAccumulationMode"))
except Exception:                                            # noqa: BLE001
    import traceback
    say(traceback.format_exc())
    RESULTS.append(False)
say("SUMMARY %d/%d" % (sum(RESULTS), len(RESULTS)))
maya.standalone.uninitialize()
```

- [ ] **Step 2: Run it**

```powershell
$env:MAYA_APP_DIR = "$env:TEMP\skeldar_curves_probe"; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs\superpowers\plans\probe_poselib_raw_layer_keys.py "$env:TEMP\probe_raw.txt"
```

Expected: `SUMMARY 27/27` (8 curves × 3 gates, the composite, the angles, the weights; none FAIL). Write down the three printed lines (plug spelling, the two enums).

- [ ] **Step 3: If any «raw value back» gate FAILS** — the curve-node road is out; Task 3 uses its `_raw_key` FALLBACK (`MFnAnimCurve`, given in Task 3 Step 3). Change the probe's inner loop to call that fallback and re-run until it passes. If the plug spelling is NOT `node.longAttr` with a node name `cmds.ls(long=True)` can resolve, adjust Task 3's `layer_plugs` (it already normalises both halves).

- [ ] **Step 4: Commit**

```powershell
git add docs/superpowers/plans/probe_poselib_raw_layer_keys.py
git commit -F $env:TEMP\skeldar_msg.txt   # "test(poselib): probe - how a raw layer-curve value is keyed"
```

---

### Task 2: `curvedata` — the pure rules

**Files:**
- Create: `SkeldarAnim/maya_poselib/curvedata.py`
- Test: `tests/test_poselib_curvedata.py`

**Interfaces:**
- Produces (exact names every later task uses):
  - `VERSION = 1`, `BASE = "BaseAnimation"`, `WHOLE = "whole"`, `ROTATION = {0: "component", 1: "quaternion"}`, `SCALE = {0: "additive", 1: "multiply"}`, `BROKEN = "%s: not a card's curves"`
  - `layer_record(name, base=False, override=False, weight=1.0, mute=False, rotation="component", scale="multiply") -> dict`
  - `check(data, names, where="curves") -> data` (ValueError when broken)
  - `summary(records, count) -> {"layers": [...], "nodes": count}`
  - `records(header) -> [dict]`, `has_curves(header) -> bool`, `layer_names(header) -> [str]`
  - `has_keys(per_layer_dicts) -> bool`
  - `chosen(card_names, wanted) -> [str]`
  - `keeps_control(named, members, whole) -> bool`
  - `pair_nodes(card_names, target_paths, leaf) -> ({card name: path}, [missing names])`
  - `layer_target(record, existing) -> (kind, name)` with kind `"base" | "layer" | "make" | "refused"`
  - `per_layer(curve) -> {layer name: CURVE}`
  - `connect_ok(names) -> bool`, `connect_offset(before, now, weight) -> float | None`

- [ ] **Step 1: Write the failing tests**

```python
"""maya_poselib.curvedata - the pure rules of an animation card's ORIGINAL curves (spec
2026-10-28-pose-library-curves-and-layers-design.md): the layer records, the curves file's check,
the header's `curves` block, the layers a paste picks, which controls a card keeps, the pairing of
the card's nodes and layers on the target, Connect's one-layer rule. Stdlib data only."""

import unittest

from maya_poselib import curvedata as cd

BASE = cd.layer_record(cd.BASE, base=True)
ADD = cd.layer_record("tab1:AnimLayer1", weight=0.5)
OVER = cd.layer_record("Fix", override=True)
KEYED = {"keys": [[0.0, 1.0, "auto", "auto", 0.0, 1.0, 0.0, 1.0]], "weighted": False,
         "breakdown": []}


def nodes(*names):
    return [{"name": name, "attrs": {"rotateX": {cd.BASE: KEYED, "AnimLayer1": {"static": 2.0}}}}
            for name in names]


class LayerRecord(unittest.TestCase):

    def test_a_layer_keeps_its_leaf_name_and_settings(self):
        self.assertEqual(ADD, {"name": "AnimLayer1", "base": False, "override": False,
                               "weight": 0.5, "mute": False, "rotation": "component",
                               "scale": "multiply"})

    def test_the_base_is_always_named_base_animation(self):
        self.assertEqual(cd.layer_record("skeldarTabsLayerRoot", base=True)["name"], cd.BASE)
        self.assertTrue(BASE["base"])


class Check(unittest.TestCase):

    def test_a_whole_file_passes_and_comes_back(self):
        data = {"version": 1, "nodes": nodes("FKWrist_R")}
        self.assertIs(cd.check(data, [cd.BASE, "AnimLayer1"]), data)

    def test_a_layer_the_header_does_not_name_is_broken(self):
        with self.assertRaises(ValueError):
            cd.check({"version": 1, "nodes": nodes("a")}, [cd.BASE])

    def test_wrong_shapes_are_broken(self):
        nan = float("nan")
        for bad in (None, [], {"nodes": "x"}, {"nodes": [{"name": 1, "attrs": {}}]},
                    {"nodes": [{"name": "a", "attrs": {"rx": []}}]},
                    {"nodes": [{"name": "a", "attrs": {"rx": {}}}]},
                    {"nodes": [{"name": "a", "attrs": {"rx": {cd.BASE: {"keys": [[0.0, nan]]}}}}]},
                    {"nodes": [{"name": "a", "attrs": {"rx": {cd.BASE: {"static": "x"}}}}]},
                    {"nodes": [{"name": "a", "attrs": {"rx": {cd.BASE: {"static": True}}}}]}):
            with self.assertRaises(ValueError, msg=repr(bad)):
                cd.check(bad, [cd.BASE])


class Header(unittest.TestCase):

    def test_summary_and_reading_it_back(self):
        block = cd.summary([BASE, ADD], 3)
        self.assertEqual(block, {"layers": [BASE, ADD], "nodes": 3})
        header = {"curves": block}
        self.assertTrue(cd.has_curves(header))
        self.assertEqual(cd.layer_names(header), [cd.BASE, "AnimLayer1"])
        self.assertEqual(cd.records(header), [BASE, ADD])

    def test_no_block_or_a_broken_one_is_no_curves(self):
        for header in (None, {}, {"curves": None}, {"curves": {"layers": []}},
                       {"curves": {"layers": "x"}}, {"curves": {"layers": [{"name": 1}]}},
                       {"curves": {"layers": [ADD]}}):          # the first record is no base
            self.assertFalse(cd.has_curves(header), header)
            self.assertEqual(cd.layer_names(header), [])

    def test_has_keys_wants_one_keyed_curve(self):
        self.assertFalse(cd.has_keys([{cd.BASE: {"static": 1.0}}]))
        self.assertFalse(cd.has_keys([{cd.BASE: {"keys": []}}]))
        self.assertTrue(cd.has_keys([{cd.BASE: {"static": 1.0}}, {"AnimLayer1": KEYED}]))


class Chosen(unittest.TestCase):

    def test_none_is_every_layer_in_the_cards_order(self):
        self.assertEqual(cd.chosen([cd.BASE, "A", "B"], None), [cd.BASE, "A", "B"])

    def test_a_pick_keeps_the_cards_order_and_drops_unknown_names(self):
        self.assertEqual(cd.chosen([cd.BASE, "A", "B"], ["B", "Z", cd.BASE]), [cd.BASE, "B"])

    def test_connect_needs_exactly_one_layer(self):
        self.assertTrue(cd.connect_ok(["A"]))
        self.assertFalse(cd.connect_ok([cd.BASE, "A"]))
        self.assertFalse(cd.connect_ok([]))


class KeepsControl(unittest.TestCase):

    def test_a_control_whose_bones_meet_the_members(self):
        self.assertTrue(cd.keeps_control(["hand_l"], ["hand_l", "lowerarm_l"], False))
        self.assertFalse(cd.keeps_control(["hand_r"], ["hand_l"], False))
        self.assertFalse(cd.keeps_control([], ["hand_l"], True))

    def test_main_only_with_a_whole_body_card(self):
        self.assertTrue(cd.keeps_control(cd.WHOLE, ["pelvis"], True))
        self.assertFalse(cd.keeps_control(cd.WHOLE, ["hand_l"], False))


class PairNodes(unittest.TestCase):

    def test_by_leaf_namespace_and_path_ignored(self):
        def leaf(path):
            return path.split("|")[-1].split(":")[-1]
        paired, missing = cd.pair_nodes(
            ["FKWrist_R", "Main", "FKGone_L"],
            ["|Manny_Rig1:grp|Manny_Rig1:FKWrist_R", "|Manny_Rig1:Main"], leaf)
        self.assertEqual(paired, {"FKWrist_R": "|Manny_Rig1:grp|Manny_Rig1:FKWrist_R",
                                  "Main": "|Manny_Rig1:Main"})
        self.assertEqual(missing, ["FKGone_L"])


class LayerTarget(unittest.TestCase):

    EXISTING = [
        {"name": "tab1:AnimLayer1", "override": False, "rotation": "component", "locked": False},
        {"name": "Fix", "override": False, "rotation": "component", "locked": False},
        {"name": "Held", "override": False, "rotation": "component", "locked": True}]

    def test_the_base_goes_to_the_base(self):
        self.assertEqual(cd.layer_target(BASE, self.EXISTING), ("base", None))

    def test_a_namesake_of_the_same_mode_takes_it(self):
        self.assertEqual(cd.layer_target(ADD, self.EXISTING), ("layer", "tab1:AnimLayer1"))

    def test_a_namesake_of_another_mode_makes_a_new_one(self):
        self.assertEqual(cd.layer_target(OVER, self.EXISTING), ("make", None))

    def test_another_rotation_accumulation_makes_a_new_one(self):
        record = cd.layer_record("Fix", rotation="quaternion")
        self.assertEqual(cd.layer_target(record, self.EXISTING), ("make", None))

    def test_a_locked_namesake_is_refused(self):
        self.assertEqual(cd.layer_target(cd.layer_record("Held"), self.EXISTING),
                         ("refused", "Held"))

    def test_no_namesake_makes_one(self):
        self.assertEqual(cd.layer_target(cd.layer_record("New"), self.EXISTING), ("make", None))


class PerLayer(unittest.TestCase):

    def test_a_plain_objects_curve_is_the_bases(self):
        self.assertEqual(cd.per_layer(KEYED), {cd.BASE: KEYED})

    def test_a_layered_one_answers_its_layers(self):
        curve = dict(KEYED, layers={cd.BASE: KEYED, "A": {"static": 1.0}})
        self.assertEqual(cd.per_layer(curve), {cd.BASE: KEYED, "A": {"static": 1.0}})


class ConnectOffset(unittest.TestCase):

    def test_the_difference_over_the_weight(self):
        self.assertAlmostEqual(cd.connect_offset(10.0, 4.0, 0.5), 12.0)
        self.assertAlmostEqual(cd.connect_offset(10.0, 4.0, 1.0), 6.0)

    def test_weight_zero_moves_nothing(self):
        self.assertIsNone(cd.connect_offset(10.0, 4.0, 0.0))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run them to see them fail**

Run: `$env:QT_QPA_PLATFORM='offscreen'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_poselib_curvedata -v`
Expected: ERROR `ModuleNotFoundError: No module named 'maya_poselib.curvedata'`.

- [ ] **Step 3: Write the module**

```python
"""maya_poselib.curvedata - the pure rules of an animation card's ORIGINAL curves (2026-10-28).
Stdlib only.

The animator: «А мы можем так сделать что бы наша библеотека поз потдерживала сохранения по слоям
и сохранения ключей?». A card keeps, beside its bones' frames, the source's own curves layer by
layer: the LAYERS in its header (`anim.json`'s `curves`: `summary`), the controls' curves in
`curves.json.gz` (`check`), an objects card's layered channels in the header beside their sampled
keys (`per_layer`). `curvecapture` reads them, `curveapply` pastes them. This module holds what
needs no scene: the records, the check, the picks, which controls a card keeps, where each card
layer goes on the target, Connect's one-layer rule.

A layer is named by its LEAF (no namespace: a scene tab puts its layers in one); the base is
always `BASE`, whatever the scene's root is called (a scene tabs session's root is
`skeldarTabsLayerRoot`).

Spec: docs/superpowers/specs/2026-10-28-pose-library-curves-and-layers-design.md
"""

import math

VERSION = 1
BASE = "BaseAnimation"
WHOLE = "whole"                        # `scene._WHOLE`: a control that names the whole body
#  an animLayer's accumulation enums (measured, task 1's probe)
ROTATION = {0: "component", 1: "quaternion"}
SCALE = {0: "additive", 1: "multiply"}

BROKEN = "%s: not a card's curves"


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _leaf(name):
    return (name or "").split("|")[-1].split(":")[-1]


def layer_record(name, base=False, override=False, weight=1.0, mute=False,
                 rotation="component", scale="multiply"):
    """One card layer as the header keeps it: its leaf name, mode, weight, own mute and
    accumulation modes. The base is `BASE` with the base's settings whatever it is called."""
    if base:
        return {"name": BASE, "base": True, "override": False, "weight": 1.0, "mute": False,
                "rotation": "component", "scale": "multiply"}
    return {"name": _leaf(name), "base": False, "override": bool(override),
            "weight": float(weight), "mute": bool(mute), "rotation": rotation, "scale": scale}


def _curve_ok(curve):
    """A CURVE a paste can key: `{"static": number}` or `{"keys": [[t, v, ...]...]}`, every time
    and value a finite number (JSON's NaN never reaches a key)."""
    if not isinstance(curve, dict):
        return False
    if "static" in curve:
        return _finite(curve["static"])
    stored = curve.get("keys")
    return isinstance(stored, list) and all(
        isinstance(key, list) and len(key) >= 2 and _finite(key[0]) and _finite(key[1])
        for key in stored)


def check(data, names, where="curves"):
    """`data` (a `curves.json.gz` read back) when whole, else ValueError(BROKEN): a dict whose
    `nodes` is a list of {name: str, attrs: {attr: {layer: CURVE}}}, every layer one of `names`
    (the header's) and every CURVE keyable - a broken card is refused before a press writes
    anything, never half pasted."""
    names = set(names or ())
    if not (isinstance(data, dict) and isinstance(data.get("nodes"), list)):
        raise ValueError(BROKEN % where)
    for node in data["nodes"]:
        if not (isinstance(node, dict) and isinstance(node.get("name"), str)
                and isinstance(node.get("attrs"), dict)):
            raise ValueError(BROKEN % where)
        for per in node["attrs"].values():
            if not isinstance(per, dict) or not per:
                raise ValueError(BROKEN % where)
            for name, curve in per.items():
                if name not in names or not _curve_ok(curve):
                    raise ValueError(BROKEN % where)
    return data


def summary(records, count):
    """The header's `curves` block: the layer `records` bottom to top (the base first) and how
    many nodes keep curves."""
    return {"layers": [dict(record) for record in records], "nodes": int(count)}


def records(header):
    """The header's layer records, bottom to top - [] when it holds no `curves` block or a broken
    one (a list of dicts with str names, the first the base)."""
    block = (header or {}).get("curves")
    if not isinstance(block, dict):
        return []
    layers = block.get("layers")
    if not (isinstance(layers, list) and layers
            and all(isinstance(r, dict) and isinstance(r.get("name"), str) for r in layers)
            and layers[0].get("base")):
        return []
    return [dict(record) for record in layers]


def has_curves(header):
    """Does the card hold original curves a paste can take?"""
    return bool(records(header))


def layer_names(header):
    """The header's layer names, bottom to top."""
    return [record["name"] for record in records(header)]


def has_keys(per_layer_dicts):
    """Does any {layer: CURVE} of `per_layer_dicts` hold a curve with keys? Statics alone say
    nothing the bones' frames do not."""
    return any(isinstance(curve, dict) and curve.get("keys")
               for per in per_layer_dicts for curve in per.values())


def chosen(card_names, wanted):
    """The card's layers a paste writes, in the card's order: every one when `wanted` is None,
    else those `wanted` names (a name the card does not hold dropped)."""
    if wanted is None:
        return list(card_names)
    wanted = set(wanted)
    return [name for name in card_names if name in wanted]


def keeps_control(named, members, whole):
    """Does a card keep a control's curves? `named` is what the control names (`scene.
    _control_bones`: its bones, or `WHOLE`), `members` the card's member bones, `whole` - the
    card is the whole body. A control naming the whole body (Main) only with a whole-body card."""
    if named == WHOLE:
        return bool(whole)
    return bool(set(named or ()) & set(members or ()))


def pair_nodes(card_names, target_paths, leaf):
    """({card name: target path}, [card names the target lacks]): the card's nodes paired with
    the target's by `leaf` name (namespace and path ignored); the first target of a leaf wins."""
    by_leaf = {}
    for path in target_paths:
        by_leaf.setdefault(leaf(path), path)
    paired, missing = {}, []
    for name in card_names:
        if name in by_leaf:
            paired[name] = by_leaf[name]
        else:
            missing.append(name)
    return paired, missing


def layer_target(record, existing):
    """Where a card layer's keys go: ("base", None) for the card's base; ("layer", name) for the
    target's first layer of the same leaf name, mode and rotation accumulation; ("refused", name)
    when that layer is locked; ("make", None) when there is none - a namesake of another mode
    included: raw values mean nothing on a layer that sums them differently. `existing` is
    `keys.existing_layers()`: [{name, override, rotation, locked}] bottom to top."""
    if record.get("base"):
        return "base", None
    leaf = _leaf(record["name"])
    for layer in existing:
        if _leaf(layer["name"]) != leaf:
            continue
        if bool(layer.get("override")) != bool(record.get("override")):
            continue
        if layer.get("rotation", "component") != record.get("rotation", "component"):
            continue
        if layer.get("locked"):
            return "refused", layer["name"]
        return "layer", layer["name"]
    return "make", None


def per_layer(curve):
    """{layer: CURVE} of an objects card's channel: its `layers` when it sat in layers, else the
    channel's own curve as the base's."""
    if isinstance(curve, dict) and isinstance(curve.get("layers"), dict):
        return dict(curve["layers"])
    return {BASE: curve}


def connect_ok(names):
    """Connect works when the paste writes ONE layer: with two, which of them takes the offset
    is no rule but a guess."""
    return len(names) == 1


def connect_offset(before, now, weight):
    """How far Connect moves one channel's pasted keys on its layer: what it showed before the
    press minus what it shows now, over the layer's weight (an additive or override layer at
    weight w moves the shown value w times its own move); None at weight 0 - nothing moves it."""
    if abs(float(weight)) < 1e-9:
        return None
    return (float(before) - float(now)) / float(weight)
```

- [ ] **Step 4: Run the tests**

Run: `... -m unittest tests.test_poselib_curvedata -v`
Expected: every test OK.

- [ ] **Step 5: Commit**

```powershell
git add SkeldarAnim/maya_poselib/curvedata.py tests/test_poselib_curvedata.py
git commit -F $env:TEMP\skeldar_msg.txt   # "feat(poselib): curvedata - the pure rules of a card's original curves"
```

---

### Task 3: `keys` — the layer stack, raw keys, new layers

**Files:**
- Modify: `SkeldarAnim/maya_poselib/keys.py` (imports; new functions after `put_curve_state`; the module docstring's «Layer curves» paragraph)
- Test: `tests/test_poselib_keys.py` (new classes at the end)

**Interfaces:**
- Consumes: `curvedata.layer_record`, `curvedata.ROTATION`, `curvedata.SCALE`, `curvedata.BASE` (Task 2); Task 1's measured facts.
- Produces:
  - `layer_stack() -> [str]` — the scene's layers bottom to top, the root first, tab roots out; `[]` without layers
  - `layer_record(name, base=False) -> dict`
  - `layer_plugs(name) -> set[str]` — `"<long node path>.<long attr>"`
  - `existing_layers() -> [{"name", "override", "rotation", "locked"}]` — non-base, bottom to top
  - `write_raw(plug, layer, keys_list, weighted=False, pre=None, post=None) -> Written`
  - `make_layer(record) -> str`
  - `RAW_NO_CURVE = "%s: no curve on %s for its keys"`

- [ ] **Step 1: Write the failing tests** (append to `tests/test_poselib_keys.py`; `CurveCmds`, `LayerSceneCmds`, `Restoring`, `ADD` already live there)

```python
from maya_poselib import curvedata


class StackCmds(LayerSceneCmds):
    """`LayerSceneCmds` plus each layer's plugs (`animLayer -q -attribute`), their long names and
    the scale accumulation."""

    def __init__(self, tree, plugs=None, scale=None, **kw):
        LayerSceneCmds.__init__(self, tree, **kw)
        self.plugs = dict(plugs or {})
        self.scale = dict(scale or {})

    def animLayer(self, name=None, **kw):
        if kw.get("query") and kw.get("attribute"):
            return list(self.plugs.get(name, [])) or None
        return LayerSceneCmds.animLayer(self, name, **kw)

    def getAttr(self, plug, **kw):
        node, attr = plug.split(".")
        if attr == "scaleAccumulationMode":
            return self.scale.get(node, 1)
        return LayerSceneCmds.getAttr(self, plug, **kw)

    def ls(self, node, long=False):
        return ["|grp|" + node.split("|")[-1]]

    def attributeQuery(self, attr, node=None, longName=False):
        return {"tx": "translateX", "rx": "rotateX"}.get(attr, attr)


class LayerStack(Restoring):

    TREE = {"BaseAnimation": ["A", "B"]}

    def test_no_layers_is_an_empty_stack(self):
        keys.cmds = StackCmds({}, root=None)
        self.assertEqual(keys.layer_stack(), [])

    def test_bottom_to_top_the_root_first(self):
        keys.cmds = StackCmds(self.TREE)
        self.assertEqual(keys.layer_stack(), ["BaseAnimation", "A", "B"])

    def test_a_layers_record(self):
        keys.cmds = StackCmds(self.TREE, override=["B"], quaternion=["A"], muted=["B"],
                              weights={"A": 0.25}, scale={"A": 0})
        self.assertEqual(keys.layer_record("A"), curvedata.layer_record(
            "A", weight=0.25, rotation="quaternion", scale="additive"))
        self.assertEqual(keys.layer_record("B"), curvedata.layer_record(
            "B", override=True, mute=True))
        self.assertEqual(keys.layer_record("BaseAnimation", base=True)["name"], curvedata.BASE)

    def test_a_layers_plugs_in_long_spellings(self):
        keys.cmds = StackCmds(self.TREE, plugs={"A": ["ctrl.tx", "ctrl.rx"]})
        self.assertEqual(keys.layer_plugs("A"), {"|grp|ctrl.translateX", "|grp|ctrl.rotateX"})
        self.assertEqual(keys.layer_plugs("B"), set())

    def test_existing_layers_leave_the_base_out(self):
        keys.cmds = StackCmds(self.TREE, override=["B"], locked=["A"])
        self.assertEqual(keys.existing_layers(), [
            {"name": "A", "override": False, "rotation": "component", "locked": True},
            {"name": "B", "override": True, "rotation": "component", "locked": False}])


class RawCmds(CurveCmds):
    """`CurveCmds` plus the curve-node keys `write_raw` writes: `setKeyframe` on a CURVE (a name
    in `types`) records a raw key; on a plug it makes that plug's curve on the layer (`made`
    {(layer, plug): curve}) as Maya's first key does."""

    def __init__(self, made=None, **kw):
        CurveCmds.__init__(self, **kw)
        self.made = dict(made or {})

    def setKeyframe(self, target, **kw):
        if target in self.types:
            self.log.append(("raw", target, kw.get("time"), kw.get("value")))
            return 1
        self.log.append(("key", target, kw.get("time"), kw.get("value"), kw.get("animLayer")))
        made = self.made.pop((kw.get("animLayer"), target), None)
        if made:
            self.found[(kw.get("animLayer"), target)] = [made]
        return 1


class WriteRaw(Restoring):

    KEYS = [[0.0, 1.5, "auto", "auto", 0.0, 1.0, 0.0, 1.0],
            [5.0, -2.0, "fixed", "fixed", 20.0, 2.0, -10.0, 3.0]]

    def test_an_existing_layer_curve_takes_the_raw_values_and_every_tangent(self):
        fake = RawCmds(found={("AddL", "a.tx"): ["cx"]}, plain={"a.tx": ["blend"]},
                       types={"cx": "animCurveTL", "blend": "animBlendNodeAdditiveDL"})
        keys.cmds = fake
        written = keys.write_raw("a.tx", "AddL", self.KEYS, weighted=True, pre="constant",
                                 post="cycle")
        self.assertEqual((written.count, written.notes, written.plugs), (2, [], ["a.tx"]))
        self.assertEqual(fake.calls("add"), [("add", "AddL", "a.tx")])
        self.assertEqual(fake.calls("raw"), [("raw", "cx", 0.0, 1.5), ("raw", "cx", 5.0, -2.0)])
        tangents = fake.calls("tangent")
        self.assertEqual(tangents[0][2], {"edit": True, "weightedTangents": True})
        fixed = tangents[1][2]
        self.assertEqual((fixed["inAngle"], fixed["outAngle"], fixed["inWeight"],
                          fixed["outWeight"]), (20.0, -10.0, 2.0, 3.0))
        self.assertEqual(fake.calls("set"), [("set", "cx.postInfinity", 3)])

    def test_a_missing_layer_curve_is_made_by_one_key_through_the_plug_then_overwritten(self):
        fake = RawCmds(made={("AddL", "a.tx"): "cx"}, plain={"a.tx": ["blend"]},
                       types={"cx": "animCurveTL", "blend": "animBlendNodeAdditiveDL"})
        keys.cmds = fake
        written = keys.write_raw("a.tx", "AddL", self.KEYS)
        self.assertEqual(written.count, 2)
        self.assertEqual(fake.calls("key"), [("key", "a.tx", 0.0, 1.5, "AddL")])
        self.assertEqual([entry[2:] for entry in fake.calls("raw")], [(0.0, 1.5), (5.0, -2.0)])

    def test_no_curve_after_the_creating_key_is_said(self):
        fake = RawCmds(plain={"a.tx": ["blend"]}, types={"blend": "animBlendNodeAdditiveDL"})
        keys.cmds = fake
        written = keys.write_raw("a.tx", "AddL", self.KEYS)
        self.assertEqual((written.count, written.plugs), (0, []))
        self.assertEqual(written.notes, [keys.RAW_NO_CURVE % ("a.tx", "AddL")])

    def test_without_layers_the_plugs_own_curve_takes_them(self):
        fake = RawCmds(plain={"a.tx": ["cx"]}, types={"cx": "animCurveTL"})
        keys.cmds = fake
        written = keys.write_raw("a.tx", None, self.KEYS)
        self.assertEqual(written.count, 2)
        self.assertEqual(fake.calls("add"), [])
        self.assertEqual(len(fake.calls("raw")), 2)

    def test_a_locked_plug_takes_nothing(self):
        fake = RawCmds(plain={"a.tx": ["cx"]}, types={"cx": "animCurveTL"}, locked=["a.tx"])
        keys.cmds = fake
        written = keys.write_raw("a.tx", None, self.KEYS)
        self.assertEqual((written.count, fake.calls("raw")), (0, []))
        self.assertIn("locked", written.notes[0])


class MakeCmds(object):
    """`animLayer` creation and edits, `setAttr`, logged."""

    def __init__(self):
        self.log = []

    def animLayer(self, name=None, **kw):
        if kw.get("edit"):
            self.log.append(("edit", name, kw))
            return None
        self.log.append(("make", name, kw))
        return name + "1"                             # Maya made the name free

    def setAttr(self, plug, value):
        self.log.append(("set", plug, value))


class MakeLayer(Restoring):

    def test_a_layer_made_with_the_cards_settings_under_its_free_name(self):
        fake = MakeCmds()
        keys.cmds = fake
        record = curvedata.layer_record("Fix", override=True, weight=0.5, mute=True,
                                        rotation="quaternion", scale="additive")
        self.assertEqual(keys.make_layer(record), "Fix1")
        self.assertEqual(fake.log[0], ("make", "Fix", {"override": True}))
        self.assertIn(("set", "Fix1.rotationAccumulationMode", 1), fake.log)
        self.assertIn(("set", "Fix1.scaleAccumulationMode", 0), fake.log)
        self.assertIn(("edit", "Fix1", {"edit": True, "weight": 0.5}), fake.log)
        self.assertIn(("edit", "Fix1", {"edit": True, "mute": True}), fake.log)
```

- [ ] **Step 2: Run them to see them fail**

Run: `... -m unittest tests.test_poselib_keys -v`
Expected: the new classes ERROR with `AttributeError: module 'maya_poselib.keys' has no attribute 'layer_stack'` (and the others); every older test still OK.

- [ ] **Step 3: Write the code** — in `keys.py` add `from maya_poselib import curvedata` under `import maya.cmds as cmds`, the constant beside `NO_CURVE`:

```python
RAW_NO_CURVE = "%s: no curve on %s for its keys"
```

and after `put_curve_state` a new section:

```python
# ------------------------------------------------------------------ original curves (2026-10-28)

def layer_stack():
    """[name] of the scene's animation layers bottom to top, the root first (`_walk`'s depth-first
    order: the stack position) - a scene tab's root left out (`_tab_root`: it holds no curves of its
    own); [] in a scene without layers."""
    root = cmds.animLayer(query=True, root=True)
    if not root:
        return []
    return [name for name in _walk(root) if not _tab_root(name, root)]


def layer_record(name, base=False):
    """`curvedata.layer_record` of the scene's layer `name` - its mode, weight, OWN mute (a
    parent's is no setting of this layer) and accumulation enums (`curvedata.ROTATION` /
    `SCALE`); `base` - the root, the card's `curvedata.BASE` whatever it is called."""
    if base:
        return curvedata.layer_record(curvedata.BASE, base=True)
    try:
        rotation = int(cmds.getAttr(name + ".rotationAccumulationMode"))
        scale = int(cmds.getAttr(name + ".scaleAccumulationMode"))
    except (RuntimeError, ValueError, TypeError):
        rotation, scale = 0, 1
    return curvedata.layer_record(
        name, override=bool(cmds.animLayer(name, query=True, override=True)),
        weight=_weight(name), mute=bool(cmds.animLayer(name, query=True, mute=True)),
        rotation=curvedata.ROTATION.get(rotation, "component"),
        scale=curvedata.SCALE.get(scale, "multiply"))


def layer_plugs(name):
    """{plug} the layer `name` holds (`animLayer -q -attribute`: one query a layer, where asking
    every plug of a rig on every layer cost a query each), spelled as the pose library spells a
    plug - the node's long path, the attribute's long name (task 1 printed Maya's own spelling:
    the shortest unique node name). Empty when it holds none or cannot be read."""
    try:
        listed = cmds.animLayer(name, query=True, attribute=True) or []
    except (RuntimeError, TypeError, ValueError):
        return set()
    out = set()
    for plug in listed:
        node, _dot, attr = plug.rpartition(".")
        try:
            found = cmds.ls(node, long=True) or []
            if found:
                out.add(found[0] + "." + cmds.attributeQuery(attr, node=found[0], longName=True))
        except (RuntimeError, TypeError, ValueError):
            continue
    return out


def existing_layers():
    """[{name, override, rotation, locked}] of the scene's layers above the base, bottom to top -
    what `curvedata.layer_target` pairs a card's layers with."""
    out = []
    for name in layer_stack()[1:]:
        out.append({"name": name,
                    "override": bool(cmds.animLayer(name, query=True, override=True)),
                    "rotation": "quaternion" if _quaternion(name) else "component",
                    "locked": bool(cmds.animLayer(name, query=True, lock=True))})
    return out


def _raw_key(curve, time, value):
    """One RAW key on the curve node `curve` - the curve's own value, in UI units (measured, task
    1: `setKeyframe <curve> -time t -value v` writes `v` on a base, additive, override and
    quaternion layer curve alike, and replaces the value of a key standing at `t`)."""
    return cmds.setKeyframe(curve, time=time, value=value)


def write_raw(plug, layer, keys_list, weighted=False, pre=None, post=None):
    """A stored LAYER CURVE onto `plug`'s curve on `layer` (a layer's name - the base when it is
    the scene's root, as `curve_for` takes it - or None: no layers, the plug's own curve):
    `Written` as `write_keys`' (keys made, notes, `.plugs` [plug] when any landed).

    The values are the curve's OWN - an additive layer's offset, an override layer's value - so
    they are written on the curve NODE (`_raw_key`), never through the plug with `value=`, which
    takes a final value (`_key`). That is what lets every tangent travel: the weighting first,
    each fixed tangent's angles and weights, then the types (`_tangent_edits(..., tangents=True)`
    - the order measured for `write_keys`), then `pre` / `post` infinity (`setInfinity`'s
    spelling, `_INFINITY_VALUE`). A plug not yet in a non-base layer is added first; a curve that
    does not exist yet is made by ONE key through the plug (`_key`, the layer's own road), whose
    value the raw keys then overwrite. A plug `writable` refuses takes nothing and is named."""
    ok, reason = writable(plug)
    if not ok:
        return Written(0, [_note(reason, [plug])])
    if not keys_list:
        return Written(0, [])
    name, base = _layer_parts(layer)
    if name is not None and not base:
        try:
            cmds.animLayer(name, edit=True, attribute=plug)
        except RuntimeError as error:
            return Written(0, [_note(_why(error), [plug])])
    curve = curve_for(plug, layer)
    if curve is None:
        try:
            _key(plug, keys_list[0][1], keys_list[0][0], name)
        except RuntimeError as error:
            return Written(0, [_note(_why(error), [plug])])
        curve = curve_for(plug, layer)
    if curve is None:
        return Written(0, [RAW_NO_CURVE % (plug, name or "the plug")])
    count, landed, refused = 0, [], {}
    for key in keys_list:
        try:
            made = _raw_key(curve, key[0], key[1]) or 0
        except RuntimeError as error:
            refused.setdefault(_why(error), []).append(key[0])
            continue
        if made:
            count += int(made)
            landed.append(key)
        else:
            refused.setdefault("no key made", []).append(key[0])
    notes = [KEYS_REFUSED % (len(times), len(keys_list), plug, why)
             for why, times in refused.items()]
    if not landed:
        return Written(count, notes)
    try:
        _put_tangents(curve, _tangent_edits(landed, weighted, True))
        for attr, value in (("preInfinity", pre), ("postInfinity", post)):
            wanted = _INFINITY_VALUE.get(value)
            if wanted is not None and int(cmds.getAttr(curve + "." + attr)) != wanted:
                cmds.setAttr(curve + "." + attr, wanted)
    except RuntimeError as error:
        notes.append(TANGENTS_LOST % (plug, _why(error)))
    return Written(count, notes, [plug])


def make_layer(record):
    """A new animation layer for the card's layer `record` (`curvedata.layer_record`), on top of
    the stack; its name - the card's, or the one Maya made free («Fix1»). Made as the Tools'
    layer bake makes its own (`cmds.animLayer(name)`): with scene tabs on, the tabs' layer hook
    moves it under the current tab's root one idle later (`maya_scenetabs.hooks.on_layer`). Its
    accumulation modes are set before any plug joins it (a scale key made under the wrong mode
    holds the wrong identity - the layer bake's note), then its weight and mute."""
    made = cmds.animLayer(record["name"], override=bool(record.get("override")))
    rotation = dict((v, k) for k, v in curvedata.ROTATION.items())
    scale = dict((v, k) for k, v in curvedata.SCALE.items())
    cmds.setAttr(made + ".rotationAccumulationMode",
                 rotation.get(record.get("rotation"), 0))
    cmds.setAttr(made + ".scaleAccumulationMode", scale.get(record.get("scale"), 1))
    cmds.animLayer(made, edit=True, weight=float(record.get("weight", 1.0)))
    cmds.animLayer(made, edit=True, mute=bool(record.get("mute")))
    return made
```

The `MakeCmds` fake answers `setAttr` with two arguments only; `write_raw` calls `getAttr` on `.postInfinity` — `CurveCmds.getAttr` answers it (0). In the module docstring's «Layer curves» paragraph add one sentence: «`write_raw` keys a stored LAYER curve with its own values (original curves, 2026-10-28) - measured in `docs/superpowers/plans/probe_poselib_raw_layer_keys.py`», followed by the probe's SUMMARY line and the two enum lines Task 1 Step 2 printed, copied as they came out.

**Task 1 fallback** — ONLY if Task 1's raw gates failed, replace `_raw_key` with:

```python
def _raw_key(curve, time, value):
    """One RAW key on the curve node `curve` through the API (task 1: `setKeyframe` on the node
    did not write the raw value): the key at `time` set to `value`, or added. An angle curve's
    value is in UI units here and radians in the API."""
    import maya.api.OpenMaya as om
    import maya.api.OpenMayaAnim as oma
    picked = om.MSelectionList()
    picked.add(curve)
    fn = oma.MFnAnimCurve(picked.getDependNode(0))
    when = om.MTime(float(time), om.MTime.uiUnit())
    if fn.animCurveType == oma.MFnAnimCurve.kAnimCurveTA:
        value = om.MAngle(float(value), om.MAngle.uiUnit()).asRadians()
    index = fn.find(when)
    if index is None:
        fn.addKey(when, float(value))
    else:
        fn.setValue(index, float(value))
    return 1
```

(and the `RawCmds` tests then patch `keys._raw_key` with a recorder instead of reading `raw` calls).

- [ ] **Step 4: Run the tests**

Run: `... -m unittest tests.test_poselib_keys -v`
Expected: every test OK.

- [ ] **Step 5: Commit**

```powershell
git add SkeldarAnim/maya_poselib/keys.py tests/test_poselib_keys.py
git commit -F $env:TEMP\skeldar_msg.txt   # "feat(poselib): keys - the layer stack, raw layer-curve keys, layers made for a card"
```

---

### Task 4: `store` — the curves file

**Files:**
- Modify: `SkeldarAnim/maya_poselib/store.py` (constants, `write`, `replace`, `_swap_in`, new `read_curves` after `read_frames`, the module docstring's file list)
- Test: `tests/test_poselib_store.py`

**Interfaces:**
- Produces: `CURVES_FILE = "curves.json.gz"`; `write(root, folder, name, data, thumbnail=None, replace=False, frames=None, preview=None, curves=None)`; `replace(path, data, frames=None, thumbnail=None, preview=None, curves=None)`; `read_curves(path) -> dict` (ValueError when missing / not gzip JSON / no `nodes` list; cached like `read_frames`).

- [ ] **Step 1: Write the failing tests** (in `tests/test_poselib_store.py`, a new class; the module's helpers write temp libraries — follow the existing `read_frames` tests' setUp in that file)

```python
class Curves(unittest.TestCase):

    CURVES = {"version": 1, "nodes": [{"name": "FKWrist_R", "attrs": {
        "rotateZ": {"BaseAnimation": {"keys": [[0.0, 1.0]], "weighted": False, "breakdown": []}}}}]}

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="skeldar_store_curves_")
        self.addCleanup(shutil.rmtree, self.root, True)

    def header(self):
        return {"format": store.ANIM_FORMAT, "kind": "character", "start": 0.0, "end": 1.0,
                "frames": 2, "curves": {"layers": [{"name": "BaseAnimation", "base": True}],
                                        "nodes": 1}}

    def test_a_card_written_with_curves_reads_them_back(self):
        card = store.write(self.root, "", "Walk", self.header(), frames={"bones": [], "world": []},
                           curves=self.CURVES)
        self.assertTrue(os.path.isfile(os.path.join(card, store.CURVES_FILE)))
        self.assertEqual(store.read_curves(card), self.CURVES)

    def test_a_pose_takes_no_curves(self):
        with self.assertRaises(ValueError):
            store.write(self.root, "", "Fist", {"format": store.FORMAT}, curves=self.CURVES)

    def test_a_replace_without_curves_keeps_them(self):
        card = store.write(self.root, "", "Walk", self.header(), curves=self.CURVES)
        store.replace(card, self.header())
        self.assertEqual(store.read_curves(card), self.CURVES)

    def test_a_card_without_the_file_or_a_broken_one_raises(self):
        card = store.write(self.root, "", "Walk", self.header())
        with self.assertRaises(ValueError):
            store.read_curves(card)
        with open(os.path.join(card, store.CURVES_FILE), "wb") as handle:
            handle.write(b"not gzip")
        with self.assertRaises(ValueError):
            store.read_curves(card)

    def test_a_file_of_another_shape_raises(self):
        card = store.write(self.root, "", "Walk", self.header(), curves={"nodes": "x"})
        with self.assertRaises(ValueError):
            store.read_curves(card)
```

(`os`, `shutil`, `tempfile`, `unittest` and `store` are already imported in that test module; add any that are not.)

- [ ] **Step 2: Run them to see them fail**

Run: `... -m unittest tests.test_poselib_store -v`
Expected: the new tests ERROR (`TypeError: write() got an unexpected keyword argument 'curves'`, `AttributeError: ... 'read_curves'`).

- [ ] **Step 3: Write the code**

Beside `FRAMES_FILE`:

```python
CURVES_FILE = "curves.json.gz"        # an animation card's original curves (2026-10-28)
```

`write` — signature and the pose refusal:

```python
def write(root, folder, name, data, thumbnail=None, replace=False, frames=None, preview=None,
          curves=None):
```

```python
    if not anim and (frames is not None or preview or curves is not None):
        raise ValueError("a pose card takes no frames, no preview and no curves")
```

and pass it on: `_swap_in(card, data, frames, thumbnail, preview, existed, curves)`. Add one sentence to its docstring: «`curves` an animation's original curves (written as `curves.json.gz`, 2026-10-28).»

`replace` — the same: signature `def replace(path, data, frames=None, thumbnail=None, preview=None, curves=None):`, the pose refusal includes `curves is not None`, and `_swap_in(card, data, frames, thumbnail, preview, True, curves)`.

`_swap_in` — signature `def _swap_in(card, data, frames, thumbnail, preview, existed, curves=None):` and, right after the frames' `stage`:

```python
        if curves is not None:
            stage(CURVES_FILE, lambda part: _dump_frames(part, curves))
```

After `read_frames`:

```python
#  `read_curves`' cache: ONE entry, as `_FRAMES`'.
_CURVES = {}


def read_curves(path):
    """The original curves of the animation card at `path` - its `curves.json.gz` decoded:
    {"version", "nodes": [...]} (spec 2026-10-28). Cached - one entry, keyed by the file's path,
    time and size; read it, never change it. ValueError when the file is missing, is not gzip
    JSON or holds no `nodes` list (the press checks the rest against the header:
    `curvedata.check` - this module imports no sibling)."""
    target = _fwd(path) + "/" + CURVES_FILE
    try:
        stat = os.stat(target)
    except OSError as exc:
        raise ValueError("%s: cannot be read (%s)" % (target, exc))
    key = (os.path.normcase(os.path.abspath(target)), stat.st_mtime_ns, stat.st_size)
    if key in _CURVES:
        return _CURVES[key]
    try:
        with gzip.open(target, "rt", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, EOFError, zlib.error, ValueError) as exc:
        raise ValueError("%s: not a card's curves (%s)" % (target, exc))
    if not (isinstance(data, dict) and isinstance(data.get("nodes"), list)):
        raise ValueError("%s: not a card's curves" % target)
    _CURVES.clear()
    _CURVES[key] = data
    return data
```

In the module docstring's list of an animation card's files add: «`curves.json.gz` (its original curves, layer by layer - read only by a paste, `read_curves`)».

- [ ] **Step 4: Run the tests**

Run: `... -m unittest tests.test_poselib_store tests.test_install -v`
Expected: all OK (the install moves a card folder file by file, so nothing there changes).

- [ ] **Step 5: Commit**

```powershell
git add SkeldarAnim/maya_poselib/store.py tests/test_poselib_store.py
git commit -F $env:TEMP\skeldar_msg.txt   # "feat(poselib): store - an animation card's curves.json.gz"
```

---

### Task 5: `animdata` — Paste as and the layer pick

**Files:**
- Modify: `SkeldarAnim/maya_poselib/animdata.py` (`PASTE_AS`, `Options`, `options_from`, the docstring's list)
- Test: `tests/test_poselib_animdata.py`

**Interfaces:**
- Produces: `PASTE_AS = ("retarget", "curves")`; `Options(..., paste_as="retarget", layers=None)` — `layers` None (every layer) or a tuple of str; `options_from` validates both.

- [ ] **Step 1: Write the failing tests**

```python
class PasteAs(unittest.TestCase):

    def test_the_defaults_keep_todays_paste(self):
        options = animdata.Options()
        self.assertEqual((options.paste_as, options.layers), ("retarget", None))

    def test_options_from_reads_and_validates_both(self):
        options = animdata.options_from({"paste_as": "curves",
                                         "layers": ["BaseAnimation", "AnimLayer1"]})
        self.assertEqual((options.paste_as, options.layers),
                         ("curves", ("BaseAnimation", "AnimLayer1")))
        self.assertEqual(animdata.options_from({"paste_as": "bake"}).paste_as, "retarget")
        self.assertIsNone(animdata.options_from({"layers": "AnimLayer1"}).layers)
        self.assertIsNone(animdata.options_from({"layers": None}).layers)
        self.assertEqual(animdata.options_from({"layers": ["A", 3, "B"]}).layers, ("A", "B"))

    def test_the_plan_ignores_them(self):
        a = animdata.paste_plan(0, 10, [], animdata.Options(), 0)
        b = animdata.paste_plan(0, 10, [], animdata.Options(paste_as="curves", layers=("A",)), 0)
        self.assertEqual(a, b)
```

- [ ] **Step 2: Run them to see them fail**

Run: `... -m unittest tests.test_poselib_animdata -v`
Expected: `AttributeError: 'Options' object has no attribute 'paste_as'`.

- [ ] **Step 3: Write the code**

```python
PASTE_AS = ("retarget", "curves")
```

```python
#  ...; `in_place` - root / Main untouched; `paste_as` - "retarget" (the bones solved onto any
#  character, today's paste) or "curves" (the card's own curves, layer by layer, onto its own rig
#  model - spec 2026-10-28); `layers` - the card layers a "curves" paste writes, None for all
Options = namedtuple("Options", "mode at_current start end connect keys in_place paste_as layers")
Options.__new__.__defaults__ = ("replace", True, None, None, False, "every", False, "retarget",
                                None)
```

In `options_from` read and validate:

```python
    paste_as = mapping.get("paste_as", base.paste_as)
    layers = mapping.get("layers")
    if isinstance(layers, (list, tuple)):
        layers = tuple(name for name in layers if isinstance(name, str))
    else:
        layers = None
    return Options(
        ...,                                          # the seven fields as today
        paste_as=paste_as if paste_as in PASTE_AS else "retarget",
        layers=layers)
```

and add «the paste as / the layers a curves paste writes» to the module docstring's description of the apply OPTIONS.

- [ ] **Step 4: Run the tests**

Run: `... -m unittest tests.test_poselib_animdata tests.test_poselib_animapply -v`
Expected: all OK.

- [ ] **Step 5: Commit**

```powershell
git add SkeldarAnim/maya_poselib/animdata.py tests/test_poselib_animdata.py
git commit -F $env:TEMP\skeldar_msg.txt   # "feat(poselib): animdata - Paste as and the layer pick"
```

---

### Task 6: Save — `curvecapture` and `animcapture.build_clip`

**Files:**
- Create: `SkeldarAnim/maya_poselib/curvecapture.py`
- Modify: `SkeldarAnim/maya_poselib/animcapture.py` (imports; `object_curves(..., layers=None)`; new `Clip`, `build_clip`, `_character_curves`, `_summarize`; `build_animation` becomes its wrapper)
- Test: `tests/test_poselib_curvecapture.py` (new), `tests/test_poselib_animcapture.py`

**Interfaces:**
- Consumes: `keys.layer_stack/layer_record/layer_plugs/feed_of/curve_for/_INFINITY` (Task 3), `curvedata.*` (Task 2), `animcapture._copied`.
- Produces:
  - `curvecapture.character_nodes(ref, bones, members) -> [long path]`
  - `curvecapture.stack() -> [(scene layer name or None, record)]`
  - `curvecapture.channel_curves(plugs, start, end, copy, layers) -> (OrderedDict {plug: {card layer: CURVE}}, [driven plugs])`
  - `curvecapture.node_curves(nodes, start, end, copy, layers) -> ([{"name", "attrs"}], [driven plugs])`
  - `curvecapture.used_records(layers, per_layer_dicts) -> [record]` (base first)
  - `curvecapture.driven_note(driven) -> str`
  - `animcapture.Clip(header, frames, curves, note)`, `animcapture.build_clip(selection=None, regions=None, start=None, end=None, progress=None) -> Clip`
  - `animcapture.object_curves(nodes, start, end, own=(), layers=None)`

- [ ] **Step 1: Write the failing tests** — `tests/test_poselib_curvecapture.py`:

```python
"""maya_poselib.curvecapture - a card's original curves read off the scene (spec
2026-10-28-pose-library-curves-and-layers-design.md, «Which channels»). `keys` and `cmds` are
faked as the module attributes (CLAUDE.md's rule); `copy` is the caller's (`animcapture._copied`)."""

import unittest
from collections import OrderedDict

from maya_poselib import curvecapture as cc
from maya_poselib import curvedata


class FakeKeys(object):
    """`keys` as curvecapture asks it."""

    _INFINITY = {0: "constant", 1: "linear", 3: "cycle", 4: "cycleRelative", 5: "oscillate"}
    NAMED = 4

    def __init__(self, stack=(), holds=None, curves=None, feeds=None):
        self.stack = list(stack)
        self.holds = dict(holds or {})
        self.curves = dict(curves or {})
        self.feeds = dict(feeds or {})
        self.asked = []

    def layer_stack(self):
        return list(self.stack)

    def layer_record(self, name, base=False):
        return curvedata.layer_record(name, base=base)

    def layer_plugs(self, name):
        return set(self.holds.get(name, ()))

    def curve_for(self, plug, layer):
        self.asked.append((layer, plug))
        return self.curves.get((layer, plug))

    def feed_of(self, plug):
        return self.feeds.get(plug, ("curve", None))


class FakeCmds(object):

    def __init__(self, values=None, infinity=None):
        self.values = dict(values or {})
        self.infinity = dict(infinity or {})

    def getAttr(self, plug):
        node, _dot, attr = plug.rpartition(".")
        if attr in ("preInfinity", "postInfinity"):
            return self.infinity.get(node, (0, 0))[attr == "postInfinity"]
        return self.values[plug]


def copy(curve, start, end):
    return {"keys": [[float(start), 1.0], [float(end), 2.0]], "weighted": False,
            "breakdown": [], "from": curve}


class Case(unittest.TestCase):

    def use(self, keys=None, cmds=None):
        for name, fake in (("keys", keys), ("cmds", cmds)):
            if fake is not None:
                self.addCleanup(setattr, cc, name, getattr(cc, name))
                setattr(cc, name, fake)


class Stack(Case):

    def test_no_layers_is_the_base_alone_on_the_plain_curves(self):
        self.use(FakeKeys())
        self.assertEqual(cc.stack(), [(None, curvedata.layer_record(curvedata.BASE, base=True))])

    def test_the_root_is_the_base_whatever_its_name(self):
        self.use(FakeKeys(stack=["skeldarTabsLayerRoot", "AnimLayer1"]))
        names = [(scene, record["name"]) for scene, record in cc.stack()]
        self.assertEqual(names, [("skeldarTabsLayerRoot", curvedata.BASE),
                                 ("AnimLayer1", "AnimLayer1")])


class ChannelCurves(Case):

    def test_a_layered_channel_keeps_each_layers_curve_with_its_infinity(self):
        keys = FakeKeys(stack=["BaseAnimation", "AnimLayer1"],
                        holds={"AnimLayer1": ["a.rx"]},
                        curves={("BaseAnimation", "a.rx"): "c0", ("AnimLayer1", "a.rx"): "c1",
                                ("BaseAnimation", "a.tx"): "c2"},
                        feeds={"a.rx": ("layer", "blend")})
        self.use(keys, FakeCmds(infinity={"c1": (0, 3)}))
        layers = cc.stack()
        found, driven = cc.channel_curves(["a.rx", "a.tx"], 0, 10, copy, layers)
        self.assertEqual(driven, [])
        self.assertEqual(list(found["a.rx"]), [curvedata.BASE, "AnimLayer1"])
        self.assertEqual(found["a.rx"]["AnimLayer1"]["from"], "c1")
        self.assertEqual((found["a.rx"]["AnimLayer1"]["pre"], found["a.rx"]["AnimLayer1"]["post"]),
                         ("constant", "cycle"))
        self.assertEqual(list(found["a.tx"]), [curvedata.BASE])
        self.assertNotIn(("AnimLayer1", "a.tx"), keys.asked)     # the layer does not hold it

    def test_a_free_channel_is_a_static_on_the_base(self):
        self.use(FakeKeys(feeds={"a.ry": ("free", None)}), FakeCmds(values={"a.ry": 7.0}))
        found, _driven = cc.channel_curves(["a.ry"], 0, 10, copy, cc.stack())
        self.assertEqual(found["a.ry"], {curvedata.BASE: {"static": 7.0}})

    def test_a_driven_channel_keeps_no_curve_and_is_named(self):
        self.use(FakeKeys(feeds={"a.rz": ("driven", "orient1")}))
        found, driven = cc.channel_curves(["a.rz"], 0, 10, copy, cc.stack())
        self.assertEqual((dict(found), driven), ({}, ["a.rz"]))
        self.assertIn("1 channel", cc.driven_note(driven))
        self.assertEqual(cc.driven_note([]), "")


class UsedRecords(Case):

    def test_the_base_first_then_the_used_layers_in_stack_order(self):
        self.use(FakeKeys(stack=["Root", "A", "B", "C"]))
        layers = cc.stack()
        used = cc.used_records(layers, [{"C": {}}, {"A": {}}])
        self.assertEqual([r["name"] for r in used], [curvedata.BASE, "A", "C"])


class CharacterNodes(Case):

    def test_a_skeleton_keeps_its_member_joints(self):
        ref = type("Ref", (), {"kind": "skeleton", "rig": None})()
        bones = OrderedDict([("pelvis", {"path": "|root|pelvis"}),
                             ("hand_l", {"path": "|root|pelvis|hand_l"})])
        self.assertEqual(cc.character_nodes(ref, bones, ["hand_l"]), ["|root|pelvis|hand_l"])

    def test_a_rig_keeps_the_controls_whose_bones_meet_the_members(self):
        rig = type("Rig", (), {"control_set": "Manny_Rig1:ControlSet"})()
        ref = type("Ref", (), {"kind": "rig", "rig": rig})()

        class Cmds(object):
            def sets(self, name, query=False):
                return ["Manny_Rig1:FKWrist_L", "Manny_Rig1:FKWrist_R", "Manny_Rig1:Main"]

            def ls(self, names, long=False):
                return ["|r|" + name for name in names]
        self.use(cmds=Cmds())
        saved = cc._named
        self.addCleanup(setattr, cc, "_named", saved)
        cc._named = lambda leaf, bones: {"FKWrist_L": ["hand_l"], "FKWrist_R": ["hand_r"]}.get(
            leaf, curvedata.WHOLE)
        saved_whole = cc.scene.whole_body
        self.addCleanup(setattr, cc.scene, "whole_body", saved_whole)
        cc.scene.whole_body = lambda bones: ["pelvis", "hand_l", "hand_r"]
        self.assertEqual(cc.character_nodes(ref, {}, ["hand_l"]), ["|r|Manny_Rig1:FKWrist_L"])
        self.assertEqual(cc.character_nodes(ref, {}, ["pelvis", "hand_l", "hand_r"]),
                         ["|r|Manny_Rig1:FKWrist_L", "|r|Manny_Rig1:FKWrist_R",
                          "|r|Manny_Rig1:Main"])


if __name__ == "__main__":
    unittest.main()
```

and in `tests/test_poselib_animcapture.py` a class for the header block (pure on its inputs):

```python
class Summarize(unittest.TestCase):

    KEYED = {"keys": [[0.0, 1.0]], "weighted": False, "breakdown": []}

    def test_a_card_with_curves_gets_the_block_of_the_layers_used(self):
        from maya_poselib import curvedata
        layers = [(None, curvedata.layer_record(curvedata.BASE, base=True)),
                  ("A", curvedata.layer_record("A")), ("B", curvedata.layer_record("B"))]
        header = {"objects": [{"attrs": {"tx": dict(self.KEYED, layers={"B": self.KEYED})},
                               "shape": {}}]}
        curves = {"version": 1, "nodes": [{"name": "c", "attrs": {"rx": {curvedata.BASE: self.KEYED}}}]}
        animcapture._summarize(header, layers, curves)
        self.assertEqual([r["name"] for r in header["curves"]["layers"]], [curvedata.BASE, "B"])
        self.assertEqual(header["curves"]["nodes"], 2)

    def test_no_curves_and_no_layered_object_leave_the_header_alone(self):
        header = {"objects": [{"attrs": {"tx": self.KEYED}, "shape": {}}]}
        animcapture._summarize(header, [], None)
        self.assertNotIn("curves", header)
```

- [ ] **Step 2: Run them to see them fail**

Run: `... -m unittest tests.test_poselib_curvecapture tests.test_poselib_animcapture -v`
Expected: `ModuleNotFoundError: No module named 'maya_poselib.curvecapture'`; `_summarize` missing.

- [ ] **Step 3: Write `curvecapture.py`**

```python
"""The Pose Library's ORIGINAL curves read off the scene (2026-10-28): every curve of a card's
channels, layer by layer - what `animcapture.build_clip` writes into `curves.json.gz` (a
character's controls or joints) and into an objects card's layered channels. The rules of the
data are `curvedata`'s.

The animator: «...сохранения по слоям и сохранения ключей». Which channels:
- a rig's ControlSet controls whose bones (`scene._control_bones`, the rule a selected control
  follows) meet the card's members - `Main` (the whole body) only with a whole-body card; a
  skeleton's member joints (`character_nodes`);
- each keyable unlocked scalar channel (`objects.channel_names`); per layer, bottom to top
  (`stack`: the root as `curvedata.BASE`, a scene tab's root left out), the curve
  `keys.curve_for` answers - a layer above the base asked only for the plugs it holds
  (`keys.layer_plugs`, one query a layer), so another character's layers never enter the card -
  read by the caller's `copy` (`animcapture._copied`: a duplicate cut to the range with a
  shape-keeping key at each end) plus its infinity; a channel nothing feeds a `{"static": v}` on
  the base; a channel a constraint, an expression or a driven key feeds holds no curve of its own
  and is named (`driven_note`) - the bones' frames still carry what it did.

The caller holds the undo queue off (the duplicates are made and deleted).

Spec: docs/superpowers/specs/2026-10-28-pose-library-curves-and-layers-design.md
"""

from collections import OrderedDict

import maya.cmds as cmds

from maya_poselib import curvedata
from maya_poselib import keys
from maya_poselib import objects as objs
from maya_poselib import scene

DRIVEN = "%s driven - no curve of theirs kept (%s)"


def _named(leaf, bones):
    """What a control names: its bones, or `curvedata.WHOLE` (`scene._control_bones`). A seam."""
    named = scene._control_bones(leaf, bones)
    return curvedata.WHOLE if named == scene._WHOLE else named


def character_nodes(ref, bones, members):
    """The long paths whose channels a character card keeps as curves: a rig's controls whose
    bones meet `members` (`curvedata.keeps_control`; the card is the whole body when its members
    hold every bone `scene.whole_body` names), a skeleton's member joints in skeleton order."""
    if ref.kind == "rig" and ref.rig is not None:
        found = cmds.sets(ref.rig.control_set, query=True) or []
        controls = (cmds.ls(found, long=True) or []) if found else []
        whole = set(scene.whole_body(bones)) <= set(members or ())
        return [path for path in controls
                if curvedata.keeps_control(_named(scene.leaf(path), bones), members, whole)]
    return [bones[name]["path"] for name in bones
            if name in set(members or ()) and bones[name].get("path")]


def stack():
    """[(the scene's layer name, its card record)] bottom to top - the root first as
    `curvedata.BASE`; [(None, the base)] in a scene without layers (the plain curves are the
    base)."""
    names = keys.layer_stack()
    if not names:
        return [(None, curvedata.layer_record(curvedata.BASE, base=True))]
    return [(name, keys.layer_record(name, base=(index == 0))) for index, name in enumerate(names)]


def _infinity(curve):
    """{"pre", "post"} of `curve` in `setInfinity`'s spelling, {} when they cannot be read."""
    try:
        pre = int(cmds.getAttr(curve + ".preInfinity"))
        post = int(cmds.getAttr(curve + ".postInfinity"))
    except (RuntimeError, ValueError, TypeError):
        return {}
    return {"pre": keys._INFINITY.get(pre, "constant"), "post": keys._INFINITY.get(post, "constant")}


def _number(value):
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    return None


def channel_curves(plugs, start, end, copy, layers):
    """(OrderedDict {plug: {card layer: CURVE}}, [driven plugs]) of `plugs` over [start, end] on
    `layers` (`stack()`'s answer, read once by the caller). A plug no layer holds a curve for
    and nothing feeds is `{"static": v}` on the base; a missing plug, or one that answers no
    number, is left out."""
    holds = dict((name, keys.layer_plugs(name)) for name, _record in layers[1:])
    out, driven = OrderedDict(), []
    for plug in plugs:
        kind, _node = keys.feed_of(plug)
        if kind == "missing":
            continue
        if kind == "driven":
            driven.append(plug)
            continue
        per = OrderedDict()
        for index, (name, record) in enumerate(layers):
            if index and plug not in holds.get(name, ()):
                continue
            curve = keys.curve_for(plug, name)
            if curve is None:
                continue
            found = dict(copy(curve, start, end))
            found.update(_infinity(curve))
            per[record["name"]] = found
        if not per:
            try:
                value = _number(cmds.getAttr(plug))
            except (RuntimeError, ValueError, TypeError):
                value = None
            if value is None:
                continue
            per[curvedata.BASE] = {"static": value}
        out[plug] = per
    return out, driven


def node_curves(nodes, start, end, copy, layers):
    """([{"name": leaf, "attrs": {attr: {card layer: CURVE}}}], [driven plugs]) of `nodes`' keyable
    channels (`objects.channel_names`), in `nodes`' order; a node with no channel left out."""
    plugs, owner = [], {}
    for path in nodes or ():
        for attr in objs.channel_names(path, cmds):
            plug = path + "." + attr
            plugs.append(plug)
            owner[plug] = (path, attr)
    found, driven = channel_curves(plugs, start, end, copy, layers)
    by_node = OrderedDict()
    for plug, per in found.items():
        path, attr = owner[plug]
        by_node.setdefault(path, OrderedDict())[attr] = dict(per)
    return [{"name": scene.leaf(path), "attrs": dict(attrs)} for path, attrs in by_node.items()], \
        driven


def used_records(layers, per_layer_dicts):
    """The card's layer records: the base first, then every layer some {card layer: CURVE} of
    `per_layer_dicts` names, in stack order."""
    used = set(name for per in per_layer_dicts for name in per)
    return [layers[0][1]] + [record for _name, record in layers[1:] if record["name"] in used]


def driven_note(driven):
    """The save line's note on the channels kept without curves, "" when there are none."""
    if not driven:
        return ""
    count = len(driven)
    shown = ", ".join(scene.leaf(plug.rsplit(".", 1)[0]) + "." + plug.rsplit(".", 1)[1]
                      for plug in driven[:keys.NAMED])
    if count > keys.NAMED:
        shown += " and %d more" % (count - keys.NAMED)
    return DRIVEN % ("%d channel%s" % (count, "" if count == 1 else "s"), shown)
```

- [ ] **Step 4: Wire it into `animcapture.py`**

Imports: add `from collections import namedtuple` beside `OrderedDict`, and `from maya_poselib import curvecapture`, `from maya_poselib import curvedata` among the siblings. Then:

```python
#  What a Save reads (2026-10-28): the header, the frames (a character card), the original curves
#  (`curves.json.gz`'s content, or None) and the line
Clip = namedtuple("Clip", "header frames curves note")
```

`object_curves` gains `layers=None`; inside its `with _unrecorded():` block, right after `found = _sampled(...)`:

```python
        layered = {}
        if layers is not None and len(layers) > 1:          # a scene without layers has none
            fed_layered = [plug for _attrs, _attr, plug in fed if keys.input_of(plug) == "layer"]
            if fed_layered:
                layered = curvecapture.channel_curves(fed_layered, start, end, _copied, layers)[0]
```

and in the loop after it:

```python
    for attrs, attr, plug in fed:
        if plug in found:
            attrs[attr] = found[plug]
            if layered.get(plug):
                attrs[attr] = dict(found[plug], layers=dict(layered[plug]))
        else:
            del attrs[attr]
```

(docstring: «`layers` (`curvecapture.stack()`) given, a channel in animation layers also keeps its curve on each layer, `"layers"` beside its sampled keys (spec 2026-10-28).»)

Then the new Save entry and its helpers, replacing `build_animation`'s body:

```python
def _character_curves(ref, header, start, end, layers):
    """(the card's `curves.json.gz` content or None, the note) of the character `ref`: its
    controls' or joints' curves (`curvecapture.node_curves` over `character_nodes`), None when
    none holds a key - statics alone say nothing the frames do not."""
    bones = scene.skeleton(ref, [])[0]
    nodes = curvecapture.character_nodes(ref, bones, header.get("members") or ())
    with _unrecorded():
        found, driven = curvecapture.node_curves(nodes, start, end, _copied, layers)
    note = curvecapture.driven_note(driven)
    pers = [per for node in found for per in node["attrs"].values()]
    if not curvedata.has_keys(pers):
        return None, note
    return {"version": curvedata.VERSION, "nodes": found}, note


def _layered(record):
    """[{card layer: CURVE}] of an objects record's channels that sat in layers."""
    out = []
    for attrs in (record.get("attrs") or {}, record.get("shape") or {}):
        for curve in attrs.values():
            if isinstance(curve, dict) and isinstance(curve.get("layers"), dict):
                out.append(curve["layers"])
    return out


def _summarize(header, layers, curves):
    """The header's `curves` block (`curvedata.summary`) when the card keeps original curves -
    its controls' (`curves`) or an objects channel's layers: the layers used, base first, and how
    many nodes keep curves. Nothing written otherwise: an older card's paste stays as it was."""
    objects = header.get("objects") or []
    layered = [(record, _layered(record)) for record in objects]
    layered = [(record, pers) for record, pers in layered if pers]
    if curves is None and not layered:
        return
    pers = [per for node in (curves or {}).get("nodes", []) for per in node["attrs"].values()]
    pers += [per for _record, found in layered for per in found]
    count = len((curves or {}).get("nodes", [])) + len(layered)
    header["curves"] = curvedata.summary(curvecapture.used_records(layers, pers), count)


def build_clip(selection=None, regions=None, start=None, end=None, progress=None):
    """`Clip(header, frames, curves, note)` of the selection over [start, end] - `build_animation`'s
    card plus its ORIGINAL curves (spec 2026-10-28): a character card's controls' or joints'
    curves layer by layer (`curves`, written as `curves.json.gz`), its objects' and an objects
    card's layered channels in the header, and the header's `curves` block. A refusal or a cancel:
    `Clip(None, None, None, why)`."""
    if start is None or end is None:
        first, last = default_range()
        start = first if start is None else start
        end = last if end is None else end
    start, end = _whole(start), _whole(end)
    if end < start:
        return Clip(None, None, None, EMPTY % (start, end))
    refs, nodes, loose_owned = scene.split(selection)
    loose = [path for path, _owner in loose_owned]
    if len(refs) > 1:
        return Clip(None, None, None, MANY)
    layers = curvecapture.stack()
    if refs:
        header, frames, note = character_animation(refs[0], nodes, regions, start, end,
                                                   progress)
        if header is None:
            return Clip(None, None, None, note)
        curves, said = _character_curves(refs[0], header, start, end, layers)
        if loose:
            own = [path for path, owner in loose_owned if scene.owned(refs[0], owner)]
            header["objects"] = object_curves(loose, start, end, own, layers)
            note += " | + %s" % scene.describe([], loose)
        _summarize(header, layers, curves)
        if said:
            note += " | " + said
        return Clip(header, frames, curves, note)
    if loose:
        header = _common("objects")
        header.update(_span(start, end))
        header["objects"] = object_curves(loose, start, end, layers=layers)
        _summarize(header, layers, None)
        return Clip(header, None, None,
                    "%s: %s" % (scene.describe([], loose), _frames_text(start, end)))
    return Clip(None, None, None, NOTHING)


def build_animation(selection=None, regions=None, start=None, end=None, progress=None):
    """(header, frames, note) - `build_clip`'s card without its curves file: the callers that
    write no `curves.json.gz` (a verify, an older script). The header still carries its `curves`
    block when the card has them."""
    clip = build_clip(selection, regions, start, end, progress)
    return clip.header, clip.frames, clip.note
```

Keep `build_animation`'s old docstring text about progress steps on `build_clip`. Add to the module docstring after «An OBJECTS card ...»: «The ORIGINAL curves (2026-10-28, `build_clip`): `curvecapture` reads a character's controls' or joints' curves layer by layer into `curves.json.gz`, an objects channel in layers keeps its layers beside its sampled keys, and the header's `curves` block names the layers.»

- [ ] **Step 5: Run the tests**

Run: `... -m unittest tests.test_poselib_curvecapture tests.test_poselib_animcapture -v`
Expected: all OK (the old `build_animation` tests pass through the wrapper; if one fakes `scene.split` it now also meets `curvecapture.stack()` - when a fake `keys` is not installed there, give that test `self.addCleanup(setattr, animcapture.curvecapture, "stack", animcapture.curvecapture.stack)` and `animcapture.curvecapture.stack = lambda: [(None, curvedata.layer_record(curvedata.BASE, base=True))]`, and `animcapture._character_curves = lambda *a: (None, "")` the same way).

- [ ] **Step 6: Commit**

```powershell
git add SkeldarAnim/maya_poselib/curvecapture.py SkeldarAnim/maya_poselib/animcapture.py tests/test_poselib_curvecapture.py tests/test_poselib_animcapture.py
git commit -F $env:TEMP\skeldar_msg.txt   # "feat(poselib): Save reads a card's original curves layer by layer"
```

---

### Task 7: Paste — `curveapply` and the dispatch

**Files:**
- Create: `SkeldarAnim/maya_poselib/curveapply.py`
- Modify: `SkeldarAnim/maya_poselib/animapply.py` (`apply`, `apply_onto`, `drop_floor`, `_press_objects`, `Blend.start`, new `_pastes_curves`, `_press_curves`; the module docstring)
- Test: `tests/test_poselib_curveapply.py` (new), `tests/test_poselib_animapply.py`

**Interfaces:**
- Consumes: Task 2-5's names; `animapply._options/_plan/_object_keys/_breakdown_times/_breakdowns/_ops/_chunk/_Steps/_undo_failed/_kept/_object_channels/_card_matched/_main_of/STEP/CANCELLED/ROTATE`; `apply.target_label/_counted/_named/_owner/NOT_POSED`; `curvecapture.character_nodes`; `skelsolve.root_leaf`.
- Produces: `curveapply.matches(header, ref)`, `curveapply.target_nodes(ref)`, `curveapply.character_channels(header, curves, ref, only=None, in_place=False) -> (OrderedDict, notes)`, `curveapply.objects_channels(matched) -> (OrderedDict, notes, paths)`, `curveapply.paste(header, groups, options=None, progress=None) -> (ok, line)` with `groups` = `[(target label, noun, OrderedDict {plug: {card layer: CURVE}}, notes)]`; constants `MIRRORED`, `BLENDED`, `UNREAD`, `RETARGETED`, `NO_LAYER`, `NOTHING`; `animapply.apply(..., curves=None)`, `apply_onto(..., curves=None)`, `drop_floor(..., curves=None)`.

- [ ] **Step 1: Write the failing tests** — `tests/test_poselib_curveapply.py`:

```python
"""maya_poselib.curveapply - the paste of a card's original curves (spec 2026-10-28, «Paste»).
The scene halves stand on seams (module attributes rebound per test); the whole press is the
mayapy verify's (`verify_poselib_curves.py`)."""

import unittest
from collections import OrderedDict

from maya_poselib import animdata
from maya_poselib import curveapply as ca
from maya_poselib import curvedata

BASE = curvedata.layer_record(curvedata.BASE, base=True)
ADD = curvedata.layer_record("AnimLayer1")
HEADER = {"name": "Walk", "start": 0.0, "end": 10.0, "key_times": [0.0, 10.0],
          "character": {"model": "Manny", "kind": "rig"},
          "curves": curvedata.summary([BASE, ADD], 1)}
KEYED = {"keys": [[0.0, 1.0, "auto", "auto", 0.0, 1.0, 0.0, 1.0],
                  [10.0, 3.0, "auto", "auto", 0.0, 1.0, 0.0, 1.0]],
         "weighted": False, "breakdown": [], "pre": "constant", "post": "cycle"}


class Ref(object):
    def __init__(self, model="Manny", kind="rig"):
        self.model, self.kind = model, kind


class Matches(unittest.TestCase):

    def test_the_same_model_and_kind(self):
        self.assertTrue(ca.matches(HEADER, Ref()))
        self.assertFalse(ca.matches(HEADER, Ref("Creep")))
        self.assertFalse(ca.matches(HEADER, Ref(kind="skeleton")))
        self.assertFalse(ca.matches({"character": {}}, Ref()))


class Planned(unittest.TestCase):

    def test_the_chosen_layers_clipped_and_moved_to_the_paste(self):
        plan = animdata.paste_plan(0, 10, [0, 10], animdata.Options(), 20)
        groups = [("Manny_Rig1", "controls",
                   OrderedDict([("c.rx", {curvedata.BASE: KEYED, "AnimLayer1": {"static": 2.0}})]),
                   [])]
        planned = ca._planned(groups, ["AnimLayer1"], plan)
        self.assertEqual(list(planned), [(0, "c.rx")])
        stored, weighted, breaks, pre, post = planned[(0, "c.rx")]["AnimLayer1"]
        self.assertEqual(stored, [[20.0, 2.0]])
        planned = ca._planned(groups, [curvedata.BASE], plan)
        stored, _w, _b, pre, post = planned[(0, "c.rx")][curvedata.BASE]
        self.assertEqual([key[:2] for key in stored], [[20.0, 1.0], [30.0, 3.0]])
        self.assertEqual((pre, post), ("constant", "cycle"))


class Refusals(unittest.TestCase):

    def seam(self, name, value):
        owner, attr = name
        self.addCleanup(setattr, owner, attr, getattr(owner, attr))
        setattr(owner, attr, value)

    def test_no_layer_picked(self):
        self.assertEqual(ca.paste(HEADER, [], animdata.Options(layers=("Gone",))),
                         (False, ca.NO_LAYER))

    def test_a_locked_namesake_refuses_before_anything_is_written(self):
        self.seam((ca.aa, "_plan"), lambda header, options: animdata.paste_plan(
            0, 10, [], options, 0))
        self.seam((ca.keys, "existing_layers"), lambda: [
            {"name": "AnimLayer1", "override": False, "rotation": "component", "locked": True}])
        ok, line = ca.paste(HEADER, [], animdata.Options())
        self.assertFalse(ok)
        self.assertIn("AnimLayer1 is locked", line)


class LayersText(unittest.TestCase):

    def test_made_layers_are_said(self):
        text = ca._layers_text([curvedata.BASE, "AnimLayer1"],
                               {curvedata.BASE: None, "AnimLayer1": "AnimLayer2"}, ["AnimLayer2"])
        self.assertEqual(text, "BaseAnimation + AnimLayer2 (made)")


if __name__ == "__main__":
    unittest.main()
```

and in `tests/test_poselib_animapply.py`:

```python
class CurvesDispatch(unittest.TestCase):
    """`apply` under Paste as «Original curves»: the card's own model takes its curves, any other
    target the bones (`_press_refs`), the line says so; Mirror and Blend refused."""

    def setUp(self):
        from maya_poselib import curveapply, curvedata
        self.ca = curveapply
        self.header = {"name": "Walk", "kind": "character", "bones": {"pelvis": {}},
                       "character": {"model": "Manny", "kind": "rig"},
                       "curves": curvedata.summary([curvedata.layer_record(
                           curvedata.BASE, base=True)], 1)}
        self.log = []
        manny = type("Ref", (), {"model": "Manny", "kind": "rig", "label": "Manny_Rig1"})()
        creep = type("Ref", (), {"model": "Creep", "kind": "rig", "label": "Creep_Rig1"})()
        self.refs = [manny, creep]
        for owner, name, value in (
                (animapply, "_targets", lambda selection, prefer=None: (self.refs, "")),
                (animapply, "_press_refs", self.press_refs),
                (animapply, "_card_matched", lambda *a, **k: ([], [])),
                (animapply.ap, "_loose", lambda selection: []),
                (animapply.ap, "target_label", lambda ref: ref.label),
                (curveapply, "character_channels",
                 lambda header, curves, ref, only=None, in_place=False: (OrderedDict(), [])),
                (curveapply, "paste", self.paste)):
            self.addCleanup(setattr, owner, name, getattr(owner, name))
            setattr(owner, name, value)

    def press_refs(self, header, frames, refs, *args, **kwargs):
        # _press_refs(header, frames, refs, mirror, alpha, options, ...): options is args[2] -
        # an Options from `_press_curves`, the caller's raw mapping on today's road
        self.log.append(("refs", [ref.label for ref in refs],
                         animapply._options(args[2]).paste_as))
        return True, "retargeted line"

    def paste(self, header, groups, options=None, progress=None):
        self.log.append(("curves", [group[0] for group in groups]))
        return True, "curves line"

    def test_the_cards_model_takes_the_curves_the_rest_the_bones(self):
        ok, line = animapply.apply(self.header, {}, selection=["x"],
                                   options={"paste_as": "curves"}, curves={"nodes": []})
        self.assertTrue(ok)
        self.assertEqual(self.log, [("curves", ["Manny_Rig1"]),
                                    ("refs", ["Creep_Rig1"], "retarget")])
        self.assertIn("curves line", line)
        self.assertIn(self.ca.RETARGETED % "Creep_Rig1", line)

    def test_mirror_and_blend_are_refused(self):
        self.assertEqual(animapply.apply(self.header, {}, selection=["x"], mirror=True,
                                         options={"paste_as": "curves"}, curves={"nodes": []}),
                         (False, self.ca.MIRRORED))
        self.assertEqual(animapply.apply(self.header, {}, selection=["x"], alpha=0.5,
                                         options={"paste_as": "curves"}, curves={"nodes": []}),
                         (False, self.ca.BLENDED))

    def test_unreadable_curves_retarget_everyone_and_say_so(self):
        ok, line = animapply.apply(self.header, {}, selection=["x"],
                                   options={"paste_as": "curves"}, curves=None)
        self.assertEqual(self.log, [("refs", ["Manny_Rig1", "Creep_Rig1"], "retarget")])
        self.assertIn(self.ca.UNREAD, line)

    def test_retarget_is_todays_press(self):
        animapply.apply(self.header, {}, selection=["x"], options={"paste_as": "retarget"})
        self.assertEqual(self.log, [("refs", ["Manny_Rig1", "Creep_Rig1"], "retarget")])
```

(`press_refs` reads `args[2]` = the options positional of `_press_refs(header, frames, refs, mirror, alpha, options, ...)`; the call in Step 4 passes them positionally in that order. Add `from collections import OrderedDict` to the test module if it lacks it.)

- [ ] **Step 2: Run them to see them fail**

Run: `... -m unittest tests.test_poselib_curveapply tests.test_poselib_animapply -v`
Expected: `ModuleNotFoundError: No module named 'maya_poselib.curveapply'`; `apply() got an unexpected keyword argument 'curves'`.

- [ ] **Step 3: Write `curveapply.py`**

```python
"""The Pose Library's paste of ORIGINAL curves (2026-10-28): the card's own keys, layer by layer,
onto its own rig model - `animapply` hands a press here when its options say
`paste_as="curves"` and the card holds curves (`curvedata.has_curves`).

The animator: «...сохранения по слоям и сохранения ключей». The press:
1. the layers: the picked card layers (`curvedata.chosen`, the card's order), each paired with the
   target scene's (`curvedata.layer_target`): the base to the root (the plain curves without
   layers), a namesake of the same mode and rotation accumulation taken, a locked one REFUSED
   before anything is written, the rest made (`keys.make_layer`, inside the chunk);
2. the channels (`groups`, built by the caller): a character of the card's model
   (`character_channels`: the card's nodes paired by leaf name, kept to the card's members on the
   target - 1P upper / lower cut the members first -, Selected only and In place applied), the
   card's objects (`objects_channels`: a plain curve the base's, a layered one its layers);
3. each picked layer's curve clipped to the paste's source range and moved to its time
   (`animapply._object_keys` - At current time and Range as an objects card's);
4. ONE undo chunk (`animapply._chunk`): the layers made, the paste mode's cut / shift on THAT
   layer's curves only (`animapply._ops`), the RAW keys with every tangent, weighting, infinity
   (`keys.write_raw`) and breakdown (`animapply._breakdowns`); Connect on the one layer pasted
   (`_connect`); `progress` stepped once per channel, Esc undoes the chunk.
Nothing is measured: the curves are the source's, key for key. Mirror and Blend change values
and are refused by the caller (`MIRRORED`, `BLENDED`).

Spec: docs/superpowers/specs/2026-10-28-pose-library-curves-and-layers-design.md («Paste»)
"""

from collections import OrderedDict

import maya.cmds as cmds

from maya_poselib import animapply as aa
from maya_poselib import apply as ap
from maya_poselib import curvecapture
from maya_poselib import curvedata
from maya_poselib import keys
from maya_poselib import look
from maya_poselib import scene
from maya_poselib import skelsolve

MIRRORED = "original curves are pasted as they were keyed - turn Mirror off or paste as Retarget"
BLENDED = "original curves are pasted whole - Blend is for Retarget"
UNREAD = "the card's curves cannot be read - retargeted instead"
RETARGETED = "retargeted - not the card's model: %s"
NO_LAYER = "no layer of the card picked"
NOTHING = "nothing to paste: no picked layer holds a curve of the targets"
MISSING = "%d of the card's controls not on %s: %s"
MADE = "%s (made)"
CONNECT_ONE = "Connect skipped - it needs one layer, %d picked"
CONNECT_WEIGHT = "Connect skipped on %s - its weight is 0"
CONNECT_QUAT = "Connect skipped on the rotations of %s - it accumulates as quaternions"


def matches(header, ref):
    """Does `ref` take the card's curves - the same model and kind as the card's character?"""
    who = (header or {}).get("character") or {}
    return bool(who.get("model")) and who.get("model") == getattr(ref, "model", None) \
        and who.get("kind") == getattr(ref, "kind", None)


def target_nodes(ref):
    """The long paths a card's nodes pair with on `ref`: a rig's ControlSet, a skeleton's joints."""
    if ref.kind == "rig" and ref.rig is not None:
        found = cmds.sets(ref.rig.control_set, query=True) or []
        return (cmds.ls(found, long=True) or []) if found else []
    return cmds.ls(ref.root, dag=True, type="joint", long=True) or []


def _root_node(ref, bones):
    """What In place leaves unkeyed: a rig's Main, a skeleton's root joint."""
    if ref.kind == "rig":
        return aa._main_of(ref)
    root = skelsolve.root_leaf(ref, bones)
    return (bones.get(root) or {}).get("path")


def character_channels(header, curves, ref, only=None, in_place=False):
    """(OrderedDict {plug: {card layer: CURVE}}, notes) of the card's curves on `ref`: each card
    node paired by leaf name (`curvedata.pair_nodes`), kept only when the save's rule keeps it for
    the card's members on this target (`curvecapture.character_nodes` - a card cut to 1P upper /
    lower body pastes that half), Selected only's paths (`only`), In place's Main / root left out;
    a card node the target lacks, and an attribute it lacks, named."""
    bones = scene.skeleton(ref, [])[0]
    allowed = set(curvecapture.character_nodes(ref, bones, header.get("members") or ()))
    nodes = curves.get("nodes") or []
    paired, missing = curvedata.pair_nodes([node["name"] for node in nodes], target_nodes(ref),
                                           scene.leaf)
    skip = _root_node(ref, bones) if in_place else None
    channels, absent = OrderedDict(), []
    for node in nodes:
        path = paired.get(node["name"])
        if path is None or path not in allowed or path == skip:
            continue
        if only is not None and path not in only:
            continue
        for attr, per in node["attrs"].items():
            if cmds.attributeQuery(attr, node=path, exists=True):
                channels[path + "." + attr] = per
            else:
                absent.append(scene.leaf(path) + "." + attr)
    notes = []
    if missing:
        notes.append(MISSING % (len(missing), ap.target_label(ref), ap._named(missing)))
    if absent:
        notes.append(ap.NOT_POSED % (len(absent), "no such attribute", ap._named(absent)))
    return channels, notes


def objects_channels(matched):
    """(OrderedDict {plug: {card layer: CURVE}}, notes, object paths) of the card's objects paired
    with the scene's (`animapply._object_channels`): a plain curve the base's, a layered one its
    layers (`curvedata.per_layer`)."""
    channels, notes, paths = aa._object_channels(matched)
    return OrderedDict((plug, curvedata.per_layer(curve)) for plug, curve in channels.items()), \
        notes, paths


def _planned(groups, names, plan):
    """OrderedDict {(group index, plug): {card layer: (keys in target time, weighted, breakdown
    times, pre, post)}} of the picked layers' curves, each clipped to the paste's source range and
    moved to its time (`animapply._object_keys`); a layer with nothing to key there left out."""
    lo, hi = plan.frames[0][0], plan.frames[-1][0]
    planned = OrderedDict()
    for index, (_label, _noun, channels, _notes) in enumerate(groups):
        for plug, per in channels.items():
            for name in names:
                curve = per.get(name)
                if not isinstance(curve, dict):
                    continue
                stored, weighted = aa._object_keys(curve, lo, hi, plan)
                if not stored:
                    continue
                breaks = aa._breakdown_times(curve, lo, hi, plan, stored) \
                    if curve.get("keys") else []
                planned.setdefault((index, plug), OrderedDict())[name] = (
                    stored, weighted, breaks, curve.get("pre"), curve.get("post"))
    return planned


def _layers(where, records, made):
    """{card layer: target layer name or None}: the layers `where` says to make, made bottom to top
    in the card's order (`keys.make_layer`, each named in `made`); a namesake as found; the base
    the scene's root AFTER the makes (a scene without layers gets its root from the first one) -
    None without layers, the plain curves."""
    out = OrderedDict()
    for name, (kind, target) in where.items():
        if kind == "make":
            target = keys.make_layer(records[name])
            made.append(target)
        out[name] = target
    root = cmds.animLayer(query=True, root=True) or None
    for name, (kind, _target) in where.items():
        if kind == "base":
            out[name] = root
    return out


def _layers_text(names, layer_of, made):
    """The line's «BaseAnimation + AnimLayer2 (made)»."""
    parts = []
    for name in names:
        layer = layer_of.get(name)
        shown = scene.leaf(layer) if layer else curvedata.BASE
        parts.append(MADE % shown if layer in made else shown)
    return " + ".join(parts)


def _connect(planned, before, plan, layer, record):
    """Connect on the ONE layer pasted: each channel's pasted keys on it moved by what it showed
    at `a` before the press minus what it shows now, over the layer's weight
    (`curvedata.connect_offset`) - read AFTER the keys, so what stands above and below the layer
    is in it. A quaternion layer's rotations are no sum of eulers: skipped; weight 0: nothing to
    move. The notes said."""
    notes = []
    weight = 1.0 if (layer is None or record.get("base")) else keys._weight(layer)
    for (_index, plug), _per in planned.items():
        if record.get("rotation") == "quaternion" and plug.rsplit(".", 1)[-1] in aa.ROTATE:
            notes.append(CONNECT_QUAT % record["name"])
            continue
        offset = curvedata.connect_offset(before[plug], cmds.getAttr(plug, time=plan.a), weight)
        if offset is None:
            return [CONNECT_WEIGHT % record["name"]]
        curve = keys.curve_for(plug, layer)
        if curve is not None and abs(offset) > 1e-12:
            cmds.keyframe(curve, edit=True, relative=True, valueChange=offset,
                          time=(plan.a, plan.b))
    return notes


def paste(header, groups, options=None, progress=None):
    """(ok, line): the card's original curves of `groups` - [(target label, noun, OrderedDict
    {plug: {card layer: CURVE}}, notes)], one a character (or the card's objects) - pasted with
    `options` (the module's press). Refusals before anything is written: no layer picked, an
    empty range, a locked namesake layer."""
    options = aa._options(options)
    names = curvedata.chosen(curvedata.layer_names(header), options.layers)
    if not names:
        return False, NO_LAYER
    try:
        plan = aa._plan(header, options)
    except ValueError as error:
        return False, str(error)
    records = dict((record["name"], record) for record in curvedata.records(header))
    existing = keys.existing_layers()
    where = OrderedDict()
    for name in names:
        kind, target = curvedata.layer_target(records[name], existing)
        if kind == "refused":
            return False, keys.LOCKED % target
        where[name] = (kind, target)
    planned = _planned(groups, names, plan)
    if not planned:
        return False, NOTHING
    said = OrderedDict()
    connect = bool(options.connect) and curvedata.connect_ok(names)
    if options.connect and not connect:
        text = CONNECT_ONE % len(names)
        said[text] = text
    before = dict((plug, float(cmds.getAttr(plug, time=plan.a)))
                  for (_index, plug) in planned) if connect else {}
    title = header.get("name") or "Animation"
    recording = bool(cmds.undoInfo(query=True, state=True))
    steps = aa._Steps()
    keyed = [set() for _group in groups]
    made, done = [], []
    reached = [0] * len(plan.ops)
    cancelled = False
    layer_of = {}
    try:
        with aa._chunk(steps):
            layer_of = _layers(where, records, made)
            for name in names:
                plugs = [plug for (_index, plug), per in planned.items() if name in per]
                if plugs:
                    reached = [n + m for n, m in zip(reached, aa._ops(plan.ops, plugs,
                                                                      layer_of[name]))]
            for (index, plug), per in planned.items():
                for name, (stored, weighted, breaks, pre, post) in per.items():
                    layer = layer_of[name]
                    written = keys.write_raw(plug, layer, stored, weighted, pre, post)
                    for text in written.notes:
                        said.setdefault(text, text)
                    if written.plugs:
                        keyed[index].add(ap._owner(plug.rsplit(".", 1)[0]))
                        for text in (aa._breakdowns(plug, layer, breaks) if breaks else ()):
                            said.setdefault(text, text)
                done.append(plug)
                if progress is not None and not progress.step(
                        aa.STEP % (title, scene.leaf(plug))):
                    cancelled = True
                    break
            if connect and not cancelled:
                for text in _connect(planned, before, plan, layer_of[names[0]],
                                     records[names[0]]):
                    said.setdefault(text, text)
    except BaseException:
        aa._undo_failed(recording and steps.recorded)
        raise
    if cancelled:
        if recording:
            cmds.undo()
            return False, aa.CANCELLED
        return False, aa._kept(ap._counted(len(done), "channels"), plan, "channels", reached)
    text = _layers_text(names, layer_of, made)
    rows = []
    for index, (label, noun, _channels, notes) in enumerate(groups):
        last = index == len(groups) - 1
        rows.append({"name": "%s (original curves)" % title, "target": label,
                     "count": len(keyed[index]), "noun": noun, "layer": text,
                     "a": plan.a, "b": plan.b, "frames": plan.b - plan.a + 1,
                     "mode": options.mode, "worst": None, "worst_frame": None,
                     "notes": list(notes) + (list(said.values()) if last else []),
                     "alpha": 1.0, "mirror": False})
    return any(keyed), look.anim_status(rows)
```

The press calls `curvedata.check(curves, curvedata.layer_names(header))` in the dispatch (Step 4), so `character_channels` reads a checked file.

- [ ] **Step 4: The dispatch in `animapply.py`**

Add `from maya_poselib import curvedata` among the siblings (curvedata is pure; `curveapply` is imported LATE inside the functions below: it imports `animapply` itself). Then:

```python
def _pastes_curves(header, options):
    """Does this press paste the card's ORIGINAL curves: Paste as «Original curves» on a card that
    holds them (spec 2026-10-28)? An older card ignores the option."""
    return _options(options).paste_as == "curves" and curvedata.has_curves(header)


def _press_curves(header, frames, refs, curves, mirror=False, alpha=1.0, options=None,
                  progress=None, only=None, loose=()):
    """The press under Paste as «Original curves»: the targets of the card's own model take its
    curves layer by layer, its objects with them (`curveapply.paste`, one chunk); every other
    target - and every one when the curves cannot be read - is pasted by the bones
    (`_press_refs`, its own chunk: a mixed press is two undo steps) and the line says so. Mirror
    and Blend change values: refused."""
    from maya_poselib import curveapply
    options = _options(options)
    if mirror:
        return False, curveapply.MIRRORED
    if ap._clamp(alpha) < 1.0:
        return False, curveapply.BLENDED
    notes = []
    if curves is not None:
        try:
            curvedata.check(curves, curvedata.layer_names(header))
        except ValueError:
            curves = None
    if curves is None:
        notes.append(curveapply.UNREAD)
        same = []
    else:
        same = [ref for ref in refs if curveapply.matches(header, ref)]
    other = [ref for ref in refs if ref not in same]
    groups = []
    for ref in same:
        channels, said = curveapply.character_channels(header, curves, ref, only,
                                                       options.in_place)
        groups.append((ap.target_label(ref), "controls" if ref.kind == "rig" else "bones",
                       channels, said))
    matched = []
    if same:
        matched, onotes = _card_matched(header, loose, same, only is not None)
        if matched:
            channels, more, paths = curveapply.objects_channels(matched)
            groups.append((ap._counted(len(paths), "objects"), "objects", channels,
                           list(onotes) + list(more)))
    oks, lines = [], []
    if groups:
        ok, line = curveapply.paste(header, groups, options, progress)
        oks.append(ok)
        lines.append(line)
    if other:
        rest = dict(header, objects=[]) if matched else header
        ok, line = _press_refs(rest, frames, other, False, 1.0,
                               options._replace(paste_as="retarget"), progress, only,
                               () if matched else loose)
        oks.append(ok)
        lines.append(line)
        if curves is not None:
            notes.append(curveapply.RETARGETED % ", ".join(ap.target_label(r) for r in other))
    return any(oks), " | ".join(lines + notes)
```

`apply` gains `curves=None` (docstring: «`curves` - the card's `curves.json.gz` (`store.read_curves`) for Paste as «Original curves»; None for any other paste, or when it cannot be read»), and after `refs, refusal = _targets(selection)` / its refusal:

```python
    if _pastes_curves(header, options):
        return _press_curves(header, frames, refs, curves, mirror, alpha, options, progress,
                             ap.selected_nodes(selection) if only else None, loose)
```

`apply_onto(header, frames, root, mirror=False, alpha=1.0, options=None, progress=None, curves=None)` — before its `_press_refs` call:

```python
    if _pastes_curves(header, options):
        return _press_curves(header, frames, [ref], curves, mirror, alpha, options, progress)
```

`drop_floor(header, frames, point, mirror=False, options=None, progress=None, curves=None)` — its `onto` lambda passes `curves=curves` to `apply_onto`.

`_press_objects` — right after `options = _options(options)`:

```python
    if _pastes_curves(header, options):
        from maya_poselib import curveapply
        if ap._clamp(alpha) < 1.0:
            return False, curveapply.BLENDED
        if matched is None:
            matched, notes, refusal = _objects_pairs(header, selection)
            if refusal:
                return False, refusal
        else:
            notes = []
        channels, more, paths = curveapply.objects_channels(matched)
        return curveapply.paste(header, [(ap._counted(len(paths), "objects"), "objects",
                                          channels, list(lead) + list(notes) + list(more))],
                                options, progress)
```

`Blend.start` — first lines of its body:

```python
        if _pastes_curves(header, options):
            from maya_poselib import curveapply
            return curveapply.BLENDED
```

Add to the module docstring: «Paste as «Original curves» (2026-10-28) is `curveapply`'s press: `apply`, `apply_onto`, `drop_floor` and an objects card's press hand it over (`_press_curves`), the targets of another model going through the bones as before.»

- [ ] **Step 5: Run the tests**

Run: `... -m unittest tests.test_poselib_curveapply tests.test_poselib_animapply -v`
Expected: all OK.

- [ ] **Step 6: Commit**

```powershell
git add SkeldarAnim/maya_poselib/curveapply.py SkeldarAnim/maya_poselib/animapply.py tests/test_poselib_curveapply.py tests/test_poselib_animapply.py
git commit -F $env:TEMP\skeldar_msg.txt   # "feat(poselib): paste a card's original curves layer by layer onto its own rig"
```

---

### Task 8: The window — Paste as, the layer checklist, Save and paste with curves

**Files:**
- Modify: `SkeldarAnim/maya_poselib/look.py` (`details`: one line), `SkeldarAnim/maya_poselib/window.py` (constants, `remembered_options`, `press_steps`, `Scene._save_animation/update/_curves/apply/apply_onto/drop_floor`, `PoseWindow._build_options/_load_options/options/pick/show_targets` + new `_paste_as_changed/_fill_layers/_layer_toggled/_sync_curves/_mirrored`)
- Test: `tests/test_poselib_look.py`, `tests/test_poselib_window.py`

**Interfaces:**
- Consumes: `curvedata.has_curves/layer_names` (Task 2), `store.read_curves` / `write(curves=)` / `replace(curves=)` (Task 4), `animdata.Options.paste_as/layers` (Task 5), `animcapture.build_clip` (Task 6), `animapply.apply/apply_onto/drop_floor(curves=)` (Task 7).
- Produces: `PASTE_AS_VAR = "skeldarPoseLibraryPasteAs"`, `PASTE_AS_LABELS`, `CURVES_OFF`; the window's `paste_as_buttons`, `paste_as_row`, `layer_box`, `layer_checks`; `options()` gains `"paste_as"` and `"layers"`.

- [ ] **Step 1: Write the failing tests**

`tests/test_poselib_look.py`:

```python
class CurvesDetails(unittest.TestCase):

    def test_a_card_with_curves_names_its_layers(self):
        data = {"format": "skeldar.anim", "kind": "character", "start": 0.0, "end": 9.0,
                "frames": 10, "curves": {"layers": [{"name": "BaseAnimation", "base": True},
                                                    {"name": "AnimLayer1"}], "nodes": 4}}
        lines = look.details(None, data)
        self.assertIn("original curves %s BaseAnimation, AnimLayer1" % look.DOT, lines)

    def test_a_card_without_says_nothing_of_curves(self):
        data = {"format": "skeldar.anim", "kind": "character", "start": 0.0, "end": 9.0,
                "frames": 10}
        self.assertFalse(any("original curves" in line for line in look.details(None, data)))
```

`tests/test_poselib_window.py` — first, every dict literal in this file that holds `"in_place":` gains `"paste_as": "retarget", "layers": None` (the options now carry both; `AnimOptions.WHOLE` is one of them). Then `FakeModules` gains `build_clip`, and `install()` puts it on the fake `animcapture` namespace beside `build_animation`:

```python
    def build_clip(self, selection=None, regions=None, start=None, end=None, progress=None):
        header, frames, note = self.build_animation(selection, regions, start, end, progress)
        import types
        return types.SimpleNamespace(header=header, frames=frames, curves=self.curves, note=note)
```

(with `self.curves = None` in `__init__` and `build_clip=self.build_clip` in the `animcapture` SimpleNamespace). Then a new class:

```python
class CurvesOptions(AnimCase):
    """A card holding original curves (spec 2026-10-28): its Paste as row, its layer checklist,
    the options greyed under «Original curves»."""

    def setUp(self):
        AnimCase.setUp(self)
        from maya_poselib import curvedata
        layers = [curvedata.layer_record(curvedata.BASE, base=True),
                  curvedata.layer_record("AnimLayer1")]
        data = dict(anim_data("Layered"), curves=curvedata.summary(layers, 2))
        self.layered = store.write(self.root, "", "Layered", data, frames=FRAMES,
                                   curves={"version": 1, "nodes": []})
        self.win.refresh()

    def test_the_row_shows_only_for_a_card_with_curves(self):
        self.win.pick(self.walk)
        self.assertFalse(self.win.paste_as_row.isVisible())
        self.win.pick(self.layered)
        self.assertTrue(self.win.paste_as_row.isVisible())
        self.assertFalse(self.win.layer_box.isVisible())          # Retarget by default
        self.assertEqual(list(self.win.layer_checks), ["BaseAnimation", "AnimLayer1"])

    def test_original_curves_lists_the_layers_and_greys_what_changes_values(self):
        self.win.pick(self.layered)
        self.win.paste_as_buttons["curves"].click()
        self.assertTrue(self.win.layer_box.isVisible())
        self.assertFalse(self.win.keys_buttons["every"].isEnabled())
        self.assertFalse(self.win.mirror.isEnabled())
        self.assertFalse(self.win.blend.isEnabled())
        self.assertFalse(self.win.connect_box.isEnabled())         # two layers picked
        self.assertEqual((self.win.options()["paste_as"], self.win.options()["layers"]),
                         ("curves", None))
        self.win.layer_checks["BaseAnimation"].click()
        self.assertEqual(self.win.options()["layers"], ["AnimLayer1"])
        self.assertTrue(self.win.connect_box.isEnabled())          # one layer: Connect works
        self.assertEqual(self.scene.options.get(pw.PASTE_AS_VAR), "curves")

    def test_the_last_layer_stays_on(self):
        self.win.pick(self.layered)
        self.win.paste_as_buttons["curves"].click()
        self.win.layer_checks["BaseAnimation"].click()
        self.win.layer_checks["AnimLayer1"].click()
        self.assertTrue(self.win.layer_checks["AnimLayer1"].isChecked())

    def test_back_to_retarget_gives_everything_back(self):
        self.win.pick(self.layered)
        self.win.paste_as_buttons["curves"].click()
        self.win.paste_as_buttons["retarget"].click()
        self.assertTrue(self.win.keys_buttons["every"].isEnabled())
        self.assertTrue(self.win.mirror.isEnabled())
        self.assertTrue(self.win.connect_box.isEnabled())
```

`RealScene` (same file) — two tests (`self.scene.option` is the real one there: give it what the test needs with `self.scene.option = lambda name, default=None: default`):

```python
    def test_a_curves_paste_reads_the_cards_curves_and_hands_them_on(self):
        from maya_poselib import curvedata
        layers = [curvedata.layer_record(curvedata.BASE, base=True)]
        curves = {"version": 1, "nodes": []}
        path = store.write(self.root, "", "Layered",
                           dict(anim_data("Layered"), curves=curvedata.summary(layers, 0)),
                           frames=FRAMES, curves=curves)
        self.scene.apply(path, False, options={"paste_as": "curves"})
        entry = self.logged("animapply.apply")[-1]
        self.assertEqual(entry[4].get("curves"), curves)

    def test_a_retarget_paste_hands_no_curves(self):
        self.scene.apply(self.walk, False, options={"paste_as": "retarget"})
        self.assertNotIn("curves", self.logged("animapply.apply")[-1][4])

    def test_save_writes_the_clips_curves(self):
        self.fakes.curves = {"version": 1, "nodes": []}
        path, _text = self.scene._save_animation("Clip", "", None, None, {"start": 3, "end": 9})
        self.assertEqual(store.read_curves(path), {"version": 1, "nodes": []})
```

- [ ] **Step 2: Run them to see them fail**

Run: `$env:QT_QPA_PLATFORM='offscreen'; ... -m unittest tests.test_poselib_look tests.test_poselib_window -v`
Expected: the new tests FAIL / ERROR (`AttributeError: 'PoseWindow' object has no attribute 'paste_as_row'`, the details line missing, `curves` not handed on).

- [ ] **Step 3: `look.details`** — after the clip line is added (`clip`), add the curves line when `data` holds a `curves` block (look imports no sibling, so it reads the block itself):

```python
def _curves_line(data):
    """«original curves · BaseAnimation, AnimLayer1» of a card that keeps its source's curves
    (spec 2026-10-28), "" otherwise."""
    block = data.get("curves") if isinstance(data, dict) else None
    layers = block.get("layers") if isinstance(block, dict) else None
    if not isinstance(layers, list) or not layers:
        return ""
    names = [layer.get("name") for layer in layers
             if isinstance(layer, dict) and isinstance(layer.get("name"), str)]
    return "original curves %s %s" % (DOT, ", ".join(names)) if names else ""
```

and in `details`, right after the line list gets the clip line, `lines.append(_curves_line(data))` (the function already leaves empty lines out — follow how it builds its list; add the docstring example line «original curves · BaseAnimation, AnimLayer1» under the animation example).

- [ ] **Step 4: The window** — constants beside `KEYS_VAR`:

```python
PASTE_AS_VAR = "skeldarPoseLibraryPasteAs"     # Paste as: "retarget" | "curves" (2026-10-28)
PASTE_AS_LABELS = {"character": (("retarget", "Retarget"), ("curves", "Original curves")),
                   "objects": (("retarget", "Active layer"), ("curves", "Original curves"))}
CURVES_OFF = "Off for original curves - they are pasted as they were keyed"
```

`remembered_options` reads `"paste_as": read(PASTE_AS_VAR)` too.

`press_steps(header, options, current, curves=None)` — first lines:

```python
    if _as_options(options).paste_as == "curves" and curvedata.has_curves(header):
        if curves is not None:
            return max(1, sum(len(node.get("attrs") or {}) for node in curves.get("nodes") or ()))
        return max(1, sum(len((record or {}).get("attrs") or {})
                          for record in header.get("objects") or ()))
```

(import `curvedata` at the top of `window.py` beside `animdata` — it is pure.)

`Scene` — a reader and the presses:

```python
    def _curves(self, path, options):
        """The card's `curves.json.gz` when the press pastes Original curves of a CHARACTER card
        (an objects card keeps its curves in the header), else None - a file that cannot be read
        hands None too, and the press retargets and says so."""
        if _as_options(options).paste_as != "curves" or not store.is_anim(path):
            return None
        try:
            header = store.read(path)
            if header.get("kind") == "objects" or not curvedata.has_curves(header):
                return None
            return store.read_curves(path)
        except ValueError:
            return None
```

In `apply`, `apply_onto` and `drop_floor` (the animation branches), read it first and hand it on ONLY when there is one (the fakes compare kwargs):

```python
            curves = self._curves(path, options)
            extra = {"curves": curves} if curves is not None else {}
            return self._paste_read(lambda header, frames, progress: animapply.apply(
                header, frames, mirror=mirror, options=options, progress=progress,
                **dict(_only(only), **extra)), path, options)
```

(`apply_onto`: `animapply.apply_onto(header, frames, root, mirror=mirror, options=options, progress=progress, **extra)`; `drop_floor`: `animapply.drop_floor(header, frames, point, mirror=mirror, options=options, progress=progress, **extra)`), and `_paste` / `_paste_read` pass `curves` to `press_steps`: give both a `curves=None` parameter, `steps = press_steps(header, options, _current_time(), curves)`, and the three callers pass `curves=curves`.

`_save_animation` — `clip = animcapture.build_clip(regions=regions, start=start, end=end, progress=progress)`, then `header, frames, note = clip.header, clip.frames, clip.note` and `store.write(..., frames=frames, preview=sheet if made else None, curves=clip.curves)`. `update` — `clip = animcapture.build_clip(start=start, end=end, progress=progress)`; `header, frames, note = clip.header, clip.frames, clip.note`; `store.replace(path, header, frames=frames, curves=clip.curves)`.

`PoseWindow._build_options` — after the Keys row, before `return frame`:

```python
            track, self.paste_as_buttons = self._segments(
                "skeldarPosePasteAs_", PASTE_AS_LABELS["character"],
                lambda value: self._paste_as_changed(value))
            self.paste_as_buttons["retarget"].setToolTip(
                "The card's bones solved onto any character, keyed on the active layer")
            self.paste_as_buttons["curves"].setToolTip(
                "The card's own keys and layers - onto a rig of the card's own model")
            self.paste_as_row = QtWidgets.QWidget()
            row = QtWidgets.QHBoxLayout(self.paste_as_row)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(s(6))
            row.addWidget(self._label("Paste as", "context"))
            row.addWidget(track, 1)
            column.addWidget(self.paste_as_row)
            self.layer_box = QtWidgets.QWidget()
            self.layer_box.setObjectName("skeldarPoseCurveLayers")
            self.layer_flow = QtWidgets.QVBoxLayout(self.layer_box)
            self.layer_flow.setContentsMargins(s(8), 0, 0, 0)
            self.layer_flow.setSpacing(s(2))
            self.layer_checks = OrderedDict()
            column.addWidget(self.layer_box)
```

(add `from collections import OrderedDict` to `window.py`'s imports if it lacks it). New methods next to `_option_changed`:

```python
        def _paste_as_changed(self, value):
            """Paste as clicked: remembered, the blend put back, the options greyed for it."""
            self._option_changed(PASTE_AS_VAR, value)
            self._sync_curves()

        def _fill_layers(self, names):
            """The checklist of the picked card's layers, every one on (a pick is per card, never
            remembered)."""
            for check in self.layer_checks.values():
                self.layer_flow.removeWidget(check)
                check.deleteLater()
            self.layer_checks = OrderedDict()
            for name in names:
                check = QtWidgets.QCheckBox(name)
                check.setObjectName("skeldarPoseCurveLayer_" + name)
                check.setChecked(True)
                check.toggled.connect(lambda _on, name=name: self._layer_toggled(name))
                self.layer_flow.addWidget(check)
                self.layer_checks[name] = check

        def _layer_toggled(self, name):
            """A layer unticked: one always stays on (a paste of no layer is no paste)."""
            if not any(check.isChecked() for check in self.layer_checks.values()):
                self.layer_checks[name].setChecked(True)
                return
            self.blend_reset(RESET_OPTION)
            self._sync_curves()

        def _curves_on(self):
            data = self.picked_data if isinstance(self.picked_data, dict) else {}
            return curvedata.has_curves(data) and \
                self._lit(self.paste_as_buttons, "retarget") == "curves"

        def _sync_curves(self):
            """The Paste as row for a card with curves (its labels the card kind's), the layer
            checklist under «Original curves», and what changes values greyed there with a tooltip
            that says why: Keys, Mirror, Blend - and Connect unless ONE layer is picked. Nothing
            before the options block is built (`show_targets` can run first)."""
            if not hasattr(self, "paste_as_buttons"):
                return
            data = self.picked_data if isinstance(self.picked_data, dict) else {}
            kind = "objects" if data.get("kind") == "objects" else "character"
            for value, label in PASTE_AS_LABELS[kind]:
                self.paste_as_buttons[value].setText(label)
            self.paste_as_row.setVisible(curvedata.has_curves(data))
            curves = self._curves_on()
            self.layer_box.setVisible(curves)
            picked = [name for name, check in self.layer_checks.items() if check.isChecked()]
            card = self._card(self.picked) if self.picked else None
            for widget, on in ([(button, not curves) for button in self.keys_buttons.values()]
                               + [(self.mirror, not curves),
                                  (self.blend, card is not None and not curves),
                                  (self.connect_box, not curves or len(picked) == 1)]):
                if widget.property("skTip") is None:
                    widget.setProperty("skTip", widget.toolTip())
                widget.setEnabled(on)
                widget.setToolTip(widget.property("skTip") if on else CURVES_OFF)

        def _mirrored(self):
            """Mirror as a press takes it: off while it is greyed (Original curves)."""
            return self.mirror.isChecked() and self.mirror.isEnabled()
```

`_load_options`: `self.paste_as_buttons[opts.paste_as].setChecked(True)`.

`options()`: two more fields:

```python
            picked = [name for name, check in self.layer_checks.items() if check.isChecked()]
            ...
                    "in_place": self.in_place.isChecked(),
                    "paste_as": self._lit(self.paste_as_buttons, "retarget"),
                    "layers": None if len(picked) == len(self.layer_checks) else picked}
```

`pick()`: after `self.anim_options.setVisible(anim)` add `self._fill_layers(curvedata.layer_names(self.picked_data) if anim else [])`. `unpick()`: `self._fill_layers([])`. `show_targets()`: last line `self._sync_curves()` (it sets `self.blend` enabled first; the sync greys it after). Replace the three reads of Mirror for a press (`self.mirror.isChecked()` in the apply / drag / blend paths, around the lines that read `mirror = self.mirror.isChecked()` and `self.scene.blend_start(path, self.mirror.isChecked(), ...)`) with `self._mirrored()`.

- [ ] **Step 5: Run the tests**

Run: `$env:QT_QPA_PLATFORM='offscreen'; ... -m unittest tests.test_poselib_look tests.test_poselib_window -v`
Expected: all OK.

- [ ] **Step 6: The whole suite**

Run: `$env:QT_QPA_PLATFORM='offscreen'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t .`
Expected: `OK` (CLAUDE.md's count plus the new tests; no failure anywhere else - the purity pins included).

- [ ] **Step 7: Commit**

```powershell
git add SkeldarAnim/maya_poselib/look.py SkeldarAnim/maya_poselib/window.py tests/test_poselib_look.py tests/test_poselib_window.py
git commit -F $env:TEMP\skeldar_msg.txt   # "feat(poselib): the window - Paste as, the layer checklist, Save and paste with curves"
```

---

### Task 9: End to end in mayapy

**Files:**
- Create: `docs/superpowers/plans/verify_poselib_curves.py`

**Interfaces:**
- Consumes: everything above, through the window's road: `animcapture.build_clip` → `store.write(curves=)` → `store.read` / `read_frames` / `read_curves` → `animapply.apply(..., options=..., curves=...)`.

- [ ] **Step 1: Write the verify**

```python
"""Original curves and layers in animation cards (2026-10-28), end to end, mayapy STANDALONE.

Never in the animator's Maya: it adds rigs and layers and keys them. Run with a scratch
MAYA_APP_DIR:

    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' verify_poselib_curves.py [out]

Rig A (Manny_Rig) keyed on the base - FKWrist_R rotateZ with a weighted fixed tangent, a breakdown
and cycle post-infinity, Main translateZ - plus an additive layer AddFix (FKWrist_R rotateX) and an
override layer OverHand at weight 0.5 (FKElbow_R rotateY). Saved whole body over 0..30:
  save      the header names BaseAnimation, AddFix, OverHand; the curves keep FKWrist_R and Main;
            the save of the whole rig takes under 2 s;
  same      onto rig B (same scene: AddFix / OverHand exist, same modes): every saved curve equal
            on B's curve of its layer, key for key - time, value, tangent types, angles, weights,
            breakdowns, infinity;
  one       onto rig C, only AddFix picked, Merge at frame 100: C's base untouched, AddFix keyed
            from 100;
  fresh     a new scene, one rig: AddFix and OverHand MADE with the card's mode, weight, mute;
  mode      a scene whose AddFix is an override: a new additive layer made beside it, said;
  undo      one cmds.undo() after the fresh paste: the keys AND the layers it made gone;
  other     a Creep rig in the same press: retargeted, the line says so;
  objects   a locator keyed on the base + AddFix saved as an objects card: pasted per layer.
Every gate prints PASS/FAIL, the run ends SUMMARY x/y.
"""

import io
import os
import sys
import tempfile
import time
import traceback

import maya.standalone
maya.standalone.initialize(name="python")

import maya.cmds as cmds  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.normpath(os.environ.get("POSELIB_PLUGIN") or
                          os.path.join(HERE, "..", "..", "..", "SkeldarAnim"))
sys.path.insert(0, PLUGIN)
for _plugin in ("matrixNodes", "quatNodes", "fbxmaya"):
    cmds.loadPlugin(_plugin, quiet=True)
cmds.currentUnit(time="ntsc")
cmds.undoInfo(state=True, infinity=True)
cmds.autoKeyframe(state=False)

import maya_rigs  # noqa: E402
from maya_scenesetup import catalog, character  # noqa: E402
from maya_poselib import animapply, animcapture, curvedata, keys, store  # noqa: E402

OUT = io.open(sys.argv[1], "w", encoding="utf-8") if len(sys.argv) > 1 else None
RESULTS = []
LIBRARY = tempfile.mkdtemp(prefix="skeldar_curves_lib_")


def say(*parts):
    line = " ".join(str(p) for p in parts)
    print(line)
    if OUT is not None:
        OUT.write(line + "\n")
        OUT.flush()


def gate(name, ok, value=""):
    RESULTS.append(bool(ok))
    say("%s %s %s" % ("PASS" if ok else "FAIL", name, value))


def add_rig(key="Manny_Rig"):
    before = set(r.namespace for r in maya_rigs.rigs())
    character.add_character(catalog.character_by_key(key))
    cmds.select(clear=True)
    return [r for r in maya_rigs.rigs() if r.namespace not in before][0]


def ctrl(rig, leaf):
    return cmds.ls(rig.namespace + ":" + leaf, long=True)[0]


def curve_table(curve):
    """Every key of `curve`: (time, value, in type, out type, in angle, in weight, out angle, out
    weight, breakdown), rounded - and its infinity."""
    times = cmds.keyframe(curve, query=True, timeChange=True) or []
    rows = []
    for t in times:
        span = (t, t)
        value = cmds.keyframe(curve, query=True, time=span, valueChange=True)[0]
        tan = [cmds.keyTangent(curve, query=True, time=span, **{f: True})[0]
               for f in ("inTangentType", "outTangentType", "inAngle", "inWeight", "outAngle",
                         "outWeight")]
        brk = bool(cmds.keyframe(curve, query=True, time=span, breakdown=True))
        rows.append((round(t, 4), round(value, 4), tan[0], tan[1], round(tan[2], 3),
                     round(tan[3], 3), round(tan[4], 3), round(tan[5], 3), brk))
    return rows, (cmds.getAttr(curve + ".preInfinity"), cmds.getAttr(curve + ".postInfinity"))


def save(selection, name, start=0, end=30):
    clip = animcapture.build_clip(selection, start=start, end=end)
    if clip.header is None:
        raise RuntimeError(clip.note)
    path = store.write(LIBRARY, "", name, clip.header, frames=clip.frames, curves=clip.curves)
    header = store.read(path)
    frames = store.read_frames(path) if clip.frames is not None else None
    curves = store.read_curves(path) if clip.curves is not None else None
    return header, frames, curves, clip


def paste(card, selection, **options):
    header, frames, curves, _clip = card
    options.setdefault("paste_as", "curves")
    return animapply.apply(header, frames, selection=selection, options=options, curves=curves)


def same_curves(a, b, layer):
    """Every curve of `a`'s keyed channels on `layer` equal on `b` (key for key, infinity)."""
    bad = []
    for leaf in ("FKWrist_R", "FKElbow_R", "Main"):
        for attr in ("rotateX", "rotateY", "rotateZ", "translateZ"):
            src = keys.curve_for(ctrl(a, leaf) + "." + attr, layer)
            if src is None:
                continue
            dst = keys.curve_for(ctrl(b, leaf) + "." + attr, layer)
            if dst is None or curve_table(src) != curve_table(dst):
                bad.append((leaf, attr, layer))
    return bad


try:
    cmds.playbackOptions(minTime=0, maxTime=120, animationStartTime=0, animationEndTime=120)
    cmds.currentTime(0)
    a, b, c = add_rig(), add_rig(), add_rig()
    wrist, elbow, main = ctrl(a, "FKWrist_R"), ctrl(a, "FKElbow_R"), a.main
    for t, v in ((0, 0.0), (10, 40.0), (20, -10.0), (30, 25.0)):
        cmds.setKeyframe(wrist, attribute="rotateZ", time=t, value=v)
        cmds.setKeyframe(main, attribute="translateZ", time=t, value=t * 5.0)
    rz = keys.curve_for(wrist + ".rotateZ", None)
    cmds.keyTangent(rz, edit=True, weightedTangents=True)
    cmds.keyTangent(rz, edit=True, time=(10, 10), inAngle=15.0, outAngle=-5.0, inWeight=2.0,
                    outWeight=4.0, lock=False, weightLock=False)
    cmds.keyframe(rz, edit=True, time=(20, 20), breakdown=True)
    cmds.setAttr(rz + ".postInfinity", 3)
    add = cmds.animLayer("AddFix")
    cmds.animLayer(add, edit=True, attribute=[wrist + ".rotateX"])
    for t, v in ((0, 0.0), (15, 12.0), (30, 0.0)):
        cmds.setKeyframe(wrist, attribute="rotateX", time=t, value=v, animLayer=add)
    over = cmds.animLayer("OverHand", override=True)
    cmds.animLayer(over, edit=True, weight=0.5, attribute=[elbow + ".rotateY"])
    for t, v in ((0, 30.0), (30, -30.0)):
        cmds.setKeyframe(elbow, attribute="rotateY", time=t, value=v, animLayer=over)

    # ---- save
    began = time.time()
    card = save([main], "Layered")
    took = time.time() - began
    header, _frames, curves, clip = card
    gate("save: the header names the layers", curvedata.layer_names(header) ==
         [curvedata.BASE, "AddFix", "OverHand"], curvedata.layer_names(header))
    names = set(node["name"] for node in curves["nodes"])
    gate("save: the curves keep FKWrist_R and Main", {"FKWrist_R", "Main"} <= names,
         sorted(names)[:8])
    gate("save: the whole rig under 2 s", took < 2.0, "%.2f s" % took)
    say("save line:", clip.note)
    arm = save([wrist], "Arm")
    arm_names = set(node["name"] for node in arm[2]["nodes"])
    gate("save: an arm card keeps the arm's controls, not Main",
         "FKWrist_R" in arm_names and "Main" not in arm_names, sorted(arm_names))

    # ---- same scene, rig B
    ok, line = paste(card, [b.main])
    say("same:", line)
    gate("same: pasted", ok)
    for layer in (cmds.animLayer(query=True, root=True), add, over):
        gate("same: B equals A on %s" % layer, not same_curves(a, b, layer),
             same_curves(a, b, layer))

    # ---- rig C, AddFix only, Merge at 100
    cmds.currentTime(100)
    base_before = keys.curve_for(ctrl(c, "FKWrist_R") + ".rotateZ", None)
    ok, line = paste(card, [c.main], layers=["AddFix"], mode="merge")
    say("one:", line)
    gate("one: C's base untouched", keys.curve_for(ctrl(c, "FKWrist_R") + ".rotateZ",
                                                    cmds.animLayer(query=True, root=True)) == base_before)
    rx = keys.curve_for(ctrl(c, "FKWrist_R") + ".rotateX", add)
    gate("one: AddFix keyed from 100", rx is not None and
         (cmds.keyframe(rx, query=True, timeChange=True) or [None])[0] == 100.0)

    # ---- Insert at 90 on the same layer: the keys from 90 on move the clip's 31 frames later
    cmds.currentTime(90)
    ok, line = paste(card, [c.main], layers=["AddFix"], mode="insert")
    say("insert:", line)
    rx = keys.curve_for(ctrl(c, "FKWrist_R") + ".rotateX", add)
    times = cmds.keyframe(rx, query=True, timeChange=True) or []
    gate("insert: the old 100 moved to 131, the clip keyed from 90",
         131.0 in times and 90.0 in times, times)

    # ---- other model in the same press
    creep = add_rig("Creep_Rig")
    ok, line = paste(card, [b.main, creep.main])
    say("other:", line)
    gate("other: the Creep retargeted and said", "retargeted" in line and "Creep" in line, line)

    # ---- a fresh scene: the layers are made
    cmds.file(new=True, force=True)
    cmds.currentTime(0)
    d = add_rig()
    ok, line = paste(card, [d.main])
    say("fresh:", line)
    layers = keys.layer_stack()
    gate("fresh: AddFix and OverHand made", "AddFix" in layers and "OverHand" in layers, layers)
    gate("fresh: OverHand is an override at 0.5",
         cmds.animLayer("OverHand", query=True, override=True)
         and abs(cmds.animLayer("OverHand", query=True, weight=True) - 0.5) < 1e-6)
    gate("fresh: the line says made", "(made)" in line, line)

    # ---- undo
    cmds.undo()
    gate("undo: the layers made are gone", "AddFix" not in (keys.layer_stack() or []),
         keys.layer_stack())
    gate("undo: the keys are gone", keys.curve_for(ctrl(d, "FKWrist_R") + ".rotateZ", None) is None)

    # ---- a namesake of another mode
    fix = cmds.animLayer("AddFix", override=True)
    ok, line = paste(card, [d.main])
    made = [name for name in keys.layer_stack() if name.startswith("AddFix") and name != fix]
    gate("mode: a new additive AddFix beside the override one", len(made) == 1 and not
         cmds.animLayer(made[0], query=True, override=True), made)

    # ---- objects
    cmds.file(new=True, force=True)
    loc = cmds.spaceLocator(name="prop")[0]
    for t, v in ((0, 0.0), (10, 10.0)):
        cmds.setKeyframe(loc, attribute="translateY", time=t, value=v)
    layer = cmds.animLayer("PropFix")
    cmds.animLayer(layer, edit=True, attribute=[loc + ".translateY"])
    cmds.setKeyframe(loc, attribute="translateY", time=5, value=20.0, animLayer=layer)
    objects = save([loc], "Prop", 0, 10)
    gate("objects: the header names PropFix", "PropFix" in curvedata.layer_names(objects[0]))
    cmds.file(new=True, force=True)
    loc = cmds.spaceLocator(name="prop")[0]
    ok, line = animapply.apply(objects[0], None, selection=[loc],
                               options={"paste_as": "curves"})
    say("objects:", line)
    gate("objects: PropFix made and keyed", "PropFix" in keys.layer_stack() and
         keys.curve_for(cmds.ls(loc, long=True)[0] + ".translateY", "PropFix") is not None, line)
except Exception:                                            # noqa: BLE001
    say(traceback.format_exc())
    RESULTS.append(False)
say("SUMMARY %d/%d" % (sum(RESULTS), len(RESULTS)))
maya.standalone.uninitialize()
```

- [ ] **Step 2: Run it**

```powershell
$env:MAYA_APP_DIR = "$env:TEMP\skeldar_curves_verify"; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs\superpowers\plans\verify_poselib_curves.py "$env:TEMP\verify_curves.txt"
```

Expected: `SUMMARY n/n`, no FAIL. A FAIL is a bug in Tasks 2-8: use superpowers:systematic-debugging, fix it in its task's files (with a unit test that pins it), re-run. Do not loosen a gate to pass.

**Only if «the whole rig under 2 s» FAILS** (the spec's budget): most curves of a clip lie wholly inside the saved range, and those need no duplicate - only a curve the range CUTS needs the shape-keeping end keys. In `animcapture.py` add, and pass it as `copy` in `_character_curves` and `object_curves`' layered read instead of `_copied`:

```python
def _copied_fast(curve, start, end):
    """`_copied`'s CURVE without its duplicate when every key of `curve` stands inside
    [start, end] - nothing to cut, so the scene's curve is only READ (the 2 s budget, spec
    2026-10-28); a curve the range cuts goes through `_copied`."""
    times = cmds.keyframe(curve, query=True, timeChange=True) or []
    if not times or min(times) < start or max(times) > end:
        return _copied(curve, start, end)
    span = (start, end)
    pairs = cmds.keyframe(curve, query=True, time=span, timeChange=True, valueChange=True) or []
    columns = [cmds.keyTangent(curve, query=True, time=span, **{flag: True}) or []
               for flag in _TANGENTS]
    weighted = bool((cmds.keyTangent(curve, query=True, weightedTangents=True) or [False])[0])
    breakdown = [float(t) for t in
                 cmds.keyframe(curve, query=True, time=span, breakdown=True) or []]
    out = []
    for index, (time, value) in enumerate(zip(pairs[0::2], pairs[1::2])):
        in_type, out_type, in_angle, in_weight, out_angle, out_weight = (
            column[index] for column in columns)
        out.append([float(time), float(value), str(in_type), str(out_type), float(in_angle),
                    float(in_weight), float(out_angle), float(out_weight)])
    return {"keys": out, "weighted": weighted, "breakdown": breakdown}
```

with a unit test in `tests/test_poselib_animcapture.py` (a fake `cmds` whose curve holds keys 0/10 asked over 0..10: no `duplicate` call; over 2..8: `duplicate` called), then re-run the verify.

- [ ] **Step 3: The other poselib verifies still pass** (nothing they press changed by default)

```powershell
$env:MAYA_APP_DIR = "$env:TEMP\skeldar_curves_verify"; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs\superpowers\plans\verify_poselib_anim.py "$env:TEMP\verify_anim.txt"
$env:MAYA_APP_DIR = "$env:TEMP\skeldar_curves_verify"; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs\superpowers\plans\verify_poselib_objects.py "$env:TEMP\verify_objects.txt"
```

Expected: their SUMMARY as CLAUDE.md records it (anim 113/113, objects all PASS).

- [ ] **Step 4: Commit**

```powershell
git add docs/superpowers/plans/verify_poselib_curves.py
git commit -F $env:TEMP\skeldar_msg.txt   # "test(poselib): verify original curves and layers end to end (n/n)"
```

---

### Task 10: The record — CLAUDE.md and the spec

**Files:**
- Modify: `CLAUDE.md` (a new section after «The Pose Library: compact, Selected only, toned cards, a blend that holds (2026-10-15)»), `docs/superpowers/specs/2026-10-28-pose-library-curves-and-layers-design.md` (a «Measured» section)

- [ ] **Step 1: The CLAUDE.md section** — written as the other Pose Library sections are: the animator's request quoted, what a card now holds (`curves.json.gz`, the header's `curves` block), Paste as and the layer checklist, which target takes the curves, how layers pair and when one is made, Connect's one-layer rule, the mixed press's two undo steps, the raw-key road (`keys.write_raw`) with Task 1's measured line, the proof (Task 9's SUMMARY, the unit-test count from Task 8 Step 6) and what was NOT exercised (a GUI Maya; scene tabs on — the adopt-on-idle of a made layer is the Tools' road, not run here).

- [ ] **Step 2: The spec's «Measured» section** — Task 1's facts (the raw road, the plug spelling, the enums) and Task 9's numbers (the save's time on the whole rig, the gates).

- [ ] **Step 3: Commit**

```powershell
git add CLAUDE.md docs/superpowers/specs/2026-10-28-pose-library-curves-and-layers-design.md
git commit -F $env:TEMP\skeldar_msg.txt   # "docs(poselib): original curves and layers - the section and the measured facts"
```
