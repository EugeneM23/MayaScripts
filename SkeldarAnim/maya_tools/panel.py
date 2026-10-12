"""The hub's Tools card (2026-10-12): OverRig's Knots and Double knot, native.

The animator: «заведем раздел тул и реализуем такие же инструменты»; the same day «все кнопочки
одинаково важные» (every button orange) and «два под раздела Knots и Double knots ... кнопочки ...
растягивать вместе с интерфейсом»: the subsection Knots - Knot, Offset (two presses: it reads
Finish while a pivot waits), Orient; the subsection Double knot - Local, World; the buttons of a
row share the card's width (the skin's `fill`); under them the knots' rotate order
[Object | XYZ | XZY] and Bake, Remove; the status line; which knots stand is the subtitle. The
presses are module functions reading the remembered rotate order, so the hotkey rows work with the
card closed. The scene half is `knots`, the pure half `knotplan`.

Spec: docs/superpowers/specs/2026-10-12-tools-knots-design.md
"""

import traceback

import maya.cmds as cmds

import maya_hubcopy as hubcopy
import maya_hubstyle as hubstyle
from maya_tools import knotplan as plan
from maya_tools import knots

HUB_SECTION = "tools"
SUBTITLE = "skeldarToolsSubtitle"
STATUS = "skeldarToolsStatus"
KNOTS_HEADING = "skeldarToolsKnotsHeading"
DOUBLE_HEADING = "skeldarToolsDoubleHeading"
ORDER_LABEL = "skeldarToolsOrderLabel"
KNOT_BTN = "skeldarToolsKnot"
OFFSET_BTN = "skeldarToolsKnotOffset"
ORIENT_BTN = "skeldarToolsKnotOrient"
LOCAL_BTN = "skeldarToolsDoubleLocal"
WORLD_BTN = "skeldarToolsDoubleWorld"
BAKE_BTN = "skeldarToolsBake"
REMOVE_BTN = "skeldarToolsRemove"
ORDER = "skeldarToolsOrder"
ORDER_SEG = dict((choice, "skeldarToolsOrder_" + choice) for choice in plan.ORDERS)
ORDER_VAR = "skeldarKnotRotateOrder"
GAP = "skeldarToolsGap"
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
    "remove": "Remove: the selected knots go and their objects play their own animation "
              "again exactly; a waiting pivot is dropped",
}
ORDER_TIPS = {
    "object": "New knots take their object's own rotate order",
    "xyz": "New knots rotate in XYZ order",
    "xzy": "New knots rotate in XZY order",
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
    """Which knots stand, and the offset button's word."""
    if not cmds.text(SUBTITLE, exists=True):
        return
    try:
        count, waiting = len(knots.knots()), len(knots.pivots())
    except Exception:                                        # noqa: BLE001
        return
    cmds.text(SUBTITLE, edit=True, label=plan.subtitle(count, waiting))
    if cmds.button(OFFSET_BTN, exists=True):
        cmds.button(OFFSET_BTN, edit=True, label=plan.offset_label(bool(waiting)))


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


def remove():
    return _press(knots.remove)


def _order_changed(choice):
    return lambda *_: set_order(choice)


# ------------------------------------------------------------------- card

def _heading(name, label):
    """A subsection's title (the hub's `heading`: bold, a hairline under it)."""
    return hubstyle.mark(cmds.text(name, label=label, align="left", font="boldLabelFont"),
                         "heading")


def _button(name, label, icon, tip, press):
    """Every button of the card alike - orange, the animator's ask («все кнопочки одинаково
    важные ... сделаем выделение для всех одинаковое»)."""
    return hubstyle.mark(cmds.button(name, label=label, annotation=tip,
                                     height=hubstyle.height("button", 28),
                                     command=lambda *_: press()), "primary", icon)


def _fill_row(columns):
    """A row whose buttons share the card's width and stretch with it (the skin's `fill`; the
    classic hub keeps their own widths)."""
    row = cmds.rowLayout(numberOfColumns=columns,
                         columnAttach=[(1, "both", 0)]
                         + [(i, "both", 4) for i in range(2, columns + 1)])
    return hubstyle.mark(row, "fill", layout=True)


def build_panel():
    """The card into the current layout: two subsections, Knots and Double knot, their buttons
    stretched over the card (2026-10-12, «два под раздела ... растягивать вместе с
    интерфейсом»); under them the knots' rotate order, Bake and Remove; the line."""
    column = cmds.columnLayout(adjustableColumn=True, rowSpacing=hubstyle.row_spacing(6),
                               columnOffset=("both", hubstyle.pick(0, 8)))
    hubstyle.mark(cmds.text(SUBTITLE, label="", align="left"), "subtitle")

    _heading(KNOTS_HEADING, "Knots")
    _fill_row(3)
    _button(KNOT_BTN, "Knot", "link", TIPS["knot"], knot)
    _button(OFFSET_BTN, plan.offset_label(False), "focus-2", TIPS["offset"], knot_offset)
    _button(ORIENT_BTN, "Orient", "rotate", TIPS["orient"], knot_orient)
    cmds.setParent("..")

    _heading(DOUBLE_HEADING, "Double knot")
    _fill_row(2)
    _button(LOCAL_BTN, "Local", "stack-2", TIPS["local"], double_local)
    _button(WORLD_BTN, "World", "stack-2", TIPS["world"], double_world)
    cmds.setParent("..")

    cmds.separator(GAP, style="none", height=hubstyle.pick(4, 6))
    cmds.rowLayout(numberOfColumns=2, adjustableColumn=2,
                   columnAttach=[(1, "both", 0), (2, "both", 6)])
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

    _fill_row(2)
    _button(BAKE_BTN, "Bake", "check", TIPS["bake"], bake)
    _button(REMOVE_BTN, "Remove", "trash", TIPS["remove"], remove)
    cmds.setParent("..")

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
    JOB[_card_key()] = cmds.scriptJob(event=["SelectionChanged", refresh], parent=STATUS)


def is_open():
    return bool(cmds.text(STATUS, exists=True))


def show_window():
    """The hub, on the Tools section."""
    import maya_hub
    return maya_hub.show(HUB_SECTION)
