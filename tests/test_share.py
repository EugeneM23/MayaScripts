"""maya_share: the Shared section - sending, receiving, history, deleting,
the panel.

On a recording `cmds`, a fake network that keeps uploads by address, and
threads and deferred calls that run at once.

Spec: docs/superpowers/specs/2026-09-30-shared-files-design.md,
      docs/superpowers/specs/2026-09-30-shared-delete-and-naming-design.md
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
        self.fields = {}             # textField name -> its text
        self.picked = None           # the list's picked indices, when it is up
        self.dialog = None
        self.confirms = []
        self.messages = []
        self.playback = None
        self.config = "playbackOptions -min 5 -max 45 -ast 0 -aet 50 "

    def objExists(self, name):
        return name == "sceneConfigurationScriptNode"

    def scriptNode(self, name, **kwargs):
        return self.config if kwargs.get("beforeScript") else None

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
        if not (kwargs.get("query") or kwargs.get("q")):
            self.playback = kwargs
            return None
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
        """Up once a test says what is picked (`picked`): the rows are the
        state's, the selection those indices."""
        if self.picked is None:
            return FakeUiCmds.__getattr__(self, "textScrollList")(
                *args, **kwargs)
        if kwargs.get("exists"):
            return True
        if kwargs.get("query") or kwargs.get("q"):
            if kwargs.get("selectIndexedItem"):
                return list(self.picked)
            if kwargs.get("numberOfItems"):
                return len(share.state()["rows"])
            return None
        return None

    def confirmDialog(self, **kwargs):
        self.confirms.append(kwargs)
        return "Delete"


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
        self.refuse = set()          # names whose publish ntfy.sh refuses
        self.midway = None           # called at the first progress tick

    def publish(self, text, topic=None, base=None):
        record = records.parse(text)
        if record["name"] in self.refuse:
            raise net.ShareError("could not reach ntfy.sh: refused")
        self.published.append(record)
        return "m{0}".format(len(self.published))

    def _tick(self, progress, done, total):
        """A progress tick, as net makes it: False from the callback cancels."""
        if self.midway is not None:
            midway, self.midway = self.midway, None
            midway()
        if progress is not None and progress(done, total) is False:
            raise net.Cancelled("cancelled")

    def upload_any(self, path, progress=None):
        if self.fail is not None:
            raise self.fail
        with open(path, "rb") as handle:
            data = handle.read()
        self._tick(progress, len(data) // 2, len(data))
        url = "https://litter.catbox.moe/f{0}.zip".format(len(self.store))
        self.store[url] = data
        self._tick(progress, len(data), len(data))
        return url

    def download(self, url, path, progress=None):
        if url not in self.store:
            raise net.Expired("gone")
        data = self.store[url]
        with open(path, "wb") as out:
            out.write(data[:len(data) // 2])
        self._tick(progress, len(data) // 2, len(data))
        with open(path, "wb") as out:
            out.write(data)
        self._tick(progress, len(data), len(data))
        return len(data)


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
        message = share.send_file(path)
        self.assertIn("clip.fbx", message)
        states = [r["state"] for r in self.net.published]
        self.assertEqual(states, ["sending", "ready"])
        ready = self.net.published[-1]
        self.assertEqual(ready["name"], "clip.fbx")
        self.assertEqual(ready["comment"], "")
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
        share.send_scene()
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


class Naming(_Base):
    """Author is who a file is from; Name names the upload."""

    def test_a_scene_under_the_typed_name_keeps_its_type(self):
        self.fake.scene_name = "C:/work/Orc_attack.mb"
        share.send_scene(name="attack v2")
        exports = [(a, k) for a, k in self.fake.files if k.get("exportAll")]
        self.assertTrue(exports[0][0][0].endswith("attack v2.mb"))
        self.assertEqual(exports[0][1]["type"], "mayaBinary")
        self.assertEqual(self.net.published[-1]["name"], "attack v2.mb")

    def test_a_file_under_the_typed_name_keeps_its_extension(self):
        share.send_file(self._source("clip.fbx"), name="run cycle.ma")
        ready = self.net.published[-1]
        self.assertEqual(ready["name"], "run cycle.fbx")
        local = share.state()["entries"][ready["id"]]["local"]
        self.assertEqual(os.path.basename(local), "run cycle.fbx")
        with zipfile.ZipFile(__import__("io").BytesIO(
                self.net.store[ready["url"]])) as z:
            self.assertEqual(z.namelist(), ["run cycle.fbx"])

    def test_the_field_names_the_upload_and_is_cleared(self):
        self.fake.fields[share.FILE_NAME_FIELD] = "  Orc  hit  "
        share.send_file(self._source("clip.fbx"))
        self.assertEqual(self.net.published[-1]["name"], "Orc hit.fbx")
        self.assertEqual(self.fake.fields[share.FILE_NAME_FIELD], "")

    def test_an_empty_field_is_the_files_own_name(self):
        self.fake.fields[share.FILE_NAME_FIELD] = ""
        share.send_file(self._source("clip.fbx"))
        self.assertEqual(self.net.published[-1]["name"], "clip.fbx")

    def test_the_author_is_remembered_where_the_name_was(self):
        self.fake.fields[share.AUTHOR_FIELD] = "  Oleg "
        share._author_changed()
        self.assertEqual(self.fake.optionvars["skeldarShareName"], "Oleg")
        self.assertEqual(share.sender_name(), "Oleg")
        share.send_file(self._source())
        self.assertEqual(self.net.published[-1]["from"], "Oleg")

    def test_no_comment_is_sent_any_more(self):
        self.assertFalse(hasattr(share, "COMMENT_FIELD"))
        self.assertFalse(hasattr(share, "NAME_FIELD"))
        share.send_file(self._source())
        self.assertEqual(self.net.published[-1]["comment"], "")


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
        self.assertEqual(self.fake.playback, {
            "minTime": 5.0, "maxTime": 45.0, "animationStartTime": 0.0,
            "animationEndTime": 50.0})


class Deleting(_Base):
    """Delete takes the picked files off EVERYBODY's list («Всё у всех»)."""

    def _here(self, name="Longsword.fbx"):
        """A colleague's file, received and downloaded."""
        rec = self._colleague(name=name)
        share.receive(rec)
        local = share.state()["entries"][rec["id"]]["local"]
        self.assertTrue(os.path.isfile(local))
        return rec, local

    def _pick(self, *rids):
        """The list up, with `rids` picked in it."""
        self.fake.picked = []
        share.refresh()
        rows = share.state()["rows"]
        self.fake.picked = [rows.index(rid) + 1 for rid in rids]

    def test_a_delete_publishes_and_takes_the_row_and_the_copy(self):
        rec, local = self._here()
        share.delete_entries([rec["id"]])
        gone = self.net.published[-1]
        self.assertEqual(gone["state"], "deleted")
        self.assertEqual(gone["id"], rec["id"])
        self.assertEqual(gone["by"], share.sender_name())
        self.assertEqual(gone["by_machine"], share.machine_id())
        entry = share.state()["entries"][rec["id"]]
        self.assertEqual(entry["record"]["state"], "deleted")
        self.assertEqual(entry["local"], "")
        self.assertFalse(os.path.exists(local))
        self.assertFalse(os.path.exists(os.path.dirname(local)))
        self.assertEqual(self.statuses[-1], "Deleted 1 file for everybody")
        self.assertEqual(share._labels(time.time())[0], [])

    def test_the_confirm_names_the_files(self):
        saved = share._confirm_delete
        asked = []
        share._confirm_delete = lambda text: asked.append(text) or True
        try:
            rec, _local = self._here()
            share.delete_entries([rec["id"]])
        finally:
            share._confirm_delete = saved
        self.assertIn("Longsword.fbx (Oleg)", asked[0])
        self.assertIn("for everybody", asked[0])

    def test_the_confirm_is_maya_s_dialog_outside_batch(self):
        saved = self.fake.about
        self.fake.about = lambda **kw: (False if kw.get("batch")
                                        else saved(**kw))
        try:
            self.assertTrue(share._confirm_delete("Delete 1 file?"))
        finally:
            self.fake.about = saved
        self.assertEqual(self.fake.confirms[0]["button"], ["Delete", "Cancel"])
        self.assertEqual(self.fake.confirms[0]["defaultButton"], "Cancel")

    def test_cancel_changes_nothing(self):
        rec, local = self._here()
        before = len(self.net.published)
        saved = share._confirm_delete
        share._confirm_delete = lambda text: False
        try:
            message = share.delete_entries([rec["id"]])
        finally:
            share._confirm_delete = saved
        self.assertEqual(message, "Delete cancelled - nothing changed.")
        self.assertEqual(len(self.net.published), before)
        self.assertEqual(
            share.state()["entries"][rec["id"]]["record"]["state"], "ready")
        self.assertTrue(os.path.isfile(local))

    def test_several_at_once_and_one_refused(self):
        a, local_a = self._here("a.fbx")
        b, local_b = self._here("b.fbx")
        self.net.refuse.add("b.fbx")
        share.delete_entries([a["id"], b["id"]])
        entries = share.state()["entries"]
        self.assertEqual(entries[a["id"]]["record"]["state"], "deleted")
        self.assertFalse(os.path.exists(local_a))
        self.assertEqual(entries[b["id"]]["record"]["state"], "ready")
        self.assertTrue(os.path.isfile(local_b))
        self.assertIn("Deleted 1 file for everybody", self.statuses[-1])
        self.assertIn("b.fbx not deleted: could not reach ntfy.sh",
                      self.statuses[-1])
        self.assertIn("nothing changed for it", self.statuses[-1])

    def test_my_own_file_goes_too(self):
        share.send_file(self._source())
        rid = self.net.published[-1]["id"]
        local = share.state()["entries"][rid]["local"]
        share.delete_entries([rid])
        self.assertEqual(self.net.published[-1]["state"], "deleted")
        self.assertFalse(os.path.exists(local))

    def test_nothing_picked(self):
        self.assertEqual(share.delete_selected(),
                         "Pick files in the list first.")
        self.assertEqual(self.net.published, [])

    def test_the_picked_rows(self):
        a, _ = self._here("a.fbx")
        b, _ = self._here("b.fbx")
        c, local_c = self._here("c.fbx")
        self._pick(a["id"], c["id"])
        self.assertEqual(sorted(share.selected_ids()),
                         sorted([a["id"], c["id"]]))
        self.assertIsNone(share.selected_id())
        self.assertIn("2 files picked", share._selected())
        share.delete_selected()
        states = dict((r["id"], r["state"]) for r in self.net.published)
        self.assertEqual(states[a["id"]], "deleted")
        self.assertEqual(states[c["id"]], "deleted")
        self.assertNotIn(b["id"], states)
        self.assertFalse(os.path.exists(local_c))

    def test_open_import_and_save_take_one(self):
        a, _ = self._here("a.fbx")
        b, _ = self._here("b.fbx")
        self._pick(a["id"], b["id"])
        self.assertEqual(share.open_selected(),
                         "Pick one file to open - 2 are picked.")
        self.assertEqual(share.import_selected(),
                         "Pick one file to import - 2 are picked.")
        self.assertEqual(share.save_selected(),
                         "Pick one file to save - 2 are picked.")

    def test_a_colleagues_delete_takes_the_row_and_the_copy(self):
        rec, local = self._here()
        self.assertTrue(share.receive(records.deleted(rec, "Oleg", "theirs")))
        self.assertFalse(os.path.exists(local))
        self.assertEqual(share.state()["entries"][rec["id"]]["local"], "")
        self.assertEqual(self.statuses[-1], "Oleg deleted Longsword.fbx")

    def test_our_own_echo_changes_nothing(self):
        rec, _local = self._here()
        share.delete_entries([rec["id"]])
        said = len(self.statuses)
        self.assertFalse(share.receive(self.net.published[-1]))
        self.assertEqual(len(self.statuses), said)

    def test_the_open_scene_stays_on_the_disk(self):
        rec, local = self._here("Orc.ma")
        self.fake.scene_name = local.replace("\\", "/")
        share.receive(records.deleted(rec, "Oleg", "theirs"))
        self.assertTrue(os.path.isfile(local))
        self.assertIn("it is the open scene", self.statuses[-1])
        self.assertEqual(share._labels(time.time())[0], [])

    def test_nothing_outside_the_share_folder_is_deleted(self):
        rec, _local = self._here()
        outside = self._source("mine.fbx")
        share.state()["entries"][rec["id"]]["local"] = outside
        share.receive(records.deleted(rec, "Oleg", "theirs"))
        self.assertTrue(os.path.isfile(outside))

    def test_a_ready_after_the_delete_changes_nothing(self):
        rec = self._colleague()
        self.assertTrue(share.receive(records.deleted(rec, "Oleg", "theirs")))
        self.assertFalse(share.receive(rec))
        entry = share.state()["entries"][rec["id"]]
        self.assertEqual(entry["record"]["state"], "deleted")
        self.assertEqual(entry["local"], "")
        self.assertEqual(self.fake.messages, [])
        self.assertEqual(share.fetch(rec["id"]), False)

    def test_a_delete_during_my_upload_stops_it(self):
        def midway():
            rid = list(share.state()["transfers"])[0]
            share.delete_entries([rid])
        self.net.midway = midway
        share.send_file(self._source())
        states = [r["state"] for r in self.net.published]
        self.assertEqual(states, ["sending", "deleted"])
        self.assertEqual(self.net.store, {})
        self.assertEqual(share.state()["transfers"], {})
        self.assertFalse(any("failed" in s for s in self.statuses),
                         self.statuses)

    def test_a_delete_during_a_download_stops_it(self):
        rec = self._colleague()
        self.net.midway = lambda: share.receive(
            records.deleted(rec, "Oleg", "theirs"))
        share.receive(rec)
        entry = share.state()["entries"][rec["id"]]
        self.assertEqual(entry["record"]["state"], "deleted")
        self.assertEqual(entry["local"], "")
        self.assertEqual(share.state()["transfers"], {})
        folder = os.path.dirname(share.inbox_path(rec))
        self.assertFalse(os.path.exists(folder))

    def test_the_tombstone_survives_a_fresh_state(self):
        rec, _local = self._here()
        share.delete_entries([rec["id"]])
        del sys._skeldar_share
        share.load_history()
        self.assertEqual(
            share.state()["entries"][rec["id"]]["record"]["state"], "deleted")
        self.assertFalse(share.receive(rec))


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
        for name in (share.AUTHOR_FIELD, share.FILE_NAME_FIELD, share.LIST,
                     share.STATUS, share.SUBTITLE):
            self.assertIn(name, self.fake.children, name)

    def test_author_and_name(self):
        labels = [c[2].get("label") for c in self.fake.calls
                  if c[0] == "text"]
        self.assertIn("Author", labels)
        self.assertIn("Name", labels)
        self.assertNotIn("Comment", labels)
        self.assertEqual(self.fake.fields[share.AUTHOR_FIELD],
                         share.sender_name())
        self.assertEqual(self.fake.fields[share.FILE_NAME_FIELD], "")

    def test_the_list_takes_several_rows_and_the_delete_key(self):
        made = [c[2] for c in self.fake.calls
                if c[0] == "textScrollList" and c[1] == (share.LIST,)]
        self.assertIs(made[0]["allowMultiSelection"], True)
        self.assertTrue(callable(made[0]["deleteKeyCommand"]))

    def test_a_delete_button(self):
        danger = [m for m in self.marks if m.role == "danger"]
        self.assertEqual(len(danger), 1)
        self.assertEqual(danger[0].icon, "trash")
        buttons = [c[2] for c in self.fake.calls if c[0] == "button"]
        self.assertIn("Delete", [b.get("label") for b in buttons])

    def test_one_primary_action(self):
        primary = [m for m in self.marks if m.role == "primary"]
        self.assertEqual(len(primary), 1)
        roles = set(m.role for m in self.marks)
        self.assertIn("subtitle", roles)
        self.assertIn("status", roles)

    def test_it_starts_listening(self):
        self.assertEqual(self.listened, [True])

    def test_the_list_has_a_height_grip(self):
        """2026-10-08: an 8 px placeholder right under the list, marked as
        that list's grip (the skin draws it and keeps the rows; the classic
        hub keeps the pixel height and the placeholder is a quiet gap)."""
        grips = [m for m in self.marks if m.role == "grip"]
        self.assertEqual([(m.name, m.target) for m in grips],
                         [(share.LIST_GRIP, share.LIST)])
        self.assertEqual(share.LIST_GRIP, "skeldarShareListGrip")
        order = [c[1][0] for c in self.fake.calls
                 if c[0] in ("textScrollList", "separator") and c[1]
                 and c[1][0] in (share.LIST, share.LIST_GRIP)
                 and not (c[2].get("edit") or c[2].get("e")
                          or c[2].get("query") or c[2].get("q")
                          or c[2].get("exists"))]
        self.assertEqual(order, [share.LIST, share.LIST_GRIP])
        made = [c[2] for c in self.fake.calls
                if c[0] == "separator" and c[1] == (share.LIST_GRIP,)][0]
        self.assertEqual((made["height"], made["style"]), (8, "none"))
        self.assertEqual([c[2]["height"] for c in self.fake.calls
                          if c[0] == "textScrollList"
                          and c[1] == (share.LIST,) and "height" in c[2]],
                         [share.LIST_HEIGHT])

    def test_the_classic_hub_keeps_the_two_labelled_rows(self):
        rows = [c for c in self.fake.calls if c[0] == "rowLayout"
                and c[2].get("numberOfColumns") == 2
                and c[2].get("adjustableColumn") == 2]
        self.assertEqual(len(rows), 2)
        self.assertEqual([c[2]["label"] for c in self.fake.calls
                          if c[0] == "text" and c[2].get("label") in
                          ("Author", "Name")], ["Author", "Name"])
        fields = dict((c[1][0], c[2]) for c in self.fake.calls
                      if c[0] == "textField" and c[1])
        self.assertEqual(fields[share.AUTHOR_FIELD]["placeholderText"],
                         "your name, as your colleagues see it")
        self.assertEqual(fields[share.FILE_NAME_FIELD]["placeholderText"],
                         "empty: the scene's own name")

    def test_the_classic_numbers(self):
        buttons = dict((c[2]["label"], c[2]) for c in self.fake.calls
                       if c[0] == "button" and c[2].get("label"))
        self.assertEqual(buttons["Send scene"]["height"], 32)
        self.assertEqual((buttons["Send file..."]["height"],
                          buttons["Send file..."]["width"]), (32, 110))
        for label in ("Open", "Import", "Save to...", "Delete"):
            self.assertEqual(buttons[label]["height"], 28, label)
        self.assertEqual((buttons["Save to..."]["width"],
                          buttons["Delete"]["width"]), (90, 64))
        self.assertEqual(self.fake.column["rowSpacing"], 6)

    def test_the_status_tells_the_hub(self):
        """2026-10-08: the line is told to the hub where it was written (the
        skin hides the card's own line and shows the hub's)."""
        heard = []
        listener = lambda control, text, viewport: heard.append((control, text))
        plain = self.fake.text
        self.fake.text = lambda *a, **kw: (
            True if kw.get("exists") else plain(*a, **kw))
        maya_hubstyle.listen(listener)
        try:
            self.saved_status("sent")
        finally:
            maya_hubstyle.unlisten(listener)
        self.assertEqual(heard, [(share.STATUS, "sent")])

    def test_a_status_with_no_line_goes_to_the_hubs_message_line_only(self):
        heard, said = [], []
        listener = lambda control, text, viewport: heard.append((control, text))
        saved_say = maya_hub.say
        maya_hub.say = lambda message, state=None: said.append(message)
        maya_hubstyle.listen(listener)
        try:
            self.saved_status("sent")           # `exists` answers False
        finally:
            maya_hubstyle.unlisten(listener)
            maya_hub.say = saved_say
        self.assertEqual((heard, said), ([], ["sent"]))

    def test_show_window_asks_the_hub(self):
        asked = []
        saved = maya_hub.show
        maya_hub.show = lambda key=None: asked.append(key)
        try:
            share.show_window()
        finally:
            maya_hub.show = saved
        self.assertEqual(asked, ["shared"])


class PanelSkin(_Base):
    """The panel built for the skin (2026-10-08): the compact numbers, author
    and name on one row without labels, the icon-only Save to... and Delete."""

    def setUp(self):
        _Base.setUp(self)
        maya_hubstyle.take_marks()
        self.saved_listen = share.listen
        share.listen = lambda: None
        maya_hubstyle.set_skinning(True)
        try:
            share.build_panel()
        finally:
            maya_hubstyle.set_skinning(False)
        self.marks = maya_hubstyle.take_marks()

    def tearDown(self):
        share.listen = self.saved_listen
        _Base.tearDown(self)

    def _row_of(self, name):
        """The creation calls inside the rowLayout that holds control `name`
        (the nearest enclosing one), and the row's own call."""
        depth_stack = []
        for call in self.fake.calls:
            if call[0] == "rowLayout" and not (call[2].get("edit")
                                               or call[2].get("exists")):
                depth_stack.append([call, []])
            elif call[0] == "setParent" and call[1] == ("..",):
                if depth_stack:
                    row = depth_stack.pop()
                    if any(c[1] == (name,) for c in row[1]):
                        return row
            elif depth_stack:
                depth_stack[-1][1].append(call)
        return None

    def test_author_and_name_share_one_row_without_labels(self):
        row, inside = self._row_of(share.AUTHOR_FIELD)
        self.assertEqual(row[2]["numberOfColumns"], 2)
        self.assertEqual(row[2]["adjustableColumn"], 2)
        self.assertEqual(row[2]["columnWidth2"], (110, 200))
        self.assertEqual([c[1][0] for c in inside if c[0] == "textField"],
                         [share.AUTHOR_FIELD, share.FILE_NAME_FIELD])
        self.assertEqual([c for c in inside if c[0] == "text"], [])
        labels = [c[2].get("label") for c in self.fake.calls
                  if c[0] == "text"]
        self.assertNotIn("Author", labels)
        self.assertNotIn("Name", labels)

    def test_the_placeholders_say_which_is_which(self):
        fields = dict((c[1][0], c[2]) for c in self.fake.calls
                      if c[0] == "textField" and c[1])
        self.assertEqual(fields[share.AUTHOR_FIELD]["placeholderText"],
                         "author")
        self.assertEqual(fields[share.AUTHOR_FIELD]["annotation"],
                         "your name, as your colleagues see it")
        self.assertTrue(callable(fields[share.AUTHOR_FIELD]["changeCommand"]))
        self.assertEqual(fields[share.FILE_NAME_FIELD]["placeholderText"],
                         "name (empty: the scene's)")
        self.assertNotIn("changeCommand", fields[share.FILE_NAME_FIELD])
        for field in fields.values():
            self.assertEqual(field["height"], 20)
        self.assertEqual(self.fake.fields[share.AUTHOR_FIELD],
                         share.sender_name())
        self.assertEqual(self.fake.fields[share.FILE_NAME_FIELD], "")

    def test_the_compact_numbers(self):
        buttons = dict((c[2]["label"], c[2]) for c in self.fake.calls
                       if c[0] == "button" and "label" in c[2])
        self.assertEqual(buttons["Send scene"]["height"], 24)
        self.assertEqual((buttons["Send file..."]["height"],
                          buttons["Send file..."]["width"]), (24, 104))
        for label in ("Open", "Import"):
            self.assertEqual(buttons[label]["height"], 24, label)
        #  Save to... and Delete are icons alone: their label is empty
        icons = [c[2] for c in self.fake.calls
                 if c[0] == "button" and c[2].get("label") == ""]
        self.assertEqual([(b["width"], b["height"]) for b in icons],
                         [(26, 24), (26, 24)])
        self.assertEqual(self.fake.column["rowSpacing"], 3)

    def test_the_roles_and_the_grip_are_the_same(self):
        by_role = {}
        for mark in self.marks:
            by_role.setdefault(mark.role, []).append(mark)
        self.assertEqual(len(by_role["primary"]), 1)
        self.assertEqual(len(by_role["danger"]), 1)
        self.assertEqual([(m.name, m.target) for m in by_role["grip"]],
                         [(share.LIST_GRIP, share.LIST)])
        self.assertEqual(by_role["subtitle"][0].name, share.SUBTITLE)
        self.assertEqual(by_role["status"][0].name, share.STATUS)


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
