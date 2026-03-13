"""
Maya Animation Overshoot Tool
Creates overshoot animation after existing keyframes.
Separate override layers for position and rotation.
Run in Maya Script Editor (Python tab).
"""

import maya.cmds as cmds
import math


# ---------------------------------------------------------------------------
#  Overshoot curve functions
# ---------------------------------------------------------------------------

def _curve_spring(t):
    return math.sin(3.0 * math.pi * t) * math.exp(-4.0 * t)


def _curve_elastic(t):
    return math.sin(4.5 * math.pi * t) * math.exp(-2.5 * t)


def _curve_bounce(t):
    return abs(math.sin(3.0 * math.pi * t)) * math.exp(-5.0 * t)


CURVES = {
    "Spring": _curve_spring,
    "Elastic": _curve_elastic,
    "Bounce": _curve_bounce,
}

TRANSLATE_ATTRS = {"translateX", "translateY", "translateZ"}
ROTATE_ATTRS = {"rotateX", "rotateY", "rotateZ"}


def _build_layer(obj, safe_name, channel_tag, curve_type, curve_func,
                 anim_attrs, strength, duration):
    """Delete old overshoot layers for this channel and build a new one."""

    # Delete old layers for ALL curve types on this channel
    for ctype in CURVES:
        old = "{}_overshoot_{}_{}".format(safe_name, channel_tag, ctype)
        if cmds.animLayer(old, query=True, exists=True):
            cmds.delete(old)

    # Collect data from clean base
    attr_data = {}
    global_first = None
    global_last = None

    for attr in anim_attrs:
        full = "{}.{}".format(obj, attr)
        keys = cmds.keyframe(full, query=True, timeChange=True)
        if not keys or len(keys) < 2:
            continue
        t_first = keys[0]
        t_last = keys[-1]
        v_at_last = cmds.getAttr(full, time=t_last)
        v_before = cmds.getAttr(full, time=t_last - 1)
        velocity = v_at_last - v_before
        attr_data[attr] = (t_first, t_last, v_at_last, velocity)

        if global_first is None or t_first < global_first:
            global_first = t_first
        if global_last is None or t_last > global_last:
            global_last = t_last

    if not attr_data:
        return False

    # Create override layer
    layer_name = "{}_overshoot_{}_{}".format(safe_name, channel_tag, curve_type)
    layer = cmds.animLayer(layer_name, override=True)

    # Animate weight: OFF during original, ON after
    weight_attr = "{}.weight".format(layer)
    cmds.setKeyframe(weight_attr, time=global_first, value=0)
    cmds.keyTangent(weight_attr, time=(global_first,), outTangentType="step")
    cmds.setKeyframe(weight_attr, time=global_last, value=1)
    cmds.keyTangent(weight_attr, time=(global_last,), inTangentType="step")

    # Set overshoot keys (absolute values)
    for attr in attr_data:
        t_first, t_last, v_at_last, velocity = attr_data[attr]

        if abs(velocity) < 0.0001:
            continue

        overshoot_amount = velocity * strength * duration * 0.3
        full = "{}.{}".format(obj, attr)

        cmds.animLayer(layer, edit=True, attribute=full)

        cmds.setKeyframe(obj, attribute=attr,
                         time=t_last, value=v_at_last,
                         animLayer=layer)

        for f in range(1, duration + 1):
            t = f / float(duration)
            offset = overshoot_amount * curve_func(t)
            cmds.setKeyframe(obj, attribute=attr,
                             time=t_last + f,
                             value=v_at_last + offset,
                             animLayer=layer)

        cmds.setKeyframe(obj, attribute=attr,
                         time=t_last + duration,
                         value=v_at_last,
                         animLayer=layer)

    return True


# ---------------------------------------------------------------------------
#  Core logic
# ---------------------------------------------------------------------------

def apply_overshoot(curve_type="Spring", *_args):
    sel = cmds.ls(selection=True)
    if not sel:
        cmds.warning("Select at least one animated object.")
        return

    do_translate = cmds.checkBox("overshootTranslate", query=True, value=True)
    do_rotate = cmds.checkBox("overshootRotate", query=True, value=True)

    t_strength = cmds.floatSliderGrp("overshootTStrength", query=True, value=True)
    t_duration = int(cmds.intSliderGrp("overshootTDuration", query=True, value=True))

    r_strength = cmds.floatSliderGrp("overshootRStrength", query=True, value=True)
    r_duration = int(cmds.intSliderGrp("overshootRDuration", query=True, value=True))

    curve_func = CURVES[curve_type]

    if not do_translate and not do_rotate:
        cmds.warning("Enable at least Translate or Rotate.")
        return

    processed = 0

    for obj in sel:
        safe_name = obj.replace("|", "_").replace(":", "_")
        attrs = cmds.listAttr(obj, keyable=True) or []
        did_something = False

        # --- Translate layer ---
        if do_translate:
            t_attrs = []
            for attr in attrs:
                if attr not in TRANSLATE_ATTRS:
                    continue
                full = "{}.{}".format(obj, attr)
                keys = cmds.keyframe(full, query=True, timeChange=True)
                if keys and len(keys) >= 2:
                    t_attrs.append(attr)

            if t_attrs:
                ok = _build_layer(obj, safe_name, "pos", curve_type,
                                  curve_func, t_attrs, t_strength, t_duration)
                if ok:
                    did_something = True

        # --- Rotate layer ---
        if do_rotate:
            r_attrs = []
            for attr in attrs:
                if attr not in ROTATE_ATTRS:
                    continue
                full = "{}.{}".format(obj, attr)
                keys = cmds.keyframe(full, query=True, timeChange=True)
                if keys and len(keys) >= 2:
                    r_attrs.append(attr)

            if r_attrs:
                ok = _build_layer(obj, safe_name, "rot", curve_type,
                                  curve_func, r_attrs, r_strength, r_duration)
                if ok:
                    did_something = True

        if did_something:
            processed += 1
        else:
            cmds.warning("{}: no matching keyed attributes.".format(obj))

    cmds.select(sel)
    cmds.headsUpMessage("Overshoot ({}) applied to {} object(s)".format(curve_type, processed))


# ---------------------------------------------------------------------------
#  UI
# ---------------------------------------------------------------------------

def show_overshoot_ui():
    win_id = "animOvershootWin"

    if cmds.window(win_id, exists=True):
        cmds.deleteUI(win_id)

    cmds.window(win_id, title="Overshoot Tool", widthHeight=(320, 440), sizeable=True)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=4, columnOffset=("both", 10))

    cmds.separator(height=8, style="none")
    cmds.text(label="Animation Overshoot", font="boldLabelFont", align="center")
    cmds.separator(height=8, style="in")

    # ---- Translate section ----
    cmds.checkBox("overshootTranslate", label="Translate", value=True)

    cmds.floatSliderGrp("overshootTStrength",
                        label="Strength  ", field=True,
                        minValue=0.05, maxValue=2.0, value=0.3,
                        fieldMinValue=0.01, fieldMaxValue=100.0,
                        columnWidth3=(70, 50, 170))

    cmds.intSliderGrp("overshootTDuration",
                      label="Duration  ", field=True,
                      minValue=4, maxValue=60, value=15,
                      fieldMinValue=2, fieldMaxValue=120,
                      columnWidth3=(70, 50, 170))

    cmds.separator(height=6, style="in")

    # ---- Rotate section ----
    cmds.checkBox("overshootRotate", label="Rotate", value=False)

    cmds.floatSliderGrp("overshootRStrength",
                        label="Strength  ", field=True,
                        minValue=0.05, maxValue=2.0, value=0.3,
                        fieldMinValue=0.01, fieldMaxValue=100.0,
                        columnWidth3=(70, 50, 170))

    cmds.intSliderGrp("overshootRDuration",
                      label="Duration  ", field=True,
                      minValue=4, maxValue=60, value=15,
                      fieldMinValue=2, fieldMaxValue=120,
                      columnWidth3=(70, 50, 170))

    cmds.separator(height=8, style="in")

    # ---- Overshoot type buttons ----
    cmds.text(label="Overshoot type", font="smallBoldLabelFont", align="left")

    cmds.button(label="Spring", height=28,
                backgroundColor=(0.45, 0.75, 0.45),
                command=lambda *_: apply_overshoot("Spring"))
    cmds.button(label="Elastic", height=28,
                backgroundColor=(0.45, 0.65, 0.85),
                command=lambda *_: apply_overshoot("Elastic"))
    cmds.button(label="Bounce", height=28,
                backgroundColor=(0.85, 0.75, 0.45),
                command=lambda *_: apply_overshoot("Bounce"))

    cmds.separator(height=4, style="none")
    cmds.text(label="Select animated obj(s), click type to apply",
              font="smallFixedWidthFont", align="center")

    cmds.showWindow(win_id)


show_overshoot_ui()
