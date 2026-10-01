"""The UE Bridge list's drag (2026-10-01): a row pressed and carried out of the
list drops its animation onto the rig under the cursor, or onto a new rig.
Offscreen, on a real QListWidget (what Maya's textScrollList is) and a fake
scene - the viewport half is verify_uebridge_drag.py's.

Spec: docs/superpowers/specs/2026-10-01-uebridge-drag-to-viewport-design.md
"""
import collections
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    import maya_hubqt
    QT = maya_hubqt.qt()
except Exception:                                            # noqa: BLE001
    QT = None

from maya_uebridge import listdrag

Rec = collections.namedtuple("Rec", "name package")


class FakeScene(object):

    def __init__(self):
        self.log = []
        self.aim = dict(kind="rig", rig="Manny_Rig1", label="Manny_Rig1",
                        text="retarget onto Manny_Rig1")

    def scale(self):
        return 1.0

    def snapshot(self):
        self.log.append(("snapshot",))
        return ["the rigs"]

    def target(self, gx, gy, snap):
        self.log.append(("target", snap))
        return self.aim

    def over_hub(self, gx, gy):
        return False

    def drop(self, records, aim):
        names = [r.name for r in records]
        self.log.append(("drop", names[0] if len(names) == 1 else names, aim["kind"]))
        return "exporting %s from the editor..." % ", ".join(names)

    def say(self, text):
        self.log.append(("say", text))


class Caption(unittest.TestCase):

    def test_a_rig_or_a_new_rig_is_good_and_names_the_clip(self):
        self.assertEqual(listdrag.caption("A_Jump", dict(kind="rig", text="retarget onto X")),
                         ("A_Jump · retarget onto X", True))
        self.assertEqual(listdrag.caption("A_Jump", dict(kind="new_rig", text="a new Manny [rig]")),
                         ("A_Jump · a new Manny [rig]", True))

    def test_several_onto_a_rig_name_the_first(self):
        self.assertEqual(listdrag.caption(["A_Jump", "A_Walk", "A_Run"],
                                          dict(kind="rig", text="retarget onto X")),
                         ("A_Jump · retarget onto X · first of 3", True))

    def test_several_onto_the_floor_are_a_square_of_new_rigs(self):
        aim = dict(kind="new_rig", label="Creep [rig]", point=(120.4, 0.0, -35.6),
                   text="a new Creep [rig] · floor (120, -36)")
        self.assertEqual(listdrag.caption(["A_Jump", "A_Walk"], aim),
                         ("2 animations · 2 new Creep [rig] in a square · floor (120, -36)", True))
        aim = dict(kind="new_rig", label="Manny [rig]", point=None, text="a new Manny [rig]")
        self.assertEqual(listdrag.caption(["A", "B", "C"], aim),
                         ("3 animations · 3 new Manny [rig] in a square", True))

    def test_one_in_a_list_reads_as_one(self):
        self.assertEqual(listdrag.caption(["A_Jump"], dict(kind="rig", text="retarget onto X")),
                         ("A_Jump · retarget onto X", True))

    def test_nothing_says_why_muted(self):
        self.assertEqual(listdrag.caption("A_Jump", dict(kind="none", text="no target - drop")),
                         ("no target - drop", False))
        self.assertEqual(listdrag.caption("A_Jump", {}), ("no target", False))


@unittest.skipIf(QT is None, "no Qt")
class Drag(unittest.TestCase):

    def setUp(self):
        self.app = QT.QtWidgets.QApplication.instance() or QT.QtWidgets.QApplication([])
        self.list = QT.QtWidgets.QListWidget()
        self.list.addItems(["A_Jump", "A_Walk", "A_Run"])
        self.list.resize(300, 200)
        self.list.move(3000, 3000)
        self.list.show()
        self.addCleanup(self.list.deleteLater)
        self.records = [Rec("A_Jump", "/Game/A_Jump"), Rec("A_Walk", "/Game/A_Walk"),
                        Rec("A_Run", "/Game/A_Run")]
        self.scene = FakeScene()
        self.drag = listdrag.attach_widget(self.list, lambda: list(self.records), self.scene)
        self.E, self.L, self.R, self.N = (QT.QtCore.QEvent, QT.QtCore.Qt.LeftButton,
                                          QT.QtCore.Qt.RightButton, QT.QtCore.Qt.NoButton)

    def row(self, index):
        return self.list.visualItemRect(self.list.item(index)).center()

    def mouse(self, kind, local, button, buttons):
        port = self.list.viewport()
        g = port.mapToGlobal(local)
        event = QT.QtGui.QMouseEvent(kind, QT.QtCore.QPointF(local), QT.QtCore.QPointF(g),
                                     button, buttons, QT.QtCore.Qt.NoModifier)
        QT.QtWidgets.QApplication.sendEvent(port, event)

    def far(self, local):
        return local + QT.QtCore.QPoint(-900, 500)

    def acts(self, name):
        return [e for e in self.scene.log if e[0] == name]

    def selected(self):
        return [item.text() for item in self.list.selectedItems()]

    def test_press_drag_release_outside_drops_the_pressed_row(self):
        start = self.row(1)
        self.mouse(self.E.MouseButtonPress, start, self.L, self.L)
        self.mouse(self.E.MouseMove, start + QT.QtCore.QPoint(30, 0), self.N, self.L)
        self.assertIsNotNone(self.drag.dragging())
        self.mouse(self.E.MouseMove, self.far(start), self.N, self.L)
        self.mouse(self.E.MouseButtonRelease, self.far(start), self.L, self.N)
        self.assertIsNone(self.drag.dragging())
        self.assertEqual(self.acts("drop"), [("drop", "A_Walk", "rig")])
        self.assertEqual(self.acts("target"), [("target", ["the rigs"])])
        self.assertEqual(self.drag.status_text, "exporting A_Walk from the editor...")
        self.assertEqual(self.selected(), ["A_Walk"])

    def test_a_click_is_no_drag_and_the_list_selects_as_before(self):
        start = self.row(2)
        self.mouse(self.E.MouseButtonPress, start, self.L, self.L)
        self.mouse(self.E.MouseButtonRelease, start, self.L, self.N)
        self.assertEqual(self.acts("drop"), [])
        self.assertEqual(self.selected(), ["A_Run"])

    def test_moves_while_held_are_eaten_the_pressed_row_travels(self):
        """Qt's single selection would follow the held mouse to another row;
        the drag carries the row PRESSED."""
        start = self.row(0)
        self.mouse(self.E.MouseButtonPress, start, self.L, self.L)
        self.mouse(self.E.MouseMove, self.row(2), self.N, self.L)
        self.assertEqual(self.selected(), ["A_Jump"])
        self.assertEqual(self.drag.dragging().name, "A_Jump")

    def test_the_ghost_says_off_the_hub_on_the_list_and_the_target_off_it(self):
        start = self.row(1)
        self.mouse(self.E.MouseButtonPress, start, self.L, self.L)
        self.mouse(self.E.MouseMove, start + QT.QtCore.QPoint(30, 0), self.N, self.L)
        ghost = self.drag.ghost()
        self.assertEqual((ghost.text, ghost.good), (listdrag.OFF_HUB, False))
        self.drag.caption_at(self.list.viewport().mapToGlobal(self.far(start)), force=True)
        self.assertEqual((ghost.text, ghost.good), ("A_Walk · retarget onto Manny_Rig1", True))
        self.assertIs(type(ghost), maya_hubqt.ghost_class())

    def test_escape_cancels(self):
        start = self.row(0)
        self.mouse(self.E.MouseButtonPress, start, self.L, self.L)
        self.mouse(self.E.MouseMove, start + QT.QtCore.QPoint(40, 0), self.N, self.L)
        key = QT.QtGui.QKeyEvent(self.E.KeyPress, QT.QtCore.Qt.Key_Escape, QT.QtCore.Qt.NoModifier)
        QT.QtWidgets.QApplication.sendEvent(self.list, key)
        self.assertIsNone(self.drag.dragging())
        self.mouse(self.E.MouseButtonRelease, self.far(start), self.L, self.N)
        self.assertEqual(self.acts("drop"), [])
        self.assertIn(("say", "cancelled"), self.scene.log)

    def test_the_right_button_cancels(self):
        start = self.row(0)
        self.mouse(self.E.MouseButtonPress, start, self.L, self.L)
        self.mouse(self.E.MouseMove, start + QT.QtCore.QPoint(40, 0), self.N, self.L)
        self.mouse(self.E.MouseButtonPress, start + QT.QtCore.QPoint(40, 0), self.R,
                   self.L | self.R)
        self.assertIsNone(self.drag.dragging())
        self.mouse(self.E.MouseButtonRelease, self.far(start), self.L, self.N)
        self.assertEqual(self.acts("drop"), [])

    def test_a_release_on_the_hub_does_nothing(self):
        self.scene.over_hub = lambda gx, gy: True
        self.drag.drop_at(10, 10, self.records[0])
        self.assertEqual(self.acts("drop"), [])
        self.assertEqual(self.acts("target"), [])

    def test_a_release_back_on_the_list_does_nothing(self):
        point = self.list.viewport().mapToGlobal(self.row(2))
        self.drag.drop_at(point.x(), point.y(), self.records[0])
        self.assertEqual(self.acts("drop"), [])

    def test_off_every_viewport_nothing_and_it_says_why(self):
        self.scene.aim = dict(kind="none", text="no target - drop onto a viewport")
        self.drag.drop_at(10, 10, self.records[0])
        self.assertEqual(self.acts("drop"), [])
        self.assertIn(("say", "no target - drop onto a viewport"), self.scene.log)

    def test_a_drop_without_a_drag_reads_the_rigs_itself(self):
        """What a verify drives: drop_at with no mouse behind it."""
        self.scene.aim = dict(kind="new_rig", text="a new Manny [rig]")
        self.drag.drop_at(10, 10, self.records[2])
        self.assertEqual(self.acts("snapshot"), [("snapshot",)])
        self.assertEqual(self.acts("drop"), [("drop", "A_Run", "new_rig")])

    def test_a_drop_that_raises_says_so(self):
        def boom(record, aim):
            raise RuntimeError("the editor said no")
        self.scene.drop = boom
        self.drag.drop_at(10, 10, self.records[0])
        self.assertIn("the editor said no", self.drag.status_text)

    def test_a_press_below_the_rows_starts_nothing(self):
        empty = QT.QtCore.QPoint(150, 190)
        self.assertFalse(self.list.indexAt(empty).isValid())
        self.mouse(self.E.MouseButtonPress, empty, self.L, self.L)
        self.mouse(self.E.MouseMove, empty + QT.QtCore.QPoint(-60, 0), self.N, self.L)
        self.assertIsNone(self.drag.dragging())

    def test_a_row_without_a_record_starts_nothing(self):
        self.records[:] = self.records[:1]
        start = self.row(2)
        self.mouse(self.E.MouseButtonPress, start, self.L, self.L)
        self.mouse(self.E.MouseMove, start + QT.QtCore.QPoint(40, 0), self.N, self.L)
        self.assertIsNone(self.drag.dragging())

    def test_attaching_again_replaces_the_filter(self):
        again = listdrag.attach_widget(self.list, lambda: list(self.records), self.scene)
        start = self.row(1)
        self.mouse(self.E.MouseButtonPress, start, self.L, self.L)
        self.mouse(self.E.MouseMove, start + QT.QtCore.QPoint(30, 0), self.N, self.L)
        self.mouse(self.E.MouseButtonRelease, self.far(start), self.L, self.N)
        self.assertEqual(len(self.acts("drop")), 1)
        self.assertIsNone(self.drag.dragging())
        self.assertIsNot(again, self.drag)


class CarriedRows(unittest.TestCase):
    """Which rows a drag carries: the pressed row with the others picked
    before the press (Explorer's rule), else what the press left picked."""

    def test_a_plain_press_on_a_picked_row_carries_every_picked_row(self):
        self.assertEqual(listdrag.carried_rows(2, [0, 2, 4], [2], True), [0, 2, 4])

    def test_a_press_on_an_unpicked_row_carries_it_alone(self):
        self.assertEqual(listdrag.carried_rows(1, [0, 2], [1], True), [1])

    def test_a_modified_press_carries_what_it_left_picked(self):
        self.assertEqual(listdrag.carried_rows(4, [0], [0, 1, 2, 3, 4], False), [0, 1, 2, 3, 4])

    def test_a_ctrl_press_that_unpicked_the_row_carries_the_row(self):
        self.assertEqual(listdrag.carried_rows(2, [0, 2], [0], False), [2])


@unittest.skipIf(QT is None, "no Qt")
class DragSeveral(unittest.TestCase):
    """2026-10-01: a list taking several rows (Maya's multi-select
    textScrollList is a QListWidget in ExtendedSelection)."""

    def setUp(self):
        self.app = QT.QtWidgets.QApplication.instance() or QT.QtWidgets.QApplication([])
        W = QT.QtWidgets
        self.list = W.QListWidget()
        self.list.setSelectionMode(W.QAbstractItemView.ExtendedSelection)
        self.list.addItems(["A_Jump", "A_Walk", "A_Run", "A_Idle"])
        self.list.resize(300, 200)
        self.list.move(3000, 3000)
        self.list.show()
        self.addCleanup(self.list.deleteLater)
        self.records = [Rec(n, "/Game/" + n) for n in ("A_Jump", "A_Walk", "A_Run", "A_Idle")]
        self.scene = FakeScene()
        self.drag = listdrag.attach_widget(self.list, lambda: list(self.records), self.scene)
        self.E = QT.QtCore.QEvent
        self.L, self.N = QT.QtCore.Qt.LeftButton, QT.QtCore.Qt.NoButton

    def row(self, index):
        return self.list.visualItemRect(self.list.item(index)).center()

    def mouse(self, kind, local, button, buttons, modifiers=None):
        port = self.list.viewport()
        g = port.mapToGlobal(local)
        event = QT.QtGui.QMouseEvent(kind, QT.QtCore.QPointF(local), QT.QtCore.QPointF(g),
                                     button, buttons,
                                     modifiers or QT.QtCore.Qt.NoModifier)
        QT.QtWidgets.QApplication.sendEvent(port, event)

    def click(self, index, modifiers=None):
        self.mouse(self.E.MouseButtonPress, self.row(index), self.L, self.L, modifiers)
        self.mouse(self.E.MouseButtonRelease, self.row(index), self.L, self.N, modifiers)

    def drag_from(self, index, modifiers=None):
        start = self.row(index)
        self.mouse(self.E.MouseButtonPress, start, self.L, self.L, modifiers)
        self.mouse(self.E.MouseMove, start + QT.QtCore.QPoint(30, 0), self.N, self.L, modifiers)
        carried = [r.name for r in self.drag.carried()]
        far = start + QT.QtCore.QPoint(-900, 500)
        self.mouse(self.E.MouseMove, far, self.N, self.L)
        self.mouse(self.E.MouseButtonRelease, far, self.L, self.N)
        return carried

    def selected(self):
        return sorted(self.list.row(item) for item in self.list.selectedItems())

    def drops(self):
        return [e for e in self.scene.log if e[0] == "drop"]

    def test_two_picked_and_the_press_on_one_carries_both_and_both_stay_picked(self):
        ctrl = QT.QtCore.Qt.ControlModifier
        self.click(0)
        self.click(2, ctrl)
        self.assertEqual(self.selected(), [0, 2])
        carried = self.drag_from(2)
        self.assertEqual(carried, ["A_Jump", "A_Run"])
        self.assertEqual(self.drops(), [("drop", ["A_Jump", "A_Run"], "rig")])
        self.assertEqual(self.drag.dragging(), None)
        self.assertEqual(self.selected(), [0, 2])

    def test_a_press_on_an_unpicked_row_carries_it_alone(self):
        ctrl = QT.QtCore.Qt.ControlModifier
        self.click(0)
        self.click(2, ctrl)
        carried = self.drag_from(1)
        self.assertEqual(carried, ["A_Walk"])
        self.assertEqual(self.drops(), [("drop", "A_Walk", "rig")])
        self.assertEqual(self.selected(), [1])

    def test_a_ctrl_press_that_adds_a_row_carries_it_with_the_rest(self):
        """A modified press carries what it left picked. (Ctrl, not Shift:
        offscreen Qt ignores a sent Shift for a range - measured on a bare
        QListWidget, no filter of ours - and Shift goes the same road.)"""
        ctrl = QT.QtCore.Qt.ControlModifier
        self.click(0)
        self.click(2, ctrl)
        carried = self.drag_from(3, ctrl)
        self.assertEqual(carried, ["A_Jump", "A_Run", "A_Idle"])
        self.assertEqual(self.selected(), [0, 2, 3])

    def test_the_ghost_names_them(self):
        ctrl = QT.QtCore.Qt.ControlModifier
        self.click(1)
        self.click(3, ctrl)
        start = self.row(3)
        self.mouse(self.E.MouseButtonPress, start, self.L, self.L)
        self.mouse(self.E.MouseMove, start + QT.QtCore.QPoint(30, 0), self.N, self.L)
        far = self.list.viewport().mapToGlobal(start + QT.QtCore.QPoint(-900, 500))
        self.drag.caption_at(far, force=True)
        self.assertEqual(self.drag.ghost().text,
                         "A_Walk · retarget onto Manny_Rig1 · first of 2")
        self.mouse(self.E.MouseButtonRelease, start + QT.QtCore.QPoint(-900, 500), self.L, self.N)

    def test_drop_at_takes_a_list(self):
        self.drag.drop_at(10, 10, self.records[1:3])
        self.assertEqual(self.drops(), [("drop", ["A_Walk", "A_Run"], "rig")])


class Boundary(unittest.TestCase):

    def test_the_module_imports_no_qt_or_maya_at_import(self):
        import ast
        with open(listdrag.__file__, encoding="utf-8") as handle:
            tree = ast.parse(handle.read())
        top = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
        names = [a.name for n in top for a in n.names] + [
            n.module or "" for n in top if isinstance(n, ast.ImportFrom)]
        for banned in ("maya", "PySide6", "shiboken6", "maya_hubqt"):
            self.assertFalse(any(name == banned or name.startswith(banned + ".")
                                 for name in names), banned)


if __name__ == "__main__":
    unittest.main()
