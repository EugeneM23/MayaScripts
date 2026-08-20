# Root Offset Batch Tool — splice, not wipe (2026-08-20)

The tool: `C:/!!!Work/Perforce/Atone/Scripts/Maya/root_offset_batch_tool.py`.
It lives in the Perforce depot, not in this repo, because that folder is what
the animator has on `sys.path`. Its proof lives here:
`docs/superpowers/plans/verify_root_offset_batch.py` (**35/35 green**), and it
runs in its own `mayapy` session rather than through the command port, because
the tool opens a new scene per file and a bridge run would discard whatever the
animator has open.

The reported symptom was one sentence — «клип обрезается». Five separate bugs
were behind it and around it, all measured before anything was changed.

## What the tool is for, restated by the animator

> Скрипт должен отработать только в указанном промежутке, а всю остальную
> анимацию сохранить как есть ничего не удалять и не ломать! Если после
> указанного промежутка на руте есть анимация то скрипт должен ее сохранить и
> продолжить с места остановки в промежутке.

So the operation is a **splice**, not the wipe-and-rekey the code did:

| region | what happens |
|---|---|
| before the window | untouched, shape included |
| the window | the straight offset, `base → base + distance` |
| after the window | kept, and shifted by `(base + distance) - old_end` so it continues from where the offset stopped |
| every other channel | never touched |

The tail shift is what "продолжить с места остановки" means: without it the
character teleports back at the seam. Worked example — a root walking 0→100 over
frames 0..40, offset 200 over frames 10..20: it walks to 25, slides to 225, then
walks on from 225 to 275. The clip gets longer in space, not in time.

## The five bugs

1. **The export was clipped to the offset window.** `apply_root_offset` set
   `playbackOptions` to `[start, start+frames]`, and FBX export writes the take
   across the animation range. Measured: a scene holding keys from -20 to 30
   exported as 0..30. This is the reported symptom. The range is now the
   **union** of the clip's own keys and the window.
2. **Every animCurve on the root was deleted.** On
   `ShortSword_Attack_Right_3P` that is 135 curves — `Pose_0..9`,
   `MoveData_Speed`, `DisableLegIK`, `DisableHandIKRetargeting`,
   `RootMotionAdditiveInput` and the pose drivers (`thigh_l_fwd_90` and
   friends) — all of them UE animation curves that drive IK toggles and pose
   blending. The tool now touches nothing but the translate channels it keys.
3. **The offset started from whatever frame Maya happened to sit on.**
   `getAttr` with no `time=` reads the current frame, and after the wipe the
   channel kept that stale pose. Measured on the attack clip: at current frame
   10 the root sat at `(-8.72, 0, 42.58)` instead of `(-7.19, 0, -11.80)`. The
   base is now read explicitly at the window's start frame.
4. **`exmerge` left over from another tool killed the whole batch.** The FBX
   import mode is one global setting for the whole session (trap 33), and
   `maya_uebridge` leaves it there. Measured: `add` and `merge` import 93
   joints, `exmerge` imports **0**, so every file died with "no root joint
   found in the scene" — a message pointing at the clip while the clip is
   fine. The mode is now set explicitly and put back.
5. **A stray `ik_hand_root` outranked the real skeleton.** The old scoring
   liked any name ending in "root"; measured, it picked `|ik_hand_root` over a
   `pelvis` skeleton and offset the helper. Candidates are now limited to
   joints with no joint above them — which is also what keeps UE's
   `ik_foot_root`/`ik_hand_root` out while they hang under `root` — an exact
   `root` wins, and failing that the joint with the most joints under it.

Plus two hazards that were not the reported bug but sit in the same code path:
the batch **discarded the open scene without asking** (`file(new=True,
force=True)` per file — now one confirm when the scene is modified), and an
empty name suffix with the output folder set to the source folder **overwrote
the source clip** (`clip.FBX` and `clip.fbx` are one file on Windows — now
refused).

## Decisions worth keeping

**`setKeyframe -insert` is what makes the outside survive.** It plants a key at
each window edge without changing the curve's shape, so the segments reaching
the window from either side stay bounded by their own slopes. Only the two
tangents facing **into** the window are dictated; the outward-facing pair
belongs to the animation we promised to keep, which is why the in/out pair is
unlocked (`keyTangent -lock false`) before setting one of them. Measured worst
error on the frames outside the window: **0.000000000**.

**`FBXImport`, not `cmds.file(i=True, type="FBX")`.** The two go through
different translator paths, and only `FBXImport` obeys the `FBXImport*`
settings. Note this is *not* trap 22 repeating: `cmds.file` did import the
curves here (583 either way). The measured difference is the frame rate — these
clips are 30 fps, and read into a 24 fps scene `cmds.file` resamples them onto
fractional frames (`-25..18` becomes `-20..14.4`) and they re-export at the
wrong rate. `FBXImportSetMayaFrameRate -v true` makes the scene adopt the
file's rate; the scene is brand new one line above, so there is nothing to
protect by keeping the old one — unlike `maya_uebridge`, which imports into the
animator's own scene and reports a mismatch instead.

**The idle axes are held, not wiped.** With the checkbox on, the two axes that
are not the offset axis are held flat *inside* the window and their tails
continue from the hold — the same splice with a distance of zero. With it off
they are not touched at all. The label says "Hold the other two axes" now,
because "Key all translate axes" described the old destructive behaviour.

## Two red herrings, recorded so they are not chased twice

**Negative frames are fine.** The walk clip's earliest keys are at -25 and they
do not appear in the export, which looks exactly like a clamp at frame zero. It
is not: those seven curves belong to `Manny_rig:camera1`, and the tool
deliberately exports no cameras (`FBXExportCameras -v false`). An isolated joint
keyed at -10, -5, 0, 5, 10 round-trips through the tool's own export exactly —
gates 30 and 31 pin that down, and gate 28 measures the range over the
**skeleton's** curves only. The first version of that gate compared against
every curve in the scene and read the tool as lossy.

**A gate that passes is not a gate that works.** The first overwrite-guard gate
"passed" because an unrelated leftover (`exmerge`, bug 4) had made the import
fail long before the export could overwrite anything. It now runs on a copy and
compares the file's md5 before and after, and asserts the refusal names the
reason.

## Not done

The window is still typed in frames rather than offered as the clip's own
range, and a clip whose root motion should be *scaled* rather than replaced
needs a different operation. Both are features, not bugs, and neither was
asked for.
