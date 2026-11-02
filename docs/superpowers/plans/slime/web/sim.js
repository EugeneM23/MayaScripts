// The host side of the solver: buffers, the four dispatches, the step.
//
// Everything is in cell units and one cell is 1 cm, so the default 96-cell
// domain is about a metre on a side - the scale of a character and a floor,
// which is what this slime is eventually for.

const SIM = {
  // --- what the material is. These are the numbers the sliders move.
  params: {
    gravity: 900.0,        // cells/s^2, so 9 m/s^2 at 1 cell = 1 cm
    mu: 220.0,             // elasticity: the jiggle
    lam: 12000.0,          // incompressibility
    yieldS: 85.0,          // how much shape it holds before it gives in
    visc: 2.4,             // how slowly it gives in once it does
    wallStick: 0.55,       // 0 slips along a wall, 1 clings
    substeps: 9,
    // 64 cells is 64 cm at 1 cell = 1 cm: a basin of slime, not a room. The
    // grid is cleared and solved once per substep over every node, so its cost
    // is the cube of this number and it is the first thing to turn down.
    gridN: 64,
    maxParticles: 120000,
  },

  device: null,
  limits: null,
  grid: 0,
  max: 0,
  // How many slots have ever been handed out: the dispatch only covers these.
  high: 0,
  cursor: 0,
  frame: 0,
  stats: { mass: 0, nan: 0, live: 0 },

  buf: {},
  pipe: {},
  bind: null,
  paramData: new Float32Array(44),

  // One particle per half-cell: 8 a cell, which is what pvol and pmass assume.
  LATTICE: 0.5,

  _statsBusy: false,
  _timing: null,

  async init(device, hasTimestamp) {
    this.device = device;
    this.limits = device.limits;
    if (hasTimestamp) {
      this._timing = {
        set: device.createQuerySet({ type: 'timestamp', count: 2 }),
        resolve: device.createBuffer({ size: 16, usage: GPUBufferUsage.QUERY_RESOLVE | GPUBufferUsage.COPY_SRC }),
        read: device.createBuffer({ size: 16, usage: GPUBufferUsage.COPY_DST | GPUBufferUsage.MAP_READ }),
        busy: false,
        ms: 0,
      };
    }

    const mod = device.createShaderModule({ code: SIM_WGSL, label: 'sim' });
    const info = await mod.getCompilationInfo();
    for (const m of info.messages) {
      const where = `sim.wgsl:${m.lineNum}:${m.linePos}`;
      if (m.type === 'error') console.error(where, m.message);
      else console.warn(where, m.message);
    }
    if (info.messages.some((m) => m.type === 'error')) {
      throw new Error('the solver shader did not compile - see the console');
    }

    this.layout = device.createBindGroupLayout({
      entries: [
        { binding: 0, visibility: GPUShaderStage.COMPUTE, buffer: { type: 'uniform' } },
        ...[1, 2, 3, 4, 5, 6, 7, 8].map((binding) => ({
          binding, visibility: GPUShaderStage.COMPUTE, buffer: { type: 'storage' },
        })),
      ],
    });
    const pl = device.createPipelineLayout({ bindGroupLayouts: [this.layout] });
    for (const name of ['clearGrid', 'clearStats', 'p2g', 'solveGrid', 'g2p', 'seed', 'killAll']) {
      this.pipe[name] = device.createComputePipeline({
        layout: pl, compute: { module: mod, entryPoint: name }, label: name,
      });
    }

    this.allocate();
  },

  // --- memory. Rebuilt whenever the grid or the particle budget changes.
  allocate() {
    const d = this.device;
    const g = this.params.gridN;
    const n = this.params.maxParticles;
    const nodes = g * g * g;

    const perBinding = this.limits.maxStorageBufferBindingSize;
    const need = Math.max(nodes * 16, n * 48);
    if (need > perBinding) {
      throw new Error(`that needs a ${(need / 1048576) | 0} MB buffer and the limit is ${(perBinding / 1048576) | 0} MB`);
    }

    for (const b of Object.values(this.buf)) { if (b && b.destroy) b.destroy(); }
    const S = GPUBufferUsage.STORAGE;
    const mk = (size, usage, label) => d.createBuffer({ size, usage, label });

    this.buf = {
      params: mk(this.paramData.byteLength, GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST, 'params'),
      // Position is a buffer of its own, not a field of one fat struct: a
      // contiguous position buffer is a single copy away from a frame of a
      // point cache, which is what the bake will want.
      // Every particle buffer is readable back, not only position: the bake
      // will want positions and velocities, and a solver you cannot read is a
      // solver you can only guess about. Measuring the deformation is how the
      // material gets tuned at all.
      pos: mk(n * 16, S | GPUBufferUsage.COPY_SRC, 'pos'),
      vel: mk(n * 16, S | GPUBufferUsage.COPY_SRC, 'vel'),
      defo: mk(n * 48, S | GPUBufferUsage.COPY_SRC, 'defo'),
      affine: mk(n * 48, S | GPUBufferUsage.COPY_SRC, 'affine'),
      extra: mk(n * 4, S | GPUBufferUsage.COPY_SRC, 'extra'),
      gridA: mk(nodes * 16, S, 'gridA'),
      gridV: mk(nodes * 16, S, 'gridV'),
      stats: mk(32, S | GPUBufferUsage.COPY_SRC, 'stats'),
      statsRead: mk(32, GPUBufferUsage.COPY_DST | GPUBufferUsage.MAP_READ, 'statsRead'),
    };

    this.bind = d.createBindGroup({
      layout: this.layout,
      entries: [
        { binding: 0, resource: { buffer: this.buf.params } },
        { binding: 1, resource: { buffer: this.buf.pos } },
        { binding: 2, resource: { buffer: this.buf.vel } },
        { binding: 3, resource: { buffer: this.buf.defo } },
        { binding: 4, resource: { buffer: this.buf.affine } },
        { binding: 5, resource: { buffer: this.buf.extra } },
        { binding: 6, resource: { buffer: this.buf.gridA } },
        { binding: 7, resource: { buffer: this.buf.gridV } },
        { binding: 8, resource: { buffer: this.buf.stats } },
      ],
    });

    this.grid = g;
    this.max = n;
    this.nodes = nodes;
    this.clear();
  },

  bytes() {
    const n = this.max, nodes = this.nodes;
    return n * 132 + nodes * 32;
  },

  // Particle volume and mass for ~8 particles a cell at unit density.
  pvol() { return 0.125; },
  pmass() { return 0.125; },

  writeParams(extra) {
    const p = this.paramData;
    const q = this.params;
    const g = this.grid;
    p[0] = g; p[1] = g; p[2] = g; p[3] = 0;
    const e = extra || {};
    const v4 = (off, a) => { p[off] = a[0]; p[off + 1] = a[1]; p[off + 2] = a[2]; p[off + 3] = a[3]; };
    v4(4, e.mouse || [0, 0, 0, 0]);
    v4(8, e.mouseVel || [0, 0, 0, 0]);
    v4(12, e.obstacle || [0, 0, 0, 0]);
    v4(16, e.emitPos || [0, 0, 0, 0]);
    v4(20, e.emitDir || [0, 1, 0, 0]);
    p[24] = e.dt != null ? e.dt : 0;
    p[25] = q.gravity;
    p[26] = q.mu;
    p[27] = q.lam;
    p[28] = q.yieldS;
    p[29] = q.visc;
    p[30] = q.wallStick;
    p[31] = this.pmass();
    p[32] = this.pvol();
    p[33] = Math.max(this.high, 1);
    p[34] = e.seedBase || 0;
    p[35] = e.seedCount || 0;
    p[36] = e.seedKind || 0;
    p[37] = this.frame;
    p[38] = e.jitter != null ? e.jitter : 0;
    p[39] = e.latN || 1;
    p[40] = e.latM || 1;
    p[41] = e.latStep || this.LATTICE;
    p[42] = 0;
    p[43] = 0;
    this.device.queue.writeBuffer(this.buf.params, 0, p);
  },

  groups(n) { return Math.max(1, Math.ceil(n / 256)); },

  clear() {
    this.high = this.max;         // killAll must cover every slot
    this.writeParams({});
    const enc = this.device.createCommandEncoder();
    const pass = enc.beginComputePass();
    pass.setPipeline(this.pipe.killAll);
    pass.setBindGroup(0, this.bind);
    pass.dispatchWorkgroups(this.groups(this.max));
    pass.end();
    this.device.queue.submit([enc.finish()]);
    this.high = 0;
    this.cursor = 0;
    this.frame = 0;
    this.stats = { mass: 0, nan: 0, live: 0, why: { pos: 0, vel: 0, defo: 0, fast: 0 }, maxSpeed: 0 };
    // The reset counters live on the GPU and are session totals, so a clear
    // zeroes them here too - otherwise "Заново" would not clear the warning.
    this.device.queue.writeBuffer(this.buf.stats, 0, new Int32Array(8));
  },

  // --- emission. One ring of slots: a held pour recycles the oldest slime
  // instead of growing without bound, so the cost of pouring is capped.
  //
  // A run that would cross the end of the ring is split in two, so the seed
  // kernel never has to wrap an index and the dispatch bound stays simple.
  emit(count, kind, centre, radius, dir, speed, jitter, lat) {
    if (count <= 0) return 0;
    let left = Math.min(count, this.max);
    let placed = 0;
    while (left > 0) {
      const base = this.cursor;
      const n = Math.min(left, this.max - base);
      this._seedRun(base, n, kind, centre, radius, dir, speed, jitter, lat);
      this.cursor = (base + n) % this.max;
      // Every slot from 0 up to where the cursor has reached has been handed
      // out; once the ring wraps, that is all of them.
      this.high = (base + n >= this.max) ? this.max : Math.max(this.high, base + n);
      left -= n;
      placed += n;
    }
    return placed;
  },

  _seedRun(base, n, kind, centre, radius, dir, speed, jitter, lat) {
    this.writeParams({
      dt: 1 / 60,
      emitPos: [centre[0], centre[1], centre[2], radius],
      emitDir: [dir[0], dir[1], dir[2], speed],
      seedBase: base, seedCount: n, seedKind: kind, jitter: jitter || 0,
      latN: (lat && lat.n) || 1, latM: (lat && lat.m) || 1, latStep: this.LATTICE,
    });
    const enc = this.device.createCommandEncoder();
    const pass = enc.beginComputePass();
    pass.setPipeline(this.pipe.seed);
    pass.setBindGroup(0, this.bind);
    pass.dispatchWorkgroups(Math.max(1, Math.ceil(n / 64)));
    pass.end();
    this.device.queue.submit([enc.finish()]);
  },

  // The counts are lattice sites, not particles: the sites outside the shape
  // are marked dead by the kernel, so a sphere keeps about half of them and a
  // disc about three quarters.
  dropBlob(centre, radius) {
    const n = Math.max(1, Math.ceil((2 * radius) / this.LATTICE));
    return this.emit(n * n * n, 0, centre, radius, [0, -1, 0], 0, 0.0, { n, m: 1 });
  },

  pour(centre, dir, radius, speed, seconds) {
    const n = Math.max(1, Math.ceil((2 * radius) / this.LATTICE));
    const m = Math.max(1, Math.round((speed * seconds) / this.LATTICE));
    return this.emit(n * n * m, 1, centre, radius, dir, speed, 0.0, { n, m });
  },

  // --- one frame.
  step(dtFrame, world) {
    if (this.high <= 0) return;
    const sub = Math.max(1, this.params.substeps | 0);
    const dt = dtFrame / sub;
    const d = this.device;
    const enc = d.createCommandEncoder();
    const t = this._timing;

    // Written once, not per substep: queue.writeBuffer is ordered on the queue
    // and not inside the encoder, so eight writes before one submit would all
    // land before the first dispatch ran and only the last would be seen. Only
    // dt varies between substeps and it is constant, so one write is correct.
    // Anything that must change per substep needs its own submit, or a
    // dynamically offset uniform.
    this.writeParams({ ...world, dt });

    for (let s = 0; s < sub; s++) {
      const tw = {};
      if (t && s === 0) tw.beginningOfPassWriteIndex = 0;
      if (t && s === sub - 1) tw.endOfPassWriteIndex = 1;
      const pass = enc.beginComputePass(
        Object.keys(tw).length ? { timestampWrites: { querySet: t.set, ...tw } } : undefined);
      pass.setBindGroup(0, this.bind);

      pass.setPipeline(this.pipe.clearStats);
      pass.dispatchWorkgroups(1);
      pass.setPipeline(this.pipe.clearGrid);
      pass.dispatchWorkgroups(this.groups(this.nodes));
      pass.setPipeline(this.pipe.p2g);
      pass.dispatchWorkgroups(this.groups(this.high));
      pass.setPipeline(this.pipe.solveGrid);
      pass.dispatchWorkgroups(this.groups(this.nodes));
      pass.setPipeline(this.pipe.g2p);
      pass.dispatchWorkgroups(this.groups(this.high));
      pass.end();
    }

    if (t) {
      enc.resolveQuerySet(t.set, 0, 2, t.resolve, 0);
      if (!t.busy) enc.copyBufferToBuffer(t.resolve, 0, t.read, 0, 16);
    }

    if (!this._statsBusy) enc.copyBufferToBuffer(this.buf.stats, 0, this.buf.statsRead, 0, 32);
    d.queue.submit([enc.finish()]);
    this.frame++;

    // The readbacks are deliberately not awaited: a map that is still in flight
    // is skipped, so the numbers on the panel lag by a frame or two instead of
    // stalling the pipeline every frame to be exact.
    if (!this._statsBusy) {
      this._statsBusy = true;
      this.buf.statsRead.mapAsync(GPUMapMode.READ).then(() => {
        const a = new Int32Array(this.buf.statsRead.getMappedRange()).slice();
        this.buf.statsRead.unmap();
        this.stats = {
          mass: a[0] / 256, nan: a[1], live: a[2],
          why: { pos: a[3], vel: a[4], defo: a[5], fast: a[6] },
          maxSpeed: a[7] / 16,
        };
        this._statsBusy = false;
      }).catch(() => { this._statsBusy = false; });
    }
    if (t && !t.busy) {
      t.busy = true;
      t.read.mapAsync(GPUMapMode.READ).then(() => {
        const a = new BigUint64Array(t.read.getMappedRange()).slice();
        t.read.unmap();
        const ns = Number(a[1] - a[0]);
        if (ns > 0 && ns < 1e10) t.ms = t.ms * 0.8 + (ns / 1e6) * 0.2;
        t.busy = false;
      }).catch(() => { t.busy = false; });
    }
  },

  gpuMs() { return this._timing ? this._timing.ms : 0; },
};
