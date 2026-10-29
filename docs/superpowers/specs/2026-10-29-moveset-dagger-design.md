# Moveset: the Dagger beside the Longsword, and a weapon chooser (2026-10-29)

The animator, the day the Moveset card landed: «Давай теперь дагер сделаем точно также и добавим
возможность выбирать между мечем и дагером». Asked, they chose: **the graph now, the previews later**;
the dagger's files **beside** the sword's, nothing of the sword moved; the chooser **in the card and on
the page**, both showing one weapon at a time; the dagger's cards labelled **as the project names
them**. Spec of the card itself:
`docs/superpowers/specs/2026-10-29-moveset-combo-trees-design.md`.

## What the dagger is, measured

- **21 montages** `AM_Dg_Atk_*` in `Content/Prototype/Animation/PlayerCharacter/Weapons/Dagger/` — a
  flat folder, the `AS_Dg_Atk_*_1P/_3P` sequences beside them; the sword has 39 in its own `Montages`
  subfolder.
- **Its own chooser**, `CHT_DG_MeleeAttack`, with five sub-tables (`CHT_DG_LLt_LHd`,
  `CHT_DG_NLt_NLt_NHd`, `CHT_DG_RLt_RHd`, `CHT_DG_JA_Cmb`, `CHT_Dagger_JumpAscent_Pair`).
- **`DA_Resources_Dagger` names it exactly as the sword's preset names the sword's** — the same
  `Resource.Chooser.MeleeAttack` row (read out of both uassets). Their extractor never hardcodes the
  chooser: it loads the resources preset and reads that row. So the dagger needs the preset swapped,
  not a second extractor.
- **A different naming scheme**: the direction is a letter (`F`, `B`, `L`, `R`, `N`) and the type an
  abbreviation (`Lt` light, `Hd` hold), plus `Spr` and `JA_*` — `AM_Dg_Atk_NLt_NLt_NHd` against the
  sword's `AM_Longsword_Attack_Light_Forward_Combo_3`. The card's colours and the page's type chips
  read the sword's words («Light», «Hold»), which match nothing of the dagger's.
- **No previews at all** (the sword has 52 files in `media/`).

## The decisions

1. **The graph says whose it is.** The extractor writes `meta.weapon = {key, label, prefix, media}`
   and, per node, `type` (`light` / `hold` / `sprint` / `jump` / `dodge`). Neither the card nor the
   page then holds a naming rule per weapon, and a third weapon is a row in the extractor's table and
   nothing else. **A graph without those fields is the Longsword read by today's rules**, so the
   sword's current `graph.json` needs no regeneration and nothing of it moves.
2. **The dagger's files lie beside the sword's**: `graph.dagger.json` and `media/dagger/`, the
   sword's `graph.json` and `media/` untouched. The weapon's graph file and media subfolder come from
   the graph's own `meta.weapon`, so the layout is a fact of the data, not a table in the code.
3. **One `state.json` for both.** The node ids of the two weapons cannot collide
   (`AM_Longsword_Attack_*` against `AM_Dg_Atk_*`), so the statuses, assignees and people stay one
   board; «N of M done» counts the weapon shown.
4. **The chosen weapon is shared state**, the key `longswordMoveset.weapon` in that same file, so the
   card and the page always show the same weapon — the card's 1.5 s poll and the page's own reload
   carry a switch made on the other side.
5. **The dagger's labels are the project's**, the prefix from `meta.weapon.prefix` stripped and the
   underscores spaced: «NLt NLt NHd», «LLt LHd», «JA Active Success», «Spr». Nothing is expanded into
   words no one can search for in the editor or in a Maya scene name.
6. **Four knobs a weapon in their extractor**, and no more: the resources preset, the montage folder
   (for the «in the folder, not in the graph» list), the label prefix, and the named combo checks the
   sword has. The dagger's row carries the general checks only (every node has an animation and a
   slot, every chooser row resolved): the sword's three named pairs are knowledge about the sword, and
   inventing the dagger's would be inventing knowledge.

## The card

- Segments `[Longsword | Dagger]` under the subtitle, before the filters. The list is **the graphs
  found in the folder** (`graph.json` and `graph.*.json`), the plain `graph.json` first and the rest by
  their file name; one graph in the folder, no segments at all. A weapon's name on its segment is its
  `meta.weapon.label`, else the file's own middle word capitalised (`graph.dagger.json` → «Dagger»,
  `graph.json` → «Longsword»).
- A switch rereads the graph, rebuilds Opening / Assignee / the type chips / the trees and fits them.
- The type chips are the types the graph actually holds: the dagger has no Dodge, so no Dodge chip.
- The colour of a card's top and of a wire is `nodes[id].type`, else today's name rule.
- Previews come from the weapon's media subfolder (`media/dagger/<id>.jpg`); with no file the card
  draws as it already draws a card whose preview is missing.
- **Open 3P / Open 1P do not change by a line**: the slot is the node's, and the road is the UE
  Bridge's montage import.
- The folder button, the state sharing, the statuses and the assignees are the card's as they are.

## The page

The same two buttons in its header, reading and writing the same key. A switch loads
`graph.dagger.json` and the dagger's media subfolder. The board, the statuses, the 3D viewer and the
sync are untouched.

## Proof

- **Unit tests** (the plugin): a folder with two graphs lists two weapons, the sword first; a folder
  with one lists one; the dagger's graph gives its own labels, types and media paths; a graph with no
  `meta.weapon` reads as the Longsword by the old rules; the switch writes the shared key and the
  card rebuilds its menus, chips and trees; the statuses of the two weapons do not touch each other.
- **The extractor's own proof, in one editor run**: the sword regenerated into a scratch file and
  compared with today's `graph.json` — equal but for `meta.generated` and the new `meta.weapon` /
  `type` fields. That is what shows the parameterisation changed nothing for the sword.
- **The dagger's graph, checked against the project**: every node is an `AM_Dg_Atk_*` that exists in
  the dagger folder, every node has an animation and a slot, and the «in the folder, not in the
  graph» list is printed for the animator to read (a montage the chooser never returns is a fact
  about the game, not a bug in the extraction).
- **The page** in the browser: the two buttons switch the trees, and a switch made in Maya reaches the
  page and the other way round.
- **Not seen in a GUI Maya**: the animator's own check, as the card itself was.

## What the build changed

- **The chips are dimmed, not absent.** A `rowLayout`'s column count is fixed when it is made, so a
  chip row cannot grow or shrink per weapon. Every type keeps its chip; the ones the weapon has no
  attacks for are disabled and cleared, and a type that leaves the filter this way takes its own filter
  value with it. The animator sees that the type exists in the vocabulary and that this weapon has none.
- **The page's weapon list comes from `serve.py`**, which answers `GET /graphs.json` with the same
  listing `model.weapons` computes (a page served by a plain `http.server` gets a 404 and shows the
  Longsword alone). A page cannot list a folder by itself, and probing for file names would be guessing.
- **The page's buttons wear a class of their own** (`.weaponswitch`): its own page switch toggles `on`
  for every `.pageswitch button` by `data-page`, which cleared the lit weapon. Found in the browser.
- **The page's card names go through the weapon's prefix too** (`strip`, the listing's `prefix` field);
  before that the dagger's cards read «Dg Atk NLt».
- **The dagger has a Dodge chip after all**: its chooser reuses the sword's `Back_Dodge_Thrust`. The
  chips being data rather than a table is what made that right without a line of code about it.
- **`work/weapon.txt` and `work/graph_out.txt`** carry the weapon and the output file into the editor,
  the way the render step already reads `work/render_only.txt`; an environment variable would not reach
  an editor that is already up.

## Not built

- The dagger's previews, webm, 1P pies and 3D — a second editor run, when the graph is right.
- The sword's graph is not regenerated (it needs no new field to keep working).
- A third weapon: a row in the extractor's table, and nothing in the plugin or the page.
