"""maya_chat.emoji on the shipped index."""
import unittest

import tests  # noqa: F401  (puts SkeldarAnim/ on sys.path)

from maya_chat import emoji

THUMB, TONE3 = "\U0001F44D", "\U0001F44D\U0001F3FD"
ASTRO = "\U0001F469\u200D\U0001F680"          # woman astronaut (ZWJ)
HEART = "\u2764\ufe0f"


class Index(unittest.TestCase):
    def test_loaded_with_its_groups(self):
        idx = emoji.index()
        self.assertEqual(idx.groups[0][0], "smileys")
        self.assertEqual(len(idx.groups), 8)
        self.assertTrue(idx.of_group("animals"))

    def test_a_toned_glyph_finds_its_record_and_tone(self):
        rec, tone = emoji.index().find(TONE3)
        self.assertEqual(rec["g"], THUMB)
        self.assertEqual(tone, 3)

    def test_a_missing_file_is_an_empty_index(self):
        idx = emoji.index("C:/nowhere/emoji.json")
        self.assertEqual(idx.records, [])
        self.assertEqual(emoji.tokens("hi \U0001F525", idx), [("text", "hi \U0001F525")])


class Tokens(unittest.TestCase):
    def test_text_and_emoji(self):
        self.assertEqual(emoji.tokens("огонь \U0001F525\U0001F525!"),
                         [("text", "огонь "), ("emoji", "\U0001F525"), ("emoji", "\U0001F525"),
                          ("text", "!")])

    def test_sequences_stay_whole(self):
        self.assertEqual(emoji.tokens(ASTRO + TONE3), [("emoji", ASTRO), ("emoji", TONE3)])

    def test_a_heart_with_or_without_its_selector(self):
        self.assertEqual(emoji.tokens(HEART), [("emoji", HEART)])

    def test_a_plain_digit_or_copyright_stays_text(self):
        self.assertEqual(emoji.tokens("1 \u00a9"), [("text", "1 \u00a9")])

    def test_empty(self):
        self.assertEqual(emoji.tokens(""), [])


class Search(unittest.TestCase):
    def test_russian(self):
        found = [r["g"] for r in emoji.search("кот")]
        self.assertIn("\U0001F431", found)

    def test_english_and_prefix(self):
        self.assertIn("\U0001F525", [r["g"] for r in emoji.search("fir")])

    def test_every_word_must_match(self):
        self.assertEqual(emoji.search("кот zzzz"), [])

    def test_empty_query_finds_nothing(self):
        self.assertEqual(emoji.search("   "), [])

    def test_limit(self):
        self.assertLessEqual(len(emoji.search("a", limit=5)), 5)


class Tones(unittest.TestCase):
    def test_toned_and_base(self):
        rec, _t = emoji.index().find(THUMB)
        self.assertEqual(emoji.toned(rec, 3)[0], TONE3)
        self.assertEqual(emoji.toned(rec, 0)[0], THUMB)

    def test_no_tones_gives_the_base(self):
        rec, _t = emoji.index().find("\U0001F525")
        self.assertEqual(emoji.toned(rec, 4)[0], "\U0001F525")


class Count(unittest.TestCase):
    def test_sequences_count_as_one(self):
        self.assertEqual(emoji.count(ASTRO + " " + TONE3), 2)
        self.assertTrue(emoji.only_emoji(ASTRO))

    def test_text_is_none(self):
        self.assertEqual(emoji.count("ok \U0001F525"), 0)

    def test_is_emoji_mirrors_the_server(self):
        self.assertTrue(emoji.is_emoji(ASTRO))
        self.assertTrue(emoji.is_emoji(TONE3))
        self.assertFalse(emoji.is_emoji("1\ufe0f\u20e3"))      # a keycap: the server refuses digits
        self.assertFalse(emoji.is_emoji("\U0001F525a"))
