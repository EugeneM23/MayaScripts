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


def _scope():
    """The curves the Time Bar's keys are: with animation layers, the selection's
    curves in the ACTIVE layer only, as Maya's slider shows them (2026-10-19); None
    without layers (the selection's every curve, Maya's default)."""
    try:
        from . import layerscene
        layerscene.key_hook()
        return layerscene.active_curves()
    except Exception:                                        # noqa: BLE001
        return None


def _kq(**flags):
    """`keyframe -q` over the scope: the selection's, or the active layer's curves."""
    scope = _scope()
    if scope is None:
        return cmds.keyframe(q=True, **flags)
    return cmds.keyframe(scope, q=True, **flags) if scope else []


def _on(command, **flags):
    """A key command over the scope; nothing when the active layer holds none."""
    scope = _scope()
    if scope is None:
        return command(**flags)
    return command(scope, **flags) if scope else None


def keys():
    """(keys, breakdowns): the selection's key times, as Maya's slider shows them -
    with animation layers, those of the active layer."""
    if not cmds.ls(selection=True):
        return [], []
    try:
        times = _kq(timeChange=True) or []
        broken = _kq(breakdown=True) or []
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
    """`selection` (first, last) highlighted, or None: cleared. Unrecorded, as
    Maya's own slider highlight is: a `playbackOptions` edit is an undo step, so
    after a key drag (which moves the highlight with the keys) the first Ctrl+Z
    put the highlight back and left the keys moved (2026-10-19). Called only from
    the strip's mouse events, never inside an open undo chunk (trap 145)."""
    try:
        with _unrecorded():
            if selection is None:
                cmds.playbackOptions(edit=True, selectionVisible=False)
                return
            first, last = selection
            cmds.playbackOptions(edit=True, selectionStartTime=first, selectionEndTime=last,
                                 selectionVisible=True)
    except Exception:                                        # noqa: BLE001
        pass


def set_time(frame):
    """The time set, unrecorded, as Maya's own slider sets it: in a GUI Maya a
    scripted `currentTime -e` IS an undo step, so every click, scrub step and
    transport button put one on Ctrl+Z - and with scene tabs it made the tab look
    worked in and buried the previous tab's history (2026-10-19, measured in a GUI
    Maya: queue 101 -> 102, unrecorded 102 -> 102). Called from the strip's
    presses, never inside an open undo chunk (trap 145)."""
    with _unrecorded():
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


def layer_state():
    """(the chip's text, the number of animation layers - the root counted) from ONE read of the
    layers: ('', 0) without any."""
    found = layers()
    return layer_label(found), len(found)


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
    """Time moved without updating the scene (Maya's middle-drag); unrecorded, as
    `set_time`."""
    with _unrecorded():
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


def layer_link():
    """The layer panel's road into Maya."""
    from . import layerscene
    return layerscene


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
    """The key menu's Set key: into the active layer, as S (layerscene.before_key)."""
    try:
        from . import layerscene
    except Exception:                                        # noqa: BLE001
        layerscene = None
    if layerscene is not None:
        layerscene.before_key()
    try:
        cmds.setKeyframe()
    finally:
        if layerscene is not None:
            layerscene.after_key()


def run_key_command(name):
    """One of Maya's Set Key runtime commands (`look.DRAG_KEYS`), as its hotkey runs it."""
    if name not in look.DRAG_KEYS.values():
        raise ValueError("not a key command: %r" % (name,))
    import maya.mel as mel
    mel.eval(name)


def breakdown(selection, frame):
    a, b = _span(selection, frame)
    with _chunk("skeldarTimeBarBreakdown"):
        if not _kq(time=(a, b)):
            cmds.setKeyframe(breakdown=True)
        else:
            _on(cmds.keyframe, edit=True, time=(a, b), breakdown=True)


def cut_keys(selection, frame):
    _on(cmds.cutKey, time=_span(selection, frame), option="keys")


def copy_keys(selection, frame):
    _on(cmds.copyKey, time=_span(selection, frame), option="keys")


def paste_keys(selection, frame):
    _on(cmds.pasteKey, time=(_span(selection, frame)[0],), option="merge")


def delete_keys(selection, frame):
    _on(cmds.cutKey, time=_span(selection, frame), clear=True)


def tangents(selection, frame, kind):
    a, b = _span(selection, frame)
    if kind == "step":
        _on(cmds.keyTangent, time=(a, b), outTangentType="step")
    else:
        _on(cmds.keyTangent, time=(a, b), inTangentType=kind, outTangentType=kind)


def snap_keys(selection, frame):
    _on(cmds.snapKey, time=_span(selection, frame), timeMultiple=1)


def move_keys(selection, target, only=None):
    """The selection's keys in `selection` moved or scaled onto `target`, on
    whole frames: one undo step. `only` ({curve: [times]}, what `stamp_keys`
    answered) after S during the drag: those keys alone move, and the copies S
    put down inside the block stay where they are."""
    a, b = selection
    na, nb = target
    if (na, nb) == (a, b):
        return
    if only:
        with _chunk("skeldarTimeBarMoveKeys"):
            _move_only(only, selection, target)
            _show_now(list(only))
        return
    #  the live drag's begin and release, one undo step (the highlight's cells, a key
    #  between frames in the last cell too): a key standing where a moved one lands
    #  goes - `keyframe -option over` left both, or parked the moved one at
    #  x.9999998 - and breakdowns keep their frames (2026-10-20, `_shift_all`)
    if live_begin(selection):
        live_end(tuple(target))


def _show_now(curves):
    """The scene shown at the current frame from the curves just edited. A key
    edit made by command leaves a GUI Maya's viewport on the old values until the
    time changes (2026-10-19, «переношу ключи по таймслайдеру ... анимация не
    обновляется во вьюпорте»; mayapy reads the new value at once, so only the
    animator's Maya shows it): the edited curves dirtied, the frame evaluated
    again. Never raises - the keys moved either way."""
    try:
        if curves:
            cmds.dgdirty(curves)
        cmds.currentTime(cmds.currentTime(q=True), update=True)
    except Exception:                                        # noqa: BLE001 - a redraw only
        pass


def key_range(a, b, name):
    """`name` (a Set Key runtime command, `look.DRAG_KEYS`) on every whole frame
    from `a` to `b`, as if S were pressed on each: a highlight standing and S
    pressed («такая себе версия бейка»). One undo step; the time put back."""
    if name not in look.DRAG_KEYS.values():
        raise ValueError("not a key command: %r" % (name,))
    import maya.mel as mel
    now = cmds.currentTime(q=True)
    frames = range(int(a), int(b) + 1)
    with _chunk("skeldarTimeBarKeyRange"):
        cmds.refresh(suspend=True)
        try:
            #  the curves that stand get their keys first, inserted (the shape kept):
            #  keyed one frame after another, each new key would reshape the spline
            #  ahead of it and the "bake" would drift off the motion
            #  each inside its own keys (an insert past a curve's keys re-types the key
            #  beside it, CLAUDE.md trap 267)
            for curve in _kq(name=True) or []:
                times = cmds.keyframe(curve, q=True, timeChange=True) or []
                if not times:
                    continue
                for frame in frames:
                    if min(times) < frame < max(times):
                        cmds.setKeyframe(curve, insert=True, time=(frame,))
            for frame in frames:
                cmds.currentTime(frame, update=True)
                mel.eval(name)
        finally:
            cmds.currentTime(now, update=True)
            cmds.refresh(suspend=False)


def _key_data(curve, t):
    """One key as it stands: value, tangents, breakdown - enough to write it again."""
    span = (t, t)
    one = lambda **flag: (cmds.keyTangent(curve, q=True, time=span, **flag) or [None])[0]
    return {
        "value": (cmds.keyframe(curve, q=True, time=span, valueChange=True) or [0.0])[0],
        "breakdown": bool(cmds.keyframe(curve, q=True, time=span, breakdown=True)),
        "itt": one(inTangentType=True), "ott": one(outTangentType=True),
        "ia": one(inAngle=True), "oa": one(outAngle=True),
        "iw": one(inWeight=True), "ow": one(outWeight=True), "lock": one(lock=True),
        "weighted": bool((cmds.keyTangent(curve, q=True, weightedTangents=True) or [False])[0]),
    }


def _put_key(curve, t, data):
    """`data` (`_key_data`) written at `t`, replacing a key standing there."""
    span = (t, t)
    cmds.setKeyframe(curve, time=(t,), value=data["value"], breakdown=data["breakdown"])
    cmds.keyTangent(curve, edit=True, time=span, lock=False)
    for key, flag in (("itt", "inTangentType"), ("ott", "outTangentType")):
        if data[key]:
            cmds.keyTangent(curve, edit=True, time=span, **{flag: data[key]})
    if data["itt"] == "fixed" and data["ia"] is not None:
        cmds.keyTangent(curve, edit=True, time=span, inAngle=data["ia"])
    if data["ott"] == "fixed" and data["oa"] is not None:
        cmds.keyTangent(curve, edit=True, time=span, outAngle=data["oa"])
    # a weight only on a fixed side: Maya works an auto / spline / linear side's weight
    # out from the neighbours, and a weight written on it turns it fixed (measured
    # 2026-10-20: an auto key on a weighted curve came back fixed, its angle 0)
    if data["weighted"] and data["itt"] == "fixed" and data["iw"] is not None:
        cmds.keyTangent(curve, edit=True, time=span, inWeight=data["iw"])
    if data["weighted"] and data["ott"] == "fixed" and data["ow"] is not None:
        cmds.keyTangent(curve, edit=True, time=span, outWeight=data["ow"])
    if data["lock"] is not None:
        cmds.keyTangent(curve, edit=True, time=span, lock=bool(data["lock"]))


def _place(only, selection, target):
    """{curve: [(new time, data)]} - every dragged key at its place on `target`."""
    return dict((curve, [(float(round(look.mapped(t, selection, target))), data)
                         for t, data in rec["keys"]])
                for curve, rec in only.items() if cmds.objExists(curve))


def _move_only(only, selection, target):
    """The dragged keys (`only`, read by the first S) set down on `target` from what
    they were, replacing what stands there (a copy S put down); where they stood
    nothing is left but the copies S put there."""
    for curve, placed in _place(only, selection, target).items():
        rec = only[curve]
        for t, _data in rec["keys"]:
            if round(t, 4) not in rec["stamped"]:
                cmds.cutKey(curve, time=(t, t), clear=True)
        for nt, data in placed:
            _put_key(curve, nt, data)


def stamp_keys(selection, target, only=None):
    """A copy of each selected key in `selection` put down where the drag has it
    now (`target`, moved or scaled by an edge: `look.mapped`), value and tangents
    with it; nothing in the gaps between them, the originals stay («когда мы
    переносим массив ключей и нажимаем s то мы должны проставлять все ключи которые
    у нас выделены, ключи в пробелах массива проставлять не нужно»). One undo step.

    Answers the dragged keys as they were ({curve: {"keys": [(time, data)],
    "stamped": {times}}}); the strip hands it back on the next S of the same drag
    (`only`: copies are written from it, never copied again) and on the release
    (`move_keys`)."""
    a, b = selection
    span = (a, b + 1 - 1e-3)
    if only is None:
        only = {}
        for curve in _kq(time=span, name=True) or []:
            times = cmds.keyframe(curve, q=True, time=span, timeChange=True) or []
            if times:
                only[curve] = {"keys": [(t, _key_data(curve, t)) for t in times],
                               "stamped": set()}
    if tuple(target) == tuple(selection):
        return only
    with _chunk("skeldarTimeBarStampKeys"):
        for curve, placed in _place(only, selection, target).items():
            for nt, data in placed:
                _put_key(curve, nt, data)
                only[curve]["stamped"].add(round(nt, 4))
        _show_now(list(only))
    return only


# the live key drag ---------------------------------------------------------------
#
# 2026-10-19, «во время переноса анимация во вьюпорте не обновляется»: Maya's own
# slider moves the keys while they are dragged, ours moved them on the release. Now
# the keys go where the drag has them on every step, unrecorded (a drag of forty
# steps is no forty undo steps); the release puts the curves back as they were and
# makes the whole move again inside one undo chunk, so one Ctrl+Z takes the drag.
# Each step touches only the keys that change: a dense curve costs what its dragged
# keys cost, not what its length does.

_LIVE = {}


def _curve_keys(curve):
    """[(time, data)] of every key on `curve`, read in a few queries."""
    times = cmds.keyframe(curve, q=True, timeChange=True) or []
    if not times:
        return []
    n = len(times)

    def each(values):
        values = list(values or [])
        return values if len(values) == n else [None] * n

    def tangent(**flag):
        return each(cmds.keyTangent(curve, q=True, **flag))

    values = each(cmds.keyframe(curve, q=True, valueChange=True))
    broken = set(round(t, 4) for t in (cmds.keyframe(curve, q=True, breakdown=True) or []))
    itt, ott = tangent(inTangentType=True), tangent(outTangentType=True)
    ia, oa = tangent(inAngle=True), tangent(outAngle=True)
    iw, ow = tangent(inWeight=True), tangent(outWeight=True)
    lock = tangent(lock=True)
    weighted = bool((cmds.keyTangent(curve, q=True, weightedTangents=True) or [False])[0])
    return [(t, {"value": values[i] if values[i] is not None else 0.0,
                 "breakdown": round(t, 4) in broken,
                 "itt": itt[i], "ott": ott[i], "ia": ia[i], "oa": oa[i],
                 "iw": iw[i], "ow": ow[i], "lock": lock[i], "weighted": weighted})
            for i, t in enumerate(times)]


def _placed(t, selection, target):
    """A dragged key's time with the drag on `target` (a whole frame when it is one)."""
    nt = look.mapped(t, selection, target)
    return float(nt) if abs(nt - round(nt)) > 1e-6 else float(round(nt))


def _wanted(rec, selection, target):
    """{round(time): (time, data)} the curve should hold with the drag on `target`:
    the keys that stay, the copies S put down, the dragged keys on their places
    (over whatever stood there)."""
    out = dict(rec["fixed"])
    for t, data in rec["moved"]:
        nt = _placed(t, selection, target)
        out[round(nt, 4)] = (nt, data)
    return out


def _bring(curve, rec, wanted):
    """The curve from what it holds (`rec["now"]`) to `wanted`, key by key: the new
    keys put down FIRST, the old ones cut after. Maya deletes a curve a cut empties
    (CLAUDE.md trap 210), so a curve whose every key was dragged - one key on a
    channel - lost its curve on the first cut and the keys vanished (2026-10-19:
    «ключи просто изчезают при переносе по таймлайну»)."""
    now = rec["now"]
    for k, (t, data) in sorted(wanted.items()):
        held = now.get(k)
        if held is None or held[1] is not data:
            _put_key(curve, t, data)
            now[k] = (t, data)
    for k, (t, _data) in list(now.items()):
        if k not in wanted:
            cmds.cutKey(curve, time=(t, t), clear=True)
            del now[k]


def _shift_of(selection, prev, goal):
    """Frames the dragged keys move going from `prev` to `goal` (targets of the drag)
    when the step is one shift of them all - the block's body dragged, or a key
    alone; None for an edge (a scale lands each key on its own rounded frame)."""
    length = selection[1] - selection[0]
    if selection[1] <= selection[0] or (prev[1] - prev[0] == length and goal[1] - goal[0] == length):
        return goal[0] - prev[0]
    return None


def _shift_all(target, prev, change, full=False):
    """The step from `prev` to `target` (None: back to the start) as one shift of the
    dragged keys (2026-10-20, «ключи сильно задерживаются за курсором»: writing every
    dragged key again cost 190 ms a step for a 40-frame block on 48 curves). Per curve:
    the keys in the way cut first - Maya moves a key onto one that stands there and
    leaves TWO keys on that frame -, the dragged keys moved by one `keyframe -relative
    -option over` (which passes keys standing between them, tangents kept), curves
    with the same keys moved together, and only what the block uncovered put back.
    Breakdowns are plain keys for the length of the move: Maya slides a breakdown
    to keep its place between neighbours that move (measured: 45 -> 45.5).

    A step of the drag touches only the block's two places, where it stood and
    where it lands: everywhere else a curve is as it was (a key the block once
    covered was cut then, and stands under it still). `full` (back to the start,
    and the release's move from there) looks at every key: from the start, the
    copies S put down stand where the curve holds its own keys. The shared key times of a rig's
    curves are placed once a step; the cuts, like the moves, are one command for
    the curves that want the same frames (2026-10-20: 1100 ms a step on Manny_Rig
    keyed on every frame before the shift, 107 after it, 522 curves)."""
    selection = _LIVE["selection"]
    goal = target if target is not None else selection
    spots, cuts, groups, puts, changed, plain, again = {}, {}, {}, [], [], {}, {}
    alive = set(cmds.ls(list(_LIVE["curves"])) or [])
    for curve, rec in _LIVE["curves"].items():
        if curve not in alive:
            continue
        times = rec.get("times")
        if times is None:
            times = rec["times"] = tuple(t for t, _data in rec["moved"])
        spot = spots.get(times)
        if spot is None:
            old = [_placed(t, selection, prev) for t in times]
            new = [_placed(t, selection, goal) for t in times]
            spot = spots[times] = (tuple(sorted(set(old))), new,
                                   set(round(t, 4) for t in old), set(round(t, 4) for t in new))
        cur, new, here, there = spot
        now = rec["now"]
        if full:                             # S's copies may stand anywhere: every key looked at
            wanted = rec["start"] if target is None else _wanted(rec, selection, target)
            cut = [t for k, (t, data) in now.items() if k not in here and (
                k in there or k not in wanted or wanted[k][1] is not data)]
            gone = set(round(t, 4) for t in cut)
            back = [(t, data) for k, (t, data) in sorted(wanted.items())
                    if k not in there and not (k in now and k not in here and k not in gone)]
        else:
            fixed = rec["fixed"]
            cut = [now[k][0] for k in there if k in now and k not in here]
            gone = set(round(t, 4) for t in cut)
            back = [fixed[k] for k in sorted(here) if k not in there and k in fixed]
        broken = rec.get("bd")
        if broken is None:
            broken = rec["bd"] = any(data.get("breakdown") for _t, data in rec["start"].values())
        off = ([t for k, (t, data) in now.items() if data.get("breakdown") and k not in gone]
               if broken and change and cur else [])
        if full:
            now = rec["now"] = dict(wanted)
        else:
            for k in here:
                now.pop(k, None)
            for k in gone:
                now.pop(k, None)
            for nt, (_t, data) in zip(new, rec["moved"]):
                now[round(nt, 4)] = (nt, data)
            for t, data in back:
                now[round(t, 4)] = (t, data)
        if off:
            put = set(round(t, 4) for t, _data in back)
            plain[curve] = off
            again[curve] = [t for k, (t, data) in now.items()
                            if data.get("breakdown") and k not in put]
        puts.extend((curve, t, data) for t, data in back)
        if cut:
            cuts[curve] = cut
        if change and cur:
            groups.setdefault(cur, []).append(curve)
        if cut or back or (change and cur):
            changed.append(curve)
    for times, curves in _grouped(cuts).items():
        cmds.cutKey(curves, time=[(t, t) for t in times], clear=True)
    for times, curves in _grouped(plain).items():
        cmds.keyframe(curves, edit=True, time=[(t, t) for t in times], breakdown=False)
    for cur, curves in groups.items():
        cmds.keyframe(curves, edit=True, time=[(t, t) for t in cur], relative=True,
                      timeChange=change, option="over")
    for times, curves in _grouped(again).items():
        if times:
            cmds.keyframe(curves, edit=True, time=[(t, t) for t in times], breakdown=True)
    for curve, t, data in puts:
        _put_key(curve, t, data)
    return changed


def _grouped(per_curve):
    """{frames: [curves]} - one command for the curves that want the same frames."""
    out = {}
    for curve, times in per_curve.items():
        out.setdefault(tuple(times), []).append(curve)
    return out


def _bring_all(target, prev=None):
    """The curves from the drag on `prev` (None: the selection, where they started)
    to `target` (None: back to the start). A move of the block is one shift of its
    keys (`_shift_all`); an edge drag writes the keys that change one by one."""
    full = target is None or prev is None
    prev = tuple(prev) if prev is not None else _LIVE["selection"]
    goal = tuple(target) if target is not None else _LIVE["selection"]
    change = _shift_of(_LIVE["selection"], prev, goal)
    if change is not None:
        return _shift_all(target, prev, change, full)
    changed = []
    for curve, rec in _LIVE["curves"].items():
        if not cmds.objExists(curve):
            continue
        wanted = (dict(rec["start"]) if target is None
                  else _wanted(rec, _LIVE["selection"], target))
        if set(wanted) != set(rec["now"]) or any(
                rec["now"][k][1] is not wanted[k][1] for k in wanted):
            _bring(curve, rec, wanted)
            changed.append(curve)
    return changed


class _unrecorded(object):
    def __enter__(self):
        self.was = cmds.undoInfo(q=True, state=True)
        if self.was:
            cmds.undoInfo(stateWithoutFlush=False)

    def __exit__(self, *_exc):
        if self.was:
            cmds.undoInfo(stateWithoutFlush=True)
        return False


def live_begin(selection):
    """A key drag of the highlight `selection` begins: what each curve holds, read
    once. True when there are keys to drag."""
    _LIVE.clear()
    a, b = selection
    span = (a, b + 1 - 1e-3)
    curves = {}
    for curve in _kq(time=span, name=True) or []:
        keys = _curve_keys(curve)
        moved = [(t, d) for t, d in keys if look.inside(t, selection)]
        if not moved:
            continue
        start = dict((round(t, 4), (t, d)) for t, d in keys)
        fixed = dict((round(t, 4), (t, d)) for t, d in keys if not look.inside(t, selection))
        curves[curve] = {"start": start, "now": dict(start), "fixed": fixed,
                         "moved": moved, "stamped": set()}
    if not curves:
        return False
    _LIVE.update(selection=tuple(selection), target=tuple(selection), curves=curves)
    return True


def live_to(target):
    """The dragged keys where the drag has them now, the viewport showing it."""
    if not _LIVE:
        return
    target = tuple(target)
    if target == _LIVE["target"]:
        return
    with _unrecorded():
        changed = _bring_all(target, _LIVE["target"])
        _LIVE["target"] = target
        _show_now(changed)


def live_stamp():
    """S in the drag: the dragged keys' copies stay where they are now. Answers what
    `stamp_keys` answers ({curve: {"keys": the dragged keys as they were,
    "stamped": the copies' times}}), so the strip draws it alike."""
    if not _LIVE:
        return None
    selection, target = _LIVE["selection"], _LIVE["target"]
    out = {}
    for curve, rec in _LIVE["curves"].items():
        for k, (t, data) in _wanted(rec, selection, target).items():
            if any(data is d for _t, d in rec["moved"]):
                copy = dict(data)                    # a key of its own, not the dragged one
                rec["fixed"][k] = (t, copy)
                rec["now"][k] = (t, copy)           # it stands there already
                rec["stamped"].add(k)
        out[curve] = {"keys": list(rec["moved"]), "stamped": set(rec["stamped"])}
    return out


def live_end(target=None):
    """The drag let go on `target` (None: given up, the keys back where they were).
    The curves go back to what they held, unrecorded, and the move is made again in
    one undo chunk."""
    if not _LIVE:
        return
    try:
        with _unrecorded():
            _bring_all(None, _LIVE["target"])
        if target is not None:
            for rec in _LIVE["curves"].values():
                rec["now"] = dict(rec["start"])
            with _chunk("skeldarTimeBarMoveKeys"):
                changed = _bring_all(tuple(target), None)
                _show_now(changed)
        else:
            _show_now(list(_LIVE["curves"]))
    finally:
        _LIVE.clear()


def playback_from(selection):
    if selection:
        cmds.playbackOptions(edit=True, minTime=selection[0], maxTime=selection[1])


# ------------------------------------------------------------ the skill bar (2026-10-19)

def skills():
    """The skill bar's model in Maya: the user's file, the runs through maya_skillbar.run."""
    from maya_skillbar import skills as skills_module
    return skills_module.MayaSkills()


def page_height(strip):
    """A page shown: the host as tall as the strip now wants (the bottom edge places itself,
    the docked control is resized, in logical px)."""
    import maya_timebar
    state = maya_timebar._state()
    edge = state.get("edge")
    if edge is not None and getattr(edge, "strip", None) is strip:
        try:
            edge.place()
        except Exception:                                    # noqa: BLE001
            pass
        return
    if state.get("host") != "docked" or not cmds.workspaceControl(maya_timebar.CONTROL, exists=True):
        return
    ui = getattr(strip, "ui", 1.0) or 1.0
    height = int(round(strip.sizeHint().height() / float(ui)))
    try:
        cmds.workspaceControl(maya_timebar.CONTROL, edit=True, resizeHeight=max(maya_timebar.HEIGHT, height))
    except Exception:                                        # noqa: BLE001
        pass
