"""The chat's emoji, avatars cache, everybody-directory, reactions records and the chime."""
import os
import shutil
import tempfile
import unittest

import tests  # noqa: F401  (puts SkeldarAnim/ on sys.path)

import maya_hubsound as sound
from maya_chat import avatars
from maya_chat import emoji
from maya_chat import look
from maya_chat import records

ME = {"id": "me", "nick": "me", "name": "Me", "avatar_v": 0}


class Emoji(unittest.TestCase):
    def test_every_emoji_is_a_reaction_the_server_takes(self):
        for e in emoji.every():
            if "⃣" in e:            # keycaps carry an ASCII digit: the server refuses them
                continue
            self.assertTrue(emoji.is_emoji(e), e)
        for e in emoji.QUICK:
            self.assertTrue(emoji.is_emoji(e), e)

    def test_text_is_no_emoji(self):
        for t in ("", "a", "👍a", "1", " ", "x" * 3):
            self.assertFalse(emoji.is_emoji(t), t)

    def test_only_emoji_is_drawn_big(self):
        self.assertTrue(emoji.only_emoji("🔥"))
        self.assertTrue(emoji.only_emoji("❤️ 😂"))
        self.assertTrue(emoji.only_emoji("👍🏽"))           # a skin tone is one emoji
        self.assertFalse(emoji.only_emoji("🔥🔥🔥🔥"))
        self.assertFalse(emoji.only_emoji("ok 🔥"))

    def test_recent_comes_first_once(self):
        raw = emoji.used(None, "🔥")
        raw = emoji.used(raw, "😂")
        raw = emoji.used(raw, "🔥")
        self.assertEqual(emoji.recent(raw)[:2], ["🔥", "😂"])
        self.assertEqual(emoji.recent("broken"), list(emoji.QUICK))

    def test_pills(self):
        self.assertEqual(emoji.pills({"👍": ["a", "me"], "🔥": ["b"]}, "me"),
                         [("👍", 2, True), ("🔥", 1, False)])


class Records(unittest.TestCase):
    def test_a_message_carries_its_reactions(self):
        m = records.message({"id": "m", "chat": "c", "seq": 1, "from_id": "a", "cid": "x",
                             "text": "hi", "reply_to": None, "at": 1,
                             "reactions": {"👍": ["a", "a", 3], "": ["b"], "🔥": []}})
        self.assertEqual(m["reactions"], {"👍": ["a"]})

    def test_the_reaction_event(self):
        e = records.event({"seq": 4, "kind": "reaction", "chat_id": "c", "id": "m",
                           "user_id": "u", "emoji": "🔥", "on": False})
        self.assertEqual((e["emoji"], e["on"]), ("🔥", False))
        self.assertIsNone(records.event({"seq": 4, "kind": "reaction", "chat_id": "c"}))

    def test_toggled(self):
        r = records.toggled({}, "👍", "a", True)
        r = records.toggled(r, "👍", "b", True)
        r = records.toggled(r, "👍", "a", True)
        self.assertEqual(r, {"👍": ["a", "b"]})
        r = records.toggled(r, "👍", "a", False)
        r = records.toggled(r, "👍", "b", False)
        self.assertEqual(r, {})


class Directory(unittest.TestCase):
    def test_chats_then_everybody_without_a_dm(self):
        bob = {"id": "bob", "nick": "bob", "name": "Bob"}
        dm = {"id": "dm", "kind": "dm", "members": [ME, bob], "last": {"at": 5}}
        people = [bob, {"id": "zed", "nick": "zed", "name": "Zed", "online": True},
                  {"id": "amy", "nick": "amy", "name": "Amy", "online": False, "last_seen": 0},
                  dict(ME)]
        chats, persons = look.directory([dm], people, "me", {}, "", 10 ** 12)
        self.assertEqual([c["id"] for c in chats], ["dm"])
        self.assertEqual([p["id"] for p in persons], ["zed", "amy"])   # online first
        self.assertIn("в сети", persons[0]["line"])
        _chats, persons = look.directory([dm], people, "me", {"amy": {"online": True}}, "am", 0)
        self.assertEqual([(p["id"], p["online"]) for p in persons], [("amy", True)])

    def test_everybody(self):
        rows = look.everybody([ME, {"id": "b", "nick": "b", "name": "Bo"},
                               {"id": "a", "nick": "a", "name": "Al"}], "me")
        self.assertEqual([r["id"] for r in rows], ["a", "b"])


class FakeApi(object):
    def __init__(self, data=b"jpeg"):
        self.data, self.asked = data, []

    def avatar(self, uid):
        self.asked.append(uid)
        if self.data is None:
            raise IOError("no")
        return self.data


class Cache(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.api = FakeApi()
        self.cache = avatars.Cache(self.dir, lambda: self.api, start=lambda fn: fn())

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_no_picture_fetches_nothing(self):
        self.assertIsNone(self.cache.file({"id": "u", "avatar_v": 0}))
        self.assertEqual(self.api.asked, [])

    def test_a_picture_is_fetched_once_a_version(self):
        user = {"id": "u", "avatar_v": 2}
        self.assertIsNone(self.cache.file(user))
        self.assertTrue(self.cache.take_changed())
        self.assertEqual(self.cache.file(user), avatars.path_for(self.dir, "u", 2))
        self.cache.file(user)
        self.assertEqual(self.api.asked, ["u"])
        self.cache.file({"id": "u", "avatar_v": 3})
        self.assertEqual(self.api.asked, ["u", "u"])

    def test_a_failure_is_not_asked_again(self):
        self.api.data = None
        user = {"id": "u", "avatar_v": 1}
        self.cache.file(user)
        self.cache.file(user)
        self.assertEqual(self.api.asked, ["u"])
        self.assertFalse(self.cache.take_changed())

    def test_put_is_on_disk_at_once(self):
        self.cache.put("me", 4, b"x")
        self.assertTrue(os.path.isfile(avatars.path_for(self.dir, "me", 4)))


class Chime(unittest.TestCase):
    def test_the_shipped_chime_is_the_synthesis(self):
        with open(sound.sound_path("message"), "rb") as f:
            shipped = f.read()
        self.assertEqual(shipped, sound.wav_bytes(sound.synth(sound.SOUNDS["message"])))

    def test_its_second_note_starts_late_and_it_ends_on_zero(self):
        samples = sound.synth(sound.SOUNDS["message"])
        self.assertEqual(samples[0], 0.0)
        self.assertAlmostEqual(samples[-1], 0.0, places=6)
        self.assertAlmostEqual(max(abs(v) for v in samples), 0.25, places=6)

    def test_force_plays_with_the_interface_sounds_off(self):
        sound.reset()
        made = []

        class P(object):
            def play(self):
                made.append(1)
        try:
            orig = sound.make_player
            sound.make_player = lambda path: P()
            sound.set_enabled(False)
            self.assertFalse(sound.play("message", now=100.0))
            self.assertTrue(sound.play("message", now=101.0, force=True))
            self.assertEqual(made, [1])
        finally:
            sound.make_player = orig
            sound.reset()


if __name__ == "__main__":
    unittest.main()
