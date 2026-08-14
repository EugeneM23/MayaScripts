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
| `bodymap.py` | 64-button body map, pure data | **stdlib only** |
| `naming.py` | Skeleton root discovery, name resolution, prefix detection, UUID binding | `maya.cmds` |
| `picker_view.py` | Qt scene, button items, painting, input | **Qt only** |
| `picker_window.py` | Window, toolbar, Maya selection wiring, scriptJob | Qt + `maya.cmds` |
| `overrig.py` | Thin binding to the MEL toolset, no policy | `maya.cmds`, `maya.mel` |
| `builder.py` | Limb table, manifest, build / bake / teardown policy | `maya.cmds`, `naming`, `overrig` |

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

**Rig Picker** — an anatomical T-pose body map, 64 buttons, front view with the
character's left on the viewer's right. Click selects, `shift` adds, `ctrl`
toggles, drag marquee-selects, wheel zooms, middle-drag pans.

**Connect** binds the panel to one skeleton. Any joint of the character works —
it climbs to the root — as does the enclosing group. The root is remembered by
UUID so renaming or regrouping does not break the link. A single-skeleton scene
connects on open. Every lookup goes through the bound subtree, which is what
makes namespaces and per-joint prefixes a non-issue.

**Build** creates IK on both arms and both legs via
`apply_rebike_3_or_more_object_to_IK`, one undo step, rebuilding if pressed again.

**Bake+Delete** bakes back to FK whichever limbs the selection touches — an IK
control, any descendant of one, or the limb's source joints (so the picker's own
`Leg L` / `Main` buttons drive it). Nested rigs are baked before their container.

**Build FK** builds real FK controllers through OverRig knots: 17 chains over
the 64 bones (`apply_ForwHierarhy` per chain, `apply_parentConstrAnim` for
root), existing animation baked onto the controllers, our sized rings attached
as shapes on the knots, machinery locators/joints hidden. Chains are then
**coupled** with `apply_Parent_in` (selection: child first, parent last): each
chain-root controller hangs off its parent bone's controller, animation re-baked
into the new local space (zero drift verified) — never use a bare `parent` for
this, it preserves only the current frame. FK and IK are mutually exclusive
(guards in the window layer — a guard in `builder` would be an import cycle).
`Bake+Delete` with FK present bakes the whole FK back. Ring sizing comes from
the skinned mesh, not bone length; a correction table (`_BORROW`/`_SCALE`) holds
user-driven fixes. Knot→bone mapping is read from the BONE side (constraint →
driver → ancestor walk): a ForwHierarhy knot drives its bone through a child
locator, so looking for constraints on the knot itself finds nothing.

Two hard-won facts about this rig: bind orientation lives in the joints' ROTATE
channels, not jointOrient — non-zero local rotates are NOT a bent skeleton, and
`dagPose` restore is the way to check. And **Build FK bakes the pose the
skeleton stands in** — verify the pose before building; a proposed safety
(snapshot a dagPose before every build) is not yet implemented.

Not built: FK/IK coexistence and switching; IK on spine and neck; docking;
mirror-select; per-chain FK bake (FK bakes back as one unit).

## OverRig facts, learned by reading the MEL and by being bitten

- **Most procs are selection-driven.** `apply_Fast_Bake`, `apply_range_Fast_Bake`,
  `apply_Bake_to_layer`, `delete_constraint_attributes_on_objects` all act on the
  selection. Only `barn_fast_bake_source_obj_and_delete_knots()` is scene-global,
  and only because it selects the whole set first. **Never call that one** — it
  destroys the user's hand-made OverRig setups.
- **`return_constrained_object(1)`** maps a selected knot back to the object it
  drives. Useful; the `SelCon` button on the OverRig dock.
- **IK needs exactly three joints selected in order** root, middle, end.
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
