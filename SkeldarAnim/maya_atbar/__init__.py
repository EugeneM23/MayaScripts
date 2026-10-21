"""The AT bar (2026-10-21): animBot's animation tools, native, as a strip of their own in the hub's look.

The animator: «в пустій сцені з відкритим портом 7001 я хочу щоб ти мені зробив аналог кнопок анімботу»,
then «а зроби не полку, а окреме меню такого ж типу як таймслайдер і зроби галочку на АТ в панельці
налаштувань Timebar». While the Time Bar stands docked the strip is its TOP ROW, inside the Time Bar's own
control (then «прибери ще сірі роздєлітєльні лінії»: a control of its own stood behind Maya's splitter
line); the Time Bar's height counts it (`maya_timebar.extra_height`). Without a docked Time Bar it is a
workspaceControl `skeldarATBar` of its own, with no tab and no title, docked where the Time Bar would be.
⋮ -> Time bar ▸ AT bar turns it on and off (optionVar skeldarATBar, off by default). Nothing heavy at
import.

Its look is layout B of the mockups (https://claude.ai/artifact/FG74SWkoW6u2UoQ2Xw6Ak4): every animBot icon
redrawn 1:1 in our line style (`glyphs`), a caption over each group in its colour, the Time Bar's controls
and motion (`bar`). The tools are `core`.
"""

import os

CONTROL = "skeldarATBar"
TIMEBAR = "skeldarTimeBar"
LABEL = "AT"
OPTIONVAR = "skeldarATBar"
HEIGHT = 57                 # logical px: the caption row and one row of 24 px controls

MESSAGES = {
    True: "AT bar on, above the Time Bar",
    False: "AT bar off - ⋮ -> Time bar ▸ AT bar brings it back",
}


def plugin_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace("\\", "/")


def uiscript(root):
    root = root.replace("\\", "/").rstrip("/")
    return ("import sys\n_p = \"{0}\"\nif _p not in sys.path:\n    sys.path.insert(0, _p)\n"
            "import maya_atbar.bar\nmaya_atbar.bar.build()\n").format(root)


def wanted():
    """The animator turned the bar on (⋮ -> Time bar ▸ AT bar); off until then."""
    import maya.cmds as cmds
    return bool(cmds.optionVar(q=OPTIONVAR)) if cmds.optionVar(exists=OPTIONVAR) else False


def dock_target(exists, visible):
    """(flag, value) for a new control: on top of the Time Bar while it shows, else on top of Maya's Time
    Slider, else the bottom of Maya's window. `exists(name)` / `visible(name)` ask the scene. Pure."""
    for name in ("skeldarTimeBar", "TimeSlider"):
        if exists(name) and visible(name):
            return "dockToControl", (name, "top")
    for name in ("skeldarTimeBar", "TimeSlider"):
        if exists(name):
            return "dockToControl", (name, "top")
    return "dockToMainWindow", ("bottom", False)


def _exists(name):
    import maya.cmds as cmds
    return bool(cmds.workspaceControl(name, exists=True))


def _visible(name):
    import maya.cmds as cmds
    return bool(cmds.workspaceControl(name, q=True, visible=True))


def _timebar_host():
    """The docked Time Bar's control widget while it stands docked and shows, else None."""
    try:
        import maya_hubqt
        import maya_timebar
    except Exception:                                        # noqa: BLE001
        return None
    if maya_timebar._state().get("host") != "docked" or not _exists(TIMEBAR) or not _visible(TIMEBAR):
        return None
    return maya_hubqt.host_widget(TIMEBAR)


def ensure():
    """The bar standing: the Time Bar's top row while it stands docked (our own control deleted), else
    our own control made (or restored) with the strip in it. Where it stands."""
    import maya.cmds as cmds
    if cmds.about(batch=True):
        return ""
    from . import bar
    host = _timebar_host()
    if host is not None:
        if _exists(CONTROL):
            cmds.deleteUI(CONTROL)
        bar.attach(host)
        return TIMEBAR
    bar.detach()
    if _exists(CONTROL):
        cmds.workspaceControl(CONTROL, edit=True, restore=True, visible=True)
    else:
        options = dict(label=LABEL, retain=False, floating=False, heightProperty="fixed",
                       initialHeight=HEIGHT, actLikeMayaUIElement=True, uiScript=uiscript(plugin_root()))
        flag, value = dock_target(_exists, _visible)
        options[flag] = value
        cmds.workspaceControl(CONTROL, **options)
    if bar.current() is None:
        bar.build()
    return CONTROL


def hide():
    """The strip out of the Time Bar and our own control hidden."""
    import maya.cmds as cmds
    if cmds.about(batch=True):
        return
    from . import bar
    bar.detach()
    if _exists(CONTROL):
        cmds.workspaceControl(CONTROL, edit=True, visible=False)


def docked_height():
    """Logical px of the strip as the Time Bar's top row; 0 when it is not there
    (`maya_timebar.extra_height`). Imports nothing that is not loaded already."""
    import sys
    bar = sys.modules.get(__name__ + ".bar")
    strip = bar.embedded() if bar is not None else None
    return strip.logical_height() if strip is not None else 0


def set_on(on):
    """⋮ -> Time bar ▸ AT bar: remembered, the bar shown or hidden. What to say."""
    import maya.cmds as cmds
    on = bool(on)
    cmds.optionVar(intValue=(OPTIONVAR, 1 if on else 0))
    if on:
        ensure()
    else:
        hide()
    return MESSAGES[on]


def ensure_wanted():
    """At the hub's build: the bar back when the animator left it on."""
    return ensure() if wanted() else None
