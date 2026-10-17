"""Drop this file into a Maya viewport: a report on why the Maya theme does or
does not show (2026-10-17). It records Qt's palette, the application's sheet
and a few screen pixels, turns the theme ON through the hub (what ⋮ -> Maya
theme does), records again at once and 3 s later (something resetting the
palette on idle shows there), and writes everything to
<Documents>/maya/skeldar_theme_report.json. It changes nothing but switching
the theme on.
"""

import json
import os
import sys
import traceback


def _report():
    from PySide6 import QtCore, QtGui, QtWidgets
    import maya.OpenMayaUI as omui
    import shiboken6
    import maya.cmds as cmds

    app = QtWidgets.QApplication.instance()
    main = shiboken6.wrapInstance(int(omui.MQtUtil.mainWindow()),
                                  QtWidgets.QWidget)
    out = os.path.join(os.path.normpath(cmds.internalVar(userAppDir=True)),
                       "skeldar_theme_report.json")
    report = {"steps": []}

    def take(tag):
        row = {"tag": tag}
        try:
            row["app_window"] = app.palette().color(QtGui.QPalette.Window).name()
            row["main_window"] = main.palette().color(QtGui.QPalette.Window).name()
            sheet = app.styleSheet() or ""
            row["app_sheet_len"] = len(sheet)
            row["app_sheet_has_ours"] = "skeldarMayaTheme start" in sheet
            row["app_sheet_head"] = sheet[:300]
            row["main_sheet_len"] = len(main.styleSheet() or "")
            row["style"] = app.style().objectName()
            row["main_own_palette"] = main.testAttribute(QtCore.Qt.WA_SetPalette)
            img = main.screen().grabWindow(main.winId()).toImage()
            row["pixels"] = [img.pixelColor(x, y).name() for x, y in
                             ((300, 12), (300, 40), (15, 300))]
            row["theme_var"] = (cmds.optionVar(q="skeldarMayaTheme")
                                if cmds.optionVar(exists="skeldarMayaTheme")
                                else None)
            mod = sys.modules.get("maya_mayatheme")
            row["theme_module"] = getattr(mod, "__file__", None)
            row["theme_state"] = str(getattr(sys, "_skeldar_mayatheme", None))[:200]
        except Exception:                                    # noqa: BLE001
            row["error"] = traceback.format_exc()
        report["steps"].append(row)
        with open(out, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=1)

    take("before")
    report["modules"] = sorted(m for m in sys.modules
                               if m.split(".")[0].lower() in
                               ("animbot", "mgear", "ngskintools", "studiolibrary",
                                "tweenmachine", "qtpy", "qdarkstyle"))
    report["plugins"] = cmds.pluginInfo(query=True, listPlugins=True) or []
    try:
        import maya_hub
        report["switch"] = maya_hub.set_mayatheme(True)
    except Exception:                                        # noqa: BLE001
        report["switch_error"] = traceback.format_exc()
    take("after the switch")
    QtCore.QTimer.singleShot(3000, lambda: take("3 s later"))
    print("SkeldarAnim: the theme report goes to " + out)


def onMayaDroppedPythonFile(*_args):                         # noqa: N802
    try:
        _report()
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()


if __name__ == "__main__":
    onMayaDroppedPythonFile()
