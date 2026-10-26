Agent "Walking biomechanics numbers research" finished (rerun 2026-10-26)

## Human walking: research notes for the animation reference (sources opened, with flags)

**How to read the flags**
- **[D]** = a value digitized from the pixels of a published figure (an open-access JPEG, about 700 px wide). Not printed in any source as a number. Typical error ±1–2°, up to ±3° on steep parts.
- **[S]** = seen only in a search snippet; page not opened.
- **[calc]** = own arithmetic on numbers from a page opened.
- No open web page prints a full 0–100 % normative table for hip, ankle or pelvis (Winter, Kadaba, Perry, CGA, Moissenet are paywalled or dataset files). The only exact curve is Winter's knee. Hip, ankle, pelvis and force curves are [D] from the open Fukuchi et al. (2018) paper. (Note, second session: the guide's section 3 uses curves computed from the Fukuchi 2018 data files themselves, `scripts/wbds_curves.py`; they agree with these [D] values to ~1°.)

---

### 1. Temporal-spatial norms

**Young adults at three self-selected speeds.** Winiarski et al. 2019: 20 women, age 20.1, height 168.6 cm, Plug-in Gait. https://pmc.ncbi.nlm.nih.gov/articles/PMC6335661/

| | Slow | Preferred | Fast |
|---|---|---|---|
| Speed (m/s) | 1.04 | 1.32 | 1.62 |
| Cadence (steps/min) [calc] | 101 | 116 | 128 |
| Stride length (m) | 1.25 | 1.38 | 1.54 |
| Step length (m) | 0.56 | 0.61 | 0.65 |
| Step / height [calc] | 0.33 | 0.36 | 0.39 |
| Stride / height [calc] | 0.74 | 0.82 | 0.91 |
| Stride time (s) | 1.20 | 1.04 | 0.93 |
| Stance (% cycle) | 64.5 | 62.9 | 62.0 |
| Swing (% cycle) | 35.5 | 36.6 | 38.0 |
| "Relative double stance" (%)* | 14.5 | 13.0 | 11.7 |
| Stride width (m, heel centres) | 0.16 | 0.15 | 0.15 |

\*Not said whether one double-support period or both.

**Perry's Rancho Los Amigos norms** quoted by Hollman: stance 62 %, swing 38 %, double support 24 %, single support 38 %, ~136 cm/s. https://pmc.ncbi.nlm.nih.gov/articles/PMC3104090/

**Rules of thumb**
- Stance ≈60 %, swing ≈40 %, single support ≈40 %, double support ≈20 %. https://now.aapmr.org/biomechanics-normal-gait/
- Double support ~10 % at each end of stance. https://ouhsc.edu/bserdac/dthompso/web/gait/intro.htm
- "Step ≈ 0.41–0.45 × height" [S] (Science Buddies) is higher than the measured 0.36.

**Speed by age and sex** (Bohannon & Andrews 2011 meta-analysis, 41 studies, 23,111 adults), m/s:

| Age | 20–29 | 30–39 | 40–49 | 50–59 | 60–69 | 70–79 | 80–99 |
|---|---|---|---|---|---|---|---|
| Men | 1.36 | 1.43 | 1.43 | 1.43 | 1.34 | 1.26 | 0.97 |
| Women | 1.34 | 1.34 | 1.39 | 1.31 | 1.24 | 1.13 | 0.94 |

https://www.physicaltherapy.utoronto.ca/sites/default/files/assets/files/11walking-speed-age-and-sex-specific-normative-values-final.pdf

**Elderly 70+** (Hollman 2011, GAITRite, n = 294)
- Men: ~103 steps/min, step 66 cm, stride 133 cm, 115 cm/s, step width 10.0 cm.
- Women: ~112 steps/min, step 57 cm, stride 115 cm, 108 cm/s, step width 7.9 cm.
- Stance 63.9 %, swing 36.1 %, double support 27.9 % (30.3 % in men 85+).
- Speed normalised to height removes the sex difference; women take shorter strides at higher cadence.

**Comfortable-speed ranges** in a speed meta-analysis: children 1.07–1.32 m/s, young adults 1.05–1.43, older 0.94–1.34. Slower walking lowers cadence and step length. https://pmc.ncbi.nlm.nih.gov/articles/PMC6595586/

**Toddlers** (Guffey 2015, GAITRite) https://pmc.ncbi.nlm.nih.gov/articles/PMC4681623/

| Age (y) | Cadence | Velocity (cm/s) | Step (cm) | Stride (cm) |
|---|---|---|---|---|
| 2–2.5 | 174.7 | 96.7 | 32.9 | 66.3 |
| 3–3.5 | 156.1 | 99.7 | 38.3 | 76.9 |
| 4.5–5 | 141.1 | 102.9 | 43.6 | 87.4 |

Step normalised to leg length ≈ 0.9–0.97 across these ages.

**Toe-out:** Winiarski mean −9.3° at preferred speed (range −2.8 to −14.3° over the cycle; negative = toe-out in Plug-in Gait); another study 6.1 ± 5.0° at mid-stance. Seber 2000 13.0–13.7° [S]; NHS range −5 to +20° [S].

---

### 2. Phases (Perry / Rancho Los Amigos) — AAPMR https://now.aapmr.org/biomechanics-normal-gait/

| Phase | % of cycle | Ends at |
|---|---|---|
| Initial contact | 0–2 | |
| Loading response | 2–12 | opposite toe-off ≈12 % |
| Mid-stance | 12–31 | heel lift ≈31 % |
| Terminal stance | 31–50 | opposite initial contact 50 % |
| Pre-swing | 50–62 | toe-off 62 % |
| Initial swing | 62–75 | feet adjacent ≈75 % |
| Mid-swing | 75–87 | tibia vertical ≈87 % |
| Terminal swing | 87–100 | initial contact |

Physiopedia: foot flat 8–10 %, heel off 30–40 %, toe off 60 %, swing 60–75 / 75–85 / 85–100 %, both feet down ~25 %. https://www.physio-pedia.com/Joint_Range_of_Motion_During_Gait

---

### 3. Joint-angle curves (0 % = heel strike, flexion +)

- **Winter knee (exact)**, 1987 1st ed., natural cadence, every 2 % in a SAS program's data: https://www.ouhsc.edu/bserdac/dthompso/web/pk/kneesas.txt — rows marked * are means of neighbours. Peaks 21.74° at 16 %, min 9.29° at 42 %, 64.60° at 74 %.
- **Fukuchi [D]**: young adults n = 24, comfortable overground, Visual3D: Fig. 3 https://cdn.ncbi.nlm.nih.gov/pmc/blobs/1e89/5922232/23bcaf42ec99/peerj-06-4640-g003.jpg and Fig. 8 https://cdn.ncbi.nlm.nih.gov/pmc/blobs/1e89/5922232/672796a4fe0a/peerj-06-4640-g008.jpg
- **Pelvis [D]**: tilt + anterior; obliquity + stance side up; rotation + stance side forward.

| % | Winter knee | Hip | Knee | Ankle DF(+) | Pelvic tilt | Obliquity | Rotation |
|---|---|---|---|---|---|---|---|
| 0 | 6.5 | 30.8 | 2.9 | 0.7 | 11.2 | 1.1 | 5.9 |
| 5 | 11.1* | 30.3 | 6.4 | −3.6 | 11.2 | 2.5 | 5.9 |
| 10 | 17.9 | 29.0 | 13.3 | −2.7 | 10.9 | 4.2 | 4.8 |
| 15 | 21.5* | 24.5 | 14.4 | 2.4 | 10.2 | 5.1 | 3.7 |
| 20 | 21.0 | 17.4 | 10.2 | 4.2 | 10.3 | 4.4 | 3.7 |
| 25 | 18.1* | 13.9 | 9.6 | 7.0 | 10.3 | 2.8 | 3.0 |
| 30 | 14.4 | 8.5 | 6.8 | 8.6 | 10.3 | 0.9 | 1.5 |
| 35 | 11.3* | 3.4 | 4.2 | 10.5 | 10.1 | −0.5 | −0.3 |
| 40 | 9.4 | −1.9 | 3.5 | 11.5 | 10.6 | −1.1 | −2.4 |
| 45 | 10.0* | −5.0 | 4.1 | 13.0 | 11.0 | −1.1 | −4.8 |
| 50 | 14.0 | −8.0 | 8.5 | 12.3 | 11.0 | −1.6 | −6.2 |
| 55 | 22.9* | −7.7 | 14.3 | 7.3 | 10.7 | −3.2 | −6.2 |
| 60 | 36.8 | −5.8 | 24.9 | −8.8 | 10.0 | −5.3 | −5.3 |
| 65 | 52.2* | 1.9 | 44.8 | −11.6 | 9.7 | −5.8 | −4.3 |
| 70 | 62.7 | 12.0 | 59.0 | −7.2 | 9.8 | −5.4 | −4.3 |
| 75 | 64.0* | 20.8 | 61.7 | −0.2 | 9.9 | −3.5 | −3.7 |
| 80 | 57.0 | 26.4 | 49.0 | 4.3 | 9.8 | −2.2 | −2.3 |
| 85 | 42.8* | 30.7 | 40.2 | 6.8 | 10.4 | −0.3 | 0.0 |
| 90 | 24.9 | 31.6 | 21.1 | 4.7 | 10.8 | 0.2 | 2.2 |
| 95 | 10.0* | 31.0 | 5.6 | 2.0 | 11.4 | 0.4 | 4.6 |
| 100 | 5.3 | 30.3 | −0.4 | 0.9 | 11.6 | 0.5 | 5.4 |

**Physiopedia phase-anchored values**: IC hip 20° flex, knee 0, ankle 0; foot flat 15° / 15° / 0–5° PF; mid-stance 0 / 5 / 5° DF; heel off 10–20° ext / 0 / 0; toe off 10–20° ext / 30 / 20° PF; early swing 20° flex / 60 / 10° PF; mid-swing 30 / 30 / 0; late swing 30 / 0 / 0.

**Speed effects, Fukuchi [D]** (slow / comfortable / fast): hip ext −6.6 @55 / −8.7 @50 / −10.5 @55–60; hip flex 31.4 / 31.7 / 33.5; knee loading 9.6 @10 / 15.4 @10 / 21.4 @15; knee swing 57.9 / 63.2 / 62.9 @75; ankle DF 14.5 / 13.0 / 12.7 @45–50; ankle PF −7.9 @70 / −12.5 @65 / −14.6 @65.

**Winiarski (women, preferred)**: obliquity +5.9 / −5.4 (range 11.3; 9.5 slow, 12.9 fast); tilt 6.2 mean, range 1.8; rotation +7.4 / −8.8 (range 15.9; 12.9 slow, 19.3 fast); hip +33.3 / −13.0, knee peak 61.5, ankle +14.5 / −19.3; hip ab/adduction +9.4 / −7.7.

**Moissenet 2019 key points** (54 adults, ISB, regressions in v* = v/√(gL)) https://www.ebi.ac.uk/europepmc/webservices/rest/PMC6606631/fullTextXML — [calc] man 30 y, BMI 23, leg 0.90 m, v* 0.3/0.4/0.5 ≈ 0.89/1.19/1.49 m/s:

| Key point | v*0.3 | v*0.4 | v*0.5 |
|---|---|---|---|
| Hip at foot strike | 20.1° | 22.2° | 24.2° |
| Hip min in stance | −14.8 @56.7 % | −16.5 @55.2 % | −18.2 @53.7 % |
| Hip max in swing | 21.0 @90.2 % | 22.4 @89.9 % | 23.8 @89.5 % |
| Knee loading peak | 6.8 @13.4 % | 9.9 @14.0 % | 13.0 @14.7 % |
| Knee at foot off | 34.7 @66.5 % | 33.5 @64.3 % | 32.3 @62.2 % |
| Knee swing peak | 50.2 @74.3 % | 52.4 @73.5 % | 54.5 @72.8 % |
| Ankle loading min | −4.8 @7.2 % | −4.4 @7.2 % | −4.0 @7.2 % |
| Ankle stance max | 14.9 @49.3 % | 14.7 @47.8 % | 14.4 @46.4 % |
| Ankle push-off min | −12.5 @67.8 % | −14.1 @66.2 % | −15.7 @64.6 % |

No numeric thorax, shoulder or elbow curve found.

---

### 4. Centre of mass

- Vertical p-p: Orendurff 2004 (10 adults) 2.74 ± 0.52 cm at 0.7 m/s up to 4.83 ± 0.92 cm at 1.6 m/s https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:15685471%20AND%20SRC:MED&format=json&resultType=core ; Collins 2009 5.0 ± 1.0 cm at 1.25 m/s https://pmc.ncbi.nlm.nih.gov/articles/PMC2817299/
- Lateral: Orendurff 6.99 ± 1.34 cm slowest → 3.85 ± 1.41 fastest; Tesio & Rota 2019 ~10 cm at 0.3 m/s, ~5 cm at 1.4 m/s; 3-D path with travel removed is a figure-eight, perimeter ~18 cm; standing CoM ~57 % of height https://www.ebi.ac.uk/europepmc/webservices/rest/PMC6763727/fullTextXML
- Timing: rises in early single support, falls in late single support (Tesio) → highest at mid single stance (~25–30 % and 75–80 %), lowest in double support; inverted-pendulum exchange https://pmc.ncbi.nlm.nih.gov/articles/PMC2816028/ . Lateral extremes over each stance foot (geometry; no % timing source).
- Horizontal velocity [calc from the digitized fore-aft force, stride ~1.05 s]: ~0.19 m/s p-p (±7 % of 1.3 m/s); max just after contralateral push-off (~5–8 %), min at mid single stance (~33 %). Estimate.

### 5. Ground reaction forces — Fukuchi Fig. 6 [D] https://cdn.ncbi.nlm.nih.gov/pmc/blobs/1e89/5922232/5c92d319088a/peerj-06-4640-g006.jpg

Toe-off ~61.5 %. Fore-aft − = braking; side + = medial.

| % stance | % cycle | Vertical (BW) | Fore-aft | Side |
|---|---|---|---|---|
| 0 | 0 | ~0.2 | −0.01 | −0.014 |
| 10 | 6 | 0.63 | −0.11 | −0.004 |
| 20 | 12 | 0.98 | −0.15 | 0.041 |
| 30 | 18 | 0.98 | −0.09 | 0.045 |
| 40 | 25 | 0.83 | −0.04 | 0.041 |
| 50 | 31 | 0.78 | −0.01 | 0.034 |
| 60 | 37 | 0.88 | +0.01 | 0.039 |
| 70 | 43 | 1.04 | +0.07 | 0.050 |
| 80 | 49 | 1.07 | +0.15 | 0.052 |
| 90 | 55 | 0.65 | +0.15 | 0.022 |
| 100 | 61.5 | ~0 | +0.02 | 0 |

Peaks [D]: vertical 1.03 BW at 15 % cycle (24 % stance), valley 0.77 at 30 % (49 %), second 1.10 at 47.5 % (77 %). Braking −0.15 at ~11 %, propulsion +0.18 at 52.5 %, zero crossing ~34 % (55 % stance). Side: lateral spike −0.02 at ~2.5 %, then medial ~0.05. Fast: humps ~1.17, valley ~0.64; slow flatter.
Printed table at ~1.16 m/s (Barela, harness at 0 % unloading): 104 % / 75–76 % / 93–95 % BW; braking −12.3 to −12.9 %, propulsion 12.7–13.2 % https://pmc.ncbi.nlm.nih.gov/articles/PMC4311602/

### 6. The foot

- Rockers: Perry's three split at 12 %, 31 %, 50 % [S]; one deck 0–10 / 10–30 / 30–50 [S]. Opened: foot flat ~12 % → heel lift 31 % → opposite strike 50 % → toe-off 62 % (AAPMR). A fourth "toe rocker" in pre-swing (50–62 %) is common usage, not confirmed.
- Heel-to-toe (Physiopedia): lateral calcaneus strikes first; CoP posterior calcaneus through loading; subtalar pronation to max at end of loading, neutral at mid-stance, then supination; terminal stance weight over metatarsal heads; toes the final lever.
- Clearance: min toe clearance 1.29 cm (variability ~4 mm); heel horizontal speed at contact 0.87 m/s, vertical negligible (Winter 1992) https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=TITLE:%22Foot%20trajectory%20in%20human%20gait%22&format=json&resultType=core ; Winter 1991 13 mm young / 11 mm elderly at mid-swing https://clinicalgaitanalysis.com/teach-in/clearance ; shoe sensors, 66–77 y, n = 1433, ~1.2 m/s (sensor error ~4 cm): max heel height 0.32 m (men) / 0.27 m (women); first toe peak 0.06–0.08 m at 20–25 % of swing; second toe peak just before heel strike 0.11–0.16 m; min toe clearance 0.02 m https://www.ebi.ac.uk/europepmc/webservices/rest/PMC3926567/fullTextXML

### 7. Six determinants and the critique

- Claims: pelvic rotation, pelvic tilt/drop, stance knee flexion, foot/ankle and knee mechanisms, lateral pelvic displacement — together flattening the CoM path to save energy (quoted in Kuo & Donelan https://pmc.ncbi.nlm.nih.gov/articles/PMC2816028/). Classic magnitudes (rotation ~4°, tilt ~5°) only on flashcard sites [S]; measured pelvic ranges are larger.
- Pelvic list: "virtually no effect" on trunk vertical excursion (Gard & Childress 1997, via Kuo & Donelan).
- Stance knee flexion: no meaningful reduction of p-p trunk height; lowers mean by a few mm, delays the waveform 2–6 % (Gard & Childress 1999) https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=AUTH:%22Gard%20SA%22%20AND%20(TITLE:%22pelvic%20list%22%20OR%20TITLE:%22stance-phase%20knee%20flexion%22%20OR%20TITLE:%22vertical%20displacement%22)&format=json&resultType=core
- Pelvic rotation reduces CoM displacement by 2.5 ± 1.1 mm, 12 % of the actual reduction (Kerrigan 2001) https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=TITLE:%22effect%20of%20pelvic%20list%22%20OR%20TITLE:%22Quantification%20of%20pelvic%20rotation%20as%20a%20determinant%20of%20gait%22&format=json&resultType=core
- Heel rise is the main determinant: estimated 23.4 ± 7.6 mm against a measured reduction of 21.2 ± 6.5 mm (Kerrigan 2000); up to two-thirds of the reduction vs ≤10 % for pelvic rotation (Della Croce 2001) https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=TITLE:%22refined%20view%20of%20the%20determinants%20of%20gait%22&format=json&resultType=core
- Flattening the CoM path raises energy cost up to double; bent-knee walking > 3× knee torque; steps 40 % shorter double the cost; the theory "has not prevailed"; the inverted pendulum explains gait better (Kuo & Donelan 2010).
- Pelvic rotation < 3 % of step length (VU Amsterdam 2013) [S]; rotation and list contribute little at all speeds (Lin, Gfoehler & Pandy 2014) [S].

### 8. Arm swing and trunk counter-rotation

- Amplitude: wrist sensor, ages 30–40: 53.4° dominant / 49.6° non-dominant at 1.43 m/s, 64.6 / 60.4° at 1.75 m/s; 35.7° at 61–77 y usual speed (Mirelman 2015) https://www.ebi.ac.uk/europepmc/webservices/rest/PMC4549059/fullTextXML ; upper-arm sagittal swing 28.6° right / 33.1° left at 4 km/h https://www.ebi.ac.uk/europepmc/webservices/rest/PMC12023011/fullTextXML . No open numeric shoulder or elbow curve.
- Phase: arms ~50 % of the cycle apart; arm swing lags trunk rotation by ~30 % of the cycle (Mirelman); arm angular momentum opposite to the legs, each arm with the opposite leg (Collins).
- Frequency: 2:1 at very low speeds (also in Collins' passive model); can occur below comfortable speed, normal pattern 1:1 https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0315332 ; the ~0.8 m/s threshold [S].
- Why (Collins, Adamczyk & Kuo 2009, 1.25 m/s): arms held +12 % energy, bound +7 %, anti-phase +26 %; without arm swing the foot's twisting moment rises 63 % (3.0 → 5.0 N·m bound; 8.8 N·m anti-phase); shoulder torque ~2.5 N·m — nearly passive.
- Thorax vs pelvis: phase ~−20° at 1 km/h (nearly in phase) → ~−150° at 5.4 km/h (nearly opposite) (Lamoth 2002, cited in Prins 2019) https://www.ebi.ac.uk/europepmc/webservices/rest/PMC6355803/fullTextXML ; with speed thorax rotation decreases, pelvic increases (Yang 2013) [S]; older adults ~1.0–1.15 m/s: thorax transverse 9.5°, coronal 5.8°, sagittal 4.5°; pelvis 8.3 / 5.4 / 4.3° https://www.ebi.ac.uk/europepmc/webservices/rest/PMC7350916/fullTextXML ; spinal rotation per segment T1–T7 3.4°, T7–L1 9.1°, L1–L3 8.9°, L3–S 4.8° (PMC12023011).

### 9. Head and trunk

Peters et al. (NASA), treadmill 1.8 m/s, distant target https://ntrs.nasa.gov/api/citations/20080026154/downloads/20080026154.pdf : head pitch 3.58° p-p (1.8–7.2°), yaw 2.85°; C7 vertical 5.43 cm, lateral 3.56 cm; pitch and bob twice per stride, yaw and sway once; "as the body translated up, the head pitched down"; literature 2–9 cm vertical, 1.5–8.5° pitch; head rotation ≤ 20° in locomotion (Pozzo 1990) [S]. No open normative forward-lean mean; thorax sagittal oscillation ~4–5°.

### Gaps

No open full-cycle thorax, shoulder or elbow numbers; no open children's data at 6–12 y; no open GRF table at true comfortable speed; Winter's hip and ankle tables paywalled.
