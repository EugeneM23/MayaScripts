# Slime in the browser: the build

Spec: `docs/superpowers/specs/2026-11-02-slime-webgpu-prototype-design.md`.
Everything lands in `docs/superpowers/plans/slime/web/`.

Verification is by eye, in the Claude browser pane over `http://127.0.0.1` (a `file://` page is a
static snapshot there). WebGPU works in it: Chrome 152, Intel Xe-LPG, `timestamp-query` available.

## 1. The page stands up and clears a frame

`index.html`, `ui.js` skeleton, `sim.js` device setup. A canvas configured for WebGPU, a panel, a
"no WebGPU" message where `navigator.gpu` is missing, `serve.py`.

Done when: the pane shows the floor grid and the panel, and the console reports the adapter.

## 2. Particles exist and fall

The five buffers, a seeding kernel (a blob of particles in a jittered lattice), and the point debug
view. No MPM yet — integrate gravity on the particles and bounce them off the floor.

Done when: a screenshot shows a blob of points falling and piling on the floor. This proves the
buffers, the dispatch and the camera before any solver physics can confuse them.

## 3. The MLS-MPM step, as a fluid

`shaders.sim.js`: clear, P2G, grid, G2P, with the Q16.16 fixed-point atomics and the quadratic
B-spline weights. The constitutive model at its **water** limit first (pressure only, no SVD) —
the simplest thing that can be correct.

Done when: the blob behaves as a liquid (spreads flat, no blow-up), total mass is conserved on the
readout, and the NaN counter stays at zero.

## 4. The material: SVD, yield, viscosity

Add the 3×3 Jacobi SVD, the Hencky stress and the Herschel–Bulkley return mapping. The NaN guard
and its counter.

Done when the four behaviours from the spec can be told apart by moving the sliders: a high yield
holds a mound, a zero yield spreads flat, a high viscosity coils a poured stream.

## 5. Screen-space rendering

`render.js` / `shaders.render.js`: sphere depth, thickness, narrow-range filter, normals,
composite with Fresnel and Beer–Lambert. The depth/normals debug view.

Done when: a screenshot reads as a translucent material rather than a cloud of points.

## 6. The sandbox

Nozzle, mouse sphere, obstacle sphere, sticky walls, drop/pour/reset/pause/step, the presets and
the readouts.

Done when a strand can be pulled out of a pool with the mouse and it snaps.

## 7. Tune kissel, and measure

Screenshot the four judging behaviours, set the Kissel preset's numbers against them, and record
the frame time on the integrated GPU. Write what was measured into the spec's own record and
CLAUDE.md.

## Known risks, and the fallback for each

- **The SVD in f32** is the fragile step. The NaN guard means a bad slider degrades rather than
  explodes; if it proves unstable at useful settings, the fallback is a polar decomposition plus an
  analytic symmetric eigendecomposition.
- **Speed on the integrated GPU.** The substep, particle and grid counts are sliders, so a slow
  machine turns them down; the measurement goes in the record rather than a promise.
- **`file://`** may refuse the plain `<script src>` tags. `serve.py` is the supported road either
  way; if the double-click road fails it is stated and not fought.
