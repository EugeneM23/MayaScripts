# Center of mass: a live point, a fast trail, and a tool that moves it — design

2026-10-01. The animator: «Нам необходимо хорошо продумать и реализовать центр масс для нашего рига.
… какая-то точка к которой мы можем сделать motion trail … моушен треил изменялся если мы изменяем
положение нашего персонажа … в реальном времени как и для обычного объекта. … передвигать сам центр
массы и при этом наш риг в зависимости от карты весов тоже будет двигаться корректно … эта система
должна быть производительной … если мы сделаем на констрейнах … моушен треил отрисуется с задержкой».

Asked, and answered:
- the mass comes **from the mesh and the skin** («Из меша и скина»);
- moving the CoM moves **every part of the body** («Должны двигаться все части в зависимости от карты
  весов. Давай пока так а потом мы реализуем … запрещать передвигать например ноги когда они стоят на
  полу»);
- the UE bone `center_of_mass` is **left alone** («Не трогать»);
- the CoM is moved by **our own tool**, not a manipulator plug-in («Да, делай свой инструмент, строй до
  конца»).

## Measured first

All on `Manny_Rig.ma` with ten controls keyed over 0..100.

- **Maya's own Motion Trail on a CoM point is 4.5 s per key edit** in a GUI Maya with Cached
  Playback on and filled (5.4–6.1 s in mayapy; a trail on `hand_r` alone: 0.75 s).
  - `snapshot -motionTrail` evaluates every trail frame through a DG time context:
    `getAttr(COM.translate, time=t)` costs 41 ms a frame, `MDGContext` 45 ms, `time1.outTime` 33 ms.
  - The same frame through the parallel Evaluation Manager costs **5 ms**
    (`currentTime` / `MAnimControl.setCurrentTime` with refresh suspended), whole rig and skin included.
  - So the user's fear is right, but constraints are not the cause: the cost is evaluating the rig at
    every trail frame, whatever computes the point.
- **Cached Playback cannot be read**: refills 0.36–0.41 s after an edit, in the background, but no API
  serves its values (`dbpeek -op cache -a data` is a 277 MB dump with no values). Ghosting the CoM
  locator drew nothing in a playblast.
- **`motionTrailShape` takes points we give it**: `points` (pointArray), `startTime`, `increment`,
  `keyframeTimes`, frame markers, colours, `xrayDraw` are all writable on a shape we create.
- A timeChanged scriptJob does not fire during a scripted time walk (0 of 101 steps); a walk leaves
  nothing in the undo queue.
- The three shipped rigs carry the same world-space drivers: `RootX_M`, `IKLeg_L/R`, `IKArm_L/R`,
  `PoleLeg_L/R`, `PoleArm_L/R` (follow blends of Main/Root/limb), `IKSpine1..3_M` (follow blends).
  FK chains, fingers and the head ride them through constraints.
- The meshes are open and overlap:
  - `Skin_3p`: 45 shells, 5142 border edges; `Hands_1P` is a second copy of the arms;
  - the Creep: five meshes, the arms open at the shoulder;
  - the Orc D: one mesh with cloth layered over the skin.

  So a per-surface volume (divergence theorem) would count overlaps twice and leak through holes.

## The mass model (`maya_com/massmodel.py`, numpy, pure)

The body is the **union of the character's mesh shells, each closed by fan caps** over its border
loops, at uniform density, sampled on a voxel grid (`VOXEL` = 1.5 cm).

- **A voxel is inside** when, for any one shell, at least two of three axis rays (X, Y, Z) cross that
  shell an odd number of times: ray parity per closed shell, a majority vote over the three axes.
  The grid is offset by irrational fractions so a ray never runs through an edge.
- **A voxel is skinned** with the barycentric blend of the skin weights at the closest point of the
  meshes (`OpenMaya.MMeshIntersector`).
- **Exact for linear skinning.** With the current joint matrices `M_j` and bind matrices `B_j`, each
  voxel's rest point is `r = q · (Σ w_j B_j M_j)⁻¹`, so the model can be built in any pose. A joint
  then holds
  - mass `m_j = Σ dV w_j`,
  - local centre `c_j = Σ dV w_j (r · B_j) / m_j`,

  and **CoM(t) = Σ_j m_j (c_j · M_j(t)) / Σ m_j** at any frame.
- **Meshes used**: renderable, non-intermediate, skinned, of the character. A 1P mesh (a name token
  `1P`: `Hands_1P`, `Orc_D_1P`) is left out, or the arms count twice. Unskinned props (a weapon) carry
  no mass.
- **Sanity, gated on Manny**:
  - the segment fractions against the de Leva (1996) table;
  - total volume ≈ 70–90 L;
  - the CoM's height at the bind pose 0.53–0.59 of stature.

## The live point (`maya_com/network.py`, stock nodes)

`ns:CenterOfMass` (a transform marked `skeldarCom`, under the rig's top group or beside a bare
skeleton) holds:

- **the sum**: four `wtAddMatrix` reading the skinned joints' `worldMatrix`, with weights `m̂_j·c_jx`,
  `m̂_j·c_jy`, `m̂_j·c_jz`, `m̂_j`. In row-vector maths
  `c·M = c_x·row0 + c_y·row1 + c_z·row2 + row3`, so the CoM is
  `row0(Wx) + row1(Wy) + row2(Wz) + row3(Wt)`: four `rowFromMatrix`, one `plusMinusAverage`. That is
  nine nodes, no constraint, no extra transform per bone. The constants live in the weights and the
  model is recomputed only by Rebuild;
- `ns:COM_handle`: the point, its translate through the handle's own `parentInverseMatrix`
  (`multiplyPointByMatrix`), so it is right wherever the group stands. A three-ring sphere and a cross,
  `alwaysDrawOnTop` (the CoM is inside the body), 3 % of the character's height;
- `ns:COM_floor`: the CoM at the skeleton root's height (root motion keeps the root on the ground);
- `ns:COM_trail`, `ns:COM_floorTrail`: two `motionTrailShape`s whose points the engine writes.

Attributes on the group: `trail` (bool), `floor` (bool), `range` (enum Playback / Around),
`around` (frames), `volume` (litres), `joints` (count). The scene owns the state; a saved file reopens
with its CoM and trails.

## The trail engine (`maya_com/engine.py` + `frames.py`, pure)

The engine keeps per character the range, `points[frame]` (CoM and root height) and a set of dirty
frames. Its state lives on `sys` (trap 111), callback ids included, so a fresh module object first
removes the old one's.

**What marks frames dirty:**
- an **edited time curve** (`MAnimMessage.addAnimCurveEditedCallback`) of a node of the character. The
  frames whose sampled value changed are dirty, against a snapshot of the curve sampled at every frame
  of the range (`MFnAnimCurve.evaluate`), refreshed after each edit. A curve with no snapshot (a
  channel's first key) dirties the whole range. Driven-key curves are ignored;
- a **static attribute set** on a control or skinned joint (`MNodeMessage` attribute-changed, a plug
  with no curve input) dirties the whole range;
- a set on a curve-driven plug is a temporary tweak: only the current frame, which the engine reads
  live;
- the playback range changing, or Around's window moving with the time, dirties only the new frames;
- a scene open, or the engine starting, dirties everything.

**How it computes** — on a single-shot Qt timer, never inside a callback:
- it skips while a mouse button is down, during playback, or in a modal state;
- otherwise it walks the dirty frames nearest the current time with
  `MAnimControl.setCurrentTime` under `refresh -suspend`, ≤ `SLICE_MS` (25) per tick;
- it reads every tracked CoM at each frame (one walk serves every character), returns to the current
  frame and writes the shapes' points;
- the current frame's point is always the live CoM.

**Unkeyed tweaks survive the walk**: every curve-driven plug of the character whose live value differs
from its curve at the current time is recorded before the walk and set back after it, with undo off.

## The CoM tool (`maya_com/drag.py`, a `draggerContext`)

**When it is on.** Selecting a CoM handle switches to the tool and remembers the previous one;
selecting anything else restores that tool. W/E/R with the handle selected comes back to ours (a
handle's translate is driven, so nothing else can move it).

**What a press, drag and release do:**
- **Press**: picks the drag plane through the CoM — the view plane, **Shift** the floor (XZ), **Ctrl**
  the vertical line. It then measures the drivers' world response once (`plan_drivers`, finite
  differences in three axes, two corrective passes for the follow blends) into a local-translate map
  `A_c` per driver.
- **Drag**: `translate_c = start_c + d · A_c`, with `d` the mouse's point on the plane minus the start.
  Every part moves by `d`, so the CoM moves by `d` exactly.
- **Release**: under autoKey, a key on every moved channel that already has a curve (Maya's autoKey
  rule); a channel with no curve is a static set, as Maya's Move does it.
- `undoMode="all"`: one Ctrl+Z per drag.

**Which drivers move:**
- on a rig: the world drivers above, those that exist with free translates. **`Main` (root motion) is
  never moved**;
- on a bare skeleton: `pelvis`, `ik_foot_root`, `ik_hand_root`;
- a locked channel the move needs is named.

**Why every part, and how the pins will come in.** Among all moves that put the CoM at the target,
moving every part by the same `d` is the one with the least mass-weighted displacement
(`min Σ m_p |d_p|²` subject to `Σ m_p d_p = M·Δ` gives `d_p = Δ`). The pins come later: the driver
plan carries a mobility per part (all 1 today), and with a pinned part the free parts take
`Δ · M / M_free`, solved through the CoM's Jacobian with a Newton step on release.

## The hub section (`maya_com/panel.py`)

Section `com`, **Center of Mass**, group Animation (after Graph Overlay), icon `target` (Tabler). It
holds:
- the character's line;
- **Add CoM** (primary) / **Remove** (danger), **Rebuild** (the mass model again);
- chips **Trail** and **Floor**, segments **Playback | Around** with a frames field;
- **Select CoM** (which puts the tool on);
- a status line.

Hotkey row `window.com`. The character follows the toolset's rule (`skeleton.current_root`: the
selection, the sole rig, the sole skeleton).

## Out of scope (stated)

- pinning feet on the floor (the next step, prepared above);
- per-bone mass edits;
- weapons' mass;
- the `center_of_mass` bone;
- a manipulator with axis arrows;
- the trail's keyframe beads.

## Proof

`docs/superpowers/plans/verify_com.py` runs in a disposable GUI Maya: Manny, Creep and Orc D added,
the real engine running. It gates:

- the mass model's sanity on Manny;
- the DG CoM equal to the voxel model deformed by its skin at posed frames;
- the network's cost per frame against the rig without it;
- every trail point equal to a reference walk;
- a key edit recomputing only its frames, within budget per slice;
- a static change recomputing everything;
- a tweak surviving;
- a drag moving the CoM and every deformation joint by `d`, Main still, one undo, autoKey keys;
- the other rigs untouched;
- Remove leaving nothing.

Unit tests cover the pure halves: the mass model on synthetic solids, the frame maths and the drag
maths.
