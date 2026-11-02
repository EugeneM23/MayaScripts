# The rig pose is built on the additive pose, and acts on the whole animation as a top layer

2026-11-02. The animator, their Maya on port 7002: «Давай сделаем так что бы наша риг поза в walk builder
строилась с учетом адитивной позы и влияла на всю анимайию как верхний слой».

Asked, and answered: the pelvis's move stays **in the layer** (not in the Height / Forward parameters, which
`keyrig.split_common` does for the four keys), and the old correction on walkers already processed is **left as
it is** — read where it is read today, with new edits laid on top.

**This replaces** what `docs/superpowers/specs/2026-10-15-walk-mean-pose-rig-design.md` says about where the
mean pose rig stands and where its correction goes.

## What is wrong today, measured in the code

Two halves of one defect.

- **The rig stands in a pose the walker does not show.** `meanrig.press` stands it in
  `meanpose.mean_pose(walk, fix)` — the mean pose of the walk's own cleaned clip with its correction in it. The
  additive pose (a Pose Library card at the Pose share), the parameters and the physics are applied later, in
  `model.Walk.evaluate`, so none of them is in what the rig shows.
- **The correction is a bottom layer, and the pose washes it out.** It goes in through
  `meanpose.correct(clip, fix)` inside `scene.load_walk` — into the cycle's frames **before** the analysis — and
  the legs' share through `Walk.fix`. In `evaluate` a pose's own means then replace the walk's: the spine map and
  the pose's locals take the upper body, and the model's own comment says it for the legs — «the correction's
  turns, giving way to a pose's own at its share», `own_k = (1.0 - ctx["alpha"])`, the same for the width and the
  height's reference. At **Pose share 1** — the animator's own case, `LongSword_Idle_3P` at share 1 — the
  correction reads as nothing at all.

So a press of Update moves a correction that the next evaluation throws away, and the rig it is read from stands
somewhere the animator never sees.

## The design: the correction is the key poses' fifth entry, `cycle`

The key poses already solved this shape on 2026-10-27: `keyposes.on_result` puts their edits on the walker's
**evaluated** animation — after the parameters, the pose and the physics — so a walker shows at each key exactly
what its rig shows. The mean pose is the same thing with no phase: one entry applied at **every** frame.

Nothing new is written about legs. `keyposes` already carries the upper body's turns in the parent's frame (the
motion about them kept), the pelvis moved over the root, the feet's prints (the planted foot held, the swing
drawn toward it) and the knees' turn about the leg's line.

### `keyposes`

- `CYCLE = "cycle"`, `ENTRIES = KEYS + (CYCLE,)`; `loads` accepts it, `dumps` writes it, `LABELS[CYCLE]` is
  «Mean pose». The entry's shape is `empty_key()`'s, unchanged, so the file (`<walk>.walkkeys.json`) and the
  walker's own attribute carry it with no new format.
- `cycle_values(entry, walk)` — the entry as the `values` dict `knots` builds (turns as log vectors in the
  bone's parent frame, the pelvis in travel coordinates, the knees, the feet), **never mirrored**: a mean-pose
  edit of the left arm holds the left arm through the whole cycle, where a key's edit swaps sides on the other
  foot's step (`knots`' own rule, which is right for a phase-bound key and wrong for a mean).
- `correct(clip, keys, steps, walk)` adds the cycle entry to every frame's mixed values. With `steps` None, or
  with no key edit at all, the cycle alone is applied: **the mean correction needs no step detection**, so a
  result whose steps cannot be read still takes it.
- `stance_prints(keys)` mirrors the keys' prints as today and takes the cycle's unmirrored.
- `increment(key, base, now, walk, frame, knees=None, planted=None)` — `planted=True` reads every foot as
  planted: a mean pose has no foot in the air, so a foot's move along the ground is its **print** (where it
  stands for its whole stance) and its turn about up is its toe-out. A lift of it is not taken, and said, as the
  planted road already does.
- `is_empty`, `summary`, `key_empty` read the cycle like any entry; `summary(keys, only=)` lets a line name the
  four keys apart from the mean pose.

### `meanrig`

- `press` reads the walker's own animation **with its steps** (`scene.walker_animation(root)`, so `anim.rw` —
  the result read as a walk, the key rigs' own reading) and stands the rig in `meanpose.mean_pose(anim.rw)`: the
  mean pose of what the walker shows, the pose, the parameters, the physics and every standing correction
  inside. The memo keeps the base reading as it does today ({bone: 4x4}, `_flat`).
- `update` measures the base and the rig against `anim.rw` (`keyposes.measure`), takes
  `keyposes.increment(CYCLE, ..., frame=0, planted=True)` and adds it to `edits["keys"]` (`keyposes.add`), then
  re-keys the walker unrecorded, as today. No `split_common`: the animator chose the layer.
- `reset` drops the cycle entry **and** the old `fix` — it is the «drop the correction» button.
- The press line says the mean pose's own summary and, where a walker still carries one, the old correction's.

### The order of the layers

The mean pose first (the whole cycle), the key poses' edits on top. That is the order the readings themselves
assume: a key rig stands in the result, which already has the mean correction in it, so its own delta is read
against that.

A consequence to keep: the upper body lands exactly. The cycle's turn is a constant post-multiply on each
frame's local, and the Karcher mean on SO(3) is equivariant under right multiplication, so the mean of the
corrected locals is the mean times the turn — the rig's next reading finds what it asked for. The legs go
through the IK solve, so they land as closely as a key pose's do.

### What the key poses must not break

`keyrig.reset` sets `edits["keys"] = keyposes.empty()` today, which would throw the mean correction away. It
drops the four keys alone now, and `meanrig.reset` the cycle alone; `keyrig.press`/`update` iterate `KEYS` and
their lines name the keys alone.

### What is left alone

`meanpose.correct` in `scene.load_walk` and `Walk.fix` in the model, with the model's own mixing against a
pose's share. A correction an animator already dialled keeps working where it is; new edits go on top, and the
line names both. Nothing in `model.py` changes.

## The cost, stated

The mean correction no longer goes through the model's smarts. A pelvis raised on the result can ask a leg past
its reach: the layer's own leg solve then stands it straight at the ankle and the line says so — the same cost a
key pose's pelvis move already has, and the animator's own choice here. The Height parameter, with its reach and
its passing-knee straightening, stays the road for a hips change that should be paid for.

## Proof

`docs/superpowers/plans/walkparam/verify_walk_rig_pose_layer.py`, mayapy standalone, on a Manny UE5 skeleton
walking a saved cycle under a pose card at **share 1** (the case where today's build reads as nothing):

- the rig stands in the mean pose of the **result**, not of the cycle: every bone of the rig's game skeleton
  within a tolerance of the result's own mean, and a control that the walk's own mean pose differs where the
  pose moves it;
- an arm turned 20° on the rig and Update: the walker's game bone turned that far **on every frame**, with the
  build before this as the control — at share 1 it reads 0;
- the pelvis raised: the walker's hips up on every frame, the planted feet still, the line naming a leg the lift
  pulled straight where it did;
- a foot turned on the rig: its print, every stance;
- a knee turned: its bend, and not read where the leg is near straight (the existing rule);
- the key poses still land: a key edit on top of a standing mean correction is exact at its key;
- one Ctrl+Z after Update is the rig's (the walker is re-keyed unrecorded), Reset drops the correction and the
  walker plays the plain cycle again;
- `verify_walk_keyposes.py`, `verify_walk_meanpose.py`, `verify_walk_working.py`, `verify_walk_many.py` and
  `verify_walk_straight_leg.py` as green as they are on the commit before this.

Then live on port 7002: Create, a control turned, Update, and the walker's bone read back off its keys.

## Not built

- Folding an old `.walkfix` correction into the new layer (the animator's choice: it stays where it is).
- The pelvis's move as the Height / Forward parameters (asked and declined for this feature).
- `Walk.fix` and `meanpose.correct` removed from the model and `load_walk` — they stay for old corrections, and
  retiring them is a job of its own.
