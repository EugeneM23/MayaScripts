"""The Time Bar's live key drag (`scene.live_begin / live_to / live_end`) on a fake
cmds that, like Maya, deletes an animCurve the moment a cut leaves it empty
(CLAUDE.md trap 210). 2026-10-19, the animator: «ключи просто изчезают при
переносе по таймлайну» - a curve whose every key was dragged (one key on a
channel) lost its curve on the first cut, and the keys with it."""
import unittest

from maya_timebar import scene


class FakeCmds(object):
    """Curves as {name: {time: (value, breakdown)}}; an emptied curve is deleted."""

    def __init__(self, curves):
        self.curves = dict((c, dict((float(t), (float(v), False)) for t, v in keys))
                           for c, keys in curves.items())
        self.deleted = []

    # -- scene
    def objExists(self, name):
        return name in self.curves

    def ls(self, *args, **kw):
        return ["cube"] if kw.get("selection") else []

    def undoInfo(self, *args, **kw):
        return True if kw.get("q") else None

    def dgdirty(self, *args, **kw):
        pass

    def currentTime(self, *args, **kw):
        return 0.0

    # -- keys
    def _in(self, t, span):
        return span is None or span[0] - 1e-9 <= t <= span[1] + 1e-9

    def keyframe(self, curve=None, q=False, time=None, timeChange=False, valueChange=False,
                 breakdown=False, name=False, **kw):
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
        return None

    def setKeyframe(self, curve, time=(), value=0.0, breakdown=False, **kw):
        if curve not in self.curves:
            raise ValueError("No object matches name: %s" % curve)
        self.curves[curve][float(time[0])] = (float(value), bool(breakdown))

    def cutKey(self, curve, time=None, clear=False, **kw):
        keys = self.curves[curve]
        for t in [t for t in keys if self._in(t, time)]:
            del keys[t]
        if not keys:                                   # Maya: an emptied curve is deleted
            del self.curves[curve]
            self.deleted.append(curve)


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
