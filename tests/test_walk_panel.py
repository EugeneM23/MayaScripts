"""Walk Builder (maya_walk.panel): the hub card of the parametric walk on a fake cmds - the controls, the
parameters (maya_walk.gait: Main shown, one tab of the others), a parameter kept as a change from the cycle's own
and pinned, the macros, the Diagnosis, the presses, a walked skeleton's settings taken, the memory."""

import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.join(os.path.dirname(HERE), "SkeldarAnim")
if PLUGIN not in sys.path:
    sys.path.insert(0, PLUGIN)

from maya_walk import panel, scene             # noqa: E402
from maya_walk import model as wm              # noqa: E402
from maya_walk import gait                     # noqa: E402
from maya_poselib import store                 # noqa: E402


def write_card(library, folder, name, kind="character", anim=False):
    """A pose card in `library` (two bones), its path."""
    eye = [1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0]
    bones = {"root": {"parent": None, "canonical": "root", "rest": eye, "world": eye},
             "pelvis": {"parent": "root", "canonical": "pelvis", "rest": eye, "world": eye}}
    data = {"format": store.ANIM_FORMAT if anim else store.FORMAT, "kind": kind, "bones": bones,
            "character": {"label": name}, "members": sorted(bones), "objects": []}
    return store.write(library, folder, name, data)


class FakeCmds(object):
    """Just enough of maya.cmds for the card: records controls, answers queries."""

    def __init__(self):
        self.values = {}
        self.vars = {}
        self.created = []
        self.items = {}
        self.managed = {}
        self.jobs = {}
        self.killed = []
        self.selection = []
        self.current_menu = None
        self.labels = {}
        self.enabled = {}
        self.buttons = set()

    def _made(self, kind, name, **kw):
        self.created.append((kind, name, kw))
        return name

    def columnLayout(self, name=None, exists=False, edit=False, manage=None, **kw):
        if exists:
            return name in self.managed
        if edit:
            self.managed[name] = manage
            return name
        if name:
            self.managed[name] = kw.get("manage", True) if manage is None else manage
        return self._made("columnLayout", name or "col", manage=manage, **kw)

    def rowLayout(self, *a, **kw):
        return self._made("rowLayout", "row", **kw)

    def flowLayout(self, *a, **kw):
        return self._made("flowLayout", "flow", **kw)

    def setParent(self, *a, **kw):
        pass

    def text(self, name=None, edit=False, label=None, exists=False, **kw):
        if exists:
            return name in self.values
        self.values[name] = label
        if not edit:
            self._made("text", name, label=label, **kw)
        return name

    def button(self, name=None, edit=False, exists=False, enable=None, **kw):
        if exists:
            return name in self.buttons
        if edit:
            if enable is not None:
                self.enabled[name] = enable
            return name
        self.buttons.add(name)
        return self._made("button", name, **kw)

    def optionMenu(self, name, exists=False, query=False, edit=False, value=None, itemListLong=False, **kw):
        if exists:
            return name in self.items
        if query and itemListLong:
            return ["%s|%s" % (name, label) for label in self.items[name]]
        if query:
            return self.values.get(name)
        if edit:
            self.values[name] = value
            return name
        self.items[name] = []
        self.current_menu = name
        return self._made("optionMenu", name, **kw)

    def menuItem(self, label=None, parent=None, **kw):
        if parent in self.items:
            self.items[parent].append(label)
            if self.values.get(parent) is None:
                self.values[parent] = label
        return self._made("menuItem", label, parent=parent, **kw)

    def popupMenu(self, **kw):
        return self._made("popupMenu", "popup", **kw)

    def deleteUI(self, item):
        menu, label = item.split("|", 1)
        self.items[menu].remove(label)
        if self.values.get(menu) == label:
            self.values[menu] = None

    def _slider(self, kind, name, query=False, edit=False, exists=False, value=None, **kw):
        if exists:
            return name in self.values
        if query:
            return self.values[name]
        if value is not None:
            self.values[name] = value
        if "label" in kw:
            self.labels[name] = kw["label"]
        if not edit:
            self._made(kind, name, value=value, **kw)
        return name

    def floatSliderGrp(self, name, **kw):
        return self._slider("floatSliderGrp", name, **kw)

    def intSliderGrp(self, name, **kw):
        return self._slider("intSliderGrp", name, **kw)

    def checkBox(self, name, query=False, edit=False, exists=False, value=None, **kw):
        if exists:
            return name in self.values
        if query:
            return self.values[name]
        self.values[name] = value
        if not edit:
            self._made("checkBox", name, value=value, **kw)
        return name

    def iconTextRadioCollection(self, name, **kw):
        return name

    def iconTextRadioButton(self, name, exists=False, edit=False, select=None, **kw):
        if exists:
            return name in self.values
        self.values[name] = bool(select)
        if not edit:
            self._made("iconTextRadioButton", name, select=select, **kw)
        return name

    def optionVar(self, exists=None, query=None, q=None, floatValue=None, stringValue=None, intValue=None,
                  remove=None):
        if remove is not None:
            self.vars.pop(remove, None)
            return None
        if exists is not None:
            return exists in self.vars
        if query is not None or q is not None:
            return self.vars[query if query is not None else q]
        name, value = floatValue or stringValue or intValue
        self.vars[name] = value

    def scriptJob(self, event=None, parent=None, exists=None, kill=None, force=False):
        if exists is not None:
            return exists in self.jobs
        if kill is not None:
            self.killed.append(kill)
            self.jobs.pop(kill, None)
            return None
        number = len(self.jobs) + len(self.killed) + 1
        self.jobs[number] = (event, parent)
        return number

    def ls(self, node=None, uuid=False, selection=False, **kw):
        if selection:
            return list(self.selection)
        return ["uuid-" + node] if uuid else [node]

    def select(self, nodes, replace=True, **kw):
        self.selection = list(nodes)

    def textScrollList(self, name, exists=False, query=False, edit=False, allItems=False, removeAll=False,
                       append=None, selectIndexedItem=None, deselectAll=False, **kw):
        rows = self.items.setdefault(name, [])
        if exists:
            return name in self.values
        if query and allItems:
            return list(rows)
        if query and selectIndexedItem:
            return list(self.values.get(name) or [])
        if not edit:
            self.values[name] = []
            return self._made("textScrollList", name, **kw)
        if removeAll:
            del rows[:]
        if append is not None:
            rows.append(append)
        if deselectAll:
            self.values[name] = []
        if selectIndexedItem is not None:
            self.values[name] = list(selectIndexedItem)
        return name


class FakeReport(object):
    changed = True

    def text(self):
        return "spikes: hand_l 23 (91 deg)"

    def short(self):
        return "cleaned: 1 spike"


_WALK = []


def synthetic():
    """The synthetic walker of tests/test_walkmodel.py (one per run: analysing it costs)."""
    if not _WALK:
        from tests import test_walkmodel as tw
        _WALK.append(tw.walk())
    return _WALK[0]


class CardTests(unittest.TestCase):

    def setUp(self):
        import maya_hubstyle
        self.hubstyle = maya_hubstyle
        maya_hubstyle.take_marks()
        self.fake = FakeCmds()
        self.applied = []
        self.memos = {}
        self.findings = None                      # what the fake apply's Diagnosis answers
        self.state = {"loaded": {}, "target": None}
        names = ("_cmds", "walk_names", "walk_exists", "load_walk", "apply", "selected_root", "selected_top",
                 "selected_roots", "memo_of", "pick", "target_root", "_state", "fix_posture", "folder", "walkers",
                 "walker_label", "set_listed", "has_source", "has_keys", "own_name", "capture_source",
                 "restore_source", "keys_changed", "drop_source")
        self.saved = (panel._cmds, dict((n, getattr(scene, n)) for n in names), dict(panel.JOB), panel._library,
                      getattr(sys, "_skeldar_walk_diag", None))
        sys._skeldar_walk_diag = None
        self.temp = tempfile.mkdtemp()
        self.library = os.path.join(self.temp, "library").replace("\\", "/")
        os.makedirs(self.library)
        panel._library = lambda: self.library
        scene.folder = lambda: os.path.join(self.temp, "walks")
        panel.JOB.clear()
        panel._SELECTED[0] = None
        panel._cmds = lambda: self.fake
        scene._cmds = lambda: self.fake
        scene.walk_names = lambda: ["asd", "dw"]
        scene.walk_exists = lambda name: name in ("asd", "dw") or scene.is_card(name)
        self.loaded = []
        self.walk = synthetic()
        self.own = gait.own(self.walk)

        def load_walk(name, given=None):
            self.loaded.append((name, given))
            return self.walk, {}, 0, FakeReport()
        scene.load_walk = load_walk
        scene._state = lambda: self.state
        self.fixed = []

        def fix_posture(name, given=None):
            self.fixed.append((name, given))
            return FakeReport(), "Fix posture: %s foot_l out: mirrored" % name
        scene.fix_posture = fix_posture

        def apply(root, walk, given, pose, parts, pose_card=None, record=True, params=None):
            self.applied.append((root, walk, given, pose_card, parts, params))
            self.state["target"] = "uuid-" + root
            memo = dict(self.memos.get(root, {}), walk=walk, knobs=dict(given), listed=True, parts=list(parts),
                        version=3)
            if params is not None:
                memo["params"] = scene.plain_params(params)
            self.memos[root] = memo
            info = {"clean": FakeReport()}
            if self.findings is not None:
                info["diagnosis"] = list(self.findings)
            return None, info, "%s on %s" % (walk, root)
        scene.apply = apply
        scene.walkers = lambda: sorted(r for r, m in self.memos.items() if m.get("walk") and m.get("listed", True))
        scene.walker_label = lambda root: root.rsplit("|", 1)[-1]
        self.keyed = set()                        # skeletons that carry keys of their own
        self.sources = {}                         # root: its kept own cycle
        scene.has_keys = lambda root: root in self.keyed
        scene.has_source = lambda root: root in self.sources
        self.reloaded = set()                     # walkers a clip was loaded onto since their walk
        scene.keys_changed = lambda root: root in self.reloaded
        scene.drop_source = lambda root: self.sources.pop(root, None)
        self.fake.vars[panel.OPTION + "walk"] = "asd"            # the walk well's active walk (a saved file here)

        def own_name(root):
            return self.sources[root]
        scene.own_name = own_name

        def capture_source(root):
            self.sources.setdefault(root, scene.OWN + root.strip("|"))
            return self.sources[root]
        scene.capture_source = capture_source
        self.restored = []

        def restore_source(root):
            self.restored.append(root)
            self.memos.pop(root, None)
            return "%s restored" % root
        scene.restore_source = restore_source
        real_exists = scene.walk_exists
        scene.walk_exists = lambda name: scene.is_own(name) or real_exists(name)

        def set_listed(root, listed):
            self.memos[root]["listed"] = listed
        scene.set_listed = set_listed

        def selected_roots():
            if not self.fake.selection:
                raise scene.Refusal("select a bone of a skeleton first")
            return list(self.fake.selection)
        scene.selected_roots = selected_roots

        def selected_root():
            if not self.fake.selection:
                raise scene.Refusal("select a bone of a skeleton first")
            return self.fake.selection[0]
        scene.selected_root = selected_root
        scene.selected_top = lambda: self.fake.selection[0] if self.fake.selection else None
        scene.memo_of = lambda root: self.memos.get(root, {})

        def target_root():
            if not self.state["target"]:
                raise scene.Refusal("select a skeleton and press Pick first")
            return self.state["target"][len("uuid-"):]
        scene.target_root = target_root

    def tearDown(self):
        panel._cmds, functions, job, panel._library, diag = self.saved
        sys._skeldar_walk_diag = diag
        shutil.rmtree(self.temp, ignore_errors=True)
        for name, value in functions.items():
            setattr(scene, name, value)
        panel.JOB.clear()
        panel.JOB.update(job)
        self.hubstyle.take_marks()

    def made(self, kind):
        return [c for c in self.fake.created if c[0] == kind]

    def command(self, control, flag="changeCommand"):
        for c in self.fake.created:
            if c[1] == control:
                return c[2][flag]
        raise KeyError(control)

    def release(self, name, value):
        """A parameter's slider (or chip) set and let go."""
        control = panel._control(name) if name in gait.P else name
        self.fake.values[control] = value
        return self.command(control)()

    def params(self):
        return self.applied[-1][5]

    def assertChange(self, change, kind, x):
        self.assertEqual(change[0], kind)
        self.assertAlmostEqual(change[1], x, places=9)

    def test_the_card(self):
        panel.build_panel()
        marks = dict((m.name, (m.role, m.icon)) for m in self.hubstyle.take_marks())
        self.assertEqual(marks[panel.SUBTITLE][0], "subtitle")
        self.assertEqual(marks[panel.STATUS][0], "status")
        self.assertEqual(marks[panel.APPLY_BTN], ("primary", "walk"))
        self.assertEqual(marks[panel.RESET_BTN], ("secondary", "refresh"))
        self.assertEqual(marks[panel.SAVE_WALK_BTN], ("tool", "device-floppy"))
        self.assertFalse(hasattr(panel, "SAVE_POSE_BTN"))          # a pose is saved by the Pose Library
        self.assertFalse(hasattr(panel, "WALK_MENU"))           # the walk is a card in the walk well
        self.assertIn(panel.WALK_WELL, [c[1] for c in self.made("columnLayout")])
        self.assertIn("Walk: asd", self.fake.values[panel.WALK_WELL_TEXT])        # no Qt here: its line
        self.assertIn(panel.POSE_WELL, [c[1] for c in self.made("columnLayout")])   # the well's placeholder
        #  the walks folder; Pick's own; the list; and every parameter's right button
        self.assertEqual(len(self.made("popupMenu")), 3 + len(gait.PARAMS))
        self.assertEqual(marks[panel.MEAN_UPDATE_BTN], ("primary", "refresh"))
        self.assertIn("rigpose", [key for row in panel.GROUP_ROWS for key in row])
        chips = [c[1] for c in self.made("checkBox")]
        toggles = [panel._control(p.name) for key, _, names in panel.GROUPS for p in gait.PARAMS
                   if p.name in names and p.kind == "toggle"]
        self.assertEqual(chips, [panel._part_control(p) for p, _ in panel.PART_LABELS] + [panel.IN_PLACE_BOX]
                         + toggles + [panel.PHYSICS_BOX])
        self.assertTrue(all(marks[c][0] == "chip" for c in chips))
        tabs = [(c[1], c[2]["collection"]) for c in self.made("iconTextRadioButton")]
        rows = [key for row in panel.GROUP_ROWS for key in row]
        self.assertEqual(sorted(rows), sorted(k for k, _, _ in panel.GROUPS))
        self.assertEqual(tabs, [(panel._side_tab(m), panel.SIDE_TABS) for m, _ in panel.SIDE_MODES]
                         + [(panel._group_tab(k), panel.GROUP_TABS) for k in rows])
        sliders = [c[1] for c in self.made("floatSliderGrp")]
        self.assertEqual(sorted(sliders), sorted([panel._control(p.name) for p in gait.PARAMS if p.kind != "toggle"]
                                                 + [panel._control(k) for k in ("pose", "seam", "smooth")]
                                                 + [panel.SPEED, panel.WEIGHT, panel.STRENGTH]))
        self.assertEqual(self.made("intSliderGrp"), [])
        #  every parameter at the active cycle's own value, in its unit
        self.assertAlmostEqual(self.fake.values[panel._control("step")], self.own["step"], places=6)
        self.assertAlmostEqual(self.fake.values[panel._control("tempo")], self.own["tempo"], places=6)
        self.assertEqual(self.fake.labels[panel._control("step")], "Step, cm")
        self.assertAlmostEqual(self.fake.values[panel.SPEED], self.own["speed"], places=6)
        self.assertEqual(self.fake.values[panel.CHARACTER], gait.CHARACTERS[0][0])
        self.assertEqual(marks[panel.CLEAN_REPORT][0], "caption")       # a note would hide (CLAUDE.md trap 226)
        self.assertEqual(marks[panel.DIAG_CAPTION][0], "caption")
        self.assertEqual(self.fake.values[panel.DIAG_CAPTION], "Diagnosis: Pick a walker")
        self.assertFalse(any(self.fake.managed[panel._diag_row(i)] for i in range(panel.DIAG_ROWS)))
        self.assertTrue(panel.is_open())

    def test_main_is_always_shown_and_one_tab_at_a_time(self):
        panel.build_panel()
        shown = [k for k, _, _ in panel.GROUPS if self.fake.managed[panel._group_column(k)]]
        self.assertEqual(shown, ["timing"])                      # the first, when none is remembered
        panel.group_changed("legs")()
        shown = [k for k, _, _ in panel.GROUPS if self.fake.managed[panel._group_column(k)]]
        self.assertEqual(shown, ["legs"])
        self.assertEqual(self.fake.vars[panel.OPTION + "group"], "legs")
        self.fake.created, self.fake.managed = [], {}
        panel.build_panel()                                      # remembered across a rebuild
        self.assertEqual([k for k, _, _ in panel.GROUPS if self.fake.managed[panel._group_column(k)]], ["legs"])
        self.fake.vars[panel.OPTION + "group"] = "chest"         # a tab of the knobs before: its parameters' tab
        self.fake.created, self.fake.managed = [], {}
        panel.build_panel()
        self.assertEqual([k for k, _, _ in panel.GROUPS if self.fake.managed[panel._group_column(k)]], ["trunk"])
        main = [c[1] for c in self.made("floatSliderGrp") if c[1] in [panel._control(n) for n in panel.MAIN_PARAMS]]
        self.assertEqual(len(main), len(panel.MAIN_PARAMS))       # Main stands in no tab

    def test_a_released_parameter_is_a_change_from_the_cycle_s_own_and_pinned(self):
        panel.build_panel()
        self.fake.selection = ["|root"]
        panel.press_apply()
        self.release("step", 1.2 * self.own["step"])
        self.assertChange(self.params()["changes"]["step"], "ratio", 1.2)
        self.assertIn("step", self.params()["pins"])
        self.assertEqual(self.fake.labels[panel._control("step")], "Step, cm" + panel.PIN_MARK)
        self.release("lean", self.own["lean"] + 5.0)              # an offset kind: degrees added
        self.assertAlmostEqual(self.params()["changes"]["lean"][1], 5.0, places=6)
        self.release("step", self.own["step"])                    # back at its own: no change, still held
        self.assertNotIn("step", self.params()["changes"])
        self.assertIn("step", self.params()["pins"])
        self.assertEqual(self.applied[-1][:2], ("|root", "asd"))
        self.assertEqual(self.fake.vars[panel.OPTION + "walk"], "asd")

    def test_nothing_selected_says_so(self):
        panel.build_panel()
        self.assertIn("select", panel.press_apply())
        self.assertEqual(self.applied, [])

    def test_a_parameter_rekeys_every_walker_with_the_same_change_and_none_says_so(self):
        panel.build_panel()
        self.assertIn("Pick", panel.slider_changed())
        self.assertEqual(self.applied, [])
        self.fake.selection = ["|a", "|b"]
        panel.press_apply()
        self.fake.selection = []                                 # the list stays the list
        self.release("bounce", 1.5 * self.own["bounce"])
        keyed = self.applied[-2:]
        self.assertEqual([a[0] for a in keyed], ["|a", "|b"])
        for a in keyed:
            self.assertChange(a[5]["changes"]["bounce"], "ratio", 1.5)

    def test_pick_adds_every_selected_skeleton_to_the_list(self):
        panel.build_panel()
        self.fake.selection = ["|a|root", "|b|root"]
        line = panel.press_apply()
        self.assertIn("2 skeletons pick asd", line)
        self.assertEqual([a[0] for a in self.applied], ["|a|root", "|b|root"])
        self.assertEqual(self.fake.items[panel.WALKER_LIST], ["root - asd", "root - asd"])

    def test_the_pose_parts_and_clean_reach_apply(self):
        panel.build_panel()
        self.fake.vars[panel.OPTION + "walk"] = "dw"
        card = write_card(self.library, "Walk poses", "goblin")
        self.fake.vars[panel.OPTION + "poseCard"] = "Walk poses/goblin.pose"
        self.fake.values[panel._part_control("arms")] = False
        self.fake.values[panel._control("smooth")] = 2.0
        self.fake.selection = ["|root"]
        self.assertEqual(panel.press_apply(), "dw on |root")
        root, walk, given, pose, parts, params = self.applied[-1]
        self.assertEqual((root, walk, pose), ("|root", "dw", "Walk poses/goblin.pose"))
        self.assertTrue(os.path.isdir(card))
        self.assertNotIn("arms", parts)
        self.assertEqual((given["smooth"], params["clean"]["smooth"]), (2.0, 2.0))
        self.assertEqual(sorted(given), sorted(panel.CARD_KNOBS))   # the model's knobs are the parameters'

    def test_the_right_button_back_to_the_clip_or_follow_the_links(self):
        panel.build_panel()
        self.fake.selection = ["|root"]
        panel.press_apply()
        self.release("arm_swing", 2.0 * self.own["arm_swing"])
        panel.reset_param("arm_swing")                           # held at the clip's: the links leave it alone
        self.assertNotIn("arm_swing", self.params()["changes"])
        self.assertIn("arm_swing", self.params()["pins"])
        self.assertIn(panel.PIN_MARK, self.fake.labels[panel._control("arm_swing")])
        panel.free_param("arm_swing")                            # free again: it follows the speed
        self.assertNotIn("arm_swing", self.params()["pins"])
        self.assertNotIn(panel.PIN_MARK, self.fake.labels[panel._control("arm_swing")])

    def test_speed_moves_step_and_tempo_and_gives_way_to_them(self):
        panel.build_panel()
        self.fake.selection = ["|root"]
        panel.press_apply()
        self.release("step", 1.1 * self.own["step"])
        self.release(panel.SPEED, 2.0 * self.own["speed"])
        params = self.params()
        self.assertAlmostEqual(params["macros"]["speed"], 2.0 * self.own["speed"], places=6)
        self.assertNotIn("step", params["changes"])               # Speed takes over the step set by hand
        self.assertNotIn("step", params["pins"])
        vals = scene.param_values(self.walk, params)[1]
        self.assertAlmostEqual(vals["step"], self.own["step"] * 2.0 ** 0.5, places=4)
        self.assertAlmostEqual(self.fake.values[panel.SPEED], 2.0 * self.own["speed"], places=4)
        self.assertIn(panel.PIN_MARK, self.fake.labels[panel.SPEED])
        self.release("tempo", 0.9 * self.own["tempo"])            # a Tempo by hand: the Speed macro gives way
        self.assertNotIn("speed", self.params()["macros"])

    def test_weight_a_character_its_strength_and_the_physics(self):
        panel.build_panel()
        self.fake.selection = ["|root"]
        panel.press_apply()
        self.release(panel.WEIGHT, 0.6)
        self.release(panel.CHARACTER, "Tired")
        self.release(panel.STRENGTH, 0.5)
        self.release(panel.PHYSICS_BOX, False)
        params = self.params()
        self.assertEqual((params["macros"]["weight"], params["character"], params["strength"], params["physics"]),
                         (0.6, "Tired", 0.5, False))
        self.release(panel.CHARACTER, gait.CHARACTERS[0][0])      # Natural: none
        self.assertEqual(self.params()["character"], "")

    def test_reset_puts_the_clip_back_and_rekeys(self):
        panel.build_panel()
        self.fake.selection = ["|root"]
        panel.press_apply()
        self.release("bounce", 2.0 * self.own["bounce"])
        self.release(panel.WEIGHT, 0.5)
        panel.press_reset()
        params = self.params()
        self.assertEqual((params["changes"], params["pins"], params["macros"]), ({}, [], {}))
        self.assertAlmostEqual(self.fake.values[panel._control("bounce")], self.own["bounce"], places=6)

    def test_the_diagnosis_shows_the_walker_keyed_last_and_fix_sets_it(self):
        self.findings = [gait.Finding("arms_in_step", "Arms in step with the legs", {"arm_lag": 3.0}),
                         gait.Finding("physics", "Physics gave way", {})]
        panel.build_panel()
        self.fake.selection = ["|root"]
        panel.press_apply()
        self.assertEqual(self.fake.values[panel.DIAG_CAPTION], "Diagnosis - root - asd")
        self.assertEqual([self.fake.managed[panel._diag_row(i)] for i in range(panel.DIAG_ROWS)],
                         [True, True, False, False])
        self.assertEqual(self.fake.values[panel._diag_text(0)], "Arms in step with the legs")
        self.assertEqual(self.fake.enabled[panel._diag_fix(1)], False)   # nothing to set: no Fix
        self.findings = []
        line = self.command(panel._diag_fix(0), "command")()
        self.assertIn("fixed: Arms in step", line)
        kind, x = self.params()["changes"]["arm_lag"]
        self.assertAlmostEqual(self.own["arm_lag"] + x, 3.0, places=6)
        self.assertIn("arm_lag", self.params()["pins"])
        self.assertEqual(self.fake.values[panel.DIAG_CAPTION], "Diagnosis - root - asd: nothing to say")

    def test_take_settings_puts_a_walker_s_parameters_in_the_card(self):
        params = scene.plain_params({"changes": {"step": ("ratio", 1.25)}, "pins": ["step"],
                                     "macros": {"weight": 0.4}, "character": "Happy", "pose": 1.0})
        self.memos["|walked"] = {"walk": "dw", "pose": "", "pose_card": "Swords/sword.pose",
                                 "parts": ["torso", "feet"], "knobs": {}, "params": params, "version": 3}
        panel.build_panel()
        self.fake.selection = ["|walked"]
        panel.refresh()                                          # selecting it does not take its settings
        self.assertNotIn("step", panel.card_params()["changes"])
        panel.take_settings("|walked")
        self.assertEqual(self.applied, [])                       # taking them keys nothing
        p = panel.card_params()
        self.assertEqual((p["changes"]["step"], p["macros"], p["character"], p["pose"]),
                         (("ratio", 1.25), {"weight": 0.4}, "Happy", 1.0))
        self.assertEqual(self.fake.vars[panel.OPTION + "poseCard"], "Swords/sword.pose")
        self.assertAlmostEqual(self.fake.values[panel._control("step")], 1.25 * self.own["step"], places=6)
        self.assertFalse(self.fake.values[panel._part_control("knees")])

    def test_a_walker_keyed_before_the_parameters_brings_its_knobs_read_as_parameters(self):
        self.memos["|old"] = {"walk": "asd", "pose": "", "parts": list(scene.ALL_PARTS), "version": 2,
                              "knobs": dict(wm.DEFAULTS, stride=1.2, bob=1.5, pose=0.5)}
        panel.build_panel()
        panel.take_settings("|old")
        p = panel.card_params()
        self.assertEqual((p["changes"]["step"], p["changes"]["bounce"], p["pose"]),
                         (("ratio", 1.2), ("ratio", 1.5), 0.5))

    def test_the_knobs_a_card_remembered_before_become_parameters_once(self):
        self.fake.vars[panel.OPTION + "knob_stride"] = 1.3
        self.fake.vars[panel.OPTION + "knob_bob"] = 1.0
        self.fake.vars[panel.OPTION + "knob_overlap"] = 2.0
        panel.build_panel()
        p = panel.card_params()
        self.assertEqual(p["changes"]["step"], ("ratio", 1.3))
        self.assertNotIn("bounce", p["changes"])                  # at its default: nothing to translate
        self.assertAlmostEqual(p["changes"]["arm_lag"][1], 1.6)   # Overlap: the upper arm's share
        self.fake.vars[panel.OPTION + "knob_stride"] = 2.0        # done once: a later build leaves the card's
        panel.build_panel()
        self.assertEqual(panel.card_params()["changes"]["step"], ("ratio", 1.3))

    def test_a_skeleton_not_walked_is_named(self):
        panel.build_panel()
        self.fake.selection = ["|a|root"]
        panel.refresh()
        self.assertEqual(self.fake.values[panel.SUBTITLE], "root: Pick adds it with asd")

    def test_a_press_with_the_card_closed_reads_the_memory(self):
        self.fake.vars[panel.OPTION + "params"] = json.dumps({"changes": {"step": ["ratio", 1.4]}, "pins": ["step"]})
        self.fake.vars[panel.OPTION + "walk"] = "dw"
        self.fake.vars[panel.OPTION + "parts"] = json.dumps(["torso"])
        self.fake.selection = ["|root"]
        panel.press_apply()
        root, walk, given, pose, parts, params = self.applied[-1]
        self.assertEqual((walk, params["changes"]["step"], parts, pose), ("dw", ("ratio", 1.4), ("torso",), None))
        self.assertFalse(panel.is_open())

    def test_the_clean_knobs_reach_apply_and_fix_posture_rekeys(self):
        panel.build_panel()
        self.fake.values[panel._control("smooth")] = 2.0
        self.fake.selection = ["|root"]
        panel.press_apply()
        self.assertEqual(self.applied[-1][2]["smooth"], 2.0)
        count = len(self.applied)
        self.fake.vars[panel.OPTION + "walk"] = "dw"
        line = panel.press_fix_posture()
        self.assertEqual(self.fixed[-1][0], "dw")
        self.assertIn("Fix posture: dw", line)
        self.assertEqual(len(self.applied), count)              # nobody walks dw: nothing keyed
        self.fake.vars[panel.OPTION + "walk"] = "asd"
        panel.press_fix_posture()
        self.assertEqual(len(self.applied), count + 1)          # the walker on asd keyed again
        self.assertEqual(self.fake.values[panel.CLEAN_REPORT], "spikes: hand_l 23 (91 deg)")

    def test_fix_posture_with_no_target_only_writes_the_walk(self):
        panel.build_panel()
        line = panel.press_fix_posture()
        self.assertIn("Fix posture", line)
        self.assertEqual(self.applied, [])

    def test_the_in_place_chip_rekeys_the_target(self):
        panel.build_panel()
        self.fake.selection = ["|root"]
        panel.press_apply()
        self.assertEqual(self.applied[-1][2]["in_place"], 0.0)
        self.fake.values[panel.IN_PLACE_BOX] = True
        panel.in_place_changed()
        self.assertEqual((self.applied[-1][2]["in_place"], self.params()["in_place"]), (1.0, 1.0))
        self.assertEqual(self.fake.vars[panel.OPTION + "knob_in_place"], 1.0)
        panel._set_knobs({"in_place": 0.0})
        self.assertFalse(self.fake.values[panel.IN_PLACE_BOX])

    def test_a_failing_press_says_why(self):
        panel.build_panel()
        self.fake.selection = ["|root"]

        def broken(*a, **kw):
            raise RuntimeError("boom")
        scene.apply = broken
        self.assertEqual(panel.press_apply(), "Walk Builder failed: boom")

    def test_one_selection_job_per_card(self):
        panel.build_panel()
        first = panel.JOB[""]
        (event, job), parent = self.fake.jobs[first]
        self.assertEqual((event, parent), ("SelectionChanged", panel.STATUS))
        #  the refresh, run only while the card is on screen (maya_hubqt.when_seen)
        self.assertEqual(job._skeldar_seen, (panel.STATUS, panel.refresh))
        panel.build_panel()
        self.assertEqual(self.fake.killed, [first])
        self.assertEqual(len(self.fake.jobs), 1)

    def test_a_walker_that_fails_is_named_and_the_others_keyed(self):
        panel.build_panel()
        self.fake.selection = ["|a", "|b"]
        panel.press_apply()
        apply = scene.apply

        def picky(root, *a, **kw):
            if root == "|a":
                raise scene.Refusal("a is gone")
            return apply(root, *a, **kw)
        scene.apply = picky
        line = panel.slider_changed()
        self.assertIn("1 walker keyed: b - asd", line)
        self.assertIn("a - asd: a is gone", line)

    def test_removing_from_the_list_and_selecting_a_walker(self):
        panel.build_panel()
        self.fake.selection = ["|a", "|b"]
        panel.press_apply()
        self.memos["|b"]["walk"] = "dw"
        self.fake.selection = ["|b"]
        panel.refresh()                                          # its cycle the active one, nobody keyed
        self.assertEqual(self.fake.vars[panel.OPTION + "walk"], "dw")
        self.assertEqual(self.fake.values[panel.WALKER_LIST], [2])
        self.assertIn("b walks dw", self.fake.values[panel.SUBTITLE])
        self.fake.values[panel.WALKER_LIST] = [1]
        panel.list_selected()
        self.assertEqual(self.fake.selection, ["|a"])
        panel.remove_from_list()
        self.assertFalse(self.memos["|a"]["listed"])
        self.assertEqual(self.fake.items[panel.WALKER_LIST], ["b - dw"])
        count = len(self.applied)
        panel.slider_changed()
        self.assertEqual([a[0] for a in self.applied[count:]], ["|b"])

    def test_pick_puts_the_card_on_every_skeleton_and_keeps_their_own_animation(self):
        panel.build_panel()
        self.keyed = {"|a"}                                      # a carries an animation of its own
        self.fake.selection = ["|a", "|b"]
        panel.press_apply()                                      # the card comes first («Карточка важнее»)
        self.assertEqual([a[1] for a in self.applied], ["asd", "asd"])
        self.assertEqual(self.sources, {"|a": scene.OWN + "a"})  # a's own animation kept before the card
        self.fake.values[panel.WALKER_LIST] = [1]
        panel.use_own_picked()                                   # the list's right button brings it back
        self.assertEqual(self.applied[-1][:2], ("|a", scene.OWN + "a"))
        self.fake.selection = ["|a"]                             # a walker on its own cycle: Pick puts the card
        panel.press_apply()
        self.assertEqual(self.applied[-1][:2], ("|a", "asd"))

    def test_pick_own_processes_each_skeleton_on_its_own_cycle(self):
        panel.build_panel()
        self.keyed = {"|a", "|b"}                                # both carry an animation of their own
        self.fake.selection = ["|a", "|b", "|c"]                 # c has no keys: the walk well's card
        line = panel.press_apply_own()
        self.assertEqual([a[1] for a in self.applied], [scene.OWN + "a", scene.OWN + "b", "asd"])
        self.assertIn("3 skeletons processed", line)
        self.assertEqual(self.sources, {"|a": scene.OWN + "a", "|b": scene.OWN + "b"})
        self.fake.selection = []
        self.release("bounce", 1.5 * self.own["bounce"])          # one change, every cycle from its own
        keyed = dict((a[0], a) for a in self.applied[-3:])
        self.assertEqual([keyed[r][1] for r in ("|a", "|b", "|c")], [scene.OWN + "a", scene.OWN + "b", "asd"])
        for r in keyed:
            self.assertChange(keyed[r][5]["changes"]["bounce"], "ratio", 1.5)
        count = len(self.applied)
        self.keyed.discard("|a")                                 # its keys are the result now: the kept one stays
        self.fake.selection = ["|a"]
        panel.press_apply_own()
        self.assertEqual(self.applied[count][1], scene.OWN + "a")
        self.fake.values[panel.WALKER_LIST] = [1]                # Restore: its original keys, out of the list
        panel.restore_picked()
        self.assertEqual(self.restored, ["|a"])

    def test_choosing_a_card_puts_it_on_card_walkers_and_leaves_own_cycles(self):
        panel.build_panel()
        self.keyed = {"|own"}
        self.fake.selection = ["|own"]
        panel.press_apply_own()
        self.fake.selection = ["|card"]
        panel.press_apply()
        self.assertEqual(self.memos["|card"]["walk"], "asd")
        self.fake.selection = []
        self.release("tempo", 0.5 * self.own["tempo"])            # twice as fast: a ratio, on every cycle
        count = len(self.applied)
        rel = "Walk cycles/dw.anim"
        os.makedirs(os.path.join(self.library, rel))
        from maya_poselib import store as st
        real = st.is_anim
        st.is_anim = lambda path: True
        try:
            panel.take_walk_card(os.path.join(self.library, rel))
        finally:
            st.is_anim = real
        keyed = self.applied[count:]
        self.assertEqual([a[0] for a in keyed], ["|card"])      # nothing selected: every card walker, no own one
        self.assertEqual(keyed[0][1], scene.card_walk(rel))
        self.assertChange(keyed[0][5]["changes"]["tempo"], "ratio", 0.5)   # the change goes with the card
        self.assertEqual(self.memos["|own"]["walk"], scene.OWN + "own")
        self.fake.selection = ["|own"]                           # selected: the card reaches it too
        count = len(self.applied)
        rel2 = "Walk cycles/asd.anim"
        os.makedirs(os.path.join(self.library, rel2))
        st.is_anim = lambda path: True
        try:
            panel.take_walk_card(os.path.join(self.library, rel2))
        finally:
            st.is_anim = real
        self.assertEqual([a[:2] for a in self.applied[count:]], [("|own", scene.card_walk(rel2))])

    def test_a_clip_loaded_onto_a_walker_is_what_the_next_pick_reads(self):
        panel.build_panel()
        del self.fake.vars[panel.OPTION + "walk"]                # an empty walk well
        self.keyed = {"|a"}
        self.fake.selection = ["|a"]
        panel.press_apply()
        self.assertEqual(self.applied[-1][1], scene.OWN + "a")   # no card: its own animation, never a saved file
        self.reloaded.add("|a")                                  # a new clip loaded onto it
        count = len(self.applied)
        line = panel.slider_changed()                            # a parameter does not wipe the new clip
        self.assertEqual(len(self.applied), count)
        self.assertIn("new keys on it since the walk", line)
        self.sources["|a"] = scene.OWN + "a"
        panel.press_apply()                                      # Pick drops the old kept cycle, reads the new
        self.assertEqual(self.applied[-1][1], scene.OWN + "a")
        self.assertEqual(len(self.applied), count + 1)

    def test_an_empty_well_and_no_animation_is_refused(self):
        panel.build_panel()
        del self.fake.vars[panel.OPTION + "walk"]
        self.fake.selection = ["|bare"]
        self.assertIn("walk well holds no card", panel.press_apply())
        self.assertEqual(self.applied, [])

    def test_with_no_walk_card_the_first_own_cycle_is_the_active_one(self):
        scene.walk_names = lambda: []
        del self.fake.vars[panel.OPTION + "walk"]
        panel.build_panel()
        self.keyed = {"|a", "|b"}
        self.fake.selection = ["|a", "|b"]
        panel.press_apply()                                      # no card at all: each on its own animation
        self.assertEqual(self.fake.vars[panel.OPTION + "walk"], scene.OWN + "a")
        self.assertEqual([a[1] for a in self.applied], [scene.OWN + "a", scene.OWN + "b"])
        self.assertTrue(all("tempo" not in a[5]["changes"] for a in self.applied))   # each at its own tempo


class SideTests(CardTests):
    """[Both | Left | Right]: a two-sided parameter sets both sides, or one side alone."""

    def test_left_sets_the_left_side_alone(self):
        panel.build_panel()
        self.fake.selection = ["|root"]
        panel.press_apply()
        panel.side_changed("l")()
        self.assertEqual(self.fake.labels[panel._control("foot_lift")], "Foot lift, cm L")
        self.assertEqual(self.fake.labels[panel._control("step")], "Step, cm")           # one-sided: as it is
        self.release("foot_lift", 2.0 * self.own["foot_lift_l"])
        changes = self.params()["changes"]
        self.assertChange(changes["foot_lift_l"], "ratio", 2.0)
        self.assertNotIn("foot_lift", changes)
        self.assertNotIn("foot_lift_r", changes)
        panel.side_changed("r")()                       # the right shows its own
        self.assertAlmostEqual(self.fake.values[panel._control("foot_lift")], self.own["foot_lift_r"], places=6)
        panel.side_changed("both")()                    # Both marks a parameter whose sides differ
        self.assertEqual(self.fake.labels[panel._control("foot_lift")], "Foot lift, cm *" + panel.PIN_MARK)

    def test_both_links_a_parameter_s_sides_again(self):
        panel.build_panel()
        self.fake.selection = ["|root"]
        panel.press_apply()
        panel.side_changed("l")()
        self.release("arm_swing", 0.0)
        panel.side_changed("both")()
        self.release("arm_swing", 1.5 * self.own["arm_swing"])
        changes = self.params()["changes"]
        self.assertChange(changes["arm_swing"], "ratio", 1.5)
        self.assertNotIn("arm_swing_l", changes)
        self.assertNotIn("arm_swing_l", self.params()["pins"])
        self.assertEqual(self.fake.labels[panel._control("arm_swing")], "Arm swing, deg" + panel.PIN_MARK)

    def test_a_one_sided_parameter_is_the_same_in_every_mode(self):
        panel.build_panel()
        self.fake.selection = ["|root"]
        panel.press_apply()
        panel.side_changed("r")()
        self.release("bounce", 2.0 * self.own["bounce"])
        self.assertEqual(list(self.params()["changes"]), ["bounce"])
        self.assertChange(self.params()["changes"]["bounce"], "ratio", 2.0)

    def test_reset_links_every_side(self):
        panel.build_panel()
        self.fake.selection = ["|root"]
        panel.press_apply()
        panel.side_changed("l")()
        self.release("toe_out", self.own["toe_out_l"] + 10.0)
        panel.press_reset()
        self.assertEqual(self.params()["changes"], {})

    def test_the_right_button_on_one_side_lets_that_side_go(self):
        panel.build_panel()
        self.fake.selection = ["|root"]
        panel.press_apply()
        panel.side_changed("l")()
        self.release("elbow", self.own["elbow_l"] + 20.0)
        panel.side_changed("r")()
        self.release("elbow", self.own["elbow_r"] + 10.0)
        panel.free_param("elbow")                       # the right's alone
        changes = self.params()["changes"]
        self.assertIn("elbow_l", changes)
        self.assertNotIn("elbow_r", changes)


class HubTests(unittest.TestCase):

    def test_the_section(self):
        import maya_hub
        sec = maya_hub.section("walk")
        self.assertEqual((sec.label, sec.module, sec.builder, sec.frame, sec.group, sec.icon),
                         ("Walk Builder", "maya_walk.panel", "build_panel", "skeldarHubFrameWalk",
                          "animation", "walk"))
        keys = [s.key for s in maya_hub.SECTIONS]
        #  after Tail Builder, and Dynamics (2026-10-26) between them
        self.assertEqual(keys.index("walk"), keys.index("dynamics") + 1)
        self.assertEqual(keys.index("dynamics"), keys.index("tailbuilder") + 1)
        self.assertEqual(panel.HUB_SECTION, "walk")

    def test_the_icons(self):
        import maya_hubicons
        for name in ("walk", "device-floppy"):
            self.assertIn("<path", maya_hubicons.svg(name))

    def test_ships(self):
        import install
        self.assertIn("maya_walk", install.payload())

    def test_the_hotkey_rows(self):
        import maya_hotkeys
        self.assertEqual(maya_hotkeys.row("window.walk")[4].args, ("maya_walk.panel", "show_window"))
        found = maya_hotkeys.row("walk.apply")
        self.assertEqual(found[1], "SkeldarAnim.Walk Builder")
        self.assertIs(found[4].func, maya_hotkeys._walk)
        self.assertEqual(found[4].args, ("press_apply",))

    def test_importing_the_package_imports_nothing_heavy(self):
        import subprocess
        code = ("import sys; sys.path.insert(0, %r); import maya_walk; "
                "print(sorted(k for k in sys.modules if k.startswith(('maya', 'numpy'))))" % PLUGIN)
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120)
        self.assertEqual(out.stdout.strip(), "['maya_walk']", out.stderr)


if __name__ == "__main__":
    unittest.main()


class PoseCardTests(unittest.TestCase):
    """The pose is a Pose Library card dropped into the well (2026-10-15)."""

    setUp = CardTests.setUp
    tearDown = CardTests.tearDown

    def test_a_dropped_card_is_the_pose_and_rekeys_the_target(self):
        panel.build_panel()
        self.fake.selection = ["|root"]
        panel.press_apply()
        card = write_card(self.library, "Swords", "two_handed_sword")
        self.fake.values[panel._control("pose")] = 0.0
        line = panel.take_card(card)
        self.assertIn("pose card two_handed_sword (Pose share set to 1)", line)
        self.assertEqual(self.fake.vars[panel.OPTION + "poseCard"], "Swords/two_handed_sword.pose")
        self.assertEqual(self.applied[-1][3], "Swords/two_handed_sword.pose")
        self.assertEqual(self.applied[-1][2]["pose"], 1.0)
        self.assertIn("two_handed_sword", self.fake.values[panel.POSE_WELL_TEXT])
        path, name, thumbnail, note = panel.well_state()
        self.assertEqual((name, thumbnail, note), ("two_handed_sword", "", ""))

    def test_an_animation_or_objects_card_is_refused_and_changes_nothing(self):
        panel.build_panel()
        self.fake.selection = ["|root"]
        panel.press_apply()
        count = len(self.applied)
        anim = write_card(self.library, "", "Run", anim=True)
        self.assertIn("animation card", panel.take_card(anim))
        objects = write_card(self.library, "", "Cam", kind="objects")
        self.assertIn("card of objects", panel.take_card(objects))
        self.assertEqual(len(self.applied), count)
        self.assertNotIn(panel.OPTION + "poseCard", self.fake.vars)

    def test_clear_takes_the_pose_away(self):
        panel.build_panel()
        card = write_card(self.library, "", "goblin")
        panel.take_card(card)
        self.fake.selection = ["|root"]
        panel.press_apply()
        panel.clear_card()
        self.assertEqual(self.fake.vars[panel.OPTION + "poseCard"], "")
        self.assertIsNone(self.applied[-1][3])

    def test_a_card_gone_is_said_in_the_well(self):
        card = write_card(self.library, "", "goblin")
        panel.take_card(card)
        shutil.rmtree(card)
        self.assertEqual(panel.well_state()[3], "the card is gone from the library")

    def test_an_old_pose_name_means_its_migrated_card(self):
        write_card(self.library, "Walk poses", "goblin")
        self.fake.vars[panel.OPTION + "pose"] = "goblin"
        self.assertEqual(panel.chosen_card(), "Walk poses/goblin.pose")
        self.fake.vars[panel.OPTION + "pose"] = "missing"
        self.assertIsNone(panel.chosen_card())

    def test_several_cards_one_active_the_target_keyed_with_it(self):
        panel.build_panel()
        self.fake.selection = ["|root"]
        panel.press_apply()
        sword = write_card(self.library, "Swords", "sword")
        goblin = write_card(self.library, "", "goblin")
        panel.take_card(sword)
        panel.take_card(goblin)
        self.assertEqual(panel.card_list(), ["Swords/sword.pose", "goblin.pose"])
        self.assertEqual([row[1] for row in panel.well_rows()], ["sword", "goblin"])
        self.assertEqual([row[4] for row in panel.well_rows()], [False, True])
        self.assertEqual(self.applied[-1][3], "goblin.pose")
        panel.pick_card(sword)
        self.assertEqual(self.applied[-1][3], "Swords/sword.pose")
        self.assertEqual(panel.card_list(), ["Swords/sword.pose", "goblin.pose"])   # the order kept
        self.assertIn("2 cards in the well", self.fake.values[panel.POSE_WELL_TEXT])

    def test_removing_cards_and_no_pose_active(self):
        panel.build_panel()
        sword = write_card(self.library, "", "sword")
        goblin = write_card(self.library, "", "goblin")
        panel.take_card(sword)
        panel.take_card(goblin)
        self.fake.selection = ["|root"]
        panel.press_apply()
        self.assertIn("taken out of the well", panel.remove_card(sword))
        self.assertEqual((panel.card_list(), panel.chosen_card()), (["goblin.pose"], "goblin.pose"))
        panel.clear_card()                                        # none active, the card stays
        self.assertEqual((panel.card_list(), panel.chosen_card()), (["goblin.pose"], None))
        self.assertIsNone(self.applied[-1][3])
        panel.take_card(goblin)
        panel.remove_card(goblin)                                 # the active one: the walk's own posture
        self.assertEqual((panel.card_list(), panel.chosen_card()), ([], None))
        self.assertIsNone(self.applied[-1][3])
        panel.take_card(sword)
        panel.remove_all_cards()
        self.assertEqual(panel.card_list(), [])

    def test_a_card_picked_before_the_list_heads_it(self):
        self.fake.vars[panel.OPTION + "poseCard"] = "old.pose"
        self.assertEqual(panel.card_list(), ["old.pose"])


class RekeyLaterTests(unittest.TestCase):
    """A press that keys every walker again (a pose card, a knob) keys them on Maya's next idle, ONCE however
    many presses came before it ran, under a progress window Esc stops (2026-10-16: two pose cards switched with
    several walkers in the list - every click re-keyed them all while Maya stood still, and the clicks made
    meanwhile stacked into more of them: «переключение между ними перестает работать и кажется плагин тоже»)."""

    def setUp(self):
        CardTests.setUp(self)
        sys._skeldar_walk_rekey = None                        # the session's re-key state starts afresh
        self.jobs = []
        self.saved_later = panel._later
        panel._later = self.jobs.append
        self.fake.about = lambda **kw: False                  # a Maya with its UI: there is an idle
        for root in ("|a", "|b"):
            self.memos[root] = {"walk": "asd", "knobs": {}, "listed": True, "parts": []}

    def tearDown(self):
        panel._later = self.saved_later
        sys._skeldar_walk_rekey = None
        CardTests.tearDown(self)

    def run_jobs(self):
        jobs, self.jobs[:] = list(self.jobs), []
        for job in jobs:
            job()

    def test_a_pose_click_lights_the_card_at_once_and_keys_the_walkers_on_idle(self):
        panel.build_panel()
        sword = write_card(self.library, "", "sword")
        goblin = write_card(self.library, "", "goblin")
        line = panel.take_card(sword)
        self.assertEqual(panel.chosen_card(), "sword.pose")
        self.assertEqual(self.applied, [])
        self.assertIn("keying 2 walkers", line)
        panel.take_card(goblin)
        panel.pick_card(sword)                                    # clicked in turn before Maya was idle
        panel.pick_card(goblin)
        self.assertEqual(panel.chosen_card(), "goblin.pose")
        self.assertEqual(len(self.jobs), 4)
        self.run_jobs()
        self.assertEqual([(a[0], a[3]) for a in self.applied], [("|a", "goblin.pose"), ("|b", "goblin.pose")])
        self.assertIn("pose card goblin | 2 walkers keyed", self.fake.values[panel.STATUS])

    def test_parameters_released_in_a_row_key_every_walker_once_with_the_last_value(self):
        panel.build_panel()
        for ratio in (1.1, 1.2, 1.3):
            self.fake.values[panel._control("step")] = ratio * self.own["step"]
            panel.param_changed("step")()
        self.assertEqual(self.applied, [])
        self.run_jobs()
        self.assertEqual([a[0] for a in self.applied], ["|a", "|b"])
        self.assertAlmostEqual(self.applied[-1][5]["changes"]["step"][1], 1.3, places=9)

    def test_with_nobody_listed_there_is_nothing_to_wait_for(self):
        self.memos.clear()
        sword = write_card(self.library, "", "sword")
        self.assertIn("select skeletons and press Pick", panel.take_card(sword))
        self.assertEqual(self.jobs, [])

    def test_esc_in_the_progress_window_stops_after_the_walker_it_is_on(self):
        self.memos["|c"] = {"walk": "asd", "knobs": {}, "listed": True, "parts": []}
        calls = []

        def progress_window(**kw):
            calls.append(kw)
            if kw.get("query"):
                return sum(1 for c in calls if c.get("edit")) >= 2        # Esc seen before the second walker
            return None
        self.fake.progressWindow = progress_window
        line = panel.rekey_all()
        self.assertEqual([a[0] for a in self.applied], ["|a"])
        self.assertIn("1 walker keyed: a - asd", line)
        self.assertIn("stopped by Esc - not keyed: b - asd, c - asd", line)
        self.assertEqual(calls[0].get("maxValue"), 3)
        self.assertTrue(calls[0].get("isInterruptable"))
        self.assertTrue(any(c.get("endProgress") for c in calls))

    def test_a_newer_press_takes_the_rest_over_between_walkers(self):
        line = panel.rekey_all(stop=lambda: len(self.applied) >= 1)
        self.assertEqual([a[0] for a in self.applied], ["|a"])
        self.assertIn("a newer press keys the rest: b - asd", line)

    def test_an_idle_inside_the_progress_window_never_nests_and_the_press_made_there_is_served_after(self):
        panel.build_panel()
        sword = write_card(self.library, "", "sword")
        goblin = write_card(self.library, "", "goblin")
        panel.take_card(sword)
        clicked = []

        def progress_window(**kw):
            if kw.get("query") and len(self.applied) == 1 and not clicked:
                clicked.append(panel.pick_card(goblin))           # a click the progress window let through ...
                self.run_jobs()                                   # ... and an idle Maya ran right there
            return False if kw.get("query") else None
        self.fake.progressWindow = progress_window
        self.run_jobs()                                           # the sword's re-key: stopped after |a
        self.assertTrue(clicked)
        self.assertEqual([(a[0], a[3]) for a in self.applied], [("|a", "sword.pose")])
        self.assertIn("a newer press keys the rest: b - asd", self.fake.values[panel.STATUS])
        self.assertEqual(len(self.jobs), 1)                       # one more job, for the click
        self.run_jobs()
        self.assertEqual([(a[0], a[3]) for a in self.applied],
                         [("|a", "sword.pose"), ("|a", "goblin.pose"), ("|b", "goblin.pose")])
        self.assertIn("pose card goblin | 2 walkers keyed", self.fake.values[panel.STATUS])
        self.run_jobs()
        self.assertEqual((len(self.applied), self.jobs), (3, []))

    def test_one_walker_needs_no_progress_window_nor_does_batch(self):
        calls = []
        self.fake.progressWindow = lambda **kw: calls.append(kw)
        del self.memos["|b"]
        panel.rekey_all()
        self.memos["|b"] = {"walk": "asd", "knobs": {}, "listed": True, "parts": []}
        self.fake.about = lambda **kw: True                       # batch: no window to show
        panel.rekey_all()
        self.assertEqual(calls, [])

    def test_in_batch_the_walkers_are_keyed_at_once(self):
        del self.fake.about                                       # no Maya to ask: as batch
        sword = write_card(self.library, "", "sword")
        line = panel.take_card(sword)
        self.assertEqual(self.jobs, [])
        self.assertEqual([a[0] for a in self.applied], ["|a", "|b"])
        self.assertIn("pose card sword", line)
        self.assertIn("| 2 walkers keyed: a - asd, b - asd", line)

    def test_the_job_runs_in_the_card_it_was_pressed_in(self):
        import maya.utils
        import maya_hubcopy as hubcopy
        panel._later = self.saved_later
        caught, seen = [], []
        had = getattr(maya.utils, "executeDeferred", None)
        maya.utils.executeDeferred = caught.append
        try:
            scope = hubcopy.new_scope("walk")
            with hubcopy.entered(scope):
                panel._later(lambda: seen.append(hubcopy.current()))
            self.assertEqual(len(caught), 1)
            caught[0]()
            self.assertEqual(seen, [scope])
            hubcopy.close(scope, self.fake)
        finally:
            if had is None:
                del maya.utils.executeDeferred
            else:
                maya.utils.executeDeferred = had


class EvaluatedTests(unittest.TestCase):
    """scene.evaluated: a walk's evaluations kept on the walk object, so a switch back to a pose already keyed
    skips the model (2026-10-16: two pose cards switched over several walkers ran it on every walker every time -
    85 % of a re-key)."""

    def walk(self):
        class Walk(object):
            def __init__(self):
                self.calls = 0

            def evaluate(self, knobs=None, pose=None):
                self.calls += 1
                return ("result", self.calls)
        return Walk()

    def test_the_same_knobs_and_pose_reuse_the_result(self):
        walk, prepared = self.walk(), object()
        first = scene.evaluated(walk, {"stride": 1.0}, {"filtered": 1}, prepared, ("torso",))
        again = scene.evaluated(walk, {"stride": 1.0}, {"filtered": 2}, prepared, ("torso",))
        self.assertIs(first, again)
        self.assertEqual(walk.calls, 1)

    def test_other_knobs_parts_or_pose_evaluate_again(self):
        walk, sword, goblin = self.walk(), object(), object()
        scene.evaluated(walk, {"stride": 1.0}, {}, sword, ("torso",))
        scene.evaluated(walk, {"stride": 1.1}, {}, sword, ("torso",))
        scene.evaluated(walk, {"stride": 1.0}, {}, sword, ("arms",))
        scene.evaluated(walk, {"stride": 1.0}, {}, goblin, ("torso",))
        scene.evaluated(walk, {"stride": 1.0}, None)
        self.assertEqual(walk.calls, 5)

    def test_two_poses_switched_back_and_forth_evaluate_once_each(self):
        walk, sword, goblin = self.walk(), object(), object()
        for _ in range(3):
            scene.evaluated(walk, {"pose": 1.0}, {}, sword, ("torso",))
            scene.evaluated(walk, {"pose": 1.0}, {}, goblin, ("torso",))
        self.assertEqual(walk.calls, 2)

    def test_only_the_last_few_are_kept(self):
        walk = self.walk()
        for i in range(scene.EVALS_KEPT + 1):
            scene.evaluated(walk, {"stride": float(i)}, None)
        scene.evaluated(walk, {"stride": 0.0}, None)               # the oldest went
        self.assertEqual(walk.calls, scene.EVALS_KEPT + 2)
        scene.evaluated(walk, {"stride": float(scene.EVALS_KEPT)}, None)
        self.assertEqual(walk.calls, scene.EVALS_KEPT + 2)
