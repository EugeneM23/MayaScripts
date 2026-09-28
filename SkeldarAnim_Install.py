"""SkeldarAnim_Install.py - drag this ONE file into an open Maya viewport.

It downloads the latest SkeldarAnim build from GitHub's Releases
(github.com/EugeneM23/MayaScripts), unpacks it to a temporary folder and runs
that build's own install.py: the plugin lands in <prefs>/scripts/SkeldarAnim,
the SkeldarAnim shelf is built, the SkeldarAnim window opens. The open scene
is not touched. Dropping it again updates to the latest build, the same as
the window's Update > Check update.

    Download: https://github.com/EugeneM23/MayaScripts/releases/latest/download/SkeldarAnim_Install.py

Or paste into the Script Editor (Python tab):

    exec(open(r"<path>/SkeldarAnim_Install.py", encoding="utf-8").read())

Stdlib only at import - at drop time nothing of ours is on sys.path, and
maya.cmds is imported inside the functions that run in Maya.

Spec: docs/superpowers/specs/2026-09-28-setup-script-design.md
"""

import importlib.util
import json
import os
import shutil
import socket
import sys
import tempfile
import traceback
import urllib.error
import urllib.request
import zipfile

REPO = "EugeneM23/MayaScripts"
ZIP_URL = ("https://github.com/{0}/releases/latest/download/"
           "SkeldarAnim.zip".format(REPO))
TOP = "SkeldarAnim"

#  Never `install`: the Maya this runs in may hold an installed copy's own.
INSTALLER_MODULE = "skeldar_setup_installer"

TIMEOUT = 30
CHUNK = 256 * 1024
USER_AGENT = "SkeldarAnim-setup"
TITLE = "SkeldarAnim setup"


class SetupError(Exception):
    """A refusal before anything was installed."""


# ------------------------------------------------------------------- pure

def archive_problems(names):
    """What is wrong with an archive's member list, as sentences."""
    problems = []
    if TOP + "/install.py" not in names:
        problems.append("no {0}/install.py in the archive".format(TOP))
    for name in names:
        parts = name.replace("\\", "/").split("/")
        if name.startswith(("/", "\\")) or ".." in parts or ":" in parts[0]:
            problems.append("a path outside the archive: " + name)
    return problems


# ---------------------------------------------------------------- network

def _open(url, timeout=TIMEOUT):
    """The one function that touches the network."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    return urllib.request.urlopen(request, timeout=timeout)


def download(url, path, progress=None):
    """`url` into `path` in chunks; `progress(done, total)` returning False
    cancels. SetupError for anything that is not a whole file."""
    try:
        with _open(url) as response, open(path, "wb") as out:
            total = int(response.headers.get("Content-Length") or 0)
            done = 0
            while True:
                chunk = response.read(CHUNK)
                if not chunk:
                    return done
                out.write(chunk)
                done += len(chunk)
                if progress is not None and progress(done, total) is False:
                    raise SetupError("download cancelled")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise SetupError("no build is published at github.com/{0} "
                             "yet".format(REPO))
        raise SetupError("GitHub answered {0} {1}".format(exc.code,
                                                          exc.reason))
    except (urllib.error.URLError, socket.timeout, OSError) as exc:
        raise SetupError("could not reach GitHub: {0}".format(
            getattr(exc, "reason", None) or exc))


def unpack(zip_path, into):
    """The archive into `into`; returns `(<into>/SkeldarAnim, its record)`."""
    try:
        with zipfile.ZipFile(zip_path) as archive:
            bad = archive.testzip()
            if bad:
                raise SetupError("the archive is damaged at " + bad)
            problems = archive_problems(archive.namelist())
            if problems:
                raise SetupError("; ".join(problems))
            archive.extractall(into)
    except zipfile.BadZipFile:
        raise SetupError("the download is not a zip archive")
    folder = os.path.join(into, TOP)
    try:
        with open(os.path.join(folder, "version.json"),
                  encoding="utf-8") as handle:
            record = json.load(handle)
    except (OSError, ValueError):
        record = {}
    return folder, record if isinstance(record, dict) else {}


def run_installer(folder, quiet):
    """The DOWNLOADED install.py, loaded by path. Returns where it installed."""
    path = os.path.join(folder, "install.py")
    spec = importlib.util.spec_from_file_location(INSTALLER_MODULE, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[INSTALLER_MODULE] = module
    spec.loader.exec_module(module)
    return module.install(path, quiet=quiet)


# ------------------------------------------------------------------- Maya

class _Progress(object):
    """Maya's progress window, opened on the first chunk, cancellable."""

    def __init__(self, cmds):
        self.cmds = cmds
        self.open = False

    def __call__(self, done, total):
        status = "Downloading SkeldarAnim: {0:.1f} of {1:.1f} MB".format(
            done / 1048576.0, total / 1048576.0) if total else \
            "Downloading SkeldarAnim: {0:.1f} MB".format(done / 1048576.0)
        value = int(100 * done / total) if total else 0
        if not self.open:
            self.cmds.progressWindow(title=TITLE, progress=value,
                                     maxValue=100, status=status,
                                     isInterruptable=True)
            self.open = True
        else:
            self.cmds.progressWindow(edit=True, progress=value,
                                     status=status)
        return not self.cmds.progressWindow(query=True, isCancelled=True)

    def close(self):
        if self.open:
            self.cmds.progressWindow(endProgress=True)
            self.open = False


def _maya_ui():
    """The progress window, or None outside a Maya with a UI."""
    try:
        import maya.cmds as cmds
        if cmds.about(batch=True):
            return None
        return _Progress(cmds)
    except Exception:                                        # noqa: BLE001
        return None


def _dialog(message):
    try:
        import maya.cmds as cmds
        cmds.confirmDialog(title=TITLE, message=message, button=["OK"])
    except Exception:                                        # noqa: BLE001
        pass


def _open_hub(dest):
    """The SkeldarAnim window, from the copy just installed."""
    dest = (dest or "").replace("\\", "/")
    if dest and dest not in [p.replace("\\", "/") for p in sys.path]:
        sys.path.insert(0, dest)
    try:
        import importlib
        importlib.import_module("maya_hub").show()
    except Exception:                                        # noqa: BLE001
        print(traceback.format_exc())


# -------------------------------------------------------------------- run

def run(quiet=False, work_root=None, ask=None):
    """Download, unpack, install, open the window. Returns the message.

    `quiet` skips every dialog (the installer's too) - a scripted run over
    the command port must never raise a modal. Dropped by hand, the
    installer's own dialog reports the install, and a refusal is said in
    `ask` (a confirmDialog by default).
    """
    say = ask or _dialog
    work = tempfile.mkdtemp(prefix="skeldar_setup_",
                            dir=work_root or tempfile.gettempdir())
    progress = _maya_ui()
    try:
        archive = os.path.join(work, "SkeldarAnim.zip")
        download(ZIP_URL, archive, progress)
        folder, record = unpack(archive, os.path.join(work, "build"))
    except SetupError as exc:
        shutil.rmtree(work, ignore_errors=True)
        return _refuse("{0} - nothing was installed.".format(exc), quiet,
                       say)
    finally:
        if progress is not None:
            progress.close()
    try:
        dest = run_installer(folder, quiet)
    except Exception as exc:                                 # noqa: BLE001
        print(traceback.format_exc())
        return _refuse("The installer failed: {0}. The build is unpacked at "
                       "{1} - drag its install.py into Maya to finish.".format(
                           exc, folder.replace("\\", "/")), quiet, say)
    shutil.rmtree(work, ignore_errors=True)
    _open_hub(dest)
    message = "SkeldarAnim {0} installed into {1}".format(
        record.get("short") or "(unknown build)",
        (dest or "").replace("\\", "/"))
    print(TITLE + ": " + message)
    return message


def _refuse(message, quiet, say):
    print(TITLE + ": " + message)
    if not quiet:
        say(message)
    return message


def onMayaDroppedPythonFile(*args):
    run()


if __name__ == "__main__":
    run()
