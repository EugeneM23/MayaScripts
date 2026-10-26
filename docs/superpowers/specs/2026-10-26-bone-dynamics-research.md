# Bone dynamics: research guide (2026-10-26)

The animator: «Давай сделаем свою систему кинематической симуляции для костей чтобы мы могли удобно
анимировать всякие висюльки и ткань на костях. Система должна включать в себя коллайдеры, возможность
зациклить анимацию, ветер и разные настройки гибкости и тд. Изучи информацию в интернете собери себе гайд и
давай делать».

This is the guide the design is built on: what the known spring-bone systems do, which solver fits our
plugin, how colliders, wind and looping are done, and which pieces of the plugin it reuses. Not a design.

## 1. What exists, and what each one actually does

| System | Model | Per-joint knobs | Colliders | Wind | Notes |
|---|---|---|---|---|---|
| **VRM SpringBone** (UniVRM, three-vrm) | one Verlet particle per joint's TAIL, solved root to tip | stiffness, gravityPower + gravityDir, dragForce, hitRadius | spheres and capsules in collider groups, `inside` mode | `gravityDir` pointed sideways | lengths never stretch; oversized colliders make hair stick out |
| **Dynamic Bone** (Unity) | position-based particles | Damping, Elasticity, Stiffness, Inert, Friction, Radius, each with a *Distrib* curve multiplied along the chain | sphere, capsule, plane; inside/outside | Force vector | Inert = how much of the character's own travel is ignored |
| **Kawaii Physics** (UE, MIT) | PhysX-free pseudo-physics in one AnimGraph node | Damping, Stiffness, WorldDamping, LimitAngle, Radius + curves along the chain; DummyBoneLength past the tip | sphere, capsule, tapered capsule, box, plane, world | gravity, external force, procedural wind, gusts | lengths fixed ("never stretch or collapse"); warm-up pre-roll; teleport thresholds; bone-to-bone distance constraints (skirts) |
| **UE AnimDynamics** | rigid bodies with linear/angular springs | linear damping, spring, angular limits | planar, spheres | wind (`bEnableWind`) | heavier; needs a rig node |
| **Godot SpringBoneSimulator3D** | VRM-style | stiffness, drag, gravity, radius, rotation axis | sphere, capsule (height incl. caps), plane, `inside` | — | capsule with height ≤ 2r behaves as a sphere |

### The VRM update, verbatim (three-vrm `VRMSpringBoneJoint.update`)

```
nextTail = currentTail
         + (currentTail - prevTail) * (1 - dragForce)          // inertia, damped
         + worldBoneAxis * stiffness * dt                      // pull toward the rest direction
         + gravityDir * gravityPower * dt                      // gravity / wind
nextTail = bonePos + normalize(nextTail - bonePos) * boneLength   // length constraint
collide(nextTail)                                              // push out, then length again
prevTail = currentTail; currentTail = nextTail
bone.rotation = fromTo(restAxis, nextTail - bonePos) * initialLocalRotation
```

`worldBoneAxis` is the joint's rest tail direction carried by its PARENT's current frame - so stiffness pulls
toward "where the bone would point if it simply followed its parent" (the animated pose), not a world pose.
Two quirks not to copy: gravity and stiffness are scaled by `dt`, not `dt²` (frame-rate dependent), and the
whole step is per frame with no substeps (VRM clamps dt to ~50 ms to stop it exploding).

### Dynamic Bone's step (its public source, as widely documented)

```
v = p - prevP
prevP = p + characterMove * inert          // inert: ignore part of the character's own travel
p += v * (1 - damping) + force + characterMove * inert
rest = parent's frame applied to the rest local offset
p += (rest - p) * elasticity               // soft pull to the animated pose
maxLen = restLen * (1 - stiffness) * 2     // hard limit: never further than this from the animated pose
if |rest - p| > maxLen: p moves onto that limit
collide (friction adds to damping while touching); keep length to the parent
```

Elasticity is a SPRING to the animated pose; Stiffness is a CAGE around it. Together they read as
"flexibility" to an animator, and both are what makes a chain feel soft or stiff.

### Capsule collision (three-vrm `VRMSpringBoneColliderShapeCapsule.calculateCollision`)

```
d   = p - head ; axis = tail - head
t   = clamp(dot(d, axis) / dot(axis, axis), 0, 1)
c   = head + axis * t                     // closest point on the segment
dist = |p - c| - pRadius - capRadius      // inside mode: capRadius - pRadius - |p - c|
if dist < 0: p -= normalize(p - c) * dist (negated when inside); then the length constraint again
```

A sphere is the capsule with `head == tail`; a plane is `dist = dot(p - origin, n) - pRadius`.

## 2. Vocabulary for our knobs

The same idea under different names, collapsed into what an animator needs:

| Ours (proposed) | VRM | Dynamic Bone | Kawaii | Meaning |
|---|---|---|---|---|
| **Stiffness** (spring to the animation) | stiffness | Elasticity | Stiffness | how hard each joint is pulled back to its animated pose |
| **Damping** | dragForce | Damping | Damping | how fast motion dies; 0 rings for ever |
| **Limit** (cage) | — | Stiffness | LimitAngle | the most a joint may swing off its animated pose (deg) |
| **Gravity** | gravityPower | Gravity | Gravity | constant pull, cm/s² |
| **Inertia** (follow) | — | Inert | SkelCompMoveScale / WorldDamping | how much of the CHARACTER's travel the chain ignores (1 = travel does not drag it) |
| **Radius** | hitRadius | Radius | Radius | each joint's sphere for colliders |
| **Distribution** | — | *Distrib* curves | curves | each knob × a root-to-tip curve (stiff root, loose tip) |
| **Wind** | gravityDir sideways | Force | wind, gusts | direction, strength, turbulence, gust |

## 3. The solver: two candidates

**A. Tail particles (Verlet / PBD)** - VRM / Dynamic Bone / Kawaii. Each joint's tail is a point; integrate,
pull toward the animated pose, cage it, collide, project back to the bone length, root to tip; the joint's
rotation is the least turn from its rest axis onto the new tail direction. Twist about the bone stays the
animation's. Collisions are natural (points vs shapes). Cheap and stable with substeps.

**B. Rotational damped springs** - our Walk Builder's `_limb_motion` and Ragdoll's `plan.spring_step` (exact
for a linear spring). Each joint's rotation error against its target is a 3-vector integrated with
`α = -ω²e - 2ζω·w` plus the pivot's acceleration. Smooth, exact, and the loop machinery already exists
(`ARM_CYCLES` / seam spreading) - but colliders and wind are awkward in rotation space.

Measured choice for here: **A for the motion, with B's discipline** - proper `dt²` units, substeps (4-8 a
frame, frame-rate independent), numpy across all chains at once, gravity and wind in cm/s². Damping per
substep as `(1 - d)^(dt/frame)` so the knob means the same at any substep count.

## 4. Colliders

- Shapes: sphere, capsule, plane (the floor). A capsule drawn from a bone (two joints and a radius) covers
  arms, legs and a torso with three or four shapes per side.
- They MOVE with the character: read every collider's world matrix per frame in the same time walk as the
  chains, interpolate between frames for substeps.
- Per joint `Radius` (with its distribution curve) - the joint's own sphere.
- `inside` (keep a point inside a capsule) is rare; skip unless asked.
- Friction while touching (Dynamic Bone): extra damping on contact so cloth does not skate on a leg.
- Iterate collide + length 2-3 times per substep: a push-out followed by the length projection can push the
  point back in.
- From meshes (auto-fit capsules from a skinned mesh's per-bone vertices, the Ragdoll's median rule) - a
  convenience, not v1 necessarily.

## 5. Wind

- A world direction, a strength (cm/s²), turbulence (smooth noise on strength and direction, our Camera
  Shake's B-spline noise), gusts (a slow envelope).
- Spatial phase: noise sampled at the joint's REST position (or chain index + joint index) so strands do not
  wave in lockstep.
- Wind acts on the tail as a force, scaled by how much the bone faces it (`1 - |dot(bone, wind)|`) so a bone
  pointing downwind does not keep accelerating - a cheap drag model.
- For a loop the wind must be periodic: noise built from harmonics at whole multiples of the cycle frequency.

## 6. Looping

Nobody publishes a clean recipe (the Houdini and Blender threads ask and get no answer; UE's commercial
loopers blend the end into the start). What works, and what our Walk Builder already does for its arms:

1. **Periodic steady state**: feed the source cycle in repeatedly (pre-roll k cycles, starting from the
   animated pose), until the state at the cycle's start stops changing between cycles (a tolerance), then
   record one more cycle. Damped systems converge in a few cycles; Damping near 0 may not - cap the cycles.
2. **Close the seam**: the residual between the recorded cycle's end state and its start (rotation log per
   joint) spread linearly over the cycle (`series = record · exp(-miss · f/n)`), so frame n meets frame 0.
3. Travel: a walk cycle with root motion is periodic only after taking the travel out - the source's
   per-cycle offset is applied as the chain's own travel, Inertia decides how much of it the chain feels.
4. Not looping: **pre-roll** (Kawaii's warm-up) - start the simulation N frames before the range, holding the
   first frame's pose, so frame 1 is not a chain snapping out of its rest.

## 7. What the plugin already has to reuse

- `maya_tools/overlap.py`: chains from a selection (through AS's FKX joints and offset groups), one
  `timewalk.Walk` sampling the chain's world frames, deltas written to a new additive layer
  (`layerbake.write_deltas`), a second press replacing the first, Keep edges, Cycled, a highlight. Its
  math (`overlapplan.py`) is a kinematic lag - no forces, colliders or wind. The new system can be the
  same scene half with a dynamic model.
- `maya_ragdoll/plan.py`: `spring_step` (exact damped spring), capsules from skinned vertices (median rule),
  a rig's drives.
- `maya_walk/model.py` `_limb_motion`: substeps, pivot acceleration from low harmonics (trap 234), the
  periodic steady state and seam spreading.
- `maya_camshake.py`: seeded smooth noise in blocks, rates measured in frames (trap 238).
- `maya_hubmotion`, `docs/interface-motion.md`: the card's look and motion.

## 8. Traps that apply

- Euler continuity on every baked rotation (trap 108); rotations written as the nearest euler.
- Accelerations from a smooth fit, never second differences of sampled frames (trap 234).
- `getAttr(time=)` is stale through constraints and layers (traps 69, 232, 236): sample in a real time walk.
- A same-frame `currentTime` re-evaluates every curve (trap 206): the walk restores tweaks.
- Animation layers go through `maya_tools/layered.py`; the active layer rules.
- Session state on `sys` (trap 111).
- Scene Time Warp: walks and bakes go through `maya_timewarp` / `timewalk.Walk`.
- Maya Bullet is unsuitable: it does not step with Cached Playback on (275) or refresh suspended (266), and a
  per-press build is heavy - our own numpy solver instead.

## Sources

- three-vrm `VRMSpringBoneJoint.ts`: https://github.com/pixiv/three-vrm/blob/dev/packages/three-vrm-springbone/src/VRMSpringBoneJoint.ts
- three-vrm `VRMSpringBoneColliderShapeCapsule.ts`: https://github.com/pixiv/three-vrm/blob/dev/packages/three-vrm-springbone/src/VRMSpringBoneColliderShapeCapsule.ts
- VRM spring implementation notes: https://vrm.dev/en/api/spring/spring_and_scaling/
- VRM spring settings (VirtualCast wiki): https://wiki.virtualcast.jp/wiki/en/vrm/setting/spring
- Kawaii Physics: https://github.com/pafuhana1213/KawaiiPhysics
- Dynamic Bone ReadMe: https://g.freya.cat/unityprojects/plain/VRCSDK3AvatarsLegacy/Assets/Resources/DynamicBone/ReadMe.txt
- Dynamic bone chain parameters (Resonite): https://wiki.resonite.com/Dynamic_bone_chain_parameters
- Godot SpringBoneCollisionCapsule3D: https://docs.godotengine.org/en/4.5/classes/class_springbonecollisioncapsule3d.html
- UE physics damping: https://dev.epicgames.com/documentation/en-us/unreal-engine/physics-damping-in-unreal-engine
- Houdini KineFX looping secondary motion thread: https://www.sidefx.com/forum/topic/92351
- Cinema 4D cycle modes for loops: https://novedge.com/blogs/design-news/cinema-4d-tip-timeline-cycle-modes-for-seamless-loops-and-root-motion
