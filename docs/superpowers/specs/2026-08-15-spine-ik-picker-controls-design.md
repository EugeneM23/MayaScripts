# Spine IK, controller-only picker, single Build button

Date: 2026-08-15
Status: designed autonomously (user away, "сделай все от и до"); user reviews
the result in the scene afterwards
Branch: `feature/overrig-picker`
Follows: `2026-08-15-switch-fk-ik-design.md`, `2026-08-15-fk-control-axes-design.md`

## Goal

Four requests, one coherent rework:

1. **Spine IK** — the spine can be switched to IK like the limbs. The IK is
   three controllers: top, bottom, centre.
2. **Picker selects controllers, not bones.** Before any build the picker is
   inert; buttons whose controller is absent (limb in IK, chain not built) are
   dimmed and unclickable.
3. **IK controls in the picker** — same logic as FK: present and clickable
   when the control exists, dimmed when it does not.
4. **One Build button** with an `FK Limbs` toggle: off (default) builds a
   hybrid rig — IK arms and legs, FK everything else; on builds full FK.
   `Build FK` disappears.

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Spine IK mechanism | `apply_rebike_3_or_more_object_to_IK` on exactly **(pelvis, spine_03, spine_05)** | "Аналогично тому как мы делали для рук и ног" — the same proc, the same 3-joint form. Its output IS the user's description: `pelvis_IK_strech_gr` (bottom), `spine_03_IK_knee` (centre), `spine_05_IK_feet` (top). The >3 "spider" branch was read in the MEL and rejected: it builds per-vertebra `inner_rotate_ctr` twist controls and unnamed groups — a different tool, not what was asked for. |
| Undriven intermediates | spine_01/02/04 keep their baked animation | Exactly what OverRig gives anyone using the 3-joint IK on a spine by hand. spine_01/02 ride on the pelvis, spine_04 on spine_03. |
| Where spine IK lives | `builder.LIMBS` gains `("spine", ("pelvis", "spine_03", "spine_05"))` | Every generic mechanism — manifest diff, bake, resolve, nesting order, reclaim — works unchanged on a fifth entry. |
| Default IK set | `builder.DEFAULT_IK = ("arm_l", "arm_r", "leg_l", "leg_r")` | Part 4 is explicit: default Build gives FK torso. Spine IK is reached through Switch. |
| Spine switch dependents | FK chains whose root controller sits inside the spine chain's nodes are `apply_Parent_out`-ed, the spine converts, then they are `apply_Parent_in`-ed onto the control now carrying their attach bone | The finger pattern generalised. Neck and FK clavicle chains hang off `spine_05`'s controller, FK thigh chains off the pelvis's. They are DAG children of what gets deleted; anything less loses them. |
| Re-hang targets on an IK spine | attach bone `spine_05` → the `_IK_feet` control; `pelvis` → the `_IK_strech_gr` | `_IK_feet` drives spine_05 directly. The pelvis bone follows the strech group's attach machinery, so controllers hung on the strech group follow the pelvis exactly, and the strech group doubles as the bottom controller. |
| IK control identification | Substring within the limb's manifest members: `_IK_feet` / `_IK_knee` / `_IK_strech_gr`, transform or joint type | The `_ik_hand_control` precedent. Manifest membership first, name second — never a bare scene-wide name. Moves to `builder.ik_control(limb, role)`, roles `end`/`pole`/`base`; `fkcontrols` reuses it. |
| Picker buttons select | FK: `<joint>_FK_ctrl` by name-exists; IK: `builder.ik_control` per button | FK controller names are our own renames and are already trusted by name throughout `fkcontrols` (align, attach, switch). |
| Availability | A button is clickable iff its controller resolves right now; recomputed on every selection sync and after every build/bake/switch | One rule covers all of part 2 and 3: unbuilt picker inert, IK limb dims its FK buttons, missing IK dims its circles. |
| IK buttons on the map | 2 per arm/leg (end + pole, drawn as circles), 3 for the spine (top/mid/bot column left of the spine stack) | Circles vs rounded rects distinguishes IK from FK at a glance. Strech groups of the limbs are not exposed — animators use feet + knee. |
| Bone selection | Removed entirely | Part 2. Group buttons and marquee resolve to available controllers only. |
| Single Build | `fkcontrols.rebuild(scene_map, fk_limbs)`: bake FK back, bake IK back, then build per toggle | Full teardown first makes Build idempotent from any state, including mixed post-Switch states. FK is baked before IK because finger controls can hang inside IK hand controls — the reverse order would delete them with the arm rig. |
| Hybrid build | `build_fk` on root/spine/neck/fingers, then `builder.build(only=DEFAULT_IK)`, then hang each hand's finger chains on that arm's IK end control | Reuses the Switch machinery verbatim. Fingers must follow the IK hand; `apply_Parent_in` re-bakes them into its space. |
| No clavicle/ball controls in hybrid | Accepted | Identical to today's post-Switch IK state. Switching a limb to FK brings them back with the full chain. |
| Toggle | Checkable `FK Limbs` button next to Build; unchecked by default | The user's naming. State is read at press time; no persistence. |

## Architecture

New/changed pieces, respecting the import table:

| Module | Change |
|---|---|
| `bodymap.py` | `IkButton` namedtuple + `IK_BUTTONS` tuple (id, limb, role, x, y, w, h, region), mirrored like the FK side; `group_members` includes IK ids |
| `pickerstate.py` (new, stdlib only) | Pure resolution: given `{joint: path-or-None}` and `{(limb, role): path-or-None}`, produce `{button_id: path}` |
| `picker_view.py` | `ButtonItem` learns a `shape` hint; IK buttons paint as ellipses. No Maya, as before |
| `picker_window.py` | Buttons select controllers via the resolution map; availability refreshed each sync; `Build FK` removed; `FK Limbs` toggle added; Switch accepts spine |
| `builder.py` | Spine in `LIMBS`, `DEFAULT_IK`, `ik_control(limb, role)` |
| `fkcontrols.py` | `SWITCHABLE` = limbs + spine; spine dependents in `switch_limbs`; `rebuild(scene_map, fk_limbs)`; `_ik_hand_control` delegates to `builder.ik_control` |

## Error handling

| Situation | Behaviour |
|---|---|
| Build pressed unbound | Refused, as today |
| Build over any existing state | Torn down (FK first, then IK) inside the same undo chunk, then rebuilt |
| Switch spine with no rig on it | Skipped, named in the report — existing rule |
| Switch a limb to FK while the spine is IK | Chain stays world-space, noted in the status line — existing mixed-state honesty |
| Bake+Delete an IK spine carrying dependent controllers | The existing intruder guard refuses with a message; Switch or a full bake is the route |
| Picker button whose control vanished (manual delete) | Dimmed at the next sync; clicking selects nothing |

## Testing

Pure (mayapy, no scene): spine entry resolves through `limb_joints`;
`DEFAULT_IK` excludes spine; role table; `IK_BUTTONS` geometry, mirroring,
id uniqueness, group membership; `pickerstate` resolution; hybrid chain list;
dependent-chain selection logic; view shape hints.

Live (bridge scripts, run when the port is open):

- `verify_spine_ik.py` — key animation, build spine IK, confirm the three
  controls exist and drive (top moves spine_05, bottom moves pelvis, centre
  bends), zero drift on bake back.
- `verify_hybrid_build.py` — Build (default): 4 IK limbs + FK torso + fingers
  on IK hands; toggle on: full FK; both from dirty mixed states.
- `verify_spine_switch.py` — full FK, switch spine to IK: neck/clavicle/thigh
  controllers survive and follow; switch back: FK restored, zero drift.

## Out of scope

- Neck IK; per-chain FK bake from the UI; docking; mirror-select
- The pose-snapshot safety before Build (still proposed, still unbuilt)
- Coupling a fresh FK limb to an IK spine's controls
- The bind-pose reference for axis alignment (recorded gap, unchanged)
