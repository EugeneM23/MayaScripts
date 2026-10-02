"""Several animations at once, laid out in a square.

2026-10-01, the animator: «Если мы нажали add new rig или перетянули в
пустое место на сцене то давай мы создадим все наши анимации в линию с
некоторым шагом что бы они не пересекались. В случае с кнопкой пусть
анимации будут выставляться симметрично относительно нуля сцены а в случае
с перетягиванием пускай относительно точки в которую мы указали.» Asked:
the step is 2.5 m widened by each clip's root travel (`lineup`), and the
Skeleton mode lays its skeletons out the same way. The same evening, «всегда
располагать наши анимации в квадратной формации в не зависимости от угла
камеры»: a square on world X and Z (`lineup.square_slots`), no camera axis.

One press, in this order:

1. the refusals, nothing touched (New rig: the rig file);
2. every clip out of the editor (a dead editor leaves the scene untouched;
   one clip it cannot export is named and left out);
3. every clip imported as its own namespaced skeleton;
4. each clip's root track measured over its own range (`rigimport.root_at`,
   a time-context read of a bare skeleton - a frame walk would evaluate
   every rig in the scene per frame), the square laid out, the timeline set
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
from maya_uebridge import skeletonimport
import maya_skeletonmap as skelmap

TARGETS = ("new_rig", "skeleton")
NOTHING = "select an animation first"
CANCELLED = "cancelled - nothing changed"


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
            step=lineup.STEP, cancelled=False, shape=None, label=None):
    """The status line after the press. Pure.

    `done` is [(label, clip name)] in the square's order - the rig's label
    onto which the clip went, or the skeleton's namespace; `failures`
    [(clip, reason)]; `shape` the square's (columns, rows); `label` the
    skeleton row the Skeleton mode adds."""
    where = "about ({0}, {1})".format(int(round(centre[0])), int(round(centre[2])))
    square = ("a {0} x {1} square".format(shape[0], shape[1]) if shape
              else "a square")
    parts = []
    if not done:
        parts.append("no animation laid out")
    else:
        count = (_plural(len(done), "animation") if len(done) == total
                 else "{0} of {1} animations".format(len(done), total))
        if target == "new_rig":
            rigs = (_plural(len(done), "new rig") if len(done) == total
                    else "new rigs")
            head = "{0} onto {1} in {2} {3}".format(count, rigs, square, where)
            names = ", ".join("{0} {1}".format(label, name) for label, name in done)
        elif label:
            what = ("{0} new {1}".format(len(done), label) if len(done) == total
                    else "new {0}".format(label))
            head = "{0} onto {1} in {2} {3}".format(count, what, square, where)
            names = ", ".join("{0} {1}".format(top, name) for top, name in done)
        else:
            head = "{0} as skeletons in {1} {2}".format(count, square, where)
            names = ", ".join(top for top, _name in done)
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


class _Versions(object):
    """The retarget version for every clip of the batch, asked ONCE
    (2026-10-02, `maya_retargetmode.choose_batch`): measured against the first
    target the batch adds - every target of a batch is the same catalog row -
    the worst clip named. Raises `maya_retargetmode.Cancelled` on Cancel."""

    def __init__(self, clips):
        self.clips = clips
        self.decisions = None
        # by UUID: the clip being placed is wrapped (re-parented) before it is
        # asked about, so its recorded path is stale by then (trap 16)
        self.uuids = []
        for clip in clips:
            try:
                self.uuids.append((cmds.ls(clip["source"], uuid=True) or [None])[0])
            except Exception:                                # noqa: BLE001
                self.uuids.append(None)

    def _source(self, index):
        uuid = self.uuids[index] if index < len(self.uuids) else None
        if uuid:
            found = cmds.ls(uuid, long=True) or []
            if found:
                return found[0]
        return self.clips[index]["source"]

    def _decide(self, measures):
        import maya_retargetmode
        self.decisions = maya_retargetmode.choose_batch(measures)

    def for_rig(self, index, rig, mod):
        """The Decision for clip `index` onto a new rig; None for the legacy
        retarget (a module that cannot measure)."""
        if self.decisions is None:
            probe = getattr(mod, "measure", None)
            if probe is None:
                return None
            self._decide([probe(source_root=self._source(i), rig=rig)[0]
                          for i in range(len(self.clips))])
        return self.decisions[index]

    def for_skeleton(self, index):
        """A `decide` for `skeletonimport.onto_skeleton` of clip `index`."""
        def decide(source, root, label, start):
            if self.decisions is None:
                self._decide([skeletonimport.measure(self._source(i), root,
                                                     c["info"].get("start"), label)
                              for i, c in enumerate(self.clips)])
            return self.decisions[index]
        return decide

    def reasons(self):
        """The distinct reasons the batch's versions were taken for."""
        out = []
        for d in self.decisions or []:
            if d is not None and d.reason and d.reason not in out:
                out.append(d.reason)
        return out


def _onto_new_rig(plan, clip, point, versions=None, index=0):
    """(label, failure): a rig added, the clip retargeted onto it standing on
    `point`, the clip's skeleton deleted. One undo chunk, as one press.
    `versions` (a `_Versions`) answers the retarget version; its Cancelled
    deletes the rig just added and goes on up."""
    import maya_rigs
    cmds.undoInfo(openChunk=True, chunkName="UE anim import + retarget")
    try:
        rig, mod, notes, failure = rigimport.ready_rig(plan)
        if failure:
            _discard(clip["namespace"])
            line = ""
        else:
            decision = None
            if versions is not None:
                import maya_retargetmode
                try:
                    decision = versions.for_rig(index, rig, mod)
                except maya_retargetmode.Cancelled:
                    rigimport.discard_added(rig)
                    raise
            line, failure = rigimport.retarget_imported(
                rig, mod, clip["namespace"], clip["info"], clip["source"],
                clip["name"], {"point": tuple(point), "yaw": None},
                **({"bones": decision.mode} if decision is not None and decision.mode
                   else {}))
    finally:
        cmds.undoInfo(closeChunk=True)
    for text in notes + [line]:
        if text:
            print("[uebridge] {0}".format(text))
    if failure:
        return None, failure
    return maya_rigs.label(rig), ""


def auto_summary(done, total, centre, widened, failures, step=lineup.STEP,
                 cancelled=False, shape=None):
    """The status line after an Auto press of several (2026-10-02). Pure.

    `done` is [(label, clip name)] in the square's order - the rig's label, the new skeleton's
    top, or «own <base>» for a clip kept in its own skeleton."""
    where = "about ({0}, {1})".format(int(round(centre[0])), int(round(centre[2])))
    square = ("a {0} x {1} square".format(shape[0], shape[1]) if shape
              else "a square")
    parts = []
    if not done:
        parts.append("no animation laid out")
    else:
        count = (_plural(len(done), "animation") if len(done) == total
                 else "{0} of {1} animations".format(len(done), total))
        parts.append("{0} in {1} {2}: {3}".format(
            count, square, where, ", ".join("{0} {1}".format(label, name)
                                            for label, name in done)))
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


def auto_order(clips):
    """The order an Auto batch works in (2026-10-02): the clips matched to a row of ours first -
    any question about a retarget version is asked before a clip is kept in its own skeleton,
    so a Cancel finds nothing of that kind done - each keeping its own slot. Pure."""
    matched = [i for i, clip in enumerate(clips) if clip.get("entry") is not None]
    return matched + [i for i, clip in enumerate(clips) if clip.get("entry") is None]


def _auto_one(clip, point, versions, groups, index):
    """(label, failure) for one clip of an Auto batch: onto a new rig / skeleton of its matched
    row, else kept in its own skeleton on `point`."""
    from maya_uebridge import autoimport, nativeimport
    entry = clip["entry"]
    if entry is None:
        line, failure, base = nativeimport.keep(clip["namespace"], clip["info"], clip["source"],
                                                clip["name"], point, clip.get("why", ""))
        if line:
            print("[uebridge] {0}".format(line))
        return ("own {0}".format(base) if not failure else None), failure
    group = versions[entry.key]
    position = groups[entry.key].index(index)
    if entry.kind == "rig":
        if not rigimport._rig_file_ok(entry):
            _discard(clip["namespace"])
            return None, rigimport.NO_RIG_FILE.format(rigimport._rig_file_name(entry))
        plan = dict(rig=None, mod=None, add=True, entry=entry)
        return _onto_new_rig(plan, clip, point, group, position)
    refusal = skeletonimport.precheck(entry)
    if refusal:
        _discard(clip["namespace"])
        return None, refusal
    line, failure, label = autoimport.onto_new_skeleton(
        entry, clip["namespace"], clip["info"], clip["source"], clip["name"], point,
        decide=group.for_skeleton(position))
    if line:
        print("[uebridge] {0}".format(line))
    return label, failure


def run(record_list, export, target, centre=(0.0, 0.0, 0.0),
        set_timeline=True, step=lineup.STEP, auto=False):
    """The press for several animations. Returns the status line.

    `export(record)` answers (fbx path, fps) - the window's round trip to the
    editor. `target` is "new_rig" (a new rig per clip, retargeted) or
    "skeleton" (each clip its own skeleton). The square stands on world X
    and Z about `centre`, filled in the order given: row 0 in front (+Z),
    each row left to right (+X) - whatever the camera.

    `auto` (2026-10-02, the Auto card): `target` is only the KIND - each
    clip is matched among our rows of it (`autoimport.match_clip`) and goes
    onto a new rig / skeleton of its row, else stays in its own skeleton on
    its slot (`nativeimport.keep`); the retarget version is asked at most once
    per row, and the travel is not scaled (a twin keeps it, a native too)."""
    record_list = list(record_list or [])
    if target not in TARGETS:
        return "unknown import target {0!r}".format(target)
    if not record_list:
        return NOTHING
    plan = entry = None
    if auto:
        pass                              # each clip's row is checked once it is matched
    elif target == "new_rig":
        plan, refusal = rigimport.plan_press("new_rig")
        if refusal:
            return refusal
    else:
        entry = skeletonimport.skeleton_entry()
        refusal = skeletonimport.precheck(entry)
        if refusal:
            return refusal
    centre = tuple(centre or (0.0, 0.0, 0.0))
    total = len(record_list)
    failures, done, widened, imported = [], [], [], []
    shape = versions = None
    cancelled = False
    reasons = []
    timing = rigimport.time_state()
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
            if auto:
                from maya_scenesetup import catalog
                from maya_uebridge import autoimport, skeletonmatch
                kind = "rig" if target == "new_rig" else "skeleton"
                for clip in imported:
                    found = autoimport.match_clip(clip["source"], clip["info"], kind)
                    clip["entry"] = (catalog.character_by_key(found.key)
                                     if found.key else None)
                    clip["why"] = skeletonmatch.match_text(found, autoimport.label_of)
                tracks = [track_of(clip["source"], clip["info"].get("start"),
                                   clip["info"].get("end")) for clip in imported]
            else:
                # each track at the size the bake will carry it (a foreign clip is
                # scaled to ours about its first frame - `skeletonimport.travel_scale`)
                tracks = [skelmap.scaled_track(
                    track_of(clip["source"], clip["info"].get("start"), clip["info"].get("end")),
                    skeletonimport.travel_scale(clip["source"], target)) for clip in imported]
            x_reach = [lineup.side_extent(t, lineup.COLUMNS) for t in tracks]
            z_reach = [lineup.side_extent(t, lineup.ROWS) for t in tracks]
            points = lineup.square_slots(centre, x_reach, z_reach, step)
            shape = lineup.grid_shape(len(imported))
            widened = lineup.widened([clip["name"] for clip in imported],
                                     x_reach, z_reach)
            span = span_of([clip["info"] for clip in imported])
            if set_timeline and span:
                cmds.playbackOptions(minTime=span[0], maxTime=span[1],
                                     animationStartTime=span[0],
                                     animationEndTime=span[1])

            import maya_retargetmode
            if auto:
                groups = {}
                for index, clip in enumerate(imported):
                    if clip["entry"] is not None:
                        groups.setdefault(clip["entry"].key, []).append(index)
                by_row = dict((key, _Versions([imported[i] for i in indices]))
                              for key, indices in groups.items())
                order = auto_order(imported)
            else:
                versions = _Versions(imported)
                order = list(range(len(imported)))
            finished = {}
            for step_index, index in enumerate(order):
                clip, point = imported[index], points[index]
                if progress.cancelled():
                    cancelled = True
                    for rest in order[step_index:]:
                        _discard(imported[rest]["namespace"])
                    break
                if auto:
                    what = ("its own skeleton" if clip["entry"] is None
                            else "onto a new {0}".format(clip["entry"].label))
                else:
                    what = ("retarget onto a new rig" if target == "new_rig"
                            else "onto a new skeleton")
                progress.step("{0}: {1}".format(clip["name"], what))
                try:
                    if auto:
                        label, failure = _auto_one(clip, point, by_row, groups, index)
                    elif target == "new_rig":
                        label, failure = _onto_new_rig(plan, clip, point,
                                                       versions, index)
                    else:
                        line, failure, label = skeletonimport.onto_skeleton(
                            entry, clip["namespace"], clip["info"],
                            clip["source"], clip["name"], point,
                            decide=versions.for_skeleton(index))
                        if line:
                            print("[uebridge] {0}".format(line))
                except maya_retargetmode.Cancelled:
                    # asked before the clip went on: every clip skeleton not yet
                    # done goes - before the first clip that is everything
                    for rest in order[step_index:]:
                        _discard(imported[rest]["namespace"])
                    if not finished:
                        rigimport.restore_time(timing)
                        text = "{0} animations: {1}".format(len(imported), CANCELLED)
                        print("[uebridge] {0}".format(text))
                        return text
                    cancelled = True
                    break
                except Exception as error:                   # noqa: BLE001
                    traceback.print_exc()
                    label, failure = None, _short(error)
                if failure:
                    failures.append((clip["name"], failure))
                else:
                    finished[index] = (label, clip["name"])
            done = [finished[i] for i in sorted(finished)]
            if auto:
                for group in by_row.values():
                    reasons.extend(r for r in group.reasons() if r not in reasons)
            elif versions is not None:
                reasons = versions.reasons()
    finally:
        progress.close()
    if auto:
        text = auto_summary(done, total, centre, widened, failures, step, cancelled, shape)
    else:
        text = summary(target, done, total, centre, widened, failures, step,
                       cancelled, shape, entry.label if entry else None)
    if reasons:
        text = "{0}  |  {1}".format(text, "; ".join(reasons))
    print("[uebridge] {0}".format(text))
    return text
