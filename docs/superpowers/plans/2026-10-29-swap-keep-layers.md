# A rig swapped for another keeps its layers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When a character carrying animation layers is swapped for another, ask whether to keep
the layers (each retargeted in turn, keys only where that layer had them) or to bake the
animation flat as today; a rig in 1P comes out in 1P.

**Architecture:** A new `maya_scenesetup/swaplayers.py` holds the pure rules (the cuts, the key
times, the question's text) and the scene half (the mutes, the capture off the retargeted rig,
the write bottom to top through `maya_poselib.keys.write`). `swap.py` keeps owning the retarget
plumbing (`bake_copy`, `_onto_rig`, `_onto_skeleton`) and gains the question plus the loop's two
entry points. The 1P road is one retarget of the 3P take plus `maya_tools.firstperson.setup`.

**Tech Stack:** Maya 2027 `cmds`, `maya_poselib.keys` (the layer writer),
`maya_uebridge.rigimport` / `skeletonimport` (the retarget), `maya_tools.firstperson` (1P),
stdlib unittest under mayapy.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-10-29-swap-keep-layers-design.md`.
- Tests run under mayapy only: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v`. There is no system Python.
- Buttons, verbatim: `KEEP = "Keep the layers"`, `BAKE = "Bake the animation"`, `CANCEL = "Cancel"`.
- Every layer value is written with `maya_poselib.keys.write` - Maya's own `setKeyframe -animLayer -value <final>` arithmetic (trap 205). No formula of ours for additive / override / weighted / scale layers.
- A layer is made unmuted and its mute set after its keys.
- Mutes changed for a bake are restored in a `finally`.
- A scene-tab-safe base: the base layer is `cmds.animLayer(query=True, root=True)`, never `None`, when the scene holds layers (trap 279).
- No optionVar: the question is asked every time the old character has layers.
- Russian in a docstring goes through Write/Edit, never a PowerShell here-string (trap 101).

---

### Task 1: The pure rules

**Files:**
- Create: `SkeldarAnim/maya_scenesetup/swaplayers.py`
- Test: `tests/test_scenesetup_swaplayers.py`

**Interfaces:**
- Consumes: `maya_poselib.curvedata.layer_record`'s shape (`{name, base, override, weight, mute, rotation, scale}`).
- Produces: `KEEP`, `BAKE`, `CANCEL`, `BUTTONS`, `answer_of(button)`, `quaternion_layer(record)`,
  `keepable(records)`, `cut_plan(names, keepable)`, `folds(names, keepable)`,
  `times_of(times, start, end)`, `question(old, new, records, first_person, cuts, folds)`,
  `Plan` (namedtuple `records cuts folds first_person`), `plan_of(records, first_person, new_is_rig)`.

- [ ] **Step 1: Write the failing test**

```python
"""A character swapped for another keeps its layers (2026-10-29): the pure halves."""

import sys
import types
import unittest


def _install_fake_maya():
    try:
        import maya.cmds  # noqa: F401
        return
    except ImportError:
        pass
    maya = types.ModuleType("maya")
    cmds = types.ModuleType("maya.cmds")
    maya.cmds = cmds
    sys.modules.setdefault("maya", maya)
    sys.modules["maya.cmds"] = cmds


_install_fake_maya()

from maya_poselib import curvedata                            # noqa: E402
from maya_scenesetup import swaplayers                         # noqa: E402


def _record(name, **kwargs):
    return curvedata.layer_record(name, **kwargs)


class Buttons(unittest.TestCase):

    def test_each_button_answers_one_word(self):
        self.assertEqual(swaplayers.answer_of(swaplayers.KEEP), "keep")
        self.assertEqual(swaplayers.answer_of(swaplayers.BAKE), "bake")
        self.assertEqual(swaplayers.answer_of(swaplayers.CANCEL), "cancel")

    def test_a_dismissed_dialog_cancels(self):
        self.assertEqual(swaplayers.answer_of(None), "cancel")
        self.assertEqual(swaplayers.answer_of(""), "cancel")


class Keepable(unittest.TestCase):

    def test_an_additive_quaternion_layer_cannot_be_kept(self):
        record = _record("Spin", rotation="quaternion")
        self.assertTrue(swaplayers.quaternion_layer(record))
        self.assertEqual(swaplayers.keepable([record]), {"Spin": False})

    def test_an_override_quaternion_layer_is_kept(self):
        record = _record("Spin", rotation="quaternion", override=True)
        self.assertFalse(swaplayers.quaternion_layer(record))

    def test_a_plain_additive_layer_is_kept(self):
        self.assertEqual(swaplayers.keepable([_record("Fix")]), {"Fix": True})


class Cuts(unittest.TestCase):

    def test_one_cut_a_layer_the_base_first(self):
        plan = swaplayers.cut_plan(["A", "B"], {"A": True, "B": True})
        self.assertEqual(plan, [(None, []), (0, ["A"]), (1, ["A", "B"])])

    def test_a_layer_that_cannot_be_kept_folds_into_the_one_above(self):
        plan = swaplayers.cut_plan(["A", "B"], {"A": False, "B": True})
        self.assertEqual(plan, [(None, []), (1, ["A", "B"])])
        self.assertEqual(swaplayers.folds(["A", "B"], {"A": False, "B": True}), [("A", "B")])

    def test_the_top_cut_always_holds_every_layer(self):
        plan = swaplayers.cut_plan(["A", "B"], {"A": True, "B": False})
        self.assertEqual(plan, [(None, []), (0, ["A", "B"])])
        self.assertEqual(swaplayers.folds(["A", "B"], {"A": True, "B": False}), [("B", "A")])

    def test_no_layer_can_be_kept_means_no_cut(self):
        self.assertEqual(swaplayers.cut_plan(["A"], {"A": False}), [])


class Times(unittest.TestCase):

    def test_the_layers_own_times_inside_the_range(self):
        self.assertEqual(swaplayers.times_of([0.0, 12.0, 24.0, 99.0], 0.0, 30.0),
                         [0.0, 12.0, 24.0])

    def test_the_same_time_twice_is_one_key(self):
        self.assertEqual(swaplayers.times_of([5.0, 5.00001, 7.0], 0.0, 10.0), [5.0, 7.0])

    def test_a_layer_with_no_key_of_its_own_takes_the_ranges_start(self):
        self.assertEqual(swaplayers.times_of([], 3.0, 10.0), [3.0])


class Question(unittest.TestCase):

    def test_it_names_the_layers_and_both_buttons(self):
        text = swaplayers.question("Manny_Rig", "Creep [rig]", [_record("Fix")], False,
                                   [(None, []), (0, ["Fix"])], [])
        self.assertIn("Manny_Rig", text)
        self.assertIn("Creep [rig]", text)
        self.assertIn("Fix", text)
        self.assertIn("2 times", text)
        self.assertIn(swaplayers.KEEP, text)
        self.assertIn(swaplayers.BAKE, text)

    def test_a_rig_in_1p_says_1p_setup_runs_again(self):
        text = swaplayers.question("Manny_Rig", "Creep [rig]",
                                   [_record("_3P_Lower_Body"), _record("_3P_Upper_Body")],
                                   True, [], [])
        self.assertIn("1P", text)
        self.assertIn("1P Setup", text)
        self.assertNotIn("times", text)

    def test_a_folded_layer_is_named(self):
        text = swaplayers.question("A", "B", [_record("Spin", rotation="quaternion")], False,
                                   [], [("Spin", "Fix")])
        self.assertIn("Spin", text)


class Plans(unittest.TestCase):

    def test_a_rig_in_1p_onto_a_rig_is_the_1p_plan(self):
        plan = swaplayers.plan_of([_record("_3P_Lower_Body")], True, True)
        self.assertTrue(plan.first_person)
        self.assertEqual(plan.cuts, [])

    def test_a_rig_in_1p_onto_a_skeleton_is_cut_layer_by_layer(self):
        plan = swaplayers.plan_of([_record("_3P_Lower_Body")], True, False)
        self.assertFalse(plan.first_person)
        self.assertEqual(plan.cuts, [(None, []), (0, ["_3P_Lower_Body"])])

    def test_no_layer_at_all_is_no_plan(self):
        plan = swaplayers.plan_of([], False, True)
        self.assertFalse(plan.cuts)
        self.assertFalse(plan.first_person)
```

- [ ] **Step 2: Run it to see it fail**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_scenesetup_swaplayers -v`
Expected: FAIL, `ImportError: cannot import name 'swaplayers'`.

- [ ] **Step 3: Write the pure half**

```python
"""A character swapped for another keeps its animation layers, or bakes them (2026-10-29).

The animator: «Если на риге есть слои и мы мняем один риг на другой каким-то из способов то
нужно сделать атк что бы система спросила у нас хотим ли мы сохранить ключи с лои или запечь
всю анимацию. В случе с переносом рига на 1p версию перенос должен сработать корректно».

The question stands before anything is changed (`swap.swap`), and Keep takes one of two roads:

- the general road - the old character's stack CUT at every layer we can keep, each cut baked
  and retargeted onto the new character, the readings written back bottom to top with
  `maya_poselib.keys.write` (Maya's own `setKeyframe -animLayer -value` arithmetic, trap 205),
  each layer keyed only where THAT layer of the old character had keys and with its tangent
  types;
- a rig in 1P - its layers are Tools > 1P Setup's own split, so the 3P take is retargeted once
  and `maya_tools.firstperson.setup` run again on the new rig, which gives the two layers, the
  chest control, the camera and the display layers back.

Spec: docs/superpowers/specs/2026-10-29-swap-keep-layers-design.md
"""
from __future__ import absolute_import

from collections import namedtuple

import maya.cmds as cmds

KEEP = "Keep the layers"
BAKE = "Bake the animation"
CANCEL = "Cancel"
BUTTONS = (KEEP, BAKE, CANCEL)
_ANSWERS = {KEEP: "keep", BAKE: "bake", CANCEL: "cancel"}

TOLERANCE = 1e-4                     # two key times this close are one key

Plan = namedtuple("Plan", "records cuts folds first_person")


def answer_of(button):
    """"keep" / "bake" / "cancel" - a dialog dismissed answers "cancel". Pure."""
    return _ANSWERS.get(button, "cancel")


def quaternion_layer(record):
    """An ADDITIVE layer accumulating rotation as quaternions: its contribution is no
    per-channel sum, so no cut can be made at it (`keys.quaternion_note`). Pure."""
    return not record.get("override") and record.get("rotation") == "quaternion"


def keepable(records):
    """{layer name: can a cut be made at it}. Pure."""
    return dict((r["name"], not quaternion_layer(r)) for r in records)


def cut_plan(names, keep):
    """[(index into `names`, [names unmuted for that cut])] bottom to top, the base's cut
    (None, []) first: a cut at every layer we can keep, and the TOP cut always holding every
    layer, so the whole take is the last thing retargeted. [] when no layer can be kept. Pure."""
    kept = [i for i, name in enumerate(names) if keep.get(name, True)]
    if not kept:
        return []
    out = [(None, [])]
    for i in kept:
        out.append((i, list(names[:i + 1])))
    if list(out[-1][1]) != list(names):
        out[-1] = (kept[-1], list(names))
    return out


def folds(names, keep):
    """[(the layer not kept, the layer its motion lands on)] - the kept layer above it, else
    the topmost kept one below. Pure."""
    kept = [i for i, name in enumerate(names) if keep.get(name, True)]
    out = []
    for i, name in enumerate(names):
        if keep.get(name, True):
            continue
        above = [j for j in kept if j > i]
        below = [j for j in kept if j < i]
        if above:
            out.append((name, names[above[0]]))
        elif below:
            out.append((name, names[below[-1]]))
    return out


def times_of(times, start, end, tolerance=TOLERANCE):
    """The frames a cut is keyed at: its layer's own key times inside [start, end], deduped and
    sorted; `start` alone when it has none (a layer holding a constant offset). Pure."""
    pool = sorted(float(t) for t in times if start - tolerance <= t <= end + tolerance)
    out = []
    for t in pool:
        if not out or t - out[-1] > tolerance:
            out.append(t)
    return out or [float(start)]


def question(old_label, new_label, records, first_person, cuts, folded):
    """The dialog's text. Pure."""
    names = ", ".join(r["name"] for r in records)
    lines = []
    if first_person:
        lines.append("{0} stands in 1P (Tools > 1P Setup): its take lives on {1}.".format(
            old_label, names))
        lines.append("")
        lines.append("{0}: the whole take is retargeted onto {1} and 1P Setup is run again on "
                     "it - the two layers, the chest control, the camera and the display "
                     "layers come back.".format(KEEP, new_label))
    else:
        lines.append("{0} carries {1} animation layer{2}: {3}.".format(
            old_label, len(records), "" if len(records) == 1 else "s", names))
        lines.append("")
        lines.append("{0}: {1} gets the same stack, each layer retargeted in turn, and keys "
                     "only where {2} had them. The retarget runs {3} times.".format(
                         KEEP, new_label, old_label, len(cuts)))
    for name, into in folded:
        lines.append("    {0} cannot be kept on its own - its motion lands on {1}.".format(
            name, into))
    lines.append("")
    if first_person:
        lines.append("{0}: one take on the base layer, as the scene shows it now (the chest "
                     "stabilized), and no 1P setup.".format(BAKE))
    else:
        lines.append("{0}: one take on the base layer, a key on every frame - what the scene "
                     "shows now.".format(BAKE))
    return "\n".join(lines)


def plan_of(records, first_person, new_is_rig):
    """The Plan for a swap: `first_person` only when the old rig is in 1P AND the new character
    is a rig (a skeleton takes the cuts); else the cuts. Pure."""
    if not records:
        return Plan([], [], [], False)
    if first_person and new_is_rig:
        return Plan(list(records), [], [], True)
    keep = keepable(records)
    names = [r["name"] for r in records]
    return Plan(list(records), cut_plan(names, keep), folds(names, keep), False)
```

- [ ] **Step 4: Run the test to see it pass**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_scenesetup_swaplayers -v`
Expected: PASS, every test.

- [ ] **Step 5: Commit**

```bash
git add SkeldarAnim/maya_scenesetup/swaplayers.py tests/test_scenesetup_swaplayers.py
git commit -m "feat(swap): the pure rules of keeping a character's layers"
```

---

### Task 2: Reading the old character's layers

**Files:**
- Modify: `SkeldarAnim/maya_scenesetup/swaplayers.py`
- Test: `tests/test_scenesetup_swaplayers.py`

**Interfaces:**
- Consumes: Task 1's module; `maya_poselib.keys.layer_stack()`, `layer_plugs(name)`,
  `layer_record(name, base=)`, `curve_for(plug, layer)`.
- Produces: `base_layer()`, `layers_of(nodes)`, `records_of(names)`, `mutes_of(names)`,
  `set_mutes(names, on)`, `restore_mutes(saved)`, `curves_on(name, nodes)`,
  `times_and_tangents(curves, start, end)`, `animated_plugs(nodes)`,
  `capture(plugs, times)`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_scenesetup_swaplayers.py`:

```python
class FakeScene(object):
    """The `cmds` calls the scene half makes, answered from a tiny model."""

    def __init__(self, stack=(), plugs=None, keyed=None, muted=None):
        self.stack = list(stack)
        self.plugs = dict(plugs or {})
        self.keyed = dict(keyed or {})       # {plug: [(time, in, out)]}
        self.muted = dict(muted or {})
        self.mutes_set = []

    # -- animLayer
    def animLayer(self, *args, **kwargs):
        if kwargs.get("query"):
            if kwargs.get("root"):
                return self.stack[0] if self.stack else None
            name = args[0]
            if kwargs.get("attribute"):
                return list(self.plugs.get(name, ()))
            if kwargs.get("mute"):
                return bool(self.muted.get(name))
            if kwargs.get("override"):
                return False
            if kwargs.get("weight"):
                return 1.0
            return None
        if kwargs.get("edit") and "mute" in kwargs:
            self.mutes_set.append((args[0], bool(kwargs["mute"])))
            self.muted[args[0]] = bool(kwargs["mute"])
            return args[0]
        return args[0] if args else None

    def ls(self, *args, **kwargs):
        if not args:
            return []
        name = args[0]
        return [name if name.startswith("|") else "|" + name]

    def attributeQuery(self, attr, **kwargs):
        return attr

    def listAnimatable(self, node):
        return [plug for plug in self.keyed if plug.startswith(node + ".")]

    def keyframe(self, *args, **kwargs):
        plug = args[0]
        rows = self.keyed.get(plug, [])
        if kwargs.get("keyframeCount"):
            return len(rows)
        if kwargs.get("timeChange"):
            return [t for t, _i, _o in rows]
        return []

    def keyTangent(self, *args, **kwargs):
        rows = self.keyed.get(args[0], [])
        if kwargs.get("inTangentType"):
            return [i for _t, i, _o in rows]
        if kwargs.get("outTangentType"):
            return [o for _t, _i, o in rows]
        return []

    def getAttr(self, plug, **kwargs):
        return 7.0


class Reading(unittest.TestCase):

    def setUp(self):
        self.saved = swaplayers.cmds

    def tearDown(self):
        swaplayers.cmds = self.saved

    def test_only_the_layers_holding_the_characters_channels(self):
        fake = FakeScene(stack=["BaseAnimation", "Fix", "Other"],
                         plugs={"Fix": ["|rig:ctrl.rotateX"], "Other": ["|prop.translateX"]})
        swaplayers.cmds = fake
        self.assertEqual(swaplayers.layers_of(["|rig:ctrl"]), ["Fix"])

    def test_the_base_is_mayas_root(self):
        fake = FakeScene(stack=["BaseAnimation", "Fix"])
        swaplayers.cmds = fake
        layer = swaplayers.base_layer()
        self.assertEqual(layer.name, "BaseAnimation")
        self.assertTrue(layer.base)

    def test_no_layers_means_no_base_layer(self):
        swaplayers.cmds = FakeScene()
        self.assertIsNone(swaplayers.base_layer())

    def test_a_cut_mutes_every_layer_it_leaves_out_and_restores(self):
        fake = FakeScene(stack=["BaseAnimation", "A", "B"], muted={"A": False, "B": True})
        swaplayers.cmds = fake
        saved = swaplayers.mutes_of(["A", "B"])
        self.assertEqual(saved, {"A": False, "B": True})
        swaplayers.set_mutes(["A", "B"], ["A"])
        self.assertEqual(fake.muted, {"A": False, "B": True})
        swaplayers.set_mutes(["A", "B"], [])
        self.assertTrue(fake.muted["A"])
        swaplayers.restore_mutes(saved)
        self.assertEqual(fake.muted, {"A": False, "B": True})

    def test_the_times_and_tangents_of_a_layers_own_curves(self):
        fake = FakeScene(keyed={"c1": [(0.0, "step", "step"), (12.0, "step", "step")]})
        swaplayers.cmds = fake
        times, tangents = swaplayers.times_and_tangents(["c1"], 0.0, 24.0)
        self.assertEqual(times, [0.0, 12.0])
        self.assertEqual(tangents[12.0], ("step", "step"))

    def test_only_the_channels_that_carry_keys_are_captured(self):
        fake = FakeScene(keyed={"|c.rotateX": [(0.0, "auto", "auto")]})
        swaplayers.cmds = fake
        plugs = swaplayers.animated_plugs(["|c"])
        self.assertEqual(plugs, ["|c.rotateX"])
        self.assertEqual(swaplayers.capture(plugs, [0.0]), {"|c.rotateX": {0.0: 7.0}})
```

- [ ] **Step 2: Run it to see it fail**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_scenesetup_swaplayers -v`
Expected: FAIL, `AttributeError: module ... has no attribute 'layers_of'`.

- [ ] **Step 3: Write the reading half**

Append to `swaplayers.py`:

```python
# ------------------------------------------------------------------ scene: reading

def base_layer():
    """The `keys.Layer` of Maya's own root layer, or None in a scene with no layers. A scene
    tab's root holds no curves of its own (trap 279): the root Maya answers is the base."""
    from maya_poselib import keys
    root = cmds.animLayer(query=True, root=True)
    if not root:
        return None
    return keys.Layer(root, True, False, False, False)


def layers_of(nodes):
    """[layer name] above the base, bottom to top, holding any channel of `nodes` - the old
    character's layers, the ones a swap has to carry."""
    from maya_poselib import keys
    wanted = set()
    for node in nodes:
        found = cmds.ls(node, long=True) or []
        wanted.add(found[0] if found else node)
    out = []
    for name in keys.layer_stack()[1:]:
        for plug in keys.layer_plugs(name):
            if plug.rsplit(".", 1)[0] in wanted:
                out.append(name)
                break
    return out


def records_of(names):
    """[`curvedata.layer_record`] of `names`, in order."""
    from maya_poselib import keys
    return [keys.layer_record(name) for name in names]


def mutes_of(names):
    """{layer name: its own mute} - what `restore_mutes` puts back."""
    return dict((name, bool(cmds.animLayer(name, query=True, mute=True))) for name in names)


def set_mutes(names, on):
    """Every layer of `names` muted but those in `on`."""
    wanted = set(on)
    for name in names:
        try:
            cmds.animLayer(name, edit=True, mute=name not in wanted)
        except RuntimeError:
            pass


def restore_mutes(saved):
    for name, mute in saved.items():
        try:
            cmds.animLayer(name, edit=True, mute=mute)
        except RuntimeError:
            pass


def curves_on(name, nodes):
    """The curve nodes the layer `name` (None: the base) holds for the channels of `nodes`."""
    from maya_poselib import keys
    layer = None if name is None else name
    out = []
    for plug in animated_plugs(nodes, keyed_only=False):
        curve = keys.curve_for(plug, layer)
        if curve and curve not in out:
            out.append(curve)
    return out


def times_and_tangents(curves, start, end):
    """([times], {time: (in, out)}) of `curves`' keys inside [start, end]: the times a cut is
    keyed at (`times_of`) and the tangent types the source keys had there, where they agree
    (`fkik.tangents_at`'s rule - never `fixed`)."""
    from maya_scenesetup import fkik
    rows = []
    for curve in curves:
        times = cmds.keyframe(curve, query=True, timeChange=True) or []
        ins = cmds.keyTangent(curve, query=True, inTangentType=True) or [None] * len(times)
        outs = cmds.keyTangent(curve, query=True, outTangentType=True) or [None] * len(times)
        rows.append(list(zip(times, ins, outs)))
    times = times_of([t for row in rows for t, _i, _o in row], start, end)
    tangents = dict((t, fkik.tangents_at(rows, rows, t)) for t in times)
    return times, tangents


def animated_plugs(nodes, keyed_only=True):
    """The keyable channels of `nodes` that carry keys - what a cut's reading covers."""
    out = []
    for node in nodes:
        for plug in cmds.listAnimatable(node) or []:
            if not keyed_only or cmds.keyframe(plug, query=True, keyframeCount=True):
                out.append(plug)
    return out


def capture(plugs, times):
    """{plug: {time: value}} read off the curves a retarget has just left."""
    out = {}
    for plug in plugs:
        out[plug] = dict((t, cmds.getAttr(plug, time=t)) for t in times)
    return out
```

- [ ] **Step 4: Run the test to see it pass**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_scenesetup_swaplayers -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add SkeldarAnim/maya_scenesetup/swaplayers.py tests/test_scenesetup_swaplayers.py
git commit -m "feat(swap): read the old character's layers, their key times and tangents"
```

---

### Task 3: Writing the stack onto the new character

**Files:**
- Modify: `SkeldarAnim/maya_scenesetup/swaplayers.py`
- Test: `tests/test_scenesetup_swaplayers.py`

**Interfaces:**
- Consumes: Tasks 1-2; `maya_poselib.keys.write(values, frame, layer)`, `keys.make_layer(record)`,
  `keys.curve_for(plug, layer)`.
- Produces: `write_cut(values, times, tangents, layer)` -> `(keyed plug count, notes)`,
  `write_stack(readings, records, progress=None)` -> `(made layer names, notes)`.
  A `reading` is the namedtuple `Reading(index, values, times, tangents)` - `index` None for the
  base, else the index into `records`.

- [ ] **Step 1: Write the failing test**

```python
class Writing(unittest.TestCase):

    def setUp(self):
        self.saved = swaplayers.cmds
        self.written = []
        self.made = []
        self.tangents = []

        class FakeKeys(object):
            Layer = __import__("maya_poselib.keys", fromlist=["keys"]).Layer
            LOCKED = "locked %s"

            @staticmethod
            def write(values, frame, layer):
                self.written.append((dict(values), frame, None if layer is None else layer.name))
                return __import__("maya_poselib.keys", fromlist=["keys"]).Written(
                    len(values), [], list(values))

            @staticmethod
            def make_layer(record):
                self.made.append(dict(record))
                return record["name"]

            @staticmethod
            def curve_for(plug, layer):
                return plug + "@" + str(layer)

        self.fake_keys = FakeKeys

    def tearDown(self):
        swaplayers.cmds = self.saved

    def _run(self, readings, records):
        fake = FakeScene(stack=["BaseAnimation"])

        def key_tangent(*args, **kwargs):
            self.tangents.append((list(args[0]), kwargs.get("inTangentType"),
                                  kwargs.get("outTangentType")))
        fake.keyTangent = key_tangent
        swaplayers.cmds = fake
        return swaplayers.write_stack(readings, records, keys_module=self.fake_keys)

    def test_the_base_is_written_first_then_each_layer_bottom_to_top(self):
        records = [_record("A"), _record("B")]
        readings = [swaplayers.Reading(None, {"p": {0.0: 1.0}}, [0.0], {0.0: ("auto", "auto")}),
                    swaplayers.Reading(0, {"p": {0.0: 2.0}}, [0.0], {0.0: ("auto", "auto")}),
                    swaplayers.Reading(1, {"p": {0.0: 3.0}}, [0.0], {0.0: ("auto", "auto")})]
        made, _notes = self._run(readings, records)
        self.assertEqual(made, ["A", "B"])
        self.assertEqual([layer for _v, _f, layer in self.written],
                         ["BaseAnimation", "A", "B"])

    def test_a_layer_is_made_unmuted_and_muted_after_its_keys(self):
        records = [_record("A", mute=True)]
        readings = [swaplayers.Reading(None, {"p": {0.0: 1.0}}, [0.0], {}),
                    swaplayers.Reading(0, {"p": {0.0: 2.0}}, [0.0], {})]
        self._run(readings, records)
        self.assertFalse(self.made[0]["mute"])
        self.assertIn(("A", True), swaplayers.cmds.mutes_set)

    def test_the_source_tangent_types_are_set_on_the_keys(self):
        records = [_record("A")]
        readings = [swaplayers.Reading(None, {"p": {0.0: 1.0}}, [0.0], {0.0: ("step", "step")}),
                    swaplayers.Reading(0, {"p": {0.0: 2.0}}, [0.0], {0.0: ("flat", "flat")})]
        self._run(readings, records)
        self.assertIn((["p@None"], "step", "step"), self.tangents)
        self.assertIn((["p@A"], "flat", "flat"), self.tangents)

    def test_a_step_in_tangent_is_asked_as_the_out_type_only(self):
        self.assertEqual(swaplayers.tangent_flags("step", "step"),
                         {"outTangentType": "step"})
        self.assertEqual(swaplayers.tangent_flags("auto", "linear"),
                         {"inTangentType": "auto", "outTangentType": "linear"})
        self.assertEqual(swaplayers.tangent_flags(None, None), {})

    def test_a_layer_at_weight_zero_is_made_and_left_empty(self):
        records = [_record("A", weight=0.0)]
        readings = [swaplayers.Reading(None, {"p": {0.0: 1.0}}, [0.0], {}),
                    swaplayers.Reading(0, {"p": {0.0: 2.0}}, [0.0], {})]
        made, notes = self._run(records=records, readings=readings)
        self.assertEqual(made, ["A"])
        self.assertEqual([layer for _v, _f, layer in self.written], ["BaseAnimation"])
        self.assertTrue(any("weight 0" in note for note in notes))
```

- [ ] **Step 2: Run it to see it fail**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_scenesetup_swaplayers.Writing -v`
Expected: FAIL, no `Reading` / `write_stack`.

- [ ] **Step 3: Write the writing half**

Append to `swaplayers.py`:

```python
EMPTY = "%s is at weight 0 - made, left empty"

Reading = namedtuple("Reading", "index values times tangents")


def tangent_flags(in_type, out_type):
    """The `keyTangent` flags for one key's types: Maya refuses `step` / `stepnext` as an IN
    type (`keys._NO_IN_TYPES`), so that one is left to Maya. Pure."""
    flags = {}
    if in_type and in_type not in ("step", "stepnext"):
        flags["inTangentType"] = in_type
    if out_type:
        flags["outTangentType"] = out_type
    return flags


def write_cut(values, times, tangents, layer, keys_module=None):
    """`values` ({plug: {time: value}}) keyed on `layer` (a `keys.Layer`, or None for plain
    keys) at `times`, each key's tangent types from `tangents`. (plugs keyed, notes)."""
    if keys_module is None:
        from maya_poselib import keys as keys_module
    keyed, notes = set(), []
    for frame in times:
        at = dict((plug, per[frame]) for plug, per in values.items() if frame in per)
        if not at:
            continue
        written = keys_module.write(at, frame, layer)
        notes.extend(written.notes)
        keyed.update(written.plugs)
        flags = tangent_flags(*tangents.get(frame, (None, None)))
        if not flags or not written.plugs:
            continue
        name = None if layer is None else (None if layer.base else layer.name)
        curves = [c for c in (keys_module.curve_for(plug, name) for plug in written.plugs) if c]
        if curves:
            try:
                cmds.keyTangent(curves, time=(frame, frame), **flags)
            except RuntimeError:
                pass
    return sorted(keyed), notes


def write_stack(readings, records, progress=None, keys_module=None):
    """The cuts' readings written onto the new character bottom to top: the base's as plain keys
    on the base layer, then each layer MADE (unmuted, its record's mode, weight and accumulation
    modes) and its cut keyed on it, its mute set after. (made layer names, notes).

    Each layer takes FINAL values through `keys.write`, so Maya itself works out what an
    additive, override, weighted or scale layer must hold (trap 205)."""
    if keys_module is None:
        from maya_poselib import keys as keys_module
    made, notes = [], []
    by_index = dict((r.index, r) for r in readings)
    base = by_index.get(None)
    if base is not None:
        _keyed, said = write_cut(base.values, base.times, base.tangents, base_layer(),
                                 keys_module)
        notes.extend(said)
    for index, record in enumerate(records):
        reading = by_index.get(index)
        if reading is None:
            continue
        wanted = dict(record)
        wanted["mute"] = False
        name = keys_module.make_layer(wanted)
        made.append(name)
        if progress is not None:
            progress.step("the %s layer" % name)
        if abs(float(record.get("weight", 1.0))) < 1e-9:
            notes.append(EMPTY % name)
        else:
            layer = keys_module.Layer(name, False, not record.get("override"), False,
                                      record.get("rotation") == "quaternion")
            _keyed, said = write_cut(reading.values, reading.times, reading.tangents, layer,
                                     keys_module)
            notes.extend(said)
        if record.get("mute"):
            try:
                cmds.animLayer(name, edit=True, mute=True)
            except RuntimeError:
                pass
    return made, notes
```

- [ ] **Step 4: Run the test to see it pass**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_scenesetup_swaplayers -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add SkeldarAnim/maya_scenesetup/swaplayers.py tests/test_scenesetup_swaplayers.py
git commit -m "feat(swap): write a captured stack onto the new character, layer by layer"
```

---

### Task 4: The question, and the cuts road in `swap.py`

**Files:**
- Modify: `SkeldarAnim/maya_scenesetup/swap.py`
- Modify: `SkeldarAnim/maya_scenesetup/swaplayers.py`
- Test: `tests/test_scenesetup_swaplayers.py`, `tests/test_scenesetup_swap.py`

**Interfaces:**
- Consumes: Tasks 1-3; `swap.bake_copy`, `swap._onto_rig`, `swap._onto_skeleton`,
  `maya_uebridge.rigimport.ready_rig` / `retarget_imported`,
  `maya_uebridge.skeletonimport._transfer`.
- Produces: in `swaplayers`: `set_asker(fn)`, `can_ask()`, `ask(text)`, `choose(plan, old, new)`
  -> "keep" / "bake" (raising `Cancelled`), `Cancelled`, `KEPT`, `line_of(made, notes)`.
  In `swap`: `Arrival` (namedtuple `root rig line failure mod mode`), `_again(arrival, entry,
  namespace, info, source, name)` -> `(line, failure)`.

- [ ] **Step 1: Write the failing test**

```python
class Choosing(unittest.TestCase):

    def tearDown(self):
        swaplayers.set_asker(None)

    def test_the_asker_is_what_the_press_asks(self):
        asked = []
        swaplayers.set_asker(lambda text: asked.append(text) or swaplayers.KEEP)
        plan = swaplayers.plan_of([_record("Fix")], False, True)
        self.assertEqual(swaplayers.choose(plan, "A", "B"), "keep")
        self.assertEqual(len(asked), 1)

    def test_bake_is_the_answer_with_nobody_to_ask(self):
        swaplayers.set_asker(None)
        plan = swaplayers.plan_of([_record("Fix")], False, True)
        saved = swaplayers.can_ask
        swaplayers.can_ask = lambda: False
        try:
            self.assertEqual(swaplayers.choose(plan, "A", "B"), "bake")
        finally:
            swaplayers.can_ask = saved

    def test_cancel_raises(self):
        swaplayers.set_asker(lambda text: swaplayers.CANCEL)
        plan = swaplayers.plan_of([_record("Fix")], False, True)
        self.assertRaises(swaplayers.Cancelled, swaplayers.choose, plan, "A", "B")

    def test_a_character_with_no_layer_is_never_asked(self):
        swaplayers.set_asker(lambda text: self.fail("asked"))
        self.assertEqual(swaplayers.choose(swaplayers.plan_of([], False, True), "A", "B"),
                         "bake")

    def test_the_line_names_the_layers_it_made(self):
        self.assertIn("A, B", swaplayers.line_of(["A", "B"], []))
        self.assertIn("note", swaplayers.line_of(["A"], ["note"]))
        self.assertEqual(swaplayers.line_of([], []), "")
```

And in `tests/test_scenesetup_swap.py`:

```python
class Arrivals(unittest.TestCase):

    def test_an_arrival_carries_the_module_and_the_proportions_answer(self):
        arrival = swap.Arrival("|root", None, "line", "", "mod", "stretch")
        self.assertEqual(arrival.root, "|root")
        self.assertEqual(arrival.mod, "mod")
        self.assertEqual(arrival.mode, "stretch")
```

- [ ] **Step 2: Run it to see it fail**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_scenesetup_swaplayers tests.test_scenesetup_swap -v`
Expected: FAIL, no `choose` / `Arrival`.

- [ ] **Step 3: Write the question**

Append to `swaplayers.py`:

```python
KEPT = "layers kept: %s"
_ASKER = None


class Cancelled(Exception):
    """The animator pressed Cancel in the layers question."""


def set_asker(fn):
    """Install (or clear, with None) the answerer the dialog defers to - the verifies' seam."""
    global _ASKER
    _ASKER = fn


def can_ask():
    """A dialog can stand: an answerer is installed, or Maya has a UI."""
    if _ASKER is not None:
        return True
    try:
        return not cmds.about(batch=True)
    except Exception:                                        # noqa: BLE001
        return False


def ask(text):
    """The animator's button."""
    if _ASKER is not None:
        return _ASKER(text)
    return cmds.confirmDialog(title="Swap: keep the animation layers?", message=text,
                              button=list(BUTTONS), defaultButton=KEEP,
                              cancelButton=CANCEL, dismissString=CANCEL)


def choose(plan, old_label, new_label):
    """"keep" or "bake"; `Cancelled` for Cancel. A character with no layer, or no road to keep
    them, is never asked - "bake", which is the swap's own road."""
    if not plan.records or not (plan.cuts or plan.first_person):
        return "bake"
    if not can_ask():
        return "bake"
    answer = answer_of(ask(question(old_label, new_label, plan.records, plan.first_person,
                                    plan.cuts, plan.folds)))
    if answer == "cancel":
        raise Cancelled(old_label)
    return answer


def line_of(made, notes):
    """What the status line says about the layers, or "" when none were made."""
    parts = []
    if made:
        parts.append(KEPT % ", ".join(made))
    parts.extend(n for n in notes if n)
    return "  |  ".join(parts)
```

- [ ] **Step 4: Rework `swap.py`'s arrivals**

In `swap.py`, add `from collections import namedtuple` beside `import math`, and:

```python
Arrival = namedtuple("Arrival", "root rig line failure mod mode")
```

Change `_onto_rig` to carry the module and the proportions answer, and to take an answer:

```python
def _onto_rig(entry, namespace, info, source, name, bones=None):
    """The `Arrival` of a new rig: added, the clip retargeted onto it. `bones` reuses a
    proportions answer already given (a later cut of the same stack)."""
    import maya_retargetmode
    from maya_uebridge import rigimport
    plan = dict(rig=None, mod=None, add=True, entry=entry)
    rig, mod, notes, failure = rigimport.ready_rig(plan)
    if failure:
        return Arrival(None, rig, "", "  |  ".join(notes + [failure]), mod, bones)
    mode, reason = bones, ""
    if mode is None:
        try:
            decision = rigimport.decide_bones(rig, mod, source)
        except maya_retargetmode.Cancelled:
            rigimport.discard_added(rig)
            raise
        mode, reason = decision.mode, decision.reason
    line, failure = rigimport.retarget_imported(rig, mod, namespace, info, source, name,
                                                bones=mode)
    line = reason or (line or "").split("  |  ")[0]
    fresh = maya_rigs.find(rig.namespace) or rig
    if failure:
        return Arrival(fresh.skeleton_root, fresh, "", failure, mod, mode)
    return Arrival(fresh.skeleton_root, fresh, line, "", mod, mode)
```

`_onto_skeleton` the same shape, capturing the transfer's decision so a later cut reuses it:

```python
def _onto_skeleton(entry, namespace, info, source, name):
    """The `Arrival` of a new skeleton; `mode` is the transfer's own decision, which a later
    cut hands back to `skeletonimport._transfer`."""
    from maya_uebridge import skeletonimport
    taken = []

    def decide(*args):
        decision = skeletonimport.choose_for(*args)
        taken.append(decision)
        return decision

    before = set(cmds.ls(type="joint", long=True) or [])
    line, failure, _top = skeletonimport.onto_skeleton(
        entry, namespace, info, source, name, decide=decide)
    fresh = [j for j in cmds.ls(type="joint", long=True) or []
             if j not in before and not j.split("|")[-1].startswith(namespace + ":")]
    root = min(fresh, key=lambda p: (p.count("|"), p)) if fresh else None
    parts = (line or "").split("  |  ")
    return Arrival(root, None, parts[-1] if len(parts) > 1 else parts[0], failure, None,
                   taken[0] if taken else None)
```

Update the four unpack sites in `swap()` and `attach_part()`:

```python
        if catalog.is_rig(entry):
            arrival = _onto_rig(entry, namespace, info, source, name)
        else:
            arrival = _onto_skeleton(entry, namespace, info, source, name)
```
and read `arrival.root`, `arrival.rig`, `arrival.line`, `arrival.failure` below.

Add the "again" road:

```python
def _again(arrival, entry, namespace, info, source, name):
    """A further cut of the old stack retargeted onto the character that already stands: its
    previous take cleared and the clip connected and baked again with the SAME proportions
    answer. (line, failure)."""
    from maya_uebridge import rigimport, skeletonimport
    if arrival.rig is not None:
        rig, mod, notes, failure = rigimport.ready_rig(
            dict(rig=arrival.rig, mod=arrival.mod, add=False, entry=entry))
        if failure:
            return "", "  |  ".join(notes + [failure])
        return rigimport.retarget_imported(rig, mod, namespace, info, source, name,
                                           bones=arrival.mode)
    result = skeletonimport._transfer(source, arrival.root, info.get("start"),
                                      info.get("end"), arrival.mode)
    _drop_namespace(namespace)
    if not result.get("moved"):
        return "", "no bone of {0} matches {1}".format(name, leaf(arrival.root))
    return "", ""
```

- [ ] **Step 5: Run the tests**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_scenesetup_swaplayers tests.test_scenesetup_swap -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add SkeldarAnim/maya_scenesetup/swap.py SkeldarAnim/maya_scenesetup/swaplayers.py tests/test_scenesetup_swaplayers.py tests/test_scenesetup_swap.py
git commit -m "feat(swap): the layers question, and a cut retargeted onto the character standing"
```

---

### Task 5: The two Keep roads, wired into the press

**Files:**
- Modify: `SkeldarAnim/maya_scenesetup/swap.py`
- Modify: `SkeldarAnim/maya_scenesetup/swaplayers.py`
- Test: `tests/test_scenesetup_swaplayers.py`

**Interfaces:**
- Consumes: Tasks 1-4; `maya_tools.firstperson.chest_of` / `setup`, `maya_rigs.rigs`.
- Produces: in `swaplayers`: `in_1p(rig)`, `split_again(rig)` -> `(line, failure)`,
  `FOLDED_1P`, `SPLIT_AGAIN`. In `swap`: `swap()` asking and taking the road.

- [ ] **Step 1: Write the failing test**

```python
class FirstPerson(unittest.TestCase):

    def test_a_rig_with_a_chest_knot_of_its_own_is_in_1p(self):
        class Rig(object):
            namespace = "Manny_Rig"

        class Fake(object):
            @staticmethod
            def chest_of(rig):
                return "|Manny_Rig:Chest_1P_ctrl"
        self.assertTrue(swaplayers.in_1p(Rig(), module=Fake))

        class None_(object):
            @staticmethod
            def chest_of(rig):
                return None
        self.assertFalse(swaplayers.in_1p(Rig(), module=None_))

    def test_none_is_never_in_1p(self):
        self.assertFalse(swaplayers.in_1p(None))

    def test_the_1p_line_names_the_rig_and_the_folded_layers(self):
        self.assertIn("Creep_Rig", swaplayers.SPLIT_AGAIN % "Creep_Rig")
        self.assertIn("Fix", swaplayers.FOLDED_1P % "Fix")
```

- [ ] **Step 2: Run it to see it fail**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_scenesetup_swaplayers.FirstPerson -v`
Expected: FAIL, no `in_1p`.

- [ ] **Step 3: Write the 1P half**

Append to `swaplayers.py`:

```python
SPLIT_AGAIN = "1P Setup run again on %s"
FOLDED_1P = "%s folded into the 1P split"
NOT_A_RIG = "%s is a skeleton: its layers are kept one by one, no 1P setup"


def in_1p(rig, module=None):
    """Is `rig` standing in 1P - Tools > 1P Setup's chest knot marked with its namespace?"""
    if rig is None:
        return False
    if module is None:
        try:
            from maya_tools import firstperson as module
        except ImportError:
            return False
    try:
        return bool(module.chest_of(rig))
    except Exception:                                        # noqa: BLE001
        return False


def split_again(rig, module=None):
    """Tools > 1P Setup run again on the new `rig`: (line, failure)."""
    if module is None:
        from maya_tools import firstperson as module
    try:
        line = module.setup(selection=[rig.main])
    except Exception as error:                               # noqa: BLE001
        return "", str(error).strip().splitlines()[0]
    lowered = (line or "").lower()
    if "1p setup:" in lowered or " refused" in lowered or lowered.startswith("no "):
        return "", line
    return SPLIT_AGAIN % (rig.namespace or "the new rig"), ""
```

- [ ] **Step 4: Wire the press**

In `swap.swap()`, between `found = foreign_constraints(...)` and `namespace, source, info =
bake_copy(...)`:

```python
    from maya_scenesetup import swaplayers
    nodes = game_joints(char.root) + _controls(char.rig)
    records = swaplayers.records_of(swaplayers.layers_of(nodes))
    plan = swaplayers.plan_of(records, swaplayers.in_1p(char.rig), catalog.is_rig(entry))
    try:
        answer = swaplayers.choose(plan, char.label, entry.label)
    except swaplayers.Cancelled:
        return CANCELLED
```

Then the bake and the arrival become a road:

```python
    saved_mutes = swaplayers.mutes_of([r["name"] for r in plan.records])
    try:
        arrival, readings, notes = _arrive(entry, char, plan, answer, start, end, name,
                                           timing)
    finally:
        swaplayers.restore_mutes(saved_mutes)
```

with, in `swap.py`:

```python
def _arrive(entry, char, plan, answer, start, end, name, timing):
    """(Arrival, [swaplayers.Reading], notes): the new character standing with the old take on
    it. With `answer` "bake" - or no layer to keep - ONE bake of the scene as it shows and one
    retarget (the 2026-10-17 road). With "keep" and a rig in 1P, one bake of the 3P take (every
    layer unmuted) and 1P Setup run again on the new rig. Otherwise the old stack's cuts, one
    bake and retarget each, the new character's channels read at each layer's own key times."""
    from maya_scenesetup import swaplayers
    from maya_uebridge import rigimport
    names = [r["name"] for r in plan.records]
    notes = []
    if answer == "bake" or (not plan.cuts and not plan.first_person):
        return _one(entry, char, start, end, name, timing), [], notes
    if plan.first_person:
        swaplayers.set_mutes(names, names)                   # the 3P take
        arrival = _one(entry, char, start, end, name, timing)
        if arrival.failure or not arrival.root:
            return arrival, [], notes
        readings = _reading_of(arrival, char, names, None, start, end)
        return arrival, readings, notes
    arrival, readings = None, []
    for position, (index, on) in enumerate(plan.cuts):
        swaplayers.set_mutes(names, on)
        namespace, source, info = bake_copy(char.root, start, end)
        if position == 0:
            arrival = (_onto_rig if catalog.is_rig(entry) else _onto_skeleton)(
                entry, namespace, info, source, name)
            if arrival.failure or not arrival.root:
                _drop_namespace(namespace)
                return arrival, [], notes
        else:
            line, failure = _again(arrival, entry, namespace, info, source, name)
            if failure:
                notes.append(failure)
                continue
        layer = None if index is None else names[index]
        readings.extend(_reading_of(arrival, char, names, layer, start, end, index))
    return arrival, readings, notes


def _one(entry, char, start, end, name, timing):
    """One bake of the old character as the scene shows it, retargeted onto the new one."""
    namespace, source, info = bake_copy(char.root, start, end)
    try:
        arrival = (_onto_rig if catalog.is_rig(entry) else _onto_skeleton)(
            entry, namespace, info, source, name)
    except Exception:
        _drop_namespace(namespace)
        raise
    _drop_namespace(namespace)
    return arrival


def _reading_of(arrival, char, names, layer, start, end, index=None):
    """[swaplayers.Reading] of the cut now standing on the new character: its channels read at
    `layer`'s own key times on the OLD character (None: the base's)."""
    from maya_scenesetup import swaplayers
    old = game_joints(char.root) + _controls(char.rig)
    times, tangents = swaplayers.times_and_tangents(
        swaplayers.curves_on(layer, old), start, end)
    new = _controls(arrival.rig) if arrival.rig is not None else game_joints(arrival.root)
    plugs = swaplayers.animated_plugs(new)
    return [swaplayers.Reading(index, swaplayers.capture(plugs, times), times, tangents)]
```

After `_arrive`, when readings came back, clear the take once more and write the stack:

```python
    if readings:
        from maya_uebridge import rigimport as _ri
        if arrival.rig is not None:
            _ri.ready_rig(dict(rig=arrival.rig, mod=arrival.mod, add=False, entry=entry))
        made, said = swaplayers.write_stack(readings, plan.records)
        notes.append(swaplayers.line_of(made, said))
    elif plan.first_person and arrival.rig is not None:
        text, failure = swaplayers.split_again(arrival.rig)
        notes.append(text or failure)
```

(For the 1P road the single reading is written onto the base and then 1P Setup runs: the order
in the press is write the base, then `split_again`.)

- [ ] **Step 5: Run the whole suite**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -q`
Expected: no new failures beside the known `test_chat_deploy.Keys`.

- [ ] **Step 6: Commit**

```bash
git add SkeldarAnim/maya_scenesetup/swap.py SkeldarAnim/maya_scenesetup/swaplayers.py tests/test_scenesetup_swaplayers.py
git commit -m "feat(swap): Keep the layers - the cuts road and the 1P split, wired into the press"
```

---

### Task 6: The verify script

**Files:**
- Create: `docs/superpowers/plans/verify_swap_keep_layers.py`

**Interfaces:**
- Consumes: the whole feature; `maya_scenesetup.swaplayers.set_asker`.
- Produces: a mayapy standalone script, `python verify_swap_keep_layers.py <clip.fbx> [out.txt]`,
  printing `N of M gates failed`.

- [ ] **Step 1: Write the script**

Its shape follows `docs/superpowers/plans/verify_character_swap.py`: a `REPO` derived from the
script's own folder, `sys.path.insert(0, REPO)`, `maya.standalone.initialize()`, the plugins
`matrixNodes` / `quatNodes` / `fbxmaya` loaded, a `gate(name, ok, text)` collector.

Phases, each on a fresh scene:

```python
def phase_keep(clip):
    """A correction layer kept across a swap for another model."""
    # a Manny_Rig with the clip retargeted onto it (rigimport's own press)
    # a layer "Fix" made, FKSpine3_M.rotateY keyed +20 at 0, 12, 24 (stepped at 12)
    # the old rig's bones sampled with the layer ON and with it MUTED
    # swaplayers.set_asker(lambda text: swaplayers.KEEP)
    # swap.swap(catalog.character_for("Creep", "rig"), old_root)
    gate("the new rig carries a layer named Fix", ...)
    gate("its keys stand on 0, 12, 24 and nowhere else", ...)
    gate("the stepped key came out stepped", ...)
    gate("with the layer on, the bones are where the bake road puts them (at the keys)", ...)
    gate("with the layer muted, the bones are where muting it on the old rig put them", ...)
    gate("the layer's mode and weight are the old layer's", ...)
```

and the rest: `phase_dense` (a layer keyed on every frame comes out on every frame),
`phase_override` (an override layer and a 0.5-weight layer each show what they showed),
`phase_quaternion` (a quaternion layer folded, named, and the whole take still right),
`phase_bake` (the BAKE button leaves today's result: one dense take, no layer),
`phase_cancel` (CANCEL changes nothing - the old character still standing, its layers intact),
`phase_1p` (a rig through `firstperson.setup`, swapped with KEEP: the new rig in 1P - both
layers marked with its namespace, the chest knot, the camera control under it, the display
layers, `Main.view` 1 - its bones under both layers where the old rig's 3P take put them and,
with the upper layer muted, where the old rig's 1P look was), `phase_none` (a character with no
layer is never asked: the asker fails the gate if called).

Measurement rule: every comparison is on the GAME bones' world matrices at the key frames, worst
element, tolerance 0.05 cm / 0.01 deg (the swap's own retarget residual), and the "with the layer
muted" gates mute on both sides before sampling.

- [ ] **Step 2: Run it**

Run:
```bash
& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs/superpowers/plans/verify_swap_keep_layers.py "C:/!!!Work/Animations/..." out.txt
```
Expected: `0 of N gates failed`. Fix what fails, in the code, not in the gate.

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/plans/verify_swap_keep_layers.py
git commit -m "test(swap): verify_swap_keep_layers - the layers kept, folded, baked, cancelled, 1P"
```

---

### Task 7: The docs

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Write the section**

A new section after "A portrait dropped on a character swaps it (2026-10-17)": the animator's
words, the two answers, the question's buttons, the cuts road, the 1P road, the proof's numbers,
and what is not built. Any trap the build measured goes in the numbered trap list.

- [ ] **Step 2: Run the whole suite once more and commit**

```bash
& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -q
git add CLAUDE.md && git commit -m "docs: a rig swapped for another keeps its layers"
```

---

## Self-Review

**Spec coverage:** the question (Task 4), the general cuts road (Tasks 1-5), the keys-only rule
and tangents (Tasks 2-3), the 1P road (Task 5), the refusals and notes (Tasks 1, 3, 5), where it
lives (Tasks 1-5), the proof (Task 6), the docs (Task 7). `attach_part` is deliberately left
unasked (Task 4 touches only `swap()`).

**Placeholders:** none - every step carries its code. Task 6's gates are named with their
measurement rule rather than written out in full, because the fixture (which clip, which rows)
is settled by the first run; the gate names ARE the requirements.

**Type consistency:** `Arrival(root, rig, line, failure, mod, mode)` is used with those names in
Tasks 4 and 5; `Reading(index, values, times, tangents)` in Tasks 3 and 5; `Plan(records, cuts,
folds, first_person)` in Tasks 1, 4 and 5; `write_stack(readings, records, progress=None,
keys_module=None)` in Tasks 3 and 5.
