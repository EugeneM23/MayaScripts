"""The bridge's rows: browse the editor's animations, search, import onto a character.

Pure `maya.cmds` - a scroll list and a text field need no Qt.

Since 2026-10-01 the rows are part of the Characters card, under the
portraits («UE bridge и character эти две вкладки имеют общий функционал ...
их нужно объеденить в одно окно»): `build_rows` builds them into the card's
column, they write the card's one status line, and the press's mode is the
card's [Rig | Skeleton] times the Import row's [Onto selected | New]
(`mode_for`) - the bridge's own Rig / New rig / Skeleton said the kind a
second time. Skeleton x Onto selected is new: the clip onto a skeleton
already in the scene (`skeletonimport.import_onto_existing`).
Spec: docs/superpowers/specs/2026-10-01-characters-and-bridge-one-card-design.md

One window since 2026-09-07 (the animator: «сделаем одно окно для всех
действий, а не так как сейчас импорт и экспорт отдельно» and «уберем весь
функционал по работе с перфорсом»): the list, the search, the import mode,
and three buttons -- Export FBX..., Export to uasset, IMPORT. The Export tab,
the Checkout button and the version-control row are gone from the window;
`vcs.py` and `checkouts.py` stay as modules and this file imports neither.

Since 2026-10-01 a row also DRAGS into a viewport (`listdrag`, Qt, attached
lazily): onto a rig it is Import with the Rig mode onto THAT rig, onto empty
floor Import with New rig (`import_dropped`). And the list takes SEVERAL
rows the same day: the Rig mode and a drop on a rig take the first; New
rig, Skeleton and a floor drop lay them all out in a square on the world's
axes (`lineimport`).

IMPORT in the default mode is the whole pipeline (`rigimport`): the
AdvancedSkeleton rig added if the scene has none, the clip imported as its
own skeleton, the retarget connected and baked -- weapon and camera bones
carried, the camera set up -- and the source skeleton deleted. The other
mode imports the clip as a new namespaced skeleton and stops there.

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

import maya_hubstyle as hubstyle
from maya_uebridge import animimport
from maya_uebridge import records
from maya_uebridge import uelink
from maya_uebridge import uescripts

#  2026-10-01 («UE bridge и character ... их нужно объеденить в одно окно»):
#  the bridge's rows live in the Characters card, under the portraits, and
#  write the card's one status line - `maya_scenesetup.window._CHARACTER_STATUS`,
#  spelled here so this package imports nothing of Scene Setup's at load (a
#  test pins the two equal).
HUB_SECTION = "characters"      # the card of the SkeldarAnim hub we live in
LIST_HEIGHT = 300               # the animation list, inside the hub's column
_LIST = "ueAnimBridgeList"
_SEARCH = "ueAnimBridgeSearch"
_STATUS = "mayaSceneSetupCharacterStatus"
_HEADER = "ueAnimBridgeHeader"
#  2026-10-08 («сделаем его компактным»): the editor line is hidden in the
#  skin - its text is the project dropdown's tooltip, and the state shows as a
#  dot before the dropdown (● connected, ○ not); under the list a grip sets
#  how many rows it shows.
_DOT = "ueAnimBridgeDot"
_LIST_GRIP = "ueAnimBridgeListGrip"
DOT_ON, DOT_OFF = "●", "○"
_HEADING = "ueAnimBridgeHeading"     # «Connect», the block's title (2026-10-02)
_TIMELINE = "ueAnimBridgeTimeline"
_PROJECT = "ueAnimBridgeProject"
_MODE = "ueAnimBridgeMode"
#  2026-10-02 («раздел с подключением к unreal engine нужно визуально как-то
#  отделить ... подключаться не только к анриал енжину а и к Unity, и просто к
#  папке с FBX файлами»): the rows are one block set into the card, and a
#  switch above them says where the animations come from.
_INSET = "ueAnimBridgeInset"
_SOURCE = "ueAnimBridgeSource"
_UASSET = "ueAnimBridgeExportUasset"
SOURCE_VAR = "ueAnimBridgeSourceKind"          # the switch's memory
LOCATION_VAR = "ueAnimBridgeLocation_{0}"       # the folder / project picked
RECENT_VAR = "ueAnimBridgeRecent_{0}"           # JSON list: folders / projects
BROWSE = "Browse..."
#  The block's look in the classic hub (the skin styles it by its role).
INSET_CLASSIC_BG = (0.215, 0.22, 0.235)

# Windows earlier builds left open: the checkouts popup of 2026-08-21's
# afternoon, and the bridge's own standalone window (before the hub,
# 2026-09-17). `maya_hub.show` deletes both, or a panel from an older
# build stays up wired to dead code.
LEGACY_WINDOWS = ("ueBridgeCheckouts", "ueAnimBridgeWindow")

CACHE_NAME = "maya_uebridge_cache.json"

_STATE = {"records": [], "filtered": [], "project": "", "choice": "",
          "content_dir": "", "source": None, "menu": [], "location": "",
          "unreal_labels": []}


# ---------------------------------------------------------------- cache

def cache_payload(record_list, project="", choice="", content_dir=""):
    """The cache is stored in the editor's own reply shape, so one parser reads both."""
    return {"project": project,
            "choice": choice,
            "content_dir": content_dir,
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


def save_cache(record_list, project, choice="", content_dir=""):
    try:
        with open(cache_path(), "w") as handle:
            json.dump(cache_payload(record_list, project, choice, content_dir),
                      handle)
    except (OSError, IOError):
        pass  # a cache we cannot write is not worth failing a refresh over


def load_cache():
    try:
        with open(cache_path(), "r") as handle:
            payload = json.load(handle)
    except (OSError, IOError, ValueError):
        return [], "", "", ""
    return (records_from_cache(payload),
            payload.get("project", ""),
            payload.get("choice", ""),
            payload.get("content_dir", ""))


def temp_folder():
    folder = os.path.join(tempfile.gettempdir(), "maya_uebridge")
    if not os.path.isdir(folder):
        os.makedirs(folder)
    return folder


# ---------------------------------------------------------------- ui state

def search_hint(count):
    """The search field's placeholder: how many animations the source holds
    (2026-10-08: the editor line is a tooltip in the compact skin, so the
    count the line used to carry moved here). Pure."""
    return ("search {0} animations".format(count) if count
            else "search name or folder")


def _status(text):
    """The card's one line, and the hub's message line too (the skin hides
    the card's own and shows what `hubstyle.tell` carries)."""
    if cmds.text(_STATUS, exists=True):
        cmds.text(_STATUS, edit=True, label=text)
    hubstyle.tell(_STATUS, text)


def _header(text):
    """The editor line: its own text (shown in the classic hub, hidden in the
    skin), the project dropdown's tooltip, and the dot before it (● connected,
    ○ not). The dropdown and the dot are written without asking `exists`
    first - a card built without them (a headless session) just skips."""
    if cmds.text(_HEADER, exists=True):
        cmds.text(_HEADER, edit=True, label=text)
    for edit in (lambda: cmds.optionMenu(_PROJECT, edit=True, annotation=text),
                 lambda: cmds.text(_DOT, edit=True,
                                   label=DOT_ON if text == "connected"
                                   else DOT_OFF, annotation=text)):
        try:
            edit()
        except (RuntimeError, TypeError, ValueError):
            pass


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


def _repopulate(quiet=False):
    """Rebuild the list: rows and the selection.

    `quiet` skips the status write, for callers that are about to say
    something more specific.
    """
    query = cmds.textField(_SEARCH, query=True, text=True) if cmds.textField(
        _SEARCH, exists=True) else ""
    shown = records.filter_records(_STATE["records"], query)

    # The selection survives the rebuild by identity, not by position - a
    # narrowed filter must not silently select a different animation.
    previous = _STATE.get("filtered") or []
    picked = cmds.textScrollList(_LIST, query=True,
                                 selectIndexedItem=True) or []
    keep = set(previous[i - 1].package for i in picked
               if 0 < i <= len(previous))

    _STATE["filtered"] = shown
    #  the placeholder says how many animations the source holds (the skin
    #  has no editor line to carry the count)
    try:
        cmds.textField(_SEARCH, edit=True,
                       placeholderText=search_hint(len(_STATE["records"])))
    except (RuntimeError, TypeError, ValueError):
        pass
    cmds.textScrollList(_LIST, edit=True, removeAll=True)
    for record in shown:
        cmds.textScrollList(_LIST, edit=True, append=records.format_row(record))
    for index, record in enumerate(shown, 1):
        if record.package in keep:
            cmds.textScrollList(_LIST, edit=True, selectIndexedItem=index)
    if not quiet:
        _status(count_line(len(_STATE["records"]), len(shown), query))
    return shown


def _selected_records():
    """Every picked row's record, in list order (2026-10-01: the list takes a
    multiple selection)."""
    indices = cmds.textScrollList(_LIST, query=True, selectIndexedItem=True) or []
    shown = _STATE["filtered"]
    return [shown[i - 1] for i in sorted(indices) if 0 < i <= len(shown)]


def _selected_record():
    """The first picked record, or None."""
    chosen = _selected_records()
    return chosen[0] if chosen else None


def _with_note(text, note):
    """`note` ahead of `text`: the status shows two lines of a long line, and
    "only the first went" is what must not be clipped (measured live)."""
    return "{0}  |  {1}".format(note, text) if note else text


# ---------------------------------------------------------------- actions

def _project_changed():
    """Picking another editor reloads the list from it; for a folder or a
    Unity project, picking one shows its last scan (Browse... asks)."""
    if current_source() != "unreal":
        _location_changed()
        return
    _STATE["choice"] = project_choice()
    refresh()


def refresh():
    """Re-read the list from the source: the chosen editor's every
    AnimSequence for Unreal, a scan of the folder or the Unity project
    otherwise. Either way the answer is cached."""
    if current_source() != "unreal":
        _refresh_files()
        return
    _refresh_unreal()


def _refresh_unreal():
    """Ask the chosen editor for every AnimSequence and cache the answer."""
    # Discovery is answered without connecting to anything, so the menu can be
    # filled before we decide who to talk to.
    nodes = uelink.discover_nodes()
    labels = uelink.node_labels(nodes)
    fill_project_menu(labels)
    _STATE["unreal_labels"] = list(labels)
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
    _STATE["content_dir"] = payload.get("content_dir", "")
    save_cache(found, _STATE["project"], chosen, _STATE["content_dir"])

    _header(editor_line(True))
    # _repopulate writes the count itself, honouring whatever is in the search
    # box - overwriting it here would report the unfiltered total over a
    # filtered list.
    _repopulate()
    extra = editors_line(labels, chosen)
    if extra:
        _status("{0}  |  {1}".format(
            cmds.text(_STATUS, query=True, label=True), extra))


# ---------------------------------------------------------------- sources

def current_source():
    """"unreal", "unity" or "folder": the switch over the block."""
    source = _STATE.get("source")
    if source is None:
        # not built yet (a hotkey row, another module): the switch's memory,
        # or a refresh would ignore the remembered Folder / Unity (fix review)
        try:
            source = _var(SOURCE_VAR, "unreal")
        except Exception:                                    # noqa: BLE001
            source = "unreal"
    return source if source in ("unreal", "unity", "folder") else "unreal"


def _var(name, default=""):
    if cmds.optionVar(exists=name):
        return cmds.optionVar(query=name)
    return default


def _recent(source):
    try:
        return [p for p in json.loads(_var(RECENT_VAR.format(source), "[]") or "[]")
                if isinstance(p, str)]
    except ValueError:
        return []


def _remember(source, location):
    from maya_uebridge import sources
    cmds.optionVar(stringValue=(LOCATION_VAR.format(source), location or ""))
    if location:
        cmds.optionVar(stringValue=(RECENT_VAR.format(source), json.dumps(
            sources.recent(_recent(source), location))))


def menu_items(source, recent, hub=(), open_projects=()):
    """[(label, value)] of the dropdown for a file source: the Unity Hub's
    projects (an open one says so) and the ones browsed to, or the folders
    browsed to; then Browse... (value None). Pure."""
    items, seen = [], set()
    if source == "unity":
        for title, path, version, _modified in hub:
            key = os.path.normcase(os.path.normpath(path))
            seen.add(key)
            label = "{0}  ({1}{2})".format(
                title, version, ", open" if key in open_projects else "")
            items.append((label, path))
    for path in recent:
        key = os.path.normcase(os.path.normpath(path))
        if key in seen:
            continue
        seen.add(key)
        name = os.path.basename(os.path.normpath(path)) or path
        #  the path's TAIL only: a dropdown is as wide as its longest item,
        #  and a whole temp path widened the block to 682 px (measured in
        #  the card, 2026-10-02 - the animator's dock is 360)
        items.append(("{0}  -  {1}".format(name, records._tail(
            os.path.dirname(os.path.normpath(path)).replace("\\", "/"), 24))
                      if source == "folder" else name, path))
    items.append((BROWSE, None))
    return items


def _fill_menu(items, chosen=None):
    """The dropdown holds `items`; `chosen` (a value) picked when it is one."""
    if not cmds.optionMenu(_PROJECT, exists=True):
        _STATE["menu"] = [v for _l, v in items]
        return
    for item in (cmds.optionMenu(_PROJECT, query=True, itemListLong=True) or []):
        cmds.deleteUI(item)
    for label, _value in items:
        cmds.menuItem(parent=_PROJECT, label=label)
    _STATE["menu"] = [v for _l, v in items]
    #  by the folder, not the spelling: the Hub writes C:\\a, a browse C:/a
    keys = [os.path.normcase(os.path.normpath(v)) if v else None
            for v in _STATE["menu"]]
    if chosen is not None:
        key = os.path.normcase(os.path.normpath(chosen))
        if key in keys:
            cmds.optionMenu(_PROJECT, edit=True, select=keys.index(key) + 1)


def _file_menu(source, chosen):
    from maya_uebridge import unityfiles
    hub, opened = (), set()
    if source == "unity":
        hub = unityfiles.hub_projects()
        for _title, path, _v, _m in hub:
            if unityfiles.is_open(path):
                opened.add(os.path.normcase(os.path.normpath(path)))
    recent = _recent(source)
    if chosen and chosen not in recent:
        recent = [chosen] + recent
    _fill_menu(menu_items(source, recent, hub, opened), chosen)


def _menu_value():
    if not cmds.optionMenu(_PROJECT, exists=True):
        return _STATE.get("location") or None
    index = cmds.optionMenu(_PROJECT, query=True, select=True) or 0
    values = _STATE.get("menu") or []
    return values[index - 1] if 0 < index <= len(values) else None


def _browse(source):
    caption = ("Pick a Unity project folder" if source == "unity"
               else "Pick a folder of animations")
    picked = cmds.fileDialog2(fileMode=3, dialogStyle=2, caption=caption)
    return picked[0].replace("\\", "/") if picked else None


def file_cache_payload(record_list, source, location):
    """The cache of a file source: the records whole. Pure."""
    return {"source": source, "location": location,
            "assets": [dict(rec._asdict()) for rec in record_list]}


def _file_cache_path(source, location):
    from maya_uebridge import sources
    return os.path.join(temp_folder(), sources.cache_name(source, location))


def _load_file_cache(source, location):
    try:
        with open(_file_cache_path(source, location), "r") as handle:
            return records.parse_payload(json.load(handle))
    except (OSError, IOError, ValueError):
        return None


def _save_file_cache(record_list, source, location):
    try:
        with open(_file_cache_path(source, location), "w") as handle:
            json.dump(file_cache_payload(record_list, source, location), handle)
    except (OSError, IOError):
        pass


def _show_location(source, location):
    """The list from `location`'s last scan, without scanning."""
    from maya_uebridge import sources
    _STATE["location"] = location or ""
    cached = _load_file_cache(source, location) if location else None
    _STATE["records"] = cached or []
    _repopulate(quiet=True)
    _header(sources.header_line(source, location, len(cached) if cached is not None
                                else None, cached is not None))


def _source_changed(source):
    """The switch moved: the dropdown, the list and the exports follow."""
    _STATE["source"] = source
    cmds.optionVar(stringValue=(SOURCE_VAR, source))
    if cmds.button(_UASSET, exists=True):
        cmds.button(_UASSET, edit=True, enable=source == "unreal")
    if source == "unreal":
        cached, project, choice, content_dir = load_cache()
        _STATE.update(records=cached, project=project, choice=choice,
                      content_dir=content_dir)
        # the editors the last Refresh found, not the cache's one label: a
        # switch to Folder and back must not drop them (the fix review)
        labels = list(_STATE.get("unreal_labels") or [])
        label = choice or _project_label(project)
        if label and (choice or project) and label not in labels:
            labels.insert(0, label)
        _fill_menu([(l, None) for l in labels])
        if label and label in labels and cmds.optionMenu(_PROJECT, exists=True):
            cmds.optionMenu(_PROJECT, edit=True, value=label)
        _repopulate(quiet=True)
        _header(editor_line(False, len(cached)))
        return
    location = _var(LOCATION_VAR.format(source), "") or ""
    _file_menu(source, location or None)
    _show_location(source, location)


def _location_changed():
    """A pick in the dropdown of a file source: its last scan, or - for
    Browse... - a folder asked for and remembered."""
    source = current_source()
    value = _menu_value()
    if value is None:
        value = _browse(source)
        if not value:
            _file_menu(source, _STATE.get("location") or None)
            _status("nothing picked")
            return
    _remember(source, value)
    _file_menu(source, value)
    _show_location(source, value)
    if _load_file_cache(source, value) is None:
        _status("press Refresh to scan {0}".format(value))


def _refresh_files():
    """Scan the picked folder or Unity project, under a cancellable
    progress window, and cache what it holds."""
    from maya_uebridge import formats, sources, unityfiles
    source = current_source()
    location = _STATE.get("location") or _menu_value()
    if not location:
        location = _browse(source)
        if not location:
            _status("nothing picked")
            return
        _remember(source, location)
        _file_menu(source, location)
    if not os.path.isdir(location):
        _status("{0} is not a folder".format(location))
        return
    if source == "unity" and not unityfiles.is_project(location):
        _status("{0} is not a Unity project (no Assets and ProjectSettings in "
                "it)".format(location))
        return
    progress = _ScanProgress()
    try:
        found = sources.scan(location, source, formats.fbx_takes,
                             progress=progress.step)
    finally:
        progress.close()
    _STATE["location"] = location
    _STATE["records"] = found
    if not progress.cancelled:
        _save_file_cache(found, source, location)
    _header(sources.header_line(source, location, len(found), False))
    _repopulate()
    if progress.cancelled:
        _status("scan cancelled - {0} animations so far, not cached".format(
            len(found)))


class _ScanProgress(object):
    """Maya's progress window over a scan, cancellable; nothing where it
    cannot stand (a batch session)."""

    def __init__(self):
        self.on = False
        self.cancelled = False
        try:
            cmds.progressWindow(title="Connect", progress=0, maxValue=100,
                                status="scanning...", isInterruptable=True)
            self.on = True
        except Exception:                                    # noqa: BLE001
            pass

    def step(self, done, total, path):
        if not self.on or done % 10:
            return True
        try:
            if cmds.progressWindow(query=True, isCancelled=True):
                self.cancelled = True
                return False
            cmds.progressWindow(edit=True, progress=int(100 * done / max(1, total)),
                                status="{0} / {1}  {2}".format(
                                    done, total, os.path.basename(path)[:40]))
        except Exception:                                    # noqa: BLE001
            pass
        return True

    def close(self):
        if self.on:
            try:
                cmds.progressWindow(endProgress=True)
            except Exception:                                # noqa: BLE001
                pass


#  The press's internal modes: the Characters card's kind times the target.
MODES = ("rig", "new_rig", "skeleton", "onto_skeleton")
KINDS = ("rig", "skeleton")                 # the Characters card's switch
TARGETS = ("onto", "new")                   # the Import row's two segments

#  (target, the segment's label, its tooltip) -- since 2026-10-01 the card's
#  [Rig | Skeleton] says WHAT a press makes, these two say WHERE it goes
#  («Слить»: the bridge's old Rig / New rig / Skeleton said the kind twice).
TARGET_SEGMENTS = (
    ("onto", "Onto selected",
     "Onto the selected character: with Rig picked in Animation Setup the "
     "SELECTED AdvancedSkeleton rig (any control, bone or mesh), else the "
     "only one - a rig of the picked portrait is added when the scene has "
     "none; with Skeleton picked the selected skeleton (a bone, its mesh, "
     "its weapon), else the only one - the portrait's skeleton is added when "
     "none stands. A character already there keeps its place and facing; "
     "the clip is imported, put on it and baked (a rig: weapon and camera "
     "bones carried, the camera set up), and the clip's skeleton is "
     "deleted. Several picked: the first goes."),
    ("new", "New",
     "A NEW character of the picked portrait - its rig or its skeleton, as "
     "Animation Setup says - takes the clip; several picked stand in a square "
     "about the scene's zero, one per animation."),
)

#  The segment's label where the full one is too wide for the one-row Import
#  line (2026-10-08, variant B: «Onto selected» is «Onto sel.» in both hubs;
#  the tooltip above says the rest). Keyed by TARGETS' values.
SHORT_TARGET = {"onto": "Onto sel."}


def mode_for(kind, target):
    """The press's mode for the Characters card's `kind` and the Import
    row's `target`. Pure; anything unknown means the default, the whole
    pipeline onto the rig.

        rig      x onto -> "rig"            the selected rig (or one added)
        rig      x new  -> "new_rig"        a new rig of the portrait
        skeleton x new  -> "skeleton"       a new skeleton of the portrait
        skeleton x onto -> "onto_skeleton"  the selected skeleton (or one added)
    """
    if kind == "skeleton":
        return "skeleton" if target == "new" else "onto_skeleton"
    return "new_rig" if target == "new" else "rig"


def target_button(target):
    """The Import row's segment of `target` ("onto" / "new")."""
    return "{0}_{1}".format(_MODE, target)


def import_target():
    """"onto" or "new", from the Import row's segments; "onto" when they are
    not built (a headless session) or nothing is lit."""
    if not cmds.iconTextRadioCollection(_MODE, exists=True):
        return TARGETS[0]
    chosen = (cmds.iconTextRadioCollection(_MODE, query=True, select=True)
              or "").split("|")[-1]
    for target in TARGETS:
        if chosen == target_button(target):
            return target
    return TARGETS[0]


def import_kind():
    """"rig" or "skeleton": what the Characters card's [Rig | Skeleton] says
    (its memory - the card need not be open), "rig" without Scene Setup."""
    try:
        from maya_scenesetup import window as scene_window
        kind = scene_window.current_choice()[1]
    except Exception:                                        # noqa: BLE001
        return KINDS[0]
    return kind if kind in KINDS else KINDS[0]


def auto_kind():
    """The kind the Auto card brings when it is the card picked in Animation Setup (2026-10-02),
    else None - every road asks this first; None without Scene Setup."""
    try:
        from maya_scenesetup import window as scene_window
        kind = scene_window.auto_kind()
    except Exception:                                        # noqa: BLE001
        return None
    return kind if kind in KINDS else None


def import_mode():
    """The press's mode: `mode_for(import_kind(), import_target())`."""
    return mode_for(import_kind(), import_target())


def retarget_selected():
    """True when IMPORT retargets onto a rig (the selected one or a new
    one); False when it puts the clip on a skeleton."""
    return import_mode() in ("rig", "new_rig")


def _export_from_editor(record, mesh=False):
    """The clip out of its source: (clip reference, fps) for the import
    funnel (`rigimport.import_source`). Every road calls this one function
    - the button, the double click, the drag, the square of several - so a
    file source needs no road of its own (2026-10-02): its record already
    names its file and clip (`sources.record_ref`). An Unreal record is
    exported by the editor into the temp folder, as since 2026-08-16 - with
    its mesh when `mesh` asks (the Auto card: a clip that is no character of
    ours comes in its own skeleton). A file brings what it holds either way."""
    if getattr(record, "source", "unreal") != "unreal":
        from maya_uebridge import sources
        ref = sources.record_ref(record)
        refusal = file_refusal(record) or _clip_check(ref)
        if refusal:
            raise uelink.UeBridgeError(refusal)
        return ref, record.fps
    return _export_unreal(record, mesh)


def _export_with_mesh(record):
    """`_export_from_editor` asking Unreal for the clip's mesh too (the Auto card's export)."""
    return _export_from_editor(record, mesh=True)


def _clip_check(ref):
    """The file read again for what its import would refuse - a take no
    longer in it, a Unity clip with no model and no positions, a glTF with
    no skeleton - BEFORE the press adds a rig (the fix review, 2026-10-02:
    these used to raise inside the import, after a 9.5 s Manny was added)."""
    from maya_uebridge import formats  # lazy: Maya's own readers
    return formats.check(ref)


def file_refusal(record):
    """Why a file's clip cannot be imported, "" when it can. Pure: a row
    that is listed only to say so (a Humanoid muscle clip, an unreadable
    file) refuses BEFORE anything is imported or added."""
    note = getattr(record, "skeleton", "") or ""
    if note == "humanoid":
        return "{0}: a Humanoid muscle clip - export it as FBX from Unity".format(
            record.name)
    if note == "compressed":
        return "{0}: a compressed Unity clip - untick Anim. Compression, or " \
               "export FBX".format(record.name)
    if note.startswith("unreadable") or note == "no curves":
        return "{0}: {1}".format(record.name, note)
    if record.path and not os.path.isfile(record.path):
        return "{0}: the file is gone ({1}) - Refresh".format(record.name, record.path)
    return ""


def _export_unreal(record, mesh=False):
    """The clip out of the editor into the temp folder: (fbx path, fps) - bones
    only, or with the clip's preview mesh skinned beside them (`mesh`)."""
    out = os.path.join(temp_folder(), "export.json")
    fbx = os.path.join(temp_folder(), "{0}.fbx".format(record.name))
    # Export from the same editor the list came from, or a second open project
    # would answer with an asset path it does not have.
    payload = uelink.run_script(uescripts.export_script(out, record.package, fbx,
                                                        preview_mesh=mesh),
                                out, project=project_choice())
    return payload.get("path") or fbx, payload.get("fps") or record.fps


def import_selected():
    """Export the selected animation from the editor and bring it in.

    Default: onto the rig, through `rigimport` -- the selected rig, else the
    only one, added if the scene has none; import the clip as its own
    skeleton, retarget, bake, delete the source. "onto a NEW rig" adds
    another rig first. Otherwise: the clip as a new namespaced skeleton, and
    nothing more.

    Several picked (2026-10-01): the Rig mode takes the first («в этом
    случае мы работаем с конкретным ригом») and says so; New rig and
    Skeleton lay every one out in a square on world X and Z, symmetric about
    the scene's zero (`lineimport`).

    Since the merge into the Characters card the mode is the card's kind
    times the Import row's target (`mode_for`); Skeleton x Onto selected
    puts the clip on the selected skeleton (`skeletonimport`), keeping its
    place - else the only one, else a new one where the clip is.
    """
    chosen = _selected_records()
    if not chosen:
        _status("select an animation first")
        return

    auto = auto_kind()
    if auto:
        # 2026-10-02, the Auto card: ours if the clip's skeleton is ours, else its own
        _status(_auto_press(chosen, auto))
        return

    mode = import_mode()
    if len(chosen) > 1 and mode in ("new_rig", "skeleton"):
        from maya_uebridge import lineimport   # lazy: keeps the import graph flat
        _status(lineimport.run(chosen, _export_from_editor, mode,
                               set_timeline=_timeline()))
        return
    record = chosen[0]
    note = ""
    if mode == "onto_skeleton":
        from maya_uebridge import skeletonimport
        _status(_onto_existing(record, None,
                               skeletonimport.first_only([r.name for r in chosen])))
        return
    if len(chosen) > 1:
        from maya_uebridge import lineimport
        note = lineimport.first_only([r.name for r in chosen])

    if mode == "skeleton":
        # 2026-10-01: the Characters card's skeleton, with its geometry
        _status(_onto_skeleton(record))
        return

    # Which rig is decided BEFORE the round trip to the editor: two rigs and
    # nothing selected is a refusal, and it should cost nothing.
    import maya_rigs
    if mode == "rig" and maya_rigs.rigs():
        rig, refusal = maya_rigs.current_rig()
        if rig is None:
            _status(refusal)
            return

    exported, fps = _export_from_editor(record)
    from maya_uebridge import rigimport   # lazy: keeps the import graph flat
    _status(_with_note(rigimport.import_and_retarget(
        exported, record.name, clip_fps=fps, set_timeline=_timeline(),
        target=mode), note))


def _auto_press(chosen, kind):
    """Import with the Auto card picked (2026-10-02, «если он найдет скелет который совпадает с
    нашим то перенесем анимацию на наш риг или скелет, если ... совпадений нету то импортируем в
    сцену родной риг или скелет»). Returns the status line.

    Onto selected with a character of the kind selected: it takes the clip exactly as the Rig /
    Skeleton press always did (the explicit target wins - asked). Otherwise, Onto selected with
    nothing named or New: each clip is matched - our rig / skeleton of its row added and the clip
    put on it, else the clip kept in its own skeleton (`autoimport`); several in a square about
    the scene's zero (`lineimport`). Unreal is asked for the clip's mesh."""
    from maya_uebridge import autoimport   # lazy: keeps the import graph flat
    from maya_uebridge import lineimport
    names = [r.name for r in chosen]
    if import_target() == "onto":
        if kind == "rig":
            rig, refusal = autoimport.explicit_rig()
            if refusal:
                return refusal
            if rig is not None:
                exported, fps = _export_from_editor(chosen[0])
                from maya_uebridge import rigimport
                return _with_note(rigimport.import_and_retarget(
                    exported, chosen[0].name, clip_fps=fps, set_timeline=_timeline(),
                    target="rig", rig=rig), lineimport.first_only(names))
        else:
            root, refusal = autoimport.explicit_skeleton()
            if refusal:
                return refusal
            if root is not None:
                from maya_uebridge import skeletonimport
                return _onto_existing(chosen[0], root, skeletonimport.first_only(names))
    if len(chosen) > 1:
        return lineimport.run(chosen, _export_with_mesh,
                              "new_rig" if kind == "rig" else "skeleton",
                              set_timeline=_timeline(), auto=True)
    exported, fps = _export_with_mesh(chosen[0])
    return autoimport.import_auto(exported, chosen[0].name, kind, clip_fps=fps,
                                  set_timeline=_timeline())


def _timeline():
    """The «set timeline to clip range» checkbox; on when it is not built."""
    if not cmds.checkBox(_TIMELINE, exists=True):
        return True
    return bool(cmds.checkBox(_TIMELINE, query=True, value=True))


def import_dropped(record, aim):
    """An animation dragged out of the list and released over a viewport
    (2026-10-01, `listdrag`; «если я попадаю в какой-то риг то анимация
    должна перекинутся на него какбуд-то мы нажали import с опцией rig если
    мы не нашли ничего то тогда нам нужно сделать new rig»).

    `aim` is `droptarget.clip_target`'s answer at the release: "rig" (the
    rig under the cursor, by namespace) takes the clip as Import with the Rig
    mode would, whatever is selected; "new_rig" adds the rig active in the
    Characters card (Manny when that is no rig), standing on the floor point
    the drop aimed at after every bake («риг с анимацией оставался в том
    месте куда мы указали после всех перезапеканий»), or where the clip is
    when the cursor saw no floor. Of the import-mode segments only Skeleton
    changes a drop (below); the timeline checkbox applies. The rig is found again after
    nothing but the drop: it can have been deleted while the editor
    exported. Returns the status line.

    `record` may be a list (2026-10-01, a drag of several picked rows): onto
    a rig the first goes and the rest are named; onto the floor every one
    gets a new rig, in a square on the world's axes centred on the point
    (`lineimport`) - on the origin when no floor was seen - whatever the
    camera.

    And the Skeleton mode reaches the drag the same day («если у нас выбран
    скелет то будем располагать в сцене скелеты»): `aim` kind "skeleton"
    (`droptarget.skeleton_target`, a rig under the cursor ignored) - one
    clip as its own skeleton, its root at its first frame on the floor
    point, several in the square about it.
    """
    aim = aim or {}
    kind = aim.get("kind")
    chosen = ([record] if hasattr(record, "name")
              else [r for r in (record or []) if r is not None])
    if not chosen or kind not in ("rig", "new_rig", "skeleton", "onto_skeleton"):
        text = aim.get("text") or "no target"
        _status(text)
        return text
    if aim.get("auto") and kind in ("new_rig", "skeleton"):
        # 2026-10-02, the Auto card over the floor: each clip ours if its skeleton is ours, else
        # its own, standing on the point (several in the square about it)
        from maya_uebridge import autoimport   # lazy: keeps the import graph flat
        if len(chosen) > 1:
            from maya_uebridge import lineimport
            text = lineimport.run(chosen, _export_with_mesh, kind,
                                  centre=aim.get("point") or (0.0, 0.0, 0.0),
                                  set_timeline=_timeline(), auto=True)
        else:
            exported, fps = _export_with_mesh(chosen[0])
            text = autoimport.import_auto(
                exported, chosen[0].name, "rig" if kind == "new_rig" else "skeleton",
                clip_fps=fps, set_timeline=_timeline(), at=aim.get("point"))
        _status(text)
        return text
    if kind == "onto_skeleton":
        # A skeleton under the cursor with Skeleton picked in Characters (the
        # merge, 2026-10-01): it takes the first, keeping its place. Found
        # again by UUID - it can have been deleted while the drag went on.
        from maya_uebridge import skeletonimport
        root = (cmds.ls(aim.get("uuid") or "", long=True) or [None])[0]
        if root is None:
            text = "the skeleton {0} is gone - nothing imported".format(
                aim.get("label") or "")
        else:
            text = _onto_existing(chosen[0], root, skeletonimport.first_only(
                [r.name for r in chosen]))
        _status(text)
        return text
    if kind in ("new_rig", "skeleton") and len(chosen) > 1:
        from maya_uebridge import lineimport   # lazy: keeps the import graph flat
        text = lineimport.run(chosen, _export_from_editor, kind,
                              centre=aim.get("point") or (0.0, 0.0, 0.0),
                              set_timeline=_timeline())
        _status(text)
        return text
    if kind == "skeleton":
        text = _onto_skeleton(chosen[0], aim.get("point"))
        _status(text)
        return text
    record = chosen[0]
    note = ""
    if len(chosen) > 1:
        from maya_uebridge import lineimport
        note = lineimport.first_only([r.name for r in chosen])
    rig = None
    if kind == "rig":
        import maya_rigs
        rig = maya_rigs.find(aim.get("rig") or "")
        if rig is None:
            text = "the rig {0} is gone - nothing imported".format(
                aim.get("label") or aim.get("rig") or "")
            _status(text)
            return text
    exported, fps = _export_from_editor(record)
    from maya_uebridge import rigimport   # lazy: keeps the import graph flat
    text = _with_note(rigimport.import_and_retarget(
        exported, record.name, clip_fps=fps, set_timeline=_timeline(),
        target=kind, rig=rig,
        at=aim.get("point") if kind == "new_rig" else None), note)
    _status(text)
    return text


def _onto_skeleton(record, point=None):
    """One clip in the Skeleton mode (2026-10-01, «использовать скелет
    который активен в вкладке character»): the Characters card's skeleton
    added, with its geometry, and the clip transferred onto it standing on
    the floor `point` (None: where the clip is) - `skeletonimport`. The
    skeleton file is checked before the editor is asked. Returns the status
    line."""
    from maya_uebridge import skeletonimport   # lazy: keeps the import graph flat
    refusal = skeletonimport.precheck()
    if refusal:
        return refusal
    exported, fps = _export_from_editor(record)
    return skeletonimport.import_onto_skeleton(
        exported, record.name, clip_fps=fps, set_timeline=_timeline(), at=point)


def _onto_existing(record, root=None, note=""):
    """One clip onto a skeleton already in the scene (Skeleton x Onto
    selected, or a drop on it): `root`, else the one the selection names,
    else the only one - and with none standing, a new skeleton of the
    Characters card where the clip is (`_onto_skeleton`). Every refusal
    comes before the editor is asked. Returns the status line, `note` (the
    "only the first" of several) ahead of it."""
    from maya_uebridge import skeletonimport   # lazy: keeps the import graph flat
    if root is None:
        root, refusal = skeletonimport.target_skeleton()
        if refusal:
            return refusal
        if root is None:
            return _with_note(_onto_skeleton(record), note)
    refusal = skeletonimport.onto_refusal(root)
    if refusal:
        return refusal
    exported, fps = _export_from_editor(record)
    return _with_note(skeletonimport.import_onto_existing(
        exported, record.name, root, clip_fps=fps, set_timeline=_timeline()),
        note)


def import_line(name, info):
    """What the status says after a plain import. Pure, so the wording is tested."""
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


def export_uasset_selected():
    """Overwrite the selected AnimSequence with the scene's animation.

    The short road: no Perforce, an FBX staged in the temp folder, and the
    read-only flag cleared if it is set. Everything that can refuse refuses
    inside `uassetexport`, which also owns the confirm dialog -- this is only
    the UI state it needs.
    """
    chosen = _selected_records()
    if current_source() != "unreal" or any(
            getattr(r, "source", "unreal") != "unreal" for r in chosen):
        return _status("Export to uasset writes an Unreal asset - pick Unreal "
                       "in Connect and the AnimSequence to overwrite")
    if len(chosen) > 1:
        return _status("pick one animation to overwrite - {0} are picked"
                       .format(len(chosen)))
    from maya_uebridge import uassetexport   # lazy: keeps the import graph flat
    return _status(uassetexport.export_to_uasset(
        chosen[0] if chosen else None, _STATE.get("content_dir") or "",
        project_choice(), temp_folder()))


def export_fbx_selected():
    """A plain FBX of the resolved skeleton, where the dialog says.

    The p4-less half of what the Export tab used to do: the skeleton is the
    same one an import would target (selection, the rig, the sole
    skeleton), baked on export so no rig is ever touched.
    """
    from maya_uebridge import animexport   # lazy: keeps the import graph flat
    paths = cmds.fileDialog2(fileFilter="FBX (*.fbx)", dialogStyle=2,
                             fileMode=0, caption="Export skeleton animation")
    if not paths:
        _status("export cancelled")
        return
    info = animexport.export_hierarchy(paths[0])
    _status(animexport.export_line(os.path.basename(paths[0]), info))


# ---------------------------------------------------------------- window

def is_open():
    """True while the card we live in is built in the hub (read by
    maya_hotkeys): its status line is ours too."""
    return bool(cmds.control(_STATUS, exists=True))


def show_window():
    """Open the SkeldarAnim hub on the Characters card, where the bridge
    lives since 2026-10-01 (see `maya_hub`)."""
    import maya_hub
    return maya_hub.show(HUB_SECTION)


def editor_line(connected, cached=0):
    """The line above the editor dropdown: which state the bridge is in and,
    on open, what the cache holds. Pure."""
    if connected:
        return "connected"
    if cached:
        return ("not connected - {0} animations from the last refresh, press "
                "Refresh for the live list".format(cached))
    return "not connected - press Refresh to read the animations from the open editor"


def build_rows():
    """The bridge's rows, built into whatever layout is current - since
    2026-10-01 the Characters card's column, under the portraits («UE bridge
    и character ... объеденить в одно окно»). Returns nothing; the card owns
    the status line the rows write (`_STATUS`).

    Rows in a column, not a formLayout: measured in the hub 2026-09-17, a
    formLayout inside an adjustable column reported a 1128 px minimum
    width whatever its children were told, and the whole panel grew a
    horizontal scrollbar with the buttons pushed off the right edge.
    2026-09-28 (the skin): the target is short segments (the long
    explanation is their tooltip), Import the card's one primary action,
    the two exports a row under it. The editor line is the card's CONTEXT
    now - the character line is its subtitle.

    2026-10-08 («сделаем его компактным», variant B): the block stands on
    fewer rows. The skin has no «Connect» heading; the editor line is hidden
    there and its text is the project dropdown's tooltip, with a dot before
    the dropdown (● connected, ○ not); the search placeholder counts the
    animations (`search_hint`); the list shows ten rows by default and a grip
    under it moves that (`hubstyle.grip`); and ONE row holds [Onto sel. |
    New] [timeline] [Import] [FBX] [uasset] - the timeline box a clock chip,
    the FBX export an icon in the skin.
    """
    #  2026-10-02: ONE block set into the card - its own background, a
    #  hairline round it, padded («раздел с подключением ... визуально как-то
    #  отделить») - holding everything of the connection; the card's status
    #  line stays outside it. The skin paints it by its role ("inset"); the
    #  classic hub gives the column a background of its own.
    inset = cmds.columnLayout(_INSET, adjustableColumn=True,
                              rowSpacing=hubstyle.pick(3, 4),
                              columnAttach=("both", hubstyle.pick(0, 6)),
                              **hubstyle.pick({}, {"backgroundColor":
                                                   INSET_CLASSIC_BG}))
    hubstyle.mark(inset, "inset", layout=True)
    #  the block's title (2026-10-01 «UE Connect»; «Connect» since it reaches
    #  Unity and a folder too) - the classic hub's only: the compact skin's
    #  inset says it by standing apart (2026-10-08)
    if not hubstyle.skinning():
        hubstyle.mark(cmds.text(_HEADING, label="Connect", align="left",
                                font="boldLabelFont"), "heading")
    #  where the animations come from
    from maya_uebridge import sources
    segments = cmds.rowLayout(numberOfColumns=len(sources.SOURCES),
                              columnAttach=[(i + 1, "both", 1)
                                            for i in range(len(sources.SOURCES))])
    hubstyle.mark(segments, "segments", layout=True)
    cmds.iconTextRadioCollection(_SOURCE)
    remembered = _var(SOURCE_VAR, "unreal") or "unreal"
    if remembered not in sources.SOURCES:
        remembered = "unreal"
    tips = {"unreal": "The running Unreal editor's AnimSequences (Python "
                      "Remote Execution on)",
            "unity": "A Unity project read off the disk - Unity Hub's recent "
                     "projects, or Browse...: model files' clips and .anim "
                     "clips under Assets",
            "folder": "A folder of animation files: FBX (every take), Collada, "
                      "Maya .ma/.mb, BVH, glTF/GLB, USD, Unity .anim"}
    for source in sources.SOURCES:
        hubstyle.mark(cmds.iconTextRadioButton(
            source_button(source), style="textOnly",
            label=sources.LABELS[source],
            height=hubstyle.height("segment", 22),
            select=source == remembered, annotation=tips[source],
            onCommand=lambda *_a, s=source: _run(lambda: _source_changed(s))),
            "segment")
    cmds.setParent("..")
    #  the editor line: shown in the classic hub, hidden in the skin (its
    #  text is the dropdown's tooltip and the dot's state, `_header`).
    #  Two lines tall: a wrapped label keeps the one-line height it was
    #  given and clips the rest (measured in the hub, 2026-09-17).
    hubstyle.mark(cmds.text(_HEADER, label=editor_line(False), align="left",
                            wordWrap=True, height=36), "context")
    cmds.rowLayout(numberOfColumns=3, adjustableColumn=2,
                   columnAttach=[(1, "left", 0), (2, "both", 3),
                                 (3, "left", 3)])
    hubstyle.mark(cmds.text(_DOT, label=DOT_OFF, width=12, align="center",
                            annotation=editor_line(False)), "dot")
    cmds.optionMenu(
        _PROJECT, annotation="Unreal: the running editor to read from. Unity: "
                             "the project. Folder: the folder - Browse... "
                             "picks another",
        changeCommand=lambda *_: _run(_project_changed,
                                      busy="switching..."))
    hubstyle.mark(cmds.button(
        label=hubstyle.tool_label("Refresh"),
        width=hubstyle.tool_width(90), height=hubstyle.height("field", 24),
        annotation="Read the animations again: from the open editor, or a "
                   "scan of the project / folder",
        command=lambda *_: _run(refresh, busy=_refresh_busy())),
        "tool", "refresh")
    cmds.setParent("..")

    cmds.textField(_SEARCH, placeholderText=search_hint(0),
                   height=hubstyle.height("field", 24),
                   textChangedCommand=lambda *_: _run(_repopulate))

    cmds.textScrollList(
        _LIST, allowMultiSelection=True, font="fixedWidthFont",
        height=LIST_HEIGHT,
        annotation="Double-click imports the way Animation Setup and the Import "
                   "row say. Drag a row into a viewport: with Rig picked in "
                   "Animation Setup, onto a rig it retargets there and the rig "
                   "keeps its place, onto empty floor a new rig of the picked "
                   "portrait stands where you pointed; with Skeleton picked, "
                   "onto a skeleton it goes on that skeleton (a rig is "
                   "ignored), onto empty floor a new skeleton. Ctrl/Shift "
                   "pick several: onto a character the first goes; New and a "
                   "drop on the floor lay them all out in a square - about "
                   "the scene's zero for the button, about the point for a "
                   "drop.",
        doubleClickCommand=lambda *_: _run(import_selected, busy=_import_busy()))
    #  under the list its height grip (2026-10-08): the skin turns this 8 px
    #  placeholder into a grip and shows the list's remembered rows (ten by
    #  default); the classic hub keeps the list's pixel height and the
    #  placeholder is a quiet gap
    hubstyle.grip(cmds.separator(_LIST_GRIP, height=8, style="none"), _LIST)

    #  [Onto sel. | New] [clock] [Import] [FBX] [uasset] - one row (variant B)
    cmds.rowLayout(numberOfColumns=5, adjustableColumn=3,
                   columnAttach=[(1, "left", 0), (2, "left", 3),
                                 (3, "both", 3), (4, "left", 3),
                                 (5, "left", 3)])
    segments = cmds.rowLayout(numberOfColumns=len(TARGETS),
                              columnAttach=[(i + 1, "both", 1)
                                            for i in range(len(TARGETS))])
    hubstyle.mark(segments, "segments", layout=True)
    cmds.iconTextRadioCollection(_MODE)
    for target, label, note in TARGET_SEGMENTS:
        hubstyle.mark(cmds.iconTextRadioButton(
            target_button(target), style="textOnly",
            label=SHORT_TARGET.get(target, label),
            height=hubstyle.height("segment", 22),
            select=target == TARGETS[0], annotation=note), "segment")
    cmds.setParent("..")
    #  a clock pill in the skin, the word «timeline» in the classic hub
    hubstyle.mark(cmds.checkBox(
        _TIMELINE, label=hubstyle.pick("", "timeline"), value=True,
        annotation="set the timeline to the clip's range"), "chip", "clock")
    hubstyle.mark(cmds.button(
        label=hubstyle.pick("Import", "Import Animation"),
        height=hubstyle.height("button", 32),
        annotation="Import the selected animation(s) from the source onto the "
                   "character Animation Setup and the Import row say",
        command=lambda *_: _run(import_selected,
                                busy=_import_busy())),
        "primary", "download")
    hubstyle.mark(cmds.button(
        label=hubstyle.pick("", "FBX..."),
        height=hubstyle.height("button", 28), width=hubstyle.pick(26, 50),
        annotation="Export FBX... - Write the scene skeleton's animation to "
                   "an FBX of your choosing (selection, else the rig, else "
                   "the only skeleton), baked on export.",
        command=lambda *_: _run(export_fbx_selected,
                                busy="writing the fbx...")),
        "secondary", "upload")
    hubstyle.mark(cmds.button(
        _UASSET, label="uasset", height=hubstyle.height("button", 28),
        width=hubstyle.pick(52, 56),
        annotation="Overwrite the selected AnimSequence with the scene's "
                   "animation. Asks first. Does NOT touch Perforce: the "
                   "uasset is written on disk with no changelist behind it, "
                   "and a read-only flag is cleared. Unreal only.",
        command=lambda *_: _run(export_uasset_selected,
                                busy="writing the uasset...")),
        "secondary")
    cmds.setParent("..")
    cmds.setParent("..")             # out of the Connect block

    # Show the remembered source's last listing straight away (its cache);
    # Refresh replaces it with what is there now. Discovery on open would make
    # the card take a second to appear even with no editor about. Quiet: the
    # card's line says the portrait's choice on open.
    _source_changed(remembered)
    _attach_drag()


def source_button(source):
    """The Connect switch's segment of `source`."""
    return "{0}_{1}".format(_SOURCE, source)


def _refresh_busy():
    return {"unreal": "asking the editor...", "unity": "scanning the project...",
            "folder": "scanning the folder..."}.get(current_source(), "...")


def _import_busy():
    return ("exporting from the editor..." if current_source() == "unreal"
            else "importing...")


def _attach_drag():
    """The list's rows drag into a viewport (`listdrag`, 2026-10-01) where Qt
    stands; without it the list is the list it always was."""
    try:
        from maya_uebridge import listdrag   # lazy: Qt stays out of cmds
        listdrag.attach(_LIST, lambda: list(_STATE["filtered"]))
    except Exception:                                        # noqa: BLE001
        print(traceback.format_exc())
