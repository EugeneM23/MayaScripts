"""
Maya Animation Shake Tool
Creates shake animation on position, rotation and/or scale.
Each channel gets its own override animation layer.
Per-axis strength and enable/disable controls.
Run in Maya Script Editor (Python tab).
"""

import maya.cmds as cmds
import math
import random


# ---------------------------------------------------------------------------
#  Envelope
# ---------------------------------------------------------------------------

def _envelope(frame, start, end, fade_in_frames, fade_out_frames,
              fade_in_type, fade_out_type):
    if frame < start or frame > end:
        return 0.0
    value = 1.0
    if fade_in_frames > 0 and frame < start + fade_in_frames:
        t = (frame - start) / float(fade_in_frames)
        if fade_in_type == "Sine":
            value *= math.sin(t * math.pi * 0.5)
    if fade_out_frames > 0 and frame > end - fade_out_frames:
        t = (end - frame) / float(fade_out_frames)
        if fade_out_type == "Sine":
            value *= math.sin(t * math.pi * 0.5)
    return value


# ---------------------------------------------------------------------------
#  Noise
# ---------------------------------------------------------------------------

def _shake_value(frame, frequency, seed_offset):
    phase = frame * frequency
    key_index = int(phase)
    frac = phase - key_index
    random.seed(key_index * 73856093 + seed_offset)
    val_a = random.uniform(-1, 1)
    random.seed((key_index + 1) * 73856093 + seed_offset)
    val_b = random.uniform(-1, 1)
    blend = (1.0 - math.cos(frac * math.pi)) * 0.5
    return val_a + (val_b - val_a) * blend


# ---------------------------------------------------------------------------
#  Axis definitions
# ---------------------------------------------------------------------------

# (channel_key, axis_suffix, attr_name)
ALL_AXES = [
    ("pos", "X", "translateX"),
    ("pos", "Y", "translateY"),
    ("pos", "Z", "translateZ"),
    ("rot", "X", "rotateX"),
    ("rot", "Y", "rotateY"),
    ("rot", "Z", "rotateZ"),
    ("scl", "X", "scaleX"),
    ("scl", "Y", "scaleY"),
    ("scl", "Z", "scaleZ"),
]


# ---------------------------------------------------------------------------
#  Core logic
# ---------------------------------------------------------------------------

def apply_shake(*_args):
    sel = cmds.ls(selection=True)
    if not sel:
        cmds.warning("Select at least one object.")
        return

    start = int(cmds.intFieldGrp("shakeRange", query=True, value1=True))
    end = int(cmds.intFieldGrp("shakeRange", query=True, value2=True))
    fade_in_frames = int(cmds.intSliderGrp("shakeFadeIn", query=True, value=True))
    fade_out_frames = int(cmds.intSliderGrp("shakeFadeOut", query=True, value=True))
    fade_in_type = "Sine" if cmds.radioButtonGrp("shakeFadeInType", query=True, select=True) == 1 else "Sharp"
    fade_out_type = "Sine" if cmds.radioButtonGrp("shakeFadeOutType", query=True, select=True) == 1 else "Sharp"

    if end <= start:
        cmds.warning("End frame must be greater than start frame.")
        return

    # Gather per-axis settings: which axes are enabled, their strength
    # Group by channel (pos/rot/scl)
    channel_axes = {}  # ch_key -> [(attr_name, strength)]
    for ch_key, axis, attr_name in ALL_AXES:
        cb_name = "shake_{}_{}".format(ch_key, axis)
        str_name = "shake_{}_{}_str".format(ch_key, axis)
        if not cmds.checkBox(cb_name, query=True, value=True):
            continue
        strength = cmds.floatSliderGrp(str_name, query=True, value=True)
        channel_axes.setdefault(ch_key, []).append((attr_name, strength))

    if not channel_axes:
        cmds.warning("Enable at least one axis.")
        return

    # Read frequency per channel
    freq_map = {}
    for ch_key in channel_axes:
        freq_name = "shake_{}_freq".format(ch_key)
        freq_map[ch_key] = cmds.floatSliderGrp(freq_name, query=True, value=True)

    processed = 0

    for obj in sel:
        safe_name = obj.replace("|", "_").replace(":", "_")

        for ch_key, axes in channel_axes.items():
            frequency = freq_map[ch_key]

            # Delete old shake layer
            layer_name = "{}_shake_{}".format(safe_name, ch_key)
            if cmds.animLayer(layer_name, query=True, exists=True):
                cmds.delete(layer_name)

            # Read base values after cleanup
            base_values = {}
            for attr_name, _ in axes:
                full = "{}.{}".format(obj, attr_name)
                base_values[attr_name] = cmds.getAttr(full)

            # Create override layer
            layer = cmds.animLayer(layer_name, override=True)

            # Layer weight: on during shake range only
            weight_attr = "{}.weight".format(layer)
            cmds.setKeyframe(weight_attr, time=start - 1, value=0)
            cmds.keyTangent(weight_attr, time=(start - 1,), outTangentType="step")
            cmds.setKeyframe(weight_attr, time=start, value=1)
            cmds.keyTangent(weight_attr, time=(start,), inTangentType="step")
            cmds.setKeyframe(weight_attr, time=end, value=1)
            cmds.keyTangent(weight_attr, time=(end,), outTangentType="step")
            cmds.setKeyframe(weight_attr, time=end + 1, value=0)
            cmds.keyTangent(weight_attr, time=(end + 1,), inTangentType="step")

            # Set shake keys per axis
            for attr_name, strength in axes:
                full = "{}.{}".format(obj, attr_name)
                cmds.animLayer(layer, edit=True, attribute=full)

                base = base_values[attr_name]
                seed_offset = hash(obj + attr_name) % 100000

                for frame in range(start, end + 1):
                    env = _envelope(frame, start, end,
                                    fade_in_frames, fade_out_frames,
                                    fade_in_type, fade_out_type)
                    noise = _shake_value(frame, frequency, seed_offset)

                    if ch_key == "scl":
                        value = base + noise * strength * env * 0.01
                    else:
                        value = base + noise * strength * env

                    cmds.setKeyframe(obj, attribute=attr_name,
                                     time=frame, value=value,
                                     animLayer=layer)

        processed += 1

    cmds.select(sel)
    cmds.headsUpMessage("Shake applied to {} object(s)".format(processed))


# ---------------------------------------------------------------------------
#  UI helpers
# ---------------------------------------------------------------------------

def _axis_row(parent, ch_key, axis, default_on, default_strength,
              str_min, str_max, str_field_max):
    """Create a checkbox + strength slider row for one axis."""
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(40, 270), parent=parent)
    cmds.checkBox("shake_{}_{}".format(ch_key, axis),
                  label=axis, value=default_on, width=40)
    cmds.floatSliderGrp("shake_{}_{}_str".format(ch_key, axis),
                        label="", field=True,
                        minValue=str_min, maxValue=str_max,
                        value=default_strength,
                        fieldMinValue=0.001, fieldMaxValue=str_field_max,
                        columnWidth3=(1, 45, 200))
    cmds.setParent("..")


# ---------------------------------------------------------------------------
#  UI
# ---------------------------------------------------------------------------

def show_shake_ui():
    win_id = "animShakeWin"

    if cmds.window(win_id, exists=True):
        cmds.deleteUI(win_id)

    cmds.window(win_id, title="Shake Tool", widthHeight=(340, 680), sizeable=True)
    main_col = cmds.columnLayout(adjustableColumn=True, rowSpacing=4,
                                 columnOffset=("both", 10))

    cmds.separator(height=8, style="none")
    cmds.text(label="Animation Shake", font="boldLabelFont", align="center")
    cmds.separator(height=8, style="in")

    # ---- Frame range ----
    cmds.intFieldGrp("shakeRange", numberOfFields=2,
                     label="Frame Range  ",
                     value1=1, value2=24,
                     columnWidth3=(90, 60, 60))

    cmds.separator(height=6, style="in")

    # ---- Fade In ----
    cmds.text(label="Fade In", font="smallBoldLabelFont", align="left")
    cmds.intSliderGrp("shakeFadeIn",
                      label="Frames  ", field=True,
                      minValue=0, maxValue=30, value=5,
                      fieldMinValue=0, fieldMaxValue=200,
                      columnWidth3=(70, 40, 190))
    cmds.radioButtonGrp("shakeFadeInType",
                        label="Type  ", numberOfRadioButtons=2,
                        labelArray2=["Sine", "Sharp"],
                        select=1, columnWidth3=(70, 80, 80))

    cmds.separator(height=4, style="in")

    # ---- Fade Out ----
    cmds.text(label="Fade Out", font="smallBoldLabelFont", align="left")
    cmds.intSliderGrp("shakeFadeOut",
                      label="Frames  ", field=True,
                      minValue=0, maxValue=30, value=5,
                      fieldMinValue=0, fieldMaxValue=200,
                      columnWidth3=(70, 40, 190))
    cmds.radioButtonGrp("shakeFadeOutType",
                        label="Type  ", numberOfRadioButtons=2,
                        labelArray2=["Sine", "Sharp"],
                        select=1, columnWidth3=(70, 80, 80))

    cmds.separator(height=6, style="in")

    # ---- Translate ----
    cmds.text(label="Translate", font="smallBoldLabelFont", align="left")
    _axis_row(main_col, "pos", "X", True, 1.0, 0.01, 10.0, 1000.0)
    _axis_row(main_col, "pos", "Y", True, 1.0, 0.01, 10.0, 1000.0)
    _axis_row(main_col, "pos", "Z", True, 1.0, 0.01, 10.0, 1000.0)
    cmds.floatSliderGrp("shake_pos_freq",
                        label="Frequency ", field=True,
                        minValue=0.1, maxValue=5.0, value=1.0,
                        fieldMinValue=0.01, fieldMaxValue=50.0,
                        columnWidth3=(70, 50, 190))

    cmds.separator(height=4, style="in")

    # ---- Rotate ----
    cmds.text(label="Rotate", font="smallBoldLabelFont", align="left")
    _axis_row(main_col, "rot", "X", False, 5.0, 0.001, 30.0, 1000.0)
    _axis_row(main_col, "rot", "Y", False, 5.0, 0.001, 30.0, 1000.0)
    _axis_row(main_col, "rot", "Z", False, 5.0, 0.001, 30.0, 1000.0)
    cmds.floatSliderGrp("shake_rot_freq",
                        label="Frequency ", field=True,
                        minValue=0.1, maxValue=5.0, value=1.0,
                        fieldMinValue=0.01, fieldMaxValue=50.0,
                        columnWidth3=(70, 50, 190))

    cmds.separator(height=4, style="in")

    # ---- Scale ----
    cmds.text(label="Scale", font="smallBoldLabelFont", align="left")
    _axis_row(main_col, "scl", "X", False, 5.0, 0.001, 50.0, 1000.0)
    _axis_row(main_col, "scl", "Y", False, 5.0, 0.001, 50.0, 1000.0)
    _axis_row(main_col, "scl", "Z", False, 5.0, 0.001, 50.0, 1000.0)
    cmds.floatSliderGrp("shake_scl_freq",
                        label="Frequency ", field=True,
                        minValue=0.1, maxValue=5.0, value=1.0,
                        fieldMinValue=0.01, fieldMaxValue=50.0,
                        columnWidth3=(70, 50, 190))

    cmds.separator(height=8, style="in")

    # ---- Apply ----
    cmds.button(label="Apply Shake", height=36,
                backgroundColor=(0.85, 0.4, 0.35),
                command=apply_shake)

    cmds.separator(height=4, style="none")
    cmds.text(label="Select object(s), set params, click Apply",
              font="smallFixedWidthFont", align="center")

    cmds.showWindow(win_id)


show_shake_ui()