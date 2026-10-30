"""Walk Builder's presets: a named set of the card's settings, kept beside the walks (2026-10-30).

The animator: «Давай сделаем в Walk builder возможность сохранять присеты настроек».

A preset holds what the card itself holds and nothing of the scene: the walk's PARAMETERS (each a change from the
cycle's own, so a preset reads the same on any clip - gait.stored_change), the macros, the character and its
strength, the physics' flags, the pose's share, In place, the clean's knobs, the pose parts and the pose card's
path. Never the walk cycle, never a walker: a preset is a look, put on whatever cycle is active.

The file is `<walks folder>/presets.json` - the walks folder, outside the plugin folder an install replaces:

    {"version": 1, "presets": {"<name>": {"params": {...}, "parts": [...], "pose_card": "<rel>"}}}

stdlib only: the panel hands the folder in, so a verify can point it at a temporary one.
"""

import json
import os

FILE = "presets.json"
VERSION = 1
MAX_NAME = 60


def path(folder):
    return os.path.join(folder, FILE)


def clean_name(name):
    """`name` as a preset may be named: whitespace collapsed, no path separator, at most MAX_NAME characters.
    "" when nothing is left (the caller refuses it)."""
    text = " ".join(str(name or "").split())
    for bad in "\\/:":
        text = text.replace(bad, "-")
    return text[:MAX_NAME].strip()


def read(folder):
    """{name: record} - {} when there is no file, or it cannot be read."""
    try:
        with open(path(folder), "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (IOError, OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    kept = data.get("presets")
    if not isinstance(kept, dict):
        return {}
    out = {}
    for name, record in kept.items():
        name = clean_name(name)
        if name and isinstance(record, dict):
            out[name] = record
    return out


def names(folder):
    """The presets' names, by name (what the dropdown lists)."""
    return sorted(read(folder).keys(), key=lambda n: n.lower())


def get(folder, name):
    """One preset's record, None when there is none of that name."""
    return read(folder).get(clean_name(name))


def write(folder, presets):
    """`presets` ({name: record}) into the file, through a temporary one (a half-written file loses every preset)."""
    if not os.path.isdir(folder):
        os.makedirs(folder)
    whole = path(folder)
    temp = whole + ".part"
    with open(temp, "w", encoding="utf-8") as handle:
        json.dump({"version": VERSION, "presets": presets}, handle, indent=1, sort_keys=True)
    if os.path.exists(whole):
        os.remove(whole)
    os.replace(temp, whole)
    return whole


def record(params, parts=(), pose_card=""):
    """A preset's record out of the card's settings: `params` as JSON holds them (scene.plain_params)."""
    return {"params": dict(params or {}), "parts": sorted(parts or ()), "pose_card": str(pose_card or "")}


def fields(stored):
    """(params, parts, pose_card) of a record, whatever is in the file."""
    stored = stored if isinstance(stored, dict) else {}
    params = stored.get("params")
    parts = stored.get("parts")
    card = stored.get("pose_card")
    return (params if isinstance(params, dict) else {},
            tuple(p for p in (parts if isinstance(parts, (list, tuple)) else ()) if isinstance(p, str)),
            card if isinstance(card, str) else "")


def save(folder, name, params, parts=(), pose_card=""):
    """A preset saved (a name already there is replaced). The name used."""
    name = clean_name(name)
    if not name:
        raise ValueError("a preset needs a name")
    presets = read(folder)
    presets[name] = record(params, parts, pose_card)
    write(folder, presets)
    return name


def remove(folder, name):
    """A preset deleted; True when there was one of that name."""
    name = clean_name(name)
    presets = read(folder)
    if name not in presets:
        return False
    del presets[name]
    write(folder, presets)
    return True


def rename(folder, name, into):
    """A preset renamed (replacing a preset of the new name). The new name; None when there was none to rename."""
    name, into = clean_name(name), clean_name(into)
    if not into:
        raise ValueError("a preset needs a name")
    presets = read(folder)
    if name not in presets:
        return None
    presets[into] = presets.pop(name)
    write(folder, presets)
    return into
