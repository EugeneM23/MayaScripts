r"""SkeldarAnim_Cascadeur_Install.py - the SkeldarAnim bridge for Cascadeur.

Run it once in Cascadeur's Python console (no Maya needed):

    exec(open(r"<path>\SkeldarAnim_Cascadeur_Install.py", encoding="utf-8").read())

It downloads the latest SkeldarAnim build from GitHub's Releases, unpacks it,
copies the plugin to  %USERPROFILE%\Documents\SkeldarAnim  and adds that
folder and the skeldar_cascadeur package to Cascadeur's settings.json (a
backup is written first). Restart Cascadeur afterwards: the menu entry
SkeldarAnim > Bridge appears then.

Stdlib only. The open scene is not touched. A folder at the install path that
is not ours is refused and left alone. Spec:
docs/superpowers/specs/2026-10-09-cascadeur-bridge-design.md
"""

import json
import os
import shutil
import tempfile
import urllib.request
import zipfile

REPO = "EugeneM23/MayaScripts"
ZIP_URL = "https://github.com/{0}/releases/latest/download/SkeldarAnim.zip".format(REPO)
TOP = "SkeldarAnim"
PACKAGE = "skeldar_cascadeur"
MARKER = PACKAGE + "/bridge.py"
BACKUP_SUFFIX = ".skeldar-backup"
USER_AGENT = "SkeldarAnim-cascadeur-setup"
TIMEOUT = 30
CHUNK = 256 * 1024


class SetupError(Exception):
    """A refusal before anything was changed."""


# ---------------------------------------------------------------- pure

def archive_problems(names):
    """What is wrong with the archive's member names, as sentences."""
    problems = []
    members = [name.replace("\\", "/") for name in names]
    if TOP + "/" + MARKER not in members:
        problems.append("the archive holds no {0}/{1} module".format(TOP, MARKER))
    for name in names:
        parts = name.replace("\\", "/").split("/")
        if name.startswith(("/", "\\")) or ".." in parts or ":" in parts[0]:
            problems.append("a path outside the archive: " + name)
    return problems


def _same_path(a, b):
    def norm(text):
        return os.path.normcase(os.path.normpath(text)).rstrip("\\/")
    return norm(a) == norm(b)


def settings_edit(text, install_dir, package):
    """(new_text, changed): the settings with the install folder on Python.Path
    and the package on Python.Scripts. Every other key is kept. Raises
    SetupError when the text is not a JSON object."""
    try:
        data = json.loads(text) if text.strip() else {}
    except ValueError:
        raise SetupError("settings.json is not valid JSON - nothing changed")
    if not isinstance(data, dict):
        raise SetupError("settings.json is not a JSON object - nothing changed")
    python = data.get("Python")
    if not isinstance(python, dict):
        python = {}
        data["Python"] = python
    changed = False
    paths = list(python.get("Path") or [])
    if not any(_same_path(p, install_dir) for p in paths if isinstance(p, str)):
        paths.append(install_dir)
        changed = True
    python["Path"] = paths
    scripts = list(python.get("Scripts") or [])
    if package not in scripts:
        scripts.append(package)
        changed = True
    python["Scripts"] = scripts
    if "Commands" not in python:
        python["Commands"] = ["commands"]
    return json.dumps(data, indent=4, ensure_ascii=False) + "\n", changed


def is_ours(folder):
    """True when the folder is missing or holds our marker module."""
    return (not os.path.exists(folder)) or os.path.isfile(
        os.path.join(folder, *MARKER.split("/")))


# ------------------------------------------------------------ the world

def default_install_dir():
    return os.path.join(os.path.expanduser("~"), "Documents", TOP)


def default_settings_path():
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(base, "Nekki Limited", "Cascadeur", "settings.json")


def download(url, path, progress=None):
    """`url` into `path`; `progress(done, total)` returning False cancels."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response, \
                open(path, "wb") as out:
            total = int(response.headers.get("Content-Length") or 0)
            done = 0
            while True:
                block = response.read(CHUNK)
                if not block:
                    break
                out.write(block)
                done += len(block)
                if progress and progress(done, total) is False:
                    raise SetupError("cancelled - nothing changed")
    except SetupError:
        raise
    except Exception as exc:                          # noqa: BLE001
        raise SetupError("could not download the build ({0}) - nothing "
                         "changed".format(exc))


def _backup(settings_path):
    backup = settings_path + BACKUP_SUFFIX
    if not os.path.isfile(backup):
        shutil.copy2(settings_path, backup)
    return backup


def install(source_zip=None, install_dir=None, settings_path=None, progress=None):
    """Install (or update) the bridge. Returns the status line."""
    install_dir = install_dir or default_install_dir()
    settings_path = settings_path or default_settings_path()
    if not is_ours(install_dir):
        raise SetupError("{0} exists and is not a SkeldarAnim install - nothing "
                         "changed".format(install_dir))
    if not os.path.isfile(settings_path):
        raise SetupError("no Cascadeur settings.json at {0} - start Cascadeur "
                         "once, then run this again".format(settings_path))
    with open(settings_path, "r", encoding="utf-8") as handle:
        current = handle.read()
    new_text, changed = settings_edit(current, install_dir, PACKAGE)
    if changed and not os.access(settings_path, os.W_OK):
        raise SetupError("{0} is read-only - nothing changed. Clear its "
                         "read-only flag and run this again".format(settings_path))

    work = tempfile.mkdtemp(prefix="skeldar_cascade_install_")
    try:
        archive = source_zip
        if archive is None:
            archive = os.path.join(work, "SkeldarAnim.zip")
            download(ZIP_URL, archive, progress)
        with zipfile.ZipFile(archive) as zipped:
            problems = archive_problems(zipped.namelist())
            if problems:
                raise SetupError("; ".join(problems) + " - nothing changed")
            zipped.extractall(os.path.join(work, "unpacked"))
        source = os.path.join(work, "unpacked", TOP)
        # The settings first: if they cannot be written, the plugin folder is
        # not touched either.
        if changed:
            try:
                _backup(settings_path)
                with open(settings_path, "w", encoding="utf-8") as handle:
                    handle.write(new_text)
            except OSError as exc:
                raise SetupError("could not write {0} ({1}) - nothing changed"
                                 .format(settings_path, exc))
        if os.path.isdir(install_dir):
            shutil.rmtree(install_dir)
        shutil.copytree(source, install_dir)
    finally:
        shutil.rmtree(work, ignore_errors=True)

    if changed:
        return ("installed to {0} and added to Cascadeur's settings - restart "
                "Cascadeur, then SkeldarAnim > Bridge".format(install_dir))
    return ("updated {0}; Cascadeur's settings already hold it - restart "
            "Cascadeur if it was open".format(install_dir))


if __name__ == "__main__":
    print(install())
