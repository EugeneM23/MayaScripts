# MayaScripts — working notes

Read this first. It is written for a fresh session with no conversation history:
what exists, how to run and verify it, and the things that already went wrong so
they do not go wrong again.

## What is here

**The repo root is the workshop. `SkeldarAnim/` is the plugin.** That split
landed 2026-09-01 ("изолируем нашу полку как отдельный плагин чтобы ты тут не
путался куда какие скрипты") and it is the first thing to know: if it is in
`SkeldarAnim/`, a colleague receives it; if it is at the root, it builds,
tests or rebuilds what ships — nothing else lives there.

```
MayaScripts/                  the workshop (one branch: main)
├── SkeldarAnim/              THE PLUGIN -- this, and only this, ships
│   ├── install.py  README_INSTALL.txt  skeldar_features.py
│   ├── maya_hub*.py  maya_uebridge/  maya_scenesetup/  maya_poselib/  ...
│   ├── maya_rigs.py  maya_asretarget.py  maya_pmretarget.py  maya_rig_retarget.py
│   └── icons/  assets/  overrig/  poses/  plug-ins/
├── sources/                  what the assets are REBUILT from -- never ships
│   ├── weapons/  orc/  creep/  manny/  armor/  README.md
│   └── AdvancedSkeleton/     local only, .gitignore (its licence)
├── make_build.py             dev tool: builds the zip from SkeldarAnim/
├── SkeldarAnim_Install.py  SkeldarAnim_Cascadeur_Install.py   one-file installers (release assets)
├── .github/workflows/        every push to main touching the plugin -> a release (Check update)
└── tests/  docs/  CLAUDE.md
```

**The cleanup, 2026-10-10** (the animator: «Давай пока откажимся от живой
комуникации в плагине и уберем ее из проекта. Потом давай сделаем чистку
удалим из проекта все что не входит в сборку, все старые скрипты нам не нужны.
Наведем порядок на гит хабе сольем все в одну ветку … Позы можно удалить»;
asked, they kept `tests/`, `sources/` and `docs/` whole):

- **Voice is gone** — the hub's Voice section (group voice rooms, screen
  share; `SkeldarAnim/maya_voice/`, the Cloudflare Worker `voice_server/`,
  its tests, spec and plan), built and released the same morning (618a9ee,
  3d54714), reverted out by `54a8ccb`. Shared and Stash stay. The server was
  never deployed from here (no Node on this machine).
- **The standalone root tools are gone**: `maya_skelfit` and `maya_meltmorph`
  with their project skills (`manny-skeleton`, `melt-morph`), `maya_retarget`
  (Manny → the protective suit), `maya_anim_batch_export` / `_headcam`,
  `maya_bonemelt` / `bonemorph` / `bonewave`, `maya_center_of_mass` (superseded
  by `maya_com`), `maya_geobones` / `geobonesrig` + `geobones_groups.json`,
  `maya_meshsnap`, `maya_shake`, `maya_skin_weight_helper`, and `archive/`
  (the superseded rig tools and the Curve Overlay). Their sections left this
  file; their verify scripts and specs stay in `docs/` as history. Everything
  is in git: the parent of the cleanup commit `283f0dd` holds them all.
- **One branch, `main`.** `feature/overrig-picker` (where everything was
  built) and every feature / worktree branch were merged into it and deleted,
  locally and on GitHub; the worktrees beside the repo went with them. CI
  builds on a push to `main`. Work goes straight onto `main` now.
- The Pose Library's test cards left `SkeldarAnim/poses/` (only `.gitkeep`
  ships; the installer still keeps a colleague's local cards).

**Nothing outside the repository is needed since 2026-09-28** («все нужные
файлы для работы нашего плагина давай перенесем в папку плагина»). The
plugin reads only its own folder — the fallbacks to the animator's
`Animations/` (the sword, Manny's infected original skeleton, `Manny_rig_02`,
the old OverRig install) and the `Character.legacy` column are gone, and
`tests/test_sources.py` pins that no plugin string names `Animations/` or
`Downloads`. The asset scripts' inputs were COPIED (originals left where they
were) into `sources/`, beside the plugin rather than in it — in git, never in
a build — as the animator chose: `weapons/Spear_03.fbx` + `Halberd_A.tga` +
`Dagger.fbx`, `orc/SK_Orc_Marauder_F.FBX`, `creep/creep_T-pose_draft.fbx`
(Cascadeur's, byte-identical to the Downloads `(1)` copy; its textures are
embedded, so the `.fbm` an import extracts is ignored), `manny/Manny_rig_02.ma`;
`sources/README.md` says what reads each. **AdvancedSkeleton 6.797 is in
`sources/AdvancedSkeleton/` but NOT in git**: its EULA says «You may not
resell, redistribute, or sublicense the software itself» and the repository
is public — the animator chose local-only; a fresh clone unpacks it there
before a rig build. Every script's `AS_MEL` points there. Proof: 2341 unit
tests; `verify_spear03_weapon.py` 19/19 and
`verify_creep_skeleton_fbx_cascadeur.py` 6/6 reading from `sources/`.

**Read the next two sections first — since 2026-09-07 the shelf is the
AdvancedSkeleton pipeline, OverRig and the picker are switched OFF, and
since 2026-09-08 a scene may hold MANY rigs (each in its own namespace),
Retarget and Bake are ONE button, Overshoot is off the shelf and the Curve
Overlay is out of the plugin (in git history only since the 2026-10-10
cleanup).**
Everything below about OverRig, the Rig Picker, Connect Arms, Add Aim and
Camera Setup as a button describes code that is still in the repo and the
payload, and still tested, but not on the shelf; two flags bring it back.

`install.payload()` did not change: its names were always relative to
`source_root()`, the folder holding `install.py`. Three things did —
`tests/__init__.py` puts the plugin folder on `sys.path` (discovery gives the
repo root), `make_build.py` derives its OUTPUT dir from its own location so
the zip still lands beside the repository, and every dev entry point and
verify plan now says `.../MayaScripts/SkeldarAnim`. (The standalone root
tools that stayed at the root then were removed in the 2026-10-10 cleanup.)

One convention inside:

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

## The AdvancedSkeleton pipeline (2026-09-07) — what the shelf is NOW

The animator's ask, that morning: «отключим все что связано с over rig и
полностью перейдем на наш риг и ретаргет адванцед скелетон … Bridge: import
onto the skeleton поменяем на автоматический импорт нашего рига + импорт
выбранной анимации, потом ретаргет, бейк, удаление скелета … уберем весь
функционал по работе с перфорсом … одно окно … Add character добавляет наш
адванцед скелетон риг … оружие к персонажу по выделенному контролу …
Connect arms / disconnect / add aim / Camera setup убираем; сетап камеры в
момент ретаргета … переносим анимацию weapon bone и camera root/bone».
Spec: `docs/superpowers/specs/2026-09-07-advancedskeleton-pipeline-design.md`,
plan `docs/superpowers/plans/2026-09-07-advancedskeleton-pipeline.md`.
Proof: `verify_rig_pipeline.py` — **green 2026-09-07, 0 of 30 gates
failed**, in **mayapy standalone** (it adds a rig and deletes skeletons, so
never in the animator's scene); the installed copy refreshed and smoked
live the same evening (2129 unit tests).

**The shelf** (since 2026-09-08): UE Bridge, Scene Setup, Retarget,
Hotkeys, Studio, Colour — **and since 2026-09-17 all of them live as
collapsible sections of ONE dockable window, `maya_hub`, with a button
`SkeldarAnim` ahead of them that opens it; Scene Setup is two sections,
Characters and Weapons; see "The SkeldarAnim hub" below. Since
2026-09-19 the shelf is TWO buttons, `SkeldarAnim` and `OverRig` — the
seven section buttons wait behind `SECTION_BUTTONS`; see "Two buttons on
the shelf" below.** **`skeldar_features.py`** (stdlib, five booleans)
gates the OverRig panel button (`OVERRIG`, True), the 84 OverRig hotkey
rows (`OVERRIG_HOTKEYS`), the Rig Picker button and its 6 rows and
handing a new character to the picker (`PICKER`, `character.connect`),
the Overshoot button with its 6 rows (`OVERSHOOT`) and the seven section
buttons (`SECTION_BUTTONS`); all but `OVERRIG` False. `install.features()`
loads it from beside `install.py` by path (at drop time nothing of ours
is on `sys.path`); `maya_hotkeys.commands(flags)` is the pure table.
Nothing was deleted — the animator's words were «оставь его где-то».

**The retarget lives in the plugin**: `maya_asretarget.py`,
`maya_pmretarget.py`, `maya_rig_retarget.py` moved from the repo root into
`SkeldarAnim/` (payload rows; `maya_pmretarget.ASSETS` is `<dir>/assets`
now, it used to assume the repo root; the three verify scripts' `REPO`
points at the plugin folder). The Retarget/Bake shelf buttons are the
INSTALLER's (`maya_rig_retarget.retarget_button` / `bake_button` — call,
print, `inViewMessage`), which retires the animator's two hand-made ones
that every re-drag wiped.

**The bake is ours, on the vendor's contract.** `vendor_bake(start, end)`
in both modules is `asMoCapMatcherBake` read whole and replicated in
`cmds` flag for flag (constraints off the holder's switch, resolved through
`constraintParentInverseMatrix`, `bakeResults -simulation` over the range,
`delete -staticChannels`); `bake()` calls it over `source_key_range()`.
**No `mel.eval` is left in either module** — AdvancedSkeleton lives under
one animator's `Downloads/` and a colleague's fresh Maya, or the bridge's
IMPORT, would otherwise die on `Cannot find procedure` (trap 20's shape).
The two modules stay independent copies (a test pins that pmretarget
imports nothing from its sibling), so the helper is duplicated on purpose.

**The Bake button does the whole "after the retarget"**
(`maya_rig_retarget.bake`, one undo chunk): the module's bake → a standing
camera setup torn down (`camera.teardown` bakes the bone back first) → any
weapon link on `weapon_r`/`weapon_l` unlinked → the **helper bones**
`weapon_r, weapon_l, camera_root, camera_bone` each parent-constrained to
the source's bone of the same name, baked over the same range, released
(`transfer_bone`; keys cut FIRST, or the constraint splices a pairBlend —
trap 37's mechanism) → links relinked (the sword snaps onto the new track
and takes its stored grip back) → the module's `disconnect()` → **Camera
Setup** on the rig's `camera_bone` (`camera.setup`; the Scene Setup button
is gone, this is where it happens). World space, no offset: the source is a
twin and the rig's hand reproduces the source's to 0.0016 cm. Measured
standalone: hand_r on the reference **0.000007**, weapon_r/weapon_l
**0.000001**, camera_root/camera_bone **0.000000**, root motion
**0.000000**; the camera sits in the bone's transform to **0.000000**. A
Mixamo source has none of the four and the step says so; a bone under
somebody else's constraint is skipped by name (`helper_plan`, pure).

**The bridge is one window and IMPORT is the pipeline**
(`maya_uebridge/rigimport.py`): rig present? else
`character.add_character(default_rig())` (9.5 s measured) → the previous
take cleared and the rig returned to build pose (below) → the clip imported
as its own namespaced skeleton (`import_clip(..., merge=False)`) → source
root = the topmost joint among `namespaceInfo(recurse=True, dagPath=True)`
(a Mixamo clip nests `ns:mixamorig:Hips`; `ls("ns:*")` does not reach it) →
`connect(source_root=...)` → `bake()` → `namespace(removeNamespace,
deleteNamespaceContent=True)`. Refusals (`precheck`, pure) happen before
anything is imported: no rig FILE when there is no rig, a standing
`MoCapConstraints` ("press Bake, or disconnect, first"), a rig still posed
after the reset. A connect refusal AFTER the import leaves the skeleton in
the scene and says so. The other mode, «as a new skeleton», is the old
namespaced import and stops there. The Export tab, Checkout and the VCS row
left the window — `vcs.py`/`checkouts.py` stay as modules and a test pins
that `window.py` imports neither; `Export FBX...` is the p4-less export,
`Export to uasset` unchanged.

**A clip import REPLACES the take** (`reset_build_pose()` in both
modules): the controls' TIME curves deleted (driven keys are the rig's),
translate/rotate zeroed where settable. Needed because **a BAKED rig
passes `posed_controls()`** — a keyed channel is not settable and is
skipped — while standing in the take's pose, and a connect made there
measures the pole offsets against that pose. The same rule the merge had
(trap 27). What is still posed afterwards is a channel the reset may not
touch, and that IS the refusal, by name.

**Which character — the selection, the rig, the sole skeleton**
(`maya_scenesetup.skeleton.current_root`, pure `choose_root` +
`selection_roots`): a node under the rig's top group (the top ancestor of
`Main`, never `|Group` by name) or a joint's topmost joint; several answers
→ none; then the rig's game skeleton (`rig_skeleton_root(rig_paths())`,
schema-blind); then the only skeleton with the rig's own deformation
joints excluded; then none. `animimport.connected_root()` feeds the same
answer into the bridge's target rule, so Import, Export and Add Weapon
never disagree. Scene Setup's header reads «Character: root (rig)».

**Scene Setup**: `catalog.Character` gained `kind`; rows «Manny [rig]»
(row 0, the dropdown's default, `default_rig()`), «Manny UE5 [skeleton]»
(`default_character()` — `character_path()` with no argument still means
`Manny_Skeleton.ma`), «UE4 Mannequin
[skeleton]». **As many rigs as the animator likes since 2026-09-08**, each in its own
namespace (`RIG_PRESENT` is gone; `character.rig_present` now means "at
least one" — see the many-rigs section). Connect Arms,
Disconnect Arms, Add Aim, Camera Setup are gone from the window and from
the hotkey table (modules stay; the Add/Remove guards over a standing link
or aim keep protecting old files).

**The shipped rig** `assets/Manny_Rig.ma` is the animator's final
`Manny_rig_02.ma` minus its leftover `camera1` (15 lines, transform +
shape, cut by line range, `diff` shows nothing else changed — textual like
the vaccine cut, never an open-and-resave). It carries no vaccine, no
references, no `MoCapConstraints`, and **the animator's own
`skeldarColour_red` blinn on its meshes**, which `colour.paint` would have
REUSED — every rig arriving red, swatch ignored. Add Character paints
through `colour.paint_fresh` (a new material regardless of what the asset
wears; the file's material is left unassigned and stops counting). Import
of the `.ma` needs `matrixNodes`/`quatNodes`; interactive Maya auto-loads
them, mayapy does not (`loadPlugin` in the verify). `requires mtoa /
materialx / mayaUsdPlugin` in the file print warnings and import fine.

Three things measured on the way, each a trap of its own:

58. **`cutKey` leaves a channel at whatever the DG last EVALUATED, and a
    bare `currentTime(start)` evaluates nothing in a session with no
    viewport pulling the joint.** `bonedrive.link` captured its
    `maintainOffset` at frame 0 against a bone still holding its frame-24
    values: the sword's own track was exact (0.000000) and the bone rode it
    **0.319 cm** off for the whole take — the live proofs passed because the
    viewport happened to evaluate the joint (trap 14's family). The
    frame-start values are now read off the curves before the cut and
    written back after it (`_keyed_values_at`). Diagnosed by measuring, not
    by guessing: `simulation=True` on the bake changed nothing about the
    sword's track, which was never the problem.
59. **`getAttr(plug, settable=True)` is False for a KEYED channel**, so a
    pose check that skips unsettable channels reads a baked rig as "at
    build pose". Hence the reset before every import.
60. **A test fixture that installs a fake `maya` when the real one is
    importable shadows the real package for every test module loaded after
    it** — `maya.api` is then not a package and `maya.api.OpenMayaAnim`
    fails to import. Guard on `try: import maya.cmds` first (the window
    tests' pattern); `"maya.cmds" in sys.modules` alone is not enough.

Not built: a PlayerMale rig row in Add Character; Retarget from the Scene
Setup window; removal of anything. Several rigs in one scene: the next
section.

## Many rigs in one scene, one Retarget button (2026-09-08)

The animator's ask: «Давай уберем с нашей полки оверлапер, кастомный граф
эдитор (уберем не только из полки но и из плагина в целом). Ретаргет и бейк
объединим в один скрипт. Дальше давай сделаем так чтобы наша вся система
поддерживала работу с множеством ригов, я должен иметь возможность добавить
в сцену много ригов как через add так и через import». Spec:
`docs/superpowers/specs/2026-09-08-many-rigs-design.md`. Proof:
`verify_many_rigs.py` — **green 2026-09-08, 0 of 32 gates failed**, in
**mayapy standalone** (it adds rigs and deletes skeletons); the reworked
`verify_rig_pipeline.py` **0 of 30** the same day; 2050 unit tests; the
installed copy refreshed and smoked in the animator's live Maya.

**A rig is a NAMESPACE** (`maya_rigs.py`, the one module that answers
"which rig"). Add Character imports each rig into its own —
`Manny_Rig`, `Manny_Rig1`, … (`character.free_namespace`, the clip
importer's rule) — and the message says `added as Manny_Rig1`. Measured in
mayapy: every one of the file's 2713 nodes lands under the namespace, none
stray (`ns:ControlSet`, `ns:Main`, `ns:buildPose`, `ns:FKNeck_M`,
`|ns:root`); asked for a namespace that exists, Maya makes `Manny_Rig2`
itself. **A rig already in the ROOT namespace keeps working** — every scene
made before this — as the rig whose namespace is `""`, found by its group
and its skeleton (gates 30–32). Bare skeletons stay unnamespaced.

- `Rig(namespace, control_set, main, group, skeleton_root)`; `rigs()` finds
  every objectSet whose leaf is `ControlSet` with exactly one `Main` beside
  it in the same namespace; the group is `Main`'s top ancestor (never
  `|Group` by name); the skeleton root is the shallowest constrained joint
  of that namespace outside the group. `node(rig, leaf)` → `ns:leaf`, and
  the root-namespace rig is the identity case — which is why the legacy
  scenes needed no special path.
- **Which rig**: `rig_of(path, rigs)` — a path in a rig's namespace is that
  rig's (a control, a bone, **a mesh**), a path under a root-namespace rig's
  group or skeleton is that rig's; `choose_rig`: the selection's one rig,
  else the sole rig, else a refusal that NAMES them («2 rigs in the scene
  (Manny_Rig, Manny_Rig1) - select any control or bone of the one you
  mean»). Two rigs selected is no answer. `skeleton.current_root` is
  rewritten on it (selection → the only rig → the only skeleton → none), so
  Scene Setup, Colour, the bridge and the retarget all agree.
- **Add Character SELECTS the new rig's `Main`**, so the rig just added is
  the one the next press acts on — "add it" and "work on it" stay one
  press without the picker's Connect.

**Both retarget modules take a `rig`** (`None` means `current_rig()`), and
every rig node name goes through `_n(rig, leaf)`: the controls,
`ControlSet`, the neck knobs, the FKX joints, and **the holder** —
`ns:MoCapConstraints`, one per rig, so two rigs can be connected at once
and each bake walks its own. The helper nodes (`asrtDriver_*`,
`pmrtScale`, `pmrtPole_*`) are created in the rig's namespace, or the
second rig's `pmrtScale` finds the first's. `foreign_constraints` compares
against the rig's own group. The pure halves did not change: a `Drive`
keeps its plain control name and the scene name is looked up at the point
of use. The two modules stay independent copies; both import `maya_rigs`,
which imports neither. `rig_skeleton_root` still accepts the old
`rig_paths()` list for the verify scripts that pass one.

**One Retarget button** (`maya_rig_retarget.retarget` / `run_retarget`):
which rig (above) → which source (the selection's joints that are not the
rig's own; a rig control in the same selection names the rig and is not a
source bone) → `reset_build_pose` (a rig carrying a take passes
`posed_controls` while standing in the take's pose, the bridge's
2026-09-07 lesson; still posed = refusal by name) → connect → `bake()`
(controls, helper bones, camera, disconnect) — one undo chunk. **The
source skeleton is KEPT** (the bridge's IMPORT still deletes its own
import). A holder already standing on the rig is baked rather than refused:
one button means "finish the retarget". `bake_button` is gone; `bake()`,
`connect()`, `report()`, `disconnect()` stay as API and take `rig=`.

**The bridge has three import modes**: «retarget onto the rig» (the
selected rig, else the only one — a rig is ADDED when the scene has none,
as before), «onto a NEW rig» (always adds one and retargets onto it — this
is "many rigs through import"), «as a new skeleton». `window.import_mode`
/ `mode_for` (pure); `rigimport.import_and_retarget(..., target=)`, with
`fresh_rig` (pure) finding the rig the add created by namespace diff. Two
rigs and nothing selected refuses **before the round trip to the editor**.

**Export strips the namespace** (`animimport.target_plain_names`, used by
`animexport.export_hierarchy`): measured, **the FBX exporter writes
`rigns:root`, `rigns:pelvis`** and there is no strip flag
(`FBXExportStripNamespace` does not exist), so Unreal would receive bones a
UE skeleton does not have. `cmds.rename(path, ":pelvis")` moves a node into
the root namespace (measured, and back again with the prefix); every joint
of the target does that for the length of the export, the root's collision
with a plain `root` handled as `target_root_plain` always did (others held
aside as `rpHold_`, the name Maya actually gave checked), restored by UUID
in a `finally`. Gate 28 re-imports the export into a `chk` namespace and
finds `chk:root`, `chk:pelvis`, nothing nested. **`choose_target_root` now
takes a namespaced CONNECT** — it used to drop every namespaced root as an
earlier clip's import, and with the rig's skeleton at `|Manny_Rig:root`
that read "several skeletons in the scene" on the first export (found by
the verify, gate 26). Roots found by scanning stay plain-only.

**Per-rig camera**: `camera.setup(bone)` names its camera in the bone's
namespace (`Manny_Rig1:SceneSetup_camera`, `camera_name_for`, pure) and
`teardown(bone)` removes only the camera constrained to THIS bone
(`camera_for`), never "any of ours" — two rigs mean two cameras (gate 15,
each sitting in its own bone's transform to 0.000000). The weapon already
resolved inside the chosen root's subtree and needed nothing (gate 29: a
sword on rig B drives rig B's `weapon_r` only).

Measured on the way (each a gate): the second rig's `hand_r` on its
reference **0.000007**, root motion and `camera_bone` **0.000000**; the
OTHER rig unmoved through an import and through the button
**0.000000000**; a hand-imported source retargeted by the button onto the
selected rig **0.000006**, source kept, holder gone; the legacy rig's
`hand_r` **0.000007**.

**The removals.** Overshoot went the way the picker went: `OVERSHOOT =
False` in `skeldar_features` gates its shelf row and its six hotkey rows
(the window and the five shapes); the module ships. The Curve Overlay left
the plugin as asked — the package, its six
test modules and `verify_curveview.py` went to `archive/` (last shipped at commit `f65be61`;
`archive/` itself and the section about it left in the 2026-10-10 cleanup) — and `alt+c` is given back through
`RELEASED_KEYS` on `DEFAULT_KEYS_VERSION` 5, only while it still holds our
command; `name_command` is a pure spelling, so a released row needs no
table entry. `bake.png` and `curveview.png` and their drawers are gone;
the hotkey table is one `retarget.run` row instead of connect + bake.

61. **The FBX exporter writes namespaces into the file and offers no
    flag to strip them** — measured 2026-09-08: a `rigns:root|rigns:pelvis`
    chain exports as `Model::rigns:root`, `Model::rigns:pelvis`, and
    `FBXExportStripNamespace` is "Cannot find procedure". Anything in a
    namespace that must reach Unreal by bone name has to be renamed into
    the root namespace for the length of the export (`cmds.rename(path,
    ":leaf")`) and back.
62. **A rule that excludes namespaced skeletons "because they are clip
    imports" excludes the rig the moment the rig has a namespace.**
    `choose_target_root` dropped the connect's `|Manny_Rig:root` and
    answered "several skeletons in the scene" on a correct scene; every
    unit test was green, because none of them had a namespaced connect.
    The verify's export gate caught it on the first run.
63. **A verify gate that formats `_fmt(x)` (a string) with `%.6f` raises
    only when it is reached**: `verify_rig_pipeline.py`'s gate 25 had
    carried that since 2026-09-07 and was green because an earlier gate's
    text never got there in this form. `%s` for anything `_fmt` returns.

## The SkeldarAnim hub — one dockable window, every tool a section (2026-09-17)

The animator's ask: «объединим наши скрипты в одно окошко которое можно
будет куда-то прикрепить или открепить; каждый раздел — вкладка с
возможностью закрыть и раскрыть». Chosen in the brainstorm: an
**accordion** (sections stacked in one scrollable column, each
collapsible, several open at once), not a `tabLayout`; the six shelf tools
as six sections; the shelf keeps its six buttons and gains a seventh,
`SkeldarAnim`, ahead of them. Spec:
`docs/superpowers/specs/2026-09-17-skeldar-hub-design.md` — **read its
addendum**, the live run changed four things. Proof:
`docs/superpowers/plans/verify_hub.py` — **green live 2026-09-17, 0 of 18
gates failed**, against the INSTALLED copy; 2125 unit tests; photographed
at three states through `widget.grab()`.

**`SkeldarAnim/maya_hub.py`** (`cmds` only, in the payload): one
`workspaceControl` `skeldarAnimHub` (dock it anywhere, tear it off, Maya
remembers) → `scrollLayout -childResizable` → `columnLayout
-adjustableColumn` → per section a `frameLayout(collapsable=True)` whose
collapse is remembered in `skeldarAnimHub_collapsed_<key>`. `SECTIONS` is
the table (key, label, module, builder, frame) in shelf order: UE Bridge,
Scene Setup, Retarget, Hotkeys, Studio, Colour. `show(key=None)` deletes
the four legacy standalone windows, restores the control if it exists or
creates it with `uiScript=uiscript(plugin_root())` — the script carries
the `sys.path` bootstrap with the plugin folder baked in, because **Maya
replays a docked control's uiScript at startup before any shelf button
ran** — then `expand(key)`: un-collapse, remember, and scroll the section
into view through `evalDeferred` (heights are real only after the layout
runs; measured landing at the scroll's maximum for the bottom section).
A section whose builder raises gets a text with the error and the other
five still build.

**Scene Setup is TWO sections, Characters and Weapons** (the same evening,
«декомпозируем scenesetup на characters и weapons»; the animator chose the
UI-only split over splitting the module): `window.build_characters_panel`
(the «Character: …» header, the skeleton/rig dropdown, its colour, Add
Character, its own line `mayaSceneSetupCharacterStatus`) and
`window.build_weapons_panel` (weapon dropdown, FBX, Add, Remove Weapon,
Rotate/Translate, its colour, the line `mayaSceneSetupStatus`). One
module still, because the two halves share `refresh`, the character
resolution and the colour scan; `_status(message, control)` and
`_run(action, status)` route each press to its own line. **Weapons must
follow Characters in `SECTIONS`**: the weapons builder's `refresh` writes
the Characters header. `show_window()` opens Characters, `show_weapons()`
Weapons (the package forwards both); the shelf has `Characters` and
`Weapons` buttons in place of `Scene Setup` (eight in all), the hotkey
rows `scene.weapon`/`scene.remove_weapon` open the Weapons section when
nothing is built (`_scene(..., section="weapons")`), and `window.weapons`
is a new opener row.

**Every tool gained `build_panel()`** — its controls into whatever layout
is current, same control NAMES as before, so every callback, `refresh`,
hotkey row and test kept working — **and every `show_window()` now opens
the hub on its own section** (`HUB_SECTION`). The `WINDOW` constants are
gone: a `cmds` control has ONE name per Maya session, so a tool cannot
live in the hub and in a window of its own; "is the panel open" is
`is_open()` (its status control exists) in each module, and
`maya_hotkeys._scene` asks that. Retarget and Hotkeys, which were bare
shelf actions, got small sections: one instruction, the `Retarget` button
and a status line `skeldarRetargetStatus` that `_show` also writes; the
`Hotkey map: ON/OFF` toggle `skeldarHotkeysToggle`, painted by the same
`paint()` as the shelf button, plus `Hotkey Editor...`. `maya_winfit` is
no longer called (the hub scrolls) and stays for Overshoot. Overshoot,
the picker and OverRig are not sections (not on the shelf; the last two
do not fit an accordion).

Measured in the live run, each a gate or a rewrite:

66. **A `formLayout` inside an adjustable column reports a huge minimum
    width — 1128 px here — whatever its children are told**, and the
    column grows a horizontal scrollbar with the right-attached buttons
    off the edge. Nothing set on the list (`width=100`) changed it. The
    UE Bridge section is rows in a column now; the three mode radios
    stand vertically (in a row they want 670 px at 150 %).
67. **A `text -wordWrap` inside a `columnLayout` keeps its one-line
    height and clips the wrapped second line**; give it `height=36`. And
    a long status label WITHOUT wordWrap widens the whole column (Scene
    Setup's refusal asked for 657 px). Default group widths are wide
    too: `floatFieldGrp` ×3 = 588 px, `textFieldGrp` 580,
    `colorSliderGrp (60,60,130)` + button = 544 — set `columnWidth`s.
    After: the column's minimum is **331 logical** against the hub's
    initial 500.
68. **`workspaceControl -q -uiScript` answers None** — Maya keeps the
    script and will not show it — so a gate about the uiScript proves the
    string `show()` hands over, not what Maya stored. And **`widget.grab()`
    in the SAME send as the collapse that changed the layout photographs
    the OLD layout** (a collapsed frame drawn at full height as an empty
    grey block — trap 57's family): the state change and its picture must
    be two sends. The collapsed header is 30 px in the next one.

## The hub's skin — style B, grouped cards, the header (2026-09-28)

The animator: «Давай попробуем для нашего плагина нарисовать кастомный красивый интерфейс. За одно
можно подумать над тем как сделать расположение кнопок более красивым». Picked in the brainstorm from
mockups: **style B** (our own dark charcoal, rounded cards, ONE orange primary action per section,
the palette as dots) over A (Maya's greys tidied) and C (a dense icon grid); **scheme 3** — the
accordion stays (several open at once), grouped **Scene** (Characters, Weapons, Connections),
**Animation** (UE Bridge, Retarget), **Look** (Studio, Colour), with a strip of icons on top that
opens a section and scrolls to it; **Hotkeys and Update are the header** (the keyboard lights while
the map is on, the chip is the installed commit and checks for an update on a click, ⋮ holds Hotkey
Editor / Check update / Classic look). Mid-build: «сделаем чтобы активное окно подсвечивалось
немного другим цветом» — the card last pressed or focused in, or jumped to, is lit (`card_active`
background, a thin warm `card_edge`). Spec: `docs/superpowers/specs/2026-09-28-hub-skin-design.md`,
plan beside it. Proof: `docs/superpowers/plans/verify_hub_skin.py` — **26/26 live in the animator's
Maya, 2026-09-28**, against the installed copy, the hub docked and rebuilt IN PLACE (five sends:
open every card, measure, classic, back, memory); 2522 unit tests.

**Three new modules** (payload rows, and a test now pins that every `maya_*.py` beside install.py
ships): `maya_hubstyle.py` (stdlib: `TOKENS`, `GROUPS`, `stylesheet(scale, arrow=)`, the MARKS —
`hubstyle.mark(cmds.button(...), "primary", "plus")` records what a control IS and returns its name;
`swatch(name, rgb)`; `take_marks()`; `pick(skin, classic)` / `tool_label` / `tool_width` for the few
things one arrangement does differently in the two hubs, while `set_skinning` says which is being
built), `maya_hubicons.py` (stdlib: 24 Tabler outline icons, MIT notice in the module, `svg(name,
colour)`), `maya_hubqt.py` (the Qt layer: `Skin` — root, header, message line, strip, group labels,
`Card`s — and `apply_marks`). `maya_hub` builds the SKIN where `maya_hubqt.available()` and the
optionVar `skeldarAnimHub_classic` is not 1, else the CLASSIC frameLayout accordion (the 2026-09-17
hub, every section, plus a «Switch to the new look» button when Qt is there); a skin failing as a
whole is destroyed at once and the classic hub built instead. `SECTIONS` gained `group` and `icon`
and the new order (characters, weapons, connections, uebridge, retarget, studio, colour, hotkeys,
update); **a new tool is now a row with a group and an icon** (`maya_hubicons.ICONS`). `say(message,
state)`, `paint_hotkeys`, `set_classic` (deferred — the press comes from inside what the rebuild
deletes). `maya_hotkeys.paint` and `maya_update._status` tell the hub only if `maya_hub` is already
in `sys.modules`.

**How cmds controls live in Qt cards** (measured in a probe window first): the workspaceControl's
widget has a QVBoxLayout; our root goes into it; each card's body is a named `QVBoxLayout`, and
`cmds.setParent(MQtUtil.fullName(getCppPointer(layout)))` puts the builder's controls in it — names,
exists/edit/query unchanged, the path running through our Qt objects (so every one is named). Maya's
controls are Qt subclasses a stylesheet reaches (`QmayaOptionMenu`→QComboBox, `QmayaField`→QLineEdit,
`QmayaIconTextRadioButton`→a checkable QPushButton, `QmayaLabel`→QLabel, layouts plain QWidgets that
paint nothing); one stylesheet on the root styles them by `skRole`. Every builder kept its control
names and callbacks; what changed is arrangement: dots + swatch + brush instead of a colour slider,
Add + Remove in one row, a folder button for any FBX (`browse_fbx`), Connections' three parents and
the bridge's import mode as SEGMENTS (`iconTextRadioCollection`; `menus()` / `import_mode()` read
them, the pure halves untouched), Studio's checks as chips two to a row and no fixed widths, the
Retarget paragraph a tooltip, `bound_message` without its "Character:" prefix (it is the card's
subtitle).

96. **A layout reached through a temporary wrapper dies with it.** `find(control).layout()` answered
    valid and was «Internal C++ object (QVBoxLayout) already deleted» one call later, when the
    widget's wrapper had been collected — the skin fell back to classic on its very first live
    build. Hold the WIDGET (`host_widget`) for as long as its layout is used. The same family:
    `layout.itemAt(i).widget()` wrappers are invalidated with the item wrapper and handed back DEAD
    by the next `wrapInstance` of that address («QPushButton already deleted» one mark later);
    `find` now `shiboken.invalidate`s a dead wrapper and wraps afresh, and `wrapInstance(ptr,
    QLabel)` returns the cached QWidget wrapper when one exists, so class methods (`setWordWrap`,
    `setIcon`) go through `setProperty("wordWrap"/"icon"/"iconSize")`.
97. **Maya's rowLayout places its children at their own widths whatever Qt says.** Its layout is
    `QmayaRowLayout` (a QHBoxLayout underneath); `setStretch(i, 1)` and Expanding size policies
    changed nothing (segments 35 / 62 px in a 314 px track). A minimum width moves them — and would
    stop the dock ever getting narrower. The segments are moved into a row of OURS laid over the
    track (an event filter keeps it over it); Maya still finds them by name. And
    `findChildren(type, "", FindDirectChildrenOnly)` answered nothing in PySide6 6.8.3 —
    `children()` with an isinstance filter did.
98. **Stylesheet specificity and Maya's QLabels**: a blanket `QFrame[skCard] QWidget {background:
    transparent}` outranked `QPushButton[skRole=primary]` and emptied every field; a `QLabel`
    background hid the colour slider's swatch (`QmayaColorSliderLabel` is a QLabel). No blanket
    rules; a test pins it. Stylesheet PIXELS ARE PHYSICAL here (devicePixelRatio 1.0, logical DPI
    144, the UI font 16 px): every px × `mayaDpiSetting -q -realScaleValue`.
99. **Deleting a classic hub runs every frameLayout's collapseCommand**: after a classic hub was
    deleted every section came back remembered collapsed. `rebuild()` saves the collapse memory
    before deleting the classic scroll layout and writes it back after.
100. **The disposable Maya is on the animator's screen, and they use it** (trap 85 again): all seven
     cards came back collapsed twice in the dev Maya — the first time it was clicks (only card
     sections were set), the second was trap 99 (Hotkeys, a classic frame, was set too). Tell the
     two apart by WHICH memory changed before blaming either.
101. **PowerShell's `@" "@` here-string expands backticks**: `` `r `` in a Python docstring became a
     carriage return (git then called connections.py binary, `-text`) and every other backticked
     word lost its quotes. Python source goes through Write/Edit, or a literal `@' '@` string.

A hidden card body is never laid out: measure segments or widths with the card OPEN, in a send
after opening it (the verify's phase 0 — Connections collapsed read 35 and 56 px). The content
must fit the animator's 360 px dock: `content.minimumSizeHint().width()` ≤ the viewport (465 ≤ 510
live); the colour rows were 29 px too wide until the hidden slider stopped taking width
(`pick((1, 30, 1), (1, 34, 60))`).

**The same evening, after using it** («UE bridge давай передвинем наверх как он и был. При нажатии
на верхнюю панель с разделами все другие панели должны закрыться и открыться только нужная.
Выделение активной панели должно быть ярче. Раздел с обновлением давай вернём»): the order is
UE Bridge first — a group stays together, so **Animation** (UE Bridge, Retarget) is the first
group, then Scene, Look, and **Settings** holding the **Update card** again (its installed line
the subtitle; `HEADER_ONLY = ("hotkeys",)` replaced the settings-group rule). A **jump is
exclusive** (`maya_hub.focus`: every other card closed and remembered so), a card's own header
still toggles that card alone; `show(key)` stays non-exclusive. The active card: `card_active`
`#383a41` and a 2 px outline in the accent itself. The header chip opens the Update card and
checks; `maya_update._status` writes the card's line and only colours the chip
(`maya_hub.chip_state`), the header's message line serving a skin without the card. Proof:
`verify_hub_skin.py` **26/26 live again**, with gate 2 now counting the roots in the control.

102. **An install left TWO skins in the hub**: the fresh `maya_hub` does not know the `_SKIN` an
     older module object built (the install purges modules, not widgets), so its rebuild added a
     root beside the old one — two hubs at half height each, every control name twice, and
     `find` styling the OLD set (the verify: subtitles not moved, Apply all / Import without a
     role, focus lighting the wrong card). `_build_skin` now deletes every root named
     `skeldarAnimHubRoot` in the control first (`maya_hubqt.destroy_roots`) — found by name,
     never by module state (trap 75's family).

**And the light follows the mouse** («когда я наводил мышкой на какой-то раздел у него включалась
подсветка»): the card under the mouse is lit; with the mouse off every card (in the gaps, the
header, the viewport, another window) the one worked in is lit again — last pressed or focused
in, or jumped to (`Skin.pinned`; `set_active` pins, `_light` only shows). The same
application-wide watcher now takes `Enter` (and `Leave` on the root, for leaving to a window
where no Enter of ours arrives); `card_of` answers None after ONE `isAncestorOf` for everything
outside the hub, so Maya's own widgets cost one parent walk per entry. Verify gate 27, **27/27
live**.

**…but not back to a closed card, and not at once** (minutes later: «если я убираю курсор с
раздела, то подсветка перепрыгивает на последний активный раздел ... картинка как бы мигает.
Давай будем переключать подсветку на последний активный раздел только если он открыт»): off
every card the light goes to `Skin.resting()` — the pinned card only while it is OPEN, else
nothing — and only after `FALLBACK_MS` (150) on a single-shot timer that entering another card
cancels, so crossing the gap between two cards no longer flashes the pinned one. Gate 27 checks
the pause, the closed case and the open case: **27/27 live**.

## Connections — the hands on the weapon, on the AdvancedSkeleton rig (2026-09-18)

The animator's ask: «вкладка connections, в которой мы сможем привязывать и
отвязывать руки к оружию. При помощи OverRig, будем перепекать анимацию
(важно, чтобы мы не ломали иерархию нашего рига)». Spec:
`docs/superpowers/specs/2026-09-18-connections-design.md`. Module:
`maya_scenesetup/connections.py`, a hub section after Weapons (no shelf
button, no icon — the 2026-09-17 rule); hotkey rows `window.connections`,
`connections.connect`, `connections.disconnect`. Proof:
`docs/superpowers/plans/verify_connections.py` — **21 of 22 gates live
2026-09-18** in the animator's Maya on a throwaway rig it adds and deletes;
the one failure (gate 15, "moving the weapon moves the hand", read 0.000)
was the MEASUREMENT (trap 69 below): a probe re-measured the same nudge
after a real time change at **10.000** and the round trip at 0.000000. The
gate was rewritten; **the fixed script has not re-run whole** — by then the
animator had a rig of their own in the scene, with the left hand connected
through this very section, and the verify SKIPS beside a standing rig. Run
it in a rig-free scene at the next chance. 2154 unit tests. **Live, not standalone: OverRig's `apply_Parent_out/in` read the
time slider and die in mayapy with «Cannot convert data of type int to
type float[]»** (line 4375 / 4230, measured).

**Since the same evening the section is a SWITCHING MODEL, not two
buttons** («нужна гибкая система переключений: обе руки к мечу, руки по
отдельности, меч к левой или правой руке, меч к правой а левую руку к
мечу» — read the spec's addendum). Three nodes, two links: each of L–W and
R–W is `holds` (the weapon hangs in that hand; one hand at most), `follows`
(the IK control rides the weapon) or nothing; a scheme is `{"L", "R"}`.
The panel is **three parent rows** — `Hand_R [Free|Weapon] Apply`,
`Hand_L [Free|Weapon] Apply`, `Weapon [World|Hand_R|Hand_L] Apply` — and
**Apply all** (the animator's shape after an arrow row read unclear). A
pick fixes a cycle in the other menu and says so (`resolve_menus`, pure)
and touches nothing; a row's Apply changes that link only
(`wanted_for_row`, pure), Apply all takes all three (`scheme_from_menus`,
pure, round-trips with `menus_from_scheme`); either runs `plan(current,
wanted)` (pure) — releases first, then the weapon's move (lift, hang),
then new followers — and the menus are re-read from the scene after.
Photographed live 2026-09-18 on the animator's own scene: «Manny_Rig:
LongSwordMesh - weapon in the right hand; left hand free», menus
Free / Free / Hand_R.
**The drive bone follows the holding hand**: `weapon_r` in the right,
`weapon_l` in the left, unchanged in world; a bone change unlinks the old
bone and constrains the new one with NO offset (the socket sits ON the
weapon). `connect()`/`disconnect()` remain as the hotkeys' two schemes.
The verify was rewritten for the model (25 gates: right-holds-left-follows,
both follow, weapon into the LEFT hand driving `weapon_l` with the nudged
track kept, back to the right) and **has not run**: the animator has had a
rig of their own in the scene since the first build. 2159 unit tests.

**A following hand rides a PROXY since the same evening** («сейчас мы
теряем возможность анимировать объект, который был приконстрейнен …
через прокси-локатор внутри родителя, перепечь на него анимацию и уже
потом констрейнить» — the spec's addendum 2). `handProxy_<side>` is a
locator parented under the weapon's geometry (`_make_proxy`, the module's
one `cmds.parent`, on our own locator — a test pins that), marked
`skeldarHandProxy`; the hand's world track is baked onto it (`_bake_onto`:
temp no-offset constraint, `bakeResults`, still channels un-keyed via
`is_constant`), then the IK control is constrained to the proxy with NO
offset. So the take is kept frame for frame (the direct constraint had
flattened it to one frame's grip) **and the proxy is what the animator
keys** — a key on it moves the hand against the weapon. Release deletes
the proxy too (`proxy_of`, by attribute). The bake span is playback ∪ the
weapon's keys ∪ the controls' keys. 2167 unit tests; the verify gained
four proxy gates (26–29) and still awaits a rig-free scene.

**Five fixes after first use, and BakeAcross** (the same night — the
spec's addendum 3): proxies are found **by attribute, never by
`cmds.ls("*.attr")`** (trap 70 below; the old lookup left
`Manny_Rig:handProxy_*` behind after every bake), `sweep_orphans()` at the
front of every Apply/BakeAcross; **the rider is hidden while it rides**
(`visibility` off, the old value on the constraint as `skeldarHiddenVis`,
back on release); `PROXY_SCALE` 8.4; no description text in the section;
**BakeAcross** — every selected object rides the LAST selected one through
a proxy of its own (`attach_to_proxy`, generic; `across_plan` pure:
parent = last, refusals for fewer than two, a cycle, a child inside the
parent, a rider already riding), **Release** beside it (riders or their
proxies baked, freed, shown). `_transforms` resolves the selection to LONG
paths first — the cycle check is a path-prefix test and a short name read
as outside everything (a cube got attached to its own proxy). **Proof,
live on the animator's own rig** («риг в сцене для тебя»):
`verify_connections.py` **39 of 39 gates, 2026-09-18**, the scene left as
found (sword in the right hand, linked, controls shown, no keys, no
proxies) — the borrowed-rig cleanup deletes only the sandbox nodes and our
proxies and cuts the test keys by name: a blanket UUID diff once took the
sword's link along with the baked curves. Gates measure the IK CONTROLS,
not the hand bone: the bone follows only as far as the arm reaches (5.658
of a 10 cm nudge at the animator's grip), and a proxy key on a SCALED
weapon moves the control exactly as far as the proxy moved in world
(3.753 for +5 local, both). 2174 unit tests.

70. **`cmds.ls("*.attr")` does not cross a namespace colon.** A `*`
    pattern matches a plain `handProxy_L.skeldarHandProxy` and never
    `Manny_Rig:handProxy_L.skeldarHandProxy`; `"*:*.attr"` reaches one
    level and no deeper. Every rig lives in a namespace here (2026-09-08),
    so a by-attribute lookup written with a pattern finds nothing of ours —
    and fails as "nothing to clean up", silently. Walk the candidates by
    type (`ls(type="locator")`) and ask `attributeQuery` on each. The one
    other pattern lookup in the plugin, `maya_vpstudio.find_rig`'s
    `ls("*.skeldarVpStudio")`, works only because the studio group stands
    outside every namespace.

**The split is the design.** The AdvancedSkeleton IK hand controls
`IKArm_R/L` live at `CustomOrientIKArm_*|IKExtraArm_*|IKArm_*` and that
place is load-bearing, so **the hands are constrained, never re-parented**
(before the proxy: a `parentConstraint` to the weapon's geometry with
`maintainOffset` captured on the CURRENT frame; now to the proxy with no
offset; keys cut FIRST, trap 37; the current values read off the curves
with `keyframe -eval` and written back after the cut, trap 58), while
**the weapon is re-baked by OverRig**:
`parent_out` lifts it from the hand bone to world (drift **0.000000**,
still driving `weapon_r` — the link's constraint targets the node),
`parent_in` hangs it back on Disconnect with whatever the animator did out
in the world re-baked into the hand's space. Disconnect bakes the controls
with `cmds.bakeResults` over the playback range ∪ the weapon's keys and
deletes only OUR constraints — identity by the `skeldarHandLink` attribute
(the weapon's UUID), never by name. `FKIKArm_*.FKIKBlend` goes to 10; a
blend KEYED elsewhere is refused by name. Poles untouched. Two checkboxes,
Right/Left, both on, remembered. **The retarget refuses a connected rig**
(`maya_rig_retarget.hands_connected`, in `run_retarget` and `bake`): its
`connect` would skip the constrained controls as foreign. Weapons > Add /
Remove already refuse a linked weapon; the Weapons panel finds a weapon out
in world through `bonedrive.driving_weapon`. The old
`maya_scenesetup/connect.py` (the OverRig-rig picker's Connect Arms) is
untouched behind its flag.

Measured: the right hand's world track through Connect **0.000192**
(the constraint's offset re-expressed), the hand following a 10 cm weapon
nudge by **10.000**, the nudged track kept through Disconnect's bake to
**0.000000**, the controls' DAG paths identical before and after.

69. **`getAttr(plug, time=t)` does NOT pull a constraint + IK chain.** The
    weapon nudged 10.000 and the hand's `worldMatrix[0]` read at `time=12`
    answered **0.000**, while a real `currentTime(11); currentTime(12)` and
    `xform` answered **10.000**. A gate written the first way passed its
    "unchanged" checks trivially and failed the one that had to see a
    change; a gate about a driven node needs a real time change (trap 14's
    family). And **OverRig's `apply_Parent_out` bakes across the ANIMATION
    range (`-ast/-aet`), not the playback range**: 743 keys over 0..742
    with the slider at 0..24 — set the outer range too when it matters.

## The camera stands on `camera_root` (2026-09-18)

The animator: «в наш риг нужно добавить камеру так же, как мы делаем при
ретаргете, только не camera bone привязывать к камере, а camera root, и в
механизм ретаргета тоже внесём эту правку». Spec:
`docs/superpowers/specs/2026-09-18-camera-on-camera-root-design.md`.
`maya_scenesetup.camera.BONE` is `camera_root`; measured first: on the rig
`camera_root` and its child `camera_bone` stand in the SAME world
transform at rest (0.000000 apart, both at (0, 164, 0) turned (−90, 0, 0),
local rotates and jointOrients zero), so `AXIS_OFFSET` measured against
`camera_bone` on 2026-08-17 holds unchanged. `maya_rig_retarget.
carry_helpers` sets the camera up on `camera_root` and tears a standing
camera down on BOTH bones first (a camera an older build left on
`camera_bone` would meet the transfer and splice a pairBlend); both bones
are still carried from the source. **Camera Setup is a button in the
Characters section again** (`window.camera_setup`, after Add Character):
the retarget's step by hand over playback ∪ the bone's keys; a second
press bakes the bone back and removes the camera. Proof:
`verify_rig_pipeline.py` **0 of 30 gates, 2026-09-18** with the camera
gates on `camera_root` (the camera in the bone's transform to 0.000000,
both camera bones carried to 0.000000); the button pressed twice live on
the animator's rig over the port — «SceneSetup_camera sits on camera_root
and drives it - 101 frames baked», the camera in the bone's transform to
**0.000000**, a 7 cm move of the camera moving `camera_root` **7.000**,
the second press «camera removed - camera_root baked back and free» with
the bone back to 0.000000. **The game's lens since 2026-10-15**: read from
the open Atone editor, `BP_Character`'s `PlayerCamera` is FieldOfView 100,
16:9, MaintainXFOV (100 is horizontal), and the project's NearClipPlane 0.5;
`camera.lens` sets a 16:9 gate fitted horizontally, focal 15.100 mm
(`focal_for`), near clip 0.5 - Maya reads 100.0001 deg across (was camera1's
16.494 mm, 95 deg). `verify_many_rigs.py`'s camera gates were
pointed at `camera_root` too and not re-run. 2175 unit tests.

## Two buttons on the shelf: SkeldarAnim and OverRig (2026-09-19)

The animator: «Давай из нашей полки уберем все лишнии скрипты. Пока
пусть будет только наш SkeldarAnim ну и овер риг тоже пускай
устанавливается вместе с ним» — and, asked, the OverRig BUTTON only, not
its 84 hotkey rows. Spec:
`docs/superpowers/specs/2026-09-19-two-button-shelf-design.md`. Nothing
deleted («пока»): two flags in `skeldar_features.py` do it, the shape the
picker and Overshoot already had.

- **`SECTION_BUTTONS = False`**: the seven per-section rows of
  `install._PYTHON_BUTTONS` (UE Bridge, Characters, Weapons, Retarget,
  Hotkeys, Studio, Colour) carry this flag where they carried `""`. The
  hub row is unflagged. Icons, every `show_window()` and the `window.*`
  hotkey rows stay and still open the hub on their section; `True`
  restores all seven in their old places.
- **`OVERRIG` was split**: `OVERRIG = True` is the shelf button alone
  (Barnev's own installer command, verbatim, at the shipped `overrig/`);
  **`OVERRIG_HOTKEYS = False`** is the 84 rows in `maya_hotkeys.commands`.
  `install.button_specs` and `commands` read their flag with `getattr`, so
  an older `skeldar_features` beside an installed copy answers False
  rather than raising.
- `maya_hotkeys.paint` finds the `Hotkeys` shelf button by label and
  skips the paint when it is absent (already so); the hub's toggle
  `skeldarHotkeysToggle` is what lights up now.

Proof: 2178 unit tests; the repo's `install.install(quiet=True)` run in
the animator's open Maya over the port (the installed folder's own
`install` and `skeldar_features` purged first) — shelf labels
`['SkeldarAnim', 'OverRig']`, the installed `skeldar_features.py`
carrying the new values, the `SkeldarAnim` button's baked command
opening the hub (`skeldarAnimHub` visible) and the `OverRig` button's
MEL sourcing `base_OverRig_scripts` and raising `basicOverRigScripts`;
`docs/superpowers/plans/verify_install.py`'s shelf gates rewritten for
the two labels (not re-run whole). `make_build.py` →
`SkeldarAnim_2026-09-19.zip`, 85 files, 26.8 MB.

## Update: every push is a build, Check update installs it (2026-09-28)

The animator: «раздел update … кнопка Check update: мая пойдет в
репозиторий на гит хабе и скачает сборку последней версии, если сборка еще
не установлена … при каждом коммите в гит хаб делать актуальную сборку и
заливать ее … я сделаю репозиторий публичным». Spec:
`docs/superpowers/specs/2026-09-28-update-button-design.md`. **Raised before
building and decided by the animator: the repository goes public WHOLE** —
OverRig (paid; its licence's clause 3 forbids making it available), Epic's
Manny/UE4 Mannequin, the Orc, the studio's Perforce host in this file, all
of history. The private road (read-only token) was offered and declined.
The visibility flip is theirs; nothing here does it.

- **CI**: `.github/workflows/build.yml`, on push to `main` (`feature/overrig-picker` until 2026-10-10)
  touching `SkeldarAnim/**`, `make_build.py` or the workflow (+
  `workflow_dispatch`): `python3 make_build.py --out dist/SkeldarAnim.zip
  --version-out dist/version.json` (stdlib — the runner's python is
  enough), `gh release create build-<utc>-<payload sha7>` with both assets,
  `--latest`, notes = the push's commits under `SkeldarAnim/`; skipped when
  a release for that payload commit exists; builds beyond the newest 10
  pruned with their tags. `concurrency: release`, nothing cancelled.
- **`version.json`** — one record (`commit`, `short`, `subject`, `date`,
  `branch`, `dirty`, `log` = the last 30 `[sha, subject]`, plus `built` in a
  build), shaped by `install.git_record` (stdlib `subprocess` git,
  `CREATE_NO_WINDOW`; `{}` without git). **The commit is the last one that
  touched the PAYLOAD, not HEAD** (`git log -1 -- <payload>`), and so is
  the log: a CLAUDE.md-only push is not a new build — it would otherwise
  publish identical files, and a source install would be offered the
  previous build. `make_build` writes it INTO the
  archive and, with `--version-out`, beside it; a release build refuses
  without a commit. `install.install` writes `<dest>/version.json`: the
  build's own, or — installed from the repo — the git record plus
  `"source"`. Not a payload row (the source tree holds none); a re-drag
  from the installed folder leaves it alone.
- **`SkeldarAnim/maya_update.py`** — hub section `update`, last; the
  installed line, **Check update**, a status line. Reads
  `github.com/EugeneM23/MayaScripts/releases/latest/download/version.json`
  (a plain redirecting URL: no REST API, no token, no 60/hour limit shared
  behind the studio's NAT), compares commits, asks with installed /
  available / what's new (`confirm_text`; a source install is warned it
  gets replaced), downloads the zip under a cancellable `progressWindow`,
  checks and unpacks it, and runs **the DOWNLOADED `install.py`** loaded by
  path as `skeldar_update_installer` (a new build may change the payload).
  Every refusal before the install says «nothing changed»; an installer
  failure keeps the unpacked build and names it. The installer purges our
  modules, so the rebuild is an `evalDeferred` that imports `maya_hub`
  afresh — its `_BUILT_HERE` is False, so `show()` rebuilds in place (trap
  75) — and writes «Updated to …» on the fresh status line.

Proof: `docs/superpowers/plans/verify_update.py` — **16/16 + 9/9 live
2026-09-28** in a DISPOSABLE Maya with its own `MAYA_APP_DIR` (scratch prefs,
scratch install folder, scratch shelf — the animator's installed copy never
touched) against a local `http.server` standing in for the release: a
colleague's first drag (record copied, shelf `SkeldarAnim` + `OverRig`), the
shelf button's baked command opening the hub on the INSTALLED copy, the
record wound back a commit, Check update asking once with both builds and
the new commit's subject, the old build's stray file gone, the record the
published one, the modules purged; then the hub rebuilt from fresh modules
with the message, a second press «Up to date», 404 / cancel / refused
connection each changing nothing. While the repo was private the real
address answered «No build is published … (or the repository is private)».
**The real road, after the animator made the repository public the same
morning**: Actions runs 1 and 2 green, releases `build-…-e298bdc` and
`build-…-601eaae` (48.3 MB each), `latest/download/version.json` = 601eaae,
clean; the animator's live Maya pressed «Up to date: 601eaae» with no
question asked; the disposable Maya (scratch prefs holding an older build)
asked once listing the two new commits, downloaded and installed from
GitHub in **7.5 s**, its record equal to the release's, the hub rebuilt
from fresh modules, a second press «Up to date», the shelf still two
buttons. The panel's lines carry no commit subject since `601eaae`: in the
animator's 360 px dock the installed line wrapped past its height (trap
67). 2314 unit tests. A colleague on a build from before this has no
Update section: one manual drag of a new build, then the button.

**…and one file installs it from GitHub** (the same day: «скрипт который можно кинуть в
открытую сцену и он установит наш плагин с гит хаба»; spec
`docs/superpowers/specs/2026-09-28-setup-script-design.md`). **`SkeldarAnim_Install.py`** at the
repo root — beside the plugin, not in the payload: what a colleague has BEFORE the plugin.
Dropped into a viewport it downloads `releases/latest/download/SkeldarAnim.zip` (cancellable
progress window), checks and unpacks it to a temp folder, runs **that build's own `install.py`**
(loaded by path as `skeldar_setup_installer`, not quiet — its dialog reports the install), removes
the temp folder and opens the hub from the installed copy. Refusals say «nothing was installed»;
an installer failure keeps the unpacked build and names it; the scene is never touched; a second
drop updates. Stdlib at import — **Maya's drop handler
(`maya.app.general.executeDroppedPythonFile`) `import_module`s the file by its stem, so
`__name__` is never `"__main__"` there** and the `__main__` block only serves a Script Editor
`exec`. Every release carries it as a third asset (stable link
`releases/latest/download/SkeldarAnim_Install.py`); a push touching only it builds nothing and
re-uploads it onto the latest release (`--clobber`). `README_INSTALL.txt` leads with it.
Proof: `verify_setup_script.py` in a disposable Maya with a FRESH `MAYA_APP_DIR` (nothing of ours
installed or importable): the file downloaded from the real release (8.9 KB), dropped through
Maya's own `executeDroppedPythonFile` with `confirmDialog` recorded, **installed in 10.0 s**, the
record the published one, the payload in place, the shelf two buttons, the download gone, the hub
open from the installed copy, Check update «Up to date». **That run's dialog told the fresh Maya
«The previous version was loaded in this session (1 modules dropped)»** — trap 89 below; fixed in
`install.install`, the gate added. 2361 unit tests.

89. **The installer purged the flags module it had just loaded itself and called it the previous
    version.** `_build_shelf` → `button_specs` → `features()` puts `skeldar_features` into
    `sys.modules`, and `purge_modules()` ran AFTER the shelf, dropped it and counted it — so every
    install into a fresh Maya (a hand drag of `install.py` too) said an old build had been loaded.
    The purge runs first now, the button count is taken before `skeldar_features` is popped (it
    was read from the SOURCE, a temp folder for the one-file installer), and a test pins the order.

## The Creep: its own AS rig, and a ROTATION-ONLY retarget (2026-09-24)

**Named the Hunter until the night of 2026-09-24** (the animator: «всё что Hunter переименуем на
Creep»): the catalog rows «Creep [rig]» / «Creep [skeleton]» / «Creep Sword», the assets
`Creep_Rig.ma` / `Creep_Skeleton.ma` / `Creep_Sword.fbx`, the meshes `Creep_Body/Back/Arm_L/Arm_R/
Face`, the layer `Creep_Skeleton`, `CreepSwordMesh`, the rig's namespace `Creep_Rig`, every script
`*_creep_*`. The animator's own SOURCE files keep the old spelling and the scripts still read them
by it: the group `|Hunter` (`|Hanter` that morning), `Hanter_Skeleton`, `Hunter_Sword` /
`Hunter_Sword_Low`. A scene holding a rig added before the rename (namespace `Hunter_Rig`) keeps
working — a rig is found by its structure, the weapon by its marker attribute, and a remembered
«Hunter [rig]» in the dropdown falls back to the first row.

A creature on a UE5 Manny skeleton (Manny's bone names plus `weapon_test`; arms 34.8 +
36.0 cm against Manny's 27.8 + 27.3, a longer neck, the same legs) in the animator's
`Downloads/creep_T-pose_MIX_06_skin.mb`, group `|Hunter` (it was `|Hanter` in the morning
— the animator renamed it mid-session, and deleted the UE reference Manny too; find
things, never hardcode them). Spec:
`docs/superpowers/specs/2026-09-24-creep-rig-rotation-retarget-design.md`. In one day:
joint scales removed (12 joints, mesh unchanged: `BPM' = BPM·WM_old·WM_new⁻¹`), the bind
re-baked into the UE A-pose in place (Orig shapes written, `BPM = WM⁻¹`), an AS rig, and
the retarget mode. **The scene was left unsaved** with backups beside it
(`creep_T-pose_MIX_06_skin_BACKUP_*.mb`).

**The rig** — `docs/superpowers/plans/as_creep_rig_procedure.py`, proof
`verify_advancedskeleton_creep_rig.py` **0 of 25 gates, live**. The Manny procedure by
LONG PATH (two skeletons with the same bone names were in the scene), the fit put on every
bone, and three deliberate differences:

- **Bones take ORIENTATION only** (the pelvis its position too). The vendor's point +
  orient + scale let the LEFT arm's lengths wander 0.01–0.07 cm: AS mirrors the left side
  from the right fit, the skeleton is 0.045 cm asymmetric, and a `-mo` pointConstraint
  keeps that offset in the bone's PARENT space. Orientation only = lengths exact, no
  translation keys below the pelvis in an export.
- **IK feet LEVEL** in AS's own world frame (the animator: the foot bones' turn tilted the
  foot boxes). `as_frames` + `align_ik_target` — see trap 71.
- **`Group.skeldarRetarget = "rotation"`** marks it for the retarget.
- **Hand helpers, the animator's layout**: `ik_hand_r`/`ik_hand_l` exactly ON the hands and
  following them with no offset, `ik_hand_gun` (their parent) undriven with zero channels
  (`place_ik_helpers`); `ik_foot_*` follow the feet as on Manny.

**The retarget** — `maya_asretarget.rotation_mode(rig)` reads that mark; the animator's
rule «ретаргет не должен учитывать растяжение костей (привязываем только по
ротейшенам)». FK controls take the source bone's world orientation and NO position; IK
ends and poles follow the rig's OWN FKX joints (the PlayerMale rule, copied — this module
still imports nothing from its sibling; the pole's geometry is now measured before the
first constraint); Main and RootX_M keep the twin drive (root motion and hips exact,
unscaled). An unmarked rig is driven exactly as before; the dispatcher needed nothing.
17 unit tests (`tests/test_asretarget_rotation.py`), 2195 in all; the installed copy
refreshed. Proof: `verify_creep_rotation_retarget.py` in **mayapy standalone** on a saved
copy with a Longsword clip — **0 of 10**: bones on the source's orientation to 0.001°,
lengths unchanged on every frame (0.000000 cm) against a source whose own lengths differ,
root/pelvis 0.000000, IK = FK to 0.001 cm.

**Limb bones are judged by where they point, not by their roll**: AS's
Shoulder/Elbow/Hip/Knee never roll — the roll lives in the twist joints (94.9° on that
clip, the Manny rig's design too) — and AS removes it about ITS joint's axis, so a child
standing off the bone's X (the Creep's lowerarm 0.32 cm, 0.53°) swings on a cone; the
bound is twice each skeleton's off-axis angle, measured from the children's local
translations.

**The Creep ships as the second rig row** (the same day, «добавим хантера как риг в наш
плагин»): `catalog.CHARACTERS[1]` = «Creep [rig]», `assets/Creep_Rig.ma` (39 MB), Manny
stays row 0 and `default_rig()`. A rig now lands in a namespace named for its OWN key
(`character.rig_namespace`: `Creep_Rig`, `Creep_Rig1`, …) — `RIG_NAMESPACE_BASE` would
have made it `Manny_Rig1`. Before the export the animator's scene was tidied («назовем
правильно и сгруппируем, чтобы геометрия не валялась непонятно где»; `tidy()` in the
procedure): `|root` out of the FBX wrapper to world level with the Z-up turn in its
jointOrient (Manny_Rig's shape), the meshes `Creep_Body/Back/Arm_L/Arm_R/Face` in the rig's
own `Group|Geometry`, the swords out of the skeleton into `Geometry|Creep_Props` riding
`weapon_test` by constraint, the wrapper renamed `Manny_Reference` holding only the
`SKM_Manny_Simple` mesh the animator did not want shipped. The asset is built in mayapy
standalone from a saved copy (`make_creep_rig_asset.py`: the reference mesh, its skin and
curves, `camera1`, `materialXStack1`, unused shading networks, unknown nodes and empty
dagPoses deleted; saved as `.ma`; banned text refused). Proof:
`verify_creep_rig_asset.py` — **0 of 10 gates, standalone**: two Creeps and a Manny added
into an empty scene, each in its own namespace, the Creeps marked rotation-only, at their
bind, painted, no script node; a Longsword clip retargeted onto the first Creep through
the button (orientations 0.001°, lengths 0.000000 cm) while the second Creep and the Manny
moved 0.000000000. 2198 unit tests; the installed copy refreshed (the hub's dropdown is
built when the section opens — close and reopen it).

**And a clean skeleton row, «Creep [skeleton]»** («не только риг хантера, а и чистый
скелет»): `assets/Creep_Skeleton.ma` (37.7 MB), built from `Creep_Rig.ma` by
`make_creep_skeleton_asset.py` in standalone — every bone's world matrix recorded, the
constraints deleted, the bones re-seated from their world matrices (drift 0.000000000),
the meshes and props to `|Creep` at world level (the props keep their weapon_test
constraint), `|Group` deleted, then every node nothing kept depends on (the kept set is
the two hierarchies, the meshes' and props' history, their shading, the bind pose, the
skeleton's layer, the default nodes) — 315 of AS's utility nodes, its sets and driven-key
curves, plus FBX-embedded textures nothing wore. Row after «Manny UE5 [skeleton]», plain
names like every skeleton row. Proof `verify_creep_skeleton_asset.py`, **0 of 9
standalone**: 90 joints at `|root`, 5 skins at their bind, nothing of the rig, the sword
following the hand, a rig beside it untouched by it and not moving it. `rename_note` now
names the PLAIN root that collided — beside an AS rig it had named
`Creep_Rig:FKXAnkle_L`, one of the rig's dozens of top joints. 2202 unit tests.

**Weapons on the Creep, as on every rig** (the same day: «оружие хантера встроено прямо в
риг ... добавлять и удалять оружие и анимация переносилась на вепон бону и обратно ... меч
хантера в список нашего оружия»). `make_creep_sword_asset.py` (standalone, on the shipped
rig): the blade (`Creep_Sword` — and NOT the handle: `Creep_Sword_Low` was described as "a
second grip piece" when the animator was asked, and it is THE grip; fixed the same night, below)
exported as `assets/Creep_Sword.fbx` in the frame the Creep's weapon
bone WILL have — blade +Y (tip +74.3), guard X, thickness Z, the origin where the Creep held
it — catalog row «Creep Sword» on `weapon_r`, scale 1; the swords dropped from the rig;
`weapon_test` renamed **`weapon_r`** and turned half a turn about its own Z (the sword lay
along its −Y, every catalog weapon lies along +Y), **`weapon_l`** created under hand_l as
its behaviour mirror (S·M·S); BPM re-expressed, bindPose reset; the clean skeleton rebuilt
from the new rig (**both turned a further quarter into UE's orientation on 2026-09-30** —
"One weapon socket for every rig" below). Procedure steps `export_sword` (BEFORE the bone turns — the sword rides it
by constraint), `drop_props`, `weapon_bones`. **The retarget carries the helper bones
RELATIVE TO THEIR PARENT on a rotation-only rig** (`maya_rig_retarget.helper_space`,
`transfer_bone(relative=True)`: world = W_src · P_src⁻¹ · P_dst through a multMatrix): in
world space the Creep's weapon_r would stand at the SOURCE's hand, 26% of an arm away.
Proof `verify_creep_rig_asset.py` **0 of 13** (Add at zero grip on weapon_r to 7.8e-14 and
driving it; after the retarget weapon_r on the clip's hand-relative track to 1.7e-13, moving
4.69 in the hand, the sword on it; Remove Weapon hands the bone its track back to 0.0);
`verify_creep_skeleton_asset.py` 9/9; 2205 unit tests. A scene holding a Creep rig added
BEFORE this has the old rig (swords inside, weapon_test) — re-add it.

**The weapon lives OUTSIDE the skeleton — every rig, every skeleton** (the same evening:
«можем ли мы вообще не располагать наше оружие прямо в иерархии скелета? … давай делать всё
максимально правильно, так чтобы мы не нарушали иерархию нашего скелета»; spec addendum 4).
`maya_scenesetup/weaponspace.py` (a leaf): per hand a **weapon space**
`hand_r_weaponSpace`, a transform parent-constrained to the hand with NO offset, marked
`mayaWeaponSpace`, in a `WeaponSpaces` group (marked, locked) under the rig's top group —
or at world level beside a bare skeleton. The weapon is the space's CHILD, so its channels
still mean "relative to the hand" and the grip, the bonedrive link, the relink after an
import and OverRig's `parent_in`/`_out` needed nothing. **Found from the hand, never by
name** (`space_of`: the constraint the hand drives → its marked parent); `ensure_space` on
the first Add or hang, `prune` once only its constraint is left (and the group once empty);
`holding_hand(weapon)` answers for a spaced weapon AND for one a file from before holds
directly under the hand — the legacy shape keeps working where it is and moves into a space
on the next Connections hang or Remove + Add. `hand_for(path)` lets a selected weapon still
name its character (`skeleton.current_root`). Wired through `attach.attach/find_attached/
detach` and `connections.apply/read_scheme`. **And the export writes bones only** (trap 76).
Proof: `verify_weapon_space.py` **11/11 standalone** (both rigs' skeletons bones and
constraints only, retargeted with the swords on weapon_r, FBXs read back 91/93 joints and 0
meshes, a hand-parented cube included, Remove pruning the space and group, a legacy sword
found and removed); `verify_connections.py` **40/40 twice** — Manny_Rig + Long Sword and
Creep_Rig + Creep Sword — **in a SEPARATE disposable Maya** launched with
`PYTHONPATH` pointing at a scratch `userSetup.py` that opens port 7002 (OverRig's
`parent_in`/`_out` need a live Maya; the animator's scene was not the place, and the
process was killed afterwards so it saved no prefs). 2211 unit tests.

**The bind is SKM_Manny_Simple's pose since the same night** (the animator, with the original
creature `|SKM_Manny_Simple` — the untouched T-bind file, old joint scales and all — keyed at
frame 0 into the pose wanted: «исходная поза у рига Creep_Rig:Group и у скелета этого рига не
должна никак отличаться от позы скелета SKM_Manny_Simple … текущая поза SKM_Manny_Simple должна
стать байнд позой для Creep_Rig:root»; spec addendum 5). Measured first: the A bind differed by
50.6° on the hands, 55–91° on the fingers, 11° neck, 6° spine, 7.5° legs, 5° feet, 1.4° / 2.4 cm
pelvis — clavicles/upperarms/forearms already exact. **That pose turns the hands ~50° and SKM's
skin stretches the hand meshes ×3.1 / ×4.7 at the wrist and thumb** (62 / 112 edges past 1.5×,
the first A bake's damage); asked, the animator chose the exact pose with the mesh exactly as SKM
shows it. The pipeline, re-runnable: the pose and SKM's five deformed meshes dumped read-only to
`docs/superpowers/plans/creep_bind_pose.json.gz` (2 MB) → `rebind_creep_pose.py` (mayapy, on
the clean skeleton: bones onto the pose's world matrices SCALE STRIPPED, helpers by their rules —
ik_hand_r/l on the hands, ik_hand_gun at zero, ik_foot_* keeping their relation to the feet,
weapon_r/l riding the hands untouched — each Orig shape = SKM's deformed points, BPM = WM⁻¹,
bindPose1 reset; refuses a mesh whose vertex order does not match: face 100 %, body 71 %, back
48 % on SKM's T rest, the arm meshes by edge lengths) → `rebuild_creep_rig.py` (LIVE, the
procedure's fit → build → constrain → orient → align → SDK axes → level feet → mark, meshes into
`Group|Geometry`) → `make_creep_rig_asset.py` → `make_creep_skeleton_asset.py`. **The rig
needed no pose work of its own: `fit()` puts every fit joint on its bone, so a rig built over a
skeleton standing in the pose has that pose as its build pose.** The AS build ran in a
**disposable second Maya** on port 7002 (AS reads its own UI, so not mayapy; and not the
animator's scene). Proof: `verify_creep_bind_pose.py` **9/9 standalone** (the rig at zero: every
bone on the pose to 9.9e-10, every vertex on SKM's to 5.1e-6 cm, skin at bind 3e-13, helpers on
their rules; a positive control; the clean skeleton the same; weapon_r/l in the hands exactly as
in the old asset to 2.8e-14, so the Creep Sword's frame holds); `verify_advancedskeleton_creep_rig.py`
**25/25 live**; `verify_creep_rig_asset.py` **13/13** (its gate 11 still expected the sword under
hand_r — written before the weapon spaces, never re-run; now asks `holding_hand`);
`verify_creep_skeleton_asset.py` 9/9; `verify_weapon_space.py` 11/11; `verify_connections.py`
40/40 on the new Creep; 2211 unit tests. The old A-pose assets are NOT in git (the Creep assets
were never committed); a scene holding a Creep added before this has the A bind — re-add it.

**…and the rig's joints stand ON the skeleton's, both sides** (minutes later, the animator: «кости
скелета и кости рига не совпадают, как минимум на левой руке»; spec addendum 6). Measured: the
LEFT fingers' AS joints 1.1–3.2 cm off their bones — exactly the pose's own asymmetry (SKM's
fingers bend differently per hand), because **AdvancedSkeleton builds the left side as the MIRROR
of the right fit**; and the upper-arm twist Parts 2.35 / 4.70 cm off on both sides plus
`NeckPart1_M` 0.51 cm — present in every Creep build since the first (the old asset measured the
same), because AS spaces Parts evenly (1/3, 2/3) while the Creep's upper-arm twists stand at
0.266 / 0.532. Two procedure changes: `fit()` runs the vendor's **`asCreateNonSymmetryJoints`**
(every side chain under a middle joint copied into `<joint>_NonSymmetry` fit joints, `noMirror`
on the right; the build turns them into the same `_L` names, so nothing downstream changed) and
fits them onto the `_l` bones, the Knee's `twistJoints` copied onto its copy by hand; new
**`place_parts()`** after the build sets each `<joint>PartBM<side>.target[0].weight` to the game
twists' step (evenly stepped or refused) — the child (Elbow/Wrist/Knee/Ankle) is POINT-CONSTRAINED
by AS and holds its place by itself — and shifts `NeckPart1_M_pointConstraint1.offset` (parent =
Neck_M space, the frame neck_02 is rigid in) onto neck_02. The skeleton does not move (orientation
only). Live verify gate 26: every deformation joint on its bone to **0.0000 cm** (left fingers
included), twist Parts to 0.17 cm (the Creep's own twists stand that far off the bone line);
**26/26**; the other five verifies and Connections re-run green on the rebuilt assets. The rig now
carries 360 joints (the fit skeleton's 36 non-symmetry copies stay in the hidden FitSkeleton).

**…and the normals** (the animator, looking at the new hands: «что произошло с геометрией, почему
она стала такой тёмной?»). Trap 77 below. `dump_creep_bind_normals.py` (standalone) imports the
very FBX the animator brought in as SKM_Manny_Simple (`Downloads/creep_T-pose_draft (1).fbx`; its
points at the pose match the pose data to 1.5e-6, so it is the same mesh) and dumps its skin's own
world-space face-vertex normals there to `creep_bind_normals.json.gz`; `rebind_creep_pose.py`
now writes them onto the Orig shapes, locked (`set_normals`, also `--normals-only` for a scene
already re-bound — the built rig was fixed that way, the rig itself does not depend on normals).
Measured: the hand meshes' stored normals from **55–59° median off their surface (p90 99–107°)
to 4.6–4.8°**, the same as the face and back; the shown normals are SKM's to 0.0008°.
`verify_creep_bind_pose.py` gates 10/11 (rig and clean skeleton), **11/11**; rig asset 13/13,
skeleton 9/9 after the rebuild. The morning's A-pose asset already had the arms 44° off — nobody
had looked at the shading.

**The Creep Sword, whole and on the grip** (the animator, with a test take on the rig: «меч хантера
почему-то оказался без рукоятки … и он повёрнут на 45 градусов; при повороте меча 0 0 0 он должен
встать так, как сейчас»). Measured first: the creature's sword is TWO meshes on weapon_test —
`SwordPacked` (10890 vertices, blade/guard/pommel) and `Sword_Low.001` (1170, the grip, −7.3..+13.6
along the bone) — and the scene's sword stood right at the Weapons grip Rotate (0, 45, 0).
`make_creep_sword_fbx.py` (standalone, from the tidy backup scene, never saved) takes both pieces
into weapon_r's frame (FLIP_Z · weapon_test), turns them by that grip, unites them into ONE mesh
(`CreepSwordMesh`, 12060 vertices — a catalog weapon is one geometry) and exports; read back the
way Add reads it, the blade is the old asset turned by the grip to 8.7e-7. In the animator's scene
the sword was swapped through `attach.detach` / `attach.attach` at zero grip in one undo chunk (the
Connections scheme checked first: the right hand holds, nothing follows) and the remembered grip
`mayaSceneSetup_offset_Creep_Sword` zeroed — or the next Add would put the 45 on top: the new node
ON weapon_r (6e-14), every blade vertex where the old one stood at 45 over the whole take (8.7e-7
cm), weapon_r unmoved. A first check compared the sword NODES' matrices and read 0.69 — the old node
carried the 45 and the new one carries it in the mesh; compare vertices, not nodes. Rig asset
verify 13/13, weapon spaces 11/11.

**…and its axes on its geometry: a weapon's FRAME** (minutes later: «сейчас у меча развёрнута
геометрия, а оси стоят ровно … чтобы оси соответствовали направлению геометрии» — «но при этом меч
сохранил свою позу в руке»). The 45 in the POINTS left the node's axes on the bone and the guard 45°
off them. So the points are the model's own again (`make_creep_sword_fbx.py` without the turn: guard
±6.17 on X, thickness ±1.74 on Z) and the 45 is the catalog row's **`frame`** (`Weapon` gained the
column, default identity; the Creep Sword's `(0, 45, 0)`), written on the marked node at Add as
**`bonedrive.FRAME_ROTATE`** (`mayaWeaponFrameRotate`). Zero grip stands the NODE in its frame:
`world = grip · frame · bone` (`framed`, `_seat_of`), `place_at_grip`/`apply_grip`/`regrip` compose it,
`measured_grip` takes it away (the fields read 0 0 0), `relink` with nothing stored places at zero
grip (= the old snap for a frameless weapon), `attach` stores it before any placement. A node without
it is the identity, so every other weapon and every older sword is unchanged. **Connections' drive
bone sits on the weapon's SOCKET**, not on the turned node: `_drive_bone` sets the constraint's
`targetOffsetRotate` to `unframing(frame, bone rotateOrder)` — weapon_l taking the sword over lands
where weapon_r stands (2.8e-14). Proof: `verify_creep_rig_asset.py` **15/15** (gate 11 the node on
frame · weapon_r to 1.4e-14; gate 14 the guard along the node's X, the fields 0 0 0, and — given the
grip-in-its-points asset — every vertex where that one stood to 8.7e-7; gate 15 the socket);
`verify_weapon_space.py` 11/11 (gates 4/5/7 against frame · bone); `verify_connections.py` **40/40
twice** in a disposable Maya (gate 18 now the full socket, rotation and position, 0.000000);
2222 unit tests. The animator's scene held no sword at the time; their next Add took the new one.

**…and the smoothing and the bind pose, for the FBX** (the animator, on
`Animations/Rigs/Characters/Creep_Skeleton.fbx` from `export_creep_skeleton_fbx.py`: «скелет
выгрузился без групп сглаживания на геометрии»). Trap 78 below: the file DID carry a smoothing layer
— of zeros, every edge hard — because every edge of all five Creep meshes was hard in Maya, already
in the animator's creature scene before any of our work, under all-locked normals. The creature's
source FBX (`creep_T-pose_draft (1).fbx`) has the real flags and they are exactly the edges whose two
faces' normals differ (plus the borders): **618 of 2949 on an arm, 2832 of 16735 on the back, 10833
of 43992 on the body, 1284 of 139827 on the face** — so `rebind_creep_pose.soft_edges`/`set_edges`
derive them from the normals the meshes carry (0.01°: the same normal), flags only. The same export's
log said «Unable to find the bind pose for : / root / ik_foot_root / ik_foot_l. No bind poses …
will be exported» — trap 79 — so `whole_bind_pose` saves bindPose1 again over all 91 joints and moves
every skin onto it. Both run in the rebind pipeline now, and **`repair_creep_assets.py`** applied them
to the shipped `Creep_Rig.ma` in place (standalone: points unchanged 0, normals 0.0011°, skins at
bind, script nodes cut), then `make_creep_skeleton_asset.py` rebuilt `Creep_Skeleton.ma` from it.
`export_creep_skeleton_fbx.py` refuses an all-hard mesh, reads the smoothing back (hard counts equal
the asset's) and takes `--overwrite`; the re-export's layer holds 33159 soft / 10833 hard on the body
and so on, and the log carries no bind-pose warning. Maya 2027 writes "smoothing groups" as a
**ByEdge** layer (measured on a cube: the option on gives ByEdge, off gives none). Proof:
`verify_creep_bind_pose.py` **15/15** (gates 12/13 the smoothing on rig and skeleton equal to the
source's with 0 edges off the rule, 14/15 the bind pose whole), rig asset 15/15, skeleton 9/9, weapon
spaces 11/11. The assets are smaller now (24.6 / 23.0 MB): shared normals where the edges are soft.
A Creep added before this carries the all-hard edges — re-add it before exporting its mesh.

**…and the sword at the size the creature holds it** (2026-09-25, the animator: «наш меч крипа стал
меньше чем был изначально, нужно вернуть прежний размер»). Trap 86 below: in the creature's own files
(Cascadeur's `creep_T-pose_draft (1).fbx`, the animator's scene before our work) `lowerarm_r` scales
1.32 and the sword, a plain child of weapon_test, inherits it — **124.017 cm** pommel to tip; every
asset since the morning's joint-scale removal held **93.952**, exactly 1/1.32. `make_creep_sword_fbx.py`
now takes the creature's ORIGINAL file and expresses the pieces in weapon_test's RIGID frame (scale
stripped), so the chain's 1.32 lands in the points: read back, the new sword is the shrunk one ×1.32
about weapon_r's origin to 1.6e-5 cm — the grip stays in the hand, the handle −17.9..+9.7 on the bone.
Catalog scale stays 1.0 (the size is the model's, not a correction). Proof:
`verify_creep_rig_asset.py` **16/16** (new gate 16: the sword in the Creep's hand 124.017 cm),
`verify_weapon_space.py` 11/11. Against Cascadeur's own sword at frame 0 our zero-grip sword stands 3.3 cm
median / 11 cm at the tip away — the frame's (0, 45, 0) against Cascadeur's (0.2, 46.1, −6.3), the
same length. The animator's scene held no Creep Sword; the next Add takes the new one.

86. **Removing joint scales in place keeps the skin and loses every UNSKINNED child's size.** The
    rebind's `BPM' = BPM·WM_old·WM_new⁻¹` holds each skinned vertex where it was; a mesh parented under
    the scaled chain (the Creep's sword under weapon_test, under `lowerarm_r` at 1.32) just loses the
    inherited scale — 124 cm became 94, silently, and every later asset was cut from that. Every gate
    since compared the sword against the PREVIOUS asset, never against the creature's source; the
    animator saw it. Before removing a scale, list the non-skinned shapes under it and carry their
    world matrices across; and gate a prop against its source file, not against yesterday's copy.

79. **Maya's FBX exporter drops the bind pose WHOLE over one bad member.** The Creep's bindPose1
    held 87 of 91 bones, and three members (ik_foot_l, ik_hand_gun, ik_hand_l) linked
    `parents[i]` to the parent NODE's `.message` instead of the parent's `members[j]` slot; the log
    names the first («/ root / ik_foot_root / ik_foot_l») and writes no dagPose at all — the file
    keeps only the per-cluster poses. Adding the missing bones did NOT fix it (measured); saving
    the pose again over every joint did. And `dagPose -save` takes the joints' DAG CHILDREN too —
    85 constraints on the rig — so remove non-joints after the save.
78. **Locked normals hide all-hard edges — until an FBX export writes the edge flags as the
    smoothing layer.** In Maya a locked normal wins over the edge flags, so a mesh with every edge
    hard looks right; the FBX's smoothing is the flags, so it exports with no smoothing at all.
    Two things that do not fix it: `cleanupEdgeSmoothing` after `setEdgeSmoothings` re-shares the
    normals around each vertex (5449 face-vertex normals changed on the body, some by 180°), and
    writing the normals back with `setFaceVertexNormals` per face-vertex hardens every edge again.
    `setEdgeSmoothings` alone, then `updateSurface`: the flags and the locked normals are separate
    data, and Maya then shares the normals the soft edges join (the normal counts match the
    source's exactly: 2077 on an arm). Count hard edges (`isEdgeSmooth`), not only normals.

77. **Moving the points of a mesh with LOCKED normals leaves the normals where they were.** The
    FBX importer locks every normal (the file's own); the rebind in place writes new points into
    the Orig shape, and `setPoints` does not touch locked normals, so the rest mesh kept its
    T-pose normals under an A-pose / SKM-pose arm and the hands shaded dark — 44° off after the
    first bake, 55–59° median (p90 99–107°) after the second. The skin DOES turn locked normals
    when the rig moves (measured: 34–56° for a 60° shoulder turn), so only the REST normals are
    wrong: write the right ones (`setFaceVertexNormals` on the Orig), never unlock (that loses the
    file's hard edges). The measure: the angle between each vertex's stored normal and its
    area-weighted surface normal — a healthy mesh reads a median of 3–6°. Every gate of the
    rebind had passed, because they all measured positions.

76. **The FBX exporter takes a selected node's CHILDREN along, whatever they are.**
    `FBXExport -s` on the skeleton root wrote the sword hung under `hand_r` into every
    animation FBX — measured 10890 vertices, six curves and a material — and `FBXExportSkins
    false` / `FBXExportShapes false` do not stop a plain mesh. `FBXExportIncludeChildren -v
    false` plus selecting every joint (by UUID, inside the plain-name rename — trap 16) is
    what makes the file bones only; the gate that proves it parents a cube under a bone by
    hand and reads the FBX back.

74. **Maya writes its own `uiConfigurationScriptNode` and `sceneConfigurationScriptNode`
    on EVERY save, batch mode included** — deleting them before `cmds.file(save=True)` does
    not keep them out of the file. The asset script cuts their blocks out of the saved
    `.ma` text afterwards (a block runs to the next top-level statement), the way the
    vaccine was cut from Manny_Skeleton.ma, and the catalog test pins that no
    `createNode script` is in the shipped Creep.

75. **An update left the OPEN hub showing the old build**: `install.purge_modules` drops
    the plugin's modules, but the hub's workspaceControl stays, and `maya_hub.show()` only
    restored it — the animator pressed the button and saw the character dropdown without
    the Creep row the update had just added («НЕ вижу хантера в списке персонажей»),
    while `catalog.character_labels()` in the same session listed him. `maya_hub` now
    remembers whether THIS module object built the accordion (`_BUILT_HERE`, set by
    `build()` — Maya's startup replay of the uiScript sets it too) and `show()` rebuilds in
    place (`rebuild()`: the scroll layout deleted and rebuilt inside the same control, so
    where it is docked survives) when it did not. 2199 unit tests.

71. **`asControlOrientAttach` re-orients the FK↔IK align target (`AlignIKToAnkle_*`) only
    for a control that ends up CUSTOM-oriented.** Put a control back on AS's own frame and
    it gets no CustomOrient, its align target keeps the old bone-frame turn, and
    asAlignIK2FK lands the IK foot in the right place turned **117.93°** — exactly the old
    frame's angle, which is what gave it away. Do Attach's `delete orientConstraint ctrl
    alignTo` yourself. The Manny verify never tested leg IK→FK, only FK→IK.
72. **"The mesh is unchanged across the bake" is a trivially-true gate for a bind-pose
    change.** The first A-pose bake copied the UE hand orientation (a 51° wrist turn),
    every gate was green, and the animator saw «геометрия в области кистей изменила свои
    размеры». Edge lengths against the old rest mesh found it: ×4.4 at the wrist. Judge a
    re-bind by edge ratios; DQ skinning and a temporary deltaMush did not rescue the wrist,
    keeping the hand's own turn did.
73. **A scene can hold the dead DG half of a deleted AS rig** — 264 utility nodes in
    `AllSet`/`Sets`, empty layers `BodyControls`/`DeformationJoints`, no transforms. A new
    build would get uniquified names beside them. Check they connect to nothing outside
    themselves, then delete, before `fit()`.

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

There is **no system Python** — `python` resolves to the Microsoft Store stub,
and that stub does not fail, it **HANGS**: a `python - <<EOF` in the Bash tool
sits there until the timeout and a `|| mayapy` fallback beside it never fires.
Use Maya's interpreter, and never `pip install` into the Maya tree.

```
& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v
```

Qt tests run headless with `$env:QT_QPA_PLATFORM = 'offscreen'` (PySide6 6.8.3 /
Qt 6.8.3 ship with Maya 2027). 5804 tests after the 2026-10-10 cleanup, all passing, about a minute.

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

**The network cannot express a roll past ±180°, and since 2026-09-03 it
REFUSES instead of whipping** (the animator: «иногда случается перекрут
костей на руках»). `quatToEuler` wraps its output into (−180°, +180°] —
measured on isolated nodes: fed a 190° twist it answers **−170°**, fed 350°
it answers **−10°** — and `decomposeMatrix.outputQuat` canonicalises the sign
before that, so a delta past 180° is re-expressed the short way upstream of
our arithmetic and **nothing downstream can recover it**. Crossing the
boundary therefore delivered a ~360° step in one frame: measured on
`longsword Idle.0031.mb`, the network's angle went **+164.86° → −170.39°**
between frames 9 and 10 and `upperarm_twist_01_r.rotateX` stepped **223.50°**
(× the 0.667 weight), with `upperarm_twist_02_r`'s world orientation stepping
**163.66°** at frame 29. Sub-frame sampling put **121.44° of the 134.33°**
jump inside one 0.1-frame interval — an instantaneous whip, not interpolation.
So `build` now samples the driver's roll across the playback range **before it
creates anything** (`driver_rolls` → `roll_refusal`, the pure halves being
`lift`/`anchored`/`excursion`/`sampled_rolls`) and skips a segment that does
not fit, by name and with the number ("the roll reaches 473 deg, past the 180
the network can express"). That is the module's existing character — it
already refuses an axis more than 10° off the bone and a channel driven by
anything that is not ours. Two anchoring rules, both load-bearing: the zero is
the **build frame**, where the delta is the identity and the roll is exactly 0
(so that frame is sampled with the range and the sequence shifted to put it at
0), and a **span wider than 360° wraps wherever the zero sits**, which is
checked as well and needs no anchor at all. `excursion` must NOT lift its
input — a lift takes the short way between neighbours, so re-lifting a genuine
+200° reading pulls it to −160° and reports a wrapping segment as a fitting
one; a test pins that.

**Two candidate fixes were built and REFUTED by measurement, so do not
re-propose them.** Removing the swing geometrically (transport the reference
perpendicular by the minimal rotation taking the build-pose axis to the
current one) gave `upperarm_r` **−309.6..+206.6 — identical** to what shipped.
Reading the driver's innermost rotate channel diverged from the geometric roll
by **138.46°** on `upperarm_l`, and is not available at all for the follow
segments, whose drivers sit **14.35–33.83°** off the segment axis. (The
innermost-channel claim itself IS true and now measured: with order `xyz`, +30
on `rotateX` turns **30.0000°**, **0.0000°** off the joint's own X — with
`zyx` the same +30 lands 50.23° off, so it holds only for the innermost
channel, which is what `axis_choice` already checks.) The reason no third
formula helps: the right arm's bone axis swings **160.0°** on this clip and
`hand_r`'s **174.0°**, and the roll of a bone whose axis sweeps that far has
**no continuous bounded definition** — it is path-dependent, the same holonomy
that makes parallel transport around a loop come back rotated. Both
formulations agree on a 516° range because the quantity itself is unbounded.

**And the extreme input was not ours.** Every arm bone in that file carries a
**pairBlend at weight 1.000** — `input1` the imported clip's animCurves,
`input2` the OverRig parentConstraints — so the clip's keys are **muted** and
the bones are driven entirely by the IK. That is **trap 37's signature**: an
FBX merge onto a rigged skeleton. The tell that no two-handed grip explains:
the hands travel through space almost identically (**368.76** vs **375.61** cm
on the forearms, 458 vs 466 on the hands) while the right forearm rotates
**3.23×** more violently than the left (117.72° vs 36.44° per frame) and the
right upper arm **2.45×**. Files like this want `Bake+Delete` before the
merge, which `animimport`'s guard already asks for. Spec:
`docs/superpowers/specs/2026-09-03-twist-roll-limit-design.md`. Proof:
`verify_twist_roll_limit.py` — **green live 2026-09-03, 0 of 31 gates
failed**, including the two that matter most: our arithmetic matched the
standing network on **65 of 69 frames with 4 differing by exactly 360°** (the
wraps themselves), and the build-pose anchor read **0.000000000000**. Not
covered: the creation half of `build`, which wants a throwaway skeleton in an
empty scene — phase 2 walks build's call chain read-only instead, because
running a real build beside the animator's rig is not something a verify run
may do. Deliberately not done: unwrapping `twist.bake` (it samples the
channel, so it needs the per-joint 360°×weight period or a recompute from the
network's own `delta`/`dot`/`weight` nodes before they are deleted) — with the
refusal in place a freshly built rig can never wrap, so that would only patch
files already damaged.

**The twist joints have MANUAL controls too** (2026-09-03, the same evening:
«А можем ли мы сделать для твистов дополнительные контроллы и там где не
справляется авто вращение вращать твисты руками?»). One ring per SEGMENT —
eight of them — whose `rotateX` is distributed to that segment's twist joints
by **the same signed fractions `weights()` computes for the automatic term**.
That is the whole reason it is one ring per segment and not one per joint: the
distribution cannot drift between the two paths, because there is one number.
Spec: `docs/superpowers/specs/2026-09-03-twist-manual-control-design.md`.

The network's last node was already an `addDoubleLinear` holding a constant, so
the addition point existed. Per joint: `gate = auto × ring.autoTwist`,
`manual = ring.rotateX × fraction`, `blend = gate + manual`, then the old
`total = blend + build-pose value`. Three nodes a joint, eight rings; 112 nodes
becomes about 170.

**A refused segment gets the same shape minus the automatic term** — no
`delta`/`quat`/`dot`/`norm`/`angle`/`weight`/`gate` at all, just
`manual` + `total`, and **no `autoTwist` attribute**, because a dial over a
term that does not exist would be a lie and its absence is how the ring says
the segment is the animator's alone. `_drive` **refuses by name** when neither
source is present rather than connecting from nothing.

**And this closes the gap the roll limit left open.** `build` bakes any
standing network before rebuilding, and the refusal then *skipped* the segment
— so a rebuild baked the old 223° whip into keys and refused to re-rig, leaving
the whip alive as plain animation. A manual-only network reaches
`_clear_channel`, which deletes those keys. The refusal changed meaning from
**skip** to **manual only**, and the message says `MANUAL ONLY, no auto:`.

The ring is **a DAG child of its own BONE** (bones survive an FK/IK switch; an
FK controller would take the control down with it), local rotation identity so
its X is the bone's own X and `rotateX` is the innermost channel of the xyz
order, at the bone's **midpoint along the MEASURED bone direction**, radius from
the skin through `fkrings` with an outward margin so it can be grabbed over the
geometry. Every channel but `rotateX` is locked. It is **seated** like `attach.seat` does it — shear, both
pivots, both pivot translates and `rotateAxis` zeroed (trap 32). Identity is
`rigPickerTwistSegment` plus membership of `RigPicker_twist_<limb>`; `find_ring`
never asks for the name, which Maya uniquifies on the second character.
`segment.limb` **is** a bodymap region (`arm_l`, `leg_r`), so the ring wears its
limb's own colour with no lookup.

Ring creation lives in `fkrings` (`twist_ring`, `measured_radii`) because that
module already owns ring sizing and dressing for the whole toolset — no second
implementation of sizes. The new `twist → fkrings` edge is acyclic.

Nothing else changed: no picker buttons (the animator chose viewport selection),
and `bake` already samples the driven channel, so the sum lands in the keys by
itself and the rings die as manifest members.

**Known cost, stated rather than solved:** Build always tears down and
rebuilds, so a dialled ring is baked into the joints and the fresh ring starts
at zero — **dial the twists after the last Build**. Also the ring turns +30
while its joints turn 10 and 20 (it is a distributor, exactly as the automatic
term is), and `autoTwist` gates a whole segment rather than one joint. All
three were offered and accepted.

**The bone axis runs down BOTH signs of local X, and assuming +X put four of
the eight controls outside their bone** (2026-09-03, minutes after the first
build: «твисты по левой стороне строятся нормально по правой криво»).
Measured, the bone direction in each bone's OWN frame: **+X on
`upperarm_l`/`lowerarm_l` and `thigh_r`/`calf_r`, −X on `upperarm_r`/
`lowerarm_r` and `thigh_l`/`calf_l`** — not left versus right, arms and legs
use opposite conventions per side. `ring_offset(length, direction)` follows the
measured direction; before that it returned `(+length/2, 0, 0)` and four rings
sat at **t = −0.5 along the bone, outside it entirely** — 27.771 cm off on
`upperarm_r`, 43.348 on `thigh_l`. The twist joints and their fractions were
right on both sides all along; only the placement was wrong.

**`axis_sense` cancels the handedness `choice.sign` carries for the automatic
term**, so the manual share is the signed distribution and nothing else:
`manual = ring.rotateX × fraction`. That follows the convention
`align_controllers` set — *equal values on both sides give a mirrored pose* —
verified on all four pairs (a +30 ring moves both upper arms by
**−20.000000**, both forearms by **+10.000000**) while the bones run down
opposite signs. The deliberate consequence: on a −X segment the ring dials
**against** the automatic term's reported number, which is the half that does
not matter with the mesh in front of the animator.

**And the FIXTURE is the lesson.** `verify_twist_manual.py` first built every
bone along +X on both sides, so it could not see a control placed by assuming
+X. **A fixture more symmetric than the skeleton proves nothing about the
skeleton.** It now carries Manny's actual signs and gates that all eight
controls sit at t = +0.5 **and** that the two sides really do run down
opposite signs, so the gate cannot pass by accident. A first version of the
sense gate then failed on correct code by assuming the other convention (that
setting the ring to the network's own roll reading reproduces the automatic
term); it was replaced by the mirror invariant, which is what the toolset
actually promises.

Proof: `verify_twist_manual.py` — **green 2026-09-03, 0 of 88 gates failed**.
It runs a REAL `twist.build` in **mayapy standalone on a skeleton it builds
itself**, never in the animator's scene: this feature creates rings, attributes
and nodes, and a read-only walk cannot prove any of it, while building for real
beside the animator's rig is what `verify_two_characters.py` refuses to do.
Measured: the counter distribution exactly **−20.000000 / −10.000000** for a
+30 ring, follow **+10.000000 / +20.000000**, `autoTwist` 0 removing the
automatic contribution to **0.000000000** while the ring still drives
(−10.000000), the refused joint **not following its driver's 300° roll (range
0.000000000)** against a control that the left joint does follow (40.000000),
and the bake reproducing every sampled frame to **0.000000000** while removing
198 nodes and all eight rings. Two fixture lessons from getting it green, both
CLAUDE.md's own in miniature: expectations are **computed from the geometry the
run measured** (a hand-written +1/3 failed on correct code once the fixture's
forearm was 24 long, not 30), and `node_names` must be asked for the **real
prefixed path** — the first version asked for unprefixed names that do not
exist either way, so the gate "no automatic chain was created" **could not
fail**. Three positive controls were added for exactly that reason.
**`mayapy` standalone does not auto-load `matrixNodes`/`quatNodes`**, so
`quatNormalize` comes back an unknown node type and the wiring dies on a
missing destination attribute; interactive Maya loads them, which is why the
module needs no guard.

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
52. **`quatToEuler` wraps into (−180°, +180°] and `decomposeMatrix` throws
    the long way away before it, so a stock-node roll network cannot pass
    180° — and it fails as a WHIP, not as an error.** Measured in isolation
    2026-09-03: feed the pipeline a 190° twist as `(sin 95°, cos 95°)` and
    it answers **−170°**; feed 350° and it answers **−10°**; the
    discontinuities sit at exactly ±180°. `quatNormalize` in front is
    innocent — it passes `x` and `w` through element for element. And
    `decomposeMatrix.outputQuat` canonicalises the sign, so a >180° delta is
    already re-expressed the short way when our nodes see it: **there is
    nothing downstream to recover.** In `maya_overrig/twist.py` that turned
    a genuinely unbounded quantity into a 223.50° single-frame whip on a
    twist joint, silently — and `verify_twist_bones.py` was green on 30
    gates because its largest test roll is **170°**, ten degrees short of
    the cliff. Two lessons beyond the nodes. A gate whose extreme stops just
    inside a boundary proves the boundary is never crossed, not that
    crossing it is handled. And when a DG network's output is a BOUNDED
    reading of an UNBOUNDED quantity, the build must measure the range and
    refuse, because the runtime cannot.

53. **`__file__` does not exist in a file the command port runs**, and a
    runner that derives its own directory from it dies before writing its
    marker — no marker, no output file, Maya's CPU flat. Every symptom of a
    blocked idle queue (notes 6/7/8) with a healthy Maya and a correct
    script on the other end. Trap 17's family: `exec(open(path).read())`
    hands the file's TEXT to a namespace that has neither `__file__` nor a
    module of its own. Hardcode the path in the runner, and pass `__file__`
    explicitly in the globals dict it exec's the payload with.
54. **Qt's `WA_TransparentForMouseEvents` does not cross a native-window
    boundary.** It is a routing flag *inside* Qt: the event goes to the
    widget below in the SAME window, and for a top-level window "below" is
    another native window Qt will not forward to. Measured on a translucent
    overlay over Maya's viewport: no marquee, no camera orbit, the events
    simply died in our window. On Windows the mechanism that does work is
    `WS_EX_LAYERED | WS_EX_TRANSPARENT` via ctypes, set **after `show()`**
    (re-parenting recreates the native window and drops it), after which
    `WindowFromPoint` stops answering our window and `alt`+LMB orbits the
    camera straight through. `WindowFromPoint` is also the hands-free test:
    the docs say it skips a `WS_EX_TRANSPARENT` window, which is the same
    decision a real click takes.
55. **`MGlobal.selectFromScreen`'s CLICK form of `kXORWithList` is a
    no-op, while its BOX form toggles correctly.** Measured from both
    starting states: from an empty selection the click form selects
    nothing, from a held one it changes nothing. So a shift-click routed
    through the API's own adjustment silently does nothing — the animator
    shift-clicks, sees no change, and blames their aim. `kReplaceList` is
    the one value measured to behave identically in both forms: pick with
    that and apply the modifier yourself with `cmds.select(... add / toggle
    / deselect)`.
56. **Maya's pick runs through the viewport's own DRAW pass**, so a node
    that has never been drawn cannot be selected from screen. A locator
    created and immediately picked at screen centre returned nothing at all
    under every listAdjustment — which reads exactly like a broken
    adjustment table and cost a whole probe round to separate. Trap 14's
    family, from the selection side: `cmds.refresh()` before any scripted
    pick of something just created.
57. **`repaint()` is a no-op while a bridge script holds the main thread**,
    because the Qt event loop never turns and the window has never been
    exposed — measured, `paint_count` stayed 0 on a window that was up and
    visibly correct. `widget.render(QImage)` forces `paintEvent`
    synchronously, and counting the non-zero bytes it leaves is the gate
    worth having: it proves ink, not merely that a handler ran. And
    **`cutKey(clear=True)` answers 0 even when it worked**, so a status line
    built on its return value reports "Deleted 0 key(s)" over keys it has
    just removed — count the selection before the cut.


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
| `animexport.py` | FBX export of the skeleton hierarchy, bake-on-export, range policy; `LAYOUT` / `UNREAL_LAYOUT` | `maya.cmds`, `maya.mel`, `animimport`, `fbxlayout` |
| `fbxlayout.py` | **Cascadeur's layout for the length of an export** (2026-09-25): the wrapper `Armature` (`WRAPPER_NAME`), `root` at zero, restored by UUID; a legacy tag held out of the file | `maya.cmds`, OpenMaya (lazy) |
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

80. **…and the importer switches it anyway.** Measured 2026-09-24 in mayapy: a
    scene at `film` (24), `FBXImportSetMayaFrameRate -q` answering 0, and one
    `FBXImport` of a 30 fps UE clip later (bare, or through
    `animimport.import_clip`) the scene reads `ntsc`, the keys on whole
    frames 0..71. So a clip round trip through the bridge lands at 30 by the
    plugin's doing, not ours. Meanwhile a scene that never imported a clip
    (Add Character, animate, export) exports at ITS rate: our exports write the
    scene's time unit (`animexport`, measured "cinema 24"). The Atone project
    is 30 fps (465 of 525 clips in the bridge cache, 15 at 60), and so are the
    Creep's Cascadeur sources. The animator's Maya opened new scenes at 24 that
    day. Importing a `.ma` does not change the scene's rate (measured, both
    ways); opening one does. The Creep assets' headers say `film`, Manny's
    `ntsc`. The axes need nothing: Maya Y-up cm, our FBX Y-up scale 1.0, the
    root's −90° X jointOrient carrying UE's Z-up. Our exports match Unreal's
    own in root space (Manny's pelvis `(0, −2.281, 95.897)` in both). Every rig
    faces +Z with its left on +X, exactly as Unreal's exported UE4_Mannequin
    imports.

**Exports in Cascadeur's layout (2026-09-25).** The animator moves animation Maya ⇄
Cascadeur («перенос анимации» was the pain, asked). Of three ways they chose ONE layout for
every export, Cascadeur's own, with the wrapper named for the character («по персонажу») — and
the same evening **`Armature`** for every character («появилось требование чтобы верхняя группа
называлась Armature»; see "The wrapper is `Armature`, and one shader" below).
Spec: `docs/superpowers/specs/2026-09-25-cascadeur-export-layout-design.md`; plan beside it.

**Measured first:**
- Unreal's clip, Cascadeur's clip and ours agree bone for bone below `root`. They differ only
  in where the Z-up → Y-up −90° X lives:
  - Unreal: a Z-up file with `root` at identity;
  - Cascadeur: a Y-up file with a Null (`SKM_Manny_Simple`) at −90 X, `root` at zero beneath it,
    its translation in the Null's Z-up space;
  - ours: `root` at world level carrying the −90 as its jointOrient.
- **Cascadeur → Maya already worked**, measured on `creep_attack_forward.fbx`: import, retarget
  onto a Creep_Rig, export. Root 8e-10, every bone 0.0006°, limbs pointing 0.025°. The twist
  bones are up to 58° off: AdvancedSkeleton spreads the arm roll its own way. That is not an
  axis matter and is left for the retarget.
- **`FBXExportUpAxis z` is no shortcut** (trap 81 below).
- **Z-up Maya was rejected**:
  - AdvancedSkeleton's author advises against it in `AdvancedSkeleton.mel` («Highly recommended
    to Stay with Maya Y-Up axis»); the toggle is commented out in 6.797 and its MoCap Library
    errors under Z-up;
  - Unreal is left-handed, so one axis would still differ in sign.

**`maya_uebridge/fbxlayout.py`** (cmds; OpenMaya imported lazily because the bridge's tests fake
`maya`). For the length of an export it:
1. frees the name: anything answering to it is held as `rpHold_` (a node of the animator's
   called `Armature`; in the morning's per-character naming, the Creep skeleton's `|Creep` group);
2. creates the Null `Armature` (`WRAPPER_NAME`) at −90 X;
3. re-parents `root` under it with `relative=True`;
4. gives `root` the jointOrient `JO · W⁻¹` (`jo_after`; zero for our −90), and its translate
   `(x, −z, y)`. That step follows `layout_plan` (pure):
   - **constrained** (the rig's `root ← Main`): nothing more, the constraint re-solves under the
     new parent;
   - **keyed**: the curves are routed through a negating multDoubleLinear, no key edited;
   - **static**: the values are rewritten and written back after;
   - **anything else** (a pairBlend, keys plus a constraint, a root already parented): the
     plain file, with a note.

Everything goes back by UUID in a `finally`.

**The name** was the character's that morning (`wrapper_name`: the root's `skeldarCharacter` tag
Add Character wrote, else the rig namespace, else the skins' colour key, through
`catalog.export_name`) and is **`Armature`** for everyone since the evening; the naming, the tag's
writer and `export_name` are gone, `tag_held` stays for roots tagged that one day.

**Where it is on:**
- `export_hierarchy(..., layout=LAYOUT)` defaults to `"cascadeur"`: Export FBX… and the
  no-checkout save-as.
- **Export to uasset and the checkouts' EXPORT follow `animexport.UNREAL_LAYOUT = "plain"`**
  until `verify_cascadeur_layout_unreal.py` has seen Unreal read the wrapped file as it reads
  the plain one. It has NOT run: the editor's Remote Execution (UDP 6766) was not listening
  after a restart. One word flips both.
- `export_creep_skeleton_fbx.py` writes the Creep's skeletal mesh the same way: the meshes at
  world level beside the Null, as Cascadeur's file has them. The bind pose is saved again over
  the Null too (trap 79 again: «Unable to find the bind pose for : / Creep»). The result is
  root `(0.002, −2.401, 0)` under `Armature` at −90, Cascadeur's own numbers, and ONE material.

**Proof:**
- `verify_cascadeur_layout.py` — **9/9 standalone**:
  - root LOCAL values against Cascadeur's own file 1.5e-6 cm and 0.0000°, other bones 0.0006°;
  - a keyed skeleton, with the `|Creep` group held and restored;
  - a static skeleton (root `(0.0017, −2.4012, 0)` in the file);
  - Manny_Rig → `Manny`;
  - a pairBlend root → plain with a note;
  - `layout="plain"`;
  - every case leaving the scene exact: no node added or lost, the same connections,
    jointOrient and names.
- 2252 unit tests.
- **The skeletal mesh against the file Cascadeur itself wrote for this creature** (2026-09-25,
  the animator: «экспорт персонажа creep с группой по новому пайплайну, чтобы в каскадере всё было
  хорошо и его не переворачивало»; Cascadeur is not installed here):
  `verify_creep_skeleton_fbx_cascadeur.py` — **5/5 standalone**, against `Downloads/creep_T-pose_draft
  (1).fbx` (Cascadeur 2024.1; its frame 0 is the Creep's bind pose):
  - the header, read from each file: +Y up, +Z front, +X coord, unit 1, both;
  - in the file: `Creep` at −90 X holds `root` at Cascadeur's `(0.0017, −2.4012, 0)`, the meshes at the
    top unturned and unscaled, like Cascadeur's (it writes its own Null as −89.99998, float noise);
    `Creep_Face` keeps the model's pivot `(0, 6.058, 0)`, which the animator's own Maya file of the
    creature (`creep_T-pose_draft2.fbx`) has too and Cascadeur's bakes to 0;
  - imported alike: 85 bones where Cascadeur has them at frame 0 to 2e-6 cm and 0.00000°, all 70738
    vertices to 9.5e-5 cm;
  - named, not gated: the five IK helpers stand by the Creep's own rules (`ik_hand_gun` at zero,
    `ik_hand_r/_l` on the hands, `ik_foot_*` by the feet), and Cascadeur's file never took them into
    its pose (54 / 7.4 cm off); `weapon_r` is in place, turned 46.5° in the hand from Cascadeur's
    `weapon_test` (which Cascadeur's file holds turned (0.2, 46.1, −6.3)° at frame 0; the Creep Sword's
    frame (0, 45, 0) was dialled to it by eye);
  - a control: Cascadeur's Null at +90, the flip, reads 335 cm.

Two things found on the way:
- **deleting a node takes the animCurves feeding it** (the negate node took `root_translateZ`
  along: let a temporary node's inputs go first);
- **the exporter writes our `skeldarCharacter` tag into the file** as a property of `root`,
  which Unreal would read as root data (trap 40). `fbxlayout.tag_held` takes it off for the
  length of every export.

**The wrapper is `Armature`, and one shader on every model (2026-09-25, evening).** The
animator: «Появилось требование чтобы верхняя группа называлась Armature. Еще нужно на все наши
модели и риги настроить единый шейдер. Такой чтобы он смотрелся хорошо в мае и в каскадере. Сейчас
при экспорте в каскадер модель выглядит темной и на модели много материалов» — then away for an
hour («сделай все самостоятельно»), so every choice here was taken alone and is in the spec
`docs/superpowers/specs/2026-09-25-armature-and-one-shader-design.md`.
- **`fbxlayout.WRAPPER_NAME = "Armature"`** for every export (`animexport`, the Creep skeletal-mesh
  script). The per-character naming is deleted with its only users.
- **Measured before choosing the shader**: the assets were a patchwork (the Creep's arms and face a
  0.5 grey blinn at diffuse 0.8, its back red, its body NO material; the Orc five per-face
  materials; Manny's skeleton MaterialX; 8–15 unworn materials per file, textures on `E:\work\...`),
  and the skeletal-mesh FBX sent to Cascadeur carried three materials, each with DiffuseFactor 0.8,
  SpecularColor 0.5 and ReflectionFactor 0.5. Cascadeur's own FBX of the creature carries phongs
  at full colour, Specular 0.2, Shininess 20, Reflectivity 0. Its viewport is PBR and the FBX →
  PBR mapping is C++ (none of its Python).
- **The one shader = that material**: `colour.SHADER = "phong"` wearing `colour.LOOK` (diffuse 1,
  specularColor 0.2, cosinePower 20, reflectivity 0), applied by `colour.dress` inside
  `make_material` — so Add Character, Add Weapon and any fresh Recolour make it. A phong's
  cosinePower is FBX's ShininessExponent: the numbers land in the file unconverted. The colours per
  character stay (one shader TYPE and look, one material per character); a whole-shape
  `forceElement` replaces a per-face assignment (the Orc's five sets become one). Asset files were
  NOT rewritten (Add repaints them anyway; Manny's `.ma` cannot be resaved without mtoa/USD/MaterialX).
  Old scenes keep their blinns until a re-Add.
- `export_creep_skeleton_fbx.py` paints the five meshes with one `Creep_Mat` in 0.8 grey
  (Cascadeur's default base colour), its marker removed.
- Proof: `verify_one_shader.py` **4/4 standalone** (all six characters and four weapons wear one
  material of the shader; an artist's own FBX of the Orc's meshes carries one phong with
  Cascadeur's numbers; the animation export's top node is `Armature`);
  `verify_creep_skeleton_fbx_cascadeur.py` **6/6** (gate 6: one material in the file on all five
  meshes, specular/shininess/reflectivity equal to Cascadeur's own body material);
  `verify_cascadeur_layout.py` **9/9**; 2249 unit tests.
- **Seen in Cascadeur itself, 2026-09-28** (its script server, menu **Scripts → MCP → Start script
  server**, 127.0.0.1:8765; each file imported into a tab of its own, the window photographed with
  Win32 `PrintWindow`). `Creep_Skeleton.fbx`: `Armature` at the top, the character standing (pelvis
  Y 95.9, head 167.8, foot 8.2, left on +X), ONE `Creep_Mat` read as base 0.8, roughness 0.8,
  reflectance 0. The export before (three materials) came in at base 0.5 × factor 0.8 on the arms
  and face, red on the back, FBX's `Default_Material` on the body — **dark on screen, next to ours
  light**: that was the complaint. **metallic 0.5 and ambient occlusion 0.5 are Cascadeur's importer
  constants** — the same for a blinn, our phong, a material-less mesh and Cascadeur's own FBX of the
  creature; nothing in a file moves them. Roughness follows the file (phong spec 0.2 → 0.8, blinn
  → 0.937, none → 0.75). Its viewport shows materials only with textures on (`MeshObject.
  always_show_textures`; off, even a red handle draws clay grey). Cascadeur's own file looks more
  detailed because it EMBEDS textures — per group a diffuse (dark brown scans) and a normal map,
  2048², six images — and Cascadeur draws the normal maps; ours carry none. Not the smoothing
  groups (an export without them looked the same) and not the normals (both files' normals sit on
  their surfaces alike: arm median 0.68° against 0.72°, p90 26° against 27°, same polygon order).
  And the file is at **30 fps** since (`export_creep_skeleton_fbx.py`; TimeMode 6, Cascadeur's own):
  at the asset's 24 Cascadeur warned «Incompatible fps. Scene: 30, fbx: 24» on every import.
  `verify_creep_skeleton_fbx_cascadeur.py` **6/6** with the time mode in gate 1.

81. **`FBXExportUpAxis z` writes a Z-up HEADER and leaves the turn on `root`.** Measured
    2026-09-25 on our Y-up skeleton: the file declares up +Z, front −Y (Unreal's header), but
    `root` carries PreRotation +90 X, not Unreal's identity. Read back into a Y-up Maya, the
    joints stood **169 units** off. It is not Unreal's layout, and it is not a round trip.
    Moving the turn into the file's hierarchy (fbxlayout) is.

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
| `colour.py` | the palette, which colour is free, our blinn and who wears it, a character's meshes | `maya.cmds` (a leaf) |
| `character.py` | the working character into the current scene: import, the rename note, connecting it, the malware sweep | `maya.cmds`, `catalog`, `colour`, `builder` + `picker_window` (both lazy) |
| `skeleton.py` | which character — and it becomes the ACTIVE one — and where its weapon bone is | `maya.cmds`, `maya_overrig` |
| `bonedrive.py` | a bone that follows a marked node: `link`/`unlink`/`relink`, grip-space composition (a weapon's own `FRAME_ROTATE` under the grip, 2026-09-24), range policy; owns `MARKER` | `maya.cmds`, OpenMaya (a leaf — the bridge imports it lazily) |
| `weaponspace.py` | the hand's weapon space OUTSIDE the skeleton (2026-09-24): make, find from the hand, prune; which hand holds a weapon | `maya.cmds`, `maya_rigs` (a leaf) |
| `attach.py` | find the mesh, parent it into the hand's weapon space, invert the drive, read/write offsets | `maya.cmds`, `bonedrive`, `colour`, `fbximport`, `weaponspace` |
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
`verify_add_character.py` and three test modules ask that
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

**Every character and every weapon arrives in its own COLOUR** (2026-09-03,
the animator's ask: «нужно добавить опцию выбора цвета для персонажа и
оружия которого мы добавляем в сцену. Я предлагаю при добавлении в сцену
задавать новый материал и назначать ему указаный цвет»). Two Mannys in one
scene were indistinguishable in the viewport — the outliner can tell `root`
from `Manny_Skeleton_root` and the eye cannot. So each press creates one
**blinn** and assigns it to every mesh it brought. `maya_scenesetup/colour.py`.
Spec: `docs/superpowers/specs/2026-09-03-scene-colour-design.md` — read its
ADDENDUM, which reverses two of the main text's decisions the same day.
Proof: `verify_scenesetup_colour.py` — **green live 2026-09-03, 0 of 32
gates failed**, in four phases (a sandbox, two real Add presses, the weapon,
and the panel itself).

- **blinn, not lambert** («у него лучше шейдинг и он блестит»): a lambert is
  flat, so a coloured figure lost the form the grey one had. `colour.SHADER`,
  one constant, specular attributes left at Maya's defaults — the ask was for
  the shine and the defaults give it. **A file coloured earlier keeps its
  lamberts**: `is_ours` asks for the marker and knows nothing about the node
  type, so `paint` reuses what is there rather than swapping a material out
  from under an assignment the animator may have tuned.
- **The swatch is the colour of the NEXT Add** («цвет будем задавать перед
  созданием персонажа или оружия в сцене»), and a **Recolour** button beside
  it puts that colour on the connected character / attached weapon. One
  meaning per control. The first build had the swatch show the connected
  character and repaint on change; the animator reversed it after using it —
  and the tell is still in their scene, a `skeldarColour_red` **lambert**
  on their own Manny from the afternoon they tried the slider.
- **`refresh` must never touch a swatch, and that is the one bug this shape
  can have.** It fires on every dropdown change and at the front of every
  press, so a write there discards the colour the animator picked a second
  earlier. The swatches are filled on open and advanced after each press
  (`_advance_swatch`). A unit test strips the comments out of `refresh` and
  asserts it calls neither setter; live gate 27 sets a colour, calls
  `refresh` and measures the swatch still holding it.

- **Identity by attribute**: the lambert carries `skeldarColour` with the
  owner's key, and every lookup asks for that. The name (`skeldarColour_red`)
  is for the Hypershade and is never searched for — Maya uniquifies it to
  `...red1` on the second character, which is exactly what happened in the
  live run.
- **The free colour is read from the SCENE**, not from a counter: eight named
  hues, `next_colour` (pure) takes the first not already worn. A counter is
  right until the animator opens another file or deletes a character.
  Character and weapon share one scan, so a sword in an amber character's
  hand came out orange (measured).
- **An unassigned material stops counting** (`is_assigned`). Replacing a
  weapon deletes its geometry and leaves the lambert behind, as any Maya
  delete does; without this rule a re-Added sword walks down the palette on
  every press. Nothing is deleted — chasing shading nodes is how a tool
  eventually deletes something the animator wanted.
- **Add reads the swatch, and the swatch is refilled with the next free
  colour after every press** — so choosing is optional and two presses in a
  row still never collide. Gate 30 sets it to teal and measures the arriving
  character wearing teal to 0.000000012.
- **A character's meshes are found through the skinCluster**, not the DAG.
  Manny's meshes sit at WORLD level, so a walk down from `root` finds
  **zero** (measured, gate 18). Identity by connection; the DAG walk stays in
  the union for unskinned geometry parented in by hand. At Add time neither
  is used — the import's own node list is exact.
- **`cmds.skinCluster(query=True, geometry=True)` answers with SHORT names**
  — measured: `['Hands_1PShape']`, not a path. Trap 28 from a new side, and
  the next thing that happens to those shapes is a `forceElement`, so a name
  resolving to several nodes would repaint somebody else's character. Maya
  hands back the shortest UNIQUE name, so one path is what normally comes
  out; `colour.unambiguous` drops anything that does not, because skipping is
  the safe direction of failure.
- **A gate asserting the animator's own character is UNPAINTED fails on a
  correct run** — they use this tool, and theirs is already red. Gate 29
  compares before against after (`red -> red`) instead.
- **Manny's "6 meshes" are six mesh SHAPES and only TWO are renderable** —
  `Hands_1P` and `Skin_3p`, each with its own `...Orig` intermediates from
  the skinCluster and blendshape history (measured 2026-09-03). The status
  line has always counted shapes. A gate written as `>= 6` fails on correct
  code, and did.
- The asset's own materials are **not deleted**, only unassigned, so a hand
  re-assignment in Hypershade brings the original look back. A checkbox to
  skip the colouring and a "restore the original material" button were both
  offered and declined: «нет, красим всегда». `grey_black_materials` stays —
  the colour is an assignment, the grey is a fix to the asset's own material.
- Nothing downstream is touched: `animexport` runs `FBXExportSkins false` and
  `FBXExportShapes false`, so no material of ours can reach Unreal, and no
  part of `maya_overrig` reads a material.

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

**The spear is the second catalog weapon** (2026-09-08, «в открытой сцене
есть Spear1 … добавить в список так же как и sword … выровнять оси этой
модели чтобы совпадали с осями sword»). `assets/Spear_01.fbx` was exported
over the command port from a **duplicate** of the animator's `Spear1` (a
3ds Max export, 266 cm, identity transform, pivot at the origin; the
original never touched, the duplicate and its temp material deleted, the
selection put back). Measured before turning it: the head at **−X** (the
blade 15–22 cm wide in Z and 4 cm thin in Y out to x = −206.7), the butt cap
at +X (+59.4), the origin on the shaft 59 cm above the butt. The sword's
frame is the blade along **+Y** with the tip at +Y, the crossguard on X, the
thickness on Z — so the duplicate took the rotation **spear −X → +Y, spear
Z → X, spear Y → −Z** (det +1; Y → +Z would have been a mirror) and was
frozen, and imports back as `SpearMesh` at **X ±10.91, Y −59.4..206.7,
Z ±6.63**. **The origin's HEIGHT along the shaft stays where the model's
author put it** (Add puts it on `weapon_r` and the grip fields dial the
rest, as with the sword), but **transversely the shaft is centred on the
origin**: after the turn the butt cap's centroid sat **3.81 cm** off the Y
axis (the author's pivot is the 3ds Max scene origin, beside the shaft),
while the sword's origin is on its own axis (X ±15.58, Z ±1.57), so the mesh
was shifted by that centroid before freezing — the first export skipped
this and the verify's axis gate caught it (both end centroids 3.81 off).
`catalog._asset_path(name, legacy)` generalises `_sword_path`; the row is
`Weapon("Spear_01", "Spear 01", ..., "weapon_r", 1.0)`. Spec:
`docs/superpowers/specs/2026-09-08-spear-weapon-design.md`. Proof:
`verify_spear_weapon.py` — **green 2026-09-08, 0 of 15 gates failed**, in
mayapy standalone: both files' frames measured in one run and compared
(longest axis Y, tip +Y, width X, thickness Z for both), `aim.placement` on
+Y for both, a real Add landing the spear under the hand driving `weapon_r`
at **0.000000** at the zero grip, and the sword replacing it. One gate
lesson: a "vertices within the shaft's radius" test measured the head base
and the butt cap (7–14 cm off-axis by design) and failed on a correct model;
the axis question is answered by the two end centroids, both within 3 cm.

**The dagger is the third** (2026-09-17, «по аналогии с мечем и копьем
нужно добавить нож»): `assets/Dagger_01.fbx`, written from the animator's
`Animations/Sources/Dagger.fbx` by the re-runnable
`docs/superpowers/plans/make_dagger_asset.py` in mayapy standalone (the
source never written). Measured: one mesh, 7292 vertices, long axis **Z**
(114.3 cm, −84.2..+30.0) with the **tip at −Z**, the blade 8–21 cm wide in
Y and 1–2 cm thin in X, the guard at −27..+1.5, the grip +1.5..+20, the
pommel to +30 — the origin between guard and grip, where the sword's is.
The turn **Z → −Y, Y → −X, X → +Z** (det +1; Y → +X would be a mirror)
puts the tip at +Y and the grip at −Y like the sword's; the grip's centroid
(x −0.444, z −0.172 after the turn) is shifted onto the axis (0.0000);
frozen, a plain lambert in place of the source's untextured
`openPBRSurface` (a node type not every Maya has), exported as
`DaggerMesh`. Read back **X −12.60..12.04, Y −30.02..84.24, Z ±2.85**.
**The model is 114 cm; the row's scale is 0.4** («в два с половиной раза
меньше», the animator's call minutes after seeing it at 1.0) — the asset
untouched, `attach.seat` writes the catalog scale onto the mesh's scale
channel, which `bonedrive` never touches. Spec:
`docs/superpowers/specs/2026-09-17-dagger-weapon-design.md`. Proof:
`verify_dagger_weapon.py` — **green 2026-09-17, 0 of 16 gates failed**,
in mayapy standalone: the frame compared against the sword's in the same
run, both grips' centroids on the axis to 0.0000, `aim.placement` on +Y
for both, a real Add landing the dagger on `weapon_r` at **0.000000** with
scale 0.4 and the blade **45.71 cm** along its own axis in the hand, the
sword replacing it. The live dropdown lists all three.

**Spear 03 is the first weapon that arrives in its TEXTURE** (2026-09-28,
the animator, with `Downloads/Spear_03.fbx` + `Halberd_A.tga`: «это должно
выдаваться сразу с текстурой»). Spec:
`docs/superpowers/specs/2026-09-28-spear03-textured-weapon-design.md`.
Measured: a Blender FBX from a Unity project, LOD0 (230 vertices) + LOD1, 199.6
cm along +Y, head at +Y but its width on **Z**, the butt ON the origin, a phong
whose file node points at a `D:\Unity_Project\...` path, the UV set `UVКарта`
(Maya shows `UV?????`); the TGA 2048², 24-bit, no alpha, 12.6 MB. The animator
chose the grip **at Spear 01's fraction of the length** (0.2233, measured on
`Spear_01.fbx` in the script's own run) and **Recolour replaces the texture
with a colour** (one meaning per control; the next Add brings it back).
`make_spear03_asset.py` (standalone): LOD0 alone, a quarter turn about +Y,
the origin up to the grip, UV set `map1`, a plain lambert, and the TGA as
**`assets/Spear_03.png`** (6.7 MB, pixel-for-pixel). **`catalog.Weapon`
gained `texture`** (default ""; `missing()` names a missing image);
**`colour.paint_texture`** dresses the shapes in the one shader wearing LOOK
with a colour-managed file node (place2dTexture wired as Hypershade wires
it) on `.color`, marked **`skeldarTexture`** = the image — never
`skeldarColour`, so the palette scan does not count it and `paint`'s reuse
path (a `setAttr` on `.color`) never finds it; the same image's material is
reused on the next Add. **Weapons > Add** says «textured», leaves the swatch,
and turns **Textures on in every model panel** where they are off, saying so
(«textured (viewport textures on)»). Proof: `verify_spear03_weapon.py` **19/19
standalone** (the frame and the grip fraction against Spear 01 in the same
run, the PNG = the TGA, on weapon_r at zero grip 4.8e-7, the file node's
samples at six texel centres equal to the PNG's pixels to **0.0000** — the
rows flipped read 0.43, so an upside-down image cannot pass — outside the
palette, Recolour over it, the second Add on the same material with one file
node, the sword replacing it); the real Weapons > Add in a disposable Maya
(textures turned on in all four panels, the playblast showing a wood shaft
and a steel head); 2330 unit tests.

87. **`MImage.pixels()` answers an ADDRESS and `MImage.getSize()` a LIST.**
    `bytes(image.pixels())` is a MemoryError (an int that size), and
    `image.getSize() == (w, h)` is always False — which, short-circuiting,
    made a first "the PNG equals the TGA" check report False without ever
    comparing a pixel. `ctypes.string_at(image.pixels(), w * h *
    image.depth())` is the buffer.
88. **`cmds.getPanel(visiblePanels=True)` can answer None with a model panel
    up and focused** (a GUI Maya launched to the background, measured
    2026-09-28). A viewport setting meant to be seen goes through
    `getPanel(type="modelPanel")`; the visible-only version turned nothing on.

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

## `maya_overshoot` — the stop of a move, on any pose

**Off the shelf since 2026-09-08** («уберем с нашей полки оверлапер»),
behind `skeldar_features.OVERSHOOT` exactly as the picker is behind
`PICKER`: the module ships, its button and its six hotkey rows come back
with the flag.

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

## `maya_vpstudio` — Viewport Studio: a juicy real-time picture on one press

Shipped single-file tool (2026-09-03, `SkeldarAnim/maya_vpstudio.py`, `cmds`
only, no Qt), the **seventh shelf button** — the animator's ask: «скрипт
который по нажатию будет автоматически настраивать красивый рендер во
вьюпорте который будет работать в реальном времени … студийное освещение,
тени, амбиент аклюжен, моушен блур, пол геометрией». Spec:
`docs/superpowers/specs/2026-09-03-viewport-studio-design.md`. Proof:
`docs/superpowers/plans/verify_vpstudio.py` — **green live 2026-09-03, 0 of
101 gates failed**, plus 16 panel gates driving the real buttons. Two gate
lessons from it, both CLAUDE.md note 4 in miniature: the AO gate asserted
a literal `18` and failed on correct code when the animator swapped what
was in the scene mid-session (the subject became 257 cm and the tool
correctly computed 26), so expectations are COMPUTED from the frame the
run measured; and the entry state must be captured AFTER clearing a studio
an earlier run left standing, or the leftover rig's own settings get
recorded as "what the animator had".

```python
import sys; sys.path.append(r"C:/!!!Work/MayaScripts/SkeldarAnim")
import maya_vpstudio; maya_vpstudio.show_window()
```

One press builds a **look** — picked from a dropdown, `Studio` or
`Outdoor` (added the same day: «давай сделаем еще присет для уличного…
чтобы я мог выбрать присеты из выпадающего списка») — plus a **floor**
(polyPlane + blinn, receives shadows, casts none, reference display so it
stays out of a marquee select) and the whole Viewport 2.0 set: AO,
multisample AA, motion blur, bloom, depth-peeled transparency, all lights,
shadows, grid off, light icons off, a backdrop. **Measured: 8.1 ms/frame —
123 fps — at Good quality on two skinned Mannys** (Fast 147, Beauty 87).

**A look is a BUNDLE, not a light table** (`LOOKS`): the lights, the
floor's colour and roughness, the backdrop, the shadow filter size and the
bloom amount — everything that reads differently between a dark stage and
a sunny day. So a third look is a row in that table, not a branch. Studio
is five lights (warm **key** spot with a depth-map shadow, cool **fill**
directional, **rim** spot, **bounce** from below, a breath of
**ambient**); Outdoor is four, and **the kinds change rather than the
numbers**: one hard parallel **`sun`** (directional — a spot sun lights a
pool on the ground and reads as a stadium floodlight), a **`sky`** ambient
three times the studio's, which is what fills the sun's shadows and why
they read blue, a **`skylight`** giving that dome a direction, and a warm
ground **`bounce`**.

**The sun's shadow map is focused BY HAND, and that is what the
directional sun costs.** A directional has no cone to bound its depth map
and `useDmapAutoFocus` fits it to the whole scene — which includes a floor
twenty radii across: measured live, 2048 texels over a 5575 cm floor is
2.7 cm/texel and the shadow is mush. With auto-focus off and
`dmapWidthFocus` at 2.6 radii the same map covers 725 cm at **0.35
cm/texel**. Spots never get it — their map already covers the cone, and
the two levers would fight.

**Picking a look applies it at once**, and it REBUILDS rather than retunes
(a different look is different lights, floor and sky). Two consequences
that each have a test: **the dropdowns are wired up only after the window
is built** — setting an `optionMenu`'s value fires its `changeCommand`, so
restoring the remembered look during the build would rebuild the whole
studio just from opening the panel — and **the dials read the look off the
GROUP, never off the dropdown**, since `retune` scales from each spec's
base intensity and must use the table these very lights came from
(Outdoor standing + dropdown flipped to Studio would scale the sun off the
studio key). `retune` writes the standing look back, not the dropdown's,
or the next retune inherits the lie.

**It is reversible, and the memory lives on our own group.**
`hardwareRenderingGlobals` is a scene node and the panel flags are the
animator's, so what the press overwrites is captured first and stored as
JSON on `VPStudio` (`skeldarVpStudioState`). **The capture happens only on
the press that finds no rig** — a second press carries the FIRST press's
memory forward, or Restore hands back our own studio as if it were theirs.
That is the most breakable thing in the tool and it has a unit test and a
live gate.

**Everything is measured, nothing tabulated in centimetres.** The light
table is in subject RADII and degrees (`radius` = half the bbox diagonal,
the one measure that does not collapse on a flat subject), and the AO
radius is 10% of the subject's height — 16 cm reads as contact shadow on a
180 cm character and as nothing on a 20 m one. **Our own floor is excluded
from the measurement**, or every press measures the last press's floor and
the studio walks off to infinity. **The azimuth comes from the viewing
camera**, so nothing has to guess which way a character faces, and the
Rotate dial spins the rig as one attribute on one pivot. Identity is by
attribute (`skeldarVpStudio`) with a `{light: UUID}` index
(`skeldarVpStudioLights`) for the dials; deletion is by UUID with existence
re-checked in front of each one (trap 18). **The selection is deliberately
ignored** — `hand_r` owns the sword mesh, and Manny's body meshes are not
under his skeleton at all, so "light what is selected" would light a 40 cm
sword.

Five things measured on the way, each of which cost something:

- **A bare attribute name in a plug-writer fails SILENTLY.**
  `render_settings` returns `ssaoEnable`, `apply_plugs` needs
  `hardwareRenderingGlobals.ssaoEnable`, and `objExists` on the former is
  False — so every render setting was dropped and the studio came out with
  no AO, no AA, no motion blur and no bloom, looking entirely plausible.
  **Two screenshots were judged by eye in that state.** Hence
  `render_plugs`, `_setup` counting its writes and naming the shortfall,
  and a gate comparing every planned setting against the scene (trap 48).
- **`playblast` ignores the background gradient** and renders from the flat
  `background` colour, so the tool sets all three — an animator reviews on
  playblasts.
- **A playblast PNG carries alpha and a transparent background reads as
  white.** Three shots were mis-read as "the backdrop is not applying".
  Judge a viewport look in a format with no alpha channel.
- **Viewport 2.0 motion blur never reaches playblast output.** A cube
  crossing at 300 cm/frame came out crisp with blur on, at 8 and 16
  samples, single frame and over a sequence, offscreen and on-screen. It is
  an interactive-redraw effect: the attributes are proven set, the visual
  effect is confirmable only by a human scrubbing — the bridge cannot drive
  an interactive redraw, the same wall the hotkey map hit.
- **A Qt `widget.grab()` of a model panel captures the chrome and a blank
  white rectangle** where the GL surface is. CLAUDE.md note 3 is about Qt
  panels; a viewport is not one, and `playblast` is the way.

**Clean view is off by default** and unticking it puts the animator's own
flags back *from the saved state* rather than forcing them True — "clean
off" means "as they had it". The first version merely omitted those flags,
which left the rig invisible until Restore. Manipulators are never hidden:
an animator who cannot see the manipulator cannot animate.

**The window fits its content and can be stretched** (2026-09-17, the
animator: «окошко … не растягивается из-за чего кнопочки с применением
освещения не видно», then «такая же проблема в панеле в которой мы задаем
цвет»). Studio was `sizeable=False` at a hard `height=470` over a column
that measured **669 px** live; Colour the same at 260 over **361 px** —
Apply Look / Restore, and Next free colour / the taken line / the status,
sat below the edge with no way to drag them into view. The sizing is ONE
shared module, **`SkeldarAnim/maya_winfit.py`** (payload row; every
function takes the caller's `cmds`, because each tool's tests rebind its
own `cmds` to a fake): `forget_saved_size` drops the stale `windowPref`
(the saved clipped size, which Maya restores over the size the code asks
for) before the window is created; the window is `sizeable=True` with an
`adjustableColumn`; and `fit_window` sums the children's REAL heights
after `showWindow` (`fit_height`, pure) and writes them back in LOGICAL
units (`logical`, pure) because Maya scales every control for the
display. Measured after: Studio 716 px with the lowest control ending at
715, Colour 362 with 361. `tests/uifakes.FakeUiCmds` is the recording
`cmds` both panels' window tests run on. Overshoot still opens
`sizeable=False` at a fixed height (off the shelf, unmeasured). Two facts
cost a live run each:

64. **`cmds.control -q -height` answers PHYSICAL pixels while
    `cmds.window -e -height` takes LOGICAL units and Maya multiplies them
    by the display scale** — measured on a 150 % display: a `height=26`
    button queries as 40, `window -e -height 600` queries back as 900,
    and writing the measured 678 px sum straight back made a **1018 px**
    window. Divide by `cmds.mayaDpiSetting(q=True, realScaleValue=True)`
    (1.5 there; `scaleValue` answers 1.0 and is not it) before the write.
65. **A saved `windowPref` wins over the size a `cmds.window` creation
    asks for**, so a sizing fix never reaches a Maya that has opened the
    old panel once unless the pref is removed first
    (`windowPref(name, remove=True)`).

**Soft Studio, the third look, on a warm cyclorama** (2026-10-01, the animator: «еще одну схему
студийного освещения где свет будет распределен в 3 раза более широким пятном ... приятные теплые цвета
для подложки заднего фона (ее нужно сделать) ... спереди теплый свет сзади холодный»; asked: the backdrop is
a real photo-studio **cyclorama**, and only the new look gets it). Spec
`docs/superpowers/specs/2026-10-01-vpstudio-soft-studio-design.md` (read its addendum). `LOOKS["Soft Studio"]`,
third in the dropdown, Studio still the default. A look now also carries `spot` (penumbra/dropoff), `fog` and
`dmap_scale`, and its floor a `kind` (`plane` / `cyclorama`).
- **Three times the pool**: `cover` 5.1 / 4.5 (Studio's 1.7 / 1.5) at Studio's distances, so `tan(half)` is
  exactly 3× (key 126° against 66°, back lights 116°). The falloff widens with it: dropoff 1.3, penumbra 20,
  because at Studio's dropoff of 6 a 126° cone is dark past 40°. The key gets twice the quality's map (max
  4096) and filter 6.
- **Warm in front, cold behind**: the key, fill and bounce are warm, on the camera's side; the cold rim (2.6) and
  kicker (1.7) are behind on either side and outshine the key on purpose (at Studio-like strengths nothing read
  cold). They cool the floor around the subject to a pale neutral; the wall faces away from them and stays warm.
  Light-linking them off the paper was tried: Viewport 2.0 then dropped the rim from the character as well.
- **The cyclorama** (`cyclorama_profile` / `cyclorama_plan` / `cyclorama_targets`, `_make_cyclorama`): in radii,
  the floor from +12 r toward the camera, a quarter-circle cove (radius 1.5 r, 16 segments) from −3 r, a wall
  at −4.5 r up to 8 r, ±12 r wide. It is turned to the camera's heading at the press and hangs under the GROUP,
  not the light pivot, so the Rotate dial leaves it behind the subject. It starts behind every light's reach
  (a test pins it). It is a `polyPlane` with each vertex moved by its own starting position (not OpenMaya: an
  API mesh is not in the press's undo chunk) and its edges softened (a fresh polyPlane's are hard). Shared
  dressing with the floor (`_dress_catcher`). A warm matte blinn (0.62, 0.47, 0.36), and a warm viewport
  gradient and haze behind it. «Dark backdrop» is now «Backdrop».

Proof: `docs/superpowers/plans/verify_vpstudio_soft.py` **34/34 in a disposable GUI Maya** (port 7017, scratch
`MAYA_APP_DIR`, `MAYA_NO_HOME`) on a textured Manny:
- the cones 125.97° / 116.22°, ×3.00000 on Studio's;
- warm lights 176–212 cm toward the camera, cold 224–243 cm behind;
- the wall 4.500 r behind from the camera; every one of its 18 faces facing the subject;
- 17 interior edges, all soft;
- Rotate moving the key 344 cm and the paper 0;
- the paper warm in the picture;
- 6.3 ms a frame (Studio 5.9);
- Studio ⇄ Soft Studio leaving nothing behind, and Restore.

3164 unit tests.

142. **Maya's light commands make lights with RAY-TRACED shadows on, and Viewport 2.0 draws them.**
     `cmds.spotLight()` / `directionalLight()` / `ambientLight()` answer `useRayTraceShadows` True, so
     although the tool turned depth-map shadows off on everything but the key, **every light of every look threw a
     shadow**: up the wall from the low bounce, sideways from the fill, toward the camera from the back lights.
     It shipped like that since 2026-09-03: Studio's "streak to the right" was the fill's shadow. Found by
     switching the lights off one at a time; it first read as a shadow-map wrap from the wide cone, which it was
     not (a 126° spot shadows cleanly). `_make_light` sets `useRayTraceShadows 0` on every light.

## `maya_colour` — the palette on the shelf

Shipped single-file tool (2026-09-03, `SkeldarAnim/maya_colour.py`, `cmds`
only), the **eighth shelf button** — «добавим давай на полку скрипт
настройки цвета», asked minutes after the colour feature landed inside
Scene Setup. Spec:
`docs/superpowers/specs/2026-09-03-colour-on-the-shelf-design.md`. Proof:
`docs/superpowers/plans/verify_colour_tool.py` — **green live 2026-09-03,
0 of 34 gates failed** (it paints a SANDBOX character of its own — a joint
chain with a skinned sphere, a marked prop and an unmarked one — never the
animator's figures, and gates that their colours are untouched).

A grid of the eight palette colours, a custom swatch, a **Next free
colour** button and a "taken:" line naming what the scene already wears.

**It holds no colour policy at all** — the palette, the free colour, our
blinn, who wears it and how a character's meshes are found all stay in
`maya_scenesetup.colour`; this is a panel over it. Three unit tests read
the module's own source and assert that neither the palette values nor a
`free_colour` nor any `shadingNode`/`forceElement` appears in it. A second
copy of "which colour is free" would answer differently from Scene Setup's
swatch within a week.

**It recolours the SELECTION; Scene Setup's swatch is the colour of the
NEXT Add.** One meaning per control — the animator's own ruling that
morning — so the two never overlap. Target order is the toolset's
convention: selection, then the picker's connect, then a refusal.

**A bone means the character, anything else holding geometry means that
geometry, and the joint question is asked FIRST.** `hand_r` has the sword
parented under it, so a mesh-first rule would resolve a hand-bone click to
the sword. It climbs to the TOPMOST joint — the nearest joint above a hand
is the hand.

**A marked weapon is not part of its character, and that is a real bug the
live run found.** `colour.character_meshes` finds a figure through the
skinCluster AND a DAG walk (the walk is deliberate — unskinned geometry
parented in by hand is part of the figure), so a sword in the hand is
caught by it; `colour.paint` then reuses whatever material of ours is
already on those shapes, the two share one material, and **painting the
sword repaints the character** (measured: the character went pink when
only the prop was clicked). `maya_colour.without_weapons` drops shapes
under anything carrying `bonedrive.MARKER`, so the sword keeps the colour
Add Weapon gave it; an UNmarked prop still travels with the figure, gated
both ways. **Scene Setup's own Recolour button is deliberately untouched**
— it has the same property and has had it since that morning.

Two smaller rules, each with a test: `refresh` never writes to a colour
control (it fires after every press and would discard the colour just
dialled — `maya_scenesetup.window`'s swatch lesson), and a refusal opens
no undo chunk, since an empty chunk eats the animator's previous undo step.

## `install.py` — the SkeldarAnim shelf, drag-and-drop

**`SkeldarAnim/` is the distribution folder** (it was the repo root until
2026-09-01): `make_build.py` zips it, a colleague unzips and drags
`SkeldarAnim/install.py` into an open Maya viewport, and gets a shelf named
**SkeldarAnim** with **two buttons since 2026-09-19: SkeldarAnim** (the
hub, `maya_hub.show`) **and OverRig** (the native panel). The seven
section buttons — **UE Bridge, Characters, Weapons, Retarget, Hotkeys,
Studio, Colour**, each opening the hub on its own section (Characters
and Weapons are Scene Setup's two halves, `maya_scenesetup.show_window` /
`show_weapons`) — come back with `SECTION_BUTTONS`; the Rig Picker,
Overshoot and the OverRig hotkey rows with `PICKER`, `OVERSHOOT`,
`OVERRIG_HOTKEYS` in `skeldar_features.py` (`install.features()` reads
it from beside `install.py`, `_PYTHON_BUTTONS` rows carry the flag's
name). The zip is
**26.4 MB, 79 files** now (`assets/Manny_Rig.ma`, 53 MB uncompressed, `assets/Spear_01.fbx` 34 KB;
`maya_rigs.py` joined the payload, `maya_curveview/` and two icons left).
Design: `docs/superpowers/specs/2026-08-21-installer-design.md` (written
when there were five; the sixth arrived 2026-09-02, Viewport Studio and
Colour both on 2026-09-03, and the Curve Overlay on 2026-09-05, each with
its own spec), proof:
`docs/superpowers/plans/verify_install.py` (**11 gates, 0 failed** in the
live Maya, 2026-08-21: real install, payload exact, five buttons each
opening its window, OverRig dock up, sword resolved from the installed
copy, idempotent re-run, sys.path put back).

A drop copies a **whitelist** (`install.payload()`) into
`<userAppDir>/scripts/SkeldarAnim/` — the four packages, the three
single-file tools, `icons/`, `assets/`, `overrig/`, plus `install.py`
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
  so an import shim alone would not be enough. The other seven buttons are
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
24 gates failed** (three legitimate SKIPs: the animator's set already
existed, so the creation gates step aside rather than touch it). The ones
that matter most: the fresh set really inherited its source's sample key
(so it IS a copy), **the shelf button's own baked command** toggles both
ways (`SkeldarAnim_verify_base → SkeldarAnim → SkeldarAnim_verify_base`) —
everything else calls the module directly, and that string is what the
animator's finger travels — the four starter keys are ours **inside our set
while `Maya_Default` keeps its own**, insert/remove round-trip a sandbox
locator's keys exactly (`0,1,2,10 → 0,1,3,11 → 0,1,2,10`), and a real
set-driven curve's driver values do not move, and each of the four keys
resolves to a nameCommand whose runTimeCommand **runs by its MEL name** —
the chain a keypress travels, closed link by link since a keypress itself
cannot be sent over the port. The run leaves the set list,
the current set, the selection, the frame and autoKey as it found them.

**The map's contents are the animator's, laid out in Maya's own Hotkey
Editor.** A map file, a panel of ours and a cheat sheet were all offered and
declined, so there is no editor and no map format here. What the module adds
is the switch plus **113 runTimeCommands** worth binding, in the editor's own
category tree (categories nest with a **dot** — measured, Maya ships
`Editors.Time Editor.Clip`) — and, since 2026-09-02, **six keys bound for
you** (below).

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

**Six commands on eight starter keys, bound in OUR set only** (2026-09-02,
the animator's ask: «alt+a — кадр назад, alt+s — кадр вперед… добавить
inbetween кадр между… убрать»; alt+g and alt+o joined the next day, below,
and the inbetweens moved off alt+4/alt+5 onto the plus and minus keys the
same day). `DEFAULT_KEYS` is a table; `bind_defaults()`
runs **after** the switch, so the keys land in our set and never in theirs.
All four were already taken by a Maya default — measured: alt+a
`CycleDisplayMode`, alt+s `HIKSetFullBodyKey`, alt+4 `ImagePlaneOption`,
alt+5 `WireframeOnShaded` — and overwriting them was the animator's own
call («если возникают конфликты то перезапиши»); the press **names what it
displaced** rather than taking a key silently, and in their own set those
four go on doing what Maya says. Binding happens on the press that CREATES
the set **and** once per `DEFAULT_KEYS_VERSION` for a set that already
exists — "only on creation" would never have reached the animator's, which
existed before these keys did — recorded in the optionVar
`skeldarAnimDefaultKeys`. After that their edits in the editor stand: the
keys are a starting point, not a policy.

**Both spellings of the plus and minus keys are bound to the same command**
(2026-09-03, «переделаем добавление инбитвинов на alt + + и alt + -»).
Maya keeps `+` and `=` as **separate bindings** — measured: binding alt++
leaves alt+= untouched — and which one a physical alt+shift+= press fires
cannot be measured over the command port, since a keypress is the one thing
the bridge cannot send. So insert is on alt++ *and* alt+=, remove on alt+-
*and* alt+_, and the key works whichever way a hand reaches it. All four
were unbound in the animator's set, so nothing was taken.

**A key we stop using is given back.** `RELEASED_KEYS` names the keys
`DEFAULT_KEYS` used to hold — alt+4 and alt+5 — and `release_keys()`
unbinds each **only while it still holds the very command we put there**:
one the animator has since re-assigned in the editor is theirs, and taking
it a second time to tidy up would be the rudest thing this module could do.
It runs under the same version gate, just before the binding, and the
press says what it gave back. A key must never be in both tables, which a
test and a live gate both pin — releasing one we had just bound would leave
a dead key and no way to guess why.

**Insert / remove frame are exact inverses**, which is why they are defined
the way round they are: `insert_plan` moves everything strictly after the
current frame one frame later, so the frame after the pose comes free;
`remove_plan` clears that frame, keys and all, and pulls the rest back.
Press one then the other and the timeline is where it started. Both are
pure and tested as such. They act on **the selection's curves, or every
curve in the scene when nothing is selected** — "insert a frame" means the
shot when nothing is picked and that limb when something is.

**`cmds.ls(type="animCurve")` answers the DRIVEN-key curves too**, and
their x axis is a driver's VALUE rather than time — shifting one moves a
set-driven-key relationship instead of animation, silently. `time_curves()`
filters to `TIME_CURVES` (`animCurveTL/TA/TT/TU`), and this is not
theoretical: the animator's open scene held `animCurveUU` when this was
written. The live gate measures those curves with **`floatChange`**, not
`timeChange` — a driven curve answers nothing at all for `timeChange`, so
the gate's first version compared `[]` with `[]` and could not fail.

**alt+g toggles the Graph Editor, alt+o the Outliner** (2026-09-03,
«чтобы alt+g не просто открывал граф эдитор а делал toggle»), and the two
are **different mechanisms** — measured, not assumed:

- The Graph Editor opens as a **workspaceControl of its own**,
  `graphEditor1Window`; `close` on that control removes it entirely, after
  which `GraphEditor` opens it again. So `toggle_workspace_editor` closes
  only when the control exists AND is visible, and otherwise runs **Maya's
  own opener** — which also RAISES a control hidden behind a tab, and that
  is what a keypress should do in that case rather than a close nobody can
  see. The helper takes (label, control, command), so the Dope Sheet is one
  row whenever it is wanted.
- The Outliner is **not** a workspaceControl: in a normal layout it is a
  PANEL of the layout, so `outlinerPanel1Window` never exists at all. Maya
  already has the toggle — `ToggleOutliner`, measured taking the visible
  panels from `[modelPanel4, outlinerPanel1]` to `[modelPanel4]` and back —
  so `toggle_outliner` runs that and only reports which way it went, from
  `getPanel(visiblePanels=True)`. A layout with no Outliner in it is said
  so rather than reported as done. There is no `ToggleGraphEditor` to
  match it; that is why the two halves differ.

Both go through `_maya_mel`, **not** `_mel`: the latter sources OverRig
first, and pressing alt+g to look at a curve has no business loading a
rigging toolset. A test pins that.

Two flag names cost a probe round each: `cmds.getPanel` takes
**`scriptType`** and not `scriptedType` (`TypeError: Invalid flag`), and
`workspaceControl` carries `-close`, `-restore`, `-raise` and `-visible`.

`remove_frame` is **the one undo chunk** in the module, and it earns it:
clearing the frame and pulling the rest back are two commands, and a
Ctrl+Z that undid half of that leaves the timeline in a state nobody asked
for. Everything else inherits its target's undo, as the shelf buttons do.

**Ours are 26 rows with every flag on, and each one presses a panel
button** — bar the four timeline ones and the two editor toggles, which are
the module's own work (2026-09-08: the four Curve Overlay rows left with the
tool, the two retarget rows became one `retarget.run`, and the six Overshoot
rows ride `OVERSHOOT`).
Every action of
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

Two more, both paid for in a live run. **`cmds.hotkey` reverses its own
flag between reading and writing, and each wrong way round RAISES**:
writing is `hotkey(keyShortcut="a", name=<nameCommand>)` — positionally it
answers `RuntimeError: Please specify a key` — and reading is
`hotkey("a", query=True, name=True)`, where `keyShortcut=` answers
`TypeError: Flag 'keyShortcut' must be passed a boolean argument when
query flag is set`. Each form cost a live run, in opposite directions:
first the query written with the flag, then the write done positionally —
by which point this paragraph already said so, which is its own lesson.
The unit tests missed the second because the fake `cmds` accepted either
form; **the fake now raises exactly as Maya does**, which is what a fake
of a fussy command is for. And
**`cmds.nameCommand` has no query flag at all** (no `-q` in its synopsis),
so a binding cannot be followed from the key to the command body: the
verify script proves the chain in two halves instead — the key resolves to
our nameCommand, and a runTimeCommand run by its own name reaches `run()`.

A door left open: `hotkeySet` has `-export`/`-import` for `.mhk`, so handing
the finished map to a colleague — the one thing living in prefs costs us —
is one flag each whenever it is asked for.

## Conventions

- **No more per-tool shelf icons** (the animator, 2026-09-17: «точечные
  иконки для полки мы не рисуем, они больше не нужны»). Since the hub, a
  new tool is a SECTION of `maya_hub.SECTIONS` — a `build_panel()` and a
  row in the table — and nothing else: no shelf button of its own, no row
  in `install._PYTHON_BUTTONS`, no `draw_*` in `icons/make_icons.py`. The
  eight buttons and ten icons that exist stay as they are (the animator
  kept them in the brainstorm); the rule is about what gets added.
- **One branch: `main`** (since 2026-10-10; until then everything was built on
  `feature/overrig-picker`, which is merged and deleted), remote
  `github.com/EugeneM23/MayaScripts`. A push to `main` that touches the plugin
  is a release. Git identity is set **repo-locally** (`EugeneM`,
  `johnyanimation@gmail.com`) because the global `.gitconfig` does not exist.
- **Nothing at the root that does not build, test or rebuild the plugin**
  (2026-10-10). A one-off script belongs in `docs/superpowers/plans/` with its
  spec, never as a loose `maya_*.py` beside the plugin.
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

## AdvancedSkeleton rig over the UE5 skeleton (2026-09-04)

Not a plugin change: a control rig built in the animator's scene with the
third-party **AdvancedSkeleton 6.797**
(`C:/Users/MY PC/Downloads/AdvancedSkeleton/AdvancedSkeleton.mel`, shelf
Custom) on the studio's UE5 Manny, at the user's ask («сделай риг оснастку для
управления скелетом… есть специальные пресеты под этот скелет… сделай всё от
начала и до конца»). Spec:
`docs/superpowers/specs/2026-09-04-advancedskeleton-ue5-rig-design.md`.
Procedure, re-runnable: `docs/superpowers/plans/as_ue5_rig_procedure.py`.
Proof: `docs/superpowers/plans/verify_advancedskeleton_ue5_rig.py` — **green
live 2026-09-04, 0 of 24 gates failed**.

**What it is.** The UE skeleton is untouched — names, hierarchy, skin, bind
pose (drift 0.000000000 on all 93 joints) — and every one of AS's 79
deformation joints drives its UE twin through point+orient+scale constraints
(`-mo`; the vendor's Name Matcher "Constraint to Joints" with nine
twist/in-between rows added by hand — UE numbers the lower twists from the
wrist/ankle end, so `ElbowPart2 → lowerarm_twist_01`, `KneePart2 →
calf_twist_01`). `root ← Main` (parentConstraint, no scale — **Main is root
motion**; in-place work moves `RootX_M` and the IK controls),
`ik_hand_gun/ik_hand_r ← hand_r`, `ik_hand_l ← hand_l`, `ik_foot_* ← foot_*`;
`weapon_*`, `camera_*`, `interaction`, `center_of_mass`, `ik_*_root` ride
their parents. Legs default to IK (`FKIKLeg_*.FKIKBlend 10`), arms to FK. The
UE joints sit in a `UE5_Skeleton` display layer. **Every FK control and the six
IK end controls carry the LOCAL AXES OF THEIR UE BONE** (the user's ruling,
«оси контролов должны соответствовать осям костей на исходном скелете»;
`RootX_M` keeps AS's world frame, as AS itself insists): rotating a control 25°
about its X/Y/Z turns the bone 25.000° about its own X/Y/Z, and equal values on
both sides mirror to 0.0003 cm. Shoulder/Elbow/Hip/Knee do not roll about their
own X — AS sends that roll to the twist joints by design, which is what UE's
twist bones expect.

**How it was made, and the traps** (each measured):

- Fit = the vendor's `fitSkeletons/UE5.ma`, authored on this very skeleton
  (0.0003 cm everywhere but Neck/Head, 4.7 cm, snapped); Knee given
  `twistJoints 2` (the preset has none), Neck `inbetweenJoints 1`, Eye/Jaw fit
  joints deleted, heel pivot moved to the back of the sole. The Name Matcher's
  own `nameMatchers/Unreal5.ma` is a 17-unit template scaled by height/17 with
  a stray `Chest` off `Spine3` — not used.
- **Never call `asNameMatcherCheck` over the port**: it compares
  `joint.bindPose` (measured: the WORLD matrix at bind) with `.matrix` (local)
  and puts up "Reset joints to Bind-Pose?" for any hierarchy — a modal that
  blocks the idle queue (bridge note 6). The vendor's procs read their own UI
  controls, so `AdvancedSkeleton;` (the window) must be open before any of
  them; it opens without dialogs here (`asHaveRanThisVersion` 1, units cm).
- **Control axes = `asControlOrientDetach` → set each control's world rotation
  (`local = R_bone · R_parent⁻¹`, in its own rotate order) →
  `asControlOrientAttach` with mirror OFF**, each side from its own bone. The
  FKX joint is a DAG child of its FK control; Detach parks children in
  `CustomOrientReverse*`, Attach inserts `CustomOrient*` above the Extra.
  **The in-between neck breaks**: `NeckInbetweenMM_M` /
  `NeckPart1InbetweenMM_M.matrixIn[1]` read
  `FKExtraNeck_M.parentInverseMatrix`, which Attach turns into the rotated
  CustomOrient, and `FKXNeck_M` came back rotated (180, 0, −0.938) —
  `neck_01` flipped. Reconnect both to `FKOffsetNeck_M.worldInverseMatrix`
  BEFORE detaching (they are the only consumers of any
  `*Extra*.parentInverseMatrix`); done after Attach it leaves NeckPart1/Head
  with stale transforms that had to be normalised by hand. IK end controls are
  safe: the IKX ankle/wrist read the CHILD `IKFKAligned*` nodes and Attach
  re-orients `AlignIKTo*` (FK↔IK align still lands to 1e-6); the one consumer
  of an IK control's own rotation, the arm pole's follow offset
  `PoleOffsetArmMMArm_*.matrixIn[1]`, is right-multiplied by D⁻¹ so its
  product is unchanged.
- **Maya crashed at the first parallel evaluation of the freshly wired rig**
  (15:55, `MayaCrashLog260904.1555.dmp`; the recovered scene held the whole
  rig). Every later poke ran under `evaluationManager -mode off` and put it
  back. Cause not isolated.
- `asCreateGameEngineRootMotion` errors while a UE `root` exists (6.800 renames
  its joint `RootMotion_M`) — hence `root ← Main`.
- A ReBuild regenerates the neck network with the vendor's reading and
  re-applies `customAxis` through its own Set Axis batch: run
  `as_ue5_rig_procedure.orient_controls()` again afterwards. The UE bridge's
  import guard (trap 37) refuses merges onto constrained joints, so this
  character takes clips through AS's MoCap Matcher or with the rig
  disconnected; export bakes as before.
- Pre-rig backup:
  `Documents/maya/projects/default/scenes/Manny_before_AdvancedSkeleton_20260904_1548.mb`.
  The scene lives at the crash-recovery path until the user saves it.
- **Two follow-ups the same evening, both measured.** The Fingers curl/spread
  set-driven keys drive the `SDKFK*` groups, which sit ABOVE `CustomOrient`
  and so kept AS's axes (curl 14° off the UE knuckle axis); each is now under
  a `UEAxis*` node framed y = bone Z, z = bone Y, x = y × z, the CustomOrient
  below recomputed — curl turns all 28 phalanges about exactly +Z (inward on
  both UE hands), spread opens the tips 4.76 cm. And Detach/Attach does not
  do Set Axis's "keep curve unaffected": the IK foot boxes came out flipped.
  Putting the CVs back exactly (`R_old · R_new⁻¹`) fixed that and drew the
  next complaint — AS draws the IK hand cube in the WORLD frame, so a
  drawing put back exactly is skew to the bone axes («визуально
  ориентирован по мировым координатам»). The rule that stands: every
  custom-oriented control's curve is drawn axis-aligned in the control's own
  frame, extents on the nearest signed permutation of AS's drawing axes
  (identity when no axis dominates — the hand cube); feet turned 8.71°,
  finger rings up to 27.8°, frames untouched (`align_shapes` in the
  procedure, gate 24).
- Harness: a Bash call longer than ~8 KB dies with "unexpected EOF" and runs
  nothing (three times that day) — write big payloads with Write and keep
  the Bash call to the run command.

## `maya_asretarget` — a clip on a second UE5 skeleton onto the AS rig (2026-09-04)

Root-level standalone (`cmds` + `maya.api.OpenMaya`, no Qt, no package), the
sibling of the old `maya_retarget.py` (removed 2026-10-10) — that one drove another skeleton FROM Manny,
this one drives the AdvancedSkeleton rig FROM another skeleton. The animator's
ask: «я импортирую в сцену анимацию с аналогичного скелета… наш ретаргет
привязан к этим костям. Потом я сам иду в настройки андванцед скелетона и делаю
запекание. Твоя задача сделать сам ретаргет». Spec:
`docs/superpowers/specs/2026-09-04-as-retarget-design.md` (read its ADDENDUM —
the live run changed three decisions). Proof:
`docs/superpowers/plans/verify_asretarget.py` — **green live 2026-09-04, 0 of
26 gates failed**; 47 unit tests.

```python
import sys; sys.path.append(r"C:/!!!Work/MayaScripts/SkeldarAnim")
import maya_asretarget
print(maya_asretarget.report())      # read-only: what would be driven, from what
print(maya_asretarget.connect())     # build it, from the SELECTED source skeleton
print(maya_asretarget.disconnect())  # the same as AdvancedSkeleton's own button
```

The loop: import the clip on a second UE5 skeleton → select any joint of it →
`connect()` → set the playback range to the clip → in AdvancedSkeleton, **MoCap
Matcher > Bake**, then **Disconnect MoCap Skeleton**.

**The vendor's Bake and Disconnect are reused verbatim, because they run on a
convention rather than on their own bookkeeping.** `asMoCapMatcherBake` finds
the node `MoCapConstraints`, walks the destinations of its `disableConstraints`
attribute for the constraints, resolves each one's
`constraintParentInverseMatrix` to the object it drives, bakes exactly those
across `playbackOptions -min/-max` and ends in `delete -staticChannels`;
`asMoCapMatcherDisconnect` deletes the same constraints and the node. So we
register every constraint's `nodeState` on that attribute and park every helper
UNDER `MoCapConstraints` — the helpers then die with the parent on Disconnect.
**The vendor's own `MoCapConnect` is deliberately NOT used**: it constrains with
`-mo` (so the clip's pose at press time becomes the rest pose, hence its
"zero-out MoCap-joints" step), it resolves source bones by scene-wide NAME
(with two Mannys `upperarm_l` is a coin flip), it drives no poles, and it leaves
root motion in the pelvis. Its `moCapMatchers/Unreal.txt` template is UE4-schema
(`Chest=spine_03`, no metacarpals, no `neck_02`) and does not fit this rig.

**74 controls, and no maintainOffset anywhere.** After the 2026-09-04 axis work
a control's frame IS its bone's frame (measured: posing `FKSpine3_M` turned
`spine_03` by 24.95° with the frames 0.00001° apart), so an `orientConstraint`
with no offset copies the source's world orientation 1:1 — at any frame, in any
pose, with no pose matching. FK controls take rotation only; `IKArm/IKLeg` take
point+orient from `hand_*`/`foot_*`, `IKToes` orientation from `ball_*`; `Main`
takes `root` so **root motion stays in the exported `root` bone** rather than
smearing into the pelvis; `RootX_M` takes `pelvis`; and the four poles ride the
UPPER bone's frame (`thigh_*`/`upperarm_*`) — a pole point-constrained to the
mid joint is degenerate on a straight limb, while the limb plane is fixed by the
upper bone's roll. Twist joints are skipped: no FK controls, and the rig's twist
network recomputes them from the bones we drive. Both FK and IK are driven, as
the vendor does, so whichever mode a limb is in it follows — and a limb flipped
to FK after the bake reproduces the source bone for bone (0.048 cm, which is the
rig's own FitSkeleton fit tolerance).

**The offset helper, and why it exists at all.** Where a control's rest frame is
NOT its bone's (`Main`, `RootX_M`, the poles, and — measured — the IK end
controls, which stand 0.0003–0.0095 cm off their bones), the drive goes through
two nodes under the holder: `asrtDriver_<control>` point+orient-constrained to
the source bone 1:1, and `asrtTarget_<control>` whose LOCAL matrix is the
analytic rest offset `C_rest · B_rest⁻¹` (row vectors: `world = local · parent`).
A transform pair rather than a constraint's `offset` attribute, because trap 19
is the record of how easy that convention is to get backwards — and a pair is
measurable, which gate 10 does.

Three things the live run changed, each worth not re-deriving:

- **Whether a drive needs the offset is MEASURED, never tabulated**
  (`needs_offset`, pure). The design had a table flag; the IK end controls then
  snapped the limb by 0.0095 cm because the table said "no offset".
- **Every rest matrix is read BEFORE the first constraint.** Reading them as the
  build went along put a pole's offset 0.022 cm out: a leg pole rides its IK
  control (`followLeg` 10), which an earlier drive had already constrained. For
  the same reason `connect` **refuses a posed rig** (a pole's offset is
  pose-dependent) and names AdvancedSkeleton's *Go To BuildPose*;
  `connect(require_build_pose=False)` overrides.
- **Both sides of the offset are made rigid** (`rigid`, pure). The rig's scale
  chain leaves ~4e-7 of scale on a bone and the helper's driver cannot carry it:
  85 cm out at the pole that was 33 microns of error, now 4.

**The neck cannot be exact, and the number says why.** Measured at a 15° source
neck bend: `FKNeck_M` reaches its target perfectly (0.00000° from the source's
`neck_01`) and the BONE still lands **7.5000° short** — half. That is the neck
in-between the rig was built with (`Neck.inbetweenJoints 1`), which distributes
a control's bend across both neck joints. `neck_02` and `head` keep exact
ORIENTATION and pay 0.6554 cm of position. The knob is the animator's own:
**`FKNeck_M.bias`**, keyable, soft range 0..10, default 0, feeding the blend
weight linearly — measured **0 → weight 0.5** (30° on the control turns
`neck_01` 15.0000°) and **10 → 1.0** (30.0000°, and the retargeted neck then
lands 0.000015°/0.000001 cm off). `connect` names it in the status line and
`connect(exact_neck=True)` sets it — **the default since 2026-09-05**, together
with the in-between's second knob (the twist share, below); both decide how the
baked neck keys distribute, so both stay where connect put them.

**What is exact:** pelvis, spine 1–5, clavicles and every finger to
**0.000020177** (world-matrix element) over sampled frames; hands, feet and
balls to **0.0016 cm** (the IK solver's own residual); knees and elbows to
**0.0876°**; root motion **0.000000000** against 100 cm travelled; and after
Bake + Disconnect with the source deleted the rig plays the take to the same
0.0016 cm, with no pairBlend spliced anywhere (trap 37's signature never
appears).

**Two facts about the vendor's Bake.** It reads the PLAYBACK RANGE, so match it
to the clip first — `connect` prints the range and the source's own key range
because the animator's scene was sitting at 0..46400. And `delete
-staticChannels` means it keys only what moves: 20 controls of 74 on the test
take, which is right — root motion arriving through `Main` turns the whole rig,
so everything else keeps its local values.

The source is resolved from the **selection**, climbed to the topmost joint, and
its bones matched by LEAF name inside that subtree — so a namespaced import, a
plain second Manny whose root Maya renamed, or a group around either all behave
the same, and nothing is ever found by a scene-wide lookup. It refuses: our own
rigged skeleton (its joints carry our constraints) or anything under `Group`, an
empty or jointless selection, two skeletons at once, a standing
`MoCapConstraints`, and a posed rig. A source bone the map needs but the clip
lacks is named and skipped (a UE4-schema source loses 11 rows and works).
Proportions are compared pose-independently by segment length and a >2%
difference is a WARNING, not a refusal — scaling a source is the vendor's own
MoCap Matcher step and guessing it would distort a take.

Harness note from this session: a probe that set `evaluationManager -mode off`
outside its own try/finally died on an unrelated error and left the animator's
Maya in DG evaluation for the rest of the session. Set scene state inside the
guard that restores it, from the first line.

**And it retargets from MIXAMO too** (2026-09-05, «в открытой сцене у нас есть
скелет который я взял с миксамо на скелете анимация… сделай так чтобы наш
скрипт делал ретаргет и для миксамовского скелета»). Spec:
`docs/superpowers/specs/2026-09-05-asretarget-mixamo-design.md`. Proof:
`docs/superpowers/plans/verify_asretarget_mixamo.py` — **green live
2026-09-05, 0 of 18 gates failed** on the animator's own clip, with the twin's
own `verify_asretarget.py` re-run **green, 0 of 26**; 77 unit tests.

**A source skeleton is a `Schema` row now, not a branch** — `rows`, `sides`
(`side_before` for Mixamo's `LeftUpLeg` prefix), the IK and pole rows, the
pelvis, the root bone, where the rest pose comes from, whether to align, and
five hint bones for `detect_schema`, which **refuses** a skeleton it cannot
name rather than guessing. Measured on the animator's clip: 65 joints under
`mixamorig:Hips`, 52 animated, 12084 keys over 0..75, and against our rig —
different names, side as a PREFIX, bones down local **Y** against our X, bind
in **jointOrient** against our rotate channels, a **T-pose** rest against our
A-pose, 3 spine joints against 5, 1 neck against 2, no metacarpals, no root
bone, arm **+16.5%**, leg **−2.6%**.

**The core is aligning the rest poses bone by bone.** A rigid offset (`-mo`, or
the twin's `C_rest · S_rest⁻¹`) preserves the source's motion relative to ITS
rest, so a T-posed source hands an A-posed rig arms **54.83°** too low for the
whole clip — that is the classic broken retarget and the number is exactly the
rest difference. So `R_align` is the minimal rotation taking OUR rest bone
direction onto the SOURCE's, `C_ref = C_rest · R_align`, and the offset is
`C_ref · S_rest⁻¹`. The property that follows is what "correct" means here and
it is what gate 11 measures: **our bone POINTS exactly where the source's bone
points at every frame** — measured worst **0.028°** over 6 samples and 18
bones. Minimal because the two skeletons agree on where a bone points and say
nothing about the roll, so our rig keeps the roll its own axis work
established; and because it is all world-space, the X-against-Y axis
conventions need no handling at all.

Facts to not re-derive:

- **A bone needs a mapped child to point at.** The hand reaches past the
  missing metacarpal to `middle_01_l ↔ LeftHandMiddle1`; the head, the toes and
  the finger tips have none and **inherit their parent's** alignment
  (`alignments` walks root-down).
- **The NEAREST mapped child is the wrong one for a hand, and it cost 30.77°.**
  A hand's nearest mapped descendant is the **thumb** — the one finger that
  does not continue the hand — and taking it rolled the wrist by that much for
  the whole clip. `DIRECTION_CHILD` names the two exceptions; every other bone
  then measured ≤ 0.028°.
- **The source's rest pose is declared, never observed**: it is not visible at
  any frame of an animated clip. `rest="jointOrient"` walks the hierarchy with
  every rotate at 0 (Mixamo; measured to be an exact T-pose, arm along +X to
  0.000, 47.23 cm out, 0.00 up), `rest="live"` means a twin standing in our own
  bind pose. **Our own rig must never be read the jointOrient way** — its bind
  is in the rotate channels, and zeroing them straightened it **76.25 cm**,
  which is how that probe found the rule.
- **An `orientConstraint`'s own `offset` holds `W_target = O · W_source`**
  (measured, worst element 0.000000000 — trap 19's convention), which is exactly
  our rest offset's shape. So a rotation-only drive needs **no helper node**:
  53 of the 62 Mixamo drives are one constraint each and only the 9 position
  drives get the two-node helper. Without it the Mixamo case would add ~140
  transforms and double the vendor bake, which bakes every object its
  constraints drive. The euler goes in the CONTROL's rotate order (the rig uses
  four different ones, `FKWrist_L` is `zyx`); a test round-trips all six.
- **Maya refuses a negative point-constraint target weight** ("Cannot set the
  attribute below its min"), so the weighted-constraint trick that would scale
  the IK reach for a 1.165 arm ratio is not available. Not built; the two modes
  below are the answer instead.
- **Both modes are driven and both are named, nothing is scaled**: in **FK** the
  rig copies the source's ANGLES and keeps its own proportions (our hand
  therefore sits **8.29 cm** from the source's), in **IK** the hand and foot
  land on the source's own positions (**0.0003 cm** and **0.0094 cm**) with the
  elbow bending more to get there. `proportion_note` says it with the measured
  percentages; the FKIKBlend chooses.
- **`Main` takes the hips' horizontal travel only** when the schema has no root
  bone (`pointConstraint`, `skip=["y"]`; measured x −10.85, y 0.00, z −59.73).
  The travel is unambiguous, a yaw would be invented — and since the pelvis is
  constrained absolutely it absorbs whatever `Main` does, so the pose is
  untouched either way.
- The 3-against-5 spine drives `Spine1←Spine`, `Spine3←Spine1`,
  `Spine5←Spine2` and leaves `spine_02`/`spine_04` at rest (the driven spans
  then measure 0.000°); the 1-against-2 neck leaves `NeckPart1` undriven so the
  rig's own neck in-between does the smoothing it was built for.
- **A gate must measure its promise in the mode that makes it.** Gate 11's
  first version measured the FK promise with the legs in IK and read 6–20° —
  which was the OTHER promise working. It also exposed a real bug in the verify
  teardown: **`asGoToBuildPose` writes the FKIKBlend values the rig was BUILT
  with**, so restoring the animator's blends before it hands them back a rig in
  the wrong mode. Restore them after.

**A twin's bones carry TRANSLATION, and since 2026-09-05 its FK controls follow
it** (the animator: «на AS_Death_Front_3p_01 совпадение положения костей очень
точное (кроме шеи), на AS_Longsword_Attack_Backcombo положение костей начинает
отличаться заметно… мне важно чтобы мой ретаргет всегда имел 100% точность»).
Spec: the twin spec's **Addendum 2**. Both clips are full UE5 twins; the
difference is what they animate — the Longsword clip translates its bones
(neck_01 **3.67 cm**, clavicles **3.65**, spine_05 2.52, thighs 0.81) and an
orientation-only FK drive lost every centimetre, stacked down the chain
(measured: clavicle_l **6.35 cm**, neck_01 5.04, spine_05 2.83; pelvis 0.000).
Facts:

- **`Schema.twin`** (was `keep_position`): one fact, two consequences — a
  twin's FK rows take position, and its position drives keep our rest offset.
  Mixamo's FK stays rotation-only (its joints would hand the rig its
  proportions).
- **A position+rotation drive is ONE `parentConstraint`** carrying the rest
  offset on its target offsets. Measured over all six rotate orders:
  `targetOffsetTranslate` = the offset's translation and `targetOffsetRotate` =
  its euler **in the constrained node's rotate order** reproduce `W_c = O · W_t`
  to **4.6e-14** (xyz for a zyx control is off by up to 1.47); `-mo` stores
  exactly those; `constraintParentInverseMatrix` exists, so AS Bake/Disconnect
  are unchanged. 68 such drives, no helper; only the 4 poles keep the helper
  pair (a pointConstraint cannot turn its offset). 82 constraints + 4 helpers,
  against 96 + 8 before. `parent_offsets` is the pure half.
- **AS's FK controls take translation**: all 62 have free translate channels,
  and +2 cm on one moves its UE bone and everything below by 2.0000, nothing
  above.
- **Measured after** on the real clips, all FK: Longsword every bone
  ≤ **0.0009 cm**, Death ≤ **0.0004**, except the LEFT leg at 0.06–0.08 cm —
  the rig's own: `FKKnee_L` stands 0.0637 cm off `calf_l` (mirrored fit against
  Manny's 0.068 cm asymmetric calf; the right knee 0.00004) and the Knee joint
  does not roll with the bone, so that constant offset wanders with the knee's
  roll. A fit fact, not a retarget fact.
- **The neck has a SECOND knob.** `neck_02`'s orientation read up to **24.24°**
  off with its control exact: `NeckPart1_M_orientConstraint1.offsetX` is
  **DRIVEN** by the head's twist (`HeadQTETwist_M` ×
  `twistAmountDivideNeckPart1_M.input2` = 0.5) — the in-between takes half the
  head's roll, like the limb twist joints, while a UE source keeps neck_02 at
  its rest roll. Share 0 → exact on every frame. `set_exact_neck` sets both
  knobs (bias 10, share 0) and that is the default. **A constraint's `offset`
  can be a live input — read it under the pose, never at rest**: its (0,0,0)
  at build pose cost eleven probes.
- **Verify**: the twin fixture now slides clavicle_l 3 cm / spine_05 2 /
  neck_01 −2.5 and rolls the head 30 — a fixture without translation could not
  see this bug — **0 of 27 gates**; Mixamo **0 of 18** on the animator's
  `Sweep Fall.fbx` imported into a throwaway namespace (the wrapper must save
  the playback range BEFORE the import: FBXImport moves it). Both verifies
  save and restore the neck knobs. 84 unit tests.
- **Workflow**: Disconnect without Bake leaves the rig posed, so the next
  connect refuses until Go To BuildPose — by design (a pole's offset is
  pose-dependent), and the message names the button.

## AdvancedSkeleton rig over the PlayerMale game skeleton (2026-09-05)

The second AS rig, over a skeleton that is NOT Unreal's — the animator: «В
открытой сцене новый скелет, это не unreal engine. Давай для этого скелета
соберем риг на базе advanced skeleton». `PlayerMale_v6.fbx` (a Unity-style
`Assets/Game/...` project), opened as an FBX: 57 joints `Root > Hip > Spine1..4
> Neck > Head > Jaw/Eyes`, sides as a PREFIX (`Right_`/`Left_`), five 3-joint
fingers and no metacarpals, one `Toes` per foot, no twist joints, bones down
local X with the LEFT side down −X, mixed rotate orders, bind partly in the
rotate channels, **17.5 units tall in a cm scene (1:10)** — which happens to be
the scale AS's own templates are drawn at. 70 skinClusters (every outfit) on
the same joints. Spec:
`docs/superpowers/specs/2026-09-05-advancedskeleton-playermale-rig-design.md`.
Procedure, re-runnable: `docs/superpowers/plans/as_playermale_rig_procedure.py`
(`run()`, or stage by stage). Proof:
`docs/superpowers/plans/verify_advancedskeleton_playermale_rig.py` — **green
live 2026-09-05, all 27 gates passed**.

**Same shape as the Manny rig**: the game skeleton untouched (names, hierarchy,
skin, bind pose to 2.3e-5), each of AS's 56 deformation joints driving its twin
through point+orient+scale `-mo` written by long path (169 constraints,
`Root ← Main` so Main is root motion), 55 FK controls carrying their bone's
axes (0.000003°; 25° on any axis turns the bone 25.00000° about its own), the
finger SDK groups re-framed on the bones, the fit's foot/head/finger END joints
placed from the geometry. Legs IK, arms FK. Facts, each measured or paid for:

- **The game joint names collide with AS's fit joints.** `Root`, `Hip`, `Spine1`,
  `Spine2`, `Spine3`, `Neck`, `Head`, `Jaw` are exactly the FitSkeleton's names,
  and AS addresses those by SHORT name everywhere (`getAttr Hip.twistJoints`);
  `asFitModeManualUpdate` runs `asUniqueNameAll`, which renames a non-unique
  FIT joint to `Hip1`, and `asLabel` errors on ambiguity. `hold()` renames the
  eight game joints to `PMhold_<name>` (the original kept on `asHeldName`) for
  the fit and the build, `release()` gives them back — constraints, skin and
  bindPose are wired to nodes, so the round trip is free (gate 25, 0.00000°).
  Cost: afterwards both `Hip`s exist, so **a ReBuild needs `hold()` first** and
  AS's fit-mode buttons complain until then. The vendor's own answer — a
  permanent `NameMatcher:` namespace on the other skeleton — was rejected: it
  rides into every exported bone name.
- **`asFitSkeletonImport` ends in `asImportMatcherScan`, which pops a MODAL**
  ("External skeleton detected. Align joints with this skeleton?") for any
  joint named `*Hip*`/`*hip*`/`*pelvis*` under a biped template — a blocked
  idle queue over the port (note 6). The vendor's own Name Matcher suppresses
  it with a node named `FitSkeletonNameMatcherImporting`; so does the procedure.
- **`biped.ma`'s spine is `Root > Spine1 > Chest`** — no Spine2 (the first fit
  died on that KeyError); Spine2 and Spine3 are duplicated from Spine1 and
  chained, `Chest` keeps its name so the IK spine and every Chest special case
  build. `Cup` deleted with its two `SDK1FKCup_*` curves; `twistJoints 0` on
  Shoulder/Elbow/Hip because the skeleton has no twist bones — the roll then
  lands on `*_Arm` itself (measured: `FKShoulder_R.rx 25` rolls `Right_Arm`
  25.00000°, the forearm's local rotate untouched), on Manny AS sent it to the
  Part joints; `inbetweenJoints 0` everywhere. `reset_fit()` lets a fit start
  over without the vendor's Replace/Merge dialog; every mapped fit joint landed
  **0.000000** from its bone.
- **The IK end controls keep AS's own world-aligned frames** — the one
  departure from Manny, and the animator's call after seeing them on the
  bones' axes: «оси контролов руки не совпадают с осями костей и стоят криво…
  Контролы ног тоже». Measured, the controls were on the bones to 0.00000°;
  the BONES are crooked — `Right_Ankle` points at the ball 26° below
  horizontal, `Right_Hand` is rolled 34° against AS's wrist — so the foot
  boxes stood nose-down into the floor. And AS's deformation skeleton was
  drawn exactly on the game bones with axes 64° (ankle), 34° (wrist), 85°
  (head) off theirs, so a viewport click on "the bone" compared against it.
  Fix = option A of three offered: `as_frames()` put the six IK ends back
  (drawings to AS's CVs, Detach / set to the IKOffset frame / Attach, pole
  offset compensated; 0.000000° left), `orient_controls(ik_ends=False)` builds
  that directly, and AS's 72 deformation joints sit in a hidden display layer
  `AS_DeformSkeleton` (the game skeleton in the visible `PlayerMale_Skeleton`).
  On Manny the same bone-axis rule looked right because UE's foot bone is
  nearly world-aligned (boxes turned 8.71°); the rule is skeleton-dependent.
- **The HAND controls carry a frame the animator drew as two locators**
  (`locator10` right, `locator9` left, «я сделал их как подсказку для тебя»):
  X along the fingers, Z the palm normal — **29.28° off the hand bone**, whose
  X points at the middle finger's root, and 7.9° off AS's wrist; neither
  earlier answer was it. `frame_controls({ctrl: R})` puts a chosen few
  controls on given frames (shape alignment undone first, Detach / set /
  Attach, pole offset compensated, curves re-aligned) — `IKArm_R/L` and
  `FKWrist_R/L` sit on it to 0.000000°; `HAND_FRAME_IN_BONE` records it so
  `run()` needs no locators. **The animator works in the scene meanwhile**: the
  left arm's FK controls turned up parent-constrained to `locator1/2/3` beside
  an OverRig `base_IK_strech1` — their own test, made between two runs; the
  verify skips, and names, any pose through a control whose constraint target
  lies outside `|Group` (`foreign_constraints`) rather than calling the rig
  broken.
- **Finger SDK axes are measured**: on this skeleton the knuckle line is a
  phalanx's local Y and the palm normal its Z (both hands, same formula — on
  UE it was Z/Y). **The palm is the side the THUMB sits on**: the cross product
  `(index−hand)×(pinky−hand)` points to the palm on one hand and the back of
  the other, and the first probe "fixed" a correct left hand into curling
  backwards. `finger_probe` / `calibrate_finger_axes` flip y or z per hand
  only when a measured channel goes the wrong way. Curl mirrors to 8e-6.
- **`cmds.exactWorldBoundingBox` did not follow the skin over the bridge**:
  with Main moved 3.0 every joint and every Body vertex had moved 3.000 and the
  bbox answered 0.00002 — in DG, after refresh, in parallel. A gate about skin
  reads a vertex (`pointPosition`).
- The arm stands 99.4 % extended, so an IK push forward reads 0.928 (out of
  reach, not a bug) — the test lifts the hand; the forearm frames are 0.156°
  asymmetric between sides, so equal values mirror to 0.003.
- `bodySetup` (as in `asGoToBuildPose bodySetup`) is a UI name, not a node;
  `buildPose` is the node. Backups in `Documents/maya/projects/default/scenes/`
  (`PlayerMale_v6_before_AdvancedSkeleton_*.mb`, `..._rig_*.mb`,
  `..._rig_final_*.mb`); the scene itself is the opened FBX — Save As is the
  animator's.

## `maya_pmretarget` — rotations onto the PlayerMale rig from UE, Mixamo or itself (2026-09-06)

Root-level standalone, a COPY of `maya_asretarget.py` for the PlayerMale rig
(«сделаем копию скрипта ретаргета на разные скелеты… не учитывать изменения
позиций в костях, только вращения… отдельным модулем»); it imports nothing from
its sibling and a test pins that. Same API (`report()`, `connect()`,
`disconnect()`) plus **`bake()`** — the vendor's MoCap Bake over the CLIP's key
range (the holder remembers the source), then its Disconnect — same vendor
contract (`MoCapConstraints.disableConstraints`, helpers under the holder). **A
Disconnect without the Bake keeps nothing**: the morning after, the animator's
«ретаргет сработал только на 1 кадре» was exactly that — connected, disconnected,
never baked, the rig frozen in one pose; connected again it followed the clip on
every sampled frame (0.000–0.008°). `connect()` now ends by naming `bake()`. Spec:
`docs/superpowers/specs/2026-09-05-pmretarget-design.md`. Proof:
`docs/superpowers/plans/verify_pmretarget.py` — **green live 2026-09-06, all 32
gates passed** on three sources it builds or imports itself (a copy of the game
skeleton with a known take, a 93-joint Manny from the shipped template, the
animator's `Sweep Fall.fbx`); 55 unit tests.

- **FK controls take rotation only** (orientConstraint, rest offset, rest poses
  aligned bone by bone as in the Mixamo work) — a source bone translated 1.0 is
  ignored while its orientation lands to 0.00000°. **The IK ends and poles follow
  OUR OWN FK joints** (`IKArm ← FKXWrist`, `IKLeg ← FKXAnkle`, …): a rotation-only
  retarget has no source position to give an IK hand, so the IK pose is the FK
  pose in our proportions and the animator switches either way after one bake.
- **Travel is scaled** by our pelvis height over the source's, each above its own
  root (a UE or Mixamo clip is ~8.6× this 17.5-unit character): `Main` follows the
  source root's rotation and scaled translation (100 cm → 11.6869), or the hips'
  horizontal travel from rest when there is no root bone; `RootX_M` the pelvis.
- **Four schemas by required/absent bones, in order**: `OWN` (rest = our bones'
  rest by name), `UE5` (rest from `assets/manny_skeleton_template.json`), `UE4`
  (`spine_03` chest, no `spine_05`; rest from `assets/ue4_mannequin_template.json`,
  68 joints extracted from the shipped fbx in mayapy), `MIXAMO` (rest = rotates at
  0). Spines: UE5 `Chest ← spine_05` (spine_04 alone), UE4 `Chest ← spine_03`,
  Mixamo `Chest ← Spine2` (our Spine3 alone).
- **A `pointConstraint`'s `offset` is in the constrained node's PARENT space.**
  `RootX_M`'s parent follows `Main`, so a 25° root turn turned the pelvis offset
  with it (0.115 off). The offset lives on a helper under the scaled group
  (`pmrtOffset_`, divided by the scale) and the control's constraint carries none
  → 0.000000. Rotation offsets are fine: an orientConstraint holds `W = O · W_src`.
- **The pole took three tries.** Riding the upper bone at its rest standoff (the
  Manny module's way): 0.11° on our own take, **5.0°** on a UE take whose bends
  come through the alignment about axes that are not our knee's hinge. Riding the
  knee's frame: the same. The vendor's three-point placement with its world-z nudge
  a tenth of the limb long: **19.7°** on a straight leg under a yaw. What stands:
  base on the hip–ankle line at the knee's share, nudge **in the FK knee's frame**
  and **0.2 % of the limb** long, aimed at the knee, pole a limb out — pole 0.0004
  off the FK plane, IK knee on the FK knee to 8e-5, UE take in IK 0.0388°.
- **What is left in IK is the skeleton's own**: the IK thigh and knee still differ
  from FK by **0.33° of roll** (directions exact) because this skeleton's knee
  hinge stands 0.36° off its own rest bend plane and a solver bends about the
  plane's normal. Stated, gated at 0.5°; the FK bake is the product.
- **A control the animator has constrained to their own nodes is skipped and
  named** (`foreign_constraints`; ours are told apart by their holder
  registration). `ls("ns:*")` does not reach a NESTED namespace
  (`pmrtMx:mixamorig:Hips`): find imported nodes by the UUIDs the import created.
- **One button for both rigs: `maya_rig_retarget.py`** («я просто выделяю скелет,
  нажимаю на скрипт и ретаргет готов. Точно так же я хочу и для Lugal_Rig_01»).
  The animator's shelf button ran `maya_asretarget.connect()`, which on the Lugal
  rig can only refuse (its bones are UE's). The dispatcher reads the rig's
  constrained game skeleton — UE names → `maya_asretarget`, PlayerMale names →
  `maya_pmretarget` — and forwards `report/connect/bake/disconnect`;
  `maya_asretarget` gained the same `bake()` (vendor Bake over the clip's keys,
  then Disconnect) so the pair of buttons means the same on `Manny_rig_02` and
  `Lugal_Rig_01`. **Since 2026-09-07 the buttons are the INSTALLER's**
  (`maya_rig_retarget.retarget_button`), the three modules live in
  `SkeldarAnim/`, the bake is native (`vendor_bake`) and also carries the
  helper bones and sets the camera up — see the pipeline section at the
  top. **Since 2026-09-08 Retarget and Bake are ONE button** and every
  module function takes a `rig` — see the many-rigs section. The animator's hand-made
  `shelfButton9`/`shelfButton32` were replaced by the 2026-09-07 re-install.

## The Creep in its FBX's layout: `Armature` over `root` in the scene (2026-09-28)

The animator: «При добавлении крипа у нас добавляется не последняя версия скелета. Последняя
версия скелета вот тут C:\!!!Work\Animations\Rigs\Characters\Creep_Skeleton.fbx». **Measured
first: the same skeleton** — that FBX is `export_creep_skeleton_fbx.py`'s, from our own
`assets/Creep_Skeleton.ma`: 91 bones, the hierarchy, the pose to 0.0 cm / 0.0°, five meshes to
0.0001 cm, uvs 0.0, weights to the FBX's 0.003. What differed was the LAYOUT — asked: «Структура
сцены», and why: «Как в файле, единообразно» + «И риг крипа тоже». So both Creep assets now stand
in Cascadeur's layout in the scene: a transform `Armature` at the origin turned -90 X, `root` under
it with what is left of its jointOrient (2e-5, -4e-5, -3e-5 — the FBX's own PreRotation) and, on the
skeleton, its translate in the Null's space; the rig's root rides Main by its parentConstraint,
which re-solves; the clean skeleton's five meshes at the top beside `Armature` (the `|Creep` group
gone), the rig's in `Group|Geometry`; the bind pose saved again whole over the joints AND the Null
(trap 79). `make_creep_armature_layout.py` (mayapy, in place, idempotent) did it: every joint
moved 3e-14, every vertex 0.0, skins at bind unchanged (3.84e-6 on ik_hand_l, as before), the rig
posed through Main/RootX_M and back to 5e-7. `make_creep_skeleton_asset.py` knows both layouts and
keeps the Null; the layout script after it takes the meshes out (a rebuild from the new rig gave the
same asset). A second Creep skeleton arrives with its Null renamed (the top node clashes) and its
`root` still called `root`.

**The exports read the standing layout** (`maya_uebridge.fbxlayout`): `in_layout` (pure — the
parent a plain transform whose world IS `WRAP_ROTATE` at the origin, the root's own orient under
0.01°) / `root_in_layout`. Cascadeur's layout writes the Null as it stands, called `Armature` in the
root namespace for the length of the export (`_named`: a rig's `Creep_Rig:Armature`, a second
Creep's `Creep_Skeleton_Armature`, whatever else answers to `Armature` held aside, all put back);
the plain layout (the roads into Unreal) takes the root OUT to world level for the length of it
(`flattened`: `jo_before` = `jo_after` undone, `unswizzled` = (x, z, -y), a keyed translate routed,
never edited, a constraint re-solving) — and a root that cannot be moved (a pairBlend) goes out in
the layout it stands in, with its Null, and says so, never as bones missing their Null. A root at
world level behaves exactly as before. Proof: `verify_cascadeur_layout.py` **10/10** (gate 5 the
keyed Creep while the animator's `|Armature` holds the name, gate 8 the pairBlend both ways, gate 10
new: a keyed Creep under its Armature to the plain file, root world 1.7e-6, the scene back exact);
`verify_creep_rig_asset.py` **16/16**, `verify_creep_skeleton_asset.py` **9/9**,
`verify_weapon_space.py` **11/11**, `verify_creep_bind_pose.py` all gates, `verify_one_shader.py`
**4/4**, and the skeletal-mesh FBX re-exported from the new asset against Cascadeur's own file
**6/6** (`verify_creep_skeleton_fbx_cascadeur.py`). The Manny and the Orc D are unchanged (root at
world level); the UE bridge's imports retarget (world space) and need nothing — there is no merge
onto a skeleton in its window any more, and a UE clip merged by exmerge onto a skeleton under a -90
Null would lie down (the wrapper trap of 2026-09-01), which is why nothing else was moved.

## The Orc: Unreal's SK_Orc_Marauder_F as a third rig row (2026-09-25)

**Out of the plugin since 2026-09-28** («орка без текстур уберем из плагина он больше не нужен»):
the catalog row is gone and `Orc_Rig.ma` moved to `sources/orc/`, where it is what
`make_orc_d_rig_asset.py` builds the textured «Orc D [rig]» from (next section; the rebuild from the
new place gave the same asset but for node UUIDs). `make_orc_rig_asset.py` writes there now;
`verify_orc_rig_asset.py` is history and no longer runs as it is. A scene holding an `Orc_Rig`
keeps working (a rig is found by its structure), and a remembered «Orc [rig]» in the dropdown
falls back to the first row. What follows is the record of building it.

The animator: «В открытом проекте в Unreal есть персонаж SK_Orc_Marauder_F его скелет
совпадает с нашим manny rig ... добавим к нам в проект еще один риг "ORC". я так понимаю что у
нас все готово просто нужно перенести». Spec:
`docs/superpowers/specs/2026-09-25-orc-rig-design.md`. The asset is in the animator's
`MyProject2` (`/Game/Orc_Marauder/Meshes/`, skeleton `SKEL_Orc_Marauder`), where Remote Execution
was OFF (UDP 6766 unbound) — the animator exported the FBX by hand; the copy the scripts read is
`C:/!!!Work/Animations/Sources/SK_Orc_Marauder_F.FBX`. `Content/Orc_Marauder/ORC.zip` is the
same uassets again, no source files.

**"Совпадает" meant the NAMES.** Measured: 91 joints, Manny's hierarchy for every shared bone,
root/pelvis/spine/legs/forearms/hands exactly Manny's (the hands' world positions to 0.0000) —
but the neck 1.39× (head 5.16 cm higher), the upper arm 1.07×, clavicle 1.05×, fingers up to
2.3 cm. So Manny's rig was NOT reused (its AS stands on Manny's bones; the orc's skin on it
tears the neck); the orc got its own rig by **the Creep's procedure** unchanged — the case it was
written for: Manny's names, a body of its own, bones orientation-only, controls on the bones'
frames, IK feet level, `skeldarRetarget = "rotation"`. Three things set from
`rebuild_orc_rig.py`: HEAD_MESH/ROOT/LAYER, and **Manny's ik_hand rule** (ik_hand_gun and
ik_hand_r follow hand_r, ik_hand_l hand_l, from where the file has them) in place of the
Creep's (ik_hand_gun zeroed — that animator's layout). The twist bones stand at exactly 1/3,
2/3 (AS's own spacing), so `place_parts` moved nothing.

Two design answers from the animator: **all four helper bones added** («все четыре») —
camera_root/camera_bone/weapon_r/weapon_l with Manny's LOCAL values from
`manny_skeleton_template.json` (relative to their parents as on Manny to 2.8e-14; they are not
in `SKEL_Orc_Marauder`, so Unreal skips them or they are added there); **the shoulder pads
`AB_Armor_Shoulder_L/R` ride their clavicles**, no control. Decided without asking: LOD0 only
(`Orc_Body`), the blendShape kept (52 ARKit + 4 elbow correctives, weights 0, undriven), key
`Orc_Rig`, label «Orc [rig]», the third row; export wrapper `Orc` (`Armature` since the evening).

Pipeline: `make_orc_source.py` (mayapy: out of the FBX wrapper into Manny's shape, helper bones,
bind pose whole over 95 joints, Blender properties deleted) → `rebuild_orc_rig.py` (LIVE, a
disposable Maya — this time on port **7003**, because a peer session may hold 7002) →
`make_orc_rig_asset.py` (mayapy → `assets/Orc_Rig.ma`, 22.1 MB). Proof:
`verify_advancedskeleton_orc_rig.py` **29/29 live**; `verify_orc_rig_asset.py` **16/16
standalone** (orientations 0.00127°, limb directions 0.062°, lengths 0.000000 cm, the other two
rigs 0.000000000, weapon_r carried in the hand to 2e-6, camera_root to 3e-16, the export 95
joints / 0 meshes under `Orc`); `verify_connections.py` with `VERIFY_RIG = "Orc_Rig"` **40/40
live**; 2254 unit tests. The fur cards read dark in the viewport under our colour blinn (no
opacity map in the asset) — cosmetic, stated.

82. **An FBX from Unreal can carry the DCC's own properties on its joints, and our exports then
    write them back into every clip.** The orc was made in Blender with Auto-Rig Pro: root held
    `flip_fluid` (a `<bpy id prop ...>` string), `set`, `binded`, `arp_rig_name`, eleven helpers
    `ori_name`. The first export of the rig wrote them (the read-back printed `setAttr: No object
    matches name: Orc|root.flip_fluid`), and Unreal reads the root's properties as game data
    (trap 40). Delete every user attribute on the joints but Maya's own `filmboxTypeID` /
    `lockInfluenceWeights` (and our `skeldarCharacter`, which the export holds off itself).
83. **No clip on this disk moves `weapon_r` in the hand or `camera_root` at all** (measured on
    five, 2026-09-25) — so a gate "the retarget carries the helper bones" passes on a bone that
    stands still. `verify_orc_rig_asset.py` keys a move of each into the clip's own copy at
    mid-take and requires the motion (0.43 in the hand, 20 cm) before it trusts the match.
84. **Purging SOME of our modules splits a class in two** (trap 49 from the harness side): a
    payload that dropped `maya_rigs` but not `maya_asretarget` left the latter holding the old
    `Rig` class, and `maya_rigs.node(rig, ...)` fell through `isinstance(rig, Rig)` into
    `TypeError: can only concatenate tuple (not "str") to tuple`. Purge all our package roots
    together, or none.
85. **A disposable Maya is a real window on the animator's desktop, and the animator can click
    in it.** Mid-session its scene suddenly held `Manny_Rig:*` and no orc; no process of ours had
    sent it anything — «это случайно», the animator had pressed something there. Re-read a
    disposable scene's state before trusting it, like the live one (note 4).

## The Orc D: SK_Orc_Marauder_D in Unreal's own textures (2026-09-28)

The animator: «Давай добавим еще один вариант орка но на этот раз SK_Orc_Marauder_D ... и для этой
версии сделаем материал с текстурами», MyProject2 open in the editor. Spec:
`docs/superpowers/specs/2026-09-28-orc-d-textured-design.md`, plan beside it. **The fourth rig row
«Orc D [rig]»** (`Orc_D_Rig`, `assets/Orc_D_Rig.ma`, 12.4 MB) and **the first CHARACTER that
arrives in its textures** (`catalog.Character.textured`).

**Out of the editor by script, not by hand**: the animator ticked Project Settings > Plugins >
Python > Enable Remote Execution (instant, no restart; UDP 6766 came up) and
`export_orc_d_from_unreal.py` (mayapy, `uelink`) wrote `sources/orc/`: the FBX (LOD0 + 56 morph
targets), seven Texture2Ds as PNG — **an `AssetExportTask` of a Texture2D to `.png` writes its
SOURCE data** (the image as imported, 4096², not the platform compression; byte-identical on a
re-run) — and `orc_d_materials.json`, every parameter the maps are baked with. A
`CurveLinearColorAtlas` does not export (FAILED); its `gradient_curves` are sampled instead.

Measured first:
- **D's skeleton IS F's**: 91 joints, every rest world matrix and every bindPreMatrix equal to F's to
  **0.0**. So nothing was rebuilt live: `make_orc_d_rig_asset.py` (mayapy) opens `Orc_Rig.ma`,
  deletes F's mesh, and binds D's onto the same game joints — the FBX's weights vertex for vertex
  (0.0), its 56 targets sampled at weight 1 (2.4e-7 cm), the FBX's own output mesh duplicated (so
  points, UVs and normals are Unreal's to 7e-9 / 0.001° / 7e-9), `map1` the only UV set.
- **Five sections in Unreal**: Cloth, Body, Eye, Skirt_Sim (the one using cloth simulation,
  `SkeletalMesh.is_section_using_cloth`) and **Skirt_Proxy** — 885 faces / 489 vertices, one shell
  a median 1.65 cm off the skirt: the clothing asset's cage. Dropped (trap 92). No fur in D.
- **Unreal's material maths, read off the master materials' GRAPHS** (trap 93), baked into the
  maps by `make_orc_d_textures.py` (numpy, all in linear, sRGB last, refuses clipping): body
  `lerp(pow(base·1.70377, 1.095925), TattooColorA·atlas(u), tattooMask.R)` (Saturation clamped to 1
  by the graph, the body colour mask off, Skin_Color white — no-ops); cloth `base·1.5`, its
  opacity mask the base colour's ALPHA at clip 0.3333 → a 0/255 PNG (4.8 % cut: the chain-mail
  netting, the fringes); eye `shadow(uv)·lerp(sclera·2.30, iris·4.16·limbus, irisMask)` without the
  refraction, 1024²; normal maps renormalised with green flipped (Unreal's are DirectX).
- **2048 JPG** (the animator's pick over 4096 JPG and 4096 PNG, «2048, JPG»): six maps, 7.4 MB in
  `assets/Orc_D/`; the build zip 65.0 MB, 102 files.

**Four materials, one shader** (phong wearing `colour.LOOK`, `colour.TEXTURE_MARKER`): body
(colour + normal through a bump2d in tangent-space mode), cloth (the same), eye, and **ClothCut** —
the cloth's own colour and normal file nodes plus the cut on `transparency`, worn ONLY by the 106 of
20122 cloth faces whose uvs touch a cut texel (the mask grown a texel for the bilinear filter;
`faces_touching_cut`: a summed-area table, then texel centres in the fan triangles) — trap 95.
So a textured character wears one material per texture set. **The asset
names its images RELATIVELY**: each file node carries `colour.ASSET_IMAGE`
(`skeldarAssetImage`, "Orc_D/<file>"), colour space set with `ignoreColorSpaceFileRules` (Raw for
normals and the cut), and **Add Character points them at the installed copy**
(`colour.relink_images(nodes, catalog.asset_path)`, pure half `relink_plan`) — no path of the
building machine is in the `.ma`, and a test pins it. A textured Add paints nothing, does not move
the swatch, turns Textures on in every model panel where they are off, and says «textured
(viewport textures on)» (`character.appearance`, pure; a missing image is named, the character
still arrives). **Recolour replaces the textures** with a colour (Spear 03's ruling, a whole-shape
assignment over the per-face ones); the next Add is textured again.

Proof: `verify_orc_d_rig_asset.py` — **19/19 standalone** (the third rig beside the two Orc D is
a Manny since the F orc left the plugin; gate 19: Maya's own sampler at the
centre and near the corners of all 20016 opaque cloth faces, 80064 samples, 0 in a cut): two Orc D and an F orc added (the F red,
the palette untouched by the D's), rotation-marked, at bind, controls at default; the file node
samples the JPG's pixels to 0.0000 the right way up (flipped rows 0.61); the cut mask 0 / 1;
Unreal's mesh minus the proxy to 7.45e-9 cm; the targets to 2.4e-7; **under a retargeted take,
D's mesh where the FBX's OWN skin puts it with its joints on the rig's: 4.2e-5 cm**; the button
onto D (orientations 0.0008°, lengths 0.000000 cm), the other two 0.000000000; Recolour, re-Add;
the export 95 bones, 0 meshes under `Armature`. A playblast in a disposable Maya (port 7003,
scratch `MAYA_APP_DIR`) shows it textured, normal-mapped, the vest's torn edges cut, the eyes.
2379 unit tests; the installed copy refreshed in the animator's Maya over the port.

Not built: F textured (the same maps fit all but its fur), the fur, the cloth simulation, the eye's
refraction, the skin's subsurface scattering.

**A first-person mesh beside it, `Orc_D_1P`, and `Main.view` (2026-09-28)** — the animator: «В сцене я
добавил новый меш для 1P анимацией. Давай обновим риг орка в нашем плагине». Measured in their scene
first: the rig untouched node for node, `Orc_D_Body` renamed `Orc_D_3P` (out of the rig's namespace —
a rename in the outliner does that), and a new `Orc_D_1P`: the 3P without its head (8049 vertices
gone, y 155–183, the eyes with them) — every one of its 33365 faces a 3P face by its vertices'
positions, none ambiguous, in the same order, its 19458 vertices likewise (coincident vertices in the
3P, where shells touch, make a match by vertex position alone ambiguous — 4872 faces unmatched that
way; by whole faces, none), uvs identical. Its skin was a quick bind: max 5 influences, weight on
`weapon_r` (0.50), `weapon_l`, `camera_root`/`camera_bone` (0.31 at the neck) and `ik_hand_gun` on
the LEFT hand — bones that move on their own. Asked: «Веса 3P» and «Переключатель на Main».
`sources/orc/orc_d_1p_faces.json` records which 3P faces the 1P keeps (read off the animator's mesh
over the port); `make_orc_d_rig_asset.py` builds the 1P from the 3P by deleting the rest (the same
order again), skins it on the same 91 joints with the 3P's weights one for one, both skins on the
whole bindPose1, no blendShape (the face shapes went with the head), and adds `Main.view` — enum
`3P:1P`, 3P by default, in the channel box, NOT keyable (a view, not animation: no bake or key takes
it) — driving each mesh's visibility through a `condition`. The asset: 17.7 MB. Proof:
`verify_orc_d_rig_asset.py` **22/22** (gate 20: under the retargeted take every 1P vertex on its 3P
vertex to 0.0 cm; 21: the 3P's materials, no eye — 13243 / 20016 / 106; 22: the switch both ways, not
keyable, untouched by the retarget). A scene with an Orc D added before this has no 1P: re-add it.

**…and the 1P alone as an FBX** (the same day: «Отэкспортируй отдельный файл орка для 1p только с новым
мешем»): `export_orc_d_1p_fbx.py` (mayapy, the shape of `export_creep_skeleton_fbx.py`) →
`Animations/Rigs/Characters/Orc_D_1P.fbx`, 9.0 MB: the rig's constraints off the skeleton, the bones
re-seated at the bind (4.3e-14), `Orc_D_1P` out of the Geometry group made visible (`Main.view` hides it
by default), the 3P and `Group` deleted; our layout (`Armature` -90 X over `root`), 30 fps, 95 bones, the
one mesh with its three materials under plain names (`Orc_D_Body_Mat`, `Orc_D_Cloth_Mat`,
`Orc_D_ClothCut_Mat`) and their five images EMBEDDED. Read back from a copy in a temp folder (the importer
extracts embedded images into a `.fbm` beside the file it reads): the header, the tree, each image in
the file byte for byte, nothing of the rig or the 3P or our markers; imported, every vertex where the
asset has it to 9.9e-5 cm, weights and uvs exact, faces per material 13243 / 20016 / 106, colour, normal
map (bump2d, tangent space) and the cut wired back. **Unreal's mesh is split along its normal seams: all
5345 hard edges of the 3P/1P are BORDER edges, every interior edge smooth**, and the importer brings
every border back hard — the 1P's 8 neck borders (interior in the 3P, smooth-flagged) came back hard,
which shades nothing; the check compares interior edges and counts borders. A playblast in a
disposable Maya shows it as Add Character's Orc D shows it, headless.

90. **A duplicate of a deformed mesh carries its source's COMPONENT TAGS** — `gtag[i].gtagnm`
    naming the SOURCE's deformers (`srcD:skinCluster1`), written into the saved `.ma`. The asset's
    banned-word check caught the namespace. `removeMultiInstance` every `gtag` on the copy before
    deforming it; the new deformers make their own.
91. **Deleting a skinCluster takes its bindPose with it.** `Orc_Rig.ma`'s `bindPose1` (95 joints)
    was gone the moment F's skin was deleted; a new one saved WHOLE over every joint (trap 79's
    rule, its constraint children removed again) is what the new skin connects to.
92. **Unreal's FBX export of a skeletal mesh writes every section, the clothing asset's proxy
    cage included**, as its own material slot, with nothing to say it is not drawn. Identify it
    (the slot's name, `is_section_using_cloth` on the neighbour, one shell hovering off the
    render mesh) and drop it, or it pokes through the skirt.
93. **Unreal Python: `Material.expressions` is protected**, but
    `MaterialEditingLibrary.get_material_expressions(m)` +
    `get_inputs_for_material_expression(m, e)` +
    `get_input_node_output_name_for_material_expression(e, input)` +
    `get_material_property_input_node(m, MaterialProperty.MP_BASE_COLOR)` walk the whole graph —
    the parameter NAMES alone said "BC_Intensity", the graph said `pow(base·I, C)` after a
    clamped saturation, and which mask channel the tattoos read.

94. **An install with the hub open left the hub on the OLD build** — trap 75 from the
    installer's side (2026-09-28, the Orc D: «у меня нет возможности выбрать orc d»). The copy
    and the purge happened, the catalog in memory listed the row, and the dropdown on screen
    was still the one the old modules had built; nothing rebuilt it until somebody pressed the
    shelf button (only `maya_update._reopen` did it for them). `install.install` now schedules
    `rebuild_open_hub(dest)` (`evalDeferred`, lowest priority — an install run from a hub
    button must not delete the layout holding it) when `HUB_CONTROL` stands: the FRESH
    `maya_hub`, the installed folder first on `sys.path`, `rebuild()` in the standing control.
    Measured live: `maya_hub` absent right after the install, then a new module object from the
    installed copy with `_BUILT_HERE` True and the new row in the dropdown, no press.
95. **Viewport 2.0's default transparency (Object Sorting) draws a material with ANY transparency
    input in the transparent pass whole, and does not depth-sort inside one render item.** The
    Orc D's whole cloth wore the cut-out: from behind the vest's leather drew over the metal
    shoulder plates, the belt over its buckle, the wraps over the knee pads (the animator: «при
    стандартных настройках рендера определенные части орка просвечиваются»). The distant shots
    had looked right; a diff against the same scene with the transparency disconnected found
    12k–57k pixels per view. A binary mask does not help — the pass is chosen by the connection.
    Give the transparency only to the faces that touch the cut (106 of 20122 here): the diff
    fell to 44–1515 pixels, all on the vest's torn edge. `hardwareRenderingGlobals.
    transparencyAlgorithm` is the animator's scene setting, not ours to change on an Add.

## Manny in Unreal's own textures, the rig and the skeleton (2026-09-30)

The animator: «Давай для нашего мени рига и скелета найдем текстуры и добавим их в проект точно так же как и
для орка». Spec `docs/superpowers/specs/2026-09-30-manny-textured-design.md`, plan beside it. Both Manny rows,
«Manny [rig]» and «Manny UE5 [skeleton]», are `textured=True` since: the Orc D's road end to end (the plugin's
code did not change, only the catalog flags, the assets and the scripts that make them).

**Measured first** (MyProject2 open, Remote Execution on):
- the editor holds TWO Mannys: the Third Person template's (`/Game/Characters/Mannequins/`, textures 1024²,
  its mesh's UVs 0.017 off ours) and the Orc Marauder pack's demo copy
  (`/Game/Orc_Marauder/Demo/Characters/Mannequins/`, 4096²). **Our `Skin_3p` IS the demo `SKM_Manny_Simple`
  index for index** (every UV to 7.5e-9, points to 0.073 cm), and `Hands_1P` (arms, shoulders, hands, 72–162 cm)
  is a cut of it (all 21570 vertices on Unreal's to 0.0001 cm, position and UV). Both shipped files had lost
  Unreal's per-face split (one material on every face) and still carried dead `MI_Manny_*` networks naming
  `D:/dev/temp/...` and `/Users/Shared/Epic Games/...`;
- the demo `M_Mannequin`, read off its graph as T3D (an `AssetExportTask` of a Material or MaterialFunction to
  `.t3d` writes every expression, its properties and links — the way through the NamedReroutes whose
  `declaration` the Python API will not read): Masked with no opacity mask (opaque), ClearCoat. The base
  colour is a metal/plastic lerp chain over `D` with desaturations, brightnesses, a Tint and
  `ML_BaseColorFallOff`; **at both instances' values every lerp collapses and the colour is `D` itself**. The
  `Normal` pin reads `_N` (the clear coat's, nearly flat); the bevels are `_BN` on
  `ClearCoatNormalCustomOutput` (the base layer). The torso's emissive is `MF_logo3layers`: `T_UE_Logo_M`
  at `ScaleUVsByCenter(uv + (−0.241, 0.259), 0.076)` (= `(uv − 0.5)/S + 0.5`, read off the engine function),
  three parallax/blur layers, layer 0 `(0, 1, 1) × 16`.

**The pipeline** (all re-runnable, docs/superpowers/plans/):
- `export_manny_from_unreal.py` (uelink) → `sources/manny/`: the demo `SKM_Manny_Simple.fbx` (LOD0 — which face
  wears `M_HeadLegs` / `M_Torso`), `textures/T_Manny_0{1,2}_{D,BN}.png` + `T_UE_Logo_M.png` from SOURCE data,
  `manny_materials.json`;
- `make_manny_textures.py` → `SkeldarAnim/assets/Manny/Manny_{HeadLegs,Torso}_{Color,Normal}.jpg`, 2048 q95,
  3.9 MB: colour = `D` shrunk in linear (the script re-checks the collapse's parameters and refuses
  otherwise); the torso gets the logo's layer 0 **saturated into the colour** (the animator's pick, «Запечь
  лого в цвет»: `lerp(D, cyan, saturate(16 · logo · sphereMask))`, supersampled 4×4 in its box — one sample a
  texel drew the saturated edge in steps), no glow, no parallax; normals = `BN`, renormalised, green flipped;
- `make_manny_textured_assets.py` dresses `assets/Manny_Rig.ma` and `Manny_Skeleton.ma` IN PLACE (mayapy, one
  process per asset): Unreal's slot per face (`Skin_3p` by its vertex-id triples, all 92178, **38166 /
  54012** as Unreal's; `Hands_1P` by position+UV-matched vertices, all 40258 faces by their ids, 8402 /
  31856), two materials `skeldarTexture_Manny_HeadLegs` / `_Torso` (the one shader wearing `colour.LOOK`,
  `TEXTURE_MARKER`, colour sRGB, normal Raw through a bump2d in tangent space, `ASSET_IMAGE` "Manny/…"), all
  unused shading deleted (36 nodes in the rig, 57 in the skeleton — AdvancedSkeleton's unassigned lamberts
  there too), the UV set left `DiffuseUV`. **And it proves nothing else changed**: the header must be the same
  bar the name/date/UUID/requires, and every body line `git diff` reports must be shading, the meshes' face
  groups (groupId/groupParts, `.iog`, the input now through a groupParts), the shading lists' counts, the
  scene singletons' fresh uuids, the external-content table, or two measured resave noises (`.ndt 0` on a
  mesh, a constraint's cached `.lr` in the last digits) — rig and skeleton: **0** lines otherwise.
- the portraits: Manny's rendered again textured; **the Orc D's shipped portrait was half-loaded too** (grey
  shoulder pads and belt) and was rendered again — trap 120.

Proof: `verify_manny_textured.py` **12/12** standalone (the slot face by face: at 1364 faces our colour against Unreal's `D` for the face's own slot mean 0.028, median 0.008, against the other slot's 0.34; the logo agreeing with the pattern Unreal's maths draws from `T_UE_Logo_M` at 925 of 960 decided samples, Unreal's `D` cyan at none; the normals `BN` to a median 1.62°; the skins as far off their bind as before, 0.0719 at the left calf — Manny's own); `verify_rig_pipeline.py` **30/30** (its gate 24 compared the sword with the bone itself, stale since the socket turn — it now asks `bonedrive._seat_of`), `verify_many_rigs.py` **32/32**,
`verify_add_character.py` **31/31** in the disposable Maya (its gate 21 still expected the label «UE4 Mannequin»; it reads the catalog's now), `verify_one_shader.py` **4/4**, `verify_orc_d_rig_asset.py` **22/22** (its palette control
rig is a Creep now — the Manny arrives textured); a disposable Maya (port 7005, scratch `MAYA_APP_DIR`) showed
it white with its dark inserts and the cyan chest logo; 2829 unit tests; the installed copy refreshed. A Manny
added before this still wears its palette colour: re-add it. The Colour section still repaints a Manny (the
textures give way to a colour, the next Add is textured again).

119. **A file node given a relative path that resolves FROM THE PROCESS'S WORKING DIRECTORY stores it
     absolute.** The Manny build run from `SkeldarAnim/assets/` got `C:/!!!Work/.../assets/Manny/...` back for
     `Manny/...` (the banned-word check caught it); run from the repo root it stayed relative — and the Orc D's
     build never saw it, its scene being in `sources/`. A build that writes relative texture paths works from an
     empty folder (`os.chdir(tempfile.mkdtemp())`) and asserts `fileTextureName == ASSET_IMAGE` before saving.
120. **Viewport 2.0 loads textures only while Maya is IDLE.** The portrait's "six draws half a second apart"
     blasted the textured Manny near black; a `time.sleep` between blasts let two blasts agree on a half-loaded
     torso. Between blasts run `maya.utils.processIdleEvents()` + `QApplication.processEvents()`, and wait for
     two identical blasts after at least three. The Orc D's portrait had shipped half-loaded the same way.
121. **mayaUsd makes a `UsdDefaultRenderSettings` on every file open and renames the file's own out of its way**,
     so every open-and-resave adds one: `Creep_Rig.ma` carries ten, `Orc_D_Rig.ma` three. The Manny build deletes
     the one the open made (by the UUIDs the file's text names) and gives the file's their names back.
122. **The second file opened in one mayapy session comes back with `shapeEditorManager1` /
     `poseInterpolatorManager1`** (the scene's own were already there). One asset per process.
123. **`difflib.SequenceMatcher` on a 1.2-million-line `.ma` ran over half an hour**; `git diff --no-index -U0`
     answers in seconds.

## The Creep in its own textures, the rig and the skeleton (2026-09-30)

The animator, with three images (`Downloads/creep_body_diff.png`, `creep_body_norm.png`, `creep_face_diff.jpg`):
«Вот текстуры для крипа давай сделаем тоже самое что и для мени»; asked, **the whole Creep** («Весь Крип»).
Spec `docs/superpowers/specs/2026-09-30-creep-textured-design.md`. «Creep [rig]» and «Creep [skeleton]» are
`textured=True` since — so **every row but the UE4 Mannequin arrives textured**, and that mannequin is what the
unit tests' "an untextured row is still painted" uses now.

**Measured first:**
- the body's two images are byte for byte what the Creep's Cascadeur FBX (`sources/creep/creep_T-pose_draft.fbx`)
  embeds as `8.png`/`9.png`, the head's colour its `0.jpg` re-encoded (mean 0.0006). That FBX's meshes wear:
  `body` 8/9, `face` 0/1, and `back`, `arm_l`, `arm_r` ONE shared set 2/3 (4/5 and 6/7 are the same bytes).
  Its materials are phongs at full colour — no maths to bake;
- **our five meshes carry that FBX's UVs index for index** (counts, values to 7.5e-9, per-face uv ids);
- **the normal maps' green, by the curl of the field**: a height field's normals are curl-free, so in image
  coordinates (x right, rows down) `d(nx)/dy` and `d(ny)/dx` correlate positively for DirectX, negatively for
  OpenGL. Unreal's own maps as controls (+0.27, +0.39 at 512²), our flipped Manny map −0.39: **the body −0.24
  and the back/arms −0.30 are OpenGL (Maya's) already, the head +0.61 DirectX** — at 256..2048 alike, and by
  the residual curl of either reading. One character's sources can mix conventions.

**The pipeline**, the Manny's with its machinery shared:
- `docs/superpowers/plans/asset_dress.py` — what dressing a shipped `.ma` needs whatever the character (the empty
  working folder of trap 119, the open with mayaUsd's extra `UsdDefaultRenderSettings` dropped, the one-shader
  textured material, a previous run's materials, unused shading, the relative-image check, the save with the
  header, banned words and `git diff` explained line by line, one process per asset). `make_manny_textured_assets.py`
  runs on it now; re-run into scratch (`--out DIR`) it gave its committed assets again, down to shading
  bookkeeping (group ids renumbered, component lists, SG links);
- `sources/creep/textures/`: the animator's three under their names, the FBX's `1.jpg`/`2.png`/`3.png` as
  `creep_face_norm.jpg`, `creep_limbs_diff.png`, `creep_limbs_norm.png` (the `.fbm` folder is not in git);
- `make_creep_textures.py` → `assets/Creep/Creep_{Body,Face,Limbs}_{Color,Normal}.jpg`, 2048 q95, 8.2 MB: the
  colour as it is, the normals renormalised with the green flipped where the curl test says DirectX (the head),
  a map it cannot decide (|corr| < 0.1) refused;
- `make_creep_textured_assets.py` dresses `Creep_Rig.ma` and `Creep_Skeleton.ma` in place — **the Creep pipeline's
  last step now**, after `make_creep_weapon_sockets.py`: `skeldarTexture_Creep_Body` on `Creep_Body`, `_Face` on
  `Creep_Face`, `_Limbs` on `Creep_Back`/`Creep_Arm_L`/`Creep_Arm_R`, each mesh whole; the uv counts checked
  against the FBX's; `fileInfo "exportedFrom"` removed (both assets carried the path of the animator's creature
  scene in Downloads); **0** body lines changed but shading. The Creep portrait rendered again textured.

Proof: `verify_creep_textured.py` **12/12** standalone (per mesh, our colour against its own set's source 0.011–0.035
on the mean over its faces, against each other set 0.07–0.15, own/nearest-other at worst 0.26; the normals as
decided to 2.3/1.0/2.4° against 10.4/1.6/11.5° the other way; skins at their bind 3.8e-6); `verify_creep_rig_asset.py`
**16/16**, `verify_creep_skeleton_asset.py` **9/9** (their "painted" gates now ask for the three textured materials),
`verify_creep_bind_pose.py` all gates, `verify_one_shader.py` **4/4** (its hand export of the Creep's meshes carries
three materials, each with the look), `verify_orc_d_rig_asset.py` **22/22**, `verify_weapon_space.py` **11/11**,
`verify_inventory.py` **14/14**; 2959 unit tests. A Creep added before this still wears its palette colour:
re-add it.

124. **The Creep assets carried `fileInfo "exportedFrom" "C:/Users/MY PC/Downloads/creep_T-pose_MIX_06_skin.mb"`**
     since they were first cut out of the creature scene — a path of the animator's machine in a file every colleague
     receives, which no check had looked at (the catalog tests read `createNode` lines). The dressing's banned-word
     check found it; `asset_dress.save_checked(drop_info=...)` removes a fileInfo and expects exactly that line gone.
125. **An open-and-resave rewrites numbers that did not change**: a constrained joint's cached rotate comes back
     re-evaluated (1e-6°), and a double is printed with other digits (`5.497270456626897e-05` /
     `5.4972704566268963e-05`). A text check allows a hunk that replaces lines one for one with the same text but
     for numbers within 1e-5 — nothing looser.

## The weapon inventory: two hands, the floor, a Diablo window (2026-09-29)

The animator: «Возможно ли сделать во вкладке Weapon кнопку которая будет инвентарь похожий на
инвентарь как в игре diablo что бы я оружие переносил из этого инвентаря прямо на персонажа и оно как
вставлялось в руку или выпадало на пол?» Asked, and answered: a weapon on the floor is the
CHARACTER's (its hand's bone follows it — the Connections "World" state); **two weapons per
character, one per hand**; a weapon dropped into an occupied hand REPLACES (Add's rule); look A,
Diablo. «делай все». Spec: `docs/superpowers/specs/2026-09-29-weapon-inventory-design.md`, plan
beside it. Proof: `verify_inventory.py` **14/14 standalone** (Manny + Creep, two hands, the floor, a
retarget, the export); `verify_inventory_live.py` **setup 13/13 + drops 8/8 live** in a disposable
Maya (a scratch `MAYA_APP_DIR`, port 7003, killed after) — Connections with two weapons, the window
open, `drop_at` onto the projected left hand and onto the floor; `verify_connections.py` **40/40**
there (one weapon: unchanged); 2651 unit tests.

**Two weapons.** Structurally the hands were already independent (a space and a drive bone each);
what assumed one weapon was the Weapons section (every press on `weapon_r`), Connections
(`weapon_of` answered one node) and `window._attached` (a weapon out in world read as "the hands
ride it").
- **Weapons > `Hand [Right | Left]`** (`window._HAND`, remembered in `mayaSceneSetup_hand`): Add,
  Remove, the grip fields and Recolour act on that hand; its bone is `catalog.side_bone` (`weapon_r`
  → `weapon_l`). The panel names, and remembers the grip of, the weapon IN that hand
  (`_held_entry`), not the dropdown's.
- **The grip is remembered per hand** (`grips.py`, shared with the inventory): the right hand keeps
  `mayaSceneSetup_offset_<key>`, the left has `..._L`. An undialled left grip is the MIRROR of the
  right one through the rig's own sockets — `bonedrive.mirror_grip`: G_l = Mz · G_r · Fr · S_r · F ·
  S_l⁻¹ (Mz the model's thickness mirror, Fr its frame, S the drive bones' local matrices in their
  hands, F the hands' behaviour mirror). Measured: every shipped rig's hands are UE's behaviour mirror
  (`hand_l = F · hand_r · Mx`, 0.0003 cm on Manny/Orc, 0.045 on the Creep) but the weapon bones are
  not — Manny's `weapon_l` stands **6.9 cm / 2.16°** off the mirror of `weapon_r` and at ZERO grip a
  left sword points its blade **backwards** (−0.9993); the mirror grip is (1.39, 0.49, −178.42) /
  (6.62, −1.71, −0.98) and stands the left sword as the world mirror of the right to **2.9e-4** at
  the build pose. The Creep's own `weapon_l` mirrored differently: its zero grip came out a half turn
  ABOUT the blade (179.9, 0.05, 179.8). **Since 2026-09-30 (one socket, below) the numbers moved**:
  the frame is the socket-composed one, Manny's left fields read (1.38, −1.58, −179.51) / (6.62,
  −0.98, 1.71), and the Creep's weapon_l is UE's, so its zero grip mirrors like Manny's, a half turn
  about the THICKNESS (0.09, −0.05, −179.77) / (0.01, 0.08, 0.01).
- **`linked` means the hands ride it** (`connections.followers_of`, the proxies inside it): a weapon
  out in world that nothing rides is its hand's to replace or remove, and `attach.detach` takes it
  off (a weapon on the floor hands its parked track back). A hand holds XOR follows, in every path.
- `attach.import_weapon` is split out of `attach` (the import, mark, seat, dress — a weapon at world
  level for the floor) and records `mayaWeaponSource` (the file), so the inventory can put the same
  weapon into another hand.
- **Connections acts on ONE weapon at a time**: an `Acts on [<A> | <B>]` chooser (two fixed segments,
  an empty one disabled "-"), the selection naming one too — `choose_weapon` (pure): the pick while
  the selection is what it was at the pick, else the selection's, else the pick, else the first.
  Each weapon keeps its own scheme; `blocked` (pure) refuses by name a hand the other weapon hangs in
  or rides, and a hand whose bone the other weapon drives from world. A holding hand rides nothing,
  so no chain of rides can loop. The drive bone is per weapon (`driven_side(rig, bones, weapon)`).

**The floor** (`floor.py`): `attach.import_weapon` at world level, `lying_pose` (pure: thickness up,
blade along the camera's right, the box's middle over the point, its lowest point on Y = 0), the
bone's own curves **parked** on the weapon (`bonedrive.park`: reconnected to doubleLinear/doubleAngle
attributes, never baked — «анимация сохранилась в исходном виде»), the bone on the weapon's socket
(`bonedrive.drive_socket`, moved out of Connections). Taking it off while it lies there reconnects
the SAME curve nodes (measured: keys, values, tangents identical). **`bonedrive.relink` leaves a
weapon no hand holds where it is** and parks the fresh track — a retarget kept the floor spear to
0.0 and parked the clip's `weapon_r` (2.4e-4 cm). A hang in Connections drops the parked track. Whose
weapon: the character nearest the point; which bone: the free one, right first; both taken → the
right one's replaced.

**The window** (`maya_inventory.py`, `maya_invlook.py` — stdlib: palette, cells, packing, layout,
hits; `maya_scenesetup/droptarget.py`, `equip.py`): Weapons > **Inventory** or the hotkey row
`window.inventory`. A frameless tool window (bronze bevel, gold small-caps «Inventory», parchment —
in the hub's own look since 2026-09-30, below), object name `skeldarInventory` (an update's `show()` deletes an older module's window by name), its
position in `skeldarInventoryGeometry`. The grid (10 × 5 cells of 40 logical px) is the catalog;
two hand slots show the current character's hands (the right hand on the viewer's LEFT) — held,
dimmed «on the floor», or «follows <weapon>». A press on an item captures the mouse for the whole
drag (Maya's viewport never sees it, Maya's drop handling never enters); a ghost with the icon and
a caption naming the target follows the cursor; Esc / right button cancels. The target
(`droptarget.choose`, pure): a character whose nearest bone ON SCREEN is within max(16 px, 8 % of
its projected height) is under the cursor, its hand nearer the cursor the target; else the camera
ray meets Y = 0 and the nearest character owns the weapon. Bones, not meshes — a bare skeleton too,
no ray against 70 000 skinned vertices per move. Measured live: the cursor on the projected
`hand_l` aimed at the left hand; Spear 01 dropped on the floor lay **0.2 cm** from the point, its
lowest vertex at 0.000000. **Icons**: `docs/superpowers/plans/make_weapon_icons.py` renders each
catalog model's own triangles (mayapy, offscreen QPainter: steel above the grip, bronze guard,
leather grip, wooden shaft by a shape rule — no model says which part is which; Spear 03 from its
texture) into `assets/weapon_icons/<key>.png` at 80 px per cell with `weapon_icons.json` (cells from
the length: Dagger 2, Creep Sword 3, Long Sword 4, spears 5). A new catalog row needs its icon (a
test pins it): re-run the script.

103. **A drive bone that follows a weapon on the FLOOR is not standing on its socket.** The mirror
     grip read `weapon_l`'s local matrix while it followed a floor spear, so the "socket" was the
     floor: a sword moved into the left hand stood **134 cm** off it, and `to_hand` REMEMBERED that
     grip. `grips.socket_of` reads such a bone from its own parked track (1.1e-16 against the socket
     before the drop), and `to_hand` computes the grip after the old weapon is off (6.9 cm from
     `weapon_l` after — Manny's own socket asymmetry). Anything that reads a weapon bone's local
     matrix must ask first whether a world weapon drives it. (Since 2026-09-30 `to_hand` remembers
     nothing at all — trap 107.)
104. **A chooser pick lost to the selection an Apply leaves behind.** Connections' own presses
     (OverRig's parent_in/out) leave the weapon selected, and "the selection names the weapon"
     snapped a pick of the other one straight back. The pick holds while the selection is what it
     was at the pick (`_PICKED["selection"]`).
105. **A disposable Maya with a fresh `MAYA_APP_DIR` opens the Home screen and keeps `MayaWindow`
     hidden**: every model panel reads 100 × 30 with a 1 × 1 port, `getPanel(visiblePanels=True)`
     answers None, and a projection lands nowhere — while `playblast` still works (it renders
     offscreen), which hides the problem. `showWindow MayaWindow` and a Win32 `ShowWindow` did not
     tell Qt; hiding the `MayaAppHomeWindow` top-level (a `QWebEngineView`) and `setVisible(True)`
     on the main window did. Probe `M3dView.portWidth()` before trusting a projection.
106. **The Weapons dropdown names the NEXT Add, not what the hand holds.** With one weapon the two
     rarely differed; with two, the Left hand's status read «Long Sword 02 on hand_l» over a dagger,
     and dialling the fields saved the dagger's grip under the sword's key. Messages and grip memory
     follow the weapon in the hand (`_held_entry`, by its marker key).

**The grid is rearranged by hand** (minutes later: «Давай сделаем так что бы оружие в инвентаре можно было
перетаскивать по инвентарю»; spec `2026-09-29-inventory-rearrange-design.md`): a grid item released in the
grid MOVES - its grab point stays under the cursor, the spot clamped into the grid - or SWAPS with the one
item it lands on when that one fits where the first came from (the animator's pick over refusing and over
Diablo 2's pick-up-the-other); two items under it, or the other not fitting back, is «no room» and nothing
moves. `maya_invlook.plan_move` / `arrange` / the record are pure; a green or red preview of the cells while
dragging; the layout remembered in `skeldarInventoryLayout` (JSON) and read back through `arrange` - a stored
spot kept while it lies in the grid and overlaps nothing, a new catalog row or a broken record packed into
the free cells, never an item lost; right click on the grid → «Sort the inventory». No scene change, no
undo. 2672 unit tests.

Not built: custom FBX files in the inventory (Weapons > FBX... stays); a pickup
at a chosen frame; a ray against meshes; more than two weapons per character — the floor counts:
a floor weapon holds its hand's bone, so a character has at most two weapons in hands and on the
floor together. **The drag itself (a real mouse over the viewport) is the animator's to try**: the
bridge drives `drop_at`, everything but the mouse.

## One weapon socket for every rig, and the inventory in the hub's look (2026-09-30)

The animator: «Давай сделаем дизайн инвентаря все же не в стиле диабло а в стиле нашего интерфейса.
Также сейчас некоторые виды оружия нужно поворачивать на 90 а некоторые сразу встают в руку, давай
сделаем так что бы по умолчанию все виды оружия вставлялись в руку правильно без офсетов». Asked
whether the Creep's weapon bones should follow the same standard (it changes a shipped rig):
«Yes, one standard». Spec: `docs/superpowers/specs/2026-09-30-weapon-socket-and-inventory-skin-design.md`,
plan beside it.

**Measured first** (standalone), the fist at the bind pose in each weapon bone's own axes. A hammer
grip holds the blade along the knuckle line pinky_01 → index_01, the width along the metacarpals,
the thickness along the palm normal.
- **Manny's and the Orc D's `weapon_r` is UE's**: the grip line along its +Z (0.978), the palm
  normal along −Y. `weapon_l` is its behaviour mirror (grip line −Z).
- Every catalog model lies along +Y, so **every weapon stood 84° off the fist at zero grip**. The
  animator's prefs held exactly the correction: (90, 0, 0) on Long Sword 02, Dagger 01 and Spear 03.
- **The Creep's weapon bones (ours, 2026-09-24) held the grip line along +Y**, so the same models
  fitted there at its bind. But a UE clip retargeted onto the Creep hands its `weapon_r` UE's local
  rotation (helper bones travel relative to the hand on a rotation-only rig), and a sword that
  fitted at the bind stood **101.9°** off the fist mid-take.

**The standard:**
- **`catalog.SOCKET_TURN = (90, 0, 0)`** takes a model's axes (blade +Y) into a UE weapon bone's
  (grip line +Z, palm −Y). `bonedrive.socket_frame(frame)` = R(frame) · R(SOCKET_TURN) is what a new
  weapon node stores (`attach.import_weapon`) and what the left hand's mirror uses (`grips.for_hand`).
- A row's `frame` stays the model's own extra turn (the Creep Sword's 45 about its blade). Everything
  downstream already read the node's frame: the grip fields read 0 0 0 at zero grip, and relink,
  mirror, floor and Connections are unchanged.
- **The Creep's `weapon_r` / `weapon_l` were turned a quarter about their own X** (Rx(−90) / Rx(+90))
  in both Creep assets by `make_creep_weapon_sockets.py`: grip line 0.995 / −0.995 on ±Z, every
  other joint and every vertex 0.0, skins at their bind, the bind pose saved whole. It is
  idempotent BY MEASUREMENT (a second run turns nothing and saves nothing), and it is the Creep
  pipeline's last step, after `make_creep_armature_layout.py`. The Creep Sword stands on the Creep
  exactly where it did (8.5e-14): Rx(90) · Rx(−90) = I.
- **Remembered grips are carried once** (`grips.migrate`, on the first read, gated by
  `mayaSceneSetup_gripSocket`): G · R(frame) · R(socket_frame)⁻¹, both hands and the legacy name.
  The animator's (90, 0, 0) became 0 0 0 with the weapon where it stood (4.9e-7 live).
- **A weapon node added before this keeps its old frame** and still reads and dials in the standard
  (`grips.standard` / `on_node`, the Weapons fields' two edges), so an old scene's correctly held
  sword reads 0 0 0 and a re-Add does not add another 90.
- A Creep added before this has the old weapon bones: re-add it. A clip exported from Maya off the old
  Creep skeleton carries `weapon_r` in the old orientation; Cascadeur's own Creep clips carry
  `weapon_test` and are untouched. The animator's `Animations/Rigs/Characters/Creep_Skeleton.fbx`
  was not re-exported.

**Two defects found on the way, both fixed:**
- **The inventory remembered grips it had only computed** (trap 107).
- **Weapon and helper-bone bakes left euler flips between keys** (trap 108): `bonedrive._bake` and
  `transfer_bone` now run `bonedrive.euler_filter`.

**The inventory in the hub's look:**
- `maya_invlook.PALETTE` IS `maya_hubstyle.TOKENS` (`RADIUS` card 8 / well 6 / item 4); no serif,
  no bevel, no diamonds.
- The window: the `panel` with a `line` outline, rounded (a translucent top-level), the hub's
  `backpack` icon and a bold «Inventory».
- The hand slots and the grid are `card`s on `field` wells.
- A drop target is lit as the hub's active card (`card_active`, a 2 px `accent` outline); a dragged
  slot is lit `danger`.
- The grid preview is `ok_tint` / `danger_tint` with an outline, the status the hub's message line,
  the ghost's caption a card pill.
- Tests pin that no colour of its own and no Diablo styling is left; the layout is unchanged but
  for the grid's card gap.

Proof:
- `verify_weapon_socket.py` **10/10 standalone**, run with a scratch `MAYA_APP_DIR`:
  - every catalog weapon at zero grip in the right fist of Manny / Orc D / Creep: blade 11.9 / 11.3
    / 5.8° off the grip line, thickness 8.8 / 8.3 / 17.0° off the palm (each socket's own roll —
    the Creep's is its creature's `weapon_test`), fields 0;
  - the left mirror through each rig's OWN sockets, 11.9 / 11.3 / 5.9°;
  - the Creep Sword where the old asset stood it;
  - the migration;
  - a UE take on the Creep holding the sword in the hand as Manny does, at every key (0.0007°) and
    every half frame (0.001°).
- Re-run on the new assets: `verify_creep_rig_asset.py` 16/16, `verify_inventory.py` 14/14,
  `verify_weapon_space.py` 11/11, `verify_creep_skeleton_asset.py` 9/9, `verify_creep_bind_pose.py`
  all gates.
- Live in a disposable Maya (port 7003, `MAYA_NO_HOME=1`):
  - the three seeded (90, 0, 0) grips migrated to 0;
  - `verify_inventory_live.py` setup 13/13 + drops 8/8;
  - front, side and top playblasts: a Long Sword and a Spear 03 pointing forward out of the fists
    at the default grips.
- 2696 unit tests.

107. **The inventory froze a COMPUTED grip as a dialled one.** `equip.to_hand` ran
     `grips.remember` with whatever `for_hand` answered, the left hand's mirror included. From then
     on that weapon's left grip was "dialled": it stopped following the right grip and each rig's
     own sockets. Measured: the Orc and the Creep got Manny's mirror numbers. The inventory dials
     nothing and remembers nothing; the Weapons fields are what remember.
108. **A bake keeps whichever euler each frame evaluated to.** On a UE take retargeted onto the Creep
     the sword stood in the hand exactly at every key (0.0007°), while its rotate curves stepped
     **347 / 538 / 188°** from key to key: the same rotations written the other way round, so it
     spun BETWEEN frames. Manny's, baked from a direct world-space constraint, stepped 17°. The
     Creep's went through the relative helper-bone transfer, where a decomposeMatrix rotation wraps.
     `cmds.filterCurve(..., filter="euler")` after the bake: 17.1°, equal to Manny's. A gate
     sampling only whole frames cannot see this; sample half frames too.
109. **A relaunched disposable Maya did not run the userSetup on `PYTHONPATH`** (the same boot
     folder that worked the day before): CPU flat, no port, only the Home screen up. With the
     userSetup copied into `<MAYA_APP_DIR>/2027/scripts/` it came up in 35 s. And a Home screen that
     keeps `MayaWindow` hidden (trap 105) did NOT give way this time: hiding it, `setVisible(True)`,
     `show()`, `appHome -visible 0` / `-toggleVisibility` all left the viewport invisible.
     **`MAYA_NO_HOME=1` in the environment at launch** is the reliable road: the viewport was up at
     1662 × 1044 on the first probe.

## Graph Overlay: Maya's own Graph Editor over the viewport, background out (2026-09-30)

The animator: «А возможно ли для Maya graph editor сделать так что бы его задний фон стал прозрачным но
при этом все остальные эллементы кривые и тд остались такимиже?» — offered a colour key with its costs
(floating only, a click-through background, a fringe): «мне нужен граф эдитор с прозрачным фоном». Two
answers: shape **Б**, a mode on a key with the curve area on the whole viewport («А весь функционал графа
останется?» — yes, every click and key is the real Graph Editor's), and **alt+mouse is the camera**
(«1, камеры»). The Curve Overlay's idea (2026-09-05, archived) done with Maya's own drawing and input.
Spec: `docs/superpowers/specs/2026-09-30-graph-overlay-design.md` — **read its addendum**, the live run
changed five things. Plan beside it.

**Why not Maya itself** (measured in a disposable Maya first): the curve area is `TanimCurveCanvas`, a
`QOpenGLWindow` (→ `QmayaCanvasWidgetGL`) in a QWindowContainer, a native child HWND with 8 alpha bits;
its background colour `modernGraphEditorBackground` takes an alpha (`displayRGBColor ... alpha=True`) and
**the canvas ignores it** — `grabFramebuffer()` reads alpha 255 on every pixel; DWM glass on the window
changed nothing. So the route is two windows:

- **The ghost** (`ghost.py`): a `scriptedPanel(type="graphEditor")` of OURS (never graphEditor1) in a
  frameless Qt host via the hub skin's `setParent(fullName(layout))`; menu bar `menuBarVisible=False`,
  the toolbar frameLayout (parent of the panel's `QadskFrameLayoutFrame`) unmanaged, the channel list's
  QSplitter side 0 with handle 0; placed by `geometry.host_rect` so its canvas equals the viewport's GL
  rect pixel for pixel; made invisible by **Qt's own `setWindowOpacity(1/255)`**. Measured: at alpha 1 it
  keeps rendering (`frameSwapped`, the marker moves) and keeps taking clicks (`WindowFromPoint` answers
  its canvas) — a layered window lets the mouse through only where alpha is 0.
- **The glass** (`glass.py`): a frameless translucent click-through Qt top-level
  (`WindowTransparentForInput` + WS_EX_TRANSPARENT) on the same rect, showing each `grabFramebuffer()`
  frame (PySide hands the canvas back as QPaintDeviceWindow: `shiboken6.invalidate`, then wrap as
  `QtOpenGL.QOpenGLWindow`) with the background keyed out.
- **Keying** (`keying.py`, numpy only): straight alpha, `table[min over keys of max_c |P - K|]`, 0→255
  over 28 levels, colours untouched; the keys are the colours covering 5 % of a frame (64 in the playback
  range, 55 outside it on the animator's Graph Editor), learnt over frames (`mode.learn_tones`, ≤ 3).
  uint8 on four threads: 5.7 ms at 1850×1067 (float32 was 54 ms at 968×723).
- **The mode** (`mode.py`): every `frameSwapped` coalesced (≥ 15 ms apart) → grab (WGL context kept,
  `winstyle.gl_kept`) → key → glass; a 10 Hz follow (the viewport moved, Maya behind another app, our
  panel gone, the ghost's opacity, the glass's click-through); a 30 ms alt poll (`GetAsyncKeyState`) —
  held, the ghost is click-through and the viewport's camera takes the drag. Scene opened → the mode ends.

Hub section **Graph Overlay** in Animation (icon `chart-line`); hotkey row `graph.overlay` on **alt+c** —
the Curve Overlay's key, out of `RELEASED_KEYS`, `DEFAULT_KEYS_VERSION` 6, so it binds in the SkeldarAnim
set on the next switch of the hotkey map (in `Maya_Default` alt+c is Maya's own); a payload row. Proof:
`docs/superpowers/plans/verify_graphoverlay.py`, phased, **in the animator's own Maya on port 7001** (an
untitled scene; their choice after the disposable Maya was closed twice): 20 gates — 19 on the full run,
gate 12 failing once on another Maya's window over the point (below), 15/15 on the rerun of its phases:
canvas and glass on the viewport (1526×1044) to the pixel, alpha 1, a time change reaching the glass, a
posted click grabbing the key under its pixel, alt handing the mouse over and back, **8.5–9.3 ms a frame**
(grab 3.7), 93 % of a framed view clear, the section ON/OFF, nothing left after, the colour preference
untouched. 2806 unit tests. The scene was put back to an empty untitled one.

110. **Qt drops a window style it did not set.** WS_EX_LAYERED written with ctypes on our Qt host came
     back gone (`0xa0`): the "invisible" Graph Editor stood grey on the viewport and the timer's
     re-assertions redrew it ~40 times a second. `setWindowOpacity` makes Qt keep the bit (`0x80080`,
     alpha 1) — and that very call dropped the WS_EX_TRANSPARENT we had set. Ask Qt (opacity,
     `WindowTransparentForInput`), and compare with the window's REAL style, never a cached flag.
111. **Module state is per module OBJECT, and purges multiply the objects.** Four copies of `mode` lived
     in one session (an install, a verify's purge, the hub's rebuild importing afresh); the running
     overlay sat in one nobody could reach and `import` handed out one that said "off". A mode that owns
     windows keeps its state on `sys` (trap 49/102 from the module side).
112. **Maya's Graph Editor reads the real cursor while a button is down.** A posted
     WM_LBUTTONDOWN/UP at a key's pixel grabbed THAT key and dragged it towards the animator's actual
     mouse (60 → 80.46). A scripted click proves which key was taken, not a clean click; put the keys
     back. Maya 2027's PySide6 has no QtTest.
113. **An install from a working tree another session is editing can die halfway.** A peer's uncommitted
     `install.py` listed a file not yet written; `copy_payload` raised FileNotFoundError after the rmtree
     and the animator's installed folder was left without assets, icons, overrig or install.py. With
     other sessions in the repo install from a snapshot of a commit (`git archive <commit> SkeldarAnim`),
     compare it back (`diff -rq`), and write `version.json` into the snapshot first.
114. **A `WindowFromPoint` gate sees every program's windows.** Gate 12 read the canvas of the
     animator's other Maya's floating Graph Editor lying over the point; the rerun, with it moved, passed.


**…the whole Graph Editor, and Maya's own** (the same evening, after using it: «я не могу выделить
отдельно каналы для редактирования кривых и нет остальных инструментов»). The mode now lays the WHOLE
Graph Editor on the viewport — menus, toolbar, channel list — with only the curve area see-through:
- the glass shows the chrome opaque, cut band by band around the curve area (`geometry.chrome_bands`)
  out of one **DWM copy of the host window** (`winstyle.capture`: `PrintWindow`,
  `PW_RENDERFULLCONTENT`, read as RGB32), re-taken when a chrome widget repaints (an event filter on the
  host's widgets, silent while capturing, ≥ 30 ms apart, first capture 0.5 s after switching on);
- the panel is **Maya's own `graphEditor1`, borrowed** (`ghost.BORROWED`) and given back where it lived
  — its dock, its window, or unparented — with its channel list's sizes: **55 of Maya's runtime
  commands name `graphEditor1GraphEd` outright** (the view modes, Copy/Paste/Delete keys, infinity,
  frame all/selected, bake, simplify, smoothness), and the toolbar, menus and hotkeys reach them — in a
  panel of our own the Stacked View button switched the animator's Graph Editor. While the mode is on
  their own Graph Editor window is empty; opening it takes the panel back and ends the mode (Maya
  re-parents it), a new scene ends it too;
- the channel list is opened at max(320, its own minimum 310) for the first two seconds (the borrowed
  panel shut it once more itself while laying out), then left to the animator.
Proof: `verify_graphoverlay.py` **26/26 in a disposable Maya** (`MAYA_NO_HOME=1`, scratch
`MAYA_APP_DIR`, port 7003 — the animator's choice after the crash below): the whole Graph Editor on the
viewport, the chrome opaque, a click on the channel list's Rotate Z landing in the list, the toolbar's
view mode switching the Graph Editor ON the viewport, alt, **8.4 ms a frame at 1334×969**, six
switch-on/off cycles, the Graph Editor window taking the panel back, a new scene — each ending cleanly.
The installed copy was brought to the fixed build by copying the three package files (no port was open;
`diff -rq` against a `git archive` equal).

134. **`QWidget.grab()` of Maya's widgets from Python crashed Maya.** Right after switching on over a
     just re-parented `graphEditor1` — an access violation in `SharedUI.dll` with `ufe_7` and
     `shiboken6` on the stack (the minidump parsed by hand: no debugger here). A grab re-renders every
     widget, Maya's channel list mid-rebuild included. Take pixels from DWM (`PrintWindow`,
     `PW_RENDERFULLCONTENT`): no Maya paint code runs. A test now fails on any `.grab(` call in the
     package.
135. **A wrapper of a Maya-owned object Maya has deleted is not "already deleted".** shiboken was never
     told, so a method call reads freed memory and crashes instead of raising. Look live objects up
     every time (`QGuiApplication.allWindows()`), compare by `getCppPointer` address, and disconnect a
     signal only from the live object that is still the one connected.
136. **Maya's Graph Editor commands are hard-wired to `graphEditor1`** — 55 runtime commands. A second
     graph editor panel's toolbar, menus and hotkeys act on the first; borrow `graphEditor1` rather than
     make another.
137. **`QSplitter` collapses a side set below its `minimumSizeHint`** — the Graph Editor's channel list
     (310 px) set to 260 came back 0. Set at least the minimum, after the layout.
138. **A click POSTED into Qt widgets proves nothing about them.** Qt takes the real cursor into
     account: even an application-wide filter saw no press for a `WM_LBUTTONDOWN` posted to the host,
     and the channel list selected nothing; Maya's curve canvas takes the press at the posted pixel but
     drags with the real cursor (60 → 80.46). Prove routing with `WindowFromPoint` + `childAt`, commands
     with `QAbstractButton.click()`, and leave the rest to a real click.
139. **A session state kept on `sys` outlives its class.** Made by the first build, its `reset()` knew
     neither `keys` nor the chrome fields: the tones and a dead event filter survived a switch-off. Reset
     by THIS module's field list (`mode.reset_state`), at every switch-on too.

## The Characters card: a portrait grid, a character dragged into the scene (2026-09-30)

The animator: «Все что касается покраски вынесем из меню, будем красить в меню с красками.
Давай полностью переделаем наше меню на сетку с портретами (как меню выбора героев в Mortal
Kombat или Dota 2) ... кликнув по нему мышкой и потом нажав кнопочку Add Character ... зажать
на портрете и перетащить его в сцену Maya, и персонаж создастся в том месте, куда я его
перетащил». Asked, and answered:
- head and shoulders, square (MK);
- ONE portrait per model with a `[Rig | Skeleton]` switch;
- a dropped character faces +Z as its file does, translation only;
- «делай все до самого конца».

Spec `docs/superpowers/specs/2026-09-30-character-portrait-grid-design.md` (read its addendum),
plan beside it. Proof `verify_character_grid.py`, **11/11 live in a disposable Maya** (port 7004,
scratch `MAYA_APP_DIR`, `MAYA_NO_HOME=1`). 2808 unit tests. The installed copy refreshed in
the animator's Maya from a `git archive HEAD` export (not the working tree, which held another
session's edits), `diff -rq` clean.

**The card** (`window.build_characters_panel`):
- the subtitle, the `[Rig | Skeleton]` segments `mayaSceneSetupCharacterKind_<kind>`, the grid,
  Add Character (primary), Camera Setup, the status line;
- **no colour**: the dots, the swatch and Recolour are gone (`_CHARACTER_COLOUR`,
  `_CHARACTER_DOT`, `recolour_character` deleted, gone-tests pin it). Add passes no colour, so
  the character arrives in the next free palette colour, and the **Colour** section repaints
  the selection. Add leaves the rig's `Main` selected, so one click there paints it (gate 8).
  The Weapons card keeps its colour row;
- the pick is remembered as `mayaSceneSetup_characterModel` + `mayaSceneSetup_characterKind`
  (`remembered_choice`; the old dropdown's `mayaSceneSetup_character` label is the fallback,
  so the animator's last pick survived: the live card opened on Creep);
- a model without the chosen kind (Orc D has no skeleton, the UE4 Mannequin no rig) is dimmed
  with a «no rig» pill, cannot be picked or dragged, and Add refuses it by name;
- where Qt cannot stand, the card builds the old dropdown of six rows (`_character_dropdown`)
  and `chosen_character()` reads it.

**The catalog**: `Character.model` and `catalog.MODELS` (Manny, Creep, Orc_D, UE4_Mannequin
in grid order), `KINDS`, `character_for(model, kind)`, `kinds_of`, `portrait_path`. **A new
character row needs a model and, for a new model, a portrait** (a test pins one per model):
re-run `docs/superpowers/plans/make_character_portraits.py` in a disposable GUI Maya. It
renders:
- each model's rig row (else its skeleton), a clay phong on all but the textured Orc D;
- three directional lights, AO, 16x AA;
- an 85 mm camera framed from the upper arms and the meshes' top, turned 22 degrees;
- a 512 px playblast with alpha, scaled to a 256 px RGBA PNG in
  `assets/character_portraits/`.

Viewport 2.0 loads textures in the background: the first Orc D blast had black shoulder pads,
hence a few forced draws for a textured row.

**The grid** (`maya_chargrid`, Qt; its look `maya_charlook`, stdlib; both in the payload):
- columns of at least 72 and at most 120 logical px (one row of four in the 360 px dock);
- how it sits in the card: the builder makes an empty `cmds.columnLayout`
  `mayaSceneSetupPortraits`, and `attach()` lays the grid OVER it (the `_spread` pattern) with
  a `Keeper` filter that keeps the placeholder `setFixedHeight(grid.height_for(width))` on every
  resize. Measured: 685 x 192 physical at 150 %, honoured by Maya's layouts in the skin and the
  classic hub alike (gates 1, 11);
- a click selects (`window.select_model`);
- a press past `startDragDistance` starts the drag:
  - the shared ghost rides the cursor (`maya_hubqt.ghost_class()`, moved there from the
    inventory, which uses it too), the caption «Manny [rig] · floor (120, -36)»;
  - Esc or the right button cancels; a release on the hub does nothing (`Scene.over_hub`:
    widget ancestry, else the `skeldarAnimHub` control's rect);
- the release: `droptarget.floor_at` (the camera ray meets Y = 0), then
  `window.place_character` → `character.add_character(entry, at=point)`.

**Placement** (`character.place`): a rig's `Main`, else the skeleton's `root`, moved by
`(x, 0, z)` relative in world space. **Never the Creep skeleton's `Armature`**: a moved Null
is no longer Cascadeur's layout to `fbxlayout.in_layout`. Measured:
- Main on the floor point to 1e-6, unturned;
- the Creep root moved by exactly (x, 0, z), `Armature` at the origin, `root_in_layout` True;
- a synthetic press-drag-release on the Creep portrait: a rig at the release point, 1e-6.

A retarget then puts `Main` where the clip's root is, world space as always: the drop chooses
where a character appears.

115. **`file -import` FLUSHES Maya's undo queue.** Measured 2026-09-30 in a deferred call: a
     cube made before the import could not be undone after it («There are no more commands to
     undo»). Nothing that imports a file can be undone, Maya's own File > Import included. A
     press that wraps an import in an undo chunk therefore half-undoes: the chunk left held only
     what followed, and a Ctrl+Z moved the dropped Orc D back to the origin. Everything after the
     import runs unrecorded now (`character._unrecorded`: `undoInfo -stateWithoutFlush`, the
     previous state put back). Gate 10: a Ctrl+Z after a drop changes nothing.
116. **A scripted `iconTextRadioButton -e -select` is not a click.** It ran the segment's
     `onCommand` in one hub build (the grid and the optionVar followed) and not in the next
     (the segment moved, the grid kept its kind); a Qt `click()` on the button ran it every
     time. A verify switches a segment by clicking its Qt button (`pick_kind`). Also from this
     run: a skeleton added beside rigs alone kept its plain `root` and the rename note still
     named `Manny_Rig:FKXAnkle_L`. With no plain top joint among the others nothing collided,
     and `rename_note` says nothing now.

## The Weapons card IS the inventory: hands with a Channel Box, the grid, Add / Remove (2026-09-30)

The animator: «Давай сделаем с меню Weapon тоже самое что сделали с персонажами. Все что касается
покраски оружия вынесем в покраску. А сам выбор оружия превратим в наш инвентарь ... не в отдельном
окне а как часть нашего меню. Возможность задавать офсеты давай добавим возле окошек правой и левой
руки оружия. Возможность добавлять кастомное оружие по указанию пути давай пока уберем совсем.» Asked:
the hand slots stay side by side as in the window, «слева от окошка столбик с параметрами так как в
стандартном интерфейсе маи в channel box»; Add / Remove «как в Characters». Spec
`docs/superpowers/specs/2026-09-30-weapons-card-inventory-design.md`, plan beside it. Proof
`verify_weapons_card.py` **10/10 live in a disposable Maya** (port 7005, scratch `MAYA_APP_DIR`,
`MAYA_NO_HOME=1`): card 3, hands 6, classic 1. 2825 unit tests. The installed copy refreshed from a
`git archive` of `77b5689` (only the six changed files differed from what was installed); the open hub
of the 7001 Maya rebuilt from it. **"The weapon inventory" section above describes a floating window:
that window is gone, it is this card.**

**The card**: the subtitle `mayaSceneSetupWeaponsBound` (the character, written by `_bound_root` with
the Characters one), the inventory (`maya_inventory.InventoryPanel`, laid over the `cmds` placeholder
`mayaSceneSetupInventory` by the Characters grid's `attach` + `Keeper`, so it stands in the skinned hub
and the classic one), Add (primary) + Remove Weapon (danger) in one row, the line `mayaSceneSetupStatus`.
- **Gone**, a gone-test for each: the weapon dropdown; the FBX field and folder button (`chosen_entry`,
  `custom_changed`, `browse_fbx`, `mayaSceneSetup_custom_fbx`); the Hand row; the two grip
  `floatFieldGrp`s (`offsets_changed`); the colour row (dots, swatch, Recolour, `recolour_weapon`); the
  Inventory button; the floating window (`InventoryWindow`, `make_window`, its position optionVar).
  `catalog.entry_for_path` stays: `equip.entry_of` still names the file of a weapon an older scene added
  from one, so the inventory can move it between hands.
- **A weapon arrives in the next free colour**; the Colour section repaints a selected weapon (gate 9:
  the dagger blue, Manny's body as it was).
- **Picked**: the weapon clicked last in the grid (`mayaSceneSetup_weapon`, a key; the first catalog row
  when unset or stale) and the hand card clicked last (`mayaSceneSetup_hand`) - `window.chosen_weapon`,
  `side`, `picked`, `select_weapon`, `select_hand`. **Add** is `equip.to_hand(root, side(),
  chosen_weapon())` after the card's own refusals (the character, the bone, its parent, the legacy
  OverRig link, an aim); **Remove** is `equip.take_off`. The hotkey rows `scene.weapon` /
  `scene.remove_weapon` press the same functions and read the optionVars. Without Qt the placeholder
  gets a weapon dropdown and the Hand segments (`_weapon_fallback`), no grip fields.

**The panel** - `maya_invlook.panel(width)` is the whole layout, logical px from the card's width:
- two hand cards side by side (the right hand on the viewer's left), each its name, a **Channel Box
  column** (`CHANNELS` = tx ty tz rx ry rz, shown `Translate X` ... `Rotate Z` - the Channel Box's own
  order, translate first) and the well right of it; the grid under them, its cell `(width - 8) / 10`
  clamped to 24..40, centred;
- twelve `ChannelField` QLineEdits (object `skeldarChannel`, property `skChannel` = `"R_tx"` ...),
  styled by an ID-selector sheet set on the panel (it outranks the hub's own `QLineEdit` rule),
  right-aligned; a value reads `look.channel_text` (three decimals, zeros dropped, never `-0`). **Enter,
  or leaving the field, applies that hand's six** (`window.set_hand_grip`: remembered per weapon and
  hand; a clean held weapon re-gripped live, the bone still - gate 6: 30° typed, the bone moved 2e-14);
  **Esc** puts back what was shown; a hand that follows another weapon, no character or no bone:
  read-only. A refresh never rewrites the field being typed in;
- what a column shows (`window.hand_grips`): a clean held weapon - measured, in the socket standard;
  an animated or a floor one - remembered; an empty hand - the grip the PICKED weapon would take there,
  the left one the right's mirror (gate 5 read Manny's 6.621 / -0.978 / 1.706 / 1.379 / -1.576 /
  -179.508);
- **a click picks** (an item: `card_active` and a 2 px accent outline, the Characters grid's selected
  tile; a hand card: the same, its name bold); **a drag starts past `startDragDistance`** (the window
  started one on the press, which left no click); the drop table is the window's, unchanged;
- the nice names while a value still fits beside them (`look.split_row` with the font's own widths),
  the Channel Box's short names (`tx` ... `rz`) below that.

117. **The card is much narrower than the dock.** A floating hub whose scroll viewport is 510 physical
     px (the animator's 360 px dock, measured 2026-09-28) gives the Weapons card 275-317 logical px, and
     at the hub's 16 px UI font `Translate X` (75 px) beside `-179.51` (54 px + padding) did not fit a
     129 px column - every run fell to the short names. The channel font is 9.5 logical (14 px: 66 and
     49 px), the well 1.2 cells (at least 32), the name-value gap 3: the nice names with 66-92 px value
     fields. Two harness facts: `workspaceControl -e -resizeWidth` on a floating hub did not stick (it
     read 922 px again one send later) - size the hub's window until its viewport is 510; and offscreen
     Qt has no font family (the fallback draws wide), so the unit test sets the font size itself.
118. **A refresh a scriptJob queues can run in the MIDDLE of an import.** The FBX import changes the
     selection and Maya turns Qt's event loop while it imports, so the panel's queued `SelectionChanged`
     refresh ran half way through Add: the left column read zeros under a mirrored grip, and nothing
     read the scene again after (gate 5 failed once). Add and Remove refresh the panel when they finish
     (`window._refresh_inventory`); anything else that changes the hands has to as well. The same run
     had the animator using the disposable Maya between sends (trap 85 again: its optionVars and undo
     queue showed an Orc D picked, Spear 01 dropped into a hand, the hub resized): the clean sequence
     card -> hands -> photo is what the 10/10 stands on.

## Connections: FK / IK for the arms (2026-09-30)

The animator: «Для вкладки connections нужно реализовать кнопочки которые будут переключать руки в FK IK.
Тут нужно учесть несколько нюансов. У адванцед скелетона уже есть встроенный переключатель FK IK.» Asked,
and answered: the span is **the highlighted range on the time slider, else the whole take**; FK on a hand
that rides the weapon **releases it, then switches**; **[FK | IK] per arm, acting at once**. Spec:
`docs/superpowers/specs/2026-09-30-connections-fkik-switch-design.md` — **read its addendum**, the build
changed the source. Module `maya_scenesetup/fkik.py` (cmds + OpenMaya, imports no panel and no OverRig).
Proof: `docs/superpowers/plans/verify_fkik_switch.py` **63/63 standalone** (21 per rig: Manny, Creep,
Orc D, a UE clip retargeted through the button); `verify_connections.py` **40/40 live** in a disposable
Maya; the card clicked through Qt there; 2959 unit tests.

**AdvancedSkeleton's own switch, read and replicated** (`asSwitchFKIK` / `asAlignFKIK` in
`AdvancedSkeleton.mel`): the state is `FKIKArm_<side>.FKIKBlend` (0 FK, 10 IK); FK2IK puts `IKArm` on
`AlignIKTo<Wrist>`, the pole from the FKX chain and every custom attribute to its default; IK2FK turns
each FK control onto its IKX joint. It is not called - a colleague's Maya has no AS and the plugin runs
none of it since 2026-09-07 (`vendor_bake`).

- **The arm keeps what it shows**: the FKX and IKX chains and the blend are sampled on every frame BEFORE
  anything moves and blended as the rig blends them (the twist network's `<Joint>BM_<side>` blendMatrix:
  positions lerped, rotations slerped the short way) - so a switch works from FK, IK or a keyed / half-way
  blend alike. NOT the deformation joints (trap 126).
- **to FK**: control world = `L⁻¹ · source` (L = the FKX joint in its control, constant -
  `CustomOrientReverse`, 172.9–180°), the elbow's and wrist's parents the rigid chain from the NEW upper
  joint; translate + rotate, the euler nearest the frame before (trap 108). **Exact: 0.0000 cm, 0.000°.**
- **to IK**: `IKArm = K · source_wrist` (K = `AlignIKTo<Wrist>` in the FKX wrist - it stands where `IKArm`
  does at build pose on all three rigs, ≤ 3e-6°); the pole on the source's plane (`maya_pmretarget`'s:
  base on the shoulder-wrist line at the elbow's share, nudged 0.2 % of the limb in the elbow's frame,
  aimed at the elbow, a limb out); `swivel`, `antiPop`, `Lenght1/2`, the pole's `followArm` and `lock`
  reset over a whole take (named), a refusal inside a range. **An IK elbow is a hinge, so the FK elbow's
  twist about its own bone is lost** - the clip's forearm pronation, up to 59° at one frame of
  `LongSword_Attack_Right_Heavy_3P`, the same on every rig; AS's own switch has the same limit. Places
  kept to 0.016–0.048 cm (a retargeted FK arm has the SOURCE's bone lengths, the IK the rig's -
  `TOLERANCE_CM` 0.05), the hand's turn to 0.0001°. On an FK take an IK arm can hold, exact both ways.
- **Measured and said**: after the write the deformation joints are read again - places, the hand's turn,
  the arm's roll - and the status line says which («hand and elbow kept to 0.026 cm; the FK forearm twist
  is lost, up to 59 deg at frame 32 (an IK elbow does not twist)»).
- **A range** (`timeControl -rangeArray`, end exclusive, through `overrig.slider_selection`): the blend
  keyed `a-1` (inserted, shape kept) / `a` / `b` target / `b+1` (inserted), stepped out of `a-1` and `b`;
  the target controls' keys outside the range kept. **The whole take**: the blend unkeyed, a constant
  channel collapsed to a value. autoKey off, one undo chunk. **Which frames are keyed: only the keys
  (2026-10-08, below)** - the first build keyed every frame of playback ∪ the controls' keys.
- **The card**: two rows at the top, `Arm_R [FK | IK]`, `Arm_L [FK | IK]` - `iconTextCheckBox`es
  (`QmayaIconTextCheckBox`, a QPushButton, so the skin's segment style lights it), not radios: a radio
  does not fire on the lit segment (a range inside a take in that mode) and a mixed take must light
  neither. Either press switches; `refresh` lights the mode read from the rig (FK / IK when every blend
  value sits at one end) under a quiet flag (trap 116); the header names a mixed arm. The status line is
  three lines now (54, trap 67).
- **Connections**: FK on a following hand = its release (baked where the proxy carried it) + the switch;
  IK on it «already IK (it follows …)», or «set it Free first» in a mixed take. **Hand -> Weapon switches
  the arm to IK over the whole take first** - the old «blend to 10» put the arm on whatever the IK held,
  and **the retarget's own IK stands 20.7 cm off its FK on Manny** (its pole rides the upper arm's frame;
  0.06 cm on the rotation-only Creep and Orc D); so `blend_refusal` is gone (a keyed blend is switched),
  and `verify_connections.py`'s gate 5 refuses a blend DRIVEN by a node instead.
- **The cost is the rig's evaluation**: 14 ms a frame on Manny live, two walks (sample, measure) - 1.35–2.2
  s for 61 frames; `refresh -suspend` saved nothing (trap 127).

Not built then: legs (built 2026-10-10 with the spine, below), scale, an IK stretched to a longer FK arm,
hotkey rows (`maya_hotkeys.py` held another session's uncommitted work, and nobody asked).

**…and on animation layers** (2026-10-16, the animator in a scene after Tools > 1P Setup:
«перестал работать connection переключение IK FK»). Every press refused «IKArm_R.translateX is
driven by IKArm_R_translateX__3P_Upper_Body - not a key the switch can rewrite»: 1P Setup puts
every animated control on `_3P_Upper_Body` / `_3P_Lower_Body`, and the switch took any input
that was not an animCurve for a foreign driver. Now (`fkik`, used by `fkikspine` too):
- a channel whose layers hold only time curves or values is not foreign (`_stack_foreign`);
- a LAYERED channel is keyed with what it must SHOW on the active layer
  (`maya_poselib.keys.active_layer`: the selected non-base layer, else BaseAnimation) through
  `setKeyframe -animLayer L -value v` - the Tools' and Pose Library's rule; the active layer's
  keys in the span are cut first, every other layer keeps its curves, nothing is collapsed to
  a plain value (it would not hold under a layer); `_seed` reads a layered channel after a real
  time change (trap 232); a layered solve attribute is keyed at its default; a layered blend is
  keyed to show the target (stepped);
- refused before anything moves (`layer_refusal`): a locked active layer, an additive one in
  quaternion accumulation asked for rotate keys;
- a Tools knot's pairBlend is named as such: «driven by a Tools knot (FKSpine3_M_parentConstraint1)
  - Bake or Remove it in Tools first» (1P Setup leaves one on FKSpine3_M, so the spine's FK is
  refused after it).
Proof: `verify_fkik_layers.py` **37/37 standalone** (a UE clip on Manny, 1P Setup, then Arm_R,
Leg_L to IK and back with nothing selected: the limb's places to 0.008 cm, the rest of the body
0.000000, both layers' curves untouched; Arm_L with `_3P_Upper_Body` selected: its keys there,
the base untouched; one undo; a locked layer refused; Spine to IK; the knot named). Checked
read-only in the animator's scene: all eight limbs of their two rigs pass `refusal`.

**The card follows the selection, and works in its popup copy** (2026-10-13, the animator: «у окошка
conection в режиме виджета не работает переключение рук на оружие и обратно ... статусы не обновляются
при выделении персонажа а только после применения скрипта»). Two causes:
- **In a popup copy every row read its first choice**: `menus()` compared the collection's answer (the
  copy's segment, made prefixed by `maya_hubcopy`) with the plain segment name, so nothing matched — a pick
  snapped back to Free / World and a row's Apply asked for nothing. It compares with
  `hubcopy.resolve(name)`'s leaf now (`_made_leaf`). The same in `maya_uebridge.window.import_target`
  (Import New in a copy of Animation Setup read Onto).
- **No card listened to the scene**: each card (the hub's and every copy) now has its own SelectionChanged
  / Undo / Redo jobs (`start`, `JOB` keyed by the copy's tag, parented to its status line), and a press
  re-reads every standing card (`_refresh_cards`). `_set_menus` is quiet (trap 116), so a refresh never
  writes «press Apply for» over the status.

A refresh costs ~21 ms with one rig (mayapy, half of it `maya_rigs.rigs()`). Unit tests `PopupCopy` (the
fake put through `maya_hubcopy`'s wrapper) and `test_a_popup_copy_reads_its_own_lit_segment`. Not seen live.

**…keys where the arm has keys, not on every frame** (2026-10-08, the animator: «если на ФК руке 3 ключа то
и на ИК тоже должно быть 3 ключа и наоборот. Нужно избавится от запекания лишних ключей»; asked, both the
recommendation: the arm's keys **and the keys of what it hangs on**, the tangents **as the source keys'**).
Spec `docs/superpowers/specs/2026-10-08-fkik-keys-only-design.md`.
- **Which frames** (`fkik.key_plan`): every time curve upstream of what the arm SHOWS (`sources`: the FKX
  chain, or the IKX chain + IK control + pole, or both + the blend in a mixed take), walked by
  `driving_curves` - a transform's matrix inputs (`MATRIX_INPUTS`, long and short names) and its parent; a
  compute node's (DG, constraint, shape, ikHandle) every input and parent; a joint's ikHandles (the solver
  sets IKX rotations with no DG connection, so they are found through `joint.message`); a transform's own
  attribute read by something (`IKArm.Lenght1`, a follow) that attribute's input; a driven key's driver.
  So the arm's own keys, the clavicle's, the spine's, the pelvis's, Main's, an animation layer's, a
  constraint weight's count; the other arm, the legs, the fingers, a visibility do not (nothing of them is
  upstream). The IK hand lives in Main's space and does not ride the body: a body key on a frame the arm
  has none is a frame the shown hand changes course, so it is keyed too.
- `key_frames` (pure): the whole take - every key time once (1e-4 frames apart is one key); a range - its
  keys plus its two ends (the blend steps there). Nothing keyed over the whole take - one sample at the
  current frame, plain values, «Arm_R to IK, no keys - nothing keyed moves the arm».
- `tangents_at` / `tangent_for` (pure): the in/out types of the keys ON the frame - the arm's own controls'
  first, else every walked curve's - where they agree, never `fixed`; a range's end inside a segment takes
  the out type of the key before; else Maya's default. Stepped blocking stays stepped and then matches on
  every frame.
- The measure walks the keys only; the line: «Arm_R to IK on 5 keys (0..24) - the arm kept to ...».
  **Between keys each chain interpolates its own way** (FK rotations against an IK hand's path): measured
  9.9 cm / 12° mid-way between auto keys 10 frames apart with a 30° elbow change - the cost of the ask.
- **Hand -> Weapon still switches on every frame** (`switch(..., every_frame=True)` in `_follow`): the
  proxy is baked on every frame anyway.
Proof: `docs/superpowers/plans/verify_fkik_keys.py` **14/14 standalone** (Manny stepped blocking: the arm
on 0/12/24, the clavicle on 6, Main on 18, the other arm / a leg / a finger on 3/9/15/21 - IK keyed on exactly
0, 6, 12, 18, 24, stepped, every frame kept, back to FK the same; Creep auto: a range 8..32 → 8, 10, 20, 25,
30, 32, auto/linear as the source, the mixed take → 10 keys, a layer key counted; nothing keyed → plain
values); `verify_fkik_switch.py` **63/63** again (a retargeted take is keyed on every frame: «on 61 keys»);
4651 unit tests.
- **…and under animation layers** (2026-10-16, the animator: «потеряли умный перенос анимации по ключам ...
  перепекают весь таймлайн»). The walk reached an `animLayer` through a blend node's weight and took the
  layer's every input - and a layer's inputs are its MEMBER channels (`dagSetMembers`), so every curve on the
  layer (the other limbs', dense ones too) came into the arm's plan (`driving_curves` now follows a layer
  only into its weight / mute and its parent layer, never a `message`).
- **…the limb's OWN keys only, not what it hangs on** (the same day, after that fix, on a take whose arm was
  keyed on 5 frames under a body - Main, RootX_M, the spine - baked on all 71: every frame again, by the
  2026-10-08 rule; the animator: «при любом переносе фк ик ик фк нужно переносить ключи а не запекать весь
  таймлайн целиком»). `key_plan` (arms, legs) and `fkikspine.key_plan` are `own_keys(own, plugs, span)`: the
  curves on the shown chain's own controls (`own_curves`: straight, or through animation layers' blends, a
  knot's pairBlend, a unitConversion) and a mixed take's blend; tangents from them. **The cost**: between
  keys, a body move the arm has no key for is not followed the same way by both chains (the IK hand stands
  in Main's space): measured on Creep, the clavicle keyed at 25 alone, the IK arm 12.3 cm / 17° off the FK
  there; on the keys exact. No key of the limb's own: one plain value at the current frame («no keys of its
  own - set at the current frame»). `verify_fkik_keys.py` **16/16** (A: 0/12/24 with the clavicle on 6 and
  Main on 18; D: under a layer); layers 37/37, switch 63/63, legs 12/12, spine 14/14, spine take 36/36;
  6759 unit tests. `driving_curves` is no longer used by the switch.
- **…and a MUTED layer's keys are not the limb's** (the same day, `Knife/AS_DG_ATK_JA_02.ma`: the arm's
  baked take, 71 keys, on a muted `_3P_Upper_Body` over 5 base keys - «не будем учитывать тот слой который
  отключен»). `own_curves` leaves out a blend's `inputB` when its layer (`blend.message -> animLayer`) is
  muted (`_layer_off`). On that scene: Arm_R to IK on 0, 14, 26, 40, 51, the arm kept to 0.0000 cm.
  `verify_fkik_keys.py` **18/18** (E: 31 keys with the layer on, the base's 3 muted); layers 37/37, switch
  63/63, legs 12/12, spine 14/14; 6766 unit tests.

126. **AdvancedSkeleton's deformation arm joints are NOT the FK/IK blend.** Their orient constraint's
     `offsetX` is driven by the twist network (`twistAdditionElbow_R_output1DUC1.o ->
     Elbow_R_orientConstraint1.ox`, memory "constraint offset can be driven"), so `Shoulder/Elbow_R`
     stand off both chains by the arm's own roll - 59–83° at one frame of a UE clip - while their places
     are exact. A switch that took them as "what the arm shows" and put the FKX chain on them came out
     with every position right and the forearm rolled 83°. The shown arm is the FKX and IKX blend the
     network itself reads (`ElbowBM_R`, a blendMatrix); the deformation joints are only for measuring.
127. **`currentTime -update false` + `getAttr` reads stale values**: 12x faster over 82 frames and 289 off
     the full update, measured in parallel AND with the evaluation manager off. A frame walk that reads
     a rig needs the full update (14 ms a frame on Manny live), and `refresh -suspend` does not make it
     cheaper - the cost is evaluation, not drawing.

**…and the legs and the spine** (2026-10-10, «Давай во вкладку conections добавим переключение FK IK для
ног и спины»; after the push: «При переключении с ФК на ИК спины у нас ломается анимация. При использовании
стандартного переключения в advanced skeleton все работает корректно»). Spec
`docs/superpowers/specs/2026-10-10-legs-spine-fkik-design.md` — read its addendum. Rows `Leg R / Leg L`
under the arms and `Spine` under the legs, the same `[FK | IK]` presses, keys only.
- **A leg** (`fkik`, `kind=LEG`) is the arm's switch with the toes as a fourth joint. The toes' IK
  control is fitted per frame (`_fit_toes`: its rest frame is the FK control's - the wrist's fixed
  relation read 177° off). The pole stands on the shown knee's bend side and is placed after the IK
  control is written (a leg's pole rides it, `followLeg`: placed before, 31 cm off). Not held: the knee's
  roll, ~84° in the IK knee's own frame when bent (said on the line).
- **The spine** (`fkikspine`): an ikSpline on five CVs, locators under `IKSpine1_M`, `IKcvSpine1..3_M`,
  `IKSpine3_M`; its joints sit ON the curve, not on the CVs, so to IK is a FIT. One Levenberg-Marquardt
  step per frame (`fkik.gauss_newton_step`, the damping raised and the step retried when it does not
  help). The unknowns are the CV controls' translates and the rotates of `IKSpine1_M`, `IKSpine3_M` and
  the mid `IKSpine2_M`. The targets are the shown Spine1..4 AND the root, places and turns, the root's
  residual ×100. To FK, `FKRoot_M` goes onto the IK root where the two part (the hip moved in IK). Then
  every FK spine control takes its place and turn (the IK spine stretches, `IKSpine3_M.stretchy` 10).
  Spine5's piece is measured against the shown Spine4: its parent `FKParentConstraintToSpine4_M` hangs
  under the DEFORM Spine4. The line: «the root and legs kept to 0.0000 cm».
- **AdvancedSkeleton's own switch** (`asAlignFKIK`, read and run in mayapy on the same take). It puts
  `IKSpine1_M` on the root exactly («since it affect legs») and the spine on a rebuilt curve («Target
  might not fully Align»): the root 0.0000, the spine 0.42-0.81 cm / 3.3-5.3° off. Its IK2FK keys `.t`
  and `.r` of every FK spine control, `FKRoot_M` included.

Proof: `verify_fkik_spine_take.py`, a UE clip retargeted through the button and pressed through
Connections, the game skeleton and the skin's vertices on every frame, Manny / Creep / Orc D.
- Keyed on every frame, **36/36**: the root, the pelvis and both legs **0.0000 cm**, both ways and after
  a 3 cm IK hip edit. The spine 0.013 / 0.037 (0.51° at one Creep frame, the spline's twist) / 0.011 cm.
- Keyed every 8 frames, **45/45**: between keys the spine stays within 0.12 cm.
- Also: `verify_fkik_spine.py` 14/14 on all three, `verify_fkik_legs.py` 12/12, the unit suite.

217. **The spline's hip control IS the IK root, and the spine's blend blends the root.** `Root_M` reads
     `FKXRoot_M` and `IKXRoot_M` through the SPINE's FKIKBlend, and `IKXRoot_M` follows `IKSpine1_M`
     1:1, place and turn. The first spine switch fitted the spline to Spine1..4 alone; it moved and turned
     `IKSpine1_M` and took the root, the pelvis and both legs with it. Measured on a retargeted take: the
     root 0.39 cm / 1.16°, the feet 2 cm, on every frame. Every gate was green, because every gate
     measured the spine; one even required keys on `IKSpine1_M`, which encoded the bug. A switch's verify
     measures everything the switched blend reaches, and the skin.
218. **With the root held, the spline's start twist is gone, and `IKSpine2_M` gives it back.**
     `IKSpine1_M`'s turn carries the root 1:1. The mid control twists the middle and leaves the root
     alone (rotateY +10 turns IKX1..3 by 5, 10, 5°). Fitting without it, the Orc D's strongly bent spine
     rolled 2.6° off; with it 0.41°. Probe which control moves what before choosing a fit's unknowns.
258. **A fit seeded only from the frame before walks into a wrong basin and stays there.** The animator's
     `AS_Dagger_Attack_Sprint_1p_SpineBug_` (2026-10-15, «при переключении IK FK из вкладки connection
     у нас ломается спина, AS-овское работает»): `FKSpine4_M` moved 12 cm and turned −140°, a chest no
     spline can follow. The LM fit, started from the previous frame, traded the top for the middle and
     drifted: chest, head, arms 29 cm / 167° off, still off on 25 frames of a held pose that, fitted
     alone, came within 2 cm. AdvancedSkeleton's own switch puts `IKSpine1_M` / `IKSpine3_M` on their
     `AlignIKTo` nodes - both ends exact, the middle approximate. Now every frame is fitted from both
     starts (the frame before, and AS's placement, `_as_seed`), the better kept, the top joint weighted
     as the root (`TOP_WEIGHT`): top 0.004 cm / 0.009°, root 0.002 cm, the middle 10 cm / 45° at worst
     on that take (AS's own: 12 cm / 165°). A seed that sets a channel the fit does not own (the mid
     control's translate) leaves it moved under every later frame: 1 cm lost on every normal take.

## Shared: scenes and FBX between colleagues, one press (2026-09-30)

The animator: «Мне очень часто приходится передавать какие-то сцены локально между сотрудниками. Можем ли
мы сделать какое-то Shared Temp хранилище ... не только сцен а еще и fbx файлов». Asked, in order:

- GitHub was asked about and rejected: an upload to GitHub always needs a key. A write key to the
  plugin's own public repository would also let anyone holding it replace the build every
  colleague's Check update installs. Their words: «Ключи никакие не нужны. Мне нужен максимально
  быстрый и удобный способ ... Один человек нажал кнопочку у второго через 2 секунды появился файлик
  в списке. Пока что мы не переживаем за приватность проекта».
- **Everyone works remotely**, so there is no office LAN for a Maya-to-Maya road.
- Of the two internet roads they chose **free services with no account for anybody** over our own
  Cloudflare Worker.

Spec: `docs/superpowers/specs/2026-09-30-shared-files-design.md` (read its addendum). Plan beside it.

**What it is.** A hub card **Shared** (group Scene, after Connections, icon `send`; hotkey row
`window.shared`). It holds an **Author** field (`skeldarShareAuthor`, remembered in the optionVar
`skeldarShareName`; the Windows user here is «MY PC», which names nobody), a **Name** field naming
the upload (below), **Send scene** (primary) and **Send file...** (.ma/.mb/.fbx), the list (several
rows can be picked), **Open / Import / Save to... / Delete**, and a status line that spells out the
picked row. (Until the evening the fields were Name and Comment: see "Delete, Author, and a name
for every upload" below.)

- **The file** goes to **temp.sh** (anonymous, 4 GB, 3 days), else to **litterbox.catbox.moe**
  (1 GB, 72 h).
- **A RECORD of it** (JSON: id, state, from, machine, name, sizes, url, comment, fps, range) goes
  to the ntfy.sh channel `maya_sharenet.TOPIC`.
- **Every Maya with the hub open** holds that channel on a `Subscriber` thread. A colleague's
  ready file downloads into `<userAppDir>/SkeldarShare/<date_time_sender_id6>/` at once, with an
  in-view message when it is news. Nothing ever opens by itself.

| module | does | imports |
|---|---|---|
| `maya_sharerecords.py` | the record: make, parse (strict), merge, rows, expiry, the history file, `playback_from_script` | stdlib only (a subprocess test) |
| `maya_sharenet.py` | temp.sh / litterbox upload (`upload_any`), publish, download, `Subscriber` | stdlib only |
| `maya_share.py` | the card, the presses, the state on `sys._skeldar_share` (trap 111), the Maya glue | `cmds` + the two, `maya_scenesetup`, `maya_uebridge` (lazy) |

- **Send scene** writes a COPY (`cmds.file(path, exportAll=True, type=<the scene's>,
  preserveReferences=False)`): the working file, its name and its modified flag are untouched.
  It then publishes "sending" (the colleagues' row appears), and on a thread zips, uploads and
  publishes "ready". A failure publishes "failed", and the colleagues drop the row.
- **Open**: `executeScriptNodes=False, prompt=False`, then the scene's ranges are restored (trap
  129), the vaccine swept, and the plugin's images relinked through `skeldarAssetImage`. An FBX
  opens as a new scene with `animimport.import_clip` into a namespace.
- **Import**: the same without the new scene; every script node that arrived is deleted.
- **Trust**: records are unauthenticated and the topic is in a public repository. `parse` accepts
  only our app/version, a 32-hex id, a plain .ma/.mb/.fbx name, and an https url on temp.sh or
  litterbox. Expressions in a hostile scene would still run when evaluated: that is stated, the
  cost of "no keys".
- **Not built**: deleting a file off its host (neither host has a delete; files die at 3 days —
  Delete takes it off every list and disk), sending to one person, the files a scene references,
  listening before the hub is opened.

**Proof** — `verify_shared_sender.py` (a disposable GUI Maya on port 7006) and
`verify_shared_receiver.py` (a mayapy colleague), on a test topic, the plugin from a `git archive`.
A 17.2 MB Orc D scene (5.0 MB zipped):

- in the colleague's list **1.2 s** after the press, ready at **6.3 s**, downloaded by two
  colleagues at **9.6-9.9 s**;
- opened with its script node never run, the 6 textures on the colleague's plugin, ntsc and both
  ranges (5-45 / 0-50), the unsaved edit along;
- an FBX sent back imported as 68 joints in its namespace;
- a send whose two hosts refuse published "failed", the colleague dropped the row, the sender's
  line named both refusals.

The animator pressed Send scene in the disposable Maya during the run and their file arrived too.
2960 unit tests. The installed copy was refreshed from a `git archive` of HEAD (the payload at `055e11a`;
`diff -rq` clean, the peer's files identical but for line endings). The live hub's card is online on the
studio channel.

128. **http.client sends a body that has `read()` in 8 KB writes, and a TLS upload crawls.**
     Measured 2026-09-30, 5 MB to temp.sh: 25.0 s as a file-like body (0.20 MB/s), 3.2 s given
     as an iterator of 1 MB pieces (1.56 MB/s). The same defect produced an afternoon's "litterbox
     fell to 0.15 MB/s", which was then wrongly blamed on litterbox; the morning's probes had
     sent `bytes`. Stream an upload as `MultipartBody.chunks()` with an explicit Content-Length,
     and probe a network road through the code that will use it.
129. **`executeScriptNodes=False` drops the scene's time ranges**: `sceneConfigurationScriptNode`
     is what sets `playbackOptions`, so a scene opened that way keeps the defaults (1.25-150 at
     ntsc, i.e. 1-120 film). The unit comes back; it is in the header. The first probe said the
     ranges survived only because it opened the copy in the same session that had set them. Parse
     the node's `playbackOptions` line (`records.playback_from_script`, numbers only) and apply
     it; never eval it.
130. **Maya clears the modified flag on the idle after a save, even over an edit made after the
     save in the same command** (measured: `file -save`, `setAttr`, `file -q -modified` answers
     True; the next send answers False). A verify that saves and edits in one send reads a clean
     scene afterwards: save and edit in separate sends. Our send and receive never touch the flag
     (measured step by step).
131. **Stopping a thread blocked on an HTTP stream (Windows)**: `response.close()` from another
     thread waits on the buffer's lock until the read times out, and `socket.shutdown` does not
     wake a read waiting under a timeout. `response.fp.raw.close()` (the SocketIO under the
     buffer) wakes it at once. The reader's own `response.close()` then raises; swallow it.
132. **Anonymous hosts gate their downloads differently.** filebin.net serves the file only to a
     client calling itself curl (an HTML warning page otherwise), so it is not used: we do not
     pretend to be curl. temp.sh answers a GET with its download page and the file to a POST —
     what that page's own button sends. `cmds.file(..., exportAll=True)` of a 17 MB scene takes
     0.4 s; `zipfile` level 6 takes a 51 MB rig scene to 12.4 MB in 2.1 s.

**Delete, Author, and a name for every upload** (the same evening: «кнопку которая будет удалять
выбранные файлы. И Name заменить на author а comment на имя файла или сцены, что бы можно было
удобно называть заливки»). Asked what Delete removes (the hosts have no delete), the animator chose
**«Всё у всех»**: any picked file, theirs or a colleague's, leaves every colleague's list. Spec
`docs/superpowers/specs/2026-09-30-shared-delete-and-naming-design.md`.

- **Name** (`skeldarShareFileName`) names the upload: `records.upload_name(typed, fallback)` (pure)
  keeps the SOURCE's extension (a scene its .ma/.mb, a file its own; a typed .ma/.mb/.fbx is dropped,
  so «attack.fbx» over a scene is `attack.ma`), collapses whitespace, turns Windows' forbidden
  characters into `_`, strips leading dots and trailing dots/spaces, caps at 80, prefixes a device
  name (CON, NUL, COM1 ...); empty means the scene's or the file's own name. Cleared after a send.
  `send_scene(name=)` / `send_file(path, name=)` replace the `comment=` parameters. **No comment is
  sent any more**; an older build's comment still shows in its row.
- **Delete**: a danger button (the trash alone in the skin, «Delete» in the classic hub) and the
  Delete key on the list (`deleteKeyCommand`); the list is `allowMultiSelection`, and Open / Import
  / Save to... take ONE («Pick one file to open - 2 are picked.»). One confirm names the files
  (`records.delete_question`; batch skips it). Then one **`deleted` record** per file (the record in
  state `deleted` + `by`, `by_machine`), published side by side on a thread (`DELETE_WORKERS` 4), and
  what the channel took is applied here (`_deleted`); what it refused stays, named.
- **Applying a `deleted`** (`_apply_delete`, here and from the channel): **terminal** (`_RANK` 2), so
  a `sending`/`ready` arriving after it in any order changes nothing, and the entry stays in the
  history as a tombstone until it expires; the row goes; a transfer stops at its next tick
  (`_progress` answers False — net's Cancelled — and a stopped send publishes no `failed`, a `ready`
  that raced past it is never applied); the local copy and its folder go (`_forget_local`: only
  inside SkeldarShare/, **never the scene open in this Maya** — that one stays and the status says
  so); a colleague's delete says «Oleg deleted Longsword.fbx», our own echo says nothing.
- **An older build refuses the unknown state** and keeps the row until the file expires.

Proof: `verify_shared_delete.py` — **9/9, two mayapy colleagues** (own `MAYA_APP_DIR` each) on a test
topic over the real ntfy.sh and temp.sh: A sends one scene three times under typed names, B's rows
carry them (row at **0.86 s**, ready at 2.5 s), B opens «one»; A deletes one and three together: B's
rows go in **0.85 s**, three's copy and folder go, one's copy STAYS (it is B's open scene) and the
status says so; B deletes two (A's file): A's row and sent copy go in **0.93 s**. And the card in a
disposable GUI Maya (port 7008, scratch prefs, started minimized, killed after) at the animator's
dock (viewport 510 physical): two rows picked through `selectIndexedItem`, kept across a refresh,
the trash clicked — «Deleted 2 files for everybody», the subtitle «0 files»; the Delete key sent to
the list's widget deletes too; every button at or above its size hint in the skin (Open 99 ≥ 93,
trash 58 ≥ 55) and the classic hub (Delete 96 ≥ 61). 3054 unit tests.

140. **ntfy.sh can deliver a message to the stream BEFORE the publish call returns.** A delete's own
     echo reached the subscriber first (the row gone, `_receive_delete` silent for our machine) and
     the press's «Deleted 1 file» came 0.8 s later, when `publish` answered; a gate that checked the
     status on "the row is gone" failed on correct code. Anything applied from both the press and the
     channel must be idempotent and may run in either order — `_deleted` asks the entry, not its
     own `_apply_delete`'s answer, whether the copy was kept.

## Open scene on the right button: a portrait's or a weapon's own file (2026-09-30)

The animator, having asked whether Maya allows a context menu on the icons at all: «Давай сделаем так
что бы когда я нажимал правой клавишей по иконке рига или оружия то у меня появлялось опция Open scene
и при нажатии на нее у нас бы открывался соответствующий фаил». Spec
`docs/superpowers/specs/2026-09-30-open-scene-menu-design.md`.

- **Characters grid**: the right button on a portrait shows one row, **Open scene** — the model's file in
  the kind the `[Rig | Skeleton]` switch shows (`catalog.character_file`). A dimmed portrait shows it
  disabled, «Open scene (no skeleton)». A right press never picks; during a drag it still cancels.
- **Weapons inventory**: on a weapon in the grid, or on a hand card holding one (held or on the floor),
  **Open scene** — the row's FBX; on the grid **Sort the inventory** stays under a separator; an empty
  hand offers nothing (`InventoryPanel.context_actions`, `PortraitGrid.context_actions`, both pure over
  the hit and tested without a menu).
- **One menu helper**, `maya_hubqt.build_menu` / `run_menu`: rows (label, callable), a None callable
  disabled, None a separator; the QMenu is parented to the grid, so the hub's stylesheet reaches it.
- **`maya_scenesetup/opener.py`** does the opening: Maya's own «save changes?» (`saveChanges("")`, Cancel
  → «Open scene cancelled - nothing changed»); a `.ma` with `executeScriptNodes=False` (Shared's rule),
  its ranges parsed out of the configuration node (trap 129), a vaccine node deleted, the shipped images
  pointed at the plugin's copy (`colour.relink_images` — the assets name them relatively); an `.fbx`
  through **`fbximport.open_file`**, the trap-33 import-mode guard now shared by import and open; then
  `file -modified false` either way. The line: «Opened Manny [rig] - assets/Manny_Rig.ma. Save As to
  keep changes: a save writes into the plugin, and an update replaces its files» — the ask was the file
  itself, so Ctrl+S does write into the installed plugin, and the line says so. The file opens as it is
  on disk: Spear 03's FBX untextured (Add applies its texture), the UE4 Mannequin in its importer wrapper.
- **An FBX open reads as a modified scene** (measured 2026-09-30 on every catalog weapon and the UE4
  Mannequin): it is an import into a new scene. Without the reset the next Open scene asked to save an
  untouched file.

Proof: `verify_open_scene_files.py` **61/61 in mayapy standalone** — every character row and every weapon
opened from the repo's assets: the scene is that file, unmodified, its geometry in, no script node of its
own, every shipped image on the plugin's copy (Manny 4/4, Creep 6/6, Orc D 6/6), the FBXs whole under a
forced `exmerge` with the mode put back. 2992 unit tests. The installed copy refreshed in the animator's
Maya from a `git archive` of `688ba9d`, their modified scene untouched; the open hub rebuilt on the new
modules (read back: the grid offers «Open scene» over Manny, the inventory «Open scene / Sort the
inventory» over Spear 03). **`verify_open_scene_menu.py` (real right-button events, the real QMenu read
and activated while its `exec()` runs, Maya's save dialog answered by clicking) is written and NOT run**:
every new GUI Maya launched that afternoon hung before Python (below), and the animator's own Maya held
a modified scene an Open scene would have replaced.

133. **A new GUI Maya hung at startup, three times in a row, whatever the launch** (2026-09-30 afternoon:
     scratch `MAYA_APP_DIR` with a short path, with a long path, and the shared prefs; `MAYA_NO_HOME=1`,
     `-hideConsole`, a PYTHONPATH userSetup — the recipe that worked that morning). Licensing authorized
     it (MayaCLM log «Authorized»), then it sat at **277 MB with one core busy** for 5 minutes, no visible
     window, nothing written to its prefs but `Maya.env`, no userSetup run — two other Mayas running
     beside it. Cause not found. Before blaming a verify, look at the new process's working set: a Maya
     that loads climbs past ~900 MB within a minute; a flat 277 MB never gets there.

## Main at Manny's size on every rig (2026-09-30)

The animator: «Давай сделаем размер главного контрола у всех ригов такой же как и у menny сейчас он ну
них меньше значительно». Spec `docs/superpowers/specs/2026-09-30-main-control-size-design.md`. Measured:
`Main` is an identity transform in every rig, its `MainShape` a periodic cubic circle on the floor wired to
nothing but `MotionSystem.v`; **Manny's radius 40.5236 cm, the Creep's and the Orc's 7.7574** — the same
curve 5.223893× smaller, AdvancedSkeleton's default drawing that the Creep procedure's build keeps (Manny
was built through AS's own UI), lost inside the feet. The feet stand where Manny's do on all three, so the
circle is the same ABSOLUTE size.

- **The shipped files, as text**: `docs/superpowers/plans/make_main_control_size.py` (stdlib) replaces the
  11 CV lines of MainShape's `.cc` with Manny's in `Creep_Rig.ma`, `Orc_D_Rig.ma` and
  `sources/orc/Orc_Rig.ma` (what the Orc D is built from) — the curve's header must already be Manny's, the
  file checked to differ in those lines only; idempotent. Safe to run after any rig asset rebuild.
- **The build**: `as_creep_rig_procedure.main_size()` scales Main's CVs in its own space to `MAIN_RADIUS`
  after `mark()` (in `run()`, `rebuild_creep_rig.py`, `rebuild_orc_rig.py`), so a rebuilt Creep or Orc
  comes out right.
- `tests/test_scenesetup_catalog.MainControlSize` pins every rig row's Main, and the Orc source's, to
  Manny's CVs. **A new rig row must pass it**: run the script or the procedure step.

Proof: `verify_main_control_size.py` **9/9 standalone** (the old Creep's 7.757 as the control, `main_size`
×5.223893 then ×1.0, three rigs added side by side each 40.523613 cm in world, flat, only the drawing
changed, Main still carrying the root). 2994 unit tests. A rig already in a scene keeps its small circle:
re-add it.

## The Creep's and the Orc's clavicle and shoulder controls, sized for the body (2026-09-30)

The animator: «У орка и крипа контролы ключиц плечей не видны они внутри шеометрии тела»; asked how, **grow
them to fit the body** (over `alwaysDrawOnTop`, or both). Spec
`docs/superpowers/specs/2026-09-30-clavicle-shoulder-control-size-design.md`. Measured: AdvancedSkeleton
draws every rig's controls alike — `FKShoulder_*` Manny's to the CV (radius 12.5503 about its origin),
`FKScapula_*` AS's default 9.2476 where Manny's is 12.3966 — and the Creep's and the Orc D's necks and
shoulders (the Orc's pads) are bulkier, so the drawings were buried.

- **"Seen"** (`measure_control_sizes.py`): per point of the curve, the share of 32 directions (a Fibonacci
  sphere) along which a ray reaches open space past the character's own visible meshes. No inside/outside
  test, so open or overlapping meshes do not fool it (a ray-parity probe read the Creep's five overlapping
  meshes 0.69 or 0.95 "inside" depending on its rays). Before: Manny's clavicle 0.25, shoulder 0.47; the
  Creep's 0.003 / 0.28–0.32; the Orc's **0.000** / 0.07.
- **The rule**: the drawing grows uniformly about the control's origin (its pivot, checked) by the smallest
  factor on a 0.05 grid at which both sides are seen at least as well as Manny's pair, L and R alike.
  Clavicle ×1.75 on both (16.183303), shoulder ×1.65 on the Creep (20.707995), ×1.80 on the Orc (22.590540).
  Manny is the standard and is untouched. Checked by eye first: viewport playblasts from a disposable Maya
  (port 7011, minimized, scratch prefs, killed after) showed the fins at the throat and on the back as
  Manny's are, and the rings round the Orc's pads.
- **The files, as text**: `make_control_sizes.py` (stdlib) scales the CV lines of the four shapes' `.cc` in
  `Creep_Rig.ma`, `Orc_D_Rig.ma`, `sources/orc/Orc_Rig.ma` — 64 lines a file, nothing else, idempotent. These
  `.cc` blocks end in component tags (`"gtag" 1 "tempCluster" ...`) after the CVs: a parser takes exactly as
  many numbers as the header announces.
- **The build**: `as_creep_rig_procedure.control_sizes()` (`CONTROL_RADII`, the Creep's; `rebuild_orc_rig.py`
  sets the Orc's) after `main_size()`.
- `tests/test_scenesetup_catalog.ClavicleShoulderSize` pins the radii and L = R.

Proof: `verify_control_sizes.py` **9/9 standalone** (the old files as the control, seen less than Manny's;
the procedure step ×1.75 / ×1.65 / ×1.80 then ×1.0; the eight controls seen 0.26–0.49 against Manny's
0.25–0.48; L = R; Manny untouched; `FKShoulder_L` +30 about Z turning `upperarm_l` 30.000 as before — its X is
the roll, which AS hands to the twist joints, 0.23° on the bone; only the curves changed). 3056 unit tests.
A rig in a scene keeps its small drawings: re-add it. In a second scene the verify's Manny arrived as
`Manny_Rig1`: mayaUsd's `UsdDefaultRenderSettings` lands in the first rig's namespace and keeps it alive
across a new scene — find a rig by its namespace, never by the name you expect.

## UE Bridge: an animation dragged out of the list into the viewport (2026-10-01)

The animator: «я зажимаю клавишу мышки и ташу анимацию из списка во вьюпорт и подобно с нашим оружием если я
попадаю в какой-то риг то анимация должна перекинутся на него какбуд-то мы нажали import с опцией rig если мы не
нашли ничего то тогда нам нужно сделать new rig». Asked: a new rig stands **where the clip is** («Где клип» — the
retarget puts `Main` on the clip's root, so a drop point could only be honoured by shifting the clip into the
exported root bone), and it is **Manny** («Manny, как New rig»). **Both reversed the same day**
(«анимация закидывалась ... на тот который активен во вкладке characters но если в персанажах нет
активного рига то тогда берем базовый маникен ... если мы указываем на пол ... риг с анимацией оставался в
том месте куда мы указали после все перезапеканий»): see the last two bullets. Spec
`docs/superpowers/specs/2026-10-01-uebridge-drag-to-viewport-design.md` (its addendum), plan beside it.

- **Press a row, move past Qt's start distance**: the hub's shared ghost (Tabler's `run` icon, new in
  `maya_hubicons`) rides the cursor, its caption «A_Jump · retarget onto Manny_Rig1» over a rig, «A_Jump · a new
  Manny [rig]» over a viewport with no rig, muted «release off the hub to import» / «no target - drop onto a
  viewport» elsewhere. **Release** on a rig = Import with the Rig mode onto THAT rig; on a viewport with no rig =
  Import with New rig; on the hub or off every viewport = nothing. Esc / the right button cancel. The mode
  segments and the selection do not change a drop; the timeline checkbox does; a double click still imports
  through the mode.
- **Which rig** (`droptarget.rig_snapshot` + `figure_under` in `clip_target`): every rig's game skeleton (a rig
  driving none: the joints under its group) read once per drag, projected per move, the Weapons rule —
  max(16 px, 8 % of its projected height), a tie to the rig nearer the camera. Bare skeletons are not targets.
  `choose` (the weapons) now runs on `figure_under`'s `_closest`.
- **`maya_uebridge/listdrag.py`** (Qt lazily; the window stays `cmds`): an event filter on the textScrollList's
  `QListWidget` and its viewport. The press passes through (Maya selects the row) and is remembered with its
  record (`indexAt` row → `window._STATE["filtered"]`); every MOVE while that button is held is eaten (no
  drag-select to another row, no autoscroll); at the drag's start a synthetic release at the press point,
  `sendEvent`ed past the filter, ends the click for the list — its selection stays, Qt's implicit grab stays
  (the moves keep coming over the viewport). The real `Scene.drop` defers the import one idle
  (`maya.utils.executeDeferred`, through `window._run`) so the ghost is gone before the editor's round trip.
- **`window.import_dropped(record, aim)`**: the rig found again by namespace after nothing but the drop (it can
  be deleted while the editor exports — said, nothing imported), the editor's export,
  **`rigimport.import_and_retarget(..., rig=)`** — an explicit rig takes the clip with `target="rig"` and the
  selection is not asked; `"new_rig"` ignores it.
- **`maya_hubqt.on_hub(gx, gy)`** (over `maya_hubstyle.over_hub(names)`) answers "is this point on the hub" for
  the Characters grid and the list alike; `maya_charlook.over_hub` is gone.
- **A rig the bridge ADDS is the Characters card's active row when it is a rig** (`rigimport.new_rig_entry` →
  `rig_entry_for(window.chosen_character(), default_rig())`, from the card's memory, so the card need not be
  open), Manny for a skeleton or a model with no rig — for a floor drop, Import with New rig and Import with
  Rig in a scene with none alike. The caption names it («A_Jump · a new Creep [rig] · floor (120, -36)»).
- **A floor drop leaves the new rig on the point after every bake**: `clip_target` gives the floor point
  (None above the horizon: the rig stands where the clip is); `import_and_retarget(at=)` wraps the clip's
  root in a group of its namespace (`skeldarDropShift`) BEFORE the connect — the holder remembers the root
  by PATH (`asrtSourceRoot`), so the root must not be re-parented after it (trap 16) — the connect measures
  the clip unmoved, then the group moves by `shift_for(at, root at the clip's first frame)`, horizontal
  only, and the bake carries it into the controls, helper bones and camera. Measured: `maya_asretarget`'s
  twin offsets are taken from the rig's OWN bones, its constraints are world-space, so the move reaches
  everything 1:1. The exported root bone carries the move. The rig's `Main` is what lands on the point
  (the Creep's root bone stands 2.4 cm ahead of it), as a portrait dropped from Characters stands.
- **A rig dropped ON keeps its place and facing** (the same evening: «я хочу чтобы риг остался на своем
  месте» — it used to jump to the clip's root): `rig_place` reads `Main` on the current frame BEFORE
  `reset_build_pose` zeroes it; after the connect the wrapper turns about `Main`'s start by `place_moves`'
  turn (`heading` = +Z on the floor, the short way round) and moves onto the place. The Import button's
  Rig mode does the same. Gate 12: turned 60° at x = 90 → `Main` at frame 0 on (90, 0) facing 60.0000°,
  root and `hand_r` on the rigidly moved clip to 8.5e-6 cm.

Proof: `docs/superpowers/plans/verify_uebridge_drag.py` **8/8 in a disposable Maya** (port 7015, scratch
`MAYA_APP_DIR`, `MAYA_NO_HOME=1`; the editor's export replaced by the UE clips on disk, so no Unreal): two
Manny rigs at x = ±90, `clip_target` over each projected pelvis names that rig, beside them `new_rig`, on the
time slider `none`, the list counts as the hub; a press-drag-release sent through Qt to Maya's real list,
released on the SECOND rig while the FIRST was selected and the mode read Skeleton — the second rig's `hand_r`
travels 17.056 cm under LongSword_Attack_Right_Heavy_1P, the source namespace deleted, the first rig drifts
0.0; `drop_at` on empty floor adds `Manny_Rig2` playing ShortSword_Walk_1P (15 controls keyed), the first two
0.0. A second run's gate 8 counted an extra rig: the animator was dragging clips in that Maya themselves (its
status line: LongSword dropped onto their own Manny_Rig, take cleared, retargeted) — trap 85 again, and the
real mouse half working in their hands. 3090 unit tests. Not run: a drop with a live Unreal editor exporting.

The reversal's proof, the same script's gates 9-11 in a fresh disposable Maya: Characters on Creep
[skeleton] or the UE4 Mannequin adds Manny, on Orc D / Creep [rig] that rig; with Creep [rig] active a floor
drop adds a Creep whose root at frame 0 stands on the point to 0.0 and walks ShortSword_Walk_1P's own root
track moved by exactly that much (0.0, against the clip imported as a plain skeleton); with Manny [rig] active
LongSword on another point, the same, the camera on its `camera_root` to 7e-14; the rigs already standing
0.0. The Creep carries no camera bones (only weapon_r / weapon_l travel), so its camera is not asked about.
In a second full run gate 8's status-line clause failed: the animator was in that Maya again and added an
Orc D, so a later import had overwritten the line; its geometry passed the same. 3191 unit tests.

141. **A verify that dodges a floating hub by parking it in ONE corner can park it over the very point it
     dodges.** The hub went to the top-left, the floor point projected to the left, and `drop_at` correctly
     did nothing (a release on the hub) — read as a failed drop. Try the corners until no aimed point is on
     the hub (`keep_hub_off`), and re-project after the move.

## UE Bridge: several animations at once, in a square (2026-10-01)

The animator: «Давай добавим возможность выделить массив анимаций и выполнить действие над массивом анимаций
как по кнопке так и перетягивание в сцену рукой. Если мы выбрали массив анимаций и нажали import to rig или
перетянули в уже созданный риг на сцене то пускай загружается только первая анимация ... Если мы нажали add
new rig или перетянули в пустое место на сцене то давай мы создадим все наши анимации в линию с некоторым шагом
что бы они не пересекались. В случае с кнопкой ... симметрично относительно нуля сцены а в случае с
перетягиванием ... относительно точки в которую мы указали». Asked: **the step is 2.5 m widened by the roots'
travel**, **Skeleton mode lays its skeletons out the same way**. Shipped first as a line (a drag's along the
camera's right); after the push, «всегда располагать наши анимации в квадратной формации в не зависимости от угла
камеры» - **a square on world X and Z**, the camera axis gone. Spec
`docs/superpowers/specs/2026-10-01-uebridge-many-animations-design.md` (its addendum), plan beside it.

- **The list takes a multiple selection** (`allowMultiSelection=True`; Maya's list is Qt's ExtendedSelection,
  measured). "The first" is the topmost picked row in list order (`window._selected_records`).
- **One animation behaves exactly as before**, both roads. Several: **Rig** (button, or a drop on a rig) takes the
  first and the status LEADS with «only A_Jump: a rig takes one animation (2 more picked)» — at the end it was
  clipped by the two-line status box (seen live); **New rig / Skeleton** (button) lay them all out in a square
  about the origin; **a floor drop** of several about the drop point (the origin when no floor was seen),
  whatever the camera. **Export to uasset** refuses several. (The Skeleton mode: the last two bullets.)
- **The square** (`maya_uebridge/lineup.py`, stdlib, pure): `grid_shape(n)` = (ceil(√n) columns, rows) - 3 and 4
  are 2 × 2, 5 and 6 are 3 × 2; clip i in column `i % cols`, row `i // cols`; **row 0 in front (+Z), each row left
  to right (+X)** (`COLUMNS = (1, 0, 0)`, `ROWS = (0, 0, −1)`). `side_extent` is a clip's root reach relative to
  its first frame along an axis; a column's (row's) **band** is the union of its clips' reach; `offsets` stands
  each band `step + hi - lo` past the last, first and last equidistant from the centre - so two clips in two
  columns stay a whole step apart in X and two in one column a whole step apart in Z: no two root paths ever come
  within a step, and still clips stand on an even grid. `square_offsets`, `square_slots`, `widened`,
  `sample_frames`. A rig's slot is where its **Main** stands at its clip's first frame (the floor drop's rule,
  `rigimport._place`, facing kept); a skeleton's is where its root stands.
- **The press** (`maya_uebridge/lineimport.run(records, export, target, centre, set_timeline)`): refusals (the rig
  file), EVERY clip out of the editor before anything enters the scene (one it cannot export is named and left
  out), every clip imported as its own skeleton, each root track read through `getAttr(worldMatrix[0], time=)`
  (`rigimport.root_at` - a bare skeleton on its curves, no constraint; a frame walk would evaluate every rig in
  the scene per frame), laid out, the timeline set ONCE to the union before any bake, then each clip: a rig added
  and retargeted standing on its slot, or the skeleton's root wrapped (`skeldarDropShift`) and moved. A
  cancellable progress window; a cancel keeps what is done and deletes the clip skeletons of the rest. The
  status: «3 animations onto 3 new rigs in a 2 x 2 square about (0, 0): Manny_Rig A, Manny_Rig1 B, … | step 2.5 m,
  widened beside B».
- `rigimport.import_and_retarget` is now four pieces the batch reuses - `plan_press`, `ready_rig`,
  `import_source`, `retarget_imported` - plus `root_at` / `stand_skeleton`; the one-animation press composes
  them in the old order (its press tests unchanged and green).
- **The drag carries several** (`listdrag.carried_rows`, pure): a plain press on a row picked before it carries
  every picked row (Explorer's rule), else what the press left picked, else the pressed row; the list's
  selection is put back to what is carried after the synthetic release (cmds sees it: gate 8). The ghost:
  «A_Jump · retarget onto Manny_Rig1 · first of 3», «3 animations · 3 new Manny [rig] in a square · floor (2, 1)».
  `drop_at(gx, gy, records)` and `window.import_dropped(records, aim)` take a record or a list.
- **The Skeleton mode reaches the drag** (the animator, after the square: «групповое перетягивание работает только
  с ригом даже если выбран skeleton»; the mode is read when the drag starts, `listdrag.Scene.snapshot`): over a
  viewport the clips go onto skeletons standing on the floor point under the cursor - **a rig under the cursor is
  ignored**, nothing retargeted (`droptarget.skeleton_target`) - one with its root at its first frame on the
  point, several in the square about it. Rig and New rig drags are unchanged.
- **…and Skeleton means the Characters card's skeleton, with its geometry** («скелет вставлялся с геометрией» -
  then «будем использовать скелет который активен в вкладке character»; asked: by bone names respecting
  proportions, a rig there means that model's skeleton). `maya_uebridge/skeletonimport.py`: `skeleton_entry_for`
  (the active row when a skeleton, else that model's skeleton, else Manny UE5 [skeleton]); every press of the
  mode - button or drag, one or several - adds it (`character.add_character`: meshes, textures or a palette
  colour), moves the CLIP onto the slot (its root wrapped, never the new skeleton - the Creep's `Armature` keeps
  Cascadeur's layout), `transfer`s the clip onto it by leaf name and deletes the clip's skeleton. **Twin or not
  is measured by the MEDIAN relative bone-length difference** (`is_twin`, ≤ 1 %): 0.0000 against Manny UE5 on six
  UE clips, 0.2424 against the Creep, 0.2403 against the UE4 Mannequin - the share within 1 % (the first try) read
  0.90 for a 3P clip against Manny, because 3P clips animate bone translations and scale (trap 152). A twin takes
  every bone's world matrix (`parentConstraint`, no offset): exact; another body every bone's world orientation,
  its own lengths kept, root and pelvis placed too, its `ik_*` helpers at rest (the Creep's `ik_hand_gun` stands at
  zero with `ik_hand_r` 110 cm under it); a UE4 target takes the UE4 spine map; baked
  (`bakeResults -simulation`), the constraints deleted. The ghost: «A_Jump · a new Manny UE5 [skeleton] · floor
  (100, -50)»; the status «ShortSword_Attack_Thrust_3P onto Manny UE5 [skeleton] root: 91 bones exact, frames 0-36
  | not in the clip: camera_bone, camera_root | standing at floor (100, -50)».

Proof: `docs/superpowers/plans/verify_uebridge_many.py` **15/15 in a disposable Maya** (port 7023, scratch
`MAYA_APP_DIR`, `MAYA_NO_HOME=1`, minimized, killed after; the editor's export replaced by
LongSword_Attack_Right_Heavy_1P, ShortSword_Attack_Thrust_3P - 248.7 cm of root travel forward, 23 cm sideways -
and ShortSword_Walk_1P on disk), run again whole for the square: the button with New rig - three Mannys on a 2 × 2
about the origin, Main at each clip's first frame on its slot to 0.0 (columns ±132.8, widened by the thrust's
15.6 cm sideways reach; rows ±125 - it walks forward, away from row 1), the least clearance between root paths
250.0, the timeline 0–61; Skeleton - each root playing its own keys moved onto its slot, 0.0 off; Rig - the first
only, the note first; a real press–drag–release of the three picked rows onto the floor with the camera looking
along X: all three carried, the list kept them picked, the same square on the world's axes about the point (0.0
off, clearance 250.0); the three dropped on a rig - the first only, the other two rigs 0.0 drift. The Skeleton mode, rerun for the Characters skeleton (a snapshot of HEAD plus these files, a
peer's half-built Armor card left out): the button with Manny UE5 [skeleton] active - three Manny skeletons, 2
skinned meshes each, every sampled bone on the moved clip to 1.3e-13 cm and 2.4e-4°; Creep [rig] active, the three
dragged onto a Manny rig's pelvis - three Creep skeletons, 5 meshes each, every bone turned as the clip's to
2.1e-4°, the root on the moved track 0.0, `lowerarm_l` never stretched, the rig untouched; the thrust alone onto
the floor with Manny's skeleton - exact on the point (gates 6, 12-15, **15/15** in all). A
verify phase that drags must pick its mode itself: a Skeleton mode left by the phase before made gate 8's drop
skeletons, correctly. The slots were
held against each clip's root walked frame by frame with `currentTime` on a plain import. The bridge's 619 unit tests green. A
Shift range cannot be tested offscreen (Qt ignores a sent Shift for a range on a bare QListWidget - measured; Ctrl
works): the Shift road is the same code as Ctrl's.

151. **`importlib.reload` of a module re-runs its module-level state**: reloading `maya_uebridge.window` in a live
     Maya to pick up a fix emptied `_STATE`, and the list still showed three rows while Import answered «select
     an animation first». A reload in a verify run must put the state back (`_STATE["records"]` + `_repopulate`)
     - or purge and rebuild the panel; the closures over the module see the new, empty dict.
152. **A UE 3P clip animates its bones' translations and scale**, so "the same skeleton?" asked as "what share of
     the bones has the rest length at frame 0" reads 0.90 against the very skeleton it was made on (ShortSword
     Attack Thrust 3P against Manny UE5; `spine_01` scales 1.0022) - on a 0.9 threshold. Ask the MEDIAN bone:
     0.0000 against Manny on all six clips, 0.24 against other bodies. And a disposable Maya the animator
     minimized has no viewport to drop on: `Viewport.at` answers nothing (verify `_drag_rows` restores it).

## Characters and the UE Bridge: one card (2026-10-01)

The animator: «UE bridge и character эти две вкладки имеют общий функционал они добавляют персонажей в
сцену и они зависят дргу от друга. Я думаю их нужно объеденить в одно окно давай попробуем». Asked (three
mockups): **A** — who on top, what below; **the two switches merged**; **«Characters» the first card, the
Scene group above Animation**; **Skeleton + Onto selected = onto the selected skeleton**. Then «Делай все
до самого конца». Spec `docs/superpowers/specs/2026-10-01-characters-and-bridge-one-card-design.md`.

- **The hub**: the `uebridge` section is gone; `characters` is the first row of `maya_hub.SECTIONS`, so the
  groups read Scene (Characters, Weapons, Connections, Shared, Armor), Animation (Retarget, Graph Overlay,
  Center of Mass), Look, Settings. `maya_hub.ALIASES = {"uebridge": "characters"}`: `section`, `show`,
  `focus`, `expand` and `scroll_to` resolve it, so `maya_uebridge.show_window()` (its `HUB_SECTION` is
  `"characters"`), the hotkey row `window.uebridge` and the flagged shelf button land on the card. The
  `skeldarAnimHub_collapsed_uebridge` memory is left unread.
- **The card** (`maya_scenesetup.window.build_characters_panel`), top down: the subtitle (the character),
  `[Rig | Skeleton]`, the portraits, Add Character (**secondary** now) + Delete, Camera Setup, then
  `maya_uebridge.window.build_rows()` (was `build_panel`; no column of its own) — the editor line
  `ueAnimBridgeHeader` (role **context**, two lines tall: «Unreal: not connected - 619 animations from the
  last refresh, press Refresh for the live list», `editor_line`), the editor dropdown + Refresh, search, the
  list, `Import [Onto selected | New]`, the timeline box, **Import** (the card's one primary), the two
  exports — and **one status line**, `mayaSceneSetupCharacterStatus`. The bridge's `_STATUS` IS that name
  (a test pins the two equal); its old `ueAnimBridgeStatus` is gone. On open the line says the portrait's
  choice (`_repopulate(quiet=True)`). A bridge that fails to build is a line of text, the rest of the card
  stands (`_bridge_rows`).
- **The modes**: `import_mode() = mode_for(import_kind(), import_target())` (pure table): the kind is the
  card's memory (`chosen_character().kind`, else `remembered_choice()[1]`), the target the segments
  `ueAnimBridgeMode_onto` / `_new` (not remembered, Onto selected lit on each build). Rig x Onto → `rig`,
  Rig x New → `new_rig`, Skeleton x New → `skeleton` — the three old modes, unchanged inside — and
  **Skeleton x Onto → `onto_skeleton`**, new. `MODE_SEGMENTS` and `mode_button` are gone.
- **Onto a skeleton in the scene** (`skeletonimport`): `bare_roots` (character roots no rig owns);
  `selection_names` (a joint → its topmost joint, a mesh → its skin's influences, a transform → the
  skeleton under it, a weapon / armor piece → the bone its space follows, a rig node → that rig);
  `choose_skeleton` (pure): one named; several → refused; a rig named and no skeleton → «Manny_Rig is a rig
  - pick Rig in Characters, or select a skeleton»; nothing named → the only one, none → a new skeleton
  where the clip is (the `skeleton` road), several → refused, named («Manny UE5 [skeleton] (root)»,
  `skeleton_label`, from Delete's import record). `onto_refusal`: a bone under a constraint that is not our
  weapon's (a camera on camera_root) refuses before the editor is asked. The press: its place read first
  (`skeleton_place`: the root on the current frame and `rigimport.facing` — the flatter of +Z and −Y, so a
  UE root under −90 X and Main both read 0 as their files stand), the clip imported, our weapon links
  unlinked, the clip wrapped and turned/moved (`rigimport.move_wrapper`, `place_moves(..., facing_of)`),
  `transfer` (which now cuts the time curves on the bones it drives first, or the constraint splices a
  pairBlend over a previous take), the links relinked, the clip's skeleton deleted. Bones the clip has
  nothing for keep what they had and are named. Several picked: the first (`skeletonimport.first_only`).
- **The drag** reads the KIND at its start (`listdrag.Scene._read_kind` → `window.import_kind`): Rig as
  before; Skeleton snapshots the bare skeletons (`droptarget.skeleton_snapshot`) and a skeleton under the
  cursor is kind `onto_skeleton` («A_Jump · onto Manny UE5 [skeleton] (root)», found again by UUID at the
  drop), else empty floor a new skeleton as before; a rig under the cursor is still ignored.

Proof: `docs/superpowers/plans/verify_characters_card.py` — **13/13 in a disposable Maya** (port 7047,
scratch `MAYA_APP_DIR`, `MAYA_NO_HOME`, minimized, killed after; the editor's export replaced by UE clips
on disk): the first card Characters, `show("uebridge")` opening and lighting it; the controls top down by
their Qt positions, one status line; the content's minimum **504 ≤ 510** at the animator's dock; Import the
one primary; both modules writing the one line; the four modes clicked through Qt; Rig x Onto onto a Manny
rig moved to (−150, 80) and turned 45° — kept in place and facing; Skeleton x New exact (1.2e-13 cm);
**Skeleton x Onto with the skeleton's MESH selected**, the skeleton at (100, −50) turned 90° with a Long
Sword in its right hand — every bone, weapon_r included, on the clip moved by one rigid floor move to
2.7e-4 cm / 2.4e-4°, its root at the first frame on (100, −50) facing 90, «kept in place at (100, -50) |
weapon re-linked on weapon_r», the sword riding weapon_r at one grip over the take (5.6e-7); the two
refusals with the editor never asked; a real press–drag–release onto a skeleton's pelvis (the ghost
naming it) and that skeleton playing the clip in its place (7e-14 cm). Picture:
`docs/superpowers/plans/characters_card.png`. 3506 unit tests. `verify_uebridge_many.py`,
`verify_uebridge_drag.py` and `verify_hub_skin.py` still click `window.mode_button` / read
`skin.cards["uebridge"]`: history, written for the bridge's own card.

**…called Animation Setup, with two orange Imports** (the same evening, after the push: «Давай Раздел
Character Заменим на Animationsetup. Add Character на + Import (Вернем кнопке оранжевый цвет)»; asked:
«+ Import» on top, «Import Animation» below, both orange). The label is **Animation Setup**, the key
still `characters`; Add Character is **«+ Import»** and `primary` again (the skin's label «Import» with
its plus icon, the classic hub spells «+ Import», `hubstyle.pick`); the bridge's button is **«Import
Animation»**, also `primary` — one orange button per half. The wording followed: the portrait line
«press Import», the refusal «pick Rig in Animation Setup», the tooltips, Delete's dialog title, the
hotkey rows «Animation Setup» / «Import Character». `verify_characters_card.py` card + photo again in a
disposable Maya (gate 4 now: the two primaries); 3507 unit tests.

## One Inventory card: Weapon and Armor, tiles everywhere, headings everywhere (2026-10-01)

The animator, the same evening: «Та часть где мы подключаемся к анрилу ее нужно озаглавить UE Connect
пускай будет. Далее давай объеденим вкладки weapon и армор в одну inventory. Пускай в ней будет два
раздела weapon и армор. Давай для wepon раздела уберем функционал сетчатого инвентаря, оружия одевать на
персонажей и выкидывать в сцену драгом можно но перемещать по сетке не нужно. Пусть все будет
конссистентно». Asked (a mockup): tiles + the hand cards; Equip / Unequip in both; armor drags too;
headings everywhere — all four the recommendation. Spec
`docs/superpowers/specs/2026-10-01-inventory-card-design.md`.

- **Headings**: a hub role `heading` (`maya_hubstyle.ROLES`; bold, the primary text, a hairline under;
  classic: `boldLabelFont`). Animation Setup: «Characters» (`mayaSceneSetupCharactersHeading`) and «UE
  Connect» (`ueAnimBridgeHeading`, the editor line under it lost its «Unreal: » prefix); Inventory:
  «Weapon» (`mayaSceneSetupWeaponHeading`) and «Armor» (`mayaSceneSetupArmorHeading`).
  `scenesetup.window.heading(name, label)` makes one.
- **The hub**: the `weapons` row is **Inventory**, icon `backpack`; the `armor` row is gone and
  `ALIASES["armor"] = "weapons"` (`armorpanel.show_window`, the `window.armor` hotkey row). Key `weapons`
  kept, as Animation Setup kept `characters`; Connections still follows it.
- **The card** (`build_weapons_panel`): subtitle, Weapon, the weapon panel, **Equip** (primary, `sword`)
  + **Unequip** (danger) — Add / Remove Weapon renamed, same functions, the line's wording with them —
  then `armorpanel.build_rows()` (Armor, its tiles, Equip (primary, `shield`) + Unequip), **one status
  line** `mayaSceneSetupStatus` (armor's `_STATUS` and `_BOUND` ARE the card's, pinned equal), then
  `armorpanel.watch()` — the SelectionChanged job on that line refreshes the pills with `say=False`, the
  line staying the last press's. `armorpanel.build_panel` is gone. Hotkey rows: «Inventory», «Equip
  Weapon», «Unequip Weapon».
- **The weapon panel** (`maya_inventory`, `maya_invlook`): the hand cards unchanged (their proportions
  still follow a tenth of the width, `UNIT`), under them **tiles** — `maya_charlook.grid`, the portraits'
  and the armor's geometry — the icon turned 45° (`TURN`; an upright 1 × 4 sword would be a quarter of the
  tile wide), the name under it, the pick lit, an «equipped» pill on a weapon the character holds in a
  hand or on the floor (`look.worn`). Drops: tile → hand card / a hand in the viewport / the floor as
  before; hand card → the other card moved, → the tiles taken off; tile → tiles nothing. **Gone**: the
  cell grid, rearranging, Sort, `skeldarInventoryLayout`, `pack` / `plan_move` / `arrange` / the record;
  the ghost is the portraits' (square, `backdrop="field"`).
- **The armor tiles drag** (`maya_armorgrid`): past Qt's start distance the hub's ghost; over a character
  in a viewport (`droptarget.character_target` over `droptarget.snapshot()`, the Weapons rule) «Tech Limb ·
  onto Manny_Rig», the release `armorpanel.equip_on(root, key)`; elsewhere «drop onto a character»,
  nothing; on the hub nothing; Esc / the right button cancel.

Proof: `docs/superpowers/plans/verify_inventory_card.py` **8/8 in a disposable Maya** (port 7047): the
card right after Animation Setup, `show("armor")` lighting it; the four headings; the card top down with
one line and the two orange Equips, content 504 ≤ 510; the tiles (no grid); `drop_at` of Long Sword onto
the rig's projected right hand (into it, its pill), of Spear 01 onto the floor (weapon_l follows it), of
the right hand card onto the tiles (taken off); a real press–drag–release of the Tech Limb tile onto the
rig's spine (worn, the caption naming the rig). `verify_characters_card.py` card 5/5 again with the
headings. Pictures `inventory_card.png`, `characters_card.png`. 3504 unit tests.
`verify_inventory_live.py` and `verify_weapons_card.py` drove the cell grid: history.

**…two tabs, not two stacked sections** (minutes later, after using it: «у нас есть вкладка inventory и
в ней два раздела между которыми мы переключаемся нажимая на название раздела Weapon Или Armor как бы в
разделе две под вкладки»; spec addendum). The card opens with a **[Weapon | Armor]** segment row
(`mayaSceneSetupInventoryTabs`); each tab is a column (`mayaSceneSetupWeaponTab` / `_ArmorTab`), one
managed at a time (`window.show_tab`: the column, the segment, the memory `mayaSceneSetup_inventoryTab`,
the shown panel fitted to its placeholder again, that tab's pick on the line); the «Weapon» / «Armor»
headings are gone, the segments name the sections (Animation Setup keeps its headings: it was asked
stacked). `window.refresh` writes the weapon line only on the Weapon tab. `armorpanel.show_window` opens
the Armor tab, `window.show_weapons` the Weapon tab. `verify_inventory_card.py` **8/8** again, the tabs
clicked through Qt (one column visible at a time, the card 757 / 460 px tall, the line following the
tab); pictures `inventory_card.png`, `inventory_card_armor.png`; 3507 unit tests.

## Center of Mass: a live point, a fast trail, the CoM tool (2026-10-01)

The animator: «у нас должна быть какая-то точка к которой мы можем сделать motion trail … моушен треил
изменялся если мы изменяем положение нашего персонажа … передвигать сам центр массы и при этом наш риг в
зависимости от карты весов тоже будет двигаться корректно … эта система должна быть производительной …
если мы сделаем на констрейнах … моушен треил отрисуется с задержкой». Asked, and answered: the mass
**from the mesh and the skin**; moving the CoM moves **every part** («пока так», pinning the feet comes
later); the UE bone `center_of_mass` **left alone**; **our own tool**, not a manipulator plug-in. Spec
`docs/superpowers/specs/2026-10-01-center-of-mass-design.md`, plan beside it. Package
`SkeldarAnim/maya_com/` (payload row), hub section **Center of Mass** (Animation, icon `target`), hotkey
row `window.com`.

**Measured first, and it decided the design**: Maya's own Motion Trail on a CoM point costs **4.5 s per
key edit** in a GUI Maya with Cached Playback filled — every trail frame goes through a DG time context
(`getAttr -time` 41 ms, `MDGContext` 45 ms a frame for the whole body) — while the same frame through
the parallel EM (`MAnimControl.setCurrentTime` under `refresh -suspend`) costs **5 ms**. The animator's
fear was right but constraints are not the cause: the cost is evaluating the rig at every trail frame,
whatever computes the point. Cached Playback cannot be read (`dbpeek -op cache -a data` is a 277 MB dump
with no values); ghosting the point drew nothing. **`motionTrailShape` takes points we give it**
(`points` pointArray, `startTime`, the draw attributes), so the trail looks like Maya's and is ours.

- **The mass** (`massmodel.py`, numpy, pure): the union of the character's mesh shells, welded (Unreal's
  are split along normal seams), each closed by fan caps over its border loops, ray parity per shell
  along X/Y/Z with a majority vote, OR-ed — Manny's Skin_3p is 45 shells / 5142 border edges, the Creep
  five overlapping meshes, the Orc D cloth over skin, so a surface integral would leak and double-count.
  Voxels of 1.5 cm, each skinned by the closest surface point (`MMeshIntersector`; its
  `barycentricCoords` (u, v) weight corners 0 and 1 of `getTriangles`' order, measured 1e-5), its rest
  point through the blended skin matrix, so a joint gets a mass and a local centre and
  **CoM = Σ m_j (c_j · M_j) / Σ m_j exactly for linear skinning**, from any pose. 1P meshes (a `1P`
  token) are left out — Hands_1P would weigh the arms twice. Manny 83 L, the CoM at 0.585 of stature;
  feet, hands, head, shanks on de Leva's table, the thigh light (8.9 % against 14.2) because Manny's skin
  gives the buttocks to the pelvis — the partition is the skin's, as chosen. Weighing takes 1.2–2.2 s.
- **The live point** (`network.py`): four `wtAddMatrix` over the skinned joints' worldMatrix with
  weights m̂·c_x, m̂·c_y, m̂·c_z, m̂ — row-vector `c·M = c_x·row0 + c_y·row1 + c_z·row2 + row3` — four
  `rowFromMatrix`, one `plusMinusAverage`: nine nodes, no constraint. Equal to the formula at a posed
  frame to 6.5e-7. Group `ns:CenterOfMass` under the rig's top group (marked `skeldarCom`, the parts by
  UUID in `skeldarComNodes`, the root by message), the handle `alwaysDrawOnTop`, a floor marker at the
  root's height, two trail shapes (Past / Future in our colours; the default future colour is purple).
  **Cost: none measurable** — `verify_com_cost.py`, mayapy A/B, best of seven walks ×3: 5.45 ms without,
  5.41 with the network, 5.04 with the engine's callbacks too.
- **The engine** (`engine.py`, `frames.py` pure): frames are marked DIRTY by a time curve edited (only the
  frames whose sampled value changed, against a snapshot; through blend nodes a few hops), a static set
  on a control or joint (all frames), the range moving (the new frames); a set on a curve-driven plug is
  a tweak — the current frame's point is read live. Slices on a Qt single-shot timer, nearest the
  current frame first, ≥ 2 frames a slice while a frame is cheap, never with a mouse button down or
  during playback; unkeyed tweaks recorded before a walk and put back after it (MDGModifier). One walk
  serves every character. State on `sys._skeldar_com` (trap 111). Measured live with three rigs (15 ms
  a frame — the EM evaluates every rig at each step): a key edit → its 17 frames in 9 slices, the trail
  redrawn **0.52 s** after the key, slices ≤ 57 ms; one rig: 17 frames in 0.12 s.
- **The tool** (`drag.py`, `dragmath.py` pure): selecting a handle puts a `draggerContext` on (W/E/R
  bounce back to it, selecting anything else restores the tool); LMB in the view plane, Shift the floor,
  Ctrl vertical; a click without a drag selects. A press measures each world driver's local response by
  finite differences (`plan`, cached by the follow blends and the drivers' parent rotations; 43–119 ms)
  — `RootX_M`, IK legs/arms, poles (they follow blends of the others), IK spine; never `Main`; a bare
  skeleton's pelvis and ik roots — and every part moves by the same d (the least mass-weighted
  displacement putting the CoM there). Release keys channels that have curves (Maya's autoKey rule);
  a channel without one is a static set, as Maya's Move does. `undoMode="all"`.

Proof: `verify_com.py`, every phase green in a disposable Maya (Manny, Creep, Orc D, port 7013): the
three trails equal to a plain walk to **0.0**; a key edit recomputing exactly the 17 changed frames, the
other two rigs untouched to 0.0; an unkeyed pole recomputing all 61; a tweak surviving the engine with
the trail's current point on it; the simulated drag putting the CoM 0.0099 cm off the cursor's ray,
every weighed bone moved by d to 1.3e-7, Main still, RootX_M keyed, one undo putting it back; Remove
leaving nothing; Cached Playback out of safe mode; playblasts of the trail and its floor shadow. 3182
unit tests. **Not proven: a real mouse drag** (the context's own press/drag/release were driven with
their queries faked) — the animator's hands are the proof of that.

143. **Maya's Motion Trail evaluates each trail frame through a DG time context, and Cached Playback does
     not help it**: 4.5 s per key edit for a whole-body point (41 ms a frame), 0.75 s for one hand, while
     the EM does a frame in 5 ms. A trail of anything driven by a rig wants its points computed by an EM
     time walk and handed to a `motionTrailShape`.
144. **API 2.0 `M3dView.viewToWorld(x, y, MPoint, MVector)` FILLS its arguments** (two arguments raise
     "takes exactly 4"), and `cacheEvaluator -q -safeModeTriggered` answers the STRING `'0'` — truthy.
145. **Turning the undo queue off and on (`undoInfo -stateWithoutFlush`) inside an open chunk breaks the
     chunk**: one Ctrl+Z left the drag half applied. Probes that net to nothing can stay recorded. And
     `autoKeyframe -state` is itself undoable: a verify that switches autoKey off after a drag and then
     undoes, undoes the switch.
146. **A scripted time walk fires timeChanged afterwards even though it ends on the frame it started
     from.** The engine marked the tweaked frame dirty and drew the keyed pose under a standing tweak;
     anything reacting to a time change must compare with the frame it recorded.
147. **A GUI Maya's per-frame time swings ±0.6 ms a rig from one run to the next** — Cached Playback
     refills in background threads after every graph change and takes the cores (the same scene read 15
     and then 11 ms). A cost measured there needs the cache off, the best of several runs, and the
     precise A/B belongs in mayapy.

## The hub's interface sounds: a tick on every button (2026-10-01)

The animator: «Давай добавим звуковое сопровождение для нашего интерфейса. Давай для теста сделаем приятный
звук когда срабатывает выделение какого-то эллемента ... я вожу мышкой по кнопочкам нашего меню и вот тут
давай сделаем приятный и простой звук наводки на кнопочку». Asked: **every button of the hub** (not only the
action buttons, not the grid tiles), **one sound, chosen by me**, the ⋮ menu only switching it. Spec
`docs/superpowers/specs/2026-10-01-hub-hover-sound-design.md`, plan beside it.

**Measured first**: Maya 2027 ships `PySide6.QtMultimedia` (backend `plugins/multimedia/windowsmediaplugin.dll`);
a `QSoundEffect` on a WAV is `Ready` in 21 ms in mayapy (the pool of three: 0.44 s, hence the preload). The
hub's clickable widgets, read off the animator's open hub: Maya's `cmds.button` is a `QPushButton`, the
segments `QmayaIconTextRadioButton` / `QmayaIconTextCheckBox` (`QPushButton`s), `checkBox` `QmayaCheckBox`
(a `QCheckBox`), the strip and header `QToolButton`s — every one a **`QAbstractButton`**; dropdowns
`QmayaOptionMenu` → `QComboBox`; card headers our `CardHead`.

- **`SkeldarAnim/maya_hubsound.py`** (stdlib at import, a payload row): `synth(Tone)` / `wav_bytes` (pure) —
  the "glass tick": E6 1318.51 Hz + its octave at 0.2, decays 16 / 7 ms, a 1.5 ms raised-cosine attack, 80 ms
  with a 15 ms cosine fade to exactly 0, peak 0.178 (−15 dBFS), 48 kHz 16-bit mono; shipped as
  **`assets/sounds/hover.wav`** (7.7 KB), written by `docs/superpowers/plans/make_hub_sounds.py`, a test pins
  the file to the synthesis (1 LSB of slack). `play(name)` never raises: off (optionVar
  **`skeldarAnimHub_sounds`**, **default OFF** since the same afternoon — «Отключи воспроизведение звуков
  по умолчанию»; the first push, 969dadd, shipped it ON), a missing file or no backend answers False; a pool of **3
  `QSoundEffect`s used in turn** (a play on a playing effect restarts it, and the cut tail clicks), else
  `winsound` async; **no new sound within 35 ms** (a sweep enters a button every 15-30 ms). Players and the
  throttle on `sys._skeldar_hubsound` (trap 111), one per file (path, size, mtime — an update's new file gets
  a new player).
- **`maya_hubqt.sounding(widget, root)`**: a `QAbstractButton`, `QComboBox` or `CardHead`, enabled, under the
  root — the type asked first, since every Enter in Maya passes the skin's application-wide watcher.
  `Skin._hover_from` calls back **`"hover"`**; ⋮ gains a checkable **Interface sounds** row (callback
  `"sounds"`, `Skin.sounds_action`, `paint_sounds`). `maya_hubqt` imports no audio (a test reads its source).
- **`maya_hub`**: `"hover"` → `maya_hubsound.play("hover")`, `"sounds"` → `set_sounds(on)` (remembered, the
  row painted; turning it on plays the tick once); `_dress_sounds` at the end of `_dress_header` paints the
  row and, only while the sounds are on, preloads (off, no audio is opened at all). The classic hub is
  silent.

Proof: `docs/superpowers/plans/verify_hub_sound.py` **17/17 in a disposable Maya** (port 7021, scratch
`MAYA_APP_DIR`, `MAYA_NO_HOME=1`, minimized, killed after; the 898c18c build from a `git archive`): Qt Enter
events sent to the REAL widgets — a Maya button, a segment, a checkbox, a dropdown, a card header, a strip
jump each play once (the effect playing 1-13 ms after the call); a label, a field and a card frame stay silent;
three Enters 10 / 60 ms apart play / throttle / play; the menu row off writes 0 and silences, on writes 1 and
ticks once; left as found. 3250 unit tests. **The first live run, in the animator's Maya on 7001, crashed
that Maya** — trap 148. The disposable hub's floating window sat under the animator's real cursor and Qt
delivered genuine Enters to its card headers mid-run (the throttle ate one): the gates count only the plays
made inside each synthetic send. Not built: a click sound, sounds on grid tiles / list rows, a volume.

148. **A verify that held widget wrappers across `processEvents()` killed the animator's Maya** (2026-10-01
     11:55:48, `MayaCrashLog261001.1155.dmp`): an access violation reading `0x8` in `Qt6Core` called straight
     from PySide's `QtCore.pyd` — a `QCoreApplication.sendEvent` to a deleted widget. Another session had
     installed its build into that same Maya 40 s before (`install.install` → purge → deferred
     `rebuild_open_hub`), and the verify collected the hub's widgets with one `findChildren` and pumped events
     for two seconds before using them. A wrapper of a Maya-owned widget that is deleted is not "already
     deleted" (trap 135), so the next call reads freed memory. Two rules: a verify finds every widget AGAIN
     by name, in the hub standing right then, before each use (`verify_hub_sound.find`), and **before sending
     anything to the animator's Maya, ask the other sessions (ListAgents / SendMessage) whether one of them is
     installing or running there** — the port serves whoever connects, and an install rebuilds the hub under
     whatever is running. Maya left `Manny_Rig[Recovered-MY PC.2026-10-01-11.55].ma` (54 MB, complete) in
     `%TEMP%`: the untitled scene at the crash, named after the last file it imported.

## The hub's cards slide, a jump glides (2026-10-01)

The animator: «А элементы нашего интерфейса возможно открывать закрывать с какими-то анимациями, просто для
красоты и приятности?»; of three scopes offered they chose the cards and the scroll (not the light, the
message line, the grids). Spec `docs/superpowers/specs/2026-10-01-hub-card-motion-design.md` (read its
addendum), plan beside it.

- **A card's body slides** open and shut, ease-out cubic, `maya_hubmotion.duration` (140 + 0.12 a logical
  px, kept within 160..260 ms; an OPENING 1.5 times that, 240..390 — the animator, the same evening:
  «замедлим анимацию открытия вкладки примерно на 50%»), the chevron turning with it (`maya_hubqt.rotated`). How: the body's own
  layout is DISABLED for the slide and laid out once at its full height (`Card._lay_out_full`, re-read every
  tick), and the body's `maximumHeight` is capped tick by tick — so a short body CLIPS its children; a plain
  height animation of a laid-out widget squeezes them to their minimums. At the end the idle card is what it
  was before (cap off, layout enabled). The gap under the header moved into the body's top margin.
- **A jump glides**: `Skin.scroll_to(key, animate=True)` waits for the OTHER cards to finish sliding
  (`_glide_when_settled`, at most `GLIDE_WAIT_S` 0.6 s), then eases over `SCROLL_MS` 240 toward
  `min(card.frame.y(), bar.maximum())`, both read live, for at least what is left of its card's opening,
  and lands again one turn after it ends (the scroll area widens its range later, on its own LayoutRequest);
  the wheel or the bar (`actionTriggered`, `sliderPressed`) stops it.
- **Only the animator's moves animate**: `Card.toggle`, `maya_hub.focus` / `expand` (the strip, `show(key)`,
  the update chip) pass `animate=True`; `set_collapsed(c)` from code is instant, as is a card off screen.
- **⋮ → Interface animations** beside Interface sounds (`maya_hubmotion.OPTIONVAR`
  `skeldarAnimHub_animations`, ON by default; `maya_hub.set_animations`). The classic hub is untouched.
- Measured before building (a disposable Maya, the repo's hub): a HIDDEN body's size hint is wrong (Weapons
  537 against 657 settled, Characters 763 against 420) — shown at `maximumHeight 0` it is right; a step
  costs 2.5 ms (3.6 with ten cards closing at once).

Proof: `docs/superpowers/plans/verify_hub_motion.py` — **11/11 in a disposable Maya** (port 7016, scratch
`MAYA_APP_DIR`, the repo's hub FLOATED and sized to the animator's dock, viewport 510): every card opened and
shut through real time (the send turns the event loop itself), monotonic onto its settled height, its content
at full height every turn and clipped, the header steady; p99 turn 5.0 ms; a slide turned back mid-way; a
jump to Studio with three cards open above — they shut, Studio opens, the glide monotonic onto it; switched
off, instant. 3264 unit tests. The animator watched and clicked in that Maya meanwhile (one run's UE Bridge
was shut mid-slide and the hub resized under the gates — trap 100 again), and saw what no gate measured: the
title shaking (trap 149). Installed in the animator's Maya (7001, reopened) from a `git archive` of 7f8880e (payload
a67f5f8): the open hub rebuilt from the installed copy, the folder equal to the snapshot; pushed, release a67f5f8.

149. **A widget's own layout runs on its OLD size, and a Preferred child takes the difference.** Capping a
     card's body every tick posts LayoutRequests; the card's column ran first, on the height the outer column
     had given the card a moment earlier, so while shutting the HEADER grew (33 → 34, 36 … 350 px and back)
     and while opening it shrank to 17 — its title and chevron, centred in it, shook («название заголовка
     "дрожит"»). Every gate passed: they measured the body. A part that must not move gets a `Fixed` policy on
     that axis, and an animation lays its widget AND the column holding it out at once each tick
     (`layout().activate()` on both — `Card._lay_out_now`). Offscreen tests never see the interleaving: read
     the layout right after the tick, before `processEvents`, and require it equal to the settled one.
150. **`host_widget(CONTROL).window()` is MAYA'S MAIN WINDOW while the hub is docked** — and a disposable
     Maya's hub opens docked. A probe that "sized the hub's window" shrank MayaWindow to 560 px and left the
     hub a 127 px viewport (content minimum 305): four of the first gates failed on a layout nobody uses.
     Float it first (`workspaceControl -e -floating true`), then size the floating window until the scroll
     viewport reads the dock's 510.

## The hub's card light: a glow that fades, a flash when chosen (2026-10-01)

The animator, after the slides: «Теперь давай сделаем красивый глоу и анимацию подсветки при выделении
карточки или наведении на раздел. Сделай все сам я отойду на часик.» Every choice was taken alone; spec
`docs/superpowers/specs/2026-10-01-hub-card-light-design.md`.

- **Each card's frame is a `CardFrame`** (`maya_hubqt._frame_class`, still `QFrame[skCard]` to the
  stylesheet, which draws the plain face) holding `level` and `flash` (0..1); its `paintEvent` adds
  `paint_light`: the face `card_active` at `level`, an INNER glow — the accent at `GLOW["alpha"]` 0.28 at the
  ring falling off as (1 − depth)² over 10 logical px, drawn as rings ONE PHYSICAL PIXEL wide
  (`maya_hubstyle.glow_rings`; 1.5 px rings showed as bands at 150 %) — and the 2 px ring `card_edge`.
  The stylesheet's `[skActive="true"]` rule is gone (it switched the look at once); the property is still
  set on the lit card, with no repolish.
- **It fades**: `Card.set_lit(on, animate)` — in `LIGHT_IN_MS` 140 (ease-out), out `LIGHT_OUT_MS` 260
  (smoothstep), from wherever it stands (`light_ms` takes its share). `Skin._light` cross-fades the old card
  and the new one; who is lit is the 2026-09-28 rule, unchanged.
- **A card newly chosen flashes** (`Card.pulse`, `FLASH_MS` 480, `flash_at`: up over the first 18 %, then a
  long fall): the ring toward `accent_text`, the glow brighter and 60 % deeper. `Skin.set_active` pulses
  only when the pinned card CHANGES — a press inside the card already chosen would flash on every click.
- **Interface animations off**: the light switches at once, no flash.
- **No outer halo**: the cards stand against the scroll area's left edge, so a halo would be cut on one
  side, and making room narrows every card (the Weapons card is tuned to the 360 px dock, trap 117); a
  `QGraphicsDropShadowEffect` would render the whole card offscreen on every repaint inside it.
- Measured first: a full repaint of a card costs 1.5 ms median, 3.0 p95 (UE Bridge, 881 px with its list),
  0.5 for Retarget, ~0 scrolled out of view — so the whole card repaints each tick and the face fades too.

Proof: `docs/superpowers/plans/verify_hub_light.py` **6/6 in a disposable Maya** (port 7016, the repo's
hub floated to the dock's 510 px): a hover fades a card up monotonically, another cross-fades the two,
a press on another card flashes it to 1.00 and back while a press inside it does not, a quick sweep across
the cards keeps the loop's p99 turn at 6.5 ms, the screen's pixels the lit ring (224, 122, 54) = card_edge
and face (56, 58, 65) = card_active, a dark ring the plain card; off = instant. `verify_hub_motion.py` 12/12
again on the new frame. 3284 unit tests.

## The hub's controls glow under the mouse (2026-10-02)

The animator: «Давай поработаем над красотой нашего интерфейса. Попробуй сделать так что бы все надпись
немного подсвечивались легким свечением когда мы наводим на них мышкой. Сейчас у нас панели разделов
выделяются подсветкой но все остальные эллементы нет». A prototype (the hub's stylesheet at 150 %, every
control hovered at once, three looks) was shown; asked, they chose **the glow in the text's OWN colour**
(over a warm accent glow for all) and **everything clickable** (over every text: a glow under the mouse
says "this can be pressed"). Minutes after the first build: «уберем свечение из надписей заголовков
разделов мы и так разделы подсвечивали раньше» — **card headers do not glow**. Spec
`docs/superpowers/specs/2026-10-02-hub-hover-glow-design.md` (read its addendum), plan beside it.

- **What glows** (`maya_hubqt.glowing`): what ticks on hover (`sounding`: Maya's buttons, segments,
  checkboxes and chips, dropdowns, the strip's and the header's icons) minus card headers (their card
  lights), swatches (a dot has no ink) and a widget carrying somebody else's graphics effect. One at a
  time; the mouse onto a child of a lit control keeps it lit. Skin only (the classic hub as before).
- **The look** (`maya_hubstyle.HOVER_GLOW`, the arithmetic `SkeldarAnim/maya_hubglow.py`, numpy + stdlib,
  a payload row): the control's INK — luminance above its own face (the commonest inside its rect) by
  `lo` 25, fully by 95: letters, icons, a checked box, never the border or the hover fill — blurred
  `radius` 5 logical px (three box passes), × `gain` 2.2, taken off the ink itself, ADDED at `strength`
  0.42 in the colour of the ink around it (white text white, Delete's pink pink, the orange box orange).
  The orange primary button (dark letters on a lit face, no ink) gets a warm rim `#fff1e2` 0.38 inside
  its edge, 6 px deep, like a card. Cropped to the ink and blurred at half resolution at 150 %: 15 ms →
  2.6 ms for a wide control.
- **The fade** (`maya_hubmotion.GLOW_IN_MS` 110 ease-out / `GLOW_OUT_MS` 220 smoothstep, `glow_ms`),
  from where it stands; ⋮ → Interface animations off: at once.
- **`HoverGlow`** (`_glow_class()`), a `QGraphicsEffect` with `level`, `mode` ("ink"/"rim"), `rising`:
  coming up or lit it draws the control from Qt's source pixmap and the glow over it (computed once per
  picture, crc32 of the pixmap's bytes — a fade only changes the opacity); going dark it draws the control
  DIRECTLY with the lit picture's glow over it where the control stands now (trap 202). Dark, it is
  DISABLED, so Qt paints the control as if it had none (trap 204). A failure marks it `broken` (and
  `error`) and it draws the plain control for good.
- **`Glower`** (`Skin.glow`) is fed every Enter / Leave by the skin's application-wide watcher
  (`_hover_from` / `_left_from`), one 16 ms timer on the root ticks the fades. **It never keeps a widget**
  (trap 135): it holds its EFFECTS (Python-made: one whose control died answers `isValid` False and
  raises instead of crashing) and finds them again through `widget.graphicsEffect()` while the widget is
  in its own event; an effect stays on its control once made. `Skin.destroy` stops it.

Proof: `docs/superpowers/plans/verify_hub_glow.py` — **11/11 in a disposable GUI Maya** (port 7029,
scratch `MAYA_APP_DIR`, `MAYA_NO_HOME`) on the repo's hub floated to the animator's dock (viewport 510),
real `QEnterEvent`s sent to Maya's own widgets: every kind lights to level 1 with its glow computed; up in
126–154 ms, down in 223–247 ms, monotonic; light only round the control (outside its rect + reach: 0)
and, going dark after the control repainted itself, nothing darker than the plain control anywhere; the
primary's rim +85 at the edge, +0 in the middle; a heading, the search field, the status line, a card
header (its card lit instead) and a disabled button dark; a sweep across 14 controls with every cache
cleared p99 13–16 ms (the card light alone 10–12); 16 dark effects on the Characters card: its grab 15.0
ms against 15.3 with none; a hub rebuilt mid-fade glows again. Picture `hub_glow.png`. The hub's root is
made transparent for mouse events for the run (`deaf`): the animator's real cursor over that Maya
produced 65 foreign Enter/Leave events in one gate and moved the glow under it (a spy counts them, 0 in
the passing runs). `verify_hub_light.py` 6/6 again; `verify_hub_motion.py` fails its Weapons gate and
dies on the gone `uebridge` card — identically on the build BEFORE this work (a snapshot of `a618123`),
so history, not this. 4005 unit tests.

201. **PySide deletes a QGraphicsEffect whose Python wrapper is collected**, even after
     `widget.setGraphicsEffect(effect)`: a temporary `E()` left `graphicsEffect()` None after
     `gc.collect()` and its `draw` was never called (measured 2026-10-02) — which reads like "effects do
     not work on Maya's widgets". Hold every effect; when its widget dies, ours answers `isValid` False
     and a call raises `RuntimeError` (no crash).
202. **Text drawn from an effect's source pixmap loses ClearType** (the pixmap has alpha): 434 edge
     pixels of "Camera Setup" up to 52 levels apart. Inside one `draw` there is no way round it:
     `drawSource` after `sourcePixmap` draws that very cached pixmap, and `sourcePixmap` after
     `drawSource` broke the drawing in Maya (2800 pixels up to 145 dark — not reproducible offscreen,
     where every unit test passed). A font's `NoSubpixelAntialias` changed nothing in Maya's direct
     rendering. What works: draw from the pixmap only while lit, directly while going dark — Qt renders
     a control afresh once it repaints itself (the hover style coming off as the mouse leaves), so the
     switch lands with a change the eye already sees.
203. **`QGraphicsEffect.sourceBoundingRect()` is a QRectF**: a numpy slice built from it raised inside
     the effect, a catch-all made the glow silently do nothing (`computed` 0, `broken` True, every gate
     about the picture failing for "no light"). Keep the exception (`error`) where a verify can read it.
204. **An enabled QGraphicsEffect costs a Python call on every repaint of its widget**, at level 0
     too, and an effect stays on every control ever hovered — a sliding card repaints them all.
     `setEnabled(False)` when dark: Qt then paints the widget as if it had none.

## Armor: the Tech Limb's shield out of Atone, a card that equips it (2026-10-01)

The animator, with the Atone editor open: «достанем technolimb сам его fbx и добавим его ... в наши ассеты с
возможностью одеть ... не будем добавлять его в панель с оружием а сделаем для него отдельную панель Armor в
которой пока будет только техно лимб но позже мы добавим еще разные варианты одежды и брони ... не нужно делать
сетчатый инвентарь а просто будем выделять предмет нажимать кнопочку equip и он будет добавляться к нашему
персонажу в заранее указанное место». Asked: icon tiles. Spec
`docs/superpowers/specs/2026-10-01-armor-techlimb-design.md` — **read its addendum**: the first build shipped the
wrong mesh.

**What the Tech Limb is in Atone** (measured over Remote Execution, project `Atone`):
- Both techlimb items (`DA_Techlimb`, and the test roster's `DA_EquipmentItem_TechlimbTestStartingRoster`) equip
  on `lowerarm_l`. `UEquipmentComponent::AttachActorToSocket` snaps the actor (`SnapToTargetNotIncludingScale`)
  there, and no Manny mesh has a socket of that name: it is the bone.
- The production `BP_Techlimb` shows `SM_Shield_Test`, a static plate centred on the elbow, plus an energy shield.
  **That plate was the first build — wrong** («совсем не так как в игре ... в игре у нас есть скелет для щита»).
- **The shield the game animates is `SKM_Techlimb_Shield`**. Its source is
  `atone-art/Prototype/Meshes/Export/Techlimb_Shield.fbx`, 407 vertices, on `SK_Techlimb_Shield`: `Root`, `Main`
  under it (socket `EnergySieldSocked`), and 36 `joint_on_vertex_NNN` rim joints under `Main`.
- `BP_Techlimb_TestStartingRoster` puts it at identity on the actor root. `ABP_Shield` plays
  `AS_Techlimb_Shield_Block_In/Idle/Out_1P`: In opens the rim from `Main`'s centre, Out folds it back.
- **Those clips `force_root_lock` to the REF pose.** Their `Root` track holds a world position from the
  animator's scene, (17, 34, 138), and the game ignores it: `Root` stays on `lowerarm_l`, and only `Main` and the
  rim move.
- In Block Idle, `Main` is 21 cm down the forearm. The animator's `Animations/Rigs/Weapons/Shield_rig.ma` is the
  shield rig, and `TechnoLimb/New/LongSword_technoLimb_Block_1P_03.ma` constrains its `Root` onto `lowerarm_l`
  (0.000 at every sampled frame).

**The asset**:
- `export_techlimb_shield_from_unreal.py` (uelink) writes `sources/armor/`:
  - `SKM_Techlimb_Shield.fbx`;
  - `techlimb_shield_ue.json`: every bone's reference pose, local and component space; the Idle clip's locals;
    the game's Idle component pose, composed by Unreal itself with `Root` at its reference.
- `make_techlimb_shield_asset.py` builds `assets/Armor/Tech_Limb_Shield.ma` (175 KB):
  - a group `TechLimbShield` stands for `lowerarm_l`'s space;
  - each joint is posed by **Unreal's own reference→Idle motion**, `D = T_idle T_ref⁻¹`, mapped through N
    (Unreal `lowerarm_l` axes → Maya's, diag(1, −1, 1), measured over Manny's bind) and applied to where the
    import put that joint (G, the import's map, a signed permutation to 7e-7 cm);
  - the skinned mesh is bound where the import put it, not inheriting, so the skin alone moves it.
- On Manny: every joint where the game puts it, to 3e-14 in the asset and to 1.3e-4 cm against Unreal through the
  rig.
- The morning's plate scripts (`export_techlimb_from_unreal.py`, `make_techlimb_asset.py`) and
  `sources/armor/SM_Shield_Test.fbx` stay as the record. `assets/Armor/Tech_Limb.fbx` is gone.

**In the scene**:
- `maya_scenesetup/armor.py`. A piece hangs in an **armor space** (`<bone>_armorSpace`, marked `mayaArmorSpace`):
  a transform parent-constrained to the bone with no offset, in an `ArmorSpaces` group under the rig's group (at
  world level beside a bare skeleton). It is never in the skeleton, so the export stays bones only and a
  retarget moves it with the bone.
- `weaponspace`'s machinery is generic over its markers since then: `marked_space_of`, `ensure_marked_space`,
  `prune_marked`, `owner_for`, `bone_of`. The weapon API kept its names.
- **A skeletal piece is its `.ma`'s one group**, imported into a namespace of its own (`Tech_Limb`,
  `Tech_Limb1`, …; a namespaced root is never a bridge target), at identity in the space, marked `mayaArmor` /
  `mayaArmorSlot` / `mayaArmorNamespace`. Unequip deletes it and removes the namespace with what is left (skin,
  bind pose, its own material). A static piece (an FBX with one mesh) still works the plate's way.
- `slot_plan` (pure): an Equip takes off what its slot holds; the same piece again is replaced.
- The next free palette colour (the Colour card repaints a selected shield). What follows the import runs
  unrecorded (trap 115).
- A selected piece names its character (`skeleton.current_root` → `armor.bone_for`).
- **`maya_overrig.active.character_roots` leaves every ArmorSpaces group out** (`ARMOR_GROUP_MARKER`, pinned
  equal to `armor.GROUP_MARKER`). The shield's `Root` has no joint parent and would otherwise be one more
  character.

**The catalog**: `catalog.Armor(key, label, path, bone, slot, texture)` and `ARMOR`, one row: `Tech_Limb` →
`Armor/Tech_Limb_Shield.ma` on `lowerarm_l`, slot `left_forearm`. A future piece is a row, plus its icon
(`make_armor_icons.py` renders it from the posed, deformed mesh; a test pins one per row). Its model must already
stand at its place in its bone's axes.

**The Armor card**:
- `maya_scenesetup/armorpanel.py`, the Scene group's last card. Connections and Shared are each pinned right
  after their neighbour by their own tests.
- It holds the subtitle, the tiles, **Equip** (primary, `shield`) + **Unequip** (danger), and the line.
- The tiles are `maya_armorgrid.py` (Qt, a payload row), laid over `mayaSceneSetupArmorTiles` with the
  portraits' Keeper:
  - a click picks (`mayaSceneSetup_armor`);
  - a worn row carries a green «equipped» pill;
  - the right button offers Open scene;
  - no drag.
- Without Qt, a dropdown stands in.
- The pills follow the selection (a `SelectionChanged` job owned by the line).
- The hotkey row is `window.armor`.

**Proof**:
- `verify_armor.py` **15/15 standalone**, against Unreal:
  - on Manny, all 38 shield joints where the game's Block Idle puts them, to 1.3e-4 cm (the map re-derived from
    the rig's own bones);
  - the mesh following the joints only, to 2.5e-5 cm;
  - the Creep and the Orc D the same;
  - the shield's `Root` no character;
  - a second Equip replacing;
  - LongSword_Attack_Right_Heavy_3P retargeted: the shield on the bone to 4e-6 over 208 cm;
  - the export 93 joints, none of the shield's;
  - Unequip leaving no node and no namespace;
  - the others unmoved.
- A disposable GUI Maya (port 7031, a `git archive` of HEAD): the tile, Equip and Unequip pressed through Qt.
  Pictures: `docs/superpowers/plans/armor_card.png`, `armor_techlimb_on_manny.png`.
- 3438 unit tests.
- **Not built**: exporting the shield's own clip to Unreal (`Root` at its reference, `Main` + rim baked) — the
  next step («делай как лучше»).

152. **Atone's `SK_Mannequin_proto` and our Manny agree on every deforming bone and NOT on the helpers**:
     `weapon_r` 5.7 cm, `camera_root` 4.0, `weapon_l` 2.4, `camera_bone` 1.0 apart. A UE↔Maya axis fit over
     every shared bone read a 5.7 cm residual and looked like a wrong axis map. Fit over the deforming bones.
153. **A hub card's place can be pinned by ANOTHER feature's test**: `test_scenesetup_connections` pins
     Connections right after Weapons, `test_share` Shared right after Connections. A new card inserted between
     them fails both; the Scene group's end is free.
154. **A UE skeletal FBX's joints do not share one axis convention in Maya.** Unreal's bone frame → Maya joint
     frame was one matrix for `Root`/`Main` (they sit under the importer's −90 X wrapper) and another for the 36
     rim joints (each carrying a local 90° rotate). Posing joints "as Unreal's frames times a convention K"
     failed outright. What the skin sees is each joint's MOTION from its bind, so pose by Unreal's own
     `T_pose T_ref⁻¹` mapped into Maya and applied to the imported world matrix: no per-joint convention enters.
     And trap 51 again on the way: the importer LOCKS the skinned mesh's t/r/s, so its re-parent silently lost
     the wrapper's −90 X. Unlock it first.
155. **"Which mesh is the item" was asked before the meshes were understood.** The production BP showed a static
     plate; the animator knew the skeletal shield the game animates (a test BP, its clips, their own rig in
     `Rigs/Weapons`). Before asking which of several assets is "the thing", trace what plays in the game (the
     anim BP, the clips, root lock) and what the animators' own scenes use.

## The hub as a rail and one card (2026-10-16)

The animator: «адвай переосмыслим весь наш интерфейс и улучшим его. сейчас очень много где все
сливается! лоигческие разделы не отделены визуально». Three layouts were shown as mockups
(https://claude.ai/artifact/KYPDH1djZXZS3vXeKPA9jA): A group headers, B group tabs, C a rail and
one card. The animator picked **C**, a second card as a **popup**, and **a ⋮ switch back** to the
accordion. Spec `docs/superpowers/specs/2026-10-16-hub-rail-layout-design.md`, plan beside the
render script. **This changes the default skin**: what the hub-skin sections above say about the
header row, the jump strip and collapsing cards is now the accordion's (⋮ → Layout → Accordion).

- **`maya_hubqt.Skin(..., layout="rail")`**:
  - the root is a row: `self.rail` (`skeldarHubRail`, role `rail`, 32 logical px wide) and a column
    holding the message line and the scroll of cards. `self.header` is None;
  - the rail holds the SA mark, then the section icons (`add_jump(..., group=)`). Before the first
    icon of each new group stands a gap with a hairline (`skeldarHubRailGap_<group>`). The hotkeys
    switch, the edge pin and ⋮ sit at the bottom (`_build_head_buttons`, shared with the accordion's
    header);
  - `show_card(key, animate)` hides every frame but one. It marks the icon `skCurrent`
    (`card_active` with a 2 px bar of the group colour) and sets the scroll to 0. It fades the card
    in from `hubmotion.RAIL_SLIDE` (12) over `RAIL_SWITCH_MS` (160) through a
    `QGraphicsOpacityEffect`, which is removed at the end (`_stop_switch`);
  - a click on an icon calls `("jump", key)`. Ctrl held (`_modifiers`, a seam), a middle click
    (`_middle_class`) or the right button's «Open as popup» (`rail_actions`) call `("popup", key)`;
  - rail cards are built `collapsible=False`: no chevron, `toggle` and `set_collapsed(True)` do
    nothing;
  - ⋮ → Layout ▸ Rail / Accordion (`layout_actions`, `paint_layout`) calls `("layout", choice)`.
- **`maya_hub`**:
  - `layout()` reads `skeldarAnimHub_layout` ("rail" by default) and `set_layout(choice)` writes it
    and does a deferred `rebuild`;
  - `current()` / `remember_current` keep `skeldarAnimHub_current`, falling back to the first card
    for unset or stale, aliases read;
  - `_build_skin` passes the layout and the groups. On the rail it ignores the collapse memory and
    shows `current()`;
  - `focus` / `expand` on the rail are `_show_on_rail` (show, light, remember; nothing closed,
    no collapse remembered);
  - `_press_popup` is `maya_hubpop.open_at(key, cursor)`, falling back to the popout toggle.
- The edge panel builds the same skin and follows the layout. Classic look is untouched.

Proof:
- `tests/test_hubqt.Rail` (10) and `tests/test_hub.RailLayout` (6). The `Skinned` tests hold
  `layout = accordion`. 6798 unit tests OK;
- `docs/superpowers/plans/render_hub_rail.py` → `hub_rail.png`: the real rail and stub card bodies
  at 150 % in the 360 px dock. The rail is 48 physical px and the card viewport 477, where it was
  510.

**Not seen live.** The cards' own minimum widths against that 477 are not measured: Animation
Setup read 504 on 2026-10-01, before the compact skin. Nor are the fade, a middle click or the
popup in Maya. The animator's to try after Check update. Not built: the inner card rules from the
mockups (captioned sections, one orange button a card, segments vs tabs, a status plate).

## The card rules: switches, captions, labels, a toned message line (2026-10-16)

The animator, after the rail: «давай приступим теперь к дизайну». Shown as before/after mockups
(https://claude.ai/artifact/228rNcXckRzKZMcBUjV7Fd). Asked: the shared rules first, then the densest
three cards; **one orange button per SECTION** of a card. Spec
`docs/superpowers/specs/2026-10-16-hub-card-rules-design.md`.

**Shared (`maya_hubstyle`, `maya_hubqt`)**:
1. A `segments` track is recessed: `track` #17181a with a 1 px `track_edge`. The checked
   `segment` is a raised `thumb` #44474e with bold text. It used to be `line` grey, a button's
   outline colour.
2. `heading` is a section's caption: bold `muted` text at `{caption}` (8.5 logical px), padding
   above it and a `hover` hairline under it. `_apply_mark` upper-cases it and spaces the letters,
   which a Qt stylesheet cannot do.
3. A new role, `label`: a row's label left of a field or a switch, muted and not bold.
4. Every card's body opens with a hairline (`skeldarHubCardRule_<key>`) and 4 px under it. It
   shows and hides with the body.
5. The message line carries `skTone` from `hubstyle.tone(text)` (pure), shown as its left edge:
   - `ok`: the text starts with a done word, a green edge;
   - `wait`: «waiting» / «press Finish», orange;
   - `no`: refused / cannot / failed / nothing changed / not found / error, red;
   - plain otherwise, `line` grey.

   The writers are unchanged. When `tone` is unsure it says plain, never green.

**Cards**:
- **Connections** has three captions: «FK / IK», «Weapon in hands» and «Any object»
  (`CAPTION`, `_caption`). Every row label is a `label` (`_row_label`) and reads «Hand R».
  Apply all stands alone under the parent rows; BakeAcross and Release have their own row.
- **Animation Setup**: the skin captions «Character» and «Animation». It draws no Connect inset;
  the classic hub keeps it and its «Characters» / «Connect» titles.
- **Inventory**: `maya_invlook.panel` gains two `CAPTION_H` (18) bands, `cap_hands` and
  `cap_tiles`, painted «HANDS» / «WEAPONS» with a hairline. The hands start under the first band.
  The hand cards are named `HAND_CAPTION` («RIGHT» / «LEFT») in the caption style, the picked one
  in `accent_text`.

Proof: unit tests for `tone`, the sheet's rules, a heading's capitals and spacing, the card's rule,
the message tone, the inventory bands, the Connections and Animation Setup builders' marks;
6814 OK. `docs/superpowers/plans/render_card_rules.py` → `card_rules.png` draws a Connections-like
card of Qt stand-ins under the skin's marks and the real Inventory panel, at 150 %. **Not seen
live.** Next: the other cards, one by one.

## A section popup bursts out of a point and folds back into one (2026-10-17)

The animator: «Давай сделаем так что бы наши поапы появлялись с приятной анимацией сделай мекеты». Five
live variants (https://claude.ai/artifact/AQZc8xz9Bys9kXzXiFgZ2z); they chose **D, from the point**.
Spec `docs/superpowers/specs/2026-10-17-popup-burst-design.md`. **This replaces the 2026-10-09 fade and
rise of `maya_hubpop`'s open and close**; that fade remains only as the fallback when a burst cannot start.

- **The point**: a popup opens from the global point it was called from and closes into the point the
  close came from.
  - `open_at` passes the cursor (the radial menu, a Ctrl-click on the rail, the card's popout button);
    `open_popup(..., origin=)` and `close_popup(..., origin=)` take one.
  - `_defer_close` (the X) passes the cursor where it was pressed; None means the cursor.
  - The point is clamped `ORIGIN_PAD` (12 logical px) inside the card.
- **The timing**: `SkeldarAnim/maya_hubburst.py` (stdlib, pure, a payload row; `plan_open`, `plan_close`,
  `at(plan, ms)`, `rows`, `bands`).
  - **Opening**:
    - the card's rounded shape grows from a 28 x 20 box at the point to the card over `SHAPE_MS` 300
      (ease-out quint), its radius 10 to 8;
    - the face fades in over 60 ms;
    - each row starts `DELAY0` 40 + 22 ms per 60 logical px of distance from the point, nearest first;
      it fades in over 140 ms and scales 0.82 to 1 about its point-side over 240 ms (back ease 1.6).
  - **Closing**:
    - the rows fold the farthest first, 22 ms apart, 130 ms each, to 0 and 0.86;
    - the shape closes into the point over 200 ms (in-cubic), from 60 ms before the last row ends;
    - the face fades out over its last 80 ms.
  - Rows are the title and the section's content split until no piece is taller than 64 logical px
    (visible children, depth 8, clipped to the scroll viewport). Past 48 rows they are merged into
    bands.
- **The drawing**: `PopupBurst`, a `QGraphicsEffect` on the popup's frame (`_burst_class`), held by the
  popup (trap 201) and DISABLED at rest (trap 204).
  - It takes the frame's picture once a burst (`sourcePixmap`; the text is grayscale-antialiased only
    while it stands in, trap 202). Each tick it draws:
    - the picture;
    - each row's place filled with the card's face (`card` toward `card_active` by the light's level);
    - each row's piece at its opacity and scale;
    - all of it masked by the antialiased rounded shape (`DestinationIn`), at the face's opacity.
  - The plan is made at the first draw, when the window is laid out. Maya's controls are never touched.
  - A drawing that raises marks it `broken` (`error` kept) and draws the frame plain to the end.
- **While it moves**:
  - the window takes no mouse;
  - the card light waits (`_on_hover` returns), and is set from where the cursor is when the burst ends
    (`_under`);
  - a `QVariantAnimation` over `MAX_MS` drives it and stops at the plan's total;
  - a fold ends by hiding the window, then the old close path deletes it.
  - `open_at` still destroys a standing copy of the section at once: two copies must not overlap.
  - ⋮ -> Interface animations off: at once, no effect made.

Proof: `tests/test_hubburst.py` (the origin's clamp, the open and close schedules, rows and bands, a
subprocess check that it imports no Maya or Qt) and `tests/test_hubpop.Burst` (8: the frame plain and
the mouse back after an open; a small shape at the point and a far pixel transparent mid-way; the close
leaving the list and destroying the window; a failing drawing; animations off; the light waiting;
`open_at`'s and the X's points). 7040 unit tests OK. `docs/superpowers/plans/render_popup_burst.py` ->
`popup_burst.png`, a filmstrip of both on the test seams. **Not seen in a GUI Maya.**

## Characters > Delete: a character out of the scene, whole (2026-10-01)

The animator: «Давай в разделе character сделаем кнопку удаления. Суть такая - я выделяю любую часть
персонажа рига или скелета не важно какую нажимаю эту кнопку и у меня удаляется из сцены все что связано с
этим персонажем. Также если я выделил несколько разных персонажей кнопка должна удалить все их части».
Asked: **a confirm dialog first**. Spec `docs/superpowers/specs/2026-10-01-delete-character-design.md`.
Module `SkeldarAnim/maya_scenesetup/deletion.py`; the Characters card's **Delete** (danger, trash) stands in
Add Character's row (`window.delete_characters`).

**Which characters**: every one a selected node belongs to — under one of its PARTS or in its namespace
(`deletion.owners`, pure). A rig's parts are every top-level node of its namespace (measured: besides
`Group` and the game skeleton, `Manny_Rig:SKM_Manny_Simple` and `Manny_Rig:materialXStack1`); a
root-namespace rig's, its group and skeleton. A skeleton's are its root. Both get the meshes skinned to
their joints, the weapon/armor spaces at world level following their bones, our weapons and cameras that
DRIVE their bones (a weapon on the floor, a camera on `camera_root`) and the CoM group linked to the root.
Parts are raised over plain transforms they empty (the Creep's `Armature`, `SKM_Manny_Simple`). So a
control, a bone, a mesh, a weapon in the hand or on the floor, an armor piece, the CoM handle, the camera
and the `Armature` all name the character; a shared `WeaponSpaces` group names nobody. Nothing selected,
or nothing of a character's, is refused: a destructive button never falls back to "the only one".

**What goes** (`plan`, read-only, then `execute` in one undo chunk):
- the CORE: the parts raised over the union (an emptied `WeaponSpaces` goes), everything below them, the
  rig's namespace whole, a skeleton's namespace when it holds nothing else (a clip imported as its own
  skeleton), a skeletal armor piece's namespace;
- the DG GARBAGE: components of the connection graph outside the core with the scene's HUBS cut out
  (`HUB_TYPES`, default, locked and referenced nodes); one goes when it holds no DAG node and touches the
  core — materials worn only by it, skinClusters, bind poses, curves, layers and sets of only its members,
  our palette recolours. A component holding any DAG node stays whole, so an unknown hub can only make
  it KEEP, never delete another's node. Measured before: a plain delete of the DAG left 292 nodes after
  Manny's skeleton, 28 after the Creep's, 9 after the UE4 Mannequin;
- what the Add RECORDED: `character._after_import` writes, for a skeleton (a rig has its namespace), a
  `network` node `<root>_skeldarImport` fed by `root.message` (`skeldarImportNodes`: the import's UUIDs,
  hubs left out; `skeldarImportLabel`: the catalog row), and `attach.import_weapon` puts
  `skeldarImportNodes` on the weapon itself. Needed because Manny's skeleton asset carries the dead half of
  an AS rig (275 DG nodes, `AllSet`, `BodyControls`), a `camera1` and a `materialXStack1`, and the palette
  unassigns an FBX's own materials (the UE4 Mannequin's, every weapon's): connected to nothing of the
  character. A recorded DAG node with nothing foreign below it joins the core; a component touching
  nothing goes only when every node in it was recorded. A skeleton added before this has no record:
  its recorded-only junk stays;
- on the way, inside the chunk: an object of somebody else's riding a proxy inside it (BakeAcross) is
  released (`connections.release_across`); a rig left standing whose MoCap holder's source goes is
  disconnected (`maya_rig_retarget.disconnect`, the take not baked — the confirm says so); the CoM engine
  forgets the groups; the core's locked nodes are unlocked; then the DAG tops, the DG left, the emptied
  namespaces (deepest first), the orphaned hand proxies.

The confirm names the characters and what of theirs goes («Manny_Rig1 (rig) - 1 weapon, 1 armor piece,
camera, centre of mass»), the rig to be disconnected, and the animator's objects constrained to them;
batch skips it. A skeleton reads «Creep [skeleton] (root)» (its record's label), «root1 (skeleton)»
without one. A referenced character is refused by name.

Proof: `docs/superpowers/plans/verify_delete_character.py` — **82/82 in mayapy standalone**:
- every catalog row added alone and deleted through a part of it (a rig control, a mesh): the scene's
  UUIDs exactly what they were but Maya's singleton copies (trap 121/122), the namespace gone, Ctrl+Z
  bringing every node back, redo taking them again — 2699 / 2616 / 2628 nodes for the rigs in ~2 s, 410 /
  139 / 83 for the skeletons in 0.1–0.2 s;
- a full kit, three characters in one press (a rig with sword, Tech Limb, camera, CoM, keys, a palette
  recolour, a layer of its controls; a Manny skeleton with a dagger in hand, a spear on the floor, a camera
  and a CoM; a clip skeleton rig B was retargeted from): 18 parts each naming their character, the confirm
  saying all of it, 4389 nodes gone in 3 s, every node that stood before still standing, nothing of the
  three left but the cubes' own new nodes, rig B disconnected, the Creep (whose sword shares the world
  `WeaponSpaces` group) untouched, the BakeAcross rider baked, shown and keyed, Ctrl+Z all back;
- refusals, Cancel, and a mixed selection deleting the character and keeping the cube.
And in a disposable GUI Maya (port 7041, scratch `MAYA_APP_DIR`, `MAYA_NO_HOME`, killed after): the
hub's Delete clicked through Qt with a rig control and a Creep mesh selected, Maya's real confirm read and
answered by clicking its Delete (`delete_character_confirm.png`, the card `delete_character_card.png`),
both gone, the line «Deleted Manny_Rig (rig), ... - 2849 nodes», one Ctrl+Z bringing both back. 3473 unit
tests. Not built: a hotkey row.

**…and the animation layers it was in** (2026-10-16, «кнопочка удаления ... должна удалять и слои в
которых находился персонаж (только если там нет объектов которые не относятся к удаляемому)»).
`animLayer` is a HUB type, so until then a layer of only the rig's controls stayed behind, empty.
`deletion.doomed_layers` (pure): a layer goes when it held something that goes (a member plug's node
or a blend node in core ∪ doomed) or a child layer of it goes, holds nothing that stays, and every
child of it goes; a layer that never held the character and every root stay. `emptied_roots`: a root
left with no child goes too (Maya's editor does that with BaseAnimation), never Scene Tabs'
`skeldarTabsLayerRoot` / `AnimLayerRoot` (trap 248). `Plan.layers` (UUIDs), deleted children first
(a locked layer unlocked), named in the confirm and the line. Proof `verify_delete_layers.py` 14/14
standalone (only-rig, locked, parent + child go; shared with a cube or another rig, an empty one stay;
the cube still plays its layer; Ctrl+Z / redo; an emptied BaseAnimation goes and comes back);
`verify_delete_character.py` 82/82; 6722 unit tests.

156. **`lightLinker1` is not a default node, and it links every shading group of the scene.**
     `ls -defaultNodes` leaves it out; a connection-graph walk around one character's material reached
     every other character's shading groups through it and, from those, their meshes — so "delete what
     only this character uses" found nothing (the same with the IK solvers, which every ikHandle meets,
     and `renderPartition`). Cut the scene's registries out by TYPE before walking.
157. **Maya deletes a constraint whose last target is deleted**, and the constrained object keeps the pose
     it stood in. A cube parent-constrained to a character's hand lost its constraint with the character
     and stood still (measured to the matrix): there is no "constraint left without a target" to clean up.
158. **The first import into an empty scene makes the scene's own managers INSIDE its namespace**
     (`Manny_Rig:shapeEditorManager`, `Manny_Rig:poseInterpolatorManager`), Maya will not delete them, and
     they keep the namespace alive after everything else in it is gone. `namespace -removeNamespace
     -mergeNamespaceWithRoot` moves them out and removes it. And mayaUsd's LOCKED `UsdDefaultSettings`
     copies an asset carries into a rig's namespace make `-deleteNamespaceContent` fail outright
     («is locked, can not remove it»): unlock first.

## Four tasks in one day: sources, retargets, groups, labels (2026-10-02)

The animator, leaving for two hours: «Выдам тебе большое задание которое тебе нужно сделать самостоятельно
от начала и до конца ... пушить и делать сборку не нужно пока я не проверю». Four tasks:
1. separate the connection block in Animation Setup, and connect to Unity and plain folders as well as
   Unreal, reading as many formats as possible;
2. two retargets (rotations only / squash & stretch), chosen automatically and asked when proportions
   would break, for every common skeleton convention found on the internet;
3. every part of a character in one outliner group, and one display layer per character;
4. the animation's name under each character after a group import or a drag.

Built as FIVE parallel branches (task 2 split: the conventions, the two versions), each in its own git
worktree from `3606438`, each reviewed independently and fixed, then merged here by hand. The five sections
below are the branches' own records. **Nothing was pushed, no build was made, the installed copy and the
animator's Maya (port 7001) were not touched.**

**What the merge itself decided** (the branches could not see each other):
- **A label stands in its character's outliner group** (`cliplabel.home_for(kind, group, character)`: the
  character group first, for rigs and skeletons alike, so the character's layer hides its label too; a
  legacy character keeps the labels branch's homes). `deletion` takes both the group and the label.
- **A foreign convention honours the stretch onto a skeleton too**: `skeletonimport.transfer_foreign(...,
  mode)` adds a point constraint on every paired bone in `stretch` (the source already scaled to our size
  by its wrapper); the conventions branch drove orientations only.
- **The conventions branch's unit-size stand-ins (`_unit_sources`) run only when the stretch does not
  scale the clip itself** (`plan.scaled`), so no drive is scaled twice.
- **The bridge press onto a rig**: the clip is imported (with the sources branch's rollback of a failed
  file import - namespaces and an added rig taken back, the scene time restored) BEFORE the question
  (the stretch branch's order), and a rig that stood is reset only after the answer.

Proof on the MERGED tree, every one standalone (mayapy, scratch `MAYA_APP_DIR` each, nine at once):
- `verify_import_sources.py` **27/27** (gates 50-53 re-run after the verify learnt that a rig's bones stand
  in its character group - trap 185 again);
- `verify_skeleton_conventions.py` **122/122**; `verify_retarget_modes.py` **40/40** (phases a-h);
- `verify_character_groups.py` **146/146**; `verify_clip_labels.py` **17/17** (gates 1, 4, 9 now ask for
  the character group, the merge's home for a label);
- `verify_rig_pipeline.py` **30/30**, `verify_many_rigs.py` **32/32**, `verify_delete_character.py`
  **82/82**, `verify_weapon_space.py` **11/11**;
- **3796 unit tests**, OK.

**Seen on the merged tree in a disposable GUI Maya** (port 7071, scratch `MAYA_APP_DIR`, killed after):
the Animation Setup card with the Connect inset (content 504 within the dock's 510 viewport) and the
Retarget card's `[Auto | Rotations | Stretch]`; three UE clips as a square onto new Manny rigs - the scene's
top level exactly `Manny_Rig_Character`, `Manny_Rig1_Character`, `Manny_Rig2_Character`, a layer each, each
`<ns>:clipLabel` inside its group naming its clip, the Auto version «stretch - twin, exact»
(`merged_animation_setup.png`, `merged_retarget_card.png`, `merged_outliner.png`, `merged_square_labels.jpg`).
**Not proven there**: the stretch question dialog on screen (every proof answers it through
`maya_retargetmode.set_asker`; a modal blocks the port) and a real mouse drag. Unity is read off the disk
only (no live editor link). No real Max / Blender / Unity / BVH file exists on this machine: those
conventions are proven on synthetic skeletons and on files the verifies wrote.

## Connect: Unreal, Unity, a folder - and every format we can read (2026-10-02)

The animator, away for two hours: «Во вкладке Animation setup раздел с подключением к unreal engine
нужно визуально как-то отделить. Далее я бы хотел что бы у нас была возможность подключаться не только к
анриал енжину а и к Unity, и просто к папке с FBX файлами.......хорошо бы было сделать максимальный
обхват форматов которые мы можем прочитать и вытащить из них анимацию.» Every choice was taken alone;
spec `docs/superpowers/specs/2026-10-02-connect-sources-and-formats-design.md`.

**The block**: the connection rows are one column set into the Animation Setup card, `ueAnimBridgeInset`,
hub role **`inset`** (tokens `inset` / `inset_line`; `maya_hubqt` sets `WA_StyledBackground` - a plain
QWidget paints no stylesheet background - and pads it 8 px; the classic hub a `backgroundColor`). Top
down: the heading **Connect** (was «UE Connect»), **[Unreal | Unity | Folder]** (`ueAnimBridgeSource_*`,
remembered in `ueAnimBridgeSourceKind`), the source's line, the dropdown + Refresh, search, the list, the
Import target, the timeline box, Import Animation, the two exports. The card's status line stays outside.

- **Unreal** as before. **Unity**: Unity Hub's projects (`%APPDATA%/UnityHub/projects-v1.json`, one per
  folder - it lists one twice by drive-letter case; «open» = `Library/EditorInstance.json`'s pid alive),
  then browsed ones, then **Browse...**; Refresh scans `Assets`: a model's `.meta` `clipAnimations`
  (name, takeName, firstFrame, lastFrame) one row each, else one per take; `.anim` one row, Humanoid /
  compressed listed and marked. **Folder**: remembered folders (`ueAnimBridgeRecent_folder`) and
  Browse...; Refresh scans recursively, skipping `Library`/`Temp`/`.git`. Scans run under a cancellable
  progress window and are cached in the temp folder per source and place (`sources.cache_name`).
- **One funnel**: `records.AnimRecord` gained `source, path, clip, fmt` (defaults = Unreal). Every road
  calls `window._export_from_editor`; a file record answers a **clip reference** (`C:/a/p.fbx|take=2`,
  `x.glb|anim=0`, `Bow.fbx|first=0&last=5&take_name=Take+001`), and `rigimport.import_source` sends a
  plain FBX to `animimport.import_clip` as always, anything else to `formats.import_clip`, which leaves the
  same shape (a namespaced keyed skeleton + info). Retarget, skeleton transfer, the square of several and
  the drag needed nothing. Export to uasset is Unreal's only; a row that cannot import refuses on press.
- **Formats** (`maya_uebridge/formats.py`, readers `bvh.py`, `gltf.py`, `unityfiles.py`, scan rules
  `sources.py` - the last four stdlib): FBX takes (`FBXRead` + `FBXGetTakeName i`, positional; `FBXImport
  -t i`), Collada and FBX through the FBX plugin, `.ma/.mb` imported with script nodes not run and
  deleted, USD by `mayaUSDImport(readAnimData=True)`, BVH / glTF / Unity `.anim` by our parsers and one
  builder (`formats.build`: `MFnAnimCurve.addKeys`, times in SECONDS, the scene's rate untouched and a
  difference said). BVH's listed `Z X Y` is Maya's `yxz`; glTF rest TRS is the jointOrient, metres x100;
  Unity is left-handed (`(-x, y, z)`, quaternion `(x, -y, -z, w)`) and a generic clip lands on the model
  beside it (never above `Assets`) found by its bones' names in the file's bytes.

- **Refused before the press** (the fix review): `formats.check(ref)` reads the file again for what
  its import would refuse - a take not in it (or the default take would come in silently), a Unity clip
  with no model and no positions, a glTF with no skeleton - and `window._export_from_editor` raises it,
  so no road adds a rig first; what still fails inside an import is taken back
  (`rigimport._undo_failed_import`: the clip's namespaces, the rig the press added). A file with one
  moving take among several names its take. A whole-saved `.ma`'s locked `UsdDefaultSettings` is
  unlocked and deleted (`formats.tidy_scene_import`). A Unity model comes in with NO take of its own
  (`formats.import_model_rest`). Every file of the animator's is read from a COPY in the bridge's temp
  folder (`sources.staged`): the plugin writes `<file>.fbm` beside what it reads.

Proof: `docs/superpowers/plans/verify_import_sources.py` **27/27 standalone** - a UE 3P clip written as
a two-take FBX, DAE, USD, `.ma`, BVH, GLB and two `.anim`, read back through the real funnel against
every joint's world matrix with a frame-off control (34-175 cm): FBX takes 0.000000 cm, USD 0.000018,
`.ma` 0.000000 (its script node never ran), BVH 0.000090, glTF 0.000033, Unity 0.000000, DAE 0.000527 at
its own key times; the real `TwoHandGunFireStanding.anim` against Maya's own import of the model clip
it is Unity's copy of - 36 of 37 bones within 0.6° / 0.05 cm on all 40 frames, the 37th a constant
20.000° at every key (an edit on the copy), and only the X mirror landing (the others 0 of the bones where
they differ); refusals before the press (no rig added) and after it (the added rig removed, 3.8 s); a
whole-saved `.ma` retargeted with its namespace gone; no `.fbm` beside a source file; the Lugal project listed (1975 rows, 4-5 s); a BVH onto a new Manny rig,
a GLB onto a new Manny UE5 skeleton, an FBX take + DAE + USD at once in a 2 x 2 square, every clip
namespace gone. A disposable GUI Maya (port 7061): the card at the dock's 510 px viewport, content 504 /
431, the Lugal project scanned in 3.9 s, a BVH imported from the folder onto a new rig in 4.8 s; pictures
`connect_block_unreal.png`, `connect_block_unity.png`, `connect_block_folder.png`. 3564 unit tests.

159. **`FBXImport -f file -t i` looks the take index up in the file the plugin READ LAST**, not in
     `file`. After a scan had `FBXRead` other files, `-t 2` answered «FBXImport error: take not found»
     on a file that has three takes. Read the file again (`FBXRead -f`) right before a take import. And
     `FBXGetTakeName` takes the index positionally: `FBXGetTakeName -n 1` is «Use syntax».
160. **Maya's Collada writer resamples onto 24 fps whatever the scene's rate**: a 30 fps clip came
     back with keys 1.25 frames apart, exact at its own key times (0.0005 cm) and up to 165 cm off
     between them (an euler flip a resample put between two keys). A DAE from Maya is lossy; judge a
     reader of it at the file's own key times.
161. **A verify's `write_glb` returned its loop variable**: `for key, path, kind in ...` inside a
     function whose argument is `path` wrote the file as `./rotation` and returned "rotation" - the
     verify then found no GLB. Never reuse an argument's name as a loop variable.
162. **A model search that climbs folders left the sandbox**: a clip "alone" in `%TEMP%/.../alone`
     climbed into `%TEMP%` and took another tool's `skeldar_inventory_export.fbx` as its model (it named
     the bones). A search for a sibling file stops at the project's `Assets`, and outside a project looks
     in its own folder only.
163. **The scratchpad is shared between parallel agents**: another agent's `probe1.py` replaced this
     one's between two runs, and another's commit message replaced a `msg1.txt`. Each agent works in a
     folder of its own inside it, its files named for it.
164. **A whole-saved `.ma` carries mayaUsd's `UsdDefaultSettings`, and it imports LOCKED into the
     clip's namespace**: `namespace -rm -deleteNamespaceContent` then raises «is locked, can not remove
     it» and the clip's whole scene stays behind (measured 2026-10-02, trap 158's family from the import
     side). Unlock what an import of a scene brought, and delete its furniture, before the namespace goes.
165. **`FBXResetImport` turns every `FBXProperty` back to its default**, so an option set before a
     helper that resets (`animimport.import_clip` does) is lost silently: the model under a Unity clip
     kept importing its 333-curve take with `Import|IncludeGrp|Animation` set false just before. Set it
     AFTER the reset, and put it back in a finally - it is session-wide.
166. **`FBXImport` extracts a file's embedded media into `<file>.fbm` beside the file** (a folder in a
     Unity project's Assets, which Unity then imports); `FBXRead` does not. Read a file you do not own from
     a copy.
167. **A gate that writes its own input with the inverse of the conversion it tests cannot fail**, and
     a mirror control that counts every bone cannot either: a bone turning about its local Z alone reads
     the same under Unity's X and Y mirrors (41 % "landed" for the wrong one). Prove a conversion against
     the other program's own output (Unity's copy of a model clip against Maya's import of that take),
     and count a control only where the candidates differ.

## Every common source convention onto our rigs and skeletons (2026-10-02)

The animator: «прошелся по интернету нашел самые часто используемые иерархии костей для Unity,
Mixamo, blender, motionbuilder, 3dmax Unrealengine и сделал ретаргеты для этих систем на наши
риги и скелеты» (one of four tasks left for two hours, «сделать самостоятельно»). Spec:
`docs/superpowers/specs/2026-10-02-skeleton-conventions-design.md` - its table lists every
convention with its quirks and the sources read.

**`SkeldarAnim/maya_skeletonmap.py`** (stdlib, pure; a payload row): `recognize(paths,
positions)` answers {our UE5 name: source path} for Unreal, Mixamo, MotionBuilder HumanIK
(`Character1_`), Unity Mecanim, VRM (`J_Bip_`), Blender Rigify (`DEF-`) and Auto-Rig Pro
(`.x`), 3ds Max Biped (`Bip001`), Character Creator (`CC_Base_`), Daz Genesis, CMU BVH, Xsens
and Synty. Names first (namespaces, prefixes, camel case, the side anywhere: `Left`, `l`,
`_l`, `.L`, `_L_`), then the CHAIN: the hips where both legs and the spine meet (Biped hangs
its thighs off `Spine`, CC splits `Hip` into `Pelvis` and `Waist`), an arm the path from the
spine to a hand - so `Shoulder` is a clavicle in HumanIK and an upper arm in Synty by where it
stands - the spine and neck distributed onto ours with both ends kept (`distribute`, Mixamo's
3-onto-5 rule). Twist, roll, end, nub, IK, weapon and camera bones are never mapped. A root
counts only at the floor (Biped's `Bip001` is the centre of mass: Main takes the hips' travel).
Names failing, positions give a STRUCTURAL pass (lowest leaves the feet, the top the head,
furthest leaves sideways the hands). It refuses by name: «generic: no Hips/pelvis found - not a
humanoid this retarget knows». The rest pose is CHOSEN (`choose_rest`: the candidate - rotates
at 0, the first frame, the bind - whose bones point most like the rig's, each in its own body
frame); it sets only the roll, never where a bone points.

**Wired in without touching UE5 or Mixamo**: `maya_asretarget` / `maya_pmretarget` keep their
schemas; a source neither (or one only SCORING as Mixamo - CMU, Unity - or as UE5 by one shared
name - ARP's `hand_r`, Daz's `pelvis`) becomes a `GenericSchema` re-keyed into UE names, never
a twin, its rest chosen, beyond 2 % of our size driven through unregistered stand-ins
(`_unit_sources`). If the map refuses a source that DID score (an arms-only UE clip), the old
road runs. `skeletonimport.transfer`: a clip without the UE limbs by name goes to
`transfer_foreign` - both skeletons read, paired through our names (chains distributed chain
onto chain), each bone oriented through a rest-aligned offset, the pelvis placed, the root on
the hips' ground travel (`ground_axis`: the Creep's root is under a -90 X Null), the source
scaled for the bake; a map refusal with leaf pairs falls back to the leaf road. `Sweep
Fall.fbx` now goes onto our skeletons too.

**The size, without the pose** (`size_ratio`): the pelvis over the floor in the first
candidate rest that STANDS on it (`stands`: legs straight and down an upright body, the ankles
near its floor), else the leg lengths - never the pelvis of a crouched first frame. Over the
FLOOR, not the ankles: Mixamo's hips stand 5 cm over its thighs, Manny's 2, and the ankle
reading put Sweep Fall 4.4 % off. **Scaled about the floor under the root's first frame**
(`scale_pivot`), so a drop, a kept place and the square (read off the unscaled first frame)
hold; the square reads each clip's travel at its baked size (`travel_scale`). **A root that
never moves while the hips travel** (HumanIK's Reference, CC's BoneRoot) is no root
(`drop_static_root`).

Proof: `verify_skeleton_conventions.py` **122/122 in mayapy standalone** - 13 synthetic
conventions (each with its own joint axes, rest in jointOrient or in rotate, metres / BVH units,
a Z-up Biped wrapper) plus Sweep Fall onto Manny_Rig, Creep_Rig, Orc_D_Rig (the Retarget
button) and Manny UE5 / Creep skeletons: every mapped bone POINTS where the source's does -
**0.0078 deg** Manny_Rig (0.16 at its neck in-between), **0.0002** Creep/Orc D, **0.0005** the
skeletons - lengths unchanged (0.000000 cm; Manny's left leg its own 0.05 cm wander), travel
scaled exactly (x100.94 metres, x2.2432 CMU, 0.0000 cm), refusals, the rest forced either way
(directions 0.0000 / 0.0000, frames 95.8 deg apart), controls 70-149 deg; and, after an
independent review, four variants (15 % longer legs x0.8888, a crouched first frame x1.041 by
the legs and x1 on its bindPose, a static HumanIK Reference) with the expected size DERIVED
from the fixture's constants, the UE4 Mannequin as a target, an arms-only UE clip on both
roads, a CMU clip 20 cm off its origin dropped on a point (Main / root 0.0000 cm off; scaled
about its origin, the control, 25.02 cm) and two in a square (250.00 cm apart; 219.79 at the
keyed size). `verify_rig_pipeline.py` 30/30, `verify_many_rigs.py` 32/32,
`verify_creep_rig_asset.py` 16/16 on the branch. 3576 unit tests. No real Max/Blender/Unity/
BVH file exists here: synthetic only.

168. **Maya has no `.` or `-` in a node name: an FBX import writes Rigify's `DEF-spine.003` as
     `DEF_spine_003` and ARP's `root.x` as `root_x`.** A reader written for the source file's
     spelling missed the scene's: Rigify's numbered spine read as six spine joints and no head,
     and the structural fallback took over with 21 bones. Read both spellings.
169. **One shared bone name made a foreign skeleton score as Unreal.** `detect_schema` takes
     any hint: ARP's `hand_r`, Daz's `pelvis` -> the UE5 TWIN schema -> fingers 170 deg off and
     70 cm of travel lost. Unreal is the UE limbs BY NAME (`covers_ue_core`).
170. **…and not the head: a first-person UE clip carries none.** The first guard required it
     and sent `LongSword_Attack_Right_Heavy_1P` (90 joints) down the generic road, which refused
     it - `verify_rig_pipeline.py` 13 of 30 failed until the head left `UE_LIMBS`.
171. **A skeleton can stand off its own bind** (Manny's, 0.07 cm at the left calf): directions
     read off the `.bindPose` matrices came out 0.0989 deg wrong at EVERY frame. Read where a
     bone points from where its children stand, in the bind frame.
172. **A hand aimed past a mapped metacarpal at the middle finger depends on the metacarpal's
     own turn**: 3.3 deg on Rigify/Daz sources. With metacarpals both sides, aim at the
     metacarpal.
173. **A rig carrying the last take reads as another size.** The verify read the rig road's
     size with `_plan` before the button's `reset_build_pose` and got x100 for x100.94, x2.222
     for x2.243: `rest_matrices(..., "live")` read the game skeleton in the previous clip's pose.
     Every press resets first; anything that asks the plan must too.
174. **"Where is the pelvis" is a pose question.** The first build sized a source by its pelvis
     height in the chosen rest - a crouched first frame read it 20-60 % low. And the pelvis over
     the ANKLES is a convention question: Mixamo's hips stand 5 cm over its thighs, Manny's 2,
     4.4 % apart on the same height. Size by the pelvis over the floor in a pose that STANDS,
     else by the leg bones.
175. **A scale about the origin moves a clip that does not start there.** Drops and kept places
     read the unscaled first frame; a CMU clip x2.24 starting 20 cm out landed 25.02 cm off the
     cursor. Scale about the floor under the first frame.

## Two retargets: rotations, or squash & stretch - and which one runs (2026-10-02)

The animator: «у нас должно быть две версии ретаргета в первой где мы делаем ретаргет но
гарантируем что кости не растягиваются ... Вторая версия где у нас учитывается растяжение костей.
Наш скрипт должен определить какую ретаргет систему стоит использовать и если перенос анимации на
риг или скелет будет ломать пропорции то необходимо спросить у пользователя согласен ли он на сквош
и стрейч костей.» Away for two hours: every choice taken alone, in the spec
`docs/superpowers/specs/2026-10-02-retarget-stretch-design.md`.

**`SkeldarAnim/maya_retargetmode.py`** (stdlib at import, a payload row; its scene wrappers import
`cmds` inside) holds the measurement, the rule, the question and the scaled followers; the retarget
modules build their own drives.

- **ROTATIONS**: every bone turns as the clip's and keeps the target's length; root and pelvis
  placed; on a rotation-marked rig (the Creep, the Orc D) the IK ends and poles follow the rig's
  own FK, on any other (Manny) they stay on the clip's hands and feet - the legacy plan with no FK
  position (`drive_plan(keep_lengths=True)`): an AS IK limb has `stretchy` 0 on every shipped rig,
  it bends and never stretches. **STRETCH**: every bone on the clip's joint,
  the clip taken at OUR size (`s` = our legs over the clip's; a clip's rest is never visible, its
  legs are) - the target's lengths become the clip's, its animated stretch included. **The twin's
  stretch IS the old twin path**, unchanged to **0.0 cm** (a Manny retargeted with the new press
  against one with the legacy call, every bone, every frame).
- **The setting** `skeldarRetargetBones` = auto (default) | rotation | stretch, as `[Auto | Rotations
  | Stretch]` segments in the **Retarget card** (only there: one setting for every press, and the
  Animation Setup import rows were another session's that day). **Auto**: a twin (median paired
  bone ≤ 1 %) - stretch, exact, never asked; the same proportions at another size (the scaled
  median ≤ 1 %) - stretch; anything else - one `confirmDialog` («Heavy onto Creep_Rig: ... Squash &
  stretch would change Creep_Rig's proportions: arms -17 %, spine +1 %, fingers -30 %.» - and «a
  limb in IK keeps its own lengths, its end following the FK»; **Keep proportions** (default) /
  **Squash & stretch** / **Cancel**); batch mode: rotations, said so. The status line always names
  the version and why, and a stretch's names the limbs in IK («SQUASH & STRETCH - leg_l, leg_r in
  IK keep their own lengths ...»). `set_asker` installs an answerer (the verify).
- **Lengths by the retarget's own map**: each paired bone against its nearest PAIRED ancestor (a
  3-joint Mixamo spine against our 5 compares chord with chord); root, pelvis and the helpers are
  not lengths; regions by our bone's name. Ours from the skinCluster's `bindPreMatrix` (trap 176),
  the clip's at its first frame.
- **Scaled followers**: under the holder, a space riding the clip root's PARENT rigidly (the
  bridge's wrapper is moved onto the rig's place after the connect: the move rides 1:1), a follow
  point+orient-constrained to the joint, its channels connected into a node under a group scaled s
  **about the clip root's first-frame floor point** (`scalePivot`, trap 180), a child cancelling
  the body's whole world scale - at the joint times s, turned as it, scale 1. Transforms and
  connections only.
- `maya_asretarget.connect(bones=None|"rotation"|"stretch")` (None the legacy rule every older
  caller keeps): stretch onto another body is `drive_plan(scaled=True)` - the rotation plan whose FK
  controls (and Main, RootX_M) take position from the followers with the twin path's own offsets.
  **The Creep's and the Orc D's game bones follow AS by orientation only** (trap 177): a stretch
  press gives each such bone a point constraint from its AS joint (marked `skeldarStretchFollow`, no
  offset - the joint stands on the bone, its own translate kept on it as `skeldarStretchRest`), a
  rotations press takes them away and writes that translate back (trap 58's mechanism). The holder
  remembers the version (`connected_mode`); the helper bones carry in world space only for the
  twin. `maya_pmretarget.connect(bones=)`: stretch puts every FK control on the clip's joint in the
  frame Main and the pelvis ride - pm's own scaled group, plus the pelvis's rest offset - so the body
  is the clip's shape about its pelvis whatever moves the clip after the connect.
- **Every press decides before anything changes**: the Retarget button before the reset; the
  bridge onto a rig imports the clip FIRST, asks, then resets (Cancel removes the clip; an added rig
  is deleted again); onto a skeleton (`onto_skeleton` / `onto_existing(decide=)`; Cancel deletes the
  added skeleton and the clip); a batch (`lineimport._Versions`) measures every clip against the
  first target it adds and asks ONCE, the worst named, by UUID (trap 178). «cancelled - nothing
  changed» - and it is: every Cancel after an import puts the scene's time unit (with its keys),
  ranges and frame back (`rigimport.time_state` / `restore_time`, trap 179). The skeleton transfer
  runs on the twin verdict the press decided on (`Decision.twin`), never its own second opinion.

Proof: `docs/superpowers/plans/verify_retarget_modes.py` **39 of 39 gates standalone** after the
review's fix pass (phases a-h; numbers in the spec): Manny a twin, 0 questions, every bone on the
clip's 0.072 cm (its left-leg fit), the legacy path to 0.0; Creep_Rig / Orc_D_Rig asked once each,
Keep - lengths kept 5.9e-14 / 1.9e-5 cm, orientations 0.0013°; Squash AS THE RIG STANDS - every bone
outside the IK legs on the clip's joint 0.0001 / 0.0002 cm, the IK legs' lengths kept (3.9e-10 /
1.6e-6) with their ends 0.0002 cm off the clip's, the line naming them; the lengths changed by the
measured -16.7 % / -4.9 %; Rotations on the same rig took the 62 follows away and wrote every
translate back to 0.0; skeletons Manny exact 8.9e-4 cm unasked, Creep Keep 5.6e-14 / Squash
7.2e-14; the Lugal rig opened read-only - Keep 6e-4 units, Squash 0.0007 units at x0.117 about its
pelvis, and 0.0007 again with the clip moved 36 units and turned 25° AFTER the connect; a Mixamo
clip onto Manny - Keep IS the legacy plan (a second Manny retargeted by the legacy call 0.0 cm,
limbs in FK and in IK), Squash 0.064 cm; a batch of 3 asked once; Cancel - 0 nodes left, the rig's
190 curves and 11590 keys untouched, and in a film scene with keys at 24/48 the unit, the keys, the
ranges 5-40 / 0-50 and frame 7 all back; a clip under a group turned 30° and scaled 0.8 (x1.25),
its root's keys moved (150, -80) off the group's origin: the stretched game root starts ON it to
0.0000 cm, where the pre-fix code put it 33.78 cm away (the positive control: the pre-fix plugin
fails d-squash 0.267 units, d-frame 31.99, h1 33.78);
`verify_rig_pipeline.py` 30/30, `verify_many_rigs.py` 32/32, `verify_creep_rig_asset.py` 16/16 after
the fix pass. 3580 unit tests.

176. **A joint's own `.bindPose` attribute can be stale by centimetres**: on Manny_Rig's game
      skeleton parent-child distances read from it differed from the bind by up to 3.5 cm, so a
      rest length read there would call a twin "not a twin". The skinCluster's `bindPreMatrix` is
      the bind the mesh uses (its inverse is the joint's world matrix at bind); read that.
177. **A rotation-only rig's game bones ignore a control's translation.** The Creep's and the Orc
      D's bones take ORIENTATION ONLY from their AS joints (lengths exact by design), so the first
      squash & stretch put every FK control on the clip's joints and the exported skeleton did not
      move: lengths 0.0 % against an asked -16.7 %, a fingertip 18.6 cm off. Every control gate
      would have passed; only measuring the GAME bones caught it.
179. **An FBX import changes the scene's time, and a Cancel has to change it back.** Measured in
      mayapy: FBXImport of a 30 fps clip into a film scene (FBXImportSetMayaFrameRate off) switches
      it to ntsc AND RESCALES the keys already there - a key at 24 lands on 30 - and puts the
      playback and animation ranges on the clip's and the time on its first frame. `currentUnit
      -time film -updateAnimation true` takes the keys back to 24; the ranges and the frame are
      then set in the old unit's frames. A Cancel that only deleted the imported nodes left all four
      changed, and every node-counting gate passed.
180. **A body scaled about its space's ORIGIN stands (1 - s) of its start away from where the
      bridge put it** - every place (`place_moves`, a drop point, a skeleton's own place) is
      measured from the UNSCALED root at its first frame. Scale about the root's first-frame floor
      point (`scalePivot`). Two verify lessons from proving it: the Creep's legs equal a UE clip's,
      so s = 1.0000 and no pivot can show - scale the clip's group to make s 1.25; and `cmds.parent`
      KEEPS the world position, so moving a group and then parenting the clip under it moves
      nothing (the gate read a root at (0, 0) and could not fail) - parent first, then move.
181. **Maya names a constraint in the ROOT namespace**: `pointConstraint` on `Creep_Rig:b` makes
      `b_pointConstraint1`, so a gate filtering constraints by a namespace prefix on short names
      finds nothing whatever happened - "no follow left" could not fail. Find our nodes by their
      attribute under the rig's skeleton.
178. **A batch that measures every clip when the first is placed reads the first clip at a stale
      path**: `onto_skeleton` wraps the clip's root (re-parents it) before it asks, and the other
      clips' recorded paths were fine while the first one's was `|Heavy:root` - «No object matches
      name» three times, every clip failed. Keep clips by UUID across anything that re-parents
      (trap 16 again).

## One outliner group and one layer per character (2026-10-02)

The animator: «Сейчас каждый персонаж в сцене создает кучу мусора если это не повредит нам то давай
сделаем так чтобы все части которые относятся к одному персонажу ригу были в одной группе, важно что
бы пользователь открыл аутлайнер и сразу все понял. Так же каждый риг должен иметь свою группу слой
что бы его можно было включать и отключать в сцене.» Away for two hours; every choice taken alone.
Spec `docs/superpowers/specs/2026-10-02-character-groups-design.md`.

**Measured first** (`measure_character_tops.py`, standalone, the build before and after): a Manny rig
left 4 world-level nodes (`Group`, `root`, `SKM_Manny_Simple`, `materialXStack1`), a Creep skeleton 6
(`Armature` and five meshes), a Manny skeleton 4 (`root`, `SKM_Manny_Simple`, `camera1`,
`materialXStack1`), and every extra on a bare skeleton one more (`WeaponSpaces`, `SpearMesh`,
`ArmorSpaces`, `SceneSetup_camera`, `CenterOfMass` - the spaces SHARED by every skeleton). After: one
node per character, and 0 for every extra.

- **The group** (`maya_scenesetup/chargroup.py`): `<base>_Character` at world level - a rig's base its
  namespace (`Manny_Rig1_Character`), a skeleton's its asset's file stem made free
  (`Manny_Skeleton_Character`, `Manny_Skeleton1_Character`); marked `skeldarCharacterGroup` (the
  catalog label) with a message link `skeldarCharacterRoot` from the root; found by the marker
  (`maya_rigs.group_of`), never by name; **t/r/s locked at identity** (a folder - the rig moves by
  `Main`, a skeleton by `root` - and an identity parent makes every `relative=True` re-parent exact).
  Add Character makes it for every row and every road (`character.group_character`, in
  `_after_import`'s unrecorded block): a rig's world-level nodes of its namespace, a skeleton's
  world-level nodes of its import.
- **One layer** `<base>_Layer`, the group its one member: V off hides the whole character, the assets'
  own layers included (`MDagPath.isVisible`, gated).
- **Parked in it** (`chargroup.park(node, owner)` - the one call for any future part;
  `character.character_group(root_or_rig)` the public question): Camera Setup's camera, a floor
  weapon, a weapon Connections lifts to world, a bare skeleton's CoM and its OWN `WeaponSpaces` /
  `ArmorSpaces` (a rig's stay in its AS `Group`).
- **`maya_rigs`**: `Rig.character` (default ""); `rig.group` is still AdvancedSkeleton's -
  `top_below(Main, character groups)` - so every rule about it holds; `rig_of` answers for the group
  and its loose parts. `top_of(rig.group)` was the identity and is `rig.group` now everywhere.
- **Exports lift the character's top out of the group** (`chargroup.lifted`, around
  `animexport._export_hierarchy`, both layouts, every road), because the exporter writes ancestors
  (trap 182), all of it inside ONE closed undo chunk (`skeldarExportFbx`), so a Ctrl+Z after an
  export is a net nothing (trap 186); the status line names the root as the outliner shows it, never
  the lift's transient `root1` beside a world-level `root` (`_export_hierarchy(shown=)`).
- **Who is it**: the group or a non-joint in a skeleton's group (a mesh, the camera, a floor weapon,
  the CoM) names that skeleton - `skeleton._group_root` and `skeletonimport.selection_names` alike;
  Delete takes the group and its layer, but a **stranger** in the group (the animator's own prop:
  nothing of ours, not recorded, not in the namespace - `deletion.strangers`) names no character, is
  moved out to world level and kept, and the confirm names it; a legacy character (no group) behaves
  exactly as before.
- **`chargroup.make` is all or nothing**: a failure moves the tops back to world by UUID, deletes the
  layer and the group (never a group still holding a top), re-raises, and the Add line says «no
  character group (...)».
- **Plain names now**: a grouped second Manny skeleton is `|Manny_Skeleton1_Character|root` with plain
  meshes (nothing collides at world level), so Export / Import with NOTHING selected and two plain
  skeletons refuses where "the one named `root`" used to pick the first silently; a mesh, bone or the
  group selected decides it.

Proof: `verify_character_groups.py` **146/146 standalone** - A every row: one node + one layer,
locked, linked, the grouping moving nothing (joints and sampled vertices **0.0 cm** against the same Add
ungrouped), V off **75 / 83 / 79 / 4 / 5 / 1 visible shapes → 0** with the assets' own layers forced on;
B four characters with their kits: nothing at world level but the four groups, the who-is-it questions
answering from the group, the bridge onto / new rig / new skeleton / a square of two all grouped; C the
exports in both layouts equal to the same character ungrouped (top node, joints, frame-20 matrices
**0.0**), the scene put back exactly, the control without the lift writing `Manny_Skeleton_Character`
into the file; D Delete (433 / 2723 nodes) + Ctrl+Z (the layer holding the group again) + redo; E a
legacy character as before; F a portrait drop moved by exactly the point, the group at the origin. The
existing verifies re-run on the branch: delete 82/82, rig pipeline 30/30, many rigs 32/32, weapon space
11/11, inventory 14/14, armor 15/15, cascadeur layout 10/10, Creep rig 16/16, Orc D 22/22, one shader
4/4, Creep skeleton 9/9, FK/IK 63/63, weapon socket 10/10; in a disposable GUI Maya (port 7064) Connections 40/40 and Add
Character 31/31 - every first-run failure a world-level path literal in the verify, moved into the
group. G a grouping that fails half way leaves a legacy character and says so; H a UE clip onto a turned, moved grouped rig equal to the ungrouped one (0.0 over 5 frames); I two Manny + two Creep skeletons (plain `root`s): recolour, export, Onto selected, the animator's prop kept by Delete. 3545 unit tests; the Outliner and Layer Editor photographed (`character_groups_outliner.png`).

182. **The FBX exporter writes a selected node's ANCESTORS into the file.** Measured 2026-10-02:
     `FBXExport -s` of the joints of `|CharGrp|root|pelvis` with `FBXExportIncludeChildren false` came
     back as `|CharGrp|root|pelvis`. Anything that groups a skeleton must take its top out to world
     for the length of an export (relative, by UUID, the name put back) - or every file carries the
     group, and Cascadeur's layout reads "root stands under X" and goes out plain.
183. **A node cannot take a namespace's name, and a namespace cannot be made over a node's - the
     second silently.** `createNode -name :Manny_Rig` beside a namespace `Manny_Rig` answered
     `Manny_Rig1`; `namespace -add Bar` beside a node `|Bar` raised nothing and `namespace -exists`
     answered False. A group named exactly for its rig would have blocked the next rig's namespace.
185. **A verify that names a character's nodes by world-level long path breaks the day the character
     moves into a group** - `"|Manny_Rig:root"`, `"|Creep_Rig:Group|Creep_Rig:Geometry"`,
     `"|Armature|root"`, «lies at world level»: 14 gates across 9 verifies failed on correct code here.
     Ask `maya_rigs` / `character.character_group`, or use a partial path (`Manny_Rig:root`), and keep
     the expectation as strict as it was.
184. **Re-parenting the import's nodes invalidates the paths `returnNewNodes` gave** (trap 16 in
     Add Character): the first grouped build said «added - 0 joints, 0 meshes». Resolve the import by
     UUID across any re-parent.
186. **A context manager that edits the scene and puts it back leaves its LAST step on the undo
     queue.** `chargroup.lifted` re-parented the top to world and back around every export; both moves
     were recorded, so the animator's first Ctrl+Z after Export FBX... undid the "back" and the
     grouped root jumped to world level - the scene state after the export was exact, and no gate
     pressed undo. Wrap a round trip in ONE closed undo chunk (a net no-op to undo), not in
     `stateWithoutFlush` (trap 145 breaks an enclosing chunk), and gate it with `cmds.undo()` + a
     control without the chunk.
187. **Grouping characters ends the world-level name clash that a rule quietly relied on.** Every
     second skeleton used to arrive renamed (`Manny_Skeleton_root`), so "the one named `root`" picked
     the first plain one; grouped, every skeleton keeps a plain `root`, and an Export / Import with
     nothing selected now refuses between them. Right by the bridge's own rule (never guess), but a
     behaviour change: list every rule that reads a short name before removing what made names unique.

## The animation's name under each character (2026-10-02)

The animator: «при групповом импорте в сцену в том числе и при переноси мышкой драгом давай внизу под
каждым скелетом или ригом персонажем будем писать имя анимации а то сейчас не понятно» - away for two
hours, every choice taken alone. Spec `docs/superpowers/specs/2026-10-02-clip-labels-design.md`.

- **One rule at the bottom of every road**: `rigimport.retarget_imported` (the Rig and New rig presses,
  a drop on a rig or the floor, the batch square) and `skeletonimport.onto_skeleton` / `onto_existing`
  (the Skeleton presses and drops) end in `_label`, a lazy seam onto
  **`maya_scenesetup/cliplabel.py`** (`label_rig` / `label_skeleton`, never raising). `lineimport` and
  `window` needed nothing. One label per character: a later clip REPLACES its text on the same node
  (`plan`: create / keep / update) - and **a label names the take, so whatever clears the take clears
  the label**: the rig reset in front of every bridge import (`rigimport.ready_rig`) deletes it, so no
  refusal after the reset (still posed, no joint, a connect refused) leaves a stale name, and the press
  writes a fresh one after its bake. **The Retarget button** (`maya_rig_retarget.run_retarget`) clears
  at its reset too and relabels after the bake from its source (`clip_name_from`, pure: the outermost
  namespace, else a top group that is not a joint or a generic wrapper, else the clip file the scene was
  OPENED from) - or leaves the rig unlabelled when the source names nothing: never the old clip's name.
- **What it is, measured against text curves (115 nodes, illegible at 16 m)**: an `annotationShape`,
  `displayArrow` off - fixed screen size, centred on its point, facing the camera, drawn over every mesh,
  in a playblast, hidden by Show > Dimensions. **Unselectable AND coloured** (trap 188): the transform in
  reference display, the shape's own override back to normal with RGB. In the hub's **accent** - measured
  behind the labels of a textured 2 x 2 square, no luminance beats ~2.3 against a grey background and
  white bodies at once (muted 2.10, accent 2.14 the best worst case; near-white 4.91 over the floor,
  1.35 over a body), and the orange's hue stands apart from every neutral.
- **Where**: 50 cm ahead of the root on world +Z (`FRONT`, past Main's ring, 40.52) on the floor,
  following the root in WORLD space through four DG nodes (`_follow`: the root's world X/Z, Y on the
  floor, FRONT on world +Z, then the label's own `parentInverseMatrix`): exact (0.000000 cm over the
  thrust's 248 cm) and still exact with the rig's group moved and turned (trap 189). Each node is linked
  to the label by message (`skeldarClipLabelOf`); a label whose network is gone is mended on the next
  import (`follows`).
  A label hangs in its character's outliner group (the merge, below; `home_for` gives the group first),
  else - a character added before the groups - under the rig's group in its namespace (`<ns>:clipLabel`)
  or at world level beside a skeleton (`<root>_clipLabel`), linked by message (`skeldarClipLabelRoot`) and marked `skeldarClipLabel` (the
  clip's name). **`home_for` is the one place that decides where** - the per-character group points it
  there in one line. `deletion._clip_labels` takes it as a part; never under the skeleton, never in an
  export (trap 76; gated by reading the FBX back, with the label exported on purpose as the control).
  The root only FEEDS the label's network (its `worldMatrix` out), so the existing checks - a joint's
  constraint CHILDREN, a root's incoming connections - see nothing new on it.
- Viewport Studio's **Clean view hides the labels** with `dimensions` (by design: it is the beauty
  picture); unticking it gives them back.

Proof: `verify_clip_labels.py` **17/17 standalone** (batch onto rigs and skeletons, the reset taking
the label, a single import relabelling, following to 0.000000 cm, the exports free of labels, Delete +
Ctrl+Z, a Creep, the group moved and turned - the label 0.000000 against the old constraint's 32.139 cm
-, a broken label mended, the Retarget button relabelling from its source's namespace and unlabelling
for a nameless source); `verify_clip_labels_gui.py` all gates in a disposable Maya (each label's ink at
its own character's feet by hiding one at a time, no overlap, a marquee takes no label, the colour
table, drops onto the floor and onto a rig); pictures `clip_labels_square.png`, `_dark`,
`clip_labels_drag.png`; 3558 unit tests.

188. **An annotation in reference display draws BLACK whatever its colour** - an override on the
      transform, on the shape, or a display layer's own colour - so "unselectable" read as "invisible on
      a dark backdrop". The pick reads the PARENT's display type and the draw the SHAPE's override: the
      transform in reference, the shape's override enabled at display type 0 with RGB on, is both
      unselectable by a marquee and drawn in its colour. Template draws a dim grey.
189. **A `pointConstraint`'s offset - and the constrained node's own skipped channel - live in its
      PARENT space** (the memory note "pointConstraint offset is parent-space", met again). The first
      build's label hung under the rig's group with `offset=(0, 0, 50)` and `skip="y"`: with the group
      moved (37, 22, -15) and turned 40 deg it stood **32.139 cm** off its floor point, turned with the
      group and lifted 22. A WORLD point for a node under a group that may move is computed in world and
      brought in through the node's own `parentInverseMatrix` (decompose -> compose -> mult ->
      decompose -> translate): 0.000000.
190. **`cmds.annotate` refuses a bare transform** («Annotation command only works on shapes»), and when
      given a shape it draws an arrow to it; `createNode("annotationShape", parent=t)` needs no target.
191. **Work queued with `maya.utils.executeDeferred` does not run inside the same command-port send**,
      not even through `maya.utils.processIdleEvents()`: a drop's import (`listdrag` defers it one idle)
      happens after the send ends, and a gate in the same send reads the scene before it. Drop in one
      send, measure in the next.
192. **A disposable GUI Maya left MINIMIZED playblasts fine and measures wrong**: the same square read
      label boxes overlapping each other, the contrast at 1.93 for 2.15 and a whole-view marquee picking
      **0** nodes - the pick runs through the viewport's draw (trap 56) and a minimized window draws
      nothing - while the picture itself was the same to the eye. `MayaWindow.showNormal()` (port 802 x
      650) and every gate passed with the first run's numbers. Restore the window before a gate that
      picks or diffs, and probe `M3dView.portWidth()` (trap 105's family).
193. **A playblast diff's bounding box is stretched across the picture by a few stray changed pixels**
      (a texture filtered a hair differently between two blasts, at JPG quality 100): one label's box
      read as overlapping all three others. Trim the box to the 2nd..98th percentile of the changed
      pixels. And hide one thing at a time rather than projecting points: no film-fit arithmetic to get
      wrong.

## The IK limbs follow the FK limbs, stretch included (2026-10-02)

The animator: «если мы перенесли анимацию с растяжением костей то кости при переключении контролов на
IK не растянулись они остались прежнего размера. Это не верно анимация IK должна соответствовать
анимации FK это обязательное условие». Spec `docs/superpowers/specs/2026-10-02-ik-follows-fk-design.md`.
**This replaces what the sections above say about IK**: «a limb in IK keeps its own lengths», Manny's
Rotations with «the IK hands and feet on the clip's», the twin's IK on the clip's hands with its poles
on the clip's upper bones, and fkik's `Lenght1/2` reset.

**Measured first** (the Retarget button in Squash & stretch, each limb's blend 0 against 10 on the
game bones): the Creep's elbows **11.5 cm** off in IK (arms -17 %), the Orc D's shoulders **0.91**
(its clavicle), elbows 3.4 and balls 0.55, Manny under Sweep Fall shoulders **4.1**, hips **3.0-3.2**
and a foot **2.14 cm** longer in FK - and **Manny under a UE clip, the twin, elbows 11.4 / 20.0 and
knees 9.6 / 17.8 cm off**: its IK poles rode the CLIP's upper bones, whose roll is not the elbow's
plane. No gate had switched a blend; they all measured the rig as it stands (Manny's arms and legs
in FK).

**What an AdvancedSkeleton IK limb is** (its network and the vendor's `asAlignFKIK`):
`IKX<mid>.tx = |input2X| * Lenght1` (the multiplyDivide on `IK<Limb>.Lenght1`'s output, negative on
the left), `IKX<end>.tx` with `Lenght2`, with `stretchy` 0 (its stretch factor runs through an
animCurveUU flat at the rest sum below it, so 1); the chain's root `IKX<start>` at `t = 0` under
`IKXOffset<start>`, free, followed by nothing of the FK; the foot's `IKX<end>` aimed by an SC handle
under `RollToes` at the ball, `IKXToes.t` the ball in the ankle, the toe control pivoting at the rest
ball (`IKOffsetToes`). The vendor's own FK→IK switch sets `Lenght1/2` from the FK (with `stretchy` 10)
and does not move the root.

- **The IK ends and poles follow the rig's own FKX in every version** (`maya_asretarget.drive_plan`,
  the legacy call included): `IK_FOLLOW` / `POLE_FOLLOW` - the rotation-only rigs' and the
  PlayerMale's rule. The schema's `ik_rows` / `pole_rows` drive nothing any more; `keep_lengths` is
  `rotation`; Rotations on any rig is the rotation plan (`ROTATIONS ONLY` on the line).
- **`SkeldarAnim/maya_ikmatch.py`** (a payload row): `carry(rig, start, end)` after the bake, when the
  FK took position (the holder's `asrtFkPosition`; pm: its stretch) - one walk reading each limb's FKX
  chain and the frames the IK nodes hang in, then `IKX<start>.translate` (the FK start joint in
  `IKXOffset<start>`), `Lenght1/2` (the FK segment over `|input2X|` times the chain's world scale) and
  on a leg `IKXToes.translate` (the FK ball in the FK ankle) with the ankle's SC handle and
  `IKOffsetToes` moved onto the FK ball (`moved_local`: the move as a vector, pivot-agnostic). A series
  at rest writes nothing (`TOL_RATIO` 1e-5, `TOL_CM` 1e-4), a constant one a value, else keys; the bake
  line names it («the IK limbs take the FK's shape: arm_r lengths x0.798/0.758, the shoulder moved
  0.91 cm; leg_r ..., the ball moved 2.14 cm»). `restore(rig)` from both modules' `reset_build_pose`:
  curves deleted, `Lenght` at its default, every moved translate at its own value, kept on the node the
  first time it moved (`skeldarIkRest`). Limbs found by the FKIK node's start/middle/end joints; the
  toes the nearest FKX joint BELOW the FK ankle (trap 197).
- **The Connections FK / IK switch carries the same** (`fkik`, arms): to IK writes `Lenght1/2` and
  `IKXShoulder.translate` from the SHOWN chain; `IK_SOLVE` is `swivel, antiPop, stretchy` (the lengths
  left it).
- The question, the connect lines and the notes lost «a limb in IK keeps its own lengths»;
  `stretch_ik_note` is gone (a test pins it).

Proof: `docs/superpowers/plans/verify_ik_follows_fk.py` **16/16 standalone**, every limb's game bones
with the blend at 0 and at 10 over 13 frames - the control first (the carry switched off: elbows
**13.99 cm**); the Creep **0.0501 cm**, 0.105 deg; the Orc D **0.0495** (shoulders 0.91 and balls 0.55
carried); Manny under Mixamo **0.0551** (4.14 / 3.0-3.2 / 2.14 carried); the twin **0.0370**, its IK
on our FK; Rotations after a stretch: every carried channel at rest to 1.8e-15, IK = FK 0.048; the
Connections switch on a stretched arm 0.019 cm both ways and over a range; Manny Rotations under
Mixamo 0.055 cm, no length touched. `verify_retarget_modes.py` all phases again (b4 now: every bone,
the IK legs included, on the clip's joint, the Creep to 0.0005 cm; e: Rotations on Manny has the IK
where the FK is, 0.053), `verify_rig_pipeline.py` 30/30, `verify_many_rigs.py` 32/32,
`verify_creep_rig_asset.py` 16/16, `verify_orc_d_rig_asset.py` 22/22,
`verify_skeleton_conventions.py` 122/122, `verify_fkik_switch.py` 63/63, `verify_weapon_space.py`
11/11, `verify_character_groups.py` 146/146 (that mayapy then died in its shutdown, after the summary line), `verify_clip_labels.py` 17/17, `verify_import_sources.py` 27/27; 3822 unit tests. The 0.02-0.05 cm left is the pole rig's nudge, as before.

**Still not IK = FK, and not this**: an IK knee or elbow is a hinge - a clip's calf or forearm rolled
about its own bone is not an IK pose (the Creep under Heavy: the calf 30-55 deg, the forearm 33 deg
about their own axes in IK against FK, every position and direction exact; the same in the rotation
version before this work, and AdvancedSkeleton's own switch has the limit). The IK spine is driven by
no version. The vendor's Switch FK/IK button re-derives the lengths (with `stretchy` 10) and leaves
the root. `verify_asretarget.py` / `verify_asretarget_mixamo.py` (live, the legacy call) still gate
the IK on the clip's bones: history. A rig with a take from before this has the old IK: retarget again.

194. **AdvancedSkeleton's IK limb has its own lengths and nothing carries the FK's into them.** A take
     that translates the FK controls (a twin's slides, any squash & stretch) moves the FK chain's root
     and changes its segments; the IK chain keeps `Lenght1/2` 1 and its root on the rest offset, and the
     IK end still on the FK wrist hides it - the hand is exact, the elbow 11 cm off. Every gate passed
     because none of them switched the blend. Measure IK against FK by switching it.
195. **A pole riding the source's upper bone is not on the limb's plane**: the bone's roll about its
     own axis is free in a UE clip (the twist bones take it back), so Manny's twin IK - its poles on
     `upperarm`/`thigh` with their rest offset - stood its elbows 20 cm and knees 18 cm off its FK on
     `LongSword_Attack_Right_Heavy_3P`. The 2026-09-04 proof ran on a synthetic take that bent like a
     hinge. The pole belongs on the plane the joints themselves make (`_pole_rig`).
196. **`test_asretarget.py` reads the module's source with the default encoding (cp1252)**: a Cyrillic
     quote in `maya_asretarget`'s docstring broke three tests with UnicodeDecodeError, a byte cp1252
     has no character for (`«»` alone decode, as mojibake). That module stays ASCII.
197. **The FKX toes joint is not the FKX ankle's child**: AdvancedSkeleton puts the toes' own FK
     control between them (`FKXAnkle > FKOffsetToes > ... > FKToes > FKXToes`), so a children walk found
     no toes and the foot carry silently did nothing - the ball 2.14 cm off while the line said the legs
     were carried. Look among the descendants, the shallowest FKX joint whose IKX twin is the IK ankle's
     child.

## The Characters cards catch fire under the mouse (2026-10-02)

The animator: «Хочу попробовать сделать крутые карточки выбора ригов и скелетов. Когда навожу мышкой на
карточку то хочу что бы на заднем фоне в карточке загорался огонь летели искры и она немного увеличивалась
в размере. попробуй сделать визуальный прототип но в плагин пока не вставляй». A standalone prototype came
first (`docs/superpowers/plans/proto_fire_cards.py`: `mayapy proto_fire_cards.py` opens a window of the
grid in the hub's colours, the same QPainter; `--frames DIR` renders a scripted hover offscreen and an HTML
flipbook). The verdict: «У каждого персонажа свой цвет огня. А так все хорошо мне нравится давай делать
фичу». Spec `docs/superpowers/specs/2026-10-02-character-card-fire-design.md`.

- **What it draws**, on an available portrait under the mouse:
  - **flames behind the character**: a heat field (80 x 90 cells) rising from the card's bottom edge,
    shaped by a cooling map scrolling up with it, torn by the classic one-random-neighbour-below rule. The
    HEAT is interpolated to the card's pixels and the palette applied after, so the edges stay crisp. It
    is drawn additively under the portrait (the portraits carry alpha);
  - **sparks**: 24 on catching, 30 on a click, 30 a second while it burns; a quarter in front of the
    character; they fly on past the card;
  - **the character backlit**: the silhouette 30 % darker, a rim on the inside of its edge, firelight
    from below, all flickering with the field's heat;
  - **the card grown 7 %** on a spring (a touch of overshoot), with an outer glow, a ring and a name in
    the fire's colour.
  The mouse off: the source dies, the flames finish rising and burn out (1.4 s measured), the card settles.
- **A fire per character** - `maya_charfire.FIRES` by model key: Manny `ember` (the hub's orange), Creep
  `spectral` blue, Orc D `toxic` green, UE4 Mannequin `arcane` violet, and the «?» card (`catalog.AUTO`)
  `ember`, as Manny's. A model not in it has no fire and the old hover. A new character model wants a
  fire there (a test pins every model with a catalog row to a palette of its own). The table is NOT in
  `catalog.py` on purpose (a peer was rewriting `MODELS` the same hour).
- **The «?» card** first got a BLACK fire («... черный огонь на фоне», 2dff3fb): black laid over (not
  added onto) a red glow standing behind the tongues. The animator then asked for it to burn like
  Manny's («Давай не делать черный огонь а сделаем так же как и карточка менни»), and the black fire
  was taken out whole (its palettes, `style()`, the "over" blend). Its portrait is a TRANSLUCENT
  silhouette (alpha 0.30, the «?» 1.0), so the fire showed through the body and the orange «?» melted
  into the flames; then «сделай что бы огонь как и на других карточках горел за силуэтом».
- **Every portrait hides the fire behind its body**: under the portrait `_paint_hot` lays
  `charfire.body_mask(alpha)` (alpha 0.25 and up as opaque, the edges soft) filled with the card's own
  face colour (`_body_for`, cached per model, size and face). A faint silhouette then looks as it does
  cold, with the fire behind it; an opaque portrait (Manny's) is unchanged, no halo.
- **No fire**: on a dimmed portrait, during a drag (the drag puts it out), with ⋮ → Interface animations
  off (`maya_hubmotion.enabled()`, asked through `maya_chargrid._animations`, a test seam).
- **`SkeldarAnim/maya_charfire.py`** (numpy + stdlib; a subprocess test pins it; a payload row): the
  palettes and their premultiplied B G R A LUT, `Fire` (`field(lut, w, h)`), `Sparks`, `CardFx` (hover ->
  `power`, the grow spring, the flash, `active()`, `shown_grow()` never below rest), `lit_masks(alpha)`.
  Fixed-step and seeded: 23 tests with no Qt.
- **`maya_chargrid`** paints it. `fx` {model: CardFx} lives only while a card burns; a 16 ms
  `fire_timer` runs only then. `_paint_cold` is the old tile, `_paint_hot` a burning one.
  `hover_model(model)` is the hover's seam for a verify; `advance(dt)` the loop.
- **The overlay.** The grid is clipped to its placeholder, so a grown card, its glow and its sparks would
  be cut at every edge. A burning card is drawn by `FireOverlay` (`skeldarCharacterFire`), a
  mouse-transparent child of the hub's SCROLLED CONTENT (the first ancestor whose parent is a scroll
  area's viewport: the skin's `skeldarHubContent`, the classic hub's scrollLayout).
  - It covers the grid widened by a fifth of a cell at the sides and bottom and three fifths above,
    re-synced every tick: a card sliding above moves the grid and sends it no event.
  - The grid skips the cards it draws (`overlaid`).
  - While the grid is not whole inside every ancestor up to the content (a card sliding shut caps its
    body), the grid draws its burning cards itself, clipped.
  - The grid's `destroyed` deletes it; the content's death takes it too.

Proof: `tests/test_charfire.py` 25; `tests/test_chargrid.py` 15 new (lights, not a dimmed one, not with
the animations off, not a model with no fire, moving on, burning out and the timer stopping, the Creep blue
and the Orc green in the picture, the «?» card burning orange and behind its silhouette, a drag, a click
burst, the overlay in a scroll area drawing it past the grid and the grid skipping it, a grid cut by its
parent drawing itself, the overlay dying with the grid); 3960 unit tests. `docs/superpowers/plans/verify_character_fire.py`
**10/10 in a disposable GUI Maya** (port
7037, scratch `MAYA_APP_DIR`, `MAYA_NO_HOME`, minimized, killed after) on the repo's hub floated to the
dock's 510 px, a real QMouseEvent on the grid:
- the overlay at (0, 122, 510 x 376) around the grid's (16, 189, 475 x 287), drawing the Creep;
- 405 blue samples in it, 0 in the grid; the Orc D 73 green;
- the paints of a burning frame p95 **4.2 ms** (grid + overlay), a loop turn p99 9.2 ms;
- cold 1.43 s after the mouse left, the timer stopped, the overlay hidden;
- off with Interface animations off;
- after `maya_hub.rebuild()`: 0 overlays left, the new grid burning again;
- the «?» card burning orange (295 fire samples in the overlay's picture) and behind its silhouette:
  the body at the bottom stays grey (84, 81, 83);
- a run sent seconds after Maya's launch reads a loop turn p99 of 56-58 ms (Maya still settling, the
  paints still p95 4.8 ms); the same run on the warmed-up Maya: p99 10.6 ms, paints 4.35 ms.
Pictures: the hub with Manny burning, and with the «?» card (DWM's copy of the window).

198. **A Bash heredoc in this harness turns a double backslash into a single one** (2026-10-02, twice:
     a patch script, and this very paragraph, both written with `<<'EOF'`, the quoted delimiter that should
     keep the text literal). In the script a backslash + newline inside a `'''` string became a line
     continuation and the replacement's text no longer matched the file (the assert caught it). Write
     Python and anything with backslashes through the Write / Edit tools (trap 101 is PowerShell's
     version).

## The «?» card: a clip onto ours when its skeleton is ours, else in its own (2026-10-02)

The animator, with Maya and their Unreal project MarkerLess_02 open («где много разных персонажей»): «Иногда
хочется иметь возможность импортировать анимацию с исходным ригом скелетом который находится в движке а не
переносить на наши. Давай сделаем карточку рига и скелета со знаком вопроса и когда переносим анимацию при
выбраной этой карточке наш плагин будет смотреть какой скелет в исходном файле если он найдет скелет который
совпадает с нашим то перенесем анимацию на наш риг или скелет, если ... совпадений нету то импортируем в
сцену родной риг или скелет». Asked, all three the recommendation: an **explicit target wins** (Onto selected
with a character of the kind selected, a drop on one; never "the only rig in the scene"); a native is
**painted in a palette colour** (Unreal's FBX carries no textures); **the kind is kept** (Rig matches our rigs,
Skeleton our skeletons - a UE4 clip with Rig, an Orc clip with Skeleton come in their own skeleton). Spec
`docs/superpowers/specs/2026-10-02-auto-character-import-design.md`, plan beside it.

**Measured first** (12 skeletons, ~2500 clips):
- `FbxExportOption.export_preview_mesh = True` brings the skinned mesh beside `root` (no wrapper) with a
  `bindPose`; the exporter picks the mesh itself (none of the preview-mesh calls exist in Python).
- **Unreal gives a Manny clip QUINN's mesh** (trap 199), so the match reads the ANIMATION's bones.
- The share of the clip's voting bones whose animated length - the median over 9 sampled frames, to the
  nearest bone both sides share - is within 1 % of ours at the bind separates every skeleton there: matches
  0.88-1.00 (Manny, MC_DungeonLife's and MC_LongswordVol2's UE5 mannequins, Orc on Orc D, UE4), the rest
  ≤ 0.47 (an Orc clip against Manny). A single median does not: Orc against Manny reads 1.9 %.

**The card**: `catalog.AUTO = "Auto"` last in `MODELS` (`is_auto`; `kinds_of(AUTO)` is `KINDS`;
`character_for(AUTO, k)` None; `rows_of_kind`), a drawn «?» (`assets/character_portraits/Auto.png`,
`make_auto_portrait.py` - vector paths: offscreen Qt has no font). Picked in both kinds, never dragged in, no
Open scene; + Import, a portrait drop and Open scene refuse it (`charlook.AUTO_ADD`); the line says
`charlook.auto_text(kind)`. `scene window.current_choice()` / `auto_kind()` answer for the grid and the
dropdown fallback («Auto [rig]» / «Auto [skeleton]») alike; `chosen_character()` stays None for it. The grid
wraps 4 + 1 in the 360 px dock. `make_character_portraits.render_all` skips it.

**The match** (`maya_uebridge/skeletonmatch.py`, stdlib): `assets/character_skeletons.json` is every catalog
row's game skeleton at its bind (`leaf: [parent, x, y, z]`, `maya_retargetmode.rest_world`) with the asset's
sha1 - written by `docs/superpowers/plans/make_character_skeletons.py` (mayapy); **a unit test pins the sha1:
rebuild a character asset, re-run the script**. `score` (helpers and root/pelvis never vote, bones < 1 cm
neither, the two anchors must agree), `match` (≥ 10 voters, share ≥ 0.75, ties to catalog order),
`match_text` («matched Manny [rig] - 78 of 78 bones» / «no skeleton of ours (best Orc D [rig]: 3 % of 64
bones)»). The clip side is `autoimport.clip_bones` - `getAttr(worldMatrix, time=)` on the plain keyed skeleton.

**The roads** (`maya_uebridge/autoimport.py`): `window.auto_kind()` first in `import_selected` /
`import_dropped`. `_auto_press`: Onto selected + a character of the kind selected (`explicit_rig` /
`explicit_skeleton`, selection only) → today's road onto it, bones-only export; otherwise one clip →
`import_auto`, several → `lineimport.run(..., auto=True)`, both with `_export_with_mesh`
(`uescripts.export_script(preview_mesh=True)`; a file source brings what it holds). `import_auto`: import
(a failure takes the namespaces back, time restored) → match among the kind's rows → a rig row:
`onto_new_rig` (`ready_rig` → `decide_bones` → `retarget_imported`, one chunk; a twin is never asked) / a
skeleton row: `onto_new_skeleton` → else `nativeimport.keep`. The batch matches each clip, lays the square out
unscaled, works the matched first (a Cancel then finds nothing kept), one `_Versions` per row, `auto_summary`
(«Manny_Rig MM_Fall_Loop, own Kwang_GDC Ability_Q_Catch»). The drag reads `auto_kind` at its start: a floor aim
carries `auto` (`Scene._marked`), its caption «A_Jump · our rig if it matches, else its own · floor (x, z)»;
over a rig / skeleton it is today's drop.

**The native character** (`maya_uebridge/nativeimport.keep`, unrecorded - trap 115): placed by offsetting
its root's translate keys (`local_delta` through the parent's world-inverse; no wrapper, trap 182), ONE group
+ layer (`chargroup.make`) named for its largest skinned mesh (`Kwang_GDC_Character`) else the clip, its
namespace - and any nested in it, Mixamo's `mixamorig:` - merged into the root namespace AFTER the group
exists (plain names, nothing at world level to collide), the next palette colour, Delete's record («Kwang_GDC
[own skeleton]»), the clip's label. A root under an ancestor the clip ANIMATES (a Unity clip keyed on the
model's top, a Blender Armature) is not moved and says so: an offset in a moving space swings it on an arc,
and moving the ancestor would move a skinned mesh under it twice. Only a CHAIN of nested namespaces is
flattened; siblings (a scene holding two namespaced characters) keep their own. From then on it is a
skeleton like any other (Onto selected, Export FBX, Delete, Colour).

**The review's fixes** (a four-lens review, every finding verified twice): an Auto press runs inside
`autoimport.kept_selection` - the rig it ADDS selects itself (Add Character's rule), and the next Auto press,
Onto selected, took that for the animator's explicit target (a Kwang clip landing on the Manny just added,
its take replaced; verify phase `repeat`); the native's move is read through its parent at the clip's
FIRST frame; the template pin hashes the asset with CRLF read as LF (`skeletonmatch.asset_digest`: a
Windows checkout writes a text `.ma` with CRLF, and the pin must agree in every worktree).

Proof: `verify_auto_character.py` (fixtures by `export_auto_fixtures.py`, six clips with their meshes) -
**all 44 gates green standalone**: the match table 6/6; Manny and Orc D added and retargeted, nothing asked
(Manny 0.097 cm - its own left-leg fit; Orc D every bone pointing as the clip's to 0.087°, trap 200); the UE4
skeleton 0.021 cm; Kwang native - group, layer, plain names, 116 joints, skin, colour, record, label, the
root on the drop point to 0.0000, every joint on the moved clip 0.000000 cm, the mesh 8e-6 cm, Delete whole +
Ctrl+Z; an Orc clip with Skeleton in its own skeleton (`SK_Orc_Marauder_G`); Mixamo's Sweep Fall in its own
(`|Sweep_Fall_Character|Hips`); the batch of three, nothing asked, slots 250 cm apart; two Auto presses in a row (the
second matched, not put on the rig the first added); the explicit target
(the selected Manny takes a Kwang clip, asked; nothing selected → native); the native exported (116 bones,
plain, no mesh); a later clip onto the native, exact, in place. Live in a disposable GUI Maya (7033) against
the running editor: the card picked through a Qt press (`auto_card.png`), Import Animation on Kwang (3.7 s,
native) and MM_Fall_Loop (11.7 s, Manny_Rig, Onto selected with nothing selected), a batch of four (31.8 s:
Manny_Rig, Orc_D_Rig, own Kwang_GDC, own SK_AttackTest - `auto_square.jpg`), two floor drops through
`import_dropped`. Unit tests: `test_uebridge_skeletonmatch.py`, `test_uebridge_autoimport.py`, the Auto
classes of the lineimport / listdrag / window / catalog / chargrid / charlook / scenesetup-window tests.
Not built: textures for a native (asked), an AS rig for one, choosing Unreal's mesh, matching by the Skeleton
asset's name.

199. **Unreal's AnimSequence FBX export gives a Manny clip QUINN's mesh.** With `export_preview_mesh` the
     exporter takes the clip's preview mesh, else its skeleton's, else `FindCompatibleMesh()` - and for
     three SK_Mannequin folders it found `SKM_Quinn_Simple`. The mesh's bind then has Quinn's proportions
     (2 % of the bones within 1 % of Manny's) while the animation's bones are Manny's (100 %). A skeleton
     test read off the bind would call every Manny clip a stranger; read the animated bones.
200. **An Orc pack's MM_ clips carry Manny-length arms** (the arm bones 6.4 % off Orc D's rest; Unreal's
     translation retargeting hides it on the Orc's mesh). They still match Orc D (0.88), and the twin
     retarget keeps Orc D's bones: the hand ends 1.7 cm off the raw FBX joints while every bone POINTS as
     the clip's (0.087°) - what Unreal shows. A gate on positions alone calls that broken.

## The Pose Library: cards of bones, onto any rig or skeleton (2026-10-02/03)

The animator: «библиотеку поз на подобии studio library ... если анимация относится к ригу то мы должны
сохранять анимацию не контроллов а костей ... задействовал уже написаные элементы ретаргета ... достаточно
выделить любую часть скелета или рига нажать apply ... перетягивать наши карточки на персонажа ... Поза должна
накладываться на текущий активный анимационный слой ... в пустую сцену ... загрузит исходный риг или скелет».
Asked: **Blend and Mirror** in the first version; the library is **a `poses/` folder in the plugin, installed
like all our content**, local poses survive an install, and on the animator's machine the library points at
the repo's `SkeldarAnim/poses` once (`skeldarPoseLibraryRoot`) so a commit + push ships them; **the character
stays where it stands** (root/Main never written, the pelvis relative to the root); **always a key**, on the
active layer; **both FK and IK** keyed on a rig. Poses only - animation cards later. Spec
`docs/superpowers/specs/2026-10-02-pose-library-design.md`, plan beside it. Built in its own worktree
(`feature/pose-library`) by subagent waves, each task reviewed, then a four-lens final review with three
skeptics per finding (10 confirmed, 2 critical) and two fix rounds.

- **A card** is `<Name>.pose/` (`pose.json` + `thumbnail.jpg`) in plain folders (`maya_poselib/store.py`,
  stdlib, atomic writes, deletes to `<userAppDir>/SkeldarPoses_trash`). A character card holds EVERY bone of
  the source skeleton (rest = `rest_world`, the bind; world; the canonical name from `maya_skeletonmap.
  recognize` over the WHOLE skeleton - it refuses a hand chain alone) and the members; a rig card also the
  DRIVE of the eight unrolled limb bones (`G·D⁻¹·S`: the roll AdvancedSkeleton moved into the twist joints,
  put back). An objects card holds keyable attributes (Studio Library's kind); the selection decides where it
  goes, and never onto a character's parts.
- **The transfer** (`posemath`, pure): pairs by leaf when both skeletons are UE-named, else by canonical name
  (spine/neck distributed); each member's rotation relative to its nearest PAIRED ancestor, carried through the
  two rests (`O = rigid(T_rest)·A·rigid(S_rest)⁻¹`, `A` the minimal rest-direction turn); every bone keeps its
  own length; the pelvis takes the card's offset from the root, scaled. A skeleton is ROOTED only when its top
  joint is a canonical `root` at its own feet; otherwise (Mixamo's Hips, a Biped's Bip001) it stands on its
  GROUND frame (the floor under the top joint, turned by its heading), source and target alike. A twin (median
  length ≤ 1 % AND every rest chord within `TWIN_DEG`, 1°) is exact. Mirror reflects each bone's root-space
  delta from rest (`r[s]·F·D[opposite]·F`). The drive is read where the target does not carry the source's
  twist bones.
- **Onto a rig** (`rigsolve`, `fkik`'s analytic switch generalised to the whole rig; no constraint, no bake,
  never `reset_build_pose`): sampled once; per AS base `S* = O_g⁻¹·W*`; FK controls level by level DOWN THE
  GAME SKELETON with each parent read live (robust to the `FKPS2*` point constraints, the finger SDK groups,
  `FKGlobalHead_M`); **`FKNeck_M` has no FKX joint under it** (the neck in-between drives `FKXNeck_M`) - it is
  solved numerically, `bias`/share never written; IK ends from `K·S*` (`AlignIKTo*`), poles on the plane,
  IKToes by a relation plus a numeric finish (the SC handle is not rigid: 9.9° off by the relation alone);
  RootX_M from the pelvis; a half-blended limb's IK half keeps its non-member places from the IKX chain.
  **Onto a skeleton** (`skelsolve`): joint channels `R = RA⁻¹·L·JO⁻¹`, the euler nearest the current one.
- **Keys** (`keys`): the active layer = the selected non-base layer (several → the topmost, named), else
  BaseAnimation; a locked one is refused, a muted or zero-weight one is said; plugs are added to the layer; one
  undo chunk per press, autoKey off inside it.
- **The window** (`maya_poselib/window.py` + `cardgrid.py`, a workspaceControl `skeldarPoseLibrary` on the
  hub's pattern): folders, search (name, folder, character), sort, card size, **+ Save pose** (region chips
  pre-lit from the selection; Snapshot = a playblast of the active panel, square, controls/joints/labels hidden
  and put back), details with **Apply**, **Mirror**, **Blend** (the slider, or a middle drag across a card;
  previews unrecorded, keys on the release, Esc puts every value back), **Select objects**; the right button
  (Apply, Apply mirrored, Select objects, Rename, Move to…, Replace thumbnail, Update from selection, Show in
  Explorer, Delete). A card dragged onto a character in a viewport applies onto it; onto the empty floor it
  adds the card's source character there (a native skeleton is rebuilt bones-only, grouped) and poses it; onto
  a folder it moves there. Hub card **Pose Library** (Animation, icon `books`), hotkey row `window.poses`.
- **The install** keeps local poses CARD BY CARD against `poses/.shipped.json` (what each build shipped, with
  sha1s): a colleague's card is never merged file by file into a shipped one (a clash goes back beside it as
  «Name (local)»), a shipped card deleted or renamed upstream does not come back, a failure keeps the aside
  folder and says where. An open Pose Library is rebuilt after an install, like the hub.

Proof: `verify_poselib_solve.py` **109/109** and `verify_poselib_apply.py` **117/117** (mayapy standalone:
layers, undo in DG and parallel, the animator's tweaks, mirror, blend, partial cards, half-blended limbs,
Mixamo, a Biped, characters standing low and high, objects, the floor drop); `verify_poselib_gui.py` **50/50**
in a disposable GUI Maya on port 7031 (the window from the hub card, Save with a real thumbnail, search,
folders, drops onto a rig and onto the floor, the blend slider and the middle drag, Esc; pictures
`poselib_window.png`, `poselib_window_save.png`, `poselib_viewport.png`); 4595 unit tests. Not exercised: a
real OS mouse over the viewport, Alt+Tab mid-drag (proven with sent Qt events only). Not built: animation
cards, selection sets, bone translations below the pelvis, applying with the root, the IK spine, sending a
pose through Shared.

205. **`setKeyframe(plug, animLayer=L, value=v)` takes `v` as the plug's FINAL value** on an additive layer
     (it writes `v − base`, divided by the weight), on an override layer, and on BaseAnimation under an
     additive layer (measured 2026-10-02, mayapy). Without `animLayer` the key goes to Maya's own best layer,
     not the selected one; a plug not in `L` is refused with a warning (add it first); a LOCKED layer still
     takes a scripted key; quaternion accumulation (`rotationAccumulationMode` 1) breaks the per-channel
     arithmetic. `setAttr` on a layered channel works and holds until the next time evaluation.
206. **A same-frame `currentTime` re-evaluates every time curve in the scene**, so every unkeyed tweak on a
     keyed channel snaps back to its curve - on characters and props the press never touched. The pose
     library's first build "settled" with it: an Apply of a hand card threw away the animator's hand-posed
     body, and Esc after a blend "put back" the curve values. Every gate was green, because no fixture carried
     a tweak. An evaluation-manager switch (DG ↔ parallel) does the same. Dirty only what you changed
     (`dgdirty` the feeding nodes); where a re-evaluation cannot be avoided, record the plugs whose value
     differs from their curve at the frame and set them back through **MPlug** - a `setAttr` inside the
     press's chunk is replayed to the curve by its Ctrl+Z.
207. **Under the parallel evaluation manager a read after scripted `setAttr`s can go stale on a KEYED rig**
     (measured in a GUI Maya, 2026-10-03): `FKHead_M.parentMatrix[0]` read after the neck's numeric probes set
     `FKNeckPart1_M` came back 4e-4 and then 0.62 off, and the head landed 8-24° off in 16 of 16 trials, while
     an unkeyed rig read identically to DG. The solve runs under DG (`rigsolve.FRESH_MODE = "off"`, the mode
     put back after): the switch costs ~0.03 s and FLUSHES Cached Playback, which refills on the next
     evaluation (61 frames in 0.3-0.4 s).
208. **An install that restores a folder FILE BY FILE glues two things into one.** `keep_local` put back every
     file the new build lacked: a colleague's card at a shipped card's path got the shipped `pose.json` with
     its own thumbnail, and a shipped card renamed upstream came back for ever. Decide per unit (a `.pose`
     folder) against a manifest of what the previous build shipped.
209. **A "rest" mixed from two sources moves with the character.** `rest_world` answers the skinCluster's bind
     for a skinned joint and the CURRENT world for an unskinned one (Manny's `weapon_*`, `camera_*`), so with
     Main at y = -150 half the rest stood 150 cm away from the other half, recognize's floor rule read the root
     as no root, and the pelvis landed 245.9 cm over it instead of 95.9. One consistent rest per skeleton: an
     unskinned joint below the top rests at its parent's bind, an unskinned TOP joint at its bind pose
     (`dagPose`) - never through a descendant that moves against it: taken from the pelvis, an unweighted
     root followed a crouch and the whole card landed turned 30°.

**The card under the mouse grows twice its size** (2026-10-03, the animator: «при наведении на карточку позы
в библиотеке поз наша карточка увеличивалась в двое»; asked, all three the recommendation: over its
neighbours, at once and eased, new thumbnails at 640 px). Spec
`docs/superpowers/specs/2026-10-03-pose-card-hover-zoom-design.md`.
- **Where** (`look.zoom_rect`, pure): the card's tile (square + name strip) grown `ZOOM` (2) times about its
  centre, then moved inside the viewport's visible part of the canvas (`CardCanvas.view`) less `ZOOM_MARGIN`
  (6); a card already closer to the edge than the margin (the grid's first column touches the pane) grows
  flush with that edge, so the grown card always holds the card's own tile and the mouse stays on it; a
  viewport too short for 2x shrinks the factor (never below 1). Computed at paint time: a scroll or a resize
  mid-zoom needs nothing.
- **When** (`look.Zoom`, one per card while lifted, by PATH): eased out from where it stands, `ZOOM_IN_MS` 140
  growing, `ZOOM_OUT_MS` 180 shrinking; at once with ⋮ → Interface animations off (`cardgrid._animations`).
  A 16 ms `zoom_timer` runs only while one moves, each tick repainting only `_reach` (own ∪ grown tile + the
  shadow).
- **Drawn**: everything at `z` (radius, outline, fonts, chip), on a plate of the canvas colour with a soft
  drop shadow, the picture read at twice the card's side (`zoom_side`, kept by `fit`'s cache); the cards
  shrinking under the one growing (`lifted_order`).
- **The mouse — always the card's PLACE** (the same day, after using it: «принимала решение о том какую
  карточку увеличить ... всегда на основе границ изначальной карточки. Сейчас бывает такое что одна
  карточка почти полностью перекрывает другую»): `index_at` is `look.hit` on the grid alone. The first
  build let the grown card keep the hover and take the presses wherever it covered a neighbour, so a
  neighbour was reachable only from its far half. Now the mouse onto a neighbour's place grows the
  neighbour even under the grown card; the one growing is drawn on top, so the card on top is the card a
  click, a drag, the right button or a middle-drag blend acts on; a gap between places grows nothing. A
  left drag starting shrinks the card (the ghost takes over); a scroll re-reads the card under the cursor;
  a re-read of the library keeps the hover by path.
- `capture.THUMB_SIZE` 640 (was 320; a 112 px card at 150 % is 336 px grown). Cards saved before keep their
  320 px picture; Replace thumbnail re-takes it.
Proof: `docs/superpowers/plans/verify_poselib_zoom.py` in a disposable GUI Maya (port 7043, scratch
`MAYA_APP_DIR`, `MAYA_NO_HOME`; Qt mouse events, no OS cursor) — **26/26 on the place rule**, plus its
`thumb` gate from the first build's run: 2x reached monotonically in 143 ms and back in 184 ms, the timer
stopping; the grown tile holding the card's own and inside the viewport (flush with its top-left corner
for card 0); a frame's repaint median 3.3-4.1 ms, p95 4.1-4.7 ms; DWM's copy of the window showing the
grown card's colour over its neighbour (`poselib_zoom.png`); the mouse onto that covered part growing the
NEIGHBOUR, a click there picking it, a gap growing nothing; a neighbour growing while the first shrinks,
drawn on top; a scroll; animations off at once; a real `capture.thumbnail` 640 x 640. Unit tests
`test_poselib_look` (`zoom_rect`, `zoom_at`, `Zoom`) and `test_poselib_cardgrid.HoverZoom`;
`verify_poselib_gui.py` 47/47 on the first build (its save gate now asks for `capture.THUMB_SIZE`); 4629
unit tests.

**The grid keeps one gap and one margin at every width** (2026-10-09, the animator: «отступы между
карточками плавают в зависимости от размера окна, это не верно давай сделаем их константными. Так же
нужно добавить отступы от краев окна интерфейса»):
- `look.grid` keeps `GAP` (8) between cards and rows and `MARGIN` (10) from all four edges. Until then
  the leftover width went into the gaps and the cards stood on the pane's edges.
- As many columns fit as cards of the slider's size do, and the cards of those columns share the room,
  like the hub's portrait grid. A card is at least the slider's size, less than one column more, and
  never past `CELL_MAX`. The room's last few px (fewer than the columns), and what `CELL_MAX` leaves,
  stay on the right.
- A card's place is a function of the width and its column, so a Save moves nobody.
- The card side now follows the pane by a px or two. So a picture is read at the next
  `cardgrid.CACHE_STEP` (8 px) and drawn into the card: dragging the splitter re-reads nothing.

Proof: unit tests — the gap and the margin at every pixel width from 60 to 1500 at three scales, the
slider as the least size, a resize reading no picture again; 5550 in all. An offscreen render of the
canvas at 300–640 px read the gaps 8 and the edges 10 (13 on the right at 640: 3 px five cards cannot
share). Not seen in a GUI Maya (the animator's live checks).

## The Pose Library: animation cards, Studio Library's paste modes, previews on hover (2026-10-03/09)

The animator: «теперь давай добавим возможность сохранять анимации. Все правила которые работают для поз
должны работать и для анимаций. Так же мы должны уметь выбирать способ вставки анимации как в studio
library. Карточки с сохраненной анимацией должны проигрывать превью этой анимации». Asked, all three the
recommendation: the clip's travel is carried **from where the character stands** (an «In place» box for
the pose rule); keys **on every frame** by default, «Source keys» as an option; the preview **plays on
hover**, the picked card's big picture loops. Then «Дальше делай все сам». Spec
`docs/superpowers/specs/2026-10-03-pose-library-animation-design.md`, plan beside it. Built in the worktree
`C:/!!!Work/MayaScripts-poseanim` (branch `feature/pose-animation`) by subagent waves, every task reviewed.

- **A card** is `<Name>.anim/` beside the `.pose` cards, in the same library and catalogs
  (`store.CARD_SUFFIXES`; a name is free only when neither suffix holds it): `anim.json` — the HEADER
  (the pose card's fields with `format: skeldar.anim`, `start`, `end`, `frames`, `key_times`, the bones
  STATIC only — parent, canonical, rest, rotateOrder — `members`, `regions`, `preview` grid), read by
  every listing; `frames.json.gz` — every bone's world on every frame as a quaternion + translation
  (`animdata.encode`, scale dropped) plus a rig's eight drives, read only by Apply/Blend/Update
  (`store.read_frames`, one cached entry); `thumbnail.jpg`; `preview.jpg` — a SPRITE SHEET of up to 60
  cells (every `step`-th frame), 320 px each, `ceil(sqrt(n))` to a row. The main file is written last; a
  replace keeps the files it is not given. An objects card keeps its curves in the header (keys with their
  tangents, cut to the range on a duplicate; a fed channel sampled in one time walk). The install keeps an
  `.anim` folder as one card unit exactly as a `.pose` one (`install.CARD_SUFFIXES`, `free_card`,
  `_rename_inside` by suffix).
- **Save** (`animcapture.build_animation`): the pose rules (one character → its bones; else objects),
  the static half read once at the current frame, the per-frame half in ONE time walk
  (`timewalk.Walk`: `MAnimControl.setCurrentTime` under `refresh -suspend`, the tweaks read first and put
  back, the time back); `key_times` from every time curve feeding the character's nodes (through
  animBlendNodes). The preview (`animcapture.preview`): the thumbnail's flags and settle, then ONE
  playblast of the sheet's frames, painted with Qt. A Save is no step on the undo queue; a cancel writes
  nothing; a preview that cannot be made (or raises) saves the card without one and says why.
- **Apply** (`animapply`), per target, in this order: the layer refusals; `animdata.paste_plan` (Replace /
  Replace all / Insert / Merge — Maya's `pasteKey` meanings, Insert moving the keys at or after the paste
  frame by the clip's length — At current time, a Range, Source keys); under ONE `Walk(fresh=True)` (one
  DG switch): the structure once (`posemath.Transfer`, the alignment fixed on the FIRST pasted frame so a
  non-twin cannot jitter; `rigsolve.Solver`; the pairing, scale, members), a dry solve at the paste frame
  (the plugs, the Connect offsets, the seed); a Blend partner read per frame; the mode's cut / shift on the
  ACTIVE layer's curves (`keys.curve_for`: `animLayer -q -findCurveForPlug`, falling back to the plug's own
  curve on the base), the curves' infinity and weighting saved (`keys.curve_state`) and given back after
  (`put_curve_state`) because **Maya deletes a curve a cut empties**; then per frame: the target re-read
  (`scene.refresh_world`), the card's frame decoded (`animdata.bones_at`, mirrored per frame), the travel
  (`Transfer.travel`: `Q·F·L·F·Q⁻¹`, scaled, reflected when mirrored) onto the root frame read at the
  paste frame, solved with the PREVIOUS frame's values as the euler seeds, Connect, the mix, keyed at that
  frame on the layer, measured. Main (rig) / the root joint (skeleton) carry the travel when the card holds
  the pelvis and all six channels are writable — else the pose rule and the line says so. One undo chunk;
  Esc undoes it whole. Floor drops add the source character there first (`apply.drop_floor(..., onto=)`).
- **The window**: a type filter [All | Poses | Animations], «+ Save» with [Pose | Animation] and a range
  (the slider's highlight, else playback; a name already taken in the folder is refused before the walk),
  an options block UNDER Apply / Mirror / Blend / Select objects, two to a row (Paste segments, At current
  time + Connect, Range, Keys + In place; remembered in `skeldarPoseLibrary*` optionVars, a missing one is
  its default) passed to every press of an animation card and never to a pose card; a «▶ 24» badge; the
  animation card under the mouse plays its sheet at the clip's own rate (`look.play_cell`) after a 150 ms
  dwell (a sweep decodes nothing), the picked card's big picture loops (resting at a 500 ms beat while Maya
  is minimised); «Replace thumbnail and preview» and Update write the card AT ITS PATH
  (`store.replace`), so a card renamed in Explorer is not doubled; a card just saved is shown (the type
  filter goes to All), or the line says the search hides it.
- **The final review's fix wave** (four lenses, three skeptics a finding): **an undo mark** — the press's
  first recorded step sets every planned plug to what it SHOWED when the press began
  (`keys.shown_at_start` / `undo_marks`), undone last, because Ctrl+Z replays the solve's temporary sets at
  other frames backwards (trap 215); **the walk ARRIVES** at the paste frame (`Walk.arrive`: no time set
  on the frame the scene stands on, trap 206) — Main dragged by hand to place the walk is where the travel
  starts, and coming back to that frame after a pre-pass (Blend < 100 %, a rootless target's grounds) it
  puts the entry tweaks back - on the paste's FIRST frame only (`arrive(..., restore=)`: an entry frame
  mid-paste read with its tweaks keyed a one-frame spike); **a rootless clip's heading steadied** past 120° of swing
  (`posemath.steady_yaws`, `clip_roots`; trap 216) — and a rootless TARGET takes off the same steadied
  heading it is given (`Transfer._steadied`), or its body turned up to 180° at the inverted frames (the
  first fix did exactly that; a second review caught it); **In place onto a rootless target reads its
  ground before the ops** (its top joint is a member the press rewrites) — at every pasted frame under
  Replace / Merge, at `a` under Insert (where the shifted take resumes); an exception inside the chunk
  undoes it, and only what the press recorded; a cancel with undo off keeps and names, with true counts,
  what it keyed and cut; breakdowns land as breakdowns; Esc during the preview's playblast writes nothing;
  `keys.cut` / `shift` count what a curve really lost (a referenced curve changes nothing); the save
  panel's auto name follows the folder picked while saving.

Proof: `verify_poselib_anim.py` **113/113 mayapy standalone** (capture exact; a twin rig 0.0011 deg, the
travel 0.000000 cm over 134 cm; the four modes on the base and on an additive layer, deg and cm; Connect
bound to twice the solve's own measured dependence, Source keys, a sub-range; Creep_Rig / Orc_D_Rig 0.018
deg pointing; mirror, the pelvis offset with an unmirrored control; Blend halfway 0.0009 deg; objects
tangents 1.3e-15; one Ctrl+Z with autoKey ON; Mixamo travel; the floor drop on the point 0.000000 cm; and
the fix wave's three, each with the pre-fix code patched in as its control: a hand-dragged Main 0.000000
against 170 cm, one Ctrl+Z after Merge / Replace off the current frame 0 of 1408 channels off against 180
off (34.95° on `FKHead_M`), In place onto a walking Mixamo target 0.000000 against 12.69 cm; and the
second review's: a Mixamo roll over its hips onto a rootless twin, with the travel and In place, 0.000000°
against 180°, Insert In place onto the walking target 0.000000 against 75.39 cm, a left-leg Blend 50 % over
a hand-dragged RootX_M every first key as shown against 10.78 cm);
`verify_poselib_anim_gui.py` **75/75 in a disposable GUI Maya** (port 7051) BEFORE the fix wave: the save's
5×5 sheet whose cells each match their own frame, hover playback 17 cells in 0.76 s at 2.3 ms a paint, the
options read back, Insert onto a second rig, a drag onto the floor, Replace onto a third, one Ctrl+Z with
autoKey on under the parallel EM; pictures `poselib_anim_*.png`. **Its post-fix version (Apply in view at
the default size, the dwell, a sweep decoding nothing) has NOT run** — the animator keeps the live checks.
Speed: **0.18-0.25 s a frame onto a rig** (0.197 in the GUI), 0.04-0.07 onto a skeleton, 0.03-0.05 to
save. The pose library's own verifies stayed green (apply 117/117, solve 109/109); 5459 unit tests on
the merge.
An intermediate build went out at the animator's ask before the second review's fixes (`d35cc13`).

Limits, measured and stated: a non-twin cannot follow a card whose child wanders in its parent's frame
(Manny_Rig's neck_02 against the head, 0.32 deg); a mirrored paste onto a non-twin carries the card's own
first-frame left/right asymmetry (0.29 deg at the neck); a rig solve depends on its start pose by 0.0012 deg;
a rolled clip onto a NON-twin rootless target whose top joint pairs with another source bone (a Biped's
`Bip001` over its `Pelvis`, onto Mixamo's `Hips`) can still turn near upside down by those two bones'
heading difference (found by the last review, as it was before the fix wave);
pasted frame for frame across frame rates (the line says so). Not built: retiming, several clips at once,
sub-frame keys, the IK spine, bone translations below the pelvis.

210. **Maya deletes an animCurve that a cut empties** — plain, base or layer curve alike (`objExists`
     False after `cutKey`). The plug keeps whatever the DG last evaluated and the next `setKeyframe`
     makes a NEW curve with Maya's defaults: a Replace that empties a cycled channel loses its infinity
     and its weighting. Read the curve's settings before the cut, give them back after the keys.
211. **`animLayer -q -findCurveForPlug` answers a LIST, None for a plug the layer holds but has no keys
     for yet, None on BaseAnimation for a plug keyed plainly in a layered scene, and RAISES with no layers
     at all** («A single anim layer node must be specified»). And `setInfinity` on a curve NODE sets
     nothing (its flags are `-preInfinite/-postInfinite`, its query answers None): write the curve's own
     `preInfinity` / `postInfinity` attributes.
212. **A `cmds.autoKeyframe` switch is a step on the undo queue even when it sets the state autoKey
     already has** — so a tweak restore after a press's chunk took the animator's Ctrl+Z (one undo left 192
     curves changed, the second turned autoKey off). `MAnimControl.setAutoKeyMode` is no step and
     `autoKeyframe -q` reads what it set. And with autoKey ON an `MPlug` set of a keyed channel does not hold
     — the tweak restore turns autoKey off through the API around its sets.
213. **A floating Qt window hidden with its minimised Maya gets no hideEvent**: `isVisible` stays True,
     `isExposed` False, Win32 `IsWindowVisible` False — a 33 ms timer drew on for nothing. Ask Windows from
     the widget's own `effectiveWinId()`; a `windowHandle()` wrapper of a Maya widget came back DEAD on the
     first tick after a rebuild (trap 96's family).
214. **`getAttr(plug, time=)` read a prop held by an IK hand 1.25e-4 cm off** when consecutive context reads
     carried the chain's state from one to the next (trap 69's family): an objects card's fed channels are
     read in one real time walk.
215. **Ctrl+Z replays every recorded step of a press, the ones at OTHER frames too.** A paste walks the
     frames and its solve sets channels temporarily at each one, inside the press's chunk; undoing the
     chunk replays those sets backwards, so a channel the press did not cut or move (Merge, or Replace
     with no key inside the pasted range) ended holding what it was set to at the FIRST pasted frame -
     180 channels of a rig showed frame 0's pose at frame 100 after one Ctrl+Z (`FKHead_M` 34.95° off),
     until the next key or autoKey wrote it in. Every gate had pasted at the current frame. Make the
     chunk's FIRST recorded step a set of every planned plug to the value it showed when the press
     began: the last thing the undo undoes puts that value back.
216. **A swing-twist heading is ill-conditioned near upside down.** A rootless clip's travel read each
     frame's heading off its top joint's yaw; a hips forward roll (360° about X, ±2° of side tilt, no
     turn) read -7.5, 15.1, **180.0**, -15.1, 7.5 at the inverted frames, and Main was keyed spinning
     while the pelvis stayed exact - a gate on the bones could not see it. Past 120° of swing the yaw
     is taken from the frames on either side (`posemath.steady_yaws`). And the noise had been cancelling
     itself: a rootless TARGET took off its own per-frame heading and put the ground's back, so steadying
     only the ground turned a twin's whole body by the difference (180° at frame 12, measured). Whatever
     a frame's heading is replaced by, it must be replaced by on both sides of the transfer.

253. **`cmds.playblast(frame=[list], filename=base)` numbers its images by their PLACE in the list, not
     by frame** (measured 2026-10-15, Maya 2027: frames 5..39 wrote `base.0000..0034`). The animation
     card's preview read them by frame, so every clip not starting at 0 with every frame kept (a range
     from 5, anything over 60 frames) was saved «without a preview: the playblast wrote 30 of 35
     frames» and never played on hover - the animator's «previews don't always play». The test fake
     had encoded the same wrong naming. `animcapture.preview` pairs the images with the frames in
     order. A card saved before keeps no preview: right-click → Replace thumbnail and preview.

## The Pose Library: compact, Selected only, toned cards, a blend that holds (2026-10-15)

The animator: «1 - более компактный интерфейс. 2 - опция применить наложение только на выделенные
объекты ... 3 - Превью поз должно быть оранжевым, а превью анимаций приятно холодно голубым. 4 -
ручка blend должна оставаться на своем месте ... ключ должен ставиться только по нажатию apply.
Если мы изменили таймлайн или куда-то переключились то пусть бленд сбросится на 0». Asked, all the
recommendation: Selected only keys only the selected nodes; Apply at blend 0 keys the whole card. Spec
`docs/superpowers/specs/2026-10-15-pose-library-compact-selected-blend-design.md`. **This replaces
what the sections above say about the blend keying on release and about the window's header row.**
- **Compact**: one top row (search, type, sort, size, + Save, ⋮ - the folder is ⋮'s tooltip and
  first menu row, `path_label` hidden, no title); margins 4; the details picture 150 px; Select
  objects an icon beside Apply; Mirror + Selected only one row; the paste options' three checks on
  one row, Keys beside its segments; the side panel at least what its content needs (`_fit_side`).
- **Selected only** (`skeldarPoseLibrarySelectedOnly`, off): `apply.apply` / `Blend.start` /
  `animapply.apply` / `animapply.Blend.start` take `only=True` (off: the call they always made).
  The WHOLE card is solved, then only the selected transforms' plugs kept (`selected_nodes`,
  `keep_selected` pure, `only_selected` says «Selected only: 1 of 73 controls keyed»); nothing
  measured when the cut left members part-keyed; none of them in the card is refused before any
  chunk. Drops ignore it (they name their character).
- **The backdrop**: a pose's picture is SHOT on orange, an animation's on blue -
  `capture.backdrop(kind)` sets `displayRGBColor background/backgroundTop/backgroundBottom`
  (`BACKDROPS`) and the gradient off for the blast, everything put back; `thumbnail(kind=)`, the
  preview sheet (`animcapture._blast`) on blue, the save panel shooting again when its type
  switches. The first push (bf7d386) recoloured the cards at paint time instead - «не закрашивать
  всю карточку каким-то оверлеем» - and that overlay is gone. Old cards stay grey until Replace
  thumbnail. **And a studio light** («Добавь красивый градиент на фон или студийный свет»): a
  playblast cannot draw a gradient, but its PNG keeps the background transparent - the blasts are
  PNGs now and each is laid over `capture.studio(qt, image, kind)` (a radial light above the
  middle, the colour, dark corners, a faint floor glow; `studio_stops` pure); an opaque blast
  shows the flat colour as before. Not seen in a live playblast.
- **The blend holds**: let go (slider or middle drag), the preview stays («Blend 40 % - Apply keys
  it», Apply reads «Apply 40 %»); Apply keys it (`blend_key`) and the slider goes to 0; back to 0
  with every value back (`blend_reset(why)`): a `timeChanged` job made only while a blend stands
  (reset one idle later), `follow` (selection, undo, redo, scene opened), another card, Mirror /
  Selected only / a paste option, the window hidden, Esc, a drop. A lost release keeps the
  preview. No keyboard grab.

Proof: `verify_poselib_selected_only.py` **13/13 mayapy standalone** (FKWrist_R alone at the whole
solve's value to 0.0, two controls alone, a refusal keying nothing, a 50 % blend on one control
exact, an animation onto FKElbow_R alone equal to the whole paste's to 1.6e-5, a skeleton's hand_r
alone); 6526 unit tests; picture `poselib_compact.png` (offscreen). Not seen in a live Maya.

## Physical stop: a pose-to-pose transition that stops like an object (2026-10-10) - the Tail Builder card

The animator, with a cube animated by hand in their open scene: «нужно изучить анимацию кубика и сделать
математическую модель построения подобных анимаций ... скрипт берет два последних ключа ... амплетудность,
сила захлеста (отставания) верхней части от нижней, вес ... время овершута ... имитирует физичную остановку
объектов». **A script SEPARATE from the plugin first** («после того как все настроим вмонтируем его в сам
плагин»): `docs/superpowers/plans/physstop/skeldar_physstop.py`, one file, dropped into a viewport (or exec'd)
it opened its window. Spec `docs/superpowers/specs/2026-10-10-physical-stop-design.md` (read its addendum),
plan beside the folder.

**In the plugin since 2026-10-12: the hub card Tail Builder** («Давай добавим в наш плагин вкладку с этим
инструментом ... Tail Builder»). The script moved whole (`git mv`) into **`SkeldarAnim/maya_tailbuilder.py`**
and the drop-in file is gone. Its four layers stay: the model (stdlib), the geometry, the scene, and the
card (`build_panel`) where the window was.
- **The hub**: section `tailbuilder` («Tail Builder»), Animation, after Tools, Tabler icon `wave-sine`. It
  is a payload row.
- **The card**:
  - the subtitle follows the selection: «cube: A at 0, M at 5, B at 10», «a tail 0-28, M at 5, B at 10»,
    or the refusal;
  - the three sliders;
  - **Apply** (primary; its tooltip is the old intro), **Restore keys**, **Reset**;
  - the three-line status, also told to the hub's line;
  - a SelectionChanged job per card, hub and popup copies alike (the Tools card's pattern).
- **The presses are module functions**. With the card closed they read the remembered values, so the
  hotkey rows work: `window.tailbuilder`, `tailbuilder.apply`, `tailbuilder.restore`
  (`maya_hotkeys._tailbuilder`).
- **The scene marker `skeldarPhysStop` and the optionVars `skeldarPhysStop_*` keep their names**: tails
  already in scenes and the values set in the standalone window carry over.
- The dev tools stay in `docs/superpowers/plans/physstop/` and load the plugin module:
  `verify_physstop.py` (31/31), `calibrate_physstop.py` and `cube_reference.json`. The tests are
  `tests/test_tailbuilder.py`, 61 of them, with the card on a fake cmds.

**What the cube is** (read over the port, nothing written; `physstop/cube_reference.json`): its BOTTOM was
keyed at extremes with flat tangents (a smoothstep over 10 frames to 0.85 cm past the target, -0.95, +0.32,
still at f24); its TOP lags like a spring driven by the bottom's velocity (tilt back to 24 deg, -7.4, +7.6);
it SINKS like the same spring driven by speed (-3.1 cm at f7); it sways left 1.25 cm with 5.7 deg of yaw.
Overlap and weight are one rule: speed loads springs, braking releases them.

**The model** (answered in the brainstorm: B stays at its key and the settle comes after; "overshoot time" is
ONE swing, weight is how many; a rigid object; sway a parameter; keys on every frame):
- the path `p(t)`: `3u^2 - 2u^3 + m(u^3 - u^2)` from A at rest through B at B's key with speed, then
  `1 + (vB/w) e^(-sigma tau) sin(w tau)`, `w = pi/swing`, `vB` set by the first overshoot; channels lerp by p
  (eulers too - a 350->370 spin stays a spin);
- three springs (damped period 2 swings, damping `0.30/weight`) driven by the bottom's speed in object
  heights per frame: tilt about the bottom against the motion, sink down, sway left (slower, with yaw);
- the end: every residual within 2 % of its peak, the last 30 % faded, the last key exactly pose B;
- the geometry: up axis = the local axis nearest world up; bottom = the low end of the shapes' box; the
  world result decomposed back into translate/rotate through the parent and the transform's own pivots,
  shear and rotate axis (`X^-1 L = R . Tr(rp + rpt + t)`).

**Three poses since 2026-10-12** (the animator: «давай попробуем сделать не две позы а 3 задача
промежуточной позы определить арку входа в овершут и силу захлеста ... улучшить найминг парамметров»; asked:
M is a key hit exactly at its frame, three poses only). Spec
`docs/superpowers/specs/2026-10-12-physical-stop-three-poses-design.md` (its two addenda). **This replaces the
two-pose source, the Overlap slider, the sink and sway springs and the Side sway / Up axis controls above**:
- **The source** is the last THREE key times on translate/rotate: A (from), M (the breakdown), B (to).
  Fewer, or two less than a frame apart, is refused by name.
- **The timing** `p(t)` is a clamped cubic Hermite spline through (tA, 0), (tM, s_M), (tB, 1): at rest at
  A, `vB` at B, at M the slope that keeps the curvature continuous. The slopes are held to Fritsch-Carlson's
  `[0, 3 x secant]`, so the object never runs backwards and hits M exactly at its frame. Past B it settles
  as before.
- **The arc**: the bottom runs on the parabola through its places at A, M and B, parameterised by the
  chords; `s` is the arc-length fraction, from a 256-sample table. Past B it runs along the arc's tangent,
  so the overshoot leaves the way the arc arrived.
- **Nothing moves the bottom off the arc** (the same day, after the first try: «если поднимаем то он все
  равно будет заходить в овершут снизу»). The speed-driven sink spring had held the bottom 1.3-3 cm under the
  arc right before B, so a raised M still came into B from below. The sink and sway springs are gone:
  - M sets how the object comes in: raised from above, lowered from below, aside from the side, level
    straight in;
  - it stands on B's height at B's frame, then goes on along the arrival (a raised M dips past B and
    comes back up);
  - Weight is how long it rings.
- **The lag is read off M**: `G = W_path(tM)^-1 . W_M`, a rotation about the bottom. It is spread in time
  by the tilt spring's shape, scaled to 1 at M (to its peak where the spring barely bends at M). Its axis
  is wherever M was posed: back, aside, twisted.
- **Exactly M**: what is left at M (numerics, a lag the spring could not carry) is pinned with a smoothstep
  bump, 0 at A, 1 at M, 0 at B. A, B and the settle are untouched.
- **The controls**: Overshoot, % (3), Swing length, fr (5), Weight (1). There is no up-axis choice: the
  object's axis nearest world up is used. The optionVars are `skeldarPhysStop_overshoot/swing/weight`; an
  older `_sway`/`_axis` and a memo's old keys are ignored.
- **Re-apply and Restore**: the marker holds tA, tM, tB, tE. A re-run reads M at tM and B at the last key,
  so editing those keys edits the poses. Restore keys puts the three keys back. A two-pose marker asks
  for Restore keys first, and Restore puts its two keys back.
- **The status line**: «cube: frames 0-28 | breakdown at 5: lag 17.8 deg back, arc bends 2.7 cm down-left
  | settles 19 frames after B» («straight in» for a level M).

Proof:
- `tests/test_physstop.py`, 53 tests:
  - the spline, the arc, the pin, the composition, the window;
  - M raised, lowered and aside coming in from above, below and the side;
  - the cube with M at frame 5.
- `verify_physstop.py`, **31/31 standalone**:
  - the cube rebuilt from its frames 0 and 5 and its final pose at 9: M exact to 3.6e-15, the tilt
    peaking at frame 7 at 23.3 deg (the cube: 8, 24.1). The bottom is 0.909 cm rms against the
    animator's cube and the top 1.106 (0.405 / 0.602 with the sink spring): the cube still came into its
    place 2 cm low as it passed it, and with three poses that dip is M's to set;
  - M raised 6 cm: +0.97 cm above B at 9, on B's height at 10, -0.47 at 11. Lowered: the mirror. Level:
    on the floor every frame;
  - a breakdown 15 cm aside: the bottom on the arc on every frame in 3D, the overshoot along its tangent
    0.00 deg off;
  - a breakdown tilted left lagging left;
  - the parented pivoted zxy prop to 4.4e-16;
  - the spin, the refusals, re-apply, one undo, Restore.
- `calibrate_physstop.py` prints the fit at the script's constants and the best on its grid. Damping 0.32,
  3 % and 5 frames are kept: travel 0.316 cm and tilt 2.34 deg rms, against 0.382 / 1.72 for the grid's
  edge (0.28, 2 %, 5.5 frames).

**The live try is the animator's**.

Not built:
- a chain, sparse keys, more than three poses;
- a constrained/IK parent (read it per frame with `getAttr(time=)`, trap 69);
- scale between the poses, angular speed as a drive;
- what becomes of `maya_overshoot.py` (off the shelf since 2026-09-08) beside Tail Builder.

219. **`cmds.xform(node, q=True, boundingBox=True, objectSpace=True)` answers the box in the PARENT's space**
     (the node's own transform applied): a 1-unit cube scaled 4 x 11 x 3 and turned read -3.98..5.98. The
     object-space box is the shapes' own `boundingBoxMin/Max` (carried in through their transforms for a
     group).
220. **Maya's viewport drop imports a .py by its stem ONCE** (`importlib.import_module`, then
     `onMayaDroppedPythonFile(obj)`): dropping the file again after editing it runs the OLD code from
     `sys.modules`. A dropped tool reloads itself in its drop handler.

## Tools: OverRig's Knots and Double knot, native (2026-10-12)

The animator: «В скрипте over rig ... есть несколько фичей которые я бы хотел реализовать в нашем
плагине. 1 то что находится во вкладке knots 2 что что во вкладке double knots. Давай заведем раздел
тул и реализуем такие же инструменты». Asked: Knot Offset finishes with a **two-step button** (not
OverRig's deselect scriptJob); knots come off through **Bake and Remove**; «делай все до конца».
Spec `docs/superpowers/specs/2026-10-12-tools-knots-design.md` (its first section is what each
OverRig proc builds, read through the obfuscated `BOVER_10_2_<md5>` helpers), plan beside it.

**Native, not a wrapper**: nothing of OverRig's MEL runs (the highlight is read through
`overrig.slider_selection`); ours are known by our attributes, so Bake / Remove never touch a knot
the animator made with OverRig itself. Package `SkeldarAnim/maya_tools/` (payload row):
`knotplan.py` (stdlib, pure: kinds, spans, attach keys, channel plans, sizes, bake order, the
lines), `knots.py` (the scene), `panel.py` (the card). Hub section **Tools** (key `tools`, last in
Animation, Tabler `tool`); hotkey rows `window.tools` and `tools.knot / knot_offset / knot_orient /
double_local / double_world / bake / remove` (`maya_hotkeys._tools`: the presses need no panel and
report in the viewport when the card is closed). New icons `tool`, `rotate`, `focus-2`, `stack-2`.

**The card**, as it stands after two rounds the same day (first «более компактным ... все кнопочки
одинаково важные ... сделаем выделение для всех одинаковое» - every button orange, Remove too, it
destroys nothing; then «скомпоновал все хорошо но не красиво. Давай сделаем два под раздела Knots и
Double knots ... кнопочки ... растягивать вместе с интерфейсом»): the subtitle («3 knots in the
scene, 1 pivot waiting»); heading **Knots** and one row Knot, Offset (reads **Finish** while a
pivot waits), Orient; heading **Double knot** and one row Local, World; a small gap; «Rotate order»
`[Object | XYZ | XZY]` (`skeldarKnotRotateOrder`, default Object: the knot takes its object's
order); one row Bake, Remove; the line. Every button is `primary` (the hub's one-orange-per-card
habit is broken here on purpose) and every row of buttons is marked **`fill`** - a new hub role:
`maya_hubqt._spread(row, scale, "fill")` lays the row's buttons over its whole width with equal
stretches (the segments' mechanism, trap 97, without the track: no insets, no background, the
button height, a 4 px gap) so they stretch with the card. The classic hub keeps their own widths. A
SelectionChanged job per card (hub and popup copies) refreshes the subtitle and the Offset button.
Not seen live: the stretched rows in the animator's dock (unit-tested offscreen at 320 px).

**Since 2026-10-13 the card is a LIST, and nothing is orange but a waiting Finish** (the animator:
«сделать все более понятно, разложить по разделам. Все кнопки не должны быть такими оранжевыми»;
four mockups shown - tabs, coloured blocks of tiles, a list with explanations, the old order
restyled - they chose the list, C). Spec `docs/superpowers/specs/2026-10-13-tools-card-list-design.md`.
This replaces the paragraph above and what the parent and aim tabs below say about rows and headings.
- **Three subsections, each a head that opens and closes its body** (`panel.SECTIONS`, `HEAD`,
  `BODY`; a head is the skin's new `subhead`: a chevron, the name bold, a muted hint on the right, a
  hairline above). **Knots** «drive with a locator»: Knot, Offset, Orient, Local ×2, World ×2, **Aim**
  (moved in: it is a knot kind) and the **Rotate order** of new knots (moved up from the bottom).
  **Parent** «motion kept»: Inside, To world, Swap, Across, then the caption «Across, pair by pair»,
  `Objects n | Targets n | ⇄` and `Rotate | Translate | Pairs` (Multiple across's press reads Pairs
  now). **Overlap** «on a new layer»: the three numbers side by side (a row of their names over a row of
  fields, the skin's new `columns`), the four chips, the press. Open / closed is remembered per
  subsection (`skeldarToolsOpen_<key>`; Knots open, the others closed at first); a head's press flips
  what ITS card shows (`toggle_section` asks its own body - the hub's card and a popup copy share the
  memory, not their state).
- **Every tool is a flat row** (the skin's new `toolrow`): its icon in the Animation group's blue
  (`TOKENS["tool_icon"]`), its name, and its explanation (`panel.HINTS`, ≤ 28 characters) muted after
  a name column (`hubstyle.ROW_NAME` 72 logical px), elided; the long OverRig story stays the tooltip.
  **A row that reads Finish (Offset or Aim waiting) is filled with the accent** - the card's only
  orange: `maya_hubqt.set_state(name, "wait")`, reached through the panel's one Qt seam `_light`.
- **«Selected knots»** - an inset under the subsections, always shown: a caption and one row `0`
  (Attach 0), `1` (Attach 1), Bake, Layer and Remove as a red trash icon; outlined buttons.
- The skin's additions are generic: `hubstyle.mark(..., hint=)` (`Mark.hint`); roles `toolrow`,
  `subhead`, `caption` (a small muted label that STAYS - a `note` becomes the header's tooltip,
  trap 226), `columns` (`_spread_columns`: any widgets share a row); `set_state` sets `skState` even
  before the marks are applied and `_apply_mark` paints what it finds. New icon `world`.
- The classic hub shows the same controls plain: a row is a left-aligned button with its name.
- Proof: unit tests (the card top down, roles, hints, the subsection memory, the waiting row; the skin
  offscreen: a hint after the name column and elided, the wait state's icon, a head's chevron,
  columns), 6318 in all; `docs/superpowers/plans/render_tools_card.py` draws the card offscreen from
  the builder's own calls with the skin's code and stylesheet at 150 % in the 510 px viewport
  (`tools_card.png`, both states). `verify_tools_card.py` gained the head click and the lit Finish -
  not run (live checks are the animator's).

**One set of rules for all five** (OverRig's double knots had no range or attach; ours do):
- refusals first, for every selected object, by name: nothing selected; riding a knot already (a
  knot itself CAN be knotted); a waiting pivot; no free channel; a free channel driven by anything
  but a time curve (a constraint, an expression, a driven key, an **animation layer** - not
  supported yet);
- the span: a highlight `[a, b)` gives `[a-1, b]` and `attach` keyed 0/1/1/0 at a-1, a, b-1, b
  (flat); else the whole take (playback ∪ the object's keys), attach 1 unkeyed - keyable either way;
- the object's free unconnected t/r channels are keyed at their values (recorded in
  `skeldarKnotKeyed`) so Maya's pairBlend keeps the object's own curves as input 1;
- the knot baked on every frame of the span (`bakeResults -simulation`, rotates euler-filtered,
  still channels plain), its temporary constraints deleted;
- the object follows through ONE constraint `-mo` skipping its locked channels (marked
  `skeldarKnotOf` = the knot's UUID); `attach` drives its weight and the pairBlend weight
  (`blendParentN`), the pairBlend in quaternion mode (Maya wires the object's rotateOrder into it);
- **Knot** `<leaf>_knot`; **Knot Offset**: a space `<leaf>_pivotSpace` rides the object, a red
  `<leaf>_pivot` in it waits (it rides the object while placed - OverRig's stood still in world),
  the span and order kept on it; **Finish** bakes `<leaf>_knotOffset` from the pivot's world track;
  **Knot Orient** `<leaf>_knotOrient` rides the position (a kept pointConstraint, translate locked)
  and drives the rotation only (`orientConstraint`); **Double Local** `<leaf>_dknotBase` carries
  the whole track, `<leaf>_dknot` under it drives (a key on it = an offset in the animated object's
  axes); **Double World** `<leaf>_dknotMove` has no rotation and carries the position,
  `<leaf>_dknotRotate` the rotation (turning the outer bends the animation about the pivot in WORLD
  axes);
- knots live in a locked `Knots` group (`skeldarKnotGroup`) inside the object's character group,
  else a world-level `SkeldarKnots`; Delete character takes them (our attribute prefix keeps them
  out of `deletion.strangers`).

**Measured before designing**: deleting a knot's constraint deletes Maya's pairBlend and
`blendParent1` and reconnects the object's own curves - so **Remove** is that delete plus cutting
our static keys (while still static, the value written back: trap 58) - every curve comes back
exactly. `bakeResults -preserveOutsideKeys` on a pairBlended channel bakes INTO input 1's curve
and leaves the constraint - so **Bake** is that bake over where `attach` > 0 (`knotplan.influence`;
an unkeyed attach above 0 = the whole take), then the constraint's delete; a knot on a knot is
baked first (`bake_order`).

Proof: `docs/superpowers/plans/verify_knots.py` **90/90 mayapy standalone** (a keyed prop under an
animated carrier, rotate pivot off its origin, zxy, a locked rz, free unkeyed channels; and a Manny
rig control): nothing moves at creation (0.000000 cm, 0.000002 deg) for all five; the knot on the
pivot; Knot +10 tx moves the prop 10 along world X; attach 0 the original; Remove restores every
curve exactly; one undo per press; Bake keeps the edit with nothing left; a ranged knot moves only
inside and its Bake leaves the outside **unbent at half frames** (0.000000); Orient +30 turns
30.000 deg with the pivot path fixed; Offset's chosen point rides the knot through a 90 deg turn;
Double Local's inner rx 30 turns the prop about its own X; Double World's outer ry 90 about world Y,
tx +5 shifts 5 along world X; refusals change nothing; a knot on a knot bakes inward; on
Manny_Rig's FKShoulder_R the game bone does not move, the knot in `|Manny_Rig_Character|Knots`,
Delete character takes it. `tests/test_tools_knotplan.py`, `tests/test_tools_panel.py`; 5934 unit
tests. **An independent review then found seven defects, all fixed and gated** (case L): Bake
euler-filtered the object's WHOLE rotate curves (a key at 300 far outside the knot became -60 - now
only the bake's own keys are made continuous, `knotplan.continuous_eulers`, from the key before
them, the other euler solution by the rotate order's middle axis); picking a base knot orphaned the
knot riding it (now ridden knots bake / go first); a whole-take span ignored the animation range and
the parents' keys (6.25 cm frozen outside a narrowed playback); an unevenly scaled, sheared or
mirrored parent drifted 0.4-0.8 cm (now refused, `uneven_parent`); every selection change walked all
locators (now our groups only); Bake left our static keys when the constraint was gone; deleting a
knot deleted the animator's nodes parented under it (now moved out to world first). **`verify_tools_card.py` (the card in a live Maya, buttons clicked through Qt on a sandbox
cube) is written and NOT run** - the live checks are the animator's.

Not built: knots on animation layers, OverRig's "smart object" tab (S_Knot), Knot Offset on
several objects at once, keys only on the object's keys (a knot is baked on every frame, as
OverRig's), default hotkeys.

221. **`bakeResults -preserveOutsideKeys` keeps the keys outside a range, not the curve.** A bake of
     [10, 29] on a curve keyed at 0, 20, 40 re-aimed key 0's auto tangent at the new key 10 and bent
     [0, 10] by **0.9 cm**; a curve keyed only INSIDE the range (the static key a knot sets at the
     current frame) lost its value outside entirely (**5.97 cm** - its new first key's value held
     by pre-infinity). Before a ranged bake insert a key one frame outside each end of every curve
     (`setKeyframe -insert` keeps the shape and pins its neighbours' tangents to fixed) and pin the
     edge key and its outer neighbour if their tangents are neighbour-made (spline, clamped,
     plateau, auto*). Gate it at HALF frames: integer frames hide a bent spline.
222. **In mayapy standalone a `currentTime` is an undo step, and it ends the redo queue.** A verify
     that walked the time slider between a press and its `cmds.undo()` undid the time change and
     read "undo does not bring the knot back"; a `redo` after a walk raised «There are no more
     commands to redo». Undo and redo straight after the press, measure after.
223. **A locked channel holds the object off its knot**: a knot's constraint skips it (OverRig's
     -st / -sr), so a turn that needs that channel cannot reach the object - on a zxy prop with rz
     locked, a local X turn of a double knot landed 6.1 deg off while the turns that only change ry
     were exact. A fixture proving a local turn needs every rotate channel free.
226. **The skin HIDES a `note`** - it becomes the card header's tooltip (`maya_hubqt._apply_mark`:
     `card.add_hint(...); widget.setVisible(False)`), like `context` and `status`. The compact Tools
     card named its rows with `note`s («Knots», «Double», «Order») and in the animator's hub they
     never showed - three rows of unexplained buttons («скомпоновал все хорошо но не красиво»), while
     every unit test passed on the fake `cmds`. A label meant to be SEEN carries no role (a plain
     text) or `heading`; read what a role does in `_apply_mark` before choosing it.

**The parent tab** (the same day: «Теперь давай реализуем весь функционал из вкладки parent»;
asked, all the recommendation: re-parents refuse rig controls and bones, Across is a knot inside
the parent with Connections' BakeAcross left as it is, multiple across a block in the card). Spec
`docs/superpowers/specs/2026-10-12-tools-parent-design.md`, plan beside it. Two subsections more in
the card - **Parent** [Inside | World | Swap | Across] and **Multiple across** [Objects n | Targets n
| Swap] / (Rotate) (Translate) [Across] - and an **Attach** [0 | 1] row above Bake / Remove; every
button orange, every row `fill`.
- **Inside / World / Swap** (`maya_tools/reparent.py`, OverRig's `apply_Parent_in / _out /
  apply_Swap_parent`): each moving node keeps its world motion on every frame - a temporary
  locator takes its world track (`parentConstraint` with NO offset: pivots matched), the DAG
  moves, the node is constrained back to its locator with no offset (an offset captured after a
  move reads the old curves in the new space) and baked, the locator goes, only the baked rotate
  keys made continuous. Always the whole take (playback ∪ animation range ∪ the keys of the moving
  nodes and of their old and new parents' chains) - OverRig baked only a highlight and left the
  curves outside it in the old space. The world scale crosses the move as well (below; OverRig cut
  the scale keys and hid scale and visibility, not copied). Swap is OverRig's rule: all to world,
  the others under the last selected, the last under the former parent of the one before it
  (`knotplan.swap_plan`; select the parent first, then its child). Refused before any change: a
  bone, a control of an AS rig (its
  namespace, or under its group in the root namespace), the plugin's own nodes (deletion's
  `OUR_ATTR_PREFIXES`, pinned equal), a knot rider, locked or driven translate / rotate, an uneven
  new parent, a scale channel locked or driven by anything but a time curve while the parents'
  scales differ, a cycle, already there.
- **Across**: a knot kind `across` (`<leaf>_across`, teal) created as a DAG child of the target,
  baked from the object's world track (its keys in the target's space) - the rest is a knot's:
  pairBlend, `attach` and a range, Bake / Remove. It lives outside the Knots groups, so every across
  knot is a member of an objectSet marked `skeldarKnotRegistry` (`SkeldarAcrossKnots`, gone with its
  last member, trap 18) - `knots()` reads it. A target may be a rig control or a bone (a cup in a
  hand); the object is refused when it is its own target or the target lies inside it.
- **Multiple across**: Objects / Targets remember the selection by UUID on `sys` (trap 111) and show
  their counts; Across pairs them one to one (`knots.create_across`), refused when empty or of
  different lengths; Rotate / Translate (chips, `skeldarAcrossRotate` / `...Translate`) off skip that
  half in the follow constraint and do not key it.
- **Attach 0 / 1** (`knots.set_attach`): the selected knots' attach keyed (flat) at the highlight's
  ends, else the selected graph keys' first and last time, else the current frame.
- Hotkey rows `tools.inside / world / swap / across / attach_0 / attach_1`.
Proof: `verify_parent.py` **42/42 mayapy standalone** - Inside / World / Swap keep every integer
frame's world track (0.000000 cm), the hierarchy as asked, one undo; ten refusals change nothing (a
Manny control among them); Across: nothing moves, the knot inside the target and the registry, the
target's move takes the prop along, Bake keeps it and empties the registry, Remove restores, a range
rides only inside; Multiple across with Rotate off keeps the prop's own rotation while it follows
its target's move; Attach at a frame, a highlight, selected keys; a cup riding Manny's FKWrist_R
goes with Delete character's knot, the cup kept. `verify_knots.py` 90/90 again; 6032 unit tests.
`verify_tools_card.py` gained an Across press (still not run - the live checks are the animator's).

**…and the scale of a keyed object** (2026-10-13: «В панеле tools во вкладке Parent скрипты не
работают если на объектах уже есть ключи»). The line read «has scale keys and its new parent is
scaled differently»: the **S key keys scale too**, so every keyed object under (or out of) a scaled
parent was refused. Reproduced headless before anything else - plainly keyed objects, stepped and
weighted keys, the parallel EM all worked; only scale keys plus a scaled parent, and a channel on
an animation layer, refuse. The fix carries the world scale instead of refusing
(`reparent._scale_plans` / `_carry_scale`, the pure half `knotplan.scale_plan`, `carried_scale`,
`scale_refusal`):
- each node's old parent's world scale over its new parent's (the mean axis length), read BEFORE
  the move. One value when nothing in the parents' chains animates scale (a constant curve, what S
  leaves, counts as still), else one per frame of the span (one `timewalk.Walk`, unrecorded);
- **one factor**: the scale curves `scaleKey`ed by it (they stay keys, exact between frames too); an
  unkeyed channel is what Maya's `parent` already compensated;
- **a changing factor** (a parent's scale animated): every frame of the span keyed with the old local
  value times that frame's factor (a still result a plain value);
- done right after the DAG move, before the t/r bake: a Swap child's space reads its moved parent's
  scale;
- refused, by name: a scale channel locked or driven by anything but a time curve when the factor is
  not 1.
Proof: `verify_parent.py` **49/49** - new case S (prop and carrier keyed with S, the carrier at 2):
Inside keeps the whole world matrix on every frame (7e-15), the prop's three scale keys stay three,
halved, the scale exact at half frames (4e-16); one undo; World out of it back to 1; a carrier scale
animated 2 → 3 keyed on every frame, the matrix kept; a locked scaleY refused. 6335 unit tests.

**The aim tab** (2026-10-13: «Теперь давай реализуем функционал AIM»; asked, all the
recommendation: both tools, Aim in two presses, Overlap on an additive layer). Spec
`docs/superpowers/specs/2026-10-13-tools-aim-overlap-design.md` (what OverRig's `make_aim_from_selected`
and `execute_overlap_command` build, read from the MEL), plan beside it. Two subsections more in the
card - **Aim** [Aim] (reads **Finish** while an aim waits) and **Overlap** (Softness 2 / Lag, fr 1 /
Easing 0 as named float fields; chips Hierarchy (on), Cycled, Total lag, Keep edges; [Overlap]), all
remembered (`skeldarOverlap*`); hotkey rows `tools.aim`, `tools.overlap`. OverRig's `desel` (its
deselect-triggered build) is not copied: Finish is the second press.
- **Aim** (`knots.begin_aim` / `finish_aim`, the `aim` kind): the first press puts, per selected
  object, a space riding it (`<leaf>_aimSpace`, marked a waiting space of kind `aim`,
  `skeldarKnotPendingKind`) holding `<leaf>_aimTarget` along its X and `<leaf>_aimUp` along its Y,
  four knot sizes out, rotation locked; the second press (the aims the selection names, else every
  one waiting) refuses a target on the object or an up on its line (3°), then builds a group
  `<leaf>_aim` (the knot's top, at identity) holding the target and the up baked from their world
  positions (translate only, marked inner) and `aimConstraint -mo` with the vectors read off the
  placement in the object's own axes (so the offset is the identity), `worldUpType object` on the
  up. Maya names the aim's pairBlend weight `blendAimCnstraint1`; the knots' attach wiring needed
  nothing new. Bake, Remove, Attach as on every knot; Remove on a waiting aim drops its space.
- **Overlap** (`maya_tools/overlapplan.py` numpy and pure, `overlap.py` the scene): OverRig's
  construction (a joint chain, a locator ahead of each joint by softness x the next distance,
  aimed at, its keys shifted later by the lag, top to bottom) COMPUTED from the members' sampled
  world frames - no rig, constraint or bake: the member's track before its aim `P_i = l_i · C_{i-1}`,
  its target and up read from `P_i(t - lag)` (Catmull-Rom; cycled wrapped), the root's smoothed by
  a Gaussian of softness x easing frames, the new frame's `d` on the target and `u` leaning to the
  up. Chains: Hierarchy - each selected root and, step by step, the one node of its kind below
  (through FKX joints and offset groups; a branch ends it, said); off - the selection. One time walk
  per chain (`timewalk.Walk`), the window widened by the chain's whole lag; the new frames turned
  into `rotate = RA^-1 · local · JO^-1` deltas (nearest the base euler) and, for a member not
  parented under the one above, translate deltas; Keep edges multiplies by a smoothstep ramp 0 at
  the ends; written as `final - base` on the layer curves of a new additive layer `Overlap`
  (marked `skeldarOverlap`, rotation accumulation by component), zero one frame outside a
  highlight, cycled curves cycling; a second press takes the members out of our earlier layers
  first (replaces). One undo chunk.
Proof: `docs/superpowers/plans/verify_aim_overlap.py` **57/57 mayapy standalone** - Aim: the
target rides the prop, nothing moves at creation (0.000002°), the target moved turns the prop onto
it (0.00000° off, turned 80°), the up rolls it (90.7°) still aiming, attach 0 the original, Remove
exact, Bake, undo of each press, a range only inside, refusals, a Manny head; Overlap on a keyed
joint chain: the base curve untouched under the layer's blend, **the root delayed by exactly the
lag (0.000000°)**, the tip peaking 13 frames after the root, lengths kept, refusals, keep edges
exact at both ends, cycled curves and frame 0 looking back round the end, a second press replacing
the first, one undo, a highlight only inside, the selection mode, a loose chain's positions
following, a knotted member refused, Manny's FKIndexFinger1_R chain (through its FKX joints) moving
the game finger 48°. 6145 unit tests (`test_tools_overlapplan.py`: the model, OpenMaya's euler
convention, the root delayed exactly, cycled, easing). The live card is the animator's to try.

**Layer: everything that animates an object, baked onto an additive layer** (2026-10-13: «Теперь
давай реализуем функционал запекания на адитивный слой»; asked: **any object**, whatever drives it,
a **new layer per press**, a third button **Bake | Layer | Remove**; after using it, «я выделил
объект на котором просто ключи нажал леер и он не запекся», asked: **everything onto the layer, the
base a still pose**; then «чтобы она переносилась по ключам и мы их не теряли»: **the object's own
keys move as keys**). Spec `docs/superpowers/specs/2026-10-13-tools-bake-to-layer-design.md` (its
three addenda). OverRig's `>layer` bakes onto an OVERRIDE layer `BakedAnim`; Maya's own `bakeResults
-destinationLayer` into an additive layer doubles the motion (measured). Ours: the object's keys, its
knots and its constraints all go onto a new ADDITIVE layer `Baked_<leaf>` (marked `skeldarBakeLayer`
= the leaves, rotation by component), the base keeps the pose of the span's first frame: mute it and
the object stands, weight it to blend, delete it to drop the motion. `maya_tools/layerbake.py`
(`bake(selection, highlight)`; the pure half in `knotplan`: `driver_kind`, `driver_refusal`,
`undriven_refusal`, `layer_deltas`, `anchored`, `bridged`, `layer_message`); hotkey row
`tools.bake_layer`.
- **What the selection names**: an object, a constraint (its object), or since 2026-10-15 a knot
  ITSELF (below); a waiting pivot is skipped and said.
- **Its drivers, classified before anything changes** - the constraints feeding its t/r directly
  or through Maya's pairBlend (input 2):
  - our knot (`skeldarKnotOf`): off as Remove takes it, riders first;
  - the Retarget's (its `nodeState` on a `disableConstraints`): refused;
  - another card's: the constraint marked with our prefixes (Connections' link, the stretch
    follow), the object a weapon / armor space, or a JOINT following a `mayaWeapon` /
    `mayaSceneSetupCamera` target - refused («undo it in its own card»). A prop the animator
    constrained to the sword is the animator's;
  - the rig's own (the constraint in a rig's namespace; a root-namespace rig: the object and every
    target under its group or skeleton): refused;
  - anything else: baked and deleted.
  Its base: each channel's base plug reached through pairBlend input 1 and any layer's blend input A
  (`_base`); a base curve that moves is the object's own keys. An object with no keys of its own, no
  knot and no constraint is refused («nothing animates X»; or by what does drive it: an expression,
  a driven key; or «its animation is on layers already» - a second press); base keys from a reference
  are refused; a refusal of any object refuses the whole press, nothing changed.
- **The span**: the highlight `[a, b)` as `a..b-1`, the layer zero at `a-1` and `b`; else per object
  the take with the keys of the object, its parents, its constraints' targets (and theirs) and its
  knots.
- **The object's own keys move as keys** (`_sorting`):
  - over the whole take, a channel only its own keys move: the base curve NODE itself is moved onto
    the layer (`_move`: off the base, onto the layer's blend input B, shifted by its first-frame
    value, which the base holds) - every key, tangent, weight and infinity kept, exact between
    frames (measured: the layer finds it as its own curve);
  - under a highlight, a plain channel's keys inside it move exactly (`_bridge`): the base gets a key
    one frame outside each end (inserted, it and its outer neighbour pinned - trap 221), the keys
    between are cut, and the layer takes the original's keys there with values and in / out slopes
    less the bridge's (`knotplan.bridge_keys`), fixed tangents written as angles (tan = UI units a
    frame, measured at film / ntsc / 60 fps); all-stepped keys move as they are over a still bridge;
    weighted or mixed-step curves go on every frame (`bridge_kind`);
  - a channel a knot or constraint drives has no keys of its own and is keyed on every frame (keying
    a constraint only at its targets' keys lost a two-turn spin between two keys).
- **The press**, one undo chunk: a time walk reads every object's t/r values (the current frame
  too); the drivers come off; the base's own animation comes off (`_clear_base`) - the whole take:
  each moving base curve (not the ones moved whole) deleted, those channels and the driven ones set
  to a value; a highlight: each moving curve bridged, an unkeyed channel a foreign constraint drove
  held at the current frame's pose (trap 238, said); a second walk reads what is left (the base plus
  the animator's other layers, untouched); per frame `shown - left` for the channels read off the
  scene, the shown rotation made continuous from what is left and then from the frame before
  (`knotplan.layer_deltas`: the other euler solution with all three rotates free, whole turns
  otherwise; two turns of a spin keyed 18° a frame, no jump); over the whole take each such
  channel's first-frame difference is moved onto its base (`anchored`, `_shift`); a channel under
  1e-4 on every frame is left off; written by `layerbake.write_deltas` (tracks, exact keys and moved
  curves) - the writer the Overlap uses too. `setKeyframe` takes no `fixed` tangent and leaves the
  types of a key already there: types go through `keyTangent`.
Proof: `docs/superpowers/plans/verify_bake_layer.py` **66/66 mayapy standalone** - the report's plainly
keyed prop: its three curves on the layer as themselves (the same nodes, key times, tangent types, a
step, a cycle), the prop as it was at every frame and half frame, the base frame 0's pose with no
curve, muted standing still, a second press refused; a highlight over a smooth curve with a broken
tangent and a fractional key and a stepped curve - exact to 3.4e-9 at half frames, the stepped keys as
they are, a weighted curve on every frame, the base bridged on keys at 9 and 21; a knot edited and baked (as the knot showed it, the knot and the pairBlend gone, weight 0.5 every
channel half way); a ranged knot over the take, a whole-take knot under a highlight (zero at 9 and 21,
the original outside); the animator's parentConstraint to a moving locator; an unkeyed constrained
object; two turns of an orientConstraint; a double knot on a knot; refusals changing nothing; one undo
putting the knot and the base keys back; a Manny game bone refused, a keyed knotted FKHead_M and a
constrained FKShoulder_R baked with the game bones exact; an object under the animator's own layer
(only the base moved, their layer untouched); the Overlap through the shared writer.
`verify_aim_overlap.py` 57/57. The live card is the animator's to try.

**…and it no longer freezes Maya** (2026-10-16, a colleague: «bake to layer иногда вызывает зависание
маи»). No loop ran forever: the press grew with the selection times the frames and with the keys times
the calls, with the viewport suspended and nothing on screen. Spec addendum 5 of
`2026-10-13-tools-bake-to-layer-design.md`. Measured in mayapy, a Manny rig, a UE clip retargeted over
692 frames, the parallel EM:
- **Before**: one constrained control among 65 selected read all 65 on every frame of both walks (273 129
  getAttr, 28-38 s); the 65 under a highlight walked the scene twice and bridged key by key (1.69 million
  Maya calls, 76-92 s).
- **Each walk reads only what it samples** (`knotplan.layer_reads`).
- **Under a highlight, a channel whose own curve bridges exactly needs no walk**: it is known before the
  walk (`_bridge_kind` → `knotplan.bridge_plan` / `bridge_outs`), and `_bridge` goes by the same answer.
- **What is left once the drivers are off is read off its own curves** when nothing else stands on the
  channel (`_plain_left`): a second walk only under a layer, a conversion or another driver.
- **A bridge reads its curve in a few queries whatever its key count** (`_keys_in`; `_evs`: `keyframe
  -eval` takes many times at once), and the writer sets a key's tangent types and angles in one call.
- **Side by side** (HEAD and after alternating in one process, best of 2):
  - one constrained control 10.9 → 5.4 s, a knot 12.7 → 5.2 s;
  - 65 and one constrained 27.9 → 7.9 s (283k → 14k calls);
  - the 65 under a highlight 76.2 → 18.8 s (1.69M → 297k calls): the rest is the writer, two calls a key.
- **A press of 60 steps or more shows Maya's progress window** (`timewalk.Progress`; steps are frames
  walked, curves bridged, channels keyed).
  - Esc in the first walk changes nothing; later the chunk is undone («Layer: cancelled - nothing
    changed»). The chunk's first step is a select, so the undo never takes the animator's step before it.
  - A press that fails is undone the same way before its error goes on.
  - With undo off, Esc is heard in the first walk only.
  - 1P Setup calls it with `cancellable=False`: it runs inside 1P Setup's own chunk.
- On the way, trap 267: an edge past a curve's keys is read on every frame now, and a stepped key beside
  an inserted edge keeps its hold (`_insert`).

Proof: `verify_bake_layer.py` **107/107 standalone**. Its L13:
- a highlight over 12 props' dense keys walks no frame, exact at half frames;
- one constrained prop among 12 keyed is the only one read;
- a bridge's calls do not grow with its keys;
- 80 curves under five highlight placements show what they showed;
- Esc at every stage leaves the scene and the animator's last undo step as they were;
- a writer that raises is undone.

The neighbours: `verify_tools_layers` 31/31, `verify_aim_overlap` 57/57, `verify_snapshot` 42/42,
`verify_1p_setup` 13/13, `verify_knots` 90/90; 6888 unit tests. **Not seen in a GUI Maya**: mayapy has no
progress window, and the verify fakes its Esc.

267. **Maya's `setKeyframe -insert` past a curve's keys re-types the key beside it.** Surveyed in 2027 on
     1296 curves: 108 changed shape, every one past the keys; inside a segment the shape holds.
     - Before the first key, it turns that key's out tangent `fixed`: a `step` becomes a smooth segment.
     - After the last key, it turns the last key's in tangent `fixed`: a spline 0.0625 off on a whole
       frame.
     - Layer's bridge inserts a key one frame outside the highlight. A highlight from a blocking curve's
       first key to before its next took the base's hold OUTSIDE the highlight (2.98 off at 4.75), in
       HEAD as well.
     - After an insert, give a stepped neighbour its type back, and never rebuild a curve from its keys
       past their range.
268. **A walk with the viewport suspended and no window reads as a hang.** Layer read every selected
     object on every frame either walk visited, and bridged key by key. None of it showed on the
     41-frame verify props; a colleague's long takes froze Maya for minutes. Measure a press on a long
     take and a big selection, give a walk or a per-key loop a progress window, and read the scene only
     for what needs it.

**Snapshot: a free copy of an object's motion** (2026-10-13, «Давай реализуем создание снапшотов»;
asked: **Object only** - OverRig's component and particle snapshots declined - and **a key on every
frame**). Spec `docs/superpowers/specs/2026-10-13-tools-snapshot-design.md`. OverRig's
`apply_LOH_Fast`: a `LOH_<name>` locator per object, parent-constrained to it, baked over the
highlight `a..b-1` (else `ast..aet`), the constraint deleted. Ours is a knot that drives nothing -
the `knotplan` kind `snapshot` (OverRig's colour 0.8 0.5 0.5, constraint None):
- **The press**:
  - `knots.snapshot(selection, order, highlight)` makes a `<leaf>_snapshot` locator in the object's
    Knots group, sized and turned (the card's Rotate order) as a knot;
  - a temporary `parentConstraint` with no offset carries the object's world track, baked on every
    frame of the span and euler-filtered, then deleted;
  - the snapshots are left selected; one undo chunk.
- **The span** (`knotplan.snapshot_span`): the highlight's own frames `a..b-1`, no ramp; else the
  whole take, as a knot's.
- **The object is never touched**, so nothing is refused for what it is (a rig control, a bone, a
  constrained object, a knot, a snapshot). A component in the selection is refused.
- **Marked** `skeldarKnot = "snapshot"` + `skeldarSnapshotOf` (the object's UUID) + the span, and
  NEVER `skeldarKnotSource`. So it rides nothing:
  - `_with_riders` and `bake_order` pass it by;
  - Remove of the object's knot leaves it, and a knot made ON a snapshot goes with it.
- **The other presses**:
  - Remove deletes it («1 snapshot deleted»);
  - Bake deletes it too (it skipped it until 2026-10-15: «После нажатия бейк если были выделены
    какие-то наши knot то они должны удалиться»), the line «1 snapshot deleted»;
  - Attach finds no `attach` on it;
  - Layer bakes the snapshot itself (`layerbake._object_of` stops at a snapshot);
  - the subtitle counts snapshots apart («2 knots, 1 snapshot in the scene»);
  - Delete character takes it with the Knots group.
- A toolrow **Snapshot** in Knots after Aim (icon `camera`, «free copy of the motion»); hotkey row
  `tools.snapshot`.
Proof: `docs/superpowers/plans/verify_snapshot.py` **42/42 mayapy standalone**:
- verify_knots' prop: the snapshot on its world pivot and orientation on every frame (3e-6 deg), 41
  keys a channel, the prop untouched;
- a highlight keyed on exactly 10..20, holding its ends outside;
- the rotate order; one undo;
- on a knotted prop; Remove of the knot keeping it; a rider removed with it;
- Bake beside a knot; Layer on it;
- the refusals;
- on Manny a bone and a control snapshotted in place, in `|Manny_Rig_Character|Knots`, gone with
  Delete character.

verify_knots 90/90, verify_bake_layer 66/66 and verify_parent 42/42 again; 6330 unit tests;
`render_tools_card.py` shows the row in the 360 px dock.

**Every Tools press on an object with animation layers** (2026-10-15, the animator: «Bake to layer
должна создавать новый слой и перекидывать туда анимацию с текущего выбранного слоя ... опция смены
парента не работает если на объекте уже есть слой ... To world тоже ... Давай проверим все
инструменты»). Reproduced first: every knot kind, Aim, Across, Inside, World and Swap refused a
layered channel as «driven by an animation layer»; Layer took only the base. Module
`SkeldarAnim/maya_tools/layered.py`. Measured in mayapy before writing it:
- a constraint on a layered channel splices Maya's pairBlend in AFTER the top layer's blend (input 1 =
  the layers' result); deleting it gives the channel back to the blend. So a knot rides a layered
  object as it rides a keyed one; Remove gives the layers back exactly;
- `bakeResults` on such a channel bakes into pairBlend input 1, a blend node, and lands wrong (9.9 cm
  on a two-layer cube). So Bake (knots) and Inside / World / Swap, on a layered object only, read what
  it shows on every frame (`layered.read`) and key FINAL values on one layer (`layered.key_shown`:
  `setKeyframe -animLayer L -value v`, exact on the base under an additive layer and on an additive
  layer, at any time; rotations made continuous; the layer's keys in the span replaced, a ranged knot's
  outside kept by inserted, pinned edge keys or flat edge keys);
- that layer is the ACTIVE one (`layered.target` = `maya_poselib.keys.active_layer`: the selected
  non-base layer, else BaseAnimation); the other layers keep their curves. An additive layer in
  quaternion accumulation is refused for rotations;
- a layer's blend node belongs to its layer by `.message -> layer.blendNodes[]`; its own value is
  `inputB` (`inputBX`.. on a rotation blend).
- `knots._channels(..., layers=True)` accepts a layered channel whose layers' inputs are all time
  curves or values (`layered.stack_word`); an expression or driven key inside a layer still refuses.
  Scale keeps refusing a layer when the parents' scales differ.
- `knots._unkey` finds the static key a knot set on the base under a layer the bake keyed the
  channel into.
- ~~Layer bakes FROM the selected layer~~ - reversed the same afternoon (below): Layer always
  takes the base.
Proof: `docs/superpowers/plans/verify_tools_layers.py` **32/32 mayapy standalone** (a prop keyed on
the base and on an additive Anim1): every knot kind, Offset, Aim, Across made with nothing moving
(0.000000 cm); a knot edited moves it 10 cm, Remove exact with Anim1's curves untouched; Bake into the
base (nothing selected) and into Anim1 (selected; the base untouched, Anim1 taking tz) as shown;
a ranged knot unbent outside at half frames; Inside / World / Swap kept to 0.000000 cm with Anim1
untouched, or into Anim1 with the base untouched; one undo each; Layer from the only layer, from a
selected Anim1 with its keys moved as keys, under a highlight, from Anim2 over Anim1, on a knot of the
layered prop; muted source and a second press refused; Overlap, Snapshot, Attach on layered objects.
verify_knots 90/90, verify_parent 49/49, verify_bake_layer 66/66, verify_aim_overlap 57/57,
verify_snapshot 42/42 again; 6460 unit tests. Not seen live (the animator's checks).

**…Layer: a knot bakes as itself, always from the base** (the same afternoon: «При запекании
анимации knot на слой сам knot не должен удаляться анимация должна запечься на для него точно так же
как и для любого другого объекта ... Когда запекаем анимацию на слой то давай будем анимацию с
базового слоя удалять»; asked, both the recommendation). Spec
`docs/superpowers/specs/2026-10-15-layer-knot-and-base-design.md`. **This replaces the "bakes FROM the
selected layer" bullet above and "a knot names its object" in the Layer section.**
- Measured first: with ANY layer selected in the Anim Layer Editor (an empty one too) the press took
  the animation from that layer - the knot was deleted, the base kept every curve, and no layer was
  made («nothing changed»). Both complaints were that one rule.
- **A selected knot node names itself** (`layerbake._object_of`: its top, a double knot's inner, an
  aim's target or up, a snapshot): planned as any object, its own base curves move onto
  `Baked_<knot>` as themselves, it keeps its constraint and goes on driving; muted, the knot stands
  in its first frame. A knot riding the selected knot comes off, as on any object. **A selected
  object riding a knot keeps the old rule**: the knot comes off, its motion onto the object's layer.
- **Drivers on free channels only** (`_drivers`): Knot Orient's kept point constraint rides its LOCKED
  translate and is the knot's own - left alone.
- **Always the base**: `_chosen_source`, `_only_layer`, `_source_refusal`, `_whole_curves_ok` and every
  `source` parameter in `layerbake` gone. An object whose animation lives only on layers is refused
  («its animation is on layers already - Layer bakes what the base layer holds»); every other layer,
  selected, muted or not, stays as it is.
- Not built: Remove of a knot leaves its `Baked_<knot>` layer behind, empty.
Proof: `verify_bake_layer.py` **83/83** (L10: Layer on the knot - one layer `Baked_prop_knot`, the knot
kept and driving, the prop and the knot as they were at every half frame, its curves on the layer as
themselves, muted the knot and the prop at frame 0's pose, a key edit still moving the prop, one undo;
L11: an empty layer and the animator's own layer selected - the base's keys taken, the base without a
curve under both layers, their layer untouched; a knot with a layer selected baked onto its own);
`verify_tools_layers.py` **31/31** (its L rewritten: the prop only on Anim1 refused; Anim1, a muted
Anim1 or Anim2 selected - taken from the base; a highlight; a knot then its prop); verify_knots 90/90,
verify_snapshot 42/42, verify_aim_overlap 57/57; Layer on every knot kind's nodes (orient, double local
and world, an aim's target and up) with the object unmoved.

235. **A channel on an animation layer is fed by the layer's `animBlendNode*`, not by its curve.**
     The base curve hangs on the blend's input A, untouched; a gate reading "the curve connected to
     the plug" after an Overlap read the blend node and called the base changed (verify gate 33's
     first run). Read the base curve by name, or through the blend's inputs.
238. **A constraint over an unkeyed channel keeps nothing of its old value.** Maya routes every t/r
     channel through the constraint's pairBlend, but an unkeyed one's input 1 reads 0, not the value
     it had (measured: ty 1.0, rz 5.0 before a parentConstraint, inTranslateY1 / inRotateZ1 0.0); a
     channel driven directly keeps nothing either. Deleting the constraint leaves whatever the DG last
     evaluated (trap 58's family). A tool that takes a constraint off sets those channels itself to a
     pose it read, and says which.

## Parametric walk: a walk cycle read once, rebuilt from knobs (2026-10-12)

The animator, with a walk cycle in Maya (bones only, `Desktop/Walk_01.fbx`): «проанализировать эту
анимацию построить ее математическую модель и затем менять параметрически эту походку? Например делать
короче шаг или добавить веса амплитудности в шаг» - then «давай попробуем сделать». Asked: the first
version is **the knobs** (a character pose - the hunched goblin - plugs in later: the model keeps the mean
pose apart from the motion around it); the result is **a copy beside the source**, re-keyed on every change;
**all four groups of knobs**; the source's stance-foot slide kept. Spec
`docs/superpowers/specs/2026-10-12-parametric-walk-design.md` (read its addendum), plan beside it. Like
the physical stop it is **outside the plugin** first: `docs/superpowers/plans/walkparam/` -
`walkmodel.py` (numpy only, a test pins it), `skeldar_walk.py` (Maya + the window; drop it into a
viewport), `verify_walk.py` (mayapy standalone on a temp copy of the Desktop FBX, never committed).
**In the plugin since 2026-10-13: the hub card Walk Builder, package `SkeldarAnim/maya_walk/`** (see "…the
Walk Builder card" at the end of this section). `walkmodel.py` is `maya_walk/model.py` now, `walkfile.py`
`files.py`, `walktarget.py` `target.py`, `walkpose.py` `pose.py`, `skeldar_walk.py` `scene.py` without its
window. `verify_walk.py` and the pictures stay in `walkparam/`.

**The clip, measured** (read only over 7001): 93 joints under `|Armature|root`, ntsc, keys on every frame
0..31, frame 31 = frame 0 moved by the travel (2e-4): a closed loop of two steps; root motion +Z 176.95 cm
a cycle (stride 88.5 cm, 1.71 m/s), the root exactly under the pelvis; the pelvis bobs 7.7 cm (lows just
after the contacts) and sways 4 cm; stance L frames 11-24, R 26-9; the stance foot slides ~0.3 cm a frame;
every helper follows a body bone rigidly. **Fourier decided the model**: the upper body is 4-6 harmonics to
1 deg, the legs keep 2-4 deg of error at 8 (a contact is a corner) - so legs come from where the feet go,
through IK, never from their angles.

**The model** (approach A of three; Fourier per channel and blending several walks rejected): everything
it reads is the source's own data at a phase, and a knob scales a deviation, shifts a sampling time or
moves a footprint - so **the defaults ARE the source**, by construction.
- the sampler: every joint's world at a fractional source time (positions minus the travel line, rotations
  as log-vectors about the joint's chordal mean, periodic Catmull-Rom; exact on whole frames);
- the travel line `O + T·τ/P`; the new cycle N frames (tempo, whole: a seamless loop), travel `k·T`;
- root and pelvis: deviations in (fwd, side, up) about their means - surge × stride, sway, bob shaped by
  the weight on a warped clock; pelvis rotation; upper body local deviations × spine / arms, the head in
  WORLD (0 holds it steady), overlap = a later sampling time, a share per bone (0.2 spine_01 … 1.0 hand);
- feet: stance = the source's foot moved with its new footprint (`k·` spacing, ± width); swing = the
  source's swing between the new footprints, its lift above the straight blend scaled;
- legs: two-bone IK hip → the new ankle, lengths the source's per frame, the knee toward the source's
  knee direction, thigh and calf turned by the rotation taking the source's (bone, leg plane) onto the
  new one (roll kept, identity at the defaults); no knee straighter than the source's straightest;
- **the reach sinks the pelvis per frame, not for the cycle**: each frame's least drop, a smooth periodic
  cover over them (`smooth_cover`: widen by the neighbours, Gaussian, scale to cover). Built first as one
  constant: 8.6 cm of crouch over the whole cycle at stride 1.3, when only the double-support frames need it
  (frames 5-11 and 20-25); now 8.9 cm at the contacts and ~0 at the passing poses;
- helpers keep their rigid relation to their body bone.

**The first build keyed a copy** of the cycle beside it (`<top>_walk`); the same day it became the walk onto
any skeleton (below) and the copy mode went. Its proof, on the model itself: `verify_walk.py` (that day's
version, in git history) **23/23 standalone** on Walk_01: the defaults = the source on 93 joints × 32 frames to 0.0002 cm (the
source's own seam); stride 0.7 / 1.3 travel ×0.700 / ×1.300, stance feet as still as the source's, bone
lengths 1e-5, seam 0; stride 1.6 the legs never straighter than the source's, the pelvis down 29 cm at
the contacts and 4.7 at the passing pose; tempo 25 / 40 seamless; lift 2 exactly ×2 over the blend; width
+10.00 cm; bob 0 level, bob 2 exactly twice; sway 0; arms 0 still, arms 2 ×2.00000; head 0 still; overlap 3
the hand exactly 3 frames late; weight 1 the pelvis 2 cm lower, the knee at contact 45.1 deg against 39.4;
exaggeration 0 still body, walking feet; one Ctrl+Z; the source's 753 curves untouched. Picture:
`docs/superpowers/plans/walkparam/walk_sheet.png` (side-view onion skins of six settings).
`tests/test_walkmodel.py` 43 on a synthetic walker (feet planted, legs by IK).

**…onto any skeleton** (the same day: «сделаем так что бы я выделил любой скелет и моя походка применилась к
нему и дальше я мог ее настраивать»; asked: onto the skeleton itself, walks saved to files, any skeleton,
rigs not yet). Spec `docs/superpowers/specs/2026-10-12-walk-onto-any-skeleton-design.md` (its addendum).
- **Save walk...** (a bone of a cycle selected): `walkfile.py` writes `walkparam/walks/<name>.walk.gz` (gzip
  JSON `skeldar.walk` 1: names, parents, worlds per frame, fps, start, and per bone parent / canonical /
  rest). **git ignores `walks/`** (the animator's data, a public repo). The rest: a skin's bind, else - an
  unskinned skeleton with Manny's bones (median length within 1 % of `assets/manny_skeleton_template.json`;
  Walk_01's 93 bones are his to 1.5e-6) - **Manny's bind from the template**, else as it stands (said). The
  same rule reads a target, so a cycle onto its own skeleton is a twin of itself.
- **Apply to selection** (any skeleton; a rig refused): `walktarget.Retarget` - per frame the Pose Library's
  `posemath.Transfer` (pairs by leaf or canonical name, rotations through the two rests, the target's own
  lengths, the pelvis offset and the travel scaled, from the target's PLACE - stored in the marker, so a
  re-tune never drifts), then **the legs by IK in the target's lengths onto the walk's ankles mapped as the
  pelvis is** (a planted foot stays planted at any size), the knee toward the transferred knee, roll kept;
  the pelvis dropped per frame where the target's legs fall short (`smooth_cover`); the helpers on the bones
  they follow in the walk (translation x the size). **The size is the legs' ratio** (thigh + calf at rest,
  both sides averaged): posemath's pelvis-height ratio snaps within 2 % to 1 and left the UE4 Mannequin
  4.06 cm short at the contacts (now x0.967, 0.89 cm); a twin (posemath.twin AND legs within 1 % - the
  twin test's median let 6 shortened leg bones of 30 through) is exactly 1. The target is read at its REST,
  so old animation on it changes nothing; written: rotate curves on every paired bone, the legs, the root
  frame's bone and the re-placed helpers, translate curves on the root frame's bone, the pelvis and the
  helpers, every other written bone's translate static at its rest local (old translate curves deleted).
  Marker on the top joint `skeldarWalk` = JSON {walk, knobs, place, start, version 2}. One undo chunk.
- **Pick selection** reads a walked skeleton's walk and knobs into the window and makes it the target; a
  released slider re-keys the target. The window: the walk list + Save walk..., Apply / Pick, Target, the
  knobs, Reset, the status (the walk, the target, bones paired, the size, stride and speed AT the target's
  size, the drop, the time). 0.25-0.4 s an apply.

**Proof** (on top of 52 unit tests: the file round trip, onto itself = identity, onto a copy at 0.7, legs 20 %
shorter, the helpers): `verify_walk.py` **14/14 standalone** - Walk_01 saved resting on Manny's bind; onto
the plugin's Manny skeleton (a twin): 80 bones on the walk's rotations to 0.0017, every bone but thighs and
calves to 0.015 cm = the pelvis's 0.0152 drop, thighs and calves to 0.074 cm - **the walk's own left leg
breathes 0.058 cm** (keyed), a target keeps its lengths; onto the Creep (x1.000), the UE4 Mannequin (x0.967),
Mixamo `Sweep Fall.fbx` (x1.027, 65 bones) and a Manny shrunk to 0.6 (x0.600): the stance ankle's spread =
the walk's x the size to 0.05 cm (6.172 -> 5.970 / 6.337 / 3.703), lengths constant to 2e-6, the travel x
the size, seam 0; re-tuned (stride 1.3) from the stored place with the time at 17 - frame 0's root unmoved;
Pick reads it back; one Ctrl+Z; the walk's cycle untouched by five applies; onto its own skeleton the cycle
itself (but the breathing legs). Picture `walkparam/walk_targets.png` (`WALK_SHEET=<png>` renders it).
**The window in the animator's Maya is theirs to try**; nothing was written there.

**…and a character pose under it** (the same day, the goblin: «В открытой сцене стоит скелет в нужной позе
попробуй теперь сделать адаптацию этой позы под нашу походку»; asked: the torso and head, the pelvis (height,
tilt) and the knees - not the arms, not the feet; the asymmetry as it is; Save pose + a Pose knob). Spec
`docs/superpowers/specs/2026-10-12-walk-pose-design.md`. The pose measured (read only): the pelvis at 68.3 cm
(the walk's 95.1), the torso leaning 60.2 deg (32 cm forward, 25 to the right), the head 29.5 deg off, the
feet 85 cm apart, **the left knee 31 deg INWARD, the right 46 outward** - a lunge more than a stance.
- **Save pose...** writes `walks/<name>.wpose.gz` (`skeldar.walkpose` 1: the bones as the Pose Library
  reads them at the current frame, the walk tool's rest rule). The animator's pose was saved through the tool
  itself over the port (read only: the scene's time, selection and modified flag checked unchanged) as
  `walks/goblin.wpose.gz`.
- `walkpose.prepare` carries it onto the walk's skeleton (`posemath.Transfer`, the walk's skeleton at rest on
  its first frame's root frame, the size the legs' ratio, 1 for a twin) and hands the model numpy data: the
  spine/neck locals, the head's and the pelvis's world rotations, the pelvis height over the travel line,
  each knee's turn (the pose's knee heading about up minus the walk's mean).
- **The Pose knob** (0..1, `walkmodel` knob `pose`, first): the spine/neck local means and the head's and
  pelvis's world means slerped toward the pose (`toward`), the pelvis height lerped, each leg's IK bend turned
  about the hip-ankle line (`turned_about`); the walk's deviations ride on top. 0 is the walk exactly.
- **The upper arms hang and swing in the WORLD** (every walk): `exp(g . w_world) . mean_world` - on a hunched
  torso they still hang by gravity; at the defaults the source exactly; Arms 0 holds them still in the world.
- The marker gains `pose`; Pick puts the pose back in the list.
Proof: 61 unit tests (pose 0 = the walk, pose 1 with the motion off = the pose, half way, the knees, the feet
planted under a pose, arms under a spine knob, prepare on a twin and on a 1.25x body); `verify_walk.py`
**20/20** with the animator's goblin on Manny: the pelvis **68.28 cm at Pose 1 (the pose 68.28)**, 95.14 at 0,
81.71 at 0.5; the torso **60.2 deg (the pose 60.2)**, 3.5 at 0; the knees turned left -43.5 (the pose -41.2,
inward), right -38.5 (-38.2, outward); the stance feet, lengths and seam as at Pose 0. Picture
`walkparam/walk_goblin.png` (`WALK_POSE_SHEET=<png>`). 6014 repo tests.

**…every part of a pose: the two-handed sword** (the same day: «Это поза с двуручным мечем давай для нее
возьмем все части тела»). The pose (read only, saved through the tool as `walks/two_handed_sword.wpose.gz`):
the pelvis at 85.3, both hands to the right in front 21 cm apart on the hilt, `weapon_r` / `weapon_l` keyed on
the sword (no mesh), the left foot forward and the right back turned 70 deg out.
- **Pose takes: Torso / Pelvis / Knees / Arms / Feet** - checkboxes (`walkpose.PARTS`, `filtered`),
  remembered on the walked skeleton (`parts` in the marker), Pick puts them back; the goblin keeps its three.
- **Arms are HELD**: the pose's arm and finger locals (clavicle to fingertips) and the arm chain's swing
  scaled by (1 - Pose) - at 1 the arms ride the chest, so a two-handed grip never comes apart; the upper arms
  leave the world-hang mode when the pose has arms. The weapon bones take the pose's hold
  (`blend_matrix` of the walk's relation and the pose's), and **walktarget now reads each helper's relation
  from the walk's result frame by frame** (was the walk's constant one), so a target holds the sword too.
- **Feet**: the pose's width (its ankles' spread against the walk's footprints, onto the Width knob) and each
  toe's turn about up (the foot's world rotation, so a planted foot stays planted). The pose's split stance
  (one foot forward) is no walk and is not taken.
Proof: 65 unit tests (+ held arms keep the hands' relation, half the swing at 0.5, the feet wider and turned,
the parts filter, prepare's arms and feet); `verify_walk.py` **25/25** - on Manny under the sword at 1, every
part: **the left hand in the right's space still to 0.000000 over the cycle**, the pose's grip to 0.015 cm;
the weapon bones on the pose's hold to 0.000000; the feet 32.1 cm apart (the walk 16.6 + the pose's 15.5),
toes turned -12.1 / -73.5 deg as the pose's; the pelvis 85.25 as the pose's. Picture `walkparam/walk_sword.png`
(`WALK_SWORD_SHEET=<png>`). 6027 repo tests.

**…and its balance: the centre of mass over the feet** (the same day: «тело постоянно сваливается в ту
сторону где нету опоры ... мы делаем шаг и как бы ловим наше тело ... инструмент который будет учитывать
поведения центра массы и корректно переносить вес»; asked: **physics on top of the style** - the defaults
unchanged, Sway still the style - and **masses from a table by bone names**). Spec
`docs/superpowers/specs/2026-10-12-walk-balance-design.md` (its addendum).
- **Measured first**: Walk_01's CoM (de Leva's table on the UE bones) sways 3.3 cm; a linear inverted
  pendulum `x'' = (g/h)(x - p)` on its own feet's pressure predicts that sway's shape at **correlation 0.98**
  (x1.4 the size), forward only 0.89 (x2-3). So the model takes the pendulum's CHANGES, each axis x how
  strongly the walk's own CoM follows its pendulum (fitted on the source, clamped 0.25..1.25: Walk_01 0.71
  sideways, 0.42 forward). The pressure's contact is the foot point's HEIGHT (within 2.5 cm of its lowest),
  not the step's planted window (13 of 30 frames, a frame with no foot down).
- **`walkmodel`**: `mass` - de Leva as one weight a joint (trunk spread at the thirds of pelvis..neck_01, the
  head on its joint, limbs at their centres, the hand half way to middle_01), so the CoM is one weighted sum
  (`com`); `pressure` - per foot a heel point (0.4 of the foot behind the ankle) and a toe point (0.4 past
  the ball), each loaded by its SOURCE contact at the phase; `pendulum` - per harmonic `w^2/(w^2 + w_k^2)`,
  `w^2 = g/h` (cm; a crouch sways more), `w_k` from the cycle's seconds (slower sways more), the mean exact.
- **Knob Balance** (0..1, default 1, the Weight group): the new CoM target = the walk's own + Balance x [the
  pendulum's change (new pressure and tempo against the source's) about its mean, x the follow, forward x
  Exaggeration, sideways x Sway x Exaggeration; plus the mean's change - the pressure's mean change minus the
  CoM's own], so **a leaning pose takes the hips back over the feet**. The pelvis is CARRIED horizontally
  per frame to put the CoM there (secant steps; a carry moves the body over the pelvis rigidly and only the
  legs are re-solved - `_moved_com`, `_leg_source` / `_leg` split - 0.25-0.4 s an evaluate on Walk_01, was
  1-1.4 s solving whole frames), then the reach's drop again, in turns until it holds. Forward, Balance
  takes over the old guess: the pelvis's forward swing scales by `(1 - Balance) x Stride + Balance`.
- **Only feet that are down hold the pelvis down** (`down`, the reach and the shortfall): a foot in the air
  that cannot reach its path passes nearer the body (`swing_in`, said). Trap 227.
- The status line: «balance: the pelvis carried up to x cm over the feet (the CoM sways y cm, the source's z)».
Proof: 20 new unit tests, 73 in `test_walkmodel` (masses, the pendulum's gain and phase, the defaults
unchanged, wider / slower / faster, the leaning pose, Sway 0, Balance 0 = the stride guess, the reach rule,
the knob in a window group);
`verify_walk.py` **47/47 standalone**, Balance on Manny's KEYS: the CoM's change = the pendulum's on the keyed
feet to **0.0013 cm** (20 cm wider: sways 6.63 against 3.28), 0.0054 (tempo 45: 5.27 against 3.26), 0.0004
(tempo 22: 2.02 against 3.21), the feet down unmoved; stride 1.3 on its target to 0.011 cm; **the goblin's CoM
14.3 cm ahead of the walk's at Balance 0, over the feet again to 0.002 cm at 1 - the pelvis carried 16.7 cm
back**; the sword's CoM mean moving with its wider, turned feet to 0.002 cm. Pictures `walkparam/walk_balance.png`
(`WALK_BALANCE_SHEET`: the CoM from above over the footprints; the goblin side and the sword front at mid-stance,
Balance 0 against 1), `walk_goblin.png` and `walk_sword.png` rendered again under Balance. Under Balance the
goblin with every part (its feet 68.6 cm wider) waddles: the CoM sways 21.5 cm and the pelvis dips 8.8 cm
where the far foot lands while the hips still sit over the other (the pose leans to its right). 6054 repo
tests (`test_hubqt.CardMotion` flaked once under the suite's load, 3/3 alone).

**…and its legs and pelvis** (the same day, the animator looking at the goblin keyed in their scene: «ноги стоят
сильно широко … нужен параметр … сужение\расширение позиции ног … амплитуду выброса ноги в сторону … подворота
колена в зависимости от подворота ступни … в 11 кадре правая нога сломана … таз … вращается в зависимости от
разворота ног и … продавливает таз вверх … усилит анимацию захлеста стоп»; asked: a stance multiplier plus a
swing-out in cm, knee and foot meeting half way, physiological pelvis amplitudes in degrees, the feet's overlap in
the swing). Spec `docs/superpowers/specs/2026-10-12-walk-legs-design.md` (read its addendum).
- **Measured first** (Walk_01 and the scene's goblin, rebuilt standalone; the scene only read):
  - the walk's pelvis already twists ±6.1° with its feet's split (corr 0.99): the norm for its step (step/leg
    1.01). Its hip drop is weak, ±1.1°, peaking late;
  - in the goblin the twist did not read because its chest stopped counter-turning (corr −0.45 against −0.86):
    the pose leans the spine 60°, and a joint's walk turn, kept in the joint's own frame, then turns about a
    leaning axis;
  - the feet stood 70 cm apart: the Feet part adds the pose's own 68.6 cm, which Width (−15 at least) could not
    take back;
  - the left shin twisted −40° (the pose turns the knee 38.6° in, the toe not), and a swinging foot kept the
    walk's WORLD turn instead of following its shin.
- **`walkmodel`**, the knobs (Width is gone; a saved `width` is filtered out by Pick):
  - **Stance** ×: a planted foot's place across the line, the walk's half-spread about the middle of its two
    prints plus half the pose's spread, all ×Stance.
  - **Swing out** cm: `sign · sin(π s)` along side over the foot's FLIGHT (`air`, `air_progress`: the longest
    stretch with heel and toe off the ground, found to 1/64 frame).
  - **Leg turn** ×: the pose's knee and toe turns.
  - **Knee ↔ foot**: past `TWIST_FREE_DEG` 15° of knee-against-toe turn the excess is shared (`meet`; 0 the
    knee to the foot, 1 the foot to the knee).
  - **Foot lag** frames and **Foot flex** ×: in the flight the foot hangs in its calf (`foot_in_calf`, blended
    in by `swing_weight`, 0 on the ground), late by the lag and its turn ×flex; the ball at 1.5× the lag.
  - **Twist** (deg, at a normal step of 0.8 leg, ×step: Walk_01 ×1.265, so 5 gives ±6.3°) and **Hip drop**
    (deg, a cosine peaking 17 % of the cycle after the left heel strike):
    - each brings the walk's fitted amplitude (`pelvis_fit`, `own_knobs()`) to the knob's, as a world turn
      post-multiplied on the pelvis (`pelvis_extra`);
    - spine_01..03 take it back (`COUNTER_SHARES`), so the chest keeps the walk's own turn;
    - **Pelvis motion** (was Pelvis turn) scales all of it;
    - the defaults are people's (5, 4), so **the defaults are no longer the source; `own_knobs()` are**.
- **A posed pelvis and spine turn about the walk's world axes** (`_spine_map`, the pelvis likewise): the goblin's
  chest counter-turns again, corr −0.80.
- The window's groups: Pose / Step / **Legs** (stance, swing out, leg turn, knee ↔ foot, foot lag, foot flex) /
  Pelvis (+ twist, hip drop) / Upper body / Weight. The status line says the pelvis's twist and hip drop in
  degrees.
- **Proof**:
  - 18 new unit tests, 91 in `test_walkmodel`;
  - `verify_walk.py` **58/58 standalone**. The twin checks run at `own_knobs()`. On Manny's keys:
    - the hip line ±6.09 / ±1.02 at the walk's own; ±6.47 / ±3.99 at the defaults (asked 6.46 / 4); ±11.65 /
      ±6.98 at 9 / 7;
    - the chest unchanged by them to 0.000000;
    - the goblin, every part, Stance 0.35: the feet 29.7 cm apart, no foot out of reach, the shins within 20.3°
      (the walk's 17.6), the chest corr −0.80;
    - Swing out 8 bows 7.94 / 8.00 cm with the feet on the ground unmoved;
    - Foot lag 2 hangs the foot as the walk's 2 frames earlier to 0.04°.
  - The scene's goblin against the new model, Stance 0.35:
    - the left shin's worst twist −13° instead of −41°;
    - the right knee off its reach, where the old one sat straight for six frames.
  - Picture `walkparam/walk_legs.png` (the scene's result / Stance 0.35 / + Leg turn 0.5, Foot lag 2; the legs
    at frames 11 and 6). The other walk pictures were rendered again. 6072 repo tests.
- **The goblin's right knee at frame 11 is turned out, not twisted**:
  - its knee is 35.5° out and its toe 44.8° out, on a leg folded to 50 cm hip to ankle under a 68 cm pelvis
    (the walk's 80);
  - it stands 32 cm outside the hip; Leg turn 0.5 brings it to 24.

**…and Foot placement: no slides, one foot always down** (the same day: «Давай реализуем парамметр foot
placement который будет исключать проскальзования ног. Сейчас у нас есть момент когда двигаются сразу две
ноги, но так не бывает когда человек идет»; asked: one knob, on by default). Spec
`docs/superpowers/specs/2026-10-12-walk-foot-placement-design.md`.
- **Measured on Walk_01**: its stance feet slide up to 0.87 cm a frame (about 6.5 cm a contact), and the
  left-to-right step has −0.19 frames of double support (a flight): both feet move at frames 7, 8 and 14.
- **Knob Foot placement** (`foot_placement`, 0..1, default 1, first in the window's Legs group;
  `own_knobs()` gives 0 = the walk's own feet). The model (`walkmodel.py`):
  - **contacts by height**: the heel (the ankle) or the ball within `CONTACT_TOL` (1.5 cm) of its own lowest,
    the longest such stretch; a pivot weight λ from heel (0) to ball (1);
  - **the lock** (`_locks`, per evaluate, on the foot's own output at 1/16 frame) holds the pivot
    `(1−λ)·heel + λ·ball` still along the ground. It is zero at the load-weighted mean of the walk's
    contact, so the mean pressure is unchanged. Across the swing a cubic whose end slopes cancel the pivot's
    speed, so the foot lifts and lands without sliding;
  - **each foot on its own clock** (`foot_time`, a periodic monotone C1 cubic): the trailing foot's contact
    grows (`_growth`) toward `DOUBLE_SUPPORT` 8 % of the cycle per step. The growth is cut back while its
    leg, rolled over its ball, can't reach the knobs' own hip as well as at the walk's lift-off. It is never
    below one new frame (no flight). The strike keeps its time; the leg, `down`, the balls and the twists
    read the foot's time, the hip the body's;
  - **the roll** (`_rolled`, closed form): a foot mostly on its ball rolls further over it, heel up to 30°,
    its toes taking the turn back. A foot mostly on its heel rolls back onto it, toes up to 15°. Either
    rolls as far as its leg needs to reach before the pelvis drops;
  - **only the lock's contact holds the pelvis down** (`planted`); a foot 1.5–2.5 cm up passes nearer the
    body;
  - **Balance's pressure loads the feet on the walk's own timing**: the longer push-off rolls off a foot
    the weight has left. `info["placement"]` holds on, slide, double support, the planted frames per foot,
    and a note.
- **Proof**:
  - `verify_walk.py` **66/66 standalone**, on Manny's keys:
    - a foot on the ground slides **0.135 cm a frame** at most (the walk's 0.749);
    - **no frame with both feet moving** (the walk's 7, 8, 23); both feet down 2 and 3 frames a step;
    - at stride 1.3, both feet down every step and the pelvis 5.32 cm lower (5.83 without);
    - under the goblin, slides 0.141 cm.
  - Balance moves the point a planted foot rolls about by ≤ 0.0001 cm.
  - Picture `walkparam/walk_feet.png`. 6079 repo tests.
- **The pelvis drop**, placement 1 against 0:

  | stride | placement 1 | placement 0 |
  |---|---|---|
  | defaults | 0.7 | 0.5 |
  | 1.15 | 0.0 | 1.3 |
  | 1.3 | 4.5 | 5.5 |
  | 1.45 | 11.9 | 11.2 |
  | 1.6 | 21.6 | 18.5 |

- **Seen, not fixed**: the goblin pose (knees) dips the swinging toe to floor height mid-swing (0.8 cm
  without placement, −0.8 with it).

**…and four fixes after using it** (the same evening, on `asd` in their scene: «root почему-то смещается и
откланяется в право … Фут плйсмент вызывает дрожание левой ноги … поза двуручного меча … носок правой ноги и стопа
в 11 кадре имеют неприродную форму. Нам нужны какие-то инструменты что бы корректировать стопу … в 27 кадре есть
щелчек ноги»). Spec `docs/superpowers/specs/2026-10-12-walk-fixes-design.md`.
- **Read first, over the port**: the scene's keys are the window's knobs with no pose (recomputed in the session
  to 2.7e-5 cm); the marker on `|root` holds an older apply (the sword, Stance 0.13, Swing out −9.06).
- **The root's drift**:
  - `asd` itself travels 2.71° right of its root's facing (−8.19 cm a cycle), its body facing the same way;
  - the transfer carries the travel in the root's axes, so the target drifted;
  - and its root weaves with the hips, 3.7 cm off the line.
  - Fix: `walkmodel.straightened` turns a cycle at most `STRAIGHTEN_MAX` (15°) off its root's nearest horizontal
    axis onto it: every place and every turn but the root's own, about up through the root's first place.
    `Walk.turned` holds the angle and the summary says it.
  - And knob **Root sway** (`root_sway`, default 0, group Pelvis): 0 runs the root straight down the line, 1
    weaves it; `own_knobs()` gives 1.
- **The jitter and the click: one cause, the roll** (measured at a quarter frame, tempo × 4).
  - Before: the left foot's speed jumped 11.9° a quarter frame at 28 and its ankle jerked 6.4 cm (the walk's own:
    under 3.2°, ~1.5 cm).
  - The least reaching roll leapt between branches (30 → 10.5 → 0° in half a frame at the toe-off, 0 → 12° for a
    3 mm shortfall at a strike) and stopped dead off the ground. Its axis, `up × flat(ball − ankle)`, flipped as
    a near-vertical foot passed upright.
  - Fix, the roll is now:
    - one signed number a frame (`_roll_need`, `ctx["rolls"]`), every leg solve of the frame taking the same;
    - turned about the foot's own side (`foot_side`);
    - a trade (`_roll_cost`: `ROLL_COST` 25 cm² · angle² + a shortfall eased in over `ROLL_SOFT` 1 cm), eased
      into its cap from 0.6 of it;
    - blended heel ↔ ball over `ROLL_SENSE`, faded off the ground over the height;
    - kept under a sole limit (`SOLE_HEEL_UP` 65° / `SOLE_TOES_UP` 30°, eased over `SOLE_EASE` 15°).
  - Two more:
    - a foot just off the ground (`_just_off`: the first `SWING_EASE` of its swing) holds the pelvis down no
      lower than its stance did;
    - `_growth` tests the lift-off and the swing's start (`GROWTH_SAMPLES`, bisected).
  - After: the left foot's jump 1.7° and jerk 0.6 cm, the calves ≤ 2.0 cm; double support 1.4 / 2.3 frames
    (2.5 / 2.4); the drop 0.85 cm (0.66).
- **The foot under the sword pose**:
  - Frame 11 is the right foot's push-off, heel up 53° and toes bent 55° on the ball. Without the pose it is 57°
    and 58°: `asd`'s own steep toe-off.
  - The pose turns the whole right leg out ~75°, so it reads sideways.
  - An "unwind to the knee" was built, measured (≤ 9°, the knee turns with the foot) and taken out.
  - **The tool is animation layers**: `skeldar_walk.base_input` follows a layered channel's blend chain
    (`animBlendNodeAdditive*`, `inputA*`) and re-keys the BASE layer, so the animator's correction layer (Anim
    Layer Editor → Create Layer from Selected on the foot and ball, key the fix) stays through every slider move.
    Until then a layer broke Apply (`connectAttr` onto a driven plug).
  - A channel driven by anything else is refused by name before anything is written.
- **Proof**:
  - `tests/test_walkmodel.py` 105 (RootTests: skewed ±3/7° gives the straight walker back exactly, a strafe left
    alone, Root sway; RollTests: the roll grows smoothly; the foot's jolt 5.8 / 5.6° against the old 13.2 / 9.5;
    `base_input`); two older tests now name the walker's own feet;
  - `test_walktarget.py` green;
  - `verify_walk.py` **67/67 standalone**: new gate 66, a +20° correction on an animation layer on top of a re-key
    at stride 1.2;
  - picture `walkparam/walk_fixes.png` (before / after: the root from above, the left foot's speed, the leg at
    24–31).

**…and the chest and the arms: amplitudes, a pose's arms, the body's inertia** (the same evening, after the
push: «Точно так же как у нас отрабатывает таз мы должны уметь параметрически изменять анимацию груди и рук … наша
поза полностью перетирает анимацию рук … захлесты рук … универсально»; a reference on `Creep_Skeleton_Character`;
asked: a two-handed grip HOLDS and the weapon sways as one, the overlap is PHYSICAL inertia). Spec
`docs/superpowers/specs/2026-10-12-walk-upper-body-design.md`.
- **The reference, read only**:
  - a fast creature gait, 20.2-frame cycle, ~3 m/s;
  - the arms in a stylised pose (left held out 75°, right back), swinging 20–25°, forearm and hand ×1.3–1.5
    wider;
  - the shoulders ±7° in the world.
  - `asd` reads alike (±6.9 / tilt ±5.1). What generalises is the sizes and how the limbs carry them, not the
    creature's posture.
- **Chest twist / Chest sway (deg, defaults 7 / 5)**: the shoulder line's yaw (× the step's gain, as Twist) and
  tilt, on the walk's own first-harmonic shapes (`_chest`).
  - Added as a world turn on the top three spine joints (`CHEST_SHARES`);
  - measured under the current pose first (`_chest_own`, spine and shoulders only, plus one correction), so a
    bent spine lands within 0.5°;
  - the head keeps its world turn; `own_knobs()` gives the walk's own.
- **A pose's arms are a mean, not a hold**: the walk's swing (Arms, and Elbow × the forearm's) runs about them.
  Only hands that hold one thing together stay held (`grip`: `walkpose.prepare`, hands within `GRIP_DIST` 30 cm).
- **`_arm_dynamics`**: the frames are the arms' TARGET; each limb follows it through a damped spring and feels its
  pivot's acceleration (carried down the chain).
  - Arm drag: `w0 = 2 zeta / drag`. Arm bounce: `zeta = 1 − 0.75 b`.
  - Integrated to a periodic steady state, the seam spread; children and following helpers are re-attached.
  - A grip: the right hand carries the held thing through the same spring (travel taken out), the left keeps its
    hold, two-bone IK for the arms.
  - Balance carries the arms as they move (recomputed under each round's carry).
  - New window groups Chest and Arms.
  - `asd` at the default 1.5 / 0.3: the forearms 2.2 frames late, the wrists ~11 cm off their target; bounce 0.7
    whips them 1.4–1.6× as far; an evaluate 0.6–0.8 s.
- **Proof**:
  - `tests/test_walkmodel.py` 126 (ChestTests, ArmTests; older arm tests name Arm drag 0, the grip fixture carries
    `grip`);
  - `verify_walk.py` **70/70 standalone**:
    - Chest 10/7 → ±12.92/7.00 on Manny's keys;
    - drag 3 / bounce 0.6: the forearms 5.9 frames late, bones whole;
    - the sword under drag 3: grip held to 4.4e-5, sword trailing 7.9 cm;
  - picture `walkparam/walk_upper_body.png`.
- **The goblin's hands and elbows shook** (the same night: «В позе гоблина у них сильное дрожание в захлесте
  как у кистей так и у локтей»). Rebuilt standalone from the scene's knobs (equal to its keys, 0.0000°): the
  hands turned 0.6 → 33 → 8 deg a frame in turn, against 4–9 for their target; Arm drag 0 or the pivot term off
  took it away. Two causes, each measured alone (trap 234):
  - the shoulder's acceleration was the frames' second difference, so every frame's noise in the shoulder's
    path pushed the arms: now its first `ARM_HARMONICS` (6) harmonics a cycle, differentiated analytically
    (`_smooth_accel`) - the body's bob, sway and twist;
  - the hand's lever was its metacarpals' base (4.2 cm): a 4 cm pendulum, 3× as stiff to its wrist's jolts as a
    hand. Now its farthest finger joint (`_hand_lever`, 13.4 cm on `asd`).
  - Above harmonic 8 of the cycle, the hands went from 5.33 / 3.20° rms to 0.55 / 0.82 (the target without
    drag 0.49 / 0.54); the frame-to-frame turn change from 37 / 22° to 6.6 / 6.9. What is left is the source's
    own: `asd`'s keyed forearms carry 0.4–0.9° above harmonic 8, and the hand whips it on.
  - Tests: the hand's lever reaches the farthest finger; a shoulder jolted ±0.5 cm on alternate frames leaves the
    hand as smooth as without the jolt (taken from every harmonic it shook 2.5× as much). Picture
    `walkparam/walk_arm_jitter.png`.
- **Not built**: gravity on the arms, a held weapon swinging with the walk's arm swing, the clavicle under
  inertia, per-arm knobs.

**…a cycle of several steps, and the pelvis over the feet** (2026-10-13, a second walk `dw` under the sword pose:
«фут плейсмент не справился … в исходной анимации весь персонаж приподнят над землей, а в нашей позе он как бы
стоит ниже … в присяде. Давай добавим параметр который просто будет контролировать расстояние между тазом и
ногами»). Spec `docs/superpowers/specs/2026-10-13-walk-many-steps-and-height-design.md`.
- **Read first** (the scene only read):
  - `dw` is a 90-frame cycle holding TWO uneven steps of each foot: left 14-47 and 65-77, right 81-14 and 50-62;
  - its first stances float 2-3 cm over the second ones;
  - its root is 17 cm under its feet.
- **The model assumed one stance a foot a cycle**:
  - placement locked the lowest stance and its swing cubic ran across the other one, dragging that standing foot
    1-7 cm a frame;
  - the hip drop's and chest's harmonics and Twist's step assumed one stride a cycle.
- **Every per-foot quantity is a list, one entry a step** (`walk.steps[side]`, `walk.strides`; `walk.feet[side]`
  the longest). One step a foot gives exactly what it did: `asd` against the previous model to 1e-13.
  - Steps are the slow runs merged across a gap that stays within `MERGE_HIGH` (4 cm) of the foot's lowest. The
    feet must alternate (refused by name).
  - **A local floor** (`walk.floor`): each step's own low, interpolated across the swings. A floating stance is
    still down.
  - Contacts, pivots, handoffs, growth and locks are per contact. `foot_time` is one monotone C1 Hermite through
    every knot; `_contact_at` finds the contact a time is in. `foot_target` runs a swing between its step's print
    and the next step's.
  - **Per stride**: `stride_phase` (linear between the left strikes) for the hip drop and the chest; Twist's gain,
    the stride readout, the arms' harmonics, the reach blur (the model's and `walktarget`'s), Weight's clock. Own
    chest amplitudes are a least-squares fit (`chest_fit`). Pelvis twist now reaches 40 and Chest twist 60:
    `dw`'s own are 17.8 and 40.8, and the old ranges clamped `own_knobs()` 7.7 cm off the source.
- **A pose's pelvis height is read over its feet** (`walkpose.pose_floor_gap`: the pelvis over the pose's lower
  ball, put over the walk's floor, `walk_floor`), not over the root line. Goblin on `asd` 68.3 → 70.7 cm, sword
  85.3 → 88.0.
- **Knob Pelvis height** (`pelvis_height`, cm, −40..40, first in Pelvis): added to the pelvis over the feet. The
  reach still holds, so no leg straightens past the walk's straightest.
- **Proof**:
  - `tests/test_walkmodel.py` and `test_walktarget.py`, 137 tests: a synthetic walker of two uneven steps a foot,
    its steps found, own knobs giving it back to 1e-4, every stance held at a 6 cm slip, per-stride gains, the
    refusal, Pelvis height up / down / at the reach, the height over the feet;
  - `verify_walk.py` **73/73 standalone**, gates 66-68 on `dw` (from `walks/dw.walk.gz`, skipped without it) under
    the sword on Manny:
    - each stance's still point slides 0.001-0.033 cm a frame (the walk's own 0.48-0.93; before this 1.5 / 7.1);
    - no frame with both feet off the ground;
    - the pelvis 84.90 cm over the feet (the pose over its own 84.91), the legs 0.74-0.99 of their length (before:
      68.2 cm, 0.53-0.80, the crouch);
    - Pelvis height +8 → 92.47, −10 → 75.15.
  - Picture `walkparam/walk_dw.png` (both feet's slide, the pelvis over the floor, side on, before against now).

**…the Walk Builder card** (2026-10-13, «Давай встроим этот скрипт в наш плагин. Интерфейс рисуй
компактным»). Spec `docs/superpowers/specs/2026-10-13-walk-builder-card-design.md`.
- **The package** `SkeldarAnim/maya_walk/` (a payload row):
  - `model`, `files`, `target` and `pose` moved there with `git mv`, importing each other relatively;
  - `scene` is the old tool without its window;
  - `panel` is the card;
  - `__init__` imports none of them (a test pins it).
- **The walks** live in `<userAppDir>/SkeldarWalks` (`scene.folder()`), outside the plugin folder an install
  replaces. The optionVar `skeldarWalkFolder` overrides it; `scene.WALKS` (a verify's temp) overrides both.
  The animator's walks and poses were copied there: asd, dw, Creep_Drunk, goblin, two_handed_sword. They do
  not ship.
- **The hub**: section `walk` «Walk Builder», Animation, after Tail Builder, Tabler `walk` (`device-floppy`
  new too). Hotkey rows `window.walk` and `walk.apply`.
- **The card, top down**:
  - the subtitle: the selection, else the target;
  - Walk and Pose, each a dropdown with a floppy icon (Save, with a name prompt); right click: show the
    walks folder, read the lists again;
  - the Pose share;
  - the parts as chips;
  - Apply (primary, `walk`) and Reset;
  - `[Step | Legs | Pelvis | Chest | Arms | Weight]` segments, **one knob group shown at a time**
    (remembered);
  - a three-line status.
- **No Pick button**: selecting a skeleton that carries a walk (`scene.selected_top`, cheap) reads its walk,
  pose, parts and knobs into the card. It becomes the target, read once: the card is the truth while tuned.
- A released knob, pose or part re-keys the target. Filling the card from the scene is quiet (`_QUIET`): an
  optionMenu set by code fires its changeCommand.
- Everything is remembered (`skeldarWalk_*`), so a hotkey row presses with the card closed.
- The marker `skeldarWalk` v2 is unchanged: skeletons walked with the window are read by the card.
- The apply line is shorter for the three lines.
- **Proof**:
  - `tests/test_walk_panel.py`, 16 tests on a fake cmds;
  - the model and target suites import the package;
  - `verify_walk.py` **73/73 standalone** on the package;
  - every saved walk through the package: own knobs reproduce its source to 0.0002 cm, both poses on each.
- **Not seen live**: the card in the animator's Maya, after Check update.

**…Pelvis forward and Ground time** (2026-10-13, «нужен парамметр который будем котролировать выдвижение таза
вперед и назад … растяжку ног во время шага (как долго нога стоит на земле перед тем как пойти вперед)»):
- **Pelvis forward** (`pelvis_forward`, cm, −30..30, group Pelvis after Pelvis height):
  - in `_body`, the pelvis along the walk's line (the body over it with it, the legs by IK);
  - Balance would carry the hips straight back over the feet (its mean term cancels the CoM's change), so
    `_balance_target` adds back the CoM shift the knob makes (`_moved_com` with the pelvis moved back);
  - exact with Balance 0; with Balance on Manny's keys +8 → 6.74 cm, −8 → −7.34 (the reach's drop and the arms'
    inertia take the rest).
- **Ground time** (`ground_time`, ×, 0.7..1.8, group Legs after Foot placement): each contact
  `(g − 1) × its length` longer at its lift-off, past what Foot placement grows. It is applied after the
  growth's reach cut-back, since it is asked for.
  - A longer stance takes at most `GROUND_ROOM` (0.6) of its swing's time; a shorter one keeps half its contact
    and, at Foot placement, a frame of both feet down.
  - It retimes the feet with Foot placement 0 too (`foot_time` takes a growth there).
  - Past 1 the legs may straighten toward `STRETCH_REACH` (0.995 of their length, all of it at 1.15,
    `ctx["reach"]`), and the toes roll further (`ROLL_BALL × g`).
  - `info["ground"]` is (asked, held) a contact; the status line says when the swing's room or both feet stopped
    it.
- **Measured, and the cost**: at a fixed stride a longer stance puts the trailing foot further behind (the hip
  travels duty × the stride over it). `asd`'s trailing leg is already straight on its toes at lift-off, so even
  ×1.05 sinks the pelvis 5 cm at the push-off, ×1.1 12 cm, ×1.3 42 cm. dw: ×1.1 11 cm. The tooltip says so.
- **Proof**:
  - `PelvisForwardTests` (3) and `GroundTimeTests` (5) on the synthetic walker;
  - `verify_walk.py` **75/75** (gates 66-67 on Manny's keys: forward ±8 with Balance, the CoM on target to 0.001;
    Ground time 1.1: each foot down 1 / 2 frames longer, a planted foot sliding 0.100 cm a frame at most, never
    both feet up, the pelvis down 12.1 cm);
  - 6175 unit tests;
  - picture `walkparam/walk_forward_ground.png`.

**…the knee click, one side at a time, Surge** (2026-10-13, over the port in the animator's scene: «у левой ноги с
26 по 31 кадры в колене идут щелчки … режим в котором левая и правая сторона станут раздельными, по умолчанию
коррекция двух сторон … коррекция таза вверх вниз, а нужна ещё вперёд и назад»).
- **The click.** Read only over 7001: `|Manny_Skeleton_Character|root` walked with asd under the goblin, Ground
  time 1.16, Pelvis height +9.68, Pelvis forward 4.95. The left knee by frame read 44, 32, 27, 28, 14, 14, then 44
  at the next cycle's frame 1. Reproduced in mayapy at those knobs (0.1 deg of jerk at Ground time 1, 3.9 at 1.16).
  Three causes, each measured:
  - the long stance ended with the leg at the walk's own straightest (0.993 of its length, the knee 13.7°), where
    a knee turns tens of degrees for millimetres of reach. Ground time past 1 now LOWERS the legs' reach toward
    `STRETCH_REACH` 0.96 (all of it at 1.15), and the pelvis sinks the rest;
  - the heel's roll was each frame's own need, falling 20° in two frames as the stance ended (the ankle jumped
    back). It is now `released` after its peak (`ROLL_RELEASE` 0.1 of a stride), and under Ground time past 1
    the whole roll is a `smooth_cover` (heel up and toes up apart);
  - a leaving foot's roll faded by its height (2.5 cm, half a frame at toe-off). It now fades over the first
    `SWING_EASE` of the swing, and a Ground-timed foot just off the ground holds the pelvis without the
    stance's cap.
  - Now the left knee reads 58, 55, 48, 41, 33 down to the lift-off, then 43, 63, 81: the turn into the shortened
    swing is quick, the wobble gone. Picture `walkparam/walk_knee_fix.png`.
- **One side at a time**: `model.SIDED` (stance, lift, swing out, leg turn, knee <-> foot, foot lag, foot flex,
  Ground time, arms, elbow, arm drag, arm bounce) take "<name>_l" / "<name>_r" (`knobs()` accepts them,
  `sided(k)` gives each side its knobs).
  - Read per side in the model: the foot, the turns, the foot lag (a dict now), the reach, the growth, the arms
    by the joint's name (`_side`), each arm's own spring (a grip: the two sides' mean).
  - The card's `[Both | Left | Right]` row under the group tabs (`skeldarWalk_side`, Both by default). In
    Left / Right a leg or arm slider shows and sets that side alone (its label marked L / R). In Both a knob
    whose sides differ is marked *, and moving it links its sides again. Each slider has its own
    `knob_changed(name)`; Reset links every side.
  - The marker keeps a side's own values and `pick` reads them back.
- **Surge** (×, Pelvis group after Sway): the pelvis's forward and back as it walks, Bob's partner along the walk
  (the balance pendulum's forward gain with it). Pelvis forward was already the static shift.
- **Proof**:
  - `SideKnobTests` (4), `SurgeTests` (2), the card's `SideTests` (5): 181 walk tests;
  - `verify_walk.py` **78/78 standalone**:
    - gate 68: the animator's knobs under the goblin, both knees down to their least bend without turning back,
      least 32.3 / 35.0°;
    - gate 69: Foot lift L 2 lifts the left foot to 40.3 cm (28.4), the right 24.4 (24.4); Arms R 0 stills the
      right hand (0.0 of 51.8 cm), the left 39.4 (39.4);
    - gate 70: Surge 0 / 1 / 2 → 0.00 / 2.76 / 5.51 cm.

**…a run keeps its flight** (2026-10-13, the animator's HavyRun over the port: «попробовал новый цикл бега и в этом
цикле фут плейсмент плохо справляется»).
- **Read first**: a 26-frame run, 2.72 m/s, each foot down 6-7 frames (23-27 %) with **both feet up 5.75 and 7
  frames** between the steps.
- **What placement did**: it grew every contact to a walk's `DOUBLE_SUPPORT` (8 % of a stride) at each handoff,
  i.e. by 7.8 and 9.1 frames.
  - The run became a walk: the swings were crushed into what was left, a swinging foot grazed the floor at
    28-42 cm a frame, and a "planted" right foot slid 10 cm a frame;
  - the pelvis sank 64.5 cm, the foot fell 28 cm short.
- **The fix**: a handoff whose source double support is below `-RUN_FLIGHT` (5 %) of a stride is a run's flight
  (`Walk.is_flight`). Such a contact is not grown (`extend` 0); the growth's "a frame of both feet down" and
  Ground time's floor do not apply. The stances are still locked.
- **Walks are untouched**: asd, dw, Creep_Drunk, TestStrefe and sadda at the defaults equal the previous model to
  0.0.
- **HavyRun now**: both feet up 11 of 26 frames, a planted foot sliding 0.09 cm a frame at most, the pelvis sinking
  0.0. Stride 0.8-1.3, tempo 20, Ground time 1.2, Weight 1, Pelvis height −10, Stance 0.5 / Swing out 6 all keep the
  flight with no slide.
- **Proof**:
  - `RunTests` (2) on a synthetic run (stance 0.2, lift 20);
  - `verify_walk.py` **79/79**, gate 74 HavyRun on Manny's keys;
  - picture `walkparam/walk_run.png`.

Not built: an in-place clip, a curved walk, a non-UE-named walk SOURCE (targets are any convention), rigs as
targets, a symmetry knob, the pose's split stance, several clips as a style knob, stance duration, a redo of an
update (trap 224); for Balance: a held weapon's mass, the target's own masses
(its mesh), vertical pendulum vaulting, a CoM trail drawn in the scene; for the legs: a per-frame knee-to-foot
solve, the pelvis's tilt in degrees, the swing path kept clear of the other leg.

224. **`cmds.setAttr(curve + ".ktv[0:n]", ...)` is refused from a script** («should be set with the
     keyframe or setKeyframe command») - only a .ma may write keyTimeValue. The fast road: create the
     curve node with cmds (undoable) and add its keys with `MFnAnimCurve.addKeys` (times in the UI unit,
     angles in RADIANS): 540 curves × 32 keys in 0.05 s against 0.8 s by setKeyframe. Ctrl+Z deletes the
     nodes and puts back any deleted with cmds; a REDO recreates the nodes empty - the keys were never on
     the queue.
225. **Row vectors put the relative transform the other way round**: a joint in its pelvis's space is
     `W_joint · W_pelvis^-1`, not `W_pelvis^-1 · W_joint`. A verify gate written the second way read the
     walk's seam as 247 cm on a seamless loop (trap 19's family, from the measuring side).
226. **A cache kept on `sys` outlives the code that filled it** (trap 111's other side). The walk tool's
     session cache - kept on `sys` so a re-dropped tool still knows its target - held a `Walk` analysed by
     the walkmodel loaded before the pose work; the re-dropped tool loaded the new walkmodel, its `apply`
     called the OLD object's `evaluate(given, pose)`, and Apply to selection died with «Walk.evaluate()
     takes from 1 to 2 positional arguments but 3 were given» - on the status line, which the next
     slider then overwrote. Every gate was green: each verify loads the code once. `_state()` now starts
     the cache afresh when the model module is not the one that filled it (the target survives).
227. **A reach rule over BOTH legs lets the swinging leg pull the pelvis down.** The walk's lowering asked
     both feet to be reachable on every frame, the one in the air too. Harmless until Balance carried the
     goblin's hips 20 cm over its standing foot with its feet 85 cm apart: the swinging foot's wide path in
     the air went out of reach and the pelvis sank **27 cm** mid-cycle to reach it. The model's picture
     showed it; every gate passed (the CoM was on target, the feet planted). Only a foot that is down (its
     heel or toe within 2.5 cm of its own lowest) may hold the pelvis down; a foot in the air passes nearer
     the body: 8.8 cm, at the far foot's landing only. Look at a pose's walk, not only its numbers.
228. **A step's planted window is not when the foot is off the ground.** The walk's contact window
     (`Foot.on/length`, where the foot is slow) ends while the toe is still within 2.5 cm of the ground
     (`down`). Keyed to the window, the new swing effects turned and slid toes still on the ground: Balance
     moved a goblin toe 3.8 cm, Swing out 8 moved a foot 0.9 cm sideways. Every unit test passed; the verify's
     "feet down unmoved" gates (written for Balance) caught it. Anything a foot does in the air keys off the
     ground contact (`air_progress`), not the step's window. And the contact itself flickers: Catmull-Rom over
     a heel at 0.86 → 0.08 → 0 rises back to 0.0015 just before the next frame, so "off the ground" is the
     longest stretch, never every frame where it reads 0.
229. **A pose's turns live in the pose's frames.** The walk keeps each joint's turn in its own local frame.
     That is right while the frames are the walk's. A pose that leans the spine 60° turns the same twist about
     a leaning axis, so the chest's counter-turn against the pelvis fell from corr −0.86 to −0.45. Nothing
     failed; it just stopped reading. Re-express the turn so it acts about the world axis it had in the walk
     (`turn @ W_walk @ W_pose^T`, both from chains of mean locals); without a pose the map is the identity.
230. **Pinning feet and lengthening their contact make the legs reach further, and every place that measured
     "is it down" with a looser rule turned that into pelvis drop.** The first Foot placement doubled the
     pelvis drop at stride 1.3 (5.5 → 13.2 cm) and at 1.6 (18.5 → 39). The causes, measured one at a time:
     - the strike was moved earlier as well as the lift-off made later; the front leg cannot roll much;
     - the 8 % double support was asked at every stride, where a real walk's double support shortens as
       the step lengthens;
     - frames 1.5–2.5 cm up, which the lock had already let go, still counted as down for the reach.

     Another made Balance carry the pelvis 6.6 cm back on every frame: the pressure loaded a foot for its
     whole lengthened contact. Make the rules agree: the contact that pins is the contact that holds the
     pelvis and the contact that bears weight. And give the leg its real way to reach, the foot rolling
     over its ball, before the pelvis drops.
231. **"The least X that satisfies the constraint" leaps when the constraint barely depends on X.** The roll
     that just lets a leg reach jumped 0 → 12° for a 3 mm shortfall where rolling hardly helped, and between its
     reachable and nearest branches as the foot turned fast — every frame correct, the animation a jolt. A
     per-frame choice the eye sees across frames must move smoothly with its inputs: minimise a cost that
     weighs the effort against the error, and ease every limit in. And a flattened direction is no axis: the
     roll's axis from `up × flat(ball − ankle)` flipped 180° as the foot passed upright — take the foot's own
     side, read in its frame.
232. **`getAttr(plug, time=t)` does not evaluate an animation layer's blend.** A rotateX keyed +20 on an additive
     layer read the base value through `time=` (11 where the scene showed 31), and the gate reported the layer
     lost while it stood. Measure a layered channel after a real time change (trap 69's family).
233. **An effect added after a solver's last pass undoes what the solver solved.** The arms' inertia ran after
     Balance had carried the pelvis to put the centre of mass on its target, and moved 10 % of the body's mass:
     the residual went from 0.000 to 0.5–0.8 cm, every balance test failing. And computed once before the carry
     it was still 1.4 mm off, because the carry itself moves the shoulders the arms hang from. Fold the effect
     into the solver's loop (the arms recomputed under each round's carry).
234. **A body that feels its pivot's acceleration feels the frames' noise twice over.** The arms' inertia took
     the shoulder's acceleration as the second difference of its frames: a 0.3 cm wobble of one frame is a 1.2
     cm/frame² kick, and the goblin's hands shook 33° a frame while every gate (lags, bones whole, the loop
     closed) passed. The hand made it worse: its lever was the first finger joint (4.2 cm), and the pendulum
     term goes as 1/L. Take a driving acceleration from a smooth fit of the path (the cycle's low harmonics),
     give a limb the lever of its whole mass, and gate the shake itself - a joint's motion above the cycle's
     low harmonics against its target's.
235. **A walk model built on one clip took that clip's shape for the shape of a walk.** `asd` holds one step of
     each foot a cycle, its stances on the floor, its root under its pelvis on the ground; every rule assumed
     all three (one contact a foot, "down" against the foot's lowest of the cycle, a pose's height over the root
     line). The second clip broke all three at once: the lock held the wrong one of two stances and dragged the
     other 7 cm a frame, and the sword pose crouched the body 17 cm because the root stood under the feet.
     Every gate passed: they all ran on `asd`. Test a model on a second source before calling it general, and
     measure heights against the thing that stands on the ground.
239. **A knee near straight and a quantity solved frame by frame both click, and finer sampling of a WALK
     changes the walk.** The animator's knee clicks came from a leg held at 0.993 of its length (13.7°: a
     millimetre of reach is degrees of knee) and from a heel roll taken as each frame's own need (20° gone in
     two frames). Keep a stretched leg off straight, and give a per-frame need a time profile: a smooth cover,
     a gradual release. Measuring between the keys by evaluating at 8x the tempo misled: the tempo is a knob
     (Balance's pendulum, the arms' drag in frames, Foot placement's frame all change with it), so 8x was
     another walk. Judge the keys the scene gets.

**…on a sprint under a side-on pose: Leg match, Gait lean, the trunk and the head on springs** (2026-10-14, the
animator in a second Maya on port 7002 with `AGS_Sprint` (Unreal's Game Animation Sample) under `two_handed_sword`:
«ноги сопоставляются между анимацией и позой плохо ... волшебная палочка ... одну настройку», «шум в верхней части
туловища ... красивый и аккуратный захлест», «захлесты головы строятся как-то странно ... более физичный»; asked: the
hips face the run while the shoulders keep the pose's turn; the physics on by default, Overlap for the arms only).
Spec `docs/superpowers/specs/2026-10-14-walk-sprint-legs-and-body-design.md` (read its addendum).
- **Measured first** (the scene only read; the walk and the pose in mayapy):
  - the saved `AGS_Sprint` had frame 61 a copy of 60 (trap 241): the cycle stood still a frame and every place
    carried a 23 cm sawtooth, which the arms', the grip's and Balance's springs took as a jolt - the forearms flipped
    105-128 deg at the seam, the arms straight at frame 0. This was most of the "noise";
  - the pose stands side-on (its hips 36.5 deg right of the walk's); the knees and toes were read against the RUN
    (the right knee -63 deg) and each bend plane turned about the hip-ankle line on every frame - in the sprint's
    swing the bent knee went sideways (31.7 cm aside of the hip);
  - `_smooth_accel`'s 6 harmonics a stride reached a 2.5-frame period on a 15-frame stride.
- **`trimmed(clip)`** at analysis: a last frame equal to the one before (or a first to the one after) is dropped
  (`Walk.dropped`, said in the summary).
- **Leg match** (`leg_match`, 0..1, default 1, Legs, before Leg turn; `matched_pose`): the pose's turn about up
  (`hips_yaw`, from `pose.prepare`: its hip line against the walk's) comes off the pelvis and the lumbar spine (the
  counter joints) takes it back - the hips face the walk, the chest keeps the pose's facing; the knees' and toes'
  turns re-read against the pose's own hips, outward, only their symmetric splay kept over the walk's own, x **keep
  = 1 / (1 + Fr)**, `Fr = v^2 / (g L)` of the new cycle (`gait_keep`: a walk 0.75, the sprint 0.15); the width x
  keep. 0 is the old reading. Status: «legs matched x0.15, hips 36 deg to the spine».
- **Gait lean** (`gait_lean`, 0..1, default 1, Chest; `leaned_pose`) - the stop builder's idea (the peer session
  "Билдер для стартов и стопов", whose `poseclip` runs the clip's motion over its still reference on the pose): a
  pose's torso replaced the walk's mean and the sprint's 32 deg lean with it. `prepare` hands each torso bone's mean
  forward pitch over the skeleton's rest (`gait_lean`) and `lean_room` = (90 - the pose's trunk lean) / (90 - the
  rest's); the model turns the pose's bones forward by it. The sword now leans 38.5 deg.
- **The trunk and the head on springs** (`_body_dynamics`, before `_arm_dynamics`, in Balance's rounds too; knobs
  **Torso drag** 1.5, **Torso bounce** 0.2, **Head drag** 2.0, Chest): the chest's world turn follows the frames'
  through `_limb_motion`'s spring (`_body_motion`), feeling the first spine joint's acceleration on the upper body's
  centre of mass, spread up the spine (1/N ... 1); the head keeps its gaze through its own spring on the neck
  (inertia `HEAD_INERTIA` 0.3, trap 242), the neck taking 0.3 / 0.55 of the difference; upper arms the frames hang in
  the world keep hanging there (`_reattach(held=)`). `ACCEL_HZ` 8 caps every pivot acceleration (the arms' too).
  Overlap's LAG shares: the arms only. `own_knobs()` give the walk back (both drags 0).
- Proof: `verify_walk_sprint.py` **12/12 standalone** - the arms' worst jitter 3.3 deg (the old reading 104.9), the
  knees 10.1 / 8.7 cm aside at most (31.7), the hips 85.2 deg (the clip 85.3, the old 48.7), the shoulders 25.4 deg
  turned against them, the lean 38.5 (the clip 31.8, the old 6.9), chest jitter 1.09 (the frames 1.53), head 0.45
  (the clip 0.96), bones and grip exact; picture `walkparam/walk_sprint.png`. 202 walk unit tests (Leg match, Gait
  lean, BodyDynamics, Trim; tests of other features name the knobs they hold still), 6390 in the repo;
  `verify_walk.py` **79/79** again (five gates now name `leg_match` 0 or the drags 0: they test the old reading of a
  pose's legs and the chest knobs' exact degrees).

241. **An exported clip can repeat its last frame, and a cycle reader takes it as a frame of motion.** AGS_Sprint
     was saved 0..61 with 61 = 60 (an FBX's closing frame keyed again); the loop check passed (61 = 0 + travel), so
     the model read a 61-frame cycle that stood still one frame, and every joint's place against the straight travel
     line carried a sawtooth one frame of travel high (23 cm on a sprint). Nothing kinematic showed it; every spring
     downstream (the arms, the grip, Balance's pendulum - all fed by FFTs and accelerations of those paths) rang
     with it, and the animator saw "noise in the upper body". Drop a frame equal to its neighbour before reading a
     cycle (the stop builder's clip had the same repeat).
242. **A spring that feels its pivot's acceleration near the drive's own frequency bobs instead of calming.** The
     head at inertia 1 on a sprint (steps at 4 Hz, the spring's own ~3 Hz) swung 12 deg off its gaze and came out
     noisier than the clip; the trunk's inertia changed nothing (its lag is the spring's). A held body part (a head
     stabilised by the neck) takes a fraction of the inertia; measure the result's jitter against the source's, not
     only against the frames'.
243. **A drag in FRAMES costs a fast motion more.** Torso drag 2 kept 95 % of a walk chest's motion and 83 % of the
     sprint's, trailing it 15.5 deg. Pick a drag on the fastest gait it will meet.

**…a raw clip read clean: the loop, Smooth, In place, a Fix posture button** (2026-10-14, a walk broken on purpose beside
a reference idle `M_Neutral_Stand_Idle_Loop`: «Давай улучшим алгоритмы работы нашего motionbuilder ... научить наш билдер
исправлением такой анимации»). Spec `docs/superpowers/specs/2026-10-14-walk-clean-levers-overlap-design.md` (read both
addenda). **Built whole first** - a Clean tab (Despike, Smooth, Fix posture, Floor, Seam, a Reference dropdown), In place,
six levers (pelvis tilt, chest pitch, head nod, shoulder swing / bob, arm swing) and an Overlap tab (upper body offset, spine
wave, shoulder and pelvis drag), pushed as `fb2a343` - **then cut back the same day after a try**: «полезным оказались функции
inPlace, FixPosture, Seam fr ... Можно еще сглаживание оставить. Fix pos давай сделаем кнопкой ... Остальной функционал
алгоритмы, ручки, логику давай все откатим». The levers, the Overlap tab and its knobs, Despike, the floor, the root's carry,
the in-place-clip travel restore and the Reference dropdown are gone (`model.py` is 9b06363's plus In place; all in git at
`fb2a343`). The loop method from the animator's note (`Downloads/Перенос стиля движения для запекания.md`): Kovar-Gleicher
loop points, Holden's two-sided cubic offsets.
- **Save walk stores the clip AS IT STANDS** (looped or not); **`maya_walk/clean.py`** (numpy) makes the cycle when it is
  read: `scene.load_walk(name, knobs)` returns (walk, statics, start, Report), cached per file and knobs (six readings a
  file). At read:
  1. the loop: closed as it is; a cycle missing its closing frame given it (travel = a line + 6 harmonics fit of the root's
     path); else cut out - body points in the root's ground frame +-2 frames, whole strides, within 1.2x the least + 0.5 cm
     the FEWEST strides, the longest of those (20 cycles -> one); the cut's climb taken off;
  2. the seam (**Seam, fr**, default 8): a helper or twist that does not loop is REBUILT (the helper on its bone at its rest
     relation; the twist by the UE rule, counter -(1-t) / follow t); a body joint keyed short refilled; else Holden, value
     and slope;
  3. **Smooth, fr** (default 0): a periodic Gaussian on every joint - **the feet kept where the source steps**
     (`clean._keep_feet`: each leg solved again from its smoothed hip onto its old ankle, meanpose's leg solve).
     Until 2026-10-16 the feet were smoothed too: their heights blurred across the contacts and the step reading
     broke - at 0.9 one of three walks in the animator's scene read «the left foot steps 4 times a cycle and the
     right 3» and Pick refused it (its status line only in the popup copy pressed); at 1.5 all three refused, at 3
     they read as one stride a cycle.
- **Fix posture is a BUTTON** in the Clean tab (`scene.fix_posture(name, knobs)`, `panel.press_fix_posture`): the walk read
  as it will be read (looped, its seam closed, not smoothed), its posture set right against the shipped UE5 idle
  (`assets/walk_reference_ue5.wpose.gz`, its 302 frames' mean, carried onto the walk by `pose.carried` - a headless 1P walk
  too; one it cannot stand on is judged against the rest, said as a report note): a bone off its opposite's length by
  max(1 cm, 10 %) -> its rest; clavicles (rise -22..+35, forward +-30) and feet (pitch +-35, out +-35) out of limits -> the
  opposite's motion mirrored half a stride on, else the idle's mean with its own motion; a clavicle's upper arm keeps its
  world turn. **Written into the walk's file**, the file as it was kept once as `<name>.walk.gz.orig` (`scene.BACKUP`; a
  listing never shows it); nothing out of place - the file untouched; then the target is keyed again. Reading never fixes
  posture.
- **In place** (a chip by Apply, model knob `in_place`): the travel and the root's surge off every joint.
- The card's groups on two rows: [Clean | Step | Legs | Pelvis] / [Chest | Arms | Weight]; Clean holds Seam, Smooth, Fix
  posture and the report of what the clean found.
- Proof: `verify_walk_clean.py` **25/25 standalone** (the broken clip looped with its helpers and twists rebuilt, every joint
  loops to 0.0004 cm; Fix posture sets both clavicles and the foot (its mean 9.9 deg off `asd`'s, was 72), keeps the
  original, a second press finds nothing; every saved walk of the animator's read with only its loop touched; Apply loops
  0.0000 cm, In place 0.000 cm); `verify_walk.py` 79/79, `verify_walk_sprint.py` 12/12; `tests/test_walkclean.py` 23.
  Not seen live: the card - the animator's to try after Check update.

**…the walk's mean pose on a Manny rig, edited for the whole cycle** (2026-10-15: «кнопочку которая рядом с нашей походкой
будет создавать manny rig на котором будет наша средняя поза и меняя анимацию на этом риге мы будем менять нашу позу для
всего цикла»; asked: the pose may be abstract, the edit corrects the WALK itself and Pose stays on top, it reaches the walk
by itself after the mouse is let go, it belongs to the walk, the upper body's rewrites the frames). Spec
`docs/superpowers/specs/2026-10-15-walk-mean-pose-rig-design.md` (its addendum).
- **The walk's mean pose** (`maya_walk/meanpose.py`, numpy): every bone by FK of its local means (`lmean`, the mean local
  translation; the root at `wmean` on the origin) - abstract, each bone's mean taken alone (before this the model kept
  these means only as the centres its deviations scale about).
- **The Rig pose tab** (the eighth knob tab, `rigpose`, second row; since the same day - «отдельную вкладку где
  будут кнопки, создать риг позу, удалить риг позу, и сделать Update ... по нажатию кнопки» - the first build's
  Mean... button and its automatic watch are gone) → `maya_walk/meanrig.py`:
  - **Create** (`press`): one Manny [rig] in a scene (Add Character), 150 cm beside the target, marked
    `skeldarWalkMean` on its Main ({walk, clean knobs, base}); posed through the Pose Library's solve
    (`apply.plan_for`), its controls set with NO keys (their time curves deleted), unrecorded; its legs come out in
    FK; labelled «asd - mean pose». Pressed again: the same rig posed again;
  - **Update** (`update`, primary): reads the rig, writes the correction, re-keys the target; «nothing moved on the
    rig pose since the last Update» when nothing did; refuses with no rig;
  - **Delete** (`delete`, danger): Animation Setup's Delete on the rig, no question; the walk keeps its correction;
  - **Reset** (`reset`): the correction dropped, the rig back in the plain mean pose, the target keyed again.
- **Read back as a difference** from the last reading (`base`, kept on the marker), both carried onto the walk's
  skeleton as a pose is (`pose._onto`):
  - the upper body's locals: pelvis, spine, neck, head, clavicles, arms, fingers (no twist, helper or leg);
  - the pelvis over the root, along up;
  - the ankles apart along the walk's side axis;
  - each knee's turn about the leg's line (`knee_turn`: the old bend laid across the new line, so a leg that only moved
    reads none - an absolute heading read 16 deg for a 20 deg turn once the width and height had moved the line);
  - each foot's heading.
  An untouched rig reads nothing, whatever the walk's skeleton.
- **The correction, beside the walk**: `<walk>.walkfix.json`, `{"rot": {bone: C}, "height", "width", "knee", "toe"}`;
  `combine` turns a bone's correction by `now . base^T`, adds the rest; an empty one removes the file.
  `scene.load_walk` reads it (cached by its time):
  - `mp.correct` rewrites the cleaned clip's frames before the analysis: a corrected bone's local
    `L . lmean^T . C . lmean`, the body by FK;
  - each leg solved again from its new hip onto its OLD ankle on every frame (its plane turned the least; out of reach
    the leg stands straight at the ankle, the shin stretched - the target's reach takes the pelvis down), the foot and
    what is under it kept in the world;
  - a helper that followed a bone rigidly follows it again.
  The legs' share goes on `Walk.fix` (zeros by default): `evaluate` adds the height to the pelvis's mean height, the
  width to the feet's spread, the knee and toe turns to the turns - each giving way to a pose's own at the Pose share.
- **Update re-keys the target UNRECORDED** (`scene.apply(record=False)` → `write_curves(in_place=True)`: a standing
  curve emptied and re-keyed through the API, no node made or deleted behind the undo queue) - Ctrl+Z is the rig's,
  then Update again; an older Apply's undo still finds its nodes. `stop()` takes down a watch the first build left on
  `sys._skeldar_walk_mean` (Create, Update and Delete call it).
  - The Apply line adds «mean pose corrected (1 bone turned, pelvis -5.0 cm)».
- Proof: `docs/superpowers/plans/walkparam/verify_walk_meanpose.py` **27/27 standalone** (asd, the plugin's Manny
  skeleton the target; Update pressed by hand):
  - the rig's game skeleton on the walk's mean pose to 0.0001 deg, 187 controls unkeyed, an untouched rig writing
    nothing;
  - FKShoulder_L +20 → upperarm_l's correction 20.00 deg, the target's upperarm_l mean over the cycle 20.01 deg
    (1.2 s an update);
  - RootX_M -5 cm → -5.00, the target's pelvis 4.65 lower;
  - Ctrl+Z on the rig back to 0;
  - the left leg switched to IK reading no change, its pole → knee 15.2 deg;
  - IKLeg_L 15 deg about world up → the foot 15.0;
  - RootX_M 8 deg → the pelvis 8.00, the corrected cycle's ankles where the walk plants them to 0.000000 cm;
  - Reset dropping the file, the target on the plain walk to 0.0000 deg.
  `tests/test_walkmeanpose.py` 12 (the file, the mean pose, the legs' corrections reading back as themselves, combine,
  correct keeping the feet and the loop, the model's fix, a pose taking the knees over); `verify_walk.py` 79/79 again.
  **Not seen live**: the button, the watch's timer and the label in a GUI Maya - the animator's to try after Check update.

**…the pose is a Pose Library card dropped into a well** (2026-10-15). The animator asked why a pose put on the mean
pose rig walks worse than a saved pose. It is not the same road: the Pose knob takes a pose part by part (the grip
held, the height over the feet, Leg match, Gait lean, Balance), while the rig's Update writes a plain local correction
into the walk's frames. Then: «вместо строчки pose окошко для карточек которые будем перекидывать драгом прямо из
библиотеки поз». Asked, both the recommendation: **only the library** (the old `.wpose` poses moved in as cards,
Walk Builder's Save pose gone), and **follow the card, with a copy**. Spec
`docs/superpowers/specs/2026-10-15-walk-pose-card-well-design.md`.
- **A card's bones ARE a `.wpose`'s**, plus `rotateOrder` and, from a rig, `drive`. `walkpose.prepare` hands them
  to `posemath.Transfer`, which already reads a drive where the target cannot carry the roll. Nothing to convert.
- **The well** (`maya_walk/posewell.py`, Qt) is a strip laid over the `cmds` placeholder `skeldarWalkPoseWell` (the
  portraits' `attach` + Keeper), one per scope (the hub's card and every popup copy).
  - It shows the card's thumbnail, name and a note («the card is gone from the library»); empty: «Drop a pose card
    here».
  - Click: the card in the library. Right button: Show in Pose Library, Clear.
  - Without Qt: a line `skeldarWalkPoseWellText`.
  - The Pose share and the part chips stay under it.
- **The drop**: `maya_poselib.window.aim` asks `walk_well(gx, gy)` before «over the hub: nothing».
  - It answers kind `walk` (ghost «Name · Walk Builder pose») and lights the well while the card is over it.
  - An animation or objects card reads `none`.
  - The release is the well's scope-bound `take` → `panel.take_card`: refused for an animation or objects card;
    else the card remembered (`skeldarWalk_poseCard`, relative to the library), a Pose share of 0 set to 1 (said),
    and a standing target re-keyed.
  - The card's right button **Use in Walk Builder** does the same (the classic hub, the card closed).
- **Storage** (`maya_walk/cards.py`): the marker `skeldarWalk` gains `pose_card`; the bones last used go into a
  second string attribute `skeldarWalkPose` (gzip + base64).
  - `scene.apply(..., pose_card=)` reads the card (cached by `pose.json`'s time), so the card's Update from
    selection is taken on the next re-key.
  - A card renamed or deleted: the copy, and the line «pose card X is gone - using the copy on the skeleton».
  - An old memo's `pose` name: its migrated card, else its `.wpose`.
- **The old poses**: `cards.migrate` on the card's build (once a session) writes every `.wpose` of the walks folder
  as `Walk poses/<name>.pose` (every bone a member, no thumbnail), listed in `<walks>/library_poses.json`, so a card
  deleted later is not made again. A taken name is left. The `.wpose` files stay.
- **The mean pose rig's way into the Pose knob**: pose the rig, save it in the library with + Save, drop the card.
- Proof:
  - `docs/superpowers/plans/walkparam/verify_walk_pose_card.py`, **6/6 mayapy standalone** (copies of `asd` and
    `two_handed_sword` in a temp walks folder, a temp library, Manny UE5 skeletons):
    - the `.wpose` and its migrated card key the same curves, worst 0.0;
    - the card edited (spine_03 turned 20 deg) moves the keys 20.0 deg on the next re-key;
    - the card deleted re-keys from the copy exactly, said;
    - an old memo's name keys through its card.
    A pelvis moved alone in a card changes nothing: the pose is carried by rotations, so the feet go with it.
  - Unit tests `tests/test_walk_cards.py` (11, the well offscreen) and `test_walk_panel.PoseCardTests`; the
    library's `Drops.test_over_a_walk_builder_well_the_well_takes_the_card`.
  - **The live drag is the animator's.**

**…a column of cards, one active** (the same day: «давай сделаем массив в столбик так что бы я мог закинуть
несколько карточек а работала та поза которая активна тоесть выбрана»):
- **The well is a column** (`posewell`): one row a card (48 logical px, its thumbnail, its name, «active -
  the walk takes this pose» / «click to use this pose» / a note for a card gone), the active row lit (accent
  outline, `card_active`), and a dashed drop row under them («Drop another pose card here»); with no card the
  old empty strip. The well sets its placeholder as tall as the column on every refresh (`well_height`,
  `row_index` pure).
- **A drop** adds the card at the bottom and makes it active (a card already there is made active, not
  doubled); **a click** on a row makes it active and re-keys the target (`panel.pick_card`); a double click
  shows it in the library; the right button: Use this pose, Show in Pose Library, Remove from the well, Use no
  pose (the list kept, the walk's own posture), Remove all.
- **Storage**: the list is the optionVar `skeldarWalk_poseCards` (JSON, relative to the library, top down);
  `skeldarWalk_poseCard` stays the active one, and an active card not in the list heads it (`card_list`), so
  an older memo and a walked skeleton's `pose_card` join the column. The skeleton's marker still keeps only
  the active card and its copy. `panel.well_rows`, `remove_card`, `remove_all_cards`; `clear_card` is now
  «no card active».
- Proof: unit tests (`test_walk_cards.Well` / `WellLayout`, `test_walk_panel.PoseCardTests`), 6672 in all; an
  offscreen render of three rows. **Not seen live.**

**…Apply is Pick, and the walk cycle is an animation card too** (the same evening: «Давай Applay заменим на
Pick (мне кажется так понятнее что эта кнопка делает) и для циклов походок тоже добавим возможность применять
карточки»; asked: Walk Builder's main button; the walk cycles as Pose Library ANIMATION cards, in place of the
Walk dropdown).
- **Pick**: the button's label and every line that named it («press Pick», «Pick puts asd on it»); the control
  is still `skeldarWalkApply` and the hotkey row `walk.apply` («Pick walk»).
- **The walk well** (`posewell`, kind `"walk"`: one class, its texts by kind in `TEXTS`; `WalkScene`) above the
  pose well, under «Walk cycle» + Save...: a column of animation cards, the active one is the walk Pick puts on.
  A drop, a click or the library's Use in Walk Builder (now on animation cards too) makes a card active, sets
  the walk's tempo and re-keys the target (`panel.take_walk_card`); removing the active one moves on to the next
  (`remove_walk_card`, `remove_all_walk_cards`). The library's drag: the walk well takes an animation card and
  refuses a pose card, the pose well the other way round (`look.WALK_NOT_POSE` / `WALK_NOT_ANIM`; the aim carries
  `well_kind`). The Walk dropdown is gone (`WALK_MENU`, `_menu_row`, `_fill_menus`).
- **A walk's name** is a file's name, or `scene.CARD` + the card's path in the library (`card:Walk cycles/asd.anim`,
  `scene.card_walk`, `is_card`, `walk_label` for every line). `scene.walk_path` is the one resolver: a card is read
  (`cards.walk_data`: the header's statics, every frame decoded, Manny's template bind for Manny's bones, the
  frames' order kept) into a walk file of its own under `<walks>/cards/`, written again when the card's files
  change (`<file>.source` holds the card and its times); a card gone keeps the walk it gave. Fix posture and the
  mean pose's correction live beside that file, so everything downstream (load_walk, Fix posture, meanrig,
  prepared_pose) reads cards unchanged. `walk_exists` replaces `name in walk_names()`.
- **Save...** writes an animation card into the library's `Walk cycles` (`scene.save_walk_card`: the clip read as
  before, `cards.card_of_walk`, a still where a viewport stands) and puts it in the well.
- **The old walks move into the library once** (`cards.migrate_walks` on the card's build, listed in
  `<walks>/library_walks.json`, a deleted card never made again; the files stay). A walk remembered by its file
  name means its migrated card (`chosen_walk`), and the first read of a migrated card copies the file's mean pose
  correction (`*.walkfix.json`) beside its cache. A skeleton walked before keeps its file name in its marker and
  keys from the file.
- Proof: `tests/test_walk_cycle_cards.py` (12: the round trip, refusals, migration, the cache and its re-read, the
  correction carried, the panel's presses), `test_poselib_window` (the walk well's aim and drop, the menu on an
  animation card), 6685 in all; `docs/superpowers/plans/walkparam/verify_walk_cycle_card.py` **6/6 mayapy
  standalone** on copies of `asd` and `dw` (asd from its file and its card 2.8e-4; Save as a card and as a file of
  one skeleton under the sword 2.0e-2 - a pose amplifies the card's 9-decimal rounding, asd reads 1.3e-2 there
  too; the card edited re-keyed, deleted keyed on). **Not seen live.**

**…several walkers at once: Pick adds to a list** (2026-10-16: «обрабатывать сразу несколько циклов на разных
персонажах ... pick должна добавлять персонажа в список ... для каждого цикла своя средняя поза ... все настройки
работают одинаково для всех циклов но каждый цикл уникальный»; asked, all the recommendation: the knobs shared,
the pose card shared, the mean pose per CYCLE). Spec `docs/superpowers/specs/2026-10-16-walk-builder-many-walkers-design.md`.
**This replaces "the target" everywhere above: there is no single target any more.**
- **The list is the scene's walked skeletons** (`scene.walkers()`: every top joint with the `skeldarWalk` marker v2
  in the active tab whose memo is not `"listed": false`; read from the scene each time, so it survives save and
  reopen, and older walked skeletons are listed). `scene.set_listed`, `walker_label` (the character group without
  `_Character`, else the namespace, else the short name), `selected_roots`.
- **Pick** (`press_apply`) puts the walk well's ACTIVE cycle on every selected skeleton and lists it; on a walker
  already listed it changes its cycle. Activating another walk card re-keys nobody.
- **Every re-key is `rekey_all(walk=None)`**: a released knob, a pose card taken / cleared / removed, a part chip,
  In place, Reset - every listed walker, each on its own cycle with the card's knobs and pose; a walker that fails
  is named and the others still keyed. Fix posture re-keys the walkers on that cycle only.
- **Tempo is a ratio** (`walk_knobs`): the card counts the active cycle's frames, a walker on another cycle takes
  the same ratio of its own (≥ 4); `_walk_taken` rescales the card's tempo to keep the ratio.
- **The card's list** `skeldarWalkList` under Pick: «character - cycle», click selects them in the scene, Delete /
  right click > Remove from the list (`listed` false, keys kept), right click > Take its settings into the card
  (`take_settings`: what selecting a walked skeleton used to do). Selecting a NEW listed walker makes its cycle the
  active one (`_activate`, `_SELECTED`: a refresh with the same walker still selected leaves a clicked walk card).
- **Rig pose: one Manny rig per cycle** (`meanrig.rigs()`, `find(walk)`): Create acts on the active cycle (beside
  its first walker); Update reads every rig into its own cycle and re-keys that cycle's walkers
  (`update(rekey=panel.rekey_walkers)`, unrecorded); Reset / Delete the active cycle's.
Proof: `docs/superpowers/plans/walkparam/verify_walk_many.py` **16/16 mayapy standalone** (three Manny skeletons,
two on asd and one on dw: Pick on two at once, a knob re-keying all three each on its cycle, the tempo ratio (45 of
dw's 90 → 16 of asd's 31), out of the list and back, two rig poses, asd's +20° reaching A and B 20.02° and C
0.0000); `verify_walk_meanpose.py` again; unit tests in `test_walk_panel` / `test_walk_cycle_cards`. **Not seen
live.**
- **…and Pick processes each skeleton's OWN cycle** (the same day, after the push: «pick ко всем скелетам ...
  применяет один и тот же цикл а он должен брать цикл у каждого скелета и обрабатывать его отдельно ... для
  обработки массивов анимаций»; asked: onto the same skeleton, the source kept on it). `panel.walk_for`: the cycle a
  walked skeleton walks, else its kept source, else its own keys read as its cycle (`scene.capture_source`, kept as
  `skeldarWalkSource` on the top joint, base64 of the walk file - it travels with the scene), else (no keys) the
  walk well's card. An own cycle is named `own:<digest>` and read into `<walks>/own/<digest>.walk.gz`, rewritten
  from the scene when missing. Right button on the list: Use the active walk card, Use its own cycle, Restore the
  original keys (`scene.restore_source`). With no card active the first own cycle is the active one (each keeps its
  tempo). Proof: `verify_walk_own.py` **12/12 mayapy standalone** (three skeletons keyed asd / dw / asd x1.3 and
  stripped: each processed on its own cycle (32 / 91 frames, travel x1.000 each), stride 1.2 → x1.200 on all three,
  a second Pick on the kept cycle, the scene saved and reopened with the cache deleted re-keying from the scene,
  Restore 0.000000 cm). Limit: the mean pose correction of an own cycle lives in the walks folder, not the scene.
- **…and choosing a cycle puts it on at once again** (after that push: «Мы сломали старый функционал теперь при
  выборе цикла цикл сильно ускоряется» - reproduced: dw (90 fr) chosen, Pick, the skeleton kept asd (31 fr), three
  times as fast). A walk card chosen in the well keys the selected card walkers (none selected: every card walker;
  `card_walkers`) at the card's own tempo; Pick (`walk_for`): own cycle → kept, walks a card → the active card, not
  walked → its own keys captured, else the card. A walker on its own cycle is never changed by a card, and selecting
  one leaves the well alone; selecting a card walker activates its card with the tempo ratio kept.
- **…and the card comes first** (after that push: «карточка анимации цикла не применяется вообще» - the skeletons
  the previous build had read as own cycles were out of every card's reach; asked, «Карточка важнее»). Pick puts the
  active card on every selected skeleton, own-cycle walkers too, keeping an unwalked skeleton's keys first
  (`_keep_original`, best effort) for Use its own cycle / Restore. **Pick's right button > Pick: each on its own
  animation** (`press_apply_own`) is the array road, and Pick's road with no card at all. A chosen card keys the
  selected walkers whatever they walk (none selected: the card walkers). `verify_walk_own.py` **15/15** (13-15: Pick
  on an animated skeleton puts dw on it, its own animation kept, Restore 0.000000 cm).
  Found on the way: **Pick changed the animator's selection** - `write_curves`' `createNode` selected each new
  curve, so after Pick the selection was an animCurve and a card clicked next reached nobody. `skipSelect=True`;
  `card_walkers` reads the selection as walkers only (a bone, the top, a skinned mesh - `_selected_walkers`).
- **…an empty well, a clip loaded onto a walker, a card taken out, the tempo** (spec addendum 4). `chosen_walk` no
  longer falls back to the first saved walk FILE (it put `Creep_Drunk` on a skeleton carrying its own clip): an empty
  well is no walk. `apply` keeps `keys` (`scene.keys_print`: a digest of the base-layer keys it wrote); `keys_changed`
  = a clip was put on since - Pick drops the old kept cycle and reads the new keys, a knob skips that walker. Taking a
  card out of the well puts its walkers back on their own animation (`_back_to_own`). The tempo knows the cycle it
  counts (`tempo_walk`, `skeldarWalk_tempoWalk`): a Pick after the active cycle changed some other way read another
  cycle's frames (Creep_Drunk 90 fr squeezed into 31). `verify_walk_own.py` **22/22**.
- **…two pose cards switched over several walkers** (spec addendum 5; «переключение между ними перестает работать и
  кажется плагин тоже»). Every card click re-keyed every walker on the spot (four walkers of 90 frames: 8.5-9 s with
  Maya still, the well unlit) and the clicks made meanwhile each came in after as one more full re-key - nothing
  failed, it looked dead. A press that re-keys everybody (a pose card, a knob, a part, In place, Reset) now changes
  the card at once and keys on Maya's next idle (`panel._rekey`: `executeDeferred` through `maya_hubcopy.wrap`), one
  re-key for a burst of presses (every job is `_serve`, counters on `sys`; a job run while a re-key works does
  nothing - never nested - and that re-key stops between walkers and queues one more), under a progress window Esc
  stops; batch keys at once. `scene.evaluated` keeps a walk's last 4 evaluations on the walk
  object (knobs + the prepared pose object + parts): a switch back 2.3 s for the four (was 8.5-9), its keys equal a
  fresh evaluation's to 2.7e-15. Pick, a walk card, Fix posture and the rig pose's Update still key at once.

246. **AdvancedSkeleton's limb bones do not roll, so a rig's game upperarm / lowerarm / thigh / calf read bare lose the
     roll its twist joints carry.** The mean pose put on Manny_Rig read back 8-14 deg off on the arms (hand_r 14.5, the
     forearms 8-9) and a 20 deg shoulder turn came with a phantom 0.9 deg on the forearm. Read them in their DRIVE
     (`rigsolve.drive_matrices`, which `poselib.scene.skeleton` hands as `bone["drive"]`): 0.0001 deg.
247. **A manipulator sets the COMPOUND `rotate` / `translate`, and a compound is never keyable** - only its children
     are. The mean pose rig's watch took keyable plugs only, so a drag in the viewport reached nothing while an edit in
     the Channel Box (which sets `rotateZ`) did: «работает не стабильно». Read live over port 7002 by logging every
     attribute-changed message (msg 2056 `FKSpine4_M.rotate keyable=False`). `meanrig.watched`: a keyable plug, or a
     compound with a keyable child. A verify that edits a channel by `setAttr(ctrl.rotateZ)` cannot see this - set the
     compound as a manipulator does.

**…a backward walk** (2026-10-16, the animator's own clip on a Manny skeleton in their scene, 115 frames, four
steps a foot, under LongSword_Idle_3P: «походка назад ... ноги сломаны ... на 93 кадре таз сильно проваливается»;
read over 7001, reproduced in mayapy). Two defects, both of the model:
- **The body's left is not the travel's left** (trap 260). `Walk.left` (+1 / -1, the mean hip line against
  `side`), `lside = left * side`, `ahead = left * fwd` are the body's own. Leg match reads the knees' and toes'
  headings from the body's front (`front` π for a backward walk); the pelvis and chest twist / sway fits read
  against `lside` and their added turns are x `left`; Gait lean, `lean_room` and Swing out use `lside` / `ahead`.
  A forward walk is unchanged to 0.0. Before: the pose turned both knees 40-50 deg in (now 26 / 15 deg out, as on
  asd), the twist was fitted across ±180 (own knobs 0.44 cm off the source, now 0.0000), the hip drop reversed.
- **A foot skimming the floor is no contact** (trap 261): `_placement` grows a contact past its step only while the
  point that is down moves slower than the walk travels (`HELD_SHARE` 1.0 of the travel a frame). The right foot
  skimmed 40 cm along the floor for six frames after its step, the lock pinned it, and the pelvis sank 20 cm at
  frame 93 (now 0). Every forward walk on disk the same but sadda (its slide 53.8 -> 17 cm, drop 11.9 -> 10.6).
Tests `test_walkmodel.BackwardTests` (the synthetic walker played backward: fails 4/4 on the old code) and
`SkimTests`; three StepTests / PoseTests read the synthetic foot's 10 cm-a-frame landing as no contact now.
verify_walk 79/79, sprint 12/12, own 22/22; 6819 unit tests. Not re-keyed in the animator's scene.

**…and a diagonal backward walk: the pose on the body, the feet spread across the body** (2026-10-16, the same
day, a backward-right walk and its mirror in the animator's scene: «анимация выглядит так какбуд-то наш
алгоритм перепутал ноги»). The pair's bodies stand ±35° against their own roots (their travel 125° off the body's
front). Two defects, measured:
- **The pose was placed by the walk's ROOT**: the sword pose (side-on, 41° against its own root) read 76° off one
  body and 7° off the other, Leg match turned the hips back 76°, and the feet crossed the body line on 58 of 113
  frames, up to 66 cm (the source: a 24 cm crossover). `pose.body_turn` (the walk's mean hip line against its rest
  stood on the root) turns the carried pose about up through the root (`_turned`) before anything is read: hips
  −41.3° on all three walks; a walk facing its root moves by its own 2-5°.
- **Stance and a pose's width worked across the TRAVEL line**: a side-on stance projected onto it read +64 cm on
  one of the pair and −41 on the other. Both now spread the feet along the body's own left-right
  (`Walk.across`, the flat mean hip line; `print_across`, `body_print`) - for a forward walk the same axis to a
  few degrees. The pair now come out alike (closest 39 / 39 cm, mean 21); at Stance below 1 a diagonal walk's
  feet now narrow by the whole knob (before, only its across-travel part).
Tests: `test_walktarget.PoseTests.test_a_pose_stands_on_the_walk_s_body_not_on_its_root` (fails by 35° on the old
code); `verify_walk_sprint.py` gate 2 now reads «hips 41 deg» (36 before: the sprint's body is 4.8° off its root).

260. **A walk's travel axes are not its body's.** The model read "forward" and "the walk's left" off the travel
     and took the body to face it. Walking backward, the knees point near 180 deg off the travel, so an absolute
     heading wraps (an outward knee read as turned in), a hip line read against `side` sits at ±180 (a least-squares
     fit across the wrap is garbage), and a rotation about `fwd` drops the other hip. Measure body quantities in the
     body's own axes; a frame turned 180 deg about up keeps every difference and handedness.
261. **Near the floor is not planted.** A contact grown by height alone (heel or ball within 1.5 cm of its low)
     took a foot skimming back along the floor at up to 15 cm a frame; Foot placement pinned it there and the leg
     could not reach. A contact needs the down point HELD too.

**…a raised pelvis without knee clicks** (2026-10-16, `asd` under DG_Idle with Pelvis height +11.45 on the
animator's Manny skeleton: «сильно дергаются колени»; read over 7001, reproduced in mayapy to the degree). The
knees snapped 10-19 deg a frame where a leg reached its limit (the walk's straightest, 0.993): a swinging leg
asked for 1.5-3 % past it sat clamped there for five frames; a stance leg was held exactly at it by the drop's
cover; and the foot's roll came in 10-15 deg in one frame at the strike and flipped toes up -> heel up 15-22 deg
in one frame at the heel-to-ball handoff. Three changes in `_lowering`:
- the roll changes no faster than `ROLL_RATE` (100 deg a stride; `rate_limited`, the lower Lipschitz envelope -
  only ever LESS roll: a cover put roll on frames that asked for none and slid the planted foot 0.56 cm); the
  pelvis's drop takes the rest;
- once the stance legs fall short anywhere (eased in over `MARGIN_FULL` 2 cm, so the defaults are untouched) every
  leg is held `LEG_MARGIN` (0.8 %) of its length short of its limit; a foot coming down to its print holds the
  pelvis by (1 - swing_weight);
- a swinging foot past its reach is drawn in toward its hip by a smooth cover over the excess (`ctx["reel"]`,
  `_reel_of`, x swing_weight in `_leg`) instead of clamped.
On the scene: the knees' least 22.2 / 17.2 deg (was 13.7 / 12.4, clamped), the worst second difference 8.0 / 7.5
deg (was 17.7 / 18.1; the walk's own at height 0: 11.0 / 6.1). The cost: past the reach Pelvis height gives
up to ~1.5 cm less than asked (`verify_walk.py` gate 73: dw +8 -> +6.75). A soft clamp letting legs straighten
past the limit was tried and dropped: the target's retarget sank the pelvis back to the limit, and the knee still
crossed 18 deg in a frame (near straight the angle is a square root of the distance). Tests
`PelvisHeightTests` (rolls without a flip, legs off the limit); `verify_walk.py` 79/79, sprint 12/12, own 22/22.

**…and Foot flat** (the same evening, the same walk under LongSword_Idle_3P: «носки дергаются и немного торчат
вверх», under Dagger_Idle_01 «вроде как все хорошо»). After the strike a stance leg short of its reach rocked its
foot back on its heel (the toes-up reach roll, up to `ROLL_HEEL` 15 deg) - the ball 4.4-5.3 cm over the floor
for five frames, the toes 2-5 deg up and wavering; the dagger pose stands lower and needed none. Knob **Foot
flat** (`foot_flat`, Legs, sided, 0..1, default 1): it scales that roll's cap by (1 - flat) in `_roll_cost`, so
at 1 the landed foot lies as the walk's own (ball 3.3 -> 2.4 cm, toes -2..-4 deg - equal to the dagger's) and
the pelvis's drop reaches instead; the heel-up roll at the push-off is untouched. Test
`test_foot_flat_keeps_a_landed_foot_flat_on_the_ground`; verify_walk 79/79, sprint 12/12, own 22/22.

266. **Near straight, a knee is a square root of its reach.** A smooth hip-to-ankle distance touching the limit
     (a cover's peak) or clamped at it is a V or a plateau in the knee angle: 1 % of reach is 10 deg there. Keep a
     leg a little short of straight wherever something else has to give, and smooth what moves the ankle (a roll
     switching pivots) in time.

## Camera Shake: handheld filming and an impact, on a layer of their own (2026-10-13)

The animator: «Нужно реализовать отдельный от нашего плагина скрипт (после тестов мы вставим его в наш плагин).
Скрипт нужен для создания процедурной анимации камеры … я выбираю участок на таймлайне, выставляю разные
параметры а скрипт делает на дополнительном слое анимацию камеры … 1 - режим реальной съемки … покачивания и
микро тряска. 2 - режим удара … Камеру тряхнуло, она вздрогнула и успокаивается». Asked, all four the
recommendation: **the selected camera** (nothing selected: our `SceneSetup_camera` when there is exactly one),
**one additive layer per press**, **an impact is a kick plus a rattle**, **live tuning**. Spec
`docs/superpowers/specs/2026-10-13-camera-shake-design.md`, plan beside it. Built **outside the plugin** first
(`docs/superpowers/plans/camshake/skeldar_camshake.py`, dropped into a viewport); **in the plugin the same day**
(«Давай встроим скрипт камеры в наш плагин»): `git mv` to **`SkeldarAnim/maya_camshake.py`** (a payload row),
its window replaced by the hub card **Camera Shake** (Animation, after Walk Builder, Tabler `video`); hotkey rows
`window.camshake` and `camshake.apply` (`maya_hotkeys._camshake`: with the card closed it presses with the
remembered settings and says its line in the viewport). The optionVars kept the script's names, so what was
set there comes back. The verify and the picture's renderer stay in `docs/superpowers/plans/camshake/` and load
the plugin module.

- **The model** (numpy): a smooth noise - Gaussian knots through a uniform cubic B-spline, unit RMS by the
  spline's own mean variance, knots in seeded blocks of 64 so a longer range keeps its start; **5.57 knots a
  cycle** (measured: such a spline crosses zero 0.359 times a knot), so "Hz" means swings a second as a sine's.
  Every frequency below 0.42 x fps; an amplitude is two RMS.
  - **Handheld**: Sway (a 3-octave fractal from 0.25 Hz x Speed; tilt 0.75, pan 1, roll x Roll), Jitter (deg)
    at **Jitter, Hz** (its own rate since the same evening, «как изменить его частоту?»; Speed is the body's),
    Drift (cm, a 2-octave fractal from 0.2 Hz; side 0.7, bob 1, push 0.4), Ease in and out. Presets Calm /
    Handheld / Nervous (2.71 / 7 / 9.5 Hz; Calm is the animator's own since 2026-10-14 - sway 2.57, speed
    0.49, jitter 0.07, roll 0.38, drift 6.04 cm - and the one preset that sets Ease, to 0).
  - **The jitter and the rattle are a narrow-band `tremor`**: a sine at their Hz whose amplitude swells and
    fades (0.45 RMS) and whose phase wanders (0.6 rad), both at Hz/7 - a hand's tremor is a rhythm. Trap 238
    is why it is not the smooth noise: it shows 10 Hz as 10 swings a second at 30 fps (gated to 10 % up to
    12 Hz) where the noise showed 7.15.
  - **Impact** over `[a, b]` (since the same evening, «нужен параметр который будет отвечать за длину волн и
    тип затухания»): a sine from the hit, **Wave** frames crest to crest (never under 2.38, the alias limit),
    under a **Decay** envelope across the range - Exponential (`e^-4u` brought to 0: a fast fall, a long thin
    tail), Linear, Smooth (`1 - smoothstep`: holds, then fades), Sharp (`(1-u)^6`: gone in the first waves) -
    1 at its first crest (found by a ternary search on the first lobe). It turns the view toward where the hit
    throws it (Below / Above / Left / Right / Front / Random), Push along it, roll for a side hit, a
    perpendicular wobble at 1.37x the rate, a rattle (a tremor at **Rattle, Hz**) under the envelope squared;
    still at `a` (the jolt is
    `a+1`) and at `b`. Swing and Bounce are gone (an older layer's record re-tunes with Wave 8, Exponential).
    No highlight: the current frame + Length. Presets Light / Hit / Heavy / Explosion / Recoil, each with its
    wave and decay.
  - **Axes** (both modes): Tilt / Pan / Roll checkboxes; one switched off removes that turn about the camera's
    own axis whole - the waves, the wobble, the rattle, the jitter (the push and drift are moves, not turns,
    and stay).
- **Onto the camera, exact**: a rotation `S` about the camera's own axes and an offset along them; the new euler
  is the one of `RA^-1 . S . RA . R(e)` nearest the base (both solutions, every 360; Maya's six orders by
  permuting the axes onto xyz), the offset `d . (RA . R . JO)`. The layer adds by component
  (`rotationAccumulationMode` 0), so the camera shows `S . M` on every keyed frame. The base is the camera's
  rotate read through every layer (`getAttr(time=)` after dirtying the curves upstream, trap 236) minus this
  layer's own share x its weight.
- **The layer**: `CamShake_<Mode>_<a>_<b>` (`m5` for -5), additive, marked `skeldarCamShake` (JSON: mode,
  settings, frames, the cameras' UUIDs), **locked** after writing (a later key of the animator's lands on the
  base layer, gated); keys on every frame (spline), 0 a frame outside each end (flat) with `a`'s in and `b`'s
  out tangent linear: nothing leaks, not between frames. Translate only when Drift / Push > 0. Refused, by name,
  before any change: nothing to shake, a channel driven by anything but time curves and layers (a constraint
  on a camera's target says which camera to select), a 1-frame range. One undo chunk a press.
- **The card** (cmds + the hub's marks), top down: the subtitle (the shake edited, else «New impact shake on
  SceneSetup_camera, frames 45-70 (the highlight)»); Shake (+ New shake and every shake of ours) with a Delete
  tool button; `[Handheld | Impact]` segments; Preset; Tilt / Pan / Roll chips (checkBoxes in a flow); the
  mode's column (Impact: Hit from, Decay, then the sliders); Seed + New seed; Apply (primary); the status line
  (also the hub's message line). A released slider, a preset, a chip, the direction, the decay or a new seed
  **re-keys the picked shake** on its own cameras and frames, else «Set for the next Apply.»; a shake newly
  selected in the Anim Layer Editor is picked (`animLayerRefresh`, remembered per card); Undo / Redo show its
  settings again. Four jobs per card (SelectionChanged, animLayerRefresh, Undo, Redo), parented to the status
  line and keyed by the card (`JOB[scope tag]`), so a popup copy's die with it. **Every named control is a
  command `maya_hubcopy` can scope** - no `checkBoxGrp` / `radioButtonGrp`, which a copy would not rename
  (a test pins it). Settings remembered per mode (`skeldarCamShake_<mode>`, JSON) and the mode
  (`skeldarCamShake_mode`); the picked shake on `sys` (trap 111).

Proof: `tests/test_camshake.py` **68** (the noise, the tremor's rate in frames, the envelopes, both modes, the
waves' period and decay types, the axes, the algebra against OpenMaya on every order with rotate axes and joint
orients, the card on a fake cmds - 73 since the card); `verify_camshake.py` **29/29 mayapy standalone**, on the
plugin module too (gate 15: a hit from the left with Pan and Roll off turns
the camera about its own X only, 2.8e-16 off it): the shake in the camera's own axes on every frame to
**2.8e-16 deg**, the translation exact, the
camera's own keys untouched, nothing outside the range at quarter frames, a re-tune keeping the layer, its
weight and lock (doubling the settings doubling the shake to 0.4 %), one undo each, an impact stacked on the
handheld exactly (1.4e-16), a hit from below throwing the view up 4.2-4.3 deg, two cameras each their own shake,
a joint (orient, yxz) exact, refusals changing nothing, a 300-frame shake applied in 0.07 s and re-tuned in
0.08 s, and on the plugin's Manny with Camera Setup, nothing selected: the SceneSetup camera shaken and
`camera_root` following it to 8e-16 - the shake reaches the export. Picture
`docs/superpowers/plans/camshake/camshake_curves.png` (`render_camshake_curves.py`, offscreen Qt with Windows'
Segoe UI loaded - offscreen Qt draws boxes otherwise). **The card in Maya is the animator's to try** (no GUI
Maya of ours): not seen live yet, nor a popup copy of it.

**Apply replaces the shake of its own mode** (2026-10-15, «при нажатии apply должен сам удалить существующий
слой и наложить новый ... определять с каким слоем ему работать, с слоем импактов или слоем ручной камеры»):
a camera keeps ONE handheld layer and ONE impact layer. Apply in the card's mode takes off every shake of
that mode holding any of the cameras it shakes (`replaced`, `_take_off`) and lays a new layer (weight 1,
locked) - at whatever frames, so a second impact moves the impact rather than adding one; the other mode's
layer is never touched. A layer shared with cameras not being shaken keeps them: only these cameras'
channels leave it (`animLayer -removeAttribute`, its curves with them) and its record names the rest. Nothing
selected, Apply takes the picked shake's cameras when it is of the card's mode (`apply_targets`). The
subtitle says «... - replaces CamShake_Impact_40_60», the line «| replaced ...». One undo puts the old layer
back. A new layer whose name is still taken gets `_v2` (Maya would bump the last frame: `0_60` -> `0_101`).
Before this, Apply reused a layer only with the same mode, frames AND cameras, else stacked a new one.
`verify_camshake.py` **33/33** (gates 15, 17-19, 21, 25 new); 75 unit tests.

Not built: an operator walking (step bob), a pivot behind the lens, translation in the rattle, moving a shake's
range after Apply, several impacts on one camera (a second Apply replaces the first).

236. **A DG context read keeps a stale value per time.** `getAttr(plug, time=t)` after a key at `t` was edited
     answered the OLD value (measured in mayapy: 0.0 where the curve now said 20, then 30 after a second edit
     to 40) - a different time (`t + 0.0001`) read fresh, and `dgdirty` on the PLUG did not help; `dgdirty` on
     the edited CURVE did. A tool that reads a channel through animation layers at other times dirties every
     curve upstream first (the layers' blend nodes, their curves, the layers' weight curves).
237. **A layer's rotation blend node reads its channel's owner.** `animBlendNodeAdditiveRotation.rotateOrder`
     is connected from the camera's own `rotateOrder`, so a walk upstream of `rotate` meets the camera itself
     and calls it a driver - the first re-tune of every shake was refused. Leave the owner out of the walk.
238. **A broad-band noise sampled once a frame cannot swing faster than a quarter of the frame rate.** White
     noise changes sign on half the frames: 7.5 swings a second at 30 fps, 6 at 24. The camera shake's smooth
     noise asked for 10 Hz showed 7.15, for 7 Hz 6.12 (measured), so a "Jitter, Hz" slider over it did almost
     nothing above 5. A rhythm (a sine whose amplitude and phase drift slowly) shows its own rate up to the
     frame rate's limit. Measure a rate on the keyed frames, not on the function.

## Pose on clip: our poses onto a locomotion clip, a separate script (2026-10-14)

The animator, after asking how a start/stop builder could work («наша главная задача - на одну базовую
анимацию уметь накладывать любые аддитивные позы и добиваться хорошего результата»): «насаживать наши позы
на локомоушен циклы такие как вот стоп ... отдельным скриптом и не трогать наш плагин ... не рисуй интерфейс».
Asked, all three the recommendation: the result on **a copy of the character beside** the original; **the pose
plus the clip's motion** (the sprint's lean and the brake's crouch ride on the pose); the stop **ends in the
pose's stance**. Spec `docs/superpowers/specs/2026-10-14-pose-on-clip-design.md` (read its addendum), plan
beside it. **Nothing in `SkeldarAnim/` changed.**

- **Where**: `docs/superpowers/plans/poseclip/` - `poseclip.py` the model (numpy + `posemath`), `poseclip_maya.py`
  the scene, `posemath.py` / `skeletonmap.py` / `manny_skeleton_template.json` COPIED from the plugin (one import
  line changed), `verify_poseclip.py`, `render_poseclip.py`, `poseclip_stop.png`. From the Script Editor, the
  character selected: `poseclip_maya.apply("goblin")`, `apply("two_handed_sword", share=0.7, motion=0.8,
  parts=(...), offset=-150)`. Poses are Walk Builder's `.wpose.gz` (SkeldarWalks). One copy a pose per
  character (a second apply of the pose replaces it), `offset` cm to its right (negative: left). One undo step.
- **The model**: the clip's **reference** is its longest still run (every body bone under 1.5 cm a frame; the
  stop's idle 69-142); the pose (posemath.Transfer onto the clip's skeleton placed at the reference) takes its
  place. Torso, head and pelvis: `T . G(f)^motion` with `G` the clip's motion in WORLD axes about the
  reference; arms and fingers: locals; pelvis height in proportion (`h' = T_h (1 + motion (h/h_ref - 1))`);
  each foot's contact moved by ONE rigid motion of space (the last contact onto the pose's stance, about the
  reference's ankle midpoint), blended between contacts, so a planted foot stays planted and the clip's own
  skid stays; legs by IK with the clip's lengths; the pelvis sunk (non-periodic cover, iterated) where a down
  foot is out of reach; the pelvis carried so `CoM - support` is the clip's (+ the pose's own, by stillness).
- **Three rules the real stop asked for** (the goblin: 85 cm stance, 54 deg trunk, CoM 15 cm aside): a stance
  (the pose's extra width on earlier steps, its balance over its feet) comes in with the body's **stillness**
  (1 - CoM speed / 240 cm/s) - a sprint's steps take none; and the clip's **forward lean takes the room the pose
  leaves** to horizontal (x0.41 goblin, x0.95 sword) - before, the trunk reached 94 deg and the head 37 cm.

Proof: `verify_poseclip.py` **18/18 mayapy standalone** on `M_Neutral_Sprint_Stop_F_Lfoot` (Unreal's Game
Animation Sample, from the bridge's temp folder - not in git) keyed onto the plugin's Manny UE5 skeleton by the
tool's own writer: share 0 plays the clip (9e-12 cm), the copy's mesh on the copy's joints, motion 0 stands in
the pose (0.0000 deg, 0.0000 cm), planted feet never move more than the clip's (0.0006 cm), bone lengths
1.8e-13, the CoM rule 0.005 cm, the grip 5e-13, the labels, the original's curves, replace and one undo;
`tests/test_poseclip.py` 28. Live in the animator's Maya (7001): the goblin to the right, the sword to the left
of their stop, 15 s for both, measured read-only after: feet 0.0000 over the clip's, lengths 1e-13, grip 6e-13.
Not built: rigs as targets, turning clips, the arms' inertia, a share that changes over the clip, non-UE clips.

**…as one tool, a window** (the same day: «Собери все скрипты в один инструмент ... выделил нужный мне цикл бега и
дальше мог работать применять позы и парамметры коррекции»; spec addendum 2). **`poseclip_tool.py`, dropped into a
viewport**: Use selected (any part of the character; nothing - the only keyed one), the pose menu, twelve knobs
(each part's share; the clip's motion in trunk and arms; pelvis height and forward in cm; stance width x, the
speed a stance is gone at, the forward-lean limit) and the copy's offset, each re-keying the window's ONE copy in
place when let go (one undo step each). The clip is read once a session (`poseclip_maya.Session` on
`sys._skeldar_poseclip`); the synthesis builds the body above the legs once a frame and the balance and reach only
move it (0.3-0.8 s, 3-10x faster, the same result to 1e-13); a re-key 1.4 s standalone. `verify_poseclip.py`
22/22. Opened in the animator's Maya over 7001.

**…overlap, a start and a final pose, the stop starting on a cycle** (the same day: «такую же оверлеп систему как и
walk builder ... стартовую позу и финальную ... начинал анимацию остановки в цикле а заканчивал уже в указанной позе»;
spec addendum 3). Start pose on the run, the final as the body stops (`final_speed`, the stance's stillness);
Walk Builder's trunk / head / arm springs (`torso_drag`/`_bounce`, `head_drag`, `arm_drag`/`_bounce`, its
defaults) run forward from frame 0 at rest, the pivots' accelerations off paths blurred over 2 frames; **Use
selected as cycle** reads a looping clip (a Walk Builder skeleton, any loop; period from the closing frame, a
repeated end frame dropped, any frame rate): the phase whose first frames match the stop's best, placed by the
stop's planted foot and its root's travel, frame 0 the cycle's (4e-10 cm), `from_cycle` frames into the stop with
a foot the stop has planted held on its place. `knobs_from` (the script's `apply`) keeps the overlap off.
`verify_poseclip.py` 25/25, `tests/test_poseclip.py` 36.

**…Walk Builder's tools, and the cycle's posture as the start** (the same day: «такие же инструменты которые бы
контролировали веса позы и все остальное ... опцию которая будет за основу для старта брать позу исходного цикла»;
asked, all three the recommendation: everything of Walk Builder a stop has a use for, the cycle's posture read off
its frames, each pose a share plus part chips; spec addendum 4 and its "What the build changed").
- **The window** is Walk Builder's card:
  - Final pose and Start pose, each a menu, a Share and the chips Torso / Pelvis / Knees / Arms / Feet (knobs
    `share_<part>`, `start_<part>`); the start menu offers `(same as final)` and `(the cycle's posture)`;
  - `[Both | Left | Right]` for the sided knobs (`<name>_l` / `_r`, `model.sided`; Both links them again, a knob
    whose sides differ is marked *);
  - a tabLayout `[Stop | Legs | Pelvis | Chest | Arms | Weight]`.
  - The optionVars are the truth (`knobs_from_memory`), since a sided slider shows one side.
- **New knobs**: Stance (was Width), Foot lift, Swing out, Leg match, Leg turn, Knee <-> foot, Foot lag / flex,
  Bob, Pelvis motion, Spine (was Torso motion), Gait lean, Head, Arms (was Arms motion), Elbow, Balance,
  Exaggeration.
  - **Leg match**: running, a side-on pose's hips face the run (the pelvis's turn given to the lumbar spine), the
    knees and toes keep their splay x `1/(1+Fr)`; standing, the pose as it is.
- **The cycle's posture**:
  - the trunk is the cycle's mean WORLD turns over the stop's run mean (exact: each trunk bone sits off it as
    the clip sits off its own run mean);
  - the arms are local means;
  - the knees, toes, hips and height come from the GAIT (`gait`: on the frames each foot is down, against the
    travel). The mean posture's running foot points backwards, and the stop's brake plants a foot across, so
    the stop is read only at speed (`RUN_SHARE`);
  - Leg match leaves it alone.
- **The toes' turn turns the whole foot rigidly**: about the contact's point on the ground, about itself in the
  air. A rolling foot no longer slides (the goblin's ball 0.55 cm a frame before).
- **Live, the animator** («после применения не меняется поза»):
  - the start on the cycle's posture with no cycle refused every Apply; it now falls back to the final pose
    and says so;
  - a weapon they put in the copy's hand killed the re-key (`weapon_r` constrained); a channel something else
    drives is now left to it and named.
- **Proof**: `verify_poseclip.py` 30/30, 58 unit tests, `poseclip_cycle_posture.png`.
- **With no cycle loaded, `(the cycle's posture)` is the clip's own run** (`poseclip.OWN_RUN`: no pose on the
  run, the final as it stops; the copy's label «own run > <pose>»). It first fell back to the final pose, and the
  animator read that as «the cycle posture does not work». The status line names the frames the start holds.
- **The left arm exploded at frame 15** under the sword with Arm drag 2.74: trap 245, fixed in every IK of the
  model (legs, the grip, the grip's springs, the start on the cycle); measured in the animator's copy the left
  upper arm 98-171 deg a frame before, 7-29 after (the springs' own whip). 60 unit tests.

244. **A mean posture of a gait is no stance.** The cycle's mean local turns put the running foot pointing
     backwards (-150 deg - half a run it is kicked up behind), and a stop's "run" read by its stillness includes
     the brake, where a foot plants turned 105-133 deg across. Read a gait's knee and toe lines on the frames the
     foot is down, and a stop's at speed. And a correction held still on a contact must be the EXTRA over the
     contact's own motion, applied about the contact's point - a total held still, or a turn about the ankle,
     slides a foot that rolls onto its ball.
245. **A two-bone IK's plane read back off its knee is noise when the limb is straight.** `two_bone` puts the
     knee off the hip-ankle line toward the hint; stretched to its length (a goal past reach) the knee lies ON the
     line, and every caller that re-read the plane as `unit(knee - its projection on the line)` got a zero vector's
     direction: the animator's two-handed grip, its held hand carried 8 % past the left arm's reach by the arm
     springs, flipped the left arm 98-171 deg a frame («на 15 кадре происходит взрыв левой руки»). Read the plane
     from the hint (`poseclip.bend_side`, what `two_bone` itself bends toward), in every caller.

240. **The plugin LOCKS its clip label's marker** (`cliplabel._write` unlocks around its own write), so a tool
     writing `skeldarClipLabel` dies on «is locked or connected». The verify's Manny had no label and passed;
     the live scene's, imported through the bridge, had one. Give a verify the furniture the real scene has.

## The Pose Library: any object beside the character, found again on load (2026-10-15)

The animator: «объекты которые не относятся к ригу мы не сохраняем ... мы сохранили наш риг и камеру ...
поиск камеры с учетом того что в другой сцене на ней уже может быть немспейс (... только для тех объектов
которые находятся в выделении)». Asked, all three the recommendation: an unselected saved object is still
posed when found by its exact path; the transform's AND its shape's channels (a camera's focal length);
poses and animation cards alike. Spec `docs/superpowers/specs/2026-10-15-pose-library-any-objects-design.md`.
**This replaces "objects selected beside one character are left out" above.**
- **Body or object** (`scene.is_body` / `scene.split`): the body is a joint, anything under a rig's AS
  `Group`, a skinned mesh, a group holding the skeleton or the rig, a weapon or armour piece. Everything
  else is an OBJECT - a camera (Camera Setup's `Manny_Rig:SceneSetup_camera` too, which used to count as
  the rig and name the whole body), a knot, a locator, a prop - whoever's group it stands in.
- **A character card holds its objects** (`objects`, records from `maya_poselib/objects.py`:
  `name` without namespace, `path`, `attrs`, `shape` {attr: value / curve}, `own` = the card's
  character's). Objects alone selected: an objects card, as before, now with `shape`.
- **Load** (`objects.pair_card`, pure; `found_for`): the selected objects pair as an objects card always
  did (path, name with the namespace ignored, order); the card's objects left over are found - an `own`
  one in each TARGET character (its namespace + name, or by name under its character group), so a pose
  saved on `Manny_Rig` keys `Manny_Rig1`'s own camera; any other by its exact path only; what is not
  found is said («not in the scene: shotCam»), never searched for by name. Selected only: the
  selection alone. A character card with only objects selected poses them alone and says so. Mirror
  leaves objects unmirrored (said). An animation card's object curves go in the character press's one
  undo chunk (`animapply._key_objects`).
- Every new function that touches the scene takes the caller's `cmds` (`objects.plugs_of(record, path,
  cmds)`) or lives on `scene`, so the tests' fake `cmds` / `FakeScene` reach it.
Proof: `docs/superpowers/plans/verify_poselib_objects.py` **25/25 mayapy standalone** (two Manny rigs with
Camera Setup, a free camera moved into a `shot:` namespace after saving, a locator): B's own camera
takes A's camera's values, `shot:shotCam` its values and focal length by name, the prop by path, A's
camera untouched, one undo each; B alone - the shot camera not searched for, said; the camera alone -
B untouched; the animation's curves and focal length on all three, one undo); `tests/test_poselib_objects.py`.

## The radial menu: hold alt+q, point, let go (2026-10-15)

The animator: «я зажимаю какую-то клавишу появляется радиальное меню ... можно поместить как и раздел так
и отдельную функцию раздела ... раздел -> попап раздела (если он уже был открыт где-то то он должен
открыться в новом месте возле курсора мышки) ... двухэтапная кнопка например AIM - попап финиша действия».
Asked, all four the recommendation: hold-and-release (a tap keeps it up for a click), **alt+q** in the
SkeldarAnim hotkey set, an editor card, 8 slots and no submenus. Spec
`docs/superpowers/specs/2026-10-15-radial-menu-design.md`.
- **`maya_radial_rules.py`** (stdlib): slots clockwise from north (`slot_at`, `slot_position`,
  `pill_anchor` - east labels grow right, west left), items `"section:<key>"` / `"cmd:<hotkey row>"` in the
  optionVar `skeldarRadialSlots` (JSON of 8, broken -> `DEFAULTS`), `TWO_STEP` (`tools.knot_offset`,
  `tools.aim` and the knots function asking whether each waits), `release_action`.
- **`maya_radial.py`**: `press()` / `release()` are the hotkey rows `radial.press` / `radial.release`.
  - The press reads which ordinary keys are down (Win32 `GetAsyncKeyState`) and a 16 ms timer calls the
    moment they are all up the release. Maya's release command acts only then too: it may come early
    (auto-repeat) or never (focus elsewhere).
  - The overlay: a frameless translucent `Qt.Tool` over the cursor's whole screen (alpha 1, so a click
    anywhere lands on it), never taking focus.
  - A section opens its popup by the cursor (**`maya_hubpop.open_at`**: the viewport under the point;
    one already open is closed and reopened there, unrolled). A header-only section opens the hub.
  - A function runs through `maya_hotkeys.run`. A two-step one left waiting gets the **Finish popup**
    (Finish runs the row again; X leaves the tool waiting; it closes itself when nothing waits); its slot
    reads «Finish Aim» meanwhile.
  - Esc, the right button or a click off the slots closes the menu.
- **The card** «Radial Menu» (Settings, Tabler `aperture`): **Slots** 2..12 (2026-10-16, «возможность
  указывать количество разделов»; optionVar `skeldarRadialCount`, 8 by default), then one row a slot -
  its direction (`rules.direction`: the compass point, else «30 deg») and its item (left click: Empty /
  Sections / one submenu per hotkey category; right click: Clear); rows past the count hidden, their
  items kept (`skeldarRadialSlots` holds `MAX_SLOTS` 12). Reset to defaults (8 slots, the default
  items), **Bind alt+q** (into the current set, only when it is ours). Each slot is 360/count degrees;
  past eight the ring widens (`ring_radius`: 112 x count/8).
- `maya_hotkeys`: `RELEASE_ROWS` gives a key its release nameCommand (`bind_row`, which `bind_defaults`
  now calls per row); `DEFAULT_KEYS` + alt+q, version 7 (the next switch of the hotkey map binds it).
- Proof: `tests/test_radial_rules.py`, `tests/test_radial.py`, the hotkeys' release binding;
  `docs/superpowers/plans/render_radial_menu.py` draws the menu (hold and click) and the Finish popup
  offscreen (`radial_menu.png`). **Not seen in a live Maya**: the key's hold and release, the overlay's
  focus and clicks, a popup opening by the cursor - the animator's to try after Check update.

**…and it moves** (2026-10-16, «элементы появлялись с анимацией из центра ... подсвечивались и
увеличивались немного в размере ... скрывались анимацией как бы съезжаясь в центр»; shown first as a
live HTML demo beside the hub proposals, https://claude.ai/artifact/KYPDH1djZXZS3vXeKPA9jA - the
animator picked hub layout C, a rail and one card, for later). Spec
`docs/superpowers/specs/2026-10-16-radial-menu-motion-design.md`.
- **The timing is pure** (`maya_radial_rules`): `item_open` (ease-out-back from the centre,
  `OPEN_MS` 200, slot i `OPEN_STEP_MS` 18 after slot 0 - clockwise from north; the menu opens AT
  the cursor, so its direction gives no order), `item_close` (ease-in back in, `CLOSE_MS` 140, the
  last slot first, 12 apart), `ring_open` / `ring_close`, `pose(u)` (place, size from
  `START_SCALE` 0.3, opacity), `approach` (a lift over `HOVER_MS` 110), `lifted_scale`
  (`HOVER_SCALE` 1.10), `FLASH_MS` 120.
- **`Menu.phase`**: "open" (opening or up), "fired" (the chosen pill solid accent and flashing; the
  item runs when the flash ends), "leaving" (back into the centre, then destroyed). `close_menu()`
  moves a menu to `_state()["leaving"]` and lets it play; a new press `drop_leaving()`s it. A
  leaving menu paints no alpha-1 veil (clicks go through to Maya) and takes no clicks. The pointed
  pill: a lighter face, 2 px accent outline, accent glow rings, 1.10 times, the pointer line fading
  in with it (it used to turn solid orange at once - that look is the chosen one's now).
- **⋮ -> Interface animations off** (`animated()` = `maya_hubmotion.enabled()`): shown, run and
  closed at once, as before.
- `paint(widget, now=None, device=None)` - a test or a renderer draws on an image.
Proof: `tests/test_radial_rules.MotionTests` (11), `tests/test_radial.MotionTests` (6, offscreen
Qt on a fake clock: the ink grows from nothing, a lit pill draws more, the flash then the close then
the run, no veil while leaving, off = at once); 6782 unit tests OK;
`docs/superpowers/plans/render_radial_motion.py` draws the filmstrip `radial_menu_motion.png`.
**Not seen live** (the animator's to try after Check update).

259. **`QColor(image.pixel(x, y))` is always opaque**: `QImage.pixel` answers an ARGB int and
     `QColor(int)` reads it as RGB, alpha 255. A test counting painted pixels by alpha read every
     pixel as ink. Use `image.pixelColor(x, y).alpha()`. And `widget.render()` of a never-shown
     translucent window fills its background: draw on the image through the paint code instead.

## Scene tabs: several scenes in one Maya, switched like browser tabs (2026-10-15)

The animator: «Возможно ли в maya сделать вкладки как в браузере что бы открывать разные сцены а не запускать
сразу несколько программ?» - then the references route: «мы нажимаем на вкладку и все объекты которые она
референсит скрываются и деактивируются, изменяется найтройки вюпорта, открываются старые окна и показываются
новые». Asked: tabs are for all three of working on several scenes, carrying things between them and looking
at a scene beside the work; approach A (imports, not references); one shared undo history; the bar above the
viewport; each tab its own whole layout. Spec `docs/superpowers/specs/2026-10-15-scene-tabs-design.md` (read
its planning addendum), plan `docs/superpowers/plans/2026-10-15-scene-tabs-stage1.md`. Stage 2, the plugin seeing only the active tab, is `2026-10-15-scene-tabs-plugin-scope-design.md` (its
planning addendum), plan `docs/superpowers/plans/2026-10-15-scene-tabs-stage2.md` - built with stage 1: stage 1
alone doubles the tab's prefix on everything the plugin creates.

- **`maya_scenetabs/scope.py`** holds the three rules; with tabs off every function is the identity. **A reader**
  keeps the active tab's paths (`active_only`): `maya_rigs.rigs()`, `builder.character_roots()`,
  `animimport.skeleton_roots()`, the colour scan, the studio, the retargets' joint scans, the CoM groups - and
  everything built on them. **The current namespace is the active tab's**: a reset after an import is
  `enter_active`; a clip is imported into a root-level namespace and, when kept, moved under the tab
  (`home_namespace`; a namespace whose move fails stays at the root and the line names it). **A name that
  carries a namespace is made absolute** where a node is created or renamed with it (`as_created`), a name
  given back after a hold is `root_name`; a leaf needs nothing.
- **What the animator reads** is named as the tab shows it (`local`, `relative`): «Manny_Rig's right hand», a
  character group `Manny_Rig_Character`, never `tab_x_...`.
- **The scene is the active tab** for Shared and Stash (a copy of that tab alone, references written in; a
  received scene opens as a tab, without asking to save the current one), Open scene, and the scene's name.
- **A new plugin feature** that lists the scene, creates a node with a namespaced name or names a character in
  a message goes through `scope` - `tests/test_scenetabs_scope.py` and `verify_tabs_scope.py` are the
  reference. Proof 2026-10-15: `verify_scene_tabs.py all` 0 of 138 gates, `verify_tabs_scope.py` 0 of 42, 6638
  unit tests OK.

- **A tab** is a `.ma` / `.mb` imported with `preserveReferences=True, executeScriptNodes=False` into
  `tab_<stem>`; the session is a `network` node `skeldarSceneTabs` (JSON) and the scene is named
  `<userAppDir>/SkeldarTabs/session_<stamp>.ma` (never written by a Save; autosave writes it, and opening it
  restores the tabs - once, even when a SceneOpened job fires inside the open). One scene open is ordinary
  Maya; the second converts it into tab 1 (1 ms, by UUID).
- **Switching** records the tab being left (modified flag, unit, ranges, frame, selection, views, layout) and
  hides it (`lodVisibility`, `hiddenInOutliner`), then shows the new one - ONE undo chunk, so Ctrl+Z past a
  switch brings the tab back before undoing its step.
- **Saving** lifts the tab into the root namespace by UUID, cuts its layer root free (written as
  `BaseAnimation`), writes its ranges into its configuration node, exports to a temp file and replaces the
  tab's file; refuses by name on a root-namespace clash; asks when the file changed on disk. A save puts back
  every step and the undo state even when one step fails.
- **Layers**: the session owns the root `skeldarTabsLayerRoot` (trap 248).
- **Maya's own Save / Open / New** are redirected while two or more tabs are open (the check callbacks), an
  autosave passes; Save prints Maya's «File operation cancelled by user supplied callback» and then «Saved ...».
  A check that fails on an internal error REFUSES (a bar message naming Tabs off) rather than failing open.
- **The bar** (`maya_scenetabs/bar.py`) is a QTabBar in a workspaceControl docked at the top, shown by the
  hub's build (optionVar `skeldarSceneTabsBar`); hotkey rows `window.tabs`, `tabs.next`, `tabs.previous`
  (unbound). **No «Scene Tabs» header since 2026-10-16** («ровная полоска с просто вкладками»): the control
  is made `actLikeMayaUIElement` (Maya's own Status Line / Shelf way, the Time Bar's flag), and one an
  older build made with Maya's tab is edited so, else deleted and made again (`bar._headerless`; it holds
  only the bar, which its uiScript builds). Its X went with the tab: the bar's own menu hides it. Not seen
  in a GUI Maya.

Proof: `docs/superpowers/plans/verify_scene_tabs.py` **0 of 138 gates failed** in mayapy standalone (phases
session, layers_alone, convert, layers, open_close, switch, save, hooks, hook_failures, restore); 6612 unit
tests OK. **The animator's live checks** (none of these can be proven headless): the bar docked above the
viewport; per-tab workspaces and how long a switch takes with them; whether a hidden tab still costs the
viewport anything (if it does, the plan's fallback is the `frozen` evaluator); the quit dialog; Ctrl+Tab free
for `tabs.next`.

248. **Maya remembers its root animation layer internally, and does not promote another.** Closing the tab
     whose `BaseAnimation` was the scene's root deleted every other tab's layers with it; with the root gone
     and layers left, `animLayer -q -root` answered None and the next new layer crashed mayapy (measured
     2026-10-15). A layer's name and connections do not make it the root. Keep one root that never goes while
     anything else hangs below it.
249. **An import runs the file's open-type script nodes** unless `executeScriptNodes=False` (measured) - the
     vaccine malware's road into a scene that only imported a file.
250. **`animLayer -e -parent` rebuilds the layer's blend nodes in the ROOT namespace**, whatever namespace is
     current, and a save's rename of a layer rebuilds some under names of Maya's own (`hero_rotate_Layer2` came
     back `Layer10`). Anything that groups nodes by namespace must bring a layer's blend nodes home after it
     re-parents a layer (`animLayer -q -blendNodes` finds them), and never re-parent to restore a connection it
     cut - put back the exact connections.
251. **Renaming a reference node by hand breaks it**: `referenceQuery -namespace` then raises «Cannot find the
     associated namespace», and a reference's namespace moved and moved back leaves its node renamed in the
     root. Find a reference by its namespace, remove it by its node (`file -removeReference -referenceNode`): a
     path is ambiguous between two copies of one file (`file.ma{1}`).
252. **Maya imports a file's configuration node only when the root namespace holds none.** In a tab (whose
     configuration node sits in the tab) every import brings one, and in the saved file it runs after the tab's
     and wins. Export exactly one.

254. **Maya resolves a creation or rename name relative to the CURRENT namespace, even when the name carries
     one.** With a tab's namespace current, `createNode(name="tab_x:Rig:Holder")` made
     `tab_x:tab_x:Rig:Holder` and created the missing namespaces silently - the retarget then set an attribute
     on a node that did not exist. Lookups (`ls`, `objExists`) go from the root, so the code read and wrote two
     different nodes. Make a namespaced creation name absolute (`":" + name`); `namespace -add x` adds under the
     current namespace, `-add :x` at the root.
255. **A node made by an absolute name is answered without the leading colon** (`":A:x"` -> `"A:x"`). A fake
     `cmds` that echoes the name it was given answers `":A:x"`, and a test then compares paths Maya never makes.
256. **"The outermost namespace" names the tab.** A message's character (`split(":")[0]`) read «tab_plain's
     right hand» and a clip label «tab_plain» once every node carried the tab's prefix. Read a path the animator
     sees through `scope.local`.
**A paste from another tab is folded on save** (2026-10-16, the animator: «сцена не сохраняется»).
Maya's Copy / Paste from tab A into tab B keeps A's namespace under B's current one
(`tab_B:tab_A:Maya_Blinn4`, a MaterialX shader, its SG, a `materialXStack1` and an empty
display layer measured in the live scene), and every save of B then refused - `lift` moves a
tab's child namespaces into the root, where tab A holds that name: «cannot save tab_B: the
scene already holds a namespace tab_A». It went to the bar's inViewMessage and the scene stayed
`*`. `session.fold_pasted` (called first in `saving._save_tab`) folds a child namespace named
like a tab of the session (or `tab_` + taken at the root) into the tab for good -
`namespace -moveNamespace -force` (measured: clashing nodes renamed `mat` -> `mat1`, clashing
child namespaces `Bow` -> `Bow1`, locked nodes moved), the emptied namespace removed - and the
line says «nodes pasted from tab_A are this tab's own now». The file holds them under plain
names, which is what a paste between two Mayas gives. `verify_scene_tabs.py pasted` 8/8, all
**0 of 201**; saved live in the animator's scene (the files from before in
`SkeldarTabs/before_save_20261016_091023`, a whole-session copy `rescue_20261016_090505.ma`).

**…and the temporary file keeps the extension** (the same morning): with Maya's «Default file
extensions» preference on (`file -q -defaultExtensions`), an export to `X.ma.skeldartmp` writes
`X.ma.skeldartmp.ma` (measured), and the rename after it died «[WinError 2] The system cannot
find the file» - the save failed and left the file beside the tab's (the animator's Knife folder
held `AS_DG_ATK_JA_01.ma.skeldartmp.ma` and `…skeldartmp.ma.skeldartmp.ma`). The temporary is
`<stem>.skeldartmp<ext>` now; a save gate runs with the preference on.

257. **A save renames nodes, not strings.** A camera's `imageName` (`tab_plain:camera2`, the name it was
     created with) and an FBX's display layer (`tab_plain:DeformationJoints`) keep the tab's prefix. Neither
     names a bone; a gate that searches a whole file for the prefix fails on them - gate the node names.

**The Anim Layer Editor shows the active tab as a scene** (2026-10-16, the animator: «вижу какие-то
анимационные слои даже в новой вкладке ... когда я выделяю нижний слой то ... выделяются все слои»).
Maya's editor walks from the root, so it drew our holders as layers: `skeldarTabsLayerRoot` alone in an
empty tab, `<tab>:AnimLayerRoot` between the base and a tab's layers. And the animator's root carried
`collapse` on, where Maya's `animLayerEditorOnSelect` selects a collapsed layer's children.
`maya_scenetabs/layereditor.py` reads Maya's `layerEditor.mel` and changes three lines in two procs:
- `rebuildAnimLayerEditor`: a layer under a tab's root sits at the top; the root reads BaseAnimation
  and a tab's layer reads its name without the prefix;
- `animLayerEditorOnSelect`: a click on our root selects it alone.

How it is loaded:
- Ours is sourced as a whole copy, `%TEMP%/skeldar_scenetabs/skeldarLayerEditor.mel`, because those
  procs call local procs of their file (a lone redefinition died on «Cannot find procedure
  "getBestLayers"»).
- The copy leaves out the file's last bare block, which builds the editor UI (sourced twice:
  «'DisplayLayerUITabLayout' is not unique»).
- `buildAnimLayerArray` is ours on top: no holders, and an empty list for an empty tab.
- Maya sources its own file again when it builds the Channel Box / Layer Editor. Before every refresh
  of ours, `layers._rebuild_editors` puts the copy back (`layereditor.ensure`).
- Tabs off: every proc is Maya's.

A Maya whose text differs keeps its own procs, said in the Script Editor. The scene's layers are never
touched. Proof: `verify_tab_layer_editor.py` **13/13 in a disposable GUI Maya** (real Qt clicks down the
tree; the base collapsed; Maya's own file sourced again), the labels read through the proc, pictures.

**The lag on selecting a control in tab mode** (2026-10-16, «чувствую задержку ... каждый раз когда
выделяю контроллер и перетаскиваю его»). Measured in a disposable GUI Maya: three Manny rig tabs, the hub
open (294 scriptJobs).
- The drag is not it: a drag step costs 16.2 ms with tabs and 16.2 ms in one scene. Hidden tabs cost
  nothing to draw or evaluate.
- The selection was it: **680 ms from select to idle**, the hub cards' SelectionChanged jobs:
  - Walk Builder's `scene.walkers()` ran 250 ms: an `attributeQuery` on every joint of every tab, twice;
  - Center of Mass `network.find_all` ran 180 ms: the same on every transform;
  - `maya_rigs.rigs()` ran ten times a selection, each a `listRelatives` on every joint;
  - `naming.find_skeleton_roots` did one `listRelatives` per joint.
- The fixes:
  - a marker lookup is `ls("*.attr", recursive=True, objectsOnly=True, type=...)`: `recursive` crosses
    namespaces, trap 70's pattern without it does not;
  - `skeleton_root_of` asks for the namespace's joints alone, shallowest first;
  - a skeleton root is a joint whose parent's path is no joint's, read off one listing.
- After: **125-210 ms**, the same as one scene (125-175).

**Each tab has its own persp / top / front / side** (2026-10-16, «камеры перспективы и других
направлений общие для всех вкладок»). The startup cameras are the scene's, one of each for every tab.
Measured first:
- an import leaves them as they are (the file's own persp never came in);
- a tab's `exportSelected` wrote none, so its file reopened with Maya's defaults;
- a new tab kept the last tab's camera; only the cameras a panel looked through were remembered.

Now a tab's record carries `cameras` (`records.CAMERA_ATTRS`: translate, rotate, focal length, centre of
interest, ortho width, clip planes, tumble pivot, film aperture, overscan, in the scene's units):
- `switching.leave` captures them and `enter` puts them back. A locked, keyed or driven channel is left
  alone (a keyed one is the tab's own curve since the same evening, below);
- `open_tab` reads its FILE's: `.ma` up to the first other node, `.mb` from its chunks (DBLE / DBL3
  after the node's CREA, internal cm and radians). The `.ma` is in its header's units, converted;
- `new_tab` takes Maya's defaults (`DEFAULT_CAMERAS`, measured);
- a save selects them too, so the file holds the tab's cameras;
- `restore` takes the session file's (the active tab's as saved, newer than its record);
- a reload keeps them;
- a model panel left on a hidden tab's camera goes to persp.

And a switch no longer flags the tab modified. Every switch's setAttrs and the session node's write
flagged the scene, so a tab visited came out «unsaved»; `start()`'s moves flagged tab 1 the same way.
`switching.settle_flag` sets the active record's flag after the last write (switch, a new tab), `start()`
the scene's own, and a failed switch puts the old flag back. Proof: `verify_scene_tabs.py cameras`
**19/19** (mayapy), all **0 of 220**, `verify_tabs_scope.py` 0 of 46, unit tests
`test_scenetabs_records.Cameras`. Not seen in a GUI Maya.

**…and its own keys on them** (the same evening, the animator: «если я накину анимации на камеру которая в
сцене по умолчанию то она будет во всех сценах. Мы можем сделать так что бы в каждой вкладке были свои
камеры по умолчанию?»). Measured first (mayapy): a key on persp made while a tab is active is a curve in the
tab's namespace (`tab_x:persp_translateX`; the current namespace is the tab's); an import of a file with an
animated persp brings its curves into the tab's namespace and CONNECTS them to the scene's persp (`connectAttr
"persp_translateX.o" ":persp.tx"`); a disconnected curve lives on and reconnects cleanly. So a tab's keys on
the startup cameras are its own curves, on the camera only while the tab is active:
- `switching.camera_curves(ns)`: the time curves of the tab's namespace (nested too) driving any channel of
  persp / top / front / side and their shapes;
- `leave` records them in `camera_curves` ({"persp.translateX": UUID}) and disconnects them
  (`detach_cameras`); `enter` connects them back (`attach_cameras`) before `apply_cameras`, which skips the
  keyed channels. A channel something else drives meanwhile is left alone;
- the record keeps `camera_curves` through the session node (`records.loads` keeps only the keys it lists:
  until then the list was read back empty and a tab's keys stayed off);
- a reload of a HIDDEN tab takes the active tab's curves off for the length of the import (the file's would
  otherwise fail to connect) and keeps the file's as the hidden tab's;
- a save writes the tab's keys with persp (it is the active one then), nothing of another tab's; a hidden tab
  closed takes its curves with it; a saved session brings them back by UUID.
Not handled: an animation layer or a constraint on a startup camera (one for every tab, as before), and a
key made with the ROOT namespace current (a script's): its curve is no tab's and stays on the camera in
every tab.
Proof: `verify_scene_tabs.py camera_keys` **15/15** (mayapy: three files keyed differently, switching both
ways, a key made in a tab, Ctrl+Z past a switch, a save, a hidden reload, a session restored, a hidden tab
closed), all **0 of 284**, `verify_tabs_scope.py` 0 of 46; 6858 unit tests. Not seen in a GUI Maya.

**A tab's save wrote another whole tab into its file** (2026-10-16, the animator: «No object matches name:
tab_AS_DG_ATK_JA_01_ma_skeldartmp_ma_skeldartmp:AnimLayerRoot.solo … Не могу открыть сцену»). The file
was `Knife/AS_DG_ATK_JA_04.ma`, saved at 12:48. Read off it, it holds 3316 nodes of a tab that was
hidden then: a Manny rig with `.lodv` off, its layers carrying their stored links (`skeldarTabOut`),
and the session's `skeldarTabsLayerRoot`. Two separate failures:
- **The save.** `exportSelected` writes a node's whole upstream (trap 263). The tab was tied to the
  hidden one by a MaterialX blinn fed by that tab's `materialXStackShape1`, and to the session root by
  a layer hanging on it, and the export followed both.
  - `saving.foreign_inputs` walks upstream from the tab's nodes through every node the export would
    write (not Maya's defaults, shared nodes or a reference's) and cuts every input from another tab
    or from the session's root layer and node. The edges are kept as handles and full attribute
    names, and put back after the export (`_cut` / `_join`).
  - `layers.adopt_strays` moves a tab layer hanging on the session root under the tab's own root.
- **The open.** `show_layers` re-attached the stored links of the session that WROTE the file, naming
  nodes that are not here. Every open of such a file now runs `opening._tidy_file`, in `_import` and
  in `start()` (a scene opened plainly, then the first tab):
  - `leaked_tabs` finds a child `tab_*` namespace holding our hide state (stored links, a set we hid);
    a rig pasted from another tab carries none. The animator is asked **Remove / Keep**, and the line
    says which;
  - `layers.forget_stored` drops every stored link the file brought; its display layers go back on
    the Layer Editor;
  - `layers.tidy_imported` puts layers hanging on the session root under the tab's root and dissolves
    a copy of the session root (`is_root_copy`);
  - `take_root` renames a copy named like the session root out of the way first: the real root came
    out `skeldarTabsLayerRoot1`, and the copy was taken for it by name;
  - `attach` skips a link whose node is gone.

Proof: `verify_scene_tabs.py leak` **20/20** (mayapy):
- tab B tied to hidden A through a root node and to C directly, with a layer on the session root, saves
  clean: nothing of A or C or of the session, the layer under B's root, every connection back;
- with the walk switched off, the same save writes A, C and the session root in (the control);
- that file opens in a tab with Remove (asked, nothing left over) and with Keep (A and C inside, their
  layers under the tab's root), away and back;
- opened plainly, then a new tab: the real root named right, the copy gone.

The animator's own JA_04 (a copy in mayapy): opened plainly, then a new tab, Remove takes the 3316 nodes
out (10765 → 7449); its next save (5.2 s, 0.6 s of it the walk over 7403 nodes) holds no session root and
no stored link. `verify_scene_tabs.py all` **0 of 240**, `verify_tabs_scope.py` 0 of 46; unit tests
`tests/test_scenetabs_leak.py`. Not seen in a GUI Maya.

262. **`namespace -removeNamespace -deleteNamespaceContent` over a DETACHED animation layer tree (a root
     with no parent - a hidden tab's) corrupted Maya's heap**: the command returned, and the next `file`
     operation (or the interpreter's exit) died with 0xc0000374. `cmds.delete` of the same layers, one at
     a time, was fine, and so was the namespace delete after the root was parented again. Delete layers
     node by node (`opening._remove_namespace`, the path a closed tab takes).
263. **`file -exportSelected` writes every selected node's upstream, whatever its namespace.** One input from
     another tab (or through a root-namespace node between them) writes that whole tab. A parent link to
     the session's root layer writes the root, and through its children every tab still attached to it.
     A tab's export must cut what leads outside first; `-exportSelectedStrict` would also drop the tab's
     own nodes Maya made in the root namespace.

**…a Remove leaves the tab flagged** (the same afternoon, the animator in a fresh Maya met the question on
JA_04 again): the tab opened clean, nothing asked for a save, and the leak stayed in the file. A tab whose
tidying removed something is in `opening.CHANGED` and opens flagged (`open_tab`, `reload_tab`, tab 1 in
`start()`); the line ends «save this tab to clean the file». Keep leaves it unflagged.

**The plugin's opens: the first scene in place, every later one in a tab** (2026-10-16, the animator:
«открываю какую-то сцену, потом открываю сташ и открываю сцену из сташа ... в уже существующей
переоткрывается сцена, но если нажать + empty tab то тогда следующие открытие из сташа будет открывать
новую вкладку ... первая сцена открывается в первой вкладке если та пустая, дальше сцены в любом случае
будут открываться в новых вкладках»). Stash, Shared and Open scene opened a tab only while tabs were on;
with one scene open they replaced it. `scope.scene_empty`: tabs off, untitled (a session file name an
untitled scene kept counts), and unmodified or holding no node and no reference of its own
(`session.own_nodes("")`, `top_references("")`; unreadable = holds something). Only then does
`scope.open_scene` / `new_scene` open in place; else `opening.open_tab` / `new_tab` (the open scene
becomes tab 1, its unsaved changes kept and flagged, nothing asked). `opener.open_path` (Stash, Open
scene) and `maya_share.open_entry` go by it; Stash's line says «in a tab». Proof: `verify_scene_tabs.py
stash_open` 12/12 (mayapy), all **0 of 255**, `verify_tabs_scope.py` 0 of 46; `test_scenetabs_scope.SceneEmpty`
/ `OpenNew`, Stash and Shared's tab tests; 6840 unit tests. Not seen in a GUI Maya.

**…and Maya's own File > Open too** (the same day, asked: «Сделай так, чтобы и Maya File > Open открывал
новую вкладку, если сцена уже открыта и не пустая»). One rule for every road, `scope.opens_in_tab(path)`:
tabs on - a tab; tabs off - a tab unless the scene is empty or `path` IS the scene (opening it again reverts it,
as Maya does: a second tab of one file would save over the first). `hooks.on_open` with tabs off redirects
when `hooks.redirects(path)`: a .ma / .mb, `opens_in_tab`, and no saved session (that brings its tabs back as
before); an FBX, New, an empty scene stay Maya's. The plugin's own plain opens run inside `scope.decided()` (the
check's bypass): a Save As between its decision and its open must not turn it into a tab. Maya's File > Open
and Open Recent ask «save changes?» BEFORE `file -o` (trap 264), so `maya_scenetabs/savechanges.py` sources a
copy of Maya's `saveChanges.mel` with its proc renamed `skeldarMayaSaveChanges` and defines `saveChanges`
over it: an action that opens a scene the check takes into a tab (`savechanges.opened_path`,
`hooks.goes_to_tab`) runs at once; anything else, an error, or the checks off is Maya's copy word for word
(`hooks.install`, GUI only; a Maya whose file it does not know keeps its own). Tabs on gained the same: no
question before a tab opens. **A script's `cmds.file(path, open=True)` beside a non-empty scene now opens a
tab too** (it raises «File operation cancelled by user supplied callback» and the tab opens one idle later) -
as it already did with tabs on. Proof: `verify_scene_tabs.py maya_open` 14/14 (Maya's saveChanges + file -o
through the real checks in mayapy: into an empty scene in place, B beside a modified A in a tab with A's
change kept, the same file reopened, a session, an FBX, New, the checks off), all **0 of 269**,
`verify_tabs_scope.py` 0 of 46; `tests/test_scenetabs_savechanges.py`; 6857 unit tests. Not seen in a GUI
Maya (the dialog itself never shows in mayapy).

264. **Maya asks «save changes?» before `file -open` runs, not inside it.** File > Open and Open Recent go
     through `pv_performAction` / `performFileAction`, which build `file -f ... -o "<path>"` and hand it to
     `saveChanges(action)`: the dialog, then `evalEcho(action)`. A `kBeforeOpenCheck` that redirects the open
     fires only after the animator has answered a question about a scene that is not going anywhere. Steer
     the question in `saveChanges` itself.

## Tools > 1P Setup: a 3P take split by layers for first person (2026-10-16)

The animator: «мы нажимаем кнопку и у нас все распределяется по слоям. Включив слой нижней анимации
мы получим нашу анимацию нижней части и стабилизированый верх, но ... старая анимация для третего
лица на верхней части ... в слое хранится на всякий случай». Asked: Spine1-2 with the lower body;
the camera in the knot with no animation; a rig with no 1P switch done without it, said; a second
press refused. Spec `docs/superpowers/specs/2026-10-16-tools-1p-setup-design.md`.
`SkeldarAnim/maya_tools/firstperson.py`; a fourth Tools subsection **1P** with the row **1P Setup**;
hotkey row `tools.fp_setup`. One press on any part of a rig, one undo chunk:
- `Main.view` = 1 (Manny, Orc D; else «no 1P mesh on this rig»);
- Tools > Knot on `FKSpine3_M` over the whole take;
- Tools > Layer (`layerbake.bake(..., name=)`) over the whole take: the lower controls (`Main`,
  `RootX_M`, `FKRoot_M`, `HipSwinger_M`, `FKSpine1/2_M`, leg words, IK spine) and the knot onto
  **`_3P_Lower_Body`**, every other animated control onto **`_3P_Upper_Body`** (Maya will not start
  a node name with a digit: `3P_...` becomes `P_...`); the base keeps the first frame's pose; then
  the knot's rotate curves moved from Lower to Upper (`move_curve`: the same curve node, exact -
  both add by component). Both marked `skeldarFirstPerson` = the rig's namespace;
- Camera Setup on `camera_root`, then the camera's keys cut and it parented under the knot where
  it stood at the take's first frame (none on the Creep: no camera_root, said).
Refused before anything changes: no rig, layers of ours for it, no `FKSpine3_M`, the spine in IK,
anything Layer or Knot would refuse. Proof: `verify_1p_setup.py` **13/13** on Manny and Orc D,
**12/12** on the Creep (a UE 3P clip retargeted): one undo / redo; both layers on the take to
0.0000 cm / deg; both muted the first frame's pose; Lower alone the pelvis and legs as before and
spine_03's world turn the first frame's (the take turns it 102.5 deg); the knot's turn on Upper
only; the camera under the knot, unkeyed, camera_root following it; a second press refused. 6701
unit tests. Not seen live (the animator's checks). Custom attributes (IK foot roll, swivel) stay on
the base: Layer bakes translate / rotate / scale.

## Ragdoll: a fall out of the take, simulated and baked (2026-10-16)

The animator: «ТЫ можешь настроить регдол для наших ригов? что бы персонажи падали по физике». Asked:
a death or knockdown out of an animation, keeping the clip's momentum; baked into the rig's controls;
**no ragdoll in the rigs** («наши риги не должны начать есть больше ресурсов») - a temporary one built
per press, simulated, baked and deleted; muscles that hold the first frame's pose and FADE; the floor
plus meshes selected with the rig as colliders; a «Drop weapon» check (on); a new override layer
`Ragdoll_<frame>` by default or the base layer; the span the highlight, else the current frame plus
Length. Spec `docs/superpowers/specs/2026-10-16-ragdoll-fall-design.md`.

Package `SkeldarAnim/maya_ragdoll/` (payload row): `plan.py` (numpy, pure, a test pins no Maya), `sim.py`
(Bullet), `weapon.py`, `fall.py` (the press), `panel.py` (the card). Hub section **Ragdoll** (Animation,
after Camera Shake, Tabler `skull`); hotkey rows `window.ragdoll`, `ragdoll.fall`.
- **The body**: 16 capsules (`plan.BODIES`: pelvis, two spine pieces, head, upper / lower arms, hands,
  thighs, calves, feet) on the GAME skeleton, mass by de Leva's shares of Mass (75 kg); a capsule runs
  from its first bone to the next body's, its radius the MEDIAN distance of the skinned vertices whose
  heaviest influence rides it. Every other bone rides its nearest body rigidly (`riders`, `offsets`).
  The floor is the lowest skinned sole point of the feet. Velocities at the start from frames a-1 and
  a (cm/s, deg/s, world axes).
- **The joints**: SixDOF2 (type 5) springs, linear locked, angular limits per joint (`BALL`, hinges for
  knees and elbows read off the bend's own plane, straight: knee back, elbow forward); the spring holds
  the first frame's pose at `MUSCLE_GAIN` 8 x m g L x Strength and is keyed to 0 over Muscle fade frames.
- **The run**: our own solver (gravity -980, 240 Hz, 40 iterations, splitImpulse), a group
  `skeldarRagdoll` deleted by UUID diff in a `finally`; stepped with `cmds.currentTime` one frame at a
  time, unrecorded; the bodies' worlds become a Pose Library animation card in memory (the game bones, a
  rig's drives) and are pasted with `animapply` (Replace, every frame, not in place - Main holds its
  frame-a place). New layer: an override layer, weight 0 at a-1 and 1 at a (stepped), the take kept
  under it; base: the keys after b cut. Drop weapon: the held weapon a box body, then on the floor road
  (`bonedrive.park`, its bone following it), the hand track kept before the fall. One undo.
- Refused: no rig / two rigs, a standing MoCap holder, a missing body bone.

Proof: `docs/superpowers/plans/verify_ragdoll.py <clip> <rig key>` **26/26 mayapy standalone** on
Manny_Rig, Creep_Rig and Orc_D_Rig (a UE sprint retargeted): the take before untouched 0.000000, bone
lengths kept, the start velocity, nothing under the floor, lying and at rest at the end, no knee bent
backward, the rig on the simulation within 3 cm (Orc D's hand_l 2.19 - the joints' slack), one undo /
redo, no Bullet node left, the sword in the hand then on the floor, a box stopping the body (pelvis z
205 against 349 free), a second press replacing its layer, the card's press with the card closed;
`tests/test_ragdoll_plan.py` 18; 6876 unit tests. **Not seen live** (the animator's checks).

**…and impulses: an arrow on a body part, a hit at its own frame** (the same day: «реализовать возможность
задать импульс в определенную часть тела по определенному вектору»; asked, all the recommendation: an
arrow in the scene, its own Frame, its strength a speed in m/s). Spec
`docs/superpowers/specs/2026-10-16-ragdoll-impulse-design.md`. `maya_ragdoll/impulse.py`; the card's
**+ Impulse** (secondary, beside Fall), hotkey row `ragdoll.impulse`.
- **+ Impulse**: the body whose capsule axis passes nearest the first selected node's pivot
  (`plan.nearest_body`, read on the game skeleton now); an arrow `<ns>:impulse1` with its tip on that body's
  centre pointing along the active view (`view_direction`, persp without one), in a space following the
  body's first bone (`weaponspace.ensure_marked_space`, `skeldarRagdollImpulseSpace`, group
  `RagdollImpulses` under the rig's group - Delete character takes it). Marked `skeldarRagdollImpulse` =
  the body; Channel Box `frame`, `speed` (m/s, default 5), `enabled`; the head drawn on the arrow, the
  shaft on a child stretched `speed` x 6 cm. One undo.
- **In Fall** (`impulse.hits`, read at the fall's first frame in each body's frame, `plan.in_body`): a
  frame at or before the fall hits on its first step, after it none (named); before the step into the
  frame `sim.Scene.impulse` sets J = body mass x speed x 100 along the arrow at the tip less the body's
  centre (`plan.impulse`), the step runs, `clear_impulses`. The line: «| 1 impulse: head 6 m/s at 9».
- **The hit part does not reach the whole Speed**: the joints share the knock with the body - a 6 m/s
  hit on the head gave the head 3.8-4.0 m/s on the hit step on all three rigs. Speed is the part's
  speed as if it were loose.

Proof: `verify_ragdoll.py` **36/36** on Manny_Rig, Creep_Rig and Orc_D_Rig (phase 6: + Impulse on
FKHead_M names the head, one undo / redo, under the rig's group; a disabled arrow changes nothing,
0.0; the hit along +X 376 / 400 / 375 cm/s on the head; off the head's axis 6.7-8.5 deg from the hit
through its centre; a hit at a+10 changes nothing before it, 0.0, and moves the head 38.7 cm after; an
arrow after the fall named; Fall's line); 6925 unit tests. Three verifies run at once once read the
Creep's last frames 3.21 cm apart where alone it reads 0.28 twice: Bullet under a loaded machine is not
bit-for-bit repeatable. Not seen in a GUI Maya (port 7002 closed).

265. **Maya Bullet, measured** (2026-10-16): gravity is in METRES (-9.8 drops a cm scene in slow motion:
     -980); `initialVelocity` cm/s and `initialAngularVelocity` deg/s, world axes; the solver
     initialises only on a time change AT its startTime (build, then `currentTime(a)`), steps only on
     `cmds.currentTime` one frame at a time (not `MAnimControl`, and a skipped frame breaks it);
     `CreateRigidBody` wires the scene's FIRST solver; `autoFit` defaults True and overrides the radius;
     a capsule's `length` runs tip to tip; collision filters default group 1 / mask 1, so a ragdoll in
     group 2 falls through a default floor (floor mask 1|2); angular limits are DEGREES in the
     constraint transform's frame; only SixDOF2 (5) takes springs, type 4 ignores them silently.
266. **Bullet does not step in a GUI Maya while the viewport is suspended** (`refresh -suspend`, which every
     `timewalk.Walk` turns on). The first Ragdoll push keyed 61 frames of one still pose in the animator's
     Maya («ключи запекаются но ничего не происходит»): a test capsule fell 31 cm with the refresh on and
     0 with it suspended, in DG and parallel alike. mayapy has no viewport, so every verify fell. The
     simulation steps run with the refresh on (`fall.simulate`), suspended again after.

**…a human's joints and a body that does not pass through itself** (the same evening: «найти в интернете
параметры настройки гуманоида и перенести их к нам ... что бы части тела не протыкали друг друга»). Done
alone. **This replaces the `BALL` limits above** (about the pose at the fall) and «the capsules: group 2,
mask 1 - not each other».
- **Human ranges about the anatomical NEUTRAL** (`plan.ANATOMY`: standing, arms hanging, feet forward;
  AAOS norms - shoulder flex 170 / ext 60 / abd 150 / add 40 / twist 80, hip 120 / 30 / 45 / 30 / 45, wrist
  80 / 70 / 25 / 80, ankle plantar 50 / dorsi 20, neck 45 / 45 / 40 / 60, the thoracolumbar 80 / 25 / 35 /
  45 split over the two spine joints; hinges `HINGE_RANGE` elbow 145 + 5, knee 135 + 2). Each ball joint's
  neutral frame is read on the REST facing (`anatomical_frame`: X the neutral direction, Z the flexion axis,
  Y = Z x X, a positive Y turn takes a limb to the body's left - mirrored for the right side); the child's
  own neutral is that frame turned the least onto its bind direction; the difference now is the offset.
  A rig's unrolled limb bones are read in their drive (trap 246).
- **Bullet's frame is the CHILD's** (`anatomical_joint`): a Bullet turn `m` is the anatomical `offset . m`,
  so Bullet's X stays the limb's own twist (in the parent's frame a twist turned a hand already bent 20
  degrees into a swing 30 past its range). Each axis's limit is how far a turn about it alone keeps the
  joint inside its **swing-twist cone** (`cone_excess`: the swing as a rotation vector against the ellipse
  of its abduction and flexion ranges - PhysX's and Unreal's measure, no gimbal - the twist against its
  range); a pose already past it is kept from going further, never snapped back; the middle axis inside
  +-85; then the box's corners are brought inside the cone, the sideways half-side giving way first
  (`_inside_cone`). Only the swing: Bullet's two swings carry a twist of their own, and shrinking for it
  left a hip 60 of its 120 degrees.
- **Self-collision** (`collision_filters`): 12 groups (a limb's first body alone, the rest of the limb
  together; Maya's Bullet keeps 16 bits), each body colliding with every group but its own, its jointed
  neighbours' and those it already touches at the fall (`OVERLAP_SHARE` 0: touching capsules are pushed
  apart on the first step - a hand on a thigh threw the Creep's pelvis 1.6 cm). The weapon its own bit,
  the world only. `penetration` puts a capsule's cap centres half a radius INSIDE its segment.
- Damping 0.05 / 0.6 (Bullet's ragdoll demo: 0.05 / 0.85), the joints' 0.5 (Maya's Ragdoll.py).
- Sources read: Bullet's `BenchmarkDemo.cpp` RagDoll, Unity's CharacterJoint, community UE physics-asset
  values, AAOS range-of-motion tables (they disagree by 10-20 degrees; ours sit a little inside the active
  range - a ragdoll's joints are passive).

Proof: `verify_ragdoll.py` (three new gates: self-penetration, swing past the human range, twist past it;
the knee gate now signs the bend in the knee's own hinge, `RAGDOLL_PLUGIN` runs another build as the
control): **39/39 on Manny_Rig, Creep_Rig and Orc_D_Rig** on a UE sprint; on a sprint attack the same
three pass (penetration <= 0.4 cm, swing <= 12 deg past) but the Orc's wrist twist once read 42.8 - the
clip-specific gates (floor, bake, the box's place, at rest) fail there for the old build as well. The old
build on the same gates: **penetration 13-21 cm, 60-77 degrees past the human range**. 39 unit tests in
`test_ragdoll_plan` (6983 in all). Not seen in a GUI Maya.

270. **Maya's Bullet, more measured** (2026-10-16): the SixDOF2 constraint composes its angles **Rz . Ry .
     Rx** (a joint locked at (30, 20, 10) settled on that product to 0.0000, XYZ was 0.18 off) - read with
     XYZ, the middle limit was held on the wrong angle and a wrist drifted 40 past it; positive = a
     right-handed turn of body B about the axis (B = `rigidBodyB`). `collisionFilterGroup/Mask` are 16
     bits (a group of 1<<17 fell through the floor). On type 5, `angularLimitSoftness/Bias/Relaxation`,
     `angularSoftness` and `maxNumIterations` change nothing (bit-for-bit); `internalFixedFrameRate` is
     an enum 60 / 120 / 240. Its limits hold to ~5 degrees under a 1500 deg/s spin.

**…and Blend: the take and the ragdoll mixed** (2026-10-17, «Возможно ли сделать режим в котором будет
смешиваться наша анимация и работа регдола?»; asked: all three kinds - the body following the take, part
take part physics, a blend in time - six zones in the card with presets, the span plus Blend in / out).
Spec `docs/superpowers/specs/2026-10-17-ragdoll-blend-design.md` (read its addendum). `maya_ragdoll/blend.py`;
the card is `[Fall | Blend]` now, hotkey row `ragdoll.blend` (`panel.press_blend`, `press_main`).
- **The card in Blend**: Length / Mass / Friction / Bounce (both modes), presets **Hit reaction** (legs
  Anim, the rest Follow 0.5), **Arm overlap** (arms Follow 0.3, the rest Anim), **All follow** (0.6); six
  rows Torso / Head / Arm L / Arm R / Leg L / Leg R `[Anim | Follow | Free]` + a strength 0..1; Blend in /
  Blend out, fr; the layer; + Impulse; **Blend**. Fall's muscles and Drop weapon show in Fall only.
  Settings in `skeldarRagdoll_settings` (`mode`, `zones`, `blend_in`, `blend_out` added).
- **The run**: the take read on every frame a-1..b; Fall's 16 capsules, all dynamic; each frame each
  body KICKED toward the take's next frame (`plan.servo`: an impulse and a torque impulse, Strength the
  share of the way, gravity paid for; Anim 1, Free 0, every zone easing from 1 over Blend in and back over
  Blend out); half the last frame's landing error leaned against (`plan.aimed`); a limb rolls with its
  bend plane (`plan.blend_bodies`); the joints' human range grown to the take's own angles and their
  linear axes to the take's own reach (`plan.widened`, `plan.joint_travel`); bodies the take brings
  together left apart; the pelvis plays the take whenever a leg does (`plan.body_states`); impulses hit
  as in Fall (an Anim body's hit is dropped, said).
- **The bake**: each bone the take turned by its body's SWING only (`plan.swung`, the take's roll kept),
  laid down the skeleton by the take's offsets (its lengths); an Anim zone's bones and drives the take's
  exactly. A new layer `RagdollBlend_<a>` (override, 0 before, 1 over the span, easing to 0 over Blend
  out), else the base layer with nothing after the span cut. Weapons are not dropped.
- Proof: `verify_ragdoll_blend.py` **14/14 standalone on Manny_Rig, Creep_Rig and Orc_D_Rig**:
  - All follow at 1: every game bone within 2.75 / 3.17 / 2.74 cm of the take; lengths kept;
  - the take outside the span 0.000000; one undo / redo; no Bullet node left;
  - Hit reaction with a 4 m/s head arrow: the leg bones 0.0000-0.0024 cm; the head the same as without
    the hit before it (0.000), knocked 5.7-6.3 cm, back on the take by the end;
  - a sprint attack on Manny the same (its Anim leg bodies 3.98 cm, their bones exact).
  57 plan tests; 7085 unit tests. **Not seen in a GUI Maya** (the card, a real press).
- **…Follow is a spring with weight** (the same day: «персонаж остается на своем месте и что-то там
  дергается ... Я вообще не вижу работы регдола»; spec addendum 2). The share-of-the-way kick lagged a
  fast take and snapped back (the error flipping sign frame to frame, its jump 17.6 cm) and read as no
  physics. Now a Follow body's error from the take is carried on by a damped spring solved exactly
  (`plan.follow`, `spring_step`, `follow_spring`: 0.5..6 Hz log-spaced by strength, damping 0.4, the
  muscles holding strength² of gravity), and the kick lands it at the take plus that error; Anim (1)
  keeps the servo and its drift lean, Free (0) nothing. A press with no impulse and no Free zone says
  Follow only adds weight and lag. Measured: the jump 3-4 cm; on a 60-frame emote Follow 0.5 lags and
  sags the hand 6-11 cm, Free arms hang 50-64 cm off; the verify 14/14 on all three rigs, a 4 m/s head
  hit knocking the head 13-16 cm (6 before). 63 plan tests. Not seen in a GUI Maya.

273. **A powered ragdoll follows a take's roll at its peril.** A UE upper arm spins about its own axis up
     to 80 deg a frame in a sword attack; a capsule servoed to that spin precesses (Bullet's gyroscopic
     term, an anisotropic inertia) and swung 28 deg off its axis, 15 cm at the hand, while every body's
     POSITION tracked to 0.5 cm. Servo the roll a joint needs (a limb's bend plane; the chest's, which
     carries the shoulders), never the bone's. And a joint's linear lock fights a take whose clavicle
     shrugs the shoulder 10 cm across the chest - give each joint the take's own reach.
274. **`cmds.currentTime` in a verify between a press and its undo undoes the time, not the press**
     (trap 222 again): a "run without the hit" undone after tracking it stayed in the scene, and the run
     with the hit read the first run's layer as its take - 5 cm apart before the hit, with a
     deterministic Bullet. Undo straight after the press, and compare runs through their cards.

**…and Cached Playback switched off while it simulates** (2026-10-17, the animator: «после того как мы
сделали бленд у нас вообще весь регдолл сломался теперь и фол не работает хотя до этого фол работал
отлично»; asked, «Персонаж стоит»: the layer is made, the character stands). Spec addendum in
`2026-10-16-ragdoll-fall-design.md`.
- **Not the Blend code**: every headless verify still fell, and the build before Blend gave the same
  numbers as HEAD.
- **Reproduced in a disposable GUI Maya**: with Cached Playback on, Bullet does not step at all (trap 275).
  A Fall left the pelvis at 86.5 cm at the end (the take's 83.3); with the cache off the same press
  fell to 23.5.
- **The fix**: `sim.Scene` switches the cache off before it makes its first node, when it was on, and back
  on once `delete` has taken the nodes (`cache_on`, `_cache`; a build that fails puts it back).
- **Measured in the GUI Maya with the cache on**:
  - Fall falls: the pelvis at 23.7 at the end, the cache on again after, no Bullet node left;
  - Blend with Free arms hangs them 71-77 cm off the take. The build before held them 2-5 cm off
    mid-span: frozen in the first frame's direction, the morning's «стоит и что-то там дергается».
- **Tests**: `tests/test_ragdoll_sim.py`, 5 tests (two fail on the build before); 7121 unit tests;
  `verify_ragdoll.py` 39/39 and `verify_ragdoll_blend.py` 14/14 on Manny_Rig, Creep_Rig and Orc_D_Rig.
- **Seen live**: the animator updated through Check update and pressed Fall and Blend in their own Maya;
  both work (2026-10-17).

275. **Bullet does not step in a GUI Maya with Cached Playback on**, whatever the refresh. Measured
     2026-10-17: a capsule fell 0.0 cm over 10 frames with the cache on (refresh on or suspended), and
     85.3 cm with it off and the refresh on. A fresh Maya 2027 has the cache on, and the Time Bar has a
     chip for it. mayapy has no cache evaluator, so no headless verify can see it. Switch the cache off
     before the solver is built (`evaluator -name cache -enable 0`, which flushes it) and back on once
     its nodes are gone.

## Time Bar: Maya's time slider redrawn in the hub's look (2026-10-16)

The animator: «Давай попробуем перерисовать интерфейс таймслайдера маи под наш стиль. Сделай пару макетов а я
выберу».
- The first mockups (https://claude.ai/artifact/JS83VQsVewRHtnmjWBnwWZ) went to **A, one bar**, in place of
  Maya's; it shipped as `79bca77`. The playhead jumped frames (fixed in `3a2aaa3`, trap 269).
- Then: «Ты не заменил интерфейс таймлайна а смастерил какую-то полку». Maya draws its own slider, so its shape
  cannot be restyled. Asked, they chose **our panel made into a full time slider**, with every element of
  Maya's two rows («все эллементы на скриншоте желательно перенести к нам»).
- Also asked for: the radial menu's motion (a lift and a glow under the mouse, a scale) and keys that light up
  as the playhead reaches them and fade back.
- Mockup: https://claude.ai/artifact/4wDFBEEQgnjBvLv85ciwSt. Spec:
  `docs/superpowers/specs/2026-10-16-time-bar-design.md` (its first version, one bar).

**Package `SkeldarAnim/maya_timebar/`** (a payload row):
- `look.py` (stdlib, a test pins it):
  - `Track` frame <-> x, `ticks`, `dragged`, `highlight` / `range_array`, `neighbour_key`;
  - `zoomed`, `highlight_hit`, `key_drag`, `mapped`, `passed`, `flash`, `approach`, `back_out`, `opening`,
    `envelope`;
  - `FPS`, `SPEEDS`, `LOOPS`, `TANGENTS`.
- `scene.py` (cmds): every read and write the strip sends.
- `bar.py` (Qt): `Strip`, `Timeline`, `RangeBlock`, `Pill`. It talks to Maya only through a `Link` (a fake in the
  tests).
- `__init__.py`: the workspaceControl `skeldarTimeBar` (84 logical px, `actLikeMayaUIElement`: no tab, no
  title), plus `show` / `hide` / `toggle` / `active()` / `highlight()`.

**Range row**:
- The fields: animation start, playback start, playback end, animation end.
- The range block: drag the body to slide the playback range, its orange edges to resize it.
- Bookmarks: previous, add over the highlight, next. They are Maya's own `timeSliderBookmark` nodes, made
  directly: the plugin's `createBookmark` reads Maya's slider and jumps time to the end.
- Chips: character set (Maya's `highlightList`, as `currentCharacters.mel` reads it), the layer keys go to, fps.
- Toggles: loop (continuous, once, oscillate in turn), cached playback (`evaluator -name cache`), speed (a chip:
  real-time, every frame, half, twice), sound, Auto key, preferences (`preferencesWnd "timeslider"`).

**Time row**:
- The timeline shows the playback range; the wheel zooms about the mouse; Frame the playback range (key menu)
  or a double click puts it back.
- Bookmarks are a band along the top, their names inside. The sound is a waveform: `.wav` read with stdlib
  `wave`, a ~2 kHz mono copy cached per file.
- Keys are orange and breakdowns cyan; the playhead carries its frame on a flag.
- **Shift-click or shift-drag highlights** (one frame too). Drag the blue block to move its keys, an edge to
  scale them toward the other edge: one `keyframe -relative` or `scaleKey` + `snapKey`, one undo chunk, applied on
  the release (a preview while dragging).
- The right button opens the key menu: Set key, Breakdown, Cut / Copy / Paste / Delete, Tangents ▸, Snap,
  Add bookmark, Playback range = highlight, Frame the playback range, Back to Maya's time slider.
- A middle drag scrubs without updating the scene (`currentTime -update false`).
- On the right: the frame field, then eight transport buttons (start, back a frame, back a key, play
  backwards, play, forward a key, forward a frame, end).

**Motion**:
- The radial menu's: controls open from small with a bounce (`opening`, 18 ms apart), lift +10 % and glow under
  the mouse (`HOVER_MS` 110), flash on a press, pop on a toggle.
- The key under the mouse grows 60 %. A key the playhead reaches (playing, scrubbing, stepping) lights up and
  fades back over `KEY_FADE_MS` 600. Only the keys it swept over or landed on light: leaving a key lights
  nothing, a loop's jump lights only where it lands.
- One 16 ms timer, running only while something moves.
- ⋮ -> Interface animations off makes it all instant.

**The highlight** is written to `playbackOptions -selectionStartTime / -selectionEndTime /
-selectionVisible`. `overrig.slider_selection()` and Camera Shake read the Time Bar's while it is active (a
one-frame highlight is none to them).
- **Not known**: whether Maya's own commands and OverRig's MEL, which read `timeControl -q -rangeArray` on the
  hidden slider, see it.

**Kept current**:
- scriptJobs parented to the control: `timeChanged` repaints the playhead at once (`repaint()`, not
  `update()`), plus `playbackRangeChanged`, `SelectionChanged`, `animLayerRefresh`, `Undo`, `Redo`.
- `MAnimMessage.addAnimKeyframeEditedCallback` marks keys dirty; a 250 ms timer reads the rest.
- Keys are not read during playback. The jobs find the strip through `sys._skeldar_timebar`.

**In place of Maya's**: docked against `TimeSlider`, then `TimeSlider` and `RangeSlider` hidden. Hotkey row
`window.timebar` switches ours and Maya's.

**Three modes** (the same evening: «всплывающим когда наводим в область нижней части экрана»; asked: a third
mode, the edge of Maya's window). ⋮ -> **Time bar ▸ Maya's / Docked / Bottom edge**:
- optionVar `skeldarTimeBarMode`; an older `skeldarTimeBar` 1/0 reads as Docked / Maya's (`look.mode_from`).
- `maya_timebar.ensure()` is called by the hub's build; `set_mode`.
- **Bottom edge** (`maya_timebar/edge.py`, `BottomEdge`): two frameless Qt.Tool windows owned by Maya's main
  window:
  - a host along the bottom of its client area (`look.bottom_band`), holding the strip;
  - a 2 px sensor at window opacity 1/255.
- It reuses `maya_edgerules`:
  - the dwell, `may_reveal`, `hide_blockers`, the hide delay;
  - plus a drag in the strip as a blocker.
- It slides by moving the strip inside the host under a mask (`look.slide`, 180 ms out, 140 back).
- It follows Maya's window on a 300 ms poll.
- The strip shows a 📌 (`Strip.set_edge`) there only.
- In this mode the docked control is hidden and its uiScript builds nothing (`bar.build`).
- The jobs (`bar.start_jobs`) belong to no control: the old ones are killed and made again for whichever host
  stands.
- Tests: `tests/test_timebar_edge.py`. **Not seen in a GUI Maya.**
- **The zone** (after using it: «очень не удобно... выезжать когда мышка не на самом краю а в области где
  стандартный таймлайн»): the cursor resting `ZONE_DWELL_MS` (150) anywhere in the band where Maya's slider stood
  (`look.bottom_band`) brings it out.
  - It is watched by a 50 ms cursor poll (`BottomEdge.zone_tick`), not a window: a window over the band would
    take the viewport's and the command line's clicks.
  - Never with a button held (a marquee near the viewport's bottom), with Maya not active, or with a floating
    window or a menu over the band (`over_maya`: `QApplication.widgetAt` must be Maya's main window or ours).
  - The 2 px edge sensor still works too.
- **The burst from the cursor** (mockup https://claude.ai/artifact/YKqW7DScHBYWFt64nWBArX, A, «скорость на 50 %
  медленнее»; «и ключи на таймлайне пусть тоже проанимированы будут»). Every timing is the mockup's ×1.5, then 20 % faster («давай ускорим анимацию на 20%»): ×1.2
  (`look.BURST_SLOW`).
  - Coming out: the host's mask unrolls sideways from the cursor's x (`look.unroll`, ease-out quint, 288 ms, its
    corners rounding while narrow, `BottomEdge._mask_span`).
  - Meanwhile every painted control and every key pops from 0.3 with the radial menu's back ease, the nearest
    first (`Strip.burst_at` / `entrance_of`, `look.burst_delay`: 48 ms + 22 ms per 60 logical px, a row down
    counting 1.5).
  - Qt's own fields and the dividers fade on the same schedule (`Strip._fading`: a held `QGraphicsOpacityEffect`,
    disabled at rest - traps 201 / 204).
  - Going back: they fold toward the cursor, the farthest first (`fold_delay`, `back_in`), then the mask closes
    onto it 72 ms after the last one.
  - Interface animations off: at once.
  - Filmstrip: `render_time_bar_burst.py` -> `time_bar_burst.png`.
- **Bottom edge is the default** («по умолчанию выдвижной снизу таймлайн был активен при установке нашего
  обновления»): `look.DEFAULT_MODE` "edge", and once per `look.DEFAULT_VERSION` (optionVar
  `skeldarTimeBarDefaults`) `maya_timebar.upgrade()` - called first by `ensure()`, i.e. the hub's build - moves
  Docked or unset to the bottom edge; Maya's own slider, if chosen, is kept. A choice made after it stands. Raise
  DEFAULT_VERSION to make a later update switch it again.
- **Not hidden while Maya plays** (2026-10-17, «прятали тайм слайдер только когда он не используется»):
  `BottomEdge.blockers` adds "playing" (`play -q -state`), so the hide waits for the stop; and Play while it
  is hidden (a hotkey, Maya's own) brings it out with the same burst - `bar._time_changed` calls
  `BottomEdge.on_time` every frame: it reveals it from the cursor's x on the bar's row (`on_row`) and, since
  playback turns no event loop and the burst's timers do not tick, steps the burst itself on each frame
  (`BottomEdge.step`: `slide_tick`, the strip's `_animate`, a `repaint`). **A bake too** («когда мы делаем
  bake simulation таймслайдер тоже должен быть виден»): measured in mayapy, `bakeResults -simulation` walks the
  time frame by frame (the time-change callback fires on each) with `play -q -state` False, and
  `MCommandMessage` reports the command only after it ran (and never a Python `cmds` call). So `on_time` counts
  time changes outside playback, each within `BAKE_GAP_MS` (250) of the last; `BAKE_RUN` (3) in a row with the
  viewport NOT suspended (our own frame walks suspend it) is a bake: it reveals and steps the bar like Play,
  `baking` blocks the hide until a gap. Holding a step hotkey reads the same. Tests in `test_timebar_edge`;
  not seen in a GUI Maya.

**Speed** (the same evening: «проверим быстродействие... фпс программы проседает когда перетаскиваешь
ползунок»). Measured headless (`docs/superpowers/plans/bench_time_bar.py`: the real strip at 150 % on a fake
link, a key on every frame of 300, breakdowns, three bookmarks, a sound; a scrub at 60 steps a second; the
same run on the previous build through `TIMEBAR_PLUGIN`):
- before: the strip's own work **6.1 ms a scrub step** and **6.3 ms every 16 ms** while keys faded - on top of
  Maya's frame change, **5.8 ms** on a keyed Manny rig in parallel (`bench_time_bar_maya.py`, mayapy; the
  viewport's redraw comes on top in a GUI Maya). That roughly doubled a step's cost: the drop the animator felt.
- after: **0.97 ms** a step (0.12 with Interface animations off), **0.5 ms** a fade tick, a paint 0.06 ms:
  - the still part (the track, the sound as ONE path, bookmarks, the highlight, the ruler, the keys at rest as
    one path a colour) is one cached picture (`Timeline._static`), drawn again only when `_static_key`
    changes - the size, the view, the ranges, the keys, the marks, the sound, the highlight or a key drag's
    preview (`static_builds` counts, a test pins none during a scrub);
  - each frame paints the picture, the lit or lifted keys (`_draw_moving_keys`) and the playhead;
  - a lit key's glow is a picture drawn once per colour and size (`halo`), one drawPixmap instead of three
    antialiased rectangles.
- The time-change callback adds nothing measurable (5.75 against 5.77 ms).
- **The scrub meter** (`maya_timebar/meter.py`; the key menu's «Measure scrubbing (10 s)», hotkey row
  `timebar.measure`): for 10 s every frame change Maya makes is clocked through `MDGMessage` - whichever
  slider drives it, ours or Maya's - and, when ours does, its own work and Maya's `currentTime` per step
  (`look.meter_report`; pauses over 0.5 s are not counted). The report goes to the Script Editor and the
  viewport: the animator's A/B, ours against Maya's, in their own scene.

**Frames are cells, as in Maya's slider** (2026-10-17, the animator with two screenshots of Maya's: «кадр он не
пустой а как бы прямоугольной формы ... метка ключа отображает расположение ключа во времени ... ползунок ...
закрашивает прямоугольник кадра»):
- `look.Track(..., cells=True)` (the timeline only): frame f is the cell [f, f + 1), the track runs to v1 + 1,
  `whole(x)` is the cell x falls in (floor), `cell(f)`, `end(f)`; the wheel zooms over cell edges;
- the playhead fills its frame's cell (`HEAD_FILL`, accent edges top and bottom), the flag centred on it;
- a key is a line on its time (`add_key`, `KEY_W` 2.5): solid on a whole frame (`look.on_frame`), dashed where it
  stands between frames; lit and lifted keys the same mark, wider and glowing;
- the highlight covers its cells [a, b + 1) (`look.inside`): a move takes a key between frames in the last cell
  and keeps its fraction (`mapped`, `scene.move_keys`); an edge drag counts frame lines (`Timeline._grip`);
- the playback range's dimming starts after p1's cell; `passed` lights the keys in the playhead's cell.

**Two key effects, the rest of the mockup taken back** (2026-10-17). The whole effects mockup went in
(`6c76e6b`: a playhead glide, a scrub trail, play / loop / move / bookmark effects, button ripples, morphs and
sparks); the same day the animator: «откатив все эффекты вернем как было. Только одно исключение оставим вспышку
глоу (без частиц) когда ставим ключик и эффект удаления ключа тоже оставим только без глоу одни частицы ... не
делай глоу овальной формы пускай будет круглый». So bar.py and look.py are the build before, plus:
- `FxLayer` (`skeldarTimeBarFx`): a mouse-deaf child over the whole strip, painting only while an effect lives.
  A key set: a ROUND glow (`soft_dot`, 30 logical px, its colour the key's) with a small warm core, 520 ms. A
  key deleted: 24 sparks thrown up and falling (`look.sparks`, seeded, drawn from their age), no glow, 600 ms.
- Read by diffing the keys a refresh reads (`look.key_changes`): the first read, a reload (more than
  `SMALL_CHANGE` keys), a snap onto a frame and a key move (`_quiet_keys`) start nothing; none with ⋮ →
  Interface animations off.
- Speed as before the mockup (`bench_time_bar.py`: a scrub step 1.5 ms). 110 timebar tests. Not seen in a GUI Maya.
- **…and two more back** (minutes later: «эффект сужения на таймлайне когда нажал плей ... клеточки ... перекрашиваются
  и гаснут ... добавим его для плей режима»): Play pressed closes an accent frame in round the timeline (`played`,
  `play_at`, 420 ms; stopping makes none); the cell the playhead leaves glows `TRAIL_ALPHA` 0.28 and fades over 380 ms
  (`Timeline.leave`, `trail`) - while scrubbing, and in playback from `on_time`. Playback turns no timer (trap 269), so
  the trail is drawn from its age in the paint `on_time` forces and pruned on each `leave`. A scrub step 1.6 ms; 116
  timebar tests.
- **…a key fills its frame** (the same day, from an animated mockup: «ключ закрашивает кадр»): a key on a whole
  frame is its cell filled, rounded 1.5 px (`look.key_cell`: a gap of 0.18 of the cell, at most 3 logical px,
  between neighbours, none in a cell too thin for it; 2 px inset top and bottom); a lit key's cell grows 1.5 px
  with its glow, an entering one is squeezed about its middle. A key between frames stays a dashed line on its
  time. Aim, the key effects and the entrance use the cell's middle (`look.key_centre`), and a key is aimed
  anywhere in its cell. A scrub step 2.0 ms (bench); 126 timebar tests. Not seen in a GUI Maya.
- **…stronger** (the same day: «глоу должен быть сильнее ... брызги ярче»): both effects are drawn as ADDED
  light (`CompositionMode_Plus`); a key set: a halo `SET_GLOW` 44 logical px laid twice plus a 13 px hot core,
  fading as (1 − u)^1.5; a key deleted: `SPARKS` 34, each a 6 px glow in the key's colour with a hot `RIM` core.
- **…a deletion of many keys is a wave, left to right, within 300 ms** (the same day: «массив ключей ... по
  очереди с лева на право ... 1000 ... не дольше чем 300 мс ... ключи должны удалиться мгновенно»). The keys
  are gone at once; only the sparks are staggered (`Timeline.delete_wave`, `look.delete_plan`): one key as
  before, up to `SMALL_CHANGE` 40 ms apart, more spread over 120 ms with a 180 ms life each (the sparks fly
  faster to keep their reach), `SPARK_BUDGET` 700 sparks a wave (1000 keys: one each). A pure deletion of any
  size counts only when Maya reported a key edit (`keys_edited`, set by the AnimKeyframeEdited callback and our
  own Cut / Delete), so a selection change dropping many keys plays nothing. A spark is one cached picture
  (`spark_sprite`). A 1000-key wave: setup 9 ms, frames ≤ 6.3 ms (the timeline's own redraw after the keys go,
  68 ms, is there without the wave too). PySide6's `drawPixmapFragments` takes one fragment, not a list.
  133 timebar tests.
- **…the sparks replaced: a deleted key BREAKS, the wave twice as slow; a key set over a key flashes** (the same
  day: «3-5 кусочков которые разлетаются и по объему повторяют сам ключ ... скорость удаления массива ключей можно
  замедлить в двое», then «эффект постановки ключа должен срабатывать даже если ключ уже стоял»). This replaces
  the sparks and the 300 ms above.
  - `look.shards`: the key's own rectangle (its cell, or its line between frames) cut down its height into 3..5
    uneven pieces (`shard_cuts`, `SHARDS`) that together ARE the key at age 0. They part left and right
    alternately, are kicked up (the top ones higher), spin, fall, and fade over the last half. `EFFECT_MS`
    delete 700.
  - The wave: `DELETE_STEP_MS` 80, `DELETE_TOTAL_MS` 600, `DELETE_LIFE_MIN` 360. Past `SHARD_BUDGET` (900
    pieces) neighbouring keys break as one block of their keys (`shard_groups`): 1000 keys, a pixel or two
    each, throw ~900 pieces, not 3000. A piece is a `fillRect` under its own transform (3000 in 8.7 ms
    antialiased; paths of many subpaths were slower). A 1000-key wave: frames ≤ 8.2 ms.
  - A key set over a standing key changes no key time, so Maya's MEL `setKeyframe` (the S key, Channel Box ›
    Key) is read off `MCommandMessage.addCommandCallback` (`look.set_key_command`: `-t`/`-time`, else the
    current frame; a Python `cmds.setKeyframe` is not reported) and flashes when its frame holds a key; the
    strip's own Set key marks itself. 138 timebar tests. Not seen in a GUI Maya.
  - **The wave's rule changed the same day** («когда ключей много осколки летят сильно далеко и сильно быстро ...
    полет самих частиц не должен ускоряться ... запустить эффект не позднее чем за 1 секунду»): every key flies
    exactly as a single key - the whole `EFFECT_MS` 700, the same speed and gravity - and only the starts are
    staggered, `DELETE_STEP_MS` 80 apart, squeezed so the last starts by `DELETE_START_MS` 1000. The 600 ms
    total and the faster short-lived pieces are gone. A 1000-key wave: frames ≤ 3.7 ms.
  - **…the last within 0.5 s, and a key stays drawn until it breaks** (minutes later: «максимальное время
    уменьшим до 0.5 ... не нужно удалять картинку ключа пока не запустился разлет осколков»): `DELETE_START_MS`
    500. Each wave item carries its keys' own rectangles (`ghosts`); while it waits its turn the overlay draws
    them as the keys were, so a key vanishes only when its pieces fly. The data is still gone at once.
    A 1000-key wave: frames ≤ 9.7 ms.
  - **…the flight is «Snap and drop»** («давай уменьшим дальность разлета или скорость ... тестовые макеты»):
    six flights were played side by side at the strip's real 84 px, clipped as in Maya
    (https://claude.ai/artifact/T7Re27ujCv5iAAT3RPyrwv), and the animator picked D: `SHARD_SPEED` 110,
    `SHARD_FALL` 1600, `SHARD_SPIN` 300 (logical px / s, deg / s), `EFFECT_MS` delete 600. It was 260 / 900 /
    540 / 700, which threw the pieces out of the strip's top. Then «на 30 процентов увеличим силу разлета»:
    `SHARD_SPEED` 143. Then «B · Shorter - давай вот эту попробуем»: B is what stands - `SHARD_SPEED` 170,
    `SHARD_FALL` 900, `SHARD_SPIN` 420, `EFFECT_MS` delete 700.

271. **Python painting element by element costs more than the drawing.** The Time Bar's paint called
     drawRect / drawRoundedRect ~1700 times a frame (a waveform bin, a tick, a key each) and cProfile put 2.6
     of its 6 ms in the Python loop itself. What does not change between two frames belongs in a cached
     QPixmap, many like shapes in one QPainterPath, a repeated glow in a sprite.

**Proof**:
- `tests/test_timebar_look.py` and `tests/test_timebar_bar.py`: 71 tests. The strip runs offscreen on a fake
  link and covers both rows, painting, scrubbing, the middle scrub, the transport, highlights, key moves and
  scales, the range block, zoom, the menus' rows, toggles, the reached keys and the opening.
- `docs/superpowers/plans/verify_time_bar.py`: **all gates passed in mayapy standalone**:
  - keys and breakdowns read;
  - the highlight round trip;
  - a move, a scale and a single key, each one undo, on whole frames;
  - the key menu's commands;
  - scrub without update;
  - loop / speed / cache;
  - bookmarks made and stepped;
  - a generated `.wav`'s click found at its frame with the sound's offset;
  - character sets listed;
  - layers.
  The current character set is a GUI-only check: batch Maya keeps none.
- `docs/superpowers/plans/render_time_bar.py` -> `time_bar.png`: three states at 150 %.

**Not seen in a GUI Maya**: the docking without a tab, real playback, the sound scrubbing, the highlight seen by
Maya's own commands.

269. **A widget painted with `update()` waits for an idle Maya never gives between frames.** `currentTime`
     evaluates the scene before it returns and playback does not turn the event loop, so the Time Bar's playhead
     jumped several frames while Maya's own slider moved on every one. Paint what must follow time with
     `repaint()` before the call that evaluates, and from the `timeChanged` job.

## Side panel: the Channel Box and the Attribute Editor at the right edge (2026-10-17)

The animator: «боковую панель по концепту нашего таймлайна, только для chanalbox/layer editor и атрибут
эдитор», then «Сделай все до конца на свое усмотрение». Every choice was taken alone. Spec
`docs/superpowers/specs/2026-10-17-side-panel-design.md`. Package `SkeldarAnim/maya_sidepanel/`
(a payload row).
- **The Time Bar's bottom edge on its side**: a frameless Qt.Tool host along the right of Maya's
  window, 340 logical px (260..700, a grip on its left edge, `skeldarSidePanelWidth`). It comes out
  when the cursor rests in a 14 px zone or on the 2 px sensor, unrolls from the cursor's height
  (`maya_timebar.look.unroll`), and goes 1.2 s after the cursor left. A 📌, a held reveal
  (`maya_edgerules.Hold`), a button, a menu or typing in a field keep it out. `look.py` is
  stdlib; `edge.py` (`SideEdge`) and `panel.py` are Qt.
- **Maya's own editors, borrowed, not copied** (`holder.py`): the Qt widgets of
  `MainChannelsLayersLayout` (or `MainChannelBoxLayout` + `MainLayerEditorLayout` with
  channelsLayersSeparate) and `MainAttributeEditorLayout` go into the tabs
  `[Channels | Attributes]` (`skeldarSidePanelTab`), and their workspaceControls are hidden. The
  record of each (control, parent's objectName, index, shown) is on `sys._skeldar_sidepanel`.
  **Give back before any delete**: `drop_edge` gives every form back, then deletes the host. A
  host deleted with a form inside would delete Maya's editor.
- **Maya must think they are shown**: the Attribute Editor refreshes only while
  `isAttributeEditorVisible()` is true, and showEditor (Ctrl+A) would restore the empty control.
  While held, `isAttributeEditorVisible` / `isChannelBoxVisible` are redefined
  (`look.MEL_OVERRIDE`, asking `maya_sidepanel.holds(tab)`); off, Maya's two files are sourced
  again.
- A held editor's control shown again by Maya (its toggles, Windows menu) is hidden on the next
  300 ms tick, and ours comes out on that tab, held (`_maya_wants`).
- Controls we hid are remembered (`skeldarSidePanelHidden`) and shown again in Maya's mode, at the
  next start too.
- ⋮ -> **Side panel ▸ Maya's / Right edge** (`skeldarSidePanelMode`, **Maya's by default** until
  seen live). The hub's build calls `ensure()` deferred. Hotkey rows `window.sidepanel`,
  `sidepanel.channels`, `sidepanel.attributes`.
- Proof: `tests/test_sidepanel.py` (the band, the zone, out / back, the pin, a hold, the grip, the
  tabs, take / give on stand-in widgets), 7201 unit tests. `verify_side_panel.py` (GUI, ten
  gates) is written and not run.
- **First live use, the same day** («панель не отрендерилась полностью, парамметров нету»), two
  defects found over port 7001 and fixed (pictures by DWM `PrintWindow`, never `grab()`, trap 134):
  - trap 276: the Attribute Editor never updated. Fix: our own `skeldarSidePanelRefreshAE`
    (`look.MEL_REFRESH_AE`), an unconditional `updateAE` of the last selected node. It runs on
    reveal, on a tab switch and deferred after every SelectionChanged while the panel is out on
    Attributes (a job killed by `drop_edge`);
  - the Attribute Editor wants ~648 px at 150 % and the host grew to it while its mask stayed at
    510: half the panel was black. The host's layout is `SetNoConstraint`, and the band is at
    least what the borrowed forms' `minimumSizeHint` asks (`look.min_width_px`, `SideEdge.least`).
  Seen live after: pCube1's and persp's attributes following the selection, the panel drawn
  whole, the Channel Box exact.

- **The Time Bar's burst, and a wider zone** (the same day: «хороший дизайн и плавная анимация ...
  точно также и для этих панелей ... невидимая область»). Maya's editors are too heavy to move
  frame by frame, so a PICTURE moves. The reveal shows the host at window opacity 0, refreshes the
  editors, and takes the panel's picture by DWM `PrintWindow` (~60 ms, live). An overlay
  (`skeldarSidePanelBurst`) paints that picture in `look.rows` of 44 logical px, each popping
  (`maya_timebar.look.popping`) nearest the cursor's height first (`open_delay`), under the mask
  unrolling from the cursor. Going back, the rows fold the farthest first (`fold_delay`), then
  the mask closes onto the cursor. Measured live: out 424 ms, back 582 ms; no picture means the
  plain unroll. The zone is 48 logical px (was 14).
- **Inside the other interfaces' bounds** (the same day: «не растягивалась на весь экран а видела
  границы других интрефейсов»). The panel, its sensor and zone live in the viewport area: Maya's
  `MainPane` workspaceControl, under the menus, status line, shelf and scene tabs. They end above
  the Time Bar's band when it sits at the bottom edge (`look.area`, `edge._window_rect`, looked up
  every 300 ms). Measured live: the window (0, 34, 2560, 1494), the pane (2, 176, 2556, 1350),
  the panel 176..1411 with the Time Bar's host from 1411. The least width is read again on every
  refresh (`_fit`): the Attribute Editor asks 308 px empty and 648 px on a mesh.
- **Out while something is selected** (the same day: «если у нас не пустое выделение то она
  выезжает и не прячется. Суть в том что бы показывать панель тогда когда она нужна»). The
  deferred SelectionChanged job calls `SideEdge.selection_changed()`. Something selected brings
  the panel out (from the cursor's height) and `selected` keeps it out (`look.blockers`).
  Nothing selected starts the usual hide (the cursor over it, the 📌 still keep it). The edge
  hover works as before, and a panel built with a selection standing comes out at once.
  Seen live: pSphere1 selected, out, kept by `selected`. **During playback** («во время плей мода
  выделяю объект то панель не выезжает») no idle and no timer tick comes between frames (trap 269):
  the selection job runs `later()` at once instead of `evalDeferred`, the reveal is instant, and
  `repaint_all` repaints the host synchronously - and the selection is heard through
  `om.MEventMessage.addEventCallback("SelectionChanged")`, not a scriptJob (trap 277). Seen live
  after that: pSphere1 selected at frame 10 of playback, the panel out at once, its Channel Box
  filled. The first try (scriptJob) did nothing: commands sent over the port wait
  for idle too, so playback is the animator's to try.
- **The Time Bar steps aside, the panel goes to the bottom** (the same day: «таймслайдер будет
  тоже учитывать наши интрефейсы и не перекрывать их ... если нет на экране таймслайдера то
  можно нашу боковую панель растянуть до низа»). The side panel takes MainPane's whole height
  again. The Time Bar's bottom-edge band and sensor are cut to `maya_timebar.look.free_span`:
  MainPane across (docked editors left out), less our panels reaching into the band
  (`edge._obstacles`). Those are the side panel while it shows (hidden, it leaves the bar the whole width - «не доезжает до края»; the bottom-right corner is then the bar's, `sidepanel.edge.in_timebar_band`) and
  the hub's edge panel while out; a panel in the right half cuts the end, in the left the start.
  The side panel's reveal and hide call `nudge_timebar()` so the bar moves at once. Live: side
  out 2008..2558 down to 1526, the bar 2..2008; side in, the bar 2..2558. **The side panel waits
  600 ms before it hides** (`look.HIDE_MS`, half the Time Bar's 1200: «в 2 раза меньше»).

277. **A scriptJob does not fire during playback.** Maya runs scriptJobs when it is idle, and
     playback never is: a timeChanged job fired 0 times in 25 s of playback (measured
     2026-10-17), and the side panel's SelectionChanged job never heard a selection made while
     playing. What must react during playback hangs on OpenMaya callbacks
     (`MEventMessage.addEventCallback`, `MDGMessage.addTimeChangeCallback` - the Time Bar's).

276. **Maya's `autoUpdateAttrEd` updates the Attribute Editor only while its workspaceControl is
     RAISED** (`workspaceControl -q -raise`); otherwise it sets `$gAEDeferredUpdate`, to be done
     when the control is raised. A form moved out of a hidden control is never refreshed, even
     with `isAttributeEditorVisible` answering true. Call `updateAE` yourself, deferred after
     Maya's own selection handlers: run first, it was undone, the AE back on "Select an object".

## Maya theme: Maya in the hub's colours (2026-10-17)

The animator: «Можем ли мы поменять цвета маи под наш интерфейс?». Four mockups
(https://claude.ai/artifact/3cscUGngcoXQjp4on8Lr1Z); they chose **B, the hub whole**. Spec
`docs/superpowers/specs/2026-10-17-maya-theme-design.md`. `SkeldarAnim/maya_mayatheme.py` (stdlib at import, a
payload row); ⋮ → **Maya theme**, a checkable row (optionVar `skeldarMayaTheme`, **off by default**).
- **Qt's palette** on the QApplication from `hubstyle.TOKENS` (`PALETTE`, `DISABLED`; selection `#5a3922` with
  `accent_text`), and **a sheet appended to the application's own** between `START` / `END` markers: tooltips, the
  menu bar, line edits, item-view selection, header sections, splitter handles. **Colours, borders and radii only,
  never a size** (a test pins it) and no blanket QWidget rule: the hub's root sheet sets the same properties for its
  widgets and wins.
- **Maya's display colours** (`RGB`: the viewport gradient, the Graph Editor, Outliner child highlight, Node Editor,
  Dope Sheet, Hypergraph) plus `displayPref -displayGradient` on. Keys, curves, tangents and manipulators keep Maya's.
- On: what stands is kept ONCE as JSON in `skeldarMayaTheme_saved` (a second On never saves the theme as theirs);
  Off: written back, the memory removed, the palette and sheet put back (`sys._skeldar_mayatheme`). At Maya's start the
  hub's build calls `ensure()` (deferred): only the Qt part, since Maya keeps the display colours in its prefs.
- Proof: `tests/test_mayatheme.py` (18, the Qt part offscreen), the menu row in `test_hubqt`; 7078 unit tests.
  **`verify_maya_theme.py` (a GUI Maya: every colour, the palette and sheet, Maya controls' size hints unchanged,
  playblasts on/off, everything back after Off) is written and NOT run.** Not seen in a GUI Maya: how far Maya's own
  style follows the palette.

## Maya icons: every icon recoloured, the most visible redrawn (2026-10-17)

The animator: «перерисовать все иконки интерфейса маи под наш стиль»; shown both ways
(https://claude.ai/artifact/TpsFZDd63bpcYJ6Wm7EZ5w), «Build both». Spec
`docs/superpowers/specs/2026-10-17-maya-icons-design.md` - **read its addendum**: the first build (997a053) wrote into
prefs/icons and changed nothing on screen. ⋮ → **Maya icons** (optionVar `skeldarMayaIcons`, off by default), **at
once, no restart**.
- **How Maya finds its icons** (measured in a scratch GUI Maya): every icon is in Qt's resources at three sizes,
  `:/name.png`, `:/name_150.png`, `:/name_200.png` (`resourceManager` lists only the 1x), and a 150 % display takes
  the `_150`. **Maya's own buttons never read prefs/icons**, a restart changes nothing, a registered `QResource`
  does not override Maya's; `MQtUtil.createIcon` answers a prefs/icons file, which made the first mayapy proof pass
  while the screen did not change. **A button pointed at a file by its full path draws it at once.**
- `SkeldarAnim/maya_mayaicons.py`: On draws or recolours all 7282 PNGs at the root of `:/` into
  `<userAppDir>/<version>/SkeldarIcons` (`write_icons`, 10.9 s; `recolour` numpy: greys between the hub's darkest and
  its text by luminance, saturated colours to the accent's hue, alpha kept, `AXES` keep their red/green/blue), then
  points every icon button of `KINDS` there (`repoint` over `lsUI -type <kind> -long` - **by full path: every
  viewport's bar names its buttons alike**, `pointed` pure) and starts a Qt timer that sweeps again every `WATCH_MS`
  2 s for panels built later (~0.02 s a sweep). The hub's build calls `ensure()` at Maya's start. Off points every
  button back at its bare name and empties the folder; the first build's prefs/icons files go by its manifest.
  **Autodesk's pictures are recoloured on each machine and never shipped.** Not changed: the Outliner's node icons and
  anything else Maya draws without a cmds image.
- `SkeldarAnim/maya_mayaicons_art.py` (stdlib): 24-grid SVG bodies, classes `l` / `a` / `m` / `f` / `af` / `tint`
  (and the dashed `ld` / `ad` / `md`); **146 hand drawings** (`ART`) out of the 184 icons Maya's main bars name, plus
  the 16 panel layouts generated from their names (`layout_panels`) and 14 selection-mask "Partial" states. Drawn at
  each size's own pixels (`base_stem`: `move_M_150.png` is `move_M` at 48 px).
- Proof: `tests/test_mayaicons.py` (25); live in a scratch Maya: 347 buttons on ours at once, every viewport's bar,
  the Graph Editor opened afterwards caught by the watch, Off 425 back and none left (pictures in the session only).
  `docs/superpowers/plans/verify_maya_icons.py` (GUI, phased) is written to that run's gates. `render_maya_icons.py`
  draws Maya / recoloured / ours side by side (local only: it holds Autodesk's pictures).

243. **QtSvg drops a dashed element's stroke when the dash is an attribute or a style beside its CSS class**
     (measured 2026-10-17: `class="m" stroke-dasharray="2.2 2.2"` and `class="m" style="stroke-dasharray:..."` both
     drew nothing - `pickTemplate` came out empty). A dashed class of its own (`.md{stroke-dasharray:2.2,2.2}`) draws.
244. **"Maya's icon lookup answers our file" is not "Maya's buttons show it".** `MQtUtil.createIcon("move_M.png")`
     answered a prefs/icons file in mayapy and in the GUI, and every button Maya draws - the toolbox, the status line,
     the panel bars, a fresh `iconTextButton` - drew its Qt resource all the same, after a restart too. A proof about
     what is on screen looks at the screen (a window grab), and a cmds control is edited by its full path.

**Both hidden the same day** (the animator: «давай пока откатим наши наработки по изменению цвета и иконок вернем
старые цвета в маю по умолчанию а функционал который включает новые спрячем но оставим в проекте»):
`skeldar_features.MAYA_THEME` and `MAYA_ICONS` are False, so the hub menu builds neither row
(`maya_hubqt.feature`, `FLAGGED_ROWS`; the paint methods do nothing without their row), and the hub's build
(`maya_hub._on_or_retired`) switches off whichever the animator left on - the theme's saved colours written back, our
icon files taken out of SkeldarIcons and prefs/icons, every button back on Maya's. Flip a flag to bring a row back;
the modules, tests, specs and verify scripts stay.
