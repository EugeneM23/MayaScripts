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
        self.assertEqual(m.initials("anna petrova"), "AP")


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

    def test_an_assignee_filter_and_unassigned(self):
        stand = m.trees(graph(), state())[0]
        s = state(assignee={"AM_Longsword_Attack_Left_Hold|1p": "Anna"})
        keep = m.kept(stand, s, who="Anna")
        self.assertIn(stand.nodes[1].key, keep)
        self.assertNotIn(stand.nodes[2].key, keep)
        free = m.kept(stand, s, who="")
        self.assertIn(stand.nodes[0].key, free)


class Files(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.folder, True)

    def test_state_round_trip_keeps_the_pages_other_keys(self):
        path = os.path.join(self.folder, m.STATE)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"longswordMoveset.page": "board",
                       "longswordMoveset.status": json.dumps({"A|3p": "done"})}, handle)
        s = m.read_state(self.folder)
        m.write_state(self.folder, status=m.set_status(s, "B", "1p", "progress"),
                      assignee=m.set_assignee(s, "B", "1p", "Anna"))
        with open(path, encoding="utf-8") as handle:
            raw = json.load(handle)
        self.assertEqual(raw["longswordMoveset.page"], "board")
        self.assertEqual(m.read_state(self.folder)["status"], {"A|3p": "done", "B|1p": "progress"})
        self.assertEqual(m.read_state(self.folder)["assignee"], {"B|1p": "Anna"})
        s = m.read_state(self.folder)
        self.assertEqual(m.set_status(s, "A", "3p", ""), {"B|1p": "progress"})

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


if __name__ == "__main__":
    unittest.main()
