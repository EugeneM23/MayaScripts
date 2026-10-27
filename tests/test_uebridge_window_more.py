"""maya_uebridge.window - what tests/test_uebridge_window.py leaves: the Unreal cache on disk, the
editor dropdown, a Refresh from the editor and from a folder or a Unity project (the scan, its
progress window, its cache), the dropdown of a file source (recent places, Browse...), the Unreal
export, the name and overwrite dialogs, Save scene, the list's right-button menu, the build's
callbacks, the Export fold, the portrait's name, the drag's attach. On a fake card (controls by
name, an optionMenu with items); the editor and the disk faked or in a temp folder."""

import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import types
import unittest


def _install_fake_maya():
    try:
        import maya.cmds  # noqa: F401
        return
    except ImportError:
        pass
    if "maya.cmds" in sys.modules:
        return
    maya = types.ModuleType("maya")
    cmds = types.ModuleType("maya.cmds")
    mel = types.ModuleType("maya.mel")
    maya.cmds = cmds
    maya.mel = mel
    sys.modules.setdefault("maya", maya)
    sys.modules["maya.cmds"] = cmds
    sys.modules["maya.mel"] = mel


_install_fake_maya()

import maya_hubstyle as hubstyle  # noqa: E402
from maya_uebridge import records, sources, uelink, uescripts, window  # noqa: E402

REAL_TEMP_FOLDER = window.temp_folder


class Card(object):
    """The bridge's controls by name; the dropdown keeps items and a 1-based pick."""

    def __init__(self):
        self.controls = {}
        self.menus = {}
        self.popups = {}
        self.vars = {}
        self.calls = []
        self.serial = 0
        self.dialog = None
        self.prompt = ("OK", "")
        self.confirm = "Cancel"
        self.prefdir = None
        self.progress = []
        self.cancel_at = None
        self.no_progress = False

    # --- plain controls
    def _control(self, kind):
        def call(*args, **kw):
            name = args[0] if args else None
            if kw.get("exists"):
                return name in self.controls
            if (kw.get("query") or kw.get("edit")) and name not in self.controls:
                raise RuntimeError("Object '%s' not found" % name)
            if kw.get("query"):
                item = self.controls[name]
                for flag in ("label", "value", "text", "selectIndexedItem", "manage"):
                    if kw.get(flag):
                        return item.get(flag)
                return None
            if kw.get("edit"):
                item = self.controls[name]
                for key, value in kw.items():
                    if key != "edit":
                        item[key] = value
                return name
            name = name or "%s%d" % (kind, len(self.controls))
            self.controls[name] = dict(kw, kind=kind)
            return name
        return call

    def __getattr__(self, name):
        if name in ("text", "button", "checkBox", "textField", "iconTextRadioButton", "layout",
                    "columnLayout"):
            return self._control(name)

        def other(*args, **kw):
            self.calls.append((name, args, kw))
            return None
        return other

    def textScrollList(self, name, exists=False, query=False, edit=False, removeAll=False,  # noqa: N802
                       append=None, selectIndexedItem=None, **_kw):
        if exists:
            return name in self.controls
        item = self.controls.setdefault(name, {"rows": [], "picked": []})
        if query:
            return list(item["picked"])
        if removeAll:
            item["rows"], item["picked"] = [], []
        if append is not None:
            item["rows"].append(append)
        if selectIndexedItem is not None and not isinstance(selectIndexedItem, bool):
            item["picked"] = sorted(set(item["picked"]) | {selectIndexedItem})

    # --- the dropdown
    def optionMenu(self, name, exists=False, query=False, edit=False, itemListLong=False,  # noqa: N802
                   numberOfItems=False, value=None, select=None, annotation=None, **_kw):
        if exists:
            return name in self.menus
        if name not in self.menus:
            raise RuntimeError("Object '%s' not found" % name)
        menu = self.menus[name]
        if query:
            if itemListLong:
                return [item for item, _label in menu["items"]]
            if numberOfItems:
                return len(menu["items"])
            if value:
                return menu["items"][menu["select"] - 1][1] if menu["select"] else None
            if select:
                return menu["select"]
            return None
        if edit:
            if value is not None:
                labels = [label for _item, label in menu["items"]]
                if value not in labels:
                    raise RuntimeError("no item '%s'" % value)
                menu["select"] = labels.index(value) + 1
            if select is not None:
                menu["select"] = select
            if annotation is not None:
                menu["annotation"] = annotation
        return name

    def menu(self, name, labels=()):
        self.menus[name] = {"items": [], "select": 0}
        for label in labels:
            self.menuItem(parent=name, label=label)

    def labels(self, name):
        return [label for _item, label in self.menus[name]["items"]]

    def chosen(self, name):
        menu = self.menus[name]
        return menu["items"][menu["select"] - 1][1] if menu["select"] else None

    def menuItem(self, parent=None, label=None, **kw):      # noqa: N802
        self.serial += 1
        item = "menuItem%d" % self.serial
        if parent in self.menus:
            self.menus[parent]["items"].append((item, label))
            if not self.menus[parent]["select"]:
                self.menus[parent]["select"] = 1
        else:
            self.popups.setdefault(parent, []).append(dict(kw, label=label))
        return item

    def deleteUI(self, item):                               # noqa: N802
        for menu in self.menus.values():
            names = [i for i, _l in menu["items"]]
            if item in names:
                del menu["items"][names.index(item)]
                menu["select"] = min(menu["select"], len(menu["items"]))

    def popupMenu(self, menu, edit=False, deleteAllItems=False, **_kw):  # noqa: N802
        if deleteAllItems:
            self.popups[menu] = []

    # --- memory, dialogs, files
    def optionVar(self, exists=None, query=None, stringValue=None, intValue=None):  # noqa: N802
        if exists is not None:
            return exists in self.vars
        if query is not None:
            return self.vars[query]
        name, value = stringValue or intValue
        self.vars[name] = value

    def internalVar(self, userPrefDir=False):               # noqa: N802
        return self.prefdir

    def fileDialog2(self, **kw):                            # noqa: N802
        self.calls.append(("fileDialog2", (), kw))
        return self.dialog

    def promptDialog(self, query=False, text=None, **kw):   # noqa: N802
        if query:
            return self.prompt[1]
        self.calls.append(("promptDialog", (), dict(kw, text=text)))
        return self.prompt[0]

    def confirmDialog(self, **kw):                          # noqa: N802
        self.calls.append(("confirmDialog", (), kw))
        return self.confirm

    def progressWindow(self, query=False, edit=False, isCancelled=False, endProgress=False,  # noqa: N802
                       **kw):
        if self.no_progress:
            raise RuntimeError("no UI in batch")
        if query:
            return self.cancel_at is not None and len(self.progress) >= self.cancel_at
        self.progress.append("end" if endProgress else dict(kw))
        return None


#  two editors answer the broadcast; the list comes from the one picked
NODES = [{"project_name": "MarkerLess_02", "node_id": "b"}, {"project_name": "Atone",
                                                             "node_id": "a"}]
PAYLOAD = {"project": "C:/p/Atone/Atone.uproject", "content_dir": "C:/p/Atone/Content",
           "assets": [{"name": "A_Jump", "package": "/Game/Manny/A_Jump", "frames": 45,
                       "fps": 30.0},
                      {"name": "A_Walk", "package": "/Game/Manny/A_Walk", "frames": 30,
                       "fps": 30.0}]}


class Base(unittest.TestCase):

    def setUp(self):
        self.card = Card()
        self.tmp = tempfile.mkdtemp(prefix="uebridge_more_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.patch(window, "cmds", self.card)
        state = dict(window._STATE)
        self.addCleanup(lambda: (window._STATE.clear(), window._STATE.update(state)))
        window._STATE.update({"records": [], "filtered": [], "project": "", "choice": "",
                              "content_dir": "", "source": None, "menu": [], "location": "",
                              "unreal_labels": [], "list_mode": None, "tree_rows": []})
        window._STATE.pop("menu_row", None)
        self.patch(window, "temp_folder", lambda: self.tmp)
        self.said = []
        hubstyle.listen(self._heard)
        self.addCleanup(hubstyle.unlisten, self._heard)

    def _heard(self, control, text, viewport=False):
        if control == window._STATUS:
            self.said.append(text)

    def patch(self, owner, name, value):
        saved = getattr(owner, name)
        setattr(owner, name, value)
        self.addCleanup(setattr, owner, name, saved)

    def card_with_rows(self):
        """The controls a refresh writes: the line, the search, the list, the dropdown."""
        for name in (window._STATUS, window._HEADER, window._DOT):
            self.card.text(name, label="")
        self.card.textField(window._SEARCH, text="")
        self.card.textScrollList(window._LIST, edit=True, removeAll=True)
        self.card.menu(window._PROJECT)


class UnrealCache(Base):

    def test_the_list_survives_a_save_and_a_load(self):
        self.card.prefdir = self.tmp
        found = records.parse_payload(PAYLOAD)
        window.save_cache(found, "C:/p/Atone/Atone.uproject", "Atone", "C:/p/Atone/Content")
        self.assertEqual(window.cache_path(), os.path.join(self.tmp, window.CACHE_NAME))
        self.assertEqual(window.load_cache(), (found, "C:/p/Atone/Atone.uproject", "Atone",
                                               "C:/p/Atone/Content"))

    def test_no_cache_and_a_broken_one_are_empty(self):
        self.card.prefdir = self.tmp
        self.assertEqual(window.load_cache(), ([], "", "", ""))
        with open(window.cache_path(), "w") as handle:
            handle.write("{broken")
        self.assertEqual(window.load_cache(), ([], "", "", ""))

    def test_a_cache_that_cannot_be_written_is_no_failure(self):
        self.card.prefdir = os.path.join(self.tmp, "missing", "deeper")
        window.save_cache([], "", "")
        self.assertFalse(os.path.exists(window.cache_path()))

    def test_the_temp_folder_is_made_once(self):
        self.patch(window.tempfile, "gettempdir", lambda: self.tmp)
        folder = REAL_TEMP_FOLDER()
        self.assertEqual(folder, os.path.join(self.tmp, "maya_uebridge"))
        self.assertTrue(os.path.isdir(folder))
        self.assertEqual(REAL_TEMP_FOLDER(), folder)


class Dropdown(Base):

    def test_the_choice_with_no_dropdown_or_an_empty_one_is_the_remembered(self):
        window._STATE["choice"] = "Atone"
        self.assertEqual(window.project_choice(), "Atone")
        self.card.menu(window._PROJECT)
        self.assertEqual(window.project_choice(), "Atone")
        self.card.menuItem(parent=window._PROJECT, label="MarkerLess_02")
        self.assertEqual(window.project_choice(), "MarkerLess_02")

    def test_a_rebuilt_dropdown_keeps_the_editor_still_up(self):
        self.card.menu(window._PROJECT, ["Atone", "MarkerLess_02"])
        self.card.menus[window._PROJECT]["select"] = 2
        self.assertEqual(window.fill_project_menu(["Atone", "Lugal", "MarkerLess_02"]),
                         "MarkerLess_02")
        self.assertEqual(self.card.labels(window._PROJECT), ["Atone", "Lugal", "MarkerLess_02"])

    def test_an_editor_gone_falls_to_the_first(self):
        self.card.menu(window._PROJECT, ["Atone", "MarkerLess_02"])
        self.card.menus[window._PROJECT]["select"] = 2
        self.assertEqual(window.fill_project_menu(["Atone"]), "Atone")


class RefreshUnreal(Base):

    def setUp(self):
        Base.setUp(self)
        self.card_with_rows()
        self.ran = []
        self.saved_cache = []
        self.patch(uelink, "discover_nodes", lambda: list(NODES))
        self.patch(uescripts, "list_script", lambda out: "LIST " + out)
        self.payload = dict(PAYLOAD)
        self.patch(uelink, "run_script", lambda script, out, project=None: (
            self.ran.append((script, out, project)) or self.payload))
        self.patch(window, "save_cache", lambda *args: self.saved_cache.append(args))

    def test_the_list_from_the_picked_editor_cached_and_said(self):
        window._STATE["choice"] = "MarkerLess_02"
        window._refresh_unreal()
        out = os.path.join(self.tmp, "list.json")
        self.assertEqual(self.ran, [("LIST " + out, out, "MarkerLess_02")])
        self.assertEqual(self.card.labels(window._PROJECT), ["Atone", "MarkerLess_02"])
        self.assertEqual(self.card.chosen(window._PROJECT), "MarkerLess_02")
        self.assertEqual([r.name for r in window._STATE["records"]], ["A_Jump", "A_Walk"])
        self.assertEqual((window._STATE["project"], window._STATE["content_dir"]),
                         ("C:/p/Atone/Atone.uproject", "C:/p/Atone/Content"))
        self.assertEqual(window._STATE["unreal_labels"], ["Atone", "MarkerLess_02"])
        found, project, choice, content = self.saved_cache[0]
        self.assertEqual((len(found), project, choice, content),
                         (2, "C:/p/Atone/Atone.uproject", "MarkerLess_02", "C:/p/Atone/Content"))
        self.assertEqual(self.card.controls[window._HEADER]["label"], "connected")
        self.assertEqual(self.card.controls[window._DOT]["label"], window.DOT_ON)
        self.assertEqual(self.card.controls[window._STATUS]["label"],
                         "2 animations  |  2 editors open, reading MarkerLess_02")
        self.assertEqual(self.card.controls[window._LIST]["rows"],
                         [records.format_row(r) for r in window._STATE["records"]])

    def test_one_editor_says_only_the_count(self):
        self.patch(uelink, "discover_nodes", lambda: NODES[1:])
        window._refresh_unreal()
        self.assertEqual(self.card.controls[window._STATUS]["label"], "2 animations")

    def test_a_registry_still_scanning_waits(self):
        self.payload = {"scanning": True}
        window._refresh_unreal()
        self.assertEqual(self.said[-1],
                         "the asset registry is still scanning - try again in a moment")
        self.assertEqual(window._STATE["records"], [])
        self.assertEqual(self.saved_cache, [])

    def test_a_refresh_with_no_editor_up_keeps_the_picked_editor(self):
        """Fixed 2026-10-27: `_refresh_unreal` stored `node_label(pick_node([], ...))` -
        «no project (? ?)» - as the choice before the editor is asked, so after a Refresh with no
        editor running the next Refresh (both editors up) reads the first by name, not the one
        picked. Should: the picked editor kept until another is picked."""
        window._STATE["choice"] = "MarkerLess_02"
        self.patch(uelink, "discover_nodes", lambda: [])

        def nobody(script, out, project=None):
            raise uelink.UeBridgeError("no editor answered")
        self.patch(uelink, "run_script", nobody)
        with self.assertRaises(uelink.UeBridgeError):
            window._refresh_unreal()
        self.assertEqual(window._STATE["choice"], "MarkerLess_02")

    def test_refresh_asks_the_editor_or_scans_the_files(self):
        asked = []
        self.patch(window, "_refresh_unreal", lambda: asked.append("unreal"))
        self.patch(window, "_refresh_files", lambda: asked.append("files"))
        window._STATE["source"] = "unreal"
        window.refresh()
        window._STATE["source"] = "folder"
        window.refresh()
        self.assertEqual(asked, ["unreal", "files"])

    def test_picking_another_editor_reads_its_list(self):
        refreshed = []
        self.patch(window, "refresh", lambda: refreshed.append(window._STATE["choice"]))
        self.card.menu(window._PROJECT, ["Atone", "MarkerLess_02"])
        self.card.menus[window._PROJECT]["select"] = 2
        window._STATE["source"] = "unreal"
        window._project_changed()
        self.assertEqual(refreshed, ["MarkerLess_02"])
        located = []
        self.patch(window, "_location_changed", lambda: located.append(True))
        window._STATE["source"] = "unity"
        window._project_changed()
        self.assertEqual(located, [True])


class Places(Base):
    """A file source's dropdown: the places browsed to, remembered."""

    def test_recent_reads_only_paths(self):
        self.card.vars[window.RECENT_VAR.format("folder")] = json.dumps(["C:/a", 3, "C:/b"])
        self.assertEqual(window._recent("folder"), ["C:/a", "C:/b"])
        self.card.vars[window.RECENT_VAR.format("folder")] = "[broken"
        self.assertEqual(window._recent("folder"), [])
        self.assertEqual(window._recent("unity"), [])

    def test_remember_puts_the_place_first(self):
        self.card.vars[window.RECENT_VAR.format("folder")] = json.dumps(["C:/a", "C:/b"])
        window._remember("folder", "C:/b")
        self.assertEqual(self.card.vars[window.LOCATION_VAR.format("folder")], "C:/b")
        self.assertEqual(json.loads(self.card.vars[window.RECENT_VAR.format("folder")]),
                         ["C:/b", "C:/a"])
        window._remember("folder", "")
        self.assertEqual(self.card.vars[window.LOCATION_VAR.format("folder")], "")
        self.assertEqual(json.loads(self.card.vars[window.RECENT_VAR.format("folder")]),
                         ["C:/b", "C:/a"])

    def test_the_folder_dropdown_shows_the_chosen_first_then_browse(self):
        self.card.menu(window._PROJECT)
        self.card.vars[window.RECENT_VAR.format("folder")] = json.dumps(["C:/clips/a"])
        window._file_menu("folder", "C:/clips/b")
        self.assertEqual(window._STATE["menu"], ["C:/clips/b", "C:/clips/a", None])
        self.assertEqual(self.card.labels(window._PROJECT)[-1], window.BROWSE)
        self.assertEqual(self.card.menus[window._PROJECT]["select"], 1)
        self.assertEqual(window._menu_value(), "C:/clips/b")

    def test_the_unity_dropdown_lists_the_hub_s_projects(self):
        from maya_uebridge import unityfiles
        self.patch(unityfiles, "hub_projects",
                   lambda: [("Lugal", "C:/w/Lugal", "2022.3", 1)])
        self.patch(unityfiles, "is_open", lambda path: True)
        self.card.menu(window._PROJECT)
        window._file_menu("unity", None)
        self.assertEqual(self.card.labels(window._PROJECT),
                         ["Lugal  (2022.3, open)", window.BROWSE])

    def test_the_dropdown_s_value_with_no_dropdown_is_the_location(self):
        window._STATE["location"] = "C:/clips"
        self.assertEqual(window._menu_value(), "C:/clips")
        window._STATE["location"] = ""
        self.assertIsNone(window._menu_value())
        self.card.menu(window._PROJECT)
        self.assertIsNone(window._menu_value())             # nothing picked

    def test_browse_asks_for_a_folder(self):
        self.card.dialog = ["C:\\clips\\mocap"]
        self.assertEqual(window._browse("folder"), "C:/clips/mocap")
        self.assertEqual(self.card.calls[-1][2]["caption"], "Pick a folder of animations")
        self.card.dialog = None
        self.assertIsNone(window._browse("unity"))
        self.assertEqual(self.card.calls[-1][2]["caption"], "Pick a Unity project folder")


class FileListing(Base):

    def setUp(self):
        Base.setUp(self)
        self.card_with_rows()
        self.clips = os.path.join(self.tmp, "clips").replace("\\", "/")
        os.makedirs(self.clips)
        self.found = [sources.file_record(self.clips + "/run.bvh", "run", "", 10, fps=30.0),
                      sources.file_record(self.clips + "/walk.fbx", "walk", "", 20, fps=30.0)]

    def test_a_file_cache_round_trip_and_none_for_a_place_never_scanned(self):
        window._save_file_cache(self.found, "folder", self.clips)
        self.assertEqual(window._load_file_cache("folder", self.clips), self.found)
        self.assertIsNone(window._load_file_cache("folder", self.clips + "/other"))
        self.assertTrue(window._file_cache_path("folder", self.clips).startswith(self.tmp))

    def test_a_place_shows_its_last_scan_without_scanning(self):
        window._save_file_cache(self.found, "folder", self.clips)
        window._show_location("folder", self.clips)
        self.assertEqual(window._STATE["records"], self.found)
        self.assertEqual(window._STATE["location"], self.clips)
        self.assertEqual(len(self.card.controls[window._LIST]["rows"]), 2)
        self.assertEqual(self.card.controls[window._HEADER]["label"],
                         sources.header_line("folder", self.clips, 2, True))

    def test_a_place_never_scanned_shows_nothing_and_asks_for_refresh(self):
        window._show_location("folder", self.clips)
        self.assertEqual(window._STATE["records"], [])
        self.assertIn("press Refresh to scan it", self.card.controls[window._HEADER]["label"])

    def test_browse_picked_in_the_dropdown_asks_and_remembers(self):
        window._STATE["source"] = "folder"
        window._file_menu("folder", None)                        # only Browse...
        self.card.dialog = [self.clips]
        window._location_changed()
        self.assertEqual(self.card.vars[window.LOCATION_VAR.format("folder")], self.clips)
        self.assertEqual(window._STATE["location"], self.clips)
        self.assertEqual(self.said[-1], "press Refresh to scan {0}".format(self.clips))

    def test_browse_cancelled_changes_nothing(self):
        window._STATE.update(source="folder", location=self.clips)
        window._file_menu("folder", None)
        self.card.menus[window._PROJECT]["select"] = len(self.card.labels(window._PROJECT))
        self.card.dialog = None
        window._location_changed()
        self.assertEqual(self.said[-1], "nothing picked")
        self.assertEqual(self.card.chosen(window._PROJECT), "clips  -  " + records._tail(
            os.path.dirname(os.path.normpath(self.clips)).replace("\\", "/"), 24))

    def test_a_scanned_place_picked_says_nothing_more(self):
        window._save_file_cache(self.found, "folder", self.clips)
        window._STATE["source"] = "folder"
        window._file_menu("folder", self.clips)
        window._location_changed()
        self.assertEqual(window._STATE["records"], self.found)
        self.assertNotIn("press Refresh", " ".join(self.said))

    def scan(self, cancel_after=None):
        calls = []

        def scan(location, source, takes_of, progress=None):
            calls.append((location, source))
            for i in range(1, 31):
                if progress(i, 30, location + "/clip%d.fbx" % i) is False:
                    return self.found[:1]
            return list(self.found)
        from maya_uebridge import sources as src
        self.patch(src, "scan", scan)
        return calls

    def test_a_refresh_scans_the_folder_and_caches_it(self):
        calls = self.scan()
        window._STATE.update(source="folder", location=self.clips)
        window._refresh_files()
        self.assertEqual(calls, [(self.clips, "folder")])
        self.assertEqual(window._STATE["records"], self.found)
        self.assertEqual(window._load_file_cache("folder", self.clips), self.found)
        self.assertEqual(self.card.controls[window._HEADER]["label"],
                         sources.header_line("folder", self.clips, 2, False))
        steps = [p for p in self.card.progress if p != "end"]
        self.assertEqual(steps[0]["title"], "Connect")
        self.assertEqual([p.get("progress") for p in steps[1:]], [33, 66, 100])
        self.assertEqual(self.card.progress[-1], "end")

    def test_a_cancelled_scan_keeps_what_it_found_and_caches_nothing(self):
        self.scan()
        self.card.cancel_at = 2
        window._STATE.update(source="folder", location=self.clips)
        window._refresh_files()
        self.assertEqual(window._STATE["records"], self.found[:1])
        self.assertIsNone(window._load_file_cache("folder", self.clips))
        self.assertEqual(self.said[-1], "scan cancelled - 1 animations so far, not cached")

    def test_no_place_asks_for_one_and_a_cancel_says_so(self):
        calls = self.scan()
        window._STATE["source"] = "folder"
        self.card.dialog = None
        window._refresh_files()
        self.assertEqual((calls, self.said[-1]), ([], "nothing picked"))
        self.card.dialog = [self.clips]
        window._refresh_files()
        self.assertEqual(calls, [(self.clips, "folder")])
        self.assertEqual(self.card.vars[window.LOCATION_VAR.format("folder")], self.clips)

    def test_not_a_folder_and_not_a_unity_project_are_refused(self):
        calls = self.scan()
        window._STATE.update(source="folder", location=self.clips + "/gone")
        window._refresh_files()
        self.assertEqual(self.said[-1], "{0}/gone is not a folder".format(self.clips))
        window._STATE.update(source="unity", location=self.clips)
        window._refresh_files()
        self.assertIn("is not a Unity project", self.said[-1])
        self.assertEqual(calls, [])

    def test_a_scan_with_no_progress_window_still_runs(self):
        self.scan()
        self.card.no_progress = True
        window._STATE.update(source="folder", location=self.clips)
        window._refresh_files()
        self.assertEqual(window._STATE["records"], self.found)


class ScanProgress(Base):

    def test_only_every_tenth_file_asks_and_moves(self):
        progress = window._ScanProgress()
        self.assertTrue(progress.on)
        self.assertTrue(progress.step(3, 100, "C:/x.fbx"))
        self.assertEqual(len(self.card.progress), 1)
        self.assertTrue(progress.step(10, 100, "C:/a/" + "n" * 60 + ".fbx"))
        moved = self.card.progress[-1]
        self.assertEqual(moved["progress"], 10)
        self.assertEqual(moved["status"], "10 / 100  " + "n" * 40)
        progress.close()
        self.assertEqual(self.card.progress[-1], "end")

    def test_a_cancel_is_heard_and_kept(self):
        progress = window._ScanProgress()
        self.card.cancel_at = 1
        self.assertFalse(progress.step(20, 30, "x"))
        self.assertTrue(progress.cancelled)

    def test_no_window_answers_true_and_closes_nothing(self):
        self.card.no_progress = True
        progress = window._ScanProgress()
        self.assertFalse(progress.on)
        self.assertTrue(progress.step(10, 10, "x"))
        progress.close()
        self.assertEqual(self.card.progress, [])

    def test_a_window_gone_mid_scan_is_no_failure(self):
        progress = window._ScanProgress()
        self.card.no_progress = True
        self.assertTrue(progress.step(10, 10, "x"))
        progress.close()


class ExportUnreal(Base):

    def test_the_clip_out_of_the_picked_editor(self):
        asked = []
        self.patch(uescripts, "export_script", lambda out, package, fbx, preview_mesh=False: (
            asked.append((package, fbx, preview_mesh)) or "EXPORT"))
        self.patch(uelink, "run_script", lambda script, out, project=None: (
            asked.append((script, project)) or {"path": "C:/t/A_Jump.fbx", "fps": 60.0}))
        window._STATE["choice"] = "Atone"
        rec = records.AnimRecord("A_Jump", "/Game/A_Jump", "", 45, 1.5, 30.0)
        self.assertEqual(window._export_unreal(rec, mesh=True), ("C:/t/A_Jump.fbx", 60.0))
        self.assertEqual(asked, [("/Game/A_Jump", os.path.join(self.tmp, "A_Jump.fbx"), True),
                                 ("EXPORT", "Atone")])

    def test_a_reply_without_path_or_fps_takes_the_record_s(self):
        self.patch(uescripts, "export_script", lambda *a, **k: "EXPORT")
        self.patch(uelink, "run_script", lambda script, out, project=None: {})
        rec = records.AnimRecord("A_Walk", "/Game/A_Walk", "", 30, 1.0, 24.0)
        self.assertEqual(window._export_unreal(rec),
                         (os.path.join(self.tmp, "A_Walk.fbx"), 24.0))


class Dialogs(Base):

    def test_the_name_asked_or_none(self):
        self.card.prompt = ("OK", "Hero walk")
        self.assertEqual(window._ask_name("Export FBX", "anim", "C:/clips"), "Hero walk")
        asked = self.card.calls[-1][2]
        self.assertEqual((asked["title"], asked["message"], asked["text"]),
                         ("Export FBX", "Name in C:/clips:", "anim"))
        self.card.prompt = ("Cancel", "ignored")
        self.assertIsNone(window._ask_name("Export FBX", "anim", "C:/clips"))

    def test_overwrite_only_on_overwrite(self):
        self.card.confirm = "Overwrite"
        self.assertTrue(window._ask_overwrite("C:/a.fbx"))
        self.assertEqual(self.card.calls[-1][2]["defaultButton"], "Cancel")
        self.card.confirm = "Cancel"
        self.assertFalse(window._ask_overwrite("C:/a.fbx"))

    def test_the_disk_questions(self):
        self.assertTrue(window._isdir(self.tmp))
        self.assertFalse(window._isdir(os.path.join(self.tmp, "nope")))
        self.assertTrue(window._exists(self.tmp))
        self.assertFalse(window._exists(os.path.join(self.tmp, "nope.fbx")))


class SaveScene(Base):

    def test_without_tabs_the_scene_is_renamed_and_saved_in_its_type(self):
        from maya_scenetabs import scope
        self.patch(scope, "tabs_on", lambda *a: False)
        self.assertEqual(window._save_scene("C:/c/take.mb"), "saved the scene as take.mb - in C:/c")
        self.assertEqual(window._save_scene("C:/c/take.ma"), "saved the scene as take.ma - in C:/c")
        files = [c[2] for c in self.card.calls if c[0] == "file"]
        self.assertEqual(files, [{"rename": "C:/c/take.mb"}, {"save": True, "type": "mayaBinary"},
                                 {"rename": "C:/c/take.ma"}, {"save": True, "type": "mayaAscii"}])

    def test_with_tabs_the_active_tab_is_saved_and_a_cancel_is_the_line(self):
        from maya_scenetabs import saving, scope, session
        self.patch(scope, "tabs_on", lambda *a: True)
        saved = []
        self.patch(saving, "save_tab", lambda path=None: saved.append(path) or None)
        self.assertEqual(window._save_scene("C:/c/take.ma"), "saved the scene as take.ma - in C:/c")
        self.assertEqual(saved, ["C:/c/take.ma"])
        self.patch(saving, "save_tab", lambda path=None: session.Cancelled("save cancelled"))
        self.assertEqual(window._save_scene("C:/c/take.ma"), "save cancelled")
        self.assertEqual([c for c in self.card.calls if c[0] == "file"], [])

    def test_save_scene_with_no_folder_opens_maya_s_dialog(self):
        saved = []
        self.patch(window, "_save_scene", lambda path: saved.append(path) or "saved")
        self.card.textScrollList(window._LIST, edit=True, removeAll=True)
        self.card.dialog = ["C:\\c\\take.ma"]
        window.save_scene_selected()
        dialog = [c[2] for c in self.card.calls if c[0] == "fileDialog2"][0]
        self.assertEqual(dialog["fileFilter"], "Maya ASCII (*.ma);;Maya Binary (*.mb)")
        self.assertEqual(saved, ["C:/c/take.ma"])
        self.assertEqual(self.said[-1], "saved")


class ListMenu(Base):

    def test_the_menu_is_filled_for_the_row_and_its_items_press(self):
        from maya_uebridge import foldertree
        window._STATE.update(source="folder", location=self.tmp.replace("\\", "/"),
                             list_mode="folders")
        os.makedirs(os.path.join(self.tmp, "walks"))
        row = foldertree.Row("folder", 0, "walks", "walks", None, 1, False)
        window._STATE["tree_rows"] = [row]
        window._right_pressed(0)
        pressed = []
        self.patch(window, "run_menu", lambda key, r: pressed.append((key, r.path)))
        self.card.popups["menu1"] = [{"label": "stale"}]
        window._fill_list_menu("menu1")
        items = self.card.popups["menu1"]
        self.assertEqual([i["label"] for i in items],
                         ["Show in Explorer", "Export FBX here...", "Save scene here..."])
        self.assertTrue(all(i["enable"] for i in items))
        for item in items:
            item["command"]()
        self.assertEqual(pressed, [(window.MENU_EXPLORER, "walks"), (window.MENU_EXPORT, "walks"),
                                   (window.MENU_SAVE, "walks")])

    def test_no_row_is_one_disabled_line(self):
        self.card.textScrollList(window._LIST, edit=True, removeAll=True)
        window._fill_list_menu("menu1")
        self.assertEqual(self.card.popups["menu1"], [{"label": "no file here", "enable": False}])

    def test_a_menu_press_that_fails_goes_to_the_line(self):
        from maya_uebridge import foldertree
        window._STATE.update(source="folder", location=self.tmp.replace("\\", "/"),
                             list_mode="folders")
        os.makedirs(os.path.join(self.tmp, "walks"))
        window._STATE["tree_rows"] = [foldertree.Row("folder", 0, "walks", "walks", None, 1,
                                                     False)]
        window._right_pressed(0)

        def boom(key, row):
            raise ValueError("Explorer is gone")
        self.patch(window, "run_menu", boom)
        window._fill_list_menu("m")
        with contextlib.redirect_stdout(io.StringIO()):
            self.card.popups["m"][0]["command"]()
        self.assertEqual(self.said[-1], "ValueError: Explorer is gone")


class Fold(Base):

    def test_the_export_fold_opens_closes_and_is_remembered(self):
        self.card.columnLayout(window._EXPORT_ROW, manage=False)
        self.card.button(window._EXPORT_TOGGLE, label=window.export_toggle_label(False))
        window.toggle_export()
        self.assertEqual(self.card.vars[window.EXPORT_OPEN_VAR], 1)
        self.assertTrue(self.card.controls[window._EXPORT_ROW]["manage"])
        self.assertEqual(self.card.controls[window._EXPORT_TOGGLE]["label"], "Export \u25be")
        window.toggle_export()
        self.assertEqual(self.card.vars[window.EXPORT_OPEN_VAR], 0)
        self.assertFalse(self.card.controls[window._EXPORT_ROW]["manage"])
        self.assertEqual(self.card.controls[window._EXPORT_TOGGLE]["label"], "Export \u25b8")

    def test_the_fold_with_the_card_closed_only_remembers(self):
        window.toggle_export()
        self.assertEqual(self.card.vars[window.EXPORT_OPEN_VAR], 1)

    def test_the_busy_words_follow_the_source(self):
        for source, words in (("unreal", "asking the editor..."),
                              ("unity", "scanning the project..."),
                              ("folder", "scanning the folder...")):
            window._STATE["source"] = source
            self.assertEqual(window._refresh_busy(), words)
        self.assertEqual(window._import_busy(), "importing...")
        window._STATE["source"] = "unreal"
        self.assertEqual(window._import_busy(), "exporting from the editor...")


class Portrait(Base):

    def test_the_picked_portrait_s_name(self):
        from maya_scenesetup import window as scene_window
        self.patch(scene_window, "current_choice", lambda: ("Creep", "rig"))
        self.assertEqual(window._model_label(), "Creep")
        self.patch(scene_window, "current_choice", lambda: ("NoSuchModel", "rig"))
        self.assertEqual(window._model_label(), "")

        def broken():
            raise RuntimeError("no Scene Setup")
        self.patch(scene_window, "current_choice", broken)
        self.assertEqual(window._model_label(), "")


class Drag(Base):

    def test_the_list_is_handed_to_the_drag_with_its_rows_and_the_right_button(self):
        from maya_uebridge import listdrag
        handed = []
        self.patch(listdrag, "attach", lambda name, records_of, on_right=None: handed.append(
            (name, records_of, on_right)))
        window._STATE["filtered"] = ["a", None]
        window._attach_drag()
        name, records_of, on_right = handed[0]
        self.assertEqual(name, window._LIST)
        self.assertEqual(records_of(), ["a", None])
        self.assertIs(on_right, window._right_pressed)

    def test_no_drag_where_it_cannot_stand(self):
        from maya_uebridge import listdrag

        def broken(*args, **kw):
            raise ImportError("no Qt")
        self.patch(listdrag, "attach", broken)
        with contextlib.redirect_stdout(io.StringIO()) as printed:
            window._attach_drag()
        self.assertIn("no Qt", printed.getvalue())


class SourceSwitch(Base):

    def setUp(self):
        Base.setUp(self)
        self.card_with_rows()
        self.card.button(window._UASSET, enable=True)

    def test_to_a_folder_shows_its_place_and_turns_the_uasset_export_off(self):
        clips = os.path.join(self.tmp, "clips").replace("\\", "/")
        self.card.vars[window.LOCATION_VAR.format("folder")] = clips
        window._source_changed("folder")
        self.assertEqual(self.card.vars[window.SOURCE_VAR], "folder")
        self.assertFalse(self.card.controls[window._UASSET]["enable"])
        self.assertEqual(window._STATE["location"], clips)
        self.assertEqual(window._STATE["menu"], [clips, None])
        self.assertIn("press Refresh to scan it", self.card.controls[window._HEADER]["label"])

    def test_back_to_unreal_shows_the_cache_s_editor_beside_the_ones_found(self):
        found = records.parse_payload(PAYLOAD)
        self.patch(window, "load_cache", lambda: (found, "C:/p/Atone/Atone.uproject", "Atone",
                                                  "C:/p/Atone/Content"))
        window._STATE["unreal_labels"] = ["MarkerLess_02"]
        window._source_changed("unreal")
        self.assertTrue(self.card.controls[window._UASSET]["enable"])
        self.assertEqual(self.card.labels(window._PROJECT), ["Atone", "MarkerLess_02"])
        self.assertEqual(self.card.chosen(window._PROJECT), "Atone")
        self.assertEqual(window._STATE["records"], found)
        self.assertEqual(self.card.controls[window._HEADER]["label"],
                         window.editor_line(False, 2))


class MoreRoads(Base):
    """The rest of the presses' refusals and fallbacks."""

    def test_an_editor_error_is_its_first_line_and_an_empty_one_failed(self):
        def raise_(text):
            raise uelink.UeBridgeError(text)
        with contextlib.redirect_stdout(io.StringIO()):
            window._run(lambda: raise_("no editor answered\nis Remote Execution on?"))
            self.assertEqual(self.said[-1], "no editor answered")
            window._run(lambda: raise_("   "))
            self.assertEqual(self.said[-1], "failed")
        window._run(lambda: None, busy="asking the editor...")
        self.assertEqual(self.said[-1], "asking the editor...")
        self.assertIn(("refresh", (), {}), self.card.calls)

    def test_nothing_picked_is_said_before_anything(self):
        self.card.textScrollList(window._LIST, edit=True, removeAll=True)
        window.import_selected()
        self.assertEqual(self.said[-1], "select an animation first")

    def test_two_rigs_and_none_selected_refuse_before_the_editor_is_asked(self):
        import maya_rigs
        self.card.textScrollList(window._LIST, edit=True, removeAll=True)
        rec = records.AnimRecord("A_Jump", "/Game/A_Jump", "", 45, 1.5, 30.0)
        window._STATE["filtered"] = [rec]
        self.card.textScrollList(window._LIST, edit=True, selectIndexedItem=1)
        self.patch(window, "auto_kind", lambda: None)
        self.patch(window, "import_mode", lambda: "rig")
        self.patch(maya_rigs, "rigs", lambda: ["Manny_Rig", "Creep_Rig"])
        self.patch(maya_rigs, "current_rig", lambda: (None, "2 rigs in the scene - select one"))
        asked = []
        self.patch(window, "_export_from_editor", lambda *a, **k: asked.append(a))
        window.import_selected()
        self.assertEqual((self.said[-1], asked), ("2 rigs in the scene - select one", []))

    def test_auto_onto_a_skeleton_that_refuses(self):
        from maya_uebridge import autoimport
        self.patch(window, "import_target", lambda: "onto")
        self.patch(autoimport, "explicit_skeleton", lambda: (None, "two skeletons selected"))
        rec = records.AnimRecord("A_Jump", "/Game/A_Jump", "", 45, 1.5, 30.0)
        self.assertEqual(window._auto_press([rec], "skeleton"), "two skeletons selected")

    def test_the_uasset_export_takes_one_unreal_animation(self):
        from maya_uebridge import uassetexport
        rec = records.AnimRecord("A_Jump", "/Game/A_Jump", "", 45, 1.5, 30.0)
        picked = []
        self.patch(window, "_selected_records", lambda: list(picked))
        window._STATE["source"] = "folder"
        window.export_uasset_selected()
        self.assertIn("pick Unreal in Connect", self.said[-1])
        window._STATE["source"] = "unreal"
        picked[:] = [rec, rec]
        window.export_uasset_selected()
        self.assertEqual(self.said[-1], "pick one animation to overwrite - 2 are picked")
        picked[:] = [rec]
        window._STATE.update(content_dir="C:/p/Content", choice="Atone")
        written = []
        self.patch(uassetexport, "export_to_uasset", lambda *args: written.append(args)
                   or "A_Jump written")
        window.export_uasset_selected()
        self.assertEqual(written, [(rec, "C:/p/Content", "Atone", self.tmp)])
        self.assertEqual(self.said[-1], "A_Jump written")

    def test_a_file_s_notes_refuse_by_name(self):
        compressed = sources.file_record("C:/u/w.anim", "Walk", note="compressed")
        unreadable = sources.file_record("C:/u/x.fbx", "X", note="unreadable: bad header")
        curveless = sources.file_record("C:/u/y.fbx", "Y", note="no curves")
        self.assertIn("compressed Unity clip", window.file_refusal(compressed))
        self.assertEqual(window.file_refusal(unreadable), "X: unreadable: bad header")
        self.assertEqual(window.file_refusal(curveless), "Y: no curves")

    def test_the_file_check_is_the_formats_one(self):
        from maya_uebridge import formats
        self.patch(formats, "check", lambda ref: "checked " + ref)
        self.assertEqual(window._clip_check("C:/f/p.fbx|take=2"), "checked C:/f/p.fbx|take=2")

    def test_the_default_name_falls_back_to_the_scene_then_the_pick(self):
        from maya_scenetabs import scope

        def broken(*a, **k):
            raise RuntimeError("no tabs")
        self.patch(scope, "scene_name", broken)
        self.card.textScrollList(window._LIST, edit=True, removeAll=True)
        self.assertEqual(window._default_name(), "animation")
        rec = records.AnimRecord("A_Jump", "/Game/A_Jump", "", 45, 1.5, 30.0)
        window._STATE["filtered"] = [rec]
        self.card.textScrollList(window._LIST, edit=True, selectIndexedItem=1)
        self.assertEqual(window._default_name(), "A_Jump")

    def test_a_dialog_cancelled_writes_nothing(self):
        self.patch(window, "_save_scene", lambda path: self.fail("saved"))
        self.card.textScrollList(window._LIST, edit=True, removeAll=True)
        self.card.dialog = None
        window.save_scene_selected()
        self.assertEqual(self.said[-1], "save cancelled")

    def test_save_scene_without_scene_tabs_at_all(self):
        from maya_scenetabs import scope

        def broken(*a, **k):
            raise ImportError("no tabs")
        self.patch(scope, "tabs_on", broken)
        self.assertEqual(window._save_scene("C:/c/a.ma"), "saved the scene as a.ma - in C:/c")

    def test_explorer_from_the_menu_shows_the_row_s_file(self):
        from maya_uebridge import foldertree
        shown = []
        self.patch(window, "show_in_explorer", lambda path, is_file: shown.append(
            (path, is_file)))
        window._STATE.update(source="folder", location="C:/clips")
        rec = records.AnimRecord("W", "C:/clips/w/W.fbx", "", 24, 1.0, 30.0, "folder",
                                 "C:/clips/w/W.fbx", "", "fbx")
        window.run_menu(window.MENU_EXPLORER, foldertree.Row("anim", 0, "", "W", rec, 1, False))
        window.run_menu(window.MENU_EXPLORER,
                        foldertree.Row("folder", 0, "w", "w", None, 1, False))
        self.assertEqual([s[1] for s in shown], [True, False])

    def test_a_list_row_in_list_mode_is_an_animation_row(self):
        rec = records.AnimRecord("A_Jump", "/Game/A_Jump", "", 45, 1.5, 30.0)
        window._STATE.update(filtered=[None, rec], list_mode="list")
        row = window._row_at(1)
        self.assertEqual((row.kind, row.label, row.record), ("anim", "A_Jump", rec))
        self.assertIsNone(window._row_at(0))
        self.assertIsNone(window._row_at(5))

    def test_a_file_cache_that_cannot_be_written_is_no_failure(self):
        self.patch(window, "temp_folder", lambda: os.path.join(self.tmp, "gone", "deeper"))
        window._save_file_cache([], "folder", "C:/clips")

    def test_a_list_mode_memory_that_cannot_be_read_is_the_list(self):
        def broken(name, default=""):
            raise RuntimeError("no prefs")
        self.patch(window, "_var", broken)
        window._STATE["list_mode"] = None
        self.assertEqual(window.list_mode(), "list")


class Words(Base):
    """`paint_import`: the words follow the card's kind, the picked folder and the picked clips."""

    def setUp(self):
        Base.setUp(self)
        self.card_with_rows()
        for target in window.TARGETS:
            self.card.iconTextRadioButton(window.target_button(target), label="")
        for name in (window._EXPORT_FBX, window._SAVE_SCENE, window._IMPORT):
            self.card.button(name, label="")
        self.patch(window, "import_kind", lambda: "skeleton")
        self.patch(window, "auto_kind", lambda: None)
        self.patch(window, "_model_label", lambda: "Creep")

    def label(self, name):
        return self.card.controls[name]["label"]

    def test_the_kind_s_words_and_one_picked_folder(self):
        from maya_uebridge import foldertree
        window._STATE.update(list_mode="folders", tree_rows=[
            foldertree.Row("folder", 0, "Game/Chars", "Game/Chars", None, 2, True)],
            filtered=[None])
        self.card.textScrollList(window._LIST, edit=True, selectIndexedItem=1)
        window.paint_import()
        self.assertEqual([self.label(window.target_button(t)) for t in window.TARGETS],
                         list(records.target_labels("skeleton")))
        self.assertEqual(self.label(window._EXPORT_FBX), "Export FBX to Chars...")
        self.assertEqual(self.label(window._SAVE_SCENE), "Save scene to Chars...")
        self.assertEqual(self.label(window._IMPORT), "Import animation")

    def test_the_import_button_names_the_picked_clip(self):
        rec = records.AnimRecord("A_Jump", "/Game/A_Jump", "", 45, 1.5, 30.0)
        window._STATE.update(filtered=[rec], list_mode="list")
        self.card.textScrollList(window._LIST, edit=True, selectIndexedItem=1)
        window.paint_import()
        self.assertEqual(self.label(window._IMPORT),
                         records.import_label(["A_Jump"], "skeleton", "onto", "Creep"))
        self.assertEqual(self.label(window._EXPORT_FBX), "Export FBX...")

    def test_words_never_raise(self):
        def broken():
            raise RuntimeError("no Scene Setup")
        self.patch(window, "import_kind", broken)
        window.paint_import()


class BuildCallbacks(unittest.TestCase):
    """Every control build_rows makes reaches its press (built on the recording fake)."""

    def setUp(self):
        from tests.uifakes import FakeUiCmds
        self.fake = FakeUiCmds()
        self.pressed = []
        self.saved = {}
        for name in ("_source_changed", "_attach_drag", "_project_changed", "refresh",
                     "_repopulate", "set_list_mode", "_on_select", "_on_double",
                     "_fill_list_menu", "paint_import", "import_selected", "toggle_export",
                     "export_fbx_selected", "save_scene_selected", "export_uasset_selected"):
            self.saved[name] = getattr(window, name)
            setattr(window, name, lambda *args, n=name, **kw: self.pressed.append(
                (n,) + tuple(args)))
        self.saved["cmds"] = window.cmds
        window.cmds = self.fake
        hubstyle.take_marks()
        window.build_rows()
        hubstyle.take_marks()
        self.pressed[:] = []

    def tearDown(self):
        for name, value in self.saved.items():
            setattr(window, name, value)

    def made(self, kind, name=None, **match):
        for call in self.fake.calls:
            if call[0] != kind or call[2].get("edit") or call[2].get("query"):
                continue
            if name is not None and (not call[1] or call[1][0] != name):
                continue
            if all(call[2].get(k) == v for k, v in match.items()):
                return call[2]
        raise AssertionError("no %s %s" % (kind, name))

    def test_the_source_segments_and_the_dropdown(self):
        for source in sources.SOURCES:
            self.made("iconTextRadioButton", window.source_button(source))["onCommand"]()
        self.made("optionMenu", window._PROJECT)["changeCommand"]()
        self.assertEqual([p[0] for p in self.pressed],
                         ["_source_changed"] * 3 + ["_project_changed"])
        self.assertEqual([p[1] for p in self.pressed[:3]], list(sources.SOURCES))

    def test_refresh_search_and_the_list_modes(self):
        refresh = [c[2] for c in self.fake.calls if c[0] == "button"
                   and str(c[2].get("annotation", "")).startswith("Read the animations again")]
        refresh[0]["command"]()
        self.made("textField", window._SEARCH)["textChangedCommand"]()
        for mode, _words, _note in window.LIST_MODES:
            self.made("iconTextRadioButton", window.list_mode_button(mode))["onCommand"]()
        self.assertEqual(self.pressed, [("refresh",), ("_repopulate",),
                                        ("set_list_mode", "list"),
                                        ("set_list_mode", "folders")])

    def test_the_list_s_click_double_click_and_menu(self):
        made = self.made("textScrollList", window._LIST)
        made["selectCommand"]()
        made["doubleClickCommand"]()
        menu = [c for c in self.fake.calls if c[0] == "popupMenu" and c[2].get("edit")][0]
        menu[2]["postMenuCommand"]()
        self.assertEqual([p[0] for p in self.pressed], ["_on_select", "_on_double",
                                                        "_fill_list_menu"])

    def test_the_import_row_and_the_exports(self):
        for target in window.TARGETS:
            self.made("iconTextRadioButton", window.target_button(target))["onCommand"]()
        for name in (window._IMPORT, window._EXPORT_TOGGLE, window._EXPORT_FBX,
                     window._SAVE_SCENE, window._UASSET):
            self.made("button", name)["command"]()
        self.assertEqual([p[0] for p in self.pressed],
                         ["paint_import", "paint_import", "import_selected", "toggle_export",
                          "export_fbx_selected", "save_scene_selected",
                          "export_uasset_selected"])

    def test_the_build_ends_on_the_remembered_source_and_the_drag(self):
        self.fake.optionvars[window.SOURCE_VAR] = "nonsense"
        hubstyle.take_marks()
        window.build_rows()
        hubstyle.take_marks()
        self.assertIn(("_source_changed", "unreal"), self.pressed)
        self.assertIn(("_attach_drag",), self.pressed)

    def test_the_export_fold_opens_as_remembered(self):
        self.fake.optionvars[window.EXPORT_OPEN_VAR] = 1
        hubstyle.take_marks()
        window.build_rows()
        hubstyle.take_marks()
        rows = [c[2] for c in self.fake.calls if c[0] == "columnLayout" and c[1]
                and c[1][0] == window._EXPORT_ROW]
        self.assertEqual([r["manage"] for r in rows], [False, True])
        toggle = [c[2]["label"] for c in self.fake.calls if c[0] == "button" and c[1]
                  and c[1][0] == window._EXPORT_TOGGLE]
        self.assertEqual(toggle, ["Export \u25b8", "Export \u25be"])


if __name__ == "__main__":
    unittest.main()
