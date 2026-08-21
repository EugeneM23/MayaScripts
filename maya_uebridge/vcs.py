"""Perforce placement for imported animation FBX.

stdlib only: every decision here is a pure function over p4's text output, so
the whole decision table is testable with neither Maya nor a Perforce server.
The p4 runner and every dialog are injectable - a modal dialog raised during a
command-port run blocks Maya's idle queue, so the live verify script drives
these functions with canned answers instead of real dialogs.

Three measured facts shape the parsing (2026-08-21, real depot): p4 exits 0
even for "no such file(s)", so failures are classified by stderr text and
"no such file(s)" / "not in client view" are normal answers, not errors;
ztag's other-open block arrives double-prefixed ("... ... otherOpen0 ...");
and P4CHARSET is utf8 on this machine, so output decodes as utf-8.
"""

import os
import re
import shutil
import stat
import subprocess

# Folders the uasset hierarchy carries that the fbx hierarchy does not.
VIEW_FOLDERS = ("1p", "3p")

_OTHER_OPEN = re.compile(r"^otherOpen(\d+)$")

# stderr texts that are answers, not failures. The root ones are measured:
# a target outside the workspace (the verify sandbox, a user-picked folder)
# gets "Path ... is not under client's root ..." (no "the" on this p4 build;
# other builds spell it with one) - it can never be in this depot, so it is
# "untracked", not an error.
_NORMAL_ANSWERS = ("no such file", "not in client view",
                   "not under client's root", "not under the client's root")


# ---------------------------------------------------------------- parsing

def parse_ztag(text):
    """-ztag output as a dict. otherOpen0.. stay distinct keys; the bare
    otherOpen count key does not collide with them."""
    fields = {}
    for line in (text or "").splitlines():
        if not line.startswith("... "):
            continue
        line = line[4:]
        if line.startswith("... "):  # the other-open block's second prefix
            line = line[4:]
        parts = line.split(" ", 1)
        fields[parts[0]] = parts[1].strip() if len(parts) > 1 else ""
    return fields


def other_openers(fields):
    """user@client strings, in otherOpen0..N order (numeric, not lexical)."""
    found = []
    for key, value in fields.items():
        match = _OTHER_OPEN.match(key)
        if match:
            found.append((int(match.group(1)), value))
    return [value for _, value in sorted(found)]


def classify_failure(stderr, returncode):
    """A human reason for a p4 failure, or "" when the output is a normal
    answer (including "no such file(s)", which p4 says with exit code 0)."""
    text = (stderr or "").strip()
    low = text.lower()
    if any(marker in low for marker in _NORMAL_ANSWERS):
        return ""
    if ("session has expired" in low or "please login" in low
            or "p4passwd" in low):
        return "Perforce session expired - log in via P4V"
    if "connect to server failed" in low or "no such host" in low:
        return "cannot reach the Perforce server"
    if returncode or text:
        return "p4: " + (text.splitlines()[0] if text
                         else "exit code {0}".format(returncode))
    return ""


def plan_for(fields):
    """The decision for one target file, from its fstat fields.

    kind: "untracked" (not in the depot - place the file, no p4),
    "mine" (already opened by this user - just overwrite),
    "others" (opened only by other people - the caller must ask),
    "edit" (tracked and free - p4 edit it).
    """
    users = other_openers(fields)
    if not fields.get("depotFile"):
        return {"kind": "untracked", "users": []}
    if fields.get("action"):
        return {"kind": "mine", "users": users}
    if users:
        return {"kind": "others", "users": users}
    return {"kind": "edit", "users": []}


# ---------------------------------------------------------------- placement

def package_folder(package):
    """The uasset folder of a package path - the dir-map key."""
    text = (package or "").replace("\\", "/")
    return text.rsplit("/", 1)[0] if "/" in text else ""


def conventional_folder(package, root):
    """Where a NEW fbx belongs, derived from the uasset package path.

    The measured convention (2026-08-21): the path relative to /Game, with
    Exports inserted after the Animation segment (not doubled) and a trailing
    1P/3P view folder dropped.
    """
    text = (package or "").replace("\\", "/")
    if text.lower().startswith("/game/"):
        text = text[len("/game/"):]
    segments = [part for part in text.split("/") if part][:-1]
    if segments and segments[-1].lower() in VIEW_FOLDERS:
        segments = segments[:-1]
    for index, segment in enumerate(segments):
        if segment.lower() == "animation":
            following = (segments[index + 1].lower()
                         if index + 1 < len(segments) else "")
            if following != "exports":
                segments = (segments[:index + 1] + ["Exports"]
                            + segments[index + 1:])
            break
    return os.path.join(root, *segments) if segments else root


def find_fbx(name, root):
    """Every <name>.fbx under root, case-insensitively. Fresh walk per call -
    the tree is local and a cache would go stale under the animator's hands."""
    wanted = (name + ".fbx").lower()
    found = []
    if not root or not os.path.isdir(root):
        return found
    for folder, _, files in os.walk(root):
        for filename in files:
            if filename.lower() == wanted:
                found.append(os.path.join(folder, filename))
    return found


def remembered_folder(dir_map, package):
    return (dir_map or {}).get(package_folder(package), "")


def remember_folder(dir_map, package, folder):
    """A new map with the answer for this uasset folder recorded."""
    grown = dict(dir_map or {})
    grown[package_folder(package)] = folder
    return grown


def choose_target(name, package, root, dir_map, ask_file, ask_folder):
    """The working-file path for one asset, or "" when the user cancelled.

    Search by NAME first (the user's call - the measured hierarchies diverge,
    the names match exactly). The convention only decides where a NEW file
    goes; a folder the user was asked for once is remembered per uasset
    folder and never asked again.
    """
    hits = find_fbx(name, root)
    if len(hits) == 1:
        return hits[0], dir_map
    if len(hits) > 1:
        remembered = remembered_folder(dir_map, package)
        if remembered:
            for hit in hits:
                if (os.path.normcase(os.path.dirname(hit))
                        == os.path.normcase(remembered)):
                    return hit, dir_map
        picked = ask_file(hits)
        if not picked:
            return "", dir_map
        return picked, remember_folder(dir_map, package,
                                       os.path.dirname(picked))
    filename = name + ".fbx"
    remembered = remembered_folder(dir_map, package)
    if remembered and os.path.isdir(remembered):
        return os.path.join(remembered, filename), dir_map
    folder = conventional_folder(package, root)
    if os.path.isdir(folder):
        return os.path.join(folder, filename), dir_map
    picked = ask_folder(name)
    if not picked:
        return "", dir_map
    return (os.path.join(picked, filename),
            remember_folder(dir_map, package, picked))


# ---------------------------------------------------------------- p4 calls

_CREATE_NO_WINDOW = 0x08000000  # or every p4 call flashes a console over Maya


def run_p4(args, cwd):
    """(returncode, stdout, stderr); returncode None when p4 could not run at
    all, with the reason in stderr. Output decodes as utf-8 - P4CHARSET is
    utf8 on this machine and user names may be non-ASCII."""
    try:
        proc = subprocess.run(
            ["p4"] + list(args), cwd=cwd or None, capture_output=True,
            timeout=15,
            creationflags=_CREATE_NO_WINDOW if os.name == "nt" else 0)
    except FileNotFoundError:
        return None, "", "p4.exe not found - is Perforce installed?"
    except subprocess.TimeoutExpired:
        return None, "", "p4 timed out - server unreachable?"
    except OSError as error:
        return None, "", "p4 could not run: {0}".format(error)
    return (proc.returncode,
            proc.stdout.decode("utf-8", "replace"),
            proc.stderr.decode("utf-8", "replace"))


def fstat(path, run=run_p4):
    """(fields, failure). Empty fields with no failure = untracked."""
    code, out, err = run(["-ztag", "fstat", "-Or", path],
                         os.path.dirname(path))
    if code is None:
        return {}, err or "p4 failed"
    failure = classify_failure(err, code)
    if failure:
        return {}, failure
    return parse_ztag(out), ""


def checkout(path, run=run_p4):
    """p4 edit; "" on success. A file never synced answers "not on client" -
    sync it and retry once (self-healing beats pre-classifying local state)."""
    folder = os.path.dirname(path)
    code, out, err = run(["edit", path], folder)
    if code is not None and "not on client" in (err or "").lower():
        run(["sync", path], folder)
        code, out, err = run(["edit", path], folder)
    if code is None:
        return err or "p4 failed"
    low = (out or "").lower()
    if "opened for edit" in low or "currently opened" in low:
        return ""
    failure = classify_failure(err, code)
    return failure or "p4 edit did not open the file"


def prepare_target(target, ask_others, ask_failure, run=run_p4):
    """The depot side of placing one file: (proceed, note).

    ask_others(users) and ask_failure(reason) answer True to continue
    locally; both are injectable because a modal over the command port
    blocks Maya. Nothing here touches the depot except p4 edit on a
    tracked, unopened file.
    """
    fields, failure = fstat(target, run)
    if failure:
        if not ask_failure(failure):
            return False, ""
        return True, "no checkout - {0}".format(failure)
    decision = plan_for(fields)
    if decision["kind"] == "untracked":
        return True, "not in depot"
    if decision["kind"] == "mine":
        return True, "checked out"
    if decision["kind"] == "others":
        if not ask_others(decision["users"]):
            return False, ""
        return True, "overwritten locally - checked out by {0}".format(
            ", ".join(decision["users"]))
    failure = checkout(target, run)
    if failure:
        if not ask_failure(failure):
            return False, ""
        return True, "no checkout - {0}".format(failure)
    return True, "checked out"


# ---------------------------------------------------------------- the disk

def ensure_writable(path):
    if os.path.isfile(path):
        os.chmod(path, stat.S_IMODE(os.stat(path).st_mode) | stat.S_IWRITE)


def place(source, target):
    """Copy the exported temp fbx onto the working file. The export never
    writes the working file directly: the UE exporter deletes its destination
    first, so a failed export straight onto it would leave nothing there."""
    folder = os.path.dirname(target)
    if folder and not os.path.isdir(folder):
        os.makedirs(folder)
    ensure_writable(target)
    shutil.copyfile(source, target)


def status_suffix(target, root, is_new, note):
    """What the status line appends after a VCS placement."""
    base = os.path.dirname((root or "").rstrip("\\/"))
    try:
        shown = os.path.relpath(target, base) if base else target
    except ValueError:  # different drive
        shown = target
    if shown.startswith(".."):
        shown = target
    tags = []
    if is_new:
        tags.append("new file")
    if note and not (is_new and note == "not in depot"):
        tags.append(note)
    tail = " ({0})".format(", ".join(tags)) if tags else ""
    return "fbx -> {0}{1}".format(shown, tail)
