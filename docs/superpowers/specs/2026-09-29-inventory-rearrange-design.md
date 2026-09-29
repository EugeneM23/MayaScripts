# The inventory's grid, rearranged by hand (2026-09-29)

The animator, after the weapon inventory: «Давай сделаем так что бы оружие в инвентаре можно было
перетаскивать по инвентарю». Asked: an item dropped onto another one **swaps with it** when that one
fits where the first came from (over "refuse" and "Diablo 2's pick-up-the-other").

## The rules

- **The grab point stays under the cursor**: pressed on the third cell of a 4-tall sword, the sword
  lands with its third cell under the cursor. The spot is clamped into the grid, so a long item near
  the edge slides in rather than hanging out.
- **A preview while over the grid**: the cells the item would cover lit green (it fits, or it swaps)
  or red (no room); the caption says «move here», «swap with Dagger 01» or «no room».
- **The release** (`maya_invlook.plan_move`, pure):
  - the footprint is free, or only the item's own old cells → **move**;
  - it covers exactly ONE other item, and that item fits at the dragged one's old top-left with
    nothing overlapping → **swap**;
  - anything else (two items under it, the other does not fit back) → nothing, «no room».
- **Remembered** between sessions: the optionVar `skeldarInventoryLayout`, JSON `{key: [col, row]}`.
  Read back through `arrange` (pure): stored spots taken in catalog order while in the grid and not
  overlapping what is already placed; everything else (a new catalog row, a stale or broken record)
  first-fit into the free cells. A bad record never loses an item.
- **Right click on the grid → «Sort the inventory»**: the catalog order packed again (`pack`), and
  remembered.
- Unchanged: a hand slot dropped on the grid takes its weapon off; the grid onto a slot or the
  viewport puts one on. A move in the grid touches nothing in the scene and needs no undo.

## Proof

Unit tests: `plan_move` (move, move over its own cells, swap, two under it, the other not fitting
back, the clamp), `arrange` (stored, overlapping, out of the grid, unknown keys dropped, a new row
placed), the window offscreen on the fake scene (a grid drop moves and remembers, a swap, a refusal
leaves the grid as it was, the preview's colours, Sort). Photographed offscreen mid-drag.
