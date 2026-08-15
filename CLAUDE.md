# MayaScripts — working notes

Read this first. It is written for a fresh session with no conversation history:
what exists, how to run and verify it, and the things that already went wrong so
they do not go wrong again.

## What is here

Two things, with different conventions:

- **Root-level `maya_*.py`** — standalone single-file tools, pure `maya.cmds`, no
  Qt, no package. Leave that style alone when touching them.
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

## Running tests

There is **no system Python** — `python` resolves to the Microsoft Store stub.
Use Maya's interpreter, and never `pip install` into the Maya tree.

```
& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v
```

Qt tests run headless with `$env:QT_QPA_PLATFORM = 'offscreen'` (PySide6 6.8.3 /
Qt 6.8.3 ship with Maya 2027). 122 tests at time of writing, all passing.

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
| `spineik.py` | The spline-IK spine rig, self-contained | `maya.cmds`, `maya.api.OpenMaya`, `overrig` |
| `builder.py` | Limb table, manifest, build / bake / teardown policy | `maya.cmds`, `naming`, `overrig` |
| `axes.py` | Rotation algebra for controller axes, pure | `maya.api.OpenMaya` only |

**Load-bearing rules — do not break these:**

- `bodymap.py` imports nothing outside the stdlib, `picker_view.py` never imports
  `maya.cmds`. A subprocess test in `tests/test_bodymap.py` enforces it.
- `__init__.py` resolves `show_picker` through `__getattr__` so importing the
  package does not drag Qt and Maya in. Making that import eager breaks the
  plain-Python tests.
- The fiddly logic is deliberately pushed into **pure functions taking the scene
  as data** (`resolve_limbs`, `order_by_nesting`, `foreign_knots_inside`,
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
and builds fresh in one undo step (`fkcontrols.rebuild`). Default: the hybrid
rig — IK arms and legs (`builder.DEFAULT_IK`), FK on root/spine/neck/fingers
(`HYBRID_FK_CHAINS`), finger chains hung on the IK hand controls via
`apply_Parent_in`. With the **FK Limbs** toggle pressed: full FK on all 17
chains (the old Build FK). No clavicle or ball controls in hybrid — same as
the post-Switch IK state; switching a limb to FK brings them back.

**Spine IK** is OUR spline rig (`spineik.py`), not an OverRig proc — the
rebike version was built first and rejected by the user; see
`2026-08-15-spline-ik-spine-design.md` (v4). Mechanism: a **degree-3 curve
with one CV per driven bone** (spine_01..04, carriers hip/mid/mid/top) —
the first cut used 3 CVs at degree 2, and a deep FK bend left that curve
far shorter than the chain: the solver ran out of curve, the bones bunched
up, and the then-position-pinned chest stretched the top segment ("the
spine scales"). `ikSplineSolver` runs **spine_01→spine_04** (the top
control sits one bone below the chest tip by the user's request; spine_05
rides above it keeping its own local keys) with advanced twist (Object
Rotation Up start/end, forward axis +X — the only axis the twist supports,
and the bones' axis here); spine_04 takes the top control's ORIENTATION
only — bone lengths are untouchable (verified: 0.000 segment deviation
under a 74 cm bend). The middle control rides a blend group
point+orient-constrained 50/50 between the hips and the top and stays
animatable on top of that. **The bottom node carries the pelvis through
`IKSpine_hipdrive`**: an identity group slipped above the pelvis controller
(relative parenting — its keys are untouched), parent-constrained to the
bottom node with the rest offset kept; the chain bot_zero ← root bone ←
root controller is rigid, so the offset is exact on every frame by
construction. `apply_Parent_in` was used here first and its attach
machinery LATCHED under interaction — one push-and-restore of the bottom
node shifted the pose permanently. On a bare skeleton (Switch on a plain
bone, no FK anywhere) the bottom node captures the pelvis animation and
drives the bone directly; the bone's keys stay under the pairBlend and
come straight back on teardown. Hidden
followers: `IKSpine_hip` rides the pelvis BONE (carries the curve base CV
and the mid blend); `IKSpine_chest` rides the spine_05 BONE (what neck and
clavicle chains re-hang on, so spine_05's local keys keep carrying them);
zero groups follow the ROOT bone (chest planted during hip sway, root
motion carries all). **The pelvis is its own single-knot FK chain**
(`CHAINS` has `pelvis` separate from `spine`) so its controller survives a
spine switch; the switch lifts it out of the bottom node before teardown
and re-hangs it on the root controller. The spine is the fifth entry in
`builder.LIMBS` (spine_01..05), NOT in `DEFAULT_IK` — spine IK is reached
through Switch. Controls resolve by role via `builder.ik_control(limb,
role)`: limbs match `IK_ROLES` substrings, the spine matches
`SPINE_IK_MARKS` leaf names EXACTLY (a substring match grabbed
`IKSpine_mid_blend` before the control). Build converts animation by
capture-bake onto the controls, then CUTS the driven bones' rotation keys —
they would fight the solver through pairBlends; bake-back restores them.
spine_04, spine_05 and the pelvis convert exactly; interior bones are a
curve+twist projection (measured 0.00–0.13 cm here).

**Bake+Delete bakes ONLY what the selection touches** onto clean bones —
controllers, bones, or picker buttons — and everything else stays rigged
(`fkcontrols.bake_targets` resolves, `bake_selection` orchestrates). One
resolution across BOTH manifest kinds with the **innermost owner winning**
(`innermost_owner`): FK controllers nest, and "descendant of any member"
once resolved a hand-controller click into root+pelvis+spine+arm at once —
Bake+Delete then wiped the whole FK rig. An IK limb takes its riding finger
chains down with it; the pelvis controller on an IK spine survives, re-hung
on the root; FK chains bake per chain, expanding to whatever rides inside
them (a chain cannot outlive its container). Nested rigs are baked before
their container.

**Switch auto-builds**: selecting any bone of a switchable chain (viewport
or picker) with no rig on that chain makes the first Switch press build its
IK; the next press converts to FK as usual (`switchable_bones` resolves
bones to chains, including clavicles and balls).

**The FK engine** (`fkcontrols.build_fk`, driven by Build) builds real FK
controllers through OverRig knots: up to 17 chains over the 64 bones
(`apply_ForwHierarhy` per chain, `apply_parentConstrAnim` for root), existing
animation baked onto the controllers, our sized rings attached as shapes on
the knots, machinery locators/joints hidden. `only=` restricts it to named
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

Two hard-won facts about this rig: bind orientation lives in the joints' ROTATE
channels, not jointOrient — non-zero local rotates are NOT a bent skeleton, and
`dagPose` restore is the way to check. And **Build FK bakes the pose the
skeleton stands in** — verify the pose before building; a proposed safety
(snapshot a dagPose before every build) is not yet implemented. The build pose
is also the reference the axis alignment zeroes against, so a lopsided build
pose costs the mirror symmetry as well as the animation.

**Switch FK/IK** converts whatever arms/legs/spine the selection touches to
the opposite rig type, per limb, animation re-baked at every step
(`fkcontrols.switch_limbs`, table `SWITCHABLE`). The FK manifest is per-chain
(`RigPicker_fk_<chain>`; the flat `RigPicker_fk` is legacy, absorbed by a full
bake). Fingers ride through an arm switch: `apply_Parent_out` lifts them to
world, the arm converts, `apply_Parent_in` hangs them on the new hand control
— they are DAG children of what gets deleted, so anything less loses them.
The spine carries the same bracket writ large, with one hard-won filter:
`spine_dependent_chains` (pure) lifts only chains whose OWN attach bone the
spine re-hangs (`SPINE_REHANG = {spine_05: end}` — neck and FK clavicles).
Containment alone is NOT enough: finger chains sit inside the spine
containers transitively through the FK arm, and lifting them detached the
fingers from the hand — "everything moves except the fingers", a real
user-reported bug. Deeper chains ride their parent chain's subtree. Thighs
hang on the pelvis controller, which survives the switch untouched. Baking
an IK spine that carries dependents through Bake+Delete refuses via the
existing intruder guard — Switch or a full bake is the route.
`apply_Parent_out`/`_in` semantics (both verified by experiment): selection is
child-then-parent for `_in`, the child alone for `_out`; both re-bake into the
new space with zero drift. Mixed FK/IK states are now normal; `Bake+Delete`
resolves selection to IK limbs first, then falls back to full-FK bake.

**Fingers on an IK arm hang on `<limb>_IK_anchor`** — a hidden locator
riding the hand BONE, parented under the IK end control (created on demand
by `fkcontrols._limb_anchor`, recorded in the limb manifest) — never on the
IK control itself: past full extension the control keeps travelling while
the bone stops, and fingers riding the control tore off the hand (measured:
hand-to-metacarpal 33 cm on a 40 cm overpull; with the anchor it stays at
the 4.2 cm rest). The limbs themselves do NOT stretch — OverRig's rebike
keeps bone lengths constant (measured identical under overpull) — so no
extra no-stretch work was needed.

Not built: neck switching and neck IK; per-chain FK bake from the UI (Switch
does it internally); coupling a fresh FK limb to an IK spine's controls (it
stays world-space, noted in the status line); docking; mirror-select; the
pose-snapshot safety before Build (proposed, not confirmed).

**Live verification: all green** (run in the Manny scene with animated
pelvis/spine): `verify_spine_ik.py`, `verify_spine_switch.py`,
`verify_hybrid_build.py` in `docs/superpowers/plans/`. Bridge-script
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
  groups). Neither fits a torso — that is why the spine IK is our own
  spline rig in `spineik.py`.
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
9. **The finger chains sit inside the spine containers transitively.**
   Containment alone made a spine switch lift them to world, detaching them
   from the hand ("everything moves except the fingers").
   `spine_dependent_chains` filters riders by their own attach bone.
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
