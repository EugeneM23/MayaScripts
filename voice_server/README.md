# Skeldar voice server

The server behind the Maya plugin's **Voice** section: group voice rooms and
screen share. Cloudflare Workers with two Durable Object classes:

- `Room` — one per room name. Keeps its members, gives each a numeric id,
  relays media frames, rebroadcasts the roster. Nothing is stored.
- `Lobby` — one for the whole server. Keeps the list of occupied rooms and
  their member names, for the Voice section's room list.

The rules shared with the Maya client are in `src/logic.js`; the wire format
is described in `docs/superpowers/specs/2026-10-10-voice-screen-design.md`.

## Deploy (one time)

You need a Cloudflare account (free works for the Workers and Durable Objects
used here; check the current plan limits on cloudflare.com).

```bash
cd voice_server
npm install
npx wrangler login
npx wrangler deploy
```

`wrangler deploy` prints the address, for example
`https://skeldar-voice.<your-subdomain>.workers.dev`. Type that address (without
`https://` is fine) into the **Server** field of the Voice section in Maya.

Check it is up: open `https://skeldar-voice.<your-subdomain>.workers.dev/` in a
browser. It answers `skeldar voice ok`. `/rooms` answers the lobby as JSON.

## Test

```bash
npm test          # the pure rules, with Node's built-in test runner
npm run dev       # a local server (wrangler dev) for the Maya client
```

`npm test` needs Node 18 or newer. The Durable Objects run only under
`wrangler dev` or a deploy; they are not covered by `npm test`.

## Limits

- 30 members per room (`MAX_MEMBERS`); the 31st gets `room full`.
- A message over 2 MB is dropped (`MAX_MESSAGE_BYTES`); a video frame is well
  below that.
- Room names: lowercase letters, digits, `_` and `-`, up to 40 characters.
- The lobby forgets a room after a day with no update (`LOBBY_MAX_AGE_MS`).

## What it does not do

No accounts, no tokens, no encryption beyond the TLS of the connection, no
recording, no history. Anyone who knows the server address and a room name can
join that room. This is intentional for the studio's use: the goal is ease of
use, not privacy.
