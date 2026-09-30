# Shared: Delete, Author, and a name for every upload (2026-09-30)

## The ask

«Во вкладку shared нужно добавить кнопку которая будет удалять выбранные файлы. И Name заменить
на author а comment на имя файла или сцены, что бы можно было удобно называть заливки».

Asked what Delete removes (the hosts have no delete: temp.sh and litterbox keep a file its 3 days
whatever we do; what can go is the row and the downloaded copies), the animator chose **«Всё у
всех»**: any picked file, their own or a colleague's, leaves every colleague's list.

## The card

```
Shared                               online - 4 files
Author   [Eugene            ]
Name     [Orc_attack_v2     ]   <- empty: the scene's or the file's own name
[ Send scene ]  [ Send file... ]
+-------------------------------------------------+
| list, several rows can be picked (ctrl / shift) |
+-------------------------------------------------+
[ Open ]  [ Import ]  [ Save to... ]  [trash]
status line
```

- **Author** is the old Name field relabelled: control `skeldarShareAuthor`, remembered in the
  SAME optionVar `skeldarShareName`, so the name already typed survives.
- **Name** replaces Comment: control `skeldarShareFileName`. What is typed names the upload:
  Send scene sends `<typed>.ma` (or `.mb`, as the scene is saved), Send file... sends
  `<typed>.<the file's extension>`. Empty: the scene's own name (`untitled_HHMM` unsaved), or the
  picked file's. It is cleared after a send, as the comment was: a name is one upload's.
  `records.upload_name(typed, fallback)` (pure) makes it a file name:
  - whitespace collapsed;
  - a typed `.ma` / `.mb` / `.fbx` dropped (the source's extension is the one that counts, so
    «attack.fbx» typed over a scene is `attack.ma`);
  - Windows' forbidden characters replaced with `_`, leading dots and trailing dots and spaces
    stripped, at most 80 characters;
  - a Windows device name (CON, NUL, COM1 ...) prefixed with `_`.
- **The comment is no longer sent** (a record's `comment` is ""). A colleague on an older build
  still sends one, and their row still shows it.
- **Delete**: a danger button, the trash icon alone in the skinned hub (a fourth labelled button
  does not fit the 360 px dock beside Open / Import / Save to...), «Delete» in the classic hub;
  and the Delete / Backspace key on the list (`deleteKeyCommand`).
- **The list takes several rows** (`allowMultiSelection`). Delete acts on all of them; Open,
  Import and Save to... on one and say so when more are picked. The status line of a multiple
  pick counts them.

## Delete, step by step

1. The picked rows. Nothing picked: «Pick files in the list first».
2. One confirm naming them (the first five, then «and N more») and saying it is for everybody
   and cannot be undone; Cancel is «nothing changed».
3. On a thread, one `deleted` record per file to the channel, in parallel (ntfy.sh answers a
   publish in ~0.8 s; ten deletes one after another would take 8). A deleted record is the file's
   record in state `deleted` with `by` (the author) and `by_machine`.
4. Back on the main thread, what the channel took is applied here (below) and the status says
   «Deleted N files for everybody». What it refused stays in the list, named, with «nothing was
   deleted» for it.

**Applying a `deleted`** (here after the press, and in every Maya from the channel):
- the record becomes `deleted`: **terminal** (rank 2, above ready/failed), so a `sending` or
  `ready` arriving after it, in any order, changes nothing;
- the row goes (`visible` drops `deleted`);
- a transfer of the file stops at its next progress tick (`_progress` answers False: net's
  Cancelled). A send stopped that way publishes no `failed`; a `ready` that raced past the delete
  is never applied;
- the downloaded or sent copy on this disk is deleted, and its folder when empty, **unless it is
  the scene open in this Maya** (that one stays, and the status says so);
- a colleague's delete puts «Oleg deleted Longsword.fbx» on the status line; our own echo from
  the channel changes nothing.

The entry stays in the history as a tombstone until it expires (72 h), so a replay of the channel
cannot bring the row back.

## Trust

Anybody can delete anybody's row, as asked, and a forged `deleted` could too (the channel is not
authenticated, as before). The file itself stays on its host until it expires; a delete takes it
off every list and every disk, not off the internet.

**Older builds** do not know `deleted` (their `parse` refuses an unknown state): the row stays in
their list until the file expires. Check update brings them in.

## Proof

- Unit tests: `upload_name`; `deleted` parsed, merged terminal, not visible; the press (confirm,
  cancel, parallel publish, partial failure), receiving a delete (row, transfer, local file, the
  open scene kept, the folder), a cancelled send publishing no `failed`, the one-row rule for
  Open / Import / Save, the panel's controls.
- Live, two mayapy processes on a test topic (`verify_shared_delete.py`), each with its own
  `MAYA_APP_DIR`: A sends a file under a typed name; B's row carries that name and B downloads
  it; A deletes it: B's row and file go; B deletes a second file A sent: A's row and copy go.
  Times measured.

## Addendum: what the live runs showed (2026-09-30, the same evening)

- **Proof**: `verify_shared_delete.py` 9/9 over the real ntfy.sh and temp.sh. A delete reached
  the colleague in 0.85 s and 0.93 s; a row appeared 0.86 s after its send.
- **The echo can come first.** Our own `deleted` came back on the stream BEFORE `publish` returned
  (the row went, then the press's status 0.8 s later). So `_deleted` asks the entry whether the copy
  was kept instead of trusting its own `_apply_delete`'s answer, and the verify waits for the status.
- **The card at the animator's dock** (viewport 510 physical, a disposable GUI Maya): at the first
  widths Open stood exactly at its size hint (93) and the trash 3 px under its own. Import 84, Save
  to... 94 and the trash 38 in the skin give Open 99 and the trash 58 (hint 55). The Name hint became
  «empty: the scene's own name», because the longer one was cut off.
- Two rows picked with `selectIndexedItem` stay picked across a refresh, and the trash deletes both.
  A Delete key sent to the list's widget runs `deleteKeyCommand`.
