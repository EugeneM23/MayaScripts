# Our Channel Box, variant A "Rows" (2026-10-18)

The animator: «Давай попробуем сделать свое меню для Chenel box. Предложи несколько вариантов в
стиле нашего таймлайна». Three live mockups were shown
(https://claude.ai/artifact/BSFzRVGoQejgtwHc1VJkzJ): A rows, B vectors, C per-channel tracks.
They picked **A**: «A - строки. Только давай избавимся от мусорной полоски оранжевого цвета по
краям окошка» - the mockup's reveal glow along the panel's edges. So the Channel Box has **no
edge light** of its own; the side panel's own burst (a moving picture) is all it gets on the way in.

## What it is

A painted Channel Box in the side panel's **Channels** tab, above Maya's Layer Editor:

- a head: the lead object's name, a «+N» pill when more objects are selected (an edit goes to all
  of them), and a chip naming the animation layer keys go to (a click: the layers, pick one);
- rows in Maya's order (the lead object's keyable attributes, then its channel-box-only ones),
  a hairline between translate / rotate / scale / visibility / the rest;
- each row: a **key cell** on the left (the Time Bar's key), the attribute's nice name
  right-aligned, a value well on the right in Consolas;
- below: **SHAPES**, **INPUTS**, **OUTPUTS** headers (Maya's own lists, read from its hidden
  Channel Box), each opening its nodes' channels as rows of the same kind.

## The key cell (one look per state)

| state | cell | value |
|---|---|---|
| a key on this frame | filled accent | plain |
| a breakdown on this frame | filled cyan `#6fb7c9` | plain |
| keyed, between keys | accent outline | plain |
| changed since its key (the curve says otherwise) | dashed accent ring | accent text |
| muted | the mute brown, slashed | brown text |
| locked | a lock, faint | faint, no well |
| constrained, expression, driven key, other input | a link in highlight blue | blue text |
| not keyed | a hollow track cell | plain |

## What the hand does

- Click a name: select the channel; Ctrl toggles, Shift extends. The selection is written into
  Maya's hidden `mainChannelBox` (`channelBox -e -select`), so the Graph Editor, S with "key
  selected channels" and every tool reading the Channel Box keep working.
- Drag a name or a value sideways: the virtual slider over every selected channel of every
  selected object - Maya's channel speed (`channelBox -q -speed`) × a step per kind (0.1 a px for
  distances and plain numbers, 1° for angles, 0.01 for scale, a 200th of the range when bounded);
  Shift ×5, Ctrl ×0.2. One undo chunk per drag. Autokey is Maya's.
- Double-click a value: type it; `+=`, `-=`, `*=`, `/=` relative. Enter or leaving the field
  applies it (to every selected channel when the row is one of them), Esc does not.
- Click a bool's value: on/off. Click an enum's value: its names.
- Click the key cell: a key on this frame on that channel of every selected object, or the key
  there taken off.
- The right button: Key / Breakdown / Delete keys at the frame on the selected channels, Mute /
  Unmute, Lock / Unlock, Select connection, Break connections, Copy / Paste values, Channel speed
  (Slow / Medium / Fast: Maya's own setting), and "Maya's Channel Box" (ours off).

## Motion (docs/interface-motion.md)

- Hover: a key cell and a value well lift 10 % and glow (110 ms, `approach`); a row's face goes
  to `hover`. A press flashes (120 ms), a bool pops (200 ms).
- A key set on a row (by us, S, autokey, the Time Bar): the Time Bar's round flash on its cell,
  added light (520 ms). A key taken off: the cell breaks into its 3-5 pieces (700 ms), several in
  the Time Bar's wave. Both found by comparing the rows before and after a refresh on one frame.
- A key the playhead reaches (playing, scrubbing, stepping): its cell lights and fades (600 ms),
  the Time Bar's `passed` rule.
- The data is instant; the picture catches up. One 16 ms driver, stopped at rest. ⋮ → Interface
  animations off: no motion, no effect.
- No edge glow (the animator's word).

## Where it lives and what it costs

- `SkeldarAnim/maya_channelbox/`: `look.py` (stdlib: formatting, typed values, states, groups,
  the row layout, selection, the slider's step), `scene.py` (cmds: the snapshot, the writes),
  `box.py` (Qt: the head, the canvas, the effects layer, the driver), `__init__.py` (mount into
  the side panel, the callbacks, the switch).
- Mounted only while the side panel holds Maya's Channels forms (right edge mode) and the switch
  is on (⋮ → Side panel ▸ Our Channel Box, `skeldarChannelBoxOurs`, on by default). Maya's
  Channel Box half is hidden in place (combined: `ChannelsLayersPaneLayout` shows only
  `LayerEditorForm`; separate: `MainChannelBoxLayout` hidden in our page) and given back as it was.
  Our box and the Layer Editor share a splitter (`skeldarChannelBoxSplit`, remembered).
- Kept current by: SelectionChanged / Undo / Redo / keyframe-edited / attribute-changed
  (on the shown nodes) / time-changed callbacks. A full read costs a few ms on a selection; a
  time change reads only the values and repaints.
- A box that fails to mount prints why and leaves Maya's Channel Box in place.

## Proof

Unit tests for the look (pure), the scene on a fake cmds, the canvas offscreen (paints, hit
tests, selection, a drag's chunk, the effects from a refresh diff) and the mount on stand-in
widgets; a picture rendered offscreen. **Not seen in a GUI Maya** (the live checks are the
animator's): the hidden pane, the `-select` sync, the callbacks.

## Checklist (docs/interface-motion.md §8)

- [x] Every part moves on its own; hover 110 + 10 % + glow; press flash 120; toggle pop 200.
- [x] Effects are added light, where their key is, made of that key.
- [x] The data changes at once; only the picture is animated.
- [x] Colours from TOKENS; one orange per row (the key); lengths × ui.
- [x] Numbers in a stdlib module, the Time Bar's imported.
- [x] Drawn from age; one 16 ms driver that stops at rest.
- [x] Effects on an overlay.
- [x] Playback: the time callback repaints.
- [x] Interface animations off: the same end state at once.
- [x] A paint error prints once; no Maya wrapper kept; no grab().
- [ ] Not seen in a GUI Maya.
