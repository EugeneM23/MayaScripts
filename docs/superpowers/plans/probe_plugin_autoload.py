"""probe_plugin_autoload.py - how Maya autoloads a Python plug-in (2026-10-08, Task 13).

What `install.register_startup` rests on, measured before it was written. Runs in a
DISPOSABLE GUI Maya - never the animator's: launch maya.exe with a scratch
`MAYA_APP_DIR` (a short path), `MAYA_NO_HOME=1`, and a `userSetup.py` in
`<MAYA_APP_DIR>/2027/scripts/` that opens a commandPort of its own; send this file over
it as ONE globals dict - `exec(compile(open(P, encoding='utf-8').read(), P, 'exec'),
{'__name__': '__main__'})` with P this file's path: a bare `exec(open(P).read())` runs
with globals and locals apart, and the functions below then see neither the imports nor
the constants (trap 17; it cost this probe a run). The port runs a line twice, hence the
`.ran` guard. Two phases:

    PHASE = 1   two probe plug-ins written, each writing a marker line from
                initializePlugin: A in a folder NOT on MAYA_PLUG_IN_PATH, B in the
                user's `<userAppDir>/<version>/plug-ins`. Both loaded by full path, set
                to autoload, the plug-in prefs saved; the prefs lines, MAYA_PLUG_IN_PATH,
                and what the loader gives a plug-in (`__file__`, `__name__`,
                `pluginInfo -path`) printed. Then kill that Maya and start it again
                with the same MAYA_APP_DIR.
    PHASE = 2   which of the two Maya loaded at its start (the markers, pluginInfo).

A's load puts up Maya 2027's modal «Untrusted Plugin Loading - Security Warning»
(Allow / Deny) - over the port that blocks the idle queue until it is answered; answer
it Allow (by hand, or UI Automation's Invoke on the "Allow" button).

What it answered on Maya 2027.2 (2026-10-08):
- the prefs line is the FILE NAME only: `evalDeferred("autoLoadPlugin(\\"\\",
  \\"skProbe.py\\", \\"skProbe\\")");` - A was not loaded at the next start, B was;
- MAYA_PLUG_IN_PATH = `<MAYA_APP_DIR>/2027/plug-ins;<MAYA_APP_DIR>/plug-ins;...`, the
  user folders on it whether they exist or not;
- B loaded by its path with no dialog even though its folder was made after Maya
  started; by NAME it was "not found on MAYA_PLUG_IN_PATH" in that session;
- `__file__` and `__name__` read None in the plug-in at import and in initializePlugin;
  `pluginInfo -query -path` answered the full path there.
"""

import os
import sys
import traceback

PHASE = 1
OUT = r"C:/tmp_sk13/out/probe_plugin_autoload_{0}.txt".format(PHASE)
SCRATCH = r"C:/tmp_sk13/probe"                  # not on MAYA_PLUG_IN_PATH

PROBE = '''
import time
MARK = r"{mark}"
SEEN = (repr(globals().get("__file__")), repr(globals().get("__name__")))


def maya_useNewAPI():
    pass


def initializePlugin(plugin):
    import maya.api.OpenMaya as om
    import maya.cmds as cmds
    om.MFnPlugin(plugin, "probe", "1.0")
    with open(MARK, "a") as handle:
        handle.write("init %s __file__=%s __name__=%s pluginInfo -path=%r\\n" % (
            time.ctime(), SEEN[0], SEEN[1],
            cmds.pluginInfo("{name}", query=True, path=True)))


def uninitializePlugin(plugin):
    import maya.api.OpenMaya as om
    om.MFnPlugin(plugin)
'''


def _probes(cmds):
    user = os.path.join(cmds.internalVar(userAppDir=True),
                        str(cmds.about(version=True)), "plug-ins")
    out = os.path.dirname(OUT)
    return [("skProbeA", SCRATCH, os.path.join(out, "skProbeA_marker.txt")),
            ("skProbeB", user, os.path.join(out, "skProbeB_marker.txt"))]


def phase_1(cmds):
    print("MAYA_PLUG_IN_PATH", os.environ.get("MAYA_PLUG_IN_PATH"))
    for name, folder, mark in _probes(cmds):
        if not os.path.isdir(folder):
            os.makedirs(folder)
        path = os.path.join(folder, name + ".py").replace("\\", "/")
        with open(path, "w") as handle:
            handle.write(PROBE.format(mark=mark.replace("\\", "/"), name=name))
        try:
            print("by name", name, cmds.loadPlugin(name))
        except RuntimeError as error:
            print("by name", name, "-", error)
        print("by path", path, cmds.loadPlugin(path))
        cmds.pluginInfo(name, edit=True, autoload=True)
    cmds.pluginInfo(savePluginPrefs=True)
    with open(os.path.join(cmds.internalVar(userPrefDir=True), "pluginPrefs.mel")) as h:
        for line in h:
            if "skProbe" in line:
                print("PREFS", line.rstrip())


def phase_2(cmds):
    for name, _folder, mark in _probes(cmds):
        print(name, "loaded at start:", cmds.pluginInfo(name, query=True, loaded=True))
        print(open(mark).read() if os.path.exists(mark) else "(no marker)")


_RAN = OUT + ".ran"
if not os.path.exists(_RAN):
    open(_RAN, "w").close()
    _handle = open(OUT, "w")
    _saved = sys.stdout, sys.stderr
    sys.stdout = sys.stderr = _handle
    try:
        import maya.cmds as _cmds
        (phase_1 if PHASE == 1 else phase_2)(_cmds)
    except Exception:                                         # noqa: BLE001
        traceback.print_exc()
    finally:
        print("DONE")
        sys.stdout, sys.stderr = _saved
        _handle.close()
