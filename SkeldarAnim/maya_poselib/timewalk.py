"""The pose library's time walk and its progress window (the animation cards, 2026-10-03).

An animation card is saved by reading the character at every frame of a range, and applied by
keying it at every frame of the paste: both are a WALK of the time. The CoM engine's walk is the
house pattern (`maya_com.engine.Scene.walk`): `MAnimControl.setCurrentTime` under `refresh
-suspend`, the time put back after. `currentTime -update 0` is not an option - it reads stale
(trap 127). Measured in mayapy 2027 for this module:

- a walk is UNRECORDED: the undo queue's last name ('probe') unchanged across a walk of three
  `setCurrentTime`s and back - a press's chunk holds its keys, not its time changes;
- a read right after each set is FRESH under DG: a spline keyed 0/10/20 at frames 0/10/20 read
  1.53 / 6.37 / 16.25 at frames 3 / 7 / 15;
- a walk THROWS AWAY the animator's unkeyed tweaks: a keyed ty set to 99 by hand read 1.112
  after a walk to frame 5 and back (trap 206's mechanism). So `keys.Tweaks()` reads every
  time-fed channel FIRST, and the exit sets back every one that moved - but the plugs the press
  keyed (`walk.keyed`), which show their new keys;
- `refresh -suspend` answers None in batch mode and its query too (no state to read back), so a
  walk suspends and resumes, as the CoM engine does.

Under `fresh` the whole walk runs under the solve's evaluation (`rigsolve._fresh`: DG - the
parallel EM read stale after scripted sets on a keyed rig, trap 207), ONE switch for the whole
press rather than one per frame; `_fresh` sets the tweaks back after its own switches, skipping
`walk.keyed` too (the same list object, so what is keyed later is skipped as well).

`Progress` is Maya's cancellable progress window (`progressWindow -isInterruptable`, Esc
cancels) and nothing at all in batch mode (measured: `progressWindow` answers None there and
`-q -isCancelled` None): a standalone verify or a mayapy session saves and pastes uninterrupted.

Spec: docs/superpowers/specs/2026-10-03-pose-library-animation-design.md ("What is read", "The
press, in order").
"""

import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma
import maya.cmds as cmds

from maya_poselib import keys


def _evaluation(tweaks, skip):
    """The solve's evaluation (`rigsolve._fresh`) as a context, `tweaks` the walk's own reading
    and `skip` its `keyed` list. Imported here, late: the solver pulls the retarget modules in,
    and a walk that only reads (a save) never needs them. A seam."""
    from maya_poselib import rigsolve
    return rigsolve._fresh(tweaks, skip)


class Walk(object):
    """with Walk(fresh=True) as walk: walk.go(frame) ... - a time walk.

    On entry, in this order: the animator's tweaks read (`keys.Tweaks()` - before anything can
    re-evaluate the scene), the time it stands on remembered, the viewport suspended (`refresh
    -suspend`), and - `fresh` - the solve's evaluation entered (`_evaluation`). Each `go` is an
    `MAnimControl.setCurrentTime` in the scene's time unit: unrecorded, and a full evaluation on
    the next read (measured). On exit, in this order, each step run whatever the one before did:
    the time put back, the viewport resumed, the evaluation put back (its own tweak set-back
    skipping `keyed`), and the tweaks set back but `walk.keyed` - the plugs the press keyed,
    which the press extends as it keys. `Tweaks.restore` knows a node under any spelling but an
    attribute by its spelling: `keyed` holds LONG attribute names (`rotateX`, as the solvers and
    `keys.write` answer them) - checked on real Maya, a keyed `loc.sx` was set back over its new
    key while `loc.scaleX` was skipped. An exception inside the walk goes on after all of that;
    a step that fails on exit is raised after the others ran, unless the walk's own exception is
    already on its way. An evaluation that cannot be made or entered (the solver's late import
    failing, the switch refused) resumes the viewport before the error goes on.

    `restore_all()` is a cancelled press's: its chunk undone, nothing it keyed stands, so every
    tweak goes back - now, and again on exit (the time put back throws them away once more)."""

    def __init__(self, fresh=True):
        self.fresh = fresh
        self.keyed = []
        self.frame = None
        self.moved = False                   # has a `go` changed the time yet?
        self.tweaks = None
        self._here = None
        self._evaluating = None

    def __enter__(self):
        self.tweaks = keys.Tweaks()
        self._here = oma.MAnimControl.currentTime()
        cmds.refresh(suspend=True)
        if self.fresh:
            try:
                # inside the guard: `_evaluation` imports the solver late, and an import that
                # fails must not leave the viewport suspended any more than a switch refused
                evaluating = _evaluation(self.tweaks, self.keyed)
                evaluating.__enter__()
            except BaseException:
                cmds.refresh(suspend=False)
                raise
            self._evaluating = evaluating
        return self

    def go(self, frame):
        """The scene at `frame` (the scene's own time unit); `walk.frame` says where it stands."""
        oma.MAnimControl.setCurrentTime(om.MTime(frame, om.MTime.uiUnit()))
        self.frame = frame
        self.moved = True

    def arrive(self, frame):
        """`go(frame)` - unless the walk has not moved yet and the scene already stands on
        `frame`: a `setCurrentTime` to the frame the scene stands on re-evaluates every time
        curve and throws away the animator's unkeyed tweaks (measured: a tweak of 77 read back
        as 2.8), so a press pasting at the current frame reads what the animator SEES there -
        the tweaks the entry set back after its own evaluation switch (the final review, M2:
        Main dragged by hand to place a walk was keyed where its curve stood). True when it
        went."""
        if not self.moved and self._here is not None and \
                abs(float(frame) - float(self._here.value)) <= 1e-9:
            self.frame = frame
            return False
        self.go(frame)
        return True

    def restore_all(self):
        """Every tweak set back, the press's keyed plugs included - the press was undone. The
        plugs set back; the exit sets them back again after the time has gone home."""
        del self.keyed[:]
        return self.tweaks.restore() if self.tweaks is not None else []

    def __exit__(self, kind, error, trace):
        failed = []

        def attempt(step, *args):
            try:
                step(*args)
            except Exception as problem:            # noqa: BLE001 - every step must run
                failed.append(problem)

        attempt(oma.MAnimControl.setCurrentTime, self._here)
        attempt(_resume)
        if self._evaluating is not None:
            evaluating, self._evaluating = self._evaluating, None
            attempt(evaluating.__exit__, None, None, None)
        attempt(self.tweaks.restore, self.keyed)
        if failed and kind is None:
            raise failed[0]
        return False


def _resume():
    """The viewport back (`refresh -suspend 0`)."""
    cmds.refresh(suspend=False)


class Progress(object):
    """with Progress("Saving Walk", total) as progress: progress.step(text) -> False once the
    animator pressed Esc (`walk` and keying stop there; the caller undoes or writes nothing).

    Maya's `progressWindow` - opened with the title, `maxValue` the total (at least 1) and
    `isInterruptable`, stepped by one per `step` with `text` as its status, ended on exit
    whatever happened inside. A no-op that always answers True in batch mode (`about -batch`)
    and where the window cannot open (no UI); `cancelled` stays True once Esc was seen."""

    def __init__(self, title, total):
        self.title, self.total = title, total
        self.on = False
        self.cancelled = False

    def __enter__(self):
        try:
            batch = bool(cmds.about(batch=True))
        except Exception:                            # noqa: BLE001 - no Maya to ask
            batch = True
        if not batch:
            try:
                cmds.progressWindow(title=self.title, progress=0,
                                    maxValue=max(1, int(self.total or 0)), status="...",
                                    isInterruptable=True)
                self.on = True
            except Exception:                        # noqa: BLE001 - no UI to show it in
                self.on = False
        return self

    def step(self, text=""):
        """One step done, `text` the status: False once the animator pressed Esc."""
        if not self.on:
            return True
        if not self.cancelled:
            try:
                cmds.progressWindow(edit=True, step=1, status=text)
                self.cancelled = bool(cmds.progressWindow(query=True, isCancelled=True))
            except Exception:                        # noqa: BLE001 - the window is gone
                self.on = False
                return True
        return not self.cancelled

    def __exit__(self, kind, error, trace):
        if self.on:
            self.on = False
            try:
                cmds.progressWindow(endProgress=True)
            except Exception:                        # noqa: BLE001
                pass
        return False
