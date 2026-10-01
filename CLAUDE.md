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
│   ├── install.py  README_INSTALL.txt  skeldar_features.py
│   ├── maya_overrig/  maya_uebridge/  maya_scenesetup/
│   ├── maya_rigs.py  maya_asretarget.py  maya_pmretarget.py  maya_rig_retarget.py
│   ├── maya_hotkeys.py  maya_vpstudio.py  maya_colour.py  maya_overshoot.py
│   └── icons/  assets/  overrig/
├── sources/                  what the assets are REBUILT from -- never ships
│   ├── weapons/  orc/  creep/  manny/  README.md
│   └── AdvancedSkeleton/     local only, .gitignore (its licence)
├── make_build.py             dev tool: builds the zip from SkeldarAnim/
├── .github/workflows/        every plugin push -> a release (Check update)
├── maya_skelfit.py  maya_meltmorph.py  maya_retarget.py  ...
└── tests/  docs/  archive/  CLAUDE.md
```

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
Overlay is out of the plugin (`archive/maya_curveview`).**
Everything below about OverRig, the Rig Picker, Connect Arms, Add Aim and
Camera Setup as a button describes code that is still in the repo and the
payload, and still tested, but not on the shelf; two flags bring it back.

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
`Manny_Skeleton.ma`, `maya_skelfit` asks it that way), «UE4 Mannequin
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
the plugin as asked — `archive/maya_curveview/` holds the package, its six
test modules and `verify_curveview.py` (last shipped at commit `f65be61`;
its section below is history) — and `alt+c` is given back through
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
the bone back to 0.000000. `verify_many_rigs.py`'s camera gates were
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

- **CI**: `.github/workflows/build.yml`, on push to `feature/overrig-picker`
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
Qt 6.8.3 ship with Maya 2027). 2041 tests at time of writing, all passing.

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

## `maya_curveview` — Curve Overlay: the graph editor over the viewport (ARCHIVED 2026-09-08)

**Out of the plugin since 2026-09-08** at the animator's ask («уберем не
только из полки но и из плагина в целом»): the package, its six test
modules and `verify_curveview.py` live in `archive/maya_curveview/`, last
shipped at commit `f65be61`. The section below is kept as the record of
what was measured building it; nothing in it is on the shelf or in the
payload.

The **ninth** shelf button (2026-09-05), a package
(`SkeldarAnim/maya_curveview/`) — the animator's ask: «сделать свой кастомный
граф эдитор в мая… кривые рисовались прямо поверх вьюпорта, так чтобы я мог
двигать кривую прямо во вьюпорте… какой-то режим превращал мой вьюпорт в граф
эдитор с прозрачным фоном». Spec:
`docs/superpowers/specs/2026-09-05-viewport-curve-overlay-design.md` — **read
its ADDENDUM**, which reverses three of the main text's decisions the same
day. Proof: `docs/superpowers/plans/verify_curveview.py` — **green live
2026-09-05, 0 of 44 gates failed**, 1943 unit tests.

```python
import sys; sys.path.append(r"C:/!!!Work/MayaScripts/SkeldarAnim")
import maya_curveview; maya_curveview.toggle()
```

One press turns the whole viewport into a graph editor with no background:
the selected control's curves are drawn over the live picture, keys as
squares on the keys, and the character stays visible underneath. **The point
is the feedback loop, not the screen space** — «Хочу править кривые и сразу
же смотреть на результат».

**The architecture was chosen from five live probes, not from an opinion
about Qt**, and every one of these is measured:

- **`QmayaGLWidget` is a NATIVE Windows window** (inside a `QStackedWidget`
  inside two `QmayaLayoutWidget`s). A native child window composites above
  every non-native sibling, so a child overlay **cannot paint over the
  viewport at all** — and Maya's own layout owns the panel, which gave a
  child overlay a height of **zero** with `paintEvent` running 0 times.
- **A frameless translucent TOP-LEVEL window does composite**, with real
  alpha over live GL: the character, the grid, the manipulator arrows and
  Maya's own `Focal Length / 10.4 fps` HUD all read through it.
- **Qt's `WA_TransparentForMouseEvents` does NOT pass the mouse through a
  top-level window** — under the overlay there was no marquee and no camera
  orbit. It is a Qt-internal routing flag: it forwards an event to the widget
  below **inside the same window**, and Qt forwards nothing across a
  native-window boundary. The Windows recipe is
  **`WS_EX_LAYERED | WS_EX_TRANSPARENT`** through ctypes, applied **after
  `show()`** (re-parenting recreates the native window and loses it) — and
  `alt`+LMB then orbits the camera straight through the overlay.
- **`cmds.draggerContext` runs its command as PYTHON, not MEL.** A MEL-style
  `python("...")` answered `NameError: name 'python' is not defined`, which
  was itself the proof that the callback fires.
- **`draggerContext(space="screen")` reports `[x, y, 0.0]` viewport-local
  with Y from the BOTTOM** — `qt_y = height − y`, confirmed by drawing both
  readings and watching which followed the cursor. `button` is `1` for LMB,
  `modifier` is a **string** (`'none'`), and `alt` never arrives: all 1725
  drag events of a recorded session carried `'none'` while the animator was
  orbiting.
- **~860 events per drag**, about one per pixel of travel.

So input is an ordinary Maya context — which is the whole reason the camera
still works, since `alt`+mouse is taken upstream in Maya's own event
dispatch — and the overlay is a pure painter the OS hit-tests straight
through. The rejected alternatives are in the spec: a `MPxContext` +
`MUIDrawManager` plugin (the fallback, its one unknown never closed), and a
Qt overlay handling its own mouse (dead on the measurement above).

| Module | Responsibility | May import |
|---|---|---|
| `mapping.py` | **all the arithmetic**: time/value ↔ pixels, the Y flip, autoframe, normalise, hit-testing, marquee, grid step, tangent geometry, the modifier table, the throttle decision | **stdlib only** |
| `curves.py` | which curves are drawn (the channel-box rule), plugs → animCurves, sampling | `maya.cmds` |
| `edits.py` | the undo chunk, the relative key move, tangents, insert/delete, the throttled time follow | `maya.cmds` |
| `overlay.py` | the window: translucency, click-through, painting | **Qt + ctypes only, never `maya.cmds`** |
| `viewport.py` | the active model panel's GL widget and its global rect | `maya.cmds`, Qt |
| `tool.py` | the dragger context, the gestures, entering and leaving the mode | `maya.cmds` + all the above |

Both boundaries are enforced by subprocess tests, as `bodymap`'s is.

**The gestures.** LMB **works on keys, and selects objects when it caught
none** — a click with nothing under it click-selects in the scene, a marquee
that caught no key box-selects, and both halves are reachable with no modal
switch. MMB drags the selected keys, or a tangent handle when the press
landed on one: the Graph Editor's own division of labour, which the animator
already has in his hands. `alt`+anything is the camera, natively.

**Key selection is MAYA's**, not a private set: a key picked in the overlay
is picked in the Graph Editor too, `cmds.keyframe(edit=True,
relative=True, animation="keys")` moves "the selected keys" with no list to
pass, and undo needs no bookkeeping of ours.

**What is drawn, and the fix that only LOOKING found.** No selection means
nothing at all. A selected control means the channels picked in the channel
box; with nothing picked there it means the **TRANSFORM** channels, widening
to everything animated only when the node has no animated transform channel
(so a rig gizmo animated on custom attributes still shows). The reason is
measured: the most animated transform in the animator's own scene is a UE
clip's `root` with **141 animated channels** — `Pose_0..9`, `MoveData_*`,
`DisableLegIK` and about 130 pose drivers, which **trap 40** is the record of:
the game's data, not animation anybody poses. Drawn together they crushed the
real root motion into a flat band. `MAX_CURVES` (12) is the backstop behind
that and **names the count** rather than silently drawing twelve of a hundred.
A custom attribute is still one channel-box click away.

The same look found there was **no value axis at all** — the shape of a curve
read and its magnitude did not, which is half a graph editor. Horizontal lines
come from `mapping.value_lines`, which has **no floor of 1** unlike the frame
grid (a rotation living between 0 and 0.5 still needs lines), with the zero
line brighter and a short label at the left edge. They are skipped when
normalised, where one shared value line would be a lie — `Scene` carries the
flag for exactly that.

**How that was looked at, since a screen grab cannot be trusted here:** the
picture is a composite of a real one-frame `playblast` (exactly what the
viewport renders) and the overlay's own `render()` into a `QImage` (exactly
what it paints), alpha-blended. Both halves are the real thing and it does
not care which window is in front — which a screen grab does, and the
animator is usually reading somewhere else.

Load-bearing details, each measured or paid for elsewhere:

- **The drag sends the DIFFERENCE from what it has already applied**, never
  the running total — snapping the time to whole frames on a total would
  re-round every one of ~860 events and drift. A test walks 200 events to
  +37 frames and asserts they sum to exactly 37.
- **Sampling evaluates the animCURVE NODE** (`cmds.keyframe(curve,
  query=True, eval=True, time=(t, t))`), never the driven plug: a plug
  sample pulls a whole rig evaluation, which on the animator's scene is
  10 fps per sample.
- **The Y window is fitted to the SAMPLES as well as the keys**, because a
  curve overshoots between its keys and that overshoot is the shape being
  looked at.
- **Time follows the dragged key, throttled to ~20 Hz**, with one guaranteed
  evaluation on release. One gate governs both the evaluation and the
  repaint, since a repaint needs a re-sample anyway.
- **There is no pan and no zoom.** X is the playback range — so the curve's
  time lines up under the time slider — and Y autofits. That is what leaves
  every camera gesture to the camera, and it removes a whole subsystem.
  `normalise` (one Y window per curve) is a toggle for channels of different
  magnitudes; the default is the shared axis, as the Graph Editor's is.
- **The viewport is followed by a 10 Hz QTimer, not an event filter.** Maya
  destroys and rebuilds those widgets on a layout change, so a filter dies
  with them; a timer comparing the rectangle covers the window move,
  Ctrl+Space, the layout switch, a monitor with another DPI **and** the
  focus change in one mechanism.
- **Changing the tool leaves the mode** (a scriptJob on `ToolChanged`).
  Press W and the context is no longer ours, so an overlay still hanging
  there lies: curves are drawn and nothing can grab them. That is exactly
  what happened between two probes.
- `selectKey(clear=True)` is wrapped — **trap 43**: it RAISES when nothing
  is selected, which is exactly the case with nothing to clear.

**`MGlobal.selectFromScreen`'s CLICK form of `kXORWithList` is a NO-OP**, and
this is the bug the live run found. Measured from both starting states: from
an empty selection it selects nothing, from a held one it changes nothing —
while the **box** form of the same value toggles correctly. So shift-click
silently did nothing, which is the worst kind of wrong: the animator
shift-clicks, sees no change, and blames their own aim. The pick is now
always `kReplaceList` — the one value measured to behave identically in both
forms — and the modifier is applied afterwards through `cmds.select(...
add/toggle/deselect)`. Gate 29b keeps the quirk itself measured, so a Maya
that fixes it will announce itself.

**`cutKey(clear=True)` answers 0 even when it worked**, so the status line
read "Deleted 0 key(s)" over keys it had just removed. Counted before the cut.

Two harness facts this feature paid for, both of which will bite the next
live run:

- **Maya's pick runs through the viewport's own DRAW pass**, so a node that
  has never been drawn cannot be found: an unrefreshed locator at screen
  centre picked nothing at all under every adjustment, which reads exactly
  like a broken adjustment table and cost a whole probe round. Trap 14's
  family. Real use always has a drawn viewport; a verify run must ask for
  one with `cmds.refresh()`.
- **The Qt event loop does not turn while a bridge script holds the main
  thread**, so a window it just created has never been exposed and
  `repaint()` is a **no-op** — `paint_count` stayed 0 while the window was
  up and correct. `render()` into a `QImage` forces `paintEvent`
  synchronously, and the gate counts the non-zero bytes it left (164067 of
  7874460) rather than trusting that it ran.

Stated costs, not hidden: the overlay sits above Maya's own panels, so a
menu opened over the viewport gets curve lines drawn across it (reduced by
hiding on focus loss, not removed); **Windows only**, since click-through is
the Win32 ex-style; one viewport at a time, the active model panel; and
**`playblast` never sees the overlay** — it is an OS window, not part of the
viewport render, so reviews come out clean of curves.

Not built: weighted-tangent dragging, curve cycling/infinity display, the
Dope Sheet's key grid, retiming tools. Hotkeys: `alt+c` toggles the mode,
and three more rows (insert a key at the current frame, delete the selected
keys, normalise on/off) are in `maya_hotkeys` waiting to be bound.

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
sibling of `maya_retarget.py` — that one drives another skeleton FROM Manny,
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
  the target controls' keys outside the range kept. **The whole take**: playback ∪ every involved
  control's keys, the blend unkeyed, a constant channel collapsed to a value. autoKey off, one undo chunk.
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

Not built: legs (toes, heel roll, IKToes), scale, an IK stretched to a longer FK arm, hotkey rows
(`maya_hotkeys.py` held another session's uncommitted work, and nobody asked).

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
  zero with `ik_hand_r` 110 cm under it); a UE4 target takes `maya_retarget`'s spine map; baked
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

## Armor: the Tech Limb out of Atone, a card that equips it (2026-10-01)

The animator, with the Atone editor open: «достанем technolimb сам его fbx и добавим его ... в наши ассеты с
возможностью одеть ... не будем добавлять его в панель с оружием а сделаем для него отдельную панель Armor в
которой пока будет только техно лимб но позже мы добавим еще разные варианты одежды и брони ... не нужно делать
сетчатый инвентарь а просто будем выделять предмет нажимать кнопочку equip и он будет добавляться к нашему
персонажу в заранее указанное место». Asked: the item is **the plate only**, and the card shows **icon tiles**.
Spec `docs/superpowers/specs/2026-10-01-armor-techlimb-design.md`, plan beside it.

**What the Tech Limb is in Atone** (measured over Remote Execution, project `Atone`):
- `DA_Techlimb.equip_socket` = `lowerarm_l`. `UEquipmentComponent::AttachActorToSocket` snaps the actor
  (`SnapToTargetNotIncludingScale`) to that socket, and neither `SKM_Manny_Simple_3p` nor `_1p` has a socket of
  that name, so it lands on the bone.
- `BP_Techlimb`'s visible parts:
  - **`SM_Shield_Test`**: the plate, a shield frame, a ring with a boss and three studs. Its source is
    `S3.obj` on the Desktop. 1526 render vertices, at (0.079, −0.550, 0.328) / (P 1.187, Y 89.817,
    R 84.316) / scale 1.17647. It wears `M_TechLimb_Test`, a constant grey.
  - `SKM_Techlimb_Shield_Energy`, shown only while blocking. Not taken.
  - Niagara.

  The C++ root `Mesh` holds nothing; every form's `Mesh` is null.

**The asset: the game's placement baked into the points.**
- `export_techlimb_from_unreal.py` (uelink) writes `sources/armor/`:
  - the FBX;
  - `techlimb_ue.json`: the vertices in mesh, bone and component space, computed by Unreal itself
    (`MathLibrary.transform_location`, `AnimPoseExtensions.get_ref_bone_pose(..., WORLD)`,
    `ProceduralMeshLibrary.get_section_from_static_mesh`, components read through `SubobjectDataSubsystem`).
- `make_techlimb_asset.py` measures the maps (`ue_maya_axes.py`, numpy):
  - Unreal component space → Maya is (x, z, y), over 82 deforming bones to 0.073 cm (Manny's own calf);
  - Unreal's `lowerarm_l` axes → Maya's are diag(1, −1, 1);
  - the imported FBX's points are a signed permutation of Unreal's mesh space, to 2e-6 cm.
- It writes `assets/Armor/Tech_Limb.fbx` (`TechLimbMesh`, 48.7 KB) with the points in Manny's `lowerarm_l`
  axes. The similarity was fitted at scale 1.176471 and frozen, so the normals turn with the points. Read back:
  identity, on Unreal's place to 6e-6 cm.
- Equipped, the plate stands at identity in its space and its channels read 0 where the game puts it: the
  weapons' «без офсетов» rule.

**In the scene**:
- `maya_scenesetup/armor.py`. A piece hangs in an **armor space** (`lowerarm_l_armorSpace`, marked
  `mayaArmorSpace`): a transform parent-constrained to the bone with no offset, in an `ArmorSpaces` group under
  the rig's group (at world level beside a bare skeleton). It is never in the skeleton, so the export stays bones
  only and a retarget moves it with the bone.
- `weaponspace`'s machinery is generic over its markers since: `marked_space_of`, `ensure_marked_space`,
  `prune_marked`, `owner_for`, `bone_of`. The weapon API kept its names, and neither kind finds the other's space.
- A piece carries `mayaArmor` (its row's key) and `mayaArmorSlot`. `slot_plan` (pure): an Equip takes off what
  its slot holds, and the same piece again is replaced.
- It wears the next free palette colour (the Colour card repaints it; a textured row would wear its image).
  What follows the import runs unrecorded (trap 115).
- A selected piece names its character (`skeleton.current_root` → `armor.bone_for`).

**The catalog**: `catalog.Armor(key, label, path, bone, slot, texture)` and `ARMOR`, one row:
`Tech_Limb` on `lowerarm_l`, slot `left_forearm`. A future piece of armor or clothing is a row, plus its icon
(`make_armor_icons.py` → `assets/armor_icons/<key>.png`; a test pins one per row). Its points must already be in
its bone's axes at its place.

**The Armor card**:
- `maya_scenesetup/armorpanel.py`, the Scene group's last card. Connections and Shared are each pinned right
  after their neighbour by their own tests.
- It holds the subtitle, the tiles, **Equip** (primary, `shield`) + **Unequip** (danger), and the line.
- The tiles are `maya_armorgrid.py` (Qt, a payload row), laid over the `mayaSceneSetupArmorTiles` placeholder
  with the portraits' Keeper:
  - a click picks (`mayaSceneSetup_armor`);
  - a worn row carries a green «equipped» pill;
  - the right button offers Open scene;
  - no drag.
- Without Qt, a dropdown stands in.
- The pills follow the selection through a `SelectionChanged` scriptJob parented to the line. One refresh
  resolves the character once.
- The hotkey row is `window.armor`.

**Proof**:
- `verify_armor.py` **14/14 standalone**:
  - on Manny, every plate vertex where Unreal puts it to 1.1e-4 cm (the map re-derived from the rig's own bones);
  - channels 0, the space in `Manny_Rig:Group|ArmorSpaces`;
  - the Creep and the Orc D at identity on their own `lowerarm_l`;
  - a second Equip replacing;
  - LongSword_Attack_Right_Heavy_3P retargeted through the button: the piece on the bone to 4e-6 over 208 cm;
  - the export 93 joints, 0 meshes;
  - a bare skeleton's space at world level;
  - Unequip leaving nothing;
  - the others unmoved.
- A disposable GUI Maya (port 7031, the plugin from a `git archive` of HEAD): the tile clicked, then Equip and
  Unequip pressed through Qt (the pill on and off, nothing left, a second Unequip «does not wear»). Pictures:
  `docs/superpowers/plans/armor_card.png`, `armor_techlimb_on_manny.png`.
- 3434 unit tests.

152. **Atone's `SK_Mannequin_proto` and our Manny agree on every deforming bone and NOT on the helpers**:
     `weapon_r` 5.7 cm, `camera_root` 4.0, `weapon_l` 2.4, `camera_bone` 1.0 apart. A UE↔Maya axis fit over
     every shared bone read a 5.7 cm residual and looked like a wrong axis map. Fit over the deforming bones.
153. **A hub card's place can be pinned by ANOTHER feature's test**: `test_scenesetup_connections` pins
     Connections right after Weapons, `test_share` Shared right after Connections. A new card inserted between
     them fails both; the Scene group's end is free.
