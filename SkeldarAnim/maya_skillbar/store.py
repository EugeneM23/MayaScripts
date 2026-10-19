"""The skill bar's file (2026-10-19): `<userAppDir>/SkeldarSkills/skills.json`, one per user. Stdlib.

`read` answers the defaults on first use; a file that is not ours is moved aside
(`skills.broken-<stamp>.json`) and the defaults read; `write` is atomic (a temp file replaced).
"""

import os
import time

from . import look

FOLDER = "SkeldarSkills"
NAME = "skills.json"


def path_in(app_dir):
    return os.path.join(app_dir, FOLDER, NAME).replace("\\", "/")


def read(path):
    """(data, note): the model in the file, the defaults when there is none or it is broken (the
    note then says where the broken file went)."""
    if not os.path.isfile(path):
        return look.defaults(), ""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return look.decode(handle.read()), ""
    except (ValueError, OSError, UnicodeDecodeError) as error:
        aside = "%s.broken-%s.json" % (path[:-5] if path.endswith(".json") else path,
                                        time.strftime("%Y%m%d_%H%M%S"))
        try:
            os.replace(path, aside)
        except OSError:
            aside = ""
        note = "The skill bar's file could not be read (%s)" % error
        if aside:
            note += " - kept as %s" % os.path.basename(aside)
        return look.defaults(), note


def write(path, data):
    folder = os.path.dirname(path)
    if folder and not os.path.isdir(folder):
        os.makedirs(folder)
    temp = path + ".tmp"
    with open(temp, "w", encoding="utf-8") as handle:
        handle.write(look.encode(data))
    os.replace(temp, path)
    return path
