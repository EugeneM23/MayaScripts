# Moveset: no planning in the card, and Export into a montage slot (2026-10-29)

The animator, the same evening: «Давай пока уберем все возможности задавать исполнителей и статусы
прогресса, но добавим возможность проэкспортировать анимацию сразу в слот монтажа». Asked: the planning
goes **from the card only** — the page keeps its board — and the export **cuts the scene by the slot's
own segments**, the exact inverse of the montage import. Spec of the card:
`2026-10-29-moveset-combo-trees-design.md`; of the weapons: `2026-10-29-moveset-dagger-design.md`.

## What a slot holds, measured

A slot's track is not one animation. Over the two graphs (a node and a view is one row):

| | one whole sequence | several segments | plays a slice | rate ≠ 1 | no track |
|---|---|---|---|---|---|
| Dagger (44) | 25 | 11 (up to 4) | 6 | 0 | 2 |
| Longsword (50) | 19 | 21 (up to 5) | 9 | 1 | 0 |

A segment carries `anim` (the AnimSequence's object path), `start_pos` (where it begins on the montage's
clock), `anim_start` / `anim_end` (the part of the sequence it plays), `rate` and `anim_length`.
**Unreal's import replaces a whole AnimSequence**, so a segment that plays a slice of its sequence
(`AM_Melee_Jump_nomove` takes 0.1–1.5 s of a 1.53 s sequence) cannot be written back without throwing the
rest of that asset away, and a segment at another rate (`AM_Longsword_Attack_Jump_Ascent`, 1.25) cannot be
written back without changing what the montage shows.

## The planning leaves the card

- The cards lose the 3P / 1P status dots, and the right-button menu loses its status and assignee rows
  (it keeps Open and gains Export).
- The **Assignee** dropdown and the assignee filter go, and the subtitle drops «N of M done»: «Dagger -
  22 attacks».
- `model.set_status`, `set_assignee` and `kept`'s `who` go with their tests. `read_state` still reads the
  page's keys the card needs — `custom`, `hidden`, and the chosen weapon — and the card writes only the
  weapon.
- **The page is not touched**: its board, its statuses and its people stay, and what it wrote stays in
  `state.json`.

## Export into a slot

Two buttons beside Open, and the same two rows in the right-button menu: **Export 3P** and **Export 1P**.
One press, for the picked attack and that view:

1. **The plan, before anything is written** (pure, from the graph): the slot's segments, each with the
   scene frames it owns — `start_pos` to `start_pos + (anim_end - anim_start)`, at the scene's frame rate
   — and the package its sequence lives in. The first segment of a slot starts at frame 0, which is where
   the import put it.
2. **The refusals**, by name, touching nothing: a segment playing a slice, a rate other than 1, no track
   for the view, a card of the animator's own, no montage in the graph, no skeleton in the scene to
   export (the bridge's own rule: the selection, else the connected character, else the only one), no
   editor.
3. **One confirm dialog** for the press, naming every sequence it will replace, the skeleton it exports
   and what a replace-import throws away (the asset's own curves — `Pose_*`, `MoveData_*`,
   `DisableLegIK`; trap 40).
4. **Per segment**: the scene's frames of that segment to a temp FBX (`animexport.export_hierarchy(...,
   start=, end=, layout=UNREAL_LAYOUT)`), the uasset's read-only flag cleared as the existing road does,
   and `uescripts.reimport_script` onto that segment's package. A failure stops the press and says which
   sequences were already written — the earlier ones are not rolled back, and the line says so.
5. **The status line** names what went where: «NLt NLt NHd 1P - 3 sequences written: AS_Dg_Atk_NLt_1P
   (frames 0-43), …».

Perforce is not touched, as on the bridge's own «Export to uasset» road; the read-only flag is cleared
and left off, because the file is modified and hiding that would be worse.

### The one thing to measure first

A segment in the middle of a slot owns scene frames that do not start at 0 (say 44–87). Whether Unreal's
replace-import normalises an FBX take that starts at frame 44, or writes a sequence 88 frames long with
the first 44 empty, decides whether the export shifts the keys to 0 before writing. **The build measures
it against the editor on a sandbox copy of a sequence before the feature is called done**; a single-segment
slot (the common case) starts at 0 and is unaffected either way.

## Proof

- Unit tests (at the end, as the animator asked): the plan's frames and packages for a one-segment and a
  four-segment slot; every refusal with nothing written; the confirm's text naming every sequence; the
  press writing each segment's own range; the card without a status dot, an assignee menu row or the done
  count; `set_status` / `set_assignee` gone (a gone-test).
- The measurement above, against the editor, on a duplicated sandbox sequence that is deleted after - the
  animator's own assets are not written to by a verify run.
- **Not seen in a GUI Maya**: the animator's own check, as the card itself was.

## Not built

- Writing back a slice of a sequence, or a segment at another rate (refused by name).
- Creating a new AnimSequence beside the montage (the animator chose to write what the game plays).
- Perforce: the checkouts road stays the UE Bridge card's.
- The montage's own notifies: the scan windows are the montage's, and an exported sequence does not carry
  them.
- The page: it keeps its planning board whole.
