# Walk Builder: the weapon's overlap, a tab of its own (2026-10-30)

The animator, with a Manny skeleton walking on port 7004 and a Long Sword in its hands:

> Давай сделаем новую фкладку для оружия и в этой вкладке один парамметр с захлестом оружия. Суть - если
> бы я делал руками что бы я сделал: я бы привязал наши руки при помощи ИК к оружию а на оружие сделал бы
> aim из нашего tools, верхней ноже за которой следит меч я бы поставил на кончик меча и запек анимацию,
> после чего я бы сдвигал анимацию кончика на какое-то количество кадров так что бы он больше или меньше
> отставал от моей анимации и получил бы захлест.

Asked, both answered as recommended:

- **the hands go with the weapon** (their recipe: the hands IK'd to the weapon, the wrists turning with the
  sword), not the sword lagging inside a fixed grip;
- **milliseconds**, like the three overlaps already in the Arms tab (they said frames, which is how they
  would do it by hand; ms is the family's unit and does not move when the tempo does).

## What the scene holds (measured on 7004, read only)

- The walker is a bare Manny UE5 skeleton, `|Manny_Skeleton_Character|root`, walking its own captured cycle
  (`own:8e4ef9f3703a44a3`, 27 frames at ntsc) under the pose card `LongSword_Idle_3P`, tempo pinned.
- One weapon: `LongSwordMesh`, a child of `hand_r_weaponSpace`, which is parent-constrained to `hand_r` with
  no offset. So **the weapon rides the hand rigidly** and its local matrix in the hand's frame is constant.
- Its mesh's own extents: X ±15.58 (the crossguard), **Y −31.1 .. +115.9** (the blade, the tip at +Y), Z ±1.57
  (the thickness) — the catalog's convention, every model along +Y with its tip at +Y.
- `weapon_r` carries **no keys and a `weapon_r_parentConstraint1`**: Add Weapon's `bonedrive.link` cut its
  curves and hung the bone on the mesh. So the bone follows the mesh, and what the animator sees and what
  Unreal gets are both decided by the mesh's place in the hand.
- `weapon_l` carries the walk's own 168 keys (a helper of `hand_l`, nothing holding it).

So the weapon is **rigid in the hand**, and anything that turns the hand turns the weapon with it. That is
the whole lever this feature needs: nothing of the weapon's own has to be keyed.

## The parameter

`Weapon overlap`, **ms**, sided (per hand; one weapon in two hands takes the two sides' mean), in a new gait
group **Weapon** — so the card grows a `Weapon` tab beside `Arms` with that one slider, and
`gait.PARAMS` / the panel's tab table need nothing else. Its own value is 0 (kind `added`), its slider reaches
**half the walk's own cycle either way** (`gait.overlap_cap`, as the arm overlaps: past half a cycle the lag
of a periodic signal comes back on itself).

## The mechanism — their recipe, in the model

Inside `model._arm_overlap`, after Arm / Elbow / Hand overlap have made the late hands and before
`_arm_to_hand` rebuilds the arms (so one IK rebuild serves all four knobs, and Whip takes the swung arm as
its target):

1. the weapon's **grip** and **tip** are two points in its holding hand's own frame, read from the scene
   (below). The assembly's own paths are `o(f) = grip · hand(f)` and `T(f) = tip · hand(f)`, where `hand(f)`
   is the hand as every knob before this has left it;
2. the aim's target is **the assembly's own tip path read `w` frames earlier** — `shifted_points`, the place
   half of `shifted_cycle`: the linear travel taken out for the shift and put back, so a travelling cycle
   does not leave the tip behind and the result is a cycle again;
3. the weapon is **swung about its grip** by the minimal rotation taking `unit(T(f) − o(f))` onto
   `unit(want(f) − o(f))` — a minimal swing adds no twist, so the roll about the blade stays the frames'
   own (their recipe's up locator, which follows the weapon, says the same);
4. **every hand holding that weapon takes the same swing** (`hands[side] = hands[side] @ swung_about(o, S)`):
   the holding hand, and the other one too when the pose has a two-handed grip and holds no weapon of its
   own. One swing for both hands keeps a two-handed hold exact.

`w = 0` is a no-op matrix for matrix: the target is the tip where it already is, so the swing is the
identity. That is why the target is read off the **assembly's** tip and not the frames' — with Hand overlap
set, the frames' tip is not where the blade points.

The arms are then rebuilt by `_arm_to_hand` as they are for every other overlap: from the current shoulder,
the elbow bending the way the frames bend it, the bones keeping their lengths (a hand past the arm's reach
clamped along its own line). `moved_arms` in the balance counts the knob, so the carry balances the swung
arms.

Nothing of the weapon is keyed: the mesh rides the hand through its weapon space and lands on the aim, and
`weapon_r` follows the mesh (bonedrive) or the hand (the walk's own helper keys) — either way the exported
bone carries the lag.

## What the scene reads

`scene.weapons_in_hands(root)` → `{side: {"grip": (3,), "tip": (3,)}}`, in the holding hand's own frame:

- every marked weapon (`bonedrive.MARKER`, through `maya_markers.find`) whose `weaponspace.holding_hand` is
  a hand of this walker's skeleton;
- its grip is the weapon's own origin, its tip the farthest end of its longest local axis — the plugin's own
  blade rule, shared with Tools' Aim (`aim.tip_offset`, which `aim.placement` now uses for its target
  locator): the animator's "the aim's target at the sword's tip", one rule in the repo;
- both carried into the hand's frame (`tip_local · weapon_in_hand`), so the weapon's own scale (the
  dagger's 0.4) is already in them and the model needs no matrix of the weapon at all;
- a hand holding nothing is not in the answer, and a weapon out in the world (on the floor, in Connections'
  World) is not either: it is no longer rigid in a hand.

It rides into the model beside the pose (`animate` → `evaluated` → `walk.evaluate(knobs, pose,
weapons=)`), and into the evaluation cache's key, so a re-key with the same weapons still skips the model.

The Pick line says what it did — `| the weapon trails 4.5 fr (its tip 12.3 cm behind)` — and says
`| no weapon in the hands: Weapon overlap does nothing` when the knob is set and nothing is held.

## Not built

- a second knob for the lever (the aim at a share of the blade rather than its tip);
- the weapon lagging inside the grip (the other answer to the first question): nothing writes the weapon's
  own channels, so that road would need a writer of its own;
- a weapon out in the world, a two-handed grip across two weapons, the weapon's twist about the blade.
