"""maya_hubqt: the hub skin's Qt widgets, offscreen.

The two Maya seams (`find`, `path_of`) are replaced: a Maya control is
stood in for by a plain Qt widget of the matching class, registered by name.

Spec: docs/superpowers/specs/2026-09-28-hub-skin-design.md
"""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtWidgets

import maya_hubqt as hubqt
import maya_hubstyle as style


def _app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


class SeamsMixin(object):

    def setUp(self):
        self.app = _app()
        self.saved = (hubqt.find, hubqt.path_of)
        self.controls = {}
        hubqt.find = lambda name, layout=False: self.controls.get(name)
        hubqt.path_of = lambda obj: "path|" + obj.objectName()
        self.calls = []
        self.host = QtWidgets.QWidget()
        self.host_layout = QtWidgets.QVBoxLayout(self.host)
        callbacks = {
            "hotkeys": lambda: self.calls.append("hotkeys"),
            "version": lambda: self.calls.append("version"),
            "check_update": lambda: self.calls.append("check_update"),
            "hotkey_editor": lambda: self.calls.append("hotkey_editor"),
            "classic": lambda: self.calls.append("classic"),
            "jump": lambda key: self.calls.append(("jump", key)),
            "toggled": lambda key, c: self.calls.append(("toggled", key, c)),
        }
        self.skin = hubqt.Skin(self.host_layout, scale=1.0,
                               callbacks=callbacks)

    def tearDown(self):
        hubqt.find, hubqt.path_of = self.saved
        if self.skin.alive():
            self.skin.destroy()
        self.host.deleteLater()

    def control(self, cls, name, parent=None):
        widget = cls(parent)
        widget.setObjectName(name)
        self.controls[name] = widget
        return widget


class TheShell(SeamsMixin, unittest.TestCase):

    def test_the_root_goes_into_the_host_named_for_the_stylesheet(self):
        self.assertEqual(self.skin.root.objectName(), style.ROOT)
        self.assertIs(self.skin.root.parent(), self.host)
        self.assertEqual(self.skin.content.objectName(), style.CONTENT)
        self.assertEqual(self.skin.scroll.objectName(), style.SCROLL)
        self.assertEqual(self.skin.scroll.viewport().objectName(),
                         style.VIEWPORT)

    def test_a_host_widget_is_taken_and_kept(self):
        """The workspaceControl's WIDGET: a layout reached through a
        temporary wrapper died with it (measured 2026-09-28)."""
        host = QtWidgets.QWidget()
        QtWidgets.QVBoxLayout(host)
        skin = hubqt.Skin(host, scale=1.0)
        self.assertIs(skin.root.parent(), host)
        self.assertIs(skin.host, host)
        skin.destroy()

    def test_destroy_roots_takes_every_skin_in_the_control(self):
        """A root an older module object built is found by name."""
        host = self.control(QtWidgets.QWidget, "hubControl")
        QtWidgets.QVBoxLayout(host)
        old = hubqt.Skin(host, scale=1.0)
        new = hubqt.Skin(host, scale=1.0)
        self.assertEqual(hubqt.destroy_roots("hubControl"), 2)
        self.assertFalse(old.alive())
        self.assertFalse(new.alive())
        self.assertEqual(hubqt.destroy_roots("hubControl"), 0)
        self.assertEqual(hubqt.destroy_roots("nothing"), 0)

    def test_the_scroll_area_never_scrolls_sideways(self):
        self.assertEqual(self.skin.scroll.horizontalScrollBarPolicy(),
                         QtCore.Qt.ScrollBarAlwaysOff)
        self.assertTrue(self.skin.scroll.widgetResizable())

    def test_the_header_holds_logo_title_hotkeys_version_menu(self):
        names = [w.objectName() for w in
                 self.skin.header.findChildren(QtWidgets.QWidget)]
        for name in ("skeldarHubLogo", "skeldarHubTitle", "skeldarHubHotkeys",
                     "skeldarHubVersion", "skeldarHubMenu"):
            self.assertIn(name, names)

    def test_the_header_buttons_call_back(self):
        self.skin.hotkeys.click()
        self.skin.version.click()
        self.assertEqual(self.calls, ["hotkeys", "version"])

    def test_the_menu_offers_check_update_hotkey_editor_classic(self):
        actions = [a for a in self.skin.menu.actions() if not a.isSeparator()]
        self.assertEqual([a.text() for a in actions],
                         ["Check update", "Hotkey Editor...", "Classic look"])
        for action in actions:
            action.trigger()
        self.assertEqual(self.calls,
                         ["check_update", "hotkey_editor", "classic"])

    def test_every_object_of_ours_has_a_name(self):
        """They are parts of the cmds paths of everything inside."""
        card = self.skin.add_card("colour", "Colour", "palette", "#c89be8",
                                  "#3a2a4a")
        chain = card.body_layout
        names = []
        obj = chain
        while obj is not None and obj is not self.host:
            names.append(obj.objectName())
            obj = obj.parent()
        self.assertTrue(all(names), names)


class Message(SeamsMixin, unittest.TestCase):

    def test_hidden_until_something_is_said(self):
        self.assertTrue(self.skin.message.isHidden())
        self.skin.say("Up to date: 601eaae")
        self.assertFalse(self.skin.message.isHidden())
        self.assertEqual(self.skin.message_text.text(), "Up to date: 601eaae")

    def test_saying_nothing_hides_it(self):
        self.skin.say("x")
        self.skin.say("")
        self.assertTrue(self.skin.message.isHidden())

    def test_the_cross_hides_it(self):
        self.skin.say("x")
        self.skin.message_close.click()
        self.assertTrue(self.skin.message.isHidden())

    def test_a_state_recolours_the_version_chip(self):
        self.skin.say("Up to date", state="ok")
        self.assertEqual(self.skin.version.property("skState"), "ok")


class HeaderState(SeamsMixin, unittest.TestCase):

    def test_paint_hotkeys_checks_the_button(self):
        self.skin.paint_hotkeys(True)
        self.assertTrue(self.skin.hotkeys.isChecked())
        self.assertIn("ON", self.skin.hotkeys.toolTip())
        self.skin.paint_hotkeys(False)
        self.assertFalse(self.skin.hotkeys.isChecked())
        self.assertIn("OFF", self.skin.hotkeys.toolTip())

    def test_set_version(self):
        self.skin.set_version("d0a2631", "d0a2631, 2026-09-28 12:22")
        self.assertEqual(self.skin.version.text(), "d0a2631")
        self.assertEqual(self.skin.version.toolTip(),
                         "d0a2631, 2026-09-28 12:22")
        self.skin.set_version("d0a2631", "", state="new")
        self.assertEqual(self.skin.version.property("skState"), "new")


class Cards(SeamsMixin, unittest.TestCase):

    def test_a_card_has_a_named_body_layout_for_the_builder(self):
        card = self.skin.add_card("characters", "Characters", "user",
                                  "#f0a26b", "#4a3322")
        self.assertEqual(card.body_layout.objectName(),
                         "skeldarHubBodyLayout_characters")
        self.assertEqual(card.body_path(),
                         "path|skeldarHubBodyLayout_characters")
        self.assertTrue(card.frame.property("skCard"))
        self.assertIs(self.skin.cards["characters"], card)

    def test_cards_stack_in_order_under_their_group_labels(self):
        self.skin.add_group("scene", "Scene")
        self.skin.add_card("characters", "Characters", "user", "#f0a26b",
                           "#4a3322")
        self.skin.add_group("look", "Look")
        self.skin.add_card("colour", "Colour", "palette", "#c89be8",
                           "#3a2a4a")
        column = self.skin.column
        names = [column.itemAt(i).widget().objectName()
                 for i in range(column.count()) if column.itemAt(i).widget()]
        self.assertEqual(names, ["skeldarHubGroup_scene",
                                 "skeldarHubCard_characters",
                                 "skeldarHubGroup_look",
                                 "skeldarHubCard_colour"])

    def test_collapse_hides_the_body(self):
        card = self.skin.add_card("colour", "Colour", "palette", "#c89be8",
                                  "#3a2a4a", collapsed=True)
        self.assertTrue(card.collapsed())
        self.assertTrue(card.body.isHidden())
        card.set_collapsed(False)
        self.assertFalse(card.body.isHidden())
        self.assertFalse(card.collapsed())

    def test_a_click_on_the_header_toggles_and_calls_back(self):
        card = self.skin.add_card("colour", "Colour", "palette", "#c89be8",
                                  "#3a2a4a")
        card.toggle()
        self.assertTrue(card.collapsed())
        self.assertEqual(self.calls[-1], ("toggled", "colour", True))
        card.toggle()
        self.assertEqual(self.calls[-1], ("toggled", "colour", False))

    def test_set_collapsed_does_not_call_back(self):
        """Only the animator's click is remembered; code opening a card
        remembers through the hub itself."""
        card = self.skin.add_card("colour", "Colour", "palette", "#c89be8",
                                  "#3a2a4a")
        card.set_collapsed(True)
        self.assertEqual(self.calls, [])

    def test_the_jump_strip_calls_back_with_the_key(self):
        self.skin.add_jump("studio", "Studio", "bulb", "#c89be8")
        button = self.skin.jumps["studio"]
        self.assertEqual(button.toolTip(), "Studio")
        button.click()
        self.assertEqual(self.calls, [("jump", "studio")])

    def test_scroll_to_answers_the_card_s_offset(self):
        self.skin.add_card("a", "A", "user", "#f0a26b", "#4a3322")
        self.skin.add_card("b", "B", "user", "#f0a26b", "#4a3322")
        self.assertEqual(self.skin.scroll_to("b"),
                         self.skin.cards["b"].frame.y())
        self.assertIsNone(self.skin.scroll_to("nonsense"))

    def test_destroy_takes_everything_at_once(self):
        self.skin.add_card("a", "A", "user", "#f0a26b", "#4a3322")
        self.skin.destroy()
        self.assertFalse(self.skin.alive())
        self.assertEqual(self.host_layout.count(), 0)


class ActiveCard(SeamsMixin, unittest.TestCase):
    """2026-09-28: «активное окно подсвечивалось немного другим цветом» -
    the card being worked in is lit."""

    def setUp(self):
        SeamsMixin.setUp(self)
        self.a = self.skin.add_card("characters", "Characters", "user",
                                    "#f0a26b", "#4a3322")
        self.b = self.skin.add_card("colour", "Colour", "palette", "#c89be8",
                                    "#3a2a4a")
        self.field = QtWidgets.QLineEdit(self.b.body)

    def test_none_is_lit_at_first(self):
        self.assertIsNone(self.skin.active)
        self.assertFalse(self.a.frame.property("skActive"))

    def test_set_active_lights_one_and_puts_the_other_back(self):
        self.skin.set_active("characters")
        self.assertTrue(self.a.frame.property("skActive"))
        self.skin.set_active("colour")
        self.assertTrue(self.b.frame.property("skActive"))
        self.assertFalse(self.a.frame.property("skActive"))
        self.assertEqual(self.skin.active, "colour")

    def test_the_card_of_a_widget_inside_it(self):
        self.assertEqual(self.skin.card_of(self.field), "colour")
        self.assertEqual(self.skin.card_of(self.a.header), "characters")
        self.assertIsNone(self.skin.card_of(self.skin.header))
        self.assertIsNone(self.skin.card_of(None))

    def test_focus_inside_a_card_lights_it(self):
        from PySide6 import QtCore as C, QtGui as G
        QtWidgets.QApplication.sendEvent(
            self.field, G.QFocusEvent(C.QEvent.FocusIn))
        self.assertEqual(self.skin.active, "colour")

    def test_a_press_inside_a_card_lights_it(self):
        from PySide6 import QtCore as C, QtGui as G
        press = G.QMouseEvent(C.QEvent.MouseButtonPress, C.QPointF(2, 2),
                              C.QPointF(2, 2), C.Qt.LeftButton,
                              C.Qt.LeftButton, C.Qt.NoModifier)
        QtWidgets.QApplication.sendEvent(self.a.header, press)
        self.assertEqual(self.skin.active, "characters")

    def _enter(self, widget):
        from PySide6 import QtCore as C, QtGui as G
        QtWidgets.QApplication.sendEvent(
            widget, G.QEnterEvent(C.QPointF(1, 1), C.QPointF(1, 1),
                                  C.QPointF(1, 1)))

    def test_the_mouse_over_a_card_lights_it(self):
        """2026-09-28: «когда я наводил мышкой на какой-то раздел у него
        включалась подсветка» - not only after a click."""
        self._enter(self.field)
        self.assertEqual(self.skin.active, "colour")
        self._enter(self.a.header)
        self.assertEqual(self.skin.active, "characters")
        self.assertTrue(self.a.frame.property("skActive"))
        self.assertFalse(self.b.frame.property("skActive"))

    def test_off_every_card_the_open_one_worked_in_is_lit_after_a_pause(self):
        self.skin.set_active("colour")                   # pressed in
        self._enter(self.a.header)                       # hovering
        self.assertEqual(self.skin.active, "characters")
        self._enter(self.skin.header)                    # off the cards
        self.assertEqual(self.skin.active, "characters")  # not yet
        self.assertTrue(self.skin._fallback.isActive())
        self.assertEqual(self.skin._fallback.interval(), hubqt.FALLBACK_MS)
        self.skin._fallback.timeout.emit()
        self.assertEqual(self.skin.active, "colour")
        self.assertEqual(self.skin.pinned, "colour")

    def test_a_gap_between_two_cards_lights_nothing_in_between(self):
        """«подсветка перепрыгивает на последний активный раздел ...
        картинка как бы мигает»: the next card, entered within the pause,
        cancels the fall back."""
        self.skin.set_active("colour")
        self._enter(self.a.header)
        self._enter(self.skin.content)                   # the gap
        self._enter(self.field)                          # the next card
        self.assertFalse(self.skin._fallback.isActive())
        self.assertEqual(self.skin.active, "colour")

    def test_a_closed_card_worked_in_stays_dark(self):
        """2026-09-28: back to the last card worked in only if it is open."""
        self.skin.set_active("colour")
        self.b.set_collapsed(True)
        self._enter(self.a.header)
        self._enter(self.skin.header)
        self.skin._fallback.timeout.emit()
        self.assertIsNone(self.skin.active)
        self.assertEqual(self.skin.resting(), None)
        self.b.set_collapsed(False)
        self.assertEqual(self.skin.resting(), "colour")

    def test_leaving_the_hub_lights_the_open_one_worked_in(self):
        from PySide6 import QtCore as C
        self.skin.set_active("characters")
        self._enter(self.field)
        QtWidgets.QApplication.sendEvent(self.skin.root,
                                         C.QEvent(C.QEvent.Leave))
        self.skin._fallback.timeout.emit()
        self.assertEqual(self.skin.active, "characters")

    def test_a_hover_pins_nothing(self):
        self._enter(self.field)
        self.assertIsNone(self.skin.pinned)
        self._enter(self.skin.header)
        self.skin._fallback.timeout.emit()
        self.assertIsNone(self.skin.active)

    def test_a_press_cancels_a_pending_fall_back(self):
        self._enter(self.a.header)
        self._enter(self.skin.header)
        self.skin.set_active("colour")
        self.assertFalse(self.skin._fallback.isActive())
        self.assertEqual(self.skin.active, "colour")

    def test_widgets_outside_the_hub_are_no_card(self):
        outside = QtWidgets.QLineEdit()
        self.assertIsNone(self.skin.card_of(outside))

    def test_the_stylesheet_lights_it(self):
        sheet = style.stylesheet()
        self.assertIn('[skActive="true"]', sheet)
        self.assertIn(style.TOKENS["card_active"], sheet)


class ApplyMarks(SeamsMixin, unittest.TestCase):

    def setUp(self):
        SeamsMixin.setUp(self)
        self.card = self.skin.add_card("characters", "Characters", "user",
                                       "#f0a26b", "#4a3322")

    def test_a_role_becomes_the_property_and_an_icon_is_set(self):
        button = self.control(QtWidgets.QPushButton, "addCharacter",
                              self.card.body)
        marks = [style.Mark("addCharacter", "primary", "plus", False, None)]
        self.assertEqual(hubqt.apply_marks(marks, self.card, 1.0), 1)
        self.assertEqual(button.property("skRole"), "primary")
        self.assertFalse(button.icon().isNull())

    def test_a_layout_mark_is_found_as_a_layout(self):
        seen = []
        row = self.control(QtWidgets.QWidget, "segRow", self.card.body)
        hubqt.find = lambda name, layout=False: (seen.append(layout)
                                                 or self.controls.get(name))
        hubqt.apply_marks([style.Mark("segRow", "segments", None, True,
                                      None)], self.card, 1.0)
        #  twice: its own mark, then the segments pass
        self.assertEqual(seen, [True, True])
        self.assertEqual(row.property("skRole"), "segments")

    def test_segments_share_their_track_equally(self):
        """Measured 2026-09-28: Maya's rowLayout (QmayaRowLayout) places
        its children at their own widths whatever their stretch says, so
        the segments move into a row of ours laid over the track."""
        row = self.control(QtWidgets.QWidget, "track", self.card.body)
        box = QtWidgets.QHBoxLayout(row)
        buttons = [self.control(QtWidgets.QPushButton, "seg" + t, row)
                   for t in ("Free", "Weapon")]
        for button in buttons:
            box.addWidget(button)
        hubqt.apply_marks(
            [style.Mark("track", "segments", None, True, None),
             style.Mark("segFree", "segment", None, False, None),
             style.Mark("segWeapon", "segment", None, False, None)],
            self.card, 1.0)
        cover = buttons[0].parentWidget()
        self.assertIs(cover.parentWidget(), row)
        self.assertEqual(cover.objectName(), "track_skinSegments")
        stretch = cover.layout()
        self.assertEqual([stretch.stretch(i) for i in range(stretch.count())],
                         [1, 1])
        self.assertIs(buttons[1].parentWidget(), cover)
        self.assertGreater(row.minimumHeight(), 0)
        self.assertEqual(row.minimumWidth(), 0)       # the dock may narrow
        row.resize(300, 30)
        QtWidgets.QApplication.sendEvent(
            row, __import__("PySide6.QtGui", fromlist=["QResizeEvent"])
            .QResizeEvent(QtCore.QSize(300, 30), QtCore.QSize(10, 10)))
        self.assertEqual(cover.geometry().width(), 300)
        self.assertEqual(buttons[0].property("skRole"), "segment")

    def test_a_swatch_is_painted_its_colour(self):
        dot = self.control(QtWidgets.QPushButton, "dot1", self.card.body)
        hubqt.apply_marks([style.Mark("dot1", "swatch", None, False,
                                      "#e05a4f")], self.card, 1.0)
        self.assertIn("#e05a4f", dot.styleSheet())

    def test_a_swatch_s_label_reads_on_its_colour(self):
        light = self.control(QtWidgets.QPushButton, "amber", self.card.body)
        dark = self.control(QtWidgets.QPushButton, "blue", self.card.body)
        hubqt.apply_marks([
            style.Mark("amber", "swatch", None, False, "#d9b93a"),
            style.Mark("blue", "swatch", None, False, "#2c4fa8")],
            self.card, 1.0)
        self.assertIn("color: " + style.TOKENS["panel"], light.styleSheet())
        self.assertIn("color: " + style.TOKENS["text"], dark.styleSheet())

    def test_a_subtitle_moves_into_the_card_header(self):
        line = self.control(QtWidgets.QLabel, "boundLine", self.card.body)
        line.setWordWrap(True)
        line.setFixedHeight(36)
        hubqt.apply_marks([style.Mark("boundLine", "subtitle", None, False,
                                      None)], self.card, 1.0)
        self.assertTrue(self.card.header.isAncestorOf(line))
        self.assertFalse(line.wordWrap())
        self.assertEqual(line.property("skRole"), "subtitle")
        self.assertLess(line.minimumHeight(), 36)

    def test_swatchonly_hides_the_slider_and_its_label(self):
        grp = self.control(QtWidgets.QWidget, "colourGrp", self.card.body)
        label = QtWidgets.QLabel(grp)
        label.setObjectName("color")
        port = QtWidgets.QLabel(grp)
        port.setObjectName("port")
        slider = QtWidgets.QSlider(grp)
        slider.setObjectName("slider")
        hubqt.apply_marks([style.Mark("colourGrp", "swatchonly", None, False,
                                      None)], self.card, 1.0)
        self.assertTrue(slider.isHidden())
        self.assertTrue(label.isHidden())
        self.assertFalse(port.isHidden())

    def test_one_control_refusing_its_look_costs_only_itself(self):
        good = self.control(QtWidgets.QPushButton, "good", self.card.body)
        saved = hubqt.find

        def find(name, layout=False):
            if name == "bad":
                raise RuntimeError("Internal C++ object already deleted")
            return saved(name, layout)
        hubqt.find = find
        applied = hubqt.apply_marks(
            [style.Mark("bad", "primary", None, False, None),
             style.Mark("good", "primary", None, False, None)], self.card, 1.0)
        self.assertEqual(applied, 1)
        self.assertEqual(good.property("skRole"), "primary")

    def test_a_missing_control_is_skipped(self):
        self.assertEqual(hubqt.apply_marks(
            [style.Mark("gone", "primary", None, False, None)], self.card,
            1.0), 0)


class Icons(unittest.TestCase):

    def setUp(self):
        _app()

    def test_an_icon_file_is_the_svg_in_its_colour(self):
        import shutil
        import tempfile
        folder = tempfile.mkdtemp()
        try:
            path = hubqt.icon_file("chevron-down", "#9a9ca3", folder=folder)
            self.assertNotIn("\\", path)
            self.assertTrue(path.endswith("chevron-down_9a9ca3.svg"))
            with open(path) as handle:
                self.assertIn('stroke="#9a9ca3"', handle.read())
        finally:
            shutil.rmtree(folder, ignore_errors=True)

    def test_an_icon_renders(self):
        icon = hubqt.icon("sword", "#f0a26b", 16)
        self.assertFalse(icon.isNull())
        self.assertFalse(icon.pixmap(16, 16).isNull())


class Available(unittest.TestCase):

    def test_not_without_maya_s_ui(self):
        """mayapy standalone has Qt but no OpenMayaUI windows; the skin
        must not be tried there (the tests' fake cmds cannot host it)."""
        saved = hubqt._maya_ui_ok
        hubqt._maya_ui_ok = lambda: False
        try:
            self.assertFalse(hubqt.available())
        finally:
            hubqt._maya_ui_ok = saved

    def test_qt_is_found(self):
        self.assertIsNotNone(hubqt.qt())


if __name__ == "__main__":
    unittest.main()


class Ghost(unittest.TestCase):
    """2026-09-30: the inventory's drag ghost, shared with the Characters grid."""

    def setUp(self):
        from PySide6 import QtGui
        self.app = _app()
        self.QtGui = QtGui

    def test_the_caption_grows_the_ghost_and_the_cursor_sits_on_the_anchor(self):
        pix = self.QtGui.QPixmap(40, 40)
        pix.fill(QtCore.Qt.red)
        ghost = hubqt.ghost_class()(pix, 40, 80, 1.0, anchor=(0.5, 0.5),
                                    name="skeldarTestGhost", backdrop="field")
        self.addCleanup(ghost.deleteLater)
        self.assertEqual(ghost.objectName(), "skeldarTestGhost")
        ghost.set_caption("a caption far wider than the icon is", True)
        self.assertGreater(ghost.width(), 40)
        ghost.follow(QtCore.QPoint(500, 500))
        self.assertEqual(ghost.x() + ghost.width() // 2, 500)
        self.assertEqual(ghost.y() + 40, 500)
        image = self.QtGui.QImage(ghost.size(), self.QtGui.QImage.Format_ARGB32)
        image.fill(0)
        ghost.render(image)
        self.assertGreater(image.pixelColor(ghost.width() // 2, 20).alpha(), 0)

    def test_one_class_for_every_drag(self):
        self.assertIs(hubqt.ghost_class(), hubqt.ghost_class())
