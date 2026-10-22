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

    def __init__(self, path, count=3, fail=False):
        self.path, self.count = path, count
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


class Recorded(unittest.TestCase):
    """2026-10-22: the hover tick is gone, the animator's own recordings ship."""

    def test_no_hover_sound_is_left(self):
        self.assertNotIn("hover", sound.SOUNDS)
        self.assertFalse(os.path.exists(os.path.join(_PLUGIN, "assets", "sounds",
                                                     "hover.wav")))

    def test_each_recording_ships_as_sixteen_bit_pitch_variants(self):
        """The window-open lid went the same day; the whoosh and the fireball
        ship as VARIANTS files each, a higher variant a shorter one."""
        self.assertEqual(sound.RECORDED, ("drag", "delete"))
        self.assertFalse(os.path.exists(os.path.join(_PLUGIN, "assets", "sounds",
                                                     "open.wav")))
        for name in sound.RECORDED:
            lengths = []
            for i in range(sound.VARIANTS):
                with open(sound.sound_path(sound.variant_name(name, i)), "rb") as f:
                    params, values = _decoded(f.read())
                self.assertEqual(params[1:], (2, 44100), name)
                lengths.append(len(values))
            self.assertEqual(lengths, sorted(lengths, reverse=True), name)

    def test_the_whoosh_is_thirty_percent_quieter_than_it_was(self):
        """-6 dB was the first build's; x0.7 more is -3.1 dB."""
        self.assertAlmostEqual(sound.GAIN_DB["drag"], -6.0 + 20 * __import__("math").log10(0.7),
                               places=1)


class Variants(SoundMixin, unittest.TestCase):
    """2026-10-22: «настройку в диапазоне 25 % питча что бы они немного по
    разному звучали каждый раз»."""

    def setUp(self):
        SoundMixin.setUp(self)
        self.cmds.optionvars[sound.OPTIONVAR] = 1           # switched on

    def test_the_variants_span_twenty_five_percent_about_the_recording(self):
        rates = [sound.pitch(i) for i in range(sound.VARIANTS)]
        self.assertAlmostEqual(rates[-1] - rates[0], 0.25)
        self.assertAlmostEqual(rates[sound.VARIANTS // 2], 1.0)
        self.assertEqual(sound.PITCH_SPREAD, 0.25)

    def test_a_pick_is_never_the_last_one_and_reaches_every_other(self):
        for last in range(sound.VARIANTS):
            seen = set()
            for k in range(1000):
                i = sound.pick(last, rand=lambda: k / 1000.0)
                self.assertNotEqual(i, last)
                seen.add(i)
            self.assertEqual(seen, set(range(sound.VARIANTS)) - {last})

    def test_each_play_plays_a_variant_file_one_effect_each(self):
        heard = []
        for k in range(12):
            self.assertTrue(sound.play("delete", now=10.0 + k))
            heard.append(sound._state()["variant"]["delete"])
        self.assertTrue(all(a != b for a, b in zip(heard, heard[1:])))
        for player in FakePlayer.made:
            self.assertEqual(player.count, 1)
            self.assertRegex(os.path.basename(player.path), r"^delete_[0-6]\.wav$")

    def test_preload_makes_every_variant(self):
        self.assertTrue(sound.preload("drag"))
        self.assertEqual(len(FakePlayer.made), sound.VARIANTS)


class WavFile(unittest.TestCase):

    def test_mono_sixteen_bit_at_the_rate(self):
        data = sound.wav_bytes(sound.synth(sound.SOUNDS["ring"]))
        params, values = _decoded(data)
        self.assertEqual(params, (1, 2, 48000))
        self.assertEqual(len(values), int(round(1.6 * 48000)))
        self.assertEqual(max(abs(v) for v in values),
                         int(round(0.25 * 32767)))

    def test_a_sample_past_full_scale_is_clipped_not_wrapped(self):
        params, values = _decoded(sound.wav_bytes([1.5, -1.5, 0.5]))
        self.assertEqual(values, (32767, -32767, 16384))

    def test_write_puts_the_file_where_asked(self):
        folder = tempfile.mkdtemp()
        path = sound.write("ring", os.path.join(folder, "x", "ring.wav"))
        with open(path, "rb") as f:
            self.assertEqual(f.read(),
                             sound.wav_bytes(sound.synth(sound.SOUNDS["ring"])))

    def test_the_shipped_file_is_the_synthesis(self):
        """make_hub_sounds.py wrote it; regenerate after changing a Tone. One
        LSB of slack for a libm that rounds a sine differently."""
        path = sound.sound_path("ring")
        self.assertEqual(path, os.path.join(_PLUGIN, "assets", "sounds", "ring.wav"))
        with open(path, "rb") as f:
            shipped = _decoded(f.read())
        made = _decoded(sound.wav_bytes(sound.synth(sound.SOUNDS["ring"])))
        self.assertEqual(shipped[0], made[0])
        self.assertEqual(len(shipped[1]), len(made[1]))
        self.assertLessEqual(max(abs(a - b) for a, b in
                                 zip(shipped[1], made[1])), 1)

    def test_the_message_is_the_animator_s_recording(self):
        """make_ui_sound_variants.py wrote it from sources/sounds/message_*.mp3."""
        self.assertNotIn("message", sound.SOUNDS)
        self.assertIn("message", sound.CLIPS)
        with wave.open(sound.sound_path("message"), "rb") as w:
            self.assertEqual((w.getnchannels(), w.getsampwidth(), w.getframerate()),
                             (2, 2, 44100))
            self.assertGreater(w.getnframes() / 44100.0, 3.0)

    def test_every_sound_ships(self):
        for name in sound.SOUNDS:
            self.assertTrue(os.path.isfile(sound.sound_path(name)), name)


class Switch(SoundMixin, unittest.TestCase):

    def test_off_by_default(self):
        """2026-10-22: «пусть звуки по умолчанию будут отключены» - ⋮ →
        Interface sounds turns them on."""
        self.assertFalse(sound.enabled())
        self.assertFalse(sound.play("drag", now=1.0))
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
        self.assertTrue(sound.play("message", now=10.0))
        self.assertEqual(len(FakePlayer.made), 1)
        self.assertEqual(FakePlayer.made[0].path, sound.sound_path("message"))
        self.assertEqual(FakePlayer.made[0].plays, 1)

    def test_disabled_is_silent(self):
        sound.set_enabled(False)
        self.assertFalse(sound.play("message", now=10.0))
        self.assertEqual(FakePlayer.made, [])

    def test_a_sweep_is_throttled(self):
        self.assertTrue(sound.play("message", now=10.000))
        self.assertFalse(sound.play("message", now=10.010))
        self.assertTrue(sound.play("message", now=10.010 + sound.MIN_GAP))
        self.assertEqual(sound.MIN_GAP, 0.035)
        self.assertEqual(FakePlayer.made[0].plays, 2)

    def test_one_player_per_sound(self):
        sound.play("message", now=1.0)
        sound.play("message", now=2.0)
        self.assertEqual(len(FakePlayer.made), 1)

    def test_a_missing_file_is_silent_and_makes_no_player(self):
        self.assertFalse(sound.play("nothing", now=1.0))
        self.assertEqual(FakePlayer.made, [])

    def test_a_player_that_raises_is_silent(self):
        sound.make_player = lambda path, count=3: FakePlayer(path, fail=True)
        self.assertFalse(sound.play("message", now=1.0))

    def test_a_player_that_cannot_be_made_is_silent(self):
        def broken(path, count=3):
            raise ImportError("no QtMultimedia")
        sound.make_player = broken
        self.assertFalse(sound.play("message", now=1.0))
        self.assertFalse(sound.preload("message"))

    def test_preload_makes_the_player_without_a_sound(self):
        self.assertTrue(sound.preload("message"))
        self.assertEqual(len(FakePlayer.made), 1)
        self.assertEqual(FakePlayer.made[0].plays, 0)

    def test_the_players_outlive_a_purge(self):
        """An install purges our modules (trap 111): a fresh module object
        finds the players already made, and the throttle with them."""
        sound.play("message", now=5.0)
        del sys.modules["maya_hubsound"]
        try:
            fresh = importlib.import_module("maya_hubsound")
            self.assertIsNot(fresh, sound)
            fresh.make_player = FakePlayer
            fresh._cmds = lambda: self.cmds
            self.assertFalse(fresh.play("message", now=5.01))     # throttled
            self.assertTrue(fresh.play("message", now=6.0))
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
