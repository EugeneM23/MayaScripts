# UE → Maya animation bridge — design

**Date:** 2026-08-16
**Status:** implemented and live-verified — 25/25 for the listing and export
path, 25/25 for the merge onto a scene skeleton, 438 unit tests. Traps found
on the way are recorded in `CLAUDE.md` as 22-28.

## The ask

A window in Maya listing every `AnimSequence` in the Unreal project the animator
has open, searchable by name, with an Import button that brings the selected
animation into the Maya scene as a skeleton with keys.

Explicitly out of scope, by the user's call: what the animation is used for
afterwards. It lands in the scene as its own skeleton and the tool's job ends
there.

## Why `.uasset` is not read directly

The obvious reading of the request — parse the `uasset` in Maya — is not
buildable. The format is closed, versioned against the engine build, and
animation curves inside it are stored under UE's compression codecs. Any parser
would be a multi-month project that breaks on the next engine upgrade. The
engine itself is the only thing that can read the file, so the engine does the
reading and hands us FBX.

## The machine this runs on

Measured 2026-08-16, not assumed:

- Engine is a **source build** at `C:\!!!Work\Perforce\Engine`. The project
  `Atone` lives inside that tree (`C:\!!!Work\Perforce\Atone\Atone.uproject`),
  which is why its `EngineAssociation` is the zero GUID.
- `remote_execution.py` is present at the stock path
  `Engine/Plugins/Experimental/PythonScriptPlugin/Content/Python/`.
- `Atone.uproject` **already enables** `PythonScriptPlugin` and
  `EditorScriptingUtilities`. Nothing has to be turned on project-wide.
- `DefaultEngine.ini` already carries a `[/Script/PythonScriptPlugin.PythonScriptPluginSettings]`
  section with `AdditionalPaths` — Python is in live use for automation tests.
- `bRemoteExecution` is **not** set anywhere, and UDP 6766 is unbound: remote
  execution is off and needs enabling once.

## Transport: Python Remote Execution

Epic's own mechanism — UDP multicast on `239.0.0.1:6766` to discover a running
editor, then a TCP command connection. It is the exact counterpart of the
`commandPort :7001` this repo already drives Maya with.

Two alternatives were weighed and rejected:

- **A file drop-box** (`init_unreal.py` in the project polling a request folder
  on tick) needs a file committed inside a Perforce-managed project — either
  pushed onto the whole team or lost at the next sync. Kept in reserve: if the
  corporate firewall eats multicast, only `uelink.py` changes.
- **A pre-exported FBX library** severs the live connection entirely; the list
  goes stale and the disk fills up. Only a fallback if both others fail.

Decisions inside the transport:

- **`remote_execution.py` is loaded from the engine, never vendored.** It is
  Epic's code under the UE EULA, and a copy in this repo would drift from the
  engine build it has to speak to. It loads through `importlib` from an explicit
  file path, without touching `sys.path`.
- **Engine root discovery** in order: explicit override → registry
  `HKCU\Software\Epic Games\Unreal Engine\Builds` → `C:\Program Files\Epic Games\UE_*`.
  On this machine the registry hits `C:/!!!Work/Perforce` first.
- **The connection is opened per operation and closed after.** Refresh and
  Import are button presses; a second of discovery is invisible, and a
  short-lived connection removes every stale-socket failure that follows an
  editor restart.
- **Results never travel through the socket.** The UE-side script writes JSON to
  a temp file and prints only the path. Both processes are on one machine, and a
  project with thousands of animations would otherwise push a large payload
  through the protocol's output channel. This mirrors the output-file trick the
  Maya bridge already uses.

## The UE side

**Listing** queries the Asset Registry with an `AnimSequence` filter. Name, path,
skeleton and frame count come back **from asset tags, without loading a single
asset**, which is what keeps a large project listable in seconds.

`is_loading_assets()` is checked first. Immediately after the editor starts the
registry is still scanning, and without that check a partial list reads as "this
project has few animations" — a silent wrong answer, the worst kind.

**Export** drives `AssetExportTask` with `AnimSequenceExporterFBX` into a temp
folder: bones only, no preview mesh. `automated=True` is mandatory — without it
UE raises a modal dialog that nobody can click, and the editor hangs. That is
the same failure class as animbot's `snapshotMirrorSettings_click()` freezing
Maya from a command-port call.

Exact field names on `FbxExportOption` are confirmed against the live 5.8 editor
during the spike rather than written from memory.

## The Maya side

Two modes, chosen by a radio button.

**Onto the skeleton already in the scene** — the default, and what the tool is
for. FBX exclusive merge matches bone names against what is there and writes
the animation onto it, creating nothing. The clip must not go into a namespace:
a namespace is exactly what stops the names matching. The target is chosen
rather than assumed — the selection wins, else the only skeleton, else the one
named `root`; two plausible skeletons with no hint is refused, since guessing
animates the wrong character in silence. The target's existing animation is
cleared first, because the importer rewrites curves in place and otherwise
nothing about the result can be measured (see trap 27).

**As a new skeleton** — the original behaviour, imported into a **namespace
derived from the asset name**, uniquified if taken. Nothing already in the
scene is touched and no bone name collides with a character already standing
there. Useful as a reference beside the working character, and it is what the
merge is verified against.

**Scene frame rate is never changed silently.** A UE clip is almost certainly 30
fps and the scene may not be; on a mismatch the import still proceeds and the
status line says so plainly. Rewriting the frame rate of a scene the animator is
working in would be the most destructive thing this tool could do — and per
`CLAUDE.md` the user is working in the scene while the tool runs.

A "set timeline to clip range" checkbox defaults to on, because otherwise the
animation arrives and cannot be seen.

## The window

Pure `maya.cmds` UI — a scroll list and a text field need no Qt.

```
Project: Atone                    ● connected      [Refresh]
Search: [ jump____________________ ]
┌──────────────────────────────────────────────────────┐
│ A_Jump_Start        /Game/Characters/Manny/   45 fr  │
│ A_Jump_Loop         /Game/Characters/Manny/   30 fr  │
└──────────────────────────────────────────────────────┘
[x] set timeline to clip range          [   IMPORT   ]
status: ...
```

Search filters the **cache**, never the editor, so typing is instant. The cache
is written to disk, so the window opens with a browsable (if stale) list even
with the editor closed.

**Every error goes to the status line, never to the Script Editor.** Trap 20 in
`CLAUDE.md` was exactly this: an exception escaping a UI callback made a panel
look dead.

## Module layout

A package, `maya_uebridge/`, not a root-level single file. Root-level tools top
out near 430 lines with one dependency set; this has four, and separating the
pure parts from the Maya-touching parts is what makes it testable — the same
reasoning that justifies `maya_overrig/`.

| Module | Responsibility | May import |
|---|---|---|
| `uelink.py` | engine discovery, connection, running Python in the editor | **stdlib only** |
| `uescripts.py` | UE-side script text | **stdlib only** |
| `records.py` | record model, search, namespace naming, row text | **stdlib only** |
| `animimport.py` | FBX import into a namespace, timeline, fps policy | `maya.cmds` |
| `window.py` | the `cmds` window | `maya.cmds` |

The first three are testable with neither Maya nor Unreal running. The record
model was split out of `uescripts.py` during implementation so that module
holds only UE source text.

## Errors

| Condition | What the user sees |
|---|---|
| No editor answers discovery | Whether Remote Execution is enabled, and that the editor needs a restart |
| Asset registry still scanning | Said plainly, instead of a short list |
| Export failed in UE | UE's own error text, verbatim |
| FBX plugin missing | Load attempted, failure reported |
| Clip fps ≠ scene fps | Warning; the import still happens |

## Not building

Maya → UE export, mesh and skin, other asset types, batch import.

## Verification

Unit tests (`tests/test_uebridge.py`, mayapy + unittest, no Maya session) cover
the pure halves: UE script generation with safely embedded paths, JSON reply
parsing, the search filter, namespace sanitisation, engine-root selection from a
candidate list.

The real proof is `docs/superpowers/plans/verify_uebridge.py`, run through the
bridge against the live editor: connect, list, compare the count against what UE
reports, export one named animation, import it, and assert the bones exist, the
keys exist, and the range matches what UE said. Unit tests in this project have
repeatedly passed while the scene was broken.

## Risks, as they actually resolved

- **`bRemoteExecution`** — no restart needed after all. The checkbox calls
  `SyncRemoteExecutionToSettings()` straight from `PostEditChangeProperty`
  (read in `PythonScriptPluginSettings.cpp`). It writes `DefaultEngine.ini`
  though, which is shared under Perforce, so personal persistence belongs in
  `Saved\Config\WindowsEditor\Engine.ini`.
- **Multicast** was never blocked on this machine; the editor binds
  `127.0.0.1:6766` and Epic's client binds the same by default.
- **The preview mesh** was not a problem: the exporter falls back to
  `FindCompatibleMesh()` and every asset tried exported cleanly.
- **`FbxExportOption` field names** — every field we set exists on 5.8; the
  script reports any it cannot set rather than failing.

Two risks that were not on the list turned out to be the real ones: the engine
root has to come from the running editor process rather than the registry,
and `cmds.file` imports FBX skeletons without their animation. Both are
recorded in `CLAUDE.md` (traps 22 and 26).
