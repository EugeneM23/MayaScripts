# Taking our Qt down before Maya finalises Python

2026-11-02. The animator: «Посмотри логи маи за послении пару дней если такое возможно
мая начала очень часто вылетать. Не связано ли это с нашим плагином?» — and then, on the
answer, «Да, починить».

It was ours. This is what was measured, what the cause is, and what the cure does.

## What the logs say

451 dumps in `%TEMP%` (`MayaCrashLog<YYMMDD>.<HHMM>.dmp`; Maya writes no readable log).
Parsed by hand — there is no debugger on this machine; the recipe and its traps are in the
`maya-minidumps-by-hand` memory.

October, GUI Maya alone: **256 crashes, 244 of them one signature** — an ACCESS_VIOLATION in
`shiboken6.abi3.dll` (PySide's binding layer), always on the **main thread**, reading a
near-null address, at three offsets (`+0x5bb4c` 181×, `+0x64c60` 58×, `+0x516da` 22×).

**The signature changed on 2026-09-29/30.** Before: `Qt6Gui.dll` and `pyside6.abi3.dll`,
1–5 a day and not every day. After: shiboken, every day, climbing — 10–11 in early October,
**32 on the 16th**, 17 on the 21st and 22nd, 20 on the 30th, 9 on 1 November. Median session
at the crash 52 min; 29 of the 244 under five minutes (Maya restarted and crashing again).

**227 of the 244 have the C runtime's exit handlers on the faulting stack**, the chain reading

    _execute_onexit_table → ~QObject → ~QObjectPrivate → ~QMetaObject::Connection
    → PySide's signal machinery → shiboken reads 0

so Maya crashes **as it closes**. The other **26 are mid-session** — the ones that lose work,
13 of them on 30 October — and their stack names itself completely:

    QTimer::timerEvent → QMetaObject::activate → QObject::qt_static_metacall
    → PySide::SignalManager::callPythonMetaMethod → PyGILState_Ensure
    → call the Python slot → shiboken reads 0

a timer tick delivered to a Python slot whose receiver was gone.

Maya's crash handler writes the dump and then **exits 0**, which is why Windows reports a
clean exit and only the dump betrays it.

## The cause

The plugin attaches Python to Maya's own Qt objects and detaches none of it:

| | 2026-09-20 | 2026-09-29 | 2026-10-15 | 2026-11-01 |
|---|---|---|---|---|
| `.connect(` | 13 | 20 | 103 | **261** (against 17 `.disconnect(`) |
| QTimers | **0** | 2 | 29 | **82** |
| event filters | **0** | 2 | 21 | **38** |

Before 29 September there were no timers and no event filters at all — which is the day the
crash signature changed. Beyond those counts: graphics effects left on Maya's own controls
(the hover glow), `destroyed.connect(<python callable>)` in five places, Maya's own Channel
Box and Attribute Editor held **inside our frameless window** (the animator runs the side
panel at the right edge), and our own windows parented to Maya's main window. And the hub,
scene tabs, the Pose Library and the AT bar are saved in the active workspace, so all of it
comes up at **every** Maya start without the animator pressing anything.

There was **no shutdown cleanup anywhere in the plugin** — no `kMayaExiting`, no
`aboutToQuit`, no `atexit`. Python finalises first; Qt then destroys those objects and PySide
calls into dead Python. The teardown functions themselves mostly existed already
(`maya_sidepanel.drop_edge`, `maya_timebar.drop_edge`, `maya_viewportbar.remove_all`,
`maya_windowlight.stop`, …) — nothing ever called them at exit.

**Reproduced** before anything was written: a throwaway Maya with its own `MAYA_APP_DIR` and
the animator's own switches → quitting wrote `MayaCrashLog261102.0436.dmp`, the identical
offset `shiboken6+0x5bb4c`, `rcx=0`, the same chain; the same Maya **without** the plugin →
no dump.

## The cure

`SkeldarAnim/maya_shutdown.py` (stdlib at import; a payload row) and one
`MSceneMessage.kMayaExiting` hook, armed from `maya_hub.build()` — which is what Maya replays
at every start, so it is armed in every session the interface comes up in.

`PLAN` is an ordered tuple of `Step(module, function, what, phase)` over three phases:

1. **GIVE_BACK** — Maya's own widgets out of ours while both still live: the Graph Editor
   (`maya_graphoverlay.mode.disable`, which also disconnects `frameSwapped` from Maya's
   canvas), the Channel Box and Attribute Editor (`maya_sidepanel.drop_edge`,
   `maya_channelbox.unmount`), the time slider (`maya_timebar.drop_edge`), Maya's icons and
   sheets (`maya_viewportbar.remove_all`/`unwatch`, `maya_mainbar.remove`/`unwatch`).
2. **STOP** — nothing of ours may tick while Maya tears itself down: the window light's 50 ms
   poll, the camera watch, a camera flight, the centre-of-mass engine, the chat's socket and
   calls, the sound pools.
3. **DESTROY** — ours destroyed by us, not by Qt after Python has gone: the floating section
   windows, the edge rail, the hub's skin (`maya_hub.drop_skin`, new — what `rebuild` already
   did on its own), then **every remaining top-level window of ours**.

Two rules hold it up, and the tests pin both:

- **Only what is standing.** A step is looked up in `sys.modules` and **never imported** —
  importing `maya_chat` here would start the chat as Maya closes.
- **GIVE_BACK before DESTROY.** The side panel's own docstring says why: «a host deleted with
  a form inside would delete Maya's editor». Every step is guarded, so one refusal cannot
  strand the rest.

Decisions worth recording:

- **A widget is ours when its Python CLASS is** (`ours(type(w).__module__)`: the root starts
  with `maya_`). Not by `objectName`: Maya's own popups for our `cmds` controls are top-level
  too and are named after them (`skeldarWalkPreset`, `skeldarCamShakeDecay` — an `optionMenu`'s
  popup window), and deleting those would be deleting Maya's.
- **Our workspaceControls are deliberately NOT deleted.** Maya saves the workspace at exit; a
  deleted control would not come back at the next start. The skin inside the control is
  destroyed, the control is left.
- **Timers are stopped, not hunted.** `stop_timers` walks our own widgets and stops every
  active `QTimer` under them, destroying nothing — it costs nothing and cannot upset Maya,
  and it closes the mid-session mechanism at exit too.
- **The installer runs the same teardown before `purge_modules`** (`install._take_qt_down`).
  That *is* the mid-session half: a dropped module's timer firing into a slot that is gone.
  What it takes down, `rebuild_interface` and `rebuild_open_hub` bring back, deferred, as they
  already did for the Time Bar and the side panel.
- The hook's id lives on `sys` (`_skeldar_shutdown`), not in a module global, so an install
  that purges our modules cannot register a second one — trap 111's rule.

## It does not cure the exit crash

Four attempts, each measured in a throwaway Maya (`verify_shutdown.py`, phase `armed`), each
still writing a dump at the identical offset:

1. The hook with the named steps, the timers stopped and our top-level windows swept.
2. Plus `sweep_widgets` over every widget of ours anywhere (32 of them were standing
   re-parented under `MayaWindow` after step 1 — the whole Time Bar strip with its ten
   timers and its `DragKeys` filter, the side panel with its grips and burst overlay, the
   skill bar's rows, the scene tabs bar) and `drop_qt_state` over the Qt our own
   `sys._skeldar_*` state holds (the `QMediaDevices` watcher connected to a Python function,
   a `QuitFilter` on Maya's main window, the Stash's timer). Measured afterwards: **0 of our
   widgets, 0 of our non-widget QObjects, 0 graphics effects** left in the application.
3. Plus clearing all 37 state entries, **purging 221 of our modules and collecting 7124
   objects** inside the `kMayaExiting` hook.
4. Plus `forget_maya_wrappers` — `shiboken6.invalidate` on every wrapper we ever took of one
   of **Maya's** widgets, handing shiboken's knowledge of them back (a wrapper of a
   Maya-owned widget is not ours to delete; the C++ is Maya's). 3 of 3 runs crashed.

So the fault is not our objects being attached, not our Python still holding wrappers, and
not shiboken's map of them.

**And the stack says why none of it could work.** The newest dump, walked whole:

    _execute_onexit_table → ~QObject → killTimer → ~QObjectPrivate
      → ~QMetaObject::Connection → PySide initQObjectSubType → shiboken reads 0x153a8

`_execute_onexit_table` is the C runtime destroying **static-duration** objects, after Python
has been finalised. Every object the four attempts destroyed is a heap object owned by a Qt
parent — Maya destroys those when it destroys its main window, which is a different moment
and a different chain. Nothing destroyed from Python can reach an object the C runtime
destroys at `atexit`. What lives there and holds a connection to Python is **PySide's own
static signal machinery**: a connection from a sender to a plain Python callable is held by a
`GlobalReceiverV2` registered against **the sender**, so a connection whose sender is one of
*Maya's* objects survives everything of ours being destroyed — and the plugin has **261
`.connect(` against 17 `.disconnect(`**, which is also the count that tracks the crash rate.

That is the next hypothesis, and it is the first one the cleanup cannot test, because the
cleanup has nothing to disconnect: it does not know which of Maya's objects we connected to.

What the escalation does establish (dumps attributed by the **pid** in the dump's MiscInfo —
by timestamp alone the animator's own Mayas and a dump written late both corrupt the result):
a throwaway Maya quits clean when plain, after a bare install, after taking a shiboken wrapper
of one of Maya's own widgets, and after making, showing and destroying our own QWidget with a
connected QTimer. It crashes with the interface up. So it takes the interface, not PySide as
such.

## Proof of what is done

- `tests/test_shutdown.py` (36): the order, that nothing is imported, that a step which
  raises does not stop the rest, the `ours` discriminator against Maya's / Qt's / animBot's
  modules, both sweeps, `takeable` leaving Maya's own widget in our state alone, `deep` only
  at exit, arming's idempotence — and **`NamesExist`**, which parses each module on disk and
  fails if the plan names a function that is gone (it caught `maya_hub.drop_skin` before it
  existed).
- The install path, measured in a throwaway Maya: with the interface up, installing again
  (which now tears the Qt down before `purge_modules`) leaves the hub skinned, the Time Bar
  up, the side panel holding Maya's Channel Box and Attribute Editor, and the hook re-armed.
- `verify_shutdown.py`: **`disarmed`** and **`plain`** green — the control crashes in
  `shiboken6`, a plain Maya does not — and **`armed` still failing**. It is the standing
  failing test for whoever takes this further.

## What this does not fix

- The exit crash itself. It costs the crash dialog and whatever prefs are written after it,
  not the scene (`userPrefs.mel` at 21:47:35, the crash at 21:47:37).
- The 26 mid-session crashes are only half addressed: the installer no longer leaves a purged
  module's timers ticking, but a timer whose receiver dies for any other reason can still
  land on a dead slot.
- The panels that live inside a workspaceControl keep their control at exit by design.
- 261 `.connect(` against 17 `.disconnect(` is unchanged as a habit.

## Where to look next

The bisect by optionVar is the tool: `probe_which.py` in the session scratchpad runs one
throwaway Maya per feature with `skeldarTimeBarDefaults` pinned (the Time Bar's
once-per-version upgrade switched itself on in the first bisect, which is why that one said
nothing). The hub alone, the sounds, the Time Bar at the edge and the side panel each quit
clean; the animator's full set crashes. The untested difference is the viewport bar and the
main bar — the two features that restyle and re-point Maya's OWN controls.
