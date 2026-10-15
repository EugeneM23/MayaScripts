"""Scene tabs: the bar above the viewport (2026-10-15).

A workspaceControl `skeldarSceneTabs` holding a QTabBar in the hub's colours:
a tab per scene, `*` on a modified one, x to close, "+" to open (a file, a
recent one, an empty tab), the right button for Save / Save As / Reload /
Show in Explorer / Close others, the middle button closes, the menu turns
tabs off or hides the bar. Maya replays the control's uiScript at startup,
which also installs the hooks.
Spec: docs/superpowers/specs/2026-10-15-scene-tabs-design.md
"""

import os
import sys
import traceback

import maya.cmds as cmds

from . import records, session

CONTROL = "skeldarSceneTabs"
LABEL = "Scene Tabs"
TABS_BAR_VAR = "skeldarSceneTabsBar"
ROOT_NAME = "skeldarSceneTabsRoot"
HEIGHT = 30


def _state():
    state = getattr(sys, "_skeldar_scenetabs_bar", None)
    if state is None:
        state = {"bar": None}
        sys._skeldar_scenetabs_bar = state
    return state


def plugin_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace("\\", "/")


def uiscript(root):
    root = root.replace("\\", "/").rstrip("/")
    return ("import sys\n_p = \"{0}\"\nif _p not in sys.path:\n    sys.path.insert(0, _p)\n"
            "from maya_scenetabs import bar\nbar.build()\n").format(root)


def say(message):
    if message and not cmds.about(batch=True):
        cmds.inViewMessage(assistMessage=message, position="topCenter", fade=True)
    print("Scene Tabs: %s" % message)
    return message


def ensure_docked():
    """The bar shown (made the first time, docked above the viewport) and the hooks on."""
    if cmds.about(batch=True):
        return ""
    if cmds.workspaceControl(CONTROL, exists=True):
        cmds.workspaceControl(CONTROL, edit=True, restore=True, visible=True)
    else:
        cmds.workspaceControl(CONTROL, label=LABEL, retain=False, floating=False,
                              dockToMainWindow=("top", False), heightProperty="fixed",
                              initialHeight=HEIGHT, uiScript=uiscript(plugin_root()))
    from . import hooks
    hooks.install()
    return CONTROL


def show():
    cmds.optionVar(intValue=(TABS_BAR_VAR, 1))
    return ensure_docked()


def hide_bar():
    cmds.optionVar(intValue=(TABS_BAR_VAR, 0))
    if cmds.workspaceControl(CONTROL, exists=True):
        cmds.workspaceControl(CONTROL, edit=True, visible=False)
    return "Scene tabs bar hidden - the Scene Tabs hotkey row (window.tabs) brings it back"


def stylesheet(tokens, scale):
    px = lambda value: "%dpx" % max(1, int(round(value * scale)))      # noqa: E731
    return (
        "QWidget#{root} {{ background: {panel}; }}"
        "QTabBar#skeldarSceneTabsTabs::tab {{ background: {card}; color: {text2}; padding: {p4} {p10};"
        " margin-right: {p2}; border: 1px solid {line}; border-bottom: none;"
        " border-top-left-radius: {p6}; border-top-right-radius: {p6}; }}"
        "QTabBar#skeldarSceneTabsTabs::tab:selected {{ background: {card_active}; color: {text};"
        " border-color: {accent}; }}"
        "QTabBar#skeldarSceneTabsTabs::tab:hover:!selected {{ background: {hover}; }}"
        "QToolButton#skeldarSceneTabsButton {{ color: {text2}; padding: {p2} {p8}; border: none; }}"
        "QToolButton#skeldarSceneTabsButton:hover {{ background: {hover}; color: {text}; }}"
    ).format(root=ROOT_NAME, p2=px(2), p4=px(4), p6=px(6), p8=px(8), p10=px(10), **tokens)


def bar_class():
    """The Qt class, made on first use (no Qt at import)."""
    import maya_hubqt
    q = maya_hubqt.qt()
    QtCore, QtWidgets = q.QtCore, q.QtWidgets

    class TabBar(QtWidgets.QWidget):

        def __init__(self, actions, parent=None):
            super(TabBar, self).__init__(parent)
            self.setObjectName(ROOT_NAME)
            self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
            self.actions = actions
            self.items = []
            self._filling = False
            row = QtWidgets.QHBoxLayout(self)
            row.setContentsMargins(4, 2, 4, 0)
            row.setSpacing(4)
            self.tabs = QtWidgets.QTabBar(self)
            self.tabs.setObjectName("skeldarSceneTabsTabs")
            self.tabs.setDocumentMode(True)
            self.tabs.setExpanding(False)
            self.tabs.setTabsClosable(True)
            self.tabs.setElideMode(QtCore.Qt.ElideMiddle)
            self.tabs.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            self.tabs.currentChanged.connect(self._current)
            self.tabs.tabCloseRequested.connect(self._close)
            self.tabs.customContextMenuRequested.connect(self._menu)
            self.tabs.installEventFilter(self)
            row.addWidget(self.tabs, 1)
            self.plus = self._button("+", "Open a scene in a new tab", self._plus_menu)
            self.more = self._button(u"⋮", "Scene tabs", self._more_menu)
            row.addWidget(self.plus)
            row.addWidget(self.more)
            self.timer = QtCore.QTimer(self)
            self.timer.setInterval(500)
            self.timer.timeout.connect(self.tick)
            self.timer.start()

        def _button(self, text, tip, opener):
            button = QtWidgets.QToolButton(self)
            button.setObjectName("skeldarSceneTabsButton")
            button.setText(text)
            button.setToolTip(tip)
            button.clicked.connect(lambda: opener(button))
            return button

        def populate(self, items):
            self._filling = True
            try:
                while self.tabs.count():
                    self.tabs.removeTab(0)
                for index, item in enumerate(items):
                    self.tabs.addTab(item["text"])
                    self.tabs.setTabToolTip(index, item["tip"])
                    if not item["closable"]:
                        #  the style decides the close button's side: clear both
                        for side in (QtWidgets.QTabBar.LeftSide, QtWidgets.QTabBar.RightSide):
                            if self.tabs.tabButton(index, side) is not None:
                                self.tabs.setTabButton(index, side, None)
                    if item["active"]:
                        self.tabs.setCurrentIndex(index)
                self.items = list(items)
            finally:
                self._filling = False

        def tick(self):
            """The stars kept current without repopulating (no flicker)."""
            fresh = self.actions.items()
            if [i["ns"] for i in fresh] != [i["ns"] for i in self.items]:
                self.populate(fresh)
                return
            for index, item in enumerate(fresh):
                if self.tabs.tabText(index) != item["text"]:
                    self.tabs.setTabText(index, item["text"])
            self.items = list(fresh)

        def _ns(self, index):
            return self.items[index]["ns"] if 0 <= index < len(self.items) else ""

        def _current(self, index):
            if not self._filling and self._ns(index):
                self.actions.switch(self._ns(index))

        def _close(self, index):
            if self._ns(index):
                self.actions.close(self._ns(index))

        def eventFilter(self, obj, event):
            if obj is self.tabs and event.type() == QtCore.QEvent.MouseButtonRelease \
                    and event.button() == QtCore.Qt.MiddleButton:
                point = event.position().toPoint() if hasattr(event, "position") else event.pos()
                namespace = self._ns(self.tabs.tabAt(point))
                if namespace:
                    self.actions.close(namespace)
                    return True
            return False

        def _menu(self, point):
            namespace = self._ns(self.tabs.tabAt(point))
            if not namespace:
                return
            a = self.actions
            maya_hubqt.run_menu(self.tabs, self.tabs.mapToGlobal(point), [
                ("Save", lambda: a.save(namespace)), ("Save As...", lambda: a.save_as(namespace)), None,
                ("Reload from disk", lambda: a.reload(namespace)),
                ("Show in Explorer", lambda: a.explore(namespace)), None,
                ("Close others", lambda: a.close_others(namespace))])

        def _plus_menu(self, button):
            a = self.actions
            rows = [("Open file...", a.open_file)]
            recent = a.recent()
            if recent:
                rows.append(None)
                rows.extend((os.path.basename(p), (lambda p=p: a.open_path(p))) for p in recent)
            rows.extend([None, ("Empty tab", a.empty_tab)])
            maya_hubqt.run_menu(button, button.mapToGlobal(button.rect().bottomLeft()), rows)

        def _more_menu(self, button):
            a = self.actions
            maya_hubqt.run_menu(button, button.mapToGlobal(button.rect().bottomLeft()),
                                [("Tabs off", a.tabs_off), ("Hide this bar", a.hide)])

    return TabBar


def _run(fn):
    try:
        message = fn()
    except Exception as exc:                                    # noqa: BLE001
        print(traceback.format_exc())
        message = "Scene Tabs: %s" % exc
    refresh()
    return say(message) if message else ""


class Actions(object):
    """What the bar's presses do in Maya."""

    def items(self):
        return records.bar_items(session.state(), cmds.file(q=True, sceneName=True) or "",
                                 bool(cmds.file(q=True, modified=True)))

    def switch(self, namespace):
        from . import switching
        return _run(lambda: switching.switch(namespace) and "Tab: %s" %
                    records.title(dict(records.tab(session.state(), namespace), modified=False)))

    def close(self, namespace):
        from . import opening
        return _run(lambda: opening.close_tab(namespace))

    def save(self, namespace):
        from . import saving
        return _run(lambda: saving.save_tab(namespace))

    def save_as(self, namespace):
        from . import saving
        return _run(lambda: saving.save_as(namespace))

    def reload(self, namespace):
        from . import opening
        return _run(lambda: opening.reload_tab(namespace))

    def explore(self, namespace):
        from . import opening
        return _run(lambda: opening.explore(namespace))

    def close_others(self, namespace):
        from . import opening
        return _run(lambda: opening.close_others(namespace))

    def open_file(self):
        found = cmds.fileDialog2(fileMode=1, caption="Open in a new tab",
                                 fileFilter="Maya Scenes (*.ma *.mb)") or []
        return self.open_path(found[0]) if found else ""

    def open_path(self, path):
        from . import opening
        return _run(lambda: opening.open_tab(path))

    def recent(self):
        if not cmds.optionVar(exists="RecentFilesList"):
            return []
        found = cmds.optionVar(q="RecentFilesList") or []
        return [p for p in reversed(found) if os.path.splitext(p)[1].lower() in records.FILE_TYPES][:10]

    def empty_tab(self):
        from . import opening
        return _run(opening.new_tab)

    def tabs_off(self):
        from . import opening
        return _run(opening.tabs_off)

    def hide(self):
        return _run(hide_bar)


def build():
    """The uiScript body: the bar inside the workspaceControl."""
    import maya_hubqt
    import maya_hubstyle
    q = maya_hubqt.qt()
    host = maya_hubqt.host_widget(CONTROL) if q is not None else None
    if host is None:
        return None
    for old in host.findChildren(q.QtWidgets.QWidget, ROOT_NAME):
        old.setParent(None)
        old.deleteLater()
    widget = bar_class()(Actions())
    scale = cmds.mayaDpiSetting(q=True, realScaleValue=True) or 1.0
    widget.setStyleSheet(stylesheet(maya_hubstyle.TOKENS, scale))
    host.layout().addWidget(widget)
    _state()["bar"] = widget
    refresh()
    from . import hooks
    hooks.install()
    return widget


def refresh():
    widget = _state()["bar"]
    if widget is None:
        return
    try:
        import maya_hubqt
        if not maya_hubqt.qt().shiboken.isValid(widget):
            _state()["bar"] = None
            return
        widget.populate(widget.actions.items())
    except RuntimeError:
        _state()["bar"] = None
