# The montage's hit windows on the timeline, as bookmarks — design

**The animator's ask** (2026-10-29): «давй сделаем так что бы у нас на таймлайн при экспортеиз
монтажа переносились нотифаи в виже book mark», then, asked which notifies: «Melee scan njkmrj /
только мили скан» — the melee scan windows alone. Then «Делай все до конца».

So: importing a montage slot through Animation Setup also puts that montage's **MeleeScanWindow**
notifies on Maya's timeline as time-slider bookmarks, so the animator sees the game's hit window
while animating.

This builds on *Animation Setup: montages, a slot's track as one take* (2026-10-29,
`2026-10-29-montage-slot-import-design.md`). Nothing about the composite itself changes.

## What was measured first

In the animator's own open editor, read-only (nothing written into the project), over **132
montages** — Longsword, Dagger, Block, Hitreacts, Sword/1p, Creep:

- **979 notifies**, 7.4 a montage on average, up to 20. Every montage of the sample has some.
- **They live on the MONTAGE, not in the clips**: of the 115 source clips the sample's slots run,
  **0** carry a notify. So a notify's time is already the montage's own clock, and a slot's track
  always starts at 0 (measured with the import itself) — the time needs no mapping through the
  spans.
- `montage.get_editor_property("notifies")` is **refused**: «Property 'Notifies' ... is protected
  and cannot be read». `unreal.AnimationLibrary.get_animation_notify_events(montage)` answers them.
- The struct exposes no time to Python (`dir()` has `notify_name`, `notify`,
  `notify_state_class`, `montage_tick_type`, the filters — no duration, no link value). Two roads
  carry it: **`AnimationLibrary.get_anim_notify_event_trigger_time(event)` and
  `..._duration(event)`** (both answered for all 979), and `event.export_text()`, whose text holds
  `Duration`, `TrackIndex`, `EndLink(... LinkValue=...)`, `NotifyColor`. The library is the road;
  the text is the fallback nobody needs yet.
- 539 of the 979 are notify **states** (a range), 440 are points (duration exactly 0).
- `notify_color` cannot be read through Python, and the text shows it unset (black) anyway. Our own
  colour, then.
- **Only 294 of 979 trigger times land on a whole 30 fps frame.**
- 357 pairs overlap in time, in 98 of the 132 montages — which would be a mess on one 11 px band,
  and is the reason the animator was shown the crowding before choosing.

**MeleeScanWindow alone** (the animator's pick):

- **90 windows in 66 of the 132 montages**: 50 montages have exactly one, 10 have two, 4 three,
  2 four. Half the montages have none at all.
- All 90 are states, all of class **`AnimNotifyState_MeleeScanWindow`**. By NAME they are
  `MeleeScanWindow` (88) and `GameplayEvent Window` (2) — **so the class is what identifies them**;
  a name match would lose two.
- Duration 0.033..1.000 s = **1..30 frames at 30 fps**, median 3.5 frames.
- Only **3 overlapping pairs in 3 montages**, so one band holds them.
- 44 slots of the sample are shorter than their montage, and **3 of 1928 slot/notify pairs sit past
  the slot's end**.

## The design

### Where the data comes from

The editor is not asked anything new. Picking a montage row already runs `montage_plan_script`
(~1.5 s, cached per montage in the window's `_STATE["montage_plans"]`), and the plan file written
for the import already travels to Maya as the `montage:<path>` reference. The notifies ride both.

`uescripts.montage_plan_script` gains, per montage row, a `notifies` list:

```python
{"name": str, "class": str, "state": bool, "trigger": float, "duration": float}
```

read through the library (`get_animation_notify_events`, then `get_anim_notify_event_trigger_time`
/ `..._duration`), every field through the script's own `attempt` so a missing engine API cannot
abort the read.

**The script sends every notify; the pick happens in pure Python.** A later «and ComboWindow too»
is then one constant, with no editor round trip and no stale cache.

### The pure half (`maya_uebridge/montage.py`)

```python
SCAN_CLASS = "AnimNotifyState_MeleeScanWindow"   # the animator's pick, by class
Window = collections.namedtuple("Window", "name t0 t1")

def is_scan(row)                       # by class, never by name
def windows_of(payload, package)       # -> [Window], montage time, sorted by t0
def clipped(windows, end)              # a window past the slot's end dropped, one
                                       # crossing it cut back to `end`
def bookmarks_for(plan, fps)           # -> [(name, start, stop)] in FRAMES
```

`Plan` gains a trailing field `windows` with a default of `()`, the way `AnimRecord` gained `kind`:
every positional construction keeps working, and an older plan file read by a newer build answers
no windows rather than raising.

`plan_for` fills `windows=clipped(windows_of(...), end)` — the slot's own end, not the montage's.

**The frames.** `bookmarks_for` snaps **outward**: `floor(t0 · fps)` to `ceil(t1 · fps)`, at least
one frame wide. So:

- a window is never shown shorter than it is;
- the range is always whole frames, so a double click on the bookmark (Maya sets the playback range
  from it) cannot leave a FRACTIONAL playback range — the trap that made Unreal refuse a clip
  («Animation length ... is not frame-border aligned», trap 50).

The cost, stated: up to half a frame wider at each end.

### The scene half

`montage.write_bookmarks(plan, fps)`, called by `import_clip` after the composite is written and
the timeline set:

- the `timeSliderBookmark` plugin loaded as the Time Bar loads it;
- **ours are deleted first**, so a re-import replaces rather than piles up;
- one node per window: `timeRangeStart` / `timeRangeStop` from `bookmarks_for`, `name` the
  notify's own name, `color` our `SCAN_COLOUR` (the hub's `danger` red — it is a hit window),
  `priority` the plugin's next one;
- identity is the attribute **`skeldarMontageNotify`** holding «montage · slot», never the node's
  name (Maya uniquifies a repeated name, and the animator may rename one);
- the nodes land in the active scene tab's namespace, as everything the plugin creates does;
- it runs **unrecorded** (`undoInfo -stateWithoutFlush`, the way Add Character's own work does).
  **Measured 2026-10-29: an `FBXImport` inside an open undo chunk is NOT undone, while a node made
  after it in the same chunk is.** A montage import is FBX imports, so the take cannot be undone;
  recording the bookmarks would make the first Ctrl+Z after an import strip them off a take that
  stays — and bring the previous import's bookmarks back, which reads like a bug. Unrecorded, a
  Ctrl+Z after an import changes neither the take nor its bookmarks;
- it never fails the import: a refusal from the plugin or the node is caught and named in the line.

`info["montage"]["windows"]` carries the count, and `note_of` says «2 scan windows» beside «cuts at
19, 38».

### What the animator sees

The Time Bar's own band draws them (it already reads every `timeSliderBookmark`), **and so does
Maya's own time slider** — this works in either mode. Maya's bookmark list and the band's names
show `MeleeScanWindow`.

### Deliberately not built

- **Other notifies.** Only the scan class, as asked. The script brings every notify, so the rest is
  a constant away.
- **No switch in the card.** Always carried; what is not wanted is deleted by hand. A
  «Notifies [All | Windows | None]» row is five lines if it is ever asked for.
- **Plain clips are not touched.** 0 of the 115 clips in the sample carry a notify; a clip import
  behaves exactly as before.
- No road back into the montage (the animator's own ruling on the import itself).
- The notify TRACKS are not used. Their names in Atone are mostly `1`..`9`, with a few real ones
  (`Footstep`, `Foley`, `WarpKnock`, `CombatImpactPush`); the per-event track index is not in the
  Python struct, only in `export_text`.

## Proof

- **Unit tests** over the pure half: the class pick (the two `GameplayEvent Window` rows included,
  a name-only match would lose them), the clipping at the slot's end, the outward snap and the
  one-frame floor, `Plan.windows`'s default, the payload round trip, the status line.
- **`verify_montage_import.py`** gains gates in its standalone phases: after an import the
  bookmarks stand at the measured frames, a re-import replaces them, a bookmark the animator made
  by hand survives, a Ctrl+Z after a press leaves both the take and its bookmarks, and a slot too
  short for a window gets none.
- **The live phase** against the open editor: `AM_Longsword_Attack_Left_Forward_Hold` (4 windows,
  measured 0.600+0.397, 1.000+0.115, 1.114+0.187, 1.301+0.107) — the bookmarks against the engine's
  own trigger times and durations.
