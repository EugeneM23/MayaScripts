"""Walk Builder's card (maya_walk.panel), the corners the first tests left - on test_walk_panel's fake cmds and fake
scene: the memory read back when it is broken, the active cycle and the walk well's rows, the re-key on Maya's
idle (its state, a press while one keys, a failure, Maya's progress window), the parameters released quiet or with
no walk, the macros, the Diagnosis's Fix, the knobs from before the parameters, the list's right button, Pick on
its own animation, Save, the Rig pose and the tabs' Reset, the first card of a session moving the old walks and
poses into the library, and the selection's walker brought into the card."""

import contextlib
import io
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.join(os.path.dirname(HERE), "SkeldarAnim")
if PLUGIN not in sys.path:
    sys.path.insert(0, PLUGIN)

from tests import test_walk_panel as base      # noqa: E402 - its fakes (a module: none of its tests here)
from maya_walk import panel, scene             # noqa: E402
from maya_walk import gait                     # noqa: E402
from maya_walk import files as wf              # noqa: E402
from maya_poselib import store                 # noqa: E402

MISSING = object()
CARD_A = "Walk cycles/run.anim"
CARD_B = "Walk cycles/stroll.anim"


@contextlib.contextmanager
def hushed(out=None):
    """What a press prints on its way (a traceback, a migration's line), kept off the test's output."""
    out = out if out is not None else io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        yield out


class More(unittest.TestCase):
    """test_walk_panel.CardTests's card and scene fakes, plus every other module attribute a test rebinds."""

    made = base.CardTests.made
    command = base.CardTests.command
    release = base.CardTests.release
    params = base.CardTests.params
    assertChange = base.CardTests.assertChange

    def setUp(self):
        self.selected_was = panel._SELECTED[0]
        self.quiet_was = panel._QUIET[0]
        self.rekey_was = getattr(sys, "_skeldar_walk_rekey", None)
        sys._skeldar_walk_rekey = None
        self.extra = {}
        base.CardTests.setUp(self)

    def rebind(self, module, name, value=MISSING):
        """`module.name` set to `value` (MISSING: taken away) for this test."""
        key = (module, name)
        if key not in self.extra:
            self.extra[key] = module.__dict__.get(name, MISSING)
        if value is MISSING:
            module.__dict__.pop(name, None)
        else:
            setattr(module, name, value)

    def tearDown(self):
        for (module, name), value in self.extra.items():
            if value is MISSING:
                module.__dict__.pop(name, None)
            else:
                setattr(module, name, value)
        base.CardTests.tearDown(self)
        panel._QUIET[0] = self.quiet_was
        panel._SELECTED[0] = self.selected_was
        sys._skeldar_walk_rekey = self.rekey_was

    def var(self, name, default=None):
        return self.fake.vars.get(panel.OPTION + name, default)

    def set_var(self, name, value):
        self.fake.vars[panel.OPTION + name] = value

    def walker(self, root, walk="asd", working=True, **memo):
        self.memos[root] = dict({"walk": walk, "knobs": {}, "listed": True, "parts": [], "working": working,
                                 "version": 3}, **memo)

    def card_dir(self, rel, thumbnail=False):
        path = os.path.join(self.library, rel)
        os.makedirs(path)
        if thumbnail:
            open(os.path.join(path, "thumbnail.jpg"), "wb").close()
        return path.replace("\\", "/")


class Memory(More):

    def test_a_remembered_value_that_is_not_json_or_not_its_kind_is_the_default(self):
        self.set_var("params", "{not json")
        self.set_var("macros", "[1, 2]")
        p = panel.card_params()
        self.assertEqual((p["changes"], p["pins"], p["macros"]), ({}, [], {}))
        self.assertEqual(panel._json("macros", {}), {})
        self.set_var("macros", '{"speed": 1.2, "weight": "0.5", "who": 3}')
        self.assertEqual(panel._macros(), {"speed": 1.2, "weight": 0.5})          # only the two macros

    def test_parts_remembered_badly_or_not_at_all_mean_every_part(self):
        self.assertEqual(panel.chosen_parts(), scene.ALL_PARTS)
        self.set_var("parts", json.dumps(["torso", "wings"]))
        self.assertEqual(panel.chosen_parts(), ("torso",))
        for broken in ("{bad", "5"):
            self.set_var("parts", broken)
            self.assertEqual(panel.chosen_parts(), scene.ALL_PARTS)

    def test_a_side_remembered_wrong_is_both(self):
        self.set_var("side", "up")
        self.assertEqual(panel.side_mode(), "both")
        self.set_var("side", "l")
        self.assertEqual(panel.side_mode(), "l")

    def test_with_the_card_closed_the_card_knobs_are_the_remembered_or_their_defaults(self):
        self.set_var("knob_seam", 3.0)
        knobs = panel.values()
        self.assertEqual(knobs["seam"], 3.0)
        self.assertEqual(knobs["smooth"], scene.ALL_DEFAULTS["smooth"])
        self.assertEqual(sorted(knobs), sorted(panel.CARD_KNOBS))

    def test_only_the_card_s_own_knobs_are_set_and_in_place_is_one_or_zero(self):
        panel._set_knobs({"step": 2.0, "seam": 3.0, "in_place": 0.7})
        self.assertEqual((self.var("knob_seam"), self.var("knob_in_place")), (3.0, 1.0))
        self.assertIsNone(self.var("knob_step"))

    def test_the_library_is_the_pose_library_s_folder_when_it_names_one(self):
        real_library = self.saved[3]
        self.assertTrue(real_library().endswith("/poses"))
        self.fake.vars[store.ROOT_VAR] = self.library
        self.assertEqual(real_library(), self.library)

    def test_the_real_cmds_is_maya_s(self):
        import maya.cmds
        self.assertIs(self.saved[0](), maya.cmds)


class Walks(More):
    """The active cycle and the walk well's rows."""

    def test_a_name_from_before_the_cards_with_neither_its_card_nor_its_file_is_no_walk(self):
        self.set_var("walk", "ghost")
        with self.assertRaises(scene.Refusal) as raised:
            panel.chosen_walk()
        self.assertEqual(str(raised.exception), panel.NO_WALK)
        self.assertIsNone(panel._active_walk_rel())

    def test_a_stored_cycle_that_cannot_be_read_gives_way_to_the_first_card_that_can(self):
        readable = scene.card_walk(CARD_B)
        self.rebind(scene, "walk_exists", lambda name: name == readable)
        self.set_var("walkCards", json.dumps([CARD_A, CARD_B]))
        self.set_var("walk", scene.card_walk("Walk cycles/gone.anim"))
        self.assertEqual(panel.walk_list(), ["Walk cycles/gone.anim", CARD_A, CARD_B])   # the stored one heads it
        self.assertEqual(panel.chosen_walk(), readable)
        self.set_var("walk", scene.OWN + "nobody")                                   # an own cycle gone
        self.assertEqual(panel.chosen_walk(), readable)
        self.assertEqual(panel._active_walk_rel(), CARD_B)

    def test_a_broken_walk_list_is_empty_but_a_stored_card_still_heads_it(self):
        self.set_var("walkCards", "{bad")
        self.assertEqual(panel.walk_list(), [])
        self.set_var("walk", scene.card_walk(CARD_A))
        self.assertEqual(panel.walk_list(), [CARD_A])
        self.set_var("walkCards", json.dumps([CARD_A, "", 5, CARD_B]))             # only the paths
        self.assertEqual(panel.walk_list(), [CARD_A, CARD_B])

    def test_the_rows_show_a_thumbnail_and_say_a_card_gone_and_whether_its_walk_is_kept(self):
        kept, lost = "Walk cycles/kept.anim", "Walk cycles/lost.anim"
        run = self.card_dir(CARD_A, thumbnail=True)
        self.rebind(scene, "walk_exists", lambda name: name != scene.card_walk(lost))
        self.set_var("walkCards", json.dumps([CARD_A, kept, lost]))
        self.set_var("walk", scene.card_walk(CARD_A))
        rows = panel.walk_rows()
        self.assertEqual(rows[0], (run, "run", os.path.join(run, "thumbnail.jpg"), "", True))
        self.assertEqual(rows[1][1:], ("kept", "", "gone from the library - its walk is kept", False))
        self.assertEqual(rows[2][1:], ("lost", "", "the card is gone from the library", False))
        self.rebind(scene, "walk_exists", lambda name: False)                       # no cycle reads: none active
        self.assertEqual([row[4] for row in panel.walk_rows()], [False, False, False])

    def test_without_qt_the_walk_line_names_the_walk_and_the_cards_or_says_none(self):
        panel.build_panel()
        self.set_var("walkCards", json.dumps([CARD_A, CARD_B]))
        self.set_var("walk", scene.card_walk(CARD_B))
        panel._show_walk_line()
        self.assertEqual(self.fake.values[panel.WALK_WELL_TEXT], "Walk: stroll (2 cards in the well)")
        self.set_var("walkCards", "[]")
        self.set_var("walk", "")
        panel._show_walk_line()
        self.assertEqual(self.fake.values[panel.WALK_WELL_TEXT],
                         "Walk: none - Pose Library animation card > Use in Walk Builder")

    def test_a_well_that_cannot_be_read_again_leaves_the_card_s_memory_set(self):
        from maya_walk import posewell

        def broken():
            raise RuntimeError("Qt is gone")
        self.rebind(posewell, "refresh_all", broken)
        panel._set_walk(scene.card_walk(CARD_A))
        panel._set_card("goblin.pose")
        self.assertEqual((self.var("walk"), self.var("poseCard")), (scene.card_walk(CARD_A), "goblin.pose"))
        self.assertEqual(panel.walk_list(), [CARD_A])

    def test_the_walk_read_again_shows_its_own_and_what_the_clean_did(self):
        panel.build_panel()
        line = panel.walk_changed()
        self.assertTrue(line.startswith("walk asd | " + self.walk.summary()))
        self.assertIn("cleaned: 1 spike", line)
        self.assertTrue(line.endswith("- Pick puts it on the selected skeletons"))
        self.assertEqual(self.applied, [])                                          # read, nobody keyed
        panel._QUIET[0] = True
        self.assertIsNone(panel.walk_changed())

    def test_a_card_taken_out_brings_back_only_the_walkers_on_it(self):
        card = scene.card_walk(CARD_A)
        self.set_var("walkCards", json.dumps([CARD_A, CARD_B]))
        self.set_var("walk", scene.card_walk(CARD_B))
        self.walker("|a", card)
        self.sources["|a"] = scene.OWN + "a"
        self.walker("|b", "asd")
        self.walker("|c", card)
        line = panel.remove_walk_card(self.library + "/" + CARD_A)
        self.assertEqual([a[:2] for a in self.applied], [("|a", scene.OWN + "a")])
        self.assertEqual(self.memos["|b"]["walk"], "asd")
        self.assertIn("back on their own animation: a", line)
        self.assertIn("(keep the card's keys): c", line)
        self.assertEqual(panel.walk_list(), [CARD_B])                              # the active one stays


class Selection(More):

    def test_the_walkers_the_selection_names_a_bone_a_top_or_a_mesh_skinned_to_one(self):
        roots = {"|mesh": "|b|root", "|a|root|pelvis": "|a|root"}

        def root_of(node):
            if node not in roots:
                raise scene.Refusal("%s is no skeleton" % node)
            return roots[node]
        self.rebind(scene, "skeleton_root_of", root_of)
        self.fake.selection = ["|a|root|pelvis", "|mesh", "|curve", "|a|root", "|c|root"]
        self.assertEqual(panel._selected_walkers(["|a|root", "|b|root"]), ["|a|root", "|b|root"])
        self.fake.selection = ["|curve"]
        self.assertEqual(panel._selected_walkers(["|a|root"]), [])

    def test_the_subtitle_names_the_selected_skeleton_or_counts_the_walkers(self):
        self.walker("|w", "asd", working=False)
        self.assertEqual(panel.selection_line("|w"), "w walks asd")
        self.memos["|w"]["listed"] = False
        self.assertEqual(panel.selection_line("|w"), "w walks asd - out of the list (Pick puts it back)")
        self.assertEqual(panel.selection_line("|new"), "new: Pick adds it with asd")
        self.assertEqual(panel.selection_line(None), panel.NOTHING)                 # w is out of the list
        self.memos["|w"]["listed"] = True
        self.assertEqual(panel.selection_line(None), "1 walker in the list - Pick or click one to work on it")
        self.walker("|v", "asd", working=False)
        self.assertIn("2 walkers in the list", panel.selection_line(None))
        del self.fake.vars[panel.OPTION + "walk"]
        self.assertEqual(panel.selection_line("|new"), "new: drop a walk cycle card first")

    def test_the_working_line_names_three_and_counts_the_rest(self):
        for name in "abcde":
            self.walker("|" + name)
        self.assertEqual(panel.working_line(), "Working on a (asd), b (asd), c (asd) +2 - every change keys them")
        for name in "bcde":
            self.memos["|" + name]["working"] = False
        self.assertEqual(panel.working_line(), "Working on a (asd) - every change keys it")

    def test_a_refresh_that_fails_prints_and_leaves_the_card(self):
        panel.build_panel()
        before = self.fake.values[panel.SUBTITLE]

        def broken():
            raise RuntimeError("the scene is gone")
        self.rebind(scene, "working", broken)
        with hushed() as out:
            panel.refresh()
        self.assertIn("the scene is gone", out.getvalue())
        self.assertEqual(self.fake.values[panel.SUBTITLE], before)

    def test_a_path_s_last_name(self):
        self.assertEqual(panel._short("|a|b|root"), "root")
        self.assertEqual(panel._short(""), "-")


class Activate(More):
    """_activate: a walker newly named brings its settings and its cycle into the card, keying nobody."""

    def setUp(self):
        More.setUp(self)
        params = scene.plain_params({"changes": {"step": ("ratio", 1.25)}, "pins": ["step"]})
        self.walker("|w", scene.card_walk(CARD_A), working=False, params=params, pose="", parts=["torso"])

    def test_a_walker_newly_named_brings_its_settings_and_its_card(self):
        panel._activate("|w")
        self.assertEqual(self.var("walk"), scene.card_walk(CARD_A))
        self.assertEqual(panel.card_params()["changes"]["step"], ("ratio", 1.25))
        self.assertEqual(panel._SELECTED[0], "|w")
        self.assertEqual(self.applied, [])
        panel._remember_hand({}, set())                                            # changed in the card since
        panel._activate("|w")                                                      # the same walker: nothing
        self.assertEqual(panel.card_params()["changes"], {})

    def test_a_walker_on_its_own_cycle_leaves_the_walk_well_s_cards_alone(self):
        self.walker("|o", scene.OWN + "o", working=False)
        self.set_var("walkCards", json.dumps([CARD_B]))
        panel._activate("|o")
        self.assertEqual(panel.walk_list(), [CARD_B])
        self.assertEqual(self.applied, [])

    def test_a_walker_whose_settings_cannot_be_read_still_makes_its_card_the_active_cycle(self):
        def broken(root=None, memo=None, translate=True):
            raise RuntimeError("a memo from the future")
        self.rebind(scene, "memo_params", broken)
        del self.fake.vars[panel.OPTION + "walk"]                                  # an empty well
        with hushed() as out:
            panel._activate("|w")
        self.assertIn("a memo from the future", out.getvalue())
        self.assertEqual(self.var("walk"), scene.card_walk(CARD_A))
        self.assertEqual(panel.walk_list(), [CARD_A])
        self.assertEqual(self.applied, [])

    def test_a_walker_whose_cycle_is_gone_or_unnamed_changes_no_cycle(self):
        self.memos["|w"]["walk"] = ""
        with hushed() as out:
            panel._activate("|w")                                                  # its settings: refused
        self.assertIn("w carries no walk of this tool", out.getvalue())
        self.assertEqual(self.var("walk"), "asd")


class Rekey(More):
    """The re-key on Maya's next idle: its state, a press while one keys, a failure, Maya's progress window."""

    def test_with_walkers_but_none_working_nothing_is_keyed(self):
        self.walker("|a", working=False)
        self.assertEqual(panel._rekey("pose card x"), "pose card x - " + panel.NO_WORKING)
        self.assertEqual(panel._rekey(""), panel.NO_WORKING)
        self.assertEqual(panel._rekey_state()["wanted"], 0)
        self.assertEqual(self.applied, [])

    def test_the_state_an_older_build_left_is_filled_in_and_a_broken_one_replaced(self):
        sys._skeldar_walk_rekey = {"wanted": 2}
        state = panel._rekey_state()
        self.assertEqual(state, {"wanted": 2, "served": 0, "running": False, "line": "", "roots": None})
        sys._skeldar_walk_rekey = ["not", "a", "state"]
        self.assertEqual(panel._rekey_state()["wanted"], 0)
        self.assertIsInstance(sys._skeldar_walk_rekey, dict)

    def test_a_rekey_running_is_never_nested(self):
        self.walker("|a")
        state = panel._rekey_state()
        state.update(wanted=1, served=0, running=True)
        self.assertIsNone(panel._serve())
        self.assertEqual(self.applied, [])
        state["running"] = False
        self.assertEqual(panel._serve(), "asd on |a")                             # one walker: its own line
        self.assertIsNone(panel._serve())                                         # served: nothing left

    def test_an_idle_rekey_that_fails_says_so_and_frees_the_state(self):
        panel.build_panel()
        later = []
        self.rebind(panel, "_later", later.append)

        def broken(**kw):
            raise RuntimeError("boom")
        self.rebind(panel, "rekey_all", broken)
        state = panel._rekey_state()
        state.update(wanted=1, served=0, line="pose card x")
        with hushed():
            panel._rekey_idle()
        self.assertEqual(self.fake.values[panel.STATUS], "Walk Builder failed: boom")
        self.assertEqual((state["running"], state["served"], later), (False, 1, []))
        self.fake.values[panel.STATUS] = "kept"
        panel._rekey_idle()                                                         # nothing pending
        self.assertEqual(self.fake.values[panel.STATUS], "kept")

    def test_a_press_while_maya_cannot_defer_is_done_at_once(self):
        import maya.utils
        self.rebind(maya.utils, "executeDeferred")                                 # taken away
        self.assertEqual(panel._later(lambda: "ran"), "ran")
        caught = []
        self.rebind(maya.utils, "executeDeferred", caught.append)
        self.assertIsNone(panel._later(lambda: "later"))
        self.assertEqual([job() for job in caught], ["later"])

    def test_batch_is_what_maya_says_and_yes_when_it_cannot_say(self):
        self.fake.about = lambda **kw: kw.get("batch") and False
        self.assertFalse(panel._batch())
        self.fake.about = lambda **kw: True
        self.assertTrue(panel._batch())

        def broken(**kw):
            raise RuntimeError("no about")
        self.fake.about = broken
        self.assertTrue(panel._batch())

    def test_a_deleted_walker_is_passed_and_one_that_crashes_is_named(self):
        for name in "abc":
            self.walker("|" + name)
        self.fake.objExists = lambda node: node != "|b"
        apply = scene.apply

        def crashing(root, *a, **kw):
            if root == "|c":
                raise RuntimeError("crashed")
            return apply(root, *a, **kw)
        scene.apply = crashing
        with hushed():
            line = panel.rekey_all()
        self.assertEqual([a[0] for a in self.applied], ["|a"])
        self.assertTrue(line.startswith("1 walker keyed: a - asd | not keyed: c - asd: crashed | "), line)
        self.assertTrue(line.endswith(" s"))

    def test_a_cycle_nobody_walks_and_a_list_nobody_is_in(self):
        self.assertEqual(panel.rekey_all(), "no walker in the list - select skeletons and press Pick")
        self.walker("|a")
        self.assertEqual(panel.rekey_all(walk="dw"), "no walker on dw - Pick puts it on skeletons")
        self.assertEqual(panel.rekey_all(roots=["|z"]), "no walker in the list - select skeletons and press Pick")
        self.fake.objExists = lambda node: False                                   # every walker deleted
        self.assertEqual(panel.rekey_all(), "no walker in the list - select skeletons and press Pick")

    def window(self, fail=()):
        calls = []

        def progress_window(**kw):
            step = "query" if kw.get("query") else "edit" if kw.get("edit") else \
                "end" if kw.get("endProgress") else "open"
            calls.append(step)
            if step in fail:
                raise RuntimeError("no window")
            return False if step == "query" else None
        self.fake.progressWindow = progress_window
        self.fake.about = lambda **kw: False
        return calls

    def test_a_progress_window_that_cannot_open_lets_the_rekey_go_on(self):
        calls = self.window(fail=("open",))
        with panel._Progress(3) as progress:
            self.assertFalse(progress.on)
            self.assertTrue(progress.at(1, "keying 2 of 3"))
        self.assertEqual(calls, ["open"])

    def test_a_progress_window_gone_while_it_keys_lets_the_rekey_go_on(self):
        calls = self.window(fail=("edit",))
        for name in "abc":
            self.walker("|" + name)
        line = panel.rekey_all()
        self.assertIn("3 walkers keyed", line)
        self.assertEqual(calls, ["open", "edit"])                                  # no more asks, no end to call

    def test_a_progress_window_that_cannot_close_is_left(self):
        calls = self.window(fail=("end",))
        with panel._Progress(2) as progress:
            self.assertTrue(progress.at(0, "keying 1 of 2"))
        self.assertFalse(progress.on)
        self.assertEqual(calls, ["open", "edit", "query", "end"])


class Cards(More):
    """The pose well's cards and the Pose Library opened on one."""

    def test_no_card_active_is_four_nothings_and_a_broken_list_is_empty(self):
        self.assertEqual(panel.well_state(), ("", "", "", ""))
        self.set_var("poseCards", "{bad")
        self.assertEqual(panel.card_list(), [])
        self.set_var("poseCard", "goblin.pose")
        self.assertEqual(panel.card_list(), ["goblin.pose"])

    def show_card(self, window):
        from maya_poselib import window as library
        import maya.utils
        opened, deferred = [], []
        self.rebind(library, "show_window", lambda: opened.append(True))
        self.rebind(library, "live", lambda: window)
        self.rebind(maya.utils, "executeDeferred", deferred.append)
        line = panel.show_card(self.library + "/Swords/sword.pose")
        return opened, deferred, line

    def test_show_card_opens_the_library_and_picks_the_card_on_maya_s_idle(self):
        class Window(object):
            def __init__(self):
                self.calls = []

            def refresh(self):
                self.calls.append("refresh")

            def pick(self, path):
                self.calls.append(("pick", path))
        window = Window()
        opened, deferred, line = self.show_card(window)
        self.assertEqual((opened, line), ([True], "sword in the Pose Library"))
        self.assertEqual(window.calls, [])                                        # not before the library stands
        deferred[0]()
        self.assertEqual(window.calls, ["refresh", ("pick", self.library + "/Swords/sword.pose")])

    def test_show_card_with_no_library_window_or_one_that_fails(self):
        opened, deferred, line = self.show_card(None)
        deferred[0]()                                                              # nothing to pick in

        class Broken(object):
            def refresh(self):
                raise RuntimeError("closed meanwhile")
        opened, deferred, line = self.show_card(Broken())
        with hushed():
            deferred[0]()
        self.assertEqual(line, "sword in the Pose Library")

    def test_where_maya_s_utilities_cannot_be_imported_the_card_is_picked_at_once(self):
        from maya_poselib import window as library
        picked = []

        class Window(object):
            def refresh(self):
                pass

            def pick(self, path):
                picked.append(path)
        self.rebind(library, "show_window", lambda: None)
        self.rebind(library, "live", lambda: Window())
        import maya.utils                                      # loaded, so the swap below puts it back
        had = sys.modules.get("maya.utils", MISSING)
        sys.modules["maya.utils"] = None                       # this one entry swapped: `import` raises
        try:
            line = panel.show_card(self.library + "/goblin.pose")
        finally:
            if had is MISSING:
                sys.modules.pop("maya.utils", None)
            else:
                sys.modules["maya.utils"] = had
        self.assertEqual((line, picked), ("goblin in the Pose Library", [self.library + "/goblin.pose"]))

    def test_a_pose_card_dropped_with_a_share_already_set_keeps_it(self):
        self.walker("|a")
        self.set_var("knob_pose", 0.4)
        card = base.write_card(self.library, "", "goblin")
        line = panel.take_card(card)
        self.assertNotIn("Pose share set to 1", line)
        self.assertEqual(self.applied[-1][2]["pose"], 0.4)

    def test_a_card_that_is_not_the_active_one_taken_out_keys_nobody(self):
        self.walker("|a")
        sword, goblin = base.write_card(self.library, "", "sword"), base.write_card(self.library, "", "goblin")
        panel.take_card(sword)
        panel.take_card(goblin)
        count = len(self.applied)
        self.assertEqual(panel.remove_card(sword), "sword taken out of the well")
        self.assertEqual(len(self.applied), count)
        self.assertEqual(panel.remove_all_cards(), "the well emptied - the walk's own posture | asd on |a")
        self.assertIsNone(self.applied[-1][3])
        count = len(self.applied)
        self.assertEqual(panel.remove_all_cards(), "the well emptied")             # none was active: no re-key
        self.assertEqual(len(self.applied), count)


class Parameters(More):
    """A parameter, a macro or a card knob released: quiet while the card is filled, with no walk, no control."""

    def test_the_speed_of_a_cycle_with_no_tempo_or_step_is_its_own(self):
        self.assertEqual(panel._speed_of({"speed": 1.5}, {"tempo": 0.0, "step": 80.0}), 1.5)
        self.assertEqual(panel._speed_of({"speed": 1.5, "step": 0.0, "tempo": 30.0}, {"tempo": 30.0, "step": 70.0}),
                         1.5)
        self.assertEqual(panel._speed_of({}, {"tempo": 0.0}), 0.0)
        own = {"speed": 1.0, "step": 80.0, "tempo": 30.0}
        self.assertAlmostEqual(panel._speed_of(own, {"step": 120.0, "tempo": 15.0}), 3.0)

    def test_a_toggle_is_one_or_zero_and_pinned(self):
        panel.build_panel()
        self.walker("|a")
        self.fake.values[panel._control("balance")] = False
        panel.param_changed("balance")()
        self.assertEqual(self.params()["changes"]["balance"], ("offset", -1.0))
        self.assertIn("balance", self.params()["pins"])
        panel._set_key("balance", 0.7, self.own)                                   # 0.7 is on: its own, no change
        changes, pins = panel._hand()
        self.assertNotIn("balance", changes)
        self.assertIn("balance", pins)

    def test_a_parameter_released_quiet_or_with_its_card_closed_does_nothing(self):
        self.walker("|a")
        panel._QUIET[0] = True
        self.assertIsNone(panel.param_changed("step")())
        panel._QUIET[0] = False
        self.assertIsNone(panel.param_changed("step")())                          # no slider: the card closed
        self.assertIsNone(panel.param_changed("balance")())
        self.assertEqual(self.applied, [])
        self.assertNotIn(panel.OPTION + "params", self.fake.vars)

    def test_a_parameter_released_with_no_walk_says_so(self):
        def refused(name, given=None):
            raise scene.Refusal("no such walk")
        scene.load_walk = refused
        self.assertEqual(panel.param_changed("step")(), panel.NO_WALK)
        self.assertEqual(panel.speed_changed(), panel.NO_WALK)
        self.assertIsNone(panel.show_values())

    def test_every_macro_released_quiet_does_nothing(self):
        panel.build_panel()
        self.walker("|a")
        panel._QUIET[0] = True
        for press in (panel.speed_changed, panel.weight_changed, panel.character_changed, panel.strength_changed,
                      panel.physics_changed, panel.knee_pops_changed, panel.slider_changed, panel.in_place_changed,
                      panel.knob_changed("seam")):
            self.assertIsNone(press(), press)
        self.assertEqual(self.applied, [])

    def test_speed_and_weight_back_at_nothing_are_dropped(self):
        panel.build_panel()
        self.walker("|a")
        self.set_var("macros", json.dumps({"speed": 2.0, "weight": 0.5}))
        self.release(panel.SPEED, self.own["speed"] + 0.001)                        # the cycle's own speed
        self.release(panel.WEIGHT, 0.0004)
        self.assertEqual(self.params()["macros"], {})

    def test_a_card_knob_released_is_remembered_and_keys_the_working_walkers(self):
        panel.build_panel()
        self.walker("|a")
        self.fake.values[panel._control("seam")] = 4.0
        panel.knob_changed("seam")()
        self.assertEqual(self.var("knob_seam"), 4.0)
        self.assertEqual((self.applied[-1][0], self.applied[-1][2]["seam"]), ("|a", 4.0))
        self.assertEqual(self.params()["clean"]["seam"], 4.0)

    def test_a_card_knob_released_with_its_slider_gone_still_keys(self):
        self.walker("|a")
        panel.knob_changed("smooth")()
        self.assertIsNone(self.var("knob_smooth"))
        self.assertEqual(self.applied[-1][0], "|a")

    def test_an_unknown_tab_shows_the_first(self):
        panel.build_panel()
        panel.show_group("nonsense")
        self.assertEqual(self.var("group"), panel.GROUPS[0][0])
        self.assertEqual([k for k, _, _ in panel.GROUPS if self.fake.managed[panel._group_column(k)]],
                         [panel.GROUPS[0][0]])
        panel.show_group("weight")                                                 # a tab from before
        self.assertEqual(self.var("group"), "physics")

    def test_a_side_switched_with_the_card_closed_is_remembered(self):
        panel.show_side("r")
        self.assertEqual(panel.side_mode(), "r")
        panel.show_side("sideways")
        self.assertEqual(panel.side_mode(), "both")


class Diagnosis(More):

    def test_with_the_card_closed_the_diagnosis_shows_nowhere(self):
        state = panel._diag_state()
        state.update(who="a - asd", findings=[gait.Finding("x", "Arms in step", {"arm_lag": 3.0})])
        panel.show_diagnosis()
        self.assertNotIn(panel.DIAG_CAPTION, self.fake.values)

    def test_a_fix_past_the_findings_or_without_one(self):
        state = panel._diag_state()
        state.update(who="a - asd", walk="asd", findings=[gait.Finding("physics", "Physics gave way", {})])
        self.assertEqual(panel.fix_pressed(3)(), "nothing to fix")
        self.assertEqual(panel.fix_pressed(0)(), "Physics gave way")
        self.assertNotIn(panel.OPTION + "params", self.fake.vars)

    def test_a_fix_with_no_walk_read_by_the_finding_uses_the_active_cycle(self):
        self.walker("|a")
        state = panel._diag_state()
        state.update(who="a", walk=None, findings=[gait.Finding("lean", "Leans back", {"lean": 7.0})])
        line = panel.fix_pressed(0)()
        self.assertIn("fixed: Leans back", line)
        self.assertEqual(self.loaded[-1][0] if self.loaded else None, "asd")
        kind, x = panel.card_params()["changes"]["lean"]
        self.assertAlmostEqual(self.own["lean"] + x, 7.0, places=6)


class Legacy(More):
    """The knobs a card remembered before the parameters, read as parameters once."""

    def test_a_tempo_at_the_cycle_s_own_is_no_change_and_a_weight_becomes_the_macro(self):
        self.set_var("knob_tempo", float(self.walk.P))
        self.set_var("knob_weight", 0.5)
        panel._migrate_knobs()
        self.assertEqual(json.loads(self.var("params")), {"changes": {}, "pins": []})
        self.assertEqual(json.loads(self.var("macros")), {"weight": 0.5})

    def test_knobs_wait_while_no_walk_can_be_read(self):
        self.set_var("knob_stride", 1.3)
        self.set_var("walk", "")
        panel._migrate_knobs()
        self.assertIsNone(self.var("params"))                                       # tried again later
        self.set_var("walk", "asd")
        panel._migrate_knobs()
        self.assertEqual(json.loads(self.var("params"))["changes"]["step"], ["ratio", 1.3])

    def test_the_cycle_the_tempo_was_counted_in_is_the_one_read(self):
        self.set_var("knob_stride", 1.2)
        self.set_var("tempoWalk", "dw")
        panel._migrate_knobs()
        self.assertEqual(self.loaded[-1][0], "dw")
        self.set_var("tempoWalk", "gone")
        self.fake.vars.pop(panel.OPTION + "params")
        panel._migrate_knobs()
        self.assertEqual(self.loaded[-1][0], "asd")                                 # a cycle gone: the active one

    def test_no_knob_from_before_writes_empty_parameters_and_once_done_nothing_again(self):
        panel._migrate_knobs()
        self.assertEqual(json.loads(self.var("params")), {"changes": {}, "pins": []})
        self.set_var("knob_stride", 1.5)
        panel._migrate_knobs()
        self.assertEqual(json.loads(self.var("params"))["changes"], {})


class Presses(More):

    def test_no_active_cycle_and_no_walk_named_keys_nothing(self):
        del self.fake.vars[panel.OPTION + "walk"]
        with self.assertRaises(scene.Refusal):
            panel._apply_to("|r")
        self.assertEqual(self.applied, [])
        self.assertEqual(panel._apply_to("|r", "dw"), "dw on |r")                  # a walk named: keyed

    def test_a_clip_that_cannot_be_kept_still_takes_the_card(self):
        self.keyed = {"|a"}

        def no_cycle(root):
            raise scene.Refusal("not a cycle")
        scene.capture_source = no_cycle
        self.fake.selection = ["|a"]
        self.assertEqual(panel.press_apply(), "asd on |a")
        self.assertEqual(self.sources, {})

    def test_pick_own_on_a_walker_of_a_card_that_kept_nothing_of_its_own(self):
        self.walker("|w", "dw", working=False)
        self.fake.selection = ["|w"]
        panel.press_apply_own()
        self.assertEqual(self.applied[-1][:2], ("|w", "asd"))                       # the well's card
        del self.fake.vars[panel.OPTION + "walk"]
        line = panel.press_apply_own()
        self.assertEqual(line, "w walks asd and keeps no animation of its own - load a clip on it, or drop a walk "
                               "cycle card into the walk well")

    def test_the_list_s_right_button_with_nothing_picked(self):
        panel.build_panel()
        for press in (panel.use_card_picked, panel.use_own_picked, panel.restore_picked, panel.remove_from_list):
            self.assertEqual(press(), "pick walkers in the list first")
        self.assertEqual(panel.take_settings_picked(), "pick a walker in the list first")

    def test_use_the_active_card_and_its_own_cycle_from_the_list(self):
        panel.build_panel()
        self.fake.selection = ["|a", "|b"]
        panel.press_apply()
        self.set_var("walk", "dw")
        self.fake.values[panel.WALKER_LIST] = [2]
        self.assertEqual(panel.use_card_picked(), "dw on |b")
        self.fake.values[panel.WALKER_LIST] = [2]                 # a press lights the working rows again
        self.assertEqual(panel.use_own_picked(), "b keeps no animation of its own")
        self.fake.values[panel.WALKER_LIST] = [1, 2, 9]
        self.assertEqual(panel.use_card_picked(), "dw on |a | dw on |b")

    def test_the_lit_rows_with_the_list_gone(self):
        self.assertEqual(panel._picked_walkers(), [])
        self.assertIsNone(panel.show_list())
        panel.build_panel()
        self.assertIsNone(panel.list_selected())                                    # nothing lit

    def test_a_walker_whose_settings_cannot_be_read_is_still_worked_on(self):
        panel.build_panel()
        self.fake.selection = ["|a"]
        panel.press_apply()
        said = []
        real_status = panel.status

        def status(text):
            said.append(text)
            return real_status(text)
        self.rebind(panel, "status", status)

        def refused(root=None, memo=None, translate=True):
            raise scene.Refusal("a memo this build cannot read")
        self.rebind(scene, "memo_params", refused)
        self.fake.selection = []
        self.fake.values[panel.WALKER_LIST] = [1]
        line = panel.list_selected()
        self.assertEqual(said[0], "a memo this build cannot read")
        self.assertEqual(line, "working on a - every change keys it")
        self.assertEqual((self.memos["|a"]["working"], self.fake.selection), (True, ["|a"]))

    def test_the_first_lit_walker_s_settings_into_the_card(self):
        panel.build_panel()
        self.fake.selection = ["|a", "|b"]
        panel.press_apply()
        self.fake.values[panel.WALKER_LIST] = [2, 1]
        line = panel.take_settings_picked()
        self.assertEqual(line, "b's settings are in the card - a parameter moved keys the working walkers")

    def test_a_walker_s_settings_taken_show_its_cycle_s_clean_report(self):
        """Fixed 2026-10-27, the bug as it was (maya_walk/panel.py:1343): in _take the loop `for box, name in ((PHYSICS_BOX, "physics"),
        (KNEE_POPS_BOX, "knee_pops"))` rebinds `name`, the walker's walk read at line 1329, so line 1347 asks
        scene.walk_exists("knee_pops") - never a walk - and the Clean tab keeps the report of the cycle shown
        before: take_settings (and a row clicked in the walkers' list) never shows the walker's own cycle's clean."""
        def load_walk(name, given=None):
            self.loaded.append((name, given))
            return self.walk, {}, 0, "the clean of %s" % name
        scene.load_walk = load_walk
        self.memos["|w"] = {"walk": "dw", "pose": "", "parts": list(scene.ALL_PARTS), "listed": True,
                            "version": 3, "params": scene.plain_params({})}
        panel.build_panel()
        self.fake.values[panel.CLEAN_REPORT] = "the clean of the cycle before"
        panel.take_settings("|w")
        self.assertEqual(self.fake.values[panel.CLEAN_REPORT], "the clean of dw")

    def test_a_skeleton_walked_by_no_walk_of_this_tool_gives_no_settings(self):
        self.memos["|x"] = {"listed": True}
        self.assertEqual(panel.take_settings("|x"), "x carries no walk of this tool - Pick one first")

    def test_save_puts_the_selected_clip_in_the_walk_well_or_saves_nothing(self):
        panel.build_panel()
        self.fake.selection = ["|clip"]

        class Clip(object):
            name = "stroll"
        self.rebind(scene, "read_clip", lambda root: (Clip(), None))
        saved = []

        def save_walk_card(root, name=None):
            saved.append((root, name))
            return scene.card_walk("Walk cycles/%s.anim" % name), "%s saved as a walk card" % name
        self.rebind(scene, "save_walk_card", save_walk_card)
        prompts = []

        def prompt(**kw):
            prompts.append(kw)
            if kw.get("query"):
                return "my walk"
            return self.answer
        self.fake.promptDialog = prompt
        self.answer = "Save"
        self.assertEqual(panel.press_save_walk(), "my walk saved as a walk card")
        self.assertEqual(saved, [("|clip", "my walk")])
        self.assertEqual(prompts[0]["text"], "stroll")                             # the clip's own name offered
        self.assertEqual(self.var("walk"), scene.card_walk("Walk cycles/my walk.anim"))
        self.assertIn("Walk cycles/my walk.anim", panel.walk_list())
        self.answer = "Cancel"
        self.assertEqual(panel.press_save_walk(), "nothing saved")
        self.assertEqual(len(saved), 1)

    def test_fix_posture_that_finds_nothing_leaves_the_walker_s_edits(self):
        self.walker("|a")
        scene.fix_posture = lambda name, given=None: (base.FakeReport(), "Fix posture: nothing out of place", False)
        line = panel.press_fix_posture()
        self.assertTrue(line.startswith("Fix posture: nothing out of place | "))
        self.assertNotIn("|a", self.edits)
        self.assertEqual(self.applied[-1][0], "|a")


class RigPose(More):
    """The Rig pose tab's presses on the working walker, and the tabs' Reset."""

    def setUp(self):
        More.setUp(self)
        from maya_walk import keyrig, meanrig
        self.meanrig, self.keyrig = meanrig, keyrig
        self.calls = []

        def recorder(name, line):
            return lambda *a, **kw: self.calls.append((name,) + a + tuple(sorted(kw))) or line
        self.rebind(meanrig, "press", recorder("mean press", "mean pose rig"))
        self.rebind(meanrig, "delete", recorder("mean delete", "mean pose rig deleted"))
        self.rebind(keyrig, "press", recorder("key press", "4 key poses"))
        self.rebind(keyrig, "delete", recorder("key delete", "key poses deleted"))

    def test_create_reset_and_delete_need_a_working_walker(self):
        self.rebind(self.meanrig, "reset", lambda root, clean=None, rekey=None: self.calls.append(
            ("mean reset", root, rekey)) or "mean pose reset")
        for press in (panel.press_mean_create, panel.press_mean_reset):
            self.assertEqual(press(), panel.NO_WORKING)
        self.assertEqual(panel.press_mean_delete(), "mean pose rig deleted")       # nobody: the active cycle's
        self.assertEqual(self.calls, [("mean delete", None)])
        self.walker("|a")
        self.assertEqual(panel.press_mean_create(), "mean pose rig")
        self.assertEqual(panel.press_mean_reset(), "mean pose reset")
        panel.press_mean_delete()
        self.assertEqual(self.calls[1][:2], ("mean press", "|a"))
        self.assertEqual(sorted(self.calls[1][2]), sorted(panel.CARD_KNOBS))        # the card's clean knobs
        self.assertEqual(self.calls[2], ("mean reset", "|a", panel._rekey_root))
        self.assertEqual(self.calls[3], ("mean delete", "|a"))

    def test_an_update_refused_for_another_reason_says_it(self):
        def refused(rekey=None):
            raise self.meanrig.Refusal("the rig pose is referenced")
        self.rebind(self.meanrig, "update", refused)
        self.assertEqual(panel.press_mean_update(), "the rig pose is referenced")

    def test_an_update_of_one_kind_of_rig_alone_says_its_line(self):
        def none(rekey=None, shift=None):
            raise self.keyrig.Refusal(self.keyrig.NO_RIG)
        self.rebind(self.keyrig, "update", none)
        self.rebind(self.meanrig, "update", lambda rekey=None: "mean pose of a: spine_02 5.0 deg")
        self.rebind(self.meanrig, "rigs", lambda walker=None: ["mean"])
        self.rebind(self.keyrig, "rigs", lambda walker=None: [])
        self.assertEqual(panel.press_mean_update(), "mean pose of a: spine_02 5.0 deg")

    def test_what_all_four_keys_moved_goes_to_a_finished_walker_s_own(self):
        self.walker("|b", working=False)
        self.rebind(self.keyrig, "shift_memo", lambda root, common: "%s moved %s" % (root, sorted(common)))
        self.assertEqual(panel._shift("|b", {"height": 2.0}), "|b moved ['height']")
        self.assertNotIn(panel.OPTION + "params", self.fake.vars)                 # the card's untouched

    def test_the_rig_pose_tab_s_reset_drops_both_edits_of_the_working_walker(self):
        self.assertEqual(panel.press_reset_group("rigpose"), panel.NO_WORKING)
        self.walker("|a")
        mean_rekeys = []

        def mean_reset(root, clean=None, rekey=None):
            mean_rekeys.append(rekey(root))
            return "mean pose of a reset"
        self.rebind(self.meanrig, "reset", mean_reset)
        self.rebind(self.keyrig, "reset", lambda root, rekey=None: "key poses of a reset" + rekey(root))
        line = panel.press_reset_group("rigpose")
        self.assertEqual(line, "mean pose of a reset | key poses of a reset -> a keyed again")
        self.assertEqual(mean_rekeys, [""])                                         # keyed once, by the second
        self.assertEqual([a[0] for a in self.applied], ["|a"])

    def test_the_clean_tab_s_reset_puts_seam_and_smooth_back_and_fix_posture_off(self):
        self.walker("|a")
        self.walker("|b")
        self.walker("|c", working=False)
        self.edits["|a"] = dict(scene.empty_edits("asd"), posture=True)
        self.edits["|c"] = dict(scene.empty_edits("asd"), posture=True)
        self.set_var("knob_seam", 3.0)
        self.set_var("knob_smooth", 2.0)
        line = panel.press_reset_group("clean")
        self.assertIn("Clean back to its defaults, Fix posture off", line)
        self.assertEqual((self.var("knob_seam"), self.var("knob_smooth")),
                         (scene.ALL_DEFAULTS["seam"], scene.ALL_DEFAULTS["smooth"]))
        self.assertFalse(self.edits["|a"]["posture"])
        self.assertNotIn("|b", self.edits)                                         # nothing to turn off
        self.assertTrue(self.edits["|c"]["posture"])                               # a finished walker kept
        self.assertEqual(sorted(a[0] for a in self.applied), ["|a", "|b"])
        self.assertEqual(self.applied[-1][2]["seam"], scene.ALL_DEFAULTS["seam"])

    def test_the_physics_tab_s_reset_turns_the_helpers_back_on(self):
        self.walker("|a")
        self.set_var("physics", 0.0)
        self.set_var("knee_pops", 0.0)
        panel._remember_hand({"balance": ("offset", -1.0), "step": ("ratio", 1.2)}, {"balance", "step"})
        line = panel.press_reset_group("physics")
        self.assertIn("Physics back to the clip's own", line)
        p = self.params()
        self.assertEqual((p["physics"], p["knee_pops"]), (True, True))
        self.assertEqual(sorted(p["changes"]), ["step"])                           # Main's change stays
        self.assertEqual(p["pins"], ["step"])


class Folders(More):

    def test_the_walks_folder_is_made_and_shown(self):
        opened = []
        self.rebind(os, "startfile", opened.append)
        folder = scene.folder()
        self.assertFalse(os.path.isdir(folder))
        self.assertEqual(panel.show_folder(), "the walks folder: %s" % folder)
        self.assertTrue(os.path.isdir(folder))
        self.assertEqual(opened, [folder])
        panel.show_folder()                                                        # there already
        self.assertEqual(opened, [folder, folder])

    def test_the_lists_read_again_count_the_cards_and_the_files(self):
        panel.build_panel()
        self.set_var("walkCards", json.dumps([CARD_A, CARD_B]))
        line = panel.refresh_lists()
        self.assertEqual(line, "2 walk cards in the well, 2 walk files in %s" % scene.folder())
        self.assertEqual(self.fake.values[panel.STATUS], line)


class Build(More):
    """build_panel: the first card of a session moves the old walks and poses into the library; a migration or a
    well that fails leaves the card standing; the skinned card; its selection job; the hub opened on it."""

    def old_files(self):
        from tests import test_walk_cycle_cards as cycles
        from tests import test_walk_cards as poses
        from maya_walk import model as wm
        data = cycles.walk()
        wf.save(wf.path_for(scene.folder(), "asd"), wf.clip_of(data, wm), data["statics"], data["start"])
        wf.save_pose(wf.pose_path_for(scene.folder(), "goblin"), "goblin", poses.bones(2.0))

    def test_the_first_card_moves_the_old_walks_and_poses_into_the_library_once(self):
        self.old_files()
        with hushed() as out:
            panel.build_panel()
        printed = out.getvalue()
        self.assertIn("1 walk(s) moved into the Pose Library, folder Walk cycles: asd", printed)
        self.assertIn("1 old pose(s) moved into the Pose Library, folder Walk poses: goblin", printed)
        walk = os.path.join(self.library, "Walk cycles", "asd.anim")
        pose = os.path.join(self.library, "Walk poses", "goblin.pose")
        self.assertTrue(os.path.isdir(walk) and os.path.isdir(pose))
        import shutil
        shutil.rmtree(walk)
        with hushed() as out:
            panel.build_panel()                                                    # the same session: not again
        self.assertNotIn("moved", out.getvalue())
        self.assertFalse(os.path.isdir(walk))

    def test_a_migration_or_a_well_that_fails_leaves_the_card_with_its_lines(self):
        from maya_walk import posewell

        def broken(*a, **kw):
            raise RuntimeError("cannot")
        self.rebind(scene.wcards, "migrate_walks", broken)
        self.rebind(scene.wcards, "migrate", broken)
        self.rebind(posewell, "attach", broken)
        with hushed() as out:
            panel.build_panel()
        self.assertGreaterEqual(out.getvalue().count("RuntimeError: cannot"), 4)
        self.assertIn("Walk: asd", self.fake.values[panel.WALK_WELL_TEXT])
        self.assertEqual(self.fake.values[panel.POSE_WELL_TEXT], "Pose: none - Pose Library card > Use in Walk Builder")
        self.assertTrue(panel.is_open())

    def test_the_skinned_card_lays_the_parts_in_a_flow(self):
        import maya_hubstyle
        was = maya_hubstyle.skinning()
        maya_hubstyle.set_skinning(True)
        try:
            panel.build_panel()
        finally:
            maya_hubstyle.set_skinning(was)
        self.assertEqual(len(self.made("flowLayout")), 1)
        marks = dict((m.name, m.role) for m in self.hubstyle.take_marks())
        self.assertEqual(marks[panel._part_control("torso")], "chip")

    def test_the_selection_job_forgets_a_closed_copy_s_and_one_maya_forgot(self):
        panel.JOB["hubcopy99999"] = 41                                             # a popup copy closed long ago
        panel.JOB[""] = 42
        real = self.fake.scriptJob

        def job(**kw):
            if kw.get("exists") is not None:
                raise RuntimeError("Maya forgot it")
            return real(**kw)
        self.fake.scriptJob = job
        panel.start()
        self.assertNotIn("hubcopy99999", panel.JOB)
        self.assertNotEqual(panel.JOB[""], 42)
        self.assertEqual(self.fake.killed, [])

    def test_show_window_opens_the_hub_on_walk_builder(self):
        import maya_hub
        shown = []
        self.rebind(maya_hub, "show", lambda key: shown.append(key) or "hub")
        self.assertEqual(panel.show_window(), "hub")
        self.assertEqual(shown, ["walk"])

    def test_the_report_s_height_follows_its_wrapped_lines(self):
        self.assertEqual(panel.report_height(""), 2 * panel.REPORT_LINE + 6)
        long = "x" * (panel.REPORT_CHARS * 3 + 1)
        self.assertEqual(panel.report_height(long + "\nshort"), 5 * panel.REPORT_LINE + 6)
        panel.show_report("closed card")                                           # nowhere to show it
        self.assertNotIn(panel.CLEAN_REPORT, self.fake.values)


if __name__ == "__main__":
    unittest.main()
