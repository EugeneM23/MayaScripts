Agent "Mathematical models of gait research" finished

# Mathematical models of human walking and running: reference notes for animators

**Markers used below.**
- **[D]**: my own algebra or worked numbers, computed from the cited equations.
- **[S]**: taken from a secondary reproduction, not from the original paper.
- **[NO]**: I did not open the paper. The details come from the citation or from memory, so treat them as unconfirmed.

The web-search budget ran out late in the work. A few items therefore rest on abstracts and are flagged.

**Reference adult for the worked numbers:**
- height 1.75 m, mass 70 kg, g = 9.81 m/s²;
- leg length (hip height) L ≈ 0.9 m. Morin's method uses L = 0.53 × height, which gives 0.93 m.

---

## 1. Inverted pendulum (compass gait, rimless wheel) and step-to-step transitions

**Idea.** In single support the stance leg acts as a rigid strut. The centre of mass (COM) vaults over the foot on an arc, trading kinetic energy for potential energy: it is slowest and highest at midstance. The vault itself costs almost nothing. The cost comes at each step transition, where the trailing leg's push-off and the leading leg's collision turn the COM velocity from downward to upward.

**Equations**
- **Stance.** $\ddot\theta = \frac{g}{L}\sin\theta$, and $\tfrac12 Mv^2 + MgL\cos\theta$ stays constant.
- **Collision (rimless wheel, inter-leg angle $2\alpha$).** $\dot\theta^+ = \dot\theta^-\cos 2\alpha$, so a fraction $\sin^2 2\alpha$ of the kinetic energy is lost.
  - Step map on a slope $\gamma$: $\dot\theta^+_{n+1} = \cos2\alpha\sqrt{(\dot\theta^+_n)^2 + 4\tfrac gL\sin\alpha\sin\gamma}$.
  - Steady rolling speed: $\omega^* = \cot 2\alpha\sqrt{4\tfrac gL\sin\alpha\sin\gamma}$.
  - Source: https://underactuated.mit.edu/simple_legs.html
- **Cavagna's energy recovery.** $R = 100\,\frac{|W_v| + |W_f| - W_{ext}}{|W_v| + |W_f|}\,\%$, where:
  - $W_v$ is the work to lift the COM;
  - $W_f$ is the work to re-accelerate it forward;
  - $W_{ext}$ is the sum of the increases in its total energy.
  - Sources: https://pmc.ncbi.nlm.nih.gov/articles/PMC1307665 and https://clinicalgaitanalysis.com/teach-in/efficiency
- **Maximum walking speed.** Moving on an arc needs a centripetal acceleration no larger than g: $v^2/L \le g$, so $v_{max} = \sqrt{gL}$ (Froude number Fr = 1).
  - At leg angle φ the condition is $\omega^2 L \le g\cos\varphi$, so the foot would lift first at the start and end of stance.
  - The half step angle is limited to $\Phi \le \cos^{-1}(2/3) = 48.2°$.
  - Source: https://pmc.ncbi.nlm.nih.gov/articles/PMC1617162
- **Transition work [D]** (geometry of Kuo's "simplest walking model"):
  - A push-off along the trailing leg that makes the COM velocity horizontal costs $W_{push} = \tfrac12 Mv^2\tan^2\alpha$ per step. The collision then removes the same amount.
  - If the collision comes first instead, the loss is $\tfrac12 Mv^2\sin^2 2\alpha$, about 4×. This matches Kuo &amp; Donelan's statement that a pre-emptive push-off "can reduce collision losses by three quarters".
  - With $\alpha \approx s/2L$ and $v = sf$: $W \approx \frac{Mv^2 s^2}{8L^2}$ per step, so the rate is $\dot W \approx \frac{M s^4 f^3}{8L^2}$. At fixed cadence this is the s⁴ law.
  - Example [D]: 70 kg at 1.25 m/s with s = 0.68 m gives ≈ 8.6 J per step, ≈ 15 W at 1.8 steps/s.
- **Measured (Donelan, Kram &amp; Kuo 2002).** Step length 0.4 → 1.1 m at a fixed 1.8 Hz:
  - external work rate 1 → 38 W, r² 0.96;
  - metabolic rate 7 → 379 W, r² 0.95;
  - both scale with s⁴.
  - Source: https://europepmc.org/article/MED/12409498
- **Other costs** (from https://www.sfu.ca/locomotionlab/assets/physicaltherapyreview2010.pdf):
  - swinging the leg costs ∝ f⁴ (Doke et al. 2005);
  - at comfortable speed about ⅔ of the net cost is step transitions and up to ⅓ is moving the legs;
  - the cost of step width grows with width².
- **Citation note.** The "Kuo, Donelan &amp; Ruina" paper is 2005 (Exerc Sport Sci Rev 33:88–97). The 2002 papers are Kuo (J Biomech Eng 124:113) and Donelan, Kram &amp; Kuo (J Exp Biol 205:3717).

**What it predicts for animators**
- **Timing.** The COM is highest at midstance and lowest at double support. Vertical and fore-aft motion repeat once per step (2× stride frequency); lateral motion repeats once per stride (clinicalgaitanalysis link above). Forward speed is lowest at midstance.
- **Do not flatten the bob** (Kuo &amp; Donelan PDF):
  - deliberately reducing COM displacement can double the energy cost;
  - a bent-knee walk needs more than 3× the knee torque and 2–3× the work;
  - steps 40% shorter at the same speed more than double the cost.
  
  A flat COM path reads as effortful.
- **Speeding up.** People walk faster by raising step length and frequency in nearly equal proportion, a trade-off between the s⁴ and f⁴ costs.
- **Feet.** The foot rolls like a wheel of radius ≈ 0.3 L, which cuts the collision.
- **Walk-to-run switch.** It happens near Fr ≈ 0.5 (≈ 2.1 m/s for L = 0.9 m), well below √(gL) ≈ 3 m/s.
  - Near Fr = 1 only tiny steps at unrealistic swing frequencies keep the foot down. If legs are not swung above 2–3 Hz, inverted-pendulum walking stops at ≈ 2.3–2.6 m/s.
  - Bertram &amp; Ruina's data show people avoid speeds above 2.2 m/s, cadences above 2.5 Hz and steps above 0.9 m.
  - Race walkers exceed the limit.
  - Source: Usherwood, link above.

**Limits**
- A rigid leg gives a single-hump vertical force; the real force has two humps (§2).
- It predicts too much vertical excursion (§9).
- Recovery tops out near 65%. Cavagna found the model "no longer tenable above 7 km/h".

| Quantity | Human value | Source |
|---|---|---|
| L (hip height) | ≈ 0.53 × height | https://pmc.ncbi.nlm.nih.gov/articles/PMC13211122/ |
| v_max = √(gL) | 2.9–3.1 m/s [D] | Usherwood |
| Maximum recovery | ≈ 65% at intermediate speeds; W_v = W_f (and minimum W_ext per km) at ≈ 4 km/h | Cavagna 1976 |
| Running recovery | 0–4% | Cavagna 1976 |
| Roll-over radius | ≈ 0.3 L | Kuo &amp; Donelan 2010 |
| Avoided in walking | &gt; 2.2 m/s, &gt; 2.5 Hz, &gt; 0.9 m step | Usherwood |

---

## 2. Spring-mass model (SLIP) for running, and the bipedal SLIP

**Idea.** In running the leg is a massless linear spring carrying a point mass. Elastic energy stored at landing is returned at take-off, and kinetic and potential energy fall and rise together, so there is no pendulum exchange. Geyer, Seyfarth &amp; Blickhan showed that two such springs with a double-support phase also reproduce walking.

**Equations of motion** (polar coordinates about the foot; source https://underactuated.mit.edu/simple_legs.html)
- Radial: $m\ddot r - m r\dot\theta^2 + mg\cos\theta - k(l_0 - r) = 0$.
- Angular: $m r^2\ddot\theta + 2 m r\dot r\dot\theta - m g r\sin\theta = 0$.
- Flight is ballistic. Touchdown happens when $z = l_0\cos\theta_{td}$; take-off when $r = l_0$.
- Dimensionless forms: $\tilde k = k l_0/mg$ and $\tilde E = E/mgl_0$.

**McMahon &amp; Cheng 1990** (https://europepmc.org/article/MED/2081746)
- Inputs: horizontal Froude number $U = v/\sqrt{gL}$, vertical $V = v_z/\sqrt{gL}$, and $K_{LEG} = k_{leg}L/mg$.
- At high speed, $K_{LEG}$ varies roughly linearly with U and V, and the effective vertical stiffness varies quadratically with U.
- Human data are fitted by $K_{LEG} = 15$ and $V = 0.18$.

**Stiffness from timing alone** (Morin's sine-wave method; https://pmc.ncbi.nlm.nih.gov/articles/PMC13211122/)
$$F_{max} = mg\tfrac{\pi}{2}\left(\tfrac{t_f}{t_c} + 1\right),\quad \Delta y_c = \frac{F_{max}t_c^2}{m\pi^2} - \frac{g t_c^2}{8},\quad \Delta L = L - \sqrt{L^2 - (v t_c/2)^2} + \Delta y_c$$
$$k_{vert} = F_{max}/\Delta y_c,\qquad k_{leg} = F_{max}/\Delta L$$
- $L - \sqrt{L^2 - (vt_c/2)^2} = L(1 - \cos\theta_0)$, where $\sin\theta_0 = vt_c/2L$ and $\theta_0$ is half the angle the leg sweeps.

**Stance time against stiffness [D]**
- For a vertical spring-mass that touches down at $v_{td} = g t_f/2$, with $\omega = \sqrt{k_{vert}/m}$: $t_c = [\pi + 2\arctan(g/\omega v_{td})]/\omega$. This is always longer than half the natural period.
- Worked example with the measured runner (3.1 m/s, $t_c$ = 262 ms, $t_f$ = 96 ms, 70 kg, L = 0.93 m):
  - $F_{max}$ = 1474 N (2.15 body weights);
  - $\Delta y_c$ = 6.2 cm, so $k_{vert}$ = 23.7 kN/m;
  - $\Delta L$ = 15.6 cm, so $k_{leg}$ = 9.5 kN/m;
  - $\theta_0$ = 25.9°, i.e. an angle of attack of ≈ 64° from horizontal;
  - fed back into the formula, the stiffness returns $t_c$ = 0.263 s.

**Bipedal SLIP** (Geyer et al. 2006; https://pmc.ncbi.nlm.nih.gov/articles/PMC1664632)
- Two springs: $P = k(\ell_0/\sqrt{x^2 + y^2} - 1)$ and $Q = k(\ell_0/\sqrt{(d-x)^2 + y^2} - 1)$. In double support $m\ddot x = P_x - Q(d - x)$ and $m\ddot y = P_y + Qy - mg$. The swing leg touches down at $y = \ell_0\sin\alpha_0$.
- Parameters: m = 80 kg, ℓ₀ = 1 m.
- Walking at ≈ 1.2 m/s (system energy 816 J):
  - stiff, steep solutions have α₀ &gt; 75° with k &gt; 17 kN/m;
  - compliant, flatter ones have α₀ &lt; 75° with k &lt; 17 kN/m.
- The vertical force is **M-shaped**: an early and a late peak with a dip at midstance. A rigid inverted pendulum cannot produce this.
- Model recovery is 15–35%; biped experiments reach up to ≈ 70%.
- Running solutions exist only above ≈ 3 m/s, with a gap between the walking and running speeds.
- Humans switch at ≈ 2.3 m/s on a treadmill when instructed. Overground they walk at about 1.8 m/s before switching to a run at about 2.3 m/s.

**For animators**
- In running the COM is **lowest at midstance** and highest in mid-flight, the reverse of walking. Example [D]: ≈ 6.2 cm compression plus ≈ 1.1 cm flight rise.
- A stiffer leg means shorter contact and a smaller dip.
- In walking, the double hump means a small sink just after loading and again before push-off; the pelvis is not a pure arc.
- Blickhan: bounce frequency and vertical displacement are tightly coupled (https://europepmc.org/article/MED/2625422).

**Limits.** Point mass, massless leg, no swing-leg or trunk dynamics, energy-conserving. Real leg stiffness changes somewhat with speed and surface.

| Quantity | Value | Source |
|---|---|---|
| k_leg, running | ≈ 7.5–12 kN/m (Morin); 6.5–8 kN/m in another cohort; 9.1 kN/m at 3.1 m/s | https://pmc.ncbi.nlm.nih.gov/articles/PMC6942482/, PMC13211122 |
| k_vert, running | ≈ 20–46 kN/m, rises with speed | PMC6942482 |
| K_LEG, V | 15, 0.18 | McMahon &amp; Cheng 1990 |
| Contact / flight at 3.1 m/s | 262 / 96 ms | PMC13211122 |
| Walking spring (bipedal SLIP) | ≈ 17 kN/m (80 kg, 1 m), α₀ ≈ 75° | Geyer 2006 |
| Running angle of attack | ≈ 64° [D]; "68°" in Seyfarth et al. 2002 [NO] | — |

---

## 3. Froude number and dynamic similarity

**Idea.** Two legged animals of different size move alike when they move at the same $Fr = v^2/(gL)$, with L the hip height. At equal Fr, every length scales with L and every time with $\sqrt{L/g}$.

**Equations**
- **Normalisation divisors** (Hof 1996; https://clinicalgaitanalysis.com/faq/normalisation.html):

  | Quantity | Divide by |
  |---|---|
  | Length | L |
  | Time | $\sqrt{L/g}$ |
  | Velocity | $\sqrt{gL}$ |
  | Cadence | $\sqrt{g/L}$ |
  | Force | mg |
  | Moment | mgL |
  | Power | $m g^{3/2} L^{1/2}$ |

- **Alexander (1976).** $\lambda/h = 2.3\,Fr^{0.3}$, which is the same as $v = 0.25\,g^{0.5}\lambda^{1.67}h^{-1.17}$ [D algebra].
  - Mammals switch from walk to run or trot at λ/h ≈ 2.0.
  - Thulborn's dinosaur version: walk below 2.0, trot 2.0–2.9, run above 2.9.
  - The printed formula in this source omits $g^{0.5}$.
  - Source: https://www.app.pan.pl/archive/published/app46/app46-235.pdf
- **Walk-run at Fr ≈ 0.5.** It holds across species and leg lengths, and with simulated reduced gravity the transition moved to slower speeds at about the same Fr (https://europepmc.org/article/MED/9076966). A later study in real lunar gravity reportedly found Fr &gt; 1 [NO].
- **Preferred walking.** Bohannon's comfortable speeds of 1.27–1.46 m/s give Fr ≈ 0.18–0.24 for L = 0.9 m [D]. Maximum walking at 2.53 m/s gives Fr ≈ 0.73.

**Scaling a walk [D]**
- At equal Fr: $v \propto \sqrt{gL}$, stride ∝ L, cycle time ∝ $\sqrt{L/g}$, cadence ∝ $\sqrt{g/L}$.
- Keep the joint-angle curves the same in normalised time.
- Reference: a human with L = 0.9 m walking at 1.3 m/s, step 0.68 m, 115 steps/min.

| Character | L | Walk speed | Step | Cadence | Walk-run speed (Fr 0.5) |
|---|---|---|---|---|---|
| Human | 0.9 m | 1.3 m/s | 0.68 m | 115/min | 2.1 m/s |
| Giant (×10) | 9 m | 4.1 m/s | 6.8 m | 36/min | 6.6 m/s |
| Child | 0.5 m | 0.97 m/s | 0.38 m | 154/min | 1.57 m/s |
| Mouse-sized biped | 0.05 m | 0.31 m/s | 3.8 cm | 488/min | 0.50 m/s |
| Human on the Moon (g = 1.62) | 0.9 m | 0.53 m/s | 0.68 m | 47/min | 0.85 m/s |

The classic mistake is speeding a giant's cycle linearly with size, or keeping a small creature at human tempo.

**Limits.** It assumes geometric similarity and the same joint angles. It ignores that muscle strength scales with L² while weight scales with L³, so real giants cannot sustain the same Fr. Animals that crouch, such as birds, deviate.

---

## 4. Empirical relations (stride, cadence, walk ratio, cost)

**Basic identity.** Speed = step length × cadence, $v = s\,n$; a stride is two steps.

**Stride-length power laws**

| Relation | Formula | Notes and source |
|---|---|---|
| Grieve 1968 | $s/L = (v/\sqrt{gL})^{0.42}$ | Dimensionless. L = 1 m at 1.25 m/s gives s = 0.68 m and step time 0.58 s. https://elifesciences.org/articles/81939 |
| Grieve, cadence form [D] | $n\sqrt{L/g} = (v/\sqrt{gL})^{0.58}$ | — |
| Hof 1983 | $s' = 1.1\sqrt{v'} \pm 0.2$ | Dimensionless step length (normalisation page above) |
| Alexander | $\lambda/h = 2.3\,Fr^{0.3}$ | Stride ∝ v^0.6 |

The exponents of 0.42–0.6 restate Kuo's point that step length and frequency rise nearly equally.

**Walk ratio** (Sekiya et al. 1996)
- WR = step length / cadence = **0.0063–0.0069 m/(steps/min)** from preferred speed (79 m/min) to fast (118 m/min).
- Below ≈ 62 m/min it rises sharply and becomes variable.
- Source: https://pmc.ncbi.nlm.nih.gov/articles/PMC5430280
- Consequence [D]: $s = \sqrt{WR\cdot v}$ and $n = \sqrt{v/WR}$ with v in m/min. At 80 m/min and WR 0.0065: s = 0.72 m, n = 111 steps/min.

**Step length against height.** The rule of thumb "≈ 0.41–0.45 × height" is **unconfirmed**. The models above give ≈ 0.38–0.40 × height at comfortable speed [D].

**Speeds** (Bohannon 1997; https://europepmc.org/article/MED/9143432)
- Comfortable: 1.27 m/s (women in their 70s) to 1.46 m/s (men in their 40s).
- Maximum: 1.75 m/s (women in their 70s) to 2.53 m/s (men in their 20s).

**Phases and step width**
- Boulic's support duration: $T_S = 0.752\,T_C - 0.143$ s [S]. At $T_C$ = 1.07 s that is 62% stance, 38% swing and ≈ 12% double support twice per cycle [D].
- Measured stance in youths at 1.4 m/s: 57.6%; running at 3.3 m/s: 35.6% (https://proceedings.cmbes.ca/index.php/proceedings/article/download/211/207/426).
- Preferred step width ≈ **0.13 L**; the cost rises with width² above it (https://www.sfu.ca/locomotionlab/assets/stepwidth2001.pdf).

**Metabolic cost** (Ralston 1958; https://link.springer.com/article/10.1007/BF00698754)
- $\dot E = 29 + 0.0053\,v^2$, in cal·kg⁻¹·min⁻¹ with v in m/min.
- The cost of transport $\dot E/v$ is U-shaped, with its minimum of **0.78 cal·kg⁻¹·m⁻¹ (≈ 3.3 J·kg⁻¹·m⁻¹)** at **74 m/min (1.23 m/s)**.
- The curve is flat within ≈ 3% between 1.0 and 1.6 m/s [D].
- Carlisle &amp; Kuo use 1.25 m/s as the energy-optimal steady speed (eLife link above).

**Preferred step frequency and the leg as a pendulum**
- Natural period: $T = 2\pi\sqrt{I/(mgd)}$. For a uniform rod $T = 2\pi\sqrt{2\ell/3g}$, which for ℓ = 0.9 m gives ≈ 1.55 s, i.e. 0.64 Hz [D]. Winter's segment fractions give 1.54 s [D].
- Real strides take ≈ 1.05–1.16 s, so the leg is driven faster than it would swing on its own. This fits the leg-swing cost ∝ f⁴.
- The "force-driven harmonic oscillator" (Holt et al. 1990) adds a spring to explain the preferred cadence [NO].

---

## 5. LIPM, ZMP, capture point / divergent component of motion (DCM)

**Idea.** Hold the COM at a constant height $z_c$ and the inverted pendulum becomes linear. The horizontal motion is then closed-form, sagittal and lateral decouple, and balance becomes "where to put the next foot".

**Equations**
- **LIPM.** $\ddot x = \omega^2(x - p)$, with $\omega = \sqrt{g/z_c}$ and $T_c = 1/\omega$.
- **Solution, relative to the support point.** $x(t) = x_0\cosh(t/T_c) + T_c\dot x_0\sinh(t/T_c)$ and $\dot x(t) = \frac{x_0}{T_c}\sinh(t/T_c) + \dot x_0\cosh(t/T_c)$.
- **Orbital energy.** $E = \tfrac12(\dot x^2 - \omega^2 x^2)$ is conserved.
  - E &gt; 0: the COM passes over the foot.
  - E &lt; 0: it falls back.
  - E = 0: it comes to rest over the foot.
  - Source: https://arxiv.org/abs/2011.02793 (Missura et al., citing Kajita 2001)
- **ZMP (centre of pressure).** $p = \sum_i p_i f_{iz}/\sum_i f_{iz}$ (https://underactuated.mit.edu/humanoids.html). For the LIPM, $p = x - (z_c/g)\,\ddot x$ [D].
- **DCM / capture point / extrapolated COM.** $\xi = x + \dot x/\omega$ and $\dot\xi = \omega(\xi - p)$. "The DCM is repelled by the ZMP, while the CoM is attracted to the DCM" (https://arxiv.org/abs/1909.07732, citing Pratt 2006 and Englsberger).
- **Hof's dynamic stability rule.** The extrapolated COM (XcoM, Hof's name for the same quantity) $= x + v\sqrt{l/g}$ must lie inside the base of support. The margin of stability is its distance to the edge (https://europepmc.org/article/MED/15519333).

**Lateral sway as a LIPM oscillation [D]**
- Set-up: feet at ±b (b = half the step width), step time T, instant weight transfer, t = 0 at midstance over the foot at +b.
  - Path: $y(t) = b\left[1 - \frac{\cosh\omega t}{\cosh(\omega T/2)}\right]$.
  - Peak: $y_{max} = b\,[1 - \mathrm{sech}(\omega T/2)]$; peak-to-peak sway is $2y_{max}$.
- Worked values with b = 0.0585 m (0.13 L) and $z_c$ = 0.9 m:

  | Step time T | Predicted sway (peak-to-peak) |
  |---|---|
  | 0.47 s | 2.8 cm |
  | 0.55 s | 3.6 cm |
  | 0.75 s | 5.4 cm |

- Measured sway falls from **6.99 cm at 0.7 m/s to 3.85 cm at 1.6 m/s** (Orendurff 2004; https://europepmc.org/article/MED/15685471).
- The model gets the trend right but comes out ≈ 25% low: the centre of pressure travels inside the foot, and double support is ignored.

**For animators**
- Procedural foot placement: stepping onto ξ brings the character to a stop.
- The COM leads its "stop point" by $\dot x/\omega$, ≈ 0.39 m at 1.3 m/s [D]. This sets stopping distance and push recovery.
- Faster walking means less sideways sway.
- Lateral foot placement is reportedly a constant margin outside the XcoM (Hof et al. 2010) [NO].

**Limits.** Constant height (real COM bobs 3–5 cm), point feet, massless legs, no angular momentum (Pratt added a flywheel [NO]).

| Quantity | Value |
|---|---|
| $z_c$ | ≈ 0.9 m (assumed) |
| $T_c$ | 0.30 s |
| ω | 3.3 s⁻¹ |
| Step width | 0.13 L (≈ 12 cm) |
| Lateral sway | 3.9–7.0 cm (fast to slow) |

---

## 6. Fourier / harmonic description of gait

**Idea.** A steady gait is periodic, so each joint angle is a short Fourier series of the stride frequency. Editing the coefficients interpolates, exaggerates or transfers style.

**Series.** $\theta(t) = a_0 + \sum_{n=1}^{N}\left[a_n\cos n\omega t + b_n\sin n\omega t\right]$, with $\omega = 2\pi/T$.

**How many harmonics**

| Data | Harmonics | Fit | Source |
|---|---|---|---|
| Walking joint angles | 3 (hip, knee), 4 (ankle) | r ≈ 0.99 / 0.98; relative RMSE 7.4% / 9.8% | https://pmc.ncbi.nlm.nih.gov/articles/PMC12758755/ |
| Running joint angles | ≤ 5 coefficient pairs for most of 104 angles | r &gt; 0.99, RMSD &lt; 0.5° | https://vbn.aau.dk/da/publications/running-in-circles-describing-running-kinematics-using-fourier-se |
| Whole-body markers (Troje) | mean + fundamental + 2nd harmonic | "better than 95% accuracy" | https://blogs.mathworks.com/cleve/?p=1373 |

**Unuma, Anjyo &amp; Takeuchi 1995** [S] (https://www.old.cescg.org/CESCG-2004/papers/42_KrausMichal.pdf)
- Each joint m of a gait, with time normalised to a 2π period: $\Theta_m(t) = A_{m0} + \sum_n A_{mn}\sin(nt + \phi_{mn})$. A second gait is $\Psi_m$ with coefficients $B$ and phases $\psi$.
- Blend: $\Theta_m(t,s) = [(1-s)A_{m0} + sB_{m0}] + \sum_n[(1-s)A_{mn} + sB_{mn}]\sin\big(nt + (1-s)\phi_{mn} + s\psi_{mn}\big)$.
  - 0 &lt; s &lt; 1 interpolates;
  - s &gt; 1 exaggerates ("very tired");
  - s &lt; 0 gives the opposite ("brisk").
- A style is the difference $C_{mn} = A_{mn} - B_{mn}$, $\gamma_{mn} = \phi_{mn} - \psi_{mn}$, and can be superimposed on another gait (a "tired" or "brisk" run).

**Bruderlin &amp; Williams 1995, "Motion signal processing"** (https://research.cs.wisc.edu/graphics/Courses/777-s2006/TextWeb/Summaries/Week04/eldawy-MoSigProcessing.txt)
- Per-joint multiresolution band split with per-band gains, used like an equaliser.
- Multitarget blending done band by band, with dynamic-programming time-warping.
- Waveshaping through a lookup table (e.g. joint limits).
- Displacement mapping.

**Limits.** Works only on periodic, steady gaits. Foot contacts are not preserved under blending, so footskate cleanup or IK is needed (§7).

---

## 7. Procedural walk generators in computer animation

**KLAW** (Bruderlin &amp; Calvert 1989; abstract via https://history.siggraph.org/?p=119374)
- Velocity, step length and step frequency generate many walks in near real time.
- Hybrid control: dynamic leg equations "analytically constrained" to locomotion, with the stance leg as an inverted pendulum [S, patent description], plus kinematics for the rest.

**Running** (Bruderlin &amp; Calvert 1996; https://graphicsinterface.org/proceedings/gi1996/gi1996-25/)
- Interactive parameters: speed, step length, flight height, heel or toe strike.
- Three kinds of knowledge:
  - empirical rules (e.g. a speed change also adjusts step length);
  - per-step ballistic physics;
  - limb-coordination states.

**Boulic, Magnenat-Thalmann &amp; Thalmann 1990** [S] (reproduced in https://patents.google.com/patent/US9714797B2/en)
- Relative velocity: $v_{rel} = v/H_t$, with $H_t = 0.491\,\times$ height.
- Relative cycle length: $R_C = 1.3461\sqrt{v_{rel}}$, in thigh-height units [D, from the units].
- Cycle duration: $T_C = R_C/v_{rel}$; support: $T_S = 0.752\,T_C - 0.143$.
- Body translations are sinusoids of normalised time $t_R$: vertical at 2× the cycle frequency with amplitude ∝ $v_{rel}$, lateral at 1×.
- The reproduction's amplitude constants look garbled, so they are unconfirmed.
- Check [D]: height 1.8 m at 1.4 m/s gives a 1.50 m stride and a 1.07 s cycle, which is realistic.

**Further references**
- Multon et al. 1999, "Computer animation of human walking: a survey" [NO]. It sorts approaches into kinematic, dynamic and motion-capture based.
- Sun &amp; Metaxas 2001, "Automating gait generation" [NO]. From memory, it adapts a walk to terrain using sagittal elevation angles.

**Central pattern generators**
- Taga et al. 1991: neural oscillators coupled with body dynamics give a "global limit cycle" that walks stably under disturbances. Changing one parameter produces running, with hysteresis (https://link.springer.com/article/10.1007/BF00198086).
- Matsuoka 1985: mutually inhibiting neurons with adaptation oscillate sustainably (https://link.springer.com/article/10.1007/BF00449593). Usual form [NO]: $\tau\dot u_i = -u_i - \beta v_i - \sum_j w_{ij}y_j + s_i$, $\tau'\dot v_i = -v_i + y_i$, $y_i = \max(0, u_i)$.

**Footskate cleanup** (Kovar, Schreiner &amp; Gleicher 2002; https://research.cs.wisc.edu/graphics/Gallery/kovar.vol/Cleanup/)
- Footplant constraints are switched on and off over time.
- The root is projected so the ankle can reach, and those projections are filtered over time.
- Leg lengths are allowed tiny changes, which avoids the knee "popping" near full extension.
- Ankle orientation is blended at heel-to-flat transitions.

---

## 8. Physics-based and learned controllers

**SIMBICON** (Yin, Loken &amp; van de Panne 2007; https://www.cs.ubc.ca/~van/papers/2007-siggraph-simbicon.pdf)
- A finite state machine: 4 states for walking, 2 for running. Transitions happen on time or on foot contact.
- Each joint uses PD control, $\tau = k_p(\theta_d - \theta) - k_d\dot\theta$.
- Torso and swing hip are controlled in the world frame, with the stance hip given $\tau_A = -\tau_{torso} - \tau_B$.
- Balance comes from the swing-hip target: $\theta_d = \theta_{d0} + c_d d + c_v v$, where d is the horizontal distance from the stance ankle to the COM and v is the COM velocity. The hip midpoint stands in for the COM.

**DeepMimic** (Peng, Abbeel, Levine &amp; van de Panne 2018; https://arxiv.org/abs/1804.02717)
- PPO policy at 30 Hz setting PD targets; Bullet physics at 1.2 kHz.
- Reward: $r = 0.7r^I + 0.3r^G$ (imitation and goal).
- Imitation reward: $r^I = 0.65\,e^{-2\sum\|\hat q\ominus q\|^2} + 0.1\,e^{-0.1\sum\|\dot{\hat q} - \dot q\|^2} + 0.15\,e^{-40\sum\|\hat p_e - p_e\|^2} + 0.1\,e^{-10\|\hat p_c - p_c\|^2}$ (pose, velocity, end-effectors, COM).
- Episodes start from states sampled along the reference clip and end early when the torso or head touches the ground. A phase ϕ ∈ [0, 1] is part of the state.

**Phase-Functioned Neural Network** (Holden, Komura &amp; Saito 2017; https://theorangeduck.com/media/uploads/other_stuff/phasefunction.pdf)
- The regression network's weights are a cyclic cubic Catmull-Rom spline of the phase p over 4 weight sets β:
$$\Theta = \beta_{k_1} + w(\tfrac12\beta_{k_2} - \tfrac12\beta_{k_0}) + w^2(\beta_{k_0} - \tfrac52\beta_{k_1} + 2\beta_{k_2} - \tfrac12\beta_{k_3}) + w^3(\tfrac32\beta_{k_1} - \tfrac32\beta_{k_2} + \tfrac12\beta_{k_3} - \tfrac12\beta_{k_0})$$
  with $w = (4p/2\pi) \bmod 1$ and $k_n = (\lfloor 4p/2\pi\rfloor + n - 1) \bmod 4$.
- 512 hidden units per layer, ELU activation.
- Runs in milliseconds with a few MB of memory; the phase function can be precomputed.

**Motion matching** (Clavet, GDC 2016 [NO; the vault was in maintenance])
- Every few frames, search the whole mocap database for the frame whose feature vector best matches the current pose and the desired future trajectory, then jump there.
- Features in Holden's reference implementation (https://github.com/orangeduck/Motion-Matching, database.h):
  - both feet's positions and velocities, and the hip velocity, in the root's frame;
  - the root's future positions and facing at +20, +40 and +60 frames.
- Each group is z-normalised and weighted. The cost is a squared distance plus a transition cost, with pruning by bounding boxes.
- Memory grows linearly with the data (https://theorangeduck.com/page/learned-motion-matching).

---

## 9. Small models useful to animators

**Swing foot path**
- Minimum-jerk curve: Flash &amp; Hogan minimise $\int\dddot x^2dt$ (https://pmc.ncbi.nlm.nih.gov/articles/PMC6565116/). Rest to rest this gives $x(\tau) = x_0 + (x_f - x_0)(10\tau^3 - 15\tau^4 + 6\tau^5)$ [D, standard solution].
- A cycloid, $x = r(\phi - \sin\phi)$, $y = r(1 - \cos\phi)$, also starts and stops at zero velocity.
- Measured (Winter 1992; https://europepmc.org/article/MED/1728048):
  - minimum toe clearance is only **1.29 cm** (variability ≈ 4 mm), at mid-swing;
  - at heel contact the foot moves 0.87 m/s horizontally and almost not at all vertically, so it skims in.
- The swing covers one stride in ≈ 38–40% of the cycle, so the foot averages ≈ 2.5× walking speed [D].

**Swing as a pendulum**
- A passive straight leg would need about half its period, ≈ 0.77 s.
- Real swing lasts ≈ 0.4 s, so the swing is driven, shortened by knee flexion, and costs ∝ f⁴ (Kuo &amp; Donelan).

**Pelvis vertical path**
- $z(t) \approx \bar z - A\cos(2\pi\cdot 2t/T_{stride})$: one cycle per step, lowest at double support.
- **Compass gait [D].** $\Delta z = L(1 - \cos\theta)$ with $\sin\theta = s/2L$. For s = 0.65 m and L = 0.9 m this gives 6.1 cm peak-to-peak.
- **With a rolling foot of radius R = 0.3 L [D].** $\Delta z = (L - R)(1 - \cos\theta)$ with $s = 2(L - R)\sin\theta + 2R\theta$, which gives **4.2 cm**.
- **Measured** (Orendurff): **2.74 cm at 0.7 m/s rising to 4.83 cm at 1.6 m/s**.
- Pelvic list and stance knee flexion barely reduce it (https://clinicalgaitanalysis.com/faq/determinants.html).
- Running dips the other way: ≈ 6–9 cm, lowest at midstance (CMBES link above).

**Lateral sway.** Use the §5 formula; sway shrinks as speed rises.

**Arm swing**
- Pendulum period [D] from Winter's segment fractions (I did not re-open that table): ≈ 1.35 s. A uniform rod of 0.77 m gives 1.44 s.
- Walking strides take ≈ 1.05–1.16 s, so the arm swings slightly faster than its natural period with little effort.
- Collins, Adamczyk &amp; Kuo 2009 (https://pmc.ncbi.nlm.nih.gov/articles/PMC2817299/):
  - a passive model swings its arms like a human;
  - peak shoulder torque is 2.5 N·m, under 25% of what holding the arm horizontal needs;
  - holding the arms still raises the net cost 12%, binding them 7%, swinging them in the wrong phase 26%;
  - normal arm swing lowers the peak vertical free moment (3.0 N·m against 5.0 N·m when bound).
- At slow speeds the arms reportedly switch to swinging twice per stride (Wagenaar &amp; van Emmerik 2000) [NO].

---

## Not confirmed

- The 0.41–0.45 × height rule.
- Boulic's trajectory amplitude constants.
- Matsuoka's exact equations.
- The details of Sun &amp; Metaxas 2001 and Multon et al. 1999.
- Seyfarth's 68° running angle of attack.
- Holt's force-driven oscillator.
- The arm frequency switch at slow speeds.
- The lunar-gravity transition result.
- Winter's segment table (used for the pendulum periods but not re-opened).
- Clavet's GDC talk content.
- Kajita 2001/2003 and Pratt 2006 were not opened; their equations come from the opened papers that cite them.