# Weapon attach module — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Maya window that puts a chosen weapon model into `weapon_r` of the
skeleton the Rig Picker is bound to, with live rotate/translate offsets that
are remembered per weapon between sessions.

**Architecture:** A root-level package `maya_weapons` in four modules —
`catalog.py` (pure weapon table), `skeleton.py` (which character, which bone),
`attach.py` (import, parent, offsets), `window.py` (the `cmds` UI). The picker
gains one module-level accessor, `bound_root()`, and nothing else. The fiddly
logic lives in pure functions taking the scene as data; the Maya-touching
wrappers stay thin and are proved live.

**Tech Stack:** Python 2/3-compatible `maya.cmds` (Maya 2027), stdlib
`unittest` run under `mayapy`, no Qt anywhere in this package.

Spec: `docs/superpowers/specs/2026-08-17-weapon-attach-design.md`.

## Global Constraints

- **`catalog.py` imports stdlib only.** No `maya`, no Qt. A subprocess test
  enforces it, the way `tests/test_bodymap.py` does for `bodymap.py`.
- **`__init__.py` resolves `show_window` through `__getattr__`**, so importing
  the package does not drag Maya in.
- **Never identify a rig node by name.** The attached weapon is found by its
  `mayaWeapon` string attribute.
- **Never look a bone up scene-wide.** Every lookup goes through
  `naming.hierarchy_map(root)` on the bound root's subtree.
- **Tests inject a fake `maya.cmds` into `sys.modules` and rebind the module
  attribute.** Never delete from `sys.modules` to force a re-import — the
  stale module stays bound to the parent package (recorded in `CLAUDE.md`).
- Run the suite with:
  `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v`
  Do not pipe `2>&1` in PowerShell; unittest writes to stderr and 5.1 turns
  that into `NativeCommandError` noise.
- Commit messages go through a file (`git commit -F`) — here-strings with
  double quotes break in this shell.
- Style: module docstrings explain *why*, comments are sparse and only where
  the code cannot say it itself. Match the surrounding repo.

---

### Task 1: The weapon catalog

**Files:**
- Create: `maya_weapons/__init__.py`
- Create: `maya_weapons/catalog.py`
- Test: `tests/test_weapons_catalog.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `Weapon` namedtuple with fields `key, label, path, bone, scale`;
  `WEAPONS` (list of `Weapon`); `labels() -> list[str]`;
  `by_label(label) -> Weapon | None`; `by_key(key) -> Weapon | None`;
  `missing(entry) -> str` (the path when the file is not on disk, `""` when it
  is).

- [ ] **Step 1: Write the failing test**

Create `tests/test_weapons_catalog.py`:

```python
"""Tests for the weapon table.

It is pure data with lookups over it, so it needs neither Maya nor Qt -- and
the first test here is what keeps it that way.
"""

import os
import subprocess
import sys
import unittest

from maya_weapons import catalog


class MayaFreeBoundary(unittest.TestCase):
    """catalog must stay importable with no Maya and no Qt loaded.

    Checked in a fresh interpreter: by the time the rest of the suite has run,
    maya.cmds is already in this process's sys.modules.
    """

    def test_importing_catalog_pulls_in_neither_maya_nor_qt(self):
        script = (
            "import sys\n"
            "from maya_weapons import catalog\n"
            "leaked = [m for m in sys.modules\n"
            "          if m.startswith('maya.') or m.startswith('PySide6')]\n"
            "print(';'.join(sorted(leaked)))\n"
        )
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=repo_root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "",
                         "importing catalog leaked: " + result.stdout.strip())


class Table(unittest.TestCase):

    def test_holds_the_long_sword(self):
        entry = catalog.by_key("LongSword_02")
        self.assertIsNotNone(entry)
        self.assertTrue(entry.path.endswith("LongSword_02.fbx"))

    def test_the_sword_goes_to_the_right_hand(self):
        self.assertEqual(catalog.by_key("LongSword_02").bone, "weapon_r")

    def test_paths_use_forward_slashes(self):
        """A backslash starts an escape in the MEL the FBX plugin sees."""
        for entry in catalog.WEAPONS:
            self.assertNotIn("\\", entry.path, entry.key)

    def test_keys_are_unique(self):
        keys = [entry.key for entry in catalog.WEAPONS]
        self.assertEqual(len(keys), len(set(keys)))

    def test_labels_are_unique(self):
        """The dropdown resolves a pick by its label, so duplicates would hide
        an entry the animator can see."""
        found = catalog.labels()
        self.assertEqual(len(found), len(set(found)))

    def test_labels_are_in_table_order(self):
        self.assertEqual(catalog.labels(),
                         [entry.label for entry in catalog.WEAPONS])


class Lookups(unittest.TestCase):

    def test_by_label_finds_the_entry(self):
        entry = catalog.WEAPONS[0]
        self.assertIs(catalog.by_label(entry.label), entry)

    def test_by_label_is_none_for_a_stranger(self):
        self.assertIsNone(catalog.by_label("Halberd"))

    def test_by_key_is_none_for_a_stranger(self):
        self.assertIsNone(catalog.by_key("Halberd"))


class OnDisk(unittest.TestCase):

    def test_missing_names_the_path_that_is_not_there(self):
        entry = catalog.Weapon("X", "X", "C:/nowhere/X.fbx", "weapon_r", 1.0)
        self.assertEqual(catalog.missing(entry), "C:/nowhere/X.fbx")

    def test_missing_is_empty_for_a_file_that_exists(self):
        here = os.path.abspath(__file__).replace("\\", "/")
        entry = catalog.Weapon("X", "X", here, "weapon_r", 1.0)
        self.assertEqual(catalog.missing(entry), "")
```

- [ ] **Step 2: Run it and watch it fail**

```bash
'/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe' -m unittest tests.test_weapons_catalog -v
```

Expected: `ModuleNotFoundError: No module named 'maya_weapons'`.

- [ ] **Step 3: Write `maya_weapons/__init__.py`**

```python
"""Put weapon models into a character's hands.

`show_window` is resolved lazily on first access, the way the other packages
here do it: importing it eagerly would drag maya.cmds in through the package
and break the rule that catalog.py is testable in plain Python.
"""

__all__ = ["show_window"]


def __getattr__(name):
    if name == "show_window":
        from maya_weapons.window import show_window
        return show_window
    raise AttributeError(
        "module {0!r} has no attribute {1!r}".format(__name__, name))
```

- [ ] **Step 4: Write `maya_weapons/catalog.py`**

```python
"""The weapon table: what can be attached, and where it goes.

The target bone is a property of the entry rather than a constant in the code,
so a shield later is one line with `weapon_l` and no logic to touch. `scale` is
here for the same reason: a model that arrives at the wrong size is a fact
about that model, not something the animator should retype every time.

Paths are written with forward slashes. The FBX plugin is driven through MEL,
where a backslash starts an escape.
"""

import collections
import os

Weapon = collections.namedtuple("Weapon", "key label path bone scale")

WEAPONS = [
    Weapon("LongSword_02", "Long Sword 02",
           "C:/!!!Work/Animations/Sources/LongSword_02.fbx", "weapon_r", 1.0),
]


def labels():
    """Dropdown labels, in table order."""
    return [entry.label for entry in WEAPONS]


def by_label(label):
    for entry in WEAPONS:
        if entry.label == label:
            return entry
    return None


def by_key(key):
    for entry in WEAPONS:
        if entry.key == key:
            return entry
    return None


def missing(entry):
    """The entry's path if the file is not on disk, "" if it is."""
    return "" if os.path.isfile(entry.path) else entry.path
```

- [ ] **Step 5: Run the tests**

```bash
'/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe' -m unittest tests.test_weapons_catalog -v
```

Expected: 12 tests, all passing.

- [ ] **Step 6: Commit**

```bash
git add maya_weapons/__init__.py maya_weapons/catalog.py tests/test_weapons_catalog.py
git commit -F <message file>
```

Message: `feat(weapons): the weapon table, and the package around it`

---

### Task 2: Which character, which bone

**Files:**
- Create: `maya_weapons/skeleton.py`
- Modify: `maya_overrig/picker_window.py` (one module-level function at the
  end of the file, next to `show_picker`)
- Test: `tests/test_weapons_skeleton.py`

**Interfaces:**
- Consumes: `maya_overrig.naming` (`find_root`, `hierarchy_map`,
  `detect_prefix`, `strip_prefix`), `maya_overrig.builder.character_roots`,
  `maya_overrig.bodymap.BUTTONS`.
- Produces:
  - `maya_overrig.picker_window.bound_root() -> str | None` — the open
    picker's bound root path.
  - `skeleton.choose_root(picker_root, selection_roots, scene_roots) -> str | None`
    (pure).
  - `skeleton.bone_in(hierarchy, bone_name) -> str | None` (pure) — long path
    of the named bone in a prefix-stripped hierarchy map.
  - `skeleton.current_root() -> str | None`
  - `skeleton.resolve_bone(root, bone_name) -> str | None`

- [ ] **Step 1: Write the failing test**

Create `tests/test_weapons_skeleton.py`:

```python
"""Tests for picking the character and finding the bone inside it.

The decision itself is a pure function over data -- which picker binding,
which selection, which scene roots -- so it is exercised without Maya. The
thin wrappers that read those three things out of the scene are proved live by
docs/superpowers/plans/verify_weapons.py.
"""

import sys
import types
import unittest


def _install_fake_maya():
    """Let skeleton import without Maya. See CLAUDE.md on rebinding."""
    if "maya.cmds" in sys.modules:
        return
    maya = types.ModuleType("maya")
    cmds = types.ModuleType("maya.cmds")
    mel = types.ModuleType("maya.mel")
    maya.cmds = cmds
    maya.mel = mel
    sys.modules.setdefault("maya", maya)
    sys.modules["maya.cmds"] = cmds
    sys.modules["maya.mel"] = mel


_install_fake_maya()

from maya_weapons import skeleton  # noqa: E402

MANNY = "|SKM_Manny|root"
SUIT = "|Mesh_protective_suit|root"


class ChooseRoot(unittest.TestCase):

    def test_the_picker_wins_when_it_is_bound(self):
        """The point of the module: the same character the picker drives."""
        self.assertEqual(
            skeleton.choose_root(MANNY, [SUIT], [MANNY, SUIT]), MANNY)

    def test_selection_answers_when_the_picker_is_closed(self):
        self.assertEqual(
            skeleton.choose_root(None, [SUIT], [MANNY, SUIT]), SUIT)

    def test_several_joints_of_one_character_are_one_answer(self):
        """find_root maps every selected bone to the same root."""
        self.assertEqual(
            skeleton.choose_root(None, [MANNY, MANNY, MANNY], [MANNY, SUIT]),
            MANNY)

    def test_two_characters_selected_is_no_answer(self):
        """Arming the wrong character in silence is worse than saying no."""
        self.assertIsNone(
            skeleton.choose_root(None, [MANNY, SUIT], [MANNY, SUIT]))

    def test_a_lone_skeleton_answers_with_nothing_selected(self):
        self.assertEqual(skeleton.choose_root(None, [], [MANNY]), MANNY)

    def test_two_skeletons_and_no_hint_is_no_answer(self):
        self.assertIsNone(skeleton.choose_root(None, [], [MANNY, SUIT]))

    def test_an_empty_scene_is_no_answer(self):
        self.assertIsNone(skeleton.choose_root(None, [], []))

    def test_selection_outside_any_skeleton_is_ignored(self):
        """naming.find_root returns None for a light or a mesh."""
        self.assertEqual(skeleton.choose_root(None, [None, None], [MANNY]),
                         MANNY)


class BoneIn(unittest.TestCase):

    def test_finds_the_bone(self):
        hierarchy = {"root": MANNY, "weapon_r": MANNY + "|weapon_r"}
        self.assertEqual(skeleton.bone_in(hierarchy, "weapon_r"),
                         MANNY + "|weapon_r")

    def test_is_none_when_the_skeleton_has_no_such_bone(self):
        """A UE4-schema rig may carry no weapon bone at all."""
        self.assertIsNone(skeleton.bone_in({"root": MANNY}, "weapon_r"))

    def test_reads_a_namespaced_hierarchy(self):
        """hierarchy_map strips namespaces from the keys, not the values."""
        hierarchy = {"weapon_r": "|hero:root|hero:weapon_r"}
        self.assertEqual(skeleton.bone_in(hierarchy, "weapon_r"),
                         "|hero:root|hero:weapon_r")
```

- [ ] **Step 2: Run it and watch it fail**

```bash
'/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe' -m unittest tests.test_weapons_skeleton -v
```

Expected: `ModuleNotFoundError: No module named 'maya_weapons.skeleton'`.

- [ ] **Step 3: Add the accessor to the picker**

In `maya_overrig/picker_window.py`, directly **above** `def show_picker():`:

```python
def bound_root():
    """The open picker's bound skeleton root, or None.

    Companion tools ask this so they act on the character the animator is
    already driving. The binding lives in the live window and is not persisted
    anywhere, so there is nothing else to read it out of.
    """
    for widget in QtWidgets.QApplication.topLevelWidgets():
        if widget.objectName() == WINDOW_OBJECT_NAME:
            return widget.bound_root()
    return None
```

- [ ] **Step 4: Write `maya_weapons/skeleton.py`**

```python
"""Which character to arm, and where its weapon bone is.

The picker holds its binding in the live window, so when it is open that is
the answer -- the whole point of the module is to act on the character the
animator is already driving. With no picker the module binds the same way the
picker itself does, and refuses to guess between two candidates: arming the
wrong character in silence is worse than saying no.

The bone is looked up inside the bound root's subtree, never scene-wide. That
is what makes a namespace, a per-joint prefix or a second character in the
scene a non-issue -- and a scene-wide `ls("weapon_r")` would arm whichever
character Maya happened to list first.
"""

import maya.cmds as cmds

from maya_overrig import bodymap
from maya_overrig import naming


def picker_root():
    """The root the Rig Picker is bound to, or None if it is not open."""
    try:
        from maya_overrig import picker_window
    except ImportError:
        return None  # no Qt in this session; the fallbacks still work
    return picker_window.bound_root()


def choose_root(picker_root_path, selection_roots, scene_roots):
    """Decide which skeleton to act on. Pure: the scene arrives as data."""
    if picker_root_path:
        return picker_root_path

    # dict.fromkeys keeps order and collapses the repeats that come from
    # selecting several bones of the same character.
    selected = list(dict.fromkeys(root for root in selection_roots if root))
    if len(selected) == 1:
        return selected[0]
    if selected:
        return None

    if len(scene_roots) == 1:
        return scene_roots[0]
    return None


def current_root():
    """Ask the scene the three questions and let `choose_root` decide."""
    from maya_overrig import builder  # drags maya.mel in; not needed to import

    selection = cmds.ls(selection=True, long=True) or []
    return choose_root(picker_root(),
                       [naming.find_root(node) for node in selection],
                       builder.character_roots())


def bone_in(hierarchy, bone_name):
    """Long path of `bone_name` in a prefix-stripped hierarchy map, or None."""
    return hierarchy.get(bone_name)


def resolve_bone(root, bone_name):
    """Long path of `bone_name` inside `root`'s subtree, or None.

    The prefix is derived once for the whole skeleton, exactly as the picker
    derives it, so a rig imported as `char_weapon_r` resolves too.
    """
    if not root:
        return None
    raw = naming.hierarchy_map(root)
    known = [button.joint for button in bodymap.BUTTONS]
    prefix = naming.detect_prefix(raw, known)
    return bone_in(naming.strip_prefix(raw, prefix), bone_name)
```

- [ ] **Step 5: Run the tests**

```bash
'/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe' -m unittest tests.test_weapons_skeleton -v
```

Expected: 11 tests, all passing.

- [ ] **Step 6: Run the whole suite — the picker was touched**

```bash
'/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe' -m unittest discover -s tests -t . -v
```

Expected: every previously passing test still passes.

- [ ] **Step 7: Commit**

```bash
git add maya_weapons/skeleton.py maya_overrig/picker_window.py tests/test_weapons_skeleton.py
git commit -F <message file>
```

Message: `feat(weapons): take the character from the picker, the bone from its subtree`

---

### Task 3: Attaching the model

**Files:**
- Create: `maya_weapons/attach.py`
- Test: `tests/test_weapons_attach.py`

**Interfaces:**
- Consumes: `catalog.Weapon` (fields `key, path, bone, scale`).
- Produces:
  - `attach.MARKER` = `"mayaWeapon"`
  - `attach.carrier_name(key) -> str`
  - `attach.outermost(paths) -> list[str]` (pure)
  - `attach.find_attached(bone) -> str | None`
  - `attach.remove_attached(bone) -> str | None`
  - `attach.import_model(path) -> list[str]`
  - `attach.attach(entry, bone, rotate, translate) -> str` (carrier long path)
  - `attach.read_offsets(carrier) -> (tuple, tuple)`
  - `attach.write_offsets(carrier, rotate, translate) -> None`

- [ ] **Step 1: Write the failing test**

Create `tests/test_weapons_attach.py`:

```python
"""Tests for the attach mechanics.

The import itself needs a live Maya and a real FBX, so it is proved by
docs/superpowers/plans/verify_weapons.py. What is testable here is everything
around it: which imported transforms are the roots, how the attached weapon is
recognised, and that writing offsets cannot leave autoKey on.
"""

import sys
import types
import unittest


def _install_fake_maya():
    """Let attach import without Maya. See CLAUDE.md on rebinding."""
    if "maya.cmds" in sys.modules:
        return
    maya = types.ModuleType("maya")
    cmds = types.ModuleType("maya.cmds")
    mel = types.ModuleType("maya.mel")
    maya.cmds = cmds
    maya.mel = mel
    sys.modules.setdefault("maya", maya)
    sys.modules["maya.cmds"] = cmds
    sys.modules["maya.mel"] = mel


_install_fake_maya()

from maya_weapons import attach  # noqa: E402

BONE = "|SKM_Manny|root|hand_r|weapon_r"


class FakeCmds(object):
    """Enough of maya.cmds for the child walk and the attribute writes."""

    def __init__(self, children=(), marked=()):
        self._children = list(children)
        self._marked = set(marked)
        self.attrs = {}
        self.deleted = []
        self.autokey = True
        self.autokey_during_write = []

    def listRelatives(self, node, children=False, type=None, fullPath=False,
                      **kwargs):
        if not children:
            return None
        return [c for c in self._children if c.rsplit("|", 1)[0] == node] or None

    def attributeQuery(self, name, node=None, exists=False, **kwargs):
        return node in self._marked and name == attach.MARKER

    def delete(self, node):
        self.deleted.append(node)

    def setAttr(self, plug, *values, **kwargs):
        self.attrs[plug] = values[0] if len(values) == 1 else values
        self.autokey_during_write.append(self.autokey)

    def getAttr(self, plug):
        return self.attrs.get(plug, 0.0)

    def autoKeyframe(self, query=False, state=None):
        if query:
            return self.autokey
        self.autokey = state


class Outermost(unittest.TestCase):
    """Which of the imported transforms go into the carrier."""

    def test_keeps_a_lone_transform(self):
        self.assertEqual(attach.outermost(["|sword"]), ["|sword"])

    def test_drops_the_children(self):
        self.assertEqual(
            attach.outermost(["|sword", "|sword|blade", "|sword|grip"]),
            ["|sword"])

    def test_keeps_two_unrelated_roots(self):
        self.assertEqual(attach.outermost(["|sword", "|scabbard"]),
                         ["|sword", "|scabbard"])

    def test_a_shared_prefix_is_not_containment(self):
        """'|swordExtra' is not a child of '|sword'. The separator is the test."""
        self.assertEqual(attach.outermost(["|sword", "|swordExtra"]),
                         ["|sword", "|swordExtra"])

    def test_empty_stays_empty(self):
        self.assertEqual(attach.outermost([]), [])


class CarrierName(unittest.TestCase):

    def test_names_the_carrier_after_the_weapon(self):
        self.assertEqual(attach.carrier_name("LongSword_02"),
                         "LongSword_02_weapon")


class FindAttached(unittest.TestCase):

    def test_finds_the_marked_child(self):
        fake = FakeCmds(children=[BONE + "|prop", BONE + "|LongSword_02_weapon"],
                        marked=[BONE + "|LongSword_02_weapon"])
        attach.cmds = fake
        self.assertEqual(attach.find_attached(BONE),
                         BONE + "|LongSword_02_weapon")

    def test_ignores_children_the_animator_parented_by_hand(self):
        """Only what this module attached is ours to delete."""
        fake = FakeCmds(children=[BONE + "|LongSword_02_weapon"], marked=[])
        attach.cmds = fake
        self.assertIsNone(attach.find_attached(BONE))

    def test_is_none_when_the_bone_is_bare(self):
        attach.cmds = FakeCmds()
        self.assertIsNone(attach.find_attached(BONE))

    def test_remove_deletes_only_the_marked_child(self):
        fake = FakeCmds(children=[BONE + "|prop", BONE + "|LongSword_02_weapon"],
                        marked=[BONE + "|LongSword_02_weapon"])
        attach.cmds = fake
        attach.remove_attached(BONE)
        self.assertEqual(fake.deleted, [BONE + "|LongSword_02_weapon"])

    def test_remove_on_a_bare_bone_deletes_nothing(self):
        fake = FakeCmds()
        attach.cmds = fake
        self.assertIsNone(attach.remove_attached(BONE))
        self.assertEqual(fake.deleted, [])


class Offsets(unittest.TestCase):

    def setUp(self):
        self.fake = FakeCmds()
        attach.cmds = self.fake

    def test_writes_all_six_channels(self):
        attach.write_offsets("|c", (10.0, 20.0, 30.0), (1.0, 2.0, 3.0))
        self.assertEqual(self.fake.attrs["|c.rotateY"], 20.0)
        self.assertEqual(self.fake.attrs["|c.translateZ"], 3.0)

    def test_autokey_is_off_for_every_write(self):
        """The user works with autoKey ON; a scripted poke must not key."""
        attach.write_offsets("|c", (10.0, 0.0, 0.0), (0.0, 0.0, 0.0))
        self.assertEqual(set(self.fake.autokey_during_write), {False})

    def test_autokey_is_put_back(self):
        attach.write_offsets("|c", (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
        self.assertTrue(self.fake.autokey)

    def test_autokey_is_put_back_even_when_a_write_blows_up(self):
        def boom(plug, *values, **kwargs):
            raise RuntimeError("locked channel")
        self.fake.setAttr = boom
        with self.assertRaises(RuntimeError):
            attach.write_offsets("|c", (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
        self.assertTrue(self.fake.autokey)

    def test_reads_what_it_wrote(self):
        attach.write_offsets("|c", (10.0, 20.0, 30.0), (1.0, 2.0, 3.0))
        rotate, translate = attach.read_offsets("|c")
        self.assertEqual(rotate, (10.0, 20.0, 30.0))
        self.assertEqual(translate, (1.0, 2.0, 3.0))
```

- [ ] **Step 2: Run it and watch it fail**

```bash
'/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe' -m unittest tests.test_weapons_attach -v
```

Expected: `ModuleNotFoundError: No module named 'maya_weapons.attach'`.

- [ ] **Step 3: Write `maya_weapons/attach.py`**

```python
"""Put a weapon model into a bone, and move it once it is there.

Attachment is a plain DAG parent: the model hangs under the bone and inherits
its motion. What the animator adjusts is the CARRIER -- a transform of ours
between the bone and the imported model -- so the offsets live on a node this
module owns and the imported geometry keeps whatever the artist authored.

The carrier is found by a string attribute, never by name. Maya uniquifies
imported names, the animator may rename anything, and every tool in this repo
that identified a node by name has paid for it.
"""

import maya.cmds as cmds

MARKER = "mayaWeapon"


def carrier_name(key):
    return "{0}_weapon".format(key)


def outermost(paths):
    """The paths with no ancestor among the others.

    The trailing separator is the whole test: `|swordExtra` is not a child of
    `|sword`, and a plain startswith would swallow it.
    """
    return [path for path in paths
            if not any(path.startswith(other + "|")
                       for other in paths if other != path)]


def find_attached(bone):
    """The carrier this module put in `bone`, or None."""
    children = cmds.listRelatives(bone, children=True, type="transform",
                                  fullPath=True) or []
    for child in children:
        if cmds.attributeQuery(MARKER, node=child, exists=True):
            return child
    return None


def remove_attached(bone):
    """Delete our carrier under `bone`. Returns what was removed, or None."""
    carrier = find_attached(bone)
    if carrier:
        cmds.delete(carrier)
    return carrier


def import_model(path):
    """Import `path` and return the transforms that arrived at world level.

    `cmds.file` rather than the plugin's `FBXImport`, which is the opposite of
    what the UE bridge does and is deliberate: trap 22 is about losing
    animation curves, and there is no animation in a weapon model, while
    `returnNewNodes` gives the exact node list `FBXImport` cannot report at all.
    """
    if not cmds.pluginInfo("fbxmaya", query=True, loaded=True):
        cmds.loadPlugin("fbxmaya", quiet=True)

    new = cmds.file(path, i=True, type="FBX", returnNewNodes=True,
                    ignoreVersion=True) or []
    return outermost(cmds.ls(new, long=True, type="transform") or [])


def write_offsets(carrier, rotate, translate):
    """Set the carrier's local rotate and translate.

    autoKey is off for the duration. The carrier carries no curves, so it
    would not fire -- but the user works with autoKey ON and this repo has
    already paid for assuming a scripted poke is harmless.
    """
    state = cmds.autoKeyframe(query=True, state=True)
    cmds.autoKeyframe(state=False)
    try:
        for axis, value in zip("XYZ", rotate):
            cmds.setAttr("{0}.rotate{1}".format(carrier, axis), value)
        for axis, value in zip("XYZ", translate):
            cmds.setAttr("{0}.translate{1}".format(carrier, axis), value)
    finally:
        cmds.autoKeyframe(state=state)


def read_offsets(carrier):
    """The carrier's local rotate and translate, as two triples."""
    rotate = tuple(cmds.getAttr("{0}.rotate{1}".format(carrier, axis))
                   for axis in "XYZ")
    translate = tuple(cmds.getAttr("{0}.translate{1}".format(carrier, axis))
                      for axis in "XYZ")
    return rotate, translate


def attach(entry, bone, rotate=(0.0, 0.0, 0.0), translate=(0.0, 0.0, 0.0)):
    """Put `entry`'s model into `bone` and return the carrier's long path.

    Whatever this module attached there before is removed first: one weapon per
    bone, so the offset fields always have exactly one thing to move. All of it
    is one undo chunk -- a half-undone import leaves geometry with no home.
    """
    cmds.undoInfo(openChunk=True)
    try:
        remove_attached(bone)

        roots = import_model(entry.path)
        if not roots:
            raise RuntimeError("nothing came out of " + entry.path)

        carrier = cmds.group(roots, name=carrier_name(entry.key), world=True)
        cmds.addAttr(carrier, longName=MARKER, dataType="string")
        cmds.setAttr(carrier + "." + MARKER, entry.key, type="string")

        carrier = cmds.ls(cmds.parent(carrier, bone)[0], long=True)[0]
        for axis in "XYZ":
            cmds.setAttr("{0}.translate{1}".format(carrier, axis), 0.0)
            cmds.setAttr("{0}.rotate{1}".format(carrier, axis), 0.0)
            cmds.setAttr("{0}.scale{1}".format(carrier, axis), entry.scale)

        write_offsets(carrier, rotate, translate)
        return carrier
    finally:
        cmds.undoInfo(closeChunk=True)
```

- [ ] **Step 4: Run the tests**

```bash
'/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe' -m unittest tests.test_weapons_attach -v
```

Expected: 16 tests, all passing.

- [ ] **Step 5: Commit**

```bash
git add maya_weapons/attach.py tests/test_weapons_attach.py
git commit -F <message file>
```

Message: `feat(weapons): import the model and hang it on the bone`

---

### Task 4: The window

**Files:**
- Create: `maya_weapons/window.py`
- Test: `tests/test_weapons_window.py`

**Interfaces:**
- Consumes: `catalog`, `skeleton`, `attach` from the tasks above.
- Produces: `window.show_window()`; the pure helpers
  `optionvar_name(key) -> str`, `pack_offsets(rotate, translate) -> list[float]`,
  `unpack_offsets(values) -> (tuple, tuple)`, `added_message(entry, bone) -> str`,
  `missing_bone_message(root, bone) -> str`, `missing_file_message(path) -> str`,
  `bound_message(root) -> str`, and the constants `NO_CHARACTER`, `NOT_ATTACHED`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_weapons_window.py`:

```python
"""Tests for the window's policy: optionVars, and what the status line says.

The widgets themselves are proved live -- a `cmds` window cannot be built
without Maya. What is testable is everything the callbacks decide before they
touch a widget.
"""

import sys
import types
import unittest


def _install_fake_maya():
    """Let window import without Maya. See CLAUDE.md on rebinding."""
    if "maya.cmds" in sys.modules:
        return
    maya = types.ModuleType("maya")
    cmds = types.ModuleType("maya.cmds")
    mel = types.ModuleType("maya.mel")
    maya.cmds = cmds
    maya.mel = mel
    sys.modules.setdefault("maya", maya)
    sys.modules["maya.cmds"] = cmds
    sys.modules["maya.mel"] = mel


_install_fake_maya()

from maya_weapons import catalog  # noqa: E402
from maya_weapons import window  # noqa: E402

SWORD = catalog.by_key("LongSword_02")


class OptionVars(unittest.TestCase):

    def test_each_weapon_remembers_its_own_grip(self):
        self.assertNotEqual(window.optionvar_name("LongSword_02"),
                            window.optionvar_name("Shield_01"))

    def test_the_name_carries_the_key(self):
        self.assertIn("LongSword_02", window.optionvar_name("LongSword_02"))

    def test_packs_rotate_then_translate(self):
        self.assertEqual(
            window.pack_offsets((10.0, 20.0, 30.0), (1.0, 2.0, 3.0)),
            [10.0, 20.0, 30.0, 1.0, 2.0, 3.0])

    def test_unpacks_what_it_packed(self):
        packed = window.pack_offsets((10.0, 20.0, 30.0), (1.0, 2.0, 3.0))
        self.assertEqual(window.unpack_offsets(packed),
                         ((10.0, 20.0, 30.0), (1.0, 2.0, 3.0)))

    def test_an_unset_optionvar_reads_as_zeros(self):
        """Maya answers a missing optionVar with 0 or an empty list."""
        self.assertEqual(window.unpack_offsets(None),
                         ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0)))
        self.assertEqual(window.unpack_offsets([]),
                         ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0)))

    def test_a_short_optionvar_reads_as_zeros(self):
        """Rather than half a grip from an older version of this tool."""
        self.assertEqual(window.unpack_offsets([1.0, 2.0]),
                         ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0)))

    def test_reads_integers_maya_stored_as_ints(self):
        self.assertEqual(window.unpack_offsets([0, 90, 0, 0, 0, 0]),
                         ((0.0, 90.0, 0.0), (0.0, 0.0, 0.0)))


class Messages(unittest.TestCase):

    def test_no_character_points_at_both_ways_out(self):
        self.assertIn("picker", window.NO_CHARACTER)
        self.assertIn("select", window.NO_CHARACTER)

    def test_missing_bone_names_the_bone_and_the_character(self):
        message = window.missing_bone_message(
            "|SKM_Manny|root", "weapon_r")
        self.assertIn("weapon_r", message)
        self.assertIn("root", message)
        self.assertNotIn("|", message)

    def test_missing_file_names_the_path(self):
        self.assertIn("C:/x/y.fbx", window.missing_file_message("C:/x/y.fbx"))

    def test_added_names_the_weapon_and_the_bone(self):
        message = window.added_message(SWORD, "|SKM_Manny|root|weapon_r")
        self.assertIn(SWORD.label, message)
        self.assertIn("weapon_r", message)
        self.assertNotIn("|", message)

    def test_bound_names_the_character(self):
        self.assertIn("root", window.bound_message("|SKM_Manny|root"))

    def test_bound_says_so_when_nothing_is_bound(self):
        self.assertIn("no", window.bound_message(None).lower())
```

- [ ] **Step 2: Run it and watch it fail**

```bash
'/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe' -m unittest tests.test_weapons_window -v
```

Expected: `ModuleNotFoundError: No module named 'maya_weapons.window'`.

- [ ] **Step 3: Write `maya_weapons/window.py`**

```python
"""The window: pick a weapon, press Add, dial in the grip.

Plain `maya.cmds` -- a dropdown, a button and two float rows need no Qt.

Two habits from the rest of this repo are load-bearing. Every callback goes
through `_run`, which puts the failure on the status line: an exception
escaping a UI callback lands in the Script Editor and the panel just looks
dead. And the offset fields are read back from the scene whenever they might
have gone stale, so the numbers on screen are never a lie about the scene.

The offsets are remembered per weapon in an optionVar. A grip dialled in once
should not be retyped tomorrow, and a sword and a shield want different ones.
"""

import traceback

import maya.cmds as cmds

from maya_weapons import attach
from maya_weapons import catalog
from maya_weapons import skeleton

WINDOW = "mayaWeaponsWindow"
_MENU = "mayaWeaponsMenu"
_ROTATE = "mayaWeaponsRotate"
_TRANSLATE = "mayaWeaponsTranslate"
_STATUS = "mayaWeaponsStatus"
_BOUND = "mayaWeaponsBound"

_OPTIONVAR = "mayaWeapons_offset_{0}"

NO_CHARACTER = ("no character - open the picker and press Connect, "
                "or select a joint")
NOT_ATTACHED = "nothing attached yet - press Add"


# ------------------------------------------------------------------ policy

def optionvar_name(key):
    return _OPTIONVAR.format(key)


def pack_offsets(rotate, translate):
    return [float(value) for value in tuple(rotate) + tuple(translate)]


def unpack_offsets(values):
    """Six stored numbers -> (rotate, translate). Anything else -> zeros.

    Maya answers a missing optionVar with 0 or an empty list, and a stored
    value of the wrong length can only come from an older version of this
    tool; half a grip is worse than none.
    """
    zeros = ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
    try:
        numbers = [float(value) for value in values]
    except (TypeError, ValueError):
        return zeros
    if len(numbers) != 6:
        return zeros
    return tuple(numbers[:3]), tuple(numbers[3:])


def bound_message(root):
    return "no character bound" if not root else root.split("|")[-1]


def missing_bone_message(root, bone):
    return "{0} has no bone '{1}'".format(root.split("|")[-1], bone)


def missing_file_message(path):
    return "file not found: " + path


def added_message(entry, bone):
    return "{0} added to {1}".format(entry.label, bone.split("|")[-1])


# ------------------------------------------------------------------ state

def _entry():
    """The catalog entry the dropdown is showing."""
    return catalog.by_label(cmds.optionMenu(_MENU, query=True, value=True))


def _fields():
    rotate = cmds.floatFieldGrp(_ROTATE, query=True, value=True)[:3]
    translate = cmds.floatFieldGrp(_TRANSLATE, query=True, value=True)[:3]
    return tuple(rotate), tuple(translate)


def _set_fields(rotate, translate):
    cmds.floatFieldGrp(_ROTATE, edit=True, value1=rotate[0], value2=rotate[1],
                       value3=rotate[2])
    cmds.floatFieldGrp(_TRANSLATE, edit=True, value1=translate[0],
                       value2=translate[1], value3=translate[2])


def _remembered(entry):
    name = optionvar_name(entry.key)
    if not cmds.optionVar(exists=name):
        return unpack_offsets(None)
    return unpack_offsets(cmds.optionVar(query=name))


def _remember(entry, rotate, translate):
    name = optionvar_name(entry.key)
    cmds.optionVar(clearArray=name)
    for value in pack_offsets(rotate, translate):
        cmds.optionVar(floatValueAppend=(name, value))


def _status(message):
    cmds.text(_STATUS, edit=True, label=message)


def _carrier(entry):
    """The carrier for `entry`'s bone on the bound character, or None.

    Returns the bone as well, so callers can tell "no character" from
    "character has no such bone" from "bone is bare".
    """
    root = skeleton.current_root()
    cmds.text(_BOUND, edit=True, label=bound_message(root))
    if not root:
        return None, None, None
    bone = skeleton.resolve_bone(root, entry.bone)
    if not bone:
        return root, None, None
    return root, bone, attach.find_attached(bone)


# --------------------------------------------------------------- callbacks

def _run(action):
    """Run a callback, and put anything it throws on the status line."""
    try:
        action()
    except Exception:
        _status(traceback.format_exc().strip().splitlines()[-1])
        raise


def refresh():
    """Re-read the scene: which character, and what the fields should show."""
    entry = _entry()
    root, bone, carrier = _carrier(entry)

    if carrier:
        rotate, translate = attach.read_offsets(carrier)
        _set_fields(rotate, translate)
        _status("{0} on {1}".format(entry.label, bone.split("|")[-1]))
        return

    _set_fields(*_remembered(entry))
    if not root:
        _status(NO_CHARACTER)
    elif not bone:
        _status(missing_bone_message(root, entry.bone))
    else:
        _status(NOT_ATTACHED)


def add_weapon():
    """Put the chosen weapon into its bone, replacing what we put there before."""
    entry = _entry()
    root, bone, _ = _carrier(entry)
    if not root:
        _status(NO_CHARACTER)
        return
    if not bone:
        _status(missing_bone_message(root, entry.bone))
        return

    absent = catalog.missing(entry)
    if absent:
        _status(missing_file_message(absent))
        return

    rotate, translate = _fields()
    attach.attach(entry, bone, rotate, translate)
    _remember(entry, rotate, translate)
    _status(added_message(entry, bone))


def offsets_changed():
    """Live edit: write the fields into the attached weapon, and remember them."""
    entry = _entry()
    rotate, translate = _fields()
    _remember(entry, rotate, translate)

    _root, bone, carrier = _carrier(entry)
    if not carrier:
        _status(NOT_ATTACHED)
        return
    attach.write_offsets(carrier, rotate, translate)
    _status("{0} on {1}".format(entry.label, bone.split("|")[-1]))


# ------------------------------------------------------------------ window

def show_window():
    """Open the window, replacing one left from a previous call."""
    if cmds.window(WINDOW, exists=True):
        cmds.deleteUI(WINDOW)

    cmds.window(WINDOW, title="Weapons", widthHeight=(380, 190),
                sizeable=True)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=6,
                      columnOffset=("both", 8))

    cmds.text(_BOUND, label="", align="left")

    cmds.optionMenu(_MENU, label="Weapon",
                    changeCommand=lambda *_args: _run(refresh))
    for label in catalog.labels():
        cmds.menuItem(label=label)

    cmds.button(label="Add", height=30,
                command=lambda *_args: _run(add_weapon))

    cmds.floatFieldGrp(_ROTATE, numberOfFields=3, label="Rotate",
                       value1=0.0, value2=0.0, value3=0.0, precision=3,
                       changeCommand=lambda *_args: _run(offsets_changed))
    cmds.floatFieldGrp(_TRANSLATE, numberOfFields=3, label="Translate",
                       value1=0.0, value2=0.0, value3=0.0, precision=3,
                       changeCommand=lambda *_args: _run(offsets_changed))

    cmds.text(_STATUS, label="", align="left")

    cmds.setParent("..")
    cmds.showWindow(WINDOW)

    _run(refresh)
    return WINDOW
```

- [ ] **Step 4: Run the tests**

```bash
'/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe' -m unittest tests.test_weapons_window -v
```

Expected: 14 tests, all passing.

- [ ] **Step 5: Run the whole suite**

```bash
'/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe' -m unittest discover -s tests -t . -v
```

Expected: everything green.

- [ ] **Step 6: Commit**

```bash
git add maya_weapons/window.py tests/test_weapons_window.py
git commit -F <message file>
```

Message: `feat(weapons): the window, with live offsets remembered per weapon`

---

### Task 5: Live verification in the user's scene

**Files:**
- Create: `docs/superpowers/plans/verify_weapons.py`

**Interfaces:**
- Consumes: everything above.
- Produces: a script that prints `PASS`/`FAIL` per check and a final tally.

This is the real proof. Unit tests in this repo have repeatedly passed while
the scene was broken.

- [ ] **Step 1: Write the verification script**

Create `docs/superpowers/plans/verify_weapons.py`:

```python
"""Live proof for maya_weapons, run through the command port.

Bind explicitly rather than trusting whatever the panel last did: the user
works in the scene between runs. The script leaves the scene as it found it --
if no weapon was attached when it started, none is attached when it ends.

Never cmds.undo() from a bridge script: the whole script is one command, and
undo reverts a chunk of prior work instead.
"""

import maya.cmds as cmds

from maya_weapons import attach
from maya_weapons import catalog
from maya_weapons import skeleton

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))
    print("{0} {1}{2}".format("PASS" if ok else "FAIL", name,
                              "  " + detail if detail else ""))


def world_matrix(node):
    return cmds.xform(node, query=True, matrix=True, worldSpace=True)


def local_matrix(node):
    return cmds.xform(node, query=True, matrix=True, objectSpace=True)


def biggest_difference(left, right):
    return max(abs(a - b) for a, b in zip(left, right))


entry = catalog.by_key("LongSword_02")

# --- the file and the character ------------------------------------------
check("model file is on disk", catalog.missing(entry) == "", entry.path)

root = skeleton.current_root()
check("a character was resolved", root is not None, str(root))

bone = skeleton.resolve_bone(root, entry.bone)
check("weapon_r resolved inside that character", bone is not None, str(bone))
check("the bone belongs to the bound character",
      bone and bone.startswith(root.rsplit("|", 1)[0]), str(bone))

was_attached = attach.find_attached(bone) is not None

# --- attach with no offsets ----------------------------------------------
carrier = attach.attach(entry, bone)
check("carrier is a child of the bone",
      carrier.startswith(bone + "|"), carrier)
check("carrier is marked",
      cmds.attributeQuery(attach.MARKER, node=carrier, exists=True))
check("marker holds the catalog key",
      cmds.getAttr(carrier + "." + attach.MARKER) == entry.key)
check("the model came in with it",
      bool(cmds.listRelatives(carrier, allDescendents=True, type="mesh")))

gap = biggest_difference(world_matrix(carrier), world_matrix(bone))
check("with zero offsets it sits exactly on the bone", gap < 1e-4,
      "worst matrix element {0:.7f}".format(gap))

# --- offsets --------------------------------------------------------------
attach.write_offsets(carrier, (0.0, 90.0, 0.0), (5.0, 0.0, 0.0))
rotate, translate = attach.read_offsets(carrier)
check("offsets read back as written",
      max(abs(rotate[1] - 90.0), abs(translate[0] - 5.0)) < 1e-4,
      "{0} {1}".format(rotate, translate))

moved = biggest_difference(world_matrix(carrier), world_matrix(bone))
check("a non-zero offset actually moves it", moved > 1.0,
      "worst matrix element {0:.4f}".format(moved))

# --- one weapon per bone --------------------------------------------------
attach.attach(entry, bone)
marked = [child for child
          in cmds.listRelatives(bone, children=True, type="transform",
                                fullPath=True) or []
          if cmds.attributeQuery(attach.MARKER, node=child, exists=True)]
check("a second Add leaves exactly one weapon", len(marked) == 1,
      "{0} marked children".format(len(marked)))

carrier = marked[0]
attach.write_offsets(carrier, (0.0, 30.0, 0.0), (2.0, 1.0, 0.0))

# --- it rides the arm -----------------------------------------------------
start = int(cmds.playbackOptions(query=True, minTime=True))
end = int(cmds.playbackOptions(query=True, maxTime=True))
restore = cmds.currentTime(query=True)

frames = sorted(set([start, (start + end) // 2, end]))
locals_over_time = []
bone_over_time = []
for frame in frames:
    cmds.currentTime(frame)
    locals_over_time.append(local_matrix(carrier))
    bone_over_time.append(world_matrix(bone))
cmds.currentTime(restore)

drift = max(biggest_difference(locals_over_time[0], sample)
            for sample in locals_over_time)
check("the weapon holds its offset over the range", drift < 1e-6,
      "worst {0:.9f} over frames {1}".format(drift, frames))

travel = max(biggest_difference(bone_over_time[0], sample)
             for sample in bone_over_time)
if travel < 1e-4:
    print("NOTE  the arm does not move over {0}-{1}; "
          "the carry check is vacuous".format(start, end))
else:
    check("the arm moved, so the carry is real", True,
          "bone travelled {0:.3f}".format(travel))

# --- leave the scene as we found it ---------------------------------------
if not was_attached:
    attach.remove_attached(bone)
    check("cleaned up after itself", attach.find_attached(bone) is None)

passed = sum(1 for _name, ok, _detail in RESULTS if ok)
print("\n{0}/{1} checks passed".format(passed, len(RESULTS)))
```

- [ ] **Step 2: Send it to the live Maya**

Write a runner and a sender into the scratchpad, per `CLAUDE.md`:
`exec(compile(src, path, "exec"), {"__name__": "__main__"})` inside a runner
that captures stdout/stderr into an output file, sent as a one-liner to
`127.0.0.1:7001`, and poll for the output file rather than trusting the socket
reply. Check the port is listening first:

```bash
powershell -c "Get-NetTCPConnection -State Listen -LocalPort 7001"
```

- [ ] **Step 3: Read the output and fix what it reports**

Every check must pass. A failure here outranks any green unit test — fix the
code, not the check, unless the check is measuring the wrong thing.

- [ ] **Step 4: Open the window in the live Maya and use it**

```python
import sys; sys.path.append(r"C:/!!!Work/MayaScripts")
import maya_weapons; maya_weapons.show_window()
```

Confirm by screenshot (`widget.grab().save(path)` is for Qt; this is a `cmds`
window, so ask the user to look, or capture the Maya main window): the
dropdown lists the sword, Add puts it in the right hand, and typing into
Rotate/Translate moves it immediately.

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/plans/verify_weapons.py
git commit -F <message file>
```

Message: `test(weapons): live proof that the sword lands in the hand and stays`

---

### Task 6: Document it

**Files:**
- Modify: `CLAUDE.md` (a new section after the `maya_uebridge` one)

- [ ] **Step 1: Write the section**

Add to `CLAUDE.md`, in the voice of the surrounding sections — what it is, the
entry point, the module table, and the load-bearing decisions:

- entry point (`import maya_weapons; maya_weapons.show_window()`);
- the module table and the stdlib-only rule for `catalog.py`;
- the skeleton comes from the picker's live binding through the new
  `picker_window.bound_root()`, with the selection and single-skeleton
  fallbacks, and refuses to guess between two candidates;
- the bone is resolved inside the bound subtree, never scene-wide;
- the carrier is found by its `mayaWeapon` attribute, never by name;
- **`cmds.file` here, `FBXImport` in the bridge** — say why, or the next
  reader will "fix" it into a bug;
- offsets are the carrier's local rotate/translate, live, autoKey off around
  the write, remembered per weapon in an optionVar;
- one weapon per bone, replaced on every Add;
- shading nodes survive a delete, and that is deliberate;
- the live proof and its score.

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -F <message file>
```

Message: `docs: record the weapon attach module`

---

## Self-review

**Spec coverage.** Picker binding with fallbacks → Task 2. Bone inside the
subtree → Task 2. Add's six steps, `cmds.file` reasoning, the marker → Task 3.
Live offsets, read-back, autoKey guard, per-weapon optionVars, no scale field
→ Tasks 3 and 4. Module layout, lazy `__getattr__`, `_run` → Tasks 1 and 4.
Every failure-mode message in the spec's table has a test in Task 4 and a
branch in `add_weapon`/`refresh`. Shading-node and namespace notes are
documentation, covered in Task 6. Testing section → Tasks 1-5.

**Placeholders.** None: every step carries the code it asks for. Task 5 step 2
describes the bridge runner rather than reprinting it, which `CLAUDE.md`
explicitly says to rebuild in the scratchpad each time; Task 6 is prose whose
content is enumerated.

**Type consistency.** `Weapon(key, label, path, bone, scale)` is used with
those field names everywhere. `attach.attach(entry, bone, rotate, translate)`
returns the carrier path, which is what `read_offsets`/`write_offsets` take.
`choose_root` takes three arguments in Tasks 2's test and its implementation.
`unpack_offsets` returns `(tuple, tuple)`, matching `_set_fields(rotate,
translate)`.
