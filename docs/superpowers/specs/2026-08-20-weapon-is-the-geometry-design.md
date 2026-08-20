# The weapon is the geometry — design

**Date:** 2026-08-20
**Status:** designed.

## The ask

> «давай сделаем так что бы когджа мы нажимали add и добовлось наше оружиен то
> для оружия не должна создаваться какая-то группа, я хочу анимировать просто
> выделяя геометрию. кроме того давай в скрипте Кроме захардкоженного оружия
> будет строка куда можно вставить ссылку на fbx для подставновки оружия»

Two changes to `maya_scenesetup`:

1. **Add must not build a group.** The animator wants to select the sword in
   the viewport and animate it — one click, one node.
2. **A field for an arbitrary FBX**, beside the hardcoded catalog.

## 1. The carrier goes away

Today `attach.attach` builds an empty transform `<key>_weapon`, parents the
imported model inside it, puts the `mayaWeapon` marker on it and keeps the grip
offsets there. Everything finds the weapon through that marker. The animator
therefore has two nodes for one sword: the group that moves it and the geometry
that draws it — and grabbing the geometry moves nothing, which is the complaint.

**The new rule: the weapon IS the mesh transform.**

After the import, look for the transforms that hold a mesh.

- **Exactly one** — the normal case, and the one the request is about. That
  transform is parented straight into `weapon_r`, takes the marker, is seated
  on the bone by `seat`, and its own `translate`/`rotate` are the grip offsets.
  Whatever else arrived in the file — the empty null an exporter wraps around
  the mesh, which is precisely the "какая-то группа" — is deleted once the mesh
  has been lifted out of it. Only leftover imported **transforms** are deleted:
  the shading network came in with the same import and the mesh still needs it.
- **None, or more than one** — a group is built exactly as before, and the
  status line says why ("2 meshes in the file - kept in a group"). Two meshes
  cannot both be "the node the offsets live on", and one click cannot select
  both; refusing the file outright would be worse than the group the animator
  is trying to be rid of, because it would mean the tool simply does not open
  that model.

Everything downstream keeps working, because the CONCEPT survives: there is
still exactly one marked node per bone, still found by attribute and never by
name. `find_attached` walks the bone's direct transform children; Connect's
`marked_ancestor` walks up from an IK hand control; the offsets are read and
written on the marked node; `remove_attached` deletes it whole.

**Trap 34 stops being reachable in the normal case.** Connect hangs the IK
hands on `attach.model_root(weapon)` and Add Aim builds on the same node —
"the geometry, not our group" — and with a single mesh the marked node and the
geometry are the same node. There is no longer a sibling relationship for a
control to land in.

### Two consequences, stated rather than discovered later

**`seat` now zeroes the artist's authored transform too.** It was the carrier's
job to hold our offsets while the model kept whatever the artist authored; one
node cannot do both. A model whose root arrives rotated will therefore sit
differently than it does today, and the grip has to be dialled once — it is
remembered per weapon in an optionVar, so once is once. This is deliberate: the
alternative is offsets that are not the node's own channels, and then the
fields on screen stop being the truth about the scene.

**`model_root` needs a fix, not just a rename.** It currently answers with the
first CHILD transform that has a mesh under it, and falls back to the node
itself. For a marked node that is already the geometry that fallback is right
only by accident — a mesh the animator parented under the sword by hand would
outrank the sword itself. So `model_root` asks first whether the node directly
holds a mesh shape, and only then looks at its children.

### Naming

Renamed only where the word became a lie: `attach.carrier_name` →
`attach.group_name` (still needed for the fallback), `connect.linked_carrier` →
`connect.linked_weapon`, `connect._is_carrier` → `_is_marked`, and the local
`carrier` variables and docstrings throughout `attach`, `connect`, `aim` and
`window`. `verify_connect_arms.py` and `verify_weapon_aim.py` call
`linked_carrier` and are updated in the same change — a proof script that no
longer imports is not a proof.

Names that were never about the group keep their spelling: `find_attached`,
`remove_attached`, `attach`, `model_root`, `seat`, `read_offsets`,
`write_offsets`, `is_animated`.

## 2. The FBX field

A `textFieldGrp` labelled **FBX** under the dropdown. Non-empty, it wins:

| what | from |
|---|---|
| path | the field |
| key | the file's stem, sanitised to a legal Maya name |
| bone | the dropdown entry's bone |
| scale | **1.0** |
| label | the file's stem |

The key is sanitised because it is not only a string in an attribute: it names
the aim manifest (`RigPicker_aim_<key>` reaches `cmds.sets`) and an optionVar.
A space, a dot or a leading digit there is a future traceback, so every
character outside `[A-Za-z0-9_]` becomes `_` and a leading digit gets an `_`
prefix.

Scale comes from neither the field nor the entry but is fixed at 1.0: a scale
correction is a fact about one known model, and quietly applying the sword's
correction to somebody else's file is a surprise nobody asked for. The bone
DOES come from the dropdown, so a future shield entry on `weapon_l` lets a
custom shield into the left hand with no new control.

Offsets are remembered against the derived key, exactly as for a catalog
weapon. The path itself is remembered in `mayaSceneSetup_custom_fbx`, so it
survives the session. A file that is not on disk gets the existing
`file not found: ...`.

No Browse button: the ask was a field to paste into, and a file dialog is three
lines to add later if the pasting gets old.

## Where the logic lives

Two new pure functions, both testable with no Maya:

- `catalog.entry_for_path(path, bone)` → a `Weapon` with the derived key and
  label, `scale=1.0`. `catalog.py` stays stdlib-only (a subprocess test
  enforces it), and `os.path` is stdlib.
- `window.chosen_entry(field_text, entry)` → which `Weapon` a press uses.
  Whitespace-only text counts as empty, so a stray space cannot silently
  redirect Add at a file called `" "`.

The scene work stays in `attach.attach`, which gains one decision (`mesh
transforms among what arrived`) and loses the unconditional group.

## Proof

Unit tests: the mesh-transform resolution and its fallback, `model_root`
answering the node itself when the node holds the mesh, the key sanitiser
(space, dot, leading digit, unicode), `chosen_entry` in all three states, and
`group_name` under its new name.

`docs/superpowers/plans/verify_weapons.py` gains the gates that matter live and
cannot be faked in a unit test:

1. after Add, the marked node **is** a mesh transform and its parent is
   `weapon_r` — no node of ours in between;
2. nothing left over from the import: the transform count under the bone is 1;
3. the weapon sits exactly on the bone — worst local-matrix element 0
   (trap 32 again, now on the geometry);
4. the offset fields move the thing the animator selects: write a translate,
   measure the MESH moved;
5. Connect still carries the hands when the sword is dragged (the trap-34
   gate, unchanged in form);
6. a custom path through the field attaches and reports its derived key.
