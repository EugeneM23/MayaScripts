---
name: manny-skeleton
description: Use when the user asks to build a skeleton for a humanoid character and/or skin a model in Maya — «построй скелет», «заскинь модель/персонажа», «сделай риг по Манни», rig/skin a humanoid mesh, UE5 Manny schema skeleton.
---

# Skeleton + skin for a humanoid (UE5 Manny schema)

## Overview

Drive `maya_skelfit.py` over the command-port bridge: it fits the measured
Manny template (93 joints, `assets/manny_skeleton_template.json`) onto the
mesh, and voxel-binds the skin to the 74 joints Manny actually weights.
You orchestrate; the tool does the math. Bridge mechanics: CLAUDE.md
notes 2, 5–9 and trap 17 apply to every send.

## When NOT to use

- Non-humanoid / non-bipedal characters.
- The scene's skeleton must be kept (the tool refuses over existing joints
  — that refusal is the answer, relay it).
- Retargeting an EXISTING skeleton → `maya_retarget.py` instead.

## The workflow

1. **Probe** (read-only): target mesh, `ls(type="joint")` empty, units,
   height. Report what you found before touching anything.
2. **Build**: `import maya_skelfit; maya_skelfit.build()` (repo on
   `sys.path`, purge stale module first — CLAUDE.md note 9). Relay the
   status line; any `refused:` goes to the user verbatim and stops you.
   Read its notes: `scale`, `arm_… re-aimed`, "off the ground" tell you
   how unusual the mesh is.
3. **Checkpoint — placement**: `screenshot(path, "front")` + `"side"` +
   `"persp"`, send the PNGs. The user drags joints that landed badly
   (or names them and you `cmds.xform` them). Fingers/details: they edit
   ONE side only — the mirror is the tool's job.
4. **Finalize**: `maya_skelfit.finalize()` — mirrors the edited side,
   pins the midline, re-solves orientations, cuts accidental autoKey
   keys. Re-screenshot; loop 3–4 until the user accepts. Placement is
   final after this: moving joints once the skin is on deforms the mesh,
   so a post-bind placement fix means unbind → adjust → finalize →
   re-bind.
5. **Bind**: `maya_skelfit.bind()`. "voxel-bound" in the reply is the
   success; "voxel weighting FAILED" means fallback closest-distance
   weights are on the mesh — say so loudly, do not continue as if bound.
6. **Checkpoint — deformation**: for each pose in `POSES`
   (`elbows/knees/shoulders/head/spine`): `pose_test(name)` →
   `screenshot` → `restore_pose()`. Send the captures. Polish user-named
   zones with targeted `cmds.skinPercent`, re-pose, repeat until accepted.
7. Remind the user to save. Suggest a UE clip through the bridge
   (`maya_uebridge`) as the end-to-end check — names match, clips merge.

## Sharp edges

- **Never run `verify_skelfit.py` after the user adjusted joints** — its
  cleanup DELETES the skeleton (hand edits included) and rebuilds from
  scratch. It is the development proof for an empty test scene, not a
  post-workflow check.
- `pose_test` refuses on keyed rotates and a second pose without
  `restore_pose()` — both mean state you must resolve, not force.
- The arm-tip landmark assumes the widest point per side IS the arm
  (A/T-pose). Shields, pauldrons, props wider than the hands mislead the
  arm re-aim — expect step 3 to need arm fixes there, and say so when the
  build notes show a big re-aim angle.
- One mesh per bind; several meshes → the user selects the one to fit
  (the refusal says exactly that). Bind the rest with
  `bind(mesh="|Other")` after.
- The template regenerates with
  `mayapy assets/make_skeleton_template.py` if the character scene ever
  changes; never hand-edit the JSON.
