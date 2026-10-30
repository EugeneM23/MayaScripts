# F. Emotion in gait, and injured / pathological gaits

Research notes for the walk/run guide. Every fact is followed by the page it was read on.
"(snippet)" means the number was seen only in a search-engine summary, not on a page I opened.
PMC, PubMed, JoV, ScienceDirect and Physiopedia refused automated access, so several facts come from
Europe PMC REST records (abstracts or full text) of the same papers.

---

## 1. Emotion in gait

### 1.1 Two kinds of data, two sizes of effect

- **Felt (induced) emotion changes gait only a little.** Recalled memories, 14 young adults, shank
  IMUs (Alvarez et al. 2025, *Sensors* 25:6222):
  https://www.ebi.ac.uk/europepmc/webservices/rest/PMC12526802/fullTextXML

| | Neutral | Angry | Joy | Fear | Sad |
|---|---|---|---|---|---|
| Stride velocity, m/s | 1.14 | 1.24 (+9 %) | 1.25 (+10 %) | 1.22 (+7 %) | 1.12 (−2 %) |
| Stride length, m | 1.29 | 1.37 (+6 %) | 1.35 (+5 %) | 1.35 (+5 %) | 1.30 (0 %) |
| Cadence, steps/min | 105.8 | 108.7 | 110.3 | 108.4 | 103.1 (−3 %) |
| Stance, % cycle (L) | 59.9 | 59.7 | 59.7 | 60.0 | 60.5 |

  Stride time: sad 1.20 s against joy 1.10 s. Stance %, swing % and double support did not differ.
  Percentages are mine, from the table.
- The same paper's introduction summarises 3D motion-capture work: anger and joy **about 20 % faster**
  than neutral, sadness **about 10 % slower**, with larger sagittal ranges (mostly in the arms) for
  anger and joy. Same URL.
- VR-induced emotions, 23 analysed (Homagain & Ehgoetz Martens 2023, PLOS ONE): only sadness changed
  gait, with shorter steps and speed about **0.08 m/s lower** (sad 1.13 against excitement 1.28 m/s).
  The paper cites depression at about **0.23 m/s** slower than healthy controls (Lemke et al.).
  https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0284308
- Induced emotions, standing and walking: **7 of 229** parameters differed.
  https://www.ebi.ac.uk/europepmc/webservices/rest/PMC10499259/fullTextXML
- **Acted emotion** is bigger: anger **1.82 ± 0.22 m/s** against fear **0.83 ± 0.31 m/s** (snippet,
  attributed to Roether 2009; JoV refused with 403).

### 1.2 What each emotion looks like

Roether et al. 2009 (JoV 9(6):15): 25 walkers, mocap; the features found by sparse regression depend on
a few joints and match what observers use (abstract:
https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=%22Critical%20features%20for%20the%20perception%20of%20emotion%20from%20gait%22&format=json&resultType=core).
The features below are from the review by Xu et al., which summarises Roether, Montepare 1987, Gross
2012, Halovic & Kroos 2018 and Michalak 2009: https://arxiv.org/html/2003.11461v4

- **Sad**
  - Roether: reduced head angle (read as head down; the sign depends on the paper's angle convention),
    reduced joint amplitudes.
  - Montepare: less arm swing; recognised 94 %.
  - Halovic & Kroos: slow, short strides, the slowest pace; the WHOLE arm moves, but little.
  - Gross: indirect, light, slow; torso and limbs contracted.
  - Kang & Gross: less smooth than joy.
- **Angry**
  - Montepare: heavy-footed; recognised 90 %.
  - Roether: larger elbow angles (bent arms), larger joint amplitudes.
  - Halovic & Kroos: long strides, more arm movement, faster cadence than happy.
  - Gross: expanded limbs; direct, forceful, fast, tense.
- **Happy / joy**
  - Montepare: fastest pace; recognised 74 %.
  - Halovic & Kroos: long strides, more arm movement.
  - Gross: torso more expanded than anger, flow more relaxed.
  - Kang & Gross: smoothest.
- **Fear**
  - Halovic & Kroos: fast, short "scurrying" strides; less arm movement, mostly in the forearms.
  - Roether: larger elbow angles, smaller joint amplitudes.
  - Shoulders hunched (snippet).
- **Pride** (Montepare): longer strides; recognised 56 %.

Gross, Crane & Fredrickson 2012 (*Hum Mov Sci* 31:202): speed explains the larger hip, shoulder,
elbow, pelvis and trunk amplitudes of anger and joy, but two postures are **independent of speed**:
sadness's neck and thoracic flexion, and joy's trunk extension with the shoulders down.
https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:21835480&format=json&resultType=core

**Cues observers report** (Halovic & Kroos 2018): happy bouncy with more arm movement; sad slow and
slouched; angry fast and stomping; fear fast or slow (the kinematics confirmed only fast and short).
https://researchers.westernsydney.edu.au/en/publications/not-all-is-noticed-kinematic-cues-of-emotion-specific-gait/

### 1.3 Depression and sadness (Michalak et al. 2009, *Psychosom Med* 71:580)

14 depressed inpatients against controls; 23 students in a sad or positive mood by music. Sad and
depressed gait: lower speed, less arm swing, less vertical head movement, **more lateral sway** of the
upper body, a slumped forward-leaning posture. A 2021 follow-up found the same in everyday life.
No numbers: the abstract was seen in search only, and the PDF (biomotionlab.ca) would not parse.

### 1.4 Tired

Systematic review of 11 lab muscle-fatigue studies:
- most found **wider steps** (read as a medio-lateral stability strategy);
- speed and stride results were mixed;
- several found more knee flexion and plantarflexion at heel contact.

https://www.ebi.ac.uk/europepmc/webservices/rest/PMC11939146/fullTextXML

### 1.5 Animator takeaways (emotion)

1. **Felt emotion is subtle; acted emotion reads.** Felt: sad −2–7 % speed, angry/joy +7–10 %.
   Expressed: about −10 % / +20 %. Start from the expressed numbers and let POSTURE carry the emotion:
   by speed alone sad is confused with fear and angry with happy.
2. **Sad / depressed:** speed −10 % or more, shorter strides; neck and upper back flexed, head down
   (holds even at normal speed); arm swing cut (to about half is my choice, no source gives a %), the
   whole arm still moving; smaller vertical bob, MORE side sway. No head angle in degrees found: by eye.
3. **Angry against happy** (both +10–20 % speed, longer strides, bigger arms): angry has a higher
   cadence, heavy heel strikes, bent elbows, a direct path, tension; happy bounces, chest open, shoulders
   down, loose smooth arcs.
4. **Fear:** short quick steps, elbows bent and in, small forearm-only arm motion, shoulders up.
5. **Tired:** wider steps, softer knee at contact. **Proud:** longer stride (nothing else found).

---

## 2. Pathological and injured gaits

**Reference values**:
- normal stance is about 60 % of the cycle, swing about 40 %
  (https://orthopaedicprinciples.com/painful-and-antalgic-gait/);
- the pelvis drops about **4°** on the swing side, rotates about 4°, and the knee flexes about 15° after
  heel strike (https://www.orthobullets.com/foot-and-ankle/7001/gait-cycle).

### 2.1 Antalgic gait (painful leg)

- **Cause:** pain in the hip, knee, foot or spine. **Looks like:** the painful leg is unloaded quickly
  (shorter stance, early lift, longer swing), the sound leg's step is shorter, and with a painful hip
  the trunk leans OVER the painful side to cut the joint force.
  https://orthopaedicprinciples.com/painful-and-antalgic-gait/
- **Measured, knee OA before knee replacement** (34 patients, Fukui 2024):

| | Affected leg | Sound leg |
|---|---|---|
| Stance | 0.69 s | 0.73 s |
| Swing | 0.41 s | 0.36 s |
| Double support | 0.16 s | 0.17 s |

  My arithmetic: stance is about 63 % of the affected leg's cycle against 67 % of the sound leg's. Speed
  0.87 m/s, cadence 113. After surgery both legs were 0.62 s and speed 1.08 m/s.
  https://www.ebi.ac.uk/europepmc/webservices/rest/PMC11348746/fullTextXML
- **Pain relief lengthens the painful leg's stance**: knee OA, genicular nerve block, 51 patients.
  Stance on the affected knee went from 57.8 % to 59.9 % of the cycle, and cadence from 94 to 109.
  https://www.ebi.ac.uk/europepmc/webservices/rest/PMC13051153/fullTextXML
- **After an ankle fracture** (4 months, 10 patients against 10 controls):

| | Patients | Controls |
|---|---|---|
| Speed | 0.74 m/s | 1.28 m/s |
| Step | 40.5 cm | 53.8 cm |
| Cadence | 119 | 140 |
| Vertical trunk-motion symmetry | 0.51 | 0.71 |

  https://www.ebi.ac.uk/europepmc/webservices/rest/PMC6425625/fullTextXML
- No source I opened gives a typical stance asymmetry for an acute, sharp limp.

### 2.2 Trendelenburg and Duchenne (hip abductor weakness)

- **Cause:** weak or painful hip abductors (gluteus medius / minimus).
- **Uncompensated (Trendelenburg):** in single stance on the weak leg the pelvis drops on the SWING side,
  the trunk leans toward the stance leg relative to the pelvis, the hip adducts.
- **Compensated (Duchenne):** the trunk leans over the weak stance leg; the pelvis stays level or rises
  on the swing side. Both seen in children with Perthes disease (snippet, Westhoff group); the trunk
  lean to the affected side also at https://orthopaedicprinciples.com/painful-and-antalgic-gait/
- **Thresholds:** a positive drop is over 2° (Asayama), or over 4° in single stance and over 8° at
  maximum (Westhoff 2005) (snippet, via a review). Normal is about 4°.
- **Hip OA with a Duchenne limp** (Reininga 2012, body-fixed sensors), at preferred speed:

| | Healthy | No limp | Duchenne limp |
|---|---|---|---|
| Frontal thoracic range | 4.9° | 5.3° | **9.1°** (almost double) |
| Frontal pelvic range | 8.2° | 5.4° | 5.9° (less) |
| Speed | 1.6 m/s | 1.2 m/s | 1.1 m/s |

  The trunk swings and the pelvis is held.
  https://www.ebi.ac.uk/europepmc/webservices/rest/PMC3274426/fullTextXML
- **The sign needs real weakness.** A gluteal nerve block cut abductor strength by 52 % in 9 men, and
  pelvic drop did not change consistently: only 1 of 9 showed the compensations.
  https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:22797529&format=json&resultType=core

### 2.3 Stiff-knee gait

- **Cause:** stroke, CP or MS. The classic explanation is an overactive rectus femoris in pre-swing and
  early swing; low knee speed at toe-off is another (snippet).
- **Looks like:** reduced or delayed knee flexion in swing, with the foot cleared by **hip hiking** and
  circumduction.
- **Criteria:**
  - peak swing knee flexion **< 40°** (Bacca 2025:
    https://www.ebi.ac.uk/europepmc/webservices/rest/PMC12400543/fullTextXML);
  - or **< 44.3°**, or a between-leg difference **> 17°** (Lee 2024:
    https://www.ebi.ac.uk/europepmc/webservices/rest/PMC12096336/fullTextXML);
  - the literature is converging on **< 45°** (Lee 2025, below).
  - The normal peak of about 60° is commonly cited; I did not verify it on a page I opened.
- **The most impaired stroke cluster** (Lee 2025), against controls:
  - 29.3° less peak swing knee flexion;
  - **8.8° more pelvic obliquity** on the paretic side (hip hike), the hike starting in pre-swing;
  - 8.8° more hip abduction on the other leg.

  https://www.ebi.ac.uk/europepmc/webservices/rest/PMC11863409/fullTextXML

### 2.4 Drop foot / steppage gait

- **Cause:** weak dorsiflexors (peroneal nerve palsy, neuropathy, leprosy).
- **Looks like:** the foot hangs pointed down in swing, so the leg is lifted high to clear it.
  https://www.ebi.ac.uk/europepmc/webservices/rest/PMC13418903/fullTextXML
  The foot slap at contact is from search summaries only (snippet).
- **Ankle angle** (plantarflexion negative; leprosy foot drop, Cohen 2023):

| | Affected | Controls |
|---|---|---|
| Initial contact | −16.8° | −5.4° |
| Swing | −12.4° | −1.4° |
| Terminal stance | −29.1° | −18.8° |

  https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=gait%20analysis%20leprosy%20foot%20drop%20principal%20component%20analysis&format=json&resultType=core&pageSize=3
- No source I opened gives the hip and knee excess in degrees.

### 2.5 Crouch gait

- **Cause:** cerebral palsy (spasticity, weak extensors, contractures).
- **Looks like:** too much knee flexion and ankle dorsiflexion through stance, often too much hip flexion.
- **Children** (Mullerpatan 2025), minimum stance knee flexion:

| | Typical | Mild crouch | Severe crouch |
|---|---|---|---|
| Knee flexion, mean | 4.6° | 20.3° | 40.9° (up to 86.6°) |
| Speed | 1.19 m/s | 0.79 m/s | 0.58 m/s |
| Cadence | 130 | 112 | 89 |
| 2-minute walk | 150 m | 90 m | 59 m |

  https://www.ebi.ac.uk/europepmc/webservices/rest/PMC12211203/fullTextXML
- **Common bands:** mild 15–30°, moderate 30–50°, severe ≥ 50° (snippet, Gillette / Steele). No single
  definition exists.

### 2.6 Cane and crutches

- **A cane in the hand OPPOSITE the bad hip** (11 total hip replacement patients): the operated hip's
  abductor moment fell 26 % and the other hip's rose 28 %.
  https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:15605334&format=json&resultType=core
- **3-point crutch gait**, 20 people aged 40–80: axillary crutches 0.50 m/s, forearm crutches 0.44 m/s.
  https://morthoj.org/2021/v15n2/axillary-forearm-crutches-abstract.php
- 3-point crutch walking about doubles oxygen uptake (snippet; Fisher & Patterson).

### 2.7 Animator takeaways (pathology)

1. **Antalgic:** a chronic limp is only about 4 points of stance asymmetry (63 against 67 %); for a
   READABLE acute limp push it well past that. Short, flat contact on the painful foot, an early lift,
   the sound leg rushed through with a SHORT step, speed toward 0.7–0.9 m/s; for a hip, the trunk leans
   over the painful leg in its stance.
2. **Trendelenburg / Duchenne:** in the weak leg's stance drop the opposite hip past the normal 4°
   (8°+ reads); or, compensated, keep the pelvis level and throw the shoulders over the weak leg: about
   twice the normal side-to-side trunk motion (9° against 5°).
3. **Stiff knee:** cap the swing knee at about 30–40° (normal about 60°, unverified) and delay its peak;
   hike the pelvis about 8–9° on that side and swing the leg out.
4. **Drop foot:** the swinging foot hangs about 12° plantarflexed, lands about 17° plantarflexed (toe or
   flat first, then a slap), and the hip and knee lift extra in swing to clear the toe.
5. **Crouch:** knees bent 20–40° even at mid-stance, ankles dorsiflexed, short slow steps (0.6–0.8 m/s).

---

## 3. What I could not find

- Roether 2009's degrees and velocities (JoV and the Tübingen thesis PDF unreadable); Gross 2012's and
  Michalak 2009's tables (paywall, unparsable PDF).
- Any head or trunk flexion in degrees for sadness; arm-swing amplitude, step width or vertical bounce
  in numbers per emotion.
- The stance asymmetry of an acute antalgic limp; Trendelenburg trunk lean in degrees; the hip and knee
  excess in steppage; cane and crutch timing in the cycle.
