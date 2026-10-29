# Screen share: the whole screen in one press, its own window, drawing over it (2026-10-29)

The animator, after a call: «1 - Сейчас в нашем месенджере во время стрима экрана не показываются
приложения которые я открываю даже если у меня включена опция стриминга полного экрана. 2 -
возможно ли что бы участники разговора могли рисовать по экрану того кто стримит экран?» and, a
moment later: «при стриме экрана камеры участников превращаются в узкую полоску снизу, но так не
должно быть давай мы камеры будем показывать в отдельном окне а стрим экрана в своем (как в
дискорде)».

Asked and answered: the apps were missing **for them too**, in their own tile, and they had picked
the first row, «Entire screen»; the stream window opens **by itself** as soon as a share starts;
strokes **fade after a couple of seconds**.

## 1. What the capture actually does — measured, five ways

Before any fix (`superpowers:systematic-debugging`), the capture was measured on this machine. The
probes are in the session scratchpad; their numbers:

| what was run | result |
|---|---|
| our page's own `getDisplayMedia` + `selectScreen(0)`, standalone mayapy | `displaySurface: "monitor"`, 2560×1600, the whole desktop |
| a window opened AFTER the share started | in the captured frame (222 793 px of its colour) |
| end to end, two call pages | the other side's `<video>` shows that window, 2304×1440 |
| the sender throttled to 3000 / 1200 / 500 / 200 kbit | the new window reached the other side in 0.4-0.5 s every time (6 fps at 200 kbit) |
| the same probe **inside a GUI Maya** | `surface: "monitor"`, Unreal's viewport and all; the AFTER window in the frame |

So the capture is not the bug: with «Entire screen» picked, the whole monitor is streamed, live,
including applications started after the share and hardware-accelerated ones, down to 200 kbit.
The symptom is **not reproducible** here. What is addressed instead is the class it belongs to —
the pick, and a capture that stalls — and the next occurrence is made self-diagnosing.

### What changes

- **One press shares the whole screen.** The screen button no longer opens a list. One monitor →
  it is taken at once; several → a short menu of screens only, labelled «Весь экран 1/2…» (never
  Chromium's English "Entire screen"). A **window** is shared through the button's right-button
  menu («Показать окно…»), which is also where the window list lives now. The old menu mixed one
  English screen row with eight window titles under two section headings: the only way left to
  share a window by accident is to ask for one.
- **The call window says what is being captured**: «Экран 2560×1600» or «Окно: Atone - Unreal
  Editor», from the track's own `displaySurface` and settings, for a few seconds, and in the
  Script Editor. A share that is not what was meant is now visible at once.
- **A stalled capture heals itself.** The page watches the local screen video
  (`requestVideoFrameCallback`); no new frame for `STALL_MS` (5 s) while the track is still live is
  reported as `stalled`. The window then takes the capture again **with the same source and no
  menu** (the last pick is remembered) and says so; twice at most, then it only says the picture is
  frozen. This covers the class the symptom would belong to — a desktop-duplication or WGC capture
  that dies on a full-screen transition or a driver reset and leaves the last frame standing.

## 2. The stream in its own window

Measured in Maya first, because it decides the design: Qt 6.8.3 is Chromium 122 and
**`documentPictureInPicture.requestWindow` works inside Maya** — it failed only for want of user
activation, and a synthetic `QMouseEvent` into the view's focus proxy gives it (measured: "open").
Qt routes the PiP window through `QWebEnginePage.newWindowRequested`, so the window is **ours**:
our own look-B frame, our title, our place.

That is the one road that needs **no second capture and no re-encode**: the live `<video>` element
is *moved* into the second document, media and all. (The other road tried, `window.open` +
`adoptNode`, opened the window but the video did not arrive: "no video".)

- A share starting — anyone's — opens the stage window by itself and moves the screen tile into it.
  The call window's grid goes back to a plain camera grid: **the 96 px strip is gone**.
- The stage window is dragged by its title, resized, and remembered
  (`skeldarChatStagePos` / `skeldarChatStageSize`); closing it puts the tile back in the grid; the
  share ending closes it.
- Several shares at once: one stage window per screen tile is not built — the first share takes the
  stage, a second stays in the grid.

## 3. Drawing over the shared screen

Everyone in the call may draw over the stream, the sharer included; every stroke is seen by
everyone.

- The pen lives **in the page**, in the screen tile's corner, so it travels into the stage window
  with the tile and gives the page its own user gesture.
- A stroke is carried in **normalised coordinates** (0..1 of the shared frame), so it lands in the
  same place on every window size and every screen resolution.
- Points are batched every `SEND_MS` (60) and sent through the call's existing live relay
  (`send(uid, {draw: …})` → `call_signal`, never stored), which already carries mic and camera
  state. A stroke is a few hundred bytes, far under the server's 64 KB.
- A stroke is drawn in **its author's own colour** (`maya_chat.look.user_colour`, the avatars'
  palette), handed to the page with the names.
- It holds `HOLD_MS` (1200) and fades over `FADE_MS` (1800): about three seconds, then it is gone
  and nothing has to be cleared. The canvas keeps no history: a stroke that has faded is dropped.
- Drawing is off until the pen is pressed, so a drag over the stream does not draw by accident.

## Not built

- Several stage windows for several simultaneous shares.
- Strokes that stay until cleared (the animator chose fading; the other half of that question is a
  switch, which would be one flag).
- Drawing over a camera tile, shapes, text, an eraser, undo.
- The sharer's own cursor drawn to the others.
