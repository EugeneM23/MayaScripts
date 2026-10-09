"""The Cascadeur bridge's own small settings: the author name for Shared and
the last Unreal target. A JSON file it owns; a broken file reads as empty and
is never rewritten by a read. Stdlib only.
"""

import json
import os


def default_path(appdata=None):
    """Where the prefs live: %APPDATA%\\SkeldarAnim\\cascadeur.json."""
    base = appdata or os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, "SkeldarAnim", "cascadeur.json")


def load(path):
    """The stored dict, or {} when the file is missing, broken or not an object."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save(path, data):
    """Write atomically: a temp file, then replace."""
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    temp = path + ".tmp"
    with open(temp, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
    os.replace(temp, path)


def get(path, key, default=""):
    """One stored value, or `default` when it is missing or of another type."""
    value = load(path).get(key, default)
    return value if isinstance(value, type(default)) else default


def put(path, key, value):
    """Store one value, keeping every other key."""
    data = load(path)
    data[key] = value
    save(path, data)
