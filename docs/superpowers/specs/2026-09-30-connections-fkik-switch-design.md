# Connections: FK / IK for the arms (2026-09-30)

The animator: «Для вкладки connections нужно реализовать кнопочки которые будут переключать руки в FK IK.
Тут нужно учесть несколько нюансов. У адванцед скелетона уже есть встроенный переключатель FK IK.»
Asked, and answered: the time span is **the highlighted range on the time slider, else the whole take**; a
hand that rides the weapon pressed to FK is **released, then switched**; the buttons are **[FK | IK] per arm,
acting at once**.

## What AdvancedSkeleton's own switch does (read in `AdvancedSkeleton.mel`, 6.797)

- The state is `FKIKArm_<side>.FKIKBlend`, 0 = FK, 10 = IK. It drives the deformation joints'
  point/orient constraints between the FKX and the IKX chain, and (autoVis) which controls are shown.
- `asSwitchFKIK name Arm _R FK2IK|IK2FK` refuses unless the blend is exactly 0 / 10. It keys the previous
  frame with autoKey on, aligns on the current frame (`asAlignFKIK`) and sets the blend. With a highlighted
  range it aligns every frame of it and keys the blend back at the range's end.
- `asAlignFKIK` FK2IK: every keyable custom attribute of the IK control and the pole to its default
  (swivel, follows, lock ...), `stretchy` and `volume` to 10, Lenght1/2 from the FK lengths, the IK control
  on `AlignIKTo<Wrist>`, the pole from the FKX chain. IK2FK: each FK control onto its IKX joint's world
  rotation (and the elbow and wrist onto their positions), the custom-orient correction after.
- **We cannot call it**: a colleague's Maya has no AdvancedSkeleton (local-only, its EULA), and the plugin
  runs nothing of AS since 2026-09-07 (`vendor_bake` is the precedent). The logic is replicated in cmds.

## Measured on the three shipped rigs (Manny, Creep, Orc D; mayapy standalone, build pose)

- The deformation joint, its FKX and its IKX joint stand in one frame: ≤ 3e-6°, ≤ 2e-6 cm.
- `AlignIKTo<Wrist>_<side>` (a child of `FKX<Wrist>`) stands where `IKArm_<side>` stands: ≤ 3e-6°.
- FK and IK controls: no pivots, no rotateAxis; FK rotate order zyx, IK xyz, the pole translate only.
- The FKX joint sits in its control at a constant offset (`CustomOrientReverse`, 172.9–180°).
- Fingers hang under `FKParentConstraintToWrist_<side>` - they follow the blended wrist.
- `setKeyframe` over the port-free path: 1800 keys in 0.06 s.

## The rule: the arm keeps what it SHOWS

**Read the addendum: the build changed the source to the FKX and IKX chains blended by the blend** - the
deformation joints stand off both by the arm's roll. As first written: the source is the three
deformation joints (`Shoulder/Elbow/Wrist_<side>`), sampled on every frame of the span before anything
moves. So the switch works from any state - FK, IK, a keyed or half-way blend - and
the new mode reproduces exactly what was on screen. The controls of the target mode are keyed to match;
the other mode's keys stay.

- **to FK**: each FK control's world = `L⁻¹ · D` (L = its FKX joint in the control, constant), its local
  = that · (its parent's world)⁻¹, the parent of the elbow and wrist controls being the rigid chain from
  the NEW upper joint (`P(f) · D_upper`, P sampled from the scene). Translate and rotate, the control's
  rotate order, each euler the closest to the frame before (trap 108).
- **to IK**: the IK control's world = `K · D_wrist` (K = `AlignIKTo` in the FKX wrist); the pole from the
  deformation chain - a base on the shoulder-wrist line at the elbow's share, nudged 0.2 % of the limb
  away from the pole side IN THE ELBOW'S FRAME, aimed at the elbow, the pole a limb out along the aim
  (`maya_pmretarget`'s pole, measured there: the IK plane is the shown plane when bent, the elbow's roll
  when straight). The pole side is read once from the IK chain as it stands (in-plane, in the IKX elbow's
  frame). The attributes a matched solve needs - `swivel`, `antiPop`, `Lenght1/2` on the control,
  `followArm`, `lock` on the pole - must be at their defaults: over the whole take they are reset (keys
  cut, named in the status); inside a range a non-default one is a refusal by name.
- **The span**: a highlighted range (`timeControl -rangeArray`, end exclusive) - frames `a..b` switched,
  `FKIKBlend` keyed `a-1` (inserted, shape kept) / `a` / `b` target / `b+1` (inserted), stepped out of
  `a-1` and `b`, the target controls' keys outside kept. Else the whole take: playback ∪ the keys of every
  control involved, whole frames; the blend unkeyed at 0 / 10; a channel that came out constant collapses
  to a plain value.
- **Measured after, and said**: the deformation joints over the span against the samples, worst position
  and angle; the status line names them («Arm_R to IK over 0..120 - the arm kept to 0.0004 cm, 0.001°»).
  An FK arm the IK cannot reproduce (bent off the elbow's hinge, longer than the IK reaches) is reported
  by the number, not hidden.
- autoKey off for the length of it; one undo chunk (nothing is imported, so Ctrl+Z undoes it whole).

## Connections

- **Two rows at the top of the card**: `Arm_R [FK | IK]`, `Arm_L [FK | IK]`. Two `iconTextCheckBox`es
  per row (a radio would not fire on the lit segment, and in a mixed take neither is lit); either press
  switches at once, `refresh` then lights the mode read from the rig - FK / IK when the blend is 0 / 10
  (every key of it), neither when it is mixed, which the header names.
- **FK on a hand that rides the weapon**: the hand is released first (baked where its proxy carried it,
  proxy gone - Connections' own release), then switched; the status says both.
- **Hand -> Weapon** (`_follow`): the arm is first brought to IK over the whole take by the same switch -
  before this, the blend was set to 10 over whatever the IK held, and an FK arm edited after the
  retarget jumped. So the keyed-blend refusal (`blend_refusal`) is gone: a mixed take is made IK keeping
  its motion.
- Refusals before anything moves: no rig, a standing retarget, a node of the limb missing, the blend or a
  target channel driven by something other than a curve, IK on a hand that rides the weapon in a mixed
  take, a solve attribute inside a range, "already FK/IK".

## Not built

Hotkey rows (not asked for); legs (toes, heel roll, IKToes); scale (the vendor copies it - our rigs keep joint scale 1); an IK stretched
to reproduce a longer FK arm (Lenght1/2, `stretchy`).

## Proof

`docs/superpowers/plans/verify_fkik_switch.py`, mayapy standalone on the three rigs with a retargeted
clip and an FK edit: both directions over the whole take and over a range, from a keyed blend, the
follow no longer jumping (a positive control flips the blend alone), FK on a following hand, one undo;
then the card live in a disposable Maya.

## Addendum - what the build changed (the same day)

- **The source is the FKX and IKX chains blended, not the deformation joints.** The first build sampled
  `Shoulder/Elbow/Wrist_<side>` and every switch came out 59-83 deg off at one frame while the places
  held: the deformation joint's orient constraint has its `offsetX` DRIVEN by AS's twist network
  (`twistAdditionElbow_R_output1DUC1.o -> Elbow_R_orientConstraint1.ox`; memory "constraint offset can be
  driven"), so it stands off both chains by the arm's own roll. The network reads `<Joint>BM_<side>`, a
  blendMatrix of the FKX and IKX joint by the blend - so that blend (positions lerped, rotations slerped
  the short way) is what the arm shows, and it is the source now. The deformation joints stay the MEASURE.
- **An IK arm cannot hold an FK elbow's twist about its own bone.** Measured on a UE clip retargeted onto
  each rig: the FK elbow relative to the FK shoulder turns about all three axes (the clip's forearm
  pronation), an IK elbow about its hinge only. FK -> IK then keeps every joint's place (0.016-0.048 cm:
  the retargeted FK arm has the SOURCE's bone lengths, the IK the rig's) and the hand's turn (0.0001
  deg), and the forearm twist is lost - up to 59 deg at one frame of that clip, the same on all three
  rigs. AdvancedSkeleton's own switch has the same limit. The status says it with the number
  («hand and elbow kept to 0.026 cm; the FK forearm twist is lost, up to 59 deg at frame 32 (an IK elbow
  does not twist)»); `TOLERANCE_CM` is 0.05 for that length difference. IK -> FK is exact (0.0000).
- **The retarget's own IK stands 20.7 cm off its FK on Manny** (0.06 cm on the rotation-only Creep and
  Orc D, whose IK follows their own FKX): its pole rides the upper arm's frame, not the elbow's plane.
  That is what Connections' old «blend to 10» showed when a hand went onto the weapon - fixed by the
  switch before the follow.
- **Two walks over the frames, not three** (the IK control's and the pole's parents sampled in the first;
  the pole's again only if `followArm` was reset). Every frame costs a whole rig evaluation - 14 ms on
  Manny in a live Maya; `currentTime -update 0` is 12x faster and reads stale values (289 off),
  measured in parallel AND in DG mode, so it is not used. Live: 1.35-2.2 s for 61 frames.
- The status line of the card is three lines (54) - an Apply plus the switch it made first is longer than
  two (trap 67). No hotkey rows: `maya_hotkeys.py` held another session's uncommitted work, and nobody
  asked for them.

Proof: `verify_fkik_switch.py` **63/63 standalone** (21 per rig: Manny, Creep, Orc D);
`verify_connections.py` **40/40 live** in a disposable Maya (gate 5 now: a blend DRIVEN by a node is
refused - a keyed one is switched); the card clicked through Qt in that Maya (Arm_R IK, the lit IK again
«already IK», Hand_L -> Weapon switching the arm first, FK on the following hand releasing it); 2959
unit tests.
