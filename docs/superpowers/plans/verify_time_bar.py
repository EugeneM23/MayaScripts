"""The Time Bar's Maya side, standalone (2026-10-16): every command the strip sends,
on a keyed cube in mayapy - keys and breakdowns read, keys moved and scaled with
one undo each, the highlight, bookmarks, a sound's waveform, character sets,
loop / speed / cache, the key menu. The strip itself (Qt) is tests/test_timebar_bar.py;
the docking and the look in a GUI Maya are the animator's.

    mayapy docs/superpowers/plans/verify_time_bar.py
"""
import math
import os
import struct
import sys
import tempfile
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(HERE))), "SkeldarAnim"))

import maya.standalone                                       # noqa: E402
maya.standalone.initialize()
import maya.cmds as cmds                                     # noqa: E402

from maya_timebar import look, scene                         # noqa: E402

FAILED = []


def gate(name, ok, detail=""):
    print("%s  %s%s" % ("PASS" if ok else "FAIL", name, ("  - " + detail) if detail else ""))
    if not ok:
        FAILED.append(name)


def times(node, attr="tx"):
    return cmds.keyframe(node + "." + attr, q=True, timeChange=True) or []


cmds.file(new=True, force=True)
cmds.playbackOptions(edit=True, animationStartTime=0, animationEndTime=100, minTime=0, maxTime=60)
cube = cmds.polyCube(name="tbCube")[0]
for t, v in ((0, 0), (10, 5), (20, 10), (30, 0), (40, 3)):
    cmds.setKeyframe(cube, attribute="tx", time=t, value=v)
cmds.setKeyframe(cube, attribute="ty", time=15, value=2, breakdown=True)
cmds.select(cube)

# 1 reads
keys, bds = scene.keys()
gate("keys and breakdowns read apart", keys == [0, 10, 20, 30, 40] and bds == [15], "%s %s" % (keys, bds))
light = scene.light()
gate("ranges read", (light["a0"], light["a1"], light["p0"], light["p1"]) == (0, 100, 0, 60))
gate("the extra row reads", set(scene.extra()) == {"loop", "speed", "cache", "sound", "sound_shown", "character"})

# 2 the highlight
scene.set_highlight((12, 30))
gate("a highlight round-trips", scene.read_highlight() == (12, 30), str(scene.read_highlight()))
scene.set_highlight((25, 25))
gate("a one-frame highlight", scene.read_highlight() == (25, 25))
scene.set_highlight(None)
gate("cleared", scene.read_highlight() is None)

# 3 move keys, one undo
scene.move_keys((10, 20), (15, 25))
gate("a move shifts the keys inside", times(cube) == [0, 15, 25, 30, 40], str(times(cube)))
cmds.undo()
gate("one undo puts them back", times(cube) == [0, 10, 20, 30, 40], str(times(cube)))

# 4 scale toward the other edge, on whole frames, one undo
scene.move_keys((10, 30), (10, 50))
gate("a scale stretches toward the far edge", times(cube) == [0, 10, 30, 40, 50], str(times(cube)))
gate("all on whole frames", all(abs(t - round(t)) < 1e-6 for t in times(cube)))
cmds.undo()
gate("one undo", times(cube) == [0, 10, 20, 30, 40], str(times(cube)))

# 5 a single key moved
scene.move_keys((30, 30), (33, 33))
gate("one key moved", times(cube) == [0, 10, 20, 33, 40], str(times(cube)))
cmds.undo()

# 6 the key menu
scene.set_time(10)
scene.copy_keys(None, 10)
scene.paste_keys(None, 50)
gate("copy / paste a frame", 50 in times(cube), str(times(cube)))
scene.delete_keys(None, 50)
gate("delete a frame", 50 not in times(cube), str(times(cube)))
scene.tangents((0, 40), 0, "linear")
gate("tangents over the highlight",
     set(cmds.keyTangent(cube + ".tx", q=True, outTangentType=True)) == {"linear"})
scene.tangents(None, 20, "step")
gate("stepped", cmds.keyTangent(cube + ".tx", q=True, time=(20, 20), outTangentType=True) == ["step"])
cmds.keyframe(cube + ".tx", edit=True, time=(40, 40), timeChange=40.4, absolute=True)
scene.snap_keys((0, 60), 0)
gate("snap", 40 in times(cube), str(times(cube)))
scene.breakdown(None, 20)
gate("breakdown at a key", 20 in (cmds.keyframe(cube, q=True, breakdown=True) or []))
scene.set_time(5)
scene.set_key()
gate("set key", 5 in times(cube), str(times(cube)))
scene.cut_keys((4, 6), 0)
gate("cut", 5 not in times(cube))
scene.playback_from((12, 30))
gate("playback range = highlight", scene.ranges()[2:] == (12, 30))
scene.set_ranges(0, 100, 0, 60)

# 7 time
scene.scrub_only(17)
gate("time moved without an update", scene.now() == 17)
scene.set_time(10)
gate("step to the next key", scene.step_key(True, [0, 10, 20]) and scene.now() == 20)

# 8 loop, speed, cache
gate("the loop cycles", scene.cycle_loop() == "once" and scene.cycle_loop() == "oscillate"
     and scene.cycle_loop() == "continuous")
scene.set_speed(0.0)
gate("speed: every frame", scene.extra()["speed"] == 0.0)
scene.set_speed(1.0)
before = scene.cache_on()
scene.toggle_cache()
gate("cached playback toggles", scene.cache_on() != before)
scene.toggle_cache()

# 9 bookmarks
mark = scene.add_bookmark((10, 25))
gate("a bookmark over the highlight", scene.bookmarks() and scene.bookmarks()[0][:2] == (10, 25),
     str(scene.bookmarks()))
scene.add_bookmark((40, 50))
scene.set_time(0)
gate("next bookmark", scene.step_bookmark(True) and scene.now() == 10)
gate("and the next", scene.step_bookmark(True) and scene.now() == 40)

# 10 sound: a 2 s wav at 30 fps, a click at 1 s
path = os.path.join(tempfile.mkdtemp(), "click.wav")
rate = 8000
with wave.open(path, "wb") as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(rate)
    frames = []
    for i in range(rate * 2):
        amp = 0.9 if rate <= i < rate + 400 else 0.02
        frames.append(struct.pack("<h", int(32767 * amp * math.sin(i * 0.3))))
    w.writeframes(b"".join(frames))
cmds.currentUnit(time="ntsc")
node = cmds.sound(file=path, offset=10)
env = scene.waveform(node, 0, 70)
loud = [f for f, a in env if a > 0.5]
gate("the waveform: the click at the sound's 1 s, offset 10", loud and 39.5 <= min(loud) <= 40.5,
     "loud from %s" % (min(loud) if loud else None))
gate("silence before it", all(a < 0.1 for f, a in env if f < 38))
gate("sounds listed", scene.sounds() == [node])

# 11 character sets
cset = cmds.character(cube + ".tx", name="hero")
gate("character sets listed", scene.character_sets() == ["hero"])
scene.pick_character("hero")
if scene.current_character() == "" and cmds.about(batch=True):
    #  Maya's highlightList (its own currentCharacters.mel's read) holds nothing in
    #  batch: the GUI check is the animator's
    print("SKIP  a character set picked - batch Maya keeps no current character set")
else:
    gate("a character set picked", scene.current_character() == "hero", scene.current_character())
scene.pick_character("")
gate("none", scene.current_character() == "")

# 12 layers
cmds.select(cube)
cmds.animLayer("Layer1", addSelectedObjects=True)
found = scene.layers()
gate("layers listed, the root first", [label for _n, label, _s in found][:1] == ["BaseAnimation"]
     and "Layer1" in [n for n, _l, _s in found])
scene.pick_layer("Layer1")
gate("a layer picked is the chip's", scene.layer_label() == "Layer1", scene.layer_label())

print("\n%d failed" % len(FAILED) if FAILED else "\nall gates passed")
