# UE Bridge Perforce Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A "Connect to version control" checkbox in the UE Animation Bridge that lands imported FBX in the SourceArt working tree with Perforce checkout handling.

**Architecture:** One new stdlib-only module `maya_uebridge/vcs.py` holds every decision as a pure function (ztag parsing, failure classification, the checkout decision table, the path convention, the name search) plus a thin subprocess p4 runner; every dialog is an injectable callable. `window.py` grows the checkbox row, the optionVars, the real dialogs, and threads `import_selected` through the orchestrator. `animimport.py` is untouched.

**Tech Stack:** Python (Maya 2027's), `subprocess` → `p4.exe` CLI, `maya.cmds` UI. Spec: `docs/superpowers/specs/2026-08-21-uebridge-perforce-design.md`.

## Global Constraints

- Tests run with Maya's interpreter only: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v` — there is no system Python, never pip install anything.
- `maya_uebridge/vcs.py` must import **stdlib only** (it joins the purity subprocess test in `tests/test_uebridge_records.py`).
- String formatting via `.format()`, module docstrings explaining the *why* — match the surrounding style.
- p4 output decodes as **utf-8** (P4CHARSET=utf8 on this machine); subprocess uses `CREATE_NO_WINDOW` on Windows or every call flashes a console over Maya.
- p4's exit code is 0 even for "no such file(s)" (measured) — classification is by stderr text, and "no such file(s)" / "not in client view" are *normal answers*, not errors.
- ztag other-open fields arrive with a **double** prefix: `... ... otherOpen0 user@client` (measured) — the parser must strip both.
- No `p4 add`, no `p4 submit`, nothing that mutates the depot except `p4 edit` on tracked files. The live verify mutates the depot **not at all**.
- Commit after each green task; commit messages in the repo's `feat(uebridge)/docs/test` style.

---

### Task 1: ztag parsing, failure classification, the decision table

**Files:**
- Create: `maya_uebridge/vcs.py`
- Create: `tests/test_uebridge_vcs.py`

**Interfaces:**
- Produces: `parse_ztag(text) -> dict` (field name → value, otherOpenN kept as distinct keys), `other_openers(fields) -> list` (numerically sorted `user@client` strings), `classify_failure(stderr, returncode) -> str` ("" = normal answer, otherwise a human reason), `plan_for(fields) -> dict` with keys `kind` ("untracked"|"mine"|"others"|"edit") and `users` (list).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_uebridge_vcs.py`:

```python
"""Tests for the Perforce module's pure logic.

The fixtures are real p4 output captured on the user's machine 2026-08-21 -
including the double '... ...' prefix on other-open fields and the fact that
"no such file(s)" arrives on stderr with exit code 0.
"""

import os
import unittest

from maya_uebridge import vcs

TRACKED_UNOPENED = """\
... depotFile //atone/main/Atone/Content/Prototype/Animation/PlayerCharacter/Unarmed/1P/AS_Unarmed_Idle_1P.uasset
... clientFile C:\\!!!Work\\Perforce\\Atone\\Content\\Prototype\\Animation\\PlayerCharacter\\Unarmed\\1P\\AS_Unarmed_Idle_1P.uasset
... isMapped 
... headAction edit
... headType binary+l
... headRev 2
... headChange 41316
... haveRev 2
"""

OPENED_BY_OTHERS = TRACKED_UNOPENED + """\
... ... otherOpen0 aleksei.silantev@aleksei.silantev_Lehanomicon_2914
... ... otherAction0 edit
... ... otherChange0 default
... ... otherOpen1 emrys.ryan@emrys.ryan_SULACO_306
... ... otherAction1 edit
... ... otherChange1 default
... ... otherOpen 2
"""

OPENED_BY_ME = TRACKED_UNOPENED + "... action edit\n... change default\n"


class ParseZtag(unittest.TestCase):

    def test_reads_the_plain_fields(self):
        fields = vcs.parse_ztag(TRACKED_UNOPENED)
        self.assertIn("//atone/main/", fields["depotFile"])
        self.assertEqual(fields["headRev"], "2")

    def test_reads_the_double_prefixed_other_open_block(self):
        """otherOpen lines carry '... ... ' - a parser matching one prefix
        misses every one of them and reports a busy file as free."""
        fields = vcs.parse_ztag(OPENED_BY_OTHERS)
        self.assertIn("aleksei.silantev@", fields["otherOpen0"])
        self.assertIn("emrys.ryan@", fields["otherOpen1"])

    def test_the_count_key_does_not_eat_the_numbered_ones(self):
        fields = vcs.parse_ztag(OPENED_BY_OTHERS)
        self.assertEqual(fields["otherOpen"], "2")
        self.assertIn("otherOpen0", fields)

    def test_valueless_fields_survive(self):
        self.assertEqual(vcs.parse_ztag(TRACKED_UNOPENED)["isMapped"], "")

    def test_empty_text_is_an_empty_dict(self):
        self.assertEqual(vcs.parse_ztag(""), {})


class OtherOpeners(unittest.TestCase):

    def test_lists_every_opener(self):
        users = vcs.other_openers(vcs.parse_ztag(OPENED_BY_OTHERS))
        self.assertEqual(len(users), 2)
        self.assertTrue(users[0].startswith("aleksei.silantev@"))

    def test_sorts_numerically_not_lexically(self):
        fields = {"otherOpen{0}".format(i): "user{0}".format(i)
                  for i in range(12)}
        users = vcs.other_openers(fields)
        self.assertEqual(users[9], "user9")
        self.assertEqual(users[10], "user10")

    def test_no_openers_is_an_empty_list(self):
        self.assertEqual(vcs.other_openers(vcs.parse_ztag(TRACKED_UNOPENED)), [])


class ClassifyFailure(unittest.TestCase):

    def test_no_such_file_is_a_normal_answer(self):
        """Untracked is data, not an error - and p4 exits 0 saying it."""
        err = "C:\\x\\AS_Unarmed_Idle_1P.fbx - no such file(s).\n"
        self.assertEqual(vcs.classify_failure(err, 0), "")

    def test_outside_the_client_view_is_a_normal_answer(self):
        err = "C:\\elsewhere\\a.fbx - file(s) not in client view.\n"
        self.assertEqual(vcs.classify_failure(err, 0), "")

    def test_an_expired_session_names_the_cure(self):
        err = "Your session has expired, please login again.\n"
        reason = vcs.classify_failure(err, 1)
        self.assertIn("P4V", reason)

    def test_an_unset_password_reads_as_an_expired_session(self):
        err = "Perforce password (P4PASSWD) invalid or unset.\n"
        self.assertIn("P4V", vcs.classify_failure(err, 1))

    def test_a_dead_server_says_unreachable(self):
        err = ("Perforce client error:\n"
               "\tConnect to server failed; check $P4PORT.\n")
        self.assertIn("reach", vcs.classify_failure(err, 1))

    def test_an_unknown_error_shows_its_first_line(self):
        reason = vcs.classify_failure("something odd happened\nmore\n", 1)
        self.assertIn("something odd happened", reason)
        self.assertNotIn("more", reason)

    def test_clean_output_is_no_failure(self):
        self.assertEqual(vcs.classify_failure("", 0), "")


class PlanFor(unittest.TestCase):

    def test_empty_fields_mean_untracked(self):
        self.assertEqual(vcs.plan_for({})["kind"], "untracked")

    def test_tracked_and_free_means_edit(self):
        plan = vcs.plan_for(vcs.parse_ztag(TRACKED_UNOPENED))
        self.assertEqual(plan["kind"], "edit")

    def test_open_by_me_means_mine(self):
        plan = vcs.plan_for(vcs.parse_ztag(OPENED_BY_ME))
        self.assertEqual(plan["kind"], "mine")

    def test_open_by_others_names_them(self):
        plan = vcs.plan_for(vcs.parse_ztag(OPENED_BY_OTHERS))
        self.assertEqual(plan["kind"], "others")
        self.assertEqual(len(plan["users"]), 2)

    def test_mine_wins_over_others(self):
        """Already mine = already decided to work on it; others go to the
        status line, not a modal."""
        both = OPENED_BY_OTHERS + "... action edit\n"
        plan = vcs.plan_for(vcs.parse_ztag(both))
        self.assertEqual(plan["kind"], "mine")
        self.assertEqual(len(plan["users"]), 2)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_uebridge_vcs -v`
Expected: FAIL — `ImportError`/`ModuleNotFoundError` (no `maya_uebridge.vcs`).

- [ ] **Step 3: Write the implementation**

Create `maya_uebridge/vcs.py`:

```python
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
```

- [ ] **Step 4: Run to verify pass**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_uebridge_vcs -v`
Expected: PASS (all Task 1 tests).

- [ ] **Step 5: Commit**

```bash
git add maya_uebridge/vcs.py tests/test_uebridge_vcs.py
git commit -m "feat(uebridge): p4 ztag parsing and the checkout decision table"
```

---

### Task 2: the path convention, the name search, the dir map

**Files:**
- Modify: `maya_uebridge/vcs.py` (append)
- Modify: `tests/test_uebridge_vcs.py` (append)

**Interfaces:**
- Consumes: `VIEW_FOLDERS` from Task 1.
- Produces: `conventional_folder(package, root) -> str`, `find_fbx(name, root) -> list`, `package_folder(package) -> str`, `remembered_folder(dir_map, package) -> str`, `remember_folder(dir_map, package, folder) -> dict` (a new dict, input unmutated).

- [ ] **Step 1: Write the failing tests** (append to `tests/test_uebridge_vcs.py`; add `import shutil`, `import tempfile` to the imports)

```python
class ConventionalFolder(unittest.TestCase):

    ROOT = os.path.join("C:", os.sep, "src")

    def test_the_real_example(self):
        """The measured divergence: Exports inserted after Animation, the
        trailing 1P dropped."""
        folder = vcs.conventional_folder(
            "/Game/Prototype/Animation/PlayerCharacter/Unarmed/1P/AS_Unarmed_Idle_1P",
            self.ROOT)
        self.assertEqual(folder, os.path.join(
            self.ROOT, "Prototype", "Animation", "Exports",
            "PlayerCharacter", "Unarmed"))

    def test_3p_is_dropped_too(self):
        folder = vcs.conventional_folder("/Game/P/Animation/X/3P/Asset", self.ROOT)
        self.assertEqual(folder, os.path.join(
            self.ROOT, "P", "Animation", "Exports", "X"))

    def test_1p_matching_is_case_insensitive(self):
        folder = vcs.conventional_folder("/Game/P/Animation/X/1p/Asset", self.ROOT)
        self.assertTrue(folder.endswith("X"))

    def test_exports_is_not_doubled(self):
        folder = vcs.conventional_folder(
            "/Game/P/Animation/Exports/X/Asset", self.ROOT)
        self.assertEqual(folder.lower().count("exports"), 1)

    def test_a_path_without_animation_passes_through(self):
        folder = vcs.conventional_folder("/Game/Props/Swords/Asset", self.ROOT)
        self.assertEqual(folder, os.path.join(self.ROOT, "Props", "Swords"))

    def test_a_package_without_game_prefix_still_lands_under_root(self):
        folder = vcs.conventional_folder("Odd/Path/Asset", self.ROOT)
        self.assertEqual(folder, os.path.join(self.ROOT, "Odd", "Path"))

    def test_a_bare_asset_name_lands_on_the_root(self):
        self.assertEqual(vcs.conventional_folder("Asset", self.ROOT), self.ROOT)


class FindFbx(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="vcs_find_")
        self.addCleanup(shutil.rmtree, self.root, True)

    def plant(self, *parts):
        path = os.path.join(self.root, *parts)
        folder = os.path.dirname(path)
        if not os.path.isdir(folder):
            os.makedirs(folder)
        with open(path, "w") as handle:
            handle.write("x")
        return path

    def test_finds_a_nested_file(self):
        planted = self.plant("A", "B", "AS_Walk.fbx")
        self.assertEqual(vcs.find_fbx("AS_Walk", self.root), [planted])

    def test_matching_is_case_insensitive(self):
        self.plant("A", "as_walk.FBX")
        self.assertEqual(len(vcs.find_fbx("AS_Walk", self.root)), 1)

    def test_finds_every_duplicate(self):
        self.plant("A", "AS_Walk.fbx")
        self.plant("B", "AS_Walk.fbx")
        self.assertEqual(len(vcs.find_fbx("AS_Walk", self.root)), 2)

    def test_other_names_do_not_match(self):
        self.plant("A", "AS_Walk_Fast.fbx")
        self.assertEqual(vcs.find_fbx("AS_Walk", self.root), [])

    def test_a_missing_root_is_an_empty_list(self):
        gone = os.path.join(self.root, "nowhere")
        self.assertEqual(vcs.find_fbx("AS_Walk", gone), [])


class DirMap(unittest.TestCase):

    PACKAGE = "/Game/P/Animation/X/1P/AS_Walk"

    def test_remember_and_recall(self):
        grown = vcs.remember_folder({}, self.PACKAGE, "C:/src/somewhere")
        self.assertEqual(vcs.remembered_folder(grown, self.PACKAGE),
                         "C:/src/somewhere")

    def test_the_key_is_the_uasset_folder_not_the_asset(self):
        """Two animations in one uasset folder share the remembered answer."""
        grown = vcs.remember_folder({}, self.PACKAGE, "C:/src/somewhere")
        sibling = "/Game/P/Animation/X/1P/AS_Run"
        self.assertEqual(vcs.remembered_folder(grown, sibling),
                         "C:/src/somewhere")

    def test_remember_does_not_mutate_the_input(self):
        original = {}
        vcs.remember_folder(original, self.PACKAGE, "C:/x")
        self.assertEqual(original, {})

    def test_unknown_package_recalls_nothing(self):
        self.assertEqual(vcs.remembered_folder({}, self.PACKAGE), "")
```

- [ ] **Step 2: Run to verify failure**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_uebridge_vcs -v`
Expected: FAIL — `AttributeError` on the new names.

- [ ] **Step 3: Write the implementation** (append to `maya_uebridge/vcs.py`)

```python
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
                segments = segments[:index + 1] + ["Exports"] + segments[index + 1:]
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
```

- [ ] **Step 4: Run to verify pass** — same command, expected PASS.

- [ ] **Step 5: Commit**

```bash
git add maya_uebridge/vcs.py tests/test_uebridge_vcs.py
git commit -m "feat(uebridge): fbx name search, path convention, remembered folders"
```

---

### Task 3: choose_target — the full resolution

**Files:**
- Modify: `maya_uebridge/vcs.py` (append)
- Modify: `tests/test_uebridge_vcs.py` (append)

**Interfaces:**
- Consumes: `find_fbx`, `conventional_folder`, `remembered_folder`, `remember_folder` (Task 2).
- Produces: `choose_target(name, package, root, dir_map, ask_file, ask_folder) -> (path, dir_map)` — `path` is `""` when the user cancelled; `dir_map` may be a grown copy. `ask_file(paths) -> path or ""`, `ask_folder(name) -> folder or ""` are injectable.

- [ ] **Step 1: Write the failing tests** (append)

```python
class ChooseTarget(unittest.TestCase):

    PACKAGE = "/Game/P/Animation/X/1P/AS_Walk"

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="vcs_choose_")
        self.addCleanup(shutil.rmtree, self.root, True)

    def plant(self, *parts):
        path = os.path.join(self.root, *parts)
        folder = os.path.dirname(path)
        if not os.path.isdir(folder):
            os.makedirs(folder)
        with open(path, "w") as handle:
            handle.write("x")
        return path

    def never(self, *_):
        self.fail("a dialog was raised where none belongs")

    def test_a_single_hit_is_taken_silently(self):
        planted = self.plant("anywhere", "AS_Walk.fbx")
        path, dir_map = vcs.choose_target(
            "AS_Walk", self.PACKAGE, self.root, {}, self.never, self.never)
        self.assertEqual(path, planted)
        self.assertEqual(dir_map, {})

    def test_ambiguity_prefers_the_remembered_folder(self):
        wanted = self.plant("good", "AS_Walk.fbx")
        self.plant("bad", "AS_Walk.fbx")
        remembered = vcs.remember_folder({}, self.PACKAGE,
                                         os.path.dirname(wanted))
        path, _ = vcs.choose_target(
            "AS_Walk", self.PACKAGE, self.root, remembered,
            self.never, self.never)
        self.assertEqual(path, wanted)

    def test_ambiguity_without_memory_asks_and_remembers(self):
        first = self.plant("A", "AS_Walk.fbx")
        self.plant("B", "AS_Walk.fbx")
        path, dir_map = vcs.choose_target(
            "AS_Walk", self.PACKAGE, self.root, {},
            lambda paths: first, self.never)
        self.assertEqual(path, first)
        self.assertEqual(vcs.remembered_folder(dir_map, self.PACKAGE),
                         os.path.dirname(first))

    def test_cancelling_the_pick_cancels_the_import(self):
        self.plant("A", "AS_Walk.fbx")
        self.plant("B", "AS_Walk.fbx")
        path, _ = vcs.choose_target(
            "AS_Walk", self.PACKAGE, self.root, {},
            lambda paths: "", self.never)
        self.assertEqual(path, "")

    def test_a_new_file_lands_in_the_existing_conventional_folder(self):
        folder = os.path.join(self.root, "P", "Animation", "Exports", "X")
        os.makedirs(folder)
        path, _ = vcs.choose_target(
            "AS_Walk", self.PACKAGE, self.root, {}, self.never, self.never)
        self.assertEqual(path, os.path.join(folder, "AS_Walk.fbx"))

    def test_a_new_file_prefers_the_remembered_folder(self):
        chosen = os.path.join(self.root, "elsewhere")
        os.makedirs(chosen)
        remembered = vcs.remember_folder({}, self.PACKAGE, chosen)
        path, _ = vcs.choose_target(
            "AS_Walk", self.PACKAGE, self.root, remembered,
            self.never, self.never)
        self.assertEqual(path, os.path.join(chosen, "AS_Walk.fbx"))

    def test_a_new_file_with_no_folder_asks_and_remembers(self):
        chosen = os.path.join(self.root, "picked")
        os.makedirs(chosen)
        path, dir_map = vcs.choose_target(
            "AS_Walk", self.PACKAGE, self.root, {},
            self.never, lambda name: chosen)
        self.assertEqual(path, os.path.join(chosen, "AS_Walk.fbx"))
        self.assertEqual(vcs.remembered_folder(dir_map, self.PACKAGE), chosen)

    def test_cancelling_the_folder_ask_cancels_the_import(self):
        path, _ = vcs.choose_target(
            "AS_Walk", self.PACKAGE, self.root, {},
            self.never, lambda name: "")
        self.assertEqual(path, "")
```

- [ ] **Step 2: Run to verify failure** — same command, expected `AttributeError: choose_target`.

- [ ] **Step 3: Write the implementation** (append to `vcs.py`)

```python
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
                if os.path.normcase(os.path.dirname(hit)) == os.path.normcase(remembered):
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
    return os.path.join(picked, filename), remember_folder(dir_map, package,
                                                           picked)
```

- [ ] **Step 4: Run to verify pass** — same command, expected PASS.

- [ ] **Step 5: Commit**

```bash
git add maya_uebridge/vcs.py tests/test_uebridge_vcs.py
git commit -m "feat(uebridge): choose_target resolves the working fbx for an asset"
```

---

### Task 4: the p4 runner, fstat, checkout, prepare_target, place, status_suffix

**Files:**
- Modify: `maya_uebridge/vcs.py` (append)
- Modify: `tests/test_uebridge_vcs.py` (append)

**Interfaces:**
- Consumes: `parse_ztag`, `classify_failure`, `plan_for` (Task 1).
- Produces: `run_p4(args, cwd) -> (returncode_or_None, stdout, stderr)`; `fstat(path, run=run_p4) -> (fields, failure)`; `checkout(path, run=run_p4) -> failure_or_empty`; `prepare_target(target, ask_others, ask_failure, run=run_p4) -> (proceed, note)`; `ensure_writable(path)`; `place(source, target)`; `status_suffix(target, root, is_new, note) -> str`. `ask_others(users) -> bool`, `ask_failure(reason) -> bool` are injectable (True = continue locally).

- [ ] **Step 1: Write the failing tests** (append)

```python
class FakeP4(object):
    """A scripted p4: each expected call is (args_prefix, (code, out, err))."""

    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    def __call__(self, args, cwd):
        self.calls.append(list(args))
        for index, (prefix, reply) in enumerate(self.script):
            if list(args)[:len(prefix)] == list(prefix):
                self.script.pop(index)
                return reply
        raise AssertionError("unexpected p4 call: {0}".format(args))


NO_SUCH = (0, "", "C:\\x\\AS_Walk.fbx - no such file(s).\n")
EXPIRED = (1, "", "Your session has expired, please login again.\n")


class Fstat(unittest.TestCase):

    def test_untracked_is_empty_fields_and_no_failure(self):
        run = FakeP4([(["-ztag", "fstat"], NO_SUCH)])
        fields, failure = vcs.fstat("C:\\x\\AS_Walk.fbx", run)
        self.assertEqual(fields, {})
        self.assertEqual(failure, "")

    def test_tracked_parses_the_fields(self):
        run = FakeP4([(["-ztag", "fstat"], (0, TRACKED_UNOPENED, ""))])
        fields, failure = vcs.fstat("C:\\x\\a.uasset", run)
        self.assertEqual(failure, "")
        self.assertIn("depotFile", fields)

    def test_a_dead_p4_is_a_failure_with_a_reason(self):
        run = FakeP4([(["-ztag", "fstat"], EXPIRED)])
        fields, failure = vcs.fstat("C:\\x\\a.fbx", run)
        self.assertEqual(fields, {})
        self.assertIn("P4V", failure)

    def test_a_missing_p4_exe_reports_itself(self):
        run = FakeP4([(["-ztag", "fstat"], (None, "", "p4.exe not found"))])
        fields, failure = vcs.fstat("C:\\x\\a.fbx", run)
        self.assertIn("p4.exe", failure)


class Checkout(unittest.TestCase):

    def test_a_clean_edit_succeeds(self):
        run = FakeP4([(["edit"], (0, "//d/a.fbx#2 - opened for edit\n", ""))])
        self.assertEqual(vcs.checkout("C:\\x\\a.fbx", run), "")

    def test_already_open_counts_as_success(self):
        run = FakeP4([(["edit"],
                       (0, "//d/a.fbx#2 - currently opened for edit\n", ""))])
        self.assertEqual(vcs.checkout("C:\\x\\a.fbx", run), "")

    def test_not_on_client_syncs_and_retries_once(self):
        run = FakeP4([
            (["edit"], (0, "", "//d/a.fbx - file(s) not on client.\n")),
            (["sync"], (0, "//d/a.fbx#2 - added\n", "")),
            (["edit"], (0, "//d/a.fbx#2 - opened for edit\n", "")),
        ])
        self.assertEqual(vcs.checkout("C:\\x\\a.fbx", run), "")
        self.assertEqual([call[0] for call in run.calls],
                         ["edit", "sync", "edit"])

    def test_a_failed_edit_reports_a_reason(self):
        run = FakeP4([(["edit"], EXPIRED)])
        self.assertIn("P4V", vcs.checkout("C:\\x\\a.fbx", run))


class PrepareTarget(unittest.TestCase):

    def never_ask(self, *_):
        raise AssertionError("a dialog was raised where none belongs")

    def test_untracked_proceeds_without_p4_actions(self):
        run = FakeP4([(["-ztag", "fstat"], NO_SUCH)])
        proceed, note = vcs.prepare_target("C:\\x\\a.fbx",
                                           self.never_ask, self.never_ask, run)
        self.assertTrue(proceed)
        self.assertEqual(note, "not in depot")
        self.assertEqual(len(run.calls), 1)

    def test_tracked_and_free_gets_checked_out(self):
        run = FakeP4([
            (["-ztag", "fstat"], (0, TRACKED_UNOPENED, "")),
            (["edit"], (0, "//d/a#2 - opened for edit\n", "")),
        ])
        proceed, note = vcs.prepare_target("C:\\x\\a.fbx",
                                           self.never_ask, self.never_ask, run)
        self.assertTrue(proceed)
        self.assertEqual(note, "checked out")

    def test_mine_proceeds_silently(self):
        run = FakeP4([(["-ztag", "fstat"], (0, OPENED_BY_ME, ""))])
        proceed, note = vcs.prepare_target("C:\\x\\a.fbx",
                                           self.never_ask, self.never_ask, run)
        self.assertTrue(proceed)
        self.assertEqual(note, "checked out")

    def test_others_accepted_overwrites_locally(self):
        run = FakeP4([(["-ztag", "fstat"], (0, OPENED_BY_OTHERS, ""))])
        proceed, note = vcs.prepare_target(
            "C:\\x\\a.fbx", lambda users: True, self.never_ask, run)
        self.assertTrue(proceed)
        self.assertIn("aleksei.silantev@", note)
        self.assertEqual(len(run.calls), 1)  # no edit behind their back

    def test_others_declined_cancels(self):
        run = FakeP4([(["-ztag", "fstat"], (0, OPENED_BY_OTHERS, ""))])
        proceed, _ = vcs.prepare_target(
            "C:\\x\\a.fbx", lambda users: False, self.never_ask, run)
        self.assertFalse(proceed)

    def test_p4_failure_accepted_continues_locally(self):
        run = FakeP4([(["-ztag", "fstat"], EXPIRED)])
        proceed, note = vcs.prepare_target(
            "C:\\x\\a.fbx", self.never_ask, lambda reason: True, run)
        self.assertTrue(proceed)
        self.assertIn("no checkout", note)

    def test_p4_failure_declined_cancels(self):
        run = FakeP4([(["-ztag", "fstat"], EXPIRED)])
        proceed, _ = vcs.prepare_target(
            "C:\\x\\a.fbx", self.never_ask, lambda reason: False, run)
        self.assertFalse(proceed)

    def test_a_failed_edit_falls_back_to_the_failure_ask(self):
        run = FakeP4([
            (["-ztag", "fstat"], (0, TRACKED_UNOPENED, "")),
            (["edit"], EXPIRED),
        ])
        proceed, note = vcs.prepare_target(
            "C:\\x\\a.fbx", self.never_ask, lambda reason: True, run)
        self.assertTrue(proceed)
        self.assertIn("no checkout", note)


class PlaceAndSuffix(unittest.TestCase):

    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="vcs_place_")
        self.addCleanup(shutil.rmtree, self.folder, True)

    def test_place_overwrites_a_read_only_target(self):
        source = os.path.join(self.folder, "new.fbx")
        target = os.path.join(self.folder, "old.fbx")
        for path, body in ((source, "new"), (target, "old")):
            with open(path, "w") as handle:
                handle.write(body)
        os.chmod(target, stat.S_IREAD)
        vcs.place(source, target)
        with open(target) as handle:
            self.assertEqual(handle.read(), "new")

    def test_place_creates_the_missing_folder(self):
        source = os.path.join(self.folder, "new.fbx")
        with open(source, "w") as handle:
            handle.write("new")
        target = os.path.join(self.folder, "deep", "down", "new.fbx")
        vcs.place(source, target)
        self.assertTrue(os.path.isfile(target))

    def test_suffix_shows_the_path_under_the_root_by_name(self):
        suffix = vcs.status_suffix(
            "C:\\w\\SourceArt\\P\\a.fbx", "C:\\w\\SourceArt", False,
            "checked out")
        self.assertIn(os.path.join("SourceArt", "P", "a.fbx"), suffix)
        self.assertIn("(checked out)", suffix)

    def test_suffix_marks_a_new_file(self):
        suffix = vcs.status_suffix(
            "C:\\w\\SourceArt\\P\\a.fbx", "C:\\w\\SourceArt", True,
            "not in depot")
        self.assertIn("new file", suffix)
        self.assertNotIn("not in depot", suffix)  # redundant for a new file

    def test_suffix_survives_a_target_outside_the_root(self):
        suffix = vcs.status_suffix("D:\\odd\\a.fbx", "C:\\w\\SourceArt",
                                   False, "")
        self.assertIn("D:\\odd\\a.fbx", suffix)
```

Add `import stat` to the test file imports.

- [ ] **Step 2: Run to verify failure** — expected `AttributeError` on the new names.

- [ ] **Step 3: Write the implementation** (append to `vcs.py`)

```python
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
```

- [ ] **Step 4: Run to verify pass** — full `tests.test_uebridge_vcs`, expected PASS.

- [ ] **Step 5: Commit**

```bash
git add maya_uebridge/vcs.py tests/test_uebridge_vcs.py
git commit -m "feat(uebridge): p4 runner, checkout flow and fbx placement"
```

---

### Task 5: the purity guard

**Files:**
- Modify: `tests/test_uebridge_records.py:192-207` (the `Purity` test)
- Modify: `tests/test_uebridge_vcs.py` (append the same guard for vcs)

**Interfaces:** none new.

- [ ] **Step 1: Extend the purity test.** In `tests/test_uebridge_records.py`, add `maya_uebridge.vcs` to the imports inside the subprocess code string:

```python
        code = (
            "import sys; sys.path.insert(0, %r);"
            "import maya_uebridge, maya_uebridge.records,"
            " maya_uebridge.uescripts, maya_uebridge.uelink,"
            " maya_uebridge.vcs;"
            "assert 'maya.cmds' not in sys.modules, 'maya.cmds leaked in';"
            "assert 'maya_uebridge.window' not in sys.modules, 'window leaked in';"
            "assert 'maya_uebridge.animimport' not in sys.modules, 'animimport leaked in';"
            "print('clean')" % root)
```

- [ ] **Step 2: Run to verify pass** (it should already pass — vcs.py is stdlib-only by construction; a failure here means an import slipped in):

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_uebridge_records -v`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_uebridge_records.py
git commit -m "test(uebridge): vcs joins the stdlib purity guard"
```

---

### Task 6: the window — checkbox row, optionVars, dialogs, the import flow

**Files:**
- Modify: `maya_uebridge/window.py`
- Test: `tests/test_uebridge_window.py` (append)

**Interfaces:**
- Consumes: `vcs.choose_target`, `vcs.prepare_target`, `vcs.place`, `vcs.status_suffix` (Tasks 3–4).
- Produces: UI names `_VCS = "ueAnimBridgeVcs"`, `_VCSROOT = "ueAnimBridgeVcsRoot"`; optionVars `ueBridgeVcs` (int), `ueBridgeVcsRoot` (string), `ueBridgeVcsDirMap` (JSON string); functions `vcs_enabled()`, `_saved_root()`, `_vcs_target(record, asks=None) -> (target, is_new) or None` — `asks` maps `"root"/"file"/"folder"` to injected callables for the live verify.

- [ ] **Step 1: Write the failing test** (append to `tests/test_uebridge_window.py`)

```python
class VcsStatus(unittest.TestCase):
    """The status suffix combination lives in window.py because it joins the
    import line; the wording itself is vcs.status_suffix, tested in
    test_uebridge_vcs."""

    def test_the_suffix_joins_the_import_line(self):
        line = window.with_vcs_suffix("A onto root: 92 bones", "fbx -> S\\a.fbx")
        self.assertEqual(line, "A onto root: 92 bones  |  fbx -> S\\a.fbx")

    def test_no_suffix_leaves_the_line_alone(self):
        line = window.with_vcs_suffix("A onto root: 92 bones", "")
        self.assertEqual(line, "A onto root: 92 bones")
```

- [ ] **Step 2: Run to verify failure**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_uebridge_window -v`
Expected: FAIL — `AttributeError: with_vcs_suffix`.

- [ ] **Step 3: Implement the window changes.** All in `maya_uebridge/window.py`:

3a. Imports and names — add `from maya_uebridge import vcs` to the imports; add UI names next to `_MODE`:

```python
_VCS = "ueAnimBridgeVcs"
_VCSROOT = "ueAnimBridgeVcsRoot"
```

3b. After the `merge_selected` function, the VCS block:

```python
# ---------------------------------------------------------------- vcs

def vcs_enabled():
    if not cmds.checkBox(_VCS, exists=True):
        return False
    return bool(cmds.checkBox(_VCS, query=True, value=True))


def _saved_root():
    if cmds.optionVar(exists="ueBridgeVcsRoot"):
        return cmds.optionVar(query="ueBridgeVcsRoot") or ""
    return ""


def _root_label(root):
    return root or "no source project set"


def _pick_root():
    kwargs = {"fileMode": 3, "dialogStyle": 2,
              "caption": "Where is the source project (the SourceArt root)?"}
    saved = _saved_root()
    if saved and os.path.isdir(saved):
        kwargs["startingDirectory"] = saved
    picked = cmds.fileDialog2(**kwargs) or []
    return picked[0] if picked else ""


def _apply_root(root):
    cmds.optionVar(stringValue=("ueBridgeVcsRoot", root))
    if cmds.text(_VCSROOT, exists=True):
        cmds.text(_VCSROOT, edit=True, label=_root_label(root))


def _vcs_toggled():
    """First activation asks where the source project is; declining the
    dialog flips the checkbox back off."""
    if not vcs_enabled():
        cmds.optionVar(intValue=("ueBridgeVcs", 0))
        return
    root = _saved_root()
    if not root or not os.path.isdir(root):
        root = _pick_root()
        if not root:
            cmds.checkBox(_VCS, edit=True, value=False)
            cmds.optionVar(intValue=("ueBridgeVcs", 0))
            _status("version control needs the source project folder")
            return
        _apply_root(root)
    cmds.optionVar(intValue=("ueBridgeVcs", 1))


def _change_root():
    root = _pick_root()
    if root:
        _apply_root(root)


def _load_dir_map():
    if not cmds.optionVar(exists="ueBridgeVcsDirMap"):
        return {}
    try:
        return json.loads(cmds.optionVar(query="ueBridgeVcsDirMap") or "{}")
    except ValueError:
        return {}


def _save_dir_map(dir_map):
    cmds.optionVar(stringValue=("ueBridgeVcsDirMap", json.dumps(dir_map)))


def _ask_which_file(paths):
    kwargs = {"fileMode": 1, "dialogStyle": 2, "fileFilter": "FBX (*.fbx)",
              "caption": "Several working fbx match - pick the one to use",
              "startingDirectory": os.path.dirname(paths[0])}
    picked = cmds.fileDialog2(**kwargs) or []
    return picked[0] if picked else ""


def _ask_new_folder(name):
    kwargs = {"fileMode": 3, "dialogStyle": 2,
              "caption": "Folder for the new {0}.fbx".format(name)}
    saved = _saved_root()
    if saved and os.path.isdir(saved):
        kwargs["startingDirectory"] = saved
    picked = cmds.fileDialog2(**kwargs) or []
    return picked[0] if picked else ""


def _ask_others(users):
    answer = cmds.confirmDialog(
        title="Perforce", icon="warning",
        message="Already checked out by:\n  {0}".format("\n  ".join(users)),
        button=["Overwrite locally", "Cancel"], defaultButton="Cancel",
        cancelButton="Cancel", dismissString="Cancel")
    return answer == "Overwrite locally"


def _ask_failure(reason):
    answer = cmds.confirmDialog(
        title="Perforce", icon="warning", message=reason,
        button=["Continue locally", "Cancel"], defaultButton="Cancel",
        cancelButton="Cancel", dismissString="Cancel")
    return answer == "Continue locally"


def _vcs_target(record, asks=None):
    """The working-file path for this asset: (target, is_new), or None when
    the user cancelled. `asks` overrides the dialogs - the live verify drives
    this over the command port, where a modal would block Maya (bridge
    note 6)."""
    asks = asks or {}
    root = _saved_root()
    if not root or not os.path.isdir(root):
        root = asks.get("root", _pick_root)()
        if not root:
            return None
        _apply_root(root)
    dir_map = _load_dir_map()
    target, grown = vcs.choose_target(
        record.name, record.package, root, dir_map,
        asks.get("file", _ask_which_file), asks.get("folder", _ask_new_folder))
    if grown != dir_map:
        _save_dir_map(grown)
    if not target:
        return None
    return target, not os.path.exists(target)


def with_vcs_suffix(line, suffix):
    """Pure - the status wording is tested without widgets."""
    if not suffix:
        return line
    return "{0}  |  {1}".format(line, suffix)
```

3c. Rework `import_selected` — replace its body between selecting the record and the status write with:

```python
def import_selected():
    """Export the selected animation from the editor and bring it in."""
    record = _selected_record()
    if record is None:
        _status("select an animation first")
        return

    # Resolve the working file BEFORE the export: path dialogs first, and a
    # cancel costs nothing. p4 runs AFTER the export: no depot state is
    # touched until a new file actually exists to place.
    target, is_new = None, False
    if vcs_enabled():
        resolved = _vcs_target(record)
        if resolved is None:
            _status("import cancelled")
            return
        target, is_new = resolved

    out = os.path.join(temp_folder(), "export.json")
    fbx = os.path.join(temp_folder(), "{0}.fbx".format(record.name))
    # Export from the same editor the list came from, or a second open project
    # would answer with an asset path it does not have.
    payload = uelink.run_script(uescripts.export_script(out, record.package, fbx),
                                out, project=project_choice())

    exported = payload.get("path") or fbx
    suffix = ""
    if target:
        proceed, note = vcs.prepare_target(target, _ask_others, _ask_failure)
        if not proceed:
            _status("import cancelled - {0} untouched".format(
                os.path.basename(target)))
            return
        vcs.place(exported, target)
        suffix = vcs.status_suffix(target, _saved_root(), is_new, note)

    merge = merge_selected()
    namespace = ("" if merge else
                 records.namespace_for(record.name,
                                       animimport.existing_namespaces()))
    set_timeline = cmds.checkBox(_TIMELINE, query=True, value=True)

    cmds.undoInfo(openChunk=True, chunkName="UE anim import")
    try:
        info = animimport.import_clip(
            target or exported,
            namespace,
            set_timeline=set_timeline,
            clip_fps=payload.get("fps") or record.fps,
            merge=merge)
    finally:
        cmds.undoInfo(closeChunk=True)

    _status(with_vcs_suffix(import_line(record.name, info), suffix))
```

3d. The UI row in `show_window` — after the `mode` radio group creation, add:

```python
    saved_vcs = bool(cmds.optionVar(query="ueBridgeVcs")) if cmds.optionVar(
        exists="ueBridgeVcs") else False
    vcs_check = cmds.checkBox(
        _VCS, label="Connect to version control", value=saved_vcs,
        changeCommand=lambda *_: _run(_vcs_toggled))
    vcs_root = cmds.text(_VCSROOT, label=_root_label(_saved_root()),
                         align="left", enable=saved_vcs)
    vcs_pick = cmds.button(label="...", width=30,
                           command=lambda *_: _run(_change_root))
```

and make the checkbox toggle also flip the label's enable state — add to the end of `_vcs_toggled` (both branches): `cmds.text(_VCSROOT, edit=True, enable=vcs_enabled())` (guard with `exists=True` as `_apply_root` does; simplest is one line at the top: `if cmds.text(_VCSROOT, exists=True): cmds.text(_VCSROOT, edit=True, enable=vcs_enabled())`).

In the `formLayout(... edit=True ...)` call, wire the new row between `mode` and `timeline`:

- to `attachForm` add: `(vcs_check, "left", 8)`, `(vcs_pick, "right", 8)`
- to `attachControl` add: `(vcs_check, "bottom", 6, timeline)`, `(vcs_root, "bottom", 6, timeline)`, `(vcs_pick, "bottom", 6, timeline)`, `(vcs_root, "left", 10, vcs_check)`, `(vcs_root, "right", 6, vcs_pick)`
- change the existing `(scroll, "bottom", 8, mode)` chain: `mode` now attaches above the vcs row — replace `(mode, "bottom", 6, timeline)` with `(mode, "bottom", 6, vcs_check)`.

- [ ] **Step 4: Run the window tests**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_uebridge_window -v`
Expected: PASS.

- [ ] **Step 5: Run the whole suite**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v`
Expected: every test green (714 + the new ones).

- [ ] **Step 6: Commit**

```bash
git add maya_uebridge/window.py tests/test_uebridge_window.py
git commit -m "feat(uebridge): Connect to version control - the checkbox and the import flow"
```

---

### Task 7: the live verify script and the working notes

**Files:**
- Create: `docs/superpowers/plans/verify_uebridge_vcs.py`
- Modify: `CLAUDE.md` (the `maya_uebridge` section)

**Interfaces:**
- Consumes: `window._vcs_target(record, asks)`, `vcs.*` — everything above.

- [ ] **Step 1: Write the verify script.** Gates, all against a **sandbox root** (never the real SourceArt — a verification run must not overwrite the animator's working files) and **never mutating the depot**:

```python
"""Live verification: the UE bridge's Perforce placement.

Run in the user's Maya through the command port. Uses a SANDBOX source root
in Maya's temp folder - the real SourceArt is never written - and mutates
the depot not at all: the p4 gates are fstat reads; the edit branch is
proved by unit tests over captured output. Dialog-bearing paths get injected
answers (a modal over the command port blocks Maya - bridge note 6).

Gates:
 1. vcs.find_fbx finds the planted file by name, case-insensitively
 2. choose_target: single hit taken silently
 3. choose_target: ambiguity resolved by the injected pick, remembered
 4. choose_target: new file lands in the planted conventional folder
 5. choose_target: new file with no folder asks, remembers, second call silent
 6. conventional_folder on the real example package matches the real folder
    on disk (read-only isdir check against the true SourceArt)
 7. real p4 fstat on the tracked example uasset parses: depotFile present,
    plan kind in ("edit", "others", "mine")
 8. real p4 fstat on the sandbox fbx answers untracked, prepare_target
    proceeds with "not in depot" and no dialog
 9. place() overwrites a read-only sandbox target and the bytes change
10. animimport.import_clip on the placed fbx AS A NEW NAMESPACED SKELETON
    (merge=False, so the user's scene skeleton is untouched) animates joints
11. window._vcs_target with injected asks resolves end to end and the dir
    map optionVar grows
"""
```

The script follows the repo's bridge-runner conventions: `if not os.path.exists(marker)` guard (never `raise SystemExit` — working-notes note 8), unique output file per run, results printed with a final `VERDICT: N of M gates failed` line, every cleanup step in a guarded `finally` (trap 42), `sys.path.insert(0, REPO)` plus purging the `maya_uebridge` tree from `sys.modules` before importing (note 9). For gate 10 the "exported temp" is simulated by copying the real `AS_Unarmed_Idle_1P.fbx` — no UE editor needed. Cleanup deletes the sandbox tree, the imported namespace (`cmds.namespace(removeNamespace=..., deleteNamespaceContent=True)`), and restores the `ueBridgeVcsDirMap`/`ueBridgeVcsRoot`/`ueBridgeVcs` optionVars to what they held before the run.

- [ ] **Step 2: Update `CLAUDE.md`.** In the `maya_uebridge` module table add the row `| vcs.py | Perforce placement: name search, path convention, checkout decision table, p4 runner | **stdlib only** |`; after the "weapon-driven `weapon_r`" paragraph add a short paragraph: the checkbox, the search-by-name rule, the convention for new files, the no-p4-add decision, the dialogs' injectability, and the two p4 parsing facts (exit 0 on "no such file(s)", the `... ...` double prefix). Note the verify script and its sandbox-root rule.

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/plans/verify_uebridge_vcs.py CLAUDE.md
git commit -m "docs(uebridge): vcs verify script and working notes"
```

---

### Task 8: live verification through the bridge

**Files:**
- Uses: `docs/superpowers/plans/verify_uebridge_vcs.py`
- Scratchpad: runner + sender scripts (rebuilt per working notes)

- [ ] **Step 1: Check the port** — `Get-NetTCPConnection -State Listen -LocalPort 7001`. If nothing listens, stop here and report: the user must run the command-port one-liner; the live gates wait for the next session.

- [ ] **Step 2: Build the runner and sender in the scratchpad** following every bridge note: BOM-less write (`[System.IO.File]::WriteAllText` with `UTF8Encoding($false)`), `if not os.path.exists(marker)` guard with no SystemExit, `exec(compile(src, path, "exec"), {"__name__": "__main__"})`, unique output filename, poll for the script's final `VERDICT` line (the file exists from the first print).

- [ ] **Step 3: Send, poll, read the verdict.** Expected: `VERDICT: 0 of 11 gates failed`. Any failed gate: fix, re-run (fresh output name each time).

- [ ] **Step 4: Refresh the installed copy** so the user's shelf gets the new window (note 9): send `install.install(quiet=True)` from the repo's `install.py` through the bridge, purging the `install` module first.

- [ ] **Step 5: Commit any fixes; report the verdict in the final summary.**
