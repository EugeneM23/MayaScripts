"""The Time Bar's live key drag (`scene.live_begin / live_to / live_end`) on a fake
cmds that, like Maya, deletes an animCurve the moment a cut leaves it empty
(CLAUDE.md trap 210). 2026-10-19, the animator: «ключи просто изчезают при
переносе по таймлайну» - a curve whose every key was dragged (one key on a
channel) lost its curve on the first cut, and the keys with it."""
import unittest

from maya_timebar import scene


class FakeCmds(object):
    """Curves as {name: {time: (value, breakdown)}}; an emptied curve is deleted.

    `keyframe -edit -relative -timeChange -option over` moves a group of keys as
    Maya does (2026-10-20, measured in mayapy): past keys standing between them, and
    onto each other's frames. A key moved onto a frame that holds a key outside the
    group makes TWO keys on that frame in Maya, so here it raises. A breakdown that
    stays while a neighbour moves slides to keep its place between them, as Maya
    slides it (measured: 45 -> 45.5). Every edit counts in `edits`; tangent edits
    are kept in `tangents`."""

    def __init__(self, curves, breakdowns=()):
        self.curves = dict((c, dict((float(t), (float(v), float(t) in breakdowns))
                                    for t, v in keys))
                           for c, keys in curves.items())
        self.deleted = []
        self.edits = 0
        self.tangents = []

    # -- scene
    def objExists(self, name):
        return name in self.curves

    def ls(self, *args, **kw):
        if args and isinstance(args[0], (list, tuple)):
            return [n for n in args[0] if n in self.curves]
        return ["cube"] if kw.get("selection") else []

    def undoInfo(self, *args, **kw):
        return True if kw.get("q") else None

    def dgdirty(self, *args, **kw):
        pass

    def currentTime(self, *args, **kw):
        return 0.0

    # -- keys
    def _in(self, t, span):
        if span is None:
            return True
        if isinstance(span, list):                     # several ranges, Maya's multi-use -time
            return any(self._in(t, s) for s in span)
        return span[0] - 1e-9 <= t <= span[1] + 1e-9

    def _names(self, curve):
        return list(curve) if isinstance(curve, (list, tuple)) else [curve]

    def _move(self, curves, time, change, relative, option):
        assert relative and option == "over", (relative, option)
        self.edits += 1
        for c in self._names(curves):
            keys = self.curves[c]
            moving = [t for t in keys if self._in(t, time)]
            rest = dict((t, k) for t, k in keys.items() if t not in moving)
            for t in moving:
                if any(abs(t + change - r) < 1e-6 for r in rest):
                    raise AssertionError("two keys on frame %s of %s" % (t + change, c))
            order = sorted(keys)
            slid = {}
            for i, t in enumerate(order):
                if t in moving or not keys[t][1] or i == 0 or i == len(order) - 1:
                    continue
                lo, hi = order[i - 1], order[i + 1]
                if lo in moving or hi in moving:
                    nlo = lo + change if lo in moving else lo
                    nhi = hi + change if hi in moving else hi
                    slid[t] = nlo + (t - lo) / (hi - lo) * (nhi - nlo)
            for t, nt in slid.items():
                rest[nt] = rest.pop(t)
            for t in moving:
                rest[t + change] = keys[t]
            self.curves[c] = rest

    def _flag(self, curves, time, on):
        self.edits += 1
        for c in self._names(curves):
            for t, (v, _bd) in list(self.curves[c].items()):
                if self._in(t, time):
                    self.curves[c][t] = (v, bool(on))

    def keyframe(self, curve=None, q=False, time=None, timeChange=False, valueChange=False,
                 breakdown=None, name=False, edit=False, relative=False, option=None, **kw):
        if edit:
            if not relative:
                return self._flag(curve, time, breakdown)
            return self._move(curve, time, timeChange, relative, option)
        assert q, "only queries"
        names = [curve] if curve else list(self.curves)
        if name:
            return [c for c in names if c in self.curves
                    and any(self._in(t, time) for t in self.curves[c])]
        out = []
        for c in names:
            if c not in self.curves:
                raise ValueError("No object matches name: %s" % c)
            for t in sorted(self.curves[c]):
                if not self._in(t, time):
                    continue
                v, bd = self.curves[c][t]
                if breakdown:
                    if bd:
                        out.append(t)
                elif valueChange:
                    out.append(v)
                elif timeChange:
                    out.append(t)
        return out

    def keyTangent(self, curve, q=False, edit=False, **kw):
        if curve not in self.curves:
            raise ValueError("No object matches name: %s" % curve)
        if q:
            n = len(self.curves[curve])
            if kw.get("weightedTangents"):
                return [False]
            if "inTangentType" in kw or "outTangentType" in kw:
                return ["auto"] * n
            if "lock" in kw:
                return [True] * n
            return [0.0] * n
        self.edits += 1
        self.tangents.append(dict(kw))
        return None

    def setKeyframe(self, curve, time=(), value=0.0, breakdown=False, **kw):
        if curve not in self.curves:
            raise ValueError("No object matches name: %s" % curve)
        self.edits += 1
        self.curves[curve][float(time[0])] = (float(value), bool(breakdown))

    def cutKey(self, curve, time=None, clear=False, **kw):
        self.edits += 1
        for c in self._names(curve):
            keys = self.curves[c]
            for t in [t for t in keys if self._in(t, time)]:
                del keys[t]
            if not keys:                               # Maya: an emptied curve is deleted
                del self.curves[c]
                self.deleted.append(c)


class LiveDrag(unittest.TestCase):

    def setUp(self):
        self._cmds, self._scope = scene.cmds, scene._scope
        scene._scope = lambda: None                     # no animation layers
        scene._LIVE.clear()

    def tearDown(self):
        scene.cmds, scene._scope = self._cmds, self._scope
        scene._LIVE.clear()

    def drag(self, curves, selection, target):
        fake = FakeCmds(curves)
        scene.cmds = fake
        self.assertTrue(scene.live_begin(selection))
        a, b = selection
        step = 1 if target[0] >= a else -1
        for d in range(step, target[0] - a + step, step):
            scene.live_to((a + d, b + d))
        scene.live_end(target)
        return fake

    def keys_of(self, fake, curve):
        return dict((t, v) for t, (v, _bd) in fake.curves.get(curve, {}).items())

    def test_a_single_key_on_its_channel_keeps_its_curve(self):
        fake = self.drag({"cube_tx": [(10, 5.0)]}, (10, 10), (15, 15))
        self.assertEqual(fake.deleted, [])
        self.assertEqual(self.keys_of(fake, "cube_tx"), {15.0: 5.0})

    def test_every_key_of_a_curve_dragged_keeps_them_all(self):
        fake = self.drag({"cube_tx": [(0, 1.0), (10, 5.0)]}, (0, 10), (3, 13))
        self.assertEqual(fake.deleted, [])
        self.assertEqual(self.keys_of(fake, "cube_tx"), {3.0: 1.0, 13.0: 5.0})

    def test_a_drag_backwards_keeps_the_keys(self):
        fake = self.drag({"cube_tx": [(10, 5.0)]}, (10, 10), (4, 4))
        self.assertEqual(self.keys_of(fake, "cube_tx"), {4.0: 5.0})

    def test_one_key_of_two_moves_the_other_stays(self):
        fake = self.drag({"cube_tx": [(0, 1.0), (10, 5.0)]}, (10, 10), (14, 14))
        self.assertEqual(self.keys_of(fake, "cube_tx"), {0.0: 1.0, 14.0: 5.0})

    def test_many_channels_each_with_one_key(self):
        curves = dict(("cube_%s" % a, [(20, float(i))]) for i, a in enumerate("tx ty tz rx ry rz".split()))
        fake = self.drag(curves, (20, 20), (26, 26))
        self.assertEqual(fake.deleted, [])
        for i, a in enumerate("tx ty tz rx ry rz".split()):
            self.assertEqual(self.keys_of(fake, "cube_%s" % a), {26.0: float(i)})

    def test_a_drag_given_up_puts_a_single_key_back(self):
        fake = FakeCmds({"cube_tx": [(10, 5.0)]})
        scene.cmds = fake
        scene.live_begin((10, 10))
        scene.live_to((12, 12))
        scene.live_to((16, 16))
        scene.live_end(None)
        self.assertEqual(fake.deleted, [])
        self.assertEqual(self.keys_of(fake, "cube_tx"), {10.0: 5.0})


def expected(curves, selection, target):
    """What every curve must hold with the block `selection` dragged onto `target`:
    the keys outside stay, the block's keys land on `look.mapped` (over a key that
    stood there)."""
    from maya_timebar import look
    out = {}
    for curve, keys in curves.items():
        got = dict((float(t), float(v)) for t, v in keys if not look.inside(t, selection))
        for t, v in keys:
            if look.inside(t, selection):
                got[float(look.mapped(t, selection, target))] = float(v)
        out[curve] = got
    return out


class BlockDrag(unittest.TestCase):
    """A highlight of many keys on many curves dragged (2026-10-19: «ты не проверил
    кейс когда мы переносим массив ключей»): checked on every step of the drag, not
    only on the release."""

    CURVES = {
        "a_tx": [(t, t * 0.5) for t in (0, 5, 10, 15, 20, 25, 30)],
        "a_ty": [(t, t % 10) for t in (0, 5, 10, 15, 20, 25, 30)],
        "a_tz": [(5, 5.25), (10, 10.25), (15, 15.25)],      # every key in the block
        "a_rx": [(10, 45.0)],                               # one lone key in it
        "b_tx": [(t, t + 1.0) for t in (0, 5, 10, 15, 20, 25, 30)],
        "b_rx": [(30, 7.0)],                                # nothing in the block
    }

    def setUp(self):
        self._cmds, self._scope = scene.cmds, scene._scope
        scene._scope = lambda: None
        scene._LIVE.clear()

    def tearDown(self):
        scene.cmds, scene._scope = self._cmds, self._scope
        scene._LIVE.clear()

    def run_drag(self, kind, selection, frames):
        from maya_timebar import look
        fake = FakeCmds(self.CURVES)
        scene.cmds = fake
        self.assertTrue(scene.live_begin(selection))
        step = 1 if frames > 0 else -1
        target = tuple(selection)
        grip = selection[1] if kind == "h1" else selection[0]
        for i in range(step, frames + step, step):
            target = look.key_drag(kind, selection, grip, grip + i)
            scene.live_to(target)
            now = dict((c, dict((t, v) for t, (v, _bd) in keys.items()))
                       for c, keys in fake.curves.items())
            want = expected(self.CURVES, selection, target)
            self.assertEqual(now, want, "step %d, the block on %s" % (i, target))
        scene.live_end(target)
        self.assertEqual(fake.deleted, [])
        final = dict((c, dict((t, v) for t, (v, _bd) in keys.items())) for c, keys in fake.curves.items())
        self.assertEqual(final, expected(self.CURVES, selection, target))
        return target

    def test_a_block_dragged_forward_over_a_key_that_stays(self):
        self.assertEqual(self.run_drag("hmove", (5, 15), 7), (12, 22))

    def test_a_block_dragged_back_over_a_key_that_stays(self):
        self.assertEqual(self.run_drag("hmove", (5, 15), -8), (-3, 7))

    def test_a_block_dragged_past_every_other_key(self):
        self.assertEqual(self.run_drag("hmove", (5, 15), 20), (25, 35))

    def test_the_whole_take_dragged(self):
        self.assertEqual(self.run_drag("hmove", (0, 30), 3), (3, 33))

    def test_the_right_edge_stretches_the_block(self):
        self.assertEqual(self.run_drag("h1", (5, 15), 10), (5, 25))

    def test_the_left_edge_squeezes_the_block(self):
        self.assertEqual(self.run_drag("h0", (5, 15), 8), (13, 15))

    def test_the_left_edge_stretches_the_block_back(self):
        self.assertEqual(self.run_drag("h0", (5, 15), -6), (-1, 15))


def dense(names, last):
    return dict((n, [(t, (t * (i + 3)) % 11 + 0.25) for t in range(0, last + 1)])
                for i, n in enumerate(names))


def held(fake):
    return dict((c, dict((t, v) for t, (v, _bd) in keys.items())) for c, keys in fake.curves.items())


class StepCost(unittest.TestCase):
    """2026-10-20, «ключи сильно задерживаются за курсором»: every mouse move wrote
    every dragged key again (setKeyframe and four keyTangent edits each), 190 ms a
    step for a 40-frame block on 48 curves. A block's move is one shift of its keys:
    a step costs what the keys it covers and uncovers cost, not what the block holds."""

    def setUp(self):
        self._cmds, self._scope = scene.cmds, scene._scope
        scene._scope = lambda: None
        scene._LIVE.clear()

    def tearDown(self):
        scene.cmds, scene._scope = self._cmds, self._scope
        scene._LIVE.clear()

    def step_edits(self, selection):
        fake = FakeCmds(dense(["c_tx", "c_ty", "c_tz", "c_rx", "c_ry", "c_rz"], 80))
        scene.cmds = fake
        scene.live_begin(selection)
        scene.live_to((selection[0] + 1, selection[1] + 1))
        fake.edits = 0
        scene.live_to((selection[0] + 2, selection[1] + 2))
        scene._LIVE.clear()
        return fake.edits

    def test_a_block_step_costs_the_same_whatever_the_block_holds(self):
        short, long_ = self.step_edits((10, 29)), self.step_edits((10, 49))
        self.assertEqual(short, long_)
        self.assertLess(short, 6 * 8)                    # six curves, a few edits each

    def test_a_single_key_step_writes_no_key_again(self):
        fake = FakeCmds({"c_tx": [(0, 1.0), (10, 5.0), (40, 2.0)]})
        scene.cmds = fake
        scene.live_begin((10, 10))
        scene.live_to((11, 11))
        fake.edits = 0
        scene.live_to((12, 12))
        self.assertEqual(fake.edits, 1)                  # the one move, nothing put or cut
        self.assertEqual(held(fake)["c_tx"], {0.0: 1.0, 12.0: 5.0, 40.0: 2.0})


class StampThenDrag(unittest.TestCase):
    """S during the drag leaves copies where the keys stand; the drag goes on, or is
    given up (the copies go with it)."""

    def setUp(self):
        self._cmds, self._scope = scene.cmds, scene._scope
        scene._scope = lambda: None
        scene._LIVE.clear()

    def tearDown(self):
        scene.cmds, scene._scope = self._cmds, self._scope
        scene._LIVE.clear()

    CURVES = {"d_tx": [(t, t * 0.5) for t in range(0, 41)],
              "d_ty": [(t, (t * 7) % 5) for t in range(0, 41, 4)]}

    def want(self, stamp, target):
        from maya_timebar import look
        sel = (10, 20)
        out = {}
        for c, keys in self.CURVES.items():
            got = dict((float(t), float(v)) for t, v in keys if not look.inside(t, sel))
            for t, v in keys:
                if look.inside(t, sel):
                    got[float(look.mapped(t, sel, stamp))] = float(v)
            for t, v in keys:
                if look.inside(t, sel):
                    got[float(look.mapped(t, sel, target))] = float(v)
            out[c] = got
        return out

    def test_the_copies_stay_and_the_keys_go_on(self):
        fake = FakeCmds(self.CURVES)
        scene.cmds = fake
        scene.live_begin((10, 20))
        for d in (1, 2, 3):
            scene.live_to((10 + d, 20 + d))
        scene.live_stamp()
        for d in (4, 5, 6, 7, 8, 7, 6, 12):
            scene.live_to((10 + d, 20 + d))
            self.assertEqual(held(fake), self.want((13, 23), (10 + d, 20 + d)), "step %d" % d)
        scene.live_end((22, 32))
        self.assertEqual(held(fake), self.want((13, 23), (22, 32)))

    def test_given_up_after_a_stamp_the_curves_are_as_they_were(self):
        fake = FakeCmds(self.CURVES)
        scene.cmds = fake
        scene.live_begin((10, 20))
        scene.live_to((14, 24))
        scene.live_stamp()
        scene.live_to((17, 27))
        scene.live_end(None)
        start = dict((c, dict((float(t), float(v)) for t, v in keys)) for c, keys in self.CURVES.items())
        self.assertEqual(held(fake), start)


class BreakdownsAndWeights(unittest.TestCase):
    """2026-10-20, the shift checked against Maya's own move (verify_timebar_live_shift.py):
    a breakdown beside the moving block slid between its moving neighbours (45 ->
    45.5, its curve 4.9 off), and a key written again turned a weighted curve's auto
    tangent fixed, its angle 0."""

    def setUp(self):
        self._cmds, self._scope = scene.cmds, scene._scope
        scene._scope = lambda: None
        scene._LIVE.clear()

    def tearDown(self):
        scene.cmds, scene._scope = self._cmds, self._scope
        scene._LIVE.clear()

    def test_breakdowns_keep_their_frames_and_their_flags(self):
        # every frame 0..40; breakdowns beside the block (19, 31) and in it (24)
        fake = FakeCmds({"c": [(t, t * 0.5) for t in range(0, 41)]}, breakdowns=(19.0, 24.0, 31.0))
        scene.cmds = fake
        self.assertTrue(scene.live_begin((20, 29)))
        for i in range(1, 6):
            scene.live_to((20 + i, 29 + i))
        scene.live_end((25, 34))
        keys = fake.curves["c"]
        self.assertTrue(all(abs(t - round(t)) < 1e-9 for t in keys), sorted(keys))
        self.assertEqual(sorted(t for t, (_v, bd) in keys.items() if bd), [19.0, 29.0])
        self.assertEqual(keys[19.0][0], 9.5)              # the breakdown before the block, as it was
        self.assertEqual(keys[29.0][0], 12.0)             # the dragged breakdown, from 24

    def test_a_weighted_curve_s_auto_key_written_again_gets_no_weight(self):
        fake = FakeCmds({"c": [(0, 0.0), (10, 1.0)]})
        scene.cmds = fake
        data = {"value": 2.0, "breakdown": False, "itt": "auto", "ott": "fixed",
                "ia": 10.0, "oa": 20.0, "iw": 3.0, "ow": 7.5, "lock": False, "weighted": True}
        scene._put_key("c", 5.0, data)
        flags = set(k for edit in fake.tangents for k in edit)
        self.assertNotIn("inWeight", flags)               # an auto side's weight is Maya's
        self.assertIn({"time": (5.0, 5.0), "outWeight": 7.5}, fake.tangents)


class HighlightUnrecorded(unittest.TestCase):
    """The highlight is no undo step, as Maya's own slider's is not: a key drag
    moves the highlight with the keys, and the first Ctrl+Z put the highlight back
    and left the keys moved."""

    def test_set_highlight_writes_with_undo_off(self):
        log = []

        class Cmds(object):
            def __init__(self):
                self.on = True

            def undoInfo(self, q=False, state=False, stateWithoutFlush=None, **kw):
                if q:
                    return self.on
                if stateWithoutFlush is not None:
                    self.on = bool(stateWithoutFlush)

            def playbackOptions(self, **kw):
                log.append((self.on, kw))

        saved = scene.cmds
        scene.cmds = fake = Cmds()
        try:
            scene.set_highlight((5, 8))
            scene.set_highlight(None)
        finally:
            scene.cmds = saved
        self.assertEqual([on for on, _kw in log], [False, False])
        self.assertTrue(fake.on)                        # undo is back on after

    def test_the_time_is_set_with_undo_off(self):
        # in a GUI Maya a scripted currentTime -e is an undo step; Maya's own slider
        # records none (2026-10-19, measured by the scene tabs session)
        log = []

        class Cmds(object):
            def __init__(self):
                self.on = True

            def undoInfo(self, q=False, state=False, stateWithoutFlush=None, **kw):
                if q:
                    return self.on
                if stateWithoutFlush is not None:
                    self.on = bool(stateWithoutFlush)

            def currentTime(self, *args, **kw):
                log.append((self.on, args, kw))
                return 7.0

        saved = scene.cmds
        scene.cmds = fake = Cmds()
        try:
            scene.set_time(12)
            scene.scrub_only(13)
            scene.step_key(True, [5, 20])               # to 20, through set_time
        finally:
            scene.cmds = saved
        edits = [(on, args) for on, args, kw in log if kw.get("edit")]
        self.assertEqual(edits, [(False, (12,)), (False, (13,)), (False, (20,))])
        self.assertTrue(fake.on)


if __name__ == "__main__":
    unittest.main()
