"""Cascadeur discovers menu actions by `run`/`name` (python_actions_rule). The
bridge must be the only module of its package that defines `run`, so it is
the only menu entry, and its name() is the menu text."""

import ast
import os
import sys
import unittest

PKG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "SkeldarAnim", "skeldar_cascadeur")


def _top_level_functions(path):
    with open(path, "r", encoding="utf-8") as handle:
        tree = ast.parse(handle.read(), path)
    return {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}


class Discovery(unittest.TestCase):

    def test_only_bridge_defines_run(self):
        for name in sorted(os.listdir(PKG)):
            if not name.endswith(".py") or name == "bridge.py":
                continue
            defined = _top_level_functions(os.path.join(PKG, name))
            self.assertNotIn("run", defined, name)
            self.assertNotIn("name", defined, name)

    def test_bridge_defines_the_action_contract(self):
        defined = _top_level_functions(os.path.join(PKG, "bridge.py"))
        self.assertTrue({"name", "description", "run"} <= defined)

    def test_menu_text_is_the_bridge_name(self):
        plugin = os.path.dirname(PKG)
        if plugin not in sys.path:
            sys.path.insert(0, plugin)
        from skeldar_cascadeur import bridge
        self.assertEqual(bridge.name(), "SkeldarAnim.Bridge")
        self.assertIn("Unreal", bridge.description())


if __name__ == "__main__":
    unittest.main()
