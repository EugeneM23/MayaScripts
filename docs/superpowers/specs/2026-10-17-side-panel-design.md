# Side panel: the Channel Box / Layer Editor and the Attribute Editor at the right edge (2026-10-17)

The animator: «Давай попробуем реализовать боковую панель по концепту нашего таймлайна, только для
chanalbox/layer editor и атрибут эдитор» - then «Сделай все до конца на свое усмотрение я вернусь
через часик и проверю». Every choice below was taken alone.

## What it is

The Time Bar's bottom-edge mode turned on its side: Maya's right dock (where the Channel Box /
Layer Editor and the Attribute Editor stand) is emptied, the viewport takes the whole width, and a
panel in the hub's look slides out of the RIGHT edge of Maya's window when the cursor rests there.

- **Inside it are Maya's own editors, not copies.** A second channelBox would work, but the Layer
  Editor and the Attribute Editor are MEL machinery built around fixed names
  (`MainChannelsLayersLayout`, `MainAttributeEditorLayout`); a redrawn Attribute Editor is out of
  reach. So the panel BORROWS Maya's two form layouts (the Graph Overlay borrowed `graphEditor1`
  the same way): their Qt widgets are moved into the panel, their workspaceControls hidden, and on
  the way back each form goes into the very parent it came from. Every lookup is by name, every
  time (trap 135).
- **Two tabs**: `[Channels | Attributes]` in the panel's header, remembered
  (`skeldarSidePanelTab`). Channels holds `MainChannelsLayersLayout`, or, with Maya's
  "channels and layers separate" preference, `MainChannelBoxLayout` over `MainLayerEditorLayout`.
- **Maya still thinks they are shown.** The Attribute Editor refreshes only while
  `isAttributeEditorVisible()` answers true (showEditor.mel, refreshAE.mel) - and Ctrl+A or a
  double click calls `showEditor`, which would restore the empty workspaceControl. While the panel
  holds a form, `isAttributeEditorVisible` and `isChannelBoxVisible` are redefined to say so
  (`maya_sidepanel.holder.install`); off, Maya's own files are sourced again.
- **Maya's own toggles open ours**: a held editor's workspaceControl made visible again (Ctrl+A,
  Windows > ..., the Channel Box toggle) is hidden at once and the panel comes out on that tab,
  held until the cursor has visited it and left (the hub edge panel's `Hold`).

## The time bar's concept, on the right

- the band: the right of Maya's client area, its full height, `WIDTH` 340 logical px (260..700),
  dragged wider by a grip on its inner edge, remembered (`skeldarSidePanelWidth`);
- comes out: the cursor resting `ZONE_DWELL_MS` in a `ZONE_PX` (14 logical px) strip along the
  right edge, or on the 2 px sensor; never with a button held, Maya not active, or another window /
  a menu over it;
- the reveal unrolls the panel from the cursor's height (the Time Bar's `unroll`, vertical), the
  close rolls it back onto it; ⋮ -> Interface animations off: at once;
- stays out while pinned (📌 in the header), the cursor over it, a button down, a menu or dialog
  up, or a text field in it has the keyboard focus (typing a value in the Channel Box or the
  Attribute Editor); goes `HIDE_MS` 1200 after the cursor left.

## Modes

⋮ -> **Side panel ▸ Maya's / Right edge** (`skeldarSidePanelMode`, **Maya's by default**: the borrow
of Maya's own editors has not been seen in a GUI Maya, so it is opt-in until the animator has tried
it). Maya's gives every form back and sources Maya's procs again. The hub's build calls `ensure()`
(deferred, guarded) so the mode comes back at Maya's start. Hotkey rows `window.sidepanel` (switch),
`sidepanel.channels`, `sidepanel.attributes` (out on that tab, held).

## Not built

A panel at the left, our own drawing of the Channel Box, the Outliner or Tool Settings in it.

## Proof

Unit tests offscreen (the band and the zone, coming out and going back, the pin, the grip, a held
reveal, the tabs, the borrow plan for both Maya preferences, the redefined MEL procs' text, the
menu row). The borrow itself, Maya's editors refreshing inside the panel and Maya's toggles are
GUI-only and are the animator's to check.
