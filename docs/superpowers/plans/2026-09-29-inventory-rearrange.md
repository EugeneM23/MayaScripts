# Inventory Rearrange Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Weapons in the inventory grid can be dragged to another spot (swapping with an item they land on when it fits back), the layout remembered, a right-click Sort.

**Architecture:** The decisions are pure functions in `maya_invlook` (`plan_move`, `arrange`, the record); the window (`maya_inventory`) previews and applies them and stores the record through its `Scene` adapter (an optionVar).

**Tech Stack:** stdlib (`maya_invlook`), PySide6 through `maya_hubqt.qt()`, `unittest` under mayapy, `QT_QPA_PLATFORM=offscreen`.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-29-inventory-rearrange-design.md`.
- `maya_invlook` stays stdlib only (a subprocess test pins it).
- Tests: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t .`.
- A grid move touches nothing in the scene.

---

### Task 1: the pure rules (`maya_invlook`)

**Files:** Modify `SkeldarAnim/maya_invlook.py`; Test `tests/test_invlook.py`.

**Interfaces — Produces:**
- `footprint(spot, size) -> set[(col, row)]`
- `clamp(spot, size, cols=COLS, rows=ROWS) -> (col, row)`
- `plan_move(placements, cells, key, spot, cols=COLS, rows=ROWS) -> (kind, placements, other)`, kind ∈ `"move" | "swap" | "same" | None` (None = refused, placements unchanged)
- `pack(items, cols=COLS, rows=ROWS, taken=None)` (the free cells respected)
- `arrange(items, stored, cols=COLS, rows=ROWS) -> placements`
- `layout_record(placements) -> str` (JSON), `read_record(text) -> dict`

- [ ] **Step 1: Failing tests** (appended to `tests/test_invlook.py`):

```python
DEFAULT = {"LongSword_02": (0, 0), "Spear_01": (1, 0), "Spear_03": (2, 0),
           "Dagger_01": (3, 0), "Creep_Sword": (3, 2)}
SIZES = {"LongSword_02": (1, 4), "Spear_01": (1, 5), "Spear_03": (1, 5),
         "Dagger_01": (1, 2), "Creep_Sword": (1, 3)}


class PlanMove(unittest.TestCase):

    def test_into_free_cells_it_moves(self):
        kind, placed, other = look.plan_move(DEFAULT, SIZES, "Dagger_01", (6, 1))
        self.assertEqual((kind, placed["Dagger_01"], other), ("move", (6, 1), None))
        self.assertEqual(DEFAULT["Dagger_01"], (3, 0))       # the input untouched

    def test_over_its_own_old_cells_it_moves(self):
        kind, placed, _ = look.plan_move(DEFAULT, SIZES, "Creep_Sword", (3, 1))
        self.assertIsNone(kind)                               # (3,1) is the dagger's
        kind, placed, _ = look.plan_move(DEFAULT, SIZES, "Dagger_01", (4, 0))
        kind, placed, _ = look.plan_move(placed, SIZES, "Dagger_01", (4, 1))
        self.assertEqual((kind, placed["Dagger_01"]), ("move", (4, 1)))

    def test_the_same_spot_is_nothing(self):
        self.assertEqual(look.plan_move(DEFAULT, SIZES, "Dagger_01", (3, 0))[0], "same")

    def test_onto_one_item_that_fits_back_they_swap(self):
        kind, placed, other = look.plan_move(DEFAULT, SIZES, "LongSword_02", (1, 0))
        self.assertEqual((kind, other), ("swap", "Spear_01"))
        self.assertEqual((placed["LongSword_02"], placed["Spear_01"]), ((1, 0), (0, 0)))

    def test_onto_one_item_that_does_not_fit_back_nothing(self):
        kind, placed, other = look.plan_move(DEFAULT, SIZES, "Dagger_01", (0, 0))
        self.assertEqual((kind, other), (None, "LongSword_02"))
        self.assertEqual(placed, DEFAULT)

    def test_onto_two_items_nothing(self):
        spots = dict(DEFAULT, Dagger_01=(5, 0))
        sizes = dict(SIZES, Dagger_01=(1, 2))
        spots["Creep_Sword"] = (5, 2)
        kind, placed, _ = look.plan_move(spots, sizes, "LongSword_02", (5, 0))
        self.assertIsNone(kind)
        self.assertEqual(placed, spots)

    def test_the_spot_is_clamped_into_the_grid(self):
        kind, placed, _ = look.plan_move(DEFAULT, SIZES, "Spear_01", (9, 3))
        self.assertEqual((kind, placed["Spear_01"]), ("move", (9, 0)))
        self.assertEqual(look.clamp((-3, 7), (1, 4)), (0, 1))


class Arrange(unittest.TestCase):

    ITEMS = [(k, SIZES[k]) for k in ("LongSword_02", "Spear_01", "Spear_03", "Dagger_01", "Creep_Sword")]

    def test_nothing_stored_is_the_pack(self):
        self.assertEqual(look.arrange(self.ITEMS, {}), look.pack(self.ITEMS))
        self.assertEqual(look.arrange(self.ITEMS, {}), DEFAULT)

    def test_stored_spots_are_kept(self):
        placed = look.arrange(self.ITEMS, {"Dagger_01": [9, 3], "LongSword_02": [8, 0]})
        self.assertEqual((placed["Dagger_01"], placed["LongSword_02"]), ((9, 3), (8, 0)))
        self.assertEqual(set(placed), set(k for k, _ in self.ITEMS))

    def test_an_overlap_or_a_spot_outside_is_repacked_not_lost(self):
        placed = look.arrange(self.ITEMS, {"LongSword_02": [0, 0], "Spear_01": [0, 0],
                                           "Dagger_01": [9, 4], "Creep_Sword": "x"})
        self.assertEqual(placed["LongSword_02"], (0, 0))
        self.assertEqual(set(placed), set(k for k, _ in self.ITEMS))
        cells = [c for k, s in placed.items() for c in look.footprint(s, SIZES[k])]
        self.assertEqual(len(cells), len(set(cells)))

    def test_the_record_round_trips_and_a_bad_one_reads_empty(self):
        self.assertEqual(look.read_record(look.layout_record(DEFAULT)),
                         dict((k, list(v)) for k, v in DEFAULT.items()))
        self.assertEqual(look.read_record("{not json"), {})
        self.assertEqual(look.read_record(None), {})
        self.assertEqual(look.read_record("[1, 2]"), {})
```

- [ ] **Step 2: Run — FAIL** (`plan_move` missing).
- [ ] **Step 3: Implement** in `maya_invlook.py` (after `pack`):

```python
def footprint(spot, size):
    col, row = spot
    return set((col + i, row + j) for i in range(size[0]) for j in range(size[1]))


def clamp(spot, size, cols=COLS, rows=ROWS):
    return (max(0, min(cols - size[0], int(spot[0]))),
            max(0, min(rows - size[1], int(spot[1]))))


def _clear(placements, cells, cols, rows):
    seen = set()
    for key, spot in placements.items():
        size = cells.get(key, (1, 3))
        if spot[0] < 0 or spot[1] < 0 or spot[0] + size[0] > cols or spot[1] + size[1] > rows:
            return False
        mine = footprint(spot, size)
        if mine & seen:
            return False
        seen |= mine
    return True


def plan_move(placements, cells, key, spot, cols=COLS, rows=ROWS):
    size = cells.get(key, (1, 3))
    spot = clamp(spot, size, cols, rows)
    if placements.get(key) == spot:
        return ("same", dict(placements), None)
    wanted = footprint(spot, size)
    under = [other for other, where in placements.items()
             if other != key and footprint(where, cells.get(other, (1, 3))) & wanted]
    moved = dict(placements)
    moved[key] = spot
    if not under:
        return ("move", moved, None)
    if len(under) > 1:
        return (None, dict(placements), None)
    other = under[0]
    moved[other] = placements[key]
    if _clear(moved, cells, cols, rows):
        return ("swap", moved, other)
    return (None, dict(placements), other)
```

`pack` gains `taken=None` (`taken = set(taken or ())` as its start), and:

```python
def arrange(items, stored, cols=COLS, rows=ROWS):
    placed, taken = {}, set()
    for key, size in items:
        try:
            spot = (int(stored[key][0]), int(stored[key][1]))
        except (KeyError, TypeError, ValueError, IndexError):
            continue
        if spot[0] < 0 or spot[1] < 0 or spot[0] + size[0] > cols or spot[1] + size[1] > rows:
            continue
        mine = footprint(spot, size)
        if mine & taken:
            continue
        placed[key] = spot
        taken |= mine
    placed.update(pack([(k, s) for k, s in items if k not in placed], cols, rows, taken))
    return placed


def layout_record(placements):
    return json.dumps(dict((k, list(v)) for k, v in placements.items()), sort_keys=True)


def read_record(text):
    try:
        data = json.loads(text or "")
    except (TypeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}
```

- [ ] **Step 4: Run** `tests.test_invlook` — PASS. **Step 5: Commit** — `feat(inventory): the grid's rules - move, swap, arrange a remembered layout`

### Task 2: the window drags in the grid

**Files:** Modify `SkeldarAnim/maya_inventory.py`; Test `tests/test_inventory.py`.

**Interfaces — Consumes:** Task 1. **Produces:** `Scene.remembered_layout() -> dict`, `Scene.remember_layout(placements)` (optionVar `skeldarInventoryLayout`); `InventoryWindow.grid_plan(x, y, key, grab) -> (kind, placements, other, spot)`; `InventoryWindow.drop_at(gx, gy, source, grab=None)`; `InventoryWindow.sort()`; `InventoryWindow.preview` (for paint: `(cells, ok)` or None).

- [ ] **Step 1: Failing tests** (the FakeScene gains `remembered_layout` → `self.layout_in` and `remember_layout` → `self.layout_out = dict(p)`):

```python
    def at_cell(self, col, row, dx=5, dy=5):
        gx, gy = self.win.rects["grid"][:2]
        p = self.win.mapToGlobal(QT.QtCore.QPoint(int(gx + col * look.CELL + dx),
                                                  int(gy + row * look.CELL + dy)))
        return p.x(), p.y()

    def test_a_grid_drop_moves_the_item_and_remembers(self):
        self.win.drop_at(*self.at_cell(6, 1), source=("grid", "Dagger_01"), grab=(0, 0))
        self.assertEqual(self.win.placements["Dagger_01"], (6, 1))
        self.assertEqual(self.scene.layout_out["Dagger_01"], (6, 1))
        self.assertEqual([e for e in self.scene.log if e[0] != "target"], [])

    def test_the_grab_point_stays_under_the_cursor(self):
        self.win.drop_at(*self.at_cell(6, 3), source=("grid", "LongSword_02"), grab=(0, 2))
        self.assertEqual(self.win.placements["LongSword_02"], (6, 1))

    def test_onto_another_item_that_fits_back_they_swap(self):
        self.win.drop_at(*self.at_cell(1, 0), source=("grid", "LongSword_02"), grab=(0, 0))
        self.assertEqual((self.win.placements["LongSword_02"], self.win.placements["Spear_01"]),
                         ((1, 0), (0, 0)))
        self.assertIn("swapped", self.win.status_text)

    def test_no_room_leaves_the_grid_as_it_was(self):
        before = dict(self.win.placements)
        self.win.drop_at(*self.at_cell(0, 0), source=("grid", "Dagger_01"), grab=(0, 0))
        self.assertEqual(self.win.placements, before)
        self.assertIn("no room", self.win.status_text)

    def test_sort_packs_the_catalog_again_and_remembers(self):
        self.win.drop_at(*self.at_cell(6, 1), source=("grid", "Dagger_01"), grab=(0, 0))
        self.win.sort()
        self.assertEqual(self.win.placements["Dagger_01"], (3, 0))
        self.assertEqual(self.scene.layout_out["Dagger_01"], (3, 0))

    def test_a_remembered_layout_opens_as_it_was_left(self):
        self.scene.layout_in = {"Dagger_01": [9, 3]}
        win = inv.make_window(self.scene, parent=None, remember=False)
        self.addCleanup(win.deleteLater)
        self.assertEqual(win.placements["Dagger_01"], (9, 3))

    def test_the_plan_under_the_cursor(self):
        x, y = self.win.rects["grid"][:2]
        kind, _placed, other, spot = self.win.grid_plan(x + 1 * look.CELL + 3, y + 3, "LongSword_02", (0, 0))
        self.assertEqual((kind, other, spot), ("swap", "Spear_01", (1, 0)))
```

- [ ] **Step 2: Run — FAIL.**
- [ ] **Step 3: Implement** in `maya_inventory.py`:
  - `Scene.remembered_layout()`: `look.read_record(cmds.optionVar(query=LAYOUT_OPTIONVAR))` when it exists, else `{}`; `Scene.remember_layout(placements)`: `cmds.optionVar(stringValue=(LAYOUT_OPTIONVAR, look.layout_record(placements)))`. `LAYOUT_OPTIONVAR = "skeldarInventoryLayout"`.
  - `__init__`: `self.placements = look.arrange(self._items(), scene.remembered_layout())`, `self._items()` = `[(e.key, self.cells[e.key]) for e in catalog.WEAPONS]`; `self.preview = None`.
  - `_start(source, point, grab=(0, 0))`: the press computes `grab` for a grid item: `(int((x - ix) // cell), int((y - iy) // cell))` from its `item_rect`.
  - `grid_plan(x, y, key, grab)`: the cell under (x, y) minus `grab` → `look.plan_move(self.placements, self.cells, key, spot)`; answers `(kind, placements, other, clamped spot)`.
  - `_caption` over the grid with a grid source: the plan → `self.preview = (footprint cells, kind in ("move", "swap"))`, caption «move here» / «swap with <label>» / «no room» (red) / "" for "same"; the preview cleared elsewhere and at `_end`.
  - `drop_at(gx, gy, source, grab=None)`: a grid source released on the grid (`hit` "grid" or "item") → `grab = grab if given else self._drag["grab"] or (0, 0)` → plan: "move" → «<label> moved», "swap" → «<label> and <other label> swapped», both remember the new placements; None → «no room there»; "same" → nothing.
  - `sort()`: `self.placements = look.pack(self._items())`, remembered, «inventory sorted».
  - mouse: a right press on the grid with no drag → a `QMenu` with «Sort the inventory» → `sort()`.
  - paint: the preview's cells filled `valid`/`invalid` at alpha 90 under the items.
- [ ] **Step 4: Run** `tests.test_inventory tests.test_invlook` and the whole suite — PASS; render offscreen mid-drag (a preview set) and look at it.
- [ ] **Step 5: Commit** — `feat(inventory): drag weapons around the grid - move, swap, remembered, sorted`; refresh the installed copy (port 7001) and add a paragraph to CLAUDE.md's inventory section.
