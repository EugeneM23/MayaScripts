# Voice and screen share - implementation plan (2026-10-10)

Spec: `docs/superpowers/specs/2026-10-10-voice-screen-design.md`.
Branch `feature/voice`, worktree `C:/!!!Work/MayaScripts-voice`. Commits stay
local; nothing is pushed, no build is made (the animator asked to check first).

1. [x] `protocol.py` - frame header, control JSON, name and room cleaning.
2. [x] `jitter.py` - jitter buffer, latest frame, PCM mix.
3. [x] `gate.py` - voice activity gate with hangover.
4. [x] `roster.py` - room model and speaking detection.
5. [x] `ws.py` - stdlib WebSocket client.
6. [x] `session.py` - connection threads, inbox, outbox, lobby fetch.
7. [x] `media.py` - Qt audio and screen (lazy Qt, headless-safe import).
8. [x] `window.py` - hub section panel, one Qt timer, viewer.
9. [x] Hub registration: `maya_hub.SECTIONS` row `voice`, icon `mic` in `maya_hubicons`.
10. [x] Payload: `maya_voice` in `install._PAYLOAD`.
11. [x] Server: `voice_server/` - Worker, Room and Lobby objects, pure `logic.js`,
    `wrangler.toml`, Node tests, README.
12. [x] Unit tests for every pure module and the panel with a fake `cmds`.
13. [x] Headless Qt audio device check in mayapy (`docs/superpowers/plans/voice_spike_headless.py`).
14. [ ] Live checks in Maya and a deploy to Cloudflare - the animator's.
