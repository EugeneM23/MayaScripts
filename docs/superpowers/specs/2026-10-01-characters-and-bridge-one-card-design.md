# Characters and the UE Bridge in one card

2026-10-01, the animator: «UE bridge и character эти две вкладки имеют общий функционал они
добавляют персонажей в сцену и они зависят дргу от друга. Я думаю их нужно объеденить в одно
окно давай попробуем.»

Asked, in order:
- **the shape: A** of three mockups — top down, *who* then *what*: the [Rig | Skeleton] switch and
  the portraits with Add / Delete / Camera Setup, under them the animation list from Unreal with
  Import and the two exports, one status line (B, two tabs inside the card, and C, the list first,
  were the others);
- **the switches are merged**: the card's [Rig | Skeleton] decides for Add AND for Import; Import
  keeps only [Onto selected | New];
- **the card is «Characters», the first card of the hub**, the Scene group above Animation;
- **Skeleton + Onto selected = onto the selected skeleton** — the clip transferred onto a
  skeleton already in the scene, by bone names, the way the Skeleton mode transfers.

Then «Делай все до самого конца».

## Why they depend on each other

Since the morning the bridge reads the Characters card: a rig it adds is the card's active row
when that is a rig (`rigimport.new_rig_entry`), a skeleton it adds is the card's skeleton
(`skeletonimport.skeleton_entry`). And the bridge's own [Rig | New rig | Skeleton] said the same
thing as the card's [Rig | Skeleton] a second time.

## The card

`maya_hub.SECTIONS`: the `uebridge` section is gone; `characters` is the first row (group
`scene`, icon `user`), so the groups read Scene (Characters, Weapons, Connections, Shared, Armor),
Animation (Retarget, Graph Overlay, Center of Mass), Look, Settings. `maya_hub.ALIASES =
{"uebridge": "characters"}`: `section("uebridge")`, `show("uebridge")` and
`maya_uebridge.show_window()` open the merged card (its `HUB_SECTION` is `"characters"`), so the
hotkey row `window.uebridge`, the flagged shelf button and older verify scripts still land there.

`maya_scenesetup.window.build_characters_panel`, top down:

1. the subtitle `mayaSceneSetupBound` (the character the scene works on), unchanged;
2. `[Rig | Skeleton]`, unchanged in look and memory — it now also says what Import makes;
3. the portraits, unchanged;
4. **Add Character** (secondary now, `plus`) + **Delete** (danger) in one row; **Camera Setup**;
5. the bridge's rows, `maya_uebridge.window.build_rows()`:
   - the editor dropdown + Refresh;
   - the editor line `ueAnimBridgeHeader`, role **context** (it was a subtitle: one card has one);
   - search, the list (`LIST_HEIGHT` unchanged), its drag;
   - `Import [Onto selected | New]` — two segments `ueAnimBridgeMode_onto` / `_new`, not
     remembered (each build opens on Onto selected, as the old modes opened on Rig);
   - «set timeline to clip range»;
   - **Import** — the card's one primary (`download`);
   - Export FBX... + Export to uasset;
6. **one status line**, `mayaSceneSetupCharacterStatus`. The bridge's `_STATUS` is that name
   (a test pins the two equal); the bridge no longer builds a line of its own.

On open the line says the portrait's choice; the editor line says the cache («not connected -
619 animations from the last refresh, press Refresh»), so the list's count no longer overwrites
the choice when the card is built (`_repopulate(quiet=True)`). Search, Refresh, Import and the
drag write the line as before.

## Import: the kind × the target

`maya_uebridge.window.mode_for(kind, target)` (pure) gives the press the internal mode the
bridge always had, plus one:

| kind \ target | Onto selected | New |
|---|---|---|
| Rig | `rig` — the selected rig, else the only one, else a new rig of the portrait; it keeps its place and facing | `new_rig` — a new rig of the portrait |
| Skeleton | **`onto_skeleton`** — the selected skeleton, else the only one, else a new skeleton of the portrait; it keeps its place and facing | `skeleton` — a new skeleton of the portrait |

`import_mode()` reads the kind from the card's memory (`remembered_choice`) and the target from
the segments. Several picked: `rig` and `onto_skeleton` take the first and say so first
(`lineimport.first_only`, now naming «a rig» or «a skeleton»), `new_rig` and `skeleton` lay them
out in the square as before.

### Onto a skeleton already in the scene (`skeletonimport`)

- **Which skeleton** (`choose_skeleton`, pure): the bare skeletons are the character roots that
  are neither under a rig's group nor a rig's game skeleton (`bare_roots`). The selection names
  one through a joint (its topmost joint), a mesh skinned to it (its influences' topmost joint), a
  transform above its root (the Creep's `Armature`), or a weapon / armor piece on it (the bone its
  space follows). One named: that one. Several: refused, named. A rig named and no skeleton:
  refused («Manny_Rig is a rig - pick Rig in Characters, or select a skeleton»). Nothing named:
  the only bare skeleton; none: a new skeleton of the portrait (the `skeleton` road, where the
  clip is); several: refused, named. Every refusal before the editor is asked.
- **Constrained bones**: our weapon links are released before (`bonedrive.unlink`) and relinked
  after (`bonedrive.relink`) — the old merge's rule; any other constraint on its bones refuses
  by name, before the editor is asked.
- **Its place**: where its root stands on the current frame, and its facing (`facing`, pure: the
  horizontal one of the matrix's +Z and −Y axes — +Z for Main, −Y for a UE root under −90 X),
  read before anything moves. The clip is wrapped (`skeldarDropShift`), turned about its root's
  first frame and moved there (`place_moves(..., facing=facing)`), then transferred.
- **The take**: the transfer cuts the time curves on the bones it drives before constraining them
  (a constraint on a keyed channel splices a pairBlend, trap 37's mechanism) and bakes them over
  the clip; bones the clip has nothing for keep what they had and are named.
- The clip's skeleton is deleted, as every press does.

## The drag

`listdrag.Scene` reads the KIND at the drag's start (was the Skeleton mode):
- Rig: unchanged — a rig under the cursor takes it, empty floor a new rig of the portrait.
- Skeleton: a bare skeleton under the cursor (`droptarget.skeleton_snapshot` + the same
  `figure_under`) takes it, keeping its place — kind `onto_skeleton`, caption «A_Jump · onto
  root1»; else empty floor a new skeleton of the portrait, as before. A rig under the cursor is
  still ignored. Several onto a skeleton: the first.

The [Onto selected | New] segments do not change a drop, as the old modes did not change a rig drop.

## Not changed

The portrait drag, Add, Delete, Camera Setup, the exports, the editor, the cache, the list's drag
mechanics, the square, `rigimport`. The Weapons card still follows Characters (its refresh writes
the Characters subtitle). The collapse memory of `uebridge` is left unread.

## Proof

- Unit tests: the hub's order and alias, the card's controls (one primary, one status line, the
  two segments, the context line), `mode_for`, `choose_skeleton`, `facing`, the drag's two kinds,
  the onto-skeleton press faked.
- `verify_characters_card.py` in a disposable Maya (scratch `MAYA_APP_DIR`, the editor's export
  replaced by UE clips on disk): the card first, its content within the 360 px dock, every
  control by name; Rig × Onto / New and Skeleton × New as before; Skeleton × Onto onto a Manny UE5
  skeleton moved to (100, 0, −50) and turned 90°: it stays there facing 90°, every bone on the
  moved clip; a sword on its hand relinked; a drag onto that skeleton; a picture of the card.
