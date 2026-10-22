"""maya_hubsound - the SkeldarAnim hub's interface sounds.

2026-10-01, the animator: «давай для теста сделаем приятный звук когда
срабатывает выделение какого-то элемента ... я вожу мышкой по кнопочкам
нашего меню и вот тут давай сделаем приятный и простой звук наводки».
The hover tick went on 2026-10-22 («уберем звуки интерфейса которы есть
сейчас и вставим те которые я кину»): the animator's own recordings now,
`RECORDED` - `drag` (a whoosh) when any drag of ours lifts its ghost
(`maya_hubqt.ghost_class`), `delete` (a fireball whoosh) on any deletion
(keys, layers, characters, cards, Stash / Shared files, chat messages,
Maya's Delete). Each recording ships as VARIANTS pitch variants spread over
PITCH_SPREAD (25 %), one picked at random each play, so a repeated sound is
never quite the same. Switched in the hub's menu (⋮ → Interface sounds), OFF
by default («пусть звуки по умолчанию будут отключены», the same day). `message` (the chat) is still synthesised.

    synth / wav_bytes   the sound as numbers, then as a WAV (pure)
    write               the shipped file, assets/sounds/<name>.wav
                        (docs/superpowers/plans/make_hub_sounds.py; a test
                        pins the file to the synthesis)
    play                QtMultimedia's QSoundEffect, else winsound, else
                        nothing -- never raises, answers whether it played

The players live on `sys` (trap 111): an install purges our modules while
Maya runs, and a fresh module object must find the players (and the
throttle) already there rather than open three more.

Stdlib at import: Qt, winsound and maya.cmds are imported inside the calls.

Spec: docs/superpowers/specs/2026-10-01-hub-hover-sound-design.md
"""

import collections
import io
import math
import os
import struct
import sys
import time
import wave

RATE = 48000

#  partials: ((frequency Hz, relative level, decay time constant s[, onset s[, length s]]), ...);
#  a partial with an onset is silent before it and rings from it (a chime's second note);
#  attack and fade are raised-cosine ramps (s); peak is the loudest sample
#  (1.0 = full scale).
Tone = collections.namedtuple("Tone", "partials attack length fade peak")

SOUNDS = {
    #  A chat message (2026-10-20): «в духе ICQ» - its «о-оу», not its recording (that one is
    #  ICQ's, and this repository is public): two short sung syllables falling a fourth,
    #  G4 for 110 ms then D4 for 220 ms after a 40 ms breath, each a voice-like stack of
    #  harmonics weighted toward an «у» and then an «о»; −12 dBFS.
    "message": Tone(partials=(
        (392.00, 1.00, 0.40, 0.00, 0.11), (784.00, 0.55, 0.30, 0.00, 0.11),
        (1176.0, 0.22, 0.20, 0.00, 0.11), (1568.0, 0.08, 0.15, 0.00, 0.11),
        (293.66, 1.00, 0.45, 0.15, 0.22), (587.33, 0.75, 0.35, 0.15, 0.22),
        (880.99, 0.40, 0.25, 0.15, 0.22), (1174.7, 0.12, 0.18, 0.15, 0.22)),
        attack=0.012, length=0.44, fade=0.04, peak=0.25),
}

#  The animator's recordings (2026-10-22): their mp3s in sources/sounds/, shipped as
#  assets/sounds/<name>_<i>.wav, written by docs/superpowers/plans/make_ui_sound_variants.py
#  (ffmpeg, 44.1 kHz) at GAIN_DB - the whoosh 30 % quieter than the fireball's -6 dB
#  («сделаем его на 30% тише»: x0.7 is -3.1 dB more).
RECORDED = ("drag", "delete")
GAIN_DB = {"drag": -9.1, "delete": -6.0}

#  Each recording as VARIANTS files played PITCH_SPREAD apart from the lowest to the
#  highest («в диапазоне 25 % питча»): x0.875 .. x1.125, evenly, the middle one x1.
VARIANTS = 7
PITCH_SPREAD = 0.25

#  a partial with a length ends there over this release (s)
RELEASE = 0.025

OPTIONVAR = "skeldarAnimHub_sounds"

#  No new sound this soon after the last one: a sweep across a row of
#  buttons enters one every 15-30 ms.
MIN_GAP = 0.035

#  QSoundEffects per sound, used in turn: a play on an effect still
#  playing restarts it, and the tail cut off clicks.
POOL = 3

_STATE_ATTR = "_skeldar_hubsound"


# ----------------------------------------------------------------- the sound

def synth(tone, rate=RATE):
    """The samples of `tone` (floats in -1..1), its loudest at tone.peak,
    the first and the last exactly 0."""
    n = int(round(tone.length * rate))
    attack = max(1, int(round(tone.attack * rate)))
    fade = max(1, int(round(tone.fade * rate)))
    raw = []
    for i in range(n):
        t = i / float(rate)
        value = 0.0
        for partial in tone.partials:
            freq, level, decay = partial[:3]
            onset = partial[3] if len(partial) > 3 else 0.0
            u = t - onset
            if u < 0:
                continue
            #  a note starting late gets the same raised-cosine attack, so it does not click
            ramp = 1.0 if onset <= 0 or u >= tone.attack else (
                0.5 - 0.5 * math.cos(math.pi * u / tone.attack))
            if len(partial) > 4:
                if u >= partial[4] + RELEASE:
                    continue
                if u > partial[4]:
                    ramp *= 0.5 + 0.5 * math.cos(math.pi * (u - partial[4]) / RELEASE)
            value += (ramp * level * math.exp(-u / decay)
                      * math.sin(2.0 * math.pi * freq * u))
        if i < attack:
            value *= 0.5 - 0.5 * math.cos(math.pi * i / attack)
        tail = n - 1 - i
        if tail < fade:
            value *= 0.5 - 0.5 * math.cos(math.pi * tail / fade)
        raw.append(value)
    top = max(abs(v) for v in raw) or 1.0
    return [v * tone.peak / top for v in raw]


def wav_bytes(samples, rate=RATE):
    """A mono 16-bit WAV of `samples`, clipped at full scale."""
    frames = b"".join(
        struct.pack("<h", max(-32767, min(32767, int(round(v * 32767)))))
        for v in samples)
    buf = io.BytesIO()
    out = wave.open(buf, "wb")
    try:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes(frames)
    finally:
        out.close()
    return buf.getvalue()


def pitch(i):
    """How fast variant `i` plays its recording (1.0 = as recorded)."""
    if VARIANTS < 2:
        return 1.0
    return 1.0 - PITCH_SPREAD / 2.0 + PITCH_SPREAD * i / float(VARIANTS - 1)


def variant_name(name, i):
    """The file stem of variant `i` of recording `name`: drag_3."""
    return "%s_%d" % (name, i)


def pick(last, count=VARIANTS, rand=None):
    """A variant at random, never the one played last (a replay of an effect still
    playing restarts it, and the cut tail clicks)."""
    import random
    rand = rand or random.random
    if count < 2:
        return 0
    i = int(rand() * (count - 1)) % (count - 1)
    return i + 1 if last is not None and i >= last else i


def plugin_root():
    return os.path.dirname(os.path.abspath(__file__))


def sound_path(name):
    """Where sound `name` ships: <plugin>/assets/sounds/<name>.wav."""
    return os.path.join(plugin_root(), "assets", "sounds", name + ".wav")


def write(name, path=None):
    """Write sound `name` (default: where it ships). Answers the path."""
    path = path or sound_path(name)
    folder = os.path.dirname(path)
    if folder and not os.path.isdir(folder):
        os.makedirs(folder)
    with open(path, "wb") as f:
        f.write(wav_bytes(synth(SOUNDS[name])))
    return path


# ---------------------------------------------------------------- the switch

#  Read once per module object (None: not yet); set_enabled keeps it.
_ENABLED = None


def _cmds():
    """maya.cmds, or None outside Maya (a seam for the tests)."""
    try:
        import maya.cmds as cmds
        return cmds
    except Exception:                                        # noqa: BLE001
        return None


def enabled():
    """Whether the interface sounds are on (the menu row). OFF by default
    (2026-10-01, and again 2026-10-22 with the animator's own drag and
    delete sounds: «пусть звуки по умолчанию будут отключены»)."""
    global _ENABLED
    if _ENABLED is None:
        _ENABLED = False
        cmds = _cmds()
        try:
            if cmds is not None and cmds.optionVar(exists=OPTIONVAR):
                _ENABLED = bool(cmds.optionVar(query=OPTIONVAR))
        except Exception:                                    # noqa: BLE001
            pass
    return _ENABLED


def set_enabled(on):
    """Switch the sounds, remembered; turning them on plays one, so the
    animator hears what they turned on. Answers the new state."""
    global _ENABLED
    _ENABLED = bool(on)
    cmds = _cmds()
    try:
        if cmds is not None:
            cmds.optionVar(intValue=(OPTIONVAR, int(_ENABLED)))
    except Exception:                                        # noqa: BLE001
        pass
    if _ENABLED:
        play("drag")
    return _ENABLED


# ---------------------------------------------------------------- the player

class EffectPool(object):
    """Effects of one sound, played in turn."""

    def __init__(self, effects):
        self.effects = list(effects)
        self.turn = 0

    def play(self):
        effect = self.effects[self.turn % len(self.effects)]
        self.turn += 1
        effect.play()


class WinsoundPlayer(object):
    """Where QtMultimedia is missing: the file through winsound, async (one
    at a time - a new sound replaces the one playing)."""

    def __init__(self, path):
        import winsound
        self._winsound = winsound
        self.path = path

    def play(self):
        w = self._winsound
        w.PlaySound(self.path, w.SND_FILENAME | w.SND_ASYNC | w.SND_NODEFAULT)


def _qt_pool(path, count=POOL):
    try:
        from PySide6 import QtCore, QtMultimedia
    except ImportError:
        from PySide2 import QtCore, QtMultimedia
    url = QtCore.QUrl.fromLocalFile(path)
    effects = []
    for _ in range(count):
        effect = QtMultimedia.QSoundEffect()
        effect.setSource(url)
        effect.setVolume(1.0)
        effects.append(effect)
    return EffectPool(effects)


def make_player(path, count=POOL):
    """A player of the WAV at `path`: a pool of `count` QSoundEffects, else
    winsound. Raises when neither can be made (a seam for the tests)."""
    try:
        return _qt_pool(path, count)
    except Exception:                                        # noqa: BLE001
        return WinsoundPlayer(path)


def _state():
    """The players and the throttle, kept on `sys` across a purge. Fields
    are set by THIS module's list (trap 139): a state an older build made
    may lack one."""
    state = getattr(sys, _STATE_ATTR, None)
    if not isinstance(state, dict):
        state = {}
        setattr(sys, _STATE_ATTR, state)
    state.setdefault("players", {})
    state.setdefault("last", float("-inf"))
    state.setdefault("variant", {})
    return state


def reset():
    """Forget the players, the throttle and the switch (the tests)."""
    global _ENABLED
    _ENABLED = None
    if hasattr(sys, _STATE_ATTR):
        delattr(sys, _STATE_ATTR)


def _player(name, count=POOL):
    """The player of sound file `name`, made once per file (an update that
    replaces the file gets a new one), or None without the file or a
    backend."""
    path = sound_path(name)
    try:
        info = os.stat(path)
    except OSError:
        return None
    key = (path, info.st_size, info.st_mtime)
    players = _state()["players"]
    held = players.get(name)
    if held is not None and held[0] == key:
        return held[1]
    try:
        #  the pool size only when it is not the default: a player seam that takes
        #  just the path (an older test's, a caller's) still makes the one-file sounds
        player = make_player(path) if count == POOL else make_player(path, count)
    except Exception:                                        # noqa: BLE001
        player = None
    players[name] = (key, player)
    return player


def _files(name):
    """The files sound `name` plays from: its variants, or its one file."""
    if name in RECORDED:
        return [variant_name(name, i) for i in range(VARIANTS)]
    return [name]


def preload(name="drag"):
    """Make the players now, so the first drag is not the one that waits
    for the file to load. Answers whether there is one."""
    try:
        if name in RECORDED:
            return all(_player(f, 1) is not None for f in _files(name))
        return _player(name) is not None
    except Exception:                                        # noqa: BLE001
        return False


def play(name, now=None, force=False):
    """Play sound `name` unless the sounds are off, the last sound was less
    than MIN_GAP ago, or there is nothing to play it with. `force` plays it
    whatever the interface-sounds switch says (a chat message: its own
    setting decides). Never raises; answers whether it played."""
    try:
        if not force and not enabled():
            return False
        state = _state()
        now = time.monotonic() if now is None else now
        if now - state["last"] < MIN_GAP:
            return False
        if name in RECORDED:
            #  a variant at random, one effect each: no two in a row are the same
            i = pick(state["variant"].get(name))
            player = _player(variant_name(name, i), 1)
            state["variant"][name] = i
        else:
            player = _player(name)
        if player is None:
            return False
        player.play()
        state["last"] = now
        return True
    except Exception:                                        # noqa: BLE001
        return False


def dragged():
    """A drag of ours lifted its ghost: the whoosh."""
    return play("drag")


def deleted():
    """Something was deleted: the fireball."""
    return play("delete")
