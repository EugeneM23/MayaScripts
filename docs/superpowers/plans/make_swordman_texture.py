"""The Swordman's colour map: his PSD as the JPG we ship.

    mayapy make_swordman_texture.py

Reads  the PSD beside his FBX (copied into sources/swordman/ as the record)
Writes SkeldarAnim/assets/Swordman/Swordman_Color.jpg

His body, sword and shield all sit on one atlas in the UV set `UVChannel_1`,
so the two weapon rows wear this image too, not a palette colour.
"""
import os
import shutil
import sys
import tempfile

import maya.standalone
maya.standalone.initialize(name="python")

import maya.cmds as cmds
import maya.api.OpenMaya as om

REPO = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
PSD_SOURCES = [
    os.path.join(REPO, "sources", "swordman", "Swards Man Texture.psd"),
    r"C:\Users\MY PC\Downloads\Telegram Desktop\FBX\FBX\Sward Man.fbm\Swards Man Texture.psd",
]
KEEP = os.path.join(REPO, "sources", "swordman", "Swards Man Texture.psd")
OUT_DIR = os.path.join(REPO, "SkeldarAnim", "assets", "Swordman")
OUT = os.path.join(OUT_DIR, "Swordman_Color.jpg")
QUALITY = 95


def find_psd():
    for path in PSD_SOURCES:
        if os.path.exists(path):
            return path
    raise RuntimeError("the PSD is nowhere:\n  " + "\n  ".join(PSD_SOURCES))


def main():
    psd = find_psd()
    if not os.path.exists(KEEP):
        os.makedirs(os.path.dirname(KEEP), exist_ok=True)
        shutil.copy2(psd, KEEP)
        print("kept the PSD as the record: %s (%.1f KB)" % (KEEP, os.path.getsize(KEEP) / 1024.0))

    work = os.path.join(tempfile.gettempdir(), "swordman_texture_work")
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)

    image = om.MImage()
    image.readFromFile(KEEP)
    width, height = image.getSize()
    print("read %s: %d x %d, depth %d" % (os.path.basename(KEEP), width, height, image.depth()))

    tmp = os.path.join(work, "Swordman_Color.jpg")
    cmds.optionVar(intValue=("jpegQuality", QUALITY))
    image.writeToFile(tmp, "jpg")
    if not os.path.exists(tmp):
        raise RuntimeError("MImage wrote nothing to %s" % tmp)

    # read it back, so what ships is what a file node will see
    back = om.MImage()
    back.readFromFile(tmp)
    bw, bh = back.getSize()
    if (bw, bh) != (width, height):
        raise RuntimeError("the JPG came back %d x %d, not %d x %d" % (bw, bh, width, height))

    os.makedirs(OUT_DIR, exist_ok=True)
    shutil.move(tmp, OUT)
    print("wrote %s: %d x %d, %.1f KB" % (OUT, bw, bh, os.path.getsize(OUT) / 1024.0))


if __name__ == "__main__":
    main()
    maya.standalone.uninitialize()
