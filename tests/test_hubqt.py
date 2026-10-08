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
        #  skins register on the status relay (2026-10-08); a test that
        #  deletes a skin's root without destroy() would leave it there
        style._LISTENERS[:] = []
        self.saved = (hubqt.find, hubqt.path_of)
        self.controls = {}
        hubqt.find = lambda name, layout=False: self.controls.get(name)
        hubqt.path_of = lambda obj: "path|" + obj.objectName()
        self.calls = []
        self.host = QtWidgets.QWidget()
        self.host_layout = QtWidgets.QVBoxLayout(self.host)
        callbacks = {
            "hotkeys": lambda: self.calls.append("hotkeys"),
            "check_update": lambda: self.calls.append("check_update"),
            "hotkey_editor": lambda: self.calls.append("hotkey_editor"),
            "classic": lambda: self.calls.append("classic"),
            "jump": lambda key: self.calls.append(("jump", key)),
            "toggled": lambda key, c: self.calls.append(("toggled", key, c)),
            "hover": lambda: self.calls.append("hover"),
            "sounds": lambda on: self.calls.append(("sounds", on)),
            "animations": lambda on: self.calls.append(("animations", on)),
            "pin": lambda on: self.calls.append(("pin", on)),
            "edge": lambda on: self.calls.append(("edge", on)),
            "told": lambda *a: None,
        }
        self.skin = hubqt.Skin(self.host_layout, scale=1.0,
                               callbacks=callbacks)

    def tearDown(self):
        hubqt.find, hubqt.path_of = self.saved
        if self.skin.alive():
            self.skin.destroy()
        style._LISTENERS[:] = []
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

    def test_the_header_holds_logo_jumps_hotkeys_pin_menu(self):
        """2026-10-08: ONE header row - the mark, the jump icons, the
        hotkeys, the pin (edge panel), the menu; no title, no version chip,
        no strip."""
        names = [self.skin.header.layout().itemAt(i).widget().objectName()
                 for i in range(self.skin.header.layout().count())
                 if self.skin.header.layout().itemAt(i).widget()]
        self.assertEqual(names[0], "skeldarHubLogo")
        self.assertIn("skeldarHubHotkeys", names)
        self.assertIn("skeldarHubPin", names)
        self.assertIn("skeldarHubMenu", names)
        self.assertNotIn("skeldarHubTitle", names)
        self.assertNotIn("skeldarHubVersion", names)
        self.assertFalse(hasattr(self.skin, "strip"))

    def test_jumps_go_into_the_header_before_the_buttons(self):
        self.skin.add_jump("characters", "Animation Setup", "user", "#f0a26b")
        row = self.skin.jump_row
        self.assertEqual(row.objectName(), "skeldarHubJumpRow")
        self.assertEqual(row.itemAt(0).widget(), self.skin.jumps["characters"])
        header = self.skin.header.layout()
        self.assertIs(header.itemAt(1).layout(), row)

    def test_the_hotkeys_button_calls_back(self):
        self.skin.hotkeys.click()
        self.assertEqual(self.calls, ["hotkeys"])

    def test_the_menu_offers_check_update_hotkey_editor_sounds_classic(self):
        actions = [a for a in self.skin.menu.actions() if not a.isSeparator()]
        self.assertEqual([a.text() for a in actions],
                         ["Check update", "Hotkey Editor...",
                          "Interface sounds", "Interface animations",
                          "Edge panel", "Classic look"])
        self.skin.paint_sounds(True)
        self.skin.paint_animations(True)
        for action in actions:
            action.trigger()
        self.assertEqual(self.calls,
                         ["check_update", "hotkey_editor", ("sounds", False),
                          ("animations", False), ("edge", True), "classic"])

    def test_the_sounds_row_is_a_checkbox_painted_without_a_call(self):
        """2026-10-01: «звук наводки на кнопочку», switched in the menu."""
        action = self.skin.sounds_action
        self.assertTrue(action.isCheckable())
        self.skin.paint_sounds(True)
        self.assertTrue(action.isChecked())
        self.skin.paint_sounds(False)
        self.assertFalse(action.isChecked())
        self.assertEqual(self.calls, [])
        action.trigger()
        self.assertEqual(self.calls, [("sounds", True)])

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

    def test_a_state_given_with_a_message_paints_the_update_jump(self):
        self.skin.add_jump("update", "Update", "refresh", "#9a9ca3")
        self.skin.say("Up to date", state="ok")
        self.assertEqual(self.skin.jumps["update"].property("skState"), "ok")

    def test_a_told_status_shows_on_the_line_with_its_card(self):
        card = self.skin.add_card("retarget", "Retarget", "arrows-exchange",
                                  "#7fa9e6", "#23324a")
        card.status_controls.add("skeldarRetargetStatus")
        told = []
        self.skin.cb["told"] = lambda key, text, v: told.append((key, text, v))
        style.tell("skeldarRetargetStatus", "Retargeted 61 frames")
        self.assertEqual(self.skin.message_text.text(), "Retargeted 61 frames")
        self.assertFalse(self.skin.message.isHidden())
        self.assertFalse(self.skin.message_icon.isHidden())
        self.assertEqual(told, [("retarget", "Retargeted 61 frames", False)])

    def test_an_unknown_control_is_not_shown(self):
        style.tell("somebodyElse", "x")
        self.assertTrue(self.skin.message.isHidden())

    def test_an_empty_text_from_the_shown_source_hides_the_line(self):
        card = self.skin.add_card("com", "Center of Mass", "target",
                                  "#7fa9e6", "#23324a")
        card.status_controls.add("skeldarComStatus")
        style.tell("skeldarComStatus", "added")
        style.tell("skeldarComStatus", "")
        self.assertTrue(self.skin.message.isHidden())

    def test_an_empty_text_from_another_source_leaves_the_line(self):
        a = self.skin.add_card("com", "Center of Mass", "target",
                               "#7fa9e6", "#23324a")
        b = self.skin.add_card("retarget", "Retarget", "arrows-exchange",
                               "#7fa9e6", "#23324a")
        a.status_controls.add("skeldarComStatus")
        b.status_controls.add("skeldarRetargetStatus")
        style.tell("skeldarComStatus", "added")
        style.tell("skeldarRetargetStatus", "")
        self.assertFalse(self.skin.message.isHidden())
        self.assertEqual(self.skin.message_text.text(), "added")

    def test_a_built_skin_listens_to_the_relay(self):
        self.assertIn(self.skin._told, style._LISTENERS)

    def test_destroy_stops_listening(self):
        self.skin.destroy()
        style.tell("anything", "x")                # no dead widget touched
        self.assertNotIn(self.skin._told, style._LISTENERS)

    def test_a_said_message_has_no_icon(self):
        self.skin.say("Hotkey map: ON")
        self.assertTrue(self.skin.message_icon.isHidden())

    def test_the_icon_follows_the_source_of_the_text(self):
        self.skin.add_card("retarget", "Retarget", "arrows-exchange",
                           "#7fa9e6", "#23324a")
        self.skin.say("done", source="retarget")
        self.assertFalse(self.skin.message_icon.isHidden())
        self.skin.say("later", source=None)
        self.assertTrue(self.skin.message_icon.isHidden())

    def test_the_message_line_caps_at_three_lines(self):
        self.skin.say("word " * 400)
        lines = self.skin.message_text.fontMetrics().lineSpacing()
        self.assertLessEqual(self.skin.message_text.maximumHeight(),
                             3 * lines + 2)
        self.assertEqual(self.skin.message_text.toolTip().strip(),
                         ("word " * 400).strip())


class HeaderState(SeamsMixin, unittest.TestCase):

    def test_paint_hotkeys_checks_the_button(self):
        self.skin.paint_hotkeys(True)
        self.assertTrue(self.skin.hotkeys.isChecked())
        self.assertIn("ON", self.skin.hotkeys.toolTip())
        self.skin.paint_hotkeys(False)
        self.assertFalse(self.skin.hotkeys.isChecked())
        self.assertIn("OFF", self.skin.hotkeys.toolTip())

    def test_a_state_and_a_version_paint_the_update_jump(self):
        self.skin.add_jump("update", "Update", "refresh", "#9a9ca3")
        self.skin.set_version("d0a2631", "Installed: d0a2631")
        self.assertEqual(self.skin.jumps["update"].toolTip(),
                         "Update - Installed: d0a2631")
        self.skin.set_state("new")
        self.assertEqual(self.skin.jumps["update"].property("skState"), "new")
        self.skin.set_state("")
        self.assertEqual(self.skin.jumps["update"].property("skState"), "")

    def test_set_version_with_a_state_sets_it(self):
        self.skin.add_jump("update", "Update", "refresh", "#9a9ca3")
        self.skin.set_version("d0a2631", "", state="new")
        self.assertEqual(self.skin.jumps["update"].property("skState"), "new")

    def test_a_state_without_an_update_jump_is_harmless(self):
        self.skin.set_state("ok")
        self.skin.set_version("x", "y")

    def test_the_update_jump_icon_changes_colour_with_the_state(self):
        self.skin.add_jump("update", "Update", "refresh", "#9a9ca3")
        button = self.skin.jumps["update"]

        def ink(state):
            """The colour of the icon's most opaque pixel."""
            self.skin.set_state(state)
            image = button.icon().pixmap(16, 16).toImage()
            best = max(((image.pixelColor(x, y).alpha(), x, y)
                        for x in range(image.width())
                        for y in range(image.height())))
            return image.pixelColor(best[1], best[2]).name()
        plain = [ink(""), ink("new"), ink("ok")]
        self.assertEqual(len(set(plain)), 3, plain)
        self.assertEqual(plain[0], "#9a9ca3")

    def test_the_pin_is_hidden_until_edge_mode_and_calls_back(self):
        self.calls_pin = []
        self.skin.cb["pin"] = lambda on: self.calls_pin.append(on)
        self.assertTrue(self.skin.pin.isHidden())
        self.skin.set_edge_mode(True)
        self.assertFalse(self.skin.pin.isHidden())
        self.assertTrue(self.skin.edge_action.isChecked())
        self.skin.pin.click()
        self.assertEqual(self.calls_pin, [True])
        self.skin.set_edge_mode(False)
        self.assertTrue(self.skin.pin.isHidden())
        self.assertFalse(self.skin.pin.isChecked())
        self.assertFalse(self.skin.edge_action.isChecked())

    def test_the_edge_row_calls_back_with_its_state(self):
        seen = []
        self.skin.cb["edge"] = lambda on: seen.append(on)
        self.skin.edge_action.trigger()
        self.assertEqual(seen, [True])
        self.skin.paint_edge(False)               # painted, no callback
        self.assertEqual(seen, [True])


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

    def test_a_jump_calls_back_with_the_key(self):
        self.skin.add_jump("retarget", "Retarget", "arrows-exchange", "#7fa9e6")
        button = self.skin.jumps["retarget"]
        self.assertEqual(button.toolTip(), "Retarget")
        button.click()
        self.assertIn(("jump", "retarget"), self.calls)

    def test_a_hint_goes_to_the_card_header_tooltip(self):
        card = self.skin.add_card("retarget", "Retarget", "arrows-exchange",
                                  "#7fa9e6", "#23324a")
        card.add_hint("Select the clip's skeleton")
        card.add_hint("and the rig")
        card.add_hint("   ")
        self.assertEqual(card.header.toolTip(),
                         "Select the clip's skeleton\nand the rig")

    def test_a_card_carries_its_group_stripe(self):
        card = self.skin.add_card("retarget", "Retarget", "arrows-exchange",
                                  "#7fa9e6", "#23324a")
        self.assertEqual(card.frame.stripe, "#7fa9e6")
        self.assertEqual((card.icon_name, card.colour),
                         ("arrows-exchange", "#7fa9e6"))
        self.assertEqual(card.status_controls, set())

    def test_the_stripe_is_painted_inside_the_card(self):
        from PySide6 import QtGui
        card = self.skin.add_card("retarget", "Retarget", "arrows-exchange",
                                  "#7fa9e6", "#23324a")
        frame = card.frame
        #  a frame under a layout is sized by it when it is rendered (170 x 31
        #  here), so the image is bigger than that and the sample is taken
        #  mid-height, clear of the rounded corners
        image = QtGui.QImage(200, 100, QtGui.QImage.Format_ARGB32)
        image.fill(0)
        frame.render(image)
        middle = max(1, frame.height() // 2)
        self.assertEqual(image.pixelColor(1, middle).name(), "#7fa9e6")
        self.assertEqual(image.pixelColor(2, middle).name(), "#7fa9e6")
        self.assertNotEqual(image.pixelColor(frame.width() // 2,
                                             middle).name(), "#7fa9e6")
        self.assertNotEqual(image.pixelColor(5, middle).name(), "#7fa9e6")
        frame.stripe = None                       # no group colour, no bar
        image.fill(0)
        frame.render(image)
        self.assertNotEqual(image.pixelColor(1, middle).name(), "#7fa9e6")

    def test_a_lit_card_keeps_its_stripe(self):
        """Review of the first build: the light's face and 2 px ring reach the
        edge, and a stripe painted BEFORE them vanished on a lit card. Every
        card shows its group, lit, flashing or idle."""
        from PySide6 import QtGui
        card = self.skin.add_card("retarget", "Retarget", "arrows-exchange",
                                  "#7fa9e6", "#23324a")
        frame = card.frame
        image = QtGui.QImage(200, 100, QtGui.QImage.Format_ARGB32)
        for level, flash in ((1.0, 0.0), (0.5, 0.0), (0.0, 1.0), (1.0, 1.0),
                             (0.5, 0.5)):
            frame.level, frame.flash = level, flash
            image.fill(0)
            frame.render(image)
            middle = max(1, frame.height() // 2)
            for x in (0, 1, 2):
                self.assertEqual(image.pixelColor(x, middle).name(),
                                 "#7fa9e6", (level, flash, x))
            #  the bar is 3 px: past it the card's own light shows
            self.assertNotEqual(image.pixelColor(4, middle).name(),
                                "#7fa9e6", (level, flash))
        frame.level = frame.flash = 0.0

    def test_compact_card_margins(self):
        card = self.skin.add_card("retarget", "Retarget", "arrows-exchange",
                                  "#7fa9e6", "#23324a")
        m = card.frame.layout().contentsMargins()
        self.assertEqual((m.left(), m.top(), m.right(), m.bottom()),
                         (5, 4, 5, 5))
        self.assertEqual(card.body_layout.contentsMargins().top(), 4)

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

    def test_the_card_paints_its_light_not_the_sheet(self):
        """2026-10-01: the stylesheet switched the light at once; the card
        paints it now, fading (CardLight below)."""
        self.assertNotIn('[skActive="true"]', style.stylesheet())
        self.assertTrue(hasattr(self.a.frame, "level"))


class HoverSound(SeamsMixin, unittest.TestCase):
    """2026-10-01: «я вожу мышкой по кнопочкам нашего меню и вот тут давай
    сделаем приятный и простой звук наводки» - every button of the hub
    (QAbstractButton: Maya's buttons, checkboxes and segments, our jump
    icons and header), its dropdowns and the card headers; nothing else."""

    def setUp(self):
        SeamsMixin.setUp(self)
        self.card = self.skin.add_card("colour", "Colour", "palette",
                                       "#c89be8", "#3a2a4a")
        body = self.card.body
        self.button = QtWidgets.QPushButton("Add", body)
        self.segment = QtWidgets.QPushButton("Rig", body)
        self.segment.setCheckable(True)
        self.check = QtWidgets.QCheckBox("Timeline", body)
        self.combo = QtWidgets.QComboBox(body)
        self.label = QtWidgets.QLabel("status", body)
        self.field = QtWidgets.QLineEdit(body)
        self.jump = self.skin.add_jump("colour", "Colour", "palette",
                                       "#c89be8")

    def _enter(self, widget):
        from PySide6 import QtCore as C, QtGui as G
        self.calls[:] = []
        QtWidgets.QApplication.sendEvent(
            widget, G.QEnterEvent(C.QPointF(1, 1), C.QPointF(1, 1),
                                  C.QPointF(1, 1)))
        return self.calls.count("hover")

    def test_every_kind_of_button_sounds_once(self):
        self.skin.set_edge_mode(True)             # the pin is shown
        for widget in (self.button, self.segment, self.check, self.jump,
                       self.skin.hotkeys, self.skin.pin,
                       self.skin.menu_button):
            self.assertEqual(self._enter(widget), 1, widget)

    def test_a_dropdown_and_a_card_header_sound(self):
        self.assertEqual(self._enter(self.combo), 1)
        self.assertEqual(self._enter(self.card.header), 1)

    def test_what_is_not_clickable_is_silent(self):
        for widget in (self.label, self.field, self.card.body,
                       self.card.frame, self.skin.header, self.skin.content,
                       self.card.chevron):
            self.assertEqual(self._enter(widget), 0, widget.objectName())

    def test_a_disabled_button_is_silent(self):
        self.button.setEnabled(False)
        self.assertEqual(self._enter(self.button), 0)

    def test_a_button_outside_the_hub_is_silent(self):
        outside = QtWidgets.QPushButton("Maya's own")
        self.assertEqual(self._enter(outside), 0)
        self.assertFalse(hubqt.sounding(outside, self.skin.root))
        self.assertFalse(hubqt.sounding(None, self.skin.root))

    def test_the_hover_still_lights_the_card(self):
        self._enter(self.button)
        self.assertEqual(self.skin.active, "colour")

    def test_the_layer_knows_no_audio(self):
        """maya_hubqt calls back; maya_hub plays (maya_hubsound)."""
        with open(hubqt.__file__, encoding="utf-8") as f:
            source = f.read()
        self.assertNotIn("hubsound", source)
        self.assertNotIn("QtMultimedia", source)


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


class Menu(unittest.TestCase):
    """2026-09-30: the right button's menu the inventory and the Characters
    grid share (Open scene)."""

    def setUp(self):
        self.app = _app()
        self.parent = QtWidgets.QWidget()
        self.addCleanup(self.parent.deleteLater)

    def test_rows_in_order_a_separator_and_a_disabled_row(self):
        go = lambda: "went"                                  # noqa: E731
        menu, rows = hubqt.build_menu(self.parent, [("Open scene", go), None,
                                                    ("Open scene (no rig)", None)])
        self.addCleanup(menu.deleteLater)
        actions = menu.actions()
        self.assertEqual([a.text() for a in actions],
                         ["Open scene", "", "Open scene (no rig)"])
        self.assertTrue(actions[1].isSeparator())
        self.assertEqual([a.isEnabled() for a in (actions[0], actions[2])],
                         [True, False])
        self.assertEqual([action for _row, action in rows], [go, None])
        self.assertIs(rows[0][0], actions[0])

    def test_no_rows_shows_no_menu(self):
        self.assertIsNone(hubqt.run_menu(self.parent, QtCore.QPoint(0, 0), []))


class CardMotion(SeamsMixin, unittest.TestCase):
    """2026-10-01: «открывать закрывать с какими-то анимациями» - the body
    slides, its children clipped, never squeezed."""

    def setUp(self):
        super(CardMotion, self).setUp()
        self.card = self.skin.add_card("colour", "Colour", "palette",
                                       "#c89be8", "#3a2a4a")
        self.child = QtWidgets.QWidget()
        self.child.setObjectName("motionChild")
        self.child.setFixedHeight(120)
        self.card.body_layout.addWidget(self.child)
        self.host.resize(400, 800)
        self.host.show()
        self._settle()

    def _settle(self):
        for _ in range(6):
            self.app.processEvents()

    def _at(self, fraction):
        anim = self.card._anim
        anim.setCurrentTime(int(anim.duration() * fraction))
        self._settle()

    def test_a_click_slides_the_body_shut(self):
        full = self.card.body.height()
        self.card.toggle()
        self.assertTrue(self.card.collapsed())
        self.assertTrue(self.card.sliding())
        self.assertEqual(self.card._anim.objectName(),
                         "skeldarHubCardSlide_colour")
        self.assertFalse(self.card.body.isHidden())
        self._at(0.5)
        self.assertLess(self.card.body.height(), full)
        self.assertGreater(self.card.body.height(), 0)
        self.assertEqual(self.child.height(), 120)          # clipped
        self._at(1.0)
        self.assertFalse(self.card.sliding())
        self.assertTrue(self.card.body.isHidden())
        self.assertEqual(self.card.body.maximumHeight(), 16777215)
        self.assertTrue(self.card.body_layout.isEnabled())

    def test_opening_slides_from_nothing_to_its_own_height(self):
        self.card.set_collapsed(True)
        self._settle()
        self.card.set_collapsed(False, animate=True)
        self.assertFalse(self.card.collapsed())
        self.assertTrue(self.card.sliding())
        self.assertFalse(self.card.body.isHidden())
        self.assertEqual(self.card.body.maximumHeight(), 0)
        natural = self.card.natural_height()
        self._at(0.5)
        self.assertGreater(self.card.body.height(), 0)
        self.assertLess(self.card.body.height(), natural)
        self.assertEqual(self.child.height(), 120)          # clipped
        self.assertFalse(self.card.body_layout.isEnabled())
        self._at(1.0)
        self.assertFalse(self.card.sliding())
        self.assertEqual(self.card.body.maximumHeight(), 16777215)
        self.assertTrue(self.card.body_layout.isEnabled())
        self.assertEqual(self.card.body.height(), natural)

    def test_opening_takes_longer_than_shutting(self):
        import maya_hubmotion as motion
        full = self.card.body.height()
        self.card.toggle()                                  # shutting
        self.assertEqual(self.card._anim.duration(),
                         motion.duration(full, 1.0))
        self._at(1.0)
        self.card.toggle()                                  # opening
        natural = self.card.natural_height()
        self.assertEqual(self.card._anim.duration(),
                         motion.duration(natural, 1.0, opening=True))
        self.assertGreater(motion.duration(natural, 1.0, opening=True),
                           motion.duration(full, 1.0))

    def test_a_second_click_mid_way_turns_it_back(self):
        self.card.toggle()
        self._at(0.4)
        self.card.toggle()
        self.assertFalse(self.card.collapsed())
        self.assertTrue(self.card.sliding())
        self._at(1.0)
        self.assertFalse(self.card.body.isHidden())
        self.assertEqual(self.card.body.height(), self.card.natural_height())

    def test_switched_off_it_is_instant(self):
        self.skin.animations = False
        self.card.toggle()
        self.assertFalse(self.card.sliding())
        self.assertTrue(self.card.body.isHidden())

    def test_code_without_animate_is_instant(self):
        self.card.set_collapsed(True)
        self.assertFalse(self.card.sliding())
        self.assertTrue(self.card.body.isHidden())

    def test_a_card_off_screen_is_instant(self):
        self.host.hide()
        self.card.toggle()
        self.assertFalse(self.card.sliding())
        self.assertTrue(self.card.body.isHidden())

    def test_set_collapsed_with_animate_does_not_call_back(self):
        self.card.set_collapsed(True, animate=True)
        self.assertEqual(self.calls, [])

    def test_the_chevron_turns_with_the_body(self):
        def image():
            return self.card.chevron.pixmap().toImage()
        down = image()
        self.card.toggle()
        self._at(0.5)
        self.assertGreater(self.card._angle, 0.0)
        self.assertLess(self.card._angle, 90.0)
        mid = image()
        self.assertEqual(mid.size(), down.size())
        self.assertNotEqual(mid, down)
        self._at(1.0)
        self.assertEqual(self.card._angle, 0.0)
        self.assertNotEqual(image(), mid)

    def test_the_header_keeps_its_height_while_sliding(self):
        """2026-10-01, the animator: «название заголовка "дрожит" во время
        анимации» - the header took the card's lag and its title, centred,
        shook. It is Fixed now, and the card is laid out every tick."""
        header = self.card.header
        self.assertEqual(header.sizePolicy().verticalPolicy(),
                         QtWidgets.QSizePolicy.Fixed)
        hint = header.sizeHint().height()
        for _ in range(2):                                 # shut, then open
            self.card.toggle()
            anim = self.card._anim
            for fraction in (0.1, 0.3, 0.5, 0.7, 0.9):
                #  read at the tick itself, before Qt's queue runs: what is
                #  painted next must already be laid out
                anim.setCurrentTime(int(anim.duration() * fraction))
                now = (header.height(), self.card.frame.height())
                self._settle()
                later = (header.height(), self.card.frame.height())
                self.assertEqual(now, later, fraction)
                self.assertEqual(now[0], hint, fraction)
            self._at(1.0)

    def test_the_gap_under_the_header_is_the_bodys_top_margin(self):
        """The column's spacing moved into the body's top margin, so it
        opens and shuts with the body; 4 since the compact skin
        (2026-10-08, it was 6)."""
        header = self.card.header
        bottom = header.y() + header.height()
        top = self.child.mapTo(self.card.frame, QtCore.QPoint(0, 0)).y()
        self.assertEqual(top - bottom, style.px(4, 1.0))


class Rotated(unittest.TestCase):

    def test_same_size_turned(self):
        _app()
        pix = hubqt.pixmap("chevron-right", "#9a9ca3", 14)
        turned = hubqt.rotated(pix, 90.0)
        self.assertEqual(turned.size(), pix.size())
        down = hubqt.pixmap("chevron-down", "#9a9ca3", 14).toImage()
        #  a quarter turn of right is down, to the antialiasing
        a, b = turned.toImage(), down
        diff = max(abs(a.pixelColor(x, y).alpha() - b.pixelColor(x, y).alpha())
                   for x in range(14) for y in range(14))
        self.assertLess(diff, 90)


class Glide(SeamsMixin, unittest.TestCase):
    """2026-10-01: a jump glides the scroll to its card."""

    def setUp(self):
        super(Glide, self).setUp()
        for key in ("a", "b", "c", "d"):
            card = self.skin.add_card(key, key.upper(), "user", "#f0a26b",
                                      "#4a3322")
            filler = QtWidgets.QWidget()
            filler.setFixedHeight(300)
            card.body_layout.addWidget(filler)
        self.host.resize(400, 500)
        self.host.show()
        self._settle()
        self.bar = self.skin.scroll.verticalScrollBar()

    def _settle(self):
        for _ in range(6):
            self.app.processEvents()

    def _to_end(self):
        glide = self.skin._glide
        glide.setCurrentTime(glide.duration())
        self._settle()

    def test_it_glides_onto_the_card(self):
        target = self.skin.cards["c"].frame.y()
        self.assertEqual(self.skin.scroll_to("c", animate=True), target)
        self.assertIsNotNone(self.skin._glide)
        self.assertEqual(self.skin._glide.objectName(), "skeldarHubGlide")
        self.assertEqual(self.bar.value(), 0)
        glide = self.skin._glide
        glide.setCurrentTime(glide.duration() // 2)
        self._settle()
        self.assertGreater(self.bar.value(), 0)
        self.assertLess(self.bar.value(), target)
        self._to_end()
        self.assertIsNone(self.skin._glide)
        self.assertEqual(self.bar.value(), min(target, self.bar.maximum()))

    def test_it_waits_for_the_other_cards_to_finish_sliding(self):
        """Live 2026-10-01: aimed while cards shut above, it overshot the
        shrinking range and was pulled back."""
        above = self.skin.cards["a"]
        above.toggle()                                      # sliding shut
        self.skin.scroll_to("c", animate=True)
        self.assertIsNone(self.skin._glide)
        self.assertIs(self.skin._glide_card, self.skin.cards["c"])
        self.assertTrue(self.skin._glide_wait.isActive())
        above._anim.setCurrentTime(above._anim.duration())
        self._settle()
        self.skin._glide_when_settled()
        self.assertIsNotNone(self.skin._glide)
        self.assertIsNone(self.skin._glide_card)
        self._to_end()
        self.assertEqual(self.bar.value(),
                         min(self.skin.cards["c"].frame.y(),
                             self.bar.maximum()))

    def test_the_wait_covers_every_slide(self):
        import maya_hubmotion as motion
        self.assertGreater(hubqt.GLIDE_WAIT_S * 1000.0,
                           motion.MAX_MS * motion.OPEN_FACTOR)

    def test_the_glide_lasts_while_its_card_still_opens(self):
        """An opening (1.5 times slower since 2026-10-01) may outlast
        SCROLL_MS; a glide that ended first stopped short of a card near
        the bottom, whose own opening is what lengthens the range."""
        import maya_hubmotion as motion
        card = self.skin.cards["d"]
        card.set_collapsed(True)
        self._settle()
        card.set_collapsed(False, animate=True)
        remaining = card._anim.duration() - card._anim.currentTime()
        self.assertGreater(remaining, motion.SCROLL_MS)
        self.skin.scroll_to("d", animate=True)
        self.assertGreaterEqual(self.skin._glide.duration(), remaining)
        card._anim.setCurrentTime(card._anim.duration())
        self._to_end()
        self.assertEqual(self.bar.value(),
                         min(card.frame.y(), self.bar.maximum()))

    def test_the_animator_s_own_scroll_stops_it(self):
        self.skin.scroll_to("d", animate=True)
        self.bar.triggerAction(QtWidgets.QAbstractSlider.SliderSingleStepAdd)
        self.assertIsNone(self.skin._glide)

    def test_without_animate_or_switched_off_it_jumps(self):
        self.skin.scroll_to("c")
        self.assertIsNone(self.skin._glide)
        self.assertEqual(self.bar.value(),
                         min(self.skin.cards["c"].frame.y(),
                             self.bar.maximum()))
        self.bar.setValue(0)
        self.skin.animations = False
        self.skin.scroll_to("c", animate=True)
        self.assertIsNone(self.skin._glide)
        self.assertGreater(self.bar.value(), 0)


class AnimationsRow(SeamsMixin, unittest.TestCase):

    def test_a_checkbox_painted_without_a_call(self):
        action = self.skin.animations_action
        self.assertTrue(action.isCheckable())
        self.skin.paint_animations(False)
        self.assertFalse(action.isChecked())
        self.assertFalse(self.skin.animations)
        self.skin.paint_animations(True)
        self.assertTrue(action.isChecked())
        self.assertTrue(self.skin.animations)
        self.assertEqual(self.calls, [])
        action.trigger()
        self.assertEqual(self.calls, [("animations", False)])


class CardLight(SeamsMixin, unittest.TestCase):
    """2026-10-01: «красивый глоу и анимацию подсветки при выделении карточки
    или наведении на раздел» - the light fades, a chosen card flashes."""

    def setUp(self):
        super(CardLight, self).setUp()
        for key in ("a", "b"):
            card = self.skin.add_card(key, key.upper(), "user", "#f0a26b",
                                      "#4a3322")
            filler = QtWidgets.QWidget()
            filler.setFixedHeight(120)
            card.body_layout.addWidget(filler)
        self.a, self.b = self.skin.cards["a"], self.skin.cards["b"]
        self.skin.finish(style.stylesheet())
        self.host.resize(400, 700)
        self.host.show()
        self._settle()

    def _settle(self):
        for _ in range(6):
            self.app.processEvents()

    def _end(self, anim):
        anim.setCurrentTime(anim.duration())
        self._settle()

    def test_a_hover_fades_the_new_card_up_and_the_old_down(self):
        import maya_hubmotion as motion
        self.skin._light("a")
        self.assertTrue(self.a.frame.property("skActive"))      # at once
        anim = self.a._light_anim
        self.assertEqual(anim.objectName(), "skeldarHubCardLight_a")
        self.assertEqual(anim.duration(), motion.LIGHT_IN_MS)
        anim.setCurrentTime(anim.duration() // 2)
        self.assertGreater(self.a.frame.level, 0.0)
        self.assertLess(self.a.frame.level, 1.0)
        self._end(anim)
        self.assertEqual(self.a.frame.level, 1.0)
        self.assertIsNone(self.a._light_anim)
        self.skin._light("b")
        self.assertFalse(self.a.frame.property("skActive"))
        self.assertEqual(self.a._light_anim.duration(), motion.LIGHT_OUT_MS)
        self._end(self.a._light_anim)
        self._end(self.b._light_anim)
        self.assertEqual((self.a.frame.level, self.b.frame.level), (0.0, 1.0))

    def test_turned_back_mid_way_it_goes_on_from_where_it_stands(self):
        self.skin._light("a")
        self.a._light_anim.setCurrentTime(self.a._light_anim.duration() // 2)
        mid = self.a.frame.level
        self.skin._light(None)
        self.assertAlmostEqual(self.a.frame.level, mid)
        self.assertLess(self.a._light_anim.duration(), 260)
        self._end(self.a._light_anim)
        self.assertEqual(self.a.frame.level, 0.0)

    def test_a_new_pick_flashes_the_same_pick_does_not(self):
        self.skin.set_active("a")
        flash = self.a._flash_anim
        self.assertIsNotNone(flash)
        flash.setCurrentTime(int(flash.duration() * 0.18))
        self.assertAlmostEqual(self.a.frame.flash, 1.0, places=2)
        self._end(flash)
        self.assertEqual(self.a.frame.flash, 0.0)
        self.skin.set_active("a")                     # a click inside it
        self.assertIsNone(self.a._flash_anim)
        self.skin.set_active("b")
        self.assertIsNotNone(self.b._flash_anim)

    def test_switched_off_the_light_switches_and_never_flashes(self):
        self.skin.animations = False
        self.skin.set_active("a")
        self.assertEqual(self.a.frame.level, 1.0)
        self.assertIsNone(self.a._light_anim)
        self.assertIsNone(self.a._flash_anim)
        self.skin._light("b")
        self.assertEqual((self.a.frame.level, self.b.frame.level), (0.0, 1.0))

    def _pixel(self, frame, x, y):
        image = frame.grab().toImage()
        colour = image.pixelColor(x, y)
        return colour.red(), colour.green(), colour.blue()

    def _near(self, rgb, hex_colour, tolerance=3):
        want = tuple(int(hex_colour[i:i + 2], 16) for i in (1, 3, 5))
        return all(abs(a - b) <= tolerance for a, b in zip(rgb, want))

    def test_the_painted_light(self):
        """Lit: the ring is card_edge and the face card_active (the look of
        2026-09-28); dark: both the plain card."""
        frame = self.a.frame
        x, ring_y = frame.width() // 2, 1
        face = (frame.width() // 2, frame.height() - 40)
        self.assertTrue(self._near(self._pixel(frame, x, ring_y),
                                   style.TOKENS["card"]))
        self.assertTrue(self._near(self._pixel(frame, *face),
                                   style.TOKENS["card"]))
        self.skin.animations = False
        self.skin._light("a")
        self._settle()
        ring = self._pixel(frame, x, ring_y)
        self.assertTrue(self._near(ring, style.TOKENS["card_edge"], 12), ring)
        self.assertTrue(self._near(self._pixel(frame, *face),
                                   style.TOKENS["card_active"]))
        #  the inner glow: warmer just inside the ring than in the face
        inside = self._pixel(frame, x, 4)
        middle = self._pixel(frame, *face)
        self.assertGreater((inside[0] - inside[2]) - (middle[0] - middle[2]),
                           15, (inside, middle))


class HoverGlow(SeamsMixin, unittest.TestCase):
    """2026-10-02: «все надпись немного подсвечивались легким свечением когда
    мы наводим на них мышкой» - every clickable control of the hub glows in
    its own ink's colour while the mouse is over it, fading in and out."""

    def setUp(self):
        SeamsMixin.setUp(self)
        self.card = self.skin.add_card("colour", "Colour", "palette",
                                       "#c89be8", "#3a2a4a")
        body = self.card.body
        layout = self.card.body_layout
        self.button = QtWidgets.QPushButton("Add", body)
        self.other = QtWidgets.QPushButton("Remove", body)
        self.segment = QtWidgets.QPushButton("Rig", body)
        self.segment.setCheckable(True)
        self.check = QtWidgets.QCheckBox("Timeline", body)
        self.combo = QtWidgets.QComboBox(body)
        self.label = QtWidgets.QLabel("status", body)
        self.field = QtWidgets.QLineEdit(body)
        for widget in (self.button, self.other, self.segment, self.check,
                       self.combo, self.label, self.field):
            layout.addWidget(widget)
        self.jump = self.skin.add_jump("colour", "Colour", "palette",
                                       "#c89be8")
        self.now = [100.0]
        self.skin.glow._clock = lambda: self.now[0]

    def _enter(self, widget):
        from PySide6 import QtCore as C, QtGui as G
        QtWidgets.QApplication.sendEvent(
            widget, G.QEnterEvent(C.QPointF(1, 1), C.QPointF(1, 1),
                                  C.QPointF(1, 1)))

    def _leave(self, widget):
        QtWidgets.QApplication.sendEvent(widget,
                                         QtCore.QEvent(QtCore.QEvent.Leave))

    def _at(self, ms):
        self.now[0] = 100.0 + ms / 1000.0
        self.skin.glow.tick()

    def _effect(self, widget):
        effect = widget.graphicsEffect()
        return effect if isinstance(effect, hubqt._glow_class()) else None

    # ---------------------------------------------------------------- what

    def test_what_glows_is_what_is_clickable(self):
        root = self.skin.root
        for widget in (self.button, self.segment, self.check, self.combo,
                       self.jump, self.skin.hotkeys, self.skin.pin,
                       self.skin.menu_button):
            self.assertTrue(hubqt.glowing(widget, root), widget)
        for widget in (self.label, self.field, self.card.body,
                       self.card.frame, self.skin.header, None):
            self.assertFalse(hubqt.glowing(widget, root), widget)

    def test_a_card_header_does_not_glow_its_card_lights(self):
        """«уберем свечение из надписей заголовков разделов мы и так разделы
        подсвечивали раньше» - the header still ticks and lights its card."""
        self.assertFalse(hubqt.glowing(self.card.header, self.skin.root))
        self.assertTrue(hubqt.sounding(self.card.header, self.skin.root))
        self._enter(self.card.header)
        self.assertIsNone(self.card.header.graphicsEffect())
        self.assertIsNone(self.skin.glow.lit)
        self.assertEqual(self.skin.active, "colour")
        title = self.card.header.findChild(QtWidgets.QLabel,
                                           "skeldarHubCardTitle_colour")
        self._enter(title)
        self.assertIsNone(self.skin.glow.lit)

    def test_not_disabled_not_a_swatch_not_a_foreign_effect(self):
        root = self.skin.root
        self.button.setEnabled(False)
        self.assertFalse(hubqt.glowing(self.button, root))
        self.other.setProperty("skRole", "swatch")
        self.assertFalse(hubqt.glowing(self.other, root))
        foreign = QtWidgets.QGraphicsOpacityEffect()
        self.segment.setGraphicsEffect(foreign)
        self.assertFalse(hubqt.glowing(self.segment, root))
        self._enter(self.segment)
        self.assertIs(self.segment.graphicsEffect(), foreign)
        self.assertIsNone(self.skin.glow.lit)

    def test_a_button_outside_the_hub_never(self):
        outside = QtWidgets.QPushButton("Maya")
        self._enter(outside)
        self.assertIsNone(outside.graphicsEffect())
        self.assertIsNone(self.skin.glow.lit)

    # --------------------------------------------------------------- fades

    def test_entering_fades_it_up(self):
        import maya_hubmotion as motion
        self._enter(self.button)
        effect = self._effect(self.button)
        self.assertIsNotNone(effect)
        self.assertIs(self.skin.glow.lit, effect)
        self.assertEqual(effect.mode, "ink")
        self.assertEqual(effect.level, 0.0)
        self._at(motion.GLOW_IN_MS / 2.0)
        self.assertGreater(effect.level, 0.0)
        self.assertLess(effect.level, 1.0)
        self._at(motion.GLOW_IN_MS)
        self.assertEqual(effect.level, 1.0)
        self.assertFalse(self.skin.glow._timer.isActive())

    def test_leaving_fades_it_down_and_keeps_the_effect(self):
        import maya_hubmotion as motion
        self._enter(self.button)
        self._at(motion.GLOW_IN_MS)
        effect = self._effect(self.button)
        self.assertTrue(effect.rising)
        self.now[0] = 200.0
        self._leave(self.button)
        self.assertIsNone(self.skin.glow.lit)
        self.assertFalse(effect.rising)                    # drawn directly
        self.now[0] = 200.0 + motion.GLOW_OUT_MS / 2000.0
        self.skin.glow.tick()
        self.assertGreater(effect.level, 0.0)
        self.assertLess(effect.level, 1.0)
        self.now[0] = 200.0 + motion.GLOW_OUT_MS / 1000.0
        self.skin.glow.tick()
        self.assertEqual(effect.level, 0.0)
        self.assertIs(self._effect(self.button), effect)   # kept, dark

    def test_a_dark_effect_is_disabled_so_qt_never_calls_it(self):
        """Every control hovered once keeps its effect; a sliding card
        repaints them all - dark, Qt paints them as if they had none."""
        import maya_hubmotion as motion
        self._enter(self.button)
        effect = self._effect(self.button)
        self.assertFalse(effect.isEnabled())               # not up yet
        self._at(motion.GLOW_IN_MS / 2.0)
        self.assertTrue(effect.isEnabled())
        self.now[0] = 300.0
        self._leave(self.button)
        self.now[0] = 301.0
        self.skin.glow.tick()
        self.assertEqual(effect.level, 0.0)
        self.assertFalse(effect.isEnabled())

    def test_one_at_a_time(self):
        self._enter(self.button)
        self._at(200)
        first = self._effect(self.button)
        self._enter(self.other)
        second = self._effect(self.other)
        self.assertIs(self.skin.glow.lit, second)
        self._at(600)
        self.assertEqual((first.level, second.level), (0.0, 1.0))

    def test_a_child_of_a_glowing_control_keeps_it_lit(self):
        """The mouse onto a child of the lit control (Maya builds some of
        its controls from several widgets): the control stays lit."""
        child = QtWidgets.QLabel("inner", self.button)
        self._enter(self.button)
        lit = self.skin.glow.lit
        self._enter(child)
        self.assertIs(self.skin.glow.lit, lit)
        self.assertIsNone(child.graphicsEffect())

    def test_the_card_body_darkens_it(self):
        self._enter(self.button)
        self._enter(self.card.body)
        self.assertIsNone(self.skin.glow.lit)

    def test_switched_off_it_switches_at_once(self):
        self.skin.paint_animations(False)
        self._enter(self.button)
        effect = self._effect(self.button)
        self.assertEqual(effect.level, 1.0)
        self.assertFalse(self.skin.glow._timer.isActive())
        self._leave(self.button)
        self.assertEqual(effect.level, 0.0)

    def test_switching_off_finishes_a_fade(self):
        self._enter(self.button)
        self._at(20)
        self.skin.paint_animations(False)
        self.assertEqual(self._effect(self.button).level, 1.0)
        self.assertFalse(self.skin.glow._timer.isActive())

    def test_the_primary_button_lights_its_rim(self):
        self.button.setProperty("skRole", "primary")
        self._enter(self.button)
        self.assertEqual(self._effect(self.button).mode, "rim")

    def test_a_control_deleted_mid_fade_is_dropped(self):
        import shiboken6
        self._enter(self.button)
        effect = self._effect(self.button)
        shiboken6.delete(self.button)
        self.assertFalse(shiboken6.isValid(effect))
        self._at(50)                                       # no error
        self.assertIsNone(self.skin.glow.lit)
        self.assertNotIn(effect, self.skin.glow.effects)
        self.assertFalse(self.skin.glow._timer.isActive())
        self._enter(self.other)                            # still works
        self.assertIsNotNone(self.skin.glow.lit)

    def test_destroy_stops_it(self):
        self._enter(self.button)
        self.skin.destroy()
        self.assertEqual(self.skin.glow.effects, [])
        self.assertIsNone(self.skin.glow.lit)

    def test_the_effects_are_held(self):
        """PySide deletes an effect whose wrapper is collected (measured
        2026-10-02): the glower holds every one it made."""
        import gc
        self._enter(self.button)
        self._enter(self.other)
        gc.collect()
        self.assertIsNotNone(self._effect(self.button))
        self.assertEqual(len(self.skin.glow.effects), 2)


class HoverGlowPaint(unittest.TestCase):
    """The effect's own picture: light added round a button's letters, the
    letters and everything far from them left alone, the glow cached."""

    def setUp(self):
        self.app = _app()
        self.host = QtWidgets.QWidget()
        self.host.setStyleSheet(
            "QWidget { background: #2a2c30; }"
            "QPushButton { background: #34363b; color: #e4e4e6; border: none;"
            " font-size: 14px; padding: 6px 14px; }")
        layout = QtWidgets.QVBoxLayout(self.host)
        layout.setContentsMargins(30, 30, 30, 30)
        self.button = QtWidgets.QPushButton("Camera Setup")
        layout.addWidget(self.button)
        self.host.resize(260, 110)
        self.host.show()
        for _ in range(4):
            self.app.processEvents()
        self.effect = hubqt._glow_class()("ink", 1.0)
        self.button.setGraphicsEffect(self.effect)

    def tearDown(self):
        self.host.deleteLater()

    def _pixels(self, image):
        import numpy as np
        from PySide6 import QtGui
        image = image.convertToFormat(QtGui.QImage.Format_RGB32)
        w, h, bpl = image.width(), image.height(), image.bytesPerLine()
        data = np.frombuffer(image.constBits(), np.uint8, count=bpl * h)
        return data.reshape(h, bpl // 4, 4)[:, :w, :3].astype(int)

    def _grab(self, level):
        self.effect.level = level
        self.effect.update()
        return self._pixels(self.host.grab().toImage())

    def test_light_round_the_letters_and_nothing_else(self):
        import numpy as np
        import maya_hubglow
        dark = self._grab(0.0)
        lit = self._grab(1.0)
        diff = lit - dark
        self.assertGreaterEqual(int(diff.min()), -1)        # only adds
        self.assertGreater(int(diff.max()), 25)             # it glows
        rect = self.button.geometry()
        reach = maya_hubglow.pad(1.0) + 1
        outside = np.ones(diff.shape[:2], bool)
        outside[max(0, rect.top() - reach):rect.bottom() + reach + 1,
                max(0, rect.left() - reach):rect.right() + reach + 1] = False
        self.assertEqual(int(np.abs(diff[outside]).max()), 0)
        #  the letters' cores stay the letters' colour
        bright = dark.min(axis=2) > 200
        self.assertTrue(bright.any())
        self.assertLessEqual(int(np.abs(diff[bright]).max()), 25)

    def test_the_glow_is_computed_once_per_picture(self):
        self._grab(1.0)
        self._grab(0.5)
        self._grab(1.0)
        self.assertEqual(self.effect.computed, 1)
        self.button.setText("Camera Setup...")
        self._grab(1.0)
        self.assertEqual(self.effect.computed, 2)

    def test_level_zero_draws_the_control_as_it_is(self):
        import numpy as np
        dark = self._grab(0.0)
        self.button.setGraphicsEffect(None)
        plain = self._pixels(self.host.grab().toImage())
        self.assertEqual(int(np.abs(dark - plain).max()), 0)

    def test_a_failing_glow_draws_the_plain_control_from_then_on(self):
        import maya_hubglow
        saved = maya_hubglow.bloom

        def broken(*_a, **_k):
            raise ValueError("no numpy today")
        maya_hubglow.bloom = broken
        try:
            dark = self._grab(0.0)
            lit = self._grab(1.0)
        finally:
            maya_hubglow.bloom = saved
        self.assertTrue(self.effect.broken)
        self.assertIn("no numpy today", self.effect.error)
        self.assertEqual(int(abs(lit - dark).max()), 0)

    def test_going_dark_draws_the_control_directly(self):
        """Fading out, the control is drawn as Qt draws it (its own
        ClearType text back as the hover style comes off), the lit
        picture's glow over it - no new source pixmap."""
        import numpy as np
        dark = self._grab(0.0)
        self._grab(1.0)
        drawn = self.effect.from_pixmap
        self.assertGreaterEqual(drawn, 1)
        self.effect.rising = False
        fading = self._grab(0.6)
        self.assertEqual(self.effect.from_pixmap, drawn)
        diff = fading - dark
        self.assertGreaterEqual(int(diff.min()), -1)
        self.assertGreater(int(diff.max()), 10)

    def test_going_dark_the_glow_follows_the_control(self):
        import numpy as np
        import maya_hubglow
        self._grab(1.0)
        self.effect.rising = False
        self.host.layout().setContentsMargins(30, 50, 30, 10)
        for _ in range(4):
            self.app.processEvents()
        dark = self._grab(0.0)
        self.effect.rising = False
        self.effect.level = 1.0
        fading = self._grab(1.0)
        diff = np.abs(fading - dark).max(axis=2)
        rect = self.button.geometry()
        reach = maya_hubglow.pad(1.0) + 1
        outside = np.ones(diff.shape, bool)
        outside[max(0, rect.top() - reach):rect.bottom() + reach + 1,
                max(0, rect.left() - reach):rect.right() + reach + 1] = False
        self.assertGreater(int(diff.max()), 10)
        self.assertEqual(int(diff[outside].max()), 0)

    def test_a_working_glow_is_not_broken(self):
        self._grab(1.0)
        self.assertFalse(self.effect.broken, self.effect.error)
        self.assertEqual(self.effect.computed, 1)
