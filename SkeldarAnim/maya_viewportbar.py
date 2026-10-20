"""The viewport's menu and icon bar in the hub's look (2026-10-20).

The animator, with a picture of Maya's View / Shading / Lighting / Show /
Renderer / Panels row and its icon bar: «А вот эту вот стандартную меню от
вьюпорта камеры мы можем заменить на наш дизайн?», then, after three mockups of
our own bar: «Давай сделаем просто рескин стандартного меню» - colours and
icons, Maya's bar itself kept.

What a model panel is made of (measured 2026-10-20 in a GUI Maya 2027.2):

    modelPanel4                 QmayaLayoutWidget (the panel)
      QmodelPanelMenuBar        View, Shading, ... (its QMenus are its children)
      modelPanel4               QmayaLayoutWidget
        modelEditorIconBar      a frameLayout holding a flowLayout of:
          iconTextButtonNN      the 13 px collapse bars (ShortOpenBar.png)
          formLayoutNN          a group: QmayaIconTextButton / CheckBox (28 px)
          formLayout (last)     exposure, gamma, the colour-management toggle
                                (a symbolCheckBox) and its optionMenu

So the reskin is a style sheet on each panel's widget (scoped to the bar's
classes, never a blanket QWidget rule - trap 98) and Maya's own icons of that
bar drawn into a folder of ours, its buttons pointed there by full path
(maya_mayaicons' way: a file in prefs/icons never reaches Maya's buttons): our
vector redrawing of Maya's icon (maya_viewportbar_art) where there is one, Maya's
own recoloured otherwise. Off gives every sheet and image back.

    enabled() / set_enabled(on)   ⋮ -> Viewport bar (on by default), at once
    ensure()                      at the hub's build: skin the panels, watch
    sheet(scale)                  the style sheet (pure)
"""

import os

import maya_hubstyle as hubstyle

OPTIONVAR = "skeldarViewportBar"
DEFAULT = True
STATE = "_skeldar_viewportbar"          # on sys (trap 111)
MARK = "skeldarVpBar"                   # a Qt property on a skinned panel
OLD_SHEET = "skeldarVpOldSheet"
WATCH_MS = 1500
FOLDER = "SkeldarViewportIcons"
T = hubstyle.TOKENS

#  the bar's image-carrying controls and their image flags
KINDS = (("iconTextButton", ("image1",)),
         ("iconTextCheckBox", ("image1",)),
         ("symbolCheckBox", ("onImage", "offImage")),
         ("symbolButton", ("image",)))
SIZES = ("", "_150", "_200")

CHECKED = "#3a2a1f"                     # a toggle that is on (the hub's lit well)
CHECKED_EDGE = "#6b4326"

_SHEET = """
QWidget[skeldarVpBar="1"] {{ background: {panel}; }}
QWidget[skeldarVpBar="1"] QmodelPanelMenuBar {{
    background: {panel}; color: {muted}; border: none;
    border-bottom: {b}px solid {track}; padding: {p2}px {p4}px; spacing: {p2}px; }}
QWidget[skeldarVpBar="1"] QmodelPanelMenuBar::item {{
    background: transparent; color: {muted}; padding: {p3}px {p8}px; border-radius: {r6}px; }}
QWidget[skeldarVpBar="1"] QmodelPanelMenuBar::item:selected,
QWidget[skeldarVpBar="1"] QmodelPanelMenuBar::item:pressed {{
    background: {hover}; color: {text}; }}
QWidget[skeldarVpBar="1"] QFrame#mayaLayoutInternalWidget {{ background: {panel}; border: none; }}
QWidget[skeldarVpBar="1"] QmayaIconTextButton,
QWidget[skeldarVpBar="1"] QmayaIconTextCheckBox,
QWidget[skeldarVpBar="1"] QmayaSymbolCheckBox {{
    background: transparent; border: {b}px solid transparent; border-radius: {r6}px; }}
QWidget[skeldarVpBar="1"] QmayaIconTextButton:hover,
QWidget[skeldarVpBar="1"] QmayaIconTextCheckBox:hover,
QWidget[skeldarVpBar="1"] QmayaSymbolCheckBox:hover {{
    background: {hover}; border-color: {line}; }}
QWidget[skeldarVpBar="1"] QmayaIconTextButton:pressed,
QWidget[skeldarVpBar="1"] QmayaIconTextCheckBox:pressed {{ background: {active}; }}
QWidget[skeldarVpBar="1"] QmayaIconTextCheckBox:checked {{
    background: {checked}; border-color: {checked_edge}; border-bottom: {b2}px solid {accent}; }}
QWidget[skeldarVpBar="1"] QmayaIconTextButton[skeldarVpSep="1"],
QWidget[skeldarVpBar="1"] QmayaIconTextButton[skeldarVpSep="1"]:hover {{
    background: transparent; border-color: transparent; }}
QWidget[skeldarVpBar="1"] QmayaFloatField {{
    background: {track}; color: {text}; border: {b}px solid {line};
    border-radius: {r5}px; padding: 0 {p4}px; selection-background-color: {select}; }}
QWidget[skeldarVpBar="1"] QmayaFloatField:focus {{ border-color: {accent}; }}
QWidget[skeldarVpBar="1"] QmayaOptionMenu {{
    background: {track}; color: {text}; border: {b}px solid {line};
    border-radius: {r6}px; padding: 0 {p8}px; }}
QWidget[skeldarVpBar="1"] QmayaOptionMenu:hover {{ border-color: {muted}; }}
QWidget[skeldarVpBar="1"] QmayaOptionMenu::drop-down {{ border: none; width: {p20}px; }}
QWidget[skeldarVpBar="1"] QmayaOptionMenu::down-arrow {{ image: url({chevron}); width: {p10}px; height: {p10}px; }}
QWidget[skeldarVpBar="1"] QmayaOptionMenu QAbstractItemView {{
    background: {card}; color: {text}; border: {b}px solid {line};
    selection-background-color: {active}; selection-color: {accent_text}; }}
"""


#  Maya's panel menus (the drop-downs of View, Shading, ...) stay Maya's: their
#  rows are drawn by Maya's own code in fixed greys - a style sheet changed their
#  padding only, a palette their left gutter only (measured 2026-10-20), and Maya
#  empties a menu's sheet as it builds its rows. A half-recoloured menu reads
#  worse than Maya's, so they are left alone.

#  a group's well: on the group itself, by its name (the panel's sheet did not
#  reach these plain QWidgets - measured; their own sheet does)
_GROUP_SHEET = ("#{name} {{ background: {card}; border: {b}px solid {track}; "
                "border-radius: {r8}px; }}")


def group_sheet(name, scale=1.0):
    """A group's well (pure)."""
    values = _values(scale)
    values["name"] = name
    return _GROUP_SHEET.format(**values)


def _values(scale, chevron=""):
    def px(value):
        return max(1, int(round(value * scale)))
    values = dict(T)
    values.update(active=T["card_active"], checked=CHECKED,
                  checked_edge=CHECKED_EDGE, select="#5a3922",
                  chevron=(chevron or "").replace("\\", "/"))
    for name, value in (("b", 1), ("b2", 2), ("p2", 2), ("p3", 3), ("p4", 4),
                        ("p6", 6), ("p8", 8), ("p10", 10), ("p20", 20), ("r5", 5),
                        ("r6", 6), ("r8", 8)):
        values[name] = px(value)
    return values


def sheet(scale=1.0, chevron=""):
    """The bar's style sheet at `scale` (Maya's style sheet pixels are
    PHYSICAL, trap 98). Every rule is under the panel's mark. `chevron`: the
    drop-down arrow's image (a file of ours, forward slashes)."""
    values = _values(scale, chevron)
    return _SHEET.format(**values)


CHEVRON = "skeldarVpChevron.png"
CHEVRON_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
               '<path d="M6 9l6 6 6-6" fill="none" stroke="{0}" stroke-width="2.4" '
               'stroke-linecap="round" stroke-linejoin="round"/></svg>')


def is_separator(image):
    """A bar's 13 px collapse handle (Maya draws them with these images)."""
    return bool(image) and os.path.basename(image).lower().startswith(
        ("shortopenbar", "shortclosebar", "openbar", "closebar"))


def pointed(image, folder, have, on):
    """The image a bar button should carry (maya_mayaicons' rule): on, an icon
    we wrote points into `folder`; off, ours goes back to its bare name; None =
    leave it."""
    import maya_mayaicons
    return maya_mayaicons.pointed(image, folder, have, on)


# ------------------------------------------------------------------- maya

def _cmds():
    import maya.cmds as cmds
    return cmds


def _qt():
    from PySide6 import QtCore, QtGui, QtWidgets
    return QtCore, QtGui, QtWidgets


def enabled():
    try:
        cmds = _cmds()
        if not cmds.optionVar(exists=OPTIONVAR):
            return DEFAULT
        return bool(cmds.optionVar(query=OPTIONVAR))
    except Exception:                                        # noqa: BLE001
        return False


def _state():
    import sys
    state = getattr(sys, STATE, None)
    if state is None:
        state = {"skinned": set()}
        setattr(sys, STATE, state)
    return state


def folder():
    cmds = _cmds()
    return os.path.normpath(os.path.join(cmds.internalVar(userAppDir=True),
                                         cmds.about(version=True), FOLDER))


def _scale():
    try:
        return float(_cmds().mayaDpiSetting(query=True, realScaleValue=True) or 1.0)
    except Exception:                                        # noqa: BLE001
        return 1.0


def _panel_widget(panel):
    """The panel's top Qt widget, found afresh (trap 135)."""
    from maya import OpenMayaUI
    from shiboken6 import wrapInstance
    _, _, QtWidgets = _qt()                                  # noqa: N806
    ptr = OpenMayaUI.MQtUtil.findControl(panel)
    if not ptr:
        return None
    return wrapInstance(int(ptr), QtWidgets.QWidget)


def panels():
    try:
        return list(_cmds().getPanel(type="modelPanel") or [])
    except Exception:                                        # noqa: BLE001
        return []


def _all_controls():
    """{kind: every control of it, by full path} - one lsUI a kind."""
    cmds = _cmds()
    return dict((kind, cmds.lsUI(type=kind, long=True) or []) for kind, _ in KINDS)


def bar_controls(panel, listed=None):
    """(kind, flags, full path) of every image control in `panel`'s icon bar."""
    cmds = _cmds()
    listed = listed if listed is not None else _all_controls()
    try:
        bar = cmds.modelPanel(panel, query=True, barLayout=True)
    except Exception:                                        # noqa: BLE001
        return []
    if not bar:
        return []
    prefix = bar + "|"
    out = []
    for kind, flags in KINDS:
        for control in listed.get(kind, ()):
            if control.startswith(prefix):
                out.append((kind, flags, control))
    return out


def _images(controls):
    """The bare file names the bar buttons carry, wherever they point."""
    cmds = _cmds()
    names = set()
    for kind, flags, control in controls:
        command = getattr(cmds, kind)
        for flag in flags:
            try:
                image = command(control, query=True, **{flag: True})
            except Exception:                                # noqa: BLE001
                continue
            if image:
                names.add(os.path.basename(image.replace("\\", "/")))
    return names


SIZE_PX = {"": 16, "_150": 24, "_200": 32}      # Maya's icon at each display scale
STAMP = "skeldarVpArt.txt"


def drawn_size(stem, size, image):
    """The pixel size our drawing of `stem` takes at `size` (pure): Maya's own
    image's, else the nominal one."""
    if image is not None and not image.isNull():
        return max(image.width(), image.height())
    return SIZE_PX.get(size, 16)


def _fresh_folder(dest):
    """Our files written by an older drawing (or the first build's recolours)
    taken out, so the next pass draws them again."""
    import maya_viewportbar_art as art
    path = os.path.join(dest, STAMP)
    try:
        with open(path, encoding="utf-8") as handle:
            if handle.read().strip() == str(art.VERSION):
                return False
    except Exception:                                        # noqa: BLE001
        pass
    for name in os.listdir(dest):
        if name.lower().endswith(".png") and name != CHEVRON:
            try:
                os.remove(os.path.join(dest, name))
            except Exception:                                # noqa: BLE001
                pass
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(str(art.VERSION))
    return True


def write_icons(names, dest):
    """Each of the bar's icons `names` into `dest` at every size Maya has,
    once (a file already there is kept): our redrawing where there is one
    (maya_viewportbar_art, 2026-10-20), else Maya's own recoloured. Answers
    the files there."""
    import maya_mayaicons
    import maya_viewportbar_art as art
    _, QtGui, _ = _qt()                                      # noqa: N806
    os.makedirs(dest, exist_ok=True)
    _fresh_folder(dest)
    for name in sorted(names):
        ext = os.path.splitext(name)[1]
        stem = maya_mayaicons.base_stem(name)[0]
        for size in SIZES:
            filename = stem + size + (ext or ".png")
            path = os.path.join(dest, filename)
            if os.path.exists(path):
                continue
            image = QtGui.QImage(":/" + filename)
            try:
                if stem in art.ICONS:
                    new = art.render(stem, drawn_size(stem, size, image))
                elif image.isNull():
                    continue
                else:
                    new = maya_mayaicons.qimage_recoloured(image, filename)
                data = maya_mayaicons.png_bytes(new)
            except Exception:                                # noqa: BLE001
                continue
            with open(path, "wb") as handle:
                handle.write(data)
    write_chevron(dest)
    return frozenset(n for n in os.listdir(dest) if n.lower().endswith(".png"))


def write_chevron(dest):
    """The drop-down's arrow, drawn in the hub's muted grey."""
    path = os.path.join(dest, CHEVRON)
    if os.path.exists(path):
        return path
    QtCore, QtGui, _ = _qt()                                 # noqa: N806
    from PySide6 import QtSvg
    renderer = QtSvg.QSvgRenderer(QtCore.QByteArray(
        CHEVRON_SVG.format(T["muted"]).encode("utf-8")))
    image = QtGui.QImage(48, 48, QtGui.QImage.Format_ARGB32)
    image.fill(QtCore.Qt.transparent)
    painter = QtGui.QPainter(image)
    painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
    renderer.render(painter)
    painter.end()
    image.save(path)
    return path


def _repoint(controls, dest, have, on):
    cmds = _cmds()
    changed = 0
    for kind, flags, control in controls:
        command = getattr(cmds, kind)
        for flag in flags:
            try:
                image = command(control, query=True, **{flag: True})
                new = pointed(image, dest, have, on)
                if new is not None:
                    command(control, edit=True, **{flag: new})
                    changed += 1
            except Exception:                                # noqa: BLE001
                continue
    return changed


def _mark_parts(widget, controls):
    """The groups and the collapse handles marked for the sheet. Answers
    whether a mark is new (the sheet then has to be set again)."""
    _, _, QtWidgets = _qt()                                  # noqa: N806
    cmds = _cmds()
    new = False
    for kind, flags, control in controls:
        if kind != "iconTextButton":
            continue
        try:
            image = cmds.iconTextButton(control, query=True, image1=True)
        except Exception:                                    # noqa: BLE001
            continue
        if is_separator(image):
            leaf = control.rsplit("|", 1)[-1]
            for child in widget.findChildren(QtWidgets.QPushButton, leaf):
                if child.property("skeldarVpSep") != "1":
                    child.setProperty("skeldarVpSep", "1")
                    new = True
    for child in widget.findChildren(QtWidgets.QWidget):
        name = child.objectName()
        if name.startswith("formLayout") and type(child).__name__ == "QWidget":
            parent = child.parentWidget()
            if parent is not None and parent.objectName().startswith("flowLayout"):
                wanted = group_sheet(name, _scale())
                if child.styleSheet() != wanted:      # by what stands, not a mark
                    child.setProperty("skeldarVpGroup", "1")
                    #  a plain QWidget paints no style-sheet background without it
                    child.setAttribute(_qt()[0].Qt.WA_StyledBackground, True)
                    child.setStyleSheet(wanted)
                    new = True
    return new


def skin_panel(panel, dest=None, have=None, text=None, listed=None):
    """`panel`'s bar in our look. Answers True when it was skinned now. The
    sheet is set only when something changed: a watch tick restyles nothing."""
    widget = _panel_widget(panel)
    if widget is None:
        return False
    controls = bar_controls(panel, listed)
    if dest is not None and have is not None:
        _repoint(controls, dest, have, True)
    fresh = widget.property(MARK) != "1"
    if fresh:
        widget.setProperty(OLD_SHEET, widget.styleSheet() or "")
        widget.setProperty(MARK, "1")
    marked = _mark_parts(widget, controls)
    text = text if text is not None else sheet(_scale(), os.path.join(folder(), CHEVRON))
    if fresh or marked or widget.styleSheet() != text:
        widget.setStyleSheet(text)
    _state()["skinned"].add(panel)
    return fresh


def unskin_panel(panel, dest=None, have=None, listed=None):
    widget = _panel_widget(panel)
    controls = bar_controls(panel, listed)
    if dest is not None and have is not None:
        _repoint(controls, dest, have, False)
    if widget is None:
        return False
    for child in widget.findChildren(_qt()[2].QWidget):
        if child.property("skeldarVpGroup") == "1":
            child.setProperty("skeldarVpGroup", None)
            child.setStyleSheet("")
    if widget.property(MARK) == "1":
        widget.setStyleSheet(widget.property(OLD_SHEET) or "")
        widget.setProperty(MARK, None)
        widget.setProperty(OLD_SHEET, None)
    _state()["skinned"].discard(panel)
    return True


def apply_all():
    """Every model panel skinned (new icons written as they are met)."""
    dest = folder()
    listed = _all_controls()
    names = set()
    for panel in panels():
        names |= _images(bar_controls(panel, listed))
    have = write_icons(names, dest)
    text = sheet(_scale(), os.path.join(dest, CHEVRON))
    count = 0
    for panel in panels():
        try:
            skin_panel(panel, dest, have, text, listed)
            count += 1
        except Exception:                                    # noqa: BLE001
            continue
    _remember()
    return count


def remove_all():
    dest = folder()
    try:
        have = frozenset(n for n in os.listdir(dest) if n.lower().endswith(".png"))
    except Exception:                                        # noqa: BLE001
        have = frozenset()
    listed = _all_controls()
    count = 0
    for panel in panels():
        try:
            if unskin_panel(panel, dest, have, listed):
                count += 1
        except Exception:                                    # noqa: BLE001
            continue
    _state()["seen"] = {}
    return count


def signature(widget):
    """What tells a panel's bar apart from the one we skinned: the names of its
    flowLayouts (Maya makes the bar's controls anew when it rebuilds it, under
    new names) and our mark."""
    _, _, QtWidgets = _qt()                                  # noqa: N806
    flows = sorted(child.objectName() for child in widget.findChildren(QtWidgets.QWidget)
                   if child.objectName().startswith("flowLayout"))
    return (widget.property(MARK), tuple(flows))


def stale(panels_now, seen):
    """The panels whose bar is not the one we skinned (pure): `panels_now` and
    `seen` map a panel to its signature."""
    return sorted(name for name, sig in panels_now.items() if seen.get(name) != sig)


def _tick():
    """A panel Maya built later (a new layout, a torn-off view) or a bar it
    rebuilt skinned again. Nothing else is touched: a tick that finds every bar
    as it was costs a widget walk a panel (well under a millisecond), where a
    whole pass costs ~25 ms (measured 2026-10-20, four views)."""
    try:
        if not enabled():
            return
        state = _state()
        now = {}
        for panel in panels():
            widget = _panel_widget(panel)
            if widget is not None:
                now[panel] = signature(widget)
        if stale(now, state.get("seen", {})):
            apply_all()
    except Exception:                                        # noqa: BLE001
        pass


def _remember():
    """Each skinned panel's signature, so the watch can tell a rebuilt bar."""
    seen = {}
    for panel in panels():
        widget = _panel_widget(panel)
        if widget is not None:
            seen[panel] = signature(widget)
    _state()["seen"] = seen


def watch():
    QtCore, _, _ = _qt()                                     # noqa: N806
    unwatch()
    timer = QtCore.QTimer()
    timer.setInterval(WATCH_MS)
    timer.timeout.connect(_tick)
    timer.start()
    _state()["timer"] = timer


def unwatch():
    timer = _state().pop("timer", None)
    if timer is not None:
        try:
            timer.stop()
        except Exception:                                    # noqa: BLE001
            pass


def ensure():
    """At the hub's build: the bars skinned and watched while on, else every
    bar we skinned given back."""
    cmds = _cmds()
    if cmds.about(batch=True):
        return 0
    if not enabled():
        unwatch()
        return remove_all() if _state()["skinned"] else 0
    count = apply_all()
    watch()
    return count


def set_enabled(on):
    """⋮ -> Viewport bar: our look on every viewport's bar, at once; or Maya's."""
    on = bool(on)
    cmds = _cmds()
    cmds.optionVar(intValue=(OPTIONVAR, int(on)))
    if cmds.about(batch=True):
        return "Viewport bar %s" % ("on" if on else "off")
    if on:
        count = apply_all()
        watch()
        return "Viewport bar in our look - %d viewport%s" % (count, "" if count == 1 else "s")
    unwatch()
    count = remove_all()
    return "Viewport bar back to Maya's - %d viewport%s" % (count, "" if count == 1 else "s")


def reload_live():
    """After an install: the old module's watch stopped, the bars skinned by
    this module's sheet."""
    unwatch()
    return ensure()
