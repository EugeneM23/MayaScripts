"""Quitting Maya with our interface standing writes no crash dump (2026-11-02).

Three throwaway GUI Mayas, each with its own MAYA_APP_DIR (the animator's prefs are
never touched), started minimised and driven over a command port:

  armed     the animator's own set standing -- rail hub, Time Bar at the bottom edge,
            side panel at the right edge holding Maya's Channel Box and Attribute
            Editor, our Channel Box, viewport bar, main bar -- then quit.
            Gate: no new dump.
  disarmed  the same, with the kMayaExiting hook taken off before the quit: the
            control, so the gate above can fail. Gate: a dump, and it is shiboken6.
  plain     nothing of ours. Gate: no dump.

    mayapy verify_shutdown.py [armed|disarmed|plain|all]

Maya's crash handler writes the dump and then exits 0, so the exit code proves
nothing. A dump is attributed by the PID in its MiscInfo stream, never by "it
appeared after my quit": the animator has Mayas of their own open, two crashes in
one minute share one filename (Maya names the file to the minute, so the later
overwrites the earlier), and either mistake makes every gate meaningless. For the
same reason, run this ALONE: a second Maya crashing in the same minute can
overwrite our dump with its own pid and turn a crash into a clean "no dump".

2026-11-02: `disarmed` and `plain` pass -- the control crashes in shiboken6, a
plain Maya does not -- and **`armed` FAILS**: the cleanup does not cure the exit
crash. It is the standing failing test. What has been ruled out (every widget,
QObject and effect of ours destroyed; our state cleared; 221 modules purged) is in
`docs/superpowers/specs/2026-11-02-shutdown-cleanup-design.md`.
"""
import glob
import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.normpath(os.path.join(HERE, "..", "..", "..", "SkeldarAnim"))
MAYA = r"C:\Program Files\Autodesk\Maya2027\bin\maya.exe"
TEMP = os.environ["TEMP"]

FAILED = []
N = [0]


def gate(ok, text):
    N[0] += 1
    print("  %-4s %s" % ("ok" if ok else "FAIL", text))
    if not ok:
        FAILED.append(text)


# ----------------------------------------------------------------- the dump

def dumps():
    return set(glob.glob(os.path.join(TEMP, "MayaCrashLog*.dmp")))


def dump_pid(path):
    """The pid the dump was written for (MiscInfo), or None.

    A dump is attributed by PID, never by "it appeared after my quit": the animator
    has Mayas of their own open, Maya can take longer than a few seconds to finish
    writing, and a wrong attribution here would make every gate meaningless."""
    try:
        with open(path, "rb") as fh:
            blob = fh.read(0x4000)
    except OSError:
        return None
    if blob[:4] != b"MDMP":
        return None
    count, directory = struct.unpack_from("<II", blob, 8)
    for i in range(count):
        kind, _size, rva = struct.unpack_from("<III", blob, directory + 12 * i)
        if kind == 15 and rva + 12 <= len(blob):          # MiscInfoStream
            return struct.unpack_from("<I", blob, rva + 8)[0]
    return None


def dump_for(pid, seconds=40):
    """The dump written for `pid`, waiting for Maya's handler to finish writing it."""
    for _ in range(seconds):
        for path in dumps():
            if dump_pid(path) == pid:
                return path
        time.sleep(1)
    return None


def faulting_module(path):
    """Which module the exception address falls in: the module list and the
    exception stream of a minidump, by hand (there is no debugger here)."""
    with open(path, "rb") as fh:
        blob = fh.read()
    if blob[:4] != b"MDMP":
        return "?"
    count, directory = struct.unpack_from("<II", blob, 8)
    streams = {}
    for i in range(count):
        kind, _size, rva = struct.unpack_from("<III", blob, directory + 12 * i)
        streams[kind] = rva
    if 6 not in streams or 4 not in streams:
        return "?"
    address = struct.unpack_from("<Q", blob, streams[6] + 8 + 16)[0]
    modules = struct.unpack_from("<I", blob, streams[4])[0]
    for i in range(modules):
        at = streams[4] + 4 + 108 * i
        base, size = struct.unpack_from("<QI", blob, at)
        name_rva = struct.unpack_from("<I", blob, at + 20)[0]
        if base <= address < base + size:
            length = struct.unpack_from("<I", blob, name_rva)[0]
            name = blob[name_rva + 4:name_rva + 4 + length].decode("utf-16-le", "replace")
            return os.path.basename(name)
    return "?"


# ----------------------------------------------------------------- the port

def send(port, code, timeout=900):
    try:
        s = socket.create_connection(("127.0.0.1", port), timeout=10)
    except OSError as err:
        return "no connection: %s" % err
    try:
        s.settimeout(timeout)
        s.sendall(code.encode("utf-8") + b"\n")
        try:
            return s.recv(65536).decode("utf-8", "replace").strip()
        except OSError:
            return ""
    finally:
        s.close()


def payload(port, scratch, name, body, wait=120):
    """Run a body in Maya once and read back the JSON it wrote. The port's reply is
    NOT the body's output, and the port runs a sent line twice (bridge note 5), so
    the body is guarded by a marker file - never by a raise (note 8)."""
    out = os.path.join(scratch, name + ".json").replace("\\", "/")
    path = os.path.join(scratch, name + ".py")
    guard = path + ".ran"
    with open(path, "w") as fh:
        fh.write("import os\n")
        fh.write("if not os.path.exists(r'%s'):\n" % guard)
        fh.write("    open(r'%s', 'w').close()\n" % guard)
        for line in body.replace("@OUT@", out).splitlines():
            fh.write("    " + line + "\n")
    send(port, "exec(open(r'%s').read(), {'__name__': 'verify'})" % path)
    for _ in range(wait):
        if os.path.exists(out):
            try:
                with open(out) as fh:
                    return json.load(fh)
            except ValueError:
                pass
        time.sleep(1)
    return {"error": "no report written"}


USER_SETUP = '''
import maya.cmds as cmds
import maya.utils


def _port():
    try:
        if not cmds.commandPort(":%(port)d", query=True):
            cmds.commandPort(name=":%(port)d", sourceType="python", echoOutput=False)
    except Exception:
        pass


maya.utils.executeDeferred(_port)
'''

INSTALL = '''
import json, sys, traceback
r = {}
try:
    sys.path.insert(0, r"@PLUGIN@")
    import install
    install.install(quiet=True)
    r["ok"] = True
except Exception:
    r["error"] = traceback.format_exc()
with open(r"@OUT@", "w") as fh:
    json.dump(r, fh)
'''

SETUP = '''
import json, traceback
import maya.cmds as cmds
r = {}
try:
    for key, value in (("skeldarAnimHub_layout", "rail"),
                       ("skeldarTimeBarMode", "edge"),
                       ("skeldarSidePanelMode", "edge")):
        cmds.optionVar(stringValue=(key, value))
    for key, value in (("skeldarChannelBoxOurs", 1), ("skeldarViewportBar", 1),
                       ("skeldarMainBar", 1), ("skeldarTimeBar", 1),
                       ("skeldarSidePanelPinned", 1), ("skeldarTimeBarPinned", 1)):
        cmds.optionVar(intValue=(key, value))
    import maya_hub
    maya_hub.show()
    r["ok"] = True
except Exception:
    r["error"] = traceback.format_exc()
with open(r"@OUT@", "w") as fh:
    json.dump(r, fh)
'''

CHECK = '''
import json, sys, traceback
import maya.cmds as cmds
r = {}
try:
    import maya_hub, maya_shutdown
    r["hub"] = bool(maya_hub.is_skinned())
    r["armed"] = getattr(sys, maya_shutdown.STATE, {}).get("callback") is not None
    try:
        import maya_timebar
        r["timebar"] = maya_timebar.active() is not None
    except Exception as err:
        r["timebar"] = "n/a: %r" % (err,)
    try:
        import maya_sidepanel
        r["holds"] = sorted(t for t in ("channels", "attributes")
                            if maya_sidepanel.holds(t))
    except Exception as err:
        r["holds"] = "n/a: %r" % (err,)
    from PySide6 import QtWidgets
    r["our_windows"] = sorted(set(
        w.objectName() or type(w).__name__
        for w in QtWidgets.QApplication.topLevelWidgets()
        if maya_shutdown.ours(type(w).__module__)))
except Exception:
    r["error"] = traceback.format_exc()
with open(r"@OUT@", "w") as fh:
    json.dump(r, fh, default=str)
'''

DISARM = '''
import json, traceback
r = {}
try:
    import maya_shutdown
    r["was_armed"] = bool(maya_shutdown.disarm())
except Exception:
    r["error"] = traceback.format_exc()
with open(r"@OUT@", "w") as fh:
    json.dump(r, fh)
'''


def start(mode, port):
    scratch = os.path.join(TEMP, "verify_shutdown_%s" % mode)
    shutil.rmtree(scratch, ignore_errors=True)
    scripts = os.path.join(scratch, "2027", "scripts")
    os.makedirs(scripts)
    with open(os.path.join(scripts, "userSetup.py"), "w") as fh:
        fh.write(USER_SETUP % {"port": port})
    env = dict(os.environ)
    env["MAYA_APP_DIR"] = scratch
    env["MAYA_NO_HOME"] = "1"
    for junk in ("PYTHONPATH", "MAYA_SCRIPT_PATH", "MAYA_MODULE_PATH"):
        env.pop(junk, None)
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 7   # minimised, not activated: the animator keeps their focus
    proc = subprocess.Popen([MAYA], env=env, startupinfo=si)
    begin = time.time()
    while time.time() - begin < 300 and proc.poll() is None:
        try:
            socket.create_connection(("127.0.0.1", port), timeout=2).close()
            time.sleep(10)          # let Maya finish its own UI
            return proc, scratch
        except OSError:
            time.sleep(2)
    return proc, None


def run(mode, port):
    print("[%s]" % mode)
    proc, scratch = start(mode, port)
    if scratch is None:
        gate(False, "[%s] Maya came up and opened its port" % mode)
        try:
            proc.kill()
        except OSError:
            pass
        return
    try:
        if mode != "plain":
            report = payload(port, scratch, "install",
                             INSTALL.replace("@PLUGIN@", PLUGIN), wait=180)
            gate(report.get("ok") is True and
                 os.path.isdir(os.path.join(scratch, "scripts", "SkeldarAnim")),
                 "[%s] the plugin installed (%s)" % (mode, report.get("error", "")[:90]))
            report = payload(port, scratch, "setup", SETUP)
            gate(report.get("ok") is True,
                 "[%s] the interface came up (%s)" % (mode, report.get("error", "")[:90]))
            time.sleep(12)
            state = payload(port, scratch, "check", CHECK)
            gate(state.get("hub") is True, "[%s] the hub's skin stands" % mode)
            gate(state.get("timebar") is True,
                 "[%s] the Time Bar is up at the edge" % mode)
            gate(state.get("holds") == ["attributes", "channels"],
                 "[%s] the side panel holds Maya's Channel Box AND Attribute Editor "
                 "(%s)" % (mode, state.get("holds")))
            gate(len(state.get("our_windows") or []) >= 2,
                 "[%s] our own top-level windows stand (%d)"
                 % (mode, len(state.get("our_windows") or [])))
            if mode == "disarmed":
                off = payload(port, scratch, "disarm", DISARM)
                gate(off.get("was_armed") is True,
                     "[%s] the hook was armed, and is now off" % mode)
            else:
                gate(state.get("armed") is True,
                     "[%s] the kMayaExiting hook is armed" % mode)

        send(port, "import maya.cmds as _c; _c.quit(force=True)", timeout=30)
        for _ in range(240):
            if proc.poll() is not None:
                break
            time.sleep(1)
        if proc.poll() is None:
            gate(False, "[%s] Maya quit when asked" % mode)
            return
        mine = dump_for(proc.pid)
        name = os.path.basename(mine) if mine else "none"
        if mode == "disarmed":
            gate(bool(mine), "[%s] the control crashed on quit, as it used to (%s)"
                 % (mode, name))
            gate(bool(mine) and faulting_module(mine) == "shiboken6.abi3.dll",
                 "[%s] and it is the animator's own crash: %s"
                 % (mode, faulting_module(mine) if mine else "no dump"))
        else:
            gate(mine is None, "[%s] quitting wrote no crash dump for pid %d (%s)"
                 % (mode, proc.pid, name))
    finally:
        if proc.poll() is None:
            proc.kill()


def main(which):
    modes = ("armed", "disarmed", "plain") if which == "all" else (which,)
    for i, mode in enumerate(modes):
        run(mode, 7130 + i)
    print("%d of %d gates failed" % (len(FAILED), N[0]))
    for text in FAILED:
        print("   %s" % text)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "all")
