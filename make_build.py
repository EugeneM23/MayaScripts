"""Build the SkeldarAnim distribution archive.

    mayapy make_build.py [--out <path>]

Writes `SkeldarAnim_<date>.zip` next to the repository folder: the same
payload the installer copies, wrapped in one `SkeldarAnim/` directory so
the instruction stays "unzip, drag SkeldarAnim/install.py into Maya".

The payload lives in the repo's `SkeldarAnim/` folder (2026-09-01) and
`install.py` with it, so this script puts that folder on sys.path before
importing the installer -- and derives the output directory from its OWN
location rather than the installer's, or the archive would land inside
the repository.

The composition comes from `install.payload()` and nowhere else. A second
whitelist here would drift from the installer on the first edit, and the
symptom -- a colleague's shelf button raising ImportError on a module the
archive never carried -- points at the wrong file entirely.

Development tool, not part of the payload: it never ships to the
animator's prefs.

Stdlib only, and `install` is stdlib-only at import by design, so this
runs outside Maya. There is no system Python on this machine; use mayapy.
"""

import datetime
import fnmatch
import os
import subprocess
import sys
import zipfile

PLUGIN = "SkeldarAnim"
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))

if os.path.join(REPO_ROOT, PLUGIN) not in sys.path:
    sys.path.insert(0, os.path.join(REPO_ROOT, PLUGIN))

import install  # noqa: E402  -- needs the line above

# Same exclusions the installer's copy applies. A .pyc in a handed-off
# archive is at best noise and at worst a stale compile of code the
# archive no longer holds.
_IGNORE = ("__pycache__", "*.pyc")

_STAMP = "BUILD_INFO.txt"


def _ignored(name):
    return any(fnmatch.fnmatch(name, pat) for pat in _IGNORE)


def payload_names():
    """What goes in, straight from the installer."""
    return install.payload()


def source_root():
    """The plugin folder: what the payload names are relative to."""
    return install.source_root()


def default_out_dir():
    """Beside the REPOSITORY folder, where the earlier archives live.

    Not beside `source_root()` any more -- since the payload moved into
    the repo's SkeldarAnim/ folder that would drop the archive inside the
    repository, one level in from where every earlier build landed.
    """
    return os.path.dirname(REPO_ROOT)


def archive_name(day=None):
    """`SkeldarAnim_2026-09-01.zip` -- dated, so builds never clobber."""
    day = day or datetime.date.today()
    return "{0}_{1}.zip".format(install.SHELF, day.isoformat())


def missing(src_root, names=None):
    """Payload entries the source tree does not have."""
    names = payload_names() if names is None else names
    return [n for n in names
            if not os.path.exists(os.path.join(src_root, n))]


def entries(src_root, names=None):
    """`(path on disk, name in the archive)` for everything shipped.

    Directories are entries of their own so empty ones survive the round
    trip: `overrig/misc/` is empty and load-bearing -- OverRig's own
    button points `$path_to_JGLBN` at it.
    """
    names = payload_names() if names is None else names
    top = install.SHELF
    found = []
    for name in names:
        path = os.path.join(src_root, name)
        if os.path.isfile(path):
            found.append((path, "{0}/{1}".format(top, name)))
            continue
        for walk_root, dirs, files in os.walk(path):
            dirs[:] = sorted(d for d in dirs if not _ignored(d))
            rel = os.path.relpath(walk_root, src_root).replace("\\", "/")
            found.append((walk_root, "{0}/{1}/".format(top, rel)))
            for f in sorted(files):
                if _ignored(f):
                    continue
                found.append((os.path.join(walk_root, f),
                              "{0}/{1}/{2}".format(top, rel, f)))
    return sorted(found, key=lambda pair: pair[1])


def _git(src_root, *args):
    try:
        out = subprocess.check_output(("git",) + args, cwd=src_root,
                                      stderr=subprocess.STDOUT)
    except Exception:
        return ""
    return out.decode("utf-8", "replace").strip()


def build_info(src_root, names=None, day=None):
    """Provenance for the archive.

    The two archives from 2026-08-21 are four minutes apart and there is
    no way to tell what is in either. One text file fixes that for good.
    """
    names = payload_names() if names is None else names
    day = day or datetime.datetime.now()
    branch = _git(src_root, "rev-parse", "--abbrev-ref", "HEAD") or "unknown"
    commit = _git(src_root, "log", "-1", "--oneline") or "unknown"
    dirty = _git(src_root, "status", "--porcelain", "--", *names)
    lines = [
        install.SHELF,
        "built:  {0}".format(day.strftime("%Y-%m-%d %H:%M")),
        "branch: {0}".format(branch),
        "commit: {0}".format(commit),
        "payload: {0}".format(", ".join(names)),
    ]
    if dirty:
        lines.append("UNCOMMITTED payload changes:")
        lines.extend("  " + line for line in dirty.splitlines())
    else:
        lines.append("payload matches the commit above")
    return "\n".join(lines) + "\n"


def write_archive(src_root, out_path, names=None, stamp=None):
    """The payload into `out_path`. Returns the archive names written."""
    written = []
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, arcname in entries(src_root, names):
            zf.write(path, arcname)
            written.append(arcname)
        if stamp:
            arcname = "{0}/{1}".format(install.SHELF, _STAMP)
            zf.writestr(arcname, stamp)
            written.append(arcname)
    return written


def verify(out_path, expected):
    """Read the finished archive back. Returns a list of complaints.

    Checking what we just wrote sounds redundant and is not: the failure
    this catches -- a payload entry silently absent -- reaches a colleague
    as an ImportError days later, with nothing left to point at.
    """
    problems = []
    with zipfile.ZipFile(out_path) as zf:
        bad = zf.testzip()
        if bad:
            problems.append("corrupt entry: {0}".format(bad))
        got = set(zf.namelist())
    want = set(expected)
    for name in sorted(want - got):
        problems.append("missing from the archive: {0}".format(name))
    for name in sorted(got - want):
        problems.append("unexpected in the archive: {0}".format(name))
    return problems


def build(out_path=None, src_root=None, names=None):
    """Write and verify the archive. Returns its path.

    A verification failure deletes the archive: a broken build must not
    leave something zip-shaped lying around to be handed off by mistake.
    """
    src_root = src_root or source_root()
    names = payload_names() if names is None else names
    absent = missing(src_root, names)
    if absent:
        raise RuntimeError(
            "not in {0}: {1}".format(src_root, ", ".join(absent)))
    if out_path is None:
        out_path = os.path.join(default_out_dir(), archive_name())
    out_dir = os.path.dirname(os.path.abspath(out_path))
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    stamp = build_info(src_root, names)
    written = write_archive(src_root, out_path, names, stamp)
    problems = verify(out_path, written)
    if problems:
        os.remove(out_path)
        raise RuntimeError("archive rejected:\n  "
                           + "\n  ".join(problems))
    return out_path


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    out_path = None
    if argv and argv[0] == "--out":
        out_path = argv[1]
    src_root = source_root()
    path = build(out_path, src_root)
    size = os.path.getsize(path)
    with zipfile.ZipFile(path) as zf:
        files = [n for n in zf.namelist() if not n.endswith("/")]
    print(build_info(src_root))
    print("{0}\n{1} files, {2:.1f} MB".format(
        path, len(files), size / (1024.0 * 1024.0)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
