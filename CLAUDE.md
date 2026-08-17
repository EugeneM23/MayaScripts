# MayaScripts — working notes

Read this first. It is written for a fresh session with no conversation history:
what exists, how to run and verify it, and the things that already went wrong so
they do not go wrong again.

## What is here

Two things, with different conventions:

- **Root-level `maya_*.py`** — standalone single-file tools, pure `maya.cmds`, no
  Qt, no package. Leave that style alone when touching them. Tools the packages
  superseded live in `archive/` (moved 2026-08-17; its README says why each).
- **`maya_overrig/`** — a Python wrapper around the **OverRig** MEL toolset. This
  is the active work. It uses Qt and is a package, deliberately breaking the
  flat convention; see `docs/superpowers/specs/2026-08-14-overrig-picker-design.md`.

OverRig itself is third-party MEL by Pavel Barnev, v10.2, living at
`C:/!!!Work/Animations/Scripts/base_OverRig_scripts_V10_2_f1/base_OverRig_scripts.mel`
— ~394 global procs in one 516 KB file, sourced by a button on the user's Custom
shelf. `function_for_hotkeys.TXT` next to it is the closest thing to an API list.

The user is an animator at a game studio. The target rig is a stock **UE5 Manny**
skeleton (`root`, `pelvis`, `spine_01..05`, `clavicle_*`, `upperarm_*`, `thigh_*`,
full fingers with metacarpals, plus export helpers `ik_foot_root`, `ik_hand_gun`).

## Driving the user's live Maya

The user can open a command port, and that is how everything here gets verified.
They run this once per Maya session:

```python
import maya.cmds as cmds
if not cmds.commandPort(":7001", query=True):
    cmds.commandPort(name=":7001", sourceType="python", echoOutput=False)
```

`echoOutput=False` matters: with echo on, heavy operations (OverRig bakes echo
every `autoKeyframe`) push megabytes at the client, and a client that stops
reading breaks the pipe under the running command. Results travel through the
output file anyway, so the echo buys nothing. If echo is on, the sender must
DRAIN the socket while polling for the output file, never close early. And do
not try to close/reopen the port from a command sent over that same port — the
reopen races the still-connected client and fails with "address in use",
locking you out until the user re-runs the one-liner.

Then code goes over TCP to `127.0.0.1:7001`. The working pattern is: write the
code to a file, send a one-line `exec(open(...).read())`, and have a runner
capture `stdout`/`stderr` into an output file you read back — that gives full
tracebacks instead of success/failure. Rebuild the runner + sender in the
scratchpad when needed; it is a dozen lines each.

Four things that will waste a run if forgotten:

1. **The socket reply is not a "done" signal.** With `echoOutput=True`, warnings
   printed by *other* tools arrive mid-run. AdvancedSkeleton's panel is a
   reliable source of them since it reacts to every selection change. Poll for
   the output file instead.
2. **The port dies with Maya.** After a crash the user must re-run the one-liner.
   Check `Get-NetTCPConnection -State Listen -LocalPort 7001` before blaming code.
3. **To screenshot a Qt panel, use `widget.grab().save(path)`**, not a desktop
   capture. Other windows sit on top, and the virtual desktop starts at
   `X=-2560` on this machine, so screen-coordinate arithmetic is easy to get wrong.
4. **The user works in the scene while you do.** Scene state changes between
   runs. Never assume the state a previous run left; re-read it, and make
   verification scripts bind explicitly rather than relying on auto-connect.
5. **The port executes one sent line TWICE** (measured: run-once guards
   tripping inside a single send, twice in a row). The second pass runs after
   the first completes and re-runs the whole script over the scene the first
   pass just changed — it overwrote result files with trivially-clean numbers
   and derailed a whole investigation. The runner must be idempotent: create
   a `<out>.ran` marker first thing, `SystemExit` silently when it exists,
   and give every run its own output file name.

## Running tests

There is **no system Python** — `python` resolves to the Microsoft Store stub.
Use Maya's interpreter, and never `pip install` into the Maya tree.

```
& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v
```

Qt tests run headless with `$env:QT_QPA_PLATFORM = 'offscreen'` (PySide6 6.8.3 /
Qt 6.8.3 ship with Maya 2027). 564 tests at time of writing, all passing.

Testing code that needs `maya.cmds` without a Maya session: inject a fake into
`sys.modules` and **rebind the module attribute** (`naming.cmds = fake`). Do not
try to force a re-import by deleting `sys.modules["pkg.module"]` — the stale
module stays bound as an attribute of the parent package, so the next
`from pkg import module` hands back the old object. That cost a debugging round.

In PowerShell, avoid `2>&1` on `mayapy` — unittest writes to stderr and 5.1 turns
that into `NativeCommandError` noise. Also avoid here-strings containing double
quotes for `git commit -m`; write the message to a file and use `git commit -F`.

## `maya_overrig` architecture

| Module | Responsibility | May import |
|---|---|---|
| `bodymap.py` | 64 FK buttons + 11 IK circles, pure data | **stdlib only** |
| `pickerstate.py` | Button-to-controller resolution, pure | **stdlib only** |
| `naming.py` | Skeleton root discovery, name resolution, prefix detection, UUID binding | `maya.cmds` |
| `picker_view.py` | Qt scene, button items, painting, input | **Qt only** |
| `picker_window.py` | Window, toolbar, Maya selection wiring, scriptJob | Qt + `maya.cmds` |
| `overrig.py` | Thin binding to the MEL toolset, no policy | `maya.cmds`, `maya.mel` |
| `builder.py` | Limb table, manifest, build / bake / teardown policy | `maya.cmds`, `naming`, `overrig` |
| `axes.py` | Rotation algebra for controller axes, pure | `maya.api.OpenMaya` only |
| `fkchains.py` | Chain tables + pure chain resolution (chain_root, innermost_owner, ...) | stdlib + `builder` (for `_is_inside`/`LIMBS`) |
| `fkrings.py` | Ring sizing from the skin, knot dressing | `maya.cmds`, OpenMaya, `bodymap`, `naming`, `fkchains` |
| `fkalign.py` | Controller axis algebra (align/orient) | `maya.cmds`, OpenMaya, `axes`, `fkchains` |
| `fkcontrols.py` | FK build/bake/switch orchestration; re-exports the three above | `maya.cmds`, `maya.mel`, `bodymap`, `builder`, `overrig` + the three above |

**Load-bearing rules — do not break these:**

- `bodymap.py` imports nothing outside the stdlib, `picker_view.py` never imports
  `maya.cmds`. A subprocess test in `tests/test_bodymap.py` enforces it.
- `__init__.py` resolves `show_picker` through `__getattr__` so importing the
  package does not drag Qt and Maya in. Making that import eager breaks the
  plain-Python tests.
- The fiddly logic is deliberately pushed into **pure functions taking the scene
  as data** (`order_by_nesting`, `foreign_knots_inside`,
  `detect_prefix`, `unrecorded_rig_roots`). Test those; keep the Maya-touching
  wrappers thin.

Entry point:

```python
import sys; sys.path.append(r"C:/!!!Work/MayaScripts")
import maya_overrig; maya_overrig.show_picker()
```

## What the tool does today

**Rig Picker** — an anatomical T-pose body map, 64 FK buttons plus 11 IK
circles (end + pole per limb, top/mid/bot for the spine), front view with the
character's left on the viewer's right. Click selects, `shift` adds, `ctrl`
toggles, drag marquee-selects, wheel zooms, middle-drag pans.

**The picker selects controllers, never bones.** A button is live exactly when
its controller exists right now — FK buttons resolve `<joint>_FK_ctrl` by
name, IK circles resolve through `builder.ik_control(limb, role)` and the limb
manifests. Everything else is dimmed and unclickable: before a build the whole
map is inert, a limb switched to IK dims its FK buttons and lights its
circles. Availability is recomputed on every selection sync
(`picker_window.sync_from_scene` → `_resolution` → `pickerstate.resolve`), so
builds, bakes, switches and manual deletes all show up immediately.

**Connect** binds the panel to one skeleton. Any joint of the character works —
it climbs to the root — as does the enclosing group. The root is remembered by
UUID so renaming or regrouping does not break the link. A single-skeleton scene
connects on open. Every lookup goes through the bound subtree, which is what
makes namespaces and per-joint prefixes a non-issue.

**Build** (the only build button) tears down whatever exists — FK baked back
first, then IK, because finger controls can hang inside IK hand controls —
and builds fresh in one undo step (`fkcontrols.rebuild`). Every entry point
that runs MEL — `build_fk`, `rebuild`, `switch_limbs`, `bake_fk`,
`bake_selection`, `builder.build`, `builder.bake_limbs` — calls
`overrig.ensure_loaded()` first and returns `overrig.NOT_LOADED_MESSAGE`
when the toolset cannot be found at all (trap 20). Default: the hybrid
rig — IK arms and legs (`builder.DEFAULT_IK`), FK on root/spine/neck/fingers
(`HYBRID_FK_CHAINS`), finger chains hung on the IK hand controls via
`apply_Parent_in`. With the **FK Limbs** toggle pressed: full FK on all 17
chains (the old Build FK). No clavicle or ball controls in hybrid — same as
the post-Switch IK state; switching a limb to FK brings them back.

**The spine is FK-only for now.** A full spline-IK spine (own module
`spineik.py`, three controls, hipdrive pelvis carry, per-end advanced
twist) was built, live-verified and then REMOVED at the user's call
(2026-08-15, "в будущем вернемся"). The complete implementation, its
verify scripts and the design spec history live at commit `0e0794f`; the
spec `2026-08-15-spline-ik-spine-design.md` documents every decision and
every trap it fought. The `CHAINS` split of `pelvis` from `spine` is KEPT —
it is harmless in FK and is a prerequisite for the IK's return. Selecting
a spine bone and pressing Switch now says "select an arm or leg".

**Bake+Delete bakes ONLY what the selection touches** onto clean bones —
controllers, bones, or picker buttons — and everything else stays rigged
(`fkcontrols.bake_targets` resolves, `bake_selection` orchestrates). One
resolution across BOTH manifest kinds with the **innermost owner winning**
(`innermost_owner`): FK controllers nest, and "descendant of any member"
once resolved a hand-controller click into root+pelvis+spine+arm at once —
Bake+Delete then wiped the whole FK rig. An IK limb takes its riding finger
chains down with it; FK chains bake per chain, expanding to whatever rides
inside them (a chain cannot outlive its container). Nested rigs are baked
before their container.

**Switch auto-builds**: selecting any bone of a switchable chain (viewport
or picker) with no rig on that chain makes the first Switch press build its
IK; the next press converts to FK as usual (`switchable_bones` resolves
bones to chains, including clavicles and balls).

**The FK engine** (`fkcontrols.build_fk`, driven by Build) builds real FK
controllers through OverRig knots: up to 17 chains over the 64 bones
(`apply_ForwHierarhy` per chain, `apply_parentConstrAnim` for root), existing
animation baked onto the controllers, our sized rings attached as shapes on
the knots, machinery locators/joints hidden. The whole capture loop runs
inside `overrig.full_rate_capture` — DOUBLED time — because OverRig's capture
only samples its aim rig on every second frame (trap 35); the entry points
refuse to run under a time-slider highlight (trap 36). `only=` restricts it to named
chains — the hybrid Build and Switch both use that. Chains are then
**coupled** with `apply_Parent_in` (selection: child first, parent last): each
chain-root controller hangs off its parent bone's controller, animation re-baked
into the new local space (zero drift verified) — never use a bare `parent` for
this, it preserves only the current frame. FK/IK exclusivity per bone is kept
by `rebuild`'s teardown; mixed scenes (per limb) are normal after Switch.
`Bake+Delete` with FK present bakes the whole FK back. Ring sizing comes from
the skinned mesh, not bone length; a correction table (`_BORROW`/`_SCALE`) holds
user-driven fixes, and `_SQUARE` lists bones drawn as a square instead of a ring
(pelvis, so it reads among the same-size spine rings). Knot→bone mapping is read from the BONE side (constraint →
driver → ancestor walk): a ForwHierarhy knot drives its bone through a child
locator, so looking for constraints on the knot itself finds nothing.
Since the 2026-08-17 split the implementation lives in three modules —
chain tables/resolution in `fkchains.py`, sizing/dressing in `fkrings.py`,
the axis algebra in `fkalign.py` — all re-exported by `fkcontrols`, so
every `fkcontrols.<name>` below still resolves.

The last step of a build **re-expresses every controller in its bone's axes**
(`axes.py`, `fkcontrols.align_controllers`). OverRig's knots come out on a
convention of their own, so a mirrored pose read as unequal values and no
mirroring tool could make sense of them. The fix rests on two measured facts: a
joint's world rotation is `rotateAxis · rotate · jointOrient · parent`, and the
rotation offset `C` between a knot and the bone it drives is constant over time
(1e-14 across frames). So `rotateAxis` takes `C⁻¹`, `jointOrient` takes what the
controller held at the build pose, and every rotate key is conjugated into the
new frame. The product the DAG consumes is unchanged **by construction** —
nothing moves, no constraint is touched, no node is created — and the operation
is idempotent because it works from the whole `rotateAxis · rotate ·
jointOrient` product rather than the rotate channel alone. Afterwards every
controller reads zero at the build pose and **equal values on both sides give a
mirrored pose** (verified: 0.0004). Two things to know: OverRig **locks
`jointOrient`** on its knots, so it is unlocked and re-locked around the write,
and the write order matters — a `rotateAxis` without its `jointOrient` moves the
bone. `root` is skipped: `apply_parentConstrAnim` builds it as a plain
transform with no `jointOrient`, and a lone centre control has nothing to be
symmetric with.

That alignment puts the rotate CHANNELS in the bone's axes but leaves the
knot's **own** frame where OverRig put it — measured 85–97° rolled about the
bone on the left, ~180° on the right. That frame is everything an animator can
see of a controller: the rotate manipulator in its default Local mode, the
local rotation axes, the way a dragged handle turns. So typing numbers worked
while grabbing the manipulator did not ("оси контролов не совпадают с осями
костей"). A second step, `fkcontrols.orient_controllers`, **turns each knot in
place onto its bone's frame**: `rotateAxis` takes `C · rotateAxis` (which,
after the alignment has left `C⁻¹` there, comes out exactly zero) and every DAG
child is counter-corrected so nothing below the knot moves. The bone is driven
from a locator hanging under the knot, so that counter-correction is the whole
safety argument — and it has **two halves, both required**: the child's local
rotation takes `C⁻¹`, and its local translation is TURNED by `C⁻¹` (trap 29).
Constraint nodes are skipped (OverRig parks a dead `aimConstraint` under every
knot and a constraint never reads its own transform). Idempotent, because it
works from the measured offset: once the knot stands on its bone the offset is
identity. Verified live: 180.000° → 0.00002°, bones unmoved to 4.9e-07 over 64
bones × 60 frames, a finger now turning about exactly the axis you grab
(85.19° → 0.000°), and — the check the previous design retired as unreachable
— all 19 left/right pairs' rest frames now mirroring as the skeleton does.
`root` and `pelvis` are untouched: `apply_parentConstrAnim` builds them as
plain transforms with no `jointOrient`, their frames already match their bones,
and putting their CHANNELS on the bone's axes needs an offset group above the
control — which is what every IK limb hangs on. Deliberately not done.

Two hard-won facts about this rig: bind orientation lives in the joints' ROTATE
channels, not jointOrient — non-zero local rotates are NOT a bent skeleton, and
`dagPose` restore is the way to check. And **Build FK bakes the pose the
skeleton stands in** — verify the pose before building; a proposed safety
(snapshot a dagPose before every build) is not yet implemented. The build pose
is also the reference the axis alignment zeroes against, so a lopsided build
pose costs the mirror symmetry as well as the animation.

**A chain starts at the first bone the skeleton HAS, not at the first bone
of the table.** `chain_root` / `chain_tip` / `chain_root_control` (pure) are
what every step asks: coupling, the finger hang in `rebuild`, the rider lift
and re-hang in `switch_limbs`, and the rider detection in `bake_selection`.
UE4-schema rigs have no metacarpals, stop the spine at `spine_03` and carry
no `neck_02`, and some have no `root` joint at all — see trap 21. With no
`root` bone there is no whole-character control, so the IK limbs stay
anchored in world and Build says so ("no root bone - IK limbs stay in
world"); hanging them on the pelvis instead would drag the planted feet, so
that is deliberate, and a synthetic master control is not built.

**Switch FK/IK** converts whatever arms/legs/spine the selection touches to
the opposite rig type, per limb, animation re-baked at every step
(`fkcontrols.switch_limbs`, table `SWITCHABLE`). The FK manifest is per-chain
(`RigPicker_fk_<chain>`; the flat `RigPicker_fk` is legacy, absorbed by a full
bake). Fingers ride through an arm switch: `apply_Parent_out` lifts them to
world, the arm converts, `apply_Parent_in` hangs them on the new hand control
— they are DAG children of what gets deleted, so anything less loses them.
A chain with no rig at all auto-builds its IK on the first Switch press.
`apply_Parent_out`/`_in` semantics (both verified by experiment): selection is
child-then-parent for `_in`, the child alone for `_out`; both re-bake into the
new space with zero drift. Mixed FK/IK states are normal.

**Fingers on an IK arm hang on `<limb>_IK_anchor`** — a hidden locator
riding the hand BONE, parented under the IK end control (created on demand
by `fkcontrols._limb_anchor`, recorded in the limb manifest) — never on the
IK control itself: past full extension the control keeps travelling while
the bone stops, and fingers riding the control tore off the hand (measured:
hand-to-metacarpal 33 cm on a 40 cm overpull; with the anchor it stays at
the 4.2 cm rest). The limbs themselves do NOT stretch — OverRig's rebike
keeps bone lengths constant (measured identical under overpull) — so no
extra no-stretch work was needed. The anchor hides its SHAPE, never its
transform — see trap 15.

**Every IK limb rides `root_FK_ctrl`** — all three OverRig top groups
(`_IK_strech_gr`, `_IK_knee`, `_IK_feet`) hung with `apply_Parent_in`
(`fkcontrols.hang_ik_on_root`), so the root control carries the whole
character. All three, machinery included: the IK rig is anchored in world
end to end (measured — moving the root BONE moved neither the controls nor
the `upperarm` bone), so carrying only the two animator controls drags the
effector targets while the chain base stays pinned and the shoulder tears
off. The coupling nodes go into the LIMB manifest, so they die with the IK
rig. No root controller in the scene (IK built by Switch after a full bake)
means the rig stays in world; the next Build re-hangs it. Verified: bones,
IK controls and finger rings all travel 50.000 cm with the root control.

The reverse is automatic. `_bake_fk_chains` **lifts** any riding IK limb to
world (`lift_ik_off_root`) before deleting a chain that contains it, so
Bake+Delete on root leaves the IK limbs alive and working, and the FK-first
teardown inside every full Build no longer destroys four IK rigs unbaked.
Two ordering rules there, both paid for in a live run: **re-read the
manifests after lifting** — `overrig.set_members` resolves long paths at
call time, and a stale path deletes nothing while leaving a live rig
orphaned and unrecorded — and **lift before expanding by nesting**, because
a finger chain sits inside the root controller only by way of the IK hand,
and that hand survives. Containment through a surviving rig is not
ownership (trap 9 again, from the other side).

Not built: spine IK (removed, see above) and neck IK; per-chain FK bake
from the UI (Switch does it internally); docking; mirror-select; the
pose-snapshot safety before Build (proposed, not confirmed).

**Live verification: all green** (run in the Manny scene):
`verify_arm_switch.py`, `verify_capture_edges.py`,
`verify_control_axes.py`, `verify_hybrid_build.py`,
`verify_ik_under_root.py` in `docs/superpowers/plans/`.
`verify_control_axes.py` builds the rig itself in two halves — once with
`orient_controllers` suppressed, then for real — so the turn is measured on
its own rather than inside a whole build. `verify_missing_bones.py` runs in an EMPTY
scene instead — it builds its own UE4-schema skeleton (no root, no
metacarpals, spine to `spine_03`) and is the proof for traps 20 and 21;
run it in a FRESH Maya, since half of what it proves is that the first
Build of a session sources OverRig by itself. Bridge-script
hygiene, learned the hard way: never `cmds.undo()` inside a bridge script
(the whole script is one command — undo reverts a whole prior chunk and the
damage gets baked in), and never write literal rest values into constrained
or animated channels — read the value first and write it back (`pushed`
context manager in the verify scripts).

Known gap in the axis alignment: **the reference is the pose at build time**, so
`Switch FK/IK` — which rebuilds one limb through `build_fk(only=[limb])` — zeroes
that limb against whatever pose the character is in at the moment of the switch,
while the opposite limb keeps the zero of the original build. Equal values then
stop meaning a mirrored pose for that pair. Referencing the skeleton's bind pose
instead of the current one would close this and would also make Build FK
mirror-correct from a lopsided pose; it needs the bind local rotations read from
the `bindPose` node (readable without restoring it) and a `T_ref = C⁻¹ · b_bind ·
C_parent` construction rather than a measurement.

## OverRig facts, learned by reading the MEL and by being bitten

- **Most procs are selection-driven.** `apply_Fast_Bake`, `apply_range_Fast_Bake`,
  `apply_Bake_to_layer`, `delete_constraint_attributes_on_objects` all act on the
  selection. Only `barn_fast_bake_source_obj_and_delete_knots()` is scene-global,
  and only because it selects the whole set first. **Never call that one** — it
  destroys the user's hand-made OverRig setups.
- **`return_constrained_object(1)`** maps a selected knot back to the object it
  drives. Useful; the `SelCon` button on the OverRig dock.
- **IK: exactly three joints selected (root, middle, end) takes the named-
  controls branch** — `_IK_strech_gr` / `_IK_knee` / `_IK_feet` renames. Four
  or more takes a different branch entirely ("spider leg": `base_IK_ctrl`,
  `IK_knee_ctr`, one `inner_rotate_ctr` per extra joint, unnamed `Z_IK`
  groups). Neither fits a torso — that is why the (since removed) spine IK
  was a custom spline rig, preserved at `0e0794f`.
- **The IK proc reads the timeline range** (`timeControl -q -ra`) and bakes across
  it. Not a no-op even on an unanimated skeleton.
- **`OverRig_knots` does not record everything OverRig creates.** It holds the
  three renamed groups per limb. The locators, expressions, `pairBlend` nodes and
  the *second* parentConstraint on each source joint are in no set at all. This
  caused a whole class of bugs.
- **OverRig renames collide.** If `foot_l_IK_feet` exists, the next build produces
  `foot_l_IK_feet1`. Never identify rig nodes by name — use manifest membership.
- **The IK rig contains joints of its own** (`fin_jnt11`, `knee_ctrl`) with no
  joint parent.

## Animbot, which the user has installed and mirrors animation with

- **Its buttons cannot be clicked from script.** `CORE.Tool_mirror_mirrorPose`
  is a Qt widget, and `click()`, `animateClick()`, `trigger()` and emitting
  `clicked`/`clicked_` all return quietly having done **nothing**. That reads
  exactly like "the tool ran and decided not to act", and it cost most of a
  session. The route that works is the module instance:
  `from animBot._api.core import CORE; CORE.mirror.mirrorAllKeys_click()`.
  Flush the idle queue afterwards (`QApplication.processEvents()` plus
  `maya.utils.processIdleEvents()`) before measuring.
- **`snapshotMirrorSettings_click()` blocks Maya from a command-port call** —
  it puts up a modal dialog with nothing to click it. Do not send it through
  the bridge; ask the user to press the button.
- **It pairs our controllers by name already**: `Select Opposite` finds
  `upperarm_r_FK_ctrl` from `upperarm_l_FK_ctrl` with no setup.
- **It guesses a per-channel sign pattern from the rig** and caches what it
  learns per controller, so a stale guess can outlive the rig that produced it.
  `Clear Mirror Settings Data` is the reset. Four rest-frame conventions were
  built as isolated control pairs and mirrored: `(-1,-1,-1)` and `(-1,+1,+1)`
  mirror exactly, `(+1,-1,+1)` — what OverRig's raw knots use — does not.

## Traps already hit — each cost a debugging round

1. **IK joints look like extra skeletons.** Root detection asks "a joint with no
   joint parent", so after a four-limb build the scene reported 13 skeleton roots
   and the picker refused to auto-connect. Fixed by
   `find_skeleton_roots(exclude_under=...)` fed from `OverRig_knots` via
   `builder.character_roots()`.
2. **Prefix matching vs. UE helpers.** A suffix match for `hand_l` also hits
   `ik_hand_l`. The prefix is therefore derived **once for the whole skeleton**
   (`detect_prefix`), and adopted only if it beats using no prefix at all.
3. **A manifest built from `OverRig_knots` misses most of the rig.** Baking then
   left a live constraint driven by a locator nothing tracked. The manifest is now
   a diff of **every node in the scene** across a limb's build, minus `animCurve`
   types — those hold the baked animation and must outlive the rig. ~68 nodes per
   limb, not three.
4. **The constraint node outlives its driver.** It is a child of the source joint,
   so deleting the rig root leaves the joint still reporting a constraint. Delete
   it explicitly.
5. **Walking out from a joint only reaches part of the rig.** `_IK_feet` and
   `_IK_knee` drive the IK handle, not the joints, so they survived as stray
   locators. `_rig_closure` expands across connections, following only nodes whose
   top-level ancestor is in `OverRig_knots` — which stops the walk at the skeleton
   and keeps it out of neighbouring limbs.
6. **Nested rigs lose their animation.** Parking the hand's control under the
   foot's and baking the leg destroyed the arm's rig unbaked. `order_by_nesting`
   bakes innermost first.
7. **Path prefixes need the separator.** `|foot_l_IK_feet_extra` is not a child of
   `|foot_l_IK_feet`. `_is_inside` guards this; a test locks it.
8. **The manifest diff must run on real UUIDs — and getting them is a trap
   of its own.** A long-path diff records re-parented nodes as fresh
   (`apply_Parent_in` re-parents controllers; the spine manifest swallowed
   the pelvis controller and both FK legs). A NAME diff survives
   re-parenting but breaks on duplicates: OverRig reuses `fin_jnt1` inside
   every limb rig, and when a second appears, the first one's listed name
   changes from `fin_jnt11` to `...|fin_jnt11` — both strings read as new,
   and one arm's joints landed in the other arm's manifest (bakes then
   dragged the wrong limb in and aborted). And the obvious fix is booby-
   trapped: **`cmds.ls(uuid=True)` with no object arguments silently
   returns plain names, not uuids** (measured in Maya 2027) — the flag only
   converts when objects are passed. `builder._scene_nodes()` therefore
   does `cmds.ls(cmds.ls(), uuid=True)`.
9. **Rider detection by containment alone over-lifts.** Finger chains sat
   inside the (since removed) spine IK's containers transitively, got
   lifted to world and detached from the hand ("everything moves except
   the fingers"). The rule that fixed it: lift only chains whose OWN
   attach bone belongs to what is being converted; deeper chains ride
   their parent chain's subtree.
10. **`sets -q` plus one bulk `ls` expands ambiguous names to every match.**
   `overrig.set_members` resolves member by member and settles ambiguity
   with `sets -isMember`, or duplicate short names leak other rigs' nodes
   into a manifest.
11. **A silently ignored bake abort builds FK over live IK.** That was the
   user's "pieces of IK remain after the switch"; the leftover constraint
   then led `_reclaim`'s closure through the coupled controllers (every
   controller is an OverRig knot now) and deleted the whole rig except the
   limb being switched. `switch_limbs` now respects the abort (riders are
   re-hung, the reason reaches the status line), `_reclaim` never dooms
   anything recorded in a RigPicker set, and the bake guard distinguishes
   foreign knots from recorded dependent chains.
12. **OverRig's capture procs clip a frame at each end of the range.** A
   pose keyed only at the edge frames (exactly what posing over dense
   baked keys produces) came out of `apply_ForwHierarhy` as a constant
   interior track — fingers "fell" on rebuild. `overrig.padded_range()`
   pads by one frame around the CHAIN CAPTURE procs only
   (ForwHierarhy/parentConstrAnim/rebike); Fast_Bake and Parent_in/out
   measured clean without it and blanket padding caused its own glitches.
13. **First build of a session records OverRig's own sets.** OverRig_knots
   and OverRig_rig_objects are CREATED by the first build, so they landed
   in that limb's manifest diff and died with it. `_recordable` skips
   OverRig*/RigPicker* objectSets, and bake_limbs re-filters members for
   existence right before deleting (stripping constraint channels already
   kills recorded pairBlends).
14. **Interactive probes over the port lie without a time change, and the
   user runs autoKey ON.** Reads after a bare setAttr return stale
   mixtures across nodes (phantom "leaks" of 3-11 cm that vanished under a
   time wiggle), and a scripted poke at a KEYED channel writes real keys —
   or, restored via setKeyframe, rewrites tangents and damages neighbours.
   Verify scripts wiggle time to settle, disable autoKey around pokes, and
   never mutate keyed curves.
15. **Hiding a rig helper's TRANSFORM hides whatever is parented under it.**
   `_limb_anchor` hid the anchor locator's transform, and the finger
   controllers hung on it inherited the invisibility — the rings existed and
   the picker selected them happily, but the viewport showed nothing
   ("переключаешь руку в ИК — ФК контролы пальцев не отображаются"). Hide
   the SHAPE, which is what `_hide_rig_machinery` already does for locators;
   `_mute_anchor` repairs anchors rigged by the old code on every lookup.
16. **A recorded long path is only valid until something re-parents it.**
   `overrig.set_members` resolves paths at call time, so any manifest read
   before an `apply_Parent_in`/`_out` is stale afterwards. The existence
   filter in front of `cmds.delete` then silently drops those nodes: a whole
   rig survived unrecorded, and the next bake correctly refused to touch
   strangers ("holds OverRig node(s) we did not build"). Re-read manifests
   after any re-parenting.
17. **A file exec'd over the command port may not see its own module-level
   names.** `exec(open(path).read())` sent as a one-liner runs where
   `globals()` is not `locals()`, so functions defined in that file raise
   `NameError` on module-level imports — which reads like a broken import
   rather than a harness bug. The runner must pass an explicit globals dict:
   `exec(compile(src, path, "exec"), {"__name__": "__main__"})`.
18. **Maya deletes an `objectSet` together with its last member.** A
   teardown that deletes the members and then deletes the set raises
   `No object matches name` on every *successful* run — which reads like
   the set was never created. Confirmed in isolation (two locators in a
   set, delete both, the set is gone). Re-check `objExists` before
   deleting the set.
19. **`orientConstraint(mo=True)` keeps its offset in the driven bone's
   OWN frame, not in world.** It holds `W_target = O · W_source` with `O`
   constant, and Maya's row-vector convention makes a left-multiplied `O`
   a local-frame rotation. So the quantity that transfers identically is
   `W_rest⁻¹ · W_now`, **not** `W_now · W_rest⁻¹` — the latter comes out
   conjugated by `O`. A verify script with the orders swapped passes on
   every bone whose rest offset is near zero (pelvis, spine, neck, head)
   and fails on every limb bone in proportion to its offset, which looks
   convincingly like a broken rig. It is not.

20. **A tool that only sources OverRig on SOME paths has a first-press
   bug, and a Qt slot hides it.** `build_fk` ran `apply_ForwHierarhy` /
   `apply_parentConstrAnim` without ever calling `ensure_loaded()`. In a
   fresh Maya — the OverRig shelf button unpressed, and there is no
   `userSetup.py` on this machine to press it — Build raised `Cannot find
   procedure` out of the Qt slot into the Script Editor, so the panel
   looked dead: "жму билд и ничего не происходит". `builder.build` DID
   source it, so pressing Switch once fixed Build for the rest of the
   session, which reads like a state bug and is not one. Two fixes, both
   needed: the guard on every MEL entry point, and `PickerWindow._run`,
   which puts any exception on the status bar instead of nowhere.
21. **The first bone of a chain is often not in the skeleton.** Everything
   that hangs a chain asked for `controller_name(chain[0])` —
   `index_metacarpal_l_FK_ctrl` on a rig that has no metacarpals. The
   lookup silently found nothing, so the four fingers of each hand were
   never hung on the IK hand and stood still in world space while the arm
   moved ("ФК контролы пальцев отвалились"). Only the thumbs, which start
   at `thumb_01`, followed. Resolve through `chain_root`, never `chain[0]`
   — and note the failure mode is SILENT: every call site guarded the
   lookup with `objExists` and skipped quietly.

29. **Turning a node moves its children twice: they face a new way AND they
   swing to a new place.** `orient_controllers` counter-rotated every child
   of a turned knot and left the local TRANSLATIONS alone — so each child
   ended up facing correctly at the wrong position, and since the bone is
   driven from a child locator, the character came apart by 21 cm. Local
   translation is applied after the local rotation, so the offset takes the
   same inverse turn: `R·T·C⁻¹` is `(R·C⁻¹)·T(t·C⁻¹)`. Every gate about
   ROTATION passed while this was broken — angles are blind to position —
   and only the bone-drift gate caught it. A drift check that samples world
   MATRICES, not orientations, is what makes that class of bug visible.
30. **"The bone has animCurves" is not "the animator has animation".** Every
   build leaves the bones carrying constant baked curves, so a verify script
   guarding its reset on `listConnections(bone, type="animCurve")` reads a
   perfectly idle skeleton as precious and skips the reset for ever after —
   then measures on whatever bent pose the previous run left. Ask whether a
   curve MOVES (`fkcontrols.is_constant`). Two more from the same run: a bake
   walks the timeline, so `cutKey` without returning to the rest frame first
   freezes every bone at the last baked pose *and the next Build bakes that as
   the build pose* (the tell is the ring-guess count jumping from 2 to 42);
   and keying a literal `0` on a bone to make test animation BENDS this
   skeleton, whose bind orientation lives in its rotate channels — key off the
   value the bone already holds.
31. **Comparing euler channel values across a bake reports 360° differences
   that are not differences.** A bone that read `-336.754` comes back reading
   `23.246`: the same rotation, written the other way round. Compare world
   matrices.

35. **OverRig's chain capture samples its aim rig on every SECOND frame.**
   The loop inside `apply_ForwHierarhy`'s capture increments its counter
   twice per iteration (a second `$i++` in the body, ~line 5404), so the
   `worldUpObject` locators that decide each knot's orientation are snapped
   every other frame with linear tangents and INTERPOLATED between; the
   dense bake then records that approximation. With the padded range
   starting at -1 the sampled frames are the even ones: a fast sword-attack
   clip measured up to **20.3 cm wrong on every odd frame and exactly zero
   on every even frame** ("смещение в определённых кадрах"). Slow or baked
   animation hides it, which is why every earlier live proof passed. Fixed
   by `overrig.full_rate_capture`: build_fk runs its whole capture loop in
   DOUBLED time (bone and rig curves scaled x2, playback x2), so every real
   frame lands on a sampled slot, then everything is scaled back and the
   half-frame keys are cut from captured transform channels — but never
   from the `attach` weight curves, whose fade lives half a frame outside
   the range and must stay. `root`/`pelvis` never suffered: single-bone
   chains go through `apply_parentConstrAnim`, which has no aim rig.
   Proof: `verify_capture_full_rate.py`.

36. **OverRig bakes across the time slider's HIGHLIGHT, and the graph
   editor's curve selection, before the playback range.** Its range reader
   (`timeControl -q -ra`, then `keyframe -q -n -sl`) sits in front of
   nineteen bakes. A highlight the animator dragged and forgot silently
   clips every capture and teardown bake to itself — a teardown under one
   would freeze everything outside it. Every entry point that runs MEL now
   refuses under a multi-frame highlight (`overrig.slider_selection`), and
   `full_rate_capture` clears the graph-editor key selection before
   capturing.

37. **A bridge merge onto a rigged skeleton lands on part of the bones and
   says nothing.** Keying a constrained channel splices a `pairBlend` in,
   and the importer skips other constrained channels entirely: measured in
   the live scene, 32 unrigged bones took the new clip while 60 rigged
   bones kept playing the old one — two animations on one character, which
   reads exactly like "the rig drifted". `animimport.import_clip` now
   refuses a merge when target joints carry constraints, naming Bake+Delete
   as the cure.

## Retargeting Manny onto other skeletons

`maya_retarget.py` (root level, standalone, no Qt) drives the referenced
`Mesh_protective_suit` skeleton from `SKM_Manny_Simple`. Design:
`docs/superpowers/specs/2026-08-15-manny-to-suit-retarget-design.md`, proof:
`docs/superpowers/plans/verify_retarget.py` (**21/21 green**).

- The suit is **UE4-schema**, Manny **UE5-schema**, and the difference is
  purely subtractive: all 67 suit joints have an exact name twin in Manny,
  which has 26 extra. So the map is derived from the scene, not hardcoded.
- **Matching the spine by name is wrong.** The suit hangs clavicles and neck
  on `spine_03`, Manny on `spine_05` — the same bone. `SPINE_MAP` pairs
  `spine_01→spine_02`, `spine_02→spine_04`, `spine_03→spine_05`, which drops
  the rest-pose error from 3.5/14.1/5.9° to 0.00/2.75/0.65°.
- **Hybrid offset policy** (the user's call): body on `maintainOffset=True`
  so the suit keeps its own silhouette — its clavicle genuinely runs 7 cm
  further back than Manny's, and that 24° is shape, not an axis artifact —
  and the 30 finger bones on `maintainOffset=False`, because there the 29°
  mean gap is *pose* (Manny is an FPS rig resting around a grip) and an
  offset would leave the suit's fingers idling. `finger_mode` flips it.
- **Never `parentConstraint` anything carrying the 145 cm side offset.** A
  parent constraint stores its offset in the source's space, so Manny
  turning on the spot swings the suit through an arc around him instead of
  turning it in place, and the world-constrained bones tear off. Pelvis and
  the two ik roots use `point` + `orient`. `set_side_offset(0)` overlays the
  two characters by rewriting the point constraints' `offsetX`, keeping each
  bone's own Y/Z rest delta.
- Accepted limits: feet do not land in Manny's footprints (calf ratio 0.952,
  foot 1.168 — inherent to a rotation-only transfer), metacarpal travel is
  dropped, and the suit has no root joint, so a UE export would need one.

## `maya_uebridge` — animations out of a running Unreal editor

A window listing every `AnimSequence` in the project the animator has open,
searchable, importing the selected one into the scene as its own keyed
skeleton. Design:
`docs/superpowers/specs/2026-08-16-ue-anim-bridge-design.md`, proof:
`docs/superpowers/plans/verify_uebridge.py` (**25/25 green**, run against a
live editor with 470 animations).

```python
import sys; sys.path.append(r"C:/!!!Work/MayaScripts")
import maya_uebridge; maya_uebridge.show_window()
```

**Reading `.uasset` directly is not buildable** — closed format, versioned
against the engine build, curves under UE's compression codecs. The engine
does the reading: Epic's **Python Remote Execution** (UDP multicast discovery
on `239.0.0.1:6766` plus a TCP command channel — the exact counterpart of the
`commandPort :7001` we drive Maya with) runs an Asset Registry query for the
list and an FBX export for the import.

| Module | Responsibility | May import |
|---|---|---|
| `uelink.py` | engine discovery, session, running Python in the editor | **stdlib only** |
| `uescripts.py` | UE-side script text | **stdlib only** |
| `records.py` | record model, search, namespace naming, row text | **stdlib only** |
| `animimport.py` | FBX import, timeline, fps policy | `maya.cmds` |
| `window.py` | the `cmds` window | `maya.cmds` |

The first three are testable with neither application running; a subprocess
test enforces it. `__init__.py` resolves `show_window` through `__getattr__`
for the same reason as `maya_overrig`.

**Turning it on:** `bRemoteExecution` is off by default. The checkbox
(Project Settings > Plugins > Python > Enable Remote Execution) applies
**immediately, no restart** — read the source: `PostEditChangeProperty` in
`PythonScriptPluginSettings.cpp` calls `SyncRemoteExecutionToSettings()`. But
the class is `UCLASS(config=Engine, defaultconfig)`, so the checkbox writes
`DefaultEngine.ini`, which on a Perforce project is shared and read-only; for
personal persistence put the setting in `Saved/Config/WindowsEditor/Engine.ini`
instead. `PythonScriptPlugin` and `EditorScriptingUtilities` are already
enabled in Atone.

**Which editor, when several are open:** the pong reply already carries
`project_name`, `project_root`, `engine_version`, `user` and `machine`
(`PythonScriptRemoteExecution.cpp:263-270`), so the window fills its project
dropdown from discovery alone, without connecting to anything. `pick_node`
takes an exact project match, and otherwise the **first by sorted label** —
never `nodes[0]`, which is whichever editor won the broadcast race and changes
run to run. The choice is remembered in the cache, and both the listing and
the export are pinned to it, or a second project would be asked for an asset
path it does not have.

**Results never travel through the socket.** The UE script writes JSON to a
path we chose and prints a marker; both processes are on one machine, and 470
assets would otherwise push a large payload through the command channel. The
reply file is deleted **before** the run — reading the previous answer would
report success for a script that died, which looks like a working tool
returning stale data.

**Import lands on the skeleton already in the scene** — the default and the
point of the tool. FBX **exclusive merge** (`FBXImportMode -v exmerge`) matches
bone names against what is already there, creates nothing, and writes the
animation onto it; measured on the Manny scene, 92 of 93 bones (only
`weapon_l` is absent from UE clips). The clip therefore must **not** go into a
namespace — a namespace is exactly what stops the names matching. The second
radio button keeps the old behaviour, a separate namespaced skeleton, and
`import_clip` with a namespace but no explicit `merge` follows the namespace
rather than overwriting the scene.

**The target skeleton is chosen, never assumed** (`choose_target_root`, pure):
the selection wins, else the only skeleton, else the one named `root`.
Namespaced roots are never candidates — they cannot receive a plain-name merge,
and in this tool they *are* the reference imports of earlier clips. Two
plausible skeletons with no hint is refused, because guessing animates the
wrong character in silence.

**The target's animation is cleared first**, and that is load-bearing rather
than tidiness — see trap 27. Bones the clip has no keys for end up unanimated
and are named in the status line.

Proof: `docs/superpowers/plans/verify_uebridge_merge.py` (**25/25 green**). It
imports one clip twice — merged, and as a reference skeleton — and compares
them frame by frame: 120 samples, worst 0.000000°, root motion 0.000000 cm.

Traps, each paid for:

22. **`cmds.file(i=True, type="FBX")` imports the skeleton and silently drops
    every animation curve.** It does not apply the `FBXImport*` settings, and
    it reports success either way. Measured on one file: `FBXImport -f` gives
    **1081 curves**, `cmds.file` gives **0** — with or without the namespace
    flag, with or without an options string. Use the plugin's own `FBXImport`.
    It has no namespace flag but honours the **current** namespace (verified:
    116/116 joints and 1081/1081 curves landed inside), and no way to report
    what it created, so new nodes are measured as a scene delta. Note the MEL
    string needs forward slashes — a backslash starts an escape.
23. **A modal dialog in the editor is indistinguishable from the plugin being
    off.** Discovery is answered on the game thread, so `Restore Packages`
    after a crash — or DDC maintenance, measured holding the thread 40 s —
    leaves UDP 6766 bound and answers nothing. The error message names both
    causes; the timeout is 15 s for the same reason.
24. **`AssetExportTask` with a null `Object` crashes the editor**, it does not
    raise: `Assertion failed: Object [UnrealExporter.cpp:168]`. `load_asset`
    returns None for a package that does not exist, so guard it before
    building the task. `automated=True`/`prompt=False` are equally
    load-bearing — without them UE raises a modal nobody can click.
25. **`AnimSequenceExporterFBX` needs a preview mesh** and warns instead of
    exporting without one (`EditorExporters.cpp`, `UAnimSequenceExporterFBX::ExportBinary`):
    it falls back to `FindCompatibleMesh()`, so a skeleton with no compatible
    mesh anywhere cannot be exported at all.
26. **Two engines registered in the registry means picking one is a coin
    flip.** `HKCU\Software\Epic Games\Unreal Engine\Builds` enumeration order
    is arbitrary — mayapy chose one root and the same code inside Maya chose
    the other. The engine root is taken from the **running editor process**
    (`EnumProcesses` + `QueryFullProcessImageNameW`; `OpenProcess` needs an
    explicit `HANDLE` restype or the handle truncates on 64-bit).

27. **An FBX merge rewrites animation curves IN PLACE.** Same node names and
    the same UUIDs — measured, 836 curves before and 836 after, zero fresh
    either way. So no scene diff can report what a merge touched: the status
    said "0 bones animated" over a fully animated skeleton, and the timeline
    was never set because the code found no new curves to read a range from.
    Deleting the target's animation before the merge is what makes the delta
    exact, the result idempotent, and stray bones stop carrying frames from
    whatever clip ran before.
28. **`listConnections` answers with short names.** Comparing them against the
    long paths a hierarchy walk produces matches nothing, silently, so every
    bone reads as untouched — the status claimed 92 animated and 93 untouched
    in the same sentence. Normalise with `cmds.ls(node, long=True)`. The
    live check now asserts animated + untouched equals the skeleton.

Measured facts about the listing: asset-registry tags are read **without
loading assets**, and the real tag names on 5.8 are `Number of Frames`,
`Number of Keys`, `SequenceLength`, `Target Frame Rate`, `Skeleton` — but only
about a third of assets carry them, so a missing frame count must never drop
the row. The listing is scoped to `/Game` on purpose; engine and plugin
content (MetaHuman, Engine tutorials) is excluded. Maya's imported key range
runs a frame or two past UE's reported frame count — the exporter's doing, not
worth "fixing" by trimming keys.

The scene's frame rate is **never** written: `FBXImportSetMayaFrameRate` is
forced off and a mismatch is reported instead. The animator is working in that
scene while the tool runs.

## `maya_scenesetup` — SceneSetup: the shot, not just the weapon

Renamed from `maya_weapons` on 2026-08-17 when the camera setup joined it.
Two things survived the rename deliberately: the scene marker attribute is
still **`mayaWeapon`** — it is written into the animator's files and a sword in
the open scene carries it, so renaming it would orphan that carrier and Add
would import a second sword — and the offset optionVar still **reads**
`mayaWeapons_offset_*` while writing `mayaSceneSetup_offset_*`, so a grip
dialled in before the rename survives. `show_window` deletes the legacy window
id as well, or the panel left open from before stays up wired to dead code.

**Camera Setup** puts a real Maya camera on `camera_bone`, bakes the bone's
animation onto it, and then drives the bone from the camera — the animator
animates a camera, the export bone follows. `maya_scenesetup/camera.py`, proof
`docs/superpowers/plans/verify_camera_setup.py` (**24/24 green**).

**The camera jumps into the bone's transform, and only the axes differ.** A
Maya camera looks down its own -Z and the UE camera bone does not. That turn
was measured in the user's scene from their own `camera1` against
`camera_bone` — (90, 0, 180) XYZ — and is kept as `AXIS_OFFSET`, with `FOCAL`
16.494 because that framing was a choice, not a default. It is a rotation and
nothing else: `rotation_only` strips any translation before use, so the camera
cannot end up standing away from the bone.

A first version preferred a reference camera in the scene and measured the full
offset from it, translation included. The user's call retired that: *"the
reference camera does not matter, only the rotation axes do"* — a camera lying
around must not be able to move the result, and the camera belongs ON the bone.
The reference-reading code is gone rather than disabled.

Maya's matrices are row-vector, so the camera's world matrix is
`OFFSET · bone_world` and the bone's is `OFFSET⁻¹ · camera_world`
(`placed_matrix` / `bone_matrix_for`). Getting that order backwards gives a
camera that looks plausible from one angle and is wrong everywhere else.

`camera_bone` is resolved inside the bound character first and scene-wide by
**leaf name** second — the camera bone often sits outside the character's
subtree, so the fallback is required, and a leaf comparison is what keeps
`fake_camera_bone` out where `ls("*camera_bone")` would take it. Two
candidates and no binding is refused.

The press: bake the bone onto the camera through a temporary
`parentConstraint(bone, camera, mo=True)` (the camera is already standing in
the right place, so the offset it captures is ours) and `cmds.bakeResults`;
then invert — cut the bone's own curves, snap it to `OFFSET⁻¹ · camera_world`,
and `parentConstraint(camera, bone, mo=True)`. **That order is load-bearing:**
constraining first and cutting after leaves a `pairBlend` nobody asked for, and
cutting without the snap lets `maintainOffset` capture the bone's REST pose
against the camera and bake a wrong offset in for ever. A second press bakes
the bone back off the old camera **before** deleting it — the animation lives
there now, and deleting first would take it away. `cmds.bakeResults`, not
OverRig: a camera is not a rig knot.

The live proof measures the follow in a **sandbox** — a throwaway joint with
real animation and its own camera — because after the bake the real camera's
channels are keyed and rewriting the animator's curves to prove a point is not
on the table. There: bone travels 40.000 for 40 on the camera, returns to
0.000000000000, animation unchanged 0.000000000. In the real scene the bone's
motion is unchanged to 0.000000000 across the timeline and the offset holds at
every frame.

A small window: a dropdown of weapon models, an **Add** button that imports the
chosen one and hangs it on `weapon_r`, and live rotate/translate fields for
dialling in the grip. Design:
`docs/superpowers/specs/2026-08-17-weapon-attach-design.md`, proof:
`docs/superpowers/plans/verify_weapons.py` (**17/17 green** in the Manny scene).

```python
import sys; sys.path.append(r"C:/!!!Work/MayaScripts")
import maya_scenesetup; maya_scenesetup.show_window()
```

| Module | Responsibility | May import |
|---|---|---|
| `catalog.py` | the weapon table and lookups, pure data | **stdlib only** |
| `skeleton.py` | which character, and where its weapon bone is | `maya.cmds`, `maya_overrig` |
| `attach.py` | import, replace, parent, read/write offsets | `maya.cmds` |
| `window.py` | the `cmds` window, offsets, optionVars | `maya.cmds` + the three above |

`catalog.py` stays stdlib-only (subprocess test) and `__init__.py` resolves
`show_window` through `__getattr__`, both for the same reasons as
`maya_overrig`. The window is plain `cmds` — a dropdown, a button and two float
rows need no Qt — and every callback goes through `_run`, which puts the
failure on the status line instead of the Script Editor (trap 20).

**The character comes from the picker.** `maya_overrig.picker_window` gained one
module-level `bound_root()`, which finds the open window and returns its bound
root; the binding lives in the live window and is persisted nowhere else. With
no picker the module binds as the picker does — the selection, else a lone
skeleton via `builder.character_roots()` (trap 1: a built rig reports a dozen
"skeletons") — and **refuses to guess** between two candidates. The bone is
then resolved inside that root's subtree through `naming.hierarchy_map` +
`detect_prefix`, never scene-wide: a bare `ls("weapon_r")` would arm whichever
character Maya listed first.

**The carrier** is a transform of ours between the bone and the imported model,
holding the offsets and a `mayaWeapon` string attribute with the catalog key.
Everything finds it by that marker, never by name. One weapon per bone: Add
deletes the marked carrier first, so the live fields always have exactly one
thing to move, and a child the animator parented by hand is never touched.

**`cmds.file` here, `FBXImport` in the UE bridge.** The opposite of trap 22 and
deliberate: trap 22 is about losing animation curves, a weapon model has none,
and `returnNewNodes` gives the exact node list `FBXImport` cannot report at
all. Say this out loud in the code, or the next reader "fixes" it into a bug.
The import mode is set explicitly on every import and the previous one put
back — see trap 33, which is what `cmds.file` DOES inherit.

**Connect Arms To Weapon** turns the rig inside out: the weapon leaves the
skeleton and drives the hands. Three steps, in this order —
`maya_scenesetup/connect.py`, proof
`docs/superpowers/plans/verify_connect_arms.py` (**17/17 green**):

1. **both arms brought to IK** — *brought to*, not switched. `switch_limbs`
   converts to the OPPOSITE type, so calling it on an arm that is already IK
   hands back an FK arm; the state is read from `builder.built_limbs()` and
   only the limbs that need it are switched (`connect.limbs_to_switch`);
2. **the weapon out to world** (`overrig.parent_out`), carrying the world
   motion it had, now baked onto its own channels;
3. **the IK end controls onto the weapon's GEOMETRY**
   (`fkcontrols.hang_ik_end_on` with `attach.model_root(carrier)`), each
   lifted to world first — re-parenting a knot in place is not a measured
   path, and lift-then-hang is what `switch_limbs` does with riders. The
   geometry, not the carrier: see trap 34.

Only the **end** groups ride the prop. Pole and base stay where they are, so
elbows keep answering to the body and the shoulder is not pinned to the sword.
Finger controls need no handling: they ride `<limb>_IK_anchor` under the end
control. Verified live: the hands do not move — worst world-matrix element
**0.000001662** across the timeline over the whole Connect, and 0.000000092
after the round trip.

**The link is found by walking up, never by searching.** The linked weapon is
the nearest ancestor of an IK hand control carrying the `mayaWeapon` marker
(`connect.marked_ancestor`), so two characters holding the same sword never
mix. Two guards fall out of it: **Add is refused while a link exists** (the IK
controls are the carrier's DAG children — replacing would take both arm rigs
down unbaked) and the **offset fields go quiet** once the carrier carries
curves, since `setAttr` on a connected channel raises.

**Disconnect** lifts the hands off and calls `hang_ik_on_root`, which puts them
back under the root controller *when there is one*. A rig built by Switch after
a full bake has no root controller and stands in world — so the status line
says "off the weapon" and never names a destination that may not exist. The
weapon's animation is re-baked into the bone rather than stripped: whatever was
animated out in the world survives, at the price of the offset fields staying
inert until someone deletes those keys.

Offsets are the carrier's local rotate/translate, written with **autoKey off**
(trap 14), read back from the scene on open, on Add and on switching the
dropdown, and remembered per weapon in an optionVar
(`mayaWeapons_offset_<key>`) so a grip dialled in once survives the session.
Scale is a catalog field, not a UI control: a model that arrives at the wrong
size is a fact about the model. Deleting a carrier leaves its shading nodes
behind, as any Maya delete does — chasing them is how a tool eventually
deletes something the animator wanted.

32. **Zeroing `translate` and `rotate` does NOT put a node on its parent.**
    `cmds.group` takes the pivot of what it groups — 42.4 up the sword — and
    `cmds.parent` compensates for that pivot in `rotatePivotTranslate`. The
    carrier then read translate 0, rotate 0, and hung **28.5 cm** off the hand,
    which looks exactly like a wrong bone or a bad import. The local matrix is
    the thing to check, not the two obvious channels: `attach.seat` zeroes
    `shear`, both pivots, both pivot translates and `rotateAxis` as well, and
    the carrier is now built empty and filled rather than grouped around the
    model. Live: worst world-matrix element 28.5130917 → 0.0000000.
33. **The FBX import MODE is one global setting for the whole session, and it
    reaches `cmds.file` even though the curve settings do not.** `maya_uebridge`
    leaves the plugin on `FBXImportMode -v exmerge`, where the importer matches
    names against the scene and **creates nothing**. So importing one animation
    from Unreal silently disarmed the weapon tool for the rest of the session:
    `cmds.file(..., returnNewNodes=True)` returned `[]` and Add reported
    "nothing came out of LongSword_02.fbx" — a message that points at the file
    while the file is fine. This is the other half of trap 22: `cmds.file`
    ignores the FBXImport* settings that carry animation, and inherits the one
    that decides whether nodes are created at all. Any tool importing FBX must
    set the mode it needs and put the previous one back; never inherit.
    `verify_weapons.py` forces `exmerge` before its first attach so the
    regression cannot come back quietly.
34. **Nesting is not attachment, and a check that never moves anything cannot
    tell the difference.** Connect hung the IK hand controls on the weapon
    CARRIER — our offset group — which made them SIBLINGS of the mesh inside
    it. Every gate passed: `_is_inside(control, carrier)` was true, the hands
    did not move (1.6e-6 across the timeline), the link resolved, the round
    trip was clean. Then the animator dragged the sword in the viewport and
    the hands stayed behind — sword 32.840, hands **0.000** — because what he
    grabs is the geometry, not our group. Anything riding a prop must hang on
    the **geometry** (`attach.model_root`, which asks for a mesh below rather
    than any shape, since an IK control is a locator and locators have shapes
    too). The verification now turns the sword 50 cm and measures that both
    hands travel with it; "it is nested and nothing drifted" was never the
    claim the feature makes.

## Conventions

- Branch `feature/overrig-picker`, remote `github.com/EugeneM23/MayaScripts`.
  `main` is untouched. Git identity is set **repo-locally** (`EugeneM`,
  `johnyanimation@gmail.com`) because the global `.gitconfig` does not exist.
- Work goes through brainstorm → spec → plan → TDD, with specs in
  `docs/superpowers/specs/` and plans in `docs/superpowers/plans/`. Read the specs
  for the reasoning behind any decision; they record why, not just what.
- `docs/superpowers/plans/verify_*.py` are live verification scripts meant to be
  sent through the bridge. They are the real proof — unit tests alone repeatedly
  passed while the scene was broken.
- **Verify by doing the real thing.** Every serious bug in this project survived a
  green test run and was caught by building for real and looking at the scene, or
  by the user noticing something on screen.
