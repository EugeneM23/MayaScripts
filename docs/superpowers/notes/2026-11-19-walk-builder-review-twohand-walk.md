# Walk Builder: what the animator saw in the TwoHand walk batches (2026-11-19)

The animator goes through the review scenes (`C:/!!!Work/Animations/Animations/LongSword/Locomotion/Automation/
MM2_TwoHand_Walk_NN_Review.mb`, preset `2H_Sword_02`, pose `LongSword_Idle_3P`, In place, a Long Sword in the right
hand) and says what Walk Builder must not allow. Recorded as said; nothing is fixed until they say «делай правки».

## Batch 01 (Transition Run_to_Walk, Walk_Box)

1. **Walk Builder must not break the animation's timing - this is important, everything must match.**
   («нужно убедиться в том что walk builder не нарушает таймингов анимаций это важно все должно совпадать»)
   To check when fixing: per clip, the processed take against the source - the same frame count and range, every
   contact (foot down / up) on the same frame, the same steps on the same frames, starts and stops at the same
   frames; measure, do not assume.

2. **M_TwoHand_Transition_Run_to_Walk_Lfoot** (`Manny_Skeleton_Character` in batch 01): the arms or the arm
   twists are broken - on BOTH the left and the right arm the elbows stick out to the sides. The animator's guess:
   it came from moving the sword in the rig pose (the preset's rig pose edits). Must be fixed.
   («сломаны руки или твисты на руках. как на левой руке так и на правой локти торчат в стороны (скорее всего так
   случилось из-за того что я сдвинул меч в риг позе) нужно исправить»)
   To check when fixing: the elbows' plane and the twist bones against the source take and against the same clip
   with the rig pose edits off - which of the two moves the elbows out.

3. **M_TwoHand_Transition_Run_to_Walk_Rfoot** (`Manny_Skeleton1_Character` in batch 01): the same problems as in
   2 - the elbows stick out on both arms. («все те же проблемы что и в предыдущей анимации»)

4. **M_TwoHand_Walk_Box_B_LR_Lfoot** (`Manny_Skeleton4_Character` in batch 01):
   - the arms break in places («ломаются руки местами»);
   - **frame 99**: the legs spread too far apart, the knees point inward («ноги как-то слишком разъехались, колени
     смотрят внутрь»);
   - **frame 113**: kinks in the knees («какие-то изломы коленей»);
   - **frame 142, the end of the animation**: the legs stand quite wrong («ноги совсем стоят не корректно»).

5. **General - the Box clips (walking one way, then another): Walk Builder must learn to handle a change of
   direction.** «я заметил что у нас вообще много проблем в анимациях типа box когда персонаж шел в одну сторону а
   потом в другую нужно научиться хендлить это.»
   **The legs must not spread beyond the norm**: work out how to compute the delta (how far apart the feet are, or
   how much the knob changed it) and keep to bounds. «ноги не должны разъезжаться сверх нормы нужно как-то понять
   как высчитывать дельту и придерживаться каких-то значений.»
   To check when fixing: the feet's spread (across the body) over the take against the source's own and against a
   person's normal range; where Width / Stance / the pose's feet push it past, and at a turn (the body's
   left-right changing under a walk whose travel changed direction - the model reads one `across` axis a cycle).

6. **M_TwoHand_Walk_Box_B_RL_Rfoot** (`MM2_TwoHand_Walk_01_Review_p1_Manny_Skeleton_Character` in batch 01): the
   elbows wobble a lot - must not be so. («сильно виляют локти так не должно быть»)
   To check when fixing: the elbow's place and plane frame to frame against the source's (the arm springs, Whip,
   Hold / Overlap, the shoulder assist, the rig pose's sword move).

7. **M_TwoHand_Walk_Box_B_RL_Lfoot** (`Manny_Skeleton6_Character` in batch 01): twists in the shoulders.
   («перекруты в плечах»)
   To check when fixing: the clavicle / upper arm roll frame to frame (the shoulder assist turning the clavicle up
   to 13 deg in the pilot, the upper-arm twist bones).

8. **M_TwoHand_Walk_Box_B_LR_Rfoot** (`Manny_Skeleton5_Character` in batch 01): the elbows wobble (as 6).
   («виляют локти»)

9. **M_TwoHand_Walk_Box_F_LL_Lfoot** (`MM2_TwoHand_Walk_01_Review_p1_Manny_Skeleton3_Character` in batch 01): the
   elbows wobble, and **jittering in the RIGHT shoulder** (said «левом», corrected at 10: «в предыдущей правке было
   правое плечо тоже а не левое»). («виляние локтей, джиттеринг в правом плече»)
   To check when fixing: the right clavicle / upper arm frame to frame (high-frequency, not the swing) - the
   shoulder assist's per-frame turn, Overlap, the hold.

10. **M_TwoHand_Walk_Box_F_LL_Rfoot** (`MM2_TwoHand_Walk_01_Review_p1_Manny_Skeleton4_Character` in batch 01):
    jittering in the right shoulder. («джиттеринг в правом плече») The right shoulder again (9 too) - the right
    is the hand holding the sword.

11. **M_TwoHand_Walk_Box_F_LR_Lfoot** (`MM2_TwoHand_Walk_01_Review_p1_Manny_Skeleton5_Character` in batch 01): at
    the change of direction, **around frame 35, an abrupt transition**. If it is the plugin's doing - fix it.
    («при смене направлений в районе 35 кадра какой-то резкий переход. Это делает наш плагин или было в анимации?
    Если наш плагин то нужно исправить»)
    **Measured (2026-11-19, the source FBX against the processed clip, each bone relative to the root, peak
    acceleration in frames 25-45, cm/frame²):** the jolt IS in the source - at frames 34-37, where the root's
    path turns from -Z to +X (pelvis 1.16, head 1.37, hands 2.9-3.1, foot_r 14.1). **Our plugin makes it sharper
    on the body**: pelvis 1.81 (x1.6), spine_03 1.84 (x1.5), head 2.33 (x1.7), forearms 2.82-2.88 (x1.5-2.0); the
    hands come out softer (2.2-2.4, the hold) and the feet about the same. So: fix the amplification at a change
    of direction. The take keeps its length (keys 0-133, the source 0-133).

12. **M_TwoHand_Walk_Box_F_LR_Rfoot** (`MM2_TwoHand_Walk_01_Review_p1_Manny_Skeleton6_Character` in batch 01):
    **very visible pelvis drops** - the animator thinks from a very long step. Must not be done so; the step must
    be handled better. («очень заметные проседания таза вниз я так понимаю из-за очень длинного шага. так делать
    нельзя нужно исправить. мы должны лучше обрабатывать шаг»)
    To check when fixing: the pelvis height over the take against the source's own (the pilot already read «the walk
    sinks 33-37 cm at the contacts» under this pose and preset - Height +40 asked, physics off); where the legs fall
    short of a long stride, what gives - the reach drop, Pelvis height / Stance, the Box's step at the turn.

13. **Every other animation in batch 01 has the same problems** («во всех остальных анимациях такие же
    проблемы»):
    - shoulder jittering (the right one, the sword hand - 9, 10);
    - the elbows wobbling (6, 8, 9);
    - the distance between the feet handled wrongly (4, 5);
    - wrong behaviour at a change of direction (4, 5, 11);
    - the pelvis sinking (12).
    Plus the broken arms / elbows out of the two Transitions (2, 3) and the timing rule (1).

## The list to fix, by kind (from 1-13)

| # | What | Where seen | First suspect |
|---|---|---|---|
| A | Timing must match the source exactly | all | (rule - verify: frame range, contacts, steps per clip) |
| B | Elbows sticking out / arms broken | Transitions (2, 3), Box_B_LR_Lfoot (4) | the rig pose's sword move (the preset's edits) |
| C | Elbows wobbling | 6, 8, 9, all | the arms' springs / Hold / Overlap / Shoulder assist |
| D | Shoulder jitter, the sword hand | 9, 10, all | the Shoulder assist's per-frame clavicle turn |
| E | Feet too far apart, knees inward, kinked knees, feet wrong at the end | 4, 5, all | Stance / the pose's width on one `across` axis a cycle while a Box turns |
| F | A change of direction made sharper | 11, all | the body pieces (pose, hold, springs) at the turn - x1.5-2 on pelvis, head, forearms |
| G | The pelvis sinking on long steps | 12, all | the reach drop (Height +40 asked, physics off); handle the step |

