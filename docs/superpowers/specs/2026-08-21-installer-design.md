# SkeldarAnim drag-and-drop installer — design

2026-08-21. Approved by the user in brainstorming; every decision below that
names the user is theirs, made with the trade-off on the table.

## What this is

One file, `install.py`, at the repo root. An animator drags it into an open
Maya viewport and gets a shelf named **SkeldarAnim** with five buttons: Rig
Picker, UE Bridge, Scene Setup, Overshoot, and the native OverRig panel. The
base sword ships in the folder and the weapon tool finds it by itself; OverRig
ships too, so a colleague's Build works out of the box.

The audience is **the user and their colleagues** (the user's call). That is
what makes this an installer rather than a shelf script: the folder gets
zipped and handed to another animator, who unzips it anywhere — Downloads
included — drags `install.py` in, and can delete the unzip afterwards.

## Install mechanics — the copying installer

Three mechanics were considered: copy into the user's prefs (A), reference the
unzipped folder in place (B), a Maya `.mod` module (C). The user chose **A**,
and it is the right default for this audience: B breaks the shelf the day the
colleague tidies their Downloads, and C is more moving parts for the same five
buttons. A is also the scheme OverRig's own `Drag_and_Drop_to_install.mel`
uses, so it is the pattern this studio's animators have already met.

Maya executes a dropped `.py` file and calls `onMayaDroppedPythonFile(path)`
if the file defines it (Maya 2017+; the studio is on 2027). During that exec
`__file__` is set, which is how the installer finds the distribution root.

What a drop does, in order:

1. **Locate itself** via `__file__` → the distribution root.
2. **Copy the payload** to `<internalVar(userAppDir)>/scripts/SkeldarAnim/`.
   The payload is a **whitelist**, not "everything next to install.py":
   `maya_overrig/`, `maya_uebridge/`, `maya_scenesetup/`, `maya_overshoot.py`,
   `icons/`, `assets/`, `overrig/`. Tests, docs, archive and the other
   root-level tools stay out of the animator's prefs. `__pycache__` and
   `*.pyc` are excluded on copy.
3. **Idempotence:** an existing destination folder is deleted and rewritten —
   except when the source **is** the destination (a colleague re-drags
   `install.py` from the installed folder itself to repair the shelf; deleting
   the source before copying it would destroy the installation). In that case
   only the shelf is rebuilt. The delete target is a constant path derived
   from `userAppDir`, never from user input.
4. **Build the shelf.** If the `SkeldarAnim` tab does not exist it is created
   through Maya's own `addNewShelfTab`, which keeps the shelf optionVars
   consistent; if it exists, only its buttons are deleted and re-added.
   Shelf *tabs* are never deleted — the classic deleted-shelf-reappears
   dance with `shelfName<N>` optionVars is not worth entering for a rebuild
   that button-level replacement already gives us.
5. **Report**: a small dialog — installed, shelf SkeldarAnim, five buttons.

## The five buttons

Each of our four buttons is a Python-sourceType shelf button whose command is
written **at install time** with the real destination path baked in:

```python
import sys
_p = r"<dest>"
if _p not in sys.path:
    sys.path.insert(0, _p)
import maya_overrig
maya_overrig.show_picker()
```

| Button | Entry point | Icon |
|---|---|---|
| Rig Picker | `maya_overrig.show_picker()` | `icons/picker.png` |
| UE Bridge | `maya_uebridge.show_window()` | `icons/uebridge.png` |
| Scene Setup | `maya_scenesetup.show_window()` | `icons/scenesetup.png` |
| Overshoot | `maya_overshoot.show_overshoot_ui()` | `icons/overshoot.png` |
| OverRig | native panel, see below | OverRig's own `base_OverRig.bmp` |

The fifth button replicates the command OverRig's own installer writes,
verbatim apart from the paths — this was read out of
`Drag_and_Drop_to_install.mel` rather than guessed:

```mel
source "<dest>/overrig/base_OverRig_scripts.mel";
global int $barnev_OverRig_RotateOrder = 0;
global string $path_to_JGLBN;
$path_to_JGLBN = "<dest>/overrig/misc/";
base_OverRig_scripts(1);
```

`$path_to_JGLBN` must point at the shipped `misc/` folder; the two globals and
the `(1)` coloring argument are the author's own defaults. The user chose to
have this fifth button (five, not four): without it a colleague who received
OverRig in the bundle has no way to open its panel.

## What ships, and the license question

The distribution folder is the repo root itself:

```
install.py             the installer, one file
README_INSTALL.txt     three lines for a colleague: unzip → drag → done
icons/                 picker.png, uebridge.png, scenesetup.png, overshoot.png
                       + make_icons.py (the generator)
assets/LongSword_02.fbx
overrig/               full copy of base_OverRig_scripts_V10_2_f1
```

**The sword is committed.** The repo is private (verified: unauthenticated
GitHub API answers 404), the asset is the studio's own, and 105 KB is nothing.

**OverRig is committed too — the user's explicit call, made with the license
in front of them.** `License.txt` clause 3 forbids distributing copies without
the author's written consent; the alternatives (a gitignored slot filled by
hand before zipping, or not shipping it at all) were offered and declined.
The repo is private and the distribution is intra-studio. The folder ships
**whole** — MEL, `misc/`, `icons/`, manuals and `License.txt` — because
clause 4 forbids removing proprietary notices, and because `misc/` is a
runtime dependency of the panel, not documentation.

## Two code changes

Both follow one rule: **shipped copy first, the user's legacy absolute path
as fallback**, so the same code works in the repo, in an installed copy, and
on the user's machine before `assets/`/`overrig/` exist.

- **`maya_scenesetup/catalog.py`** — the sword's path is computed at import:
  `<container>/assets/LongSword_02.fbx`, where `<container>` is two dirnames
  up from `catalog.py` (true in the repo and in the installed copy alike);
  if that file does not exist, the legacy
  `C:/!!!Work/Animations/Sources/LongSword_02.fbx`. The `Weapon` table and
  everything downstream — `missing()`, attach, offsets — are untouched,
  because the table still holds a plain absolute path. `catalog.py` stays
  stdlib-only.

- **`maya_overrig/overrig.py`** — `MEL_PATH` becomes the first existing entry
  of a candidate list: `<container>/overrig/base_OverRig_scripts.mel`, then
  the legacy `C:/!!!Work/Animations/Scripts/...` path. `NOT_LOADED_MESSAGE`
  names both places it looked. `ensure_loaded()` keeps sourcing only — the
  panel button sets the MEL globals itself, and our procs never needed them.

## Icons

32×32 PNG with transparency, drawn to read on Maya's dark shelf: flat glyphs,
~2 px strokes, one accent colour per tool.

- **Picker** — a miniature of the body map itself: circle head, dot buttons
  down the torso and limbs. Cyan.
- **UE Bridge** — a clip plate with frame ticks and an arrow coming *into*
  the scene: an import. Orange.
- **Scene Setup** — a sword: blade, crossguard, grip. Steel white.
- **Overshoot** — a curve overshooting a dashed target line and settling,
  with a key dot. Green.

`icons/make_icons.py` draws them with QPainter under mayapy
(`QT_QPA_PLATFORM=offscreen`, the repo's established headless-Qt route) and
saves the PNGs, which are committed. The generator is committed next to its
output so the icons can be regenerated and restyled. The rendered set goes to
the user for approval before the installer work is called done; the motifs
above are the starting point, not a contract.

## `install.py` structure

One file, because at drop time nothing of ours is on `sys.path` — it can
import only the stdlib at module level (`maya.cmds`/`maya.mel` imports live
inside the functions that run in Maya). The fiddly parts are pure functions
in the repo's house style:

- `payload()` — the whitelist, as data.
- `button_specs(dest)` — the five buttons as data: label, annotation, icon
  path, command string, sourceType. All path-baking happens here.
- `install()` — the Maya-touching orchestration: copy, shelf, dialog.
- `onMayaDroppedPythonFile(*args)` → `install()`.

## Verification

- **Unit tests** (`tests/test_install.py`, mayapy + unittest): every payload
  entry exists in the repo; button commands contain the destination path, the
  right import and the right call; the OverRig command carries both globals
  and the `misc/` path; `catalog` resolves the sword next to itself when the
  file exists and falls back when it does not; `overrig` prefers the shipped
  MEL. Pure functions only — no Maya session.
- **Live** (`docs/superpowers/plans/verify_install.py`, through the bridge):
  run the real install into the user's Maya; assert the folder landed with
  the whitelist and nothing else, the shelf exists with five buttons, each
  button's command string executes (windows open), and
  `catalog.missing()` is empty for the sword resolved from the installed
  copy. Respect bridge notes 5–8 (idempotent runner, no SystemExit).

## Out of scope

An uninstaller (delete the folder and the shelf tab by hand), version checks
or auto-update, a `.mod` module, Maya versions older than the studio's 2027,
and any change to how the tools themselves behave once open.
