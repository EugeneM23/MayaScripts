import os
import unittest

from maya_scenetabs import layereditor, records

MAYA_FILE = os.path.join(os.environ.get("MAYA_LOCATION", "C:/Program Files/Autodesk/Maya2027"),
                         "scripts", "startup", layereditor.FILE)


class ProcText(unittest.TestCase):

    def test_the_whole_proc_braces_in_strings_and_comments_not_counted(self):
        text = ('global proc int other() { return 1; }\n'
                'global proc string[] wanted(string $a)\n{\n'
                '    // a } in a comment\n    /* and { here */\n'
                '    string $s = "a { brace \\" and } more";\n'
                '    if ($a == "") { return {}; }\n    return {$a};\n}\n'
                'global proc after() {}\n')
        got = layereditor.proc_text(text, "wanted")
        self.assertTrue(got.startswith("global proc string[] wanted("))
        self.assertTrue(got.endswith("return {$a};\n}"))
        self.assertIsNone(layereditor.proc_text(text, "missing"))

    def test_the_bare_block_that_builds_the_ui_is_dropped_and_no_other(self):
        build = layereditor.BUILD
        text = ('global proc a() { if (1) { print "}"; } }\n'
                'if (`exists x`) { source "y.mel"; }\n'
                '// a } comment\n{\n\tglobal string $f;\n\t%s\n\tupdateLayerEditor();\n}\n' % build)
        self.assertEqual(layereditor.without_build(text),
                         'global proc a() { if (1) { print "}"; } }\n'
                         'if (`exists x`) { source "y.mel"; }\n// a } comment\n\n')
        inside_proc = "global proc b()\n{\n\t%s\n}\n" % build
        self.assertIsNone(layereditor.without_build(inside_proc))
        self.assertIsNone(layereditor.without_build("{ %s }\n{ %s }\n" % (build, build)))
        self.assertIsNone(layereditor.without_build("nothing here"))

    def test_a_line_not_there_exactly_once_refuses(self):
        self.assertEqual(layereditor.changed("a b", [("a", "x")]), "x b")
        self.assertIsNone(layereditor.changed("a b", [("c", "x")]))
        self.assertIsNone(layereditor.changed("a a", [("a", "x")]))


@unittest.skipUnless(os.path.isfile(MAYA_FILE), "Maya's layerEditor.mel is not on this machine")
class OnMayasOwnFile(unittest.TestCase):

    def setUp(self):
        with open(MAYA_FILE, encoding="utf-8", errors="replace") as handle:
            self.procs, self.reason = layereditor.patched_procs(handle.read())

    def test_every_change_lands_on_this_maya(self):
        self.assertEqual(self.reason, "")
        self.assertEqual(sorted(self.procs), ["animLayerEditorOnSelect", "rebuildAnimLayerEditor"])

    def test_the_whole_file_is_sourced_changed_in_those_procs_only(self):
        with open(MAYA_FILE, encoding="utf-8", errors="replace") as handle:
            source = handle.read()
        text, reason = layereditor.patched_file(source)
        self.assertEqual(reason, "")
        self.assertNotIn(layereditor.BUILD, text)
        expected = layereditor.without_build(source)
        self.assertGreater(len(source) - len(expected), 0)
        self.assertLess(len(source) - len(expected), 400)       # one small block, nothing else
        for name, _ in layereditor.CHANGES:
            self.assertEqual(layereditor.proc_text(text, name), self.procs[name])
            expected = expected.replace(layereditor.proc_text(source, name), self.procs[name], 1)
        self.assertEqual(text, expected)
        self.assertIn("proc string[] getBestLayers(", text)     # the local procs the changed ones call
        self.assertNotEqual(layereditor.PATCHED, layereditor.FILE)

    def test_the_changes_are_in(self):
        self.assertIn("skeldarTabsHolder($parentLayer)", self.procs["rebuildAnimLayerEditor"])
        self.assertIn("skeldarTabsLayerLabel(", self.procs["rebuildAnimLayerEditor"])
        self.assertIn('$layer != "%s"' % records.LAYER_ROOT, self.procs["animLayerEditorOnSelect"])
        for text in self.procs.values():
            self.assertEqual(text.count("{"), text.count("}"))


class Helpers(unittest.TestCase):

    def test_the_helpers_name_our_roots(self):
        self.assertIn('"%s"' % records.LAYER_ROOT, layereditor.HELPERS)
        self.assertIn("^%s[0-9]*$" % records.TAB_LAYER_ROOT, layereditor.HELPERS)
        self.assertIn("global proc string[] buildAnimLayerArray()", layereditor.HELPERS)


if __name__ == "__main__":
    unittest.main()
