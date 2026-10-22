"""Render the hub's recorded interface sounds as pitch variants (2026-10-22).

The animator: «давай сделаем нашим звукам настройку в диапазоне 25 % питча что бы
они немного по разному звучали каждый раз». QSoundEffect cannot change pitch, so
each recording ships as maya_hubsound.VARIANTS files, <name>_<i>.wav, played back
`maya_hubsound.pitch(i)` times as fast (a tape: higher and a little shorter),
spread evenly over maya_hubsound.PITCH_SPREAD; maya_hubsound.play picks one at
random each time.

    mayapy make_ui_sound_variants.py <ffmpeg.exe>

Reads sources/sounds/<name>_*.mp3 (or .wav), writes SkeldarAnim/assets/sounds/<name>_<i>.wav
(44.1 kHz stereo 16-bit) at maya_hubsound.GAIN_DB[name].
"""

import glob
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
PLUGIN = os.path.join(REPO, "SkeldarAnim")
sys.path.insert(0, PLUGIN)

import maya_hubsound as sound                                # noqa: E402

RATE = 44100


def render(ffmpeg):
    out = os.path.join(PLUGIN, "assets", "sounds")
    for name in sound.RECORDED:
        found = [p for p in glob.glob(os.path.join(REPO, "sources", "sounds", name + "_*"))
                 if p.lower().endswith((".mp3", ".wav"))]
        if len(found) != 1:
            raise SystemExit("one source for %s, found %r" % (name, found))
        for stale in glob.glob(os.path.join(out, name + "*.wav")):
            os.remove(stale)
        for i in range(sound.VARIANTS):
            rate = sound.pitch(i)
            path = os.path.join(out, "%s_%d.wav" % (name, i))
            subprocess.check_call([
                ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", found[0],
                "-af", "volume=%.2fdB,asetrate=%d,aresample=%d"
                % (sound.GAIN_DB[name], int(round(RATE * rate)), RATE),
                "-ar", str(RATE), "-ac", "2", "-c:a", "pcm_s16le", path])
            print("%s x%.4f" % (path, rate))


if __name__ == "__main__":
    render(sys.argv[1])
