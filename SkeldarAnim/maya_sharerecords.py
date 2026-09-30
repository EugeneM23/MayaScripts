"""maya_sharerecords - the Shared section's records, as data. Stdlib only.

The animator's ask (2026-09-30): «Shared Temp хранилище в котором сможем
обмениваться сценами ... а еще и fbx файлов», then «Один человек нажал
кнопочку у второго через 2 секунды появился файлик в списке ... Ключи
никакие не нужны». Everyone works remotely. So a file goes to
litterbox.catbox.moe and a RECORD of it goes to an ntfy.sh channel every
colleague's Maya listens to (`maya_sharenet`); `maya_share` is the section.

This module is the record: what a sent one holds, what a received one may
hold, how two records of one file combine, how a row reads, where a file
lands on the disk. No `maya`, no network, and no clock of its own -- `now`
is always passed in, so every rule is a plain test.

Nothing on the channel is authenticated (the topic is in a public
repository), so `parse` is strict: anything that is not one of our records,
and a `url` that is not litterbox's, is dropped.

Spec: docs/superpowers/specs/2026-09-30-shared-files-design.md
"""

import json
import os
import re
import time
import uuid
from urllib.parse import urlsplit

APP = "skeldaranim-share"
VERSION = 1
STATES = ("sending", "ready", "failed")
KINDS = {".ma": "scene", ".mb": "scene", ".fbx": "fbx"}
SCENE_TYPES = {".ma": "mayaAscii", ".mb": "mayaBinary"}
HOSTS = ("litter.catbox.moe",)

LIFETIME = 72 * 3600         # litterbox's longest keep: the file is gone after
SENDING_TIMEOUT = 2 * 3600   # a "sending" never finished: the sender's Maya died
NEWS_WITHIN = 10 * 60        # an arrival older than this is history, not news
MAX_ZIP = 1024 ** 3          # litterbox takes up to 1 GB
HISTORY_VERSION = 1

#  The list is fixed-width: name, sender, state, size, time, comment.
NAME_WIDTH = 24
WHO_WIDTH = 8
STATUS_WIDTH = 13
SIZE_WIDTH = 8
WHEN_WIDTH = 11

_ID = re.compile(r"^[0-9a-f]{32}$")
_BAD_NAME = re.compile(r'[\\/:*?"<>|\x00-\x1f]')
_SAFE = re.compile(r"[^\w-]+")
_RANK = {"sending": 0, "ready": 1, "failed": 1}


def new_id():
    """A record's id: 32 hex characters."""
    return uuid.uuid4().hex


def kind_of(name):
    """"scene" for .ma/.mb, "fbx" for .fbx, None for anything else."""
    return KINDS.get(os.path.splitext(name or "")[1].lower())


def scene_file_name(scene_path, now):
    """(file name, Maya file type) for a copy of the open scene. An untitled
    scene is `untitled_<HHMM>.ma`; a saved one keeps its name and type."""
    stem, ext = os.path.splitext(os.path.basename(scene_path or ""))
    ext = ext.lower()
    if not stem:
        stem = "untitled_" + time.strftime("%H%M", time.localtime(now))
    if ext not in SCENE_TYPES:
        ext = ".ma"
    return stem + ext, SCENE_TYPES[ext]


def make_record(state, rid, sender, machine, name, size, sent, comment="",
                maya="", fps=None, frame_range=None):
    """A record as sent. `url` and `zip` join it once the file is up
    (`with_state(record, "ready", url=..., zip=...)`)."""
    record = {"app": APP, "v": VERSION, "id": rid, "state": state,
              "from": sender, "machine": machine, "name": name,
              "kind": kind_of(name), "bytes": int(size), "sent": int(sent),
              "comment": comment or ""}
    if maya:
        record["maya"] = maya
    if fps:
        record["fps"] = fps
    if frame_range:
        record["range"] = [frame_range[0], frame_range[1]]
    return record


def with_state(record, state, **extra):
    """A copy of `record` in `state`, with `extra` fields added."""
    out = dict(record)
    out["state"] = state
    out.update(extra)
    return out


def encode(record):
    """The message body: compact JSON (a few hundred bytes of ntfy's 4096)."""
    return json.dumps(record, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


def allowed_url(url):
    """True for an https address on litterbox's download host."""
    if not isinstance(url, str):
        return False
    try:
        parts = urlsplit(url)
        host = parts.hostname
    except ValueError:
        return False
    return (parts.scheme == "https" and host in HOSTS
            and bool(parts.path.strip("/")))


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def parse(text):
    """The record in a message body, or None for anything that is not one of
    ours or does not hold together."""
    try:
        record = json.loads(text)
    except (TypeError, ValueError):
        return None
    if not isinstance(record, dict):
        return None
    if record.get("app") != APP or record.get("v") != VERSION:
        return None
    rid = record.get("id")
    if not isinstance(rid, str) or not _ID.match(rid):
        return None
    if record.get("state") not in STATES:
        return None
    name = record.get("name")
    if (not isinstance(name, str) or not name.strip()
            or _BAD_NAME.search(name) or name.startswith(".")
            or kind_of(name) is None):
        return None
    for key in ("from", "machine", "comment"):
        if not isinstance(record.get(key, ""), str):
            return None
    if not _is_int(record.get("bytes")) or not _is_int(record.get("sent")):
        return None
    if record["state"] == "ready" and not (
            allowed_url(record.get("url")) and _is_int(record.get("zip"))):
        return None
    record["kind"] = kind_of(name)
    return record


def from_event(event):
    """The record in one event of ntfy's JSON stream, or None."""
    if not isinstance(event, dict) or event.get("event") != "message":
        return None
    return parse(event.get("message"))


def merge(known, record):
    """Which of two records of one file to keep: the later state wins; a
    replay or an older state changes nothing (`known` itself comes back)."""
    if known is None:
        return record
    if _RANK[record["state"]] > _RANK[known["state"]]:
        return record
    return known


def is_mine(record, machine):
    """Sent from this machine (its id, not its sender's name)."""
    return bool(machine) and record.get("machine") == machine


def expired(record, now):
    """The file is past litterbox's keep."""
    return now - record["sent"] > LIFETIME


def visible(records, now):
    """The list's rows, newest first: not expired, not failed, and not a
    "sending" whose sender never finished."""
    out = []
    for record in records:
        if expired(record, now) or record["state"] == "failed":
            continue
        if (record["state"] == "sending"
                and now - record["sent"] > SENDING_TIMEOUT):
            continue
        out.append(record)
    return sorted(out, key=lambda r: (r["sent"], r["id"]), reverse=True)


def is_news(record, now):
    """Recent enough to announce. The channel replays its last hours when a
    Maya starts listening, and those are history."""
    return now - record["sent"] <= NEWS_WITHIN


def status_label(record, mine, progress=None, local=False, error=""):
    """The row's state."""
    if record["state"] == "failed":
        return "failed"
    if record["state"] == "sending":
        if mine and progress is not None:
            return "sending {0}%".format(int(progress * 100))
        return "sending..."
    if mine:
        return "sent"
    if local:
        return "ready"
    if error:
        return "failed, retry"
    if progress is not None:
        return "{0}%".format(int(progress * 100))
    return "waiting"


def size_text(size):
    """«340 KB», «12.3 MB», «1.20 GB»."""
    if size < 1024 * 1024:
        return "{0} KB".format(max(1, int(round(size / 1024.0))) if size
                               else 0)
    if size < 1024 ** 3:
        return "{0:.1f} MB".format(size / 1048576.0)
    return "{0:.2f} GB".format(size / 1073741824.0)


def when_text(sent, now):
    """«14:12» today, «29.09 14:12» another day, in local time."""
    at = time.localtime(sent)
    if time.strftime("%Y%m%d", at) == time.strftime("%Y%m%d",
                                                    time.localtime(now)):
        return time.strftime("%H:%M", at)
    return time.strftime("%d.%m %H:%M", at)


def _fit(text, width):
    text = " ".join((text or "").split())
    if len(text) > width:
        return text[:width - 2] + ".."
    return text


def row_text(record, mine, status, now):
    """One line of the list, in fixed columns."""
    who = "you" if mine else (record.get("from") or "someone")
    line = "{0:<{a}} {1:<{b}} {2:<{c}} {3:>{d}}  {4:<{e}}".format(
        _fit(record["name"], NAME_WIDTH), _fit(who, WHO_WIDTH), status,
        size_text(record["bytes"]), when_text(record["sent"], now),
        a=NAME_WIDTH, b=WHO_WIDTH, c=STATUS_WIDTH, d=SIZE_WIDTH, e=WHEN_WIDTH)
    comment = " ".join((record.get("comment") or "").split())
    return (line + " " + comment).rstrip() if comment else line.rstrip()


def inbox_folder(record):
    """The folder a file lands in under SkeldarShare/: when, who, which."""
    who = _SAFE.sub("_", record.get("from") or "").strip("_") or "someone"
    return "{0}_{1}_{2}".format(
        time.strftime("%Y-%m-%d_%H%M", time.localtime(record["sent"])),
        who[:24], record["id"][:6])


def announce_text(record):
    return "{0} sent {1}".format(record.get("from") or "someone",
                                 record["name"])


def archive_problems(names, name):
    """What is wrong with a received zip: it must hold `name` and nothing
    else, at its top."""
    if list(names) != [name]:
        return ["the archive holds {0}, not {1} alone".format(
            ", ".join(list(names)[:3]) or "nothing", name)]
    return []


def sender_default(user):
    return (user or "").strip() or "someone"


def subtitle(online, count):
    """The card's subtitle: the channel's state and how many files."""
    files = "{0} file{1}".format(count, "" if count == 1 else "s")
    if online == "online":
        return "online - " + files
    return "{0} - {1}".format(online, files)


def left_behind_note(names):
    """What a sent scene does not carry: textures that are not the plugin's."""
    if not names:
        return ""
    one = len(names) == 1
    shown = ", ".join(os.path.basename(n) for n in names[:3])
    more = " and {0} more".format(len(names) - 3) if len(names) > 3 else ""
    return "{0} texture{1} stay{2} on this machine: {3}{4}".format(
        len(names), "" if one else "s", "s" if one else "", shown, more)


def to_history(entries, since):
    """The history file's text: every entry and the channel's last id."""
    return json.dumps(
        {"v": HISTORY_VERSION, "since": since or "",
         "entries": [{"record": e["record"], "local": e.get("local") or ""}
                     for e in entries.values()]},
        ensure_ascii=False, indent=1, sort_keys=True)


def from_history(text, now):
    """(entries by id, since) from the history file's text. Expired and
    malformed entries are dropped; a broken file is an empty history."""
    try:
        data = json.loads(text)
    except (TypeError, ValueError):
        return {}, ""
    if not isinstance(data, dict) or data.get("v") != HISTORY_VERSION:
        return {}, ""
    entries = {}
    for item in data.get("entries") or []:
        if not isinstance(item, dict) or not isinstance(item.get("record"),
                                                        dict):
            continue
        record = parse(encode(item["record"]))
        if record is None or expired(record, now):
            continue
        local = item.get("local")
        entries[record["id"]] = {
            "record": record, "local": local if isinstance(local, str) else ""}
    since = data.get("since")
    return entries, since if isinstance(since, str) else ""
