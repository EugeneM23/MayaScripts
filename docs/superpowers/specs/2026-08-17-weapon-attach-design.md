# Weapon attach module — design

**Date:** 2026-08-17
**Status:** designed, not implemented.

## The ask

A window that lists weapon models, and an **Add** button that finds `weapon_r`
in the character's hierarchy and puts the chosen weapon into that bone. The
hierarchy is the one the Rig Picker is bound to. Attachment is a plain DAG
parent for now — no constraint, no rig. Rotation and translation offsets are
adjustable so the grip can be dialled in.

One model is hardcoded to start with:
`C:/!!!Work/Animations/Sources/LongSword_02.fbx`. Measured, that file holds a
single mesh (`LongSwordMesh`) and one material — no joints, no skin, no
animation.

Decided out of scope by the user: a Remove button (removal exists internally,
only to serve replacement), constraints, weapon switching over time, and a
scale field in the UI.

## The skeleton comes from the picker, but the module survives without it

The picker holds its binding in the live window — `PickerWindow._root_uuid`,
resolved on demand by `PickerWindow.bound_root()`. Nothing is persisted, so
there is no file or optionVar to read it out of.

So `maya_overrig.picker_window` gains one module-level function:

```python
def bound_root():
    """The open picker's bound skeleton root, or None."""
```

It walks `QApplication.topLevelWidgets()` for `WINDOW_OBJECT_NAME` — exactly
what `show_picker` already does — and returns that window's `bound_root()`.
This is the whole change to the picker.

The weapon module asks for it and falls back:

1. the picker's bound root, if a picker is open and bound;
2. else the root reachable from the current selection (`naming.find_root`);
3. else the only skeleton in the scene (`naming.find_skeleton_roots`,
   excluding rig-owned joints via `builder.character_roots()` — after a build
   the scene reports a dozen roots and a naive count would refuse to bind,
   which is trap 1 all over again);
4. else nothing, and Add says so.

The decision itself is a pure function over data — `choose_root(picker_root,
selection_roots, scene_roots)` — so it is testable without Maya.

**The bone is resolved inside that root's subtree**, never by a scene-wide
name lookup: `naming.hierarchy_map(root)` keyed by leaf name, with
`naming.detect_prefix` / `strip_prefix` applied the way the picker applies
them. That is what makes namespaces (`hero:weapon_r`), per-joint prefixes and
a second character in the scene non-issues. A scene-wide `cmds.ls("weapon_r")`
would arm whichever character Maya happened to list first.

## What Add does

1. Resolve root → resolve the entry's bone (`weapon_r` for the sword). Missing
   either one is a status-line message, not an exception.
2. Ensure the FBX plugin is loaded (`cmds.loadPlugin("fbxmaya", quiet=True)`)
   — in a fresh Maya it is not, and the import would fail with a message about
   an unknown file type.
3. Delete whatever this module previously attached to that bone (see the
   marker, below). One weapon per bone, by the user's call: live offset fields
   then always have exactly one thing to move, and flipping through models in
   the dropdown is the natural way to try them.
4. Import the file with `cmds.file(i=True, type="FBX", returnNewNodes=True,
   ignoreVersion=True)`.
5. Group the imported top-level transforms under a **carrier** transform named
   `<key>_weapon`, parent the carrier into the bone, zero its `translate` and
   `rotate`, set its `scale` from the entry's multiplier, then write the
   offsets.
6. All of it inside one `undoInfo` chunk, so a single Ctrl+Z removes the whole
   thing.

### `cmds.file`, not `FBXImport`

Trap 22 says the opposite — `cmds.file(i=True, type="FBX")` silently drops
every animation curve, and the UE bridge had to use the plugin's own
`FBXImport`. It does not apply here and the difference is worth stating so the
next reader does not "fix" it: this file has no animation to lose, and we need
to know exactly which nodes appeared, which is what `returnNewNodes` gives and
`FBXImport` cannot report at all. The bridge measures a scene delta instead
because it has no choice; here there is a cheaper, exact answer.

### The marker, not the name

The carrier carries a string attribute `mayaWeapon` holding the catalog key.
Finding what is attached is "a transform child of the bone that has that
attribute" — never a name match. Maya uniquifies imported names
(`LongSword_02_weapon1`), the animator may rename anything, and every previous
module in this repo that identified rig nodes by name paid for it.

## Offsets

Two `floatFieldGrp` rows — Rotate XYZ (degrees) and Translate XYZ (scene
units) — holding the carrier's **local** `rotate` and `translate` under the
bone. They are live: `changeCommand` writes straight into the carrier, so a
typed number turns the sword in the viewport immediately.

- The target of a live edit is resolved the same way as everything else: the
  marked carrier under the current entry's bone. Nothing attached — the write
  is skipped and the status says so; the numbers stay for the next Add.
- Writes are wrapped in `autoKeyframe` off. The carrier has no animation
  curves so autoKey would not fire, but the user works with autoKey ON and
  trap 14 was paid for exactly this class of assumption.
- On opening the window, on switching the entry in the dropdown, and after
  Add, the fields are **read back** from the attached carrier when one exists,
  so the numbers on screen are never a lie about the scene.

**Offsets persist between sessions, per weapon**, in an optionVar
(`mayaWeapons_offset_<key>`, six floats). A grip dialled in once should not be
retyped tomorrow. Switching the dropdown loads that weapon's remembered
numbers into the fields; it does not touch the scene.

Scale is deliberately not in the UI. If the sword arrives at the wrong size,
that is a property of the model, and it belongs in the catalog entry as a
multiplier — not a control the animator re-enters every time.

## Module layout

Root-level package `maya_weapons`, entry point:

```python
import sys; sys.path.append(r"C:/!!!Work/MayaScripts")
import maya_weapons; maya_weapons.show_window()
```

| Module | Responsibility | May import |
|---|---|---|
| `catalog.py` | the weapon table and lookups, pure data | **stdlib only** |
| `skeleton.py` | root choice and bone resolution | `maya.cmds`, `maya_overrig.naming` / `builder` |
| `attach.py` | import, replace, parent, read/write offsets | `maya.cmds` |
| `window.py` | the `cmds` window, offsets, optionVars | `maya.cmds`, the three above |

`__init__.py` resolves `show_window` through `__getattr__`, the way both other
packages here do, so importing the package does not drag Maya in and
`catalog.py` stays testable in plain Python.

The window is plain `maya.cmds` — a dropdown, a button and two float rows need
no Qt, and it matches `maya_uebridge`. Every callback goes through a `_run`
wrapper that puts the traceback on the status line; an exception escaping a UI
callback lands in the Script Editor and the panel just looks dead (trap 20).

A catalog entry is `key`, `label`, `path`, `bone`, `scale`:

```python
Weapon("LongSword_02", "Long Sword 02",
       r"C:/!!!Work/Animations/Sources/LongSword_02.fbx", "weapon_r", 1.0)
```

The target bone lives in the entry rather than in the code, so a shield later
is one line with `weapon_l` and no logic to touch.

## What stays in the scene

Deleting a carrier removes the mesh but leaves its shading nodes behind, as
any Maya delete does. Not chased: shaders are cheap, and a scene-wide shader
sweep is exactly the kind of "helpful" cleanup that eventually deletes
something the animator wanted.

The import runs without a namespace. Names may be uniquified on repeated
imports; since one weapon per bone is enforced, this stays bounded.

## Failure modes, each with its own message

| Situation | Add says |
|---|---|
| no picker, no selection, no single skeleton | `no character - open the picker and Connect, or select a joint` |
| bound root has no `weapon_r` | `<root> has no bone 'weapon_r'` |
| the FBX is missing from disk | `file not found: <path>` |
| the fbxmaya plugin will not load | `FBX plugin is not available` |
| import produced no transforms | `nothing came out of <file>` |

## Testing

Unit tests, in the repo's existing style — a fake `maya.cmds` injected into
`sys.modules` with the module attribute rebound, never a `sys.modules` delete
(that trap is recorded in `CLAUDE.md`):

- `catalog.py` — lookups by key and label; a subprocess test asserting it
  imports with no `maya` and no Qt present, matching `test_bodymap.py`.
- `choose_root` — all four branches, including "two skeletons and no hint"
  returning nothing rather than guessing.
- bone resolution through a prefixed and a namespaced hierarchy map.
- `attach.py` — the pure parts: picking top-level transforms out of an
  imported node list, and finding the marked carrier among a bone's children.

**The real proof is live**, per the standing rule in `CLAUDE.md`:
`docs/superpowers/plans/verify_weapons.py`, run through the command port in
the user's Manny scene, asserting that

1. the carrier ends up a child of the resolved `weapon_r`, marked;
2. its world position matches the bone's when offsets are zero;
3. a non-zero rotate/translate offset moves the mesh by exactly that much in
   the bone's local frame;
4. a second Add leaves exactly one carrier under the bone;
5. moving the arm carries the weapon with it (sample the bone and the mesh
   over several frames and compare world matrices, not orientations — trap
   29's lesson);
6. offsets read back from the scene equal what was written.
