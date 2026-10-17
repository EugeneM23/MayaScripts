"""Proof of Maya icons (2026-10-17) in a GUI Maya - a scratch one with its
own MAYA_APP_DIR, never the animator's - sent over its command port:

On through `set_enabled(True)`: every PNG of Maya's Qt resources (1x, _150,
_200) drawn or recoloured into <userAppDir>/<version>/SkeldarIcons; every
icon button of Maya pointed there by full path, in EVERY viewport (Maya names
their buttons alike); a panel built afterwards caught by the watch; Off
giving every button back and emptying the folder. Prints a line a gate.
Run twice: once to switch on (then wait 3 s for the watch), once with
VERIFY_PHASE = "off".
"""

import os
import sys

sys.path.insert(0, r"C:/!!!Work/MayaScripts/SkeldarAnim")
import maya.cmds as cmds                                      # noqa: E402
import maya_mayaicons as icons                                # noqa: E402

PHASE = globals().get("VERIFY_PHASE", "on")
RESULTS = []


def gate(name, ok, detail=""):
    RESULTS.append(ok)
    print("%s  %s  %s" % ("PASS" if ok else "FAIL", name, detail))


def on_ours():
    hits, total = 0, 0
    for kind, flag in icons.KINDS:
        for control in cmds.lsUI(type=kind, long=True) or []:
            try:
                image = getattr(cmds, kind)(control, query=True, **{flag: True})
            except Exception:                                # noqa: BLE001
                continue
            total += 1
            hits += "SkeldarIcons" in (image or "")
    return hits, total


folder = icons.icon_folder()
if PHASE == "on":
    message = icons.set_enabled(True)
    print(message)
    files = [n for n in os.listdir(folder) if n.endswith(".png")]
    gate("every size written", any(n.endswith("_150.png") for n in files)
         and any(n.endswith("_200.png") for n in files), "%d files" % len(files))
    shaded = [c for c in cmds.lsUI(type="iconTextCheckBox", long=True) or []
              if c.endswith("|ShadedBtn")]
    ours = [c for c in shaded if "SkeldarIcons" in
            cmds.iconTextCheckBox(c, query=True, image1=True)]
    gate("every viewport's Shaded button on ours", shaded and len(ours) == len(shaded),
         "%d of %d" % (len(ours), len(shaded)))
    import maya.mel as mel
    mel.eval("GraphEditor;")
    print("now wait 3 s, then run with VERIFY_PHASE = 'watch'")
elif PHASE == "watch":
    hits, total = on_ours()
    gate("the Graph Editor opened after On is on ours (the watch)",
         hits > 0.6 * total, "%d of %d buttons" % (hits, total))
else:
    print(icons.set_enabled(False))
    hits, _ = on_ours()
    gate("off: no button on ours", hits == 0, str(hits))
    gate("off: the folder emptied", not [n for n in os.listdir(folder)
                                          if n.endswith(".png")])
print("verify_maya_icons: %d of %d gates failed" % (RESULTS.count(False),
                                                    len(RESULTS)))
