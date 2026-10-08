"""The hub's Center of Mass section.

The character's line; Add CoM / Remove / Rebuild; chips Trail and Floor; the
trail's range (Playback | Around and its frames); Select CoM (which puts the
CoM tool on); a status line. The settings live on the CoM group in the scene,
so a saved file reopens as it was left.
"""

import traceback

import maya.cmds as cmds

import maya_hubstyle as hubstyle
from maya_com import drag, engine, network

HUB_SECTION = "com"
SUBTITLE = "skeldarComSubtitle"
STATUS = "skeldarComStatus"
TRAIL = "skeldarComTrail"
FLOOR = "skeldarComFloor"
RANGE = "skeldarComRange"
RANGE_SEG = ("skeldarComRangePlayback", "skeldarComRangeAround")
AROUND = "skeldarComAround"
JOB = []


# ------------------------------------------------------------------- pure

def line_for(label, group_info):
    """The character's line. `group_info` is None (no CoM) or a dict with
    volume (L) and joints."""
    if group_info is None:
        return "%s - no CoM yet" % label
    return "%s - %.0f L over %d bones" % (label, group_info["volume"],
                                         group_info["joints"])


# ------------------------------------------------------------------ scene

def status(message):
    """The card's status line - and the hub's one message line too
    (2026-10-08, `hubstyle.tell`; this writer shows nothing in the viewport,
    so the edge panel may)."""
    if cmds.text(STATUS, exists=True):
        cmds.text(STATUS, edit=True, label=message)
        hubstyle.tell(STATUS, message, viewport=False)
    return message


def _run(action):
    try:
        return action()
    except Exception as exc:                                 # noqa: BLE001
        print(traceback.format_exc())
        return status("Center of Mass failed: %s" % exc)


def _current():
    """(Character, group or None, refusal)."""
    char, refusal = network.character()
    if not char:
        return None, None, refusal
    return char, network.group_for(char), ""


def add():
    char, group, refusal = _current()
    if not char:
        return status(refusal)
    if group:
        return status("%s already has a CoM - Rebuild weighs it again" % char.label)
    status("%s: weighing the body..." % char.label)
    cmds.refresh()
    model, info = network.build_model(char)
    cmds.undoInfo(openChunk=True, chunkName="skeldarComAdd")
    try:
        group = network.create(char, model, info)
    finally:
        cmds.undoInfo(closeChunk=True)
    engine.track(group)
    refresh()
    return status("%s: CoM added - %.0f L over %d bones, weighed in %.1f s"
                  % (char.label, model.volume / 1000.0, len(model.masses),
                     info["seconds"]))


def remove():
    char, group, refusal = _current()
    if not char:
        return status(refusal)
    if not group:
        return status("%s has no CoM" % char.label)
    uuid = (cmds.ls(group, uuid=True) or [None])[0]
    engine.untrack(uuid)
    cmds.undoInfo(openChunk=True, chunkName="skeldarComRemove")
    try:
        network.remove(group)
    finally:
        cmds.undoInfo(closeChunk=True)
    refresh()
    return status("%s: CoM removed" % char.label)


def rebuild():
    char, group, refusal = _current()
    if not char:
        return status(refusal)
    if not group:
        return add()
    keep = {a: cmds.getAttr(group + "." + a)
            for a in ("trail", "floor", "range", "around")}
    status("%s: weighing the body again..." % char.label)
    cmds.refresh()
    model, info = network.build_model(char)
    uuid = (cmds.ls(group, uuid=True) or [None])[0]
    engine.untrack(uuid)
    cmds.undoInfo(openChunk=True, chunkName="skeldarComRebuild")
    try:
        network.remove(group)
        group = network.create(char, model, info)
        for attr, value in keep.items():
            cmds.setAttr(group + "." + attr, value)
    finally:
        cmds.undoInfo(closeChunk=True)
    engine.track(group)
    refresh()
    return status("%s: CoM weighed again - %.0f L over %d bones"
                  % (char.label, model.volume / 1000.0, len(model.masses)))


def select_com():
    char, group, refusal = _current()
    if not char:
        return status(refusal)
    if not group:
        return status("%s has no CoM - Add CoM first" % char.label)
    cmds.select(network.part(group, "handle"), replace=True)
    return status("%s: drag the CoM - Shift on the floor, Ctrl up and down"
                  % char.label)


def _set(attr, value):
    char, group, refusal = _current()
    if not group:
        return
    cmds.setAttr(group + "." + attr, value)
    engine.track(group)


def _trail_changed(*_):
    _run(lambda: _set("trail", int(cmds.checkBox(TRAIL, query=True, value=True))))


def _floor_changed(*_):
    _run(lambda: _set("floor", int(cmds.checkBox(FLOOR, query=True, value=True))))


def _range_changed(index):
    return lambda *_: _run(lambda: _set("range", index))


def _around_changed(*_):
    _run(lambda: _set("around", max(1, cmds.intField(AROUND, query=True,
                                                     value=True))))


def refresh(*_):
    if not cmds.text(SUBTITLE, exists=True):
        return
    try:
        char, group, refusal = _current()
    except Exception:
        return
    if not char:
        cmds.text(SUBTITLE, edit=True, label=refusal)
        return
    info = None
    if group:
        info = {"volume": cmds.getAttr(group + ".volume"),
                "joints": len(network.mass_joints(group))}
        cmds.checkBox(TRAIL, edit=True, value=bool(cmds.getAttr(group + ".trail")))
        cmds.checkBox(FLOOR, edit=True, value=bool(cmds.getAttr(group + ".floor")))
        index = int(cmds.getAttr(group + ".range"))
        if cmds.iconTextRadioButton(RANGE_SEG[index], exists=True):
            cmds.iconTextRadioButton(RANGE_SEG[index], edit=True, select=True)
        cmds.intField(AROUND, edit=True, value=int(cmds.getAttr(group + ".around")))
    cmds.text(SUBTITLE, edit=True, label=line_for(char.label, info))


def build_panel():
    """Two rows (2026-10-08, the compact hub): Add CoM, Rebuild, Remove and
    Select CoM; then the Trail and Floor chips, the range segments and the
    frames field. The skin shows the two small buttons and the field as icons
    and a bare number (their tooltips say what they are); the classic hub
    keeps the words and the "frames" label."""
    column = cmds.columnLayout(adjustableColumn=True,
                               rowSpacing=hubstyle.row_spacing(6),
                               columnOffset=("both", hubstyle.pick(0, 8)))
    hubstyle.mark(cmds.text(SUBTITLE, label="", align="left"), "subtitle")
    cmds.rowLayout(numberOfColumns=4, adjustableColumn=1,
                   columnAttach=[(1, "both", 0), (2, "both", 4),
                                 (3, "both", 4), (4, "both", 4)])
    hubstyle.mark(cmds.button(
        label="Add CoM", height=hubstyle.height("button", 32),
        annotation="Weigh the body from its mesh and skin and add its centre "
                   "of mass: a live point, its trail and its floor shadow",
        command=lambda *_: _run(add)), "primary", "target")
    hubstyle.mark(cmds.button(
        label=hubstyle.pick("", "Rebuild"),
        height=hubstyle.height("button", 32), width=hubstyle.pick(26, 64),
        annotation="Rebuild: weigh the body again (after the mesh or the "
                   "skin changed)",
        command=lambda *_: _run(rebuild)), "secondary", "refresh")
    hubstyle.mark(cmds.button(
        label=hubstyle.pick("", "Remove"),
        height=hubstyle.height("button", 32), width=hubstyle.pick(26, 60),
        annotation="Remove the character's CoM, its trail and floor shadow",
        command=lambda *_: _run(remove)), "danger", "trash")
    hubstyle.mark(cmds.button(
        label=hubstyle.pick("Select", "Select CoM"),
        #  64: its icon and its word need 60 logical at 150 % (live,
        #  2026-10-08: 56 clipped the word). The classic widths of this row
        #  (64, 60, 72; were 80, 72, 90) keep it inside the animator's dock:
        #  the row asked 496 px, its card 532 against the dock's 510
        height=hubstyle.height("button", 28), width=hubstyle.pick(64, 72),
        annotation="Select the CoM handle: the CoM tool comes on - drag it, "
                   "Shift on the floor, Ctrl up and down; the body follows",
        command=lambda *_: _run(select_com)), "secondary", "target")
    cmds.setParent("..")
    #  The segments take the slack; the classic hub's extra "frames" word is
    #  one more column before the field.
    columns = hubstyle.pick(4, 5)
    cmds.rowLayout(numberOfColumns=columns, adjustableColumn=3,
                   columnAttach=[(1, "both", 0)]
                   + [(i, "both", 4) for i in range(2, columns)]
                   + [(columns, "both", hubstyle.pick(4, 2))])
    hubstyle.mark(cmds.checkBox(TRAIL, label="Trail", value=True,
                                annotation="The CoM's trail over the range",
                                changeCommand=_trail_changed), "chip")
    hubstyle.mark(cmds.checkBox(FLOOR, label="Floor", value=True,
                                annotation="The CoM's shadow on the floor and "
                                           "its trail",
                                changeCommand=_floor_changed), "chip")
    segments = cmds.rowLayout(numberOfColumns=2,
                              columnAttach=[(1, "both", 1), (2, "both", 1)])
    hubstyle.mark(segments, "segments", layout=True)
    cmds.iconTextRadioCollection(RANGE)
    for index, (name, label, note) in enumerate((
            (RANGE_SEG[0], "Playback", "the trail over the playback range"),
            (RANGE_SEG[1], "Around", "the trail around the current frame"))):
        hubstyle.mark(cmds.iconTextRadioButton(
            name, style="textOnly", label=label,
            height=hubstyle.height("segment", 22), select=index == 0,
            annotation=note, onCommand=_range_changed(index)), "segment")
    cmds.setParent("..")
    if not hubstyle.skinning():
        cmds.text(label="frames", align="right")
    cmds.intField(AROUND, value=20, minValue=1, width=hubstyle.pick(36, 48),
                  height=hubstyle.height("field", 22),
                  annotation="Around: this many frames each way",
                  changeCommand=_around_changed)
    cmds.setParent("..")
    hubstyle.mark(cmds.text(STATUS, label="", align="left", wordWrap=True,
                            height=36), "status")
    cmds.setParent("..")
    start()
    refresh()
    return column


def start():
    """The engine, the tool's switching and the panel's own refresh."""
    try:
        engine.start()
        drag.start()
    except Exception:
        print(traceback.format_exc())
    for job in JOB:
        try:
            if cmds.scriptJob(exists=job):
                cmds.scriptJob(kill=job, force=True)
        except Exception:
            pass
    del JOB[:]
    JOB.append(cmds.scriptJob(event=["SelectionChanged", refresh],
                              parent=STATUS))


def is_open():
    return bool(cmds.text(STATUS, exists=True))


def show_window():
    """The hub, on the Center of Mass section."""
    import maya_hub
    return maya_hub.show(HUB_SECTION)
