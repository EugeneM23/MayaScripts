"""Update: Check update fetches the latest build from GitHub's releases.

The pure halves are tested as such; the press runs against a recording
`cmds`, a fake network (`_open`) and a fake installer, so no test reaches
GitHub or touches the installed folder.

Spec: docs/superpowers/specs/2026-09-28-update-button-design.md
"""

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
import urllib.error
import zipfile

import maya_update as up

from tests.uifakes import FakeUiCmds

PLUGIN = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "SkeldarAnim")

A = "a" * 40
B = "b" * 40
C = "c" * 40
D = "d" * 40


def record(commit, log=(), **extra):
    rec = {"name": "SkeldarAnim", "commit": commit, "short": commit[:7],
           "subject": "subject of " + commit[:1],
           "date": "2026-09-28T12:10:33+03:00",
           "log": [[sha, "change " + sha[:1]] for sha in log]}
    rec.update(extra)
    return rec


# ------------------------------------------------------------------- pure

class ParseRecord(unittest.TestCase):

    def test_a_record_comes_back_as_a_dict(self):
        self.assertEqual(up.parse_record(json.dumps(record(A)))["commit"], A)

    def test_no_commit_is_unreadable(self):
        with self.assertRaises(up.UpdateError):
            up.parse_record(json.dumps({"name": "SkeldarAnim"}))

    def test_not_json_is_unreadable(self):
        with self.assertRaises(up.UpdateError):
            up.parse_record("<html>rate limited</html>")

    def test_a_list_is_unreadable(self):
        with self.assertRaises(up.UpdateError):
            up.parse_record("[1, 2]")


class Describe(unittest.TestCase):

    def test_short_date_and_subject(self):
        self.assertEqual(up.describe(record(A)),
                         "aaaaaaa, 2026-09-28 12:10 - subject of a")

    def test_nothing_is_a_copy_from_before_updates(self):
        self.assertIn("unknown", up.describe({}))
        self.assertIn("unknown", up.describe(None))

    def test_a_source_install_says_so(self):
        text = up.describe(record(A, source="C:/repo/SkeldarAnim"))
        self.assertIn("source folder", text)
        self.assertNotIn("uncommitted", text)

    def test_a_dirty_source_install_says_so(self):
        text = up.describe(record(A, source="C:/repo", dirty=True))
        self.assertIn("uncommitted", text)

    def test_a_source_install_without_git(self):
        self.assertIn("source folder", up.describe({"source": "C:/x"}))

    def test_the_panel_lines_carry_no_subject(self):
        """A subject wrapped the installed line past its height in a
        360 px dock (live, 2026-09-28) - the dialog lists it anyway."""
        text = up.describe(record(A, source="C:/repo"), subject=False)
        self.assertEqual(text,
                         "aaaaaaa, 2026-09-28 12:10 (from the source folder)")

    def test_a_long_subject_is_cut(self):
        rec = record(A, subject="x" * 200)
        self.assertLess(len(up.describe(rec, width=60)), 100)


class IsCurrent(unittest.TestCase):

    def test_the_same_commit_is_current(self):
        self.assertTrue(up.is_current(record(A), record(A)))

    def test_another_commit_is_not(self):
        self.assertFalse(up.is_current(record(A), record(B)))

    def test_an_unknown_install_is_never_current(self):
        self.assertFalse(up.is_current({}, record(A)))
        self.assertFalse(up.is_current(None, record(A)))
        self.assertFalse(up.is_current({"commit": ""}, {"commit": ""}))


class ChangesSince(unittest.TestCase):

    def test_what_came_after_the_installed_commit(self):
        latest = record(D, log=(D, C, B, A))
        entries, found = up.changes_since(record(B), latest)
        self.assertTrue(found)
        self.assertEqual([sha for sha, _ in entries], [D, C])

    def test_an_installed_commit_off_the_log_shows_the_newest(self):
        latest = record(D, log=[D] * 40)
        entries, found = up.changes_since(record(A), latest, limit=15)
        self.assertFalse(found)
        self.assertEqual(len(entries), 15)

    def test_no_log_is_no_entries(self):
        self.assertEqual(up.changes_since(record(A), {"commit": B}),
                         ([], False))


class ConfirmText(unittest.TestCase):

    def test_names_both_builds_and_the_changes(self):
        text = up.confirm_text(record(B), record(D, log=(D, C, B)),
                               "C:/prefs/scripts/SkeldarAnim")
        self.assertIn("Installed:", text)
        self.assertIn("Available:", text)
        self.assertIn("ddddddd  change d", text)
        self.assertIn("ccccccc  change c", text)
        self.assertNotIn("bbbbbbb  change b", text)
        self.assertIn("C:/prefs/scripts/SkeldarAnim", text)
        self.assertIn("Install", text)

    def test_a_source_install_is_warned(self):
        """The case the confirmation exists for: a copy installed from the
        repository with work nobody has pushed."""
        text = up.confirm_text(record(A, source="C:/repo/SkeldarAnim",
                                      dirty=True),
                               record(D, log=(D,)), "C:/dest")
        self.assertIn("C:/repo/SkeldarAnim", text)
        self.assertIn("replaces", text)

    def test_history_not_reaching_the_install_is_said(self):
        text = up.confirm_text(record(A), record(D, log=(D, C)), "C:/dest")
        self.assertIn("not in the published history", text)


class ArchiveProblems(unittest.TestCase):

    def test_a_complete_archive_is_clean(self):
        names = ["SkeldarAnim/", "SkeldarAnim/install.py",
                 "SkeldarAnim/version.json", "SkeldarAnim/maya_hub.py"]
        self.assertEqual(up.archive_problems(names), [])

    def test_the_installer_and_the_record_are_required(self):
        problems = up.archive_problems(["SkeldarAnim/maya_hub.py"])
        self.assertEqual(len(problems), 2)
        self.assertTrue(any("install.py" in p for p in problems))
        self.assertTrue(any("version.json" in p for p in problems))

    def test_a_path_leaving_the_folder_is_refused(self):
        names = ["SkeldarAnim/install.py", "SkeldarAnim/version.json",
                 "SkeldarAnim/../../evil.py", "/abs.py"]
        problems = up.archive_problems(names)
        self.assertEqual(len(problems), 2)


# ---------------------------------------------------------------- network

class FakeResponse(object):
    def __init__(self, body, length=True):
        self.stream = io.BytesIO(body)
        self.headers = {"Content-Length": str(len(body))} if length else {}

    def read(self, size=-1):
        return self.stream.read(size)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def opener_for(files):
    """`_open` over a dict url -> bytes; anything else is GitHub's 404."""
    def _open(url, timeout=None):
        if isinstance(files.get(url), Exception):
            raise files[url]
        if url not in files:
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)
        return FakeResponse(files[url])
    return _open


class Network(unittest.TestCase):

    def setUp(self):
        self.saved = up._open
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        up._open = self.saved
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_fetch_text(self):
        up._open = opener_for({"u": b"hello"})
        self.assertEqual(up.fetch_text("u"), "hello")

    def test_a_404_is_not_published(self):
        up._open = opener_for({})
        with self.assertRaises(up.NotPublished):
            up.fetch_text("u")

    def test_no_network_is_an_update_error(self):
        up._open = opener_for({"u": urllib.error.URLError("no route")})
        with self.assertRaises(up.UpdateError) as caught:
            up.fetch_text("u")
        self.assertIn("no route", str(caught.exception))

    def test_download_writes_the_whole_file_and_reports_progress(self):
        body = os.urandom(up.CHUNK * 2 + 17)
        up._open = opener_for({"z": body})
        seen = []
        path = os.path.join(self.tmp, "a.zip")
        size = up.download("z", path, lambda done, total: seen.append(
            (done, total)))
        with open(path, "rb") as handle:
            self.assertEqual(handle.read(), body)
        self.assertEqual(size, len(body))
        self.assertEqual(seen[-1], (len(body), len(body)))
        self.assertEqual(len(seen), 3)

    def test_a_cancelled_download_leaves_no_file(self):
        up._open = opener_for({"z": b"x" * (up.CHUNK * 3)})
        path = os.path.join(self.tmp, "a.zip")
        with self.assertRaises(up.Cancelled):
            up.download("z", path, lambda done, total: False)
        self.assertFalse(os.path.exists(path))


# ------------------------------------------------------------ the archive

def write_build(path, commit, installer=None, extra=None):
    """A miniature build: install.py, version.json, one module."""
    installer = installer or (
        "import os\n"
        "CALLS = []\n"
        "def install(dropped=None, quiet=False):\n"
        "    CALLS.append((dropped, quiet))\n"
        "    return os.path.dirname(dropped)\n")
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("SkeldarAnim/install.py", installer)
        zf.writestr("SkeldarAnim/version.json", json.dumps(record(commit)))
        zf.writestr("SkeldarAnim/maya_hub.py", "# hub\n")
        for name, text in (extra or {}).items():
            zf.writestr(name, text)


class Unpack(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.zip = os.path.join(self.tmp, "b.zip")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_the_folder_and_its_record(self):
        write_build(self.zip, C)
        folder, rec = up.unpack(self.zip, os.path.join(self.tmp, "x"))
        self.assertEqual(os.path.basename(folder), "SkeldarAnim")
        self.assertTrue(os.path.isfile(os.path.join(folder, "install.py")))
        self.assertEqual(rec["commit"], C)

    def test_not_a_zip(self):
        with open(self.zip, "wb") as handle:
            handle.write(b"<html>not found</html>")
        with self.assertRaises(up.UpdateError):
            up.unpack(self.zip, os.path.join(self.tmp, "x"))

    def test_an_archive_without_its_installer_is_refused(self):
        with zipfile.ZipFile(self.zip, "w") as zf:
            zf.writestr("SkeldarAnim/version.json", json.dumps(record(C)))
        with self.assertRaises(up.UpdateError):
            up.unpack(self.zip, os.path.join(self.tmp, "x"))
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "x")))


class RunInstaller(unittest.TestCase):
    """The DOWNLOADED install.py runs, loaded by path, never the running
    session's `install`: a new build may change the payload."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        sys.modules.pop(up.INSTALLER_MODULE, None)

    def test_it_calls_install_quietly_with_its_own_path(self):
        zip_path = os.path.join(self.tmp, "b.zip")
        write_build(zip_path, C)
        folder, _ = up.unpack(zip_path, os.path.join(self.tmp, "x"))
        before = sys.modules.get("install")
        up.run_installer(folder)
        module = sys.modules[up.INSTALLER_MODULE]
        dropped, quiet = module.CALLS[0]
        self.assertEqual(os.path.normcase(dropped),
                         os.path.normcase(os.path.join(folder, "install.py")))
        self.assertTrue(quiet)
        self.assertIs(sys.modules.get("install"), before)


# -------------------------------------------------------------- the press

class PressCmds(FakeUiCmds):
    """The recording cmds, plus what the press asks Maya for."""

    def __init__(self, app_dir):
        FakeUiCmds.__init__(self)
        self.app_dir = app_dir
        self.labels = {}
        self.progress = []

    def internalVar(self, **kwargs):
        return self.app_dir

    def text(self, name=None, **kwargs):
        self.calls.append(("text", (name,), kwargs))
        if kwargs.get("exists"):
            return name in self.labels
        if kwargs.get("edit"):
            self.labels[name] = kwargs.get("label")
            return name
        if name:
            self.labels[name] = kwargs.get("label", "")
        self.children.append(name or "text%d" % len(self.children))
        return name

    def progressWindow(self, *args, **kwargs):
        self.progress.append(kwargs)
        if kwargs.get("query"):
            return False
        return None


class Press(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.app = os.path.join(self.tmp, "maya") + "/"
        self.dest = os.path.join(self.app, "scripts", "SkeldarAnim")
        os.makedirs(self.dest)
        self.fake = PressCmds(self.app)
        self.saved = (up.cmds, up._open, up.run_installer, up.BASE_URL)
        up.cmds = self.fake
        up.BASE_URL = "https://example/"
        self.installed = []
        self.had_installer = []

        def installer(folder):
            self.installed.append(folder)
            self.had_installer.append(
                os.path.isfile(os.path.join(folder, "install.py")))
        up.run_installer = installer
        self.asked = []

    def tearDown(self):
        (up.cmds, up._open, up.run_installer, up.BASE_URL) = self.saved
        shutil.rmtree(self.tmp, ignore_errors=True)

    def install_record(self, rec):
        with open(os.path.join(self.dest, "version.json"), "w") as handle:
            json.dump(rec, handle)

    def publish(self, latest, zip_commit=None):
        zip_path = os.path.join(self.tmp, "published.zip")
        write_build(zip_path, zip_commit or latest["commit"])
        with open(zip_path, "rb") as handle:
            body = handle.read()
        up._open = opener_for({
            "https://example/version.json": json.dumps(latest).encode(),
            "https://example/SkeldarAnim.zip": body})

    def ask(self, answer):
        def _ask(message):
            self.asked.append(message)
            return answer
        return _ask

    def test_up_to_date_downloads_nothing_and_asks_nothing(self):
        self.install_record(record(A))
        self.publish(record(A))
        message = up.check_update(ask=self.ask(True))
        self.assertIn("Up to date", message)
        self.assertEqual(self.asked, [])
        self.assertEqual(self.installed, [])

    def test_up_to_date_lights_the_header_chip(self):
        said = []
        hub = types.ModuleType("maya_hub")
        hub.say = lambda message, state=None: said.append(state)
        saved = sys.modules.get("maya_hub")
        sys.modules["maya_hub"] = hub
        try:
            self.install_record(record(A))
            self.publish(record(A))
            up.check_update(ask=self.ask(True))
        finally:
            if saved is None:
                sys.modules.pop("maya_hub", None)
            else:
                sys.modules["maya_hub"] = saved
        self.assertEqual(said, ["ok"])

    def test_a_new_build_is_asked_about_then_installed(self):
        self.install_record(record(B))
        self.publish(record(D, log=(D, C, B)))
        message = up.check_update(ask=self.ask(True))
        self.assertEqual(len(self.asked), 1)
        self.assertIn("ddddddd", self.asked[0])
        self.assertEqual(len(self.installed), 1)
        self.assertEqual(self.had_installer, [True])
        self.assertIn("Updated to ddddddd", message)

    def test_the_temp_folder_is_removed_after_a_good_install(self):
        self.install_record(record(B))
        self.publish(record(D))
        up.check_update(ask=self.ask(True))
        self.assertFalse(os.path.exists(self.installed[0]))

    def test_a_copy_from_before_updates_is_offered_the_build(self):
        self.publish(record(D))
        up.check_update(ask=self.ask(True))
        self.assertEqual(len(self.installed), 1)

    def test_cancel_changes_nothing(self):
        self.install_record(record(B))
        self.publish(record(D))
        message = up.check_update(ask=self.ask(False))
        self.assertIn("nothing changed", message)
        self.assertEqual(self.installed, [])

    def test_nothing_published_changes_nothing(self):
        self.install_record(record(B))
        up._open = opener_for({})
        message = up.check_update(ask=self.ask(True))
        self.assertIn("No build is published", message)
        self.assertIn("nothing changed", message)
        self.assertEqual(self.asked, [])

    def test_no_network_changes_nothing(self):
        up._open = opener_for({"https://example/version.json":
                               urllib.error.URLError("offline")})
        message = up.check_update(ask=self.ask(True))
        self.assertIn("offline", message)
        self.assertIn("nothing changed", message)

    def test_a_damaged_download_changes_nothing(self):
        self.install_record(record(B))
        up._open = opener_for({
            "https://example/version.json": json.dumps(record(D)).encode(),
            "https://example/SkeldarAnim.zip": b"garbage"})
        message = up.check_update(ask=self.ask(True))
        self.assertIn("nothing changed", message)
        self.assertEqual(self.installed, [])

    def test_the_message_names_what_the_archive_carries(self):
        """A newer build published between the two requests: the zip is
        the truth, and it is newer still."""
        self.install_record(record(B))
        self.publish(record(C), zip_commit=D)
        message = up.check_update(ask=self.ask(True))
        self.assertIn("ddddddd", message)

    def test_a_failing_installer_keeps_the_build_and_names_it(self):
        self.install_record(record(B))
        self.publish(record(D))

        def broken(folder):
            self.installed.append(folder)
            raise OSError("access denied")
        up.run_installer = broken
        message = up.check_update(ask=self.ask(True))
        self.assertIn("access denied", message)
        self.assertIn("install.py", message)
        self.assertTrue(os.path.isdir(self.installed[0]))
        #  <work>/build/SkeldarAnim: kept for the animator, not for the suite
        shutil.rmtree(os.path.dirname(os.path.dirname(self.installed[0])),
                      ignore_errors=True)

    def test_the_hub_is_rebuilt_later_not_during_the_press(self):
        self.install_record(record(B))
        self.publish(record(D))
        up.check_update(ask=self.ask(True))
        self.assertEqual(len(self.fake.deferred), 1)

    def test_the_status_line_carries_the_answer(self):
        up.build_panel()
        self.install_record(record(A))
        self.publish(record(A))
        up.check_update(ask=self.ask(True))
        self.assertIn("Up to date", self.fake.labels[up.STATUS])

    def test_the_progress_window_is_closed(self):
        self.install_record(record(B))
        self.publish(record(D))
        up.check_update(ask=self.ask(True))
        self.assertTrue(any(p.get("endProgress") for p in self.fake.progress))


class Reopen(unittest.TestCase):
    """After the install the hub comes back from FRESH modules."""

    def test_the_hub_shows_the_update_section_and_the_message(self):
        shown, statuses = [], []

        class Hub(object):
            @staticmethod
            def show(key=None):
                shown.append(key)

        class Update(object):
            @staticmethod
            def refresh():
                statuses.append("refresh")

            @staticmethod
            def _status(message, state=None):
                statuses.append((message, state))

        modules = {"maya_hub": Hub, "maya_update": Update}
        up._reopen("Updated to x", importer=modules.__getitem__)
        self.assertEqual(shown, ["update"])
        #  "new" colours the skinned header's version chip (2026-09-28)
        self.assertEqual(statuses, ["refresh", ("Updated to x", "new")])


class TheHeaderIsTold(unittest.TestCase):
    """2026-09-28, the skin: the messages reach the hub's header too -- but
    only a hub already imported; a message is no reason to import one."""

    def setUp(self):
        self.saved_cmds = up.cmds
        self.saved_hub = sys.modules.get("maya_hub")
        up.cmds = PressCmds(tempfile.gettempdir() + "/")
        self.said = []
        hub = types.ModuleType("maya_hub")
        hub.say = lambda message, state=None: self.said.append((message,
                                                                state))
        self.hub = hub

    def tearDown(self):
        up.cmds = self.saved_cmds
        if self.saved_hub is None:
            sys.modules.pop("maya_hub", None)
        else:
            sys.modules["maya_hub"] = self.saved_hub

    def test_a_status_reaches_the_header(self):
        sys.modules["maya_hub"] = self.hub
        up._status("Update cancelled - nothing changed.")
        up._status("Up to date: aaaaaaa", state="ok")
        self.assertEqual(self.said, [
            ("Update cancelled - nothing changed.", None),
            ("Up to date: aaaaaaa", "ok")])

    def test_no_hub_imported_imports_none(self):
        sys.modules.pop("maya_hub", None)
        up._status("hello")
        self.assertNotIn("maya_hub", sys.modules)

    def test_a_broken_hub_does_not_break_the_status(self):
        def explode(message, state=None):
            raise RuntimeError("boom")
        self.hub.say = explode
        sys.modules["maya_hub"] = self.hub
        self.assertEqual(up._status("hello"), "hello")


class Panel(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.fake = PressCmds(self.tmp + "/")
        self.saved = up.cmds
        up.cmds = self.fake

    def tearDown(self):
        up.cmds = self.saved
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_the_line_the_button_and_the_status(self):
        up.build_panel()
        self.assertIn(up.INSTALLED, self.fake.children)
        self.assertIn(up.STATUS, self.fake.children)
        labels = [c[2].get("label") for c in self.fake.calls
                  if c[0] == "button"]
        self.assertEqual(labels, ["Check update"])
        self.assertEqual(self.fake.windows, {})

    def test_the_installed_line_reads_the_installed_record(self):
        dest = os.path.join(self.tmp, "scripts", "SkeldarAnim")
        os.makedirs(dest)
        with open(os.path.join(dest, "version.json"), "w") as handle:
            json.dump(record(A), handle)
        up.build_panel()
        self.assertIn("aaaaaaa", self.fake.labels[up.INSTALLED])
        self.assertNotIn("subject of a", self.fake.labels[up.INSTALLED])

    def test_show_window_opens_the_hub_on_its_section(self):
        import maya_hub
        asked = []
        saved = maya_hub.show
        maya_hub.show = lambda key=None: asked.append(key) or "hub"
        try:
            up.show_window()
        finally:
            maya_hub.show = saved
        self.assertEqual(asked, ["update"])


class Boundary(unittest.TestCase):

    def test_no_qt(self):
        script = (
            "import sys\n"
            "import maya_update\n"
            "print(';'.join(m for m in sys.modules if m.startswith('PySide')))\n")
        result = subprocess.run([sys.executable, "-c", script], cwd=PLUGIN,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "")

    def test_the_address_is_the_repository_s_latest_release(self):
        self.assertEqual(
            up.BASE_URL,
            "https://github.com/EugeneM23/MayaScripts/releases/latest/download/")


if __name__ == "__main__":
    unittest.main()
