# MayaScripts — working notes

Read this first. It is written for a fresh session with no conversation history:
what exists, how to run and verify it, and the things that already went wrong so
they do not go wrong again.

## What is here

**The repo root is the workshop. `SkeldarAnim/` is the plugin.** That split
landed 2026-09-01 ("изолируем нашу полку как отдельный плагин чтобы ты тут не
путался куда какие скрипты") and it is the first thing to know: if it is in
`SkeldarAnim/`, a colleague receives it; if it is at the root, it is ours.

```
MayaScripts/                  the workshop
├── SkeldarAnim/              THE PLUGIN -- this, and only this, ships
│   ├── install.py  README_INSTALL.txt
│   ├── maya_overrig/  maya_uebridge/  maya_scenesetup/
│   ├── maya_overshoot.py  maya_hotkeys.py
│   └── icons/  assets/  overrig/
├── make_build.py             dev tool: builds the zip from SkeldarAnim/
├── maya_skelfit.py  maya_meltmorph.py  maya_retarget.py  ...
└── tests/  docs/  archive/  CLAUDE.md
```

`install.payload()` did not change: its names were always relative to
`source_root()`, the folder holding `install.py`. Three things did —
`tests/__init__.py` puts the plugin folder on `sys.path` (discovery gives the
repo root), `make_build.py` derives its OUTPUT dir from its own location so
the zip still lands beside the repository, and every dev entry point and
verify plan now says `.../MayaScripts/SkeldarAnim`. The standalone root tools
deliberately stayed put: they never shipped, and moving them would break the
paths written into both project skills and a dozen verify scripts for nothing.
`maya_skelfit.py` resolves `assets/` inside the plugin folder (Manny is shared
with Add Character), with the old spelling as a fallback.

Two conventions inside, unchanged:

- **Root-level `maya_*.py`** — standalone single-file tools, pure `maya.cmds`, no
  Qt, no package. Leave that style alone when touching them. Tools the packages
  superseded live in `archive/` (moved 2026-08-17; its README says why each).
- **`SkeldarAnim/maya_overrig/`** — a Python wrapper around the **OverRig** MEL
  toolset. This is the active work. It uses Qt and is a package, deliberately
  breaking the flat convention; see
  `docs/superpowers/specs/2026-08-14-overrig-picker-design.md`.

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
6. **A port that accepts connections but runs nothing means Maya's idle queue
   is blocked, not that the code is broken.** The commandPort is drained on
   idle, so a modal dialog waiting for a click leaves the socket accepting
   data that nobody reads: `create_connection` succeeds, the send succeeds,
   and the runner's marker file is never created. The measurement that
   settles it in one step is **CPU delta over a few seconds** — a busy Maya
   climbs, a blocked one is flat zero (measured: 0.00 s over 6 s while
   `Responding` still read True, PID alive, 1.4 GB resident). Two consequences.
   Neither Python nor MEL gets through, so trying the other syntax proves
   nothing. And every line sent meanwhile is still QUEUED: it fires
   unattended the moment the dialog is dismissed. Disarm a queued run by
   **deleting its runner file** — `exec(open(...).read())` then raises
   FileNotFoundError instead of baking the animator's scene while nobody is
   watching.
7. **A BOM on the runner file is indistinguishable from note 6, and
   PowerShell 5.1 puts one there by default.** `Set-Content -Encoding utf8`
   writes UTF-8 **with** a BOM, and `exec` of a string that starts with U+FEFF
   raises `SyntaxError` before the runner's first statement — so the `.ran`
   marker is never written, no output file appears, and Maya's CPU stays flat
   because nothing ran. Every symptom of a blocked idle queue, with a healthy
   Maya on the other end. Write the runner with
   `[System.IO.File]::WriteAllText($p, $body, (New-Object
   System.Text.UTF8Encoding($false)))`, or `-Encoding ascii` when it is ASCII,
   and have the runner read its payload as `open(path, encoding='utf-8')`.
   The tell that separates the two: send a two-line payload that only prints.
   If THAT works and the real one does not, it is not the queue. (Measured
   2026-08-18: a `print` payload written by PowerShell as ASCII ran; the same
   send with a BOM'd runner produced nothing at all.)
8. **Do not `raise SystemExit` in a runner — it is the prime suspect for
   killing the port for the rest of the session.** Note 5's idempotence guard
   was written as "`SystemExit` silently when the marker exists", and note 5
   also says every sent line runs TWICE. So the very first send of a session
   ends with a SystemExit escaping into Maya's command-port handler — and
   measured 2026-08-20, that is exactly where the bridge died: send #1 ran and
   wrote its output file, and from then on every send was ACCEPTED
   (`create_connection` fine, bytes written fine) and never executed. Maya
   stayed healthy the whole time — responding, 1.4 GB resident, the animator
   pressing Build in the panel and the tool working — while a two-word `print`
   payload produced nothing, which is the same signature as notes 6 and 7 with
   no dialog and no BOM anywhere. `SystemExit` is a BaseException, so a handler
   that catches `Exception` lets it through to the C++ layer that asked for the
   evaluation. **Guard with an `if`, never a raise**: wrap the runner body in
   `if not os.path.exists(marker):` and let the duplicate pass fall off the end
   doing nothing. Not yet isolated in a controlled experiment (that costs the
   animator a Maya restart), so it is a strong suspicion with a tight
   correlation rather than a measured fact — but the fix costs nothing.

   **Reopening the port does NOT bring it back — only restarting Maya does**,
   and the symptoms walk through three stages, each measured 2026-08-20. First
   the listener accepts every byte and runs nothing (notes 6 and 7's
   signature). Then `commandPort(":7001", query=True)` still answers True, so
   the usual one-liner is a no-op — it is guarded on exactly that — and the
   animator's "I reopened it" changes nothing at all. Force it with
   `commandPort(name=":7001", close=True)` first and the socket comes back
   **listening on 127.0.0.1:7001 and actively refusing connections from
   127.0.0.1** (RST, not a timeout), with a leftover CLOSE_WAIT beside it from
   an earlier send. A listening socket that refuses is a socket nobody is
   calling `accept` on: the port object is fine and the thing that services it
   is gone. Save the scene and restart.

9. **The session imports the INSTALLED SkeldarAnim copy, not the repo.**
   Measured 2026-08-21: `maya_overrig.__file__` answered
   `Documents/maya/scripts/SkeldarAnim/...` — the shelf buttons bootstrap
   that path, and it wins over a repo path APPENDED later. So a verify
   runner must `sys.path.insert(0, REPO)` and purge all three package trees
   whole from `sys.modules` (package roots included) before exec'ing the
   script, or it silently proves yesterday's code; and after changing repo
   code, refresh the installed copy (`install.install(quiet=True)` from the
   repo's `install.py`, purging the `install` module first — the installed
   folder carries its own) or the user's shelf keeps running the old build.
   Since 2026-09-01 the repo path to insert is
   `C:/!!!Work/MayaScripts/SkeldarAnim`, not the repo root — a verify plan
   still pointing at the root imports NOTHING of ours and dies on the first
   `from maya_overrig import ...`, which reads like a broken bridge.
   One more polling detail: a runner that redirects stdout into its output
   file CREATES the file immediately — poll for the script's final line,
   never for the file's existence.

## Running tests

There is **no system Python** — `python` resolves to the Microsoft Store stub.
Use Maya's interpreter, and never `pip install` into the Maya tree.

```
& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v
```

Qt tests run headless with `$env:QT_QPA_PLATFORM = 'offscreen'` (PySide6 6.8.3 /
Qt 6.8.3 ship with Maya 2027). 1392 tests at time of writing, all passing.

Discovery runs from the REPO ROOT (`-t .`), and `tests/__init__.py` is what
puts `SkeldarAnim/` on `sys.path` — so a test spawning a Maya-free subprocess
must point its `cwd`/`sys.path` at the PLUGIN folder, not the repo root. Four
purity tests do (`test_bodymap`, `test_pickerstate`, `test_scenesetup_catalog`,
`test_uebridge_records`).

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
| `active.py` | **Which character every operation acts on.** The UUID, `root_of(scene_map)` (pure), `character_roots`, `sole_character` | `maya.cmds`, `naming`, `overrig` |
| `manifest.py` | **Whose manifest is whose.** Kind/name/owner tagging, prefix discovery, the legacy claim. Pure policy + thin scene wrappers | `maya.cmds`, `overrig`, `active` |
| `builder.py` | Limb table, manifest, build / bake / teardown policy | `maya.cmds`, `naming`, `overrig`, `manifest`, `active` |
| `aimrig.py` | The aim manifest: record, resolve a selection, bake and delete. Knows nothing about weapons | `maya.cmds`, `builder`, `overrig` |
| `axes.py` | Rotation algebra for controller axes, pure | `maya.api.OpenMaya` only |
| `fkchains.py` | Chain tables, what a build may create (`BUILDABLE`/`build_targets`), pure chain resolution (chain_root, innermost_owner, ...) | stdlib + `builder` (for `_is_inside`/`LIMBS`) |
| `fkrings.py` | Ring sizing from the skin, knot dressing | `maya.cmds`, OpenMaya, `bodymap`, `naming`, `fkchains` |
| `fkalign.py` | Controller axis algebra (align/orient) | `maya.cmds`, OpenMaya, `axes`, `fkchains` |
| `twist.py` | The twist joints: the segment table, the measured axis and fractions, the seven-node network, its manifest and its bake | `maya.cmds`, OpenMaya, `naming`, `overrig` |
| `fkcontrols.py` | FK build/bake/switch orchestration; re-exports the three above | `maya.cmds`, `maya.mel`, `bodymap`, `builder`, `overrig`, `twist` + the three above |

**Load-bearing rules — do not break these:**

- `bodymap.py` imports nothing outside the stdlib, `picker_view.py` never imports
  `maya.cmds`. A subprocess test in `tests/test_bodymap.py` enforces it.
- `__init__.py` resolves `show_picker` through `__getattr__` so importing the
  package does not drag Qt and Maya in. Making that import eager breaks the
  plain-Python tests.
- The fiddly logic is deliberately pushed into **pure functions taking the scene
  as data** (`order_by_nesting`, `foreign_knots_inside`,
  `detect_prefix`, `unrecorded_rig_roots`, `manifest.pick`,
  `active.root_of`). Test those; keep the Maya-touching wrappers thin.
- **Nothing resolves a manifest or a controller BY NAME any more** (2026-09-01).
  `builder.limb_set_name` / `fkchains.chain_set` / `twist.twist_set_name` name a
  FRESH set; `manifest.find` finds an existing one; `fkcontrols.fk_controls`
  finds controllers. See the section below before adding a lookup.

## The active character

**Every rig and skeleton operation acts on the character the picker is
CONNECTED to** (2026-09-01, the user's ask: press Connect on a bone hierarchy
and that hierarchy is what we work with; a scene may hold many characters).
Spec: `docs/superpowers/specs/2026-09-01-active-character-design.md`.
**The animator confirmed all four parts by hand in the live scene the same
day** — the plugin folder, the per-character rig, repeated Add Character, and
import/export following the selection then the connect ("всё работает"). Proof:
`verify_two_characters.py` — **green live 2026-09-01, 0 of 51 gates failed**,
including the two that matter most: turning character A's spine control moved
B by **0.000000000**, and pulling A's IK hand moved B by **0.000000000**.

**What was broken.** Every manifest and every controller was found by NAME.
Maya uniquifies the second character's `RigPicker_build_arm_l` to `...arm_l1`
and its `upperarm_l_FK_ctrl` to `..._FK_ctrl1` (both confirmed live), so the
tool read character two as unrigged — building FK over its live IK — coupled
its chains onto character one's controllers, aligned somebody else's rotate
axes, and baked limbs the animator never selected. Silently, every time.

**Identity by ATTRIBUTE, discovery by PREFIX** (`manifest.py`). Every
RigPicker set carries `rigPickerRoot` (the character root's UUID),
`rigPickerKind` (`ik`/`fk`/`twist`) and `rigPickerName`. The readable name is
kept for the outliner and never searched for again. This is exactly what the
aim manifest has done since 2026-08-17, generalised. **Legacy files keep
working**: a set with no tag was built in a single-character scene, so it
answers for the sole character, and `claim_untagged` tags it on the first bind
or build — with several characters already present it is claimed only when one
of its members lies inside the asking character's own subtree (OverRig parks a
constraint under every source joint, so a rig of ours always has one there).
`pick` is pure and tagged beats untagged, for a scene part-way through.

**The controller INDEX** — `{bone: controller UUID}` — replaced trusting
`<bone>_FK_ctrl` to be unique. Two sources, and both are needed:

- *After* a build, `fkcontrols.fk_controls(scene_map)` reads it out of this
  character's own manifests. Matching inside a manifest that already belongs
  to one character is unambiguous — that is the whole point of tagging. The
  leaf is digit-stripped (`control_leaf`, pure) and compared EXACTLY against
  `bone + "_FK_ctrl"`, which is what keeps OverRig's dead
  `..._FK_ctrl_aimConstraint1` and our `..._FK_ring_tmpShape` out. The suffix
  ends in a letter, so the strip can never eat part of a bone name
  (`spine_01_FK_ctrl` survives whole).
- *During* a build it comes from the build itself: `_dress_knots` now RETURNS
  `{bone: knot path}` instead of a count, and `build_fk` threads the index
  through coupling, align and orient. Inside a build is the one moment two
  characters genuinely own a knot of the same name.

**UUIDs, not paths, in the index.** `apply_Parent_in` re-parents a chain's
root knot, changing every knot below it — a path index assembled during a
build is stale by the second chain, which is exactly when the third needs to
hang off it (trap 16 again). `control_for(bone, index)` re-resolves.

**Where the character comes from — no signature changed.** A binding map
carries its own root: it is built by `naming.hierarchy_map(root)`, so the
root is the shallowest joint path in it (`active.root_of`, pure, tie-broken
by path). Every MEL entry point calls `manifest.activate(scene_map)` — which
is why twelve live verify scripts and eight test modules needed no edits — and
the picker's `_bind` sets it directly, so Connect is what the animator
experiences. `picker_window._resolution` RE-ASSERTS the window's binding on
every selection sync: a verify script or a second panel can have adopted a
different character since.

**Guards run BEFORE activating.** Activating claims manifests, which WRITES,
and a refusal must leave the scene exactly as it found it. `bake_targets` uses
`active.adopt` (context only) rather than `activate`, because it is a
read-only resolution.

**Deliberately scene-wide:** `builder.recorded_members()`, the shield that
stops `_reclaim` dooming anything we bookkept — scoping it would let a bake on
one character reclaim another's rig. `OverRig_knots` likewise (it is
OverRig's, shared by every character, and `character_roots` excludes joints
under it — trap 1). `aimrig` was already identity-by-attribute and an aim
belongs to a weapon rather than a character; untouched.

One measured detail from the live run: with two characters, `scale_nodes` for
`full_rate_capture` is now **this character's** bones and rigs only. Scaling
another character's would drag its animation through doubled time and scale it
back against a timeline it never rode.

Entry point:

```python
import sys; sys.path.append(r"C:/!!!Work/MayaScripts/SkeldarAnim")
import maya_overrig; maya_overrig.show_picker()
```

## What the tool does today

**Rig Picker** — an anatomical T-pose body map, 64 FK buttons plus 11 IK
circles (end + pole per limb, top/mid/bot for the spine), front view with the
character's left on the viewer's right. Click selects, `shift` adds, `ctrl`
toggles, drag marquee-selects, wheel zooms, middle-drag pans.

**The picker selects controllers, never bones — except the fingers.** A button
is live exactly when its controller exists right now — FK buttons resolve
`<joint>_FK_ctrl` by name, IK circles resolve through
`builder.ik_control(limb, role)` and the limb manifests. Everything else is
dimmed and unclickable: before a build the whole map is inert, a limb switched
to IK dims its FK buttons and lights its circles. Availability is recomputed on
every selection sync (`picker_window.sync_from_scene` → `_resolution` →
`pickerstate.resolve`), so builds, bakes, switches and manual deletes all show
up immediately.

The one exception, since 2026-08-18: the **38 finger buttons fall back to the
finger BONE**, because finger FK controllers are no longer built and the
animator poses those bones (see below). `pickerstate.resolve` takes an optional
`bone_nodes` fallback and the controller always wins, so a file rigged before
that change still selects its controllers; the *policy* of which buttons may
fall back lives in `picker_window`, which offers `fkchains.FINGER_JOINTS`
resolved through the bound subtree, and the pure module knows nothing about
fingers. Nothing downstream needed changing, and each for a reason: a finger
bone in the selection lights its button (matched on the full DAG path), is
never offered by `switchable_bones`, and resolves in `bake_targets` to a chain
that is neither a built limb nor a recorded chain — so Bake+Delete does
nothing, which is the safe direction of failure.

**Connect** binds the panel to one skeleton, **and that is what chooses the
ACTIVE character** (2026-09-01): every build, switch, bake and teardown lands
on the connected hierarchy, and a scene may hold as many characters as the
animator likes. Any joint of the character works — it climbs to the root — as
does the enclosing group. The root is remembered by UUID so renaming or
regrouping does not break the link. A single-skeleton scene connects on open.
Every lookup goes through the bound subtree, which is what makes namespaces and
per-joint prefixes a non-issue; see **The active character** below for what
makes two identically-named Mannys stay apart.

**Build** (the only build button) tears down whatever exists **on the
connected character** — FK baked back first, then IK, because a file rigged
before 2026-08-18 has finger controls hanging inside IK hand controls — and
builds fresh in one undo step (`fkcontrols.rebuild`). Another character's rig
in the same scene is not touched; verified live (0.000000000 both ways).
Every entry point
that runs MEL — `build_fk`, `rebuild`, `switch_limbs`, `bake_fk`,
`bake_selection`, `builder.build`, `builder.bake_limbs` — calls
`overrig.ensure_loaded()` first and returns `overrig.NOT_LOADED_MESSAGE`
when the toolset cannot be found at all (trap 20). Default: the hybrid
rig — IK arms and legs (`builder.DEFAULT_IK`), FK on
root/pelvis/spine/neck/clavicles (`HYBRID_FK_CHAINS`, six chains, twelve
controllers). **The window always builds hybrid** (2026-08-21 — the FK Limbs
toggle is gone); the full-FK build stays reachable as
`rebuild(fk_limbs=True)`, which `verify_hybrid_build.py` still exercises,
and for the animator as Build → select all → FK Limbs. No ball controls in
hybrid — same as the post-IK state; bringing a leg to FK brings them back.

**The toolbar is directional since 2026-08-21** («от кнопочки switch давай
избавимся»): the Switch button is gone, and **FK Limbs / IK Limbs** bring
the selected limbs — controller, bone or picker button, a clavicle still
naming its arm — TO the asked type. A limb already there is left alone and
named ("Already FK: arm_l"), the opposite one converts through
`switch_limbs`, and a bare chain builds directly in the asked type (toward
IK via `switch_limbs`' own auto-build, toward FK via `build_fk(only=...)`).
The policy is pure (`fkchains.limbs_to_convert`), the orchestrator is
`fkcontrols.convert_limbs`, and **`switch_limbs` itself stays** — it is the
engine under the buttons, Connect's auto-IK, and three verify scripts'
harness. The group-selection row is one **All** button (the user's call:
the other nine duplicated the body map); `bodymap.group_members` still
knows every group.

**The clavicles are their own always-FK chains** (2026-08-21, the
pelvis/spine split applied to the shoulders): `clavicle_l/r` left the arm
chains and stand ahead of them in `CHAINS`, so the hybrid Build creates
their controllers and an arm switch no longer deletes them — the control
survives IK↔FK in both directions, and in full FK the arm chain couples
INSIDE it (rotating the clavicle still carries the FK arm). **We drive ONLY
the bone** — nothing was re-hung on the control (the user's explicit call,
offered the alternative and declined) — but the measured behaviour is
better than that promise: **OverRig's IK follows the chain's parent bone on
its own**, so turning the clavicle control carries the arm base (upperarm
moved 1.223) while the IK hand stays planted (9.6e-8) and the elbow
re-solves — classic clavicle-over-IK, for free. The earlier root-bone
measurement ("moving the root bone moves nothing") had hidden this: the
root bone never moves the clavicle BONE's baked channels, so nothing
propagated. Do not hang `_IK_strech_gr` on the clavicle control — it is
not needed and was declined. Single-bone chain ⇒ `apply_parentConstrAnim`
⇒ a plain
transform knot whose frame already matches the bone; align/orient skip it
by the no-jointOrient filter, like root and pelvis. Clicking a clavicle
BONE + Switch still converts its arm (`fkchains.CLAVICLE_OF`); the clavicle
CONTROL is not switchable — it is always FK. Old files degrade cleanly:
their clavicle knots are recorded in the old arm manifests, and teardown
reads manifests, not the table.

**The clavicle ring is drawn at the bone's far END, not its origin**
(`fkrings._AT_BONE_END`, same day: «контролеры не видно из-за меша»). The
origin sits 1.4 cm off the midline INSIDE the chest, so a ring centred
there was invisible; centred on the first joint child (the shoulder) it
arcs over the deltoid — the pivot does not move, only the drawing. The end
is computed through the knot's inverse matrix, never assumed to be
`(length, 0, 0)`. Size correction rides the existing `_SCALE` table at
**1.7** — 1.4 read right on paper and still dipped into the arm on the
real mesh; the number was chosen by looking at viewport captures taken
through the bridge, and that is the standard this table's entries are held
to now. A bone in `_AT_BONE_END` with no joint child keeps the origin.

**No FK controllers on the fingers** (2026-08-18, the user's call: "буду
анимировать на костях"). The ten finger chains stay in `CHAINS` and are left
off a new `BUILDABLE`, which is what every build filters through
(`fkchains.build_targets`, applied to an explicit `only=` as well, so no caller
can ask a finger chain back). Keeping them in the table is load-bearing twice
over: teardown walks `CHAINS`, so a chain missing from it would be a rig
nothing can find and nothing can bake (traps 3, 5, 16) — a file rigged before
the change still comes apart, and a Build clears yesterday's finger rig on the
way past — and "на время" means the hanging machinery below has to stay
reachable. Reverting is three lines in `fkchains.py` plus the tests that pin
them. Spec: `docs/superpowers/specs/2026-08-18-fingers-on-bones-design.md`.

**The spine is FK-only for now.** A full spline-IK spine (own module
`spineik.py`, three controls, hipdrive pelvis carry, per-end advanced
twist) was built, live-verified and then REMOVED at the user's call
(2026-08-15, "в будущем вернемся"). The complete implementation, its
verify scripts and the design spec history live at commit `0e0794f`; the
spec `2026-08-15-spline-ik-spine-design.md` documents every decision and
every trap it fought. The `CHAINS` split of `pelvis` from `spine` is KEPT —
it is harmless in FK and is a prerequisite for the IK's return. Selecting
a spine bone and pressing FK Limbs or IK Limbs says "select an arm or leg".

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

**A bare chain builds on the first press**: selecting any bone of a
switchable chain (viewport or picker) with no rig on it makes IK Limbs
build its IK and FK Limbs build its FK (`switchable_bones` resolves bones
to chains, including clavicles and balls; inside `switch_limbs` the
bare-to-IK path is the old Switch auto-build, unchanged).

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

**The switch engine** converts whatever arms/legs the selection touches to
the opposite rig type, per limb, animation re-baked at every step
(`fkcontrols.switch_limbs`, table `SWITCHABLE`; since 2026-08-21 the UI
reaches it through the directional `convert_limbs` — there is no flip-style
button any more). The FK manifest is per-chain
(`RigPicker_fk_<chain>`; the flat `RigPicker_fk` is legacy, absorbed by a full
bake). Rider chains ride through an arm switch: `apply_Parent_out` lifts them
to world, the arm converts, `apply_Parent_in` hangs them on the new hand
control — they are DAG children of what gets deleted, so anything less loses
them. **No chain rides today** (fingers are the only ones that ever did, and
they are off the build list), so this path runs only on a file rigged before
2026-08-18; `_rehang_riders` returns early on an empty list rather than falling
through, because asking for the anchor CREATES it.
A chain with no rig at all auto-builds its IK when asked to IK (the old
first-Switch-press behaviour, now reached through IK Limbs).
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

**That machinery is DORMANT, not gone.** With no finger chains built there is
nothing to hang, so **no anchor is created** — `rebuild` and `_rehang_riders`
both count the riders *before* asking for it, because `_limb_anchor` builds the
locator and its parent constraint on demand and every Build was otherwise
leaving two of each in the rig for nothing. The finger bones need none of it:
they are plain DAG children of the hand bone, which is why the 40 cm overpull
above cannot pull them off any more.

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

**The twist joints are driven** (2026-08-20). A UE skeleton carries
`upperarm_twist_*`, `lowerarm_twist_*`, `thigh_twist_*`, `calf_twist_*`, whose
job is to spread one segment's roll along its length so the skin shears
gradually; in Unreal the engine drives them at runtime and in a Maya file they
hang rigidly off their parent doing nothing. `twist.py` drives them with seven
stock nodes per joint, computing the **exact** swing–twist of a driver bone
about the measured bone axis: `Δ = M0⁻¹ · M`, then `θ = 2·atan2(v·a, w)` from
the delta's quaternion. **`quatNormalize` in that chain is load-bearing** —
`quatToEuler` assumes a unit quaternion and `(v·a, 0, 0, w)` is not one, so
without it the angle comes out `atan2(2wx, 1−2x²)`, which equals the twist only
when the swing is zero. No constraint is created anywhere.

Two kinds, and the sign of the fraction is the whole difference: a **follow**
joint (`lowerarm_twist_*`, `calf_twist_*`) takes `+t` of the far bone's roll —
the roll enters at the wrist, so skin near the elbow stays and skin at the
wrist follows — and a **counter** joint (`upperarm_twist_*`, `thigh_twist_*`)
takes `−(1−t)` of its own bone's roll against ITS parent, because it is a DAG
child of the rolling bone and inherits all of that roll already. `t` is
measured, not tabulated: the joint's position along its parent bone, clamped,
with an even split by index as the fallback when the positions carry no
information at all (every joint on the parent's origin, or two in one spot).
Which joints exist is discovered by the `_twist_<nn>` name infix, so one, two
or three per segment is one code path; only the eight **segments** are a table.

Two refusals rather than a guess. The bone axis is measured against the joint's
own axes, and a joint whose axis is more than 10° off the bone is **skipped
with a named reason**; so is one whose bone axis is not the **innermost channel
of its rotate order**, because adding to a channel that is not innermost turns
the joint about its parent — it would bend where it should roll. An animCurve
on a twist channel is superseded and deleted; any other driver on it (a
constraint, somebody's own connection) is refused by name, never taken over.

**Switch FK/IK needs no handling at all, and that is the point of reading
bones.** A hand is a hand whether an FK controller or an IK rig drives it, so
the whole class of rider bugs (traps 9, 16, 21) does not arise. Build builds
it last, outside the FK/IK branch; `bake_selection` takes down the twist rig of
exactly the limbs it bakes (`twist_limbs_for` — a limb name means the same in
both manifests, so a limb baked as IK and one baked as FK chains resolve
alike), and a spine bake leaves every twist alone. The manifest is
`RigPicker_twist_<limb>` holding the nodes we created — **not** a UUID scene
diff: that diff exists because OverRig conjures up nodes we cannot see, and
here every node is ours. It also carries the driven channels as
`rigPickerTwistPlugs` (`<uuid>.<attr>`), because **neither walk of the rig
finds them**: `objectType` on our addDoubleLinear answers `addDL` (trap 41)
and Maya splices a `unitConversion` in front of the angle channel (trap 42).
Those conversions are members too, or one outlives the bake still driving the
channel.

**The bake samples, then deletes, then keys.** `cmds.bakeResults` has no say
over a channel driven by our own DG nodes, so `twist.bake` reads every frame
with `getAttr(time=...)` first, deletes the network to free the channels, and
writes the keys last — writing earlier is impossible (the channel still has an
input) and deleting earlier loses the values. A still channel collapses to a
plain value instead of a key per frame. It reads the playback range, never the
time slider's highlight, so it needs no highlight guard of its own.

**The UE bridge keeps working**: no constraint means the trap-37 guard in
`animimport.import_clip` does not trip. The twist channels *are* connected, so
an FBX merge skips them silently — the right outcome, since the network
recomputes the twist from the imported hand animation.

The zero of every fraction is the pose the rig was **built** in, so build in
the bind pose; a driver carrying animation that actually moves is named in the
status line. Closing that needs the bind local rotations from the `bindPose`
node, which is the *same* gap `align_controllers` has — to be closed once for
both, deliberately not here. Spec:
`docs/superpowers/specs/2026-08-20-twist-bones-design.md`.

Not built: FK controllers on the fingers (dropped 2026-08-18, "на время");
spine IK (removed, see above) and neck IK; per-chain FK bake from the UI
(Switch does it internally); docking; mirror-select; the pose-snapshot
safety before Build (proposed, not confirmed); a character dropdown in the
picker (Connect already is one, and the user described Connect as the
mechanism).

**Live verification** (run in the Manny scene): `verify_arm_switch.py`,
`verify_capture_edges.py`, `verify_control_axes.py`, `verify_hybrid_build.py`,
`verify_ik_under_root.py` in `docs/superpowers/plans/`, plus
`verify_fingers_on_bones.py` for the 2026-08-18 change.
`verify_two_characters.py` (2026-09-01) is **green: 0 of 51 gates failed**
and is the proof for the active-character scoping — it builds two throwaway
UE5-schema skeletons of its own in whatever scene is open, so it needs
neither the Manny scene nor an empty one, and it runs in **three phases**
(`PHASES` narrows it for a staged run): manifest scoping with no OverRig at
all, a real hybrid build on both characters, and the import/export target.
Phase 2 skips itself when the scene already holds RigPicker manifests that
are not its own — it builds and tears down for real, and a verify run has no
business doing that beside the animator's rig. Measured: A's spine control
turning A by 7.87 and B by **0.000000000**, A's IK hand pulling A by 14.49
and B by **0.000000000**, B's controller resolving to nothing against A's
binding, and a Bake+Delete on B leaving A's rig standing and still driving. **All six were
rewritten that day** — five of them asserted "the finger hangs on the hand",
which is no longer true — so their last green run predated the rewrite.
**`verify_hybrid_build.py` has since run green live (2026-08-21, 0
failures)** with its new clavicle gates — including two full builds, the
FK-limbs flip and an arm switch both ways — so it doubles as proof the
rewrite itself is sound; the other four still await a live run. Its reset
now **bakes the twist rig and restores the BIND POSE** (and restores it
again at the end): the original version keyed literal zeros on
`upperarm_l`/`spine_03` — trap 30 verbatim, this skeleton's bind lives in
its rotate channels — and every run bent the skeleton a little further,
until the arm stood straight up and pose-dependent gates (world-X ring
position, a +25° shrug against a straight arm at full extension) failed on
correct code. Gates that measure placement now measure against BONES, and
the shrug is +10° with the hand judged relative to the shoulder's travel.
dagPose refuses to restore while the twist networks drive their channels —
hence the twist bake first.
`verify_twist_bones.py`
(2026-08-20) is **green: 0 of 30 gates failed** in the Manny scene, and it
found three real bugs on the way (traps 41–43). It runs in
**two phases**: the exact
numbers are measured on a SANDBOX chain it builds and deletes (poking a
sandbox is free, and it needs neither OverRig nor a rig on the character, so
the mathematics is proved on its own), and the real skeleton then gets the
integration gates — the network's output against the same twist recomputed in
plain Python, idempotence, the bake, and Switch FK/IK leaving it alone.
Measured 2026-08-20 on Manny: 22.500000 of a 90° roll on a joint at t=0.25,
**0.000000000 from a 60° bend** (the gate that separates this from a
two-target constraint), a counter joint netting 22.500001 of its parent's 90°,
127.500000 at 170° with no flip, the DG against plain Python worst
**0.000001713°** in a mixed pose, driver bones unmoved **0.000000000** over
the timeline, and an arm switched to FK and back leaving all 144 twist nodes
in place and every value within 0.000009°.
`verify_control_axes.py` builds the rig itself in two halves — once with
`orient_controllers` suppressed, then for real — so the turn is measured on
its own rather than inside a whole build; it now builds **full FK**, because
the hybrid rig's four FK chains are all on the midline and its mirror gates
need left/right pairs. `verify_missing_bones.py` runs in an EMPTY
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
- **The aim button does not build the aim.** `make_aim_from_selected(1)`
  creates the two locators (`<name>_top`, `<name>_side`) snapped onto the
  object and arms a run-once `scriptJob -ro 1 -cf "SomethingSelected"`; the
  rig — parentConstraint the locators to the source, bake, drop the
  constraints, then `aimConstraint -mo -aimVector 1 0 0 -upVector 0 1 0
  -worldUpObject <side>` — is built later, **when the animator deselects**.
  That gap is where the locators get dragged into place by hand. Anything
  automating it has to call the deferred half itself
  (`overrig.build_aim`), or the build lands outside the caller's undo chunk
  and node diff and the job stays armed to fire again. The build proc is
  driven by MEL globals the create proc sets, not by the selection, so
  calling it directly is well defined. Its bake reads
  `playbackOptions -ast/-aet`, never `timeControl -q -ra`.
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
   as the cure. Since 2026-08-21 our own weapon-driven bones are the one
   exception: they are unlinked before the merge and re-linked after it
   (`foreign_constrained` / `bonedrive`), so a sword in the hand does not
   block every import — the refusal fires on everybody else's constraints.

38. **FBX export writes the take across the ANIMATION RANGE, so a tool that
   narrows the range narrows the clip.** `root_offset_batch_tool` set the
   playback range to its own offset window before exporting; measured, a
   scene holding keys from -20 to 30 came out of the exporter as 0..30 with
   the frames before the window simply gone. That reads as "the exporter is
   lossy" and is really the range. An export must set the range to the UNION
   of what it wants and what the clip already has.
39. **`cmds.file(i=True, type="FBX")` and `FBXImport` disagree about the
   frame rate, not only about curves.** Trap 22 says `cmds.file` drops
   animation; measured again on this project's UE clips it did NOT (583
   curves either way) — but it resamples a 30 fps clip into a 24 fps scene
   onto fractional frames (`-25..18` becomes `-20..14.4`), because it never
   sees `FBXImportSetMayaFrameRate`. So the rule stands for a second reason:
   use `FBXImport` when timing matters, and decide the frame rate explicitly
   rather than inheriting whatever the scene had.
40. **Deleting "the animation" on a UE root deletes the game's data.** The
   root of an exported UE clip carries the animation curves as custom
   attributes — `Pose_0..9`, `MoveData_Speed`, `DisableLegIK`,
   `DisableHandIKRetargeting`, `RootMotionAdditiveInput`, plus a pose driver
   per joint angle. Measured: 135 curves on `ShortSword_Attack_Right_3P`,
   against 9 that are transform channels. Anything that clears a root with
   `listConnections(root, type="animCurve")` throws those away, and the loss
   only shows up in Unreal.
41. **`cmds.animLayer` has no `rotationAccumulationMode` flag in Maya 2027.**
   It is in older docs and in plenty of forum answers, and it raises
   `TypeError: Invalid flag`. So there is nothing to configure about how an
   additive layer accumulates euler offsets — measure the combined channel
   instead of setting a mode.
42. **`cmds.selectKey(clear=True)` raises when nothing is selected** —
   `TypeError: Error retrieving default arguments`, because the command wants
   objects and falls back to the selection. It works fine earlier in the same
   script and then throws in the teardown, after the sandbox nodes have been
   deleted, taking the rest of the restore with it: autoKey stayed off, the
   frame and the selection were never put back. Every teardown step in a bridge
   script should be individually guarded, and a `finally` block is exactly
   where that matters.
41. **`cmds.objectType` does not answer the type name you created the node
   with.** `createNode("addDoubleLinear")` reports **`addDL`**, and
   multDoubleLinear reports **`multDL`**. `twist.driven_plugs` filtered its
   manifest members on `== "addDoubleLinear"`, matched nothing, and returned
   an empty list — so the bake sampled nothing, deleted the whole network and
   took every twist value with it, while reporting "0 twist joint(s) baked"
   in a message nobody reads twice. Identify a node by what it is WIRED to,
   or record it; never by a type string you have not printed.
42. **Maya splices a `unitConversion` in wherever a unitless double meets an
   angle, and it is not in your manifest.** Our twist network ends in an
   addDoubleLinear whose `output` is a plain double, and the joint's
   `rotateX` is an angle — so `connectAttr` quietly creates a node in
   between, and a second one in front of the weight multiplier where
   `quatToEuler.outputRotateX` feeds a double. Two consequences, both
   measured: **no walk of `.output` finds the driven channel** (it finds the
   conversion node), and a conversion left out of the manifest **survives the
   bake still wired to the channel** — which then has an input driven by
   nothing, and no key can be written to it. Collect them after wiring
   (`listConnections(node, type="unitConversion")`) and record them as ours.
   The conversion also costs a little precision: the exact 22.5 comes back as
   22.4999998, degrees through radians and back.
43. **`cmds.selectKey(clear=True)` raises `TypeError: Error retrieving
   default arguments` when the selection is empty.** It wants objects to
   resolve its defaults against, even though clearing a key selection needs
   none. `overrig.full_rate_capture` calls it before every chain capture, so
   **Build crashed whenever nothing was selected** — and it went unnoticed
   for weeks because an animator presses Build having just clicked something,
   and every live proof selected a bone on the way in. The failure is exactly
   the case where there is nothing to clear, so the guard swallows it.
47. **A verify script that builds a skeleton by SHORT NAME injects joints
   into the ANIMATOR'S character, and a `finally` that deletes its group
   cannot clean up a failure that happened before the group existed.**
   Measured 2026-09-01: `verify_two_characters.py`'s first draft did
   `cmds.select(parent_short_name)` per joint. In a scene already holding a
   Manny, `cmds.select("root")` resolved to the animator's root, so the
   test skeleton was grown INSIDE their character until an ambiguous name
   (`neck_01`, which by then existed twice) raised `ValueError` — leaving
   six joints behind: `root1` at world level and `pelvis1`, `spine_06`,
   `spine_07`, `spine_08` and a second `neck_01` inside the animator's
   skeleton. Maya increments a trailing number until the name is free,
   which is why an injected `spine_01` comes out as `spine_06` on a rig
   that already has `spine_01..05` — the debris does not look like debris.
   Three rules out of it: build with LONG paths, register every created
   node's UUID **as it is created** and delete from that registry in the
   teardown (not from a group that may not exist yet), and clean up by
   signature — childless, no skinCluster, no animCurve, and a name the
   canonical 93-joint template does not carry — never by guesswork.
48. **`cmds.ls(stale_long_path, uuid=True)` returns `[]`, so a loop that
   skips on "no uuid" silently skips everything after the first rename.**
   `other_skeletons_held` renamed a skeleton's ROOT first and then walked
   the descendant paths it had collected beforehand; each was stale, each
   returned no uuid, and each was passed over by a `continue` meant for
   deleted nodes. The hold reported success (nothing in its `failed` list)
   while holding exactly one joint out of twenty-one — and the FBX merge
   stayed as ambiguous as it had been. Silent skips need to be counted as
   failures, or measured directly: the gate that caught this asserted every
   held joint's name, not the absence of errors.
49. **A module-level context is per module OBJECT, so purging `sys.modules`
   while a panel is open splits it in two.** Measured 2026-09-01:
   `picker_window.connect_root("|root")` returned True and the panel showed
   "Connected to root", while `active.root()` read **None** in the same
   send — the live window's `active` was the module object from before a
   verify script's purge, and the freshly imported one was a different
   object with its own `_ROOT_UUID`. Two things purge: every bridge script
   (note 9) and `install.purge_modules` on an update. This is exactly why
   `manifest.activate(scene_map)` re-derives the character from the binding
   map at every entry point instead of trusting what Connect set, and why
   `picker_window._resolution` re-asserts its own binding on every sync —
   both were written for staleness and both cover this too (verified:
   `active.clear()` followed by `activate(scene_map)` answers `|root`).
   Nothing to fix; do not "simplify" either of them into reading the
   context once.
51. **A LOCKED plug makes `cmds.xform` a silent no-op, and the FBX importer
   locks a skinned mesh's transform.** All nine of t/r/s, measured. So
   `flatten_wrappers` moved the joints correctly and could not move the
   mesh at all: the skeleton stood up and the geometry lay on its side
   («скелет стоит на правильном месте а геометрия нет»), because the
   skinCluster's stored `geomMatrix` still holds the wrapper's -90 and
   wants it supplied from the DAG above the mesh. Sampled vertices came
   out as `(x, -z, y)`; the bbox had Y and Z swapped. **Two strategies
   failed IDENTICALLY before the cause was found** — preserving the mesh's
   world matrix and preserving its local matrix — and that they agreed was
   the clue: nothing written to that transform was landing. Unlock around
   the write, lock exactly what was locked back, and the drift is
   0.000000 on both the bbox and the head. The other half of the lesson is
   about gates: every gate in the failing run passed, because they all
   measured JOINTS. Bones are the easy half to measure and the wrong half
   to trust.

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
import sys; sys.path.append(r"C:/!!!Work/MayaScripts/SkeldarAnim")
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
| `records.py` | record model, search, namespace naming, row text, **the package↔disk-path pair and the reimport reply's wording** | **stdlib only** |
| `vcs.py` | Perforce placement: fbx name search, path convention, checkout decision table, p4 runner | **stdlib only** |
| `animimport.py` | FBX import, timeline, fps policy, the target rule (selection then connect) and the exmerge name hold | `maya.cmds` |
| `animexport.py` | FBX export of the skeleton hierarchy, bake-on-export, range policy | `maya.cmds`, `maya.mel`, `animimport` |
| `uassetexport.py` | **Export to uasset: the direct road.** The warning, the read-only flag, the temp fbx. Imports no `vcs` and a test enforces it | `maya.cmds`, `animexport`, `animimport`, `records`, `uelink`, `uescripts` |
| `window.py` | the `cmds` window | `maya.cmds` |
| `checkouts.py` | the checkouts window: pair checkout, revert, export back to the uasset | `maya.cmds` + all of the above |

The first four are testable with neither application running; a subprocess
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

**The target skeleton is chosen, never assumed** (`choose_target_root`, pure).
The order, since 2026-09-01, is the animator's own words ("кнопочка импорт и
экспорт должна прежде всего смотреть не выделена ли у нас иерархия костей…
если выделение пустое тогда смотрим в коннект"):

```
selection -> the picker's CONNECTED character -> the only skeleton
          -> the one named `root` -> refuse
```

The connect sits ahead of "the only skeleton" so a scene holding several
characters is decidable at all without clicking a bone first
(`animimport.picker_root`, lazy and guarded — the bridge is plain `cmds` and
PySide6 does not exist before Maya 2025). **`animimport.resolve_target()` is
the one function both directions use** — `animexport.resolve_root` delegates to
it, so Import and Export can never disagree about "the" character, which is
what "такая же логика с экспортом" asked for. Namespaced roots are never
candidates at any step — they cannot receive a plain-name merge, and in this
tool they *are* the reference imports of earlier clips. Two plausible
skeletons with no hint is still refused, because guessing animates the wrong
character in silence.

**Choosing right is not enough on its own.** `FBXImport -v exmerge` matches
bone names INSIDE the FBX plugin, so with two Mannys in the scene `pelvis` is
ambiguous and the plugin lands on whichever it finds. So every OTHER plain-named
skeleton's joints are renamed to `rpHold_<name>` for the length of the call and
restored in a `finally` (`other_skeletons_held`). A rename is invisible to
connections — constraints, skinClusters and animCurves are wired to nodes, not
names — and it is the only lever that reaches inside the plugin's own matching.
Namespaced skeletons are skipped: their bones cannot collide, and a REFERENCED
skeleton (always namespaced) could not be renamed anyway. The whole mechanism
is a no-op in a single-character scene. `roots=` narrows the candidates so a
verify run can exercise it on throwaway characters instead of the animator's.

**Collect every UUID before the first rename, and resolve each path from its
UUID right before its own rename.** `root` is a bone in every UE clip so it is
held like any other — and renaming it invalidates the path of every joint
beneath it. Measured live 2026-09-01: walking the paths straight through
renamed the root and then SILENTLY skipped all twenty bones under it (the
stale path made `cmds.ls(path, uuid=True)` return nothing, which the loop read
as "gone" and passed over), leaving the merge exactly as ambiguous as before.
The gate that caught it was "B's bones are renamed for the length of the
merge"; nothing else would have.

**And the target's OWN root is renamed too** (2026-09-02, the animator:
«анимация root кости переносится только на первый скелет … на последующие
скелеты мы ее не переносим»). Holding the other characters aside frees
`pelvis`, but Maya renamed exactly ONE joint of the second character when
it arrived — the root, because a top-level node's path IS its short name —
so the clip's `root` reached nothing and the character played the clip on
the spot while the first one walked (**67 of 68 bones**, measured, and
recorded here for months as a cost rather than a bug).
`target_root_plain(target, joints)` nests inside the hold and gives the
root its undecorated name back for the length of the call. **Both
directions**: `export_hierarchy` wraps the same manager, or the FBX handed
to Unreal names a root the UE skeleton does not have.

Three things it does that are each load-bearing. It **refuses to guess** —
`plain_root_name` (pure) accepts only a decoration *relative to the
skeleton's own bones*: strip trailing digits, then `root` or `<prefix>_root`
where no other bone wears `<prefix>`. That is the exact statement of the
mechanism (only the top node collides), and it is what keeps `ik_foot_root`
— a real UE bone whose children `ik_foot_l`/`ik_foot_r` wear the prefix —
and every non-UE rig out. It **frees the name first**, displacing whatever
answers to `root` with the same `rpHold_` prefix: on the import path the
hold has already done it, on the export path the first character has not.
And it **checks the name Maya actually gave it** — `cmds.rename` onto a
taken name succeeds with `root1` rather than failing, and `root1` matches
the clip no better than the name we started with, so that is undone at once
and reported as nothing done. A wrong answer costs nothing: the rename
either matches the clip's root or matches nothing, which is exactly the old
behaviour, and either way the name is put back in a `finally`. Spec:
`docs/superpowers/specs/2026-09-02-root-name-collision-design.md`. Proof:
`verify_uebridge_root_name.py`, **20 gates, 0 failed** — including the
control that suppresses the rename and measures the root NOT moving
(0.000000000 against 100.0000000), which is what makes the gate one that
can fail.

**The target's animation is cleared first**, and that is load-bearing rather
than tidiness — see trap 27. Bones the clip has no keys for end up unanimated
and are named in the status line.

**A weapon-driven `weapon_r` is re-linked across the merge** (2026-08-21):
the sword's constraint would otherwise refuse every import (trap 37's guard).
Our links are found read-only BEFORE the refusal — a refusal must leave the
scene untouched — then unlinked (the bone baked back), and after the timeline
is set the sword is snapped onto the bone and re-linked, picking up the new
clip's weapon motion. Lazy `maya_scenesetup` import, so a Maya without the
weapon tool behaves exactly as before. The status line names the re-linked
bones.

Proof: `docs/superpowers/plans/verify_uebridge_merge.py` (**25/25 green**). It
imports one clip twice — merged, and as a reference skeleton — and compares
them frame by frame: 120 samples, worst 0.000000°, root motion 0.000000 cm.

**Connect to version control** (2026-08-21) reroutes every import through
the working FBX in the SourceArt tree: the editor still exports to temp,
the file is then PLACED onto the working copy (`vcs.place`) and Maya
imports THAT path — the scene references the working file, not a temp
copy. The working file is found **by name** under the source root, on the
disk AND in the depot (`vcs.find_fbx` + `vcs.find_fbx_depot` — a file at
head that was never synced is invisible to a disk walk, and treating it
as new misplaced a Longsword import «в папку на уровень выше»); a
depot-only hit resolves to the `clientFile` that `p4 fstat` reports even
for an unsynced file, and `checkout`'s not-on-client sync-retry brings it
to disk on the way to `p4 edit`. The path convention
(`vcs.conventional_folder`) is the depot's **pure mirror**: insert
`Exports` after `Animation`, keep everything else — the first version
dropped a trailing `1P`/`3P` (inferred from the local Unarmed files,
which are NOT in the depot and do not follow the convention) and that is
exactly what put the Longsword fbx one level up; the depot keeps those
folders (measured: `.../Weapons/Longsword/3P/AS_*.fbx`). The convention
only decides where a NEW file goes, and a folder the user was asked for
once is remembered per uasset folder (`ueBridgeVcsDirMap`). The depot
pattern comes from `p4 -ztag where <root>/...` — blank-line-separated
records, exclusions carry `unmap`, the effective mapping is the LAST
record without one; wildcard output needs `parse_ztag_records`, the flat
`parse_ztag` silently merges records. First activation of the checkbox
asks for the source project root (`ueBridgeVcsRoot`); the `...` button
changes it later. The p4 side (`vcs.prepare_target`): untracked files are
just written — **no `p4 add`**, versioning is the export phase's job (the
user's call) — tracked-and-free gets `p4 edit` with one sync-retry on
"not on client", checked out by others raises the only modal (named
users, Cancel / Overwrite locally), and a dead p4 (expired SSO session,
no network, no exe) offers Continue locally. No depot state is mutated
before the export has succeeded. Three measured parser facts: **p4 exits
0 even for "no such file(s)"** — failures are classified by stderr text
and that message is a normal answer meaning untracked; **ztag's
other-open block is double-prefixed** (`... ... otherOpen0 ...`) — match
one prefix and every busy file reads as free; and a target outside the
workspace answers **"is not under client's root" with no article** (exit
code 1) — also a normal answer, "can never be in this depot", and the
assumed spelling with "the" cost a verify run. Every dialog is injectable
(`window._vcs_target(record, asks=...)`, the two asks of
`prepare_target`), because a modal over the command port blocks Maya
(bridge note 6). SourceArt maps to its own depot — `//atone-art`, a local
depot, not the `//atone/main` stream — and the three example Unarmed fbx
are NOT in it, only on disk. Verify: `verify_uebridge_vcs.py` — **green
live 2026-08-21, 0 of 14 gates failed** — builds a **sandbox source
root** (never the real SourceArt — a verify run must not overwrite the
animator's working files) and imports into its own namespace with
`set_timeline=False`; the depot gates are fstat reads plus one real
sync+edit on the Longsword fbx immediately `p4 revert`ed (skipped if
anyone holds the file open — never revert a file the animator opened,
their work would go with it). Getting it green paid for trap 44. Spec:
`docs/superpowers/specs/2026-08-21-uebridge-perforce-design.md`, whose
addendum records the depot-search redesign.

**The reverse bridge** (2026-08-21, the same day): the animator's checked-out
AnimSequence uassets always in sight, and the scene going back into the
uasset. **The bridge window is two tabs** (the user's ask, same evening:
«хочется видеть сразу все наши файлы на чекауте» — the afternoon's popup
lasted hours; its `ueBridgeCheckouts` window id is deleted on every open, or
a panel left up from the older build stays wired to dead code): **Import**
is the old window — list, search, import mode, the VCS row — plus
**Checkout**, which sits beside IMPORT because it acts on that list's
selection and opens the uasset AND its source fbx as a pair (the user's
call: one changelist, one submit; «source fbx — прокладка через которую мы
работаем», so a checkout through the bridge never leaves a uasset without
its fbx — a прокладка that exists nowhere is exported out of the editor
into the conventional spot on the way, then `p4 add`ed). **Export** embeds
the checkouts list (`checkouts.build_tab`) with EXPORT / Revert / Refresh;
EXPORT with nothing checked out degrades to a save-as dialog and a plain
fbx export. **Perforce is polled only by the tab's Refresh button and after
the actions that change it** (Checkout, Revert, EXPORT) — never on a tab
switch (the user's follow-up, 2026-08-22: «не нужно каждый раз опрашивать
перфорс»); between polls the list keeps its last rows, and the tab header
says Refresh is what re-reads. The top Refresh also re-reads them, but only
with the VCS checkbox on — a p4-less machine must not pay two 15s timeouts
per press. **Both lists mark the rows** (2026-08-22, «помечались визуальным
знаком например галочка... изменены выделялись зеленым»): a `✓` prefix on
every checked-out row (`checkouts.mark_prefix`, same-width blank otherwise,
so columns hold), and GREEN text on modified ones — `edit` rows by a real
`p4 -ztag diff -sa` (`vcs.modified_under`; measured: the digest compare
works on binary uassets, ztag carries clientFile, and "not opened" is the
normal empty answer), `add` rows always (no depot side to differ from).
The marks come from the LAST poll (`checkouts.marks()`), refreshed by the
same calls that refresh the rows; the colour goes through Qt
(`checkouts.paint_rows` — `textScrollList` has no per-row colour flag, but
underneath it is a QListWidget), best-effort so headless sessions skip.
`_repopulate` now also keeps the selection by package identity across
rebuilds, not by row index.
One status line at the window bottom serves both tabs. The listing is
`fstat -Ro <Content>/....uasset` (one
call, clientFile included; `p4 opened` would need a `where` per file)
matched against the cached listing by package — anything not a known
AnimSequence is dropped — with an fbx column (`ok`/`depot`/`MISSING`).
Revert reverts the pair behind the one confirm dialog. Export per row:
resolve the working fbx (same `choose_target` as import) → export the root
hierarchy to a temp fbx (`animexport`: resolved like the import merge —
selection, else the only skeleton, else `root`; bake-on-export so the rig
is never touched; range = animation ∪ playback, trap 38; keys outside are
warned) → p4 on the fbx (`prepare_target`, add after place for a new file)
→ `vcs.place` → reimport in the editor (`uescripts.reimport_script`) →
frame-rate mismatch reported, never fixed. The Content dir rides the
listing reply and cache as `content_dir` (old caches fall back to
discovery's `project_root`). Spec:
`docs/superpowers/specs/2026-08-21-uebridge-export-back-design.md` — its
addendum records why the reimport is a legacy-path replace-import. Proof:
`verify_uebridge_export.py`, **green live 2026-08-21, 0 of 18 gates
failed** — exporter round trip exact (35.000000 at the mid key), the
animator's 4 real checkouts listed with fbx, a duplicated sandbox uasset
reimported 2 → 60 frames and deleted, the Longsword pair checked out and
reverted with the depot left exactly as found.

**Export to uasset — the direct road** (2026-09-01, the user's ask:
«кнопочка экспорта в uasset… защитное предупреждение о перезаписи… если
uasset readonly то будем снимать эту настройку… пока что ни как не будет
связываться с функционалом для перфорса»). A third button on the IMPORT
tab — `Checkout | Export to uasset | IMPORT` — because it acts on the same
list selection. Deliberately not labelled `EXPORT`: the Export tab has one
of those and it goes through Perforce.

`maya_uebridge/uassetexport.py`. One press: resolve the record, the uasset's
disk path and the scene skeleton (`animexport.resolve_root` — selection,
then the connect: one function for every direction of the bridge) — every
refusal happening **before** any dialog; then a confirm that names the asset,
the skeleton, what a replace-import throws away (`Pose_0..9`,
`MoveData_*`, `DisableLegIK`, `RootMotionAdditiveInput` — trap 40), and
that Perforce is untouched; then the FBX to
`%TEMP%/maya_uebridge/<Name>.uasset.fbx`; then the read-only flag, cleared
and **left off** (the file is modified, and hiding that is worse); then the
editor. Export before chmod, so a failed export leaves the uasset exactly
as it was. The VCS checkbox does not change any of it.

**The "no Perforce" boundary is enforced, not promised.** The only thing
this road needs from `vcs.py` is the pure package↔path pair, so
`package_of`/`uasset_path_of` MOVED to `records.py` (`vcs` re-imports them,
so no caller changed), `reimport_line` moved there too, and a subprocess
test asserts `maya_uebridge.vcs` never reaches `sys.modules` through
`uassetexport` — plus an AST check that no `vcs`/`p4`/`prepare_target`
name appears in its code.

**A "successful" reimport that writes nothing is now reported**
(`records.unchanged_warning`). The editor answers `ok: True, saved: True`,
no notes and no error while leaving the animation untouched, so the status
used to read "reimported and saved (196 frames)" over an asset nothing had
been written to. The signal is frame count AND length both identical
across the import; the wording is "check the exported bones match
`<skeleton>`" rather than an error, because re-exporting an unchanged clip
looks the same. **Both export directions use it.**

Proof: `verify_uebridge_uasset.py` — **green live 2026-09-01, 0 of 25
gates failed**, and it proves BOTH directions of that warning on sandbox
assets duplicated into `/Game/__bridge_verify` and deleted again: a real
replacement comes out changed and unwarned (195 → 100 frames, and 90 → 100
on a second asset), and a no-op is never reported as a success. It also
exercises the read-only flag for real — `chmod 0o444` on the sandbox
uasset, cleared by the press — and asserts the animator's own uasset was
never touched.

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
44. **p4 inside Maya can see a DIFFERENT HKCU Perforce store than p4 in a
    shell — same user, same exe, same key path.** Measured 2026-08-21:
    `p4 set` from a shell answered `P4PORT=ssl:perforce.atone.com:1666`
    with a client set, while the same `p4 set` spawned from Maya answered
    the dead `ssl:perforce.pulse-game.digital:1666` with no client —
    `whoami` identical in both, a `winreg` read from inside Maya confirmed
    Maya's process genuinely sees the stale values, and a full registry
    search from the shell finds no "pulse-game" anywhere. Mechanism
    unidentified (some registry overlay); the SYMPTOM is p4 hanging to
    timeout only when called from Maya while the shell works — which reads
    exactly like a network problem and is not one. env vars were None in
    both processes, HOME made no difference, no .p4enviro file exists. The
    fix that works: write the correct values THROUGH the bridge
    (`p4 set P4PORT=...`, `p4 set P4CLIENT=...` from inside Maya) — after
    that both views agree and `p4 info` connects from Maya in under a
    second.
45. **Interchange owns .fbx on this engine build, ignores `FbxImportUI`
    options entirely, and swallows a bones-only fbx with "There was nothing
    to import from the provided source data".** Measured 2026-08-21: the
    same automated `AssetImportTask` imported nothing under Interchange and
    landed frames 2 → 60 after flipping
    `Interchange.FeatureFlags.Import.FBX` to 0 (read the value first,
    restore in a finally — it is a global editor toggle). Three sibling
    facts from the same run: `unreal.ReimportSubsystem` does not exist in
    this build's Python (the documented reimport API — hence the
    replace-import over the existing package, skeleton read from the asset
    itself); `task.imported_object_paths` stays EMPTY even for a successful
    import and `task.result` answers a deprecation warning — only
    `task.get_objects()` reports; and a replace-import rebuilds the asset
    from the fbx, so uasset curves the fbx does not carry (trap 40's
    Pose_*/MoveData_*) do not survive it, same as reimporting by hand.
46. **The editor runs its own Perforce integration, and its log is the
    diagnosis tool for silent import behaviour.** Saving a new asset fires
    `p4 add` from inside UE; deleting it fires `p4 revert -w` — so a
    scripted sandbox asset makes transient p4 noise even when our own code
    never calls p4. `<project>/Saved/Logs/<name>.log` is readable with
    shared access WHILE the editor runs; the Interchange refusal above was
    invisible in every Python-side reply and sat plainly in that log.

50. **A FRACTIONAL playback range makes UE refuse the animation, and the
    import task still reports success.** Measured 2026-09-01, and it is the
    single finding that decided whether Export to uasset worked at all. The
    animator drags the time slider and it stops at **88.792**; `union_range`
    handed that to `FBXExportBakeComplexEnd`; the editor log then said

        FBXImport: Error: Animation length 2.96 is not compatible with
        import frame-rate 31 fps (sub frame 0.752), animation has to be
        frame-border aligned. Either re-export animation or enable snap...

    — while the Python reply came back `ok: True, saved: True, notes: [],
    error: ""` and the asset kept its old animation to the last frame and
    the last 0.01 s. Two wrong theories died on the way (the second
    character's root being called `Manny_Skeleton_root` rather than `root`,
    and the sandbox's skeleton being a UE4 mannequin); both were killed by
    reading the log, which trap 46 already says is the tool for exactly
    this. `union_range` now snaps OUTWARD — floor the start, ceil the end —
    which can only widen the range and so cannot re-introduce trap 38's
    clipping. **This bug was in the Perforce export direction too**, since
    2026-08-21, and would have silently written nothing every time the
    animator's range happened to end on a fraction.

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
the open scene carries it, so renaming it would orphan that weapon and Add
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

A small window: an **Add Character** button (below), a dropdown of weapon
models, a field for pasting the path of any other FBX, an **Add** button
that imports the chosen one, hangs it under the HAND and drives `weapon_r`
from it (below), a **Remove Weapon** button, live rotate/translate fields
for dialling in the grip, and an **Add Aim** button (below). Design:
`docs/superpowers/specs/2026-08-17-weapon-attach-design.md`, proof:
`docs/superpowers/plans/verify_weapons.py` (**rebuilt 2026-08-21 around the
inverted drive and green live the same day: 32/32** — the marked node is
`LongSwordMesh` itself, a direct child of the HAND, `weapon_r` driven by it
with the transfer, the drag-follow, the replace and the detach all at worst
**0.0000000** over three-frame world-matrix tracks — re-run green **31/31
on 2026-08-25** under the final bone-relative build, on a real UE clip
carrying 47 frames of weapon_r. The in-scene grip gates skip themselves
in a scene with a real clip (their relink simulation rewrites the bone's
keys) and still await a bind-pose-scene run; the grip MECHANICS are proven
live by a sandbox chain the same day, **13/13, every number 0.0000000**:
sword at the bone-relative grip, offset kept across the transfer, the bone
on its ORIGINAL track, unlink restoring it, relink under the same stored
grip, a clean bone unmoved by Add, a live re-dial moving only the sword,
and the fields reading the grip back from world matrices). It
refuses to run at all while the arms are connected or an aim exists: every
attach in it REPLACES what is in the hand, and replacing deletes the marked
node whole.

```python
import sys; sys.path.append(r"C:/!!!Work/MayaScripts/SkeldarAnim")
import maya_scenesetup; maya_scenesetup.show_window()
```

| Module | Responsibility | May import |
|---|---|---|
| `catalog.py` | the weapon table AND the character table, lookups, an entry for any FBX on disk (`entry_for_path`, `node_key`) — pure data | **stdlib only** |
| `fbximport.py` | one home for the FBX import-MODE guard (trap 33), shared by the weapon and the character | `maya.cmds`, `maya.mel` |
| `character.py` | the working character into the current scene: import, the rename note, connecting it, the malware sweep | `maya.cmds`, `catalog`, `builder` + `picker_window` (both lazy) |
| `skeleton.py` | which character — and it becomes the ACTIVE one — and where its weapon bone is | `maya.cmds`, `maya_overrig` |
| `bonedrive.py` | a bone that follows a marked node: `link`/`unlink`/`relink`, grip-space composition, range policy; owns `MARKER` | `maya.cmds`, OpenMaya (a leaf — the bridge imports it lazily) |
| `attach.py` | find the mesh, parent it under the hand, invert the drive, read/write offsets | `maya.cmds`, `bonedrive`, `fbximport` |
| `aim.py` | where the aim locators go, and the press that builds it | `maya.cmds`, OpenMaya, `attach`, `overrig`, `aimrig` |
| `window.py` | the `cmds` window, offsets, optionVars | `maya.cmds` + the four above |

`catalog.py` stays stdlib-only (subprocess test) and `__init__.py` resolves
`show_window` through `__getattr__`, both for the same reasons as
`maya_overrig`. The window is plain `cmds` — a dropdown, a button and two float
rows need no Qt — and every callback goes through `_run`, which puts the
failure on the status line instead of the Script Editor (trap 20).

**Add Character** (2026-08-25) puts the working character into the CURRENT
scene — the content the animator used to get by opening
`C:/!!!Work/Animations/Rigs/Characters/Manny_Sckeleton.ma` by hand (the typo
is in the real filename): 93 joints, 6 meshes, `camera_root`/`camera_bone`
inside the skeleton, `bindPose2`. The shipped `assets/Manny_Skeleton.ma`
(typo fixed) is that file with exactly the 13 **"vaccine" malware lines cut**
(`vaccine_gene`/`breed_gene` script nodes — the infection already on record
for this studio's scenes). The cut is textual and diff-verified; never
"clean" it with a Maya open-and-resave, which would have to load
mtoa/USD/materialx to not mangle their nodes and would execute script nodes
on the way in. `catalog.character_path()` resolves shipped-copy-first with
the user's original — infected, typo and all — as the legacy fallback, which
is why `character.add_character()` also **sweeps imported script nodes**
named like the malware on every press (import never executes script nodes,
so the sweep always wins the race). Import, never open, and **no
namespace** — the UE bridge merges clips by plain bone names.

**A DROPDOWN of skeletons** (2026-09-01, later the same day: «я бы хотел
иметь возможность добавлять скелет UE4_Mannequin… в add character сделаем
выпадающий список»). `catalog.CHARACTERS` is a table like `WEAPONS`, so a
third skeleton is a row rather than a branch, and the `optionMenu` above the
button is filled from it. The choice is remembered in
`mayaSceneSetup_character`; **Manny is row 0 and the default**, so anyone
who never opens the list has exactly the old behaviour.
`character_path()` with no argument still means Manny — deliberately, since
`maya_skelfit`, `verify_add_character.py` and three test modules ask that
question and none of them is about the dropdown.

**Row two is `assets/UE4_Mannequin.fbx`** — 1.0 MB, **68 joints, 2 meshes**,
exported once from `/Game/SwordAnimsetPro/UE4_Mannequin/Mesh/SK_Mannequin`
in the animator's own project through `uelink` (`AssetExportTask`,
`automated=True`, `load_asset` guarded — trap 24). The
Longsword/SwordAnimsetPro packs' ~1200 clips all run on it. Verified in a
standalone Maya before shipping: root at `|SK_Mannequin|root`, **no script
nodes at all**, `spine_01..03`, no metacarpals, no `neck_02`, one twist per
segment. Extracting it from the animator's `UE4_To_Many.ma` instead would
have meant separating one skeleton out of 299 joints across three skeletons
plus an AdvancedSkeleton rig, and sanitizing two vaccine/breed nodes.

**It has no `weapon_r` and no `camera_bone`** (measured), so Add Weapon and
Camera Setup refuse on it through their existing "bone not found" path.
That is stated rather than worked around; `ik_hand_gun` is not substituted.
**The rig is neither blocked nor promised**: the UE4 schema is exactly what
`verify_missing_bones.py` proves, so Connect and Build are likely to work,
but nothing on this skeleton has been live-verified.

**Both imports leave the same SHAPE** (2026-09-01, the animator's first
note after using it: «ue5 скелет вставляется кости отдельно меш отдельно,
UE4 вставляется в одной группе с мешем, нужно сделать однородно»). Flat won
— Manny's shape, unchanged — so the FBX importer's wrapper is flattened
away by `character.flatten_wrappers`.

**And the wrapper was a BUG, not untidiness.** It carries the axis
conversion (`rotateX -90`, Z-up to Y-up) while `root` beneath it is clean,
and no import option changes that (`FBXImportUpAxis y`,
`FBXImportAxisConversionEnable`, `FBXImportForcedFileAxis z` all tried
standalone, all produce the wrapper). A UE clip carries **that same -90**,
on `root`'s jointOrient — so a merge onto a WRAPPED skeleton applies it
twice and the character lies down. Measured standalone from one clip: head
at rest `0, 165.5, -4.0` either way; at frame 0 **`4.7, 2.96, -147.8`
wrapped against `4.7, 147.8, 3.0` flat**. The earlier "68 of 68 bones
animated" was true and the character was on its face; nothing had measured
which way up it stood.

**A plain unparent moves the skeleton 90°** (measured: worst world-matrix
element 1.0). Maya distributes a joint's new parentage into `jointOrient`
and the arithmetic it picks is not the pose-preserving one. So the flatten
records every child's world matrix BY UUID, unparents, and re-asserts the
world matrix by hand; the rest pose then comes out identical (165.516 both
ways). FBX only — running it over Manny's `.ma` would flatten the transform
that legitimately holds its six meshes.

**What flat costs, and it is Manny's existing cost:** at world level Maya
will not allow a second `root`, so in a scene that already holds one the
mannequin arrives as `root2` — as a second Manny arrives as
`Manny_Skeleton_root`. An exmerge matches bone NAMES, so the clip's `root`
used to match nothing and that one bone came in unanimated: **67 of 68**,
measured. **Fixed 2026-09-02** — the bridge gives the root its undecorated
name back for the length of the merge and of the export
(`animimport.target_root_plain`, see the UE bridge section); the decorated
name in the outliner is now cosmetic. The old note read this as a cost of
the flat shape. It was the feature failing on every character after the
first, and the animator reported it as such.

**The FBX row is why the import forks**, and trap 33 is the whole story:
`character.scene_type` answers `FBX`, and that path goes through
`fbximport.import_nodes`, which forces the plugin's global import MODE.
`maya_uebridge` leaves it on `exmerge`, where the importer creates NOTHING
— so without the guard Add Character would silently stop working after any
animation import from Unreal. The guard used to live inside
`attach.import_model`; it is one module now, because a fix for a silent
failure that exists in two copies is a fix that will exist in one copy soon
enough. The live gate sets the mode to `exmerge` on purpose before pressing.

**And the flatten has to write through the importer's LOCKS** (trap 51,
2026-09-02): the FBX importer locks a skinned mesh's t/r/s, a locked plug
makes `cmds.xform` a silent no-op, so the first version moved the joints
and left the mesh lying on its side. Unlock around the write, lock exactly
what was locked back; drift 0.000000 on both the bbox and the head. The
verify now measures the MESH's world bounding box, because every gate in
the failing run passed while the animator looked at a character on its
side — they all measured joints.

**The mannequin is greyed on arrival** (2026-09-02, «сильно темный»): UE
puts no textures in the FBX, so `M_UE4Man_Body` and `M_UE4Man_ChestLogo`
come in at color (0,0,0) and the reference figure is pure black.
`grey_black_materials` sets a near-black, **untextured** colour to Maya's
own default grey — textured never, whatever the plug reads, because the
texture is what decides the look. FBX path only: a black material in
Manny's `.ma` is somebody's choice.

**`import_asset` returns UUID-resolved paths**, and that is not tidiness:
the flatten re-parents everything out of the wrapper, so the import's own
long paths are stale by the time the caller counts them (trap 16). Against
stale paths the status read "0 joints, 0 meshes" and the malware sweep —
which walks that same list — scanned nothing.

Proof: `verify_add_character.py`, **green live 2026-09-02, 0 of 30 gates
failed** — the flat shape (skeleton and mesh at world level, no wrapper),
the rest pose surviving the flatten to 0.01, the mesh standing where the
skeleton does, the locks restored, the materials grey, the press counting
what actually arrived, and the point of the feature:
a `SwordAnimsetPro` clip imported onto the freshly added mannequin, every
bone the clip can name animated, the bridge resolving it as the target
through Connect, **and the animated character standing up** (head at
`4.68, 147.84, 2.96`). That last gate is the one the flatten exists for;
gate 31 computes its expectation from the root's actual name rather than
asserting the happy case.

**Press it as many times as you like** (2026-09-01, the user's ask: "я должен
иметь возможность добавить в сцену сколько угодно персонажей"). The old
blanket refusal — any skeleton in the scene and the press did nothing — is
GONE, and so is its premise: the picker and the bridge no longer guess between
two characters, they are told. `character.refusal` and `ALREADY` are deleted
rather than disabled, with a gone-test pinning it. Two things replaced them.
**The message names the rename** (`character.rename_note`): only the TOP node
collides, and `pelvis` and everything under it keep their plain names — which
is precisely what lets the bridge go on merging clips onto the second
character by name. **Two different renames, both measured live 2026-09-01,
and the difference is worth knowing**: a `cmds.file(i=True)` of a `.ma`
prefixes the clashing top node with the FILE STEM — the second Manny's root
comes out `Manny_Skeleton_root`, not `root1` — while a plain `cmds.rename` or
`duplicate` collision increments a trailing number instead, and increments it
until the name is free (an injected `spine_01` on a rig that already has
`spine_01..05` lands as `spine_06`, trap 47). So never predict the new root's
name: `character.new_root` is a path DIFF for exactly that reason.
**The new character is connected on arrival**
(`character.connect` → `picker_window.connect_root`), so "add it" and "work on
it" are one press; the import is a lazy guarded one, because Scene Setup is
plain `cmds` and has to keep working where PySide6 does not exist.

Proof: `verify_add_character.py`, **rewritten and green live 2026-09-01, 10
gates, 0 failures** in the animator's scene (which held a Manny) — the second
character arrived as `Manny_Skeleton_root` with all 93 bones resolving by
plain name, the first character untouched, the new one active, and the scene
back to one root afterwards. Its old branch proved the refusal, which no
longer exists; the empty-scene branch still runs the 13 original gates.

Two pre-existing warts to not chase: every `.ma` import
leaves Maya's locked/singleton furniture behind (`UsdDefaultRenderSettings`,
`shapeEditorManager`, `poseInterpolatorManager` — the verify's cleanup gate
excuses them by class, never by name), and the character scene carries a few
of its own leftover PoleLock expressions that print a divide-by-zero warning
on import — both predate the button and both happen with a manual open/import
too. `assets/` is already whole in the installer payload, so the character
rides the SkeldarAnim install. Spec:
`docs/superpowers/specs/2026-08-25-add-character-design.md`. Proof:
`verify_add_character.py` — adaptive: in the user's live scene (which held a
skeleton) the refusal path ran green (5 gates, scene untouched); the full
import path ran green in mayapy **standalone** (13 gates, 0 failures —
"Manny added - 93 joints, 6 meshes", weapon_r and camera_bone resolving,
header binding, second press refusing, cleanup leaving only the excused
singletons).

**The character comes from the picker.** `maya_overrig.picker_window` gained one
module-level `bound_root()`, which finds the open window and returns its bound
root; the binding lives in the live window and is persisted nowhere else. With
no picker the module binds as the picker does — the selection, else a lone
skeleton via `builder.character_roots()` (trap 1: a built rig reports a dozen
"skeletons") — and **refuses to guess** between two candidates. The bone is
then resolved inside that root's subtree through `naming.hierarchy_map` +
`detect_prefix`, never scene-wide: a bare `ls("weapon_r")` would arm whichever
character Maya listed first.

**The weapon IS the geometry** (2026-08-20, the animator's call: «для оружия не
должна создаваться какая-то группа, я хочу анимировать просто выделяя
геометрию»). After the import `attach.mesh_transforms` looks for the transforms
that hold a mesh; **exactly one** and that transform is parented straight into
the bone, takes the `mayaWeapon` marker, is seated by `seat` and holds the grip
in its own `translate`/`rotate` — and whatever the file came wrapped in (the
null an exporter puts around the mesh, which is precisely the group being
complained about) is deleted afterwards. Only leftover **transforms** are
deleted: the shading network arrived in the same import and the mesh needs it.

**Zero meshes or several keep a group** and `attach.attach` returns a note the
status line shows. Two meshes cannot both be the node the offsets live on, and
one click cannot select both; refusing the file outright would be worse than
the group. So the return is `(path, note)`, and `note` is `""` in the normal
case.

The CONCEPT is unchanged, which is why nothing downstream moved: exactly one
marked node per bone, found by that attribute and never by name. One weapon per
bone — Add deletes the marked node first, so the live fields always have
exactly one thing to move, and a child the animator parented by hand is never
touched. **Trap 34 stops being reachable** in the normal case: the marked node
and the geometry are the same node, so a control hung on it cannot be a sibling
of the mesh.

Two consequences worth knowing before they surprise someone. **`seat` now
zeroes the artist's own transform on the model root** — one node cannot hold
both their transform and our offsets, and offsets that are not the channels on
screen would make the fields a lie about the scene; the grip is dialled once
and remembered. And **`model_root` asks whether the node itself holds a mesh
BEFORE looking at its children**, or a mesh the animator parented under the
sword by hand would outrank the sword.

**The weapon drives its bone** (2026-08-21, the user's ask: «перекинуть на
него анимацию с weapon bone а потом weapon bone привязать к оружию... крепить
к кисти а не к вепон боне»). The Camera Setup pattern applied to the weapon:
Add parents the mesh under **`weapon_r`'s own DAG parent** (`hand_r` on
Manny — resolved as "the drive bone's parent", never by name), snaps it onto
`weapon_r`, writes the grip, moves any MOVING animation the bone carried
onto the mesh's channels (temp constraint + bake, **mo=True since
2026-08-25 — the transfer keeps the sword's offset from the bone**, i.e.
the grip; constant curves are not animation, trap
30), cuts the bone's curves and parent-constrains `weapon_r` to the mesh
with **`maintainOffset=True` (2026-08-25, the user's ruling: «главное чтобы
наша анимация сохранилась в исходном виде») — the captured offset is the
grip's inverse, so the sword plays grip∘clip while the bone keeps playing
exactly the clip it always had**. The grip is a Maya-side model correction
and never reaches the export bone; with no grip the offset is the identity
and the bone rides the sword 1:1. The camera drives its bone through the
same flag. The offset is captured on a SAMPLED frame (range start, time put
back) — after the transfer the sword is a baked curve, and a fractional
currentTime would bake an interpolation error into the offset for ever. It has to be the hand: a node cannot both
parent the weapon and follow it. All of it is `bonedrive.link`; the ranges
everywhere are the union of the playback range and the driver's own keys
(trap 38 from the export side). Consequences, each deliberate:

- **Replace and Remove give the bone its animation back first**
  (`attach.detach` = `bonedrive.unlink` — bake the bone off the sword,
  drop the constraint — THEN delete; the camera paid for the other order).
  **Remove Weapon** is a new button because hand-deleting the sword now
  loses the bone's animation and orphans the constraint (trap 4); it is
  refused while the arms ride the weapon or an aim exists, like Add.
- **The grip is BONE-relative** (2026-08-25, the user's third ruling that
  day: «наше оружие подставляется в позицию вепон боны с указанными
  офсетами» — the intermediate build applied the fields as channels under
  the HAND, which put the sword at the hand). Zeros mean exactly on
  `weapon_r`; the placement is `bonedrive.apply_grip` → `place_at_grip`
  (grip × the bone's WORLD matrix, two snap-style xform writes — the DAG
  parent never enters the math), and the read-back is `measured_grip`, so
  a sword nudged by hand in the viewport reads back honestly. This is the
  pre-2026-08-21 meaning, so the optionVar is the ORIGINAL
  `mayaSceneSetup_offset_<key>` (legacy `mayaWeapons_offset_*` read
  second, verbatim — grips dialled before the inverted drive return). The
  under-hand era name `mayaSceneSetup_grip_*` (2026-08-21..25 only) is
  deliberately never read, its numbers mean nothing in the bone space;
  `grip_values`, `composed_grip`-migration and `attach.write_offsets` /
  `read_offsets` are gone rather than disabled (gone-tests pin it).
- **The grip is placed BEFORE the link and RIDES the transfer**
  (2026-08-25, the user's first report that day: «офсеты… больше не
  учитываются» — the original grip-after-link applied it only to an
  unanimated bone, and a UE clip always animates `weapon_r`, so in
  practice Add always dropped it). The transfer keeps the sword's offset
  from the bone (mo=True, identity when no grip) — bone-relative, that
  offset IS the grip exactly, so the sword plays grip∘clip for the whole
  clip with no capture-frame dependence. The final constraint's mo=True
  keeps the BONE on its original track (the second ruling — the first fix
  had the bone follow grip∘clip, rejected at once). A re-Add with the same
  grip captures the same offset — nothing compounds. The grip is ALSO
  stored on the marked node (`mayaWeaponGripRotate/Translate`, written by
  `apply_grip`; bone-relative since the space change, a file saved with
  the 4-day under-hand build re-links slightly off until one re-Add) so
  the bridge's relink re-applies it after every clip import. With
  transferred animation on the sword the FIELDS are quiet (`is_animated`,
  as after Connect) — they show the remembered grip, never the animation's
  frame values: showing frame values is how a re-Add once saved them over
  the remembered grip. `add_weapon` re-runs `refresh` first for the same
  staleness reason; typed values survive the re-read through
  `offsets_changed`'s save. Three spec addenda record the full reasoning.
- **A live grip dial goes through `bonedrive.regrip`, never a plain
  placement**: the bone plays its own animation through the constraint's
  captured offset, so moving the sword under a live constraint drags the
  bone along by the OLD offset. Regrip drops our constraint (the bone
  freezes exactly where the invariant held it), places the sword at the
  new bone-relative grip (`apply_grip`), and remakes the constraint
  capturing the new offset — the sword moves, the bone does not. No
  constraint, or somebody else's, gets a plain placement and the
  constraint left standing.
- **Connect is unchanged** and Disconnect returns the sword **under the
  hand**: the constraint targets the node, not the path, so it survives
  `parent_out`/`parent_in` and `weapon_r` keeps following the sword out in
  world and back. Old files (sword parented under `weapon_r` by the old
  version) are still found — the lookup asks the hand first, `weapon_r`
  second — and come off cleanly through the same detach.
- **The UE bridge re-links across a merge** (the user's call over refusing):
  `weapon_r` under our constraint would trip the trap-37 refusal on every
  import after an Add, so `animimport` finds our links read-only
  (`bonedrive.find_links`), refuses only on OTHER constrained joints (a
  refusal touches nothing), unlinks ours, merges, and after the timeline is
  set re-links — the sword's stale curves are cut, it snaps onto the bone,
  takes its stored grip back (2026-08-25 — a merge's contract is "the scene
  plays this clip", but the grip is not the clip's to flatten) and picks up
  the new clip (`bonedrive.relink`). Lazy, guarded import: a
  Maya without `maya_scenesetup` gets the old behaviour exactly. The camera
  is out of scope — `camera_bone` sits outside the skeleton subtree, so its
  constraint never reaches the guard.

Spec: `docs/superpowers/specs/2026-08-21-weapon-drives-bone-design.md`.

**The FBX field** takes a path to any file the catalog knows nothing about and
wins over the dropdown while it holds one. It resolves in ONE place
(`window.chosen_entry` → `catalog.entry_for_path`), so Add, the offset fields,
Connect and Add Aim all follow it with no line of their own. The bone comes
from the dropdown; the scale is fixed at **1.0**, because a size correction is
a fact about one known model and applying the sword's to somebody else's file
is a surprise; the key is the file's stem through **`catalog.node_key`**, which
must produce a legal Maya name — the key reaches `cmds.sets` by way of
`RigPicker_aim_<key>`, so a space, a dot or a leading digit there is a
traceback on some later press. Quotes are stripped (that is how Explorer copies
a path) and whitespace counts as empty. The path is remembered in
`mayaSceneSetup_custom_fbx`. Spec:
`docs/superpowers/specs/2026-08-20-weapon-is-the-geometry-design.md`.

**`cmds.file` here, `FBXImport` in the UE bridge.** The opposite of trap 22 and
deliberate: trap 22 is about losing animation curves, a weapon model has none,
and `returnNewNodes` gives the exact node list `FBXImport` cannot report at
all. Say this out loud in the code, or the next reader "fixes" it into a bug.
The import mode is set explicitly on every import and the previous one put
back — see trap 33, which is what `cmds.file` DOES inherit.

**Connect Arms To Weapon** turns the rig inside out: the weapon leaves the
skeleton and drives the hands. Three steps, in this order —
`maya_scenesetup/connect.py`, proof
`docs/superpowers/plans/verify_connect_arms.py` (**22/22 green live
2026-08-21**, with the drive-bone gates: `weapon_r` rode a 50-unit sword
drag through the whole Connect, and the trap-34 drag now goes through a
key — after Connect the sword's channels are always baked, so a bare
setAttr gate reports "driven" instead of proving anything):

1. **both arms brought to IK** — *brought to*, not switched. `switch_limbs`
   converts to the OPPOSITE type, so calling it on an arm that is already IK
   hands back an FK arm; the state is read from `builder.built_limbs()` and
   only the limbs that need it are switched (`connect.limbs_to_switch`);
2. **the weapon out to world** (`overrig.parent_out`), carrying the world
   motion it had, now baked onto its own channels;
3. **the IK end controls onto the weapon's GEOMETRY**
   (`fkcontrols.hang_ik_end_on` with `attach.model_root(weapon)`), each
   lifted to world first — re-parenting a knot in place is not a measured
   path, and lift-then-hang is what `switch_limbs` does with riders. The
   geometry, which since 2026-08-20 is usually the marked node itself: see trap 34.

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
controls are the weapon's DAG children — replacing would take both arm rigs
down unbaked) and the **offset fields go quiet** once the weapon carries
curves, since `setAttr` on a connected channel raises.

**Disconnect** lifts the hands off and calls `hang_ik_on_root`, which puts them
back under the root controller *when there is one*. A rig built by Switch after
a full bake has no root controller and stands in world — so the status line
says "off the weapon" and never names a destination that may not exist. The
weapon goes back **under the hand bone** (since 2026-08-21), its animation
re-baked into that local space rather than stripped: whatever was animated out
in the world survives, at the price of the offset fields staying inert until
someone deletes those keys. `weapon_r` rides through the whole round trip —
the constraint targets the node, not the path.

**Add Aim** puts OverRig's aim on the weapon with both locators placed for
you — the thing the native button leaves to hand-dragging. Design:
`docs/superpowers/specs/2026-08-17-weapon-aim-design.md`, proof:
`docs/superpowers/plans/verify_weapon_aim.py` (**the button is confirmed
working in the live scene by the user; the verify script's ten gates have not
been run through the bridge yet** — Maya's idle queue was blocked when it was
first sent, see bridge note 6).
`maya_scenesetup/aim.py` + `maya_overrig/aimrig.py`. Works wherever the
weapon is, in the hand or out in world after Connect — the user's call, the
button does not check.

**The locators are placed from the model's own measured extents, never from an
axis convention.** The longest local axis is the blade; its **signed** further
end is the tip, because the origin sits in the grip and a model authored down
−Y must work with no special case. Measured on the real LongSword through the
port: blade on **Y with the tip at +115.925**, crossguard on X (±15.576),
thickness on Z (±1.570). `_top` goes at `tip * 1.15`; `_side` on the
second-longest axis at the **same distance**, positive on a tie — and a blade
is symmetric across its width, so the tie is the normal case, which is why
ties break by axis order rather than by sort luck.

That is correct even though OverRig hardcodes `aimVector 1 0 0`: the constraint
is built with `-mo`, so the direction that tracks the target afterwards is
whichever pointed at it when the offset was measured — the blade, not local
+X. Placing by geometry is what makes the aim intuitive, not a workaround.
Placing along local +X would aim 90° off the blade on this model. Two
caveats: the aim is set up **against the pose on the current frame**, and a
model with no mesh points (or a zero blade extent) is refused rather than
given an invented distance.

**The aim goes on the GEOMETRY** — `attach.model_root`, the
same node Connect hangs the IK hands on. The animator grabs the geometry
(trap 34), the hands then follow the aim for free, and the grip offsets stay
writable because `setAttr` into a constrained channel raises. Honest side
effect, and the status line says it: once the aim exists the weapon's
**Rotate has no visible effect** (the constraint fixes the geometry's world
orientation), while Translate still works.

**The aim has a manifest of its own**, built like the limb and chain
manifests — a UUID diff of the whole scene across the build, minus
animCurves. Nothing smaller works: OverRig's aim leaves a constraint node
parented under the source, and a manifest from `OverRig_knots` would record
only the locators and leave that constraint live, driven by nothing (traps 3
and 4). The set is `RigPicker_aim_<key>` but is **never** found by that name
(Maya uniquifies; two characters can hold the same sword) — discovery is by
prefix, and identity comes from two string attributes: `rigPickerSource`
(one UUID, the node the bake lands on) and `rigPickerHandles` (UUIDs whose
selection means this aim - the geometry and the marked weapon, deduplicated to one when they are the same node). **Neither is a
member**, because members get deleted and the sword must not.

**Bake+Delete in the picker resolves it by EXACT match**, after normalising a
selected shape to its transform. Deliberately no descendant walk: after
Connect the IK hand controls are DAG children of the sword geometry, so
"descendant of the source" would resolve a hand-control click into the aim —
trap 9 and trap 34 from a third side. The safe direction of failure here is
"nothing happens", not "the wrong rig comes apart". The bake order is
bake-while-the-constraint-still-drives, strip the constraint channels, delete
the members, then delete the set only if it still exists (trap 18). A source
someone deleted by hand still gets its orphaned locators cleaned up. The
button no longer needs a bound skeleton when only an aim is selected.

Two guards, and the split is measured rather than assumed: the aim **build**
is not gated on the time-slider highlight, because its bake reads
`playbackOptions -ast/-aet` and never `timeControl -q -ra`; the aim **bake**
is, because `apply_Fast_Bake` is one of the nineteen that do (trap 36).
`overrig.mel_gate()` now holds both guards for every MEL entry point in the
repo; `fkcontrols._mel_gate` is a delegating alias. A second Aim press
refuses; **Add refuses while an aim exists**, since it deletes the weapon
whole and would leave two locators driving a deleted node.

Offsets are the weapon's own local rotate/translate, written with **autoKey off**
(trap 14), read back from the scene on open, on Add and on switching the
dropdown, and remembered per weapon in an optionVar
(`mayaWeapons_offset_<key>`) so a grip dialled in once survives the session.
Scale is a catalog field, not a UI control: a model that arrives at the wrong
size is a fact about the model. Deleting a weapon leaves its shading nodes
behind, as any Maya delete does — chasing them is how a tool eventually
deletes something the animator wanted.

32. **Zeroing `translate` and `rotate` does NOT put a node on its parent.**
    `cmds.group` takes the pivot of what it groups — 42.4 up the sword — and
    `cmds.parent` compensates for that pivot in `rotatePivotTranslate`. The
    carrier then read translate 0, rotate 0, and hung **28.5 cm** off the hand,
    which looks exactly like a wrong bone or a bad import. The local matrix is
    the thing to check, not the two obvious channels: `attach.seat` zeroes
    `shear`, both pivots, both pivot translates and `rotateAxis` as well, and
    the fallback group is built empty and filled rather than grouped around
    the model. Live: worst world-matrix element 28.5130917 → 0.0000000.
    **Still live in 2026-08-20's shape**, where the carrier is gone and the
    MESH is what gets parented: `cmds.parent` compensates the mesh's own pivot
    into `rotatePivotTranslate` exactly the same way, so `seat` is what puts
    the sword in the hand rather than 28 cm beside it.
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
    claim the feature makes. Since 2026-08-20 there is usually **no group at
    all** — the marked node is the mesh — so the sibling relationship this
    trap is about cannot form; it still can on a file holding two meshes,
    which is why `model_root` stays and why Connect still goes through it.

## `root_offset_batch_tool` — batch root-motion offsets (lives in Perforce)

Not in this repo: `C:/!!!Work/Perforce/Atone/Scripts/Maya/root_offset_batch_tool.py`,
because that folder is what the animator has on `sys.path`. A single-file
`cmds`-only window — pick a source folder, move FBXs into a process list, pick
an axis/distance/frame window, GO — importing each clip, splicing a straight
root offset into the window and exporting to another folder. Design:
`docs/superpowers/specs/2026-08-20-root-offset-splice-design.md`, proof:
`docs/superpowers/plans/verify_root_offset_batch.py` (**35/35 green**).

```python
import sys; sys.path.append(r"C:/!!!Work/Perforce/Atone/Scripts/Maya")
import root_offset_batch_tool; root_offset_batch_tool.show()
```

**It is a splice, not a wipe** (the animator's rule, 2026-08-20: «отработать
только в указанном промежутке, а всю остальную анимацию сохранить как есть»).
Before the window: untouched. Inside: the straight offset. After: kept, and
shifted by `(base + distance) - old_end` so the original motion continues from
where the offset stopped instead of teleporting back. Everything else on the
root — rotate, scale and the 135 UE curves — is never touched (trap 40).
`setKeyframe -insert` is what makes the outside survive: it plants the two edge
keys without changing the curve's shape, and only the tangents facing INTO the
window are dictated, after unlocking the in/out pair. Worst error outside the
window: 0.000000000.

Its proof runs in **its own mayapy session**, never through the bridge: the
tool starts every file with `cmds.file(new=True, force=True)`, so a bridge run
would discard the animator's open scene. That also means the UI cannot be
tested there — `cmds.window()` returns `False` in batch — so the panel is the
one part that needs a live open to confirm.

Four things it now defends against, each measured: the export range is the
UNION of the clip and the window (trap 38, the reported bug — «клип
обрезается»); the FBX import mode is set explicitly, since `exmerge` left by
`maya_uebridge` makes the importer create nothing and every file dies with "no
root joint found" (trap 33); the scene adopts the clip's frame rate (trap 39);
and the root is resolved among joints with no joint above them, since a stray
top-level `ik_hand_root` used to outrank a whole `pelvis` skeleton. Two data
hazards closed as well: GO asks once before discarding a modified scene, and an
empty name suffix pointed at the source folder is refused (`clip.FBX` and
`clip.fbx` are one file on Windows).

## `maya_anim_batch_export` — a folder of clips, one camera placement

Root-level standalone (`cmds` only, no Qt, no package), window **Anim Batch
Export Tool**: pick an input folder and every `.ma`/`.mb`/`.fbx` in it is
opened, put through a few operations and re-exported into an output folder.
The operations are the `camera_root` placement, Clean scene (delete everything
outside the `root` hierarchy, strip namespaces), Snap root keys to whole
frames, and an optional bake on export; the timeline is set from the `root`
hierarchy's own key range **last**, after everything that could move it.

```python
import sys, importlib
_p = "C:/!!!Work/MayaScripts"
if _p not in sys.path:
    sys.path.insert(0, _p)
import maya_anim_batch_export
importlib.reload(maya_anim_batch_export)
```

The `reload` is not developer convenience: the module ends with a module-level
`show_ui()` call, so a second plain `import` finds it in `sys.modules` and no
window opens.

**`camera_root` goes to a typed XYZ vector** (2026-09-02, the animator's ask:
«не по одной оси а мог ставить кость в указаный вектор по 3 координатам»).
`op_set_camera_position(position)` deletes every animCurve on `camera_root`
and writes all three coordinates in `objectSpace` — the numbers are
translateX/Y/Z as the Channel Box shows them, so copying a placement out of an
open scene is a matter of reading three numbers off the screen. Nothing is
read out of the clip any more, which retires the read-before-delete ordering
bug commit `1e01e4f` existed to fix. The predecessor typed one axis and
inherited the other two from the file. No per-axis toggles and no "pick from
scene" button — both offered and declined; the curve deletion stays total
(rotation and scale go with translation), which is the tool's own long-
standing behaviour. Spec:
`docs/superpowers/specs/2026-09-02-camera-root-vector-design.md`.

**Trap 33 bit this tool too, and it cost a whole live run** (2026-09-02).
The FBX import MODE is one global setting for the entire Maya session,
`cmds.file(open=True)` inherits it, and any import from Unreal leaves it on
`exmerge` — where the importer matches names against what is already in the
scene and creates **nothing**. Measured: a clip opens with **0 joints** under
`exmerge` against 94 under `add` or `merge`. So the batch cleaned, placed and
exported an *empty scene* over all fourteen files — **8 KB each, holding the
four default cameras and nothing else** — counted every one as a success, and
the only symptom the animator had was «открываю fbx файл а он пустой».
`open_file` now sets the mode and puts back whatever it found (the animator is
working in that session), and `export_file` **refuses a scene with no `root`**
instead of writing 8 KB of nothing, with `run_on_folder` counting the refusal
as a failure. Both halves were needed: the mode is why the files were empty,
the missing guard is why nobody was told.

**Its proof runs in its own mayapy session, never through the bridge** — the
tool starts every file with `cmds.file(new=True, force=True)`, so a bridge run
would discard the animator's open scene. Same rule and same reason as
`root_offset_batch_tool`. `verify_anim_batch_camera.py` — **green 2026-09-02,
0 of 23 gates failed** — copies two real `AS_DownState_*.FBX` clips into a
temp sandbox, runs the whole batch **under a forced `exmerge`** and measures
the files that land on DISK: 94 joints in each export, the vector exact to
0.000000000 on all three axes, no curve left on `camera_root`, and the `root`
key range unchanged (0..91 and 0..81). Forcing the hostile mode is the point —
a fresh mayapy starts on `merge`, and the first version of this proof passed
while the tool was broken in the animator's session. Its vector has three
distinct non-zero coordinates on purpose, so an axis dropped, transposed or
inherited from the clip cannot pass.

Two measured facts any headless run of this tool needs: in mayapy batch
`cmds.window()` returns `False` while `columnLayout`/`checkBox` still succeed,
and **every UI query answers `False`** — so `get_ui_settings()` hands back a
dict of `False`, and a headless run must build the settings dict by hand and
call `run_on_folder(settings)`, never `run_tool()`.

## `maya_overshoot` — the stop of a move, on any pose

Root-level standalone tool, rewritten 2026-08-20; it had come in with the
initial commit and never been touched, and the animator's verdict on the
original was *"качество какое-то плохое, пользовался только Spring"*. Design:
`docs/superpowers/specs/2026-08-20-overshoot-redesign-design.md`, proof:
`docs/superpowers/plans/verify_overshoot.py`. **68 unit tests green; the live
gates have NOT run** — see the status note at the end.

**The pose key stays exactly where the animator put it.** Everything the tool
writes starts at the pose key and comes back to it — *"наш скрипт должен
достроить овершут, то есть тип остановки предмета... анимация должна начаться с
того места, где был последний ключ"*. That is the animator's requirement,
restated after a version that did the opposite was built and rejected on sight
(*"работает совершенно не так как раньше и совсем не правильно"*). **Do not
"fix" this into moving the pose.** The rejected design and the real tension
behind it are written up in the spec, because the tension is genuine and the
argument for the other side is good: an eased arrival has no momentum left at
the pose to continue, and none can be invented — arriving on the move's peak
speed for even three frames means being **51 units of a 100-unit move behind**
where the animator put the object. The discontinuity at the pose is therefore
inherent to this concept, and the tool's job is to make it *mean* something
rather than to remove it.

**The speed comes from the two keys of the move**, `|Δ| / (T - T_prev)`. The
original measured a one-frame difference *at the pose key* — the one place an
eased arrival has no speed — so the harder the animator sold the stop, the less
overshoot they got, and at 60 fps everything halved. This was the animator's
own prescription and it is the fix that matters most.

**One quantity is held fixed and everything else is derived from it:**

```
entry = f'(0) of the unit-peak shape     (πc/peak for the sinusoid, 4/d for an arc)
A     = strength · speed · N / entry
slope = A · entry / N  ==  strength · speed
```

So at strength 1.0 the curve leaves the pose at **exactly the speed the move
arrived with** — it reads as the motion carrying through instead of a fresh kick
out of nothing. That identity is the design in one line, and gate 2 measures it.

**The shapes are keyed at their crests, not sampled.** `raw(u) = sin(πcu)e^{-ku}`
with `k = -c·ln r`: `raw' = 0` gives `tan(πcu) = πc/k`, so the crests are
`atan(πc/k)/(πc) + i/c` — one half period apart — and being `1/c` apart makes
each crest exactly `r` times the last. So the tool writes the pose key, one key
per crest with **flat** tangents (a crest has zero velocity; flat is correct, not
a compromise), and the landing: **4-8 editable keys** where the original wrote
one on every frame, up to 120 per channel. Bounce is the same with gravity — the
object thrown off the pose, keeping `e` of its speed and `e²` of its height per
contact, so the arcs shorten geometrically; contacts get **linear** tangents to
keep the corner. Equal contact intervals are the one thing that stops a bounce
reading as a bounce, and that is what the original had.

**`frames` belongs to the preset** (Snap 5, Spring 12, Elastic 16, Recoil 8,
Bounce 7). With the exit speed fixed, the excursion is set by how long the settle
lasts, so one slow swing travels furthest: at Spring's 12 frames Snap's overshoot
is three times Spring's. Those five lengths put every preset in the same size
range for the same move. A type button loads its whole preset into the panel and
applies; *Apply, keep my numbers* in Advanced re-runs the same shape with
whatever was changed since.

**The pose key's out-tangent is calibrated against the curve, never assumed.**
Maya's `keyTangent -outAngle` is in degrees against an internal time unit that
is not the scene's frame, and the exit slope is the whole feature, so guessing
was not an option. `set_out_slope` sets a **linear** out-tangent — which aims at
the next key, whose secant is known exactly — queries the angle Maya reports for
it, and that one number calibrates degrees-per-unit-per-frame for that very
curve. No temp nodes, no assumption, correct at any frame rate. The fallback if
it ever fails is plain linear, which is about half the intended slope: a soft
failure, and the verify script recognises both failure modes by number.

**Additive layer, not override** (`<obj>_overshoot_pos` / `_rot`), which deletes
a whole bug class: the original animated the override layer's *weight* to stop it
swallowing the animation, stepping it to 1 at the LAST key over all channels of
the group — so any channel that ended earlier had its overshoot silently
multiplied by zero. An additive layer with no keys is zero offset, so there is
nothing to gate, and the weight becomes a live strength dial. Re-applying clears
only the window it is about to write. A *Bake into curves* checkbox writes the
same plan into the base curves instead (identical modulo `P`) and needs no
anim-layer semantics at all, which is why both exist.

**Where it lands with no keys selected: the LAST key of the channel**, unless
the cursor stands exactly on a key, which names that pose (`auto_poses`, with
the last key riding as fallback so a pass-through under the cursor falls
through to the end). The first shipped rule — "the key at or before the
cursor" — resolved a mid-move cursor onto a pass-through key and refused,
correctly and unhelpfully («написано что нечего овершутить хотя на объекте
кубике есть ключи»). Selected keys still win over everything and carry both a
time and a channel.

Refusals, all named in the status line: no previous key, no move, **a
pass-through key** (the next segment continues the same way — an excursion there
is a wobble in the middle of a move), no room before the next key, and an
excursion wider than twice the move is clamped rather than written.

**Three Maya facts this tool paid to learn (all measured live, out_11):**
`cmds.setKeyframe(..., animLayer=L, value=v)` takes `v` as the plug's FINAL
value and writes `v - base` onto the layer curve — a probe key of 0.0 at a pose
worth 100 briefly held −100 and was the original "объект улетает" bug. Writing
with `setKeyframe(curveNode, time=, value=)` straight onto the layer's own
animCurve (found via `animLayer -q -findCurveForPlug`) lands the value
verbatim, which is why `write_layer_keys` goes through the curve node. And a
`getAttr(plug, time=)` straight after a write returns a STALE value (trap 14
without a time change): the pose-drift guard once read a phantom 100-unit
drift from its own already-deleted probe key and deleted a perfectly good
write — the tool "не анимирует" while writing correct keys. `cmds.dgdirty(plug)`
before the guard reads is the fix.

Status: 787 unit tests green; the write path, the layer semantics and the
guard are proved live through the bridge (out_11); the full 13-gate
`verify_overshoot.py` has still never completed — the bridge died to trap 8
(a SystemExit runner template predating note 8 was reused) before it could
run, and only a Maya restart revives the port. Run it at the next natural
restart.

## `maya_skelfit` — a Manny-schema skeleton fitted to a humanoid mesh, and the skin

Root-level standalone (2026-08-27), driven by the project skill
**`.claude/skills/manny-skeleton/SKILL.md`** — the user activates it when a
character needs a skeleton and a skin; the skill is the workflow (probe →
build → placement checkpoint with screenshots → user drags joints →
finalize → voxel bind → pose-test checkpoint), the tool is the math. Design:
`docs/superpowers/specs/2026-08-27-skeleton-skin-skill-design.md`. Proof:
`docs/superpowers/plans/verify_skelfit.py` — **green live 2026-08-27, 0 of
21 gates failed** in the Manny-mesh scene (identity fit worst 0.037 cm,
symmetry exact, orientations worst 0.048°, weights sum 1.000000000,
lone-elbow isolation 0.000000, finalize mirroring a dragged hand to
0.000000). **Its cleanup deletes the skeleton and rebuilds — never run it
after the user has adjusted joints.**

```python
import sys; sys.path.append(r"C:/!!!Work/MayaScripts")
import maya_skelfit
maya_skelfit.build()      # fit + create, refuses over existing joints
maya_skelfit.finalize()   # mirror the user-edited side, re-solve orients
maya_skelfit.bind()       # geodesic voxel skin
```

**The template is measured, never assumed**:
`assets/manny_skeleton_template.json`, extracted from the shipped
`assets/Manny_Skeleton.ma` by `assets/make_skeleton_template.py` (mayapy;
IMPORTS the scene — import never executes script nodes). 93 joints;
`jointOrient` non-zero only on `root`, `rotateAxis` zero everywhere, bind
orientation in the ROTATE channels (the CLAUDE.md fact, confirmed by
extraction), rotateOrder xyz and ssc off on all 93. Landmarks (ground,
height, arm tips) are computed from Manny's own mesh by the SAME
`mesh_landmarks` the fit applies to a target mesh, so the identity case is
exact by construction. Facts that cost a debugging round each: **Manny's
own skeleton is asymmetric** (calves differ by 0.068 cm — symmetrize
splits the difference, tests compare with delta 0.05); **`weapon_l/r` are
deliberately asymmetric** attachment points (never symmetrized);
**`ik_hand_gun` has no side suffix and sits on the RIGHT hand** — the ik
helpers are followers snapped onto their targets (`IK_FOLLOWS`, measured
6e-6 off their targets in the template), and a midline rule would have
pinned it to x=0.

**The skin rides the twist bones.** Measured on Manny's own skin:
`thigh_l/r`, `upperarm_l/r` and `spine_05` carry ZERO weight — those
segments deform through their twist children — and the true per-vertex
maximum is 8 influences while the skinCluster's `maxInfluences` attr
claims 5 (the attr lies). `bind_influences` therefore hands the voxel
bind the template's **weighted** list (74 of 93): `ik_foot_l` stands
exactly on the foot and would steal its weights, and weighting `upperarm`
instead of its twists would break what the twist rig and every UE clip
assume.

**Binding is two commands, and the second needs a GPU.**
`skinCluster(bindMethod=3)` alone leaves closest-distance weights; the
voxel weighting is `geomBind -bm 3 -gvp 256 true`, which fails in batch
mayapy with "Unable to create an offscreen OpenGL buffer" (measured). A
geomBind failure is reported loudly by `bind()` — fallback weights on the
mesh must never pass as voxel-bound.

**The orientation solver is hierarchical**: a joint inherits its parent's
full swing and adds only the minimal aim correction, so a subtree swung
without roll about its root bone (the fit's own arm re-aim, a user
dragging a hand) keeps its template LOCAL channels exactly; leaves and
zero-length bones inherit the swing whole; `root` keeps its channels
verbatim and is never re-aimed. Trap 31 in full form here: the template
stores unwound eulers (428° on ik_hand_gun) AND alternate euler triples
(pelvis reads (x,y,z) vs (x±180, −y±180, z±180)) — every test compares
composed rotations, never channel values.

The fit itself is deliberately modest: uniform height scale about the
ground plane, each arm chain rigidly swung about its shoulder toward the
measured arm tip (centroid of the vertices within 2% of the x-span of the
side's extreme — assumes the widest point per side IS the arm, so
pauldrons/shields mislead it and the placement checkpoint is the
corrective), exact symmetrization. Everything else lands proportionally
and the user's adjustment pass fixes the rest — that was the user's
chosen workflow («авто + моя правка»). `finalize()` detects the edited
side against a snapshot stored on `root.skelfitReference` at build time,
mirrors it, pins template-midline joints to x=0, cuts accidental autoKey
keys (pre-bind, keys on the skeleton are noise), and re-solves every
orientation. **Placement is final once the skin is on** — a post-bind fix
is unbind → adjust → finalize → re-bind, which the skill spells out.

Not built (v1, deliberate): FBX skeletal-mesh export to UE, copy-weights
from Manny as an alternative first pass, leg re-aim, weight-painting UI.
Test scene note: the animator's test mesh `Skin_3p` IS Manny's own body
mesh (48705 verts), which is what makes the identity gates exact.

## `maya_meltmorph` — one mesh flowing into another, baked to Alembic

Root-level standalone (2026-08-31), driven by the project skill
**`.claude/skills/melt-morph/SKILL.md`**. Built for
`AS_TechLimb_MeltMorph_1P_01.ma`: a first-person techno-limb flowing into a
crossbow as a wave from the fingers to the elbow over 20 frames. Design:
`docs/superpowers/specs/2026-08-31-melt-morph-design.md`.

```python
import sys; sys.path.append(r"C:/!!!Work/MayaScripts")
import maya_meltmorph as mm
mm.probe()                          # read-only; BORDER EDGES is the headline
mm.prepare(shape)                   # hidden closed duplicate, polyCloseBorder
mm.build(source, target, axis="z", start="max")
mm.calibrate()                      # the part of the sweep that isn't dead
mm.key_range(0, 20)
mm.bake(0, 20)                      # versioned alembic + gpu cache, verified
```

**It is a level-set blend, not a morph.** Two `mesh_to_level_set` into
`merge_volumes` in `AlphaBlendLevelSet` mode (`level_set_mode = 3`), whose
`alpha` takes a **field**: `plane_field(normal=axis)` → `scale_field(W on that
axis)` gives `(p·n − F)/W`, so 0 at the front and 1 one band-width behind it.
Topology changes freely every frame — that is what reads as liquid, and it is
why blendshapes are out (a fixed-topology route was built and measured; it
crumples wherever a feature TRAVELS across the surface, see the spec).
`scale_field` DIVIDES, so the plane sits at `(F − W/2)/W` — hence `set_front()`
rather than writing the attribute by hand. The front is a published float3
input, so retiming the melt is retiming one animCurve on
`meltGraphShape.front_pos.z`.

**Live-verified 2026-08-31**: the module rebuilt the hand-authored graph and
reproduced it exactly — frame 0 at 24068 verts / area 1473.408 (pure arm) and
frame 20 at 23680 / 1452.721 (pure ballista), both MATCH, with every frame in
between changing. `calibrate()` independently found the live window
86.14 → 26.56 where the hand-tuned guess had been 88 → 30. The Alembic is
lossless: identical counts on all 21 frames, areas to three decimals, worst
closest-point distance **0.000000000**.

Decisions and traps, each paid for:

- **Open meshes are closed in Maya, never bridged by `min_hole_radius`.** Both
  sources were open (1226 border edges on the hand, 296 on the ballista) and a
  solid voxelisation of an open mesh leaks and returns NOTHING. `min_hole_radius
  = 6` did close the hand into one clean shell — and **welded the fingers into a
  mitten**, because a radius that caps a sleeve also caps finger gaps.
  `prepare()` runs `polyCloseBorder` on a hidden duplicate (1226 → 0, one face
  per loop) and the voxeliser runs at radius 0.
- **Keep the closing and smoothing small.** `iterations 2 × deviation 3`
  (0.9 cm at a 0.3 cm voxel) turned the fist into a smooth club; 1 × 1 keeps the
  knuckles. `smooth_deviation` is in VOXELS — world size is `deviation ×
  detail_size`, so 1 is nearly a no-op, which reads as "smoothing does nothing".
- **The sweep must be calibrated.** An SDF alpha blend shows nothing until the
  incoming shape's negative distance beats the outgoing shape's positive one, so
  a naive sweep has dead frames at both ends (measured: 97 → 22 left frames 0–3
  and 18–20 byte-identical). `calibrate()` walks the span and reports the live
  range; `key_range()` defaults to it.
- **The end frame is a SOFTENED target, not the target mesh** — the crossbow's
  spike came ~7 cm short, the limb span ~5 cm. A cut to the real model pops;
  cross-fade 2–3 frames or lower `detail_size`.
- **Never verify a bake vertex-i against vertex-i.** The contour is
  multithreaded and its vertex ORDER is not stable between evaluations: that
  comparison reported 167 cm of error on bit-identical geometry. `bake()`
  compares counts, area, bbox and closest-point distance.
- **Alembics are versioned, never overwritten** (`_v001`, `_v002`, …). Once
  Maya has READ an alembic this session it keeps an internal archive handle and
  `AbcExport` refuses with a bare "Can't write to file" — measured with no
  `AlembicNode`/`gpuCache`/`cacheFile` left in the scene at all, and with plain
  `open(path, "r+b")` from inside that same Maya succeeding. There is nothing to
  delete; a new name sidesteps it.
- **Playback speed cannot be measured over the bridge.** The live graph, the
  Alembic mesh and a GPU cache all timed 0.35–0.38 s/frame — and so did an
  **empty viewport**. The floor is the harness (a port round trip plus a forced
  redraw per frame). What baking really buys: no Bifrost dependency, no
  recompute on any edit, no JIT stall on the first frame after a change, and a
  portable file. The lever for real playback weight is `mesh_scale` (mean 47322
  faces/frame at scale 1).

Bifrost scripting facts live in the spec's table — `addNode` spelling, fan-in
child ports, the `volume_to_mesh` node that compiles clean and outputs an empty
mesh, float3 defaults that only take the **brace** form `"{0,0,1}"`. Every one
of them fails silently. The authoritative sources are on disk: port names in
`$BIFROST_LOCATION/resources/<pack>/docs/ENU/*.md`, graph structure in the
shipped example graphs' JSON under `$BIFROST_LOCATION/resources/graphs/*/*.json`.

Not built: a curved or noisy wave front (`fractal_noise_field` + `warp_field`
are the pieces), the cross-fade to the real target, and fixed-topology output
for UE morph targets.

## `install.py` — the SkeldarAnim shelf, drag-and-drop

**`SkeldarAnim/` is the distribution folder** (it was the repo root until
2026-09-01): `make_build.py` zips it, a colleague unzips and drags
`SkeldarAnim/install.py` into an open Maya viewport, and gets a shelf named
**SkeldarAnim** with six buttons — Rig Picker, UE Bridge, Scene Setup,
Overshoot, Hotkeys, and the native OverRig panel. Design:
`docs/superpowers/specs/2026-08-21-installer-design.md` (written when there
were five; the sixth arrived 2026-09-02 with its own spec), proof:
`docs/superpowers/plans/verify_install.py` (**11 gates, 0 failed** in the
live Maya, 2026-08-21: real install, payload exact, five buttons each
opening its window, OverRig dock up, sword resolved from the installed
copy, idempotent re-run, sys.path put back).

A drop copies a **whitelist** (`install.payload()`) into
`<userAppDir>/scripts/SkeldarAnim/` — the three packages,
`maya_overshoot.py`, `icons/`, `assets/`, `overrig/`, plus `install.py`
and `README_INSTALL.txt` so the installed folder can repair itself —
and nothing else: tests, docs, archive and the other root tools stay
home. Since the 2026-09-01 split that whitelist is also just "everything
in the folder", which is the point of the folder; keep it explicit
anyway — `make_build.py` and both installer test suites read it, and a
folder is not a contract. The shelf tab is created through Maya's own `addNewShelfTab` (it
keeps the shelf optionVars consistent) and **never deleted**; an existing
tab only has its buttons replaced, which is what makes a re-drag an
update rather than a duplicate. Button commands are written at install
time with the destination baked in (`install.button_specs(dest)`): the
four Python buttons bootstrap `sys.path` and call the tool's show
function; the fifth replays OverRig's own installer command verbatim —
`source`, `$barnev_OverRig_RotateOrder = 0`, `$path_to_JGLBN =
<dest>/overrig/misc/`, `base_OverRig_scripts(1)` — read out of
`Drag_and_Drop_to_install.mel`, not guessed.

Things that will bite if forgotten:

- **`same_place(src, dest)` guards the copy**: a re-drag of `install.py`
  from the installed folder itself must not `rmtree` the very files it is
  about to copy. Source == destination skips the copy and only rebuilds
  the shelf.
- **An update also purges `sys.modules`** (`install.purge_modules`,
  2026-09-01), and without it half the update does not happen: the files
  on disk are replaced, but a Maya that has already imported the old ones
  keeps them for the rest of the session, so the shelf button goes on
  opening the previous version — the colleague did everything right and
  reports that the update did nothing. Reproduced end to end in mayapy:
  with the old unpacked build loaded, `import maya_scenesetup.window`
  kept answering the August file **even with the new copy first on
  `sys.path`**; the purge drops 20 modules and the same import lands on
  the new one. Package ROOTS go too, not only submodules (CLAUDE.md's own
  test-runner trap, from the other side), the names are derived from
  `payload()` so no second list exists, and `install` itself is excluded —
  it is the module doing the purging. It cannot help a panel that is
  already OPEN, whose widgets hold the old classes; the confirm dialog
  says to close and reopen, and to restart Maya if anything still looks
  old.
- **The shelf needs Maya 2025 or newer, and only for the picker.**
  `picker_view.py`/`picker_window.py` import PySide6/shiboken6 at module
  level, and PySide6 ships with Maya from 2025 (2022–2024 carry PySide2).
  The picker also calls `event.position().toPoint()`, which is Qt6-only,
  so an import shim alone would not be enough. The other five buttons are
  plain `cmds` and MEL and run anywhere: UE Bridge's one Qt use — the
  green row painting in `checkouts.paint_rows` — is inside
  `except Exception: pass` and degrades to uncoloured rows.
  `README_INSTALL.txt` states the requirement.
- **`install(quiet=True)` exists for the bridge**: the normal path ends in
  a `confirmDialog`, and a modal dialog over the command port is a blocked
  idle queue (bridge note 6). Scripted installs must pass `quiet=True`.
- **Shipped-copy-first resolution, legacy path as fallback.** The sword:
  `catalog._sword_path()` takes `<container>/assets/LongSword_02.fbx`
  (two dirnames up from `catalog.py` — true in the repo and the installed
  copy alike), else the old `Animations/Sources` path. OverRig:
  `overrig.mel_path()` walks `overrig.MEL_CANDIDATES` — the shipped
  `<container>/overrig/base_OverRig_scripts.mel` first, the user's
  original install second; `NOT_LOADED_MESSAGE` names both. `MEL_PATH`
  is gone.
- **`overrig/misc/` is empty at the source and load-bearing anyway** —
  OverRig's own button points `$path_to_JGLBN` at it. Git does not track
  empty dirs, hence `overrig/misc/.gitkeep`.
- **OverRig is committed whole** — MEL, manuals, `License.txt`, `icons/`.
  Its license (clause 3) forbids redistribution without the author's
  consent; the user chose to commit it with that on the table (private
  repo, intra-studio hand-off, studio's call). Clause 4 forbids stripping
  proprietary notices, so never trim the folder.
- Icons are 32×32 PNGs drawn by `icons/make_icons.py` (QPainter under
  mayapy, `QT_QPA_PLATFORM=offscreen`); the generator is committed next to
  its output, regenerate and re-commit to restyle. The OverRig button uses
  Barnev's own `base_OverRig.bmp`.

**Never zip the distribution by hand — run `make_build.py`** (2026-09-01;
the two archives that predate it were hand-made from the *installed* copy
and carry `__pycache__/install.cpython-313.pyc` for nothing):

```
& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' make_build.py
```

Writes `SkeldarAnim_<date>.zip` beside the repository folder (`--out`
overrides), one `SkeldarAnim/` directory inside so the instruction stays
"unzip, drag `SkeldarAnim/install.py` into the viewport". Dated, so a
rebuild replaces only today's archive and never an earlier day's. It is a
development tool and is
**not** in the payload. It reads the payload out of the repo's
`SkeldarAnim/` folder and derives the OUTPUT directory from its own
location, not the installer's: `dirname(source_root())` used to be the
repo's parent and after the split would drop the archive inside the
repository. Four things it settles:

- **The composition comes from `install.payload()`**, never a second list
  here. A whitelist that drifts from the installer's reaches a colleague
  as an ImportError days later, pointing at the wrong file entirely.
- **`__pycache__`/`*.pyc` are cut** by the same patterns `copy_payload`
  ignores, and **directory entries are written** so `overrig/misc/`
  survives empty — OverRig's own button points `$path_to_JGLBN` at it.
- **Verification is part of the build**: the finished archive is reopened,
  `testzip()`ed and its entry list compared against a fresh walk of the
  payload. A mismatch **deletes the archive** and raises — a broken build
  must not leave something zip-shaped lying around to be handed off.
- **`BUILD_INFO.txt` rides inside** with the date, branch, commit and a
  named list of uncommitted payload files if any. The two 2026-08-21
  archives are four minutes apart and nothing distinguishes them.

Sizes to expect: **13.8 MB, 62 files** (2026-09-01), against the old
760 KB — `assets/Manny_Skeleton.ma` is 52 MB and mandatory (Add Character
runs on it) and `assets/UE4_Mannequin.fbx` another 1 MB. Tests:
`tests/test_make_build.py` (15, on a fake tree in a temp dir — the real
payload is never zipped to prove a rule about names).

## `maya_hotkeys` — the temporary hotkey map

The sixth shelf button, `Hotkeys` (2026-09-02, the animator's ask: «кнопочка
которая на время активации включала бы временную карту горячих клавишь»).
One press switches Maya to a hotkey set named `SkeldarAnim`; the next press
puts their own set back. Design:
`docs/superpowers/specs/2026-09-02-hotkey-map-design.md`, proof:
`docs/superpowers/plans/verify_hotkeys.py` — **green live 2026-09-02, 0 of
14 gates failed**, including the two that matter most: the fresh set really
inherited its source's sample key (so it IS a copy), and **the shelf
button's own baked command** toggles both ways
(`SkeldarAnim_verify_base → SkeldarAnim → SkeldarAnim_verify_base`) —
everything else called the module directly, and that string is what the
animator's finger travels. The run left the animator's set list and current
set exactly as found.

**The map's contents are the animator's, laid out in Maya's own Hotkey
Editor.** A map file, a panel of ours and a cheat sheet were all offered and
declined, so there is no editor and no map format here. What the module adds
is the switch plus **107 runTimeCommands** worth binding, in the editor's own
category tree (categories nest with a **dot** — measured, Maya ships
`Editors.Time Editor.Clip`).

**The set is created once as a copy of whatever is active** and never
rebuilt: rebuilding would keep the copy in step with the base set and
destroy every key assigned in it. So their Ctrl+Z and Q/W/E/R keep working
and only what they assign is different. **It is sticky by choice** — Maya
saves the active set itself and we do nothing at exit — which is why the
previous set is remembered in the optionVar `skeldarAnimPreviousHotkeySet`
rather than in a module variable: the session that turns the map off is
often not the one that turned it on. Ours is never an answer to "where do I
go back to" (the way out would lead back in) and a deleted memory falls back
to `Maya_Default`. State is read from `hotkeySet -q -current` at **every**
press and never cached — the animator can switch sets by hand between two
presses, the same reason `picker_window._resolution` re-asserts its binding
on every sync.

**Every command's body is a one-liner into a table in the module**
(`maya_hotkeys.run("picker.build")`, preceded by the shelf buttons' own
`sys.path` bootstrap with the path read from `__file__`). Maya SAVES a user
runTimeCommand into `userRunTimeCommands.mel` — measured: `default` comes
back `False` — which is what makes the sticky map fire after a restart
before the button is pressed, and also means a body outlives the plugin. So
the body carries no logic: a stale one still resolves through the current
table, and an unknown key reports itself. `toggle()` **registers first, in
both directions**, so a press that turns the map off also brings the rows
and the baked path into step with what is on disk; the installer registers
nothing.

**Ours are 23 rows, and each one presses a panel button.** Every action of
ours already is one — `picker_window.live_window()` hands back the live
picker and `build_rig()` is the Build button; Scene Setup's and Overshoot's
module-level callbacks read their own windows' controls — so a hotkey
inherits the status line, the refresh and the exception trap for free. With
the panel closed **there is nothing to press**: the command opens it and
says so, rather than re-deriving a character to act on. Two small public
names were added for this: `picker_window.live_window()` (`show_picker`
REPLACES the window, so a caller must be able to tell open from closed) and
`PickerWindow.select_group` (was `_select_group`; it has a second caller
now). `maya_overshoot.WINDOW` is a module constant for the same reason.

**OverRig's are 84 rows** — every one-press procedure in
`overrig/function_for_hotkeys.TXT`, with the author's own arguments and his
headings as the categories, a row per named mode (four for
`set_infinity_graphEditor`, five for `brn_apply_finger_bend_tool`). Each
sources the toolset first (`overrig.ensure_loaded()`, then `mel.eval`) —
without it a keypress in a fresh Maya answers `Cannot find procedure` in the
Script Editor, which is **trap 20 from the hotkey side** — and deliberately
**not** gated on the time-slider highlight the way our own MEL entry points
are (trap 36): `apply_range_Fast_Bake`, `selKeys_by_timerange` and
`double_oscillate_keys` are *about* that range.

**Two procedures are excluded and a gone-test names both:**
`barn_fast_bake_source_obj_and_delete_knots` and its `min_max` twin are the
only ones in the file that ignore the selection and bake-and-delete the
whole scene's knots. One mis-press away is not where they belong; both are
spelled out in the table's comment so a grep for either lands on the
reason. The ones needing real arguments (`execute_overlap_command`, the
motion trail, the ribbon) are registered as their windows instead —
for those, the window IS the one-press command.

Qt lives below four one-line `_*_module()` seams, so the module loads on a
Maya with PySide2 and a plain-Python test can hand in a fake panel. The
button finds itself on the shelf by label (a shelf button's command runs
with no widget context) and lights its background while the map is on;
not finding it skips the paint and still switches. There is deliberately
**no undo chunk** of ours — `rebuild` already builds in one undo step and
OverRig's procedures manage theirs.

Measured facts to not re-derive: `hotkeySet` **needs a UI**
(`RuntimeError: Maya command error` in mayapy), so the set half is
fake-`cmds` tests plus the live script and nothing else; the Hotkey
Editor is opened by the runTimeCommand **`HotkeyPreferencesWindow`** and
its window is named `HotkeyEditor`; `shelfButton` carries
`-enableBackground`/`-backgroundColor`; and `runTimeCommand -e` accepts
`command`, `category`, `label` and `annotation` — which is why
re-registration edits instead of delete-and-recreate, an edit being the
one form that cannot disturb a binding.

Two more, both paid for in the live run. **`cmds.hotkey` reverses its own
flag between reading and writing**: setting a binding is
`hotkey(keyShortcut="F12", name=<nameCommand>)`, but READING one is
`hotkey("F12", query=True, name=True)` — with `keyShortcut=` in query mode
Maya answers `TypeError: Flag 'keyShortcut' must be passed a boolean
argument when query flag is set`, and the key has to go in positionally.
That cost `verify_hotkeys.py` two gates on its first run, and the
keyword form had been introduced *by* a review of the script. And
**`cmds.nameCommand` has no query flag at all** (no `-q` in its synopsis),
so a binding cannot be followed from the key to the command body: the
verify script proves the chain in two halves instead — the key resolves to
our nameCommand, and a runTimeCommand run by its own name reaches `run()`.

A door left open: `hotkeySet` has `-export`/`-import` for `.mhk`, so handing
the finished map to a colleague — the one thing living in prefs costs us —
is one flag each whenever it is asked for.

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
  by the user noticing something on screen. Two more on 2026-09-01: 1205 unit
  tests were green while the FBX name hold was holding one joint out of
  twenty-one, and while a verify script was injecting joints into the
  animator's own skeleton (traps 47 and 48).
- **A verify script runs in the animator's OPEN scene.** Never assume an empty
  one: resolve everything by long path or UUID, register what you create as you
  create it, guard each teardown step on its own, and leave the frame, the
  playback range, autoKey and the selection exactly as you found them. Probe the
  scene state before and after — the only way to know a run was clean is to
  compare.
