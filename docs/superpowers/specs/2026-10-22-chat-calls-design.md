# Chat calls: voice, video and screen sharing, up to 4 people

2026-10-22. The animator: «Можем прокачать наш месенджер добавить аудио видео звонки» (emoji first,
built the same day; calls in this spec). Asked and answered:

- **who**: a direct chat's two people, and a group chat's call of **up to 4**;
- **screen sharing**: yes, a whole screen or one window, instead of or beside the camera;
- **where**: the call has **its own floating window** in the hub's look, which folds into a small
  always-on-top tile.

## Measured first

Maya 2027 ships Qt WebEngine (`QtWebEngineWidgets`, `QtWebEngineCore`, `QtWebChannel`,
`QtWebEngineProcess.exe`). A headless probe in mayapy (`QT_QPA_PLATFORM=offscreen`, Chromium's
fake devices) loaded a page at an `https://` base URL and found:

- Chromium 122 (`QtWebEngine/6.8.3`), a secure context;
- `RTCPeerConnection` and `getUserMedia` present; an offer made; host and server-reflexive candidates
  through `stun:stun.cloudflare.com:3478`;
- codecs: Opus (audio), VP8, VP9, AV1 (video);
- `getUserMedia({audio, video})` answered both tracks.

Cloudflare TURN: `POST https://rtc.live.cloudflare.com/v1/turn/keys/<key id>/credentials/generate-ice-servers`
with the key's API token answers `iceServers` (STUN plus TURN over UDP 3478/443, TCP 3478/80, TLS
5349/443). The first 1,000 GB a month are free (shared with the SFU), then $0.05/GB; TURN carries
only the calls whose direct connection fails.

## How it works

**Media is WebRTC inside one Chromium web view per call**, running our own page that ships in the
plugin (`SkeldarAnim/assets/call/call.html`, `call.js`, `call.css`), loaded with an `https://skeldar.call/`
base URL so it is a secure context. Everyone in a call connects to everyone else (a mesh: at most 3
connections each). No media server.

**The set-up messages go through the chat's existing socket and Worker.** The Worker relays them to
the named person's sockets and stores none of them. Python owns the socket; the page talks to Python
through `QWebChannel` (`bridge` object: `signal(to, data)`, `state(json)`, and back
`deliver(from, data)`, `command(name, args)`).

**Connection servers** come from the Worker: `GET /v1/turn` answers `iceServers` made with the
Cloudflare TURN key, valid for 24 h, cached by the client until an hour before they expire. Without a
TURN key on the server, or when Cloudflare refuses, the answer is Cloudflare's STUN alone and the call
window says «прямое соединение - через строгую сеть может не пройти».

## Server (`server/chat/worker.js`, the `Studio` Durable Object)

- Table `calls (id, chat, by, kind, started_at, answered_at, ended_at)`, `call_members (call, uid,
  joined_at, left_at)`.
- Socket frames from a member of a writable chat:
  - `call_start {chat, kind: "audio"|"video", cid}` - refused when that chat already has a live call
    (the answer names it: join it instead). A group of any size may call; at most 4 may be *in* it,
    and the 5th `call_join` is refused `call_full`;
  - `call_join {call}`, `call_leave {call}`, `call_decline {call}`;
  - `call_signal {call, to, data}` - `data` an object of at most 64 KB, relayed to `to`'s sockets
    as `{type: "call_signal", call, from, data}` when both are in the call (or `from` is calling and
    `to` is being rung).
- Events to every member of the chat (stored, with `seq`, like messages): `call` with
  `{id, chat, by, kind, state: "ringing"|"live"|"ended", members, started_at, answered_at, ended_at}`.
- Ringing: nobody joins within **45 s**, or everybody rung declines → `ended` with no answer. A call
  ends when its last member leaves, or a member's sockets are all gone for 30 s (the alarm sweeps).
- When a call ends the server posts a message in the chat from its starter: kind `call`,
  `{call, kind, answered, seconds}`; the feed draws «Пропущенный звонок» / «Звонок · 5 мин».
- `GET /v1/turn` (signed in): the ICE servers as above. The TURN key id and token are Worker secrets
  `TURN_KEY_ID`, `TURN_KEY_TOKEN`; `deploy.py` gains `turn` to create a key through Cloudflare's API
  (`POST /accounts/<id>/calls/turn_keys`) and store both. If the animator's API token lacks Realtime
  rights, `deploy.py turn` says so and how to add them; calls still work, STUN only.

## Client

| module | does |
|---|---|
| `maya_chat/calls.py` (stdlib, pinned) | the call records and events parsed strictly; the client state machine (idle, ringing in, ringing out, joining, live, ended) as a pure function of events and presses; who connects to whom (the later joiner sends the offer); the 4-person rule; ring and missed-call texts |
| `maya_chat/callview.py` (Qt) | the call window (look D, as `maya_hubwindow` frames it), the web view and its `QWebChannel` bridge, permissions (camera, microphone, screen) granted only to our page's origin, the screen/window picker, the folded tile, the incoming-call card, the ring sound |
| `assets/call/call.html`, `call.js`, `call.css` | the WebRTC mesh: one `RTCPeerConnection` per other person, `getUserMedia`, `getDisplayMedia`, a tile per person, the speaking light from an `AnalyserNode`, ICE restart on a dropped connection, device lists |
| `maya_chat/session.py` (modify) | the new frames and events, `start_call`, `join_call`, `leave_call`, `decline_call`, `call_signal`, `turn_servers()`; `state.calls` |
| `maya_chat/window.py` (modify) | the call button in a chat's header (a live call: «Присоединиться»), the call line in the feed, the list row's call marker |

**The call window**: title row (the chat's name, the call's time), a grid of tiles (1, 2, 2×2), each
with the person's name, a muted-microphone mark and the speaking light (the accent ring, as the hub
lights a card); a screen share takes the big tile with the others in a strip. Buttons: microphone,
camera, screen, settings (microphone and camera chosen from the page's device list, remembered in
`skeldarChatCallMic` / `skeldarChatCallCam`), fold, hang up (danger). Folded: a 240 px tile of the
speaker, always on top, a click unfolds it. Its place and size are remembered
(`skeldarChatCallPos` / `Size`). One call at a time: starting or accepting another ends this one,
after a question.

**An incoming call**: a ring (`maya_hubsound`, a new `ring` sound, looped until answered or 45 s) and
a card over the viewport where the message cards stand, with the caller's avatar and three buttons:
Accept with voice, Accept with video, Decline. With the chat window open the chat's header shows it
too. The card plays regardless of the interface-sounds switch, as the message chime does.

**Screen sharing**: Qt 6.8's `QWebEnginePage.desktopMediaRequested` hands our window the screens and
windows; our own picker (look D, thumbnails where Qt gives them) chooses one; the share replaces the
camera's track (`replaceTrack`), and turning it off puts the camera back.

**Interface animations off**: the window and the card appear and go at once; the speaking light is
on or off with no fade.

## When things go wrong

- No camera, or its permission refused: the call goes on with voice; the camera button says why.
- No microphone: the call is refused before it starts, by name.
- A peer connection fails: ICE restart, then a rejoin offer; after 20 s that person's tile says
  «нет соединения».
- The socket drops: the call keeps its media; set-up messages wait in the session's outbox only for
  the call's live time, never across a restart.
- TURN refused or absent: STUN only, said in the window.
- The 5th person: refused `call_full`, said in the chat's header.

## Testing

- `tests/test_chat_calls.py`: records, the state machine, who offers to whom, the 4-person rule.
- `tests/test_chat_callview.py` (offscreen): the window builds with a fake page, buttons drive commands,
  the incoming card, the folded tile, permissions granted only to our origin.
- `docs/superpowers/plans/verify_chat_server.py` phase `calls` against staging: start, ring, join,
  signals relayed only between members, decline, the 45 s ring end, the missed-call message, the 5th
  join refused, `GET /v1/turn`.
- `docs/superpowers/plans/verify_chat_calls.py`: two accounts, two web views in one headless mayapy
  with Chromium's fake devices, connected through the staging Worker: the call goes live, audio and
  video bytes flow both ways (`getStats`), a screen share replaces the video track, hang up ends it,
  the call message lands in the chat.

## Not built

More than 4 in a call (Cloudflare's SFU), recording, calls to people outside a chat, noise
suppression beyond Chromium's own, background blur, a call from a viewport's right-button menu.
