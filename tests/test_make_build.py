"""Tests for the distribution archive builder.

Everything runs against a fake source tree in a temp dir, so the real
50 MB payload is never zipped to prove a rule about naming. The one test
that touches the repository asks only where the composition comes from.
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
import zipfile

import install
import make_build


def _write(path, text="x"):
    folder = os.path.dirname(path)
    if not os.path.isdir(folder):
        os.makedirs(folder)
    with open(path, "w") as handle:
        handle.write(text)


class FakeTree(unittest.TestCase):
    """A miniature distribution: one file, one package, one empty dir."""

    NAMES = ("tool.py", "pkg", "empty")

    def setUp(self):
        self.root = tempfile.mkdtemp()
        _write(os.path.join(self.root, "tool.py"))
        _write(os.path.join(self.root, "pkg", "__init__.py"))
        _write(os.path.join(self.root, "pkg", "sub", "mod.py"))
        _write(os.path.join(self.root, "pkg", "__pycache__", "mod.pyc"))
        _write(os.path.join(self.root, "pkg", "stale.pyc"))
        os.makedirs(os.path.join(self.root, "empty"))
        self.out = os.path.join(self.root, "out", "dist.zip")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def names_in(self, path):
        with zipfile.ZipFile(path) as zf:
            return zf.namelist()


class Composition(unittest.TestCase):

    def test_payload_comes_from_the_installer(self):
        self.assertEqual(make_build.payload_names(), install.payload())

    def test_the_builder_itself_never_ships(self):
        self.assertNotIn("make_build.py", install.payload())

    def test_the_source_root_is_the_plugin_folder(self):
        self.assertEqual(os.path.basename(make_build.source_root()),
                         install.SHELF)

    def test_the_archive_lands_beside_the_repository(self):
        """Not beside source_root(): since the payload moved into the
        repo's SkeldarAnim/ that would drop the zip inside the repo, one
        level in from every earlier build."""
        self.assertEqual(
            os.path.normcase(make_build.default_out_dir()),
            os.path.normcase(os.path.dirname(make_build.REPO_ROOT)))
        self.assertNotEqual(
            os.path.normcase(make_build.default_out_dir()),
            os.path.normcase(make_build.REPO_ROOT))

    def test_archive_name_is_dated(self):
        import datetime
        name = make_build.archive_name(datetime.date(2026, 9, 1))
        self.assertEqual(name, "SkeldarAnim_2026-09-01.zip")


class Entries(FakeTree):

    def test_everything_sits_under_one_top_folder(self):
        arcnames = [a for _, a in
                    make_build.entries(self.root, self.NAMES)]
        self.assertTrue(arcnames)
        for name in arcnames:
            self.assertTrue(name.startswith(install.SHELF + "/"), name)

    def test_files_and_nested_files_are_there(self):
        arcnames = [a for _, a in
                    make_build.entries(self.root, self.NAMES)]
        self.assertIn(install.SHELF + "/tool.py", arcnames)
        self.assertIn(install.SHELF + "/pkg/__init__.py", arcnames)
        self.assertIn(install.SHELF + "/pkg/sub/mod.py", arcnames)

    def test_compiled_python_stays_home(self):
        arcnames = [a for _, a in
                    make_build.entries(self.root, self.NAMES)]
        self.assertFalse([n for n in arcnames if "__pycache__" in n])
        self.assertFalse([n for n in arcnames if n.endswith(".pyc")])

    def test_an_empty_directory_survives(self):
        """overrig/misc/ is empty and $path_to_JGLBN points at it."""
        arcnames = [a for _, a in
                    make_build.entries(self.root, self.NAMES)]
        self.assertIn(install.SHELF + "/empty/", arcnames)

    def test_missing_names_are_reported(self):
        self.assertEqual(make_build.missing(self.root, self.NAMES), [])
        self.assertEqual(
            make_build.missing(self.root, ("tool.py", "ghost")), ["ghost"])


class Build(FakeTree):

    def test_it_writes_a_readable_archive(self):
        path = make_build.build(self.out, self.root, self.NAMES)
        self.assertTrue(os.path.isfile(path))
        self.assertIn(install.SHELF + "/pkg/sub/mod.py",
                      self.names_in(path))

    def test_it_stamps_the_build(self):
        path = make_build.build(self.out, self.root, self.NAMES)
        with zipfile.ZipFile(path) as zf:
            stamp = zf.read(install.SHELF + "/BUILD_INFO.txt")
        self.assertIn(b"built:", stamp)

    def test_a_missing_payload_entry_refuses(self):
        with self.assertRaises(RuntimeError):
            make_build.build(self.out, self.root, ("tool.py", "ghost"))
        self.assertFalse(os.path.exists(self.out))

    def test_it_makes_the_output_folder(self):
        deep = os.path.join(self.root, "a", "b", "dist.zip")
        make_build.build(deep, self.root, self.NAMES)
        self.assertTrue(os.path.isfile(deep))


class VersionRecord(FakeTree):
    """The build's `version.json` (2026-09-28): inside the archive for the
    installer, beside it for GitHub's release, one record in both."""

    def _git(self, *args):
        subprocess.check_output(("git",) + args, cwd=self.root,
                                stderr=subprocess.STDOUT)

    def _commit(self):
        self._git("init", "-q")
        self._git("-c", "user.name=t", "-c", "user.email=t@t", "add", ".")
        self._git("-c", "user.name=t", "-c", "user.email=t@t", "commit",
                  "-q", "-m", "the first build")
        return subprocess.check_output(
            ("git", "rev-parse", "HEAD"), cwd=self.root).decode().strip()

    def _record_in(self, path):
        with zipfile.ZipFile(path) as zf:
            return json.loads(zf.read(install.SHELF + "/version.json"))

    def test_the_archive_carries_a_record(self):
        path = make_build.build(self.out, self.root, self.NAMES)
        rec = self._record_in(path)
        self.assertEqual(rec["name"], install.SHELF)
        self.assertIn("built", rec)

    def test_a_committed_tree_records_its_commit(self):
        head = self._commit()
        beside = os.path.join(self.root, "out", "version.json")
        path = make_build.build(self.out, self.root, self.NAMES,
                                version_out=beside)
        rec = self._record_in(path)
        self.assertEqual(rec["commit"], head)
        self.assertEqual(rec["log"][0], [head, "the first build"])
        self.assertFalse(rec["dirty"])
        with open(beside, encoding="utf-8") as handle:
            self.assertEqual(json.load(handle), rec)

    def test_a_release_without_git_is_refused(self):
        """A record with no commit would read as "not current" to every
        colleague, for ever."""
        beside = os.path.join(self.root, "out", "version.json")
        with self.assertRaises(RuntimeError):
            make_build.build(self.out, self.root, self.NAMES,
                             version_out=beside)
        self.assertFalse(os.path.exists(beside))

    def test_the_command_line_takes_both_paths(self):
        self.assertEqual(
            make_build.parse_args(["--out", "d/S.zip",
                                   "--version-out", "d/v.json"]),
            ("d/S.zip", "d/v.json"))
        self.assertEqual(make_build.parse_args([]), (None, None))


class Verify(FakeTree):

    def test_a_complete_archive_passes(self):
        stamp = make_build.build_info(self.root, self.NAMES)
        written = make_build.write_archive(
            self.root, _made(self.out), self.NAMES, stamp)
        self.assertEqual(make_build.verify(self.out, written), [])

    def test_a_short_archive_is_caught(self):
        written = make_build.write_archive(
            self.root, _made(self.out), self.NAMES)
        problems = make_build.verify(self.out, written + ["ghost.py"])
        self.assertEqual(len(problems), 1)
        self.assertIn("missing", problems[0])

    def test_an_extra_entry_is_caught(self):
        written = make_build.write_archive(
            self.root, _made(self.out), self.NAMES)
        problems = make_build.verify(self.out, written[:-1])
        self.assertEqual(len(problems), 1)
        self.assertIn("unexpected", problems[0])


def _made(path):
    folder = os.path.dirname(path)
    if not os.path.isdir(folder):
        os.makedirs(folder)
    return path


if __name__ == "__main__":
    unittest.main()
