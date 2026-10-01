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
_TIMELINE = "ueAnimBridgeTimeline"
_PROJECT = "ueAnimBridgeProject"
_MODE = "ueAnimBridgeMode"

# Windows earlier builds left open: the checkouts popup of 2026-08-21's
# afternoon, and the bridge's own standalone window (before the hub,
# 2026-09-17). `maya_hub.show` deletes both, or a panel from an older
# build stays up wired to dead code.
LEGACY_WINDOWS = ("ueBridgeCheckouts", "ueAnimBridgeWindow")

CACHE_NAME = "maya_uebridge_cache.json"

_STATE = {"records": [], "filtered": [], "project": "", "choice": "",
          "content_dir": ""}


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


#  The press's internal modes: the Characters card's kind times the target.
MODES = ("rig", "new_rig", "skeleton", "onto_skeleton")
KINDS = ("rig", "skeleton")                 # the Characters card's switch
TARGETS = ("onto", "new")                   # the Import row's two segments

#  (target, the segment's label, its tooltip) -- since 2026-10-01 the card's
#  [Rig | Skeleton] says WHAT a press makes, these two say WHERE it goes
#  («Слить»: the bridge's old Rig / New rig / Skeleton said the kind twice).
TARGET_SEGMENTS = (
    ("onto", "Onto selected",
     "Onto the selected character: with Rig picked in Characters the "
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
     "Characters says - takes the clip; several picked stand in a square "
     "about the scene's zero, one per animation."),
)


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
        entry = scene_window.chosen_character()
        kind = entry.kind if entry is not None else scene_window.remembered_choice()[1]
    except Exception:                                        # noqa: BLE001
        return KINDS[0]
    return kind if kind in KINDS else KINDS[0]


def import_mode():
    """The press's mode: `mode_for(import_kind(), import_target())`."""
    return mode_for(import_kind(), import_target())


def retarget_selected():
    """True when IMPORT retargets onto a rig (the selected one or a new
    one); False when it puts the clip on a skeleton."""
    return import_mode() in ("rig", "new_rig")


def _export_from_editor(record):
    """The clip out of the editor into the temp folder: (fbx path, fps)."""
    out = os.path.join(temp_folder(), "export.json")
    fbx = os.path.join(temp_folder(), "{0}.fbx".format(record.name))
    # Export from the same editor the list came from, or a second open project
    # would answer with an asset path it does not have.
    payload = uelink.run_script(uescripts.export_script(out, record.package, fbx),
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
        return "Unreal: connected"
    if cached:
        return ("Unreal: not connected - {0} animations from the last "
                "refresh, press Refresh for the live list".format(cached))
    return ("Unreal: not connected - press Refresh to read the animations "
            "from the open editor")


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
    """
    #  two lines tall: a wrapped label keeps the one-line height it was
    #  given and clips the rest (measured in the hub, 2026-09-17).
    hubstyle.mark(cmds.text(_HEADER, label=editor_line(False), align="left",
                            wordWrap=True, height=36), "context")
    cmds.rowLayout(numberOfColumns=2, adjustableColumn=1,
                   columnAttach=[(1, "both", 0), (2, "left", 4)])
    cmds.optionMenu(
        _PROJECT, annotation="The running Unreal editor to read from",
        changeCommand=lambda *_: _run(_project_changed,
                                      busy="switching editor..."))
    hubstyle.mark(cmds.button(
        label=hubstyle.tool_label("Refresh"),
        width=hubstyle.tool_width(90), height=24,
        annotation="Read the animations from the open editor",
        command=lambda *_: _run(refresh, busy="asking the editor...")),
        "tool", "refresh")
    cmds.setParent("..")

    cmds.textField(_SEARCH, placeholderText="search name or folder",
                   textChangedCommand=lambda *_: _run(_repopulate))

    cmds.textScrollList(
        _LIST, allowMultiSelection=True, font="fixedWidthFont",
        height=LIST_HEIGHT,
        annotation="Double-click imports the way Characters and the Import "
                   "row say. Drag a row into a viewport: with Rig picked in "
                   "Characters, onto a rig it retargets there and the rig "
                   "keeps its place, onto empty floor a new rig of the picked "
                   "portrait stands where you pointed; with Skeleton picked, "
                   "onto a skeleton it goes on that skeleton (a rig is "
                   "ignored), onto empty floor a new skeleton. Ctrl/Shift "
                   "pick several: onto a character the first goes; New and a "
                   "drop on the floor lay them all out in a square - about "
                   "the scene's zero for the button, about the point for a "
                   "drop.",
        doubleClickCommand=lambda *_: _run(import_selected,
                                           busy="exporting from the editor..."))

    cmds.rowLayout(numberOfColumns=2, adjustableColumn=2,
                   columnAttach=[(1, "left", 0), (2, "both", 4)])
    cmds.text(label="Import", align="left")
    segments = cmds.rowLayout(numberOfColumns=len(TARGETS),
                              columnAttach=[(i + 1, "both", 1)
                                            for i in range(len(TARGETS))])
    hubstyle.mark(segments, "segments", layout=True)
    cmds.iconTextRadioCollection(_MODE)
    for target, label, note in TARGET_SEGMENTS:
        hubstyle.mark(cmds.iconTextRadioButton(
            target_button(target), style="textOnly", label=label, height=22,
            select=target == TARGETS[0], annotation=note), "segment")
    cmds.setParent("..")
    cmds.setParent("..")
    cmds.checkBox(_TIMELINE, label="set timeline to clip range", value=True)

    hubstyle.mark(cmds.button(
        label="Import", height=32,
        annotation="Import the selected animation(s) from Unreal onto the "
                   "character Characters and the Import row say",
        command=lambda *_: _run(import_selected,
                                busy="exporting from the editor...")),
        "primary", "download")
    cmds.rowLayout(numberOfColumns=2, adjustableColumn=1,
                   columnAttach=[(1, "both", 0), (2, "both", 4)])
    hubstyle.mark(cmds.button(
        label="Export FBX...", height=28,
        annotation="Write the scene skeleton's animation to an FBX of your "
                   "choosing (selection, else the rig, else the only "
                   "skeleton), baked on export.",
        command=lambda *_: _run(export_fbx_selected,
                                busy="writing the fbx...")),
        "secondary", "upload")
    hubstyle.mark(cmds.button(
        label="Export to uasset", height=28, width=130,
        annotation="Overwrite the selected AnimSequence with the scene's "
                   "animation. Asks first. Does NOT touch Perforce: the "
                   "uasset is written on disk with no changelist behind it, "
                   "and a read-only flag is cleared.",
        command=lambda *_: _run(export_uasset_selected,
                                busy="writing the uasset...")),
        "secondary")
    cmds.setParent("..")

    cached, project, choice, content_dir = load_cache()
    _STATE["records"] = cached
    _STATE["project"] = project
    _STATE["choice"] = choice
    _STATE["content_dir"] = content_dir
    # Show the remembered project straight away; Refresh replaces the menu with
    # whatever is actually running. Discovery on open would make the window
    # take a second to appear even with no editor about.
    if choice or project:
        fill_project_menu([choice or _project_label(project)])
    # Quiet: the card's line says the portrait's choice on open; the cache is
    # the editor line's to say.
    _repopulate(quiet=True)
    _header(editor_line(False, len(cached)))
    _attach_drag()


def _attach_drag():
    """The list's rows drag into a viewport (`listdrag`, 2026-10-01) where Qt
    stands; without it the list is the list it always was."""
    try:
        from maya_uebridge import listdrag   # lazy: Qt stays out of cmds
        listdrag.attach(_LIST, lambda: list(_STATE["filtered"]))
    except Exception:                                        # noqa: BLE001
        print(traceback.format_exc())
