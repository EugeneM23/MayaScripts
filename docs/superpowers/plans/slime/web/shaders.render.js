// Screen-space fluid rendering, in WGSL.
//
// A cloud of points says nothing about whether a material reads as kissel, so
// the surface is reconstructed from the particles in screen space (van der Laan
// 2009): sphere depth, a narrow-range filter that smooths the surface without
// bleeding across its silhouette, normals from the filtered depth, and then
// Fresnel plus Beer-Lambert absorption through an accumulated thickness, so a
// thin film is pale and a deep pool is saturated.
//
// The passes, in order: shadow (top-down, so the puddle sits on the floor
// instead of floating), background (a raytraced floor and obstacle), depth,
// thickness, filter x2, composite.

const RENDER_WGSL = /* wgsl */ `

struct Cam {
  view     : mat4x4<f32>,
  proj     : mat4x4<f32>,
  invView  : mat4x4<f32>,
  eye      : vec4<f32>,
  res      : vec4<f32>,   // w, h, 1/w, 1/h
  lens     : vec4<f32>,   // tanHalfFovX, tanHalfFovY, near, far
  misc     : vec4<f32>,   // particle radius (cells), grid span, time, mode
  obstacle : vec4<f32>,   // xyz centre, w radius  (cells)
  tint     : vec4<f32>,   // slime colour, w absorption
  look     : vec4<f32>,   // roughness, refract strength, shadow strength, opacity
  capN     : vec4<f32>,   // how many bone capsules are live
  caps     : array<vec4<f32>, 72>,   // (a.xyz, radius), (b.xyz, -), (vel.xyz, -)
};

@group(0) @binding(0) var<uniform> C : Cam;
@group(0) @binding(1) var<storage, read> pos : array<vec4<f32>>;
@group(0) @binding(2) var<storage, read> vel : array<vec4<f32>>;

// ------------------------------------------------------------- the world
//
// Everything is in cell units, one cell is 1 cm, and the floor is at y = 2
// (the solver keeps two cells of margin, so that is where the fluid can
// actually rest).

const FLOOR : f32 = 2.0;

fn skyColour(d: vec3<f32>) -> vec3<f32> {
  let t = clamp(d.y * 0.5 + 0.5, 0.0, 1.0);
  let low = vec3<f32>(0.075, 0.080, 0.092);
  let high = vec3<f32>(0.26, 0.30, 0.37);
  // A warm band near the horizon, so there is something for a wet surface to
  // catch: a fluid reads as wet mostly through what it reflects, and a flat
  // background gives it nothing to reflect.
  let horizon = exp(-abs(d.y) * 7.0) * 0.10;
  return mix(low, high, t * t) + vec3<f32>(horizon * 1.1, horizon * 0.85, horizon * 0.6);
}

// A grid every 10 cells, a heavier line every 50, so the scale is readable.
//
// The line width is worked out from the pixel footprint handed in rather than
// from dpdx: WGSL only allows a derivative in uniform control flow, and this is
// called from inside the "did the ray hit the floor" branch. Analytic is also
// better behaved at a grazing angle, where a screen-space derivative of a
// fract() blows up.
fn floorColour(p: vec3<f32>, foot: f32) -> vec3<f32> {
  let f1 = max(foot / 10.0, 1.0e-4);
  let g = abs(fract(p.xz / 10.0 + vec2<f32>(0.5)) - vec2<f32>(0.5)) / f1;
  let line = 1.0 - min(min(g.x, g.y), 1.0);
  let f2 = max(foot / 50.0, 1.0e-4);
  let g2 = abs(fract(p.xz / 50.0 + vec2<f32>(0.5)) - vec2<f32>(0.5)) / f2;
  let line2 = 1.0 - min(min(g2.x, g2.y), 1.0);
  var base = vec3<f32>(0.185, 0.190, 0.205);
  base = mix(base, vec3<f32>(0.27, 0.278, 0.30), line * 0.8);
  base = mix(base, vec3<f32>(0.40, 0.385, 0.36), line2 * 0.9);
  return base;
}

// The world size of one pixel on the floor, at distance t along a ray whose
// vertical component is rdy: the pixel's angular size times the distance,
// stretched by how obliquely the ray meets the ground.
fn floorFootprint(t: f32, rdy: f32) -> f32 {
  let pix = t * 2.0 * C.lens.y * C.res.w;
  return pix / max(abs(rdy), 0.06);
}

// ------------------------------------------------------------ fullscreen VS

struct FSOut {
  @builtin(position) pos : vec4<f32>,
  @location(0) uv : vec2<f32>,
};

@vertex
fn fsVert(@builtin(vertex_index) vi: u32) -> FSOut {
  // One triangle covering the viewport.
  var p = array<vec2<f32>, 3>(vec2<f32>(-1.0, -1.0), vec2<f32>(3.0, -1.0), vec2<f32>(-1.0, 3.0));
  var o : FSOut;
  o.pos = vec4<f32>(p[vi], 0.0, 1.0);
  o.uv = vec2<f32>(p[vi].x * 0.5 + 0.5, 0.5 - p[vi].y * 0.5);
  return o;
}

fn rayThrough(uv: vec2<f32>) -> vec3<f32> {
  let ndc = vec2<f32>(uv.x * 2.0 - 1.0, 1.0 - uv.y * 2.0);
  let dView = vec3<f32>(ndc.x * C.lens.x, ndc.y * C.lens.y, -1.0);
  return normalize((C.invView * vec4<f32>(dView, 0.0)).xyz);
}

// --------------------------------------------------------- 1. the shadow
//
// Each particle is a disc on the floor plane, additively accumulated in a
// top-down orthographic texture, weaker the higher the particle sits. The
// background pass reads it. It is not a real shadow, it is contact: without it
// a puddle looks like it is hovering.

struct ShadowOut {
  @builtin(position) pos : vec4<f32>,
  @location(0) local : vec2<f32>,
  @location(1) strength : f32,
};

@vertex
fn shadowVert(@builtin(vertex_index) vi: u32, @builtin(instance_index) ii: u32) -> ShadowOut {
  var corners = array<vec2<f32>, 6>(
    vec2<f32>(-1.0, -1.0), vec2<f32>(1.0, -1.0), vec2<f32>(-1.0, 1.0),
    vec2<f32>(-1.0, 1.0), vec2<f32>(1.0, -1.0), vec2<f32>(1.0, 1.0));
  let corner = corners[vi];
  let p = pos[ii];
  var o : ShadowOut;
  if (p.w < 0.0) {
    o.pos = vec4<f32>(0.0, 0.0, 2.0, 1.0);   // behind the far plane: clipped
    o.local = corner;
    o.strength = 0.0;
    return o;
  }
  let span = C.misc.y;
  let r = C.misc.x * 2.2;
  let xz = (p.xz + corner * r) / span * 2.0 - vec2<f32>(1.0);
  o.pos = vec4<f32>(xz.x, -xz.y, 0.0, 1.0);
  o.local = corner;
  o.strength = exp(-max(p.y - FLOOR, 0.0) * 0.06);
  return o;
}

@fragment
fn shadowFrag(i: ShadowOut) -> @location(0) vec4<f32> {
  let d2 = dot(i.local, i.local);
  if (d2 > 1.0) { discard; }
  let fall = 1.0 - d2;
  return vec4<f32>(fall * fall * i.strength * 0.06, 0.0, 0.0, 0.0);
}

// ----------------------------------------------------- 2. the background

@group(1) @binding(0) var samp : sampler;
@group(1) @binding(1) var shadowTex : texture_2d<f32>;

struct BgOut {
  @location(0) colour : vec4<f32>,
  @location(1) depth  : vec4<f32>,
};

// Where a ray meets a capsule, or -1. The usual quadratic against the infinite
// cylinder, with the two end caps tried as spheres, because a bone drawn as a
// cylinder with flat ends reads as a robot.
fn capsuleHit(ro: vec3<f32>, rd: vec3<f32>, a: vec3<f32>, b: vec3<f32>,
              r: f32, maxT: f32) -> f32 {
  let ba = b - a;
  let oa = ro - a;
  let baba = dot(ba, ba);
  var best = -1.0;
  if (baba > 1.0e-8) {
    let bard = dot(ba, rd);
    let baoa = dot(ba, oa);
    let k2 = baba - bard * bard;
    let k1 = baba * dot(oa, rd) - baoa * bard;
    let k0 = baba * dot(oa, oa) - baoa * baoa - r * r * baba;
    let h = k1 * k1 - k2 * k0;
    if (h >= 0.0 && abs(k2) > 1.0e-8) {
      let t = (-k1 - sqrt(h)) / k2;
      let y = baoa + t * bard;
      if (t > 0.0 && t < maxT && y > 0.0 && y < baba) { best = t; }
    }
  }
  // the caps
  for (var e = 0; e < 2; e = e + 1) {
    let c = select(a, b, e == 1);
    let oc = ro - c;
    let bq = dot(oc, rd);
    let cq = dot(oc, oc) - r * r;
    let hq = bq * bq - cq;
    if (hq > 0.0) {
      let t = -bq - sqrt(hq);
      if (t > 0.0 && t < maxT && (best < 0.0 || t < best)) { best = t; }
    }
  }
  return best;
}

@fragment
fn bgFrag(i: FSOut) -> BgOut {
  let ro = C.eye.xyz;
  let rd = rayThrough(i.uv);
  var col = skyColour(rd);
  var dist = C.lens.w;

  // the obstacle sphere
  if (C.obstacle.w > 0.0) {
    let oc = ro - C.obstacle.xyz;
    let b = dot(oc, rd);
    let c = dot(oc, oc) - C.obstacle.w * C.obstacle.w;
    let h = b * b - c;
    if (h > 0.0) {
      let t = -b - sqrt(h);
      if (t > 0.0 && t < dist) {
        dist = t;
        let p = ro + rd * t;
        let n = normalize(p - C.obstacle.xyz);
        let l = normalize(vec3<f32>(0.4, 0.8, 0.35));
        let dif = max(dot(n, l), 0.0);
        let rim = pow(1.0 - max(dot(n, -rd), 0.0), 3.0);
        col = vec3<f32>(0.30, 0.31, 0.33) * (0.18 + 0.8 * dif) + vec3<f32>(0.1) * rim;
      }
    }
  }

  // the character, a capsule a bone
  let nc = u32(max(C.capN.x, 0.0));
  for (var k = 0u; k < nc; k = k + 1u) {
    let a = C.caps[k * 3u];
    let b = C.caps[k * 3u + 1u];
    if (a.w <= 0.0) { continue; }
    let t = capsuleHit(ro, rd, a.xyz, b.xyz, a.w, dist);
    if (t > 0.0) {
      dist = t;
      let p = ro + rd * t;
      let ab = b.xyz - a.xyz;
      let l2 = max(dot(ab, ab), 1.0e-8);
      let h = clamp(dot(p - a.xyz, ab) / l2, 0.0, 1.0);
      let n = normalize(p - (a.xyz + ab * h));
      let l = normalize(vec3<f32>(0.4, 0.8, 0.35));
      let dif = max(dot(n, l), 0.0);
      let rim = pow(1.0 - max(dot(n, -rd), 0.0), 3.0);
      col = vec3<f32>(0.26, 0.28, 0.32) * (0.20 + 0.75 * dif) + vec3<f32>(0.12) * rim;
    }
  }

  // the floor
  if (rd.y < -1.0e-4) {
    let t = (FLOOR - ro.y) / rd.y;
    if (t > 0.0 && t < dist) {
      dist = t;
      let p = ro + rd * t;
      var fc = floorColour(p, floorFootprint(t, rd.y));
      // contact darkening from the shadow texture
      let span = C.misc.y;
      let suv = p.xz / span;
      if (all(suv > vec2<f32>(0.0)) && all(suv < vec2<f32>(1.0))) {
        let sh = textureSampleLevel(shadowTex, samp, suv, 0.0).r;
        fc = fc * (1.0 - clamp(sh, 0.0, 1.0) * C.look.z);
      }
      // fade to the sky at the horizon so the grid does not alias away
      let fade = clamp(t / (C.misc.y * 2.5), 0.0, 1.0);
      fc = mix(fc, skyColour(rd), fade * fade);
      col = fc;
    }
  }

  var o : BgOut;
  o.colour = vec4<f32>(col, 1.0);
  o.depth = vec4<f32>(dist, 0.0, 0.0, 0.0);
  return o;
}

// ------------------------------------------------- 3. the particle depth

struct SphereOut {
  @builtin(position) pos : vec4<f32>,
  @location(0) local  : vec2<f32>,
  @location(1) centre : vec3<f32>,   // view space
  @location(2) speed  : f32,
};

@vertex
fn sphereVert(@builtin(vertex_index) vi: u32, @builtin(instance_index) ii: u32) -> SphereOut {
  var corners = array<vec2<f32>, 6>(
    vec2<f32>(-1.0, -1.0), vec2<f32>(1.0, -1.0), vec2<f32>(-1.0, 1.0),
    vec2<f32>(-1.0, 1.0), vec2<f32>(1.0, -1.0), vec2<f32>(1.0, 1.0));
  let corner = corners[vi];
  let p = pos[ii];
  var o : SphereOut;
  if (p.w < 0.0) {
    o.pos = vec4<f32>(0.0, 0.0, 2.0, 1.0);
    o.local = corner;
    o.centre = vec3<f32>(0.0);
    o.speed = 0.0;
    return o;
  }
  let r = C.misc.x;
  let vc = (C.view * vec4<f32>(p.xyz, 1.0)).xyz;
  let vp = vc + vec3<f32>(corner * r, 0.0);
  o.pos = C.proj * vec4<f32>(vp, 1.0);
  o.local = corner;
  o.centre = vc;
  o.speed = length(vel[ii].xyz);
  return o;
}

struct DepthOut {
  @location(0) lin : vec4<f32>,
  @builtin(frag_depth) z : f32,
};

@fragment
fn depthFrag(i: SphereOut) -> DepthOut {
  let d2 = dot(i.local, i.local);
  if (d2 > 1.0) { discard; }
  let r = C.misc.x;
  // The point on the front of the sphere, in view space. The camera looks down
  // -z, so the near surface is at centre.z + r*nz.
  let nz = sqrt(1.0 - d2);
  let vp = i.centre + vec3<f32>(i.local * r, nz * r);
  let clip = C.proj * vec4<f32>(vp, 1.0);
  var o : DepthOut;
  o.z = clip.z / clip.w;
  o.lin = vec4<f32>(-vp.z, 0.0, 0.0, 0.0);
  return o;
}

// -------------------------------------------------- 4. the thickness pass
//
// Every particle, including the occluded ones, so there is no depth test here.
// Rendered at half resolution: it is a low-frequency quantity and it is the
// most expensive pass otherwise.

@fragment
fn thickFrag(i: SphereOut) -> @location(0) vec4<f32> {
  let d2 = dot(i.local, i.local);
  if (d2 > 1.0) { discard; }
  let fall = 1.0 - d2;
  return vec4<f32>(fall * fall * C.misc.x * 0.6, 0.0, 0.0, 0.0);
}

// ------------------------------------------------------- 5. the filter
//
// Narrow range: a sample further from the centre depth than the window is left
// out instead of being averaged in, so the surface smooths but the silhouette
// stays an edge. A plain blur rounds the fluid into the background.

@group(1) @binding(2) var srcTex : texture_2d<f32>;
@group(2) @binding(0) var<uniform> axis : vec4<f32>;   // xy direction in pixels, z radius, w window

@fragment
fn filterFrag(i: FSOut) -> @location(0) vec4<f32> {
  let centre = textureSampleLevel(srcTex, samp, i.uv, 0.0).r;
  if (centre >= C.lens.w) { return vec4<f32>(centre, 0.0, 0.0, 0.0); }
  let radius = i32(axis.z);
  let window = axis.w;
  let step = axis.xy * C.res.zw;
  var sum = centre;
  var wsum = 1.0;
  for (var k = 1; k <= radius; k = k + 1) {
    let fk = f32(k);
    let g = exp(-fk * fk / (0.5 * axis.z * axis.z + 1.0e-4));
    for (var s = 0; s < 2; s = s + 1) {
      let off = select(step * fk, -step * fk, s == 1);
      let d = textureSampleLevel(srcTex, samp, i.uv + off, 0.0).r;
      if (d < C.lens.w && abs(d - centre) < window) {
        sum = sum + d * g;
        wsum = wsum + g;
      }
    }
  }
  return vec4<f32>(sum / wsum, 0.0, 0.0, 0.0);
}

// ---------------------------------------------------------- 6. composite

@group(1) @binding(3) var bgTex : texture_2d<f32>;
@group(1) @binding(4) var bgDepthTex : texture_2d<f32>;
@group(1) @binding(5) var fluidTex : texture_2d<f32>;
@group(1) @binding(6) var thickTex : texture_2d<f32>;

fn viewFromUV(uv: vec2<f32>, lin: f32) -> vec3<f32> {
  let ndc = vec2<f32>(uv.x * 2.0 - 1.0, 1.0 - uv.y * 2.0);
  return vec3<f32>(ndc.x * C.lens.x * lin, ndc.y * C.lens.y * lin, -lin);
}

@fragment
fn compositeFrag(i: FSOut) -> @location(0) vec4<f32> {
  let mode = i32(C.misc.w);
  let bg = textureSampleLevel(bgTex, samp, i.uv, 0.0).rgb;
  let bgDepth = textureSampleLevel(bgDepthTex, samp, i.uv, 0.0).r;
  let d = textureSampleLevel(fluidTex, samp, i.uv, 0.0).r;
  let thick = textureSampleLevel(thickTex, samp, i.uv, 0.0).r;

  if (mode == 1) {
    // the points view draws over a plain background
    return vec4<f32>(bg, 1.0);
  }
  if (mode == 2) {
    // depth
    if (d >= C.lens.w) { return vec4<f32>(0.0, 0.0, 0.0, 1.0); }
    let t = clamp((d - C.lens.z) / (C.misc.y * 2.0), 0.0, 1.0);
    return vec4<f32>(vec3<f32>(1.0 - t), 1.0);
  }
  if (mode == 4) {
    return vec4<f32>(vec3<f32>(clamp(thick * 0.25, 0.0, 1.0)), 1.0);
  }

  // No fluid in front of the background: the background, as it is.
  if (d >= C.lens.w || d > bgDepth) { return vec4<f32>(bg, 1.0); }

  // --- the surface, from the filtered depth.
  let vp = viewFromUV(i.uv, d);
  let e = C.res.zw;
  let dx1 = textureSampleLevel(fluidTex, samp, i.uv + vec2<f32>(e.x, 0.0), 0.0).r;
  let dx0 = textureSampleLevel(fluidTex, samp, i.uv - vec2<f32>(e.x, 0.0), 0.0).r;
  let dy1 = textureSampleLevel(fluidTex, samp, i.uv + vec2<f32>(0.0, e.y), 0.0).r;
  let dy0 = textureSampleLevel(fluidTex, samp, i.uv - vec2<f32>(0.0, e.y), 0.0).r;

  // One-sided where a neighbour is background, so the silhouette does not get a
  // normal pointing off into nothing.
  var ddx : vec3<f32>;
  if (dx1 < C.lens.w && abs(dx1 - d) < abs(dx0 - d)) {
    ddx = viewFromUV(i.uv + vec2<f32>(e.x, 0.0), dx1) - vp;
  } else if (dx0 < C.lens.w) {
    ddx = vp - viewFromUV(i.uv - vec2<f32>(e.x, 0.0), dx0);
  } else {
    ddx = vec3<f32>(1.0, 0.0, 0.0);
  }
  var ddy : vec3<f32>;
  if (dy1 < C.lens.w && abs(dy1 - d) < abs(dy0 - d)) {
    ddy = viewFromUV(i.uv + vec2<f32>(0.0, e.y), dy1) - vp;
  } else if (dy0 < C.lens.w) {
    ddy = vp - viewFromUV(i.uv - vec2<f32>(0.0, e.y), dy0);
  } else {
    ddy = vec3<f32>(0.0, 1.0, 0.0);
  }

  var nView = normalize(cross(ddx, ddy));
  if (nView.z < 0.0) { nView = -nView; }
  let nWorld = normalize((C.invView * vec4<f32>(nView, 0.0)).xyz);

  if (mode == 3) {
    return vec4<f32>(nWorld * 0.5 + vec3<f32>(0.5), 1.0);
  }

  let wp = (C.invView * vec4<f32>(vp, 1.0)).xyz;
  let viewDir = normalize(C.eye.xyz - wp);
  let lightDir = normalize(vec3<f32>(0.45, 0.78, 0.4));

  // --- refraction: the background, pushed aside by the surface. Scaled by
  // 1/depth so a far surface bends less, which is what stops the distortion
  // swimming when the camera moves.
  let bend = C.look.y * 0.06 / max(d * 0.02, 0.4);
  let ruv = clamp(i.uv + nView.xy * bend, vec2<f32>(0.001), vec2<f32>(0.999));
  var behind = textureSampleLevel(bgTex, samp, ruv, 0.0).rgb;
  // Do not drag a sample from in front of the surface into it.
  if (textureSampleLevel(bgDepthTex, samp, ruv, 0.0).r < d) {
    behind = bg;
  }

  // --- Beer-Lambert through the accumulated thickness.
  let depthThrough = max(thick, 0.35);
  let absorb = C.tint.w;
  let transmit = exp(-absorb * depthThrough * (vec3<f32>(1.0) - C.tint.rgb) * 3.0);
  var col = behind * transmit + C.tint.rgb * (vec3<f32>(1.0) - transmit) * 0.75;

  // a little scattered light from the body of it, so a thick pool is not flat
  let wrap = clamp((dot(nWorld, lightDir) + 0.35) / 1.35, 0.0, 1.0);
  col = col + C.tint.rgb * wrap * 0.22 * clamp(depthThrough * 0.2, 0.08, 0.5);

  // --- specular and Fresnel.
  let h = normalize(lightDir + viewDir);
  let rough = max(C.look.x, 0.02);
  let specPow = 2.0 / (rough * rough) - 2.0;
  let spec = pow(max(dot(nWorld, h), 0.0), max(specPow, 1.0)) * (0.4 / (rough + 0.1));
  let f0 = 0.035;
  let fres = f0 + (1.0 - f0) * pow(1.0 - clamp(dot(nWorld, viewDir), 0.0, 1.0), 5.0);
  let reflDir = reflect(-viewDir, nWorld);
  var refl = skyColour(reflDir) * 3.0;
  // the floor, reflected
  if (reflDir.y < -0.01) {
    let t = (FLOOR - wp.y) / reflDir.y;
    if (t > 0.0) { refl = floorColour(wp + reflDir * t, floorFootprint(d + t, reflDir.y)) * 1.2; }
  }

  col = mix(col, refl, clamp(fres * 1.6, 0.0, 0.8));
  col = col + vec3<f32>(spec) * clamp(fres * 8.0, 0.2, 1.0);

  // The silhouette keeps a sliver of the background, so the edge is not a hard
  // cut-out: a thin rim of slime is translucent.
  let edge = clamp(thick * 1.6, 0.0, 1.0);
  col = mix(bg, col, clamp(edge * C.look.w + 0.25, 0.0, 1.0));

  return vec4<f32>(col, 1.0);
}

// --------------------------------------------------- the points debug view

struct PointOut {
  @builtin(position) pos : vec4<f32>,
  @location(0) local : vec2<f32>,
  @location(1) tintv : vec3<f32>,
};

@vertex
fn pointVert(@builtin(vertex_index) vi: u32, @builtin(instance_index) ii: u32) -> PointOut {
  var corners = array<vec2<f32>, 6>(
    vec2<f32>(-1.0, -1.0), vec2<f32>(1.0, -1.0), vec2<f32>(-1.0, 1.0),
    vec2<f32>(-1.0, 1.0), vec2<f32>(1.0, -1.0), vec2<f32>(1.0, 1.0));
  let corner = corners[vi];
  let p = pos[ii];
  var o : PointOut;
  if (p.w < 0.0) {
    o.pos = vec4<f32>(0.0, 0.0, 2.0, 1.0);
    o.local = corner;
    o.tintv = vec3<f32>(0.0);
    return o;
  }
  let r = C.misc.x * 0.55;
  let vc = (C.view * vec4<f32>(p.xyz, 1.0)).xyz;
  o.pos = C.proj * vec4<f32>(vc + vec3<f32>(corner * r, 0.0), 1.0);
  o.local = corner;
  // Colour by how fast the material is flowing plastically: blue holds its
  // shape, orange is giving way. This is the view that shows the yield point
  // doing its job.
  let flow = clamp(vel[ii].w * 0.08, 0.0, 1.0);
  o.tintv = mix(vec3<f32>(0.35, 0.6, 1.0), vec3<f32>(1.0, 0.55, 0.15), flow);
  return o;
}

@fragment
fn pointFrag(i: PointOut) -> @location(0) vec4<f32> {
  let d2 = dot(i.local, i.local);
  if (d2 > 1.0) { discard; }
  return vec4<f32>(i.tintv * (1.2 - d2 * 0.5), 1.0);
}
`;
