"""The animation record and everything pure that operates on it.

stdlib only: no maya.cmds, no unreal. This module holds the fiddly parts —
parsing what the editor sent, the search filter, and namespace naming — so they
can be tested without either application running.
"""

import collections
import re

AnimRecord = collections.namedtuple(
    "AnimRecord", ["name", "package", "skeleton", "frames", "length", "fps"])

_ILLEGAL = re.compile(r"[^A-Za-z0-9_]")


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
            fps=_number(entry.get("fps"), float)))
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


def format_row(record):
    """One line for the scroll list: name, folder, and length if we know it."""
    folder = record.package.rsplit("/", 1)[0]
    frames = "{0} fr".format(record.frames) if record.frames is not None else ""
    return "{0:<38} {1:<44} {2}".format(record.name[:38], folder[:44], frames)
