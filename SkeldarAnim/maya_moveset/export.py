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


# ---- the press ----------------------------------------------------------------
#
#  The order is the uasset road's, for its reasons: everything that can refuse
#  refuses first (a refusal must cost nothing), every FBX goes to a temp file
#  before any read-only flag is touched, and the editor is asked last. What is
#  different here is that ONE press can write several sequences, so a failure in
#  the middle names what is already written - the earlier ones are not rolled
#  back, and saying so is the only honest answer.

NO_CONTENT_DIR = ("press Refresh in Animation Setup first - the project's Content folder is not "
                  "known yet")
NO_UASSET = "no uasset at {0}"
CANCELLED = "cancelled - nothing written"
READONLY_FAILED = "cannot clear read-only on {0}: {1}"
CONFIRM = "Overwrite"
CANCEL = "Cancel"


def message(label, view, pieces, root, read_only):
    """The one confirm dialog's text. Pure, so the wording is tested.

    It names what is at stake rather than asking "are you sure": every
    sequence the press replaces with the frames it takes, the skeleton the
    scene is exported from, what a replace-import throws away, that Perforce
    is not involved, and the flag.
    """
    from maya_uebridge.uasset_core import LOST_CURVES
    head = "Overwrite the {0}animation{1} of {2} {3}?".format(
        "" if len(pieces) == 1 else "{0} ".format(len(pieces)),
        "" if len(pieces) == 1 else "s", label, view.upper())
    lines = [head, ""]
    for piece in pieces:
        lines.append("    {0}   frames {1}-{2}".format(piece.package, piece.start, piece.end))
    lines += ["    skeleton: {0}".format(root.split("|")[-1] if root else "?"),
              "",
              "Each asset is REBUILT from an FBX of the scene, so curves the FBX",
              "does not carry do not survive it ({0}).".format(LOST_CURVES),
              "",
              "Perforce is not touched: the uasset is written on disk with no",
              "changelist behind it."]
    if read_only:
        lines += ["",
                  "{0} read-only. That flag will be CLEARED and left off.".format(
                      "One file is" if read_only == 1 else
                      "{0} files are".format(read_only))]
    return "\n".join(lines)


def _ask(text):
    """The confirm dialog. Cancel is the default and the dismiss.

    Injectable through `asks` because a modal raised over the command port
    blocks Maya's idle queue, and every live proof here runs over that port.
    """
    from maya import cmds
    answer = cmds.confirmDialog(title="Export into the slot", message=text,
                                button=[CONFIRM, CANCEL], defaultButton=CANCEL,
                                cancelButton=CANCEL, dismissString=CANCEL)
    return answer == CONFIRM


def _bridge():
    """(content_dir, project, temp_folder) from the UE Bridge's own state."""
    from maya_uebridge import window as bridge
    return bridge.content_dir(), bridge.project_choice(), bridge.temp_folder()


def _root():
    from maya_uebridge import animexport
    return animexport.resolve_root()


def _fps():
    from maya_uebridge import animimport
    return animimport.scene_fps()


def _export(fbx, root, start, end):
    from maya_uebridge import animexport
    return animexport.export_hierarchy(fbx, root=root, start=start, end=end,
                                       layout=animexport.UNREAL_LAYOUT)


def _notes(piece, info, payload):
    """What one written sequence adds to the status line, beyond its name."""
    from maya_uebridge import records
    said = []
    if (info or {}).get("warning"):
        said.append("{0}: {1}".format(piece.anim, info["warning"]))
    unchanged = records.unchanged_warning(payload)
    if unchanged:
        said.append("{0}: {1}".format(piece.anim, unchanged))
    elif not (payload or {}).get("saved"):
        said.append("{0}: {1}".format(piece.anim, records.reimport_line(payload)))
    return said


def _stopped(label, view, written, failure):
    """A failure in the middle: what went wrong, and what is already written."""
    if not written:
        return failure
    return "{0}  |  already written: {1}".format(
        failure, ", ".join("{0} (frames {1}-{2})".format(p.anim, p.start, p.end)
                           for p in written))


def export_slot(graph, node_id, view, label, asks=None):
    """The scene's take back into the AnimSequences one slot plays.

    Every seam the scene, the editor and the disk come through is in `asks`,
    so the press itself is tested with neither Maya nor Unreal: "fps",
    "bridge", "root", "export", "exists", "read_only", "clear", "confirm",
    "run_script".
    """
    import os as _os

    from maya_uebridge import records, uescripts
    from maya_uebridge.uasset_core import clear_read_only, is_read_only

    asks = asks or {}
    fps = asks.get("fps", _fps)()
    pieces, refusal = plan(graph, node_id, view, fps)
    if refusal:
        return refusal

    content_dir, project, temp_folder = asks.get("bridge", _bridge)()
    if not content_dir:
        return NO_CONTENT_DIR
    exists = asks.get("exists", _os.path.isfile)
    read_only = asks.get("read_only", is_read_only)
    assets = [records.uasset_path_of(piece.package, content_dir) for piece in pieces]
    for piece, uasset in zip(pieces, assets):
        if not exists(uasset):
            return NO_UASSET.format(uasset)

    #  before the dialog: an undecidable skeleton must not cost a click
    try:
        root = asks.get("root", _root)()
    except RuntimeError as error:
        return str(error)

    locked = [uasset for uasset in assets if read_only(uasset)]
    confirm = asks.get("confirm", _ask)
    if not confirm(message(label, view, pieces, root, len(locked))):
        return CANCELLED

    export = asks.get("export", _export)
    clear = asks.get("clear", clear_read_only)
    run_script = asks.get("run_script")
    if run_script is None:
        from maya_uebridge import uelink
        run_script = uelink.run_script

    written, said = [], []
    for piece, uasset in zip(pieces, assets):
        fbx = _os.path.join(temp_folder, "{0}.slot.fbx".format(piece.anim))
        try:
            info = export(fbx, root, piece.start, piece.end)
        except (RuntimeError, OSError) as error:
            return _stopped(label, view, written, "{0}: {1}".format(piece.anim, error))
        if uasset in locked:
            failure = clear(uasset)
            if failure:
                return _stopped(label, view, written, READONLY_FAILED.format(uasset, failure))
        out = _os.path.join(temp_folder, "moveset_reimport.json")
        try:
            payload = run_script(uescripts.reimport_script(out, piece.package, fbx),
                                 out, project=project)
        except Exception as error:          # uelink.UeBridgeError and its family
            return _stopped(label, view, written, "{0}: {1}".format(piece.anim, error))
        if not (payload or {}).get("ok") or (payload or {}).get("error"):
            return _stopped(label, view, written, "{0}: editor: {1}".format(
                piece.anim, (payload or {}).get("error") or "the import did not run"))
        written.append(piece)
        said.extend(_notes(piece, info, payload))

    if locked:
        said.append("read-only cleared on {0} file{1}".format(
            len(locked), "" if len(locked) == 1 else "s"))
    return "  |  ".join([line(label, view, written)] + said)
