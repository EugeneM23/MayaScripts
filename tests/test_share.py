"""maya_share: the Shared section - sending, receiving, history, the panel.

On a recording `cmds`, a fake network that keeps uploads by address, and
threads and deferred calls that run at once.

Spec: docs/superpowers/specs/2026-09-30-shared-files-design.md
"""

import os
import shutil
import sys
import tempfile
import time
import unittest
import zipfile

import maya_hub
import maya_hubstyle
import maya_share as share
import maya_sharenet as net
import maya_sharerecords as records

from tests.uifakes import FakeUiCmds


class _Cmds(FakeUiCmds):
    """FakeUiCmds plus the scene calls the section makes."""

    def __init__(self, app_dir):
        FakeUiCmds.__init__(self)
        self.app_dir = app_dir
        self.scene_name = ""
        self.files = []
        self.comment = ""
        self.dialog = None
        self.messages = []

    def internalVar(self, **kwargs):
        return self.app_dir + "/"

    def file(self, *args, **kwargs):
        self.files.append((args, kwargs))
        if kwargs.get("query") or kwargs.get("q"):
            if kwargs.get("sceneName"):
                return self.scene_name
            if kwargs.get("modified"):
                return False
            return None
        if kwargs.get("exportAll"):
            with open(args[0], "wb") as out:
                out.write(b"//Maya ASCII scene " * 1000)
            return args[0]
        return None

    def about(self, **kwargs):
        if kwargs.get("version"):
            return "2027"
        if kwargs.get("batch"):
            return True
        return None

    def playbackOptions(self, **kwargs):
        if kwargs.get("minTime"):
            return 0.0
        if kwargs.get("maxTime"):
            return 60.0
        return None

    def currentUnit(self, **kwargs):
        return "ntsc"

    def ls(self, *args, **kwargs):
        return []

    def fileDialog2(self, **kwargs):
        return [self.dialog] if self.dialog else None

    def inViewMessage(self, **kwargs):
        self.messages.append(kwargs.get("assistMessage"))

    def textField(self, *args, **kwargs):
        if kwargs.get("query") or kwargs.get("q"):
            return self.comment
        return FakeUiCmds.__getattr__(self, "textField")(*args, **kwargs)


class _Sub(object):
    made = []

    def __init__(self, on_event, since="12h", on_state=None, **kwargs):
        self.on_event, self.since, self.on_state = on_event, since, on_state
        self.started = self.stopped = False
        _Sub.made.append(self)

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True


class _Net(object):
    """Records every publish; keeps uploads by address and serves them."""
    ShareError = net.ShareError
    Expired = net.Expired
    Cancelled = net.Cancelled
    Subscriber = _Sub

    def __init__(self):
        self.published = []
        self.store = {}
        self.fail = None

    def publish(self, text, topic=None, base=None):
        self.published.append(records.parse(text))
        return "m{0}".format(len(self.published))

    def upload(self, path, progress=None, url=None, keep="72h"):
        if self.fail is not None:
            raise self.fail
        with open(path, "rb") as handle:
            data = handle.read()
        url = "https://litter.catbox.moe/f{0}.zip".format(len(self.store))
        self.store[url] = data
        if progress is not None:
            progress(len(data), len(data))
        return url

    def download(self, url, path, progress=None):
        if url not in self.store:
            raise net.Expired("gone")
        with open(path, "wb") as out:
            out.write(self.store[url])
        if progress is not None:
            progress(len(self.store[url]), len(self.store[url]))
        return len(self.store[url])


class _Base(unittest.TestCase):

    def setUp(self):
        if hasattr(sys, "_skeldar_share"):
            del sys._skeldar_share
        self.dir = tempfile.mkdtemp(prefix="share_")
        self.fake = _Cmds(self.dir)
        self.net = _Net()
        self.saved = (share.cmds, share.net, share._defer, share._spawn)
        share.cmds = self.fake
        share.net = self.net
        share._defer = lambda fn, *args: fn(*args)
        share._spawn = lambda fn: fn()
        _Sub.made = []
        self.statuses = []
        self.saved_status = share._status
        share._status = lambda message, **kw: (
            self.statuses.append(message) or message)

    def tearDown(self):
        share.cmds, share.net, share._defer, share._spawn = self.saved
        share._status = self.saved_status
        if hasattr(sys, "_skeldar_share"):
            del sys._skeldar_share
        shutil.rmtree(self.dir, ignore_errors=True)

    def _source(self, name="clip.fbx", data=b"FBX" * 5000):
        path = os.path.join(self.dir, "src", name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as out:
            out.write(data)
        return path

    def _colleague(self, name="Longsword.fbx", data=b"FBX" * 4000,
                   sent=None, machine="theirs"):
        """A colleague's ready record whose zip is in the fake store."""
        rid = records.new_id()
        archive = os.path.join(self.dir, rid + ".zip")
        with zipfile.ZipFile(archive, "w") as z:
            z.writestr(name, data)
        url = "https://litter.catbox.moe/{0}.zip".format(rid[:6])
        with open(archive, "rb") as handle:
            self.net.store[url] = handle.read()
        rec = records.make_record("sending", rid, "Oleg", machine, name,
                                  len(data), sent or int(time.time()))
        return records.with_state(rec, "ready", url=url,
                                  zip=len(self.net.store[url]))


class Sending(_Base):

    def test_send_file_publishes_sending_then_ready(self):
        path = self._source()
        message = share.send_file(path, comment="look at the root")
        self.assertIn("clip.fbx", message)
        states = [r["state"] for r in self.net.published]
        self.assertEqual(states, ["sending", "ready"])
        ready = self.net.published[-1]
        self.assertEqual(ready["comment"], "look at the root")
        self.assertEqual(ready["kind"], "fbx")
        self.assertEqual(ready["machine"], share.machine_id())
        entry = share.state()["entries"][ready["id"]]
        self.assertEqual(entry["record"]["state"], "ready")
        self.assertTrue(os.path.isfile(entry["local"]))
        self.assertTrue(entry["local"].startswith(share.share_dir()))
        with open(entry["local"], "rb") as a, open(path, "rb") as b:
            self.assertEqual(a.read(), b.read())
        with zipfile.ZipFile(__import__("io").BytesIO(
                self.net.store[ready["url"]])) as z:
            self.assertEqual(z.namelist(), ["clip.fbx"])

    def test_a_failed_upload_publishes_failed(self):
        self.net.fail = net.ShareError("could not reach litterbox: refused")
        share.send_file(self._source())
        self.assertEqual([r["state"] for r in self.net.published],
                         ["sending", "failed"])
        rid = self.net.published[0]["id"]
        self.assertEqual(share.state()["entries"][rid]["record"]["state"],
                         "failed")
        self.assertTrue(any("nothing was sent" in s for s in self.statuses),
                        self.statuses)

    def test_send_file_refuses_other_files(self):
        message = share.send_file(self._source("notes.txt"))
        self.assertIn("nothing sent", message)
        self.assertEqual(self.net.published, [])

    def test_send_file_with_no_pick_sends_nothing(self):
        message = share.send_file()
        self.assertIn("Nothing sent", message)
        self.assertEqual(self.net.published, [])

    def test_send_scene_exports_all_and_leaves_the_scene_alone(self):
        self.fake.scene_name = "C:/work/Orc_attack.mb"
        share.send_scene(comment="v2")
        exports = [(a, k) for a, k in self.fake.files if k.get("exportAll")]
        self.assertEqual(len(exports), 1)
        args, kwargs = exports[0]
        self.assertTrue(args[0].endswith("Orc_attack.mb"))
        self.assertEqual(kwargs["type"], "mayaBinary")
        self.assertIs(kwargs["preserveReferences"], False)
        self.assertTrue(kwargs["force"])
        renames = [k for a, k in self.fake.files
                   if k.get("rename") or k.get("save")]
        self.assertEqual(renames, [])
        ready = self.net.published[-1]
        self.assertEqual(ready["name"], "Orc_attack.mb")
        self.assertEqual(ready["fps"], 30.0)
        self.assertEqual(ready["range"], [0.0, 60.0])


class Receiving(_Base):

    def test_a_colleagues_file_is_fetched_and_announced(self):
        rec = self._colleague()
        self.assertTrue(share.receive(rec))
        entry = share.state()["entries"][rec["id"]]
        self.assertTrue(os.path.isfile(entry["local"]))
        self.assertTrue(entry["local"].endswith("Longsword.fbx"))
        with open(entry["local"], "rb") as handle:
            self.assertEqual(handle.read(), b"FBX" * 4000)
        self.assertEqual(self.fake.messages, ["Oleg sent Longsword.fbx"])

    def test_history_is_fetched_but_not_announced(self):
        rec = self._colleague(sent=int(time.time()) - 3600)
        share.receive(rec)
        self.assertTrue(share.state()["entries"][rec["id"]]["local"])
        self.assertEqual(self.fake.messages, [])

    def test_a_replay_changes_nothing(self):
        rec = self._colleague()
        share.receive(rec)
        self.assertFalse(share.receive(dict(rec)))
        self.assertFalse(share.receive(records.with_state(rec, "sending")))

    def test_our_own_record_is_never_fetched(self):
        rec = self._colleague(machine=share.machine_id())
        share.receive(rec)
        self.assertEqual(share.state()["entries"][rec["id"]]["local"], "")
        self.assertEqual(self.fake.messages, [])

    def test_an_expired_file_is_not_fetched(self):
        rec = self._colleague(sent=int(time.time()) - records.LIFETIME - 60)
        share.receive(rec)
        self.assertEqual(share.state()["entries"][rec["id"]]["local"], "")

    def test_a_download_that_fails_says_so_and_can_retry(self):
        rec = self._colleague()
        stored = self.net.store.pop(rec["url"])
        share.receive(rec)
        transfer = share.state()["transfers"][rec["id"]]
        self.assertTrue(transfer["error"])
        self.net.store[rec["url"]] = stored
        self.assertIn("downloading", share.open_entry(rec["id"]))
        self.assertTrue(share.state()["entries"][rec["id"]]["local"])

    def test_a_zip_holding_something_else_is_refused(self):
        rec = self._colleague()
        archive = os.path.join(self.dir, "bad.zip")
        with zipfile.ZipFile(archive, "w") as z:
            z.writestr("../evil.ma", b"x")
        with open(archive, "rb") as handle:
            self.net.store[rec["url"]] = handle.read()
        share.receive(rec)
        self.assertEqual(share.state()["entries"][rec["id"]]["local"], "")
        self.assertIn("archive", share.state()["transfers"][rec["id"]]["error"])

    def test_the_event_handler_takes_ours_only(self):
        rec = self._colleague()
        share._on_event({"event": "message", "id": "abc",
                         "message": records.encode(rec)})
        share._on_event({"event": "message", "id": "abd",
                         "message": "somebody's own notification"})
        self.assertIn(rec["id"], share.state()["entries"])
        self.assertEqual(share.state()["since"], "abd")
        self.assertEqual(len(share.state()["entries"]), 1)


class History(_Base):

    def test_survives_a_fresh_state(self):
        rec = self._colleague()
        share.receive(rec)
        share.state()["since"] = "m42"
        share.save_history()
        del sys._skeldar_share
        share.load_history()
        entry = share.state()["entries"][rec["id"]]
        self.assertEqual(entry["record"], rec)
        self.assertTrue(entry["local"])
        self.assertEqual(share.state()["since"], "m42")

    def test_a_local_file_deleted_meanwhile_is_forgotten(self):
        rec = self._colleague()
        share.receive(rec)
        share.save_history()
        os.remove(share.state()["entries"][rec["id"]]["local"])
        del sys._skeldar_share
        share.load_history()
        self.assertEqual(share.state()["entries"][rec["id"]]["local"], "")


class Actions(_Base):

    def test_open_waits_for_a_file_still_being_sent(self):
        rec = self._colleague()
        sending = records.with_state(rec, "sending")
        del sending["url"], sending["zip"]
        share.receive(sending)
        self.assertIn("still being sent", share.open_entry(rec["id"]))

    def test_open_of_nothing_picked(self):
        self.assertIn("Pick a file", share.open_selected())

    def test_save_to_copies_the_local_file(self):
        rec = self._colleague()
        share.receive(rec)
        dest = os.path.join(self.dir, "out", "Longsword.fbx")
        os.makedirs(os.path.dirname(dest))
        self.fake.dialog = dest
        self.assertIn("Saved", share.save_entry(rec["id"]))
        with open(dest, "rb") as handle:
            self.assertEqual(handle.read(), b"FBX" * 4000)

    def test_open_of_a_scene_runs_no_script_node(self):
        rec = self._colleague(name="Orc.ma", data=b"//Maya ASCII")
        share.receive(rec)
        cleaned = []
        saved = share._clean
        share._clean = lambda nodes, every_script: cleaned.append(
            every_script) or ""
        try:
            share.open_entry(rec["id"])
        finally:
            share._clean = saved
        opens = [k for a, k in self.fake.files if k.get("open")]
        self.assertEqual(len(opens), 1)
        self.assertIs(opens[0]["executeScriptNodes"], False)
        self.assertIs(opens[0]["prompt"], False)
        self.assertEqual(cleaned, [False])


class Listening(_Base):

    def test_listen_replaces_the_subscriber(self):
        first = share.listen()
        second = share.listen()
        self.assertTrue(first.started and first.stopped)
        self.assertTrue(second.started and not second.stopped)
        self.assertIs(share.state()["subscriber"], second)
        self.assertEqual(first.since, "12h")

    def test_listen_resumes_from_the_last_id(self):
        share.state()["since"] = "m7"
        self.assertEqual(share.listen().since, "m7")


class Panel(_Base):

    def setUp(self):
        _Base.setUp(self)
        maya_hubstyle.take_marks()
        self.listened = []
        self.saved_listen = share.listen
        share.listen = lambda: self.listened.append(True)
        share.build_panel()
        self.marks = maya_hubstyle.take_marks()

    def tearDown(self):
        share.listen = self.saved_listen
        _Base.tearDown(self)

    def test_the_named_controls(self):
        for name in (share.NAME_FIELD, share.COMMENT_FIELD, share.LIST,
                     share.STATUS, share.SUBTITLE):
            self.assertIn(name, self.fake.children, name)

    def test_one_primary_action(self):
        primary = [m for m in self.marks if m.role == "primary"]
        self.assertEqual(len(primary), 1)
        roles = set(m.role for m in self.marks)
        self.assertIn("subtitle", roles)
        self.assertIn("status", roles)

    def test_it_starts_listening(self):
        self.assertEqual(self.listened, [True])

    def test_show_window_asks_the_hub(self):
        asked = []
        saved = maya_hub.show
        maya_hub.show = lambda key=None: asked.append(key)
        try:
            share.show_window()
        finally:
            maya_hub.show = saved
        self.assertEqual(asked, ["shared"])


class Registered(unittest.TestCase):
    """The section in the hub, its icon, its payload rows, its hotkey row."""

    def test_a_scene_section_after_connections(self):
        keys = [s.key for s in maya_hub.SECTIONS]
        self.assertEqual(keys.index("shared"), keys.index("connections") + 1)
        section = maya_hub.section("shared")
        self.assertEqual(section.group, "scene")
        self.assertEqual(section.module, "maya_share")

    def test_its_icon(self):
        import maya_hubicons
        self.assertIn(maya_hub.section("shared").icon, maya_hubicons.ICONS)

    def test_the_payload_rows(self):
        import install
        for name in ("maya_sharerecords.py", "maya_sharenet.py",
                     "maya_share.py"):
            self.assertIn(name, install.payload())

    def test_the_hotkey_row(self):
        import maya_hotkeys
        rows = [row[0] for row in maya_hotkeys.COMMANDS]
        self.assertIn("window.shared", rows)


if __name__ == "__main__":
    unittest.main()
