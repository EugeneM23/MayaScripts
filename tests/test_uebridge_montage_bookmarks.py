"""The scan windows as time-slider bookmarks, on a fake `cmds`.

What the real nodes are, measured in mayapy 2026-10-29: the
`timeSliderBookmark` plugin's node with `timeRangeStart` / `timeRangeStop` /
`color` (a double3) / `name` (a string) / `priority`, which both our Time Bar
and Maya's own slider draw; `addAttr` + `attributeQuery` mark ours, and Maya
uniquifies a repeated node name (`scanWindow`, `scanWindow1`).
"""

import unittest

from maya_uebridge import montage


class FakeCmds(object):
    """Only what `write_bookmarks` asks of Maya."""

    def __init__(self, existing=()):
        self.nodes = {}
        self.attrs = {}
        self.deleted = []
        self.plugin_loaded = False
        for name, mark in existing:
            self.nodes[name] = "timeSliderBookmark"
            if mark is not None:
                self.attrs[name + "." + montage.MARK_ATTR] = mark

    # --- the plugin
    def pluginInfo(self, name, **kw):
        if kw.get("q") or kw.get("query"):
            return self.plugin_loaded
        return None

    def loadPlugin(self, name, **kw):
        self.plugin_loaded = True

    # --- nodes
    def createNode(self, kind, **kw):
        name = kw.get("name") or kind
        taken, number = name, 1
        while taken in self.nodes:
            taken, number = "{0}{1}".format(name, number), number + 1
        self.nodes[taken] = kind
        return taken

    def ls(self, *args, **kw):
        if kw.get("type") == "timeSliderBookmark":
            return [n for n, k in self.nodes.items()
                    if k == "timeSliderBookmark"]
        return []

    def objExists(self, name):
        return name.split(".")[0] in self.nodes

    def addAttr(self, node, **kw):
        self.attrs[node + "." + kw["longName"]] = ""

    def setAttr(self, plug, *values, **kw):
        self.attrs[plug] = values[0] if len(values) == 1 else tuple(values)

    def getAttr(self, plug, **kw):
        return self.attrs.get(plug)

    def attributeQuery(self, attr, **kw):
        return (kw.get("node", "") + "." + attr) in self.attrs

    def delete(self, *nodes):
        names = nodes[0] if nodes and isinstance(nodes[0], list) else list(nodes)
        for name in names:
            self.nodes.pop(name, None)
            self.deleted.append(name)


PLAN = montage.Plan(
    montage="AM_Longsword_Attack_Left_Forward_Hold", slot="DefaultSlot",
    spans=[], end=2.4333334, clips=[],
    windows=[montage.Window("MeleeScanWindow", 0.6, 0.9966667),
             montage.Window("GameplayEvent Window", 1.1136667, 1.3003334)])


class Fake(unittest.TestCase):
    """Every test here runs `write_bookmarks` against a fake Maya."""

    existing = ()

    def setUp(self):
        self.cmds = FakeCmds(existing=self.existing)
        self.old = montage._maya
        montage._maya = lambda: self.cmds

    def tearDown(self):
        montage._maya = self.old


class WriteBookmarks(Fake):
    def test_one_node_a_window(self):
        done = montage.write_bookmarks(PLAN, 30.0)
        self.assertEqual(len(done["made"]), 2)
        self.assertEqual("", done["error"])

    def test_the_frames_are_the_snapped_ones(self):
        made = montage.write_bookmarks(PLAN, 30.0)["made"]
        self.assertEqual(self.cmds.getAttr(made[0] + ".timeRangeStart"), 18.0)
        self.assertEqual(self.cmds.getAttr(made[0] + ".timeRangeStop"), 30.0)

    def test_the_label_is_the_notify_s_own_name(self):
        made = montage.write_bookmarks(PLAN, 30.0)["made"]
        self.assertEqual(self.cmds.getAttr(made[1] + ".name"),
                         "GameplayEvent Window")

    def test_every_one_is_marked_as_ours_with_the_montage_and_the_slot(self):
        made = montage.write_bookmarks(PLAN, 30.0)["made"]
        self.assertEqual(
            self.cmds.getAttr(made[0] + "." + montage.MARK_ATTR),
            u"AM_Longsword_Attack_Left_Forward_Hold · DefaultSlot")

    def test_the_colour_is_ours(self):
        made = montage.write_bookmarks(PLAN, 30.0)["made"]
        self.assertEqual(self.cmds.getAttr(made[0] + ".color"),
                         montage.SCAN_COLOUR)

    def test_the_plugin_is_loaded(self):
        montage.write_bookmarks(PLAN, 30.0)
        self.assertTrue(self.cmds.plugin_loaded)

    def test_a_slot_with_no_window_makes_nothing(self):
        done = montage.write_bookmarks(PLAN._replace(windows=()), 30.0)
        self.assertEqual(done["made"], [])
        self.assertEqual(self.cmds.ls(type="timeSliderBookmark"), [])


class Replacing(Fake):
    existing = (("oldScan", u"AM_X · 1P"),    # ours, a previous import
                ("animatorsOwn", None))            # the animator's own

    def test_ours_are_found_by_the_attribute(self):
        self.assertEqual(montage.our_bookmarks(self.cmds), ["oldScan"])

    def test_a_re_import_deletes_ours(self):
        montage.write_bookmarks(PLAN, 30.0)
        self.assertIn("oldScan", self.cmds.deleted)

    def test_a_re_import_leaves_the_animator_s_own(self):
        montage.write_bookmarks(PLAN, 30.0)
        self.assertNotIn("animatorsOwn", self.cmds.deleted)
        self.assertIn("animatorsOwn", self.cmds.nodes)

    def test_what_is_left_is_only_the_new_ones_and_theirs(self):
        made = montage.write_bookmarks(PLAN, 30.0)["made"]
        self.assertEqual(sorted(self.cmds.ls(type="timeSliderBookmark")),
                         sorted(made + ["animatorsOwn"]))


class NeverFailsTheImport(unittest.TestCase):
    def test_a_refusal_is_named_and_raises_nothing(self):
        class Angry(FakeCmds):
            def createNode(self, kind, **kw):
                raise RuntimeError("no bookmark for you")

        old = montage._maya
        montage._maya = lambda: Angry()
        try:
            done = montage.write_bookmarks(PLAN, 30.0)
        finally:
            montage._maya = old
        self.assertEqual(done["made"], [])
        self.assertIn("no bookmark for you", done["error"])

    def test_a_maya_without_the_plugin_is_named_too(self):
        class NoPlugin(FakeCmds):
            def loadPlugin(self, name, **kw):
                raise RuntimeError("timeSliderBookmark is not here")

        old = montage._maya
        montage._maya = lambda: NoPlugin()
        try:
            done = montage.write_bookmarks(PLAN, 30.0)
        finally:
            montage._maya = old
        self.assertEqual(done["made"], [])
        self.assertIn("not here", done["error"])


if __name__ == "__main__":
    unittest.main()
