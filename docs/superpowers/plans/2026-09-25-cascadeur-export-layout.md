# Cascadeur Export Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every animation export writes Cascadeur's layout: a Null named for the character, rotated −90° X, over a `root` with no orientation of its own and its translation in Z-up space.

**Architecture:** A new leaf module `maya_uebridge/fbxlayout.py`. Its pure half decides the plan and the name; its scene half is a context manager that re-parents `root` under a temporary wrapper for the length of the export and restores everything by UUID in a `finally`. `animexport.export_hierarchy` wraps its export in it (`layout="cascadeur"`, default; `layout="plain"` is the old file). Add Character tags the root with its catalog key. `export_creep_skeleton_fbx.py` uses the same module.

**Tech Stack:** Maya 2027 `maya.cmds` / `maya.api.OpenMaya`, FBX plugin, stdlib `unittest` under mayapy.

## Global Constraints

- Maya stays **Y-up**. The world pose of every joint must be identical with and without the layout (the verify measures it).
- Wrapper rotation **(−90, 0, 0)** XYZ. Wrapper name = the character's name: the catalog key without a trailing `_Rig` (`Creep`, `Manny`, `UE4_Mannequin`); fallback `Character`.
- `root` under the wrapper: `jointOrient' = jointOrient · W⁻¹`; translation `t' = (x, −z, y)`.
- Nothing about the animator's scene may change after an export: the root's world at sampled frames, its connections, jointOrient, names, no wrapper left.
- No key value is ever edited. Keyed translate goes through temporary nodes; static values are written back.
- Unknown root drivers (pairBlend, expression, other), or a root already under a parent: the plain layout, with a note.
- Tests: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t .` from the repo root (`QT_QPA_PLATFORM=offscreen`).

---

### Task 1: `catalog.export_name`

**Files:**
- Modify: `SkeldarAnim/maya_scenesetup/catalog.py` (after `character_by_key`)
- Test: `tests/test_scenesetup_catalog.py`

**Interfaces:**
- Produces: `catalog.export_name(key: str) -> str`; `catalog.character_keys() -> list[str]`

- [ ] **Step 1: Write the failing test** (append a class to `tests/test_scenesetup_catalog.py`)

```python
class ExportName(unittest.TestCase):
    """2026-09-25: the wrapper over `root` in an exported FBX is named for the
    character («по персонажу») - the rig and the bare skeleton of one character
    give one name."""

    def test_a_rig_key_loses_its_rig_suffix(self):
        self.assertEqual(catalog.export_name("Creep_Rig"), "Creep")
        self.assertEqual(catalog.export_name("Manny_Rig"), "Manny")

    def test_a_skeleton_key_is_its_own_name(self):
        self.assertEqual(catalog.export_name("Creep"), "Creep")
        self.assertEqual(catalog.export_name("UE4_Mannequin"), "UE4_Mannequin")

    def test_every_character_key_is_listed(self):
        self.assertEqual(catalog.character_keys(), [c.key for c in catalog.CHARACTERS])
```

- [ ] **Step 2: Run it — FAIL** (`AttributeError: ... export_name`)

- [ ] **Step 3: Implement** (in `catalog.py`)

```python
def character_keys():
    """Every character's key, in table order."""
    return [entry.key for entry in CHARACTERS]


def export_name(key):
    """The character's name for an exported file's top node (2026-09-25).

    The rig and the bare skeleton of one character are one name: the key
    without a trailing `_Rig` (`Creep_Rig` and `Creep` -> `Creep`).
    """
    return key[:-len("_Rig")] if key.endswith("_Rig") else key
```

- [ ] **Step 4: Run it — PASS**
- [ ] **Step 5: Commit** `feat(catalog): export_name - a character's name for its export wrapper`

---

### Task 2: `fbxlayout` pure half

**Files:**
- Create: `SkeldarAnim/maya_uebridge/fbxlayout.py`
- Test: `tests/test_uebridge_fbxlayout.py`

**Interfaces:**
- Produces:
  - `WRAP_ROTATE = (-90.0, 0.0, 0.0)`, `TAG = "skeldarCharacter"`, `FALLBACK_NAME = "Character"`;
  - `swizzled(t) -> (x, -z, y)`;
  - `jo_after(jo) -> (x, y, z)` degrees;
  - `wrapper_name(tag, namespace, colour_keys, known) -> str`;
  - `layout_plan(parent, kinds) -> (mode, reason)`, where `mode` is `"constrained" | "keyed" | "static" | None` and `kinds` is `{channel: "curve"|"constraint"|"pairBlend"|"other"|None}` over the six translate/rotate channels.

- [ ] **Step 1: Write the failing tests** `tests/test_uebridge_fbxlayout.py`

```python
"""Tests for the Cascadeur export layout's pure half (2026-09-25)."""

import math
import sys
import types
import unittest

try:
    import maya.cmds  # noqa: F401  the real one when mayapy has it
    import maya.api.OpenMaya as om
except ImportError:  # pragma: no cover
    raise unittest.SkipTest("needs maya.api.OpenMaya")

from maya_uebridge import fbxlayout

TR = ("translateX", "translateY", "translateZ")
RO = ("rotateX", "rotateY", "rotateZ")


def kinds(t, r):
    return dict(list(zip(TR, t)) + list(zip(RO, r)))


class Swizzle(unittest.TestCase):

    def test_is_the_translation_in_the_wrappers_space(self):
        """t' = t . W^-1 for W = Rx(-90): the wrapper then puts it back."""
        t = (1.0, 2.0, 3.0)
        w = om.MEulerRotation(*[math.radians(v) for v in fbxlayout.WRAP_ROTATE]).asMatrix()
        back = om.MPoint(*fbxlayout.swizzled(t)) * w
        self.assertLess(max(abs(a - b) for a, b in zip((back.x, back.y, back.z), t)), 1e-12)
        self.assertEqual(fbxlayout.swizzled(t), (1.0, -3.0, 2.0))


class JointOrientAfter(unittest.TestCase):

    def test_our_roots_minus_ninety_becomes_zero(self):
        self.assertLess(max(abs(v) for v in fbxlayout.jo_after((-90.0, 0.0, 0.0))), 1e-9)

    def test_any_orient_keeps_the_world(self):
        """R . JO' . W == R . JO for any JO: the rotate curves need no edit."""
        jo = (12.0, -30.0, 47.0)
        m = lambda e: om.MEulerRotation(*[math.radians(v) for v in e]).asMatrix()
        got = m(fbxlayout.jo_after(jo)) * m(fbxlayout.WRAP_ROTATE)
        self.assertLess(max(abs(a - b) for a, b in zip(list(got), list(m(jo)))), 1e-9)


class WrapperName(unittest.TestCase):
    KNOWN = ["Manny_Rig", "Creep_Rig", "Manny", "Creep", "UE4_Mannequin"]

    def test_the_tag_comes_first(self):
        self.assertEqual(fbxlayout.wrapper_name("Creep", "Manny_Rig", ["Manny_Rig"], self.KNOWN), "Creep")

    def test_a_rig_namespace_without_its_digits(self):
        self.assertEqual(fbxlayout.wrapper_name("", "Creep_Rig1", [], self.KNOWN), "Creep")
        self.assertEqual(fbxlayout.wrapper_name("", "Manny_Rig", [], self.KNOWN), "Manny")

    def test_the_one_character_the_skins_colour_names(self):
        self.assertEqual(fbxlayout.wrapper_name("", "", ["Creep", "Creep_Sword"], self.KNOWN), "Creep")

    def test_two_characters_in_the_colours_is_no_answer(self):
        self.assertEqual(fbxlayout.wrapper_name("", "", ["Creep", "Manny"], self.KNOWN), fbxlayout.FALLBACK_NAME)

    def test_an_unknown_tag_or_namespace_falls_through(self):
        self.assertEqual(fbxlayout.wrapper_name("Goblin", "casc", [], self.KNOWN), fbxlayout.FALLBACK_NAME)


class LayoutPlan(unittest.TestCase):

    def test_the_rigs_constrained_root(self):
        self.assertEqual(fbxlayout.layout_plan("", kinds(["constraint"] * 3, ["constraint"] * 3)),
                         ("constrained", ""))

    def test_a_keyed_root(self):
        self.assertEqual(fbxlayout.layout_plan("", kinds(["curve", None, "curve"], [None, "curve", None])),
                         ("keyed", ""))

    def test_a_root_with_nothing_on_it(self):
        self.assertEqual(fbxlayout.layout_plan("", kinds([None] * 3, [None] * 3)), ("static", ""))

    def test_a_pairblend_is_the_plain_layout(self):
        mode, reason = fbxlayout.layout_plan("", kinds(["pairBlend"] * 3, ["pairBlend"] * 3))
        self.assertIsNone(mode)
        self.assertIn("pairBlend", reason)

    def test_keys_and_a_constraint_together_is_the_plain_layout(self):
        mode, reason = fbxlayout.layout_plan("", kinds(["constraint", "curve", None], [None] * 3))
        self.assertIsNone(mode)

    def test_a_root_under_a_parent_is_the_plain_layout(self):
        mode, reason = fbxlayout.layout_plan("|casc:SKM_Manny_Simple", kinds([None] * 3, [None] * 3))
        self.assertIsNone(mode)
        self.assertIn("SKM_Manny_Simple", reason)
```

- [ ] **Step 2: Run — FAIL** (`ImportError: cannot import name 'fbxlayout'`)

- [ ] **Step 3: Implement the pure half** `SkeldarAnim/maya_uebridge/fbxlayout.py`

```python
"""Export in Cascadeur's layout: a Null named for the character over `root`, `root` at zero.

2026-09-25. The animator moves animation Maya <-> Cascadeur and chose one layout for every export,
Cascadeur's own. Cascadeur writes a Y-up file whose skeleton hangs under a Null (named for the
character) rotated -90 deg X, `root` beneath it with no orientation and its translation in the
Null's Z-up space. We keep that turn on `root`'s jointOrient in the scene, so for the length of
an export `root` is re-parented under a temporary wrapper and given `jointOrient . W^-1`
(zero for our usual -90 X) and `t . W^-1` = (x, -z, y), then everything goes back.
The world pose of every joint never changes. Spec:
docs/superpowers/specs/2026-09-25-cascadeur-export-layout-design.md
"""
import contextlib
import math
import re

import maya.cmds as cmds


def _om():
    # lazy: the bridge's tests install a fake `maya` with no `api` (trap 60's family)
    import maya.api.OpenMaya as om
    return om

WRAP_ROTATE = (-90.0, 0.0, 0.0)
TAG = "skeldarCharacter"            # the catalog key Add Character writes on a root
COLOUR_MARKER = "skeldarColour"     # maya_scenesetup.colour.MARKER: its value is the owner's key
FALLBACK_NAME = "Character"
HOLD_PREFIX = "rpHold_"
TRANSLATE = ("translateX", "translateY", "translateZ")
ROTATE = ("rotateX", "rotateY", "rotateZ")


# ------------------------------------------------------------------ pure

def swizzled(t):
    """`t` in the wrapper's space: t . W^-1 for W = Rx(-90), i.e. (x, -z, y)."""
    return (t[0], -t[2], t[1])


def _euler_matrix(degrees):
    return _om().MEulerRotation(*[math.radians(v) for v in degrees]).asMatrix()


def jo_after(jo):
    """The jointOrient that keeps `root`'s world under the wrapper: JO . W^-1 (XYZ, degrees).

    A joint's world is R . JO . parent (row vectors); with the parent now W, R . JO' . W equals
    R . JO exactly, so the rotate channels -- keyed or driven -- need nothing.
    """
    om = _om()
    m = _euler_matrix(jo) * _euler_matrix(WRAP_ROTATE).inverse()
    e = om.MTransformationMatrix(m).rotation(asQuaternion=False).reorder(om.MEulerRotation.kXYZ)
    return tuple(math.degrees(v) for v in (e.x, e.y, e.z))


def wrapper_name(tag, namespace, colour_keys, known):
    """The character's name for the wrapper: the root's tag, its rig namespace without digits,
    the one character its skins' colour names, else FALLBACK_NAME. Pure."""
    from maya_scenesetup.catalog import export_name
    if tag and tag in known:
        return export_name(tag)
    base = re.sub(r"\d+$", "", namespace or "")
    if base and base in known:
        return export_name(base)
    owners = sorted(set(k for k in colour_keys if k in known))
    if len(owners) == 1:
        return export_name(owners[0])
    return FALLBACK_NAME


def layout_plan(parent, kinds):
    """How `root` goes under the wrapper, as (mode, reason). Pure.

    constrained -- every channel a constraint's: it re-solves under the new parent by itself;
    keyed       -- curves or nothing: translate routed through a swizzle, rotate untouched;
    static      -- nothing at all: the translate values rewritten and written back;
    None        -- anything else, and the reason (the plain layout is exported instead).
    """
    if parent:
        return None, "root stands under %s - exported in the plain layout" % parent.split("|")[-1]
    odd = sorted(set(k for k in kinds.values() if k not in (None, "curve", "constraint")))
    if odd:
        return None, "root is driven by %s - exported in the plain layout" % ", ".join(odd)
    present = set(k for k in kinds.values() if k)
    if present == {"constraint"}:
        return "constrained", ""
    if "constraint" in present:
        return None, "root mixes keys and a constraint - exported in the plain layout"
    return ("keyed" if present else "static"), ""
```

- [ ] **Step 4: Run — PASS**
- [ ] **Step 5: Commit** `feat(bridge): fbxlayout - Cascadeur's export layout, the pure half`

---

### Task 3: `fbxlayout` scene half — `character_name`, `root_state`, `wrapped`

**Files:**
- Modify: `SkeldarAnim/maya_uebridge/fbxlayout.py`
- Test: `tests/test_uebridge_fbxlayout.py` (source-level checks; the behaviour is proven by the Task 7 verify)

**Interfaces:**
- Produces:
  - `character_name(root) -> str`
  - `root_state(root) -> (parent, kinds)`
  - context manager `wrapped(root, name)` yielding `(wrapper_long_path or None, note)`
  - context manager `unwrapped()` yielding `(None, "")`

- [ ] **Step 1: Write the failing source tests** (append)

```python
class SceneHalf(unittest.TestCase):
    """The surgery is proven in a live scene (verify_cascadeur_layout.py); these pin the rules
    the design rests on."""

    def source(self, fn):
        import inspect
        return inspect.getsource(fn)

    def test_root_goes_under_the_wrapper_without_compensation(self):
        self.assertIn("relative=True", self.source(fbxlayout.wrapped))

    def test_everything_is_found_again_by_uuid_in_the_finally(self):
        text = self.source(fbxlayout.wrapped)
        self.assertIn("finally:", text)
        self.assertIn("uuid=True", text)

    def test_no_key_is_ever_edited(self):
        text = self.source(fbxlayout.wrapped) + self.source(fbxlayout._route_translate)
        for forbidden in ("keyframe(", "scaleKey", "setKeyframe", "cutKey"):
            self.assertNotIn(forbidden, text)

    def test_the_name_is_freed_and_checked(self):
        text = self.source(fbxlayout.wrapped)
        self.assertIn("HOLD_PREFIX", text)
        self.assertIn("!= name", text)
```

- [ ] **Step 2: Run — FAIL** (`AttributeError: wrapped`)

- [ ] **Step 3: Implement** (append to `fbxlayout.py`)

```python
# ------------------------------------------------------------------ scene

def _kind(plug):
    src = cmds.listConnections(plug, source=True, destination=False, skipConversionNodes=True) or []
    if not src:
        return None
    t = cmds.nodeType(src[0])
    if t.startswith("animCurve"):
        return "curve"
    if t.endswith("Constraint"):
        return "constraint"
    return "pairBlend" if t == "pairBlend" else "other"


def root_state(root):
    """(parent long path or "", {channel: kind}) for `root`."""
    parent = (cmds.listRelatives(root, parent=True, fullPath=True) or [""])[0]
    return parent, dict((c, _kind(root + "." + c)) for c in TRANSLATE + ROTATE)


def _colour_keys(root):
    joints = [root] + (cmds.listRelatives(root, allDescendents=True, type="joint", fullPath=True) or [])
    keys = set()
    skins = set()
    for j in joints:
        skins.update(cmds.listConnections(j + ".worldMatrix", type="skinCluster") or [])
    for sc in skins:
        for shape in cmds.skinCluster(sc, query=True, geometry=True) or []:
            for sg in cmds.listConnections(shape, type="shadingEngine") or []:
                for mat in cmds.listConnections(sg + ".surfaceShader") or []:
                    if cmds.attributeQuery(COLOUR_MARKER, node=mat, exists=True):
                        keys.add(cmds.getAttr(mat + "." + COLOUR_MARKER) or "")
    return sorted(keys)


def character_name(root):
    """The wrapper's name for `root` (read BEFORE any rename: the namespace is a clue)."""
    try:
        from maya_scenesetup import catalog
        known = catalog.character_keys()
    except Exception:
        known = []
    tag = cmds.getAttr(root + "." + TAG) if cmds.attributeQuery(TAG, node=root, exists=True) else ""
    leaf = root.split("|")[-1]
    namespace = leaf.rsplit(":", 1)[0] if ":" in leaf else ""
    return wrapper_name(tag or "", namespace, _colour_keys(root), known)


@contextlib.contextmanager
def unwrapped():
    yield None, ""


def _set_locked(plug, value):
    locked = cmds.getAttr(plug, lock=True)
    if locked:
        cmds.setAttr(plug, lock=False)
    cmds.setAttr(plug, *value, type="double3") if isinstance(value, tuple) else cmds.setAttr(plug, value)
    if locked:
        cmds.setAttr(plug, lock=True)


def _route_translate(root, mode):
    """Put `root`'s translate into the wrapper's space; returns the undo record."""
    record = {"sources": {}, "values": {}, "nodes": []}
    before = set(cmds.ls(type="unitConversion") or [])
    for c in TRANSLATE:
        plug = root + "." + c
        src = cmds.listConnections(plug, source=True, destination=False, plugs=True) or []
        record["sources"][c] = src[0] if src else None
        record["values"][c] = cmds.getAttr(plug)
        if src:
            cmds.disconnectAttr(src[0], plug)
    x, y, z = (record["values"][c] for c in TRANSLATE)
    new_values = swizzled((x, y, z))
    # target channel <- (source channel, sign): x' = x, y' = -z, z' = y
    for target, (source, sign), value in zip(TRANSLATE, (("translateX", 1), ("translateZ", -1), ("translateY", 1)),
                                             new_values):
        src = record["sources"][source]
        plug = root + "." + target
        if src is None:
            _set_locked(plug, value)
        elif sign == 1:
            cmds.connectAttr(src, plug, force=True)
        else:
            neg = cmds.createNode("multDoubleLinear", name="cascadeurLayoutNegate")
            cmds.setAttr(neg + ".input2", -1.0)
            cmds.connectAttr(src, neg + ".input1", force=True)
            cmds.connectAttr(neg + ".output", plug, force=True)
            record["nodes"].append(neg)
    record["nodes"] += [n for n in cmds.ls(type="unitConversion") or [] if n not in before]
    return record


def _unroute_translate(root, record):
    for c in TRANSLATE:
        plug = root + "." + c
        for src in cmds.listConnections(plug, source=True, destination=False, plugs=True) or []:
            cmds.disconnectAttr(src, plug)
    for node in record["nodes"]:
        if cmds.objExists(node):
            cmds.delete(node)
    for c in TRANSLATE:
        plug = root + "." + c
        if record["sources"][c]:
            cmds.connectAttr(record["sources"][c], plug, force=True)
        else:
            _set_locked(plug, record["values"][c])


@contextlib.contextmanager
def wrapped(root, name):
    """For the length of the block, `root` stands under a Null `name` rotated WRAP_ROTATE.

    Yields (wrapper long path, "") -- or (None, reason) when the root's drivers are not ones this
    can move without editing a key; nothing is touched then. Everything is put back in a
    `finally`, found again by UUID.
    """
    parent, kinds = root_state(root)
    mode, reason = layout_plan(parent, kinds)
    if mode is None:
        yield None, reason
        return
    root_uuid = cmds.ls(root, uuid=True)[0]
    held, wrapper_uuid, jo, record, parented = [], None, None, None, False
    try:
        for node in cmds.ls(":" + name, long=True) or []:
            uuid = cmds.ls(node, uuid=True)[0]
            cmds.rename(node, HOLD_PREFIX + name)
            held.append((uuid, name))
        wrapper = cmds.createNode("transform", name=":" + name)
        wrapper_uuid = cmds.ls(wrapper, uuid=True)[0]
        if wrapper.split("|")[-1] != name:
            yield None, "could not name the wrapper %s (Maya gave %s) - exported in the plain layout" % (name, wrapper)
            return
        cmds.setAttr(wrapper + ".rotate", *WRAP_ROTATE, type="double3")
        now = cmds.ls(root_uuid, long=True)[0]
        cmds.parent(now, wrapper, relative=True)
        parented = True
        now = cmds.ls(root_uuid, long=True)[0]
        jo = tuple(cmds.getAttr(now + ".jointOrient")[0])
        _set_locked(now + ".jointOrient", jo_after(jo))
        if mode in ("keyed", "static"):
            record = _route_translate(now, mode)
        yield cmds.ls(wrapper_uuid, long=True)[0], ""
    finally:
        now = (cmds.ls(root_uuid, long=True) or [None])[0]
        if now and record is not None:
            _unroute_translate(now, record)
        if now and jo is not None:
            _set_locked(now + ".jointOrient", jo)
        if now and parented:
            cmds.parent(now, world=True, relative=True)
        for path in (cmds.ls(wrapper_uuid, long=True) or []) if wrapper_uuid else []:
            cmds.delete(path)
        for uuid, original in held:
            for path in cmds.ls(uuid, long=True) or []:
                cmds.rename(path, original)
```

- [ ] **Step 4: Run — PASS** (all of `tests/test_uebridge_fbxlayout.py`)
- [ ] **Step 5: Commit** `feat(bridge): fbxlayout - the wrapper for the length of an export, put back by UUID`

---

### Task 4: `animexport.export_hierarchy(layout=...)`

**Files:**
- Modify: `SkeldarAnim/maya_uebridge/animexport.py` (`export_hierarchy`)
- Test: `tests/test_uebridge_export.py`

**Interfaces:**
- Consumes: `fbxlayout.character_name`, `fbxlayout.wrapped`, `fbxlayout.unwrapped`
- Produces: `export_hierarchy(fbx_path, root=None, start=None, end=None, layout="cascadeur")`; the returned dict gains `"layout"` (`"cascadeur"` or `"plain"`) and `"wrapper"` (the name, or `""`); a refusal's reason is appended to `notes`. `animexport.LAYOUT = "cascadeur"`.

- [ ] **Step 1: Write the failing test** (append to `tests/test_uebridge_export.py`)

```python
class CascadeurLayout(unittest.TestCase):
    """2026-09-25: every export writes Cascadeur's layout unless asked for the plain one."""

    def test_the_default_layout_is_cascadeurs(self):
        import inspect
        self.assertEqual(animexport.LAYOUT, "cascadeur")
        self.assertEqual(inspect.signature(animexport.export_hierarchy).parameters["layout"].default, "cascadeur")

    def test_the_name_is_read_before_the_plain_rename_and_the_wrapper_is_selected(self):
        import inspect
        source = inspect.getsource(animexport.export_hierarchy)
        self.assertLess(source.index("character_name("), source.index("target_plain_names("))
        self.assertIn("fbxlayout.wrapped(", source)
        self.assertIn("[wrapper]", source)
```

- [ ] **Step 2: Run — FAIL** (`AttributeError: LAYOUT`)

- [ ] **Step 3: Implement** in `animexport.py`: `from maya_uebridge import animimport, fbxlayout` beside the existing import; `LAYOUT = "cascadeur"` below `_EXPORT_OPTIONS`; in `export_hierarchy`:

```python
def export_hierarchy(fbx_path, root=None, start=None, end=None, layout=LAYOUT):
    ...
    root_uuid = (cmds.ls(root, uuid=True) or [None])[0]
    joint_ids = cmds.ls(joints, uuid=True) or []
    exported_as = leaf
    # Cascadeur's layout (2026-09-25): the wrapper's name comes from the root's tag or its rig
    # namespace, so it is read now, before the plain-name rename strips the namespace.
    name = fbxlayout.character_name(root) if layout == "cascadeur" else ""
    wrapper_used = ""
    try:
        with animimport.target_plain_names(root, joints) as took:
            exported_as = took or leaf
            bones = cmds.ls(joint_ids, long=True) or []
            ...
            root_now = (cmds.ls(root_uuid, long=True) or [root])[0] if root_uuid else root
            manager = fbxlayout.wrapped(root_now, name) if name else fbxlayout.unwrapped()
            with manager as (wrapper, layout_note):
                if layout_note:
                    notes.append(layout_note)
                bones = cmds.ls(joint_ids, long=True) or bones
                cmds.select(bones + ([wrapper] if wrapper else []), replace=True)
                mel.eval(export_command(fbx_path))
                wrapper_used = name if wrapper else ""
    finally:
        ...
    return {..., "layout": "cascadeur" if wrapper_used else "plain", "wrapper": wrapper_used}
```

(The existing `bones` fallback lines stay as they are, inside the `with target_plain_names`, before `root_now`.)

- [ ] **Step 4: Run — PASS**, then the whole suite.
- [ ] **Step 5: Commit** `feat(bridge): every export writes Cascadeur's layout (layout="plain" for the old file)`

---

### Task 5: Add Character tags the root

**Files:**
- Modify: `SkeldarAnim/maya_scenesetup/character.py` (`add_character`, after `root = new_root(...)`)
- Test: `tests/test_scenesetup_character.py`

**Interfaces:**
- Produces: the new character's skeleton root carries string attribute `skeldarCharacter` = `entry.key` (for a rig: its game skeleton's root, found by `maya_rigs.find(namespace).skeleton_root`).

- [ ] **Step 1: Failing test** (append)

```python
class TagsItsRoot(unittest.TestCase):
    """2026-09-25: the export names its wrapper for the character, and a bare skeleton's
    plain names say nothing about which one it is -- Add Character writes the key."""

    def test_add_character_writes_the_key_on_the_root(self):
        import inspect
        source = inspect.getsource(character.add_character)
        self.assertIn("tag_root(", source)

    def test_tag_root_writes_a_string_attribute(self):
        calls = []

        class Fake(object):
            def objExists(self, n):
                return True

            def attributeQuery(self, a, node=None, exists=False):
                return False

            def addAttr(self, n, longName=None, dataType=None):
                calls.append(("add", n, longName, dataType))

            def setAttr(self, plug, value, type=None):
                calls.append(("set", plug, value, type))

        real = character.cmds
        character.cmds = Fake()
        try:
            character.tag_root("|root", "Creep")
        finally:
            character.cmds = real
        self.assertEqual(calls, [("add", "|root", "skeldarCharacter", "string"),
                                 ("set", "|root.skeldarCharacter", "Creep", "string")])
```

- [ ] **Step 2: Run — FAIL**
- [ ] **Step 3: Implement** in `character.py`:

```python
CHARACTER_TAG = "skeldarCharacter"      # read by maya_uebridge.fbxlayout (the export's wrapper name)


def tag_root(root, key):
    """The catalog key on a character's skeleton root (2026-09-25)."""
    if not root or not cmds.objExists(root):
        return
    if not cmds.attributeQuery(CHARACTER_TAG, node=root, exists=True):
        cmds.addAttr(root, longName=CHARACTER_TAG, dataType="string")
    cmds.setAttr(root + "." + CHARACTER_TAG, key, type="string")
```

and in `add_character`, after `root = new_root(...)`:

```python
    skeleton_root = root
    if namespace:
        import maya_rigs
        rig = maya_rigs.find(namespace)
        skeleton_root = rig.skeleton_root if rig else None
    tag_root(skeleton_root, entry.key)
```

- [ ] **Step 4: Run — PASS**, whole suite.
- [ ] **Step 5: Commit** `feat(characters): Add Character writes the catalog key on the skeleton root`

---

### Task 6: the Creep skeletal-mesh FBX in the layout

**Files:**
- Modify: `docs/superpowers/plans/export_creep_skeleton_fbx.py`

- [ ] **Step 1:** after the colour-marker removal, before the export:

```python
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "..", "SkeldarAnim")))
from maya_uebridge import fbxlayout
# Cascadeur's layout (2026-09-25): the meshes at world level beside the skeleton, the skeleton
# under a Null named for the character -- the |Creep group would take the wrapper's name
for m in MESHES:
    tr = cmds.ls(m, type="transform", long=True)[0]
    if cmds.listRelatives(tr, parent=True):
        cmds.parent(tr, world=True)
if cmds.objExists("|Creep") and not cmds.listRelatives("|Creep", children=True):
    cmds.delete("|Creep")
```

and the export inside `with fbxlayout.wrapped("|root", "Creep") as (wrapper, note):` with `assert wrapper, note` and `cmds.select([wrapper] + [cmds.ls(m, type="transform", long=True)[0] for m in MESHES], replace=True)` (IncludeChildren stays on here: the skeleton rides under the wrapper). The read-back gains: `assert cmds.listRelatives(cmds.ls("root", type="joint", long=True)[0], parent=True) == ["Creep"]`.
- [ ] **Step 2:** run `mayapy docs/superpowers/plans/export_creep_skeleton_fbx.py --overwrite` — expected `OK`, smoothing read back equal, root under `Creep`.
- [ ] **Step 3:** dump the header with the scratch `fbx_axes.py`: `Creep Null R [-90, 0, 0]`, `root PreR [0,0,0]`.
- [ ] **Step 4: Commit** `feat(creep): the skeletal-mesh FBX in Cascadeur's layout`

---

### Task 7: `verify_cascadeur_layout.py` (standalone)

**Files:**
- Create: `docs/superpowers/plans/verify_cascadeur_layout.py`

Gates (each prints PASS/FAIL, `RESULT: n of N`):

| Gate | What it checks |
|---|---|
| 1 | Creep_Rig on `creep_attack_forward.fbx` (as in the scratch `cascadeur_probe.py`) → `export_hierarchy` → `layout == "cascadeur"`, `wrapper == "Creep"` |
| 2 | The file: top Null `Creep` R (−90, 0, 0); `root` PreR ≈ 0; read back beside Cascadeur's own file, `root` LOCAL translation and rotation equal Cascadeur's per frame (≤1e-3 cm, ≤0.01°) |
| 3 | Every other bone's world equal (≤0.001°, twists excepted as measured before) |
| 4 | Scene restored: root world at 5 frames equal to before (≤1e-9), `jointOrient` back, root at world level, no node named `Creep` created, root connections identical |
| 5 | Bare Creep skeleton (Add Character "Creep [skeleton]"), root keyed in translate X/Z and rotate; the `\|Creep` group holds the name → the file's wrapper named exactly `Creep`, root world in the file equal to the scene's per frame; the group back with its name |
| 6 | The same skeleton unkeyed (static) → the layout, the scene restored |
| 7 | Manny_Rig → `wrapper == "Manny"` |
| 8 | A pairBlend on root (key + constraint on translateX) → `layout == "plain"`, a note naming pairBlend, nothing changed |
| 9 | `layout="plain"` writes the old file (root PreR −90, no wrapper) |

- [ ] **Step 1:** write the script (built from `cascadeur_probe.py` / `cascadeur_compare.py` in the scratchpad, with the gates above).
- [ ] **Step 2:** run it: `mayapy docs/superpowers/plans/verify_cascadeur_layout.py "C:/Users/MY PC/Downloads/creep_attack_forward.fbx"`. Expected `RESULT: 0 of 9 gates failed`.
- [ ] **Step 3: Commit** `test(verify): the Cascadeur layout, standalone`

---

### Task 8: the Unreal sandbox round trip

**Files:**
- Create: `docs/superpowers/plans/verify_cascadeur_layout_unreal.py`

In mayapy standalone, the editor reached through `uelink` (pattern: `verify_uebridge_uasset.py`):
1. discover the Atone editor;
2. duplicate one Manny-skeleton AnimSequence from the cache into `/Game/__bridge_verify`;
3. export it out of Unreal (`uescripts` export script), import onto a fresh Manny_Rig, retarget, `export_hierarchy(layout="cascadeur")`;
4. reimport that FBX into the sandbox asset (`uescripts.reimport_script`, Interchange flag handled as in the bridge);
5. export the sandbox asset back out, import it into a fresh scene beside our file;
6. compare every bone's world per frame (≤0.01 cm, ≤0.01°) and root motion;
7. read `Saved/Logs/Atone.log` since the start for `bone` / `skeleton` warnings naming `Manny`;
8. delete the sandbox.

- [ ] **Step 1:** write it.
- [ ] **Step 2:** run. If it passes, keep the default everywhere. If Unreal misreads the wrapper, set `layout="plain"` in `uassetexport.py` and `checkouts.py` calls, and re-run the unit suite.
- [ ] **Step 3: Commit** `test(verify): the Cascadeur layout through Unreal's own import`

---

### Task 9: docs, install, report

- [ ] CLAUDE.md: a section "Exports in Cascadeur's layout (2026-09-25)" (the measurements, the design, the proofs, the `FBXExportUpAxis z` trap as trap 81, the twist note), the bridge module table row for `fbxlayout.py`.
- [ ] Refresh the installed copy in the animator's Maya (`install.install(quiet=True)` over port 7001).
- [ ] Commit `docs: exports in Cascadeur's layout`.
- [ ] Report to the animator: the one Cascadeur check left to them (import one exported file onto their Creep in Cascadeur).
