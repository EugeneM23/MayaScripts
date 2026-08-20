"""
Maya Animation Overshoot Tool

Turns a pose key into the extreme of an overshoot: the object goes past the
pose by a share of the move that arrived, then settles back onto it. Works on
any pose in the clip, not only the last key -- select the keys, or stand on the
frame, and press a shape.

Design and the reasoning behind every number:
docs/superpowers/specs/2026-08-20-overshoot-redesign-design.md

Run in Maya Script Editor (Python tab), or:
    import sys; sys.path.append(r"C:/!!!Work/MayaScripts")
    import maya_overshoot; maya_overshoot.show_overshoot_ui()
"""

import collections
import math

import maya.cmds as cmds


# ---------------------------------------------------------------------------
#  Shapes -- pure, no Maya
# ---------------------------------------------------------------------------

Key = collections.namedtuple("Key", "time value tangent")

TAN_FLAT = "flat"        # a turning point: zero velocity, so flat is correct
TAN_LINEAR = "linear"    # a bounce contact: the corner is the impact
TAN_COPY = "copy"        # the arrival: keep whatever the animator shaped

SHAPES = {
    "Snap":    {"family": "spring", "swings": 1, "ratio": 0.30},
    "Spring":  {"family": "spring", "swings": 3, "ratio": 0.30},
    "Elastic": {"family": "spring", "swings": 6, "ratio": 0.60},
    "Recoil":  {"family": "spring", "swings": 2, "ratio": 0.15},
    "Bounce":  {"family": "bounce", "restitution": 0.50},
}
SHAPE_ORDER = list(SHAPES)

GROUPS = collections.OrderedDict((
    ("pos", ("translateX", "translateY", "translateZ")),
    ("rot", ("rotateX", "rotateY", "rotateZ")),
))

MAX_ARCS = 4
EPSILON = 1e-4


def spring_value(u, swings, ratio):
    """A spring released from rest at 1.0, settling on 0.0 at u = 1.

    f(u) = e^-ku (cos(pi c u) + k/(pi c) sin(pi c u)),  k = -c ln r

    f(0) = 1 and f'(0) = 0 -- it leaves the extreme the way an extreme is
    left. Its derivative is -e^-ku (k^2 + a^2)/a sin(a u), a = pi c, which is
    zero only at u = i/c: those are the only turning points, and that is why
    keying them is enough.
    """
    swings = int(swings)
    a = math.pi * swings
    k = 0.0 if ratio >= 1.0 else -swings * math.log(ratio)
    return math.exp(-k * u) * (math.cos(a * u) + (k / a) * math.sin(a * u))


def spring_extremes(swings, ratio):
    """The turning points as (u, value): evenly spaced, geometric, alternating."""
    swings = int(swings)
    return [(i / float(swings), (-1.0) ** i * ratio ** i)
            for i in range(swings + 1)]


def bounce_extremes(restitution, min_height=0.02):
    """A ball dropped onto the pose, as (u, value, kind).

    Apex i is at height e^(2i) and the fall times go as sqrt(h), so arc i
    lasts 2 d e^i where d is the first fall. Contacts therefore close in
    geometrically, which is the whole difference between a bounce and a
    metronome.
    """
    arcs = 0
    while arcs < MAX_ARCS and restitution ** (2 * (arcs + 1)) > min_height:
        arcs += 1

    span = 1.0 + 2.0 * sum(restitution ** i for i in range(1, arcs + 1))
    d = 1.0 / span

    out = [(0.0, 1.0, "apex")]
    t = d
    out.append((t, 0.0, "contact"))
    for i in range(1, arcs + 1):
        half = d * restitution ** i
        out.append((t + half, restitution ** (2 * i), "apex"))
        t += 2.0 * half
        out.append((t, 0.0, "contact"))
    # the series sums to 1 by construction; say so exactly
    out[-1] = (1.0, 0.0, "contact")
    return out


def _round(x):
    """Half-up, so a bounce contact at 4.5 does not land on 4."""
    return math.floor(x + 0.5)


def plan_overshoot(pose_time, pose_value, prev_time, prev_value,
                   next_time=None, next_value=None,
                   amount=0.15, frames=12, shape="Spring",
                   swings=None, ratio=None, restitution=None,
                   peak_delay=0, epsilon=EPSILON):
    """Plan one channel's overshoot as OFFSETS from the base curve.

    Returns (keys, note). An empty key list with a note means the channel was
    skipped, and the note says why. Pure: everything it needs about the scene
    is in the arguments.
    """
    if prev_time is None:
        return [], "no previous key"

    delta = pose_value - prev_value
    if abs(delta) < epsilon:
        return [], "no move into the pose"

    if next_value is not None:
        forward = next_value - pose_value
        if abs(forward) > epsilon and (forward > 0) == (delta > 0):
            return [], "not a stop (the move continues past it)"

    preset = SHAPES.get(shape) or SHAPES["Spring"]
    family = preset["family"]
    if swings is None:
        swings = preset.get("swings", 3)
    if ratio is None:
        ratio = preset.get("ratio", 0.3)
    if restitution is None:
        restitution = preset.get("restitution", 0.5)

    notes = []
    peak_time = pose_time + peak_delay

    if next_time is not None:
        room = next_time - 1 - peak_time
        if room < 1:
            return [], "no room before the next key"
        if frames > room:
            frames = room
            notes.append("shortened to %d frames" % frames)

    if family == "bounce":
        shape_keys = [(u, v, TAN_LINEAR if k == "contact" else TAN_FLAT)
                      for u, v, k in bounce_extremes(restitution)]
    else:
        swings = int(swings)
        if swings > frames:
            swings = max(1, int(frames))
            notes.append("swings reduced to %d" % swings)
        shape_keys = [(u, v, TAN_FLAT) for u, v in spring_extremes(swings, ratio)]

    amplitude = amount * abs(delta) * (1.0 if delta > 0 else -1.0)

    # times collapse onto one frame in a tight window; the bigger excursion wins
    merged = collections.OrderedDict()
    for u, v, tangent in shape_keys:
        t = peak_time + _round(u * frames)
        value = amplitude * v
        if t in merged and abs(merged[t].value) >= abs(value):
            continue
        merged[t] = Key(t, value, tangent)

    keys = sorted(merged.values(), key=lambda k: k.time)
    # the settle lands on the pose exactly, whatever the decay had left
    keys[-1] = Key(keys[-1].time, 0.0, TAN_FLAT)
    keys.insert(0, Key(prev_time, 0.0, TAN_COPY))

    return keys, ", ".join(notes)


def plan_window(keys):
    """The span the plan writes into, or None for an empty plan."""
    if not keys:
        return None
    return (keys[0].time, keys[-1].time)


def as_absolute(keys, pose_value, prev_value):
    """The same plan as values for a base curve instead of offsets for a layer.

    The first key is the arrival, which sits on the previous key's own value;
    every other key is the pose plus its offset.
    """
    if not keys:
        return []
    out = [Key(keys[0].time, prev_value + keys[0].value, keys[0].tangent)]
    out.extend(Key(k.time, pose_value + k.value, k.tangent) for k in keys[1:])
    return out


# ---------------------------------------------------------------------------
#  Reading the scene
# ---------------------------------------------------------------------------

def base_curve(plug):
    """The animCurve holding the animator's own animation for this plug.

    With anim layers in the scene the plug's direct input is a blend node, so
    ask the root (BaseAnimation) layer first and fall back to the plain case.
    """
    root = cmds.animLayer(query=True, root=True)
    if root:
        found = cmds.animLayer(root, query=True, findCurveForPlug=plug) or []
        if found:
            return found[0]
    found = cmds.listConnections(plug, source=True, destination=False,
                                 type="animCurve") or []
    return found[0] if found else None


def curve_keys(curve):
    """(times, values) of an animCurve, or ([], []) for a curve with none."""
    times = cmds.keyframe(curve, query=True, timeChange=True) or []
    values = cmds.keyframe(curve, query=True, valueChange=True) or []
    return times, values


def neighbours(times, values, pose_time):
    """(pose_value, prev_time, prev_value, next_time, next_value) around a key.

    None for pose_value when the channel has no key at that time at all.
    """
    index = None
    for i, t in enumerate(times):
        if abs(t - pose_time) < 1e-6:
            index = i
            break
    if index is None:
        return (None, None, None, None, None)
    prev_time = times[index - 1] if index > 0 else None
    prev_value = values[index - 1] if index > 0 else None
    next_time = times[index + 1] if index + 1 < len(times) else None
    next_value = values[index + 1] if index + 1 < len(times) else None
    return (values[index], prev_time, prev_value, next_time, next_value)


def selected_key_times(obj, attr):
    return sorted(set(cmds.keyframe(obj, attribute=attr, query=True,
                                    selected=True, timeChange=True) or []))


def key_at_or_before(times, now):
    earlier = [t for t in times if t <= now + 1e-6]
    return max(earlier) if earlier else None


# ---------------------------------------------------------------------------
#  Writing
# ---------------------------------------------------------------------------

def layer_for(obj, group):
    """The additive layer holding this object's overshoots for this group.

    Additive, so a layer with no keys is zero offset and the base animation
    passes through untouched -- no weight curve, nothing to gate.
    """
    name = "%s_overshoot_%s" % (obj.split("|")[-1].replace(":", "_"), group)
    if cmds.animLayer(name, query=True, exists=True):
        return name
    return cmds.animLayer(name)          # additive is the default; keep it


def _apply_tangents(curve, keys, source_curve):
    for k in keys:
        at = (k.time, k.time)
        if k.tangent == TAN_COPY:
            itt = ott = None
            if source_curve:
                got_i = cmds.keyTangent(source_curve, time=at, query=True,
                                        inTangentType=True) or []
                got_o = cmds.keyTangent(source_curve, time=at, query=True,
                                        outTangentType=True) or []
                itt = got_i[0] if got_i else None
                ott = got_o[0] if got_o else None
            if itt and ott:
                cmds.keyTangent(curve, time=at, inTangentType=itt,
                                outTangentType=ott)
            continue
        cmds.keyTangent(curve, time=at, inTangentType=k.tangent,
                        outTangentType=k.tangent)


def merge_plans(plans, use_layer=True):
    """Several poses on one channel, in time order, into one key list.

    Adjacent poses share a frame: the later pose's arrival key sits exactly on
    the earlier pose's extreme. The arrival is the one that gives way -- the
    curve is already where it needs to be there, and writing a zero would
    flatten the extreme the animator just asked for.

    `plans` is [(keys, pose_value, prev_value)]; the values come out as layer
    offsets, or as absolute curve values when `use_layer` is False.
    """
    merged = collections.OrderedDict()
    for keys, pose_value, prev_value in plans:
        for i, k in enumerate(keys):
            arrival = (i == 0)
            if k.time in merged:
                if arrival or abs(merged[k.time][1]) >= abs(k.value):
                    continue
            base = prev_value if arrival else pose_value
            value = k.value if use_layer else base + k.value
            merged[k.time] = (Key(k.time, value, k.tangent), k.value)
    return [item[0] for item in
            sorted(merged.values(), key=lambda item: item[0].time)]


def write_channel(obj, attr, plans, layer=None):
    """Put every plan for one channel into the scene, in one pass."""
    plug = "%s.%s" % (obj, attr)
    source = base_curve(plug)
    keys = merge_plans(plans, use_layer=bool(layer))
    if not keys:
        return None

    if layer:
        cmds.animLayer(layer, edit=True, attribute=plug)
        existing = cmds.animLayer(layer, query=True,
                                  findCurveForPlug=plug) or []
        if existing:
            cmds.cutKey(existing[0], time=(keys[0].time, keys[-1].time),
                        clear=True)
        for k in keys:
            cmds.setKeyframe(obj, attribute=attr, time=k.time, value=k.value,
                             animLayer=layer)
        target = (cmds.animLayer(layer, query=True,
                                 findCurveForPlug=plug) or [None])[0]
    else:
        # a previous run's settle keys, per plan -- never the arrival, and
        # never a stretch of the animator's own curve between two poses
        for plan_keys, _, _ in plans:
            cmds.cutKey(source, time=(plan_keys[1].time + 0.001,
                                      plan_keys[-1].time + 0.001), clear=True)
        for k in keys:
            cmds.setKeyframe(obj, attribute=attr, time=k.time, value=k.value)
        target = base_curve(plug)

    if target:
        _apply_tangents(target, keys, source)
    return target


# ---------------------------------------------------------------------------
#  The press
# ---------------------------------------------------------------------------

def overshoot_objects(objects, shape="Spring", do_pos=True, do_rot=False,
                      amount_pos=0.15, frames_pos=12,
                      amount_rot=0.15, frames_rot=12,
                      swings=None, ratio=None, restitution=None,
                      peak_delay=0, use_layer=True):
    """Overshoot every pose the selection points at. Returns a report string."""
    plan_of = collections.OrderedDict()
    skipped = []
    notes = []
    any_selected = False

    for obj in objects:
        for group, attrs in GROUPS.items():
            if group == "pos" and not do_pos:
                continue
            if group == "rot" and not do_rot:
                continue
            for attr in attrs:
                if selected_key_times(obj, attr):
                    any_selected = True

    now = cmds.currentTime(query=True)

    for obj in objects:
        for group, attrs in GROUPS.items():
            if group == "pos" and not do_pos:
                continue
            if group == "rot" and not do_rot:
                continue
            amount = amount_pos if group == "pos" else amount_rot
            frames = frames_pos if group == "pos" else frames_rot
            for attr in attrs:
                plug = "%s.%s" % (obj, attr)
                curve = base_curve(plug)
                if not curve:
                    continue
                times, values = curve_keys(curve)
                if len(times) < 2:
                    continue

                if any_selected:
                    poses = selected_key_times(obj, attr)
                else:
                    at = key_at_or_before(times, now)
                    poses = [at] if at is not None else []

                for pose_time in poses:
                    (pose_value, prev_time, prev_value,
                     next_time, next_value) = neighbours(times, values, pose_time)
                    if pose_value is None:
                        skipped.append("%s.%s@%g no key there"
                                       % (obj.split("|")[-1], attr, pose_time))
                        continue
                    keys, note = plan_overshoot(
                        pose_time, pose_value, prev_time, prev_value,
                        next_time=next_time, next_value=next_value,
                        amount=amount, frames=frames, shape=shape,
                        swings=swings, ratio=ratio, restitution=restitution,
                        peak_delay=peak_delay)
                    if not keys:
                        skipped.append("%s.%s@%g %s"
                                       % (obj.split("|")[-1], attr,
                                          pose_time, note))
                        continue
                    if note:
                        notes.append(note)
                    plan_of.setdefault((obj, group, attr), []).append(
                        (keys, pose_value, prev_value))

    if not plan_of:
        return "nothing to overshoot: " + ("; ".join(skipped[:4]) or "no keys")

    auto = cmds.autoKeyframe(query=True, state=True)
    cmds.autoKeyframe(state=False)
    cmds.undoInfo(openChunk=True, chunkName="overshoot")
    try:
        layers = {}
        poses = 0
        for (obj, group, attr), plans in plan_of.items():
            layer = None
            if use_layer:
                layer = layers.get((obj, group)) or layer_for(obj, group)
                layers[(obj, group)] = layer
            write_channel(obj, attr, plans, layer=layer)
            poses += len(plans)
    finally:
        cmds.undoInfo(closeChunk=True)
        cmds.autoKeyframe(state=auto)

    end = cmds.playbackOptions(query=True, maxTime=True)
    past = [k.time for plans in plan_of.values() for keys, _, _ in plans
            for k in keys if k.time > end]
    report = "%s on %d channel(s), %d pose(s)" % (shape, len(plan_of), poses)
    if notes:
        report += " (%s)" % "; ".join(sorted(set(notes))[:2])
    if past:
        report += " - %d key(s) past the range end" % len(past)
    if skipped:
        report += " | skipped: " + "; ".join(skipped[:3])
    return report


_LAST_SHAPE = "Spring"


def apply_overshoot(shape="Spring", *_args):
    """The button: read the panel, do it, report on the status line."""
    global _LAST_SHAPE
    _LAST_SHAPE = shape
    objects = cmds.ls(selection=True, long=True) or []
    if not objects:
        return _status("select an animated object")

    report = overshoot_objects(
        objects, shape=shape,
        do_pos=cmds.checkBox("overshootTranslate", query=True, value=True),
        do_rot=cmds.checkBox("overshootRotate", query=True, value=True),
        amount_pos=cmds.floatSliderGrp("overshootTAmount",
                                       query=True, value=True) / 100.0,
        frames_pos=int(cmds.intSliderGrp("overshootTFrames",
                                         query=True, value=True)),
        amount_rot=cmds.floatSliderGrp("overshootRAmount",
                                       query=True, value=True) / 100.0,
        frames_rot=int(cmds.intSliderGrp("overshootRFrames",
                                         query=True, value=True)),
        swings=_advanced_swings(shape),
        ratio=cmds.floatSliderGrp("overshootRatio", query=True, value=True),
        restitution=cmds.floatSliderGrp("overshootRestitution",
                                        query=True, value=True),
        peak_delay=int(cmds.intSliderGrp("overshootPeakDelay",
                                         query=True, value=True)),
        use_layer=not cmds.checkBox("overshootBake", query=True, value=True))
    cmds.select(objects, replace=True)
    return _status(report)


def _advanced_swings(shape):
    """The Swings field, which a bounce has no use for."""
    if SHAPES.get(shape, {}).get("family") == "bounce":
        return None
    return int(cmds.intSliderGrp("overshootSwings", query=True, value=True))


def _status(text):
    if cmds.control("overshootStatus", exists=True):
        cmds.text("overshootStatus", edit=True, label=text)
    cmds.headsUpMessage(text, time=2.5)
    return text


def _run(fn, *args):
    """Failures belong on the status line, not in the Script Editor (trap 20)."""
    try:
        return fn(*args)
    except Exception as exc:                                  # noqa: BLE001
        _status("%s: %s" % (type(exc).__name__, exc))
        raise


# ---------------------------------------------------------------------------
#  UI
# ---------------------------------------------------------------------------

def _preset_press(shape):
    """A type button loads its preset into Advanced, then applies it.

    So the sliders always show what just happened, and the Advanced Apply
    below re-runs the same shape with whatever the animator has changed.
    """
    def go(*_args):
        preset = SHAPES[shape]
        if preset["family"] == "spring":
            cmds.intSliderGrp("overshootSwings", edit=True,
                              value=preset["swings"])
            cmds.floatSliderGrp("overshootRatio", edit=True,
                                value=preset["ratio"])
        else:
            cmds.floatSliderGrp("overshootRestitution", edit=True,
                                value=preset["restitution"])
        _run(apply_overshoot, shape)
    return go


def _custom_press(*_args):
    _run(apply_overshoot, _LAST_SHAPE)


BUTTON_COLOUR = {
    "Snap": (0.45, 0.75, 0.45),
    "Spring": (0.45, 0.65, 0.85),
    "Elastic": (0.55, 0.55, 0.85),
    "Recoil": (0.85, 0.55, 0.45),
    "Bounce": (0.85, 0.75, 0.45),
}


def show_overshoot_ui():
    win_id = "animOvershootWin"

    if cmds.window(win_id, exists=True):
        cmds.deleteUI(win_id)

    cmds.window(win_id, title="Overshoot Tool", widthHeight=(340, 560),
                sizeable=True)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=4,
                      columnOffset=("both", 10))

    cmds.separator(height=8, style="none")
    cmds.text(label="Animation Overshoot", font="boldLabelFont", align="center")
    cmds.text(label="the selected key becomes the extreme",
              font="smallObliqueLabelFont", align="center")
    cmds.separator(height=8, style="in")

    cmds.checkBox("overshootTranslate", label="Translate", value=True)
    cmds.floatSliderGrp("overshootTAmount", label="Amount % ", field=True,
                        minValue=1.0, maxValue=60.0, value=15.0,
                        fieldMinValue=0.1, fieldMaxValue=400.0,
                        columnWidth3=(70, 50, 170))
    cmds.intSliderGrp("overshootTFrames", label="Frames  ", field=True,
                      minValue=2, maxValue=48, value=12,
                      fieldMinValue=1, fieldMaxValue=200,
                      columnWidth3=(70, 50, 170))

    cmds.separator(height=6, style="in")

    cmds.checkBox("overshootRotate", label="Rotate", value=False)
    cmds.floatSliderGrp("overshootRAmount", label="Amount % ", field=True,
                        minValue=1.0, maxValue=60.0, value=15.0,
                        fieldMinValue=0.1, fieldMaxValue=400.0,
                        columnWidth3=(70, 50, 170))
    cmds.intSliderGrp("overshootRFrames", label="Frames  ", field=True,
                      minValue=2, maxValue=48, value=12,
                      fieldMinValue=1, fieldMaxValue=200,
                      columnWidth3=(70, 50, 170))

    cmds.separator(height=8, style="in")
    cmds.text(label="Overshoot type", font="smallBoldLabelFont", align="left")
    for shape in SHAPE_ORDER:
        cmds.button(label=shape, height=28,
                    backgroundColor=BUTTON_COLOUR[shape],
                    command=_preset_press(shape))

    cmds.separator(height=6, style="none")
    cmds.frameLayout("overshootAdvanced", label="Advanced", collapsable=True,
                     collapse=True, marginWidth=4, marginHeight=4)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=3)
    cmds.intSliderGrp("overshootSwings", label="Swings  ", field=True,
                      minValue=1, maxValue=10, value=3,
                      columnWidth3=(70, 50, 150))
    cmds.floatSliderGrp("overshootRatio", label="Keep  ", field=True,
                        minValue=0.05, maxValue=0.9, value=0.30,
                        columnWidth3=(70, 50, 150))
    cmds.floatSliderGrp("overshootRestitution", label="Bounce e ", field=True,
                        minValue=0.2, maxValue=0.8, value=0.50,
                        columnWidth3=(70, 50, 150))
    cmds.intSliderGrp("overshootPeakDelay", label="Peak +  ", field=True,
                      minValue=0, maxValue=8, value=0,
                      columnWidth3=(70, 50, 150))
    cmds.checkBox("overshootBake", label="Bake into curves (no anim layer)",
                  value=False)
    cmds.button(label="Apply with these", height=24, command=_custom_press)
    cmds.setParent("..")
    cmds.setParent("..")

    cmds.separator(height=6, style="in")
    cmds.text("overshootStatus", label="select keys, or stand on the pose",
              align="center", font="smallFixedWidthFont")

    cmds.showWindow(win_id)


if __name__ == "__main__":
    show_overshoot_ui()
