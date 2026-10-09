"""maya_stash: the Stash section - stashing, opening, importing, saving,
deleting, the panel, the registration.

On a recording `cmds` (the `uifakes` pattern of test_share), in a temp
folder that stands for the stash. The scene calls that would open a dialog
are answered in advance; the FBX import is replaced by a recorder.

Spec: docs/superpowers/specs/2026-10-09-stash-design.md
"""

import os
import shutil
import sys
import tempfile
import time
import unittest

import maya_hub
import maya_hubicons
import maya_stash as stash
import maya_stashstore as store
from maya_scenesetup import colour, opener

from tests.uifakes import FakeUiCmds


class _Cmds(FakeUiCmds):
    """FakeUiCmds plus the scene and file calls the section makes."""

    def __init__(self, app_dir):
        FakeUiCmds.__init__(self)
        self.app_dir = app_dir
        self.scene_name = ""
        self.fields = {}
        self.picked = []
        self.list_up = True
        self.dialog = None
        self.batch = True
        self.answer = "Delete"
        self.confirms = []
        self.file_calls = []
        self.scripts = []
        self.removed = []
        self.imported = []
        self.modified = True

    # ------------------------------------------------------- scene and files
    def internalVar(self, **kwargs):
        return self.app_dir + "/"

    def file(self, *args, **kwargs):
        self.file_calls.append((args, kwargs))
        if kwargs.get("query") or kwargs.get("q"):
            if kwargs.get("sceneName"):
                return self.scene_name
            if kwargs.get("modified"):
                return False
            return None
        if "modified" in kwargs:
            self.modified = kwargs["modified"]
            return None
        if kwargs.get("exportAll"):
            with open(args[0], "wb") as out:
                out.write(b"//Maya ASCII scene " * 100)
            return args[0]
        if kwargs.get("i"):
            return list(self.imported)
        return None

    def about(self, **kwargs):
        if kwargs.get("batch"):
            return self.batch
        return None

    def scriptNode(self, name, **kwargs):
        return "playbackOptions -min 5 -max 45 -ast 0 -aet 50 "

    def objExists(self, name):
        return name == "sceneConfigurationScriptNode" or name in self.scripts

    def ls(self, *args, **kwargs):
        if kwargs.get("type") == "script" or "script" in (
                kwargs.get("type") or []):
            return list(self.scripts)
        return []

    def lockNode(self, *args, **kwargs):
        return None

    def delete(self, *args, **kwargs):
        self.removed.extend(args)
        return None

    def fileDialog2(self, **kwargs):
        return [self.dialog] if self.dialog else None

    def confirmDialog(self, **kwargs):
        self.confirms.append(kwargs)
        return self.answer

    # ---------------------------------------------------------- the panel
    def textField(self, *args, **kwargs):
        name = args[0] if args else None
        if kwargs.get("exists"):
            return name in self.fields
        if kwargs.get("query") or kwargs.get("q"):
            return self.fields.get(name, "")
        if kwargs.get("edit") or kwargs.get("e"):
            if "text" in kwargs:
                self.fields[name] = kwargs["text"]
            return None
        self.fields[name] = kwargs.get("text", "")
        return FakeUiCmds.__getattr__(self, "textField")(*args, **kwargs)

    def textScrollList(self, *args, **kwargs):
        if kwargs.get("exists"):
            return self.list_up
        if kwargs.get("query") or kwargs.get("q"):
            if kwargs.get("selectIndexedItem"):
                return list(self.picked)
            if kwargs.get("numberOfItems"):
                return len(stash.state()["rows"])
            return None
        if kwargs.get("edit") or kwargs.get("e"):
            if kwargs.get("selectIndexedItem"):
                self.picked = list(kwargs["selectIndexedItem"])
            return None
        self.calls.append(("textScrollList", args, kwargs))
        return args[0] if args else None


class _Base(unittest.TestCase):

    def setUp(self):
        if hasattr(sys, "_skeldar_stash"):
            del sys._skeldar_stash
        self.dir = tempfile.mkdtemp(prefix="stash_")
        self.fake = _Cmds(self.dir)
        self.saved = (stash.cmds, opener.cmds, colour.cmds)
        stash.cmds = self.fake
        opener.cmds = self.fake
        colour.cmds = self.fake
        self.statuses = []
        self.saved_status = stash._status
        stash._status = lambda message, **kw: (
            self.statuses.append(message) or message)
        self.opened = []
        self.imports = []
        self.saved_open_file = opener.fbximport.open_file
        self.saved_import_clip = None
        opener.fbximport.open_file = lambda path: self.opened.append(path)

    def tearDown(self):
        stash.cmds, opener.cmds, colour.cmds = self.saved
        stash._status = self.saved_status
        opener.fbximport.open_file = self.saved_open_file
        if self.saved_import_clip is not None:
            from maya_uebridge import animimport
            animimport.import_clip = self.saved_import_clip
            animimport.existing_namespaces = self.saved_namespaces
        if hasattr(sys, "_skeldar_stash"):
            del sys._skeldar_stash
        shutil.rmtree(self.dir, ignore_errors=True)

    def folder(self):
        return os.path.join(self.dir, store.FOLDER)

    def stashed(self, name, data=b"x" * 100):
        os.makedirs(self.folder(), exist_ok=True)
        path = os.path.join(self.folder(), name)
        with open(path, "wb") as out:
            out.write(data)
        return path

    def source(self, name, data=b"FBX" * 500):
        path = os.path.join(self.dir, "src", name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as out:
            out.write(data)
        return path

    def fake_import_clip(self, result):
        from maya_uebridge import animimport
        self.saved_import_clip = animimport.import_clip
        self.saved_namespaces = animimport.existing_namespaces

        def fake(path, namespace=None, merge=None, set_timeline=None):
            self.imports.append((path, namespace, merge, set_timeline))
            return result
        animimport.import_clip = fake
        animimport.existing_namespaces = lambda: []


class Stashing(_Base):

    def test_a_scene_is_copied_in_under_its_stem_and_the_time(self):
        self.fake.scene_name = "C:/work/shot.ma"
        message = stash.stash_scene()
        names = os.listdir(self.folder())
        self.assertEqual(len(names), 1)
        self.assertTrue(names[0].startswith("shot_") and names[0].endswith(
            ".ma"), names)
        self.assertIn("Stashed", message)
        self.assertIn("open scene is untouched", message)

    def test_the_scene_is_exported_as_a_copy_only(self):
        self.fake.scene_name = "C:/work/shot.ma"
        stash.stash_scene()
        exports = [(a, k) for a, k in self.fake.file_calls
                   if k.get("exportAll")]
        self.assertEqual(len(exports), 1)
        self.assertEqual(exports[0][1]["type"], "mayaAscii")
        self.assertFalse(any(k.get("save") or k.get("rename")
                             for _a, k in self.fake.file_calls))

    def test_a_second_press_never_overwrites_the_first(self):
        self.fake.scene_name = "C:/work/shot.ma"
        stash.stash_scene()
        stash.stash_scene()
        names = sorted(os.listdir(self.folder()))
        self.assertEqual(len(names), 2)
        self.assertTrue(any(n.endswith(" (2).ma") for n in names), names)

    def test_a_typed_name_is_used_and_the_field_cleared(self):
        self.fake.scene_name = "C:/work/shot.ma"
        self.fake.fields[stash.NAME_FIELD] = "Rig draft"
        stash.stash_scene()
        self.assertEqual(os.listdir(self.folder()), ["Rig draft.ma"])
        self.assertEqual(self.fake.fields[stash.NAME_FIELD], "")

    def test_an_untitled_scene_is_called_untitled(self):
        stash.stash_scene()
        (name,) = os.listdir(self.folder())
        self.assertTrue(name.startswith("untitled_"), name)

    def test_a_binary_scene_keeps_its_type(self):
        self.fake.scene_name = "C:/work/rig.mb"
        stash.stash_scene()
        exports = [k for _a, k in self.fake.file_calls if k.get("exportAll")]
        self.assertEqual(exports[0]["type"], "mayaBinary")
        (name,) = os.listdir(self.folder())
        self.assertTrue(name.endswith(".mb"), name)

    def test_a_file_is_copied_in(self):
        src = self.source("clip.fbx")
        message = stash.stash_file(src)
        self.assertEqual(os.listdir(self.folder()), ["clip.fbx"])
        self.assertIn("Stashed clip.fbx", message)
        with open(src, "rb") as a, open(os.path.join(self.folder(),
                                                     "clip.fbx"), "rb") as b:
            self.assertEqual(a.read(), b.read())

    def test_a_file_stashed_twice_gets_two(self):
        src = self.source("clip.fbx")
        stash.stash_file(src)
        stash.stash_file(src)
        self.assertEqual(sorted(os.listdir(self.folder())),
                         ["clip (2).fbx", "clip.fbx"])

    def test_other_files_are_refused(self):
        src = self.source("notes.txt", b"hi")
        self.assertIn("Only .ma, .mb and .fbx", stash.stash_file(src))
        self.assertFalse(os.path.isdir(self.folder()))

    def test_a_missing_file_is_refused(self):
        message = stash.stash_file(os.path.join(self.dir, "gone.fbx"))
        self.assertIn("No file at", message)

    def test_no_pick_stashes_nothing(self):
        self.assertEqual(stash.stash_file(""), "Nothing stashed.")

    def test_the_file_dialog_pick_is_used(self):
        self.fake.dialog = self.source("pick.mb", b"//Maya")
        stash.stash_file()
        self.assertEqual(os.listdir(self.folder()), ["pick.mb"])


class Listing(_Base):

    def test_the_list_shows_the_folder_newest_first(self):
        old = self.stashed("old.ma")
        new = self.stashed("new.fbx")
        os.utime(old, (1000, 1000))
        os.utime(new, (2000, 2000))
        stash.refresh()
        self.assertEqual(stash.state()["rows"], ["new.fbx", "old.ma"])

    def test_a_missing_folder_lists_nothing(self):
        stash.refresh()
        self.assertEqual(stash.state()["rows"], [])

    def test_a_leftover_and_a_stranger_are_not_listed(self):
        self.stashed("kept.ma")
        self.stashed("notes.txt")
        self.stashed("half.ma.part")
        stash.refresh()
        self.assertEqual(stash.state()["rows"], ["kept.ma"])

    def test_the_picked_rows_are_kept_across_a_refresh(self):
        self.stashed("a.ma")
        self.stashed("b.ma")
        stash.refresh()
        self.fake.picked = [2]
        stash.refresh()
        self.assertEqual(stash.selected_names(), [stash.state()["rows"][1]])


class Acting(_Base):

    def setUp(self):
        _Base.setUp(self)
        self.scene_path = self.stashed("draft.ma", b"//Maya ASCII")
        self.fbx_path = self.stashed("clip.fbx", b"FBX" * 100)
        stash.refresh()

    def pick(self, *names):
        rows = stash.state()["rows"]
        self.fake.picked = [rows.index(n) + 1 for n in names]

    def test_open_nothing_picked(self):
        self.assertIn("Pick a file", stash.open_selected())

    def test_open_several_picked(self):
        self.pick("draft.ma", "clip.fbx")
        self.assertIn("Pick one file to open - 2 are picked",
                      stash.open_selected())

    def test_a_scene_opens_with_its_script_nodes_off(self):
        self.pick("draft.ma")
        message = stash.open_selected()
        opens = [k for _a, k in self.fake.file_calls if k.get("open")]
        self.assertEqual(len(opens), 1)
        self.assertIs(opens[0]["executeScriptNodes"], False)
        self.assertIs(opens[0]["prompt"], False)
        self.assertIn("Ctrl+S writes the draft back", message)

    def test_an_fbx_opens_through_the_import_guard(self):
        self.pick("clip.fbx")
        message = stash.open_selected()
        self.assertEqual(self.opened, [self.fbx_path])
        self.assertIn("as a new scene", message)

    def test_a_cancelled_save_changes_opens_nothing(self):
        self.pick("draft.ma")
        self.fake.batch = False
        saved = opener.save_changes
        opener.save_changes = lambda: False
        try:
            message = stash.open_selected()
        finally:
            opener.save_changes = saved
        self.assertIn("cancelled", message)
        self.assertFalse([k for _a, k in self.fake.file_calls if k.get("open")])

    def test_a_scene_import_takes_its_script_nodes_out(self):
        self.pick("draft.ma")
        self.fake.imported = ["persp", "vaccine"]
        self.fake.scripts = ["vaccine"]
        message = stash.import_selected()
        imports = [a for a, k in self.fake.file_calls if k.get("i")]
        self.assertEqual(len(imports), 1)
        self.assertIn("vaccine", self.fake.removed)
        self.assertIn("Imported draft.ma from the stash", message)
        self.assertIn("script node removed", message)

    def test_an_fbx_import_is_its_own_skeleton_in_a_namespace(self):
        self.fake_import_clip({"nodes": ["a"], "joints": 3, "curves": 9})
        self.pick("clip.fbx")
        message = stash.import_selected()
        self.assertEqual(len(self.imports), 1)
        path, namespace, merge, timeline = self.imports[0]
        self.assertEqual(path, self.fbx_path)
        self.assertEqual(namespace, "clip")
        self.assertIs(merge, False)
        self.assertIs(timeline, True)
        self.assertIn("Imported clip.fbx as clip - 3 joints, 9 curves",
                      message)

    def test_an_fbx_that_brings_nothing_says_so(self):
        self.fake_import_clip({"nodes": []})
        self.pick("clip.fbx")
        self.assertIn("brought nothing", stash.import_selected())

    def test_save_to_copies_the_stashed_file_out(self):
        dest = os.path.join(self.dir, "out", "clip.fbx")
        os.makedirs(os.path.dirname(dest))
        self.fake.dialog = dest
        self.pick("clip.fbx")
        self.assertIn("Saved clip.fbx", stash.save_selected())
        with open(dest, "rb") as handle:
            self.assertEqual(handle.read(), b"FBX" * 100)

    def test_a_file_gone_meanwhile_is_said_and_the_list_refreshes(self):
        self.pick("clip.fbx")
        os.remove(self.fbx_path)
        self.assertIn("no longer in the stash", stash.open_selected())
        self.assertNotIn("clip.fbx", stash.state()["rows"])

    def test_show_folder_opens_it_and_makes_it(self):
        opened = []
        saved = getattr(os, "startfile", None)
        os.startfile = lambda path: opened.append(path)
        try:
            shutil.rmtree(self.folder())
            stash.show_folder()
        finally:
            if saved is None:
                del os.startfile
            else:
                os.startfile = saved
        self.assertEqual(opened, [self.folder()])
        self.assertTrue(os.path.isdir(self.folder()))


class Deleting(_Base):

    def setUp(self):
        _Base.setUp(self)
        self.one = self.stashed("one.ma")
        self.two = self.stashed("two.fbx")
        stash.refresh()

    def pick(self, *names):
        rows = stash.state()["rows"]
        self.fake.picked = [rows.index(n) + 1 for n in names]

    def test_delete_removes_the_picked_files_from_disk(self):
        self.pick("one.ma", "two.fbx")
        message = stash.delete_selected()
        self.assertFalse(os.path.exists(self.one))
        self.assertFalse(os.path.exists(self.two))
        self.assertIn("Deleted 2 files from the stash", message)

    def test_the_confirm_names_the_files_outside_batch(self):
        self.fake.batch = False
        self.pick("one.ma")
        stash.delete_selected()
        self.assertEqual(len(self.fake.confirms), 1)
        self.assertIn("one.ma", self.fake.confirms[0]["message"])
        self.assertFalse(os.path.exists(self.one))

    def test_cancel_changes_nothing(self):
        self.fake.batch = False
        self.fake.answer = "Cancel"
        self.pick("one.ma")
        message = stash.delete_selected()
        self.assertTrue(os.path.exists(self.one))
        self.assertIn("Delete cancelled", message)

    def test_the_scene_open_in_this_maya_is_refused_and_kept(self):
        self.fake.scene_name = self.one
        self.pick("one.ma", "two.fbx")
        message = stash.delete_selected()
        self.assertTrue(os.path.exists(self.one))
        self.assertFalse(os.path.exists(self.two))
        self.assertIn("scene open in this Maya", message)
        self.assertIn("Deleted 1 file from the stash", message)

    def test_only_the_open_scene_picked_deletes_nothing(self):
        self.fake.scene_name = self.one
        self.pick("one.ma")
        message = stash.delete_selected()
        self.assertTrue(os.path.exists(self.one))
        self.assertIn("nothing deleted", message)

    def test_nothing_picked(self):
        self.assertIn("Pick files", stash.delete_selected())


class Panel(_Base):

    def test_the_named_controls_are_built(self):
        stash.build_panel()
        names = []
        for call in self.fake.calls:
            for arg in call[1]:
                if isinstance(arg, str):
                    names.append(arg)
        for name in (stash.NAME_FIELD, stash.LIST, stash.STATUS):
            self.assertIn(name, names)

    def test_it_lists_the_folder_once_built(self):
        self.stashed("kept.ma")
        stash.build_panel()
        self.assertEqual(stash.state()["rows"], ["kept.ma"])

    def test_show_window_asks_the_hub_for_the_section(self):
        import maya_hub as hub_now   # the module the section will import
        asked = []
        saved = hub_now.show
        hub_now.show = lambda key=None: asked.append(key)
        try:
            stash.show_window()
        finally:
            hub_now.show = saved
        self.assertEqual(asked, ["stash"])


class Registered(unittest.TestCase):

    def test_a_scene_section_after_shared(self):
        keys = [s.key for s in maya_hub.SECTIONS]
        self.assertEqual(keys.index("stash"), keys.index("shared") + 1)
        section = maya_hub.section("stash")
        self.assertEqual(section.group, "scene")
        self.assertEqual(section.module, "maya_stash")
        self.assertEqual(section.builder, "build_panel")

    def test_its_icon_exists(self):
        self.assertIn("archive", maya_hubicons.ICONS)
        self.assertEqual(maya_hub.section("stash").icon, "archive")

    def test_the_payload_rows(self):
        import install
        for name in ("maya_stashstore.py", "maya_stash.py"):
            self.assertIn(name, install.payload())

    def test_the_hotkey_row(self):
        import maya_hotkeys
        rows = [row[0] for row in maya_hotkeys.COMMANDS]
        self.assertIn("window.stash", rows)

    def test_the_opener_keeps_its_message(self):
        self.assertEqual(
            opener.CANCELLED, "Open scene cancelled - nothing changed.")


if __name__ == "__main__":
    unittest.main()
