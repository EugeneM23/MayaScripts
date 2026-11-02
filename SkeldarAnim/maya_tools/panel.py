"""The hub's Tools card (2026-10-12): OverRig's Knots and Double knot, native.

The animator: «заведем раздел тул и реализуем такие же инструменты»; the same day «все кнопочки
одинаково важные» (every button orange) and «два под раздела Knots и Double knots ... кнопочки ...
растягивать вместе с интерфейсом»: the subsection Knots - Knot, Offset (two presses: it reads
Finish while a pivot waits), Orient; the subsection Double knot - Local, World; the buttons of a
row share the card's width (the skin's `fill`); under them the knots' rotate order
[Object | XYZ | XZY] and Bake, Remove; the status line; which knots stand is the subtitle. The
presses are module functions reading the remembered rotate order, so the hotkey rows work with the
card closed. The scene half is `knots`, the pure half `knotplan`.

The parent tab (2026-10-12) added Parent, Multiple across and Attach; the aim tab (2026-10-13,
«Теперь давай реализуем функционал AIM») adds Aim (two presses: it reads Finish while an aim
waits) and Overlap (Softness, Lag, Easing, four chips, the press; the scene half `overlap`, the
pure half `overlapplan`). Layer (2026-10-13, «запекания на адитивный слой») stands between Bake and
Remove: everything that animates the selected objects baked onto a new additive layer, the base
left on the first frame's pose (`layerbake`).

The card as a list (2026-10-13, «сделать все более понятно, разложить по разделам ... кнопки не
должны быть такими оранжевыми»; the animator chose mockup C of four): three subsections - Knots
(Knot, Offset, Orient, Local ×2, World ×2, Aim and the rotate order of new knots), Parent (Inside,
To world, Swap, Across and the pairs), Overlap - each a head that opens and closes its body
(remembered), each tool a flat row with its explanation beside its name (the skin's `toolrow`);
under them «Selected knots»: Attach 0 / 1, Bake, Layer, Remove. Nothing is orange but a row that
reads Finish (a pivot or an aim waiting for you).

Snapshot (2026-10-13, «Давай реализуем создание снапшотов») is a row of Knots after Aim: a
locator per selected object repeating its world motion on every frame, driving nothing
(`knots.snapshot`).

Spec: docs/superpowers/specs/2026-10-12-tools-knots-design.md,
docs/superpowers/specs/2026-10-13-tools-aim-overlap-design.md,
docs/superpowers/specs/2026-10-13-tools-bake-to-layer-design.md,
docs/superpowers/specs/2026-10-13-tools-card-list-design.md,
docs/superpowers/specs/2026-10-13-tools-snapshot-design.md
"""

import sys
import traceback

import maya.cmds as cmds

import maya_hubcopy as hubcopy
import maya_hubstyle as hubstyle
from maya_tools import firstperson
from maya_tools import knotplan as plan
from maya_tools import knots
from maya_tools import layerbake
from maya_tools import overlap as overlapper
from maya_tools import overlapplan
from maya_tools import reparent

HUB_SECTION = "tools"
SUBTITLE = "skeldarToolsSubtitle"
STATUS = "skeldarToolsStatus"
#  The subsections (2026-10-13): key, name, the hint beside the name. Each a head that opens and
#  closes its body, remembered (`OPEN_VAR`); Knots open by default.
SECTIONS = (
    ("knots", "Knots", "drive with a locator"),
    ("parent", "Parent", "motion kept"),
    ("overlap", "Overlap", "on a new layer"),
    ("firstperson", "1P", "3P take split by layers"),
)
HEAD = dict((key, "skeldarToolsHead_" + key) for key, _, _ in SECTIONS)
BODY = dict((key, "skeldarToolsBody_" + key) for key, _, _ in SECTIONS)
OPEN_VAR = "skeldarToolsOpen_%s"
OPEN_DEFAULT = {"knots": True, "parent": False, "overlap": False, "firstperson": False}
ORDER_LABEL = "skeldarToolsOrderLabel"
KNOT_BTN = "skeldarToolsKnot"
OFFSET_BTN = "skeldarToolsKnotOffset"
ORIENT_BTN = "skeldarToolsKnotOrient"
LOCAL_BTN = "skeldarToolsDoubleLocal"
WORLD_BTN = "skeldarToolsDoubleWorld"
BAKE_BTN = "skeldarToolsBake"
LAYER_BTN = "skeldarToolsBakeLayer"
REMOVE_BTN = "skeldarToolsRemove"
ORDER = "skeldarToolsOrder"
ORDER_SEG = dict((choice, "skeldarToolsOrder_" + choice) for choice in plan.ORDERS)
ORDER_VAR = "skeldarKnotRotateOrder"
#  The parent tab (2026-10-12, «весь функционал из вкладки parent»).
INSIDE_BTN = "skeldarToolsInside"
TOWORLD_BTN = "skeldarToolsToWorld"
SWAP_BTN = "skeldarToolsSwap"
ACROSS_BTN = "skeldarToolsAcross"
PAIRS_CAPTION = "skeldarToolsPairsCaption"
OBJECTS_BTN = "skeldarToolsObjects"
TARGETS_BTN = "skeldarToolsTargets"
LISTSWAP_BTN = "skeldarToolsListSwap"
ROTATE_CHIP = "skeldarToolsAcrossRotate"
TRANSLATE_CHIP = "skeldarToolsAcrossTranslate"
MULTI_BTN = "skeldarToolsMultiAcross"
FOOTER = "skeldarToolsFooter"
FOOTER_CAPTION = "skeldarToolsFooterCaption"
ATTACH0_BTN = "skeldarToolsAttach0"
ATTACH1_BTN = "skeldarToolsAttach1"
ROTATE_VAR = "skeldarAcrossRotate"
TRANSLATE_VAR = "skeldarAcrossTranslate"
#  The aim tab (2026-10-13).
AIM_BTN = "skeldarToolsAim"
SNAPSHOT_BTN = "skeldarToolsSnapshot"
FP_BTN = "skeldarTools1PSetup"
#  The camera's parent (2026-10-21): its control under Main / Root / Chest / World.
CAMPARENT_CAPTION = "skeldarToolsCameraParentCaption"
CAMPARENT_BTN = dict((c, "skeldarToolsCameraParent" + c)
                     for c in ("Main", "Root", "Chest", "World"))
OVERLAP_NAMES = "skeldarToolsOverlapNames"
OVERLAP_FIELDS = "skeldarToolsOverlapFields"
SOFT_LABEL = "skeldarToolsSoftnessLabel"
SOFT_FIELD = "skeldarToolsSoftness"
LAG_LABEL = "skeldarToolsLagLabel"
LAG_FIELD = "skeldarToolsLag"
EASE_LABEL = "skeldarToolsEasingLabel"
EASE_FIELD = "skeldarToolsEasing"
HIER_CHIP = "skeldarToolsHierarchy"
CYCLE_CHIP = "skeldarToolsCycled"
TOTAL_CHIP = "skeldarToolsTotalLag"
EDGES_CHIP = "skeldarToolsKeepEdges"
OVERLAP_BTN = "skeldarToolsOverlap"
SOFT_VAR = "skeldarOverlapSoftness"
LAG_VAR = "skeldarOverlapLag"
EASE_VAR = "skeldarOverlapEasing"
HIER_VAR = "skeldarOverlapHierarchy"
CYCLE_VAR = "skeldarOverlapCycled"
TOTAL_VAR = "skeldarOverlapTotal"
EDGES_VAR = "skeldarOverlapEdges"
#  The name column of the Rotate order row, logical px (skin, classic).
LABEL_W = (78, 90)
#  The refresh job of each card standing: '' the hub's, a popup copy's tag its own (the
#  2026-10-09 rule: closing a popup kills only its own job).
JOB = {}

#  OverRig's own explanations, from its buttons' annotations, in the card's words.
TIPS = {
    "knot": "Knot - select objects: each one's animation is baked onto a knot (a locator) and the "
            "object follows it. A highlighted range on the time slider makes the knot work "
            "only there (attach blends it in and out)",
    "offset": "Knot Offset - select one object: a pivot appears on it - move and turn it where "
              "the knot should turn the object (it rides the object while you place it), then "
              "press this button again (it reads Finish)",
    "orient": "Knot Orient - select objects: the knot rides each object's position and carries only its "
              "rotation; the object keeps its own translation animation",
    "local": "Double knot, local: the outer knot carries the object's whole animation, the "
             "inner one drives it - key the inner to change the animation in the object's own "
             "animated axes",
    "world": "Double knot, world: the outer knot keeps world axes and carries the position, "
             "the inner one the rotation - turn or move the outer to bend the animation in "
             "world axes about the object's pivot",
    "bake": "Bake: the selected knots' objects (or the selected objects riding knots) take "
            "what the knots give them on every frame; the knots go",
    "layer": "Layer - select objects (or their knots): everything that animates them moves "
             "onto a new additive layer - their own keys as keys (none lost), our knots and "
             "your constraints baked - and the base keeps the pose of the first frame (mute the "
             "layer and they stand, weight it to blend). A highlighted range moves only that "
             "part: outside it the base keeps its keys",
    "remove": "Remove: the selected knots go and their objects play their own animation "
              "again exactly; a waiting pivot is dropped",
    "inside": "Inside - select the objects, then the parent LAST: they move under it in the "
              "hierarchy, their animation re-baked into its space (the motion stays)",
    "to_world": "World - the selected objects move out to world level, their animation "
                "re-baked into world space (the motion stays)",
    "swap": "Swap - select the parent first, then its child: the child takes the parent's place "
            "and the parent goes under it, the motion of both kept",
    "across": "Across - select the objects, then the one they ride LAST: each object rides a "
              "knot inside it (attach, a range, Bake / Remove like any knot)",
    "objects": "Objects - remember the selection as the objects of Multiple across",
    "targets": "Targets - remember the selection as the targets: object 1 rides target 1, ...",
    "swap_lists": "Swap the Objects and the Targets",
    "multi": "Pairs - Across, pair by pair: each remembered object rides a knot inside its "
             "target (Rotate / Translate say which half follows)",
    "rotate": "Multiple across: the objects follow their targets' rotation",
    "translate": "Multiple across: the objects follow their targets' translation",
    "attach0": "Attach 0: key the selected knots off (the object plays its own animation) - at "
               "the highlight's ends, the selected keys, or the current frame",
    "attach1": "Attach 1: key the selected knots on - at the highlight's ends, the selected "
               "keys, or the current frame",
    "aim": "Aim - select objects: a target (along each object's X) and an up (along its Y) "
           "appear, riding it - move them where it should point and lean, then press this "
           "button again (it reads Finish): the object's rotation aims at the target from then "
           "on (attach, a range, Bake / Remove like any knot)",
    "snapshot": "Snapshot - select objects: each gets a locator repeating its motion in world "
                "space, keyed on every frame (of the highlighted range, else the whole take). "
                "Nothing follows it - use it as a target or a reference; Remove deletes it",
    "softness": "Overlap: how far ahead each link looks, times its length - smaller gives more "
                "overlap",
    "lag": "Overlap: the frames each link trails the one above (Total lag: the whole chain's)",
    "easing": "Overlap: smooths the root's motion before it travels down the chain - takes the "
              "shake out (0: none)",
    "hierarchy": "Overlap: each selected object is a chain's root - the chain follows its "
                 "descendants of the same kind; off: the selection, top to bottom, is the chain",
    "cycled": "Overlap: the take loops - the lag wraps round its end",
    "total": "Overlap: Lag is the whole chain's, shared over its links",
    "edges": "Overlap: the first and last poses stay as they are - the overlap fades in over "
             "the first fifth and out over the last",
    "fp_setup": "1P Setup - select any part of a rig: its geometry to 1P, the chest control "
                "Chest_1P_ctrl (a red square) on FKSpine3_M, the lower body and the chest's "
                "travel onto layer _3P_Lower_Body, the upper body and the chest's turn onto "
                "_3P_Upper_Body (the base keeps the first frame); the camera's control, the IK "
                "arms, a weapon out of the hands and Aim Mode's controllers ride the chest. Lower alone: the legs with a stable top; both: the 3P take as "
                "it was",
    "camparent": "The selected character's camera control (Camera_ctrl) under %s - its "
                 "motion kept on every frame",
    "overlap": "Overlap - select a chain's root (Hierarchy) or its members top to bottom: each "
               "link trails its own motion, keyed on a new additive layer 'Overlap' (mute, "
               "weight or delete it; pressing again replaces it). A highlighted range overlaps "
               "only there",
}
ORDER_TIPS = {
    "object": "New knots take their object's own rotate order",
    "xyz": "New knots rotate in XYZ order",
    "xzy": "New knots rotate in XZY order",
}
#  Each tool row's explanation, beside its name in the skin (2026-10-13, mockup C). Short: the
#  card is ~290 logical px wide in the animator's dock; the tooltip keeps the whole story.
HINTS = {
    KNOT_BTN: "object follows a locator",
    OFFSET_BTN: "knot at your own pivot",
    ORIENT_BTN: "carries rotation only",
    LOCAL_BTN: "double knot, own axes",
    WORLD_BTN: "double knot, world axes",
    AIM_BTN: "points at a target",
    SNAPSHOT_BTN: "free copy of the motion",
    INSIDE_BTN: "under the last selected",
    TOWORLD_BTN: "out to world level",
    SWAP_BTN: "child takes parent's place",
    ACROSS_BTN: "rides the last selected",
    OVERLAP_BTN: "trail onto a new layer",
    FP_BTN: "layers, chest, 1P camera",
}


# ------------------------------------------------------------------ state

def order():
    """The rotate order new knots take: 'object', 'xyz' or 'xzy' (remembered)."""
    value = cmds.optionVar(query=ORDER_VAR) if cmds.optionVar(exists=ORDER_VAR) else None
    return value if value in plan.ORDERS else plan.ORDER_DEFAULT


def set_order(choice):
    if choice in plan.ORDERS:
        cmds.optionVar(stringValue=(ORDER_VAR, choice))
    return order()


def status(message):
    """The card's line - and the hub's one message line (`hubstyle.tell`). Answers `message`,
    so a hotkey row can show it when the card is closed."""
    if cmds.text(STATUS, exists=True):
        cmds.text(STATUS, edit=True, label=message)
        hubstyle.tell(STATUS, message)
    return message


def refresh(*_):
    """Which knots stand, and the Offset and Aim rows' word - lit while they read Finish."""
    if not cmds.text(SUBTITLE, exists=True):
        return
    try:
        snaps = len(knots.snapshots())
        count, waiting = len(knots.knots()) - snaps, len(knots.pivots())
        aims = len(knots.aims_waiting())
    except Exception:                                        # noqa: BLE001
        return
    cmds.text(SUBTITLE, edit=True, label=plan.subtitle(count, waiting, aims, snaps))
    for name, word, waits in ((OFFSET_BTN, plan.offset_label(bool(waiting)), bool(waiting)),
                              (AIM_BTN, plan.aim_label(bool(aims)), bool(aims))):
        if cmds.button(name, exists=True):
            cmds.button(name, edit=True, label=word)
            _light(name, "wait" if waits else "")
    _paint_lists()


def _light(name, state):
    """The skin's state of control `name` (maya_hubqt.set_state): a tool row "wait", a head
    "open" / "closed". Nothing without Maya's UI - the one place this module reaches Qt."""
    try:
        import maya_hubqt
        if maya_hubqt.available():
            maya_hubqt.set_state(name, state)
    except Exception:                                        # noqa: BLE001
        pass


# ------------------------------------------------------------ subsections

def is_section_open(key):
    """Whether subsection `key` is open (remembered; Knots open, the others closed, at first)."""
    var = OPEN_VAR % key
    if cmds.optionVar(exists=var):
        return bool(cmds.optionVar(query=var))
    return OPEN_DEFAULT.get(key, True)


def set_section_open(key, on):
    """Open or close subsection `key` in this card - its body managed or not, its head's chevron
    - and remember it. Answers `on`."""
    on = bool(on)
    cmds.optionVar(intValue=(OPEN_VAR % key, int(on)))
    if cmds.columnLayout(BODY[key], exists=True):
        cmds.columnLayout(BODY[key], edit=True, manage=on)
    _light(HEAD[key], "open" if on else "closed")
    return on


def toggle_section(key):
    """A head's press: this card's body flips (asked of the body itself - the hub's card and a
    popup copy share the memory, not their state)."""
    if cmds.columnLayout(BODY[key], exists=True):
        shown = bool(cmds.columnLayout(BODY[key], query=True, manage=True))
    else:
        shown = is_section_open(key)
    return set_section_open(key, not shown)


# ------------------------------------------------------- multiple across

def _lists():
    """The remembered Objects and Targets (UUIDs) for the Maya session - on `sys`, so a purge
    of our modules (an update, a verify) does not split them (trap 111)."""
    if not hasattr(sys, "_skeldar_tools_lists"):
        sys._skeldar_tools_lists = {"objects": [], "targets": []}
    return sys._skeldar_tools_lists


def _resolved(key):
    """The remembered list's nodes that still exist, long paths, in order."""
    out = []
    for uuid in _lists()[key]:
        found = cmds.ls(uuid, long=True) or []
        if found:
            out.append(found[0])
    return out


def _paint_lists():
    for name, key, word in ((OBJECTS_BTN, "objects", "Objects"),
                            (TARGETS_BTN, "targets", "Targets")):
        if cmds.button(name, exists=True):
            cmds.button(name, edit=True, label=plan.list_label(word, len(_resolved(key))))


def _remember(key):
    nodes = knots._selection(None)
    _lists()[key] = [knots._uuid(n) for n in nodes]
    _paint_lists()
    word = "Objects" if key == "objects" else "Targets"
    return status("%s: %s" % (word, ", ".join(plan.leaf(n) for n in nodes) if nodes
                              else "cleared"))


def remember_objects():
    return _remember("objects")


def remember_targets():
    return _remember("targets")


def swap_lists():
    lists = _lists()
    lists["objects"], lists["targets"] = lists["targets"], lists["objects"]
    _paint_lists()
    return status("Objects and Targets swapped")


def _flag(var, default=True):
    return bool(cmds.optionVar(query=var)) if cmds.optionVar(exists=var) else default


def _flag_changed(var):
    return lambda value, *_: cmds.optionVar(intValue=(var, int(bool(value))))


def _number(field, var, default):
    """A remembered number: the card's field while it stands (and remembered), else the
    optionVar, else `default` - so the hotkey row works with the card closed."""
    if field and cmds.floatField(field, exists=True):
        value = float(cmds.floatField(field, query=True, value=True))
        cmds.optionVar(floatValue=(var, value))
        return value
    if cmds.optionVar(exists=var):
        return float(cmds.optionVar(query=var))
    return default


def _number_changed(var):
    return lambda value, *_: cmds.optionVar(floatValue=(var, float(value)))


def multiple_across():
    def act():
        objects, targets = _resolved("objects"), _resolved("targets")
        rotate, translate = _flag(ROTATE_VAR), _flag(TRANSLATE_VAR)
        refusal = plan.multiple_refusal(len(objects), len(targets), rotate, translate)
        if refusal:
            return refusal
        return knots.create_across(list(zip(objects, targets)), order(), rotate=rotate,
                                   translate=translate)
    return _press(act)


# ---------------------------------------------------------------- presses

def _press(action):
    try:
        message = action()
    except Exception as exc:                                 # noqa: BLE001
        print(traceback.format_exc())
        message = "Tools failed: %s" % exc
    refresh()
    return status(message)


def knot():
    return _press(lambda: knots.create("knot", order=order()))


def knot_offset():
    """Offset, or Finish while a pivot waits."""
    return _press(lambda: knots.finish_offset() if knots.waiting()
                  else knots.begin_offset(order=order()))


def knot_orient():
    return _press(lambda: knots.create("orient", order=order()))


def double_local():
    return _press(lambda: knots.create("double_local", order=order()))


def double_world():
    return _press(lambda: knots.create("double_world", order=order()))


def bake():
    return _press(knots.bake)


def bake_layer():
    return _press(layerbake.bake)


def inside():
    return _press(reparent.inside)


def to_world():
    return _press(reparent.to_world)


def swap():
    return _press(reparent.swap)


def across():
    return _press(lambda: knots.across(order=order()))


def attach_0():
    return _press(lambda: knots.set_attach(0.0))


def attach_1():
    return _press(lambda: knots.set_attach(1.0))


def aim():
    """Aim, or Finish while an aim waits."""
    return _press(lambda: knots.finish_aim() if knots.aims_waiting()
                  else knots.begin_aim(order=order()))


def snapshot():
    return _press(lambda: knots.snapshot(order=order()))


def fp_setup():
    """1P Setup (2026-10-16)."""
    return _press(firstperson.setup)


def camera_parent(choice):
    """The camera's control under `choice` (Main / Root / Chest / World), 2026-10-21."""
    return _press(lambda: firstperson.camera_parent(choice))


def _camera_parent(choice):
    return lambda: camera_parent(choice)


def overlap_settings():
    """The Overlap's settings as the card (or the memory) holds them."""
    d = overlapplan.DEFAULTS
    return overlapplan.Settings(
        softness=_number(SOFT_FIELD, SOFT_VAR, d.softness),
        lag=_number(LAG_FIELD, LAG_VAR, d.lag),
        easing=_number(EASE_FIELD, EASE_VAR, d.easing),
        hierarchy=_flag(HIER_VAR, d.hierarchy), cycled=_flag(CYCLE_VAR, d.cycled),
        total=_flag(TOTAL_VAR, d.total), edges=_flag(EDGES_VAR, d.edges))


def overlap():
    return _press(lambda: overlapper.run(settings=overlap_settings()))


def remove():
    return _press(knots.remove)


def _order_changed(choice):
    return lambda *_: set_order(choice)


# ------------------------------------------------------------------- card

def _row(name, label, icon, tip, press):
    """A tool: a flat row, its icon, its name and its explanation (the skin's `toolrow`; the
    classic hub's plain button) - 2026-10-13, mockup C."""
    return hubstyle.mark(cmds.button(name, label=label, annotation=tip, align="left",
                                     height=hubstyle.height("button", 26),
                                     command=lambda *_: press()),
                         "toolrow", icon, hint=HINTS.get(name))


def _button(name, label, icon, tip, press, role="secondary"):
    """An ordinary button of the card (the pairs, the footer): outlined, not orange."""
    return hubstyle.mark(cmds.button(name, label=label, annotation=tip,
                                     height=hubstyle.height("button", 26),
                                     command=lambda *_: press()), role, icon)


def _caption(name, label):
    """A small muted line that stays visible (a `note` would become the header's tooltip)."""
    return hubstyle.mark(cmds.text(name, label=label, align="left"), "caption")


def _head(key, label, hint):
    """A subsection's head: its chevron, its name, its hint; a press opens or closes it."""
    name = hubstyle.mark(cmds.button(HEAD[key], label=label, align="left",
                                     height=hubstyle.height("button", 26),
                                     annotation="Open or close %s" % label,
                                     command=lambda *_: toggle_section(key)),
                         "subhead", hint=hint)
    _light(name, "open" if is_section_open(key) else "closed")
    return name


def _body(key):
    """A subsection's body: a column managed while it is open."""
    return cmds.columnLayout(BODY[key], adjustableColumn=True,
                             rowSpacing=hubstyle.row_spacing(4),
                             manage=is_section_open(key))


def _named_row():
    """A row with its name in a column of one width (Rotate order)."""
    return cmds.rowLayout(numberOfColumns=2, adjustableColumn=2,
                          columnWidth=[(1, hubstyle.pick(LABEL_W[0], LABEL_W[1]))],
                          columnAttach=[(1, "both", 0), (2, "both", 0)])


def _chip(name, label, var, tip, default=True):
    return hubstyle.mark(cmds.checkBox(name, label=label, value=_flag(var, default),
                                       annotation=tip, changeCommand=_flag_changed(var)), "chip")


def _fill_row(columns):
    """A row whose buttons share the card's width and stretch with it (the skin's `fill`; the
    classic hub keeps their own widths)."""
    row = cmds.rowLayout(numberOfColumns=columns,
                         columnAttach=[(1, "both", 0)]
                         + [(i, "both", 4) for i in range(2, columns + 1)])
    return hubstyle.mark(row, "fill", layout=True)


def _columns_row(name, columns):
    """A row whose widgets - names or fields - share the card's width (the skin's `columns`)."""
    row = cmds.rowLayout(name, numberOfColumns=columns,
                         columnAttach=[(1, "both", 0)]
                         + [(i, "both", 4) for i in range(2, columns + 1)])
    return hubstyle.mark(row, "columns", layout=True)


def _knots_body():
    _row(KNOT_BTN, "Knot", "link", TIPS["knot"], knot)
    _row(OFFSET_BTN, plan.offset_label(False), "focus-2", TIPS["offset"], knot_offset)
    _row(ORIENT_BTN, "Orient", "rotate", TIPS["orient"], knot_orient)
    _row(LOCAL_BTN, "Local ×2", "stack-2", TIPS["local"], double_local)
    _row(WORLD_BTN, "World ×2", "world", TIPS["world"], double_world)
    _row(AIM_BTN, plan.aim_label(False), "target", TIPS["aim"], aim)
    _row(SNAPSHOT_BTN, "Snapshot", "camera", TIPS["snapshot"], snapshot)
    _named_row()
    cmds.text(ORDER_LABEL, label="Rotate order", align="left")
    segments = cmds.rowLayout(numberOfColumns=3, columnAttach=[(1, "both", 1),
                                                               (2, "both", 1),
                                                               (3, "both", 1)])
    hubstyle.mark(segments, "segments", layout=True)
    cmds.iconTextRadioCollection(ORDER)
    current = order()
    for choice, label in (("object", "Object"), ("xyz", "XYZ"), ("xzy", "XZY")):
        hubstyle.mark(cmds.iconTextRadioButton(
            ORDER_SEG[choice], style="textOnly", label=label,
            height=hubstyle.height("segment", 22), select=choice == current,
            annotation=ORDER_TIPS[choice], onCommand=_order_changed(choice)), "segment")
    cmds.setParent("..")
    cmds.setParent("..")


def _parent_body():
    _row(INSIDE_BTN, "Inside", "transfer-in", TIPS["inside"], inside)
    _row(TOWORLD_BTN, "To world", "upload", TIPS["to_world"], to_world)
    _row(SWAP_BTN, "Swap", "arrows-exchange", TIPS["swap"], swap)
    _row(ACROSS_BTN, "Across", "hand-grab", TIPS["across"], across)
    _caption(PAIRS_CAPTION, "Across, pair by pair")
    _fill_row(3)
    _button(OBJECTS_BTN, plan.list_label("Objects", len(_resolved("objects"))), "plus",
            TIPS["objects"], remember_objects)
    _button(TARGETS_BTN, plan.list_label("Targets", len(_resolved("targets"))), "target",
            TIPS["targets"], remember_targets)
    _button(LISTSWAP_BTN, hubstyle.tool_label("Swap"), "arrows-exchange", TIPS["swap_lists"],
            swap_lists)
    cmds.setParent("..")
    _fill_row(3)
    _chip(ROTATE_CHIP, "Rotate", ROTATE_VAR, TIPS["rotate"])
    _chip(TRANSLATE_CHIP, "Translate", TRANSLATE_VAR, TIPS["translate"])
    _button(MULTI_BTN, "Pairs", "hand-grab", TIPS["multi"], multiple_across)
    cmds.setParent("..")


def _overlap_body():
    d = overlapplan.DEFAULTS
    _columns_row(OVERLAP_NAMES, 3)
    for label_name, label, key in ((SOFT_LABEL, "Softness", "softness"),
                                   (LAG_LABEL, "Lag, fr", "lag"),
                                   (EASE_LABEL, "Easing", "easing")):
        hubstyle.mark(cmds.text(label_name, label=label, align="left", annotation=TIPS[key]),
                      "caption")
    cmds.setParent("..")
    _columns_row(OVERLAP_FIELDS, 3)
    for field, var, default, key, minimum in (
            (SOFT_FIELD, SOFT_VAR, d.softness, "softness", 0.01),
            (LAG_FIELD, LAG_VAR, d.lag, "lag", None),
            (EASE_FIELD, EASE_VAR, d.easing, "easing", 0.0)):
        kwargs = dict(value=_number(None, var, default), precision=2, annotation=TIPS[key],
                      height=hubstyle.height("field", 20), changeCommand=_number_changed(var))
        if minimum is not None:
            kwargs["minValue"] = minimum
        cmds.floatField(field, **kwargs)
    cmds.setParent("..")
    _fill_row(2)
    _chip(HIER_CHIP, "Hierarchy", HIER_VAR, TIPS["hierarchy"], d.hierarchy)
    _chip(CYCLE_CHIP, "Cycled", CYCLE_VAR, TIPS["cycled"], d.cycled)
    cmds.setParent("..")
    _fill_row(2)
    _chip(TOTAL_CHIP, "Total lag", TOTAL_VAR, TIPS["total"], d.total)
    _chip(EDGES_CHIP, "Keep edges", EDGES_VAR, TIPS["edges"], d.edges)
    cmds.setParent("..")
    _row(OVERLAP_BTN, "Overlap", "wave-sine", TIPS["overlap"], overlap)


def _firstperson_body():
    _row(FP_BTN, "1P Setup", "camera", TIPS["fp_setup"], fp_setup)
    _caption(CAMPARENT_CAPTION, "Camera parent, motion kept")
    _fill_row(4)
    for choice in ("Main", "Root", "Chest", "World"):
        _button(CAMPARENT_BTN[choice], choice, None, TIPS["camparent"] % choice,
                _camera_parent(choice))
    cmds.setParent("..")


_BODIES = {"knots": _knots_body, "parent": _parent_body, "overlap": _overlap_body,
           "firstperson": _firstperson_body}


def _footer():
    """«Selected knots»: what acts on knots already standing (and Layer, on any object) - an
    inset block under the subsections, always shown."""
    hubstyle.mark(cmds.columnLayout(FOOTER, adjustableColumn=True,
                                    rowSpacing=hubstyle.row_spacing(4)), "inset", layout=True)
    _caption(FOOTER_CAPTION, "Selected knots")
    _fill_row(5)
    _button(ATTACH0_BTN, "0", "unlink", TIPS["attach0"], attach_0)
    _button(ATTACH1_BTN, "1", "link", TIPS["attach1"], attach_1)
    _button(BAKE_BTN, "Bake", "check", TIPS["bake"], bake)
    _button(LAYER_BTN, "Layer", "stack-2", TIPS["layer"], bake_layer)
    _button(REMOVE_BTN, hubstyle.tool_label("Remove"), "trash", TIPS["remove"], remove,
            role="danger")
    cmds.setParent("..")
    cmds.setParent("..")


def build_panel():
    """The card into the current layout (2026-10-13, mockup C): the subtitle; the subsections
    Knots, Parent and Overlap, each a head over its body; «Selected knots»; the line."""
    column = cmds.columnLayout(adjustableColumn=True, rowSpacing=hubstyle.row_spacing(6),
                               columnOffset=("both", hubstyle.pick(0, 8)))
    hubstyle.mark(cmds.text(SUBTITLE, label="", align="left"), "subtitle")
    for key, label, hint in SECTIONS:
        _head(key, label, hint)
        _body(key)
        _BODIES[key]()
        cmds.setParent("..")
    _footer()
    hubstyle.mark(cmds.text(STATUS, label="", align="left", wordWrap=True, height=36),
                  "status")
    cmds.setParent("..")
    start()
    refresh()
    return column


def _card_key():
    scope = hubcopy.current()
    return "" if scope is None else scope.tag


def start():
    """This card's own refresh on every selection change (per card: a popup copy's job dies
    with the copy and leaves the hub's)."""
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
    return bool(cmds.text(STATUS, exists=True))


def show_window():
    """The hub, on the Tools section."""
    import maya_hub
    return maya_hub.show(HUB_SECTION)
