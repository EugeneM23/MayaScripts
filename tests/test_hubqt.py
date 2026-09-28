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
        self.assertEqual(seen, [True])
        self.assertEqual(row.property("skRole"), "segments")

    def test_a_swatch_is_painted_its_colour(self):
        dot = self.control(QtWidgets.QPushButton, "dot1", self.card.body)
        hubqt.apply_marks([style.Mark("dot1", "swatch", None, False,
                                      "#e05a4f")], self.card, 1.0)
        self.assertIn("#e05a4f", dot.styleSheet())

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

    def test_a_missing_control_is_skipped(self):
        self.assertEqual(hubqt.apply_marks(
            [style.Mark("gone", "primary", None, False, None)], self.card,
            1.0), 0)


class Icons(unittest.TestCase):

    def setUp(self):
        _app()

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
