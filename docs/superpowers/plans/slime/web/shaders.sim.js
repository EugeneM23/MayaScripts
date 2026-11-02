// The MLS-MPM solver, in WGSL.
//
// Four kernels a substep: clear the grid, scatter the particles onto it (P2G),
// solve the grid, gather back (G2P). The material model lives at the end of G2P
// and is the whole point of the prototype: elasticity, a yield point and a
// viscous relaxation, so the same solver is water, honey, kissel or jelly.
//
// Two things here are not obvious and are explained where they happen: the grid
// accumulates in fixed point because WGSL has no float atomics, and the 3x3 SVD
// is the one step that can produce a NaN, so a particle that goes bad is reset
// and counted instead of being allowed to poison the grid.

const SIM_WGSL = /* wgsl */ `

// ---------------------------------------------------------------- fixed point
//
// WGSL's atomicAdd works on i32 and u32 only. The grid therefore accumulates
// mass and momentum as Q16.16 integers. The budget: a node is reached by at
// most 27 cells' worth of particles at ~8 a cell, each weight <= 1 and a
// particle mass of 0.125, so mass per node stays under ~30 and momentum under
// ~30*v with v bounded by the CFL condition. At x65536 that is ~1e8 against the
// 2.1e9 an i32 holds.
//
// The happy side effect: integer addition is associative, so the result does
// not depend on the order the workgroups land in. The same seed gives the same
// frame, every run.
const FP : f32 = 65536.0;
const INV_FP : f32 = 0.0000152587890625;
const STAT_FP : f32 = 256.0;

struct Params {
  gn        : vec4<f32>,   // grid resolution, xyz
  mouse     : vec4<f32>,   // xyz centre in cells, w radius (0 = off)
  mouseVel  : vec4<f32>,   // xyz velocity in cells/s, w strength
  obstacle  : vec4<f32>,   // xyz centre, w radius
  emitPos   : vec4<f32>,   // xyz centre, w radius
  emitDir   : vec4<f32>,   // xyz direction, w speed
  dt        : f32,
  gravity   : f32,
  mu        : f32,         // elasticity: the shear modulus
  lam       : f32,         // incompressibility: the bulk modulus
  yieldS    : f32,         // how much shape it holds before it gives in
  visc      : f32,         // how slowly it gives in once it does
  wallStick : f32,         // 0 slips along a wall, 1 clings to it
  pmass     : f32,
  pvol      : f32,
  nParts    : f32,
  seedBase  : f32,
  seedCount : f32,
  seedKind  : f32,         // 0 blob, 1 stream
  frame     : f32,
  jitter    : f32,
  latN      : f32,         // lattice points across the shape
  latM      : f32,         // and along a stream
  latStep   : f32,         // the spacing, in cells
  pad1      : f32,
  pad2      : f32,
};

@group(0) @binding(0) var<uniform> P : Params;
@group(0) @binding(1) var<storage, read_write> pos    : array<vec4<f32>>;  // xyz cells, w age (<0 dead)
@group(0) @binding(2) var<storage, read_write> vel    : array<vec4<f32>>;  // xyz cells/s, w plastic rate
@group(0) @binding(3) var<storage, read_write> defo   : array<vec4<f32>>;  // F, three columns a particle
@group(0) @binding(4) var<storage, read_write> affine : array<vec4<f32>>;  // C, three columns a particle
@group(0) @binding(5) var<storage, read_write> extra  : array<f32>;        // accumulated plastic flow
@group(0) @binding(6) var<storage, read_write> gridA  : array<atomic<i32>>;// m, px, py, pz a node
@group(0) @binding(7) var<storage, read_write> gridV  : array<vec4<f32>>;  // xyz velocity, w mass
// 0 mass, 1 resets, 2 live, then why a reset happened: 3 position, 4 velocity,
// 5 deformation, 6 the speed cap, and 7 the fastest particle seen (x16).
// Knowing which of those trips is the difference between fixing a blow-up and
// guessing at it.
@group(0) @binding(8) var<storage, read_write> stats  : array<atomic<i32>>;

fn gdim() -> vec3<i32> { return vec3<i32>(P.gn.xyz); }

fn nodeIndex(c: vec3<i32>) -> i32 {
  let g = gdim();
  return (c.z * g.y + c.y) * g.x + c.x;
}

fn inGrid(c: vec3<i32>) -> bool {
  let g = gdim();
  return all(c >= vec3<i32>(0)) && all(c < g);
}

// Clamped so a wild value cannot wrap the integer.
fn toFixed(v: f32) -> i32 {
  return i32(clamp(v * FP, -2.0e9, 2.0e9));
}

fn getF(i: u32) -> mat3x3<f32> {
  return mat3x3<f32>(defo[i * 3u].xyz, defo[i * 3u + 1u].xyz, defo[i * 3u + 2u].xyz);
}

fn setF(i: u32, m: mat3x3<f32>) {
  defo[i * 3u]      = vec4<f32>(m[0], 0.0);
  defo[i * 3u + 1u] = vec4<f32>(m[1], 0.0);
  defo[i * 3u + 2u] = vec4<f32>(m[2], 0.0);
}

fn getC(i: u32) -> mat3x3<f32> {
  return mat3x3<f32>(affine[i * 3u].xyz, affine[i * 3u + 1u].xyz, affine[i * 3u + 2u].xyz);
}

fn setC(i: u32, m: mat3x3<f32>) {
  affine[i * 3u]      = vec4<f32>(m[0], 0.0);
  affine[i * 3u + 1u] = vec4<f32>(m[1], 0.0);
  affine[i * 3u + 2u] = vec4<f32>(m[2], 0.0);
}

fn diag3(d: vec3<f32>) -> mat3x3<f32> {
  return mat3x3<f32>(vec3<f32>(d.x, 0.0, 0.0), vec3<f32>(0.0, d.y, 0.0), vec3<f32>(0.0, 0.0, d.z));
}

fn outer3(a: vec3<f32>, b: vec3<f32>) -> mat3x3<f32> {
  // Column j of the result is a * b[j], which is the outer product a (x) b.
  return mat3x3<f32>(a * b.x, a * b.y, a * b.z);
}

// The quadratic B-spline weights of MPM. Returned as three vec3s: row a holds
// the weight of offset a along each axis, so the node weight is the product
// w[a].x * w[b].y * w[c].z.
struct Kernel {
  base : vec3<i32>,
  fx   : vec3<f32>,
  w0   : vec3<f32>,
  w1   : vec3<f32>,
  w2   : vec3<f32>,
};

fn kernelAt(p: vec3<f32>) -> Kernel {
  var k : Kernel;
  k.base = vec3<i32>(floor(p - vec3<f32>(0.5)));
  k.fx = p - vec3<f32>(k.base);
  let a = vec3<f32>(1.5) - k.fx;
  let b = k.fx - vec3<f32>(1.0);
  let c = k.fx - vec3<f32>(0.5);
  k.w0 = 0.5 * a * a;
  k.w1 = vec3<f32>(0.75) - b * b;
  k.w2 = 0.5 * c * c;
  return k;
}

fn kw(k: Kernel, i: i32) -> vec3<f32> {
  if (i == 0) { return k.w0; }
  if (i == 1) { return k.w1; }
  return k.w2;
}

// ------------------------------------------------------------------ 3x3 SVD
//
// Jacobi iteration on the symmetric F^T F. Six sweeps is plenty for the
// conditioning a fluid produces, and the singular values are clamped away from
// zero so the stress below cannot divide by nothing. This is the only step in
// the solver that can go non-finite; G2P checks for it afterwards.

struct SVD {
  u : mat3x3<f32>,
  s : vec3<f32>,
  v : mat3x3<f32>,
};

fn at3(m: mat3x3<f32>, r: i32, c: i32) -> f32 {
  return m[c][r];
}

fn svd3(F: mat3x3<f32>) -> SVD {
  var A = transpose(F) * F;
  var V = mat3x3<f32>(vec3<f32>(1.0, 0.0, 0.0), vec3<f32>(0.0, 1.0, 0.0), vec3<f32>(0.0, 0.0, 1.0));

  for (var sweep = 0; sweep < 6; sweep = sweep + 1) {
    for (var pq = 0; pq < 3; pq = pq + 1) {
      var p = 0; var q = 1;
      if (pq == 1) { p = 0; q = 2; }
      if (pq == 2) { p = 1; q = 2; }

      let apq = at3(A, p, q);
      if (abs(apq) > 1.0e-10) {
        let app = at3(A, p, p);
        let aqq = at3(A, q, q);
        // The standard numerically stable Jacobi angle.
        let theta = (aqq - app) / (2.0 * apq);
        let sgn = select(-1.0, 1.0, theta >= 0.0);
        let t = sgn / (abs(theta) + sqrt(theta * theta + 1.0));
        let cs = 1.0 / sqrt(t * t + 1.0);
        let sn = t * cs;

        // J is the identity with [p][p]=[q][q]=cs, [q][p]=sn, [p][q]=-sn.
        var J = mat3x3<f32>(vec3<f32>(1.0, 0.0, 0.0), vec3<f32>(0.0, 1.0, 0.0), vec3<f32>(0.0, 0.0, 1.0));
        J[p][p] = cs;  J[q][q] = cs;
        J[p][q] = sn;  J[q][p] = -sn;

        A = transpose(J) * A * J;
        V = V * J;
      }
    }
  }

  var sigma = vec3<f32>(sqrt(max(at3(A, 0, 0), 0.0)), sqrt(max(at3(A, 1, 1), 0.0)), sqrt(max(at3(A, 2, 2), 0.0)));
  sigma = clamp(sigma, vec3<f32>(0.02), vec3<f32>(30.0));

  var U = F * V * diag3(vec3<f32>(1.0) / sigma);

  // An inverted particle (a negative determinant) needs one negative singular
  // value, or U comes out a reflection and the stress pushes the wrong way.
  if (determinant(F) < 0.0) {
    // Flip the smallest, which is the one physically being inverted.
    var k = 0;
    if (sigma.y < sigma[k]) { k = 1; }
    if (sigma.z < sigma[k]) { k = 2; }
    sigma[k] = -sigma[k];
    U[k] = -U[k];
  }

  var out : SVD;
  out.u = U;
  out.s = sigma;
  out.v = V;
  return out;
}

// ------------------------------------------------------------------- hashing

fn hash1(n: u32) -> f32 {
  var x = n;
  x = x ^ (x >> 17u);  x = x * 0xed5ad4bbu;
  x = x ^ (x >> 11u);  x = x * 0xac4c1b51u;
  x = x ^ (x >> 15u);  x = x * 0x31848babu;
  x = x ^ (x >> 14u);
  return f32(x) * 2.3283064365386963e-10;
}

fn hash3(n: u32) -> vec3<f32> {
  return vec3<f32>(hash1(n * 3u + 0u), hash1(n * 3u + 1u), hash1(n * 3u + 2u));
}

// ---------------------------------------------------------------- 1. clear

@compute @workgroup_size(256)
fn clearGrid(@builtin(global_invocation_id) gid: vec3<u32>) {
  let g = gdim();
  let n = u32(g.x * g.y * g.z);
  let i = gid.x;
  if (i >= n) { return; }
  atomicStore(&gridA[i * 4u + 0u], 0);
  atomicStore(&gridA[i * 4u + 1u], 0);
  atomicStore(&gridA[i * 4u + 2u], 0);
  atomicStore(&gridA[i * 4u + 3u], 0);
  gridV[i] = vec4<f32>(0.0);
}

@compute @workgroup_size(1)
fn clearStats() {
  atomicStore(&stats[0], 0);
  atomicStore(&stats[2], 0);
  atomicStore(&stats[7], 0);
  // The reset counts, stats[1] and stats[3..6], are deliberately NOT cleared:
  // they are session totals, so a blow-up that happened once stays visible.
}

// ------------------------------------------------------------------ 2. P2G

@compute @workgroup_size(256)
fn p2g(@builtin(global_invocation_id) gid: vec3<u32>) {
  let i = gid.x;
  if (i >= u32(P.nParts)) { return; }
  let pp = pos[i];
  if (pp.w < 0.0) { return; }

  let k = kernelAt(pp.xyz);
  let F = getF(i);
  let C = getC(i);

  // --- the material: stress from the current elastic deformation.
  //
  // Fixed corotated, and deliberately not the logarithmic model the plasticity
  // below is written in. The reason is one line of algebra: MLS-MPM only ever
  // needs the product P*F^T, and for fixed corotated that product is
  //
  //     P*F^T = 2*mu*(F - R)*F^T + lam*J*(J - 1)*I
  //
  // with no division by a singular value anywhere. The logarithmic model needs
  // (2*mu*eps + lam*tr)/sigma, which multiplies by 20 as a particle is squashed
  // to a twentieth of its volume - and that gain is what blew this solver up:
  // one over-compressed particle threw enough momentum into its 27 nodes to
  // take its neighbours with it, and the cascade sustained itself at ~90
  // particles a substep with the fastest reaching 1.1e6 cells/s.
  //
  // The signs are worth reading: under compression J < 1 makes the pressure
  // term negative, which pushes the material apart, and under expansion J > 1
  // makes it positive, which pulls it back together. That second half is free
  // cohesion, and it is a large part of why slime holds a strand together.
  let sv = svd3(F);
  let R = sv.u * transpose(sv.v);
  let J = clamp(determinant(F), 0.4, 1.6);
  let press = P.lam * J * (J - 1.0);
  let PFt = (F - R) * transpose(F) * (2.0 * P.mu)
            + diag3(vec3<f32>(press, press, press));

  // The MLS-MPM affine momentum term. dx is 1, so the usual 4/dx^2 is just 4.
  let stress = PFt * (-P.dt * P.pvol * 4.0);
  let afn = stress + C * P.pmass;

  for (var a = 0; a < 3; a = a + 1) {
    for (var b = 0; b < 3; b = b + 1) {
      for (var c = 0; c < 3; c = c + 1) {
        let node = k.base + vec3<i32>(a, b, c);
        if (!inGrid(node)) { continue; }
        let weight = kw(k, a).x * kw(k, b).y * kw(k, c).z;
        if (weight <= 0.0) { continue; }
        let dpos = vec3<f32>(f32(a), f32(b), f32(c)) - k.fx;
        let contrib = weight * (vel[i].xyz * P.pmass + afn * dpos);
        let o = u32(nodeIndex(node)) * 4u;
        atomicAdd(&gridA[o + 0u], toFixed(weight * P.pmass));
        atomicAdd(&gridA[o + 1u], toFixed(contrib.x));
        atomicAdd(&gridA[o + 2u], toFixed(contrib.y));
        atomicAdd(&gridA[o + 3u], toFixed(contrib.z));
      }
    }
  }
}

// ------------------------------------------------------- 3. solve the grid

// A collider pushes the fluid out and drags it along. Returns the corrected
// velocity. 'stick' mixes between sliding along the surface and clinging.
fn collideSphere(p: vec3<f32>, v: vec3<f32>, centre: vec3<f32>, radius: f32,
                 colVel: vec3<f32>, stick: f32) -> vec3<f32> {
  let d = p - centre;
  let len = length(d);
  if (len >= radius || len < 1.0e-6) { return v; }
  let n = d / len;
  let rel = v - colVel;
  let normal = dot(rel, n);
  if (normal >= 0.0) { return v; }
  // Remove the inward component, then damp what is left by the stickiness.
  let tangent = rel - n * normal;
  return colVel + mix(tangent, vec3<f32>(0.0), stick);
}

@compute @workgroup_size(256)
fn solveGrid(@builtin(global_invocation_id) gid: vec3<u32>) {
  let g = gdim();
  let n = u32(g.x * g.y * g.z);
  let i = gid.x;
  if (i >= n) { return; }

  let m = f32(atomicLoad(&gridA[i * 4u + 0u])) * INV_FP;
  if (m <= 1.0e-9) { gridV[i] = vec4<f32>(0.0); return; }

  let px = f32(atomicLoad(&gridA[i * 4u + 1u])) * INV_FP;
  let py = f32(atomicLoad(&gridA[i * 4u + 2u])) * INV_FP;
  let pz = f32(atomicLoad(&gridA[i * 4u + 3u])) * INV_FP;
  var v = vec3<f32>(px, py, pz) / m;

  v.y = v.y - P.dt * P.gravity;

  // Where this node sits, in cells.
  let c = vec3<i32>(i32(i) % g.x, (i32(i) / g.x) % g.y, i32(i) / (g.x * g.y));
  let p = vec3<f32>(c);

  // --- walls. Two cells of margin, because the kernel reaches that far.
  let bw = 2;
  let stickT = P.wallStick;

  if (c.x < bw)         { v.x = max(v.x, 0.0); v = mix(v, vec3<f32>(v.x, 0.0, 0.0), stickT); }
  if (c.x >= g.x - bw)  { v.x = min(v.x, 0.0); v = mix(v, vec3<f32>(v.x, 0.0, 0.0), stickT); }
  if (c.z < bw)         { v.z = max(v.z, 0.0); v = mix(v, vec3<f32>(0.0, 0.0, v.z), stickT); }
  if (c.z >= g.z - bw)  { v.z = min(v.z, 0.0); v = mix(v, vec3<f32>(0.0, 0.0, v.z), stickT); }
  if (c.y >= g.y - bw)  { v.y = min(v.y, 0.0); }

  // The floor is where the stickiness is most visible, so it gets its own,
  // stronger grip: slime should drag to a halt on it, not skate.
  if (c.y < bw) {
    v.y = max(v.y, 0.0);
    let floorGrip = clamp(stickT * 1.4, 0.0, 1.0);
    v = mix(v, vec3<f32>(0.0, v.y, 0.0), floorGrip);
  }

  // --- the obstacle and the mouse.
  if (P.obstacle.w > 0.0) {
    v = collideSphere(p, v, P.obstacle.xyz, P.obstacle.w, vec3<f32>(0.0), clamp(stickT, 0.0, 1.0));
  }
  if (P.mouse.w > 0.0) {
    let d = p - P.mouse.xyz;
    let len = length(d);
    if (len < P.mouse.w) {
      // Inside the hand: carry the fluid with it. This is what lets a strand be
      // pulled out of a pool, so it drags rather than only pushing.
      let grab = P.mouseVel.w * (1.0 - len / P.mouse.w);
      v = mix(v, P.mouseVel.xyz, clamp(grab, 0.0, 1.0));
      if (len > 1.0e-6) {
        let nrm = d / len;
        let into = dot(v - P.mouseVel.xyz, nrm);
        if (into < 0.0) { v = v - nrm * into; }
      }
    }
  }

  // --- the hard CFL cap, and the reason the solver cannot run away.
  //
  // A particle may not travel more than most of a cell in one substep: beyond
  // that it leaves the support its own kernel was built for and the transfer
  // stops meaning anything. Capping here, on the grid, bounds every particle
  // that reads this node, so a single bad particle can no longer throw its
  // neighbours across the domain. It is one line and it makes a blow-up
  // impossible rather than merely unlikely.
  let vmax = 0.9 / max(P.dt, 1.0e-6);
  let sp = length(v);
  if (sp > vmax) { v = v * (vmax / sp); }

  gridV[i] = vec4<f32>(v, m);
  atomicAdd(&stats[0], i32(clamp(m * STAT_FP, -2.0e9, 2.0e9)));
}

// ------------------------------------------------------------------ 4. G2P

@compute @workgroup_size(256)
fn g2p(@builtin(global_invocation_id) gid: vec3<u32>) {
  let i = gid.x;
  if (i >= u32(P.nParts)) { return; }
  var pp = pos[i];
  if (pp.w < 0.0) { return; }

  let k = kernelAt(pp.xyz);
  var newV = vec3<f32>(0.0);
  var newC = mat3x3<f32>(vec3<f32>(0.0), vec3<f32>(0.0), vec3<f32>(0.0));

  for (var a = 0; a < 3; a = a + 1) {
    for (var b = 0; b < 3; b = b + 1) {
      for (var c = 0; c < 3; c = c + 1) {
        let node = k.base + vec3<i32>(a, b, c);
        if (!inGrid(node)) { continue; }
        let weight = kw(k, a).x * kw(k, b).y * kw(k, c).z;
        if (weight <= 0.0) { continue; }
        let dpos = vec3<f32>(f32(a), f32(b), f32(c)) - k.fx;
        let gv = gridV[u32(nodeIndex(node))].xyz;
        newV = newV + weight * gv;
        // APIC: the affine velocity field, which is what stops a particle
        // losing the rotation of the flow it sits in.
        newC = newC + outer3(gv, dpos) * (4.0 * weight);
      }
    }
  }

  // --- advect
  var newPos = pp.xyz + P.dt * newV;
  let g = gdim();
  newPos = clamp(newPos, vec3<f32>(2.0), vec3<f32>(g) - vec3<f32>(3.0));

  // --- the material: elastic update, then flow.
  var F = (mat3x3<f32>(vec3<f32>(1.0, 0.0, 0.0), vec3<f32>(0.0, 1.0, 0.0), vec3<f32>(0.0, 0.0, 1.0))
           + newC * P.dt) * getF(i);

  let sv = svd3(F);
  // Bounded well inside anything physical: a particle elastically squashed past
  // 40% or stretched past 60% is a numerical artefact, not a material, and
  // letting it keep that state is how one bad step becomes a cascade.
  var S = clamp(sv.s, vec3<f32>(0.6), vec3<f32>(1.6));
  var eps = log(S);
  let tr = clamp(eps.x + eps.y + eps.z, -0.5, 0.4);
  var dev = eps - vec3<f32>(tr / 3.0);
  let nrm = length(dev);

  // The deviatoric stress the current shear is carrying.
  let s = 2.0 * P.mu * nrm;

  // How far to project back toward the yield surface. This one expression is
  // the material:
  //   a tiny mu              -> the shear memory is wiped every step: a fluid.
  //   s below the yield      -> nothing is projected: it holds its shape.
  //   s above it             -> it gives, and visc/dt decides how far, so a
  //                            slow push flows and a fast one resists.
  var dgamma = 0.0;
  if (P.mu < 1.0e-3) {
    dgamma = nrm;
  } else if (s > P.yieldS) {
    dgamma = min(nrm, (s - P.yieldS) / max(2.0 * P.mu + P.visc / max(P.dt, 1.0e-6), 1.0e-6));
  }

  var plastic = 0.0;
  if (dgamma > 0.0 && nrm > 1.0e-9) {
    dev = dev - dev * (dgamma / nrm);
    plastic = dgamma;
  }

  // F is rebuilt from the projected strain every step, not only when something
  // yielded. Two things fall out of that: the projection is written back, so
  // the flow is permanent - which is the whole difference between kissel and
  // jelly - and the clamp above becomes a real bound on the stored state rather
  // than a bound on this step's stress only. With nothing out of range and
  // nothing yielding it is the identity, so a jelly keeps its spring.
  eps = dev + vec3<f32>(tr / 3.0);
  S = exp(eps);
  F = sv.u * diag3(S) * transpose(sv.v);

  // --- the guard. A NaN here would reach every node this particle touches on
  // the next P2G and take the whole grid with it, so a particle that has gone
  // bad is reset to a clean state and counted. A blow-up then shows as a number
  // on the panel instead of a frozen screen.
  let badPos = !all(newPos == newPos);
  let badVel = !all(newV == newV);
  let badF = !all(F[0] == F[0]) || !all(F[1] == F[1]) || !all(F[2] == F[2]);
  let tooFast = any(abs(newV) > vec3<f32>(1.0e5));
  let bad = badPos || badVel || badF || tooFast;

  atomicMax(&stats[7], i32(clamp(length(newV) * 16.0, 0.0, 2.0e9)));

  if (bad) {
    atomicAdd(&stats[1], 1);
    if (badPos) { atomicAdd(&stats[3], 1); }
    if (badVel) { atomicAdd(&stats[4], 1); }
    if (badF)   { atomicAdd(&stats[5], 1); }
    if (tooFast){ atomicAdd(&stats[6], 1); }
    pos[i] = vec4<f32>(clamp(pp.xyz, vec3<f32>(2.0), vec3<f32>(g) - vec3<f32>(3.0)), pp.w);
    vel[i] = vec4<f32>(0.0);
    setF(i, mat3x3<f32>(vec3<f32>(1.0, 0.0, 0.0), vec3<f32>(0.0, 1.0, 0.0), vec3<f32>(0.0, 0.0, 1.0)));
    setC(i, mat3x3<f32>(vec3<f32>(0.0), vec3<f32>(0.0), vec3<f32>(0.0)));
    return;
  }

  pos[i] = vec4<f32>(newPos, pp.w + P.dt);
  vel[i] = vec4<f32>(newV, plastic / max(P.dt, 1.0e-6));
  setF(i, F);
  setC(i, newC);
  extra[i] = extra[i] * 0.98 + plastic;
  atomicAdd(&stats[2], 1);
}

// ------------------------------------------------------------------- seeding

@compute @workgroup_size(64)
fn seed(@builtin(global_invocation_id) gid: vec3<u32>) {
  let j = gid.x;
  if (j >= u32(P.seedCount)) { return; }
  // The host splits a run that would cross the end of the ring, so this never
  // needs to wrap.
  let i = u32(P.seedBase) + j;
  let salt = u32(P.frame) * 7919u + u32(P.seedBase) * 131u + j * 31u + 17u;
  let r = hash3(salt);

  var centre = P.emitPos.xyz;
  var radius = P.emitPos.w;
  var v0 = P.emitDir.xyz * P.emitDir.w;

  // --- a jittered lattice, not random points.
  //
  // Random placement looks the same and is not: it leaves Poisson noise in the
  // density, and MPM cannot repair that. A particle carries its own volume
  // through its deformation gradient, which starts at 1 for everybody, so a
  // cell that happens to be seeded with three times its share of particles has
  // three times the mass and no pressure at all telling it to spread out. The
  // material is then locally three times as heavy and a third as stiff, for
  // good. Measured on the random version: 26 particles in a cell against the 8
  // the solver assumes.
  //
  // One particle per lattice site with a small jitter gives an even density;
  // sites outside the shape are marked dead and skipped by everything else.
  let n = max(u32(P.latN), 1u);
  let ix = j % n;
  let iy = (j / n) % n;
  let iz = j / (n * n);
  let step = P.latStep;
  let jit = (hash3(salt * 17u + 3u) - vec3<f32>(0.5)) * step * 0.55;

  var p = vec3<f32>(0.0);
  var alive = true;

  if (P.seedKind > 0.5) {
    // A stream: a disc across the nozzle, latM sites deep along the flow, so a
    // held pour arrives as a column and not as pulses.
    let m = max(u32(P.latM), 1u);
    let dx = (f32(j % n) + 0.5) * step - radius;
    let dz = (f32((j / n) % n) + 0.5) * step - radius;
    // Spread the layers over exactly the distance the stream covers in one
    // frame, not over the lattice spacing. Those two are not the same number,
    // and the difference between them is what printed visible rings down a
    // falling column: every frame laid its slab a little clear of the last.
    let travel = P.emitDir.w * P.dt;
    let along = (f32((j / (n * n)) % m) + hash1(salt * 23u + 7u)) * travel / f32(m);
    alive = (dx * dx + dz * dz) <= radius * radius;
    let ax = select(vec3<f32>(1.0, 0.0, 0.0), vec3<f32>(0.0, 0.0, 1.0), abs(P.emitDir.y) < 0.9);
    let t1 = normalize(cross(P.emitDir.xyz, ax));
    let t2 = normalize(cross(P.emitDir.xyz, t1));
    p = centre + t1 * dx + t2 * dz + P.emitDir.xyz * along + jit;
    v0 = v0 * (0.97 + 0.06 * hash1(salt * 11u));
  } else {
    let local = (vec3<f32>(f32(ix), f32(iy), f32(iz)) + vec3<f32>(0.5)) * step - vec3<f32>(radius);
    alive = dot(local, local) <= radius * radius;
    p = centre + local + jit;
  }

  if (!alive) {
    pos[i] = vec4<f32>(0.0, 0.0, 0.0, -1.0);
    return;
  }

  let g = gdim();
  pos[i] = vec4<f32>(clamp(p, vec3<f32>(2.0), vec3<f32>(g) - vec3<f32>(3.0)), 0.0);
  vel[i] = vec4<f32>(v0 + (r - vec3<f32>(0.5)) * P.jitter, 0.0);
  setF(i, mat3x3<f32>(vec3<f32>(1.0, 0.0, 0.0), vec3<f32>(0.0, 1.0, 0.0), vec3<f32>(0.0, 0.0, 1.0)));
  setC(i, mat3x3<f32>(vec3<f32>(0.0), vec3<f32>(0.0), vec3<f32>(0.0)));
  extra[i] = 0.0;
}

@compute @workgroup_size(256)
fn killAll(@builtin(global_invocation_id) gid: vec3<u32>) {
  let i = gid.x;
  if (i >= u32(P.nParts)) { return; }
  pos[i] = vec4<f32>(0.0, 0.0, 0.0, -1.0);
  vel[i] = vec4<f32>(0.0);
  extra[i] = 0.0;
  setF(i, mat3x3<f32>(vec3<f32>(1.0, 0.0, 0.0), vec3<f32>(0.0, 1.0, 0.0), vec3<f32>(0.0, 0.0, 1.0)));
  setC(i, mat3x3<f32>(vec3<f32>(0.0), vec3<f32>(0.0), vec3<f32>(0.0)));
}
`;
