"""Side panel: Maya's Channel Box / Layer Editor and Attribute Editor in a panel that
slides out of the right edge of Maya's window, the Time Bar's bottom edge on its side
(2026-10-17). ⋮ -> Side panel ▸ Maya's / Right edge (Maya's by default); hotkey rows
window.sidepanel, sidepanel.channels, sidepanel.attributes.

Nothing heavy at import: MEL asks `holds(tab)` on every selection.
Spec: docs/superpowers/specs/2026-10-17-side-panel-design.md
"""

import sys
import traceback

MODE_VAR = "skeldarSidePanelMode"
TAB_VAR = "skeldarSidePanelTab"
WIDTH_VAR = "skeldarSidePanelWidth"
HIDDEN_VAR = "skeldarSidePanelHidden"   # Maya's controls we hid, shown again on Maya's mode
SELECT_VAR = "skeldarSidePanelOnSelect"  # 1 (default): a selection brings it out, keeps it


def _state():
    state = getattr(sys, "_skeldar_sidepanel", None)
    if state is None:
        state = {"edge": None, "held": {}}
        sys._skeldar_sidepanel = state
    return state


def holds(tab):
    """The panel holds `tab`'s editors (asked by Maya's visibility procs)."""
    try:
        return 1 if _state()["held"].get(tab) else 0
    except Exception:                                        # noqa: BLE001
        return 0


def _cmds():
    import maya.cmds as cmds
    return cmds


def _var(name, default=None):
    cmds = _cmds()
    return cmds.optionVar(q=name) if cmds.optionVar(exists=name) else default


def mode():
    from . import look
    return look.mode_from(_var(MODE_VAR))


def tab():
    from . import look
    return look.tab_from(_var(TAB_VAR))


def on_select():
    """A selection brings the panel out and keeps it out - optional since
    2026-10-17 («сделаем опциональным выезд по выделению»), on by default."""
    try:
        return bool(_var(SELECT_VAR, 1))
    except Exception:                                        # noqa: BLE001
        return True


def set_on_select(on):
    """⋮ -> Side panel ▸ Out on selection."""
    on = bool(on)
    _cmds().optionVar(intValue=(SELECT_VAR, 1 if on else 0))
    controller = _state().get("edge")
    if controller is not None and on:
        try:
            controller.selection_changed()
        except Exception:                                    # noqa: BLE001
            print(traceback.format_exc())
    return ("Side panel: comes out on a selection" if on
            else "Side panel: a selection no longer brings it out")


def _has_selection():
    """The edge's `selected` seam: False whenever the option is off."""
    if not on_select():
        return False
    try:
        return bool(_cmds().ls(selection=True, head=1))
    except Exception:                                        # noqa: BLE001
        return False


def _remember_tab(value):
    _cmds().optionVar(stringValue=(TAB_VAR, value))


def _remember_width(width):
    _cmds().optionVar(intValue=(WIDTH_VAR, int(width)))


def _remember_hidden(names):
    cmds = _cmds()
    cmds.optionVar(remove=HIDDEN_VAR)
    for name in names:
        cmds.optionVar(stringValueAppend=(HIDDEN_VAR, name))


def _fit_layers():
    """The display layers' rows across the panel, on its colours (holder.fit_layers);
    asked every 300 ms while out - the panel is resized by the grip and Maya builds
    the rows again whenever layers change."""
    from . import holder
    import maya_hubstyle
    h = maya_hubstyle.TOKENS["track"].lstrip("#")
    holder.fit_layers(background=[int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])


def _maya_wants(controller):
    """A held editor's own workspaceControl shown again (Ctrl+A, Maya's toggles):
    hidden at once, and ours comes out on that tab, held."""
    from . import holder
    if controller.shown and _state()["held"].get("channels"):
        _fit_layers()
    for name, records in _state()["held"].items():
        for record in records:
            if record.get("ws") and holder.ws_visible(record["ws"]):
                holder._set_ws(record["ws"], False)
                controller.reveal(held=True, tab=name)
                _remember_tab(name)
                return


def _borrow(controller):
    from . import holder, look
    separate = holder.separate()
    held, hidden = {}, []
    for name in look.TABS:
        records = []
        for component, form in look.forms(name, separate):
            record = holder.take(component, form, controller.panel.pages[name])
            if record is not None:
                records.append(record)
                if record.get("ws"):
                    hidden.append(record["ws"])
        held[name] = records
    _state()["held"] = held
    _remember_hidden(hidden)
    holder.install()
    _mount_box(controller, held.get("channels") or [])
    return held


def _mount_box(controller, records):
    """Our Channel Box over Maya's Layer Editor (maya_channelbox, 2026-10-18). Never
    fatal: a box that cannot mount leaves Maya's Channel Box in place."""
    try:
        import maya_channelbox
        if maya_channelbox.enabled() and records:
            maya_channelbox.mount(controller.panel, records, getattr(controller.panel, "ui", 1.0))
    except Exception:                                        # noqa: BLE001
        print("SkeldarAnim: our Channel Box could not mount - Maya's stays")
        print(traceback.format_exc())
        try:
            import maya_channelbox
            maya_channelbox.unmount()
        except Exception:                                    # noqa: BLE001
            pass


def rebuild():
    """The panel built again (our Channel Box switched on or off)."""
    drop_edge()
    return ensure_edge()


def give_back():
    """Every borrowed form back where it came from; Maya's procs again. Safe to call
    any time - it acts only on what is held."""
    from . import holder
    try:                                    # ours away first: Maya's forms back in the page
        import maya_channelbox
        maya_channelbox.unmount()
    except Exception:                                        # noqa: BLE001
        print(traceback.format_exc())
    held = _state().get("held") or {}
    _state()["held"] = {}
    gone = 0
    try:                                    # Maya's greys back on what goes back
        import maya_hubqt
        from . import skin
        for records in held.values():
            for record in records:
                w = holder.widget(record.get("form"))
                if w is not None:
                    skin.recolor(w, maya_hubqt.qt().QtGui, back=True)
    except Exception:                                        # noqa: BLE001
        pass
    for records in held.values():
        for record in records:
            try:
                if holder.give(record):
                    gone += 1
            except Exception:                                # noqa: BLE001
                print(traceback.format_exc())
    holder.uninstall()
    from . import skin
    skin.channel_box(False)
    holder.unfit_layers()
    return gone


def _show_hidden():
    """Maya's controls an earlier session of ours left hidden, shown again."""
    from . import holder
    names = _var(HIDDEN_VAR) or []
    if isinstance(names, str):
        names = [names]
    for name in names:
        if _cmds().workspaceControl(name, exists=True):
            holder._set_ws(name, True)
    _cmds().optionVar(remove=HIDDEN_VAR)


def ensure_edge():
    cmds = _cmds()
    if cmds.about(batch=True):
        return None
    edge = _state().get("edge")
    if edge is not None and edge.alive():
        return edge
    drop_edge()
    from . import edge as edge_module, look, panel
    import maya_hubmotion
    import maya_hubstyle
    edge_module.destroy_all()
    ui = cmds.mayaDpiSetting(q=True, realScaleValue=True) or 1.0

    def make(parent, on_tab, on_pin, on_width):
        return panel.make(parent, ui, maya_hubstyle.TOKENS, motion=maya_hubmotion.enabled(),
                          on_tab=on_tab, on_pin=on_pin, on_width=on_width)

    def on_tab(value):
        _remember_tab(value)
        refresh()

    from . import holder
    controller = edge_module.SideEdge(make, width=_var(WIDTH_VAR, look.WIDTH), scale=ui,
                                      on_tab=on_tab, on_width=_remember_width, tick=_maya_wants,
                                      on_reveal=refresh, selected=_has_selection)
    controller.panel.set_tab(tab())
    _state()["edge"] = controller
    try:
        _borrow(controller)
        _skin(controller, ui)
        _fit(controller)
        _start_job()
        controller.selection_changed()          # something selected already: out
    except Exception:                                        # noqa: BLE001
        print("SkeldarAnim: the side panel could not take Maya's editors - Maya's are back")
        print(traceback.format_exc())
        drop_edge()
        _show_hidden()
        return None
    return controller


def _skin(edge, ui):
    """The pages and Maya's editors in them in the Time Bar's colours (2026-10-17).
    Never fatal: a skin that fails leaves Maya's colours."""
    try:
        import maya_hubqt
        from . import skin
        skin.apply(edge.panel.stack, maya_hubqt.qt().QtGui, ui)
        skin.channel_box(True)
    except Exception:                                        # noqa: BLE001
        print(traceback.format_exc())


def _recolor(edge):
    """Maya's filled greys swapped again - the Attribute Editor builds new widgets
    for every node it shows."""
    try:
        import maya_hubqt
        from . import skin
        skin.recolor(edge.panel.stack, maya_hubqt.qt().QtGui)
    except Exception:                                        # noqa: BLE001
        pass


def _fit(edge):
    """The panel at least as wide as Maya's borrowed forms ask now - the Attribute
    Editor asks more once it shows a node (308 px empty, 648 px on a mesh, live)."""
    from . import holder, look
    widths = []
    for records in (_state().get("held") or {}).values():
        for record in records:
            w = holder.widget(record["form"])
            if w is not None:
                widths.append(w.minimumSizeHint().width())
    least = look.min_width_px(widths, getattr(edge.panel, "ui", 1.0))
    if least > edge.least:
        edge.least = least
        edge.place()


def refresh():
    """What the panel shows brought up to date: Maya defers both editors' updates
    while their own controls are hidden, so the panel asks when it is out."""
    edge = _state().get("edge")
    if edge is None or not edge.alive() or not edge.shown:
        return
    from . import holder
    if edge.panel.tab == "attributes":
        holder.refresh_attribute_editor()
    else:
        holder.update_channel_box()
        try:
            import maya_channelbox
            maya_channelbox.refresh()
        except Exception:                                    # noqa: BLE001
            pass
    _fit(edge)
    _recolor(edge)
    edge.repaint_all()


def _start_job():
    """A SelectionChanged callback while the panel holds Maya's editors (removed by
    drop_edge): the panel comes out with a selection and the Attribute Editor
    follows it. OpenMaya's event callback, not a scriptJob: Maya runs scriptJobs
    only when it is idle, and playback is never idle - the panel stayed in while
    the animator selected during playback (2026-10-17, measured: a timeChanged
    scriptJob fired 0 times in 25 s of playback)."""
    _kill_job()
    try:
        import maya.OpenMaya as om
        _state()["callback"] = om.MEventMessage.addEventCallback(
            "SelectionChanged", lambda *args: _on_selection())
    except Exception:                                        # noqa: BLE001
        _state()["callback"] = None
        try:
            _state()["job"] = _cmds().scriptJob(event=["SelectionChanged", _on_selection],
                                                killWithScene=False)
        except Exception:                                    # noqa: BLE001
            _state()["job"] = None


def playing():
    try:
        return bool(_cmds().play(q=True, state=True))
    except Exception:                                        # noqa: BLE001
        return False


def _on_selection():
    """After Maya's own selection handlers (deferred): theirs ran last and left the
    Attribute Editor empty when ours ran first (measured live 2026-10-17)."""
    def later():
        try:
            edge = _state().get("edge")
            if edge is not None and edge.alive() and edge.selection_changed():
                return                          # brought out: the reveal refreshed it
            refresh()
        except Exception:                                    # noqa: BLE001
            print(traceback.format_exc())
    try:
        if playing():
            later()          # playback starves the idle queue: now, or never (2026-10-17)
        else:
            _cmds().evalDeferred(later, lowestPriority=True)
    except Exception:                                        # noqa: BLE001
        later()


def _kill_job():
    callback = _state().pop("callback", None)
    if callback is not None:
        try:
            import maya.OpenMaya as om
            om.MMessage.removeCallback(callback)
        except Exception:                                    # noqa: BLE001
            pass
    job = _state().pop("job", None)
    if job:
        try:
            cmds = _cmds()
            if cmds.scriptJob(exists=job):
                cmds.scriptJob(kill=job, force=True)
        except Exception:                                    # noqa: BLE001
            pass


def drop_edge():
    """The forms given back FIRST - deleting the host would delete Maya's editors
    with it - then the windows."""
    _kill_job()
    give_back()
    edge = _state().pop("edge", None)
    if edge is not None:
        try:
            edge.destroy()
        except Exception:                                    # noqa: BLE001
            pass


MESSAGES = {
    "maya": "Maya's Channel Box and Attribute Editor are back in place",
    "edge": "Side panel at the right edge - rest the mouse on the right of Maya's window",
}


def set_mode(choice):
    from . import look
    choice = look.mode_from(choice)
    _cmds().optionVar(stringValue=(MODE_VAR, choice))
    if choice == "edge":
        if ensure_edge() is None:
            _cmds().optionVar(stringValue=(MODE_VAR, "maya"))
            return "The side panel could not be built - see the Script Editor"
    else:
        drop_edge()
        _show_hidden()
    return MESSAGES[choice]


def ensure():
    """The mode the animator chose, standing (the hub's build calls it)."""
    if mode() == "edge":
        return ensure_edge()
    _show_hidden()
    return None


def toggle():
    return set_mode("maya" if mode() == "edge" else "edge")


def show_tab(value):
    """Out on `value`'s page, held (a hotkey); the panel switched on first if off."""
    from . import look
    value = look.tab_from(value)
    edge = _state().get("edge")
    if edge is None or not edge.alive():
        set_mode("edge")
        edge = _state().get("edge")
    if edge is None:
        return "The side panel is not available"
    _remember_tab(value)
    edge.reveal(held=True, tab=value)
    return "Side panel: " + dict((t, l) for l, t in look.TAB_LABELS)[value]
