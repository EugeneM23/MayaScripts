# UE bridge — Perforce integration for imports — design

2026-08-21. Approved by the user in brainstorming; every decision below that
names the user is theirs, made with the trade-off on the table.

## What this is

A **Connect to version control** checkbox in the UE Animation Bridge window.
Unchecked, the bridge works exactly as today: the editor exports to a temp
folder and Maya imports from there. Checked, the exported FBX lands in the
**working directory** — the SourceArt tree that mirrors the project's uasset
hierarchy — with Perforce checkout handling, and Maya imports *that* file, so
the scene honestly references the working file rather than a temp copy.

The user's framing: pulling animation straight out of the engine is «не совсем
правильно» — the working FBX files in SourceArt are the real sources, and the
bridge should keep them, not bypass them. This phase covers the **import
direction only**. Phase 2 — «обратный мост», Maya → Perforce submit and
Perforce → Unreal — is explicitly out of scope, and so is touching the uasset
(an FBX export does not modify the asset, so there is nothing to check out on
the Content side).

## Measured facts the design rests on

All measured 2026-08-21 on the user's machine, through the real depot:

- p4 CLI installed (`C:\Program Files\Perforce\p4.exe`), configured via
  `p4 set`: user `yevhen.merezhko`, client `yevhen.merezhko_ASD`, root
  `C:\!!!Work\Perforce`, stream `//atone/main`, `P4CHARSET=utf8`, SSL server,
  SSO auth optional. `p4 info` answers — the connection is live.
- **SourceArt is its own depot.** The client view *excludes*
  `//atone/main/SourceArt/...` and maps `//atone-art/...` (a local, non-stream
  depot: "Art Sources for Atone Game") onto `<root>/SourceArt/...`. The
  uassets live in the stream: `//atone/main/Atone/Content/...`, filetype
  `binary+l` (exclusive lock).
- **The example FBX files are not in the depot at all.** The three
  `AS_Unarmed_*.fbx` under
  `SourceArt/Prototype/Animation/Exports/PlayerCharacter/Unarmed/` exist on
  disk, writable, and `p4 fstat` answers "no such file(s)" — nobody has
  submitted them. Their uasset twins in the depot are at revision 2.
- **The hierarchies genuinely diverge.** uasset dir
  `Content/Prototype/Animation/PlayerCharacter/Unarmed/1P/`, FBX dir
  `SourceArt/Prototype/Animation/Exports/PlayerCharacter/Unarmed/` — the
  uasset path carries a trailing `1P`, the FBX path carries `Exports` after
  `Animation`. The file **names** match exactly
  (`AS_Unarmed_Idle_1P.fbx` ↔ `AS_Unarmed_Idle_1P.uasset`). The user confirms
  the project does not always follow its own convention («сейчас так бывает
  не всегда»).
- **`p4 -ztag fstat` output shapes** (captured, used as parser fixtures):
  a tracked unopened file answers `... depotFile`, `... clientFile`,
  `... headRev`, `... haveRev` and **no** `action`/`otherOpen`; a file opened
  by others answers `... ... otherOpen0 user@client`, `... ... otherAction0
  edit`, …, `... ... otherOpen 3` — note the **double** `... ...` prefix on
  the other-open block, a parser matching only `... field value` misses it.
- **"no such file(s)" goes to stderr with exit code 0.** p4's exit code does
  not separate "not in depot" from success, so classification is by text, and
  "no such file(s)" is a *normal answer* (untracked), never an error.

## Decisions

### The working FBX is found by NAME, not by path (the user's pick)

On Import with the checkbox on, the bridge searches the source root
recursively for `<AssetName>.fbx`, case-insensitively (Windows). The measured
hierarchy divergence is why: a path convention would miss files the project
has already misplaced, while the names match exactly today. Outcomes:

- **Exactly one hit** — that is the target.
- **Several hits** — if one of them sits in the folder remembered for this
  uasset's folder (see the dir map below), it wins silently; otherwise a
  file-picker dialog seeded at the source root, and cancel aborts the import.
- **No hits — a new animation** — the conventional folder is derived from the
  uasset's package path (the user's pick: convention first, ask only when it
  fails): the path relative to `/Game`, with **`Exports` inserted after the
  `Animation` segment** (not doubled if already there) and a **trailing
  `1P`/`3P` segment dropped**. If that folder exists on disk, the file goes
  there silently. If not, a folder-picker dialog, and the choice is
  **remembered per uasset folder** in an optionVar JSON map
  (`ueBridgeVcsDirMap`), so the same question is never asked twice for one
  folder. Cancel aborts the import.

The search walks the disk fresh on every Import press — no cache to go stale;
the tree is local and the walk is subsecond at this project's size.

### First activation asks for the source project (the user's addition)

Ticking the checkbox with no remembered root — or with a remembered root that
no longer exists on disk — opens a folder dialog («где наш source проект»).
Cancel flips the checkbox back off. The root persists in `ueBridgeVcsRoot`,
the checkbox state in `ueBridgeVcs`, and a `...` button next to the checkbox
re-opens the dialog to change the root later without touching optionVars by
hand.

### No `p4 add` (the user's pick)

Files the depot does not know — brand new, or on disk but never submitted,
which is what all three example files are today — are just written to disk.
Opening them for add is phase 2's job («выгрузка из Маи в перфорс»). This
phase's only depot mutation is `p4 edit` on files the depot already tracks.

### The Perforce decision table

`p4 -ztag fstat -Or <target>` runs with the target's directory as cwd (so
P4CONFIG setups would also work), output decoded as utf-8 (P4CHARSET is
utf8 — user names may be non-ASCII), and the console window suppressed
(`CREATE_NO_WINDOW` — without it every p4 call from Maya flashes a black
console). Then:

| fstat says | Action |
|---|---|
| Not in depot ("no such file(s)") | No p4 at all; clear read-only if set, overwrite |
| Tracked, opened by nobody | `p4 edit`; on "file(s) not on client" → `p4 sync` that file, retry edit once |
| Opened by **me** (`action` present) | Nothing — already mine, overwrite; others also on it are named in the status line, not a modal |
| Opened by **others only** (`otherOpen*`) | Modal: "Checked out by <user@client>, …" → **Cancel** (abort import) / **Overwrite locally** (clear read-only, overwrite, no p4) |
| p4 itself failed (no exe, no network, session expired) | Modal with the classified reason ("session expired — log in via P4V") → **Cancel** / **Continue locally** (the user's pick — the FBX still lands in the right folder, just without checkout) |

The edit-then-sync-retry order is deliberate: pre-classifying "do we need a
sync" needs three-way local-file state analysis, while letting `p4 edit`
answer and retrying once after a sync is self-healing and covers the one real
case (tracked file never synced locally).

### Order of operations, and why

**Resolve target (dialogs about paths) → export to temp → p4 (fstat, dialogs,
edit) → copy temp onto target → Maya imports the target.**

Two reasons the export never writes the working file directly: the UE export
script deletes its destination before writing, so a failed export straight
onto the working file would leave *nothing* there; and no depot state is
mutated until a new file actually exists to place — a cancelled or failed
export leaves no checkout taken for nothing. The copy clears the target's
read-only bit when the local-overwrite branch chose to keep p4 out of it.

Maya then imports **the target path**, not the temp file — same bytes, but
the scene's history points at the working file.

The status line grows a suffix naming what happened:
`| fbx → SourceArt\...\Unarmed (checked out)` / `(overwritten locally)` /
`(not in depot)` / `(new file)`.

## Architecture

| Module | Change |
|---|---|
| `maya_uebridge/vcs.py` | **New, stdlib only** (subprocess/os/json/re). Pure: ztag parsing (both `...` and `... ...` prefixes), p4 failure classification by stderr text, the decision table, the path convention, the name search, the dir-map lookup, status-suffix wording. Thin: a p4 runner (subprocess) and an orchestrator `resolve_target`/`prepare_target` taking the runner **and every dialog as injectable callables** — the pure logic never imports Maya and never raises a modal itself. |
| `maya_uebridge/window.py` | The checkbox row (checkbox + root label + `...` button), the optionVars, the real dialogs (`cmds.confirmDialog`, `cmds.fileDialog2`), and wiring `import_selected` through the orchestrator when the checkbox is on. |
| `maya_uebridge/animimport.py` | Unchanged — `import_clip` already takes a path. |

The injectable dialogs are not a testing nicety but a bridge-safety rule: a
modal dialog raised during a command-port run blocks Maya's idle queue
(working-notes note 6), so the live verify script must be able to drive every
branch with canned answers.

`vcs.py` joins the stdlib-purity subprocess test that already guards
`records`/`uescripts`/`uelink`.

## Testing

- **Unit (mayapy, no Maya session):** the ztag parser on the captured real
  outputs (tracked-unopened, opened-by-three-others, no-such-file); the
  failure classifier on real p4 error texts; the decision table over every
  row above; the path convention (`1P`/`3P` dropped, `Exports` inserted, not
  doubled, non-`Animation` paths passed through, packages without `/Game`);
  the name search on a temp tree (unique, ambiguous, case-insensitive, dir-map
  preference); the status suffixes; window-side pure helpers with the repo's
  fake-cmds pattern.
- **Live (`docs/superpowers/plans/verify_uebridge_vcs.py`, through the
  bridge):** runs the real orchestrator with a **sandbox source root** built
  in the scratchpad — never the real SourceArt, so the animator's working
  files are not overwritten by a verification run — with injected dialog
  answers. Gates: found-by-name overwrite, ambiguity resolution via injected
  pick, new-file conventional placement, new-file remembered-folder placement,
  real `p4 fstat` against a known tracked file (read-only) parsing into the
  expected plan, untracked plan for a sandbox file, and a full import into the
  scene from the placed target. **The depot is never mutated** — the `p4 edit`
  branch is proved by unit tests over the captured outputs; nothing in the
  verify script opens, adds or submits anything.
- If no UE editor is up when the verify runs, the export step is simulated by
  copying a known FBX into the temp slot — the placement, p4 and import gates
  do not need the editor.

## Addendum, same day: the depot is part of the search, and the convention keeps 1P/3P

Paid for live with `AS_Longsword_Attack_Back_Combo_2_Hold_1_3P`: the import
landed the fbx «в папку на уровень выше» — one level above where it belongs.
Two causes, measured against the real depot:

- **The "drop 1P/3P" rule was wrong.** It was inferred from the local Unarmed
  files, which are NOT in the depot and do not follow the project convention.
  The depot's canonical layout keeps the view folder: uasset
  `Content/Prototype/Animation/PlayerCharacter/Weapons/Longsword/3P/AS_*.uasset`
  ↔ fbx `//atone-art/Prototype/Animation/Exports/PlayerCharacter/Weapons/`
  `Longsword/3P/AS_*.fbx`. So the convention is a **pure mirror**: the path
  relative to `/Game`, with `Exports` inserted after `Animation` (not
  doubled) and nothing dropped. The old rule pointed at `.../Longsword`,
  which exists on disk, so the file was placed there silently.
- **The search must cover the depot, not only the disk** (the user's
  requirement: «посмотреть не только локально на диске а еще и в депоте;
  если нету на диске а есть в депоте то загрузить ее взять на чекаут и
  импортировать»). The Longsword fbx exists in the depot at head but was
  never synced — a disk-only walk cannot see it, so the file read as "new"
  and went to the (wrongly derived) conventional folder.

The mechanics, all measured: `p4 -ztag where <root>/...` answers one record
per view line, blank-line separated, exclusions carrying an `unmap` field —
the effective depot pattern is the **last record without `unmap`**
(`//atone-art/...` for this root). `p4 -ztag fstat -Or
<pattern>/.../<name>.fbx` finds the file wherever it is under the root and
answers **both `depotFile` and `clientFile` even for a file never synced**
(no `haveRev` line then), so the mapped local path comes for free. Records
whose `headAction` is a delete are dropped. The multi-record output needs a
record-splitting parser (`parse_ztag_records`); the flat `parse_ztag` merges
records and is kept for single-file calls.

`choose_target` merges disk and depot hits (deduplicated case-insensitively
by local path; the depot search is skipped when no runner is passed, and a
p4 failure during discovery degrades silently to disk-only — `prepare_target`
will surface the failure with its dialog anyway). A depot-only hit needs no
new checkout logic: `checkout` already answers "not on client" with one
`p4 sync` and a retry, which is exactly the sync-then-edit the user asked
for. The ambiguity dialog becomes a numbered `confirmDialog` — a file picker
cannot select a depot-only path that does not exist on disk yet.

The "new file" status tag is now derived from the *depot* answer, not the
disk: a synced-on-demand file did not exist locally but is anything but new
(`is_new and note == "not in depot"` at the call site).

## Out of scope (phase 2 and later)

Submitting from Maya (`p4 add`/`p4 submit`, changelist description policy),
pushing updated FBX into Unreal (reimport), checking out uassets, and any
UI for changelists. The dir map and the source-root optionVar are designed to
be reused by that phase.
