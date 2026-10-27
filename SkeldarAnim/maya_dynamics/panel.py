"""The Dynamics card (2026-10-26): chains kept in the scene, their knobs, colliders, the wind, Simulate.

Top down: the subtitle (what Simulate acts on), the Chains list (multi-select; picking rows selects
their roots and shows the first one's knobs) with + Chain and Remove, the presets, the knob rows
(each a slider and its Tip x field), the Colliders (Auto body, + Sphere, + Capsule, + Floor, and the
selected collider's Radius / Length), the Wind (+ Wind and the arrow's channels at the current
frame), the Bake options (Loop, Pre-roll, Substeps) and Simulate - the one orange.

A released knob writes it into every picked chain and re-solves the ones already baked from the
last reading (`run.simulate(reuse=True)`); Simulate reads the scene afresh. Every press is a module
function reading the card when it is open and what was remembered when it is not, so the hotkey
rows press it with the card closed. A plain `cmds` card under the hub's marks; its jobs per card
(a popup copy's die with it), a hidden card refreshing when it is next shown.
"""

import json

import maya.cmds as cmds

from maya_dynamics import model
from maya_dynamics import run
from maya_dynamics import setup

HUB_SECTION = "dynamics"
SUBTITLE = "skeldarDynamicsSubtitle"
STATUS = "skeldarDynamicsStatus"
CHAINS = "skeldarDynamicsChains"
ADD_BTN = "skeldarDynamicsAddChain"
REMOVE_BTN = "skeldarDynamicsRemove"
SIMULATE_BTN = "skeldarDynamicsSimulate"
LOOP_CHIP = "skeldarDynamicsLoop"
PREROLL = "skeldarDynamicsPreroll"
SUBSTEPS = "skeldarDynamicsSubsteps"
COLLIDER_RADIUS = "skeldarDynamicsColliderRadius"
COLLIDER_LENGTH = "skeldarDynamicsColliderLength"
OPTION = "skeldarDynamics_settings"
WIND_RANGES = dict((attr, (low, high)) for attr, _v, low, high in setup.WIND_CHANNELS)

LABELS = {"stiffness": "Stiffness", "damping": "Damping", "limit": "Limit, deg",
          "gravity": "Gravity, g", "inertia": "Inertia", "wind": "Wind", "radius": "Radius, cm",
          "friction": "Friction"}
TIPS = {
    "stiffness": "How hard each joint is pulled back to where its animation points it (0: none, a "
                 "chain that only hangs)",
    "damping": "The share of a joint's swing lost every 1/30 s (0 rings for long)",
    "limit": "The most a joint may swing off its animated direction",
    "gravity": "Gravity, 1 = 980 cm/s^2 (negative floats up)",
    "inertia": "How much of the character's own travel the chain does NOT feel (1: a run does not "
               "drag it back)",
    "wind": "How much this chain feels the Wind arrow",
    "radius": "Each joint's sphere against the colliders",
    "friction": "Velocity lost along a collider while touching it",
    "tip": "The knob at the chain's last joint: its value times this, the joints between in between",
    "preset": "Sets the picked chains' knobs (their Substeps, Pre-roll and Loop kept)",
    "add": "Every selected node a chain's root: it and, step by step, the one node of its kind below "
           "(a branch ends it). A root already in a chain picks that chain",
    "remove": "The picked chains' layers and setups (their colliders stay)",
    "auto": "Capsules on the selected character's pelvis, spine, head, arms and legs, sized from its "
            "skin, and a floor at its feet - pressed again, replaced",
    "sphere": "A sphere on the selected bone; its Radius below or in the Channel Box",
    "capsule": "A capsule along the selected bone; its Radius and Length below",
    "floor": "A floor at the selected character's lowest point (local Y its normal)",
    "wind_add": "The Wind arrow (local +Z the direction), made in front of the camera",
    "wind_channel": "The Wind arrow's channel at the current frame (keyed there when it has keys)",
    "loop": "The range is one cycle: the chain settles into a loop and its last frame flows into "
            "its first; the curves cycle",
    "preroll": "Frames the simulation runs before the range holding its first frame, so frame one is "
               "settled (not with Loop)",
    "substeps": "Solver steps a frame: more for fast motion or thin colliders",
    "simulate": "Read the animation and bake the picked chains (else the selection's, else every "
                "chain) onto a layer each: Dynamics_<root>. The highlight, else the playback range",
    "collider": "The selected collider's radius / capsule length, cm",
}
JOB = {}
_PICKED = {}                  # card key: [chain UUIDs] the list's picked rows
_ROWS = {}                    # card key: [chain paths] the list's rows


def _slider(key):
    return "skeldarDynamics_" + key


def _tip(key):
    return "skeldarDynamicsTip_" + key


def _preset(name):
    return "skeldarDynamicsPreset_" + name


def _wind_slider(attr):
    return "skeldarDynamicsWind_" + attr


def _card_key():
    import maya_hubcopy as hubcopy
    scope = hubcopy.current()
    return "" if scope is None else scope.tag


# ------------------------------------------------------------------- memory

def remembered():
    """The settings a new chain takes (the card's last ones)."""
    try:
        given = json.loads(cmds.optionVar(query=OPTION)) if cmds.optionVar(exists=OPTION) else None
    except (TypeError, ValueError):
        given = None
    return model.settings(given if isinstance(given, dict) else {})


def remember(s):
    cmds.optionVar(stringValue=(OPTION, json.dumps(model.settings(s), sort_keys=True)))


def is_open():
    return bool(cmds.text(STATUS, exists=True))


def status(text):
    import maya_hubstyle as hubstyle
    if cmds.text(STATUS, exists=True):
        cmds.text(STATUS, edit=True, label=text)
        hubstyle.tell(STATUS, text)
    return text


# ------------------------------------------------------------------- chains

def picked():
    """The chains the card's list picks (long paths); none when the card is closed."""
    uuids = _PICKED.get(_card_key(), [])
    out = []
    for uuid in uuids:
        path = setup._by_uuid(uuid)
        if path and cmds.objExists(path):
            out.append(path)
    return out


def _set_picked(chains):
    _PICKED[_card_key()] = [setup._uuid(c) for c in chains if c]


def acting():
    """The chains a press acts on: the picked ones, else `run.targets()`."""
    return picked() or run.targets()


def subtitle():
    chains = acting()
    if not chains:
        return run.NOTHING
    try:
        first, last, _ranged = run.frame_range(run._highlight(run.SLIDER))
        frames = " over %d-%d" % (first, last)
    except Exception:                                    # noqa: BLE001 - no time slider
        frames = ""
    names = [setup.leaf(setup.root_of(c) or c) for c in chains]
    shown = ", ".join(names[:4]) + (" and %d more" % (len(names) - 4) if len(names) > 4 else "")
    return "Simulate: %s%s" % (shown, frames)


def _fill_list():
    if not cmds.textScrollList(CHAINS, exists=True):
        return
    chains = setup.chains()
    _ROWS[_card_key()] = chains
    cmds.textScrollList(CHAINS, edit=True, removeAll=True)
    for chain in chains:
        cmds.textScrollList(CHAINS, edit=True, append=setup.label(chain))
    wanted = set(picked())
    for index, chain in enumerate(chains):
        if chain in wanted:
            cmds.textScrollList(CHAINS, edit=True, selectIndexedItem=index + 1)


def list_picked(*_):
    """Rows picked in the list: they are the card's chains, their roots selected, the first one's
    knobs shown."""
    indices = cmds.textScrollList(CHAINS, query=True, selectIndexedItem=True) or []
    rows = _ROWS.get(_card_key(), [])
    chains = [rows[i - 1] for i in indices if 0 < i <= len(rows)]
    _set_picked(chains)
    roots = [setup.root_of(c) for c in chains]
    roots = [r for r in roots if r]
    if roots:
        cmds.select(roots, replace=True)
    if chains:
        show_settings(setup.read_settings(chains[0]))
    _subtitle()


def show_settings(s):
    """`s` into the knob rows and the Bake options."""
    for key, *_rest in model.KNOBS:
        if cmds.floatSliderGrp(_slider(key), exists=True):
            cmds.floatSliderGrp(_slider(key), edit=True, value=float(s[key]))
        if cmds.floatField(_tip(key), exists=True):
            cmds.floatField(_tip(key), edit=True, value=float(s[key + "_tip"]))
    if cmds.checkBox(LOOP_CHIP, exists=True):
        cmds.checkBox(LOOP_CHIP, edit=True, value=bool(s["loop"]))
    if cmds.intField(PREROLL, exists=True):
        cmds.intField(PREROLL, edit=True, value=int(s["preroll"]))
    if cmds.intField(SUBSTEPS, exists=True):
        cmds.intField(SUBSTEPS, edit=True, value=int(s["substeps"]))


def card_settings():
    """The settings as the card shows them (remembered when it is closed)."""
    s = remembered()
    for key, *_rest in model.KNOBS:
        if cmds.floatSliderGrp(_slider(key), exists=True):
            s[key] = cmds.floatSliderGrp(_slider(key), query=True, value=True)
        if cmds.floatField(_tip(key), exists=True):
            s[key + "_tip"] = cmds.floatField(_tip(key), query=True, value=True)
    if cmds.checkBox(LOOP_CHIP, exists=True):
        s["loop"] = bool(cmds.checkBox(LOOP_CHIP, query=True, value=True))
    if cmds.intField(PREROLL, exists=True):
        s["preroll"] = cmds.intField(PREROLL, query=True, value=True)
    if cmds.intField(SUBSTEPS, exists=True):
        s["substeps"] = cmds.intField(SUBSTEPS, query=True, value=True)
    return model.settings(s)


def _write(keys, s):
    """`keys` of `s` into every picked chain (and remembered); the baked ones solved again from
    the last reading. The line."""
    remember(s)
    chains = picked()
    if not chains:
        return status("Set for the next chain - pick chains in the list to change theirs")
    for chain in chains:
        mine = setup.read_settings(chain)
        for key in keys:
            mine[key] = s[key]
        setup.write_settings(chain, mine)
    baked = [c for c in chains if setup.layer_of(c)]
    if not baked:
        _fill_list()
        return status("Set on %d chain%s - press Simulate" % (len(chains),
                                                              "" if len(chains) == 1 else "s"))
    return _press(lambda: run.simulate(baked, reuse=True), "Simulate")


def knob_changed(key):
    s = card_settings()
    return _write([key], s)


def tip_changed(key):
    s = card_settings()
    return _write([key + "_tip"], s)


def option_changed(key):
    s = card_settings()
    return _write([key], s)


def apply_preset(name):
    """A preset's knobs into the card and the picked chains."""
    s = card_settings()
    keep = dict((k, s[k]) for k in ("substeps", "preroll", "tip", "loop"))
    s.update(model.PRESETS[name])
    s.update(keep)
    s = model.settings(s)
    show_settings(s)
    keys = [k for k in s if k not in keep]
    return _write(keys, s)


# ------------------------------------------------------------------- presses

def _press(work, name):
    try:
        message = work()
    except Exception as error:                              # noqa: BLE001 - the card stays usable
        import traceback
        print(traceback.format_exc())
        message = "%s failed: %s" % (name, error)
    refresh()
    return status(message)


def press_simulate(*_):
    """Simulate: the picked chains (else the selection's, else every chain), read afresh."""
    def work():
        run.forget()
        return run.simulate(acting())
    return _press(work, "Simulate")


def press_add_chain(*_):
    """+ Chain: every selected node a chain's root, with the card's settings."""
    def work():
        chains, notes, refusal = setup.add_chains(None, card_settings() if is_open() else
                                                  remembered())
        if refusal:
            return refusal
        _set_picked(chains)
        names = ", ".join(setup.leaf(setup.root_of(c) or c) for c in chains)
        line = "Chains: %s - press Simulate" % names
        return line + "".join(" | " + n for n in notes)
    return _press(work, "+ Chain")


def press_remove(*_):
    def work():
        line = run.remove(picked())
        _set_picked([])
        return line
    return _press(work, "Remove")


def _selected():
    return cmds.ls(selection=True, long=True) or []


def press_auto_body(*_):
    def work():
        made, refusal = setup.auto_body(_selected())
        if refusal:
            return refusal
        return "Auto body: %d colliders" % len(made)
    return _press(work, "Auto body")


def _bone_press(kind):
    def work():
        nodes = [n for n in _selected() if cmds.objectType(n, isAType="transform")]
        if not nodes:
            return "select a bone for the %s" % kind
        made = [setup.add_collider(kind, node) for node in nodes]
        cmds.select(made, replace=True)
        return "%s: %s" % (kind.capitalize(), ", ".join(setup.leaf(m) for m in made))
    return _press(work, "+ " + kind.capitalize())


def press_sphere(*_):
    return _bone_press("sphere")


def press_capsule(*_):
    return _bone_press("capsule")


def press_floor(*_):
    def work():
        nodes = _selected()
        floor = setup.add_floor(nodes[0]) if nodes else setup.add_floor(None, height=0.0)
        cmds.select(floor, replace=True)
        return "Floor: %s" % setup.leaf(floor)
    return _press(work, "+ Floor")


def press_wind(*_):
    def work():
        wind = setup.add_wind()
        cmds.select(wind, replace=True)
        return "Wind: the arrow's +Z blows - strength %.2f g" % cmds.getAttr(wind + ".strength")
    return _press(work, "+ Wind")


def collider_changed(attr):
    """The selected colliders' radius or length from the card, redrawn."""
    field = COLLIDER_RADIUS if attr == "radius" else COLLIDER_LENGTH
    value = cmds.floatField(field, query=True, value=True)
    changed = []
    for node in _selected():
        if setup.is_collider(node) and setup._has(node, attr):
            cmds.setAttr(node + "." + attr, max(0.0, value))
            setup.redraw(node)
            changed.append(setup.leaf(node))
    return status("%s %s = %.2f" % (", ".join(changed), attr, value) if changed
                  else "select a collider")


def wind_changed(attr):
    """The Wind arrow's channel at the current frame: keyed there when it has keys."""
    wind = setup.wind()
    if not wind:
        return status("press + Wind first")
    value = cmds.floatSliderGrp(_wind_slider(attr), query=True, value=True)
    plug = wind + "." + attr
    if cmds.keyframe(plug, query=True, keyframeCount=True):
        cmds.setKeyframe(wind, attribute=attr, value=value)
    else:
        cmds.setAttr(plug, value)
    return status("Wind %s %.2f" % (attr, value))


# ------------------------------------------------------------------- refresh

def _subtitle():
    if cmds.text(SUBTITLE, exists=True):
        cmds.text(SUBTITLE, edit=True, label=subtitle())


def _collider_fields():
    colliders = [n for n in _selected() if setup.is_collider(n)]
    shown = colliders[0] if colliders else None
    for field, attr in ((COLLIDER_RADIUS, "radius"), (COLLIDER_LENGTH, "length")):
        if not cmds.floatField(field, exists=True):
            continue
        on = bool(shown) and setup._has(shown, attr) and not (
            attr == "length" and setup.kind_of(shown) == "sphere")
        cmds.floatField(field, edit=True, enable=on)
        if on:
            cmds.floatField(field, edit=True, value=float(cmds.getAttr(shown + "." + attr)))


def _wind_sliders():
    wind = setup.wind()
    for attr, *_rest in setup.WIND_CHANNELS:
        if cmds.floatSliderGrp(_wind_slider(attr), exists=True):
            cmds.floatSliderGrp(_wind_slider(attr), edit=True, enable=bool(wind))
            if wind:
                cmds.floatSliderGrp(_wind_slider(attr), edit=True,
                                    value=float(cmds.getAttr(wind + "." + attr)))


def refresh(*_):
    if not cmds.text(SUBTITLE, exists=True):
        return
    with setup.reading():                    # the chains and the wind looked up once
        _fill_list()
        _subtitle()
        _collider_fields()
        _wind_sliders()


# --------------------------------------------------------------------- build

def _heading(label):
    import maya_hubstyle as hubstyle
    hubstyle.mark(cmds.text(label=label, align="left"), "heading")


def _fill_row(buttons):
    """A row of buttons sharing the card's width: [(name, label, tip, command, role, icon)]."""
    import maya_hubstyle as hubstyle
    hubstyle.mark(cmds.rowLayout(numberOfColumns=len(buttons),
                                 columnAttach=[(i + 1, "both", 1) for i in range(len(buttons))]),
                  "fill", layout=True)
    for name, label, tip, command, role, icon in buttons:
        flags = dict(label=label, height=hubstyle.height("small", 24), annotation=tip,
                     command=command)
        control = cmds.button(name, **flags) if name else cmds.button(**flags)
        if icon:
            hubstyle.mark(control, role, icon)
        else:
            hubstyle.mark(control, role)
    cmds.setParent("..")


def _knob_row(key, low, high, has_tip, s):
    import maya_hubstyle as hubstyle
    step = 1.0 if key == "limit" else 0.01
    cmds.rowLayout(numberOfColumns=2 if has_tip else 1, adjustableColumn=1,
                   columnAttach=[(1, "both", 0)] + ([(2, "right", 0)] if has_tip else []))
    cmds.floatSliderGrp(_slider(key), label=LABELS[key], field=True, minValue=low, maxValue=high,
                        fieldMinValue=low, fieldMaxValue=high, step=step,
                        precision=0 if key == "limit" else 2, value=float(s[key]),
                        columnWidth3=hubstyle.pick((80, 44, 80), (90, 50, 120)),
                        adjustableColumn=3, height=hubstyle.height("small", 22),
                        annotation=TIPS[key], changeCommand=lambda *_a, k=key: knob_changed(k))
    if has_tip:
        cmds.floatField(_tip(key), value=float(s[key + "_tip"]), minValue=model.TIP_LOW,
                        maxValue=model.TIP_HIGH, precision=2, step=0.1,
                        width=hubstyle.pick(42, 48), height=hubstyle.height("small", 22),
                        annotation=TIPS["tip"], changeCommand=lambda *_a, k=key: tip_changed(k))
    cmds.setParent("..")


def build_panel():
    """The card into the current layout."""
    import maya_hubstyle as hubstyle
    s = remembered()
    column = cmds.columnLayout(adjustableColumn=True, rowSpacing=hubstyle.row_spacing(6),
                               columnOffset=("both", hubstyle.pick(0, 8)))
    hubstyle.mark(cmds.text(SUBTITLE, label=run.NOTHING, align="left"), "subtitle")
    _heading("Chains")
    cmds.textScrollList(CHAINS, allowMultiSelection=True, height=hubstyle.pick(84, 90),
                        annotation="Your chains: pick rows to act on them",
                        selectCommand=list_picked)
    _fill_row([(ADD_BTN, "+ Chain", TIPS["add"], press_add_chain, "secondary", "plus"),
               (REMOVE_BTN, "Remove", TIPS["remove"], press_remove, "danger", "trash")])
    _fill_row([(_preset(name), model.PRESET_LABELS[name], TIPS["preset"],
                lambda *_a, n=name: apply_preset(n), "tool", None) for name in model.PRESETS])
    tip_of = dict((key, tip is not None) for key, _l, _h, _d, tip in model.KNOBS)
    for key, low, high, _default, _tip_default in model.KNOBS:
        _knob_row(key, low, high, tip_of[key], s)
    _heading("Colliders")
    _fill_row([(None, "Auto body", TIPS["auto"], press_auto_body, "tool", None),
               (None, "+ Sphere", TIPS["sphere"], press_sphere, "tool", None),
               (None, "+ Capsule", TIPS["capsule"], press_capsule, "tool", None),
               (None, "+ Floor", TIPS["floor"], press_floor, "tool", None)])
    cmds.rowLayout(numberOfColumns=4, adjustableColumn=4,
                   columnAttach=[(1, "left", 0), (2, "both", 2), (3, "left", 6), (4, "both", 2)])
    hubstyle.mark(cmds.text(label="Radius", align="left"), "label")
    cmds.floatField(COLLIDER_RADIUS, value=setup.DEFAULT_RADIUS, minValue=0.0, precision=2,
                    width=hubstyle.pick(56, 60), enable=False, annotation=TIPS["collider"],
                    changeCommand=lambda *_a: collider_changed("radius"))
    hubstyle.mark(cmds.text(label="Length", align="left"), "label")
    cmds.floatField(COLLIDER_LENGTH, value=0.0, minValue=0.0, precision=2,
                    width=hubstyle.pick(56, 60), enable=False, annotation=TIPS["collider"],
                    changeCommand=lambda *_a: collider_changed("length"))
    cmds.setParent("..")
    _heading("Wind")
    _fill_row([(None, "+ Wind", TIPS["wind_add"], press_wind, "tool", "wind")])
    for attr, default, low, high in setup.WIND_CHANNELS:
        cmds.floatSliderGrp(_wind_slider(attr), label=attr.capitalize(), field=True,
                            minValue=low, maxValue=min(high, 4.0 if attr != "frequency" else 5.0),
                            fieldMinValue=low, fieldMaxValue=high, step=0.01, precision=2,
                            value=default, columnWidth3=hubstyle.pick((80, 44, 80), (90, 50, 120)),
                            adjustableColumn=3, height=hubstyle.height("small", 22),
                            enable=False, annotation=TIPS["wind_channel"],
                            changeCommand=lambda *_a, a=attr: wind_changed(a))
    _heading("Bake")
    cmds.rowLayout(numberOfColumns=5, adjustableColumn=1,
                   columnAttach=[(1, "left", 0), (2, "right", 2), (3, "both", 2),
                                 (4, "right", 2), (5, "both", 2)])
    hubstyle.mark(cmds.checkBox(LOOP_CHIP, label="Loop", value=bool(s["loop"]),
                                annotation=TIPS["loop"],
                                changeCommand=lambda *_a: option_changed("loop")), "chip")
    hubstyle.mark(cmds.text(label="Pre-roll", align="right"), "label")
    cmds.intField(PREROLL, value=int(s["preroll"]), minValue=0, maxValue=model.MAX_PREROLL,
                  width=hubstyle.pick(42, 48), annotation=TIPS["preroll"],
                  changeCommand=lambda *_a: option_changed("preroll"))
    hubstyle.mark(cmds.text(label="Substeps", align="right"), "label")
    cmds.intField(SUBSTEPS, value=int(s["substeps"]), minValue=1, maxValue=model.MAX_SUBSTEPS,
                  width=hubstyle.pick(36, 42), annotation=TIPS["substeps"],
                  changeCommand=lambda *_a: option_changed("substeps"))
    cmds.setParent("..")
    hubstyle.mark(cmds.button(SIMULATE_BTN, label="Simulate", height=hubstyle.height("button", 28),
                              annotation=TIPS["simulate"], command=press_simulate),
                  "primary", "wind")
    hubstyle.mark(cmds.text(STATUS, label="", align="left", wordWrap=True, height=54), "status")
    cmds.setParent("..")
    start()
    refresh()
    return column


def start():
    """This card's own jobs (a popup copy's die with the copy): the selection, undo and redo."""
    import maya_hubcopy as hubcopy
    import maya_hubqt
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
    for event in ("SelectionChanged", "Undo", "Redo"):
        try:
            jobs.append(cmds.scriptJob(event=[event, maya_hubqt.seen_only(STATUS, refresh)],
                                       parent=STATUS))
        except Exception:                                  # noqa: BLE001
            pass
    JOB[_card_key()] = jobs


def show_window():
    """The hub, on the Dynamics section."""
    import maya_hub
    return maya_hub.show(HUB_SECTION)
