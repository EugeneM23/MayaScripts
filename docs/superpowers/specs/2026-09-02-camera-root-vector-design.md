# `camera_root` to a vector, not to one axis (2026-09-02)

The tool: `maya_anim_batch_export.py` at the repo root — a standalone
`cmds`-only window ("Anim Batch Export Tool") that walks a folder of
`.ma`/`.mb`/`.fbx`, opens each file, applies a few operations and re-exports.
It is the one root tool CLAUDE.md never documented; three fix commits
(`a268ff6`, `1e01e4f`, `e8abab8`) are its whole written history.

The ask, verbatim:

> в папке C:\Users\MY PC\Desktop\DownState fbx анимации во всех этих
> анимациях нужно поставить camera_root в позицию из текущей сцены. Давай
> модернизируем скрипт так что бы он смещал не по одной оси а мог ставить
> кость в указаный вектор по 3 координатам

Fourteen `AS_DownState_*.FBX` clips, all of which need the same `camera_root`
placement — a position the animator reads off the scene they have open.

## What the operation was, and what it becomes

`op_set_camera_position(height_value, height_axis)` found `root`, found
`camera_root` below it, went to frame 0, **read the position out of the file**,
deleted every animCurve on `camera_root`, overrode **one** axis with the
typed value and wrote the result back in `objectSpace`. Two of the three
coordinates therefore came from the clip and one from the animator.

It becomes `op_set_camera_position(position)` taking `(x, y, z)`: find `root`,
find `camera_root`, delete its curves, write all three coordinates. Nothing is
read from the file any more.

That deletion of the read is worth naming, because it retires a bug rather
than moving it: commit `1e01e4f` ("read camera_root position before deleting
anim curves to avoid reset to 0") exists because the old order read a channel
after freeing it. With no read there is no order to get wrong.

## The three decisions, all the animator's

**Typed by hand, no "pick from scene" button.** Offered a button that would
read `camera_root` out of the open scene into the three fields, and it was
declined in favour of three plain fields. This matters more than it looks:
`run_on_folder` starts each file with `cmds.file(new=True, force=True)`, so
the scene the numbers came from is gone before the first clip is processed.
Whatever holds the vector has to survive that, and a UI field does.

**`objectSpace`, unchanged.** The numbers are `translateX/Y/Z` as the Channel
Box shows them — relative to `camera_root`'s parent. That is what makes
"copy the value from the open scene" a matter of reading three numbers off
the screen. World space was offered and declined; with root motion in the
clips it would have given a different local value in every file.

**All three axes, every time.** No per-axis "set this one, keep those two"
checkboxes. The old behaviour — one axis typed, two inherited from the clip —
has no successor and is not missed: the request is a vector.

## Settings and UI

The settings dict is the interface between the window and the operations, and
it is what a headless run binds to. `height_value` and `height_axis` are
replaced by one key, `camera_position`, a 3-tuple of floats.

In the window, `floatFieldGrp("ffHeight")` plus `optionMenuGrp("omAxis")`
become a single `floatFieldGrp("ffCamPos", numberOfFields=3)` labelled
`camera_root position (XYZ)`. It is read with three explicit
`value1`/`value2`/`value3` queries rather than one `-q -value`: the file
already reads fields that way, and the list form's shape is one more thing to
be wrong about.

The `Set camera_root position` checkbox is unchanged and still decides whether
the vector is applied at all.

## Deliberately not built

Per-axis toggles. A "read from the current scene" button. Persisting the
vector in an optionVar between sessions (the tool has no optionVars at all
today). Touching `camera_bone` — the operation is about `camera_root`, as it
always was.

The curve deletion stays total: `listConnections(camera_root, type="animCurve")`
takes rotation and scale curves down with translation. That is the tool's
existing behaviour, and narrowing it to the translate channels would be a
second change hiding inside this one. Worth revisiting if a clip ever turns up
with rotation on `camera_root` that has to survive.

## How it is proved

`docs/superpowers/plans/verify_anim_batch_camera.py`, run in its **own mayapy
session and never through the command port** — the batch opens a new scene per
file, so a bridge run would discard whatever the animator has open. Same rule,
and the same reason, as `verify_root_offset_batch.py`.

Two measured facts shape that script. In `mayapy` batch, `cmds.window()`
returns `False` while `columnLayout`/`checkBox` succeed, and **every UI query
returns `False`** — so `get_ui_settings()` answers a dict of `False` and a
headless run must build the settings dict by hand and call
`run_on_folder(settings)`, never `run_tool()`. The module itself imports
cleanly in batch, module-level `show_ui()` included.

The gates run over copies of real `AS_DownState_*.FBX` clips in a temp
sandbox, never the animator's Desktop folder, and assert on the files that
land on disk rather than on the scene in memory:

- `camera_root`'s local translate in the export equals the typed vector, on
  all three axes,
- a vector with three distinct non-zero coordinates, so an axis silently
  dropped or transposed cannot pass,
- no animCurve left on `camera_root`,
- the `root` key range in the export matches the source clip's — the
  placement must not cost the animation,
- and the same for a second clip, because the failure that matters is a batch
  that works on the first file.

## Addendum, the same day: the run that came back empty

The first live run wrote all fourteen files and every one of them was empty —
8 KB, four default cameras, no skeleton. The tool was fine; the session was
not. `cmds.file(open=True)` inherits the FBX plugin's global import mode, an
Unreal import earlier in the session had left it on `exmerge`, and in that
mode the importer creates nothing at all. Measured: 0 joints under `exmerge`,
94 under `add` and 94 under `merge`.

That is trap 33 in CLAUDE.md, already paid for twice — once in
`maya_scenesetup` (a weapon silently stopped arriving) and once in
`root_offset_batch_tool` (every file died with "no root joint found"). This
tool imported FBX and never set the mode.

Two fixes, and both are needed. `open_file` sets `FBXImportMode add` and
restores whatever it found in a `finally`, because the animator is working in
that session and the mode is not ours to leave changed. And `export_file`
**refuses a scene with no `root`**: everything this tool does is anchored on
that hierarchy, so a scene without one is a scene nothing worked on. The
export mode explains why the files were empty; the missing guard explains why
fourteen of them were written, counted as successes, and only noticed when
somebody opened one.

The proof now runs the entire batch with the mode forced to `exmerge`. This
matters more than it sounds: a fresh mayapy starts on `merge`, so the original
version of this script passed on exactly the code that was destroying the
animator's exports. A proof that cannot fail in the animator's conditions is
not a proof.
