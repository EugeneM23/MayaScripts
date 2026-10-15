# Scene tabs, stage 2: the plugin sees only the active tab

2026-10-15, the second half of `2026-10-15-scene-tabs-design.md` (read it first). With
tabs, one Maya scene holds every open tab's characters, each tab in its own namespace and
the inactive ones hidden. The plugin was written for one scene: wherever it falls back on
"the only rig", "the only skeleton", "every joint in the scene" or writes a name in the
root namespace, a hidden tab would take part - «2 rigs in the scene» refusals, Delete or an
export picking a character of another tab, a drop target projected from a hidden rig.

## The rule

**A tab is the scene.** While tabs are on, every plugin question about the scene is asked
of the active tab only; with tabs off nothing changes (the active namespace is `""`, the
identity case - the same shape `maya_rigs.node` already has for the root-namespace rig).

`maya_scenetabs/scope.py` (stdlib + `cmds`, imports nothing else of the plugin):

- `active_namespace()` - the active tab's namespace, `""` when tabs are off (read from the
  session node; cheap; no Qt);
- `in_active(path)` (pure over the namespace) - the node lies in the active tab: its
  namespace is the tab's or nested in it; with tabs off, always True;
- `active_only(paths)` - the filter.

## Where it is applied (the scene readers)

Found by `grep` for scene-wide listings; the plan lists each call site:

- `maya_rigs`: `control_sets`, `character_groups`, the joint walk at `rigs()`'s skeleton
  lookup - so `rigs()`, `choose_rig`, `current_rig`, `rig_of` and everything built on
  them (Retarget, the bridge, Connections, FK/IK, Pose Library, Walk Builder targets, the
  Tools, Camera Setup) see one tab;
- `maya_overrig.active.character_roots`, `builder.character_roots`, `naming`'s and
  `fkrings`' joint walks - the skeleton fallbacks of `skeleton.current_root`;
- `maya_uebridge`: `animimport` (`choose_target_root`, the name hold over "other
  skeletons", which must hold the hidden tabs' plain-named skeletons too - a merge onto
  `root` must not land in another tab), `skeletonimport.bare_roots`, `nativeimport`,
  `formats` (its before/after assemblies diff stays scene-wide - it finds what an import
  made);
- `maya_scenesetup`: `droptarget.snapshot` / `rig_snapshot` / `skeleton_snapshot`,
  `deletion` (owners, garbage components and strangers inside the active tab only),
  `weaponspace` world-level spaces, `colour`'s free-colour scan (per tab: the colours a
  saved tab file carries are its own);
- `maya_asretarget` / `maya_pmretarget` source joint scans, `maya_vpstudio`'s subject,
  `maya_com/network`'s transform walk;
- `maya_share.send_scene`: sends the ACTIVE TAB, written by stage 1's save to a temp path
  (never the session).

## Names written in the root namespace

Every absolute name (`":" + leaf`, `rename(x, ":...")`, `namespace(add/set)`,
`createNode(name=":...")`) is audited - `maya_rigs`, `chargroup`, `camera`, `armor`,
`deletion`, `poselib/apply`, `com/network`, `uebridge/animimport`, `fbxlayout`,
`formats`, `nativeimport`. Each one is either:

- **meant to be the root namespace for the length of one operation** (the FBX export's
  plain bone names, `fbxlayout`'s `Armature`, the root-name hold) - kept, its restore by
  UUID checked under a tab;
- **meant to be "where new things go"** (a character group, a camera, an armor space, a
  CoM group, a namespace for a new rig, a clip's import namespace) - made relative to the
  current namespace, so it lands in the active tab and is saved with it. Add Character
  then makes `<tab>:Manny_Rig`, `<tab>:Manny_Rig_Character`.

## Not built

Carrying a character between tabs by a dedicated command (copy / paste of keys and the
Pose Library already cross tabs, since both act on whatever is shown); a tab-aware
outliner filter beyond stage 1's `hiddenInOutliner`.

## Proof

- Unit tests on `scope` (nested namespaces, tabs off, a namespace that only starts with
  the tab's name - `attack` against `attack_01`).
- `docs/superpowers/plans/verify_tabs_scope.py`, mayapy standalone: a DECOY tab opened
  first and hidden, holding a Manny rig, a Manny UE5 skeleton (plain `root`) and a Creep
  rig; in the active tab the existing proofs re-run through their own functions -
  `verify_rig_pipeline`, `verify_many_rigs`, `verify_character_groups`,
  `verify_delete_character`, `verify_cascadeur_layout` (exports), `verify_clip_labels`,
  `verify_weapon_space` - with two gates added to each: every decoy node unmoved to 0.0
  (world matrices over the take) and untouched (keys, connections, names); and each
  refusal and choice the same as the same verify run with no decoy.
- Live only (the animator's): drags onto the viewport with a hidden tab behind the
  active one.

## Addendum: measured while planning (2026-10-15)

- **Maya resolves a creation or rename name relative to the CURRENT namespace, even when the name carries
  a namespace**, and creates the missing namespaces silently: with `tabx` current, `createNode(name=
  "tabx:Rig:a")` made `tabx:tabx:Rig:a`. Lookups (`ls`, `objExists`) go from the root. So "made relative so
  it lands in the active tab" is two rules, not one: the current namespace is the active tab's (stage 1
  sets it on a switch; every reset to `":"` after an import becomes `scope.enter_active`), and every name that
  carries a namespace is made absolute where a node is created or renamed with it (`scope.as_created`; a
  name given back after a hold, `scope.root_name`). A leaf (`hand_r_weaponSpace`, `<leaf>_knot`) stays
  relative and lands in the tab. A node made with `":A:x"` is answered as `"A:x"`.
- **Stage 1 alone breaks the plugin inside a tab** (Task 1's measurement): the retarget's holder
  `tab_plain:Manny_Rig:MoCapConstraints` was created as `tab_plain:tab_plain:Manny_Rig:MoCapConstraints` and
  the next `setAttr` found nothing. The two stages ship together.
- **Sites the main text did not list**, each with an edit: the namespace resets after an import
  (`animimport`, `formats`, `deletion`); a clip's namespace made at the root whatever is current
  (`animimport` already set `":"` first; `formats._in_namespace` adds `":" + name`); `character.
  existing_namespaces` (a new character's namespace is taken in the tab, a clip's at the root: both must be
  free); `choose_target_root(home=)` (inside a tab every node carries its namespace: `tab_x:root` is plain);
  Add Character qualifying the namespace its import made; the armor piece's namespace taken off in the tab;
  the Pose Library's rebuilt skeleton moved under the tab; Shared and Stash - a scene received opens as a tab,
  an FBX imports into one (`home_namespace`), a copy sent is the active tab alone with its references written
  in (`saving.save_tab(preserve_references=False)` through `scope.export_scene`); Open scene (a portrait's or
  a weapon's file) opens a tab; the scene's name (Shared, Stash, the Pose Library's capture, the clip label,
  Walk Builder) is the active tab's file; and the names a message or a label shows (`equip` / `armor`'s
  character, the clip label's clip, a character group's base) are read with the tab's prefix taken off
  (`scope.local`, `scope.relative`) - "the outermost namespace" was the tab.
- **Viewport Studio**: each tab has its own studio (built in the tab by its plain names, found there).
- **The proof** is one script with independent sections, not the seven verifies re-run inside a tab (each of
  them opens or news scenes itself): a decoy tab holding a keyed Manny rig, a Manny UE5 skeleton and a UE4
  Mannequin skeleton (untextured, so it wears the palette's red - Manny and the Creep are textured since
  2026-09-30 and wear none), the work in another tab (questions, Add Character, a retarget with its camera,
  an export read back, a weapon, Delete, a clip kept, a save, Shared's copy), the decoy checked untouched
  and no stray or doubled namespace left, and last Open scene on a weapon's FBX opening a tab of its own.
  Not proven headless (the animator's): the drags onto the viewport with a hidden tab behind the active one.
- **Known and stated**: an FBX export from a tab carries the name of a display layer its bones are in with
  the tab's prefix (`tab_plain:DeformationJoints`, the Manny skeleton asset's leftover AdvancedSkeleton
  layer) - a collection, not a bone; read back, every bone is plain. A saved tab file keeps strings that
  once held a node's name (a camera's `imageName` `tab_plain:camera2`): a save renames nodes, not strings.
