# Chat: previews for files, pictures by Ctrl+V (2026-10-22)

The animator: «давай сделаем так что бы в чате передавалось и превью позы или анимации. ТАк же
сейчас поза не перетаскивается прямо на риг во вьюпорт ... Еще хорошо бы было делать маленькое
превью картинку когда мы экспортируем что-то из сцены в чат или пересылаем сцену», then «а так же я
хочу иметь возмождность кидать в чат картинки просто через ctrl + v». Done alone.

## What a preview is

Made on the sender's machine, one JPEG under 256 KB (the server's picture limit):

- a pose card: its own `thumbnail.jpg`, its longest side 360 px;
- an animation card: its `preview.jpg` sheet painted again at 128 px cells (smaller if it would not
  fit), with its grid `{cells, columns, step, fps}` from the card's header - the chat plays it on
  hover at the clip's rate, as the library does; at rest the middle cell;
- a scene (Send scene) or a selection (Send selection): one playblast of the panel the animator
  looks at, at the current frame, with the library's HIDDEN flags off for it (controls, joints,
  grid ...) and back after, the panel's own aspect;
- a picture: itself, its longest side 640 px.

A preview that cannot be made (batch, no panel, a broken image) leaves the file going without one.

## Server

- `files` gains `thumb` (BLOB), `thumb_type`, `thumb_v`, `sheet` (JSON).
- `PUT /v1/files/<id>/thumb[?cells&columns&step&fps]` - the sender, while the file is uploading or
  ready (409 once it is sent), a JPEG/PNG under 256 KB; the grid when cells >= 2.
- `GET /v1/files/<id>/thumb` - a member, once the file is in a message (the sender earlier).
- A file's view carries `thumb_v` and `sheet`.
- Pictures are files: `.png`, `.jpg`, `.jpeg`, kind `image`.

## Client

- `maya_chat/thumbs.py`: the makers, `sheet_of`, `play_cell`, `cell_rect`, and `Cache`
  (`<store>/thumbs/<id>_<v>.jpg`, fetched once on a thread - the avatars' way). The sender's own
  preview goes into the cache when the upload ends: no fetch for my own.
- `files._begin(..., thumb)` keeps the preview beside the upload (`upload["thumb"]`, so my pending
  card shows it at once) and `_upload_work` puts it right after `file_start`; a refusal sends the
  file without it.
- `files.send_image(session, chat, QImage)`: a PNG, or a JPEG when that is under a third of it,
  at most 50 MB.
- The window: a preview frame over the card (132 logical px; a picture's 220), drawn fitted; an
  animation's sheet plays while the mouse is on it (the feed's timer runs while `playing`); a
  picture's card has Открыть (the system viewer) / Сохранить как…, a click on its picture opens it,
  and it is not dragged. Ctrl+V (and a paste through the menu, a drop on the composer) of a picture
  sends it; of files from Explorer, sends the sendable ones; text stays text
  (`Composer.insertFromMimeData`).

## The drop onto a rig

Driven in a disposable GUI Maya with a Manny_Rig: `card_aim` over the projected pelvis answered
«на Manny_Rig», with the chat's ghost under the cursor too, and a real press-move-release through the
feed's mouse handlers applied the card (hand_r on the card's place to 1e-6). Nothing was found wrong
on that road; the animator's report stands to be retried on this build.
