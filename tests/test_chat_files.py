"""maya_chat files (2026-10-22): records.file, the api's file calls, uploads and downloads."""
import io
import json
import os
import shutil
import tempfile
import unittest
import urllib.error
import zipfile

from maya_chat import api as a
from maya_chat import files
from maya_chat import records as r

from tests.test_chat_session import Base, ME


FILE = {"id": "f" * 16, "name": "Run.ma", "kind": "scene", "bytes": 300, "zip": 120,
        "fps": 30, "range": [0, 48], "expired": False}


class Records(unittest.TestCase):
    def test_a_file_is_read(self):
        f = r.file(FILE)
        self.assertEqual(f["name"], "Run.ma")
        self.assertEqual(f["range"], [0.0, 48.0])
        self.assertEqual(f["fps"], 30.0)

    def test_a_bad_file_is_dropped_and_the_message_kept(self):
        self.assertIsNone(r.file({"id": "x", "name": "a.ma", "kind": "exe"}))
        self.assertIsNone(r.file("nope"))
        m = r.message({"id": "m", "chat": "c", "seq": 1, "from_id": "u", "text": "",
                       "at": 1, "file": {"name": 3}})
        self.assertIsNone(m["file"])
        m = r.message({"id": "m", "chat": "c", "seq": 1, "from_id": "u", "text": "",
                       "at": 1, "file": FILE})
        self.assertEqual(m["file"]["id"], "f" * 16)


class Answer(io.BytesIO):
    def __init__(self, data, headers=None):
        io.BytesIO.__init__(self, data)
        self.headers = headers or {}
        self.status = 200

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class ApiCalls(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.calls = []

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def opener(self, answer):
        def call(req, timeout=None):
            self.calls.append((req.get_method(), req.full_url, req.data, timeout))
            if isinstance(answer, Exception):
                raise answer
            return answer
        return call

    def test_start_names_the_file(self):
        api = a.Api("https://x.dev", "tok", self.opener(Answer(b'{"id": "abc", "part_size": 4, "parts": 2}')))
        got = api.file_start("c", "Run.ma", "scene", 300, 7, 30, [0, 48])
        self.assertEqual(got["parts"], 2)
        method, url, data, _t = self.calls[0]
        self.assertEqual((method, url), ("POST", "https://x.dev/v1/files"))
        self.assertEqual(json.loads(data), {"chat": "c", "name": "Run.ma", "kind": "scene",
                                            "bytes": 300, "zip": 7, "fps": 30, "range": [0, 48]})

    def test_a_part_is_put_as_bytes(self):
        api = a.Api("https://x.dev", "tok", self.opener(Answer(b'{"ok": true}')))
        api.file_part("abc", 2, b"1234")
        method, url, data, timeout = self.calls[0]
        self.assertEqual((method, url, data), ("PUT", "https://x.dev/v1/files/abc/parts/2", b"1234"))
        self.assertEqual(timeout, a.PART_TIMEOUT)

    def test_a_download_lands_whole(self):
        api = a.Api("https://x.dev", "tok", self.opener(Answer(b"x" * 3000000, {"content-length": "3000000"})))
        seen = []
        path = os.path.join(self.dir, "z.zip")
        self.assertEqual(api.file_download("abc", path, lambda d, t: seen.append((d, t))), 3000000)
        self.assertEqual(os.path.getsize(path), 3000000)
        self.assertEqual(seen[-1], (3000000, 3000000))
        self.assertFalse(os.path.exists(path + ".part"))

    def test_an_expired_file_is_refused_and_nothing_left(self):
        error = urllib.error.HTTPError("u", 410, "gone", {}, io.BytesIO(b'{"error": "expired", "text": "This file has expired"}'))
        api = a.Api("https://x.dev", "tok", self.opener(error))
        path = os.path.join(self.dir, "z.zip")
        with self.assertRaises(a.ChatError) as cm:
            api.file_download("abc", path)
        self.assertEqual(cm.exception.code, "expired")
        self.assertFalse(os.listdir(self.dir))

    def test_a_short_download_is_refused(self):
        api = a.Api("https://x.dev", "tok", self.opener(Answer(b"x" * 10, {"content-length": "20"})))
        path = os.path.join(self.dir, "z.zip")
        with self.assertRaises(a.ChatError):
            api.file_download("abc", path)
        self.assertFalse(os.listdir(self.dir))


class FileApi(object):
    """The file half of the server, in memory."""

    def __init__(self, fail_part=None):
        self.objects = {}
        self.parts = {}
        self.fail_part = fail_part
        self.cancelled = []
        self.started = []

    def file_start(self, chat, name, kind, size, zip_size, fps=None, frame_range=None):
        fid = "%016x" % (len(self.started) + 1)
        self.started.append((chat, name, kind, size, zip_size, fps, frame_range))
        self.parts[fid] = {}
        return {"id": fid, "part_size": 64, "parts": max(1, -(-zip_size // 64))}

    def file_part(self, fid, n, data):
        if self.fail_part == n:
            self.fail_part = None
            raise a.ChatError("offline", "The chat server did not answer (cut)")
        self.parts[fid][n] = bytes(data)
        return {"ok": True}

    def file_complete(self, fid):
        self.objects[fid] = b"".join(self.parts[fid][n] for n in sorted(self.parts[fid]))
        return {"id": fid, "state": "ready"}

    def file_cancel(self, fid):
        self.cancelled.append(fid)
        return {"ok": True}

    def file_download(self, fid, path, progress=None):
        data = self.objects.get(fid)
        if data is None:
            raise a.ChatError("expired", "This file has expired", 410)
        with open(path, "wb") as out:
            out.write(data)
        if progress:
            progress(len(data), len(data))
        return len(data)


class Inline(Base):
    def setUp(self):
        Base.setUp(self)
        files.DEFER = lambda fn: fn()
        files.SPAWN = lambda fn: fn()
        self.src = tempfile.mkdtemp()
        self.scene = os.path.join(self.src, "Run.ma")
        with open(self.scene, "wb") as out:
            out.write(os.urandom(500))     # does not compress: several parts

    def tearDown(self):
        files.DEFER = files.SPAWN = None
        shutil.rmtree(self.src, ignore_errors=True)
        Base.tearDown(self)

    def ready(self, fake=None):
        ses = self.session()
        ses.api = fake or FileApi()
        ses.protocol.opened()
        return ses


class Upload(Inline):
    def test_a_file_goes_up_in_parts_then_out_as_a_message(self):
        ses = self.ready()
        cid = files.send_path(ses, "dm", self.scene, "the run")
        api = ses.api
        fid = "%016x" % 1
        self.assertEqual(api.started[0][:4], ("dm", "Run.ma", "scene", 500))
        self.assertGreater(len(api.parts[fid]), 1)
        with zipfile.ZipFile(io.BytesIO(api.objects[fid])) as zf:
            self.assertEqual(zf.namelist(), ["Run.ma"])
            with open(self.scene, "rb") as handle:
                self.assertEqual(zf.read("Run.ma"), handle.read())
        frame = [f for f in ses.link.frames() if f.get("type") == "send"][-1]
        self.assertEqual((frame["cid"], frame["file"], frame["text"]), (cid, fid, "the run"))
        self.assertEqual(frame["file_meta"]["name"], "Run.ma")
        p = ses._find_pending(cid)
        self.assertIsNone(p["upload"])
        self.assertEqual(p["file"]["id"], fid)
        # the sent copy is the sender's own file, kept; the upload folder is gone
        self.assertTrue(files.local_path(ses, p["file"]))
        self.assertFalse(os.listdir(os.path.join(self.dir, "uploads")))
        self.assertIn("upload", self.told)

    def test_the_outbox_draws_the_card_after_a_restart(self):
        ses = self.ready()
        cid = files.send_path(ses, "dm", self.scene)
        ses.stop()
        again = self.session()
        p = again._find_pending(cid)
        self.assertEqual(p["file"]["name"], "Run.ma")

    def test_a_part_that_fails_is_a_failed_message_and_retry_sends_it(self):
        ses = self.ready(FileApi(fail_part=2))
        cid = files.send_path(ses, "dm", self.scene)
        p = ses._find_pending(cid)
        self.assertEqual(p["state"], "failed")
        self.assertIn("did not answer", p["error"])
        self.assertFalse([f for f in ses.link.frames() if f.get("type") == "send"])
        self.assertTrue(ses.retry(cid))
        self.assertIsNone(p["upload"])
        self.assertTrue([f for f in ses.link.frames() if f.get("type") == "send"])

    def test_discarding_a_failed_upload_cancels_it_on_the_server(self):
        ses = self.ready(FileApi(fail_part=2))
        cid = files.send_path(ses, "dm", self.scene)
        self.assertTrue(ses.discard(cid))
        self.assertIsNone(ses._find_pending(cid))
        self.assertEqual(ses.api.cancelled, ["%016x" % 1])

    def test_only_scenes_and_fbx(self):
        ses = self.ready()
        other = os.path.join(self.src, "a.txt")
        open(other, "w").close()
        with self.assertRaises(a.ChatError):
            files.send_path(ses, "dm", other)
        with self.assertRaises(a.ChatError):
            files.send_path(ses, "dm", os.path.join(self.src, "gone.ma"))


class Download(Inline):
    def test_a_file_lands_unzipped_and_then_runs(self):
        ses = self.ready()
        files.send_path(ses, "dm", self.scene)
        fid = "%016x" % 1
        f = dict(FILE, id=fid)
        shutil.rmtree(os.path.join(self.dir, "files"))      # as on the receiver's machine
        got = []
        self.assertFalse(files.fetch(ses, f, got.append))
        self.assertEqual(len(got), 1)
        with open(got[0], "rb") as a_, open(self.scene, "rb") as b_:
            self.assertEqual(a_.read(), b_.read())
        self.assertEqual(ses.state.downloads[fid]["state"], "done")
        # the second press uses what is on disk
        self.assertTrue(files.fetch(ses, f, got.append))
        self.assertEqual(got[0], got[1])

    def test_an_expired_file_says_so(self):
        ses = self.ready()
        with self.assertRaises(a.ChatError):
            files.fetch(ses, dict(FILE, expired=True))
        f = dict(FILE, id="e" * 16)
        files.fetch(ses, f)
        self.assertEqual(ses.state.downloads[f["id"]]["state"], "failed")
        self.assertIn("expired", ses.state.downloads[f["id"]]["error"])


if __name__ == "__main__":
    unittest.main()


class Cards(Inline):
    """A Pose Library card (its folder) sent and received (2026-10-22)."""

    def make_card(self):
        card = os.path.join(self.src, "Fist.pose")
        os.makedirs(card)
        with open(os.path.join(card, "pose.json"), "w") as out:
            out.write('{"format": "skeldar.pose"}')
        with open(os.path.join(card, "thumbnail.jpg"), "wb") as out:
            out.write(os.urandom(300))
        return card

    def test_the_kinds(self):
        self.assertEqual(files.card_kind("C:/lib/Fist.pose/"), "pose")
        self.assertEqual(files.card_kind("Walk.anim"), "anim")
        self.assertIsNone(files.card_kind("Run.ma"))
        self.assertTrue(files.is_card({"kind": "anim"}))
        self.assertEqual(r.file(dict(FILE, kind="pose", name="Fist.pose"))["kind"], "pose")

    def test_a_card_goes_as_its_folder_and_comes_back_whole(self):
        ses = self.ready()
        card = self.make_card()
        files.send_card(ses, "dm", card)
        fid = "%016x" % 1
        api = ses.api
        self.assertEqual(api.started[0][1:3], ("Fist.pose", "pose"))
        with zipfile.ZipFile(io.BytesIO(api.objects[fid])) as zf:
            self.assertEqual(sorted(zf.namelist()), ["Fist.pose/pose.json", "Fist.pose/thumbnail.jpg"])
        shutil.rmtree(os.path.join(self.dir, "files"))
        got = []
        files.fetch(ses, {"id": fid, "name": "Fist.pose", "kind": "pose"}, got.append)
        self.assertEqual(sorted(os.listdir(got[0])), ["pose.json", "thumbnail.jpg"])
        with open(os.path.join(card, "thumbnail.jpg"), "rb") as a_, \
                open(os.path.join(got[0], "thumbnail.jpg"), "rb") as b_:
            self.assertEqual(a_.read(), b_.read())

    def test_nothing_climbs_out_of_a_card_zip(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("Fist.pose/pose.json", "{}")
            zf.writestr("Fist.pose/../../evil.txt", "x")
            zf.writestr("other/evil.txt", "x")
        folder = tempfile.mkdtemp(dir=self.src)
        with zipfile.ZipFile(io.BytesIO(buf.getvalue())) as zf:
            path = files._unzip_card(zf, folder, "Fist.pose")
        self.assertEqual(os.listdir(path), ["pose.json"])
        self.assertEqual(sorted(os.listdir(folder)), ["Fist.pose"])
        self.assertFalse(os.path.exists(os.path.join(self.src, "evil.txt")))

    def test_a_folder_that_is_no_card_is_refused(self):
        ses = self.ready()
        with self.assertRaises(a.ChatError):
            files.send_card(ses, "dm", self.src)
