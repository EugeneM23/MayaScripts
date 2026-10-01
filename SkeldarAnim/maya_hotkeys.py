"""The temporary hotkey map: one shelf button that switches Maya's set.

Press `Hotkeys` on the SkeldarAnim shelf and Maya switches to a hotkey set
of our name; press it again and the animator's own set comes back. The map's
CONTENTS are theirs to lay out, in Maya's own Hotkey Editor -- what this
module adds is the switch, plus a command list worth binding: every button
of our panels, and -- while `skeldar_features.OVERRIG_HOTKEYS` is on -- every
one-press procedure OverRig's author published in `function_for_hotkeys.TXT`.

Design: docs/superpowers/specs/2026-09-02-hotkey-map-design.md

`maya.cmds` and `maya.mel` only at module level. Qt lives below the four
`_*_module()` seams: `picker_window` imports PySide6 when it loads, and four
of the five shelf buttons have to keep working on a Maya that has PySide2.
The seams are also where the tests hand in a fake panel.
"""

import importlib
import os
import sys
import traceback
from functools import partial

import maya.cmds as cmds
import maya.mel as mel

SET = "SkeldarAnim"
SHELF = "SkeldarAnim"
BUTTON_LABEL = "Hotkeys"
PREVIOUS_VAR = "skeldarAnimPreviousHotkeySet"
FALLBACK_SET = "Maya_Default"
PREFIX = "skeldarAnim"
EDITOR_COMMAND = "HotkeyPreferencesWindow"
ON_COLOUR = (0.27, 0.38, 0.48)
HUB_SECTION = "hotkeys"                 # our section of the SkeldarAnim hub
PANEL_BUTTON = "skeldarHotkeysToggle"   # the hub's toggle, painted like the shelf's
PANEL_NOTE = ("One press switches Maya to the SkeldarAnim hotkey set (a copy "
              "of yours, with our commands registered); the next puts your "
              "own set back. Assign keys in Maya's Hotkey Editor.")

# The time-based curve types, and the whole list of them. Everything else
# `ls(type="animCurve")` answers is a driven key -- see `time_curves`.
TIME_CURVES = ("animCurveTL", "animCurveTA", "animCurveTT", "animCurveTU")

# Keys bound in OUR set when it is created (2026-09-02, the animator's ask:
# «alt+a - кадр назад, alt+s - кадр вперед. alt+4 - добавить inbetween кадр
# между alt+5 убрать»). All four were taken by a Maya default -- alt+a
# CycleDisplayMode, alt+s HIKSetFullBodyKey, alt+4 ImagePlaneOption, alt+5
# WireframeOnShaded, measured -- and overwriting them was the animator's own
# call («если возникают конфликты то перезапиши»). Only inside our set: in
# their own set those four keep doing what Maya says.
# alt+g and alt+o joined on 2026-09-03 («чтобы alt+g не просто открывал
# граф эдитор а делал toggle... и тоже самое для аутлайнера на alt+o»).
# alt+g held `GraphEditorNameCommand` -- Maya's plain opener -- and alt+o
# was free.
# The inbetweens moved off alt+4/alt+5 on 2026-09-03 («давай переделаем
# добавление инбитвинов на alt + + и alt + -»). BOTH spellings of each key
# are bound to the same command, because Maya keeps `+` and `=` as separate
# bindings -- measured: binding alt++ leaves alt+= untouched -- and which
# one a physical alt+shift+= press fires cannot be measured over the
# command port. Both bound, so the key works whichever way a hand reaches
# it. All four were unbound in the animator's set, so nothing was taken.
# alt+c joined on 2026-09-05 with the Curve Overlay, left with it on
# 2026-09-08, and came back on 2026-09-30 for the Graph Overlay - the same
# idea (the graph over the viewport, see-through) done with Maya's own
# Graph Editor. A set still holding the Curve Overlay's toggle there is
# simply rebound; nobody else's binding was on it.
DEFAULT_KEYS = (
    ("a", {"altModifier": True}, "time.prev"),
    ("s", {"altModifier": True}, "time.next"),
    ("+", {"altModifier": True}, "time.insert"),
    ("=", {"altModifier": True}, "time.insert"),
    ("-", {"altModifier": True}, "time.remove"),
    ("_", {"altModifier": True}, "time.remove"),
    ("g", {"altModifier": True}, "editor.graph"),
    ("o", {"altModifier": True}, "editor.outliner"),
    ("c", {"altModifier": True}, "graph.overlay"),
)

# Keys DEFAULT_KEYS used to hold and does not any more. They are given back
# on the version bump -- unbound, and only while they still hold the very
# command we put there, so a key the animator has since re-assigned in the
# editor is left alone. A key must never be in both tables. The row key of
# a released binding need not be in the table any more (`window.curveview`
# left with the Curve Overlay): `name_command` is a pure spelling.
RELEASED_KEYS = (
    ("4", {"altModifier": True}, "time.insert"),
    ("5", {"altModifier": True}, "time.remove"),
)

# Bumped when either table changes, which re-installs them once -- which is
# how alt+g and alt+o reached a set that already existed, and how the
# number keys are handed back -- and alt+c, given back on 2026-09-08 (5)
# and taken again for the Graph Overlay on 2026-09-30 (6).
DEFAULT_KEYS_VERSION = 6
DEFAULT_KEYS_VAR = "skeldarAnimDefaultKeys"


# --------------------------------------------------------------- reporting

def _report(message):
    """Say it where a keypress can be seen, and hand the text back.

    A hotkey has no status bar of its own. An exception out of a
    runTimeCommand goes to the Script Editor and nowhere else, which is
    exactly how "I press it and nothing happens" happened before (trap 20).
    """
    cmds.inViewMessage(assistMessage=message, position="midCenterTop",
                       fade=True)
    return message


# ------------------------------------------------------------------- seams

def _picker_module():
    """Lazy, and the seam the tests replace. Qt lives below this line."""
    from maya_overrig import picker_window
    return picker_window


def _scene_module():
    from maya_scenesetup import window
    return window


def _overshoot_module():
    import maya_overshoot
    return maya_overshoot


def _overrig_module():
    """The MEL binding. cmds and mel only -- no Qt below here either."""
    from maya_overrig import overrig
    return overrig


# ----------------------------------------------------------------- actions

def _show(module_name, func):
    """Open a tool's window; its own module knows how."""
    module = importlib.import_module(module_name)
    return getattr(module, func)()


def _picker(method, *args):
    """Press a Rig Picker button.

    With the panel closed there is nothing to press: the picker's binding is
    the character the animator can SEE, and re-deriving one to act on is how
    two characters got rigged onto each other. So we open it and say so.
    """
    module = _picker_module()
    window = module.live_window()
    if window is None:
        module.show_picker()
        return _report(
            "Rig Picker opened - connect a character and press again")
    return getattr(window, method)(*args)


def _scene(func, *args, **kwargs):
    """Press a Scene Setup button. Its callbacks read their own controls.

    `section="weapons"` opens the hub on the Weapons section when nothing is
    built yet; the default is Characters (the two sections since 2026-09-17).
    """
    section = kwargs.pop("section", "characters")
    module = _scene_module()
    if not module.is_open():
        if section == "weapons":
            module.show_weapons()
            return _report("Weapons opened - press again")
        module.show_window()
        return _report("Animation Setup opened - press again")
    return getattr(module, func)(*args)


def _connections_module():
    from maya_scenesetup import connections
    return connections


def _connections(func):
    """Press a Connections button; with the hub closed, open it and say so."""
    module = _connections_module()
    if not module.is_open():
        module.show_window()
        return _report("Connections opened - press again")
    return getattr(module, func)()


def _retarget_module():
    """Lazy: the Retarget shelf button's module."""
    import maya_rig_retarget
    return maya_rig_retarget


def _retarget(func):
    """Press the Retarget shelf button; it reports in the viewport itself."""
    return getattr(_retarget_module(), func)()


def _overshoot(shape):
    """Apply one overshoot preset. Strength and Frames come from the panel."""
    module = _overshoot_module()
    if not cmds.window(module.WINDOW, exists=True):
        module.show_overshoot_ui()
        return _report("Overshoot opened - press again")
    return module.apply_overshoot(shape)


def step_frame(delta):
    """One frame back or forward."""
    cmds.currentTime(cmds.currentTime(query=True) + delta, edit=True)


def insert_plan(now, last):
    """(start, end, +1) for the keys that make room after `now`.

    Everything strictly after the current frame moves one frame later, so
    the frame right after the pose the animator is standing on comes free.
    None when there is nothing after `now` to move -- inserting room at the
    end of a clip is what the timeline is already for.
    """
    if last is None or last <= now:
        return None
    return (now + 1.0, last, 1.0)


def remove_plan(now, last):
    """(frame to clear, range to pull back or None, -1) -- insert's inverse.

    The frame after `now` goes, keys and all, and everything past it comes
    back one frame. Press insert then remove and the timeline is exactly
    where it started, which is the whole reason the pair is defined this
    way round.
    """
    if last is None or last <= now:
        return None
    shift = (now + 2.0, last) if last >= now + 2.0 else None
    return (now + 1.0, shift, -1.0)


def time_curves():
    """The curves to shift: the selection's, else every one in the scene.

    Two things this is careful about. `cmds.ls(type="animCurve")` also
    answers the DRIVEN-key curves -- `animCurveUU` and friends, whose x
    axis is a driver's VALUE and not time -- and shifting one of those
    moves a set-driven-key relationship instead of the animation, silently.
    Measured 2026-09-02: the animator's open scene holds animCurveUU right
    now, so the filter is not theoretical. And a selection narrows it,
    because "insert a frame" means the shot when nothing is picked and that
    limb when something is.
    """
    selected = cmds.ls(selection=True, long=True) or []
    if selected:
        curves = cmds.keyframe(selected, query=True, name=True) or []
    else:
        curves = cmds.ls(type=TIME_CURVES) or []
    return [c for c in curves if cmds.objectType(c) in TIME_CURVES]


def insert_frame():
    """Make room for an inbetween after the current frame."""
    curves = time_curves()
    if not curves:
        return _report("Insert frame: no animation to move")
    now = cmds.currentTime(query=True)
    plan = insert_plan(now, cmds.findKeyframe(curves, which="last"))
    if plan is None:
        return _report("Insert frame: no keys after {0:g}".format(now))
    start, end, delta = plan
    cmds.keyframe(curves, edit=True, relative=True, timeChange=delta,
                  time=(start, end))
    return _report("Frame {0:g} is free - {1} curve(s) moved".format(
        start, len(curves)))


def remove_frame():
    """Take the frame after the current one back out, keys and all.

    The one undo chunk in this module, and it earns it: clearing the frame
    and pulling the rest back are two commands, and a Ctrl+Z that undid
    half of that would leave the timeline in a state nobody asked for.
    """
    curves = time_curves()
    if not curves:
        return _report("Remove frame: no animation to move")
    now = cmds.currentTime(query=True)
    plan = remove_plan(now, cmds.findKeyframe(curves, which="last"))
    if plan is None:
        return _report("Remove frame: no keys after {0:g}".format(now))
    clear, shift, delta = plan
    cmds.undoInfo(openChunk=True)
    try:
        cut = cmds.cutKey(curves, time=(clear, clear), clear=True) or 0
        if shift:
            cmds.keyframe(curves, edit=True, relative=True,
                          timeChange=delta, time=shift)
    finally:
        cmds.undoInfo(closeChunk=True)
    return _report("Frame {0:g} removed ({1} key(s)) - {2} curve(s) "
                   "moved".format(clear, cut, len(curves)))


def _maya_mel(script):
    """Run one of MAYA's own MEL commands.

    Deliberately not `_mel`, which sources OverRig first: pressing alt+g
    to see the Graph Editor has no business loading a rigging toolset.
    """
    return mel.eval(script if script.endswith(";") else script + ";")


def toggle_workspace_editor(label, control, command):
    """Close the editor if it is up, open it with Maya's own command if not.

    The Graph Editor and its kind live in a workspaceControl of their own
    (measured: `GraphEditor` makes `graphEditor1Window`, and `close` on
    that control removes it entirely, after which the same command opens it
    again). Closing is the only lever we pull ourselves; opening goes
    through Maya's command, which also RAISES a control that exists but
    sits hidden behind a tab -- and that is what an animator pressing the
    key wants in that case, not a close they cannot see.
    """
    if cmds.workspaceControl(control, exists=True) \
            and cmds.workspaceControl(control, query=True, visible=True):
        cmds.workspaceControl(control, edit=True, close=True)
        return _report(label + " closed")
    _maya_mel(command)
    return _report(label + " open")


def _outliner_shown():
    """Whether any Outliner panel is visible in the current layout."""
    visible = set(cmds.getPanel(visiblePanels=True) or [])
    return any(panel in visible
               for panel in (cmds.getPanel(type="outlinerPanel") or []))


def toggle_outliner():
    """Maya's own ToggleOutliner, with a word about which way it went.

    The Outliner is NOT a workspaceControl of its own: in a normal layout
    it is a PANEL of that layout, so `outlinerPanel1Window` never exists
    and there is nothing of ours to close. Measured 2026-09-03: one
    `ToggleOutliner` takes the visible panels from
    `[modelPanel4, outlinerPanel1]` to `[modelPanel4]` and the next brings
    it back -- Maya already has this toggle, so we only report it. A layout
    holding no Outliner at all is said so rather than reported as done.
    """
    before = _outliner_shown()
    _maya_mel("ToggleOutliner")
    after = _outliner_shown()
    if before == after:
        return _report("Outliner unchanged - none in this layout")
    return _report("Outliner " + ("shown" if after else "hidden"))


def _mel(script):
    """Run one OverRig procedure, sourcing the toolset first.

    Without the source, a fresh Maya with the OverRig shelf button unpressed
    answers a keypress with `Cannot find procedure` in the Script Editor
    (trap 20 from the hotkey side). Deliberately NOT gated on the time
    slider's highlight the way our own MEL entry points are (trap 36): half
    of these procedures are ABOUT the highlighted range.
    """
    overrig = _overrig_module()
    if not overrig.ensure_loaded():
        return _report(overrig.NOT_LOADED_MESSAGE)
    return mel.eval(script)


# ------------------------------------------------------------ registration

def install_dir():
    """The folder this module was installed into.

    The path a command's body has to put on `sys.path`: a key pressed
    before any shelf button in a fresh Maya has nothing of ours there. Read
    from our own location, so the installed copy knows where it lives and a
    move is picked up by the next registration.
    """
    return os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")


def command_name(key):
    """`picker.build` -> `skeldarAnimPickerBuild`.

    Maya wants an identifier; the readable name is the row's `label`, which
    is what the Hotkey Editor shows.
    """
    parts = [chunk[:1].upper() + chunk[1:]
             for chunk in key.replace(".", "_").split("_") if chunk]
    return PREFIX + "".join(parts)


def command_body(key, dest=None):
    """The runTimeCommand's body: bootstrap, then dispatch through us.

    Deliberately a one-liner into the table rather than real logic. Maya
    SAVES a user runTimeCommand into userRunTimeCommands.mel (measured:
    `default` comes back False), so a body is a copy that outlives the
    installed plugin -- and this one keeps resolving through whatever table
    is current, or reports an unknown key instead of raising.
    """
    dest = install_dir() if dest is None \
        else dest.replace("\\", "/").rstrip("/")
    return ("import sys\n"
            "_p = \"{0}\"\n"
            "if _p not in sys.path:\n"
            "    sys.path.insert(0, _p)\n"
            "import maya_hotkeys\n"
            "maya_hotkeys.run(\"{1}\")\n").format(dest, key)


def register(dest=None):
    """Create or refresh every command. Returns (created, updated).

    Called from `toggle()` in both directions, which is the only moment
    registration happens: a press that turns the map OFF refreshes the
    commands too, so an updated plugin's rows -- and the path baked inside
    them -- come into step with what is on disk.
    """
    created = updated = 0
    for key, category, label, annotation, _action in COMMANDS:
        name = command_name(key)
        body = command_body(key, dest)
        if cmds.runTimeCommand(name, query=True, exists=True):
            cmds.runTimeCommand(name, edit=True, command=body,
                                category=category, label=label,
                                annotation=annotation,
                                commandLanguage="python")
            updated += 1
        else:
            cmds.runTimeCommand(name, command=body, category=category,
                                label=label, annotation=annotation,
                                commandLanguage="python", default=False)
            created += 1
    return created, updated


# ------------------------------------------------------------ the hotkey set

def current_set():
    """Maya's active hotkey set."""
    return cmds.hotkeySet(query=True, current=True)


def is_active():
    """True when the map is on.

    Asked at every press and never cached: the animator can switch sets by
    hand in the Hotkey Editor between two presses, and a stored boolean
    would then lie -- the same reason `picker_window._resolution`
    re-asserts its binding on every sync.
    """
    return current_set() == SET


def previous_set():
    """The set to come back to.

    Ours is never an answer: it would make the way out lead back in. A
    remembered set that has since been deleted is not one either, so both
    fall back to `Maya_Default`, which always exists and cannot be deleted.
    """
    remembered = ""
    if cmds.optionVar(exists=PREVIOUS_VAR):
        remembered = cmds.optionVar(query=PREVIOUS_VAR) or ""
    if remembered and remembered != SET \
            and cmds.hotkeySet(remembered, query=True, exists=True):
        return remembered
    return FALLBACK_SET


def open_editor():
    """Maya's own Hotkey Editor -- the editor for this map."""
    mel.eval(EDITOR_COMMAND + ";")


def name_command(key):
    """The nameCommand wrapping a row's runTimeCommand.

    A hotkey binds a nameCommand, never a runTimeCommand -- the Hotkey
    Editor makes one when the animator drags a command onto a key, and
    with no editor in the loop we make it ourselves.
    """
    return command_name(key) + "Name"


def bind_defaults():
    """Bind DEFAULT_KEYS in whatever set is CURRENT. What it displaced.

    Called from `activate()` while our set is current -- never against the
    animator's own set, which is why it is called after the switch and not
    before. Returns [(key, the nameCommand that was there)] so the press
    can say what moved instead of taking a key silently.
    """
    displaced = []
    for key, modifiers, row_key in DEFAULT_KEYS:
        found = row(row_key)
        if found is None:                      # a table edit went wrong
            continue
        # `cmds.hotkey` reverses itself between reading and writing, and
        # getting it the wrong way round raises rather than misbehaving:
        # READING takes the key POSITIONALLY (`keyShortcut=` under query
        # answers "must be passed a boolean argument"), WRITING takes it as
        # the `keyShortcut` FLAG ("Please specify a key" otherwise). Both
        # measured live 2026-09-02; the second cost a live run.
        held = cmds.hotkey(key, query=True, name=True, **modifiers) or ""
        wrapper = name_command(row_key)
        if held and held != wrapper:
            displaced.append((_key_label(key, modifiers), held))
        cmds.nameCommand(wrapper, annotation=found[3],
                         command=command_name(row_key), sourceType="mel")
        cmds.hotkey(keyShortcut=key, name=wrapper, **modifiers)
    return displaced


def release_keys():
    """Give back the keys we no longer use. Which ones were freed.

    Only a key that still holds the command WE put there is unbound: one
    the animator has since re-assigned in the editor is theirs, and taking
    it a second time to "clean up" would be the rudest thing this module
    could do.
    """
    freed = []
    for key, modifiers, row_key in RELEASED_KEYS:
        wrapper = name_command(row_key)
        held = cmds.hotkey(key, query=True, name=True, **modifiers) or ""
        if held == wrapper:
            cmds.hotkey(keyShortcut=key, name="", **modifiers)
            freed.append(_key_label(key, modifiers))
    return freed


def _key_label(key, modifiers):
    """`alt+a`, for a message the animator can read."""
    parts = [name[:-8] for name in ("ctrlModifier", "altModifier",
                                    "shiftModifier") if modifiers.get(name)]
    return "+".join(parts + [key])


def defaults_installed():
    """Which version of DEFAULT_KEYS this user has already been given."""
    if not cmds.optionVar(exists=DEFAULT_KEYS_VAR):
        return 0
    try:
        return int(cmds.optionVar(query=DEFAULT_KEYS_VAR) or 0)
    except (TypeError, ValueError):
        return 0


def shelf_button(shelf=SHELF, label=BUTTON_LABEL):
    """Our shelf button, or None.

    A shelf button's command runs with no widget context, so there is no
    `self` to edit -- the button is found by walking the shelf's children
    and matching the label we gave it. Not finding it is a normal outcome
    (the module called from the Script Editor, the shelf renamed): the set
    still switches and only the paint is skipped.
    """
    if not cmds.shelfLayout(shelf, exists=True):
        return None
    for child in cmds.shelfLayout(shelf, query=True, childArray=True) or []:
        if not cmds.control(child, query=True, exists=True):
            continue
        if cmds.shelfButton(child, query=True, label=True) == label:
            return child
    return None


def paint(active):
    """Light the button while the map is on. True when one was painted.

    Maya shows the active hotkey set nowhere but the Hotkey Editor's own
    dropdown, so a toggle with no feedback is a toggle you lose track of.
    Both buttons are ours - the shelf's and the hub section's - and either
    may be absent (the module called from the Script Editor, the hub
    closed); painting whichever is there is the normal outcome.
    """
    painted = False
    button = shelf_button()
    if button:
        cmds.shelfButton(button, edit=True, enableBackground=bool(active),
                         backgroundColor=ON_COLOUR)
        painted = True
    if cmds.control(PANEL_BUTTON, exists=True):
        cmds.button(PANEL_BUTTON, edit=True, label=panel_label(active),
                    enableBackground=bool(active), backgroundColor=ON_COLOUR)
        painted = True
    #  The skinned hub's header switch (2026-09-28). Only a hub already
    #  imported is asked: a paint is no reason to import one.
    hub = sys.modules.get("maya_hub")
    if hub is not None:
        try:
            if hub.is_skinned():
                hub.paint_hotkeys(active)
                painted = True
        except Exception:                                    # noqa: BLE001
            traceback.print_exc()
    return painted


def panel_label(active):
    """What the hub's toggle reads. Pure."""
    return "Hotkey map: ON" if active else "Hotkey map: OFF"


def is_open():
    """True while our section is built in the hub."""
    return bool(cmds.control(PANEL_BUTTON, exists=True))


def show_window():
    """Open the SkeldarAnim hub on the Hotkeys section (see `maya_hub`)."""
    import maya_hub
    return maya_hub.show(HUB_SECTION)


def build_panel():
    """The hub section: the toggle, lit while the map is on, and a way
    into Maya's own Hotkey Editor (2026-09-17)."""
    import maya_hubstyle as hubstyle   # stdlib; the section is classic-only
    column = cmds.columnLayout(adjustableColumn=True, rowSpacing=6,
                               columnOffset=("both", 8))
    hubstyle.mark(cmds.text(label=PANEL_NOTE, align="left", wordWrap=True,
                            height=54), "note")
    active = is_active()
    hubstyle.mark(cmds.button(
        PANEL_BUTTON, label=panel_label(active), height=30,
        enableBackground=active, backgroundColor=ON_COLOUR,
        annotation="Switch between the SkeldarAnim hotkey set and your own",
        command=lambda *_a: toggle()), "secondary", "keyboard")
    hubstyle.mark(cmds.button(
        label="Hotkey Editor...", height=24,
        annotation="Maya's Hotkey Editor: assign keys to the SkeldarAnim "
                   "commands",
        command=lambda *_a: _maya_mel("HotkeyPreferencesWindow")),
        "secondary")
    cmds.setParent("..")
    return column


def activate():
    """Switch to our set, creating it if this is its first press.

    The set is created ONCE, as a copy of whatever is active at that
    moment, and never rebuilt: rebuilding it on every press would keep the
    copy in step with the base set and destroy every key the animator
    assigned in it.
    """
    base = current_set()
    fresh = not cmds.hotkeySet(SET, query=True, exists=True)
    if base != SET:
        cmds.optionVar(stringValue=(PREVIOUS_VAR, base))
    if fresh:
        cmds.hotkeySet(SET, source=base, current=True)
    else:
        cmds.hotkeySet(SET, edit=True, current=True)
    paint(True)

    # The starter keys go in AFTER the switch, so they land in our set and
    # never in the animator's. A fresh set always gets them; an existing
    # one gets them once per version, because "only on creation" would
    # never reach a set the animator had already made -- theirs existed
    # before these keys did. After that their edits in the editor stand.
    note = ""
    if fresh or defaults_installed() < DEFAULT_KEYS_VERSION:
        freed = release_keys()
        displaced = bind_defaults()
        cmds.optionVar(intValue=(DEFAULT_KEYS_VAR, DEFAULT_KEYS_VERSION))
        note = " - {0} key(s) bound".format(len(DEFAULT_KEYS))
        if displaced:
            note += ", took " + ", ".join(
                "{0} from {1}".format(key, held) for key, held in displaced)
        if freed:
            note += ", gave back " + ", ".join(freed)

    if fresh:
        open_editor()
        return _report("Hotkeys: {0} created from {1}{2} - assign the "
                       "rest".format(SET, base, note))
    return _report("Hotkeys: " + SET + note)


def deactivate():
    """Put the animator's own set back."""
    back = previous_set()
    cmds.hotkeySet(back, edit=True, current=True)
    paint(False)
    return _report("Hotkeys: " + back)


def toggle():
    """The shelf button. Registers first, in both directions."""
    register()
    return deactivate() if is_active() else activate()


# --------------------------------------------------------------- the table

def row(key):
    """The row for `key`, or None."""
    return _INDEX.get(key)


def run(key):
    """Run one command. The body of every runTimeCommand we register.

    Every failure is reported where the animator is looking and the full
    traceback still goes to the Script Editor -- the panels' own `_run`,
    for a button that has no panel.

    Deliberately NO undo chunk of our own: `rebuild` already builds in one
    undo step and OverRig's procedures manage theirs, so wrapping a chunk
    in another chunk buys nothing and nests. A hotkey inherits whatever its
    target does, which is what the shelf buttons already do.
    """
    found = row(key)
    if found is None:
        return _report("Unknown hotkey command '{0}' - re-drag the "
                       "installer".format(key))
    label, action = found[2], found[4]
    try:
        return action()
    except Exception as error:  # noqa: BLE001 - the message is the report
        traceback.print_exc()
        return _report("{0} failed: {1}".format(label, error))


_OURS = (
    # key, category leaf, label, annotation, action
    ("window.picker", "Windows", "Rig Picker",
     "Open the Rig Picker panel",
     partial(_show, "maya_overrig", "show_picker")),
    ("window.uebridge", "Windows", "UE Bridge",
     "Open the UE animation bridge",
     partial(_show, "maya_uebridge", "show_window")),
    ("window.scenesetup", "Windows", "Animation Setup",
     "Open the Animation Setup section: the rig or a skeleton, and the UE Bridge",
     partial(_show, "maya_scenesetup", "show_window")),
    ("window.weapons", "Windows", "Weapons",
     "Open the Weapons section: a weapon in the hand, the grip",
     partial(_show, "maya_scenesetup", "show_weapons")),
    ("window.overshoot", "Windows", "Overshoot",
     "Open the Overshoot panel",
     partial(_show, "maya_overshoot", "show_overshoot_ui")),
    ("window.hotkeys", "Windows", "Hotkey map on/off",
     "Switch between the SkeldarAnim hotkey set and your own", toggle),
    ("window.hub", "Windows", "SkeldarAnim window",
     "Open the SkeldarAnim panel: every tool a section, dock it anywhere",
     partial(_show, "maya_hub", "show")),

    ("time.prev", "Timeline", "Frame back", "One frame back",
     partial(step_frame, -1.0)),
    ("time.next", "Timeline", "Frame forward", "One frame forward",
     partial(step_frame, 1.0)),
    ("time.insert", "Timeline", "Insert frame",
     "Make room for an inbetween after the current frame - the selection's "
     "curves, or the whole scene when nothing is selected",
     insert_frame),
    ("time.remove", "Timeline", "Remove frame",
     "Take the frame after the current one out, keys and all - the exact "
     "inverse of Insert frame",
     remove_frame),

    ("editor.graph", "Editors", "Toggle Graph Editor",
     "Open the Graph Editor, or close it if it is already up",
     partial(toggle_workspace_editor, "Graph Editor", "graphEditor1Window",
             "GraphEditor")),
    ("editor.outliner", "Editors", "Toggle Outliner",
     "Show or hide the Outliner in this layout", toggle_outliner),
    ("graph.overlay", "Editors", "Graph Overlay",
     "Maya's Graph Editor over the viewport with its background taken out; "
     "alt+mouse is the camera. The same key leaves it",
     partial(_show, "maya_graphoverlay", "toggle")),

    ("picker.connect", "Rig Picker", "Connect",
     "Bind the picker to the selected character",
     partial(_picker, "connect_to_selection")),
    ("picker.build", "Rig Picker", "Build",
     "Build the hybrid rig on the connected character",
     partial(_picker, "build_rig")),
    ("picker.fk", "Rig Picker", "FK Limbs",
     "Bring the selected limbs to FK",
     partial(_picker, "convert_selected_limbs", False)),
    ("picker.ik", "Rig Picker", "IK Limbs",
     "Bring the selected limbs to IK",
     partial(_picker, "convert_selected_limbs", True)),
    ("picker.bake", "Rig Picker", "Bake+Delete",
     "Bake what the selection touches back onto clean bones",
     partial(_picker, "bake_selected_limbs")),
    ("picker.all", "Rig Picker", "Select All",
     "Select every controller on the body map",
     partial(_picker, "select_group", "all")),

    ("scene.character", "Scene Setup", "Import Character",
     "Import the chosen skeleton into this scene",
     partial(_scene, "add_character")),
    ("scene.weapon", "Scene Setup", "Add Weapon",
     "Import the chosen weapon and drive its bone from it",
     partial(_scene, "add_weapon", section="weapons")),
    ("scene.remove_weapon", "Scene Setup", "Remove Weapon",
     "Bake the bone back off the weapon and delete it",
     partial(_scene, "remove_weapon", section="weapons")),
    ("window.armor", "Windows", "Armor",
     "Open the Armor section: put a piece of armor on the character",
     partial(_show, "maya_scenesetup.armorpanel", "show_window")),
    ("window.connections", "Windows", "Connections",
     "Open the Connections section: hands on the weapon and off it",
     partial(_show, "maya_scenesetup.connections", "show_window")),
    ("window.inventory", "Windows", "Weapon inventory",
     "Open the Weapons card - the inventory: drag a weapon onto a hand in "
     "the viewport, or onto the floor",
     partial(_show, "maya_inventory", "show")),
    ("window.shared", "Windows", "Shared",
     "Open the Shared section: send the scene or an FBX to everybody, open "
     "what they sent",
     partial(_show, "maya_share", "show_window")),
    ("window.com", "Windows", "Center of Mass",
     "Open the Center of Mass section: the CoM point, its trail, the CoM "
     "tool",
     partial(_show, "maya_com.panel", "show_window")),
    ("connections.connect", "Connections", "Connect hands to weapon",
     "The chosen IK hands onto the weapon (OverRig lifts the weapon to "
     "world), the arms in IK",
     partial(_connections, "_press_connect")),
    ("connections.disconnect", "Connections", "Disconnect hands",
     "Bake the hands where the weapon carried them, weapon back in the hand",
     partial(_connections, "_press_disconnect")),
    # Connect Arms / Disconnect Arms / Add Aim / Camera Setup left Scene
    # Setup on 2026-09-07 with the move to the AdvancedSkeleton rig; the
    # camera setup happens inside the retarget's Bake now.

    # One row since 2026-09-08: Retarget and Bake are one button.
    ("retarget.run", "Retarget", "Retarget the selected skeleton onto the rig",
     "The rig takes the selected imported skeleton's clip: retarget, bake, "
     "weapon and camera bones carried, camera set up",
     partial(_retarget, "retarget_button")),

    ("shoot.snap", "Overshoot", "Overshoot Snap",
     "One tight swing out of the pose", partial(_overshoot, "Snap")),
    ("shoot.spring", "Overshoot", "Overshoot Spring",
     "Three decaying swings", partial(_overshoot, "Spring")),
    ("shoot.elastic", "Overshoot", "Overshoot Elastic",
     "Six slowly decaying swings", partial(_overshoot, "Elastic")),
    ("shoot.recoil", "Overshoot", "Overshoot Recoil",
     "Two hard swings", partial(_overshoot, "Recoil")),
    ("shoot.bounce", "Overshoot", "Overshoot Bounce",
     "Arcs under gravity", partial(_overshoot, "Bounce")),
)

# Pavel Barnev's own list of procedures meant for hotkeys, from
# overrig/function_for_hotkeys.TXT, with his headings as the categories and
# his arguments as written there.
#
# Two procedures are deliberately absent, spelled out here so a grep for
# either one lands on the reason: barn_fast_bake_source_obj_and_delete_knots
# and barn_fast_bake_min_max_or_range_source_obj_and_delete_knots are the
# only ones in the file that ignore the selection and work on the whole
# scene -- they select all of OverRig_rig_objects, bake, and delete every
# knot -- which is not a thing to put one keypress away. A gone-test names
# both. The ones needing real arguments (execute_overlap_command, the motion
# trail, the ribbon) are here as their windows instead: for those, the
# window IS the one-press command.
_OVERRIG = (
    ("overrig.panel", "Menu", "OverRig panel",
     "The native OverRig panel", partial(_mel, "base_OverRig_scripts(1);")),

    ("overrig.rotate_order_xyz", "Rotation order", "Convert to xyz",
     "Convert the selection's rotation order to xyz",
     partial(_mel, 'barn_execute_convert_rotation_order("xyz");')),

    ("overrig.smart_knot", "Smart object", "Smart knot",
     "Bake the animation onto a smart locator",
     partial(_mel, "apply_smart_parentConstrAnim(1);")),
    ("overrig.smart_pivot", "Smart object", "Smart pivot knot",
     "Bake the animation onto a smart offset locator",
     partial(_mel, "apply_smart_PivotParentAnimation(1.5);")),
    ("overrig.smart_orient", "Smart object", "Smart orient knot",
     "Bake the animation onto a smart orient locator",
     partial(_mel, "apply_smart_Knot_Orient_Point(1.5);")),
    ("overrig.smart_bake_object", "Smart object", "Smart bake (object keys)",
     "Bake with this object's keyframes",
     partial(_mel, "apply_Smart_Bake(0);")),
    ("overrig.smart_bake_knot", "Smart object", "Smart bake (knot keys)",
     "Bake with the smart knot's keyframes",
     partial(_mel, "apply_Smart_Bake(1);")),

    ("overrig.knot_orient", "Knot", "Knot orient",
     "Create an orient knot on the selection",
     partial(_mel, "apply_Knot_Orient_Point(1);")),
    ("overrig.knot_pivot", "Knot", "Pivot knot",
     "Create a pivot knot on the selection",
     partial(_mel, "apply_PivotParentAnimation(1);")),
    ("overrig.knot", "Knot", "Knot",
     "Create a knot on the selection",
     partial(_mel, "apply_parentConstrAnim(1);")),

    ("overrig.parent_out", "Parent", "Parent to world",
     "Lift the selection to world, animation re-baked",
     partial(_mel, "apply_Parent_out();")),
    ("overrig.parent_in", "Parent", "Parent inside",
     "Hang the child on the parent - select child first, parent last",
     partial(_mel, "apply_Parent_in();")),
    ("overrig.parent_swap", "Parent", "Swap parent",
     "Swap the parent", partial(_mel, "apply_Swap_parent();")),
    ("overrig.parent_across", "Parent", "Parent across knot",
     "Create a parent-across knot",
     partial(_mel, "apply_parent_anim_across(1);")),

    ("overrig.aim", "Aim", "Create aim",
     "Create the aim locators on the selection",
     partial(_mel, "make_aim_from_selected(1);")),
    ("overrig.overlap_window", "Aim", "Overlapper window",
     "Open the overlapper window",
     partial(_mel, "bar_tail_overlap_window;")),
    ("overrig.attach_on", "Aim", "Key attach 1",
     "Key the attach attribute at 1",
     partial(_mel, "setKey_on_attach_attr(1);")),
    ("overrig.attach_off", "Aim", "Key attach 0",
     "Key the attach attribute at 0",
     partial(_mel, "setKey_on_attach_attr(0);")),

    ("overrig.lag_key", "Key tools", "Lag key",
     "Lag the keys by 1.2 frames", partial(_mel, "Lag_Key(1.2);")),
    ("overrig.infinity_cycle", "Key tools", "Infinity: cycle",
     "Pre/post infinity to cycle",
     partial(_mel, 'set_infinity_graphEditor("cycle");')),
    ("overrig.infinity_oscillate", "Key tools", "Infinity: oscillate",
     "Pre/post infinity to oscillate",
     partial(_mel, 'set_infinity_graphEditor("oscillate");')),
    ("overrig.infinity_linear", "Key tools", "Infinity: linear",
     "Pre/post infinity to linear",
     partial(_mel, 'set_infinity_graphEditor("linear");')),
    ("overrig.infinity_constant", "Key tools", "Infinity: constant",
     "Pre/post infinity to constant",
     partial(_mel, 'set_infinity_graphEditor("constant");')),
    ("overrig.oscillate", "Key tools", "Oscillate keys",
     "Oscillate the period taken from the time slider",
     partial(_mel, "double_oscillate_keys(2);")),
    ("overrig.first_to_last", "Key tools", "Copy first frame to last",
     "For cycling animation", partial(_mel, "copy_start_frame_to_end();")),
    ("overrig.keys_first_last", "Key tools", "Key first and last frame",
     "Set keys on the first and last frame",
     partial(_mel, "set_start_end_key();")),
    ("overrig.key_range_all", "Key tools", "Key range: all",
     "The same keyframe across the selected time range",
     partial(_mel, 'set_key_time_range("all");')),
    ("overrig.key_range_translate", "Key tools", "Key range: translate",
     "Translate keys across the selected time range",
     partial(_mel, 'set_key_time_range("translate");')),
    ("overrig.key_range_rotate", "Key tools", "Key range: rotate",
     "Rotate keys across the selected time range",
     partial(_mel, 'set_key_time_range("rotate");')),
    ("overrig.key_range_channelbox", "Key tools", "Key range: channel box",
     "The channel box's channels across the selected time range",
     partial(_mel, 'set_key_time_range("channelbox");')),
    ("overrig.select_keys_range", "Key tools", "Select keys in range",
     "Select the current key or the selected frame range",
     partial(_mel, "selKeys_by_timerange();")),
    ("overrig.delete_keys", "Key tools", "Delete keys",
     "Delete the selected frames on every channel of every selection",
     partial(_mel, "delete_keys_from_selected_or_timeslider();")),
    ("overrig.slider_range", "Key tools", "Toggle slider range",
     "Toggle the time slider range by 24",
     partial(_mel, "time_slider_range(24);")),
    ("overrig.time_to_mid", "Key tools", "Time to mid selection",
     "Move the time slider to the middle of the selection",
     partial(_mel, "set_currenttime_to_mid_selection();")),
    ("overrig.copy_keys", "Key tools", "Copy keys",
     "Copy the selected single-curve frames",
     partial(_mel, "barn_copy_keys();")),
    ("overrig.paste_scaled", "Key tools", "Paste scaled keys",
     "Paste, scaled to the selected frames",
     partial(_mel, "barn_past_scaled_keys();")),
    ("overrig.offset_half_period", "Key tools", "Offset by half period",
     "Shift the keys by half a period",
     partial(_mel, "offset_keys_by_period(2);")),
    ("overrig.mirror_keys", "Key tools", "Mirror keys in X",
     "Inverse-mirror the selected keys about X",
     partial(_mel, 'double_inv_oscillate_or_mirror(2, "x", "x");')),
    ("overrig.noise_window", "Key tools", "Noise window",
     "Open the noise window", partial(_mel, "overRig_noise_window;")),
    ("overrig.tween_window", "Key tools", "Tween window",
     "Tween, overshoot and curve push",
     partial(_mel, "overRig_tween_window();")),
    ("overrig.tween_left", "Key tools", "Tween 0%",
     "All the way to the left-side key",
     partial(_mel, "bar_tween_machine(0, `ls -sl`);")),
    ("overrig.tween_right", "Key tools", "Tween 100%",
     "All the way to the right-side key",
     partial(_mel, "bar_tween_machine(1, `ls -sl`);")),

    ("overrig.select_constrained", "Selector", "Select constrained object",
     "From a knot to the object it drives",
     partial(_mel, "return_constrained_object(1);")),
    ("overrig.select_sources", "Selector", "Select rig sources",
     "Every object OverRig's rigs drive",
     partial(_mel, 'barn_sel_set_member("OverRig_rig_objects");')),
    ("overrig.select_knots", "Selector", "Select knots",
     "Every OverRig knot in the scene",
     partial(_mel, 'barn_sel_set_member("OverRig_knots");')),

    ("overrig.double_global", "Double knots", "Double global knot",
     "Create a double global knot",
     partial(_mel, "apply_DoubleUzelGlobal(1);")),
    ("overrig.double_local", "Double knots", "Double local knot",
     "Create a double local knot",
     partial(_mel, "apply_DoubleUzelLocal(1);")),

    ("overrig.snapshot_object", "Snapshot", "Object snapshot",
     "Create an object snapshot", partial(_mel, "apply_LOH_Fast(1);")),
    ("overrig.snapshot_component", "Snapshot", "Component snapshot",
     "Create a component snapshot",
     partial(_mel, "apply_LOH_Component(1);")),

    ("overrig.forward_hierarchy", "Hierarchy", "Forward hierarchy",
     "Create a forward hierarchy over the selection",
     partial(_mel, "apply_ForwHierarhy(1);")),
    ("overrig.reverse_hierarchy", "Hierarchy", "Reverse hierarchy",
     "Create a reverse hierarchy over the selection",
     partial(_mel, "apply_ReverseHierarhy(1);")),
    ("overrig.spine_menu", "Hierarchy", "Vertebra system menu",
     "Bake to the easy vertebra system",
     partial(_mel, "create_recalc_spine_rig_menue();")),

    ("overrig.to_ik", "IK", "Bake FK to IK",
     "Three or more selected joints to IK",
     partial(_mel, "apply_rebike_3_or_more_object_to_IK;")),
    ("overrig.spline_ik", "IK", "Bake to spline IK",
     "Two or more selected to spline IK",
     partial(_mel, "apply_objects_spline_IK(0);")),
    ("overrig.spline_ik_depend", "IK", "Bake to depend spline IK",
     "Two or more selected to dependent spline IK",
     partial(_mel, "apply_objects_spline_IK(1);")),

    ("overrig.bake", "Bake", "Bake",
     "Bake the selection", partial(_mel, "apply_Fast_Bake();")),
    ("overrig.bake_range", "Bake", "Bake range",
     "Bake min-max or the selected range, keys outside kept",
     partial(_mel, "apply_range_Fast_Bake();")),
    ("overrig.bake_layer", "Bake", "Bake to layer",
     "Bake the selection to an anim layer",
     partial(_mel, "apply_Bake_to_layer();")),
    ("overrig.bake_range_layer", "Bake", "Bake range to override layer",
     "Bake min-max or the selected range to an override layer",
     partial(_mel, "apply_range_Bake_to_Over_layer();")),
    ("overrig.strip_constraints", "Bake", "Delete constraint channels",
     "Strip the constraint channels from the selection",
     partial(_mel, "delete_constraint_attributes_on_objects(`ls -sl`);")),
    ("overrig.euler_filter", "Bake", "Euler filter",
     "Fast euler filter from zero",
     partial(_mel, "euler_filter_on_selected();")),
    ("overrig.viewport_on", "Bake", "Enable viewport",
     "Turn the viewport back on after a bake",
     partial(_mel, "OVR_en_viewport();")),

    ("overrig.arc_tool", "Sword", "Arc polish tool",
     "Open the arc polish tool", partial(_mel, "BP_arc_tool_menue();")),
    ("overrig.sword_reverse", "Sword", "Sword reverse system",
     "Assign the sword reverse system",
     partial(_mel, "assign_Sword_pivot_System(1);")),
    ("overrig.sword_system", "Sword", "Sword system",
     "Assign the sword system", partial(_mel, "assign_Sw_System;")),

    ("overrig.jiggle", "Physics", "Jiggle point",
     "Assign a physical point on the selection",
     partial(_mel, "assign_jiggle_bone_soft(1);")),
    ("overrig.chain_menu", "Physics", "Physic chain menu",
     "Open the physics chain window",
     partial(_mel, "dyn_tail_tool_window();")),

    ("overrig.locators_on_selected", "Misc", "Locators on selected",
     "Create locators on the selection",
     partial(_mel, "create_normalised_locators_on_selected();")),
    ("overrig.locators_inside", "Misc", "Locators inside",
     "Create locators inside the selection",
     partial(_mel, "mocup_parent_locators_inside();")),
    ("overrig.color_menu", "Misc", "Colour menu",
     "Override the display colour",
     partial(_mel, "small_DisplayColorOverrideUI();")),
    ("overrig.shape_menu", "Misc", "Shape menu",
     "Override the control shape",
     partial(_mel, "small_Shape_OverrideUI();")),
    ("overrig.scale_up", "Misc", "Scale locator or joint 1.5",
     "Locally scale the selected locator or joint",
     partial(_mel, "scale_selected_lock_or_joint(1.5);")),
    ("overrig.anim_pivot_last", "Misc", "Anim pivot (last selected)",
     "Animated pivot at the last selected position",
     partial(_mel, "move_and_rotate_total_pivot(0);")),
    ("overrig.anim_pivot_average", "Misc", "Anim pivot (average)",
     "Animated pivot at the average position",
     partial(_mel, "move_and_rotate_total_pivot(1);")),
    ("overrig.isolate_toggle", "Misc", "Isolate selection toggle",
     "Toggle isolate-select in the current viewport",
     partial(_mel, "apply_bar_isolate_selection_toggler(0);")),
    ("overrig.translate_axis", "Misc", "Translate tool axis",
     "Change the translate tool's axis",
     partial(_mel, "bar_translate_toggler();")),
    ("overrig.rotate_axis", "Misc", "Rotate tool axis",
     "Change the rotate tool's axis",
     partial(_mel, "bar_rotate_toggler();")),
    ("overrig.xray", "Misc", "X-ray toggle",
     "Toggle x-ray in the current viewport",
     partial(_mel, "bar_x_ray_toggler();")),

    ("overrig.finger_pivot_window", "Finger", "Finger pivot window",
     "Open the finger pivot window",
     partial(_mel, "brn_apply_finger_pivot_window();")),
    ("overrig.finger_bend", "Finger", "Finger bend",
     "Finger bend tool",
     partial(_mel, 'brn_apply_finger_bend_tool("bend");')),
    ("overrig.finger_3ik", "Finger", "Finger 3IK",
     "Finger three-joint IK",
     partial(_mel, 'brn_apply_finger_bend_tool("3IK");')),
    ("overrig.finger_4ik", "Finger", "Finger 4IK",
     "Finger four-joint IK variant",
     partial(_mel, 'brn_apply_finger_bend_tool("4IK_var");')),
    ("overrig.finger_rot_pivot", "Finger", "Finger rotate pivot",
     "Finger rotate-pivot tool",
     partial(_mel, 'brn_apply_finger_bend_tool("rot_piv");')),
    ("overrig.finger_twist", "Finger", "Finger twist",
     "Finger twist tool",
     partial(_mel, 'brn_apply_finger_bend_tool("twist");')),
)


def _prefixed(root, table):
    return tuple((key, root + "." + category, label, note, action)
                 for key, category, label, note, action in table)


def commands(flags):
    """The table for a set of feature flags. Pure.

    Since 2026-09-07 the picker's six rows ride `flags.PICKER`; since
    2026-09-08 Overshoot's six ride `flags.OVERSHOOT`; and since 2026-09-19
    the author's 84 OverRig rows ride `flags.OVERRIG_HOTKEYS` -- a flag of
    their own, because `OVERRIG` is the OverRig SHELF BUTTON, which the
    animator wanted back without the rows. All three ship off. The rows
    themselves stay in the tables above, so a flag flipped back registers
    them again on the next press.
    """
    overshoot = getattr(flags, "OVERSHOOT", False)
    ours = tuple(row for row in _OURS
                 if (flags.PICKER or not row[0].startswith("picker."))
                 and (overshoot or not (row[0].startswith("shoot.")
                                        or row[0] == "window.overshoot")))
    table = _prefixed("SkeldarAnim", ours)
    if getattr(flags, "OVERRIG_HOTKEYS", False):
        table += _prefixed("OverRig", _OVERRIG)
    return table


import skeldar_features  # noqa: E402 - beside this file, stdlib only

COMMANDS = commands(skeldar_features)

_INDEX = dict((command[0], command) for command in COMMANDS)
