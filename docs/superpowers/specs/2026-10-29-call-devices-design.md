# A call survives its microphone: the device chosen, lost, switched (2026-10-29)

The animator: «У меня случился баг при переключении беспроводных наушников. мая говорит что
микрофон не найден и отклоняет звонки и я ничего не слышал когда мне звонили».

## What was wrong — measured, not guessed

Their own prefs hold the first half of it
(`C:/Users/MY PC/Documents/maya/2027/prefs/userPrefs.mel`):

    -sv "skeldarChatCallMic" "11ead41f8b74a1272f91217584631128375bd0bf9928bd8a2ef9f048889efc21"

A microphone they once picked from the call window's devices menu, kept as the deviceId Chromium
gave for it. And **our call page's profile is off the record, so Chromium salts its device ids
afresh every Maya session** — probed twice in a row in mayapy, the same Realtek microphone:

| run | its deviceId |
|---|---|
| 1 | `74fe12fd2e1f…` |
| 2 | `c1da5ef941ce…` |

The page then asked for that id **exactly** (`call.js`, `userMedia` / `camConstraints` /
`COMMANDS.devices`):

```js
const audio = S.devices.mic ? { deviceId: { exact: S.devices.mic } } : true;
```

and a `deviceId` that is not there, asked as `exact`, raises `OverconstrainedError` — measured on
this machine and on Chromium's fake devices alike. The same id asked as an **ideal** (no `exact`)
is honoured when the device is there (`same: true`) and **falls back to the default by itself**
when it is not.

From there, two more rules finished the call off:

- `COMMANDS.start` set `S.error = "Микрофон недоступен: " + e.name` and **returned** — no peer
  connection was ever built, so nothing was sent and, the part that matters,
  **nothing was heard**;
- `callview._page_state` read that error and called `fail()`, which **leaves the call on the
  server** and closes the window. From the other side that is a decline.

So: after choosing a microphone once, every call in every later Maya session was declined with
«Микрофон не найден», in or out. Switching the headphones is what made them pick a device; the
stored id was doomed on the next start whatever they switched to.

## The rules now

1. **A remembered device is a wish, never a demand.** The page resolves it against the current
   `enumerateDevices` list: the id if it is still there, else the first device whose **label**
   matches the remembered label, else nothing — and asks for it as an ideal. So a re-salted id, a
   re-plugged device and a device that is gone all land on something that works.
2. **The window remembers the label too** (`skeldarChatCallMicLabel`, `…CamLabel`), which is what
   survives a new session. The id alone is kept for the one session it belongs to.
3. **A call without a microphone is still a call.** `getUserMedia` for audio failing no longer
   stops `start`: the mesh is built, every voice is heard, the page reports `nomic` with the
   reason, the microphone button shows muted, and the line says «Микрофон не найден (…) — вы
   слышите остальных, но вас не слышно». An audio transceiver is added by kind either way
   (`addTransceiver(audio || "audio")`, already so), so the others still reach us.
4. **A microphone never leaves a call.** `fail()` on a media error is gone; the window says it and
   stays in. The only thing that ends a call is the call ending.
5. **A device change is followed** (`navigator.mediaDevices.devicechange`, and the track's own
   `ended`): the list is read again (so the menu is current), and when the microphone in use has
   gone — or we had none — the page takes what rule 1 now answers and `replaceTrack`s it into every
   peer. That is the live headphone switch: it used to leave a dead track sending silence.
6. **The camera follows the same three rules**, including «a camera that cannot start does not cost
   the microphone» (they were one `getUserMedia` before, so either loss took both).

## What is not changed

- The output device. Chromium plays the remote voices to the system default and follows it; the
  ring is a fresh `QSoundEffect` per ring, so it is built on whatever is default then. What a
  device switch may leave stale is `maya_hubsound`'s **cached** pools (the chat chime, drag,
  delete): those effects are made once a session. `QMediaDevices.audioOutputsChanged` exists in
  this Qt, so the pools are dropped when the outputs change and the next play builds them on the
  new device — a cheap guard, and the one thing here that **cannot be shown broken or fixed
  without the hardware**: a headphone switch is not something a headless run can do.
- An output picker in the devices menu (`setSinkId` is there). Not asked for; say so if the
  animator wants to choose where a call is heard.

## Proof

- `tests/test_chat_calls.py`, `tests/test_chat_callview*.py`: the labels stored and passed, no
  `fail()` over a media error, the devices menu.
- `docs/superpowers/plans/verify_call_devices.py` — **0 of 25 gates**, three pages in one
  headless mayapy as `verify_call_page.py` does: `exact` on a dead id raises
  OverconstrainedError (the root cause, pinned); a page started with that id connects and
  carries audio both ways; the remembered label lands on the device it names; a `devicechange`
  and an `ended` track take the other microphone into the peer and the audio keeps flowing; a
  page whose audio is refused joins, hears both others, says so, is muted, and is heard as soon
  as its button takes a microphone; a refused camera leaves the microphone alone.
  **The same verify on the build before: 16 of 25 failed**, every one with
  «Микрофон недоступен: OverconstrainedError» and no peers at all.
- `verify_call_page.py` 18/18 and `verify_chat_calls.py` 0 of 20 on staging, both again.
- 12451 unit tests (the known `test_chat_deploy.Keys` failing).
- **Not seen in a GUI Maya**: a real headphone switch is the animator's.
