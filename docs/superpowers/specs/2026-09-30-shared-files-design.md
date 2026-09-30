# Shared: scenes and FBX between colleagues, one press (2026-09-30)

## The ask

«Мне очень часто приходится передавать какие-то сцены локально между сотрудниками. Можем ли мы
сделать какое-то Shared Temp хранилище в котором сможем обмениваться сценами?» and minutes later
«возможно не только сцен а еще и fbx файлов».

Decided with the animator, in order:

- GitHub (the plugin's own repository, or a private one) was asked about and **rejected**: an
  upload to GitHub always needs a key, and «Ключи никакие не нужны. Мне нужен максимально быстрый
  и удобный способ передавать файлы. Один человек нажал кнопочку у второго через 2 секунды
  появился файлик в списке. Пока что мы не переживаем за приватность проекта».
- **Everyone works remotely** («Все работают удаленно»), so there is no office LAN to go Maya to
  Maya over: the road is the internet.
- Of the two internet roads offered, **ntfy.sh + litterbox** (no account for anybody) over our own
  Cloudflare Worker (a one-time account for the animator, no limits).
- Privacy is not a concern for now: the files and the channel are public.

## Measured first (2026-09-30, from mayapy on the animator's machine)

| what | number |
|---|---|
| ntfy.sh: publish call | 0.77 s |
| ntfy.sh: publish -> a second process's open stream | **1.08 s** |
| ntfy.sh: how long a message stays in the channel | 12 h (the message's `expires`) |
| litterbox: 2 MB up / down | 4.6 s / 5.2 s |
| litterbox: 8 MB up / down, three runs | 2.6-5.8 s / 2.5-13.7 s (1.3-3.3 MB/s) |
| GitHub release asset, for comparison, down | 4.06 MB/s |
| litterbox limits (its own pages) | 1 GB a file; kept 1 h / 12 h / 24 h / 72 h |
| tmpfiles.org | 1.0 MB/s up; 100 MB and 60 minutes |
| filebin.net | the download answers a 5 KB HTML page, not the file |
| 0x0.st, ntfy attachments (8 MB) | the connection aborted |

So the notification is not the slow part; the file is. Two things hide its time: the row appears
at the colleagues' **when the sender presses** (a "sending" record goes out before the upload),
and a colleague's Maya **downloads in the background** the moment the file is ready, so Open is
local by the time anybody clicks it.

## The shape

A hub section **Shared** (`maya_share`, group Scene, after Connections, a new Tabler icon `send`),
in both hubs:

```
Shared                               online - 4 files      <- subtitle: the channel's state
Name     [Eugene            ]
Comment  [attack v2, check the sword]
[ Send scene ]  [ Send file... ]                           <- primary, secondary
+----------------------------------------------------------+
| 14:12  Eugene   Orc_attack.ma        12.3 MB   ready      |
| 14:05  Oleg     Longsword_02.fbx      2.1 MB   45%        |
| 13:40  you      Creep_idle.ma         8.0 MB   sent       |
+----------------------------------------------------------+
[ Open ]  [ Import ]  [ Save to... ]
status line
```

- **Name** is remembered (`skeldarShareName`) and starts as the Windows user name. The animator's
  is «MY PC», which names nobody, hence the field.
- **Send scene** (one press, no dialog):
  1. On the main thread, a COPY of the scene is written into the inbox (below). The working
     file, its name and its modified flag are untouched. The method (Export All, or a save under
     a temporary name and the name put back) is measured in the plan: it must keep the frame
     rate and the playback range.
  2. A **sending** record goes to the channel: the colleagues' rows appear within about a second.
  3. On a background thread the copy is zipped and uploaded to litterbox (kept 72 h), the
     progress on the status line; the animator keeps working.
  4. A **ready** record carries the file's address. On any failure a **failed** record goes out
     instead, and the colleagues' rows go away.
  5. The status names what did not travel with the scene: references, and textures that are not
     the plugin's own. The plugin's images travel by their `skeldarAssetImage` marker and are
     relinked on arrival.
- **Send file...**: a file dialog (`.ma`, `.mb`, `.fbx`), then steps 2-4 on that file. The file is
  copied into the inbox first, so a later edit of the original does not change what was sent.
- **The list**: newest first, the sender (`you` for this machine's own), the file, its size, its
  state (sending / NN% / ready / sent / failed), then the comment (a textScrollList row has no
  tooltip of its own). Rows older than 72 h leave the list (litterbox has deleted the file by
  then); the inbox copies stay on the disk.
- **Open** (and a double click): a modified scene is asked about with Maya's own save prompt.
  A scene is opened with `executeScriptNodes=False`, the vaccine nodes deleted
  (`character.malware_nodes`), the plugin's images relinked to the installed copy
  (`colour.relink_images`). An FBX opens as a new scene with the clip imported (FBXImport,
  mode add) and the timeline set to it.
- **Import**: a scene imported with `executeScriptNodes=False`, the same sweep and relink on the
  new nodes; an FBX through `animimport.import_clip` into a free namespace named for the file,
  as the bridge's "as a new skeleton" mode does.
- **Save to...**: the local copy copied where the animator picks.
- **A file from a colleague** triggers a Maya in-view message («Oleg sent Longsword_02.fbx»)
  and its background download; nothing ever opens by itself.

## The pieces

| module | does | imports |
|---|---|---|
| `maya_sharerecords.py` | the record (make, parse, validate), the states, the row text, expiry, the inbox folder name, size text | **stdlib only** |
| `maya_sharenet.py` | the upload (streamed multipart, progress, cancel), the publish, the download, the `Subscriber` thread (stream, reconnect, `since`) | **stdlib only** |
| `maya_share.py` | the section, the presses, the scene work, the history file, the glue from threads to Maya | `cmds`, the two above, `maya_scenesetup`, `maya_uebridge.animimport` (lazy) |

Payload rows for all three; the hub row; a hotkey row `window.shared` (the section openers'
convention).

**The record** (the ntfy message body, JSON, a few hundred bytes of ntfy's 4096):
`app` = `"skeldaranim-share"`, `v` 1, `id` (32 hex), `state` (`sending` / `ready` / `failed`),
`from`, `machine` (a random id remembered in `skeldarShareMachine`, so "you" means this machine),
`name`, `kind` (`scene` / `fbx`), `bytes`, and, once ready, `url` and `zip`; `comment`, `sent`
(unix time), `maya`, and for a scene `fps` and `range`. Parsing refuses anything else: another
app's message, an unknown version, a name with a path in it, and **a `url` whose host is not
`litter.catbox.moe`**.

**The channel**: `https://ntfy.sh/<TOPIC>`, `TOPIC` one constant (`skeldaranim-share-` + 16 random
hex); a verify run uses its own topic. The stream is `GET .../json?since=<last message id>`
(`since=12h` the first time), read line by line; a lost connection reconnects after 1, 2, 4 ...
30 s with the last id, so nothing is missed while the cache holds it.

**The state on `sys`** (trap 111): the subscriber, the history and the running transfers live in
`sys._skeldar_share`, so an update's purge does not start a second subscriber beside the first:
a fresh module stops the old one and starts its own. Threads never call `cmds`; they hand work to
`maya.utils.executeDeferred`.

**When it listens**: the subscriber starts when the Shared section is built. The hub builds every
section when it opens, and a docked hub is rebuilt at Maya's start, so a docked hub means Maya
listens from the start; with the hub never opened this session, nothing is received until it is.

**On disk**, under `<userAppDir>/SkeldarShare/`: `history.json` (the records by id and the
channel's last message id) and one folder per file, `<YYYY-MM-DD_HHMM>_<from>_<id6>/<name>`,
for what was sent and what arrived.

## Errors

Each refusal names itself and says «nothing was sent» / «nothing changed»:

- no internet or a service that does not answer;
- litterbox answering something that is not its file address;
- a zip over 1 GB;
- a download that answers 404 (the file expired);
- a scene that cannot be written;
- an FBX import that brings nothing.

A failed upload publishes `failed`. A download that fails leaves the row at «failed - Open
retries».

## Trust, stated

Nothing is authenticated: the topic is in the public repository and anybody who reads it can post
a record. Our defences:

- only litterbox addresses are accepted;
- a received file is never opened by itself;
- scenes are opened and imported without running script nodes, and the vaccine is swept out.

**Expressions in a hostile scene would still run when evaluated.** That is the cost of "no keys",
told to the animator.

## Not built

- deleting a sent file (litterbox has no delete; the file dies at 72 h);
- sending to one person (everybody sees everything, as asked);
- the files a scene references;
- resuming an interrupted upload;
- listening before the hub has been opened.

## Proof

- **Unit tests**: the pure record module, and the net module against a local HTTP server that
  imitates litterbox's multipart upload and ntfy's publish and stream.
- **A panel test** on the fake `cmds`.
- **Live**: `docs/superpowers/plans/verify_shared.py`, run in a disposable Maya (its own
  `MAYA_APP_DIR`, `MAYA_NO_HOME=1`, the plugin from a `git archive`) on a test topic, with a
  second process as the colleague. It proves:
  - a real scene holding an Orc D is sent;
  - the colleague's row appears (the press-to-row time measured);
  - the file downloads by itself (the press-to-ready time measured);
  - Open brings the Orc D in its textures, no script node runs, and the working file of the
    sender is unchanged;
  - an FBX is sent and imported;
  - a failure publishes `failed`.
