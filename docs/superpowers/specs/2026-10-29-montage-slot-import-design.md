# Montage import: a slot's track as one take (2026-10-29)

The animator: «Можем ли мы как-то в наш анимейшен сетап во вкладку unreal добавить опцию
отображения монтажей и дальнейшей импорт анимаций из монтажа? Суть такая - сейчас в игре
анимации в монтаже могут быть с разным тайм скейлом и порезаные на разные кусочки я бы хотел
иметь возможность импортировать анимации из определенного слоя в монтаже в точности в том
состоянии как они внутри монтажа».

Asked and answered:

- **one take per slot** (not a clip per segment): the whole slot track as the game plays it;
- the list gets a **`[Animations | Montages]` filter**, the slot a row of its own in the card;
- **import only** — no road back into the montage's clips («Работаю в Maya, назад в монтаж не
  нужно»). The composed take exports like any other clip.

Then: «делай до конца».

## What a montage is here, measured (Atone, 2026-10-29, read-only)

195 AnimMontages, every one on `SK_Mannequin_proto` (the twin of our Manny family — trap 152:
it agrees with our Manny on every deforming bone).

- **Slots**: `DefaultSlot` 184, `1P` 84, `FullBody` 60, `UpperBody` 10, `UpperBodyAdditive` 1.
  The usual montage carries 3P in `DefaultSlot` or `FullBody` and 1P in `1P`
  (`1P+DefaultSlot` 73, `DefaultSlot+FullBody` 56, `DefaultSlot` alone 51).
- **498 segments**, **121 of them at a play rate other than 1** — 0.42 to 3.5.
  70 slot tracks hold more than one segment.
- A segment is a SLICE of one AnimSequence at a rate: `anim_reference`, `start_pos` (where in the
  montage), `anim_start_time`..`anim_end_time` (which part of the clip), `anim_play_rate`,
  `looping_count`.
- **The example the animator means** — `AM_SwordShield_1p_blockreact_mid`: one clip
  (`AS_Techlimb_Character_Parry_3P_Anim`) cut into three pieces, 0–0.27 @1.5, 0.27–0.867 @0.8,
  the same piece again @1.2; and the `1P` slot the same shape over its own 1P clip.
  `AM_LongSword_Block_Stun`: `DefaultSlot` three slices of one 3P clip at 0.52 / 0.475 / 1.1,
  `1P` three DIFFERENT clips (In / Idle / Out) at rate 1.
- **No montage has sections** (`composite_sections` empty in all 195), so the «кусочки» are the
  segments, not sections.
- **No gaps and no head gap**: every slot track starts at 0 and its segments abut
  (the next `start_pos` equals the previous end within 2 ms).
- `looping_count` is 1 on every segment; every `anim_reference` is a plain `AnimSequence` (no
  nested composites); **one additive clip in the whole project** (the `UpperBodyAdditive` slot).
- **The slot's track is often shorter than the montage**: `AM_Grab_AttackerCancel`'s
  `DefaultSlot` ends at 1.733 s against the montage's 2.167 (the rest is blend-out), and nine
  more like it. The take's length is the SLOT's, never the montage's.
- Distinct clips in one slot track: 1 in 327 tracks, 2 in 4, 3 in 5, **7 in 3**.

Two engine limits decide the shape of the work:

- **`AnimSequenceExporterFBX.supported_class` is `AnimSequence`** — a montage cannot be exported
  to FBX at all.
- **`AnimSequence.get_controller()` does not exist on this build** (5.8.4), so a montage cannot be
  baked into a temporary AnimSequence from Python either.

So the composite is assembled in Maya, out of the slot's own source clips. Nothing is written into
the animator's project.

## What the animator sees

In Animation Setup's Connect block, with the Unreal source:

- a row **`Show [Animations | Montages]`** (`ueAnimBridgeAssetKind`, remembered, segments like
  «Put it on»). Hidden for the Unity and Folder sources, which have no montages.
- In **Montages** the list is the project's 195 montages — name, folder, the tag `montage` —
  built from the asset registry alone, so Refresh stays instant (0.023 s for the query; the
  registry carries no slot and no length tag for a montage, and loading all 195 would pull their
  clips).
- Under it a row **`Slot [▾]`** (managed, shown in Montages): a dropdown filled from the picked
  montage. Picking a montage row reads its plan from the editor once (one round trip, cached for
  the session) and fills the dropdown with its slots in the montage's own order; the choice is
  remembered (`ueAnimBridgeSlot`) and kept across rows, falling back to the montage's first slot
  when it has no slot of that name. A dropdown, not segments: `UpperBodyAdditive` beside
  `DefaultSlot` does not fit the animator's 360 px dock (trap 117).
- Everything else is as it is: search, `[List | Folders]`, «Put it on», the timeline box, the one
  Import button (whose words name the montage and the slot), the drag into a viewport, a square of
  several montages, Auto, the clip label under the character.

## What comes in

One take per slot, the slot's track as the engine plays it:

- its length is the **slot track's** end (`AM_LongSword_Block_Stun` slot `1P`: 1.9333 s → 58
  frames at 30 fps), never the montage's;
- at frame `f` the pose is the montage's pose at `t = f / fps`: the span covering `t` is found and
  its clip read at `anim_start_time + (t − start_pos) · rate` (for a negative rate, backwards from
  `anim_end_time`);
- keys on **whole frames** of the scene's rate, dense. A segment boundary falls on a fractional
  frame (0.18 s = frame 5.4) and gets no key of its own: on every whole frame the pose is exact,
  and the corner is smoothed across one frame. The status line names the cuts in frames, so the
  animator knows where the montage's edits are: «AM_SwordShield_1p_blockreact_mid · 1P: 43 frames,
  cuts at 5.4, 27.8».
- Between frames the value is Maya's interpolation of the source clip's curves (the engine's own
  is its compression's). On the frames there is no difference.
- Every channel the slot's clips animate is composed, not only translate / rotate / scale: a UE
  root carries the game's curves as custom attributes (`Pose_0..9`, `MoveData_*`, trap 40), and
  they are sampled by the same rule. A channel one span's clip does not animate reads that clip's
  static value; a joint a clip does not have holds the previous sample and is named.
- The rotate samples are made continuous (a step over 180° between consecutive frames is a wrap,
  not motion, at 30 fps — trap 108's rule, as after every bake in this plugin).

From there it is an ordinary clip: onto the selected rig, onto a new rig, onto a skeleton, Auto,
a drag onto a character or the floor, a square of several, the retarget's own rules (a twin onto
Manny, rotations onto the Creep and the Orc D), the clip label, Export FBX.

## How it is built

### The editor's side — three scripts (`uescripts.py`, stdlib text as every script there)

- `montage_list_script(out, package_path)`: every `AnimMontage` under the path from the asset
  registry — name, package, the `Skeleton` tag. **Loads nothing.**
- `montage_plan_script(out, packages)`: loads those montages and answers, per montage, its slots
  in order, and per slot its segments (clip package, `start_pos`, `anim_start_time`,
  `anim_end_time`, `anim_play_rate`, `looping_count`) plus each clip's additive type, length and
  frame count. Takes a LIST so a pick (one) and a square (several) are one round trip.
- `montage_export_script(out, packages, folder, preview_mesh)`: exports every AnimSequence of the
  list to `<folder>/<name>.fbx` in ONE round trip and answers `{package: path}` — a slot with 7
  clips would otherwise cost 7 trips. The body is `export_script`'s, per package, and a clip it
  cannot export is named in the reply rather than failing the lot.

### The plan model — `maya_uebridge/montage.py`, pure half (stdlib only, a test pins it)

- `Span(clip, t0, t1, src, rate)`: one playable piece on the montage's clock; a segment with
  `looping_count` N expands into N spans.
- `slots_of(payload, package)`, `segments_of(payload, package, slot)`.
- `plan_for(payload, package, slot)` → `Plan(montage, slot, spans, end, clips)`.
- `samples(plan, fps)` → `[(frame, clip, source_time)]` for frames 0..`floor(end · fps)`, the
  source time clamped into its span (the last frame can sit a thousandth of a second past the
  end).
- `cuts(plan, fps)` → the boundaries in frames, for the status line.
- `refusal(payload, package, slot)`: no such slot, an empty track, an additive clip (the one in
  Atone), a segment whose clip has no package. Refusals happen **before anything is exported or
  imported**.
- `clip_name(montage, slot)` → `AM_LongSword_Block_Stun_1P`: the namespace, the label and the
  status line all name the montage and its slot.

### The composer — `montage.py`, scene half

`import_clip(ref, namespace, set_timeline=True, clip_fps=None)`, the shape
`formats.import_clip` has, so `rigimport.import_source` gains one branch and nothing downstream
changes:

1. read the plan file the export step wrote (the plan plus `{clip: fbx}`);
2. import the FIRST span's clip into the target `namespace` through `animimport.import_clip`
   (`merge=False`, no timeline) — so the target skeleton is exactly what a plain import of that
   clip gives: hierarchy, orients, rotate orders, and its mesh when Auto asked for one;
3. import every other distinct clip into a scratch namespace, for reading only;
4. sample and write: per (joint leaf, attribute) one fresh animCurve through
   `MFnAnimCurve.addKeys` (trap 224: times in UI units, angles in radians), read from the source
   curves with `keyframe -q -eval` taking every time of a span in one call;
5. the rotate series made continuous, the scratch namespaces removed;
6. the timeline set to 0..N when asked;
7. the info dict names the frames, the cuts, the clips used and anything held or skipped.

### Where it plugs in

- `records.AnimRecord` gains `kind` (default `""`, so every positional constructor and every
  record made before still means what it meant); `kind="montage"` marks a montage row,
  `records.is_montage` asks. `parse_payload` reads it, `format_row` shows the tag, `import_label`
  names the slot.
- `window`: `asset_kind()` / `set_asset_kind()`, the slot dropdown and its memory,
  `_refresh_unreal` branching on the kind (its own cache file, so switching back and forth costs
  no round trip), `_montage_plan(package)` cached per package, and `_export_from_editor` growing
  a montage branch — which is the one place that knows the montage road, so the button, the double
  click, the drag, the square and Auto all take it.
- `rigimport.import_source`: a `montage:` reference goes to `montage.import_clip`.

## What is not built

- No road back into the montage (the animator's choice): the composed take exports as a clip like
  any other.
- Sections: no montage in the project has any; `composite_sections` is read and named in the plan
  for the day one does.
- Additive slots: refused by name (one such slot exists in Atone).
- Blend-in / blend-out and slot blend profiles: a slot's track is taken as it is; the montage's
  blend times are how the game mixes the slot INTO the body, not part of the slot's animation.
- The engine's own pose evaluation: the composite is built from the slot's clips, not from a
  montage evaluated through a SkeletalMeshComponent.

## Proof

- Unit tests for the whole pure half (spans, looping, a negative rate, the samples at a given
  fps, the cuts, every refusal, the slot order, the record's kind and row, the window's kind and
  slot state on a fake `cmds`, the `import_source` branch).
- `docs/superpowers/plans/verify_montage_import.py`:
  - **standalone** (mayapy, no editor): two fixture clips built in Maya and exported as FBXs, a
    plan written by hand with three spans at rates 1.5 / 0.8 / 1.2 across two clips. Gates: every
    frame's pose equals the source clip read at the mapped time, computed independently in the
    verify; the take's length is the slot's end; the scratch namespaces are gone; a custom
    attribute on the root is composed; one Ctrl+Z; the refusals change nothing.
  - **live** (the editor open): `AM_LongSword_Block_Stun` slot `1P` (three clips) and slot
    `DefaultSlot` (one clip in three slices at three rates), and
    `AM_SwordShield_1p_blockreact_mid` slot `1P`, each imported onto a Manny rig — and the
    composed bones compared against the ENGINE's own reading of the source clips at the mapped
    times (`unreal.AnimationLibrary.get_bone_pose_for_time`, if this build exposes it; else the
    editor's own sampling of the clip), so the comparison does not go through our own arithmetic
    twice.

## Addendum — read as the engine reads (the same day, after the first live run)

The first build read every source channel off the imported clip's own curve at the mapped time. The
live phase then measured the composite against the engine's own evaluation
(`unreal.AnimationLibrary.get_bone_pose_for_time`, which this build does expose) and found the
difference growing with the retime: **3.233°** on `AM_LongSword_Block_Stun`'s DefaultSlot (rates
0.52 / 0.475 / 1.1), 0.350° on `AM_SwordShield_1p_blockreact_mid`'s 1P (1.5 / 0.8 / 1.2), 0.000° on a
slot at rate 1.

That difference is not the mapping — it is the interpolation. A play rate other than 1 maps a target
frame BETWEEN the clip's own keys, and Unreal lerps its compressed keys (slerping the rotations) while
an imported FBX curve carries the file's own cubic tangents and each euler channel lerps on its own.
So the composer now reads the sources the way the engine does:

- a **rotate triple is read together and SLERPED** between the two neighbouring whole frames (which are
  the engine's own neighbours: a UE clip is keyed every frame), the euler chosen against the previous
  sample — the rotation itself or its alternate solution, whole turns aligned; never Maya's
  `closestSolution`, which trades x for z near gimbal lock;
- every **other** channel (translate, scale, a UE root's own curves) is read off a **linearised** source
  curve, which is the engine's lerp.

The curves this touches are the source clips' own imports — a scratch namespace, or the first clip's,
whose curves are rewritten right after — so nothing of the animator's is changed.

Measured again, worst over 5 bones: **0.134° / 0.0005° / 0.0000045°** on the three slots above. The
statement in «What comes in» stands with that correction: on every whole frame the pose is the
montage's, and between frames the take now interpolates as the engine does rather than as the FBX's
tangents did.

Two smaller things the live runs added:

- **the status line names the cuts** in both roads (`montage.note_of` in `rigimport.result_line` and
  `skeletonimport.result_line`): «AM_LongSword_Block_Stun_1P retargeted onto Manny_Rig, frames 0-58 |
  the montage's cuts at 19, 38, 3 clips». The press's line never carried `info["warning"]`, so without
  this the cuts the spec promised were nowhere to be seen;
- **a slot the montage lacks is not a refusal from the card**: the remembered slot can be another
  montage's, so the press takes the montage's first slot (as the dropdown does on a pick) and the line
  names which slot came in. `montage.refusal` keeps the sentence for a slot asked for through the API.
