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

# stderr texts that are answers, not failures.
_NORMAL_ANSWERS = ("no such file", "not in client view")


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
