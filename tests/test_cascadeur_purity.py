"""Only cascade_io may import csc or pycsc. Every other module must stay
importable where Cascadeur is absent."""

import ast
import os
import unittest

PKG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "SkeldarAnim", "skeldar_cascadeur")
ALLOWED = {"cascade_io.py"}
BANNED = ("csc", "pycsc")


def _imports(path):
    with open(path, "r", encoding="utf-8") as handle:
        tree = ast.parse(handle.read(), path)
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


class OnlyCascadeIoTouchesCsc(unittest.TestCase):

    def test_no_other_module_imports_csc(self):
        for name in sorted(os.listdir(PKG)):
            if not name.endswith(".py") or name in ALLOWED:
                continue
            for module in _imports(os.path.join(PKG, name)):
                root = module.split(".")[0]
                self.assertNotIn(root, BANNED, "%s imports %s" % (name, module))

    def test_cascade_io_is_the_one_that_does(self):
        names = _imports(os.path.join(PKG, "cascade_io.py"))
        self.assertTrue(any(n.split(".")[0] == "csc" for n in names))


if __name__ == "__main__":
    unittest.main()
