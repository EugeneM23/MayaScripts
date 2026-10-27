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
every walked skeleton in the scene (scene.walkers). A skeleton with no keys takes the walk well's card. The knobs and the pose are the card's - a released knob re-keys the
SELECTED walkers only (since 2026-10-26: a knob moved while testing one skeleton had overwritten a finished walk
on another), each on its own cycle (the tempo as a ratio of the active cycle) - and each cycle keeps its own mean
pose. Selecting a walker makes its cycle the active one and puts its own settings in the card. Every value is remembered (optionVars), so the card
comes back as it was and a hotkey row presses with the card closed. A press that re-keys the walkers changes
the card at once and keys them on Maya's next idle, once for a burst of presses, under a progress window Esc
stops (_rekey).

Since 2026-10-26 the knobs are the walk's PARAMETERS (maya_walk.gait; the animator: «главная идея walk builder в
том что это математическая модель которую можно редактировать»): each a measured feature of a cycle in its unit
(cm, deg, frames, % of a stride), shown at the active cycle's own value; Main always shown, the others in tabs. A
value set by hand is kept as a change from the cycle's own (a ratio or an offset - gait.stored_change), so every
walker takes the same change on its own cycle, and is pinned: its label marked, the physics' links leave it alone
(its right button lets it go back to the clip's, or to the links). Speed, Weight and a Character move several at
once. The Diagnosis under the status line reads the walker keyed last against the guide and offers a Fix.
The design: docs/superpowers/specs/2026-10-13-walk-builder-card-design.md,
2026-10-16-walk-builder-many-walkers-design.md, 2026-10-26-walk-builder-editable-model-design.md.
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
#  ... and the cycle's four key poses on four Manny rigs (2026-10-26), taken by the same Update
KEY_CREATE_BTN = "skeldarWalkKeyCreate"
KEY_DELETE_BTN = "skeldarWalkKeyDelete"
KEY_RESET_BTN = "skeldarWalkKeyReset"
MEAN_CAPTION = "skeldarWalkMeanCaption"
KEY_CAPTION = "skeldarWalkKeyCaption"
#  Knobs shown as a checkbox (0 / 1), not a slider: In place, beside Pick
CHECKS = {"in_place": IN_PLACE_BOX}
#  The card's own knobs - the walk's parameters are maya_walk.gait's: the pose's share, In place and the clean's
#  Seam and Smooth, remembered as before (knob_<name>) and handed to apply as `given`
CARD_KNOBS = ("pose", "in_place", "seam", "smooth")
#  [Both | Left | Right] (2026-10-13, «режим в котором левая и правая сторона станут раздельными, по
#  умолчанию коррекция двух сторон»): which side a two-sided parameter shows and sets
SIDE_MODES = (("both", "Both"), ("l", "Left"), ("r", "Right"))
SIDE_MARK = {"l": " L", "r": " R"}
PIN_MARK = " \u2022"     # a parameter set by hand (pinned): the physics' links leave it alone
OPTION = "skeldarWalk_"
NO_POSE = scene.NO_POSE
NOTHING = "Select skeletons - Pick puts the walk on them and lists them"
gait = scene.gait
#  The macros (2026-10-26): Speed (the walk ratio: the step and the cadence each as its root), Weight, a Character
#  at a Strength - and the physics' helpers as a whole
SPEED = "skeldarWalkMacro_speed"
WEIGHT = "skeldarWalkMacro_weight"
CHARACTER = "skeldarWalkCharacter"
STRENGTH = "skeldarWalkStrength"
PHYSICS_BOX = "skeldarWalkPhysics"
KNEE_POPS_BOX = "skeldarWalkKneePops"
MAIN_HEAD = "skeldarWalkMainHead"
DETAILS_HEAD = "skeldarWalkDetailsHead"
NO_WORKING = "no working walker - press Pick on a skeleton, or click one in the list"
#  The Diagnosis: a caption and rows of a finding with its Fix
DIAG_CAPTION = "skeldarWalkDiagnosis"
DIAG_ROWS = 4


def _names(group):
    return tuple(p.name for p in gait.PARAMS if p.group == group)


MAIN_PARAMS = _names(gait.MAIN)
#  The tabs: gait's groups but Main (always shown), the clean's knobs, the Rig pose's buttons
GROUPS = tuple((g, gait.GROUP_LABELS[g], _names(g)) for g in gait.GROUPS if g != gait.MAIN) + (
    ("clean", "Clean", ("seam", "smooth")),
    ("rigpose", "Rig pose", ()),           # buttons, not knobs: the walk's mean pose on a Manny rig
)
#  The tabs on two rows (nine in a 360 px dock would not read)
GROUP_ROWS = (("timing", "pelvis", "legs", "trunk", "head"), ("arms", "physics", "clean", "rigpose"))
OLD_GROUPS = {"step": "timing", "chest": "trunk", "weight": "physics"}      # a tab remembered from before
PART_LABELS = (("torso", "Torso"), ("pelvis", "Pelvis"), ("knees", "Knees"), ("arms", "Arms"), ("feet", "Feet"))
LABELS = {
    "smooth": ("Smooth, fr", "Every joint through a soft periodic blur this many frames wide: quiets jitter that is "
                             "not a spike; 0 leaves the motion as it is"),
    "seam": ("Seam, fr", "A loop cut out of a longer clip - or a joint that does not loop - is closed over this "
                         "many frames each side of its seam, in value and speed"),
    "pose": ("Pose", "How far the pose picked above replaces the walk's own (its parts below): 0 is the walk, "
                     "1 the pose"),
    "in_place": ("In place", "1: the walk on the spot - the root stays where the first frame has it, the body "
                             "moves about it and the planted feet slide back; the stride and speed said are the "
                             "walk's"),
    "speed": ("Speed, m/s", "The walk's speed: the step and the cadence each change as its square root (the "
                            "guide's walk ratio); a Step or a Tempo set by hand takes over again"),
    "weight": ("Weight", "Heavier: a deeper bob lower after the strike, bent knees, flat feet longer, the arms and "
                         "the trunk later, a slower step; negative: lighter (half as far)"),
    "strength": ("Strength", "How far the Character moves the parameters: 0 none, 1 the character's"),
}
TIPS = {}         # filled below
TIPS = {
    "apply": "Pick: the walk well's active card on every selected skeleton (UE5/UE4, Mixamo, HumanIK, Unity, "
             "Biped ...), in its own proportions, from where it stands; each joins the list below. A skeleton's own "
             "animation is kept on it first (Restore the original keys puts it back). Right button: each on its "
             "own animation - for arrays of clips. A released parameter re-keys the selected walkers only, each on "
             "its own cycle with the same change from that cycle's own; selecting one walker puts its settings "
             "in the card.",
    "apply_own": "Every selected skeleton processed on the animation it carries (read on the first press and kept "
                 "on it) with the card's knobs and pose - one press for a whole array of clips",
    "reset": "Every parameter back to the clip's own (the macros and the character off); the selected walkers are "
             "keyed again",
    "character": "A character's changes on top of the clip (the guide's styles and emotions), at the Strength "
                 "beside it; Natural changes nothing",
    "physics": "On: the physics' helpers - Foot placement, Balance, the knees' soft limit, Whip's springs and their "
               "links; off: the clip's own feet and body, every parameter mapped straight (the clip itself at its "
               "own values)",
    "knee_pops": "Fix knee pops (the gait guide, «Колено щёлкает»): a knee that straightens fully and bends at once "
                 "clicks - around each click the leg keeps the bend of its own smoothed curve, the pelvis lowered "
                 "for it while the foot stands, the ankle drawn in while it swings",
    "diagnosis": "What the walker keyed last does against the guide (Ходьба и бег: полное руководство) - Fix sets "
                 "its parameters, pinned",
    "param_menu": "Right button: back to the clip's (held there), or let it follow the links (the speed, the "
                  "step) and the macros again",
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
    "mean_update": "Update: what you changed on the rig pose and on the key poses goes into the walk - the mean pose "
                   "for the whole cycle (the spine, the arms, the head and the pelvis's turn, its height, the feet's "
                   "width, the knees' and the feet's turn), a key pose at its key, fading to the keys on either side "
                   "and mirrored onto the other foot's steps - kept beside the walk's file. Every rig in the scene is "
                   "read, each into its own cycle, and the walkers on the cycles that changed are keyed again, each "
                   "with its own settings. Undo on the rig, then Update, takes a change back",
    "mean_delete": "Delete: the active cycle's rig pose out of the scene; the cycle keeps its correction",
    "mean_reset": "Reset: the active cycle's correction dropped - its rig pose back in the plain mean pose, the "
                  "walkers on it keyed again",
    "key_create": "Create key poses: four Manny rigs beside the first walker on the active cycle, standing in its key "
                  "poses - Contact, Down, Passing and Up of the cycle's first step of the left foot, found in the "
                  "cycle (a run's Up is its flight) - with every edit made so far. Pose their controls, then "
                  "Update: each key's edit is exact at its key, fades to the keys on either side, and the right "
                  "foot's steps take it mirrored. A foot planted flat on the ground stays where it is planted (Step "
                  "and Width move it); the helpers keep the feet and the knees right",
    "key_delete": "Delete key poses: the active cycle's four key rigs out of the scene; the cycle keeps their edits",
    "key_reset": "Reset key poses: the active cycle's key pose edits dropped - its key rigs back in the cycle's own key "
                 "poses, the walkers on it keyed again",
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
    """The value a card knob's slider (or checkbox) shows, or None without one."""
    cmds = _cmds()
    control = _control(name)
    if name in CHECKS:
        box = CHECKS[name]
        return (1.0 if cmds.checkBox(box, query=True, value=True) else 0.0) \
            if cmds.checkBox(box, exists=True) else None
    return float(cmds.floatSliderGrp(control, query=True, value=True)) \
        if cmds.floatSliderGrp(control, exists=True) else None


def values():
    """The card's own knobs (CARD_KNOBS: the pose's share, In place, Seam, Smooth): the card's where it stands (and
    remembered), else what was remembered - what apply takes as `given`. The walk's parameters: card_params."""
    out = {}
    for name in CARD_KNOBS:
        shown = _shown(name)
        if shown is not None:
            out[name] = shown
            _remember("knob_" + name, shown)
        else:
            out[name] = float(_stored("knob_" + name, scene.ALL_DEFAULTS[name]))
    return out


def _json(name, default):
    """A remembered JSON value, `default` when there is none or it is not of the default's type."""
    try:
        value = json.loads(_stored(name) or "null")
    except (TypeError, ValueError):
        value = None
    return value if isinstance(value, type(default)) else default


def _hand():
    """(changes {key: (kind, x)}, pins {key}): the parameters the card set by hand."""
    stored = _json("params", {})
    p = scene.normal_params({"changes": stored.get("changes") or {}, "pins": stored.get("pins") or []})
    return dict(p["changes"]), set(p["pins"])


def _remember_hand(changes, pins):
    _remember("params", json.dumps({"changes": dict((k, [kind, x]) for k, (kind, x) in changes.items()),
                                    "pins": sorted(pins)}))


def _macros():
    return dict((k, float(v)) for k, v in _json("macros", {}).items() if k in ("speed", "weight"))


def card_params():
    """The card's parameters as scene.apply takes them (scene.normal_params): the changes and pins, the macros,
    the character and its strength, the physics, the pose's share, In place, Seam and Smooth."""
    changes, pins = _hand()
    knobs = values()
    return scene.normal_params({"changes": changes, "pins": sorted(pins), "macros": _macros(),
                                "character": _stored("character", "") or "",
                                "strength": float(_stored("strength", 1.0)),
                                "physics": float(_stored("physics", 1.0)) >= 0.5, "pose": knobs["pose"],
                                "knee_pops": float(_stored("knee_pops", 1.0)) >= 0.5,
                                "in_place": knobs["in_place"],
                                "clean": dict((k, knobs[k]) for k in ("seam", "smooth"))})


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


def _walk_taken(name, say=True, keep_ratio=False):
    """The walk `name` made the active one (what Pick puts on a skeleton walking a card): the card's parameters
    shown at its own values (the changes stay: every cycle takes them from its own). The line."""
    walk, _, _, report = scene.load_walk(name, values())      # refused here: nothing remembered
    _set_walk(name)
    show_report(report)
    show_values()
    line = "walk %s | %s" % (scene.walk_label(name), walk.summary())
    if report.changed:
        line += " | " + report.short()
    return line + (" - Pick puts it on the selected skeletons" if say else "")


def card_walkers():
    """The walkers a chosen walk card re-keys: the working ones (Pick chose them, or rows clicked in the list),
    whatever is selected (2026-10-27, «все наши изменения попадут на нее в независимости от выделения»)."""
    return scene.working()


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
        _SELECTED[0] = scene.selected_top()          # keyed with the card: nothing to take back from it
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
    to 1 (a pose dropped to do nothing reads as broken); the selected walkers keyed again. Answers the line."""
    def run():
        name, _bones = scene.wcards.read_card(path)          # refused: an animation or an objects card
        _set_card(scene.wcards.relative(path, _library()))
        note = ""
        if float(values().get("pose", 0.0)) <= 0.0:
            quiet, _QUIET[0] = _QUIET[0], True
            try:
                _set_knobs({"pose": 1.0})
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

REKEY_STATE = {"wanted": 0, "served": 0, "running": False, "line": "", "roots": None}


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
    """`line`, and the SELECTED walkers keyed again - on Maya's next idle, once for a burst of presses (above). Only
    the selected: a knob moved while testing one skeleton re-keyed every walker in the scene and overwrote a walk
    the animator had finished (2026-10-26). None selected: nothing keyed, said. The line the card shows now: in
    batch the re-key's own, else that it is coming."""
    listed = scene.walkers()
    if not listed:
        return (line + " - " if line else "") + "select skeletons and press Pick"
    walkers = scene.working()
    if not walkers:
        return (line + " - " if line else "") + NO_WORKING
    state = _rekey_state()
    state["wanted"] += 1
    state["line"] = line
    state["roots"] = list(walkers)
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
        text = rekey_all(stop=lambda: _rekey_state()["wanted"] != target, roots=state.get("roots"))
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
    """No card active: the walk's own posture (the well keeps its cards); the selected walkers keyed again."""
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


def _set_knobs(knobs, frames=None):
    """The card's own knobs (CARD_KNOBS) into the card and the memory; others are ignored."""
    cmds = _cmds()
    for name, value in knobs.items():
        if name not in CARD_KNOBS:
            continue
        if name in CHECKS:
            if cmds.checkBox(CHECKS[name], exists=True):
                cmds.checkBox(CHECKS[name], edit=True, value=value >= 0.5)
            _remember("knob_" + name, 1.0 if value >= 0.5 else 0.0)
            continue
        if cmds.floatSliderGrp(_control(name), exists=True):
            cmds.floatSliderGrp(_control(name), edit=True, value=value)
        _remember("knob_" + name, value)


# ---- the parameters in the card ----

def _active():
    """(the active cycle's name, its Walk, its own parameters, their ranges) - None without one."""
    try:
        name = chosen_walk()
        walk = scene.load_walk(name, values())[0]
    except scene.REFUSALS:
        return None
    own = gait.own(walk)
    return name, walk, own, gait.ranges(own, float(getattr(walk, "leg_length", 0.0) or 0.0), walk)


def _key(name, mode=None):
    """The key a parameter's slider shows and sets in side `mode`: a side's own in Left / Right."""
    p = gait.P[name]
    mode = side_mode() if mode is None else mode
    return name if (mode == "both" or not p.sided) else name + "_" + mode


def _keys(name):
    p = gait.P[name]
    return [name] + ([name + "_" + s for s in gait.SIDES] if p.sided else [])


def _label(p, mode, changes, pins):
    """The slider's label: its name and unit, marked L / R on a side, * where its sides differ, pinned when set by
    hand."""
    unit = ", " + p.unit if p.unit not in ("", "x") else ""
    mark = ""
    if p.sided and mode != "both":
        mark = SIDE_MARK[mode]
        held = any(k in changes or k in pins for k in (p.name, p.name + "_" + mode))
    else:
        if p.sided and any(k in changes for k in _keys(p.name)[1:]):
            mark = " *"
        held = any(k in changes or k in pins for k in _keys(p.name))
    return p.label + unit + mark + (PIN_MARK if held else "")


def _speed_of(own, vals):
    """The speed (m/s) the parameters' step and tempo give on the cycle whose own are `own`."""
    speed = float(own.get("speed", 0.0) or 0.0)
    step, tempo = gait.own_value(own, "step"), gait.own_value(own, "tempo")
    if not step or not tempo or not vals.get("tempo"):
        return speed
    return speed * (vals["step"] / step) / (vals["tempo"] / tempo)


def show_values():
    """Every parameter's slider (and checkbox) at its value on the active cycle - the card's changes, macros and
    character on the cycle's own - in the cycle's range, its label marked; the macros' row. Quiet: nothing keyed."""
    cmds = _cmds()
    active = _active()
    if active is None:
        return
    _, walk, own, rng = active
    params = card_params()
    vals = scene.param_values(walk, params)[1]
    changes, pins = set(params["changes"]), set(params["pins"])
    mode = side_mode()
    quiet, _QUIET[0] = _QUIET[0], True
    try:
        for p in gait.PARAMS:
            control = _control(p.name)
            key = _key(p.name, mode)
            value = float(vals.get(key, gait.own_value(own, key)))
            label = _label(p, mode, changes, pins)
            if p.kind == "toggle":
                if cmds.checkBox(control, exists=True):
                    cmds.checkBox(control, edit=True, value=value >= 0.5, label=label)
                continue
            if not cmds.floatSliderGrp(control, exists=True):
                continue
            lo, hi = rng.get(key, rng.get(p.name, (value - 1.0, value + 1.0)))
            lo, hi = min(lo, value), max(hi, value)
            if hi - lo < 1e-6:
                hi = lo + 1.0
            cmds.floatSliderGrp(control, edit=True, minValue=lo, maxValue=hi, fieldMinValue=min(lo, 0.0) - 2.0 * (hi - lo),
                                fieldMaxValue=hi + 2.0 * (hi - lo), value=value, label=label)
        own_speed = float(own.get("speed", 0.0) or 0.0)
        if cmds.floatSliderGrp(SPEED, exists=True) and own_speed > 0.0:
            value = _speed_of(own, vals)
            cmds.floatSliderGrp(SPEED, edit=True, minValue=min(0.4 * own_speed, value),
                                maxValue=max(2.0 * own_speed, value), value=value,
                                label=LABELS["speed"][0] + (PIN_MARK if "speed" in params["macros"] else ""))
        if cmds.floatSliderGrp(WEIGHT, exists=True):
            cmds.floatSliderGrp(WEIGHT, edit=True, value=params["macros"].get("weight", 0.0))
        if cmds.optionMenu(CHARACTER, exists=True):
            cmds.optionMenu(CHARACTER, edit=True, value=params["character"] or gait.CHARACTERS[0][0])
        if cmds.floatSliderGrp(STRENGTH, exists=True):
            cmds.floatSliderGrp(STRENGTH, edit=True, value=params["strength"])
        if cmds.checkBox(PHYSICS_BOX, exists=True):
            cmds.checkBox(PHYSICS_BOX, edit=True, value=params["physics"])
    finally:
        _QUIET[0] = quiet


def _set_key(key, value, own):
    """The parameter key `key` set by hand to `value` (in its unit, on the cycle whose own are `own`): a change from
    the own kept (none when it is the own), pinned; a two-sided parameter's own key links its sides again."""
    p, side = gait.param_of(key)
    changes, pins = _hand()
    if side is None and p.sided:
        for s in gait.SIDES:
            changes.pop(p.name + "_" + s, None)
            pins.discard(p.name + "_" + s)
    if p.kind == "toggle":
        value = 1.0 if value >= 0.5 else 0.0
    kind, x = gait.stored_change(p, gait.own_value(own, key), float(value))
    if (kind == "ratio" and abs(x - 1.0) < 1e-6) or (kind == "offset" and abs(x) < 1e-6):
        changes.pop(key, None)
    else:
        changes[key] = (kind, x)
    pins.add(key)
    _remember_hand(changes, pins)
    if p.name in ("step", "tempo"):            # set by hand: the Speed macro gives way
        macros = _macros()
        if macros.pop("speed", None) is not None:
            _remember("macros", json.dumps(macros))


def param_changed(name):
    """A released parameter: its value kept as a change from the active cycle's own, pinned - in Left / Right the
    side's alone, in Both the parameter's (its sides linked again). Every walker keyed again."""
    def changed(*_):
        if _QUIET[0]:
            return None
        active = _active()
        if active is None:
            return status(NO_WALK)
        cmds = _cmds()
        control = _control(name)
        if gait.P[name].kind == "toggle":
            if not cmds.checkBox(control, exists=True):
                return None
            value = 1.0 if cmds.checkBox(control, query=True, value=True) else 0.0
        else:
            if not cmds.floatSliderGrp(control, exists=True):
                return None
            value = float(cmds.floatSliderGrp(control, query=True, value=True))
        _set_key(_key(name), value, active[2])
        show_values()
        return slider_changed()
    return changed


def _let_go(name, keep_pin):
    """A parameter's change dropped - in Left / Right its side's, in Both every key of it: `keep_pin` holds it at the
    clip's value, else it follows the links and the macros again. Every walker keyed again."""
    def run():
        changes, pins = _hand()
        mode = side_mode()
        keys = [_key(name, mode)] if (gait.P[name].sided and mode != "both") else _keys(name)
        for key in keys:
            changes.pop(key, None)
            pins.discard(key)
        if keep_pin:
            pins.add(keys[0])
        _remember_hand(changes, pins)
        show_values()
        return _rekey("%s %s" % (gait.P[name].label, "back to the clip's" if keep_pin else "follows the links"))
    return _press(run)


def reset_param(name):
    return _let_go(name, True)


def free_param(name):
    return _let_go(name, False)


def speed_changed(*_):
    """The Speed macro: the step and the tempo each as its root (a Step or Tempo set by hand dropped)."""
    if _QUIET[0]:
        return None
    active = _active()
    if active is None:
        return status(NO_WALK)
    own_speed = float(active[2].get("speed", 0.0) or 0.0)
    value = float(_cmds().floatSliderGrp(SPEED, query=True, value=True))
    macros = _macros()
    if own_speed <= 0.0 or abs(value - own_speed) < 0.005:
        macros.pop("speed", None)
    else:
        macros["speed"] = value
    _remember("macros", json.dumps(macros))
    changes, pins = _hand()
    for key in ("step", "tempo"):
        changes.pop(key, None)
        pins.discard(key)
    _remember_hand(changes, pins)
    show_values()
    return slider_changed()


def weight_changed(*_):
    if _QUIET[0]:
        return None
    value = float(_cmds().floatSliderGrp(WEIGHT, query=True, value=True))
    macros = _macros()
    if abs(value) < 1e-3:
        macros.pop("weight", None)
    else:
        macros["weight"] = value
    _remember("macros", json.dumps(macros))
    show_values()
    return slider_changed()


def character_changed(*_):
    if _QUIET[0]:
        return None
    value = _cmds().optionMenu(CHARACTER, query=True, value=True) or ""
    _remember("character", "" if value == gait.CHARACTERS[0][0] else value)
    show_values()
    return slider_changed()


def strength_changed(*_):
    if _QUIET[0]:
        return None
    _remember("strength", float(_cmds().floatSliderGrp(STRENGTH, query=True, value=True)))
    show_values()
    return slider_changed()


def physics_changed(*_):
    if _QUIET[0]:
        return None
    _remember("physics", 1.0 if _cmds().checkBox(PHYSICS_BOX, query=True, value=True) else 0.0)
    return slider_changed()


def knee_pops_changed(*_):
    """Fix knee pops (the Physics tab): the knee pop fix of the retarget on or off (maya_walk.target.fix_pops)."""
    if _QUIET[0]:
        return None
    _remember("knee_pops", 1.0 if _cmds().checkBox(KNEE_POPS_BOX, query=True, value=True) else 0.0)
    return slider_changed()


# ---- the Diagnosis ----

def _diag_state():
    """The Diagnosis of the walker keyed last: who, its cycle, the findings. On sys (trap 111)."""
    state = getattr(sys, "_skeldar_walk_diag", None)
    if not isinstance(state, dict):
        state = {}
        sys._skeldar_walk_diag = state
    state.setdefault("who", "")
    state.setdefault("walk", None)
    state.setdefault("findings", [])
    return state


def _diag_row(i):
    return "skeldarWalkDiag_%d" % i


def _diag_text(i):
    return "skeldarWalkDiagText_%d" % i


def _diag_fix(i):
    return "skeldarWalkDiagFix_%d" % i


def show_diagnosis():
    """The Diagnosis rows: a finding each, its Fix enabled where it has one."""
    cmds = _cmds()
    state = _diag_state()
    findings = list(state["findings"])[:DIAG_ROWS]
    if cmds.text(DIAG_CAPTION, exists=True):
        if not state["who"]:
            label = "Diagnosis: Pick a walker"
        elif not findings:
            label = "Diagnosis - %s: nothing to say" % state["who"]
        else:
            label = "Diagnosis - %s" % state["who"]
        cmds.text(DIAG_CAPTION, edit=True, label=label)
    for i in range(DIAG_ROWS):
        if not cmds.columnLayout(_diag_row(i), exists=True):
            continue
        cmds.columnLayout(_diag_row(i), edit=True, manage=i < len(findings))
        if i < len(findings):
            cmds.text(_diag_text(i), edit=True, label=findings[i].text)
            cmds.button(_diag_fix(i), edit=True, enable=bool(findings[i].fix))


def fix_pressed(i):
    """A Diagnosis row's Fix: its parameters set (pinned) on the cycle the finding read, the selected walkers keyed again."""
    def go(*_):
        def run():
            state = _diag_state()
            if i >= len(state["findings"]):
                return "nothing to fix"
            finding = state["findings"][i]
            if not finding.fix:
                return finding.text
            name = state["walk"] or chosen_walk()
            own = gait.own(scene.load_walk(name, values())[0])
            for key, value in finding.fix.items():
                _set_key(key, value, own)
            show_values()
            return _rekey("fixed: %s" % finding.text)
        return _press(run)
    return go


def _show_findings(root, walk, info):
    """The Diagnosis of a walker just keyed."""
    if info.get("diagnosis") is None:
        return
    state = _diag_state()
    state.update(who="%s - %s" % (scene.walker_label(root), scene.walk_label(walk)), walk=walk,
                 findings=list(info["diagnosis"]))
    show_diagnosis()


def _migrate_knobs():
    """Once: the knobs a card remembered before the parameters (knob_<model knob>) read as parameters on the cycle
    its tempo was counted in (gait.from_legacy); tried again while no walk can be read."""
    cmds = _cmds()
    if cmds.optionVar(exists=OPTION + "params"):
        return
    knobs = {}
    for name in list(scene.wm.LEGACY) + [k for k, b in scene.wm.SIDE_KNOBS.items() if b in scene.wm.LEGACY]:
        if name in CARD_KNOBS:
            continue
        stored = _stored("knob_" + name)
        if stored is not None:
            knobs[name] = float(stored)
    if not knobs:
        _remember_hand({}, set())
        return
    name = _stored("tempoWalk") or ""
    try:
        name = name if name and scene.walk_exists(name) else chosen_walk()
        walk = scene.load_walk(name, values())[0]
    except scene.REFUSALS:
        return
    changes, pins, macros = gait.from_legacy(walk, knobs)
    for key, (kind, x) in list(changes.items()):
        if (kind == "ratio" and abs(x - 1.0) < 1e-6) or (kind == "offset" and abs(x) < 1e-6):
            del changes[key]
            pins.discard(key)
    _remember_hand(changes, pins)
    if macros:
        _remember("macros", json.dumps(macros))


def _set_parts(parts):
    cmds = _cmds()
    for part, _ in PART_LABELS:
        if cmds.checkBox(_part_control(part), exists=True):
            cmds.checkBox(_part_control(part), edit=True, value=part in parts)
    _remember("parts", json.dumps(list(parts)))


def show_side(mode):
    """The two-sided parameters on side `mode` ("both", "l", "r"): each slider shows that side's value (Both: the
    parameter's, marked * where the sides differ), its segment lit, remembered."""
    cmds = _cmds()
    mode = mode if mode in dict(SIDE_MODES) else "both"
    _remember("side", mode)
    if cmds.iconTextRadioButton(_side_tab(mode), exists=True):
        cmds.iconTextRadioButton(_side_tab(mode), edit=True, select=True)
    show_values()


def side_changed(mode):
    def go(*_):
        show_side(mode)
    return go


def knob_changed(name):
    """A released card knob (the pose's share, Seam, Smooth): remembered, the selected walkers keyed again."""
    def changed(*_):
        if _QUIET[0]:
            return None
        shown = _shown(name)
        if shown is not None:
            _remember("knob_" + name, shown)
        return slider_changed()
    return changed


def show_group(key):
    """Show the knob group `key` alone: its column managed, its tab lit, remembered."""
    cmds = _cmds()
    key = OLD_GROUPS.get(key, key)
    if key not in dict((k, l) for k, l, _ in GROUPS):
        key = GROUPS[0][0]
    _remember("group", key)
    for each, _, _ in GROUPS:
        if cmds.columnLayout(_group_column(each), exists=True):
            cmds.columnLayout(_group_column(each), edit=True, manage=each == key)
    if cmds.iconTextRadioButton(_group_tab(key), exists=True):
        cmds.iconTextRadioButton(_group_tab(key), edit=True, select=True)


def take_settings(root):
    """A walker's stored parameters, pose card and parts into the card (right button > Take its settings; selecting
    the walker does it too). Its cycle becomes the active one. A walker keyed before the parameters brings its knobs
    read as parameters (scene.memo_params)."""
    return _press(lambda: _take(root))


def _take(root):
    """take_settings's body: the card set from `root`'s memo, nobody keyed. The line."""
    if True:
        memo = scene.memo_of(root)
        if not memo.get("walk"):
            raise scene.Refusal("%s carries no walk of this tool - Pick one first" % scene.walker_label(root))
        params = scene.memo_params(root, memo)
        name, pose = memo["walk"], memo.get("pose")
        card = memo.get("pose_card") or (scene.wcards.legacy_card(pose) if pose else "")
        quiet, _QUIET[0] = _QUIET[0], True
        try:
            _set_walk(name)
            _set_card(card)
            _set_parts(tuple(memo.get("parts", scene.ALL_PARTS)))
            _remember_hand(params["changes"], set(params["pins"]))
            _remember("macros", json.dumps(params["macros"]))
            _remember("character", params["character"])
            _remember("strength", params["strength"])
            _remember("physics", 1.0 if params["physics"] else 0.0)
            _remember("knee_pops", 1.0 if params.get("knee_pops", True) else 0.0)
            cmds = _cmds()
            for box, name in ((PHYSICS_BOX, "physics"), (KNEE_POPS_BOX, "knee_pops")):
                if cmds.checkBox(box, exists=True):
                    cmds.checkBox(box, edit=True, value=bool(params.get(name, True)))
            _set_knobs(dict(params["clean"], pose=params["pose"], in_place=params["in_place"]))
            if scene.walk_exists(name):
                show_report(scene.load_walk(name, values())[3])
            show_values()
        finally:
            _QUIET[0] = quiet
        return "%s's settings are in the card - a parameter moved keys the working walkers" \
            % scene.walker_label(root)


_SELECTED = [None]       # the walker the selection named last: only a NEW one activates its cycle (a press that
                         # refreshes the card with that walker still selected must not undo a walk card clicked)


def _activate(root):
    """A listed walker that walks a card newly selected: that card the walk well's active one, the tempo's ratio
    kept (nobody re-keyed). A walker on its own cycle leaves the well alone."""
    if root == _SELECTED[0]:
        return
    _SELECTED[0] = root
    try:                                     # its own settings in the card: tuning starts from what it walks
        _take(root)
    except Exception:                                        # noqa: BLE001 - a memo the card cannot read
        print(traceback.format_exc())
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
    return "%d walker%s in the list - Pick or click one to work on it" % (count, "" if count == 1 else "s")


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
    """The subtitle and the list: the working walkers (the selection no longer chooses them, 2026-10-27)."""
    cmds = _cmds()
    if not cmds.text(SUBTITLE, exists=True):
        return
    try:
        cmds.text(SUBTITLE, edit=True, label=working_line())
        show_list()
    except Exception:                                        # noqa: BLE001
        print(traceback.format_exc())


def working_line():
    """The card's subtitle: the walkers it works on (Pick chose them), else what the selection would take."""
    working = scene.working()
    if working:
        names = ", ".join("%s (%s)" % (scene.walker_label(r), scene.walk_label(scene.memo_of(r).get("walk")))
                          for r in working[:3])
        more = " +%d" % (len(working) - 3) if len(working) > 3 else ""
        return "Working on %s%s - every change keys %s" % (names, more, "it" if len(working) == 1 else "them")
    return selection_line(scene.selected_top())


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
    """The walk `walk` (the active cycle) keyed onto `root` with the card's parameters (each a change from the
    cycle's own), the card's pose and parts; the Diagnosis of it shown. The line."""
    try:
        active = chosen_walk()
    except scene.Refusal:                     # an empty walk well: only a walk named here can be keyed
        if not walk:
            raise
        active = None
    walk = walk or active
    _remember("parts", json.dumps(list(chosen_parts())))
    result, info, text = scene.apply(root, walk, values(), None, chosen_parts(), pose_card=chosen_card(),
                                     params=card_params())
    if info.get("clean") is not None and walk == active:
        show_report(info["clean"])
    _show_findings(root, walk, info)
    return text


def rekey_all(walk=None, stop=None, roots=None):
    """Every listed walker (only those on the cycle `walk` when given, only `roots` when given) keyed again, each on its own cycle with the
    card's knobs and pose. A walker that fails is named, the others still keyed. Several walkers: a progress window
    names each in turn and Esc stops after the one it is on; `stop` (asked before each walker) True - a newer press
    waits, the rest are left to it. The line."""
    import time
    started = time.time()
    done, failed, lines, left, why = [], [], [], [], ""
    only, roots = roots, []
    for root in scene.walkers():
        name = scene.memo_of(root).get("walk")
        if (walk is None or name == walk) and (only is None or root in only):
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
        scene.set_working(roots)                     # the card works on them now, whatever is selected
        _SELECTED[0] = scene.selected_top()          # keyed with the card: nothing to take back from it
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
    """A released knob (a pose, a part): the selected walkers keyed again; none - say how to get one."""
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
    """The In place chip: remembered, the selected walkers keyed again."""
    if _QUIET[0]:
        return None
    shown = _shown("in_place")
    if shown is not None:
        _remember("knob_in_place", shown)
    return slider_changed()


def press_reset(*_):
    """Every parameter back to the clip's own: the changes, the pins, the macros and the character gone, the
    physics on (the pose's share, In place and the clean's knobs stay)."""
    def run():
        _remember_hand({}, set())
        _remember("macros", "{}")
        _remember("character", "")
        _remember("strength", 1.0)
        _remember("physics", 1.0)
        _remember("knee_pops", 1.0)
        show_values()
        return _rekey("every parameter back to the clip's")
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
        show_report(scene.load_walk(name, values())[3])
        show_values()
        return line
    return _press(run)


def press_fix_posture(*_):
    """Fix posture: the working walkers' walk posture set right - their own edit (scene.fix_posture says what it
    changes; the library's walk is never written, 2026-10-27) - the report shown, they keyed again."""
    def run():
        roots = scene.working()
        if not roots:
            raise scene.Refusal(NO_WORKING)
        lines = []
        for walk in sorted(set(scene.memo_of(r).get("walk") for r in roots)):
            report, line, fixed = scene.fix_posture(walk, values())
            show_report(report)
            lines.append(line)
            if fixed:
                for root in [r for r in roots if scene.memo_of(r).get("walk") == walk]:
                    edits = scene.walker_edits(root, walk)[0]
                    edits["posture"] = True
                    scene.set_edits(root, edits)
        return " | ".join(lines) + " | " + rekey_all(roots=roots)
    return _press(run)


def _working_root():
    working = scene.working()
    if not working:
        raise scene.Refusal(NO_WORKING)
    return working[0]


def _rekey_root(root):
    """The Rig pose's re-key of one walker, unrecorded (Ctrl+Z is the rig's): a working walker with the card's
    settings - the card works on it - another as it was keyed last."""
    from . import meanrig
    if root not in scene.working():
        return meanrig.rekey_root(root)
    memo = scene.memo_of(root)
    scene.apply(root, memo["walk"], values(), None, chosen_parts(), record=False, pose_card=chosen_card(),
                params=card_params())
    return " -> %s keyed again" % scene.walker_label(root)


def _shift(root, common):
    """What the key rigs moved alike on all four keys ({"height", "forward"} cm): the card's parameters when the
    walker is working (pinned changes, the sliders show them), else the walker's own."""
    from . import keyrig
    if root not in scene.working():
        return keyrig.shift_memo(root, common)
    params = scene.shift_params(card_params(), common)
    _remember_hand(params["changes"], set(params["pins"]))
    show_values()
    return ""


def press_mean_create(*_):
    """Rig pose > Create: the working walker's mean pose on a Manny rig (maya_walk.meanrig)."""
    from . import meanrig
    return _press(lambda: meanrig.press(_working_root(), values()))


def press_mean_update(*_):
    """Rig pose > Update: every rig pose's and every key rig's change into its walker's edits, that walker keyed
    again (unrecorded)."""
    from . import keyrig, meanrig

    def run():
        lines = []
        for module, quiet, kw in ((meanrig, (meanrig.NO_RIG, meanrig.NOTHING_MOVED), {"rekey": _rekey_root}),
                                  (keyrig, (keyrig.NO_RIG, keyrig.NOTHING_MOVED),
                                   {"rekey": _rekey_root, "shift": _shift})):
            try:
                line = module.update(**kw)
            except module.Refusal as error:
                if str(error) != module.NO_RIG:
                    raise
                continue
            if line not in quiet:
                lines.append(line)
        if not meanrig.rigs() and not keyrig.rigs():
            raise scene.Refusal("no rig pose and no key poses in the scene - press Create first")
        if not lines:
            return "nothing moved on the rig pose or the key poses since the last Update"
        return " | ".join(lines)
    return _press(run)


def press_mean_delete(*_):
    """Rig pose > Delete: the working walker's rig out of the scene."""
    from . import meanrig
    working = scene.working()
    return _press(lambda: meanrig.delete(working[0] if working else None))


def press_mean_reset(*_):
    """Rig pose > Reset: the working walker's mean pose correction dropped, its rig and the walker with it."""
    from . import meanrig
    return _press(lambda: meanrig.reset(_working_root(), values(), rekey=_rekey_root))


def press_key_create(*_):
    """Rig pose > Key poses > Create: the working walker's four key poses on four Manny rigs (maya_walk.keyrig)."""
    from . import keyrig
    return _press(lambda: keyrig.press(_working_root()))


def press_key_delete(*_):
    """Rig pose > Key poses > Delete: the working walker's key rigs out of the scene."""
    from . import keyrig
    working = scene.working()
    return _press(lambda: keyrig.delete(working[0] if working else None))


def press_key_reset(*_):
    """Rig pose > Key poses > Reset: the working walker's key pose edits dropped, its key rigs and it with them."""
    from . import keyrig
    return _press(lambda: keyrig.reset(_working_root(), rekey=_rekey_root))


# ---- Reset, a tab at a time (2026-10-27, «у каждой вкладки должна быть кнопка ресет») ----

def _group_params(key):
    """The parameters (base names) a tab's Reset takes back: a gait group's; Main's own."""
    if key == "main":
        return MAIN_PARAMS
    return dict((k, names) for k, _, names in GROUPS).get(key, ())


def reset_changes(changes, pins, names):
    """(changes, pins) less every key of the parameters `names` (both sides of a sided one) - pure."""
    def of(key):
        for name in names:
            if key == name or (key.startswith(name + "_") and key[len(name) + 1:] in gait.SIDES):
                return True
        return False
    return dict((k, v) for k, v in changes.items() if not of(k)), set(k for k in pins if not of(k))


def press_reset_group(key):
    """A tab's Reset: its parameters back to the clip's own (their changes and pins). Main: with Speed, Weight, the
    character and its strength. Physics: with Physics helpers and Fix knee pops on. Clean: Seam and Smooth back to
    their defaults and the working walkers' Fix posture off. Rig pose: the working walker's mean pose correction
    and key edits dropped. The working walkers keyed again."""
    from . import keyrig, meanrig

    def run():
        if key == "rigpose":
            root = _working_root()
            line = meanrig.reset(root, values(), rekey=lambda r: "")
            return line + " | " + keyrig.reset(root, rekey=_rekey_root)
        label = dict((k, name) for k, name, _ in GROUPS).get(key, "Main")
        if key == "clean":
            quiet, _QUIET[0] = _QUIET[0], True
            try:
                _set_knobs(dict((k, scene.ALL_DEFAULTS[k]) for k in ("seam", "smooth")))
            finally:
                _QUIET[0] = quiet
            for root in scene.working():
                walk = scene.memo_of(root).get("walk")
                edits = scene.walker_edits(root, walk)[0]
                if edits.get("posture"):
                    edits["posture"] = False
                    scene.set_edits(root, edits)
            return _rekey("Clean back to its defaults, Fix posture off")
        changes, pins = _hand()
        changes, pins = reset_changes(changes, pins, _group_params(key))
        _remember_hand(changes, pins)
        if key == "main":
            _remember("macros", "{}")
            _remember("character", "")
            _remember("strength", 1.0)
        if key == "physics":
            _remember("physics", 1.0)
            _remember("knee_pops", 1.0)
        show_values()
        return _rekey("%s back to the clip's own" % label)
    return _press(run)


def _section_head(name, label, tip, key):
    """A section's head: its name (a heading) and its Reset (press_reset_group(key)) on one row."""
    import maya_hubstyle as hubstyle
    cmds = _cmds()
    hubstyle.mark(cmds.rowLayout(numberOfColumns=2, adjustableColumn=1,
                                 columnAttach=[(1, "both", 0), (2, "both", 4)]), "fill", layout=True)
    hubstyle.mark(cmds.text(name, label=label, align="left", annotation=tip), "heading")
    hubstyle.mark(cmds.button(name + "Reset", label="Reset", height=hubstyle.height("small", 22),
                              annotation="%s: every setting here back to the clip's own" % label,
                              command=lambda *_: press_reset_group(key)), "secondary", "arrow-back-up")
    cmds.setParent("..")


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
    """A card knob's slider (the pose's share, Seam, Smooth)."""
    import maya_hubstyle as hubstyle
    cmds = _cmds()
    label, tip = LABELS[name]
    low, high = scene.ALL_RANGES[name]
    cmds.floatSliderGrp(_control(name), label=label, field=True, columnWidth3=hubstyle.pick((92, 44, 100), (100, 50, 150)),
                        adjustableColumn=3, height=hubstyle.height("small", 22), annotation=tip,
                        changeCommand=knob_changed(name), minValue=low, maxValue=high, fieldMinValue=low,
                        fieldMaxValue=high, step=0.05, precision=2,
                        value=float(_stored("knob_" + name, scene.ALL_DEFAULTS[name])))


def _param_menu(control, name):
    """A parameter's right button: back to the clip's (held), or let it follow the links again."""
    cmds = _cmds()
    cmds.popupMenu(parent=control, button=3)
    cmds.menuItem(label="Back to the clip's", annotation=TIPS["param_menu"], command=lambda *_: reset_param(name))
    cmds.menuItem(label="Follow the links", annotation=TIPS["param_menu"], command=lambda *_: free_param(name))
    cmds.setParent("..", menu=True)


def _param_control(p):
    """A parameter's slider (a toggle's chip), its range and value set by show_values."""
    import maya_hubstyle as hubstyle
    cmds = _cmds()
    control = _control(p.name)
    tip = p.tip + " | " + TIPS["param_menu"]
    if p.kind == "toggle":
        hubstyle.mark(cmds.checkBox(control, label=p.label, value=p.default >= 0.5, annotation=tip,
                                    changeCommand=param_changed(p.name)), "chip")
    else:
        fine = p.unit in ("", "x")
        cmds.floatSliderGrp(control, label=p.label, field=True,
                            columnWidth3=hubstyle.pick((92, 44, 100), (110, 50, 150)), adjustableColumn=3,
                            height=hubstyle.height("small", 22), annotation=tip, minValue=0.0, maxValue=1.0,
                            fieldMinValue=-1000.0, fieldMaxValue=1000.0, value=0.0, step=0.01 if fine else 0.1,
                            precision=2 if fine else 1, changeCommand=param_changed(p.name))
    _param_menu(control, p.name)


def _macro_rows():
    """Speed, Weight; the Character and its Strength."""
    import maya_hubstyle as hubstyle
    cmds = _cmds()
    common = dict(field=True, columnWidth3=hubstyle.pick((92, 44, 100), (110, 50, 150)), adjustableColumn=3,
                  height=hubstyle.height("small", 22))
    macros = _macros()
    cmds.floatSliderGrp(SPEED, label=LABELS["speed"][0], annotation=LABELS["speed"][1], minValue=0.2, maxValue=3.0,
                        fieldMinValue=0.05, fieldMaxValue=10.0, value=1.4, step=0.01, precision=2,
                        changeCommand=speed_changed, **common)
    cmds.floatSliderGrp(WEIGHT, label=LABELS["weight"][0], annotation=LABELS["weight"][1], minValue=-1.0,
                        maxValue=1.0, fieldMinValue=-1.0, fieldMaxValue=1.0, value=macros.get("weight", 0.0),
                        step=0.05, precision=2, changeCommand=weight_changed, **common)
    hubstyle.mark(cmds.rowLayout(numberOfColumns=2, adjustableColumn=2,
                                 columnAttach=[(1, "both", 0), (2, "both", 4)]), "fill", layout=True)
    cmds.optionMenu(CHARACTER, label="", annotation=TIPS["character"], changeCommand=character_changed)
    for name, _ in gait.CHARACTERS:
        cmds.menuItem(label=name, parent=CHARACTER)
    cmds.floatSliderGrp(STRENGTH, label=LABELS["strength"][0], annotation=LABELS["strength"][1], field=True,
                        columnWidth3=hubstyle.pick((56, 40, 60), (60, 44, 80)), adjustableColumn=3,
                        height=hubstyle.height("small", 22), minValue=0.0, maxValue=1.5, fieldMinValue=0.0,
                        fieldMaxValue=3.0, value=float(_stored("strength", 1.0)), step=0.05, precision=2,
                        changeCommand=strength_changed)
    cmds.setParent("..")


def _diagnosis_rows():
    """The Diagnosis: a caption, then DIAG_ROWS rows of a finding and its Fix (hidden while unused)."""
    import maya_hubstyle as hubstyle
    cmds = _cmds()
    hubstyle.mark(cmds.text(DIAG_CAPTION, label="Diagnosis: Pick a walker", align="left",
                            annotation=TIPS["diagnosis"]), "caption")
    for i in range(DIAG_ROWS):
        cmds.columnLayout(_diag_row(i), adjustableColumn=True, manage=False)
        cmds.rowLayout(numberOfColumns=2, adjustableColumn=1, columnAttach=[(1, "left", 0), (2, "left", 4)])
        cmds.text(_diag_text(i), label="", align="left", wordWrap=True, height=30, annotation=TIPS["diagnosis"])
        hubstyle.mark(cmds.button(_diag_fix(i), label="Fix", width=hubstyle.tool_width(44),
                                  height=hubstyle.height("field", 24), annotation=TIPS["diagnosis"],
                                  command=fix_pressed(i)), "secondary", "tool")
        cmds.setParent("..")
        cmds.setParent("..")


LIST_ROW = 18            # logical px a row of the walkers' list
LIST_ROWS = (2, 6)       # rows shown at least / at most (it scrolls past)


WORKING_MARK = "\u25b6 "


def _list_rows():
    """[(walker root, its row text)] - the card's list as the scene has it now; a working walker marked."""
    rows = []
    for root in scene.walkers():
        memo = scene.memo_of(root)
        rows.append((root, "%s%s - %s" % (WORKING_MARK if memo.get("working") else "   ", scene.walker_label(root),
                                          scene.walk_label(memo.get("walk")))))
    return rows


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
    lit = [i + 1 for i, (root, _) in enumerate(rows) if scene.memo_of(root).get("working")]
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
    """Rows clicked: those walkers are the working ones (and selected in the scene); the first one's settings come
    into the card, nobody is keyed (2026-10-27)."""
    roots = _picked_walkers()
    if not roots:
        return None
    scene.set_working(roots)
    try:
        _take(roots[0])
    except scene.REFUSALS as refusal:
        status(str(refusal))
    _cmds().select(roots, replace=True)
    refresh()
    return status("working on %s - every change keys %s" % (", ".join(scene.walker_label(r) for r in roots),
                                                            "it" if len(roots) == 1 else "them"))


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
    """The Rig pose tab: the mean pose's Create / Reset / Delete, the key poses' Create / Reset / Delete, one Update
    for both, a line on what they do."""
    import maya_hubstyle as hubstyle
    cmds = _cmds()
    sections = (
        (MEAN_CAPTION, "Mean pose", ((MEAN_CREATE_BTN, "Create", "secondary", "user", "mean_create", press_mean_create),
                                     (MEAN_RESET_BTN, "Reset", "secondary", "arrow-back-up", "mean_reset",
                                      press_mean_reset),
                                     (MEAN_DELETE_BTN, "Delete", "danger", "trash", "mean_delete", press_mean_delete))),
        (KEY_CAPTION, "Key poses", ((KEY_CREATE_BTN, "Create", "secondary", "walk", "key_create", press_key_create),
                                    (KEY_RESET_BTN, "Reset", "secondary", "arrow-back-up", "key_reset", press_key_reset),
                                    (KEY_DELETE_BTN, "Delete", "danger", "trash", "key_delete", press_key_delete))),
        (None, None, ((MEAN_UPDATE_BTN, "Update", "primary", "refresh", "mean_update", press_mean_update),)))
    for caption, title, row in sections:
        if caption:
            hubstyle.mark(cmds.text(caption, label=title, align="left"), "heading")
        columns = len(row)
        attach = [(1, "both", 0)] + [(i, "both", 4) for i in range(2, columns + 1)]
        hubstyle.mark(cmds.rowLayout(numberOfColumns=columns, adjustableColumn=1, columnAttach=attach), "fill",
                      layout=True)
        for name, label, role, icon, tip, action in row:
            hubstyle.mark(cmds.button(name, label=label, height=hubstyle.height("button", 28), annotation=TIPS[tip],
                                      command=(lambda act: lambda *_: act())(action)), role, icon)
        cmds.setParent("..")
    hubstyle.mark(cmds.text(MEAN_NOTE, label="Create a rig, pose its controls, then Update: the mean pose changes "
                            "the whole cycle, a key pose its key.", align="left", wordWrap=True, height=36),
                  "caption")


def build_panel():
    """The card into the current layout: the subtitle; the walk and the pose wells; the pose's share and parts;
    Pick / Reset / In place; the walkers; [Both | Left | Right]; the Main parameters; the macros; the tabs of the
    other parameters and the one shown; the status line; the Diagnosis."""
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
    side = side_mode()
    sides = cmds.rowLayout(numberOfColumns=len(SIDE_MODES),
                           columnAttach=[(i + 1, "both", 1) for i in range(len(SIDE_MODES))])
    hubstyle.mark(sides, "segments", layout=True)
    cmds.iconTextRadioCollection(SIDE_TABS)
    for mode, label in SIDE_MODES:
        hubstyle.mark(cmds.iconTextRadioButton(
            _side_tab(mode), style="textOnly", label=label, height=hubstyle.height("segment", 24),
            select=mode == side, collection=SIDE_TABS,
            annotation=("A two-sided parameter sets both sides" if mode == "both" else
                        "A two-sided parameter (marked %s) sets the %s side alone; Both links its sides again "
                        "when it is moved" % (SIDE_MARK[mode].strip(), "left" if mode == "l" else "right")),
            onCommand=side_changed(mode)), "segment")
    cmds.setParent("..")
    _section_head(MAIN_HEAD, "Main", "The whole walk at once: tempo, step, width, bounce, lean, the arms - and the "
                  "macros under them", "main")
    for name in MAIN_PARAMS:
        _param_control(gait.P[name])
    _macro_rows()
    hubstyle.mark(cmds.text(DETAILS_HEAD, label="Details", align="left",
                            annotation="A part of the walk at a time - each tab has its own Reset"), "heading")
    shown = OLD_GROUPS.get(_stored("group", GROUPS[0][0]), _stored("group", GROUPS[0][0]))
    labels = dict((key, (label, names)) for key, label, names in GROUPS)
    cmds.iconTextRadioCollection(GROUP_TABS)
    for row in GROUP_ROWS:                # the tabs on two rows, one collection
        segments = cmds.rowLayout(numberOfColumns=len(row),
                                  columnAttach=[(i + 1, "both", 1) for i in range(len(row))])
        hubstyle.mark(segments, "segments", layout=True)
        for key in row:
            label, names = labels[key]
            what = ", ".join(gait.P[n].label if n in gait.P else LABELS[n][0] for n in names) or "the walk's mean pose"
            hubstyle.mark(cmds.iconTextRadioButton(
                _group_tab(key), style="textOnly", label=label, height=hubstyle.height("segment", 24),
                select=key == shown, collection=GROUP_TABS, annotation="%s: %s" % (label, what),
                onCommand=group_changed(key)), "segment")
        cmds.setParent("..")
    for key, label, names in GROUPS:
        cmds.columnLayout(_group_column(key), adjustableColumn=True, rowSpacing=hubstyle.row_spacing(2),
                          manage=key == shown)
        _section_head("skeldarWalkHead_" + key, label, "The %s settings" % label, key)
        for name in names:
            if name in gait.P:
                _param_control(gait.P[name])
            else:
                _slider(name)
        if key == "physics":              # the helpers as a whole
            hubstyle.mark(cmds.checkBox(PHYSICS_BOX, label="Physics helpers", annotation=TIPS["physics"],
                                        value=float(_stored("physics", 1.0)) >= 0.5,
                                        changeCommand=physics_changed), "chip")
            hubstyle.mark(cmds.checkBox(KNEE_POPS_BOX, label="Fix knee pops", annotation=TIPS["knee_pops"],
                                        value=float(_stored("knee_pops", 1.0)) >= 0.5,
                                        changeCommand=knee_pops_changed), "chip")
        if key == "rigpose":              # the walk's mean pose on a Manny rig: create, pose it, Update
            _rig_pose_buttons()
        if key == "clean":                # the posture set right once, then what the clean found
            hubstyle.mark(cmds.button(FIX_BTN, label="Fix posture", height=hubstyle.height("button", 26),
                                      annotation=TIPS["fix_posture"], command=lambda *_: press_fix_posture()),
                          "secondary", "tool")
            hubstyle.mark(cmds.text(CLEAN_REPORT, label="", align="left", wordWrap=True, height=72), "caption")
        cmds.setParent("..")
    hubstyle.mark(cmds.text(STATUS, label="", align="left", wordWrap=True, height=54), "status")
    _diagnosis_rows()
    cmds.setParent("..")
    try:
        _migrate_knobs()
        walk, _, _, report = scene.load_walk(chosen_walk(), values())
        show_report(report)
    except Exception:                                        # noqa: BLE001 - no walk saved yet
        pass
    show_group(shown)
    show_side(side)                       # the parameters' values with it
    show_diagnosis()
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
    import maya_hubqt
    #  a hidden card refreshes when it is next shown (2026-10-17, maya_hubqt.when_seen)
    JOB[_card_key()] = cmds.scriptJob(event=["SelectionChanged", maya_hubqt.seen_only(STATUS, refresh)],
                                      parent=STATUS)


def is_open():
    return bool(_cmds().text(STATUS, exists=True))


def show_window():
    """The hub, on the Walk Builder section."""
    import maya_hub
    return maya_hub.show(HUB_SECTION)
