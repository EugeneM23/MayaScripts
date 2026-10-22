"""The Pose Library's window offscreen, at 150 %, in its grid and its list (2026-10-22, our look,
variant B): writes `poselib_restyle.png` beside this file.

    $env:QT_QPA_PLATFORM = 'offscreen'
    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' docs/superpowers/plans/render_poselib_restyle.py

The window stands over the unit tests' fake scene (no Maya); the thumbnails are the plugin's
character portraits.
"""

import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "SkeldarAnim"))

import maya_hubqt                                           # noqa: E402
from maya_poselib import look, store, window as pw          # noqa: E402
from tests import test_poselib_window as tw                 # noqa: E402

QT = maya_hubqt.qt()
SCALE = 1.5


def main():
    app = QT.QtWidgets.QApplication.instance() or QT.QtWidgets.QApplication([])
    QT.QtGui.QFontDatabase.addApplicationFont("C:/Windows/Fonts/segoeui.ttf")
    QT.QtGui.QFontDatabase.addApplicationFont("C:/Windows/Fonts/segoeuib.ttf")
    app.setFont(QT.QtGui.QFont("Segoe UI"))
    tmp = tempfile.mkdtemp(prefix="skeldar_poselib_render_")
    try:
        root = os.path.join(tmp, "poses").replace("\\", "/")
        os.makedirs(root)
        portraits = os.path.join(REPO, "SkeldarAnim", "assets", "character_portraits")
        pictures = [os.path.join(portraits, name) for name in sorted(os.listdir(portraits))
                    if name.endswith(".png")]
        for folder in ("Hands", "Knife", "Walk cycles"):
            store.make_folder(root, "", folder)
        rows = [("Crouch", "", 0), ("Idle", "", 0), ("Knife", "Knife", 0), ("Run", "", 48),
                ("Walk", "Walk cycles", 48), ("Fist", "Hands", 0), ("Point", "Hands", 0),
                ("Block", "Knife", 22), ("Fall", "", 36)]
        paths = {}
        for index, (name, folder, frames) in enumerate(rows):
            data = tw.card_data(name)
            if frames:
                data.update(format="skeldar.anim", frames=frames, start=0, end=frames - 1)
            paths[name] = store.write(root, folder, name, data,
                                      pictures[index % len(pictures)])
        scene = tw.FakeScene(root, os.path.join(tmp, "trash"))
        scene.scale = lambda: SCALE
        sheet = QT.QtGui.QImage(int(1000 * SCALE), int(2 * 640 * SCALE) + 40,
                                QT.QtGui.QImage.Format_ARGB32)
        sheet.fill(QT.QtGui.QColor("#101113"))
        p = QT.QtGui.QPainter(sheet)
        for row, cell in enumerate((look.CELL_DEFAULT, look.CELL_MIN)):
            scene.options[pw.SIZE_VAR] = cell
            win = pw.make_window(scene)
            win.resize(int(1000 * SCALE), int(640 * SCALE))
            win.move(4000, 4000)
            win.show()
            for _ in range(5):
                app.processEvents()
            win.pick(paths["Walk"])
            if row == 1:
                win.set_folder("Walk cycles")
            for _ in range(5):
                app.processEvents()
            p.drawImage(0, row * (int(640 * SCALE) + 40), win.grab().toImage())
            if row == 0:
                win.open_folders()
                for _ in range(5):
                    app.processEvents()
                popup = win.folder_popup
                at = win.mapFromGlobal(popup.pos())
                p.drawImage(at.x(), at.y(), popup.grab().toImage())
            win.close_folders()
            win.close()
            win.deleteLater()
        p.end()
        out = os.path.join(HERE, "poselib_restyle.png")
        sheet.save(out)
        print("wrote", out)
    finally:
        shutil.rmtree(tmp, True)


if __name__ == "__main__":
    main()
