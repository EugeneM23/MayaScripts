Agent "Running biomechanics numbers research" finished

I ran out of web-search budget partway through. Searching stopped once the budget was spent (it is shared across agents). After that I only opened specific known URLs. Several classic papers are therefore not used (see "Gaps" at the end); you can send a follow-up to continue searching. I wrote no files. The dataset was streamed into memory and analysed in mayapy.

**Backbone source.** Fukuchi, Fukuchi &amp; Duarte 2017, PeerJ, an open running dataset (paper https://pmc.ncbi.nlm.nih.gov/articles/PMC5426356/; data https://api.figshare.com/v2/articles/4543435, CC-BY):
- 28 treadmill runners, 27 men and 1 woman: age 34.8 ± 6.7 y, height 176.0 ± 6.8 cm, mass 69.6 ± 7.7 kg (metadata https://ndownloader.figshare.com/files/7841131); trochanter height 0.93 m.
- Speeds: 2.5, 3.5 and 4.5 m/s.

"Computed here" means I calculated it from the dataset files myself:
- 101-point processed curves, e.g. https://ndownloader.figshare.com/files/7824949.
- About 11 s of raw 150 Hz markers and 300 Hz treadmill force per trial.

My right-side peaks match the paper's Table 4 exactly for hip and knee (knee max 93.52 / 108.68 / 119.12°). My raw-force cadence (161.6 / 171.2 / 183.6 steps/min) matches the paper's 80.8 / 85.7 / 91.7 strides/min.

---

## 1. Gait cycle and phases

**Table 1 – phase timing vs speed**

| Speed | Stride time | Stance per foot (duty factor) | Each flight | Contact | Flight | Source |
|---|---|---|---|---|---|---|
| 2.5 m/s (jog) | 0.745 s | 38.5 % | 11.4 % | 287 ms | 85 ms | computed here (raw force) |
| 3.5 m/s | 0.703 s | 33.8 % | 16.1 % | 237 ms | 113 ms | computed here |
| 4.5 m/s | 0.657 s | 32.6 % | 17.5 % | 214 ms | 115 ms | computed here |
| 3.9 m/s (14 km/h), trained middle-distance runners | — | 32.1 % | — | 237 ms (−8 ms per km/h) | 132 ms (+3 ms per km/h) | Burns 2021, https://www.ebi.ac.uk/europepmc/webservices/rest/PMC8131362/fullTextXML |
| ~10 m/s, 12 sprinters | — | ≈21 % (derived by me) | — | 90 ms (minimum, 20th step) | — | Nagahara 2014, https://www.ebi.ac.uk/europepmc/webservices/rest/PMC4133722/fullTextXML |
| 12.14 m/s, Bolt (fastest 20 m) | 0.459 s | 18.7 % | 31.6 % | 86 ms | 145 ms | Čoh 2018, https://ojs.srce.hr/kinesiology/article/view/5579/4681 |

- **Layout at 3.5 m/s:** R foot strike 0 % → R toe-off ~34 % → flight → L foot strike 50 % → L toe-off ~84 % → flight → 100 %.
- **Toe-off in the processed files:** 40.4 / 35.8 / 33.8 % (their force is low-pass filtered, which stretches stance). Raw-force values are in Table 1.
- **Absorption vs propulsion:** the fore-aft force changes from braking to propulsion at about 50 % of stance at all three speeds (computed here).
  - Bolt: braking 37 % / propulsion 63 % of contact.
  - Elite sprinters: about 43 % braking (Mero 1992, cited by Čoh 2018).
- **One shared instant, ~15–16 % of the cycle (~40–45 % of stance):** the deepest point of the centre of mass (COM), the peak vertical force and the peak stance knee bend all fall here (computed here).
- **Running vs walking:**
  - Running has no double support, two flights per stride, and stance under 50 %.
  - Near the transition speed, the COM moves **down 7.3 cm** in the first half of stance when running and **up 3.1 cm** when walking. Leg compression is 12.3 vs 9.1 cm; leg sweep angle is 19.2 vs 30.4° (Lee &amp; Farley 1998 abstract, https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=TITLE%3A%22determinants%20of%20the%20center%20of%20mass%20trajectory%20in%20human%20walking%20and%20running%22&amp;resultType=core&amp;format=json).

## 2. Temporal and spatial measures

**Table 2**

| Condition | Stride length | Step length | Cadence (steps/min) | Source |
|---|---|---|---|---|
| Walk–run transition, ~2.14 m/s | 1.81 m | 0.91 m | 141 (70.6 strides/min) | Hansen 2017, https://www.ebi.ac.uk/europepmc/webservices/rest/PMC5435734/fullTextXML |
| 2.5 m/s | 1.86 ± 0.11 m | 0.93 m | 161.6 | Fukuchi Table 4 |
| 2.9 m/s (preferred, 45 runners) | — | 1.008 m | 172.6 ± 8.8 | Heiderscheit 2011, https://pmc.ncbi.nlm.nih.gov/articles/PMC3022995/ |
| 3.5 m/s | 2.46 ± 0.15 m | 1.23 m | 171.4 | Fukuchi |
| 4.5 m/s | 2.96 ± 0.20 m | 1.48 m | 183.5 | Fukuchi |
| Elite 100 km race pace | — | — | 182 (range 155–203) | Burns 2019 abstract, https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=TITLE%3A%22step%20frequency%20patterns%20of%20elite%20ultramarathon%20runners%22&amp;resultType=core&amp;format=json |
| Sprint acceleration | — | up to 2.14 m (24th step) | max 292 (4.87 Hz, 8th step) | Nagahara 2014 |
| Bolt, race average 2008–2012 | — | 2.42–2.44 m | 250–258 (4.16–4.30 Hz) | Čoh 2018, Table 2 |
| Bolt, top speed | 5.40 m | 2.70 m (1.38 × height) | 262 (4.36 Hz) | Čoh 2018, Table 3 |

- **Step width** narrows with speed: 0.10 / 0.09 / 0.08 m at the three speeds (Fukuchi Table 4).
- **Length first, then frequency:**
  - From 2.5 to 4.5 m/s (+80 % speed), stride length rose **+59 %** and cadence only **+13.5 %** (Fukuchi).
  - Up to about **7 m/s** stride length grows faster, driven by the ankle plantarflexors. Above 7 m/s the strategy shifts to stride frequency, driven by the hip muscles (Dorn 2012, https://journals.biologists.com/jeb/article/215/11/1944/10883/Muscular-strategy-shift-in-human-running).
  - Both length and frequency rise up to about 90 % of top speed, then mainly frequency (Mero &amp; Komi 1986, cited by Čoh 2018).
  - Top speeds ranged 6.2–11.1 m/s, and swing time did not differ between fast and slow runners. Faster runners apply more force: 1.26 × at 11.1 vs 6.2 m/s (Weyand 2000 abstract, https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=TITLE%3A%22faster%20top%20running%20speeds%20are%20achieved%22&amp;resultType=core&amp;format=json).
  - In sprint acceleration, step frequency plateaus by the 4th step while step length keeps growing to the 24th (Nagahara).
- **The "180" claim:**
  - Souza notes that some suggest about 180 steps/min is ideal, but the evidence comes mainly from running-economy studies, and he says no single value should be recommended to everyone (https://pmc.ncbi.nlm.nih.gov/articles/PMC4714754/).
  - Cadence actually tracks speed (Table 2): 162 steps/min at 2.5 m/s and 184 at 4.5 m/s.
  - In the 100 km race study, step frequency rose with speed and fell with runner height (Burns 2019).
- **Contact and flight times:** see Table 1. World-class sprinters touch down for 70–95 ms (Mann &amp; Sprague; Mero 1992; Taylor &amp; Beneke, all cited by Čoh 2018).

## 3. Joint-angle curves (computed here)

**Table 3 – Fukuchi dataset, mean of 28 runners, right side, Visual3D angles, degrees.**
- 0 % = foot strike.
- Hip + = flexion (thigh relative to pelvis); knee + = flexion; ankle + = dorsiflexion.
- The processed ankle zero is 3.4° more plantarflexed than the paper's Table 4. Add 3.4° to match the paper.
- Between-runner SD: hip about 5–7°, knee about 4–12° (largest in swing), ankle about 2–10°.

| % cycle | Hip 2.5 | Knee 2.5 | Ankle 2.5 | Hip 3.5 | Knee 3.5 | Ankle 3.5 | Hip 4.5 | Knee 4.5 | Ankle 4.5 |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 32.8 | 11.3 | 2.2 | 37.6 | 11.8 | 2.1 | 41.8 | 13.3 | 1.6 |
| 5 | 31.4 | 21.3 | 2.3 | 35.3 | 22.2 | 0.7 | 38.4 | 22.9 | −0.7 |
| 10 | 31.4 | 35.8 | 10.8 | 35.0 | 37.6 | 9.4 | 37.7 | 38.4 | 8.1 |
| 15 | 29.0 | 42.4 | 18.6 | 31.0 | 43.5 | 18.7 | 32.3 | 44.4 | 18.7 |
| 20 | 23.2 | 40.9 | 22.6 | 22.3 | 40.2 | 22.8 | 21.1 | 40.1 | 23.0 |
| 25 | 15.1 | 33.9 | 20.6 | 11.4 | 31.2 | 17.7 | 7.7 | 29.7 | 14.9 |
| 30 | 6.7 | 24.4 | 10.9 | 0.8 | 20.1 | 1.9 | −4.3 | 17.1 | −5.6 |
| 35 | 0.2 | 16.7 | −3.4 | −5.7 | 13.3 | −15.8 | −10.4 | 12.5 | −22.6 |
| 40 | −2.7 | 15.8 | −14.6 | −7.1 | 18.0 | −22.6 | −10.3 | 22.9 | −24.5 |
| 45 | −2.3 | 24.4 | −18.8 | −5.3 | 33.4 | −20.4 | −7.6 | 42.2 | −22.3 |
| 50 | 0.7 | 41.0 | −17.5 | −1.8 | 54.0 | −18.7 | −4.1 | 64.4 | −21.9 |
| 55 | 4.8 | 60.0 | −14.7 | 3.2 | 75.2 | −17.2 | 1.7 | 86.3 | −19.4 |
| 60 | 10.9 | 77.2 | −11.0 | 12.4 | 94.0 | −12.8 | 13.2 | 105.6 | −14.4 |
| 65 | 20.4 | 89.3 | −5.8 | 25.7 | 105.9 | −7.8 | 29.5 | 117.1 | −9.3 |
| 70 | 30.9 | 93.1 | −1.4 | 39.1 | 107.4 | −4.0 | 44.9 | 116.8 | −5.4 |
| 75 | 38.9 | 87.2 | 1.3 | 48.0 | 97.8 | −1.6 | 54.6 | 105.4 | −3.0 |
| 80 | 43.0 | 72.9 | 2.3 | 52.0 | 80.5 | −0.5 | 59.2 | 86.8 | −1.6 |
| 85 | 42.9 | 52.4 | 2.9 | 52.0 | 58.0 | 0.9 | 60.0 | 63.9 | 0.8 |
| 90 | 39.5 | 29.8 | 3.3 | 47.9 | 33.4 | 2.7 | 55.7 | 38.0 | 3.2 |
| 95 | 35.5 | 13.7 | 3.1 | 42.1 | 14.9 | 3.2 | 48.1 | 17.8 | 3.4 |

**Table 4 – peaks and their timing (mean of individual runners, computed here).** Values are degrees, with % of cycle in brackets.

| Event | 2.5 m/s | 3.5 m/s | 4.5 m/s |
|---|---|---|---|
| Knee at contact | 11.3 | 11.8 | 13.3 |
| Peak stance knee flexion | 42.7 (16 %) | 43.7 (15 %) | 44.6 (15 %) |
| Peak ankle dorsiflexion | 23.0 (21 %) | 23.2 (20 %) | 23.4 (20 %) |
| Peak hip extension | −3.6 (41 %) | −8.0 (39 %) | −11.8 (37 %) |
| Peak plantarflexion | −20.0 (46 %) | −23.8 (41 %) | −26.5 (40 %) |
| Peak swing knee flexion | 93.5 (69 %) | 108.7 (68 %) | 119.1 (68 %) |
| Peak hip flexion | 43.7 (82 %) | 52.8 (82 %) | 60.5 (84 %) |

- **Cross-checks:** at 2.9 m/s the knee is at 17.8° at contact and peaks at 46.3° in stance; peak hip adduction is 10.4° (Heiderscheit 2011). A normal stance knee peak is about 45° (Souza).
- **Pelvis (computed here from the ASIS and PSIS markers):**
  - Signs: tilt + = anterior; obliquity + = right side up; rotation + = right side forward.
  - Standing pelvis (ASIS–PSIS line): 9.8°.
  - **Tilt:** on average 4.3 / 5.9 / 6.7° more anterior than standing. It oscillates twice per stride over a range of 8.2 / 8.9 / 8.9°. Least anterior at about 10 % (early stance); most anterior at about 40 %, just after toe-off.
  - **Obliquity:** peak-to-peak 10.7 / 13.4 / 15.4°. The stance side is highest at about 15 %, i.e. the swing side drops at mid-stance.
  - **Rotation:** peak-to-peak 8.2 / 11.2 / 14.6°. The pelvis turns with the swinging leg. The right side is furthest back at about 10 % and furthest forward at about 60 %, i.e. the leg's mid-swing.
  - Per-5 % values at 3.5 m/s are in Table 5.
- **Trunk and arms:**
  - Upper-body (shoulder) rotation is **23.75°** when running at 3.0 m/s vs 8.1° when walking at 1.5 m/s. It rises to 35.7° with the arms restrained. Head yaw is 6.1°. Peak pelvis and peak shoulder rotation are **94° out of phase** in running vs 149° in walking (Pontzer 2009, https://journals.biologists.com/jeb/article/212/4/523/18953/Control-and-function-of-arm-swing-in-human-walking).
  - Trunk lean: about 7° more lean lowered patellofemoral stress (Teng &amp; Powers, cited by Souza). Mean trunk lean differed by about 20° between runners (Folland 2017, https://www.ebi.ac.uk/europepmc/webservices/rest/PMC5473370/fullTextXML).
  - **Not verified:** a normative trunk-lean value for distance running, and the elbow ~90° figure.

## 4. Centre of mass (computed here: double integration of the treadmill force)

- **Vertical oscillation per stride (peak to trough):** 8.9 / 8.8 / 8.0 cm. Pelvis markers give 9.9 / 9.5 / 8.2 cm.
  - The drop from touchdown to the lowest point is 6.5 / 5.6 / 4.8 cm.
  - Lowest at **~15 % and ~65 %** (mid-stance of each foot), the opposite of walking. Highest at **~40 % and ~90 %** (mid-flight).
- **Literature:**
  - 8.7 cm at 2.9 m/s; 10.7 cm at −10 % cadence and 7.3 cm at +10 % (Heiderscheit).
  - Bolt: 4.9 cm. Elite sprinters: 4.7–12 cm (Čoh 2018).
- **Forward-speed fluctuation:** the range is 0.19 / 0.23 / 0.25 m/s (≈6–8 % of speed). Slowest at about 15–20 %, fastest in flight.

**Table 5 – 3.5 m/s, per 5 % (computed here).** COM and forward-velocity values are deviations from the stride mean.

| % | Pelvic tilt vs standing (°) | Obliquity (°) | Rotation (°) | COM height (cm) | Forward velocity (m/s) |
|---|---|---|---|---|---|
| 0 | 5.8 | 2.7 | −2.6 | 1.2 | 0.07 |
| 5 | 3.1 | 3.5 | −3.7 | −1.5 | 0.03 |
| 10 | 2.6 | 5.1 | −4.9 | −3.6 | −0.07 |
| 15 | 3.9 | 5.6 | −4.3 | −4.1 | −0.14 |
| 20 | 4.8 | 2.8 | −3.4 | −2.8 | −0.11 |
| 25 | 5.8 | −0.5 | −3.1 | −0.4 | −0.03 |
| 30 | 7.1 | −3.8 | −2.4 | 2.0 | 0.05 |
| 35 | 8.9 | −5.5 | −1.1 | 3.6 | 0.07 |
| 40 | 9.7 | −4.7 | 0.0 | 4.0 | 0.07 |
| 45 | 8.6 | −3.6 | 1.0 | 3.2 | 0.07 |
| 50 | 5.9 | −3.7 | 2.4 | 1.2 | 0.06 |
| 55 | 3.3 | −4.4 | 3.7 | −1.6 | 0.03 |
| 60 | 2.8 | −5.6 | 5.1 | −3.8 | −0.07 |
| 65 | 3.7 | −5.5 | 4.7 | −4.5 | −0.14 |
| 70 | 4.7 | −3.1 | 3.9 | −3.3 | −0.12 |
| 75 | 5.4 | −0.2 | 3.3 | −1.0 | −0.03 |
| 80 | 6.5 | 2.9 | 2.3 | 1.5 | 0.05 |
| 85 | 8.1 | 4.4 | 0.8 | 3.2 | 0.07 |
| 90 | 9.1 | 3.7 | −0.3 | 3.7 | 0.07 |
| 95 | 8.3 | 2.5 | −1.2 | 3.1 | 0.07 |

## 5. Ground reaction forces

**Peaks:**
- Raw vertical peak: **2.38 ± 0.15 / 2.65 ± 0.16 / 2.83 ± 0.21 BW**, reached at about 15–16 % of the cycle (computed here).
- 2.41 BW at 2.9 m/s (Heiderscheit).
- 2.46 BW at 14 km/h, +0.06 BW per km/h (Burns 2021).
- 2.7 BW at 3.5 m/s → 3.6 BW at 7.0 m/s, then flat to 9 m/s (Dorn 2012).
- Bolt: 4.2 BW, estimated from a sine model (Čoh 2018).
- Average vertical force over contact at top speed: 2.30 vs 1.76 BW for top speeds of 9.96 vs 7.10 m/s (Weyand 2000).

**Rearfoot-strike impact transient (computed here, simple peak detector on the raw force):**
- 1.29 ± 0.27 BW at 36 ms; 1.64 ± 0.34 BW at 35 ms; 1.84 ± 0.46 BW at 29 ms.
- Loading rate (20–80 % of the impact peak): **55 / 73 / 97 BW/s**.
- **Uncertain:** the same detector also flagged bumps in most midfoot and forefoot trials, so do not rely on strike-type contrasts.

**Impulses** (Fukuchi Table 4): braking −0.34 / −0.49 / −0.56 N·s/kg; propulsive 0.27 / 0.33 / 0.40 N·s/kg.

**Table 6 – force over normalized stance, BW (processed and filtered, so the impact spike is smoothed out).** Vertical shows a single hump; fore-aft is braking (−) then propulsion (+).

| % stance | Vertical 2.5 | Vertical 3.5 | Vertical 4.5 | Fore-aft 2.5 | Fore-aft 3.5 | Fore-aft 4.5 |
|---|---|---|---|---|---|---|
| 0 | 0.06 | 0.07 | 0.08 | −0.01 | −0.02 | −0.02 |
| 10 | 0.76 | 0.78 | 0.79 | −0.05 | −0.10 | −0.13 |
| 20 | 1.53 | 1.65 | 1.74 | −0.17 | −0.23 | −0.28 |
| 30 | 2.03 | 2.17 | 2.27 | −0.23 | −0.31 | −0.37 |
| 40 | 2.27 | 2.47 | 2.57 | −0.12 | −0.19 | −0.26 |
| 50 | 2.14 | 2.42 | 2.57 | 0.01 | −0.01 | −0.02 |
| 60 | 1.73 | 2.05 | 2.22 | 0.13 | 0.17 | 0.22 |
| 70 | 1.15 | 1.44 | 1.58 | 0.20 | 0.28 | 0.36 |
| 80 | 0.56 | 0.75 | 0.83 | 0.16 | 0.25 | 0.33 |
| 90 | 0.17 | 0.24 | 0.27 | 0.08 | 0.13 | 0.17 |
| 100 | 0.04 | 0.05 | 0.06 | 0.03 | 0.05 | 0.06 |

## 6. Foot strike

**Prevalence in races** (meta-analysis, Bovalino &amp; Kingsley 2021, https://www.ebi.ac.uk/europepmc/webservices/rest/PMC8581084/fullTextXML):
- Rearfoot **79 %** at the first checkpoint, **86 %** later in the race. 11 % of runners change pattern, 84 % of them toward rearfoot.
- Sapporo half marathon (elite, 15 km): 74.9 % rearfoot, 23.7 % midfoot, 1.4 % forefoot (Hasegawa).
- Manchester marathon: 87.8 → 93 % rearfoot (Larson).
- World Championship marathon (elite): 60–70 % rearfoot.
- Men's 10 km World Championship final: **0 %** rearfoot.
- In the lab (Fukuchi): 68 / 14 / 18 % at 2.5 m/s; speed did not change the pattern.

**At contact, by strike type (computed here; Rearfoot / Midfoot / Forefoot):**
- Ankle (processed angle):
  - 2.5 m/s: +6.3 / −3.2 / −8.8°.
  - 4.5 m/s: +6.5 / −4.1 / −8.0°.
- Knee: 9.6 / 12.8 / 16.6° at 2.5 m/s. Forefoot strikers land with a more bent knee.
- Foot angle relative to standing (toes up +): rearfoot +14 / +17 / +19° (at 2.5 / 3.5 / 4.5 m/s); forefoot −3 to −1°.
- Maximum eversion: −4.9 / −6.6 / −7.8° (Fukuchi Table 4).

**Where the foot lands (computed here, ±2 cm timing uncertainty):**
- Heel ahead of the pelvis centre: **11.5 / 16.1 / 19.8 cm**.
- Ankle centre ahead of the pelvis centre: 17.9 / 22.0 / 25.5 cm.
- Shank angle (ankle ahead of knee): **6.0 / 8.5 / 10.3°**, steeper in rearfoot strikers (12.0° at 4.5 m/s).
- Heel ahead of COM: 9.2 cm at 2.9 m/s; 7.0 cm at +10 % cadence and 11.4 cm at −10 % (Heiderscheit).
- Overstriding test: a vertical line through the ankle bone falls in front of the pelvis at loading (Souza).
- Bolt at top speed: foot 34 cm (17 % of height) ahead of the COM, landing on the forefoot with the foot at 19.5° to the ground.

## 7. Spring-mass view (computed here)

Method: COM drop Δy from force integration; leg length L₀ = trochanter height; Farley-style geometry.

| | 2.5 m/s | 3.5 m/s | 4.5 m/s |
|---|---|---|---|
| Vertical stiffness (kN/m) | 24.9 | 31.7 | 40.2 |
| Leg stiffness (kN/m) | 11.8 | 11.5 | 10.8 |
| COM drop Δy (cm) | 6.5 | 5.6 | 4.8 |
| Leg compression ΔL (cm) | 13.8 | 15.5 | 17.9 |
| Half sweep angle (°) | 22.7 | 26.5 | 30.6 |

- **The pattern:** vertical stiffness rises with speed; leg stiffness stays roughly constant.
- **Burns 2021, 14 km/h, trained runners:** vertical stiffness 23.1 kN/m (+1.6 per km/h), leg stiffness 8.4 kN/m (no change with speed; elite +2.1), Δy 6.7 cm, ΔL 19.1 cm.
- **Brughelli &amp; Cronin review:** leg stiffness averages 11.2 vs 17.0 kN/m below vs above 5 m/s (cited in https://pmc.ncbi.nlm.nih.gov/articles/PMC10368467/).
- **Caveat:** the numbers depend on method. The model's sweep angle is larger than the real heel-to-pelvis angle, because the centre of pressure travels along the foot during stance.

## 8. Walk–run transition

- **Speed:**
  - Preferred transition 1.93 ± 0.08 m/s vs energy-optimal 2.03 m/s (Abe 2019, https://www.ebi.ac.uk/europepmc/webservices/rest/PMC6924320/fullTextXML).
  - 1.89–2.16 m/s across studies, including Hreljac 1993 (Hreljac 2005, https://jssm.org/jssm-04-446.xml-Fulltext).
  - 7.7 km/h ≈ 2.14 m/s (Hansen 2017).
- **Froude number** Fr = v²/(gL) at the transition: 0.48 ± 0.06 measured, 0.57 predicted (Hansen). With L = 0.93 m, Fr 0.5 corresponds to 2.14 m/s (my arithmetic).
- **Why it happens (no consensus):**
  - Energy alone does not explain it: people switch about 5 % below the energy-optimal speed (Abe).
  - Dorsiflexor fatigue or discomfort (Hreljac).
  - Inverted-pendulum limit (Alexander; Kram 1997 — cited only, not opened).
  - Stride frequency: people switch when it nears the running "attractor" (Hansen).
- **At the switch:**
  - Stride frequency is 70.6 strides/min, between freely chosen walking (58.8) and running (82.8). Stride length is 1.81 m.
  - The COM changes from vaulting to bouncing, and the leg sweep angle shrinks (Lee &amp; Farley).

## 9. Sprint mechanics

- **Acceleration has three sections**, with breakpoints at step 4.4 ± 0.9 and step 14.1 ± 2.0 (Nagahara):
  - Top speed 10.04 m/s at the 23rd step.
  - COM height rises fast up to the 4th step, then slowly to the 14th; it peaks at 54.9 % of stature.
  - At top speed the upper trunk is about 14° from vertical and the lower trunk about 5° (derived from 75.7° and 84.7° measured from horizontal).
- **Bolt** (Čoh 2018):
  - Fastest 20 m at 12.14 m/s.
  - COM speed drops 11.44 → 11.13 m/s in braking, then rises to 12.04 m/s.
  - Swing-foot speed in propulsion is 23.4 m/s, about twice the COM's.
  - Knee angular velocity about 850°/s; thigh 587°/s at mid-stance (500–800°/s in other sprinters).
  - Berlin 2009: maximum 12.34 m/s at 67.9 m; 99 % of maximum at 48 m.
- **Elite context** (Haugen 2019, https://www.ebi.ac.uk/europepmc/webservices/rest/PMC6872694/fullTextXML):
  - Top speed is held for only 10–30 m.
  - Women run about 10 % slower.
  - Flying speeds approach 12 m/s.
- **Not verified:** trunk lean at block exit (the often-quoted ~45°), swing knee flexion when sprinting, and arm drive angles.

## 10. What looks different between speeds

| Feature | Jog (2.5 m/s) | Run (4.5 m/s) | Sprint (~10–12 m/s) |
|---|---|---|---|
| Cadence | 162 | 184 | 250–290 |
| Stance per foot / each flight | 38.5 % / 11.4 % | 32.6 % / 17.5 % | ~19–21 % / ~32 % |
| Knee lift (peak hip flexion) | 44° | 61° | higher (not verified) |
| Heel kick (peak swing knee flexion) | 94° | 119° | higher (not verified) |
| Push-off (peak hip extension) | −4° | −12° | — |
| Heel ahead of pelvis at contact | 11.5 cm | 19.8 cm | 34 cm ahead of COM (Bolt) |
| COM bounce per stride | 8.9 cm | 8.0 cm | 4.9 cm (Bolt) |
| Peak vertical force | 2.4 BW | 2.8 BW | 3.6–4.2 BW |
| Pelvis rotation / obliquity range | 8° / 11° | 15° / 15° | — |

## Gaps and flags

- **Not opened (paywalled or out of search budget), so not used:** Novacheck 1998 (its abstract has no numbers), Mann &amp; Hagy, the Schache pelvis papers, Cavanagh &amp; Lafortune, Lieberman 2010, McMahon &amp; Cheng, Farley &amp; Gonzalez, Kram 1997, Physiopedia.
- **My own computations:** the pelvis, COM, stiffness, impact and contact-geometry values from raw markers and force use my own event detection and marker-based pelvis frame. Expect a few degrees or centimetres of method error.