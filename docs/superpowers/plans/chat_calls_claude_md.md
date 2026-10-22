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
  gone 30 s leaves. When a call ends the server posts the **call line**: a message from its starter with
  `call: {id, kind, answered, seconds}`. `GET /v1/turn`: Cloudflare TURN credentials
  (`TURN_KEY_ID` / `TURN_KEY_TOKEN` secret bindings, port 53 dropped), else Cloudflare's STUN, `turn: false`.
- **Client**: `maya_chat/calls.py` (stdlib: `merge`, `of_chat`, `mine`, `ringing_for`, `can_join`,
  `start_args`, `peer_commands`, `note_text`); `records.call` / `call_note`; `Session.start_call /
  join_call / decline_call / leave_call / call_signal / turn_servers` (cached to the ttl), `state.calls`.
  Who offers: the one who JOINS offers to every member already in; the starter never offers.
- **The call page** (`assets/call/call.html|css|js`, `maya_chat/callpage.py`): a WebRTC mesh in Maya's
  Chromium (QtWebEngine), loaded at base URL `https://skeldar.call/`, the bridge over QWebChannel
  (`qwebchannel.js` from Qt's resource). Camera and microphone granted by `CallPage` to that origin only;
  the screen through `screen_requested`. The joiner makes the transceivers, the answerer puts its tracks on
  the offer's (`attachLocal`): with its own `addTransceiver` the answerer sent nothing. Commands wait for
  `start`; a signal before `start` is held by the window and replayed.
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
  `turn_servers` STUN only. production: (filled at merge). `verify_call_page.py` 0 of 17 (the page alone,
  three people). Picture `docs/superpowers/plans/chat_calls.png` (`render_chat_calls.py`).
- **Not seen in a GUI Maya**: real devices, the real screen picker, remote audio's autoplay in Maya's
  QtWebEngine, the burst over a QWebEngineView, the ring, two machines on different networks.

289. **Offscreen Qt with Chromium's GPU on segfaulted mayapy mid-call** (2 runs of 3: «context is marked as
     lost»). Headless call runs take `--disable-gpu --disable-gpu-compositing`, and `--mute-audio`: the
     fake microphone beeps on the animator's speakers. And `--use-fake-ui-for-media-stream` makes Chromium
     grant the media itself, so the page's own permission handler is never asked: a proof of the grant
     leaves it out.
