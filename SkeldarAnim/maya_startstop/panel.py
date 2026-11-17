"""maya_startstop.panel - the Start/Stop Builder card (2026-11-17).

Select skeletons carrying a start or a stop, drop a Pose Library card into the Stand pose well, press Apply:
each skeleton's own clip is rebuilt on the pose - the steps it stands on (a stop's last, a start's first) on the
pose's stance, the run in the run pose, the clip's motion over both, Walk Builder's knobs on top - and keyed onto
the skeleton itself. Apply makes the selected skeletons the WORKING ones; a knob released keys them again.
Restore puts a skeleton's own keys back. A cycle (Use selected) is where a stop starts and a start ends.

Pose on clip's window (docs/superpowers/plans/poseclip/poseclip_tool.py until 2026-11-17) as a hub card, Idle
Builder's way. The animator: «У нас где-то был инструмент который обрабытвал старты и стопы анимаций можешь
встроить его в реил?» Spec: docs/superpowers/specs/2026-11-17-start-stop-builder-design.md
"""
import json
import traceback

from . import model
from . import scene

HUB_SECTION = "startstop"
OPTION = "skeldarStartStop_"
SUBTITLE = "skeldarStartStopSubtitle"
STATUS = "skeldarStartStopStatus"
CYCLE_TEXT = "skeldarStartStopCycle"
APPLY_BTN = "skeldarStartStopApply"
RESTORE_BTN = "skeldarStartStopRestore"
RESET_BTN = "skeldarStartStopReset"
CYCLE_BTN = "skeldarStartStopUseCycle"
CLEAR_BTN = "skeldarStartStopClearCycle"
LIST = "skeldarStartStopList"
RUN_TABS = "skeldarStartStopRunTabs"
GROUP_TABS = "skeldarStartStopGroupTabs"
SIDE_TABS = "skeldarStartStopSideTabs"
RUN_COLUMN = "skeldarStartStopRunColumn"
PART_LABELS = (("torso", "Torso"), ("pelvis", "Pelvis"), ("knees", "Knees"), ("arms", "Arms"), ("feet", "Feet"))
#  the two poses: (which, the model's knob prefix, the well, its heading)
POSES = (("stand", "share", "skeldarStartStopStandWell", "Stand pose"),
         ("run", "start", "skeldarStartStopRunWell", "Run pose"))
RUN_MODES = (("stand", "Stand", "The stand pose all along"),
             ("clip", "Clip", "The clip's own run posture - with a cycle set, the cycle's posture"),
             ("card", "Card", "The pose card in the run well"))
SIDE_MODES = (("both", "Both"), ("l", "Left"), ("r", "Right"))
SIDE_MARK = {"l": "  L", "r": "  R"}
#  (key, tab, ((knob, label, tooltip), ...)) - Walk Builder's names where the knob is Walk Builder's
GROUPS = (
    ("timing", "Timing", (
        ("final_speed", "Stand pose at, cm/s", "The run pose is all there is while the body moves faster; the "
                                               "stand pose comes in as it slows to this"),
        ("stance_speed", "Stance at, cm/s", "The pose's stance (its width, its balance over its feet) is gone "
                                            "at this speed and comes in as the body stands"),
        ("from_cycle", "Cycle blend, fr", "With a cycle set: frames a stop takes from the cycle's frames into its "
                                          "own, and a start from its own into the cycle's"))),
    ("legs", "Legs", (
        ("stance", "Stance x", "x each foot's place across the stance (the pose's width): 0 the feet together"),
        ("lift", "Foot lift x", "x the swinging foot's height over its line from takeoff to landing"),
        ("swing_out", "Swing out, cm", "The swing bowed out (+) or in (-), sideways"),
        ("leg_match", "Leg match", "Running, a side-on pose's hips face the run and its knees and toes keep only "
                                   "the splay the gait allows; standing, the pose stands as it is"),
        ("leg_turn", "Leg turn x", "x the poses' knee and toe turns"),
        ("knee_foot", "Knee <-> foot", "A knee and its foot turned apart past 15 deg meet: 0 the knee goes to "
                                       "the foot, 1 the foot to the knee"),
        ("foot_lag", "Foot lag, fr", "Frames the swinging foot trails its shin"),
        ("foot_flex", "Foot flex x", "x the swinging foot's turn in its ankle (and the toes')"))),
    ("pelvis", "Pelvis", (
        ("pelvis_height", "Height, cm", "The pelvis up (+) or down (-) - the legs follow by IK"),
        ("pelvis_forward", "Forward, cm", "The hips ahead (+) or behind (-) of where the balance puts them"),
        ("bob", "Bob x", "x the pelvis's up and down"),
        ("pelvis_rot", "Pelvis turns x", "x the pelvis's turns over the reference"))),
    ("chest", "Chest", (
        ("spine", "Spine x", "x the spine's and the neck's motion"),
        ("gait_lean", "Gait lean", "x the forward lean the clip's motion keeps (in the room the pose leaves)"),
        ("lean_limit", "Lean limit, deg", "The trunk's forward lean never past this"),
        ("head", "Head x", "x the head's motion in the world; 0 keeps the pose's gaze"),
        ("torso_drag", "Torso drag, fr", "Overlap: frames the trunk trails its motion by"),
        ("torso_bounce", "Torso bounce", "How far the trunk and the head overshoot"),
        ("head_drag", "Head drag, fr", "Frames the head trails its gaze by"))),
    ("arms", "Arms", (
        ("arms", "Arms x", "x the clip's motion in the arms and fingers"),
        ("elbow", "Elbow x", "x the forearm's own motion in the elbow, on top of Arms"),
        ("arm_drag", "Arm drag, fr", "Overlap: frames the arms trail by"),
        ("arm_bounce", "Arm bounce", "How far the arms overshoot"))),
    ("weapon", "Weapon", (                 # Walk Builder's Weapon tab (2026-11-17, maya_startstop.weapon)
        ("weapon_hold", "Hold", "The hand rides the chest rigidly at its own (slow) offset from it - where a pose "
                                "holds the arm, or the scene gives the hand a weapon - and takes no arm spring"),
        ("weapon_inherit", "Inherit", "The share of the chest's own motion a held hand takes: 1 all of it, 0 only "
                                      "its slow motion (running into the stance, the crouch)"),
        ("weapon_overlap", "Overlap, ms", "The chest the held hand rides is this old - the weapon trails the body"),
        ("weapon_aim", "Aim target", "The blade swung about its grip onto a target keeping this share of its own "
                                     "motion - the weapon's weight (no weapon in the scene: weapon_r stands for one)"),
        ("weapon_shoulder", "Shoulder", "The share of the arm's reach changes the clavicle takes, so the elbow "
                                        "is not overstretched"))),
    ("weight", "Weight", (
        ("balance", "Balance", "How far the pelvis is carried to keep the centre of mass over the feet"),
        ("exaggeration", "Exaggeration x", "x every motion of the clip: spine, pelvis, bob, head, arms"))),
)
GROUP_ROWS = (("timing", "legs", "pelvis", "chest"), ("arms", "weapon", "weight"))
TOGGLES = ("weapon_hold",)          # a chip, not a slider
JOB = {}
_QUIET = [False]       # set while the card fills itself: a control's command does nothing
_LISTED = []           # the paths the list shows, row by row (1-based rows = index + 1)


def _cmds():
    import maya.cmds as cmds
    return cmds


# ---- memory: optionVars are the card's truth (a side's slider shows one side of a knob) ----

def _stored(name, default):
    cmds = _cmds()
    key = OPTION + name
    if not cmds.optionVar(exists=key):
        return default
    value = cmds.optionVar(query=key)
    if isinstance(default, float):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default
    return value


def _remember(name, value):
    cmds = _cmds()
    if isinstance(value, str):
        cmds.optionVar(stringValue=(OPTION + name, value))
    else:
        cmds.optionVar(floatValue=(OPTION + name, float(value)))


def _forget(name):
    cmds = _cmds()
    if cmds.optionVar(exists=OPTION + name):
        cmds.optionVar(remove=OPTION + name)


def _slider(name):
    return OPTION + name + "Slider"


def _part_box(which, part):
    return "%spart_%s_%s" % (OPTION, which, part)


def _share_slider(which):
    return "%s%sShareSlider" % (OPTION, which)


def _group_tab(key):
    return "skeldarStartStopGroupTab_" + key


def _group_column(key):
    return "skeldarStartStopGroup_" + key


def _side_tab(mode):
    return "skeldarStartStopSide_" + mode


def _run_tab(mode):
    return "skeldarStartStopRun_" + mode


def side_mode():
    mode = _stored("side", "both")
    return mode if mode in dict(SIDE_MODES) else "both"


def run_mode():
    mode = _stored("runMode", "stand")
    return mode if mode in dict((m, l) for m, l, _ in RUN_MODES) else "stand"


def part_on(which, part):
    return _stored("part_%s_%s" % (which, part), 1.0) >= 0.5


def share(which):
    return min(max(_stored(which + "Share", 1.0), 0.0), 1.0)


def _side_value(name, side):
    """A two-sided knob as one side reads it: its own value where it has one, else the knob's."""
    return _stored("%s_%s" % (name, side), _stored(name, model.DEFAULTS[name]))


def knob_names():
    return [name for _key, _tab, rows in GROUPS for name, _label, _tip in rows]


def values():
    """Every knob as the card holds it: the groups' knobs (and a side's own values), each pose's Share x its lit
    parts (`share_<part>` for the stand pose, `start_<part>` for the run pose)."""
    given = {}
    for name in knob_names():
        given[name] = _stored(name, model.DEFAULTS[name])
    for name in model.SIDED:
        for side in model.SIDES:
            if _cmds().optionVar(exists=OPTION + "%s_%s" % (name, side)):
                given["%s_%s" % (name, side)] = _side_value(name, side)
    for which, prefix, _well, _head in POSES:
        amount = share(which)
        for part, _label in PART_LABELS:
            given["%s_%s" % (prefix, part)] = amount if part_on(which, part) else 0.0
    return model.knobs(**given)


# ---- the pose cards: one list and one active card a well ----

def card_list(which):
    try:
        return [p for p in json.loads(_stored(which + "Cards", "[]")) if isinstance(p, str) and p]
    except ValueError:
        return []


def chosen_card(which):
    return _stored(which + "Card", "") or None


def _set_cards(which, paths, active):
    seen = []
    for p in paths:
        if p and p not in seen:
            seen.append(p)
    _remember(which + "Cards", json.dumps(seen))
    _remember(which + "Card", active or "")
    _show_wells()


def well_rows(which):
    import os
    from maya_walk import cards as wcards
    active = chosen_card(which)
    rows = []
    for path in card_list(which):
        name = wcards.card_name(path)
        if not os.path.isdir(path):
            rows.append((path, name, "", "the card is gone from the library", path == active))
            continue
        thumb = os.path.join(path, "thumbnail.jpg")
        rows.append((path, name, thumb if os.path.isfile(thumb) else "", "", path == active))
    return rows


def take_card(which, path):
    def run():
        from maya_walk import cards as wcards
        try:
            name, _bones = wcards.read_card(path)
        except wcards.Refusal as error:
            raise scene.Refusal(str(error))
        paths = card_list(which)
        if path not in paths:
            paths.append(path)
        _set_cards(which, paths, path)
        if which == "run" and run_mode() != "card":
            _set_run_mode("card")
        return _rekey("%s pose card %s" % (which, name))
    return _run(run)


def remove_card(which, path):
    paths = [p for p in card_list(which) if p != path]
    active = chosen_card(which)
    _set_cards(which, paths, (paths[0] if paths else "") if active == path else active)
    return _run(lambda: _rekey("card removed"))


def remove_all_cards(which):
    _set_cards(which, [], "")
    return _run(lambda: _rekey("no %s pose" % which))


def clear_card(which):
    _set_cards(which, card_list(which), "")
    return _run(lambda: _rekey("no %s pose: the clip's own posture" % which))


def show_card(path):
    from maya_poselib import window as library
    library.show_window()


class WellScene(object):
    """What a well asks (maya_walk.posewell's Scene), answered for the stand or the run pose."""

    def __init__(self, which):
        self.which = which

    def scale(self):
        try:
            return float(_cmds().mayaDpiSetting(query=True, realScaleValue=True) or 1.0)
        except Exception:                                    # noqa: BLE001
            return 1.0

    def cards(self):
        return well_rows(self.which)

    def take(self, path):
        return take_card(self.which, path)

    def pick(self, path):
        return take_card(self.which, path)

    def remove(self, path):
        return remove_card(self.which, path)

    def remove_all(self):
        return remove_all_cards(self.which)

    def clear(self):
        return clear_card(self.which)

    def show(self, path):
        return show_card(path)


def _well_text(which):
    return "skeldarStartStop%sWellText" % which.capitalize()


def _show_wells():
    cmds = _cmds()
    from maya_walk import cards as wcards
    for which, _prefix, _well, head in POSES:
        if cmds.text(_well_text(which), exists=True):
            active = chosen_card(which)
            cmds.text(_well_text(which), edit=True,
                      label="%s: %s" % (head, wcards.card_name(active) if active else "none - drag a Pose Library "
                                                                                       "card into the well"))
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


def _refusals():
    from maya_walk import scene as ws
    return (scene.Refusal, model.Refusal, ws.Refusal)


def _run(fn):
    try:
        return _say(fn() or "")
    except _refusals() as error:
        return _say(str(error))
    except Exception as error:                               # noqa: BLE001
        print(traceback.format_exc())
        return _say("Start/Stop Builder: %s (the Script Editor has the trace)" % error)


def working():
    cmds = _cmds()
    out = []
    for uuid in scene._state().get("working", []):
        found = cmds.ls(uuid, long=True) or []
        if found:
            out.append(found[0])
    return out


def _set_working(roots):
    cmds = _cmds()
    scene._state()["working"] = [u for r in roots for u in (cmds.ls(r, uuid=True) or [])]
    show_list()


def _apply_on(roots):
    import time
    began = time.time()
    lines, failed = [], []
    k = values()
    stand, mode, run = chosen_card("stand"), run_mode(), chosen_card("run")
    progress = len(roots) > 1 and not _cmds().about(batch=True)
    if progress:
        _cmds().progressWindow(title="Start/Stop Builder", progress=0, maxValue=len(roots), isInterruptable=True,
                               status="%d skeletons" % len(roots))
    try:
        for i, root in enumerate(roots):
            if progress:
                if _cmds().progressWindow(query=True, isCancelled=True):
                    failed.append("cancelled after %d" % i)
                    break
                _cmds().progressWindow(edit=True, progress=i, status=scene.label(root))
            try:
                lines.append(scene.apply(root, k, stand, mode, run))
            except _refusals() as error:
                failed.append("%s: %s" % (scene.label(root), error))
    finally:
        if progress:
            _cmds().progressWindow(endProgress=True)
    if len(roots) == 1:
        return " | ".join(lines + failed)
    text = "%d of %d skeletons keyed in %.1f s" % (len(lines), len(roots), time.time() - began)
    return text + (" | " + " | ".join(failed) if failed else "")


def press_apply():
    def run():
        roots = scene.selected_tops() or working()
        if not roots:
            return "Select a bone of each skeleton carrying a start or a stop"
        work = working()
        _set_working(work + [r for r in roots if r not in work])
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
            return "Select a skeleton built by Start/Stop Builder"
        lines = [scene.restore(r) for r in roots if scene.has_source(r)]
        _set_working([r for r in working() if r not in roots])
        return " | ".join(lines) or "nothing built among them"
    return _run(run)


def press_reset():
    """Every knob to its default, both sides linked; the poses, their shares and parts kept."""
    cmds = _cmds()
    _QUIET[0] = True
    try:
        for name in knob_names():
            _remember(name, model.DEFAULTS[name])
            if name in model.SIDED:
                for side in model.SIDES:
                    _forget("%s_%s" % (name, side))
            if name in TOGGLES:
                if cmds.checkBox(_slider(name), exists=True):
                    cmds.checkBox(_slider(name), edit=True, value=model.DEFAULTS[name] >= 0.5)
            elif cmds.floatSliderGrp(_slider(name), exists=True):
                cmds.floatSliderGrp(_slider(name), edit=True, value=model.DEFAULTS[name])
    finally:
        _QUIET[0] = False
    show_side(side_mode())
    return _run(lambda: _rekey("knobs back to their defaults"))


def knob_changed(name):
    """A slider let go: remembered (a two-sided knob for the side the row shows, or both sides linked again in
    Both), the working skeletons keyed again."""
    def changed(*_):
        if _QUIET[0]:
            return None
        cmds = _cmds()
        if name in TOGGLES:
            value = 1.0 if cmds.checkBox(_slider(name), query=True, value=True) else 0.0
        else:
            value = float(cmds.floatSliderGrp(_slider(name), query=True, value=True))
        side = side_mode()
        if name in model.SIDED and side != "both":
            _remember("%s_%s" % (name, side), value)
        else:
            _remember(name, value)
            if name in model.SIDED:
                for s in model.SIDES:
                    _forget("%s_%s" % (name, s))
        show_side(side)
        return _run(lambda: _rekey(_label_of(name)))
    return changed


def share_changed(which):
    def changed(*_):
        if _QUIET[0]:
            return None
        _remember(which + "Share", float(_cmds().floatSliderGrp(_share_slider(which), query=True, value=True)))
        return _run(lambda: _rekey("%s pose share" % which))
    return changed


def part_changed(which, part):
    def changed(*_):
        if _QUIET[0]:
            return None
        on = bool(_cmds().checkBox(_part_box(which, part), query=True, value=True))
        _remember("part_%s_%s" % (which, part), 1.0 if on else 0.0)
        return _run(lambda: _rekey("%s pose %s" % (which, part)))
    return changed


def _set_run_mode(mode):
    """The run mode remembered and shown (the run well and its share only for Card)."""
    cmds = _cmds()
    _remember("runMode", mode)
    _QUIET[0] = True
    try:
        if cmds.iconTextRadioButton(_run_tab(mode), exists=True):
            cmds.iconTextRadioButton(_run_tab(mode), edit=True, select=True)
    finally:
        _QUIET[0] = False
    if cmds.columnLayout(RUN_COLUMN, exists=True):
        cmds.columnLayout(RUN_COLUMN, edit=True, manage=mode == "card")


def run_changed(mode):
    def changed(*_):
        if _QUIET[0]:
            return None
        _set_run_mode(mode)
        return _run(lambda: _rekey("run pose: %s" % dict((m, l) for m, l, _ in RUN_MODES)[mode]))
    return changed


def _label_of(name):
    for _key, _tab, rows in GROUPS:
        for knob, label, _tip in rows:
            if knob == name:
                return label
    return name


def show_side(mode):
    """The two-sided sliders as the side row reads them: Both - the knob, marked * where its sides differ; Left
    or Right - that side's value, its label marked L or R."""
    cmds = _cmds()
    _remember("side", mode)
    _QUIET[0] = True
    try:
        if cmds.iconTextRadioButton(_side_tab(mode), exists=True):
            cmds.iconTextRadioButton(_side_tab(mode), edit=True, select=True)
        for name in model.SIDED:
            control = cmds.checkBox if name in TOGGLES else cmds.floatSliderGrp
            if not control(_slider(name), exists=True):
                continue
            label = _label_of(name)
            if mode == "both":
                base = _stored(name, model.DEFAULTS[name])
                differ = any(abs(_side_value(name, s) - base) > 1e-6 for s in model.SIDES)
                value, label = base, label + (" *" if differ else "")
            else:
                value, label = _side_value(name, mode), label + SIDE_MARK[mode]
            control(_slider(name), edit=True, value=(value >= 0.5) if name in TOGGLES else value, label=label)
    finally:
        _QUIET[0] = False


def side_changed(mode):
    def changed(*_):
        if not _QUIET[0]:
            show_side(mode)
    return changed


def show_group(key):
    """Show the knob group `key` alone: its column managed, its tab lit, remembered."""
    cmds = _cmds()
    if key not in dict((k, t) for k, t, _ in GROUPS):
        key = GROUPS[0][0]
    _remember("group", key)
    for each, _tab, _rows in GROUPS:
        if cmds.columnLayout(_group_column(each), exists=True):
            cmds.columnLayout(_group_column(each), edit=True, manage=each == key)
    if cmds.iconTextRadioButton(_group_tab(key), exists=True):
        _QUIET[0] = True
        try:
            cmds.iconTextRadioButton(_group_tab(key), edit=True, select=True)
        finally:
            _QUIET[0] = False


def group_changed(key):
    def changed(*_):
        if not _QUIET[0]:
            show_group(key)
    return changed


# ---- the cycle ----

def show_cycle():
    cmds = _cmds()
    if not cmds.text(CYCLE_TEXT, exists=True):
        return
    current = scene.cycle()
    cmds.text(CYCLE_TEXT, edit=True, label=("Cycle: " + current["name"]) if current else
              "No cycle: a stop starts and a start ends as its clip does")


def press_use_cycle():
    def run():
        selection = _cmds().ls(selection=True, long=True)
        if not selection:
            return "Select the skeleton carrying the looping clip (a bone, a mesh), then Use selected"
        name = scene.use_cycle(selection[0])
        show_cycle()
        return _rekey("cycle: " + name)
    return _run(run)


def press_clear_cycle():
    def run():
        scene.clear_cycle()
        show_cycle()
        return _rekey("no cycle")
    return _run(run)


# ---- the list of skeletons ----

def show_list():
    """Every built skeleton, the working ones marked; the working ones picked in the list."""
    cmds = _cmds()
    if not cmds.textScrollList(LIST, exists=True):
        return
    work = working()
    rows = scene.built()
    for r in work:
        if r not in rows:
            rows.append(r)
    _LISTED[:] = rows
    cmds.textScrollList(LIST, edit=True, removeAll=True)
    for r in rows:
        kind = (scene.memo(r) or {}).get("transition") or ""
        cmds.textScrollList(LIST, edit=True, append=("> " if r in work else "   ") + scene.label(r) +
                            ("  (%s)" % kind if kind else ""))
    picked = [i + 1 for i, r in enumerate(rows) if r in work]
    if picked:
        cmds.textScrollList(LIST, edit=True, selectIndexedItem=picked)


def _list_rows():
    cmds = _cmds()
    picked = cmds.textScrollList(LIST, query=True, selectIndexedItem=True) or []
    return [_LISTED[i - 1] for i in picked if 0 < i <= len(_LISTED)]


def list_picked(*_):
    """Rows clicked in the list: those skeletons are the working ones (a knob keys them), selected in the scene."""
    roots = _list_rows()
    _set_working(roots)
    if roots:
        _cmds().select(roots, replace=True)
    refresh()
    return _say("working: %d skeleton(s) - a knob keys them, Apply keys them now" % len(roots))


def list_select_all(*_):
    _set_working(list(_LISTED))
    if _LISTED:
        _cmds().select(_LISTED, replace=True)
    refresh()
    return _say("working: all %d skeletons" % len(_LISTED))


def list_key_now(*_):
    return _run(lambda: _apply_on(working()) if working() else "pick skeletons in the list")


def list_restore(*_):
    def run():
        roots = _list_rows()
        lines = [scene.restore(r) for r in roots if scene.has_source(r)]
        _set_working([r for r in working() if r not in roots])
        return " | ".join(lines) or "nothing picked"
    return _run(run)


# ---- the card ----

def _button(name, label, role, icon, tip, press):
    import maya_hubstyle as hubstyle
    return hubstyle.mark(_cmds().button(name, label=label, annotation=tip, height=hubstyle.height("button", 28),
                                        command=lambda *_: press()), role, icon)


def _float_slider(name, label, low, high, value, tip, command, precision=2):
    import maya_hubstyle as hubstyle
    _cmds().floatSliderGrp(name, label=label, field=True, minValue=low, maxValue=high, fieldMinValue=low,
                           fieldMaxValue=high, step=(high - low) / 100.0, precision=precision, value=value,
                           columnWidth3=hubstyle.pick((104, 48, 100), (112, 52, 150)), adjustableColumn=3,
                           height=hubstyle.height("small", 22), annotation=tip, changeCommand=command)


def _well(which, placeholder):
    """The pose well over a `cmds` placeholder; where it cannot stand, a line saying the card."""
    cmds = _cmds()
    cmds.columnLayout(placeholder, adjustableColumn=True, annotation="Drag a pose card from the Pose Library here")
    cmds.setParent("..")
    well = None
    try:
        from maya_walk import posewell
        well = posewell.attach(placeholder, scene=WellScene(which))
    except Exception:                                        # noqa: BLE001
        print(traceback.format_exc())
    if well is None:
        cmds.text(_well_text(which), label="", align="left")


def _pose_rows(which):
    """A pose's Share and the parts it takes, as chips."""
    import maya_hubstyle as hubstyle
    cmds = _cmds()
    _float_slider(_share_slider(which), "Share", 0.0, 1.0, share(which),
                  "How much of the %s pose the lit parts take" % which, share_changed(which))
    cmds.rowLayout(numberOfColumns=len(PART_LABELS))
    for part, label in PART_LABELS:
        hubstyle.mark(cmds.checkBox(_part_box(which, part), label=label, value=part_on(which, part),
                                    annotation="The %s pose's %s" % (which, label.lower()),
                                    changeCommand=part_changed(which, part)), "chip")
    cmds.setParent("..")


def _segments(collection, items, selected, command, tab_name):
    import maya_hubstyle as hubstyle
    cmds = _cmds()
    row = cmds.rowLayout(numberOfColumns=len(items), columnAttach=[(i + 1, "both", 1) for i in range(len(items))])
    hubstyle.mark(row, "segments", layout=True)
    cmds.iconTextRadioCollection(collection)
    for key, label, tip in items:
        hubstyle.mark(cmds.iconTextRadioButton(
            tab_name(key), style="textOnly", label=label, height=hubstyle.height("segment", 24),
            select=key == selected, collection=collection, annotation=tip, onCommand=command(key)), "segment")
    cmds.setParent("..")


def build_panel():
    import maya_hubstyle as hubstyle
    cmds = _cmds()
    column = cmds.columnLayout(adjustableColumn=True, rowSpacing=hubstyle.row_spacing(6),
                               columnOffset=("both", hubstyle.pick(0, 8)))
    hubstyle.mark(cmds.text(SUBTITLE, label="", align="left"), "subtitle")
    _QUIET[0] = True
    try:
        # the stand pose: what the body stands in (a stop's end, a start's beginning)
        hubstyle.mark(cmds.text(OPTION + "standHeading", label="Stand pose", align="left",
                                annotation="The pose the body stands in: a stop's end, a start's beginning - its "
                                           "steps there land on this pose's stance"), "heading")
        _well("stand", POSES[0][2])
        _pose_rows("stand")
        # the run pose
        hubstyle.mark(cmds.text(OPTION + "runHeading", label="Run pose", align="left",
                                annotation="The pose the body runs in; the stand pose comes in as it slows"),
                      "heading")
        mode = run_mode()
        _segments(RUN_TABS, RUN_MODES, mode, run_changed, _run_tab)
        cmds.columnLayout(RUN_COLUMN, adjustableColumn=True, rowSpacing=hubstyle.row_spacing(4),
                          manage=mode == "card")
        _well("run", POSES[1][2])
        _pose_rows("run")
        cmds.setParent("..")
        # the cycle
        hubstyle.mark(cmds.text(OPTION + "cycleHeading", label="Cycle", align="left",
                                annotation="A looping clip: a stop starts on a frame of it, a start ends on one"),
                      "heading")
        cmds.text(CYCLE_TEXT, label="", align="left", wordWrap=True, height=hubstyle.height("small", 36))
        cmds.rowLayout(numberOfColumns=2, adjustableColumn=1, columnAttach=[(1, "both", 0), (2, "both", 4)])
        _button(CYCLE_BTN, "Use selected", "secondary", "refresh",
                "The selected skeleton's looping clip as the cycle: a stop starts on a frame of it, a start ends "
                "on one - and the run pose Clip is its posture", press_use_cycle)
        _button(CLEAR_BTN, "Clear", "secondary", "x", "No cycle: a stop starts and a start ends as its clip does",
                press_clear_cycle)
        cmds.setParent("..")
        # the knobs, a group at a time
        hubstyle.mark(cmds.text(OPTION + "knobsHeading", label="Settings", align="left",
                                annotation="Walk Builder's knobs for a start or a stop - a group at a time"),
                      "heading")
        shown = _stored("group", GROUPS[0][0])
        if shown not in dict((k, t) for k, t, _ in GROUPS):
            shown = GROUPS[0][0]
        tabs = dict((key, (tab, rows)) for key, tab, rows in GROUPS)
        cmds.iconTextRadioCollection(GROUP_TABS)
        for row_keys in GROUP_ROWS:
            row = cmds.rowLayout(numberOfColumns=len(row_keys),
                                 columnAttach=[(i + 1, "both", 1) for i in range(len(row_keys))])
            hubstyle.mark(row, "segments", layout=True)
            for key in row_keys:
                tab, rows = tabs[key]
                hubstyle.mark(cmds.iconTextRadioButton(
                    _group_tab(key), style="textOnly", label=tab, height=hubstyle.height("segment", 24),
                    select=key == shown, collection=GROUP_TABS,
                    annotation="%s: %s" % (tab, ", ".join(label for _n, label, _t in rows)),
                    onCommand=group_changed(key)), "segment")
            cmds.setParent("..")
        side = side_mode()
        _segments(SIDE_TABS, [(m, l, "Both: a leg or arm knob sets both sides (marked * where they differ)" if
                               m == "both" else "That side alone") for m, l in SIDE_MODES], side, side_changed,
                  _side_tab)
        for key, tab, rows in GROUPS:
            cmds.columnLayout(_group_column(key), adjustableColumn=True, rowSpacing=hubstyle.row_spacing(2),
                              manage=key == shown)
            for name, label, tip in rows:
                if name in TOGGLES:
                    hubstyle.mark(cmds.checkBox(_slider(name), label=label, annotation=tip,
                                                value=_stored(name, model.DEFAULTS[name]) >= 0.5,
                                                changeCommand=knob_changed(name)), "chip")
                    continue
                low, high = model.RANGES[name]
                _float_slider(_slider(name), label, low, high, _stored(name, model.DEFAULTS[name]), tip,
                              knob_changed(name), precision=0 if name == "weapon_overlap" else 2)
            cmds.setParent("..")
        cmds.rowLayout(numberOfColumns=3, adjustableColumn=1,
                       columnAttach=[(1, "both", 0), (2, "both", 4), (3, "both", 4)])
        _button(APPLY_BTN, "Apply", "primary", "run",
                "The selected skeletons' starts and stops rebuilt on the poses and added to the list (nothing "
                "selected: the picked ones in the list)", press_apply)
        _button(RESTORE_BTN, "Restore", "secondary", "arrow-back-up", "Their own keys back", press_restore)
        _button(RESET_BTN, "Reset", "secondary", "refresh", "The knobs back to their defaults (the poses kept)",
                press_reset)
        cmds.setParent("..")
        hubstyle.mark(cmds.text(OPTION + "listHeading", label="Skeletons", align="left"), "heading")
        cmds.textScrollList(LIST, allowMultiSelection=True, numberOfRows=6, height=110,
                            annotation="Every skeleton Start/Stop Builder has built. Click (Ctrl / Shift for "
                                       "several) to pick the WORKING ones: a knob released keys them. Apply adds "
                                       "the scene's selection.", selectCommand=list_picked)
        cmds.popupMenu(parent=LIST, button=3)
        cmds.menuItem(label="Pick all", command=list_select_all)
        cmds.menuItem(label="Key the picked now", command=list_key_now)
        cmds.menuItem(label="Restore the picked (their own keys)", command=list_restore)
        cmds.setParent("..", menu=True)
        hubstyle.mark(cmds.text(STATUS, label="", align="left", wordWrap=True, height=54), "status")
    finally:
        _QUIET[0] = False
    cmds.setParent("..")
    _show_wells()
    show_cycle()
    show_side(side)
    show_list()
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
        text = "Select skeletons carrying a start or a stop"
    if work:
        text += " | working: %d" % len(work)
    cmds.text(SUBTITLE, edit=True, label=text)


def _card_key():
    import maya_hubcopy as hubcopy
    scope = hubcopy.current()
    return "" if scope is None else scope.tag


def start():
    """The card's SelectionChanged job (one a card: the hub's and every popup copy's), refreshed when seen."""
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
