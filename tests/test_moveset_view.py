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

    def test_the_menu_opens_each_views_montage_and_nothing_else(self):
        """The planning left the menu (2026-10-29): Open 3P and Open 1P, and a
        view with no slot is a dimmed row."""
        stand = self.view.cards[0].node
        rows = self.view.menu_rows(stand)
        labels = [r[0] for r in rows if r]
        self.assertEqual(labels[:2], ["Open 3P montage (DefaultSlot)", "Open 1P montage (1P)"])
        self.assertFalse([one for one in labels if "Done" in one or "→" in one])
        dict((r[0], r[1]) for r in rows if r)["Open 1P montage (1P)"]()
        self.assertIn(("open", stand.id, "1p"), self.calls)
        left = [c.node for c in self.view.cards if c.node.id == "AM_Longsword_Attack_Left_Hold"][0]
        self.assertIsNone(self.view.menu_rows(left)[1][1])

    def test_a_double_click_opens_the_3p_slot(self):
        card = self.view.cards[0]
        event = types.SimpleNamespace(button=lambda: QtCore.Qt.LeftButton,
                                      accept=lambda: None, pos=lambda: QtCore.QPointF(20, 50))
        card.mouseDoubleClickEvent(event)
        self.assertIn(("open", card.node.id, "3p"), self.calls)

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

    def test_the_planning_is_gone_from_the_card(self):
        for name in ("_set", "WHO_MENU", "_fill_people"):
            self.assertFalse(hasattr(self.panel, name), name)

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
        for name in (panel.SUB, panel.ROOT_MENU, panel.MODE_MENU, panel.PLACE,
                     panel.OPEN.format("3p"), panel.OPEN.format("1p"), panel.STATUS):
            self.assertIn(name, names)
        for key, _label in m.TYPES:
            self.assertIn(panel.CHIP.format(key), names)


class Quiet(object):
    """A `cmds` that answers nothing: a control exists, a query is False, an
    edit is recorded. `_load` and `_poll` run on it."""

    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        def call(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            if kwargs.get("query") or kwargs.get("q"):
                return [] if kwargs.get("itemListLong") else False
            if kwargs.get("exists"):
                return True
            return None
        return call

    def edits(self, command, flag):
        return [(c[1][0] if c[1] else None, c[2][flag]) for c in self.calls
                if c[0] == command and flag in c[2] and (c[2].get("edit") or c[2].get("e"))]


class FakeView(object):
    def __init__(self, folder):
        self.folder = folder
        self.graph, self.state, self.weapon = {}, m.read_state(""), None
        self.mode, self.root, self.types = "combos", "", set()
        self.framed = 0

    def set_data(self, graph, state, folder, weapon=None):
        self.graph, self.state, self.folder, self.weapon = graph, state, folder, weapon

    def set_state(self, state):
        self.state = state

    def set_filter(self, root=None, types=None, mode=None):
        if types is not None:
            self.types = set(types)

    def frame(self):
        self.framed += 1


class WeaponCard(unittest.TestCase):
    """The card on a folder of two weapons, on a `cmds` that answers nothing."""

    def setUp(self):
        from maya_moveset import panel
        self.panel = panel
        self.folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.folder, True)
        for name, data in ((m.GRAPH, graph()), ("graph.dagger.json", dagger_graph())):
            with open(os.path.join(self.folder, name), "w", encoding="utf-8") as handle:
                json.dump(data, handle)
        self.cmds = Quiet()
        for name, value in (("cmds", self.cmds), ("folder", lambda: self.folder)):
            patcher = mock.patch.object(panel, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def card(self):
        return {"view": FakeView(self.folder), "status": "st", "sub": "sub",
                "root_menu": "root", "weapon": None,
                "chips": dict((key, "chip_" + key) for key, _l in m.TYPES),
                "segs": {"longsword": "seg_longsword", "dagger": "seg_dagger"},
                "roots": [], "mtime": 0.0}

    def test_load_takes_the_weapon_the_state_names(self):
        card = self.card()
        self.panel._load(card, frame=True)
        self.assertEqual(card["weapon"].key, "longsword")        # the first, with no key written

        m.write_state(self.folder, weapon="dagger")
        self.panel._load(card)
        self.assertEqual(card["weapon"].key, "dagger")
        self.assertEqual(card["view"].weapon.graph, "graph.dagger.json")
        self.assertIn("AM_Dg_Atk_NLt", card["view"].graph["nodes"])
        self.assertEqual(self.cmds.edits("iconTextRadioButton", "select")[-1][0], "seg_dagger")

    def test_a_type_the_weapon_has_none_of_is_dimmed_and_leaves_the_filter(self):
        card = self.card()
        card["view"].types = set(["dodge", "hold"])
        m.write_state(self.folder, weapon="dagger")
        self.panel._load(card)
        enabled = dict(self.cmds.edits("checkBox", "enable"))
        self.assertFalse(enabled["chip_dodge"])                  # the dagger has no dodge
        self.assertTrue(enabled["chip_hold"])
        self.assertEqual(card["view"].types, set(["hold"]))       # and it left the filter

    def test_the_summary_counts_the_weapon_shown(self):
        card = self.card()
        m.write_state(self.folder, weapon="dagger")
        self.panel._load(card)
        said = dict((c[1][0], c[2].get("label")) for c in self.cmds.calls
                    if c[0] == "text" and (c[2].get("edit") or c[2].get("e")))
        self.assertEqual(said["sub"], "Dagger - 5 attacks")

    def test_the_poll_follows_a_weapon_switch_made_on_the_page(self):
        card = self.card()
        self.panel._load(card)
        self.assertEqual(card["weapon"].key, "longsword")
        m.write_state(self.folder, weapon="dagger")              # the page wrote it
        self.panel._poll(card)
        self.assertEqual(card["weapon"].key, "dagger")
        self.assertEqual(card["view"].weapon.key, "dagger")

    def test_picking_a_weapon_writes_the_shared_key_and_reloads(self):
        card = self.card()
        with mock.patch.object(self.panel, "_card", lambda: card):
            self.panel.pick_weapon("dagger")
        self.assertEqual(m.read_state(self.folder)[m.STATE_WEAPON], "dagger")
        self.assertEqual(card["weapon"].key, "dagger")
        self.assertEqual(card["view"].framed, 1)

    def test_no_graph_at_all_says_so_and_draws_nothing(self):
        for name in (m.GRAPH, "graph.dagger.json"):
            os.remove(os.path.join(self.folder, name))
        card = self.card()
        self.panel._load(card)
        self.assertIsNone(card["weapon"])
        self.assertEqual(card["view"].graph["nodes"], {})
        said = [c[2].get("label") for c in self.cmds.calls
                if c[0] == "text" and (c[2].get("edit") or c[2].get("e"))]
        self.assertTrue(any("No graph.json" in (text or "") for text in said), said)


if __name__ == "__main__":
    unittest.main()
