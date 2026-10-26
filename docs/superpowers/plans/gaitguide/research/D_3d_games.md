Agent "3D walk/run curves and game locomotion" finished

I found per-channel guidance for most of the walk curves, and Epic's docs and the primary papers on the game side. A few named sources (Kenny Roy, Jason Ryan, "Sergio", Bobby Anguelov) and some rig topics could not be researched (details at the end).

**Labels:** unmarked facts were read on the page cited. **[S]** = seen only in search-result text (the page refused my fetcher). **[D]** = my own arithmetic from cited numbers. **[U]** = not confirmed. Numbers in brackets refer to the URL list at the bottom.

## 1. Workflow

**Order of work**
- Hips and feet first (contacts, then downs and ups), then spine counter-rotation, arms, head, polish [7][3].
- Cave Academy refines "from the root outward": hips (a figure-8 checked with an editable motion trail), legs and feet, spine, neck and head, arms [1].
- Ward's game book does legs plus Root_Control, then torso, then arms and clavicles [2].
- Rig use: legs in IK, arms in FK [1][5]. Rusty switches the arms from IK to FK "for natural joint dependency" [3].

**Poses and frames (24 fps, 12 frames per step)**
- Contacts at 1/13/25, downs at 4/16, passing at 7/19, ups at 10/22 [3][21][9]. Cave uses the same frames at 25 fps [1].
- Frame 25 equals frame 1, so the timeline and the render stop at 24 [1][9].
- Where the down goes: "one or two frames after the contact" [5], or "a couple of frames after" [12]. The up goes about halfway between passing and contact [12].
- Breakdowns are not centred: "The more it is off center the more pronounced the arc" [13].
- Ward (game book): timeline 0–32, extremes at 0 and 32, breakdown at 16, in-betweens at 8 and 24 [2].
- Digital Tutors: a 33-frame cycle with poses every 4 frames [11].

**Blocking, then splining**
- Block with stepped default out-tangents [1][13].
- Then set every curve to Spline or Auto, except foot translateZ while the foot is on the ground, which stays Linear [1][6].
- Animation Mentor's Martinsen tutorial does the same: auto tangents, foot translation linear [S].

**In place vs moving forward**
- Moving: root translateZ is "a continuous straight line" with only the first and last keys, Linear, and post-infinity set to Cycle with Offset [2][5].
- Moom uses Cycle with Offset for hip and foot translateZ and plain Cycle for everything else [5]. AnimSchool and Digital Tutors put Cycle with Offset on all curves [8][11]. [D] That is harmless on any channel whose first and last keys are equal.
- Loop seam: match the first and last frame, smooth the tangents at both ends, and check with Graph Editor › View › Infinity [1][11][6].

**Making the foot slide at constant speed (in place)**
- Keep the planted foot's backward translation "constant while it's flat" [1].
- Digital Tutors: the left foot moves back linearly from 1 to 17, then eases up [11].
- Linear or clamped tangents give even spacing along translateZ for the planted foot [13].
- The two contact poses must be exact opposites "to avoid foot slip" [12]. Stride lengths must be equal [5].
- To match the root to the feet: copy the straight foot section, flip it onto the root and extrapolate linearly. "The root controller… will move forward at the same rate as the feet are sliding back" [22].
- [D] Slide speed = step length ÷ step time. A 72 cm step on 12s at 24 fps is 1.44 m/s, or 6 cm per frame.

**Checking travel**
- Ward parents the camera to a locator that follows the root [2].
- The SIGGRAPH exercise moves a ground plane linearly by two strides per cycle (400 units per 32 frames) [10].
- Motion trails or arc trackers on the hips and hands [1][3].

## 2. The curves (walk; one cycle = two steps)

| Channel | Shape over the cycle | Extremes / cycle | Where the extremes fall | Tangents | Typical values |
|---|---|---|---|---|---|
| **COG translateY (bob)** | Two waves, like an inverted bouncing ball: "fast into the down, slow over the up" [7] | 2 lows, 2 highs | Lows: the down, 1–2 frames after each contact [5][12]; biomechanics puts the minimum at mid double support, ~5% and 55% of the cycle [23]. Highs: biomechanics at mid single support, ~30% and 80% [23], which is the passing pose (Moom keys the high there [5]). Many animators put the high at the "up" instead [8][3]. [D] On a 24-frame cycle, 30% is frame 7 (passing) and 5% is about frame 2. | Spline; the Y values at the two contacts match | ≈5 cm total [23][24]; Digital Tutors lowers the COG "slightly" at the down [11] |
| **COG translateX (sway)** | One wave | 1 left, 1 right | Over the stance foot; peak at passing (biomechanics 30% and 80% [23]; "passing is usually the extreme" [17]) | Ward: flat tangents at the extremes | 4 cm total [23] to 6 cm [24]; Ward ±0.015 scene units keyed at the passing frames 0/16/32 [2] |
| **COG/root translateZ** | Moving: a straight line. In place: flat, or a small surge | — | The body brakes in double support (peak deceleration at 46–53% of the cycle, just before the opposite toe-off) [25] | Linear, Cycle with Offset [2][5] | Speed ≈1.37 m/s for an average adult [23]. Ripples in this curve read as stop-start [17] |
| **Hip rotateY (twist)** | One wave | 1 / 1 | Contact: turned toward the front foot [3][5][12]. Passing: hips and shoulders parallel [10] | Spline. A stylised female walk swings contact→passing in ~3 frames [6] | Biomechanics ±3–4° [23]. Ward keys 10° [2] |
| **Hip rotateZ (tilt)** | One wave | 1 / 1 | Swing-leg side low from the down to passing: Digital Tutors keys it at the down [11]; "Tilt hips so that passing side is low" [13][12]. Ward holds it until the foot plants, then reverses [2]. **Conflict:** Rusty rotates the hips *up* on the lifted side at passing [3] | Ward: flat tangents plus hold keys | Ward ±7°, with 1.7° holds at frames 11/27 [2]; ~5° [S, UW]. Biomechanics: the swing side dips early in stance and rises from 20% to 60% [23] |
| **Hip rotateX** | Two small waves | 2 / 2 | Forward at contact or down, back toward upright near passing [5] | Spline | Pelvic tilt 2–4° total [23] |
| **Foot translateZ (in place)** | Sawtooth: a linear slide back during stance, a quick S-curve forward in swing | 1 max, 1 min | Max at heel contact; min at toe-off (60% of the cycle, so stance ≈60%, swing 40%) [23]. Tutorials often make the slide exactly half the cycle and let the toe peel [11] | Linear while on the ground; break the tangents at the first and last ground keys; spline in the air [1][6]. CAT: slower moves get more ease in the air, runs are "almost linear" [28] | [D] With a 60/40 split the swing foot averages 1.5× the body speed relative to the hips (2.5× in world space) |
| **Foot translateY** | Flat at 0 in stance (the pivots do the peeling), one arc in swing | 1 peak per foot | Around passing, when the feet are adjacent (73% of the cycle, where the knee peaks at 60° [23]); Rusty lifts it "high and close to the body" at passing [3] | Flat on the ground keys, or a spline can push the foot under the floor [S, UW]. Ward deletes extra keys and lowers the highest ones if they read too high [2] | Real toe clearance is only 1.2–1.9 cm at mid-swing [23] |
| **Foot rotateX / roll** | Toes up at the strike, slap flat, flat through stance, heel peel, roll over the ball, toe flick in swing | heel peak + ball peak | Flat 2–3 frames after contact [5]; Roll=0 two frames after contact with the toe slap about 1 frame later, "four frames to become flat" [1]; heel-off at 30–40% of the cycle [23]; ball peaks before lift-off [2] | Fast; flat stretches in the roll curve read as pauses [S] | Ankle 0–5° plantarflexion at contact; [D] so the foot is ≈20–25° toes-up. Toe joint 45–55° at push-off; 15–20° plantarflexion after toe-off [23]. Ward ball_rotate 45° [2] |
| **Knee / pole vector** | Follows the foot | — | Knee 5° at contact, +10–15° loading, 35° at toe-off, 60° max in swing [23] | — | Key the pole vectors "otherwise his legs will twist as the walk moves forward" [5]; Ward adds a slight inward knee bend [2] |
| **Spine/chest rotateY** | One wave, opposite the hips, growing up the spine | 1 / 1 | At contact, opposite the hips [5][1]; each level a little later [6][18] | Spline | Shoulder girdle 7–9° total, opposite the pelvis [23]; Ward 2° on each of 3 spine controls [2] |
| **Spine/chest rotateZ** | One wave, opposite the hip tilt | 1 / 1 | Upper-body Z extreme 2 frames after passing [3] | Ward: flat | Ward ±1.5° [2] |
| **Chest rotateX (lean)** | Two waves | 2 / 2 | Forward at contact, back near passing [5]; X extreme 2 frames after the down [3] | — | Ward 2° / 0.7° [2] |
| **Shoulders / clavicles** | Tilt opposite the hips (one wave); each clavicle dips as its arm passes the body (two per cycle) | — | Rusty drops the shoulder on the passing frames 7/19 [3]; the forward-swinging shoulder goes forward and up [11] | Ease in and out of the high at contact [3] | — [13][10] |
| **Arm (FK upper arm)** | A pendulum opposite the same-side leg; elbow and wrist drag behind | 1 / 1 | At contact [5], or Rusty at the down (frames 4 and 16). Elbow +2 frames, hand +2 more [3]. Ward adds a 4-frame pause after each extreme [2] | Spline | Shoulder from 25° back at same-side heel contact to 10° forward (≈35° total, biased backward); elbow 20°→45° [23] |
| **Head** | Y counters the chest; X nods, lagging | X: 2 / 2 | Nodded forward as the body rises after the down, upright at passing [5]. Neck keys delayed 2 frames, head 1–2 more [1]. Chest low 2 frames after the hips; head translate 2 after that; head rotate 1 after that [12] | — | "Level-ish"; too much bob reads as pecking [7]; keep the eyes forward [10] |

**Runs**
- Frames (Rusty, on 8s): contacts 1/9/17, downs 3/11, passing 5/13, ups 7/15. Both feet are in the air for at least 2 frames [4].
- The down (mid-stance) is the lowest hip point and the extreme forward bend; the up is the highest point and the extreme backward bend, with both feet off the ground [4].
- Measured: the COM low point falls at 50% of stance at 3.5 m/s and 57% at 4.9 m/s. Stance is 38% of the stride at 3.5 m/s and 32% at 4.9 m/s [27].
- Offsets from the key poses (Rusty): hips X +2, Z +1, Y −1; chest X +3, Z +2, Y 0; head X +4, Z +3, Y +1. Hip and torso Y are zeroed and the Z apex falls at passing [4].
- Arms "pump harder with the elbows bent"; keep "height in the hips" during the flight [15]. Sprint lean 15–30° [48].

## 3. Numbers

**Frames per step at 24 fps**
- 12 = natural walk, "on 12s", about 2 steps a second [8][7]; it is "march time" [16].
- 8 = brisk walk; 16 = heavy or relaxed walk [7].
- Monmouth chart, in frames per cycle: 8 very fast run, 12 run or very fast walk, 16 slow run or cartoon walk, 24 natural walk, 32 stroll, 40 elderly or tired, 48 slow step. Its per-step figures in brackets are inconsistent [9].
- Runs: 12–16 frames per cycle [15]. At 30 fps, a run is 16–20 frames per cycle and a sprint 12–16 [48].

**At 30 and 60 fps [D]**
- 12 frames at 24 fps = 15 at 30 = 30 at 60.
- An average real cadence of 110 steps/min [23] is 13.1 frames per step at 24 fps and 16.4 at 30.
- Walk turns into run at about 180 steps/min [23], which is 8 frames at 24 or 10 at 30.

**Distances and speeds**
- Average adult walk: step 72 cm, stride 1.44 m, 1.37 m/s, step width 8–10 cm, toe-out 5–7°; stance 60%, double support 0–10% and 50–60% of the cycle [23]. [U] Values for a 1.8 m man would be somewhat larger; no source was found.
- Run [D]: 3.5 m/s at 180 steps/min is a 1.17 m step, a 2.33 m stride.
- Unreal blend space example speeds: walk ~150, run ~400, sprint ~600 cm/s [48].

**Bob and sway**
- Walk: ≈5 cm vertical [23][24]; lateral 4 cm [23] to 6 cm [24].
- Run: 7.2–7.8 cm measured [27]; Garmin's typical band is 8.2–9.7 cm (chest sensor) and below 6.4 cm for the most efficient runners [26].

**Rotations**
- Pelvis ±3–4° twist, 2–4° tilt; shoulder girdle 7–9° total; arm swing ≈35°; elbow 20–45° [23].
- Animation keys in Ward's game walk: hip twist 10°, hip tilt 7°, spine 3×2° [2].

**Overlap offsets**
- Elbow +2 frames and hand +4 behind the upper arm [3]; forearm 2–3 frames behind [5]; forearm and wrist 1–2 frames each [6].
- Neck 2 frames late, head 1–2 more [1].
- Arms "a frame or two" behind the legs [7].

## 4. Problems and fixes

- **Foot sliding.**
  - Causes: a stance segment that is not linear [1][13], contact poses that are not exact opposites [12], unequal strides [5], ripples in the root's translateZ [17], a root that moves at a different speed from the slide [22], and IK feet that drift if left unchecked [7].
  - In game blend spaces: clips with different strides per loop (one example: 180 cm forward against 120 cm strafe) [48].
- **Knee pop** [S, forum threads]: lower the COG on the frame the leg goes fully straight; never fully extend; the knee pops when it goes from straight to bent too fast, the heel rises too much, the foot is too far from the hip, or the hips are too high. Soft IK hides the pop but makes the planted foot slide.
  - Opened pages agree: fix knee pops frame by frame with foot stretch and hip adjustments [3], use a knee deformer through contact and down [6], or add "more bend to the knee" [19].
- **Floating:** there is no down, or the down is too shallow [7]; runs need a higher hip in the flight for "a more dramatic drop" [15].
- **Robotic symmetry ("twinning"):** offset the limbs [7], let the chest and arms differ from the mirrored pose [12], offset arm timing [2]. Real runners are asymmetric: 6.0 cm on one step against 8.4 cm on the other [27].
- **"Stop-motion" look:** forward travel came from the spine parts instead of one motion control [18].
- **Gimbal:** put the main swing axis first in the rotate order (Rusty's example: xyz to zyx when Z is the swing) [3]. [U] The usual rule that the middle axis must stay away from 90° and the use of the Euler filter were not confirmed.
- **Twist in the wrong direction:** the pelvis turns *toward* the front foot at contact [3][5][12].
- **Toes in the ground:** flatten the tangents on the contact keys [S, UW]; bend the toes if they hit the floor in swing [10]; check every view for floor intersections [11].
- **Pops at the loop:** see section 1.

## 5. Game locomotion

**Root motion vs in place**
- Unreal root motion moves the capsule with the root bone. Without it, the mesh "disconnects… before snapping back" at the end of the cycle. Root lock options: Ref Pose, first frame, zero [33].
- Unity: Bake Into Pose for rotation, Y position and XZ position; the root is the body's projection on the ground plane [47].
- Holden compares code-driven and data-driven displacement:
  - syncing the character to the capsule can feel "floaty… foot sliding";
  - syncing the capsule to the animation can feel sluggish;
  - he favours a damped correction toward the capsule, clamped, plus little foot locking [41].

**Matching speed**
- Unreal's set-play-rate-to-match-speed node "assumes that the animation has a constant speed"; the default clamp is 0.75–1.25 [30].
- Stride warping: StrideScale = locomotion speed ÷ root-motion speed. The node moves the IK feet and pelvis and has a maximum pelvis displacement [31].
- Lyra's blog gives a 15–20% maximum play-rate or warp adjustment; past that, foot sliding is preferable [S, 38].
- Paragon warps stride by up to 60%, plus 15% from play rate, dropping the hips when the IK targets are out of reach [40].

**Sync groups and markers**
- The leader sets the length and followers adjust their speed [32].
- Markers such as "Right Foot Down": "Only markers common to all animations within a group are synced."
- Clips need the same planted feet at their first and last frames, and should avoid large length differences [32].

**Distance matching**
- The animation is driven by a distance curve, not time. XY is for starts, stops and pivots; Z for landings. The curve comes from the Distance Curve Modifier [29].
- A stop seeks the frame matching the remaining distance and "doesn't respect phase" of the previous jog [30].
- Lyra: distance matching on starts, handing over to stride warping toward the jog. Orientation warping covers limited directional coverage (the default 90° threshold is the node's [31]). Turn in place uses a root yaw offset [35].

**Foot IK and ground**
- Slope warping: feet follow the floor normal, with a maximum step height and pull-pelvis-down. Epic marks it as in development [31].
- The Foot Placement node decides when feet lock from root-motion speed or a per-foot speed curve [37].
- For Honor: foot IK with toe locking, hip lowering on slopes [39].

**Motion matching (Clavet, GDC 2016)**
- Data: mocap dance cards of walks and runs, starts and stops, circles, plant-and-turns at 45/90/135/180°, and strafes.
- Each candidate frame is scored on ~10 pose factors (feet position and velocity, a few bones, weapon) plus its future trajectory.
- Brute-force search; time scaling limited to 10% faster or 20% slower; the character kept within 15 cm of the simulated point; "predictable" over "responsive" [39][40].
- Unreal's version: a schema of trajectory and bone channels with weights, a search throttle, inertial blending; root motion is required [36].

**Procedural approaches**
- Rosen (Overgrowth): 13 keyed poses in all; a "stride wheel / surveyor wheel" drives the cycle phase by distance travelled; pass and reach poses; spring-damper interpolation between additive poses; bounce from gravity; acceleration tilt [44][45][46].

**PFNN (Holden 2017)**
- Phase is 0 at right foot contact, π at left contact, 2π at the next right contact.
- The network weights come from a cyclic cubic Catmull-Rom spline over 4 control points.
- Inputs: 12 trajectory samples covering 1 s back and 0.9 s ahead, terrain heights, gait labels.
- Trained on about 1 hour of 60 fps mocap (≈1.5 GB); runs in 1.8 ms with 10 MB [42][43].

## 6. Rig features that help

- **Reverse foot:** pivots at the ankle, heel, ball and toe; one Roll attribute plus separate heel, ball and toe offsets and a bank [S].
  - Cave's rig carries Roll and Toe Wiggle attributes [1].
  - 3ds Max CAT: the pitch pivot moves from the toe at lift-off to the heel at the plant, and the roll starts before lift-off and ends after the plant [28].
- **Separate root and hip controls:** root_ctrl translates, hip_ik_ctrl rotates [1].
- **IK legs, FK arms, with an IK/FK switch** [1][3][5]. Pole vectors keyed or following the foot [5].
- [U] Space switching and auto-hips: no source found.

## Not found or blocked

- No web searches were left for Kenny Roy, Jason Ryan, "Sergio", Bobby Anguelov, Zadziuk's talk itself, or gimbal and space-switching sources: the 200-search budget for the turn ran out.
- Pages that refused the fetcher: Animation Mentor, Polycount, CG Cookie, Autodesk forums, the UW course pages (login), GDC Vault (maintenance), Epic's Lyra tech blog.

## URLs

1 https://caveacademy.com/wiki/post-production-shots/animation/animation-training/introduction-to-animation-course/animating-a-walk-cycle/ · 2 https://flylib.com/books/en/3.450.1.131/1/ · 3 https://rustyanimator.com/animation-walk-cycle/ · 4 https://rustyanimator.com/run-cycle/ · 5 http://walkingmoom.blogspot.com/2011/11/introduction-to-walkcycles-using-basic.html · 6 https://iwanttobeananimator.wordpress.com/2017/01/29/tutorial-2/ · 7 https://anim.works/walk-cycle/ · 8 https://blog.animschool.edu/?p=588 · 9 https://animation.monmouth.edu/instruct/wp-json/wp/v2/posts/351 · 10 https://education.siggraph.org/static/HyperGraph/animation/character_animation/walking/walking_excercise.htm · 11 https://abigailgelston.wordpress.com/2015/12/16/digital-tutors-creating-walk-cycles-in-maya/ · 12 http://brendanbody.blogspot.com/2008/12/walk-cycle.html · 13 https://pushingposes.blogspot.com/2008/03/basic-walk-cycle-part-2.html · 15 https://blogs.ulster.ac.uk/scottmoore/2024/10/21/animation-strategies-animation-walk-and-runs-regular-run-cycle/ · 16 https://blogs.ulster.ac.uk/scottmoore/?p=1719 · 17 https://xhong.myblog.arts.ac.uk/2020/11/15/week-3-whole-body-walk-cycle-and-constraints/ · 18 https://ecopeland.myblog.arts.ac.uk/2020/11/24/knight-stylized-walk-corrections/ · 19 https://annamckeeart.com/blog/animation-workshop-walk-and-run-cycles-blog · 21 https://irendering.net/advanced-tips-for-walk-cycles-in-blender/ · 22 https://blenderartists.org/t/walk-cycle-along-path-without-feet-sliding/682128 · 23 https://clinicalgate.com/kinesiology-of-walking/ · 24 https://ouhsc.edu/bserdac/dthompso/web/gait/knmatics/gait.htm · 25 https://pmc.ncbi.nlm.nih.gov/articles/PMC12326370/ · 26 https://www8.garmin.com/manuals-apac/webhelp/instincte/EN-SG/GUID-C5C1229F-0C90-455E-94D3-227E00F7AC8F-401.html · 27 https://ojs.ub.uni-konstanz.de/cpa/article/view/1308/1229 · 28 https://help.autodesk.com/cloudhelp/2017/ENU/3DSMax/files/GUID-0E2F0A54-EE66-41FD-AB00-702FC8DDB449.htm · 29 https://dev.epicgames.com/documentation/en-us/unreal-engine/distance-matching-in-unreal-engine · 30 https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/AnimDistanceMatchingLibrary?application_version=5.3 · 31 https://dev.epicgames.com/documentation/unreal-engine/pose-warping-in-unreal-engine · 32 https://dev.epicgames.com/documentation/en-us/unreal-engine/animation-sync-groups-in-unreal-engine · 33 https://dev.epicgames.com/documentation/en-us/unreal-engine/root-motion-in-unreal-engine · 35 https://dev.epicgames.com/documentation/en-us/unreal-engine/animation-in-lyra-sample-game-in-unreal-engine · 36 https://dev.epicgames.com/documentation/en-us/unreal-engine/motion-matching-in-unreal-engine · 37 https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/AnimNode_FootPlacement?application_version=5.3 · 38 https://www.unrealengine.com/en-US/tech-blog/adapting-lyra-animation-to-your-ue5-game · 39 https://www.gameanim.com/?p=13538 · 40 https://www.gamedeveloper.com/programming/most-inspiring-game-animation-tech-talks-of-2016 · 41 https://theorangeduck.com/page/code-vs-data-driven-displacement · 42 https://theorangeduck.com/media/uploads/other_stuff/phasefunction.pdf · 43 https://www.theorangeduck.com/page/phase-functioned-neural-networks-character-control · 44 https://techarthub.com/first-do-no-harm-to-the-gameplay/ · 45 https://discussions.unity.com/threads/surveyor-wheel-technique.251435/ · 46 https://people.engr.tamu.edu/sueda/courses/CSCE450/2022F/projects/Peter_Castelein/index.html · 47 https://docs.unity3d.com/Manual/RootMotion.html · 48 https://mocaponline.com/blogs/mocap-news/run-cycle-animation