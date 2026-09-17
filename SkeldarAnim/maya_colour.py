"""
Colour -- the palette on the shelf: recolour what is selected, one press.

Two Mannys in one scene are indistinguishable in the viewport (the outliner
can tell `root` from `Manny_Skeleton_root`; the eye cannot), which is why
Add Character and Add Weapon each bring their own colour. This is the other
half: change the colour of something that is ALREADY in the scene, without
opening Scene Setup.

    import sys; sys.path.append(r"C:/!!!Work/MayaScripts/SkeldarAnim")
    import maya_colour; maya_colour.show_window()

**Every bit of colour policy lives in `maya_scenesetup.colour`** -- the
palette, which colour is free, our blinn, who wears it, how a character's
meshes are found. This module is a panel over that and holds none of it. A
second copy of "which colour is free" would answer differently from Scene
Setup's swatch within a week.

**It recolours the selection; Scene Setup's swatch is the colour of the
NEXT Add.** One meaning per control, which was the animator's own ruling on
2026-09-03 after trying it the other way round -- so these two do not
overlap and neither needs to know about the other.

The target follows the convention the rest of the toolset already uses
(`animimport.choose_target_root`, `skeleton.choose_root`): the selection
first, the connected character second, a refusal third. Guessing paints
somebody else's character in silence.

Design: docs/superpowers/specs/2026-09-03-colour-on-the-shelf-design.md
"""

import collections

import maya.cmds as cmds

from maya_scenesetup import colour as colouring


#  A resolved thing to paint: what to call it, which shapes wear the
#  colour, and the key that names the material for the Hypershade.
Target = collections.namedtuple("Target", "label shapes key")


# ---------------------------------------------------------------------------
#  Policy -- pure
# ---------------------------------------------------------------------------

def leaf(path):
    """The last component of a DAG path. Pure."""
    return (path or "").split("|")[-1].split(":")[-1]


def choose_source(selection, connected):
    """What the press acts on: the selection, else the connected character.

    Pure, and the same order Import, Export and Camera Setup already use.
    Nothing at all is a refusal rather than a guess -- painting whichever
    character Maya happened to list first is exactly the silent wrong
    answer this convention exists to prevent.
    """
    chosen = [node for node in (selection or []) if node]
    if chosen:
        return chosen
    return [connected] if connected else []


def merge_targets(targets):
    """One entry per set of shapes, first label wins. Pure.

    A selection of three bones of one character resolves to that character
    three times over; painting it three times would work and would report
    nonsense.
    """
    merged = []
    seen = []
    for target in targets:
        if not target or not target.shapes:
            continue
        shapes = frozenset(target.shapes)
        if shapes in seen:
            continue
        seen.append(shapes)
        merged.append(target)
    return merged


def painted_message(targets, rgb):
    """What the status line says after a press. Pure."""
    name = colouring.colour_name(rgb)
    if not targets:
        return NOTHING_TO_PAINT
    if len(targets) == 1:
        return "%s is %s" % (targets[0].label, name)
    return "%d objects are %s" % (len(targets), name)


NOTHING_TO_PAINT = ("nothing to paint - select a character, a bone or a "
                    "mesh, or connect one in the Rig Picker")


# ---------------------------------------------------------------------------
#  Resolving the selection
# ---------------------------------------------------------------------------

def skeleton_root(path):
    """The TOPMOST joint at or above `path`, or None.

    Topmost rather than nearest: a character is painted whole, and the
    nearest joint above a hand is the hand.
    """
    node = path
    found = None
    while node:
        if cmds.nodeType(node) == "joint":
            found = node
        parents = cmds.listRelatives(node, parent=True, fullPath=True) or []
        node = parents[0] if parents else None
    return found


def weapon_marker():
    """The attribute an attached weapon carries.

    Read from `bonedrive`, which owns it, and only fallen back to as a
    literal so a Maya without Scene Setup's weapon half still paints.
    Lazy and guarded for the same reason `animimport` imports it lazily.
    """
    try:
        from maya_scenesetup import bonedrive
        return bonedrive.MARKER
    except Exception:                                         # noqa: BLE001
        return "mayaWeapon"


def is_weapon(node, marker=None):
    """Whether `node` -- or anything above it -- is a weapon we attached."""
    marker = weapon_marker() if marker is None else marker
    current = node
    while current:
        try:
            if cmds.attributeQuery(marker, node=current, exists=True):
                return True
        except Exception:                                     # noqa: BLE001
            pass
        parents = cmds.listRelatives(current, parent=True,
                                     fullPath=True) or []
        current = parents[0] if parents else None
    return False


def without_weapons(shapes):
    """`shapes` minus anything belonging to an attached weapon.

    A character's meshes are found partly by a DAG walk, deliberately, so
    that unskinned geometry parented in by hand counts as part of the
    figure -- and a sword in the hand is caught by exactly that walk.

    But a weapon has its OWN colour by design (Add Weapon gives it one,
    and telling the sword from the hand holding it is half of why colours
    exist here). Worse, `colour.paint` reuses whatever material of ours is
    already on the shapes: with the sword in the character's list the two
    end up sharing one material, and then painting the SWORD repaints the
    character. Measured live 2026-09-03, and it is the whole reason this
    filter exists.

    Only MARKED weapons are dropped. A prop the animator parented in by
    hand carries no marker, is part of the figure, and travels with it.
    """
    marker = weapon_marker()
    kept = []
    for shape in shapes or []:
        parents = cmds.listRelatives(shape, parent=True,
                                     fullPath=True) or []
        owner = parents[0] if parents else shape
        if not is_weapon(owner, marker):
            kept.append(shape)
    return kept


def connected_root():
    """The character the Rig Picker is bound to, or None.

    Lazy and guarded, like `animimport.picker_root`: this module is plain
    `cmds`, and the picker drags Qt in. A Maya where that import fails
    still paints whatever is selected.
    """
    try:
        from maya_scenesetup import skeleton
        return skeleton.current_root()
    except Exception:                                         # noqa: BLE001
        return None


def target_for(node):
    """What painting `node` should mean, or None when it means nothing.

    A JOINT means the character it belongs to -- click any bone, recolour
    the figure. Anything else that holds geometry means that geometry,
    which is how the weapon tool already works: the sword IS the mesh, and
    an animator clicking a sword wants the sword rather than the character
    holding it.

    Asking about the joint FIRST is what makes those two rules disjoint.
    `hand_r` has the sword mesh parented under it, so a mesh-first rule
    would resolve a hand-bone click to the sword.
    """
    if not node or not cmds.objExists(node):
        return None
    long_name = (cmds.ls(node, long=True) or [node])[0]
    if cmds.nodeType(long_name) == "joint":
        root = skeleton_root(long_name)
        if root:
            return Target(leaf(root),
                          without_weapons(colouring.character_meshes(root)),
                          leaf(root))
        return None
    shapes = colouring.mesh_shapes([long_name])
    if shapes:
        return Target(leaf(long_name), shapes, leaf(long_name))
    #  A control curve, a locator, an empty group: it names no geometry of
    #  its own and no character. The caller falls back to the connect.
    return None


def targets(selection=None, connected=None):
    """Everything the press should paint, resolved and de-duplicated."""
    selection = (cmds.ls(selection=True, long=True) or []
                 if selection is None else selection)
    resolved = merge_targets([target_for(node) for node in selection])
    if resolved:
        return resolved
    #  Nothing in the selection named anything paintable -- a rig control,
    #  or an empty selection. Fall back to the connected character.
    root = connected_root() if connected is None else connected
    return merge_targets([target_for(root)]) if root else []


# ---------------------------------------------------------------------------
#  The press
# ---------------------------------------------------------------------------

def paint(rgb, selection=None, connected=None, undoable=True):
    """Put `rgb` on whatever the selection names. Returns the message."""
    found = targets(selection, connected)
    if not found:
        return NOTHING_TO_PAINT
    if undoable:
        cmds.undoInfo(openChunk=True, chunkName="Colour")
    try:
        for target in found:
            colouring.paint(target.shapes, rgb, target.key)
        return painted_message(found, rgb)
    finally:
        if undoable:
            cmds.undoInfo(closeChunk=True)


def paint_free(selection=None, connected=None):
    """Paint with the first colour nothing in the scene is wearing.

    The same question Add Character asks, asked through the same function
    -- so a character recoloured here and one added a moment later cannot
    both come out red.
    """
    return paint(colouring.free_colour().rgb, selection, connected)


def scene_colours():
    """What is worn in this scene right now, as (name, rgb) pairs.

    For the panel's "taken" line: with eight colours and several
    characters, knowing which are gone is most of the choice.
    """
    return [(colouring.colour_name(rgb), rgb)
            for rgb in colouring.used_colours()]


def taken_message(pairs):
    """The taken line. Pure."""
    if not pairs:
        return "nothing painted yet"
    names = []
    for name, _rgb in pairs:
        if name not in names:
            names.append(name)
    return "taken: " + ", ".join(names)


# ---------------------------------------------------------------------------
#  UI
# ---------------------------------------------------------------------------

HUB_SECTION = "colour"          # our section of the SkeldarAnim hub
WIDTH = 268
ROW_SPACING = 4                 # the column's gap between controls
STATUS_WIDTH = 40
CUSTOM = "skeldarColourCustom"
TAKEN = "skeldarColourTaken"
STATUS = "skeldarColourStatus"

#  Four across, two rows: eight palette entries, and a label under a
#  coloured button has to stay readable at 60 px.
COLUMNS = 4


def _status(text):
    """Fixed width, so a long message cannot stretch the window."""
    short = text if len(text) <= STATUS_WIDTH else text[:STATUS_WIDTH - 1] + "…"
    if cmds.control(STATUS, exists=True):
        cmds.text(STATUS, edit=True, label=short)
    cmds.headsUpMessage(text, time=2.5)
    return text


def _run(fn, *args):
    """Failures belong on the status line, not in the Script Editor."""
    try:
        return fn(*args)
    except Exception as exc:                                  # noqa: BLE001
        _status("%s: %s" % (type(exc).__name__, exc))
        raise


def refresh(*_args):
    """Re-read the scene's taken colours. Writes no colour control.

    The one bug this shape can have is a refresh that discards the colour
    the animator dialled a second ago, so this touches the taken line and
    nothing else -- the lesson `maya_scenesetup.window` paid for with its
    swatch.
    """
    if not cmds.control(TAKEN, exists=True):
        return ""
    message = taken_message(scene_colours())
    cmds.text(TAKEN, edit=True, label=message)
    return message


def _press(rgb):
    def go(*_args):
        _run(lambda: _status(paint(rgb)))
        refresh()
    return go


def _press_custom(*_args):
    def go():
        rgb = cmds.colorSliderGrp(CUSTOM, query=True, rgbValue=True)
        return _status(paint(tuple(rgb)))
    _run(go)
    refresh()


def _press_free(*_args):
    _run(lambda: _status(paint_free()))
    refresh()


def is_open():
    """True while our section is built in the hub (read by maya_hotkeys)."""
    return bool(cmds.control(STATUS, exists=True))


def show_window():
    """Open the SkeldarAnim hub on the Colour section (see `maya_hub`)."""
    import maya_hub
    return maya_hub.show(HUB_SECTION)


def build_panel():
    """A grid of eight colours, a custom swatch, and what is taken -
    built into whatever layout is current (the hub's section)."""
    column = cmds.columnLayout(adjustableColumn=True, rowSpacing=ROW_SPACING,
                               columnOffset=("both", 8))

    cmds.text(label="paints the selection, else the connected character",
              font="smallObliqueLabelFont", align="center",
              width=WIDTH - 16)
    cmds.separator(height=7, style="in", width=WIDTH - 16)

    cell = (WIDTH - 16) // COLUMNS
    for start in range(0, len(colouring.PALETTE), COLUMNS):
        row = colouring.PALETTE[start:start + COLUMNS]
        cmds.rowLayout(numberOfColumns=len(row),
                       columnWidth=[(i + 1, cell)
                                    for i in range(len(row))])
        for entry in row:
            cmds.button(label=entry.name, width=cell - 3, height=30,
                        backgroundColor=entry.rgb,
                        annotation="paint the selection " + entry.name,
                        command=_press(entry.rgb))
        cmds.setParent("..")

    cmds.separator(height=7, style="in", width=WIDTH - 16)

    cmds.rowLayout(numberOfColumns=2, columnWidth2=(158, 92),
                   columnAlign2=("left", "left"))
    cmds.colorSliderGrp(CUSTOM, label="", rgbValue=colouring.PALETTE[0].rgb,
                        columnWidth3=(1, 44, 105), width=155,
                        annotation="any colour off the palette")
    cmds.button(label="Paint", width=88, height=24,
                annotation="paint the selection with the swatch's colour",
                command=_press_custom)
    cmds.setParent("..")

    cmds.button(label="Next free colour", width=WIDTH - 16, height=26,
                backgroundColor=(0.45, 0.60, 0.70),
                annotation="the first colour nothing in the scene wears - "
                           "the same question Add Character asks",
                command=_press_free)

    cmds.separator(height=7, style="in", width=WIDTH - 16)
    cmds.text(TAKEN, label="", align="center", width=WIDTH - 16,
              font="smallObliqueLabelFont")
    cmds.text(STATUS, label="select something and pick a colour",
              align="center", width=WIDTH - 16,
              font="smallFixedWidthFont")

    cmds.setParent("..")
    refresh()
    return column


if __name__ == "__main__":
    show_window()
