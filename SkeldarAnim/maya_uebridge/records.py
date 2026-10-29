"""The animation record and everything pure that operates on it.

stdlib only: no maya.cmds, no unreal. This module holds the fiddly parts —
parsing what the editor sent, the search filter, namespace naming, the
package↔disk-path conversion and the reimport reply's wording — so they can
be tested without either application running.

The last two moved here from `vcs.py` and `checkouts.py` on 2026-09-01, when
Export to uasset needed them and must not touch Perforce: they are string and
path work with no p4 anywhere in them, and one home is what keeps two status
lines from drifting apart. `vcs.py` re-imports them, so nothing else moved.
"""

import collections
import os
import re

#  2026-10-02 (sources: Unreal, a Unity project, a folder): a record also says
#  which SOURCE it came from and, for a file, the file, the clip inside it and
#  its format (`sources.file_record`). The six old fields keep their places and
#  the new ones default to an Unreal asset, so every record made before and
#  every positional constructor still means what it meant.
#  2026-10-29 (montages): `kind` says what the row IS - "" an animation,
#  "montage" an AnimMontage, whose `clip` carries the chosen slot once the
#  card has slotted it (`with_slot`). It is the LAST field with a default, so
#  every positional constructor and every record made before still means what
#  it meant.
AnimRecord = collections.namedtuple(
    "AnimRecord", ["name", "package", "skeleton", "frames", "length", "fps",
                   "source", "path", "clip", "fmt", "kind"],
    defaults=("unreal", "", "", "", ""))

MONTAGE = "montage"


def is_montage(record):
    """True for a row that is an AnimMontage rather than an animation. Pure."""
    return getattr(record, "kind", "") == MONTAGE


def montage_slot(record):
    """The slot a montage record has been given, "" before the card gives it
    one. Pure."""
    return getattr(record, "clip", "") if is_montage(record) else ""


def with_slot(record, slot):
    """The montage record named for one of its slots: «AM_X» -> «AM_X_1P»,
    the slot kept in `clip`. Pure, and never stacks - a record already slotted
    is re-slotted from the montage's own name, so every road (the Import
    button's words, the namespace, the clip label, the drag, the square) names
    the montage AND the slot with no plumbing of its own."""
    if not slot or not is_montage(record):
        return record
    base = record.name
    held = montage_slot(record)
    if held and base.endswith("_" + held):
        base = base[:-(len(held) + 1)]
    return record._replace(name=clip_name(base, slot), clip=slot)


def clip_name(montage, slot):
    """«AM_LongSword_Block_Stun» + «1P» -> «AM_LongSword_Block_Stun_1P». Pure.

    The one spelling: `montage.clip_name` is this function, so the namespace,
    the label under the character and the status line cannot drift apart."""
    return "{0}_{1}".format(montage, slot) if slot else montage

_ILLEGAL = re.compile(r"[^A-Za-z0-9_]")

#  Animation Setup's Import button says what it will do (2026-10-19, variant
#  A). A Qt button is as wide as its words and widens the dock's column
#  (trap 67), so the words are kept within this many characters.
IMPORT_LABEL_MAX = 44


def target_labels(kind):
    """The «Put it on» segments' words for the card's kind: («Selected rig»,
    «A new rig»)."""
    return ("Selected " + kind, "A new " + kind)


def import_label(names, kind, target, model_label="", auto=False):
    """The Import button's words: «Import A_Jump → selected rig», «Import 3
    animations → 3 new Manny rigs». `names` are the picked rows' clip names
    in order, `target` "onto" / "new", `auto` the Auto card. A long clip
    name is cut with «…» so the whole stays within IMPORT_LABEL_MAX."""
    if not names:
        return "Import animation"
    count = len(names)
    if auto:
        where = ("selected " + kind if target == "onto"
                 else "our {0} or its own".format(kind))
    elif target == "onto":
        where = "selected " + kind
    else:
        what = "{0} {1}".format(model_label, kind).strip()
        where = ("a new " + what if count == 1
                 else "{0} new {1}s".format(count, what))
    clip = names[0] if count == 1 else "{0} animations".format(count)
    room = IMPORT_LABEL_MAX - len("Import  → ") - len(where)
    if len(clip) > room:
        #  the MIDDLE goes, as in a list row (`_middle`): a UE name carries
        #  meaning at both ends, and a montage's slot is its tail - cutting
        #  from the right left «Import AM_LongSword_Block_St… → selected rig»,
        #  which does not say which slot comes in
        keep = max(room - 1, 4)
        head = (keep + 1) // 2
        clip = clip[:head] + "…" + clip[len(clip) - (keep - head):]
    return "Import {0} → {1}".format(clip, where)


def _number(value, cast):
    """Asset registry tags arrive as text, and some assets carry none at all."""
    if value is None or value == "":
        return None
    try:
        return cast(value)
    except (TypeError, ValueError):
        return None


def parse_payload(payload):
    """Turn the editor's JSON reply into records, sorted by name.

    A row without a package path is dropped: there would be nothing to export
    from it later. Every other field is optional — a missing frame count must
    not cost us the animation.
    """
    out = []
    for entry in (payload or {}).get("assets") or []:
        package = entry.get("package") or ""
        if not package:
            continue
        out.append(AnimRecord(
            name=entry.get("name") or package.rsplit("/", 1)[-1],
            package=package,
            skeleton=entry.get("skeleton") or "",
            frames=_number(entry.get("frames"), int),
            length=_number(entry.get("length"), float),
            fps=_number(entry.get("fps"), float),
            source=entry.get("source") or "unreal",
            path=entry.get("path") or "",
            clip=entry.get("clip") or "",
            fmt=entry.get("fmt") or "",
            kind=entry.get("kind") or ""))
    out.sort(key=lambda r: r.name.lower())
    return out


def filter_records(records, query):
    """Keep records matching every whitespace-separated term.

    Terms match against name and package together, case-insensitively, so
    "manny walk" narrows to walks under a Manny folder. Narrowing rather than
    widening is what makes a second word useful.
    """
    terms = (query or "").lower().split()
    if not terms:
        return list(records)
    out = []
    for rec in records:
        haystack = (rec.name + " " + rec.package).lower()
        if all(term in haystack for term in terms):
            out.append(rec)
    return out


def namespace_for(asset_name, taken):
    """A Maya-legal namespace derived from the asset name, unique against `taken`.

    Uniquifying happens after sanitising, because `taken` holds real namespaces
    that already went through the same cleaning.
    """
    base = _ILLEGAL.sub("_", asset_name or "")
    if not base:
        base = "anim"
    if base[0].isdigit():
        base = "_" + base
    if base not in taken:
        return base
    index = 1
    while "{0}{1}".format(base, index) in taken:
        index += 1
    return "{0}{1}".format(base, index)


NAME_WIDTH = 46
FOLDER_WIDTH = 44


def _middle(text, width):
    """Drop the MIDDLE of a name that will not fit.

    UE animation names carry meaning at both ends - the head says what it is
    (AS_Longsword_Attack_Back...) and the tail says which one
    (...Combo_v2_2_1P). Cutting either end makes a dozen rows read alike.
    """
    if len(text) <= width:
        return text
    keep = width - 3
    head = (keep + 1) // 2
    return text[:head] + "..." + text[len(text) - (keep - head):]


def _tail(text, width):
    """Keep the END of a path when it will not fit.

    A UE folder says what the animation is at its tail - Characters/Heroes/Sevarog
    - and nothing at its head, where every row reads /Game/... alike.
    """
    if len(text) <= width:
        return text
    return "..." + text[-(width - 3):]


def format_row(record):
    """One line for the scroll list: name, folder, and length if we know it.

    A file's row (2026-10-02) shows its own folder and, after the length, its
    format and what stops it importing, if anything («humanoid»). A montage's
    (2026-10-29) says «montage» where a frame count would be - the registry
    carries neither a length nor a slot for one - and names its slot once the
    card has slotted it."""
    file_row = record.source != "unreal" and record.path
    folder = (record.path if file_row else record.package).rsplit("/", 1)[0]
    frames = "{0} fr".format(record.frames) if record.frames is not None else ""
    if file_row:
        frames = "  ".join(t for t in (frames, record.fmt, record.skeleton) if t)
    elif is_montage(record):
        frames = "  ".join(t for t in (MONTAGE, montage_slot(record)) if t)
    return "{0:<{1}} {2:<{3}} {4}".format(
        _middle(record.name, NAME_WIDTH), NAME_WIDTH,
        _tail(folder, FOLDER_WIDTH), FOLDER_WIDTH,
        frames)


# ------------------------------------------------- package <-> disk path

def package_of(client_file, content_dir):
    """The /Game package of a file under the project's Content dir, "" when it
    is not under it. Case-insensitive: Windows paths arrive in mixed case."""
    if not client_file or not content_dir:
        return ""
    node = os.path.normpath(client_file)
    prefix = os.path.normpath(content_dir) + os.sep
    if not os.path.normcase(node).startswith(os.path.normcase(prefix)):
        return ""
    relative = os.path.splitext(node[len(prefix):])[0]
    return "/Game/" + relative.replace(os.sep, "/")


def uasset_path_of(package, content_dir):
    """/Game/A/B/AS_X -> <content_dir>/A/B/AS_X.uasset. Pure inverse of
    `package_of` (modulo case, which Windows does not keep anyway)."""
    text = (package or "").replace("\\", "/")
    if text.lower().startswith("/game/"):
        text = text[len("/game/"):]
    parts = [part for part in text.split("/") if part]
    return os.path.join(content_dir, *parts) + ".uasset"


# ----------------------------------------------------- the editor's reply

def reimport_line(payload):
    """What the status says about the editor's side of an export. Pure.

    Shared by both export directions -- the Perforce round trip on the
    Export tab and the direct Export to uasset -- so the wording cannot
    drift between them.
    """
    payload = payload or {}
    frames = payload.get("frames")
    tail = " ({0} frames)".format(frames) if frames is not None else ""
    if not payload.get("saved"):
        return "reimported, NOT saved - save it in the editor" + tail
    return "reimported and saved" + tail


def unchanged_warning(payload):
    """A warning when the reimport left the asset exactly as it was. Pure.

    Measured 2026-09-01: an FBX whose bones do not match the asset's
    skeleton imports "successfully" -- ok, saved, no notes, no error -- and
    the animation is untouched. The status said "reimported and saved (196
    frames)" over an asset nothing had been written to, which is the worst
    kind of failure this project keeps finding.

    Frame count AND length both identical is the signal. Re-exporting the
    same clip unchanged would look the same, so this is worded as something
    to check rather than as an error.
    """
    payload = payload or {}
    before, after = payload.get("before_frames"), payload.get("frames")
    if before is None or after is None or before != after:
        return ""
    if payload.get("before_length") != payload.get("length"):
        return ""
    skeleton = payload.get("skeleton") or "the asset's skeleton"
    return ("the asset did NOT change ({0} frames) - check the exported "
            "bones match {1}".format(after, skeleton))
