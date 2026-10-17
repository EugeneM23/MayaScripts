"""The Time Bar's Maya side (2026-10-16): what the strip shows, read off the scene, and
what its presses write. Every function is small and guarded - the strip asks four
times a second.
"""

import maya.cmds as cmds

from . import look

#  one command a layer editor refresh (maya_scenetabs.layers._rebuild_editors' own)
LAYER_EDITOR = ('if (`treeView -exists AnimLayerTabanimLayerEditor` && '
                '`exists rebuildAnimLayerEditor`) rebuildAnimLayerEditor("AnimLayerTab");')


def ranges():
    """(a0, a1, p0, p1): the animation and the playback range."""
    q = lambda **flag: cmds.playbackOptions(q=True, **flag)        # noqa: E731
    return (q(animationStartTime=True), q(animationEndTime=True),
            q(minTime=True), q(maxTime=True))


def now():
    return cmds.currentTime(q=True)


def light():
    """What changes without an event the strip hears of: the time, the ranges, the
    unit, autoKey, playback, the highlight."""
    a0, a1, p0, p1 = ranges()
    return {"now": now(), "a0": a0, "a1": a1, "p0": p0, "p1": p1,
            "unit": cmds.currentUnit(q=True, time=True),
            "auto": bool(cmds.autoKeyframe(q=True, state=True)),
            "playing": bool(cmds.play(q=True, state=True)),
            "highlight": read_highlight()}


def keys():
    """(keys, breakdowns): the selection's key times, as Maya's slider shows them."""
    if not cmds.ls(selection=True):
        return [], []
    try:
        times = cmds.keyframe(q=True, timeChange=True) or []
        broken = cmds.keyframe(q=True, breakdown=True) or []
    except Exception:                                        # noqa: BLE001 - nothing keyable picked
        return [], []
    bd = sorted(set(round(t, 4) for t in broken))
    bd_set = set(bd)
    return sorted(set(round(t, 4) for t in times) - bd_set), bd


def read_highlight():
    """(first, last) of the highlight, or None."""
    try:
        if not cmds.playbackOptions(q=True, selectionVisible=True):
            return None
        first = cmds.playbackOptions(q=True, selectionStartTime=True)
        last = cmds.playbackOptions(q=True, selectionEndTime=True)
    except Exception:                                        # noqa: BLE001 - a Maya without the flags
        return None
    return look.highlight(first, last)


def set_highlight(selection):
    """`selection` (first, last) highlighted, or None: cleared."""
    try:
        if selection is None:
            cmds.playbackOptions(edit=True, selectionVisible=False)
            return
        first, last = selection
        cmds.playbackOptions(edit=True, selectionStartTime=first, selectionEndTime=last,
                             selectionVisible=True)
    except Exception:                                        # noqa: BLE001
        pass


def set_time(frame):
    cmds.currentTime(frame, edit=True)


def set_ranges(a0, a1, p0, p1):
    cmds.playbackOptions(edit=True, animationStartTime=a0, animationEndTime=a1,
                         minTime=p0, maxTime=p1)


def _slider():
    """Maya's (hidden) time slider; batch Maya has none - raised, never a MEL error printed."""
    if cmds.about(batch=True):
        raise RuntimeError("no time slider in batch")
    import maya.mel as mel
    return mel.eval("$gPlayBackSlider=$gPlayBackSlider")


def begin_scrub():
    """Maya's scrub mode for the length of a drag (Maya's slider's own: the sound
    scrubs, the evaluation is the interactive one); the hidden slider still takes it."""
    try:
        cmds.timeControl(_slider(), edit=True, beginScrub=True)
    except Exception:                                        # noqa: BLE001 - no slider, no scrub mode
        pass


def end_scrub():
    try:
        cmds.timeControl(_slider(), edit=True, endScrub=True)
    except Exception:                                        # noqa: BLE001
        pass


def toggle_play(forward=True):
    """Play forwards (or backwards); a press while playing stops."""
    if cmds.play(q=True, state=True):
        cmds.play(state=False)
    else:
        cmds.play(forward=bool(forward))


def step_key(forward, known):
    """To the next (or previous) of `known` keys; False when there is none."""
    frame = look.neighbour_key(known, now(), forward)
    if frame is None:
        return False
    set_time(frame)
    return True


def toggle_auto():
    cmds.autoKeyframe(state=not cmds.autoKeyframe(q=True, state=True))


def set_unit(unit):
    cmds.currentUnit(time=unit)


def _label(name):
    try:
        from maya_scenetabs import scope
        return scope.local(name)
    except Exception:                                        # noqa: BLE001
        return name.split(":")[-1]


def layers():
    """[(name, label, selected)] - the animation layers, the root first; [] without any."""
    root = cmds.animLayer(q=True, root=True)
    if not root:
        return []
    found = [root]
    i = 0
    while i < len(found):
        found.extend(cmds.animLayer(found[i], q=True, children=True) or [])
        i += 1
    try:
        from maya_scenetabs import scope
        found = [found[0]] + [n for n in scope.active_only(found[1:])]
    except Exception:                                        # noqa: BLE001
        pass
    out = []
    for name in found:
        label = "BaseAnimation" if name == root else _label(name)
        out.append((name, label, bool(cmds.animLayer(name, q=True, selected=True))))
    return out


def layer_label(found=None):
    """The chip's text: the layer keys go to (the last selected one that is not the
    root), BaseAnimation otherwise, '' without layers."""
    found = layers() if found is None else found
    if not found:
        return ""
    picked = [label for _name, label, sel in found[1:] if sel]
    return picked[-1] if picked else "BaseAnimation"


def pick_layer(name):
    for other, _label_, _sel in layers():
        try:
            cmds.animLayer(other, edit=True, selected=(other == name), preferred=(other == name))
        except Exception:                                    # noqa: BLE001
            pass
    try:
        import maya.mel as mel
        mel.eval(LAYER_EDITOR)
    except Exception:                                        # noqa: BLE001 - a UI refresh only
        pass


# -- the full bar (2026-10-16, the second mockup) -------------------------------------

_WAVES = {}             # (path, mtime) -> (samples, rate): a sound file read once


def scrub_only(frame):
    """Time moved without updating the scene (Maya's middle-drag)."""
    cmds.currentTime(frame, edit=True, update=False)


def extra():
    """What the range row shows besides the ranges."""
    return {"loop": cmds.playbackOptions(q=True, loop=True),
            "speed": cmds.playbackOptions(q=True, playbackSpeed=True),
            "cache": cache_on(),
            "sound": current_sound(),
            "sound_shown": sound_shown(),
            "character": current_character()}


# loop, speed, cache ------------------------------------------------------------------

def cycle_loop():
    order = list(look.LOOPS)
    now_ = cmds.playbackOptions(q=True, loop=True)
    nxt = order[(order.index(now_) + 1) % len(order)] if now_ in order else order[0]
    cmds.playbackOptions(edit=True, loop=nxt)
    return nxt


def set_speed(speed):
    cmds.playbackOptions(edit=True, playbackSpeed=speed)


def cache_on():
    try:
        return bool(cmds.evaluator(name="cache", q=True, enable=True))
    except Exception:                                        # noqa: BLE001
        return False


def toggle_cache():
    try:
        cmds.evaluator(name="cache", enable=not cache_on())
    except Exception:                                        # noqa: BLE001
        pass


def preferences():
    import maya.mel as mel
    mel.eval('preferencesWnd "timeslider";')


# character sets ----------------------------------------------------------------------

def character_sets():
    return sorted(cmds.ls(type="character") or [])


def current_character():
    """Maya keeps the current character set in the `highlightList` selection
    connection (setCurrentCharacters.mel)."""
    try:
        found = cmds.selectionConnection("highlightList", q=True, object=True) or []
    except Exception:                                        # noqa: BLE001
        return ""
    found = [n for n in found if cmds.objExists(n) and cmds.nodeType(n) == "character"]
    return found[0] if found else ""


def pick_character(name):
    import maya.mel as mel
    mel.eval('setCurrentCharacters({%s});' % ('"%s"' % name if name else ""))


# bookmarks ---------------------------------------------------------------------------

def _bookmark_plugin():
    if not cmds.pluginInfo("timeSliderBookmark", q=True, loaded=True):
        cmds.loadPlugin("timeSliderBookmark", quiet=True)


def bookmarks():
    """[(start, stop, (r, g, b), name)] of Maya's time slider bookmarks, by start."""
    try:
        if not cmds.pluginInfo("timeSliderBookmark", q=True, loaded=True):
            return []
    except Exception:                                        # noqa: BLE001
        return []
    out = []
    for bm in cmds.ls(type="timeSliderBookmark") or []:
        try:
            out.append((cmds.getAttr(bm + ".timeRangeStart"), cmds.getAttr(bm + ".timeRangeStop"),
                        tuple(cmds.getAttr(bm + ".color")[0]), cmds.getAttr(bm + ".name") or bm))
        except Exception:                                    # noqa: BLE001
            pass
    return sorted(out)


def add_bookmark(selection):
    """A bookmark over the highlight, else over the playback range (Maya's rule).
    Made as the plugin's `createBookmark` makes it, without its two side effects:
    reading Maya's slider (none in batch, hidden here) and moving time to the end."""
    _bookmark_plugin()
    from maya.plugin.timeSliderBookmark import timeSliderBookmark as tsb
    if selection:
        start, stop = min(selection), max(selection)
    else:
        start, stop = cmds.playbackOptions(q=True, minTime=True), cmds.playbackOptions(q=True, maxTime=True)
    with _chunk("skeldarTimeBarBookmark"):
        cmds.pluginInfo("timeSliderBookmark", edit=True, writeRequires=True)
        picked = cmds.ls(selection=True)
        node = cmds.createNode("timeSliderBookmark", skipSelect=True)
        cmds.setAttr(node + ".timeRangeStart", start)
        cmds.setAttr(node + ".timeRangeStop", stop)
        cmds.setAttr(node + ".color", *[c / 255.0 for c in tsb.pickColor()])
        cmds.setAttr(node + ".priority", tsb.getNextPriority())
        cmds.select(picked, replace=True)
    return node


def step_bookmark(forward):
    """The time to the next (or previous) bookmark's start; False with none."""
    starts = [b[0] for b in bookmarks()]
    frame = look.neighbour_key(starts, now(), forward)
    if frame is None:
        return False
    set_time(frame)
    return True


# sound -------------------------------------------------------------------------------

def sounds():
    return sorted(cmds.ls(type="audio") or [])


def current_sound():
    try:
        return cmds.timeControl(_slider(), q=True, sound=True) or ""
    except Exception:                                        # noqa: BLE001
        return ""


def sound_shown():
    try:
        return bool(cmds.timeControl(_slider(), q=True, displaySound=True))
    except Exception:                                        # noqa: BLE001
        return False


def set_sound(node):
    """`node` the slider's sound (scrubbing plays it), '' none."""
    cmds.timeControl(_slider(), edit=True, sound=node or "", displaySound=bool(node))


def toggle_sound():
    cmds.timeControl(_slider(), edit=True, displaySound=not sound_shown())


def _samples(path):
    """(mono samples -1..1, rate) of a .wav, or None (another format, unreadable)."""
    import array
    import os
    import wave
    try:
        key = (path, os.path.getmtime(path))
    except OSError:
        return None
    if key in _WAVES:
        return _WAVES[key]
    found = None
    try:
        with wave.open(path, "rb") as w:
            width, channels, rate = w.getsampwidth(), w.getnchannels(), w.getframerate()
            raw = w.readframes(w.getnframes())
        if width == 2:
            data, scale = array.array("h", raw), 32768.0
        elif width == 4:
            data, scale = array.array("i", raw), 2147483648.0
        elif width == 1:
            data, scale = [b - 128 for b in raw], 128.0
        else:
            data = None
        if data is not None:
            keep = max(1, rate // 2000)          # a ~2 kHz mono copy: plenty for a bar
            step = max(1, channels) * keep
            found = ([data[i] / scale for i in range(0, len(data), step)], rate / float(keep))
    except Exception:                                        # noqa: BLE001 - not a wav Python reads
        found = None
    _WAVES[key] = found
    return found


def waveform(node, start, end):
    """[(frame, amplitude)] of the sound `node` over [start, end], or []."""
    if not node or not cmds.objExists(node):
        return []
    found = _samples(cmds.getAttr(node + ".filename") or "")
    if not found:
        return []
    fps = look.UNIT_FPS.get(cmds.currentUnit(q=True, time=True), 30) or 30
    return look.envelope(found[0], found[1], fps, cmds.getAttr(node + ".offset"), start, end)


# keys --------------------------------------------------------------------------------

def _span(selection, frame):
    return (selection[0], selection[1]) if selection else (frame, frame)


class _chunk(object):
    def __init__(self, name):
        self.name = name

    def __enter__(self):
        cmds.undoInfo(openChunk=True, chunkName=self.name)

    def __exit__(self, *_exc):
        cmds.undoInfo(closeChunk=True)
        return False


def set_key():
    cmds.setKeyframe()


def breakdown(selection, frame):
    a, b = _span(selection, frame)
    with _chunk("skeldarTimeBarBreakdown"):
        if not cmds.keyframe(q=True, time=(a, b)):
            cmds.setKeyframe(breakdown=True)
        else:
            cmds.keyframe(edit=True, time=(a, b), breakdown=True)


def cut_keys(selection, frame):
    cmds.cutKey(time=_span(selection, frame), option="keys")


def copy_keys(selection, frame):
    cmds.copyKey(time=_span(selection, frame), option="keys")


def paste_keys(selection, frame):
    cmds.pasteKey(time=(_span(selection, frame)[0],), option="merge")


def delete_keys(selection, frame):
    cmds.cutKey(time=_span(selection, frame), clear=True)


def tangents(selection, frame, kind):
    a, b = _span(selection, frame)
    if kind == "step":
        cmds.keyTangent(time=(a, b), outTangentType="step")
    else:
        cmds.keyTangent(time=(a, b), inTangentType=kind, outTangentType=kind)


def snap_keys(selection, frame):
    cmds.snapKey(time=_span(selection, frame), timeMultiple=1)


def move_keys(selection, target):
    """The selection's keys in `selection` moved or scaled onto `target`, on
    whole frames: one undo step."""
    a, b = selection
    na, nb = target
    if (na, nb) == (a, b):
        return
    #  the highlight's cells, [a, b + 1): a key between frames in the last cell
    #  moves too (2026-10-17, the cells drawn as Maya's slider draws them)
    span = (a, b + 1 - 1e-3)
    with _chunk("skeldarTimeBarMoveKeys"):
        if b <= a or (nb - na) == (b - a):
            cmds.keyframe(edit=True, time=span, relative=True, timeChange=na - a, option="over")
        else:
            pivot = b if nb == b else a
            factor = float(nb - na) / (b - a)
            cmds.scaleKey(time=span, timeScale=factor, timePivot=pivot)
            #  half a frame wider: a scaled key lands a hair past the edge (50.0000002)
            far = pivot + (b + 1 - pivot) * factor
            cmds.snapKey(time=(min(na, a) - 0.5, max(nb, b, far) + 0.5), timeMultiple=1)


def playback_from(selection):
    if selection:
        cmds.playbackOptions(edit=True, minTime=selection[0], maxTime=selection[1])
