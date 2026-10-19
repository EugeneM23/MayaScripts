"""Our Channel Box (2026-10-18), variant A "Rows": a painted Channel Box in the side
panel's Channels tab, alone, the whole height (no Layer Editor: «нужно убрать окно
слоев»). Mounted while the side panel holds Maya's Channels forms (right edge mode)
and the switch is on (⋮ -> Side panel ▸ Our Channel Box, optionVar
skeldarChannelBoxOurs, on by default).

Maya's own Channels forms (Channel Box / Layer Editor) are kept hidden in our page
and given back as they were. Its Channel Box stays alive: ours writes the selected
channels into it, so the Graph Editor and every tool reading it keep working.

Nothing heavy at import. The state lives on `sys` (trap 111); every Maya widget is
found again by name when used (trap 135).
Spec: docs/superpowers/specs/2026-10-18-channel-box-rows-design.md
"""

import sys
import traceback

VAR = "skeldarChannelBoxOurs"
HOLDER = "skeldarSidePanelChannelBoxKept"   # Maya's Channels forms, hidden, alive


def _state():
    state = getattr(sys, "_skeldar_channelbox", None)
    if state is None:
        state = {"box": None, "holder": None, "page": None,
                 "callbacks": [], "node_callbacks": [], "pending": None}
        sys._skeldar_channelbox = state
    return state


def _cmds():
    import maya.cmds as cmds
    return cmds


def enabled():
    try:
        cmds = _cmds()
        return bool(cmds.optionVar(q=VAR)) if cmds.optionVar(exists=VAR) else True
    except Exception:                                        # noqa: BLE001
        return True


def set_enabled(on):
    """⋮ -> Side panel ▸ Our Channel Box: the side panel rebuilt with ours, or with
    Maya's Channel Box again."""
    on = bool(on)
    _cmds().optionVar(intValue=(VAR, 1 if on else 0))
    try:
        import maya_sidepanel
        if maya_sidepanel.mode() == "edge":
            maya_sidepanel.rebuild()
    except Exception:                                        # noqa: BLE001
        print(traceback.format_exc())
    try:
        import maya_hub
        maya_hub.repaint_sidepanel()
    except Exception:                                        # noqa: BLE001
        pass
    return ("Side panel: our Channel Box" if on else "Side panel: Maya's Channel Box")


def current():
    """The live box, or None (a dead wrapper dropped)."""
    box = _state().get("box")
    if box is None:
        return None
    try:
        import maya_hubqt
        if maya_hubqt.qt().shiboken.isValid(box):
            return box
    except Exception:                                        # noqa: BLE001
        pass
    _state()["box"] = None
    return None


def mount(panel, records, ui=1.0):
    """Ours alone in `panel`'s Channels page; `records` the side panel's borrowed
    Channels forms (already in that page), moved into a hidden holder where Maya's
    Channel Box stays alive. The box, or None."""
    if not enabled():
        return None
    unmount()
    import maya_hubqt
    import maya_hubstyle
    from maya_sidepanel import holder
    from . import box as box_module, scene
    QtWidgets = maya_hubqt.qt().QtWidgets
    widgets = [holder.widget(r["form"]) for r in records]
    widgets = [w for w in widgets if w is not None]
    if not widgets:
        return None
    page_layout = panel.pages["channels"]
    page = page_layout.parentWidget()
    kept = QtWidgets.QWidget(page)
    kept.setObjectName(HOLDER)
    lay = QtWidgets.QVBoxLayout(kept)
    lay.setObjectName(HOLDER + "Layout")             # trap 278: no unnamed layout above Maya's
    lay.setContentsMargins(0, 0, 0, 0)
    for w in widgets:
        lay.addWidget(w)
    kept.hide()
    box = box_module.make(scene, ui, maya_hubstyle.TOKENS, parent=page)
    page_layout.addWidget(box)
    _state().update(box=box, holder=kept, page=page)
    _start_callbacks()
    try:
        box.refresh(effects=False)
    except Exception:                                        # noqa: BLE001
        print(traceback.format_exc())
    return box


def unmount():
    """Maya's forms back in the page as they came, ours gone. Safe to call any time."""
    state = _state()
    _stop_callbacks()
    box, kept, page = state.get("box"), state.get("holder"), state.get("page")
    state.update(box=None, holder=None, page=None)
    try:
        import maya_hubqt
        q = maya_hubqt.qt()
        if kept is not None and q.shiboken.isValid(kept):
            if page is not None and q.shiboken.isValid(page):
                lay = kept.layout()
                for w in [lay.itemAt(i).widget() for i in range(lay.count())]:
                    if w is not None:
                        page.layout().addWidget(w)   # out of ours BEFORE ours goes
                        w.show()
            kept.setParent(None)
            kept.deleteLater()
        if box is not None and q.shiboken.isValid(box):
            box.setParent(None)
            box.deleteLater()
    except Exception:                                        # noqa: BLE001
        print(traceback.format_exc())
        return False
    return box is not None


def _shown():
    try:
        import maya_sidepanel
        edge = maya_sidepanel._state().get("edge")
        return bool(edge is not None and edge.alive() and edge.shown
                    and edge.panel.tab == "channels")
    except Exception:                                        # noqa: BLE001
        return True


def refresh():
    """Everything read again (the side panel's refresh, a selection)."""
    box = current()
    if box is None:
        return
    try:
        box.refresh()
        _watch_nodes(box.objects)
    except Exception:                                        # noqa: BLE001
        print(traceback.format_exc())


def _schedule(kind):
    """A full read ('full') or the values only ('values'), once, when the event loop
    next turns - many callbacks in one command make one read."""
    state = _state()
    if state.get("pending") == "full":
        return
    first = state.get("pending") is None
    state["pending"] = "full" if kind == "full" else (state.get("pending") or "values")
    if not first:
        return
    try:
        import maya_hubqt
        maya_hubqt.qt().QtCore.QTimer.singleShot(0, _run_pending)
    except Exception:                                        # noqa: BLE001
        _run_pending()


def _run_pending():
    state = _state()
    kind, state["pending"] = state.get("pending"), None
    box = current()
    if box is None or not _shown():
        return
    try:
        if kind == "full":
            box.refresh()
            _watch_nodes(box.objects)
        else:
            box.on_values()
    except Exception:                                        # noqa: BLE001
        print(traceback.format_exc())


def _time_changed(*_args):
    box = current()
    if box is None or not _shown():
        return
    try:
        box.on_time()
    except Exception:                                        # noqa: BLE001 - every frame: never raise
        pass


def _attr_changed(msg, plug, other, *_args):
    try:
        import maya.api.OpenMaya as om
        if msg & (om.MNodeMessage.kConnectionMade | om.MNodeMessage.kConnectionBroken
                  | om.MNodeMessage.kAttributeLocked | om.MNodeMessage.kAttributeUnlocked
                  | om.MNodeMessage.kAttributeKeyable | om.MNodeMessage.kAttributeUnkeyable):
            _schedule("full")
        elif msg & om.MNodeMessage.kAttributeSet:
            _schedule("values")
    except Exception:                                        # noqa: BLE001
        pass


def _watch_nodes(nodes):
    """Attribute-changed callbacks on the shown nodes (a manipulator drag, a value
    set elsewhere), again for each new selection."""
    state = _state()
    _drop(state.get("node_callbacks"))
    out = []
    try:
        import maya.api.OpenMaya as om
        for node in nodes or []:
            try:
                sel = om.MSelectionList()
                sel.add(node)
                out.append(om.MNodeMessage.addAttributeChangedCallback(sel.getDependNode(0), _attr_changed))
            except Exception:                                # noqa: BLE001
                pass
    except Exception:                                        # noqa: BLE001
        pass
    state["node_callbacks"] = out


def _drop(ids):
    try:
        import maya.api.OpenMaya as om
        for cid in ids or []:
            try:
                om.MMessage.removeCallback(cid)
            except Exception:                                # noqa: BLE001
                pass
    except Exception:                                        # noqa: BLE001
        pass


def _start_callbacks():
    _stop_callbacks()
    out = []
    try:
        import maya.api.OpenMaya as om
        import maya.api.OpenMayaAnim as oma
        for event in ("SelectionChanged", "Undo", "Redo", "animLayerRefresh"):
            try:
                out.append(om.MEventMessage.addEventCallback(event, lambda *_a: _schedule("full")))
            except Exception:                                # noqa: BLE001
                pass
        out.append(om.MDGMessage.addTimeChangeCallback(_time_changed))
        out.append(oma.MAnimMessage.addAnimKeyframeEditedCallback(lambda *_a: _schedule("full")))
    except Exception:                                        # noqa: BLE001
        print(traceback.format_exc())
    _state()["callbacks"] = out


def _stop_callbacks():
    state = _state()
    _drop(state.get("callbacks"))
    _drop(state.get("node_callbacks"))
    state["callbacks"], state["node_callbacks"] = [], []
