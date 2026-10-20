# Chat: everybody without friends, emoji and reactions, avatars, a message sound

2026-10-20, the animator: «Давай реализуем в нашем чате эмоджи, звуковое сообщение,
возможность добавить аватарку. Сделать еще нужно что бы я видел всех пользователей добавлять
в друзья не нужно мы просто сразу всех видим». Asked:
- "a sound message" = **a notification sound when a message comes**, not a voice recording;
- emoji = **a picker by the composer and reactions on messages**;
- friends = **gone entirely**: everybody is in the list, a click opens a dm, anybody can be put in
  a group;
- avatar = **from a file**, cropped square by its centre, 256 px.

## Server (`server/chat/worker.js`)

- No friendship is asked anywhere: a dm with anybody, a group or a member of anybody, and a dm
  stays writable. The friends routes stay (an older client calls them) and nothing needs them.
- A new account is announced: `register` emits a global `user` event, so every list gets the
  newcomer without a reload.
- Reactions: table `reactions (chat, msg, uid, emoji, at, PRIMARY KEY (msg, uid, emoji))`. The
  socket frame `{type: "react", chat, id, emoji, on}`: a member of the chat, a message not
  deleted, `emoji` 1-16 characters with no ASCII letter, digit or space, at most 8 distinct a
  person on one message. It emits `reaction {chat_id, id, user_id, emoji, on}` (a seq event).
  A message's view carries `reactions: {emoji: [user id, ...]}` (in reaction order). A deleted
  message loses its reactions; a chat that dies takes them.

## Client

- `records`: a message's `reactions` (a dict of lists, `{}` when absent), the `reaction` event.
- `session`: `_on_reaction` (idempotent: on adds once, off removes), `react(chat, id, emoji)`
  toggles mine and applies it locally at once. `resync` reads the people instead of the friends;
  `_on_user` adds a person it did not know. `set_avatar(jpeg bytes)` uploads.
- `api`: `put_avatar(bytes)`, `avatar(user id)` (raw bytes).
- `look.directory(chats, people, me, online, typing, query)`: the left column - every chat
  (newest first), then everybody I have no dm with (online first, then by name); a person row
  says «в сети» / «был(а) …» and a click opens the dm (`session.open_dm`).
- The Friends and «Все пользователи» panes and their buttons are gone. New chat / Members pick
  from everybody.
- `avatars.py`: `<cache>/avatars/<uid>_<v>.jpg`, fetched on a thread (stdlib), shown as a round
  pixmap where an initials circle stood (list, feed, toasts, settings); a user with `avatar_v` 0
  keeps the initials. `prepare(path)` (Qt): the image cropped square by its centre, 256 px, JPEG
  under 256 KB. Settings: the picture and «Выбрать картинку…».
- `emoji.py` (stdlib): categories, the six quick reactions (👍 ❤️ 😂 😮 😢 🔥), the recently
  used (optionVar `skeldarChatEmojiRecent`), `only_emoji(text)` (1-3 emoji alone are drawn big).
- The picker: a popup of tabs and a painted grid; from the composer's smiley it inserts at the
  cursor, from a message's menu («Реакция…») it reacts. The menu's first row is the six quick
  reactions.
- The feed draws a message's reactions as pills under the bubble («👍 2»), mine outlined in the
  accent; a click toggles mine, a new pill pops.
- The sound: `maya_hubsound` gains `message`, a two-note chime (E5 then B5), shipped as
  `assets/sounds/message.wav`; `play(name, force=True)` plays it whatever the hub's interface
  sounds are. The chat's Sound setting is **on by default**.

## Not built

Voice recordings, custom emoji, removing an avatar, a group's avatar from the window.
