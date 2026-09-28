"""SkeldarAnim_Install.py: one file dropped into Maya installs the plugin
from GitHub (2026-09-28, «скрипт который можно кинуть в открытую сцену и он
установит наш плагин с гит хаба»).

It must stand alone - at drop time nothing of ours is on sys.path - so the
tests load it by path, fake the network and the installer, and never reach
GitHub or the prefs folder.
"""

import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import urllib.error
import zipfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(REPO, "SkeldarAnim_Install.py")


def load():
    spec = importlib.util.spec_from_file_location("skeldar_setup_under_test",
                                                  PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


setup = load()


class FakeResponse(object):
    def __init__(self, body):
        self.stream = io.BytesIO(body)
        self.headers = {"Content-Length": str(len(body))}

    def read(self, size=-1):
        return self.stream.read(size)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def opener_for(files):
    def _open(url, timeout=None):
        if isinstance(files.get(url), Exception):
            raise files[url]
        if url not in files:
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)
        return FakeResponse(files[url])
    return _open


def build_zip(installer=None, record=True):
    buf = io.BytesIO()
    installer = installer or (
        "import os\n"
        "CALLS = []\n"
        "def install(dropped=None, quiet=False):\n"
        "    CALLS.append((dropped, quiet))\n"
        "    return os.path.join(os.path.dirname(dropped), 'installed')\n")
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("SkeldarAnim/install.py", installer)
        if record:
            zf.writestr("SkeldarAnim/version.json",
                        json.dumps({"commit": "a" * 40, "short": "aaaaaaa"}))
        zf.writestr("SkeldarAnim/maya_hub.py", "# hub\n")
    return buf.getvalue()


class Standalone(unittest.TestCase):

    def test_it_lives_beside_the_plugin_not_in_it(self):
        self.assertTrue(os.path.isfile(PATH))
        import install
        self.assertNotIn("SkeldarAnim_Install.py", install.payload())

    def test_importing_it_needs_neither_maya_nor_our_code(self):
        """Maya calls onMayaDroppedPythonFile on a file it imports cold."""
        script = (
            "import importlib.util, sys\n"
            "spec = importlib.util.spec_from_file_location('s', %r)\n"
            "m = importlib.util.module_from_spec(spec)\n"
            "spec.loader.exec_module(m)\n"
            "bad = [n for n in sys.modules if n.startswith('maya') or\n"
            "       n in ('install', 'maya_update', 'maya_hub')]\n"
            "print(';'.join(bad))\n" % PATH)
        result = subprocess.run([sys.executable, "-c", script],
                                cwd=tempfile.gettempdir(),
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "")

    def test_it_answers_maya_s_drop(self):
        self.assertTrue(callable(setup.onMayaDroppedPythonFile))

    def test_the_address_is_the_latest_release(self):
        self.assertEqual(
            setup.ZIP_URL,
            "https://github.com/EugeneM23/MayaScripts/releases/latest/"
            "download/SkeldarAnim.zip")


class Archive(unittest.TestCase):

    def test_a_build_is_clean(self):
        self.assertEqual(setup.archive_problems(
            ["SkeldarAnim/install.py", "SkeldarAnim/version.json"]), [])

    def test_the_installer_is_required(self):
        self.assertTrue(setup.archive_problems(["SkeldarAnim/x.py"]))

    def test_a_path_out_of_the_folder_is_refused(self):
        self.assertTrue(setup.archive_problems(
            ["SkeldarAnim/install.py", "SkeldarAnim/../../evil.py"]))


class Run(unittest.TestCase):
    """The press, with the network, Maya and the installer faked."""

    def setUp(self):
        self.saved = (setup._open, setup._maya_ui, setup._open_hub)
        self.dialogs, self.hub = [], []
        setup._maya_ui = lambda: None          # no progress window
        setup._open_hub = lambda dest: self.hub.append(dest)
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        (setup._open, setup._maya_ui, setup._open_hub) = self.saved
        sys.modules.pop(setup.INSTALLER_MODULE, None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def serve(self, body):
        setup._open = opener_for({setup.ZIP_URL: body})

    def test_it_downloads_unpacks_and_runs_the_downloaded_installer(self):
        self.serve(build_zip())
        message = setup.run(quiet=True, work_root=self.tmp)
        module = sys.modules[setup.INSTALLER_MODULE]
        dropped, quiet = module.CALLS[0]
        self.assertTrue(dropped.replace("\\", "/").endswith(
            "SkeldarAnim/install.py"))
        self.assertTrue(quiet)
        self.assertIn("aaaaaaa", message)
        self.assertEqual(len(self.hub), 1)

    def test_a_drop_lets_the_installer_speak(self):
        """Dropped by hand, the installer's own dialog says what happened."""
        self.serve(build_zip())
        setup.run(quiet=False, work_root=self.tmp, ask=lambda text: None)
        dropped, quiet = sys.modules[setup.INSTALLER_MODULE].CALLS[0]
        self.assertFalse(quiet)

    def test_the_download_is_cleaned_up(self):
        self.serve(build_zip())
        setup.run(quiet=True, work_root=self.tmp)
        self.assertEqual(os.listdir(self.tmp), [])

    def test_nothing_published_installs_nothing(self):
        setup._open = opener_for({})
        message = setup.run(quiet=True, work_root=self.tmp)
        self.assertIn("nothing was installed", message)
        self.assertNotIn(setup.INSTALLER_MODULE, sys.modules)
        self.assertEqual(self.hub, [])

    def test_no_network_installs_nothing(self):
        setup._open = opener_for({setup.ZIP_URL:
                                  urllib.error.URLError("offline")})
        message = setup.run(quiet=True, work_root=self.tmp)
        self.assertIn("offline", message)
        self.assertIn("nothing was installed", message)

    def test_a_damaged_download_installs_nothing(self):
        self.serve(b"<html>rate limited</html>")
        message = setup.run(quiet=True, work_root=self.tmp)
        self.assertIn("nothing was installed", message)
        self.assertNotIn(setup.INSTALLER_MODULE, sys.modules)

    def test_a_failing_installer_keeps_the_build_and_names_it(self):
        self.serve(build_zip(installer=(
            "def install(dropped=None, quiet=False):\n"
            "    raise OSError('access denied')\n")))
        message = setup.run(quiet=True, work_root=self.tmp)
        self.assertIn("access denied", message)
        self.assertIn("install.py", message)
        self.assertTrue(os.listdir(self.tmp))

    def test_a_refusal_is_said_in_a_dialog_when_dropped(self):
        setup._open = opener_for({})
        said = []
        setup.run(quiet=False, work_root=self.tmp, ask=said.append)
        self.assertEqual(len(said), 1)
        self.assertIn("nothing was installed", said[0])


class TheReleaseCarriesIt(unittest.TestCase):

    def test_every_build_attaches_the_file(self):
        with open(os.path.join(REPO, ".github", "workflows", "build.yml"),
                  encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("SkeldarAnim_Install.py", text)


if __name__ == "__main__":
    unittest.main()
