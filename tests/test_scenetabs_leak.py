"""Scene tabs: what a tab's save may not reach, and the session root's copies (2026-10-16)."""
import unittest

from maya_scenetabs import layers, records, saving


class Foreign(unittest.TestCase):
    TABS = ["tab_a", "tab_b", "tab_c"]

    def test_another_tabs_node_is_foreign_at_any_depth(self):
        self.assertTrue(saving._foreign(":tab_a:cube", "tab_b", self.TABS))
        self.assertTrue(saving._foreign("tab_c:Manny_Rig:FKHead_M", "tab_b", self.TABS))

    def test_the_tabs_own_nodes_are_not(self):
        self.assertFalse(saving._foreign(":tab_b:cube", "tab_b", self.TABS))
        self.assertFalse(saving._foreign("tab_b:tab_a:mat", "tab_b", self.TABS))

    def test_the_session_root_and_node_are_foreign_by_their_names(self):
        self.assertTrue(saving._foreign(":" + records.LAYER_ROOT, "tab_b", self.TABS))
        self.assertTrue(saving._foreign(records.SESSION_NODE, "tab_b", self.TABS))
        self.assertTrue(saving._foreign("skeldarTabsLayerRoot1", "tab_b", self.TABS,
                                        ("skeldarTabsLayerRoot1", records.SESSION_NODE)))

    def test_a_root_node_or_a_namespace_that_is_no_tab_is_not(self):
        self.assertFalse(saving._foreign(":time1", "tab_b", self.TABS))
        self.assertFalse(saving._foreign(":midNode", "tab_b", self.TABS))
        self.assertFalse(saving._foreign(":Bow:Arrow", "tab_b", self.TABS))
        self.assertFalse(saving._foreign(":tab_gone:cube", "tab_b", self.TABS))


class RootCopy(unittest.TestCase):

    def test_a_copy_of_the_session_root_inside_a_tab(self):
        for name in ("tab_x:skeldarTabsLayerRoot", "tab_x:skeldarTabsLayerRootCopy",
                     "tab_x:tab_y:skeldarTabsLayerRoot1"):
            self.assertTrue(layers.is_root_copy(name), name)

    def test_the_session_root_itself_and_other_layers_are_not(self):
        for name in (records.LAYER_ROOT, "tab_x:AnimLayerRoot", "tab_x:BaseAnimation", "tab_x:Layer1"):
            self.assertFalse(layers.is_root_copy(name), name)


if __name__ == "__main__":
    unittest.main()
