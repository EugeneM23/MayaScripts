# Chat: a person's card with their files, and a picture viewer (2026-10-22)

The animator: «давай добавим возможность нажать на аватар пользователя и у нас откроется окошко с
увеличенной аватаркой и списком всех файлов. Мы должны иметь возможность сортировать по типам
файлов, позы анимации сцены». Mid-way: «У меня картинки по умолчанию открываются в пейнте. А можно
что бы в каком-то просмотрщике?». Done alone; the choices:

- **Which files**: what that person sent, in the chats I am in (a dm, a group) - not what others
  sent them. My own card lists everything I sent.
- **Where**: a card over the chat window (a dimmed backdrop), not a pane of its own.
- **Kinds**: Все / Позы / Анимации / Сцены / FBX / Картинки, each with its count, and a search over
  the name, the caption and the group's name.

## Server

`GET /v1/users/<id>/files[?before=<ms>]`: `{user (with presence), files: [{msg, chat, seq, at, text,
file, chat_kind, chat_name}], more}` - messages from `<id>` carrying a file, not deleted, in chats
the asker is a member of, newest first, 300 a page. An unknown id is 404.

## Client

- `api.person_files`; `look.PROFILE_KINDS`, `profile_counts`, `profile_rows`, `profile_line` (pure).
- `maya_chat/profile.py`: `Profile(win, user)` - the avatar at 92 px, name, @nick, presence,
  Написать (not on my own), the kind buttons, the search, the painted `FileList` (a row its
  preview, the animation's middle cell, or the file's tag; name; «анимация · 12 KB · 07:15 · в
  «Fights»»). Read on a thread. A double click goes to the message (older history loaded until it is
  there); the right button: Показать в чате and the file's verbs; a drag is the feed's own drag.
  Esc, ✕ or the backdrop closes it.
- Clicks that open it: `AvatarDot` (the chat header - a dm's partner, Members, New chat, my own in
  the list's foot; the settings' avatar is not), a dm or person row's avatar in the list, a group
  message's avatar and its sender's name in the feed. A group's picture is no person.
- `profile.Viewer`: our picture viewer, a frameless window owned by Maya's: fitted, the wheel zooms
  about the mouse, a drag pans, a double click fits again, the title row drags it, Esc / ✕ closes.
  `files.show_picture` opens it (was the system's program - Paint on the animator's machine).
