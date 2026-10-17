"""The Ragdoll card (2026-10-16): what the press would do, its knobs, Fall or Blend, the line.

Since 2026-10-17 two modes, `[Fall | Blend]`: Fall drops the rig; Blend mixes the take with the
ragdoll zone by zone (`blend.py`) - six zone rows `[Anim | Follow | Free]` with a strength, presets,
Blend in / out. A plain `cmds` card with the hub's marks; every press reads the remembered settings
when the card is closed (a hotkey row presses it then).
"""

import json

import maya.cmds as cmds

from maya_ragdoll import fall as rd

HUB_SECTION = "ragdoll"
SUBTITLE = "skeldarRagdollSubtitle"
STATUS = "skeldarRagdollStatus"
FALL_BTN = "skeldarRagdollFall"
BLEND_BTN = "skeldarRagdollBlend"
IMPULSE_BTN = "skeldarRagdollImpulse"
DROP_CHIP = "skeldarRagdollDropWeapon"
OPTION = "skeldarRagdoll_settings"
LAYER_TABS = "skeldarRagdollLayers"
LAYERS = (("new", "New layer"), ("base", "Base layer"))
MODE_TABS = "skeldarRagdollModes"
MODES = (("fall", "Fall"), ("blend", "Blend"))
FALL_BOX = "skeldarRagdollFallBox"
BLEND_BOX = "skeldarRagdollBlendBox"

#  (key, label, low, high, step): both modes', then Fall's, then Blend's
SLIDERS = (
    ("length", "Length, fr", 10.0, 300.0, 1.0),
    ("mass", "Mass, kg", 20.0, 300.0, 1.0),
    ("friction", "Friction", 0.0, 2.0, 0.05),
    ("bounce", "Bounce", 0.0, 1.0, 0.05),
)
FALL_SLIDERS = (
    ("fade", "Muscle fade", 0.0, 60.0, 1.0),
    ("strength", "Strength", 0.0, 4.0, 0.05),
)
BLEND_SLIDERS = (
    ("blend_in", "Blend in, fr", 0.0, 60.0, 1.0),
    ("blend_out", "Blend out, fr", 0.0, 60.0, 1.0),
)
ALL_SLIDERS = SLIDERS + FALL_SLIDERS + BLEND_SLIDERS
TIPS = {
    "length": "Frames the press runs when nothing is highlighted on the time slider",
    "fade": "Frames the muscles hold the pose of the fall's first frame before they let go (0: a "
            "rag doll at once)",
    "strength": "How hard the muscles hold that pose while they fade",
    "mass": "The whole body's mass, shared by de Leva's segment table",
    "friction": "How the body grips the floor and the colliders",
    "bounce": "How much it bounces off them",
    "drop": "A weapon held in a hand is let go at the fall and lands on the floor; its bone "
            "follows it",
    "layer": "New layer: the result on its own layer (Ragdoll_<frame> or RagdollBlend_<frame>), the "
             "take kept under it (mute to see it). Base layer: the take's keys replaced",
    "impulse": "Select a part of a rig: an arrow on it - its tip is where the hit lands, the arrow "
               "its direction; Frame, Speed (m/s) and Enabled in the Channel Box. Fall and Blend "
               "hit that part at that frame",
    "fall": "Select any part of a rig (and any meshes to fall onto). The fall starts at the "
            "highlight's first frame, else the current frame",
    "blend": "Select any part of a rig (and any meshes to touch). Over the highlight, else from the "
             "current frame for Length, the take and the ragdoll are mixed zone by zone",
    "blend_in": "Frames the zones take to ease from the take into their own strength",
    "blend_out": "Frames at the end the zones and the layer take to ease back onto the take",
    "mode": "Fall: the rig drops as a rag doll. Blend: the take and the ragdoll mixed",
    "anim": "Anim: this zone plays the take exactly and carries its neighbours (legs in Anim hold "
            "the pelvis too)",
    "follow": "Follow: this zone is a body on a spring to the take - it lags, swings past and "
              "sags under its weight; Strength 1 keeps it on the take",
    "free": "Free: this zone is a rag doll between Blend in and Blend out",
    "zone_strength": "How stiff a Follow zone's spring is and how much of its weight it holds "
                     "(1: on the take; 0.5: lags and sags a hand's width; 0.2: nearly limp)",
    "preset": "Sets the six zones",
}
JOB = {}


def _slider(key):
    return "skeldarRagdoll_" + key


def _tab(key):
    return "skeldarRagdollLayer_" + key


def _mode(key):
    return "skeldarRagdollMode_" + key


def _zone_tabs(zone):
    return "skeldarRagdollZone_" + zone


def _zone_seg(zone, state):
    return "skeldarRagdollZone_%s_%s" % (zone, state)


def _zone_strength(zone):
    return "skeldarRagdollZoneStrength_" + zone


def _preset_btn(name):
    return "skeldarRagdollPreset_" + name


def remembered():
    try:
        given = json.loads(cmds.optionVar(query=OPTION)) if cmds.optionVar(exists=OPTION) else None
    except (TypeError, ValueError):
        given = None
    return rd.settings(given)


def remember(s):
    cmds.optionVar(stringValue=(OPTION, json.dumps(s)))


def values():
    """The settings as the card shows them (remembered), else as remembered."""
    s = remembered()
    if cmds.floatSliderGrp(_slider(SLIDERS[0][0]), exists=True):
        for key, *_rest in ALL_SLIDERS:
            if cmds.floatSliderGrp(_slider(key), exists=True):
                s[key] = cmds.floatSliderGrp(_slider(key), query=True, value=True)
        s["drop_weapon"] = bool(cmds.checkBox(DROP_CHIP, query=True, value=True))
        for key, _label in LAYERS:
            if cmds.iconTextRadioButton(_tab(key), query=True, select=True):
                s["layer"] = key
        for key, _label in MODES:
            if (cmds.iconTextRadioButton(_mode(key), exists=True)
                    and cmds.iconTextRadioButton(_mode(key), query=True, select=True)):
                s["mode"] = key
        zones = dict(s["zones"])
        for zone in rd.plan.ZONES:
            if not cmds.floatField(_zone_strength(zone), exists=True):
                continue
            state = zones[zone][0]
            for name in rd.plan.STATES:
                if cmds.iconTextRadioButton(_zone_seg(zone, name), query=True, select=True):
                    state = name
            zones[zone] = [state, cmds.floatField(_zone_strength(zone), query=True, value=True)]
        s["zones"] = zones
    s = rd.settings(s)
    remember(s)
    return s


def status(text):
    import maya_hubstyle as hubstyle
    if cmds.text(STATUS, exists=True):
        cmds.text(STATUS, edit=True, label=text)
        hubstyle.tell(STATUS, text)
    return text


def subtitle():
    """What the press would do now."""
    try:
        ref = rd._ref(cmds.ls(selection=True, long=True) or [])
    except rd.Refused as refusal:
        return str(refusal)
    except Exception:                                      # noqa: BLE001
        return rd.NOTHING
    s = remembered()
    a, b = rd.plan.span(rd._highlight(), cmds.currentTime(query=True), s["length"])
    from maya_ragdoll import impulse
    try:
        count = len([p for p in impulse.arrows(ref.rig) if cmds.getAttr(p + ".enabled")])
    except Exception:                                      # noqa: BLE001
        count = 0
    tail = (", %d impulse%s" % (count, "" if count == 1 else "s")) if count else ""
    if s["mode"] == "blend":
        return "%s blends with physics from frame %d to %d%s" % (ref.label, a, b, tail)
    return "%s falls from frame %d to %d%s" % (ref.label, a, b, tail)


def refresh(*_):
    if cmds.text(SUBTITLE, exists=True):
        cmds.text(SUBTITLE, edit=True, label=subtitle())


def press_fall(*_):
    """Fall: the selected rig drops from the highlight's first frame (else the current one)."""
    return _press(_run, "Ragdoll")


def press_blend(*_):
    """Blend: the take and the ragdoll mixed over the highlight (else from the current frame)."""
    return _press(_run_blend, "Ragdoll Blend")


def press_main(*_):
    """The card's main button: Fall or Blend, as the mode stands."""
    return press_blend() if values()["mode"] == "blend" else press_fall()


def _press(run, name):
    s = values()
    try:
        _ok, line = run(s)
        message = line
    except rd.Refused as refusal:
        message = str(refusal)
    except Exception as error:                              # noqa: BLE001 - the card stays usable
        import traceback
        print(traceback.format_exc())
        message = "%s failed: %s" % (name, error)
    refresh()
    return status(message)


def press_impulse(*_):
    """+ Impulse: an arrow on the selected part of a rig."""
    from maya_ragdoll import impulse
    try:
        _arrow, message = impulse.create()
    except rd.Refused as refusal:
        message = str(refusal)
    except Exception as error:                              # noqa: BLE001
        import traceback
        print(traceback.format_exc())
        message = "+ Impulse failed: %s" % error
    refresh()
    return status(message)


def _progress(name, s):
    from maya_poselib import timewalk
    try:
        return timewalk.Progress(name, int(s["length"]) + 1)
    except Exception:                                      # noqa: BLE001 - no UI
        return None


def _run(s):
    progress = _progress("Ragdoll", s)
    if progress is None:
        return rd.fall(given=s)
    with progress:
        return rd.fall(given=s, progress=lambda t: progress.step("frame %d" % t))


def _run_blend(s):
    from maya_ragdoll import blend
    progress = _progress("Ragdoll Blend", s)
    if progress is None:
        return blend.blend(given=s)
    with progress:
        return blend.blend(given=s, progress=lambda t: progress.step("frame %d" % t))


def _changed(*_):
    s = values()
    show_mode(s["mode"])
    refresh()


def show_mode(mode):
    """Fall's or Blend's own rows and button shown, the other's hidden."""
    for box, button, key in ((FALL_BOX, FALL_BTN, "fall"), (BLEND_BOX, BLEND_BTN, "blend")):
        if cmds.columnLayout(box, exists=True):
            cmds.columnLayout(box, edit=True, manage=mode == key)
        if cmds.button(button, exists=True):
            cmds.button(button, edit=True, manage=mode == key)


def apply_preset(name):
    """A preset's six zones into the card (and remembered)."""
    zones = rd.plan.preset(name)
    for zone, (state, strength) in zones.items():
        if cmds.floatField(_zone_strength(zone), exists=True):
            cmds.iconTextRadioButton(_zone_seg(zone, state), edit=True, select=True)
            cmds.floatField(_zone_strength(zone), edit=True, value=float(strength))
    s = remembered()
    s["zones"] = dict(zones)
    remember(rd.settings(s))
    values()
    refresh()
    return status("%s: %s" % (rd.plan.PRESETS[name][0], zones_text(zones)))


def zones_text(zones):
    """"Torso Follow 0.5, Head ..., Leg R Anim"."""
    parts = []
    for zone in rd.plan.ZONES:
        state, strength = zones[zone]
        parts.append("%s %s%s" % (rd.plan.ZONE_LABEL[zone], rd.plan.STATE_LABEL[state],
                                  " %.1f" % strength if state == "follow" else ""))
    return ", ".join(parts)


def _slider_row(key, label, low, high, step, s):
    import maya_hubstyle as hubstyle
    cmds.floatSliderGrp(_slider(key), label=label, field=True, minValue=low, maxValue=high,
                        fieldMinValue=low, fieldMaxValue=high * 10, step=step,
                        precision=0 if step >= 1 else 2, value=float(s[key]),
                        columnWidth3=hubstyle.pick((92, 44, 100), (100, 50, 150)),
                        adjustableColumn=3, height=hubstyle.height("small", 22),
                        annotation=TIPS[key], changeCommand=_changed)


def _segments(collection, rows, selected, tip_of, height):
    """A segment row of `rows` [(name, label, key)] in `collection`."""
    import maya_hubstyle as hubstyle
    segments = cmds.rowLayout(numberOfColumns=len(rows),
                              columnAttach=[(i + 1, "both", 1) for i in range(len(rows))])
    hubstyle.mark(segments, "segments", layout=True)
    cmds.iconTextRadioCollection(collection)
    for name, label, key in rows:
        hubstyle.mark(cmds.iconTextRadioButton(
            name, style="textOnly", label=label, height=hubstyle.height("segment", height),
            select=key == selected, collection=collection, annotation=tip_of(key),
            onCommand=_changed), "segment")
    cmds.setParent("..")


def _zone_row(zone, state, strength):
    import maya_hubstyle as hubstyle
    cmds.rowLayout(numberOfColumns=3, adjustableColumn=2,
                   columnWidth3=(hubstyle.pick(48, 64), 110, hubstyle.pick(44, 50)),
                   columnAlign3=("left", "left", "right"),
                   columnAttach=[(1, "left", 0), (2, "both", 4), (3, "right", 0)])
    hubstyle.mark(cmds.text(label=rd.plan.ZONE_LABEL[zone], font="boldLabelFont"), "label")
    _segments(_zone_tabs(zone), [(_zone_seg(zone, n), rd.plan.STATE_LABEL[n], n)
                                 for n in rd.plan.STATES], state, lambda k: TIPS[k], 22)
    cmds.floatField(_zone_strength(zone), value=float(strength), minValue=0.0, maxValue=1.0,
                    precision=2, step=0.05, width=hubstyle.pick(44, 50),
                    height=hubstyle.height("small", 22), annotation=TIPS["zone_strength"],
                    changeCommand=_changed)
    cmds.setParent("..")


def build_panel():
    """The card into the current layout."""
    import maya_hubstyle as hubstyle
    s = remembered()
    column = cmds.columnLayout(adjustableColumn=True, rowSpacing=hubstyle.row_spacing(6),
                               columnOffset=("both", hubstyle.pick(0, 8)))
    hubstyle.mark(cmds.text(SUBTITLE, label=rd.NOTHING, align="left"), "subtitle")
    _segments(MODE_TABS, [(_mode(k), label, k) for k, label in MODES], s["mode"],
              lambda _k: TIPS["mode"], 24)
    for row in SLIDERS:
        _slider_row(*(row + (s,)))
    # Fall's own: the muscles and the weapon
    cmds.columnLayout(FALL_BOX, adjustableColumn=True, rowSpacing=hubstyle.row_spacing(6))
    for row in FALL_SLIDERS:
        _slider_row(*(row + (s,)))
    if hubstyle.skinning():
        hubstyle.mark(cmds.flowLayout(wrap=True, columnSpacing=3), "flow", layout=True)
    else:
        cmds.rowLayout(numberOfColumns=1)
    hubstyle.mark(cmds.checkBox(DROP_CHIP, label="Drop weapon", value=bool(s["drop_weapon"]),
                                annotation=TIPS["drop"], changeCommand=_changed), "chip")
    cmds.setParent("..")
    cmds.setParent("..")
    # Blend's own: the presets, the six zones, the ease in and out
    cmds.columnLayout(BLEND_BOX, adjustableColumn=True, rowSpacing=hubstyle.row_spacing(4))
    hubstyle.mark(cmds.rowLayout(numberOfColumns=len(rd.plan.PRESETS),
                                 columnAttach=[(i + 1, "both", 1)
                                               for i in range(len(rd.plan.PRESETS))]),
                  "fill", layout=True)
    for name, (label, _zones) in rd.plan.PRESETS.items():
        hubstyle.mark(cmds.button(_preset_btn(name), label=label,
                                  height=hubstyle.height("small", 24), annotation=TIPS["preset"],
                                  command=lambda *_a, n=name: apply_preset(n)), "tool")
    cmds.setParent("..")
    for zone in rd.plan.ZONES:
        _zone_row(zone, *s["zones"][zone])
    for row in BLEND_SLIDERS:
        _slider_row(*(row + (s,)))
    cmds.setParent("..")
    _segments(LAYER_TABS, [(_tab(k), label, k) for k, label in LAYERS], s["layer"],
              lambda _k: TIPS["layer"], 24)
    hubstyle.mark(cmds.rowLayout(numberOfColumns=3, adjustableColumn=2,
                                 columnAttach=[(1, "both", 0), (2, "both", 0), (3, "both", 0)]),
                  "fill", layout=True)
    hubstyle.mark(cmds.button(IMPULSE_BTN, label="+ Impulse", height=hubstyle.height("button", 28),
                              annotation=TIPS["impulse"], command=lambda *_: press_impulse()),
                  "secondary", "plus")
    hubstyle.mark(cmds.button(FALL_BTN, label="Fall", height=hubstyle.height("button", 28),
                              annotation=TIPS["fall"], command=lambda *_: press_fall()),
                  "primary", "skull")
    hubstyle.mark(cmds.button(BLEND_BTN, label="Blend", height=hubstyle.height("button", 28),
                              annotation=TIPS["blend"], command=lambda *_: press_blend()),
                  "primary", "wave-sine")
    cmds.setParent("..")
    hubstyle.mark(cmds.text(STATUS, label="", align="left", wordWrap=True, height=54), "status")
    cmds.setParent("..")
    show_mode(s["mode"])
    start()
    refresh()
    return column


def _card_key():
    import maya_hubcopy as hubcopy
    scope = hubcopy.current()
    return "" if scope is None else scope.tag


def start():
    """This card's own jobs (a popup copy's die with the copy): the selection and the time."""
    import maya_hubcopy as hubcopy
    standing = set(scope.tag for scope in hubcopy.live())
    for key in [k for k in JOB if k and k not in standing]:
        del JOB[key]
    for old in JOB.pop(_card_key(), []):
        try:
            if cmds.scriptJob(exists=old):
                cmds.scriptJob(kill=old, force=True)
        except Exception:                                  # noqa: BLE001
            pass
    jobs = []
    for event in ("SelectionChanged", "timeChanged"):
        try:
            jobs.append(cmds.scriptJob(event=[event, refresh], parent=STATUS))
        except Exception:                                  # noqa: BLE001
            pass
    JOB[_card_key()] = jobs


def is_open():
    return bool(cmds.text(STATUS, exists=True))


def show_window():
    """The hub, on the Ragdoll section."""
    import maya_hub
    return maya_hub.show(HUB_SECTION)
