"""The window: browse the editor's animations, search, import one.

Pure `maya.cmds` - a scroll list and a text field need no Qt.

Two habits from the rest of this repo are load-bearing here. Every callback
goes through `_run`, which puts the failure on the status line: an exception
escaping a UI callback lands in the Script Editor and the panel just looks
dead. And the search filters the cached list rather than the editor, so typing
never waits on a round trip.
"""

import json
import os
import tempfile
import traceback

import maya.cmds as cmds

from maya_uebridge import animimport
from maya_uebridge import records
from maya_uebridge import uelink
from maya_uebridge import uescripts

WINDOW = "ueAnimBridgeWindow"
_LIST = "ueAnimBridgeList"
_SEARCH = "ueAnimBridgeSearch"
_STATUS = "ueAnimBridgeStatus"
_HEADER = "ueAnimBridgeHeader"
_TIMELINE = "ueAnimBridgeTimeline"

CACHE_NAME = "maya_uebridge_cache.json"

_STATE = {"records": [], "filtered": [], "project": ""}


# ---------------------------------------------------------------- cache

def cache_payload(record_list, project=""):
    """The cache is stored in the editor's own reply shape, so one parser reads both."""
    return {"project": project,
            "assets": [{"name": rec.name,
                        "package": rec.package,
                        "skeleton": rec.skeleton,
                        "frames": rec.frames,
                        "length": rec.length,
                        "fps": rec.fps} for rec in record_list]}


def records_from_cache(payload):
    return records.parse_payload(payload)


def cache_path():
    return os.path.join(cmds.internalVar(userPrefDir=True), CACHE_NAME)


def save_cache(record_list, project):
    try:
        with open(cache_path(), "w") as handle:
            json.dump(cache_payload(record_list, project), handle)
    except (OSError, IOError):
        pass  # a cache we cannot write is not worth failing a refresh over


def load_cache():
    try:
        with open(cache_path(), "r") as handle:
            payload = json.load(handle)
    except (OSError, IOError, ValueError):
        return [], ""
    return records_from_cache(payload), payload.get("project", "")


def temp_folder():
    folder = os.path.join(tempfile.gettempdir(), "maya_uebridge")
    if not os.path.isdir(folder):
        os.makedirs(folder)
    return folder


# ---------------------------------------------------------------- ui state

def _status(text):
    if cmds.text(_STATUS, exists=True):
        cmds.text(_STATUS, edit=True, label=text)

def _header(text):
    if cmds.text(_HEADER, exists=True):
        cmds.text(_HEADER, edit=True, label=text)


def _run(action, busy=None):
    """Run a callback, routing any failure to the status line."""
    if busy:
        _status(busy)
        cmds.refresh()
    try:
        action()
    except uelink.UeBridgeError as error:
        _status(str(error).strip().splitlines()[0] if str(error).strip() else "failed")
        print("[uebridge] {0}".format(error))
    except Exception as error:
        _status("{0}: {1}".format(type(error).__name__, error))
        print(traceback.format_exc())


def _project_label(project_path):
    if not project_path:
        return "no project"
    return os.path.splitext(os.path.basename(project_path))[0]


def _repopulate():
    query = cmds.textField(_SEARCH, query=True, text=True) if cmds.textField(
        _SEARCH, exists=True) else ""
    shown = records.filter_records(_STATE["records"], query)
    _STATE["filtered"] = shown
    cmds.textScrollList(_LIST, edit=True, removeAll=True)
    for record in shown:
        cmds.textScrollList(_LIST, edit=True, append=records.format_row(record))
    return shown


def _selected_record():
    indices = cmds.textScrollList(_LIST, query=True, selectIndexedItem=True) or []
    if not indices:
        return None
    index = indices[0] - 1
    if 0 <= index < len(_STATE["filtered"]):
        return _STATE["filtered"][index]
    return None


# ---------------------------------------------------------------- actions

def refresh():
    """Ask the editor for every AnimSequence and cache the answer."""
    out = os.path.join(temp_folder(), "list.json")
    payload = uelink.run_script(uescripts.list_script(out), out)

    if payload.get("scanning"):
        _status("the asset registry is still scanning - try again in a moment")
        return

    found = records.parse_payload(payload)
    _STATE["records"] = found
    _STATE["project"] = payload.get("project", "")
    save_cache(found, _STATE["project"])

    _header("Project: {0}     connected".format(_project_label(_STATE["project"])))
    shown = _repopulate()
    _status("{0} animations ({1} shown)".format(len(found), len(shown)))


def import_selected():
    """Export the selected animation from the editor and bring it in."""
    record = _selected_record()
    if record is None:
        _status("select an animation first")
        return

    out = os.path.join(temp_folder(), "export.json")
    fbx = os.path.join(temp_folder(), "{0}.fbx".format(record.name))
    payload = uelink.run_script(uescripts.export_script(out, record.package, fbx), out)

    namespace = records.namespace_for(record.name, animimport.existing_namespaces())
    set_timeline = cmds.checkBox(_TIMELINE, query=True, value=True)

    cmds.undoInfo(openChunk=True, chunkName="UE anim import")
    try:
        info = animimport.import_clip(
            payload.get("path") or fbx,
            namespace,
            set_timeline=set_timeline,
            clip_fps=payload.get("fps") or record.fps)
    finally:
        cmds.undoInfo(closeChunk=True)

    span = ""
    if info["start"] is not None:
        span = " frames {0:g}-{1:g}".format(info["start"], info["end"])
    message = "imported {0} into {1}: {2} joints{3}".format(
        record.name, info["namespace"], info["joints"], span)
    if info["warning"]:
        message = "{0}  |  {1}".format(message, info["warning"])
    _status(message)


# ---------------------------------------------------------------- window

def show_window():
    if cmds.window(WINDOW, exists=True):
        cmds.deleteUI(WINDOW)

    cmds.window(WINDOW, title="UE Animation Bridge", widthHeight=(760, 460))
    form = cmds.formLayout(numberOfDivisions=100)

    header = cmds.text(_HEADER, label="not connected", align="left")
    refresh_button = cmds.button(
        label="Refresh", width=90,
        command=lambda *_: _run(refresh, busy="asking the editor..."))

    search_label = cmds.text(label="Search:", align="left")
    search = cmds.textField(_SEARCH, placeholderText="name or folder",
                            textChangedCommand=lambda *_: _run(_repopulate))

    scroll = cmds.textScrollList(
        _LIST, allowMultiSelection=False, font="fixedWidthFont",
        doubleClickCommand=lambda *_: _run(import_selected,
                                           busy="exporting from the editor..."))

    timeline = cmds.checkBox(_TIMELINE, label="set timeline to clip range",
                             value=True)
    import_button = cmds.button(
        label="IMPORT", height=34,
        command=lambda *_: _run(import_selected,
                                busy="exporting from the editor..."))
    status = cmds.text(_STATUS, label="", align="left")

    cmds.formLayout(
        form, edit=True,
        attachForm=[
            (header, "top", 8), (header, "left", 8),
            (refresh_button, "top", 4), (refresh_button, "right", 8),
            (search_label, "left", 8),
            (search, "right", 8),
            (scroll, "left", 8), (scroll, "right", 8),
            (timeline, "left", 8),
            (import_button, "right", 8),
            (status, "left", 8), (status, "right", 8), (status, "bottom", 8),
        ],
        attachControl=[
            (search_label, "top", 10, header),
            (search, "top", 8, header),
            (search, "left", 6, search_label),
            (scroll, "top", 8, search),
            (scroll, "bottom", 8, import_button),
            (import_button, "bottom", 6, status),
            (timeline, "bottom", 18, status),
        ])

    cached, project = load_cache()
    _STATE["records"] = cached
    _STATE["project"] = project
    _header("Project: {0}     not connected".format(_project_label(project)))
    shown = _repopulate()
    if cached:
        _status("{0} animations from the last refresh - press Refresh for the "
                "live list".format(len(shown)))
    else:
        _status("press Refresh to read the animations from the open editor")

    cmds.showWindow(WINDOW)
    return WINDOW
