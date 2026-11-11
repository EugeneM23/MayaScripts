# Walk Builder: Snap weapon - the weapon lies on the shoulder (2026-11-11)

The animator, with an example on port 7006: «У персонажа на оружии создан aim сам aim привязан сейчас к плечу
персонажа как и его рука ... Я хочу что бы мы сделали такой же функционал в нашем walk builder который позволит
точно так же зафиксировать оружие на какой точке (пока давай на плечах). Обрати внимание что пивот эйма сдвинут
... связать этот функционал с риг позой и если в риг позе у нас aim мод у оружия то мы должны нажать кнопочку snap
weapon». Asked: the shifted pivot is **the aim target moved onto the shoulder** (the point of the blade that rests
there); **the hand rides the clavicle** as in the example; **the roll as in the example** (the up stays in Main).
Then «Делай все до конца».

## The example, read only

`Manny_Rig`, a Long Sword in `hand_r_weaponSpace`, Aim Mode (`LongSwordMesh_aim` under Main). Both `IKArm_R` and
`LongSwordMesh_aimTarget` ride Tools > Across knots inside `FKScapula_R` (the clavicle control); the target stands
~52 cm down the blade from the grip, on the shoulder, not past the tip where Aim Mode puts it. `LongSwordMesh_aimUp`
is not attached: it stays in Main. The aimConstraint: aim (0, 1, 0), up (1, 0, 0), world up the up object.

## Design

**Where it is set up: the mean pose rig.** Rig pose > Create as today; on the rig the animator puts the weapon in
the hand, Aim Mode on it (Connections), the target on the shoulder, the hand where it holds the weapon. No knots
or constraints are needed on the rig: **Snap weapon** reads where things stand.

**Snap weapon** (Rig pose tab, beside Update; module `maya_walk/snapweapon.py`) reads, off the working walker's
mean pose rig, the weapon of that rig in Aim Mode (refused by name otherwise) and, from the rig's game skeleton:

- the holding hand `s` and its world `H`, the clavicle of that side `C_s`: the hand's offset `H . C_s^-1`;
- the weapon's world `W` in the hand's frame: its grip (origin) and its aim and up axes (the constraint's
  `aimVector` / `upVector` turned by `W`);
- the target's place in the frame of the clavicle **nearest it** (a right-hand sword can lie on the left shoulder);
- the up's place in the game root's frame (the root rides Main);
- the other hand's offset from the holding hand, when it stands within `GRIP_CM` (15 cm) of the blade: two hands
  on the weapon.

It is kept on the walker (`skeldarWalkEdits`, a new `snap` entry, plain numbers) and the walker is keyed again.
**Unsnap** drops it. Reset rig pose leaves it (it is its own entry).

**On the walk** (`snapweapon.apply`, numpy), last of everything - after the parameters, the pose, the physics and
the rig pose / key poses layer (that layer turns arm bones; run first, it would pull the hand off the shoulder),
before In place:

    H(f)  = offset . C_s(f)                       the hand rides its clavicle
    G(f)  = grip . H(f), T(f) = t . C_a(f), U(f) = u . Root(f)
    R(f)  = the weapon's turn with its aim axis toward T - G and its up axis toward U - G (an object-up aim)
    H'(f) = H(f) . swung_about(G(f), R0(f)^-1 . R(f))   the hand swung about the grip so the weapon it carries aims

A weapon on the walker follows its hand by its own constraint, so the hand turns with the blade's roll (in the
example the weapon turns in the hand; on a walker nothing else can turn it). With the hand and the target both on
clavicles the blade's direction is fixed to the body; only its roll moves with the up. The other hand (two-handed)
rides the holding hand at its offset. The arms are rebuilt by IK (`_arm_to_hand`), the fingers and the weapon bones
carried (`_reattach`). Applied in full whatever the pose share: it is the rig pose's, not the additive pose's.

**The cost**: a walker whose arms are shorter than the rig's cannot reach - the hand is clamped on its line and the
line says how far the grip stood off; a walker with other proportions puts the target where ITS clavicle is.

## Proof

`docs/superpowers/plans/walkparam/verify_walk_snap_weapon.py`, mayapy standalone: a Manny UE5 skeleton walking a
saved cycle, a Manny rig pose with a Long Sword in Aim Mode, its target moved onto the shoulder; Snap weapon; on
every frame of the keyed walker the hand stays on the clavicle at its offset, the blade's line passes through the
clavicle point, its up axis leans toward the up point, the bones keep their lengths, the loop closes; Unsnap gives
the walk back key for key. Unit tests `tests/test_walk_snap_weapon.py` on the synthetic walker.
