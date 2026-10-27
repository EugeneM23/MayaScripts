"""maya_chat.files: what test_chat_files.py does not reach - a scene and the selection sent (on a
fake maya.cmds), a press's verbs (open, import, Stash, Shared, the Pose Library, a character),
Save as, the main-thread hand-off and a cancel mid-upload. A real Session on the session tests'
fake api and link, the file half of the server in memory; nothing reaches a network."""
import io
import os
import shutil
import sys
import tempfile
import threading
import types
import unittest
import zipfile

import tests  # noqa: F401  (puts SkeldarAnim/ on sys.path)

import maya.cmds  # noqa: F401,E402  (the real one, imported before any fake stands in)
import maya.utils  # noqa: E402
import maya_share  # noqa: E402
import maya_stash  # noqa: E402
import maya_stashstore  # noqa: E402
from maya_scenetabs import scope as tabscope  # noqa: E402
from maya_uebridge import animimport  # noqa: F401,E402  (binds the real cmds first)
from maya_poselib import animapply as poseanim  # noqa: E402
from maya_poselib import apply as poseapply  # noqa: E402
from maya_poselib import store as posestore  # noqa: E402
from maya_poselib import window as libwindow  # noqa: E402
from maya_chat import api as A  # noqa: E402
from maya_chat import files  # noqa: E402
from maya_chat import profile  # noqa: E402
from maya_chat import thumbs  # noqa: E402

from tests.test_chat_files import FileApi  # noqa: E402
from tests.test_chat_session import Base  # noqa: E402

MISSING = object()


class FakeCmds(types.ModuleType):
    """The few maya.cmds calls files.py makes."""

    def __init__(self):
        types.ModuleType.__init__(self, "maya.cmds")
        self.selected = []
        self.unit = "ntsc"
        self.dialog = None
        self.asked = []

    def ls(self, selection=False, long=False):
        return list(self.selected)

    def playbackOptions(self, query=False, minTime=False, maxTime=False):  # noqa: N802
        return 0.0 if minTime else 48.0

    def currentUnit(self, query=False, time=False):  # noqa: N802
        return self.unit

    def fileDialog2(self, **kw):  # noqa: N802
        self.asked.append(kw)
        return self.dialog


class Swaps(object):
    def swap(self, obj, name, value):
        old = getattr(obj, name, MISSING)
        setattr(obj, name, value)

        def back():
            if old is MISSING:
                delattr(obj, name)
            else:
                setattr(obj, name, old)
        self.addCleanup(back)

    def swap_module(self, name, module):
        """One sys.modules entry (never the whole dict), and the package attribute with it."""
        old = sys.modules.get(name, MISSING)
        sys.modules[name] = module
        parent, _dot, leaf = name.rpartition(".")
        holder = sys.modules.get(parent) if parent else None
        old_attr = getattr(holder, leaf, MISSING) if holder is not None else MISSING
        if holder is not None and module is not None:
            setattr(holder, leaf, module)

        def back():
            if old is MISSING:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old
            if holder is not None and old_attr is not MISSING:
                setattr(holder, leaf, old_attr)
        self.addCleanup(back)


class Inline(Swaps, Base):
    def setUp(self):
        Base.setUp(self)
        self.swap(files, "DEFER", lambda fn: fn())
        self.swap(files, "SPAWN", lambda fn: fn())
        self.swap(thumbs, "from_viewport", lambda: None)
        self.src = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.src, True)
        self.cmds = FakeCmds()
        self.swap_module("maya.cmds", self.cmds)

    def ready(self, api=None):
        ses = self.session()
        ses.api = api or FileApi()
        ses.protocol.opened()
        return ses

    def sent(self, ses):
        return [f for f in ses.link.frames() if f.get("type") == "send"]


# ---------------------------------------------------------------------------- sending

class SendScene(Inline):
    def setUp(self):
        Inline.setUp(self)
        self.exported = []

        def export(path, file_type, cmds_=None):
            self.exported.append((os.path.basename(path), file_type, cmds_))
            with open(path, "wb") as out:
                out.write(os.urandom(200))
        self.swap(tabscope, "scene_name", lambda cmds_=None: "C:/shots/Run.ma")
        self.swap(tabscope, "export_scene", export)

    def test_a_copy_of_the_scene_goes_with_its_rate_and_range(self):
        ses = self.ready()
        cid = files.send_scene(ses, "dm", "the shot")
        self.assertEqual(self.exported, [("Run.ma", "mayaAscii", self.cmds)])
        self.assertEqual(ses.api.started[0], ("dm", "Run.ma", "scene", 200,
                                              ses.api.started[0][4], 30.0, [0.0, 48.0]))
        frame = self.sent(ses)[-1]
        self.assertEqual((frame["cid"], frame["text"]), (cid, "the shot"))
        self.assertEqual(frame["file_meta"]["fps"], 30.0)

    def test_a_scene_at_an_odd_unit_goes_without_a_rate(self):
        self.cmds.unit = "nonsense"
        ses = self.ready()
        files.send_scene(ses, "dm")
        self.assertIsNone(ses.api.started[0][5])

    def test_the_viewport_s_picture_goes_with_it(self):
        self.swap(thumbs, "from_viewport", lambda: (b"\xff\xd8\xff-jpeg", None))
        api = FileApi()
        put = []
        api.file_thumb_put = lambda fid, data, sheet=None: put.append((fid, data)) or {"thumb_v": 1}
        ses = self.ready(api)
        held = []

        class Cache(object):
            def put(self, fid, v, data):
                held.append((fid, v, data))
        self.swap(thumbs, "cache", lambda session=None: Cache())
        files.send_scene(ses, "dm")
        self.assertEqual(put, [("%016x" % 1, b"\xff\xd8\xff-jpeg")])
        self.assertEqual(held, [("%016x" % 1, 1, b"\xff\xd8\xff-jpeg")])


class SendSelection(Inline):
    def setUp(self):
        Inline.setUp(self)
        self.exports = []

        def export(nodes, path):
            self.exports.append((list(nodes), os.path.basename(path)))
            with open(path, "wb") as out:
                out.write(b"fbx" * 50)
        self.swap(maya_stash, "_export_fbx", export)

    def test_nothing_selected_is_refused_before_anything(self):
        ses = self.ready()
        with self.assertRaises(A.ChatError) as caught:
            files.send_selection(ses, "dm")
        self.assertEqual(caught.exception.code, "nothing_selected")
        self.assertEqual(self.exports, [])

    def test_the_selection_goes_as_one_fbx_named_as_stash_names_it(self):
        self.cmds.selected = ["|grp|hero_box"]
        ses = self.ready()
        files.send_selection(ses, "dm", "look")
        nodes, name = self.exports[0]
        self.assertEqual(nodes, ["|grp|hero_box"])
        self.assertTrue(name.startswith("hero_box_") and name.endswith(".fbx"))
        self.assertEqual(ses.api.started[0][1:3], (name, "fbx"))
        self.assertEqual(ses.api.started[0][6], [0.0, 48.0])
        self.assertEqual(self.sent(ses)[-1]["text"], "look")

    def test_an_export_that_fails_says_so_and_leaves_nothing(self):
        self.cmds.selected = ["|cube"]

        def broken(nodes, path):
            raise maya_stash.ExportFailed("no FBX plug-in")
        self.swap(maya_stash, "_export_fbx", broken)
        ses = self.ready()
        with self.assertRaises(A.ChatError) as caught:
            files.send_selection(ses, "dm")
        self.assertEqual(caught.exception.code, "export_failed")
        self.assertIn("no FBX plug-in", caught.exception.text)
        uploads = os.path.join(self.dir, "uploads")
        self.assertEqual(os.listdir(uploads) if os.path.isdir(uploads) else [], [])


class Cancel(Inline):
    def setUp(self):
        Inline.setUp(self)
        self.scene = os.path.join(self.src, "Run.ma")
        with open(self.scene, "wb") as out:
            out.write(os.urandom(500))

    def test_a_cancel_mid_upload_stops_it_and_takes_it_back_on_the_server(self):
        api = FileApi()
        holder = {}
        real_part = api.file_part

        def part(fid, n, data):
            if n == 2:
                files.cancel(holder["ses"], holder["cid"])
            return real_part(fid, n, data)
        api.file_part = part
        ses = self.ready(api)
        holder["ses"] = ses
        real_add = ses.add_upload

        def add(chat, cid, text, f, local):
            holder["cid"] = cid
            return real_add(chat, cid, text, f, local)
        ses.add_upload = add
        cid = files.send_path(ses, "dm", self.scene)
        self.assertEqual(api.cancelled, ["%016x" % 1])
        self.assertIsNone(ses._find_pending(cid))
        self.assertEqual(self.sent(ses), [])
        self.assertEqual(os.listdir(os.path.join(self.dir, "uploads")), [])

    def test_a_cancel_of_nothing_is_false(self):
        ses = self.ready()
        self.assertFalse(files.cancel(ses, "no-such"))
        self.assertFalse(files.start(ses, "no-such"))


# ---------------------------------------------------------------------------- receiving

class Receive(Inline):
    def zipped(self, members):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            for name, data in members:
                zf.writestr(name, data)
        return buf.getvalue()

    def test_a_zip_without_the_name_gives_its_first_member(self):
        api = FileApi()
        api.objects["a" * 16] = self.zipped([("other.ma", b"scene bytes")])
        ses = self.ready(api)
        got = []
        files.fetch(ses, {"id": "a" * 16, "name": "Run.ma", "kind": "scene"}, got.append)
        with open(got[0], "rb") as handle:
            self.assertEqual(handle.read(), b"scene bytes")
        self.assertEqual(os.path.basename(got[0]), "Run.ma")

    def test_an_empty_zip_fails_and_says_so(self):
        api = FileApi()
        api.objects["b" * 16] = self.zipped([])
        ses = self.ready(api)
        f = {"id": "b" * 16, "name": "Run.ma", "kind": "scene"}
        files.fetch(ses, f)
        self.assertEqual(ses.state.downloads[f["id"]]["state"], "failed")
        self.assertIn("nothing", ses.state.downloads[f["id"]]["error"])

    def test_a_second_press_while_loading_waits_for_the_same_download(self):
        ses = self.ready()
        later = []
        self.swap(files, "SPAWN", later.append)
        f = {"id": "c" * 16, "name": "Run.ma", "kind": "scene"}
        got = []
        self.assertFalse(files.fetch(ses, f, got.append))
        self.assertFalse(files.fetch(ses, f, got.append))
        self.assertEqual(len(later), 1, "one thread a file")
        self.assertEqual(len(ses.state.downloads[f["id"]]["then"]), 2)

    def test_a_follow_up_that_raises_does_not_stop_the_others(self):
        api = FileApi()
        api.objects["d" * 16] = self.zipped([("Run.ma", b"x")])
        ses = self.ready(api)
        later = []
        self.swap(files, "SPAWN", later.append)
        f = {"id": "d" * 16, "name": "Run.ma", "kind": "scene"}
        got = []
        files.fetch(ses, f, lambda path: 1 / 0)
        files.fetch(ses, f, got.append)
        import traceback
        self.swap(traceback, "print_exc", lambda *a, **k: None)
        later[0]()
        self.assertEqual(len(got), 1)


# ---------------------------------------------------------------------------- what a press does

class Verbs(Swaps, unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.calls = []
        self.f = {"id": "f" * 16, "name": "Run.ma", "kind": "scene"}

    def test_record_of_is_what_shared_asks(self):
        self.assertEqual(files.record_of({"name": "a.fbx", "kind": "fbx"}, "Bob"),
                         {"name": "a.fbx", "kind": "fbx", "from": "Bob"})
        self.assertEqual(files.record_of({}), {"name": "", "kind": "scene", "from": ""})

    def test_open_import_stash_and_share_go_to_their_tools(self):
        self.swap(maya_share, "open_file", lambda path, rec: self.calls.append(
            ("open", path, rec)) or "opened")
        self.swap(maya_share, "import_file", lambda path, rec: self.calls.append(
            ("import", path, rec)) or "imported")
        self.swap(maya_share, "send_file", lambda path=None, name=None: self.calls.append(
            ("share", path, name)) or "shared")
        self.swap(maya_stash, "stash_file", lambda path=None, name=None: self.calls.append(
            ("stash", path, name)) or "stashed")
        self.assertEqual(files.open_file("C:/d/x.ma", self.f, "Bob"), "opened")
        self.assertEqual(files.import_file("C:/d/x.ma", self.f, "Bob"), "imported")
        self.assertEqual(files.to_stash("C:/d/x.ma", self.f), "stashed")
        self.assertEqual(files.to_share("C:/d/x.ma", {}), "shared")
        rec = {"name": "Run.ma", "kind": "scene", "from": "Bob"}
        self.assertEqual(self.calls, [("open", "C:/d/x.ma", rec), ("import", "C:/d/x.ma", rec),
                                      ("stash", "C:/d/x.ma", "Run.ma"),
                                      ("share", "C:/d/x.ma", "x.ma")])

    def test_save_as_copies_where_asked_and_nothing_when_cancelled(self):
        src = os.path.join(self.dir, "Run.ma")
        with open(src, "wb") as out:
            out.write(b"scene")
        dest = os.path.join(self.dir, "kept.ma")
        self.assertIn("kept.ma", files.save_to(src, self.f, dest))
        with open(dest, "rb") as handle:
            self.assertEqual(handle.read(), b"scene")
        cmds = FakeCmds()
        self.swap_module("maya.cmds", cmds)
        cmds.dialog = None
        self.assertEqual(files.save_to(src, self.f), "Nothing saved.")
        other = os.path.join(self.dir, "asked.ma")
        cmds.dialog = [other]
        self.assertIn("asked.ma", files.save_to(src, self.f))
        self.assertTrue(os.path.isfile(other))
        self.assertEqual(cmds.asked[0]["fileMode"], 0)

    def test_a_picture_opens_in_our_viewer(self):
        seen = []
        self.swap(files, "VIEWER", None)
        self.swap(profile, "view_picture", lambda path, scale=1.0: seen.append((path, scale)))
        self.assertEqual(files.show_picture("C:/d/ref.png", {}, 1.5), u"ref.png открыта")
        self.assertEqual(seen, [("C:/d/ref.png", 1.5)])
        self.swap(files, "VIEWER", seen.append)
        files.show_picture("C:/d/b.png")
        self.assertEqual(seen[-1], "C:/d/b.png")

    def test_size_text(self):
        self.assertEqual(files.size_text(0), "0 KB")
        self.assertEqual(files.size_text(100), "1 KB")
        self.assertEqual(files.size_text(5 * 1024 ** 3), "5.00 GB")


class FakeLive(object):
    def __init__(self, broken=False):
        self.refreshed = 0
        self.broken = broken

    def refresh(self):
        if self.broken:
            raise RuntimeError("the window is gone")
        self.refreshed += 1


class Library(Swaps, unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)
        root = self.root

        class Scene(object):
            def library(self):
                return root
        self.swap(libwindow, "Scene", Scene)
        self.live = FakeLive()
        self.swap(libwindow, "live", lambda: self.live)
        self.card = os.path.join(tempfile.mkdtemp(), "Fist.pose")
        self.addCleanup(shutil.rmtree, os.path.dirname(self.card), True)
        os.makedirs(self.card)
        with open(os.path.join(self.card, "pose.json"), "w") as out:
            out.write('{"format": "skeldar.pose"}')

    def test_a_card_goes_into_from_chat_and_a_second_takes_a_free_name(self):
        line = files.to_library(self.card)
        self.assertEqual(line, u"Fist - в библиотеке поз (From Chat)")
        self.assertTrue(os.path.isfile(os.path.join(self.root, "From Chat", "Fist.pose",
                                                    "pose.json")))
        self.assertEqual(self.live.refreshed, 1)
        files.to_library(self.card)
        self.assertTrue(os.path.isdir(os.path.join(self.root, "From Chat", "Fist 2.pose")))

    def test_into_a_folder_of_the_tree_or_the_library_itself(self):
        self.assertIn("(Fights)", files.to_library(self.card + "/", "Fights"))
        self.assertTrue(os.path.isdir(os.path.join(self.root, "Fights", "Fist.pose")))
        self.assertIn("(Library)", files.to_library(self.card, ""))
        self.assertTrue(os.path.isdir(os.path.join(self.root, "Fist.pose")))

    def test_a_library_window_that_cannot_refresh_still_takes_the_card(self):
        self.live = FakeLive(broken=True)
        import traceback
        self.swap(traceback, "print_exc", lambda *a, **k: None)
        self.assertIn("Fist", files.to_library(self.card))


class ApplyCard(Swaps, unittest.TestCase):
    def setUp(self):
        self.calls = []
        calls = self.calls

        class Scene(object):
            def drop_floor(self, path, point, mirror):
                calls.append(("floor", path, point, mirror))
                return ("ok", "Manny added on the floor")

            def _paste(self, press, path, options):
                calls.append(("paste", path, options))
                return press({"format": "skeldar.anim"}, ["frames"], "progress")
        self.swap(libwindow, "Scene", Scene)
        self.swap(poseanim, "apply_onto", lambda header, frames, root, mirror=False,
                  options=None, progress=None: calls.append(
                      ("anim", header["format"], frames, root, mirror, options, progress))
                  or ("done", "Walk onto Manny"))
        self.swap(poseapply, "apply_onto", lambda data, root, mirror=False: calls.append(
            ("pose", data, root, mirror)) or "Fist onto Manny")
        self.swap(posestore, "read", lambda path: {"read": path})

    def test_onto_the_floor_a_new_character(self):
        line = files.apply_card("C:/c/Walk.anim", {"kind": "floor", "point": (1, 0, 2)})
        self.assertEqual(line, "Manny added on the floor")
        self.assertEqual(self.calls, [("floor", "C:/c/Walk.anim", (1, 0, 2), False)])

    def test_an_animation_onto_a_character_the_whole_card(self):
        line = files.apply_card("C:/c/Walk.anim", {"kind": "character", "root": "|root"})
        self.assertEqual(line, "Walk onto Manny")
        self.assertEqual(self.calls, [("paste", "C:/c/Walk.anim", None),
                                      ("anim", "skeldar.anim", ["frames"], "|root", False, None,
                                       "progress")])

    def test_a_pose_onto_a_character(self):
        self.assertEqual(files.apply_card("C:/c/Fist.pose", {"kind": "character",
                                                            "root": "|root"}),
                         "Fist onto Manny")
        self.assertEqual(self.calls, [("pose", {"read": "C:/c/Fist.pose"}, "|root", False)])

    def test_an_empty_answer_is_an_empty_line(self):
        self.swap(poseapply, "apply_onto", lambda data, root, mirror=False: None)
        self.assertEqual(files.apply_card("C:/c/Fist.pose", {"kind": "character",
                                                            "root": "|r"}), "")


# ---------------------------------------------------------------------------- threads

class HandOff(Swaps, unittest.TestCase):
    def test_defer_goes_through_maya_and_without_it_runs_at_once(self):
        self.swap(files, "DEFER", None)
        queued, ran = [], []
        self.swap(maya.utils, "executeDeferred", queued.append)
        files.defer(lambda: ran.append(1))
        self.assertEqual((len(queued), ran), (1, []))
        self.swap_module("maya.utils", None)             # `import maya.utils` raises
        files.defer(lambda: ran.append(2))
        self.assertEqual(ran, [2])

    def test_spawn_runs_on_a_daemon_thread(self):
        self.swap(files, "SPAWN", None)
        done = threading.Event()
        thread = files.spawn(done.set)
        thread.join(5)
        self.assertTrue(done.is_set())
        self.assertTrue(thread.daemon)
        self.assertEqual(thread.name, "skeldar-chat-file")


if __name__ == "__main__":
    unittest.main()
