"""
Maya Animation Overshoot Tool

Builds the STOP of a move: the object carries on past its pose key with the
speed the move had, and settles back onto the pose. The pose itself never
moves -- everything the tool writes starts at the pose key and comes back to
it. Works on any pose in the clip, not only the last key: select the keys, or
stand on the frame, and press a shape.

The speed comes from the two keys of the arriving move, `delta / frames`, not
from a one-frame difference at the pose key -- an eased arrival has almost no
speed left there, which is why the amount used to collapse on exactly the
poses that were sold hardest.

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

Key = collections.namedtuple("Key", "time value tangent slope")
Key.__new__.__defaults__ = (None,)

TAN_FLAT = "flat"        # a turning point: zero velocity, so flat is correct
TAN_LINEAR = "linear"    # a bounce contact: the corner is the impact
TAN_SLOPE = "slope"      # the pose key: leaves at the speed of the move

#  `frames` is part of the character, not a separate taste: leaving the pose at
#  a fixed speed means the excursion is set by how long the settle lasts, so a
#  single slow swing travels furthest. Without a per-shape length, pressing
#  Snap at Spring's 12 frames gives three times Spring's overshoot. These four
#  numbers put every preset in the same size range for the same move.
SHAPES = collections.OrderedDict((
    ("Snap", {"family": "sine", "swings": 1, "ratio": 0.30, "frames": 5}),
    ("Spring", {"family": "sine", "swings": 3, "ratio": 0.30, "frames": 12}),
    ("Elastic", {"family": "sine", "swings": 6, "ratio": 0.60, "frames": 16}),
    ("Recoil", {"family": "sine", "swings": 2, "ratio": 0.15, "frames": 8}),
    ("Bounce", {"family": "bounce", "restitution": 0.50, "frames": 7}),
))
SHAPE_ORDER = list(SHAPES)

GROUPS = collections.OrderedDict((
    ("pos", ("translateX", "translateY", "translateZ")),
    ("rot", ("rotateX", "rotateY", "rotateZ")),
))

MAX_ARCS = 4
EPSILON = 1e-4
MAX_SHARE = 2.0          # an overshoot wider than twice the move is a mistake


def _decay(swings, ratio):
    """k, from the share of itself each swing keeps."""
    if ratio >= 1.0:
        return 0.0
    return -swings * math.log(ratio)


def sine_raw(u, swings, ratio):
    """sin(pi c u) e^-ku: zero at the pose, and it comes back to zero at u=1."""
    return (math.sin(math.pi * swings * u) *
            math.exp(-_decay(swings, ratio) * u))


def sine_first_extreme(swings, ratio):
    """Where the first crest is, in u.

    raw' = 0 gives tan(pi c u) = pi c / k, so the crests are one half period
    apart from there on -- and with k = 0 it is the quarter period, which is
    the undamped answer.
    """
    a = math.pi * swings
    k = _decay(swings, ratio)
    if k <= 0.0:
        return 0.5 / swings
    return math.atan(a / k) / a


def sine_peak(swings, ratio):
    return sine_raw(sine_first_extreme(swings, ratio), swings, ratio)


def sine_value(u, swings, ratio):
    """The shape as the keys mean it: peak exactly 1.0, zero at both ends."""
    return sine_raw(u, swings, ratio) / sine_peak(swings, ratio)


def sine_extremes(swings, ratio):
    """The crests as (u, value): a half period apart, geometric, alternating.

    Consecutive crests are 1/c apart, so each is exactly `ratio` of the last.
    """
    first = sine_first_extreme(swings, ratio)
    peak = sine_peak(swings, ratio)
    out = []
    for i in range(int(swings)):
        u = first + i / float(swings)
        if u >= 1.0:
            break
        out.append((u, (-1.0) ** i * ratio ** i))
    return out


def sine_entry_slope(swings, ratio):
    """d/du of the unit-peak shape at the pose. raw'(0) is pi c."""
    return math.pi * swings / sine_peak(swings, ratio)


def bounce_extremes(restitution, min_height=0.02):
    """A ball thrown off the pose, as (u, value, kind).

    Arc 0 is the object leaving the pose at the speed of the move and being
    pulled back to it; then it bounces, keeping e of its speed and so e^2 of
    its height, and the arcs shorten by e. That geometric shortening is the
    whole difference between a bounce and a metronome.
    """
    arcs = 0
    while arcs < MAX_ARCS - 1 and restitution ** (2 * (arcs + 1)) > min_height:
        arcs += 1

    span = sum(restitution ** i for i in range(arcs + 1))
    d = 1.0 / span

    out = []
    t = 0.0
    for i in range(arcs + 1):
        step = d * restitution ** i
        out.append((t + step * 0.5, restitution ** (2 * i), "apex"))
        t += step
        out.append((t, 0.0, "contact"))
    out[-1] = (1.0, 0.0, "contact")
    return out


def bounce_entry_slope(restitution, min_height=0.02):
    """d/du at the launch: a parabola of height h over d has slope 4h/d."""
    ext = bounce_extremes(restitution, min_height)
    first_apex_u = ext[0][0]
    return 4.0 * 1.0 / (2.0 * first_apex_u)


def _round(x):
    """Half-up, so a bounce contact at 4.5 does not land on 4."""
    return int(math.floor(x + 0.5))


def plan_overshoot(pose_time, pose_value, prev_time, prev_value,
                   next_time=None, next_value=None,
                   strength=1.0, frames=12, shape="Spring",
                   swings=None, ratio=None, restitution=None,
                   epsilon=EPSILON, max_share=MAX_SHARE):
    """Plan one channel's overshoot as OFFSETS from the base curve.

    The first key is the pose itself at offset zero, and the last key returns
    to zero: the pose the animator set is never moved. Returns (keys, note);
    an empty list with a note means the channel was skipped and why. Pure --
    everything it needs about the scene is in the arguments.
    """
    if prev_time is None:
        return [], "no previous key"

    delta = pose_value - prev_value
    if abs(delta) < epsilon:
        return [], "no move into the pose"

    span = float(pose_time - prev_time)
    if span <= 0.0:
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
    if next_time is not None:
        room = next_time - 1 - pose_time
        if frames > room:
            frames = room
            notes.append("shortened to %d frames" % frames)
    frames = int(frames)
    if frames < 2:
        return [], "no room before the next key"

    if family == "bounce":
        shape_keys = [(u, v, TAN_LINEAR if k == "contact" else TAN_FLAT)
                      for u, v, k in bounce_extremes(restitution)]
        entry = bounce_entry_slope(restitution)
    else:
        swings = int(swings)
        if swings > frames:
            swings = max(1, frames)
            notes.append("swings reduced to %d" % swings)
        shape_keys = [(u, v, TAN_FLAT) for u, v in sine_extremes(swings, ratio)]
        shape_keys.append((1.0, 0.0, TAN_FLAT))
        entry = sine_entry_slope(swings, ratio)

    #  the speed of the move, and the excursion that leaves the pose at it
    speed = abs(delta) / span
    amplitude = strength * speed * frames / entry
    share = amplitude / abs(delta)
    if share > max_share:
        amplitude = max_share * abs(delta)
        notes.append("clamped to %g x the move" % max_share)
    direction = 1.0 if delta > 0 else -1.0
    amplitude *= direction
    slope = amplitude * entry / frames

    keys = [Key(pose_time, 0.0, TAN_SLOPE, slope)]
    for u, v, tangent in shape_keys[:-1]:
        t = max(pose_time + _round(u * frames), keys[-1].time + 1)
        if t >= pose_time + frames:
            break
        keys.append(Key(t, amplitude * v, tangent))
    keys.append(Key(pose_time + frames, 0.0, TAN_FLAT))

    return keys, ", ".join(notes)


def plan_window(keys):
    """The span the plan writes into, or None for an empty plan."""
    if not keys:
        return None
    return (keys[0].time, keys[-1].time)


def peak_of(keys):
    """The largest excursion in a plan, as (time, value)."""
    if not keys:
        return None
    key = max(keys, key=lambda k: abs(k.value))
    return (key.time, key.value)


def as_absolute(keys, pose_value):
    """The same plan as values for a base curve instead of layer offsets."""
    return [Key(k.time, pose_value + k.value, k.tangent, k.slope)
            for k in keys]


def merge_plans(plans, use_layer=True):
    """Several poses on one channel into one key list, in time order.

    Windows do not overlap -- each is clamped to end before the next key -- so
    this is mostly a concatenation; a shared frame keeps the bigger excursion,
    except that a pose key itself is never overwritten, since the whole point
    is that the pose does not move.
    """
    merged = collections.OrderedDict()
    for keys, pose_value in plans:
        pose_frame = keys[0].time if keys else None
        for k in keys:
            held = merged.get(k.time)
            if held is not None:
                if k.time == pose_frame and k.tangent != TAN_SLOPE:
                    continue
                if held[1].tangent == TAN_SLOPE:
                    continue
                if abs(held[1].value) >= abs(k.value):
                    continue
            value = k.value if use_layer else pose_value + k.value
            merged[k.time] = (k, Key(k.time, value, k.tangent, k.slope))
    return [pair[1] for pair in
            sorted(merged.values(), key=lambda pair: pair[1].time)]


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

    pose_value is None when the channel has no key at that time at all.
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


def set_out_slope(curve, time, slope, next_time, next_value, value):
    """Give a key an exact outgoing slope, in value units per frame.

    Maya's tangent angle is in degrees against an internal time unit, and
    which one is not worth guessing (it is not the same as the scene's frame).
    So ask the curve itself: a linear out-tangent aims at the next key, whose
    secant we know exactly, and the angle Maya reports for it calibrates the
    scale. No temp nodes, no assumption, right at any frame rate.
    """
    at = (time, time)
    secant = (next_value - value) / float(next_time - time)
    if abs(secant) < 1e-12:
        return False
    cmds.keyTangent(curve, time=at, lock=False)
    cmds.keyTangent(curve, time=at, outTangentType="linear")
    got = cmds.keyTangent(curve, time=at, query=True, outAngle=True) or []
    if not got:
        return False
    scale = math.tan(math.radians(got[0])) / secant
    if abs(scale) < 1e-12:
        return False
    cmds.keyTangent(curve, time=at, inTangentType="flat")
    cmds.keyTangent(curve, time=at, outTangentType="fixed",
                    outAngle=math.degrees(math.atan(slope * scale)))
    return True


def _apply_tangents(curve, keys):
    for i, k in enumerate(keys):
        at = (k.time, k.time)
        if k.tangent == TAN_SLOPE:
            if i + 1 < len(keys) and k.slope is not None:
                nxt = keys[i + 1]
                if set_out_slope(curve, k.time, k.slope, nxt.time, nxt.value,
                                 k.value):
                    continue
            cmds.keyTangent(curve, time=at, inTangentType="flat",
                            outTangentType="linear")
            continue
        cmds.keyTangent(curve, time=at, inTangentType=k.tangent,
                        outTangentType=k.tangent)


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
        # a previous run's settle keys, per plan -- never the pose key itself,
        # and never a stretch of the animator's own curve before it
        for plan_keys, _ in plans:
            cmds.cutKey(source, time=(plan_keys[0].time + 0.001,
                                      plan_keys[-1].time + 0.001), clear=True)
        for k in keys:
            cmds.setKeyframe(obj, attribute=attr, time=k.time, value=k.value)
        target = base_curve(plug)

    if target:
        _apply_tangents(target, keys)
    return target


# ---------------------------------------------------------------------------
#  The press
# ---------------------------------------------------------------------------

def overshoot_objects(objects, shape="Spring", do_pos=True, do_rot=False,
                      strength_pos=1.0, frames_pos=12,
                      strength_rot=1.0, frames_rot=12,
                      swings=None, ratio=None, restitution=None,
                      use_layer=True):
    """Overshoot every pose the selection points at. Returns a report string."""
    plan_of = collections.OrderedDict()
    skipped = []
    notes = []
    peaks = []
    any_selected = False

    wanted = [g for g in GROUPS
              if (g == "pos" and do_pos) or (g == "rot" and do_rot)]

    for obj in objects:
        for group in wanted:
            for attr in GROUPS[group]:
                if selected_key_times(obj, attr):
                    any_selected = True

    now = cmds.currentTime(query=True)

    for obj in objects:
        for group in wanted:
            strength = strength_pos if group == "pos" else strength_rot
            frames = frames_pos if group == "pos" else frames_rot
            for attr in GROUPS[group]:
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
                     next_time, next_value) = neighbours(times, values,
                                                         pose_time)
                    if pose_value is None:
                        skipped.append("%s.%s@%g no key there"
                                       % (obj.split("|")[-1], attr, pose_time))
                        continue
                    keys, note = plan_overshoot(
                        pose_time, pose_value, prev_time, prev_value,
                        next_time=next_time, next_value=next_value,
                        strength=strength, frames=frames, shape=shape,
                        swings=swings, ratio=ratio, restitution=restitution)
                    if not keys:
                        skipped.append("%s.%s@%g %s"
                                       % (obj.split("|")[-1], attr,
                                          pose_time, note))
                        continue
                    if note:
                        notes.append(note)
                    peaks.append(peak_of(keys))
                    plan_of.setdefault((obj, group, attr), []).append(
                        (keys, pose_value))

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

    biggest = max(peaks, key=lambda p: abs(p[1]))
    end = cmds.playbackOptions(query=True, maxTime=True)
    past = [k.time for plans in plan_of.values() for keys, _ in plans
            for k in keys if k.time > end]

    report = "%s on %d channel(s), %d pose(s); peak %+.3f at frame %g" % (
        shape, len(plan_of), poses, biggest[1], biggest[0])
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
        strength_pos=cmds.floatSliderGrp("overshootTStrength",
                                         query=True, value=True),
        frames_pos=int(cmds.intSliderGrp("overshootTFrames",
                                         query=True, value=True)),
        strength_rot=cmds.floatSliderGrp("overshootRStrength",
                                         query=True, value=True),
        frames_rot=int(cmds.intSliderGrp("overshootRFrames",
                                         query=True, value=True)),
        swings=_advanced_swings(shape),
        ratio=cmds.floatSliderGrp("overshootRatio", query=True, value=True),
        restitution=cmds.floatSliderGrp("overshootRestitution",
                                        query=True, value=True),
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
    """A type button loads the whole preset into the panel, then applies it.

    Frames included -- see the note on SHAPES. So the sliders always show what
    just happened, and "Apply, keep my numbers" below re-runs the same shape
    with whatever the animator has changed since.
    """
    def go(*_args):
        preset = SHAPES[shape]
        for control in ("overshootTFrames", "overshootRFrames"):
            cmds.intSliderGrp(control, edit=True, value=preset["frames"])
        if preset["family"] == "sine":
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
    cmds.text(label="carries on past the pose, then settles back onto it",
              font="smallObliqueLabelFont", align="center")
    cmds.separator(height=8, style="in")

    cmds.checkBox("overshootTranslate", label="Translate", value=True)
    cmds.floatSliderGrp("overshootTStrength", label="Strength ", field=True,
                        minValue=0.05, maxValue=3.0, value=1.0,
                        fieldMinValue=0.01, fieldMaxValue=20.0,
                        columnWidth3=(70, 50, 170))
    cmds.intSliderGrp("overshootTFrames", label="Frames  ", field=True,
                      minValue=2, maxValue=48, value=12,
                      fieldMinValue=1, fieldMaxValue=200,
                      columnWidth3=(70, 50, 170))

    cmds.separator(height=6, style="in")

    cmds.checkBox("overshootRotate", label="Rotate", value=False)
    cmds.floatSliderGrp("overshootRStrength", label="Strength ", field=True,
                        minValue=0.05, maxValue=3.0, value=1.0,
                        fieldMinValue=0.01, fieldMaxValue=20.0,
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
    cmds.checkBox("overshootBake", label="Bake into curves (no anim layer)",
                  value=False)
    cmds.button(label="Apply, keep my numbers", height=24,
                command=_custom_press)
    cmds.setParent("..")
    cmds.setParent("..")

    cmds.separator(height=6, style="in")
    cmds.text("overshootStatus", label="select keys, or stand on the pose",
              align="center", font="smallFixedWidthFont")

    cmds.showWindow(win_id)


if __name__ == "__main__":
    show_overshoot_ui()
