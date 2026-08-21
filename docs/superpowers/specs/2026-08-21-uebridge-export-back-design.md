# UE bridge — export back to the uasset (the reverse bridge) — design

2026-08-21. Phase 2 of the Perforce integration — the «обратный мост» the
import-direction spec (2026-08-21-uebridge-perforce-design.md) left out of
scope. Two decisions below were answered by the user in brainstorming; the
user then left for the day with «делай все шаги до самого финала», so every
other decision is mine, made on the recorded reasoning and awaiting their
review at the end.

## What this is

Three additions to the UE Animation Bridge:

1. **A checkouts window** listing the AnimSequence uassets the animator has
   checked out — only AnimSequences, never the whole depot's uassets — each
   row saying whether its source FBX exists.
2. **Checkout and Revert from inside the bridge** — take a selected animation
   on checkout without leaving Maya, revert one that should not have been.
3. **Export back**: press Export, pick a checked-out uasset, and the scene's
   `root` hierarchy goes to the working FBX in SourceArt and the uasset is
   reimported from it in the running editor. With nothing checked out, Export
   degrades to a plain "save FBX as..." export.

The user's framing, verbatim where it matters:

- «У нас не должно быть такой ситуации что скрипт видит uasset на чекауте в
  перфорсе а fbx в сорс каталоге нету. source fbx — прокладка через которую
  мы работаем.» The FBX is the intermediary; a checked-out uasset without its
  FBX is an invariant violation, not a display problem.
- «мы должны нашу иирархию root отправить сперва в fbx потом
  переимпортировать сам uasset» — export is FBX first, reimport second.
- «Давай сразу будем открывать нашу иирархию для экспорта fbx» — the export
  selects the root hierarchy itself; the animator never hand-picks nodes.

## Decisions

### The invariant is enforced at checkout time (the user's pick)

Checkout through the bridge leaves the pair complete, always:

- FBX on disk → nothing to create.
- FBX in the depot but never synced → `p4 sync` (the existing
  `vcs.checkout` retry already knows this move).
- FBX nowhere → **the bridge exports it from the editor right away** into
  the conventional SourceArt location (the same `choose_target` machinery
  the import direction uses: name search disk+depot, remembered folder,
  conventional folder, ask-and-remember). The прокладка therefore exists
  from the moment the uasset is opened, holding the animation the uasset
  had before the animator started changing it — a baseline, not garbage.

A uasset checked out **outside** the bridge (P4V) can still show up with no
FBX; the row is flagged `fbx: missing` and the first Export heals it (the
export writes the file and `p4 add`s it).

### uasset and FBX travel as a pair in Perforce (the user's pick)

- **Checkout** opens both: `p4 edit` the uasset, `p4 edit` the FBX (or
  `p4 add` when it is untracked — including the one just created by the
  editor export). One changelist, one submit from P4V, source and asset
  never drift apart in the depot.
- **Revert** reverts both, behind one confirm dialog that names the two
  files — revert discards work, so it is the one destructive button in the
  window. `p4 revert` of an `add` abandons the add and leaves the file on
  disk (p4's own behaviour; the file staying is correct — the invariant
  wants it there).
- The phase-1 rule «no p4 add» was explicitly «versioning is the export
  phase's job». This is the export phase; `p4 add` is now in scope. The
  IMPORT path keeps its phase-1 behaviour unchanged (no add on import).

### The checkouts listing

`p4 -ztag fstat -Ro <ContentDir>/....uasset` — one call, answering every
file opened in the current workspace under the project's Content dir, with
`clientFile` for free (`p4 opened` answers depot paths and would need a
second `where` call per file). Rows are matched to AnimSequences against
the bridge's cached listing: `clientFile` → package path
(`/Game/<rel-without-ext>`), case-insensitive on Windows, and any opened
uasset whose package is not a known AnimSequence is dropped — «нас не
интересуют все uassets». An empty records cache cannot classify anything,
so the window says "press Refresh first" rather than guessing by filename.

The Content dir comes from the editor: the list script now also writes
`content_dir` (`unreal.Paths.project_content_dir()`, made absolute) into
its reply and the cache. An old cache without it falls back to discovery —
the pong already carries `project_root` — and failing that, the window asks
for a Refresh. Nothing hardcodes the project's location.

Each row also reports the FBX state, computed with the existing name
search: `ok` (on disk), `depot` (exists at head, never synced), `missing`
(nowhere). The p4 cost is one fstat per row over a handful of rows.

### Export flow, in order

Precondition: a checkout row is selected. Then:

1. **Resolve the skeleton** — `animimport.choose_target_root(skeleton_roots(),
   selected_roots())`, the exact rule the import merge uses: selection wins,
   else the only non-namespaced skeleton, else the one named `root`.
   Undecidable → refusal on the status line, nothing touched.
2. **Resolve the working FBX** for that uasset — `choose_target`, same as
   import (disk+depot by name, remembered folder, convention, ask).
3. **Export to a temp FBX** (never straight onto the working file — same
   rule and reason as the import direction: a failed export must not
   destroy the previous working file).
4. **p4 on the FBX** — `plan_for` its fstat: tracked-free → edit (with the
   sync retry), untracked → add *after* the place (p4 add wants the file on
   disk; a brand-new conventional path has no file until the copy). Opened
   by others → the existing modal. p4 dead → the existing continue-locally
   modal. No depot state is mutated before the export succeeded.
5. **Place** — `vcs.place(temp, target)`.
6. **Reimport in the editor** — a new UE-side script: `load_asset(package)`
   (guarded — trap 24), `ReimportSubsystem.set_reimport_paths(asset,
   [fbx])`, `reimport(asset, ask_new_file=False, load_new_file=False,
   preferred_file=fbx)`, then `EditorAssetLibrary.save_asset(package,
   only_if_is_dirty=False)`. `ask_new_file=False` plus an explicit path is
   what keeps the editor from raising a file dialog nobody can click
   (trap 23/24 family). The reply reports ok/saved plus the reimported
   frame count, read back the way the export script reads it.
7. Status line: bones exported, range, the FBX path suffix (existing
   wording), and the reimport verdict.

The uasset itself is already writable — it is checked out; that is what the
window lists. The reimport does not touch its p4 state.

With **no checkouts**, Export opens a save dialog (seeded at the source
root) and does steps 1 and 3 straight to the picked path — no p4, no
reimport («если файлов на чекауте нету ... пользователь укажет путь для
сохранения fbx»).

### The Maya-side FBX export

New module `animexport.py`, the export twin of `animimport.py`:

- **Selection is automatic**: the resolved skeleton root is selected
  (children ride along in an FBX selection export) and the previous
  selection is restored after. The animator never picks nodes — the user's
  closing instruction.
- **Bake on export**: `FBXExportBakeComplexAnimation` with an explicit
  range. The skeleton in this project is usually rigged (constraints from
  OverRig knots, twist DG networks); bake-on-export samples the driven
  channels into curves inside the FBX without touching the scene — no
  Bake+Delete demanded of the animator, no undo chunk needed, nothing to
  restore. `FBXExportConstraints -v false` and
  `FBXExportInputConnections -v false` keep the rig's nodes out of the
  file; skins, shapes, cameras and lights are off — bones only, which is
  what a UE animation reimport reads.
- **Range = animation range ∪ playback range** (`ast/aet ∪ min/max`), and
  the status line warns when the hierarchy carries keys outside it. Trap 38
  is the reason the range is a union rather than the visible slider alone:
  an export that silently narrows to a zoomed-in timeline trims the clip.
  Keys outside the union are the animator's own business — warned, not
  silently included, because a stray key at frame -200 must not stretch
  the clip.
- **Settings are reset then set explicitly per export** (`FBXResetExport`
  first, every flag guarded like `_apply_import_options`). Nothing is
  inherited from whatever ran before — trap 33's lesson from the import
  side. No restore-after: no tool in this session reads FBX *export*
  settings (root_offset_batch_tool runs in its own mayapy), and resetting
  before each use is the defence.
- The scene's frame rate is reported against the uasset's, never changed —
  same rule as import. A mismatch warns that UE will resample.

### UI shape

Approaches considered: (A) a popup checkouts window opened by Export, plus
a Checkout button in the main window; (B) a second list embedded in the
main window; (C) no checkout/revert in the bridge, P4V only. (B) loses to
the user's explicit «всплывает окошко», (C) to the explicit ask for
in-bridge checkout/revert. (A) is built:

- **Main window** grows two buttons: `Checkout` (acts on the selected
  animation row — that list is where every animation lives, so it is the
  natural place to pick what to open) and `Export`, which opens the
  checkouts window — or the save dialog when nothing is checked out.
- **Checkouts window** (`ueBridgeCheckouts`, plain `cmds`, deleted and
  rebuilt on open like the main window): a fixed-width scroll list of rows
  (name, folder tail, p4 action, fbx state), buttons `Export`, `Revert`,
  `Refresh`, and a status line of its own. Every callback goes through the
  same `_run` pattern — a failure lands on the status line, not the Script
  Editor (trap 20).
- Double-click on a row = Export, mirroring the main window's
  double-click-to-import.

The checkouts machinery does not require the phase-1 checkbox to be ON:
the checkbox governs where *imports* land; checkout/export inherently need
the source root and p4, so they use the same saved root (asking for it
once if unset) regardless of the checkbox. The root and dir-map optionVars
are shared with phase 1, as that spec planned.

## Architecture

| Module | Change |
|---|---|
| `vcs.py` | Additions, stdlib only: `opened_records(pattern, run)` (fstat -Ro, record-split parse, failure classified), `package_of(client_file, content_dir)` (pure), `revert(path, run)`, `add(path, run)`, `open_action(fields)` (pure: edit / add / already-open / others). Existing `checkout`, `plan_for`, `choose_target`, `place` are reused untouched. |
| `uescripts.py` | `reimport_script(out_path, package, fbx_path)`; `list_script` reply gains `content_dir`. |
| `records.py` | Unchanged (AnimRecord already carries name+package; row helpers reused). |
| `animexport.py` | **New**: skeleton resolution re-exported from `animimport`, export range policy (pure), the FBX export itself, selection save/restore, status wording (pure). |
| `checkouts.py` | **New**: the checkouts window and the orchestration — the pair checkout (uasset+fbx, including the ensure-fbx editor export), revert-pair with confirm, export-and-reimport, row building (pure helpers separated for tests). Imports `window` for the shared root/dialog/temp helpers. |
| `window.py` | Two buttons; `content_dir` through cache/state; `Checkout` and `Export` handlers delegating to `checkouts` (imported lazily in the callbacks to keep the import graph acyclic). |
| `animimport.py` | Unchanged. |

`vcs.py`, `uescripts.py`, `records.py` stay in the stdlib-purity subprocess
test. Every dialog stays injectable (`asks=` dicts), for the same
bridge-safety reason as phase 1: a modal over the command port blocks Maya.

## Testing

- **Unit (mayapy, no Maya):** fstat -Ro fixtures (opened-for-edit,
  opened-for-add, empty answer) through `opened_records`; `package_of`
  (case, separators, outside-Content, ext stripping); `open_action` over
  the fstat states; revert/add output classification; `reimport_script`
  interpolation (paths with backslashes, marker, guarded load); list-script
  `content_dir` presence; export range union + outside-keys warning
  wording; checkout/export/revert status lines; row formatting; the
  fake-cmds pattern for window-side pure helpers.
- **Live (`docs/superpowers/plans/verify_uebridge_export.py`):** sandbox
  first — a throwaway keyed skeleton exported to a scratchpad FBX and
  re-read (joint and key counts prove the exporter settings); the real p4
  listing parsed read-only; content-dir resolution against the running
  editor; the reimport gate on a **duplicated** sandbox uasset
  (`EditorAssetLibrary.duplicate_asset` into a `/Game/.../__bridge_verify`
  slot, reimported from our exported FBX, then deleted) so no real asset
  and no depot state is touched; the pair checkout+revert on the Longsword
  files, skipped unless both are free, reverted immediately — the phase-1
  pattern. The script must run without the animator present: every dialog
  injected, no modal, no mutation of their scene beyond the sandbox nodes
  it deletes.

## Out of scope

Submitting from Maya (`p4 submit`, changelist descriptions) — the animator
submits the pair from P4V. Changelist UI. Exporting anything but the root
skeleton hierarchy (no morphs, no camera clips). Matching the scene
skeleton against the uasset's skeleton tag before reimport — the reimport
matches by bone name exactly as the import merge does, and refusing on a
tag mismatch would block legitimate retargets; UE's own reimport warnings
remain visible in the editor.

## Addendum, same day: what the live run taught about the reimport

`verify_uebridge_export.py` ran green (0 of 18 gates failed) only after the
reimport mechanism was rewritten twice, each time against a measured fact
from the running editor (UE 5.8, the Atone build):

- **There is no `ReimportSubsystem` in this build's Python API** —
  `hasattr(unreal, "ReimportSubsystem")` is False (probed via dir(unreal)).
  The design's original `set_reimport_paths` + `reimport` plan cannot run at
  all. The replacement is an automated **`AssetImportTask` over the existing
  package** (`replace_existing`, `destination_name` = the asset,
  `FbxImportUI` with the skeleton read from the asset itself,
  `FBXIT_ANIMATION`). Consequence, documented in the script's docstring: a
  replace-import rebuilds the asset from the fbx, so curves the fbx does not
  carry (the trap-40 family: Pose_*, MoveData_*) do not survive it — the
  same contract as reimporting by hand.
- **Interchange owns .fbx on this build and swallows a bones-only file.**
  The editor log says `There was nothing to import from the provided source
  data using the chosen pipeline options` and the task imports nothing —
  legacy `FbxImportUI` options are ignored entirely by the Interchange
  pipeline. The fix: flip `Interchange.FeatureFlags.Import.FBX` to 0 around
  `import_asset_tasks` (read the previous value, restore in a finally) so
  the legacy fbx animation importer handles the task. Measured: the same
  task that imported nothing under Interchange lands frames 2 → 60 on the
  legacy path.
- **Success cannot be read from `imported_object_paths` or `result`** — the
  first stays empty on this build even for a successful import, the second
  answers with a deprecation warning. `task.get_objects()` is what reports
  the imported AnimSequence.
- **The editor runs its own Perforce integration**: saving a new asset
  fires `p4 add` from inside UE, deleting it fires `p4 revert -w`. For the
  real flow this is harmless (the exported uasset is already checked out),
  but any sandbox asset the verify creates makes transient p4 noise, and
  the editor log (`<project>/Saved/Logs/<name>.log`, readable shared while
  the editor runs) is the tool that made all of this diagnosable.
