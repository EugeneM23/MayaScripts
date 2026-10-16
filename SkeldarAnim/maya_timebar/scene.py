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


def toggle_play():
    if cmds.play(q=True, state=True):
        cmds.play(state=False)
    else:
        cmds.play(forward=True)


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
