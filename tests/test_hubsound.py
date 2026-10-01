"""maya_hubsound: the hub's interface sounds - the synthesis, the shipped
file, the switch and the player, with the audio backend replaced.

Spec: docs/superpowers/specs/2026-10-01-hub-hover-sound-design.md
"""

import importlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
import wave

import maya_hubsound as sound

_PLUGIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(
    __file__))), "SkeldarAnim")


class FakeCmds(object):

    def __init__(self):
        self.optionvars = {}

    def optionVar(self, exists=None, query=None, intValue=None):  # noqa: N802
        if exists is not None:
            return exists in self.optionvars
        if query is not None:
            return self.optionvars[query]
        name, value = intValue
        self.optionvars[name] = value
        return None


class FakePlayer(object):

    made = []

    def __init__(self, path, fail=False):
        self.path = path
        self.fail = fail
        self.plays = 0
        FakePlayer.made.append(self)

    def play(self):
        if self.fail:
            raise RuntimeError("no audio device")
        self.plays += 1


class SoundMixin(object):

    def setUp(self):
        self.saved = (sound._cmds, sound.make_player)
        self.cmds = FakeCmds()
        sound._cmds = lambda: self.cmds
        FakePlayer.made = []
        sound.make_player = FakePlayer
        sound.reset()

    def tearDown(self):
        sound._cmds, sound.make_player = self.saved
        sound.reset()


def _decoded(data):
    w = wave.open(io.BytesIO(data), "rb")
    try:
        params = (w.getnchannels(), w.getsampwidth(), w.getframerate())
        raw = w.readframes(w.getnframes())
    finally:
        w.close()
    import struct
    values = struct.unpack("<%dh" % (len(raw) // 2), raw)
    return params, values


class Synthesis(unittest.TestCase):

    def setUp(self):
        self.tone = sound.SOUNDS["hover"]
        self.samples = sound.synth(self.tone)

    def test_eighty_milliseconds_at_the_rate(self):
        self.assertEqual(len(self.samples), int(round(0.080 * sound.RATE)))
        self.assertEqual(sound.RATE, 48000)

    def test_the_peak_is_minus_fifteen_dbfs(self):
        self.assertAlmostEqual(max(abs(v) for v in self.samples), 0.178,
                               places=9)

    def test_it_starts_and_ends_on_zero(self):
        """No click at either end: a raised-cosine attack and fade."""
        self.assertEqual(self.samples[0], 0.0)
        self.assertEqual(self.samples[-1], 0.0)
        self.assertLess(abs(self.samples[1]), 0.01)
        self.assertLess(abs(self.samples[-2]), 1e-4)

    def test_no_dc(self):
        mean = sum(self.samples) / len(self.samples)
        self.assertLess(abs(mean), 1e-3)

    def test_it_rings_at_e6(self):
        """Zero crossings over the first 20 ms, where the fundamental
        dominates its octave: two a period."""
        n = int(0.020 * sound.RATE)
        part = self.samples[1:n]
        crossings = sum(1 for a, b in zip(part, part[1:]) if a * b < 0)
        freq = crossings / 2.0 / (len(part) / float(sound.RATE))
        self.assertAlmostEqual(freq, 1318.5, delta=60)

    def test_it_dies_away(self):
        """The last 40 ms hold less than a tenth of the peak."""
        tail = self.samples[int(0.040 * sound.RATE):]
        self.assertLess(max(abs(v) for v in tail), 0.1 * 0.178)


class WavFile(unittest.TestCase):

    def test_mono_sixteen_bit_at_the_rate(self):
        data = sound.wav_bytes(sound.synth(sound.SOUNDS["hover"]))
        params, values = _decoded(data)
        self.assertEqual(params, (1, 2, 48000))
        self.assertEqual(len(values), 3840)
        self.assertEqual(max(abs(v) for v in values),
                         int(round(0.178 * 32767)))

    def test_a_sample_past_full_scale_is_clipped_not_wrapped(self):
        params, values = _decoded(sound.wav_bytes([1.5, -1.5, 0.5]))
        self.assertEqual(values, (32767, -32767, 16384))

    def test_write_puts_the_file_where_asked(self):
        folder = tempfile.mkdtemp()
        path = sound.write("hover", os.path.join(folder, "x", "hover.wav"))
        with open(path, "rb") as f:
            self.assertEqual(f.read(),
                             sound.wav_bytes(sound.synth(sound.SOUNDS["hover"])))

    def test_the_shipped_file_is_the_synthesis(self):
        """make_hub_sounds.py wrote it; regenerate after changing a Tone. One
        LSB of slack for a libm that rounds a sine differently."""
        path = sound.sound_path("hover")
        self.assertEqual(path, os.path.join(_PLUGIN, "assets", "sounds",
                                            "hover.wav"))
        with open(path, "rb") as f:
            shipped = _decoded(f.read())
        made = _decoded(sound.wav_bytes(sound.synth(sound.SOUNDS["hover"])))
        self.assertEqual(shipped[0], made[0])
        self.assertEqual(len(shipped[1]), len(made[1]))
        self.assertLessEqual(max(abs(a - b) for a, b in
                                 zip(shipped[1], made[1])), 1)

    def test_every_sound_ships(self):
        for name in sound.SOUNDS:
            self.assertTrue(os.path.isfile(sound.sound_path(name)), name)


class Switch(SoundMixin, unittest.TestCase):

    def test_off_by_default(self):
        """2026-10-01, the animator: «Отключи воспроизведение звуков по
        умолчанию» - ⋮ → Interface sounds turns them on."""
        self.assertFalse(sound.enabled())
        self.assertFalse(sound.play("hover", now=1.0))
        self.assertEqual(FakePlayer.made, [])

    def test_on_is_remembered(self):
        self.assertTrue(sound.set_enabled(True))
        self.assertEqual(self.cmds.optionvars[sound.OPTIONVAR], 1)
        sound.reset()                          # a fresh module reads it back
        self.assertTrue(sound.enabled())

    def test_off_is_remembered(self):
        sound.set_enabled(True)
        self.assertFalse(sound.set_enabled(False))
        self.assertEqual(self.cmds.optionvars[sound.OPTIONVAR], 0)
        self.assertFalse(sound.enabled())
        sound.reset()
        self.assertFalse(sound.enabled())

    def test_turning_it_on_plays_it_once(self):
        """The animator hears what they turned on."""
        sound.set_enabled(False)
        self.assertEqual(FakePlayer.made, [])
        self.assertTrue(sound.set_enabled(True))
        self.assertEqual(self.cmds.optionvars[sound.OPTIONVAR], 1)
        self.assertEqual(sum(p.plays for p in FakePlayer.made), 1)

    def test_without_maya_it_is_off_and_says_nothing(self):
        sound._cmds = lambda: None
        sound.reset()
        self.assertFalse(sound.enabled())
        sound.make_player = FakePlayer
        self.assertTrue(sound.set_enabled(True))
        self.assertTrue(sound.enabled())


class Play(SoundMixin, unittest.TestCase):
    """With the sounds switched on (⋮ → Interface sounds)."""

    def setUp(self):
        SoundMixin.setUp(self)
        self.cmds.optionvars[sound.OPTIONVAR] = 1

    def test_it_plays_the_shipped_file(self):
        self.assertTrue(sound.play("hover", now=10.0))
        self.assertEqual(len(FakePlayer.made), 1)
        self.assertEqual(FakePlayer.made[0].path, sound.sound_path("hover"))
        self.assertEqual(FakePlayer.made[0].plays, 1)

    def test_disabled_is_silent(self):
        sound.set_enabled(False)
        self.assertFalse(sound.play("hover", now=10.0))
        self.assertEqual(FakePlayer.made, [])

    def test_a_sweep_is_throttled(self):
        self.assertTrue(sound.play("hover", now=10.000))
        self.assertFalse(sound.play("hover", now=10.010))
        self.assertTrue(sound.play("hover", now=10.010 + sound.MIN_GAP))
        self.assertEqual(sound.MIN_GAP, 0.035)
        self.assertEqual(FakePlayer.made[0].plays, 2)

    def test_one_player_per_sound(self):
        sound.play("hover", now=1.0)
        sound.play("hover", now=2.0)
        self.assertEqual(len(FakePlayer.made), 1)

    def test_a_missing_file_is_silent_and_makes_no_player(self):
        self.assertFalse(sound.play("nothing", now=1.0))
        self.assertEqual(FakePlayer.made, [])

    def test_a_player_that_raises_is_silent(self):
        sound.make_player = lambda path: FakePlayer(path, fail=True)
        self.assertFalse(sound.play("hover", now=1.0))

    def test_a_player_that_cannot_be_made_is_silent(self):
        def broken(path):
            raise ImportError("no QtMultimedia")
        sound.make_player = broken
        self.assertFalse(sound.play("hover", now=1.0))
        self.assertFalse(sound.preload("hover"))

    def test_preload_makes_the_player_without_a_sound(self):
        self.assertTrue(sound.preload("hover"))
        self.assertEqual(len(FakePlayer.made), 1)
        self.assertEqual(FakePlayer.made[0].plays, 0)

    def test_the_players_outlive_a_purge(self):
        """An install purges our modules (trap 111): a fresh module object
        finds the players already made, and the throttle with them."""
        sound.play("hover", now=5.0)
        del sys.modules["maya_hubsound"]
        try:
            fresh = importlib.import_module("maya_hubsound")
            self.assertIsNot(fresh, sound)
            fresh.make_player = FakePlayer
            fresh._cmds = lambda: self.cmds
            self.assertFalse(fresh.play("hover", now=5.01))     # throttled
            self.assertTrue(fresh.play("hover", now=6.0))
            self.assertEqual(len(FakePlayer.made), 1)
            self.assertEqual(FakePlayer.made[0].plays, 2)
        finally:
            sys.modules["maya_hubsound"] = sound


class Pool(unittest.TestCase):

    def test_the_effects_are_used_in_turn(self):
        played = []

        class Effect(object):
            def __init__(self, i):
                self.i = i

            def play(self):
                played.append(self.i)

        pool = sound.EffectPool([Effect(i) for i in range(sound.POOL)])
        for _ in range(4):
            pool.play()
        self.assertEqual(played, [0, 1, 2, 0])
        self.assertEqual(sound.POOL, 3)


class StdlibOnly(unittest.TestCase):

    def test_imports_nothing_of_maya_or_qt(self):
        code = ("import sys; import maya_hubsound; "
                "bad = [m for m in sys.modules if m.split('.')[0] in "
                "('maya', 'PySide6', 'PySide2', 'shiboken6', 'winsound')]; "
                "print(','.join(bad))")
        out = subprocess.run([sys.executable, "-c", code], cwd=_PLUGIN,
                             capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()
