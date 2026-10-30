# G. Starts, stops and turns: the biomechanics of non-steady locomotion

Every fact is followed by the page it was read on. "(snippet)" = seen only in a search summary.
PMC/PubMed refused automated access, so several links are Europe PMC REST records of the same
papers (abstracts or full text).

Short names for the record links used repeatedly:
- [HS] Hase & Stein records: https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=AUTH%3A%22Hase%20K%22%20AND%20AUTH%3A%22Stein%20RB%22&resultType=core&format=json&pageSize=10
- [GT] gait-termination abstracts (Crenna 2001, Bishop, Tirosh, Ridge): https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=(TITLE%3A%22termination%20of%20gait%22%20OR%20TITLE%3A%22gait%20termination%22%20OR%20TITLE%3A%22stopping%22)%20AND%20(AUTH%3A%22Jaeger%22%20OR%20AUTH%3A%22Bishop%20M%22%20OR%20AUTH%3A%22Crenna%22%20OR%20AUTH%3A%22Tirosh%22%20OR%20AUTH%3A%22Hase%20K%22%20OR%20AUTH%3A%22Wearing%22%20OR%20AUTH%3A%22Ridge%22)&resultType=core&format=json&pageSize=20
- [TU] turning abstracts (Taylor 2005, Akram 2010, Strike 2009, Glaister 2008): https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=(AUTH%3A%22Akram%20SB%22%20AND%20TITLE%3Aturn*)%20OR%20(AUTH%3A%22Glaister%20BC%22)%20OR%20(AUTH%3A%22Strike%20SC%22%20AND%20TITLE%3Aturn*)%20OR%20(AUTH%3A%22Taylor%20MJ%22%20AND%20TITLE%3A%22turning%20strategies%22)&resultType=core&format=json&pageSize=12
- [PARK] Park et al. 2008, ISBS: https://ojs.ub.uni-konstanz.de/cpa/article/view/1909/1778
- [DIXON] Dixon et al., turning in children: https://ora.ox.ac.uk/objects/uuid:30a0ca80-1521-49ce-9958-7b1bab80cf94/files/m0b5706c36506e35ff8001dff03655763
- [HARPER] Harper 2022 deceleration review: https://www.ebi.ac.uk/europepmc/webservices/rest/PMC9474351/fullTextXML
- [DOS] Dos'Santos 2018 angle-velocity review: https://www.ebi.ac.uk/europepmc/webservices/rest/PMC6132493/fullTextXML

---

## 1. Gait initiation

**The anticipatory phase (APA)**
- The first event is a backward CoP shift: soleus inhibition, then tibialis anterior about 100 ms later.
  Imbalance phase (first CoP shift → heel-off): **~500 ms at natural speed, ~300 ms at maximal**.
  https://www.frontiersin.org/journals/human-neuroscience/articles/10.3389/fnhum.2021.709780/full
- First backward CoP peak **46.6 ± 4.9 mm**, reached **449 ± 26 ms** after CoP onset. Muscles fire before the
  CoP moves (ms): biceps femoris −173/−167, erector spinae −158/−139, soleus −123/−147, tibialis anterior
  ≈ −79. https://www.frontiersin.org/journals/physiology/articles/10.3389/fphys.2024.1520578/full
- Feet 30 cm apart: APA **765 ± 50 ms**, swing **629 ± 60 ms**, CoM forward velocity at first contact
  **0.80 m/s**. https://www.frontiersin.org/articles/10.3389/fnhum.2016.00445/full
- **Path of the CoP** [PARK]:
  - backward and toward the leading (swing) limb, slowly;
  - when the legs' forces equalise, quickly toward the stance limb, and the leading heel lifts;
  - back and lateral, fast, to toe-off.
  - Lateral excursion ~3 cm, read off the figure.

**The first steps** (20 men) [PARK]

| | step length (m) | speed (m/s) |
|---|---|---|
| initiation step, leading / trailing limb | 0.60 / 0.64 | 0.44 / 0.63 (from movement onset) |
| 1st full cycle, leading / trailing | 0.69 / 0.69 | 1.18 / 1.28 |
| steady walking | 0.70 | 1.37 |

- Parameters "gradually increased until the second step". Jian et al. 1993 (cited there): ~90 % of steady
  velocity during step 1, 100 % by step 2.
- **The leading leg is lifted, not pushed off**: no ankle plantarflexion before toe-off (dorsiflexed 12.7°),
  and no stance knee flexion. The trailing leg reaches 19.8° dorsiflexion at heel-off.
- Leading limb: no significant preference in that study. I found no population data on which leg starts.

**Sprint start** (world-class 60 m final, 8 men) https://eprints.glos.ac.uk/9874/1/9874-Bissas-(2021)-Kinematic-factors-associated-with-start.pdf
- Block time 0.34 s, exit velocity 4.28 m/s.
- First contact **0.175 s**, +1.57 m/s (to 5.85 m/s).
- Foot lands **0.12 m behind the CoM**, leaves 0.87 m behind it. Flight 0.43 m.
- Trunk **39° (touchdown) / 43° (take-off) above horizontal** ≈ 47-51° forward of vertical. It rises over the
  acceleration.
- Breakpoints near steps 4 and 14 (snippet, Nagahara 2014).

**Takeaways - starts**
1. **Spend ~0.5 s (urgent: ~0.3 s) before any foot moves**: back and hamstring tension, the body tipping
   forward from the ankles, the pelvis shifting over the stance foot. Lift the stepping heel only then.
2. **First step ~85 % of steady length, second ~98 %**; speed ~90 % in step 1, full by step 2. Cycle from
   step 2-3.
3. **The first leg peels off**: no knee bend, no toe flick. The push comes from the stance leg, its ankle
   dorsiflexing ~20°.
4. **Sprint start**: contact ~0.17 s, foot ~10-12 cm behind the pelvis's ground point, trunk ~45-50° forward,
   rising step by step.

---

## 2. Gait termination

**Mechanisms**
- Three mechanisms [HS]: the swing leg lands extended as a brake, the stance leg's push-off is inhibited, and
  the body rises onto the toes if needed.
  - Subjects stopped with one foot ahead of the other, sometimes after one extra short step.
  - EMG changed in legs and trunk within **150-200 ms**.
- Braking up, push-off down, and a brief window in the cycle decides whether an extra step comes (Jaeger
  1992). https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=(AUTH%3A%22Jaeger%20RJ%22%20AND%20TITLE%3Atermination)%20OR%20(AUTH%3A%22Tirosh%20O%22%20AND%20TITLE%3A%22stimulus%20probability%22)%20OR%20(TITLE%3A%22Trajectory%20of%20the%20body%20COG%20and%20COP%22)&resultType=core&format=json&pageSize=5
- Unplanned stop [GT]:
  - stance-limb braking EMG ~**150 ms** after the signal, swing-limb ~**330 ms**;
  - faster walking shifts braking to the swing limb (Crenna 2001).
- Peak braking force is greatest under the **lead limb** in unplanned stops and rises with cadence (Bishop
  2002/2004). Planned vs unplanned keep the same muscle timing, but the amplitude is ~800 % higher when
  unexpected (Bishop 2006) [GT].
- **Steps and time** [GT]:
  - young adults at 1.29 m/s stopped in **463 ms** (old: 574 ms); the interval's definition is not in the
    abstract (Tirosh 2004);
  - two-step stops were **20 %** of young men's trials, 46 % of older men's (Tirosh 2005).
- Unplanned stop at ~1.25 m/s: gait-termination time **1.05-1.12 s**, step length ~55 cm.
  https://www.ebi.ac.uk/europepmc/webservices/rest/PMC9953996/fullTextXML
- Unplanned stops (youth): more knee flexion and hip-extension moment, an earlier plantarflexion peak;
  ~+16° knee flexion when fast (Ridge 2013/2016) [GT].

**Decelerating from a run** [HARPER]
- From 7.35 m/s: **6.86 m in 1.50 s**.
  - Mean −4.44 m/s² (early −3.88, late −5.99), peak −8.48 m/s².
  - The largest braking forces come LATE.
- Braking steps reach up to 2.7× acceleration-step forces, 40-60 N/kg within <50 ms of contact.
- Foot **0.39-0.44 m ahead of the CoM** at contact (matches the capture point).
- Penultimate vs final contact: 194 vs 252 ms.
- In the braking steps: the CoM is held back and low; penultimate hip flexion 81-100°, knee 106-119°;
  trunk deceleration 4-7 g.

**Takeaways - stops**
1. **Walking stop = one braking step plus a closing half step**.
   - The swing leg lands straight ahead as a brake.
   - The stance leg gives no toe push.
   - The feet end staggered. A toe-rise only for an abrupt stop.
2. **Reaction lag 150-200 ms (~5 frames at 30 fps)**; the stance leg brakes first.
   - From 1.3 m/s young adults stop in ~0.5 s, one step in ~80 % of trials.
   - Give careful or old characters two steps.
3. **An unplanned stop has a deeper knee and a sharper, earlier braking peak**. A planned stop shortens the
   steps through the approach.
4. **Running stop**: pelvis low and behind the feet, each braking foot ~40 cm ahead of it. Budget ~1.5 s /
   7 m from 7 m/s; the last contacts are the hardest and longest (~0.25 s).

---

## 3. Turning

**Strategies** https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=AUTH%3A%22Hase%20K%22%20AND%20AUTH%3A%22Stein%20RB%22%20AND%20TITLE%3Aturning&resultType=core&format=json&pageSize=3
- **Spin turn**: right foot in front, turn **right** by pivoting about that foot.
- **Step turn**: right foot in front, turn **left**: weight onto the right leg, the left hip rotates outward,
  the left foot steps into the new direction.
  - Wider base, "easy and stable".
  - Foot placement and trunk rotation change within one step of the cue, without resetting the rhythm.
- Spin turns need more transverse range of motion and muscle demand; step turns have lower moments (Taylor
  2005) [TU].
- **Prevalence**:
  - older adults prefer spin turns except fast 90° turns, where they use step turns (Akram 2010) [TU];
  - children: 43 % only spin, 56 % both, 1 of 54 only step [DIXON], which notes the adult preference is
    unclear.
- Turning steps are 8 % (office → car park) to **35-50 %** (store, office, cafeteria) of daily-life steps.
  https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=TITLE%3A%22video%20task%20analysis%20of%20turning%22&resultType=core&format=json&pageSize=3

**Reorientation sequence**
- 90° turn, young adults: eyes **407 ± 116 ms** before the first turning foot contact, head **50 ± 53 ms**
  before. Gaze up to 1000 ms ahead (Grasso 1998, cited).
  https://www.frontiersin.org/journals/sports-and-active-living/articles/10.3389/fspor.2020.00022/full
- Head → shoulders and pelvis → feet, at all speeds and turn sizes, even with eyes closed (Akram 2010, older
  adults) [TU].
- The head starts ~**1.1 m before the turn point** (turns ≤135°) and stays further into the turn than the
  trunk, more for sharper turns. Speed falls monotonically with turn angle (snippet, Sreenivasa 2008).

**Speed and steps in a 90° turn**
- Adults: "90°" turns came out ~80°. Speed and stride length were lower on the approach and departure
  strides (Strike & Taylor 2009) [TU].
- Children's spin turns [DIXON] (read off bars, ±0.03):

  | | stride velocity (m/s) | stride width (leg lengths) |
  |---|---|---|
  | straight | 1.33 | 0.11 |
  | approach | 1.17 | 0.20 |
  | turn | 1.05 | 0.15 |
  | depart | 1.00 | 0.28 |

  Stride length falls 1.6 → 1.35 leg lengths.
- Glaister 2008 [TU]: the initiation step brakes more, the apex step has a large lateral impulse and more
  propulsion, the termination step brakes less.

**Running: curves and cuts**
- **Lean**: tan θ = v²/(g·r):
  - 1.3 m/s, r 1 m: ≈10°;
  - 3 m/s, r 3 m: ≈17°;
  - 5 m/s, r 5 m: ≈27°;
  - 9.4 m/s, r 37.7 m: ≈13°.
- Bend of r 37.7 m: sprint speed −4.7 % (9.9 → 9.4 m/s). The inside step loses frequency (−0.11 Hz), the
  outside step length (−0.10 m); lateral lean increases at touchdown (Churchill 2015, Judson 2020).
  https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=(TITLE%3Acurve%20OR%20TITLE%3Abend%20OR%20TITLE%3Acurved%20OR%20TITLE%3Acircular)%20AND%20(TITLE%3Asprint*%20OR%20TITLE%3Arunning)%20AND%20(lean%20OR%20inclination%20OR%20tilt)&resultType=core&format=json&pageSize=12&sort=CITED%20desc
- **Sidestep** (plant foot opposite the new direction) **vs crossover** (plant foot toward it, the other leg
  crosses) [DOS]:
  - "90° as fast as possible" achieved **40.5° vs 33.0°** at 3.82 vs 3.67 m/s;
  - on a 45° task the CoM turned 34.9° / 29.4° / 23.8° / 17.5° at 2 / 3 / 4 / 5 m/s;
  - mean speed for 45 / 90 / 135 / 180° cuts: 4.7 / 3.8 / 3.5 / 3.4 m/s (men);
  - plant contact ~0.16-0.24 s (45°), ~0.25 s (90°), ~0.44-0.52 s (180°);
  - pelvis rotated toward the new direction **48.7° (90°) vs 14.2° (45°)**;
  - the penultimate step brakes for cuts ≥60°; pre-planned cuts begin one step before the plant.
- Braking steps from a 20 m approach: 2.9 / 5.4 / 6.4 / 6.3 for 45 / 90 / 135 / 180° (4 m approach:
  0.4 / 2.7 / 3.3 / 3.3) [HARPER].

**Takeaways - turns**
1. **Eyes ~0.4 s (12 frames at 30 fps) before the first turning footfall, head ~0.05 s**, then shoulders and
   pelvis, then feet.
   - The head starts ~1.1 m before the corner and leads the chest throughout.
2. **The foot in front picks the strategy**:
   - Turning away from it is a **step turn** (wide, safe): use it for careful or fast-90° characters.
   - Turning toward it is a **spin turn**: pivot on that foot's ball, feet close, more twist. Use it for
     casual or nimble characters.
3. **90° walk turn over ~3 steps**: −10-15 % speed on the approach, −20-25 % on the turn and departure.
   Double the step width on approach and departure.
4. **Running curve**: tilt the whole body by atan(v²/gr); the inside leg shortens its timing, the outside
   its length.
5. **Cut**: a sidestep turns sharper than a crossover; a faster approach gives a shallower real cut.
   - Rotate the pelvis ~50° toward the new direction during a 90° plant.
   - Hold the plant 0.25 s (90°) to 0.5 s (180°), after 3-6 braking steps.

---

## Gaps
- **Lateral CoP size in initiation**: read off a figure only. **Starting-leg preference**: not found.
- **Walking stops**: no last-step length, arm or trunk data found.
- **Opened only via abstracts or citations**:
  - Crenna & Frigo 1991, Jian 1993, Halliday 1998, Taylor 2005;
  - not opened: Patla 1999, Hollands 2002, Nagahara's per-step sprint tables.
- **Running lean**: no measured human lean-vs-radius table; the formula stands in.
- **Turn speed and width numbers are children's**; the adult data give direction only.
