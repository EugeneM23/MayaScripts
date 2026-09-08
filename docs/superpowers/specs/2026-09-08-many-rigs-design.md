# Many rigs in one scene, one Retarget button, a smaller shelf

**Date:** 2026-09-08
**Status:** approved by the ask; built the same day (see the verify script)

The animator's ask, 2026-09-08: «Давай уберем с нашей полки оверлапер,
кастомный граф эдитор (уберем не только из полки но и из плагина в целом).
Ретаргет и бейк объединим в один скрипт. Дальше давай сделаем так чтобы наша
вся система поддерживала работу с множеством ригов, я должен иметь
возможность добавить в сцену много ригов как через add так и через import».

Four parts. The first three are removals and a merge; the fourth is the
feature, and it changes how every module names the rig.

## 1. Overshoot off the shelf, Curve Overlay out of the plugin

- **Overshoot** goes the way the picker went (2026-09-07): a third flag,
  `skeldar_features.OVERSHOOT = False`, gates its shelf row and its six hotkey
  rows (the window row and the five shapes). `maya_overshoot.py` stays in the
  repo and in the payload; the flag brings it back. The animator's words for
  the picker were «оставь его где-то», and "с полки" is the same shape of ask.
- **Curve Overlay** is removed from the plugin as asked: `maya_curveview/`
  moves to `archive/maya_curveview/` together with its six test modules and
  `verify_curveview.py`, the payload row, the shelf row, the icon and its
  drawer, and the four hotkey rows go. `alt+c` — bound by `DEFAULT_KEYS` since
  2026-09-05 — is given back through `RELEASED_KEYS` on a version bump, only
  while it still holds our command, as the module's own rule says. The
  `archive/README.md` names it and the commit that last shipped it.

## 2. One Retarget button

The shelf loses Bake and keeps **Retarget**, which now does the whole
retarget: `maya_rig_retarget.retarget()`.

```
which rig (below) -> which source (the selection's joints, never the rig's own)
-> the previous take cleared, the rig at build pose (reset_build_pose; still
   posed = refusal by name, as the bridge does)
-> connect -> bake over the clip's keys -> helper bones carried -> camera
   set up -> disconnect
```

One undo chunk. The source skeleton is **kept** — the animator imported it,
and a failed look at the result wants it there to press again; the bridge's
IMPORT deletes its own import as before. A holder already standing on that
rig (an interrupted press, or AdvancedSkeleton's own MoCap Matcher) is baked
rather than refused: one button means "finish the retarget". `bake()`,
`connect()`, `report()`, `disconnect()` stay as module API (the bridge, the
verify scripts); `bake_button` goes, `bake.png` goes.

## 3. Many rigs: a rig is a NAMESPACE

Measured 2026-09-08 in mayapy: `cmds.file(Manny_Rig.ma, i=True,
namespace="Manny_Rig")` lands every one of its 2713 nodes under the
namespace — `Manny_Rig:ControlSet`, `Manny_Rig:Main`, `Manny_Rig:buildPose`,
`Manny_Rig:FKNeck_M`, `Manny_Rig:twistAmountDivideNeckPart1_M`, `|Manny_Rig:root`
— with **zero** stray unnamespaced nodes; a second import into `Manny_Rig1`
does the same; asked for a namespace that exists, Maya makes `Manny_Rig2`
itself. Without a namespace the second rig's `Main`, `FKWrist_R` and
`ControlSet` are ambiguous or renamed (the 2026-09-07 note), and every
lookup in both retarget modules is by those names.

So **Add Character imports a rig into its own namespace** (`Manny_Rig`,
`Manny_Rig1`, … through `records.namespace_for`, the clip importer's own
rule), and the message names it. Bare skeletons stay unnamespaced — the
merge-by-name import still exists as an API and needs plain bone names.

**A rig the animator already has in the ROOT namespace keeps working**: it
is the rig whose namespace is `""`. Every existing scene holds one.

### `maya_rigs.py` — which rig

One new module (cmds + pure halves), the one place the question is asked:

- `Rig(namespace, control_set, main, group, skeleton_root)`; `rigs()` finds
  every objectSet whose leaf is `ControlSet` with a `Main` beside it in the
  same namespace; the group is `Main`'s top ancestor; the skeleton root is
  the shallowest joint of that namespace carrying a constraint and standing
  outside the group (both retarget modules' own rule, per namespace).
- `node(rig, leaf)` → `ns:leaf`, or `leaf` for the root-namespace rig.
- `rig_of(path, rigs)` (pure): a path in a rig's (non-empty) namespace is
  that rig's; a path under a root-namespace rig's group or skeleton is
  that rig's; a mesh of a namespaced rig therefore counts, as it should.
- `choose_rig(selected, all)` (pure): the selection's one rig, else the
  sole rig, else none — and the refusal names the rigs
  («select any control of the rig you mean: Manny_Rig, Manny_Rig1»). Two
  rigs selected is no answer.
- `current_rig()` asks the scene and lets `choose_rig` decide.

`maya_scenesetup.skeleton.current_root` is rewritten on it: selection
(a rig's node → its skeleton root; a joint → its top joint) → the sole rig's
skeleton → the sole bare skeleton → none. Scene roots exclude every rig's
group (deformation joints).

### The retarget modules take a rig

Every scene function in `maya_asretarget` and `maya_pmretarget` gains
`rig` (a `Rig`; `None` means `current_rig()`), and every rig node name goes
through `node(rig, leaf)`: the controls, `ControlSet`, the neck knobs, the
FKX joints, and **the holder** — `ns:MoCapConstraints`, one per rig, so two
rigs can be connected at once and each Bake walks its own. The helper nodes
(`asrtDriver_*`, `pmrtScale`, `pmrtPole_*`) are created in the rig's
namespace too, or the second rig's `pmrtScale` finds the first's.
`foreign_constraints` compares against the rig's own group, not `|Group|`.
The pure halves (`drive_plan`, `alignments`, `parent_offsets`, …) do not
change: a `Drive` keeps its plain control name and the scene name is looked
up at the point of use. The two modules stay independent copies; both
import `maya_rigs`, which imports neither.

`maya_rig_retarget.rig_module(rig)` picks the module by the rig's own
skeleton names as before; `resolve()` → `(rig, module, refusal)`.

### The bridge: three import modes

`IMPORT` radio: **retarget onto the rig** (the selected rig, else the only
one — and a rig is ADDED when the scene has none, as before), **onto a NEW
rig** (always adds one, then retargets onto it — this is "many rigs through
import"), **as a new skeleton** (unchanged). Two rigs and nothing selected
is the refusal above, before anything is exported or imported.

### Export strips the namespace

Measured: the FBX exporter writes `rigns:root`, `rigns:pelvis` — the
namespace goes into the file, and there is no strip flag
(`FBXExportStripNamespace` does not exist). Unreal would receive bones a UE
skeleton does not have. So `animimport.target_root_plain` grows into
`target_plain_names`: for the length of the export every joint of the
target wears its leaf name in the root namespace (`cmds.rename(path,
":leaf")`, measured to move a node into the root namespace and back), with
the root's collision handled exactly as before (other plain skeletons held
aside, the name Maya actually gave checked). Restored by UUID in a
`finally`, ours first.

### Per-rig camera and weapon

`camera.setup(bone)` names its camera in the bone's namespace
(`Manny_Rig1:SceneSetup_camera`) and `teardown(bone)` removes only the
camera constrained to THIS bone (`camera_for`), never "any of ours" — two
rigs mean two cameras. The weapon already works per resolved root
(`skeleton.resolve_bone` inside the subtree) and needs nothing.

### Add Character selects the new rig

After a rig import its `Main` is selected, so the rig just added is the one
the next press acts on — "add it" and "work on it" stay one press without
the picker's Connect. Bare skeletons are not selected (unchanged).

## Not built

Deleting a rig; retargeting one clip onto several rigs at once; a rig
dropdown anywhere (the selection is the dropdown, as Connect was).

## Proof

`docs/superpowers/plans/verify_many_rigs.py`, mayapy standalone (it adds
rigs and deletes skeletons): two rigs added — one by Add Character, one by
IMPORT «onto a new rig» — a clip retargeted onto each by selection, each
rig's hand on its own reference and the OTHER rig unmoved to 0.000, two
cameras each on its own bone, the export of the second rig re-imported and
found to carry plain bone names, the resolver's refusals by name, and the
one-button Retarget on a hand-imported skeleton.
