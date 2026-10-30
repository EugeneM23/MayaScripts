"""maya_moveset.model: the trees the moveset page draws, and the shared state."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from maya_moveset import model as m

PLUGIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SkeldarAnim")


def graph():
    return {
        "entries": [
            {"situation": "onfoot", "target": "AM_Longsword_Attack_Stand_Hold", "directions": ["none"]},
            {"situation": "dodge", "target": "AM_Longsword_Attack_Stand_Hold", "directions": ["none"]},
            {"situation": "onfoot", "target": "AM_Longsword_Attack_Left_Hold", "directions": ["left"]},
        ],
        "edges": [
            {"from": "AM_Longsword_Attack_Stand_Hold", "to": "AM_Longsword_Attack_Left_Hold",
             "kind": "chain", "directions": ["left"]},
            {"from": "AM_Longsword_Attack_Stand_Hold", "to": "AM_Longsword_Attack_Right_Light",
             "kind": "chain", "directions": ["right"]},
            {"from": "AM_Longsword_Attack_Right_Light", "to": "AM_Longsword_Attack_Stand_Hold",
             "kind": "chain", "directions": []},
            {"from": "AM_Longsword_Attack_Stand_Hold", "to": "AM_Longsword_Attack_Stand_Light",
             "kind": "release", "directions": []},
            {"from": "AM_Longsword_Attack_Stand_Hold", "to": "AM_Longsword_Attack_Jump_Ascent",
             "kind": "jump", "directions": []},
            {"from": "AM_Longsword_Attack_Left_Hold", "to": "AM_Longsword_Attack_Stand_Hold",
             "kind": "fresh", "directions": []},
        ],
        "nodes": {"AM_Longsword_Attack_Stand_Hold": {
            "path": "/Game/M/AM_Longsword_Attack_Stand_Hold.AM_Longsword_Attack_Stand_Hold",
            "slot": "DefaultSlot", "slot1p": "1P"},
            "AM_Longsword_Attack_Left_Hold": {"path": "/Game/M/AM_Longsword_Attack_Left_Hold", "slot": "DefaultSlot"}},
    }


def state(**values):
    s = {"status": {}, "assignee": {}, "people": [], "icons": {}, "custom": [], "hidden": []}
    s.update(values)
    return s


class Pure(unittest.TestCase):
    def test_imports_nothing_of_maya_or_qt(self):
        code = "import sys, maya_moveset.model; print(sorted(m for m in ('maya', 'PySide6') if m in sys.modules))"
        out = subprocess.check_output([sys.executable, "-c", code], cwd=PLUGIN).decode().strip()
        self.assertEqual(out, "[]")

    def test_type_and_label(self):
        self.assertEqual(m.attack_type("AM_Longsword_Attack_Sprint_Long"), "sprint")
        self.assertEqual(m.attack_type("AM_Longsword_Attack_Left_Light"), "light")
        self.assertEqual(m.label("AM_Longsword_Attack_Stand_Hold"), "Stand Hold")
        self.assertEqual(m.label("custom-1", [{"id": "custom-1", "name": "Kick"}]), "Kick")

    def test_the_planning_is_gone_from_the_model(self):
        """The card plans nothing (2026-10-29): the page keeps its own board."""
        for name in ("set_status", "set_assignee", "STATUSES", "initials"):
            self.assertFalse(hasattr(m, name), name)


class Trees(unittest.TestCase):
    def test_combos_follow_chains_only_and_a_loop_is_a_leaf(self):
        trees = m.trees(graph(), state())
        roots = [t.root for t in trees]
        self.assertEqual(roots[:2], ["AM_Longsword_Attack_Stand_Hold", "AM_Longsword_Attack_Left_Hold"])
        stand = trees[0]
        self.assertEqual(stand.titles, ["On foot", "After dodge"])
        kids = [n.id for n in stand.nodes if n.depth == 1]
        self.assertEqual(kids, ["AM_Longsword_Attack_Left_Hold", "AM_Longsword_Attack_Right_Light"])
        loop = [n for n in stand.nodes if n.depth == 2][0]
        self.assertEqual((loop.id, loop.link), ("AM_Longsword_Attack_Stand_Hold", "repeat"))
        self.assertEqual(len(stand.wires), 3)

    def test_a_tap_release_opens_its_own_tree_in_combos(self):
        roots = [t.root for t in m.trees(graph(), state())]
        self.assertIn("AM_Longsword_Attack_Stand_Light", roots)

    def test_all_mode_takes_every_kind_but_fresh_and_a_jump_to_a_root_is_a_link(self):
        stand = m.trees(graph(), state(), "all")[0]
        kinds = [n.via for n in stand.nodes if n.depth == 1]
        self.assertEqual(kinds, ["release", "chain", "chain", "jump"])
        self.assertEqual(len(m.trees(graph(), state(), "all")), 2)

    def test_layout_is_the_pages(self):
        stand = m.trees(graph(), state())[0]
        top = stand.nodes[0]
        self.assertEqual((top.x, top.y), (0, m.ROW / 2.0))
        self.assertEqual([n.x for n in stand.nodes if n.depth == 1], [m.COL, m.COL])

    def test_hidden_and_custom_cards(self):
        s = state(hidden=["AM_Longsword_Attack_Left_Hold"],
                  custom=[{"id": "custom-9", "name": "Kick", "parent": "AM_Longsword_Attack_Stand_Hold"}])
        stand = m.trees(graph(), s)[0]
        ids = [n.id for n in stand.nodes]
        self.assertNotIn("AM_Longsword_Attack_Left_Hold", ids)
        self.assertIn("custom-9", ids)

    def test_a_filter_keeps_the_match_its_path_and_below(self):
        stand = m.trees(graph(), state())[0]
        keep = m.kept(stand, state(), types=["light"])
        names = set(n.id for n in stand.nodes if n.key in keep)
        self.assertEqual(names, {"AM_Longsword_Attack_Stand_Hold", "AM_Longsword_Attack_Right_Light"})
        self.assertIsNone(m.kept(stand, state()))

class Files(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.folder, True)

    def test_state_round_trip_keeps_the_pages_other_keys(self):
        path = os.path.join(self.folder, m.STATE)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"longswordMoveset.page": "board",
                       "longswordMoveset.status": json.dumps({"A|3p": "done"})}, handle)
        m.write_state(self.folder, weapon="dagger")
        with open(path, encoding="utf-8") as handle:
            raw = json.load(handle)
        self.assertEqual(raw["longswordMoveset.page"], "board")
        read = m.read_state(self.folder)
        self.assertEqual(read[m.STATE_WEAPON], "dagger")
        self.assertEqual(read["status"], {"A|3p": "done"})      # the page's, left alone

    def test_a_missing_or_broken_file_reads_empty(self):
        self.assertEqual(m.read_state(self.folder)["status"], {})
        with open(os.path.join(self.folder, m.STATE), "w") as handle:
            handle.write("{broken")
        self.assertEqual(m.read_state(self.folder)["people"], [])

    def test_slot_package_and_thumbnail(self):
        g = graph()
        self.assertEqual(m.slot_of(g, "AM_Longsword_Attack_Stand_Hold", "1p"), "1P")
        self.assertIsNone(m.slot_of(g, "AM_Nope", "3p"))
        self.assertEqual(m.package_of(g["nodes"]["AM_Longsword_Attack_Stand_Hold"]["path"]),
                         "/Game/M/AM_Longsword_Attack_Stand_Hold")
        os.makedirs(os.path.join(self.folder, "media", "1p"))
        open(os.path.join(self.folder, "media", "X.jpg"), "w").close()
        self.assertTrue(m.thumbnail(self.folder, "X", "1p").endswith("X.jpg"))
        self.assertEqual(m.thumbnail(self.folder, "Y"), "")


def dagger_graph():
    """The dagger's graph as its extraction writes it: its weapon declared, each node's type."""
    node = lambda name, kind: {"path": "/Game/D/{0}.{0}".format(name), "slot": "DefaultSlot",
                               "slot1p": "1P", "type": kind}
    return {
        "entries": [{"situation": "onfoot", "target": "AM_Dg_Atk_NLt", "directions": ["none"]},
                    {"situation": "sprint_long", "target": "AM_Dg_Atk_Spr", "directions": ["none"]}],
        "edges": [{"from": "AM_Dg_Atk_NLt", "to": "AM_Dg_Atk_NLt_NLt", "kind": "chain", "directions": []},
                  {"from": "AM_Dg_Atk_NLt_NLt", "to": "AM_Dg_Atk_NLt_NLt_NHd", "kind": "chain",
                   "directions": []},
                  {"from": "AM_Dg_Atk_NLt", "to": "AM_Dg_Atk_JA_Passive", "kind": "jump", "directions": []}],
        "nodes": {"AM_Dg_Atk_NLt": node("AM_Dg_Atk_NLt", "light"),
                  "AM_Dg_Atk_NLt_NLt": node("AM_Dg_Atk_NLt_NLt", "light"),
                  "AM_Dg_Atk_NLt_NLt_NHd": node("AM_Dg_Atk_NLt_NLt_NHd", "hold"),
                  "AM_Dg_Atk_JA_Passive": node("AM_Dg_Atk_JA_Passive", "jump"),
                  "AM_Dg_Atk_Spr": node("AM_Dg_Atk_Spr", "sprint")},
        "meta": {"weapon": {"key": "dagger", "label": "Dagger", "prefix": "AM_Dg_Atk_",
                            "media": "dagger"}},
    }


class Weapons(unittest.TestCase):
    """The folder's graphs are the weapons, and each graph carries its own rules."""

    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.folder, True)

    def _write(self, name, data):
        with open(os.path.join(self.folder, name), "w", encoding="utf-8") as handle:
            json.dump(data, handle)

    def test_an_empty_folder_lists_no_weapon(self):
        self.assertEqual(m.weapons(self.folder), [])

    def test_a_folder_of_two_graphs_lists_the_plain_one_first(self):
        self._write(m.GRAPH, graph())
        self._write("graph.dagger.json", dagger_graph())
        self.assertEqual([(w.key, w.label) for w in m.weapons(self.folder)],
                         [("longsword", "Longsword"), ("dagger", "Dagger")])

    def test_a_graph_with_no_meta_is_the_longsword_by_todays_rules(self):
        self._write(m.GRAPH, graph())
        sword = m.weapons(self.folder)[0]
        self.assertEqual((sword.label, sword.graph, sword.media), ("Longsword", m.GRAPH, ""))
        self.assertEqual(m.label("AM_Longsword_Attack_Stand_Hold", (), sword.prefix), "Stand Hold")

    def test_a_graph_file_names_a_weapon_that_declares_nothing(self):
        self._write("graph.dagger.json", {"nodes": {}, "edges": [], "entries": []})
        only = m.weapons(self.folder)[0]
        self.assertEqual((only.key, only.label, only.media), ("dagger", "Dagger", "dagger"))

    def test_a_broken_graph_is_passed_over(self):
        self._write(m.GRAPH, graph())
        with open(os.path.join(self.folder, "graph.bow.json"), "w") as handle:
            handle.write("{broken")
        self.assertEqual([w.key for w in m.weapons(self.folder)], ["longsword"])

    def test_the_daggers_own_prefix_and_media(self):
        self._write(m.GRAPH, graph())
        self._write("graph.dagger.json", dagger_graph())
        dagger = m.weapon_of(self.folder, "dagger")
        self.assertEqual(m.label("AM_Dg_Atk_NLt_NLt_NHd", (), dagger.prefix), "NLt NLt NHd")
        os.makedirs(os.path.join(self.folder, "media", "dagger"))
        open(os.path.join(self.folder, "media", "dagger", "AM_Dg_Atk_Spr.jpg"), "w").close()
        self.assertTrue(m.thumbnail(self.folder, "AM_Dg_Atk_Spr", "3p", dagger.media)
                        .endswith(os.path.join("dagger", "AM_Dg_Atk_Spr.jpg")))
        self.assertEqual(m.thumbnail(self.folder, "AM_Dg_Atk_Spr", "3p"), "")

    def test_the_chosen_weapon_is_the_states_one_else_the_first(self):
        self._write(m.GRAPH, graph())
        self._write("graph.dagger.json", dagger_graph())
        both = m.weapons(self.folder)
        self.assertEqual(m.chosen_weapon(state(), both).key, "longsword")
        self.assertEqual(m.chosen_weapon(state(weapon="dagger"), both).key, "dagger")
        self.assertEqual(m.chosen_weapon(state(weapon="bow"), both).key, "longsword")
        self.assertIsNone(m.chosen_weapon(state(weapon="dagger"), []))

    def test_the_weapon_is_shared_state(self):
        m.write_state(self.folder, weapon="dagger")
        self.assertEqual(m.read_state(self.folder)["weapon"], "dagger")
        m.write_state(self.folder, status={"A|3p": "done"})
        self.assertEqual(m.read_state(self.folder)["weapon"], "dagger")

    def test_a_nodes_own_type_wins_over_the_name_rule(self):
        self.assertEqual(m.node_type(dagger_graph(), "AM_Dg_Atk_NLt_NLt_NHd"), "hold")
        self.assertEqual(m.node_type(dagger_graph(), "AM_Dg_Atk_Spr"), "sprint")
        self.assertEqual(m.node_type(graph(), "AM_Longsword_Attack_Right_Light"), "light")
        self.assertEqual(m.node_type(graph(), "custom-1"), "")

    def test_the_chips_are_the_types_the_graph_holds(self):
        self.assertEqual(m.types_in(dagger_graph()),
                         [("hold", "Hold"), ("light", "Light"), ("sprint", "Sprint"), ("jump", "Jump")])
        #  the sword's graph declares no type: the chips come from its names
        self.assertEqual(m.types_in(graph()), [("hold", "Hold")])

    def test_a_weapons_graph_is_loaded_by_its_own_file(self):
        self._write("graph.dagger.json", dagger_graph())
        dagger = m.weapons(self.folder)[0]
        self.assertEqual(sorted(m.load_graph(self.folder, dagger.graph)["nodes"]),
                         sorted(dagger_graph()["nodes"]))

    def test_the_trees_of_a_dagger_graph(self):
        trees = m.trees(dagger_graph(), state(), "combos")
        self.assertEqual([t.root for t in trees], ["AM_Dg_Atk_NLt", "AM_Dg_Atk_Spr"])
        ids = [n.id for n in trees[0].nodes]
        self.assertEqual(ids, ["AM_Dg_Atk_NLt", "AM_Dg_Atk_NLt_NLt", "AM_Dg_Atk_NLt_NLt_NHd"])


if __name__ == "__main__":
    unittest.main()
