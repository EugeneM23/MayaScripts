# Cascadeur bridge — skeletal animation between Unreal and Cascadeur, Shared send

Date: 2026-10-09. Status: design approved by the animator in conversation; awaiting written-spec review.

## Goal

A bridge window that lives **inside Cascadeur only**, built on the principle of the UE Connect card in
Animation Setup. v1 covers three things:

1. **Import** a skeletal animation from Unreal into Cascadeur (each clip in a new scene tab).
2. **Export to uasset**: the animation of the current Cascadeur scene goes back into an Unreal
   AnimSequence through the existing uasset road (replace import, same warnings as Maya).
3. **Send to Shared**: the animation as an FBX goes to the team through the Shared channel.

Maya is not involved in any part of v1. Mesh export, rigs, retargeting and Cascadeur's own rigs are out.

## Decisions taken

These were settled in the brainstorm or chosen here; the animator can overrule any of them.

- **Install (option B):** a standalone installer run inside Cascadeur's Python console. No Maya.
- **No MCP server, no port.** The bridge is a Cascadeur menu action (see Architecture). The script
  server's 30 s timeout and manual start do not apply.
- **Window is a PySide6 top-level window** created by the menu action, inside Cascadeur's process.
  Not modal, does not block the scene. Errors are shown with `QMessageBox`.
- **Export scope = the whole scene's skeleton.** The scene must hold exactly one skeleton (one root
  joint); otherwise the export is refused by name. A selection rule, as in Maya, is not built in v1.
- **Import = one new scene tab per clip**, named after the clip. Nothing in the current tab changes.
- **Export target** is the uasset the window last imported from into the current tab, shown and
  changeable in the window. Without one, the export is refused until a target is picked from the list.
- **Install folder:** `%USERPROFILE%\Documents\SkeldarAnim`. Separate from Maya's
  `<userAppDir>/scripts/SkeldarAnim`; the two can coexist.
- **Payload:** the `skeldar_cascadeur` package is added to `install.payload()` so `make_build.py` puts it
  in the release zip (the Cascadeur installer unpacks that zip). The Maya install copies it too, which is
  harmless.

## Architecture

### Where the code lives

`SkeldarAnim/skeldar_cascadeur/` — a package in the plugin folder. It imports `csc` only in the module
that talks to Cascadeur (`cascade_io.py`). Everything else is plain Python and is unit-tested outside
Cascadeur.

| Module | Responsibility | Imports |
|---|---|---|
| `bridge.py` | The menu action: `name()` = `SkeldarAnim.Bridge`, `description()`, `run(scene)` opens or raises the window. Discovered by Cascadeur's `python_actions_rule.get_actions` | `window` (lazy) |
| `window.py` | The PySide6 window: Unreal list, Connect status line, the three actions, status line | PySide6, the modules below |
| `cascade_io.py` | Cascadeur side: `new_tab_import(path, name)`, `export_skeleton(path)`, `current_range()`, `current_fps()`, `scene_skeletons()` | `csc`, `pycsc` (only here) |
| `unreal.py` | Unreal side with no Maya: list AnimSequences (`uelink.run_script` + `uescripts.list_script`), export a clip to a temp FBX (`uescripts.export_script`), reimport (`uescripts.reimport_script`), the reply reading | `maya_uebridge.uelink`, `maya_uebridge.uescripts`, `maya_uebridge.records` |
| `uasset_core.py` | Maya-free helpers taken out of `maya_uebridge/uassetexport.py`: read-only check and clear, staging path, the lost-curves message, the overwrite confirmation text | stdlib |
| `shared.py` | Zip the FBX, upload with `maya_sharenet.upload_any`, publish `sending`/`ready`/`failed` with `maya_sharerecords` | `maya_sharenet`, `maya_sharerecords` |
| `prefs.py` | The author name for Shared and the last export target, as JSON in `%APPDATA%\SkeldarAnim\cascadeur.json` | stdlib |

`uasset_core` is the only change to existing code: `maya_uebridge/uassetexport.py` imports the moved
helpers under their old names, so its behaviour and its tests stay as they are.

### Installer

`SkeldarAnim_Cascadeur_Install.py` at the repo root, published as a third asset of every release (as
`SkeldarAnim_Install.py` already is; the same CI rule re-uploads it on a push that touches only it).

1. Download `SkeldarAnim.zip` from `releases/latest/download/` (cancellable, stdlib `urllib`).
2. Unpack to a temp folder; refuse unless `skeldar_cascadeur/bridge.py` and `version.json` are there.
3. Replace `%USERPROFILE%\Documents\SkeldarAnim` with the new build.
4. Edit Cascadeur's `settings.json` (`%LOCALAPPDATA%\Nekki Limited\Cascadeur\settings.json`):
   - add the install folder to `Python.Path`;
   - add `skeldar_cascadeur` to `Python.Scripts`;
   - keep every other key; write a backup `settings.json.skeldar-backup` first; do nothing if both
     entries are already present (idempotent).
5. Tell the user to restart Cascadeur (until the live check says otherwise).

The user runs it once in Cascadeur's Python console. It does not touch the open scene, so it runs with
a scene open. Every refusal names what did not change.

### Unreal round trip (reuse)

- **Import:** the clip is exported to a temp FBX with `uescripts.export_script(out, package, fbx,
  preview_mesh=False)` (bones only), run by `uelink.run_script`, which already gives the refusal text
  when the editor is off or Remote Execution is disabled. The FBX is opened by `cascade_io`
  (`import_fbx`, scene filter, new tab). Several clips: one tab each, the window reports every result.
- **Export to uasset:** the scene is exported to a temp FBX, the target is checked to exist, the
  confirmation names the asset and the lost curves (`Pose_0..9`, `MoveData_*`, `DisableLegIK`,
  `RootMotionAdditiveInput`), the read-only flag is cleared and left off, then `reimport_script` runs.
  The reply goes through `records.reimport_line` and `records.unchanged_warning`. Perforce is not
  touched (this is the direct road, as in Maya).

### Shared (reuse)

Same protocol as Maya's "Send file": the FBX is zipped (deflate, the member named as the upload name),
the record goes out as `sending`, the zip is uploaded (temp.sh, then litterbox), and `ready` is
published with the URL. Name, author and machine travel in the record. Receivers are the existing Maya
Shared cards, which already import FBX clips. The name follows `records.upload_name`.

## Errors and refusals

Every refusal happens before anything is written, and says what did not change.

- Editor off or Remote Execution off: the `uelink` message.
- No uasset for the target, or no target picked: refused by name.
- Scene with zero or several skeletons: refused, naming them.
- Import failure: the new tab is closed; the window names the clip and the reason.
- Reimport reply `unchanged`: the warning from `records.unchanged_warning`, not a success.
- Fractional scene range at export: rounded outward (the trap-50 rule; a range that ends on a fraction
  makes UE refuse the animation silently).
- Scene fps not 30: a warning in the status line, export still allowed.
- Shared failure: the record becomes `failed`; the status says which host refused.

## Testing

- **Unit tests (plain Python, under mayapy's interpreter as the repo runs them):** the `settings.json`
  edit (idempotent, backup, other keys kept), the install payload includes the package, the action
  module's `name`/`description`/`run`, `uasset_core` helpers, the zip and record building, `prefs`.
  A subprocess test pins that `cascade_io` is the only module importing `csc`.
- **Live verify `docs/superpowers/plans/verify_cascadeur_bridge.py`**, run in Cascadeur's console with
  the Unreal editor open. Gates: installer on a fresh folder and on a second run; menu entry found;
  window opens and reopens; import of a real UE clip with its joint count and frame count equal to the
  UE export; export → reimport into a sandbox asset under `/Game/__bridge_verify` (frame count and
  length equal; the sandbox asset deleted afterwards); read-only flag handled; Shared send to a **test
  topic**, not the team channel, read back through the record. The animator's own assets are never
  written.

## Open items, to check on the live Cascadeur before the plan is final

1. Does `settings.json` accept an absolute `Python.Path` entry, and does Cascadeur need a restart?
2. Does a PySide6 window open and stay usable inside Cascadeur's process?
3. Round trip of a UE clip: bone names, orientation and 30 fps survive import and `export_joints`
   (or `export_all_objects`, whichever keeps the skeleton root).
4. The exact `csc` calls for the scene's range and fps (the names are not yet confirmed on this
   build).

If item 3 fails, the design changes at that point, not in the code: the plan will say how.

## Not in v1

Mesh or skin export, Cascadeur-side rigs or retargeting, several skeletons in one scene, selection
export, cameras, exporting uassets that are not skeletal, a hotkey row, and anything in Maya.
