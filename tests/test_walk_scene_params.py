"""maya_walk.scene on the parameters (2026-10-26): the memo version 3 holding the card's parameters, a version 2
memo (the model's knobs) read and translated into parameters, apply keying the parameters' engine knobs - on the
synthetic walker of tests/test_walkmodel.py and a fake cmds."""

import json
import unittest

from tests import test_walkmodel as tw

wm = tw.wm
gait = tw.load("gait")
scene = tw.load("scene")
wc = tw.load("clean")


class FakeCmds(object):
    def __init__(self, memos):
        self.memos = memos

    def attributeQuery(self, attr, node=None, exists=False):
        return node in self.memos

    def getAttr(self, plug):
        return self.memos[plug.split(".")[0]]

    def ls(self, node, long=False, uuid=False):
        return ["uuid-" + node] if uuid else [node]


class Patched(unittest.TestCase):
    NAMES = ("_cmds", "load_walk", "read_bones", "evaluated", "weapons_in_hands", "channel_values",
             "write_curves", "keys_print", "_set_memo", "walk_fix", "walk_keys", "_Chunk", "_state",
             "walker_edits", "edits_of", "set_edits")

    def setUp(self):
        self.saved = dict((n, getattr(scene, n)) for n in self.NAMES)
        self.saved_retarget = scene.wt.Retarget
        self.memos = {}
        self.walk = tw.walk()
        self.loads = []

        def load_walk(name, given=None, edits=None):
            self.loads.append((name, dict(given or {})))
            return self.walk, {}, 0, Report()
        scene._cmds = lambda: FakeCmds(self.memos)
        scene.load_walk = load_walk
        scene.walker_edits = lambda root, walk: (scene.empty_edits(walk), "")
        scene.edits_of = lambda root: scene.empty_edits("")
        scene.set_edits = lambda root, edits: None

    def tearDown(self):
        for name, value in self.saved.items():
            setattr(scene, name, value)
        scene.wt.Retarget = self.saved_retarget


class Shift(unittest.TestCase):

    def test_what_all_four_keys_did_moves_height_and_forward_pinned(self):
        p = scene.shift_params({"changes": {"height": ("offset", 2.0), "step": ("ratio", 1.1)}}, {"height": 3.0,
                                                                                                   "forward": -1.5})
        self.assertEqual(p["changes"]["height"], ("offset", 5.0))
        self.assertEqual(p["changes"]["forward"], ("offset", -1.5))
        self.assertEqual(p["changes"]["step"], ("ratio", 1.1))
        self.assertEqual(p["pins"], ["forward", "height"])


class Report(object):
    changed = False


class Params(Patched):

    def test_normal_params_keeps_known_keys_and_fills_the_rest(self):
        p = scene.normal_params({"changes": {"step": ["ratio", "1.2"], "nope": ["ratio", 2.0],
                                             "bounce": ["sideways", 1.0], "arm_lag_l": ("offset", 2)},
                                 "pins": ["step", "nope"], "macros": {"weight": 0.5, "other": 1.0},
                                 "character": "Nobody"})
        self.assertEqual(p["changes"], {"step": ("ratio", 1.2), "arm_lag_l": ("offset", 2.0)})
        self.assertEqual(p["pins"], ["step"])
        self.assertEqual(p["macros"], {"weight": 0.5})
        self.assertEqual(p["character"], "")
        self.assertTrue(p["physics"])
        self.assertEqual(p["clean"], wc.knobs({}))

    def test_plain_params_survive_json(self):
        p = {"changes": {"step": ("ratio", 1.2)}, "pins": ["step"], "macros": {"weight": -0.5},
             "character": "Tired", "strength": 0.7, "physics": False, "pose": 0.8, "in_place": 1.0}
        back = scene.normal_params(json.loads(json.dumps(scene.plain_params(p))))
        self.assertEqual(back, scene.normal_params(p))

    def test_the_engine_knobs_are_the_parameters(self):
        p = {"changes": {"step": ("ratio", 1.2)}, "pins": ["step"], "pose": 0.6, "in_place": 1.0}
        knobs, vals = scene.params_knobs(self.walk, p)
        own = gait.own(self.walk)
        want = gait.engine_knobs(self.walk, own, gait.values(own, {"step": ("ratio", 1.2)}, ["step"]), ["step"])
        for key, value in want.items():
            self.assertAlmostEqual(knobs[key], value, places=9, msg=key)
        self.assertAlmostEqual(knobs["stride"], 1.2, places=9)
        self.assertEqual(knobs["pose"], 0.6)
        self.assertEqual(knobs["in_place"], 1.0)
        self.assertAlmostEqual(vals["step"], 1.2 * own["step"], places=6)


class Memo(Patched):

    def test_versions_two_and_three_are_read_one_is_not(self):
        for version, read in ((1, False), (2, True), (3, True)):
            self.memos["|root"] = json.dumps({"walk": "asd", "version": version})
            self.assertEqual(bool(scene.memo_of("|root")), read, version)

    def test_a_version_three_memo_gives_its_parameters(self):
        memo = {"walk": "asd", "version": 3, "params": {"changes": {"bounce": ["ratio", 1.5]}, "pins": ["bounce"]}}
        p = scene.memo_params(memo=memo)
        self.assertEqual(p["changes"], {"bounce": ("ratio", 1.5)})
        self.assertEqual(self.loads, [])                         # no walk read

    def test_a_version_two_memo_is_translated(self):
        memo = {"walk": "asd", "version": 2,
                "knobs": {"stride": 1.2, "bob": 1.5, "weight": 0.5, "overlap": 2.0, "pose": 0.7, "in_place": 1.0,
                          "seam": 6.0}}
        p = scene.memo_params(memo=memo)
        self.assertEqual(p["changes"]["step"], ("ratio", 1.2))
        self.assertEqual(p["changes"]["bounce"], ("ratio", 1.5))
        self.assertAlmostEqual(p["changes"]["arm_lag"][1], 1.6)
        self.assertEqual(p["macros"], {"weight": 0.5})
        self.assertIn("step", p["pins"])
        self.assertEqual((p["pose"], p["in_place"]), (0.7, 1.0))
        self.assertEqual(p["clean"]["seam"], wc.knobs({"seam": 6.0})["seam"])
        self.assertIsNone(scene.memo_params(memo=memo, translate=False))

    def test_a_version_two_memo_whose_walk_is_gone_keeps_its_pose_and_clean(self):
        def gone(name, given=None):
            raise scene.Refusal("no saved walk named asd")
        scene.load_walk = gone
        p = scene.memo_params(memo={"walk": "asd", "version": 2, "knobs": {"pose": 0.4, "stride": 1.3}})
        self.assertEqual(p["changes"], {})
        self.assertEqual(p["pose"], 0.4)

    def test_no_walk_no_parameters(self):
        self.assertIsNone(scene.memo_params(memo={}))


class FakeRetarget(object):
    def __init__(self, walk, statics, bones, place):
        self.place = [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]]

    def frames(self, result, knee_pops=True):
        self.knee_pops = knee_pops
        return {}, {"scale": 1.0, "drop": [0.0], "short": 0.0}

    def written(self):
        return ["pelvis"]

    def translated(self):
        return []


class Nothing(object):
    def __init__(self, *a):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class Apply(Patched):

    def setUp(self):
        Patched.setUp(self)
        self.evaluated = []
        self.written = {}
        scene.read_bones = lambda root: ({}, "")
        scene.weapons_in_hands = lambda root, commands=None: {}
        scene.wt.Retarget = FakeRetarget
        real = scene.evaluated

        def evaluated(walk, knobs, pose, prepared=None, parts=(), weapons=None):
            self.evaluated.append(dict(knobs))
            return real(walk, knobs, pose, prepared, parts)
        scene.evaluated = evaluated
        scene.channel_values = lambda bones, frames, written, translated: ({}, {})
        scene.write_curves = lambda values, static, start, in_place=False: (None, {})
        scene.keys_print = lambda root: "keys"
        scene.walk_fix = lambda name: ({}, "")
        scene.walk_keys = lambda name: ({}, "")
        scene._Chunk = Nothing
        self.state = {"loaded": {}, "target": None}
        scene._state = lambda: self.state

        def set_memo(root, memo):
            self.written[root] = memo
            self.memos[root] = json.dumps(memo)
        scene._set_memo = set_memo

    def test_apply_keys_the_parameters_engine_knobs_and_writes_a_version_four_memo(self):
        params = {"changes": {"step": ("ratio", 1.15)}, "pins": ["step"], "macros": {"weight": 0.5}}
        result, info, line = scene.apply("|root", "asd", {"seam": 4.0}, params=params)
        want = scene.params_knobs(self.walk, scene.normal_params(params))[0]
        for key, value in want.items():
            self.assertAlmostEqual(self.evaluated[-1][key], value, places=9, msg=key)
        memo = self.written["|root"]
        self.assertEqual(memo["version"], 4)
        self.assertEqual(memo["params"]["changes"], {"step": ["ratio", 1.15]})
        self.assertEqual(memo["params"]["clean"]["seam"], wc.knobs({"seam": 4.0})["seam"])   # the given's clean
        self.assertEqual(self.loads[-1][1]["seam"], wc.knobs({"seam": 4.0})["seam"])
        self.assertAlmostEqual(info["values"]["step"], 1.15 * gait.own(self.walk)["step"], places=6)
        self.assertIn("step", info["measured"])
        self.assertIsInstance(info["diagnosis"], list)
        back = scene.memo_params("|root")
        self.assertEqual(back["changes"], {"step": ("ratio", 1.15)})
        self.assertEqual(back["macros"], {"weight": 0.5})

    def test_without_parameters_apply_keys_the_given_knobs_as_before(self):
        result, info, line = scene.apply("|root", "asd", {"stride": 1.2})
        self.assertEqual(self.evaluated[-1], {"stride": 1.2})
        self.assertNotIn("params", self.written["|root"])
        self.assertNotIn("diagnosis", info)


if __name__ == "__main__":
    unittest.main()
