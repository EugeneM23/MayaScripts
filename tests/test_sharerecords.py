"""maya_sharerecords: the Shared section's records, pure.

Spec: docs/superpowers/specs/2026-09-30-shared-files-design.md
"""

import json
import os
import subprocess
import sys
import time
import unittest

import maya_sharerecords as records

PLUGIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(
    __file__))), "SkeldarAnim")
NOW = 1790760000
RID = "0123456789abcdef0123456789abcdef"
URL = "https://litter.catbox.moe/abc123.zip"


def _record(state="sending", **extra):
    rec = records.make_record(state, RID, "Eugene", "m1", "Orc_attack.ma",
                              12900000, NOW, comment="attack v2",
                              maya="2027", fps=30.0, frame_range=(0, 60))
    rec.update(extra)
    return rec


def _ready(**extra):
    fields = {"url": URL, "zip": 4000000}
    fields.update(extra)
    return records.with_state(_record(), "ready", **fields)


class Records(unittest.TestCase):

    def test_new_id_is_32_hex(self):
        rid = records.new_id()
        self.assertEqual(len(rid), 32)
        int(rid, 16)
        self.assertNotEqual(rid, records.new_id())

    def test_kind_of(self):
        self.assertEqual(records.kind_of("a.ma"), "scene")
        self.assertEqual(records.kind_of("a.MB"), "scene")
        self.assertEqual(records.kind_of("clip.fbx"), "fbx")
        self.assertIsNone(records.kind_of("notes.txt"))
        self.assertIsNone(records.kind_of(""))

    def test_make_record_holds_the_fields(self):
        rec = _record()
        self.assertEqual(rec["app"], records.APP)
        self.assertEqual(rec["v"], records.VERSION)
        self.assertEqual(rec["kind"], "scene")
        self.assertEqual(rec["range"], [0, 60])
        self.assertEqual(rec["fps"], 30.0)
        self.assertNotIn("url", rec)

    def test_with_state_copies(self):
        rec = _record()
        ready = records.with_state(rec, "ready", url=URL, zip=5)
        self.assertEqual(rec["state"], "sending")
        self.assertEqual(ready["state"], "ready")
        self.assertEqual(ready["url"], URL)

    def test_encode_parse_round_trip(self):
        for rec in (_record(), _ready(),
                    records.with_state(_record(), "failed")):
            self.assertEqual(records.parse(records.encode(rec)), rec)

    def test_a_cyrillic_name_and_comment_travel(self):
        rec = _record(name="Атака_орка.ma", comment="проверь меч")
        back = records.parse(records.encode(rec))
        self.assertEqual(back["name"], "Атака_орка.ma")
        self.assertEqual(back["comment"], "проверь меч")


class ParseRefuses(unittest.TestCase):

    def _refused(self, rec):
        self.assertIsNone(records.parse(json.dumps(rec)))

    def test_not_json_or_not_a_dict(self):
        self.assertIsNone(records.parse("hello"))
        self.assertIsNone(records.parse("[1, 2]"))
        self.assertIsNone(records.parse(None))

    def test_another_app_or_version(self):
        self._refused(_record(app="someone-else"))
        self._refused(_record(v=2))

    def test_a_bad_id(self):
        self._refused(_record(id="../../etc"))
        self._refused(_record(id=RID.upper()))

    def test_an_unknown_state(self):
        self._refused(_record(state="deleted"))

    def test_a_name_that_is_a_path_or_not_ours(self):
        for name in ("../x.ma", "a/b.ma", "C:x.ma", ".hidden.ma", "x.exe",
                     "", "   "):
            self._refused(_record(name=name))

    def test_sizes_must_be_ints(self):
        self._refused(_record(bytes="12"))
        self._refused(_record(sent=True))

    def test_a_ready_record_elsewhere(self):
        self._refused(_ready(url="https://evil.example.com/x.zip"))
        self._refused(_ready(url="http://litter.catbox.moe/x.zip"))
        self._refused(_ready(url="https://litter.catbox.moe/"))
        self._refused(records.with_state(_record(), "ready", url=URL))

    def test_the_kind_is_recomputed(self):
        back = records.parse(json.dumps(_record(kind="fbx")))
        self.assertEqual(back["kind"], "scene")

    def test_from_event_takes_messages_only(self):
        body = records.encode(_record())
        self.assertIsNone(records.from_event({"event": "open"}))
        self.assertIsNone(records.from_event({"event": "keepalive"}))
        self.assertIsNone(records.from_event("nope"))
        self.assertEqual(records.from_event(
            {"event": "message", "id": "x", "message": body})["id"], RID)

    def test_allowed_url(self):
        self.assertTrue(records.allowed_url(URL))
        self.assertFalse(records.allowed_url(None))
        self.assertFalse(records.allowed_url("https://litter.catbox.moe.evil.com/a"))


class Merge(unittest.TestCase):

    def test_ready_beats_sending(self):
        self.assertEqual(records.merge(_record(), _ready())["state"], "ready")

    def test_a_replay_keeps_the_known_object(self):
        known = _ready()
        self.assertIs(records.merge(known, _ready()), known)
        self.assertIs(records.merge(known, _record()), known)

    def test_failed_does_not_replace_ready(self):
        known = _ready()
        self.assertIs(records.merge(
            known, records.with_state(_record(), "failed")), known)

    def test_nothing_known(self):
        rec = _record()
        self.assertIs(records.merge(None, rec), rec)


class Visible(unittest.TestCase):

    def test_newest_first_and_filters(self):
        old = _ready(id="1" * 32, sent=NOW - records.LIFETIME - 1)
        failed = records.with_state(_record(id="2" * 32), "failed")
        stale = _record(id="3" * 32, sent=NOW - records.SENDING_TIMEOUT - 5)
        a = _ready(id="4" * 32, sent=NOW - 100)
        b = _record(id="5" * 32, sent=NOW - 10)
        shown = records.visible([old, failed, stale, a, b], NOW)
        self.assertEqual([r["id"] for r in shown], ["5" * 32, "4" * 32])

    def test_expired_and_news(self):
        self.assertFalse(records.expired(_record(), NOW + records.LIFETIME))
        self.assertTrue(records.expired(_record(), NOW + records.LIFETIME + 1))
        self.assertTrue(records.is_news(_record(), NOW + 60))
        self.assertFalse(records.is_news(_record(),
                                         NOW + records.NEWS_WITHIN + 1))

    def test_is_mine(self):
        self.assertTrue(records.is_mine(_record(), "m1"))
        self.assertFalse(records.is_mine(_record(), "m2"))
        self.assertFalse(records.is_mine(_record(machine=""), ""))


class Labels(unittest.TestCase):

    def test_status_label(self):
        sending, ready = _record(), _ready()
        failed = records.with_state(sending, "failed")
        self.assertEqual(records.status_label(failed, True), "failed")
        self.assertEqual(records.status_label(sending, True, 0.456),
                         "sending 45%")
        self.assertEqual(records.status_label(sending, True), "sending...")
        self.assertEqual(records.status_label(sending, False, 0.5),
                         "sending...")
        self.assertEqual(records.status_label(ready, True), "sent")
        self.assertEqual(records.status_label(ready, False, local=True),
                         "ready")
        self.assertEqual(records.status_label(ready, False, error="x"),
                         "failed, retry")
        self.assertEqual(records.status_label(ready, False, 0.3), "30%")
        self.assertEqual(records.status_label(ready, False), "waiting")

    def test_size_text(self):
        self.assertEqual(records.size_text(0), "0 KB")
        self.assertEqual(records.size_text(300), "1 KB")
        self.assertEqual(records.size_text(340 * 1024), "340 KB")
        self.assertEqual(records.size_text(12900000), "12.3 MB")
        self.assertEqual(records.size_text(3 * 1024 ** 3), "3.00 GB")

    def test_when_text(self):
        self.assertEqual(records.when_text(NOW, NOW),
                         time.strftime("%H:%M", time.localtime(NOW)))
        earlier = NOW - 3 * 86400
        self.assertEqual(records.when_text(earlier, NOW),
                         time.strftime("%d.%m %H:%M", time.localtime(earlier)))

    def test_row_text_columns(self):
        rec = _ready(name="A_very_long_scene_name_that_goes_on_and_on.ma",
                     **{"from": "Konstantin_the_animator"})
        row = records.row_text(rec, False, "ready", NOW)
        name_col = row[:records.NAME_WIDTH]
        self.assertTrue(name_col.endswith(".."))
        self.assertIn("Konsta..", row)
        self.assertIn("12.3 MB", row)
        self.assertTrue(row.endswith("attack v2"))
        self.assertIn("you", records.row_text(rec, True, "sent", NOW))
        other = records.row_text(_ready(name="short.ma"), False, "ready", NOW)
        self.assertEqual(row.index("ready"), other.index("ready"))

    def test_row_without_comment_has_no_trailing_space(self):
        row = records.row_text(_ready(comment=""), False, "ready", NOW)
        self.assertEqual(row, row.rstrip())

    def test_details_text(self):
        text = records.details_text(_ready(), False, "ready", NOW)
        self.assertTrue(text.startswith("Orc_attack.ma from Eugene, "))
        self.assertIn("30 fps 0-60", text)
        self.assertIn("attack v2", text)
        self.assertTrue(text.endswith("ready: Open, Import or Save to..."))
        waiting = records.details_text(_ready(comment="", fps=None),
                                       True, "sending 40%", NOW)
        self.assertIn("from you", waiting)
        self.assertTrue(waiting.endswith("sending 40%"))

    def test_inbox_folder(self):
        folder = records.inbox_folder(_record(**{"from": "Олег K/../x"}))
        self.assertIn("Олег_K_x", folder)
        self.assertTrue(folder.endswith("_012345"))
        self.assertTrue(folder.startswith(time.strftime(
            "%Y-%m-%d_%H%M", time.localtime(NOW))))
        self.assertNotIn("/", folder)
        self.assertIn("someone", records.inbox_folder(_record(**{"from": ""})))

    def test_announce_text(self):
        self.assertEqual(records.announce_text(_ready()),
                         "Eugene sent Orc_attack.ma")

    def test_archive_problems(self):
        self.assertEqual(records.archive_problems(["a.ma"], "a.ma"), [])
        self.assertTrue(records.archive_problems(["../a.ma"], "a.ma"))
        self.assertTrue(records.archive_problems(["a.ma", "b.ma"], "a.ma"))
        self.assertTrue(records.archive_problems([], "a.ma"))

    def test_scene_file_name(self):
        self.assertEqual(records.scene_file_name("C:/s/Orc.ma", NOW),
                         ("Orc.ma", "mayaAscii"))
        self.assertEqual(records.scene_file_name("C:/s/Orc.mb", NOW),
                         ("Orc.mb", "mayaBinary"))
        self.assertEqual(records.scene_file_name("C:/s/clip.fbx", NOW),
                         ("clip.ma", "mayaAscii"))
        name, kind = records.scene_file_name("", NOW)
        self.assertEqual(name, "untitled_" + time.strftime(
            "%H%M", time.localtime(NOW)) + ".ma")
        self.assertEqual(kind, "mayaAscii")

    def test_sender_default(self):
        self.assertEqual(records.sender_default("  Eugene "), "Eugene")
        self.assertEqual(records.sender_default(""), "someone")
        self.assertEqual(records.sender_default(None), "someone")

    def test_subtitle(self):
        self.assertEqual(records.subtitle("online", 1), "online - 1 file")
        self.assertEqual(records.subtitle("online", 3), "online - 3 files")
        self.assertEqual(records.subtitle("offline - timed out", 0),
                         "offline - timed out - 0 files")

    def test_left_behind_note(self):
        self.assertEqual(records.left_behind_note([]), "")
        self.assertEqual(records.left_behind_note(["C:/t/a.png"]),
                         "1 texture stays on this machine: a.png")
        note = records.left_behind_note(["a", "b", "c", "d", "e"])
        self.assertTrue(note.startswith("5 textures stay"))
        self.assertTrue(note.endswith("and 2 more"))


class History(unittest.TestCase):

    def test_round_trip_drops_expired_and_malformed(self):
        keep = _ready()
        gone = _ready(id="f" * 32, sent=NOW - records.LIFETIME - 10)
        entries = {keep["id"]: {"record": keep, "local": "C:/x/Orc.ma"},
                   gone["id"]: {"record": gone, "local": ""}}
        text = records.to_history(entries, "msg42")
        data = json.loads(text)
        data["entries"].append({"record": {"app": "nope"}, "local": 3})
        data["entries"].append("junk")
        back, since = records.from_history(json.dumps(data), NOW)
        self.assertEqual(since, "msg42")
        self.assertEqual(list(back), [keep["id"]])
        self.assertEqual(back[keep["id"]]["local"], "C:/x/Orc.ma")
        self.assertEqual(back[keep["id"]]["record"], keep)

    def test_a_broken_file_is_empty(self):
        self.assertEqual(records.from_history("{not json", NOW), ({}, ""))
        self.assertEqual(records.from_history('{"v": 99}', NOW), ({}, ""))


class Purity(unittest.TestCase):

    def test_imports_only_the_stdlib(self):
        code = ("import sys; sys.path.insert(0, %r); import maya_sharerecords;"
                "bad = [m for m in sys.modules if m.split('.')[0] in "
                "('maya', 'PySide6', 'shiboken6')]; print(bad)" % PLUGIN)
        out = subprocess.run([sys.executable, "-c", code], cwd=PLUGIN,
                             capture_output=True, text=True, timeout=120)
        self.assertEqual(out.stdout.strip(), "[]", out.stderr)


if __name__ == "__main__":
    unittest.main()
