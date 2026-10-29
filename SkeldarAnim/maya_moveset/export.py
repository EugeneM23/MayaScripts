"""The Moveset card's export: the scene's take back into the AnimSequences a
montage slot plays (2026-10-29).

The pure half is the inverse of the montage import's own mapping - at frame f
the take is the montage at `f / fps` - and every refusal, because Unreal's
import REPLACES a whole AnimSequence: a segment playing a slice of its
sequence, or playing it at another rate, cannot be written back without
changing what the montage shows.

A slot's track is not one segment. Measured over both graphs (a node and a
view is one row), consecutive segments of the SAME sequence are how the
designers cut a section at its hit windows: at rate 1 the pieces play the
sequence straight through and are one writable animation, at another rate they
are a hand-made time warp and are refused.

| | writable | time-warped | plays a slice | no track |
|---|---|---|---|---|
| Longsword (50) | 25 (6 of them several segments) | 19 | 6 | 0 |
| Dagger (44) | 25 | 15 | 2 | 2 |

**No track in either graph plays two different sequences**, and every writable
track starts the slot at frame 0 - so a piece that starts later is refused by
name rather than guessed at (whether Unreal normalises an FBX take that starts
at frame 44 is unmeasured, and nothing today needs it).

Stdlib only; a subprocess test pins it.
"""
import collections

#  seconds. The montage's numbers are float32 of a frame, so 1/30 s reads as
#  0.33000001311302185: a frame's worth of slack is far too much, a float32
#  epsilon too little.
TOL = 1e-4

Piece = collections.namedtuple("Piece", ["package", "anim", "start", "end"])


def _name(path):
    """«/Game/A/AS_X.AS_X» -> «AS_X»: the sequence as the animator reads it."""
    return path.rsplit("/", 1)[-1].split(".", 1)[0]


def _package(path):
    """«/Game/A/AS_X.AS_X» -> «/Game/A/AS_X»: what a reimport writes."""
    return path.split(".", 1)[0]


def _runs(segments):
    """The segments grouped into consecutive runs of one sequence."""
    runs = []
    for segment in segments:
        anim = str(segment.get("anim") or "")
        if runs and runs[-1][0] == anim:
            runs[-1][1].append(segment)
        else:
            runs.append((anim, [segment]))
    return runs


def _float(segment, key):
    try:
        return float(segment.get(key) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def plan(graph, node_id, view, fps):
    """`(pieces, refusal)` for one attack's slot track. Pure.

    `refusal` is "" when the track can be written back; then `pieces` holds one
    `Piece` per sequence, with the whole scene frames it owns.
    """
    node = (graph.get("nodes") or {}).get(node_id)
    if node is None:
        return [], "{0} is a card of your own - it has no montage".format(node_id)
    segments = node.get("segments1p" if view == "1p" else "segments") or []
    slot = node.get("slot1p" if view == "1p" else "slot")
    if not slot or not segments:
        return [], "no {0} track in the montage".format(view.upper())

    pieces, at = [], 0.0
    for anim, run in _runs(segments):
        name = _name(anim)
        if not anim:
            return [], "a segment of the {0} track names no animation".format(view.upper())
        start_pos = _float(run[0], "start_pos")
        if abs(start_pos - at) > TOL:
            return [], "the montage leaves a gap before {0}".format(name)
        length = _float(run[0], "anim_length")
        played = 0.0
        for index, segment in enumerate(run, 1):
            rate = _float(segment, "rate") or 1.0
            loops = int(segment.get("loops") or 1)
            lo, hi = _float(segment, "anim_start"), _float(segment, "anim_end")
            if abs(rate - 1.0) > TOL:
                return [], ("{0} plays at rate {1:.2f} in the montage - a time warp cannot be "
                            "written back".format(name, rate))
            if loops != 1:
                return [], "{0} loops {1} times - it cannot be written back".format(name, loops)
            if abs(lo - played) > TOL:
                return [], ("{0} plays its {1} pieces out of order - a time warp cannot be "
                            "written back".format(name, len(run)))
            played = hi
        if abs(played - length) > TOL or abs(_float(run[0], "anim_start")) > TOL:
            return [], ("{0} plays {1:.2f}-{2:.2f} s of {3:.2f} s - the import replaces the whole "
                        "animation, so a slice cannot be written back".format(
                            name, _float(run[0], "anim_start"), played, length))
        start = int(round(start_pos * fps))
        end = int(round((start_pos + length) * fps))
        if start:
            return [], ("{0} starts {1:.2f} s into the slot - writing a sequence that does not "
                        "start the slot is not built".format(name, start_pos))
        pieces.append(Piece(package=_package(anim), anim=name, start=start, end=end))
        at = start_pos + length
    return pieces, ""


def line(label, view, pieces):
    """«NLt NLt NHd 1P - 1 sequence written: AS_Dg_Atk_NLt_1P (frames 0-43)»."""
    wrote = ", ".join("{0} (frames {1}-{2})".format(p.anim, p.start, p.end) for p in pieces)
    return "{0} {1} - {2} sequence{3} written: {4}".format(
        label, view.upper(), len(pieces), "" if len(pieces) == 1 else "s", wrote)
