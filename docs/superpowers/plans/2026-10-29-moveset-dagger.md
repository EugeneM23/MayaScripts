# Moveset: the Dagger and the weapon chooser — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** the Dagger's combo trees beside the Longsword's, chosen by a switch in the Moveset card and on
the animator's page, with the dagger's graph extracted by their own pipeline.

**Architecture:** the graph file declares its weapon (`meta.weapon`) and each node's type, so neither
the plugin nor the page holds a naming rule per weapon; a graph without those fields is the Longsword
read by today's rules. The card lists the graphs it finds in the moveset folder, and the chosen weapon
is a shared key in `state.json`, so the card and the page always show the same one.

**Tech Stack:** `maya_moveset` (stdlib `model.py`, PySide6 `view.py`, `cmds` `panel.py`), mayapy's
unittest; their own local tool (`extract_graph.py`, `serve.py`, `design-b-v3.html`) in
`Documents/AtoneExperiments/LongswordMoveset`, outside this repo.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-10-29-moveset-combo-trees-design.md` (the card) and
  `docs/superpowers/specs/2026-10-29-moveset-dagger-design.md` (this work).
- `model.py` stays **stdlib only** — a subprocess test pins it.
- Nothing of the moveset's data ships: the folder is the animator's (`skeldarMovesetFolder`).
- **Nothing of the sword's data moves or is regenerated**: `graph.json` and `media/` stay as they are,
  and every new field is optional on read.
- The state file is written key by key, keeping every other key the page wrote (`model.write_state`).
- Tests run `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest ...` from the repo root,
  Qt tests with `$env:QT_QPA_PLATFORM = 'offscreen'`.
- Их инструмент (page, serve.py, extract_graph.py) правится в их папке и в git не попадает.

---

### Task 1: the model lists weapons and reads a graph's own rules

**Files:**
- Modify: `SkeldarAnim/maya_moveset/model.py`
- Test: `tests/test_moveset_model.py`

**Interfaces:**
- Consumes: today's `model.read_state`, `write_state`, `label`, `attack_type`, `thumbnail`, `TYPES`.
- Produces:
  - `Weapon = collections.namedtuple("Weapon", ["key", "label", "graph", "media", "prefix"])`
  - `weapons(folder) -> [Weapon]` — `graph.json` first, then `graph.*.json` by file name; empty list
    when the folder holds no graph.
  - `weapon_of(folder, key) -> Weapon | None`
  - `chosen_weapon(state, available) -> Weapon` — the state's key when it is available, else the first.
  - `set_weapon(state, key) -> str` — the value to write under the `weapon` key.
  - `label(node_id, custom=(), prefix=LONGSWORD_PREFIX)`
  - `node_type(graph, node_id) -> str` — the node's own `type`, else `attack_type(node_id)`.
  - `types_in(graph) -> [(key, label)]` — the rows of `TYPES` the graph actually holds.
  - `thumbnail(folder, node_id, view="3p", media="")`
  - `load_graph(folder, graph="graph.json")`
  - `STATE_WEAPON = "weapon"`

- [ ] **Step 1: Write the failing tests**

```python
class Weapons(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)

    def _write(self, name, graph):
        with open(os.path.join(self.dir, name), "w", encoding="utf-8") as handle:
            json.dump(graph, handle)

    def test_a_folder_of_two_graphs_lists_the_sword_first(self):
        self._write("graph.json", {"nodes": {}, "edges": [], "entries": []})
        self._write("graph.dagger.json", {"nodes": {}, "edges": [], "entries": [],
                                          "meta": {"weapon": {"key": "dagger", "label": "Dagger",
                                                              "prefix": "AM_Dg_Atk_", "media": "dagger"}}})
        keys = [w.key for w in m.weapons(self.dir)]
        self.assertEqual(keys, ["longsword", "dagger"])

    def test_a_graph_with_no_meta_is_the_longsword_by_todays_rules(self):
        self._write("graph.json", {"nodes": {}, "edges": [], "entries": []})
        sword = m.weapons(self.dir)[0]
        self.assertEqual((sword.label, sword.graph, sword.media), ("Longsword", "graph.json", ""))
        self.assertEqual(m.label("AM_Longsword_Attack_Light_Forward_Combo_1", (), sword.prefix),
                         "Light Forward Combo 1")

    def test_a_graph_file_names_a_weapon_with_no_meta(self):
        self._write("graph.dagger.json", {"nodes": {}, "edges": [], "entries": []})
        only = m.weapons(self.dir)[0]
        self.assertEqual((only.key, only.label, only.media), ("dagger", "Dagger", "dagger"))

    def test_the_daggers_prefix_and_media_come_from_its_graph(self):
        ...  # label("AM_Dg_Atk_NLt_NLt_NHd", (), dagger.prefix) == "NLt NLt NHd"
             # thumbnail(dir, "AM_Dg_Atk_Spr", "3p", "dagger") -> media/dagger/AM_Dg_Atk_Spr.jpg

    def test_the_chosen_weapon_falls_back_to_the_first(self):
        ...  # chosen_weapon({"weapon": "bow"}, two) is the sword; {"weapon": "dagger"} is the dagger

    def test_a_nodes_own_type_wins_over_the_name_rule(self):
        graph = {"nodes": {"AM_Dg_Atk_NLt_NLt_NHd": {"type": "hold"},
                           "AM_Longsword_Attack_Light_Forward_Combo_1": {}}}
        self.assertEqual(m.node_type(graph, "AM_Dg_Atk_NLt_NLt_NHd"), "hold")
        self.assertEqual(m.node_type(graph, "AM_Longsword_Attack_Light_Forward_Combo_1"), "light")

    def test_the_chips_are_the_types_the_graph_holds(self):
        ...  # types_in(dagger graph) has no ("dodge", "Dodge")
```

- [ ] **Step 2: Run them, see them fail** — `mayapy -m unittest tests.test_moveset_model -v`
- [ ] **Step 3: Implement in `model.py`** — `Weapon`, `weapons` (glob the folder, read each file's
      `meta.weapon`, the fallbacks: `graph.json` → longsword/`LONGSWORD_PREFIX`/media "";
      `graph.<key>.json` → key, `key.capitalize()`, media `key`), `weapon_of`, `chosen_weapon`,
      `set_weapon`, `label(prefix=)`, `node_type`, `types_in`, `thumbnail(media=)`,
      `load_graph(folder, graph=GRAPH)`. Keep every existing signature working with its old defaults.
- [ ] **Step 4: Run the tests, see them pass**, and the whole `test_moveset_model` with them.
- [ ] **Step 5: Commit** — `feat(moveset): the model lists the folder's weapons`

---

### Task 2: the view draws a weapon's own previews, types and labels

**Files:**
- Modify: `SkeldarAnim/maya_moveset/view.py`
- Test: `tests/test_moveset_view.py`

**Interfaces:**
- Consumes: Task 1's `node_type`, `thumbnail(..., media=)`, `label(..., prefix=)`, `Weapon`.
- Produces: `TreeView.set_data(graph, state, folder, weapon=None)` — `weapon` a `Weapon`; None keeps
  the Longsword's rules. `TreeView.weapon` holds it; `Card` reads its colour through
  `view.node_type(node)` and its name through `view.label(node_id)`.

- [ ] **Step 1: Write the failing tests** (offscreen, the file's own fixture pattern)

```python
def test_a_dagger_graph_draws_its_own_labels_types_and_preview_path(self):
    view = treeview.TreeView(None, {})
    view.set_data(DAGGER_GRAPH, m.read_state(""), self.dir,
                  m.Weapon("dagger", "Dagger", "graph.dagger.json", "dagger", "AM_Dg_Atk_"))
    card = [c for c in view.cards if c.node.id == "AM_Dg_Atk_NLt_NLt_NHd"][0]
    self.assertEqual(view.label(card.node.id), "NLt NLt NHd")
    self.assertEqual(view.node_type(card.node), "hold")
    self.assertTrue(view.thumb_path(card.node.id).endswith(os.path.join("dagger",
                    "AM_Dg_Atk_NLt_NLt_NHd.jpg")))
```

- [ ] **Step 2: Run it, see it fail** — `QT_QPA_PLATFORM=offscreen mayapy -m unittest tests.test_moveset_view -v`
- [ ] **Step 3: Implement** — `set_data(..., weapon=None)` keeps `self.weapon`; `label`, `node_type`,
      `thumb_path` helpers on the view; `Card.paint` and `_tip` read them; `Node.kind` is set from
      `node_type` at build time (`m.trees` already fills `kind` from the name — pass the graph's type
      through `Tree`/`Node` by setting `node.kind = m.node_type(graph, node.id)` after `m.trees`).
- [ ] **Step 4: Run the file's whole tests, see them pass.**
- [ ] **Step 5: Commit** — `feat(moveset): the view reads the weapon's own rules`

---

### Task 3: the card's `[Longsword | Dagger]` segments

**Files:**
- Modify: `SkeldarAnim/maya_moveset/panel.py`
- Test: `tests/test_moveset_view.py` (its `Build` and `Presses` classes, the repo's fake `cmds`)

**Interfaces:**
- Consumes: Task 1 and Task 2.
- Produces: `WEAPONS_COLL = "skeldarMovesetWeapons"`, `WEAPON_SEG = "skeldarMovesetWeapon_{0}"`,
  `weapon()` (the card's chosen `Weapon`), `pick_weapon(key)` (the press: write the shared key, reload),
  `_load` reading the chosen weapon's graph.

- [ ] **Step 1: Write the failing tests**

```python
def test_the_card_builds_a_segment_a_weapon_and_the_sword_is_lit(self):
    ...  # fake cmds: iconTextRadioButton names, the lit one is the state's weapon

def test_one_weapon_builds_no_segments(self):
    ...  # a folder with graph.json only: no WEAPON_SEG control

def test_picking_the_dagger_writes_the_shared_key_and_reloads_its_graph(self):
    panel.pick_weapon("dagger")
    self.assertEqual(json.load(open(state_path))["longswordMoveset.weapon"], '"dagger"')
    self.assertEqual(card["view"].weapon.key, "dagger")   # and the trees are the dagger's
```

- [ ] **Step 2: Run them, see them fail.**
- [ ] **Step 3: Implement** — the collection built from `m.weapons(folder)` right under `SUB`
      (`style="textOnly"`, `height=hubstyle.height("segment", 24)`, `collection=`, `onCommand=`,
      marked `"segment"`), skipped entirely for fewer than two weapons; `_load` picks the weapon
      (`m.chosen_weapon(state, weapons)`), loads its graph, hands `weapon` to `set_data`, fills the
      chips from `m.types_in(graph)`, and the subtitle reads the weapon's label («Dagger - 21 attacks,
      0 of 42 done»); `pick_weapon` writes `weapon` through `write_state` and reloads with `frame=True`;
      `_poll` rereads the weapon too, so a switch on the page reaches the card.
- [ ] **Step 4: Run `tests.test_moveset_model tests.test_moveset_view`, see them pass.**
- [ ] **Step 5: Commit** — `feat(moveset): the card's weapon chooser`

---

### Task 4: their page's two buttons (their folder, not in git)

**Files:**
- Modify: `~/Documents/AtoneExperiments/LongswordMoveset/serve.py` (a `GET /graphs.json` listing)
- Modify: `~/Documents/AtoneExperiments/LongswordMoveset/mockups/design-b-v3.html`
  (the header's buttons, the graph fetch at line 225, `thumbSrc` at 433 and the board's `../media/`
  at 719)

- [ ] **Step 1: `serve.py` answers the listing** — `GET /graphs.json` → `[{"key", "label", "graph",
      "media"}]` computed from the folder exactly as `model.weapons` computes it (the same fallbacks).
- [ ] **Step 2: the page reads the weapon** — `const WKEY = SPREFIX + "weapon"`, the chosen key from
      localStorage (which the state sync has already filled from the file), the list from
      `fetch("../graphs.json")` with `[{key:"longsword",label:"Longsword",graph:"graph.json",media:""}]`
      as the fallback when it 404s.
- [ ] **Step 3: the buttons** — in `<div class="top">` beside the `<h1>`, one button a weapon, the
      chosen one lit; a press writes `WKEY` (the sync pushes it to the file) and reloads the page.
- [ ] **Step 4: the paths follow the weapon** — `fetch("../" + weapon.graph)`, and
      `thumbSrc`/the board's img use `../media/<weapon.media>/<id>.jpg` (no subfolder for the sword).
- [ ] **Step 5: check it in the browser** — the two buttons switch the trees; a switch in the card
      reaches the page (its 2 s poll reloads it) and the other way round.
- [ ] **Step 6: Commit the repo side only** — the page is theirs; nothing of it goes into git.

---

### Task 5: their extractor takes a weapon (their folder, not in git)

**Files:**
- Modify: `~/Documents/AtoneExperiments/LongswordMoveset/tools/extract_graph.py`
- Modify: `~/Documents/AtoneExperiments/LongswordMoveset/tools/ue_runner.py`,
  `tools/regenerate.ps1` (a `-Weapon` parameter, default `longsword`)

- [ ] **Step 1: the weapon table** — `WEAPONS = {"longsword": {...}, "dagger": {...}}` with
      `resources` (`/Game/Characters/Presets/Resources/DA_Resources_Sword` / `_Dagger`), `folder`
      (`.../Weapons/Longsword/Montages` / `.../Weapons/Dagger`), `prefix` (`AM_Longsword_Attack_` /
      `AM_Dg_Atk_`), `label`, `out` (`graph.json` / `graph.dagger.json`), `media` (`""` / `dagger`),
      `checks` (the sword's three named pairs / none).
- [ ] **Step 2: the type rule a weapon** — the sword's words (`Hold`/`Light`/`Sprint`/`Jump`/`Dodge`
      anywhere in the id) and the dagger's abbreviations (the LAST segment: `Hd` → hold, `Lt` → light;
      `Spr` → sprint; `JA` → jump), written as `nodes[id]["type"]`.
- [ ] **Step 3: `meta.weapon`** — `{key, label, prefix, media}` into the graph's meta beside
      `playRate` / `chooser` / `generated`.
- [ ] **Step 4: the run reads the weapon** — `run(weapon="longsword")`, the output path and the
      `unreachable` folder from the table, `check()` taking the weapon's own named pairs (the general
      checks — every node has an animation, every node has a slot — stay for both).
- [ ] **Step 5: the sword's reproduction** — a `--out` override so the sword can be written to a
      scratch file and compared with today's `graph.json`.

---

### Task 6: the editor run (ask the animator first)

- [ ] **Step 1: ask** — the run starts a throwaway editor and takes minutes of their machine.
- [ ] **Step 2: the dagger** — `regenerate.ps1 -Step extract -Weapon dagger`; read the printed
      counts, the «in the folder, not in the graph» list and the no-1P list.
- [ ] **Step 3: the sword into a scratch file** in the same editor session, and `diff` it against
      `graph.json`: equal but for `meta.generated`, `meta.weapon` and the nodes' `type`.
- [ ] **Step 4: the dagger's graph checked** — every node an `AM_Dg_Atk_*` that exists in the dagger
      folder, every node with an animation and a slot; the counts said to the animator.
- [ ] **Step 5: the card and the page on the real graph** — the segments list both weapons, the trees
      draw, the labels read «NLt NLt NHd», the chips hold no Dodge.

---

### Task 7: the docs and the suite

**Files:**
- Modify: `CLAUDE.md` (the Moveset section), `docs/superpowers/specs/2026-10-29-moveset-dagger-design.md`
  (the measured proof lines)

- [ ] **Step 1: the Moveset section** gains the weapon chooser, the graph's self-describing meta, the
      dagger's own files and what the extraction measured.
- [ ] **Step 2: the whole suite** — `mayapy -m unittest discover -s tests -t .`, and the six failures
      that predate the work (`test_chat_deploy.Keys`, `test_scenetabs_leak` ×3,
      `test_timebar_lanes_sync` ×2) are the only ones.
- [ ] **Step 3: Commit** — `docs(moveset): the Dagger and the chooser, as built`

## Self-review

- **Spec coverage:** the graph declaring its weapon and node types (Tasks 1, 5); the dagger's files
  beside the sword's (Tasks 1, 5); one `state.json` and the shared weapon key (Tasks 1, 3, 4); the
  labels as the project names them (Tasks 1, 2, 5); the card's segments, chips and previews (Tasks 2,
  3); the page's buttons (Task 4); the four extractor knobs and the sword's own checks (Task 5); the
  proofs (Tasks 6, 7).
- **Placeholders:** the test bodies in Tasks 1 and 3 marked `...` are the ones whose assertions are
  spelled out in the comment beside them; every other step carries its own code or its exact command.
- **Type consistency:** `Weapon(key, label, graph, media, prefix)` is used with those names in Tasks
  1-4; `set_data(graph, state, folder, weapon=None)` in Tasks 2 and 3; `node_type(graph, node_id)` in
  Tasks 1 and 2.
