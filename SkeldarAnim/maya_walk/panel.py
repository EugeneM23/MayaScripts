"""Walk Builder - the hub card of the parametric walk (2026-10-13).

The animator: «Давай встроим этот скрипт в наш плагин. Интерфейс рисуй компактным» - the standalone window
of docs/superpowers/plans/walkparam/ becomes a card. Compact: the walk and the pose each one dropdown with a
save icon beside it, the pose's share and its parts on two lines, Apply / Reset / In place, and the knobs in
groups of which ONE is shown at a time, on two rows of tabs ([Clean | Step | Legs | Pelvis] / [Chest | Arms |
Weight] since 2026-10-14: a raw clip is looped when it is read - maya_walk.clean - by the Clean tab's Seam and
Smooth, and its Fix posture button sets the walk's bones right once, in its file).

Since 2026-10-15 the walk and the pose are both Pose Library cards in wells (columns, one card active): an
animation card of a walk cycle in the walk well, a pose card in the pose well; the old walk files and poses
were moved into the library once. Apply is called Pick («мне кажется так понятнее что эта кнопка делает»).

Select skeletons and press Pick: each is processed on its OWN cycle - the animation it carries, read on its
first Pick and kept on it (scene.capture_source) - and joins the card's list of walkers (2026-10-16,
«обрабатывать сразу несколько циклов на разных персонажах ... для обработки массивов анимаций»): the list is
every walked skeleton in the scene (scene.walkers). A skeleton with no keys takes the walk well's card. The knobs and the pose are shared - a released knob re-keys every
walker, each on its own cycle (the tempo as a ratio of the active cycle) - and each cycle keeps its own mean
pose. Selecting a walker makes its cycle the active one. Every value is remembered (optionVars), so the card
comes back as it was and a hotkey row presses with the card closed. A press that re-keys every walker changes
the card at once and keys them on Maya's next idle, once for a burst of presses, under a progress window Esc
stops (_rekey).
The design: docs/superpowers/specs/2026-10-13-walk-builder-card-design.md,
2026-10-16-walk-builder-many-walkers-design.md.
"""
import json
import os
import sys
import traceback

from . import scene

HUB_SECTION = "walk"
SUBTITLE = "skeldarWalkSubtitle"
STATUS = "skeldarWalkStatus"
#  The pose is a Pose Library card dropped into a well (2026-10-15, maya_walk.posewell): the placeholder the well
#  is laid over, and the line that stands in for it where Qt cannot
POSE_WELL = "skeldarWalkPoseWell"
POSE_WELL_TEXT = "skeldarWalkPoseWellText"
#  ...and the walk cycles too, animation cards in a well of their own (2026-10-15)
WALK_WELL = "skeldarWalkCycleWell"
WALK_WELL_TEXT = "skeldarWalkCycleWellText"
APPLY_BTN = "skeldarWalkApply"
#  The walkers (2026-10-16, «кнопочка pick должна добавлять персонажа в список»): every skeleton Pick put a cycle
#  on, read from the scene (scene.walkers); every knob re-keys them all, each on its own cycle
WALKER_LIST = "skeldarWalkList"
RESET_BTN = "skeldarWalkReset"
SAVE_WALK_BTN = "skeldarWalkSaveWalk"
GROUP_TABS = "skeldarWalkGroups"
SIDE_TABS = "skeldarWalkSides"
FIX_BTN = "skeldarWalkFixPosture"
CLEAN_REPORT = "skeldarWalkCleanReport"
IN_PLACE_BOX = "skeldarWalkInPlace"
#  The Rig pose tab (2026-10-15): the walk's mean pose on a Manny rig, its edit taken by Update
MEAN_CREATE_BTN = "skeldarWalkMeanCreate"
MEAN_UPDATE_BTN = "skeldarWalkMeanUpdate"
MEAN_DELETE_BTN = "skeldarWalkMeanDelete"
MEAN_RESET_BTN = "skeldarWalkMeanReset"
MEAN_NOTE = "skeldarWalkMeanNote"
#  Knobs shown as a checkbox (0 / 1), not a slider: In place, beside Apply
CHECKS = {"in_place": IN_PLACE_BOX}
#  [Both | Left | Right] (2026-10-13, «режим в котором левая и правая сторона станут раздельными, по
#  умолчанию коррекция двух сторон»): which side the leg and arm knobs (model.SIDED) show and set
SIDE_MODES = (("both", "Both"), ("l", "Left"), ("r", "Right"))
SIDE_MARK = {"l": " L", "r": " R"}
OPTION = "skeldarWalk_"
NO_POSE = scene.NO_POSE
NOTHING = "Select skeletons - Pick puts the walk on them and lists them"

#  The knobs but Pose (its share stands under the pose's dropdown) and In place (a chip by Apply), one group shown
#  at a time; Clean's are the clean's (maya_walk.clean - scene.ALL_DEFAULTS), the rest the model's
GROUPS = (
    ("clean", "Clean", ("seam", "smooth")),
    ("step", "Step", ("stride", "tempo", "lift")),
    ("legs", "Legs", ("foot_placement", "ground_time", "stance", "swing_out", "leg_match", "leg_turn", "knee_foot",
                      "foot_lag", "foot_flex")),
    ("pelvis", "Pelvis", ("pelvis_height", "pelvis_forward", "bob", "sway", "surge", "pelvis_rot",
                          "pelvis_twist", "pelvis_list",
                          "root_sway")),
    ("chest", "Chest", ("spine", "chest_twist", "chest_sway", "gait_lean", "torso_drag", "torso_bounce", "head",
                        "head_drag")),
    ("arms", "Arms", ("arms", "elbow", "arm_drag", "arm_bounce", "overlap")),
    ("weight", "Weight", ("weight", "balance", "exaggeration")),
    ("rigpose", "Rig pose", ()),           # buttons, not knobs: the walk's mean pose on a Manny rig
)
#  The tabs on two rows (eight in a 360 px dock would not read)
GROUP_ROWS = (("clean", "step", "legs", "pelvis"), ("chest", "arms", "weight", "rigpose"))
PART_LABELS = (("torso", "Torso"), ("pelvis", "Pelvis"), ("knees", "Knees"), ("arms", "Arms"), ("feet", "Feet"))
LABELS = {
    "smooth": ("Smooth, fr", "Every joint through a soft periodic blur this many frames wide: quiets jitter that is "
                             "not a spike; 0 leaves the motion as it is"),
    "seam": ("Seam, fr", "A loop cut out of a longer clip - or a joint that does not loop - is closed over this "
                         "many frames each side of its seam, in value and speed"),
    "pose": ("Pose", "How far the pose picked above replaces the walk's own (its parts below): 0 is the walk, "
                     "1 the pose"),
    "stride": ("Stride", "x the step length; the travel follows (a long stride sinks the contacts)"),
    "tempo": ("Tempo, fr", "Frames a cycle of two steps; fewer is faster"),
    "lift": ("Foot lift", "x how high the swinging foot rises above its path"),
    "in_place": ("In place", "1: the walk on the spot - the root stays where the first frame has it (weaving "
                             "aside only with Root sway), the body moves about it and the planted feet slide back; "
                             "the stride and speed said are the walk's"),
    "foot_placement": ("Foot placement", "1: a planted foot never slides (it rolls heel to ball about a still "
                                         "point) and one foot is always on the ground - both are down a while "
                                         "at every step; 0 is the walk's own feet, slides and all"),
    "ground_time": ("Ground time", "x how long each foot stays on the ground at a step before it swings forward: "
                                   "past 1 it leaves later - the leg stretches out behind, rises onto its toes and "
                                   "swings through quicker; where even a straight leg on its toes falls short, the "
                                   "pelvis sinks at the push-off. Under 1 it lifts sooner"),
    "stance": ("Stance","x how far apart the feet stand on the ground (the pose's spread included); 0 puts "
                         "them on one line, 1 is the walk with the pose"),
    "swing_out": ("Swing out, cm", "The swinging foot's path bowed this far out to its side between the "
                                   "steps (negative: in, toward the other leg), in the walk's size"),
    "leg_match": ("Leg match", "Fits a pose's legs to the gait: a pose standing side-on gives its hips' turn to "
                               "the spine (the hips face the walk, the shoulders keep the pose), and its knees' "
                               "and toes' splay and its width are read against its own hips and kept as much as "
                               "the gait allows - most at a walk, little at a sprint, where a leg swings in the "
                               "line of travel. 0 takes the pose's legs as they stand"),
    "leg_turn": ("Leg turn", "x how far the pose turns the knees and the toes out (or in); 0 walks on the "
                             "walk's own knees and feet"),
    "knee_foot": ("Knee <-> foot", "A knee turned against its foot past 15 deg (a shin twists that far) "
                                   "meets it: 0 turns the knee to the foot, 1 the foot to the knee"),
    "foot_lag": ("Foot lag, fr", "Frames the swinging foot trails its shin: it flicks through after it "
                                 "leaves the ground and catches up before it lands (the toes 1.5x)"),
    "foot_flex": ("Foot flex", "x how far the swinging foot turns in its ankle (and the toes in theirs)"),
    "pelvis_height": ("Pelvis height", "cm: raises (+) or lowers (-) the pelvis over the feet, the legs "
                                       "following - a walk or a pose that crouches stands up; the legs never "
                                       "straighten past the walk's straightest, so the feet stay down"),
    "pelvis_forward": ("Pelvis forward", "cm: the hips this far ahead of (+) or behind (-) the feet, the body over "
                                         "them going with them, the legs following; Balance keeps it"),
    "bob": ("Bob", "x the pelvis's up and down"),
    "sway": ("Sway", "x the pelvis's side to side"),
    "surge": ("Surge", "x the pelvis's forward and back as it walks - Bob's partner along the walk (Pelvis "
                       "forward moves it all ahead or behind)"),
    "pelvis_rot": ("Pelvis motion", "x all the pelvis's turns and tilts (Twist and Hip drop included)"),
    "pelvis_twist": ("Twist, deg", "The pelvis turns this far each way with the legs, the forward leg's hip "
                                   "forward - at a normal step (0.8 of the leg); it grows with the step. "
                                   "People: about 5; the lower back takes it back"),
    "pelvis_list": ("Hip drop, deg", "The standing leg's hip this far up, the swinging leg's down, highest "
                                     "just after the foot lands. People: about 4"),
    "root_sway": ("Root sway", "0: the root runs straight down the walk's line (what a game's capsule "
                               "wants); 1 weaves with the hips as the walk does"),
    "spine": ("Spine", "x the spine's and the neck's motion (Chest twist and sway included)"),
    "chest_twist": ("Chest twist", "deg: the shoulders turn this far each way against the hips' turn, at a "
                                   "normal step; it grows with the step (before Torso drag's overlap). "
                                   "People: about 7"),
    "chest_sway": ("Chest sway", "deg: the shoulder line tilts this far each way over the steps. People: "
                                 "about 5"),
    "gait_lean": ("Gait lean", "Under a pose's torso, the walk's own forward lean (a run leans into it) is "
                               "kept on top of the pose - as much of it as the room the pose leaves to "
                               "horizontal: a bent pose leans further less. 0 is the pose's torso as it stands"),
    "torso_drag": ("Torso drag, fr", "The trunk follows the pelvis with weight: the chest turns through a "
                                     "spring that feels the hips' motion - about this many frames late, the "
                                     "step's jolts smoothed into an overlap. 0: the trunk as the walk turns it"),
    "torso_bounce": ("Torso bounce", "How far the trunk (and the head) overshoot as they catch up: 0 settles, "
                                     "1 whips through"),
    "head": ("Head", "x the head's own motion in the world (0 holds its gaze steady)"),
    "head_drag": ("Head drag, fr", "The head keeps its gaze through a spring on the neck that feels the "
                                   "body's motion - about this many frames late, the neck taking the "
                                   "difference. 0: the head exactly where the walk looks"),
    "arms": ("Arms", "x the arms' own swing - about a pose's arms too (they are the mean it swings about); "
                     "hands holding one thing together hold it"),
    "elbow": ("Elbow", "x the forearm's own swing in the elbow, on top of Arms"),
    "arm_drag": ("Arm drag, fr", "The arms trail the body with weight: each limb follows through a spring "
                                 "that feels the shoulder's motion - about this many frames late. A held "
                                 "weapon trails the same way. 0: the arms exactly as the walk puts them"),
    "arm_bounce": ("Arm bounce", "How far the arms overshoot as they catch up: 0 settles, 1 whips through"),
    "overlap": ("Overlap, fr", "Frames the arms' own motion runs late against the body (the shoulders less); "
                               "the trunk's and the head's overlap is Torso drag and Head drag"),
    "weight": ("Weight", "Heavier: deeper, longer low poses, a slower rise, more overlap; negative: lighter"),
    "balance": ("Balance", "How far the centre of mass follows the feet like a pendulum: wider feet, a "
                           "slower step, a crouch sway it more; a leaning pose takes the hips back over the "
                           "feet. 0 leaves the pelvis to the other knobs"),
    "exaggeration": ("Exaggeration", "x every motion around the mean pose at once (not the stride)"),
}
TIPS = {
    "apply": "Pick: the walk well's active card on every selected skeleton (UE5/UE4, Mixamo, HumanIK, Unity, "
             "Biped ...), in its own proportions, from where it stands; each joins the list below. A skeleton's own "
             "animation is kept on it first (Restore the original keys puts it back). Right button: each on its "
             "own animation - for arrays of clips. Every released knob re-keys every walker, each on its own "
             "cycle; the tempo counts the active cycle's frames, the others take the same ratio of theirs.",
    "apply_own": "Every selected skeleton processed on the animation it carries (read on the first press and kept "
                 "on it) with the card's knobs and pose - one press for a whole array of clips",
    "reset": "Every knob back to its default (the tempo to the walk's own); every walker is keyed again",
    "walker_list": "The walkers: every skeleton Pick processed - «character - cycle». Click: select them (the "
                   "first one's cycle becomes the active one); right click: take a walker's settings into the card, "
                   "put the active walk card on it or its own cycle back, restore its original keys, or remove it "
                   "from the list (Delete too) - its keys stay, Pick puts it back",
    "save_walk": "Save: select a bone of a walk or a run and press - it goes to the Pose Library as an "
                 "animation card (folder Walk cycles) and into the walk well; a cycle or not: it is looped when it "
                 "is read (the loop found and its seam closed - the Clean tab)",
    "walk_well": "The walk cycle Pick puts on a skeleton: drag an animation card of a walk or a run from the Pose "
                 "Library here (or its right button: Use in Walk Builder), or Save one. Several cards stack; the "
                 "one clicked (lit) is the walk. Double click: the card in the library; right click: remove",
    "fix_posture": "Fix posture: the walk's bones set right against the UE5 idle - a bone moved off its joint goes "
                   "back; a clavicle or a foot outside a body's limits (a shoulder dropped, a foot turned out) "
                   "takes its other side's motion mirrored, or - both sides out - the idle's pose with its own "
                   "motion. Written into the walk's file (the original kept beside it as .orig); the walkers on "
                   "this cycle are keyed again",
    "in_place": "In place: the walk on the spot - the root stays where the first frame has it, the body moves "
                "about it and the planted feet slide back (what a game moves by its capsule)",
    "mean_create": "Create: a Manny rig beside the first walker on the active cycle, standing in the cycle's mean "
                   "pose (each bone's mean - an abstract pose) with every correction made so far; every cycle has "
                   "its own rig, and pressed again the active cycle's is posed again",
    "mean_update": "Update: what you changed on the rig pose goes into the walk for the whole cycle - the spine, the "
                   "arms, the head and the pelvis's turn, its height, the feet's width, the knees' and the feet's "
                   "turn - kept beside the walk's file. Every rig pose in the scene is read, each into its own "
                   "cycle, and the walkers on the cycles that changed are keyed again. Undo on the rig, then "
                   "Update, takes a change back",
    "mean_delete": "Delete: the active cycle's rig pose out of the scene; the cycle keeps its correction",
    "mean_reset": "Reset: the active cycle's correction dropped - its rig pose back in the plain mean pose, the "
                  "walkers on it keyed again",
    "pose_well": "The pose the walk takes at the Pose share: drag a pose card from the Pose Library here (or its "
                 "right button: Use in Walk Builder). The walk follows the card - its Update from selection is taken "
                 "on the next re-key; a copy kept on the walked skeleton walks on when the card is gone. Click: the "
                 "card in the library; right click: Clear",
    "parts": "What of the pose replaces the walk's own (Arms: the mean the walk's swing runs about - hands "
             "holding one thing together hold it; Feet: the width and the toes' turn)",
}
#  The selection job of each card standing: '' the hub's, a popup copy's tag its own.
JOB = {}
#  True while the card is being filled from the scene: an optionMenu's value set by code fires its
#  changeCommand (maya_vpstudio's note), and that must not re-key anything.
_QUIET = [False]


def _cmds():
    import maya.cmds as cmds
    return cmds


def _control(name):
    return OPTION + name


def _part_control(part):
    return "skeldarWalkPart_" + part


def _group_column(key):
    return "skeldarWalkGroup_" + key


def _group_tab(key):
    return "skeldarWalkGroupTab_" + key


def _side_tab(mode):
    return "skeldarWalkSide_" + mode


def _override(name, side):
    """The memory of a side's own value of a SIDED knob."""
    return "knob_%s_%s" % (name, side)


def side_mode():
    """"both" (the default: a knob sets both sides), "l" or "r"."""
    mode = _stored("side", "both")
    return mode if mode in dict(SIDE_MODES) else "both"


# ---- the memory ----

def _stored(name, default=None):
    cmds = _cmds()
    key = OPTION + name
    return cmds.optionVar(query=key) if cmds.optionVar(exists=key) else default


def _remember(name, value):
    cmds = _cmds()
    if isinstance(value, str):
        cmds.optionVar(stringValue=(OPTION + name, value))
    else:
        cmds.optionVar(floatValue=(OPTION + name, float(value)))


def _shown(name):
    """The value a knob's slider (or checkbox) shows, or None without one."""
    cmds = _cmds()
    control = _control(name)
    if name in CHECKS:
        box = CHECKS[name]
        return (1.0 if cmds.checkBox(box, query=True, value=True) else 0.0) \
            if cmds.checkBox(box, exists=True) else None
    if name == "tempo":
        return float(cmds.intSliderGrp(control, query=True, value=True)) \
            if cmds.intSliderGrp(control, exists=True) else None
    return float(cmds.floatSliderGrp(control, query=True, value=True)) \
        if cmds.floatSliderGrp(control, exists=True) else None


def values():
    """The knobs: the card's where it stands (and remembered), else what was remembered; a side's own value
    of a leg or arm knob as "<name>_l" / "<name>_r" where it has one (shown on the slider in Left / Right)."""
    mode = side_mode()
    out = {}
    for name, default in scene.ALL_DEFAULTS.items():
        shown = _shown(name)
        if shown is not None and not (name in scene.wm.SIDED and mode != "both"):
            out[name] = shown
            _remember("knob_" + name, shown)
        else:
            out[name] = float(_stored("knob_" + name, default))
    for name in scene.wm.SIDED:
        if mode != "both":                 # the slider shows this side: its value is this side's own
            shown = _shown(name)
            if shown is not None and (abs(shown - out[name]) > 1e-9 or _stored(_override(name, mode)) is not None):
                _remember(_override(name, mode), shown)
        for side in ("l", "r"):
            own = _stored(_override(name, side))
            if own is not None:
                out["%s_%s" % (name, side)] = float(own)
    return out


def _forget_sides(name=None):
    """A knob's sides linked again (every SIDED knob without `name`)."""
    cmds = _cmds()
    for each in ([name] if name else scene.wm.SIDED):
        for side in ("l", "r"):
            key = OPTION + _override(each, side)
            if cmds.optionVar(exists=key):
                cmds.optionVar(remove=key)


NO_WALK = "no walk cycle yet - drop an animation card of a walk into the walk well, or select a bone of a " \
          "walk cycle and press Save"


def chosen_walk():
    """The active cycle (what the tempo counts, what Rig pose and Fix posture act on): a walker's own cycle once
    it is selected, else the walk well's active card (scene.card_walk); a walk remembered before the cards (a
    file's name) means the card it was moved into, else the file; else the well's first card. Nothing else - an
    empty well is no walk (2026-10-16: an empty well used to fall back to the first saved walk file, and Pick put
    a walk nobody chose on a skeleton carrying its own clip)."""
    stored = _stored("walk") or ""
    if scene.is_card(stored) or scene.is_own(stored):
        if scene.walk_exists(stored):
            return stored
    elif stored:
        migrated = scene.card_walk(scene.wcards.walk_card(stored))
        if os.path.isdir(scene.wcards.absolute(scene.wcards.walk_card(stored), _library())):
            return migrated
        if stored in scene.walk_names():
            return stored
    for rel in walk_list():
        name = scene.card_walk(rel)
        if scene.walk_exists(name):
            return name
    raise scene.Refusal(NO_WALK)


def walk_list():
    """The walk cycles' cards in the walk well, top down (paths relative to the library)."""
    try:
        rels = [rel for rel in json.loads(_stored("walkCards") or "[]") if isinstance(rel, str) and rel]
    except ValueError:
        rels = []
    stored = _stored("walk") or ""
    if scene.is_card(stored) and stored[len(scene.CARD):] not in rels:
        rels.insert(0, stored[len(scene.CARD):])
    return rels


def _remember_walks(rels):
    seen = []
    for rel in rels:
        if rel and rel not in seen:
            seen.append(rel)
    _remember("walkCards", json.dumps(seen))


def _active_walk_rel():
    try:
        name = chosen_walk()
    except scene.Refusal:
        return None
    return name[len(scene.CARD):] if scene.is_card(name) else None


def walk_rows():
    """Every walk card in the well, top down: (absolute path, name, thumbnail or "", note or "", active)."""
    active = _active_walk_rel()
    rows = []
    for rel in walk_list():
        path = scene.wcards.absolute(rel, _library())
        name = scene.wcards.card_name(rel)
        if not os.path.isdir(path):
            note = "gone from the library - its walk is kept" if scene.walk_exists(scene.card_walk(rel)) \
                else "the card is gone from the library"
            rows.append((path, name, "", note, rel == active))
            continue
        thumbnail = os.path.join(path, "thumbnail.jpg")
        rows.append((path, name, thumbnail if os.path.isfile(thumbnail) else "", "", rel == active))
    return rows


def _set_walk(name):
    """`name` the walk Pick puts on a skeleton; a card's added to the walk well when new."""
    if scene.is_card(name):
        rels = walk_list()
        rel = name[len(scene.CARD):]
        if rel not in rels:
            rels.append(rel)
        _remember_walks(rels)
    _remember("walk", name or "")
    _show_walk_line()


def _show_walk_line():
    """The walk well's stand-in line (no Qt) and every well, read again."""
    cmds = _cmds()
    if cmds.text(WALK_WELL_TEXT, exists=True):
        try:
            label = "Walk: %s" % scene.walk_label(chosen_walk())
        except scene.Refusal:
            label = "Walk: none - Pose Library animation card > Use in Walk Builder"
        count = len(walk_list())
        cmds.text(WALK_WELL_TEXT, edit=True, label=label + (" (%d cards in the well)" % count if count > 1 else ""))
    try:
        from . import posewell
        posewell.refresh_all()
    except Exception:                                        # noqa: BLE001 - no Qt
        pass


def tempo_walk():
    """The cycle the card's tempo is counted in (2026-10-16): the one it was set for - by choosing a cycle, by
    moving the slider, by Reset - kept beside it, so an active cycle that changed some other way (a card gone, an
    empty well) never reads a tempo meant for another cycle (Creep_Drunk squeezed into another walk's 31 frames
    looked broken). None without one."""
    stored = _stored("tempoWalk") or ""
    if stored and scene.walk_exists(stored):
        return stored
    try:
        return chosen_walk()
    except scene.Refusal:
        return None


def _remember_tempo_walk(name=None):
    """The tempo is counted in `name` (the active cycle without it) from now on."""
    if name is None:
        try:
            name = chosen_walk()
        except scene.Refusal:
            name = ""
    _remember("tempoWalk", name or "")


def _active_frames():
    """The frames of the cycle the card's tempo is counted in, or None without one."""
    name = tempo_walk()
    if not name:
        return None
    try:
        return scene.load_walk(name, values())[0].P
    except scene.REFUSALS:
        return None


def _walk_taken(name, say=True, keep_ratio=False):
    """The walk `name` made the active one (what Pick puts on a skeleton walking a card, what the tempo counts).
    The tempo: the cycle's own frames, as it always was when a cycle is chosen - or, `keep_ratio` (a walker
    selected), the same ratio counted in the new cycle's frames. The line."""
    old = _active_frames() if keep_ratio else None
    tempo = float(values().get("tempo") or 0.0)
    walk, _, _, report = scene.load_walk(name, values())      # refused here: nothing remembered
    _set_walk(name)
    show_report(report)
    shown = walk.P if not (old and tempo >= 1) else max(4, int(round(tempo * walk.P / float(old))))
    quiet, _QUIET[0] = _QUIET[0], True
    try:
        _set_knobs({"tempo": shown}, walk.P)
    finally:
        _QUIET[0] = quiet
    _remember_tempo_walk(name)
    line = "walk %s | %s" % (scene.walk_label(name), walk.summary())
    if report.changed:
        line += " | " + report.short()
    return line + (" - Pick puts it on the selected skeletons" if say else "")


def card_walkers():
    """The walkers a chosen walk card re-keys (the card comes first): the selected walkers, whatever they walk -
    none selected, every walker that walks a card (one on its own cycle keeps it)."""
    listed = scene.walkers()
    chosen = _selected_walkers(listed)
    if chosen:
        return chosen
    return [r for r in listed if not scene.is_own(scene.memo_of(r).get("walk"))]


def _selected_walkers(listed):
    """The walkers in `listed` the selection names: a bone of one, its top, a mesh skinned to it. Anything else
    selected (a curve, a light, another character) names none."""
    cmds = _cmds()
    found = []
    for node in cmds.ls(selection=True, long=True) or []:
        hit = [r for r in listed if node == r or node.startswith(r + "|")]
        if not hit:
            try:
                root = scene.skeleton_root_of(node)
            except Exception:                                # noqa: BLE001 - a rig, nothing skinned
                root = None
            hit = [r for r in listed if r == root]
        for root in hit:
            if root not in found:
                found.append(root)
    return found


def take_walk_card(path):
    """An animation card dropped into the walk well (or clicked there, or Use in Walk Builder): the active cycle,
    at its own tempo, and - as always - put on at once: the walkers that walk a card (card_walkers) take it. A
    walker on its own cycle keeps it. Refused: a pose card, a card of objects, one that is no cycle."""
    def run():
        from maya_poselib import store
        if not store.is_anim(path):
            raise scene.wcards.Refusal("%s is a pose card - drop it into the pose well; the walk takes an "
                                       "animation card" % scene.wcards.card_name(path))
        name = scene.card_walk(scene.wcards.relative(path, _library()))
        roots = card_walkers()
        line = _walk_taken(name, say=not roots)
        if not roots:
            return line
        lines = [_apply_to(root, name) for root in roots]
        _SELECTED[0] = None
        return lines[0] if len(lines) == 1 else "%s | %d walkers take it: %s" % (
            line, len(roots), ", ".join(scene.walker_label(r) for r in roots))
    return _press(run)


def _back_to_own(walks):
    """The walkers on any of the cycles `walks` (cards taken out of the well) back on the animation they kept
    (2026-10-16: «если я удаляю карточку цикла то анимация не возвращается на ту что была выбрана на скелете»).
    One that kept nothing stays as it is, named. A tail for the line."""
    back, kept = [], []
    for root in scene.walkers():
        if scene.memo_of(root).get("walk") not in walks:
            continue
        if not scene.has_source(root):
            kept.append(scene.walker_label(root))
            continue
        _apply_to(root, scene.own_name(root))
        back.append(scene.walker_label(root))
    tail = ""
    if back:
        tail += " | back on their own animation: %s" % ", ".join(back)
    if kept:
        tail += " | no animation of their own to go back to (keep the card's keys): %s" % ", ".join(kept)
    return tail


def remove_walk_card(path):
    """A card taken out of the walk well: the walkers on it back on their own animation; the active cycle, when it
    was this card, moves on to the next card."""
    def run():
        rel = scene.wcards.relative(path, _library())
        active = _active_walk_rel() == rel
        _remember_walks([each for each in walk_list() if each != rel])
        name = scene.wcards.card_name(rel)
        line = "%s taken out of the walk well" % name
        if active:
            _remember("walk", "")
            rest = walk_list()
            if rest:
                line += " | " + _walk_taken(scene.card_walk(rest[0]), say=False)
            else:
                line += " - no walk card left"
        _show_walk_line()
        return line + _back_to_own([scene.card_walk(rel)])
    return _press(run)


def remove_all_walk_cards():
    """The walk well emptied: every walker on a card back on its own animation."""
    def run():
        gone = [scene.card_walk(rel) for rel in walk_list()]
        _remember_walks([])
        _remember("walk", "")
        _show_walk_line()
        return "the walk well emptied" + _back_to_own(gone)
    return _press(run)


def _library():
    return scene.wcards.library_root(_cmds())


def chosen_card():
    """The pose card picked (its path relative to the library), else None - a name remembered before the cards
    (an old .wpose pose) meaning the card it was moved into."""
    rel = _stored("poseCard")
    if rel:
        return rel
    old = _stored("pose")
    if old and old != NO_POSE:
        migrated = scene.wcards.legacy_card(old)
        if os.path.isdir(scene.wcards.absolute(migrated, _library())):
            return migrated
    return None


def card_list():
    """The cards dropped into the well, top down (paths relative to the library; 2026-10-15: «массив в
    столбик ... работала та поза которая активна»). The active card is always among them - a card picked
    before the list (one optionVar) heads it."""
    try:
        rels = [rel for rel in json.loads(_stored("poseCards") or "[]") if isinstance(rel, str) and rel]
    except ValueError:
        rels = []
    active = chosen_card()
    if active and active not in rels:
        rels.insert(0, active)
    return rels


def _remember_list(rels):
    seen = []
    for rel in rels:
        if rel and rel not in seen:
            seen.append(rel)
    _remember("poseCards", json.dumps(seen))


def _card_row(rel, active):
    """(the card's absolute path, its name, its thumbnail or "", a note or "", whether it is the active one)."""
    path = scene.wcards.absolute(rel, _library())
    name = scene.wcards.card_name(rel)
    if not os.path.isdir(path):
        return path, name, "", "the card is gone from the library", rel == active
    thumbnail = os.path.join(path, "thumbnail.jpg")
    return path, name, thumbnail if os.path.isfile(thumbnail) else "", "", rel == active


def well_rows():
    """Every card in the well, top down, as `_card_row`s; the active one says so."""
    active = chosen_card()
    return [_card_row(rel, active) for rel in card_list()]


def well_state():
    """(the active card's absolute path, its name, its thumbnail, a note); four "" with none active."""
    rel = chosen_card()
    if not rel:
        return "", "", "", ""
    return _card_row(rel, rel)[:4]


def _show_card_line():
    """The well's stand-in line (no Qt) and every well, read again."""
    cmds = _cmds()
    if cmds.text(POSE_WELL_TEXT, exists=True):
        rel = chosen_card()
        count = len(card_list())
        more = " (%d cards in the well)" % count if count > 1 else ""
        cmds.text(POSE_WELL_TEXT, edit=True,
                  label=("Pose: %s%s" % (scene.wcards.card_name(rel), more)) if rel else
                  "Pose: none%s - Pose Library card > Use in Walk Builder" % more)
    try:
        from . import posewell
        posewell.refresh_all()
    except Exception:                                        # noqa: BLE001 - no Qt
        pass


def _set_card(rel):
    """`rel` the active card (added to the well's list when new); "" none active, the list kept."""
    if rel:
        rels = card_list()
        if rel not in rels:
            rels.append(rel)
        _remember_list(rels)
    _remember("poseCard", rel or "")
    _remember("pose", "")                    # the old name: the card stands for it now
    _show_card_line()


def take_card(path):
    """A Pose Library card dropped into the well (or Use in Walk Builder): the walk's pose. A share of 0 is set
    to 1 (a pose dropped to do nothing reads as broken); every walker is keyed again. Answers the line."""
    def run():
        name, _bones = scene.wcards.read_card(path)          # refused: an animation or an objects card
        _set_card(scene.wcards.relative(path, _library()))
        note = ""
        if float(values().get("pose", 0.0)) <= 0.0:
            quiet, _QUIET[0] = _QUIET[0], True
            try:
                _set_knobs({"pose": 1.0}, 30)
            finally:
                _QUIET[0] = quiet
            note = " (Pose share set to 1)"
        return _rekey("pose card %s%s" % (name, note))
    return _press(run)


# ---- the re-key of every walker, on Maya's next idle ----
#
#  2026-10-16, the animator: «если прокинуть 2 карточки с позами то переключение между ними перестает работать и
#  кажется плагин тоже». Measured: with four walkers in the list one pose card click keyed them all, ~10 s with
#  Maya standing still and the card unlit until the end - and every click made meanwhile came in afterwards as one
#  more re-key of everybody. So a press that keys every walker again (a pose card, a knob, a part, In place,
#  Reset) changes the card at once and leaves the keys to Maya's next idle: the well and the line show the press
#  straight away, and every press made before the idle comes - or while a re-key works, queued by Windows - folds
#  into the one re-key that runs, with what the card holds by then. A progress window names each walker in turn
#  and Esc stops after the one it is on. Every queued job is the same "serve what is pending": the first to run
#  keys for the latest press, the others find nothing left, and one that runs while a re-key works (an idle Maya
#  let through the progress window) does nothing - that re-key stops between walkers and queues one more job for
#  the press. In batch mode (a verify, a test) no idle comes: it keys at once.

REKEY_STATE = {"wanted": 0, "served": 0, "running": False, "line": ""}


def _rekey_state():
    """The re-keys asked for: `wanted` counts the presses, `served` the last one keyed for, `running` while one
    keys, `line` the last press's. On sys (trap 111: an install's purge must not split it between two module
    objects); a field an older build's state lacks is filled in (trap 139)."""
    state = getattr(sys, "_skeldar_walk_rekey", None)
    if not isinstance(state, dict):
        state = {}
        sys._skeldar_walk_rekey = state
    for key, value in REKEY_STATE.items():
        state.setdefault(key, value)
    return state


def _batch():
    """No idle comes (mayapy; a cmds that cannot say): a re-key runs at once."""
    try:
        return bool(_cmds().about(batch=True))
    except Exception:                                        # noqa: BLE001
        return True


def _later(job):
    """`job()` on Maya's next idle, in the card (the hub's, a popup copy's) it was asked from; at once where Maya
    cannot defer."""
    import maya_hubcopy as hubcopy
    job = hubcopy.wrap(job)
    try:
        import maya.utils
        defer = maya.utils.executeDeferred
    except (ImportError, AttributeError):
        return job()
    defer(job)
    return None


def _rekey(line):
    """`line`, and every walker keyed again - on Maya's next idle, once for a burst of presses (above); none: how to
    get one. The line the card shows now: in batch the re-key's own, else that it is coming."""
    walkers = scene.walkers()
    if not walkers:
        return (line + " - " if line else "") + "select skeletons and press Pick"
    state = _rekey_state()
    state["wanted"] += 1
    state["line"] = line
    if _batch():
        text = _serve()
        return line if text is None else text
    _later(_rekey_idle)
    return "%skeying %d walker%s..." % (line + " - " if line else "", len(walkers), "" if len(walkers) == 1 else "s")


def _serve():
    """The re-key pending, now, for the latest press: None when none is pending, or while one keys (never nested).
    It stops between walkers when a press comes meanwhile. The line."""
    state = _rekey_state()
    if state["running"] or state["served"] >= state["wanted"]:
        return None
    target, line = state["wanted"], state["line"]
    state["running"] = True
    try:
        text = rekey_all(stop=lambda: _rekey_state()["wanted"] != target)
    finally:
        state["running"] = False
        state["served"] = target
    return (line + " | " if line else "") + text


def _rekey_idle():
    """The idle's re-key, the card read again and its line - and one more job when a press came while it keyed."""
    try:
        text = _serve()
    except Exception as exc:                                 # noqa: BLE001
        print(traceback.format_exc())
        text = "Walk Builder failed: %s" % exc
    if text is None:
        return
    refresh()
    status(text)
    state = _rekey_state()
    if state["served"] < state["wanted"]:
        _later(_rekey_idle)


class _Progress(object):
    """Maya's cancellable progress window over a re-key of several walkers («keying 3 of 8: Manny - dw»), Esc stops
    after the walker it is on (`at` answers False from then on). Nothing for one walker, in batch mode, or where
    it cannot open - maya_poselib.timewalk.Progress's rules, on this module's cmds."""

    def __init__(self, total):
        self.total = total
        self.on = False
        self.cancelled = False

    def __enter__(self):
        if self.total < 2 or _batch():
            return self
        try:
            _cmds().progressWindow(title="Walk Builder", progress=0, maxValue=self.total, status="...",
                                   isInterruptable=True)
            self.on = True
        except Exception:                                    # noqa: BLE001 - no UI to show it in
            self.on = False
        return self

    def at(self, done, text):
        """`done` walkers keyed, `text` the one next: False once Esc was pressed."""
        if self.on and not self.cancelled:
            try:
                cmds = _cmds()
                cmds.progressWindow(edit=True, progress=done, status=text)
                self.cancelled = bool(cmds.progressWindow(query=True, isCancelled=True))
            except Exception:                                # noqa: BLE001 - the window is gone
                self.on = False
        return not self.cancelled

    def __exit__(self, kind, error, trace):
        if self.on:
            self.on = False
            try:
                _cmds().progressWindow(endProgress=True)
            except Exception:                                # noqa: BLE001
                pass
        return False


def _gone(root):
    """Whether the walker `root` left the scene (deleted while a progress window let the animator work)."""
    try:
        return not _cmds().objExists(root)
    except Exception:                                        # noqa: BLE001 - a cmds that cannot say
        return False


def pick_card(path):
    """A card in the well clicked: the active pose (as a drop of it). A card gone from the library is refused."""
    return take_card(path)


def clear_card():
    """No card active: the walk's own posture (the well keeps its cards); every walker keyed again."""
    def run():
        _set_card("")
        return _rekey("no pose card - the walk's own posture")
    return _press(run)


def remove_card(path):
    """A card taken out of the well; the active one leaves the walk on its own posture."""
    def run():
        rel = scene.wcards.relative(path, _library())
        _remember_list([each for each in card_list() if each != rel])
        name = scene.wcards.card_name(rel)
        if rel != chosen_card():
            _show_card_line()
            return "%s taken out of the well" % name
        _set_card("")
        return _rekey("%s taken out of the well - the walk's own posture" % name)
    return _press(run)


def remove_all_cards():
    """The well emptied."""
    def run():
        active = chosen_card()
        _remember_list([])
        _set_card("")
        line = "the well emptied"
        return _rekey(line + " - the walk's own posture") if active else line
    return _press(run)


def show_card(path):
    """The Pose Library opened, the card picked."""
    from maya_poselib import window as library
    library.show_window()

    def pick():
        window = library.live()
        if window is not None:
            try:
                window.refresh()
                window.pick(path)
            except Exception:                                # noqa: BLE001
                traceback.print_exc()
    try:
        import maya.utils
        maya.utils.executeDeferred(pick)
    except ImportError:
        pick()
    return status("%s in the Pose Library" % scene.wcards.card_name(path))


def chosen_parts():
    cmds = _cmds()
    if cmds.checkBox(_part_control(PART_LABELS[0][0]), exists=True):
        return tuple(part for part, _ in PART_LABELS if cmds.checkBox(_part_control(part), query=True, value=True))
    stored = _stored("parts")
    if stored is None:
        return scene.ALL_PARTS
    try:
        return tuple(p for p in json.loads(stored) if p in scene.ALL_PARTS)
    except (TypeError, ValueError):
        return scene.ALL_PARTS


# ---- filling the card ----

def show_report(report):
    """The clean's findings into the Clean tab's text (a Report, or a line)."""
    cmds = _cmds()
    if cmds.text(CLEAN_REPORT, exists=True):
        text = report if isinstance(report, str) else report.text()
        cmds.text(CLEAN_REPORT, edit=True, label=text, height=report_height(text))


REPORT_CHARS = 44         # a caption line's characters in the 360 px dock (estimated: the skin's small font)
REPORT_LINE = 15          # logical px a caption line


def report_height(text):
    """The report's height for its text wrapped at REPORT_CHARS (a fixed height clipped a long report)."""
    lines = sum(max(1, -(-len(line) // REPORT_CHARS)) for line in text.splitlines())
    return max(2, lines) * REPORT_LINE + 6


def _set_knobs(knobs, frames):
    """The knobs into the card (and the memory); the tempo's range follows the walk's own `frames`. A side's
    own value ("lift_l") is remembered; given every knob (a walked skeleton read back), a side without one is
    linked again."""
    cmds = _cmds()
    if all(name in knobs for name in scene.wm.DEFAULTS):
        _forget_sides()
    for key, value in knobs.items():
        if key in scene.wm.SIDE_KNOBS:
            _remember("knob_" + key, value)
    for name, value in knobs.items():
        if name not in scene.ALL_DEFAULTS:
            continue
        control = _control(name)
        if name in CHECKS:
            if cmds.checkBox(CHECKS[name], exists=True):
                cmds.checkBox(CHECKS[name], edit=True, value=value >= 0.5)
            _remember("knob_" + name, 1.0 if value >= 0.5 else 0.0)
        elif name == "tempo":
            shown = int(round(value)) if value >= 1 else int(frames)
            if cmds.intSliderGrp(control, exists=True):
                cmds.intSliderGrp(control, edit=True, minValue=max(4, frames // 2), maxValue=2 * frames,
                                  fieldMaxValue=4 * frames, value=shown)
            _remember("knob_" + name, shown)
        else:
            if cmds.floatSliderGrp(control, exists=True):
                cmds.floatSliderGrp(control, edit=True, value=value)
            _remember("knob_" + name, value)
    show_side(side_mode())


def _set_parts(parts):
    cmds = _cmds()
    for part, _ in PART_LABELS:
        if cmds.checkBox(_part_control(part), exists=True):
            cmds.checkBox(_part_control(part), edit=True, value=part in parts)
    _remember("parts", json.dumps(list(parts)))


def show_side(mode):
    """The leg and arm knobs' sliders on side `mode` ("both", "l", "r"): each shows that side's own value
    (Both: the knob's, its label marked * where the sides differ), its segment lit, remembered."""
    cmds = _cmds()
    mode = mode if mode in dict(SIDE_MODES) else "both"
    _remember("side", mode)
    if cmds.iconTextRadioButton(_side_tab(mode), exists=True):
        cmds.iconTextRadioButton(_side_tab(mode), edit=True, select=True)
    quiet, _QUIET[0] = _QUIET[0], True
    try:
        for name in scene.wm.SIDED:
            control = _control(name)
            if not cmds.floatSliderGrp(control, exists=True):
                continue
            base = float(_stored("knob_" + name, scene.wm.DEFAULTS[name]))
            own = dict((side, _stored(_override(name, side))) for side in ("l", "r"))
            if mode == "both":
                split = any(v is not None and abs(float(v) - base) > 1e-9 for v in own.values())
                value, mark = base, " *" if split else ""
            else:
                value = float(own[mode]) if own[mode] is not None else base
                mark = SIDE_MARK[mode]
            cmds.floatSliderGrp(control, edit=True, value=value, label=LABELS[name][0] + mark)
    finally:
        _QUIET[0] = quiet


def side_changed(mode):
    def go(*_):
        show_side(mode)
    return go


def knob_changed(name):
    """A released slider: in Left / Right a leg or arm knob sets that side alone; in Both it sets the knob
    and links its sides again. Then every walker is keyed again."""
    def changed(*_):
        if _QUIET[0]:
            return None
        mode = side_mode()
        shown = _shown(name)
        if shown is not None:
            if name in scene.wm.SIDED and mode != "both":
                _remember(_override(name, mode), shown)
            else:
                _remember("knob_" + name, shown)
                if name in scene.wm.SIDED:
                    _forget_sides(name)
                    show_side(mode)
            if name == "tempo":                  # the frames shown are the active cycle's
                _remember_tempo_walk()
        return slider_changed()
    return changed


def show_group(key):
    """Show the knob group `key` alone: its column managed, its tab lit, remembered."""
    cmds = _cmds()
    if key not in dict((k, l) for k, l, _ in GROUPS):
        key = GROUPS[0][0]
    _remember("group", key)
    for each, _, _ in GROUPS:
        if cmds.columnLayout(_group_column(each), exists=True):
            cmds.columnLayout(_group_column(each), edit=True, manage=each == key)
    if cmds.iconTextRadioButton(_group_tab(key), exists=True):
        cmds.iconTextRadioButton(_group_tab(key), edit=True, select=True)


def take_settings(root):
    """A walker's stored knobs, pose card and parts into the card (right button > Take its settings): they reach
    every walker on the next re-key. Its cycle becomes the active one."""
    def run():
        name, knobs, pose, parts = scene.pick(root)
        memo = scene.memo_of(root)
        card = memo.get("pose_card") or (scene.wcards.legacy_card(pose) if pose else "")
        quiet, _QUIET[0] = _QUIET[0], True
        try:
            _set_walk(name)
            _set_card(card)
            _set_parts(parts)
            frames = int(knobs.get("tempo") or 30)
            if scene.walk_exists(name):
                walk, _, _, report = scene.load_walk(name, knobs)
                frames = walk.P
                show_report(report)
            _set_knobs(knobs, frames)
        finally:
            _QUIET[0] = quiet
        _remember_tempo_walk(name)
        return "%s's settings are the card's - move a knob (or press Pick) to put them on every walker" \
            % scene.walker_label(root)
    return _press(run)


_SELECTED = [None]       # the walker the selection named last: only a NEW one activates its cycle (a press that
                         # refreshes the card with that walker still selected must not undo a walk card clicked)


def _activate(root):
    """A listed walker that walks a card newly selected: that card the walk well's active one, the tempo's ratio
    kept (nobody re-keyed). A walker on its own cycle leaves the well alone."""
    if root == _SELECTED[0]:
        return
    _SELECTED[0] = root
    name = scene.memo_of(root).get("walk")
    if not name or scene.is_own(name) or not scene.walk_exists(name):
        return
    try:
        if chosen_walk() == name:
            return
    except scene.Refusal:
        pass
    quiet, _QUIET[0] = _QUIET[0], True
    try:
        _walk_taken(name, say=False, keep_ratio=True)
    finally:
        _QUIET[0] = quiet


# ---- the lines ----

def _short(path):
    return path.rsplit("|", 1)[-1] if path else "-"


def selection_line(root):
    """The card's subtitle: the selected skeleton (a walker, walked but out of the list, or not walked), else
    how many walkers the list holds."""
    try:
        walk = chosen_walk()
    except scene.Refusal:
        walk = None
    if root:
        memo = scene.memo_of(root)
        label = scene.walker_label(root)
        if memo.get("walk"):
            if not memo.get("listed", True):
                return "%s walks %s - out of the list (Pick puts it back)" % (label, scene.walk_label(memo["walk"]))
            return "%s walks %s" % (label, scene.walk_label(memo["walk"]))
        return ("%s: Pick adds it with %s" % (label, scene.walk_label(walk)) if walk else
                "%s: drop a walk cycle card first" % label)
    count = len(scene.walkers())
    if not count:
        return NOTHING
    return "%d walker%s in the list - every knob re-keys %s" % (count, "" if count == 1 else "s",
                                                               "it" if count == 1 else "them all")


def status(text):
    """The card's line - and the hub's one message line. Answers the text (a hotkey row shows it when the
    card is closed)."""
    import maya_hubstyle as hubstyle
    cmds = _cmds()
    if cmds.text(STATUS, exists=True):
        cmds.text(STATUS, edit=True, label=text)
        hubstyle.tell(STATUS, text)
    return text


def refresh(*_):
    """The subtitle and the list from the selection; a listed walker selected makes its cycle the active one."""
    cmds = _cmds()
    if not cmds.text(SUBTITLE, exists=True):
        return
    try:
        root = scene.selected_top()
        memo = scene.memo_of(root) if root else {}
        if memo.get("walk") and memo.get("listed", True):
            _activate(root)
        else:
            _SELECTED[0] = None
        cmds.text(SUBTITLE, edit=True, label=selection_line(root))
        show_list()
    except Exception:                                        # noqa: BLE001
        print(traceback.format_exc())


def _press(action):
    try:
        text = action()
    except scene.REFUSALS as refusal:
        text = str(refusal)
    except Exception as exc:                                 # noqa: BLE001
        print(traceback.format_exc())
        text = "Walk Builder failed: %s" % exc
    refresh()
    return status(text)


# ---- the presses ----

def _apply_to(root, walk=None):
    """The walk `walk` (the active cycle) keyed onto `root` with the card's knobs - the tempo as a ratio of the
    active cycle (walk_knobs) - the card's pose and parts. The line."""
    try:
        active = chosen_walk()
    except scene.Refusal:                     # an empty walk well: only a walk named here can be keyed
        if not walk:
            raise
        active = None
    walk = walk or active
    _remember("parts", json.dumps(list(chosen_parts())))
    result, info, text = scene.apply(root, walk, walk_knobs(walk), None, chosen_parts(), pose_card=chosen_card())
    if info.get("clean") is not None and walk == active:
        show_report(info["clean"])
    return text


def walk_knobs(walk):
    """The card's knobs for a walker on cycle `walk`: the card's tempo counts the frames of the cycle it was set
    for (tempo_walk), so another cycle takes the same ratio of its own (at least 4 frames)."""
    knobs = values()
    counted = tempo_walk()
    tempo = float(knobs.get("tempo") or 0.0)
    if not counted or walk == counted or tempo < 1:
        return knobs
    own = scene.load_walk(walk, knobs)[0].P
    base = scene.load_walk(counted, knobs)[0].P
    knobs["tempo"] = float(max(4, int(round(tempo * own / float(base)))))
    return knobs


def rekey_all(walk=None, stop=None):
    """Every listed walker (only those on the cycle `walk` when given) keyed again, each on its own cycle with the
    card's knobs and pose. A walker that fails is named, the others still keyed. Several walkers: a progress window
    names each in turn and Esc stops after the one it is on; `stop` (asked before each walker) True - a newer press
    waits, the rest are left to it. The line."""
    import time
    started = time.time()
    done, failed, lines, left, why = [], [], [], [], ""
    roots = []
    for root in scene.walkers():
        name = scene.memo_of(root).get("walk")
        if walk is None or name == walk:
            roots.append((root, name, "%s - %s" % (scene.walker_label(root), scene.walk_label(name))))
    with _Progress(len(roots)) as progress:
        for index, (root, name, label) in enumerate(roots):
            if not progress.at(index, "keying %d of %d: %s" % (index + 1, len(roots), label)):
                why, left = "stopped by Esc - not keyed", [each[2] for each in roots[index:]]
                break
            if stop is not None and stop():                  # after the window: a click it let through counts
                why, left = "a newer press keys the rest", [each[2] for each in roots[index:]]
                break
            if _gone(root):
                continue
            if scene.keys_changed(root):                     # new animation on it: a knob must not wipe it
                failed.append("%s: new keys on it since the walk - Pick it to take them" % label)
                continue
            try:
                lines.append(_apply_to(root, name))
                done.append(label)
            except scene.REFUSALS as refusal:
                failed.append("%s: %s" % (label, refusal))
            except Exception as exc:                         # noqa: BLE001
                print(traceback.format_exc())
                failed.append("%s: %s" % (label, exc))
    if not done and not failed and not left:
        return ("no walker on %s - Pick puts it on skeletons" % scene.walk_label(walk) if walk else
                "no walker in the list - select skeletons and press Pick")
    if len(done) == 1 and not failed and not left:
        return lines[0]
    text = "%d walker%s keyed%s" % (len(done), "" if len(done) == 1 else "s", (": " + ", ".join(done)) if done else "")
    if failed:
        text += " | not keyed: " + "; ".join(failed)
    if left:
        text += " | %s: %s" % (why, ", ".join(left))
    return text + " | %.1f s" % (time.time() - started)


def _own_for(root):
    """`root`'s own cycle: the one it keeps, else its keys read as its cycle and kept on it; None without keys."""
    if scene.has_source(root):
        return scene.own_name(root)
    if scene.has_keys(root):
        return scene.capture_source(root)
    return None


def _keep_original(root):
    """Before a card is keyed over a skeleton's own animation, it is kept (best effort) - so Use its own cycle and
    Restore the original keys can bring it back. A clip that is no cycle is simply not kept."""
    if scene.has_source(root) or not scene.has_keys(root):
        return
    try:
        scene.capture_source(root)
    except scene.REFUSALS:
        pass


def _active_card():
    """The walk well's active card (or a walk file chosen before the cards), None when the well holds none - a
    walker's own cycle made active is not a card."""
    try:
        walk = chosen_walk()
    except scene.Refusal:
        return None
    return None if scene.is_own(walk) else walk


def walk_for(root, own=False):
    """The cycle Pick processes on `root`. The walk well's card comes first (2026-10-16, «Карточка важнее»): Pick
    puts the active card on every selected skeleton, its own animation kept first. `own` (Pick > each on its own
    animation, for arrays of clips), or no card in the well: each skeleton on its own animation - the one it
    keeps, else its keys read as its cycle. A walked skeleton whose keys are not the walk's any more (a clip
    loaded onto it) carries new animation: the old kept cycle goes and the new keys are read."""
    memo = scene.memo_of(root)
    walked = bool(memo.get("walk"))
    if walked and scene.keys_changed(root):
        scene.drop_source(root)
        walked = False
    card = _active_card()
    if own or card is None:
        walk = memo.get("walk")
        if walked and scene.is_own(walk) and scene.walk_exists(walk):
            return walk
        if walked and not scene.has_source(root):            # it walks a card and kept nothing of its own
            if card:
                return card
            raise scene.Refusal("%s walks %s and keeps no animation of its own - load a clip on it, or drop a walk "
                                "cycle card into the walk well" % (scene.walker_label(root), scene.walk_label(walk)))
        found = _own_for(root)
        if found:
            return found
        if card:
            return card
        raise scene.Refusal("%s carries no animation and the walk well holds no card - load a clip on it, or drop "
                            "a walk cycle card into the walk well" % scene.walker_label(root))
    if not walked:
        _keep_original(root)
    return card


def press_apply(*_, **kw):
    """Pick: the active walk card on every selected skeleton (each joins the list); `own=True` (Pick's right
    button) - each selected skeleton on its own animation, with the card's knobs and pose. With no active cycle
    yet the first own cycle becomes it (the tempo counts its frames)."""
    own = kw.get("own", False)

    def run():
        roots = scene.selected_roots()
        walks = [walk_for(root, own) for root in roots]      # every source kept before anything is keyed
        try:
            chosen_walk()
        except scene.Refusal:
            _walk_taken(walks[0], say=False)
        lines = [_apply_to(root, walk) for root, walk in zip(roots, walks)]
        if len(lines) == 1:
            return lines[0]
        if len(set(walks)) == 1:
            return "%d skeletons pick %s: %s" % (len(roots), scene.walk_label(walks[0]),
                                                 ", ".join(scene.walker_label(r) for r in roots))
        return "%d skeletons processed, each on its cycle: %s" % (
            len(roots), ", ".join("%s (%s)" % (scene.walker_label(r), scene.walk_label(w))
                                  for r, w in zip(roots, walks)))
    return _press(run)


def press_apply_own(*_):
    """Pick > each on its own animation: every selected skeleton processed on the animation it carries."""
    return press_apply(own=True)


def _each_picked(action, verb):
    def run():
        roots = _picked_walkers()
        if not roots:
            return "pick walkers in the list first"
        return " | ".join(action(root) for root in roots)
    return _press(run)


def use_card_picked(*_):
    """Right button > Use the active walk card: the picked walkers walk the walk well's card (their own cycle
    stays kept - Use its own cycle takes it back)."""
    return _each_picked(lambda root: _apply_to(root, chosen_walk()), "card")


def use_own_picked(*_):
    """Right button > Use its own cycle: the picked walkers on the cycle they kept (else their keys read as one)."""
    def own(root):
        walk = _own_for(root)
        if walk is None:
            raise scene.Refusal("%s keeps no animation of its own" % scene.walker_label(root))
        return _apply_to(root, walk)
    return _each_picked(own, "own")


def restore_picked(*_):
    """Right button > Restore the original keys: each picked walker's own cycle keyed back, out of the list."""
    return _each_picked(scene.restore_source, "restore")


def slider_changed(*_):
    """A released knob (a pose, a part): every walker keyed again; none - say how to get one."""
    if _QUIET[0]:
        return None

    def run():
        if not scene.walkers():                          # nobody: the Clean tab still reads the walk again
            walk, _, _, report = scene.load_walk(chosen_walk(), values())
            show_report(report)
            return "no walker in the list - select skeletons and press Pick"
        return _rekey("")
    return _press(run)


def walk_changed(*_):
    """The walk read again (a hotkey row's, the old dropdown's): its own tempo in the card."""
    if _QUIET[0]:
        return None
    return _press(lambda: _walk_taken(chosen_walk()))


def in_place_changed(*_):
    """The In place chip: remembered, every walker keyed again."""
    if _QUIET[0]:
        return None
    shown = _shown("in_place")
    if shown is not None:
        _remember("knob_in_place", shown)
    return slider_changed()


def press_reset(*_):
    def run():
        knobs = dict(scene.ALL_DEFAULTS)
        walk = scene.load_walk(chosen_walk(), knobs)[0]
        knobs["tempo"] = walk.P
        _set_knobs(knobs, walk.P)          # every knob given: the sides linked again
        _remember_tempo_walk()
        return _rekey("the knobs are back at their defaults")
    return _press(run)


def _ask(title, default):
    cmds = _cmds()
    answer = cmds.promptDialog(title=title, message="Name:", text=default, button=["Save", "Cancel"],
                               defaultButton="Save", cancelButton="Cancel", dismissString="Cancel")
    return (cmds.promptDialog(query=True, text=True) or default) if answer == "Save" else None


def press_save_walk(*_):
    def run():
        root = scene.selected_root()
        name = _ask("Save walk", scene.read_clip(root)[0].name)
        if name is None:
            return "nothing saved"
        name, line = scene.save_walk_card(root, name)
        _set_walk(name)
        walk, _, _, report = scene.load_walk(name, values())
        show_report(report)
        quiet, _QUIET[0] = _QUIET[0], True
        try:
            _set_knobs({"tempo": walk.P}, walk.P)
        finally:
            _QUIET[0] = quiet
        return line
    return _press(run)


def press_fix_posture(*_):
    """Fix posture: the picked walk's posture set right in its file (scene.fix_posture), the report shown, the
    walkers on it keyed again."""
    def run():
        name = chosen_walk()
        report, line = scene.fix_posture(name, values())
        show_report(report)
        if not any(scene.memo_of(r).get("walk") == name for r in scene.walkers()):
            return line
        return line + " | " + rekey_all(name)
    return _press(run)


def press_mean_create(*_):
    """Rig pose > Create: the walk's mean pose on a Manny rig (maya_walk.meanrig)."""
    from . import meanrig

    def run():
        name = chosen_walk()
        _remember("walk", name)
        return meanrig.press(name, values())
    return _press(run)


def press_mean_update(*_):
    """Rig pose > Update: every rig pose's change into its cycle, the walkers on those cycles keyed again."""
    from . import meanrig
    return _press(lambda: meanrig.update(rekey=rekey_walkers))


def press_mean_delete(*_):
    """Rig pose > Delete: the active cycle's rig out of the scene."""
    from . import meanrig
    return _press(lambda: meanrig.delete(chosen_walk()))


def press_mean_reset(*_):
    """Rig pose > Reset: the active cycle's correction dropped, its rig and its walkers with it."""
    from . import meanrig
    return _press(lambda: meanrig.reset(chosen_walk(), values(), rekey=rekey_walkers))


def rekey_walkers(walk):
    """The Rig pose's re-key: the walkers on the cycle `walk`, unrecorded (Ctrl+Z is the rig's). « -> ...»."""
    roots = [r for r in scene.walkers() if scene.memo_of(r).get("walk") == walk]
    if not roots:
        return " (no walker on it - Pick puts it on skeletons)"
    keyed = []
    for root in roots:
        scene.apply(root, walk, walk_knobs(walk), None, chosen_parts(), record=False, pose_card=chosen_card())
        keyed.append(scene.walker_label(root))
    return " -> %s keyed again" % ", ".join(keyed)


def show_folder(*_):
    folder = scene.folder()
    if not os.path.isdir(folder):
        os.makedirs(folder)
    os.startfile(folder)
    return status("the walks folder: %s" % folder)


def refresh_lists(*_):
    _show_walk_line()
    _show_card_line()
    return status("%d walk cards in the well, %d walk files in %s" % (len(walk_list()), len(scene.walk_names()),
                                                                        scene.folder()))


def group_changed(key):
    def go(*_):
        show_group(key)
    return go


# ---- the card ----

def _walk_row():
    """The word Walk and Save..., then the walk well: a placeholder the Qt well is laid over (posewell, kind
    "walk"); without Qt a line naming the walk. The old .walk.gz walks are moved into the library first (once a
    session; maya_walk.cards.migrate_walks)."""
    import maya_hubstyle as hubstyle
    cmds = _cmds()
    state = scene._state()
    if not state.get("walks_migrated"):
        state["walks_migrated"] = True
        try:
            made = scene.wcards.migrate_walks(scene.folder(), _library())
            if made:
                print("Walk Builder: %d walk(s) moved into the Pose Library, folder %s: %s"
                      % (len(made), scene.wcards.WALK_FOLDER, ", ".join(made)))
        except Exception:                                    # noqa: BLE001
            print(traceback.format_exc())
    cmds.rowLayout(numberOfColumns=2, adjustableColumn=1, columnAttach=[(1, "left", 0), (2, "left", 3)])
    cmds.text(label="Walk cycle", align="left", annotation=TIPS["walk_well"])
    cmds.popupMenu(button=3)
    cmds.menuItem(label="Show the walks folder", command=show_folder)
    cmds.menuItem(label="Read the lists again", command=refresh_lists)
    cmds.setParent("..", menu=True)
    hubstyle.mark(cmds.button(SAVE_WALK_BTN, label=hubstyle.tool_label("Save..."), width=hubstyle.tool_width(56),
                              height=hubstyle.height("field", 24), annotation=TIPS["save_walk"],
                              command=lambda *_: press_save_walk()), "tool", "device-floppy")
    cmds.setParent("..")
    cmds.columnLayout(WALK_WELL, adjustableColumn=True, annotation=TIPS["walk_well"])
    cmds.setParent("..")
    well = None
    try:
        from . import posewell
        well = posewell.attach(WALK_WELL, kind="walk")
    except Exception:                                        # noqa: BLE001
        print(traceback.format_exc())
    if well is None:
        cmds.text(WALK_WELL_TEXT, label="", align="left", annotation=TIPS["walk_well"])
        _show_walk_line()


def _pose_well():
    """The pose well: a placeholder the Qt well is laid over (maya_walk.posewell); without Qt a line naming the
    card. The old .wpose poses are moved into the library first (once a session; maya_walk.cards.migrate)."""
    cmds = _cmds()
    state = scene._state()
    if not state.get("migrated"):
        state["migrated"] = True
        try:
            made = scene.wcards.migrate(scene.folder(), _library())
            if made:
                print("Walk Builder: %d old pose(s) moved into the Pose Library, folder %s: %s"
                      % (len(made), scene.wcards.MIGRATED_FOLDER, ", ".join(made)))
        except Exception:                                    # noqa: BLE001
            print(traceback.format_exc())
    cmds.columnLayout(POSE_WELL, adjustableColumn=True, annotation=TIPS["pose_well"])
    cmds.setParent("..")
    well = None
    try:
        from . import posewell
        well = posewell.attach(POSE_WELL)
    except Exception:                                        # noqa: BLE001
        print(traceback.format_exc())
    if well is None:
        cmds.text(POSE_WELL_TEXT, label="", align="left", annotation=TIPS["pose_well"])
        _show_card_line()


def _slider(name):
    import maya_hubstyle as hubstyle
    cmds = _cmds()
    label, tip = LABELS[name]
    default = scene.ALL_DEFAULTS[name]
    common = dict(label=label, field=True, columnWidth3=hubstyle.pick((92, 44, 100), (100, 50, 150)),
                  adjustableColumn=3, height=hubstyle.height("small", 22), annotation=tip,
                  changeCommand=knob_changed(name))
    if name == "tempo":
        stored = int(round(float(_stored("knob_tempo", 0.0) or 0.0)))
        cmds.intSliderGrp(_control(name), minValue=4, maxValue=120, fieldMinValue=4, fieldMaxValue=400,
                          value=stored if stored >= 4 else 30, **common)
        return
    low, high = scene.ALL_RANGES[name]
    cmds.floatSliderGrp(_control(name), minValue=low, maxValue=high, fieldMinValue=low, fieldMaxValue=high,
                        step=0.05, precision=2, value=float(_stored("knob_" + name, default)), **common)


LIST_ROW = 18            # logical px a row of the walkers' list
LIST_ROWS = (2, 6)       # rows shown at least / at most (it scrolls past)


def _list_rows():
    """[(walker root, its row text)] - the card's list as the scene has it now."""
    return [(root, "%s - %s" % (scene.walker_label(root), scene.walk_label(scene.memo_of(root).get("walk"))))
            for root in scene.walkers()]


def show_list():
    """The walkers' list read again from the scene, the selected walkers lit, its height following its rows."""
    cmds = _cmds()
    if not cmds.textScrollList(WALKER_LIST, exists=True):
        return
    rows = _list_rows()
    texts = [text for _, text in rows]
    shown = cmds.textScrollList(WALKER_LIST, query=True, allItems=True) or []
    if list(shown) != texts:
        cmds.textScrollList(WALKER_LIST, edit=True, removeAll=True)
        for text in texts:
            cmds.textScrollList(WALKER_LIST, edit=True, append=text)
    count = min(max(len(rows), LIST_ROWS[0]), LIST_ROWS[1])
    cmds.textScrollList(WALKER_LIST, edit=True, height=count * LIST_ROW + 4, deselectAll=True)
    picked = set(cmds.ls(selection=True, long=True) or [])
    lit = [i + 1 for i, (root, _) in enumerate(rows) if root in picked]
    if lit:
        cmds.textScrollList(WALKER_LIST, edit=True, selectIndexedItem=lit)


def _picked_walkers():
    """The walkers the list's lit rows stand for."""
    cmds = _cmds()
    if not cmds.textScrollList(WALKER_LIST, exists=True):
        return []
    indices = cmds.textScrollList(WALKER_LIST, query=True, selectIndexedItem=True) or []
    rows = _list_rows()
    return [rows[i - 1][0] for i in indices if 0 < i <= len(rows)]


def list_selected(*_):
    """Rows clicked: those walkers selected in the scene (the first one's cycle then becomes the active one)."""
    roots = _picked_walkers()
    if roots:
        _cmds().select(roots, replace=True)


def remove_from_list(*_):
    """The lit walkers out of the list - their keys stay, Pick puts one back."""
    def run():
        roots = _picked_walkers()
        if not roots:
            return "pick walkers in the list first"
        for root in roots:
            scene.set_listed(root, False)
        show_list()
        return "out of the list (keys kept): %s" % ", ".join(scene.walker_label(r) for r in roots)
    return _press(run)


def take_settings_picked(*_):
    roots = _picked_walkers()
    if not roots:
        return status("pick a walker in the list first")
    return take_settings(roots[0])


def _walker_list():
    """The walkers' list: one row a walker, «character - cycle»; Delete or the right button takes it out."""
    cmds = _cmds()
    cmds.textScrollList(WALKER_LIST, allowMultiSelection=True, height=LIST_ROWS[0] * LIST_ROW + 4,
                        annotation=TIPS["walker_list"], selectCommand=list_selected,
                        deleteKeyCommand=remove_from_list)
    cmds.popupMenu(button=3)
    cmds.menuItem(label="Take its settings into the card", command=take_settings_picked)
    cmds.menuItem(label="Use the active walk card", command=use_card_picked)
    cmds.menuItem(label="Use its own cycle", command=use_own_picked)
    cmds.menuItem(label="Restore the original keys", command=restore_picked)
    cmds.menuItem(divider=True)
    cmds.menuItem(label="Remove from the list", command=remove_from_list)
    cmds.setParent("..", menu=True)


def _rig_pose_buttons():
    """The Rig pose tab: Create / Delete, Update / Reset, a line on what it does."""
    import maya_hubstyle as hubstyle
    cmds = _cmds()
    rows = (((MEAN_CREATE_BTN, "Create", "secondary", "user", "mean_create", press_mean_create),
             (MEAN_DELETE_BTN, "Delete", "danger", "trash", "mean_delete", press_mean_delete)),
            ((MEAN_UPDATE_BTN, "Update", "primary", "refresh", "mean_update", press_mean_update),
             (MEAN_RESET_BTN, "Reset", "secondary", "arrow-back-up", "mean_reset", press_mean_reset)))
    for row in rows:
        hubstyle.mark(cmds.rowLayout(numberOfColumns=2, adjustableColumn=1,
                                     columnAttach=[(1, "both", 0), (2, "both", 4)]), "fill", layout=True)
        for name, label, role, icon, tip, action in row:
            hubstyle.mark(cmds.button(name, label=label, height=hubstyle.height("button", 28), annotation=TIPS[tip],
                                      command=(lambda act: lambda *_: act())(action)), role, icon)
        cmds.setParent("..")
    hubstyle.mark(cmds.text(MEAN_NOTE, label="Create a Manny rig in the walk's mean pose, pose its controls, then "
                            "Update: the whole cycle takes it.", align="left", wordWrap=True, height=36), "caption")


def build_panel():
    """The card into the current layout: the subtitle; the walk and the pose with their save icons; the
    pose's share and parts; Apply / Reset; the knob groups' tabs and the shown group; the status line."""
    import maya_hubstyle as hubstyle
    cmds = _cmds()
    column = cmds.columnLayout(adjustableColumn=True, rowSpacing=hubstyle.row_spacing(6),
                               columnOffset=("both", hubstyle.pick(0, 8)))
    hubstyle.mark(cmds.text(SUBTITLE, label=NOTHING, align="left"), "subtitle")
    _walk_row()
    cmds.text(label="Pose", align="left", annotation=TIPS["pose_well"])
    _pose_well()
    _slider("pose")
    stored_parts = chosen_parts()

    def chip(part, label):
        hubstyle.mark(cmds.checkBox(_part_control(part), label=label, value=part in stored_parts,
                                    annotation=TIPS["parts"], changeCommand=slider_changed), "chip")
    if hubstyle.skinning():
        hubstyle.mark(cmds.flowLayout(wrap=True, columnSpacing=3), "flow", layout=True)
    else:
        cmds.rowLayout(numberOfColumns=len(PART_LABELS))
    for part, label in PART_LABELS:
        chip(part, label)
    cmds.setParent("..")
    hubstyle.mark(cmds.rowLayout(numberOfColumns=3, adjustableColumn=1,
                                 columnAttach=[(1, "both", 0), (2, "both", 4), (3, "both", 4)]), "fill", layout=True)
    pick = hubstyle.mark(cmds.button(APPLY_BTN, label="Pick", height=hubstyle.height("button", 28),
                                     annotation=TIPS["apply"], command=lambda *_: press_apply()), "primary", "walk")
    cmds.popupMenu(parent=pick, button=3)
    cmds.menuItem(label="Pick: each on its own animation", annotation=TIPS["apply_own"],
                  command=press_apply_own)
    cmds.setParent("..", menu=True)
    hubstyle.mark(cmds.button(RESET_BTN, label="Reset", height=hubstyle.height("button", 28),
                              annotation=TIPS["reset"], command=lambda *_: press_reset()), "secondary", "refresh")
    hubstyle.mark(cmds.checkBox(IN_PLACE_BOX, label="In place", annotation=TIPS["in_place"],
                                value=float(_stored("knob_in_place", 0.0) or 0.0) >= 0.5,
                                changeCommand=in_place_changed), "chip")
    cmds.setParent("..")
    _walker_list()
    shown = _stored("group", GROUPS[0][0])
    labels = dict((key, (label, names)) for key, label, names in GROUPS)
    cmds.iconTextRadioCollection(GROUP_TABS)
    for row in GROUP_ROWS:                # the tabs on two rows, one collection
        segments = cmds.rowLayout(numberOfColumns=len(row),
                                  columnAttach=[(i + 1, "both", 1) for i in range(len(row))])
        hubstyle.mark(segments, "segments", layout=True)
        for key in row:
            label, names = labels[key]
            hubstyle.mark(cmds.iconTextRadioButton(
                _group_tab(key), style="textOnly", label=label, height=hubstyle.height("segment", 24),
                select=key == shown, collection=GROUP_TABS,
                annotation="The knobs of %s: %s" % (label.lower(), ", ".join(LABELS[n][0] for n in names)),
                onCommand=group_changed(key)), "segment")
        cmds.setParent("..")
    side = side_mode()
    sides = cmds.rowLayout(numberOfColumns=len(SIDE_MODES),
                           columnAttach=[(i + 1, "both", 1) for i in range(len(SIDE_MODES))])
    hubstyle.mark(sides, "segments", layout=True)
    cmds.iconTextRadioCollection(SIDE_TABS)
    for mode, label in SIDE_MODES:
        hubstyle.mark(cmds.iconTextRadioButton(
            _side_tab(mode), style="textOnly", label=label, height=hubstyle.height("segment", 24),
            select=mode == side, collection=SIDE_TABS,
            annotation=("The leg and arm knobs set both sides" if mode == "both" else
                        "The leg and arm knobs (marked %s) set the %s side alone; Both links a knob's sides "
                        "again when it is moved" % (SIDE_MARK[mode].strip(), "left" if mode == "l" else "right")),
            onCommand=side_changed(mode)), "segment")
    cmds.setParent("..")
    for key, label, names in GROUPS:
        cmds.columnLayout(_group_column(key), adjustableColumn=True, rowSpacing=hubstyle.row_spacing(2),
                          manage=key == shown)
        for name in names:
            _slider(name)
        if key == "rigpose":              # the walk's mean pose on a Manny rig: create, pose it, Update
            _rig_pose_buttons()
        if key == "clean":                # the posture set right once, then what the clean found
            hubstyle.mark(cmds.button(FIX_BTN, label="Fix posture", height=hubstyle.height("button", 26),
                                      annotation=TIPS["fix_posture"], command=lambda *_: press_fix_posture()),
                          "secondary", "tool")
            hubstyle.mark(cmds.text(CLEAN_REPORT, label="", align="left", wordWrap=True, height=72), "caption")
        cmds.setParent("..")
    hubstyle.mark(cmds.text(STATUS, label="", align="left", wordWrap=True, height=54), "status")
    cmds.setParent("..")
    try:
        tempo = float(_stored("knob_tempo", 0.0) or 0.0)
        walk, _, _, report = scene.load_walk(chosen_walk(), values())
        show_report(report)
        _set_knobs({"tempo": tempo if tempo >= 1 else walk.P}, walk.P)
    except Exception:                                        # noqa: BLE001 - no walk saved yet
        pass
    show_group(shown)
    show_side(side)
    start()
    refresh()
    return column


def _card_key():
    import maya_hubcopy as hubcopy
    scope = hubcopy.current()
    return "" if scope is None else scope.tag


def start():
    """This card's own refresh on every selection change (per card: a popup copy's job dies with the
    copy and leaves the hub's)."""
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
    JOB[_card_key()] = cmds.scriptJob(event=["SelectionChanged", refresh], parent=STATUS)


def is_open():
    return bool(_cmds().text(STATUS, exists=True))


def show_window():
    """The hub, on the Walk Builder section."""
    import maya_hub
    return maya_hub.show(HUB_SECTION)
