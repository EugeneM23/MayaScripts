# Voice and screen share - design (2026-10-10)

The animator (2026-10-10): «давай попробуем реализовать группу голосового чата
(как в дискорд) с возможностью шейринга экрана» and then «делай все до самого
конца я потом проверю». Approved in the brainstorm: a Cloudflare server ("the
simplest for me", «коорпаративный софт тут не нужна сильная приватность. Главное
это гибкость широкий функционал и простота использования»).

Nothing here touches Shared (ntfy.sh + temp.sh, files), Stash or the rest.
A new hub section **Voice** (Scene group, after Shared) and a new package
`maya_voice/`; the server is `voice_server/` in the repo, not in the payload.

## Goal and scope

- Voice rooms, like Discord channels: a list of rooms with who is inside, join
  and leave in one click, a roster with speaking / muted / deafened / sharing.
- Microphone: mute (not sent), deafen (incoming not played).
- Screen share: any member shares the primary screen; the others see it in a
  viewer window. Several members may share; the viewer shows the first sharer
  and the list can pick another.
- Identity: the name typed once (remembered). No accounts, no tokens.
- Not in v1: text chat, recording, history, push-to-talk, echo cancellation,
  end-to-end encryption, sharing a single window (the primary screen only),
  per-person volume.

## Architecture

### Server (`voice_server/`, Cloudflare Workers)

- `GET /` health; `GET /rooms` the lobby list; `GET /room/<name>` a WebSocket
  upgrade into that room.
- One **Room** Durable Object per room (`idFromName(room)`). It keeps the
  members in the WebSocket attachments (hibernation API), assigns each member a
  numeric id, relays media frames to everybody else, and rebroadcasts the
  roster. Nothing is written to storage.
- One **Lobby** Durable Object holds the list of non-empty rooms (name + member
  names). Rooms push an update on every roster change; entries older than an
  hour are dropped on read.
- Limits: 30 members per room; a message over 2 MB is refused by the room;
  room names `[a-z0-9][a-z0-9_-]{0,39}` (the Maya client lowercases and
  replaces spaces with `-`).

### Client (`SkeldarAnim/maya_voice/`)

Pure stdlib modules (testable without Maya):

| module | does |
|---|---|
| `protocol.py` | wire format: media frame header, control JSON, name and room cleaning, packet constants |
| `jitter.py` | per-sender jitter buffer, latest-frame holder, PCM mix |
| `gate.py` | voice activity gate: RMS threshold with a hangover, so the tail of a word is sent |
| `roster.py` | the room model from control messages; who spoke recently |
| `ws.py` | a WebSocket client (RFC 6455) over `socket` + `ssl`: handshake, masked frames, fragments, ping/pong, close |
| `session.py` | one room connection: a reader thread and a writer thread, an inbox the main thread drains, the lobby fetch |

Qt-bound modules (imported lazily, the rest of the package does not need them):

| module | does |
|---|---|
| `media.py` | `QAudioSource` (16 kHz, mono, S16; a fallback that downmixes and decimates by an integer ratio), `QAudioSink`, screen grab through `QScreen.grabWindow` to JPEG, the viewer window |
| `window.py` | the hub section: `build_panel()`, `show_window()`, `is_open()`, the single Qt timer that pumps everything on the main thread |

### Wire format

- Control messages are text frames: JSON with a field `t`.
  - client → server: `join {name}`, `state {muted, deafened, sharing}`.
  - server → client: `welcome {id, room}`, `roster {members:[{id,name,muted,deafened,sharing}]}`, `error {msg}`.
- Media messages are binary frames: header `!BHI` = type (`A` audio, `V` video),
  sender id (u16), sequence (u32), then the payload.
  - The server rewrites the sender id from the socket's own id, so a member
    cannot send as another.
- Audio: PCM s16le, 16 kHz, mono, 60 ms packets (960 samples, 1920 bytes).
  Only packets above the gate threshold are sent, plus a 3-packet hangover.
- Video: JPEG of the primary screen, at most 1280 px wide, quality 55, at most
  6 frames per second. The receiver keeps the newest frame per sender.

### Playback

- Jitter buffer depth 2 packets (120 ms). A missing packet within the window is
  played as silence; a late packet is dropped; a jump of more than 500 packets
  resets the buffer.
- Playback runs on the main thread: a timer writes one mixed 60 ms packet per
  due time into `QAudioSink`, which keeps its own small buffer.
- Deafen stops the writes; the buffers keep filling and are then dropped.

### Threads and Maya

- Socket I/O runs on two threads (reader, writer). They talk to the main thread
  only through queues.
- Everything Qt and every `cmds` call runs on the main thread, inside one Qt
  timer (30 ms). The lobby fetch runs on a short thread and returns through the
  same inbox.

## Error handling

- Connection lost: the session reports it; the panel shows «Reconnecting» and
  retries after 2, 4, 8 … seconds up to 30. The member list is cleared while
  offline.
- No microphone, no audio output, screen refused: a line in the status, no
  modal dialog (a modal blocks Maya's command port, see the bridge notes).
- Server errors (room full, bad name) show their text in the status.
- A failed send drops the oldest audio (the writer queue is bounded), never
  blocks the main thread.

## Verification

- Unit tests (stdlib, run with mayapy): protocol round trips and refusals, the
  jitter buffer (order, gaps, late packets, reset), the gate, the roster, the
  WebSocket client against a loopback server written in the test (handshake,
  masking, fragments, ping, close), the session with an injected fake socket,
  the panel with the recording `cmds` fake.
- Server tests: `voice_server/test/logic.test.mjs` (Node's `node:test`) for the
  pure functions (room and name rules, sender stamping, the lobby update).
  **Not run in this environment: Node is not installed here.** Run
  `npm test` in `voice_server/` after `npm install`.
- Headless check of the Qt audio devices in mayapy (no GUI, no port).
- The live behaviour (microphone, speaker, screen, the room) is the animator's
  to check: nothing here opens a GUI Maya or a command port.

## Open risks, measured later

1. Audio in Maya's process may stutter during heavy operations (a bake, a
   rebuild). If it does, the next step is a separate process for the voice
   client; the protocol already allows it.
2. The screen grab rate through Qt. The 6 fps cap is a guess until measured.
3. Cloudflare limits on message size and the WebSocket hibernation behaviour
   are taken from the docs, not from a live run.
