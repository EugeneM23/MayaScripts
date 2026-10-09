# Pose Library — animation cards (2026-10-03)

The animator: «У нас есть библиотека поз в которой мы умеем сохранять позы, теперь давай добавим
возможность сохранять анимации. Все правила которые работают для поз должны работать и для анимаций.
Так же мы должны уметь выбирать способ вставки анимации как в studio library. Карточки с сохраненной
анимацией должны проигрывать превью этой анимации. Сделай все задание от начала и до конца» — then
«Дальше делай все сам».

Asked and answered:

| question | answer |
|---|---|
| root motion when an animation is applied | **from where the character stands**: the clip starts where the character stands and faces, its travel carried relative to that place; an **In place** checkbox for the pose rule (root / Main untouched) |
| which keys on a rig or skeleton | **an option, every frame by default** (exact, like the retarget's bake); «on the source's keys» keys only where the source had keys |
| when a card plays its preview | **on hover** (the card under the mouse — it already grows twice its size — loops its animation); the big picture in the details of the picked card loops always |

Read the pose library spec first (`2026-10-02-pose-library-design.md`): every rule there holds for an
animation card, frame by frame, unless this spec says otherwise.

## What an animation card is

A folder `<Name>.anim/` (Studio Library's suffix) beside the `<Name>.pose/` cards, in the same library
and catalogs:

- `anim.json` — the HEADER, small (tens of KB), read by every listing:
  - the pose card's common keys (`name`, `created`, `author`, `scene`, `fps`) with
    `format: "skeldar.anim"`, `version: 1`, `kind: "character" | "objects"`;
  - `start`, `end` (the source frames, whole), `frames` (their count, `end - start + 1`);
  - **character**: `character` (the pose card's identity), `bones` — every bone of the source skeleton,
    STATIC only: `{parent, canonical, rest[16], rotateOrder}` (the rest read once, by the pose rules),
    `members`, `regions`, `key_times` (the source's key times inside the range, below), `rig_source`
    (true when the card carries drives);
  - **objects**: `objects: [{name, path, attrs: {attr: CURVE}}]`, a CURVE being
    `{"static": v}` (no time curve on the plug) or `{"keys": [[t, v, inType, outType, inAngle, inWeight,
    outAngle, outWeight]...], "weighted": bool, "breakdown": [t...]}` (the keys inside the range with a
    shape-preserving key inserted at each end — taken on a duplicate of the curve, never on the scene's);
    a plug fed by a layer or any other input is sampled every frame (`{"keys": ...}` with spline
    tangents);
  - `preview`: `{"frames": n, "columns": c, "size": px, "step": k}` when a preview was captured.
- `frames.json.gz` — the per-frame DATA, read only by Apply, Blend and Update: `{"bones": [leaf...],
  "world": [[7 floats per bone] per frame], "drive": {leaf: [[7 floats] per frame]}}`, each bone's
  world as a quaternion and a translation (`qx qy qz qw tx ty tz`, quaternion to 9 decimals, translation
  to 6), every bone of the skeleton (helpers too) on every frame; a character card only.
- `thumbnail.jpg` — the still, 640 px, as a pose card's (the frame the save panel's Snapshot took).
- `preview.jpg` — the SPRITE SHEET: up to `PREVIEW_MAX` (60) frames of the range, every `step`-th
  (`step = ceil(frames / 60)`), each `PREVIEW_SIZE` (320) px square, `columns = ceil(sqrt(n))` to a
  row, left to right, top to bottom, JPG q 85. One file decoded once; a card plays it by drawing one
  cell at a time.

Write order: the frames, the thumbnail and the preview first, `anim.json` LAST (each through `.part` +
`os.replace`) — a reader sees `anim.json` only when the card is whole. A replace keeps every file it is
not given (Update from selection keeps the still and the preview; Replace thumbnail gives both again).
A known limit: the swaps are one `os.replace` after another, so a replace that fails BETWEEN two of
them (a disk pulled away) keeps the files it had swapped already — new frames under the old header;
a write that fails while STAGING leaves an existing card as it was.

`store`:
- `CARD_SUFFIXES = (".pose", ".anim")`; a name is free in a folder only when NEITHER suffix exists
  (`unique_name`), so a pose and an animation never share a name there;
- `Card` gains, WITH DEFAULTS, `type` (`"pose" | "anim"`), `frames` (0 for a pose), `preview` (the
  sheet's path or `""`), `fps` (the unit string), `start`, `end` — every existing positional
  construction keeps working;
- `read(path)` answers the header (`anim.json` or `pose.json`); `read_frames(path)` the decoded data
  (cached by path + mtime, one entry);
- `filter_cards` hay gains the type word, matched only as a WHOLE term (`pose` / `poses`, `anim` /
  `animation` / `animations` — «po» typed on the way to a name matched every pose before, S14); a
  type filter (`all | pose | anim`) beside the search;
- a header whose `start`, `end` or `frames` is no finite number (JSON's NaN, Infinity), or whose
  `key_times` is no list of finite numbers, is a broken card - never a pick that raises half way
  (S12);
- rename / move / remove / trash / folders handle both suffixes; an older build sees an `.anim` folder
  as a catalog and never applies it — but it can WRITE INTO it: a pose moved or saved «into» that
  catalog lands inside the `.anim` folder. Nothing is deleted, but the newer build then lists only the
  animation (a card folder holds no cards), the pose hidden inside it until it is moved out by hand. An
  older build cannot be changed; the risk lasts as long as builds before this one are installed.

The install (`install.keep_local`, `free_card`, `_rename_inside`, `poses_walk`, `card_files`) treats an
`.anim` folder as one card unit exactly as a `.pose` one (its main file `anim.json`), and
`make_build`'s manifest lists both — nothing else changes: local animations survive every install,
card by card, and the animator's commits ship them.

## Save

The toolbar's **+ Save** (was «+ Save pose») opens the save panel with `[Pose | Animation]` segments
(remembered, `skeldarPoseLibrarySaveType`). Animation shows **Start / End** (defaults: the time slider's
highlight when the animator dragged one, else the playback range; whole frames) and a line saying how
many frames and preview cells it will take. The rest is the pose panel's: name (`Anim`, `Anim 2`, …),
folder, character, region chips, Snapshot.

**What is read** — the pose rules, over the range:
- the selection names ONE character (any part of it) → a **character** card of its BONES, members and
  regions as for a pose; or nothing of a character → an **objects** card of the selected transforms'
  keyable scalar attributes;
- the static half (`bones`: parent, canonical, rest, rotateOrder) is read ONCE, at the current frame,
  by the pose's rules (one rest per skeleton, trap 209);
- the per-frame half is a **time walk** over `start..end`: `MAnimControl.setCurrentTime` under
  `refresh -suspend` (the CoM engine's walk; `currentTime -update 0` reads stale, trap 127), every
  bone's `worldMatrix[0]` and, on a rig, `rigsolve.drive_matrices`; the animator's unkeyed tweaks are
  read before the walk and put back after (`keys.Tweaks`), the time put back;
- `key_times`: the union of the key times, inside the range, of every time curve feeding the
  character's nodes (a rig: its controls, through animBlendNodes for layers; a skeleton: its joints),
  rounded to whole frames, the range ends always in;
- objects: the curves as above.

**The preview**: the thumbnail's machinery over the range — the active model panel, the HIDDEN editor
flags off and put back, the first frame blasted until two blasts agree (trap 120), then ONE playblast
of the preview's frames (`frame=[...]`, JPG, the port's size, offscreen), each centre-cropped square,
scaled to 320 px and painted into the sheet (Qt); tweaks and the time put back. Batch mode, no panel or
no Qt: a card without a preview (it shows its thumbnail).

The press runs under a cancellable progress window; Cancel writes nothing.

**Update from selection** on an animation card reads the card's OWN range again (members from the
selection, as for a pose) and keeps the thumbnail and the preview; **Replace thumbnail** on an
animation card takes the still and the preview again. Both write into the card's folder BY ITS PATH
(`store.replace`), never by a name made again: a card renamed in Explorer to a name `safe_name`
changes came back from a write by name as a stray new card (the final review).

A name a card of EITHER type already holds in the folder is refused at once, the panel kept — never
after an animation's walk and preview (the final review, S7). Esc during the preview's playblast
cancels the save too: nothing written (S1).

## Apply — the options

The details of an animation card add an options block under Apply (each remembered,
`skeldarPoseLibrary<Name>`; its place: "The window"):

| option | values | default | what |
|---|---|---|---|
| **Paste** | Replace · Replace all · Insert · Merge | Replace | Studio Library's (Maya's `pasteKey`) modes, below |
| **At current time** | on / off | on | the clip starts at the current frame (rounded to a whole frame); off: at its own source frames |
| **Range** | start – end | the whole clip | a part of the clip (source frames) |
| **Connect** | on / off | off | every pasted channel offset so its first pasted value is the value the channel shows at the paste frame (Studio Library's / `pasteKey -connect`) |
| **Keys** | Every frame · Source keys | Every frame | character cards: a key on every frame, or only at the source's key times (the curves interpolate between, approximately) |
| **In place** | on / off | off | character cards: root / Main untouched (the pose rule, every frame) |

Mirror and Blend are there as for a pose.

**The paste modes**, on every channel the press keys, on the ACTIVE layer's curve of that channel
(`animLayer -q -findCurveForPlug`; the plain curve without layers): the paste range `[a, b]` is the
target frames of the first and last pasted frame;
- **Replace** — the keys inside `[a, b]` are cut, then the clip keyed;
- **Replace all** — every key of the channel is cut, then the clip keyed;
- **Insert** — every key at or after `a` moves later by the clip's length in frames (`b - a + 1`), then
  the clip keyed into the gap (the hotkey map's «insert a frame» is the one-frame case);
- **Merge** — the clip keyed over what is there; a key at another time inside `[a, b]` stays.

Other layers' curves are never cut or moved. A channel the target has no curve for just takes the keys.

**Root motion** («от места персонажа»): a character card whose members hold the PELVIS (a whole or
lower body) carries the clip's travel; a partial card (a hand, an arm) is always in place.
- the source's root frame per frame `R_s(i)` — its root bone, or, rootless, its ground frame (the pose
  rule: the floor under the top joint, turned by its heading) with the heading kept CONTINUOUS across
  the clip (`posemath.clip_roots` / `steady_yaws`): a frame whose top joint swings more than 120 deg
  off upright (`SWING_LIMIT` — the hips upside down in a roll, where the yaw of a 2 deg tilt reads as
  a half turn) takes the yaw interpolated the short way round between the nearest frames within it
  (held at the clip's ends). The travel, the transfer's pelvis offset and the mirror plane all read
  those frames: a hips forward roll (360 deg about X over 24 frames, a ±2 deg side tilt, no turn)
  keyed the target's root yaw -4, -15, 180, -6 deg at four frames in a row; steadied, the roll's
  heading stays within 3.5 deg (the final review, M3). A pose, and every frame within the limit,
  read exactly the pose rule;
- the travel relative to the first pasted frame `L(i) = R_s(i) · R_s(0)⁻¹`, carried into the target's
  root axes through the two rests (`L_t = Q · L · Q⁻¹`, `Q` the rotation of posemath's `root_offset`),
  its translation scaled by the two bodies' size (`scale_between`);
- the target's root frame at the paste frame `P` — its root as it stands at frame `a`, BEFORE the paste
  (rootless: its ground frame there) — and per frame `W_t(i) = L_t(i) · P`. Pasted at the current
  frame, `P` is what the animator SEES there: the walk sets no time on the frame the scene already
  stands on (`Walk.arrive` — a same-frame time set throws every unkeyed tweak away), so Main dragged
  by hand off its keys to place the walk is where the travel starts, not where its keys stood (the
  final review, M2); and back on that frame after the walk has moved — a pre-pass (step 3 of the
  press) — the tweaks the walk captured on entry are set back (unrecorded, the keyed plugs aside), so
  frame `a` reads as the animator sees it on every road (the re-review of the fix wave: at Blend 50 %
  with Connect, frame `a` was solved against the keyed pelvis and an IK foot's first key landed 10.8
  cm off what it showed);
- every frame's transfer runs with `W_t(i)` as the target's root frame (the pelvis relative to it, as
  for a pose); a skeleton's root joint is written to it (translate + rotate), a rig's **Main** to
  `O⁻¹ · W_t(i)` (`O` = the game root in Main, sampled at the paste frame, constant), a rootless
  target's top joint keeps the moving ground (`_on_ground` with `W_t(i)`) — taking off the heading the
  STEADIED source frame implies (its own turned by the steadied one's difference), never its own: near
  upside down its own is noise, and the body stood turned by the difference, 180 deg at a roll's
  inverted frames (the re-review of the fix wave); a twin, rootless onto rootless, lands on the card at
  every frame, with the travel and In place;
- mirrored, the travel is reflected across the source root's sagittal plane (`F · L · F`, posemath's
  reflection);
- In place, a partial card, or a Main the press cannot write (locked, driven by something not ours) →
  the pose rule: never written, named when it was asked. A skeleton's root joint, and a rootless
  skeleton's top joint, carry the travel under the same rule: all six rotate / translate channels or
  no travel (S6);
- In place on a ROOTLESS target its ground still moves under it — the take's — but its top joint is a
  planned member (Replace cuts its curve, every frame keys it), so that ground is read at every pasted
  frame BEFORE the cut and the keys, and handed to each frame's transfer (the final review, M4: read
  off the curve the press was rewriting, a walking target's ground fell 12.7 cm off the take's). Under
  **Insert** every pasted frame stands on the take's ground at `a`, where the shifted take resumes
  after the clip (the re-review of the fix wave: riding the take's own `a..b` ground, the paste was
  snapped back by the walk at `b + 1` — 75 cm on the verify's walking target).

**Per frame** (character): the pose's transfer and solve, with
- the pairing, scale, twin decision, member lists, drive choice and the rigs' structure computed ONCE
  per target (`posemath.Transfer`, `rigsolve.Solver`);
- the rest alignment of a non-twin computed ONCE, from the clip's FIRST pasted frame (the pose reads it
  from the pose; per frame it would make an animation jitter, and it fixes the mirrored non-twin case —
  mirrored rotations against unmirrored positions);
- the frame's source bones decoded from `frames.json.gz` (the card's `bones` + that frame's `world` /
  `drive`), mirrored per frame when asked;
- the target read AT THAT FRAME (a time walk — the parts of the character the card does not hold play
  their own animation under it), solved, the eulers nearest the PREVIOUS frame's solution (the first
  nearest the value at the paste frame) so the curves never flip (trap 108);
- keyed at that frame on the active layer (`value=` final; a key on the current frame, measured);
- measured (the pose's measure, every keyed frame); the line names the worst and its frame.

**The press, in order** (one undo chunk; autoKey off; the walk unrecorded and under DG — `rigsolve`'s
`FRESH_MODE` around the WHOLE walk, one switch; tweaks read first and put back after, except what was
keyed; the time put back):
1. refusals before anything is read or written: the layer (locked; a quaternion additive layer for a
   character card), the range (empty), the card's data (missing frames file);
2. targets — the pose rules (the selection's characters; nothing selected: the only one); per target
   the plan: pairs, scale, members, which plugs (a dry solve at the paste frame), the paste frame's
   values (for Connect and the seed), the root place `P`;
3. BEFORE anything is cut or keyed, one walk over `[a, b]` (when there is anything to read) reading
   what later frames must not read off curves the press rewrites: at Blend < 100 % every planned plug
   as it stands (the partner of the mix per frame); the ground of a rootless target that carries no
   travel (M4, above); then what every planned plug SHOWED when the press began (the tweaks read at
   the walk's entry, else its value);
4. the chunk's FIRST step: every planned plug set to what it showed when the press began
   (`keys.undo_marks` — set unrecorded, then through a recorded `setAttr`), undone LAST. Each frame's
   solve records its temporary sets and their restores in the chunk at frames that are not the current
   one, and a Ctrl+Z replays them backwards: without the mark one Ctrl+Z of a paste OFF the current
   frame (At current time off, a fractional current time) left every planned channel showing the
   first pasted frame's value where nothing re-evaluated it — Merge always, Replace onto a channel with
   no key inside `[a, b]` (measured: 180 channels, up to 34.9 deg; the final review, M1);
5. the paste mode's cut / move on the planned plugs' active-layer curves;
6. the walk: per frame transfer, solve, Connect offset, mix, key, measure;
7. one progress window; Cancel undoes the press's own chunk (everything back) and says so. With undo
   OFF nothing can be undone: what was keyed stays, its curves get their infinity and weighting back,
   the tweaks are never set back over it, and the line names the frames keyed and what the mode cut or
   moved (S3) — the keys the curves really lost or moved, counted; an op that reached none (a
   referenced curve warns and keeps its keys) is not claimed (the re-review of the fix wave). A press
   that RAISES inside its chunk is undone the same way before the error goes on — half a paste is
   never left behind (S2) — once the chunk recorded a step of the press: a chunk left empty (its
   autoKey question raising) undoes nothing, never the animator's step before it.

**Objects**: the pose's pairing (selection by path / name / order, a character part never an object);
per channel the stored keys shifted to the paste frame (cut to the range), Connect and Blend applied to
their values, keyed with their tangent types (and angles / weights where no layer is involved —
on a layer the tangents are the layer curve's and only their types travel), a stored breakdown key
landing as a breakdown again (S4); a static attribute keyed once at `a`. The paste modes as above.
An objects **Blend** mixes the key VALUES at the clip's own key times with what the channel showed at
each of those times, and keeps the clip's tangents (its fixed slopes): the take's motion BETWEEN the
clip's key times is no part of the mix — a take keyed densely between two of the clip's keys is not
followed there.

**Time units**: frame for frame. A card saved at another rate than the scene's is pasted frame for
frame (its timing in seconds changes) and the line says so.

**Blend** on an animation card: the slider and the middle drag preview the clip's frame that falls on
the current frame (the first when it falls outside) — one pose, live, unrecorded; the release pastes
the whole range at that weight (the per-frame mix with the take as it stood), with the progress
window.

**Drops**: onto a character in a viewport — Apply onto it with the panel's options; onto the empty
floor — the source character added there (the pose's road) and the clip applied at the current frame,
its travel starting from the drop point; onto a folder — moved.

**Select objects**: the pose's (the controls / joints the card would key), plus Main or the root when
the travel would be carried.

## The window

- the toolbar: search, a type filter `[All | Poses | Animations]` (remembered,
  `skeldarPoseLibraryType`), sort, size, **+ Save**;
- an animation card draws a small badge on its picture — a play triangle and its frame count — and
  **plays on hover**: the card under the mouse (grown twice its size) draws its sheet's cells in a loop
  at the clip's own rate (`step / fps` seconds a cell; `fps` from the unit string), from the first cell,
  once the mouse has RESTED on it `DWELL_MS` (150 ms, a single-shot timer): a sheet takes 27-33 ms to
  decode on the GUI thread (measured live), and a sweep across a row of clips decoded every one and
  stuttered — a sweep now decodes none (the final review, S9); a card without a preview shows its
  still;
- the details of a picked animation card loop its preview in the big picture, and list: «48 frames
  (0-47) · 30 fps · 12 keys», the bones and regions, author and date, the scene; then **Apply**,
  **Mirror**, **Blend**, **Select objects**, and UNDER them the options block, two options to a row
  (At current time + Connect, Keys + In place): above Apply it pushed Apply below the fold of the
  window's default size (1000 x 640 logical) for every animation card — Apply's bottom 602 px down a
  541 px side panel at a scale of 1.0 (the final review, M5);
- a Save: a name a card of either type holds in the folder refused at once (above); the save panel's
  folder line follows the tree while it is open, and so does a name the PANEL gave — the new folder's
  free one (a name the animator typed stays; the re-review of the fix wave: «Pose 2», chosen for the
  folder it opened on, was refused in one holding a «Pose 2»); the card just saved shown and picked
  — a type filter that would hide it switched to All (remembered) and said so («the type filter shows
  All, so the new card can be seen»), a search that hides it kept (it is the animator's) and the line
  says so («the new card is hidden by the search - clear it to see the card») (S7, S11);
- the right button rows are the pose card's (Replace thumbnail → «Replace thumbnail and preview» on an
  animation card);
- the playback costs only the hovered card and the details picture: one 33 ms timer in each, running
  only while something plays; the sheet decoded once per card (a small cache), only after the dwell,
  and each cell drawn straight from it, scaled at paint time. A closed library lets its decoded
  sheets go with it (S8).

The status line: «Walk onto Manny_Rig1: 73 controls keyed over frames 12-59 (48 frames, replace) on
AnimLayer1 - worst 0.003 deg at frame 31 | notes».

## Not built

Retiming (scale / fit paste), a paste of several clips at once, layer creation for the paste, the IK
spine, translations of bones below the pelvis (rotations only, as for poses), sub-frame keys, seconds-
true pasting across frame rates, sending a card through Shared.
