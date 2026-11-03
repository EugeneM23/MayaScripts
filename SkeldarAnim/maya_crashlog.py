"""The crash log: the Python line of a hard crash, written where we can read it.

The animator, 2026-11-03: «Посмотри в логи мая вылетает при использовании
connection bake IK». There were no logs to look in. Maya writes
`%TEMP%\\MayaCrashLog<date>.dmp` and nothing readable, and a crash inside a Qt
timer's slot - 28 of them since 2026-10-24, the kind that loses work - says in
the dump only that *some* Python slot was running.

Python's faulthandler fills that gap: it installs a VECTORED exception handler,
which Windows runs before any SEH and before Maya's own crash handler, so it
prints the Python traceback of the faulting thread first. Measured 2026-11-03 in
a GUI Maya, crashed on purpose: the file named the function and the line.

So every session points faulthandler at `<userAppDir>/SkeldarCrash/crash.txt`.
A session that starts and finds a traceback in that file knows the previous one
crashed: it keeps the file under its own name (`crash_<stamp>.txt`, the newest
`KEEP` kept) and says in the Script Editor which line it died on. A crash is
then one line away instead of a minidump away.

It costs nothing while nothing crashes: the handler is passive, and the only
write is this session's one-line header. `enable()` never raises - an old Python
without faulthandler, a read-only prefs folder, a handler someone else owns:
each answers None and leaves Maya alone.

State on `sys._skeldar_crashlog` (trap 111): the open handle must outlive the
call, and a module an install purges must not open a second one."""

import os
import re
import sys
import time

FOLDER = "SkeldarCrash"
CURRENT = "crash.txt"
KEPT = "crash_%s.txt"
KEEP = 20                    # the newest kept reports
STATE = "_skeldar_crashlog"

#  faulthandler's own words, whatever the platform: "Windows fatal exception",
#  "Fatal Python error", and the frame list it prints under them.
MARKERS = ("fatal exception", "Fatal Python error", "Current thread",
           "Stack (most recent call first)")
FRAME = re.compile(r'^\s*File "(?P<path>[^"]+)", line (?P<line>\d+) in (?P<fn>.+)$')

#  `faulthandler=REAL` means "import it yourself"; None means "there is none".
REAL = object()


# ------------------------------------------------------------------ the file

def _app_dir(given=None):
    if given:
        return given
    import maya.cmds as cmds
    return cmds.internalVar(userAppDir=True)


def folder(app_dir=None):
    """The folder our reports live in."""
    return os.path.join(_app_dir(app_dir), FOLDER)


def path(app_dir=None):
    """The file this session's faulthandler writes to."""
    return os.path.join(folder(app_dir), CURRENT)


def reports(app_dir=None):
    """The kept crash reports, newest first."""
    try:
        names = os.listdir(folder(app_dir))
    except OSError:
        return []
    out = [os.path.join(folder(app_dir), n) for n in names
           if n.startswith("crash_") and n.endswith(".txt")]
    return sorted(out, key=os.path.basename, reverse=True)


# ------------------------------------------------------------------ reading

def is_crash(text):
    """True when `text` holds a faulthandler report and not just our header."""
    return any(mark in (text or "") for mark in MARKERS)


def blamed(text):
    """The newest Python frame of a report, as one line: «file line N in fn».

    faulthandler prints the faulting thread's frames most recent first, so the
    first frame is where it died."""
    for raw in (text or "").splitlines():
        found = FRAME.match(raw)
        if found:
            return "%s line %s in %s" % (
                os.path.basename(found.group("path")),
                found.group("line"), found.group("fn").strip())
    return "no Python frame"


def previous():
    """What the previous session's crash said, or None - set by `enable`."""
    return _state().get("previous")


# ------------------------------------------------------------------ enabling

def _state():
    st = getattr(sys, STATE, None)
    if st is None:
        st = {"handle": None, "path": None, "previous": None}
        setattr(sys, STATE, st)
    return st


def enabled():
    return _state().get("handle") is not None


def forget():
    """Drop the session's handle (the tests, and an install's teardown)."""
    st = _state()
    handle = st.get("handle")
    st["handle"] = st["path"] = st["previous"] = None
    try:
        if handle is not None:
            handle.close()
    except Exception:                                        # noqa: BLE001
        pass


def _keep_previous(app_dir):
    """A traceback left in the current file is the previous session's crash:
    keep it under its own name and answer what it said."""
    here = path(app_dir)
    try:
        with open(here) as fh:
            text = fh.read()
    except OSError:
        return None
    if not is_crash(text):
        return None
    stamp = time.strftime("%Y%m%d_%H%M%S",
                          time.localtime(os.path.getmtime(here)))
    kept = os.path.join(folder(app_dir), KEPT % stamp)
    while os.path.exists(kept):
        stamp += "a"
        kept = os.path.join(folder(app_dir), KEPT % stamp)
    try:
        os.replace(here, kept)
    except OSError:
        return text
    for old in reports(app_dir)[KEEP:]:
        try:
            os.remove(old)
        except OSError:
            pass
    return text


def enable(app_dir=None, faulthandler=REAL):
    """Point faulthandler at our file for this session; answer its path.

    Answers None and leaves Maya alone when it cannot: no faulthandler, a
    folder it cannot write, a handler that refuses. Called once a session -
    a second call does nothing."""
    st = _state()
    if st.get("handle") is not None:
        return st.get("path")
    if faulthandler is REAL:
        try:
            import faulthandler as module
        except ImportError:
            return None
    else:
        module = faulthandler
    if module is None:
        return None
    try:
        here = path(app_dir)
        made = folder(app_dir)
        if not os.path.isdir(made):
            os.makedirs(made)
        st["previous"] = _keep_previous(app_dir)
        handle = open(here, "w")
        handle.write("SkeldarAnim %s pid %d  (a traceback below means this "
                     "session crashed)\n"
                     % (time.strftime("%Y-%m-%d %H:%M:%S"), os.getpid()))
        handle.flush()
        module.enable(file=handle, all_threads=True)
    except Exception:                                        # noqa: BLE001
        return None
    st["handle"] = handle
    st["path"] = here
    return here


def report(app_dir=None, faulthandler=REAL):
    """`enable`, and the one line to print: what the previous crash blamed."""
    here = enable(app_dir, faulthandler=faulthandler)
    if here is None:
        return "SkeldarAnim: no crash log (faulthandler is not available)"
    text = previous()
    if not text:
        return "SkeldarAnim: crashes are logged to %s" % here
    return ("SkeldarAnim: the previous session CRASHED at %s - the whole "
            "report is in %s" % (blamed(text), folder(app_dir)))
