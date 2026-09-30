# Shared (scenes and FBX between colleagues) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A hub section **Shared**: one press sends the open scene (or any .ma/.mb/.fbx) to every
colleague's Maya, where it appears in a list within about a second and downloads by itself.

**Architecture:** the file goes to litterbox.catbox.moe (anonymous, 1 GB, kept 72 h), a JSON
RECORD of it goes to an ntfy.sh channel every Maya listens to on a background thread. Three
modules: `maya_sharerecords` (pure record rules), `maya_sharenet` (stdlib network),
`maya_share` (the section, the presses, Maya glue). Threads never call `cmds`; they hand work
to `maya.utils.executeDeferred`. The state lives on `sys._skeldar_share` (trap 111).

**Tech Stack:** Maya 2027 `cmds`, Python stdlib (`urllib`, `threading`, `zipfile`, `json`),
the hub (`maya_hub`, `maya_hubstyle` marks), mayapy `unittest`.

Spec: `docs/superpowers/specs/2026-09-30-shared-files-design.md`.

## Global Constraints

- No keys, no accounts: litterbox `https://litterbox.catbox.moe/resources/internals/api.php`
  (`reqtype=fileupload`, `time=72h`, `fileToUpload`), ntfy `https://ntfy.sh/<TOPIC>`.
- A received record is accepted only with `app == "skeldaranim-share"`, `v == 1`, a 32-hex `id`,
  a state in `sending/ready/failed`, a plain `.ma/.mb/.fbx` name, and for `ready` an `https`
  url on host `litter.catbox.moe`.
- Scenes are opened and imported with `executeScriptNodes=False`; nothing received is opened by
  itself.
- The scene copy is `cmds.file(path, exportAll=True, type=..., force=True,
  preserveReferences=False)` (measured 2026-09-30: fps, playback and animation range, current
  time and unsaved edits kept; the scene's name and modified flag untouched).
- On disk: `<userAppDir>/SkeldarShare/history.json` and `<userAppDir>/SkeldarShare/<folder>/<name>`.
- Tests: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v`
  from the repo root. No system Python (it hangs).
- Commit only this work's files; `CLAUDE.md` and `export_orc_d_1p_fbx.py` hold other sessions'
  edits (stage our hunks through `git update-index --cacheinfo` when touching a shared file).

---

### Task 1: `maya_sharerecords` - the record, pure

**Files:**
- Create: `SkeldarAnim/maya_sharerecords.py`
- Test: `tests/test_sharerecords.py`

**Interfaces:**
- Produces: `APP, VERSION, STATES, HOSTS, LIFETIME, SENDING_TIMEOUT, NEWS_WITHIN, MAX_ZIP`;
  `new_id() -> str`; `kind_of(name) -> "scene"|"fbx"|None`;
  `scene_file_name(scene_path, now) -> (name, maya_type)`;
  `make_record(state, rid, sender, machine, name, size, sent, comment="", maya="", fps=None, frame_range=None) -> dict`;
  `with_state(record, state, **extra) -> dict`; `encode(record) -> str`; `allowed_url(url) -> bool`;
  `parse(text) -> dict|None`; `from_event(event) -> dict|None`; `merge(known, record) -> dict`;
  `is_mine(record, machine)`; `expired(record, now)`; `visible(records, now) -> list`;
  `is_news(record, now)`; `status_label(record, mine, progress=None, local=False, error="") -> str`;
  `size_text(n)`; `when_text(sent, now)`; `row_text(record, mine, status, now) -> str`;
  `inbox_folder(record) -> str`; `announce_text(record)`; `archive_problems(names, name) -> list`;
  `sender_default(user)`; `subtitle(online, count)`; `left_behind_note(names)`;
  `to_history(entries, since) -> str`; `from_history(text, now) -> (entries, since)`.

- [ ] **Step 1: Write the failing tests** — `tests/test_sharerecords.py`: construction and
  encode/parse round trip; `parse` refusing another app, another version, a bad id, an unknown
  state, a name with a path / a leading dot / another extension, a non-int size, a ready record
  on another host or over http; `from_event` ignoring `open`/`keepalive`; `merge` (ready over
  sending, a replay returns the known object, failed does not replace ready); `visible` (order
  newest first, expired / failed / stale sending dropped); `status_label` for every branch;
  `size_text` (KB, MB, GB); `when_text` (today / another day); `row_text` columns and truncation;
  `inbox_folder` (a Cyrillic sender kept, path characters replaced); `archive_problems`;
  `scene_file_name` (saved .ma/.mb kept, untitled named by the time, other extension -> .ma);
  `from_history(to_history(...))` round trip dropping expired and malformed entries, a broken
  file reading as empty; `subtitle`; `left_behind_note` (none, one, more than three); the module
  importing nothing outside the stdlib (a subprocess test, the `bodymap` pattern).
- [ ] **Step 2: Run** `mayapy -m unittest tests.test_sharerecords -v` — FAIL (no module).
- [ ] **Step 3: Write `SkeldarAnim/maya_sharerecords.py`** (the functions above; the row reads
  name, sender, state, size, time, comment in fixed columns 24/8/13/8/11).
- [ ] **Step 4: Run** — PASS.
- [ ] **Step 5: Commit** `feat(shared): the record, pure (maya_sharerecords)`.

### Task 2: `maya_sharenet` - litterbox and ntfy.sh, stdlib

**Files:**
- Create: `SkeldarAnim/maya_sharenet.py`
- Test: `tests/test_sharenet.py` (a local `ThreadingHTTPServer` playing both services)

**Interfaces:**
- Consumes: `records.allowed_url`.
- Produces: `UPLOAD_URL, KEEP="72h", NTFY, TOPIC, USER_AGENT`; exceptions
  `ShareError`, `Expired(ShareError)`, `Cancelled(ShareError)`;
  `MultipartBody(path, fields, file_field, filename, progress=None)` (`.read(n)`, `.length`,
  `.content_type`, `.close()`); `upload(path, progress=None, url=None, keep=KEEP) -> str` (the
  address); `publish(text, topic=None, base=None) -> str` (the message id);
  `download(url, path, progress=None) -> int` (bytes; written through `path + ".part"`);
  `Subscriber(on_event, since="12h", on_state=None, topic=None, base=None, delays=DELAYS, timeout=STREAM_TIMEOUT)`
  — a daemon `Thread` with `.since`, `.state`, `.stop()`, `.url()`. `progress(done, total)`
  returning `False` cancels. `topic=None`/`base=None` resolve to the module constants AT CALL
  TIME, so a verify run can point the module at a test topic.

- [ ] **Step 1: Write the failing tests** — upload (the two fields, the file bytes, progress
  ending at total, cancel raising `Cancelled`, a reply that is no address, an HTTP 500, an
  unreachable host, all `ShareError`); publish (the body arrives, the id comes back); download
  (bytes and progress, 404 -> `Expired` with nothing left on disk); the subscriber (messages
  published before and after it starts arrive in order, `since` follows the last id, `stop()`
  ends the thread within 3 s; a stream closed by the server reconnects with `since=<last id>`
  and the states pass through `online` and `offline - ...`).
- [ ] **Step 2: Run** — FAIL.
- [ ] **Step 3: Write `SkeldarAnim/maya_sharenet.py`.** The upload body is a file-like
  multipart stream with an explicit Content-Length (http.client reads a body that has `read`);
  the upload's filename is always `share.zip` (the real name travels in the record; a Cyrillic
  name must not reach a multipart header). The subscriber reads `GET {base}/{topic}/json?since=`
  line by line, sets `since` to each message id before calling `on_event`, swallows a callback's
  exception, reconnects after `delays` (1, 2, 4, 8, 16, 30 s), and `stop()` shuts the socket
  down so a blocked read returns.
- [ ] **Step 4: Run** — PASS.
- [ ] **Step 5: Commit** `feat(shared): litterbox + ntfy.sh, stdlib (maya_sharenet)`.

### Task 3: `maya_share` - sending, receiving, history, the section

**Files:**
- Create: `SkeldarAnim/maya_share.py`
- Test: `tests/test_share.py`

**Interfaces:**
- Consumes: Tasks 1-2; `maya_scenesetup.character.malware_nodes`,
  `maya_scenesetup.colour.relink_images / ASSET_IMAGE`, `maya_scenesetup.catalog.asset_path`,
  `maya_uebridge.animimport.import_clip / existing_namespaces / fps_from_unit`,
  `maya_uebridge.records.namespace_for` (all lazy imports).
- Produces: `HUB_SECTION = "shared"`; controls `skeldarShareName`, `skeldarShareComment`,
  `skeldarShareList`, `skeldarShareStatus`, `skeldarShareSubtitle`; `state()`,
  `sender_name()`, `machine_id()`, `share_dir()`, `inbox_path(record)`, `load_history()`,
  `save_history()`, `send_scene(comment=None)`, `send_file(path=None, comment=None)`,
  `listen()`, `receive(record, now=None)`, `fetch(rid)`, `open_entry(rid)`,
  `import_entry(rid)`, `save_entry(rid, dest=None)`, `refresh()`, `build_panel()`, `is_open()`,
  `show_window()`. Seams for tests: `_defer(fn, *args)`, `_spawn(fn)`, the module attribute
  `net`.

- [ ] **Step 1: Write the failing tests** — on a recording `cmds` (FakeUiCmds plus `file`,
  `internalVar`, `about`, `playbackOptions`, `currentUnit`, `fileDialog2`), a fake `net`
  (records every publish, keeps uploads by url, serves them on download), `_spawn` and `_defer`
  running at once:
  - `send_file` copies into the inbox, publishes `sending` then `ready`, the entry is local and
    ready, the status names the file;
  - an upload that raises publishes `failed`, the entry is failed, the status says nothing was
    sent;
  - `send_scene` writes the copy through `exportAll` with `preserveReferences=False` and the
    scene's type, and does not touch the scene's name;
  - a colleague's `ready` is fetched into the inbox and announced when it is news, not when it
    is history;
  - a replay changes nothing; our own record is never fetched;
  - the history survives a fresh state (save, clear `sys._skeldar_share`, load);
  - `open_entry` on a file not downloaded starts the download and says so; on a `sending` one
    says to wait;
  - `listen()` stops the subscriber it replaces;
  - `build_panel` lands the five named controls, marks one primary, and starts listening.
- [ ] **Step 2: Run** — FAIL.
- [ ] **Step 3: Write `SkeldarAnim/maya_share.py`.** Open/Import of a scene use
  `executeScriptNodes=False, ignoreVersion=True, prompt=False`; Open sweeps the vaccine nodes
  and relinks the plugin's images; Import deletes every script node that arrived (none ran) and
  relinks the new file nodes; an FBX goes through `animimport.import_clip` into a namespace from
  `records.namespace_for` (Open: a new scene first). Maya's own `saveChanges("")` asks about an
  unsaved scene (skipped in batch mode). The list keeps its selection by id and rewrites only
  the rows that changed, so a progress tick does not jump the scroll.
- [ ] **Step 4: Run** — PASS.
- [ ] **Step 5: Commit** `feat(shared): the Shared section (maya_share)`.

### Task 4: the hub row, the icon, the payload, the hotkey row

**Files:**
- Modify: `SkeldarAnim/maya_hub.py` (SECTIONS, after connections:
  `Section("shared", "Shared", "maya_share", "build_panel", "skeldarHubFrameShared", "scene", "send")`)
- Modify: `SkeldarAnim/maya_hubicons.py` (Tabler `send`: `"M10 14l11 -11"`,
  `"M21 3l-6.5 18a.55 .55 0 0 1 -1 0l-3.5 -7l-7 -3.5a.55 .55 0 0 1 0 -1l18 -6.5"`)
- Modify: `SkeldarAnim/install.py` (payload rows `maya_sharerecords.py`, `maya_sharenet.py`,
  `maya_share.py`)
- Modify: `SkeldarAnim/maya_hotkeys.py` (row `window.shared`, `partial(_show, "maya_share", "show_window")`)
- Test: the existing hub / icon / install / hotkey suites, plus a section test in
  `tests/test_share.py` (`show_window` asks the hub for `shared`).

- [ ] **Step 1:** add the test that `maya_hub.section("shared")` exists in group `scene` after
  `connections`, that `"send"` is in `maya_hubicons.ICONS`, that the three modules are payload
  rows, that `window.shared` is a hotkey row; run — FAIL.
- [ ] **Step 2:** make the four edits; run the WHOLE suite; fix any count a suite pins.
- [ ] **Step 3: Commit** `feat(shared): the hub section, its icon, payload and hotkey rows`.

### Task 5: the live proof

**Files:**
- Create: `docs/superpowers/plans/verify_shared.py` (the receiver, mayapy standalone) and
  `docs/superpowers/plans/verify_shared_sender.py` (sent into a disposable GUI Maya over its port)

- [ ] **Step 1:** a disposable Maya (`MAYA_APP_DIR` scratch, `MAYA_NO_HOME=1`, a free port,
  the userSetup in `<MAYA_APP_DIR>/2027/scripts/`), the repo's `SkeldarAnim` first on
  `sys.path`, `maya_sharenet.TOPIC` = a fresh test topic.
- [ ] **Step 2:** the receiver (mayapy, its own scratch `MAYA_APP_DIR`) listens on the topic,
  running deferred work on its main loop, and logs the times it sees `sending`, `ready` and the
  local file.
- [ ] **Step 3:** the sender adds an Orc D, adds a script node that would write a marker file,
  keeps an unsaved edit, opens the hub, and presses Send scene. Gates: the sender's scene name
  and modified flag unchanged; the receiver's row within 3 s of the press; the file local; Open
  in the receiver: the marker file never written, the Orc D's file nodes on the receiver's
  plugin assets and existing, fps and range as sent.
- [ ] **Step 4:** the receiver sends an FBX back (`send_file`); the GUI Maya's list shows it,
  downloads it, and Import brings its joints in a namespace.
- [ ] **Step 5:** an upload made to fail (`upload` url pointed at a closed port) publishes
  `failed` and the receiver drops the row.
- [ ] **Step 6:** kill the disposable Maya; commit the verify scripts with their numbers.

### Task 6: docs, the installed copy, memory

- [ ] CLAUDE.md: a section "Shared" (what, measured numbers, traps found); staged as our hunk
  only.
- [ ] Refresh the animator's installed copy from a `git archive` of the commit (never the
  working tree), `diff -rq` clean, the hub rebuilt.
- [ ] Ask before pushing (a push publishes a build to every colleague).
