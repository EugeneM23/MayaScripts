"""Use Skeldar interface / Use Maya interface (2026-10-19).

The animator: «в настройках нашего плагина сделаем два переключателя Use Maya
interface и use Skeldar interface. при нажатии на использоват наш интерфейс
таймслайдер ченелбокс и атрибут эдитор станут нашими».

One switch over three things that already exist:

- Skeldar: the Time Bar (at the bottom edge, or docked when that was the
  animator's choice), the side panel at the right edge holding the Attribute
  Editor, and our Channel Box in it;
- Maya: Maya's own time slider, Channel Box and Attribute Editor.

Anything else mixed by hand in ⋮ -> Time bar / Side panel reads "mixed": no row
of the switch is lit. `reload_live()` stands the chosen interface up again from
the modules on disk - an install calls it, so an update shows at once.

Stdlib at import; the Maya halves are imported inside.
"""

import traceback

SKELDAR = "skeldar"
MAYA = "maya"
MIXED = "mixed"
CHOICES = (SKELDAR, MAYA)
LABELS = ((SKELDAR, "Use Skeldar interface"), (MAYA, "Use Maya interface"))

MESSAGES = {
    SKELDAR: "Skeldar interface: our Time Bar, Channel Box and Attribute Editor",
    MAYA: "Maya interface: Maya's time slider, Channel Box and Attribute Editor",
}


def state_of(timebar_mode, side_mode, box_on=True):
    """Which interface stands (pure): Skeldar when the Time Bar is ours, the side
    panel stands at the edge and our Channel Box is in it; Maya when the Time Bar
    and the side panel are Maya's; else mixed."""
    if timebar_mode != "maya" and side_mode == "edge" and box_on:
        return SKELDAR
    if timebar_mode == "maya" and side_mode != "edge":
        return MAYA
    return MIXED


def timebar_for(choice, current, last):
    """The Time Bar mode a choice asks for (pure): Maya's for Maya; for Skeldar
    the standing ours, else the last ours, else the bottom edge."""
    if choice == MAYA:
        return "maya"
    if current in ("docked", "edge"):
        return current
    return last if last in ("docked", "edge") else "edge"


def current():
    try:
        import maya_timebar
        import maya_sidepanel
        import maya_channelbox
        return state_of(maya_timebar.mode(), maya_sidepanel.mode(),
                        maya_channelbox.enabled())
    except Exception:                                        # noqa: BLE001
        print(traceback.format_exc())
        return MIXED


def use(choice):
    """The interface switched; returns what to say."""
    import maya.cmds as cmds
    import maya_timebar
    import maya_sidepanel
    import maya_channelbox
    choice = choice if choice in CHOICES else SKELDAR
    last = (cmds.optionVar(q=maya_timebar.LAST_VAR)
            if cmds.optionVar(exists=maya_timebar.LAST_VAR) else None)
    problems = []
    try:
        maya_timebar.set_mode(timebar_for(choice, maya_timebar.mode(), last))
    except Exception:                                        # noqa: BLE001
        print(traceback.format_exc())
        problems.append("the Time Bar")
    try:
        if choice == SKELDAR:
            box_was = maya_channelbox.enabled()
            cmds.optionVar(intValue=(maya_channelbox.VAR, 1))
            if maya_sidepanel.mode() == "edge" and not box_was:
                maya_sidepanel.rebuild()           # ours mounted in the standing panel
            else:
                said = maya_sidepanel.set_mode("edge")
                if maya_sidepanel.mode() != "edge":
                    problems.append("the side panel ({0})".format(said))
        else:
            maya_sidepanel.set_mode("maya")
    except Exception:                                        # noqa: BLE001
        print(traceback.format_exc())
        problems.append("the side panel")
    message = MESSAGES[choice]
    if problems:
        message += " - not switched: " + ", ".join(problems) + " (see the Script Editor)"
    return message


def reload_live():
    """What the OLD modules built (the Time Bar, the side panel, our Channel Box)
    dropped and the chosen interface stood up again from these modules (an
    install, 2026-10-19: «при установки обновления наш плагин обнавлял интерфейс
    в реальном времени»). Never raises; returns what was rebuilt."""
    done = []
    for name in ("maya_sidepanel", "maya_timebar"):
        try:
            module = __import__(name)
            if module.reload_live():
                done.append(name)
        except Exception:                                    # noqa: BLE001
            print("SkeldarAnim: {0} was not rebuilt after the install".format(name))
            print(traceback.format_exc())
    return done
