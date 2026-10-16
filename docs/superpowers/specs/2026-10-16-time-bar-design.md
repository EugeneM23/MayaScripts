# Time Bar: Maya's time slider redrawn in the hub's look (2026-10-16)

The animator: «Давай попробуем перерисовать интерфейс таймслайдера маи под наш стиль. Сделай пару
макетов а я выберу». Three mockups (https://claude.ai/artifact/JS83VQsVewRHtnmjWBnwWZ): A one bar, B
Maya's two rows tidied, C a strip with lanes. Chosen: **A, one bar**, **in place of Maya's** (Maya's
Time Slider and Range Slider hidden, a ⋮ row brings them back), and of Maya's slider behaviours only
the **shift-drag highlight** kept in the first version (not moving / scaling keys, not the right-click
key menu, not the sound waveform).

## What it is

Package `SkeldarAnim/maya_timebar/` (a payload row):

- `look.py` (stdlib, pure): frame <-> x, the ticks a width can carry, what a press hits (playhead,
  the playback band's two handles, the animation range's two grips), the highlight from a drag, the
  previous / next key, the fps table.
- `bar.py` (Qt): the strip, drawn with QPainter in the hub's tokens.
- `scene.py` (cmds): reads the time, the two ranges, the selection's keys and breakdowns, the fps,
  autoKey, the animation layers and the highlight; writes them; the jobs that keep the strip current.
- `__init__.py`: the workspaceControl `skeldarTimeBar`, show / hide, `active()`, `highlight()`. It
  imports no Qt and no cmds at import.

## The strip (44 logical px)

Left to right: previous key, play / pause (orange), next key; the timeline; the current frame field;
the fps chip (24 / 25 / 30 / 48 / 50 / 60, `currentUnit -time`); Auto key (red dot when on); the active
layer chip (BaseAnimation or the selected layer; its menu picks a layer).

The timeline shows the **animation range**. The **playback range** is the lit band, its two edges are
handles you drag; a double click on a handle asks for a number. A small grip at each far end changes
the animation range. The selection's keys are orange ticks, breakdowns cyan; the playhead an orange
line with its frame on a flag.

- A left press or drag scrubs (and clears a highlight).
- **Shift-drag** highlights `[a, b]`; it is written to `playbackOptions -selectionStartTime /
  -selectionEndTime / -selectionVisible` (editable in Maya 2027, measured in mayapy), the shared
  model Maya's own slider most probably reads too. The strip draws whatever that model holds.
- Play runs Maya's own `play`, so real-time playback, the speed and the loop stay Maya's.
- The right button on the strip: «Back to Maya's time slider».

## In place of Maya's

`show()`: the control docked against `TimeSlider` (above it; at the bottom of the main window when
there is none), then `TimeSlider` and `RangeSlider` hidden. `hide()`: Maya's two shown again, ours
hidden. Remembered in the optionVar `skeldarTimeBar` (on by default). The hub's build shows it (as it
shows the tabs bar); ⋮ → **Time bar** (checked = ours) switches; hotkey row `window.timebar`.

## Our tools and the highlight

`overrig.slider_selection()` - which feeds Layer, the knots, FK/IK, Connections, Ragdoll and the Pose
Library - and Camera Shake's `highlight()` read the time bar's highlight while it is on
(`maya_timebar.highlight()`, `[a, b + 1)` as `timeControl -rangeArray` answers). Otherwise unchanged.

**Not known yet**: whether Maya's own commands (Bake Simulation "time slider", the slider's copy /
paste) and OverRig's MEL, which read `timeControl -q -rangeArray` on the hidden slider, see the
`playbackOptions` selection. That needs a GUI Maya, the animator's check. If they do not, those
commands run with no highlight while the time bar is on.

## Keeping it current

scriptJobs parented to the control: `timeChanged` (only the playhead and the field repaint),
`playbackRangeChanged`, `SelectionChanged`, `animLayerRefresh`, `Undo` / `Redo`; an
`MAnimMessage` keyframe-edited callback marks the keys dirty; a 250 ms timer catches what no event
reports (autoKey, the fps, the highlight). During playback the keys are not read again.

## Tests

`tests/test_timebar_look.py` (the geometry, ticks, hits, highlight, keys navigation),
`tests/test_timebar_bar.py` (the strip offscreen on a fake scene: painting, a scrub, a shift-drag, the
handles). `docs/superpowers/plans/render_time_bar.py` draws it at 150 % into `time_bar.png`. The live
check - docked in place of Maya's, playback, the highlight seen by Maya's own commands - is the
animator's.
