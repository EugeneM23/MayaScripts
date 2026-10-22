# Chat: scenes and files sent in a chat (2026-10-22)

The animator: «Давай добавим в наш мессенджер возможность пересылки сцен и файлов как в стеше и
шаре». Asked, and answered:
- the file lives in **our own Cloudflare R2**, not on Shared's anonymous hosts;
- the receiver downloads **on a click**, not at once;
- a file gets in by **a paperclip** in the composer, **a drag from Stash / Shared**, **a drag of a
  file from Explorer**, and a file card drags back **into Stash / a viewport**.
Design approved as shown in the session («Дизайн ок»).

## Server (`server/chat/worker.js`)

- An R2 bucket bound as `FILES` (`skeldar-chat-files` / `skeldar-chat-files-staging`). Without the
  binding every file route refuses `no_files` (503) «Files are not set up on this server».
- A file is one zip object `f/<id>`, uploaded with R2 multipart in parts of `PART` 16 MB (all but the
  last exactly PART: R2 asks for equal parts), at most `FILE_MAX` 1 GB.
- Table `files (id, chat, uid, name, kind, bytes, zip, fps, range, upload, parts, state, msg, at)`;
  state `uploading` -> `ready` -> `attached` (-> `expired`). Column `messages.file` (the file id),
  added by an `ALTER TABLE` that a second run ignores.
- Routes (each needs the token):
  - `POST /v1/files {chat, name, kind, bytes, zip, fps, range}` - a member of a writable chat; the
    name a plain `.ma/.mb/.fbx` file name of at most 120 characters, kind `scene` / `fbx`, zip
    1..FILE_MAX; at most 4 unfinished uploads a person. -> `{id, part_size, parts}`;
  - `PUT /v1/files/<id>/parts/<n>` - the uploader, while uploading; the body exactly the part's size;
  - `POST /v1/files/<id>/complete` - every part in -> `ready`;
  - `DELETE /v1/files/<id>` - the uploader, a file not attached yet (a cancel);
  - `GET /v1/files/<id>` - a member of the file's chat, attached: the zip, `content-length`;
    expired -> 410 `expired`.
- `send` may carry `file: <id>` (the uploader's own, `ready`, the same chat): the message's text may
  then be empty (a caption otherwise); in one transaction the file is `attached` to the message. A
  message's view carries `file {id, name, kind, bytes, zip, fps, range, expired}` or none.
- Deleting a message deletes its object and row. The daily alarm: attached files older than
  `FILE_KEEP` 30 days -> object deleted, state `expired` (the card says so); unfinished uploads older
  than a day and files whose message or chat is gone -> object and row deleted.

`deploy.py` makes the bucket when it is missing, binds it, and says plainly when R2 is not enabled
on the account (Cloudflare's 10042).

## Client

- `records.message` reads `file` (`records.file`, strict; a bad one is dropped, the message kept).
- `api`: `file_start`, `file_part`, `file_complete`, `file_cancel`, `file_download(id, path,
  progress)` (streamed to disk in 1 MB pieces).
- `maya_chat/files.py` (no Maya, no Qt at import; the scene work is lazy):
  - `Uploads` on the session: `send(chat, path, name, meta, caption)` shows a pending message at once
    with `file` and `upload {progress, state}`; a thread zips (Shared's `name` inside, level 6), starts,
    sends the parts, completes; then, on the main thread, the send frame goes into the outbox as any
    message (it survives a restart from there; an upload interrupted by quitting Maya does not, and is
    simply gone). A failure -> the pending is `failed` with the reason; `retry` uploads again, `cancel`
    / `discard` aborts on the server.
  - `Downloads`: `fetch(file, then)` on a thread into `<store>/files/<id>/`, unzipped, kept; a second
    press uses what is on disk; progress per file id; `then(path)` runs on the main thread.
  - `send_scene(chat, caption)`: a copy of the active tab exactly as Shared makes it
    (`tabscope.export_scene`, `maya_sharerecords.scene_file_name` / `upload_name`, fps and range);
    `send_path(chat, path, caption)`: a `.ma/.mb/.fbx` from disk.
  - Actions on a downloaded file reuse Shared's: `maya_share.open_file(path, record)` /
    `import_file(path, record)` (split out of `open_entry` / `import_entry`, which now call them),
    Save to... (a copy where the animator picks), To Stash (`maya_stash.stash_file`).
- Threads hand back to Maya's main thread through `maya.utils.executeDeferred` (a test passes its
  own `defer`).

## Window (`maya_chat/window.py`)

- A paperclip left of the emoji button: a menu **Send scene** / **Send file...**; the composer's text
  goes with it as the caption and is cleared.
- The window accepts drops: a file from Explorer (`.ma/.mb/.fbx`; anything else said and refused),
  and a Stash / Shared row (their drag's new target `chat`: `maya_filedrag` learns section `chat`,
  the window and the rail's chat icon). Both go to the open chat; with no chat open it is said.
- A file message's bubble is a card: the icon (scene / fbx), the name, the size and the sender's
  caption under it; buttons **Open**, **Import** and **⋯** (Save to..., To Stash). While uploading:
  a progress bar and «отмена»; downloading: a progress bar on the card; expired: «файл истёк», no
  buttons. The right-button menu gains the same rows.
- A card pressed and dragged past Qt's start distance: the hub's ghost; onto a viewport = Import,
  onto Stash = a copy into the stash (each downloaded first when needed); elsewhere nothing.

## Proof

- Unit tests: records (`file`), api (the four calls on a fake opener), files (upload in parts,
  failure and retry, the outbox frame, download and the cache), session (a file message pending,
  acked, failed), window offscreen (the card, its buttons, a drop, the menu), filedrag (`chat`).
- `verify_chat_server.py` phase `files` against staging: a 40 MB zip in three parts, a stranger
  refused the parts and the download, the member downloads it byte for byte, a send with it, a
  delete removing the object (404 after), a bad name / too big / not member refused.
- `verify_chat_client.py`: two accounts headless, a file sent through `Uploads` and received through
  `Downloads` byte for byte.
- Deployed to staging, then production.
