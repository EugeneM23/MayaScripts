"""Where the animations come from: Unreal, a Unity project, a folder. stdlib only.

2026-10-02, the animator: «я бы хотел что бы у нас была возможность
подключаться не только к анриал енжину а и к Unity, и просто к папке с FBX
файлами.......хорошо бы было сделать максимальный обхват форматов».

Every source fills the SAME list with the same `records.AnimRecord`, so the
search, the multiple selection, the double click, Import Animation, the drag
into the viewport and the square of several all work for every source with
no road of their own. What differs is one step - getting the clip out:

- an Unreal record (`source == "unreal"`) is exported by the editor, as
  since 2026-08-16;
- a file record names its file and its clip, and the clip REFERENCE
  (`ref`) is what the roads hand the import funnel (`rigimport.
  import_source`) in place of an FBX path: `C:/a/walk.fbx` for a whole
  file, `C:/a/pack.fbx|take=2` for one take, `C:/a/x.glb|anim=1`,
  `C:/u/Bow.fbx|take_name=Take 001&first=0&last=5` for a Unity clip. `|`
  cannot be in a Windows path, so the split is unambiguous.

The scan is pure over two callbacks (`walk`, `takes_of`), so the rules are
tested without a disk or a Maya: one row per clip a file holds, the folder
it lives in shown after the name, the format beside the frame count.
"""

import hashlib
import os
from urllib.parse import parse_qsl, urlencode

from maya_uebridge import records

SOURCES = ("unreal", "unity", "folder")
LABELS = {"unreal": "Unreal", "unity": "Unity", "folder": "Folder"}

#  What a folder can hold, by extension -> format.
FORMATS = {
    ".fbx": "fbx", ".dae": "dae", ".ma": "ma", ".mb": "mb",
    ".bvh": "bvh", ".gltf": "gltf", ".glb": "gltf",
    ".usd": "usd", ".usda": "usd", ".usdc": "usd", ".usdz": "usd",
    ".anim": "anim",
}
#  A Unity project's: what Unity imports as a model, and its own clips.
UNITY_FORMATS = (".fbx", ".dae", ".anim")
SKIP_DIRS = ("library", "temp", "logs", "obj", "build", "builds", ".git",
             "__pycache__", "packagecache")
SEPARATOR = "|"


def fmt_of(path):
    """The format a file is read as, "" when we do not read it. Pure."""
    return FORMATS.get(os.path.splitext(path or "")[1].lower(), "")


def ref(path, clip=""):
    """The clip reference the import funnel takes. Pure."""
    path = (path or "").replace("\\", "/")
    return path + SEPARATOR + clip if clip else path


def split_ref(text):
    """(path, {clip parameters}) of a reference. Pure."""
    path, _, clip = (text or "").partition(SEPARATOR)
    return path, dict(parse_qsl(clip, keep_blank_values=True))


def clip_text(**parts):
    """`take=2` and friends, in a stable order. Pure."""
    return urlencode(sorted((k, v) for k, v in parts.items() if v is not None
                            and v != ""))


def is_plain_fbx(text):
    """True for a whole FBX with no clip inside it named - the road the
    import funnel always took, `animimport.import_clip`. Pure."""
    path, clip = split_ref(text)
    return not clip and fmt_of(path) in ("fbx", "")


def record_ref(record):
    """The reference a file record imports through."""
    return ref(record.path, record.clip)


def file_record(path, name, clip="", frames=None, length=None, fps=None,
                source="folder", note=""):
    """A list row for a clip in a file. `package` - the record's identity
    for the selection and the search - is the reference itself. Pure."""
    path = path.replace("\\", "/")
    return records.AnimRecord(
        name=name, package=ref(path, clip), skeleton=note, frames=frames,
        length=length, fps=fps, source=source, path=path, clip=clip,
        fmt=fmt_of(path))


def cache_name(source, location):
    """The json a source's listing is cached in (temp folder). Pure."""
    digest = hashlib.md5(os.path.normcase(os.path.normpath(location or ""))
                         .encode("utf-8")).hexdigest()[:12]
    return "maya_uebridge_{0}_{1}.json".format(source, digest)


def frames_of(start, end):
    """A row's frame count from a span in frames. Pure."""
    if start is None or end is None:
        return None
    return int(round(end - start)) + 1


# ------------------------------------------------------------------ scanning

def walk_files(top, extensions, walk=os.walk, skip=SKIP_DIRS):
    """Every file under `top` with one of `extensions`, sorted, skipping the
    caches and build folders (Unity's Library, git) a walk must not enter."""
    out = []
    for folder, dirs, files in walk(top):
        dirs[:] = sorted(d for d in dirs if d.lower() not in skip
                         and not d.startswith("."))
        for name in files:
            if os.path.splitext(name)[1].lower() in extensions:
                out.append(os.path.join(folder, name).replace("\\", "/"))
    return sorted(out, key=lambda p: p.lower())


def take_rows(path, takes, source="folder", note=""):
    """Rows for a file of FBX takes `takes` [(index, name, start, end)]:
    one row when it holds one take (named for the file), one row per take
    otherwise (`stem · take`). A take that spans nothing is no animation.
    Pure."""
    stem = os.path.basename(path)          # the file, extension and all
    moving = [t for t in takes if t[3] is not None and t[2] is not None
              and t[3] > t[2]]
    if len(moving) <= 1:
        span = moving[0] if moving else None
        return [file_record(path, stem, "", frames_of(span[2], span[3]) if span
                            else None, source=source, note=note)]
    return [file_record(path, "{0} · {1}".format(stem, name),
                        clip_text(take=index), frames_of(start, end),
                        source=source, note=note)
            for index, name, start, end in moving]


def unity_model_rows(path, meta_clips, takes, source="unity"):
    """Rows for a Unity model file: one per clip its .meta defines
    [(name, takeName, first, last)], else one per take. Pure."""
    if not meta_clips:
        return take_rows(path, takes, source=source)
    rows = []
    for name, take_name, first, last in meta_clips:
        rows.append(file_record(
            path, name or os.path.splitext(os.path.basename(path))[0],
            clip_text(take_name=take_name, first="{0:g}".format(first),
                      last="{0:g}".format(last)),
            frames_of(first, last), source=source))
    return rows


def anim_row(path, summary, source="unity"):
    """A row for a Unity .anim from `unityfiles.anim_summary`. A clip we
    cannot import keeps its row, with the reason in its note. Pure."""
    rate = summary.get("rate") or None
    frames = None
    if rate and summary.get("stop") is not None:
        frames = int(round(((summary.get("stop") or 0.0)
                            - (summary.get("start") or 0.0)) * rate)) + 1
    note = {"humanoid": "humanoid", "compressed": "compressed",
            "empty": "no curves"}.get(summary.get("kind"), "")
    name = summary.get("name") or os.path.splitext(os.path.basename(path))[0]
    return file_record(path, name, "", frames, fps=rate, source=source,
                       note=note)


def scan(top, source, takes_of, read_text=None, progress=None, walk=os.walk):
    """Every clip under `top` as records, sorted by name. `takes_of(path)`
    answers an FBX's takes [(index, name, start, end)] (Maya's FBXRead,
    cached by the caller); `read_text(path)` a text file; `progress(done,
    total, path)` answers False to stop. Pure over its callbacks."""
    from maya_uebridge import bvh, gltf, unityfiles
    read_text = read_text or _read_text
    if source == "unity":
        files = walk_files(os.path.join(top, "Assets"), UNITY_FORMATS, walk)
    else:
        files = walk_files(top, tuple(FORMATS), walk)
    out = []
    for done, path in enumerate(files):
        if progress is not None and progress(done, len(files), path) is False:
            break
        fmt = fmt_of(path)
        try:
            if fmt == "anim":
                summary = unityfiles.anim_summary(read_text(path))
                if summary["kind"] != "empty":
                    out.append(anim_row(path, summary, source))
            elif source == "unity" and fmt in ("fbx", "dae"):
                meta = _read_or_empty(read_text, path + ".meta")
                if meta and unityfiles.meta_value(meta, "importAnimation") == "0":
                    continue
                takes = takes_of(path) if fmt == "fbx" else [(1, "", 0.0, 1.0)]
                out.extend(unity_model_rows(path, unityfiles.meta_clips(meta),
                                            takes, source))
            elif fmt == "fbx":
                out.extend(take_rows(path, takes_of(path), source))
            elif fmt == "bvh":
                joints, frames, fps = bvh.summary(read_text(path))
                out.append(file_record(path, _stem(path), "", frames, fps=fps,
                                       source=source))
            elif fmt == "gltf":
                doc, _buffers = gltf.load(path) if path.lower().endswith(".gltf") \
                    else (gltf.split_glb(_read_bytes(path))[0], None)
                for clip in gltf.clips(doc):
                    name = (_stem(path) if len(doc.get("animations") or []) == 1
                            else "{0} · {1}".format(_stem(path), clip.name))
                    out.append(file_record(path, name, clip_text(anim=clip.index),
                                           None, source=source))
            else:                     # ma, mb, dae, usd: one clip a file
                out.append(file_record(path, _stem(path), "", None, source=source))
        except Exception as error:                           # noqa: BLE001
            out.append(file_record(path, _stem(path), "", None, source=source,
                                   note="unreadable: {0}".format(
                                       str(error).splitlines()[0][:60]
                                       if str(error) else type(error).__name__)))
    out.sort(key=lambda r: (r.name.lower(), r.package.lower()))
    return out


def _stem(path):
    """A whole-file row's name: the file NAME with its extension - six formats
    of one clip are six rows that must read apart (measured in the card)."""
    return os.path.basename(path)


def _read_text(path):
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        return handle.read()


def _read_bytes(path):
    with open(path, "rb") as handle:
        return handle.read()


def _read_or_empty(read_text, path):
    try:
        return read_text(path) if os.path.isfile(path) else ""
    except (OSError, IOError):
        return ""


# ------------------------------------------------------------------ menus

def recent(paths, chosen, limit=12):
    """`chosen` first, then the rest without it, at most `limit`. Pure."""
    key = os.path.normcase(os.path.normpath(chosen)) if chosen else None
    rest = [p for p in paths or []
            if os.path.normcase(os.path.normpath(p)) != key]
    return ([chosen] if chosen else []) + rest[:max(0, limit - (1 if chosen else 0))]


def header_line(source, location, count, cached):
    """The line under the switch for a file source. Pure."""
    label = LABELS.get(source, source)
    if not location:
        return ("{0}: pick a {1} - Browse... in the list".format(
            label, "project" if source == "unity" else "folder"))
    where = location.replace("\\", "/")
    if cached:
        return "{0}: {1} animations in {2} (last scan) - Refresh rescans".format(
            label, count, where)
    if count is None:
        return "{0}: {1} - press Refresh to scan it".format(label, where)
    return "{0}: {1} animations in {2}".format(label, count, where)
