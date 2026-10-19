# Scene tabs: each tab its own undo history (2026-10-19)

The animator: «Для каждой вкладки нужно реализовать свою историю действий сейчас одна на вссе вкладки».

## The limit

Maya keeps one linear undo queue. Ctrl+Z takes off the top step, and redo replays
steps in reverse order. So a tab's steps made before another tab's work lie under that
work, and Maya can neither undo them past it nor take them out and put them back.
Two other designs were offered: per-tab snapshots on disk (slow on every step) and
flushing the queue on every switch. The animator chose the **tab boundary**.

## What it does

- **A switch is no undo step.** `switching.switch` hides and shows tabs outside the
  queue (`stateWithoutFlush` off). Until now a switch was one chunk, and Ctrl+Z past it
  brought the previous tab back.
- **A fence on entering.** When the queue's top is not already this tab's work, the
  switch lays a FENCE: a chunk named `skeldarTabFence:<namespace>:<serial>` holding one
  `setAttr` of a counter (`skeldarFence`) on the session node. Maya records no empty
  chunk, and `undoInfo -q -undoName` answers the chunk's name (measured in mayapy).
- **Ctrl+Z stops at a fence.** An `MEventMessage` "Undo" callback reads `redoName`. If
  the step just undone is a fence, it redoes it at once and says so in the viewport.
  This works for every road (the hotkey, Edit > Undo, a script): measured, a redo inside
  the callback holds, and three undos in a row stayed on the fence. The message says
  «Start of this tab's undo history». When the tab's own work was on the queue before
  this fence, it adds «- its earlier steps are under another tab's work».
- **A tab left untouched goes on.** When the leaving tab's fence is still the top (it
  did nothing), the switch undoes it before leaving. The tab whose work was under it
  owns the top again, and entering that tab lays no fence. So A → B (nothing) → C
  (nothing) → A goes on with A's history.
- **A fence on the redo queue is not another tab's to redo.** Popping a fence puts it
  on the redo queue. A "Redo" callback undoes a redone fence of another tab back:
  «Nothing to redo in this tab».
- **Flushes.** Every tab operation that imports (open, new, close, reload, restore)
  already flushes the queue (`opening._quiet`). It now also calls `tabundo.reset(active)`:
  no fences, and the empty top belongs to the active tab. Another flush (an Add Character
  import) leaves a stale bookkeeping that is still safe: a pop needs its fence to be the
  queue's top by name, and that proves nothing was flushed since.
- **The modified flag.** A popped fence is an undo, and an undo flags the scene. The
  switch puts the flag back before it records the tab it leaves (found by the
  `cameras` phase's "switching leaves clean tabs clean").
- **Not recording** (inside `_quiet`, a save's unrecorded part, undo off): no fence, no pop.
- One scene open: nothing changes (no switch happens).

State on `sys._skeldar_tabundo` (trap 111): `fences` {name: {ns, below, earlier}},
`owner`, `seen`, `serial`, the callbacks. The queue is the session's and never saved,
so neither is this.

## After first use (the same day)

The animator: «перехожу обратно в другую вкладку то история пустая». Read off the
7002 Maya's queue: JA_04's moves and keys (steps 0-6), then untitled's fence, then a
cube and a key made in untitled, then JA_04's new fence. That is the limit, not a
bug. Offered snapshots, or the old shared history, they kept the boundary and asked
for a clearer word. Both messages now name the tabs, and entering a tab whose history
went under another tab's work says so at once:
«JA_04: earlier undo steps are under the work done in untitled - Ctrl+Z here starts from now».
Ctrl+Z on that fence says
«JA_04: start of undo here - earlier steps are under the work done in untitled (Maya keeps one undo list)».

## Selection steps do not bury a tab (the same evening)

«История скидывается после переключения между вкладками». Measured in the 7002 Maya
with a command logger and the queue dumped around switches made through the bar's own
action, with idle between: no step is recorded by the switch or by anything that runs after it
(hub cards, Time Bar, side panel: queries and UI only, and an unrecorded `select` stays
unrecorded). The real cause was a click: a selection in a GUI Maya is a recorded `select`
step. So looking at a tab and clicking in it laid steps on its fence, the tab counted as worked,
and the tab before it was buried on the way back.

Now `_drop_selection` runs as a tab is left. While the queue's top is a MEL selection step
(`select`, `selectKey`, `hilite` by undo name - a viewport, Outliner or Graph Editor click is
MEL and named), it undoes it, down to the leaving tab's newest fence. The fence is then popped
as usual. On the first step that is not a selection, every step undone is redone, and the queue
is as it was. The selection the tab shows is put back unrecorded before `leave` records it.
A Python `cmds.select` (the plugin's own presses) has an empty undo name and stays unknown
work.

**Time changes too.** Measured live: in a GUI Maya a time change is an undo step. A Python
`cmds.currentTime(f, edit=True)` adds an unnamed entry, and MEL `currentTime -e` (Maya's
frame hotkeys) a named one, while Maya's own slider records nothing. So `currentTime` joined
the looking steps that come off as a tab is left, and the frame shown is put back with the
selection. The Time Bar's `set_time` / `scrub_only` (unnamed, so unknown to the tabs) were
asked to run unrecorded, as Maya's slider does, in `maya_timebar/scene.py`.
A code audit by agents (62 agents, every subsystem that reacts to a switch) found nothing else
recording after a switch. Its one candidate, the Layer Editor rebuild's `treeView -selectItem`,
was refuted by the live command log: it ran, and no `animLayer -edit` and no step followed.

## Module

`SkeldarAnim/maya_scenetabs/tabundo.py`. The pure half is `fence_name`, `is_fence`,
`fence_tab`, `plan_enter(fences, owner, leaving, entering, top) -> (pop, lay)` and
`blocked_message`. The scene half is `before_switch`, `after_switch`, `on_undo`, `on_redo`,
`install`, `remove` and `reset`.

## Proof

- `tests/test_scenetabs_tabundo.py`.
- `verify_scene_tabs.py undo` (mayapy). The film and the rig, each with a step:
  - Ctrl+Z in the film stops at its fence and says the earlier steps are under the rig's work;
  - back in the rig (the film left untouched), its history goes on;
  - the next undo stops at the rig's own fence, and redo works;
  - the film's fence popped into the redo queue is taken back;
  - four Ctrl+Z in a row stay in the rig.
- The gates that proved the old behaviour (`switch`, `outliner_sets`, `layer_editor`,
  `camera_keys`, `cameras`) now prove that Ctrl+Z after a switch stays in the tab.

Not seen in a GUI Maya: the viewport message, Edit > Undo, the Script Editor's
«Undo: skeldarTabFence...» lines.
