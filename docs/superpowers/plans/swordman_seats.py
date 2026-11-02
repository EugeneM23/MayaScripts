"""Where the Swordman's two props must sit IN THEIR HAND. stdlib only.

Read off the animator's own rig (the Maya on port 7002, 2026-11-02, «Меч и щит
смотрят не в ту сторону. я выставлю тебе так как это должно сидеть на персонаже»):
he placed each prop by hand and these are the matrices his placement reads.

**The hand is the reference, not the weapon bone.** `bonedrive.link` constrains
weapon_r / weapon_l TO the weapon, so the bone follows whatever the animator turns
and a grip measured against it reads zero however far the prop has moved -- that
circularity cost a wrong reading once (CLAUDE.md trap 324's neighbour). A weapon
space is constrained to its hand with no offset, so the prop's matrix in the hand's
frame is the same at every frame and in any pose.

Row vectors, as everywhere in this repo: a point is `p * matrix`, and the prop's
world matrix is `IN_HAND[key] * hand_world`. The scale is stripped (the rig's own
chain leaves 4e-6 of it on a weapon node, and a seat must not resize the model).

`make_swordman_weapons.py` folds the difference between these and what Add Weapon
gives today into each prop's exported points; `verify_swordman.py` gates a real
Add against them.
"""

IN_HAND = {
    "Swordman_Sword": (
        0.8950460702892109, 0.44282318480041993, -0.05291652920453116, 0.0,
        0.025820604415764586, 0.06700035409322558, 0.9974187931551055, 0.0,
        0.4452255927588232, -0.8941021080137299, 0.04853444135826657, 0.0,
        -5.519494312280642, -5.419160564452408, -1.0547957599686484, 1.0),
    "Swordman_Shield": (
        -0.8961011932697036, -0.30518854355945757, -0.3222772165398456, 0.0,
        -0.3501744363391873, 0.039957065555433324, 0.9358318743485559, 0.0,
        -0.2727279148806479, 0.9514533019503668, -0.14267480034189006, 0.0,
        -0.44849205017091265, 1.899271011352539, 0.4416770935058558, 1.0),
}

#  the hand each prop sits in, and the drive bone that follows it
HANDS = {"Swordman_Sword": ("R", "hand_r", "weapon_r"),
         "Swordman_Shield": ("L", "hand_l", "weapon_l")}
