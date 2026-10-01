"""maya_hubsound - the SkeldarAnim hub's interface sounds.

2026-10-01, the animator: «давай для теста сделаем приятный звук когда
срабатывает выделение какого-то элемента ... я вожу мышкой по кнопочкам
нашего меню и вот тут давай сделаем приятный и простой звук наводки».
One sound for now, `hover`: the mouse entering a button, a dropdown or a
card header of the skinned hub (`maya_hubqt.sounding`), switched in the
hub's menu (⋮ → Interface sounds), off by default («Отключи воспроизведение
звуков по умолчанию», the same day).

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

#  partials: ((frequency Hz, relative level, decay time constant s), ...);
#  attack and fade are raised-cosine ramps (s); peak is the loudest sample
#  (1.0 = full scale).
Tone = collections.namedtuple("Tone", "partials attack length fade peak")

SOUNDS = {
    #  A short soft "glass tick": E6 and its octave at a fifth of the level,
    #  the octave dying first; −15 dBFS, heard rather than noticed.
    "hover": Tone(partials=((1318.51, 1.0, 0.016), (2637.02, 0.2, 0.007)),
                  attack=0.0015, length=0.080, fade=0.015, peak=0.178),
}

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
        for freq, level, decay in tone.partials:
            value += (level * math.exp(-t / decay)
                      * math.sin(2.0 * math.pi * freq * t))
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
    (2026-10-01, the same day: «Отключи воспроизведение звуков по
    умолчанию»)."""
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
        play("hover")
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


def _qt_pool(path):
    try:
        from PySide6 import QtCore, QtMultimedia
    except ImportError:
        from PySide2 import QtCore, QtMultimedia
    url = QtCore.QUrl.fromLocalFile(path)
    effects = []
    for _ in range(POOL):
        effect = QtMultimedia.QSoundEffect()
        effect.setSource(url)
        effect.setVolume(1.0)
        effects.append(effect)
    return EffectPool(effects)


def make_player(path):
    """A player of the WAV at `path`: a QSoundEffect pool, else winsound.
    Raises when neither can be made (a seam for the tests)."""
    try:
        return _qt_pool(path)
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
    return state


def reset():
    """Forget the players, the throttle and the switch (the tests)."""
    global _ENABLED
    _ENABLED = None
    if hasattr(sys, _STATE_ATTR):
        delattr(sys, _STATE_ATTR)


def _player(name):
    """The player of sound `name`, made once per file (an update that
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
        player = make_player(path)
    except Exception:                                        # noqa: BLE001
        player = None
    players[name] = (key, player)
    return player


def preload(name="hover"):
    """Make the player now, so the first hover is not the one that waits
    for the file to load. Answers whether there is one."""
    try:
        return _player(name) is not None
    except Exception:                                        # noqa: BLE001
        return False


def play(name, now=None):
    """Play sound `name` unless the sounds are off, the last sound was less
    than MIN_GAP ago, or there is nothing to play it with. Never raises;
    answers whether it played."""
    try:
        if not enabled():
            return False
        state = _state()
        now = time.monotonic() if now is None else now
        if now - state["last"] < MIN_GAP:
            return False
        player = _player(name)
        if player is None:
            return False
        player.play()
        state["last"] = now
        return True
    except Exception:                                        # noqa: BLE001
        return False
