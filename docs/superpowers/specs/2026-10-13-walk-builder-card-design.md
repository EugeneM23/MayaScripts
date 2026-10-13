# Walk Builder: the parametric walk as a hub card (2026-10-13)

The animator: «Пуш, сделай сборку. Давай встроим этот скрипт в наш плагин. Интерфейс рисуй компактным».
The standalone tool of `docs/superpowers/plans/walkparam/` (a window, dropped into a viewport) moves into the
plugin as a card, the way the physical stop became Tail Builder on 2026-10-12.

## Where the code goes

`SkeldarAnim/maya_walk/`, a package (a payload row), the files moved with `git mv`:

| module | was | does |
|---|---|---|
| `model.py` | `walkmodel.py` | the walk's mathematics (numpy only) |
| `files.py` | `walkfile.py` | a saved walk / pose (gzip JSON) |
| `target.py` | `walktarget.py` | a walk carried onto any skeleton (posemath + IK legs) |
| `pose.py` | `walkpose.py` | a character pose under the walk |
| `scene.py` | `skeldar_walk.py` without its window | save, load, apply, the marker, the keys |
| `panel.py` | new | the hub card |

The modules import each other relatively; `maya_walk/__init__.py` imports none of them.
`verify_walk.py` and the pictures stay in `walkparam/` and load the plugin's package. The drop-in window is
gone. The marker `skeldarWalk` (version 2) is unchanged, so walks applied with the standalone window are read
by the card.

## Where the walks live

`<userAppDir>/SkeldarWalks` (`scene.folder()`), outside the plugin folder that an install replaces. The
optionVar `skeldarWalkFolder` overrides it, and `scene.WALKS` (a verify's temporary folder) overrides both.
The animator's walks and poses were copied there from `walkparam/walks/`. Walks do not ship: they are the
animator's data, from clips of unknown licence.

## The card, compact

```
dw on root, ... (subtitle: the selection, else the target)
Walk [dw            v] [floppy]
Pose [two_handed    v] [floppy]
Pose ------o------- 1.00
(Torso)(Pelvis)(Knees)(Arms)(Feet)
[ Apply ][ Reset ]
[Step|Legs|Pelvis|Chest|Arms|Weight]
  the shown group's knobs (3-7 sliders)
status (three lines)
```

- **One knob group shown at a time**: segments over six columns, one managed. The group shown is remembered.
  Pose's share stands under its dropdown, so the groups hold every other knob.
- **No Pick button**: selecting a skeleton that carries a walk (`scene.selected_top`, cheap: a joint, or a
  mesh's skin) reads its walk, pose, parts and knobs into the card, and it becomes the target. A target
  already selected is not read again: the card is the truth while the animator tunes it.
- **Apply** puts the card on the selected skeleton (the rig refusal, the rest rule, one undo), which becomes
  the target. **A released knob, a pose, a part re-keys the target** (persistent, as in the window).
  **Reset**: every knob at its default (the tempo the walk's own), the target re-keyed.
- Save walk / Save pose are the floppy icons (a name prompt). A right click on either dropdown offers "Show the
  walks folder" and "Read the lists again".
- Filling the card from the scene is quiet (`_QUIET`): an optionMenu's value set by code fires its
  changeCommand, and that must not re-key.
- Everything is remembered in `skeldarWalk_*` optionVars (walk, pose, parts, group, `knob_<name>`), so a
  rebuilt card comes back as it was and a hotkey row presses with the card closed.
- The apply line is shortened for a three-line status.

## The hub

- Section `walk`, «Walk Builder», Animation, after Tail Builder, Tabler `walk`. `device-floppy` is new too.
- Hotkey rows: `window.walk` (open) and `walk.apply`.
- A popup copy of the card has its own selection job (`JOB` by scope tag, Tail Builder's rule). The target is
  the session's (on `sys`).

## Proof

- `tests/test_walk_panel.py`, the card on a fake cmds:
  - the controls and their roles;
  - one group at a time, remembered;
  - Apply reading the card;
  - a knob re-keying the target, and none without one;
  - a walked skeleton read back without keying;
  - the card closed reading the memory;
  - Reset, a failure, one job per card;
  - the section, the icons, the payload, the hotkey rows, a light package import.
- The model and target suites on the package.
- `verify_walk.py` 73/73 standalone on the package.
- The live card is the animator's to see after Check update.
