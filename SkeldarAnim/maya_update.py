"""maya_update - Check update: the latest build from GitHub, one press.

The animator's ask (2026-09-28): «раздел update, кнопка Check update: при ее
нажатии мая пойдет в репозиторий на гит хабе и скачает сборку последней
версии, если сборка еще не установлена». Every push to the working branch
is built by GitHub Actions into a release carrying two assets,
`SkeldarAnim.zip` and `version.json`; this section reads the small one,
compares it with `<scripts>/SkeldarAnim/version.json`, says what is new,
asks, then downloads the archive and runs ITS installer.

    import maya_update; maya_update.show_window()     # the hub, on Update

`releases/latest/download/<asset>` is a plain URL that redirects to the
newest release's file: no REST API, no token, no hourly limit shared by
a studio behind one address. `cmds` and stdlib only.

Spec: docs/superpowers/specs/2026-09-28-update-button-design.md
"""

import importlib
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

import maya.cmds as cmds

import maya_hubcopy as hubcopy

REPO = "EugeneM23/MayaScripts"
BASE_URL = "https://github.com/{0}/releases/latest/download/".format(REPO)
ZIP_NAME = "SkeldarAnim.zip"
VERSION_NAME = "version.json"
TOP = "SkeldarAnim"

HUB_SECTION = "update"
INSTALLED = "skeldarUpdateInstalled"
STATUS = "skeldarUpdateStatus"

#  The downloaded installer's module name: never `install`, which may be
#  the running session's own (the installed folder carries one).
INSTALLER_MODULE = "skeldar_update_installer"

TIMEOUT = 30                    # seconds per socket read
CHUNK = 256 * 1024
LIMIT = 15                      # changes listed when the install is off the log
SUBJECT_WIDTH = 90

USER_AGENT = "SkeldarAnim-updater"


class UpdateError(Exception):
    """A refusal: said on the status line, nothing on disk changed."""


class NotPublished(UpdateError):
    """GitHub answered 404: no release yet, or the repository is private."""


class Cancelled(UpdateError):
    """The animator pressed Cancel on the progress window."""


# ------------------------------------------------------------------- pure

def parse_record(text):
    """A version.json's text as a dict with a commit, or UpdateError."""
    try:
        rec = json.loads(text)
    except ValueError:
        raise UpdateError("the published version record is not JSON")
    if not isinstance(rec, dict) or not rec.get("commit"):
        raise UpdateError("the published version record names no commit")
    return rec


def _cut(text, width):
    text = " ".join((text or "").split())
    if width and len(text) > width:
        return text[:width - 3].rstrip() + "..."
    return text


def describe(rec, width=SUBJECT_WIDTH, subject=True):
    """«bc51aee, 2026-09-25 14:07 - feat(...)» for a record. Pure.

    `subject=False` for the panel's lines: a subject wraps them past their
    height in a narrow dock (trap 67) and the dialog lists it anyway.
    """
    rec = rec or {}
    source = rec.get("source")
    short = rec.get("short") or (rec.get("commit") or "")[:7]
    if not short:
        return ("from the source folder (no git record)" if source
                else "unknown - installed before updates existed")
    text = short
    date = (rec.get("date") or "")[:16].replace("T", " ")
    if date:
        text += ", " + date
    title = _cut(rec.get("subject"), width) if subject else ""
    if title:
        text += " - " + title
    if source:
        text += (" (from the source folder, uncommitted changes)"
                 if rec.get("dirty") else " (from the source folder)")
    return text


def is_current(installed, latest):
    """The same known commit on both sides. An unknown install never is."""
    mine = (installed or {}).get("commit")
    return bool(mine) and mine == (latest or {}).get("commit")


def changes_since(installed, latest, limit=LIMIT):
    """`(entries, found)`: the log entries newer than the installed commit,
    newest first. When the installed commit is not in the published log
    (older than it reaches, or unknown) the newest `limit` and False."""
    log = [tuple(entry) for entry in (latest or {}).get("log") or []]
    mine = (installed or {}).get("commit")
    for index, (sha, _subject) in enumerate(log):
        if mine and sha == mine:
            return log[:index], True
    return log[:limit], False


def confirm_text(installed, latest, dest):
    """The dialog's message: both builds, what is new, what gets replaced."""
    lines = ["Installed:  " + describe(installed),
             "Available:  " + describe(latest), ""]
    entries, found = changes_since(installed, latest)
    if entries:
        lines.append("What's new:")
        lines.extend("  {0}  {1}".format(sha[:7], _cut(subject, 70))
                     for sha, subject in entries)
    if not found and (installed or {}).get("commit"):
        lines.append("  (the installed build is not in the published "
                     "history - the newest changes are shown)")
    source = (installed or {}).get("source")
    if source:
        lines += ["", "This copy was installed from the source folder",
                  "  " + source,
                  "and the update replaces it with the published build."]
    lines += ["", "The update replaces " + dest.replace("\\", "/"),
              "and rebuilds the SkeldarAnim shelf. Install it now?"]
    return "\n".join(lines)


def archive_problems(names):
    """What is wrong with an archive's member list, as sentences. Pure."""
    problems = []
    for need in ("install.py", VERSION_NAME):
        if "{0}/{1}".format(TOP, need) not in names:
            problems.append("no {0}/{1} in the archive".format(TOP, need))
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


def _reason(exc):
    return str(getattr(exc, "reason", None) or exc)


def fetch_text(url):
    """The body of `url` as text. NotPublished on 404, UpdateError otherwise."""
    try:
        with _open(url) as response:
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise NotPublished(url)
        raise UpdateError("GitHub answered {0} {1}".format(exc.code,
                                                           exc.reason))
    except (urllib.error.URLError, socket.timeout, OSError) as exc:
        raise UpdateError("could not reach GitHub: " + _reason(exc))


def download(url, path, progress=None):
    """`url` into `path` in chunks; `progress(done, total)` after each, and
    False from it cancels (the partial file is removed). Returns bytes."""
    done = 0
    try:
        with _open(url) as response, open(path, "wb") as out:
            total = int(response.headers.get("Content-Length") or 0)
            while True:
                chunk = response.read(CHUNK)
                if not chunk:
                    break
                out.write(chunk)
                done += len(chunk)
                if progress is not None and progress(done, total) is False:
                    raise Cancelled("download cancelled")
    except Cancelled:
        _remove(path)
        raise
    except urllib.error.HTTPError as exc:
        _remove(path)
        if exc.code == 404:
            raise NotPublished(url)
        raise UpdateError("GitHub answered {0} {1}".format(exc.code,
                                                           exc.reason))
    except (urllib.error.URLError, socket.timeout, OSError) as exc:
        _remove(path)
        raise UpdateError("the download failed: " + _reason(exc))
    return done


def _remove(path):
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


# ------------------------------------------------------------ the archive

def unpack(zip_path, into):
    """The archive into `into`. Returns `(<into>/SkeldarAnim, its record)`.
    Everything is checked before anything is written."""
    try:
        with zipfile.ZipFile(zip_path) as archive:
            bad = archive.testzip()
            if bad:
                raise UpdateError("the archive is damaged at " + bad)
            problems = archive_problems(archive.namelist())
            if problems:
                raise UpdateError("; ".join(problems))
            archive.extractall(into)
    except zipfile.BadZipFile:
        raise UpdateError("the download is not a zip archive")
    folder = os.path.join(into, TOP)
    with open(os.path.join(folder, VERSION_NAME), encoding="utf-8") as handle:
        return folder, parse_record(handle.read())


def run_installer(folder):
    """The DOWNLOADED install.py, loaded by path, run quietly.

    Not the session's `install`: a new build may change the payload, and
    the old whitelist would copy yesterday's list of files. Quiet, because
    its confirm dialog would sit on top of ours.
    """
    path = os.path.join(folder, "install.py")
    spec = importlib.util.spec_from_file_location(INSTALLER_MODULE, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[INSTALLER_MODULE] = module
    spec.loader.exec_module(module)
    return module.install(path, quiet=True)


# ------------------------------------------------------------------ scene

def installed_dir():
    """What the update replaces: the installer's own destination."""
    return os.path.join(cmds.internalVar(userAppDir=True), "scripts", TOP)


def read_record(folder):
    """The version.json in `folder`, or {} when there is none."""
    try:
        with open(os.path.join(folder, VERSION_NAME),
                  encoding="utf-8") as handle:
            rec = json.load(handle)
    except (OSError, ValueError):
        return {}
    return rec if isinstance(rec, dict) else {}


class _Progress(object):
    """Maya's progress window, opened on the first chunk, cancellable."""

    def __init__(self):
        self.open = False

    def __call__(self, done, total):
        mb = done / 1048576.0
        status = ("Downloading SkeldarAnim: {0:.1f} of {1:.1f} MB".format(
            mb, total / 1048576.0) if total
            else "Downloading SkeldarAnim: {0:.1f} MB".format(mb))
        value = int(100 * done / total) if total else 0
        if not self.open:
            cmds.progressWindow(title="SkeldarAnim update", progress=value,
                                maxValue=100, status=status,
                                isInterruptable=True)
            self.open = True
        else:
            cmds.progressWindow(edit=True, progress=value, status=status)
        return not cmds.progressWindow(query=True, isCancelled=True)

    def close(self):
        if self.open:
            cmds.progressWindow(endProgress=True)
            self.open = False


def _ask(message):
    answer = cmds.confirmDialog(title="SkeldarAnim update", message=message,
                                button=["Install", "Cancel"],
                                defaultButton="Install",
                                cancelButton="Cancel", dismissString="Cancel")
    return answer == "Install"


def check_update(ask=None):
    """The press. Returns the message it put on the status line.

    `ask(message) -> bool` defaults to a confirmDialog; a scripted run
    passes its own, because a modal over the command port blocks Maya.
    """
    dest = installed_dir()
    installed = read_record(dest)
    try:
        latest = parse_record(fetch_text(BASE_URL + VERSION_NAME))
    except NotPublished:
        return _status("No build is published at github.com/{0} yet (or the "
                       "repository is private) - nothing changed.".format(
                           REPO))
    except UpdateError as exc:
        return _status("{0} - nothing changed.".format(exc))
    if is_current(installed, latest):
        return _status("Up to date: " + describe(latest, subject=False),
                       state="ok")
    if not (ask or _ask)(confirm_text(installed, latest, dest)):
        return _status("Update cancelled - nothing changed.")
    work = tempfile.mkdtemp(prefix="skeldar_update_")
    progress = _Progress()
    try:
        archive = os.path.join(work, ZIP_NAME)
        download(BASE_URL + ZIP_NAME, archive, progress)
        folder, rec = unpack(archive, os.path.join(work, "build"))
    except UpdateError as exc:
        shutil.rmtree(work, ignore_errors=True)
        return _status("{0} - nothing changed.".format(exc))
    finally:
        progress.close()
    try:
        #  2026-10-09: the installer is the hub's business - it purges the
        #  modules, and rebuilds the hub through its own deferred call. Run
        #  inside a popup's scope, that call would make the hub's controls
        #  under the popup's prefix, so it runs in the hub's names.
        with hubcopy.entered(None):
            run_installer(folder)
    except Exception as exc:                                 # noqa: BLE001
        print(traceback.format_exc())
        return _status("The installer failed: {0}. The build is unpacked at "
                       "{1} - drag its install.py into Maya to finish.".format(
                           exc, folder.replace("\\", "/")))
    shutil.rmtree(work, ignore_errors=True)
    message = "Updated to " + describe(rec, subject=False)
    #  The installer purged our modules; this function is the old module's.
    #  The hub is rebuilt from the new ones once this callback has returned
    #  - the rebuild deletes the layout holding the button pressed.
    cmds.evalDeferred(lambda: _reopen(message), lowestPriority=True)
    return _status(message)


def _reopen(message, importer=importlib.import_module):
    """The hub on Update, from FRESH modules, with the message on its line.

    2026-10-09: deferred from a press, so it can run inside a popup's scope
    (`cmds.evalDeferred` keeps the scope that made the call). Showing the hub
    builds it, and the hub's controls are made under the hub's own names -
    asked here, not inherited from the press.
    """
    with hubcopy.entered(None):
        importer("maya_hub").show(HUB_SECTION)
        fresh = importer("maya_update")
        fresh.refresh()
        fresh._status(message, state="new")


# -------------------------------------------------------------------- UI

def _status(message, state=None):
    """The section's status line; `state` "ok" / "new" colours the skinned
    hub's version chip. With no section built (a skin without the Update
    card) the message goes to the hub's header line instead. Only a hub
    already imported is told: a message is no reason to import one."""
    print("SkeldarAnim update: " + message)
    #  2026-10-09, the popups. A press in a popup's copy writes the copy's
    #  line (`exists` is asked through the copy's own name - a creation
    #  command, so a name the copy did not make cannot reach the hub's line).
    #  Two relays to the hub are deliberate: the header's update jump takes
    #  the state (ok / new) whichever card checked, and a popup closed before
    #  its answer leaves the answer on the header's line rather than nowhere.
    shown = False
    try:
        if cmds.text(STATUS, exists=True):
            cmds.text(STATUS, edit=True, label=message)
            shown = True
            #  2026-10-08: the skin's one message line carries it too (this
            #  writer shows nothing in the viewport: viewport False)
            import maya_hubstyle   # stdlib
            maya_hubstyle.tell(STATUS, message, viewport=False)
    except Exception:                                        # noqa: BLE001
        pass
    hub = sys.modules.get("maya_hub")
    if hub is not None:
        try:
            if shown:
                if state is not None:
                    hub.chip_state(state)
            else:
                hub.say(message, state=state)
        except Exception:                                    # noqa: BLE001
            print(traceback.format_exc())
    return message


def refresh():
    """The installed line, read from the installed folder."""
    if cmds.text(INSTALLED, exists=True):
        cmds.text(INSTALLED, edit=True,
                  label="Installed: " + describe(read_record(installed_dir()),
                                                 subject=False))


def _press(*_args):
    """The Check update press: the Update card's button, the hub's menu, a
    popup's copy of the card (2026-10-09).

    From a popup the check runs at the next idle, not inside the button's own
    click: an install destroys the open popups (install.py's _destroy_popups)
    - the one that pressed included - and a widget deleted inside its own
    clicked signal is a crash waiting to happen. The deferred call keeps the
    popup's scope (maya_hubcopy wraps it), so the answer is on the popup's line.
    """
    if hubcopy.current() is not None:
        cmds.evalDeferred(_press_now, lowestPriority=True)
        return
    _press_now()


def _press_now():
    try:
        check_update()
    except Exception as exc:                                 # noqa: BLE001
        print(traceback.format_exc())
        _status("Check update failed: {0}".format(exc))


def build_panel():
    """The installed build, the button, a status line (the hub's section)."""
    import maya_hubstyle as hubstyle   # stdlib
    column = cmds.columnLayout(adjustableColumn=True,
                               rowSpacing=hubstyle.row_spacing(6),
                               columnOffset=("both", hubstyle.pick(0, 8)))
    #  the card's subtitle in the skin (2026-09-28, the card came back); one
    #  line there (2026-10-08, the compact header), two in the classic hub
    hubstyle.mark(cmds.text(INSTALLED, label="Installed:", align="left",
                            wordWrap=hubstyle.pick(False, True),
                            height=hubstyle.pick(18, 36)), "subtitle")
    hubstyle.mark(cmds.button(
        label="Check update", height=hubstyle.height("button", 36),
        backgroundColor=(0.45, 0.60, 0.70),
        annotation="Compare with the latest build on github.com/{0} and "
                   "install it".format(REPO),
        command=_press), "primary", "refresh")
    #  Three lines: the no-build refusal wraps to three in a narrow dock.
    hubstyle.mark(cmds.text(STATUS, label="", align="left", wordWrap=True,
                            height=54), "status")
    cmds.setParent("..")
    refresh()
    return column


def is_open():
    return bool(cmds.text(STATUS, exists=True))


def show_window():
    """The hub, on the Update section."""
    import maya_hub
    return maya_hub.show(HUB_SECTION)
