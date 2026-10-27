"""maya_hub - the header's dressing, the ⋮ menu's switches, the rail's helpers,
the window sections, the things queued at Maya's start, on fakes.

Every module the hub reaches lazily (maya_update, maya_timebar, ...) is a fake
put into `sys.modules` for the test and taken out after; Maya's commands are a
recording fake; the skin is a recording fake (`RecordingSkin`).
"""

import contextlib
import io
import os
import sys
import types
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tests  # noqa: F401

from PySide6 import QtCore, QtWidgets

import maya_edgerules as edgerules
import maya_hub as hub
import maya_hubqt

from tests.uifakes import FakeUiCmds

_MISSING = object()


def _app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@contextlib.contextmanager
def fake_modules(**modules):
    """`sys.modules[name]` = the fake for the block (None: the import fails),
    each entry put back as it was after."""
    saved = dict((name, sys.modules.get(name, _MISSING)) for name in modules)
    try:
        for name, module in modules.items():
            sys.modules[name] = module
        yield
    finally:
        for name, module in saved.items():
            if module is _MISSING:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module


def module(name, **attrs):
    fake = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(fake, key, value)
    return fake


def broken(name):
    """A module whose every attribute raises when called."""
    def boom(*_a, **_k):
        raise RuntimeError(name + " is broken")
    fake = types.ModuleType(name)
    fake.__getattr__ = lambda attr: boom
    return fake


class GuiCmds(FakeUiCmds):
    """The fake with a GUI (`about -batch` False unless asked) and optionVar
    removal."""

    def __init__(self, batch=False):
        super(GuiCmds, self).__init__()
        self.batch = batch

    def about(self, **kwargs):
        return self.batch

    def optionVar(self, **kwargs):
        if "remove" in kwargs:
            self.optionvars.pop(kwargs["remove"], None)
            return None
        return super(GuiCmds, self).optionVar(**kwargs)


class RecordingSkin(object):
    """maya_hubqt.Skin as the hub drives it: every method it is asked for is
    recorded; the few the hub reads back answer."""

    def __init__(self):
        self.calls = []
        self.cards = {}
        self.shown = None
        self.jumps = {}
        self.scale = 1.5
        self.host = None
        self.layout = "accordion"
        self.windowed = False
        self._alive = True

    def alive(self):
        return self._alive

    def destroy(self):
        self._alive = False

    def show_card(self, key, animate=True):
        self.calls.append(("show_card", key, animate))
        if key not in self.cards:
            return None
        self.shown = key
        return self.cards[key]

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)

        def record(*args, **kwargs):
            self.calls.append((name,) + args + tuple(sorted(kwargs.items())))
        return record

    def named(self, name):
        return [call[1:] for call in self.calls if call[0] == name]


class FakeEdge(object):

    def __init__(self, rail=True, shown=False):
        self.rail, self.shown = rail, shown
        self.slot = object()
        self.host = "edgeHost"
        self.scale = 1.5
        self.reveals, self.conceals = [], []

    def alive(self):
        return True

    def reveal(self, hold=False, origin=None):
        self.reveals.append(origin)
        self.shown = True

    def conceal(self, origin=None):
        self.conceals.append(origin)
        self.shown = False


class HubCase(unittest.TestCase):
    """The hub's cmds, Qt layer, edge layer and skin faked; put back after."""

    def setUp(self):
        self.app = _app()
        self.real = (hub.cmds, hub._hubqt, hub._hubedge, hub._SKIN,
                     hub._EDGE_FAILED, hub._EDGE_FAILURE)
        self.cmds = GuiCmds()
        hub.cmds = self.cmds
        self.qt = types.SimpleNamespace(
            available=lambda: True, qt=maya_hubqt.qt, _valid=maya_hubqt._valid,
            feature=lambda name: False)
        hub._hubqt = lambda: self.qt
        self.edge_state = {"edge": None}
        hub._hubedge = lambda: types.SimpleNamespace(
            state=lambda: self.edge_state)
        hub._SKIN = None
        hub._EDGE_FAILED = False
        hub._EDGE_FAILURE = ""
        self.made = []
        #  the badges and the chat window a skin reads live on sys
        self.saved_sys = dict((name, getattr(sys, name, _MISSING)) for name in
                              ("_skeldar_hub_badges", "_skeldar_chat_window"))
        for name in self.saved_sys:
            if hasattr(sys, name):
                delattr(sys, name)

    def tearDown(self):
        (hub.cmds, hub._hubqt, hub._hubedge, hub._SKIN, hub._EDGE_FAILED,
         hub._EDGE_FAILURE) = self.real
        for name, value in self.saved_sys.items():
            if value is _MISSING:
                if hasattr(sys, name):
                    delattr(sys, name)
            else:
                setattr(sys, name, value)
        for widget in self.made:
            widget.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)

    def skin(self):
        hub._SKIN = RecordingSkin()
        return hub._SKIN

    def printed(self, fn, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = fn(*args)
        return result, out.getvalue()


# ------------------------------------------------------------ the header

def _header_modules(calls):
    """Every module `_dress_header` reaches, each answering something of its
    own so the paints can be told apart."""
    return dict(
        maya_update=module(
            "maya_update", installed_dir=lambda: "C:/installed",
            read_record=lambda folder: {"short": "abc1234", "folder": folder},
            describe=lambda record, subject=True: "abc1234 (2026-10-27)"),
        maya_hotkeys=module("maya_hotkeys", is_active=lambda: True),
        maya_hubsound=module(
            "maya_hubsound", enabled=lambda: True, RECORDED=("drag", "delete"),
            preload=lambda name: calls.append(("preload", name))),
        maya_hubmotion=module("maya_hubmotion", enabled=lambda: False),
        maya_mayatheme=module("maya_mayatheme", enabled=lambda: True),
        maya_mayaicons=module("maya_mayaicons", enabled=lambda: False),
        maya_viewportbar=module("maya_viewportbar", enabled=lambda: True),
        maya_mainbar=module("maya_mainbar", enabled=lambda: False),
        maya_camview=module("maya_camview", enabled=lambda: True),
        maya_windowlight=module("maya_windowlight", enabled=lambda: True,
                                maya_enabled=lambda: False),
        maya_timebar=module("maya_timebar", mode=lambda: "edge",
                            steel=lambda: True),
        maya_atbar=module("maya_atbar", layout=lambda: "compact"),
        maya_sidepanel=module("maya_sidepanel", mode=lambda: "right",
                              on_select=lambda: False),
        maya_channelbox=module("maya_channelbox", enabled=lambda: True),
        maya_interface=module("maya_interface", current=lambda: "skeldar"),
        maya_hubpop=module("maya_hubpop", open_keys=lambda: ["tools"]))


class DressHeader(HubCase):

    def test_every_row_and_switch_is_painted_from_what_stands(self):
        skin = RecordingSkin()
        calls = []
        self.cmds.optionvars[edgerules.SIDE_VAR] = "right"
        with fake_modules(**_header_modules(calls)):
            hub._dress_header(skin)
        self.assertEqual(skin.named("set_version"),
                         [("abc1234", "Installed: abc1234 (2026-10-27) - "
                           "press to check for an update")])
        self.assertEqual(skin.named("paint_hotkeys"), [(True,)])
        self.assertEqual(skin.named("paint_sounds"), [(True,)])
        self.assertEqual(calls, [("preload", "drag"), ("preload", "delete")])
        self.assertEqual(skin.named("paint_animations"), [(False,)])
        self.assertEqual(skin.named("paint_mayatheme"), [(True,)])
        self.assertEqual(skin.named("paint_mayaicons"), [(False,)])
        self.assertEqual(skin.named("paint_viewportbar"), [(True,)])
        self.assertEqual(skin.named("paint_mainbar"), [(False,)])
        self.assertEqual(skin.named("paint_camview"), [(True,)])
        self.assertEqual(skin.named("paint_windowlight"), [(True, False)])
        self.assertEqual(skin.named("paint_timebar"), [("edge", True, "compact")])
        self.assertEqual(skin.named("paint_sidepanel"), [("right", False, True)])
        self.assertEqual(skin.named("paint_interface"), [("skeldar",)])
        self.assertEqual(skin.named("paint_edge"), [(False, "right")])
        self.assertEqual(skin.named("set_popped"), [("tools", True)])
        self.assertEqual(skin.named("set_floating"), [("tools", True)])

    def test_sounds_off_open_no_audio(self):
        skin = RecordingSkin()
        calls = []
        modules = _header_modules(calls)
        modules["maya_hubsound"].enabled = lambda: False
        with fake_modules(**modules):
            hub._dress_header(skin)
        self.assertEqual(skin.named("paint_sounds"), [(False,)])
        self.assertEqual(calls, [])

    def test_the_installed_build_s_name_falls_back(self):
        for record, short in (({"commit": "0123456789abcdef"}, "0123456"),
                              ({"source": True}, "source"), ({}, "?")):
            skin = RecordingSkin()
            modules = _header_modules([])
            modules["maya_update"].read_record = lambda folder, r=record: r
            with fake_modules(**modules):
                hub._dress_header(skin)
            self.assertEqual(skin.named("set_version")[0][0], short, record)

    def test_an_update_module_that_fails_still_offers_check_update(self):
        skin = RecordingSkin()
        modules = _header_modules([])
        modules["maya_update"] = broken("maya_update")
        with fake_modules(**modules):
            _result, out = self.printed(hub._dress_header, skin)
        self.assertEqual(skin.named("set_version"), [("?", "Check update")])
        self.assertIn("maya_update is broken", out)

    def test_every_row_whose_module_fails_is_printed_and_skipped(self):
        """A switch whose module cannot be read must never cost the hub."""
        skin = RecordingSkin()
        names = [name for name in _header_modules([])]
        modules = dict((name, broken(name)) for name in names)
        with fake_modules(**modules):
            _result, out = self.printed(hub._dress_header, skin)
        painted = [c[0] for c in skin.calls]
        self.assertEqual(painted, ["set_version", "paint_edge"])
        for name in ("maya_hotkeys", "maya_hubsound", "maya_hubmotion",
                     "maya_mayatheme", "maya_mayaicons", "maya_viewportbar",
                     "maya_mainbar", "maya_camview", "maya_windowlight",
                     "maya_timebar", "maya_sidepanel", "maya_interface",
                     "maya_hubpop"):
            self.assertIn(name + " is broken", out, name)

    def test_the_box_and_the_at_bar_are_none_when_unreadable(self):
        with fake_modules(maya_channelbox=None, maya_atbar=None):
            self.assertIsNone(hub._box_on())
            self.assertIsNone(hub._at_on())
        with fake_modules(
                maya_channelbox=module("maya_channelbox", enabled=lambda: False),
                maya_atbar=module("maya_atbar", layout=lambda: "full")):
            self.assertFalse(hub._box_on())
            self.assertEqual(hub._at_on(), "full")


class Badges(HubCase):

    def test_a_skin_built_later_shows_the_counts_kept(self):
        hub.paint_badge("chat", 3)
        hub.paint_badge("stash", 0)
        skin = RecordingSkin()
        hub._dress_badges(skin)
        self.assertEqual(skin.named("set_badge"), [("chat", 3)])

    def test_a_standing_skin_is_told_at_once(self):
        skin = self.skin()
        self.assertEqual(hub.paint_badge("chat", None), 0)
        self.assertEqual(skin.named("set_badge"), [("chat", None)])
        self.assertEqual(hub._badges()["chat"], 0)

    def test_a_chat_window_standing_keeps_its_rail_dot(self):
        root = QtWidgets.QWidget()
        root.show()
        self.made.append(root)
        sys._skeldar_chat_window = {"win": types.SimpleNamespace(root=root)}
        skin = RecordingSkin()
        hub._dress_badges(skin)
        self.assertEqual(skin.named("set_floating"), [("chat", True)])
        root.hide()
        skin = RecordingSkin()
        hub._dress_badges(skin)
        self.assertEqual(skin.named("set_floating"), [])

    def test_a_chat_window_whose_root_is_deleted_is_passed_over(self):
        root = QtWidgets.QWidget()
        sys._skeldar_chat_window = {"win": types.SimpleNamespace(root=root)}
        import shiboken6
        shiboken6.delete(root)
        skin = RecordingSkin()
        hub._dress_badges(skin)
        self.assertEqual(skin.named("set_floating"), [])

    def test_a_broken_badge_store_is_printed_not_raised(self):
        sys._skeldar_hub_badges = "not a dict"
        skin = RecordingSkin()
        _result, out = self.printed(hub._dress_badges, skin)
        self.assertIn("AttributeError", out)


# ------------------------------------------------------- queued at the start

class QueuedAtStart(HubCase):
    """Every switch Maya's start brings up is deferred, guarded, and does
    nothing in batch."""

    SOON = (
        ("_chat_soon", "maya_chat", "ensure"),
        ("_main_bar_soon", "maya_mainbar", "ensure"),
        ("_windowlight_soon", "maya_windowlight", "ensure"),
        ("_camview_soon", "maya_camview", "ensure"),
        ("_viewport_bar_soon", "maya_viewportbar", "ensure"),
        ("_side_panel_soon", "maya_sidepanel", "ensure"),
        ("_hotkeys_soon", "maya_hotkeys", "catch_up"),
    )

    def test_each_one_is_queued_and_runs_its_module(self):
        for soon, name, call in self.SOON:
            ran = []
            fake = module(name, **{call: lambda ran=ran: ran.append(1)})
            self.cmds.deferred = []
            getattr(hub, soon)()
            self.assertEqual(len(self.cmds.deferred), 1, soon)
            with fake_modules(**{name: fake}):
                self.cmds.run_deferred()
            self.assertEqual(ran, [1], soon)

    def test_a_failing_one_is_printed_not_raised(self):
        for soon, name, _call in self.SOON:
            self.cmds.deferred = []
            getattr(hub, soon)()
            with fake_modules(**{name: broken(name)}):
                _result, out = self.printed(self.cmds.run_deferred)
            self.assertIn("SkeldarAnim:", out, soon)
            self.assertIn(name + " is broken", out, soon)

    def test_nothing_is_queued_in_batch(self):
        self.cmds.batch = True
        for soon in [s[0] for s in self.SOON] + [
                "_time_bar_soon", "_tabs_bar_soon", "_maya_theme_soon",
                "_maya_icons_soon"]:
            getattr(hub, soon)()
        self.assertEqual(self.cmds.deferred, [])

    def test_the_time_bar_and_then_the_at_bar(self):
        ran = []
        hub._time_bar_soon()
        with fake_modules(
                maya_timebar=module("maya_timebar",
                                    ensure=lambda: ran.append("timebar")),
                maya_atbar=module("maya_atbar",
                                  ensure_wanted=lambda: ran.append("atbar"))):
            self.cmds.run_deferred()
        self.assertEqual(ran, ["timebar", "atbar"])

    def test_a_broken_time_bar_still_brings_the_at_bar(self):
        ran = []
        hub._time_bar_soon()
        with fake_modules(
                maya_timebar=broken("maya_timebar"),
                maya_atbar=module("maya_atbar",
                                  ensure_wanted=lambda: ran.append("atbar"))):
            _result, out = self.printed(self.cmds.run_deferred)
        self.assertEqual(ran, ["atbar"])
        self.assertIn("the time bar could not be shown", out)
        hub._time_bar_soon()
        with fake_modules(maya_timebar=module("maya_timebar",
                                              ensure=lambda: None),
                          maya_atbar=broken("maya_atbar")):
            _result, out = self.printed(self.cmds.run_deferred)
        self.assertIn("the AT bar could not be shown", out)

    def scenetabs(self, ran):
        hooks = module("maya_scenetabs.hooks",
                       install=lambda: ran.append("hooks"))
        bar = module("maya_scenetabs.bar",
                     ensure_docked=lambda: ran.append("bar"))
        return module("maya_scenetabs", hooks=hooks, bar=bar)

    def test_the_tabs_bar_shows_after_its_hooks(self):
        ran = []
        hub._tabs_bar_soon()
        with fake_modules(maya_scenetabs=self.scenetabs(ran)):
            self.cmds.run_deferred()
        self.assertEqual(ran, ["hooks", "bar"])

    def test_a_tabs_bar_hidden_from_its_menu_keeps_the_hooks(self):
        ran = []
        self.cmds.optionvars[hub.TABS_BAR_VAR] = 0
        hub._tabs_bar_soon()
        with fake_modules(maya_scenetabs=self.scenetabs(ran)):
            self.cmds.run_deferred()
        self.assertEqual(ran, ["hooks"])

    def test_a_tabs_bar_that_fails_is_printed(self):
        hub._tabs_bar_soon()
        with fake_modules(maya_scenetabs=None):
            _result, out = self.printed(self.cmds.run_deferred)
        self.assertIn("the scene tabs bar could not be shown", out)

    def test_maya_s_look_flags_off_and_left_off_say_nothing(self):
        for soon, name in (("_maya_theme_soon", "maya_mayatheme"),
                           ("_maya_icons_soon", "maya_mayaicons")):
            calls = []
            fake = module(name, enabled=lambda: False,
                          ensure=lambda: calls.append("ensure"),
                          set_enabled=lambda on: calls.append(on))
            getattr(hub, soon)()
            with fake_modules(**{name: fake}):
                _result, out = self.printed(self.cmds.run_deferred)
            self.assertEqual((calls, out), ([], ""), soon)

    def test_maya_s_look_left_on_with_its_flag_off_is_switched_off(self):
        for soon, name in (("_maya_theme_soon", "maya_mayatheme"),
                           ("_maya_icons_soon", "maya_mayaicons")):
            calls = []
            fake = module(name, enabled=lambda: True,
                          set_enabled=lambda on: calls.append(on) or "off now")
            getattr(hub, soon)()
            with fake_modules(**{name: fake}):
                _result, out = self.printed(self.cmds.run_deferred)
            self.assertEqual(calls, [False], soon)
            self.assertIn("SkeldarAnim: off now", out, soon)

    def test_maya_s_look_that_fails_is_printed(self):
        for soon, name, said in (
                ("_maya_theme_soon", "maya_mayatheme", "Maya theme"),
                ("_maya_icons_soon", "maya_mayaicons", "Maya icons")):
            getattr(hub, soon)()
            with fake_modules(**{name: broken(name)}):
                _result, out = self.printed(self.cmds.run_deferred)
            self.assertIn("the " + said + " could not be applied", out)


# ----------------------------------------------------------- the ⋮ switches

def _switch_module(name, message="said", **extra):
    state = {"on": None}

    def set_enabled(on):
        state["on"] = on
        return message
    fake = module(name, set_enabled=set_enabled,
                  enabled=lambda: state["on"], **extra)
    fake.state = state
    return fake


class MenuSwitches(HubCase):

    SIMPLE = (
        (hub.set_mayatheme, "maya_mayatheme", "paint_mayatheme"),
        (hub.set_mayaicons, "maya_mayaicons", "paint_mayaicons"),
        (hub.set_viewportbar, "maya_viewportbar", "paint_viewportbar"),
        (hub.set_mainbar, "maya_mainbar", "paint_mainbar"),
        (hub.set_camview, "maya_camview", "paint_camview"),
    )

    def test_each_switch_is_set_painted_and_said(self):
        for setter, name, paint in self.SIMPLE:
            skin = self.skin()
            fake = _switch_module(name, message=name + " ON")
            with fake_modules(**{name: fake}):
                self.assertEqual(setter(True), name + " ON")
            self.assertTrue(fake.state["on"])
            self.assertEqual(skin.named(paint), [(True,)], name)
            self.assertEqual(skin.named("say"), [(name + " ON", ("state", None))],
                             name)

    def test_without_a_skin_a_switch_is_only_set(self):
        for setter, name, _paint in self.SIMPLE:
            fake = _switch_module(name, message="m")
            with fake_modules(**{name: fake}):
                self.assertEqual(setter(False), "m")
            self.assertIs(fake.state["on"], False)

    def test_the_window_light_switches_paint_both_rows(self):
        skin = self.skin()
        state = {"on": True, "maya": True}
        fake = module(
            "maya_windowlight",
            set_enabled=lambda on: state.update(on=on) or "light",
            set_maya_enabled=lambda on: state.update(maya=on) or "maya",
            enabled=lambda: state["on"], maya_enabled=lambda: state["maya"])
        with fake_modules(maya_windowlight=fake):
            self.assertEqual(hub.set_windowlight(False), "light")
            self.assertEqual(hub.set_windowlight_maya(False), "maya")
        self.assertEqual(skin.named("paint_windowlight"),
                         [(False, True), (False, False)])
        self.assertEqual([s[0] for s in skin.named("say")], ["light", "maya"])

    def test_sounds_and_animations_are_set_and_painted(self):
        skin = self.skin()
        with fake_modules(
                maya_hubsound=module("maya_hubsound", set_enabled=bool),
                maya_hubmotion=module("maya_hubmotion", set_enabled=bool)):
            self.assertTrue(hub.set_sounds(1))
            self.assertFalse(hub.set_animations(0))
        self.assertEqual(skin.named("paint_sounds"), [(True,)])
        self.assertEqual(skin.named("paint_animations"), [(False,)])

    def interface_modules(self, log):
        return dict(
            maya_interface=module("maya_interface",
                                  use=lambda choice: "using " + choice,
                                  current=lambda: "maya"),
            maya_timebar=module("maya_timebar", mode=lambda: "maya",
                                steel=lambda: False,
                                set_on=lambda c: "timebar " + str(c),
                                set_steel=lambda on: "steel " + str(on)),
            maya_atbar=module("maya_atbar", layout=lambda: "off",
                              ensure_wanted=lambda: log.append("at"),
                              set_layout=lambda c: "at " + str(c)),
            maya_sidepanel=module("maya_sidepanel", mode=lambda: "maya",
                                  on_select=lambda: True,
                                  set_mode=lambda c: "side " + c,
                                  set_on_select=lambda on: "select " + str(on)),
            maya_channelbox=module("maya_channelbox", enabled=lambda: False,
                                   set_enabled=lambda on: "box " + str(on)),
            maya_viewportbar=module("maya_viewportbar", enabled=lambda: False),
            maya_mainbar=module("maya_mainbar", enabled=lambda: False),
            maya_update=module("maya_update",
                               paint_interface=lambda: log.append("card")))

    def test_the_interface_switch_repaints_every_row_and_the_update_card(self):
        skin = self.skin()
        log = []
        with fake_modules(**self.interface_modules(log)):
            self.assertEqual(hub.set_interface("maya"), "using maya")
        self.assertEqual(skin.named("paint_timebar"), [("maya", False, "off")])
        self.assertEqual(skin.named("paint_sidepanel"), [("maya", True, False)])
        self.assertEqual(skin.named("paint_viewportbar"), [(False,)])
        self.assertEqual(skin.named("paint_mainbar"), [(False,)])
        self.assertEqual(skin.named("paint_interface"), [("maya",)])
        self.assertEqual(log, ["card"])
        self.assertEqual(skin.named("say")[-1][0], "using maya")

    def test_repainting_with_no_skin_still_paints_the_update_card(self):
        log = []
        with fake_modules(**self.interface_modules(log)):
            hub.repaint_interface()
            hub.repaint_sidepanel()
        self.assertEqual(log, ["card", "card"])

    def test_an_update_card_that_fails_to_paint_is_quiet(self):
        self.skin()
        modules = self.interface_modules([])
        modules["maya_update"] = broken("maya_update")
        with fake_modules(**modules):
            hub.repaint_interface()                       # does not raise

    def test_the_time_bar_switch_brings_the_at_bar_along(self):
        skin = self.skin()
        log = []
        with fake_modules(**self.interface_modules(log)):
            self.assertEqual(hub.set_timebar("edge"), "timebar edge")
        self.assertEqual(log, ["at", "card"])
        self.assertEqual(skin.named("say")[-1][0], "timebar edge")

    def test_an_at_bar_that_fails_does_not_stop_the_time_bar_switch(self):
        modules = self.interface_modules([])
        modules["maya_atbar"] = module("maya_atbar", layout=lambda: "off")
        with fake_modules(**modules):
            result, out = self.printed(hub.set_timebar, "docked")
        self.assertEqual(result, "timebar docked")
        self.assertIn("ensure_wanted", out)

    def test_steel_keys_and_the_at_bar_paint_the_time_bar_row(self):
        skin = self.skin()
        with fake_modules(**self.interface_modules([])):
            self.assertEqual(hub.set_timebar_steel(True), "steel True")
            self.assertEqual(hub.set_timebar_at("compact"), "at compact")
        self.assertEqual(skin.named("paint_timebar"),
                         [("maya", False, "off"), ("maya", False, "off")])

    def test_the_side_panel_switches(self):
        skin = self.skin()
        log = []
        with fake_modules(**self.interface_modules(log)):
            self.assertEqual(hub.set_sidepanel("right"), "side right")
            self.assertEqual(hub.set_sidepanel_select(False), "select False")
            self.assertEqual(hub.set_sidepanel_box(True), "box True")
        self.assertEqual(skin.named("paint_sidepanel")[:2],
                         [("maya", True), ("maya", True, False)])
        self.assertEqual([s[0] for s in skin.named("say")],
                         ["side right", "select False", "box True"])

    def test_no_skin_no_paint_for_the_time_bar_and_side_panel(self):
        with fake_modules(**self.interface_modules([])):
            self.assertEqual(hub.set_timebar_steel(False), "steel False")
            self.assertEqual(hub.set_timebar_at(False), "at False")
            self.assertEqual(hub.set_sidepanel_select(True), "select True")


class MenuCallbacks(HubCase):

    def test_classic_look_is_remembered_and_rebuilt_deferred(self):
        hub._callbacks()["classic"]()
        self.assertEqual(self.cmds.optionvars[hub.CLASSIC_VAR], 1)
        self.assertEqual(self.cmds.deferred, [hub.rebuild])

    def test_every_callback_is_a_hub_function(self):
        callbacks = hub._callbacks()
        for name, fn in callbacks.items():
            self.assertTrue(callable(fn), name)
        wanted = {"hotkeys": hub._press_hotkeys, "jump": hub.focus,
                  "toggled": hub.remember, "close": hub._press_rail_close,
                  "told": hub._told, "hover": hub._hover_sound,
                  "pin": hub._press_pin, "edge": hub.set_edge,
                  "edge_side": hub.set_edge_side,
                  "windowlight_maya": hub.set_windowlight_maya,
                  "sidepanel_box": hub.set_sidepanel_box}
        for name, fn in wanted.items():
            self.assertIs(callbacks[name], fn, name)

    def test_the_hover_is_silent(self):
        self.assertFalse(hub._hover_sound())

    def test_a_layout_that_is_no_layout_is_the_rail(self):
        self.assertEqual(hub.set_layout("nonsense"), "rail")
        self.assertEqual(self.cmds.optionvars[hub.LAYOUT_VAR], "rail")

    def test_the_hotkey_map_s_switch_paints_and_says(self):
        skin = self.skin()
        state = {"on": False}

        def toggle():
            state["on"] = not state["on"]
            return "Hotkey map ON"
        with fake_modules(maya_hotkeys=module(
                "maya_hotkeys", toggle=toggle, is_active=lambda: state["on"])):
            self.assertEqual(hub._press_hotkeys(), "Hotkey map ON")
        self.assertEqual(skin.named("paint_hotkeys"), [(True,)])
        self.assertEqual(skin.named("say"), [("Hotkey map ON", ("state", None))])

    def test_a_failing_hotkey_map_still_paints_its_switch(self):
        skin = self.skin()

        def toggle():
            raise RuntimeError("hotkeySet needs a UI")
        with fake_modules(maya_hotkeys=module(
                "maya_hotkeys", toggle=toggle, is_active=lambda: False)):
            with self.assertRaises(RuntimeError):
                hub._press_hotkeys()
        self.assertEqual(skin.named("paint_hotkeys"), [(False,)])

    def test_the_hotkey_editor_is_maya_s(self):
        asked = []
        with fake_modules(maya_hotkeys=module(
                "maya_hotkeys", _maya_mel=lambda cmd: asked.append(cmd) or 1)):
            self.assertEqual(hub._press_hotkey_editor(), 1)
        self.assertEqual(asked, ["HotkeyPreferencesWindow"])


# --------------------------------------------------- the window sections

class WindowSections(HubCase):

    def window_module(self, shown=None):
        calls = []
        attrs = {"toggle": lambda point: calls.append(point) or "toggled"}
        if shown is not None:
            attrs["shown"] = lambda: shown
        fake = module("maya_chat", **attrs)
        fake.calls = calls
        return fake

    def test_the_cursor_is_qt_s(self):
        cursor = types.SimpleNamespace(pos=lambda: QtCore.QPoint(12, 34))
        self.qt.qt = lambda: types.SimpleNamespace(
            QtGui=types.SimpleNamespace(QCursor=cursor))
        self.assertEqual(hub._cursor(), (12, 34))

    def test_no_qt_no_cursor(self):
        self.qt.qt = lambda: None
        self.assertIsNone(hub._cursor())

    def test_a_window_section_s_jump_toggles_its_window_at_the_cursor(self):
        fake = self.window_module()
        with fake_modules(maya_chat=fake), \
                mock.patch.object(hub, "_cursor", return_value=(5, 6)):
            self.assertEqual(hub._toggle_window("chat"), "toggled")
        self.assertEqual(fake.calls, [(5, 6)])

    def test_a_window_section_s_jump_toggles_out_of_its_rail_icon(self):
        fake = self.window_module()
        with fake_modules(maya_chat=fake), \
                mock.patch.object(hub, "_jump_point", return_value=(70, 80)):
            hub._toggle_window("chat")
        self.assertEqual(fake.calls, [(70, 80)])

    def test_open_window_leaves_a_shown_window_alone(self):
        fake = self.window_module(shown=True)
        with fake_modules(maya_chat=fake):
            self.assertTrue(hub.open_window("chat", (1, 2)))
        self.assertEqual(fake.calls, [])

    def test_open_window_opens_a_hidden_one_at_the_point(self):
        fake = self.window_module(shown=False)
        with fake_modules(maya_chat=fake):
            self.assertEqual(hub.open_window("chat", (1, 2)), "toggled")
        self.assertEqual(fake.calls, [(1, 2)])

    def test_open_window_with_no_point_uses_the_cursor(self):
        fake = self.window_module()
        with fake_modules(maya_chat=fake), \
                mock.patch.object(hub, "_cursor", return_value=(9, 9)):
            hub.open_window("chat")
        self.assertEqual(fake.calls, [(9, 9)])

    def test_the_pose_library_is_a_window_too(self):
        fake = self.window_module(shown=False)
        with fake_modules(**{"maya_poselib.window": fake}):
            self.assertEqual(hub.open_window("poses", (3, 4)), "toggled")
        self.assertEqual(fake.calls, [(3, 4)])

    def test_the_rail_s_popup_of_a_window_section_opens_its_window(self):
        with mock.patch.object(hub, "open_window",
                               return_value="opened") as opened:
            self.assertEqual(hub._press_popup("chat"), "opened")
        opened.assert_called_once_with("chat")


# ------------------------------------------------------------- the rail

class RailHelpers(HubCase):

    def test_a_card_s_height_reads_back_as_it_was_left(self):
        var = edgerules.HEIGHT_VAR + "tools"
        self.assertIsNone(hub.card_height("tools"))
        self.cmds.optionvars[var] = 420
        self.assertEqual(hub.card_height("tools"), 420)
        self.cmds.optionvars[var] = 0
        self.assertIsNone(hub.card_height("tools"))
        self.cmds.optionvars[var] = "tall"
        self.assertIsNone(hub.card_height("tools"))

    def test_the_bottom_grip_sets_and_remembers_the_shown_card_s_height(self):
        skin = self.skin()
        skin.shown = "tools"
        heights = []
        self.qt.set_card_height = lambda s, logical, scale: heights.append(
            (s, logical, scale))
        hub._rail_height(380.6)
        self.assertEqual(heights, [(skin, 380.6, hub._scale())])
        self.assertEqual(self.cmds.optionvars[edgerules.HEIGHT_VAR + "tools"],
                         380)
        hub._rail_height(500, save=False)
        self.assertEqual(self.cmds.optionvars[edgerules.HEIGHT_VAR + "tools"],
                         380)
        hub._rail_height(None)
        self.assertNotIn(edgerules.HEIGHT_VAR + "tools", self.cmds.optionvars)
        hub._rail_height(None)                       # nothing to forget

    def test_the_grip_without_a_skin_does_nothing(self):
        hub._rail_height(300)
        self.assertEqual(self.cmds.optionvars, {})

    def test_a_skin_module_without_the_height_call_is_passed_over(self):
        skin = self.skin()
        skin.shown = "tools"
        hub._rail_height(300)
        self.assertEqual(self.cmds.optionvars[edgerules.HEIGHT_VAR + "tools"],
                         300)

    def test_the_card_rect_and_the_least_width_need_an_edge_and_a_skin(self):
        self.assertIsNone(hub._rail_card())
        self.assertEqual(hub._rail_least(), 0)
        self.edge_state["edge"] = FakeEdge()
        self.assertIsNone(hub._rail_card())                    # no skin
        self.assertEqual(hub._rail_least(), 0)
        self.skin()
        self.assertIsNone(hub._rail_card())                    # no such call
        self.assertEqual(hub._rail_least(), 0)

    def test_the_card_rect_and_the_least_width_come_from_the_skin(self):
        edge = FakeEdge()
        self.edge_state["edge"] = edge
        skin = self.skin()
        self.qt.card_rect = lambda s, host: (s, host, "rect")
        self.qt.rail_least = lambda s, host, scale: 333
        self.assertEqual(hub._rail_card(), (skin, "edgeHost", "rect"))
        self.assertEqual(hub._rail_least(), 333)

    def test_every_running_burst_is_stopped(self):
        self.assertIsNone(hub._rail_burst_stop())             # no skin
        skin = self.skin()
        stopped = []

        class Burster(object):
            def __init__(self, name, fails=False):
                self.name, self.fails = name, fails

            def stop(self):
                if self.fails:
                    raise RuntimeError("deleted")
                stopped.append(self.name)
        skin.cards = {"a": types.SimpleNamespace(burster=Burster("a")),
                      "b": types.SimpleNamespace(burster=None),
                      "c": types.SimpleNamespace(burster=Burster("c", True)),
                      "d": types.SimpleNamespace()}
        hub._rail_burst_stop()
        self.assertEqual(stopped, ["a"])


class RailBurst(HubCase):
    """The edge rail's card bursting out of a point (2026-10-18) - the hub's
    half: the Burster made once on the card, its two callbacks, the shape in
    the edge host's coordinates."""

    def setUp(self):
        super(RailBurst, self).setUp()
        self.host = QtWidgets.QWidget()
        self.host.resize(400, 600)
        self.frame = QtWidgets.QWidget(self.host)
        self.frame.setGeometry(30, 50, 300, 200)
        self.made.append(self.host)
        self.edge = FakeEdge(shown=True)
        self.edge.host = self.host
        self.edge_state["edge"] = self.edge
        self.skin_ = self.skin()
        self.card = types.SimpleNamespace(frame=self.frame)
        self.skin_.cards = {"tools": self.card}
        self.skin_.shown = "tools"
        self.qt.card_parts = lambda s, card: ("parts", card)
        self.made_bursters = []
        test = self

        class Burster(object):
            def __init__(self, frame, parts, face, scale):
                self.frame, self.parts, self.face = frame, parts, face
                self.scale = scale
                self.effect = None
                self.runs = []
                self.stopped = 0
                test.made_bursters.append(self)

            def run(self, showing, origin, done, on_tick=None):
                self.runs.append((showing, origin, done))
                if on_tick is not None:
                    on_tick((0, 0, 10, 20))
                return True

            def stop(self):
                self.stopped += 1
        self.blended = []
        self.modules = dict(
            maya_hubwindow=module("maya_hubwindow", Burster=Burster),
            maya_hubburst=module(
                "maya_hubburst",
                blend=lambda a, b, level: self.blended.append((a, b, level))
                or "face"))

    def burst(self, showing=True, origin=(100, 200), done=None, shapes=None):
        shapes = [] if shapes is None else shapes
        with fake_modules(**self.modules):
            return hub._rail_burst(showing, origin, done, shapes.append)

    def test_the_card_bursts_and_its_shape_lands_in_the_host(self):
        shapes = []
        done = object()
        self.assertTrue(self.burst(done=done, shapes=shapes))
        burster = self.made_bursters[0]
        self.assertIs(self.card.burster, burster)
        self.assertIs(burster.frame, self.frame)
        self.assertEqual(burster.scale, 1.5)
        self.assertEqual(burster.runs, [(True, (100, 200), done)])
        self.assertEqual(shapes, [(30, 50, 40, 70)])

    def test_its_callbacks_read_the_card_s_parts_and_its_face(self):
        import maya_hubstyle
        self.burst()
        burster = self.made_bursters[0]
        self.assertEqual(burster.parts(), ("parts", self.card))
        self.frame.level = 0.25
        self.assertEqual(burster.face(), "face")
        self.assertEqual(self.blended, [(maya_hubstyle.TOKENS["card"],
                                         maya_hubstyle.TOKENS["card_active"],
                                         0.25)])

    def test_the_burster_is_made_once_a_card(self):
        self.burst()
        self.burst(showing=False)
        self.assertEqual(len(self.made_bursters), 1)
        self.assertEqual([r[0] for r in self.made_bursters[0].runs],
                         [True, False])

    def test_an_effect_replaced_on_the_frame_is_dropped(self):
        self.burst()
        burster = self.made_bursters[0]
        burster.effect = object()             # not the frame's effect any more
        self.burst()
        self.assertIsNone(burster.effect)

    def test_another_card_s_burst_still_running_is_stopped(self):
        other = types.SimpleNamespace(frame=None)
        self.skin_.cards["studio"] = other
        self.burst()
        first = self.made_bursters[0]
        self.skin_.shown = "studio"
        other.frame = QtWidgets.QWidget(self.host)
        self.burst()
        self.assertEqual(first.stopped, 1)

    def test_a_frame_deleted_mid_burst_hears_no_shape(self):
        import shiboken6
        shapes = []

        class Late(object):
            def run(self_, showing, origin, done, on_tick=None):
                shiboken6.delete(self.frame)
                on_tick((0, 0, 1, 1))
                return True
        self.card.burster = Late()
        self.card.burster.effect = None
        self.assertTrue(self.burst(shapes=shapes))
        self.assertEqual(shapes, [])

    def test_no_burst_without_what_it_needs(self):
        self.assertFalse(self.burst(origin=None))
        self.skin_.shown = "studio"                 # no such card
        self.assertFalse(self.burst())
        self.skin_.shown = "tools"
        self.edge_state["edge"] = None
        self.assertFalse(self.burst())
        hub._SKIN = None
        self.assertFalse(self.burst())
        self.assertEqual(self.made_bursters, [])


class RailFocus(HubCase):
    """focus(key) on the edge rail (2026-10-17/18): a click brings that card
    out of its icon; the card already out goes back into it."""

    def setUp(self):
        super(RailFocus, self).setUp()
        self.edge = FakeEdge()
        self.edge_state["edge"] = self.edge
        skin = self.skin()
        skin.host = self.edge.slot
        skin.windowed = True
        skin.cards = {"tools": "toolsCard", "studio": "studioCard"}
        self.heights = []
        self.qt.set_card_height = lambda s, logical, scale: self.heights.append(
            logical)
        self.button = QtWidgets.QPushButton()
        self.button.setGeometry(40, 60, 30, 20)
        self.button.show()
        self.made.append(self.button)
        skin.jumps = {"tools": self.button}

    def centre(self):
        at = self.button.mapToGlobal(QtCore.QPoint(15, 10))
        return (at.x(), at.y())

    def test_the_jump_point_is_the_icon_s_centre(self):
        self.assertEqual(hub._jump_point("tools"), self.centre())
        self.assertIsNone(hub._jump_point("studio"))       # no icon
        self.assertIsNone(hub._jump_point(None))
        self.button.hide()
        self.assertIsNone(hub._jump_point("tools"))

    def test_a_click_brings_the_card_out_of_its_icon(self):
        self.cmds.optionvars[edgerules.HEIGHT_VAR + "tools"] = 410
        self.assertEqual(hub.focus("tools"), "toolsCard")
        self.assertEqual(self.edge.reveals, [self.centre()])
        skin = hub._SKIN
        self.assertIn(("show_card", "tools", False), skin.calls)
        self.assertEqual(skin.named("set_active"), [("tools",)])
        self.assertEqual(self.heights, [410])
        self.assertEqual(self.cmds.optionvars[hub.CURRENT_VAR], "tools")

    def test_a_click_on_the_card_out_sends_it_back(self):
        hub.focus("tools")
        self.assertIsNone(hub.focus("tools"))
        self.assertEqual(self.edge.conceals, [self.centre()])

    def test_a_card_without_an_icon_comes_out_at_the_cursor(self):
        with mock.patch.object(hub, "_cursor", return_value=(1, 2)):
            hub.focus("studio")
        self.assertEqual(self.edge.reveals, [(1, 2)])

    def test_a_key_with_no_card_is_nothing(self):
        self.assertIsNone(hub.focus("nonsense"))
        self.assertEqual(self.edge.reveals, [])

    def test_the_card_s_close_and_popout_fold_into_the_cursor(self):
        hub.focus("tools")
        with mock.patch.object(hub, "_cursor", return_value=(7, 8)):
            hub._press_rail_close("tools")
        self.assertEqual(self.edge.conceals, [(7, 8)])
        hub.focus("tools")
        presented = []
        with mock.patch.object(hub, "_cursor", return_value=(9, 10)), \
                fake_modules(maya_hubpop=module(
                    "maya_hubpop",
                    present=lambda key, origin: presented.append(
                        (key, origin)) or True)):
            self.assertTrue(hub._press_popout("tools"))
        self.assertEqual(presented, [("tools", (9, 10))])
        self.assertEqual(self.edge.conceals[-1], (9, 10))

    def test_a_popout_of_another_card_leaves_the_rail_out(self):
        hub.focus("tools")
        with mock.patch.object(hub, "_cursor", return_value=(9, 10)), \
                fake_modules(maya_hubpop=module(
                    "maya_hubpop", present=lambda key, origin: True)):
            hub._press_popout("studio")
        self.assertEqual(self.edge.conceals, [])

    def test_a_popout_that_fails_is_said(self):
        def boom(key, origin):
            raise RuntimeError("no window")
        with mock.patch.object(hub, "_cursor", return_value=None), \
                fake_modules(maya_hubpop=module("maya_hubpop", present=boom)):
            result, out = self.printed(hub._press_popout, "tools")
        self.assertFalse(result)
        self.assertIn("no window", out)
        self.assertEqual(hub._SKIN.named("say")[-1][0],
                         "The window could not be opened - the Script Editor "
                         "has the details")


class FocusInTheDock(HubCase):

    def test_an_alias_focuses_the_card_it_lives_in(self):
        skin = self.skin()

        class Card(object):
            def __init__(self):
                self.collapsed = []

            def set_collapsed(self, value, animate=False):
                self.collapsed.append((value, animate))
        skin.cards = {"characters": Card(), "weapons": Card()}
        hub.focus("armor")
        self.assertEqual(skin.cards["characters"].collapsed, [(True, True)])
        self.assertEqual(skin.cards["weapons"].collapsed, [(False, True)])
        self.assertEqual(self.cmds.optionvars[hub.OPTIONVAR.format(
            "characters")], 1)
        self.assertEqual(self.cmds.optionvars[hub.OPTIONVAR.format(
            "weapons")], 0)
        self.assertEqual(skin.named("set_active"), [("weapons",)])


if __name__ == "__main__":
    unittest.main()
