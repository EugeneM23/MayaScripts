# Pose Library: compact, Selected only, toned cards, a blend that holds (2026-10-15)

The animator: «Pose library нужно доработать. 1 - давай сделаем более компактный интерфейс. 2 - у
нас должна быть опция применить наложение только на выделенные объекты. Мы в нашей позе должны
найти информацию только о том что имеет отношение к нашему текущему выделению и применить только
это. 3 - Превью поз должно быть оранжевым, а превью анимаций приятно холодно голубым. 4 - ручка
blend должна оставаться на своем месте и переводить позу в нужное состояние но ключ должен
ставиться только по нажатию apply. Если мы изменили таймлайн или куда-то переключились то пусть
бленд сбросится на 0».

Asked, all three the recommendation:
- the tone is **the picture recoloured** (dark to the tone's dark, the viewport's grey to its
  middle, white to its light), not only the background and not a frame;
- **Selected only keys only the selected nodes**, each at its value in the whole card (FKWrist
  selected: FKWrist alone, the IK hand untouched);
- **Apply at blend 0 keys the whole card**; above 0 it keys that share.

## 1. Compact

- One row on top: search, type, sort, card size, + Save, ⋮. No title row (the control's tab says
  «Pose Library»); the library's folder is the ⋮ button's tooltip and its menu's first row
  (`path_label` is kept, hidden).
- Margins 4, spacing 4; the tree 140 px (at least 100); the side panel 260 (at least what its
  content needs, `_fit_side`, read once the stylesheet sized it).
- The details picture 150 px (was 220); the info lines `note`-sized; Apply with **Select objects
  as an icon** beside it; Mirror and Selected only on one row; the Blend row.
- The paste options: the three checks (At current time, Connect, In place) on one row, Keys beside
  its segments.

## 2. Selected only

A checkbox beside Mirror (`skeldarPoseLibrarySelectedOnly`, off by default, remembered).

- `apply.apply(..., only=True)` / `Blend.start(..., only=True)` /
  `animapply.apply(..., only=True)` / `animapply.Blend.start(..., only=True)`. Off, every call is
  the call it always was.
- The WHOLE card is solved (`_plan` / `_Target`), then only the plugs of the selected transforms
  are kept (`selected_nodes`: the selection's DAG transforms, long; `keep_selected`, pure;
  `only_selected` names the cut: «Selected only: 1 of 73 controls keyed»). So a child FK control
  takes exactly the value it has in the full pose (Studio Library's per-control rule), and a
  selected bone of a skeleton its own joint channels.
- Nothing measured when the cut left some of the members' nodes out.
- None of the selected nodes in the card: refused before any chunk («Selected only: the card poses
  none of the selected controls»).
- An animation card keeps the same plugs on every frame.
- A drop onto a character or the floor names its character, so it takes the whole card. An objects
  card keys the selected objects anyway.

## 3. The backdrop a card is shot on

**First built wrong and pushed (bf7d386)**: the pictures recoloured at paint time, an orange /
blue overlay over the whole card. The animator: «Мы должны делать превью с разным фоном для поз
оранжевый для анимаций голубой а не закрашивать всю карточку каким-то оверлеем». The overlay is
gone (`look.TONES`, `cardgrid.toned`, `canvas.tones`).

What stands: `capture.backdrop(kind)` sets the viewport's background for the length of a blast -
`displayRGBColor background / backgroundTop / backgroundBottom` to `capture.BACKDROPS[kind]`
(pose (0.86, 0.47, 0.19) orange, anim (0.33, 0.60, 0.83) blue) and the gradient off (a playblast
takes the flat colour) - each read first and put back, whatever happened. `capture.thumbnail(path,
kind=)` shoots the still in it; `animcapture._blast` shoots the preview sheet on blue. The save
panel shoots on its type's colour and again when Pose / Animation is switched; Replace thumbnail
(and preview) by the card's type. The character is shot as it stands. Cards saved before keep
their grey picture until Replace thumbnail.

**The studio light** (the same day: «Добавь красивый градиент на фон или студийный свет»): a
playblast takes only the flat background colour, but a PNG playblast keeps the background
transparent (Viewport Studio's measurement). So `capture.blast_options` writes PNGs and each still
and preview cell is laid over `capture.studio(qt, image, kind)`: a radial light centred a little
above the middle (the colour 42 % toward white), the colour at half its reach, the corners at
38 % of it, a faint floor glow. A blast with no alpha shows the flat backdrop colour as before.
Picture `docs/superpowers/plans/poselib_studio_backdrop.png` (a still keyed by hand to stand in
for a PNG blast).

## 4. The blend holds; Apply keys it

- The slider, or a middle drag across a card (which picks it, the slider showing the share),
  previews unrecorded, as before. **Let go, the preview stays**: «Blend 40 % - Apply keys it»;
  Apply reads «Apply 40 %».
- **Apply** with a blend above 0 on the picked card keys that share (`blend_key` →
  `scene.blend_finish`) and the slider goes to 0. At 0 (or a different card, or the menu's
  mirrored Apply) the blend is put back quietly and the whole card keyed.
- **Back to 0, every value back** (`blend_reset(why)`, the line says why): the time changed (a
  `timeChanged` job made only while a blend stands, the reset one idle later), the selection
  changed (`follow`: SelectionChanged, Undo, Redo, a scene opened), another card picked, Mirror /
  Selected only / a paste option changed, the library hidden (a docked tab behind another, the
  hub switched). Esc too. A drop puts it back and drops the whole card.
- Let go at 0: no blend. A lost release (Alt+Tab mid-drag) is a release: the preview kept.
- No keyboard grab any more: a blend can stand for minutes, and Maya's hotkeys must reach Maya.

## Proof

- Unit tests (offscreen Qt and fakes): 1123+ Pose Library tests, among them `BlendHolds`,
  `SelectedOnlyOption`, `Compact`, `Backdrop`, `test_poselib_backdrop`, `SelectedOnly`, `SelectedOnlyPress`.
- `docs/superpowers/plans/verify_poselib_selected_only.py` — **13/13 mayapy standalone**:
  - a Manny_Rig card onto another: FKWrist_R alone keyed, at the whole solve's value to 0.0;
  - FKShoulder_L + FKElbow_L alone;
  - a hand card with a leg control selected refused, nothing keyed;
  - a Blend at 50 % on FKWrist_R: it alone, halfway (mix exact);
  - without the option, 73 controls;
  - an animation onto FKElbow_R alone on 40..52, equal to the whole paste's onto a third rig to
    1.6e-5;
  - the Manny skeleton's hand_r alone.
- Picture: `docs/superpowers/plans/poselib_compact.png` (offscreen, the window over a temp library
  of the animator's own thumbnails, a blend held at 35 %).
- Not seen live (the animator's checks): the window in Maya, the time job's reset on scrubbing,
  a real playblast on the backdrop (mayapy standalone has no viewport).
