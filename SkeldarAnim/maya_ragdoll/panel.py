"""The Ragdoll card (2026-10-16): what Fall would drop, its knobs, Fall, the line.

A plain `cmds` card with the hub's marks; every press reads the remembered settings when the card is
closed (a hotkey row presses it then).
"""

import json

import maya.cmds as cmds

from maya_ragdoll import fall as rd

HUB_SECTION = "ragdoll"
SUBTITLE = "skeldarRagdollSubtitle"
STATUS = "skeldarRagdollStatus"
FALL_BTN = "skeldarRagdollFall"
IMPULSE_BTN = "skeldarRagdollImpulse"
DROP_CHIP = "skeldarRagdollDropWeapon"
OPTION = "skeldarRagdoll_settings"
LAYER_TABS = "skeldarRagdollLayers"
LAYERS = (("new", "New layer"), ("base", "Base layer"))

#  (key, label, low, high, step)
SLIDERS = (
    ("length", "Length, fr", 10.0, 300.0, 1.0),
    ("fade", "Muscle fade", 0.0, 60.0, 1.0),
    ("strength", "Strength", 0.0, 4.0, 0.05),
    ("mass", "Mass, kg", 20.0, 300.0, 1.0),
    ("friction", "Friction", 0.0, 2.0, 0.05),
    ("bounce", "Bounce", 0.0, 1.0, 0.05),
)
TIPS = {
    "length": "Frames the fall runs when nothing is highlighted on the time slider",
    "fade": "Frames the muscles hold the pose of the fall's first frame before they let go (0: a "
            "rag doll at once)",
    "strength": "How hard the muscles hold that pose while they fade",
    "mass": "The whole body's mass, shared by de Leva's segment table",
    "friction": "How the body grips the floor and the colliders",
    "bounce": "How much it bounces off them",
    "drop": "A weapon held in a hand is let go at the fall and lands on the floor; its bone "
            "follows it",
    "layer": "New layer: the fall on Ragdoll_<frame>, the take kept under it (mute to see it). Base "
             "layer: the take's keys replaced from the fall on",
    "impulse": "Select a part of a rig: an arrow on it - its tip is where the hit lands, the arrow "
               "its direction; Frame, Speed (m/s) and Enabled in the Channel Box. Fall hits that "
               "part at that frame",
    "fall": "Select any part of a rig (and any meshes to fall onto). The fall starts at the "
            "highlight's first frame, else the current frame",
}
JOB = {}


def _slider(key):
    return "skeldarRagdoll_" + key


def _tab(key):
    return "skeldarRagdollLayer_" + key


def remembered():
    try:
        given = json.loads(cmds.optionVar(query=OPTION)) if cmds.optionVar(exists=OPTION) else None
    except (TypeError, ValueError):
        given = None
    return rd.settings(given)


def remember(s):
    cmds.optionVar(stringValue=(OPTION, json.dumps(s)))


def values():
    """The settings as the card shows them (remembered), else as remembered."""
    s = remembered()
    if cmds.floatSliderGrp(_slider(SLIDERS[0][0]), exists=True):
        for key, *_rest in SLIDERS:
            s[key] = cmds.floatSliderGrp(_slider(key), query=True, value=True)
        s["drop_weapon"] = bool(cmds.checkBox(DROP_CHIP, query=True, value=True))
        for key, _label in LAYERS:
            if cmds.iconTextRadioButton(_tab(key), query=True, select=True):
                s["layer"] = key
    s = rd.settings(s)
    remember(s)
    return s


def status(text):
    import maya_hubstyle as hubstyle
    if cmds.text(STATUS, exists=True):
        cmds.text(STATUS, edit=True, label=text)
        hubstyle.tell(STATUS, text)
    return text


def subtitle():
    """What Fall would drop now."""
    try:
        ref = rd._ref(cmds.ls(selection=True, long=True) or [])
    except rd.Refused as refusal:
        return str(refusal)
    except Exception:                                      # noqa: BLE001
        return rd.NOTHING
    s = remembered()
    a, b = rd.plan.span(rd._highlight(), cmds.currentTime(query=True), s["length"])
    from maya_ragdoll import impulse
    try:
        count = len([p for p in impulse.arrows(ref.rig) if cmds.getAttr(p + ".enabled")])
    except Exception:                                      # noqa: BLE001
        count = 0
    tail = (", %d impulse%s" % (count, "" if count == 1 else "s")) if count else ""
    return "%s falls from frame %d to %d%s" % (ref.label, a, b, tail)


def refresh(*_):
    if cmds.text(SUBTITLE, exists=True):
        cmds.text(SUBTITLE, edit=True, label=subtitle())


def press_fall(*_):
    """Fall: the selected rig drops from the highlight's first frame (else the current one)."""
    s = values()
    try:
        ok, line = _run(s)
        message = line
    except rd.Refused as refusal:
        message = str(refusal)
    except Exception as error:                              # noqa: BLE001 - the card stays usable
        import traceback
        print(traceback.format_exc())
        message = "Ragdoll failed: %s" % error
    refresh()
    return status(message)


def press_impulse(*_):
    """+ Impulse: an arrow on the selected part of a rig."""
    from maya_ragdoll import impulse
    try:
        _arrow, message = impulse.create()
    except rd.Refused as refusal:
        message = str(refusal)
    except Exception as error:                              # noqa: BLE001
        import traceback
        print(traceback.format_exc())
        message = "+ Impulse failed: %s" % error
    refresh()
    return status(message)


def _run(s):
    from maya_poselib import timewalk
    total = int(s["length"]) + 1
    try:
        progress = timewalk.Progress("Ragdoll", total)
    except Exception:                                      # noqa: BLE001 - no UI
        progress = None
    if progress is None:
        return rd.fall(given=s)
    with progress:
        return rd.fall(given=s, progress=lambda t: progress.step("frame %d" % t))


def _changed(*_):
    values()
    refresh()


def build_panel():
    """The card into the current layout."""
    import maya_hubstyle as hubstyle
    s = remembered()
    column = cmds.columnLayout(adjustableColumn=True, rowSpacing=hubstyle.row_spacing(6),
                               columnOffset=("both", hubstyle.pick(0, 8)))
    hubstyle.mark(cmds.text(SUBTITLE, label=rd.NOTHING, align="left"), "subtitle")
    for key, label, low, high, step in SLIDERS:
        cmds.floatSliderGrp(_slider(key), label=label, field=True, minValue=low, maxValue=high,
                            fieldMinValue=low, fieldMaxValue=high * 10, step=step,
                            precision=0 if step >= 1 else 2, value=float(s[key]),
                            columnWidth3=hubstyle.pick((92, 44, 100), (100, 50, 150)),
                            adjustableColumn=3, height=hubstyle.height("small", 22),
                            annotation=TIPS[key], changeCommand=_changed)
    if hubstyle.skinning():
        hubstyle.mark(cmds.flowLayout(wrap=True, columnSpacing=3), "flow", layout=True)
    else:
        cmds.rowLayout(numberOfColumns=1)
    hubstyle.mark(cmds.checkBox(DROP_CHIP, label="Drop weapon", value=bool(s["drop_weapon"]),
                                annotation=TIPS["drop"], changeCommand=_changed), "chip")
    cmds.setParent("..")
    segments = cmds.rowLayout(numberOfColumns=len(LAYERS),
                              columnAttach=[(i + 1, "both", 1) for i in range(len(LAYERS))])
    hubstyle.mark(segments, "segments", layout=True)
    cmds.iconTextRadioCollection(LAYER_TABS)
    for key, label in LAYERS:
        hubstyle.mark(cmds.iconTextRadioButton(
            _tab(key), style="textOnly", label=label, height=hubstyle.height("segment", 24),
            select=key == s["layer"], collection=LAYER_TABS, annotation=TIPS["layer"],
            onCommand=_changed), "segment")
    cmds.setParent("..")
    hubstyle.mark(cmds.rowLayout(numberOfColumns=2, adjustableColumn=2,
                                 columnAttach=[(1, "both", 0), (2, "both", 0)]), "fill", layout=True)
    hubstyle.mark(cmds.button(IMPULSE_BTN, label="+ Impulse", height=hubstyle.height("button", 28),
                              annotation=TIPS["impulse"], command=lambda *_: press_impulse()),
                  "secondary", "plus")
    hubstyle.mark(cmds.button(FALL_BTN, label="Fall", height=hubstyle.height("button", 28),
                              annotation=TIPS["fall"], command=lambda *_: press_fall()),
                  "primary", "skull")
    cmds.setParent("..")
    hubstyle.mark(cmds.text(STATUS, label="", align="left", wordWrap=True, height=54), "status")
    cmds.setParent("..")
    start()
    refresh()
    return column


def _card_key():
    import maya_hubcopy as hubcopy
    scope = hubcopy.current()
    return "" if scope is None else scope.tag


def start():
    """This card's own jobs (a popup copy's die with the copy): the selection and the time."""
    import maya_hubcopy as hubcopy
    standing = set(scope.tag for scope in hubcopy.live())
    for key in [k for k in JOB if k and k not in standing]:
        del JOB[key]
    for old in JOB.pop(_card_key(), []):
        try:
            if cmds.scriptJob(exists=old):
                cmds.scriptJob(kill=old, force=True)
        except Exception:                                  # noqa: BLE001
            pass
    jobs = []
    for event in ("SelectionChanged", "timeChanged"):
        try:
            jobs.append(cmds.scriptJob(event=[event, refresh], parent=STATUS))
        except Exception:                                  # noqa: BLE001
            pass
    JOB[_card_key()] = jobs


def is_open():
    return bool(cmds.text(STATUS, exists=True))


def show_window():
    """The hub, on the Ragdoll section."""
    import maya_hub
    return maya_hub.show(HUB_SECTION)
