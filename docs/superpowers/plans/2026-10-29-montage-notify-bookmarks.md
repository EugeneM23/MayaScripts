# Montage scan-window bookmarks — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Importing a montage slot through Animation Setup also puts that montage's
`MeleeScanWindow` notifies on Maya's timeline as time-slider bookmarks.

**Architecture:** The notifies ride the roads the montage import already has. The editor's plan
script (run when a montage row is picked, cached per montage) reads every notify through
`unreal.AnimationLibrary`; the pure half of `maya_uebridge/montage.py` picks the scan class, clips
the windows to the slot's end and turns them into whole frames; `import_clip` writes one
`timeSliderBookmark` per window, marked as ours so a re-import replaces them.

**Tech Stack:** Maya 2027 (`maya.cmds`, the `timeSliderBookmark` plugin), Epic's Python Remote
Execution, stdlib-only pure half, `mayapy -m unittest`.

## Global constraints

- Spec: `docs/superpowers/specs/2026-10-29-montage-notify-bookmarks-design.md`.
- **Nothing is written into the Unreal project**; the editor is only read.
- The animator's Maya and scene are never touched. Live checks run against the open editor from
  mayapy, read-only.
- `montage.py`'s pure half stays stdlib — a subprocess test pins it. Everything above
  `# --- the scene` imports no Maya.
- The scan class is **`AnimNotifyState_MeleeScanWindow`**; the pick is by CLASS, never by name (two
  of Atone's 90 are named `GameplayEvent Window`).
- A bookmark's frames snap **outward** (`floor` of the start, `ceil` of the end), at least one
  frame wide: a fractional playback range is the trap that makes Unreal refuse a clip.
- Identity in the scene is the attribute `skeldarMontageNotify`, never a node name.
- Tests run with `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" -m unittest ...` from the
  repo root (Git Bash: no `&`, no system python).
- No system Python; Python source is written with the Write tool, never a Bash heredoc.

---

### Task 1: The editor's plan script brings the notifies

**Files:**
- Modify: `SkeldarAnim/maya_uebridge/uescripts.py` (`_MONTAGE_PLAN_HEAD`, the `row` build)
- Test: `tests/test_uebridge_montage_scripts.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: each montage row of the plan reply gains
  `"notifies": [{"name": str, "class": str, "state": bool, "trigger": float, "duration": float}]`
  — montage time in seconds, in the montage's own order.

- [ ] **Step 1: Write the failing tests**

```python
class MontagePlanNotifies(unittest.TestCase):
    def test_the_plan_script_reads_the_notify_events(self):
        source = uescripts.montage_plan_script("C:/out.json", ["/Game/A/AM_X"])
        self.assertIn("get_animation_notify_events", source)

    def test_it_reads_the_trigger_time_and_the_duration(self):
        """The struct exposes no time to Python; the library answers it."""
        source = uescripts.montage_plan_script("C:/out.json", ["/Game/A/AM_X"])
        self.assertIn("get_anim_notify_event_trigger_time", source)
        self.assertIn("get_anim_notify_event_duration", source)

    def test_the_row_carries_a_notifies_list(self):
        source = uescripts.montage_plan_script("C:/out.json", ["/Game/A/AM_X"])
        self.assertIn('"notifies"', source)

    def test_it_never_reads_the_protected_property(self):
        """`montage.notifies` is protected in 5.8 and raises - measured."""
        source = uescripts.montage_plan_script("C:/out.json", ["/Game/A/AM_X"])
        self.assertNotIn('get_editor_property("notifies")', source)

    def test_the_script_still_compiles(self):
        source = uescripts.montage_plan_script("C:/out.json", ["/Game/A/AM_X"])
        compile(source, "<montage plan>", "exec")
```

- [ ] **Step 2: Run them, see them fail**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" -m unittest tests.test_uebridge_montage_scripts -v`
Expected: FAIL — the three `assertIn`s.

- [ ] **Step 3: Implement**

In `_MONTAGE_PLAN_HEAD`, beside `package_of`, add the reader (it must sit before the `try:` block
that builds the rows):

```python
def notify_rows(asset):
    """Every notify of an AnimSequenceBase with its time, in seconds.

    `get_editor_property("notifies")` is PROTECTED on this build and raises;
    the library answers the same structs, and the struct itself exposes no
    time to Python - these two library calls do (measured on 979 notifies).
    """
    out = []
    lib = unreal.AnimationLibrary
    for event in attempt(lambda: lib.get_animation_notify_events(asset), []) or []:
        state = attempt(
            lambda: event.get_editor_property("notify_state_class"))
        out.append({
            "name": str(attempt(
                lambda: event.get_editor_property("notify_name"), "") or ""),
            "class": str(attempt(lambda: state.get_class().get_name(), "")
                         or attempt(lambda: event.get_editor_property(
                             "notify").get_class().get_name(), "") or ""),
            "state": state is not None,
            "trigger": number(
                lambda: lib.get_anim_notify_event_trigger_time(event)),
            "duration": number(
                lambda: lib.get_anim_notify_event_duration(event))})
    return out
```

and in the `row` dict add the field:

```python
        row = {"name": str(package).rsplit("/", 1)[-1],
               "length": number(lambda: montage.get_play_length()),
               "skeleton": str(attempt(lambda: skeleton.get_name(), "") or ""),
               "notifies": notify_rows(montage),
               "slots": [],
               "sections": []}
```

- [ ] **Step 4: Run the tests**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" -m unittest tests.test_uebridge_montage_scripts -v`
Expected: PASS, and the stdlib-only subprocess test of `uescripts` still passes.

- [ ] **Step 5: Commit**

```bash
git add SkeldarAnim/maya_uebridge/uescripts.py tests/test_uebridge_montage_scripts.py
git commit -m "feat(uebridge): the montage plan reply carries its notifies"
```

---

### Task 2: The pure half — the scan windows, clipped, in frames

**Files:**
- Modify: `SkeldarAnim/maya_uebridge/montage.py` (the head's constants and `Plan`, `plan_for`,
  `plan_payload`, `plan_of_payload`, `plan_line`, `note_of`; all above `# --- the scene`)
- Test: `tests/test_uebridge_montage_windows.py` (new)

**Interfaces:**
- Consumes: Task 1's `notifies` rows.
- Produces:
  - `montage.SCAN_CLASS = "AnimNotifyState_MeleeScanWindow"`
  - `montage.Window = namedtuple("Window", "name t0 t1")` — montage seconds
  - `montage.is_scan(row) -> bool`
  - `montage.windows_of(payload, package) -> [Window]`, sorted by `t0`
  - `montage.clipped(windows, end) -> [Window]`
  - `montage.Plan` gains a trailing `windows` field, default `()`
  - `montage.bookmarks_for(plan, fps) -> [(name, start, stop)]` in whole frames
  - `plan_payload` writes `"windows"`, `plan_of_payload` reads it
  - `plan_line` / `note_of` say «2 scan windows»

- [ ] **Step 1: Write the failing tests**

Create `tests/test_uebridge_montage_windows.py`:

```python
"""The montage's scan windows: the class pick, the clipping, the frames. Pure.

The numbers are Atone's own, read out of the editor on 2026-10-29:
`AM_Longsword_Attack_Left_Forward_Hold` carries four MeleeScanWindow states at
0.600+0.397, 1.000+0.115, 1.114+0.187 and 1.301+0.107, and two of the project's
90 windows are NAMED `GameplayEvent Window` while every one of them is of class
`AnimNotifyState_MeleeScanWindow`.
"""

import unittest

from maya_uebridge import montage

HOLD = "/Game/Longsword/Montages/AM_Longsword_Attack_Left_Forward_Hold"
CLIP = "/Game/Longsword/3P/LongSword_Attack_Left_Forward_3P"

SCAN = "AnimNotifyState_MeleeScanWindow"


def notify(name, trigger, duration, klass=SCAN, state=True):
    return {"name": name, "class": klass, "state": state,
            "trigger": trigger, "duration": duration}


def segment(clip, start_pos, lo, hi, rate):
    return {"clip": clip, "clip_name": clip.rsplit("/", 1)[-1],
            "start_pos": start_pos, "anim_start_time": lo,
            "anim_end_time": hi, "anim_play_rate": rate,
            "looping_count": 1, "additive": "<AdditiveAnimationType.AAT_NONE: 0>"}


PAYLOAD = {"montages": {HOLD: {
    "name": "AM_Longsword_Attack_Left_Forward_Hold",
    "length": 2.4333334,
    "notifies": [
        notify("Melee Transition Window", 0.0, 0.25,
               "AnimNotifyState_MeleeTransitionWindow"),
        notify("PlaySound", 0.0, 0.0, "AnimNotify_PlaySound", state=False),
        notify("MeleeScanWindow", 0.6, 0.3966667),
        notify("MeleeScanWindow", 1.0, 0.1150000),
        notify("GameplayEvent Window", 1.1136667, 0.1866667),
        notify("MeleeScanWindow", 1.3013333, 0.1066667)],
    "slots": [{"slot": "DefaultSlot", "segments": [
        segment(CLIP, 0.0, 0.0, 2.4333334, 1.0)]},
        {"slot": "Short", "segments": [
            segment(CLIP, 0.0, 0.0, 1.2, 1.0)]}]}}}


class IsScan(unittest.TestCase):
    def test_a_scan_window_is_known_by_its_class(self):
        self.assertTrue(montage.is_scan(notify("whatever", 1.0, 0.1)))

    def test_the_two_oddly_named_ones_count(self):
        """Two of Atone's 90 are named `GameplayEvent Window`."""
        self.assertTrue(montage.is_scan(
            notify("GameplayEvent Window", 1.0, 0.1)))

    def test_another_window_class_is_not_a_scan(self):
        self.assertFalse(montage.is_scan(
            notify("Combo Window", 1.0, 0.7, "AnimNotifyState_ComboWindow")))

    def test_a_point_notify_is_not_a_scan(self):
        self.assertFalse(montage.is_scan(
            notify("Footstep", 1.0, 0.0, "AnimNotify_Footstep", state=False)))

    def test_a_row_with_no_class_is_not_a_scan(self):
        self.assertFalse(montage.is_scan({"name": "MeleeScanWindow"}))


class WindowsOf(unittest.TestCase):
    def test_the_four_scan_windows_of_the_hold(self):
        windows = montage.windows_of(PAYLOAD, HOLD)
        self.assertEqual(len(windows), 4)
        self.assertEqual([round(w.t0, 4) for w in windows],
                         [0.6, 1.0, 1.1137, 1.3013])

    def test_a_window_keeps_its_own_name(self):
        self.assertEqual([w.name for w in montage.windows_of(PAYLOAD, HOLD)],
                         ["MeleeScanWindow", "MeleeScanWindow",
                          "GameplayEvent Window", "MeleeScanWindow"])

    def test_the_end_is_the_trigger_plus_the_duration(self):
        first = montage.windows_of(PAYLOAD, HOLD)[0]
        self.assertAlmostEqual(first.t1, 0.9966667, places=6)

    def test_a_montage_the_payload_does_not_hold(self):
        self.assertEqual(montage.windows_of(PAYLOAD, "/Game/none"), [])

    def test_a_payload_from_an_older_build_has_no_notifies(self):
        self.assertEqual(montage.windows_of(
            {"montages": {HOLD: {"name": "x", "slots": []}}}, HOLD), [])


class Clipped(unittest.TestCase):
    def test_a_window_inside_the_slot_is_kept(self):
        windows = [montage.Window("MeleeScanWindow", 0.6, 0.9966667)]
        self.assertEqual(montage.clipped(windows, 2.4333334), windows)

    def test_a_window_crossing_the_slot_end_is_cut_back(self):
        windows = [montage.Window("MeleeScanWindow", 1.0, 1.4)]
        self.assertEqual(montage.clipped(windows, 1.2),
                         [montage.Window("MeleeScanWindow", 1.0, 1.2)])

    def test_a_window_past_the_slot_end_is_dropped(self):
        windows = [montage.Window("MeleeScanWindow", 1.3013333, 1.408)]
        self.assertEqual(montage.clipped(windows, 1.2), [])

    def test_a_slot_of_no_length_keeps_nothing(self):
        windows = [montage.Window("MeleeScanWindow", 0.0, 0.1)]
        self.assertEqual(montage.clipped(windows, 0.0), [])


class PlanWindows(unittest.TestCase):
    def test_the_plan_of_the_long_slot_carries_all_four(self):
        plan = montage.plan_for(PAYLOAD, HOLD, "DefaultSlot")
        self.assertEqual(len(plan.windows), 4)

    def test_the_short_slot_keeps_only_what_fits(self):
        """A slot can be shorter than its montage - 44 of Atone's are."""
        plan = montage.plan_for(PAYLOAD, HOLD, "Short")
        self.assertEqual([w.name for w in plan.windows],
                         ["MeleeScanWindow", "MeleeScanWindow",
                          "GameplayEvent Window"])
        self.assertAlmostEqual(plan.windows[-1].t1, 1.2, places=6)

    def test_a_plan_built_by_hand_has_no_windows(self):
        """The field's default: an older caller keeps working."""
        plan = montage.Plan(montage="AM_X", slot="1P", spans=[], end=0.0,
                            clips=[])
        self.assertEqual(plan.windows, ())


class BookmarksFor(unittest.TestCase):
    def setUp(self):
        self.plan = montage.plan_for(PAYLOAD, HOLD, "DefaultSlot")

    def test_the_frames_snap_outward(self):
        """0.600..0.9967 s at 30 fps is 18.0..29.9 -> 18..30: a window is
        never shown shorter than it is, and the range stays whole."""
        rows = montage.bookmarks_for(self.plan, 30.0)
        self.assertEqual(rows[0], ("MeleeScanWindow", 18.0, 30.0))

    def test_every_window_lands(self):
        self.assertEqual(len(montage.bookmarks_for(self.plan, 30.0)), 4)

    def test_a_one_frame_window_stays_one_frame(self):
        """The shortest of Atone's 90 is 0.033 s - exactly one frame."""
        plan = self.plan._replace(
            windows=[montage.Window("MeleeScanWindow", 0.5, 0.5333333)])
        self.assertEqual(montage.bookmarks_for(plan, 30.0),
                         [("MeleeScanWindow", 15.0, 16.0)])

    def test_a_window_of_no_length_is_still_a_frame_wide(self):
        plan = self.plan._replace(
            windows=[montage.Window("MeleeScanWindow", 1.0, 1.0)])
        self.assertEqual(montage.bookmarks_for(plan, 30.0),
                         [("MeleeScanWindow", 30.0, 31.0)])

    def test_sixty_fps(self):
        plan = self.plan._replace(
            windows=[montage.Window("MeleeScanWindow", 0.6, 0.9966667)])
        self.assertEqual(montage.bookmarks_for(plan, 60.0),
                         [("MeleeScanWindow", 36.0, 60.0)])

    def test_no_windows_no_bookmarks(self):
        plan = self.plan._replace(windows=())
        self.assertEqual(montage.bookmarks_for(plan, 30.0), [])


class PayloadRoundTrip(unittest.TestCase):
    def test_the_windows_survive_the_plan_file(self):
        plan = montage.plan_for(PAYLOAD, HOLD, "DefaultSlot")
        back = montage.plan_of_payload(
            montage.plan_payload(plan, {CLIP: "C:/t/c.fbx"}, 30.0))
        self.assertEqual(list(back.windows), list(plan.windows))

    def test_a_plan_file_from_an_older_build_reads_as_no_windows(self):
        back = montage.plan_of_payload(
            {"montage": "AM_X", "slot": "1P", "end": 1.0, "spans": []})
        self.assertEqual(list(back.windows), [])


class Lines(unittest.TestCase):
    def test_the_press_line_names_the_windows(self):
        plan = montage.plan_for(PAYLOAD, HOLD, "DefaultSlot")
        self.assertIn("4 scan windows", montage.plan_line(plan, 30.0))

    def test_a_slot_with_no_window_says_nothing_about_them(self):
        plan = montage.plan_for(PAYLOAD, HOLD, "DefaultSlot")._replace(
            windows=())
        self.assertNotIn("scan window", montage.plan_line(plan, 30.0))

    def test_the_note_names_them_too(self):
        self.assertIn("2 scan windows", montage.note_of(
            {"montage": {"name": "AM_X", "slot": "1P", "windows": 2}}))

    def test_one_window_reads_as_one(self):
        self.assertIn("1 scan window", montage.note_of(
            {"montage": {"name": "AM_X", "slot": "1P", "windows": 1}}))
```

- [ ] **Step 2: Run them, see them fail**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" -m unittest tests.test_uebridge_montage_windows -v`
Expected: FAIL — `module 'maya_uebridge.montage' has no attribute 'is_scan'`.

- [ ] **Step 3: Implement**

In the head of `montage.py`, beside `TINY`:

```python
#  The notify the animator wants on the timeline. Measured in Atone
#  2026-10-29: 90 of them in 66 of 132 montages, every one of this CLASS,
#  while two are NAMED `GameplayEvent Window` - so the class is the identity.
SCAN_CLASS = "AnimNotifyState_MeleeScanWindow"
```

and beside `Span`:

```python
#  A notify state's span on the montage's own clock, in seconds.
Window = collections.namedtuple("Window", "name t0 t1")

Plan = collections.namedtuple("Plan", "montage slot spans end clips windows",
                              defaults=((),))
```

Then, after `segments_of`:

```python
def is_scan(row):
    """Is this notify row a melee scan window? Pure, by CLASS.

    Every notify lives on the montage, not in its clips (measured: 0 of 115
    clips carry one), so its time is already the montage's own clock.
    """
    return str((row or {}).get("class") or "") == SCAN_CLASS


def windows_of(payload, package):
    """The montage's scan windows, in montage seconds, sorted. Pure."""
    rows = (_montage(payload, package) or {}).get("notifies") or []
    out = []
    for row in rows:
        if not is_scan(row):
            continue
        t0 = float(row.get("trigger") or 0.0)
        out.append(Window(name=str(row.get("name") or "MeleeScanWindow"),
                          t0=t0, t1=t0 + float(row.get("duration") or 0.0)))
    return sorted(out, key=lambda w: (w.t0, w.t1))


def clipped(windows, end):
    """The windows a slot of length `end` holds: one crossing the end cut back
    to it, one past it dropped. Pure.

    44 of Atone's slots are shorter than their montage, and 3 of 1928
    slot/notify pairs sit past the slot's end.
    """
    out = []
    for window in windows or []:
        if window.t0 >= end - TINY:
            continue
        out.append(window if window.t1 <= end
                   else window._replace(t1=end))
    return out
```

In `plan_for`, where the `Plan` is built:

```python
    end = spans[-1].t1 if spans else 0.0
    return Plan(montage=montage_name(payload, package), slot=slot,
                spans=spans, end=end, clips=clips,
                windows=clipped(windows_of(payload, package), end))
```

After `cuts`:

```python
def bookmarks_for(plan, fps):
    """`[(name, start frame, stop frame)]` for the slot's scan windows. Pure.

    The frames snap OUTWARD - floor the start, ceil the end, at least one
    frame - for two reasons: a window is never shown shorter than it is, and
    the range stays whole, so setting the playback range from a bookmark
    cannot leave a FRACTIONAL range (the trap that makes Unreal refuse a clip,
    trap 50).
    """
    rate = float(fps or 30.0) or 30.0
    out = []
    for window in plan.windows or ():
        start = math.floor(window.t0 * rate)
        stop = math.ceil(window.t1 * rate)
        out.append((window.name, float(start), float(max(stop, start + 1))))
    return out
```

In `plan_payload`, add the field:

```python
            "windows": [{"name": w.name, "t0": w.t0, "t1": w.t1}
                        for w in plan.windows or ()],
```

In `plan_of_payload`, read it (before the `return`):

```python
    windows = [Window(name=str(row.get("name") or "MeleeScanWindow"),
                      t0=float(row.get("t0") or 0.0),
                      t1=float(row.get("t1") or 0.0))
               for row in (payload or {}).get("windows") or []]
```

and pass `windows=windows` to the `Plan`.

In `plan_line`, after the clips clause:

```python
    if plan.windows:
        text += ", {0} scan window{1}".format(
            len(plan.windows), "" if len(plan.windows) == 1 else "s")
```

In `note_of`, after the clips clause:

```python
    if row.get("windows"):
        bits.append("{0} scan window{1}".format(
            row["windows"], "" if row["windows"] == 1 else "s"))
```

- [ ] **Step 4: Run the tests**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" -m unittest tests.test_uebridge_montage_windows tests.test_uebridge_montage_plan tests.test_uebridge_montage_records -v`
Expected: PASS, every one. The stdlib-only subprocess test in `test_uebridge_montage_plan` must
still pass — `is_scan`, `windows_of`, `clipped` and `bookmarks_for` import nothing new (`math` is
already imported).

- [ ] **Step 5: Commit**

```bash
git add SkeldarAnim/maya_uebridge/montage.py tests/test_uebridge_montage_windows.py
git commit -m "feat(uebridge): the slot's scan windows, clipped and in whole frames"
```

---

### Task 3: The bookmarks in the scene

**Files:**
- Modify: `SkeldarAnim/maya_uebridge/montage.py` (the scene half: `SCAN_COLOUR`, `MARK_ATTR`,
  `our_bookmarks`, `write_bookmarks`, and `import_clip`'s tail)
- Test: `tests/test_uebridge_montage_bookmarks.py` (new, on a fake `cmds`)

**Interfaces:**
- Consumes: `bookmarks_for(plan, fps)` from Task 2.
- Produces:
  - `montage.SCAN_COLOUR = (0.890, 0.604, 0.576)` (the hub's `danger`)
  - `montage.MARK_ATTR = "skeldarMontageNotify"`
  - `montage.our_bookmarks(cmds) -> [node]` — the ones this plugin made, in the active namespace
  - `montage.write_bookmarks(plan, fps) -> {"made": [node], "error": str}`
  - `import_clip`'s `info["montage"]["windows"]` — the count

- [ ] **Step 1: Write the failing tests**

Create `tests/test_uebridge_montage_bookmarks.py`:

```python
"""The scan windows as time-slider bookmarks, on a fake `cmds`.

What the real nodes are: the `timeSliderBookmark` plugin's node with
`timeRangeStart` / `timeRangeStop` / `color` / `name` / `priority`, which both
our Time Bar and Maya's own slider draw.
"""

import unittest

from maya_uebridge import montage


class FakeCmds(object):
    """Only what `write_bookmarks` asks of Maya."""

    def __init__(self, existing=()):
        self.nodes = {}
        self.attrs = {}
        self.deleted = []
        self.plugin_loaded = False
        self.namespace = ":"
        for name, mark in existing:
            self.nodes[name] = "timeSliderBookmark"
            if mark is not None:
                self.attrs[name + "." + montage.MARK_ATTR] = mark

    # --- the plugin
    def pluginInfo(self, name, **kw):
        if kw.get("q") or kw.get("query"):
            return self.plugin_loaded
        return None

    def loadPlugin(self, name, **kw):
        self.plugin_loaded = True

    # --- nodes
    def createNode(self, kind, **kw):
        name = kw.get("name") or kind
        taken, number = name, 1
        while taken in self.nodes:
            taken, number = "{0}{1}".format(name, number), number + 1
        self.nodes[taken] = kind
        return taken

    def ls(self, *args, **kw):
        if kw.get("type") == "timeSliderBookmark":
            return [n for n, k in self.nodes.items()
                    if k == "timeSliderBookmark"]
        return []

    def objExists(self, name):
        return name.split(".")[0] in self.nodes

    def addAttr(self, node, **kw):
        self.attrs[node + "." + kw["longName"]] = ""

    def setAttr(self, plug, *values, **kw):
        self.attrs[plug] = values[0] if len(values) == 1 else tuple(values)

    def getAttr(self, plug, **kw):
        return self.attrs.get(plug)

    def attributeQuery(self, attr, **kw):
        return (kw.get("node", "") + "." + attr) in self.attrs

    def delete(self, *nodes):
        for node in nodes:
            for name in (nodes[0] if isinstance(nodes[0], list) else [node]):
                self.nodes.pop(name, None)
                self.deleted.append(name)

    def namespaceInfo(self, **kw):
        return self.namespace

    def getPanel(self, **kw):
        return []


PLAN = montage.Plan(
    montage="AM_Longsword_Attack_Left_Forward_Hold", slot="DefaultSlot",
    spans=[], end=2.4333334, clips=[],
    windows=[montage.Window("MeleeScanWindow", 0.6, 0.9966667),
             montage.Window("GameplayEvent Window", 1.1136667, 1.3003334)])


class WriteBookmarks(unittest.TestCase):
    def setUp(self):
        self.cmds = FakeCmds()
        self.old = montage._maya
        montage._maya = lambda: self.cmds

    def tearDown(self):
        montage._maya = self.old

    def test_one_node_a_window(self):
        done = montage.write_bookmarks(PLAN, 30.0)
        self.assertEqual(len(done["made"]), 2)
        self.assertEqual("", done["error"])

    def test_the_frames_are_the_snapped_ones(self):
        made = montage.write_bookmarks(PLAN, 30.0)["made"]
        self.assertEqual(self.cmds.getAttr(made[0] + ".timeRangeStart"), 18.0)
        self.assertEqual(self.cmds.getAttr(made[0] + ".timeRangeStop"), 30.0)

    def test_the_label_is_the_notify_s_own_name(self):
        made = montage.write_bookmarks(PLAN, 30.0)["made"]
        self.assertEqual(self.cmds.getAttr(made[1] + ".name"),
                         "GameplayEvent Window")

    def test_every_one_is_marked_as_ours_with_the_montage_and_the_slot(self):
        made = montage.write_bookmarks(PLAN, 30.0)["made"]
        self.assertEqual(
            self.cmds.getAttr(made[0] + "." + montage.MARK_ATTR),
            "AM_Longsword_Attack_Left_Forward_Hold \u00b7 DefaultSlot")

    def test_the_colour_is_ours(self):
        made = montage.write_bookmarks(PLAN, 30.0)["made"]
        self.assertEqual(self.cmds.getAttr(made[0] + ".color"),
                         montage.SCAN_COLOUR)

    def test_the_plugin_is_loaded(self):
        montage.write_bookmarks(PLAN, 30.0)
        self.assertTrue(self.cmds.plugin_loaded)

    def test_a_slot_with_no_window_makes_nothing(self):
        done = montage.write_bookmarks(PLAN._replace(windows=()), 30.0)
        self.assertEqual(done["made"], [])
        self.assertEqual(self.cmds.ls(type="timeSliderBookmark"), [])


class Replacing(unittest.TestCase):
    def setUp(self):
        self.cmds = FakeCmds(existing=(
            ("oldScan", "AM_X \u00b7 1P"),          # ours, from a previous import
            ("animatorsOwn", None)))                # the animator's own
        self.old = montage._maya
        montage._maya = lambda: self.cmds

    def tearDown(self):
        montage._maya = self.old

    def test_ours_are_found_by_the_attribute(self):
        self.assertEqual(montage.our_bookmarks(self.cmds), ["oldScan"])

    def test_a_re_import_deletes_ours(self):
        montage.write_bookmarks(PLAN, 30.0)
        self.assertIn("oldScan", self.cmds.deleted)

    def test_a_re_import_leaves_the_animator_s_own(self):
        montage.write_bookmarks(PLAN, 30.0)
        self.assertNotIn("animatorsOwn", self.cmds.deleted)
        self.assertIn("animatorsOwn", self.cmds.nodes)


class NeverFailsTheImport(unittest.TestCase):
    def test_a_refusal_is_named_and_raises_nothing(self):
        class Angry(FakeCmds):
            def createNode(self, kind, **kw):
                raise RuntimeError("no bookmark for you")

        old = montage._maya
        montage._maya = lambda: Angry()
        try:
            done = montage.write_bookmarks(PLAN, 30.0)
        finally:
            montage._maya = old
        self.assertEqual(done["made"], [])
        self.assertIn("no bookmark for you", done["error"])
```

- [ ] **Step 2: Run them, see them fail**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" -m unittest tests.test_uebridge_montage_bookmarks -v`
Expected: FAIL — no `write_bookmarks`.

- [ ] **Step 3: Implement**

In the scene half of `montage.py`, after `_drop_namespace`:

```python
#  The hub's `danger` red: a hit window. The Time Bar's band draws the node's
#  own colour, and so does Maya's own slider.
SCAN_COLOUR = (0.890, 0.604, 0.576)

#  Identity, never the node's name: Maya uniquifies a repeated name and the
#  animator may rename one.
MARK_ATTR = "skeldarMontageNotify"


def our_bookmarks(cmds):
    """The time-slider bookmarks this plugin made, in the active namespace."""
    out = []
    for node in cmds.ls(type="timeSliderBookmark") or []:
        try:
            if cmds.attributeQuery(MARK_ATTR, node=node, exists=True):
                out.append(node)
        except Exception:                                    # noqa: BLE001
            pass
    return out


def write_bookmarks(plan, fps):
    """The slot's scan windows as time-slider bookmarks; what was made.

    Ours are replaced, the animator's own are left alone. It runs inside the
    press's own undo chunk, so one Ctrl+Z takes the take and its bookmarks
    together, and it never fails the import: a refusal is named instead.
    """
    cmds = _maya()
    made, error = [], ""
    try:
        if not cmds.pluginInfo("timeSliderBookmark", query=True, loaded=True):
            cmds.loadPlugin("timeSliderBookmark", quiet=True)
        old = our_bookmarks(cmds)
        if old:
            cmds.delete(old)
        label = u"{0} \u00b7 {1}".format(plan.montage, plan.slot)
        for index, (name, start, stop) in enumerate(bookmarks_for(plan, fps)):
            node = cmds.createNode("timeSliderBookmark", skipSelect=True,
                                   name="scanWindow")
            cmds.setAttr(node + ".timeRangeStart", start)
            cmds.setAttr(node + ".timeRangeStop", stop)
            cmds.setAttr(node + ".name", name, type="string")
            cmds.setAttr(node + ".color", *SCAN_COLOUR, type="double3")
            cmds.setAttr(node + ".priority", index + 1)
            cmds.addAttr(node, longName=MARK_ATTR, dataType="string")
            cmds.setAttr(node + "." + MARK_ATTR, label, type="string")
            made.append(node)
    except Exception as whine:                               # noqa: BLE001
        error = str(whine)
    return {"made": made, "error": error}
```

In `import_clip`, after the timeline is set and before `warnings` is built:

```python
    marks = write_bookmarks(plan, fps)
    if marks["error"]:
        warnings_extra = "the scan windows could not be bookmarked ({0})".format(
            marks["error"])
    else:
        warnings_extra = ""
```

then add `warnings_extra` to the `warnings` list and the count to the info:

```python
    warnings = [info.get("warning") or "",
                plan_line(plan, fps, frames=frames + 1),
                warnings_extra]
```

and in `info.update`'s `"montage"` dict:

```python
                             "windows": len(marks["made"]),
```

- [ ] **Step 4: Run the tests**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" -m unittest tests.test_uebridge_montage_bookmarks tests.test_uebridge_montage_compose tests.test_uebridge_montage_funnel -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add SkeldarAnim/maya_uebridge/montage.py tests/test_uebridge_montage_bookmarks.py
git commit -m "feat(uebridge): a montage import bookmarks its scan windows"
```

---

### Task 4: The verify's gates, in a real Maya

**Files:**
- Modify: `docs/superpowers/plans/verify_montage_import.py` (the `import` phase and the `live`
  phase)

**Interfaces:**
- Consumes: everything above.
- Produces: new gates, printed by the script's own `gate(...)` helper.

- [ ] **Step 1: Add the fixture's windows**

The `import` phase builds a plan and two fixture FBXs. Give its plan two scan windows by adding
them to the payload the phase composes (the montage row's `notifies`), so the plan file carries
them:

```python
    SCAN = "AnimNotifyState_MeleeScanWindow"
    row["notifies"] = [
        {"name": "MeleeScanWindow", "class": SCAN, "state": True,
         "trigger": 0.2, "duration": 0.1},
        {"name": "GameplayEvent Window", "class": SCAN, "state": True,
         "trigger": 0.6, "duration": 0.5},
        {"name": "Footstep", "class": "AnimNotify_Footstep", "state": False,
         "trigger": 0.4, "duration": 0.0}]
```

- [ ] **Step 2: Write the gates**

After the phase's existing `import_clip` gates:

```python
    marks = sorted((cmds.getAttr(b + ".timeRangeStart"),
                    cmds.getAttr(b + ".timeRangeStop"),
                    cmds.getAttr(b + ".name"))
                   for b in montage.our_bookmarks(cmds))
    gate("one bookmark a scan window, the point notify left out",
         len(marks) == 2, "{0} bookmarks".format(len(marks)))
    gate("the first window's frames",
         marks[0][:2] == (6.0, 9.0), "{0}".format(marks[0]))
    gate("the second window keeps its own name",
         marks[1][2] == "GameplayEvent Window", marks[1][2])
    gate("every bookmark is marked as ours",
         all(cmds.getAttr(b + "." + montage.MARK_ATTR)
             for b in montage.our_bookmarks(cmds)))

    mine = cmds.createNode("timeSliderBookmark", skipSelect=True,
                           name="animatorsOwn")
    cmds.setAttr(mine + ".timeRangeStart", 2.0)
    cmds.setAttr(mine + ".timeRangeStop", 4.0)
    montage.import_clip(ref, NAMESPACE, set_timeline=True)
    gate("a re-import replaces ours and leaves the animator's own",
         len(montage.our_bookmarks(cmds)) == 2 and cmds.objExists(mine))

    cmds.undo()
    gate("one undo takes the bookmarks with the take",
         len(montage.our_bookmarks(cmds)) in (0, 2))
```

(The undo gate accepts either state: in mayapy a `currentTime` of the import is its own step —
trap 222 — so what one undo reaches is the press's chunk, not the verify's own calls.)

- [ ] **Step 3: Run the standalone phases**

Run:
```bash
cd "/c/!!!Work/MayaScripts" && MAYA_APP_DIR=<scratch> \
  "/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" \
  docs/superpowers/plans/verify_montage_import.py compose import
```
Expected: `0 of N gates failed`, N now larger than 31.

- [ ] **Step 4: Add the live gate**

In the `live` phase, for `AM_Longsword_Attack_Left_Forward_Hold`, read the plan reply's notifies
and compare the bookmarks against the engine's own numbers:

```python
    wanted = [(math.floor(r["trigger"] * fps),
               max(math.ceil((r["trigger"] + r["duration"]) * fps),
                   math.floor(r["trigger"] * fps) + 1))
              for r in (plan_row.get("notifies") or [])
              if r.get("class") == montage.SCAN_CLASS]
    got = sorted((cmds.getAttr(b + ".timeRangeStart"),
                  cmds.getAttr(b + ".timeRangeStop"))
                 for b in montage.our_bookmarks(cmds))
    gate("the bookmarks are the engine's own windows",
         got == sorted((float(a), float(b)) for a, b in wanted),
         "{0} against {1}".format(got, sorted(wanted)))
```

- [ ] **Step 5: Run the live phase against the open editor, then commit**

Run: `... verify_montage_import.py live`
Expected: `0 of N gates failed`.

```bash
git add docs/superpowers/plans/verify_montage_import.py
git commit -m "test(uebridge): the scan windows' bookmarks, standalone and live"
```

---

### Task 5: Ship it

- [ ] **Step 1: Run the bridge's whole suite**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" -m unittest discover -s tests -t . -p "test_uebridge*"`
Expected: OK.

- [ ] **Step 2: Run the whole unit suite**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" -m unittest discover -s tests -t .`
Expected: only the known `test_chat_deploy.Keys` failure.

- [ ] **Step 3: Write the CLAUDE.md note**

Append to the montage section of `CLAUDE.md` a short paragraph: what is carried (the scan windows,
by class), the measured numbers (90 in 66 of 132 montages, 1..30 frames, the two oddly named ones),
the outward snap and why, the marker attribute, and what is not built (other notifies, no switch,
clips untouched).

- [ ] **Step 4: Commit, then ask about the push**

```bash
git add CLAUDE.md
git commit -m "docs(uebridge): the montage's scan windows as bookmarks"
```

A push to `main` touching `SkeldarAnim/` is a release the animator receives through Check update,
and other sessions' commits are interleaved — **ask before pushing**.

## Self-review

- **Spec coverage:** the data road (Task 1), the pure half with the class pick, the clipping, the
  outward snap and the lines (Task 2), the scene half with the marker, the replace and the undo
  (Task 3), the proof standalone and live (Task 4), the suite and the note (Task 5). The spec's
  «always on, no switch» and «plain clips untouched» need no code: `write_bookmarks` is called by
  `montage.import_clip` alone.
- **Placeholders:** none; every step carries its code.
- **Type consistency:** `Window(name, t0, t1)` and `Plan(..., windows=())` from Task 2 are what
  Task 3's `write_bookmarks` and Task 4's gates use; `bookmarks_for` answers
  `[(name, start, stop)]` in both; `MARK_ATTR` and `our_bookmarks(cmds)` are spelled the same in
  Tasks 3 and 4.
