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
_PROJECT = "ueAnimBridgeProject"
_MODE = "ueAnimBridgeMode"

CACHE_NAME = "maya_uebridge_cache.json"

_STATE = {"records": [], "filtered": [], "project": "", "choice": ""}


# ---------------------------------------------------------------- cache

def cache_payload(record_list, project="", choice=""):
    """The cache is stored in the editor's own reply shape, so one parser reads both."""
    return {"project": project,
            "choice": choice,
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


def save_cache(record_list, project, choice=""):
    try:
        with open(cache_path(), "w") as handle:
            json.dump(cache_payload(record_list, project, choice), handle)
    except (OSError, IOError):
        pass  # a cache we cannot write is not worth failing a refresh over


def load_cache():
    try:
        with open(cache_path(), "r") as handle:
            payload = json.load(handle)
    except (OSError, IOError, ValueError):
        return [], "", ""
    return (records_from_cache(payload),
            payload.get("project", ""),
            payload.get("choice", ""))


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


def project_choice():
    """The project the user picked, falling back to the remembered one."""
    if not cmds.optionMenu(_PROJECT, exists=True):
        return _STATE.get("choice") or ""
    if not (cmds.optionMenu(_PROJECT, query=True, numberOfItems=True) or 0):
        return _STATE.get("choice") or ""
    return cmds.optionMenu(_PROJECT, query=True, value=True) or ""


def fill_project_menu(labels):
    """Rebuild the picker, keeping the current choice if that editor is still up."""
    previous = project_choice()
    for item in (cmds.optionMenu(_PROJECT, query=True, itemListLong=True) or []):
        cmds.deleteUI(item)
    for label in labels:
        cmds.menuItem(parent=_PROJECT, label=label)
    if previous and previous in labels:
        cmds.optionMenu(_PROJECT, edit=True, value=previous)
    return project_choice()


def editors_line(labels, chosen):
    """What the status says about which editor we are talking to. Pure."""
    if len(labels) <= 1:
        return ""
    return "{0} editors open, reading {1}".format(len(labels), chosen)


def count_line(total, shown, query):
    """What the status says about the list. Pure, so the arithmetic is tested."""
    if not (query or "").strip():
        return "{0} animations".format(total)
    if shown == 0:
        return "nothing matches '{0}' ({1} animations)".format(query, total)
    return "{0} of {1} animations match '{2}'".format(shown, total, query)


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
    _status(count_line(len(_STATE["records"]), len(shown), query))
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

def _project_changed():
    """Picking another editor reloads the list from it."""
    _STATE["choice"] = project_choice()
    refresh()


def refresh():
    """Ask the chosen editor for every AnimSequence and cache the answer."""
    # Discovery is answered without connecting to anything, so the menu can be
    # filled before we decide who to talk to.
    nodes = uelink.discover_nodes()
    labels = uelink.node_labels(nodes)
    fill_project_menu(labels)
    chosen = uelink.node_label(uelink.pick_node(nodes, project_choice()))
    if cmds.optionMenu(_PROJECT, query=True, numberOfItems=True):
        cmds.optionMenu(_PROJECT, edit=True, value=chosen)
    _STATE["choice"] = chosen

    out = os.path.join(temp_folder(), "list.json")
    payload = uelink.run_script(uescripts.list_script(out), out, project=chosen)

    if payload.get("scanning"):
        _status("the asset registry is still scanning - try again in a moment")
        return

    found = records.parse_payload(payload)
    _STATE["records"] = found
    _STATE["project"] = payload.get("project", "")
    save_cache(found, _STATE["project"], chosen)

    _header("connected")
    # _repopulate writes the count itself, honouring whatever is in the search
    # box - overwriting it here would report the unfiltered total over a
    # filtered list.
    _repopulate()
    extra = editors_line(labels, chosen)
    if extra:
        _status("{0}  |  {1}".format(
            cmds.text(_STATUS, query=True, label=True), extra))


def import_selected():
    """Export the selected animation from the editor and bring it in."""
    record = _selected_record()
    if record is None:
        _status("select an animation first")
        return

    out = os.path.join(temp_folder(), "export.json")
    fbx = os.path.join(temp_folder(), "{0}.fbx".format(record.name))
    # Export from the same editor the list came from, or a second open project
    # would answer with an asset path it does not have.
    payload = uelink.run_script(uescripts.export_script(out, record.package, fbx),
                                out, project=project_choice())

    merge = merge_selected()
    namespace = ("" if merge else
                 records.namespace_for(record.name,
                                       animimport.existing_namespaces()))
    set_timeline = cmds.checkBox(_TIMELINE, query=True, value=True)

    cmds.undoInfo(openChunk=True, chunkName="UE anim import")
    try:
        info = animimport.import_clip(
            payload.get("path") or fbx,
            namespace,
            set_timeline=set_timeline,
            clip_fps=payload.get("fps") or record.fps,
            merge=merge)
    finally:
        cmds.undoInfo(closeChunk=True)

    _status(import_line(record.name, info))


def import_line(name, info):
    """What the status says after an import. Pure, so the wording is tested."""
    span = ""
    if info.get("start") is not None:
        span = ", frames {0:g}-{1:g}".format(info["start"], info["end"])
    if info.get("merged"):
        head = "{0} onto {1}: {2} bones animated{3}".format(
            name, info.get("target") or "the scene skeleton",
            info.get("joints", 0), span)
    else:
        head = "{0} into {1}: {2} joints{3}".format(
            name, info.get("namespace", ""), info.get("joints", 0), span)
    if info.get("warning"):
        return "{0}  |  {1}".format(head, info["warning"])
    return head


def merge_selected():
    """True when the clip should land on the skeleton already in the scene."""
    if not cmds.radioButtonGrp(_MODE, exists=True):
        return True
    return cmds.radioButtonGrp(_MODE, query=True, select=True) == 1


# ---------------------------------------------------------------- window

def show_window():
    if cmds.window(WINDOW, exists=True):
        cmds.deleteUI(WINDOW)

    cmds.window(WINDOW, title="UE Animation Bridge", widthHeight=(760, 460))
    form = cmds.formLayout(numberOfDivisions=100)

    project_label = cmds.text(label="Project:", align="left")
    project_menu = cmds.optionMenu(
        _PROJECT, width=250,
        changeCommand=lambda *_: _run(_project_changed,
                                      busy="switching editor..."))
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

    mode = cmds.radioButtonGrp(
        _MODE, numberOfRadioButtons=2, label="Import:",
        labelArray2=["onto the skeleton in the scene", "as a new skeleton"],
        columnWidth3=(52, 216, 160), select=1)
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
            (project_label, "top", 10), (project_label, "left", 8),
            (project_menu, "top", 6), (header, "top", 10),
            (refresh_button, "top", 4), (refresh_button, "right", 8),
            (search_label, "left", 8),
            (search, "right", 8),
            (scroll, "left", 8), (scroll, "right", 8),
            (mode, "left", 4),
            (timeline, "left", 8),
            (import_button, "right", 8),
            (status, "left", 8), (status, "right", 8), (status, "bottom", 8),
        ],
        attachControl=[
            (project_menu, "left", 6, project_label),
            (header, "left", 12, project_menu),
            (search_label, "top", 10, project_menu),
            (search, "top", 8, project_menu),
            (search, "left", 6, search_label),
            (scroll, "top", 8, search),
            (scroll, "bottom", 8, mode),
            (mode, "bottom", 6, timeline),
            (import_button, "bottom", 6, status),
            (timeline, "bottom", 18, status),
        ])

    cached, project, choice = load_cache()
    _STATE["records"] = cached
    _STATE["project"] = project
    _STATE["choice"] = choice
    # Show the remembered project straight away; Refresh replaces the menu with
    # whatever is actually running. Discovery on open would make the window
    # take a second to appear even with no editor about.
    if choice or project:
        fill_project_menu([choice or _project_label(project)])
    _header("not connected")
    shown = _repopulate()
    if cached:
        _status("{0} animations from the last refresh - press Refresh for the "
                "live list".format(len(shown)))
    else:
        _status("press Refresh to read the animations from the open editor")

    cmds.showWindow(WINDOW)
    return WINDOW
