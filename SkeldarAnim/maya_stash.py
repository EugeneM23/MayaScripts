"""maya_stash - Stash: the local shelf of drafts and intermediate files.

    import maya_stash; maya_stash.show_window()     # the hub, on Stash

The animator's ask (2026-10-09): «раздел в котором будет список сцен или
файлов (так как сейчас у нас сделано с разделом shared). Только ... это будет
локальное хранилище ... быстро сохранять какие-то черновики и промежуточные
файлы а потом их открывать или импортировать». Nothing here touches the
network: a scene or a file is COPIED into `<userAppDir>/SkeldarStash/` and
listed there (`maya_stashstore` is the rules, this is the Maya glue).

- **Stash scene** writes a copy of the open scene (`exportAll`, as Shared's
  send does): the working file, its name and its modified flag stay as they
  are. Without a typed Name the copy is `<scene>_HHMM`; a taken name gets
  ` (2)`, so a second press never overwrites the first.
- **Stash file...** copies a picked .ma / .mb / .fbx in the same way.
- **Stash selection (FBX)** exports the objects selected in the scene as one
  FBX through the plugin's exporter (2026-10-09). The selection is put back
  afterwards; the scene is not changed.
- **Open** opens a stash scene as the scene through `maya_scenesetup.opener.
  open_path` (script nodes off, the ranges read and applied, the vaccine
  swept). The scene open IS the stash file: Ctrl+S writes the draft back.
  An FBX opens as a new scene.
- **Import** brings a scene in with its script nodes removed, or an FBX in as
  its own skeleton in a namespace (`animimport.import_clip`), as Shared does.
- **Save to...** copies a stash file out where the animator picks.
- **Delete** removes the picked files from this disk after one confirm. The
  scene open in this Maya is refused by name: deleting the file under an open
  draft would let Save recreate it without anyone noticing.
- **Show folder** opens the stash folder in Explorer.

Nothing is opened, sent or imported by itself. The state lives on
`sys._skeldar_stash` (trap 111): a purge of our modules does not lose it.

Spec: docs/superpowers/specs/2026-10-09-stash-design.md
"""

import os
import shutil
import sys
import time
import traceback

import maya.cmds as cmds
import maya.mel as mel

import maya_sharerecords as records
import maya_stashstore as store

HUB_SECTION = "stash"
NAME_FIELD = "skeldarStashName"
LIST = "skeldarStashList"
#  the placeholder under the list the skin turns into its height grip
LIST_GRIP = "skeldarStashListGrip"
STATUS = "skeldarStashStatus"
SUBTITLE = "skeldarStashSubtitle"
LIST_HEIGHT = 150


# ------------------------------------------------------------------ state

def state():
    """The section's state on `sys`: the rows as listed (folder names, in
    list order). One per Maya session, whatever module object asks."""
    st = getattr(sys, "_skeldar_stash", None)
    if st is None:
        st = {"rows": []}
        sys._skeldar_stash = st
    return st


def folder():
    """The stash folder under the user's prefs; created on demand by the
    presses that write into it, never by a listing. Normalised: Maya's
    userAppDir ends in a slash of its own."""
    return os.path.normpath(os.path.join(
        cmds.internalVar(userAppDir=True), store.FOLDER))


def _path(name):
    return os.path.join(folder(), name)


def scan():
    """The items in the folder, newest first (`maya_stashstore.entries`)."""
    if not os.path.isdir(folder()):
        return []
    listing = []
    for name in os.listdir(folder()):
        path = _path(name)
        if store.is_item(name) and os.path.isfile(path):
            info = os.stat(path)
            listing.append((name, info.st_size, info.st_mtime))
    return store.entries(listing)


def _taken():
    if not os.path.isdir(folder()):
        return []
    return os.listdir(folder())


def _makedirs():
    os.makedirs(folder(), exist_ok=True)


def _typed_name():
    if cmds.textField(NAME_FIELD, exists=True):
        return cmds.textField(NAME_FIELD, query=True, text=True) or ""
    return ""


def _clear_name():
    if cmds.textField(NAME_FIELD, exists=True):
        cmds.textField(NAME_FIELD, edit=True, text="")


def _open_scene_path():
    scene = cmds.file(query=True, sceneName=True) or ""
    return os.path.normcase(os.path.abspath(scene)) if scene else ""


def _is_open_scene(path):
    scene = _open_scene_path()
    return bool(scene) and os.path.normcase(os.path.abspath(path)) == scene


def selected_names():
    """The picked rows' file names, top to bottom (the list takes several)."""
    if not cmds.textScrollList(LIST, exists=True):
        return []
    picked = cmds.textScrollList(LIST, query=True,
                                 selectIndexedItem=True) or []
    rows = state()["rows"]
    return [rows[index - 1] for index in picked if 0 < index <= len(rows)]


def _one_picked(verb):
    """(name, "") for the one picked row, else (None, what to say)."""
    names = selected_names()
    if not names:
        return None, "Pick a file in the list first."
    if len(names) > 1:
        return None, "Pick one file to {0} - {1} are picked.".format(
            verb, len(names))
    return names[0], ""


# ---------------------------------------------------------------- stashing

def stash_scene(name=None):
    """The press: a copy of the open scene into the stash. `name` (else the
    Name field's text, else the scene's own stem with the time) names it."""
    scene = cmds.file(query=True, sceneName=True) or ""
    fallback = store.draft_name(scene, time.time())
    typed = _typed_name() if name is None else name
    base = records.upload_name(typed, fallback)
    _makedirs()
    target = store.unique_name(base, _taken())
    path = _path(target)
    _own, file_type = records.scene_file_name(scene, time.time())
    #  a copy: the working file, its name and its modified flag stay
    cmds.file(path, exportAll=True, type=file_type, force=True,
              preserveReferences=False)
    _clear_name()
    refresh()
    size = os.path.getsize(path)
    return _status("Stashed {0} - {1}. The open scene is untouched.".format(
        target, records.size_text(size)))


class ExportFailed(Exception):
    """The FBX exporter refused or wrote nothing; the message says why."""


def _export_fbx(nodes, path):
    """The objects `nodes` (long names) into one FBX at `path`, through the
    plugin's own exporter. The scene's selection is put back afterwards, and
    the scene itself is not changed. Raises ExportFailed."""
    previous = cmds.ls(selection=True, long=True) or []
    try:
        cmds.loadPlugin("fbxmaya", quiet=True)
    except RuntimeError as exc:
        raise ExportFailed("the FBX plugin will not load ({0})".format(exc))
    try:
        cmds.select(nodes, replace=True)
        mel.eval("FBXResetExport; FBXExportSmoothingGroups -v true; "
                 "FBXExportSkins -v true; FBXExportShapes -v true; "
                 "FBXExportIncludeChildren -v true")
        mel.eval('FBXExport -f "{0}" -s'.format(path.replace("\\", "/")))
    except RuntimeError as exc:
        _remove(path)
        raise ExportFailed(str(exc).strip() or "the exporter refused")
    finally:
        if previous:
            cmds.select(previous, replace=True)
        else:
            cmds.select(clear=True)
    if not os.path.isfile(path) or os.path.getsize(path) == 0:
        _remove(path)
        raise ExportFailed("the exporter wrote nothing")


def _remove(path):
    try:
        if os.path.isfile(path):
            os.remove(path)
    except OSError:
        pass


def stash_selection(name=None):
    """The press: the objects selected in the scene, as one FBX in the stash.
    Called `name` (else the Name field's text, else the object's own name, or
    `selection` for several). Nothing in the scene changes."""
    picked = cmds.ls(selection=True, long=True) or []
    if not picked:
        return _status("Select the objects to stash first.")
    fallback = store.selection_name(picked, time.time())
    typed = _typed_name() if name is None else name
    base = records.upload_name(typed, fallback)
    _makedirs()
    target = store.unique_name(base, _taken())
    path = _path(target)
    try:
        _export_fbx(picked, path)
    except ExportFailed as exc:
        return _status("Could not stash the selection - the FBX export "
                       "failed: {0}. Nothing was stashed.".format(exc))
    _clear_name()
    refresh()
    count = len(picked)
    return _status("Stashed {0} from the scene - {1} object{2}, {3}. The "
                   "scene is untouched.".format(
                       target, count, "" if count == 1 else "s",
                       records.size_text(os.path.getsize(path))))


def stash_file(path=None, name=None):
    """The press: `path` (else a file dialog's pick) copied into the stash,
    called `name` (else the Name field's text, else its own name)."""
    path = path or _pick_file()
    if not path:
        return _status("Nothing stashed.")
    own = os.path.basename(path)
    if not store.is_item(own):
        return _status("Only .ma, .mb and .fbx files can be stashed - "
                       "nothing stashed.")
    if not os.path.isfile(path):
        return _status("No file at {0} - nothing stashed.".format(path))
    typed = _typed_name() if name is None else name
    base = records.upload_name(typed, own)
    _makedirs()
    target = store.unique_name(base, _taken())
    shutil.copy2(path, _path(target))
    _clear_name()
    refresh()
    return _status("Stashed {0} - {1}.".format(target, records.size_text(
        os.path.getsize(_path(target)))))


def _pick_file():
    picked = cmds.fileDialog2(
        fileMode=1, caption="Stash a file",
        fileFilter="Maya scenes and FBX (*.ma *.mb *.fbx)")
    return picked[0] if picked else ""


# ----------------------------------------------------------------- actions

def _is_fbx(name):
    return name.lower().endswith(".fbx")


def open_selected(*_args):
    """Open the picked stash file: a scene as the scene (it IS the draft
    from here on), an FBX as a new scene."""
    name, why = _one_picked("open")
    if name is None:
        return _status(why)
    path = _path(name)
    if not os.path.isfile(path):
        refresh()
        return _status("{0} is no longer in the stash.".format(name))
    from maya_scenesetup import opener
    opened, note = opener.open_path(path)
    if not opened:
        return _status("Open cancelled - nothing changed.")
    refresh()
    if _is_fbx(name):
        return _status("Opened {0} from the stash as a new scene.".format(name))
    return _status("Opened {0} from the stash{1} - Ctrl+S writes the draft "
                   "back into the stash.".format(name, note))


def _import_fbx(path, name):
    from maya_uebridge import animimport
    from maya_uebridge import records as bridge_records
    namespace = bridge_records.namespace_for(os.path.splitext(name)[0],
                                             animimport.existing_namespaces())
    result = animimport.import_clip(path, namespace=namespace, merge=False,
                                    set_timeline=True)
    if not result.get("nodes"):
        return "{0} brought nothing into the scene.".format(name)
    return "Imported {0} as {1} - {2} joints, {3} curves.".format(
        name, namespace, result.get("joints", 0), result.get("curves", 0))


def _import_scene(path, name):
    nodes = cmds.file(path, i=True, executeScriptNodes=False,
                      ignoreVersion=True, returnNewNodes=True,
                      mergeNamespacesOnClash=False, prompt=False) or []
    #  nothing in an imported file ran: its script nodes go (the vaccine)
    removed = 0
    for node in cmds.ls(nodes, type="script") or []:
        if cmds.objExists(node):
            try:
                cmds.lockNode(node, lock=False)
                cmds.delete(node)
                removed += 1
            except Exception:                                # noqa: BLE001
                pass
    note = (" - {0} script node{1} removed".format(
        removed, "" if removed == 1 else "s")) if removed else ""
    return "Imported {0} from the stash - {1} nodes{2}".format(
        name, len(nodes), note)


def import_selected(*_args):
    """Import the picked stash file into the open scene."""
    name, why = _one_picked("import")
    if name is None:
        return _status(why)
    path = _path(name)
    if not os.path.isfile(path):
        refresh()
        return _status("{0} is no longer in the stash.".format(name))
    if _is_fbx(name):
        return _status(_import_fbx(path, name))
    return _status(_import_scene(path, name))


def save_selected(*_args):
    """A copy of the picked stash file where the animator picks."""
    name, why = _one_picked("save")
    if name is None:
        return _status(why)
    path = _path(name)
    if not os.path.isfile(path):
        refresh()
        return _status("{0} is no longer in the stash.".format(name))
    picked = cmds.fileDialog2(
        fileMode=0, caption="Save a stashed file", startingDirectory=name,
        fileFilter="{0} (*{1})".format(name, os.path.splitext(name)[1]))
    dest = picked[0] if picked else ""
    if not dest:
        return _status("Nothing saved.")
    shutil.copy2(path, dest)
    return _status("Saved {0} to {1}".format(name, dest.replace("\\", "/")))


def _confirm_delete(text):
    """Maya's confirm before a delete; True to go on. Batch has nobody to
    answer (a verify run): it goes on."""
    if cmds.about(batch=True):
        return True
    answer = cmds.confirmDialog(
        title="Stash - Delete", message=text, icon="warning",
        button=["Delete", "Cancel"], defaultButton="Cancel",
        cancelButton="Cancel", dismissString="Cancel")
    return answer == "Delete"


def delete_names(names):
    """The press: the stash files `names` removed from this disk, after one
    confirm. The scene open in this Maya is refused by name."""
    refused = [n for n in names if _is_open_scene(_path(n))]
    names = [n for n in names if n not in refused]
    lines = [store.open_refusal(n) for n in refused]
    if not names:
        refresh()
        return _status(" ".join(lines) or "Pick files in the list first.")
    if not _confirm_delete(store.delete_question(names)):
        return _status("Delete cancelled - nothing changed.")
    gone = []
    for name in names:
        try:
            os.remove(_path(name))
            gone.append(name)
        except OSError as exc:
            lines.append("{0} not deleted: {1}".format(name, exc.strerror))
    refresh()
    head = "Deleted {0} file{1} from the stash".format(
        len(gone), "" if len(gone) == 1 else "s") if gone else ""
    return _status(" ".join(([head + "."] if head else []) + lines))


def delete_selected(*_args):
    names = selected_names()
    if not names:
        return _status("Pick files in the list first.")
    return delete_names(names)


def show_folder(*_args):
    """The stash folder in Explorer (created first, so it always opens)."""
    _makedirs()
    try:
        os.startfile(folder())
    except OSError as exc:
        return _status("Could not open {0}: {1}".format(folder(), exc))
    return _status("Opened {0}".format(folder()))


# ---------------------------------------------------------------------- UI

def _status(message, **_kwargs):
    """The section's status line; a line written is also told to the hub
    (`hubstyle.tell`), as the Shared section does."""
    print("SkeldarAnim stash: " + message)
    shown = False
    try:
        if cmds.text(STATUS, exists=True):
            cmds.text(STATUS, edit=True, label=message)
            shown = True
            import maya_hubstyle   # stdlib
            maya_hubstyle.tell(STATUS, message)
    except Exception:                                        # noqa: BLE001
        pass
    hub = sys.modules.get("maya_hub")
    if hub is not None and not shown:
        try:
            hub.say(message)
        except Exception:                                    # noqa: BLE001
            pass
    return message


def refresh():
    """The list from the folder, keeping the picked rows by name."""
    if not cmds.textScrollList(LIST, exists=True):
        return
    keep = selected_names()
    items = scan()
    now = time.time()
    names = [item["name"] for item in items]
    cmds.textScrollList(LIST, edit=True, removeAll=True)
    for item in items:
        cmds.textScrollList(LIST, edit=True,
                            append=store.row_text(item, now))
    state()["rows"] = names
    again = [names.index(n) + 1 for n in keep if n in names]
    if again:
        cmds.textScrollList(LIST, edit=True, selectIndexedItem=again)
    refresh_subtitle()


def refresh_subtitle():
    if cmds.text(SUBTITLE, exists=True):
        cmds.text(SUBTITLE, edit=True,
                  label=store.subtitle(len(state()["rows"])))


def _selected(*_args):
    names = selected_names()
    if len(names) > 1:
        return _status(store.picked_text(len(names)))
    if len(names) == 1 and os.path.isfile(_path(names[0])):
        info = os.stat(_path(names[0]))
        return _status("{0} - {1}, {2}. Open, Import or Save to...".format(
            names[0], records.size_text(info.st_size),
            records.when_text(info.st_mtime, time.time())))
    return None


def _run(action):
    try:
        return action()
    except Exception as exc:                                 # noqa: BLE001
        print(traceback.format_exc())
        return _status("Stash failed: {0}".format(exc))


def build_panel():
    """The Name field, Stash scene / Stash file..., the list (several rows
    can be picked), Open / Import / icons for Save to..., Show folder and
    Delete, a status line. Lists the folder once; nothing listens.

    The compact skin and the classic hub share one arrangement: the skin's
    labels are the placeholders' and the icons' (hubstyle.pick)."""
    import maya_hubstyle as hubstyle   # stdlib
    cmds.columnLayout(adjustableColumn=True,
                      rowSpacing=hubstyle.row_spacing(6),
                      columnOffset=("both", hubstyle.pick(0, 8)))
    hubstyle.mark(cmds.text(SUBTITLE, label="", align="left"), "subtitle")
    cmds.textField(NAME_FIELD, text="",
                   placeholderText="name (empty: the scene's, with the time)",
                   height=hubstyle.height("field", 24),
                   annotation="the name the next stash is called: a taken "
                              "name gets (2), (3) ...")
    cmds.rowLayout(numberOfColumns=2, adjustableColumn=1,
                   columnAttach=[(1, "both", 0), (2, "both", 3)])
    hubstyle.mark(cmds.button(
        label="Stash scene", height=hubstyle.height("button", 32),
        annotation="A copy of the open scene into the stash, on this "
                   "machine. Your file is not touched.",
        command=lambda *_: _run(stash_scene)), "primary", "archive")
    hubstyle.mark(cmds.button(
        label="Stash file...", height=hubstyle.height("button", 32),
        width=hubstyle.pick(104, 110),
        annotation="Pick a .ma, .mb or .fbx and copy it into the stash",
        command=lambda *_: _run(stash_file)), "secondary", "plus")
    cmds.setParent("..")
    cmds.rowLayout(numberOfColumns=1, adjustableColumn=1)
    hubstyle.mark(cmds.button(
        label="Stash selection (FBX)", height=hubstyle.height("button", 28),
        annotation="The objects selected in the scene, as one FBX in the "
                   "stash. The scene is not changed.",
        command=lambda *_: _run(stash_selection)), "secondary", "hand-grab")
    cmds.setParent("..")
    cmds.textScrollList(
        LIST, allowMultiSelection=True, font="fixedWidthFont",
        height=LIST_HEIGHT,
        selectCommand=lambda *_: _run(_selected),
        doubleClickCommand=lambda *_: _run(open_selected),
        deleteKeyCommand=lambda *_: _run(delete_selected))
    hubstyle.grip(cmds.separator(LIST_GRIP, height=8, style="none"), LIST)
    cmds.rowLayout(numberOfColumns=6, adjustableColumn=1,
                   columnAttach=[(1, "both", 0), (2, "both", 4),
                                 (3, "both", 4), (4, "both", 4),
                                 (5, "both", 4), (6, "both", 4)])
    hubstyle.mark(cmds.button(
        label="Open", height=hubstyle.height("button", 28),
        annotation="Open the picked draft. A scene opened here is the stash "
                   "file: Ctrl+S writes it back.",
        command=lambda *_: _run(open_selected)), "secondary", "download")
    hubstyle.mark(cmds.button(
        label="Import", height=hubstyle.height("button", 28),
        width=hubstyle.pick(84, 80),
        annotation="Import the picked file into the open scene (an FBX "
                   "arrives as its own skeleton, in a namespace)",
        command=lambda *_: _run(import_selected)), "secondary", "transfer-in")
    hubstyle.mark(cmds.button(
        label=hubstyle.pick("", "Save to..."),
        height=hubstyle.height("button", 28),
        width=hubstyle.pick(26, 90),
        annotation="Save a copy of the picked file where you choose",
        command=lambda *_: _run(save_selected)), "secondary", "upload")
    hubstyle.mark(cmds.button(
        label=hubstyle.pick("", "Show folder"),
        height=hubstyle.height("button", 28),
        width=hubstyle.pick(26, 96),
        annotation="Open the stash folder in Explorer",
        command=lambda *_: _run(show_folder)), "secondary", "folder")
    hubstyle.mark(cmds.button(
        label=hubstyle.pick("", "Delete"),
        height=hubstyle.height("button", 28),
        width=hubstyle.pick(26, 64),
        annotation="Delete the picked files from this disk (the Delete key "
                   "too). Nothing is sent, nothing is kept elsewhere.",
        command=lambda *_: _run(delete_selected)), "danger", "trash")
    cmds.setParent("..")
    hubstyle.mark(cmds.text(STATUS, label="", align="left", wordWrap=True,
                            height=36), "status")
    cmds.setParent("..")
    state()["rows"] = []
    refresh()
    return None


def is_open():
    return bool(cmds.textScrollList(LIST, exists=True))


def show_window():
    """The hub, on the Stash section."""
    import maya_hub
    return maya_hub.show(HUB_SECTION)
