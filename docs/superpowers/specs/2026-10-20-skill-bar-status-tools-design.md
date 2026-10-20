# Maya's status-line tools on the skill bar's page row (2026-10-20)

The animator, with a screenshot of Maya's status line (the object masks, Lock, Highlight, the
snaps): «давай реализуем интерфейс и функционал этой панели самостоятельно и перенесем ее на наш
тайм бар горячих клавиш F». Asked where: **on the F row, at its right**. Mockups
(https://claude.ai/artifact/1KJ721Rcme6cgJAAqz6xoM): A inline icons, B captioned tracks, C a
mask pill; they chose **A**.

## What

At the right of the page row (F1..F12), on every page, the bar's height unchanged:

- **the selection masks of the current selection mode**, as Maya shows them: object mode Handles,
  Joints, Curves, Surfaces, Deformers, Dynamics, Rendering, Misc; component mode Points, Parameter
  points, Lines, Faces, Hulls, Pivots, Handles, Misc; hierarchy mode Root, Leaf, Template.
  A click flips the group as Maya's button does (a partial group is "on", so a click turns it
  off). A group partly on is drawn unlit with an accent dot. The right button lists the group's
  own types with their check marks (Maya's `createMaskPopup`, filled into Maya's popup and read
  back, so the rows are Maya's own);
- **Lock selection** (`selectPref -xformNoSelect`) and **Highlight selection**
  (`selectPref -allowHiliteSelection`, pressed while highlighting is OFF, as in Maya);
- **the snaps**: grid, curve, point, view plane, projected center (`snapMode`);
- **Make Live**: click `statusLineSetMakeLive`; the right button Add / Remove selection, Toggle.

## How

- `maya_skillbar/status.py` (stdlib, a test pins it): the table (each button's Maya control and
  command), 24-grid outline icons, the layout packed against the row's right edge with hairlines
  between groups, the pure state rules, `MemoryStatus`.
- `maya_skillbar/statusscene.py` (cmds / mel): `MayaStatus.read()` takes each mask off Maya's own
  status-line control (`iconTextCheckBox -q -v / -image1`, `*Partial.png` = partial): Maya's
  permanent scriptJobs keep those in step, so the state is Maya's own reckoning. No status line:
  the group's primary `selectType` flags. `press` runs the control's command; `menu` / `run` the
  right button's rows (`#1` replaced by the row's new value).
- `maya_skillbar/grid.py`: `StatusTools`, a child of `PageTabs` sized to its buttons at the row's
  right; the tabs leave it `room()` (they fold to keys first). It reads the model every 250 ms
  while shown and after each press, repainting only on a change; a mode change places it again.
  The model: the strip's `status_model` if any, `MayaStatus` for the real `Link`, else memory.
- Look and motion are the Time Bar's (`docs/interface-motion.md`): a lit button is the current
  tab's face (`card_active` with an accent outline), hover lifts 10 % with the glow, a press
  flashes, a toggle pops, the burst and the opening as every strip part. Data at once.

## Not built

Maya's selection mode buttons themselves, the hierarchy-mode presets, symmetry, the status line's
other sections.
