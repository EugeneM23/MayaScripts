# The active character, and the shelf as its own plugin

2026-09-01. Four changes asked for in one sitting, in the order they were
asked:

1. **Isolate the shelf as a separate plugin** — "чтобы ты тут не путался
   куда какие скрипты".
2. **Every rig and skeleton operation acts on the ACTIVE character** — the
   hierarchy the picker is connected to. A scene may hold many characters;
   adding, deleting or changing anything must land on the connected one.
3. **Add Character may run as many times as the animator likes.**
4. **Import and Export look at the SELECTION first**, and fall back to the
   connect. A non-empty bone selection names the skeleton the clip lands
   on, or is exported from; an empty selection means "the connected one".

They are one piece of work because (2) is what makes (3) and (4) safe:
without per-character scoping a second character in the scene turns every
name-based lookup in the rig into a coin flip.

---

## 1. The plugin folder

Everything the animator receives moves into one directory named exactly as
the shelf and the install destination:

```
MayaScripts/                  the workshop -- repo root, not shipped
├── SkeldarAnim/              THE PLUGIN -- this, and only this, ships
│   ├── install.py
│   ├── README_INSTALL.txt
│   ├── maya_overrig/
│   ├── maya_uebridge/
│   ├── maya_scenesetup/
│   ├── maya_overshoot.py
│   ├── icons/
│   ├── assets/
│   └── overrig/
├── make_build.py             dev tool: builds the zip from SkeldarAnim/
├── maya_skelfit.py           the other standalone tools stay at root
├── maya_meltmorph.py
├── ...
├── tests/  docs/  archive/  CLAUDE.md
```

`install.payload()` is unchanged: its names were always relative to
`source_root()`, which is the folder holding `install.py` — now the plugin
folder. The zip's inner directory was already `SkeldarAnim/`, so the
archive comes out byte-for-byte the same shape and the hand-off
instruction ("unzip, drag `SkeldarAnim/install.py` into the viewport") is
unchanged.

**The standalone root tools deliberately stay at the root.** They are not
in the payload and never were; moving them too would break the import
paths written into CLAUDE.md, into both project skills and into a dozen
verify scripts, buying nothing. The confusion the user named is about the
plugin's boundary, and one folder settles it: if it is in `SkeldarAnim/`,
a colleague gets it.

Three consequences, each a real edit:

- **`sys.path` for a dev import is now the plugin folder**:
  `sys.path.append(r"C:/!!!Work/MayaScripts/SkeldarAnim")`. The installed
  copy is untouched — the shelf buttons always bootstrapped their own
  destination.
- **`tests/__init__.py` puts the plugin folder on `sys.path`.** Discovery
  runs with `-t .`, which gives the repo root; the plugin folder is one
  line in the package initialiser, which unittest imports before any test
  module.
- **`make_build.py` keeps writing beside the REPO**, not beside the plugin
  folder. `default_out_dir()` used `dirname(source_root())`, which after
  the move would drop the archive inside the repository. It now derives
  the repo root from its own location.

## 2. The active character

### What breaks with two characters today

Everything the tool creates is found by NAME:

| Lookup | Name | With a second character |
|---|---|---|
| IK limb manifest | `RigPicker_build_arm_l` | Maya uniquifies to `...arm_l1`; `built_limbs()` never sees it |
| FK chain manifest | `RigPicker_fk_spine` | same |
| twist manifest | `RigPicker_twist_arm_l` | same |
| FK controller | `upperarm_l_FK_ctrl` | the second build's is `upperarm_l_FK_ctrl1`; every lookup resolves the FIRST character |

The last row is the dangerous one. `_attach_chain` would couple character
two's spine onto character one's pelvis controller; `bake_selection` would
bake a limb of the wrong character; `align_controllers` would rewrite
somebody else's rotate axes. All silently.

### The fix, in two halves

**Identity by attribute, discovery by prefix.** Exactly the pattern the
aim manifest has used since 2026-08-17 and for exactly the same reason
("Maya uniquifies; two characters can hold the same sword"). Generalised
into a new module `maya_overrig/manifest.py`:

- Every RigPicker set gets three string attributes at creation:
  `rigPickerRoot` (the character root's UUID), `rigPickerKind`
  (`ik` / `fk` / `twist`) and `rigPickerName` (the limb or chain).
- Nothing is ever found by set name again. A lookup scans
  `cmds.ls("RigPicker_*", type="objectSet")` and matches on the
  attributes. The readable name stays as it is, for the outliner.
- **Legacy files keep working**: a set with no `rigPickerRoot` belongs to
  whoever asks, but only while the scene holds a single character — which
  is the only kind of scene it could have been rigged in. The moment a
  second character arrives, untagged manifests stop answering for anyone
  but the sole-character case, and the rule is stated in one pure
  function (`manifest.owner_matches`) rather than spread across callers.

**The controller index.** `<bone>_FK_ctrl` stops being a name to look up
and becomes an entry in a per-character index, built two ways:

- **After a build** — from the character's own FK manifests. The chain set
  holds the knots; matching a leaf name *inside a set that already belongs
  to one character* is unambiguous. A trailing digit run is stripped, so
  `upperarm_l_FK_ctrl1` reads as `upperarm_l`. The match is exact against
  `bone + "_FK_ctrl"`, which is what keeps OverRig's dead
  `..._FK_ctrl_aimConstraint1` and our `..._FK_ring_tmpShape` out.
- **During a build** — from the build itself. `_dress_knots` already knows
  which knot it renamed for which bone; it now returns that map, and
  `build_fk` threads it through coupling, align and orient. No name lookup
  happens at all inside a build, which is the one moment when two
  identically-named controllers genuinely coexist.

`fkchains.controller_name(joint)` stays: it is what *names* a new
controller. What goes away is trusting it to *find* one.

### Where "the active character" comes from

Every entry point already receives `scene_map`, the picker's
`{bone name: DAG path}` binding — and a binding map carries its own root:
the shallowest joint path in it, because the map is built by
`naming.hierarchy_map(root)`, which includes the root itself.

So no signature changes anywhere. A new module `maya_overrig/active.py`
holds the context:

```python
active.adopt(scene_map)   # derive the root and make it current; -> uuid
active.root()             # long path, re-resolved from the UUID
active.root_uuid()
active.set_root(root)     # the picker's Connect
active.clear()
```

`root_of(scene_map)` is pure and tie-broken by path, so it answers the
same way every run. Every MEL-running entry point calls `adopt` first
(`build_fk`, `rebuild`, `bake_fk`, `bake_selection`, `switch_limbs`,
`convert_limbs`, `builder.build`, `builder.bake_limbs`, `twist.build`,
`twist.bake`), which means a verify script that assembles its own
`scene_map` and calls `build_fk(scene_map)` scopes correctly with zero
edits — and there are twelve of those, all of them proof this project
relies on.

The picker's `_bind` also sets it, so Connect is what the animator
experiences: press Connect on a hierarchy, and that hierarchy is what
every button acts on.

**A module-level context, deliberately.** The alternative — a `root`
parameter on thirty functions — would rewrite twelve live verify scripts
and eight test modules, and the model is wrong anyway: there is exactly
one active character, the way there is exactly one current time. The
policy stays pure and testable in `manifest.py`; `active.py` is a setter,
a getter and one pure derivation.

### What stays scene-wide, and why

- `builder.recorded_members()` — the shield that stops `_reclaim` dooming
  anything we bookkept. Scoping it would let a bake on character one
  reclaim character two's rig. Scene-wide is the safe direction.
- `overrig.set_members(overrig.KNOT_SET)` — OverRig's own set, shared by
  every character. `character_roots()` excludes joints under it, which is
  what keeps a built rig from reading as a dozen skeletons (trap 1).
- `aimrig` — already identity-by-attribute, never name-resolved, and an
  aim belongs to a weapon rather than a character. Untouched.

## 3. Add Character, many times

`character.refusal()` refused whenever the scene held any skeleton, for a
stated reason: the incoming `root` gets renamed and the picker and the
bridge "refuse to guess between" two characters. Scoping removes the
premise — the picker no longer guesses, it is told.

So the refusal goes, and two things take its place:

- **The message names the rename.** Only the TOP node collides:
  `root` → `root1`, while `pelvis` and everything below keep their plain
  names, because they are children of a different parent. That is what
  makes a second character usable at all, and it is worth saying out loud
  in the status line.
- **The new character is connected immediately.** `add_character()`
  returns the root it imported, and the Scene Setup window hands it to
  `picker_window.connect_root(root)` — so "add" and "work on it" are one
  press. With no picker open, nothing happens and the next Connect
  decides.

The refusal is kept for one case: **no** skeleton is not a problem, but a
second press within the same second is — so `add_character` still refuses
when the file it is about to import is missing, and reports what arrived.

## 4. Import and Export: selection, then connect

`animimport.choose_target_root` already preferred the selection. It gains
one step:

```
selection (non-empty)  ->  its skeleton
else the picker's connected root
else the only skeleton in the scene
else the one named `root`
else refuse
```

Namespaced roots are still never candidates: an exclusive merge matches
plain bone names, so a namespaced skeleton could not receive the clip
anyway. `animexport.resolve_root()` delegates to the same function, so
export follows import by construction — which is what the user asked for
("такая же логика с экспортом").

### The merge needs the other characters out of the way

`FBXImport -v exmerge` matches bone names inside the FBX plugin. With two
Mannys in the scene, `pelvis` is ambiguous and the plugin picks whichever
it finds — so choosing a target correctly is not enough on its own.

Before the merge, every OTHER skeleton's joints are renamed into a
temporary namespace (`rigPickerHold1:pelvis`) and put back afterwards, in
a `finally`. A rename is invisible to connections — constraints,
skinClusters and animCurves connect to nodes, not names — and it is the
only lever that reaches inside the FBX plugin's own name matching.

The isolation is skipped entirely when there is nothing to isolate, which
is every single-character scene the tool has ever run in.

## Testing

Pure and testable without Maya, in `tests/test_manifest.py` and
`tests/test_active.py`:

- `owner_matches` — tagged/untagged × sole/multiple.
- `pick` — the right manifest out of a table holding two characters' sets,
  including Maya's uniquified names.
- `control_leaf` / `controls_in` — the digit strip, the exact-suffix
  match, and the rejection of `_FK_ctrl_aimConstraint1`,
  `_FK_ctrlShape`, `_FK_ring_tmpShape`.
- `root_of` — shallowest path wins, ties broken by path, empty map is
  None.
- `choose_target_root` — selection beats connect beats sole beats named.
- `hold_namespace` / the isolation plan — which joints get renamed, and
  that the target's are not among them.

Scene-touching halves get a fake `cmds` where the shape of the call is the
thing under test (the tag write, the prefix scan), following
`tests/test_aimrig.py`.

**Live verification** — `docs/superpowers/plans/verify_two_characters.py`,
to be run in the animator's Maya: two Mannys in one scene, build on each,
and assert that every manifest, every controller, every bake and every
clip import lands on the character that was connected and leaves the
other one bit-identical. That is the proof; unit tests have repeatedly
passed here while the scene was broken.

## Not done, deliberately

- **Renaming the second character's bones.** Tempting (`root1` is ugly)
  and wrong: UE clips merge by plain bone name, and a prefix would break
  every import onto that character.
- **A character dropdown in the picker.** Connect already is one, and the
  user described Connect as the mechanism.
- **Scoping `aimrig`.** Already correct.
- **Per-character namespaces on import.** The bridge's whole merge design
  rests on plain names (trap: "a namespace is exactly what stops the
  names matching"). The temporary hold namespace above is the narrow
  version of the same idea, and it exists only for the duration of one
  `FBXImport` call.
