"""The Export tab of the bridge window: my checked-out AnimSequence uassets,
the pair checkout (uasset+fbx together), revert, and the export back into
the uasset.

The invariant this window exists for, in the user's words: «у нас не должно
быть такой ситуации что скрипт видит uasset на чекауте в перфорсе а fbx в
сорс каталоге нету» - the source fbx is the intermediary the pipeline works
through, so a checkout through the bridge always leaves the pair complete,
creating the fbx from the editor when it exists nowhere.

Every dialog is injectable (`asks=`), for the same reason as vcs.py: a modal
over the command port blocks Maya's idle queue.
"""

import collections
import os
import traceback

import maya.cmds as cmds

from maya_uebridge import animexport
from maya_uebridge import animimport
from maya_uebridge import records
from maya_uebridge import uelink
from maya_uebridge import uescripts
from maya_uebridge import vcs
from maya_uebridge import window

# The 2026-08-21 popup window this tab replaced. Deleted on every bridge
# open, or a panel left up from before stays wired to dead code (the
# maya_scenesetup rename paid for this one).
LEGACY_WINDOW = "ueBridgeCheckouts"
_LIST = "ueBridgeCheckoutsList"

_STATE = {"rows": [], "checked": set(), "modified": set()}

# The perforce-style mark on a checked-out row, and a blank of the SAME
# character width so unmarked rows keep their columns.
TICK = "✓ "
NO_TICK = "  "

# Foreground for a modified row - readable green on Maya's dark theme.
GREEN = (95, 220, 95)

CheckoutRow = collections.namedtuple(
    "CheckoutRow",
    ["record", "client_file", "action", "fbx", "fbx_path", "modified"])
# A row built before the modified flag existed (older callers, tests) is
# simply not modified.
CheckoutRow.__new__.__defaults__ = (False,)


# ---------------------------------------------------------------- pure

def anim_checkouts(opened, content_dir, record_list):
    """Match p4's opened uassets to known AnimSequences, sorted by name.

    Anything not in the record list is dropped - the window is about
    animations, never the depot's every uasset. Pure.
    """
    by_package = dict((rec.package.lower(), rec) for rec in record_list)
    rows = []
    for fields in opened:
        package = vcs.package_of(fields.get("clientFile", ""), content_dir)
        record = by_package.get(package.lower()) if package else None
        if record is None:
            continue
        rows.append((record, fields.get("clientFile", ""),
                     fields.get("action", "")))
    rows.sort(key=lambda row: row[0].name.lower())
    return rows


def is_modified(client_file, action, changed):
    """Whether a checkout row counts as changed. An add always does - it has
    no depot side to differ from; an edit follows `p4 diff -sa`. Pure."""
    if "add" in (action or ""):
        return True
    return os.path.normcase(client_file or "") in changed


def mark_prefix(package, checked):
    """The tick for a checked-out package, a same-width blank otherwise.
    `checked` holds lowercase packages. Pure."""
    return TICK if (package or "").lower() in checked else NO_TICK


def marks():
    """(checked, modified): lowercase package sets from the LAST p4 read.
    The import list marks its rows from these without polling anything -
    they move only when Refresh or a file action runs `load_rows`."""
    return _STATE["checked"], _STATE["modified"]


def format_row(row):
    """One fixed-width line: tick, name, folder tail, p4 action, fbx state.
    Every row here is a checkout, so every row carries the tick - the same
    mark the import list puts on its checked-out rows."""
    folder = row.record.package.rsplit("/", 1)[0]
    shown = row.fbx.upper() if row.fbx == "missing" else row.fbx
    return "{0}{1:<{2}} {3:<{4}} {5:<6} fbx {6}".format(
        TICK,
        records._middle(row.record.name, records.NAME_WIDTH),
        records.NAME_WIDTH,
        records._tail(folder, 30), 30,
        row.action, shown)


def count_line(count):
    if not count:
        return "nothing checked out"
    return "{0} animation uasset(s) checked out".format(count)


# Moved to records.py (2026-09-01): both export directions read this
# payload, and duplicating the wording is how two status lines drift apart.
reimport_line = records.reimport_line


# ---------------------------------------------------------------- lookups

def fbx_state(name, root, run):
    """("ok"|"depot"|"missing", path): where the прокладка is."""
    hits = vcs.find_fbx(name, root)
    if hits:
        return "ok", hits[0]
    for fields in vcs.find_fbx_depot(name, root, run):
        return "depot", fields.get("clientFile", "")
    return "missing", ""


def content_dir():
    """The project's Content folder: the cached listing first, discovery's
    pong (which carries project_root) second, "" when unknowable."""
    known = window._STATE.get("content_dir") or ""
    if known and os.path.isdir(known):
        return known
    try:
        nodes = uelink.discover_nodes()
    except uelink.UeBridgeError:
        return ""
    node = uelink.pick_node(nodes, window.project_choice()) or {}
    root = str(node.get("project_root") or "")
    if not root:
        return ""
    found = os.path.join(root, "Content")
    return found if os.path.isdir(found) else ""


def load_rows(run=vcs.run_p4):
    """(rows, failure). Needs the Content dir and the cached animation list -
    without the list nothing can be classified as an AnimSequence."""
    folder = content_dir()
    if not folder:
        return [], "no Content dir known - press Refresh in the bridge first"
    if not window._STATE.get("records"):
        return [], "no animation list - press Refresh in the bridge first"
    opened, failure = vcs.opened_records(folder, run=run)
    if failure:
        return [], failure
    matched = anim_checkouts(opened, folder, window._STATE["records"])
    # Best-effort: a diff that cannot answer costs the green marks, never
    # the listing.
    changed, _ = vcs.modified_under(folder, run=run)
    root = window._saved_root()
    rows = []
    for record, client_file, action in matched:
        state, path = fbx_state(record.name, root, run)
        rows.append(CheckoutRow(record, client_file, action, state, path,
                                is_modified(client_file, action, changed)))
    # The mark sets the import list reads through marks(), refreshed by the
    # same call that refreshed the rows.
    _STATE["checked"] = set(row.record.package.lower() for row in rows)
    _STATE["modified"] = set(row.record.package.lower() for row in rows
                             if row.modified)
    return rows, ""


# ---------------------------------------------------------------- actions

def _fbx_from_editor(record, target):
    """Export the CURRENT animation out of the editor onto `target`, so the
    прокладка holds the uasset's pre-edit state from the moment of checkout."""
    out = os.path.join(window.temp_folder(), "export.json")
    temp = os.path.join(window.temp_folder(), "{0}.fbx".format(record.name))
    payload = uelink.run_script(
        uescripts.export_script(out, record.package, temp),
        out, project=window.project_choice())
    vcs.place(payload.get("path") or temp, target)


def checkout_pair(record, asks=None):
    """Open the uasset AND its fbx; create the fbx when it exists nowhere.
    Returns the status text. The pair is the user's pick: one changelist,
    one submit, source and asset never drift apart in the depot."""
    asks = asks or {}
    run = asks.get("run", vcs.run_p4)
    folder = content_dir()
    if not folder:
        return "no Content dir known - press Refresh first"

    uasset = vcs.uasset_path_of(record.package, folder)
    fields, failure = vcs.fstat(uasset, run)
    if failure:
        return "no checkout - " + failure
    decision = vcs.plan_for(fields)
    if decision["kind"] == "others":
        return "checked out by " + ", ".join(decision["users"])
    if decision["kind"] == "untracked":
        return "uasset is not in the depot: " + record.name
    uasset_note = "uasset already checked out"
    if decision["kind"] == "edit":
        failure = vcs.checkout(uasset, run)
        if failure:
            return "no checkout - " + failure
        uasset_note = "uasset checked out"

    resolved = window._vcs_target(record, asks)
    if resolved is None:
        return uasset_note + ", fbx cancelled"
    target, _is_new = resolved

    if not os.path.isfile(target):
        fbx_fields, failure = vcs.fstat(target, run)
        if failure:
            return "{0}, fbx unknown - {1}".format(uasset_note, failure)
        if fbx_fields.get("depotFile"):
            failure = vcs.checkout(target, run)  # sync-retry lives inside
            fbx_note = ("fbx synced and checked out" if not failure
                        else "fbx not opened - " + failure)
        else:
            _fbx_from_editor(record, target)
            failure = vcs.add(target, run)
            fbx_note = ("fbx created from the editor and added"
                        if not failure
                        else "fbx created, not added - " + failure)
    else:
        fbx_fields, failure = vcs.fstat(target, run)
        if failure:
            fbx_note = "fbx not opened - " + failure
        else:
            action = vcs.open_action(fbx_fields)
            if action == "edit":
                failure = vcs.checkout(target, run)
                fbx_note = ("fbx checked out" if not failure
                            else "fbx not opened - " + failure)
            elif action == "add":
                failure = vcs.add(target, run)
                fbx_note = ("fbx added" if not failure
                            else "fbx not added - " + failure)
            elif action == "others":
                fbx_note = ("fbx checked out by "
                            + ", ".join(vcs.other_openers(fbx_fields)))
            else:
                fbx_note = "fbx already checked out"

    return "{0}: {1}, {2}".format(record.name, uasset_note, fbx_note)


def _ask_revert(paths):
    answer = cmds.confirmDialog(
        title="Perforce revert", icon="warning",
        message="Revert discards local changes:\n\n  {0}".format(
            "\n  ".join(paths)),
        button=["Revert", "Cancel"], defaultButton="Cancel",
        cancelButton="Cancel", dismissString="Cancel")
    return answer == "Revert"


def revert_pair(row, asks=None):
    """Revert the uasset and, when we hold it, the fbx - the pair goes back
    together. The one destructive button in this window, so the one confirm."""
    asks = asks or {}
    run = asks.get("run", vcs.run_p4)
    fbx_opened = ""
    if row.fbx_path:
        fields, failure = vcs.fstat(row.fbx_path, run)
        if not failure and fields.get("action"):
            fbx_opened = row.fbx_path
    confirm = asks.get("confirm", _ask_revert)
    if not confirm([row.client_file] + ([fbx_opened] if fbx_opened else [])):
        return "revert cancelled"
    failure = vcs.revert(row.client_file, run)
    if failure:
        return "revert failed - " + failure
    note = "reverted " + row.record.name
    if fbx_opened:
        failure = vcs.revert(fbx_opened, run)
        note += (", fbx reverted" if not failure
                 else ", fbx NOT reverted - " + failure)
    return note


def export_to(row, asks=None):
    """The whole reverse trip for one checkout: scene -> temp fbx -> p4 ->
    working fbx -> reimport in the editor. Returns the status text.

    Order is the import direction's, for the same reasons: dialogs about
    paths first (a cancel costs nothing), the export to a temp file (a failed
    export must not destroy the previous working file), p4 only after a new
    file exists, the editor last.
    """
    asks = asks or {}
    run = asks.get("run", vcs.run_p4)
    record = row.record
    resolved = window._vcs_target(record, asks)
    if resolved is None:
        return "export cancelled"
    target, _is_new = resolved

    temp = os.path.join(window.temp_folder(),
                        "{0}.export.fbx".format(record.name))
    info = animexport.export_hierarchy(temp, layout=animexport.UNREAL_LAYOUT)

    proceed, note = vcs.prepare_target(
        target, asks.get("others", window._ask_others),
        asks.get("failure", window._ask_failure), run=run)
    if not proceed:
        return "export cancelled - {0} untouched".format(
            os.path.basename(target))
    vcs.place(temp, target)
    if note == "not in depot":
        failure = vcs.add(target, run)
        note = "added" if not failure else "no add - " + failure

    out = os.path.join(window.temp_folder(), "reimport.json")
    payload = uelink.run_script(
        uescripts.reimport_script(out, record.package, target),
        out, project=window.project_choice())

    suffix = vcs.status_suffix(target, window._saved_root(), False, note)
    parts = [animexport.export_line(record.name, info), suffix,
             reimport_line(payload),
             # Same silent no-op as the direct road: an "ok, saved" import
             # that wrote nothing (2026-09-01).
             records.unchanged_warning(payload),
             # Same rule as import: the scene's rate is never changed, a
             # mismatch is said out loud - UE resamples the clip.
             animimport.fps_warning(record.fps, animimport.scene_fps())]
    return "  |  ".join(part for part in parts if part)


# ---------------------------------------------------------------- the tab

def _status(text):
    """The bridge window has ONE status line; this tab talks through it."""
    window._status(text)


def _run(action, busy=None):
    """Same shape as the main window's: a failure lands on the status line,
    not in the Script Editor (trap 20)."""
    if busy:
        _status(busy)
        cmds.refresh()
    try:
        action()
    except uelink.UeBridgeError as error:
        text = str(error).strip()
        _status(text.splitlines()[0] if text else "failed")
        print("[uebridge] {0}".format(error))
    except Exception as error:
        _status("{0}: {1}".format(type(error).__name__, error))
        print(traceback.format_exc())


def _selected_row():
    indices = cmds.textScrollList(_LIST, query=True,
                                  selectIndexedItem=True) or []
    if not indices:
        return None
    index = indices[0] - 1
    if 0 <= index < len(_STATE["rows"]):
        return _STATE["rows"][index]
    return None


def paint_rows(control, indices, rgb=GREEN):
    """Colour the given 0-based rows of a textScrollList green.

    Qt reaches where cmds cannot - textScrollList has no per-row colour
    flag, but underneath it IS a QListWidget. Best-effort by design: a
    headless session, a fake-cmds test, or a control that is not there
    simply skips, and the row text still carries all the information.
    """
    if not indices:
        return
    try:
        from maya import OpenMayaUI as omui
        from shiboken6 import wrapInstance
        from PySide6 import QtGui, QtWidgets
        pointer = omui.MQtUtil.findControl(control)
        if not pointer:
            return
        widget = wrapInstance(int(pointer), QtWidgets.QListWidget)
        brush = QtGui.QBrush(QtGui.QColor(*rgb))
        for index in indices:
            item = widget.item(index)
            if item is not None:
                item.setForeground(brush)
    except Exception:
        pass


def _populate(rows):
    _STATE["rows"] = rows
    cmds.textScrollList(_LIST, edit=True, removeAll=True)
    for row in rows:
        cmds.textScrollList(_LIST, edit=True, append=format_row(row))
    paint_rows(_LIST, [index for index, row in enumerate(rows)
                       if row.modified])
    _status(count_line(len(rows)))


def refresh_tab():
    """Re-read the checkouts into the tab's list. Called by the tab's
    Refresh button and after every action that changes the depot state -
    NEVER on a tab switch (the user's call: opening the tab must not poll
    Perforce). Safe from anywhere - a bridge window without the tab built
    yet just ignores it."""
    if not cmds.textScrollList(_LIST, exists=True):
        return
    rows, failure = load_rows()
    _populate(rows)
    # The same read feeds the import list's tick and green marks.
    window._repopulate(quiet=True)
    if failure:
        _status(failure)


def _export_pressed():
    # With nothing checked out the press degrades to a plain save-as export
    # («если файлов на чекауте нету ... пользователь укажет путь для
    # сохранения fbx»).
    if not _STATE["rows"]:
        path = _ask_save_path()
        if not path:
            _status("export cancelled")
            return
        info = animexport.export_hierarchy(path)
        _status("no checkouts - " + animexport.export_line(
            os.path.basename(path), info))
        return
    row = _selected_row()
    if row is None:
        _status("select a checked-out animation first")
        return
    line = export_to(row)
    refresh_tab()   # the fbx column may have changed
    _status(line)


def _revert_pressed():
    row = _selected_row()
    if row is None:
        _status("select a checked-out animation first")
        return
    line = revert_pair(row)
    refresh_tab()   # the row is usually gone now
    _status(line)


def _ask_save_path():
    kwargs = {"fileMode": 0, "dialogStyle": 2, "caption": "Save FBX as",
              "fileFilter": "FBX Files (*.fbx)"}
    saved = window._saved_root()
    if saved and os.path.isdir(saved):
        kwargs["startingDirectory"] = saved
    picked = cmds.fileDialog2(**kwargs) or []
    return picked[0] if picked else ""


def build_tab(parent):
    """The Export tab, built inside the bridge window's tabLayout.

    No window of its own since 2026-08-21 evening (the user's ask: «хочется
    видеть сразу все наши файлы на чекауте»), and no polling on a tab switch
    since the morning after - Refresh and the file actions are the only p4
    reads, so the header says where the button is and the list simply keeps
    its last rows. Every message goes to the window's one status line.
    """
    form = cmds.formLayout(parent=parent)

    header = cmds.text(
        label="AnimSequence uassets checked out in this workspace"
              " - Refresh re-reads Perforce",
        align="left")
    scroll = cmds.textScrollList(
        _LIST, allowMultiSelection=False, font="fixedWidthFont",
        doubleClickCommand=lambda *_: _run(_export_pressed,
                                           busy="exporting..."))
    refresh_button = cmds.button(
        label="Refresh", width=80,
        command=lambda *_: _run(refresh_tab, busy="asking p4..."))
    revert_button = cmds.button(
        label="Revert", width=80,
        command=lambda *_: _run(_revert_pressed))
    export_button = cmds.button(
        label="EXPORT", height=34, width=140,
        command=lambda *_: _run(_export_pressed, busy="exporting..."))

    cmds.formLayout(
        form, edit=True,
        attachForm=[
            (header, "top", 8), (header, "left", 8), (header, "right", 8),
            (scroll, "left", 8), (scroll, "right", 8),
            (refresh_button, "left", 8), (refresh_button, "bottom", 8),
            (revert_button, "bottom", 8),
            (export_button, "right", 8), (export_button, "bottom", 8),
        ],
        attachControl=[
            (scroll, "top", 8, header),
            (scroll, "bottom", 8, export_button),
            (revert_button, "left", 6, refresh_button),
        ])
    return form
