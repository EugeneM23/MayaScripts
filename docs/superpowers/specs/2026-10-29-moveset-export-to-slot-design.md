# Moveset: no planning in the card, and Export into a montage slot (2026-10-29)

The animator, the same evening: «Давай пока уберем все возможности задавать исполнителей и статусы
прогресса, но добавим возможность проэкспортировать анимацию сразу в слот монтажа». Asked: the planning
goes **from the card only** — the page keeps its board — and the export **cuts the scene by the slot's
own segments**, the exact inverse of the montage import. Spec of the card:
`2026-10-29-moveset-combo-trees-design.md`; of the weapons: `2026-10-29-moveset-dagger-design.md`.

## What a slot holds, measured

A slot's track is not one animation — and **several segments are usually one sequence cut into
pieces**, which is how the designers split a section at its hit windows. At rate 1 the pieces play the
sequence straight through and are one writable animation; at another rate they are a hand-made time
warp. Measured over both graphs with the plan's own code (a node and a view is one row):

| | writable | time-warped | plays a slice | no track |
|---|---|---|---|---|
| Longsword (50) | 25 (6 of them several segments) | 19 | 6 | 0 |
| Dagger (44) | 25 | 15 | 2 | 2 |

**No track in either graph plays two different sequences**, and every writable track starts its slot at
frame 0 — so the export always writes ONE sequence, from frame 0.

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

### A piece that does not start the slot is refused, not guessed

A second sequence in one slot would own scene frames that do not start at 0 (say 44–87), and whether
Unreal's replace-import normalises an FBX take that starts at frame 44 — or writes a sequence 88 frames
long with the first 44 empty — is **unmeasured**. Measured instead: **0 of the 50 writable rows need it**
(every writable track is one sequence starting at frame 0). So such a piece is refused by name
(«AS_X starts 1.41 s into the slot - writing a sequence that does not start the slot is not built»)
rather than written wrongly. The editor measurement waits for the day a slot plays two sequences.

## Proof

- `tests/test_moveset_export.py`, 34 tests, the fixtures the animator's own graphs' shapes (the float32
  noise included - `2.0333333015441895` is 61 frames at 30 fps, which is why `TOL` is a ten-thousandth
  of a second): the plan's frames and packages for a one-segment track and for a sequence cut at its hit
  windows (one piece, frames 0-41); the frames following the scene's own rate; every refusal with its own
  wording and nothing written; the confirm naming every asset, its frames and the skeleton; a cancel
  writing nothing; the piece exporting its own range and reimporting its own package; the flag cleared
  after the export and said; a failed export stopping before the flag and the editor; an editor error; a
  dead link; a silent no-op said out loud.
- The card's own tests in `tests/test_moveset_view.py`: the two buttons, the two menu rows under a
  separator with a dimmed row for a view with no slot, the press with nothing picked, and the picked
  attack and its name handed to the export. Gone-tests for the dots, the card's `_set` / `WHO_MENU` and
  the model's `set_status` / `set_assignee`.
- The whole suite: 13340 tests, only the six failures that predate the work.
- The editor measurement is **not needed** (above): every writable track is one sequence from frame 0, so
  a press writes exactly one sequence and nothing is shifted. It waits for the day a slot plays two.
- **Not seen in a GUI Maya**: the two buttons and a real press against the editor are the animator's
  own check, as the card itself was.

## What the build settled

- **Every seam the scene, the editor and the disk come through is in `asks`** (`fps`, `bridge`, `root`,
  `export`, `exists`, `read_only`, `clear`, `confirm`, `run_script`), so the press is tested with neither
  Maya nor Unreal and the module's own import stays stdlib (its Maya halves are lazy, inside the press).
- **One sequence a press, today.** `plan` groups consecutive segments of one sequence into one `Piece`,
  and a second sequence in the slot is refused - so `pieces` is always one. The several-pieces shape (the
  loop, the pluralised line, "already written" on a failure in the middle) is written and tested as the
  pure thing it is, for the day a slot plays two sequences.
- **`maya_uebridge.window.content_dir()`**: one accessor for every road that turns a /Game package into a
  file on disk, the window's own uasset press included.

## Not built

- Writing back a slice of a sequence, or a segment at another rate (refused by name).
- Creating a new AnimSequence beside the montage (the animator chose to write what the game plays).
- Perforce: the checkouts road stays the UE Bridge card's.
- The montage's own notifies: the scan windows are the montage's, and an exported sequence does not carry
  them.
- The page: it keeps its planning board whole.
