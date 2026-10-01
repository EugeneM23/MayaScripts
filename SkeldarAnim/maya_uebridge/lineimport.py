"""Several animations at once, laid out in a line.

2026-10-01, the animator: «Если мы нажали add new rig или перетянули в
пустое место на сцене то давай мы создадим все наши анимации в линию с
некоторым шагом что бы они не пересекались. В случае с кнопкой пусть
анимации будут выставляться симметрично относительно нуля сцены а в случае
с перетягиванием пускай относительно точки в которую мы указали.» Asked:
the step is 2.5 m widened by each clip's sideways root travel (`lineup`), a
drag's line runs across the screen, and the Skeleton mode lays its
skeletons out in the same line.

One press, in this order:

1. the refusals, nothing touched (New rig: the rig file);
2. every clip out of the editor (a dead editor leaves the scene untouched;
   one clip it cannot export is named and left out);
3. every clip imported as its own namespaced skeleton;
4. each clip's root track measured over its own range (`rigimport.root_at`,
   a time-context read of a bare skeleton - a frame walk would evaluate
   every rig in the scene per frame), the line laid out, the timeline set
   once to the union of the clips' ranges - before any bake;
5. each clip in turn: a new rig added and the clip retargeted onto it
   standing on its slot (`rigimport.retarget_imported`), or the skeleton
   stood on its slot (`rigimport.stand_skeleton`).

A cancellable progress window runs over the whole press. A cancel keeps what
is done and deletes the clip skeletons imported for the clips not yet done; a
clip whose import or retarget fails is named and the rest go on.

Spec: docs/superpowers/specs/2026-10-01-uebridge-many-animations-design.md
"""

import traceback

import maya.cmds as cmds

from maya_uebridge import lineup
from maya_uebridge import rigimport

TARGETS = ("new_rig", "skeleton")
NOTHING = "select an animation first"


# ------------------------------------------------------------------ words

def first_only(names):
    """The note when the Rig mode (or a drop on a rig) was given several: it
    takes the first. Pure; "" for one."""
    names = list(names or [])
    if len(names) < 2:
        return ""
    return "only {0}: a rig takes one animation ({1} more picked)".format(
        names[0], len(names) - 1)


def _plural(count, word):
    return "{0} {1}{2}".format(count, word, "" if count == 1 else "s")


def summary(target, done, total, centre, widened, failures,
            step=lineup.STEP, cancelled=False):
    """The status line after the press. Pure.

    `done` is [(label, clip name)] in line order - the rig's label onto which
    the clip went, or the skeleton's namespace; `failures` [(clip, reason)]."""
    where = "about ({0}, {1})".format(int(round(centre[0])), int(round(centre[2])))
    parts = []
    if not done:
        parts.append("no animation laid out")
    else:
        count = (_plural(len(done), "animation") if len(done) == total
                 else "{0} of {1} animations".format(len(done), total))
        if target == "new_rig":
            rigs = (_plural(len(done), "new rig") if len(done) == total
                    else "new rigs")
            head = "{0} onto {1} in a line {2}".format(count, rigs, where)
            names = ", ".join("{0} {1}".format(label, name) for label, name in done)
        else:
            head = "{0} as skeletons in a line {1}".format(count, where)
            names = ", ".join(label for label, _name in done)
        parts.append("{0}: {1}".format(head, names))
        if len(done) > 1:
            gap = "step {0:g} m".format(step / 100.0)
            if widened:
                gap += ", widened beside {0}".format(", ".join(widened))
            parts.append(gap)
    if failures:
        parts.append("failed: " + "; ".join(
            "{0} ({1})".format(name, reason) for name, reason in failures))
    if cancelled:
        parts.append("cancelled - the clips not yet done were discarded"
                     if done or total else "cancelled")
    return "  |  ".join(parts)


def _short(error):
    lines = [line for line in str(error).strip().splitlines() if line.strip()]
    return lines[-1] if lines else type(error).__name__


def span_of(infos):
    """(first frame, last frame) over the clips' ranges, or None. Pure."""
    starts = [i["start"] for i in infos if i.get("start") is not None]
    ends = [i["end"] for i in infos if i.get("end") is not None]
    if not starts or not ends:
        return None
    return min(starts), max(ends)


# ------------------------------------------------------------------ scene

class _Progress(object):
    """Maya's progress window, cancellable; nothing at all where it cannot
    stand (a batch session)."""

    def __init__(self, total):
        self.on = False
        try:
            cmds.progressWindow(title="UE Bridge", progress=0,
                                maxValue=max(1, total), status="...",
                                isInterruptable=True)
            self.on = True
        except Exception:                                    # noqa: BLE001
            pass

    def step(self, text):
        if self.on:
            try:
                cmds.progressWindow(edit=True, step=1, status=text)
            except Exception:                                # noqa: BLE001
                pass

    def cancelled(self):
        if not self.on:
            return False
        try:
            return bool(cmds.progressWindow(query=True, isCancelled=True))
        except Exception:                                    # noqa: BLE001
            return False

    def close(self):
        if self.on:
            try:
                cmds.progressWindow(endProgress=True)
            except Exception:                                # noqa: BLE001
                pass


def track_of(source, start, end):
    """The clip's root over its own range (`lineup.sample_frames`)."""
    if start is None:
        return [rigimport.root_at(source)]
    return [rigimport.root_at(source, frame)
            for frame in lineup.sample_frames(start, end)]


def _discard(namespace):
    """A clip skeleton imported for a clip that will not be done."""
    try:
        if cmds.namespace(exists=namespace):
            cmds.namespace(removeNamespace=namespace,
                           deleteNamespaceContent=True)
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()


def _onto_new_rig(plan, clip, point):
    """(label, failure): a rig added, the clip retargeted onto it standing on
    `point`, the clip's skeleton deleted. One undo chunk, as one press."""
    import maya_rigs
    cmds.undoInfo(openChunk=True, chunkName="UE anim import + retarget")
    try:
        rig, mod, notes, failure = rigimport.ready_rig(plan)
        if failure:
            _discard(clip["namespace"])
            line = ""
        else:
            line, failure = rigimport.retarget_imported(
                rig, mod, clip["namespace"], clip["info"], clip["source"],
                clip["name"], {"point": tuple(point), "yaw": None})
    finally:
        cmds.undoInfo(closeChunk=True)
    for text in notes + [line]:
        if text:
            print("[uebridge] {0}".format(text))
    if failure:
        return None, failure
    return maya_rigs.label(rig), ""


def run(record_list, export, target, centre=(0.0, 0.0, 0.0),
        axis=(1.0, 0.0, 0.0), set_timeline=True, step=lineup.STEP):
    """The press for several animations. Returns the status line.

    `export(record)` answers (fbx path, fps) - the window's round trip to the
    editor. `target` is "new_rig" (a new rig per clip, retargeted) or
    "skeleton" (each clip its own skeleton). The line runs along `axis` on
    the floor about `centre`, in the order given."""
    record_list = list(record_list or [])
    if target not in TARGETS:
        return "unknown import target {0!r}".format(target)
    if not record_list:
        return NOTHING
    plan = None
    if target == "new_rig":
        plan, refusal = rigimport.plan_press("new_rig")
        if refusal:
            return refusal
    axis = lineup.floor_axis(axis)
    centre = tuple(centre or (0.0, 0.0, 0.0))
    total = len(record_list)
    failures, done, widened, imported = [], [], [], []
    cancelled = False
    progress = _Progress(3 * total)
    try:
        exported = []
        for record in record_list:
            if progress.cancelled():
                return summary(target, [], 0, centre, [], failures, step,
                               cancelled=True) + " - nothing imported"
            progress.step("{0}: out of the editor".format(record.name))
            try:
                fbx, fps = export(record)
            except Exception as error:                       # noqa: BLE001
                traceback.print_exc()
                failures.append((record.name, _short(error)))
                continue
            exported.append((record, fbx, fps))

        for record, fbx, fps in exported:
            if progress.cancelled():
                cancelled = True
                break
            progress.step("{0}: importing".format(record.name))
            try:
                namespace, info, source = rigimport.import_source(
                    fbx, record.name, clip_fps=fps, set_timeline=False)
            except Exception as error:                       # noqa: BLE001
                traceback.print_exc()
                failures.append((record.name, _short(error)))
                continue
            if source is None:
                failures.append((record.name, "holds no joint"))
                _discard(namespace)
                continue
            imported.append(dict(name=record.name, namespace=namespace,
                                 info=info, source=source))
        if cancelled:
            for clip in imported:
                _discard(clip["namespace"])
            return summary(target, [], total, centre, [], failures, step,
                           cancelled=True)

        if imported:
            extents = [lineup.side_extent(
                track_of(clip["source"], clip["info"].get("start"),
                         clip["info"].get("end")), axis) for clip in imported]
            points = lineup.slots(centre, axis, lineup.offsets(extents, step))
            widened = lineup.widened([clip["name"] for clip in imported],
                                     extents)
            span = span_of([clip["info"] for clip in imported])
            if set_timeline and span:
                cmds.playbackOptions(minTime=span[0], maxTime=span[1],
                                     animationStartTime=span[0],
                                     animationEndTime=span[1])

            for index, (clip, point) in enumerate(zip(imported, points)):
                if progress.cancelled():
                    cancelled = True
                    for rest in imported[index:]:
                        _discard(rest["namespace"])
                    break
                progress.step("{0}: {1}".format(
                    clip["name"], "retarget onto a new rig"
                    if target == "new_rig" else "into the line"))
                try:
                    if target == "new_rig":
                        label, failure = _onto_new_rig(plan, clip, point)
                    else:
                        rigimport.stand_skeleton(clip["namespace"],
                                                 clip["source"], point,
                                                 clip["info"].get("start"))
                        label, failure = clip["namespace"], ""
                except Exception as error:                   # noqa: BLE001
                    traceback.print_exc()
                    label, failure = None, _short(error)
                if failure:
                    failures.append((clip["name"], failure))
                else:
                    done.append((label, clip["name"]))
    finally:
        progress.close()
    text = summary(target, done, total, centre, widened, failures, step,
                   cancelled)
    print("[uebridge] {0}".format(text))
    return text
