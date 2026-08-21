# SkeldarAnim Installer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One drag-and-drop `install.py` that installs the SkeldarAnim shelf (Rig Picker, UE Bridge, Scene Setup, Overshoot, OverRig) with drawn icons, shipping the base sword and OverRig so both are found automatically.

**Architecture:** The repo root is the distribution folder. `install.py` (single file, stdlib-only at import) copies a whitelisted payload into `<userAppDir>/scripts/SkeldarAnim/` and builds the shelf whose button commands carry the destination path baked in. Two existing modules learn shipped-copy-first path resolution: `catalog.py` for the sword, `overrig.py` for the MEL toolset.

**Tech Stack:** Maya 2027 (`mayapy` + stdlib `unittest`), PySide6 QPainter for icon generation (offscreen), `maya.cmds`/`maya.mel` only inside functions that run in Maya.

**Spec:** `docs/superpowers/specs/2026-08-21-installer-design.md`

## Global Constraints

- No system Python. Tests run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest <target> -v` from `C:\!!!Work\MayaScripts`.
- Qt work headless: `$env:QT_QPA_PLATFORM = 'offscreen'` before mayapy.
- `install.py` and `catalog.py` must import with **no** `maya.*` and no `PySide6` loaded (subprocess boundary test pattern).
- House style: `str.format()`, double quotes, docstrings that say *why*.
- All paths that reach MEL or shelf commands use **forward slashes** (`.replace("\\", "/")` after any `os.path.join`).
- Shelf name and destination folder name: `SkeldarAnim`.
- The five buttons and their entry points: Rig Picker `maya_overrig.show_picker()`, UE Bridge `maya_uebridge.show_window()`, Scene Setup `maya_scenesetup.show_window()`, Overshoot `maya_overshoot.show_overshoot_ui()`, OverRig = MEL source + `$barnev_OverRig_RotateOrder=0` + `$path_to_JGLBN=<dest>/overrig/misc/` + `base_OverRig_scripts(1)`.
- Keep the public name `overrig.NOT_LOADED_MESSAGE` (consumed by builder.py, connect.py, aim.py, verify_twist_bones.py). `MEL_PATH` is used nowhere outside `overrig.py` (grep-verified 2026-08-21) and may be replaced.
- Bridge scripts (Task 7) follow CLAUDE.md bridge notes 5–8: if-guarded run-once marker (never `raise SystemExit`), unique output file per run, `exec(compile(src, path, "exec"), {"__name__": "__main__"})`, BOM-free ASCII runner, **no modal dialogs** over the port.
- Commits end with `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

---

### Task 1: The payload data lands in the repo

`assets/` with the sword, `overrig/` with the full third-party folder, the colleague README. No unit-test cycle — this is data landing; Task 2 and Task 5 tests pin it in place.

**Files:**
- Create: `assets/LongSword_02.fbx` (copy of `C:/!!!Work/Animations/Sources/LongSword_02.fbx`, 105 KB)
- Create: `overrig/` (full copy of `C:/!!!Work/Animations/Scripts/base_OverRig_scripts_V10_2_f1/`, 9 files, 1.1 MB)
- Create: `overrig/misc/.gitkeep` (the source `misc/` is EMPTY — measured, 0 files — and git does not track empty dirs; OverRig's own installer points `$path_to_JGLBN` at it, so it must survive a clone)
- Create: `README_INSTALL.txt`

**Interfaces:**
- Produces: `assets/LongSword_02.fbx` and `overrig/base_OverRig_scripts.mel` at the repo root — the paths `catalog._sword_path()` (Task 2), `overrig.MEL_CANDIDATES` (Task 3) and `install.payload()` (Task 5) resolve.

- [ ] **Step 1: Copy the data**

```bash
cd "C:/!!!Work/MayaScripts"
mkdir -p assets
cp "C:/!!!Work/Animations/Sources/LongSword_02.fbx" assets/
mkdir -p overrig
cp -r "C:/!!!Work/Animations/Scripts/base_OverRig_scripts_V10_2_f1/." overrig/
touch overrig/misc/.gitkeep
```

- [ ] **Step 2: Write `README_INSTALL.txt`** (UTF-8):

```
SkeldarAnim — набор инструментов аниматора для Maya:
Rig Picker, UE Bridge, Scene Setup, Overshoot, OverRig.

Установка:
  1. Распакуйте папку куда угодно.
  2. Перетащите файл install.py в открытое окно Maya (во вьюпорт).
  3. Появится полка SkeldarAnim с пятью кнопками.
     После этого распакованную папку можно удалить.

Обновление: перетащите install.py из новой версии ещё раз.

Удаление: удалите вкладку полки SkeldarAnim (ПКМ по вкладке) и папку
  Документы/maya/scripts/SkeldarAnim
```

- [ ] **Step 3: Verify the landing**

```bash
cd "C:/!!!Work/MayaScripts"
ls assets/LongSword_02.fbx overrig/base_OverRig_scripts.mel overrig/misc/.gitkeep overrig/icons/base_OverRig.bmp README_INSTALL.txt
```
Expected: all five paths listed, no errors.

- [ ] **Step 4: Commit**

```bash
git add assets overrig README_INSTALL.txt
git commit -m "feat(installer): ship the sword, OverRig and the colleague README

OverRig committed whole (License.txt included, misc/ kept via .gitkeep)
per the spec: the user's explicit call, private repo, intra-studio.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: `catalog.py` finds the shipped sword

**Files:**
- Modify: `maya_scenesetup/catalog.py:19-22`
- Test: `tests/test_scenesetup_catalog.py`

**Interfaces:**
- Consumes: `assets/LongSword_02.fbx` (Task 1).
- Produces: `catalog._sword_path() -> str` (module-private helper, absolute path with forward slashes); `catalog.WEAPONS[0].path` now resolves next to the container. `Weapon` shape and every public function unchanged.

- [ ] **Step 1: Write the failing tests** — append to `tests/test_scenesetup_catalog.py`:

```python
class SwordShipsWithTheTool(unittest.TestCase):
    """The sword resolves next to the container first (repo or installed
    copy alike), the user's legacy absolute path only as fallback."""

    def test_table_path_is_the_shipped_copy(self):
        path = catalog.WEAPONS[0].path
        self.assertTrue(path.endswith("assets/LongSword_02.fbx"), path)
        self.assertTrue(os.path.isfile(path), path)

    def test_shipped_path_uses_forward_slashes(self):
        """The path reaches the FBX plugin through MEL, where a backslash
        starts an escape (module docstring rule)."""
        self.assertNotIn("\\", catalog.WEAPONS[0].path)

    def test_missing_is_empty_for_the_shipped_sword(self):
        self.assertEqual(catalog.missing(catalog.WEAPONS[0]), "")

    def test_falls_back_to_the_legacy_path(self):
        """With no shipped copy on disk the old absolute path returns --
        a machine that predates assets/ keeps working."""
        original = catalog.os.path.isfile
        catalog.os.path.isfile = lambda _p: False
        try:
            path = catalog._sword_path()
        finally:
            catalog.os.path.isfile = original
        self.assertEqual(
            path, "C:/!!!Work/Animations/Sources/LongSword_02.fbx")
```

- [ ] **Step 2: Run to verify failure**

```powershell
& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_scenesetup_catalog -v
```
Expected: FAIL — `AttributeError: module ... has no attribute '_sword_path'` and the table-path asserts failing on the legacy absolute path.

- [ ] **Step 3: Implement** — in `maya_scenesetup/catalog.py`, replace lines 19-22:

```python
# Two dirnames up from this file is the container that holds both the
# packages and assets/ -- true in the repo and in an installed copy alike.
_CONTAINER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_LEGACY_SWORD = "C:/!!!Work/Animations/Sources/LongSword_02.fbx"


def _sword_path():
    """The shipped copy first, the legacy absolute path as fallback.

    Computed once at import: the table keeps holding a plain absolute
    path, so missing(), attach and the offset optionVars never learn
    that anything changed.
    """
    local = os.path.join(_CONTAINER, "assets",
                         "LongSword_02.fbx").replace("\\", "/")
    return local if os.path.isfile(local) else _LEGACY_SWORD


WEAPONS = [
    Weapon("LongSword_02", "Long Sword 02", _sword_path(), "weapon_r", 1.0),
]
```

- [ ] **Step 4: Run tests — the whole catalog file, then the full suite briefly**

```powershell
& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_scenesetup_catalog tests.test_scenesetup_window -v
```
Expected: PASS (window tests exercise `chosen_entry`, which reads the table).

- [ ] **Step 5: Commit**

```bash
git add maya_scenesetup/catalog.py tests/test_scenesetup_catalog.py
git commit -m "feat(installer): the sword resolves next to the container first

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: `overrig.py` prefers the shipped MEL

**Files:**
- Modify: `maya_overrig/overrig.py:16-19,54-56,64-76`
- Test: `tests/test_overrig.py`

**Interfaces:**
- Consumes: `overrig/base_OverRig_scripts.mel` (Task 1).
- Produces: `overrig.MEL_CANDIDATES` (tuple of two absolute forward-slash paths, shipped first); `overrig.mel_path(candidates=MEL_CANDIDATES) -> str` (first existing, `""` when none); `ensure_loaded()` behavior unchanged except it sources `mel_path()`. `NOT_LOADED_MESSAGE` keeps its name; the constant `MEL_PATH` is removed (no external consumers, grep-verified).

- [ ] **Step 1: Write the failing tests** — append to `tests/test_overrig.py`:

```python
import os
import tempfile


class MelPathCandidates(unittest.TestCase):
    """The shipped copy first (installer and repo both put OverRig in
    overrig/ next to the package), the user's original install second."""

    def test_shipped_candidate_leads(self):
        first = overrig.MEL_CANDIDATES[0]
        self.assertTrue(
            first.endswith("overrig/base_OverRig_scripts.mel"), first)
        self.assertNotIn("\\", first)

    def test_legacy_candidate_survives(self):
        self.assertIn("base_OverRig_scripts_V10_2_f1",
                      overrig.MEL_CANDIDATES[1])

    def test_shipped_copy_exists_and_wins(self):
        """Task 1 landed the file, so in this repo mel_path() is the
        shipped one."""
        self.assertEqual(overrig.mel_path(), overrig.MEL_CANDIDATES[0])
        self.assertTrue(os.path.isfile(overrig.mel_path()))

    def test_first_existing_wins(self):
        with tempfile.NamedTemporaryFile(suffix=".mel",
                                         delete=False) as handle:
            real = handle.name
        try:
            picked = overrig.mel_path(
                candidates=("C:/nowhere/at/all.mel", real))
            self.assertEqual(picked, real)
        finally:
            os.remove(real)

    def test_none_existing_reads_empty(self):
        self.assertEqual(
            overrig.mel_path(candidates=("C:/no.mel", "C:/also/no.mel")),
            "")

    def test_not_loaded_message_names_both_places(self):
        for candidate in overrig.MEL_CANDIDATES:
            self.assertIn(candidate, overrig.NOT_LOADED_MESSAGE)
```

- [ ] **Step 2: Run to verify failure**

```powershell
& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_overrig -v
```
Expected: FAIL — `AttributeError: ... no attribute 'MEL_CANDIDATES'`.

- [ ] **Step 3: Implement** — in `maya_overrig/overrig.py` replace the `MEL_PATH` block (lines 16-19) with:

```python
# Two dirnames up from this file is the container that holds both the
# packages and the shipped overrig/ folder -- true in the repo and in an
# installed copy alike. The user's original install stays as fallback for
# machines that predate the bundle.
_CONTAINER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MEL_CANDIDATES = (
    os.path.join(_CONTAINER, "overrig",
                 "base_OverRig_scripts.mel").replace("\\", "/"),
    "C:/!!!Work/Animations/Scripts/base_OverRig_scripts_V10_2_f1/"
    "base_OverRig_scripts.mel",
)


def mel_path(candidates=MEL_CANDIDATES):
    """The first candidate that exists on disk, "" when none does."""
    for path in candidates:
        if os.path.isfile(path):
            return path
    return ""
```

replace the `NOT_LOADED_MESSAGE` block (lines 54-56) with:

```python
NOT_LOADED_MESSAGE = (
    "OverRig is not loaded - press the OverRig shelf button "
    "(looked for {0})".format(" and ".join(MEL_CANDIDATES)))
```

and rewrite `ensure_loaded` (lines 64-76):

```python
def ensure_loaded():
    """Source the toolset if it is not already in the session.

    Deliberately does not go looking around the disk beyond the two known
    places: either the procs are there, or a candidate is, or the caller
    reports failure and the user presses the OverRig shelf button.
    """
    if is_loaded():
        return True
    path = mel_path()
    if not path:
        return False
    mel.eval('source "{0}";'.format(path))
    return is_loaded()
```

(`mel_path` must be defined above `NOT_LOADED_MESSAGE`? No — `NOT_LOADED_MESSAGE` uses only `MEL_CANDIDATES`; order as shown: candidates, then `mel_path`, constants below keep their places.)

- [ ] **Step 4: Run tests**

```powershell
& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_overrig tests.test_builder tests.test_fkcontrols -v
```
Expected: PASS (builder/fkcontrols consume `NOT_LOADED_MESSAGE`).

- [ ] **Step 5: Commit**

```bash
git add maya_overrig/overrig.py tests/test_overrig.py
git commit -m "feat(installer): OverRig MEL resolves shipped-copy-first

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: The four icons

Tests first (they pin size and format), then the generator, then the PNGs, then the user sees them.

**Files:**
- Create: `icons/make_icons.py`
- Create: `icons/picker.png`, `icons/uebridge.png`, `icons/scenesetup.png`, `icons/overshoot.png` (generated, committed)
- Test: `tests/test_install.py` (new file; more classes join it in Task 5)

**Interfaces:**
- Produces: the four 32×32 PNGs `install.button_specs` (Task 5) references by name. `make_icons.main(out_dir)` regenerates them.

- [ ] **Step 1: Write the failing tests** — create `tests/test_install.py`:

```python
"""Tests for the drag-and-drop installer and its icons.

The icon checks parse the PNG header by hand -- IHDR width/height are
big-endian at bytes 16..24 -- because there is no PIL in the Maya tree
and none is going in.
"""

import os
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ICON_NAMES = ("picker.png", "uebridge.png", "scenesetup.png",
              "overshoot.png")


class Icons(unittest.TestCase):

    def _header(self, name):
        path = os.path.join(REPO, "icons", name)
        self.assertTrue(os.path.isfile(path), path)
        with open(path, "rb") as handle:
            return handle.read(24)

    def test_all_four_exist_as_png(self):
        for name in ICON_NAMES:
            head = self._header(name)
            self.assertEqual(head[:8], b"\x89PNG\r\n\x1a\n", name)

    def test_all_four_are_32_by_32(self):
        for name in ICON_NAMES:
            head = self._header(name)
            width = int.from_bytes(head[16:20], "big")
            height = int.from_bytes(head[20:24], "big")
            self.assertEqual((width, height), (32, 32), name)
```

- [ ] **Step 2: Run to verify failure**

```powershell
& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_install -v
```
Expected: FAIL — the icon files do not exist.

- [ ] **Step 3: Write `icons/make_icons.py`** (complete file):

```python
"""Draw the four SkeldarAnim shelf icons.

32x32 PNG on a dark rounded plate so they read on Maya's shelf: flat
glyphs, ~2 px strokes, one accent colour per tool. Regenerate with:

    $env:QT_QPA_PLATFORM = 'offscreen'
    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' icons/make_icons.py
"""

import os
import sys

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QColor, QGuiApplication, QImage, QPainter,
                           QPainterPath, QPen)

SIZE = 32
PLATE = QColor("#262626")
EDGE = QColor("#4a4a4a")


def _canvas():
    image = QImage(SIZE, SIZE, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(QPen(EDGE, 1))
    painter.setBrush(PLATE)
    painter.drawRoundedRect(QRectF(0.5, 0.5, SIZE - 1, SIZE - 1), 6, 6)
    return image, painter


def _pen(colour, width):
    return QPen(QColor(colour), width, Qt.SolidLine, Qt.RoundCap,
                Qt.RoundJoin)


def draw_picker(path):
    """A miniature of the body map: circle head, dot buttons."""
    image, painter = _canvas()
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#4fc3f7"))
    painter.drawEllipse(QPointF(16, 7.5), 3.0, 3.0)
    dots = [(16, 13.5), (16, 17), (16, 20.5),          # spine
            (11.5, 13.5), (8.5, 17), (20.5, 13.5), (23.5, 17),  # arms
            (13.5, 24), (12.5, 27.5), (18.5, 24), (19.5, 27.5)]  # legs
    for x, y in dots:
        painter.drawEllipse(QPointF(x, y), 1.7, 1.7)
    painter.end()
    image.save(path)


def draw_uebridge(path):
    """A clip plate with frame ticks and an arrow coming into the scene."""
    image, painter = _canvas()
    painter.setPen(_pen("#ffa726", 2.0))
    painter.setBrush(Qt.NoBrush)
    painter.drawRoundedRect(QRectF(7, 6, 18, 8), 2, 2)
    painter.setPen(_pen("#ffa726", 1.3))
    for x in (11, 14.5, 18, 21.5):
        painter.drawLine(QPointF(x, 8), QPointF(x, 12))
    painter.setPen(_pen("#ffa726", 2.4))
    painter.drawLine(QPointF(16, 17), QPointF(16, 26.5))
    painter.drawLine(QPointF(11.5, 22), QPointF(16, 26.5))
    painter.drawLine(QPointF(20.5, 22), QPointF(16, 26.5))
    painter.end()
    image.save(path)


def draw_scenesetup(path):
    """A sword: blade, crossguard, grip, pommel."""
    image, painter = _canvas()
    painter.setPen(_pen("#cfd8dc", 2.8))
    painter.drawLine(QPointF(23.5, 6.5), QPointF(12, 18))
    painter.setPen(_pen("#cfd8dc", 2.4))
    painter.drawLine(QPointF(10.1, 14.5), QPointF(15.5, 19.9))
    painter.setPen(_pen("#cfd8dc", 2.6))
    painter.drawLine(QPointF(11.3, 18.7), QPointF(8, 22))
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#cfd8dc"))
    painter.drawEllipse(QPointF(7.2, 22.8), 1.8, 1.8)
    painter.end()
    image.save(path)


def draw_overshoot(path):
    """A curve overshooting a dashed target line and settling."""
    image, painter = _canvas()
    dashed = QPen(QColor(129, 199, 132, 150), 1.3, Qt.DashLine)
    painter.setPen(dashed)
    painter.drawLine(QPointF(5, 13), QPointF(27, 13))
    curve = QPainterPath(QPointF(5.5, 26.5))
    curve.cubicTo(QPointF(9, 26.5), QPointF(10, 8.5), QPointF(13.5, 8.5))
    curve.cubicTo(QPointF(16.5, 8.5), QPointF(16, 16), QPointF(18.5, 16))
    curve.cubicTo(QPointF(20.5, 16), QPointF(20.5, 12), QPointF(22.5, 12))
    curve.cubicTo(QPointF(24.5, 12), QPointF(24.5, 13), QPointF(26.5, 13))
    painter.setPen(_pen("#81c784", 2.2))
    painter.setBrush(Qt.NoBrush)
    painter.drawPath(curve)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#81c784"))
    painter.drawEllipse(QPointF(5.5, 26.5), 2.0, 2.0)
    painter.end()
    image.save(path)


DRAWERS = {
    "picker.png": draw_picker,
    "uebridge.png": draw_uebridge,
    "scenesetup.png": draw_scenesetup,
    "overshoot.png": draw_overshoot,
}


def main(out_dir=None):
    out_dir = out_dir or os.path.dirname(os.path.abspath(__file__))
    QGuiApplication.instance() or QGuiApplication([sys.argv[0]])
    for name, draw in sorted(DRAWERS.items()):
        draw(os.path.join(out_dir, name))
        print("wrote " + name)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
```

- [ ] **Step 4: Generate the icons**

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' "C:\!!!Work\MayaScripts\icons\make_icons.py"
```
Expected: four `wrote <name>` lines.

- [ ] **Step 5: Run the icon tests**

```powershell
& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_install -v
```
Expected: PASS.

- [ ] **Step 6: Show the user.** Build a 4× preview in the scratchpad (Qt smooth scale, the four icons in a row on a #444 shelf-grey strip) and send it with SendUserFile — the spec says the motifs are a starting point, not a contract. Adjust drawing code if the user asks, regenerate, re-send.

- [ ] **Step 7: Commit**

```bash
git add icons tests/test_install.py
git commit -m "feat(installer): the four shelf icons and their generator

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: `install.py` — the pure parts

**Files:**
- Create: `install.py` (repo root; pure parts only — `payload`, `source_root`, `button_specs`, plus the module docstring)
- Test: `tests/test_install.py` (extend)

**Interfaces:**
- Consumes: icon filenames (Task 4), the entry points from Global Constraints.
- Produces: `install.SHELF == "SkeldarAnim"`; `install.payload() -> tuple[str]` (names relative to the distribution root); `install.source_root() -> str`; `install.button_specs(dest) -> list[dict]` with keys `label`, `annotation`, `image`, `sourceType`, `command` — exactly five, order: Rig Picker, UE Bridge, Scene Setup, Overshoot, OverRig. Task 6 builds `copy_payload`/`install()` on these.

- [ ] **Step 1: Write the failing tests** — append to `tests/test_install.py`:

```python
import subprocess
import sys

import install


class MayaFreeBoundary(unittest.TestCase):
    """install.py runs at drop time, before anything of ours is on
    sys.path -- it must import with stdlib alone."""

    def test_importing_install_pulls_in_neither_maya_nor_qt(self):
        script = (
            "import sys\n"
            "import install\n"
            "leaked = [m for m in sys.modules\n"
            "          if m.startswith('maya.') or m.startswith('PySide6')]\n"
            "print(';'.join(sorted(leaked)))\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=REPO, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "",
                         "importing install leaked: " + result.stdout.strip())


class Payload(unittest.TestCase):
    """The whitelist is the contract: everything on it exists in the repo,
    and the animator's prefs get nothing else."""

    def test_every_entry_exists_in_the_repo(self):
        for name in install.payload():
            self.assertTrue(
                os.path.exists(os.path.join(REPO, name)), name)

    def test_the_dev_only_folders_stay_out(self):
        for name in ("tests", "docs", "archive", "maya_retarget.py"):
            self.assertNotIn(name, install.payload())

    def test_the_installer_ships_itself(self):
        """A colleague repairs the shelf by re-dragging install.py from
        the installed folder -- so the installed folder must hold it."""
        self.assertIn("install.py", install.payload())
        self.assertIn("README_INSTALL.txt", install.payload())

    def test_source_root_is_this_repo(self):
        self.assertEqual(os.path.normcase(install.source_root()),
                         os.path.normcase(REPO))


class ButtonSpecs(unittest.TestCase):

    DEST = "C:/Users/Some Body/Documents/maya/scripts/SkeldarAnim"

    def _specs(self):
        return install.button_specs(self.DEST)

    def test_five_buttons_in_shelf_order(self):
        labels = [s["label"] for s in self._specs()]
        self.assertEqual(labels, ["Rig Picker", "UE Bridge", "Scene Setup",
                                  "Overshoot", "OverRig"])

    def test_python_buttons_bootstrap_and_call(self):
        wanted = {
            "Rig Picker": ("maya_overrig", "show_picker"),
            "UE Bridge": ("maya_uebridge", "show_window"),
            "Scene Setup": ("maya_scenesetup", "show_window"),
            "Overshoot": ("maya_overshoot", "show_overshoot_ui"),
        }
        for spec in self._specs()[:4]:
            module, func = wanted[spec["label"]]
            self.assertEqual(spec["sourceType"], "python")
            self.assertIn(self.DEST, spec["command"])
            self.assertIn("sys.path.insert(0, _p)", spec["command"])
            self.assertIn("import {0}".format(module), spec["command"])
            self.assertIn("{0}.{1}()".format(module, func), spec["command"])

    def test_python_buttons_use_our_icons(self):
        icons = [s["image"] for s in self._specs()[:4]]
        self.assertEqual(icons, [
            self.DEST + "/icons/picker.png",
            self.DEST + "/icons/uebridge.png",
            self.DEST + "/icons/scenesetup.png",
            self.DEST + "/icons/overshoot.png"])

    def test_overrig_button_replays_the_native_installer(self):
        """Verbatim from OverRig's own Drag_and_Drop_to_install.mel: the
        source, both globals, misc/ and the coloring argument."""
        spec = self._specs()[4]
        self.assertEqual(spec["sourceType"], "mel")
        command = spec["command"]
        self.assertIn(
            'source "{0}/overrig/base_OverRig_scripts.mel";'.format(
                self.DEST), command)
        self.assertIn("global int $barnev_OverRig_RotateOrder = 0;", command)
        self.assertIn(
            '$path_to_JGLBN = "{0}/overrig/misc/";'.format(self.DEST),
            command)
        self.assertIn("base_OverRig_scripts(1);", command)
        self.assertEqual(spec["image"],
                         self.DEST + "/overrig/icons/base_OverRig.bmp")

    def test_backslashes_never_reach_a_command(self):
        for spec in install.button_specs(
                "C:\\Users\\Some Body\\Documents\\maya\\scripts\\SkeldarAnim"):
            self.assertNotIn("\\", spec["command"])
            self.assertNotIn("\\", spec["image"])
```

- [ ] **Step 2: Run to verify failure**

```powershell
& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_install -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'install'`.

- [ ] **Step 3: Write `install.py`** (pure parts; Task 6 appends the rest):

```python
"""Drag this file into an open Maya viewport to install SkeldarAnim.

Copies the toolset into <userAppDir>/scripts/SkeldarAnim and builds the
SkeldarAnim shelf: Rig Picker, UE Bridge, Scene Setup, Overshoot, and the
native OverRig panel. Re-dragging updates in place. The unzipped folder
can be deleted after installing.

Design: docs/superpowers/specs/2026-08-21-installer-design.md

Stdlib-only at import: at drop time nothing of ours is on sys.path, and
maya.cmds exists only inside the running Maya -- so the Maya imports live
inside the functions that run there.
"""

import os
import shutil

SHELF = "SkeldarAnim"

# The whitelist. Everything the animator's prefs receive, and nothing
# else: tests, docs, archive and the other root-level tools stay home.
_PAYLOAD = (
    "maya_overrig",
    "maya_uebridge",
    "maya_scenesetup",
    "maya_overshoot.py",
    "icons",
    "assets",
    "overrig",
    "install.py",
    "README_INSTALL.txt",
)

_PYTHON_BUTTONS = (
    ("Rig Picker", "OverRig picker: build, switch and select the rig",
     "maya_overrig", "show_picker", "picker.png"),
    ("UE Bridge", "Import animations from the running Unreal editor",
     "maya_uebridge", "show_window", "uebridge.png"),
    ("Scene Setup", "Weapon in the hand, camera on the camera bone",
     "maya_scenesetup", "show_window", "scenesetup.png"),
    ("Overshoot", "Build the stop of a move on the selected keys",
     "maya_overshoot", "show_overshoot_ui", "overshoot.png"),
)


def payload():
    """What gets copied, as names relative to the distribution root."""
    return _PAYLOAD


def source_root():
    """The distribution root: the folder this file was dragged from."""
    return os.path.dirname(os.path.abspath(__file__))


def button_specs(dest):
    """The five shelf buttons as data, every path baked in absolute.

    `dest` may arrive with backslashes; commands reach MEL and the shelf
    editor, where a backslash starts an escape -- so it is normalised
    once here and nowhere else needs to care.
    """
    dest = dest.replace("\\", "/").rstrip("/")
    bootstrap = (
        "import sys\n"
        "_p = \"{0}\"\n"
        "if _p not in sys.path:\n"
        "    sys.path.insert(0, _p)\n").format(dest)
    specs = []
    for label, note, module, func, icon in _PYTHON_BUTTONS:
        specs.append({
            "label": label,
            "annotation": note,
            "image": "{0}/icons/{1}".format(dest, icon),
            "sourceType": "python",
            "command": (bootstrap
                        + "import {0}\n{0}.{1}()\n".format(module, func)),
        })
    # Verbatim from OverRig's own Drag_and_Drop_to_install.mel, paths
    # aside: the two globals and the (1) coloring are the author's own
    # defaults, and $path_to_JGLBN must point at the shipped misc/.
    specs.append({
        "label": "OverRig",
        "annotation": "The native OverRig panel (Pavel Barnev, v10.2)",
        "image": "{0}/overrig/icons/base_OverRig.bmp".format(dest),
        "sourceType": "mel",
        "command": (
            'source "{0}/overrig/base_OverRig_scripts.mel";\n'
            "global int $barnev_OverRig_RotateOrder = 0;\n"
            "global string $path_to_JGLBN;\n"
            '$path_to_JGLBN = "{0}/overrig/misc/";\n'
            "base_OverRig_scripts(1);\n").format(dest),
    })
    return specs
```

- [ ] **Step 4: Run tests**

```powershell
& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_install -v
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add install.py tests/test_install.py
git commit -m "feat(installer): install.py pure parts - payload and button specs

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 6: `install.py` — copy, shelf, drop entry

**Files:**
- Modify: `install.py` (append `copy_payload`, `same_place`, `_build_shelf`, `install`, `onMayaDroppedPythonFile`)
- Modify: `docs/superpowers/specs/2026-08-21-installer-design.md` (one sentence: the payload also carries `install.py` and `README_INSTALL.txt`, so the installed folder can repair itself)
- Test: `tests/test_install.py` (extend)

**Interfaces:**
- Consumes: `payload()`, `button_specs(dest)`, `SHELF` (Task 5).
- Produces: `install.copy_payload(src_root, dest)` (rmtree+copy, skips `__pycache__`/`*.pyc`); `install.same_place(a, b) -> bool`; `install.install(dropped=None, quiet=False)`; `onMayaDroppedPythonFile(*args)`. `quiet=True` skips the confirmDialog — **a modal dialog over the command port blocks Maya's idle queue** (bridge note 6), and Task 7 drives `install()` over the port.

- [ ] **Step 1: Write the failing tests** — append to `tests/test_install.py`:

```python
import shutil
import tempfile


class CopyPayload(unittest.TestCase):
    """copy_payload against a throwaway destination: whitelist in,
    caches out, idempotent, and never eats its own source."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="skeldar_install_")
        self.dest = os.path.join(self.tmp, "SkeldarAnim")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_copies_exactly_the_payload(self):
        install.copy_payload(REPO, self.dest)
        self.assertEqual(sorted(os.listdir(self.dest)),
                         sorted(install.payload()))

    def test_pycache_stays_home(self):
        install.copy_payload(REPO, self.dest)
        for base, dirs, files in os.walk(self.dest):
            self.assertNotIn("__pycache__", dirs, base)
            for name in files:
                self.assertFalse(name.endswith(".pyc"),
                                 os.path.join(base, name))

    def test_overrig_misc_survives_the_trip(self):
        """OverRig's own button points $path_to_JGLBN at misc/."""
        install.copy_payload(REPO, self.dest)
        self.assertTrue(os.path.isdir(
            os.path.join(self.dest, "overrig", "misc")))

    def test_second_run_replaces_rather_than_accumulates(self):
        install.copy_payload(REPO, self.dest)
        stray = os.path.join(self.dest, "stray.txt")
        with open(stray, "w") as handle:
            handle.write("left over")
        install.copy_payload(REPO, self.dest)
        self.assertFalse(os.path.exists(stray))

    def test_same_place_sees_through_slash_styles(self):
        os.makedirs(self.dest)
        self.assertTrue(install.same_place(
            self.dest, self.dest.replace("\\", "/")))

    def test_same_place_is_false_for_a_missing_destination(self):
        self.assertFalse(install.same_place(REPO, self.dest))
```

- [ ] **Step 2: Run to verify failure**

```powershell
& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_install -v
```
Expected: FAIL — `AttributeError: ... no attribute 'copy_payload'`.

- [ ] **Step 3: Implement** — append to `install.py`:

```python
def same_place(a, b):
    """True when the two paths are one folder on disk.

    The guard that keeps a re-drag from the installed folder itself from
    rmtree-ing the very files it is about to copy.
    """
    if not (os.path.isdir(a) and os.path.isdir(b)):
        return False
    return os.path.samefile(a, b)


def copy_payload(src_root, dest):
    """The whitelist into `dest`, replacing whatever was there."""
    if os.path.isdir(dest):
        shutil.rmtree(dest)
    os.makedirs(dest)
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
    for name in payload():
        src = os.path.join(src_root, name)
        target = os.path.join(dest, name)
        if os.path.isdir(src):
            shutil.copytree(src, target, ignore=ignore)
        else:
            shutil.copy2(src, target)


def _build_shelf(dest):
    """The SkeldarAnim tab, rebuilt button-for-button.

    The tab is created through Maya's own addNewShelfTab (it keeps the
    shelf optionVars consistent) and never deleted -- an existing tab
    only has its buttons replaced, which is what makes a re-drag an
    update rather than a duplicate.
    """
    import maya.cmds as cmds
    import maya.mel as mel
    if not cmds.shelfLayout(SHELF, exists=True):
        mel.eval('addNewShelfTab "{0}";'.format(SHELF))
    for child in cmds.shelfLayout(SHELF, query=True, childArray=True) or []:
        cmds.deleteUI(child)
    for spec in button_specs(dest):
        cmds.shelfButton(
            label=spec["label"],
            annotation=spec["annotation"],
            image=spec["image"],
            sourceType=spec["sourceType"],
            command=spec["command"],
            parent=SHELF,
        )


def install(dropped=None, quiet=False):
    """Copy the payload, build the shelf, say so.

    `dropped` is the path Maya hands onMayaDroppedPythonFile; __file__
    is the fallback. `quiet` skips the confirm dialog: a modal dialog
    over the command port blocks Maya's idle queue, so scripted runs
    must never raise one.
    """
    import maya.cmds as cmds
    src = os.path.dirname(os.path.abspath(dropped)) if dropped \
        else source_root()
    dest = os.path.join(cmds.internalVar(userAppDir=True),
                        "scripts", SHELF)
    if not same_place(src, dest):
        copy_payload(src, dest)
    _build_shelf(dest.replace("\\", "/"))
    if not quiet:
        cmds.confirmDialog(
            title="SkeldarAnim",
            message="Installed: shelf {0}, {1} buttons.\n{2}".format(
                SHELF, len(button_specs(dest)), dest),
            button=["OK"])
    return dest


def onMayaDroppedPythonFile(*args):
    install(args[0] if args else None)
```

- [ ] **Step 4: Run tests — full suite this time**

```powershell
& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v
```
Expected: all green (787 + the new ones). `copy_payload` tests copy ~1.2 MB into temp — fast.

- [ ] **Step 5: Add the spec sentence.** In `docs/superpowers/specs/2026-08-21-installer-design.md`, in the whitelist paragraph of "Install mechanics", extend the payload list with `install.py` and `README_INSTALL.txt`, with the sentence: "The installer ships itself: a colleague repairs the shelf by re-dragging `install.py` from the installed folder, so the installed folder must hold it."

- [ ] **Step 6: Commit**

```bash
git add install.py tests/test_install.py docs/superpowers/specs/2026-08-21-installer-design.md
git commit -m "feat(installer): copy step, shelf build and the drop entry point

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 7: Live verification through the bridge

**Files:**
- Create: `docs/superpowers/plans/verify_install.py`

**Interfaces:**
- Consumes: everything above, running inside the user's live Maya over commandPort 7001.

The script's gates (each prints `GATE <n> PASS/FAIL <detail>`; the runner collects into the output file):

1. `install.install(quiet=True)` runs from the repo's `install.py`, loaded with `importlib.util.spec_from_file_location("skeldar_install_probe", <repo>/install.py)` — not a bare `import install` (the session's `sys.path` must stay clean of the repo root until the buttons themselves add the install dir).
2. The destination folder exists and `sorted(os.listdir(dest)) == sorted(payload())` — nothing extra, nothing missing; `overrig/misc/` present.
3. `cmds.shelfLayout("SkeldarAnim", exists=True)` and exactly five `shelfButton` children whose labels read, in order: Rig Picker, UE Bridge, Scene Setup, Overshoot, OverRig.
4. Each of the four Python button commands, read back with `cmds.shelfButton(btn, query=True, command=True)`, executes via `exec(compile(cmd, "<shelf>", "exec"), {})` without raising, and its window appears: `cmds.window` exists for `ueAnimBridgeWindow`, `mayaSceneSetupWindow`, `animOvershootWin`; the picker via `any(w.objectName() == "rigPickerWindow" for w in QApplication.topLevelWidgets())`. Close each window after the check (`cmds.deleteUI` / `.close()`).
5. The OverRig button command via `mel.eval` — afterwards `mel.eval('exists "base_OverRig_scripts"')` is true and the `basicOverRigScripts` dockControl exists. Leave the dock open (it is the user's tool) but note it in the output.
6. The installed catalog resolves the shipped sword: load `<dest>/maya_scenesetup/catalog.py` as `spec_from_file_location("skeldar_catalog_probe", ...)` (it is stdlib-only, so it imports standalone); assert `WEAPONS[0].path` starts with the forward-slashed dest and `os.path.isfile` of it.
7. Idempotence: run `install.install(quiet=True)` again; still exactly five buttons, dest still matches the payload.
8. `sys.path` restored: the button commands each inserted `dest` — remove it and assert no repo/dest entries leaked that were not there before.

Bridge hygiene (CLAUDE.md notes 5–8, non-negotiable): the runner wraps the body in `if not os.path.exists(marker):` — **no `raise SystemExit`**; marker written first; output file name unique per run; payload read as UTF-8; runner written BOM-free (`[System.IO.File]::WriteAllText` with `UTF8Encoding($false)` or ASCII); `exec(compile(src, path, "exec"), {"__name__": "__main__"})`.

- [ ] **Step 1: Check the port is alive** — `Get-NetTCPConnection -State Listen -LocalPort 7001`. CLAUDE.md records the port died to trap 8 on 2026-08-20 and only a Maya restart revives it. If dead or unresponsive (send a two-line print probe first), STOP and ask the user to restart Maya and re-run the one-liner; do not burn runs diagnosing a dead bridge.
- [ ] **Step 2: Write `verify_install.py`** implementing gates 1–8 with the hygiene above.
- [ ] **Step 3: Send it; read the output file; every gate PASS.** On any FAIL: superpowers:systematic-debugging, fix, re-run (fresh output name each time).
- [ ] **Step 4: Ask the user to look at the shelf** — five icons visible, buttons open their windows when pressed by hand, icons legible at real size.
- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/plans/verify_install.py
git commit -m "test(installer): live verification - install, shelf, windows, sword

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 8: Documentation

**Files:**
- Modify: `CLAUDE.md` (new section after `maya_overshoot`, before "Retargeting": `## install.py — the SkeldarAnim shelf, drag-and-drop`)

**Interfaces:** none — prose.

- [ ] **Step 1: Write the CLAUDE.md section.** Cover, in the file's established voice: what a drop does (whitelist copy to `<userAppDir>/scripts/SkeldarAnim`, shelf rebuilt button-for-button, tab never deleted); the five buttons and where their commands come from (`button_specs`); shipped-copy-first resolution in `catalog._sword_path()` and `overrig.mel_path()` with the legacy paths as fallback; the `same_place` guard and why (re-drag from the installed folder must not rmtree its own source); `quiet=True` and why (modal dialog over the port = blocked idle queue, bridge note 6); `overrig/misc/.gitkeep` (source folder is empty, `$path_to_JGLBN` points at it); the OverRig license decision (clause 3 flagged, user chose to commit; private repo, intra-studio); icons regenerated by `icons/make_icons.py` under mayapy offscreen.
- [ ] **Step 2: Full suite one last time**

```powershell
& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v
```
Expected: all green.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: the SkeldarAnim installer - how a drop installs, and the traps

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```
