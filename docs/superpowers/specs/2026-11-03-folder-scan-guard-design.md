# Animation Setup: Refresh reads, and asks before it reads thousands

2026-11-03. The animator, at 05:12:

> Посмотри на мою маю которая сейчас открыта. Я нажал на обновление списка файлов в animation
> setup и теперь у меня создаюстся какие-то 14 тысяч файлов? Это какой-то очень страшный баг

Asked whether to fix the two defects the investigation found: «Да, оба».

## What happened

Nothing was created. Measured, with their port closed, from the disk and from a reproduction of
their press in mayapy:

- the listing cache **their own press wrote at 05:11:53**,
  `%TEMP%\maya_uebridge\maya_uebridge_folder_2c6740e17084.json`, says `source: folder`,
  `location: C:/Users/MY PC/Downloads`, **14 037 rows** (13 777 fbx, 115 .anim, 56 mb, 53 ma,
  36 usd);
- their Downloads holds **14 206** files the plugin reads as clips. It is full of them because a
  Unity course was unpacked there on 31 October: **7 812** fbx under «Модуль V. Мультиплеер»,
  **6 136** under «Extracted 2026-10-31» - asset-pack props, not animations;
- the same scan run over the same folder in mayapy: the tree held **188 082 entries before and
  188 082 after** (174 575 files + 13 507 folders). No `.fbm`, no copy, nothing removed. The whole
  scan took **46 s**;
- `.fbm` folders anywhere under `C:\!!!Work`, Downloads and Documents: 20, every one of them older
  than 28 September.

So what the animator saw was the progress window counting through 14 206 files - the bare
«scanning...» over a number in the thousands - while Maya worked for 46 s.

The scan reads: `FBXRead` lists a file's takes and writes nothing (trap 166 measured that the
IMPORT, `FBXImport`, is what extracts embedded media into a `<file>.fbm`). The fear was wrong, and
the press that caused it was not: one click walked somebody's Downloads with no word about its size.

## The two defects

### 1. The take read could not carry a non-ASCII path

`formats.fbx_takes` put the path into a MEL string. MEL cannot carry a non-ASCII path: measured on
their own files, `mel.eval('FBXRead -f "...Модуль V/x.fbx"')` answers «Use syntax: FBXRead -f
filename» - the command never sees the file - so `fbx_takes` returned `[]`, `take_rows` made one row
with no takes and no frames, and every clip under a Russian-named folder read as «no animation».
**5 874 of their 11 580 Downloads fbx** are such files (half of a 400-file sample was refused), and
so would be any animation folder of theirs named in Russian.

It went unnoticed because the files under those folders are props: a static FBX's row looks the same
whether its takes were read or not.

Measured roads (mayapy 2027, their files):

| call | ASCII path | Cyrillic path |
|---|---|---|
| `cmds.FBXRead("-f", path)` | ok | **ok** |
| `cmds.FBXRead(path)` | «Use syntax» | «Use syntax» |
| `cmds.FBXRead(f=path)` | «Use syntax» | «Use syntax» |
| `mel.eval('FBXRead -f "..."')` | ok | **refused** |

**The fix**: the read goes through `cmds` - the flag positional, as its own string - with
`cmds.FBXGetTakeCount()` / `FBXGetTakeName(i)` / `FBXGetTakeLocalTimeSpan(i)`. Same answers as the
MEL road for an ASCII file, same cost (0.8 ms a file over 200 of them).

**Not** the staged ASCII copy (`sources.staged`): that is the import's road, and staging 14 000
files in order to LIST them would have been the very thing the animator feared.

### 2. One press walked whatever was picked

The walk is cheap - 1.1 s over 188 082 entries - so Refresh can count before it reads.

- `sources.scan_files(top, source)` is the walk, and `sources.scan(..., files=)` takes it, so the
  tree is never walked twice (two walks also cost a second pass and could answer differently);
- `sources.ASK_OVER` is **3 000** clips. Their own legitimate scans read 1 975 rows (a Unity
  project) and 740 (`C:/!!!Work/Animations`), so a real scan is never asked about;
- `sources.scan_question(top, files)` (pure) is what to ask. It answers the question the animator
  actually asked, in this order: the count, how long the read takes (`SCAN_MS` 3.3 ms a file,
  measured on their own press), **that nothing is written**, and - `sources.biggest_folders` - the
  folders holding the most of them, which is what shows the folder was picked by mistake:

  ```
  C:/Users/MY PC/Downloads holds 14 206 animation files.
  Reading them takes about 47 s and fills the list with as many rows.
  The scan only reads - it writes nothing beside your files.

  Most of them are in:
      7 812  Модуль V. Мультиплеер
      6 136  Extracted 2026-10-31
         57  Telegram Desktop

  Scan it?
  ```

- `window._ask_scan` is the dialog, injectable as `_refresh_files(asks=)`. **Cancel reads nothing**
  and leaves the list as it was. A batch session has nobody to ask and scans, as before - there the
  press itself is the answer;
- the progress window's title says it too: «Connect - reading 14 206 files, writing nothing».

## What is not built

- the stale 14 037-row cache on their disk is left alone: the card opens on that folder until they
  pick another with `...`. Deleting somebody's cache behind their back is not a fix;
- no cap on the rows, and no "do not ask me again" for a folder: one question a press is enough, and
  a cap would hide clips;
- the other formats' readers (`bvh`, `gltf`, `unityfiles`, and the `.ma`/`.mb`/`usd` rows) read
  through Python and never had the MEL problem;
- **the EXPORT has the same hole, and is named rather than half-fixed.** `animexport` writes
  through `mel.eval(export_command(path))`, and measured the same day: `FBXExport` into a folder
  named «Анимации» fails, while `cmds.FBXExport("-f", path, "-s")` writes the file. So Export
  FBX..., Export to uasset and the checkouts' EXPORT would refuse a Russian-named destination. It
  bites nothing today - of the 12 890 clip files under `C:\!!!Work` only **8** carry a non-ASCII
  path: two «копия» duplicates and three whose name holds a Cyrillic «С» where a Latin «C» is meant
  (`Сover.fbx`, `Сontrol_panel.fbx`, `SM_WallSloped_С_01.fbx` - which the listing could not read
  either until today). The fix is two lines; it wants its own test, a gate that exports into such a
  folder and reads the file back, and `verify_uebridge_export_range.py` / `verify_uebridge_fbx_rate.py`
  re-run.

## Proof

`docs/superpowers/plans/verify_folder_scan.py` - **0 of 14 gates, mayapy standalone**:

- four of the animator's own clips copied into a folder named «Анимации Модуль V»: the MEL road is
  the **control** and reads 4 rows with **0** frames, the new one reads **45 / 41 / 85 / 49**; an
  ASCII path answers exactly what it answered before; such a row carries an import reference with no
  refusal;
- a scan of a folder holding the Creep's embedded-media FBX: **4 entries before, 4 after**, no
  `.fbm`;
- the guard asks about their real Downloads (14 206 files, naming «7 812 Модуль V. Мультиплеер») and
  says nothing about `C:/!!!Work/Animations` (740); the scan takes the walk it is given.

Unit tests: `tests/test_uebridge_fbx_takes.py` (7), `tests/test_uebridge_scan_guard.py` (12), and
five in `tests/test_uebridge_window_more.FileListing` - the walk done once and handed on, no
question for a small folder, the question and a yes, a cancel reading nothing and keeping the list,
and a batch session scanning. **13 691 in the suite**, the one failure the known
`test_chat_deploy.Keys` (this machine's own saved keys).

**Not seen in a GUI Maya**: the dialog itself and the progress title are the animator's to see, after
Check update.
