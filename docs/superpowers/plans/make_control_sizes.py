"""The Creep's and the Orc's clavicle and shoulder controls grown to be seen -- a TEXT edit (stdlib, no Maya).

    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' docs/superpowers/plans/make_control_sizes.py

2026-09-30, the animator: «У орка и крипа контролы ключиц плечей не видны они внутри шеометрии тела»;
asked, «Увеличить под тело». `measure_control_sizes.py` measured how far each drawing must grow about its
own origin to be seen at least as well as Manny's (spec
`docs/superpowers/specs/2026-09-30-clavicle-shoulder-control-size-design.md`); RADII is its table.

For every shape of every file: the CV lines of its `.cc` (one CV a line, as Maya writes them; since 2022 the
data can end in component tags, which are kept) scaled uniformly so the largest CV distance from the origin
is the table's radius.  Nothing else changes: the file is checked to differ in those lines only.
Idempotent: a shape at its radius is left alone.  The build does the same at build time
(`as_creep_rig_procedure.control_sizes`).
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
RADII = {"Creep": {"FKScapula": 16.183303, "FKShoulder": 20.707995},   # x1.75, x1.65 (measured)
         "Orc": {"FKScapula": 16.183303, "FKShoulder": 22.590540}}     # x1.75, x1.80 (measured)
TARGETS = [(os.path.join(REPO, "SkeldarAnim", "assets", "Creep_Rig.ma"), "Creep"),
           (os.path.join(REPO, "SkeldarAnim", "assets", "Orc_D_Rig.ma"), "Orc"),
           (os.path.join(REPO, "sources", "orc", "Orc_Rig.ma"), "Orc")]    # what the Orc D is built from
SIDES = ("L", "R")
CC = b'setAttr ".cc" -type "nurbsCurve"'


def cv_lines(lines, shape, parent):
    """(first, count, dim) of the CV lines of `shape`'s `.cc`.  Raises unless the block is where and what
    Maya writes: one createNode, a `.cc`, the header, the knot count and knots, the CV count on a line of
    its own, then one line of `dim` numbers per CV."""
    start = ('createNode nurbsCurve -n "%s" -p "%s";' % (shape, parent)).encode()
    found = [i for i, line in enumerate(lines) if line.startswith(start)]
    if len(found) != 1:
        raise RuntimeError("%s: %d blocks, expected 1" % (shape, len(found)))
    i = found[0] + 1
    while not lines[i].strip().startswith(CC):
        if lines[i].startswith(b"createNode"):
            raise RuntimeError("%s has no .cc" % shape)
        i += 1
    header = lines[i + 1].split()
    dim = int(header[4])
    # the knots: their count, then the values, possibly wrapped over several lines
    j, tokens = i + 2, []
    while True:
        tokens += lines[j].split()
        j += 1
        if tokens and len(tokens) >= int(tokens[0]) + 1:
            break
    if len(tokens) != int(tokens[0]) + 1:
        raise RuntimeError("%s: the knots do not end on their own line" % shape)
    count = int(lines[j].strip())
    first = j + 1
    for k in range(first, first + count):
        if len(lines[k].split()) != dim:
            raise RuntimeError("%s: CV line %d is not %d numbers" % (shape, k + 1, dim))
    return first, count, dim


def radius(lines, first, count):
    return max(sum(float(v) ** 2 for v in lines[k].split()[:3]) ** 0.5 for k in range(first, first + count))


def scaled(line, factor):
    indent = line[:len(line) - len(line.lstrip())]
    ending = line[len(line.rstrip(b"\r\n")):]
    values = [repr(float(v) * factor).encode() for v in line.split()]
    return indent + b" ".join(values) + ending


def run():
    for path, who in TARGETS:
        with open(path, "rb") as handle:
            lines = handle.read().splitlines(keepends=True)
        new = list(lines)
        spans, notes = [], []
        for name, wanted in sorted(RADII[who].items()):
            for side in SIDES:
                shape, parent = "%s_%sShape" % (name, side), "%s_%s" % (name, side)
                first, count, _dim = cv_lines(lines, shape, parent)
                before = radius(lines, first, count)
                if abs(before - wanted) < 1e-6:
                    notes.append("%s at %.6f already" % (shape, before))
                    continue
                factor = wanted / before
                for k in range(first, first + count):
                    new[k] = scaled(lines[k], factor)
                after = radius(new, first, count)
                if abs(after - wanted) > 1e-9:
                    raise RuntimeError("%s: %.9f after the edit, wanted %.9f" % (shape, after, wanted))
                spans.append((first, first + count))
                notes.append("%s %.4f -> %.4f (x%.4f)" % (shape, before, after, factor))
        changed = [i for i, (a, b) in enumerate(zip(lines, new)) if a != b]
        if len(new) != len(lines) or any(not any(a <= i < b for a, b in spans) for i in changed):
            raise RuntimeError("%s: the edit reached outside the curves' CVs" % path)
        name = os.path.basename(path)
        if not changed:
            print("// %s: all at their radii, left alone" % name)
            continue
        tmp = path + ".tmp"
        with open(tmp, "wb") as handle:
            handle.write(b"".join(new))
        os.replace(tmp, path)
        print("// %s: %d lines changed - %s" % (name, len(changed), "; ".join(notes)))
    return 0


if __name__ == "__main__":
    sys.exit(run())
