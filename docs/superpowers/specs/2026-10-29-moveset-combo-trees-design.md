# Moveset: the Longsword combo trees in the hub (2026-10-29)

The animator, with their own moveset page open in the browser: «Перенеси чат в раздел maya script и
адвай сделаем протатип этой таблицы в мая только без трело части». Asked what the card should be,
they answered: it lives **in MayaScripts** (the plugin, not their folder), and it **opens the
animation**, shows the **preview pictures** and shares the **data** with the page. The page's
planning-board half stays out.

## What the page is

Their own tool, `Documents/AtoneExperiments/LongswordMoveset`, never in this repo (its own design and
plan live beside it, `2026-10-21-longsword-moveset-graph-design.md` and `-plan.md`). Two files matter
here, side by side in that folder:

- **`graph.json`**, generated from the open Atone editor (`meta.chooser` the melee chooser table,
  `meta.generated` the stamp) — 25 nodes, 100 edges, 26 entries as it stands:
  - a node: `path` (the montage's object path), `slot` / `slot1p`, `montageLength`, `duration`,
    `segments`, `scans`, `cancels`, `posterTime`;
  - an edge: `from`, `to`, `kind` (`chain`, `release`, `dodge`, `jump`, `sprint`, `fresh`),
    `directions`, `window`;
  - an entry: `situation` (`onfoot`, `sprint_short`, `sprint_long`, `air`, `dodge`, `jumpwindup`,
    `exhausted`, `parry`), `target`, `directions`.
- **`state.json`** — the page's own localStorage, keys `longswordMoveset.*` as raw JSON strings:
  `status`, `assignee`, `people`, `icons`, `custom`, `hidden`.

## The decisions

1. **The data stays the animator's.** The plugin ships code; the folder is an optionVar
   (`skeldarMovesetFolder`), its default `Documents/AtoneExperiments/LongswordMoveset`, changed by the
   card's folder button. Nothing of the moveset is in the payload or in git — not the graph, not the
   previews, not the state.
2. **One layout, the page's.** `model.trees` is a port of the page's own build and place:
   breadth-first, one tree an opener (the graph's `entries`, and in Combos only a `release` out of an
   opener as a «Tap» root), each attack expanded once a tree, a later copy or a loop drawn as a leaf
   link (`repeat`), an edge into another opener as a conversion (`conv`), the page's own px kept
   (`COL` 236, `ROW` 178, card 176 x 160). A tree in Maya is the tree in the browser, card for card.
3. **The state is shared through the FILE, not copied.** The card reads `state.json` (`read_state`,
   every key empty where missing) and writes one key at a time keeping every other key the page wrote
   (`write_state`, atomic through a temp file in the folder, so the page's server never reads half).
   The page gained `serve.py` (`http.server` plus `PUT /state.json`): it reads the file before it
   draws, pushes its changed keys merged into the file, and reloads when another writer changed it;
   the card polls the file's mtime every 1.5 s. Both sides may edit, neither owns the file, and
   neither needs the other running.
4. **Open goes the UE Bridge's montage road, never a road of its own.** A node's `path` gives the
   package and `slot` / `slot1p` the slot, so the press builds a montage record
   (`records.with_slot(AnimRecord(..., kind=MONTAGE), slot)`) and hands it to
   `window._export_from_editor` + `rigimport.import_and_retarget(..., target=)`: onto the selected
   rig, else the only one, a new rig when the scene holds none. Every rule of the montage import is
   the bridge's — the plan's refusals before anything is exported, the slot's cuts, the scan-window
   bookmarks, the timeline — and this card has none of its own. It needs the editor open, as the
   bridge does.
5. **Per VIEW, as the page plans.** 3P and 1P are separate work, so a status and an assignee belong to
   `<node id>|3p` / `|1p` (the page's own `skey`), and the card's dots, menu rows and Open buttons are
   per view too.
6. **Qt over a `cmds` placeholder**, the hub's own pattern (the Animation Setup portraits): the trees
   are a `QGraphicsView` laid over `PLACE` through a `Keeper`, every other control plain `cmds`, so
   the skin, the classic hub and a popup copy all reach them; each copy keeps its own context keyed by
   the resolved placeholder name (`_CARDS`), and its own poll timer.

## The card

Top down: the subtitle (the moveset and what is done: «Longsword - 25 attacks, 0 of 50 done» — a
status a view, so 25 attacks are 50 cards of work) with the folder button; **Opening**
(a tree, else All), **Branches** (`Combos only` / `All transitions`), **Assignee** (`Anyone` /
`Unassigned` / the page's people); the type chips Hold / Light / Sprint / Jump / Dodge; the trees;
**Open 3P** (the one primary) / **Open 1P** / **Fit**; the status line.

- **The filters** are the page's: a type or an assignee keeps a match, its path up to the root and
  everything under it (`model.kept`), the rest dimmed; `Unassigned` means a card with a view nobody
  holds.
- **The mouse** (`view`): the wheel zooms about the cursor (0.2..2.5), a drag on empty space pans, a
  click picks and says what the card is (its slots and length), a double click opens 3P, a double
  click on the 1P dot opens 1P, the right button is Open / status / assignee for both views.
- **A card** carries its type's colour, the preview from `media/<id>.jpg` (`media/1p/<id>.jpg` for the
  1P dot), the 3P and 1P status dots with the assignee's emoji or initials, and the foot's direction
  glyphs; a wire is coloured by the attack's type.

## What a refusal says

- no `graph.json` in the folder: «No graph.json in `<the folder>` - press the folder button and pick
  the moveset folder», and the trees are empty rather than stale;
- a card of the animator's own (`custom-*`): «... is a card of your own - it has no montage»;
- a view the montage has no slot for: «... has no 1P slot»;
- several rigs in the scene: the bridge's own refusal, which names them;
- nothing picked: «Pick an attack in the tree first».

## Proof

- `tests/test_moveset_model.py` and `tests/test_moveset_view.py` (the data and the layout on stdlib
  alone, the view offscreen, the card's presses on the repo's recording fake `cmds`, the montage
  record handed to the bridge); 174 tests with the hub's, and the whole suite is unchanged but for the
  three failures that predate the work (`test_chat_deploy`, `test_scenetabs_leak`,
  `test_timebar_lanes_sync`).
- The handoff to the live modules was then read by hand, since a fake cannot see a wrong signature:
  `AnimRecord`'s field order and `MONTAGE`, `with_slot` keeping the slot in `clip` (which
  `_export_montage` reads before its own dropdown), `_export_from_editor`'s `(ref, fps)`,
  `import_and_retarget`'s signature, `current_rig`'s `(rig, refusal)`, `uelink.UeBridgeError`; and the
  popup copy's scoping, where every bare control name in a callback is mapped by `maya_hubcopy`'s
  wrapper and every name a callback keeps is resolved.
- `docs/superpowers/plans/render_moveset_tree.py` → `moveset_tree.png`.
- **Not seen in a GUI Maya**, and Open not run against the editor: the animator's own check.

## Not built

- the page's planning board (asked out);
- editing the graph here — it is generated from the editor, and the card never writes `graph.json`;
- making or hiding cards — the page's `custom` and `hidden` are read and drawn, never written;
- previews made here (the page's `media/`);
- a second weapon's moveset: one folder, the Longsword's.
