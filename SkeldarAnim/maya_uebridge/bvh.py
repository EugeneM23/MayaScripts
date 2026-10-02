"""BVH (Biovision Hierarchy) read and write. stdlib only, no Maya.

2026-10-02, the animator: «хорошо бы было сделать максимальный обхват
форматов которые мы можем прочитать и вытащить из них анимацию». BVH is the
mocap world's plain-text lingua franca - CMU, Truebones, MotionBuilder and
Blender all write it - and it is small enough to read with our own parser.

What a file says, and what we take from it:

- HIERARCHY: ROOT / JOINT blocks, each an OFFSET (its rest translation in the
  parent's frame) and CHANNELS (which of X/Y/Z position and rotation the
  MOTION rows animate, IN ORDER). End Site blocks carry only an offset (the
  tip of the last bone) and are skipped - they animate nothing.
- MOTION: `Frames: N`, `Frame Time: dt`, then N rows of floats, every
  joint's channels in hierarchy order.

The channel ORDER is the rotation order, and it is load-bearing: BVH applies
the listed rotations as a column-vector product, so `Zrotation Xrotation
Yrotation` means R = Rz·Rx·Ry - the vector meets Y first. Maya's row-vector
rotateOrder names the axis met first, so the order is the listed axes
REVERSED: ZXY -> "yxz" (`rotate_order`). A position channel replaces the
offset on that axis (the root's travel; a few exporters give every joint
positions, which is how the verify writes a translating UE clip losslessly).

Units and axes are written as found: BVH has neither, and the retarget
measures proportions itself.
"""

import collections

Joint = collections.namedtuple("Joint", "name parent offset channels")
Motion = collections.namedtuple("Motion", "joints frames frame_time")

POSITION = ("Xposition", "Yposition", "Zposition")
ROTATION = ("Xrotation", "Yrotation", "Zrotation")


class BvhError(ValueError):
    """A file that is not BVH, or one we cannot read honestly."""


def _tokens(text):
    for line in text.splitlines():
        for token in line.split():
            yield token


def parse(text):
    """`text` -> Motion(joints, frames, frame_time). Pure.

    `joints` are in file order (a parent before its children) with `parent`
    an index or None; `frames` a list of rows, one float per channel."""
    tokens = list(_tokens(text))
    if not tokens or tokens[0].upper() != "HIERARCHY":
        raise BvhError("not a BVH file (no HIERARCHY)")
    joints = []
    stack = []          # indices of the open joint blocks; -1 for an End Site
    pending = None      # (name, parent) waiting for its "{"
    i = 1
    while i < len(tokens):
        token = tokens[i]
        upper = token.upper()
        if upper in ("ROOT", "JOINT"):
            parent = next((s for s in reversed(stack) if s >= 0), None)
            if upper == "JOINT" and parent is None:
                raise BvhError("a JOINT outside any ROOT")
            pending = (tokens[i + 1], parent)
            i += 2
            continue
        if upper == "END":                       # End Site
            pending = ("", -1)
            i += 2
            continue
        if token == "{":
            if pending is None:
                raise BvhError("an unexpected '{'")
            name, parent = pending
            pending = None
            if parent == -1:
                stack.append(-1)
            else:
                joints.append(Joint(name, parent, (0.0, 0.0, 0.0), ()))
                stack.append(len(joints) - 1)
            i += 1
            continue
        if token == "}":
            if not stack:
                raise BvhError("an unbalanced '}'")
            stack.pop()
            i += 1
            if not stack and i < len(tokens) and tokens[i].upper() == "MOTION":
                break
            continue
        if upper == "OFFSET":
            values = tuple(float(v) for v in tokens[i + 1:i + 4])
            if stack and stack[-1] >= 0:
                index = stack[-1]
                joints[index] = joints[index]._replace(offset=values)
            i += 4
            continue
        if upper == "CHANNELS":
            count = int(tokens[i + 1])
            names = tuple(tokens[i + 2:i + 2 + count])
            for name in names:
                if name not in POSITION + ROTATION:
                    raise BvhError("unknown channel {0}".format(name))
            if stack and stack[-1] >= 0:
                index = stack[-1]
                joints[index] = joints[index]._replace(channels=names)
            i += 2 + count
            continue
        if upper == "MOTION":
            break
        i += 1
    if stack:
        raise BvhError("the HIERARCHY is not closed")
    while i < len(tokens) and tokens[i].upper() != "MOTION":
        i += 1
    if i >= len(tokens):
        raise BvhError("no MOTION section")
    i += 1
    if tokens[i].rstrip(":").upper() != "FRAMES":
        raise BvhError("no 'Frames:' line")
    count = int(tokens[i + 1])
    i += 2
    if tokens[i].upper() != "FRAME" or tokens[i + 1].rstrip(":").upper() != "TIME":
        raise BvhError("no 'Frame Time:' line")
    frame_time = float(tokens[i + 2])
    i += 3
    width = sum(len(j.channels) for j in joints)
    values = [float(v) for v in tokens[i:i + count * width]]
    if width == 0 or len(values) < count * width:
        raise BvhError("the MOTION holds {0} values, {1} frames x {2} channels "
                       "need {3}".format(len(values), count, width, count * width))
    frames = [values[f * width:(f + 1) * width] for f in range(count)]
    if not joints:
        raise BvhError("no joints")
    return Motion(joints, frames, frame_time)


def rotate_order(channels):
    """Maya's rotateOrder for a joint's BVH rotation channels, e.g. the
    listed Z X Y -> "yxz". Pure; "xyz" when it has fewer than three."""
    axes = [c[0].lower() for c in channels if c in ROTATION]
    if len(axes) != 3:
        return "xyz"
    return "".join(reversed(axes))


def fps_of(frame_time):
    """The frame rate a Frame Time stands for, rounded where it is a common
    rate (1/30 written as 0.0333333 is 30). Pure."""
    if not frame_time or frame_time <= 0:
        return None
    fps = 1.0 / frame_time
    nearest = round(fps)
    return float(nearest) if abs(fps - nearest) < 0.01 else fps


def joint_tracks(motion):
    """Per joint {"t": [(x, y, z)], "e": [(rx, ry, rz)]} over the frames:
    translations (the offset with any position channel over it) and the
    rotation channels as X/Y/Z degrees. Pure."""
    out = []
    column = 0
    for joint in motion.joints:
        names = joint.channels
        start = column
        column += len(names)
        t_list, e_list = [], []
        for row in motion.frames:
            cells = dict(zip(names, row[start:start + len(names)]))
            t_list.append(tuple(cells.get(axis, joint.offset[k])
                                for k, axis in enumerate(POSITION)))
            e_list.append(tuple(cells.get(axis, 0.0) for axis in ROTATION))
        out.append({"t": t_list, "e": e_list})
    return out


def write(joints, frames, frame_time, digits=6):
    """BVH text for `joints` (Joint tuples, any order, `parent` an index)
    and `frames` (rows of channel values, every joint's channels in
    `joints` order). The MOTION rows are rewritten into the HIERARCHY's
    depth-first order, the order a reader takes them in. Pure; the
    verify's writer."""
    children = collections.defaultdict(list)
    for index, joint in enumerate(joints):
        children[joint.parent].append(index)
    order = []

    def visit(index):
        order.append(index)
        for child in children[index]:
            visit(child)
    for root in children[None]:
        visit(root)
    starts, column = [], 0
    for joint in joints:
        starts.append(column)
        column += len(joint.channels)
    frames = [[value for index in order
               for value in row[starts[index]:starts[index] + len(joints[index].channels)]]
              for row in frames]
    fmt = "{0:.%df}" % digits
    lines = ["HIERARCHY"]

    def block(index, depth):
        joint = joints[index]
        pad = "  " * depth
        lines.append("{0}{1} {2}".format(pad, "ROOT" if joint.parent is None
                                          else "JOINT", joint.name))
        lines.append(pad + "{")
        lines.append("{0}  OFFSET {1}".format(
            pad, " ".join(fmt.format(v) for v in joint.offset)))
        lines.append("{0}  CHANNELS {1} {2}".format(
            pad, len(joint.channels), " ".join(joint.channels)))
        for child in children[index]:
            block(child, depth + 1)
        if not children[index]:
            lines.append(pad + "  End Site")
            lines.append(pad + "  {")
            lines.append(pad + "    OFFSET 0.0 0.0 0.0")
            lines.append(pad + "  }")
        lines.append(pad + "}")

    for root in children[None]:
        block(root, 0)
    lines.append("MOTION")
    lines.append("Frames: {0}".format(len(frames)))
    lines.append("Frame Time: {0:.8f}".format(frame_time))
    for row in frames:
        lines.append(" ".join(fmt.format(v) for v in row))
    return "\n".join(lines) + "\n"


def summary(text):
    """(joints, frames, fps) read cheaply off the text for a list row. Pure."""
    motion = parse(text)
    return len(motion.joints), len(motion.frames), fps_of(motion.frame_time)
