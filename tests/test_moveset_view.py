"""maya_moveset.view and .panel: the tree view offscreen, the card's presses on fakes."""
import json
import os
import shutil
import sys
import tempfile
import types
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6 import QtCore, QtGui, QtWidgets
except ImportError:                                            # pragma: no cover
    QtWidgets = None

from maya_moveset import model as m

from tests.test_moveset_model import dagger_graph, graph


def folder_with_graph():
    where = tempfile.mkdtemp()
    with open(os.path.join(where, m.GRAPH), "w", encoding="utf-8") as handle:
        json.dump(graph(), handle)
    return where


@unittest.skipIf(QtWidgets is None, "no Qt")
class View(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        from maya_moveset import view
        self.folder = folder_with_graph()
        self.addCleanup(shutil.rmtree, self.folder, True)
        self.calls = []
        actions = dict((k, (lambda *a, k=k: self.calls.append((k,) + a)))
                       for k in ("open", "status", "assign", "picked"))
        self.view = view.TreeView(actions=actions)
        self.view.resize(600, 400)
        self.view.set_data(m.load_graph(self.folder), m.read_state(self.folder), self.folder)

    def ids(self):
        return [c.node.id for c in self.view.cards]

    def test_every_tree_is_drawn_and_a_root_filter_keeps_one(self):
        self.assertEqual(len(self.view.cards), sum(len(t.nodes) for t in self.view.trees()))
        self.view.set_filter(root="AM_Longsword_Attack_Left_Hold")
        self.assertEqual(self.ids(), ["AM_Longsword_Attack_Left_Hold"])

    def test_a_type_filter_dims_what_it_does_not_keep(self):
        self.view.set_filter(root="AM_Longsword_Attack_Stand_Hold", types=["light"])
        dim = dict((c.node.id, c.opacity()) for c in self.view.cards if c.node.depth == 1)
        self.assertLess(dim["AM_Longsword_Attack_Left_Hold"], 0.5)
        self.assertEqual(dim["AM_Longsword_Attack_Right_Light"], 1.0)

    def test_menu_rows_open_status_and_assignee(self):
        state = m.read_state(self.folder)
        state["people"] = ["Anna"]
        self.view.set_state(state)
        stand = self.view.cards[0].node
        rows = self.view.menu_rows(stand, None)
        labels = [r[0] for r in rows if r]
        self.assertIn("Open 3P montage (DefaultSlot)", labels)
        self.assertIn("Open 1P montage (1P)", labels)
        dict((r[0], r[1]) for r in rows if r)["    1P: Done"]()
        dict((r[0], r[1]) for r in rows if r)["    3P → Anna"]()
        self.assertIn(("status", stand.id, "1p", "done"), self.calls)
        self.assertIn(("assign", stand.id, "3p", "Anna"), self.calls)
        left = [c.node for c in self.view.cards if c.node.id == "AM_Longsword_Attack_Left_Hold"][0]
        self.assertIsNone(self.view.menu_rows(left, "3p")[1][1])

    def test_a_dot_names_its_view_and_a_double_click_opens_it(self):
        card = self.view.cards[0]
        self.assertEqual(card.dot_at(card.dot_rect("1p").center()), "1p")
        self.assertIsNone(card.dot_at(QtCore.QPointF(10, 10)))
        self.view.open(card.node.id, "1p")
        self.assertIn(("open", card.node.id, "1p"), self.calls)

    def test_pick_and_paint(self):
        self.view.pick(self.view.cards[0].node)
        self.assertEqual(self.view.picked_id, "AM_Longsword_Attack_Stand_Hold")
        self.assertIn(("picked", "AM_Longsword_Attack_Stand_Hold"), self.calls)
        image = QtGui.QImage(600, 400, QtGui.QImage.Format_ARGB32)
        painter = QtGui.QPainter(image)
        self.view.render(painter)
        painter.end()
        self.view.frame()
        self.assertGreater(self.view.zoom, 0)

    def test_a_status_shows_on_its_dot(self):
        state = m.read_state(self.folder)
        state["status"] = {"AM_Longsword_Attack_Stand_Hold|3p": "done"}
        self.view.set_state(state)
        self.assertIs(self.view.state, state)


class Text(object):
    def __init__(self):
        self.labels = {}

    def text(self, name, exists=False, edit=False, label=None, **_kw):
        if exists:
            return True
        if edit:
            self.labels[name] = label


class Presses(unittest.TestCase):
    def setUp(self):
        from maya_moveset import panel
        self.panel = panel
        self.folder = folder_with_graph()
        self.addCleanup(shutil.rmtree, self.folder, True)
        self.cmds = Text()
        patcher = mock.patch.object(panel, "cmds", self.cmds)
        patcher.start()
        self.addCleanup(patcher.stop)

    def card(self):
        view = types.SimpleNamespace(folder=self.folder, graph=m.load_graph(self.folder),
                                     state=m.read_state(self.folder), set_state=lambda s: None)
        return {"view": view, "status": "st", "sub": "sub", "mtime": 0.0}

    def test_a_status_and_an_assignee_land_in_state_json(self):
        card = self.card()
        self.panel._set(card, "AM_Longsword_Attack_Stand_Hold", "1p", status="progress")
        self.panel._set(card, "AM_Longsword_Attack_Stand_Hold", "1p", person="Anna")
        state = m.read_state(self.folder)
        self.assertEqual(state["status"], {"AM_Longsword_Attack_Stand_Hold|1p": "progress"})
        self.assertEqual(state["assignee"], {"AM_Longsword_Attack_Stand_Hold|1p": "Anna"})
        self.assertIn("Anna", self.cmds.labels["st"])

    def test_open_refuses_a_card_of_ones_own_and_a_missing_slot(self):
        g = m.load_graph(self.folder)
        self.assertIn("no montage", self.panel.open_slot(g, "custom-1", "3p"))
        self.assertIn("has no 1P slot", self.panel.open_slot(g, "AM_Longsword_Attack_Left_Hold", "1p"))

    def test_open_goes_the_bridges_montage_road_with_the_views_slot(self):
        import maya_uebridge
        seen = {}
        bridge = types.SimpleNamespace(
            _export_from_editor=lambda record: seen.setdefault("record", record) and ("ref", 30))
        rigimport = types.SimpleNamespace(
            import_and_retarget=lambda ref, name, **kw: seen.update(kw, name=name) or "in")
        rigs = types.SimpleNamespace(rigs=lambda: [], current_rig=lambda: (None, "no"))
        old = sys.modules.get("maya_rigs")
        sys.modules["maya_rigs"] = rigs
        self.addCleanup(lambda: sys.modules.__setitem__("maya_rigs", old) if old
                        else sys.modules.pop("maya_rigs", None))
        with mock.patch.object(maya_uebridge, "window", bridge, create=True), \
                mock.patch.object(maya_uebridge, "rigimport", rigimport, create=True):
            line = self.panel.open_slot(m.load_graph(self.folder), "AM_Longsword_Attack_Stand_Hold", "1p")
        self.assertEqual(line, "in")
        record = seen["record"]
        self.assertEqual((record.kind, record.clip, record.package),
                         ("montage", "1P", "/Game/M/AM_Longsword_Attack_Stand_Hold"))
        self.assertEqual(seen["name"], "AM_Longsword_Attack_Stand_Hold_1P")
        self.assertEqual(seen["target"], "new_rig")



@unittest.skipIf(QtWidgets is None, "no Qt")
class WeaponRules(unittest.TestCase):
    """A graph that declares its weapon is drawn by its own rules."""

    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        from maya_moveset import view
        self.folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.folder, True)
        with open(os.path.join(self.folder, "graph.dagger.json"), "w", encoding="utf-8") as handle:
            json.dump(dagger_graph(), handle)
        os.makedirs(os.path.join(self.folder, "media", "dagger"))
        open(os.path.join(self.folder, "media", "dagger", "AM_Dg_Atk_NLt.jpg"), "w").close()
        self.dagger = m.weapons(self.folder)[0]
        self.view = view.TreeView()
        self.view.resize(600, 400)
        self.view.set_data(m.load_graph(self.folder, self.dagger.graph),
                           m.read_state(self.folder), self.folder, self.dagger)

    def test_the_labels_are_the_projects_names(self):
        self.assertEqual(self.view.label("AM_Dg_Atk_NLt_NLt_NHd"), "NLt NLt NHd")

    def test_the_colour_is_the_graphs_declared_type(self):
        kinds = dict((c.node.id, c.node.kind) for c in self.view.cards)
        self.assertEqual(kinds["AM_Dg_Atk_NLt_NLt_NHd"], "hold")
        self.assertEqual(kinds["AM_Dg_Atk_NLt"], "light")

    def test_a_type_chip_filters_on_the_declared_type(self):
        #  every transition, so the jump branch is drawn beside the chain
        self.view.set_filter(mode="all", types=["hold"])
        dim = dict((c.node.id, c.opacity()) for c in self.view.cards)
        self.assertEqual(dim["AM_Dg_Atk_NLt_NLt_NHd"], 1.0)      # the hold itself
        self.assertLess(dim["AM_Dg_Atk_JA_Passive"], 0.5)        # a jump, off the hold's path

    def test_the_preview_comes_from_the_weapons_media_subfolder(self):
        self.assertTrue(self.view.thumb_path("AM_Dg_Atk_NLt")
                        .endswith(os.path.join("dagger", "AM_Dg_Atk_NLt.jpg")))
        self.assertEqual(self.view.thumb_path("AM_Dg_Atk_Spr"), "")

    def test_a_graph_with_no_weapon_keeps_the_swords_rules(self):
        from maya_moveset import view
        plain = view.TreeView()
        plain.set_data(graph(), m.read_state(""), "")
        self.assertEqual(plain.label("AM_Longsword_Attack_Stand_Hold"), "Stand Hold")


if __name__ == "__main__":
    unittest.main()


class Build(unittest.TestCase):
    def test_the_card_builds_its_controls(self):
        from tests.uifakes import FakeUiCmds
        from maya_moveset import panel
        import maya_hubqt
        fake = FakeUiCmds()
        with mock.patch.object(panel, "cmds", fake), \
                mock.patch.object(maya_hubqt, "find", lambda *a, **k: None):
            panel.build_panel()
        made = [(c[0], c[1][0] if c[1] else None) for c in fake.calls]
        names = set(n for _k, n in made)
        for name in (panel.SUB, panel.ROOT_MENU, panel.MODE_MENU, panel.WHO_MENU, panel.PLACE,
                     panel.OPEN.format("3p"), panel.OPEN.format("1p"), panel.STATUS):
            self.assertIn(name, names)
        for key, _label in m.TYPES:
            self.assertIn(panel.CHIP.format(key), names)
