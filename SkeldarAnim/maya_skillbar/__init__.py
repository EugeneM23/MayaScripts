"""The skill bar (2026-10-19): the Time Bar's strip with pages of skills - F1 the Time Bar, F2-F12
pages of cells, each cell a skill (a section, a tool, a character, a pose card, a weapon, a Maya
command, a script, a shelf button).

The model lives in `<userAppDir>/SkeldarSkills/skills.json` (look, store); the strip draws it
(grid.py inside maya_timebar.bar); `page(n)` is what F1-F12 run; `aim` / `drop` let other panels'
drags put a skill on the bar. State on `sys` (trap 111).
Spec: docs/superpowers/specs/2026-10-19-skill-bar-design.md
"""

import sys
import traceback

from . import look, store


def _state():
    st = getattr(sys, "_skeldar_skillbar", None)
    if st is None:
        st = {"data": None, "path": None, "page": look.TIME_PAGE, "note": "", "memory": None}
        sys._skeldar_skillbar = st
    return st


def _cmds():
    import maya.cmds as cmds
    return cmds


def file_path():
    st = _state()
    if st["path"] is None:
        try:
            app = _cmds().internalVar(userAppDir=True)
        except Exception:                                    # noqa: BLE001
            app = None
        st["path"] = store.path_in(app) if app else ""
    return st["path"]


def data():
    """The model (read once a session; a test may hand in `use_memory`)."""
    st = _state()
    if st["data"] is not None and st.get("by") is not look:
        # read by the modules an update purged (the state outlives them on sys, trap 226): read
        # the file again, so a new build's model (a default page it adds) reaches this session
        if file_path():
            st["data"] = None
        else:
            st["data"], st["by"] = look.normalised(st["data"]), look
    if st["data"] is None:
        st["by"] = look
        path = file_path()
        if path:
            st["data"], st["note"] = store.read(path)
        else:
            st["data"] = look.defaults()
    return st["data"]


def set_data(new):
    """Keep `new` and write it to the file; answers the model kept."""
    st = _state()
    st["data"], st["by"] = look.normalised(new), look
    path = file_path()
    if path:
        try:
            store.write(path, st["data"])
        except Exception:                                    # noqa: BLE001
            traceback.print_exc()
    return st["data"]


def use_memory(model=None):
    """Tests: keep the model in memory only."""
    st = _state()
    st["path"] = ""
    st["data"] = look.normalised(model) if model is not None else look.defaults()
    st["by"] = look


def current_page():
    return _state()["page"]


def set_current_page(n):
    if n == look.TIME_PAGE or look.is_skill_page(n):
        _state()["page"] = n
        if look.is_skill_page(n):
            _state()["last_skill"] = n
    return _state()["page"]


def note():
    """What the read of the file said (a broken file kept aside), once."""
    st = _state()
    text, st["note"] = st["note"], ""
    return text


# ------------------------------------------------------------- F1-F12 and drags

FAR = "The skill bar lives in the Time Bar - ⋮ -> Time bar"


def strip():
    """The Time Bar's live strip, or None."""
    try:
        from maya_timebar import bar
        return bar.current()
    except Exception:                                        # noqa: BLE001
        return None


def page(n):
    """F1-F12: page n on the Time Bar. Hidden at the bottom edge, it comes out on that page (from
    the cursor's x, as a key set brings it); out, its wait for the hide begins again. Returns a
    line only when there is nothing to show it on."""
    if n != look.TIME_PAGE and not look.is_skill_page(n):
        return ""
    try:
        import maya_timebar
        if not maya_timebar.wanted():
            return FAR
        s = strip()
        if s is None:
            maya_timebar.ensure()
            s = strip()
        if s is None:
            return FAR
        edge = maya_timebar._state().get("edge")
        if edge is not None and edge.alive() and not edge.shown:
            s.skills.set_page(n)
            s._apply_page()
            edge.key_set()
            return ""
        s.show_page(n)
        if edge is not None and edge.alive():
            edge.key_set()
        return ""
    except Exception as error:                               # noqa: BLE001
        traceback.print_exc()
        return "Skill bar: %s" % error


def aim(gx, gy):
    """What a drag from another panel would hit on the bar at the global point: ("cell", n, r, c),
    ("tab", n) or None (also with no bar on screen)."""
    s = strip()
    if s is None:
        return None
    try:
        if not s.isVisible():
            return None
        return s.skill_aim(gx, gy)
    except RuntimeError:
        return None


def light(target):
    """The cell or tab a drag is over lit (None: nothing lit)."""
    s = strip()
    if s is not None:
        try:
            s.light_aim(target)
        except RuntimeError:
            pass


def drop(gx, gy, item):
    """`item` let go at the global point: onto the cell or tab there. Returns the line, or "" when
    the point is not on the bar."""
    target = aim(gx, gy)
    light(None)
    if not target or not look.valid_item(item):
        return ""
    return strip().place_skill(target, item)


def caption(label, target):
    return look.drop_caption(label, target)


# ------------------------------------------------------------- 1-0: the cells of a page

NUMBER_KEYS = ("1", "2", "3", "4", "5", "6", "7", "8", "9", "0")


def number_page():
    """The page the number keys run: the skill page shown, else the last one shown (F2 at first)."""
    st = _state()
    n = current_page()
    if look.is_skill_page(n):
        st["last_skill"] = n
        return n
    last = st.get("last_skill")
    return last if look.is_skill_page(last) else 2


def _typing_widget():
    """The focused text input, when there is one (a field, the Script Editor, a spin box): the
    number keys type there, they run nothing (2026-10-19, «если мы вводим какие-то значения в
    текстовые поля тогда скилы не должны срабатывать»)."""
    try:
        import maya_hubqt
        q = maya_hubqt.qt()
        widget = q.QtWidgets.QApplication.focusWidget()
    except Exception:                                        # noqa: BLE001
        return None
    if widget is None:
        return None
    W = q.QtWidgets
    text_kinds = (W.QLineEdit, W.QTextEdit, W.QPlainTextEdit, W.QAbstractSpinBox)
    if isinstance(widget, text_kinds):
        return widget
    if isinstance(widget, W.QAbstractItemView) and widget.state() == W.QAbstractItemView.EditingState:
        return widget
    return None


def _type_into(widget, key):
    """The digit the hotkey took, given to the field it was meant for."""
    try:
        import maya_hubqt
        q = maya_hubqt.qt()
        code = getattr(q.QtCore.Qt, "Key_" + key)
        for kind in (q.QtCore.QEvent.KeyPress, q.QtCore.QEvent.KeyRelease):
            event = q.QtGui.QKeyEvent(kind, code, q.QtCore.Qt.NoModifier, key)
            q.QtWidgets.QApplication.sendEvent(widget, event)
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()


def _cursor():
    try:
        import maya_hubqt
        p = maya_hubqt.qt().QtGui.QCursor.pos()
        return p.x(), p.y()
    except Exception:                                        # noqa: BLE001
        return 0, 0


DOUBLE_MS = 450        # a second press of the same number within this runs the skill


def _now_ms():
    import time
    return time.monotonic() * 1000.0


def _double_window():
    """Qt's double-click interval, kept within 250..DOUBLE_MS."""
    try:
        import maya_hubqt
        ms = maya_hubqt.qt().QtWidgets.QApplication.doubleClickInterval()
        return max(250.0, min(float(DOUBLE_MS), float(ms)))
    except Exception:                                        # noqa: BLE001
        return float(DOUBLE_MS)


def second_tap(index, now=None, window=None):
    """True when this press of number `index` follows its first within the window (2026-10-19, «скилы
    применялись по двойному клику на хоткей»). A first press arms the cell; a second runs it and
    disarms; any other number arms itself instead."""
    st = _state()
    now = _now_ms() if now is None else now
    window = _double_window() if window is None else window
    armed = st.get("armed")
    if armed and armed[0] == index and 0 <= now - armed[1] <= window:
        st["armed"] = None
        return True
    st["armed"] = (index, now)
    return False


def _arm(s, n, index):
    """The first press shown: the cell lit while the second is awaited."""
    try:
        if s is not None and s.isVisible() and s.skills.page() == n:
            s.skill_grid.arm((0, index), _double_window())
            return True
    except (RuntimeError, AttributeError):
        pass
    return False


def run_number(index):
    """1-0 (index 0-9), pressed twice: the skill in the first row's cell `index` of the number page.
    The first press lights the cell. Typing in a field: the digit goes there instead. The cell
    flashes and glows when the bar shows that page."""
    key = NUMBER_KEYS[index] if 0 <= index < len(NUMBER_KEYS) else ""
    field = _typing_widget()
    if field is not None:
        _state()["armed"] = None
        _type_into(field, key)
        return ""
    n = number_page()
    item = look.item_at(data(), n, 0, index)
    if not item:
        _state()["armed"] = None
        return "%s: no skill in cell %s of %s" % (key, key, look.fkey(n))
    s = strip()
    if not second_tap(index):
        if _arm(s, n, index):
            return ""
        from . import run as run_module
        return "%s - press %s again to run it" % (run_module.label(item), key)
    try:
        if s is not None and s.isVisible() and s.skills.page() == n:
            s.skill_grid.run_cell((0, index))
            return ""
    except RuntimeError:
        pass
    from . import run as run_module
    try:
        return run_module.run(item, _cursor()) or ""
    except Exception as error:                               # noqa: BLE001
        traceback.print_exc()
        return "%s: %s" % (run_module.label(item), error)
