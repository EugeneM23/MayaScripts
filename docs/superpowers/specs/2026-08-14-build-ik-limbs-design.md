# Build — IK arms and legs via OverRig

Date: 2026-08-14
Status: approved
Branch: `feature/overrig-picker`
Follows: `2026-08-14-overrig-picker-design.md`

## Context

The Rig Picker's `Build` button is currently a disabled stub. This spec fills it
in with the first real rig operation: IK on both arms and both legs of the bound
skeleton, driven through OverRig.

OverRig's `apply_rebike_3_or_more_object_to_IK()` takes no arguments. It reads
the current selection, and with exactly three objects selected it builds an IK
chain and renames the result predictably:

| Created node | Name |
|---|---|
| `$ik_obj[0]` | `<first>_IK_strech_gr` |
| `$ik_obj[1]` | `<third>_IK_feet` |
| `$ik_obj[2]` | `<second>_IK_knee` |

Two preconditions were found by reading the MEL rather than assumed:

- **Selection order matters.** The three joints must be selected root, middle,
  end — `thigh, calf, foot`.
- **The timeline range matters.** The underlying proc reads
  `timeControl -q -ra $gPlayBackSlider` and bakes constraints across that range,
  keying an `attach` attribute at its boundaries when the range spans more than
  one frame. On the working scene the range is 0–30 with no animation, so the
  bake is flat. That is fine for a test build but is not a no-op.

OverRig records what it touches in two object sets: `OverRig_rig_objects` for
source joints and `OverRig_knots` for everything it creates.

## Scope

**In**

- `Build` creates IK on all four limbs, regardless of what is selected in the
  picker or the scene
- Pressing `Build` again tears the previous build down and rebuilds
- Teardown removes only what we created, leaving the user's own OverRig work
  untouched
- The whole operation is a single undo step

**Out**

- `Bake+Delete` stays a disabled stub; teardown here exists only to serve rebuild
- No spine, neck, hands or fingers
- No per-limb selection — the button always does all four
- No FK/IK switching, no pole-vector placement beyond what OverRig produces

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Coverage | All four limbs, independent of selection | Matches the request and keeps the first version simple. Selective building can come once we know what the result looks like. |
| Repeat press | Tear down and rebuild | Chosen by the user over refusing. Makes iterating on the build cheap. |
| What teardown removes | Only nodes this tool created, tracked in our own set | OverRig's own `barn_fast_bake_source_obj_and_delete_knots()` is scene-global: it bakes and deletes *everything* in `OverRig_rig_objects` and `OverRig_knots`. The user works with OverRig by hand, so a global teardown inside our Build would silently destroy their manual setups. Scoping costs about twenty lines. |
| Name resolution | Through the picker's `_scene_map` | The binding work already handles namespaces and prefixes; Build gets that for free and needs no name logic of its own. |
| Undo | One chunk around the whole build | OverRig opens its own chunk per call, so without an outer chunk `Ctrl+Z` would undo one limb of four — a trap. Maya allows the nesting. |

## Architecture

Two new modules, split on where MEL knowledge lives.

| Module | Responsibility | May import |
|---|---|---|
| `overrig.py` | Thin binding to the MEL toolset: check it is sourced, select and call procs, read its sets. No policy. | `maya.cmds`, `maya.mel` |
| `builder.py` | Policy: the limb table, the manifest, build and teardown orchestration | `maya.cmds`, `overrig` |

`picker_window.py` gains only the button wiring and status reporting; it does
not learn anything about OverRig.

### `overrig.py`

```python
MEL_PATH   # path the user's Custom shelf sources; used only as a fallback
KNOT_SET = "OverRig_knots"
SOURCE_SET = "OverRig_rig_objects"

is_loaded() -> bool                      # the IK proc is available
ensure_loaded() -> bool                  # source MEL_PATH if needed
set_members(set_name) -> list[str]       # long paths, [] if the set is absent
build_ik(joint_paths) -> None            # select the three in order, call the proc
fast_bake(objects) -> None
delete_constraint_attributes(objects) -> None
```

`ensure_loaded` never guesses beyond `MEL_PATH`: if the procs are missing and
that file is not there, it reports failure and tells the user to press the
OverRig shelf button, rather than searching the disk.

### `builder.py`

```python
BUILD_SET = "RigPicker_build"

LIMBS = (
    ("arm_l", ("upperarm_l", "lowerarm_l", "hand_l")),
    ("arm_r", ("upperarm_r", "lowerarm_r", "hand_r")),
    ("leg_l", ("thigh_l", "calf_l", "foot_l")),
    ("leg_r", ("thigh_r", "calf_r", "foot_r")),
)

BuildResult = namedtuple("BuildResult", "built skipped created removed message")

limb_joints(scene_map) -> list[(limb, [path, path, path])]   # pure, resolvable limbs only
has_build() -> bool
build(scene_map) -> BuildResult
teardown(scene_map) -> BuildResult
```

`limb_joints` is pure given a mapping, so the limb table and its resolution are
testable without Maya.

## How the manifest works

OverRig does not tell a caller what it just made, so the manifest is built by
difference:

1. Read `OverRig_knots` membership before the limb is built.
2. Build the limb.
3. Read it again; whatever is new belongs to us.
4. Add those nodes to `RigPicker_build`.

Teardown then reverses it, using OverRig's own pieces so its structures are
dismantled the way it expects:

1. Select the twelve source joints and call `apply_Fast_Bake()`.
2. Call `delete_constraint_attributes_on_objects()` on them.
3. Delete the members of `RigPicker_build`, then the set itself.

`has_build()` is simply whether `RigPicker_build` exists and has members.

## Error handling

| Situation | Behaviour |
|---|---|
| Picker not bound to a skeleton | Refuse, status line says to press Connect first |
| OverRig procs unavailable and `MEL_PATH` missing | Refuse, status line names the path and suggests the shelf button |
| A limb's joints missing from the bound skeleton | Skip that limb, build the rest, report which were skipped |
| No limb resolvable at all | Refuse without touching the scene |
| Timeline range is a single frame | Build anyway, warn that the bake has no range to work over |
| A single limb's OverRig call raises | Abort, close the undo chunk, report which limb failed. The chunk means a `Ctrl+Z` still unwinds the partial build. |

## Testing

- `builder.LIMBS` and `limb_joints` — plain Python: twelve distinct joints, three
  per limb, every joint present in the body map, resolution skips limbs with
  missing joints and keeps order.
- `overrig.py` and the orchestration need a live Maya and are covered by a
  verification script driven over the command-port bridge, checking that: four
  limbs build; the expected `_IK_feet` and `_IK_knee` nodes appear with the
  bound skeleton's prefix; `RigPicker_build` holds exactly what was created;
  a second `Build` leaves the same node count rather than doubling it; a manually
  created OverRig knot outside our manifest survives a rebuild; and one `Ctrl+Z`
  removes the whole build.

The "manual knot survives rebuild" check is the one that proves the central
decision, so it is not optional.
