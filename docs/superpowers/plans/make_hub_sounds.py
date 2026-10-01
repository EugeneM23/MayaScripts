"""Write the hub's interface sounds into SkeldarAnim/assets/sounds/.

Every Tone of maya_hubsound.SOUNDS, synthesised by the module itself, so the
file and the synthesis cannot drift (tests/test_hubsound.py compares them).
Stdlib only:

    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' docs/superpowers/plans/make_hub_sounds.py

Spec: docs/superpowers/specs/2026-10-01-hub-hover-sound-design.md
"""

import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(REPO, "SkeldarAnim"))

import maya_hubsound  # noqa: E402

for name in sorted(maya_hubsound.SOUNDS):
    path = maya_hubsound.write(name)
    print("{0}: {1} ({2} bytes)".format(name, path, os.path.getsize(path)))
