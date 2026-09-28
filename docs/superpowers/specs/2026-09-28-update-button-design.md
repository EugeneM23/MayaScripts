# Update: one button that fetches the latest build from GitHub (2026-09-28)

The animator: «Давай в нашем плагине сделаем раздел в котором будет кнопка для
автоматического обновления наших инструментов. В разделе update есть кнопка
Check update при ее нажатии мая пойдет в репозиторий на гит хабе и скачает
сборку последней версии если сборка еще не установлена. Нужно реализовать
кнопку и при каждом коммит в гит хаб делать актуальную сборку и заливать ее.
Для этих целей я сделаю репозиторий публичным».

## Decisions taken with the animator

- **The repository goes public whole.** Raised before anything was built: a
  public repository publishes everything in it *and in its history* — OverRig
  (paid, its licence's clause 3 forbids making it available to others),
  Epic's Manny and UE4 Mannequin, the Orc from Unreal, the studio's Perforce
  host in CLAUDE.md and the specs. The private alternative (Actions still
  builds, Maya downloads with a read-only token) was offered and declined:
  «Публичный как есть». The animator flips the visibility; nothing here does.
- **Builds come from `feature/overrig-picker`**, the branch all work lands on.
- **Check update shows what is new and asks** before replacing anything: the
  installed build, the available build, the commits between them, Install /
  Cancel. It also guards a copy installed from the source folder with
  unpushed changes against being replaced by an older published build.

## Shape

```
push to feature/overrig-picker
  └─ GitHub Actions: python3 make_build.py --out dist/SkeldarAnim.zip
                                           --version-out dist/version.json
       └─ gh release create build-<utc stamp>-<sha7>  (marked Latest)
            assets: SkeldarAnim.zip, version.json;  older builds pruned to 10

Maya, hub > Update > Check update
  ├─ GET  github.com/EugeneM23/MayaScripts/releases/latest/download/version.json
  ├─ same commit as <scripts>/SkeldarAnim/version.json → "Up to date"
  ├─ else a dialog: installed / available / what's new → Install | Cancel
  ├─ GET  .../latest/download/SkeldarAnim.zip  (progress window, cancellable)
  ├─ unzip to %TEMP%, check it, run THE DOWNLOADED install.py (quiet)
  └─ deferred: the hub rebuilt from the new modules, «Updated to <sha>»
```

**`releases/latest/download/<asset>` rather than the REST API.** It is a
plain URL that redirects to the newest non-prerelease's asset — no JSON to
page through, no token, and it is not counted against the API's
60-requests-per-hour limit for unauthenticated clients, which a studio
behind one NAT address would share. The small `version.json` is read first,
so an up-to-date press costs a few hundred bytes, not the whole archive.

## Version identity: `version.json`

One record, written in three places from one function:

```json
{"name": "SkeldarAnim", "commit": "<40 hex>", "short": "bc51aee",
 "subject": "feat(export): ...", "date": "2026-09-25T14:07:11+03:00",
 "branch": "feature/overrig-picker", "built": "2026-09-28 12:10",
 "dirty": false, "log": [["<40 hex>", "subject"], ...]}
```

- `install.git_record(src_root)` (stdlib, `subprocess` git) answers
  commit/short/subject/date/branch/log (the last 30 commits, newest first) —
  `{}` where there is no git, which is every colleague's machine.
- `make_build` adds `built` and `dirty` and writes the record INTO the
  archive (`SkeldarAnim/version.json`, beside `BUILD_INFO.txt`) and, with
  `--version-out`, beside it — the release's second asset.
- `install.install` writes `<dest>/version.json`: the source's own when the
  source is a build (a colleague's drag, or the updater), otherwise
  `git_record(src)` plus `"source": <src>` — a copy installed from the
  repository says so, with its commit, so Check update compares it too.
  A re-drag from the installed folder itself (`same_place`) leaves the
  record alone. A copy installed before this existed has no record and
  reads as "unknown".

`version.json` is not a `_PAYLOAD` row: the source tree does not hold one
(the build and the install write it), and every payload row must exist in
the repository.

## `SkeldarAnim/maya_update.py` — the section

`cmds` and stdlib only, no Qt. Hub section `update`, last in `SECTIONS`, no
shelf button and no icon (the 2026-09-17 rule). Controls: a line
`skeldarUpdateInstalled` («Installed: bc51aee, 2026-09-25 14:07 - feat...»),
the **Check update** button, a status line `skeldarUpdateStatus`.

Pure halves (tested as such): `parse_record`, `describe`, `is_current`
(both commits known and equal), `changes_since` (the log entries newer than
the installed commit; when the installed commit is not in the log — older
than 30 builds, or unknown — the first 15 and a flag), `confirm_text`,
`archive_problems` (the members an archive must hold).

Thin halves, each with its seam for the tests: `fetch_text(url)` and
`download(url, path, progress)` over `urllib` with a `User-Agent` and a
timeout (`_open` is the one function that touches the network);
`unpack(zip, into)` → the extracted `SkeldarAnim/` folder and the record it
carries; `run_installer(folder)` → the downloaded `install.py` loaded **by
path under its own module name** and `install(dropped=..., quiet=True)`.
The downloaded installer, not the running one: a new build may change the
payload, and the old whitelist would copy yesterday's list of files.

`check_update(ask=None)` is the press. `ask` defaults to a `confirmDialog`
and is injectable because a modal over the command port blocks Maya's idle
queue (bridge note 6). Every refusal happens before the installed folder is
touched and says «nothing changed»: GitHub unreachable, no build published
(404 — also what a private repository answers), an unreadable record, a
cancelled download, a damaged archive. A failure INSIDE the installer keeps
the extracted folder and names it, so the animator can drag its
`install.py` by hand; otherwise the temp folder is removed.

**After the install the hub is rebuilt from the new modules.** The
installer purges our modules (`install.purge_modules`), so the callback
still running is the old module's; it defers one call that imports
`maya_hub` afresh and shows the Update section — the fresh module has not
built the accordion, so `show()` rebuilds it in place (trap 75's rule) —
and writes «Updated to <sha>» on the new section's status line. Deferred,
because the rebuild deletes the layout holding the very button whose
callback is running.

## CI: `.github/workflows/build.yml`

`on: push` to `feature/overrig-picker` (and `workflow_dispatch`),
`permissions: contents: write`, `concurrency: release` without cancelling —
the last push's build is the last release. `actions/checkout` with the full
history (the notes need `before..sha`), then `python3 make_build.py`
(stdlib only — it always was, mayapy was just the interpreter this machine
has), then `gh release create` with the two assets, `--latest`, notes = the
subjects of the commits in the push. Then releases whose tag starts with
`build-` beyond the newest 10 are deleted with their tags. Nothing else in
the repository is touched by CI.

## Addendum (the same morning): a build is the last PAYLOAD commit

With the record naming HEAD, a push of CLAUDE.md alone would publish a
new release of identical files, every colleague's Check update would offer
it, and the animator's own source install (recording the docs commit)
would be offered the previous build as "available". So `git_record` names
the last commit that touched the payload (`git log -1 -- <payload>`), the
log lists only such commits, and the workflow runs on pushes touching
`SkeldarAnim/**`, `make_build.py` or itself — the last two build the same
commit, so a release whose tag already ends in that commit is skipped.
Tags and titles carry the payload commit; the notes list the push's
commits under `SkeldarAnim/`.

## Not built

A check at Maya start, a rollback button, per-colleague channels, running
the unit tests in CI (half the suite wants mayapy; they run here before
every commit), a hotkey row for the section.
