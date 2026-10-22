# Playerchar: the draft character as a rig and a skeleton, its outfit as clothing cards

2026-10-21. The animator, with the draft character open in a scene tab on port 7002: «риг драфтового
персонажа его нужно встроить в наш пайплайн и добавить карточку в скелеты и в риг. Так же ему нужно
сделать броню шлем щит штаны как одежду и поместить карточки в раздел армор. Сам персонаж по умолчанию
пусть будет без одежды.»

## Measured first

- The scene tab is `C:/Users/MY PC/Downloads/T_Playerchar_proxy/Playerchar_Proxy.mb`, unmodified: a
  `MESH` group (Body + Outfit) skinned onto a stock `Manny_Rig` added through Add Character. The folder
  also holds the artist's `SKM_Playerchar_Proxy.fbx` (its own 93-joint skeleton - Manny's to the
  millimetre, pelvis at (0, 95.897, 2.281)) and one 2048 colour atlas, `T_Playerchar_proxy_bc.jpg`.
- Every skinned mesh's bind is the rig's game skeleton at its build pose to 4e-14. Against Manny's own
  skin the worst element is 0.072 (Manny's left calf, a known offset of Manny's mesh): the skeleton IS
  Manny's.
- The meshes: `Body` (18710 vertices), and in `Outfit`: `Pants` (pants and boots), `Shield` (a round
  shield on the back), `TorsoCloth_` (tunic), `Fabrics` (cloak and sash, **unskinned**), `chains_Beard`
  (the helmet's chain veil, **unskinned**), `chains_Legs`, `chains_Shoulders`, and `accessoires` one mesh
  of 19 shells - the helmet and its face guard (the two shells above y 158), the shoulder pads, the belt
  with its pouches, the bracers, a strap.
- Every mesh is UV'd on the atlas (the body's own `.tga` on an `E:` drive is not here; its region is in
  the atlas). Several meshes carry an empty `map1` beside `DiffuseUV`.

## Decided (asked)

- **Four cards**: Helmet (helmet + face guard), Shield, Pants (pants with boots), Body Armor (tunic,
  shoulder and belt chains, shoulder pads, belt with pouches, a bracer, strap). The body alone is the
  character. The two source meshes that were HIDDEN in the animator's scene - `chains_Beard` (a chain
  veil) and `Fabrics` (a cloak), both unskinned and absent from the artist's FBX - are left out: the
  question was asked with them in, the build found them hidden (a viewport picture of the dressed rig
  showed no veil), and the cards hold what the scene shows.
- **Name**: Playerchar - rows «Playerchar [rig]» and «Playerchar [skeleton]».
- **Fit**: a piece is skinned to Manny's bones; it equips onto a skeleton of the same proportions
  (Playerchar, Manny) and refuses any other by name.
- The portrait rendered in a disposable GUI Maya.

## The character

- `assets/Playerchar_Rig.ma`: the shipped `Manny_Rig.ma` with Manny's meshes, its lod group, its
  1P/3P `Main.view` switch and its materials taken out, and `SKM_Playerchar|Body` in, bound to the rig's
  game joints with the source's weights (bind = the build pose, as the source), the bind pose saved
  again whole over every joint (trap 79/91). Textured: one material, the atlas as
  `assets/Playerchar/Playerchar_Color.jpg`, named relatively (`colour.ASSET_IMAGE`).
- `assets/Playerchar_Skeleton.ma`: made from the rig asset the way the Creep's skeleton is - the bones
  re-seated from their world matrices, the rig and everything nothing kept depends on deleted.
- Catalog: `Character("Playerchar_Rig", "Playerchar [rig]", ...)` and `Character("Playerchar",
  "Playerchar [skeleton]", ...)`, model `Playerchar` after Orc D. Both after Manny's rows, so the Auto
  card, which ties to catalog order, still gives a Manny clip to Manny.

## The clothing - a skinned armor kind

- `catalog.Armor` gains `kind` ("rigid", the Tech Limb's, by default; "skinned" for clothing). A skinned
  row's `bone` is the bone its armor space follows (Helmet `head`, Body Armor `spine_03`, Shield
  `spine_05`, Pants `pelvis`) - bookkeeping only: selecting a piece names its character, Delete and Swap
  find it, `worn()` reads it.
- `assets/Armor/Playerchar_<Piece>.ma`: one group of skinned meshes at identity (`inheritsTransform`
  off on each mesh, so the space's motion is not added to the skin's) and a copy of the game skeleton at
  the bind the meshes were skinned on. `accessoires` is split by shell (the head-weighted shells are the
  helmet). One UV set, `map1`. No material: the row's `texture` (the atlas) is painted at Equip - the
  character's own material, reused (`colour.textured_material`).
- Equip of a skinned row: refused unless the target's game skeleton has every influence bone and its
  bone lengths at its bind are the piece's (median within 1 %, `armor.fits`); the file imported into a
  namespace of its own; every skinCluster's `matrix[i]` reconnected to the target's joint of the same
  name (the bindPreMatrix stays the piece's - a twin's joints at their bind stand where the piece's
  did, wherever the character stands); the piece's skeleton and bind pose deleted; the group hung in the
  anchor bone's armor space. Unequip, Delete character and Swap need nothing new.
- The icons: `make_armor_icons.py` paints a textured row's triangles in the atlas's colours, and sees
  clothing as the character is seen (up Y, from the front, or from behind for the shield).

## Proof

`docs/superpowers/plans/verify_playerchar.py`, mayapy standalone: both rows added, textured, at bind;
a UE clip retargeted onto the rig exact (a twin); all four pieces equipped on the rig - every vertex
where the source scene's skin puts it at the bind and under the take; Unequip; equipped on a Manny
skeleton; refused on the Creep; Delete character takes the clothes; the export bones only.

## Addendum 2026-10-22: the 1P version, as Manny's

The animator: «Для этого персонажа нужно сделать 1P версию точно так же как и для менни».

- Manny's 1P (`Skin_1p`, 2026-10-09) is the cut of his body keeping the arms from the shoulder and the
  legs from the hip: no head, no torso. `Main.view` (3P:1P, not keyable, 3P by default) switches it with
  `Skin_3p` through two conditions; the skeleton asset keeps `Skin_1p` hidden.
- Playerchar's body is not Manny's mesh, so the cut is a rule fitted on Manny's: a face is the 1P's when
  any of its vertices weighs at least 0.35 on the arm and leg bones (upperarm, lowerarm, hand, the
  fingers, thigh, calf, foot, ball). On Manny's `Skin_3p` it gives his own cut back to 1726 of 92178
  faces (1.9 %).
- `Body_1P` (7682 of 18710 vertices) beside `Body` in `SKM_Playerchar`, skinned with the body's weights
  vertex for vertex on the same bind pose, the same material; `Main.view` as Manny's; hidden in the
  skeleton asset. Tools > 1P Setup then sets the rig to 1P.
- Not done: the clothing has no 1P cut (a worn helmet stays on in 1P).
- Proof: `verify_playerchar.py` 18/18 (the 1P on the body under a take, the switch), `verify_1p_setup.py`
  30/30 on Playerchar_Rig.
