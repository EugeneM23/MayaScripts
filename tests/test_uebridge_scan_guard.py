"""Refresh asks before it scans a folder that holds thousands of clips.

2026-11-03, the animator: «Я нажал на обновление списка файлов в animation
setup и теперь у меня создаюстся какие-то 14 тысяч файлов? Это какой-то
очень страшный баг». Nothing was created - their own cache, written at
05:11:53 that morning, says `location: C:/Users/MY PC/Downloads`, 14 037
rows, and the Downloads tree held 188 082 entries before the scan and
188 082 after. What they saw was the progress window counting through the
14 206 clip files their Downloads holds (an extracted Unity course: 5 894
fbx of asset packs under «Модуль V. Мультиплеер» alone).

So one click walked somebody's Downloads with no word about the size. The
guard: the walk is cheap (1.1 s over 188 082 entries), so Refresh counts
first and asks before reading, naming the count, the time and where they
are - which is what shows the folder was picked by mistake.
"""

import unittest

from maya_uebridge import sources


def _files(*pairs, **kwargs):
    """`(folder, count)` pairs as paths under `top` (C:/d by default)."""
    top = kwargs.pop("top", "C:/d").rstrip("/")
    out = []
    for folder, count in pairs:
        for i in range(count):
            head = top + "/" + folder + "/" if folder else top + "/"
            out.append("{0}clip{1}.fbx".format(head, i))
    return out


class BiggestFolders(unittest.TestCase):

    def test_the_folders_holding_the_most_come_first(self):
        files = _files(("packs", 30), ("anim", 5), ("props/a/b", 12))
        self.assertEqual(sources.biggest_folders("C:/d", files, most=2),
                         [("packs", 30), ("props", 12)])

    def test_a_file_at_the_top_is_counted_under_the_folder_itself(self):
        files = _files(("", 4), ("packs", 2))
        self.assertEqual(sources.biggest_folders("C:/d", files),
                         [("packs", 2), (".", 4)][::-1])

    def test_backslashes_and_case_do_not_make_a_second_folder(self):
        files = ["C:\\d\\Packs\\a.fbx", "C:/d/packs/b.fbx"]
        self.assertEqual(sources.biggest_folders("c:/D", files),
                         [("Packs", 2)])

    def test_no_files_no_folders(self):
        self.assertEqual(sources.biggest_folders("C:/d", []), [])


class GroupedCount(unittest.TestCase):

    def test_a_count_in_the_thousands_is_spaced(self):
        self.assertEqual(sources.grouped(14206), "14 206")

    def test_a_small_count_is_itself(self):
        self.assertEqual(sources.grouped(7), "7")


class TheQuestion(unittest.TestCase):

    def test_a_folder_of_a_few_clips_is_scanned_with_no_word(self):
        self.assertEqual(sources.scan_question("C:/d", _files(("", 40))), "")

    def test_the_threshold_is_the_count_of_files(self):
        over = sources.ASK_OVER
        self.assertEqual(sources.scan_question("C:/d", _files(("", over))), "")
        self.assertTrue(sources.scan_question("C:/d", _files(("", over + 1))))

    def test_the_question_names_the_count_the_folder_and_the_time(self):
        text = sources.scan_question(
            "C:/Users/MY PC/Downloads",
            _files(("Extracted", 14206), top="C:/Users/MY PC/Downloads"))
        self.assertIn("14206", text.replace(" ", "").replace("\u00a0", ""))
        self.assertIn("C:/Users/MY PC/Downloads", text)
        self.assertIn("Extracted", text)
        #  the fear it has to answer: their files are not touched
        self.assertIn("writes nothing", text)
        #  and how long they will wait
        self.assertRegex(text, r"\b\d+ (s|min)\b")

    def test_the_question_takes_the_threshold_it_is_given(self):
        self.assertTrue(sources.scan_question("C:/d", _files(("", 10)), over=5))


class ScanOverAWalkedList(unittest.TestCase):
    """The window walks to count, then scans - the walk must not run twice
    (1.1 s each over the animator's Downloads, and the two could disagree)."""

    def test_the_scan_takes_the_files_it_is_given(self):
        def no_walk(top):
            raise AssertionError("the scan walked again")
        rows = sources.scan("C:/d", "folder", lambda p: [],
                            files=["C:/d/a.ma", "C:/d/b.mb"], walk=no_walk)
        self.assertEqual([r.name for r in rows], ["a.ma", "b.mb"])

    def test_an_empty_list_is_not_a_missing_one(self):
        def no_walk(top):
            raise AssertionError("the scan walked again")
        self.assertEqual(sources.scan("C:/d", "folder", lambda p: [],
                                      files=[], walk=no_walk), [])


if __name__ == "__main__":
    unittest.main()
