// A character in the sandbox: a skeleton read out of an FBX by Maya, playing
// its clip, holding the emitter and shoving the fluid about.
//
// The page never sees the FBX. serve.py hands it to mayapy, which writes the
// small thing this file reads: bone names and parents, a capsule a bone, and
// every bone's world position and rotation on every frame. See fbxread.py for
// why, and for how the capsules are measured.
//
// Everything here is in centimetres, which is one cell of the solver's grid.

const RIG = {
  data: null,
  name: '',
  time: 0,             // seconds into the clip
  playing: true,
  speed: 1,
  bone: -1,            // the bone the emitter rides, -1 for the fixed nozzle
  offset: [0, 0, 0],   // where the character stands, in cells
  collide: true,
  scale: 1,
  // An FBX with no skin in it has nothing to measure a limb's thickness
  // against, so fbxread.py guesses from the bone's length. This is the knob
  // that fixes the guess by eye.
  fat: 1,

  // Up to this many capsules reach the solver: they travel in the uniform the
  // params already use (three vec4 each), and the shader loops over them for
  // every grid node that carries mass.
  MAX_CAPS: 24,
  caps: new Float32Array(24 * 12),
  capCount: 0,

  _prev: null,         // the previous frame's bone positions, for velocity
  _prevTime: -1,

  loaded() { return !!this.data; },

  load(data) {
    if (!data || !data.bones || !data.frames) throw new Error('not a rig file');
    this.data = data;
    this.name = data.source || 'rig';
    this.time = 0;
    this._prev = null;
    this._prevTime = -1;
    this.bone = -1;
    this.fit();
    return data.bones.length;
  },

  drop() { this.data = null; this.capCount = 0; this.bone = -1; },

  // Stand the character in the middle of the floor, at a size that fits.
  //
  // A game character is about 170 cm and the room is as many centimetres as
  // the grid has cells - 96 at the middle quality - so at its own size a
  // Manny's head is through the ceiling and the fluid never sees his arms.
  // Both the size and the place are only the starting point: the two sliders
  // move them afterwards.
  fit() {
    const d = this.data;
    const g = (typeof SIM !== 'undefined' && SIM.grid) || 64;
    if (!d || !d.frames.length) { this.offset = [g * 0.5, 2, g * 0.5]; return; }
    let lo = 1e9, hi = -1e9;
    for (const b of d.frames[0]) { if (b[1] < lo) lo = b[1]; if (b[1] > hi) hi = b[1]; }
    const tall = Math.max(hi - lo, 1);
    this.scale = Math.min(1, (g * 0.78) / tall);
    const r = d.frames[0][0] || [0, 0, 0];
    this.offset = [
      g * 0.5 - r[0] * this.scale,
      1.5 - lo * this.scale,
      g * 0.5 - r[2] * this.scale,
    ];
  },

  seconds() {
    if (!this.data) return 0;
    return (this.data.frames.length) / Math.max(1, this.data.fps);
  },

  advance(dt) {
    if (!this.data || !this.playing) return;
    const len = this.seconds();
    if (len <= 0) return;
    this.time = (this.time + dt * this.speed) % len;
    if (this.time < 0) this.time += len;
  },

  // The two frames around the current time, and how far between them.
  _at() {
    const d = this.data;
    const f = this.time * d.fps;
    const i0 = Math.floor(f) % d.frames.length;
    const i1 = (i0 + 1) % d.frames.length;
    return [d.frames[i0], d.frames[i1], f - Math.floor(f)];
  },

  // One bone's world transform right now: its place and its three rotation
  // columns, already moved and scaled into the room.
  boneAt(i) {
    if (!this.data) return null;
    const [A, B, t] = this._at();
    const a = A[i], b = B[i];
    if (!a) return null;
    const s = this.scale, o = this.offset;
    const mix = (u, v) => u + (v - u) * t;
    return {
      pos: [o[0] + mix(a[0], b[0]) * s, o[1] + mix(a[1], b[1]) * s, o[2] + mix(a[2], b[2]) * s],
      // The rotation columns blended and left unnormalised: over a sixtieth of
      // a second between two frames of the same clip the drift is nothing, and
      // the only thing they are used for is pointing the emitter and placing a
      // capsule's far end.
      m: [mix(a[3], b[3]), mix(a[4], b[4]), mix(a[5], b[5]),
          mix(a[6], b[6]), mix(a[7], b[7]), mix(a[8], b[8]),
          mix(a[9], b[9]), mix(a[10], b[10]), mix(a[11], b[11])],
    };
  },

  boneNames() {
    return this.data ? this.data.bones.map((b) => b.name) : [];
  },

  // Where the emitter is, and which way it points: down the bone it rides.
  nozzle() {
    if (!this.data || this.bone < 0) return null;
    const b = this.boneAt(this.bone);
    if (!b) return null;
    const spec = this.data.bones[this.bone];
    const tip = spec.tip || [0, 0, 0];
    const m = b.m;
    // the bone's own direction, in the room
    let dir = [m[0] * tip[0] + m[3] * tip[1] + m[6] * tip[2],
               m[1] * tip[0] + m[4] * tip[1] + m[7] * tip[2],
               m[2] * tip[0] + m[5] * tip[1] + m[8] * tip[2]];
    const len = Math.hypot(dir[0], dir[1], dir[2]);
    if (len < 1e-4) dir = [0, -1, 0]; else dir = dir.map((v) => v / len);
    // Out of the FAR end of the bone - the fingers of a hand, the tip of a
    // weapon bone - not its root. The root of a hand sits inside the torso's
    // collider when the arm is down, and slime seeded inside a collider is
    // thrown out of it or dies there: the first build poured a thousand
    // particles into the hip and kept a handful.
    const s = this.scale;
    const out = [b.pos[0] + dir[0] * len * s, b.pos[1] + dir[1] * len * s,
                 b.pos[2] + dir[2] * len * s];
    return { pos: out, dir, vel: this.boneVel(this.bone) };
  },

  // How fast a bone is travelling, in cells a second. It is what makes a
  // swung hand fling the slime instead of laying it down.
  boneVel(i) {
    if (!this._prev || !this._prev[i]) return [0, 0, 0];
    const dt = this.time - this._prevTime;
    const w = dt > 1e-4 && dt < 0.5 ? 1 / dt : 0;
    const b = this.boneAt(i);
    if (!b) return [0, 0, 0];
    const p = this._prev[i];
    return [(b.pos[0] - p[0]) * w, (b.pos[1] - p[1]) * w, (b.pos[2] - p[2]) * w];
  },

  // Pack the colliders for the solver and the renderer: a segment, a radius
  // and a velocity each.
  // The capsules are packed whether or not the fluid is to feel them: the
  // picture shows the character either way, and it is the solver that is
  // handed none.
  pack() {
    this.capCount = 0;
    if (!this.data) return 0;
    const list = this.data.colliders || [];
    const n = Math.min(list.length, this.MAX_CAPS);
    for (let k = 0; k < n; k++) {
      const i = list[k];
      const b = this.boneAt(i);
      if (!b) continue;
      const spec = this.data.bones[i];
      const tip = spec.tip || [0, 0, 0];
      const m = b.m, s = this.scale;
      const end = [
        b.pos[0] + (m[0] * tip[0] + m[3] * tip[1] + m[6] * tip[2]) * s,
        b.pos[1] + (m[1] * tip[0] + m[4] * tip[1] + m[7] * tip[2]) * s,
        b.pos[2] + (m[2] * tip[0] + m[5] * tip[1] + m[8] * tip[2]) * s,
      ];
      const v = this.boneVel(i);
      const o = this.capCount * 12;
      this.caps[o + 0] = b.pos[0]; this.caps[o + 1] = b.pos[1];
      this.caps[o + 2] = b.pos[2]; this.caps[o + 3] = spec.radius * s * this.fat;
      this.caps[o + 4] = end[0]; this.caps[o + 5] = end[1];
      this.caps[o + 6] = end[2]; this.caps[o + 7] = 0;
      this.caps[o + 8] = v[0]; this.caps[o + 9] = v[1];
      this.caps[o + 10] = v[2]; this.caps[o + 11] = 0;
      this.capCount++;
    }
    return this.capCount;
  },

  // Remember where every bone was, so the next frame can measure a velocity.
  remember() {
    if (!this.data) return;
    const list = this.data.colliders || [];
    const keep = this._prev || (this._prev = []);
    for (const i of list) {
      const b = this.boneAt(i);
      if (b) keep[i] = b.pos;
    }
    if (this.bone >= 0) {
      const b = this.boneAt(this.bone);
      if (b) keep[this.bone] = b.pos;
    }
    this._prevTime = this.time;
  },

  // Ask serve.py to read an FBX with Maya. Slow - Maya has to start - so the
  // caller shows that something is happening.
  async upload(file) {
    const r = await fetch('/fbx/' + encodeURIComponent(file.name), {
      method: 'POST', body: file,
    });
    const text = await r.text();
    let data = null;
    try { data = JSON.parse(text); } catch (e) { data = null; }
    if (!r.ok || !data || data.error) {
      throw new Error((data && (data.error + (data.detail ? ': ' + data.detail : ''))) ||
        'the server could not read it (is serve.py running?)');
    }
    return data;
  },
};
