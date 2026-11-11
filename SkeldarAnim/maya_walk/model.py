"""maya_walk.model - the parametric walk's engine: a walk cycle read once, rebuilt from engine knobs.

numpy only, no Maya (tests/test_walkmodel.py runs it on a synthetic walker). Maya's row vectors
throughout: a world matrix is local . parent, a position its row 3, a rotation turns a row vector v as
v . R. The design: docs/superpowers/specs/2026-10-12-parametric-walk-design.md; since 2026-10-26 the animator's
knobs are maya_walk.gait's parameters, mapped onto these engine knobs
(docs/superpowers/specs/2026-10-26-walk-builder-editable-model-design.md). Every engine knob added since defaults to
no change, so an old caller reads the engine as before; the speed-ups and the operators came from Gait Builder's fork
(docs/superpowers/plans/gaitbuilder/gaitmodel.py).
"""
import cmath
import math
import re

import numpy as np

VERSION = 1

# name, default, low, high - tempo 0 means the source's own cycle length
KNOBS = (
    ("pose", 0.0, 0.0, 1.0),
    ("stride", 1.0, 0.4, 1.8),
    ("tempo", 0.0, 0.0, 2000.0),
    ("lift", 1.0, 0.0, 10.0),
    ("in_place", 0.0, 0.0, 1.0),
    ("foot_placement", 1.0, 0.0, 1.0),
    ("ground_time", 1.0, 0.7, 1.8),
    ("stance", 1.0, 0.0, 4.0),
    ("swing_out", 0.0, -30.0, 40.0),
    ("leg_match", 1.0, 0.0, 1.0),
    ("leg_turn", 1.0, 0.0, 2.0),
    ("knee_foot", 0.5, 0.0, 1.0),
    ("foot_lag", 0.0, 0.0, 6.0),
    ("foot_flex", 1.0, 0.0, 3.0),
    ("foot_flat", 1.0, 0.0, 1.0),
    ("bob", 1.0, 0.0, 3.0),
    ("sway", 1.0, 0.0, 3.0),
    ("surge", 1.0, 0.0, 3.0),
    ("root_sway", 0.0, 0.0, 1.0),
    ("pelvis_height", 0.0, -40.0, 40.0),
    ("pelvis_forward", 0.0, -30.0, 30.0),
    ("pelvis_rot", 1.0, 0.0, 3.0),
    ("pelvis_twist", 5.0, -40.0, 60.0),
    ("pelvis_list", 4.0, -30.0, 30.0),
    ("spine", 1.0, 0.0, 3.0),
    ("chest_twist", 7.0, -40.0, 90.0),
    ("chest_sway", 5.0, -30.0, 40.0),
    ("gait_lean", 1.0, 0.0, 1.0),
    ("torso_drag", 1.5, 0.0, 8.0),
    ("torso_bounce", 0.2, 0.0, 1.0),
    ("arms", 1.0, 0.0, 3.0),
    ("elbow", 1.0, 0.0, 3.0),
    ("arm_drag", 1.5, 0.0, 8.0),
    ("arm_bounce", 0.3, 0.0, 1.0),
    ("head", 1.0, 0.0, 3.0),
    ("head_drag", 2.0, 0.0, 8.0),
    ("overlap", 0.0, 0.0, 6.0),
    ("weight", 0.0, -1.0, 2.0),
    ("balance", 1.0, 0.0, 1.0),
    ("exaggeration", 1.0, 0.0, 2.0),
    #  Arms % and Hands % (2026-11-04): how much of the cycle's own animation a part of the arm keeps - the lever
    #  a pose's grip pulls (gain *= 1 - alpha), as a knob. `arms` is above and already multiplies the clavicle,
    #  the upper arm, the forearm and the hand bone; `hands` is the hand bone and its fingers, which carried a
    #  hard 1.0 under every knob there was (gains.get("finger", 1.0): no arms, no elbow, not even exaggeration)
    ("hands", 1.0, 0.0, 3.0),
    # Operators (Gait Builder's, 2026-10-26): each adds its unit to the walk's own - 0 changes nothing. A swing is
    # added in phase with the walk's own (its gait harmonic)
    ("lean_add", 0.0, -60.0, 60.0),           # deg: the trunk forward over the hips, spread over the spine
    ("chest_bounce_add", 0.0, -30.0, 30.0),   # deg: the chest's pitch (twice a stride)
    ("nod_add", 0.0, -45.0, 45.0),            # deg: the head forward (down)
    ("arm_fwd_add", 0.0, -90.0, 90.0),        # deg: the upper arm held further forward
    ("arm_out_add", 0.0, -60.0, 90.0),        # deg: the upper arm held further out to its side
    ("elbow_add", 0.0, -60.0, 140.0),         # deg: the elbow bent further
    ("elbow_swing_add", 0.0, -60.0, 60.0),    # deg: the elbow's bend swinging (once a stride)
    ("shoulder_add", 0.0, -40.0, 40.0),       # deg: the shoulder (clavicle) raised
    ("toe_add", 0.0, -60.0, 60.0),            # deg: the foot turned out
    ("knee_bend", 0.0, 0.0, 90.0),            # deg: a planted knee bent at least this (0: off)
    # deg: the knee of a planted leg at the middle of its contact - the passing phase - bent no more than this
    # (0: off). The cap gives way there only and the hips rise as far as every leg allows, so the contacts keep
    # the cycle's own geometry and the body vaults over a straight leg (2026-11-02). Knee bend, the opposite
    # ask, wins where both are set
    ("passing_knee", 0.0, 0.0, 90.0),
    # A leg straightened past where the source has it at that phase meets its limit (the walk's straightest)
    # with a corner, and a knee near straight is the root of its reach: the knee clicks (a grown lift-off, a
    # swing reaching for a long step, the pelvis's cover). Past max(the source's own, (1 - knee_soft) x the
    # limit) it eases into the limit with no corner, and the pelvis, the growth and the swing's draw-in aim at
    # that start. 0: Walk Builder's hard limit (Gait Builder, 2026-10-26)
    ("knee_soft", 0.0, 0.0, 0.2),
    # The decomposition (2026-10-26, the editable gait model): every body series is its regular part (the mean and
    # HARMONICS stride harmonics) plus a residual (the clip's handwriting). Detail scales the residual; a regular gain
    # scales one channel's regular part about its mean - so an amplitude read off the result's harmonics scales
    # exactly. A step's print across the body is the side's mean plus its own irregularity x Detail.
    ("detail", 1.0, 0.0, 1.0),
    ("g_bob", 1.0, 0.0, 10.0),        # the pelvis's height
    ("g_sway", 1.0, 0.0, 10.0),       # its side to side
    ("g_surge", 1.0, 0.0, 10.0),      # its forward and back
    ("g_head", 1.0, 0.0, 10.0),       # the head's world turn (0 holds the gaze)
    ("g_arm", 1.0, 0.0, 10.0),        # the upper arm's swing
    ("g_elbow", 1.0, 0.0, 10.0),      # the forearm's turn in the elbow
    ("g_spine", 1.0, 0.0, 5.0),       # the spine's and the neck's local turns
    # A swing added where the walk has (next to) none of its own: at its own phase when it has one (BOB_QUIET /
    # ARM_QUIET), else at the guide's - the bob low 5 % of a step after each strike, an arm forward at the other
    # foot's strike. Both peak to peak.
    ("bob_add", 0.0, -30.0, 30.0),    # cm
    ("arm_swing_add", 0.0, -90.0, 90.0),   # deg
    # The step's timing set directly (each per side): Ground time's share of a stride a contact lasts (0 = the
    # walk's own, else every contact lengthened or shortened to it - not x the walk's own, as ground_time); a
    # roll over the ball late in the stance (Push-off, heel up at the toe-off) and back on the heel at the strike
    # (Heel strike, toes up), gone by the foot-flat the walk's own frames + slap later. Both added to what Foot
    # placement's reach rolls, past Foot flat (they are asked for)
    ("duty", 0.0, 0.0, 0.9),
    ("push", 0.0, 0.0, 60.0),         # deg
    ("heel_strike", 0.0, 0.0, 40.0),  # deg
    ("slap", 0.0, -10.0, 20.0),       # source frames
    # Overlap as a time shift (frames of the new cycle): a joint's whole series later, its amplitude kept. The arm
    # (per side) from the clavicle (0.6 of it) down, the forearm and the hand later again; the spine bottom up (0
    # at spine_01, all of it at the top and the neck), the head later than the chest by head_lag; joints under
    # them as their parent
    ("arm_lag", 0.0, -10.0, 15.0),
    ("elbow_lag", 0.0, -10.0, 15.0),
    ("hand_lag", 0.0, -10.0, 15.0),
    # The arms' overlap (2026-10-29): the whole arm late by this many frames of the new cycle - its hand's
    # world motion (the linear travel out) read that much earlier and the arm rebuilt to it by IK from the
    # current shoulder, so what the arm takes from the body (the chest's turn, the shoulder's bob and sway) is
    # late with its own swing. Per side; under a grip the held thing goes late and both hands keep their hold
    ("arm_overlap", 0.0, -120.0, 120.0),
    ("elbow_overlap", 0.0, -120.0, 120.0),
    ("hand_overlap", 0.0, -120.0, 120.0),
    # The Weapon tab, rebuilt 2026-11-05 on the animator's own recipe, shown step by step in a scene: the IK
    # arms parent-constrained to the torso with their animation DELETED - the hand static relative to the
    # chest - and then the weapon's baked animation shifted a few frames on an additive layer, so the torso
    # leads and the weapon follows. «Вот так должен работать наш weapon overlap для всех адитивных поз без
    # исключения.» So:
    #   `weapon_hold` (Hold, ON by default): the hand rides the CHEST rigidly, at its own MEAN offset over
    #       the cycle - it stops playing the arm's swing and keeps its pose relative to the torso, which is
    #       what an additive pose's hold means. Two hands holding one thing take the carrier's transform, so
    #       the grip is kept to machine precision.
    #   `weapon_overlap` (ms in the card, frames here): the chest pose the hand rides is this many frames
    #       old - the overlap, and the one number the animator dials.
    # Per side, and ONLY where the additive pose holds that arm: at Pose 0 there is no pose, the arms play
    # the cycle and the tab does nothing (the share blends it in). It needs NO weapon in the scene - the hand
    # is the lever, and anything it holds follows by its own constraint.
    ("weapon_hold", 1.0, 0.0, 1.0),
    ("weapon_overlap", 0.0, -120.0, 120.0),
    # Inherit (2026-11-10, «ручку которая будет контролировать процент холда 1 - 100% наследования как
    # сейчас 0 - 0 процентов полная статика»): Hold parents the hand to the chest, and this is that
    # parent's weight - the share of the chest's own motion (its turn and its place, about their means)
    # the held hand takes. 1 rides the chest as before, matrix for matrix; 0 stands still in the frame
    # the cycle travels in. The 2026-11-03 Chest rotation / position strengths, as one number.
    ("weapon_inherit", 1.0, 0.0, 1.0),
    # Aim target (2026-11-10), the animator's example: the weapon in Aim Mode with its aim target's keys
    # thinned out «для придания веса оружию» - the grip plays the whole animation and the blade points at
    # a target that plays less of it. «1 - вся анимация 0 - аим таргет полностью статичен»: the share of
    # its own motion the target keeps about its mean (_weapon_aim). It needs no Hold; with no weapon in
    # the scene the right hand's weapon bone stands for the blade.
    ("weapon_aim", 1.0, 0.0, 1.0),
    # Shoulder (2026-11-10, «доводчик плеча которые будет подкручивать плече что бы мы избавились от
    # перерастяжения»): the share of the arm's REACH changes the clavicle takes. The hand the tab moves
    # (Hold's chest, late and damped; the aim) comes nearer the shoulder and goes further from it, and the
    # elbow alone paid for that - it opened to 0.94 of the arm on the animator's cycle. The clavicle turns
    # about its own pivot so the shoulder follows the hand: 0 nothing (matrix for matrix), 1 the shoulder
    # takes all of it and the elbow holds its mean bend (_shoulder_assist).
    ("weapon_shoulder", 0.0, 0.0, 1.0),
    ("torso_lag", 0.0, -10.0, 15.0),
    ("head_lag", 0.0, -10.0, 15.0),
    # The bob's timing: its regular part later (frames of the new cycle: the low point after the contact moves
    # with it), and a second bob twice a step, peak to peak, its lows at each strike and each passing
    ("bob_shift", 0.0, -30.0, 30.0),
    ("double_bounce", 0.0, 0.0, 20.0),     # cm
    ("chest_phase", 0.0, -180.0, 180.0),   # deg: the chest's twist later than its own against the hips'
    # Balance's swing on each axis (1 the pendulum's change of the side / forward sway, 0 none: a Sway or a Surge
    # the animator set holds its value)
    ("balance_sway", 1.0, 0.0, 1.0),
    ("balance_surge", 1.0, 0.0, 1.0),
    # The springs (Arm, Torso, Head drag) with their stride swing kept: 1 samples a spring's target ahead by the
    # spring's own phase delay at the stride's frequency and scales its swing by 1 / its gain there, so the stride
    # swing keeps its amplitude and timing and only the overshoot and the pivot's jolts are added (Whip)
    ("spring_comp", 0.0, 0.0, 1.0),
    # Foot placement's lock lets a foot that moves faster than LOCK_SLOW .. LOCK_FAST of the walk's travel a frame
    # move as the walk has it (1), rather than holding it still (0): a clip's foot still skimming into its contact
    # or out of it, held, stood 10 cm off where the clip had it and the run sank 16 cm (sadda, 2026-10-26)
    ("lock_skim", 0.0, 0.0, 1.0),
    # Balance gives way to the legs: its carry scaled back where it would sink the pelvis more than BALANCE_SINK
    # of the leg beyond what the step needs without it (1), else carried whole (0) - a leaning pose on a strafe
    # carried its hips 17.8 cm and sank 39 cm (TestStrefe under the goblin, 2026-10-26)
    ("balance_reach", 0.0, 0.0, 1.0),
    # Foot placement's double support: at least a new frame of both feet down at every handoff (1), or only as far
    # as the trailing leg reaches (0) - forced, a jog's 4 % flights were held 1.75 frames and sank it 16 cm (sadda)
    ("double_force", 1.0, 0.0, 1.0),
    # Height's step: a raised pelvis the legs cannot reach shortens the step (1) toward HEIGHT_STEP_FLOOR until
    # it keeps all but HEIGHT_KEEP of the raise - only where a shorter step helps (2026-10-26); 0 the step as asked
    ("height_step", 0.0, 0.0, 1.0),
    # how far a raised Height straightens the planted knees (0..1 of STRAIGHT_KNEE): evaluate sets it from what the
    # raise needs (_height_plan)
    ("height_straighten", 0.0, 0.0, 1.0),
    # Head aim (2026-11-11, «создавать голове аим и контролировать ручкой насколько она смотрит туда»): how much
    # the head looks at the rig pose's head target (maya_walk.headaim, run by the scene after the model; the model
    # itself reads nothing of it). 1 right at it, 0 the walk's own head; nothing without a target.
    ("head_aim", 1.0, 0.0, 1.0),
)
ASPECT_KNOBS = ("lean_add", "chest_bounce_add", "nod_add", "arm_fwd_add", "arm_out_add", "elbow_add",
                "elbow_swing_add", "shoulder_add", "arm_swing_add")
HARMONICS = 4             # a body series' regular part: its mean and this many stride harmonics
BOB_QUIET = 0.5           # cm: a walk's own bob under this peak to peak takes bob_add at the guide's phase
ARM_QUIET = 2.0           # deg: an arm's own swing under this peak to peak takes arm_swing_add at the guide's phase
BOB_LOW_AFTER = 0.05      # the guide's bob: lowest this share of a step after each strike (section 5: one frame)
#  The knobs the card showed until 2026-10-26 (the first part of KNOBS, through Exaggeration): a walked skeleton's
#  version 2 memo holds these; everything after them is an engine knob only maya_walk.gait sets
_NAMES = [k[0] for k in KNOBS]
LEGACY = tuple(_NAMES[:_NAMES.index("exaggeration") + 1])
ENGINE_ONLY = tuple(_NAMES[len(LEGACY):])
DEFAULTS = dict((k[0], k[1]) for k in KNOBS)
RANGES = dict((k[0], (k[2], k[3])) for k in KNOBS)
#  The knobs of a body part that has two sides (2026-10-13: «режим в котором левая и правая сторона станут
#  раздельными»): "<name>_l" / "<name>_r" set that side alone; without them both sides take "<name>".
SIDED = ("stance", "lift", "swing_out", "leg_turn", "knee_foot", "foot_lag", "foot_flex", "foot_flat", "ground_time",
         "arms", "hands", "elbow", "arm_drag", "arm_bounce", "arm_fwd_add", "arm_out_add", "elbow_add",
         "elbow_swing_add", "shoulder_add", "toe_add", "knee_bend", "passing_knee", "knee_soft", "g_arm", "g_elbow",
         "arm_swing_add", "duty", "push", "heel_strike", "slap", "arm_lag", "elbow_lag", "hand_lag",
         "arm_overlap", "elbow_overlap", "hand_overlap", "weapon_overlap", "weapon_hold", "weapon_inherit", "weapon_aim", "weapon_shoulder",
         "spring_comp")
SIDE_KNOBS = dict(("%s_%s" % (name, side), name) for name in SIDED for side in ("l", "r"))

WEIGHT_BOB_DOWN = 0.5     # the bob's low half x (1 + this . weight)
WEIGHT_BOB_UP = 0.15      # its high half x max(0, 1 - this . weight)
WEIGHT_WARP = 0.3         # the bob's clock: beta = this . weight
WEIGHT_WARP_AFTER = 0.05  # slowest this share of a cycle after each low
WEIGHT_LAG = 1.0          # frames of overlap per unit of weight
LOWER_BLUR = 0.06         # the reach's drop of the pelvis, smoothed over this share of a cycle (sigma)
PLANTED_SOFT = 0.012      # knee_soft for a planted leg: it eases into its limit from this share below it
STRAIGHT_KNEE = 12.0      # deg: a raised Height lets a planted knee straighten to this...
STRAIGHT_FULL = 10.0      # ...all of it once Height asks this many cm
STRAIGHT_SOFT = 1.0       # the share of the soft zone a full straightening takes away
#  Passing knee (2026-11-02): a planted leg straightens to the asked bend around the middle of its own contact -
#  the passing phase, where the other leg is in the air and the hips are free to rise over a straight leg. The
#  window rises over the first STRAIGHT_EDGE of the contact and falls over the last (the double supports at its
#  ends are where the other leg stands at its own limit and allows no lift)
STRAIGHT_EDGE = 0.3
STRAIGHT_LIFT_MAX = 15.0  # cm: the most the hips are lifted for it, whatever the ask
#  A CEILING on how fast the lift may move: a share of what the cycle's OWN hips do a frame (its pelvis's p90
#  rise or fall, measured over the saved walks at 1.5..7 cm a frame), floored so a cycle with no bob of its own
#  can still straighten a little. Only a ceiling: the pace that matters is in the knee's degrees below, and at
#  0.4 of the hips' own speed THIS one was the pace - which made the knee enter its ask within a frame of the
#  window's edge, since the first degrees of a straightening cost the most centimetres (2026-11-02)
STRAIGHT_SHARE = 0.6
STRAIGHT_FLOOR = 0.25     # cm a frame at a 30-frame stride
#  ...and the same pacing in the KNEE's own degrees, which is what the animator watches: the ask may turn a
#  planted knee no faster a frame than that cycle's own knee turns (its p90) by more than this much. A rate in
#  centimetres cannot do it - near straight a knee is a square root of its reach (trap 266), so one rate is 2
#  deg of knee at one frame of a cycle and 14 at another, and the hips' rate alone left the leg the rise
#  reached turning at twice its own pace while the other looked right (the animator's own walk, and asd at an
#  8 deg ask: 15.1 deg a frame against its own 6.6; 2026-11-02)
STRAIGHT_DEG_SHARE = 1.25
STRAIGHT_DEG_FLOOR = 1.5  # deg a frame at a 30-frame stride: a cycle whose knee barely moves still straightens
KNEE_SWEEPS = 24         # sweeps of the knee pace: each only lowers the hips, so it settles
KNEE_SETTLED = 1e-4       # cm: a sweep that moves the hips less than this is the last
STRAIGHT_QUIET = 1e-4    # cm: a lift under this is none (an ask the cycle already meets)
OUTSIDE = -1e9           # a frame left out of a knee's target track (its leg is in the air there)
HEIGHT_KEEP = 0.2         # Height's step: a raise losing more than this share of itself to the legs' reach...
HEIGHT_STEP_FLOOR = 0.6   # ...shortens the step (Height's own, not the animator's Step) to this at most
HEIGHT_STEP_GAIN = 1.5    # cm: ...when the shortest step would keep at least this much more of the raise

# the legs and the pelvis (docs/superpowers/specs/2026-10-12-walk-legs-design.md)
TWIST_FREE_DEG = 15.0     # the shin's own twist a knee may keep against its foot; past it they meet (Knee <-> foot)
SWING_EASE = 0.25         # the swinging foot hangs off its shin from this share of the swing to this share before it
BALL_LAG = 1.5            # the toes lag the shin this many times the foot's lag
STEP_REF = 0.8            # a normal step, in legs: Twist is the pelvis's twist at it, growing with the step
LIST_PEAK = 0.17          # the standing hip highest this share of a cycle after its heel strike (the norm)
AIR_STEPS = 64            # a foot's flight found to 1/this of a frame
COUNTER_SHARES = (0.4, 0.35, 0.25)   # spine_01..03 take the pelvis's added twist and drop back, these shares
CHEST_SHARES = (0.25, 0.35, 0.4)     # the top three spine joints take the chest's added twist and sway, these shares
CHEST_STILL = 0.5                    # degrees: a walk's own chest turn below this has no shape of its own
ARM_OUT_AXIS = 0.2        # Arm out: the arm and its side this near parallel (sin) - about the body's front instead
# Leg match (docs/superpowers/specs/2026-10-14-walk-sprint-legs-and-body-design.md): a pose's stance (its splay and
# width) kept 1 / (1 + Fr / GAIT_FROUDE) by a gait of Froude number Fr = v^2 / (g L) - a walk keeps most of it,
# a sprint little: a fast leg swings in the line of travel
GAIT_FROUDE = 1.0
# Gait lean: under a pose's torso the walk's own forward lean over its rest is put back, in the room the pose leaves
# to this lean of the trunk (degrees from up; the stop builder's rule, docs/superpowers/specs/2026-10-14-pose-on-clip)
LEAN_LIMIT = 90.0

# the arms follow the body with inertia (docs/superpowers/specs/2026-10-12-walk-upper-body-design.md)
ARM_SUBSTEPS = 4          # the arms' motion integrated at least this many steps a frame
ARM_CYCLES = 8            # at most this many cycles run to settle the arms' periodic motion
ARM_SETTLED = 1e-5        # radians: settled when a cycle's start moves less than this from the last's
ARM_INERTIA = 1.0         # x the shoulder's (elbow's, wrist's) acceleration felt by the limb below it
ARM_HARMONICS = 6         # the shoulder's path the arms feel: its first this many harmonics a stride (the body's motion)
ACCEL_HZ = 8.0            # ...and none faster than this many a second: a sprint's stride is 15 frames, and 6 harmonics of
                          # it reached a 2.5-frame period - the frames' own noise (AGS_Sprint, 2026-10-14)
OVERLAP_QUIET = 1e-6      # frames: an Arm overlap under this touches nothing
# Aim target (docs/superpowers/specs/2026-11-10-walk-weapon-aim-target-design.md)
AIM_REACH = 1.15          # the aim target stands this far past the blade's tip, x its length (Aim Mode's own)
AIM_BLADE = 100.0         # cm: the blade a weapon BONE stands for where the scene holds no weapon (along its +Z)
AIM_QUIET = 1e-9          # an Aim target this near 1 keeps the whole animation: nothing is touched
INHERIT_QUIET = 1e-9      # an Inherit this near 1 rides the chest whole: the chest's cycle is read as it is
# Shoulder: the clavicle follows the hand (_shoulder_assist)
SHOULDER_QUIET = 1e-9     # a Shoulder under this touches nothing
SHOULDER_MAX_DEG = 35.0   # the clavicle turns no further than this off the frames' own...
SHOULDER_FREE = 0.6       # ...freely up to this share of it, then easing in with no corner (soft_reach)
# the trunk and the head on springs (docs/superpowers/specs/2026-10-14-walk-sprint-legs-and-body-design.md)
BODY_INERTIA = 1.0        # x the pivot's acceleration felt by the trunk on its lever
HEAD_INERTIA = 0.3        # ...and by the head on the neck: a head is held - at 1 a sprint's steps bobbed it 12 deg off
                          # its gaze, noisier than the clip; at 0.3 it is calmer than the clip (AGS_Sprint, 2026-10-14)
HEAD_LIFT = 0.5           # the head's mass point: past the head joint by this share of the neck's length
NECK_SHARES = (0.3, 0.55) # the neck joints take these shares of the head's turn (the head all of it)
GRIP_DIST = 30.0          # cm (the walk's size): a pose's hands this near each other hold one thing together

# Foot placement: a planted foot never slides, one foot always on the ground
# (docs/superpowers/specs/2026-10-12-walk-foot-placement-design.md)
CONTACT_TOL = 1.5         # cm: the heel (ankle) or the ball this near its own lowest is planted
DOUBLE_SUPPORT = 0.08     # both feet down at least this share of the cycle at every step (a walk: ~8-10 %)
RUN_FLIGHT = 0.05         # both feet up longer than this share of a stride at a handoff: a run - its flight is kept
LOCK_STEPS = 16           # the contacts found and the lock integrated at 1/this of a frame
HELD_SHARE = 1.0         # a contact grows past its step only while its down point moves slower than the walk travels
HEEL_BACK = 0.25          # the heel's ground point: under the ankle, this share of the foot (to the ball) back
EXTEND_MAX = 0.5          # the contacts take at most this share of a foot's swing
GROUND_ROOM = 0.6         # Ground time: a longer stance takes at most this share of its swing's time
STRETCH_REACH = 0.96      # Ground time past 1: the legs straighten at most this far (of their length)...
GROUND_STRETCH = 0.15     # ...all of it at Ground time 1 + this
ROLL_RELEASE = 0.1        # the heel's roll eases down over this share of a stride after its peak
LEG_MARGIN = 0.008        # the legs held this share of their length short of their reach once they fall short...
MARGIN_FULL = 2.0         # ...all of it once they fall this many cm short (from nothing at 0)
ROLL_RATE = 100.0         # degrees a stride: a roll changes no faster (rate_limited) - the pelvis sinks the rest
ROLL_BALL = 30.0          # degrees: a foot on its ball alone may roll this much further (heel up) for its leg's reach
ROLL_HEEL = 15.0          # degrees: a foot on its heel alone may roll this much further (toes up)
ROLL_COST = 25.0          # cm^2: a radian of roll weighs as much as 5 cm of the leg falling short (_roll_cost)
ROLL_GRID = 32            # the roll's cost searched on this grid, then refined
ROLL_SOFT = 1.0           # cm: the shortfall's weight eases in over this much (_roll_cost)
KNEE_PLANE_MIN = 0.25     # cm: a knee at least this far off its hip-ankle line says where its leg bends;
                          # nearer than that the direction is noise (a clip's straight leg has none of its
                          # own) and the frames that do say it are read instead (_knee_planes)
ROLL_SENSE = 0.3          # the roll changes from the heel to the ball over this much of the foot's pivot weight
SOLE_HEEL_UP = 65.0       # degrees: no roll stands a sole steeper than this off the ground, heel up
SOLE_TOES_UP = 30.0       # degrees: nor toes up
SOLE_EASE = 15.0          # degrees: a roll eases into those limits over this much
SOLE_HARD = {True: 85.0, False: 60.0}   # degrees: an asked roll stands a sole no steeper (heel up, toes up)
AIR_HOLD = 2.0            # cm: a foot just off the ground may hold the pelvis down this much (_just_off)
GROWTH_SAMPLES = 12       # the lift-off and the swing's start tested at this many steps (_growth)
LOCK_SLOW = 0.2           # lock_skim: a pivot slower than this share of the walk's travel a frame is held whole...
LOCK_FAST = 0.6           # ...faster than this one moves as the walk has it
PUSH_FROM = 0.55          # Push-off's roll comes in from this share of the contact to the lift-off...
#                           ...and goes over the first SWING_EASE of the swing; Heel strike's comes in over the last
FLAT_TOL = 3.0            # degrees: a sole this near the floor is flat (Walk.flat_after: the strike's foot-flat)
ROLL_HOLD = 1.0           # Push-off and Heel strike held whole this many new frames either side of the lift-off /
#                           strike: the frames there read them exactly
SLAP_LEAST = 0.08         # a Heel strike's toes come down over at least this share of a stride (the
#                           loading response: the foot flat ~8 % of the gait cycle after the strike)

# the balance: the centre of mass a pendulum over the feet's pressure (the walks are in centimetres - UE's)
GRAVITY = 981.0            # cm / s^2
GROUND_TOL = 2.5           # cm: a foot point this near its own lowest is on the ground
HEEL_SHARE = 0.4           # the heel point: the ankle this share of the foot (ankle to ball) further back
TOE_SHARE = 0.4            # the toe point: the ball this share of the foot further forward
FOLLOW_RANGE = (0.25, 1.25)  # how strongly the walk's own CoM follows its pendulum, fitted per axis, clamped
CARRY_STEPS = 5            # secant steps of the pelvis carry a frame
CARRY_TOL = 1e-4           # cm: a frame's CoM this near its target is done
BALANCE_ROUNDS = 4         # the carry and the reach's drop solved in turn at most this often
BALANCE_SINK = 0.03        # balance_reach: the carry may sink the pelvis this share of the leg at most
LT_STILL = 1e-5           # cm: a bone's place in its parent this still over the cycle is one place (keyed data: ~1e-6)
ARM_RECARRY = 0.1          # cm: the arms swing again in a balance round only when the carry moved this far
# de Leva (1996): % of the body and the centre's share from the proximal joint
TRUNK_MASS = (11.17, 16.33, 15.96)   # lower, middle, upper trunk: at the thirds of the pelvis..neck_01 chain
HEAD_MASS = 6.94                     # on the head joint
LIMB_MASS = (("upperarm", "lowerarm", 2.71, 0.5772), ("lowerarm", "hand", 1.62, 0.4574),
             ("thigh", "calf", 14.16, 0.4095), ("calf", "foot", 4.33, 0.4459), ("foot", "ball", 1.37, 0.4415))
HAND_MASS = (0.61, 0.5)              # half way from the wrist to middle_01 (else the hand's fingers' mean)


class Refusal(Exception):
    """A clip the model does not read; the message says why, in the animator's terms."""


def knobs(**given):
    """The defaults with `given` on top, each clamped to its range; an unknown name raises ValueError. A side's
    own value of a SIDED knob ("lift_l") is kept when given (clamped to the knob's range)."""
    unknown = sorted(set(given) - set(DEFAULTS) - set(SIDE_KNOBS))
    if unknown:
        raise ValueError("unknown knob(s): " + ", ".join(unknown))
    out = dict(DEFAULTS)
    for name, value in given.items():
        if value is None:
            continue
        low, high = RANGES[SIDE_KNOBS.get(name, name)]
        out[name] = min(max(float(value), low), high)
    return out


def sided(k):
    """{side: the knobs that side walks with}: each SIDED knob the side's own value where one is set, else
    the knob's."""
    return dict((side, dict((name, k.get("%s_%s" % (name, side), value) if name in SIDED else value)
                            for name, value in k.items() if name in DEFAULTS))
                for side in ("l", "r"))


def _units(v):
    """Rows of `v` (..., 3) made unit."""
    n = np.linalg.norm(v, axis=-1, keepdims=True)
    return v / np.where(n > 1e-12, n, 1.0)


def _harmonic(y, phase, order):
    """(amplitude, phase phi) of `y` on cos(order . phase - phi): its least-squares fit, demeaned
    (aspects.harmonic)."""
    y = np.asarray(y, float) - float(np.mean(y))
    c, s = np.cos(order * phase), np.sin(order * phase)
    c, s = c - c.mean(), s - s.mean()
    a = np.array([[c @ c, c @ s], [c @ s, s @ s]])
    if abs(np.linalg.det(a)) < 1e-12:
        return 0.0, 0.0
    x = np.linalg.solve(a, np.array([c @ y, s @ y]))
    return float(math.hypot(x[0], x[1])), float(math.atan2(x[1], x[0]))


def _unit(v):
    v = np.asarray(v, float)
    if v.shape == (3,):             # one vector: plain floats
        x, y, z = float(v[0]), float(v[1]), float(v[2])
        n = math.sqrt(x * x + y * y + z * z)
        return np.array([x / n, y / n, z / n]) if n > 1e-12 else v * 0.0
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-12 else v * 0.0


def _any_perpendicular(e):
    return _unit(np.cross(e, np.eye(3)[int(np.argmin(np.abs(e)))]))


def _skew(w):
    z = np.zeros(w.shape[:-1])
    return np.stack([np.stack([z, -w[..., 2], w[..., 1]], -1),
                     np.stack([w[..., 2], z, -w[..., 0]], -1),
                     np.stack([-w[..., 1], w[..., 0], z], -1)], -2)


def exp_rot(w):
    """The row-vector rotation by |w| radians about w (right hand); w may be (..., 3)."""
    w = np.asarray(w, float)
    if w.shape == (3,):            # one vector: plain floats (the batched form costs ~80 us a call in numpy)
        return _exp3(w)
    th = np.linalg.norm(w, axis=-1)[..., None, None]
    small = th < 1e-12
    k = _skew(w) / np.where(small, 1.0, th)
    eye = np.broadcast_to(np.eye(3), k.shape)
    column = eye + np.sin(th) * k + (1.0 - np.cos(th)) * (k @ k)
    return np.swapaxes(np.where(small, eye, column), -1, -2)


def _exp3(w):
    """exp_rot for one rotation vector, in plain floats (the arms' integration takes thousands)."""
    x, y, z = float(w[0]), float(w[1]), float(w[2])
    th = math.sqrt(x * x + y * y + z * z)
    if th < 1e-12:
        return np.eye(3)
    x, y, z = x / th, y / th, z / th
    s, c = math.sin(th), math.cos(th)
    t = 1.0 - c
    return np.array([[c + x * x * t, z * s + x * y * t, -y * s + x * z * t],
                     [-z * s + x * y * t, c + y * y * t, x * s + y * z * t],
                     [y * s + x * z * t, -x * s + y * z * t, c + z * z * t]])


def _log3(r):
    """log_rot for one rotation, in plain floats."""
    tr = (float(r[0, 0]) + float(r[1, 1]) + float(r[2, 2]) - 1.0) / 2.0
    th = math.acos(min(max(tr, -1.0), 1.0))
    v = np.array([float(r[1, 2]) - float(r[2, 1]), float(r[2, 0]) - float(r[0, 2]), float(r[0, 1]) - float(r[1, 0])])
    s = math.sin(th)
    if s > 1e-7:
        return v * (th / (2.0 * s))
    if th < 1.0:
        return v * 0.5
    return log_rot(r)


def _cross3(a, b):
    return np.array([a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]])


def log_rot(r):
    """The rotation vector w (|w| <= pi) with exp_rot(w) == r; r may be (..., 3, 3)."""
    c = np.swapaxes(np.asarray(r, float), -1, -2)
    th = np.arccos(np.clip((np.trace(c, axis1=-2, axis2=-1) - 1.0) / 2.0, -1.0, 1.0))
    v = np.stack([c[..., 2, 1] - c[..., 1, 2], c[..., 0, 2] - c[..., 2, 0], c[..., 1, 0] - c[..., 0, 1]], -1)
    sin = np.sin(th)
    ok = sin > 1e-7
    w = v * np.where(ok, th / (2.0 * np.where(ok, sin, 1.0)), 0.5)[..., None]
    near_pi = (~ok) & (th > 1.0)
    if np.any(near_pi):
        flat_c, flat_w = c.reshape(-1, 3, 3), np.array(w).reshape(-1, 3)
        flat_th = np.broadcast_to(th, near_pi.shape).reshape(-1)
        for i in np.nonzero(near_pi.reshape(-1))[0]:
            m = (flat_c[i] + np.eye(3)) / 2.0
            flat_w[i] = _unit(m[:, int(np.argmax(np.diag(m)))]) * flat_th[i]
        w = flat_w.reshape(w.shape)
    return w


def _proper(u, vt):
    m = u @ vt
    if np.linalg.det(m) < 0.0:
        u = u.copy()
        u[:, -1] *= -1.0
        m = u @ vt
    return m


def mean_rot(rs):
    """The chordal mean of rotations (n, 3, 3)."""
    u, _, vt = np.linalg.svd(np.sum(np.asarray(rs, float), axis=0))
    return _proper(u, vt)


def orthonormal(m):
    """The rotation nearest m's 3x3 part (scale and shear stripped)."""
    u, _, vt = np.linalg.svd(np.asarray(m, float)[:3, :3])
    return _proper(u, vt)


def _batch_rot(m):
    """The rotations nearest a stack of matrices' 3x3 parts (scale and shear stripped): (..., 3, 3)."""
    u, _, vt = np.linalg.svd(np.asarray(m, float)[..., :3, :3])
    flip = np.linalg.det(u @ vt) < 0.0
    if np.any(flip):
        u = u.copy()
        u[flip, :, -1] *= -1.0
    return u @ vt


def toward(mean, target, alpha):
    """`mean` turned the share `alpha` of the way to `target` (row-vector rotations; 0 is `mean`, 1 is
    `target`): exp(alpha . log(target . mean^-1)) . mean."""
    if alpha <= 0.0:
        return mean
    return exp_rot(alpha * log_rot(target @ mean.T)) @ mean


def blend_matrix(a, b, alpha):
    """Between two rigid 4x4s: the rotation `toward`, the translation lerped; 0 is `a`, 1 is `b`."""
    if alpha <= 0.0:
        return a
    out = np.eye(4)
    out[:3, :3] = toward(orthonormal(a[:3, :3]), orthonormal(b[:3, :3]), alpha)
    out[3, :3] = (1.0 - alpha) * np.asarray(a)[3, :3] + alpha * np.asarray(b)[3, :3]
    return out


def turned_about(v, axis, angle):
    """The vector `v` turned `angle` radians about the unit `axis` (right hand; Rodrigues)."""
    c, s = math.cos(angle), math.sin(angle)
    return v * c + np.cross(axis, v) * s + axis * float(np.dot(axis, v)) * (1.0 - c)


def matrix(rot, pos):
    out = np.eye(4)
    out[:3, :3] = rot
    out[3, :3] = pos
    return out


def periodic_cr(x, tau):
    """Periodic Catmull-Rom through x[0..P-1] (period P) at any real tau; exact on whole frames."""
    p = x.shape[0]
    i = int(math.floor(tau))
    u = tau - i
    p1 = x[i % p]
    if u < 1e-12:
        return np.array(p1, float)
    p0, p2, p3 = x[(i - 1) % p], x[(i + 1) % p], x[(i + 2) % p]
    uu = u * u
    return 0.5 * (2.0 * p1 + (p2 - p0) * u + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * uu
                  + (3.0 * p1 - p0 - 3.0 * p2 + p3) * (uu * u))


def warp(phi, beta, phi0, strides=1):
    """The bob's clock: slowest (slope 1 - beta) a quarter and three quarters of a stride after phi0 (a cycle
    of `strides` strides)."""
    return phi + beta / (4.0 * math.pi * strides) * math.sin(4.0 * math.pi * strides * (phi - phi0))


def straight_ratio(bend, l1, l2):
    """The hip-to-ankle distance over a leg's length (l1 + l2) at a knee bent `bend` degrees: 1 dead straight,
    less as it bends (the law of cosines over the two bones)."""
    c = math.cos(math.radians(bend))
    return math.sqrt(max(l1 * l1 + l2 * l2 + 2.0 * l1 * l2 * c, 0.0)) / (l1 + l2)


def knee_bend_at(ratio, l1, l2):
    """The knee's bend in degrees (0 straight) at a hip-to-ankle distance of `ratio` x (l1 + l2). Near straight
    the knee is a square root of its reach (trap 266): on an 85 cm leg a centimetre of hip is fifteen degrees
    of knee, which is why the lift that straightens a passing leg is small and must move smoothly in time."""
    d = ratio * (l1 + l2)
    c = (d * d - l1 * l1 - l2 * l2) / (2.0 * l1 * l2)
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


def passing_share(r, length, edge=STRAIGHT_EDGE):
    """How far a planted leg may straighten `r` frames past its strike in a contact `length` frames long:
    nothing at the strike and at the lift-off, all of it across the middle, smoothstep in and out over `edge`
    of the contact."""
    if length <= 0.0 or r <= 0.0 or r >= length:
        return 0.0
    u = min(r, length - r) / (edge * length) if edge > 0.0 else 1.0
    if u >= 1.0:
        return 1.0
    return u * u * (3.0 - 2.0 * u)


def smooth_under(need, room, rate):
    """The largest periodic curve (one value a frame, >= 0) under both `need` and `room` that moves at most
    `rate` a frame - the lower envelope rate_limited gives a roll, which is what keeps a lift from pulling a
    knee faster than it can move. smooth_cover's mirror: a cover is the least smooth curve over its needs,
    this the most under its room. A Gaussian cannot do this job: it narrows a plateau away wherever the room
    varies within its reach, and here the room IS the ask - a leg sitting at its cap - so a blur left six
    degrees of knee on the table (2026-11-02)."""
    y = np.maximum(np.minimum(np.asarray(need, float), np.asarray(room, float)), 0.0)
    if y.size == 0 or y.max() <= 1e-9:
        return np.zeros(len(y))
    return rate_limited(y, rate)


def lift_to(q, up, target):
    """How far the hip must rise (cm, + up) for its distance to the ankle to be `target`: the smaller root of
    |q - x . up| = target, with `q` the ankle against the hip as it stands. None where no height reaches it
    (the ankle lies further aside than the target)."""
    qu, qq = float(np.dot(q, up)), float(np.dot(q, q))
    disc = qu * qu - qq + target * target
    if disc < 0.0:
        return None
    return qu + math.sqrt(disc)


def cone_above(track, step):
    """The smallest periodic curve over `track` that moves at most `step` a frame: max over g of
    (track[g] - step x the frames from g). rate_limited's mirror - that one is the largest curve UNDER its
    input, this the smallest OVER it, which is what a knee's target track wants (the straightest track no
    faster than the knee's own pace)."""
    track = np.asarray(track, float)
    n = len(track)
    if n == 0:
        return track
    offsets = np.arange(n)
    distance = np.minimum(offsets, n - offsets) * float(step)
    return np.max([np.roll(track, s) - distance[s] for s in range(n)], axis=0)


def smooth_cover(need, sigma):
    """A smooth periodic curve lying over `need` (one value a frame, periodic): `need` widened by its
    largest neighbour within `sigma` frames (so a narrow peak is not blurred away), blurred with a Gaussian
    of `sigma` frames, then scaled by the least factor that covers every frame's need."""
    need = np.asarray(need, float)
    n = len(need)
    if n == 0 or need.max() <= 1e-9:          # (a need this small is no need: "wanted" below)
        return np.zeros(n)
    reach = int(round(sigma))
    wide = np.max([np.roll(need, s) for s in range(-reach, reach + 1)], axis=0)
    offsets = np.arange(n)
    distance = np.minimum(offsets, n - offsets)
    kernel = np.exp(-0.5 * (distance / max(sigma, 1e-6)) ** 2)
    blur = np.real(np.fft.ifft(np.fft.fft(wide) * np.fft.fft(kernel / kernel.sum())))
    wanted = need > 1e-9
    return np.maximum(blur * float((need[wanted] / np.maximum(blur[wanted], 1e-12)).max()), 0.0)


def rate_limited(roll, step):
    """A periodic signed roll curve (one value a frame) changing no more than `step` a frame, by taking roll
    away only: heel up and toes up each the largest curve under it that moves `step` a frame at most (its lower
    envelope), so a flip from one to the other passes through zero (a step on each side of it)."""
    roll = np.asarray(roll, float)
    n = len(roll)
    if n == 0:
        return roll
    offsets = np.arange(n)
    distance = np.minimum(offsets, n - offsets) * step
    out = np.zeros(n)
    for part, sign in ((np.maximum(roll, 0.0), 1.0), (np.maximum(-roll, 0.0), -1.0)):
        if part.any():
            env = np.min([np.roll(part, s) + distance[s] for s in range(n)], axis=0)
            out += sign * np.minimum(env, part)
    return out


def released(roll, frames):
    """A periodic roll curve (one value a frame; + heel up) whose heel-up part lets go gradually: each frame
    the most of the heel-up rolls of the `frames` frames before it, each eased down by a smoothstep over that
    distance - never above zero earlier than the roll itself, the toes-up part (-) untouched."""
    roll = np.asarray(roll, float)
    up = np.maximum(roll, 0.0)
    if not up.any() or frames < 1.0:
        return roll
    out = up.copy()
    for k in range(1, int(math.ceil(frames)) + 1):
        u = min(k / float(frames), 1.0)
        out = np.maximum(out, np.roll(up, k) * (1.0 - u * u * (3.0 - 2.0 * u)))
    return np.where(roll < 0.0, roll, out)


def shape_bob(v, weight):
    """The weight on one bob sample about its mean: the low half deeper, the high half flatter."""
    if v < 0.0:
        return v * (1.0 + WEIGHT_BOB_DOWN * weight)
    return v * max(0.0, 1.0 - WEIGHT_BOB_UP * weight)


def pendulum(cop, seconds, height):
    """The centre of mass of a linear inverted pendulum, x'' = (g / height)(x - p), over one cycle of
    `seconds`: the pressure p (F samples a cycle, any columns) followed per harmonic k by w^2 / (w^2 + w_k^2),
    w^2 = g / height, w_k = 2 pi k / seconds - exactly at the mean, less the faster it swings."""
    cop = np.asarray(cop, float)
    frames = cop.shape[0]
    omega2 = GRAVITY / max(float(height), 1e-6)
    k = np.arange(frames // 2 + 1)
    gain = omega2 / (omega2 + (2.0 * math.pi * k / float(seconds)) ** 2)
    return np.fft.irfft(np.fft.rfft(cop, axis=0) * gain.reshape((-1,) + (1,) * (cop.ndim - 1)), n=frames, axis=0)


def _fill_periodic(values, known):
    """Rows of `values` not `known` filled by the periodic straight line between the known around them."""
    frames = len(values)
    have = np.nonzero(known)[0]
    out = np.array(values, float)
    for i in np.nonzero(~np.asarray(known))[0]:
        before = have[have < i][-1] if np.any(have < i) else have[-1] - frames
        after = have[have > i][0] if np.any(have > i) else have[0] + frames
        u = (i - before) / float(after - before)
        out[i] = (1.0 - u) * values[before % frames] + u * values[after % frames]
    return out


def soft_reach(d, soft, hard):
    """The distance a leg takes for a wanted hip-to-ankle distance `d`: itself up to `soft`, then easing into
    `hard` with no corner (C1 at `soft`, never past `hard`); `soft` >= `hard` is the hard limit."""
    if d <= soft or soft >= hard:
        return min(d, hard)
    band = hard - soft
    return soft + band * (1.0 - math.exp(-(d - soft) / band))


def two_bone(hip, ankle, l1, l2, bend, reach, soft=None):
    """The knee of a hip-knee-ankle chain bending toward `bend`, the leg never straighter than
    reach . (l1 + l2) - eased into it from soft . (l1 + l2) when given (soft_reach). Returns (knee, the ankle
    it reaches, how far it falls short)."""
    v = np.asarray(ankle, float) - hip
    d = float(np.linalg.norm(v))
    e = v / d if d > 1e-9 else np.array([0.0, -1.0, 0.0])
    if soft is not None and soft < reach:
        d_eff = max(soft_reach(d, soft * (l1 + l2), reach * (l1 + l2)), abs(l1 - l2) + 1e-6)
    else:
        d_eff = max(min(d, reach * (l1 + l2)), abs(l1 - l2) + 1e-6)
    p = bend - np.dot(bend, e) * e
    p = _unit(p) if np.linalg.norm(p) > 1e-9 else _any_perpendicular(e)
    along = (l1 * l1 - l2 * l2 + d_eff * d_eff) / (2.0 * d_eff)
    height = math.sqrt(max(0.0, l1 * l1 - along * along))
    return hip + along * e + height * p, hip + d_eff * e, max(0.0, d - d_eff)


def meet(knee, foot, lead):
    """A knee's and its foot's turns about up (radians) after they meet: the knee may stand TWIST_FREE_DEG
    against the foot (a shin twists that far); past it the excess is shared - `lead` 0 turns the knee to the
    foot, 1 the foot to the knee, 0.5 half way."""
    free = math.radians(TWIST_FREE_DEG)
    d = knee - foot
    excess = d - min(max(d, -free), free)
    if excess == 0.0:
        return knee, foot
    return knee - (1.0 - lead) * excess, foot + lead * excess


def shifted_cycle(mats, lag):
    """A cycle of world matrices (n+1, 4, 4) - its last frame its first moved by the cycle's travel - read
    `lag` frames earlier. The linear travel is taken out for the shift and put back at each frame, so the
    result is a cycle again and a travelling cycle does not leave the shifted thing behind; a fractional lag
    falls between the two frames it lies between (the rotation slerped, the place lerped). lag 0: the input,
    matrix for matrix."""
    if not lag:
        return np.array(mats)
    mats = np.asarray(mats, float)
    n = mats.shape[0] - 1
    per = (mats[n, 3, :3] - mats[0, 3, :3]) / float(n)
    rots = np.array([orthonormal(mats[f, :3, :3]) for f in range(n)])
    place = np.array([mats[f, 3, :3] - per * f for f in range(n)])
    out = np.tile(np.eye(4), (n + 1, 1, 1))
    for f in range(n + 1):
        g = (f - lag) % n
        lo = int(math.floor(g)) % n
        hi = (lo + 1) % n
        a = g - math.floor(g)
        out[f, :3, :3] = rots[lo] @ exp_rot(a * log_rot(rots[lo].T @ rots[hi]))
        out[f, 3, :3] = (1.0 - a) * place[lo] + a * place[hi] + per * f
    return out


def shifted_points(pts, lag):
    """A cycle of world points (n+1, 3) - its last frame its first moved by the cycle's travel - read `lag`
    frames earlier: shifted_cycle's place half, and it answers the same places. The linear travel is taken
    out for the shift and put back at each frame, so the result is a cycle again and a travelling cycle does
    not leave the shifted point behind; a fractional lag lerps between the two frames it lies between.
    lag 0: the input, point for point. The weapon's tip path Weapon overlap aims at."""
    if not lag:
        return np.array(pts)
    pts = np.asarray(pts, float)
    n = pts.shape[0] - 1
    per = (pts[n] - pts[0]) / float(n)
    place = np.array([pts[f] - per * f for f in range(n)])
    out = np.zeros((n + 1, 3))
    for f in range(n + 1):
        g = (f - lag) % n
        lo = int(math.floor(g)) % n
        hi = (lo + 1) % n
        a = g - math.floor(g)
        out[f] = (1.0 - a) * place[lo] + a * place[hi] + per * f
    return out


def damped_points(pts, keep):
    """A cycle of world points (n+1, 3) - its last frame its first moved by the cycle's travel - keeping the
    share `keep` of its own motion: each point pulled toward the cycle's MEAN place, the linear travel taken
    out for it and put back at each frame, so the result is a cycle again and at 0 the point glides down the
    travel line with no motion of its own (in place: it stands still). keep 1: the input, point for point.
    The weapon's aim target under Aim target."""
    if keep == 1.0:
        return np.array(pts)
    pts = np.asarray(pts, float)
    n = pts.shape[0] - 1
    per = (pts[n] - pts[0]) / float(n)
    dev = np.array([pts[f] - per * f for f in range(n + 1)])
    mean = dev[:n].mean(axis=0)
    return np.array([mean + (dev[f] - mean) * keep + per * f for f in range(n + 1)])


def aim_swing(a, b):
    """The minimal row-vector rotation (3x3) taking the direction `a` onto `b` - a swing with no twist, so a
    blade swung by it keeps the roll it had. The identity where the two already agree or either is too short
    to read; about any perpendicular where they are opposite."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    if float(np.linalg.norm(a)) < 1e-9 or float(np.linalg.norm(b)) < 1e-9:
        return np.eye(3)
    a, b = _unit(a), _unit(b)
    axis = _cross3(a, b)
    s, c = float(np.linalg.norm(axis)), float(np.dot(a, b))
    if s < 1e-12:
        return np.eye(3) if c > 0.0 else exp_rot(_any_perpendicular(a) * math.pi)
    return exp_rot(axis / s * math.atan2(s, c))


def swung_about(origin, rot):
    """The world turn `rot` (3x3) about the point `origin`, as a 4x4: a point p maps to (p - o) . rot + o
    (row vectors), so `origin` itself is held and everything else swings about it."""
    o = np.asarray(origin, float)
    out = np.eye(4)
    out[:3, :3] = rot
    out[3, :3] = o - o @ rot
    return out


def late_bend(up, low, hand, lag):
    """The bend plane's hint (n+1, 3) an arm chain gives `lag` frames earlier: the elbow's offset from the
    shoulder-wrist line, unit, read from the three joints' cycles shifted that far (Elbow overlap). It is a
    direction read from differences at ONE frame, so shifted_cycle's travel term - the same for all three
    there - cancels and a travelling cycle does not enter it. lag 0: the frames' own plane, which is what
    _arm_to_hand computes for itself."""
    u, l, h = (shifted_cycle(m, lag) for m in (up, low, hand))
    out = np.zeros((u.shape[0], 3))
    for f in range(u.shape[0]):
        sh, el, wr = u[f, 3, :3], l[f, 3, :3], h[f, 3, :3]
        e = _unit(wr - sh)
        b = (el - sh) - np.dot(el - sh, e) * e
        out[f] = _unit(b) if np.linalg.norm(b) > 1e-4 else _any_perpendicular(e)
    return out


def _runs(mask):
    """Every stretch of True in a cyclic mask, (start index, length) sorted by start; [] when it holds no
    True, [(0, n)] when it holds nothing else."""
    n = len(mask)
    if not mask.any():
        return []
    if mask.all():
        return [(0, n)]
    start = int(np.nonzero(~mask)[0][0])
    out, run, on = [], 0, 0
    for step in range(1, n + 1):
        i = (start + step) % n
        if mask[i]:
            if run == 0:
                on = i
            run += 1
        elif run:
            out.append((on, run))
            run = 0
    if run:
        out.append((on, run))
    return sorted(out)


def _longest_run(mask):
    """The longest stretch of True in a cyclic mask: (start index, length); the mask holds both values."""
    n = len(mask)
    start = int(np.nonzero(~mask)[0][0])
    best, run = (0, 0), 0
    for step in range(1, n + 1):
        i = (start + step) % n
        if mask[i]:
            run += 1
            if run > best[1]:
                best = ((i - run + 1) % n, run)
        else:
            run = 0
    return best


def _hermite(x, length, rise, m0, m1):
    """The cubic on [0, length] from 0 to `rise` with slopes m0, m1 at its ends, at x."""
    t = x / length
    t2, t3 = t * t, t * t * t
    return (t3 - 2.0 * t2 + t) * length * m0 + (3.0 * t2 - 2.0 * t3) * rise + (t3 - t2) * length * m1


def swing_weight(s):
    """How far a swinging foot hangs off its shin at swing progress s (0 at the takeoff, 1 at the landing):
    0 on the ground, eased in over SWING_EASE of the swing and out over the last SWING_EASE."""
    ease = lambda x: (lambda c: c * c * (3.0 - 2.0 * c))(min(max(x, 0.0), 1.0))
    return ease(s / SWING_EASE) * ease((1.0 - s) / SWING_EASE)


def _frame(u, n):
    return np.array([u, n, _cross3(u, n)], float)


def align(u_src, n_src, u_new, n_new):
    """The rotation taking the frame (u_src, n_src) onto (u_new, n_new): v . align = v'.
    Each n must be perpendicular to its u (a leg plane's normal against a bone in the plane)."""
    return _frame(u_src, n_src).T @ _frame(u_new, n_new)


SIDES = ("l", "r")
OTHER = {"l": "r", "r": "l"}
SIDE_WORD = {"l": "left", "r": "right"}
LEG = ("thigh", "calf", "foot")
HELPER_PREFIXES = ("ik_", "camera_", "weapon_", "interaction", "center_of_mass")
ARM_STEMS = ("clavicle", "upperarm", "lowerarm", "hand")
#  Overlap's shares: the arms only since 2026-10-14 - the spine's and the head's overlap is Torso drag / Head drag (a
#  time shift of a world-held head read as a strange lag)
LAG = {"clavicle": 0.6, "upperarm": 0.8, "lowerarm": 1.0, "hand": 1.0}
CONTACT_SHARE = 0.2      # in stance the ankle or the ball moves less than this share of the travel a frame
MERGE_HIGH = 4.0         # cm: two stances of a foot are one while its heel or ball stays this near its lowest between
FOLLOW_TOL = 1e-3        # a helper follows a bone when helper . bone^-1 holds within this (matrix elements)
LOOP_TOL = (0.1, 0.002)  # cm and rotation elements: the last frame against the first moved by the travel
STRAIGHTEN_MAX = 15.0    # degrees: a cycle travelling this little off its root's facing is turned onto it
DUP_TOL = (1e-3, 1e-5)   # cm, rotation elements: two frames this alike are one frame written twice


def _stem(name):
    m = re.match(r"([a-z]+)(_twist_\d+)?_[lr]$", name)
    return m.group(1) if m else None


def _wrapped(angle):
    """An angle (radians) brought into [-pi, pi)."""
    return (angle + math.pi) % (2.0 * math.pi) - math.pi


class Clip(object):
    """A walk cycle as data: joint names, parent indices (-1: none), world matrices (J, P+1, 4, 4) on the
    clip's whole frames (the last the first moved by the travel), frames a second, the world's up."""

    def __init__(self, names, parents, worlds, fps=30.0, up=(0.0, 1.0, 0.0), name="walk"):
        self.names = list(names)
        self.parents = [int(p) for p in parents]
        self.worlds = np.asarray(worlds, float)
        self.fps = float(fps)
        self.up = _unit(up)
        self.name = name


class Foot(object):
    """A foot's step: stance from frame `on` for `length` frames more, mid-stance at `mid`, the footprint's
    coordinates (along, aside, up) against the travel line there."""

    def __init__(self, side, on, length, mid, coords):
        self.side, self.on, self.length, self.mid, self.coords = side, on, length, mid, coords


def trimmed(clip):
    """(clip, how many frames dropped): a cycle whose last frame repeats the one before it - or whose first the
    one after it - is one frame written twice (an export's closing frame keyed again). With the copy in, every
    joint stood still a frame a cycle and every place carried a sawtooth of a frame's travel against the
    travel line, which the arms' springs and Balance took as a jolt: AGS_Sprint's forearms flipped 128 deg at
    the seam (2026-10-14). A walk's root travels, so two equal frames are never motion."""
    worlds = clip.worlds
    same = lambda a, b: (float(np.abs(worlds[:, a, 3, :3] - worlds[:, b, 3, :3]).max()) <= DUP_TOL[0] and
                         float(np.abs(worlds[:, a, :3, :3] - worlds[:, b, :3, :3]).max()) <= DUP_TOL[1])
    lo, hi = 0, worlds.shape[1] - 1
    while hi - lo > 9 and same(hi, hi - 1):
        hi -= 1
    while hi - lo > 9 and same(lo, lo + 1):
        lo += 1
    dropped = lo + (worlds.shape[1] - 1 - hi)
    if not dropped:
        return clip, 0
    return Clip(clip.names, clip.parents, worlds[:, lo:hi + 1], clip.fps, clip.up, clip.name), dropped


def straightened(clip):
    """(clip, degrees): a cycle whose travel runs a few degrees off its root's facing turned, about up through
    the root's first place, onto the root's horizontal axis nearest the travel - every joint's place and
    every joint's turn but the root's own, so the body faces and goes where the root faces (a walk saved a
    little askew drifts sideways on any skeleton it is put on: the target's root faces its own way and the
    travel is carried in the root's axes). Past STRAIGHTEN_MAX (a strafe, a turned clip) or with no root it
    is left as it is: (clip, 0.0)."""
    if "root" not in clip.names:
        return clip, 0.0
    r = clip.names.index("root")
    worlds, up = clip.worlds, clip.up
    travel = worlds[r, -1, 3, :3] - worlds[r, 0, 3, :3]
    flat = travel - np.dot(travel, up) * up
    if np.linalg.norm(flat) < 1.0:
        return clip, 0.0
    flat = _unit(flat)
    best = None
    for axis in orthonormal(worlds[r, 0, :3, :3]):
        for a in (axis, -axis):
            a = a - np.dot(a, up) * up
            if np.linalg.norm(a) < 0.5:
                continue
            a = _unit(a)
            angle = math.atan2(float(np.dot(np.cross(flat, a), up)), float(np.dot(flat, a)))
            if best is None or abs(angle) < abs(best):
                best = angle
    if best is None or abs(best) < 1e-9 or abs(best) > math.radians(STRAIGHTEN_MAX):
        return clip, 0.0
    turn = exp_rot(up * best)
    if np.dot(flat @ turn, np.cross(up, flat)) * best < 0.0:      # the turn goes the way the angle says
        turn = turn.T
    centre = worlds[r, 0, 3, :3]
    out = np.array(worlds, float)
    out[:, :, 3, :3] = (worlds[:, :, 3, :3] - centre) @ turn + centre
    keep = np.array(worlds[r, :, :3, :3])
    out[:, :, :3, :3] = worlds[:, :, :3, :3] @ turn
    out[r, :, :3, :3] = keep
    return Clip(clip.names, clip.parents, out, clip.fps, clip.up, clip.name), math.degrees(best)


def analyse(clip):
    """The clip read once (refusals by name); evaluate() rebuilds it from knobs."""
    return Walk(clip)


class Walk(object):

    def __init__(self, clip):
        clip, self.dropped = trimmed(clip)
        clip, self.turned = straightened(clip)
        self.clip = clip
        self.names, self.parents = clip.names, clip.parents
        self.index = dict((n, i) for i, n in enumerate(self.names))
        need = ["root", "pelvis"] + ["%s_%s" % (b, s) for s in SIDES for b in LEG + ("ball",)]
        missing = [n for n in need if n not in self.index]
        if missing:
            raise Refusal("not a skeleton this model reads (UE names): no " + ", ".join(missing))
        count, frames = clip.worlds.shape[:2]
        if frames < 9:
            raise Refusal("%d frames: too short for a walk cycle" % frames)
        self.P = P = frames - 1
        self.fps, self.up = clip.fps, clip.up
        rot = clip.worlds[:, :, :3, :3]
        rot = rot / np.linalg.norm(rot, axis=-1, keepdims=True)
        pos = clip.worlds[:, :, 3, :3]
        root = self.index["root"]
        travel = pos[root, P] - pos[root, 0]
        climb = float(np.dot(travel, self.up))
        flat = travel - climb * self.up
        if abs(climb) > 0.5:
            raise Refusal("the root climbs %.1f cm a cycle: a walk on flat ground only" % climb)
        if np.linalg.norm(flat) < 1.0:
            raise Refusal("the root travels %.2f cm a cycle: an in-place walk is not read yet (the root must "
                          "carry the travel)" % np.linalg.norm(flat))
        moved = float(np.abs(pos[:, P] - pos[:, 0] - travel).max())
        turned = float(np.abs(rot[:, P] - rot[:, 0]).max())
        if moved > LOOP_TOL[0] or turned > LOOP_TOL[1]:
            raise Refusal("not a closed loop: the last frame stands %.3f cm / %.4f off the first moved by the "
                          "travel - the cycle must end on its first pose" % (moved, turned))
        self.travel = travel
        self.fwd = _unit(flat)
        self.side = _unit(np.cross(self.up, self.fwd))
        self.basis = np.stack([self.fwd, self.side, self.up])     # travel coordinates: v . basis.T
        # the body's own left and front: the walk's side and forward when it walks forward, both turned round
        # when it walks backward (its left hip on the travel's right) - a knee turned out, a hip dropped, a
        # trunk leant forward are the body's, whichever way it travels (2026-10-16: a backward walk under a
        # pose had both knees turned 40-50 deg in and its hip drop reversed)
        hips = (pos[self.index["thigh_l"], :P] - pos[self.index["thigh_r"], :P]).mean(axis=0)
        self.left = 1.0 if float(np.dot(hips, self.side)) >= 0.0 else -1.0
        self.lside, self.ahead = self.left * self.side, self.left * self.fwd
        # the body's own left-right, flat: its mean hip line - what Stance and a pose's width spread the feet along
        # (across the travel line a diagonal walk's feet stand 55 deg off it, and a side-on pose's width read +64 cm
        # on one of a mirror pair and -41 on the other, 2026-10-16)
        flat_hips = hips - float(np.dot(hips, self.up)) * self.up
        self.across = _unit(flat_hips) if np.linalg.norm(flat_hips) > 1e-9 else self.lside
        steps = np.arange(P) / float(P)
        self.origin = pos[root, 0] + (pos[root, :P] - pos[root, 0] - np.outer(steps, travel)).mean(axis=0)
        self.rot, self.pos = rot[:, :P], pos[:, :P]
        self.pdev = self.pos - (self.origin + np.outer(steps, travel))[None]
        self.wmean = np.stack([mean_rot(self.rot[j]) for j in range(count)])
        self.wlog = log_rot(self.rot @ np.swapaxes(self.wmean, -1, -2)[:, None])
        self._locals()
        self._kinds()
        # a cycle may hold several steps of each foot: every per-foot quantity is a list, one entry a step
        self.steps = dict((s, self._steps(s)) for s in SIDES)
        if len(self.steps["l"]) != len(self.steps["r"]):
            raise Refusal("the left foot steps %d times a cycle and the right %d: a walk alternates its feet"
                          % (len(self.steps["l"]), len(self.steps["r"])))
        self.strides = len(self.steps["l"])
        self.feet = dict((s, max(self.steps[s], key=lambda foot: foot.length)) for s in SIDES)   # the longest
        self.reach = dict((s, self._reach(s)) for s in SIDES)
        self.follows = self._helpers()
        self.world_arms = set(self.index[n] for n in ("upperarm_l", "upperarm_r") if n in self.index)
        self._decompose()
        self.root_mean = (self.pdev[root] @ self.basis.T).mean(axis=0)
        self.pelvis_mean = (self.pdev[self.index["pelvis"]] @ self.basis.T).mean(axis=0)
        bob = self.pdev[self.index["pelvis"]] @ self.up - self.pelvis_mean[2]
        self.low_phase = float(np.argmin(bob)) / P
        self.balance_note = ""
        # the legs' share of the animator's correction of the walk's mean pose (maya_walk.meanpose: the upper
        # body's is in the clip's frames already): the pelvis raised, the feet's spread, each knee's and foot's
        # turn about up - added where a pose's are, giving way to a pose's own at the Pose share
        self.fix = {"height": 0.0, "width": 0.0, "knee": {"l": 0.0, "r": 0.0}, "toe": {"l": 0.0, "r": 0.0}}
        self._masses()
        self._grounds()
        self._legs_and_pelvis()
        self._chest()
        self._placement()
        self.air = dict((side, self._air(side)) for side in SIDES)   # the contacts': after _placement
        self._own_pendulum()
        self._aspect_shapes()

    # -- the decomposition: a regular part and a residual --

    def stride_phases(self, taus):
        """The stride phase (radians) at each source time of `taus`."""
        return np.array([self.stride_phase(float(t)) for t in taus])

    def harmonic_basis(self, taus=None, harmonics=HARMONICS):
        """(len(taus), 1 + 2K): 1, cos k a, sin k a of the stride phase a at source times `taus` (the source's
        whole frames when None)."""
        a = self.stride_phases(np.arange(self.P, dtype=float) if taus is None else taus)
        cols = [np.ones_like(a)]
        for h in range(1, harmonics + 1):
            cols += [np.cos(h * a), np.sin(h * a)]
        return np.stack(cols, axis=1)

    def regular_fit(self, y, taus=None, harmonics=HARMONICS):
        """`y` (len(taus) or P samples, any trailing shape) fitted on the stride harmonics: (fit, coefficients)."""
        y = np.asarray(y, float)
        B = self.harmonic_basis(taus, harmonics)
        flat = y.reshape(len(B), -1)
        coef = np.linalg.lstsq(B, flat, rcond=None)[0]
        return (B @ coef).reshape(y.shape), coef

    def _decompose(self):
        """`decomposed` {(series, joint): (regular (P, 3), residual (P, 3), mean (3,))} for the body series the
        engine samples: the root's and the pelvis's place against the travel line ("pdev"); the pelvis's, the
        head's and the world-held upper arms' world turns ("wlog"); the local turns of the spine, the neck, the
        arms and the fingers ("llog", the joints below a thigh ride their feet and are left out)."""
        self.decomposed = {}
        B = self.harmonic_basis()
        pinv = np.linalg.pinv(B)
        thighs = set(self.index["thigh_" + s] for s in SIDES)
        for series in ("pdev", "wlog", "llog"):
            data = getattr(self, series)
            for j, kind in enumerate(self.kind):
                if series == "pdev":
                    keep = kind in ("root", "pelvis")
                elif series == "wlog":
                    keep = kind in ("pelvis", "head") or j in self.world_arms
                else:
                    keep = (kind in ("spine", "arm", "finger", "local")
                            and not thighs.intersection(self._ancestors(j)))
                if not keep:
                    continue
                x = data[j]
                reg = B @ (pinv @ x)
                self.decomposed[(series, j)] = (reg, x - reg, x.mean(axis=0))

    def _sample(self, series, j, tau, ctx, gain=1.0, axes=None, shift=0.0):
        """The series' sample at source time tau: its mean + gain . (regular - mean) + detail . residual, the
        regular part sampled `shift` frames earlier; `gain` per row of `axes` (3, 3) when given (a scalar else).
        The series itself at gain 1, detail 1, no shift (Catmull-Rom is linear: exactly what it was)."""
        got = self.decomposed.get((series, j))
        d = ctx["k"].get("detail", 1.0) if ctx is not None else 1.0
        plain = d == 1.0 and shift == 0.0 and (np.all(np.asarray(gain) == 1.0))
        if got is None or plain:
            return periodic_cr(getattr(self, series)[j], tau - shift)
        reg, res, mean = got
        r = periodic_cr(reg, tau - shift) - mean
        if axes is not None:
            r = ((r @ axes.T) * np.asarray(gain, float)) @ axes
        else:
            r = r * float(gain)
        return mean + r + d * periodic_cr(res, tau)

    # -- the operators: the shapes they add on, read off the walk (Gait Builder's) --

    def _aspect_shapes(self):
        """The phases the aspects' swings are added in (each its own gait harmonic's, so an added swing grows the
        walk's own), each elbow's hinge in its upper arm, the spine joints the lean spreads over and how far the
        trunk's lean moves for a degree of it."""
        P, idx = self.P, self.index
        phase = np.array([self.stride_phase(float(f)) for f in range(P)])
        pel = self.pdev[idx["pelvis"]]
        bob = _harmonic(pel @ self.up, phase, 2)
        self.aspect_phase = {"bob": bob[1],
                             "sway": _harmonic(pel @ self.lside, phase, 1)[1],
                             "surge": _harmonic(pel @ self.ahead, phase, 2)[1]}
        self.aspect_amp = {"bob": 2.0 * bob[0]}
        double = _harmonic(pel @ self.up, phase, 4)
        # Double bounce: added in phase with the walk's own (twice a step); with next to none, lows at the strikes
        self.aspect_phase["double"] = double[1] if 2.0 * double[0] >= BOB_QUIET else math.pi
        if self.aspect_amp["bob"] < BOB_QUIET:     # the guide's: lowest just after each strike (cos(2a - p) at -1)
            self.aspect_phase["bob"] = 2.0 * math.pi * BOB_LOW_AFTER - math.pi
        self.leg_parts = dict((s, (float(np.linalg.norm(self.lt[idx["calf_" + s]], axis=1).mean()),
                                   float(np.linalg.norm(self.lt[idx["foot_" + s]], axis=1).mean()))) for s in SIDES)
        pel = self.pos[self.index["pelvis"]]
        rise = np.abs(np.diff(pel @ self.up, prepend=float(pel[-1] @ self.up)))
        self.bob_rate = float(np.percentile(rise, 90))      # cm a source frame: what its own hips do
        self.straight_reach = {}
        for s, (l1, l2) in self.leg_parts.items():
            c = math.cos(math.radians(STRAIGHT_KNEE))
            self.straight_reach[s] = math.sqrt(l1 * l1 + l2 * l2 + 2.0 * l1 * l2 * c) / (l1 + l2)
        self.hinge = {}
        self.arm_dir = {}
        self.arm_set =set(j for j, kind in enumerate(self.kind) if kind in ("arm", "finger"))
        for side in SIDES:
            names = ["%s_%s" % (b, side) for b in ("upperarm", "lowerarm", "hand")]
            if not all(n in idx for n in names):
                continue
            up_j, low_j, hand_j = (idx[n] for n in names)
            a = _units(self.pos[low_j] - self.pos[up_j])
            b = _units(self.pos[hand_j] - self.pos[low_j])
            fwd = np.degrees(np.arctan2(a @ self.ahead, -(a @ self.up)))
            bend = np.degrees(np.arccos(np.clip(np.sum(a * b, axis=1), -1.0, 1.0)))
            swing = _harmonic(fwd, phase, 1)
            self.aspect_phase["arm_" + side], self.aspect_amp["arm_" + side] = swing[1], 2.0 * swing[0]
            if 2.0 * swing[0] < ARM_QUIET:      # the guide's: forward as the other foot strikes (left at a = pi)
                self.aspect_phase["arm_" + side] = math.pi if side == "l" else 0.0
            # where the upper arm points in its own axes (to its elbow): Arm out turns it toward its side about
            # the axis across the two, so an arm held forward (a run) still goes out
            self.arm_dir[up_j] = _unit(self.lt[low_j].mean(axis=0))
            self.aspect_phase["elbow_" + side] = _harmonic(bend, phase, 1)[1]
            # the hinge: a x b (turning about it bends the elbow further), in the upper arm's own axes
            n = np.cross(a, b)
            local = np.einsum("fi,fji->fj", n, self.rot[up_j])       # world . R^T: row vectors
            axis = local.sum(axis=0)
            if np.linalg.norm(axis) < 1e-6:          # a straight arm: about the body's side, as it hangs
                axis = np.einsum("i,fji->fj", self.lside, self.rot[up_j]).mean(axis=0)
            self.hinge[low_j] = _unit(axis)
        spine = sorted((int(m.group(1)), j) for j, n in enumerate(self.names)
                       for m in [re.match(r"spine_(\d+)$", n)] if m and idx["pelvis"] in self._ancestors(j))
        self.lean_joints = [j for _, j in spine]
        self.lean_set = set(self.lean_joints)
        top = self.lean_joints[-1] if self.lean_joints else idx["pelvis"]
        r = self.rot[top]
        pitch = log_rot(mean_rot(r).T @ r) @ self.lside        # the world's pitch (aspects._pitch_series)
        self.aspect_phase["chest"] = _harmonic(pitch, phase, 2)[1]
        self.lean_gain = self._lean_gain()

    def _lean_gain(self):
        """How far the trunk's lean (neck_01 against the pelvis, aspects.measure's) moves for a degree of lean
        spread over the spine joints, on the walk's mean frame (the lower joints turn less of the trunk)."""
        idx = self.index
        if not self.lean_joints:
            return 1.0
        neck = idx["neck_01"] if "neck_01" in idx else self.lean_joints[-1]
        chain = self.lean_joints + ([neck] if neck not in self.lean_joints else [])
        pts = dict((j, self.pos[j].mean(axis=0)) for j in chain + [idx["pelvis"]])
        delta = math.radians(1.0) / len(self.lean_joints)

        def angle(p):
            v = p[neck] - p[idx["pelvis"]]
            return math.degrees(math.atan2(float(v @ self.ahead), float(v @ self.up)))
        moved = dict(pts)
        for i, j in enumerate(self.lean_joints):
            pivot = moved[j]
            for k in chain[i + 1:]:
                moved[k] = pivot + turned_about(moved[k] - pivot, self.lside, delta)
        gain = angle(moved) - angle(pts)
        return gain if gain > 0.2 else 1.0

    def aspect_turns(self, j, ctx, rots, a):
        """The aspects' turn of joint j (a world rotation to post-multiply, or None); `a` the stride phase at
        the frame, `rots` the joints so far (a forearm's hinge rides its upper arm)."""
        k = ctx["k"]
        kind, name = self.kind[j], self.names[j]
        rad = math.radians
        if kind == "spine" and j in self.lean_set:
            angle = rad(k["lean_add"]) / self.lean_gain / len(self.lean_joints)
            if j in self.chest_share and k["chest_bounce_add"]:
                angle += (rad(k["chest_bounce_add"]) * self.chest_share[j]
                          * math.cos(2.0 * a - self.aspect_phase["chest"]))
            return exp_rot(angle * self.lside) if angle else None
        if kind == "head":
            return exp_rot(rad(k["nod_add"]) * self.lside) if k["nod_add"] else None
        stem = _stem(name)
        if stem not in ("clavicle", "upperarm", "lowerarm"):
            return None
        side = self._side(j)
        ks = ctx["ks"][side]
        sign = 1.0 if side == "l" else -1.0
        if stem == "clavicle":
            return exp_rot(rad(ks["shoulder_add"]) * sign * self.ahead) if ks["shoulder_add"] else None
        if stem == "upperarm":
            fwd = ks["arm_fwd_add"]
            if ks["arm_swing_add"] and ("arm_" + side) in self.aspect_phase:
                fwd += 0.5 * ks["arm_swing_add"] * math.cos(a - self.aspect_phase["arm_" + side])
            out = ks["arm_out_add"]
            if not fwd and not out:
                return None
            turn = exp_rot(-rad(fwd) * self.lside) if fwd else np.eye(3)
            if out:
                # toward its side about the axis across the arm and the side (the arm forward or hanging alike);
                # an arm pointing along its side already: about the body's front, as it hangs
                axis = self.ahead * sign
                if j in self.arm_dir:
                    across = _cross3(self.arm_dir[j] @ rots[j] @ turn, sign * self.lside)
                    size = math.sqrt(float(across @ across))
                    if size > ARM_OUT_AXIS:
                        axis = across / size
                turn = turn @ exp_rot(rad(out) * axis)
            return turn
        if j not in self.hinge:
            return None
        bend = ks["elbow_add"]
        if ks["elbow_swing_add"] and ("elbow_" + side) in self.aspect_phase:
            bend += ks["elbow_swing_add"] * math.cos(a - self.aspect_phase["elbow_" + side])
        if not bend:
            return None
        return exp_rot(rad(bend) * (self.hinge[j] @ rots[self.parents[j]]))

    def aspects_on(self, k):
        """Any aspect knob of the joints' turns or the pelvis's swings away from 0 (both sides' own included)."""
        return any(k.get(name, 0.0) for name in ASPECT_KNOBS) or any(
            k.get("%s_%s" % (name, s), 0.0) for name in ASPECT_KNOBS if name in SIDED for s in SIDES)

    # -- the source, sampled at any source time tau (whole frames exact) --

    def line(self, tau):
        return self.origin + self.travel * (tau / float(self.P))

    def wrot(self, j, tau, gain=1.0):
        return exp_rot(gain * periodic_cr(self.wlog[j], tau)) @ self.wmean[j]

    def wpos(self, j, tau):
        return periodic_cr(self.pdev[j], tau) + self.line(tau)

    def lrot_at(self, j, tau, gain=1.0):
        return exp_rot(gain * periodic_cr(self.llog[j], tau)) @ self.lmean[j]

    def lt_at(self, j, tau):
        still = self._lt_const.get(j)
        return still if still is not None else periodic_cr(self.lt[j], tau)

    def source_world(self, j, tau):
        return matrix(self.wrot(j, tau), self.wpos(j, tau))

    def summary(self):
        flat = self.travel - np.dot(self.travel, self.up) * self.up
        stance = " ".join("%s %d %%" % (s.upper(), round(100.0 * sum(f.length + 1 for f in self.steps[s]) / self.P))
                          for s in SIDES)
        text = "%s: cycle %d frames (%.2f s), stride %.1f cm, %.2f m/s, stance %s" % (
            self.clip.name, self.P, self.P / self.fps, np.linalg.norm(flat) / (2.0 * self.strides),
            np.linalg.norm(flat) / (self.P / self.fps) / 100.0, stance)
        if self.strides > 1:
            text += " | %d steps of each foot a cycle" % self.strides
        if abs(self.turned) >= 0.05:
            text += " | turned %.1f deg onto its root's facing" % self.turned
        if self.dropped:
            text += " | %d repeated frame%s dropped" % (self.dropped, "" if self.dropped == 1 else "s")
        return text

    # -- the analysis --

    def _locals(self):
        count = len(self.names)
        self.lt = np.zeros_like(self.pos)
        self.lmean = np.tile(np.eye(3), (count, 1, 1))
        self.llog = np.zeros_like(self.pos)
        for j, p in enumerate(self.parents):
            if p < 0:
                continue
            back = np.swapaxes(self.rot[p], -1, -2)
            lrot = self.rot[j] @ back
            self.lt[j] = np.einsum("fi,fij->fj", self.pos[j] - self.pos[p], back)
            self.lmean[j] = mean_rot(lrot)
            self.llog[j] = log_rot(lrot @ self.lmean[j].T)
        # a bone whose place in its parent never changes (most: a rigid skeleton) answers its place without the
        # spline (Gait Builder's speed-up: lt_at was a third of the sampler's calls)
        self._lt_const = dict((j, self.lt[j][0].copy()) for j in range(count)
                              if float(np.ptp(self.lt[j], axis=0).max()) <= LT_STILL)

    def _ancestors(self, j):
        out = []
        p = self.parents[j]
        while p >= 0:
            out.append(p)
            p = self.parents[p]
        return out

    def _kinds(self):
        legs = set("%s_%s" % (b, s) for s in SIDES for b in LEG)
        self.kind, self.lag = [], []
        for j, name in enumerate(self.names):
            above = [self.names[a] for a in self._ancestors(j)]
            if name in ("root", "pelvis"):
                kind = name
            elif name in legs:
                kind = "leg"
            elif name.startswith(HELPER_PREFIXES) or any(a.startswith(HELPER_PREFIXES) for a in above):
                kind = "helper"
            elif re.match(r"(spine|neck)_\d+$", name):
                kind = "spine"
            elif name == "head":
                kind = "head"
            elif _stem(name) in ARM_STEMS:
                kind = "arm"
            elif "hand_l" in above or "hand_r" in above:
                kind = "finger"
            elif self.parents[j] < 0:
                kind = "world"
            else:
                kind = "local"
            self.kind.append(kind)
            self.lag.append(LAG.get(name, LAG.get(_stem(name), 1.0 if kind == "finger" else 0.0)))
        kids = dict((j, []) for j in range(len(self.names)))
        for j, p in enumerate(self.parents):
            if p >= 0:
                kids[p].append(j)
        bfs, queue = [], [j for j, p in enumerate(self.parents) if p < 0]
        while queue:
            j = queue.pop(0)
            bfs.append(j)
            queue.extend(kids[j])
        self.order = [j for j in bfs if self.kind[j] != "helper"] + [j for j in bfs if self.kind[j] == "helper"]
        self.forearms = set(j for j, n in enumerate(self.names) if _stem(n) == "lowerarm")
        self.hand_bones = set(j for j, n in enumerate(self.names) if _stem(n) == "hand")
        self._lag_levels()

    def _lag_levels(self):
        """Which lag knobs shift each joint's series and by what share: {j: ((knob, share, side or None), ...)}
        - the arm chain by its level (clavicle 0.6 x arm_lag, upper arm arm_lag, forearm + elbow_lag, hand and
        below + hand_lag; per side), spine_NN bottom up (torso_lag x i / (N - 1)), the necks torso_lag, the head
        torso_lag + head_lag; a joint under one of them (the jaw, the eyes) as its parent."""
        idx, levels = self.index, {}
        for side in SIDES:
            arm = ("arm_lag", 1.0, side)
            for name, level in (("clavicle", (("arm_lag", 0.6, side),)), ("upperarm", (arm,)),
                                ("lowerarm", (arm, ("elbow_lag", 1.0, side))),
                                ("hand", (arm, ("elbow_lag", 1.0, side), ("hand_lag", 1.0, side)))):
                if "%s_%s" % (name, side) in idx:
                    levels[idx["%s_%s" % (name, side)]] = level
        spine = sorted((int(m.group(1)), j) for j, n in enumerate(self.names)
                       for m in [re.match(r"spine_(\d+)$", n)] if m and idx["pelvis"] in self._ancestors(j))
        for i, (_, j) in enumerate(spine):
            levels[j] = (("torso_lag", i / float(len(spine) - 1) if len(spine) > 1 else 1.0, None),)
        for j, n in enumerate(self.names):
            if re.match(r"neck_\d+$", n):
                levels[j] = (("torso_lag", 1.0, None),)
            elif n == "head":
                levels[j] = (("torso_lag", 1.0, None), ("head_lag", 1.0, None))
        self.lag_levels = {}
        for j in self.order:
            if j in levels:
                self.lag_levels[j] = levels[j]
            elif self.kind[j] in ("arm", "finger", "local") and self.parents[j] in self.lag_levels:
                self.lag_levels[j] = self.lag_levels[self.parents[j]]

    def lags(self, k, ks, frame):
        """Each joint's time shift under knobs k / per side ks, source frames ({j: frames}, only those moved):
        the lag knobs' frames of the new cycle x `frame` (source frames a new frame)."""
        out = {}
        for j, level in self.lag_levels.items():
            d = sum((ks[side] if side else k)[knob] * share for knob, share, side in level)
            if d:
                out[j] = d * frame
        return out

    def _steps(self, side):
        """Every stance of the foot in the cycle, sorted by its start (a cycle may hold several steps of each
        foot): the runs where the slower of its ankle and ball moves less than CONTACT_SHARE of the travel a
        frame; two runs merged when the foot's heel or ball stays within MERGE_HIGH of its lowest across the
        frames between them (a stance sliding a little faster for a while); a run whose middle stands higher
        than that is no stance. Each a Foot."""
        P = self.P
        speeds, low = [], np.zeros(P, bool)
        for name in ("foot_" + side, "ball_" + side):
            p = self.pos[self.index[name]]
            ahead = np.vstack([p[1:], p[:1] + self.travel])
            behind = np.vstack([p[-1:] - self.travel, p[:-1]])
            speeds.append(np.linalg.norm(ahead - behind, axis=1) / 2.0)
            h = p @ self.up
            low |= h <= h.min() + MERGE_HIGH
        slow = np.minimum(speeds[0], speeds[1]) < np.linalg.norm(self.travel) / P * CONTACT_SHARE
        #  a gap where the foot moves faster than the walk travels is a swing, however low it stays: a foot
        #  that shuffles (its toe never 4 cm up) had its four steps joined into one stance (2026-11-05)
        swinging = np.minimum(speeds[0], speeds[1]) >= np.linalg.norm(self.travel) / P * HELD_SHARE
        if slow.all():
            raise Refusal("the %s foot never leaves the ground" % SIDE_WORD[side])
        if not slow.any():
            raise Refusal("the %s foot never stops: no contact to plant it on" % SIDE_WORD[side])
        runs = _runs(slow)
        merged = True
        while merged and len(runs) > 1:
            merged = False
            for i, (a, la) in enumerate(runs):
                b, lb = runs[(i + 1) % len(runs)]
                gap = (b - a - la) % P
                if all(low[(a + la + g) % P] and not swinging[(a + la + g) % P] for g in range(gap)):
                    runs = [r for m, r in enumerate(runs) if m not in (i, (i + 1) % len(runs))]
                    runs = sorted(runs + [(a, la + gap + lb)])
                    merged = True
                    break
        runs = [(on, n) for on, n in runs if low[(on + n // 2) % P]]
        if not runs:
            raise Refusal("the %s foot never stops near the ground: no contact to plant it on" % SIDE_WORD[side])
        out = []
        for on, n in runs:
            length = n - 1
            mid = on + length / 2.0
            coords = periodic_cr(self.pdev[self.index["foot_" + side]], mid) @ self.basis.T
            out.append(Foot(side, on, length, mid, coords))
        return out

    def _step_at(self, side, tau):
        """The step whose stance or the swing after it source time tau is in: (its index, the cycle k, how far
        past its start)."""
        best = None
        for i, foot in enumerate(self.steps[side]):
            k = math.floor((tau - foot.on) / self.P)
            r = tau - foot.on - k * self.P
            if best is None or r < best[2]:
                best = (i, k, r)
        return best

    def side_print(self, side):
        """The foot's footprints' mean place across the travel line (cm, + to the walk's left)."""
        return float(np.mean([foot.coords[1] for foot in self.steps[side]]))

    def print_across(self, step):
        """A footprint's place across the BODY (cm along `across`, + to the body's left)."""
        return float(step.coords[0] * np.dot(self.fwd, self.across) + step.coords[1] * np.dot(self.side, self.across))

    def body_print(self, side):
        """The foot's footprints' mean place across the body (cm along `across`)."""
        return float(np.mean([self.print_across(foot) for foot in self.steps[side]]))

    def stride_phase(self, tau):
        """The stride's phase at source time tau, radians: 2 pi a stride, running linearly between the left
        foot's strikes (its steps' starts) - for one stride a cycle 2 pi (tau - the left strike) / P."""
        ons = [foot.on for foot in self.steps["l"]]
        n, P = len(ons), float(self.P)
        k = math.floor((tau - ons[0]) / P)
        x = tau - k * P
        knots = ons + [ons[0] + P]
        m = max(i for i in range(n) if knots[i] <= x + 1e-12)
        u = (x - knots[m]) / (knots[m + 1] - knots[m])
        return 2.0 * math.pi * (k * n + m + u)

    def _legs_and_pelvis(self):
        """What the legs' and the pelvis's knobs read: each foot's turn in its calf (a mean and logs), the balls,
        the twist's shape (the feet's fore-aft split, demeaned, peak 1) and the hip drop's (a cosine peaking
        LIST_PEAK after the left heel strike), the twist's growth with the step, this walk's own twist and drop
        on those shapes (own_knobs) and the lumbar joints that take the pelvis's added turn back."""
        P, idx = self.P, self.index
        self.foot_rel = {}
        for side in SIDES:
            rel = self.rot[idx["foot_" + side]] @ np.swapaxes(self.rot[idx["calf_" + side]], -1, -2)
            mean = mean_rot(rel)
            self.foot_rel[side] = (mean, log_rot(rel @ mean.T))
        self.balls = dict((idx["ball_" + side], side) for side in SIDES)
        self._knee_planes()
        sep = (self.pos[idx["foot_l"]] - self.pos[idx["foot_r"]]) @ self.fwd
        sep = sep - sep.mean()
        self.split_shape = sep / max(float(np.abs(sep).max()), 1e-9)
        self.list_shape = np.array([self.list_at(float(f)) for f in range(P)])
        flat = self.travel - np.dot(self.travel, self.up) * self.up
        leg = np.mean([np.linalg.norm(self.lt[idx["calf_" + s]], axis=1).mean() +
                       np.linalg.norm(self.lt[idx["foot_" + s]], axis=1).mean() for s in SIDES])
        self.leg_length = float(leg)          # thigh + calf, both sides' mean (Leg match's Froude number)
        self.twist_gain = float(np.linalg.norm(flat)) / (2.0 * self.strides) / float(leg) / STEP_REF
        self.own_twist = self.own_list = 0.0
        twist, drop = self.pelvis_fit(self.clip.worlds)
        self.own_twist, self.own_list = twist / self.twist_gain, drop
        spine = sorted((int(m.group(1)), j) for j, n in enumerate(self.names)
                       for m in [re.match(r"spine_(\d+)$", n)] if m and idx["pelvis"] in self._ancestors(j))
        lumbar = [j for _, j in spine[:len(COUNTER_SHARES)]]
        total = sum(COUNTER_SHARES[:len(lumbar)])
        self.counter = dict((j, share / total) for j, share in zip(lumbar, COUNTER_SHARES))

    def _knee_planes(self):
        """Per side, where the source's leg bends at every source frame - the knee's offset from its
        hip-ankle line, kept in the THIGH's own frame (where it is a near-constant vector) - read only from
        the frames whose knee stands at least KNEE_PLANE_MIN off that line; the straight frames take the
        periodic line between the frames either side (_fill_periodic).

        Read per instant instead, a clip whose leg goes EXACTLY straight (a captured cycle's knee reads
        0.00 deg and 0.0000 cm off the line for two or three frames) has no plane there at all: the
        direction came out of the rounding, flipped ~180 deg from one frame to the next, and since every leg
        rotation is built from it (its normal is `align`'s source frame, and the IK bends toward it) the
        thigh and the calf spun about their own axis by up to 180 deg for a frame - the animator's walk
        twisted its right leg at frame 14 and its left at 29 (2026-10-30). A leg that is never bent enough
        anywhere keeps the travel direction, as the old fallback did."""
        self.knee_dir = {}
        for side in SIDES:
            th, ca, fo = (self.index["%s_%s" % (b, side)] for b in LEG)
            dirs, known = np.zeros((self.P, 3)), np.zeros(self.P, bool)
            for f in range(self.P):
                t = float(f)
                h, kn, a = self.wpos(th, t), self.wpos(ca, t), self.wpos(fo, t)
                e = _unit(a - h)
                b = (kn - h) - np.dot(kn - h, e) * e
                if np.linalg.norm(b) >= KNEE_PLANE_MIN:
                    dirs[f] = _unit(b) @ self.wrot(th, t).T
                    known[f] = True
            if not known.any():
                self.knee_dir[side] = None
                continue
            for k in range(3):
                dirs[:, k] = _fill_periodic(dirs[:, k], known)
            self.knee_dir[side] = dirs

    def knee_plane(self, side, tau, e):
        """Where the source's leg bends at source time tau, perpendicular to `e` (its hip-ankle line):
        _knee_planes' own direction, carried back into the world by the thigh's frame there."""
        dirs = self.knee_dir.get(side)
        out = None
        if dirs is not None:
            v = periodic_cr(dirs, tau % self.P) @ self.wrot(self.index["thigh_" + side], tau)
            v = v - np.dot(v, e) * e
            if np.linalg.norm(v) > 1e-9:
                out = _unit(v)
        if out is None:
            out = _unit(self.fwd - np.dot(self.fwd, e) * e)
        return out

    def _air(self, side):
        """The foot's flights: [(where it leaves the ground, how long it is off it)], source time to
        1/AIR_STEPS of a frame - ONE A STEP: the swing that follows each contact (_placement's `contact` and
        `swing_len`, which is what every other reader of the swing already asks - _just_off, roll_profiles,
        _roll_need), trimmed at both ends to where the foot is clear of the ground (neither heel nor toe
        within GROUND_TOL of its own low). So nothing the flight gates moves a foot that is still touching,
        and a foot that skims its print mid-swing no longer splits its own flight.

        Taken from the heights alone - every stretch off the ground, however short - a foot that comes down
        low and flat dips in and out of that band and the cycle reads SEVERAL flights a step: the animator's
        own walk read seven for its four right steps, two of them 2 frames long (2026-10-30). swing_weight is
        a share of the flight, so over a 2-frame flight it stepped 0 -> 1 -> 0 on consecutive frames, and
        everything it gates - the foot's hang in its calf, the swinging foot's draw-in (_reel_of) - came on
        and off whole in one frame: the ball jumped 9 cm and the knee kinked 13-18 deg a frame where the
        source's own knee ran smooth. A foot that clears the ground only for an instant in a whole swing (one
        that drags) still has a short flight: a share of a window is a rate, and that is as short as the
        window the heights leave. Only where Foot placement found no contacts do the heights decide alone, as
        they always did."""
        contacts = (self.contact or {}).get(side)
        step = 1.0 / float(AIR_STEPS)
        if contacts:
            out = []
            for i, (hs, to) in enumerate(contacts):
                length = self.swing_len[side][i]
                if not 0.0 < length < self.P:      # contacts that abut: a foot that never lifts, no flight
                    continue
                clear = [to + k * step for k in range(int(length * AIR_STEPS) + 1)
                         if not self.down(side, (to + k * step) % self.P)]
                if not clear or clear[-1] - clear[0] < 1.0:
                    continue
                out.append((clear[0] % self.P, clear[-1] - clear[0]))
            return out
        count = self.P * AIR_STEPS
        down = np.array([self.down(side, i * step) for i in range(count)])
        out = []
        for on, run in _runs(~down):
            if run + 1 < AIR_STEPS:
                continue
            out.append((((on - 1) % count) * step, (run + 1) * step))
        return out

    def air_progress(self, side, tau):
        """How far through its flight the foot is at source time tau (0 where it leaves the ground, 1 where it
        lands); None while it is down. The flights are `air`'s, one a step and already trimmed to where the
        foot is clear: the heights are not asked again here, or a foot that skims its print mid-swing reads as
        down for a frame and the swing flickers from one frame to the next (2026-10-30, _air)."""
        for start, length in self.air[side]:
            r = (tau - start) % self.P
            if r < length:
                return r / length
        return None

    def list_at(self, tau):
        """The hip drop's shape at source time tau: 1 with the left hip highest, -1 the right - LIST_PEAK of a
        stride after the left heel strike, once a stride."""
        return math.cos(self.stride_phase(tau) - 2.0 * math.pi * LIST_PEAK)

    def own_knobs(self):
        """The knobs that give this walk back (the defaults are physiological): its own Twist and Hip drop, no
        Foot placement (its own feet, slides and all), its root weaving as it does, its own Chest twist and
        sway, and no Arm, Torso or Head drag (its body as it moves, without the inertia on top)."""
        return {"pelvis_twist": self.own_twist, "pelvis_list": self.own_list, "foot_placement": 0.0,
                "root_sway": 1.0, "chest_twist": self.own_chest_twist, "chest_sway": self.own_chest_sway,
                "arm_drag": 0.0, "torso_drag": 0.0, "head_drag": 0.0}

    def pelvis_fit(self, worlds):
        """The hip line's twist and drop amplitudes (degrees) in a cycle of world matrices (J, n+1, 4, 4): each
        fitted on its shape (least squares, demeaned). The twist turns the forward leg's hip forward, the drop
        lifts the standing hip."""
        n = worlds.shape[1] - 1
        taus = [f * self.P / float(n) for f in range(n)]
        d = worlds[self.index["thigh_l"], :n, 3, :3] - worlds[self.index["thigh_r"], :n, 3, :3]
        across = np.linalg.norm(d - np.outer(d @ self.up, self.up), axis=1)
        twist = np.degrees(np.arctan2(d @ self.fwd, d @ self.lside))
        drop = np.degrees(np.arctan2(d @ self.up, across))
        split = np.array([float(periodic_cr(self.split_shape, t)) for t in taus])
        lists = np.array([self.list_at(t) for t in taus])

        def fit(y, x):
            y, x = y - y.mean(), x - x.mean()
            return float(np.dot(y, x) / np.dot(x, x)) if float(np.dot(x, x)) > 1e-12 else 0.0
        return fit(twist, split), fit(drop, lists)

    def _chest(self):
        """What the chest's knobs read: the shoulder line's turn about up (twist) and its tilt (sway) in the walk,
        each's first harmonic - its amplitude (degrees; the twist per step gain, as Twist's) and its shape (a
        cosine at the walk's own phase; a walk whose chest hardly turns takes the pelvis's shapes, opposite) -
        and the top spine joints that take the chest's added turn (CHEST_SHARES)."""
        idx, P = self.index, self.P
        self.chest_shape, self.own_chest_twist, self.own_chest_sway, self.chest_share = None, 0.0, 0.0, {}
        if "upperarm_l" not in idx or "upperarm_r" not in idx:
            return
        d = self.pos[idx["upperarm_l"]] - self.pos[idx["upperarm_r"]]
        across = np.linalg.norm(d - np.outer(d @ self.up, self.up), axis=1)
        yaw = np.degrees(np.arctan2(d @ self.fwd, d @ self.lside))
        tilt = np.degrees(np.arctan2(d @ self.up, across))
        phase = np.array([self.stride_phase(float(f)) for f in range(P)])     # once a stride

        def harmonic(x):
            x = x - x.mean()
            c = 2.0 / P * float(np.dot(x, np.cos(phase)))
            s = 2.0 / P * float(np.dot(x, np.sin(phase)))
            return math.hypot(c, s), math.atan2(s, c)
        twist, sway = harmonic(yaw), harmonic(tilt)
        if twist[0] < CHEST_STILL:          # no turn of its own: against the pelvis's twist (the feet's split)
            twist = (twist[0], harmonic(-np.array([float(periodic_cr(self.split_shape, f)) for f in range(P)]))[1])
        if sway[0] < CHEST_STILL:
            sway = (sway[0], harmonic(-self.list_shape)[1])
        self.chest_shape = (twist[1], sway[1])
        # the walk's own amplitudes as chest_fit reads a cycle (least squares on the shapes): with strides of
        # uneven length the projection above is not that fit, and own_knobs() must give the walk back exactly
        fitted = self.chest_fit(self.clip.worlds)
        self.own_chest_twist, self.own_chest_sway = fitted[0] / self.twist_gain, fitted[1]
        spine = sorted((int(m.group(1)), j) for j, n in enumerate(self.names)
                       for m in [re.match(r"spine_(\d+)$", n)] if m and idx["pelvis"] in self._ancestors(j))
        top = [j for _, j in spine[-len(CHEST_SHARES):]]
        shares = CHEST_SHARES[-len(top):] if top else ()
        total = sum(shares)
        self.chest_share = dict((j, share / total) for j, share in zip(top, shares))

    def chest_shapes(self, tau):
        """(twist, sway) shapes at source time tau: 1 at the walk's own peak, -1 half a stride on."""
        a = self.stride_phase(tau)
        return math.cos(a - self.chest_shape[0]), math.cos(a - self.chest_shape[1])

    def chest_targets(self, k, ex):
        """(twist, sway) the shoulders turn each way at these knobs, degrees: Chest twist at a normal step x
        the step's gain (as Twist's), Chest sway - both x Spine x Exaggeration."""
        gain = k["spine"] * ex
        return gain * self.twist_gain * k["chest_twist"] * k["stride"], gain * k["chest_sway"]

    def chest_extra(self, tau, k, ex, own=None):
        """The chest's added turn at source time tau (a world rotation vector, None when nothing is added): the
        shoulders brought from their own turn (`own`: (twist, sway) degrees as they stand under these knobs and
        pose - _chest_own; else the walk's own x Spine) to Chest twist and sway, on their shapes."""
        if self.chest_shape is None or own == "off":
            return None
        target = self.chest_targets(k, ex)
        if own is None:
            gain = k["spine"] * ex
            own = (gain * self.twist_gain * self.own_chest_twist, gain * self.own_chest_sway)
        twist, sway = target[0] - own[0], target[1] - own[1]
        # Chest timing: the shoulders' yaw added as a stride harmonic (complex, degrees) _chest_own solved for
        added = own[2] if len(own) > 2 else None
        if abs(twist) < 1e-9 and abs(sway) < 1e-9 and added is None:
            return None
        a, b = self.chest_shapes(tau)
        if added is not None:
            tw = math.radians(abs(added) * math.cos(self.stride_phase(tau) - cmath.phase(added)))
        else:
            tw = math.radians(twist) * a
        return self.left * (tw * -self.up + math.radians(sway) * b * self.fwd)

    def _chest_own(self, times, ctx):
        """(twist, sway): how far the shoulders turn each way under these knobs and pose with nothing added
        (a pose's bent spine turns them otherwise than the walk does), the spine and shoulders alone built
        over the cycle; None without a chest."""
        if self.chest_shape is None:
            return None
        only = set()
        for name in ("upperarm_l", "upperarm_r"):
            j = self.index[name]
            only.update([j] + self._ancestors(j))
        n = len(times) - 1
        worlds = np.tile(np.eye(4), (len(self.names), n + 1, 1, 1))
        ctx["chest_own"] = "off"
        for f, (phi, tau) in enumerate(times):
            worlds[:, f] = self._frame(phi, tau, ctx, 0.0, None, only)[0]
        own = self.chest_fit(worlds)
        before = self.chest_yaw(worlds)
        # once more with the turn added: a bent spine does not take a world turn one for one - what it misses
        # of the target is asked for again (its amplitudes, and the phase Chest timing turns it by)
        ctx["chest_own"] = own
        for f, (phi, tau) in enumerate(times):
            worlds[:, f] = self._frame(phi, tau, ctx, 0.0, None, only)[0]
        got, target = self.chest_fit(worlds), self.chest_targets(ctx["k"], ctx["ex"])
        ctx["chest_own"] = None
        out = (own[0] + got[0] - target[0], own[1] + got[1] - target[1])
        late = math.radians(ctx["k"].get("chest_phase", 0.0))
        if late:
            # the shoulders' yaw a stride harmonic H (complex, degrees: cos(a - arg H) x |H|): the built cycle's
            # without the turn added (B) brought to the target's amplitude and turned `late` later; the turn that
            # adds it asked, its take by the spine measured (the yaw it moved over the yaw asked) and divided out
            ratio = target[0] / own[0] if abs(own[0]) > 1e-6 else 1.0
            want = abs(before) * ratio * cmath.exp(1j * (cmath.phase(before) + late))
            asked = want - before
            ctx["chest_own"] = (own[0], own[1], asked)
            for f, (phi, tau) in enumerate(times):
                worlds[:, f] = self._frame(phi, tau, ctx, 0.0, None, only)[0]
            ctx["chest_own"] = None
            take = (self.chest_yaw(worlds) - before) / asked if abs(asked) > 1e-9 else 1.0
            if 0.3 <= abs(take) <= 3.0:
                asked = asked / take
            out = out + (asked,)
        return out

    def chest_yaw(self, worlds):
        """The shoulder line's yaw's first stride harmonic in a cycle of world matrices: complex, degrees
        (A e^(i phi) for A cos(a - phi), a the stride phase)."""
        n = worlds.shape[1] - 1
        d = worlds[self.index["upperarm_l"], :n, 3, :3] - worlds[self.index["upperarm_r"], :n, 3, :3]
        yaw = np.degrees(np.arctan2(d @ self.fwd, d @ self.lside))
        a = np.array([self.stride_phase(f * self.P / float(n)) for f in range(n)])
        yaw = yaw - yaw.mean()
        return complex(2.0 / n * float(np.dot(yaw, np.cos(a))), 2.0 / n * float(np.dot(yaw, np.sin(a))))

    def chest_fit(self, worlds):
        """The shoulder line's twist and sway amplitudes (degrees) in a cycle of world matrices (J, n+1, 4, 4),
        each fitted on its shape (least squares, demeaned)."""
        n = worlds.shape[1] - 1
        d = worlds[self.index["upperarm_l"], :n, 3, :3] - worlds[self.index["upperarm_r"], :n, 3, :3]
        across = np.linalg.norm(d - np.outer(d @ self.up, self.up), axis=1)
        yaw = np.degrees(np.arctan2(d @ self.fwd, d @ self.lside))
        tilt = np.degrees(np.arctan2(d @ self.up, across))
        shapes = np.array([self.chest_shapes(f * self.P / float(n)) for f in range(n)])

        def fit(y, x):
            y, x = y - y.mean(), x - x.mean()
            return float(np.dot(y, x) / np.dot(x, x)) if float(np.dot(x, x)) > 1e-12 else 0.0
        return fit(yaw, shapes[:, 0]), fit(tilt, shapes[:, 1])

    def pelvis_extra(self, tau, k, ex):
        """The pelvis's added turn at source time tau (a world rotation vector, None when nothing is added):
        Twist and Hip drop against this walk's own, on their shapes, x Pelvis motion x Exaggeration."""
        gain = k["pelvis_rot"] * ex
        twist = self.twist_gain * (k["pelvis_twist"] * k["stride"] - self.own_twist)
        drop = k["pelvis_list"] - self.own_list
        if gain == 0.0 or (twist == 0.0 and drop == 0.0):
            return None
        return gain * self.left * (math.radians(twist) * float(periodic_cr(self.split_shape, tau)) * -self.up
                                   + math.radians(drop) * self.list_at(tau) * self.fwd)

    def _spine_map(self, pose, alpha):
        """Under a pose that bends the spine: per spine joint the matrix taking its turn's axis (in its own
        frame) to the axis that turns about the same WORLD axis as in the walk - a hunched spine still twists
        and sways about the walk's vertical, so the chest keeps counter-turning against the pelvis. The walk's
        and the pose's mean frames: chains of mean locals from the mean pelvis. {} without a bent spine."""
        if pose is None or not pose.get("spine"):
            return {}
        pelvis = self.index["pelvis"]
        src = {pelvis: self.wmean[pelvis]}
        new = {pelvis: self.wmean[pelvis] if "pelvis" not in pose else toward(self.wmean[pelvis], pose["pelvis"], alpha)}
        out = {}
        for j in self.order:
            p = self.parents[j]
            if self.kind[j] != "spine" or p not in src:
                continue
            centre = self.lmean[j] if j not in pose["spine"] else toward(self.lmean[j], pose["spine"][j], alpha)
            src[j], new[j] = self.lmean[j] @ src[p], centre @ new[p]
            out[j] = src[j] @ new[j].T
        return out

    # -- Leg match: a pose's stance against the gait --

    def _heading(self, v):
        """A direction's heading about up (radians): from the walk's forward toward its side axis (its left)."""
        return math.atan2(float(np.dot(v, self.side)), float(np.dot(v, self.fwd)))

    def knee_headings(self):
        """{side: the walk's mean knee heading (radians)} - each frame's knee bend off the hip-ankle line,
        averaged over the cycle."""
        out = {}
        for side in SIDES:
            bends = []
            for f in range(self.P):
                hip, knee, ankle = (self.pos[self.index["%s_%s" % (b, side)]][f] for b in LEG)
                e = _unit(ankle - hip)
                bend = (knee - hip) - np.dot(knee - hip, e) * e
                if np.linalg.norm(bend) > 1e-9:
                    bends.append(_unit(bend))
            out[side] = self._heading(np.mean(bends, axis=0)) if bends else 0.0
        return out

    def toe_headings(self):
        """{side: the walk's toe heading (radians)} - ankle to ball at the foot's longest stance's middle."""
        out = {}
        for side in SIDES:
            mid = self.feet[side].mid
            out[side] = self._heading(self.wpos(self.index["ball_" + side], mid) -
                                      self.wpos(self.index["foot_" + side], mid))
        return out

    def gait_keep(self, k, n):
        """(keep, Fr): how much of a pose's stance a gait at these knobs keeps, 1 / (1 + Fr / GAIT_FROUDE) -
        Fr = v^2 / (g L), the Froude number of the new cycle (its speed after Stride and Tempo, `n` frames; L
        the legs' thigh + calf)."""
        flat = self.travel * k["stride"]
        flat = flat - np.dot(flat, self.up) * self.up
        speed = float(np.linalg.norm(flat)) / (n / self.fps)
        froude = speed * speed / (GRAVITY * self.leg_length)
        return 1.0 / (1.0 + froude / GAIT_FROUDE), froude

    def matched_pose(self, pose, m, keep):
        """The pose (as prepare hands it) with its legs matched to the gait at Leg match `m` (0: as it is, 1:
        matched) - the spec's section 2. A pose standing side-on gives its turn about up (`hips_yaw`) back from
        the pelvis and the lumbar spine takes it (the chest keeps the pose's facing); the knees' and the toes'
        turns are re-read against the pose's own hips, outward, and only their symmetric part (a front and a
        back foot are a stance) is kept, over the walk's own, x `keep`; the width x `keep`."""
        if pose is None or m <= 0.0:
            return pose
        out = dict(pose)
        yaw = float(pose.get("hips_yaw", 0.0))
        if yaw and "pelvis" in pose:
            out["pelvis"] = pose["pelvis"] @ exp_rot(self.up * (-m * yaw))
            if pose.get("spine"):
                out["spine"] = self._spine_takes(pose, m * yaw)
        sign = {"l": 1.0, "r": -1.0}
        # the headings read from the body's own front (a backward walk's knees point near 180 deg off its travel,
        # where the angle wraps: a knee turned out read as turned in, 2026-10-16) - the same turn of the frame
        # about up, so the pose's turns (differences) and the yaw stand as they are
        front = 0.0 if self.left > 0.0 else math.pi
        for key, own in (("knee_turn", self.knee_headings()), ("toe", self.toe_headings())):
            turns = pose.get(key)
            if not turns or any(s not in turns for s in SIDES):
                continue
            own = dict((s, _wrapped(own[s] - front)) for s in SIDES)
            outward = sum(sign[s] * _wrapped(turns[s] + own[s] - yaw) for s in SIDES) / 2.0
            splay = outward - sum(sign[s] * own[s] for s in SIDES) / 2.0
            out[key] = dict((s, (1.0 - m) * turns[s] + m * sign[s] * keep * splay) for s in SIDES)
        if "width" in pose:
            out["width"] = pose["width"] * ((1.0 - m) + m * keep)
        return out

    def _spine_takes(self, pose, yaw):
        """The pose's spine locals once its pelvis has given `yaw` (radians, about up) back: the
        lumbar joints (Twist's counter joints) turn it back in their shares, so every joint above them keeps the
        pose's world turn."""
        cum, done = {}, 0.0
        for j in sorted(self.counter, key=lambda j: len(self._ancestors(j))):
            done += self.counter[j]
            cum[j] = done
        pel = self.index["pelvis"]
        turn = lambda j: exp_rot(self.up * (-yaw * (1.0 - min(cum.get(j, 0.0 if j == pel else 1.0), 1.0))))
        return self._torso_turned(pose, turn)[1]

    def _torso_turned(self, pose, turn):
        """(pelvis, spine locals) of the pose with each of its torso bones' WORLD rotation turned by `turn(j)` (a
        world rotation post-multiplied) - the pelvis (the walk's mean when the pose has none) and every spine
        joint; a joint the pose gives no local for stands on the walk's mean local."""
        pel = self.index["pelvis"]
        given = pose.get("spine") or {}
        base = pose["pelvis"] if "pelvis" in pose else self.wmean[pel]
        old, new, spine = {pel: base}, {pel: base @ turn(pel)}, dict(given)
        for j in self.order:
            p = self.parents[j]
            if self.kind[j] != "spine" or p not in old:
                continue
            old[j] = given.get(j, self.lmean[j]) @ old[p]
            new[j] = old[j] @ turn(j)
            local = new[j] @ new[p].T
            if j in given or float(np.abs(local - old[j] @ old[p].T).max()) > 1e-12:
                spine[j] = local
        return new[pel], spine

    def leaned_pose(self, pose, gain):
        """The pose with the walk's own forward lean put back on its torso (Gait lean `gain`): each torso bone the
        pose replaces turned forward about the walk's side axis by the walk's mean pitch over its rest
        (`gait_lean`, from prepare) - a forward one x `lean_room` (the room the pose leaves to LEAN_LIMIT), a
        backward one as it is. A pose without its pelvis stands on the walk's, which leans already: its spine
        takes only its own lean over the pelvis's."""
        if pose is None or gain <= 0.0 or not pose.get("gait_lean"):
            return pose
        thetas, room = pose["gait_lean"], float(pose.get("lean_room", 1.0))
        lean = lambda j: gain * (thetas.get(j, 0.0) * (room if thetas.get(j, 0.0) > 0.0 else 1.0))
        pel, head = self.index["pelvis"], self.index.get("head")
        out = dict(pose)
        if "pelvis" in pose or pose.get("spine"):
            own = "pelvis" in pose
            under = 0.0 if own else lean(pel)
            turn = lambda j: exp_rot(self.lside * ((lean(pel) if own else 0.0) if j == pel else lean(j) - under))
            pelvis, spine = self._torso_turned(pose, turn)
            if own:
                out["pelvis"] = pelvis
            if pose.get("spine"):
                out["spine"] = spine
        if "head" in pose and head is not None:
            out["head"] = pose["head"] @ exp_rot(self.lside * lean(head))
        return out

    def _placement(self):
        """What Foot placement reads, per foot a list - one contact a step (in source time, hs in [0, P), to = hs
        + its length): the stretch around the step with its heel (the ankle) or its ball within CONTACT_TOL of
        that step's own low, at least the step itself; the pivot's weight there (0 the heel, 1 the ball:
        whichever is down alone, a smoothstep where both are); the other foot's strike it hands over to (the
        nearest to its lift-off) and the double support there; how much longer the foot stays down at its
        lift-off (rolling over its ball) for both feet to be down DOUBLE_SUPPORT of a stride at every step, at
        most EXTEND_MAX of the swing after it. Per foot, from its longest contact: the heel's ground point in
        the foot's frame (under the ankle at the ball's height, HEEL_BACK of the foot behind), the foot's side
        and its sole's up. And the joints below each thigh, which ride their foot's clock."""
        P, G, idx = self.P, LOCK_STEPS, self.index
        cells = P * G
        grid = np.arange(cells) / float(G)
        self.contact, self.pivot, self.heel_loc, self.placement_note = {}, {}, {}, ""
        self.foot_side, self.sole_up, self.swing_len, self.handoff = {}, {}, {}, {}
        self.flat_after = {}
        self.extend = dict((side, [{"hs": 0.0, "to": 0.0} for _ in self.steps[side]]) for side in SIDES)
        self.double_src = {}
        self.leg_side = {}
        for j, kind in enumerate(self.kind):
            for side in SIDES:
                if kind not in ("leg", "helper") and idx["thigh_" + side] in self._ancestors(j):
                    self.leg_side[j] = side
        for side in SIDES:
            heights = [np.array([float(periodic_cr(self.pos[idx[name]] @ self.up, t)) for t in grid])
                       for name in ("foot_" + side, "ball_" + side)]
            # how fast the heel (the ankle) and the ball move along the ground there, cm a frame: a point near
            # the floor that travels is skimming, not planted
            speeds = []
            for name in ("foot_" + side, "ball_" + side):
                flat_dev = self.pdev[idx[name]] - np.outer(self.pdev[idx[name]] @ self.up, self.up)
                ground = self.travel - np.dot(self.travel, self.up) * self.up
                moved = np.array([periodic_cr(flat_dev, t + 0.5 / G) - periodic_cr(flat_dev, t - 0.5 / G)
                                  for t in grid]) * G + ground / P
                speeds.append(np.linalg.norm(moved, axis=1))
            held_speed = HELD_SHARE * float(np.linalg.norm(self.travel - np.dot(self.travel, self.up) * self.up)) / P
            steps = self.steps[side]
            contacts, pivots, anywhere = [], [], np.zeros(cells, bool)
            for foot in steps:
                window = [int(round(foot.on * G)) + c for c in range(int(round(foot.length * G)) + 1)]
                downs = []
                for h in heights:
                    low = min(float(h[c % cells]) for c in window)
                    downs.append(h <= low + CONTACT_TOL)
                either = downs[0] | downs[1]
                anywhere |= either
                # the contact grows out of its step only while the point that is down is held there
                held = ((downs[0] & (speeds[0] <= held_speed)) | (downs[1] & (speeds[1] <= held_speed)))
                c0 = int(round(foot.mid * G))
                left, right = c0 - window[0], window[-1] - c0
                if either[c0 % cells]:            # out along the stretch down, never into another step
                    i = steps.index(foot)
                    before, after = steps[i - 1], steps[(i + 1) % len(steps)]
                    lo = int(round((before.on + before.length) * G))
                    while lo > window[0]:
                        lo -= cells
                    hi = int(round(after.on * G))
                    while hi <= window[-1]:
                        hi += cells
                    a = 0
                    while c0 - a - 1 > lo and held[(c0 - a - 1) % cells] and a < cells:
                        a += 1
                    b = 0
                    while c0 + b + 1 < hi and held[(c0 + b + 1) % cells] and b < cells:
                        b += 1
                    left, right = max(left, a), max(right, b)
                start, length = c0 - left, left + right + 1
                hs = (start % cells) / float(G)
                contacts.append((hs, hs + (length - 1) / float(G)))
                spans = []
                for down in downs:
                    on = [i for i in range(length) if down[(start + i) % cells]]
                    spans.append((on[0] / float(G), on[-1] / float(G)) if on else None)
                heel, ball = spans
                lam_in = 0.0 if ball is None or (heel is not None and heel[0] <= ball[0]) else 1.0
                lam_out = 1.0 if heel is None or (ball is not None and ball[1] >= heel[1]) else 0.0
                both = (max(heel[0], ball[0]), min(heel[1], ball[1])) if heel and ball else (0.0, 0.0)
                pivots.append((lam_in, lam_out, both[0], max(both[1], both[0])))
            if anywhere.all():
                self.placement_note = "the %s foot never lifts" % SIDE_WORD[side]
                return
            self.contact[side], self.pivot[side] = contacts, pivots
            self.swing_len[side] = [(contacts[(i + 1) % len(contacts)][0] - to) % P or float(P)
                                    for i, (hs, to) in enumerate(contacts)]
            hs, to = max(contacts, key=lambda c: c[1] - c[0])
            mid = 0.5 * (hs + to)
            rot = self.wrot(idx["foot_" + side], mid)
            reach = self.wpos(idx["ball_" + side], mid) - self.wpos(idx["foot_" + side], mid)
            rise = float(np.dot(reach, self.up))
            self.heel_loc[side] = (rise * self.up - HEEL_BACK * (reach - rise * self.up)) @ rot.T
            # the flat foot's side and its sole's up, in the foot's own frame: the roll turns about the foot's
            # own side (a near-vertical foot's flat direction is no axis: it flips as the foot passes upright)
            self.foot_side[side] = _unit(np.cross(self.up, reach - rise * self.up)) @ rot.T
            self.sole_up[side] = self.up @ rot.T
        for side in SIDES:     # each strike's foot-flat: the first moment the sole lies within FLAT_TOL of the floor
            fo, flats = self.index["foot_" + side], []
            for hs, to in self.contact[side]:
                steps = np.arange(0.0, to - hs + 1e-9, 0.125)
                pitch = [abs(self.sole_pitch(side, self.wrot(fo, hs + r))) for r in steps]
                flat = [r for r, p in zip(steps, pitch) if p <= math.radians(FLAT_TOL)]
                flats.append(float(flat[0]) if flat else float(steps[int(np.argmin(pitch))]))
            self.flat_after[side] = flats
        wrap = lambda d: (d + 0.5 * P) % P - 0.5 * P
        stride = P / float(self.strides)
        for s, o in (("l", "r"), ("r", "l")):     # the trailing foot stays longer: it can roll over its ball
            self.handoff[s], self.double_src[s] = [], []
            for i, (hs, to) in enumerate(self.contact[s]):
                j = min(range(len(self.contact[o])), key=lambda m: abs(wrap(to - self.contact[o][m][0])))
                ds = wrap(to - self.contact[o][j][0])
                self.handoff[s].append(j)
                self.double_src[s].append(ds)
                # a run's flight (both feet up) is its gait, not a gap to close: its contacts are not grown
                # (grown to a walk's double support, HavyRun's 6-frame stances took 8 frames more - its swings
                # crushed into the rest, a swinging foot grazed the floor and the pelvis sank 64 cm, 2026-10-13)
                self.extend[s][i]["to"] = 0.0 if self.is_flight(ds) else max(0.0, DOUBLE_SUPPORT * stride - ds)
        for side in SIDES:
            for i, ext in enumerate(self.extend[side]):
                grow, room = ext["hs"] + ext["to"], EXTEND_MAX * self.swing_len[side][i]
                if grow > room:
                    self.extend[side][i] = dict((end, v * room / grow) for end, v in ext.items())

    def is_flight(self, ds):
        """Whether a handoff's double support `ds` (source frames; negative: both feet up) is a run's flight."""
        return ds < -RUN_FLIGHT * self.P / float(self.strides)

    def _contact_at(self, side, t):
        """The contact foot time t is in, or the swing after it: (its index, how far past its strike)."""
        best = None
        for i, (hs, to) in enumerate(self.contact[side]):
            r = (t - hs) % self.P
            if best is None or r < best[1]:
                best = (i, r)
        return best

    def placed_contact(self, side, placement, grown=None):
        """The foot's contacts [(strike, lift-off)] in the new cycle's own time (source frames) at Foot
        placement `placement`: grown at their ends - by `grown` ({side: [{"hs", "to"} a contact]}, source
        frames: an evaluate's), else by the walk's own targets x `placement`."""
        out = []
        for i, (hs, to) in enumerate(self.contact[side]):
            if grown is not None:
                g = grown[side][i]
                out.append((hs - g["hs"], to + g["to"]))
            else:
                ext = self.extend[side][i]
                out.append((hs - placement * ext["hs"], to + placement * ext["to"]))
        return out

    def double_support(self, placement, grown=None):
        """Both feet down at each step, frames of the source's length: {"l": from the left's lift-off back to
        the right's strike it hands over to, "r": the other} - the least of a foot's steps (negative: a
        flight)."""
        P, out = float(self.P), {}
        for s, o in (("l", "r"), ("r", "l")):
            mine, theirs = self.placed_contact(s, placement, grown), self.placed_contact(o, placement, grown)
            out[s] = min((to - theirs[j][0] + 0.5 * P) % P - 0.5 * P
                         for (hs, to), j in zip(mine, self.handoff[s]))
        return out

    def foot_time(self, side, tau, placement, grown=None):
        """The foot's own source time at body time tau. Without Foot placement the walk's own; with it each
        contact plays over its placed_contact (slower) and the swings quicken: a periodic monotone C1 cubic
        through every (strike', strike) and (lift-off', lift-off), each knot's slope the harmonic mean of its
        two stretches'."""
        if self.placement_note or (placement <= 0.0 and grown is None):
            return tau
        contacts, placed = self.contact[side], self.placed_contact(side, placement, grown)
        if all(a == b for a, b in zip(contacts, placed)):
            return tau
        P = float(self.P)
        xs = [x for c in placed for x in c]
        ys = [y for c in contacts for y in c]
        xs.append(xs[0] + P)
        ys.append(ys[0] + P)
        n = len(xs) - 1
        d = [(ys[m + 1] - ys[m]) / (xs[m + 1] - xs[m]) for m in range(n)]
        slope = [2.0 * d[m - 1] * d[m] / (d[m - 1] + d[m]) for m in range(n)]
        slope.append(slope[0])
        k = math.floor((tau - xs[0]) / P)
        x = tau - k * P
        m = max(i for i in range(n) if xs[i] <= x + 1e-12)
        value = ys[m] + _hermite(x - xs[m], xs[m + 1] - xs[m], ys[m + 1] - ys[m], slope[m], slope[m + 1])
        return k * P + value

    def planted(self, side, t, ctx):
        """Whether the foot holds the pelvis down at foot time t: in a contact under Foot placement (the lock's
        window), else on or near the ground (down)."""
        if ctx["placement"] <= 0.0:
            return self.down(side, t)
        i, r = self._contact_at(side, t)
        hs, to = self.contact[side][i]
        return r <= to - hs

    def _just_off(self, side, t, ctx):
        """Whether the foot (foot time t) has just left the ground under Foot placement: in the first
        SWING_EASE of a swing. Its leg, straight at the lift-off of a contact held longer, would stop dead at
        its reach as the body moves on; such a foot holds the pelvis down a little (AIR_HOLD), so the leg
        straightens into the lift-off and bends out of it."""
        if ctx["placement"] <= 0.0:
            return False
        i, r = self._contact_at(side, t)
        hs, to = self.contact[side][i]
        r -= to - hs
        return 0.0 < r <= SWING_EASE * self.swing_len[side][i]

    def ground_factor(self, side, k):
        """How many times its own a contact lasts (Ground time) under knobs k: ground_time, or duty's share of a
        stride over the walk's own mean contact."""
        duty = float(k.get("duty", 0.0))
        if duty <= 0.0 or not self.contact.get(side):
            return float(k["ground_time"])
        own = float(np.mean([to - hs for hs, to in self.contact[side]]))
        return duty * self.P / float(self.strides) / max(own, 1e-6)

    def _gt(self, ctx, side):
        """Ground time's factor for side in this evaluation (ctx["gt"]), else the knob's."""
        got = (ctx.get("gt") or {}).get(side)
        if got is not None:
            return got
        return ((ctx.get("ks") or {}).get(side) or ctx.get("k") or DEFAULTS)["ground_time"]

    def _clock(self, side, tau, ctx):
        """The foot's own source time at body time tau in this cycle (Foot placement's clock)."""
        return self.foot_time(side, tau, ctx["placement"], ctx.get("grown"))

    def _growth(self, ctx):
        """How much longer each foot stays down in this cycle at each lift-off (source frames, a contact): the
        walk's own target (DOUBLE_SUPPORT of a stride at every step) x Foot placement, cut back to as long as
        the trailing leg - rolled over its ball - still reaches the hip (the knobs' own, before Balance carries
        it) at its lift-off AND over the first SWING_EASE of its swing - a foot held longer leaves from further
        behind and its swing starts there - as well as it does in the walk's own (AIR_HOLD more: a foot just
        off the ground holds the pelvis down that much); never so short that both feet are off the ground (at
        least a frame of the new cycle with both down), at most EXTEND_MAX of its swing."""
        P, v = float(self.P), ctx["placement"]
        plain = dict(ctx, balance=0.0)        # the knobs' own hip: Balance never retimes the feet
        grown = {}
        ctx["ground"] = {}
        for side in SIDES:
            th, ca, fo = (self.index["%s_%s" % (b, side)] for b in LEG)
            out, asked = [], []
            ks = ctx["ks"][side] if "ks" in ctx else ctx["k"]
            ground, duty = ks["ground_time"], float(ks.get("duty", 0.0))
            for i, (hs, to) in enumerate(self.contact[side]):
                ds = self.double_src[side][i]
                room = EXTEND_MAX * self.swing_len[side][i]
                force = (ctx["ks"][side] if "ks" in ctx else ctx["k"]).get("double_force", 1.0)
                least = 0.0 if self.is_flight(ds) else min(room, force * v * max(0.0, ctx["frame"] - ds))
                most = max(least, min(room, v * self.extend[side][i]["to"]))
                window = SWING_EASE * self.swing_len[side][i]

                def short(e):
                    test = {side: [{"hs": 0.0, "to": e if m == i else 0.0} for m in range(len(self.contact[side]))],
                            OTHER[side]: [{"hs": 0.0, "to": 0.0} for _ in self.contact[OTHER[side]]]}
                    worst = -1e9
                    for k in range(GROWTH_SAMPLES + 1):
                        tau = to + e + window * k / float(GROWTH_SAMPLES)
                        t = self.foot_time(side, tau, v, test)
                        rot, ankle = self._foot_free(side, t, ctx)
                        ankle = ankle + self._lock_at(side, t, ctx)
                        limit = self._soft_from(side, t, ctx, ctx.get("reach", self.reach)[side]) * (
                            np.linalg.norm(self.lt_at(ca, t)) + np.linalg.norm(self.lt_at(fo, t)))
                        pelvis_rot, pelvis_pos = self._body(tau / P, tau, plain)["pelvis"]
                        hip = self.lt_at(th, tau) @ pelvis_rot + pelvis_pos
                        rolled = self._rolled(side, t, rot, ankle, hip, limit, ctx)[1]
                        worst = max(worst, float(np.linalg.norm(rolled - hip)) - limit)
                    return worst
                allowed = max(0.0, short(0.0)) + 1e-6
                if short(most) <= allowed:
                    e = most
                elif short(least) > allowed:
                    e = least
                else:                                 # the longest that still reaches: bisected to 1/LOCK_STEPS
                    lo, hi = least, most
                    while hi - lo > 1.0 / LOCK_STEPS:
                        mid = 0.5 * (lo + hi)
                        lo, hi = (mid, hi) if short(mid) <= allowed else (lo, mid)
                    e = lo
                # Ground time: the contact this many times as long, its lift-off moved past what Foot placement
                # grew - asked for, so not cut back to the walk's reach: the trailing leg stretches, the foot
                # rolls further onto its toes (_roll_cost) and the pelvis sinks where even that falls short. A
                # longer stance takes its swing's time, at most GROUND_ROOM of it; a shorter one keeps half its
                # contact and, at Foot placement, a frame of both feet down.
                length, own = to - hs + 1.0, e
                floor = -0.5 * (to - hs)
                if v > 0.0:
                    floor = floor if self.is_flight(ds) else max(floor, ctx["frame"] - ds)
                if duty > 0.0:     # Ground time's share of a stride: each contact by the factor that gives it on average
                    factor = duty * P / float(self.strides) / float(np.mean([b - a for a, b in self.contact[side]]))
                    want = (factor - 1.0) * (to - hs)
                    e = min(max(want, floor), GROUND_ROOM * self.swing_len[side][i])
                    asked.append((duty, (to - hs + e) * self.strides / P))     # asked, held (share of a stride)
                    out.append({"hs": 0.0, "to": e})
                    continue
                ask = (ground - 1.0) * length
                if ask > 0.0:
                    e = max(e, min(GROUND_ROOM * self.swing_len[side][i], e + ask))
                elif ask < 0.0:
                    e = max(floor, min(e, e + ask))
                out.append({"hs": 0.0, "to": e})
                asked.append((ground, 1.0 + (e - own) / length))     # asked, held (x the contact)
            grown[side] = out
            ctx["ground"][side] = asked
        return grown

    def _pivot_weight(self, side, i, r):
        """How far the planted foot has rolled onto its ball, r frames into its contact i (0 the heel, 1 the
        ball)."""
        lam_in, lam_out, a, b = self.pivot[side][i]
        if r <= a or b <= a:
            return lam_in if r <= a else lam_out
        if r >= b:
            return lam_out
        u = (r - a) / (b - a)
        return lam_in + (lam_out - lam_in) * u * u * (3.0 - 2.0 * u)

    def _pivots(self, side, t, ctx):
        """The planted foot's heel and ball ground points at foot time t (the foot as the new cycle has it)."""
        rot, ankle = self._foot_free(side, t, ctx)
        ball = self.lt_at(self.index["ball_" + side], t) @ rot + ankle
        return ankle + self.heel_loc[side] @ rot, ball

    def _locks(self, ctx):
        """Per foot and contact the lock, in foot time: the ankle's shift along the ground that holds the foot's
        pivot (the heel rolling onto the ball) still across the contact, held where the walk's weight on it
        sits on average (zero on the load-weighted mean); across the swing after it a cubic from its
        lift-off's shift to the next contact's strike's whose end slopes cancel the pivot's own speed there, so
        the foot lifts and lands without sliding. Scaled by Foot placement. Returns ({side: [(hs, A, offsets,
        shifts, slope at its lift-off, slope at its strike)] a contact}, the longest slide held, cm)."""
        flat = lambda v: v - np.dot(v, self.up) * self.up
        G, v = LOCK_STEPS, ctx["placement"]
        locks, slide = {}, 0.0
        skim = float(ctx["k"].get("lock_skim", 0.0))
        ref = float(np.linalg.norm(flat(self.travel))) * ctx["k"]["stride"] / float(self.P)

        def held(d, dt):
            """The share of a pivot's move `d` over `dt` frames the lock holds back (1 a still foot's)."""
            if skim <= 0.0 or ref <= 1e-9 or dt <= 1e-12:
                return 1.0
            u = min(max((float(np.linalg.norm(d)) / dt / ref - LOCK_SLOW) / (LOCK_FAST - LOCK_SLOW), 0.0), 1.0)
            return 1.0 - skim * u * u * (3.0 - 2.0 * u)
        for side in SIDES:
            locks[side] = []
            for c, (hs, to) in enumerate(self.contact[side]):
                A = to - hs
                inside = [i / float(G) - hs for i in range(int(math.floor(hs * G)) + 1, int(math.ceil(to * G)))]
                offs = [0.0] + [r for r in inside if 1e-9 < r < A - 1e-9] + [A]
                points = [self._pivots(side, hs + r, ctx) for r in offs]
                lams = [self._pivot_weight(side, c, r) for r in offs]
                shifts = [np.zeros(3)]
                for i in range(len(offs) - 1):
                    lm = 0.5 * (lams[i] + lams[i + 1])
                    moved = (1.0 - lm) * (points[i + 1][0] - points[i][0]) + lm * (points[i + 1][1] - points[i][1])
                    d = flat(moved)
                    shifts.append(shifts[-1] - d * held(d, offs[i + 1] - offs[i]))
                shifts = np.array(shifts)
                slide = max(slide, float(np.linalg.norm(shifts, axis=1).max()))
                # held where the walk's weight on the foot sits on average: the pressure (and Balance) stay the walk's
                load = np.array([max(float(periodic_cr(self.ground["foot_" + side], hs + r)),
                                     float(periodic_cr(self.ground["ball_" + side], hs + r))) for r in offs])
                span = np.gradient(np.array(offs)) * np.clip(load, 0.0, 1.0)
                shifts -= (span[:, None] * shifts).sum(axis=0) / max(float(span.sum()), 1e-9)
                h = 1.0 / G
                speed = []
                for r, lam in ((0.0, lams[0]), (A - h, lams[-1])):
                    (h0, b0), (h1, b1) = self._pivots(side, hs + r, ctx), self._pivots(side, hs + r + h, ctx)
                    d = flat((1.0 - lam) * (h1 - h0) + lam * (b1 - b0))
                    speed.append(d / h * held(d, h))
                locks[side].append((hs, A, np.array(offs), v * shifts, -v * speed[1], -v * speed[0]))
        return locks, slide

    def _lock_at(self, side, t, ctx):
        """The lock's shift of the ankle at foot time t (zero without Foot placement)."""
        locks = ctx["locks"].get(side)
        if not locks:
            return 0.0
        i, r = self._contact_at(side, t)
        hs, A, offs, shifts, out, _ = locks[i]
        if r <= A:
            return np.array([np.interp(r, offs, shifts[:, c]) for c in range(3)])
        after = locks[(i + 1) % len(locks)]
        length = self.swing_len[side][i]
        u = (r - A) / length
        start, end, back = shifts[-1], after[3][0], after[5]
        return (start + (3.0 * u * u - 2.0 * u ** 3) * (end - start)
                + (u ** 3 - 2.0 * u * u + u) * length * out + (u ** 3 - u * u) * length * back)

    def _foot_free(self, side, t, ctx):
        """The new foot at foot time t before the lock: foot_target and the pose's toe-out. Kept for the
        evaluation (ctx["_feet"]): the balance rounds, the lock and the growth ask for the same feet again and
        again (Gait Builder's speed-up: a third of the calls were repeats)."""
        kept = ctx.setdefault("_feet", {})
        key = (side, t)
        got = kept.get(key)
        if got is not None:
            return got[0].copy(), got[1].copy()
        k = ctx["ks"][side] if "ks" in ctx else ctx["k"]
        rot, ankle = self.foot_target(side, t, k["stride"], k["stance"], ctx["spread"], k["lift"] * ctx["ex"],
                                      k["swing_out"], k["detail"])
        toe = ctx["turns"][side][1]
        out = ((rot @ exp_rot(self.up * toe) if toe else rot), ankle)
        kept[key] = out
        return out[0].copy(), out[1].copy()

    def _foot(self, side, tau, ctx):
        """The new foot at body time tau: (world rotation, ankle, the foot's own time)."""
        t = self._clock(side, tau, ctx)
        rot, ankle = self._foot_free(side, t, ctx)
        return rot, ankle + self._lock_at(side, t, ctx), t

    def _roll_frame(self, side, t, rot, ankle, sense):
        """The roll's geometry for the foot (rot, ankle) at foot time t: (pivot, the turn's axis) - over its
        ball (sense +1, heel up) or back on its heel (sense -1, toes up); None for a foot pointing straight
        down."""
        pivot = (self.lt_at(self.index["ball_" + side], t) @ rot + ankle if sense > 0.0
                 else ankle + self.heel_loc[side] @ rot)
        axis = self.foot_side[side] @ rot             # the foot's own side, level
        axis = axis - np.dot(axis, self.up) * self.up
        if np.linalg.norm(axis) < 1e-6:
            return None
        return pivot, _unit(axis)

    def sole_pitch(self, side, rot, axis=None):
        """How far the foot (world rotation `rot`) stands off the ground about its side: radians, + heel up,
        - toes up. `axis` the foot's level side (else read off rot)."""
        if axis is None:
            axis = self.foot_side[side] @ rot
            axis = axis - np.dot(axis, self.up) * self.up
            if np.linalg.norm(axis) < 1e-6:
                return 0.0
            axis = _unit(axis)
        n = self.sole_up[side] @ rot
        n = n - np.dot(n, axis) * axis
        return math.atan2(float(np.dot(n, np.cross(axis, self.up))), float(np.dot(n, self.up)))

    def _sole_lift(self, side, rot, axis, sense):
        """(how far the foot (rot) already stands off the ground about its side `axis` in the roll's sense -
        heel up for +1, toes up for -1 - and the sole's limit there), radians."""
        heel_up = self.sole_pitch(side, rot, axis)
        return (heel_up, math.radians(SOLE_HEEL_UP)) if sense > 0.0 else (-heel_up, math.radians(SOLE_TOES_UP))

    def _sole_room(self, side, rot, axis, sense):
        """How much further (radians) the foot (rot) may roll about its side `axis` before its sole stands
        SOLE_HEEL_UP off the ground (heel up, sense +1) or SOLE_TOES_UP (toes up, -1)."""
        lift, limit = self._sole_lift(side, rot, axis, sense)
        return max(0.0, limit - lift)

    def _sole_eased(self, side, rot, axis, sense, angle):
        """The roll `angle` eased into the sole's limit: the sole's lift after the roll saturates smoothly
        (the last SOLE_EASE degrees below the limit approach it exponentially), so a roll running into the
        limit slows down rather than stopping dead."""
        lift, limit = self._sole_lift(side, rot, axis, sense)
        width = math.radians(SOLE_EASE)
        knee = limit - width
        x = lift + angle
        if x > knee:
            x = knee + width * (1.0 - math.exp(-(x - knee) / width))
        return max(0.0, x - lift)

    def _roll_cost(self, side, t, rot, ankle, hip, limit, ctx, sense):
        """The roll about the ball (sense +1, heel up, up to ROLL_BALL) or the heel (-1, toes up, up to
        ROLL_HEEL) that best trades its angle against how far the leg falls short of the hip: the least of
        ROLL_COST . angle^2 + shortfall^2 (radians). Unlike the least roll that reaches, it moves smoothly as
        the foot moves - where rolling barely helps, the least reaching roll leapt from 0 to 12 deg for a
        3 mm shortfall; this one stays small and the pelvis covers the rest."""
        geometry = self._roll_frame(side, t, rot, ankle, sense)
        if geometry is None:
            return 0.0
        pivot, axis = geometry
        # Ground time past 1 stretches the trailing leg: its foot may stand that much higher on its toes
        ks = (ctx.get("ks") or {}).get(side) or ctx.get("k") or DEFAULTS
        knob = self._gt(ctx, side)
        stretch = max(1.0, knob) if sense > 0.0 else 1.0
        # Foot flat: a foot on the ground after its strike stays flat on it - rolled back on its heel for a leg
        # that falls short (a raised pelvis) its toes stood up off the floor and wavered (2026-10-16, a sword
        # pose); at 1 it does not, the pelvis's drop reaches instead
        flat = 1.0 - min(max(float(ks.get("foot_flat", 0.0)), 0.0), 1.0) if sense < 0.0 else 1.0
        cap = math.radians(ROLL_BALL * stretch if sense > 0.0 else ROLL_HEEL) * ctx["placement"] * flat
        most = min(2.0 * cap, self._sole_room(side, rot, axis, sense))     # searched past the cap, eased into it
        if most <= 0.0 or cap <= 0.0:
            return 0.0
        f = np.cross(axis, self.up)
        a = ankle - pivot
        x, y = float(np.dot(a, f)), float(np.dot(a, self.up))
        lat = a - x * f - y * self.up
        p = x * f + y * self.up
        q = sense * (y * f - x * self.up)            # where the ankle goes as the foot rolls (heel up / toes up)
        c0 = pivot + lat - hip
        # |ankle(th) - hip|^2 = |c0|^2 + |p|^2 + alpha cos th + beta sin th
        base = float(np.dot(c0, c0) + np.dot(p, p))
        alpha, beta = 2.0 * float(np.dot(c0, p)), 2.0 * float(np.dot(c0, q))

        def cost(th):
            reach = np.sqrt(np.maximum(base + alpha * np.cos(th) + beta * np.sin(th), 0.0))
            short = np.maximum(reach - limit, 0.0)       # eased in over ROLL_SOFT: a roll starts and ends gently
            short = np.where(short < ROLL_SOFT, short * short / (2.0 * ROLL_SOFT), short - 0.5 * ROLL_SOFT)
            return ROLL_COST * th * th + short * short
        def cost1(th):                               # cost() for one angle, in plain floats (the search's 48)
            reach = math.sqrt(max(base + alpha * math.cos(th) + beta * math.sin(th), 0.0))
            short = max(reach - limit, 0.0)
            short = short * short / (2.0 * ROLL_SOFT) if short < ROLL_SOFT else short - 0.5 * ROLL_SOFT
            return ROLL_COST * th * th + short * short
        grid = np.linspace(0.0, most, ROLL_GRID + 1)
        k = int(np.argmin(cost(grid)))
        lo, hi = float(grid[max(k - 1, 0)]), float(grid[min(k + 1, ROLL_GRID)])
        for _ in range(24):                          # golden section in the bracket
            m1, m2 = hi - 0.618034 * (hi - lo), lo + 0.618034 * (hi - lo)
            lo, hi = (lo, m2) if cost1(m1) <= cost1(m2) else (m1, hi)
        best, knee = 0.5 * (lo + hi), 0.6 * cap      # eased into the cap: a roll running into it slows down
        if best > knee:
            best = knee + (cap - knee) * (1.0 - math.exp(-(best - knee) / (cap - knee)))
        return float(best)

    def _roll_need(self, side, t, rot, ankle, hip, limit, ctx):
        """How far the foot rolls for its leg to reach the hip, signed radians: + over its ball (heel up), -
        back on its heel (toes up). Smooth over the walk: within its contact the two blend by how far the foot
        has rolled onto its ball (ROLL_SENSE about the middle); off the ground it fades out over GROUND_TOL
        of height (its lift-off's or its strike's); a leg that reaches needs none."""
        if ctx["placement"] <= 0.0 or np.linalg.norm(ankle - hip) <= limit * (1.0 + 1e-9):
            return 0.0
        i, r = self._contact_at(side, t)
        hs, to = self.contact[side][i]
        A = to - hs
        if r <= A:
            lam, held = self._pivot_weight(side, i, r), 1.0
        else:                                         # just off the ground: its lift-off's or the next strike's
            after = r - A
            leaving = after < self.swing_len[side][i] - after
            lam = (self.pivot[side][i][1] if leaving else self.pivot[side][(i + 1) % len(self.contact[side])][0])
            if leaving:
                # a foot leaving the ground keeps its roll and lets it go over the first SWING_EASE of its
                # swing: faded by the foot's height (2.5 cm, half a frame at toe-off) it turned back about its
                # ball at once - the ankle dropped behind, the leg snapped straight, the knee clicked (a
                # Ground time's long stance rolls the foot 28 deg, 2026-10-13)
                held = 1.0 - min(after / (SWING_EASE * self.swing_len[side][i]), 1.0)
            else:
                ground = max(float(periodic_cr(self.ground["foot_" + side], t)),
                             float(periodic_cr(self.ground["ball_" + side], t)))
                held = min(max(ground / (1.0 - CONTACT_TOL / GROUND_TOL), 0.0), 1.0)
            held = held * held * (3.0 - 2.0 * held)
            if held <= 0.0:
                return 0.0
        u = min(max((lam - 0.5) / ROLL_SENSE + 0.5, 0.0), 1.0)
        ball = u * u * (3.0 - 2.0 * u)
        out = 0.0
        if ball > 0.0:
            out += ball * self._roll_cost(side, t, rot, ankle, hip, limit, ctx, 1.0)
        if ball < 1.0:
            out -= (1.0 - ball) * self._roll_cost(side, t, rot, ankle, hip, limit, ctx, -1.0)
        return held * out

    def _roll_turn(self, side, t, rot, ankle, roll, asked=0.0):
        """The foot (rot, ankle) rolled `roll` radians: + about its ball (heel up), - about its heel (toes up),
        eased into the sole's limit; the point it rolls on stays where it is. `asked` of the roll (Push-off,
        Heel strike, Foot flat: what the animator asked for) is turned whole after the rest, held only by the
        sole's hard limits (SOLE_HARD). Returns (rotation, ankle, the world turn about the ball or None)."""
        need = roll - asked
        sense = 1.0 if need > 0.0 else -1.0
        geometry = None if need == 0.0 else self._roll_frame(side, t, rot, ankle, sense)
        ball = None
        if geometry is not None:
            pivot, axis = geometry
            angle = self._sole_eased(side, rot, axis, sense, abs(need))
            if angle > 0.0:
                turn = exp_rot(axis * sense * angle)     # heel up about the ball (+), toes up about the heel (-)
                rot, ankle = rot @ turn, pivot + (ankle - pivot) @ turn
                ball = turn if sense > 0.0 else None
        if asked:
            sense = 1.0 if asked > 0.0 else -1.0
            geometry = self._roll_frame(side, t, rot, ankle, sense)
            if geometry is not None:
                pivot, axis = geometry
                lift, _ = self._sole_lift(side, rot, axis, sense)
                angle = min(abs(asked), max(0.0, math.radians(SOLE_HARD[sense > 0.0]) - lift))
                if angle > 0.0:
                    turn = exp_rot(axis * sense * angle)
                    rot, ankle = rot @ turn, pivot + (ankle - pivot) @ turn
                    if sense > 0.0:
                        ball = turn if ball is None else ball @ turn
        return rot, ankle, ball

    def _rolled(self, side, t, rot, ankle, hip, limit, ctx):
        """Foot placement's reach at one instant: the foot rolled as far as _roll_need says. Returns
        (rotation, ankle, the world turn about the ball or None)."""
        return self._roll_turn(side, t, rot, ankle, self._roll_need(side, t, rot, ankle, hip, limit, ctx))

    def _roll_of(self, side, tau, ctx):
        """The signed roll (radians) the foot takes at body time tau: the one _lowering found for the frame
        (the evaluate's own frames - every leg solve of the frame takes the same), else 0."""
        rolls = ctx.get("rolls")
        if not rolls:
            return 0.0
        f = int(round(tau * (len(rolls[side]) - 1) / float(self.P)))
        return float(rolls[side][f % len(rolls[side])])

    def _asked_of(self, side, tau, ctx):
        """The part of the frame's roll (radians) the animator asked for (Push-off, Heel strike, Foot flat)."""
        asked = ctx.get("asked_rolls")
        if not asked:
            return 0.0
        f = int(round(tau * (len(asked[side]) - 1) / float(self.P)))
        return float(asked[side][f % len(asked[side])])

    def _leg_reach(self, side, t, ctx, straight=True):
        """The share of its length a leg (its foot at foot time t) straightens to at most: Knee bend on stance's
        while the foot is planted, else the walk's (and Ground time's) reach."""
        reach = ctx.get("stance_reach")
        if reach is not None and reach[side] < ctx["reach"][side] and self.planted(side, t, ctx):
            return reach[side]
        out = ctx.get("reach", self.reach)[side]
        share = self._straighten(ctx)
        if share > 0.0 and self.planted(side, t, ctx):
            # Height raised: a planted leg may straighten toward STRAIGHT_KNEE (a crouched pose's knees held the
            # pelvis down whatever Height asked, 2026-10-26); all of it at STRAIGHT_FULL cm
            out += (max(out, self.straight_reach[side]) - out) * share
        passing = self.straight_share(side, t, ctx, straight)   # Passing knee: the cap gives way at the passing
        if passing > 0.0:
            # never a lower cap than the cycle's own: an ask no straighter than the cycle changes nothing (a
            # knee bent MORE than its own is Knee bend's ask, and it wins where both are set)
            out = max(out, out + passing * (ctx["straight"][side] - out))
        return out

    def passing_window(self, side, t, ctx):
        """How far into its own contact's middle a PLANTED foot stands at foot time t (passing_share), None
        while it is in the air. It is the walk's own geometry, whatever the knobs ask: a planted leg lets the
        hips rise in proportion to it, so a leg at its strike or its toe-off pins them where the cycle has
        them and the contacts keep their look (a lift the other leg's window allowed straightened dw's strike
        by 8 deg: 2026-11-02)."""
        if not self.planted(side, t, ctx):
            return None
        i, r = self._contact_at(side, t)
        hs, to = self.contact[side][i]
        return passing_share(r, to - hs)

    def straight_share(self, side, t, ctx, on=True):
        """How far the leg (its foot at foot time t) may straighten for Passing knee: nothing with none asked,
        nothing while the foot is not planted, else its passing_window. `on` False answers 0 for a reader that
        must see the cycle's own cap - the foot's reach roll is the walk's own, and a cap raised at the passing
        would take it away (the foot stood flat where it rolled, its ankle 1.7 cm off: 2026-11-02)."""
        if not on or not ctx.get("straight") or side not in ctx["straight"]:
            return 0.0
        return self.passing_window(side, t, ctx) or 0.0

    def _straighten(self, ctx):
        """How far (0..1) a raised Height lets planted legs straighten past the walk's own: Height over
        STRAIGHT_FULL, none when Knee bend caps the stance or Height is not raised."""
        k = ctx["k"]
        ks = ctx.get("ks") or {"l": k, "r": k}
        if k["pelvis_height"] <= 0.0 or any(ks[side]["knee_bend"] > 0.0 for side in SIDES):
            return 0.0
        return min(1.0, k["pelvis_height"] / STRAIGHT_FULL) * k["height_straighten"]

    def own_stretch(self, side, t, lower=0.0):
        """The source leg's hip-to-ankle distance over its length at foot time t - from a hip `lower` cm lower
        (a pose's)."""
        th, ca, fo = (self.index["%s_%s" % (b, side)] for b in LEG)
        d = float(np.linalg.norm(self.wpos(fo, t) - self.wpos(th, t) + self.up * lower))
        return d / (float(np.linalg.norm(self.lt_at(ca, t))) + float(np.linalg.norm(self.lt_at(fo, t))))

    def _soft_from(self, side, t, ctx, reach, straight=True):
        """Where a leg at foot time t starts easing into its limit `reach` (knee_soft): never below what the
        source has there, so the walk's own legs are untouched; `reach` itself when knee_soft is 0. Under a pose
        the source's leg is read from the hip the pose lowers (ctx["pose_lower"]): the goblin's crouched legs
        never straighten, and read off the bare walk's push-off (0.99) a long step went straight from a bent
        knee to the hard limit with no soft zone - 18 deg/fr^2 at the knee (2026-10-26)."""
        ks = ctx.get("ks") or {"l": ctx["k"], "r": ctx["k"]}
        soft = ks[side].get("knee_soft", 0.0)
        if soft <= 0.0:
            return reach
        if self.planted(side, t, ctx):
            # a planted leg straightens to PLANTED_SOFT of its limit: held at its own (or the pose's crouched)
            # stretch, no Height could straighten a planted knee - the sword walked on 40 deg knees (2026-10-26)
            soft = min(soft, PLANTED_SOFT)
        out = min(reach, max(self.own_stretch(side, t, ctx.get("pose_lower", 0.0)), reach * (1.0 - soft)))
        share = self._straighten(ctx)
        if share > 0.0 and self.planted(side, t, ctx):
            out += (reach - out) * share * STRAIGHT_SOFT    # a raised Height straightens it: the soft zone gives way
        passing = self.straight_share(side, t, ctx, straight)
        if passing > 0.0:
            # Passing knee: the soft zone gives way to the asked ratio too, so the leg reaches exactly the ask
            # with no compression (a planted foot compressed off its print would slide) and goes no straighter
            out = max(out, min(reach, ctx["straight"][side] * passing + out * (1.0 - passing)))
        return out

    def swing_at(self, side, tau):
        """How far the foot hangs off its shin at source time tau: swing_weight of its flight's progress (0 on
        every frame it is down, so a foot on the ground is never turned by its shin)."""
        s = self.air_progress(side, tau)
        return 0.0 if s is None else swing_weight(s)

    def foot_in_calf(self, side, tau, gain=1.0):
        mean, logs = self.foot_rel[side]
        return exp_rot(gain * periodic_cr(logs, tau)) @ mean

    def _reach(self, side):
        th, ca, fo = (self.index["%s_%s" % (b, side)] for b in LEG)
        d = np.linalg.norm(self.pos[fo] - self.pos[th], axis=1)
        return float((d / (np.linalg.norm(self.lt[ca], axis=1) + np.linalg.norm(self.lt[fo], axis=1))).max())

    def _helpers(self):
        worlds = self.clip.worlds[:, :self.P]
        body = [j for j, k in enumerate(self.kind) if k != "helper"]
        follows = {}
        for h, kind in enumerate(self.kind):
            if kind != "helper":
                continue
            best = None
            for b in body:
                rel = worlds[h] @ np.linalg.inv(worlds[b])
                err = float(np.abs(rel - rel[0]).max())
                if err < FOLLOW_TOL:
                    key = (len(self._ancestors(b)), err)
                    if best is None or key < best[0]:
                        best = (key, b, rel[0])
            if best is not None:
                follows[h] = (best[1], best[2])
        return follows

    # -- the balance: the centre of mass and the feet's pressure --

    def _masses(self):
        """`self.mass`: de Leva's table as one weight a joint (each mass point a fixed blend of two joints),
        summing to 1; the trunk spread along pelvis..neck_01 at its thirds. A walk without that chain gets no
        masses and `balance_note` says why."""
        idx, mass = self.index, np.zeros(len(self.names))
        self.mass = mass
        if "neck_01" not in idx:
            self.balance_note = "no neck_01: Balance weighs the trunk from the pelvis to neck_01"
            return
        chain = [idx["neck_01"]]
        while chain[-1] != idx["pelvis"]:
            if self.parents[chain[-1]] < 0:
                self.balance_note = "neck_01 is not under the pelvis: Balance weighs the trunk along that chain"
                return
            chain.append(self.parents[chain[-1]])
        chain.reverse()
        lengths = np.linalg.norm(np.diff(self.pos[chain, 0], axis=0), axis=1)
        ends = np.concatenate([[0.0], np.cumsum(lengths)])
        for share, part in zip(TRUNK_MASS, (1.0 / 6.0, 0.5, 5.0 / 6.0)):
            at = part * ends[-1]
            i = min(int(np.searchsorted(ends, at, side="right")) - 1, len(lengths) - 1)
            t = (at - ends[i]) / lengths[i] if lengths[i] > 1e-9 else 0.0
            mass[chain[i]] += share * (1.0 - t)
            mass[chain[i + 1]] += share * t
        mass[idx.get("head", chain[-1])] += HEAD_MASS
        for side in SIDES:
            for a, b, share, t in LIMB_MASS:
                if a + "_" + side in idx and b + "_" + side in idx:
                    mass[idx[a + "_" + side]] += share * (1.0 - t)
                    mass[idx[b + "_" + side]] += share * t
            hand = idx.get("hand_" + side)
            if hand is not None:
                share, t = HAND_MASS
                if "middle_01_" + side in idx:
                    fingers = [idx["middle_01_" + side]]
                else:
                    fingers = [j for j, p in enumerate(self.parents) if p == hand and self.kind[j] == "finger"]
                mass[hand] += share * (1.0 - t if fingers else 1.0)
                for j in fingers:
                    mass[j] += share * t / len(fingers)
        self.mass = mass / mass.sum()

    def com(self, worlds):
        """The centre of mass of world matrices (J, F, 4, 4) -> (F, 3), or one frame's (J, 4, 4) -> (3,)."""
        return np.tensordot(self.mass, np.asarray(worlds)[..., 3, :3], axes=(0, 0))

    def _grounds(self):
        """Each foot point's floor a source frame (`floor`, cm up): its lowest within the step it stands in, and
        across a swing the two steps' floors blended (a foot may stand a little higher at one step than at
        another - one step a cycle: its own lowest); and its ground contact (`ground`): 1 on its floor, 0
        GROUND_TOL above it."""
        self.floor, self.ground = {}, {}
        P = self.P
        for side in SIDES:
            steps = self.steps[side]
            for name in ("foot_" + side, "ball_" + side):
                h = self.pos[self.index[name]] @ self.up
                lows = [float(min(h[(foot.on + i) % P] for i in range(foot.length + 1))) for foot in steps]
                floor = np.zeros(P)
                for f in range(P):
                    i, k, r = self._step_at(side, float(f))
                    foot = steps[i]
                    if r <= foot.length:
                        floor[f] = lows[i]
                    else:
                        after = steps[(i + 1) % len(steps)]
                        gap = (after.on - foot.on) % P or P
                        u = (r - foot.length) / max(gap - foot.length, 1e-9)
                        floor[f] = (1.0 - u) * lows[i] + u * lows[(i + 1) % len(steps)]
                self.floor[name] = floor
                self.ground[name] = np.clip(1.0 - (h - floor) / GROUND_TOL, 0.0, 1.0)

    def pressure(self, points, taus):
        """The centre of pressure (F, 3, on the up = 0 plane through the world) where `points` ({foot_l,
        ball_l, foot_r, ball_r: (F, 3)}) put the feet at source times `taus`: per foot a heel point and a toe
        point, each loaded by its source contact at that phase (so a swinging foot never presses); None when
        no frame has a foot down. A frame between two steps takes the straight line between its neighbours."""
        frames = len(taus)
        num, den = np.zeros((frames, 3)), np.zeros(frames)
        flat = lambda p: np.asarray(p, float) - np.outer(np.asarray(p, float) @ self.up, self.up)
        for side in SIDES:
            ankle, ball = flat(points["foot_" + side]), flat(points["ball_" + side])
            heel, toe = ankle + HEEL_SHARE * (ankle - ball), ball + TOE_SHARE * (ball - ankle)
            g_heel = np.clip([float(periodic_cr(self.ground["foot_" + side], t)) for t in taus], 0.0, 1.0)
            g_toe = np.clip([float(periodic_cr(self.ground["ball_" + side], t)) for t in taus], 0.0, 1.0)
            load = np.maximum(g_heel, g_toe)
            point = (g_heel[:, None] * heel + g_toe[:, None] * toe) / np.maximum(g_heel + g_toe, 1e-9)[:, None]
            num += load[:, None] * point
            den += load
        known = den > 1e-6
        if not known.any():
            return None
        return _fill_periodic(num / np.maximum(den, 1e-9)[:, None], known)

    def _own_pendulum(self):
        """The source's CoM, its pressure and its pendulum against its travel line (fwd, side[, up]); how
        strongly its CoM follows the pendulum per axis (`follow`, fitted, clamped to FOLLOW_RANGE)."""
        if self.balance_note:
            return
        P = self.P
        cop = self.pressure(dict((n, self.pos[self.index[n]]) for n in self.ground), np.arange(P, dtype=float))
        if cop is None:
            self.balance_note = "no foot is ever on the ground: Balance needs a walk's contacts"
            return
        line = self.origin + np.outer(np.arange(P) / float(P), self.travel)
        self.s_dev = np.tensordot(self.mass, self.pdev, axes=(0, 0)) @ self.basis.T
        self.cop_dev = ((cop - line) @ self.basis.T)[:, :2]
        self.l_dev = pendulum(self.cop_dev, P / self.fps, self.s_dev[:, 2].mean())
        follow = []
        for axis in (0, 1):
            a = self.s_dev[:, axis] - self.s_dev[:, axis].mean()
            b = self.l_dev[:, axis] - self.l_dev[:, axis].mean()
            fit = float(np.dot(a, b) / np.dot(b, b)) if float(np.dot(b, b)) > 1e-12 else 1.0
            follow.append(min(max(fit, FOLLOW_RANGE[0]), FOLLOW_RANGE[1]))
        self.follow = np.array(follow)

    def _balance_target(self, times, ctx, bases):
        """Where the new cycle's centre of mass belongs, a frame (world, 0..n-1): its own (the knobs' walk,
        nothing carried) moved by Balance x [the pendulum's change (the new pressure and tempo against the
        source's) about its mean, x the walk's follow, forward x Exaggeration, sideways x Sway x Exaggeration;
        plus the mean's: the new pressure's mean change minus the CoM's own]."""
        k, b, n = ctx["k"], ctx["balance"], len(times) - 1
        worlds = np.swapaxes(np.array(bases), 0, 1)
        own = self.com(worlds)
        line = np.array([self.origin + ctx["travel2"] * phi for phi, _ in times[:-1]])
        m_dev = (own - line) @ self.basis.T
        taus = [tau for _, tau in times[:-1]]
        # each foot loaded as in the walk (Foot placement's longer push-off rolls off a foot the weight has left)
        cop = self.pressure(dict((name, worlds[self.index[name], :, 3, :3]) for name in self.ground), taus)
        cop_dev = ((cop - line) @ self.basis.T)[:, :2]
        l_new = pendulum(cop_dev, n / self.fps, m_dev[:, 2].mean())
        l_src = np.array([periodic_cr(self.l_dev, tau) for tau in taus])
        gain = self.follow * np.array([k["surge"] * ctx["ex"] * k["balance_surge"],
                                       k["sway"] * ctx["ex"] * k["balance_sway"]])
        swing = gain * ((l_new - l_new.mean(axis=0)) - (l_src - l_src.mean(axis=0)))
        mean = ((cop_dev.mean(axis=0) - self.cop_dev.mean(axis=0))
                - (m_dev[:, :2].mean(axis=0) - self.s_dev[:, :2].mean(axis=0)))
        if k["pelvis_forward"]:
            # Pelvis forward is asked for: Balance keeps the shift of the centre of mass it makes (the body over
            # the hips moved with them, the legs re-solved) and does not carry the hips back over the feet
            back = -k["pelvis_forward"] * self.fwd
            without = np.array([self._moved_com(bases[f], tau, ctx, back, {})
                                for f, (_, tau) in enumerate(times[:-1])])
            mean = mean + ((own - without) @ self.basis.T)[:, :2].mean(axis=0)
        delta = b * (swing + mean)
        return own + delta @ self.basis[:2], {"source_sway": float(np.ptp(self.s_dev[:, 1])),
                                              "mean": [float(v) for v in b * mean],
                                              "need": float(np.abs(delta).max())}

    def _com_joints(self):
        """The joints a centre of mass needs: every weighed joint and its ancestors."""
        if getattr(self, "_com_set", None) is None:
            need = set()
            for j in np.nonzero(self.mass)[0]:
                need.add(int(j))
                need.update(self._ancestors(int(j)))
            self._com_set = need
        return self._com_set

    def _carry_parts(self):
        """The CoM's joints a pelvis carry moves rigidly (the pelvis and the body over it, not the legs), and
        per leg (thigh, calf, foot, the CoM's joints under the foot)."""
        if getattr(self, "_parts", None) is None:
            only, pelvis = self._com_joints(), self.index["pelvis"]
            legs, in_legs = {}, set()
            for side in SIDES:
                th, ca, fo = (self.index["%s_%s" % (b, side)] for b in LEG)
                below = [j for j in only if fo in self._ancestors(j)]
                legs[side] = (th, ca, fo, below)
                in_legs.update([th, ca, fo] + below)
            rigid = [j for j in only if j not in in_legs and (j == pelvis or pelvis in self._ancestors(j))]
            self._parts = (rigid, legs)
        return self._parts

    def _moved_com(self, base, tau, ctx, delta, cache):
        """The centre of mass of a base frame (J, 4, 4) with the pelvis moved by `delta` (world): the body over
        it moved rigidly, the legs re-solved to the same feet (exactly what the frame itself would give)."""
        rigid, legs = self._carry_parts()
        rots, poss = list(base[:, :3, :3]), list(base[:, 3, :3])
        for j in rigid:
            poss[j] = poss[j] + delta
        for side in SIDES:
            th, ca, fo, below = legs[side]
            before, turned = poss[fo], rots[fo]
            self._leg(side, tau, rots, poss, ctx, cache)
            turn = turned.T @ rots[fo]             # a swinging foot turns with its shin
            for j in below:
                poss[j] = (poss[j] - before) @ turn + poss[fo]
        return np.tensordot(self.mass, np.array(poss), axes=(0, 0))

    def _carry(self, times, ctx, bases, sink, target, start, caches):
        """The pelvis's horizontal carry a frame putting the frame's CoM on `target` (secant steps), the pelvis
        `sink` cm lower than in its base frame; from `start`. Returns the carry (n+1, 3), the last the first's."""
        flat = lambda v: v - np.dot(v, self.up) * self.up
        out = np.array(start, float)
        for f, (phi, tau) in enumerate(times[:-1]):
            s, down = out[f].copy(), -sink[f] * self.up
            com = self._moved_com(bases[f], tau, ctx, s + down, caches[f])
            miss, rate = flat(target[f] - com), 0.8
            for _ in range(CARRY_STEPS):
                if np.linalg.norm(miss) < CARRY_TOL:
                    break
                step = miss / rate
                s = s + step
                moved = self._moved_com(bases[f], tau, ctx, s + down, caches[f])
                rate = min(max(float(np.dot(flat(moved - com), step) / np.dot(step, step)), 0.2), 1.5)
                com, miss = moved, flat(target[f] - moved)
            out[f] = s
        out[-1] = out[0]
        return out

    # -- the new cycle --
    def _height_plan(self, given, pose, k):
        """What a raised Height may take from the legs to reach (the asks of 2026-10-26): (the planted knees'
        straightening, 0..1 of STRAIGHT_KNEE; the step's share, HEIGHT_STEP_FLOOR..1). Each only when the raise
        loses more than HEIGHT_KEEP of itself to the legs' reach (the pelvis's mean drop, read on the drop alone)
        without it - straightened knees near their limit click, a shorter step is a shorter walk: knees first,
        then the step, and the step only where it helps (a walk already on straight legs mid-stance gains
        nothing by it) and the animator left Step alone (height_step)."""
        raised = k["pelvis_height"]
        ks = sided(k)
        if raised <= 0.0 or self.placement_note or not any(ks[s]["knee_soft"] > 0.0 for s in SIDES):
            return k["height_straighten"], 1.0     # the bare engine (no physics helpers): the old rule
        keep = HEIGHT_KEEP * raised
        def eaten(straight, f):
            trial = dict(given or {}, stride=k["stride"] * f, height_step=0.0, height_straighten=straight)
            return float(np.mean(self.evaluate(trial, pose, _drop_only=True)))
        bare = eaten(0.0, 1.0)
        if bare <= keep:
            return 0.0, 1.0
        straight = 1.0
        full = eaten(1.0, 1.0)
        if full <= keep:                          # straightened enough: how little is enough
            half = eaten(0.5, 1.0)
            straight = 0.5 if half <= keep else 1.0
            return straight, 1.0
        if bare - full < 0.25 * keep:
            straight = 0.0                        # straightening did not help: the knees keep their soft zone
        if k["height_step"] <= 0.0:
            return straight, 1.0
        floor = eaten(straight, HEIGHT_STEP_FLOOR)
        now = full if straight else bare
        if now - floor < max(HEIGHT_STEP_GAIN, 0.1 * raised):     # the step bought too little
            return straight, 1.0
        target = floor + HEIGHT_KEEP * (now - floor)
        lo, hi = HEIGHT_STEP_FLOOR, 1.0
        for _ in range(3):
            mid = 0.5 * (lo + hi)
            lo, hi = (mid, hi) if eaten(straight, mid) <= target else (lo, mid)
        return straight, 1.0 - (1.0 - lo) * k["height_step"]

    def evaluate(self, given=None, pose=None, weapons=None, _drop_only=False):
        """The cycle rebuilt from knobs (the spec's model); own_knobs() give the source back. `pose` (from
        walkpose.prepare: {"spine": {joint: local 3x3}, "head": 3x3, "pelvis": 3x3, "height": cm over the
        travel line, "knee_turn": {side: radians}}) replaces the mean pose the knob `pose`'s share.
        `weapons` (from scene.weapons_in_hands: {side: {"grip": (3,), "tip": (3,)}} in the holding hand's own
        frame) is what Weapon overlap swings: with none that knob does nothing."""
        k = asked = knobs(**(given or {}))
        if _drop_only:                      # the Height plan's own trials (_height_plan): the drop, nothing more
            height_straighten, height_scale = k["height_straighten"], 1.0
        else:
            height_straighten, height_scale = self._height_plan(given, pose, k)
        if height_scale < 1.0 or height_straighten != k["height_straighten"]:
            k = knobs(**dict(given or {}, stride=k["stride"] * height_scale, height_straighten=height_straighten))
        P = self.P
        n = max(int(round(k["tempo"])), 4) if k["tempo"] >= 1.0 else P
        ctx = {"k": k, "ex": k["exaggeration"], "travel2": self.travel * k["stride"],
               "lag": max(0.0, k["overlap"] + WEIGHT_LAG * k["weight"]) * P / float(n),
               "beta": min(max(WEIGHT_WARP * k["weight"], -0.9), 0.9),
               "phi0": self.low_phase + (WEIGHT_WARP_AFTER - 0.25) / self.strides,
               "pose": pose if (pose and k["pose"] > 0.0) else None, "alpha": k["pose"],
               "balance": 0.0 if self.balance_note else k["balance"], "carry": None,
               "weapons": dict(weapons or {})}
        # Leg match: the pose's stance read against its own hips and the gait (matched_pose)
        keep, froude = self.gait_keep(k, n)
        match = k["leg_match"] if ctx["pose"] is not None else 0.0
        yaw = float(ctx["pose"].get("hips_yaw", 0.0)) if ctx["pose"] is not None else 0.0
        ctx["leg_match"] = {"on": match > 0.0, "keep": keep, "froude": froude,
                            "hips_deg": math.degrees(match * yaw) if "pelvis" in (ctx["pose"] or {}) else 0.0}
        ctx["pose"] = self.leaned_pose(self.matched_pose(ctx["pose"], match, keep), k["gait_lean"])
        fix = self.fix
        # how far a pose holds the pelvis below the walk's own (its height at its share, _body's base): the soft
        # knee limit reads the source's legs from a hip lowered that much (_soft_from)
        if ctx["pose"] and "height" in ctx["pose"]:
            ctx["pose_lower"] = ctx["alpha"] * (self.pelvis_mean[2] + fix["height"] - ctx["pose"]["height"])
        else:
            ctx["pose_lower"] = 0.0
        if ctx["pose"] and "width" in ctx["pose"]:      # a pose's width replaces the corrected walk's at its share
            ctx["spread"] = ctx["alpha"] * ctx["pose"]["width"] + (1.0 - ctx["alpha"]) * fix["width"]
        else:
            ctx["spread"] = fix["width"]
        ctx["ks"] = ks = sided(k)
        ctx["held_sides"], ctx["held_by"] = self.held_together(ctx)
        ctx["foot_lag"] = dict((side, ks[side]["foot_lag"] * P / float(n)) for side in SIDES)
        ctx["spine_map"] = self._spine_map(ctx["pose"], ctx["alpha"])
        ctx["turns"] = {}
        for side in SIDES:             # the pose's knee heading and toe-out, met (Knee <-> foot)
            pose, knee_turn, toe = ctx["pose"], 0.0, 0.0
            if pose is not None:
                turn = ctx["alpha"] * ks[side]["leg_turn"]
                knee_turn = turn * pose["knee_turn"][side] if "knee_turn" in pose else 0.0
                toe = turn * pose["toe"][side] if "toe" in pose else 0.0
                knee_turn, toe = meet(knee_turn, toe, ks[side]["knee_foot"])
            # the correction's turns, giving way to a pose's own at its share (Pose over the corrected walk)
            own_k = (1.0 - ctx["alpha"]) if pose is not None and "knee_turn" in pose else 1.0
            own_t = (1.0 - ctx["alpha"]) if pose is not None and "toe" in pose else 1.0
            out = math.radians(ks[side]["toe_add"]) * (1.0 if side == "l" else -1.0) * self.left
            ctx["turns"][side] = (knee_turn + own_k * fix["knee"][side], toe + own_t * fix["toe"][side] + out)
        ctx["placement"] = 0.0 if self.placement_note else k["foot_placement"]
        # Ground time past 1 holds the trailing leg longer: it ends its stance straight on its toes, and a
        # knee near straight turns tens of degrees for millimetres of reach - so it is kept STRETCH_REACH of
        # its length at most and the pelvis sinks the rest (at 0.993, the walk's own straightest, it clicked:
        # 2026-10-13)
        ctx["gt"] = dict((s, self.ground_factor(s, ks[s])) for s in SIDES)
        stretch = dict((s, min(1.0, max(0.0, ctx["gt"][s] - 1.0) / GROUND_STRETCH)) for s in SIDES)
        ctx["reach"] = dict((s, r + (min(r, STRETCH_REACH) - r) * stretch[s]) for s, r in self.reach.items())
        # Knee bend on stance: a PLANTED leg straightens this far at most (_leg_reach). Not the swinging leg: a
        # run's leg reaches forward nearly straight before it lands, and capped too it was drawn in and held the
        # pelvis down - a 5 deg ask read 17 on HavyRun (Gait Builder, 2026-10-26)
        ctx["stance_reach"] = dict(ctx["reach"])
        for s in SIDES:
            bent = ks[s]["knee_bend"]
            if bent > 0.0:
                l1, l2 = self.leg_parts[s]
                limit = math.sqrt(l1 * l1 + l2 * l2 + 2.0 * l1 * l2 * math.cos(math.radians(bent))) / (l1 + l2)
                ctx["stance_reach"][s] = min(ctx["reach"][s], limit)
        # Passing knee: the ratio a leg straightens to around the middle of its contact, where its cap gives
        # way (_leg_reach, _soft_from) and the hips rise as far as every leg allows (_passing_lift). Only where
        # the ask is straighter than the cycle's own reach - the knob's own value is what the cycle does, so an
        # untouched card changes nothing - and never against Knee bend, which caps the same knee the other way
        ctx["straight"] = {}
        for s in SIDES:
            want = ks[s]["passing_knee"]
            if want > 0.0 and ks[s]["knee_bend"] <= 0.0:
                ctx["straight"][s] = straight_ratio(want, *self.leg_parts[s])
        ctx["aspects"] = self.aspects_on(k)
        ctx["frame"], ctx["grown"] = P / float(n), None
        ctx["lags"] = self.lags(k, ks, ctx["frame"])
        ctx["locks"], held = self._locks(ctx) if ctx["placement"] > 0.0 else ({}, 0.0)
        ctx["ground"] = {}
        timed = any(ks[s]["ground_time"] != 1.0 or ks[s]["duty"] > 0.0 for s in SIDES)
        if not self.placement_note and (ctx["placement"] > 0.0 or timed):
            ctx["grown"] = self._growth(ctx)        # Ground time retimes the feet with or without Foot placement
        times = [(f / float(n), f * P / float(n)) for f in range(n + 1)]
        ctx["chest_own"] = self._chest_own(times, ctx)
        drop = self._lowering(times, ctx)
        balance = {"carry": 0.0, "residual": 0.0, "note": self.balance_note if k["balance"] > 0.0 else ""}
        if ctx["balance"] > 0.0:
            only = self._com_joints()
            bases = [self._frame(phi, tau, ctx, drop[f], None, only)[0] for f, (phi, tau) in enumerate(times[:-1])]
            moved_arms = any(ks[s]["arm_drag"] > 0.0
                             or abs(ks[s]["arm_overlap"]) >= OVERLAP_QUIET
                             or abs(ks[s]["elbow_overlap"]) >= OVERLAP_QUIET
                             or abs(ks[s]["hand_overlap"]) >= OVERLAP_QUIET
                             or s in self.rigid_sides(ctx)     # the Weapon tab's Hold moves the arms
                             or float(ks[s]["weapon_aim"]) < 1.0 - AIM_QUIET      # ...and so does its Aim target
                             or float(ks[s]["weapon_shoulder"]) > SHOULDER_QUIET  # ...and its Shoulder
                             for s in SIDES)
            swinging = (moved_arms and bool(self._arm_chains())) or self._bodies_on(k)
            still = list(bases)

            def armed(carry):
                """The bases with the arms' inertia as they move under `carry` (the carry itself not in them:
                _moved_com adds it) - the carry balances the arms as they move, inertia and all."""
                frames = np.stack(still + [still[0]], axis=1)
                frames[:, n, 3, :3] += ctx["travel2"]
                rigid = self._carry_parts()[0]
                if carry is not None:
                    frames[rigid, :, 3, :3] += carry[None]
                self._body_dynamics(frames, n, ctx, only)
                self._arm_overlap(frames, n, ctx, only)
                self._arm_dynamics(frames, n, ctx, only)
                if carry is not None:
                    frames[rigid, :, 3, :3] -= carry[None]
                return [frames[:, f] for f in range(n)]
            if swinging:
                bases = armed(None)
            target, said = self._balance_target(times, ctx, bases)
            need = said.pop("need")
            balance.update(said)
            caches, first, carry = [dict() for _ in bases], np.array(drop), np.zeros((n + 1, 3))
            armed_at = carry.copy()
            for round_ in range(BALANCE_ROUNDS if need >= CARRY_TOL else 0):   # nothing to carry at the defaults     # the carry, then the reach's drop with it, till the drop holds
                ctx["carry"] = carry = self._carry(times, ctx, bases, np.array(drop) - first, target, carry, caches)
                again = self._lowering(times, ctx)
                settled = float(np.abs(np.array(again) - np.array(drop)).max()) < CARRY_TOL
                drop = again
                # the arms trail the carried body too: balance them again - when the carry moved more than
                # ARM_RECARRY since they last swung (the arms' share of the CoM barely changes under a small
                # carry; each swing costs two arm integrations - Gait Builder's speed-up, 2026-10-26)
                if swinging and float(np.abs(carry - armed_at).max()) > ARM_RECARRY:
                    bases = armed(carry)
                    armed_at = carry.copy()
                if settled and (not swinging or round_ > 0):
                    break
            if k["balance_reach"] > 0.0 and ctx["carry"] is not None:
                allow = BALANCE_SINK * self.leg_length
                if float(np.max(drop)) - float(np.max(first)) > allow:
                    # the carry scaled back (bisected) until its sink is what the legs allow
                    full, lo, hi = np.array(ctx["carry"]), 0.0, 1.0
                    for _ in range(6):
                        mid = 0.5 * (lo + hi)
                        ctx["carry"] = mid * full
                        trial = self._lowering(times, ctx)
                        lo, hi = (mid, hi) if float(np.max(trial)) - float(np.max(first)) <= allow else (lo, mid)
                    ctx["carry"] = carry = lo * full
                    drop = self._lowering(times, ctx)
                    balance["limited"] = lo
            balance["carry"] = float(np.linalg.norm(carry, axis=1).max()) if ctx["carry"] is not None else 0.0
        if _drop_only:
            return np.array(drop[:-1])
        worlds = np.tile(np.eye(4), (len(self.names), n + 1, 1, 1))
        short, ctx["swing_in"] = 0.0, 0.0
        for f, (phi, tau) in enumerate(times):
            carry = None if ctx["carry"] is None else ctx["carry"][f]
            worlds[:, f], frame_short = self._frame(phi, tau, ctx, drop[f], carry)
            short = max(short, frame_short)
        body = self._body_dynamics(worlds, n, ctx)
        overlap = self._arm_overlap(worlds, n, ctx)
        arms = self._arm_dynamics(worlds, n, ctx)
        arms["overlap"] = overlap
        if not self.balance_note:
            line = np.array([self.origin + ctx["travel2"] * phi for phi, _ in times[:-1]])
            dev = (self.com(worlds[:, :n]) - line) @ self.basis.T
            balance["sway"], balance["forward"] = float(np.ptp(dev[:, 1])), float(np.ptp(dev[:, 0]))
            balance["source_sway"] = float(np.ptp(self.s_dev[:, 1]))
            balance["follow"] = [float(v) for v in self.follow]
            if ctx["balance"] > 0.0:
                balance["residual"] = float(np.abs((self.com(worlds[:, :n]) - target) @ self.basis[:2].T).max())
        if k["in_place"] > 0.0:          # after everything the walk itself measures: it walks, then stays
            self._in_place(worlds, times, ctx)
        flat = ctx["travel2"] - np.dot(ctx["travel2"], self.up) * self.up
        info = {"frames": n, "stride_cm": float(np.linalg.norm(flat)) / (2.0 * self.strides),
                "speed": float(np.linalg.norm(flat)) / (n / self.fps) / 100.0, "lowered": float(max(drop)),
                "height_step": height_scale, "height_straighten": height_straighten,
                "drop": [float(d) for d in drop], "short": short, "swing_in": ctx["swing_in"],
                "lag": ctx["lag"] * n / float(P), "knobs": asked, "ground": ctx["ground"],
                "contacts": ({} if self.placement_note else
                             dict((s, [(a * n / float(P), b * n / float(P)) for a, b in
                                       self.placed_contact(s, ctx["placement"], ctx["grown"])]) for s in SIDES)),
                "placement": {"on": ctx["placement"] > 0.0, "slide": held, "note": self.placement_note,
                              "planted": dict((side, [self.planted(side, self._clock(side, tau, ctx), ctx)
                                                      for _, tau in times[:-1]]) for side in SIDES),
                              "double": dict((s, d * n / float(P)) for s, d in
                                             (self.double_support(ctx["placement"], ctx["grown"]).items()
                                              if not self.placement_note else []))},
                "pelvis": (k["pelvis_rot"] * ctx["ex"] * k["pelvis_twist"] * k["stride"] * self.twist_gain,
                           k["pelvis_rot"] * ctx["ex"] * k["pelvis_list"]),
                "chest": self.chest_targets(k, ctx["ex"]) if self.chest_shape is not None else None,
                "arms": arms, "body": body, "leg_match": ctx["leg_match"],
                "balance": balance, "in_place": k["in_place"]}
        if ctx.get("passing"):
            info["passing"] = self._passing_seen(ctx, worlds, n)
        return Result(worlds, n, info)

    def _passing_seen(self, ctx, worlds, n):
        """ctx["passing"] with `got` and `short` read off the FINISHED worlds, at the frames the ask was solved
        on - the knee the animator will see. Neither the lift's own bisection nor the pace can say it: the pace
        comes after the bisection, and the body's own carry (Balance) moves the hip after the drop is done, by
        3 deg of knee on asd (2026-11-02)."""
        told = ctx["passing"]
        frames = ctx.get("_passing_frames") or {}
        got = {}
        for side in told.get("asked") or {}:
            each = []
            for f in frames.get(side) or []:
                if f >= n:
                    continue
                h, k, a = (worlds[self.index["%s_%s" % (b, side)], f, 3, :3] for b in LEG)
                u, v = k - h, a - k
                nu, nv = float(np.linalg.norm(u)), float(np.linalg.norm(v))
                if nu > 1e-9 and nv > 1e-9:
                    each.append(math.degrees(math.acos(max(-1.0, min(1.0, float(np.dot(u / nu, v / nv)))))))
            if each:
                got[side] = float(np.mean(each))
        if got:
            told["got"] = got
            told["short"] = dict((s, max(0.0, got[s] - told["asked"][s])) for s in got)
        return told

    def _in_place(self, worlds, times, ctx):
        """In place (on `worlds`, (J, n+1, 4, 4)): every joint moved back by the root's progress along the
        walk - the travel line's and the root's own surge along it - and by the line's climb, x In place. The root
        stays where frame 0 has it but for its weave aside (Root sway) and its own height; the body moves about it,
        the planted feet slide back at the walk's speed, the last frame is the first."""
        root = self.index["root"]
        along = (worlds[root, :, 3, :3] - worlds[root, 0, 3, :3]) @ self.fwd
        climb = float(np.dot(ctx["travel2"], self.up)) * np.array([phi for phi, _ in times])
        shift = np.outer(along, self.fwd) + np.outer(climb, self.up)
        worlds[:, :, 3, :3] -= ctx["k"]["in_place"] * shift[None]

    def lift_profile(self, side):
        """[(height over the stance's ground, foot_target's lift_up)] at every whole source frame the foot
        swings: at the knobs' lift L that frame's ankle stands h + (L - 1) . lift_up over the ground (Gait
        Builder's Foot lift solves L on it, aspects.lift_scale). Kept on the walk."""
        kept = getattr(self, "_lift_profiles", None)
        if kept is None:
            kept = self._lift_profiles = {}
        if side in kept:
            return kept[side]
        steps, j = self.steps[side], self.index["foot_" + side]
        rows, ground = [], []
        for f in range(self.P):
            tau = float(f)
            src = self.wpos(j, tau)
            h = float(np.dot(src, self.up))
            i, k, r = self._step_at(side, tau)
            foot = steps[i]
            if r <= foot.length + 1e-9:
                ground.append(h)
                continue
            nxt = (i + 1) % len(steps)
            k_on = k + (1 if nxt == 0 else 0)
            t_off, t_on = foot.on + foot.length + k * self.P, steps[nxt].on + k_on * self.P
            p_off, p_on = self.wpos(j, t_off), self.wpos(j, t_on)
            x, x_off, x_on = (float(np.dot(p, self.fwd)) for p in (src, p_off, p_on))
            s = (x - x_off) / (x_on - x_off) if abs(x_on - x_off) > 1e-9 else (tau - t_off) / (t_on - t_off)
            rows.append((h, float(np.dot(src - (1.0 - s) * p_off - s * p_on, self.up))))
        g = float(np.mean(ground)) if ground else 0.0
        kept[side] = [(h - g, up) for h, up in rows]
        return kept[side]

    def foot_target(self, side, tau, stride, stance=1.0, spread=0.0, lift=1.0, swing_out=0.0, detail=1.0):
        """The new foot at source time tau: (world rotation, ankle position). Stance: the source's foot
        moved with its step's footprint - across the travel line, the walk's half-spread about the middle of
        its prints plus half the pose's `spread`, all x `stance`; swing: the source's swing between the new
        footprints of its step and the next, its lift scaled, bowed `swing_out` cm out (+) or in along
        sin(pi s) of its flight (from where it leaves the ground to where it lands: a foot that is down never
        slides). A print stands across the body at its side's mean plus its own irregularity x `detail`."""
        steps, j, P = self.steps[side], self.index["foot_" + side], self.P
        rot, src = self.wrot(j, tau), self.wpos(j, tau)
        travel2 = self.travel * stride
        i, k, r = self._step_at(side, tau)
        foot = steps[i]
        sign = 1.0 if side == "l" else -1.0
        middle = 0.5 * (self.body_print("l") + self.body_print("r"))
        regular = self.body_print(side) - middle

        def shift(step, cycle):
            own = self.print_across(step) - middle
            half = regular + detail * (own - regular)
            across = stance * (half + sign * spread / 2.0) - own
            return ((travel2 - self.travel) * ((step.mid + cycle * P) / P)
                    + (stride - 1.0) * step.coords[0] * self.fwd + across * self.across)
        here = shift(foot, k)
        if r <= foot.length + 1e-9:
            return rot, src + here
        nxt = (i + 1) % len(steps)
        k_on = k + (1 if nxt == 0 else 0)
        after = steps[nxt]
        t_off, t_on = foot.on + foot.length + k * P, after.on + k_on * P
        p_off, p_on = self.wpos(j, t_off), self.wpos(j, t_on)
        x, x_off, x_on = (float(np.dot(p, self.fwd)) for p in (src, p_off, p_on))
        s = (x - x_off) / (x_on - x_off) if abs(x_on - x_off) > 1e-9 else (tau - t_off) / (t_on - t_off)
        lift_up = float(np.dot(src - (1.0 - s) * p_off - s * p_on, self.up))
        flight = self.air_progress(side, tau) if swing_out else None
        bow = 0.0 if flight is None else sign * swing_out * math.sin(math.pi * flight) * self.lside
        return rot, src + (1.0 - s) * here + s * shift(after, k_on) + (lift - 1.0) * lift_up * self.up + bow

    def _body(self, phi, tau, ctx, drop=0.0, carry=None):
        """The root's and the pelvis's new (rotation, position); the pelvis `drop` cm lower for the reach and
        `carry` (a world vector) along for the balance. Balance takes over the pelvis's forward swing from the
        stride: it scales by (1 - Balance) x Stride + Balance and the pendulum brings what the step changes."""
        k, ex = ctx["k"], ctx["ex"]
        line2 = self.origin + ctx["travel2"] * phi
        extra = self.pelvis_extra(tau, k, ex)
        out = {"extra": extra}
        gains = (k["g_surge"], k["g_sway"], k["g_bob"])
        for name, mean in (("root", self.root_mean), ("pelvis", self.pelvis_mean)):
            j = self.index[name]
            if name == "pelvis":
                dev = self._sample("pdev", j, tau, ctx, gains, self.basis) @ self.basis.T
            else:
                dev = self._sample("pdev", j, tau, ctx) @ self.basis.T
            scale = k["stride"] if name == "root" else (1.0 - ctx["balance"]) * k["stride"] + ctx["balance"]
            # Surge: x the pelvis's forward and back - Bob's partner along the walk (the root keeps its own)
            surge = k["surge"] if name == "pelvis" else 1.0
            along = mean[0] + surge * scale * ex * (dev[0] - mean[0])
            if name == "pelvis":         # Pelvis forward: the hips ahead of (+) or behind (-) the feet
                along += k["pelvis_forward"]
            # the root runs straight down the travel line at Root sway 0 (a root weaving with the hips weaves
            # the capsule a game moves by it); the pelvis sways
            gain = k["root_sway"] if name == "root" else k["sway"] * ex
            aside = mean[1] + gain * (dev[1] - mean[1])
            if name == "pelvis":
                pose, a = ctx["pose"], ctx["alpha"]
                clock = warp(phi, ctx["beta"], ctx["phi0"], self.strides) * self.P
                late = k["bob_shift"] * ctx.get("frame", 1.0)       # Low point: the bob's regular part later
                v = float(self._sample("pdev", j, clock, ctx, gains, self.basis, late) @ self.up) - mean[2]
                if k["bob_add"]:       # a bob where the walk has (next to) none: at its own phase, else the guide's
                    v += 0.5 * k["bob_add"] * math.cos(2.0 * self.stride_phase(clock - late) - self.aspect_phase["bob"])
                if k["double_bounce"]:  # two lows a step: the walk's own, else at each strike and each passing
                    v += 0.5 * k["double_bounce"] * math.cos(4.0 * self.stride_phase(clock - late)
                                                            - self.aspect_phase["double"])
                own = mean[2] + self.fix["height"]          # the corrected walk's mean height
                base = own if pose is None or "height" not in pose else (1.0 - a) * own + a * pose["height"]
                # Pelvis height raises or lowers it over the feet (the reach's drop still holds the legs)
                height = base + k["pelvis_height"] + k["bob"] * ex * shape_bob(v, k["weight"]) - drop
                centre = self.wmean[j] if pose is None or "pelvis" not in pose else toward(self.wmean[j], pose["pelvis"], a)
                turn = self._sample("wlog", j, tau, ctx)
                if centre is not self.wmean[j]:     # a tilted pelvis turns about the walk's world axes
                    turn = turn @ self.wmean[j] @ centre.T
                rot = exp_rot(k["pelvis_rot"] * ex * turn) @ centre
                if extra is not None:      # Twist and Hip drop: a turn in the world about the pelvis
                    rot = rot @ exp_rot(extra)
            else:
                height, rot = dev[2], self.wrot(j, tau)
            out[name] = (rot, line2 + np.array([along, aside, height]) @ self.basis)
        if carry is not None:
            rot, pos = out["pelvis"]
            out["pelvis"] = (rot, pos + carry)
        return out

    def down(self, side, tau):
        """Whether the foot is on or near the ground at source time tau (its heel or toe within GROUND_TOL of
        its own lowest in the source)."""
        return max(float(periodic_cr(self.ground["foot_" + side], tau)),
                   float(periodic_cr(self.ground["ball_" + side], tau))) > 1e-6

    def _lowering(self, times, ctx):
        """The pelvis's drop on every frame (the last = the first): each frame needs the least drop that lets
        the legs whose feet are down reach without straightening past the source's straightest (a foot in the
        air that cannot reach passes closer to the body instead); the drop is a smooth periodic curve over those
        needs (smooth_cover), so a long stride sinks the contacts, not the whole cycle."""
        n = len(times) - 1
        need, legs = np.zeros(n), []
        needs = dict((side, np.zeros(n)) for side in SIDES)
        plain_limits = dict((side, np.zeros(n)) for side in SIDES)
        for f, (phi, tau) in enumerate(times[:-1]):
            carry = None if ctx["carry"] is None else ctx["carry"][f]
            pelvis_rot, pelvis_pos = self._body(phi, tau, ctx, 0.0, carry)["pelvis"]
            legs.append({})
            for side in SIDES:
                t = self._clock(side, tau, ctx)
                th, ca, fo = (self.index["%s_%s" % (b, side)] for b in LEG)
                hip = self.lt_at(th, tau) @ pelvis_rot + pelvis_pos
                rot, ankle = self._foot(side, tau, ctx)[:2]
                length = float(np.linalg.norm(self.lt_at(ca, t))) + float(np.linalg.norm(self.lt_at(fo, t)))
                limit = self._soft_from(side, t, ctx, self._leg_reach(side, t, ctx)) * length
                # the foot's reach roll is the walk's own: it reads the cap WITHOUT Passing knee's, or a leg
                # free to stretch at the passing would stand its foot flat where the cycle rolls it
                plain = (limit if not ctx.get("straight") else
                         self._soft_from(side, t, ctx, self._leg_reach(side, t, ctx, False), False) * length)
                needs[side][f] = self._roll_need(side, t, rot, ankle, hip, plain, ctx)
                legs[f][side] = (t, rot, ankle, hip, limit)
                plain_limits[side][f] = plain      # the cap as the CYCLE's own: what the rise is measured from
        # the heel's roll lets go gradually: never earlier than a frame needs it, and after its peak it eases
        # down over ROLL_RELEASE of a stride. Taken frame by frame it fell 20 deg in two frames as a Ground
        # time's long stance ended - the heel dropped, the ankle jumped back and the knee clicked (2026-10-13)
        # Under Ground time past 1 the stance ends with a large roll that rises as fast (2 -> 20 deg in two
        # frames): there the whole curve is a smooth cover over the frames' needs, heel up and toes up apart
        # A stance leg short of its reach (a raised pelvis) rolls toes up over its heel from the strike, then heel
        # up over its ball: taken frame by frame the toes-up roll came in 10-15 deg in one frame at the strike and
        # flipped to heel up 15-22 deg in one frame at the heel-to-ball handoff, and the near-straight knee
        # snapped (2026-10-16) - so the roll changes no faster than ROLL_RATE; where that leaves the leg short
        # the pelvis's drop (a smooth cover below) takes the rest. Only ever less roll: a roll where the frame
        # asked for none would move the foot's still point
        ks = ctx.get("ks") or {"l": ctx["k"], "r": ctx["k"]}
        for side in SIDES:
            if self._gt(ctx, side) > 1.0:
                up, back = np.maximum(needs[side], 0.0), np.maximum(-needs[side], 0.0)
                sigma = LOWER_BLUR * n / self.strides
                needs[side] = smooth_cover(up, sigma) - smooth_cover(back, sigma)
            needs[side] = released(needs[side], ROLL_RELEASE * n / self.strides)
            if self._gt(ctx, side) <= 1.0:
                needs[side] = rate_limited(needs[side], math.radians(ROLL_RATE) * self.strides / float(n))
        asked = self._asked_rolls(legs, ctx)
        if asked is not None:
            for side in SIDES:
                needs[side] = needs[side] + asked[side]
        ctx["rolls"] = (dict((side, np.append(needs[side], needs[side][0])) for side in SIDES)
                        if ctx["placement"] > 0.0 or asked is not None else None)
        ctx["asked_rolls"] = (None if asked is None else
                              dict((side, np.append(asked[side], asked[side][0])) for side in SIDES))
        # Near straight a knee turns tens of degrees for a millimetre of reach, so a leg held exactly at its
        # limit by the drop's cover, or a swinging leg clamped there, snaps (2026-10-16, a raised pelvis): once
        # the legs fall short anywhere (by MARGIN_FULL cm, eased in from nothing - so the defaults are untouched)
        # they are held LEG_MARGIN of their length short of the limit, and a swinging foot past it is drawn in
        # toward its hip on a smooth curve rather than clamped
        def needs_for(margin, limits=None):
            held, aloft = dict((side, np.zeros(n)) for side in SIDES), dict((side, np.zeros(n)) for side in SIDES)
            for f, (phi, tau) in enumerate(times[:-1]):
                for side in SIDES:
                    t, rot, ankle, hip, limit = legs[f][side]
                    if limits is not None:        # the cycle's own cap, for the rise Passing knee is paced by
                        limit = float(limits[side][f])
                    limit *= 1.0 - margin
                    down = self.planted(side, t, ctx)
                    # with the margin a swinging foot holds the pelvis as far as it cannot be drawn in: fully
                    # as it comes down to its print, not at all mid-swing (swing_weight, the draw-in's own)
                    share = 0.0 if down or self._just_off(side, t, ctx) or margin <= 0.0 else 1.0 - self.swing_at(side, t)
                    if not down and share <= 0.0 and not self._just_off(side, t, ctx):
                        continue
                    ankle = self._roll_turn(side, t, rot, ankle, self._roll_of(side, tau, ctx),
                                            self._asked_of(side, tau, ctx))[1]
                    q = ankle - hip
                    if np.linalg.norm(q) <= limit * (1.0 + 1e-9):
                        continue
                    qu = float(np.dot(q, self.up))
                    disc = qu * qu - (float(np.dot(q, q)) - limit * limit)
                    if disc >= 0.0:
                        if share > 0.0:      # (the margin's pass only, so only once the stance legs fall short)
                            held[side][f] = share * (-qu - math.sqrt(disc))
                        else:
                            (held if down else aloft)[side][f] = -qu - math.sqrt(disc)
            out = np.zeros(n)
            for side in SIDES:     # a foot just off the ground holds the pelvis no lower than its stance did...
                cap = held[side].max()
                if self._gt(ctx, side) > 1.0:
                    cap = np.inf   # ...unless Ground time held it longer: its swing leaves from further behind
                out = np.maximum(out, np.maximum(held[side], np.minimum(aloft[side], cap)))
            return out
        need = needs_for(0.0)
        weight = min(1.0, float(need.max()) / MARGIN_FULL)        # the stance legs short: the margin comes in
        if weight > 0.0:
            need = np.maximum(need, weight * needs_for(LEG_MARGIN))
        drop = smooth_cover(need, LOWER_BLUR * len(need) / self.strides)     # LOWER_BLUR of a stride
        # Passing knee raises the hips through TWO channels - the cap it relaxes inside the window (this drop's
        # own need falls there) and _passing_lift's lift - and what the animator watches is neither, it is the
        # knee. So the drop the cycle would have WITHOUT the ask is worked out first: it is the track both the
        # lift's own pace and _knee_paced read the knee's own degrees off, and reading them off two different
        # tracks is what let the ask through at one allowance and took it back at a tighter one (2026-11-02).
        own = None
        if ctx.get("straight"):
            own = needs_for(0.0, plain_limits)
            share = min(1.0, float(own.max()) / MARGIN_FULL)
            if share > 0.0:
                own = np.maximum(own, share * needs_for(LEG_MARGIN, plain_limits))
            own = smooth_cover(own, LOWER_BLUR * len(own) / self.strides)
        lift = self._passing_lift(times, legs, ctx, drop, own)   # Passing knee: the hips rise at the passing
        if lift is not None:
            drop = drop - lift
        if ctx.get("straight"):
            drop = self._knee_paced(drop, own, times, legs, ctx)
            self._passing_told(ctx, np.maximum(own - drop, 0.0), times, legs, drop)
        ctx["reel"] = None
        short = self._swing_excess(times, legs, ctx, drop, 0.0).max()
        if weight > 0.0 or short > 0.0:          # a swing past its reach (or near it, with the margin): drawn in
            margin = weight * LEG_MARGIN
            reel = {}
            for side in SIDES:
                excess = self._swing_excess(times, legs, ctx, drop, margin, side)
                reel[side] = smooth_cover(excess, LOWER_BLUR * n / self.strides)
                reel[side] = np.append(reel[side], reel[side][0])
            ctx["reel"] = reel
        return np.append(drop, drop[0])

    def _knee_geometry(self, times, legs, ctx, drop):
        """{side: {frame: (qu, qq, length)}} - the ankle against the hip (as the drop `drop` leaves it) and the
        leg's length, on every frame an asked side's foot is planted. A rise of x cm leaves the ankle at
        q - x . up, so a knee's bend under any rise is a closed form in these three numbers. Every planted
        frame, not only the window's own: the window is nothing at the strike and whole across the middle, and
        its shoulders are exactly where a near-straight knee was left to turn 11 deg in a frame (2026-11-02)."""
        out = dict((side, {}) for side in SIDES)
        for f in range(len(drop)):
            tau = times[f][1]
            for side in SIDES:
                t, rot, ankle, hip, limit = legs[f][side]
                if side not in (ctx.get("straight") or {}) or not self.planted(side, t, ctx):
                    continue
                ankle = self._roll_turn(side, t, rot, ankle, self._roll_of(side, tau, ctx),
                                        self._asked_of(side, tau, ctx))[1]
                q = ankle - hip + drop[f] * self.up
                ca, fo = (self.index["%s_%s" % (b, side)] for b in LEG[1:])
                length = float(np.linalg.norm(self.lt_at(ca, t))) + float(np.linalg.norm(self.lt_at(fo, t)))
                out[side][f] = (float(np.dot(q, self.up)), float(np.dot(q, q)), length)
        return out

    def _knee_allowance(self, bend, n):
        """(a frame's turn, a frame's corner) a knee may move in degrees, from the track `bend` ({frame: deg})
        it keeps without the ask: STRAIGHT_DEG_SHARE of its own p90, floored so a cycle whose knee barely moves
        still straightens. The lift's own erosion and the pace that follows it must read the SAME number off
        the SAME track, or they fight: eroded at one allowance and judged at a tighter one, the right leg's ask
        was taken straight back out again (the animator's own walk, 2026-11-02)."""
        floor = STRAIGHT_DEG_FLOOR * 30.0 * self.strides / float(max(n, 1))
        turns = [abs(bend[(f + 1) % n] - bend[f]) for f in bend if (f + 1) % n in bend]
        corners = [abs(bend[(f + 2) % n] - 2.0 * bend[(f + 1) % n] + bend[f]) for f in bend
                   if (f + 1) % n in bend and (f + 2) % n in bend]
        return (max(STRAIGHT_DEG_SHARE * (float(np.percentile(turns, 90)) if turns else 0.0), floor),
                max(STRAIGHT_DEG_SHARE * (float(np.percentile(corners, 90)) if corners else 0.0), floor))

    def _knee_at(self, side, row, x):
        """The bend (deg) of the leg `row` describes (_knee_geometry) under a rise of `x` cm."""
        qu, qq, length = row
        l1, l2 = self.leg_parts[side]
        return knee_bend_at(min(1.0, math.sqrt(max(qq - 2.0 * x * qu + x * x, 0.0)) / length), l1, l2)

    def _knee_paced(self, drop, own, times, legs, ctx):
        """The drop, with the hips LOWERED again wherever an asked knee would turn faster a frame than it turns
        under this cycle's own cap (`own`) by more than STRAIGHT_DEG_SHARE - and never lowered by more than the
        rise Passing knee gave, so the pace can only take back what the ask added. Near straight a knee is a
        square root of its reach (trap 266), so the rate in centimetres the rise itself is held to is 2 degrees
        of knee at one frame of a cycle and 14 at another: the leg the rise reached turned at twice its own
        pace while the other looked right (the animator's own walk, 2026-11-02). Lowering the hips can only
        bend a planted knee, so the sweep below only ever lowers them: it settles, and it can put no foot out
        of reach. The reference is the knee under `own`, not the source clip's: Height, the step, the ground
        time and the pose all change what a knee does itself, by a factor of two on the synthetic walker."""
        n = len(drop)
        rise = np.maximum(own - drop, 0.0)
        geo = self._knee_geometry(times, legs, ctx, drop)
        if not any(geo[side] for side in SIDES) or float(np.max(rise)) <= 0.0:
            return drop
        plain = self._knee_geometry(times, legs, ctx, own)
        allow, allow2 = {}, {}
        paced = ctx.get("_passing_pace") or {}
        for side in SIDES:
            if side in paced:                 # the allowance the lift was eroded at, read off the same track
                allow[side], allow2[side] = paced[side]
                continue
            rows = plain[side]
            bend = dict((f, self._knee_at(side, rows[f], 0.0)) for f in rows)
            allow[side], allow2[side] = self._knee_allowance(bend, n)
        down = np.zeros(n)

        def lower(side, rows, i, target):
            """Lower frame i's hips until that knee's bend is `target`, within the rise - how much it moved."""
            qu, qq, length = rows[i]
            l1, l2 = self.leg_parts[side]
            d = straight_ratio(target, l1, l2) * length
            disc = qu * qu - qq + d * d
            if disc < 0.0:
                return 0.0
            want = min(rise[i], max(0.0, -(qu + math.sqrt(disc))))
            if want <= down[i]:
                return 0.0
            moved, down[i] = want - down[i], want
            return moved

        for _ in range(KNEE_SWEEPS):
            moved = 0.0
            for side, rows in geo.items():
                for f in sorted(rows):
                    g, h = (f + 1) % n, (f + 2) % n
                    if g not in rows:
                        continue
                    bf = self._knee_at(side, rows[f], -down[f])
                    bg = self._knee_at(side, rows[g], -down[g])
                    if abs(bg - bf) > allow[side]:
                        # the straighter of the two comes back toward the other: a step no faster than the pace
                        i = f if bf < bg else g
                        moved = max(moved, lower(side, rows, i, max(bf, bg) - allow[side]))
                    if h not in rows:
                        continue
                    bg = self._knee_at(side, rows[g], -down[g])
                    turn = bf + self._knee_at(side, rows[h], -down[h]) - 2.0 * bg
                    if turn > allow2[side]:
                        # and the dip between them no sharper than the cycle's own corner: a straightening
                        # held at its allowance and then stopped is a corner, and a corner is what the eye
                        # reads as uneven (the animator's own walk: 14 deg/fr2 against its own 7)
                        moved = max(moved, lower(side, rows, g, bg + 0.5 * (turn - allow2[side])))
            if moved <= KNEE_SETTLED:
                break
        return drop + down

    def _passing_told(self, ctx, rise, times, legs, drop):
        """What Passing knee really did, once the rise has been paced: the bend each side's knee comes to at
        its passings, under the drop the result will have, and the degrees the legs (or the pace) left on the
        table. The lift's own bisection cannot say it - the pace comes after it."""
        told = ctx.get("passing")
        if not told:
            return
        geo = self._knee_geometry(times, legs, ctx, drop)
        got = {}
        for side in ctx["straight"]:
            frames = ctx.get("_passing_frames", {}).get(side) or []
            rows = [geo[side][f] for f in frames if f in geo[side]]
            if rows:
                got[side] = float(np.mean([self._knee_at(side, row, 0.0) for row in rows]))
        if got:
            # what the PACE held back, against what the lift's own bisection had landed: the two shortfalls
            # have different cures, and the animator's lever is only the step's
            told["paced"] = dict((s, max(0.0, got[s] - told["got"].get(s, got[s]))) for s in got)
            told["got"] = got
            told["short"] = dict((s, max(0.0, got[s] - told["asked"][s])) for s in got)
        told["lift"] = float(np.max(rise))

    def _crossings(self, times, legs, ctx):
        """The frames (fractional, wrapped) the two ankles cross each other along the travel - the passing
        phase: the swinging foot overtaking the standing one. The ankles are the ROLLED ones the result will
        have: on a cycle whose feet slide, reading them unrolled put the crossing four frames out (dw,
        2026-11-02)."""
        n = len(times) - 1
        fwd = self.basis[0]
        rolled = {}
        for f, (phi, tau) in enumerate(times[:-1]):
            for side in SIDES:
                t, rot, ankle, hip, limit = legs[f][side]
                rolled[(side, f)] = self._roll_turn(side, t, rot, ankle, self._roll_of(side, tau, ctx),
                                                    self._asked_of(side, tau, ctx))[1]
        d = np.array([float(np.dot(rolled[("l", f)] - rolled[("r", f)], fwd)) for f in range(n)])
        out = []
        for f in range(n):
            g = (f + 1) % n
            if d[f] == 0.0:
                out.append(float(f))
            elif (d[f] < 0.0) != (d[g] < 0.0):
                out.append(f + abs(d[f]) / max(abs(d[f]) + abs(d[g]), 1e-12))
        return out

    def _passing_lift(self, times, legs, ctx, drop, plain=None):
        """How far the hips rise a frame for Passing knee (an (n,) curve, None with nothing asked): each frame
        wants the lift that brings a planted leg's knee to the asked bend around the middle of its contact, and
        allows the least of what every leg leaves - a planted one up to its own limit (raised inside its own
        window by _soft_from), one in the air up to its own too, so no swinging foot is put out of reach. The
        curve is the most smooth one under that room (smooth_under), so it tapers to nothing at the double
        supports, where the other leg stands at its limit: the shape falls out of the geometry, not a table."""
        if not ctx.get("straight"):
            return None
        n = len(times) - 1
        up = self.up
        need = np.zeros(n)
        room = np.zeros(n) + STRAIGHT_LIFT_MAX
        mids = dict((side, {}) for side in SIDES)       # {contact: (how near its passing, frame, qu, qq, length)}
        asks = dict((side, {}) for side in SIDES)       # {frame: (q, length, its own bend, the ask, the window)}
        own_bends = dict((side, {}) for side in SIDES)   # {frame: the bend it keeps without the ask}
        stance_bends = dict((side, {}) for side in SIDES)  # the same, its planted frames only: the pace
        planted_asked = dict((side, {}) for side in SIDES)  # {frame: True} an asked leg planted: it caps the hips
        crossings = self._crossings(times, legs, ctx)
        for f, (phi, tau) in enumerate(times[:-1]):
            for side in SIDES:
                t, rot, ankle, hip, limit = legs[f][side]
                ankle = self._roll_turn(side, t, rot, ankle, self._roll_of(side, tau, ctx),
                                        self._asked_of(side, tau, ctx))[1]
                q = ankle - hip + drop[f] * up          # the ankle against the hip as the drop leaves it
                allow = lift_to(q, up, limit)           # the limit here is the leg's soft start, in cm
                allow = max(0.0, allow if allow is not None else 0.0)
                window = self.passing_window(side, t, ctx)
                if window is None:
                    # a foot in the AIR is drawn in toward its hip where it cannot reach (ctx["reel"]), which
                    # is what that machinery is for - and the passing is exactly when the other foot is in the
                    # air, so pinning the hips to its own reach is what clipped the entry of the window
                    allow = STRAIGHT_LIFT_MAX
                elif side in ctx["straight"]:
                    # an ASKED leg caps the hips by what IT asks (its own target need, filled in below): the
                    # taper beside it was a second one, linear in centimetres against the target's own in
                    # degrees, and the two disagree in the middle of the ramp - which is where the entry was
                    # clipped and the knee then jumped 11 deg in a frame (2026-11-02)
                    planted_asked[side][f] = True
                    allow = STRAIGHT_LIFT_MAX
                else:
                    allow *= window                     # a planted leg nobody asked pins the hips at its ends
                room[f] = min(room[f], allow)
                if side not in ctx["straight"]:
                    continue
                ca, fo = (self.index["%s_%s" % (b, side)] for b in LEG[1:])
                length = float(np.linalg.norm(self.lt_at(ca, t))) + float(np.linalg.norm(self.lt_at(fo, t)))
                l1, l2 = self.leg_parts[side]
                # the bend this knee keeps WITHOUT the ask, on every frame (in the air too): the track the
                # straightening is paced against, so the ask never asks the knee to move faster than it
                # already moves of its own accord
                bend = knee_bend_at(min(1.0, math.sqrt(max(float(np.dot(q, q)), 0.0)) / length), l1, l2)
                own_bends[side][f] = bend
                if self.planted(side, t, ctx):      # the pace is read off the STANCE: a swinging knee folds
                    stance_bends[side][f] = bend    # and unfolds far faster than a standing one ever should
                share = self.straight_share(side, t, ctx)
                if share <= 0.0:
                    continue
                # the ask is about the passing instant - the frame the other ankle crosses this one, the
                # contact's own middle where a flight leaves no crossing - so that is the frame the lift is
                # solved on, one a contact: the window's shoulders lie near the double supports, where a leg
                # can be straighter than at its passing (read off the contact's middle, asd's left leg landed
                # its ask two frames late and came out 8 deg bent: 2026-11-02)
                i, r = self._contact_at(side, t)
                hs, to = self.contact[side][i]
                near = min([abs(f - c) for c in crossings] or [1e9]) if crossings else abs(r - 0.5 * (to - hs))
                row = (near, f, float(np.dot(q, up)), float(np.dot(q, q)), length)
                if i not in mids[side] or near < mids[side][i][0]:
                    mids[side][i] = row
                # what this frame's window asks, in the KNEE's OWN DEGREES - paced in degrees below
                asks[side][f] = (q, length, bend, knee_bend_at(min(1.0, ctx["straight"][side]), l1, l2), share)
        # The straightening is shaped and paced in the KNEE's own degrees, never in centimetres. Near straight a
        # knee is a square root of its reach (trap 266), so a lift ramped or rate-limited in cm reaches the ask
        # within a frame of the window's edge and then sits flat across its middle: the knee dived 12 deg in one
        # frame and snapped 15 back out - which is what the eye reads as uneven, and what the pace (_knee_paced)
        # then had to take back out of the DEPTH, so no ask under about 6 deg ever landed on the animator's own
        # walk (2026-11-02). Eroded in degrees at the pace the cycle's own knee keeps, the knee runs smoothly
        # from the bend it has at the contact's ends down to the ask and back, and the depth is nobody's to take.
        for side in SIDES:
            rows = asks[side]
            if not rows:
                continue
            l1, l2 = self.leg_parts[side]
            # nothing to do for an ask no straighter than the knee's own bend AT ITS PASSING (that is Knee
            # bend's ask, and it wins where both are set): without this a more-bent ask still straightened the
            # frames whose own bend is deeper than it, and the knob stopped being a no-op (2026-11-02)
            at_passing = [own_bends[side].get(row[1]) for row in mids[side].values()]
            at_passing = [b for b in at_passing if b is not None]
            ask_deg = knee_bend_at(min(1.0, ctx["straight"][side]), l1, l2)
            if at_passing and ask_deg >= float(np.mean(at_passing)) - 0.25:
                continue
            own = np.array([own_bends[side].get(f, 0.0) for f in range(n)])
            # the target track over this leg's STANCE - its own bend, the window's share of the way to the ask
            # taken in degrees. The frames it is in the AIR are left out of the pace (OUTSIDE): a swinging knee
            # is deeply bent, and a cone drawn from there could not descend to the ask within the contact at a
            # stance's pace - it held a crouched walker's ask 2.2 deg short from four frames away (2026-11-02).
            # The contact's own ends pin it instead, where the window is nothing and the target IS its own bend.
            raw = np.full(n, OUTSIDE)
            for f, bend in stance_bends[side].items():
                raw[f] = bend
            for f, (q, length, own_bend, ask_bend, share) in rows.items():
                raw[f] = own_bend + share * (ask_bend - own_bend)      # the window's share, taken in degrees
            # the pace: what this knee does a frame under the drop the cycle keeps WITHOUT the ask (`plain`),
            # which is the very track _knee_paced judges the result against. Read off the drop the ask already
            # raised instead, the cap's own straightening counted as the knee's own pace and a near-reach leg
            # was allowed to move at twice its own (2026-11-02)
            # Read ONCE an evaluate and kept: Balance carries the body in rounds and each round runs _lowering
            # again, so a pace read per round drifted with the carry - the last round's 9.6 deg a frame stood
            # where the first round's 6.9 was the cycle's own, and the knee then moved at the drift (2026-11-02)
            pace = ctx.setdefault("_passing_pace", {})
            if side in pace:
                allow, allow2 = pace[side]
            else:
                pace_bends = stance_bends[side]
                if plain is not None:
                    rows_plain = self._knee_geometry(times, legs, ctx, plain)[side]
                    if rows_plain:
                        pace_bends = dict((f, self._knee_at(side, rows_plain[f], 0.0)) for f in rows_plain)
                allow, allow2 = self._knee_allowance(pace_bends, n)
            # a knee that runs down to the ask at `allow` a frame and back out again turns round at the
            # passing: that reversal IS a corner of twice the pace, and the pace must not call its own
            # shape a corner and lower the hips back out of it (the right leg of the animator's own walk,
            # whose stance knee is so steady that its own corner allowance was 2 deg, 2026-11-02)
                allow2 = max(allow2, 2.0 * allow)
                pace[side] = (allow, allow2)          # the pace _knee_paced then keeps, for this evaluate
            # the straightest TRACK no faster than that pace - the own track's own motion counted, since it is
            # the TOTAL the eye reads - and never more bent than the knee is without the ask
            want = np.minimum(cone_above(raw, allow), own)
            mine = np.zeros(n)
            for f, (q, length, own_bend, ask_bend, share) in rows.items():
                if want[f] >= own_bend - 1e-9:
                    continue
                full = lift_to(q, up, straight_ratio(float(want[f]), l1, l2) * length)
                if full is not None and full > 0.0:
                    mine[f] = full
                    need[f] = max(need[f], full)
            # and this leg, while it is planted, lets the hips rise no further than its OWN target asks: at its
            # strike and its toe-off that is nothing, so a lift the other leg wants cannot straighten this one's
            # contact ends (dw's two legs overlap for most of the cycle; its strike went 9 deg straighter)
            for f in planted_asked[side]:
                room[f] = min(room[f], mine[f])
        # and a last ceiling on the hips' own speed - the degrees above are the pace that matters, so this is
        # only a guard against something silly: a share of the cycle's own hip speed (0.4) was what made the
        # entry a cliff in degrees, since the first degrees of a straightening cost the most centimetres
        rate = max(STRAIGHT_SHARE * self.bob_rate, STRAIGHT_FLOOR * 30.0 * self.strides / float(self.P))
        shape = smooth_under(need, room, rate * self.P / max(n, 1))
        peak = float(shape.max())
        if peak <= 1e-9:
            return None
        # Each frame's lift is already the one that brings its own knee to its own eroded target, so there is
        # no scale to find: the shape IS the lift (it used to be scaled as a whole until the straightest side
        # landed on its ask, which made one frame at its room limit pin the entire curve). What a tight room
        # leaves is a dip at that frame, not a loss over the cycle, and what the legs leave is `short`.
        ks = ctx.get("ks") or {"l": ctx["k"], "r": ctx["k"]}

        def bends(scale):
            """{side: its knee's bend at its passings, degrees (the contacts' mean)} at `scale` x the shape."""
            out = {}
            for side, rows in mids.items():
                if not rows:
                    continue
                l1, l2 = self.leg_parts[side]
                each = []
                for near, f, qu, qq, length in rows.values():
                    x = scale * shape[f]
                    d = math.sqrt(max(qq - 2.0 * x * qu + x * x, 0.0))
                    each.append(knee_bend_at(min(1.0, d / length), l1, l2))
                out[side] = float(np.mean(each))
            return out

        asked = dict((s, ks[s]["passing_knee"]) for s in ctx["straight"])
        scale = 1.0
        lift = np.minimum(shape, room)
        if float(lift.max()) < STRAIGHT_QUIET:          # an ask the cycle already meets: nothing at all
            return None
        got = bends(scale)
        short = dict((s, max(0.0, got[s] - asked[s])) for s in got)      # the degrees the legs left on the table
        ctx["passing"] = {"asked": asked, "got": got, "short": short, "lift": float(lift.max())}
        # the frames the ask was solved on (one a contact), so _passing_told can say what the pace left
        ctx["_passing_frames"] = dict((side, [row[1] for row in rows.values()]) for side, rows in mids.items())
        return lift

    def roll_profiles(self, side, t, k, hold=0.0):
        """Push-off's and Heel strike's shares (0..1) at foot time t: (push, heel strike). Push-off comes in from
        PUSH_FROM of the contact to its lift-off and goes over the first SWING_EASE of the swing; Heel strike comes
        in over the last SWING_EASE of the swing and goes from the strike to the walk's own foot-flat + slap
        (at least SLAP_LEAST of a stride); both held whole `hold` source frames either side of the lift-off /
        strike."""
        i, r = self._contact_at(side, t)
        hs, to = self.contact[side][i]
        A, swing = to - hs, self.swing_len[side][i]
        ease = SWING_EASE * swing
        smooth = lambda u: u * u * (3.0 - 2.0 * u)
        clamp = lambda u: min(max(u, 0.0), 1.0)
        least = SLAP_LEAST * self.P / float(self.strides)
        slap = lambda m: max(self.flat_after[side][m] + float(k.get("slap", 0.0)), least)
        hold = min(hold, 0.25 * A, 0.25 * swing)
        if r <= A:
            push = smooth(clamp((r - PUSH_FROM * A) / max((1.0 - PUSH_FROM) * A - hold, 1e-9)))
            strike = 1.0 - smooth(clamp((r - hold) / slap(i)))
        else:
            after = r - A
            push = 1.0 - smooth(clamp((after - hold) / max(ease, 1e-9)))
            before = swing - after
            strike = smooth(clamp(1.0 - (before - hold) / max(ease, 1e-9)))
        return push, strike

    def _asked_rolls(self, legs, ctx):
        """Push-off's and Heel strike's rolls on every frame ({side: radians, + heel up}), or None when neither
        is asked (they need the contacts: not on a walk Foot placement cannot read)."""
        ks = ctx.get("ks") or {"l": ctx["k"], "r": ctx["k"]}
        if self.placement_note or not any(ks[s]["push"] or ks[s]["heel_strike"] or ks[s]["slap"] for s in SIDES):
            return None
        out = {}
        for side in SIDES:
            push, strike = math.radians(ks[side]["push"]), math.radians(ks[side]["heel_strike"])
            slap = float(ks[side]["slap"])
            roll = np.zeros(len(legs))
            for f, frame in enumerate(legs):
                t = frame[side][0]
                if push or strike:
                    a, b = self.roll_profiles(side, t, ks[side], ROLL_HOLD * ctx["frame"])
                    roll[f] = push * a - strike * b
                if slap:
                    roll[f] += self._flat_stretch(side, t, slap, ctx["frame"])
            out[side] = roll
        return out

    def _flat_stretch(self, side, t, slap, frame):
        """Foot flat: the walk's own heel strike's toes coming down `slap` source frames later (or sooner) -
        its sole's pitch from the strike to its own foot-flat stretched over the foot-flat + slap; the roll
        (radians, + heel up) that does it at foot time t, eased out over a frame past it."""
        i, r = self._contact_at(side, t)
        hs, to = self.contact[side][i]
        F = self.flat_after[side][i]
        F2 = max(F + slap, 0.0)
        if F <= 0.0 or r > to - hs:
            return 0.0
        fo = self.index["foot_" + side]
        pitch = lambda u: self.sole_pitch(side, self.wrot(fo, hs + u))
        own = pitch(r)
        if r <= F2:
            return pitch(r * F / F2) - own
        if F2 < F:          # sooner: the clip's own from its foot-flat on, rejoining the clip's time over what was cut
            span = (F - F2) + max(frame, 1e-6)
            u = min((r - F2) / span, 1.0)
            return (pitch(F + (r - F2)) - own) * (1.0 - u * u * (3.0 - 2.0 * u))
        fade = max(frame, 1e-6)
        u = min((r - F2) / fade, 1.0)
        return (pitch(F) - pitch(F2)) * (1.0 - u * u * (3.0 - 2.0 * u))

    def _swing_excess(self, times, legs, ctx, drop, margin, only=None):
        """How far (cm, a frame) a swinging foot's ankle lies past its leg's reach (less `margin` of it) from the
        hip lowered by `drop` (None: not lowered); the most of both feet, or `only` that side's."""
        n = len(times) - 1
        out = np.zeros(n)
        for f, (phi, tau) in enumerate(times[:-1]):
            for side in SIDES if only is None else (only,):
                t, rot, ankle, hip, limit = legs[f][side]
                if self.planted(side, t, ctx) or self._just_off(side, t, ctx) or self.swing_at(side, t) <= 0.0:
                    continue
                if drop is not None:
                    hip = hip - self.up * drop[f]
                ankle = self._roll_turn(side, t, rot, ankle, self._roll_of(side, tau, ctx),
                                        self._asked_of(side, tau, ctx))[1]
                out[f] = max(out[f], float(np.linalg.norm(ankle - hip)) - limit * (1.0 - margin))
        return np.maximum(out, 0.0)

    def _reel_of(self, side, tau, ctx):
        """How far (cm) the swinging foot is drawn in toward its hip at body time tau (_lowering's), else 0."""
        reel = ctx.get("reel")
        if not reel:
            return 0.0
        f = int(round(tau * (len(reel[side]) - 1) / float(self.P)))
        return float(reel[side][f % len(reel[side])])

    def _frame(self, phi, tau, ctx, drop=0.0, carry=None, only=None):
        """Every joint's new world at one frame (parents first, helpers last) - or only the joints in `only`
        (closed under their parents; the rest stay identity); and how far a foot that is down fell short (a
        foot in the air that cannot reach its path: ctx["swing_in"], the most it passes closer)."""
        k, ex = ctx["k"], ctx["ex"]
        rots, poss = [None] * len(self.names), [None] * len(self.names)
        body = self._body(phi, tau, ctx, drop, carry)
        chest = self.chest_extra(tau, k, ex, ctx.get("chest_own"))
        ks = ctx.get("ks") or {"l": k, "r": k}
        holding = self._held_sides(ctx)            # the sides whose hands hold one thing (held_together)
        gains = {"spine": k["spine"] * ex}
        feet = dict((side, self._clock(side, tau, ctx)) for side in SIDES)
        aspects = ctx.get("aspects")
        stride_a = self.stride_phase(tau) if aspects else 0.0      # (not `a`: the loop's pose share is `a`)
        rolls = {}
        short = 0.0
        for j in self.order:
            if rots[j] is not None or (only is not None and j not in only):
                continue
            kind, name, p = self.kind[j], self.names[j], self.parents[j]
            if kind in ("root", "pelvis"):
                rots[j], poss[j] = body[name]
            elif kind == "world":
                rots[j], poss[j] = self.wrot(j, tau), self.wpos(j, tau) + (ctx["travel2"] - self.travel) * phi
            elif kind == "leg":
                missed = self._leg(name[-1], tau, rots, poss, ctx, None, rolls)
                if self.planted(name[-1], feet[name[-1]], ctx):
                    short = max(short, missed)
                else:
                    ctx["swing_in"] = max(ctx.get("swing_in", 0.0), missed)
            elif kind == "helper" and j in self.follows:
                b, rel = self.follows[j]
                pose = ctx["pose"]
                if pose is not None and j in pose.get("weapons", {}):     # the weapon where the pose holds it
                    rel = blend_matrix(rel, pose["weapons"][j], ctx["alpha"])
                m = rel @ matrix(rots[b], poss[b])
                rots[j], poss[j] = m[:3, :3], m[3, :3]
            else:
                clock = feet[self.leg_side[j]] if j in self.leg_side else tau     # below a thigh: its foot's
                t = clock - self.lag[j] * ctx["lag"] - ctx.get("lags", {}).get(j, 0.0)
                pose, a = ctx["pose"], ctx["alpha"]
                if kind == "head":
                    centre = self.wmean[j] if pose is None or "head" not in pose else toward(self.wmean[j], pose["head"], a)
                    rots[j] = exp_rot(k["head"] * ex * self._sample("wlog", j, t, ctx, k["g_head"])) @ centre
                elif j in self.world_arms and (pose is None or j not in pose.get("arms", {})):
                    # the upper arm hangs and swings in the world - and so does the upper arm of an arm the pose
                    # does not name: an arm left out of the pose plays the cycle whole (2026-11-02)
                    side_k = ks[self._side(j)]
                    rots[j] = exp_rot(side_k["arms"] * ex * self._sample("wlog", j, t, ctx, side_k["g_arm"])) @ self.wmean[j]
                else:
                    centre = self.lmean[j]
                    gain = ks[self._side(j)]["arms"] * ex if kind == "arm" else gains.get(kind, 1.0)
                    if pose is not None:
                        if j in pose.get("spine", {}):
                            centre = toward(centre, pose["spine"][j], a)
                        if "arms" in pose and kind in ("arm", "finger"):
                            # the pose's arms are the mean the walk's swing runs about; hands that hold one
                            # thing together HOLD it - its swing fades, the thing sways (_arm_dynamics)
                            if j in pose["arms"]:
                                centre = toward(centre, pose["arms"][j], a)
                            # the stilling is per side (held_together): an arm left out of the pose swings
                            # as the cycle does, the one that holds the thing still holds it (2026-11-02),
                            # and 2H declares a hold the pose does not have (2026-11-04)
                            if self._side(j) in holding:
                                gain *= 1.0 - a
                    if j in self.hand_bones or kind == "finger":
                        gain *= ks[self._side(j)]["hands"]
                    if j in self.forearms:
                        gain *= ks[self._side(j)]["elbow"]
                    if kind == "spine":
                        regular = k["g_spine"]
                    elif j in self.forearms:
                        regular = ks[self._side(j)]["g_elbow"]
                    elif j in self.world_arms:
                        regular = ks[self._side(j)]["g_arm"]
                    else:
                        regular = 1.0
                    turn = self._sample("llog", j, t, ctx, regular)
                    if j in ctx["spine_map"]:      # about the world axis it turns about in the walk
                        turn = turn @ ctx["spine_map"][j]
                    local = exp_rot(gain * turn) @ centre
                    if j in self.balls:        # the toes trail the swinging shin with the foot
                        hang = self.swing_at(self.balls[j], clock)
                        toe_side = self.balls[j]
                        lag, flex = ctx["foot_lag"][toe_side], ks[toe_side]["foot_flex"]
                        if hang > 0.0 and (lag > 0.0 or flex != 1.0):
                            late = exp_rot(flex * periodic_cr(self.llog[j], clock - BALL_LAG * lag))
                            local = toward(local, late @ centre, hang)
                    rots[j] = local @ rots[p]
                    if j in self.balls and self.balls[j] in rolls:       # the toes stay down as the foot rolls
                        rots[j] = rots[j] @ rolls[self.balls[j]].T
                    if j in self.counter and body["extra"] is not None:
                        rots[j] = rots[j] @ exp_rot(-self.counter[j] * body["extra"])
                    if j in self.chest_share and chest is not None:
                        rots[j] = rots[j] @ exp_rot(self.chest_share[j] * chest)
                if aspects:
                    turn = self.aspect_turns(j, ctx, rots, stride_a)
                    if turn is not None:
                        rots[j] = rots[j] @ turn
                poss[j] = self.lt_at(j, t) @ rots[p] + poss[p]
        out = np.tile(np.eye(4), (len(self.names), 1, 1))
        for j in range(len(self.names)):
            if rots[j] is not None:
                out[j, :3, :3], out[j, 3, :3] = rots[j], poss[j]
        return out, short

    # -- the trunk and the head: two bodies on springs over the frames --

    def _bodies_on(self, k):
        """Whether Torso drag or Head drag moves anything (a walk with a spine above its pelvis)."""
        return (k["torso_drag"] > 0.0 or k["head_drag"] > 0.0) and self._trunk_chains() is not None

    def _trunk_chains(self):
        """(the spine joints from the pelvis up to the chest, the neck joints, the head or None) - each the one
        child of its kind (spine_NN, then neck_NN, then head) of the joint before; None without a spine."""
        if getattr(self, "_trunk", 0) == 0:
            def climb(j, pattern):
                out = []
                while True:
                    kids = [c for c, p in enumerate(self.parents) if p == j and re.match(pattern, self.names[c])]
                    if not kids:
                        return out
                    j = kids[0]
                    out.append(j)
            spine = climb(self.index["pelvis"], r"spine_\d+$")
            necks = climb(spine[-1], r"neck_\d+$") if spine else []
            top = (necks or spine or [None])[-1]
            head = next((c for c, p in enumerate(self.parents) if top is not None and p == top
                         and self.names[c] == "head"), None)
            self._trunk = (spine, necks, head) if spine else None
        return self._trunk

    def _body_motion(self, kin_rot, pivot, lever, n, drag, bounce, inertia=1.0, comp=0.0):
        """One rigid body's world rotation (n+1, 3, 3), following `kin_rot` (n+1, 3, 3) through a damped spring
        `drag` frames late (zeta = 1 - 0.75 bounce, the arms' spring) and feeling the acceleration of its pivot's
        path `pivot` (n, 3, the travel out) on its `lever` (in the body's frame) - a rod about its end. Integrated
        periodic as the arms are, the seam spread."""
        zeta = 1.0 - 0.75 * bounce
        w0 = 2.0 * zeta / drag
        S = max(ARM_SUBSTEPS, int(math.ceil(4.0 * w0)))
        dt = 1.0 / S
        target = self._compensated(self._resampled(kin_rot, n, S), n, S, w0, zeta, comp)
        accel = self._smooth_accel(pivot, n, S)
        kk, cc = w0 * w0, 2.0 * zeta * w0
        R, w = kin_rot[0].copy(), np.zeros(3)
        record = np.zeros((n, 3, 3))
        for cycle in range(ARM_CYCLES):
            first = R.copy()
            for step in range(n * S):
                if step % S == 0:
                    record[step // S] = R
                alpha = -kk * _log3(target[step].T @ R) - cc * w
                r = lever @ R
                length2 = float(r @ r)
                if length2 > 1e-12:
                    alpha = alpha + inertia * 0.75 / length2 * _cross3(r, -accel[step])
                w = w + alpha * dt
                R = R @ _exp3(w * dt)
            if float(np.linalg.norm(_log3(first.T @ R))) < ARM_SETTLED:
                break
        miss = _log3(record[0].T @ R)
        series = np.array([record[f] @ _exp3(-miss * f / float(n)) for f in range(n)])
        return np.concatenate([series, series[:1]])

    def _spread_turn(self, worlds, kin, joints, shares, turn):
        """`joints` (a chain, parents first) turned in the world by `turn` (n+1, 3 rotation vectors) x their
        `shares`, each on its offset in its parent as `kin` had it (in place on worlds); returns the new
        {joint: (n+1, 4, 4)}."""
        n1 = worlds.shape[1]
        new = {}
        for j, share in zip(joints, shares):
            p = self.parents[j]
            back = np.swapaxes(_batch_rot(kin[p]), -1, -2)
            offset = np.einsum("fi,fij->fj", kin[j, :, 3, :3] - kin[p, :, 3, :3], back)
            m = np.tile(np.eye(4), (n1, 1, 1))
            m[:, :3, :3] = _batch_rot(kin[j]) @ exp_rot(share * turn)
            m[:, 3, :3] = np.einsum("fi,fij->fj", offset, _batch_rot(worlds[p])) + worlds[p, :, 3, :3]
            worlds[j] = m
            new[j] = m
        return new

    def _body_dynamics(self, worlds, n, ctx, only=None):
        """The trunk and the head on springs, in place on `worlds` (J, n+1, 4, 4), before the arms (they hang on
        the moving chest). The trunk: the chest's world turn follows the frames' through Torso drag's spring and
        feels the first spine joint's acceleration on the upper body's centre of mass; the difference spread up
        the spine (each joint by its place). The head: its world turn - the gaze the frames give it - through
        Head drag's spring, feeling the first neck joint's acceleration; the neck takes NECK_SHARES of the
        difference. Everything above re-attached as the frames had it. Returns {"torso", "head": the most either
        turned off its frames (deg), "drag": (torso, head)}."""
        k = ctx["k"]
        out = {"torso": 0.0, "head": 0.0, "drag": (k["torso_drag"], k["head_drag"])}
        chains = self._trunk_chains()
        if chains is None or not self._bodies_on(k):
            return out
        spine, necks, head = chains
        travel = (worlds[spine[0], n, 3, :3] - worlds[spine[0], 0, 3, :3]) / float(n)
        flat = lambda path: path[:n] - np.outer(np.arange(n), travel)
        gaze = _batch_rot(worlds[head]) if head is not None else None
        if k["torso_drag"] > 0.0:
            kin = worlds.copy()
            chest = _batch_rot(kin[spine[-1]])
            upper = [j for j in range(len(self.names)) if self.mass[j] > 0.0 and j != spine[0]
                     and self.kind[j] in ("spine", "head", "arm", "finger") and (only is None or j in only)]
            base = kin[spine[0], :n, 3, :3]
            if upper and float(self.mass[upper].sum()) > 0.0:
                com = np.tensordot(self.mass[upper] / self.mass[upper].sum(), kin[upper, :n, 3, :3], axes=(0, 0))
            else:
                com = kin[spine[-1], :n, 3, :3]
            lever = np.einsum("fi,fij->fj", com - base, np.swapaxes(chest[:n], -1, -2)).mean(axis=0)
            dyn = self._body_motion(chest, flat(kin[spine[0], :, 3, :3]), lever, n, k["torso_drag"],
                                    k["torso_bounce"], BODY_INERTIA, k["spring_comp"])
            turn = log_rot(np.swapaxes(chest, -1, -2) @ dyn)
            new = self._spread_turn(worlds, kin, spine, [(i + 1.0) / len(spine) for i in range(len(spine))], turn)
            # the upper arms the frames hang in the world (the pose names them not) keep hanging there on the
            # moving chest - an arm left out of the pose among them (2026-11-02)
            named = {} if ctx["pose"] is None else (ctx["pose"].get("arms") or {})
            held = tuple(j for j in self.world_arms if j not in named)
            self._reattach(worlds, kin, new, only, held)
            out["torso"] = math.degrees(float(np.linalg.norm(turn, axis=1).max()))
        if head is not None and (k["head_drag"] > 0.0 or k["torso_drag"] > 0.0):
            kin = worlds.copy()
            carried = _batch_rot(kin[head])
            if k["head_drag"] > 0.0:
                pivot = necks[0] if necks else self.parents[head]
                reach = np.einsum("fi,fij->fj", kin[head, :n, 3, :3] - kin[pivot, :n, 3, :3],
                                  np.swapaxes(gaze[:n], -1, -2)).mean(axis=0)
                dyn = self._body_motion(gaze, flat(kin[pivot, :, 3, :3]), reach * (1.0 + HEAD_LIFT), n,
                                        k["head_drag"], k["torso_bounce"], HEAD_INERTIA, k["spring_comp"])
            else:
                dyn = gaze             # Head drag 0: the head keeps the gaze the frames give it, the neck takes it
            turn = log_rot(np.swapaxes(carried, -1, -2) @ dyn)
            shares = [NECK_SHARES[min(i, len(NECK_SHARES) - 1)] for i in range(len(necks))] + [1.0]
            new = self._spread_turn(worlds, kin, necks + [head], shares, turn)
            self._reattach(worlds, kin, new, only)
            if k["head_drag"] > 0.0:
                out["head"] = math.degrees(float(np.linalg.norm(log_rot(np.swapaxes(gaze, -1, -2) @ dyn),
                                                                axis=1).max()))
        return out

    # -- the arms: the body's inertia on top of their motion --

    def _side(self, j):
        """"l" or "r": the side a joint's name says (UE names end in _l / _r), else "l" (a middle joint)."""
        name = self.names[j]
        return "r" if name.endswith("_r") else "l"

    def _arm_chains(self):
        """{side: [upperarm, lowerarm, hand] indices} and each chain's parent (the clavicle, else what holds the
        upper arm); sides missing a joint are left out."""
        out = {}
        for side in SIDES:
            names = ["%s_%s" % (b, side) for b in ("upperarm", "lowerarm", "hand")]
            if all(n in self.index for n in names):
                out[side] = [self.index[n] for n in names]
        return out

    def held_together(self, ctx):
        """The sides whose hands hold ONE thing, and the side that carries it: a pose's own grip. An arm the
        pose's own chip leaves out holds nothing (the 2026-11-03 rule). The Weapon tab's Hold needs nothing
        here: two hands rigid on the chest keep their hold by construction (_weapon_hold)."""
        pose, chains = ctx["pose"], self._arm_chains()
        ks = ctx.get("ks") or {"l": ctx["k"], "r": ctx["k"]}
        inside = None if pose is None or ctx["alpha"] <= 0.0 else pose.get("arm_sides")
        out_of_pose = set() if inside is None else set(SIDES) - set(inside)
        sides, carrier = set(), "r"
        if pose is not None and ctx["alpha"] > 0.0:
            # per side, as the frame walk has read it since 2026-11-02: one arm out of the pose leaves the
            # other holding its thing, and a pose from before carries the bare flag for both arms
            sides |= set(pose.get("grip_sides", SIDES if pose.get("grip") else ()))
        held = sorted(s for s in (ctx.get("weapons") or {}) if s in chains and s not in out_of_pose)
        if held and sides:
            carrier = held[0]                    # the hand the weapon is in carries it, left or right
        return sides - out_of_pose, carrier

    def _held_sides(self, ctx):
        """`ctx["held_sides"]`, which evaluate works out once; worked out here for a ctx made by hand."""
        sides = ctx.get("held_sides")
        return self.held_together(ctx)[0] if sides is None else sides

    def _chest_joint(self):
        """The joint a weapon inherits its motion from under the chest override: the TOP spine joint the chest
        knobs already use (`chest_share`), so no bone name is hardcoded here; with no spine of its own, the
        parent of an arm chain's first joint, which is what the arms hang from either way. None with neither."""
        if self.chest_share:
            return max((int(re.match(r".*?(\d+)$", self.names[j]).group(1)), j)
                       for j in self.chest_share
                       if re.match(r".*?(\d+)$", self.names[j]))[1]
        for side, chain in sorted(self._arm_chains().items()):
            parent = self.parents[chain[0]]
            if parent >= 0:
                return parent
        return None

    def _arm_dynamics(self, worlds, n, ctx, only=None):
        """The arms following the body with inertia (in place on `worlds`, (J, n+1, 4, 4)). What the frames
        give them is their TARGET; each limb (upper arm, forearm, hand) turns toward its target - its own
        motion on the joint above as that joint actually moves - through a damped spring, and feels the
        acceleration of the point it hangs from: the arms trail the body's bob, sway and twist and whip through
        (Arm drag: the spring's delay in frames; Arm bounce: how far it overshoots). Hands that hold one thing
        together (a pose's grip, or 2H: held_together) keep holding it: the thing sways and trails as one body
        and the arms reach it by IK. Integrated ARM_SUBSTEPS a frame, cycle after cycle until a cycle starts
        where the last did, the seam closed. Returns what it did (info["arms"])."""
        ks = ctx.get("ks") or {"l": ctx["k"], "r": ctx["k"]}
        chains = self._arm_chains()
        holding = self._held_sides(ctx)
        carrier = ctx.get("held_by") or self.held_together(ctx)[1]
        grip = bool(len(chains) == 2 and all(s in holding for s in chains))
        # each arm its own side's drag and bounce; hands holding one thing move as one: the two sides' mean
        own = dict((side, (ks[side]["arm_drag"], ks[side]["arm_bounce"])) for side in chains)
        #  a hand the Weapon tab holds rigid on the chest is a CHILD of the chest: no spring of its own
        #  (2026-11-05 - the animator's step 1 is a static arm, and a spring would soften it back)
        rigid = self.rigid_sides(ctx)
        for side in rigid:
            own[side] = (0.0, own[side][1])
        grip = bool(grip and not (rigid & set(chains)))
        if grip:
            own = dict((side, (sum(d for d, _ in own.values()) / 2.0, sum(b for _, b in own.values()) / 2.0))
                       for side in own)
        drag = max([d for d, _ in own.values()] or [0.0])
        out = {"drag": drag, "bounce": max([b for _, b in own.values()] or [0.0]), "grip": grip, "cycles": 0}
        if drag <= 0.0 or not chains:
            out["drag"] = 0.0
            return out

        def spring(d, b):
            zeta = 1.0 - 0.75 * b
            w0 = 2.0 * zeta / d                   # per frame: a damped spring lags 2 zeta / w0 behind its target
            return w0, zeta, max(ARM_SUBSTEPS, int(math.ceil(4.0 * w0)))   # w0 dt <= 1/4: the integration stays true
        kin = worlds.copy()
        if grip:
            new, cycles = self._grip_motion(kin, n, chains, *spring(*own[carrier]), hold_side=carrier)
        else:
            new, cycles = {}, 0
            for side, chain in chains.items():
                if own[side][0] <= 0.0:           # this arm as the frames put it
                    continue
                got, used = self._limb_motion(kin, n, chain, *spring(*own[side]), comp=ks[side]["spring_comp"])
                new.update(got)
                cycles = max(cycles, used)
        out["cycles"] = cycles
        self._reattach(worlds, kin, new, only)
        return out

    def _compensated(self, target, n, S, w0, zeta, comp):
        """A spring's target (n * S, 3, 3, at every 1/S frame) made so the spring's output keeps the target's
        stride swing: sampled ahead by the spring's phase delay at the stride's frequency and its turn about its
        mean scaled by 1 / the spring's gain there - each x `comp` (0 the target itself)."""
        if comp <= 0.0:
            return target
        w = 2.0 * math.pi * self.strides / float(n)          # the stride, radians a frame
        kk, cc = w0 * w0, 2.0 * zeta * w0
        delay = math.atan2(cc * w, kk - w * w) / w            # frames
        gain = kk / math.hypot(kk - w * w, cc * w)
        ahead = np.roll(target, -int(round(comp * delay * S)), axis=0)
        mean = mean_rot(ahead)
        scale = 1.0 + comp * (1.0 / max(gain, 1e-6) - 1.0)
        return exp_rot(scale * log_rot(ahead @ mean.T)) @ mean

    def _resampled(self, rots, n, S):
        """A rotation series (n+1, 3, 3) (the last the first) at every 1/S frame of the cycle, slerped:
        (n * S, 3, 3)."""
        steps = np.arange(n * S) / float(S)
        f = np.floor(steps).astype(int)
        frac = steps - f
        logs = log_rot(np.swapaxes(rots[:-1], -1, -2) @ rots[1:])
        return rots[f] @ exp_rot(frac[:, None] * logs[f])

    def _hand_lever(self, j):
        """A hand's lever for its inertia: where its farthest finger joint stands in it (the walk's own, mean
        over the cycle), or None without fingers. The whole hand swings; its metacarpals' bases (4 cm) made it
        a stiff little pendulum that shook with every jolt of the wrist."""
        below, todo = [], [j]
        while todo:
            p = todo.pop()
            kids = [c for c in range(len(self.names)) if self.parents[c] == p and self.kind[c] == "finger"]
            below += kids
            todo += kids
        if not below:
            return None
        back = np.swapaxes(self.rot[j], -1, -2)
        reach = [np.einsum("fi,fij->fj", self.pos[c] - self.pos[j], back).mean(axis=0) for c in below]
        return max(reach, key=lambda v: float(np.linalg.norm(v)))

    def _smooth_accel(self, path, n, S):
        """A periodic path's acceleration (per frame squared) at every 1/S frame, of its first ARM_HARMONICS
        harmonics a stride, none faster than ACCEL_HZ: (n * S, 3)."""
        coeffs = np.fft.rfft(path, axis=0) / float(n)
        u = np.arange(n * S) / float(S)
        out = np.zeros((n * S, 3))
        top = min(ARM_HARMONICS * self.strides, int(ACCEL_HZ * n / self.fps), (n - 1) // 2)
        for k in range(1, top + 1):
            w = 2.0 * math.pi * k / float(n)
            out += 2.0 * np.real(np.outer(np.exp(1j * w * u), coeffs[k])) * -(w * w)
        return out

    def _limb_motion(self, kin, n, chain, w0, zeta, S, comp=0.0):
        """One arm's chain under inertia: {joint: (n+1, 4, 4) worlds}, the cycles it took."""
        dt = 1.0 / S
        top, base = chain[0], self.parents[chain[0]]
        rot = lambda j: np.array([orthonormal(kin[j, f, :3, :3]) for f in range(n + 1)])
        R = dict((j, rot(j)) for j in chain + [base])
        rel = dict((j, np.array([R[j][f] @ R[self.parents[j]][f].T for f in range(n + 1)])) for j in chain)
        # the bones' offsets in their parents (the arm's lengths) and each limb's lever for its inertia
        offset = dict((j, self.lt[j].mean(axis=0)) for j in chain[1:])     # the walk's own: a pose turns
        lever = dict((chain[i], offset[chain[i + 1]]) for i in range(len(chain) - 1))   # bones, not lengthens
        reach = self._hand_lever(chain[-1])
        if reach is not None:
            lever[chain[-1]] = reach
        # the shoulder's acceleration per substep, the travel taken out (it does not accelerate): of the path's
        # first ARM_HARMONICS harmonics a stride - the body's bob, sway and twist; a second difference of the frames
        # would hand the arms the frames' own noise, and the hand (the shortest lever) shook with it
        travel = (kin[top, n, 3, :3] - kin[top, 0, 3, :3]) / float(n)
        path = np.array([kin[top, f, 3, :3] - travel * f for f in range(n)])
        a_shoulder = self._smooth_accel(path, n, S)
        base_rot = self._resampled(R[base], n, S)
        rel_s = dict((j, self._compensated(self._resampled(rel[j], n, S), n, S, w0, zeta, comp)) for j in chain)
        levers = [lever.get(j) for j in chain]
        state, spin = [], []
        parent = base_rot[0]
        for j in chain:
            state.append(rel_s[j][0] @ parent)
            spin.append(np.zeros(3))
            parent = state[-1]
        record = np.zeros((len(chain), n, 3, 3))
        used = 0
        kk, cc = w0 * w0, 2.0 * zeta * w0
        for cycle in range(ARM_CYCLES):
            used = cycle + 1
            first = [r.copy() for r in state]
            for step in range(n * S):
                if step % S == 0:
                    for i in range(len(chain)):
                        record[i, step // S] = state[i]
                parent = base_rot[step]
                a_pivot = a_shoulder[step]
                for i, j in enumerate(chain):
                    Rj, w = state[i], spin[i]
                    target = rel_s[j][step] @ parent
                    e = _log3(target.T @ Rj)
                    alpha = -kk * e - cc * w
                    r = levers[i] @ Rj if levers[i] is not None else None
                    if r is not None:
                        length2 = float(r @ r)
                        if length2 > 1e-12:
                            alpha = alpha + 1.5 * ARM_INERTIA / length2 * _cross3(r, -a_pivot)
                    w = w + alpha * dt
                    Rj = Rj @ _exp3(w * dt)
                    state[i], spin[i] = Rj, w
                    if r is not None:
                        a_pivot = a_pivot + _cross3(alpha, r) + _cross3(w, _cross3(w, r))
                    parent = Rj
            if max(float(np.linalg.norm(_log3(first[i].T @ state[i]))) for i in range(len(chain))) < ARM_SETTLED:
                break
        out = {}
        rots = {}
        for i, j in enumerate(chain):          # the seam: what the last cycle missed of closing, spread over it
            miss = _log3(record[i, 0].T @ state[i])
            series = np.array([record[i, f] @ _exp3(-miss * f / float(n)) for f in range(n)])
            rots[j] = np.concatenate([series, series[:1]])
        for i, j in enumerate(chain):
            m = np.tile(np.eye(4), (n + 1, 1, 1))
            m[:, :3, :3] = rots[j]
            if i == 0:
                m[:, 3, :3] = kin[j, :, 3, :3]
            else:
                p = chain[i - 1]
                m[:, 3, :3] = out[p][:, 3, :3] + np.einsum("i,fij->fj", offset[j], rots[p])
            out[j] = m
        return out, used

    def _arm_to_hand(self, kin, n, chains, hands, hints=None):
        """Each arm rebuilt to a wanted hand: `hands` {side: (n+1, 4, 4)} -> {joint: (n+1, 4, 4)} for the upper
        arm, the forearm and the hand (a side not in `hands` is left out). From the CURRENT shoulder - the
        arm's pivot is the body's - the elbow bending the way the frames bend it, the bones keeping their
        lengths (a hand past the arm's reach is clamped along its own line by two_bone). The one IK the
        springs' grip (_grip_motion) and the overlap (_arm_overlap) both reach their hands with.
        `hints` {side: (n+1, 3)} replaces the plane the elbow is sent toward (Elbow overlap's late plane, from
        late_bend); the SOURCE plane this aligns the frames' arm FROM is the frames' own either way - the one
        trap of the cascade, since `bend` below serves as both when no hint is given."""
        out = {}
        for side, chain in chains.items():
            want = hands.get(side)
            if want is None:
                continue
            hint = (hints or {}).get(side)
            up_j, low_j, hand_j = chain
            l1, l2 = (float(np.linalg.norm(self.lt[j].mean(axis=0))) for j in (low_j, hand_j))
            mu, ml, mh = (np.tile(np.eye(4), (n + 1, 1, 1)) for _ in range(3))
            for f in range(n + 1):
                hand = want[f]
                sh, el, wr = kin[up_j, f, 3, :3], kin[low_j, f, 3, :3], kin[hand_j, f, 3, :3]
                e = _unit(wr - sh)
                bend = (el - sh) - np.dot(el - sh, e) * e
                bend = _unit(bend) if np.linalg.norm(bend) > 1e-4 else _any_perpendicular(e)
                toward = bend if hint is None else hint[f]
                knee, reached, _ = two_bone(sh, hand[3, :3], l1, l2, toward, 1.0)
                e2 = _unit(reached - sh)
                #  the new arm's plane is the one two_bone bent toward, never read back off the elbow: a
                #  hand past the arm's reach leaves the elbow ON the shoulder-wrist line, and its offset
                #  is a zero vector that zeroed the upper arm's and forearm's rotation (trap 245; the
                #  Weapon tab's hold pulling a hand out of reach, 2026-11-05)
                bend2 = toward - np.dot(toward, e2) * e2
                bend2 = _unit(bend2) if np.linalg.norm(bend2) > 1e-9 else _any_perpendicular(e2)
                normal, normal2 = _unit(_cross3(e, bend)), _unit(_cross3(e2, bend2))
                mu[f, :3, :3] = orthonormal(kin[up_j, f, :3, :3]) @ align(_unit(el - sh), normal,
                                                                          _unit(knee - sh), normal2)
                ml[f, :3, :3] = orthonormal(kin[low_j, f, :3, :3]) @ align(_unit(wr - el), normal,
                                                                           _unit(reached - knee), normal2)
                mu[f, 3, :3], ml[f, 3, :3] = sh, knee
                mh[f, :3, :3], mh[f, 3, :3] = hand[:3, :3], reached
            out[up_j], out[low_j], out[hand_j] = mu, ml, mh
        return out

    def rigid_sides(self, ctx):
        """The sides the Weapon tab holds RIGID on the chest (`weapon_hold`, 2026-11-05): its chip on, and the
        additive pose holding that arm - at Pose 0 there is no pose and the arms play the cycle, and an arm
        the pose's own chip leaves out is left alone (the 2026-11-03 rule). Such a hand is a child of the
        chest, so the arm springs (Whip) leave it alone too: the animator's step 1 is a static arm."""
        pose = ctx.get("pose")
        if pose is None or ctx.get("alpha", 0.0) <= 0.0:
            return set()
        ks = ctx.get("ks") or {"l": ctx["k"], "r": ctx["k"]}
        inside = pose.get("arm_sides")
        out_of_pose = set() if inside is None else set(SIDES) - set(inside)
        return set(s for s in self._arm_chains()
                   if s not in out_of_pose and float(ks[s]["weapon_hold"]) > 0.5)

    def _arm_overlap(self, worlds, n, ctx, only=None):
        """The arms late by Arm overlap (frames of the new cycle; in place on `worlds`, (J, n+1, 4, 4)): each
        hand's world motion - the linear travel taken out - read that many frames earlier, and the arm rebuilt
        to it by IK from the current shoulder. So everything the arm takes from the body (the chest's turn, the
        shoulder's bob and sway) is late together with its own swing: the animator's hand trick, the IK arms'
        keys shifted. Under a pose's grip the held thing is what goes late (both sides' mean lag) and the two
        hands keep their hold on it. Runs before _arm_dynamics, so Whip takes the late arm as its target.
        The cascade (2026-10-30) lags what the IK leaves free, on top of that L: Hand overlap reads the hand's
        own TURN at L + h while its place stays at L (under a grip it is the HELD thing's turn that lags its
        travel, so the hold is kept to machine precision and the other hand swings round it), and Elbow
        overlap reads the elbow's bend PLANE at L + e (per arm, and free under a grip - it moves no hand).
        The Weapon tab (rebuilt 2026-11-05) then holds the hand RIGID on the chest and reads that chest
        `weapon_overlap` frames late (_weapon_hold): the animator's own recipe, for every additive pose.
        Aim target (2026-11-10) then swings the blade about its grip onto a target keeping only a share of
        its own motion (_weapon_aim): the weapon's weight.
        Returns what it did (info["arms"]["overlap"])."""
        ks = ctx.get("ks") or {"l": ctx["k"], "r": ctx["k"]}
        chains = self._arm_chains()
        lags = dict((side, float(ks[side]["arm_overlap"])) for side in chains)
        elbows = dict((side, float(ks[side]["elbow_overlap"])) for side in chains)
        turns = dict((side, float(ks[side]["hand_overlap"])) for side in chains)
        pose = ctx["pose"]
        #  an arm the pose's own chip leaves out plays the cycle, and the Weapon tab leaves it alone too
        #  (2026-11-03): no weapon of its own is processed, it rides nobody, and 2H cannot bind it. A pose
        #  that records no `arm_sides` was never filtered, so every side is in.
        inside = None if pose is None or ctx["alpha"] <= 0.0 else pose.get("arm_sides")
        out_of_pose = set() if inside is None else set(SIDES) - set(inside)
        held = dict((side, w) for side, w in (ctx.get("weapons") or {}).items()
                    if side in chains and side not in out_of_pose)
        grip = bool(pose and pose.get("grip") and ctx["alpha"] > 0.0 and len(chains) == 2)
        if grip:                      # hands holding one thing move as one: the two sides' mean
            for table in (lags, turns):
                mean = sum(table.values()) / float(len(table))
                table.update(dict((side, mean) for side in table))
        #  The Weapon tab (2026-11-05): a side HOLDS - its hand rigid on the chest, read `weapon_overlap`
        #  frames late - where its chip is on and the additive pose holds that arm. No weapon is needed in
        #  the scene: the hand is the lever. Two hands holding one thing hold together, so the carrier alone
        #  drives and the other follows (the grip kept to machine precision).
        holds = dict((side, float(ks[side]["weapon_overlap"])) for side in self.rigid_sides(ctx))
        #  Inherit (2026-11-10): the share of the chest's own motion each held hand takes (1: all of it)
        inherits = dict((side, min(max(float(ks[side]["weapon_inherit"]), 0.0), 1.0)) for side in holds)
        followers = dict((side, [side]) for side in holds)
        #  two hands on ONE thing (a pose's own grip) hold together: the carrier drives at the two sides'
        #  mean lag and the other takes its delta, so the grip is kept to machine precision. A free hand -
        #  a one-handed pose - takes its OWN hold instead (it has its own offset from the chest, and the
        #  carrier's delta would leave it swinging: 32 cm on the dagger card, 2026-11-05)
        if holds and len(holds) == 2 and grip:
            carrier = list(held)[0] if len(held) == 1 else "r"
            mean = sum(holds.values()) / float(len(holds))
            others = [s for s in sorted(holds) if s != carrier]
            holds = {carrier: mean}
            inherits = {carrier: sum(inherits.values()) / float(len(inherits))}
            followers = {carrier: [carrier] + others}
        #  Aim target (2026-11-10): a side whose blade aims at a target keeping less than all of its own
        #  motion - {carrier: (the share kept, the hands that swing with it)}. The tab's rule: only where
        #  the additive pose holds that arm; it needs no Hold. Hands holding one thing swing as one (the
        #  two sides' mean, the carrier's lever), a free hand on its own
        aims = {}
        if pose is not None and ctx["alpha"] > 0.0:
            keeps = dict((side, min(max(float(ks[side]["weapon_aim"]), 0.0), 1.0))
                         for side in chains if side not in out_of_pose)
            if grip and len(keeps) == 2:
                carrier = list(held)[0] if len(held) == 1 else "r"
                mean = sum(keeps.values()) / 2.0
                if mean < 1.0 - AIM_QUIET:
                    aims[carrier] = (mean, [carrier] + [s for s in sorted(keeps) if s != carrier])
            else:
                aims = dict((side, (keep, [side])) for side, keep in keeps.items() if keep < 1.0 - AIM_QUIET)
        #  Shoulder (2026-11-10): the share of the arm's reach changes each clavicle takes - the tab's rule
        #  again (where the additive pose holds that arm, its share blending it in), and it needs no Hold
        shoulders = {}
        if pose is not None and ctx["alpha"] > 0.0:
            shoulders = dict((side, ctx["alpha"] * min(max(float(ks[side]["weapon_shoulder"]), 0.0), 1.0))
                             for side in chains if side not in out_of_pose)
            shoulders = dict((side, v) for side, v in shoulders.items() if v > SHOULDER_QUIET)
        biggest = lambda table: max([abs(v) for v in table.values()] or [0.0])
        out = {"frames": biggest(lags), "elbow": biggest(elbows), "hand": biggest(turns), "grip": grip,
               "shoulder": {"asked": sorted(shoulders), "share": {}, "deg": 0.0, "reach": {}},
               "hold": sorted(set(s for row in followers.values() for s in row)),
               "weapon": biggest(holds), "hold_cm": 0.0,
               "inherit": min(list(inherits.values()) or [1.0]),     # the least share a held hand takes
               "aim": {"asked": sorted(aims), "keep": {}, "lever": {}, "deg": 0.0, "cm": 0.0},
               "held": sorted(held),          # the sides the SCENE gives a weapon (the line's own wording)
               "out_of_pose": sorted(s for s in out_of_pose if s in chains)}
        if not chains or (max(out["frames"], out["elbow"], out["hand"]) < OVERLAP_QUIET and not holds
                          and not aims and not shoulders):
            out["frames"] = out["elbow"] = out["hand"] = out["weapon"] = 0.0
            out["hold"] = []
            return out
        kin = worlds.copy()

        def wanted(mats, lag, turn):
            """A cycle read `lag` frames earlier, its rotation read `lag + turn` earlier (Hand overlap)."""
            want = shifted_cycle(mats, lag)
            if abs(turn) >= OVERLAP_QUIET:
                want = np.array(want)
                want[:, :3, :3] = shifted_cycle(mats, lag + turn)[:, :3, :3]
            return want
        hands = {}
        if grip:
            hold = chains["r"][-1]
            late = wanted(kin[hold], lags["r"], turns["r"])
            for side, chain in chains.items():
                hand_j = chain[-1]
                hands[side] = np.array([kin[hand_j, f] @ np.linalg.inv(kin[hold, f]) @ late[f]
                                        for f in range(n + 1)])
        else:
            for side, chain in chains.items():
                if max(abs(lags[side]), abs(turns[side]), abs(elbows[side])) >= OVERLAP_QUIET:
                    hands[side] = wanted(kin[chain[-1]], lags[side], turns[side])
        if holds:
            out["hold_cm"] = self._weapon_hold(kin, n, chains, hands, holds, followers, ctx["alpha"],
                                               inherits)
        if aims:                       # after Hold / Overlap: the blade aims from where they left the hand
            levers = self._aim_levers(kin, chains, held, sorted(aims), bool(ctx.get("weapons")))
            out["aim"].update(self._weapon_aim(kin, n, chains, hands, aims, levers, ctx["alpha"]))
        hints = {}
        for side, chain in chains.items():
            if side in hands and abs(elbows[side]) >= OVERLAP_QUIET:
                hints[side] = late_bend(kin[chain[0]], kin[chain[1]], kin[chain[2]],
                                        lags[side] + elbows[side])
        base, turned = kin, {}
        if shoulders:                  # last: the clavicle follows the hand everything above has placed
            base, turned, did = self._shoulder_assist(kin, n, chains, hands, shoulders)
            out["shoulder"].update(did)
        new = self._arm_to_hand(base, n, chains, hands, hints)
        new.update(turned)
        self._reattach(worlds, kin, new, only)
        return out

    def _shoulder_assist(self, kin, n, chains, hands, shares):
        """Shoulder (2026-11-10): the clavicle turned about its own pivot so the SHOULDER follows the hand,
        and the elbow stops paying alone for every change of the arm's reach. Per frame, with d the
        shoulder-to-hand distance the frames' shoulder leaves the wanted hand at and `ref` its mean over
        the cycle:

            d' = ref + (d - ref) (1 - share)         the reach the arm is left with

        and the clavicle swings - the least turn, in the plane of its own bone and the hand - until the
        shoulder stands d' from the hand (the triangle pivot / shoulder / hand, its two other sides fixed),
        no further than SHOULDER_MAX_DEG off the frames' own, eased into it. Both ways about the mean, so
        there is no corner where it engages and the clavicle's own mean stays the frames'. At share 1 the
        arm keeps one reach and the elbow one bend; 0 is never called.
        Returns (a copy of `kin` with each turned clavicle and its arm carried rigidly - what _arm_to_hand
        rebuilds the arm from -, {clavicle: (n+1, 4, 4)}, {"share", "deg", "reach": {side: (reach before,
        after) as the most of the arm's length}}). A hand nothing has moved joins `hands` at the frames'."""
        base = kin.copy()
        turned, did = {}, {"share": {}, "deg": 0.0, "reach": {}}
        limit = math.radians(SHOULDER_MAX_DEG)
        for side, share in sorted(shares.items()):
            up_j, low_j, hand_j = chains[side]
            clav = self.parents[up_j]
            if clav < 0 or self.kind[clav] != "arm":          # no clavicle: the arm hangs off the chest
                continue
            if side not in hands:
                hands[side] = np.array(kin[hand_j])
            want = hands[side]
            arm = sum(float(np.linalg.norm(self.lt[j].mean(axis=0))) for j in (low_j, hand_j))
            P, S, H = kin[clav, :, 3, :3], kin[up_j, :, 3, :3], want[:, 3, :3]
            d = np.linalg.norm(H - S, axis=1)
            ref = float(d[:n].mean())
            after = np.array(d)
            for f in range(n + 1):
                c, h = S[f] - P[f], H[f] - P[f]
                r, D = float(np.linalg.norm(c)), float(np.linalg.norm(h))
                if r < 1e-6 or D < 1e-6:
                    continue
                e = h / D
                p = c - np.dot(c, e) * e
                if float(np.linalg.norm(p)) < 1e-6 * r:       # the clavicle points at the hand: no plane
                    continue
                p = _unit(p)
                phi = math.acos(min(max(float(np.dot(c, e)) / r, -1.0), 1.0))
                wanted = ref + (d[f] - ref) * (1.0 - share)
                phi2 = math.acos(min(max((r * r + D * D - wanted * wanted) / (2.0 * r * D), -1.0), 1.0))
                theta = phi - phi2                             # toward the hand: positive
                theta = math.copysign(soft_reach(abs(theta), SHOULDER_FREE * limit, limit), theta)
                c2 = r * (math.cos(phi - theta) * e + math.sin(phi - theta) * p)
                M = swung_about(P[f], aim_swing(c, c2))
                for j in (clav, up_j, low_j, hand_j):
                    base[j, f] = kin[j, f] @ M
                after[f] = float(np.linalg.norm(H[f] - base[up_j, f, 3, :3]))
                did["deg"] = max(did["deg"], math.degrees(abs(theta)))
            turned[clav] = base[clav]
            did["share"][side] = share
            did["reach"][side] = (float(d.max()) / arm, float(after.max()) / arm) if arm > 1e-9 else (0.0, 0.0)
        return base, turned, did

    def steady_chest(self, mats, rotation, position):
        """A cycle (n+1, 4, 4) with its own animation scaled: its turn slerped from the cycle's MEAN heading
        by `rotation` and its place pulled toward the mean by `position`, the linear travel kept. 1 / 1 is
        the cycle itself; 0 / 0 is a cycle that glides down the travel line with no turn, no bob and no sway
        - what a weapon hung on it inherits is nothing but the walk's own locomotion. The travel stays at any
        strength: without it the weapon is left behind within a cycle and the loop does not close.
        `_weapon_hold` reads the holding hand's pose in the chest's frame through it at 0 / 0 - held at its
        mean, which is what makes the hand a CHILD of the chest rather than a mix with its own animation
        (that cycle's "travel" is nothing: a closed loop)."""
        mats = np.asarray(mats, float)
        n = mats.shape[0] - 1
        per = (mats[n, 3, :3] - mats[0, 3, :3]) / float(n)
        dev = np.array([mats[f, 3, :3] - per * f for f in range(n + 1)])
        mean_p = dev[:n].mean(axis=0)
        anchor = mats[0, :3, :3]                      # the mean turn, read against frame 0 (a chest's own
        logs = np.array([log_rot(anchor.T @ mats[f, :3, :3]) for f in range(n)])   # deviations are degrees)
        mean_r = anchor @ exp_rot(logs.mean(axis=0))
        out = np.array(mats)
        for f in range(n + 1):
            out[f, :3, :3] = mean_r @ exp_rot(log_rot(mean_r.T @ mats[f, :3, :3]) * rotation)
            out[f, 3, :3] = mean_p + (dev[f] - mean_p) * position + per * f
        return out

    def _weapon_hold(self, kin, n, chains, hands, holds, followers, alpha, inherits=None):
        """The Weapon tab, rebuilt 2026-11-05 on the animator's own recipe (in place on `hands`): the hand is
        held RIGID on the chest - its offset from the chest frozen at its own MEAN over the cycle, so it stops
        playing the arm's swing and keeps the additive pose's hold on the torso - and the chest it rides is
        read `holds[side]` frames earlier, so the torso leads and the hand with whatever it holds follows
        late:

            A    = steady(H(f) . inv(C(f)), 0, 0)      the hand's offset from the chest, held at its mean
            want = shifted(steady(C, k, k), lag)       the chest's own pose, that many frames old
            H'(f) = blend(H(f), A . want(f), alpha)    the pose's share blends it in

        `k` is Inherit (`inherits[side]`, 2026-11-10): the share of its own motion the chest hands on - its
        turn slerped from its mean heading and its place pulled toward its mean, the travel kept
        (steady_chest). 1 is the chest as it is, read untouched; 0 a chest that only travels, so the hand
        stands still in the frame the cycle travels in - «0 процентов полная статика».

        It needs NO weapon in the scene: the hand is the lever, and a weapon in it follows by its own
        constraint (the plugin's weapon space is parent-constrained to the hand with no offset). Hands that
        hold one thing are one `followers` row - the carrier drives and the others take its own delta, so the
        grip is kept to machine precision - and _arm_to_hand rebuilds each arm, so the arm follows the hand.
        At Pose 0 (alpha 0) nothing of this runs at all and the arms play the cycle. Returns the most a hand
        moved, cm (the line's "the hand rides the chest")."""
        chest = self._chest_joint()
        if chest is None or alpha <= 0.0:
            return 0.0
        moved = 0.0
        C = np.asarray(kin[chest], float)
        inv_c = np.linalg.inv(C)
        for side, lag in sorted(holds.items()):
            for s in followers.get(side, [side]):
                if s not in hands:             # a hand with no lag of its own joins at the frames' own
                    hands[s] = np.array(kin[chains[s][-1]])
            H = np.array(hands[side], float)
            arm = self.steady_chest(H @ inv_c, 0.0, 0.0)       # the offset held at its mean: a parent, not a mix
            keep = 1.0 if inherits is None else float(inherits.get(side, 1.0))
            want = shifted_cycle(C if keep >= 1.0 - INHERIT_QUIET else self.steady_chest(C, keep, keep), lag)
            inv_h = np.linalg.inv(H)
            for f in range(n + 1):
                full = blend_matrix(H[f], arm[f] @ want[f], alpha)
                T = inv_h[f] @ full
                for s in followers.get(side, [side]):
                    hands[s][f] = hands[s][f] @ T
                moved = max(moved, float(np.linalg.norm(full[3, :3] - H[f, 3, :3])))
        return moved

    def _aim_levers(self, kin, chains, held, sides, scene_has_weapons):
        """{side: (grip, aim point, "weapon" | "bone")} - the blade each of `sides` aims with, as two points
        in that hand's own frame: the weapon the SCENE holds in the hand (its grip, and its tip pushed
        AIM_REACH past - where Aim Mode stands its target); and, where the scene holds no weapon at all, the
        right hand's weapon BONE stands for one - the grip on the bone, AIM_BLADE along its +Z (UE's socket,
        which every catalog weapon lies along at zero grip), read where the frames hold the bone in the hand
        (a pose's own grip is in it). The tab has worked with no weapon in the scene since 2026-11-05, and
        the animator's own road puts the sword on the rig after the walk is built. A side with neither has
        no lever and is left out."""
        out = {}
        for side in sides:
            if side in held:
                grip, tip = (np.asarray(held[side][key], float) for key in ("grip", "tip"))
                if float(np.linalg.norm(tip - grip)) > 1e-6:
                    out[side] = (grip, grip + (tip - grip) * AIM_REACH, "weapon")
        if not scene_has_weapons and "r" in sides and "r" not in out:
            hand = chains["r"][-1]
            for h, (body, _rel) in sorted(self.follows.items()):
                if self.names[h] == "weapon_r" and body == hand:
                    rel = kin[h, 0] @ np.linalg.inv(kin[hand, 0])
                    grip = np.array(rel[3, :3], float)
                    out["r"] = (grip, grip + _unit(rel[2, :3]) * AIM_BLADE * AIM_REACH, "bone")
                    break
        return out

    def _weapon_aim(self, kin, n, chains, hands, aims, levers, alpha):
        """Aim target (2026-11-10, in place on `hands`): the animator's example - the weapon in Aim Mode, its
        aim target's keys thinned out «для придания веса оружию». The grip plays the whole animation and the
        blade points at a target that keeps only a share of its own motion:

            G(f) = grip . H(f)       T(f) = aim . H(f)        the blade's line, where the hand has it
            T'   = damped(T, keep)                             the target, pulled toward its mean
            H'(f) = H(f) . swung_about(G(f), aim_swing(T - G, T' - G))

        A swing about the grip, so the grip does not move; the minimal one, so the roll about the blade
        stays the animation's (the example's up target keeps every key). `keep` 1 is the whole animation,
        0 a target standing still in the frame the cycle travels in; the pose's share blends it in. The
        hands of one `aims` row swing together, so a two-handed hold is kept to machine precision, and
        _arm_to_hand rebuilds each arm. Returns {"keep": {side: the share kept}, "lever": {side: kind},
        "deg": the most a blade swung, "cm": the most its target moved}."""
        out = {"keep": {}, "lever": {}, "deg": 0.0, "cm": 0.0}
        for side, (keep, riders) in sorted(aims.items()):
            if side not in levers:
                continue
            grip, aim, kind = levers[side]
            for s in riders:
                if s not in hands:             # a hand nothing has moved yet joins at the frames' own
                    hands[s] = np.array(kin[chains[s][-1]])
            H = np.array(hands[side], float)
            G = np.array([grip @ H[f, :3, :3] + H[f, 3, :3] for f in range(n + 1)])
            T = np.array([aim @ H[f, :3, :3] + H[f, 3, :3] for f in range(n + 1)])
            share = 1.0 - alpha * (1.0 - keep)
            want = damped_points(T, share)
            for f in range(n + 1):
                a, b = T[f] - G[f], want[f] - G[f]
                M = swung_about(G[f], aim_swing(a, b))
                for s in riders:
                    hands[s][f] = hands[s][f] @ M
                cos = float(np.dot(_unit(a), _unit(b)))
                out["deg"] = max(out["deg"], math.degrees(math.acos(min(max(cos, -1.0), 1.0))))
                out["cm"] = max(out["cm"], float(np.linalg.norm(want[f] - T[f])))
            out["keep"][side], out["lever"][side] = share, kind
        return out

    def _grip_motion(self, kin, n, chains, w0, zeta, S, hold_side="r"):
        """Two hands holding one thing: ONE hand carries it - its world turn and place trail their target
        through the same spring (the travel taken out); the other keeps its hold on it; both arms reach their
        hands by IK (the elbows bend the way the frames bend them, the bones keep their lengths). The carrier
        is the hand the weapon is in under 2H, and the right hand for a pose's own grip (2026-11-04)."""
        dt = 1.0 / S
        hold = chains[hold_side][-1]
        R = np.array([orthonormal(kin[hold, f, :3, :3]) for f in range(n + 1)])
        travel = (kin[hold, n, 3, :3] - kin[hold, 0, 3, :3]) / float(n)
        path = np.array([kin[hold, f, 3, :3] - travel * f for f in range(n + 1)])
        path[n] = path[0]
        steps = np.arange(n * S) / float(S)
        f0 = np.floor(steps).astype(int)
        frac = (steps - f0)[:, None]
        target_x = (1.0 - frac) * path[f0] + frac * path[f0 + 1]
        target_r = self._resampled(R, n, S)
        state_r, w = R[0].copy(), np.zeros(3)
        x, v = path[0].copy(), np.zeros(3)
        rec_r, rec_x = np.zeros((n, 3, 3)), np.zeros((n, 3))
        kk, cc = w0 * w0, 2.0 * zeta * w0
        used = 0
        for cycle in range(ARM_CYCLES):
            used = cycle + 1
            first = (state_r.copy(), x.copy())
            for step in range(n * S):
                if step % S == 0:
                    rec_r[step // S], rec_x[step // S] = state_r, x
                e = _log3(target_r[step].T @ state_r)
                w = w + (-kk * e - cc * w) * dt
                state_r = state_r @ _exp3(w * dt)
                v = v + (-kk * (x - target_x[step]) - cc * v) * dt
                x = x + v * dt
            if float(np.linalg.norm(_log3(first[0].T @ state_r))) < ARM_SETTLED and \
                    float(np.linalg.norm(first[1] - x)) < ARM_SETTLED * 100.0:
                break
        miss_r, miss_x = _log3(rec_r[0].T @ state_r), x - rec_x[0]
        held = np.tile(np.eye(4), (n + 1, 1, 1))
        for f in range(n + 1):
            g = f % n
            held[f, :3, :3] = rec_r[g] @ _exp3(-miss_r * g / float(n))
            held[f, 3, :3] = rec_x[g] - miss_x * g / float(n) + travel * f
        hands = {}
        for side, chain in chains.items():
            hand_j = chain[-1]
            hands[side] = np.array([kin[hand_j, f] @ np.linalg.inv(kin[hold, f]) @ held[f]
                                    for f in range(n + 1)])
        return self._arm_to_hand(kin, n, chains, hands), used

    def _reattach(self, worlds, kin, new, only=None, held=()):
        """`new` ({joint: (n+1, 4, 4)}) into `worlds`; every joint hanging off a changed one (its DAG children,
        the helpers that follow it) carried along as the frames had it on its anchor (of `only`, when given) -
        a joint in `held` keeps the world turn the frames give it (it hangs in the world), its place carried."""
        changed = set(new)
        for j, m in new.items():
            worlds[j] = m
        for j in self.order:
            if j in changed or (only is not None and j not in only):
                continue
            p = self.parents[j]
            anchor = p if p in changed else None
            if anchor is None and j in self.follows and self.follows[j][0] in changed:
                anchor = self.follows[j][0]
            if anchor is None:
                continue
            worlds[j] = np.einsum("fij,fjk->fik", np.einsum("fij,fjk->fik", kin[j], np.linalg.inv(kin[anchor])),
                                  worlds[anchor])
            if j in held:
                worlds[j, :, :3, :3] = kin[j, :, :3, :3]
            changed.add(j)

    def _leg_source(self, side, tau, ctx):
        """What a leg's solve takes from the source and the knobs at tau - all of it independent of the hip."""
        k = ctx["k"]
        th, ca, fo = (self.index["%s_%s" % (b, side)] for b in LEG)
        foot_rot, ankle, t = self._foot(side, tau, ctx)      # the leg at its foot's own time (Foot placement)
        knee_turn = ctx["turns"][side][0]
        l1, l2 = float(np.linalg.norm(self.lt_at(ca, t))), float(np.linalg.norm(self.lt_at(fo, t)))
        h, kn, a = self.wpos(th, t), self.wpos(ca, t), self.wpos(fo, t)
        e = _unit(a - h)
        bend = self.knee_plane(side, t, e)          # the cycle's own, continuous (_knee_planes)
        knee_bend = turned_about(bend, -e, knee_turn) if knee_turn else bend      # turned about the leg
        hang = self.swing_at(side, t)
        return {"joints": (th, ca, fo), "t": t, "hip": self.lt_at(th, tau), "foot_rot": foot_rot, "ankle": ankle,
                "lengths": (l1, l2), "dirs": (_unit(kn - h), _unit(a - kn)), "normal": _unit(_cross3(e, bend)),
                "bend": knee_bend, "wrot": (self.wrot(th, t), self.wrot(ca, t)), "hang": hang,
                "in_calf": (self.foot_in_calf(side, t - ctx["foot_lag"][side], ctx["ks"][side]["foot_flex"])
                            if hang > 0.0 else None)}

    def _leg(self, side, tau, rots, poss, ctx, cache=None, rolls=None):
        """Thigh, calf and foot by IK from the new hip to the new foot; each bone turned by the rotation
        taking its source (direction, leg plane) onto the new one. Returns how far the foot fell short.
        `cache` ({side: _leg_source}) spares the source half when only the hip moves; `rolls` takes the foot's
        roll over its ball ({side: world turn}), which its toes take back."""
        src = None if cache is None else cache.get(side)
        if src is None:
            src = self._leg_source(side, tau, ctx)
            if cache is not None:
                cache[side] = src
        th, ca, fo = src["joints"]
        pelvis = self.parents[th]
        hip = src["hip"] @ rots[pelvis] + poss[pelvis]
        foot_rot, ankle, turn = self._roll_turn(side, src["t"], src["foot_rot"], src["ankle"],
                                                self._roll_of(side, tau, ctx), self._asked_of(side, tau, ctx))
        if turn is not None and rolls is not None:
            rolls[side] = turn
        reel = self._reel_of(side, tau, ctx) * self.swing_at(side, src["t"])     # in the air only
        if reel > 0.0:
            reach = ankle - hip
            d = float(np.linalg.norm(reach))
            ankle = hip + reach * max(0.0, 1.0 - reel / d) if d > 1e-9 else ankle
        reach = self._leg_reach(side, src["t"], ctx)
        knee, reached, short = two_bone(hip, ankle, src["lengths"][0], src["lengths"][1], src["bend"], reach,
                                        self._soft_from(side, src["t"], ctx, reach))
        e2 = _unit(reached - hip)
        # the new leg's plane is the one it was bent toward, not the one its solved knee happens to stand in:
        # a result leg that comes out straight has no plane of its own either, and reading it there put the
        # noise back (2026-10-30, _knee_planes). two_bone bends in the hint's plane, so this is the same
        # plane wherever the knee is off the line at all
        bend2 = src["bend"] - np.dot(src["bend"], e2) * e2
        if np.linalg.norm(bend2) > 1e-9:
            bend2 = _unit(bend2)
        else:
            bend2 = _unit((knee - hip) - np.dot(knee - hip, e2) * e2)
        n_new = _unit(_cross3(e2, bend2))
        rots[th] = src["wrot"][0] @ align(src["dirs"][0], src["normal"], _unit(knee - hip), n_new)
        rots[ca] = src["wrot"][1] @ align(src["dirs"][1], src["normal"], _unit(reached - knee), n_new)
        rots[fo] = foot_rot if src["hang"] <= 0.0 else toward(foot_rot, src["in_calf"] @ rots[ca], src["hang"])
        poss[th], poss[ca], poss[fo] = hip, knee, reached
        return short


class Result(object):
    """The new cycle: world matrices (J, N+1, 4, 4) in the source's world, N, and what happened."""

    def __init__(self, worlds, frames, info):
        self.worlds, self.frames, self.info = worlds, frames, info


def share_line(info):
    """What Arms % and Hands % hold back, for a status line ("" at their own 100 %). `info["knobs"]` is
    the asked dict and engine_knobs writes a key only where the parameter was asked, so every read
    falls back - the side's own value, then the knob's, then 1.0 (2026-11-04)."""
    k = info.get("knobs") or {}
    out = []
    for knob, many, one in (("arms", "arms", "arm"), ("hands", "hands", "hand")):
        both = float(k.get(knob, 1.0))
        per = dict((s, float(k.get("%s_%s" % (knob, s), both))) for s in SIDES)
        if abs(per["l"] - per["r"]) < 1e-9:
            if abs(per["l"] - 1.0) > 1e-9:
                out.append("the %s keep %.0f %%" % (many, 100.0 * per["l"]))
        else:
            for s, word in (("l", "left"), ("r", "right")):
                if abs(per[s] - 1.0) > 1e-9:
                    out.append("the %s %s keeps %.0f %%" % (word, one, 100.0 * per[s]))
    return (" | " + ", ".join(out) + " of the cycle") if out else ""


def hold_line(info):
    """What the Weapon tab's Hold did, for a status line ("" with no hand held): who rides the chest, how
    much of its motion they take (Inherit) and how late (Overlap)."""
    swung = (info.get("arms") or {}).get("overlap") or {}
    if not swung.get("hold"):
        return ""
    both = len(swung["hold"]) > 1
    who = "both hands" if both else "the %s hand" % {"l": "left", "r": "right"}[swung["hold"][0]]
    keep = float(swung.get("inherit", 1.0))
    if keep < 0.005:
        return " | %s %s still: none of the chest's motion" % (who, "stand" if both else "stands")
    text = " | %s %s the chest" % (who, "ride" if both else "rides")
    if keep < 1.0 - INHERIT_QUIET:
        text += " at %.0f %% of its motion" % (100.0 * keep)
    if swung.get("weapon"):
        text += ", %.1f fr late (moved %.1f cm)" % (swung["weapon"], swung["hold_cm"])
    return text


def aim_line(info):
    """What Aim target did, for a status line ("" at its own 1): the share of its motion the blade's target
    keeps and the most the blade swung to it, or why a dialled knob did nothing."""
    aim = ((info.get("arms") or {}).get("overlap") or {}).get("aim") or {}
    if aim.get("keep"):
        keep = min(aim["keep"].values())
        what = "a static target" if keep < 0.005 else "a target keeping %.0f %% of its motion" % (100.0 * keep)
        return " | the blade aims at %s (swung up to %.0f deg)" % (what, aim.get("deg", 0.0))
    if aim.get("asked"):
        return " | no weapon in the hand and no weapon bone: Aim target does nothing"
    return ""


def shoulder_line(info):
    """What Shoulder did, for a status line ("" at its own 0): the share of the arm's reach the clavicle
    takes, how far it turned, and the most the arm is stretched before and after."""
    did = ((info.get("arms") or {}).get("overlap") or {}).get("shoulder") or {}
    if not did.get("share"):
        return ""
    side = max(did["reach"], key=lambda s: did["reach"][s][0])
    before, after = did["reach"][side]
    return (" | the shoulder takes %.0f %% of the arm's reach (the clavicle turns up to %.0f deg, the arm "
            "stretched %.0f -> %.0f %%)" % (100.0 * max(did["share"].values()), did["deg"], 100.0 * before,
                                            100.0 * after))


def describe(result):
    info = result.info
    text = "%d frames, stride %.1f cm, %.2f m/s" % (info["frames"], info["stride_cm"], info["speed"])
    if info.get("in_place", 0.0) > 0.0:
        text += " in place" if info["in_place"] >= 1.0 else " (%.0f %% in place)" % (100.0 * info["in_place"])
    if info["lowered"] > 0.05:
        text += " | pelvis lowered up to %.1f cm at the contacts for the reach" % info["lowered"]
    if info.get("height_straighten", 0.0) > 0.0 and info["knobs"]["pelvis_height"] > 0.0:
        text += " | the planted knees straightened for the Height"
    if info.get("height_step", 1.0) < 0.999:
        text += " | Height shortened the step to %.0f %% (the legs could not reach it)" % (100.0 * info["height_step"])
    if info.get("passing"):
        p = info["passing"]
        got = ["%.0f" % p["got"][s] for s in SIDES if s in p["got"]]
        asked = ["%.0f" % p["asked"][s] for s in SIDES if s in p["asked"]]
        text += " | the passing knee %s deg (asked %s), the hips up to %.1f cm higher there" % (
            " / ".join(got), " / ".join(asked), p["lift"])
        left = max([p["short"].get(s, 0.0) for s in SIDES] or [0.0])
        held = max([(p.get("paced") or {}).get(s, 0.0) for s in SIDES] or [0.0])
        if left > 1.0 and held > 0.5 * left:
            text += " - the pace held it %.0f deg short: a knee turns no faster than the cycle's own" % left
        elif left > 1.0:
            text += " - the legs left %.0f deg on the table: a shorter Step gives the rest" % left
    if info["short"] > 0.005:
        text += " | a foot falls %.1f cm short of its step" % info["short"]
    if info.get("swing_in", 0.0) > 0.5:
        text += " | the swinging foot passes up to %.1f cm nearer the body" % info["swing_in"]
    turn = lambda v: "+-%.1f%s" % (abs(v), " reversed" if v < 0.0 else "")
    if "pelvis" in info:
        text += " | pelvis twists %s deg, the hips %s" % tuple(turn(v) for v in info["pelvis"])
    if info.get("chest"):
        text += " | chest twists %s deg, sways %s" % tuple(turn(v) for v in info["chest"])
    body = info.get("body") or {}
    drags = [(name, d) for name, d in (("the trunk", body.get("drag", (0.0, 0.0))[0]),
                                       ("the head", body.get("drag", (0.0, 0.0))[1])) if d > 0.0]
    if drags:
        text += " | %s frames behind" % " and ".join("%s %.1f" % (name, d) for name, d in drags)
    if info.get("arms") and info["arms"].get("drag"):
        a = info["arms"]
        text += " | %s %.1f frames behind the body%s" % (
            "the held weapon trails" if a["grip"] else "the arms trail", a["drag"],
            ", bouncing" if a["bounce"] > 0.05 else "")
    return text + hold_line(info) + aim_line(info) + shoulder_line(info) + share_line(info) + placement_line(info) + balance_line(info)


def placement_line(info):
    """What Foot placement did, for a status line ("" when it is off)."""
    placed = info.get("placement") or {}
    if placed.get("note") and info["knobs"]["foot_placement"] > 0.0:
        return " | no foot placement: " + placed["note"]
    if not placed.get("on"):
        return ""
    both = " / ".join("%.1f" % placed["double"][s] for s in SIDES if s in placed["double"])
    return " | feet planted (slides of up to %.1f cm held), both feet down %s frames a step" % (placed["slide"], both)


def balance_line(info):
    """What Balance did, for a status line ("" when nothing worth saying)."""
    balance = info.get("balance") or {}
    if balance.get("note"):
        return " | no balance: " + balance["note"]
    if balance.get("carry", 0.0) > 0.1:
        return (" | balance: the pelvis carried up to %.1f cm over the feet (the CoM sways %.1f cm, the source's "
                "%.1f)" % (balance["carry"], balance.get("sway", 0.0), balance.get("source_sway", 0.0)))
    return ""
