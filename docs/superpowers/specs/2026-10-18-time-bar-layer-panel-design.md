# The Time Bar's layer panel

2026-10-18. The animator: «Давай мы удалим с нашего таймлайна кнопки который делают book marks и
вместо этих кнопочек добавим кнопочку которая будет открывать и закрывать выдвижную панель с
слоями. Панель эту давай нарисуем свою по нашим правилам».

Three variants were shown as live mockups (https://claude.ai/artifact/VPbk5HvyxNMuw6jZv1hc5u,
version 1): A a column over the button, B lanes on the timeline, C a chip row. The animator took
**A** and changed it (version 2 of the same page):

- «передвинем меню слоев в правую часть таймлайна»: the column stands at the bar's right;
- «второй раздел в этом окне с слоями видимости»: a Display section beside Animation;
- «растягивать это окошко потянув за верхний край»: the top edge resizes it;
- «опциональную кнопку которая будет выдвигать панель как в варианте B»: a lanes button.

Then: «Макет подходит, пиши спек и план».

Everything here follows `docs/interface-motion.md` (the Time Bar's style is the rule).

## 1. What changes on the bar

- **The three bookmark pills go**: `bm_prev`, `bm_add`, `bm_next`, their handlers and their glyphs.
  - The bookmarks themselves stay: the band on the timeline and «Add bookmark» in the key menu.
  - `scene.add_bookmark` and `scene.bookmarks` stay. `scene.step_bookmark` goes with its button.
- **A layers pill** (`Strip.layers_btn`, glyph `layers`, a toggle) stands in the right group, after
  Auto key and a divider, before the preferences gear.
  - It is lit (`on`) while the panel is open.
  - A badge on it reads the number of animation layers, BaseAnimation included (none: no badge).
- **The layer chip** (`Strip.layer`) keeps its text: the layer keys go to. Its click opens or closes
  the panel too. Its menu (`layer_rows`, `_layer_menu`) goes.

## 2. The column

A window of its own: a frameless translucent `Qt.Tool` child of Maya's main window, above Maya,
never above another application, gone with Maya minimized. Its object name is
`skeldarTimeBarLayers`. It is painted by us (Pill-style controls, no Maya widgets), except one
QLineEdit made only while a name is being typed.

**Where it stands**:
- Its right edge on the strip's right edge less 6 logical px; its left edge on the timeline's right
  plus 6. So it stands over the frame field and the transport, at about 320 logical px.
- Its bottom 6 logical px above the strip's top.
- It follows the strip every 300 ms while open (the strip moves with its host in Bottom edge mode,
  with Maya's window in both modes).

**Its height**:
- Default 268 logical px. At least `MIN_H` 150.
- At most from the strip's top to the top of Maya's viewport area (`MainPane`'s top, as the side
  panel reads it) less 10.
- The top edge is a grip, 9 px tall: the cursor `SizeVerCursor`. A drag changes the height at once.
  The bar under it is lit in the accent while hovered or dragged.
- Remembered in optionVar `skeldarTimeBarLayersHeight`.

**Top down**:
- **Head**: the segments `[Animation n | Display n]` (the hub's segment look: a recessed track, the
  lit segment a raised thumb). On the right the **lanes** button (glyph `lanes`, a toggle, disabled
  on Display). The tab is remembered in `skeldarTimeBarLayersTab`.
- **List**: a recessed well (`field`, `track_edge`); one 30 px row a layer, 3 px apart; it scrolls
  (wheel; a thin painted scrollbar while it overflows).
- **Foot**: the primary **+ Layer** (orange, the one orange of the column), then icon buttons.

### 2.1 Animation

The active scene tab's animation layers, top to bottom as Maya's Layer Editor shows them: the
newest first, BaseAnimation last. With scene tabs, a tab's own root reads «BaseAnimation» and the
session's holders are never shown (`maya_scenetabs` rules, as `scene.layers` reads them today).

A row: the mode badge (`ADD`, `OVR`, `BASE`), the name, the weight (a track with an accent fill,
the value in Consolas), then **M** (mute), **S** (solo), the **lock**.
- BaseAnimation has no weight and no solo.
- A muted layer, or one left out by another's solo, is drawn dimmed with its name struck through.
- **The active row** (the layer keys go to: the last selected non-base layer, else BaseAnimation,
  `scene.layer_label`'s rule) is `card_active` with a 1.5 px accent outline and its name in
  `accent_text`.
- A click on a row makes it the active layer (`scene.pick_layer`).
- A drag on the weight sets `.weight` as it moves, one undo chunk from press to release. A weight
  with a time curve is keyed at the current frame instead.
- The right button: Additive / Override, Rename, Select objects, Add selection, Remove selection,
  Merge down, Delete.

The foot: **+ Layer** (a layer from the selection; an empty one with nothing selected), Add
selection, Remove selection, Merge (the active layer into the one under it), Delete (the active
layer; BaseAnimation never).

### 2.2 Display

Maya's display layers of the active scene tab (`defaultLayer` never), in the Layer Editor's order.

A row: the layer's colour swatch, the name, **V** (visibility), **P** (shown in playback, the
inverse of `hideOnPlayback`), the display type (`–` normal, `T` template, `R` reference; a click
steps it).
- A hidden layer is dimmed.
- A click on a row picks it for the foot's buttons; the picked row is lit as the active one is.
- The right button: Rename, Colour (Maya's palette), Select objects, Add selection, Remove
  selection, Delete.

The foot: **+ Layer** (from the selection), Add selection, Remove selection, Select objects,
Delete (the picked layer).

### 2.3 Every write

- Is Maya's at once and one undo chunk (`skeldarTimeBarLayers`). Only the picture animates.
- A refusal is said on the column's own line under the foot (a one-line status, faded after 4 s),
  never in a dialog.
- The column reads the scene again on `animLayerRefresh`, `SelectionChanged`, `Undo`, `Redo`, the
  display layer events Maya has (`displayLayerChange`, `displayLayerManagerChange`,
  `displayLayerAdded`, `displayLayerDeleted`, `displayLayerVisibilityChanged`), and on the strip's
  250 ms tick only while open. It repaints only when what it read changed (a signature of names and
  values).

## 3. The lanes

A second painted window, `skeldarTimeBarLayerLanes`, out only while the column is open, the
Animation tab is shown and the lanes button is on (optionVar `skeldarTimeBarLayerLanes`, off by
default).

- It spans from the timeline's left to the column's left, the same height as the column.
- A ruler at the head, on the timeline's frames.
- **One lane a row, at the row's own height**; the list's scroll moves the lanes with it.
- A lane shows the keys the **selection** has **in that layer** (its curves found through
  `animLayer -findCurveForPlug`; BaseAnimation's are the base curves), on the timeline's frames,
  drawn as the timeline draws keys (a cell, `key_cell`). The active lane's keys are orange, the
  others `muted`, BaseAnimation's `faint`; a dimmed row's lane is dimmed.
- The playhead's cell runs through every lane.
- A click on a lane makes its layer active.
- Read again on `SelectionChanged`, on a key edit (the strip's keys-dirty callback) and on
  `animLayerRefresh`, only while out.

## 4. Motion

The Time Bar's own numbers, imported from `maya_timebar.look` (never copied):

| moment | what |
|---|---|
| the column opens | its shape unrolls out of the layers pill (`UNROLL_MS`, ease_out_quint), its parts pop in nearest the pill first (`popping`, `burst_delay`), the reveal's top-edge light (`REVEAL_MS`) |
| the column closes | its parts fold farthest first (`folding`, `fold_delay`), the shape closes onto the pill (`CLOSE_MS`, `CLOSE_AFTER_MS`) |
| the lanes come out / go | the same, out of and into the column's left edge at the head's height |
| a tab switch | the new list's rows pop in a wave from the lit segment |
| a layer added | its row pops in (`popping` at delay 0) |
| a layer deleted | the data at once; its row's picture folds (`folding`) where it stood |
| a toggle (M, S, lock, V, P, T/R, lanes) | `POP_MS` |
| hover on any control or row | `HOVER_MS`, +`LIFT`, the glow rings |
| a press | `FLASH_MS` |

- The parts are the head's segments and the lanes button, each row, each foot button.
- A "part" is drawn from its age (scale, opacity) on the static picture of the column; the
  column's still picture is cached and drawn again only when its key changes (size, tab, rows,
  values, scroll, scale).
- One 16 ms driver for both windows, stopped at rest.
- ⋮ → Interface animations off: open, close, waves and pops land at once, no effect is made.
- The column and the lanes are drawn whole while Maya plays; nothing in them follows time but the
  lanes' playhead cell, repainted from the strip's time callback (`repaint()`, trap 269).

## 5. With the rest of the Time Bar

- **Bottom edge**: while the column is open, `BottomEdge.blockers()` answers `"layers"`, so the bar
  does not hide. The bar hidden by other means (Maya's mode, a tab switch) closes the column at once.
- **Docked**: the column follows the docked control's strip.
- **Maya's own slider** (`mode() == "maya"`): no strip, no pill, no column.
- The column and the lanes are obstacles neither for the bar nor for the side panel: they stand
  over the viewport, above the bar's band.
- `drop_edge` / a rebuild of the strip destroys both windows by name (`destroy_all`, trap 102).
- Every window and every Maya widget is found again by name when needed, never kept (trap 135).

## 6. Code

| file | holds | imports |
|---|---|---|
| `maya_timebar/layerlook.py` | the column's and the lanes' layout as pure functions: rects of the head, segments, rows, a row's controls, the foot, the grip; `hit(x, y)`; the height clamp; row order; the display-type step; the signature; the wave schedule over `look`'s functions | stdlib, `look` |
| `maya_timebar/layerscene.py` | reads (animation layers with their values, display layers, keys per layer for the selection) and writes (pick, mute, solo, lock, weight, mode, rename, create, add, remove, merge, delete, select; V, P, type, colour) | `maya.cmds`, `maya.mel` lazily |
| `maya_timebar/layerpanel.py` | `LayerColumn`, `LayerLanes`, the controller (`toggle`, `place`, `refresh`, `destroy_all`), the driver | Qt through `bar.classes()`'s helpers |
| `maya_timebar/bar.py` | the bookmark pills out, the layers pill in, the chip opens the panel, the strip's jobs and tick feed the panel | |
| `maya_timebar/edge.py` | the `"layers"` blocker | |

The panel talks to Maya only through a link object (`layerscene` in Maya, a fake in the tests), as
the strip does.

## 7. Proof

1. **Unit tests**:
   - `tests/test_timebar_layerlook.py`: the layout at 1.0 and 1.5 scale, hits, the height clamp,
     the row order, the type step, the wave's order and its last start, a subprocess check that
     the module imports no Maya and no Qt;
   - `tests/test_timebar_layerscene.py` on a fake `cmds`: the reads, scene-tab scoping, every
     write in one chunk, refusals (BaseAnimation's delete, solo or weight; merging the last layer);
   - `tests/test_timebar_layerpanel.py` offscreen on a fake link: the pill and the chip open and
     close it, the tab, a row click, M / S / lock, a weight drag, the grip, the lanes following the
     scroll, the right-button rows, the burst drawn from age (a small shape at the pill mid-way, a
     far pixel empty), no picture rebuilt during a hover, animations off at once;
   - `tests/test_timebar_bar.py` updated: no bookmark pills, the layers pill and its badge, the
     chip's click.
2. **`docs/superpowers/plans/verify_timebar_layers.py`**, mayapy standalone: every write of
   `layerscene` on a real scene (a cube keyed on the base and two layers; display layers), the
   values read back, Merge (Maya's own procedure, found and measured before it is built on), keys
   per layer for the selection exact, one undo per press, the scene tabs' scoping.
3. **A filmstrip**: `docs/superpowers/plans/render_timebar_layers.py` → `timebar_layers.png` (the
   column opening, both tabs, the lanes out, a resize).
4. **A bench**: a column of 12 layers, a hover sweep and a scrub with the lanes out; our share of a
   frame against `docs/interface-motion.md` section 5.
5. **Not in a GUI Maya** unless the animator says so: the summary says «not seen in a GUI Maya».

## 8. Checklist (`docs/interface-motion.md` section 8)

- [ ] The column opens out of the pill and closes into it: in nearest first, out farthest first.
- [ ] Every part moves on its own, within section 3's durations.
- [ ] Hover 110 + 10 % + glow; press flash 120; toggle pop 200.
- [ ] Effects are added light, where their thing is.
- [ ] The data changes at once; only the picture is animated.
- [ ] Colours from `TOKENS` only; one orange in the column; lengths × `ui`.
- [ ] Numbers in a stdlib module, imported from `maya_timebar.look`.
- [ ] Drawn from age; one 16 ms driver that stops at rest; the still part cached.
- [ ] Playback: the lanes' playhead repainted from the time callback.
- [ ] Interface animations off: the same end state at once, nothing created.
- [ ] A paint error prints once; no Maya wrapper kept; no `grab()`.
- [ ] Measured against section 5.
- [ ] Unit tests + offscreen pixels + a filmstrip; «not seen in a GUI Maya».

## 9. Not built

Nested animation layers shown as a tree (they are listed flat in Maya's order, a child after its
parent); dragging rows to reorder layers; ghosting; the rotation and scale accumulation modes;
keying the weight by a button (the drag keys it only when it is keyed already); display layers on
the lanes.
