# SceneSetup, and the camera setup — design

**Date:** 2026-08-17
**Status:** designed. Renames the weapon module and adds the camera button.

## Two parts

1. **The module becomes `SceneSetup`.** It is not a weapon tool any more; it
   sets a shot up. The package `maya_weapons` becomes `maya_scenesetup` and the
   window title becomes "Scene Setup".
2. **A Camera Setup button**: create a camera on `camera_bone`, bake the
   bone's animation onto it, and then drive the bone from the camera.

The user wrote the name as "ScerneSetup". Read as `SceneSetup` — "scerne" is
not a word and every other spelling in the request is deliberate. One rename
away from being wrong if that reading is bad.

## Part 1: the rename

Mechanical, with three decisions worth stating.

- **The scene marker attribute stays `mayaWeapon`.** It is written into the
  animator's scene, and there is a sword carrying it in the open file right
  now. Renaming the attribute would orphan that carrier: `find_attached` and
  `linked_carrier` would stop seeing it and Add would happily import a second
  sword. Node names are not our identity, attributes are — and this one is
  already in the wild.
- **The optionVar becomes `mayaSceneSetup_offset_<key>`, with a read-through
  to the old `mayaWeapons_offset_<key>`.** A grip dialled in yesterday
  survives the rename; the new name is what gets written.
- **`show_window` deletes the legacy window id too.** Otherwise the panel
  left open from before the rename stays up, wired to code that no longer
  exists, and there are two windows claiming to be the tool.

Test files follow: `tests/test_weapons_*.py` → `tests/test_scenesetup_*.py`.

## Part 2: Camera Setup

### The relationship is measured, not guessed

A Maya camera looks down its own -Z; a UE camera bone does not. The offset
between them is exactly what the user set up in the open scene, so it was
measured there rather than derived:

```
camera1 in camera_bone's space, 2026-08-17:
    [-1  0  0]
    [ 0  0  1]     euler XYZ (90, 0, 180), translation zero, scale 1
    [ 0  1  0]
```

The camera sits **at** the bone, turned by that constant. `camera1`'s focal
length is 16.493949366848657 — not a default, a framing choice — so it is part
of what gets reproduced.

**Where the offset comes from at run time, in order:**

1. a reference camera in the scene — any camera that is not one of Maya's
   defaults and not the one this tool made. The user said they would place the
   camera as it should stand by default, so a camera they have placed wins over
   anything baked into the code;
2. otherwise the constant above.

Which one was used goes on the status line. A tool that silently picks between
two sources of truth is a tool that lies later.

With several reference cameras, the first by sorted name wins — deterministic,
and named in the status line.

### The bone is found by leaf name, namespace and all

`camera_bone` may arrive namespaced. Resolution order:

1. inside the bound character's subtree through
   `skeleton.scene_map(root)` — namespace-stripped keys, prefix handled;
2. otherwise scene-wide by **leaf name**: every transform whose name after the
   last `|` and `:` is exactly `camera_bone`. Not `ls("*camera_bone")`, which
   also matches `fake_camera_bone`, and not `ls("*:camera_bone")`, which misses
   the un-namespaced one.

Two candidates and no character binding is refused, not guessed.

### What the button does

1. Delete what a previous press made: our marked camera and the parent
   constraint it left on the bone. One camera per bone.
2. Create the camera at world level, mark it with `mayaSceneSetupCamera`, give
   it the reference focal length, and place it at `bone_world · OFFSET`.
3. Bake the bone's motion onto it: a temporary `parentConstraint(bone, camera,
   maintainOffset=True)` — the camera is already standing in the right place,
   so the offset it captures is the one we want — then `bakeResults` over the
   playback range on translate and rotate, then delete the constraint.
4. Invert the drive: delete the bone's own curves on translate and rotate,
   snap the bone to `camera_world · OFFSET⁻¹`, and
   `parentConstraint(camera, bone, maintainOffset=True)`.

Step 4's order is load-bearing. Constraining first and deleting the curves
afterwards leaves a `pairBlend` between the two, which is a rig nobody asked
for; deleting the curves and constraining without the snap lets
`maintainOffset` capture the bone's REST pose against the camera, which bakes a
wrong offset into the constraint for ever.

The bone's animation is not lost — it is on the camera, and the constraint puts
it back on the bone through the same offset it came out of. That is the whole
point: the animator now animates a camera and the export bone follows.

`cmds.bakeResults`, not OverRig: a camera is not a rig knot, there is no
capture-edge problem to pad around, and OverRig's procs are selection-driven
policy we would have to work around rather than with.

### Module layout

New module `maya_scenesetup/camera.py` — `maya.cmds` plus
`maya.api.OpenMaya` for the matrix algebra, the way `maya_overrig/axes.py`
does it. Pure, testable pieces:

- `offset_matrix(euler_degrees)` → the 16 floats,
- `placed_matrix(bone_matrix, offset)` → where the camera goes,
- `bone_matrix_for(camera_matrix, offset)` → where the bone goes,
- `pick_reference(cameras)` → which camera is the reference,
- `is_default_camera(name)`.

The scene-touching parts (`resolve_bone`, `setup`, `teardown`) stay thin.

### Failure modes

| Situation | The button says |
|---|---|
| no `camera_bone` anywhere | `no camera_bone in the scene` |
| two candidates, no character bound | `two camera_bone candidates - connect the picker` |
| the bone's channels are locked | the `setAttr` failure, on the status line |

One press, one undo chunk.

## Testing

Unit: the matrix helpers round-trip (`bone_matrix_for(placed_matrix(m)) == m`),
the reference-camera choice ignores `persp`/`top`/`front`/`side` and our own
marked camera, the leaf-name matcher rejects `fake_camera_bone`, and the
default offset really is the measured one.

**Live proof** — `docs/superpowers/plans/verify_camera_setup.py`:

1. a **sandbox** first: a throwaway joint with real animation on it and a
   throwaway camera, run through the same functions, then the camera is moved
   and the joint must follow it exactly. This is the only place the follow can
   be measured — after a bake the camera's channels are keyed, and rewriting
   the animator's curves to prove a point is not on the table;
2. then the real scene: the bone's world matrices across the timeline before
   and after the setup must be identical, the camera must hold keys, the
   constraint's target must be the camera, and the camera-to-bone relationship
   must equal the offset at every sampled frame;
3. pressing it twice leaves one camera and one constraint.
