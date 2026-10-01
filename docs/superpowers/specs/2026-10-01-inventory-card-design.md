# One Inventory card: Weapon and Armor, tiles everywhere, headings everywhere

2026-10-01, the evening, the animator: «Та часть где мы подключаемся к анрилу ее нужно озаглавить UE
Connect пускай будет. Далее давай объеденим вкладки weapon и армор в одну inventory. Пускай в ней будет
два раздела weapon и армор. Давай для wepon раздела уберем функционал сетчатого инвентаря, оружия
одевать на персонажей и выкидывать в сцену драгом можно но перемещать по сетке не нужно. Пусть все
будет конссистентно».

Asked (a mockup of both cards), all four answered with the recommendation:
- **Weapon = tiles + the two hand cards**: square tiles as Armor's and the portraits' (a click picks, a
  drag goes into a hand or onto the floor), the hand cards with their Channel Box grips kept and still
  drop targets;
- **Equip / Unequip in both sections**;
- **Armor drags too**: a tile dropped on a character in a viewport puts the piece on him, in its place;
  on empty floor nothing;
- **headings everywhere**: Animation Setup «Characters» and «UE Connect», Inventory «Weapon» and «Armor».

## The hub

- `maya_hub.SECTIONS`: the `weapons` row is labelled **Inventory**, icon `backpack`; the `armor` row is
  gone and `ALIASES` gains `"armor": "weapons"`, so `armorpanel.show_window`, the hotkey row
  `window.armor` and an older verify open the Inventory card. The key stays `weapons` (the collapse
  memory, every opener) - as Animation Setup kept `characters`. Connections still follows it.
- A new hub role **`heading`** (`maya_hubstyle.ROLES`): a section's title inside a card, bold, in the
  primary text colour, with room above it. In the classic hub a `boldLabelFont` text.

## Animation Setup

- «Characters» (`mayaSceneSetupCharactersHeading`) above the [Rig | Skeleton] row.
- «UE Connect» (`ueAnimBridgeHeading`) at the top of the bridge's rows; the editor line under it drops
  its «Unreal: » prefix («not connected - 619 animations from the last refresh, press Refresh for the
  live list», «connected»).

## Inventory

`maya_scenesetup.window.build_weapons_panel`, top down: the subtitle (the character); **Weapon**
(`mayaSceneSetupWeaponHeading`); the weapon panel (`maya_inventory`, over `mayaSceneSetupInventory`);
**Equip** (primary, `sword`) + **Unequip** (danger, `trash`) - were Add / Remove Weapon, same functions;
**Armor** (`mayaSceneSetupArmorHeading`); `armorpanel.build_rows()` - the tiles, Equip + Unequip;
**one status line** `mayaSceneSetupStatus` (armor's `_STATUS` IS that name, a test pins it); then
`armorpanel.watch()` - its SelectionChanged job on that line, which re-reads the pills and writes
nothing (the line is the last press's).

### The weapon panel (`maya_inventory`, `maya_invlook`)

- The hand cards as before (name, Channel Box column, well; click picks; the right button Open scene).
- Under them the **tiles**: `maya_charlook.grid` - the portraits' and the armor's own geometry - one
  per catalog row in catalog order, the icon turned 45° and fitted into the square (a 1 x 4 cell sword
  upright would be a quarter of the tile wide), the name under it, the picked one lit as Armor's, an
  «equipped» pill on a weapon the current character holds (a hand or the floor).
- The drop table: tile → hand card: into that hand; tile → a hand in a viewport / the floor: as before;
  hand card → the other card: moved; hand card → the tiles: taken off; hand card → the viewport: as
  before; tile → the tiles: nothing.
- **Gone** (gone-tests): the cell grid, the rearrange, Sort and its menu row, the layout memory
  (`skeldarInventoryLayout`), `plan_move` / `arrange` / `pack` / the record.

### The armor tiles (`maya_armorgrid`)

- A drag past Qt's start distance carries the icon (the hub's shared ghost); over a character in a
  viewport (`droptarget.character_target`: every character's bones, the Weapons rule - its nearest bone
  on screen within max(16 px, 8 % of its height)) the caption reads «Tech Limb · onto Manny_Rig» and the
  release equips it there (`armorpanel.equip_on(root, key)`, the Equip press for that character); else
  «drop onto a character», nothing. Esc / the right button cancel; on the hub nothing.

## Proof

Unit tests for every piece; `verify_inventory_card.py` in a disposable Maya: the Inventory card right
after Animation Setup, no Armor card, `show("armor")` opening it; the four headings; the controls top
down and one status line; the tiles (no grid, no Sort); a weapon tile dropped through `drop_at` onto a
rig's hand and onto the floor; a hand card dropped on the tiles taking it off; an armor tile dragged
through Qt onto the rig, worn; a picture.

## Addendum — two tabs, not two stacked sections (minutes later)

The animator, after using it: «сейчас у нас два раздела в одной вкладке, я хотел немного не так. У нас
есть вкладка inventory и в ней два раздела между которыми мы переключаемся нажимая на название раздела
Weapon Или Armor как бы в разделе две под вкладки».

- The Inventory card opens with a **[Weapon | Armor]** row of segments (`mayaSceneSetupInventoryTabs`,
  the hub's own switch, as [Rig | Skeleton]); each tab is a column (`mayaSceneSetupWeaponTab` /
  `mayaSceneSetupArmorTab`), one managed at a time (`window.show_tab`), the last one remembered
  (`mayaSceneSetup_inventoryTab`). The «Weapon» / «Armor» headings are gone - the segments name the
  sections. Animation Setup keeps its two headings: it was asked stacked (mockup A).
- Showing a tab fits its Qt panel to its placeholder again (a hidden widget gets no resize event) and
  writes that tab's pick on the card's one line; `window.refresh` writes the weapon line only while the
  Weapon tab is shown, so a Characters press does not paint a weapon message over the Armor tab.
- `armorpanel.show_window` (the `window.armor` hotkey row) opens the Inventory on its Armor tab,
  `window.show_weapons` on its Weapon tab; `show("armor")` (the alias) just opens the card.
