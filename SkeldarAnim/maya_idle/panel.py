"""maya_idle.panel - the Idle Builder card (2026-11-06, a draft).

Select skeletons carrying idles, drop a Pose Library card into the well, press Apply: each skeleton's own
idle is rebuilt on the pose (its mean pulled toward the card's, its motion kept and scaled by the knobs).
Apply makes the selected skeletons the WORKING ones; a knob released keys them again. Restore puts a
skeleton's own keys back.
"""
import json
import sys
import traceback

from . import model as im
from . import scene

HUB_SECTION = "idle"
OPTION = "skeldarIdle_"
SUBTITLE = "skeldarIdleSubtitle"
STATUS = "skeldarIdleStatus"
WELL = "skeldarIdleWell"
WELL_TEXT = "skeldarIdleWellText"
APPLY_BTN = "skeldarIdleApply"
RESTORE_BTN = "skeldarIdleRestore"
RESET_BTN = "skeldarIdleReset"
PART_LABELS = (("torso", "Torso"), ("head", "Head"), ("arms", "Arms"), ("legs", "Legs"), ("pelvis", "Pelvis"))
SLIDERS = (
    ("share", "Pose share", "How far the idle's mean pose is pulled toward the card's (0 = the idle as it is)"),
    ("motion", "Motion x", "Every part's motion at once"),
    ("torso", "Torso x", "The spine's motion (breathing, sway)"),
    ("head", "Head x", "The neck's and the head's motion"),
    ("arms", "Arms x", "The arms' motion"),
    ("fingers", "Fingers x", "The fingers' motion"),
    ("pelvis", "Pelvis x", "The pelvis's motion: its place and turn"),
    ("feet", "Feet x", "The feet's own motion (weight shifts); 0 plants them on their mean"),
    ("tempo", "Tempo x", "Speed: 2 plays the idle twice as fast (half the frames)"),
    ("smooth", "Smooth, fr", "A Gaussian over the motion, frames"),
    ("height", "Height, cm", "The pelvis raised or lowered; the legs take it by IK"),
    ("seam", "Seam, fr", "The last frames eased onto the first, so the idle loops"),
)
WEAPON_SLIDERS = (
    ("overlap_l", "Overlap L, ms", "The left hand rides the chest this many ms late (the weapon trails the body)"),
    ("overlap_r", "Overlap R, ms", "The right hand rides the chest this many ms late"),
)
HOLDS = (("hold_l", "Hold L"), ("hold_r", "Hold R"))
JOB = {}


def _cmds():
    import maya.cmds as cmds
    return cmds


def _state():
    return scene._state()


# ---- memory ----

def _stored(name, default):
    cmds = _cmds()
    key = OPTION + name
    return cmds.optionVar(q=key) if cmds.optionVar(exists=key) else default


def _remember(name, value):
    cmds = _cmds()
    if isinstance(value, str):
        cmds.optionVar(sv=(OPTION + name, value))
    else:
        cmds.optionVar(fv=(OPTION + name, float(value)))


def _control(name):
    return OPTION + name + "Slider"


def values():
    cmds = _cmds()
    out = {}
    for name, _label, _tip in SLIDERS + WEAPON_SLIDERS:
        if cmds.floatSliderGrp(_control(name), exists=True):
            out[name] = float(cmds.floatSliderGrp(_control(name), q=True, value=True))
            _remember(name, out[name])
        else:
            out[name] = float(_stored(name, im.DEFAULTS[name]))
    for name, _label in HOLDS:
        box = OPTION + name
        if cmds.checkBox(box, exists=True):
            out[name] = 1.0 if cmds.checkBox(box, q=True, value=True) else 0.0
            _remember(name, out[name])
        else:
            out[name] = float(_stored(name, im.DEFAULTS[name]))
    return out


def parts():
    cmds = _cmds()
    out = []
    for key, _label in PART_LABELS:
        box = OPTION + "part_" + key
        if cmds.checkBox(box, exists=True):
            on = bool(cmds.checkBox(box, q=True, value=True))
            _remember("part_" + key, 1.0 if on else 0.0)
        else:
            on = float(_stored("part_" + key, 1.0)) >= 0.5
        if on:
            out.append(key)
    return tuple(out)


# ---- the pose cards ----

def card_list():
    try:
        return [p for p in json.loads(_stored("cards", "[]")) if isinstance(p, str) and p]
    except ValueError:
        return []


def chosen_card():
    path = _stored("card", "")
    return path or None


def _set_cards(paths, active):
    seen = []
    for p in paths:
        if p and p not in seen:
            seen.append(p)
    _remember("cards", json.dumps(seen))
    _remember("card", active or "")
    _show_well()


def well_rows():
    import os
    from maya_walk import cards as wcards
    active = chosen_card()
    rows = []
    for path in card_list():
        name = wcards.card_name(path)
        if not os.path.isdir(path):
            rows.append((path, name, "", "the card is gone from the library", path == active))
            continue
        thumb = os.path.join(path, "thumbnail.jpg")
        rows.append((path, name, thumb if os.path.isfile(thumb) else "", "", path == active))
    return rows


def take_card(path):
    def run():
        name, _bones = scene.card_bones(path)
        paths = card_list()
        if path not in paths:
            paths.append(path)
        _set_cards(paths, path)
        return _rekey("pose card %s" % name)
    return _run(run)


def pick_card(path):
    return take_card(path)


def remove_card(path):
    paths = [p for p in card_list() if p != path]
    active = chosen_card()
    _set_cards(paths, (paths[0] if paths else "") if active == path else active)
    return _rekey("card removed")


def remove_all_cards():
    _set_cards([], "")
    return _rekey("no pose")


def clear_card():
    _set_cards(card_list(), "")
    return _rekey("no pose: the idle's own posture")


def show_card(path):
    from maya_poselib import window as library
    library.show_window()


class _Scene(object):
    """What the well asks (maya_walk.posewell's Scene, answered by Idle Builder)."""

    def scale(self):
        try:
            return float(_cmds().mayaDpiSetting(query=True, realScaleValue=True) or 1.0)
        except Exception:                                    # noqa: BLE001
            return 1.0

    def cards(self):
        return well_rows()

    def take(self, path):
        return take_card(path)

    def pick(self, path):
        return pick_card(path)

    def remove(self, path):
        return remove_card(path)

    def remove_all(self):
        return remove_all_cards()

    def clear(self):
        return clear_card()

    def show(self, path):
        return show_card(path)


def _show_well():
    cmds = _cmds()
    if cmds.text(WELL_TEXT, exists=True):
        from maya_walk import cards as wcards
        active = chosen_card()
        cmds.text(WELL_TEXT, edit=True, label="Pose: %s" % (wcards.card_name(active) if active else
                                                         "none - Pose Library card dragged into the well"))
    try:
        from maya_walk import posewell
        posewell.refresh_all()
    except Exception:                                        # noqa: BLE001
        pass


# ---- the presses ----

def _say(text):
    cmds = _cmds()
    if cmds.text(STATUS, exists=True):
        cmds.text(STATUS, edit=True, label=text)
    try:
        import maya_hub
        maya_hub.say(text)
    except Exception:                                        # noqa: BLE001
        pass
    return text


def _run(fn):
    try:
        return _say(fn() or "")
    except (scene.Refusal, im.Refusal) as error:
        return _say(str(error))
    except Exception as error:                               # noqa: BLE001
        print(traceback.format_exc())
        return _say("Idle Builder: %s" % error)


def working():
    cmds = _cmds()
    out = []
    for uuid in _state().get("working", []):
        found = cmds.ls(uuid, long=True) or []
        if found:
            out.append(found[0])
    return out


def _apply_on(roots):
    lines = []
    for root in roots:
        try:
            lines.append(scene.apply(root, values(), chosen_card(), parts()))
        except (scene.Refusal, im.Refusal) as error:
            lines.append("%s: %s" % (scene._short(root), error))
    return " | ".join(lines)


def press_apply():
    def run():
        roots = scene.selected_tops()
        if not roots:
            return "Select a bone of each skeleton with an idle"
        cmds = _cmds()
        _state()["working"] = [u for r in roots for u in (cmds.ls(r, uuid=True) or [])]
        return _apply_on(roots)
    return _run(run)


def _rekey(line):
    roots = working()
    if not roots:
        return line + " - select skeletons and press Apply"
    return line + " | " + _apply_on(roots)


def press_restore():
    def run():
        roots = scene.selected_tops() or working()
        if not roots:
            return "Select a skeleton built by Idle Builder"
        return " | ".join(scene.restore(r) for r in roots)
    return _run(run)


def press_reset():
    cmds = _cmds()
    for name, _label, _tip in SLIDERS + WEAPON_SLIDERS:
        if cmds.floatSliderGrp(_control(name), exists=True):
            cmds.floatSliderGrp(_control(name), edit=True, value=im.DEFAULTS[name])
        _remember(name, im.DEFAULTS[name])
    return _run(lambda: _rekey("knobs back to defaults"))


def knob_changed(*_):
    return _run(lambda: _rekey("knob"))


# ---- the card ----

def _button(name, label, role, icon, tip, press):
    import maya_hubstyle as hubstyle
    return hubstyle.mark(_cmds().button(name, label=label, annotation=tip,
                                        height=hubstyle.height("button", 28),
                                        command=lambda *_: press()), role, icon)


def build_panel():
    import maya_hubstyle as hubstyle
    cmds = _cmds()
    column = cmds.columnLayout(adjustableColumn=True, rowSpacing=hubstyle.row_spacing(6),
                               columnOffset=("both", hubstyle.pick(0, 8)))
    hubstyle.mark(cmds.text(SUBTITLE, label="", align="left"), "subtitle")
    cmds.columnLayout(WELL, adjustableColumn=True,
                      annotation="Drag a pose card from the Pose Library here")
    cmds.setParent("..")
    well = None
    try:
        from maya_walk import posewell
        well = posewell.attach(WELL, scene=_Scene())
    except Exception:                                        # noqa: BLE001
        print(traceback.format_exc())
    if well is None:
        cmds.text(WELL_TEXT, label="", align="left")
        _show_well()
    cmds.rowLayout(numberOfColumns=len(PART_LABELS))
    for key, label in PART_LABELS:
        hubstyle.mark(cmds.checkBox(OPTION + "part_" + key, label=label,
                                    value=float(_stored("part_" + key, 1.0)) >= 0.5,
                                    annotation="What of the pose comes in",
                                    changeCommand=knob_changed), "chip")
    cmds.setParent("..")
    for name, label, tip in SLIDERS:
        low, high = im.RANGES[name]
        cmds.floatSliderGrp(_control(name), label=label, field=True, minValue=low, maxValue=high,
                            fieldMinValue=low, fieldMaxValue=high, step=0.05, precision=2,
                            value=float(_stored(name, im.DEFAULTS[name])),
                            columnWidth3=hubstyle.pick((92, 44, 100), (100, 50, 150)), adjustableColumn=3,
                            height=hubstyle.height("small", 22), annotation=tip, changeCommand=knob_changed)
    hubstyle.mark(cmds.text(OPTION + "weaponHeading", label="Weapon", align="left"), "heading")
    cmds.rowLayout(numberOfColumns=len(HOLDS))
    for name, label in HOLDS:
        hubstyle.mark(cmds.checkBox(OPTION + name, label=label,
                                    value=float(_stored(name, im.DEFAULTS[name])) >= 0.5,
                                    annotation="The hand rides the chest rigidly at its mean offset, so it holds "
                                               "the pose's grip on the torso (needs a pose with Arms on)",
                                    changeCommand=knob_changed), "chip")
    cmds.setParent("..")
    for name, label, tip in WEAPON_SLIDERS:
        low, high = im.RANGES[name]
        cmds.floatSliderGrp(_control(name), label=label, field=True, minValue=-500.0, maxValue=500.0,
                            fieldMinValue=low, fieldMaxValue=high, step=1.0, precision=0,
                            value=float(_stored(name, im.DEFAULTS[name])),
                            columnWidth3=hubstyle.pick((92, 44, 100), (100, 50, 150)), adjustableColumn=3,
                            height=hubstyle.height("small", 22), annotation=tip, changeCommand=knob_changed)
    cmds.rowLayout(numberOfColumns=3, adjustableColumn=1,
                   columnAttach=[(1, "both", 0), (2, "both", 4), (3, "both", 4)])
    _button(APPLY_BTN, "Apply", "primary", "user", "The selected skeletons' idles rebuilt on the pose", press_apply)
    _button(RESTORE_BTN, "Restore", "secondary", "arrow-back-up", "Their own keys back", press_restore)
    _button(RESET_BTN, "Reset", "secondary", "refresh", "The knobs back to their defaults", press_reset)
    cmds.setParent("..")
    hubstyle.mark(cmds.text(STATUS, label="", align="left", wordWrap=True, height=54), "status")
    cmds.setParent("..")
    start()
    refresh()
    return column


def refresh():
    cmds = _cmds()
    if not cmds.text(SUBTITLE, exists=True):
        return
    roots = scene.selected_tops()
    work = working()
    if roots:
        built = sum(1 for r in roots if scene.has_source(r))
        text = "%d skeleton(s) selected%s" % (len(roots), (", %d built" % built) if built else "")
    else:
        text = "Select skeletons with idles"
    if work:
        text += " | working: %d" % len(work)
    cmds.text(SUBTITLE, edit=True, label=text)


def _card_key():
    import maya_hubcopy as hubcopy
    scope = hubcopy.current()
    return "" if scope is None else scope.tag


def start():
    import maya_hubcopy as hubcopy
    cmds = _cmds()
    standing = set(scope.tag for scope in hubcopy.live())
    for key in [k for k in JOB if k and k not in standing]:
        del JOB[key]
    old = JOB.pop(_card_key(), None)
    if old is not None:
        try:
            if cmds.scriptJob(exists=old):
                cmds.scriptJob(kill=old, force=True)
        except Exception:                                    # noqa: BLE001
            pass
    import maya_hubqt
    JOB[_card_key()] = cmds.scriptJob(event=["SelectionChanged", maya_hubqt.seen_only(STATUS, refresh)],
                                      parent=STATUS)


def is_open():
    return bool(_cmds().text(STATUS, exists=True))


def show_window():
    import maya_hub
    return maya_hub.show(HUB_SECTION)
