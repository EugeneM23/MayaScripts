# Scene Tabs, Stage 2 - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** While two or more scene tabs are open, every plugin tool sees and changes only the active tab: its questions about the scene ask the active tab, what it creates lands in the active tab (and hides, saves and closes with it), and what it names it names as the tab shows it.

**Architecture:** One new module, `SkeldarAnim/maya_scenetabs/scope.py` (stdlib + the caller's `cmds`, imports nothing of the plugin but `records`), holds the three rules: a reader keeps only the active tab's paths (`active_only`), the current namespace is the active tab's (`enter_active`, `at_root`, `home_namespace`), and a name that carries a namespace is made absolute when a node is created or renamed with it (`as_created`, `root_name`). Then ~117 small, exact edits across the plugin, grouped by rule. With tabs off (no session, or one tab) the active namespace is `""` and every function is the identity, so the plugin behaves exactly as before.

**Tech Stack:** Maya 2027 `maya.cmds`, stdlib `unittest` under `mayapy`.

**Spec:** `docs/superpowers/specs/2026-10-15-scene-tabs-plugin-scope-design.md` (Task 1 adds the addendum of what was measured while planning). **Prerequisite: stage 1 is built** - `docs/superpowers/plans/2026-10-15-scene-tabs-stage1.md`, all ten tasks: this plan edits its `maya_scenetabs/saving.py` and its `verify_scene_tabs.py`, and the proof uses that verify's fixtures. **Stage 1 must not ship alone**: with a tab active the current namespace is the tab's, and the plugin's own creations then double the tab's prefix (measured: Retarget fails with «setAttr: No object matches name: tab_plain:Manny_Rig:MoCapConstraints.tx») - see Task 1's measurement.

## Global Constraints

- `scope.py` imports only the stdlib and `records` at module level (`saving`, `opening`, `maya_scenesetup.fbximport` lazily inside the functions that need them); every function that reads the scene takes the caller's `cmds` as `cmds_` and never raises from `active_namespace` (a fake or a Maya without the session answers `""`).
- Every edit below was applied to a copy of the plugin at `e2db31a` (equal to `71b0456` in every edited file) with stage 1 built from its plan, in the order this plan gives, each `old` text found exactly where the step says (once, or every occurrence where the step says EVERY). If an `old` text is not found, the file changed since: stop and re-read the rule the task states, never force a near match.
- With tabs off nothing changes: the unit suite must show no new failure after every task.
- Run the tests from the repo root: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest <module> -v` (PowerShell; no `2>&1` on mayapy). The whole suite needs `$env:QT_QPA_PLATFORM = 'offscreen'`.
- Run the verifies in the scratch prefs folder `$env:MAYA_APP_DIR = "$env:TEMP\skeldar_tabs_appdir"`, in mayapy standalone. Never through the animator's port 7001; a GUI check is the animator's.
- Commits stage only this plan's files (`git add <paths>`): other sessions work in the same checkout. Messages go through a file (`git commit -F`), ending with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Do not push, build or install into the animator's Maya.

## File Structure

| File | Responsibility |
|---|---|
| `SkeldarAnim/maya_scenetabs/scope.py` | create: the active tab's namespace, the reader filter, the current namespace, names made absolute or shown as the tab shows them, the scene's name, a copy of the scene, the plugin's own open / new |
| `tests/test_scenetabs_scope.py` | create: `scope` against a fake `cmds` |
| `docs/superpowers/plans/verify_tabs_scope.py` | create: the proof, mayapy standalone, a decoy tab beside the active one |
| `docs/superpowers/specs/2026-10-15-scene-tabs-plugin-scope-design.md` | modify: the planning addendum |
| `maya_rigs.py`, `maya_overrig/naming.py`, `maya_overrig/active.py`, `maya_uebridge/animimport.py`, `maya_scenesetup/weaponspace.py`, `maya_scenesetup/colour.py`, `maya_asretarget.py`, `maya_pmretarget.py`, `maya_vpstudio.py`, `maya_com/network.py` | Task 2: the readers |
| `maya_scenesetup/chargroup.py`, `maya_asretarget.py`, `maya_pmretarget.py`, `maya_retargetmode.py`, `maya_com/network.py`, `maya_poselib/apply.py`, `maya_scenesetup/camera.py`, `maya_scenesetup/cliplabel.py`, `maya_uebridge/rigimport.py`, `maya_uebridge/skeletonimport.py`, `maya_uebridge/animimport.py`, `maya_uebridge/fbxlayout.py`, `tests/test_uebridge_rigimport.py` | Task 3: names a node is created or renamed with |
| `maya_uebridge/animimport.py`, `maya_uebridge/formats.py`, `maya_uebridge/nativeimport.py`, `maya_scenesetup/deletion.py`, `maya_share.py`, `maya_stash.py`, `maya_scenesetup/character.py`, `maya_scenesetup/armor.py`, `maya_poselib/apply.py` | Task 4: the current namespace and what is kept |
| `maya_share.py`, `maya_stash.py`, `maya_poselib/capture.py`, `maya_scenesetup/cliplabel.py`, `maya_walk/scene.py`, `maya_scenesetup/opener.py`, `maya_scenetabs/saving.py` | Task 5: the scene's name, a copy, the plugin's own open / new |
| `maya_scenesetup/character.py`, `maya_scenesetup/equip.py`, `maya_scenesetup/armor.py`, `maya_scenesetup/cliplabel.py` | Task 6: names as the tab shows them |
| `docs/superpowers/plans/verify_scene_tabs.py` | Task 2: one stage 1 gate becomes stage 2's |
| `CLAUDE.md` | Task 7: the section's stage 2 part, traps |

Every path in the table above is under `SkeldarAnim/` unless it starts with `tests/`, `docs/` or is `CLAUDE.md`. The package `maya_scenetabs` is already a payload row (stage 1, Task 1), so `scope.py` ships with it.

## How the readers, namespaces and names were found

- **Readers**: every scene-wide listing in the plugin (`cmds.ls(type="joint")`, `ls(assemblies=True)`, `ls(type="objectSet")`, `ls(materials=True)`, `ls(type="transform")`, the marker scans) was read; those that answer "which character / rig / skeleton / colour / studio" get `scope.active_only`. Those left scene-wide on purpose: before/after diffs of an import (`formats`, `skeletonimport`: they find what an import made), lookups already narrowed to one namespace (`maya_rigs`' skeleton walk by the rig's namespace, `nativeimport`, `deletion`'s namespace tops), and the OverRig picker's `fkrings` walk (the picker is off, `skeldar_features.PICKER`). Everything built on `maya_rigs.rigs()`, `builder.character_roots()` and `animimport.skeleton_roots()` - `skeletonimport.bare_roots`, `droptarget`'s snapshots, `skeleton.current_root`, Connections, FK/IK, the Pose Library, Walk Builder, the Tools - follows from those three.
- **Creation names**: an AST scan of every `cmds.<creator>(name=...)` and `cmds.rename(node, name)` whose name is not a plain string literal (86 sites). A name built from a leaf (`plan.leaf`, `space_name`, `split(":")[-1]`) needs nothing - it lands in the current namespace, the tab's. A name that carries a namespace (a rig's, a clip's) gets `scope.as_created`; a name given back after a hold gets `scope.root_name`.
- **Measured** (mayapy, 2026-10-15): with `tabx` current, `createNode(name="tabx:Rig:a")` made `tabx:tabx:Rig:a` and Maya created the missing namespaces itself; `createNode(name=":A:x")` made `A:x` and answered `"A:x"` - no leading colon, so a fake `cmds` must answer that way too; `cmds.ls`, `objExists` look up from the root; `namespace(addNamespace="x")` adds under the current namespace, `addNamespace=":x"` at the root.

---

### Task 1: `scope`, its tests, the proof and the spec addendum

**Files:**
- Create: `SkeldarAnim/maya_scenetabs/scope.py`
- Create: `tests/test_scenetabs_scope.py`
- Create: `docs/superpowers/plans/verify_tabs_scope.py`
- Modify: `docs/superpowers/specs/2026-10-15-scene-tabs-plugin-scope-design.md` (append)

**Interfaces:**
- Consumes (stage 1): `maya_scenetabs.records` - `SESSION_NODE`, `SESSION_ATTR`, `loads(text)`, `tab(state, ns)`, `empty_state()`, `new_tab(ns, path, unit, ranges)`, `with_tab(state, item)`, `dumps(state)`; `maya_scenetabs.saving.save_tab(namespace=None, path=None, adopt=True)` (Task 5 adds `preserve_references`); `maya_scenetabs.opening.open_tab(path)`, `opening.new_tab()`; the verify uses `switching.switch(ns)`, `session.state()` and stage 1's fixtures in `%TEMP%/skeldar_tabs_verify` (`rig.ma`, `plain.mb`, `film.ma`, made by `verify_scene_tabs.py`).
- Produces: `scope.active_namespace(cmds_=None) -> str`, `own_namespace(path) -> str`, `within(namespace, active) -> bool`, `in_active(path, cmds_=None, active=None) -> bool`, `active_only(paths, cmds_=None) -> list`, `qualified(name, cmds_=None) -> str`, `absolute(name, cmds_=None) -> str`, `relative(name, cmds_=None) -> str`, `local(path, cmds_=None) -> str`, `enter_active(cmds_=None)`, `at_root(cmds_=None)` (context manager), `home_namespace(namespace, cmds_=None) -> str`, `as_created(name) -> str`, `root_name(name) -> str`, `tabs_on(cmds_=None) -> bool`, `scene_name(cmds_=None) -> str`, `export_scene(path, file_type, cmds_=None) -> str`, `open_scene(path, cmds_=None, **flags) -> str`, `new_scene(cmds_=None) -> str`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_scenetabs_scope.py`:

```python
"""maya_scenetabs.scope: the plugin sees only the active tab (2026-10-15).

Spec: docs/superpowers/specs/2026-10-15-scene-tabs-plugin-scope-design.md
"""
import unittest

from maya_scenetabs import records, scope


def _state(*namespaces, active=None):
    state = records.empty_state()
    for ns in namespaces:
        state = records.with_tab(state, records.new_tab(ns, "C:/w/%s.ma" % ns[4:], "ntsc", {}))
    state["active"] = active or (namespaces[0] if namespaces else "")
    return state


class FakeCmds(object):
    """The session node, the namespaces and what was asked of them."""

    def __init__(self, state=None, namespaces=(), scene=""):
        self.text = records.dumps(state) if state is not None else None
        self.namespaces = set(namespaces)
        self.current = ":"
        self.scene = scene
        self.calls = []

    def objExists(self, name):
        return name == records.SESSION_NODE and self.text is not None

    def getAttr(self, plug):
        return self.text

    def file(self, *args, **kwargs):
        if kwargs.get("query") and kwargs.get("sceneName"):
            return self.scene
        self.calls.append(("file", args, kwargs))

    def namespace(self, exists=None, setNamespace=None, rename=None, parent=None):
        if exists is not None:
            return exists.lstrip(":") in self.namespaces
        if setNamespace is not None:
            self.current = setNamespace
            return None
        old, new = rename
        old = old.lstrip(":")
        self.namespaces.discard(old)
        whole = (parent.lstrip(":") + ":" + new) if parent else new
        self.namespaces.add(whole)
        self.calls.append(("rename", old, whole))

    def namespaceInfo(self, under, listOnlyNamespaces=False):
        prefix = under.lstrip(":") + ":"
        return [":" + n for n in self.namespaces if n.startswith(prefix) and ":" not in n[len(prefix):]]


class ActiveNamespace(unittest.TestCase):

    def test_no_session_is_no_tabs(self):
        self.assertEqual(scope.active_namespace(FakeCmds()), "")

    def test_one_tab_is_no_tabs(self):
        self.assertEqual(scope.active_namespace(FakeCmds(_state("tab_a"))), "")

    def test_two_tabs_answer_the_active_one(self):
        self.assertEqual(scope.active_namespace(FakeCmds(_state("tab_a", "tab_b", active="tab_b"))), "tab_b")

    def test_a_fake_that_raises_answers_no_tabs(self):
        class Broken(object):
            def objExists(self, name):
                raise RuntimeError("no Maya")
        self.assertEqual(scope.active_namespace(Broken()), "")


class Membership(unittest.TestCase):

    def test_a_paths_own_namespace(self):
        self.assertEqual(scope.own_namespace("|tab_a:Group|tab_a:Rig:Main"), "tab_a:Rig")
        self.assertEqual(scope.own_namespace("|root|pelvis"), "")

    def test_a_tab_does_not_hold_a_tab_whose_name_starts_like_it(self):
        self.assertTrue(scope.within("tab_a", "tab_a"))
        self.assertTrue(scope.within("tab_a:Rig", "tab_a"))
        self.assertFalse(scope.within("tab_ab", "tab_a"))
        self.assertFalse(scope.within("", "tab_a"))

    def test_everything_is_within_when_tabs_are_off(self):
        self.assertTrue(scope.within("tab_b:Rig", ""))

    def test_active_only_keeps_the_active_tabs_paths(self):
        cmds = FakeCmds(_state("tab_a", "tab_b", active="tab_a"))
        paths = ["|tab_a:root", "|tab_b:root", "|tab_a:G|tab_a:Rig:root", "|root"]
        self.assertEqual(scope.active_only(paths, cmds), ["|tab_a:root", "|tab_a:G|tab_a:Rig:root"])

    def test_active_only_keeps_everything_with_tabs_off(self):
        self.assertEqual(scope.active_only(["|tab_b:root", "|root"], FakeCmds()), ["|tab_b:root", "|root"])


class Names(unittest.TestCase):

    def setUp(self):
        self.on = FakeCmds(_state("tab_a", "tab_b"))
        self.off = FakeCmds()

    def test_qualified_absolute_relative(self):
        self.assertEqual(scope.qualified("Manny_Rig", self.on), "tab_a:Manny_Rig")
        self.assertEqual(scope.absolute("Manny_Rig", self.on), ":tab_a:Manny_Rig")
        self.assertEqual(scope.relative("tab_a:Manny_Rig", self.on), "Manny_Rig")
        self.assertEqual(scope.relative("tab_b:Manny_Rig", self.on), "tab_b:Manny_Rig")
        self.assertEqual(scope.qualified("Manny_Rig", self.off), "Manny_Rig")
        self.assertEqual(scope.absolute("Manny_Rig", self.off), ":Manny_Rig")

    def test_a_created_name_with_a_namespace_is_absolute(self):
        # Maya resolves a creation name relative to the CURRENT namespace (measured)
        self.assertEqual(scope.as_created("tab_a:Manny_Rig:MoCapConstraints"),
                         ":tab_a:Manny_Rig:MoCapConstraints")
        self.assertEqual(scope.as_created(":A:x"), ":A:x")

    def test_a_created_leaf_stays_relative(self):
        self.assertEqual(scope.as_created("hand_r_weaponSpace"), "hand_r_weaponSpace")
        self.assertEqual(scope.as_created(""), "")

    def test_a_name_given_back_is_from_the_root(self):
        self.assertEqual(scope.root_name("tab_a:root"), ":tab_a:root")
        self.assertEqual(scope.root_name(":root"), ":root")
        self.assertEqual(scope.root_name("root"), ":root")

    def test_local_takes_the_tab_off_every_node_of_a_path(self):
        self.assertEqual(scope.local("|tab_a:G|tab_a:Rig:root", self.on), "|G|Rig:root")
        self.assertEqual(scope.local("|tab_b:G|tab_b:root", self.on), "|tab_b:G|tab_b:root")
        self.assertEqual(scope.local("|tab_a:G|tab_a:Rig:root", self.off), "|tab_a:G|tab_a:Rig:root")


class CurrentNamespace(unittest.TestCase):

    def test_enter_active_sets_the_tabs_namespace(self):
        cmds = FakeCmds(_state("tab_a", "tab_b", active="tab_b"))
        scope.enter_active(cmds)
        self.assertEqual(cmds.current, ":tab_b")

    def test_enter_active_with_tabs_off_is_the_root(self):
        cmds = FakeCmds()
        cmds.current = ":clip"
        scope.enter_active(cmds)
        self.assertEqual(cmds.current, ":")

    def test_at_root_comes_back_to_the_tab_even_on_an_error(self):
        cmds = FakeCmds(_state("tab_a", "tab_b"))
        with self.assertRaises(ValueError):
            with scope.at_root(cmds):
                self.assertEqual(cmds.current, ":")
                raise ValueError("boom")
        self.assertEqual(cmds.current, ":tab_a")


class HomeNamespace(unittest.TestCase):

    def test_a_kept_clip_moves_under_the_tab(self):
        cmds = FakeCmds(_state("tab_a", "tab_b"), namespaces=("tab_a", "tab_b", "Walk"))
        self.assertEqual(scope.home_namespace("Walk", cmds), "tab_a:Walk")
        self.assertIn("tab_a:Walk", cmds.namespaces)

    def test_a_taken_name_in_the_tab_gets_a_number(self):
        cmds = FakeCmds(_state("tab_a", "tab_b"), namespaces=("tab_a", "tab_b", "tab_a:Walk", "Walk"))
        self.assertEqual(scope.home_namespace("Walk", cmds), "tab_a:Walk1")

    def test_with_tabs_off_nothing_moves(self):
        cmds = FakeCmds(namespaces=("Walk",))
        self.assertEqual(scope.home_namespace("Walk", cmds), "Walk")
        self.assertEqual(cmds.calls, [])


class SceneName(unittest.TestCase):

    def test_tabs_off_is_the_scenes_own(self):
        self.assertEqual(scope.scene_name(FakeCmds(scene="C:/w/shot.ma")), "C:/w/shot.ma")

    def test_tabs_on_is_the_active_tabs_file(self):
        cmds = FakeCmds(_state("tab_shot", "tab_rig", active="tab_rig"), scene="C:/w/untitled")
        self.assertEqual(scope.scene_name(cmds), "C:/w/rig.ma")


class OpenNew(unittest.TestCase):

    def test_tabs_off_opens_and_news_as_maya_does(self):
        cmds = FakeCmds()
        self.assertEqual(scope.open_scene("C:/w/a.ma", cmds, force=True), "")
        self.assertEqual(scope.new_scene(cmds), "")
        self.assertEqual(cmds.calls, [("file", ("C:/w/a.ma",), {"open": True, "force": True}),
                                      ("file", (), {"new": True, "force": True})])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run them to see them fail**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_scenetabs_scope -v`
Expected: ERROR - `ImportError: cannot import name 'scope' from 'maya_scenetabs'`.

- [ ] **Step 3: Write `scope.py`**

Create `SkeldarAnim/maya_scenetabs/scope.py`:

```python
"""Scene tabs, stage 2: the plugin sees only the active tab.

Spec: docs/superpowers/specs/2026-10-15-scene-tabs-plugin-scope-design.md (and
its addendum). With tabs off (no session, or one tab) the active namespace is
"" and every function here is the identity, so the plugin behaves exactly as
before. Every function that reads the scene takes the caller's `cmds` (`cmds_`):
the plugin's unit tests replace a module's `cmds` with a fake, and the fake
then answers here too.

Three rules, each with its helpers:
- **A scene reader sees the active tab only** (`active_only`, `in_active`).
- **The current namespace is the active tab's** while tabs are on: whatever
  creates nodes by relative name puts them in the tab, so they hide, save and
  close with it. A reset to the root becomes `enter_active`; work that must
  happen at the root (a clip imported for the length of a retarget) runs in
  `at_root`, which comes back to the tab.
- **What stays lands in the tab**: a root-level namespace kept after an import
  moves under the tab (`home_namespace`), a name made absolute is the tab's
  (`absolute`), and the plugin's own open / new of a scene opens a tab
  (`open_scene`, `new_scene`) - Maya's own are redirected by the hooks, but
  deferred, while the plugin's code runs on as if the scene were there.
"""

import contextlib

from . import records


def _cmds(cmds_):
    if cmds_ is not None:
        return cmds_
    import maya.cmds as cmds
    return cmds


def active_namespace(cmds_=None):
    """The active tab's namespace, or "" with tabs off. Never raises: a fake
    or a Maya without the session answers ""."""
    try:
        cmds = _cmds(cmds_)
        if not cmds.objExists(records.SESSION_NODE):
            return ""
        state = records.loads(cmds.getAttr(records.SESSION_NODE + "." + records.SESSION_ATTR) or "")
    except Exception:                                            # noqa: BLE001
        return ""
    return state["active"] if len(state["tabs"]) >= 2 else ""


def own_namespace(path):
    """The namespace of a path's own node ("" = the root). Pure."""
    short = (path or "").split("|")[-1]
    return short.rsplit(":", 1)[0] if ":" in short else ""


def within(namespace, active):
    """`namespace` is the active tab's or nested in it; everything is, with
    tabs off. Pure. `tab_a` is not within `tab`."""
    if not active:
        return True
    return namespace == active or namespace.startswith(active + ":")


def in_active(path, cmds_=None, active=None):
    active = active_namespace(cmds_) if active is None else active
    return within(own_namespace(path), active)


def active_only(paths, cmds_=None):
    """`paths` that belong to the active tab (all of them with tabs off)."""
    active = active_namespace(cmds_)
    if not active:
        return list(paths or [])
    return [p for p in paths or [] if within(own_namespace(p), active)]


def qualified(name, cmds_=None):
    """`name` placed in the active tab (`tab_x:name`), or `name` with tabs off."""
    active = active_namespace(cmds_)
    return "%s:%s" % (active, name) if active else name


def absolute(name, cmds_=None):
    return ":" + qualified(name, cmds_)


def relative(name, cmds_=None):
    """A full name with the active tab's prefix taken off; anything else as it is."""
    active = active_namespace(cmds_)
    prefix = active + ":" if active else ""
    return name[len(prefix):] if prefix and name.startswith(prefix) else name


def local(path, cmds_=None):
    """A path as the active tab shows it: the tab's prefix taken off every
    node in it (`|tab_x:A|tab_x:Rig:root` -> `|A|Rig:root`). What a message or
    a label names - "the outermost namespace" is the tab's otherwise. As it is
    with tabs off."""
    active = active_namespace(cmds_)
    if not active:
        return path
    prefix = active + ":"
    return "|".join(p[len(prefix):] if p.startswith(prefix) else p for p in (path or "").split("|"))


def enter_active(cmds_=None):
    """The current namespace back to the active tab's (the root with tabs off)."""
    cmds = _cmds(cmds_)
    active = active_namespace(cmds)
    cmds.namespace(setNamespace=(":" + active) if active else ":")


@contextlib.contextmanager
def at_root(cmds_=None):
    """The root namespace current for the length of the block, the active
    tab's again after it."""
    cmds = _cmds(cmds_)
    cmds.namespace(setNamespace=":")
    try:
        yield
    finally:
        enter_active(cmds)


def home_namespace(namespace, cmds_=None):
    """A root-level namespace (a clip kept after its import) moved under the
    active tab. Returns its full name; with tabs off, or when it is not at the
    root, the name as it was."""
    cmds = _cmds(cmds_)
    active = active_namespace(cmds)
    leaf = namespace.lstrip(":")
    if not active or ":" in leaf or not cmds.namespace(exists=":" + leaf):
        return leaf
    target = leaf
    taken = set(n.split(":")[-1] for n in cmds.namespaceInfo(":" + active, listOnlyNamespaces=True) or [])
    number = 1
    while target in taken:
        target = "%s%d" % (leaf, number)
        number += 1
    if target != leaf:
        cmds.namespace(rename=(":" + leaf, target))
    cmds.namespace(rename=(":" + target, target), parent=":" + active)
    return "%s:%s" % (active, target)


def as_created(name):
    """A name for a node about to be CREATED or renamed: absolute when it
    carries a namespace. Maya resolves a creation name relative to the CURRENT
    namespace (measured: with `tabx` current, `tabx:Rig:a` became
    `tabx:tabx:Rig:a`, Maya making the missing namespaces itself), while a
    lookup goes from the root. A leaf stays relative and lands in the current
    namespace - the active tab's. Pure."""
    if not name or name.startswith(":") or ":" not in name:
        return name
    return ":" + name


def root_name(name):
    """A name given BACK to a node (a hold undone): its full name from the
    root, absolute, whatever namespace is current. Pure."""
    return ":" + (name or "").lstrip(":")


def tabs_on(cmds_=None):
    return bool(active_namespace(cmds_))


def scene_name(cmds_=None):
    """The file the animator is working in: the active tab's while tabs are
    on (the scene itself is the session then), else the scene's own name."""
    cmds = _cmds(cmds_)
    active = active_namespace(cmds)
    if not active:
        return cmds.file(query=True, sceneName=True) or ""
    try:
        state = records.loads(cmds.getAttr(records.SESSION_NODE + "." + records.SESSION_ATTR) or "")
    except Exception:                                            # noqa: BLE001
        return ""
    return (records.tab(state, active) or {}).get("path") or ""


def export_scene(path, file_type, cmds_=None):
    """A copy of the scene the animator is working in, references written in
    (a colleague has none of the files they point at): the active tab alone
    while tabs are on, else the whole scene. The working file, its name and its
    modified flag stay as they are."""
    cmds = _cmds(cmds_)
    if not tabs_on(cmds):
        cmds.file(path, exportAll=True, type=file_type, force=True, preserveReferences=False)
        return path
    from . import saving
    saving.save_tab(path=path, adopt=False, preserve_references=False)
    return path


def open_scene(path, cmds_=None, **flags):
    """The plugin's own open of a scene: a new tab while tabs are on (a .ma /
    .mb opened, an FBX imported into an empty tab), else Maya's open with
    `flags`. Returns the tab's message, or "" for Maya's own open."""
    cmds = _cmds(cmds_)
    if not tabs_on(cmds):
        cmds.file(path, open=True, **flags)
        return ""
    from . import opening
    if path.lower().endswith(".fbx"):
        message = opening.new_tab()
        from maya_scenesetup import fbximport
        fbximport.import_nodes(path)
        return message
    return opening.open_tab(path)


def new_scene(cmds_=None):
    """The plugin's own new scene: an empty tab while tabs are on, else Maya's new."""
    cmds = _cmds(cmds_)
    if not tabs_on(cmds):
        cmds.file(new=True, force=True)
        return ""
    from . import opening
    return opening.new_tab()
```

- [ ] **Step 4: Run the tests**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_scenetabs_scope -v`
Expected: `Ran 23 tests ... OK`.

- [ ] **Step 5: Write the proof**

Create `docs/superpowers/plans/verify_tabs_scope.py`:

```python
"""Scene tabs, stage 2: the plugin sees only the active tab - the proof in
mayapy standalone (2026-10-15).

A DECOY tab holds a Manny rig (keyed), a bare Manny UE5 skeleton and a bare
UE4 Mannequin (plain `root`s, the mannequin red from the palette); the work
happens in another tab: the plugin's scene questions, Add Character, a
retarget, an export with nothing selected, a weapon, Delete, a clip's
namespace, a save, Shared's copy. Every section is gated on its own (a
section that raises fails its "ran" gate and the next one still runs), and
the decoy is checked untouched; last, a weapon's file is opened by Open
scene (a tab of its own).

Run from the repo root (PowerShell), after verify_scene_tabs.py has built its
fixtures once:
  $env:MAYA_APP_DIR = "$env:TEMP\\skeldar_tabs_appdir"
  & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' docs/superpowers/plans/verify_tabs_scope.py
Spec: docs/superpowers/specs/2026-10-15-scene-tabs-plugin-scope-design.md
"""
import os
import shutil
import sys
import tempfile
import traceback

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds  # noqa: E402
import maya.mel as mel  # noqa: E402

for _plug in ("matrixNodes", "quatNodes", "fbxmaya"):
    try:
        cmds.loadPlugin(_plug, quiet=True)
    except RuntimeError:
        pass

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(REPO, "SkeldarAnim").replace("\\", "/"))

from maya_scenetabs import opening, records, saving, scope, session, switching  # noqa: E402

WORK = os.path.join(tempfile.gettempdir(), "skeldar_tabs_verify").replace("\\", "/")
RUN = WORK + "/scope_run"
RESULTS = []
DECOY = "tab_rig"
ACTIVE = "tab_plain"


def gate(name, ok, detail=""):
    RESULTS.append(bool(ok))
    print("%s  %s  %s" % ("PASS" if ok else "FAIL", name, detail))


def section(name, run, ctx):
    try:
        run(ctx)
    except Exception:                                            # noqa: BLE001
        gate("%s: ran to the end" % name, False, traceback.format_exc()[-600:])
    finally:
        try:
            scope.enter_active(cmds)                             # whatever a failure left current
        except Exception:                                        # noqa: BLE001
            pass


def copy(name, as_name=None):
    os.makedirs(RUN, exist_ok=True)
    target = RUN + "/" + (as_name or name)
    shutil.copyfile(WORK + "/" + name, target)
    return target


def decoy_snapshot():
    """The decoy's nodes and what they hold: names, the rig's keys, the bare skeletons' joints'
    world matrices, its materials' colours."""
    nodes = sorted(cmds.namespaceInfo(":" + DECOY, listOnlyDependencyNodes=True, recurse=True) or [])
    keys = cmds.keyframe(DECOY + ":Manny_Rig:FKShoulder_R.rotateZ", q=True, timeChange=True,
                         valueChange=True)
    joints = sorted(j for root in cmds.ls(DECOY + ":root", long=True) or []
                    for j in [root] + (cmds.listRelatives(root, allDescendents=True, type="joint",
                                                          fullPath=True) or []))
    worlds = [[round(v, 6) for v in cmds.xform(j, q=True, matrix=True, worldSpace=True)] for j in joints]
    colours = sorted((m, tuple(round(c, 4) for c in cmds.getAttr(m + ".color")[0]))
                     for m in cmds.ls(DECOY + ":*", materials=True, recursive=True) or []
                     if cmds.attributeQuery("color", node=m, exists=True))
    return {"nodes": nodes, "keys": keys, "worlds": worlds, "colours": colours}


def questions(ctx):
    import maya_rigs
    from maya_overrig import builder
    from maya_scenesetup import skeleton
    from maya_uebridge import animimport
    gate("scope: the active namespace", scope.active_namespace(cmds) == ACTIVE, scope.active_namespace(cmds))
    gate("scope: the decoy is not the active tab's", not scope.in_active(DECOY + ":root", cmds))
    gate("scope: the current namespace is the active tab's",
         cmds.namespaceInfo(currentNamespace=True).lstrip(":") == ACTIVE)
    gate("rigs: none in the active tab (the decoy's is not seen)", maya_rigs.rigs() == [],
         [r.namespace for r in maya_rigs.rigs()])
    rig, refusal = maya_rigs.current_rig([])
    gate("rigs: current_rig says there is none, not two", rig is None and refusal == maya_rigs.NO_RIG, refusal)
    gate("roots: no skeleton in the active tab", builder.character_roots() == [], builder.character_roots())
    gate("roots: the bridge sees none", animimport.skeleton_roots() == [], animimport.skeleton_roots())
    gate("roots: current_root answers nothing", skeleton.current_root() is None)


def add(ctx):
    import maya_rigs
    from maya_scenesetup import catalog, character, colour
    cmds.select(clear=True)
    message = character.add_character(catalog.default_rig())
    rigs = maya_rigs.rigs()
    gate("add: the rig is the active tab's", [r.namespace for r in rigs] == [ACTIVE + ":Manny_Rig"],
         ([r.namespace for r in rigs], message))
    gate("add: the line names it as the tab shows it", "as Manny_Rig" in message, message)
    gate("add: its character group and layer are in the tab, named as the tab shows them",
         cmds.objExists(ACTIVE + ":Manny_Rig_Character") and cmds.objExists(ACTIVE + ":Manny_Rig_Layer"))
    gate("add: Main selected", cmds.ls(selection=True) == [ACTIVE + ":Manny_Rig:Main"], cmds.ls(selection=True))
    free = colour.free_colour()
    gate("add: the tab's free colour is the palette's first (the decoy wears it)",
         free is not None and getattr(free, "rgb", free) == colour.PALETTE[0].rgb,
         (free, colour.our_materials()))
    message = character.add_character(catalog.default_character())
    gate("add: a bare skeleton in the tab", cmds.objExists(ACTIVE + ":root")
         and cmds.objExists(ACTIVE + ":Manny_Skeleton_Character"), message)
    gate("scope: the current namespace is still the tab's after two imports",
         cmds.namespaceInfo(currentNamespace=True).lstrip(":") == ACTIVE)
    ctx["rig"] = maya_rigs.rigs()[0]


def retarget(ctx):
    import maya_rig_retarget
    pelvis = cmds.ls(ACTIVE + ":pelvis", long=True)[0]
    for frame, value in ((0, 0.0), (10, 20.0)):
        cmds.setKeyframe(pelvis, attribute="translateX", time=frame, value=value)
    cmds.playbackOptions(minTime=0, maxTime=10)
    ok, text = maya_rig_retarget.run_retarget(source_root=cmds.ls(ACTIVE + ":root", long=True)[0],
                                              rig=ctx["rig"], bones="rotation")
    gate("retarget: in the tab, onto the tab's rig", ok and "rigs in the scene" not in text, text[:200])
    gate("retarget: the rig took the clip",
         (cmds.keyframe(ACTIVE + ":Manny_Rig:RootX_M", q=True, keyframeCount=True) or 0) > 0)
    gate("retarget: its camera in the rig's namespace",
         cmds.objExists(ACTIVE + ":Manny_Rig:SceneSetup_camera"),
         cmds.ls("*SceneSetup_camera*", recursive=True))


def export(ctx):
    from maya_uebridge import animexport
    cmds.select(clear=True)
    root = animexport.resolve_root()
    first = root[0] if isinstance(root, tuple) else root
    gate("export: nothing selected names the tab's character", bool(first) and scope.in_active(first, cmds), root)
    cmds.select(ACTIVE + ":root")
    fbx = RUN + "/scoped_export.fbx"
    animexport.export_hierarchy(fbx, layout="plain")
    with scope.at_root(cmds):                                    # read back beside everything, then gone
        mel.eval("FBXImportMode -v add")
        cmds.file(fbx, i=True, type="FBX", namespace="chk", ignoreVersion=True)
    names = [n.split("|")[-1] for n in cmds.ls("chk:*", type="joint", long=True) or []]
    nested = [n for n in names if n.count(":") != 1]
    gate("export: the file's bones plain (read back as chk:root, chk:pelvis)",
         "chk:root" in names and "chk:pelvis" in names and not nested, (len(names), nested[:4]))
    cmds.namespace(removeNamespace=":chk", deleteNamespaceContent=True)
    gate("export: the tab's skeleton keeps its names", cmds.objExists(ACTIVE + ":root")
         and cmds.objExists(ACTIVE + ":pelvis"))


def weapon(ctx):
    import maya_rigs
    from maya_scenesetup import catalog, equip
    line = equip.to_hand(maya_rigs.rigs()[0].skeleton_root, "R", catalog.WEAPONS[0])
    weapons = cmds.ls("*.mayaWeapon", objectsOnly=True, recursive=True) or []
    gate("weapon: in the tab", weapons and all(n.split("|")[-1].startswith(ACTIVE + ":") for n in weapons),
         (weapons, line))
    gate("weapon: the line names the character as the tab shows it", "Manny_Rig's" in line, line)


def delete(ctx):
    from maya_scenesetup import deletion
    line = deletion.delete_selected([cmds.ls(ACTIVE + ":root", long=True)[0]], confirm=lambda *a, **k: True)
    gate("delete: the tab's skeleton went", not cmds.objExists(ACTIVE + ":root"), line)
    gate("delete: the decoy's plain skeletons stayed", len(cmds.ls(DECOY + ":root") or []) == 2)


def clip(ctx):
    from maya_uebridge import formats, nativeimport
    joints = [{"name": "clipHips", "parent": None, "t": (0, 90, 0)},
              {"name": "clipSpine", "parent": 0, "t": (0, 10, 0)}]
    formats.build("clipX", joints, [None, None], [], set_timeline=False)
    gate("clip: built at the root", cmds.objExists(":clipX:clipHips"))
    gate("clip: the current namespace is the tab's again",
         cmds.namespaceInfo(currentNamespace=True).lstrip(":") == ACTIVE)
    note = nativeimport.merge_into_root("clipX")
    gate("clip: kept, it merges into the tab", cmds.objExists(ACTIVE + ":clipHips")
         and not cmds.namespace(exists=":clipX"), note)


def save(ctx):
    saved = saving.save_tab()
    saving.save_tab(path=RUN + "/plain_tab.ma", adopt=False)
    with open(RUN + "/plain_tab.ma") as handle:
        text = handle.read()
    named = [line for line in text.splitlines()
             if line.startswith(("createNode", "connectAttr", "parent ", "rename ")) and "tab_" in line]
    gate("save: the tab's file holds its rig, every node named without the tab",
         '"Manny_Rig:Main"' in text and not named, (saved, named[:3]))
    gate("save: the rig's clip label names no tab", '"tab_plain"' not in text)


def shared(ctx):
    opening.open_tab(ctx["film"])
    target = RUN + "/shared_copy.ma"
    scope.export_scene(target, "mayaAscii", cmds)
    with open(target) as handle:
        text = handle.read()
    gate("shared: the active tab alone, no prefix", "tab_" not in text and '"hero"' in text)
    gate("shared: its reference written in", '"ref:box"' in text and "file -r " not in text)
    gate("shared: the tab keeps its own path", records.tab(session.state(), "tab_film")["path"] == ctx["film"])


def decoy(ctx):
    switching.switch(DECOY)
    after = decoy_snapshot()
    for key in ("nodes", "keys", "worlds", "colours"):
        same = after[key] == ctx["before"][key]
        detail = "" if same else (sorted(set(map(str, after[key])) ^ set(map(str, ctx["before"][key])))[:8])
        gate("decoy: %s untouched" % key, same, detail)
    tabs = set(t["ns"] for t in session.state()["tabs"])
    every = [n.lstrip(":") for n in cmds.namespaceInfo(":", listOnlyNamespaces=True, recurse=True) or []]
    stray = [n for n in every if n.split(":")[0] not in tabs | {"UI", "shared"} or ":tab_" in n]
    gate("scene: no stray or doubled namespace", not stray, stray)


def open_scene(ctx):
    """Open scene on a weapon's right-button menu: its FBX opens in a tab of its own, the session stays."""
    from maya_scenesetup import catalog, opener
    before = [t["ns"] for t in session.state()["tabs"]]
    entry = catalog.WEAPONS[0]
    text = opener.open_asset(entry.path, entry.label)
    after = [t["ns"] for t in session.state()["tabs"]]
    new = [ns for ns in after if ns not in before]
    gate("open scene: a weapon's FBX opens in a tab of its own",
         len(new) == 1 and scope.active_namespace(cmds) == new[0], (new, text))
    meshes = cmds.ls(new[0] + ":*", type="mesh", recursive=True) or [] if new else []
    gate("open scene: its model is in that tab", bool(meshes), meshes[:2])
    gate("open scene: every other tab stays open", all(ns in after for ns in before), after)


def main():
    from maya_scenesetup import catalog, character
    rig_file, plain_file, film_file = copy("rig.ma"), copy("plain.mb"), copy("film.ma")
    cmds.file(new=True, force=True)
    cmds.file(rig_file, open=True, force=True)
    character.add_character(catalog.default_character())                         # plain `root`
    character.add_character(catalog.character_for("UE4_Mannequin", "skeleton"))   # untextured: red
    opening.open_tab(plain_file)
    gate("setup: the decoy tab holds a rig and two plain skeletons",
         cmds.objExists(DECOY + ":Manny_Rig:Main") and len(cmds.ls(DECOY + ":root") or []) == 2)
    switching.switch(DECOY)
    ctx = {"before": decoy_snapshot(), "film": film_file}
    switching.switch(ACTIVE)
    for name, run in (("questions", questions), ("add", add), ("retarget", retarget), ("export", export),
                      ("weapon", weapon), ("delete", delete), ("clip", clip), ("save", save),
                      ("shared", shared), ("decoy", decoy), ("open_scene", open_scene)):
        section(name, run, ctx)


if __name__ == "__main__":
    try:
        main()
    except Exception:                                            # noqa: BLE001
        gate("ran to the end", False, traceback.format_exc())
    failed = RESULTS.count(False)
    print("%d of %d gates failed" % (failed, len(RESULTS)))
    maya.standalone.uninitialize()
    sys.exit(1 if failed else 0)
```

- [ ] **Step 6: Run it - it fails until the edits are in**

Run (the fixtures must exist: run `verify_scene_tabs.py all` once first if `%TEMP%/skeldar_tabs_verify/fixtures.done` is missing):

```
$env:MAYA_APP_DIR = "$env:TEMP\skeldar_tabs_appdir"; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs/superpowers/plans/verify_tabs_scope.py
```

Expected: `20 of 33 gates failed` - still failing (a later task's):

  - rigs: none in the active tab (the decoy's is not seen)
  - rigs: current_rig says there is none, not two
  - roots: no skeleton in the active tab
  - roots: the bridge sees none
  - roots: current_root answers nothing
  - add: the rig is the active tab's
  - add: its character group and layer are in the tab, named as the tab shows them
  - add: Main selected
  - add: the tab's free colour is the palette's first (the decoy wears it)
  - add: a bare skeleton in the tab
  - retarget: ran to the end
  - export: ran to the end
  - weapon: the line names the character as the tab shows it
  - clip: ran to the end
  - save: ran to the end
  - shared: ran to the end
  - scene: no stray or doubled namespace
  - open scene: a weapon's FBX opens in a tab of its own
  - open scene: its model is in that tab
  - open scene: every other tab stays open

This is stage 1 with nothing of stage 2 but `scope.py`: the plugin's own creations double the tab's prefix (the retarget's holder) and its readers see the decoy. Every later task makes more of these pass; Task 6 ends with none failing.

- [ ] **Step 7: The spec addendum**

Append to `docs/superpowers/specs/2026-10-15-scene-tabs-plugin-scope-design.md`:

```markdown

## Addendum: measured while planning (2026-10-15)

- **Maya resolves a creation or rename name relative to the CURRENT namespace, even when the name carries
  a namespace**, and creates the missing namespaces silently: with `tabx` current, `createNode(name=
  "tabx:Rig:a")` made `tabx:tabx:Rig:a`. Lookups (`ls`, `objExists`) go from the root. So "made relative so
  it lands in the active tab" is two rules, not one: the current namespace is the active tab's (stage 1
  sets it on a switch; every reset to `":"` after an import becomes `scope.enter_active`), and every name that
  carries a namespace is made absolute where a node is created or renamed with it (`scope.as_created`; a
  name given back after a hold, `scope.root_name`). A leaf (`hand_r_weaponSpace`, `<leaf>_knot`) stays
  relative and lands in the tab. A node made with `":A:x"` is answered as `"A:x"`.
- **Stage 1 alone breaks the plugin inside a tab** (Task 1's measurement): the retarget's holder
  `tab_plain:Manny_Rig:MoCapConstraints` was created as `tab_plain:tab_plain:Manny_Rig:MoCapConstraints` and
  the next `setAttr` found nothing. The two stages ship together.
- **Sites the main text did not list**, each with an edit: the namespace resets after an import
  (`animimport`, `formats`, `deletion`); a clip's namespace made at the root whatever is current
  (`animimport` already set `":"` first; `formats._in_namespace` adds `":" + name`); `character.
  existing_namespaces` (a new character's namespace is taken in the tab, a clip's at the root: both must be
  free); `choose_target_root(home=)` (inside a tab every node carries its namespace: `tab_x:root` is plain);
  Add Character qualifying the namespace its import made; the armor piece's namespace taken off in the tab;
  the Pose Library's rebuilt skeleton moved under the tab; Shared and Stash - a scene received opens as a tab,
  an FBX imports into one (`home_namespace`), a copy sent is the active tab alone with its references written
  in (`saving.save_tab(preserve_references=False)` through `scope.export_scene`); Open scene (a portrait's or
  a weapon's file) opens a tab; the scene's name (Shared, Stash, the Pose Library's capture, the clip label,
  Walk Builder) is the active tab's file; and the names a message or a label shows (`equip` / `armor`'s
  character, the clip label's clip, a character group's base) are read with the tab's prefix taken off
  (`scope.local`, `scope.relative`) - «the outermost namespace» was the tab.
- **Viewport Studio**: each tab has its own studio (built in the tab by its plain names, found there).
- **The proof** is one script with independent sections, not the seven verifies re-run inside a tab (each of
  them opens or news scenes itself): a decoy tab holding a keyed Manny rig, a Manny UE5 skeleton and a UE4
  Mannequin skeleton (untextured, so it wears the palette's red - Manny and the Creep are textured since
  2026-09-30 and wear none), the work in another tab (questions, Add Character, a retarget with its camera,
  an export read back, a weapon, Delete, a clip kept, a save, Shared's copy), the decoy checked untouched
  and no stray or doubled namespace left, and last Open scene on a weapon's FBX opening a tab of its own.
  Not proven headless (the animator's): the drags onto the viewport with a hidden tab behind the active one.
- **Known and stated**: an FBX export from a tab carries the name of a display layer its bones are in with
  the tab's prefix (`tab_plain:DeformationJoints`, the Manny skeleton asset's leftover AdvancedSkeleton
  layer) - a collection, not a bone; read back, every bone is plain. A saved tab file keeps strings that
  once held a node's name (a camera's `imageName` `tab_plain:camera2`): a save renames nodes, not strings.
```

- [ ] **Step 8: Commit**

```bash
cd "/c/!!!Work/MayaScripts"
cat > "$TEMP/scenetabs2_msg.txt" <<'EOF'
feat(scenetabs): scope - the active tab's namespace, readers, names; the stage 2 proof

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git add SkeldarAnim/maya_scenetabs/scope.py tests/test_scenetabs_scope.py docs/superpowers/plans/verify_tabs_scope.py docs/superpowers/specs/2026-10-15-scene-tabs-plugin-scope-design.md
git commit -F "$TEMP/scenetabs2_msg.txt"
```

---

### Task 2: The scene readers see the active tab

**Files:**
- Modify: `SkeldarAnim/maya_rigs.py`
- Modify: `SkeldarAnim/maya_overrig/naming.py`
- Modify: `SkeldarAnim/maya_overrig/active.py`
- Modify: `SkeldarAnim/maya_uebridge/animimport.py`
- Modify: `SkeldarAnim/maya_scenesetup/weaponspace.py`
- Modify: `SkeldarAnim/maya_scenesetup/colour.py`
- Modify: `SkeldarAnim/maya_asretarget.py`
- Modify: `SkeldarAnim/maya_pmretarget.py`
- Modify: `SkeldarAnim/maya_vpstudio.py`
- Modify: `SkeldarAnim/maya_com/network.py`
- Modify: `docs/superpowers/plans/verify_scene_tabs.py`

**Interfaces:**
- Consumes: `maya_scenetabs.scope` (Task 1) - `active_only(paths, cmds_)`, `active_namespace(cmds_)`.
- Produces: `maya_rigs.rigs()`, `builder.character_roots()`, `animimport.skeleton_roots()`, `colour.free_colour()`, `maya_vpstudio.find_rig()` and the other readers answer for the active tab only; `animimport.choose_target_root(roots, selected_roots=(), bound_root=None, home="")`.

**The rule:** a question about the scene is asked of the active tab. Every listing below that answers "which character, rig, skeleton, colour or studio" keeps only the active tab's paths. `choose_target_root` gets the tab's namespace as `home`: inside a tab every node carries it, and a skeleton is plain when it carries nothing more.

- [ ] **Step 1: `SkeldarAnim/maya_rigs.py`**

Below `import maya.cmds as cmds` (the module's first `cmds` import), add a blank line and `from maya_scenetabs import scope`:

```python
import maya.cmds as cmds

from maya_scenetabs import scope
```

Replace (it occurs once):

```python
    return [top for top in cmds.ls(assemblies=True, long=True) or [] if is_character_group(top)]
```

with:

```python
    return [top for top in scope.active_only(cmds.ls(assemblies=True, long=True) or [], cmds)
            if is_character_group(top)]
```

Replace (it occurs once):

```python
    found, level = [], cmds.ls(assemblies=True, long=True) or []
    for _ in range(depth):
```

with:

```python
    found, level = [], scope.active_only(cmds.ls(assemblies=True, long=True) or [], cmds)
    for _ in range(depth):
```

Replace (it occurs once):

```python
    return [s for s in (cmds.ls(type="objectSet") or []) if leaf(s) == CONTROL_SET]
```

with:

```python
    return [s for s in scope.active_only(cmds.ls(type="objectSet") or [], cmds)
            if leaf(s) == CONTROL_SET]
```

- [ ] **Step 2: `SkeldarAnim/maya_overrig/naming.py`**

Below `import maya.cmds as cmds` (the module's first `cmds` import), add a blank line and `from maya_scenetabs import scope`:

```python
import maya.cmds as cmds

from maya_scenetabs import scope
```

Replace (it occurs once):

```python
    for joint in cmds.ls(type="joint", long=True) or []:
        if joint in excluded
```

with:

```python
    for joint in scope.active_only(cmds.ls(type="joint", long=True) or [], cmds):
        if joint in excluded
```

- [ ] **Step 3: `SkeldarAnim/maya_overrig/active.py`**

Below `import maya.cmds as cmds` (the module's first `cmds` import), add a blank line and `from maya_scenetabs import scope`:

```python
import maya.cmds as cmds

from maya_scenetabs import scope
```

Replace (it occurs once):

```python
    found, level = [], cmds.ls(assemblies=True, long=True) or []
    for _ in range(3):
```

with:

```python
    found, level = [], scope.active_only(cmds.ls(assemblies=True, long=True) or [], cmds)
    for _ in range(3):
```

- [ ] **Step 4: `SkeldarAnim/maya_uebridge/animimport.py`**

Below `import maya.cmds as cmds` (the module's first `cmds` import), add a blank line and `from maya_scenetabs import scope`:

```python
import maya.cmds as cmds

from maya_scenetabs import scope
```

Replace (it occurs once):

```python
    for joint in (cmds.ls(type="joint", long=True) or []):
        if not cmds.listRelatives(joint, parent=True, fullPath=True,
```

with:

```python
    for joint in scope.active_only(cmds.ls(type="joint", long=True) or [], cmds):
        if not cmds.listRelatives(joint, parent=True, fullPath=True,
```

Replace (it occurs once):

```python
def choose_target_root(roots, selected_roots=(), bound_root=None):
```

with:

```python
def choose_target_root(roots, selected_roots=(), bound_root=None, home=""):
```

Replace (it occurs once):

```python
    Guessing between two plausible skeletons would animate the wrong
    character without saying so, which is worse than asking.
    """
    def plain_only(paths):
        return [root for root in (paths or [])
                if root and ":" not in _short(root)]
```

with:

```python
    Guessing between two plausible skeletons would animate the wrong
    character without saying so, which is worse than asking.

    `home` is the active scene tab's namespace (2026-10-15): inside a tab
    every node carries it, and a skeleton is plain when it carries nothing
    more (`tab_x:root`).
    """
    def local(path):
        short = _short(path)
        return short[len(home) + 1:] if home and short.startswith(home + ":") else short

    def plain_only(paths):
        return [root for root in (paths or [])
                if root and ":" not in local(root)]
```

Replace (it occurs once):

```python
    named = [root for root in plain if _short(root) == "root"]
```

with:

```python
    named = [root for root in plain if local(root) == "root"]
```

Replace (it occurs once):

```python
    return choose_target_root(skeleton_roots(), selected_roots(),
                              connected_root())
```

with:

```python
    return choose_target_root(skeleton_roots(), selected_roots(),
                              connected_root(), home=scope.active_namespace(cmds))
```

- [ ] **Step 5: `SkeldarAnim/maya_scenesetup/weaponspace.py`**

Below `import maya.cmds as cmds` (the module's first `cmds` import), add a blank line and `from maya_scenetabs import scope`:

```python
import maya.cmds as cmds

from maya_scenetabs import scope
```

Replace (it occurs once):

```python
        if parent else (cmds.ls(assemblies=True, long=True) or [])
```

with:

```python
        if parent else scope.active_only(cmds.ls(assemblies=True, long=True) or [], cmds)
```

- [ ] **Step 6: `SkeldarAnim/maya_scenesetup/colour.py`**

Below `import maya.cmds as cmds` (the module's first `cmds` import), add a blank line and `from maya_scenetabs import scope`:

```python
import maya.cmds as cmds

from maya_scenetabs import scope
```

Replace (it occurs once):

```python
    return [material for material in (cmds.ls(materials=True) or [])
            if is_ours(material)]
```

with:

```python
    return [material for material in scope.active_only(cmds.ls(materials=True) or [], cmds)
            if is_ours(material)]
```

Replace (it occurs once):

```python
    for material in cmds.ls(materials=True) or []:
        try:
            if not cmds.attributeQuery(TEXTURE_MARKER, node=material,
```

with:

```python
    for material in scope.active_only(cmds.ls(materials=True) or [], cmds):
        try:
            if not cmds.attributeQuery(TEXTURE_MARKER, node=material,
```

- [ ] **Step 7: `SkeldarAnim/maya_asretarget.py`**

Below `import maya.cmds as cmds` (the module's first `cmds` import), add a blank line and `from maya_scenetabs import scope`:

```python
import maya.cmds as cmds

from maya_scenetabs import scope
```

Replace (it occurs once):

```python
    joints = cmds.ls(type="joint", long=True) or []
    if source_root is None:
```

with:

```python
    joints = scope.active_only(cmds.ls(type="joint", long=True) or [], cmds)
    if source_root is None:
```

- [ ] **Step 8: `SkeldarAnim/maya_pmretarget.py`**

Below `import maya.cmds as cmds` (the module's first `cmds` import), add a blank line and `from maya_scenetabs import scope`:

```python
import maya.cmds as cmds

from maya_scenetabs import scope
```

Replace (it occurs once):

```python
    joints = cmds.ls(type="joint", long=True) or []
    if source_root is None:
```

with:

```python
    joints = scope.active_only(cmds.ls(type="joint", long=True) or [], cmds)
    if source_root is None:
```

- [ ] **Step 9: `SkeldarAnim/maya_vpstudio.py`**

Below `import maya.cmds as cmds` (the module's first `cmds` import), add a blank line and `from maya_scenetabs import scope`:

```python
import maya.cmds as cmds

from maya_scenetabs import scope
```

Replace (it occurs once):

```python
    wanted = cmds.ls(type="mesh", long=True, noIntermediate=True) or []
    if rig:
```

with:

```python
    wanted = scope.active_only(cmds.ls(type="mesh", long=True, noIntermediate=True) or [], cmds)
    if rig:
```

Replace (it occurs once):

```python
    joints = cmds.ls(type="joint", long=True) or []
    if rig:
        joints = [j for j in joints if not _under(j, rig)]
```

with:

```python
    joints = scope.active_only(cmds.ls(type="joint", long=True) or [], cmds)
    if rig:
        joints = [j for j in joints if not _under(j, rig)]
```

Replace (it occurs once):

```python
    found = cmds.ls("*." + MARKER, objectsOnly=True, long=True,
                    recursive=True) or []
```

with:

```python
    found = scope.active_only(cmds.ls("*." + MARKER, objectsOnly=True, long=True,
                                      recursive=True) or [], cmds)
```

- [ ] **Step 10: `SkeldarAnim/maya_com/network.py`**

Below `import maya.cmds as cmds` (the module's first `cmds` import), add a blank line and `from maya_scenetabs import scope`:

```python
import maya.cmds as cmds

from maya_scenetabs import scope
```

Replace (it occurs once):

```python
    for node in cmds.ls(type="transform", long=True) or []:
        if cmds.attributeQuery(MARKER, node=node, exists=True):
```

with:

```python
    for node in scope.active_only(cmds.ls(type="transform", long=True) or [], cmds):
        if cmds.attributeQuery(MARKER, node=node, exists=True):
```

- [ ] **Step 11: Stage 1's proof: one gate becomes stage 2's**

In `docs/superpowers/plans/verify_scene_tabs.py` (stage 1's proof) one gate asked a scene-wide question that stage 2 now answers for the active tab only. Replace (it occurs once):

```python
    gate("open: the rig is still found", [r.namespace for r in maya_rigs.rigs()] == ["tab_rig:Manny_Rig"])
```

with:

```python
    gate("open: a hidden tab's rig is not the active tab's (stage 2)", maya_rigs.rigs() == [],
         [r.namespace for r in maya_rigs.rigs()])
```

Then run stage 1's proof:

```
$env:MAYA_APP_DIR = "$env:TEMP\skeldar_tabs_appdir"; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs/superpowers/plans/verify_scene_tabs.py all
```

Expected: `0 of 127 gates failed`.

- [ ] **Step 12: Run the unit suite**

Run:

```
$env:QT_QPA_PLATFORM = 'offscreen'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t .
```

Expected: no failure that was not there before this task (on the planning snapshot the whole suite ran with no new failure after this task).

- [ ] **Step 13: Run the proof**

Run:

```
$env:MAYA_APP_DIR = "$env:TEMP\skeldar_tabs_appdir"; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs/superpowers/plans/verify_tabs_scope.py
```

Expected: `14 of 35 gates failed` - still failing (a later task's):

  - add: its character group and layer are in the tab, named as the tab shows them
  - add: Main selected
  - add: a bare skeleton in the tab
  - retarget: ran to the end
  - export: the file's bones plain (read back as chk:root, chk:pelvis)
  - export: the tab's skeleton keeps its names
  - weapon: the line names the character as the tab shows it
  - clip: ran to the end
  - save: ran to the end
  - shared: ran to the end
  - scene: no stray or doubled namespace
  - open scene: a weapon's FBX opens in a tab of its own
  - open scene: its model is in that tab
  - open scene: every other tab stays open

«export: the file's bones plain (read back as chk:root, chk:pelvis)», «export: the tab's skeleton keeps its names» did not run after the previous task (their section stopped earlier).

- [ ] **Step 14: Commit**

```bash
cd "/c/!!!Work/MayaScripts"
cat > "$TEMP/scenetabs2_msg.txt" <<'EOF'
feat(scenetabs): the plugin's scene readers see the active tab only

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git add SkeldarAnim/maya_rigs.py SkeldarAnim/maya_overrig/naming.py SkeldarAnim/maya_overrig/active.py SkeldarAnim/maya_uebridge/animimport.py SkeldarAnim/maya_scenesetup/weaponspace.py SkeldarAnim/maya_scenesetup/colour.py SkeldarAnim/maya_asretarget.py SkeldarAnim/maya_pmretarget.py SkeldarAnim/maya_vpstudio.py SkeldarAnim/maya_com/network.py docs/superpowers/plans/verify_scene_tabs.py
git commit -F "$TEMP/scenetabs2_msg.txt"
```


---

### Task 3: Names a node is created or renamed with, made absolute

**Files:**
- Modify: `SkeldarAnim/maya_scenesetup/chargroup.py`
- Modify: `SkeldarAnim/maya_asretarget.py`
- Modify: `SkeldarAnim/maya_pmretarget.py`
- Modify: `SkeldarAnim/maya_retargetmode.py`
- Modify: `SkeldarAnim/maya_com/network.py`
- Modify: `SkeldarAnim/maya_poselib/apply.py`
- Modify: `SkeldarAnim/maya_scenesetup/camera.py`
- Modify: `SkeldarAnim/maya_scenesetup/cliplabel.py`
- Modify: `SkeldarAnim/maya_uebridge/rigimport.py`
- Modify: `SkeldarAnim/maya_uebridge/skeletonimport.py`
- Modify: `SkeldarAnim/maya_uebridge/animimport.py`
- Modify: `SkeldarAnim/maya_uebridge/fbxlayout.py`
- Modify: `tests/test_uebridge_rigimport.py`

**Interfaces:**
- Consumes: `maya_scenetabs.scope` (Task 1) - `as_created(name)`, `root_name(name)`, `absolute(name, cmds_)`.
- Produces: the retargets' `_made(rig, leaf)`, `maya_com.network._made(namespace, leaf)`; every node created with a namespaced name lands where its name says, whatever namespace is current.

**The rule:** Maya resolves a creation or rename name relative to the CURRENT namespace even when it carries a namespace (measured: `tabx:Rig:a` made `tabx:tabx:Rig:a`). A name built from a leaf needs nothing; a name that carries a namespace is made absolute where a node is created or renamed with it; a name given back after a hold is the full name from the root.

- [ ] **Step 1: `SkeldarAnim/maya_scenesetup/chargroup.py`**

Below `import maya.cmds as cmds` (the module's first `cmds` import), add a blank line and `from maya_scenetabs import scope`:

```python
import maya.cmds as cmds

from maya_scenetabs import scope
```

Replace (it occurs once):

```python
def taken_names():
    """Root-namespace node names in the scene (what a new group or layer must not collide with)."""
    return set(n for n in (cmds.ls() or []) if ":" not in n and "|" not in n)
```

with:

```python
def taken_names():
    """Node names in the namespace a new group or layer goes into - the active scene tab's while
    tabs are on (2026-10-15), else the root - with that namespace taken off."""
    active = scope.active_namespace(cmds)
    prefix = active + ":" if active else ""
    names = [n for n in (cmds.ls() or []) if "|" not in n]
    if not prefix:
        return set(n for n in names if ":" not in n)
    return set(n[len(prefix):] for n in names
               if n.startswith(prefix) and ":" not in n[len(prefix):])
```

Replace (it occurs once):

```python
        group = cmds.createNode("transform", name=":" + group_name(base), skipSelect=True)
```

with:

```python
        group = cmds.createNode("transform", name=scope.absolute(group_name(base), cmds),
                                skipSelect=True)
```

Replace (it occurs once):

```python
        layer = cmds.createDisplayLayer(name=":" + layer_name(base), empty=True, noRecurse=True)
```

with:

```python
        layer = cmds.createDisplayLayer(name=scope.absolute(layer_name(base), cmds), empty=True,
                                        noRecurse=True)
```

Replace (it occurs once):

```python
                    cmds.rename(now, name)
```

with:

```python
                    cmds.rename(now, scope.root_name(name))
```

- [ ] **Step 2: `SkeldarAnim/maya_asretarget.py`**

Replace (it occurs once):

```python
    return maya_rigs.node(rig, leaf_name)
```

with:

```python
    return maya_rigs.node(rig, leaf_name)


def _made(rig, leaf_name):
    """`_n` for a node about to be CREATED: absolute, so it lands in the rig's
    namespace whatever namespace is current (a scene tab's, 2026-10-15)."""
    return scope.as_created(_n(rig, leaf_name))
```

Replace EVERY occurrence (10) of the text between the quotes `'name=_n(rig, '` with `'name=_made(rig, '` - the trailing space is part of both.

Replace (it occurs once):

```python
        cmds.createNode("transform", name=holder, skipSelect=True)
```

with:

```python
        cmds.createNode("transform", name=scope.as_created(holder), skipSelect=True)
```

- [ ] **Step 3: `SkeldarAnim/maya_pmretarget.py`**

Replace (it occurs once):

```python
    return maya_rigs.node(rig, leaf_name)
```

with:

```python
    return maya_rigs.node(rig, leaf_name)


def _made(rig, leaf_name):
    """`_n` for a node about to be CREATED: absolute, so it lands in the rig's
    namespace whatever namespace is current (a scene tab's, 2026-10-15)."""
    return scope.as_created(_n(rig, leaf_name))
```

Replace EVERY occurrence (7) of the text between the quotes `'name=_n(rig, '` with `'name=_made(rig, '` - the trailing space is part of both.

Replace (it occurs once):

```python
        cmds.createNode("transform", name=holder, skipSelect=True)
```

with:

```python
        cmds.createNode("transform", name=scope.as_created(holder), skipSelect=True)
```

Replace (it occurs once):

```python
        grp = cmds.createNode("transform", name=group, parent=holder_of(rig), skipSelect=True)
```

with:

```python
        grp = cmds.createNode("transform", name=scope.as_created(group), parent=holder_of(rig),
                              skipSelect=True)
```

- [ ] **Step 4: `SkeldarAnim/maya_retargetmode.py`**

Replace (it occurs once):

```python
    space = cmds.createNode("transform", name=name + "Space", **kwargs)
```

with:

```python
    from maya_scenetabs import scope
    space = cmds.createNode("transform", name=scope.as_created(name + "Space"), **kwargs)
```

Replace (it occurs once):

```python
    scaled = cmds.createNode("transform", name=name + "Scaled", parent=space, skipSelect=True)
```

with:

```python
    scaled = cmds.createNode("transform", name=scope.as_created(name + "Scaled"), parent=space,
                             skipSelect=True)
```

Replace (it occurs once):

```python
    follow = cmds.createNode("transform", name=name + "Follow", parent=space, skipSelect=True)
```

with:

```python
    from maya_scenetabs import scope
    follow = cmds.createNode("transform", name=scope.as_created(name + "Follow"), parent=space,
                             skipSelect=True)
```

Replace (it occurs once):

```python
    body = cmds.createNode("transform", name=name + "Body", parent=scaled, skipSelect=True)
```

with:

```python
    body = cmds.createNode("transform", name=scope.as_created(name + "Body"), parent=scaled,
                           skipSelect=True)
```

Replace (it occurs once):

```python
    unit = cmds.createNode("transform", name=name, parent=body, skipSelect=True)
```

with:

```python
    unit = cmds.createNode("transform", name=scope.as_created(name), parent=body,
                           skipSelect=True)
```

- [ ] **Step 5: `SkeldarAnim/maya_com/network.py`**

Replace (it occurs once):

```python
def name_in(namespace, leaf):
    return namespace + ":" + leaf if namespace else leaf
```

with:

```python
def name_in(namespace, leaf):
    return namespace + ":" + leaf if namespace else leaf


def _made(namespace, leaf):
    """`name_in` for a node about to be CREATED: absolute (a scene tab may be current)."""
    return scope.as_created(name_in(namespace, leaf))
```

Replace EVERY occurrence (6) of `name=name_in(` with `name=_made(`.

- [ ] **Step 6: `SkeldarAnim/maya_poselib/apply.py`**

Replace (it occurs once):

```python
name=namespace + ":" + REST_PROXY
```

with:

```python
name=":" + namespace + ":" + REST_PROXY
```

Replace (it occurs once):

```python
name=namespace + ":restSkin"
```

with:

```python
name=":" + namespace + ":restSkin"
```

- [ ] **Step 7: `SkeldarAnim/maya_scenesetup/camera.py`**

Below `import maya.cmds as cmds` (the module's first `cmds` import), add a blank line and `from maya_scenetabs import scope`:

```python
import maya.cmds as cmds

from maya_scenetabs import scope
```

Replace (it occurs once):

```python
        transform = cmds.ls(cmds.rename(transform, name), long=True)[0]
```

with:

```python
        transform = cmds.ls(cmds.rename(transform, scope.as_created(name)), long=True)[0]
```

Replace (it occurs once):

```python
        shape = cmds.rename(shape, name + "Shape")
```

with:

```python
        shape = cmds.rename(shape, scope.as_created(name + "Shape"))
```

- [ ] **Step 8: `SkeldarAnim/maya_scenesetup/cliplabel.py`**

Below `import maya.cmds as cmds` (the module's first `cmds` import), add a blank line and `from maya_scenetabs import scope`:

```python
import maya.cmds as cmds

from maya_scenetabs import scope
```

Replace (it occurs once):

```python
    label = cmds.createNode("transform", name=node_name(namespace, root),
```

with:

```python
    label = cmds.createNode("transform", name=scope.as_created(node_name(namespace, root)),
```

Replace (it occurs once):

```python
    shape = cmds.createNode("annotationShape", name=label.split("|")[-1] + "Shape",
```

with:

```python
    shape = cmds.createNode("annotationShape",
                            name=scope.as_created(label.split("|")[-1] + "Shape"),
```

Replace (it occurs once):

```python
name="{0}_{1}".format(base, suffix)
```

with:

```python
name=scope.as_created("{0}_{1}".format(base, suffix))
```

- [ ] **Step 9: `SkeldarAnim/maya_uebridge/rigimport.py`**

Below `import maya.cmds as cmds` (the module's first `cmds` import), add a blank line and `from maya_scenetabs import scope`:

```python
import maya.cmds as cmds

from maya_scenetabs import scope
```

Replace (it occurs once):

```python
    group = cmds.group(source, name="{0}:{1}".format(namespace, SHIFT_NODE))
```

with:

```python
    group = cmds.group(source, name=scope.as_created("{0}:{1}".format(namespace, SHIFT_NODE)))
```

- [ ] **Step 10: `SkeldarAnim/maya_uebridge/skeletonimport.py`**

Below `import maya.cmds as cmds` (the module's first `cmds` import), add a blank line and `from maya_scenetabs import scope`:

```python
import maya.cmds as cmds

from maya_scenetabs import scope
```

Replace (it occurs once):

```python
                                  name=(namespace + ":" if namespace else "") + "skeldarUnitScale",
```

with:

```python
                                  name=scope.as_created((namespace + ":" if namespace else "")
                                                        + "skeldarUnitScale"),
```

- [ ] **Step 11: `SkeldarAnim/maya_uebridge/animimport.py`**

Replace (it occurs once):

```python
    try:
        cmds.rename(paths[0], short)
    except RuntimeError:
        pass                  # nothing better to do; the name is cosmetic
```

with:

```python
    try:
        cmds.rename(paths[0], scope.root_name(short))
    except RuntimeError:
        pass                  # nothing better to do; the name is cosmetic
```

Replace (it occurs once):

```python
            cmds.rename(node, hold_name(wanted))
```

with:

```python
            cmds.rename(node, scope.root_name(hold_name(wanted)))
```

Replace (it occurs once):

```python
            if _short(cmds.rename(path, wanted)) == wanted:
```

with:

```python
            if _short(cmds.rename(path, scope.root_name(wanted))) == wanted:
```

Replace (it occurs once):

```python
            try:
                cmds.rename(paths[0], short)
```

with:

```python
            try:
                cmds.rename(paths[0], scope.root_name(short))
```

- [ ] **Step 12: `SkeldarAnim/maya_uebridge/fbxlayout.py`**

Below `import maya.cmds as cmds` (the module's first `cmds` import), add a blank line and `from maya_scenetabs import scope`:

```python
import maya.cmds as cmds

from maya_scenetabs import scope
```

Replace (it occurs once):

```python
                cmds.rename(other, HOLD_PREFIX + name)
```

with:

```python
                cmds.rename(other, ":" + HOLD_PREFIX + name)
```

Replace (it occurs once):

```python
                cmds.rename(path, ":" + original if ":" not in original else original)
        for other in held:
            for path in cmds.ls(other, long=True) or []:
                cmds.rename(path, name)
```

with:

```python
                cmds.rename(path, scope.root_name(original))
        for other in held:
            for path in cmds.ls(other, long=True) or []:
                cmds.rename(path, ":" + name)
```

Replace (it occurs once):

```python
            cmds.rename(node, HOLD_PREFIX + name)
```

with:

```python
            cmds.rename(node, ":" + HOLD_PREFIX + name)
```

Replace (it occurs once):

```python
        for uuid in held:
            for path in cmds.ls(uuid, long=True) or []:
                cmds.rename(path, name)
```

with:

```python
        for uuid in held:
            for path in cmds.ls(uuid, long=True) or []:
                cmds.rename(path, ":" + name)
```

- [ ] **Step 13: The press's fake `cmds.group`**

The press's tests fake `cmds.group` and answered the name they were given; Maya answers a node made by an absolute name WITHOUT the leading colon (measured). In `tests/test_uebridge_rigimport.py` replace (it occurs once):

```python
            group=lambda node, name=None: self.calls.append(("group", node, name)) or (
                self.paths.update({"UUID-" + node: "|%s|%s" % (name, node.lstrip("|"))})
                or name),
```

with:

```python
            # Maya answers a node made by an absolute name without the leading ":" (measured)
            group=lambda node, name=None: self.calls.append(("group", node, name)) or (
                self.paths.update({"UUID-" + node: "|%s|%s" % (name.lstrip(":"), node.lstrip("|"))})
                or name.lstrip(":")),
```

and replace EVERY occurrence (two) of:

```python
[("group", "|A:root", "A:" + rigimport.SHIFT_NODE)]
```

with:

```python
[("group", "|A:root", ":A:" + rigimport.SHIFT_NODE)]
```

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_uebridge_rigimport -v`
Expected: `Ran 51 tests ... OK`.

- [ ] **Step 14: Run the unit suite**

Run:

```
$env:QT_QPA_PLATFORM = 'offscreen'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t .
```

Expected: no failure that was not there before this task (on the planning snapshot the whole suite ran with no new failure after this task).

- [ ] **Step 15: Run the proof**

Run:

```
$env:MAYA_APP_DIR = "$env:TEMP\skeldar_tabs_appdir"; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs/superpowers/plans/verify_tabs_scope.py
```

Expected: `9 of 38 gates failed` - still failing (a later task's):

  - add: its character group and layer are in the tab, named as the tab shows them
  - add: Main selected
  - weapon: the line names the character as the tab shows it
  - clip: ran to the end
  - save: the rig's clip label names no tab
  - shared: ran to the end
  - open scene: a weapon's FBX opens in a tab of its own
  - open scene: its model is in that tab
  - open scene: every other tab stays open

«save: the rig's clip label names no tab» did not run after the previous task (their section stopped earlier).

- [ ] **Step 16: Commit**

```bash
cd "/c/!!!Work/MayaScripts"
cat > "$TEMP/scenetabs2_msg.txt" <<'EOF'
fix(scenetabs): names a node is created or renamed with, made absolute inside a tab

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git add SkeldarAnim/maya_scenesetup/chargroup.py SkeldarAnim/maya_asretarget.py SkeldarAnim/maya_pmretarget.py SkeldarAnim/maya_retargetmode.py SkeldarAnim/maya_com/network.py SkeldarAnim/maya_poselib/apply.py SkeldarAnim/maya_scenesetup/camera.py SkeldarAnim/maya_scenesetup/cliplabel.py SkeldarAnim/maya_uebridge/rigimport.py SkeldarAnim/maya_uebridge/skeletonimport.py SkeldarAnim/maya_uebridge/animimport.py SkeldarAnim/maya_uebridge/fbxlayout.py tests/test_uebridge_rigimport.py
git commit -F "$TEMP/scenetabs2_msg.txt"
```


---

### Task 4: The current namespace is the tab's; what is kept lands in it

**Files:**
- Modify: `SkeldarAnim/maya_uebridge/animimport.py`
- Modify: `SkeldarAnim/maya_uebridge/formats.py`
- Modify: `SkeldarAnim/maya_uebridge/nativeimport.py`
- Modify: `SkeldarAnim/maya_scenesetup/deletion.py`
- Modify: `SkeldarAnim/maya_share.py`
- Modify: `SkeldarAnim/maya_stash.py`
- Modify: `SkeldarAnim/maya_scenesetup/character.py`
- Modify: `SkeldarAnim/maya_scenesetup/armor.py`
- Modify: `SkeldarAnim/maya_poselib/apply.py`

**Interfaces:**
- Consumes: `maya_scenetabs.scope` (Task 1) - `enter_active(cmds_)`, `home_namespace(namespace, cmds_)`, `qualified`, `relative`, `absolute`.
- Produces: a clip imported at the root comes back to the tab's namespace after its import; a kept one moves under the tab; `character.existing_namespaces()` lists the tab's own as if at the root.

**The rule:** the current namespace is the active tab's (stage 1 sets it on a switch), so anything made by a plain name lands in the tab. A reset to `":"` after an import becomes `scope.enter_active`; a clip's own namespace is made at the root (`":" + name`) and, when it is kept, moved under the tab (`home_namespace`).

- [ ] **Step 1: `SkeldarAnim/maya_uebridge/animimport.py`**

Replace (it occurs once):

```python
    found = cmds.namespaceInfo(listOnlyNamespaces=True, recurse=True) or []
```

with:

```python
    #  from the root (2026-10-15): a clip goes into a root-level namespace whatever namespace
    #  is current, and the current one is a scene tab's while tabs are on
    found = cmds.namespaceInfo(":", listOnlyNamespaces=True, recurse=True) or []
```

Replace (it occurs once):

```python
            mel.eval(import_command(fbx_path, take))
        finally:
            cmds.namespace(setNamespace=":")
```

with:

```python
            mel.eval(import_command(fbx_path, take))
        finally:
            scope.enter_active(cmds)
```

Replace (it occurs once):

```python
    new_nodes = set(cmds.ls(long=True)) - before_nodes
```

with:

```python
    scope.enter_active(cmds)          # the merge ran at the root too
    new_nodes = set(cmds.ls(long=True)) - before_nodes
```

- [ ] **Step 2: `SkeldarAnim/maya_uebridge/formats.py`**

Below `import maya.cmds as cmds` (the module's first `cmds` import), add a blank line and `from maya_scenetabs import scope`:

```python
import maya.cmds as cmds

from maya_scenetabs import scope
```

Replace (it occurs once):

```python
    if not cmds.namespace(exists=name):
        return True
    cmds.namespace(setNamespace=":")
```

with:

```python
    if not cmds.namespace(exists=name):
        return True
    scope.enter_active(cmds)
```

Replace (it occurs once):

```python
        cmds.mayaUSDImport(file=path.replace("\\", "/"), readAnimData=True,
                           primPath="/")
    finally:
        cmds.namespace(setNamespace=":")
```

with:

```python
        cmds.mayaUSDImport(file=path.replace("\\", "/"), readAnimData=True,
                           primPath="/")
    finally:
        scope.enter_active(cmds)
```

Replace (it occurs once):

```python
                                                       (euler.x, euler.y, euler.z)])
    finally:
        cmds.namespace(setNamespace=":")
```

with:

```python
                                                       (euler.x, euler.y, euler.z)])
    finally:
        scope.enter_active(cmds)
```

Replace (it occurs once):

```python
        mel.eval(animimport.import_command(sources.staged(model)))
    finally:
        cmds.namespace(setNamespace=":")
```

with:

```python
        mel.eval(animimport.import_command(sources.staged(model)))
    finally:
        scope.enter_active(cmds)
```

Replace (it occurs once):

```python
    if not cmds.namespace(exists=":" + namespace):
        cmds.namespace(addNamespace=namespace)
```

with:

```python
    if not cmds.namespace(exists=":" + namespace):
        cmds.namespace(addNamespace=":" + namespace)
```

- [ ] **Step 3: `SkeldarAnim/maya_uebridge/nativeimport.py`**

Below `import maya.cmds as cmds` (the module's first `cmds` import), add a blank line and `from maya_scenetabs import scope`:

```python
import maya.cmds as cmds

from maya_scenetabs import scope
```

Replace (it occurs once):

```python
    namespaced characters) keep namespaces of their own. Returns a note ("" when every one went)."""
    nested = [n.lstrip(":") for n in
              cmds.namespaceInfo(namespace, listOnlyNamespaces=True, recurse=True) or []]
    flatten = nested if single_chain(namespace, nested) else []
    left = []
    for each in depth_first(flatten + [namespace]):
        each = each.lstrip(":")
        if not cmds.namespace(exists=":" + each):
            continue
        try:
            cmds.namespace(removeNamespace=":" + each, mergeNamespaceWithRoot=True)
```

with:

```python
    namespaced characters) keep namespaces of their own. Returns a note ("" when every one went).
    While scene tabs are on (2026-10-15) the clip first moves under the active tab and merges
    into IT: the root is no tab's."""
    full = scope.home_namespace(namespace, cmds)
    merge = ({"mergeNamespaceWithParent": True} if full != namespace.lstrip(":")
             else {"mergeNamespaceWithRoot": True})
    nested = [n.lstrip(":") for n in
              cmds.namespaceInfo(":" + full, listOnlyNamespaces=True, recurse=True) or []]
    flatten = nested if single_chain(full, nested) else []
    left = []
    for each in depth_first(flatten + [full]):
        each = each.lstrip(":")
        if not cmds.namespace(exists=":" + each):
            continue
        try:
            cmds.namespace(removeNamespace=":" + each, **merge)
```

- [ ] **Step 4: `SkeldarAnim/maya_scenesetup/deletion.py`**

Below `import maya.cmds as cmds` (the module's first `cmds` import), add a blank line and `from maya_scenetabs import scope`:

```python
import maya.cmds as cmds

from maya_scenetabs import scope
```

Replace (it occurs once):

```python
    if current == namespace or current.startswith(namespace + ":"):
        cmds.namespace(setNamespace=":")
```

with:

```python
    if current == namespace or current.startswith(namespace + ":"):
        scope.enter_active(cmds)
```

- [ ] **Step 5: `SkeldarAnim/maya_share.py`**

Below `import maya.cmds as cmds` (the module's first `cmds` import), add a blank line and `from maya_scenetabs import scope`:

```python
import maya.cmds as cmds

from maya_scenetabs import scope
```

Replace (it occurs once):

```python
    if not result.get("nodes"):
        return "{0} brought nothing into the scene.".format(record["name"])
```

with:

```python
    if not result.get("nodes"):
        return "{0} brought nothing into the scene.".format(record["name"])
    scope.home_namespace(namespace, cmds)          # a tab's, while tabs are on
```

- [ ] **Step 6: `SkeldarAnim/maya_stash.py`**

Below `import maya.cmds as cmds` (the module's first `cmds` import), add a blank line and `from maya_scenetabs import scope`:

```python
import maya.cmds as cmds

from maya_scenetabs import scope
```

Replace (it occurs once):

```python
    if not result.get("nodes"):
        return "{0} brought nothing into the scene.".format(name)
```

with:

```python
    if not result.get("nodes"):
        return "{0} brought nothing into the scene.".format(name)
    scope.home_namespace(namespace, cmds)          # a tab's, while tabs are on
```

- [ ] **Step 7: `SkeldarAnim/maya_scenesetup/character.py`**

Below `import maya.cmds as cmds` (the module's first `cmds` import), add a blank line and `from maya_scenetabs import scope`:

```python
import maya.cmds as cmds

from maya_scenetabs import scope
```

Replace (it occurs once):

```python
def existing_namespaces():
    """Every namespace in the scene, nested ones as `a:b`."""
    return cmds.namespaceInfo(":", listOnlyNamespaces=True, recurse=True) or []
```

with:

```python
def existing_namespaces():
    """Every namespace in the scene, nested ones as `a:b` - and, while scene tabs are on
    (2026-10-15), the active tab's own as if they stood at the root: a new character's
    namespace goes into the tab, a clip's to the root, and either must be free."""
    found = list(cmds.namespaceInfo(":", listOnlyNamespaces=True, recurse=True) or [])
    active = scope.active_namespace(cmds)
    if active:
        prefix = active + ":"
        found += [n[len(prefix):] for n in found if n.startswith(prefix)]
    return found
```

Replace (it occurs once):

```python
    before_roots = builder.character_roots()
    new = import_asset(path, namespace or None)
```

with:

```python
    before_roots = builder.character_roots()
    new = import_asset(path, namespace or None)
    if namespace:
        namespace = scope.qualified(namespace, cmds)   # the import went into the active tab
```

Replace (it occurs once):

```python
                         namespace=namespace, selected=selected,
```

with:

```python
                         namespace=scope.relative(namespace, cmds), selected=selected,
```

- [ ] **Step 8: `SkeldarAnim/maya_scenesetup/armor.py`**

Below `import maya.cmds as cmds` (the module's first `cmds` import), add a blank line and `from maya_scenetabs import scope`:

```python
import maya.cmds as cmds

from maya_scenetabs import scope
```

Replace (it occurs once):

```python
    if namespace and cmds.namespace(exists=":" + namespace):
        cmds.namespace(removeNamespace=":" + namespace, deleteNamespaceContent=True)
```

with:

```python
    #  the piece's namespace as it stood when worn: in a scene tab's while tabs are on
    #  (2026-10-15), else at the root
    for name in ([scope.absolute(namespace, cmds), ":" + namespace] if namespace else []):
        if cmds.namespace(exists=name):
            cmds.namespace(removeNamespace=name, deleteNamespaceContent=True)
            break
```

- [ ] **Step 9: `SkeldarAnim/maya_poselib/apply.py`**

Replace (it occurs once):

```python
        root = _long(root_uuid)
    return root, " - ".join([REBUILT % (namespace, x, z)] + notes)
```

with:

```python
        from maya_scenetabs import scope
        scope.home_namespace(namespace, cmds)      # a tab's, while tabs are on (2026-10-15)
        root = _long(root_uuid)
    return root, " - ".join([REBUILT % (namespace, x, z)] + notes)
```

- [ ] **Step 10: Run the unit suite**

Run:

```
$env:QT_QPA_PLATFORM = 'offscreen'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t .
```

Expected: no failure that was not there before this task (on the planning snapshot the whole suite ran with no new failure after this task).

- [ ] **Step 11: Run the proof**

Run:

```
$env:MAYA_APP_DIR = "$env:TEMP\skeldar_tabs_appdir"; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs/superpowers/plans/verify_tabs_scope.py
```

Expected: `8 of 40 gates failed` - still failing (a later task's):

  - add: its character group and layer are in the tab, named as the tab shows them
  - weapon: the line names the character as the tab shows it
  - save: the tab's file holds its rig, every node named without the tab
  - save: the rig's clip label names no tab
  - shared: ran to the end
  - open scene: a weapon's FBX opens in a tab of its own
  - open scene: its model is in that tab
  - open scene: every other tab stays open

«save: the tab's file holds its rig, every node named without the tab» passed after the previous task: the measured intermediate state, put right by a later task - not a reason to stop.

- [ ] **Step 12: Commit**

```bash
cd "/c/!!!Work/MayaScripts"
cat > "$TEMP/scenetabs2_msg.txt" <<'EOF'
feat(scenetabs): the current namespace is the active tab's; kept clips land in it

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git add SkeldarAnim/maya_uebridge/animimport.py SkeldarAnim/maya_uebridge/formats.py SkeldarAnim/maya_uebridge/nativeimport.py SkeldarAnim/maya_scenesetup/deletion.py SkeldarAnim/maya_share.py SkeldarAnim/maya_stash.py SkeldarAnim/maya_scenesetup/character.py SkeldarAnim/maya_scenesetup/armor.py SkeldarAnim/maya_poselib/apply.py
git commit -F "$TEMP/scenetabs2_msg.txt"
```


---

### Task 5: The scene's name, a copy of it, the plugin's own open and new

**Files:**
- Modify: `SkeldarAnim/maya_share.py`
- Modify: `SkeldarAnim/maya_stash.py`
- Modify: `SkeldarAnim/maya_poselib/capture.py`
- Modify: `SkeldarAnim/maya_scenesetup/cliplabel.py`
- Modify: `SkeldarAnim/maya_walk/scene.py`
- Modify: `SkeldarAnim/maya_scenesetup/opener.py`
- Modify: `SkeldarAnim/maya_scenetabs/saving.py`

**Interfaces:**
- Consumes: `maya_scenetabs.scope` (Task 1) - `scene_name(cmds_)`, `export_scene(path, file_type, cmds_)`, `open_scene(path, cmds_, **flags)`, `new_scene(cmds_)`, `tabs_on(cmds_)`.
- Produces: `saving.export_uuids(namespace, references=True)`, `saving.save_tab(namespace=None, path=None, adopt=True, preserve_references=True)`.

**The rule:** while tabs are on the scene the animator works in is the active tab: its file is the scene's name, a copy sent to a colleague is that tab alone with its references written in, and the plugin's own open or new of a scene opens a tab instead of replacing the session.

- [ ] **Step 1: `SkeldarAnim/maya_share.py`**

Replace EVERY occurrence (2) of `cmds.file(query=True, sceneName=True)` with `scope.scene_name(cmds)`.

Replace (it occurs once):

```python
    cmds.file(path, exportAll=True, type=file_type, force=True,
              preserveReferences=False)
    record["bytes"] = os.path.getsize(path)
```

with:

```python
    scope.export_scene(path, file_type, cmds)
    record["bytes"] = os.path.getsize(path)
```

Replace (it occurs once):

```python
    if record["kind"] == "scene":
        cmds.file(path, open=True, force=True, executeScriptNodes=False,
                  ignoreVersion=True, prompt=False)
        _restore_playback()
```

with:

```python
    if record["kind"] == "scene" and scope.tabs_on(cmds):
        #  scene tabs on (2026-10-15): a tab of its own, with its ranges, its vaccine swept
        scope.open_scene(path, cmds)
        return _status("Opened {0} from {1} in a tab".format(
            record["name"], record.get("from") or "someone"))
    if record["kind"] == "scene":
        cmds.file(path, open=True, force=True, executeScriptNodes=False,
                  ignoreVersion=True, prompt=False)
        _restore_playback()
```

Replace (it occurs once):

```python
    cmds.file(new=True, force=True)
    return _status(_import_fbx(path, record, "Opened"))
```

with:

```python
    scope.new_scene(cmds)
    return _status(_import_fbx(path, record, "Opened"))
```

- [ ] **Step 2: `SkeldarAnim/maya_stash.py`**

Replace EVERY occurrence (2) of `cmds.file(query=True, sceneName=True)` with `scope.scene_name(cmds)`.

Replace (it occurs once):

```python
    cmds.file(path, exportAll=True, type=file_type, force=True,
              preserveReferences=False)
    _clear_name()
```

with:

```python
    scope.export_scene(path, file_type, cmds)
    _clear_name()
```

- [ ] **Step 3: `SkeldarAnim/maya_poselib/capture.py`**

Below `import maya.cmds as cmds` (the module's first `cmds` import), add a blank line and `from maya_scenetabs import scope`:

```python
import maya.cmds as cmds

from maya_scenetabs import scope
```

Replace (it occurs once):

```python
    path = cmds.file(query=True, sceneName=True) or ""
```

with:

```python
    path = scope.scene_name(cmds)
```

- [ ] **Step 4: `SkeldarAnim/maya_scenesetup/cliplabel.py`**

Replace (it occurs once):

```python
    scene = cmds.file(query=True, sceneName=True) or ""
    return clip_name_from(
```

with:

```python
    scene = scope.scene_name(cmds)
    return clip_name_from(
```

- [ ] **Step 5: `SkeldarAnim/maya_walk/scene.py`**

Replace (it occurs once):

```python
    scene = os.path.splitext(os.path.basename(cmds.file(query=True, sceneName=True) or ""))[0]
```

with:

```python
    from maya_scenetabs import scope
    scene = os.path.splitext(os.path.basename(scope.scene_name(cmds)))[0]
```

- [ ] **Step 6: `SkeldarAnim/maya_scenesetup/opener.py`**

Below `import maya.cmds as cmds` (the module's first `cmds` import), add a blank line and `from maya_scenetabs import scope`:

```python
import maya.cmds as cmds

from maya_scenetabs import scope
```

Replace (it occurs once):

```python
    if not save_changes():
        return False, ""
    note = ""
    if character.is_fbx(path):
```

with:

```python
    if scope.tabs_on(cmds):
        #  scene tabs on (2026-10-15): the file opens in a tab of its own - nothing is replaced,
        #  so nothing asks to be saved; the shipped images still go on the plugin's copy
        scope.open_scene(path, cmds)
        return True, _clean()
    if not save_changes():
        return False, ""
    note = ""
    if character.is_fbx(path):
```

- [ ] **Step 7: `SkeldarAnim/maya_scenetabs/saving.py`**

Replace (it occurs once):

```python
def export_uuids(namespace):
```

with:

```python
def export_uuids(namespace, references=True):
```

Replace (it occurs once):

```python
    return out + [uid for uid, _ in session.top_references(namespace)]
```

with:

```python
    if not references:
        #  the references written in (stage 2, a copy for a colleague): their nodes, never
        #  their reference nodes, go into the file as plain nodes
        refs = [cmds.referenceQuery(cmds.ls(uid)[0], filename=True)
                for uid, _ in session.top_references(namespace)]
        return out + (cmds.ls([n for f in refs for n in cmds.referenceQuery(f, nodes=True, dagPath=True) or []],
                              uuid=True) or [])
    return out + [uid for uid, _ in session.top_references(namespace)]
```

Replace (it occurs once):

```python
def save_tab(namespace=None, path=None, adopt=True):
```

with:

```python
def save_tab(namespace=None, path=None, adopt=True, preserve_references=True):
```

Replace (it occurs once):

```python
        uuids = export_uuids(namespace)
```

with:

```python
        uuids = export_uuids(namespace, preserve_references)
```

Replace (it occurs once):

```python
        cmds.file(temporary, exportSelected=True, preserveReferences=True, type=records.FILE_TYPES[ext],
```

with:

```python
        cmds.file(temporary, exportSelected=True, preserveReferences=preserve_references,
                  type=records.FILE_TYPES[ext],
```

- [ ] **Step 8: Run the unit suite**

Run:

```
$env:QT_QPA_PLATFORM = 'offscreen'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t .
```

Expected: no failure that was not there before this task (on the planning snapshot the whole suite ran with no new failure after this task).

- [ ] **Step 9: Run the proof**

Run:

```
$env:MAYA_APP_DIR = "$env:TEMP\skeldar_tabs_appdir"; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs/superpowers/plans/verify_tabs_scope.py
```

Expected: `4 of 42 gates failed` - still failing (a later task's):

  - add: its character group and layer are in the tab, named as the tab shows them
  - weapon: the line names the character as the tab shows it
  - save: the tab's file holds its rig, every node named without the tab
  - save: the rig's clip label names no tab

- [ ] **Step 10: Commit**

```bash
cd "/c/!!!Work/MayaScripts"
cat > "$TEMP/scenetabs2_msg.txt" <<'EOF'
feat(scenetabs): the scene's name, a copy and the plugin's own open / new follow the active tab

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git add SkeldarAnim/maya_share.py SkeldarAnim/maya_stash.py SkeldarAnim/maya_poselib/capture.py SkeldarAnim/maya_scenesetup/cliplabel.py SkeldarAnim/maya_walk/scene.py SkeldarAnim/maya_scenesetup/opener.py SkeldarAnim/maya_scenetabs/saving.py
git commit -F "$TEMP/scenetabs2_msg.txt"
```


---

### Task 6: Names as the tab shows them

**Files:**
- Modify: `SkeldarAnim/maya_scenesetup/character.py`
- Modify: `SkeldarAnim/maya_scenesetup/equip.py`
- Modify: `SkeldarAnim/maya_scenesetup/armor.py`
- Modify: `SkeldarAnim/maya_scenesetup/cliplabel.py`

**Interfaces:**
- Consumes: `maya_scenetabs.scope` (Task 1) - `local(path, cmds_)`, `relative(name, cmds_)`.
- Produces: `equip.character_name(root)`, `armor.character_name(root)`, `cliplabel.clip_name_of(source_root)` answer as the tab shows the names.

**The rule:** a name the animator reads - a message's character, a clip label, a character group's base - is read with the tab's prefix taken off. «The outermost namespace» was the tab (measured: «Long Sword 02 into tab_plain's right hand», a clip label «tab_plain»).

- [ ] **Step 1: `SkeldarAnim/maya_scenesetup/character.py`**

Replace (it occurs once):

```python
    return chargroup.make(group_base(entry, namespace), getattr(entry, "label", ""), root, tops)
```

with:

```python
    return chargroup.make(group_base(entry, scope.relative(namespace, cmds)),
                          getattr(entry, "label", ""), root, tops)
```

- [ ] **Step 2: `SkeldarAnim/maya_scenesetup/equip.py`**

Below `import maya.cmds as cmds` (the module's first `cmds` import), add a blank line and `from maya_scenetabs import scope`:

```python
import maya.cmds as cmds

from maya_scenetabs import scope
```

Replace (it occurs once):

```python
    """A rig's namespace, else the root's leaf. Pure."""
    leaf = (root or "").split("|")[-1]
```

with:

```python
    """A rig's namespace, else the root's leaf - as the active scene tab shows it."""
    leaf = scope.local(root or "", cmds).split("|")[-1]
```

- [ ] **Step 3: `SkeldarAnim/maya_scenesetup/armor.py`**

Replace (it occurs once):

```python
    """A rig's namespace, else the root's leaf. Pure."""
    leaf = (root or "").split("|")[-1]
```

with:

```python
    """A rig's namespace, else the root's leaf - as the active scene tab shows it."""
    leaf = scope.local(root or "", cmds).split("|")[-1]
```

- [ ] **Step 4: `SkeldarAnim/maya_scenesetup/cliplabel.py`**

Replace (it occurs once):

```python
    path = _long(source_root) or ""
    parts = [p for p in path.split("|") if p]
```

with:

```python
    path = scope.local(_long(source_root) or "", cmds)
    parts = [p for p in path.split("|") if p]
```

Replace (it occurs once):

```python
        top_is_joint = cmds.objectType("|" + parts[0]) == "joint"
```

with:

```python
        top_is_joint = cmds.objectType(_long(source_root).split("|")[1]) == "joint"
```

- [ ] **Step 5: Run the unit suite**

Run:

```
$env:QT_QPA_PLATFORM = 'offscreen'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t .
```

Expected: no failure that was not there before this task (on the planning snapshot the whole suite ran with no new failure after this task).

- [ ] **Step 6: Run the proof**

Run:

```
$env:MAYA_APP_DIR = "$env:TEMP\skeldar_tabs_appdir"; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs/superpowers/plans/verify_tabs_scope.py
```

Expected: `0 of 42 gates failed`.

- [ ] **Step 7: Commit**

```bash
cd "/c/!!!Work/MayaScripts"
cat > "$TEMP/scenetabs2_msg.txt" <<'EOF'
fix(scenetabs): names in messages and labels as the tab shows them

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git add SkeldarAnim/maya_scenesetup/character.py SkeldarAnim/maya_scenesetup/equip.py SkeldarAnim/maya_scenesetup/armor.py SkeldarAnim/maya_scenesetup/cliplabel.py
git commit -F "$TEMP/scenetabs2_msg.txt"
```


---

### Task 7: The proof together, CLAUDE.md, the hand-over

**Files:**
- Modify: `CLAUDE.md` (the "Scene tabs" section stage 1 added; the traps after stage 1's)

- [ ] **Step 1: Run every proof and the unit suite**

Run:

```
$env:MAYA_APP_DIR = "$env:TEMP\skeldar_tabs_appdir"; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs/superpowers/plans/verify_scene_tabs.py all
$env:MAYA_APP_DIR = "$env:TEMP\skeldar_tabs_appdir"; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs/superpowers/plans/verify_tabs_scope.py
$env:QT_QPA_PLATFORM = 'offscreen'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t .
```

Expected: `0 of 127 gates failed`; `0 of 42 gates failed`; unit tests `OK`. Record the numbers for CLAUDE.md.

- [ ] **Step 2: CLAUDE.md - the stage 2 part of the section**

In the "## Scene tabs: several scenes in one Maya, switched like browser tabs (2026-10-15)" section stage 1 wrote, replace (it occurs once):

```markdown
Stage 2 (the plugin
seeing only the active tab) is `2026-10-15-scene-tabs-plugin-scope-design.md` and is NOT built yet: until it
is, the plugin's tools see every tab's characters.
```

with:

```markdown
Stage 2, the plugin seeing only the active tab, is `2026-10-15-scene-tabs-plugin-scope-design.md` (its
planning addendum), plan `docs/superpowers/plans/2026-10-15-scene-tabs-stage2.md` - built with stage 1: stage 1
alone doubles the tab's prefix on everything the plugin creates.

- **`maya_scenetabs/scope.py`** holds the three rules; with tabs off every function is the identity. **A reader**
  keeps the active tab's paths (`active_only`): `maya_rigs.rigs()`, `builder.character_roots()`,
  `animimport.skeleton_roots()`, the colour scan, the studio, the retargets' joint scans, the CoM groups - and
  everything built on them. **The current namespace is the active tab's**: a reset after an import is
  `enter_active`; a clip is imported into a root-level namespace and, when kept, moved under the tab
  (`home_namespace`). **A name that carries a namespace is made absolute** where a node is created or renamed
  with it (`as_created`), a name given back after a hold is `root_name`; a leaf needs nothing.
- **What the animator reads** is named as the tab shows it (`local`, `relative`): «Manny_Rig's right hand», a
  character group `Manny_Rig_Character`, never `tab_x_...`.
- **The scene is the active tab** for Shared and Stash (a copy of that tab alone, references written in; a
  received scene opens as a tab), Open scene, and the scene's name.
- **A new plugin feature** that lists the scene, creates a node with a namespaced name or names a character in
  a message goes through `scope` - `tests/test_scenetabs_scope.py` and `verify_tabs_scope.py` are the
  reference.
```

- [ ] **Step 3: CLAUDE.md - the traps**

Append after the traps stage 1 added (248-252 when this plan was written; use the next free numbers and keep these in order):

```markdown
253. **Maya resolves a creation or rename name relative to the CURRENT namespace, even when the name carries
     one.** With a tab's namespace current, `createNode(name="tab_x:Rig:Holder")` made
     `tab_x:tab_x:Rig:Holder` and created the missing namespaces silently - the retarget then set an attribute
     on a node that did not exist. Lookups (`ls`, `objExists`) go from the root, so the code read and wrote two
     different nodes. Make a namespaced creation name absolute (`":" + name`); `namespace -add x` adds under the
     current namespace, `-add :x` at the root.
254. **A node made by an absolute name is answered without the leading colon** (`":A:x"` -> `"A:x"`). A fake
     `cmds` that echoes the name it was given answers `":A:x"`, and a test then compares paths Maya never makes.
255. **"The outermost namespace" names the tab.** A message's character (`split(":")[0]`) read «tab_plain's
     right hand» and a clip label «tab_plain» once every node carried the tab's prefix. Read a path the animator
     sees through `scope.local`.
256. **A save renames nodes, not strings.** A camera's `imageName` (`tab_plain:camera2`, the name it was
     created with) and an FBX's display layer (`tab_plain:DeformationJoints`) keep the tab's prefix. Neither
     names a bone; a gate that searches a whole file for the prefix fails on them - gate the node names.
```

- [ ] **Step 4: Commit**

```bash
cd "/c/!!!Work/MayaScripts"
cat > "$TEMP/scenetabs2_msg.txt" <<'EOF'
docs(scenetabs): CLAUDE.md - stage 2, traps 253-256

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git add CLAUDE.md
git commit -F "$TEMP/scenetabs2_msg.txt"
```

- [ ] **Step 5: Hand over**

Do not push, do not build, do not install into the animator's Maya. Report to the animator, together with stage 1's: the commits, the three proofs' numbers, and the live checklist - stage 1's (the bar, layouts, hidden-tab cost, quit dialog, Ctrl+Tab) plus stage 2's: with a hidden tab behind the active one, a drag from the Animation Setup portraits, the UE Bridge list and the inventory onto the viewport (the drop targets are read from the active tab only), and the Retarget button with two rigs in two tabs and nothing selected.
