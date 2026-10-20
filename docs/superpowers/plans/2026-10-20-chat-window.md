# Chat window and rail Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** the messenger's window in Maya (plan 3 of `docs/superpowers/specs/2026-10-19-chat-messenger-design.md`): a floating hub window drawn from the session of plan 2, opened from the hub rail, with an unread badge on the rail icon and a viewport message.

**Architecture:** `maya_chat/look.py` (stdlib, pure) holds every rule a test can pin without Qt: titles, times, presence text, the feed's items and ticks, search, the layout switch. `maya_chat/window.py` (Qt) draws it from `session.state`, listening through `session.listen`; it never talks to the server itself except through the session and its `api`. `maya_chat/notify.py` turns session events into the rail badge, a viewport message and a sound. `maya_chat/panel.py` is the hub card (an Open Chat button, like the Pose Library's). `maya_hub` gets the row `chat`, opens the window from a rail click, and paints the badge.

**Tech Stack:** Python 3 in Maya 2027, PySide6 6.8.3, `maya.cmds`; tests under `mayapy -m unittest` with `QT_QPA_PLATFORM=offscreen`.

## Global Constraints

- Every interface looks and moves like the Time Bar (`docs/interface-motion.md`): colours only from `maya_hubstyle.TOKENS`, mine `#5a3922`; hover lift + glow 110 ms, a press flash 120 ms, a count pop 200 ms; the data is instant, only the picture animates; ⋮ → Interface animations off (`maya_hubmotion.enabled()`) makes it all instant.
- No modal dialog anywhere (a modal blocks Maya's idle queue). Refusals are one line where the press was.
- Window: `maya_hubwindow` look B, title «Chat» with the connection state, out of the rail icon and back into it (`maya_hubwindow.Burster`); place and size in `skeldarChatWindowPos` / `skeldarChatWindowSize`, default 760 × 520, least 520 × 360; below 600 px one column.
- State lives on `sys` (trap 111); widgets are found again by name, never kept across a rebuild (trap 135); graphics effects are held (trap 201).
- UI words are the spec's (Russian).
- The client imports nothing heavy at `import maya_chat`.

---

### Task 1: `look.py`, the pure rules

**Files:** Create `SkeldarAnim/maya_chat/look.py`; Test `tests/test_chat_look.py`.

**Produces:** `initials(user)`, `user_colour(user_id)`, `display_name(user)`, `clock(ms, now_ms)`, `day_label(ms, now_ms)`, `last_seen(ms, now_ms)`, `status_title(status)`, `other(chat, me_id)`, `chat_title(chat, me_id)`, `presence(chat, me_id, online, typing, now)`, `preview(chat, me_id, typing, now)`, `ordered(chats)`, `matches(chat, query, me_id)`, `feed(messages, pending, me_id, chat, reads, now_ms)` → `[Item]` (`kind` "day" / "msg", `text`, `message`, `mine`, `first`, `last`, `tick` ∈ "", clock, sent, read, failed), `nick_problem(text)`, `one_column(width, scale)`, `count_text(n)`, `last_mine(messages, me_id)`, `DEFAULT_SIZE`, `LEAST_SIZE`, `UNSENT_MS` (10 minutes), `JOIN_MS` (5 minutes), `TYPING_S` (5).

- [ ] Tests first for each rule (today / yesterday / this year / older, groups joined within 5 minutes by one sender, a day separator, ✓ / ✓✓ by the other members' read marks, a sending message older than 10 minutes reads failed, a dm's and a group's presence, a deleted message's preview), then the module, then the tests green.

### Task 2: the window

**Files:** Create `SkeldarAnim/maya_chat/window.py`; Test `tests/test_chat_window.py` (offscreen, a fake session holding a `State`).

**Consumes:** `session.Session` (`state`, `listen`, `unlisten`, `send`, `retry`, `discard`, `edit`, `delete`, `read`, `typing`, `open_dm`, `load_history`, `sign_in`, `sign_in_code`, `code`, `sign_out`, `api`), `look`.

**Produces:** `ChatWindow(session, scale)` with `root`, `show_at(origin)`, `close_into(origin, done)`, `open_chat(chat_id)`, `refresh()`; module `show(origin=None)`, `toggle(origin=None)`, `close(origin=None)`, `is_open()`, `window()`; names `skeldarChatWindow`, `skeldarChatList`, `skeldarChatFeed`, `skeldarChatComposer`, `skeldarChatSend`, `skeldarChatLine`.

- [ ] Tests: signed out shows the sign-in page; signed in shows the list ordered by the last message; a click opens the chat and reads it; Enter sends (the session gets the text, the bubble shows a clock), the ack turns it ✓, the other's read mark ✓✓; Shift+Enter is a new line; ↑ in an empty composer edits my last; Esc cancels; Reply puts the bar up and the send carries `reply_to`; Delete calls the session; a narrow window shows one column; the window's size and place are remembered; animations off paint the same end picture.
- [ ] Then the module, then green.

### Task 3: notify, the card, the rail

**Files:** Create `SkeldarAnim/maya_chat/notify.py`, `SkeldarAnim/maya_chat/panel.py`; Modify `SkeldarAnim/maya_chat/__init__.py` (`show`, `toggle`, `ensure`), `SkeldarAnim/maya_hub.py` (the row, `WINDOW_SECTIONS`, `paint_badge`, `_chat_soon`), `SkeldarAnim/maya_hubqt.py` (`Skin.set_badge`, `icon_with_badge`), `SkeldarAnim/maya_hubicons.py` (message-circle, pencil, users, settings, arrow-left, arrow-down); Tests `tests/test_chat_notify.py`, `tests/test_hub.py`, `tests/test_hubqt.py`.

- [ ] Tests: the unread total; a message from another while the window is closed paints the badge and makes one viewport message (off by its optionVar: none); the badge pops and reads «99+» past 99; the hub row `chat` exists in group animation with icon `message-circle`; a rail press on `chat` opens the window instead of a card.
- [ ] Then the code, then green.

### Task 4: picture, CLAUDE.md, commit

- [ ] `docs/superpowers/plans/render_chat_window.py`: the window offscreen at 150 % on a made-up state (sign-in, the list and a chat with day separators, mine and others', a reply, a failed one, the narrow column) → `chat_window.png`.
- [ ] A CLAUDE.md section; commit by path through a temp index.
