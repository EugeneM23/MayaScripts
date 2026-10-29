# A call that is heard, and a share that shows the right screen (2026-10-29)

The animator, after the morning's screen-share work:

> задача для мессенджера - Сейчас когда созваниваемся то не слышно собеседников. Но становиться
> слышно когда шарим рабочий стол. Когда я свой рабочий стол шарю то у меня не видно маи а у
> коллеги все норм. Еще нельзя сейчас рисовать по окну стрима

Three reports. Two of them had causes that could be measured, and both are fixed here. The third
could not be reproduced in three different ways and is left for the animator's own words rather
than a guess.

## 1 Nobody was heard until a screen was shared

**The cause, measured.** A remote participant's voice was played by the tile's `<video>` element,
and the stream handed to that element carried the peer's video track beside the audio one. A
`<video>` whose MediaStream holds a live video track that has never delivered a frame stands at
`readyState 0` and renders **nothing at all** - not the picture, and not the audio track beside
it. A voice call is exactly that case (the video transceiver exists, nobody sends on it), and so
is every camera turned off.

Two pages wired to each other in a headless mayapy, the voice arriving and the element's own
playback as the instrument (a rendering element advances its `currentTime`; one that renders
nothing stays at 0):

| what the remote side was doing | playback in 4 s of real time |
|---|---|
| a voice call, no camera either side | **0.000 s** |
| its camera on, frames arriving | 4.026 s |
| its camera off again | **0.000 s** |
| the same audio track in an `<audio>` of its own | 4.010 s |

So the moment any frame arrives - a camera, **a shared screen** - the element starts and the voice
comes with it. That is the animator's «становится слышно когда шарим рабочий стол», exactly.

**Why no gate caught it.** Every call verify measured BYTES on the wire (`audio_in`), which were
always there, and every one of them ran with a camera on (Chromium's fake device gives frames) and
with `--autoplay-policy=no-user-gesture-required` on the command line. The one case nobody tested
was a voice call. Bytes arriving is not being heard.

**The fix.** A remote voice gets an `<audio>` element of its own, and that element lives **outside
the tiles**, in a `#sinks` div of the page:

- `sink(uid)` / `dropSink(uid)`: one per remote participant, made on demand, gone with the tile.
- `wear(el, tracks, muted)`: the element is left alone while it already holds those very tracks -
  setting `srcObject` again rebuilds the player and the picture blinks.
- `showStream(uid, stream, mine)` hands the VIDEO tracks to the `<video>` (always muted now) and
  the AUDIO tracks to the sink. Nothing of the picture can hold the voice up any more.
- The sink is outside the tiles on purpose: a screen tile travels into the stage window, and what
  is heard must not depend on where the picture lives. Gated live.

The local tile gets no sink at all - nobody hears themselves.

The speaking light is untouched: it reads its own analyser on the track (`watchLevel`).

## 2 The share showed a screen the animator was not working on

**The cause, measured on the animator's own machine.** Chromium's screen list offers **one** row,
"Entire screen", and it is the **external monitor** (LG ULTRAFINE 3840×2160). The laptop panel
(NE180QDM-NM2 2560×1600), which is the primary screen and the one their Maya stands on (measured:
their Maya's window at (-7, -7, 1714, 1026), on DISPLAY1), is not offered at all - Chromium cannot
capture it here. Our own rule from the morning ("one screen row → take it with no menu") therefore
shared, with one press and no question, a monitor with nothing of theirs on it.

The line said only «Экран 2560×1440» - which is the CONSTRAINED size (our `SCREEN` ideal), not the
monitor's, so it could not even hint at the mistake.

Three more measurements shaped the fix:

- `track.getCapabilities().width.max/height.max` is the captured monitor's **native** size
  (3840×2160 here) while `getSettings()` gives the downscaled one. That is the only thing that
  says which monitor a capture is - Chromium names none of them.
- The window list **does** carry the animator's Maya, under the title Windows shows for it.
- A **window** capture keeps its picture when another window is put over it: covered, the picture
  stayed live (46 colour buckets, 0 dark pixels) and the covering window's own colour was 0 % of
  the frame. So sharing Maya's own window is live and occlusion-proof, not a half-answer.

**The fix.**

- The page reports the capture's native size (`nw`, `nh`) beside the constrained one.
- `capture_screen(capture)` finds the monitor by matching that size against Qt's screens; two
  monitors of one size is no answer rather than a guess.
- `capture_text` names it: «Экран LG ULTRAFINE 3840×2160».
- `_wrong_screen` adds, when the captured monitor is not the screen the call window stands on:
  «— Maya на другом экране; правой кнопкой по кнопке экрана → «Окно Maya»».
- The screen button's right-button menu gains a first row **«Окно Maya»**, which takes Maya's own
  main window by the title Windows shows for it (`window_title`, read through Win32: Qt's
  `windowTitle()` carries the `[*]` placeholder where Windows draws the modified mark, so it is a
  different string). Two Mayas open and no title to go by is no answer - sharing the other one's
  window would be worse than sharing nothing.
- The menu's window rows are elided to 46 characters: a Maya row was its title AND the scene's
  full path.

**Left to the animator.** Whether ONE PRESS should share Maya's window when the only screen
Chromium offers is not the screen they are on. Today the press still shares that screen and says
so. It is their call, since a window share shows only Maya and the morning's rule was deliberately
"a window only when it was asked for by name".

## 3 Drawing over the stream window

Not reproduced, in three ways:

1. Offscreen, a real `_StageWindow` with a fake capture: the pen is there and hit-testable
   (`elementFromPoint` answers `BUTTON.pen`), a real Qt press on it turns drawing on, and a drag
   draws a stroke of 1387 ink pixels.
2. **Live in a GUI Maya with a real screen capture**: the same, 2931 ink pixels, and the stage
   window's own picture live and moving.
3. Both directions between two peers: a viewer's stroke reaches the sharer and is drawn over their
   copy (1371 ink pixels on both sides), and the sharer's reaches the viewer.

So the machinery works. What is left is what the animator did - the pen is an unlabelled 28×28 ✎
in the corner of the picture, and a stroke fades after about three seconds (their own ask). Asked
rather than guessed at.

## Proof

- `docs/superpowers/plans/verify_call_audio.py` - **0 of 18 gates**, headless mayapy, no Chromium
  flags of the verifies' kind (no fake device, no autoplay policy): the voice rendered in a voice
  call, with a camera, with the camera off again, while a screen is shared and after it stops; the
  picture muted and audio-free; nobody hearing themselves; the analyser still on the remote track;
  a peer who leaves taking their sink. On the build before: **7 gates fail**, the first of them
  reading 0.000 s of playback.
- `docs/superpowers/plans/verify_call_screen_live.py` - **0 of 16 gates, live in a GUI Maya** with
  a real screen capture: the monitor named by its native size, the warning that it is not this
  window's screen, «Окно Maya» sharing Maya's own window with a live picture, the other side's
  voice rendered (4.020 s in 4 s) and still rendered while its tile is in the stage window.
- `docs/superpowers/plans/verify_call_stage.py` - **0 of 27 gates, live** again: the stage window
  and the drawing are untouched.
- `verify_call_page.py` 0 of 18, `verify_call_devices.py` 0 of 25, 702 chat unit tests (the one
  failure is the known `test_chat_deploy.Keys`, which reads this machine's own saved keys).
- `tests/test_chat_callview_screens.py` - 26 tests: the titles, Maya's row, which monitor, the
  line, the menu.

## Not built

- One press sharing Maya's window (the question above).
- A screen Chromium does not offer cannot be shared as a screen by any road we have; the window
  list is the way to it.
- The capture is still downscaled to the `SCREEN` ideal (2560×1440) - a 4K monitor loses a third
  of its pixels for the colleague. Nobody asked, and raising it costs encoder time.
