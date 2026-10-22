## Chat: voice and video calls (2026-10-22)

The animator: calls in the messenger - voice, video and screen sharing, up to 4 people. Spec
`docs/superpowers/specs/2026-10-22-chat-calls-design.md`, plan `docs/superpowers/plans/2026-10-22-chat-calls.md`.
- **Server** (`server/chat/worker.js`): tables `calls` (id, chat, by, kind, cid, state ringing / live /
  ended, started_at, answered_at, ended_at) and `call_members` (joined_at, left_at, gone_at, declined).
  Frames `call_start {chat, kind, cid}`, `call_join`, `call_leave`, `call_decline`, `call_signal {call, to,
  data}`. The stored event `call` (a seq, replayed on reconnect) carries the view `{id, chat, by, kind, cid,
  state, members, declined, started_at, answered_at, ended_at}` to every member of the chat; `call_signal`
  is relayed live only, never stored, between two members, `data` at most 64 KB. At most 4 (`call_full`),
  one unended call a chat (`call_exists`); a ringing call ends at 45 s unanswered, when its caller hangs
  up, or when everybody else declined; a live one when one person is left; a member whose sockets are all
  gone 30 s leaves; back within 30 s, the views of the calls it is still in go out again (a new seq), and a
  second `call_join` by a member answers the view again. When a call ends the server posts the **call
  line**: a message from its starter with `call: {id, kind, answered, seconds}` and, for clients without
  calls, the note in words as its text («📞 Звонок · 7 с», «📞 Пропущенный звонок»; a call line cannot be
  edited); ours draw the note and skip the text. `GET /v1/turn`: Cloudflare TURN credentials
  (`TURN_KEY_ID` / `TURN_KEY_TOKEN` secret bindings, port 53 dropped), else Cloudflare's STUN, `turn: false`.
- **Client**: `maya_chat/calls.py` (stdlib: `merge`, `of_chat`, `mine`, `ringing_for`, `can_join`,
  `start_args`, `peer_commands`, `note_text`); `records.call` / `call_note`; `Session.start_call /
  join_call / decline_call / leave_call / call_signal / turn_servers` (cached to the ttl), `state.calls`.
  Who offers: the one who JOINS offers to every member already in; the starter never offers. A resync
  drops unended call views (they are learnt again from events). Signing out and closing the session tell
  `calls_end` while the link is up: the call window hangs up, the rings stop.
- **A Maya that restarted mid-call** stays a member on the server (its reconnect clears the 30 s): the
  calls this Maya has a window in are kept on disk (`calls.json` in the chat's store, `Session.call_here`),
  and a `call` view listing me in a call marked here that no window holds (a starter's window still waiting
  on its cid holds it) is left - looked at again 3 s later, after the catch-up, once a call
  (`notify.stray`). Only calls marked on THIS machine: a second Maya signed in elsewhere is never kicked.
- **The call page** (`assets/call/call.html|css|js`, `maya_chat/callpage.py`): a WebRTC mesh in Maya's
  Chromium (QtWebEngine), loaded at base URL `https://skeldar.call/`, the bridge over QWebChannel
  (`qwebchannel.js` from Qt's resource). Camera and microphone granted by `CallPage` to that origin only;
  the screen through `screen_requested`. The joiner makes the transceivers, the answerer puts its tracks on
  the offer's (`attachLocal`): with its own `addTransceiver` the answerer sent nothing. Commands wait for
  `start`; a signal before `start` is held by the window and replayed. `start` carries the FIRST view that
  holds me (I offer to those already in it, less any who left since); anyone who came later offers to me,
  so the membership since then follows as `add_peer` (offer False) / `remove_peer` - a page that loaded
  slowly while others joined used to offer to them as they offered to it (glare). The page refuses any
  navigation after its first load and the view takes no drops.
- **The window** (`maya_chat/callview.py`, one call at a time on `sys._skeldar_chat_call`): look-B frame,
  title with the chat's name and a timer, the page, mic / camera / screen / devices / fold / hang up; folded
  a 240x170 always-on-top tile; place and size `skeldarChatCallPos` / `skeldarChatCallSize`, devices
  `skeldarChatCallMic` / `skeldarChatCallCam`. Refusals in Russian. A second call asks to end the first.
- **The incoming call** (`maya_chat/toast.py` CallCard, `notify.py`): a card «Входящий звонок · Bob» with
  Голос / Видео / Отклонить nearest the Time Bar; the ring (`assets/sounds/ring.wav`) looped with
  `force=True` until answered, declined, ended or 45 s.
- **The chat window**: voice and video buttons in a chat's header (hidden while the chat has an unended
  call; «Присоединиться» when one can join); the call line in the feed a centred pill «Звонок · 7 мин» /
  «Пропущенный звонок» (danger), a click calls back.
- **TURN: off.** `deploy.py turn` answered «10000: Authentication error» - the Cloudflare API token lacks
  the **Calls Write** right. Calls go over STUN only (the window says «прямое соединение - через строгую
  сеть может не пройти»): two people behind strict NATs may not connect. To turn it on: give the token
  Calls Write (dash.cloudflare.com -> My Profile -> API Tokens), `deploy.py turn`, then deploy staging and
  production again.
- Proof: `docs/superpowers/plans/verify_chat_calls.py` **0 of 13 gates on staging** (twice in a row;
  headless mayapy, two real accounts made and deleted, two callview windows with real pages, Chromium's
  fake devices, `--mute-audio --disable-gpu`): it rang for B **0.11-0.34 s** after A pressed; B's answer
  to both connected **0.90-0.99 s** (host/host - both in one process); **~70 KB a side in 3 s** (audio +
  video in); A's mute at B in 0.13-0.19 s; B hung up, A's window closed in 0.10-0.12 s; both got the call
  line (answered, 7 s); a second call declined closed A's window in 0.13 s, the line «Пропущенный звонок»;
  `turn_servers` STUN only. After the final review's fixes: **0 of 20 on staging** - plus a group of
  three: C joining a live call, all three pairs connected in **0.96 s**, bytes on all six directions
  (50-83 KB in 3 s each); B and C answering a group ring at the same moment, all pairs connected in
  **0.65 s**. `verify_chat_server.py all` **0 of 135 on staging** (new gates: the call line's text, a
  second join answers the view, back within 30 s the call is heard again and can be left; the four-way
  leave now one at a time - sent at once they raced, and a late leave left a stale `no_call` on its
  socket). production: (filled at merge). `verify_call_page.py` 0 of 17 (the page alone,
  three people). Picture `docs/superpowers/plans/chat_calls.png` (`render_chat_calls.py`).
- **Not seen in a GUI Maya**: real devices, the real screen picker, remote audio's autoplay in Maya's
  QtWebEngine, the burst over a QWebEngineView, the ring, two machines on different networks.

289. **Offscreen Qt with Chromium's GPU on segfaulted mayapy mid-call** (2 runs of 3: «context is marked as
     lost»). Headless call runs take `--disable-gpu --disable-gpu-compositing`, and `--mute-audio`: the
     fake microphone beeps on the animator's speakers. And `--use-fake-ui-for-media-stream` makes Chromium
     grant the media itself, so the page's own permission handler is never asked: a proof of the grant
     leaves it out.
