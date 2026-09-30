# The Characters Portrait Grid Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The hub's Characters card becomes a Mortal-Kombat-style grid of square portraits
(one per model, a `[Rig | Skeleton]` switch above it) with no colour controls; a click
selects, Add Character imports, and a portrait dragged into a viewport adds the character
where the cursor meets the floor.

**Architecture:** The catalog gains a `model` column and a `MODELS` table. The grid is
built from three parts:
- a pure look module, `maya_charlook`;
- a Qt widget, `maya_chargrid`, laid over an empty `cmds` columnLayout the Characters
  builder makes, so it lives in both the skinned and the classic hub;
- the inventory's drag ghost, moved into `maya_hubqt` and shared.

The drop asks `droptarget.floor_at` for the floor point. `character.add_character(at=)`
then moves the new rig's `Main`, or the skeleton's `root`, relatively in world space,
all in one undo chunk. The portraits are playblasts rendered once in a disposable GUI Maya
and shipped under `assets/character_portraits/`.

**Tech Stack:** Maya 2027 `maya.cmds` / OpenMaya, PySide6 6.8 (lazy, via
`maya_hubqt.qt()`), stdlib `unittest` under mayapy.

Spec: `docs/superpowers/specs/2026-09-30-character-portrait-grid-design.md`

## Global Constraints

- Tests: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v`, Qt tests with `$env:QT_QPA_PLATFORM = 'offscreen'`; there is no system Python.
- Portrait framing: head and shoulders, square; one portrait per model; `[Rig | Skeleton]` switch; drop facing +Z (translation only).
- Grid cell: at least 72 logical px, at most 120; gap 6; the name strip 18.
- Every colour a widget paints is a `maya_hubstyle.TOKENS` name (a test pins it, as for the inventory).
- Stylesheet/Qt pixels are PHYSICAL: every logical px × `mayaDpiSetting -q -realScaleValue` (trap 98).
- Never touch `SkeldarAnim/maya_graphoverlay/` or the other session's uncommitted CLAUDE.md hunk; commit only this work's files.
- The disposable Maya for this work: port **7004**, its own scratch `MAYA_APP_DIR`, `MAYA_NO_HOME=1`, userSetup in `<MAYA_APP_DIR>/2027/scripts/`; killed after (`Stop-Process -Force`).
- A runner over the port is idempotent (`.ran` marker, guard with `if`, never `raise SystemExit`), BOM-free, reads its payload as utf-8, exec's with an explicit globals dict.

---

### Task 1: The catalog knows models

**Files:**
- Modify: `SkeldarAnim/maya_scenesetup/catalog.py`
- Test: `tests/test_scenesetup_catalog.py`

**Interfaces:**
- Produces:
  - `catalog.Model(key, label)`, `catalog.MODELS` (Manny, Creep, Orc_D, UE4_Mannequin), `catalog.KINDS = ("rig", "skeleton")`;
  - `Character.model` (a field, default "");
  - `model_by_key(key) -> Model|None`, `model_of(entry) -> Model|None`, `character_for(model_key, kind) -> Character|None`, `kinds_of(model_key) -> tuple`, `default_model() -> str`, `portrait_path(model_key) -> str`.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_scenesetup_catalog.py`)

```python
class Models(unittest.TestCase):
    """2026-09-30, the portrait grid: one portrait per MODEL, the kind a switch.
    A catalog row is (model, kind)."""

    def test_the_models_in_grid_order(self):
        self.assertEqual([m.key for m in catalog.MODELS],
                         ["Manny", "Creep", "Orc_D", "UE4_Mannequin"])
        self.assertEqual(catalog.model_by_key("Orc_D").label, "Orc D")
        self.assertIsNone(catalog.model_by_key("Sevarog"))

    def test_every_row_names_a_model_and_every_model_has_a_row(self):
        keys = set(m.key for m in catalog.MODELS)
        for entry in catalog.CHARACTERS:
            self.assertIn(entry.model, keys, entry.key)
        for model in catalog.MODELS:
            self.assertTrue(catalog.kinds_of(model.key), model.key)

    def test_a_model_and_a_kind_name_at_most_one_row(self):
        pairs = [(e.model, e.kind) for e in catalog.CHARACTERS]
        self.assertEqual(len(pairs), len(set(pairs)))

    def test_the_pairs(self):
        want = {("Manny", "rig"): "Manny_Rig", ("Manny", "skeleton"): "Manny",
                ("Creep", "rig"): "Creep_Rig", ("Creep", "skeleton"): "Creep",
                ("Orc_D", "rig"): "Orc_D_Rig",
                ("UE4_Mannequin", "skeleton"): "UE4_Mannequin"}
        for (model, kind), key in want.items():
            self.assertEqual(catalog.character_for(model, kind).key, key)
        self.assertIsNone(catalog.character_for("Orc_D", "skeleton"))
        self.assertIsNone(catalog.character_for("UE4_Mannequin", "rig"))
        self.assertEqual(catalog.kinds_of("Orc_D"), ("rig",))
        self.assertEqual(catalog.kinds_of("UE4_Mannequin"), ("skeleton",))
        self.assertEqual(catalog.kinds_of("Manny"), ("rig", "skeleton"))

    def test_the_default_is_the_default_rigs_model(self):
        self.assertEqual(catalog.default_model(), "Manny")
        self.assertIs(catalog.model_of(catalog.default_rig()),
                      catalog.model_by_key("Manny"))

    def test_the_portrait_path(self):
        self.assertTrue(catalog.portrait_path("Creep").endswith(
            "assets/character_portraits/Creep.png"))
        self.assertNotIn("\\", catalog.portrait_path("Creep"))
```

- [ ] **Step 2: Run to see it fail** — `mayapy -m unittest tests.test_scenesetup_catalog -v` → AttributeError `MODELS`.

- [ ] **Step 3: Implement** in `catalog.py`: the namedtuple becomes
`Character = collections.namedtuple("Character", "key label file kind textured model", defaults=(False, ""))`,
each row passes `model=` (Manny_Rig/Manny → "Manny", Creep_Rig/Creep → "Creep", Orc_D_Rig → "Orc_D",
UE4_Mannequin → "UE4_Mannequin"), and after `CHARACTERS`:

```python
# The portrait grid (2026-09-30, «сетка с портретами»): one portrait per MODEL,
# in this order, the kind chosen by a [Rig | Skeleton] switch above it.
Model = collections.namedtuple("Model", "key label")
MODELS = [Model("Manny", "Manny"), Model("Creep", "Creep"),
          Model("Orc_D", "Orc D"), Model("UE4_Mannequin", "UE4 Mannequin")]
KINDS = ("rig", "skeleton")


def model_by_key(key):
    for model in MODELS:
        if model.key == key:
            return model
    return None


def model_of(entry):
    return model_by_key(getattr(entry, "model", "") or "")


def character_for(model, kind):
    """The row of `model` in `kind`, or None: Orc D has no skeleton, the UE4
    Mannequin no rig."""
    for entry in CHARACTERS:
        if entry.model == model and entry.kind == kind:
            return entry
    return None


def kinds_of(model):
    """The kinds `model` ships in, in KINDS order."""
    return tuple(kind for kind in KINDS if character_for(model, kind))


def default_model():
    return default_rig().model


def portrait_path(model):
    """The model's square portrait (256 px PNG, alpha), under assets/."""
    return asset_path("character_portraits/{0}.png".format(model))
```

(`asset_path` is defined later in the file than `CHARACTERS`; it is only called at run time.)

- [ ] **Step 4: Run** — the catalog tests pass.
- [ ] **Step 5: Commit** `feat(catalog): characters grouped by model - one portrait each, the kind a switch`.

---

### Task 2: The grid as data — `maya_charlook`

**Files:**
- Create: `SkeldarAnim/maya_charlook.py`
- Modify: `SkeldarAnim/install.py` (`_PAYLOAD` gains `"maya_charlook.py"` and `"maya_chargrid.py"`)
- Test: `tests/test_charlook.py`

**Interfaces:**
- Produces: `CELL_MIN=72, CELL_MAX=120, GAP=6, NAME_H=18, RADIUS=6, GHOST=88, THROTTLE_MS=33, HUB_NAMES`;
  `grid(width, count, scale=1.0) -> (cols, cell, rects, height)` (physical px, rects are the squares);
  `tile_rect(rect, scale)` (square + name strip); `name_rect(rect, scale)`; `hit(rects, x, y, scale=1.0) -> index|None`;
  `state(model, kind, selected, kinds) -> "selected"|"selected_absent"|"absent"|"available"`;
  `place_caption(label, point)`, `absent_text(model_label, kind)`, `import_text(label)`, `tag_text(kind)`;
  `dragged(start, now, threshold) -> bool`; `over_hub(names) -> bool`.

- [ ] **Step 1: Write the failing tests** — `tests/test_charlook.py`:

```python
"""The Characters card's portrait grid as data (2026-09-30): how many columns a
width holds, where each tile is, what a point is, what the lines say. Stdlib.

Spec: docs/superpowers/specs/2026-09-30-character-portrait-grid-design.md
"""
import os
import re
import unittest

import maya_charlook as look

PLUGIN = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "SkeldarAnim")


class Grid(unittest.TestCase):

    def test_the_animators_dock_holds_one_row_of_four(self):
        cols, cell, rects, height = look.grid(330, 4)
        self.assertEqual(cols, 4)
        self.assertTrue(72 <= cell <= 120, cell)
        self.assertEqual(len(rects), 4)
        self.assertEqual(height, cell + look.NAME_H)
        self.assertEqual(len(set(r[1] for r in rects)), 1)

    def test_a_narrow_dock_wraps(self):
        cols, cell, rects, height = look.grid(200, 4)
        self.assertEqual(cols, 2)
        self.assertEqual(height, 2 * (cell + look.NAME_H) + look.GAP)
        self.assertGreater(rects[2][1], rects[0][1])

    def test_a_wide_dock_caps_the_portrait(self):
        cols, cell, _rects, _height = look.grid(900, 4)
        self.assertEqual((cols, cell), (4, look.CELL_MAX))

    def test_no_width_yet_is_one_row_at_the_minimum(self):
        cols, cell, _rects, height = look.grid(0, 4)
        self.assertEqual((cols, cell), (4, look.CELL_MIN))
        self.assertEqual(height, look.CELL_MIN + look.NAME_H)

    def test_the_scale_multiplies(self):
        one = look.grid(330, 4)
        big = look.grid(495, 4, scale=1.5)
        self.assertEqual(big[0], one[0])
        self.assertEqual(big[1], int(round(one[1] * 1.5)))

    def test_tiles_do_not_overlap_and_fit_the_width(self):
        _cols, _cell, rects, _h = look.grid(330, 4)
        for a, b in zip(rects, rects[1:]):
            self.assertLessEqual(a[0] + a[2], b[0])
        self.assertLessEqual(rects[-1][0] + rects[-1][2], 330)

    def test_nothing_to_draw(self):
        self.assertEqual(look.grid(330, 0), (0, 0, [], 0))


class Hit(unittest.TestCase):

    def test_the_tile_and_its_name_are_the_tile(self):
        _c, cell, rects, _h = look.grid(330, 4)
        x, y = rects[2][:2]
        self.assertEqual(look.hit(rects, x + 3, y + 3), 2)
        self.assertEqual(look.hit(rects, x + 3, y + cell + 5), 2)

    def test_the_gap_is_nothing(self):
        _c, _cell, rects, _h = look.grid(330, 4)
        self.assertIsNone(look.hit(rects, rects[0][0] + rects[0][2] + 2, 5))


class State(unittest.TestCase):

    def test_the_four_states(self):
        both, rig = ("rig", "skeleton"), ("rig",)
        self.assertEqual(look.state("Manny", "rig", "Manny", both), "selected")
        self.assertEqual(look.state("Orc_D", "skeleton", "Orc_D", rig), "selected_absent")
        self.assertEqual(look.state("Orc_D", "skeleton", "Manny", rig), "absent")
        self.assertEqual(look.state("Creep", "rig", "Manny", both), "available")


class Lines(unittest.TestCase):

    def test_the_place_caption_names_the_row_and_the_floor_point(self):
        self.assertEqual(look.place_caption("Manny [rig]", (120.4, 0.0, -35.6)),
                         "Manny [rig] \u00b7 floor (120, -36)")

    def test_an_absent_pair_is_refused_by_name(self):
        text = look.absent_text("Orc D", "skeleton")
        self.assertIn("Orc D has no skeleton", text)
        self.assertIn("Rig", text)
        self.assertIn("rig", look.absent_text("UE4 Mannequin", "rig"))

    def test_the_import_line(self):
        self.assertIn("Manny [rig]", look.import_text("Manny [rig]"))
        self.assertIn("drag", look.import_text("Manny [rig]"))

    def test_the_tag(self):
        self.assertEqual(look.tag_text("skeleton"), "no skeleton")


class Drag(unittest.TestCase):

    def test_a_drag_starts_past_the_distance(self):
        self.assertFalse(look.dragged((10, 10), (12, 11), 4))
        self.assertTrue(look.dragged((10, 10), (13, 11), 4))

    def test_over_the_hub(self):
        self.assertTrue(look.over_hub(["", "skeldarAnimHubRoot", "MayaWindow"]))
        self.assertTrue(look.over_hub(["skeldarAnimHub"]))
        self.assertFalse(look.over_hub(["modelPanel4", "MayaWindow"]))


class Boundary(unittest.TestCase):

    def test_no_maya_and_no_qt(self):
        with open(os.path.join(PLUGIN, "maya_charlook.py"), encoding="utf-8") as handle:
            source = handle.read()
        self.assertEqual(re.findall(r"^\s*(?:import|from)\s+(?:maya(?:\.|\s|$)|PySide)",
                                    source, re.MULTILINE), [])

    def test_the_payload_ships_it(self):
        import install
        for name in ("maya_charlook.py", "maya_chargrid.py"):
            self.assertIn(name, install.payload())
```

- [ ] **Step 2: Run** `mayapy -m unittest tests.test_charlook -v` → ModuleNotFoundError.

- [ ] **Step 3: Implement** `SkeldarAnim/maya_charlook.py`:

```python
"""The Characters card's portrait grid as data (2026-09-30).

The animator: «переделаем наше меню на сетку с портретами (как меню выбора
героев в Mortal Kombat или Dota 2)». Square head-and-shoulders portraits, one
per model, the kind a [Rig | Skeleton] switch. This module says how many
columns a width holds, where each tile is, what a point is and what the lines
say; `maya_chargrid` paints what it says. Stdlib only, like maya_hubstyle and
maya_invlook, so every decision is tested without Qt.

Sizes are LOGICAL px; `grid` multiplies by the display scale (trap 98: Qt
pixels are physical here).

Spec: docs/superpowers/specs/2026-09-30-character-portrait-grid-design.md
"""

import math

import maya_hubstyle

CELL_MIN = 72           # a portrait is at least this wide ...
CELL_MAX = 120          # ... and at most this
GAP = 6
NAME_H = 18             # the name strip under a portrait
RADIUS = 6              # a tile's corners: the hub's well radius
GHOST = 88              # the portrait riding the cursor
THROTTLE_MS = 33        # the drag's caption is re-read at most this often
DOT = "\u00b7"

PALETTE = maya_hubstyle.TOKENS
#  A release over any of these is a release back on the hub: nothing happens.
HUB_NAMES = (maya_hubstyle.ROOT, "skeldarAnimHub")


def grid(width, count, scale=1.0):
    """(columns, cell, rects, height) for `count` tiles in `width` physical
    px: as many columns of at least CELL_MIN as fit, never more than `count`,
    each tile a square of at most CELL_MAX, left-aligned, rows wrapping; the
    rects are the squares, the height includes the name strips. A width of 0
    (not laid out yet) is one row at the minimum. Pure."""
    if count <= 0:
        return (0, 0, [], 0)
    k = float(scale or 1.0)
    gap, low, high, name = GAP * k, CELL_MIN * k, CELL_MAX * k, NAME_H * k
    width = float(width or 0)
    if width <= 0:
        cols, cell = count, low
    else:
        cols = max(1, min(count, int((width + gap) // (low + gap))))
        cell = max(1.0, min(high, (width - gap * (cols - 1)) / cols))
    rows = int(math.ceil(count / float(cols)))
    rects = []
    for index in range(count):
        row, col = divmod(index, cols)
        rects.append((int(round(col * (cell + gap))),
                      int(round(row * (cell + name + gap))),
                      int(round(cell)), int(round(cell))))
    height = int(round(rows * (cell + name) + (rows - 1) * gap))
    return cols, int(round(cell)), rects, height


def name_rect(rect, scale=1.0):
    """The name strip under a portrait's square."""
    x, y, w, h = rect
    return (x, y + h, w, int(round(NAME_H * float(scale or 1.0))))


def tile_rect(rect, scale=1.0):
    """The square and its name strip: what a press on the tile covers."""
    x, y, w, h = rect
    return (x, y, w, h + int(round(NAME_H * float(scale or 1.0))))


def hit(rects, x, y, scale=1.0):
    """The index of the tile under (x, y), or None. Pure."""
    for index, rect in enumerate(rects):
        rx, ry, rw, rh = tile_rect(rect, scale)
        if rx <= x < rx + rw and ry <= y < ry + rh:
            return index
    return None


def state(model, kind, selected, kinds):
    """How a tile is drawn: "selected", "selected_absent" (picked, but the
    switch names a kind it lacks), "absent" (dimmed, not pickable) or
    "available". Pure."""
    present = kind in (kinds or ())
    if model == selected:
        return "selected" if present else "selected_absent"
    return "available" if present else "absent"


def place_caption(label, point):
    """What a release would do: «Manny [rig] · floor (120, -36)»."""
    return "{0} {1} floor ({2}, {3})".format(label, DOT, int(round(point[0])),
                                             int(round(point[2])))


def absent_text(model_label, kind):
    """The refusal when the picked model has no row of the chosen kind."""
    other = "Skeleton" if kind == "rig" else "Rig"
    return "{0} has no {1} - pick {2}, or another portrait".format(
        model_label, kind, other)


def import_text(label):
    return "{0} - press Add Character, or drag the portrait into a viewport".format(label)


def tag_text(kind):
    return "no " + kind


def dragged(start, now, threshold):
    """Whether a held press has travelled far enough to be a drag (Qt's own
    measure: the manhattan length)."""
    return abs(now[0] - start[0]) + abs(now[1] - start[1]) >= threshold


def over_hub(names):
    """Whether a point whose widget ancestry carries `names` (objectNames,
    innermost first) lies on the hub itself."""
    return any(name in HUB_NAMES for name in names or ())
```

And in `install._PAYLOAD`, after `"maya_inventory.py"`:

```python
    "maya_charlook.py",         # the Characters portrait grid's look (2026-09-30)
    "maya_chargrid.py",         # the Characters portrait grid
```

- [ ] **Step 4: Run** the new tests: all but the payload one pass until Task 5 creates `maya_chargrid.py` (the payload test is only about the name list, so it passes now too; `test_install` checks files exist — run it after Task 5).
- [ ] **Step 5: Commit** `feat(characters): the portrait grid as data - columns, tiles, lines`.

---

### Task 3: One drag ghost for the inventory and the grid

**Files:**
- Modify: `SkeldarAnim/maya_hubqt.py` (add `ghost_class()`)
- Modify: `SkeldarAnim/maya_inventory.py` (use it; delete its own `Ghost`)
- Test: `tests/test_hubqt.py` (append)

**Interfaces:**
- Produces: `maya_hubqt.ghost_class()` → class `Ghost(pixmap, icon_w, icon_h, k, anchor=(0.5, 0.25), name="skeldarDragGhost", backdrop=None)`, methods `set_caption(text, good)`, `follow(point)`; attributes `text`, `good`, `icon_w`, `icon_h`.

- [ ] **Step 1: Failing test** (append to `tests/test_hubqt.py`, which already has the offscreen QApplication pattern):

```python
@unittest.skipIf(QT is None, "no Qt")
class Ghost(unittest.TestCase):
    """2026-09-30: the inventory's drag ghost, shared with the Characters grid."""

    def setUp(self):
        self.app = QT.QtWidgets.QApplication.instance() or QT.QtWidgets.QApplication([])

    def test_the_caption_grows_the_ghost_and_the_cursor_sits_on_the_anchor(self):
        pix = QT.QtGui.QPixmap(40, 40)
        pix.fill(QT.QtCore.Qt.red)
        ghost = maya_hubqt.ghost_class()(pix, 40, 80, 1.0, anchor=(0.5, 0.5),
                                         name="skeldarTestGhost", backdrop="field")
        self.addCleanup(ghost.deleteLater)
        self.assertEqual(ghost.objectName(), "skeldarTestGhost")
        ghost.set_caption("a caption far wider than the icon is", True)
        self.assertGreater(ghost.width(), 40)
        ghost.follow(QT.QtCore.QPoint(500, 500))
        self.assertEqual(ghost.x() + ghost.width() // 2, 500)
        self.assertEqual(ghost.y() + 40, 500)
        image = QT.QtGui.QImage(ghost.size(), QT.QtGui.QImage.Format_ARGB32)
        image.fill(0)
        ghost.render(image)
        self.assertGreater(image.pixelColor(ghost.width() // 2, 20).alpha(), 0)
```

(If `tests/test_hubqt.py` names its Qt handle differently, use that name; it imports
`maya_hubqt` and builds a QApplication the same way.)

- [ ] **Step 2: Run** → AttributeError `ghost_class`.

- [ ] **Step 3: Implement** in `maya_hubqt.py`, after `_fill_class`:

```python
def ghost_class():
    """The drag ghost the hub's drags share: a pixmap riding the cursor with a
    caption pill under it naming what a release would do - the accent where
    it lands, danger where it does not. The inventory's since 2026-09-29, the
    Characters grid's too since 2026-09-30. `icon_w`/`icon_h` are physical px,
    `anchor` is where the cursor sits on the icon (0..1 of its width and
    height), `backdrop` a token painted rounded behind the icon, or None."""
    if "ghost" not in _CLASSES:
        q = qt()
        QtCore, QtGui, QtWidgets = q.QtCore, q.QtGui, q.QtWidgets
        Qt = QtCore.Qt

        def colour(name):
            return QtGui.QColor(hubstyle.TOKENS[name])

        def font(px):
            f = QtGui.QFont()
            f.setPixelSize(max(1, int(round(px))))
            return f

        class Ghost(QtWidgets.QWidget):

            def __init__(self, pixmap, icon_w, icon_h, k, anchor=(0.5, 0.25),
                         name="skeldarDragGhost", backdrop=None):
                QtWidgets.QWidget.__init__(
                    self, None, Qt.ToolTip | Qt.FramelessWindowHint
                    | Qt.WindowStaysOnTopHint)
                self.setObjectName(name)
                self.setAttribute(Qt.WA_TranslucentBackground)
                self.setAttribute(Qt.WA_TransparentForMouseEvents)
                self.setAttribute(Qt.WA_ShowWithoutActivating)
                self.pixmap, self.k = pixmap, float(k or 1.0)
                self.icon_w, self.icon_h = int(icon_w), int(icon_h)
                self.anchor, self.backdrop = anchor, backdrop
                self.text, self.good = "", True
                self._resize()

            def _caption_width(self):
                if not self.text:
                    return 0
                metrics = QtGui.QFontMetrics(font(12 * self.k))
                return metrics.horizontalAdvance(self.text) + int(16 * self.k)

            def _resize(self):
                width = max(self.icon_w, self._caption_width())
                self.resize(width, self.icon_h + int(26 * self.k))

            def set_caption(self, text, good):
                if (text, good) != (self.text, self.good):
                    self.text, self.good = text, good
                    self._resize()
                    self.update()

            def follow(self, point):
                left = (self.width() - self.icon_w) // 2
                self.move(point.x() - left - int(self.icon_w * self.anchor[0]),
                          point.y() - int(self.icon_h * self.anchor[1]))

            def paintEvent(self, _event):                    # noqa: N802
                p = QtGui.QPainter(self)
                p.setRenderHint(QtGui.QPainter.Antialiasing)
                p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
                box = QtCore.QRect((self.width() - self.icon_w) // 2, 0,
                                   self.icon_w, self.icon_h)
                radius = 6 * self.k
                p.setOpacity(0.85)
                if self.backdrop:
                    p.setPen(Qt.NoPen)
                    p.setBrush(colour(self.backdrop))
                    p.drawRoundedRect(QtCore.QRectF(box), radius, radius)
                inner = box.adjusted(int(2 * self.k), int(2 * self.k),
                                     -int(2 * self.k), -int(2 * self.k))
                if not self.pixmap.isNull() and inner.width() > 0:
                    size = self.pixmap.size().scaled(inner.size(), Qt.KeepAspectRatio)
                    target = QtCore.QRect(
                        inner.x() + (inner.width() - size.width()) // 2,
                        inner.y() + (inner.height() - size.height()) // 2,
                        size.width(), size.height())
                    p.drawPixmap(target, self.pixmap)
                p.setOpacity(1.0)
                if self.text:
                    cw = self._caption_width()
                    cap = QtCore.QRectF((self.width() - cw) // 2,
                                        self.icon_h + int(3 * self.k), cw,
                                        int(21 * self.k))
                    edge = max(1.0, self.k)
                    shape = cap.adjusted(edge / 2, edge / 2, -edge / 2, -edge / 2)
                    p.setPen(QtGui.QPen(colour("accent" if self.good else "danger"), edge))
                    p.setBrush(colour("card"))
                    p.drawRoundedRect(shape, radius, radius)
                    p.setFont(font(12 * self.k))
                    p.setPen(colour("text" if self.good else "muted"))
                    p.drawText(cap, Qt.AlignCenter, self.text)
                p.end()

        _CLASSES["ghost"] = Ghost
    return _CLASSES["ghost"]
```

In `maya_inventory.py`: delete `class Ghost` (and its now-unused `fitted`-only helpers
stay — `fitted` is still used by the window's paint); `_start` builds:

```python
            ghost = maya_hubqt.ghost_class()(
                pixmap, int(cells[0] * look.CELL * self.k),
                int(cells[1] * look.CELL * self.k), self.k,
                anchor=(0.5, 0.25), name=GHOST_NAME)
```

(`cells = self.cells.get(key, (1, 3))`; the module already imports `maya_hubqt` inside
`_classes`, so reference the one bound there), and `_CLASSES.update(Ghost=maya_hubqt.ghost_class(), ...)`.

- [ ] **Step 4: Run** `tests.test_hubqt tests.test_inventory` offscreen → all pass.
- [ ] **Step 5: Commit** `refactor(hub): one drag ghost for the inventory and what comes next`.

---

### Task 4: The floor point and the placed Add

**Files:**
- Modify: `SkeldarAnim/maya_scenesetup/droptarget.py` (`floor_at`, `NO_VIEWPORT`, `NO_FLOOR`)
- Modify: `SkeldarAnim/maya_scenesetup/character.py` (`placement`, `place`, `add_character(at=)`, one chunk, `added_message(placed=)`)
- Test: `tests/test_scenesetup_droptarget.py`, `tests/test_scenesetup_character.py` (append)

**Interfaces:**
- Produces:
  - `droptarget.floor_at(gx, gy) -> dict(kind="floor", point=(x, y, z)) | dict(kind="none", text=...)`;
  - `character.placement(at) -> (x, 0.0, z)`;
  - `character.place(entry, namespace, root, at) -> node|None`;
  - `character.add_character(entry=None, rgb=None, at=None) -> str`.

- [ ] **Step 1: Failing tests.** In `tests/test_scenesetup_droptarget.py`:

```python
class FloorAt(unittest.TestCase):
    """2026-09-30, a character dragged into the scene: the floor under the
    cursor, or why not."""

    class View(object):
        def __init__(self, near, far):
            self.near, self.far = near, far

        def to_port(self, local):
            return local

        def ray(self, port):
            return self.near, self.far

    def setUp(self):
        self.saved = dt.Viewport.at

    def tearDown(self):
        dt.Viewport.at = self.saved

    def test_the_ray_meets_the_floor(self):
        view = self.View((0.0, 100.0, 50.0), (10.0, 0.0, 40.0))
        dt.Viewport.at = classmethod(lambda cls, gx, gy: (view, (5, 5)))
        self.assertEqual(dt.floor_at(1, 2), dict(kind="floor", point=(10.0, 0.0, 40.0)))

    def test_off_every_viewport(self):
        dt.Viewport.at = classmethod(lambda cls, gx, gy: (None, None))
        self.assertEqual(dt.floor_at(1, 2), dict(kind="none", text=dt.NO_VIEWPORT))

    def test_looking_up_is_no_floor(self):
        view = self.View((0.0, 100.0, 50.0), (0.0, 200.0, 40.0))
        dt.Viewport.at = classmethod(lambda cls, gx, gy: (view, (5, 5)))
        self.assertEqual(dt.floor_at(1, 2), dict(kind="none", text=dt.NO_FLOOR))
```

In `tests/test_scenesetup_character.py`:

```python
class Placed(unittest.TestCase):
    """2026-09-30: a portrait dropped on the floor - the rig's Main, or the
    skeleton's root, moved by (x, 0, z) in world space; one undo chunk."""

    class Cmds(object):
        def __init__(self):
            self.log = []

        def undoInfo(self, **kwargs):
            self.log.append(("undo", "open" if kwargs.get("openChunk") else "close"))

        def ls(self, *args, **kwargs):
            if args and args[0] == "Manny_Rig:Main":
                return ["|Manny_Rig:Group|Manny_Rig:Main"]
            return []

        def objExists(self, name):
            return False

        def delete(self, *args):
            pass

        def move(self, *args, **kwargs):
            self.log.append(("move", args, kwargs))

    def setUp(self):
        import tempfile
        from maya_overrig import builder
        from maya_scenesetup import colour
        handle, self.file = tempfile.mkstemp(suffix=".ma")
        os.close(handle)
        self.cmds = self.Cmds()
        self.roots = [[], ["|Armature|root"]]
        self.saved = [(character, "cmds", character.cmds),
                      (character, "import_asset", character.import_asset),
                      (character, "connect", character.connect),
                      (character, "select_rig", character.select_rig),
                      (character, "existing_namespaces", character.existing_namespaces),
                      (catalog, "character_file", catalog.character_file),
                      (builder, "character_roots", builder.character_roots),
                      (colour, "paint_nodes", colour.paint_nodes)]
        character.cmds = self.cmds
        character.import_asset = lambda path, namespace=None: []
        character.connect = lambda root: False
        character.select_rig = lambda namespace: True
        character.existing_namespaces = lambda: []
        catalog.character_file = lambda entry: self.file
        builder.character_roots = lambda: self.roots.pop(0)
        colour.paint_nodes = lambda *a: "phong1"

    def tearDown(self):
        for owner, name, value in self.saved:
            setattr(owner, name, value)
        os.remove(self.file)

    def moves(self):
        return [e for e in self.cmds.log if e[0] == "move"]

    def test_the_placement_keeps_the_files_height(self):
        self.assertEqual(character.placement((120.0, 3.0, -35.0)), (120.0, 0.0, -35.0))

    def test_a_rig_moves_its_main(self):
        text = character.add_character(catalog.character_by_key("Manny_Rig"),
                                       (0.8, 0.25, 0.22), at=(120.0, 0.0, -35.0))
        self.assertEqual(self.moves(), [("move", (120.0, 0.0, -35.0,
                                                  "|Manny_Rig:Group|Manny_Rig:Main"),
                                         {"relative": True, "worldSpace": True})])
        self.assertIn(" - at (120, -35)", text)

    def test_a_skeleton_moves_its_root_never_the_armature(self):
        character.add_character(catalog.character_by_key("Creep"), (0.8, 0.25, 0.22),
                                at=(10.0, 0.0, 20.0))
        self.assertEqual(self.moves()[0][1][3], "|Armature|root")

    def test_no_point_moves_nothing(self):
        text = character.add_character(catalog.character_by_key("Manny_Rig"), (0.8, 0.25, 0.22))
        self.assertEqual(self.moves(), [])
        self.assertNotIn(" - at (", text)

    def test_one_undo_chunk_around_the_whole_press(self):
        character.add_character(catalog.character_by_key("Manny_Rig"), (0.8, 0.25, 0.22),
                                at=(1.0, 0.0, 2.0))
        chunks = [e[1] for e in self.cmds.log if e[0] == "undo"]
        self.assertEqual(chunks, ["open", "close"])
        self.assertEqual(self.cmds.log[0], ("undo", "open"))
        self.assertEqual(self.cmds.log[-1], ("undo", "close"))
```

- [ ] **Step 2: Run** → failures on `floor_at`, `placement`, `at=`.

- [ ] **Step 3: Implement.** `droptarget.py` — constants after `SIDE_LABEL`, reused by `target()`:

```python
NO_VIEWPORT = "no target - drop onto a viewport"
NO_FLOOR = "no floor under the cursor"
```

`target()` uses them in place of the two literals; and after `target()`:

```python
def floor_at(gx, gy):
    """The floor (Y = 0) under a global cursor position, in front of the
    camera: dict(kind="floor", point) or dict(kind="none", text). What a
    character dragged out of the Characters grid lands on (2026-09-30)."""
    view, local = Viewport.at(gx, gy)
    if view is None:
        return dict(kind="none", text=NO_VIEWPORT)
    near, far = view.ray(view.to_port(local))
    hit = floor_hit(near, far)
    if hit is None:
        return dict(kind="none", text=NO_FLOOR)
    return dict(kind="floor", point=hit)
```

`character.py`: `added_message(..., placed=None)` appends `" - at ({0}, {1})".format(int(round(placed[0])), int(round(placed[2])))` after the colour and before the note; new functions before `add_character`:

```python
def placement(at):
    """The world offset a drop at floor point `at` asks for: (x, 0, z). The
    move is relative, so the feet keep the height the file gives them. Pure."""
    return (float(at[0]), 0.0, float(at[2]))


def place(entry, namespace, root, at):
    """Stand the new character at floor point `at` (2026-09-30, a portrait
    dragged into the scene): a rig's `Main` -- the whole rig's control, root
    motion; the skeleton's root rides it -- else the skeleton's `root`, moved
    by `placement(at)` in world space. Never a Null above the root: the Creep
    skeleton's `Armature` must stay at the origin or the export no longer
    reads Cascadeur's layout. No rotation: a character faces +Z as its file
    does. The node moved, or None."""
    if at is None:
        return None
    node = None
    if catalog.is_rig(entry):
        import maya_rigs
        found = cmds.ls(maya_rigs.node(namespace, maya_rigs.MAIN), long=True) or []
        node = found[0] if len(found) == 1 else None
    else:
        node = root
    if not node:
        return None
    x, y, z = placement(at)
    cmds.move(x, y, z, node, relative=True, worldSpace=True)
    return node
```

`add_character(entry=None, rgb=None, at=None)`: after the missing-file refusal, open
`cmds.undoInfo(openChunk=True, chunkName="Add Character")`, run everything that follows
inside `try:` / `finally: cmds.undoInfo(closeChunk=True)`; the inner paint chunk goes (the
outer one covers it). After `root = new_root(...)` and the note:
`placed = at if place(entry, namespace, root, at) else None`, then `connect`, `select_rig`,
and `added_message(..., placed=placed)`. The docstring gains: "`at` is a floor point
(2026-09-30, a portrait dropped into a viewport): the character stands there. The whole
press is one undo chunk: one Ctrl+Z takes the character out."

- [ ] **Step 4: Run** the droptarget and character tests → pass.
- [ ] **Step 5: Commit** `feat(characters): add a character at a floor point - Main or root moved, one undo`.

---

### Task 5: The portrait grid widget — `maya_chargrid`

**Files:**
- Create: `SkeldarAnim/maya_chargrid.py`
- Test: `tests/test_chargrid.py`

**Interfaces:**
- Consumes: `maya_charlook` (Task 2), `maya_hubqt.ghost_class()` (Task 3), `catalog.MODELS/kinds_of/character_for/portrait_path/model_by_key` (Task 1), `droptarget.floor_at` (Task 4), `window.select_model(model)`, `window.place_character(model, kind, point) -> str`, `window.say_character(text)` (Task 6).
- Produces: `maya_chargrid.OBJECT_NAME = "skeldarCharacterGrid"`, `GHOST_NAME = "skeldarCharacterGhost"`, `Scene`, `make_grid(scene, parent=None, kind="rig", selected=None)`, `attach(placeholder, scene=None, kind="rig", selected=None) -> grid|None`, `live(placeholder) -> grid|None`. Grid: `set_kind(kind)`, `set_selected(model)`, `select(model) -> bool`, `height_for(width) -> int`, `model_at(x, y)`, `drop_at(gx, gy, model=None) -> str`, `status_text`.

- [ ] **Step 1: Failing tests** — `tests/test_chargrid.py`:

```python
"""The Characters card's portrait grid, offscreen (2026-09-30): it paints the
portraits, a click selects, the switch dims, a drag outside the widget drops a
character on the floor - on a fake scene, so no Maya scene is touched. The
viewport half is verify_character_grid.py's.

Spec: docs/superpowers/specs/2026-09-30-character-portrait-grid-design.md
"""
import re
import unittest

try:
    import maya_hubqt
    QT = maya_hubqt.qt()
except Exception:                                            # noqa: BLE001
    QT = None

import maya_chargrid as cg
import maya_charlook as look


class FakeScene(object):

    def __init__(self):
        self.log = []
        self.aim = dict(kind="floor", point=(120.0, 0.0, -35.0))

    def scale(self):
        return 1.0

    def target(self, gx, gy):
        self.log.append(("target", gx, gy))
        return self.aim

    def over_hub(self, gx, gy):
        return False

    def select(self, model):
        self.log.append(("select", model))

    def place(self, model, kind, point):
        self.log.append(("place", model, kind, point))
        return "placed"

    def say(self, text):
        self.log.append(("say", text))


@unittest.skipIf(QT is None, "no Qt")
class Grid(unittest.TestCase):

    def setUp(self):
        self.app = QT.QtWidgets.QApplication.instance() or QT.QtWidgets.QApplication([])
        self.scene = FakeScene()
        self.grid = cg.make_grid(self.scene, kind="rig", selected="Manny")
        self.grid.resize(330, self.grid.height_for(330))
        self.grid.move(3000, 3000)
        self.addCleanup(self.grid.deleteLater)

    def centre(self, index):
        x, y, w, h = self.grid.rects()[index]
        return QT.QtCore.QPoint(x + w // 2, y + h // 2)

    def acts(self, name):
        return [e for e in self.scene.log if e[0] == name]

    def test_it_paints_ink(self):
        image = QT.QtGui.QImage(self.grid.size(), QT.QtGui.QImage.Format_ARGB32)
        image.fill(0)
        self.grid.render(image)
        inked = sum(1 for x in range(0, image.width(), 4)
                    for y in range(0, image.height(), 4)
                    if image.pixelColor(x, y).alpha() > 0)
        self.assertGreater(inked, 200)

    def test_four_tiles_one_row_in_the_dock(self):
        self.assertEqual(len(self.grid.rects()), 4)
        self.assertEqual(self.grid.height_for(330), look.grid(330, 4)[3])

    def test_a_click_selects_and_calls_back(self):
        p = self.centre(1)
        self.grid.model_at(p.x(), p.y())
        self.assertTrue(self.grid.select("Creep"))
        self.assertEqual(self.grid.selected, "Creep")
        self.assertEqual(self.acts("select"), [("select", "Creep")])

    def test_a_dimmed_tile_is_not_selected(self):
        self.assertFalse(self.grid.select("UE4_Mannequin"))
        self.assertEqual(self.grid.selected, "Manny")
        self.assertEqual(self.acts("select"), [])

    def test_the_switch_dims_the_other_model(self):
        self.grid.set_kind("skeleton")
        self.assertTrue(self.grid.available("UE4_Mannequin"))
        self.assertFalse(self.grid.available("Orc_D"))
        self.grid.set_selected("Orc_D")
        self.assertEqual(self.grid.selected, "Orc_D")

    def test_the_model_under_a_point(self):
        p = self.centre(2)
        self.assertEqual(self.grid.model_at(p.x(), p.y()), "Orc_D")
        self.assertIsNone(self.grid.model_at(-5, -5))

    def test_a_drop_on_the_floor_places_the_chosen_kind(self):
        self.grid.drop_at(500, 500, "Creep")
        self.assertEqual(self.acts("place"), [("place", "Creep", "rig", (120.0, 0.0, -35.0))])
        self.assertEqual(self.grid.status_text, "placed")

    def test_no_floor_places_nothing_and_says_why(self):
        self.scene.aim = dict(kind="none", text="no floor under the cursor")
        self.grid.drop_at(500, 500, "Creep")
        self.assertEqual(self.acts("place"), [])
        self.assertIn(("say", "no floor under the cursor"), self.scene.log)

    def test_a_drop_back_on_the_hub_does_nothing(self):
        self.scene.over_hub = lambda gx, gy: True
        self.grid.drop_at(500, 500, "Creep")
        self.assertEqual(self.acts("place"), [])
        self.assertEqual(self.acts("target"), [])

    def test_a_drop_that_raises_says_so(self):
        def boom(*a):
            raise RuntimeError("the scene said no")
        self.scene.place = boom
        self.grid.drop_at(500, 500, "Creep")
        self.assertIn("the scene said no", self.grid.status_text)

    def _mouse(self, kind, local, button, buttons):
        g = self.grid.mapToGlobal(local)
        event = QT.QtGui.QMouseEvent(kind, QT.QtCore.QPointF(local), QT.QtCore.QPointF(g),
                                     button, buttons, QT.QtCore.Qt.NoModifier)
        QT.QtWidgets.QApplication.sendEvent(self.grid, event)

    def test_press_drag_release_outside_drops_the_pressed_portrait(self):
        E, L, N = QT.QtCore.QEvent, QT.QtCore.Qt.LeftButton, QT.QtCore.Qt.NoButton
        start = self.centre(1)
        far = start + QT.QtCore.QPoint(-900, 400)
        self._mouse(E.MouseButtonPress, start, L, L)
        self.assertEqual(self.grid.selected, "Creep")
        self._mouse(E.MouseMove, start + QT.QtCore.QPoint(30, 0), N, L)
        self.assertIsNotNone(self.grid._drag)
        self._mouse(E.MouseMove, far, N, L)
        self._mouse(E.MouseButtonRelease, far, L, N)
        self.assertIsNone(self.grid._drag)
        self.assertEqual(self.acts("place"), [("place", "Creep", "rig", (120.0, 0.0, -35.0))])

    def test_a_click_without_travel_is_no_drag(self):
        E, L, N = QT.QtCore.QEvent, QT.QtCore.Qt.LeftButton, QT.QtCore.Qt.NoButton
        start = self.centre(2)
        self._mouse(E.MouseButtonPress, start, L, L)
        self._mouse(E.MouseButtonRelease, start, L, N)
        self.assertEqual(self.acts("place"), [])
        self.assertEqual(self.grid.selected, "Orc_D")

    def test_escape_cancels_a_drag(self):
        E, L, N = QT.QtCore.QEvent, QT.QtCore.Qt.LeftButton, QT.QtCore.Qt.NoButton
        start = self.centre(0)
        self._mouse(E.MouseButtonPress, start, L, L)
        self._mouse(E.MouseMove, start + QT.QtCore.QPoint(40, 0), N, L)
        key = QT.QtGui.QKeyEvent(E.KeyPress, QT.QtCore.Qt.Key_Escape, QT.QtCore.Qt.NoModifier)
        QT.QtWidgets.QApplication.sendEvent(self.grid, key)
        self.assertIsNone(self.grid._drag)
        self._mouse(E.MouseButtonRelease, start + QT.QtCore.QPoint(900, 0), L, N)
        self.assertEqual(self.acts("place"), [])

    def test_the_ghost_is_the_shared_one(self):
        self.assertIs(cg._classes()["Ghost"], maya_hubqt.ghost_class())


class Skin(unittest.TestCase):

    def _source(self):
        with open(cg.__file__, encoding="utf-8") as handle:
            return handle.read()

    def test_no_colour_of_its_own(self):
        self.assertEqual(re.findall(r"#[0-9a-fA-F]{6}\b", self._source()), [])

    def test_every_colour_it_names_is_a_hub_token(self):
        import maya_hubstyle
        names = set(re.findall(r'colour\("([a-z_]+)"', self._source()))
        self.assertTrue(names)
        self.assertEqual(sorted(names - set(maya_hubstyle.TOKENS)), [])
```

- [ ] **Step 2: Run** (offscreen) → ModuleNotFoundError.

- [ ] **Step 3: Implement** `SkeldarAnim/maya_chargrid.py` — the full module is in the
implementation (committed with this task). Its shape:
  - `Scene`: `scale()` (mayaDpiSetting realScaleValue), `target(gx, gy)` →
    `droptarget.floor_at`, `over_hub(gx, gy)` → `look.over_hub` over the objectName chain
    of `QApplication.widgetAt`, `select(model)` → `window.select_model`, `place(...)` →
    `window.place_character`, `say(text)` → `window.say_character`;
  - `_classes()` builds `PortraitGrid` and a `Keeper` event filter (the Fill pattern
    plus `setFixedHeight(grid.height_for(host.width()))`), stores
    `Ghost = maya_hubqt.ghost_class()`;
  - `PortraitGrid`:
    - the portraits as QPixmaps from `catalog.portrait_path`;
    - `rects()` = `look.grid(self.width(), 4, k)[2]`;
    - paint: tiles in `field`, the portrait clipped to the rounded square, `card_active`
      plus a 2k `accent` outline when selected, a dashed `accent` outline when
      selected_absent, a `line` outline on hover, opacity 0.28 with a `status`/`faint`
      "no <kind>" pill when absent, the name elided under it in `text` / `text2` / `faint`,
      the hub's `user` icon when a portrait file is missing;
    - mouse: a press selects and records the press point; a move past
      `QApplication.startDragDistance()` (`look.dragged`) starts the drag (ghost `GHOST`×k
      square, anchor (0.5, 0.5), backdrop `field`, `grabKeyboard`); the caption is
      throttled to `THROTTLE_MS`; a release ends in `drop_at`; the right button or Esc
      cancels;
    - `drop_at(gx, gy, model)`: inside the widget or `scene.over_hub` → nothing; else
      `scene.target` → floor → `_act(scene.place(model, self.kind, point))` / none →
      `_say(text)`;
    - `_act` catches, prints the traceback and says the last line;
  - `attach` finds the placeholder by `maya_hubqt.find(name, layout=True)`, parents the
    grid to it, installs the `Keeper`, remembers it in `_GRIDS[name]`; `live(name)` answers
    it while `shiboken.isValid`.

- [ ] **Step 4: Run** `tests.test_chargrid tests.test_charlook` offscreen → pass.
- [ ] **Step 5: Commit** `feat(characters): the portrait grid - paint, select, drag into the scene`.

---

### Task 6: The Characters card rebuilt

**Files:**
- Modify: `SkeldarAnim/maya_scenesetup/window.py`
- Test: `tests/test_hub_sections.py`, `tests/test_scenesetup_window.py`

**Interfaces:**
- Consumes:
  - `maya_chargrid.attach/live` (Task 5);
  - `maya_charlook.absent_text/import_text` (Task 2);
  - `catalog.character_for/model_by_key/KINDS` (Task 1);
  - `character.add_character(entry, at=)` (Task 4).
- Produces:
  - `window._PORTRAITS = "mayaSceneSetupPortraits"`, `window._KIND = "mayaSceneSetupCharacterKind"`, `kind_segment(kind)`;
  - `_MODEL_OPTIONVAR = "mayaSceneSetup_characterModel"`, `_KIND_OPTIONVAR = "mayaSceneSetup_characterKind"`;
  - `choice_from(model, kind, label) -> (model, kind)` (pure), `remembered_choice()`;
  - `select_model(model)`, `kind_changed(kind) -> callback`, `say_character(text)`, `place_character(model, kind, point) -> str`, `chosen_character() -> Character|None`.
- Removes: `_CHARACTER_COLOUR`, `_CHARACTER_DOT`, `recolour_character`.

- [ ] **Step 1: Failing tests.** In `tests/test_hub_sections.py`'s `SceneSetup`:
  - `setUp` also saves/replaces `scenesetup._attach_grid` with `lambda model, kind: True`;
  - `test_characters_holds_the_character_controls_and_its_own_line` checks
    `_BOUND, _PORTRAITS, _CHARACTER_STATUS` among `after_characters` and `_CHARACTER`
    (the dropdown) NOT among them;
  - `test_the_character_dropdown_needs_no_label` → `test_the_dropdown_stands_only_without_the_grid`
    (rebuild with `_attach_grid` returning False: an `optionMenu` named `_CHARACTER`
    exists, with no label);
  - new `test_the_kind_switch_is_two_segments` (the collection `_KIND`, segments
    `kind_segment("rig")`/`kind_segment("skeleton")` labelled Rig/Skeleton, marked
    `segment`, their row `segments`);
  - `test_eight_palette_dots_per_colour_row` loops over `_WEAPON_DOT` only and asserts no
    `mayaSceneSetupCharDot` control was created;
  - `test_the_swatches_show_only_the_swatch_in_the_skin` checks `_WEAPON_COLOUR` only;
  - `test_recolour_is_a_brush_tool_on_both` → exactly ONE brush (the weapons');
  - new `test_no_colour_control_in_characters`: no `colorSliderGrp`, no brush and no
    swatch mark among the calls before the weapons build.

  In `tests/test_scenesetup_window.py`:
  - `AimRefusals.test_the_overrig_era_callbacks_are_gone` drops `recolour_character`
    from the callable list and asserts `not hasattr(window, "recolour_character")`;
  - `ColourSwatches.test_both_recolour_buttons_exist` → only `recolour_weapon`;
    `test_the_two_swatches_are_different_controls` → `assertFalse(hasattr(window, "_CHARACTER_COLOUR"))`;
  - `NextAddColour.test_advancing_writes_the_next_free_colour` uses `_WEAPON_COLOUR`;
  - `TexturedAddKeepsTheSwatch` is replaced by:

```python
class AddCharacterPress(unittest.TestCase):
    """2026-09-30: the colour left the Characters card - Add passes none (the
    next free colour), and a model without the chosen kind is refused by name."""

    def setUp(self):
        self.saved = [(window, n, getattr(window, n)) for n in
                      ("chosen_character", "remembered_choice", "refresh", "_status")]
        self.saved.append((window.character, "add_character", window.character.add_character))
        self.lines, self.added = [], []
        window.refresh = lambda: None
        window._status = lambda message, control=None: self.lines.append(message)
        window.character.add_character = lambda entry, rgb=None, at=None: (
            self.added.append((entry.key, rgb, at)) or "added")

    def tearDown(self):
        for owner, name, value in self.saved:
            setattr(owner, name, value)

    def test_add_passes_no_colour(self):
        window.chosen_character = lambda: catalog.character_by_key("Creep_Rig")
        window.add_character()
        self.assertEqual(self.added, [("Creep_Rig", None, None)])
        self.assertEqual(self.lines[-1], "added")

    def test_an_absent_pair_is_refused(self):
        window.chosen_character = lambda: None
        window.remembered_choice = lambda: ("Orc_D", "skeleton")
        window.add_character()
        self.assertEqual(self.added, [])
        self.assertIn("Orc D has no skeleton", self.lines[-1])

    def test_a_drop_places_at_the_point(self):
        text = window.place_character("Manny", "rig", (1.0, 0.0, 2.0))
        self.assertEqual(self.added, [("Manny_Rig", None, (1.0, 0.0, 2.0))])
        self.assertEqual(text, "added")

    def test_a_drop_of_an_absent_pair_places_nothing(self):
        text = window.place_character("UE4_Mannequin", "rig", (1.0, 0.0, 2.0))
        self.assertEqual(self.added, [])
        self.assertIn("UE4 Mannequin has no rig", text)


class Choice(unittest.TestCase):
    """What the card opens on: the two optionVars, else the old dropdown's
    label, else the default rig."""

    def test_the_two_optionvars_win(self):
        self.assertEqual(window.choice_from("Creep", "skeleton", "Manny [rig]"),
                         ("Creep", "skeleton"))

    def test_the_old_label_is_the_fallback(self):
        self.assertEqual(window.choice_from("", "", "UE4 Mannequin [skeleton]"),
                         ("UE4_Mannequin", "skeleton"))

    def test_nothing_is_the_default_rig(self):
        self.assertEqual(window.choice_from(None, None, ""), ("Manny", "rig"))

    def test_a_stale_model_falls_back(self):
        self.assertEqual(window.choice_from("Sevarog", "rig", ""), ("Manny", "rig"))

    def test_chosen_character_reads_the_choice_without_the_dropdown(self):
        fake = FakeUiCmds(menu_exists=False, stored={
            window._MODEL_OPTIONVAR: "Orc_D", window._KIND_OPTIONVAR: "skeleton"})
        real, window.cmds = window.cmds, fake
        try:
            self.assertIsNone(window.chosen_character())
            fake.stored[window._KIND_OPTIONVAR] = "rig"
            self.assertEqual(window.chosen_character().key, "Orc_D_Rig")
        finally:
            window.cmds = real
```

  `CharacterDropdown.test_no_menu_yet_falls_back_to_the_default` keeps passing (no
  optionVars → the default rig).

- [ ] **Step 2: Run** → failures.

- [ ] **Step 3: Implement** in `window.py`:
  - drop `_CHARACTER_COLOUR`, `_CHARACTER_DOT`, `recolour_character`;
  - `add_character` becomes:

```python
def add_character():
    """Import the chosen character at the origin, then catch the UI up.

    The colour is not this card's since 2026-09-30 («все что касается
    покраски вынесем из меню, будем красить в меню с красками»): a character
    arrives in the next free palette colour (`rgb=None`), and the Colour
    section repaints the selection - Add leaves the new rig's Main selected.
    A model without a row of the chosen kind is refused by name."""
    entry = chosen_character()
    if entry is None:
        say_character(_absent())
        return
    message = character.add_character(entry)
    refresh()
    say_character(message)
```

  plus the new pieces:

```python
_PORTRAITS = "mayaSceneSetupPortraits"   # where the portrait grid is laid over
_KIND = "mayaSceneSetupCharacterKind"    # the [Rig | Skeleton] segments
_MODEL_OPTIONVAR = "mayaSceneSetup_characterModel"
_KIND_OPTIONVAR = "mayaSceneSetup_characterKind"
KIND_LABEL = {"rig": "Rig", "skeleton": "Skeleton"}


def kind_segment(kind):
    return "{0}_{1}".format(_KIND, kind)


def choice_from(model, kind, label):
    """(model, kind) the card opens on: the stored pair, else the row the old
    dropdown remembered (its label), else the default rig. Pure."""
    fallback = catalog.character_by_label(label or "") or catalog.default_rig()
    if catalog.model_by_key(model or "") is None:
        model = fallback.model
    if kind not in catalog.KINDS:
        kind = fallback.kind
    return model, kind


def _stored(name):
    if cmds.optionVar(exists=name):
        return cmds.optionVar(query=name) or ""
    return ""


def remembered_choice():
    return choice_from(_stored(_MODEL_OPTIONVAR), _stored(_KIND_OPTIONVAR),
                       remembered_character())


def chosen_character():
    """The catalog row Add Character imports. From the old dropdown where it
    stands (no Qt: the grid could not be built), else the chosen model in
    the chosen kind - None when that model has no such row (Orc D has no
    skeleton)."""
    if cmds.optionMenu(_CHARACTER, exists=True):
        label = cmds.optionMenu(_CHARACTER, query=True, value=True) or ""
        return catalog.character_by_label(label) or catalog.default_rig()
    model, kind = remembered_choice()
    return catalog.character_for(model, kind)


def _absent():
    model, kind = remembered_choice()
    return charlook.absent_text(catalog.model_by_key(model).label, kind)


def say_character(text):
    _status(text, _CHARACTER_STATUS)


def _say_choice():
    entry = chosen_character()
    say_character(charlook.import_text(entry.label) if entry else _absent())


def select_model(model):
    """A portrait clicked: remember it, say what Add will import."""
    cmds.optionVar(stringValue=(_MODEL_OPTIONVAR, model))
    _say_choice()


def _grid():
    try:
        import maya_chargrid
        return maya_chargrid.live(_PORTRAITS)
    except Exception:                                        # noqa: BLE001
        return None


def kind_changed(kind):
    """A Rig / Skeleton segment's onCommand: remember it, dim the grid."""
    def go(*_args):
        cmds.optionVar(stringValue=(_KIND_OPTIONVAR, kind))
        grid = _grid()
        if grid is not None:
            grid.set_kind(kind)
        _run(_say_choice, _CHARACTER_STATUS)
    return go


def place_character(model, kind, point):
    """A portrait dropped on the floor (2026-09-30): the character added
    standing at `point`. Returns what the line says - the grid shows it."""
    entry = catalog.character_for(model, kind)
    if entry is None:
        text = charlook.absent_text(catalog.model_by_key(model).label, kind)
        say_character(text)
        return text
    message = character.add_character(entry, at=point)
    try:
        refresh()
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()
    say_character(message)
    return message
```

  the builder:

```python
def _kind_row(kind):
    """`[Rig | Skeleton]`: which kind a portrait brings (2026-09-30)."""
    segments = cmds.rowLayout(numberOfColumns=2,
                              columnAttach=[(1, "both", 1), (2, "both", 1)])
    hubstyle.mark(segments, "segments", layout=True)
    cmds.iconTextRadioCollection(_KIND)
    for each in catalog.KINDS:
        hubstyle.mark(cmds.iconTextRadioButton(
            kind_segment(each), style="textOnly", label=KIND_LABEL[each],
            height=22, select=each == kind,
            annotation="The portraits bring the {0}".format(
                "AdvancedSkeleton rig - what the UE Bridge retargets onto"
                if each == "rig" else "bare skeleton"),
            onCommand=kind_changed(each)), "segment")
    cmds.setParent("..")


def _attach_grid(model, kind):
    """The portrait grid laid over the placeholder; False where it cannot
    stand (no Qt) - the card then shows the old dropdown."""
    try:
        import maya_chargrid
        return maya_chargrid.attach(_PORTRAITS, kind=kind, selected=model) is not None
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()
        return False


def _character_dropdown():
    cmds.optionMenu(_CHARACTER,
                    annotation="What Add Character puts into the scene.",
                    changeCommand=lambda *_args: _run(character_changed,
                                                      _CHARACTER_STATUS))
    for label in catalog.character_labels():
        cmds.menuItem(label=label)
    remembered = remembered_character()
    if remembered and remembered in catalog.character_labels():
        cmds.optionMenu(_CHARACTER, edit=True, value=remembered)


def build_characters_panel():
    """The Characters section: a [Rig | Skeleton] switch, the portraits, Add
    Character, Camera Setup, the line (2026-09-30, «сетка с портретами»).
    No colour here: the Colour section paints."""
    column = cmds.columnLayout(adjustableColumn=True, rowSpacing=6,
                               columnOffset=("both", hubstyle.pick(0, 8)))
    hubstyle.mark(cmds.text(_BOUND, label="", align="left"), "subtitle")
    model, kind = remembered_choice()
    _kind_row(kind)
    cmds.columnLayout(_PORTRAITS, adjustableColumn=True)
    cmds.setParent("..")
    if not _attach_grid(model, kind):
        _character_dropdown()
    ... Add Character (primary, plus) and Camera Setup (secondary, camera) as before,
    the status text as before ...
    cmds.setParent("..")
    _run(_bound_root, _CHARACTER_STATUS)
    _run(_say_choice, _CHARACTER_STATUS)
    return column
```

  `import maya_charlook as charlook` at the module top (stdlib).

- [ ] **Step 4: Run** the window and hub-section tests → pass; then the whole suite.
- [ ] **Step 5: Commit** `feat(characters): the card is the portrait grid - no colour, a Rig/Skeleton switch`.

---

### Task 7: The portraits

**Files:**
- Create: `docs/superpowers/plans/make_character_portraits.py`
- Create: `SkeldarAnim/assets/character_portraits/{Manny,Creep,Orc_D,UE4_Mannequin}.png`
- Test: `tests/test_scenesetup_catalog.py` (append)

- [ ] **Step 1: Failing test:**

```python
class Portraits(unittest.TestCase):
    """Every model ships its portrait: a 256 px square PNG with alpha."""

    def test_every_model_has_its_portrait(self):
        for model in catalog.MODELS:
            path = catalog.portrait_path(model.key)
            self.assertTrue(os.path.isfile(path), path)
            with open(path, "rb") as handle:
                head = handle.read(32)
            self.assertEqual(head[:8], b"\x89PNG\r\n\x1a\n", path)
            width = int.from_bytes(head[16:20], "big")
            height = int.from_bytes(head[20:24], "big")
            self.assertEqual((width, height), (256, 256), path)
            self.assertEqual(head[25], 6, "RGBA expected: " + path)
```

- [ ] **Step 2: Write the renderer** `make_character_portraits.py`, run INSIDE the disposable
GUI Maya (port 7004), as a function `render(model_key, out_dir)`. For each model:
  - `cmds.file(new=True, force=True)`; add `catalog.character_for(model, "rig") or
    character_for(model, "skeleton")` via `character.add_character(entry)`;
  - a clay phong (0.62 grey, `colour.LOOK`) on every mesh unless the row is `textured`;
  - three directional lights (key warm 1.25, fill cool 0.45, rim 0.9);
  - the framing from the new root: `head`, `upperarm_l/_r` world points; the crown = the
    top of every mesh's world bbox; a square window of side
    `max(1.65 × shoulder span, 1.75 × (crown − shoulder height))`, its top 6 % above the
    crown;
  - a perspective camera (focal 85) at the head's X, 25° around +Y toward the character's
    left, slightly above;
  - the model panel: that camera, only polymeshes, textures and all lights on, AO,
    multisample AA, the grid and the HUD off;
  - `playblast` one frame at 512² PNG; the result scaled to 256 with
    `Qt.SmoothTransformation`, saved RGBA.
- [ ] **Step 3: Run it** (the disposable Maya boot, see Global Constraints), look at the four
  PNGs with the Read tool, adjust the framing constants until each is head and shoulders,
  centred, the crown in.
- [ ] **Step 4: Run** the portrait test → pass.
- [ ] **Step 5: Commit** `feat(characters): the four portraits, rendered in the viewport`.

---

### Task 8: Live proof and the picture

**Files:**
- Create: `docs/superpowers/plans/verify_character_grid.py`
- Modify: `docs/superpowers/plans/verify_hub_skin.py` (homes: `ss._PORTRAITS` in place of `ss._CHARACTER`)

- [ ] **Step 1: Write** `verify_character_grid.py` (run in the disposable Maya, the REPO
  plugin first on `sys.path`, modules purged). Gates:
  1. The hub is skinned and the Characters card holds `mayaSceneSetupPortraits`; the grid
     is `live()`, its four pixmaps are loaded, and its height equals `height_for(width)`
     and is > 0.
  2. No `mayaSceneSetupCharacterColour` or `mayaSceneSetupCharDot*` control exists.
  3. The Skeleton segment dims Orc D and lights the UE4 Mannequin; Rig does the reverse.
  4. A floor point P = (150, 0, -80) projected through the perspective panel to a global
     point; `floor_at` there gives Q with |Q − P| < 2 cm.
  5. `grid.drop_at(gx, gy, "Manny")` with kind rig adds a rig whose `Main` world
     translation equals Q to 1e-6, standing (Main's rotation zero).
  6. With kind skeleton, `drop_at(..., "Creep")` adds a skeleton whose root moved by
     (Q.x, 0, Q.z), its `Armature` at the origin, and `fbxlayout.root_in_layout(root)`
     is True.
  7. `window.add_character()` with Creep rig selected imports at the origin (Main at 0).
  8. `maya_colour.paint(rgb)` with the new rig's Main selected repaints that rig's meshes
     (their shading group's material colour is rgb).
  9. A synthetic press on the Creep tile, a move of 40 px, a move to the projected global
     point, a release: a Creep rig stands at Q (1e-6).
  10. A second send: `cmds.undo()` once takes the last dropped rig out whole (its
      namespace gone, the others untouched).
- [ ] **Step 2: Run it**; fix what it finds; re-run until every gate passes.
- [ ] **Step 3: The picture**: in a send of its own, `widget.grab()` of the Characters card
  (its frame, `skeldarHubCard_characters`) and of the viewport after the drops (playblast
  one frame); saved to the scratchpad, shown to the animator.
- [ ] **Step 4: Commit** the verify script and the hub-skin homes fix.

---

### Task 9: Hand-off

- [ ] Whole suite green (graphoverlay failures, if any, are the other session's work in
  progress — report them, do not touch).
- [ ] Refresh the installed copy in the animator's Maya over port 7001 if it is listening
  (`install.install(quiet=True)`, the `install` module purged first); otherwise say so.
- [ ] CLAUDE.md: a section "The Characters card: a portrait grid, a character dragged into
  the scene (2026-09-30)" — staged alone (the other session's hunk stays unstaged:
  `git apply --cached` of this hunk only).
- [ ] Memory: nothing unless a trap was found.
- [ ] Commit.
