"""Use Skeldar / Use Maya interface (2026-10-19): the pure halves of
maya_interface, and the installer's live rebuild of the Time Bar and side panel."""

import subprocess
import sys
import types
import unittest
from unittest import mock

import maya_interface as mi


class StateOf(unittest.TestCase):
    def test_ours_everywhere_is_skeldar(self):
        self.assertEqual(mi.state_of("edge", "edge", True), mi.SKELDAR)
        self.assertEqual(mi.state_of("docked", "edge", True), mi.SKELDAR)

    def test_maya_everywhere_is_maya(self):
        self.assertEqual(mi.state_of("maya", "maya", True), mi.MAYA)
        self.assertEqual(mi.state_of("maya", "maya", False), mi.MAYA)

    def test_anything_else_is_mixed(self):
        self.assertEqual(mi.state_of("edge", "maya", True), mi.MIXED)
        self.assertEqual(mi.state_of("maya", "edge", True), mi.MIXED)
        self.assertEqual(mi.state_of("edge", "edge", False), mi.MIXED)


class TimebarFor(unittest.TestCase):
    def test_maya_asks_maya(self):
        self.assertEqual(mi.timebar_for(mi.MAYA, "edge", "edge"), "maya")

    def test_skeldar_keeps_a_standing_ours(self):
        self.assertEqual(mi.timebar_for(mi.SKELDAR, "docked", "edge"), "docked")

    def test_skeldar_from_maya_takes_the_last_ours_else_the_edge(self):
        self.assertEqual(mi.timebar_for(mi.SKELDAR, "maya", "docked"), "docked")
        self.assertEqual(mi.timebar_for(mi.SKELDAR, "maya", None), "edge")
        self.assertEqual(mi.timebar_for(mi.SKELDAR, "maya", "junk"), "edge")


class ReloadLive(unittest.TestCase):
    def test_both_are_rebuilt_side_panel_first_and_a_failure_does_not_stop_the_other(self):
        calls = []

        def module(name, result):
            m = types.ModuleType(name)

            def reload_live():
                calls.append(name)
                if isinstance(result, Exception):
                    raise result
                return result
            m.reload_live = reload_live
            return m

        fakes = {"maya_sidepanel": module("maya_sidepanel", RuntimeError("x")),
                 "maya_timebar": module("maya_timebar", True),
                 "maya_viewportbar": module("maya_viewportbar", 4),
                 "maya_mainbar": module("maya_mainbar", False)}
        with mock.patch.dict(sys.modules, fakes), mock.patch("builtins.print"):
            done = mi.reload_live()
        self.assertEqual(calls, ["maya_sidepanel", "maya_timebar", "maya_viewportbar",
                                 "maya_mainbar"])
        self.assertEqual(done, ["maya_timebar", "maya_viewportbar"])


class Purity(unittest.TestCase):
    def test_it_imports_nothing_of_maya(self):
        code = ("import sys, maya_interface; "
                "print(any(n == 'maya' or n.startswith('maya.') for n in sys.modules))")
        import os
        here = os.path.dirname(os.path.abspath(mi.__file__))
        out = subprocess.run([sys.executable, "-c", code], cwd=here,
                             capture_output=True, text=True)
        self.assertEqual(out.stdout.strip(), "False", out.stderr)


class InstallRebuild(unittest.TestCase):
    def test_rebuild_interface_asks_the_fresh_module(self):
        import install
        fake = types.SimpleNamespace(reload_live=lambda: ["maya_timebar"])
        self.assertEqual(install.rebuild_interface("C:/x", importer=lambda name: fake),
                         ["maya_timebar"])

    def test_a_failure_is_said_not_raised(self):
        import install

        def boom(_name):
            raise ImportError("gone")
        with mock.patch("builtins.print") as said:
            self.assertEqual(install.rebuild_interface("C:/x", importer=boom), [])
        self.assertIn("not rebuilt", said.call_args[0][0])

    def test_only_a_standing_bar_or_panel_asks_for_a_rebuild(self):
        import install
        with mock.patch.object(sys, "_skeldar_timebar", {"bar": None, "edge": None}, create=True), \
                mock.patch.object(sys, "_skeldar_sidepanel", {"edge": None}, create=True):
            self.assertFalse(install._interface_standing())
        with mock.patch.object(sys, "_skeldar_timebar", {"bar": object()}, create=True):
            self.assertTrue(install._interface_standing())
        with mock.patch.object(sys, "_skeldar_timebar", {}, create=True), \
                mock.patch.object(sys, "_skeldar_sidepanel", {"edge": object()}, create=True):
            self.assertTrue(install._interface_standing())

    def test_the_module_ships(self):
        import install
        self.assertIn("maya_interface.py", install.payload())


if __name__ == "__main__":
    unittest.main()
