"""BaseAnimation selected whenever no animation layer is (2026-10-27, «перевір чому не працює авто
кі»: with nothing selected Maya keyed the muted _3P_Upper_Body). The live half was checked in the
animator's Maya on port 7003.

2026-10-30, the same words again: the tab's own root (`<tab>:AnimLayerRoot`, hidden from the Layer
Editor, no channel of its own) was the selected layer, so nothing looked selected, Maya keyed its best
layer - the muted _3P_Upper_Body - and the earlier fix saw a selection and did nothing."""
import unittest
from unittest import mock

from maya_scenetabs import keylayer

ROOT = "skeldarTabsLayerRoot"
HOLDER = "tab_a:AnimLayerRoot"
UPPER = "tab_a:_3P_Upper_Body"


class NeedsBase(unittest.TestCase):

    def test_no_layer_selected_selects_the_root(self):
        self.assertTrue(keylayer.needs_base(ROOT, []))

    def test_a_selected_layer_is_left_as_it_is(self):
        self.assertFalse(keylayer.needs_base("BaseAnimation", ["Upper"]))

    def test_the_root_selected_is_left_as_it_is(self):
        self.assertFalse(keylayer.needs_base(ROOT, [ROOT], [HOLDER]))

    def test_a_scene_without_layers_is_left_alone(self):
        self.assertFalse(keylayer.needs_base("", []))
        self.assertFalse(keylayer.needs_base(None, []))

    def test_only_a_tab_s_own_root_selected_selects_the_root(self):
        self.assertTrue(keylayer.needs_base(ROOT, [HOLDER], [HOLDER]))

    def test_a_layer_selected_beside_a_tab_s_own_root_is_left_as_it_is(self):
        self.assertFalse(keylayer.needs_base(ROOT, [HOLDER, UPPER], [HOLDER]))


class Holders(unittest.TestCase):

    def test_a_tab_s_own_root_on_the_root_is_a_holder(self):
        parents = {HOLDER: ROOT, "tab_b:AnimLayerRoot1": ROOT, UPPER: HOLDER, "tab_c:AnimLayerRoot": ""}
        self.assertEqual(keylayer.holders(ROOT, list(parents) + [ROOT], parents.get),
                         [HOLDER, "tab_b:AnimLayerRoot1"])


class Ensure(unittest.TestCase):

    def _run(self, selected):
        parents = {HOLDER: ROOT, UPPER: HOLDER, ROOT: ""}
        edits = []

        def anim_layer(*a, **k):
            if k.get("root"):
                return ROOT
            if k.get("query") and k.get("selected"):
                return selected.get(a[0], False)
            if k.get("query") and k.get("parent"):
                return parents[a[0]]
            if k.get("edit"):
                edits.append((a[0], k))
                selected[a[0]] = k.get("selected", selected.get(a[0], False))
            return None
        fake = mock.MagicMock()
        fake.ls.return_value = [ROOT, HOLDER, UPPER]
        fake.animLayer.side_effect = anim_layer
        mel = mock.MagicMock()
        mel.eval.side_effect = lambda text: 1 if text.startswith("exists") else selected.update({ROOT: True})
        with mock.patch.object(keylayer, "cmds", fake), mock.patch.dict("sys.modules", {"maya.mel": mel}), \
                mock.patch("maya.mel", mel, create=True):
            return keylayer.ensure(), mel, edits

    def test_the_root_is_clicked_through_the_editor(self):
        done, mel, _edits = self._run({})
        self.assertTrue(done)
        mel.eval.assert_any_call('animLayerEditorOnSelect("%s", 1)' % ROOT)

    def test_nothing_happens_with_a_layer_selected(self):
        done, mel, edits = self._run({UPPER: True})
        self.assertFalse(done)
        mel.eval.assert_not_called()
        self.assertEqual(edits, [])

    def test_a_selected_tab_root_is_let_go_and_the_root_clicked(self):
        selected = {HOLDER: True}
        done, mel, edits = self._run(selected)
        self.assertTrue(done)
        self.assertEqual(edits, [(HOLDER, {"edit": True, "selected": False, "preferred": False})])
        self.assertFalse(selected[HOLDER])
        mel.eval.assert_any_call('animLayerEditorOnSelect("%s", 1)' % ROOT)


if __name__ == "__main__":
    unittest.main()
