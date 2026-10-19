"""The scene tabs bar offscreen on fake actions (2026-10-15): tabs, stars,
switching, closing, the single-scene item. The docking is the animator's live
check.

Spec: docs/superpowers/specs/2026-10-15-scene-tabs-design.md
"""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    import maya_hubqt
    QT = maya_hubqt.qt()
except Exception:                                            # noqa: BLE001
    QT = None


def _items(active=1, star=False):
    return [{"ns": "tab_a", "text": "attack", "tip": "C:/a.ma\nntsc, 0-50", "active": active == 0, "closable": True},
            {"ns": "tab_b", "text": "walk" + ("*" if star else ""), "tip": "C:/b.ma\nfilm, 5-40",
             "active": active == 1, "closable": True}]


class FakeActions(object):

    def __init__(self):
        self.log = []
        self.next_items = _items()

    def __getattr__(self, name):
        def record(*args):
            self.log.append((name,) + args)
            return ""
        return record

    def recent(self):
        return []

    def items(self):
        return self.next_items


@unittest.skipIf(QT is None, "no Qt")
class TabBar(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QT.QtWidgets.QApplication.instance() or QT.QtWidgets.QApplication([])

    def setUp(self):
        from maya_scenetabs import bar
        self.actions = FakeActions()
        self.bar = bar.bar_class()(self.actions)
        self.bar.populate(_items())

    def test_one_tab_per_item_with_its_tooltip(self):
        tabs = self.bar.tabs
        self.assertEqual([tabs.tabText(i) for i in range(tabs.count())], ["attack", "walk"])
        self.assertEqual(tabs.tabToolTip(1), "C:/b.ma\nfilm, 5-40")
        self.assertEqual(tabs.currentIndex(), 1)

    def test_populating_switches_nothing(self):
        self.assertEqual(self.actions.log, [])

    def test_picking_a_tab_switches_to_it(self):
        self.bar.tabs.setCurrentIndex(0)
        self.assertIn(("switch", "tab_a"), self.actions.log)

    def test_a_click_while_an_operation_runs_is_ignored(self):
        from maya_scenetabs import session
        with session.busy():
            self.bar.tabs.setCurrentIndex(0)
            self.bar.tabs.tabCloseRequested.emit(0)
        self.assertEqual(self.actions.log, [])
        self.assertFalse(session.is_busy())

    def test_a_press_while_an_operation_runs_does_nothing(self):
        from maya_scenetabs import bar, session
        ran = []
        with session.busy():
            self.assertEqual(bar._run(lambda: ran.append(1) or "done"), "")
        self.assertEqual(ran, [])

    def test_a_failing_tick_does_not_raise(self):
        def broken():
            raise RuntimeError("no session")
        self.actions.items = broken
        self.bar.tick()
        self.bar.tick()

    def test_a_failing_switch_does_not_raise(self):
        def broken(namespace):
            raise RuntimeError("boom")
        self.actions.switch = broken
        self.bar.tabs.setCurrentIndex(0)

    def test_the_close_button_closes_that_tab(self):
        self.bar.tabs.tabCloseRequested.emit(0)
        self.assertIn(("close", "tab_a"), self.actions.log)

    def test_a_single_scene_has_no_close_button(self):
        self.bar.populate([{"ns": "", "text": "attack*", "tip": "C:/a.ma", "active": True, "closable": False}])
        for side in (QT.QtWidgets.QTabBar.LeftSide, QT.QtWidgets.QTabBar.RightSide):
            self.assertIsNone(self.bar.tabs.tabButton(0, side))

    def test_the_tick_updates_the_star_without_repopulating(self):
        self.actions.next_items = _items(star=True)
        self.bar.tick()
        self.assertEqual(self.bar.tabs.tabText(1), "walk*")
        self.assertEqual(self.actions.log, [])

    def test_the_stylesheet_uses_the_hubs_colours(self):
        from maya_scenetabs import bar
        import maya_hubstyle
        sheet = bar.stylesheet(maya_hubstyle.TOKENS, 1.5)
        self.assertIn(maya_hubstyle.TOKENS["accent"], sheet)
        self.assertIn("skeldarSceneTabsTabs", sheet)


class HubShowsTheBar(unittest.TestCase):

    def test_the_hub_build_shows_the_bar_once_per_session(self):
        import inspect
        import maya_hub
        source = inspect.getsource(maya_hub.build)
        self.assertIn("_tabs_bar_soon()", source)
        helper = inspect.getsource(maya_hub._tabs_bar_soon)
        self.assertIn("skeldarSceneTabsBar", helper)
        self.assertIn("ensure_docked", helper)

    def test_the_hooks_go_on_before_the_bar_question(self):
        """Hiding the bar must not turn off Save / Open / New and the session
        restore: the hub installs the hooks first, whatever the optionVar says."""
        import inspect
        import maya_hub
        from maya_scenetabs import bar
        helper = inspect.getsource(maya_hub._tabs_bar_soon)
        self.assertLess(helper.index("hooks.install()"), helper.index("TABS_BAR_VAR) and not"))
        docked = inspect.getsource(bar.ensure_docked)
        self.assertLess(docked.index("hooks.install()"), docked.index("workspaceControl("))


class FakeDockCmds(object):
    """workspaceControl as ensure_docked uses it: exists, the tab flag asked and
    edited, made, deleted."""

    def __init__(self, exists=False, tab=True, locked=False, unasked=False):
        self.exists, self.tab, self.locked, self.unasked = exists, tab, locked, unasked
        self.made = []
        self.deleted = 0

    def about(self, batch=False):
        return False

    def workspaceControl(self, name, exists=False, q=False, edit=False, **flags):
        if exists:
            return self.exists
        if q:
            if self.unasked:
                raise RuntimeError("cannot query")
            return not self.tab
        if edit:
            if "actLikeMayaUIElement" in flags:
                if self.locked:
                    raise RuntimeError("creation only")
                self.tab = not flags["actLikeMayaUIElement"]
            return name
        self.made.append(flags)
        self.exists, self.tab = True, not flags.get("actLikeMayaUIElement")
        return name

    def deleteUI(self, name, control=False):
        self.deleted += 1
        self.exists = False


class Headerless(unittest.TestCase):
    """The bar is a plain strip of tabs: no Maya tab and no "Scene Tabs" title above it."""

    def _dock(self, fake):
        from unittest import mock
        from maya_scenetabs import bar, hooks
        with mock.patch.object(bar, "cmds", fake), mock.patch.object(hooks, "install"):
            bar.ensure_docked()
        return fake

    def test_a_new_control_is_made_without_a_tab(self):
        fake = self._dock(FakeDockCmds())
        self.assertEqual(len(fake.made), 1)
        self.assertIs(fake.made[0]["actLikeMayaUIElement"], True)
        self.assertEqual(fake.made[0]["dockToMainWindow"], ("top", False))

    def test_an_older_control_loses_its_tab_in_place(self):
        fake = self._dock(FakeDockCmds(exists=True, tab=True))
        self.assertFalse(fake.tab)
        self.assertEqual((fake.made, fake.deleted), ([], 0))

    def test_an_older_control_maya_will_not_change_is_made_again(self):
        fake = self._dock(FakeDockCmds(exists=True, tab=True, locked=True))
        self.assertEqual(fake.deleted, 1)
        self.assertIs(fake.made[0]["actLikeMayaUIElement"], True)

    def test_a_flag_maya_will_not_answer_is_trusted_after_the_edit(self):
        fake = self._dock(FakeDockCmds(exists=True, tab=True, unasked=True))
        self.assertEqual((fake.made, fake.deleted), ([], 0))
        self.assertFalse(fake.tab)

    def test_a_headerless_control_is_only_shown(self):
        fake = self._dock(FakeDockCmds(exists=True, tab=False))
        self.assertEqual((fake.made, fake.deleted), ([], 0))


if __name__ == "__main__":
    unittest.main()


class Stale(unittest.TestCase):
    """A bar built by an older module object (an install purged the modules) is built again."""

    def setUp(self):
        try:
            from maya_scenetabs import bar
        except Exception as exc:                                 # noqa: BLE001
            self.skipTest("maya_scenetabs.bar does not import here: %s" % exc)
        self.bar = bar

    def test_a_bar_with_the_current_actions_is_not_stale(self):
        widget = type("W", (), {})()
        widget.actions = self.bar.Actions()
        self.assertFalse(self.bar.stale(widget))

    def test_a_bar_with_an_older_modules_actions_is_stale(self):
        class Actions(object):          # the same name, another class: an older module's
            pass
        widget = type("W", (), {})()
        widget.actions = Actions()
        self.assertTrue(self.bar.stale(widget))

    def test_no_bar_is_not_stale(self):
        self.assertFalse(self.bar.stale(None))
