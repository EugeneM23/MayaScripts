# Colour on the shelf — recolour what is selected

2026-09-03, straight after the Viewport Studio work: «добавим давай на полку
скрипт настройки цвета». The colour feature landed earlier the same day
inside Scene Setup, where the swatch means "the colour the next Add will
bring". This puts colour on the shelf as its own button, for the other
half of the job: changing the colour of something that is **already in the
scene**.

`SkeldarAnim/maya_colour.py`, single file, `cmds` only, eighth shelf
button (**Colour**). Proof:
`docs/superpowers/plans/verify_colour_tool.py` — **green live 2026-09-03,
0 of 34 gates failed**. 58 unit tests; 1686 in the suite.

## What it is

A grid of the eight palette colours, a custom swatch, and a **Next free
colour** button. A press paints **the selection**; with nothing paintable
selected it falls back to the character the Rig Picker is connected to,
and refuses if there is nothing there either. A "taken:" line names the
colours the scene already wears, because with eight colours and several
characters, knowing which are gone is most of the choice.

## The decisions

**It holds no colour policy at all.** The palette, which colour is free,
our blinn, who wears it, how a character's meshes are found — every bit of
that stays in `maya_scenesetup.colour`, and this module is a panel over
it. A second copy of "which colour is free" would answer differently from
Scene Setup's swatch within a week. Three unit tests read this module's
own source and assert that neither the palette values, nor a
`free_colour`, nor any `shadingNode`/`forceElement` call appears in it.

**It recolours the selection; Scene Setup's swatch is the colour of the
NEXT Add.** One meaning per control — which was the animator's own ruling
earlier the same day, after trying it the other way round and reversing
it. So the two do not overlap and neither needs to know about the other.

**The target follows the convention the toolset already has**:
the selection, then the connect, then a refusal — the same order
`animimport.choose_target_root` and `skeleton.choose_root` use. Painting
whichever character Maya happened to list first is exactly the silent
wrong answer that convention exists to prevent.

**A bone means the character; anything else holding geometry means that
geometry.** Click any bone and the figure changes colour; click a sword
and the sword does — which is how the weapon tool already thinks ("the
weapon IS the geometry"). **Asking the joint question FIRST is what keeps
those two rules disjoint**: `hand_r` has the sword parented under it, so a
mesh-first rule would resolve a hand-bone click to the sword. A control
curve names neither, and falls through to the connect.

**It climbs to the TOPMOST joint, not the nearest.** The nearest joint
above a hand is the hand; a character is painted whole.

**A marked weapon is not part of its character**, and this is the one real
bug the live run found. `colour.character_meshes` finds a figure's meshes
through the skinCluster **and** a DAG walk, the walk being there on
purpose so that unskinned geometry parented in by hand counts as part of
the figure. A sword in the hand is caught by exactly that walk. Then
`colour.paint` reuses whatever material of ours is already on the shapes —
so the character and the sword end up sharing one material, and **painting
the sword repaints the character**. Measured live: the character went pink
when only the prop was clicked. `without_weapons` drops shapes belonging
to anything carrying `bonedrive.MARKER`, so the sword keeps the colour Add
Weapon gave it. Only MARKED weapons are dropped: an unmarked prop is part
of the figure and travels with it, which the live run gates in both
directions.

Scene Setup's own Recolour button is left exactly as it is. It has the
same property, it has had it since the morning, and changing a button the
animator has been using is not this change's business.

**`refresh` never writes to a colour control.** It fires after every
press, so a write there would discard the colour just dialled into the
custom swatch — the lesson `maya_scenesetup.window` paid for with its own
swatch. It touches the "taken:" line and nothing else, and both a unit
test and a live gate pin it.

**A refusal opens no undo chunk.** Nothing happened, so there is nothing
for a Ctrl+Z to undo, and an empty chunk eats the animator's previous undo
step.

**The material key is a leaf name with the namespace stripped.** It
reaches `cmds.shadingNode(name=...)` through `colour.make_material`, and
`ns:root` is not a legal name component.

## Deliberately not built

An eyedropper (reading a colour off a click), a per-character colour list,
and a "restore the original material" button — that last one was offered
and declined this morning: «нет, красим всегда». Nothing here deletes a
shading node: chasing them is how a tool eventually deletes something the
animator wanted.
