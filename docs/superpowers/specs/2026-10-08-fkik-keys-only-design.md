# Connections FK / IK: keys where the arm has keys, not on every frame (2026-10-08)

The animator: «Нужно сделать так чтобы наш переключатель FK IK во вкладке конекшн при запекании ключей
запекал не весь таймлайн а только те ключи которые уже стоят. Тоесть если на ФК руке 3 ключа то и на ИК
тоже должно быть 3 ключа и наоборот. Нужно избавится от запекания лишних ключей».

Asked, both the recommendation:

- **which frames**: the arm's own keys AND the keys of everything it hangs on (clavicle, spine, pelvis,
  Main). The IK hand lives in Main's space and does not ride the body, so a body key on a frame where the
  arm has none is a frame where the shown hand changes its course; without a key there the IK hand would
  stand off the FK one at that very key pose. In blocking, where the whole character is keyed on the same
  frames, it is exactly "3 keys -> 3 keys";
- **tangents**: as the source keys' (stepped stays stepped, linear linear, auto auto); where they differ
  on a frame, Maya's default.

## What changes

`fkik.switch(arm, mode, span)` walked `range(start, end + 1)` and keyed every frame. Now (the default,
the Connections buttons) it keys only **the frames something that moves the shown arm has a key on**:

- **the source**: what the arm shows - the FKX chain (blend at 0 everywhere), the IKX chain plus the IK
  control and the pole (blend at 10), both plus the blend (a mixed take) - the same rule `_sample`
  already reads;
- **the walk** (`driving_curves`, scene): upstream from the source, at the level that moves a world
  matrix: a transform's transform inputs (translate, rotate, scale, shear, orients, pivots,
  offsetParentMatrix, inverseScale) and its parent; a DG node's every input; a DAG node met through a
  non-transform plug (`IKArm.Lenght1`, `FKIKArm.FKIKBlend`, a follow attribute) - that plug's own input;
  a shape or an IK handle - every input and its parent; a joint - the IK handles it starts. Every time
  curve met (`animCurveTL/TA/TT/TU`; driven keys are not time) is a source of frames. So the arm's own
  curves, the clavicle's, the spine's (FK and IK), the pelvis's, Main's, an animation layer's, and the
  curves behind constraint weights are counted; the other arm, the legs, the fingers, a control's
  visibility are not (nothing of them is upstream);
- **the frames** (`key_frames`, pure): over the whole take every such key time; over a highlighted range
  the key times inside it **plus the range's first and last frame** - the blend steps there, so the new
  mode must stand on the shown pose there whatever the keys;
- **nothing keyed** (whole take): nothing moves the arm, it stands still - one sample at the current
  frame, written as plain values (the existing constant rule), no key;
- **tangents** (`tangent_for`, pure): the in and out types of the source keys on that frame - first the
  curves of the arm's own controls (FK controls; IK control and pole), else every walked curve keyed
  there; a type is used where they all agree, `fixed` never (its angle belongs to the other curve), else
  Maya's default;
- **the measure** walks the key frames only (the promise is "the pose at every key"; between keys each
  chain interpolates its own way - FK rotations against an IK hand's path - which the animator accepted
  with the request), and the line says the count: «Arm_R to IK on 4 keys (0..24) - the arm kept to ...».

Unchanged: the euler nearest the key before (trap 108), the constant collapse over a whole take, the
blend unkeyed over a whole take and stepped around a range, the solve attributes reset, the refusals,
one undo chunk.

**Hand -> Weapon keeps the every-frame switch** (`connections._follow`, `switch(..., every_frame=True)`):
the IK control is then constrained to a proxy whose track is baked on every frame anyway, so keys-only
there would only make the hand's path between keys the IK's instead of what it showed.

## Proof

- unit tests: `key_frames`, `tangent_for`, `sources`, the plug classification, the message;
- `docs/superpowers/plans/verify_fkik_keys.py`, mayapy standalone on Manny_Rig and Creep_Rig, hand keys:
  the FK arm keyed on 3 frames, the clavicle on a 4th -> the IK control keyed on exactly those 4, the
  arm on its keys to the shown pose, stepped kept stepped; back to FK on the same 4; a range; nothing
  keyed -> plain values, no key; Main keyed on a 5th frame counted; the other arm's and the legs' keys
  not counted;
- `verify_fkik_switch.py` again (a retargeted take is keyed on every frame: the result is the old one).
