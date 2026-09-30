"""Every rig's Main at Manny's size -- a TEXT edit of the shipped .ma files (stdlib, no Maya).

    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' docs/superpowers/plans/make_main_control_size.py

2026-09-30, the animator: «Давай сделаем размер главного контрола у всех ригов такой же как и у
menny сейчас он ну них меньше значительно».  Measured: Manny_Rig's `MainShape` is a periodic cubic
circle of radius 40.52 cm; the Creep's and the Orc's are AdvancedSkeleton's default drawing of the
same circle at 7.76 cm (5.22x smaller, inside the feet); `Main` itself is identity in all three.
So the CV lines of the `.cc` block under `createNode nurbsCurve -n "MainShape" -p "Main";` are
replaced with Manny's, and nothing else: the degree / spans / form line, the knots and the CV count
must already be Manny's, and the file is checked afterwards to differ from what it was in those
lines only.  Textual like the vaccine cut, never an open-and-resave (traps 121-122).

Idempotent: a file whose Main is already Manny's is left alone.  The build procedure does the
same at build time (`as_creep_rig_procedure.main_size`), so a rebuilt rig needs no second pass;
this is what fixes the shipped files and anything opened from an older build.
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
REFERENCE = os.path.join(REPO, "SkeldarAnim", "assets", "Manny_Rig.ma")
TARGETS = [os.path.join(REPO, "SkeldarAnim", "assets", "Creep_Rig.ma"),
           os.path.join(REPO, "SkeldarAnim", "assets", "Orc_D_Rig.ma"),
           os.path.join(REPO, "sources", "orc", "Orc_Rig.ma")]      # what the Orc D is built from
START = b'createNode nurbsCurve -n "MainShape" -p "Main";'
CC = b'setAttr ".cc" -type "nurbsCurve"'


def main_block(lines):
    """(first, end) of the CV lines of MainShape's `.cc` in `lines` (bytes, ends kept), plus the three
    header lines before them (degree line, knots, count).  Raises when the block is not where it
    is in every AdvancedSkeleton rig."""
    starts = [i for i, line in enumerate(lines) if line.startswith(START)]
    if len(starts) != 1:
        raise RuntimeError("%d MainShape blocks, expected 1" % len(starts))
    i = starts[0] + 1
    while not lines[i].strip().startswith(CC):
        if lines[i].startswith(b"createNode"):
            raise RuntimeError("MainShape has no .cc")
        i += 1
    header = [lines[i + 1].strip(), lines[i + 2].strip(), lines[i + 3].strip()]
    first = i + 4
    end = first
    while not lines[end].strip().startswith(b";"):
        if lines[end].startswith(b"createNode") or b";" in lines[end]:
            raise RuntimeError("MainShape's .cc does not end on a line of its own")
        end += 1
    count = int(header[2])
    if end - first != count:
        raise RuntimeError("MainShape: %d CV lines for %d CVs" % (end - first, count))
    return first, end, header


def cvs(lines, first, end):
    return [tuple(float(v) for v in line.split()) for line in lines[first:end]]


def radius(points):
    return max((x * x + z * z) ** 0.5 for x, _y, z in points)


def read(path):
    with open(path, "rb") as handle:
        return handle.read().splitlines(keepends=True)


def run():
    ref = read(REFERENCE)
    r_first, r_end, r_header = main_block(ref)
    reference = [line.strip() for line in ref[r_first:r_end]]
    print("// Manny's Main: radius %.6f cm, %d CVs" % (radius(cvs(ref, r_first, r_end)), len(reference)))
    for path in TARGETS:
        lines = read(path)
        first, end, header = main_block(lines)
        if header != r_header:
            raise RuntimeError("%s: MainShape is not Manny's curve (%r)" % (path, header))
        before = radius(cvs(lines, first, end))
        if [line.strip() for line in lines[first:end]] == reference:
            print("// %s: already Manny's (%.6f cm), left alone" % (os.path.basename(path), before))
            continue
        ending = lines[first][len(lines[first].rstrip(b"\r\n")):]
        indent = lines[first][:len(lines[first]) - len(lines[first].lstrip())]
        new = lines[:first] + [indent + text + ending for text in reference] + lines[end:]
        changed = [i for i, (a, b) in enumerate(zip(lines, new)) if a != b]
        if len(new) != len(lines) or not changed or min(changed) < first or max(changed) >= end:
            raise RuntimeError("%s: the edit reached outside MainShape's CVs" % path)
        after = radius(cvs(new, first, end))
        tmp = path + ".tmp"
        with open(tmp, "wb") as handle:
            handle.write(b"".join(new))
        os.replace(tmp, path)
        print("// %s: Main %.6f -> %.6f cm (x%.6f), %d lines changed, lines %d-%d"
              % (os.path.basename(path), before, after, after / before, len(changed), first + 1, end))
    return 0


if __name__ == "__main__":
    sys.exit(run())
