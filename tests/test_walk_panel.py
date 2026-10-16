"""Walk Builder (maya_walk.panel): the hub card of the parametric walk on a fake cmds - the controls, the one
knob group shown, the presses, a walked skeleton read back by selecting it, the memory."""

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

    def button(self, name=None, **kw):
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


class FakeWalk(object):
    P = 90

    def summary(self):
        return "dw: cycle 90 frames"


class FakeReport(object):
    changed = True

    def text(self):
        return "spikes: hand_l 23 (91 deg)"

    def short(self):
        return "cleaned: 1 spike"


class CardTests(unittest.TestCase):

    def setUp(self):
        import maya_hubstyle
        self.hubstyle = maya_hubstyle
        maya_hubstyle.take_marks()
        self.fake = FakeCmds()
        self.applied = []
        self.memos = {}
        self.state = {"loaded": {}, "target": None}
        names = ("_cmds", "walk_names", "walk_exists", "load_walk", "apply", "selected_root", "selected_top",
                 "selected_roots", "memo_of", "pick", "target_root", "_state", "fix_posture", "folder", "walkers",
                 "walker_label", "set_listed")
        self.saved = (panel._cmds, dict((n, getattr(scene, n)) for n in names), dict(panel.JOB), panel._library)
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

        self.frames = {}                          # a cycle's own frames (FakeWalk.P otherwise)

        def load_walk(name, given=None):
            self.loaded.append((name, given))
            walk = FakeWalk()
            walk.P = self.frames.get(name, FakeWalk.P)
            return walk, {}, 0, FakeReport()
        scene.load_walk = load_walk
        scene._state = lambda: self.state
        self.fixed = []

        def fix_posture(name, given=None):
            self.fixed.append((name, given))
            return FakeReport(), "Fix posture: %s foot_l out: mirrored" % name
        scene.fix_posture = fix_posture

        def apply(root, walk, given, pose, parts, pose_card=None, record=True):
            self.applied.append((root, walk, given, pose_card, parts))
            self.state["target"] = "uuid-" + root
            self.memos[root] = dict(self.memos.get(root, {}), walk=walk, knobs=dict(given), listed=True,
                                    parts=list(parts))
            return None, {"clean": FakeReport()}, "%s on %s" % (walk, root)
        scene.apply = apply
        scene.walkers = lambda: sorted(r for r, m in self.memos.items() if m.get("walk") and m.get("listed", True))
        scene.walker_label = lambda root: root.rsplit("|", 1)[-1]

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

        def pick(root):
            memo = self.memos[root]
            self.state["target"] = "uuid-" + root
            return memo["walk"], wm.knobs(**memo["knobs"]), memo.get("pose") or None, tuple(memo["parts"])
        scene.pick = pick

        def target_root():
            if not self.state["target"]:
                raise scene.Refusal("select a skeleton and press Pick first")
            return self.state["target"][len("uuid-"):]
        scene.target_root = target_root

    def tearDown(self):
        panel._cmds, functions, job, panel._library = self.saved
        shutil.rmtree(self.temp, ignore_errors=True)
        for name, value in functions.items():
            setattr(scene, name, value)
        panel.JOB.clear()
        panel.JOB.update(job)
        self.hubstyle.take_marks()

    def made(self, kind):
        return [c for c in self.fake.created if c[0] == kind]

    def test_the_card(self):
        panel.build_panel()
        marks = dict((m.name, (m.role, m.icon)) for m in self.hubstyle.take_marks())
        self.assertEqual(marks[panel.SUBTITLE][0], "subtitle")
        self.assertEqual(marks[panel.STATUS][0], "status")
        self.assertEqual(marks[panel.APPLY_BTN], ("primary", "walk"))
        self.assertEqual(marks[panel.RESET_BTN], ("secondary", "refresh"))
        self.assertEqual(marks[panel.SAVE_WALK_BTN], ("tool", "device-floppy"))
        self.assertFalse(hasattr(panel, "SAVE_POSE_BTN"))          # a pose is saved by the Pose Library
        self.assertFalse(hasattr(panel, "POSE_MENU"))
        self.assertFalse(hasattr(panel, "WALK_MENU"))           # the walk is a card in the walk well
        self.assertIn(panel.WALK_WELL, [c[1] for c in self.made("columnLayout")])
        self.assertIn("Walk: asd", self.fake.values[panel.WALK_WELL_TEXT])        # no Qt here: its line
        self.assertIn(panel.POSE_WELL, [c[1] for c in self.made("columnLayout")])   # the well's placeholder
        self.assertIn("none", self.fake.values[panel.POSE_WELL_TEXT])             # no Qt here: its line
        self.assertEqual(len(self.made("popupMenu")), 2)          # the walks folder; the walkers list
        # the Rig pose tab: Create / Delete, Update (the press that takes the rig's edit) / Reset
        self.assertEqual(marks[panel.MEAN_CREATE_BTN], ("secondary", "user"))
        self.assertEqual(marks[panel.MEAN_DELETE_BTN], ("danger", "trash"))
        self.assertEqual(marks[panel.MEAN_UPDATE_BTN], ("primary", "refresh"))
        self.assertEqual(marks[panel.MEAN_RESET_BTN], ("secondary", "arrow-back-up"))
        self.assertIn("rigpose", [key for row in panel.GROUP_ROWS for key in row])
        chips = [c[1] for c in self.made("checkBox")]
        self.assertEqual(chips, [panel._part_control(p) for p, _ in panel.PART_LABELS] + [panel.IN_PLACE_BOX])
        self.assertTrue(all(marks[c][0] == "chip" for c in chips))
        tabs = [(c[1], c[2]["collection"]) for c in self.made("iconTextRadioButton")]
        rows = [key for row in panel.GROUP_ROWS for key in row]
        self.assertEqual(sorted(rows), sorted(k for k, _, _ in panel.GROUPS))
        self.assertEqual(tabs, [(panel._group_tab(k), panel.GROUP_TABS) for k in rows]
                         + [(panel._side_tab(m), panel.SIDE_TABS) for m, _ in panel.SIDE_MODES])
        self.assertTrue(self.fake.values[panel._side_tab("both")])      # Both, the default
        sliders = [c[1] for c in self.made("floatSliderGrp") + self.made("intSliderGrp")]
        self.assertEqual(sorted(sliders), sorted(panel._control(k) for k in scene.ALL_DEFAULTS
                                                 if k not in panel.CHECKS))
        self.assertEqual(marks[panel.FIX_BTN][0], "secondary")
        self.assertEqual(marks[panel.CLEAN_REPORT][0], "caption")       # a note would hide (CLAUDE.md trap 226)
        self.assertEqual(self.fake.values[panel.CLEAN_REPORT], "spikes: hand_l 23 (91 deg)")
        self.assertTrue(all(callable(c[2]["changeCommand"])
                            for c in self.made("floatSliderGrp") + self.made("intSliderGrp")))
        self.assertTrue(panel.is_open())

    def test_one_knob_group_at_a_time(self):
        panel.build_panel()
        shown = [k for k, _, _ in panel.GROUPS if self.fake.managed[panel._group_column(k)]]
        self.assertEqual(shown, ["clean"])                       # the first, when none is remembered
        panel.group_changed("legs")()
        shown = [k for k, _, _ in panel.GROUPS if self.fake.managed[panel._group_column(k)]]
        self.assertEqual(shown, ["legs"])
        self.assertEqual(self.fake.vars[panel.OPTION + "group"], "legs")
        self.assertTrue(self.fake.values[panel._group_tab("legs")])
        self.fake.created, self.fake.managed = [], {}
        panel.build_panel()                                      # remembered across a rebuild
        shown = [k for k, _, _ in panel.GROUPS if self.fake.managed[panel._group_column(k)]]
        self.assertEqual(shown, ["legs"])

    def test_apply_puts_the_card_on_the_selection_and_remembers_it(self):
        panel.build_panel()
        self.fake.vars[panel.OPTION + "walk"] = "dw"
        card = write_card(self.library, "Walk poses", "goblin")
        self.fake.vars[panel.OPTION + "poseCard"] = "Walk poses/goblin.pose"
        self.fake.values[panel._control("pelvis_height")] = 8.0
        self.fake.values[panel._part_control("arms")] = False
        self.fake.selection = ["|root"]
        self.assertEqual(panel.press_apply(), "dw on |root")
        root, walk, given, pose, parts = self.applied[-1]
        self.assertEqual((root, walk, pose), ("|root", "dw", "Walk poses/goblin.pose"))
        self.assertTrue(os.path.isdir(card))
        self.assertEqual(given["pelvis_height"], 8.0)
        self.assertEqual(given["tempo"], 90.0)                  # the walk's own, shown in the card
        self.assertNotIn("arms", parts)
        self.assertEqual(self.fake.vars[panel.OPTION + "knob_pelvis_height"], 8.0)
        self.assertEqual(self.fake.vars[panel.OPTION + "walk"], "dw")
        self.assertEqual(self.fake.values[panel.STATUS], "dw on |root")

    def test_nothing_selected_says_so(self):
        panel.build_panel()
        self.assertIn("select", panel.press_apply())
        self.assertEqual(self.applied, [])

    def test_a_knob_rekeys_every_walker_and_none_says_so(self):
        panel.build_panel()
        self.assertIn("Pick", panel.slider_changed())
        self.assertEqual(self.applied, [])
        self.fake.selection = ["|root"]
        panel.press_apply()
        self.fake.selection = []                                 # the list stays the list
        self.fake.values[panel._control("stride")] = 1.3
        panel.slider_changed()
        self.assertEqual(self.applied[-1][0], "|root")
        self.assertEqual(self.applied[-1][2]["stride"], 1.3)

    def test_pick_adds_every_selected_skeleton_to_the_list(self):
        panel.build_panel()
        self.fake.selection = ["|a|root", "|b|root"]
        line = panel.press_apply()
        self.assertIn("2 skeletons pick asd", line)
        self.assertEqual([a[0] for a in self.applied], ["|a|root", "|b|root"])
        self.assertEqual(self.fake.items[panel.WALKER_LIST], ["root - asd", "root - asd"])

    def test_each_walker_keeps_its_cycle_and_the_tempo_ratio(self):
        panel.build_panel()
        self.frames["asd"] = 32
        self.fake.vars[panel.OPTION + "walk"] = "asd"
        panel._set_knobs({"tempo": 32}, 32)
        self.fake.selection = ["|a"]
        panel.press_apply()
        panel.take_walk_card(os.path.join(self.library, "x"))    # not an animation card: refused, nothing changes
        panel._walk_taken("dw")                                  # 90 frames: the ratio 1 kept, nobody re-keyed
        count = len(self.applied)
        self.assertEqual(self.fake.values[panel._control("tempo")], 90)
        self.assertEqual(len(self.applied), count)
        self.fake.selection = ["|b"]
        panel.press_apply()
        self.assertEqual(self.applied[-1][:2], ("|b", "dw"))
        panel._set_knobs({"tempo": 45}, 90)                      # half the frames: twice as fast
        self.fake.values[panel._control("bob")] = 2.0
        line = panel.slider_changed()
        keyed = dict((a[0], a) for a in self.applied[-2:])
        self.assertEqual(keyed["|a"][1], "asd")                  # each on its own cycle
        self.assertEqual(keyed["|b"][1], "dw")
        self.assertEqual(keyed["|a"][2]["tempo"], 16.0)          # 45/90 of its own 32
        self.assertEqual(keyed["|b"][2]["tempo"], 45.0)
        self.assertEqual((keyed["|a"][2]["bob"], keyed["|b"][2]["bob"]), (2.0, 2.0))
        self.assertIn("2 walkers keyed", line)

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

    def test_take_settings_puts_a_walker_s_knobs_in_the_card(self):
        knobs = dict(wm.DEFAULTS, stance=0.33, tempo=90.0, pose=1.0)
        self.memos["|walked"] = {"walk": "dw", "pose": "two_handed_sword", "pose_card": "Swords/sword.pose",
                                 "parts": ["torso", "feet"], "knobs": knobs}
        panel.build_panel()
        self.fake.selection = ["|walked"]
        panel.refresh()                                          # selecting it no longer loads its knobs
        self.assertNotEqual(self.fake.values[panel._control("stance")], 0.33)
        panel.take_settings("|walked")
        self.assertEqual(self.applied, [])                       # taking them keys nothing
        self.assertEqual(self.fake.vars[panel.OPTION + "poseCard"], "Swords/sword.pose")
        self.assertEqual(self.fake.values[panel._control("stance")], 0.33)
        self.assertFalse(self.fake.values[panel._part_control("knees")])

    def test_a_skeleton_not_walked_is_named(self):
        panel.build_panel()
        self.fake.selection = ["|a|root"]
        panel.refresh()
        self.assertEqual(self.fake.values[panel.SUBTITLE], "root: Pick adds it with asd")

    def test_a_press_with_the_card_closed_reads_the_memory(self):
        self.fake.vars[panel.OPTION + "knob_stride"] = 1.4
        self.fake.vars[panel.OPTION + "walk"] = "dw"
        self.fake.vars[panel.OPTION + "parts"] = json.dumps(["torso"])
        self.fake.selection = ["|root"]
        panel.press_apply()
        root, walk, given, pose, parts = self.applied[-1]
        self.assertEqual((walk, given["stride"], parts, pose), ("dw", 1.4, ("torso",), None))
        self.assertFalse(panel.is_open())

    def test_reset_puts_the_defaults_back_and_rekeys(self):
        panel.build_panel()
        self.fake.selection = ["|root"]
        panel.press_apply()
        self.fake.values[panel._control("bob")] = 2.0
        panel.press_reset()
        self.assertEqual(self.fake.values[panel._control("bob")], wm.DEFAULTS["bob"])
        self.assertEqual(self.fake.values[panel._control("tempo")], 90)
        self.assertEqual(self.applied[-1][2]["bob"], wm.DEFAULTS["bob"])

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
        self.assertEqual(self.applied[-1][2]["in_place"], 1.0)
        self.assertEqual(self.fake.vars[panel.OPTION + "knob_in_place"], 1.0)
        panel._set_knobs({"in_place": 0.0}, 90)
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
        self.assertEqual(self.fake.jobs[first], (["SelectionChanged", panel.refresh], panel.STATUS))
        panel.build_panel()
        self.assertEqual(self.fake.killed, [first])
        self.assertEqual(len(self.fake.jobs), 1)


class SideTests(CardTests):
    """[Both | Left | Right]: the leg and arm knobs set both sides, or one side alone."""

    def changed(self, name, value):
        self.fake.values[panel._control(name)] = value
        for c in self.made("floatSliderGrp"):
            if c[1] == panel._control(name):
                return c[2]["changeCommand"]()

    def test_left_sets_the_left_side_alone(self):
        panel.build_panel()
        self.fake.selection = ["|root"]
        panel.press_apply()
        panel.side_changed("l")()
        self.assertEqual(self.fake.labels[panel._control("lift")], "Foot lift L")
        self.assertEqual(self.fake.labels[panel._control("arms")], "Arms L")
        self.changed("lift", 2.0)
        given = self.applied[-1][2]
        self.assertEqual((given["lift"], given["lift_l"]), (1.0, 2.0))
        self.assertNotIn("lift_r", given)
        panel.side_changed("r")()                       # the right shows its own: the knob's
        self.assertEqual(self.fake.values[panel._control("lift")], 1.0)
        panel.side_changed("l")()
        self.assertEqual(self.fake.values[panel._control("lift")], 2.0)
        panel.side_changed("both")()                    # Both marks a knob whose sides differ
        self.assertEqual(self.fake.labels[panel._control("lift")], "Foot lift *")
        self.assertEqual(self.fake.values[panel._control("lift")], 1.0)
        self.assertEqual(self.fake.labels[panel._control("arms")], "Arms")

    def test_both_links_a_knob_s_sides_again(self):
        panel.build_panel()
        self.fake.selection = ["|root"]
        panel.press_apply()
        panel.side_changed("l")()
        self.changed("arms", 0.0)
        panel.side_changed("both")()
        self.changed("arms", 1.5)
        given = self.applied[-1][2]
        self.assertEqual(given["arms"], 1.5)
        self.assertNotIn("arms_l", given)
        self.assertEqual(self.fake.labels[panel._control("arms")], "Arms")

    def test_a_knob_without_sides_is_the_same_in_every_mode(self):
        panel.build_panel()
        self.fake.selection = ["|root"]
        panel.press_apply()
        panel.side_changed("r")()
        self.changed("bob", 2.0)
        given = self.applied[-1][2]
        self.assertEqual(given["bob"], 2.0)
        self.assertNotIn("bob_r", given)

    def test_reset_links_every_side(self):
        panel.build_panel()
        self.fake.selection = ["|root"]
        panel.press_apply()
        panel.side_changed("l")()
        self.changed("foot_lag", 3.0)
        panel.press_reset()
        self.assertNotIn("foot_lag_l", self.applied[-1][2])

    def test_a_walked_skeleton_brings_its_sides(self):
        knobs = dict(wm.DEFAULTS, tempo=90.0, arm_drag_r=4.0)
        self.memos["|walked"] = {"walk": "dw", "pose": "", "parts": list(scene.ALL_PARTS), "knobs": knobs}
        panel.build_panel()
        panel.take_settings("|walked")
        self.assertEqual(self.fake.labels[panel._control("arm_drag")], "Arm drag, fr *")
        panel.side_changed("r")()
        self.assertEqual(self.fake.values[panel._control("arm_drag")], 4.0)
        self.assertEqual(panel.values()["arm_drag_r"], 4.0)


class HubTests(unittest.TestCase):

    def test_the_section(self):
        import maya_hub
        sec = maya_hub.section("walk")
        self.assertEqual((sec.label, sec.module, sec.builder, sec.frame, sec.group, sec.icon),
                         ("Walk Builder", "maya_walk.panel", "build_panel", "skeldarHubFrameWalk",
                          "animation", "walk"))
        keys = [s.key for s in maya_hub.SECTIONS]
        self.assertEqual(keys.index("walk"), keys.index("tailbuilder") + 1)
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
