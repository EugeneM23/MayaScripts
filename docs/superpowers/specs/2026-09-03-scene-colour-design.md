# A colour for every character and weapon we put into the scene

2026-09-03. The animator's ask: «нужно добавить опцию выбора цвета для
персонажа и оружия которого мы добавляем в сцену. Я предлагаю при добавлении
в сцену задавать новый материал и назначать ему указаный цвет».

Since 2026-09-01 Add Character can be pressed as many times as you like, and
every press brings the same grey figure. Two Mannys in one scene are
indistinguishable in the viewport — the outliner can tell them apart
(`root` against `Manny_Skeleton_root`) and the eye cannot. That is what the
colour is for, and the animator confirmed it: to tell characters apart, and
to tell a weapon apart from the character holding it.

Not for previz look-development, not for the render. A reference figure that
reads as *that* character.

## What arrives

**One new lambert per press, assigned to every mesh the press brought.**
The animator's own framing, and the choice they confirmed when told what it
costs: Manny's authored materials stop being what you see. Those materials
are not deleted — they stay in the scene, unassigned, and a hand
re-assignment in Hypershade brings the original look back — but nothing in
this tool offers to do it. A checkbox to skip the colouring and a "restore
the original material" button were both offered and declined: «нет, красим
всегда».

So the reference figure is one flat colour from head to foot. That is the
point: at a glance, red Manny and blue Manny.

## Identity by attribute, never by name

The lambert carries a string attribute **`skeldarColour`** holding the owner
key (`Manny`, `UE4_Mannequin`, `LongSword_02`, or a custom FBX's
`catalog.node_key`). Everything that has to find our material later — the
free-colour scan, the live recolour, the verify script — asks for that
attribute.

This is the same schema as `mayaWeapon` on the weapon geometry and
`rigPickerRoot` on the rig manifests, and it is not decoration. Maya
uniquifies `skeldarColour_red` into `skeldarColour_red1` the second time,
the animator may rename anything, and **every tool in this repo that
identified a node by name has paid for it** (OverRig renames, trap 8's
manifest diff, the whole 2026-09-01 active-character rewrite).

The material's NAME still carries the colour name, because a readable
Hypershade costs nothing.

## The palette, and why the free colour is read from the scene

Eight named colours, one per hue stop:

```python
Colour = namedtuple("Colour", "name rgb")

PALETTE = [
    Colour("red",    (0.80, 0.25, 0.22)),
    Colour("orange", (0.90, 0.50, 0.18)),
    Colour("amber",  (0.88, 0.75, 0.20)),
    Colour("green",  (0.35, 0.68, 0.32)),
    Colour("teal",   (0.20, 0.70, 0.68)),
    Colour("blue",   (0.25, 0.52, 0.85)),
    Colour("violet", (0.60, 0.40, 0.82)),
    Colour("pink",   (0.88, 0.48, 0.68)),
]
```

Mid-bright on purpose: none of them is near black, or `character.needs_grey`
would read it as an import that lost its textures and grey it out from
under us on the FBX path; none is Maya's default grey either, so a coloured
character never reads as an uncoloured one.

**`next_colour(used)` is pure** — the first palette entry not among `used`,
and `PALETTE[len(used) % 8]` once all eight are taken, which is
deterministic rather than random. `used` comes from **the scene**: every
material carrying the marker, and the colour it holds. Not from a counter in
an optionVar — a counter is right until the animator opens a different file,
deletes a character, or presses Add in a scene somebody else set up, and
then it hands out a colour that is already on screen. The repo's own rule:
never assume the state a previous run left, re-read it.

Character and weapon **share one palette and one scan**, so a sword added
into a red character's hand comes out orange. Distinguishing them from each
other is half the reason the feature exists.

Colours compare with a tolerance (`same_colour`, 0.01): a colour written as
a float and read back through Maya is not bit-identical, and an exact
compare would report every colour as free.

## Which meshes get painted — three sources, and they are not the same question

| When | Where the meshes come from |
|---|---|
| Add Character | the meshes among the import's own nodes |
| Add (weapon) | `attach.model_root(weapon)` |
| Live recolour | skinned to any joint under the character root, ∪ its DAG descendants |

The first two are exact and need no searching, which is always the better
answer: `character.import_asset` already returns UUID-resolved live paths
(it re-resolves them after `flatten_wrappers`, because re-parenting
invalidates every long path below — trap 16), and the weapon *is* the
geometry.

The third row is the one that needed thought. **Manny's six meshes sit at
world level, not inside the skeleton** — `character.flatten_wrappers`' own
docstring records it, and the UE4 mannequin is flattened to the same shape
on purpose. So a DAG walk down from `root` finds nothing at all, and the
route that works is the **skinCluster**: for every joint under the root,
the skinClusters it drives, and the geometry those deform. Identity by
connection — not by name, not by position in the hierarchy. The DAG
descendants stay in the union for unskinned geometry somebody parented into
the skeleton by hand.

## The swatch means one thing, and it is a property of the scene

Two `colorSliderGrp` rows: one under the Character dropdown, one under the
weapon's grip fields.

**A swatch shows the colour of the thing it is about** — the connected
character, the attached weapon — read back from our material on every
`refresh`, exactly as the Rotate/Translate rows already show the measured
grip. Changing it repaints, immediately, the way typing a grip moves the
sword. With nothing connected it previews the colour the next Add will
bring, and changing it then says there is nothing to repaint, which is what
the grip rows do today (`NOT_ATTACHED`).

**Add never reads the swatch.** It takes the next free palette colour at
press time. This is the one place the design departs from the animator's
literal wording («назначать ему указаный цвет»), and it was put to them as
an either/or with the cost of each spelled out; they chose this one. The
reason it is better: a swatch that both *sets the next add* and *shows the
current character* has to be lying about one of them the moment the two
differ, and this window's standing rule is that the numbers on screen are
never a lie about the scene. With Add on the palette, two characters can
never arrive identical even when nobody touches the control, and choosing a
different colour is one click **after** the press — with the character
visible, which is when a colour choice can actually be judged.

The character swatch acts on the **connected** character, the one the header
already names. Not the last one added: the whole rig, the bridge and Scene
Setup have been scoped to the connected character since 2026-09-01, and a
colour that picked a different one would be the only thing in the window
that did.

## Where it plugs in

`colour.py` is a leaf — `maya.cmds` and stdlib, nothing from this package —
and sits between `catalog` and `character` in the module table.

```
character.add_character(entry, colour=None)   # None -> the next free colour
attach.attach(entry, ..., colour=None)        # same
```

Both existing signatures grow one optional argument, so
`verify_add_character.py`, the tests and every other caller keep working and
start getting a colour. Painting happens inside the undo chunk `attach`
already opens; `add_character` opens one of its own, because create-material
plus assign is two commands and half of that undone is a mesh with no
shader.

`character.grey_black_materials` stays exactly as it is. With a colour
always assigned the greyed material is unassigned and invisible — but it is
a fix to *the asset's own material*, the colour is an *assignment*, and if
anyone ever restores the original assignment by hand they should get grey
rather than pure black. It is live-verified code and removing it buys
nothing.

The status line names the colour: `Manny added - 93 joints, 6 meshes - red`.

## What this does not touch

**The UE export.** `animexport` runs `FBXExportSkins -v false` and
`FBXExportShapes -v false` — bones only — so no material of ours can reach
Unreal down either bridge direction.

**The rig.** A shading assignment is invisible to constraints, skinClusters,
manifests and the picker. Nothing in `maya_overrig` reads a material.

## Testing

Unit (`tests/test_scenesetup_colour.py`, plain Python with the repo's fake
`cmds`): `next_colour` on an empty scene, with some taken, with all eight
taken; `same_colour`'s tolerance; the reuse-ours-versus-create decision; the
status wording. Plus the new argument threaded through
`test_scenesetup_character.py` and the swatch behaviour in
`test_scenesetup_window.py`.

Live (`docs/superpowers/plans/verify_scenesetup_colour.py`), because in this
project unit tests have repeatedly been green while the scene was wrong.
The gates that can actually fail:

1. Two Mannys added one after the other wear **different** materials with
   **different** measured RGB.
2. Every mesh of a character resolves to exactly one of our materials —
   6 of 6 for Manny, 2 of 2 for the mannequin.
3. The character's meshes are found **through the skinCluster**: assert the
   count on Manny, whose meshes are at world level, so a DAG-only
   implementation reports zero and fails here.
4. Live recolour of the connected character changes its material and leaves
   the other character's at **0.000000** unchanged.
5. A weapon added into a coloured character's hand takes a colour distinct
   from that character's.
6. Adding after a delete does not hand out a colour already on screen.
7. The run leaves the scene as it found it — every created node registered
   by UUID as it is created and deleted from that registry (trap 47), the
   frame, the selection and autoKey put back.
