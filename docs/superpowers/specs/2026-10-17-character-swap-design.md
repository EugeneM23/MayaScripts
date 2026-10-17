# A portrait dropped on a character swaps it (2026-10-17)

The animator: «когда я переносил драгом наш риг на сцену и попадал в стоящий в сцене скелет с
анимацией то скелет удалялся а анимация пересаживалась на наш риг по правилам ретаргета. Если я
переношу драгом скелет на скелет ... скелеты должны подмениться и анимация перекинуться. Важно что бы
при разных пропорциях программа у нас спрашивала ... если я переношу драгом скелет на РИГ то анимация
должна перенестись на скелет а риг удалиться ... любой из этих объектов может быть в каких-то
констрейнах или слоях обвязан локаторами ... мы должны сработать на уровне скелетной анимации».

Asked, all three the recommendation:
- objects of the animator's constrained to the old character are **re-bound to the new one** (the same
  bone, the same control, else the nearest bone); what has no counterpart is **baked** in world space;
- the old character's **weapons, armor, camera and centre of mass are carried** to the new one;
- **rig onto rig swaps too**.

## The rule

A portrait (Animation Setup's grid, the kind its switch shows) released over a character standing in a
viewport - a rig's game skeleton or a bare skeleton, the Weapons rule for "under the cursor"
(`droptarget.character_target`) - swaps that character for a new one of the portrait. Released over the
floor it stands there, as before. The ghost says «swap Manny_Rig for Creep [rig]».

## The press (`maya_scenesetup/swap.py`)

1. **Read, nothing changed**: the old character (`deletion.characters()`), its take range (playback ∪
   animation range ∪ the keys on its joints and rig controls), what it carries (a weapon per hand - held
   or on the floor - armor pieces, a camera on its camera_root, a CoM group), the constraints of objects
   outside it whose targets are inside it (Retarget holders and BakeAcross links left to Delete).
2. **The take, as a clip**: a plain copy of the old game skeleton (same names, rotate orders, joint
   orients) in a root-level namespace, every joint parent-constrained to its original with no offset,
   baked (`bakeResults -simulation`), the constraints gone, rotations euler-filtered. Whatever drove the
   old skeleton - a rig, layers, knots, constraints - is in those curves. The copy is now exactly what the
   UE Bridge's import leaves, so every rule after it is the bridge's.
3. **The new character, the take on it**: a rig - added (`rigimport.ready_rig`), asked
   (`decide_bones`: a twin never; different proportions - Keep proportions / Squash & stretch / Cancel),
   connected and baked (`retarget_imported`); a skeleton - `skeletonimport.onto_skeleton` with
   `choose_for`. It stands where the old one stood (the retarget is world space). Cancel deletes what the
   press added and the copy; the old character is untouched.
4. **Carried**: the same weapon into the same hand (`equip.to_hand`, its remembered grip), a floor weapon
   dropped where it lay (`equip.to_floor`), each armor piece (`armor.equip`), Camera Setup on a skeleton
   (a rig's bake sets one up itself), a CoM weighed again.
5. **Re-bound**: each foreign constraint's old target replaced by the new character's node - a bone by
   its leaf, a rig control by its leaf when the new one is a rig, a control otherwise by the game bone
   standing nearest it (within 5 cm), a carried weapon by its new node. Same kind (bone↔bone,
   control↔control): the parentConstraint's per-target offsets copied (the grip holds); otherwise the
   offset captured on the current frame. A non-parent constraint is re-bound only same-kind. Anything
   else - a knot inside the old character, an armor piece, a mapping that fails - is baked: the object's
   world motion over the take into its own curves (`bakeResults -simulation`, through a knot's pairBlend
   as Tools' Bake does), the constraint gone.
6. **The old character deleted** (`deletion.plan` + `execute`, no question: the drop is the question).
7. The new character selected, the time back on the frame it was.

A file import flushes Maya's undo queue (trap 115): the swap cannot be undone with Ctrl+Z.

## Not built

A floor drop of several, Connections' hands-on-weapon links (named, not carried), a weapon from an FBX
the catalog does not know, constraints whose object is itself inside the old character.
