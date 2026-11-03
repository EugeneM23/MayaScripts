// The panel, the presets, the mouse and the frame loop.
//
// The three sliders that matter are Elasticity, Hold and Viscosity. Hold is
// shown as a percentage of shear rather than as a stress, because a stress
// means nothing without knowing the elasticity: "holds its shape up to 8% of
// deformation" is a thing you can picture, and the solver's yield stress is
// worked out from it (yield = 2*mu*hold).

const UI = {
  // mu, hold %, viscosity, incompressibility, wall stick, gravity, and the look.
  //
  // The incompressibility is deliberately modest. The substeps a frame need to
  // rise as its square root, so 30k against 65k is a third off the cost of the
  // whole solver, and what it buys is a few percent of squash at the bottom of
  // a puddle - which on slime is not something anybody can see.
  // The elasticity has to be large enough that the material reaches its yield
  // stress while still inside a sane elastic strain: the strain at yield is
  // yield/(2*mu), and anything past about 20% is outside the bound the solver
  // clamps F to. For a 6 cm mound at this gravity that puts mu in the
  // thousands, not the hundreds.
  presets: {
    'Вода': { mu: 0, hold: 0, visc: 0, lam: 45000, stick: 0.05, grav: 150,
      tint: [0.46, 0.70, 0.86], absorb: 0.10, rough: 0.06, refract: 1.5, radius: 0.8 },
    'Мёд': { mu: 2000, hold: 0.4, visc: 150, lam: 36000, stick: 0.50, grav: 150,
      tint: [0.95, 0.70, 0.24], absorb: 0.52, rough: 0.12, refract: 1.2, radius: 0.85 },
    'Кисель': { mu: 6000, hold: 6, visc: 60, lam: 30000, stick: 0.60, grav: 150,
      tint: [0.80, 0.24, 0.34], absorb: 0.36, rough: 0.22, refract: 0.9, radius: 0.9 },
    'Слизь': { mu: 9000, hold: 10, visc: 90, lam: 30000, stick: 0.78, grav: 150,
      tint: [0.44, 0.80, 0.28], absorb: 0.30, rough: 0.16, refract: 1.0, radius: 0.9 },
    'Желе': { mu: 20000, hold: 40, visc: 0, lam: 36000, stick: 0.25, grav: 150,
      tint: [0.86, 0.34, 0.54], absorb: 0.26, rough: 0.10, refract: 1.1, radius: 0.9 },
    'Грязь': { mu: 5000, hold: 14, visc: 120, lam: 28000, stick: 0.85, grav: 150,
      tint: [0.34, 0.26, 0.19], absorb: 0.95, rough: 0.42, refract: 0.4, radius: 0.95 },
  },

  // How much work a frame is allowed to be. The browser is usually handed the
  // integrated GPU on a laptop - Chrome on Windows ignores powerPreference
  // (crbug.com/369219127) - so the default is sized for one of those, and a
  // machine with a discrete card can afford to go up.
  quality: {
    'Низкое': { gridN: 56, maxParticles: 90000, dpr: 1.0, thickDiv: 3, smooth: 1 },
    'Среднее': { gridN: 64, maxParticles: 120000, dpr: 1.0, thickDiv: 2, smooth: 2 },
    'Высокое': { gridN: 88, maxParticles: 240000, dpr: 1.25, thickDiv: 2, smooth: 2 },
    'Макс': { gridN: 112, maxParticles: 400000, dpr: 1.5, thickDiv: 1, smooth: 3 },
  },

  state: {
    hold: 8,                // % of shear it holds before it gives in
    autoSubsteps: true,
    paused: false,
    stepOnce: false,
    pouring: false,
    obstacle: true,
    handRadius: 7,
    handStrength: 0.85,
    nozzleHeight: 0.30,   // of the domain
    nozzleSpeed: 0.10,    // of the domain a second
    preset: 'Кисель',
    quality: 'Среднее',
    autoQuality: true,
  },

  hand: { on: false, pos: null, prev: null, vel: [0, 0, 0], depth: 0 },
  fps: { last: 0, acc: 0, n: 0, value: 0 },

  // What a frame really costs, measured from the GPU rather than from how often
  // the loop was entered. The two are not the same number: WebGPU submits
  // without blocking, so a loop that runs at 60 Hz in front of a GPU doing 2
  // can report 60 fps while the picture on the screen falls minutes behind.
  perf: {
    inFlight: false,      // a frame is still on the GPU - do not queue another
    started: 0,
    lastDone: 0,
    frameMs: 0,           // smoothed, the period between finished frames
    worstMs: 0,
    level: 0,             // index into AUTO_STEPS, 0 is the prettiest
    hot: 0, cool: 0,      // frames in a row over / under the target
    changed: 0,
  },

  // 33 ms is the target: the prototype is for judging how a material moves, and
  // a material cannot be judged below about 30 fps.
  TARGET_MS: 33,

  // How the picture gets cheaper, in the order that costs the look least. Every
  // one of these is a render setting: the governor must never touch the grid or
  // the particle count, because changing those reallocates and throws the
  // simulation away - a sandbox that resets itself when it gets slow is worse
  // than a slow one. The pixels are what the renderer spends its time on, so
  // the first lever is the resolution and the last is the surface filter.
  AUTO_STEPS: [
    { scale: 1.00, smooth: 0, thick: 0, px: 2400000 },
    { scale: 0.85, smooth: 0, thick: 0, px: 1700000 },
    { scale: 0.72, smooth: -1, thick: 0, px: 1200000 },
    { scale: 0.60, smooth: -1, thick: 1, px: 850000 },
    { scale: 0.50, smooth: -1, thick: 2, px: 600000 },
    { scale: 0.40, smooth: -2, thick: 2, px: 420000 },
  ],

  async boot() {
    if (!navigator.gpu) throw new Error('В этом браузере нет WebGPU');
    const adapter = await navigator.gpu.requestAdapter({ powerPreference: 'high-performance' });
    if (!adapter) throw new Error('WebGPU не дал адаптер (нет подходящей видеокарты?)');

    // Ask for what we can use and do without what we cannot.
    const want = ['timestamp-query', 'float32-filterable'];
    const have = want.filter((f) => adapter.features.has(f));
    const device = await adapter.requestDevice({ requiredFeatures: have });
    device.addEventListener('uncapturederror', (e) => console.error('WebGPU:', e.error.message));
    this.device = device;
    this.filterable = have.includes('float32-filterable');
    const info = adapter.info || {};
    // Kept and shown on the panel, not only logged: a browser that has fallen
    // back to a software adapter runs this at seconds a frame, and the only way
    // anybody finds that out is by being told which device they got.
    this.gpu = {
      name: [info.vendor, info.architecture, info.device].filter(Boolean).join(' ') ||
        info.description || 'неизвестно',
      fallback: !!adapter.isFallbackAdapter,
    };
    console.log('adapter:', info.vendor, info.architecture, info.description || '');
    console.log('features:', have.join(', ') || 'none of the optional ones');

    await SIM.init(device, have.includes('timestamp-query'));
    await RENDER.init(device, document.getElementById('gfx'), this.filterable,
      have.includes('timestamp-query'));
    RENDER.bindParticles(SIM.buf.pos, SIM.buf.vel);

    this.buildPanel();
    this.applyQuality(this.state.quality);
    this.applyPreset(this.state.preset);
    this.wireInput();
    // applyQuality already reallocated and dropped the first blob; dropping a
    // second one here would put two overlapping blobs in the same place, at
    // twice the density the solver assumes, which blows up on contact.
    // Coming back to the page starts the measurement again from nothing, so the
    // frames spent in the background never count toward turning the picture down.
    document.addEventListener('visibilitychange', () => {
      const p = this.perf;
      p.frameMs = 0; p.hot = 0; p.cool = 0; p.lastDone = 0; p.worstMs = 0;
    });

    this.loop = this.loop.bind(this);
    this.startDriver();
  },

  // requestAnimationFrame is the right driver, but it does not fire at all in
  // some embedded browser panes (an offscreen page is treated as a background
  // one). If no frame has arrived shortly after the start, fall back to a timer
  // so the prototype runs anywhere; in a normal Chrome window this never
  // triggers and rAF stays in charge.
  // ONE chain drives the loop, and the loop does not queue itself. It did both
  // for a while, and the two chains bred: the driver's callback queued the next
  // driver callback AND a loop callback, so the number of loop calls in a frame
  // went up by one every frame - a minute in, a single displayed frame carried
  // thousands of solver steps and the page looked frozen. It never showed in an
  // embedded pane, where requestAnimationFrame does not fire at all and only
  // the timer path ran. A driver owns the re-queue; nothing else may.
  startDriver() {
    let ticked = false;
    const raf = (now) => { ticked = true; this.loop(now); requestAnimationFrame(raf); };
    requestAnimationFrame(raf);
    setTimeout(() => {
      if (ticked) return;
      console.warn('requestAnimationFrame is not firing here - driving the loop on a timer');
      this.timerDriven = true;
      const tick = () => { this.loop(performance.now()); setTimeout(tick, 16); };
      tick();
    }, 500);
  },

  // ------------------------------------------------------- keeping up

  // What the governor does with a level, applied over whatever the quality
  // buttons chose. The quality preset stays the ceiling; auto only ever makes
  // the picture cheaper than the one that was asked for.
  applyAuto() {
    const base = this.quality[this.state.quality];
    if (!base) return;
    const step = this.AUTO_STEPS[Math.max(0, Math.min(this.AUTO_STEPS.length - 1, this.perf.level))];
    const on = this.state.autoQuality;
    RENDER.look.dpr = base.dpr * (on ? step.scale : 1);
    // Switching auto off keeps the ceiling of the best level: it means "stop
    // turning my picture down", not "ask for eight megapixels".
    RENDER.look.maxPixels = (on ? step : this.AUTO_STEPS[0]).px;
    RENDER.look.smooth = Math.max(0, base.smooth + (on ? step.smooth : 0));
    RENDER.look.thickDiv = Math.max(1, base.thickDiv + (on ? step.thick : 0));
    if (this.rows.smooth) this.rows.smooth();
  },

  // Called once a finished frame with what that frame really cost.
  govern(ms) {
    const p = this.perf;
    p.frameMs = p.frameMs ? p.frameMs * 0.8 + ms * 0.2 : ms;
    if (ms > p.worstMs) p.worstMs = ms;
    if (!this.state.autoQuality) return;

    // What the frame COST, from the GPU's own clocks, not how long it was
    // between two finished frames: the wall clock also holds everything that is
    // not work - a page the compositor is not showing reads hundreds of ms a
    // frame for a few ms of GPU, and a governor fed that turns the picture down
    // to its ugliest for nothing. Where the timestamps are missing, the wall
    // clock is all there is and it is used, with document.hidden as the guard.
    p.gpuMs = SIM.gpuMs() + RENDER.gpuMs();
    const cost = p.gpuMs > 0 ? p.gpuMs : (document.hidden ? 0 : ms);
    if (cost <= 0) { p.hot = 0; p.cool = 0; return; }
    const t = this.TARGET_MS;
    const last = this.AUTO_STEPS.length - 1;

    // Which half of the frame is expensive. The governor's levers are all
    // pixels, so if the picture is a small part of the cost there is nothing
    // for it to win: on this machine a 1239x833 frame is 2.9 ms of picture
    // against 9.2 ms of solver, and turning the picture down to its ugliest
    // would buy two milliseconds of fifty. The solver's own levers - particles,
    // substeps, the grid - are not the governor's to pull: they reallocate, or
    // they make the solver unstable. So it says what the cost is and leaves it.
    p.solverBound = p.gpuMs > 0 && RENDER.gpuMs() < 0.35 * p.gpuMs;

    if (cost > t * 1.25) {
      p.cool = 0; p.hot++;
      if (p.solverBound && p.level >= 2) { p.hot = 0; return; }
      // A frame that is catastrophically over does not get walked down one
      // level at a time: four seconds of 2 s frames to reach a usable picture
      // is four seconds in which the page looks broken.
      const jump = cost > t * 6 ? 3 : (cost > t * 2.5 ? 2 : 1);
      if (p.hot >= 3 && p.level < last) {
        p.level = Math.min(last, p.level + jump);
        p.hot = 0; p.changed = performance.now();
        this.applyAuto();
      }
    } else if (cost < t * 0.62) {
      p.hot = 0; p.cool++;
      // Slow to climb back, so a quiet moment does not start it oscillating.
      if (p.cool >= 120 && p.level > 0 && performance.now() - p.changed > 3000) {
        p.level--; p.cool = 0; p.changed = performance.now();
        this.applyAuto();
      }
    } else {
      p.hot = 0; p.cool = 0;
    }
  },

  // ------------------------------------------------------------ the world

  gridN() { return SIM.grid; },

  // Resting on the floor, not hovering over it: an obstacle with daylight under
  // it reads as a mistake, and slime draping off something that touches the
  // ground is the shot this is eventually for.
  obstacleVec() {
    if (!this.state.obstacle) return [0, 0, 0, 0];
    const g = this.gridN();
    const r = g * 0.13;
    return [g * 0.5, 2 + r, g * 0.5, r];
  },

  // Low and slow, because the pour is the most diagnostic thing in the sandbox
  // and it only says anything while the rope is still a rope when it lands.
  // It poured from 0.82 of the domain at 0.75 of it a second to start with: a
  // 70 cm fall arrives at the speed the solver caps it at, and a thick fluid
  // that fast does not coil, it splats - measured, a flat torn puddle. From 30
  // cm at a tenth of the domain a second the same material lays itself down in
  // stacked folds. Both are sliders now, because "how far it falls" is a thing
  // about the shot and not about the material.
  nozzle() {
    const g = this.gridN();
    return {
      pos: [g * 0.5, g * this.state.nozzleHeight, g * 0.5],
      dir: [0, -1, 0],
      radius: g * 0.032,
      speed: g * this.state.nozzleSpeed,
    };
  },

  frameCamera() {
    const g = this.gridN();
    RENDER.cam.target = [g * 0.5, g * 0.22, g * 0.5];
    RENDER.cam.dist = g * 2.1;
    RENDER.cam.yaw = 0.7;
    RENDER.cam.pitch = 0.32;
  },

  // Dropped from 12 cm up, not from the ceiling. A blob let go at the top of
  // the domain arrives at over a metre a second and pancakes whatever it is
  // made of - measured: a solid jelly that holds its shape exactly at zero
  // gravity still splatted from 14.5 cm across to 5.8 tall. That is the impact
  // talking, not the material, and a bench for judging a material must not
  // shout over it.
  dropBlob() {
    const g = this.gridN();
    const r = g * 0.115;
    SIM.dropBlob([g * 0.5, 2 + r + 12, g * 0.5], r);
  },

  pourTick() {
    const n = this.nozzle();
    SIM.pour(n.pos, n.dir, n.radius, n.speed, 1 / 60);
  },

  // --------------------------------------------------------------- panel

  buildPanel() {
    const host = document.getElementById('controls');
    const el = (tag, cls, txt) => {
      const e = document.createElement(tag);
      if (cls) e.className = cls;
      if (txt != null) e.textContent = txt;
      return e;
    };
    this.rows = {};

    const head = (t) => host.appendChild(el('div', 'head', t));
    const buttons = (defs) => {
      const row = el('div', 'btns');
      const made = {};
      for (const [label, fn, cls] of defs) {
        const b = el('button', cls || '', label);
        b.onclick = () => fn(b);
        made[label] = b;
        row.appendChild(b);
      }
      host.appendChild(row);
      return made;
    };
    const slider = (key, label, min, max, step, get, set, fmt) => {
      const row = el('div', 'row');
      row.appendChild(el('label', '', label));
      const r = document.createElement('input');
      r.type = 'range'; r.min = min; r.max = max; r.step = step; r.value = get();
      const v = el('div', 'val', '');
      const show = () => { v.textContent = fmt ? fmt(get()) : String(get()); r.value = get(); };
      r.oninput = () => { set(parseFloat(r.value)); show(); this.refreshRows(); };
      row.appendChild(r); row.appendChild(v);
      host.appendChild(row);
      this.rows[key] = show;
      show();
      return row;
    };

    head('Материал');
    this.presetBtns = buttons(Object.keys(this.presets).map((name) =>
      [name, () => this.applyPreset(name)]));

    slider('mu', 'Упругость', 0, 24000, 100,
      () => SIM.params.mu, (v) => { SIM.params.mu = v; this.applyHold(); },
      (v) => (v / 1000).toFixed(1) + 'k');
    host.appendChild(this._hint('дрожь и пружинистость'));
    slider('hold', 'Держит форму', 0, 40, 0.5,
      () => this.state.hold, (v) => { this.state.hold = v; this.applyHold(); },
      (v) => (v >= 40 ? 'всегда' : v.toFixed(1) + ' см'));
    host.appendChild(this._hint('какой высоты горку держит: 0 — вода, 6 — кисель'));
    slider('visc', 'Вязкость', 0, 300, 2,
      () => SIM.params.visc, (v) => { SIM.params.visc = v; }, (v) => v.toFixed(0));
    host.appendChild(this._hint('как медленно растекается, когда уже поддалась'));
    slider('lam', 'Несжимаемость', 10000, 200000, 1000,
      () => SIM.params.lam, (v) => { SIM.params.lam = v; this.applyHold(); },
      (v) => (v / 1000).toFixed(0) + 'k');
    slider('stick', 'Липкость', 0, 1, 0.01,
      () => SIM.params.wallStick, (v) => { SIM.params.wallStick = v; }, (v) => v.toFixed(2));
    slider('grav', 'Гравитация', 0, 400, 5,
      () => SIM.params.gravity, (v) => { SIM.params.gravity = v; this.applyHold(); });

    head('Сцена');
    this.sceneBtns = buttons([
      ['Капля', () => this.dropBlob()],
      ['Струя', (b) => { this.state.pouring = !this.state.pouring; b.classList.toggle('on', this.state.pouring); }],
      ['Шар', (b) => { this.state.obstacle = !this.state.obstacle; b.classList.toggle('on', this.state.obstacle); }],
      ['Заново', () => { SIM.clear(); this.dropBlob(); }],
    ]);
    this.sceneBtns['Шар'].classList.toggle('on', this.state.obstacle);
    slider('nozh', 'Высота струи', 0.12, 0.9, 0.01,
      () => this.state.nozzleHeight, (v) => { this.state.nozzleHeight = v; },
      (v) => (v * this.gridN()).toFixed(0) + ' см');
    slider('nozv', 'Напор', 0.03, 0.8, 0.01,
      () => this.state.nozzleSpeed, (v) => { this.state.nozzleSpeed = v; },
      (v) => (v * this.gridN()).toFixed(0) + ' см/с');
    host.appendChild(this._hint('ниже и медленнее — струя укладывается кольцами'));
    slider('hand', 'Радиус руки', 2, 20, 0.5,
      () => this.state.handRadius, (v) => { this.state.handRadius = v; });
    slider('grab', 'Сила руки', 0, 1, 0.05,
      () => this.state.handStrength, (v) => { this.state.handStrength = v; }, (v) => v.toFixed(2));

    head('Качество');
    this.qualityBtns = buttons(Object.keys(this.quality).map((name) =>
      [name, () => this.applyQuality(name)]));
    host.appendChild(this._hint('выше — красивее и медленнее'));
    this.autoBtns = buttons([
      ['Авто качество', (b) => {
        this.state.autoQuality = !this.state.autoQuality;
        b.classList.toggle('on', this.state.autoQuality);
        if (!this.state.autoQuality) this.perf.level = 0;
        this.perf.hot = 0; this.perf.cool = 0;
        this.applyAuto();
      }],
    ]);
    this.autoBtns['Авто качество'].classList.toggle('on', this.state.autoQuality);
    host.appendChild(this._hint('сам убавляет картинку, пока кадр не уложится в 30 к/с'));

    head('Решатель');
    slider('sub', 'Подшагов', 2, 40, 1,
      () => SIM.params.substeps, (v) => { SIM.params.substeps = v; this.state.autoSubsteps = false;
        if (this.solverBtns) this.solverBtns['Авто подшаги'].classList.remove('on'); });
    this.solverBtns = buttons([
      ['Авто подшаги', (b) => { this.state.autoSubsteps = !this.state.autoSubsteps;
        b.classList.toggle('on', this.state.autoSubsteps); this.applyHold(); }],
    ]);
    this.solverBtns['Авто подшаги'].classList.toggle('on', this.state.autoSubsteps);
    slider('grid', 'Сетка', 48, 128, 16,
      () => SIM.params.gridN, (v) => this.realloc({ gridN: v }), (v) => v + '³');
    slider('parts', 'Частиц (макс)', 50000, 500000, 10000,
      () => SIM.params.maxParticles, (v) => this.realloc({ maxParticles: v }),
      (v) => (v / 1000) + 'k');

    head('Вид');
    this.viewBtns = buttons([
      ['Слизь', () => this.setMode(0)],
      ['Точки', () => this.setMode(1)],
      ['Глубина', () => this.setMode(2)],
      ['Нормали', () => this.setMode(3)],
      ['Толщина', () => this.setMode(4)],
    ]);
    slider('radius', 'Радиус частиц', 0.4, 2.0, 0.05,
      () => RENDER.look.radius, (v) => { RENDER.look.radius = v; }, (v) => v.toFixed(2));
    slider('smooth', 'Сглаживание', 0, 4, 1,
      () => RENDER.look.smooth, (v) => { RENDER.look.smooth = v; });
    slider('rough', 'Шероховатость', 0.02, 0.8, 0.01,
      () => RENDER.look.roughness, (v) => { RENDER.look.roughness = v; }, (v) => v.toFixed(2));
    slider('absorb', 'Плотность цвета', 0.02, 1.2, 0.02,
      () => RENDER.look.absorb, (v) => { RENDER.look.absorb = v; }, (v) => v.toFixed(2));
    slider('refract', 'Преломление', 0, 3, 0.05,
      () => RENDER.look.refract, (v) => { RENDER.look.refract = v; }, (v) => v.toFixed(2));

    const srow = el('div', 'row');
    srow.appendChild(el('label', '', 'Цвет'));
    const sw = el('div', 'swatch');
    const colours = [[0.80, 0.24, 0.34], [0.44, 0.80, 0.28], [0.95, 0.70, 0.24],
                     [0.46, 0.70, 0.86], [0.86, 0.34, 0.54], [0.34, 0.26, 0.19], [0.88, 0.88, 0.9]];
    this.swatches = colours.map((c) => {
      const d = el('div');
      d.style.background = `rgb(${c.map((x) => Math.round(Math.pow(x, 1 / 2.2) * 255)).join(',')})`;
      d.onclick = () => { RENDER.look.tint = c.slice(); this.markSwatch(); };
      sw.appendChild(d);
      return { el: d, c };
    });
    srow.appendChild(sw);
    host.appendChild(srow);

    this.setMode(0);
  },

  _hint(t) {
    const e = document.createElement('div');
    e.className = 'hint';
    e.textContent = t;
    return e;
  },

  markSwatch() {
    const t = RENDER.look.tint;
    for (const s of this.swatches) {
      const near = Math.abs(s.c[0] - t[0]) + Math.abs(s.c[1] - t[1]) + Math.abs(s.c[2] - t[2]) < 0.02;
      s.el.classList.toggle('on', near);
    }
  },

  setMode(m) {
    RENDER.look.mode = m;
    const names = ['Слизь', 'Точки', 'Глубина', 'Нормали', 'Толщина'];
    names.forEach((n, i) => this.viewBtns[n].classList.toggle('on', i === m));
  },

  refreshRows() { for (const show of Object.values(this.rows)) show(); this.markSwatch(); },

  // The yield stress the solver wants, from the height the panel shows.
  //
  // The slider is in centimetres of mound, and that is not a metaphor: a pile
  // of fluid stands until the shear at its base beats the yield stress, and at
  // unit density that shear is gravity times the height. So the yield stress
  // the solver needs for a mound h tall is exactly g*h, and the slider can say
  // "holds 6 cm" and mean it.
  //
  // It was a percentage of elastic strain first, and that was wrong by two
  // orders of magnitude: 8% of strain at the elasticity kissel wants came to a
  // yield of 67 against the ~1500 a 10 cm mound generates, so every material
  // spread into a flat puddle whatever the slider said. A number that cannot be
  // compared against gravity is a number nobody can set.
  // Measured, not derived: a slump of this volume settles to about a sixth of
  // the height the textbook h = yield/(rho*g) predicts. Some of that is the
  // norms in a von Mises criterion (the deviatoric Frobenius norm against a
  // shear yield carries a root two and a root three), and some is that a small
  // puddle is not the wide slab the textbook formula is about. The constant is
  // what makes the slider's centimetres mean roughly what they say, and the
  // sweep it came from is in the spec.
  YIELD_K: 4.0,

  applyHold() {
    const h = this.state.hold;
    SIM.params.yieldS = h >= 40 ? 1e9 : SIM.params.gravity * h * this.YIELD_K;

    // A material has to be able to reach its own yield while still inside a
    // sane elastic strain - the strain at yield is yield/(2*mu), and the solver
    // bounds the stored deformation at about 50%. Too soft and it simply never
    // yields and behaves as a solid, whatever the slider says. So the
    // elasticity is floored, and the slider shows where it was pushed to.
    if (SIM.params.yieldS < 1e8) {
      SIM.params.mu = Math.max(SIM.params.mu, SIM.params.yieldS * 3.2);
    }
    if (this.state.autoSubsteps) {
      // Explicit MPM is stable while dt * sound speed stays under about 0.4 of
      // a cell, and the sound speed is sqrt(lam + 2mu) at unit density. Solving
      // for the substeps a 60 Hz frame needs, with a little margin.
      const c = Math.sqrt(SIM.params.lam + 2 * SIM.params.mu);
      SIM.params.substeps = Math.max(4, Math.min(40, Math.ceil(c / 24 * 1.15)));
      if (this.rows.sub) this.rows.sub();
    }
  },

  applyPreset(name) {
    const p = this.presets[name];
    if (!p) return;
    this.state.preset = name;
    SIM.params.mu = p.mu;
    this.state.hold = Math.min(p.hold, 60);
    SIM.params.visc = p.visc;
    SIM.params.lam = p.lam;
    SIM.params.wallStick = p.stick;
    SIM.params.gravity = p.grav;
    RENDER.look.tint = p.tint.slice();
    RENDER.look.absorb = p.absorb;
    RENDER.look.roughness = p.rough;
    RENDER.look.refract = p.refract;
    RENDER.look.radius = p.radius;
    this.applyHold();
    for (const [n, b] of Object.entries(this.presetBtns)) b.classList.toggle('on', n === name);
    this.refreshRows();
  },

  applyQuality(name) {
    const q = this.quality[name];
    if (!q) return;
    this.state.quality = name;
    this.applyAuto();
    for (const [n, b] of Object.entries(this.qualityBtns)) b.classList.toggle('on', n === name);
    this.realloc({ gridN: q.gridN, maxParticles: q.maxParticles });
  },

  realloc(change) {
    Object.assign(SIM.params, change);
    try {
      SIM.allocate();
    } catch (e) {
      console.error(e);
      this.note = String(e.message || e);
      return;
    }
    RENDER.bindParticles(SIM.buf.pos, SIM.buf.vel);
    this.frameCamera();
    this.dropBlob();
    this.refreshRows();
  },

  // ---------------------------------------------------------------- input

  wireInput() {
    const c = document.getElementById('gfx');
    let drag = null, lastX = 0, lastY = 0;

    const handFromEvent = (ev) => {
      // The hand lives on the plane through the camera target facing the
      // camera, so it tracks the cursor predictably; Shift+wheel pushes that
      // plane nearer or further.
      const rect = c.getBoundingClientRect();
      const uv = [(ev.clientX - rect.left) / rect.width, (ev.clientY - rect.top) / rect.height];
      const ndc = [uv[0] * 2 - 1, 1 - uv[1] * 2];
      const b = RENDER.basis, L = RENDER.camData;
      const tanX = L[56], tanY = L[57];
      const dir = [
        b.f[0] + b.r[0] * ndc[0] * tanX + b.u[0] * ndc[1] * tanY,
        b.f[1] + b.r[1] * ndc[0] * tanX + b.u[1] * ndc[1] * tanY,
        b.f[2] + b.r[2] * ndc[0] * tanX + b.u[2] * ndc[1] * tanY,
      ];
      const t = RENDER.cam.dist + this.hand.depth;
      return [RENDER.eye[0] + dir[0] * t, RENDER.eye[1] + dir[1] * t, RENDER.eye[2] + dir[2] * t];
    };

    c.addEventListener('contextmenu', (e) => e.preventDefault());

    c.addEventListener('pointerdown', (ev) => {
      c.setPointerCapture(ev.pointerId);
      lastX = ev.clientX; lastY = ev.clientY;
      if (ev.button === 1 || (ev.button === 0 && ev.ctrlKey)) drag = 'pan';
      else if (ev.button === 2 || ev.altKey) drag = 'orbit';
      else { drag = 'hand'; this.hand.on = true; this.hand.pos = handFromEvent(ev); this.hand.prev = this.hand.pos; }
    });

    c.addEventListener('pointermove', (ev) => {
      const dx = ev.clientX - lastX, dy = ev.clientY - lastY;
      lastX = ev.clientX; lastY = ev.clientY;
      if (drag === 'orbit') {
        RENDER.cam.yaw -= dx * 0.006;
        RENDER.cam.pitch = Math.max(-1.35, Math.min(1.45, RENDER.cam.pitch + dy * 0.005));
      } else if (drag === 'pan') {
        const b = RENDER.basis, s = RENDER.cam.dist * 0.0016;
        for (let i = 0; i < 3; i++) RENDER.cam.target[i] += (-b.r[i] * dx + b.u[i] * dy) * s;
      } else if (drag === 'hand') {
        this.hand.pos = handFromEvent(ev);
      }
    });

    const endDrag = (ev) => {
      if (drag === 'hand') { this.hand.on = false; this.hand.vel = [0, 0, 0]; }
      drag = null;
      if (ev && ev.pointerId != null && c.hasPointerCapture(ev.pointerId)) c.releasePointerCapture(ev.pointerId);
    };
    c.addEventListener('pointerup', endDrag);
    c.addEventListener('pointercancel', endDrag);

    c.addEventListener('wheel', (ev) => {
      ev.preventDefault();
      if (ev.shiftKey) {
        this.hand.depth = Math.max(-RENDER.cam.dist * 0.8, Math.min(RENDER.cam.dist * 0.8,
          this.hand.depth + ev.deltaY * 0.08));
      } else {
        RENDER.cam.dist = Math.max(this.gridN() * 0.35, Math.min(this.gridN() * 6,
          RENDER.cam.dist * (1 + ev.deltaY * 0.0012)));
      }
    }, { passive: false });

    window.addEventListener('keydown', (ev) => {
      if (ev.repeat && ev.code !== 'KeyP') return;
      switch (ev.code) {
        case 'Space': this.state.paused = !this.state.paused; ev.preventDefault(); break;
        case 'KeyS': this.state.stepOnce = true; break;
        case 'KeyR': SIM.clear(); this.dropBlob(); break;
        case 'KeyD': this.dropBlob(); break;
        case 'KeyP': this.state.pourKey = true; break;
        case 'Digit1': this.setMode(0); break;
        case 'Digit2': this.setMode(1); break;
        case 'Digit3': this.setMode(2); break;
        case 'Digit4': this.setMode(3); break;
        case 'Digit5': this.setMode(4); break;
      }
    });
    window.addEventListener('keyup', (ev) => { if (ev.code === 'KeyP') this.state.pourKey = false; });
    window.addEventListener('blur', () => { this.state.pourKey = false; this.hand.on = false; });
  },

  // ----------------------------------------------------------- the frame

  loop(now) {
    const dt = 1 / 60;    // fixed, so the solver is stable and reproducible
    const p = this.perf;

    // One frame on the GPU at a time. Without this the loop submits whether or
    // not the last frame finished, the queue grows without bound, and what is
    // on the screen is a picture of where the simulation was some seconds ago -
    // which reads as "it is frozen" rather than "it is slow", and gets worse
    // the longer it runs. Skipping keeps the picture in step with the solver:
    // a slow machine runs the fluid in slow motion, honestly, and the panel
    // says so. The watchdog is for a device that never answers at all.
    if (p.inFlight) {
      if (now - p.started > 4000) p.inFlight = false;
      else return;
    }

    if (this.state.pouring || this.state.pourKey) this.pourTick();

    // The hand's velocity is how fast the cursor is dragging it through the
    // world, which is what lets it pull a strand rather than only push.
    if (this.hand.on && this.hand.pos) {
      const p = this.hand.pos, q = this.hand.prev || p;
      this.hand.vel = [(p[0] - q[0]) / dt, (p[1] - q[1]) / dt, (p[2] - q[2]) / dt];
      this.hand.prev = p.slice();
    }

    const world = {
      obstacle: this.obstacleVec(),
      mouse: this.hand.on && this.hand.pos
        ? [this.hand.pos[0], this.hand.pos[1], this.hand.pos[2], this.state.handRadius]
        : [0, 0, 0, 0],
      mouseVel: [this.hand.vel[0], this.hand.vel[1], this.hand.vel[2], this.state.handStrength],
    };

    if (!this.state.paused || this.state.stepOnce) {
      SIM.step(dt, world);
      this.state.stepOnce = false;
    }
    RENDER.draw(SIM.high, SIM.grid, world.obstacle);

    // The frame is measured where it ends, on the GPU, not where it was queued.
    p.inFlight = true;
    p.started = performance.now();
    this.device.queue.onSubmittedWorkDone().then(() => {
      p.inFlight = false;
      const done = performance.now();
      if (p.lastDone) {
        const ms = done - p.lastDone;
        this.govern(ms);
        this.fps.acc += ms; this.fps.n++;
        if (this.fps.acc > 500) {
          this.fps.value = 1000 / (this.fps.acc / this.fps.n);
          this.fps.acc = 0; this.fps.n = 0;
          this.showStats();
        }
      }
      p.lastDone = done;
    }).catch(() => { p.inFlight = false; });
  },

  // Save what is on the canvas to shots/<name> next to the page. Needs the
  // page to be served by serve.py; it is how a frame gets looked at properly,
  // and it is the only way the look can be checked at all where a screenshot
  // of the window is not available.
  async saveShot(name) {
    const c = document.getElementById('gfx');
    const blob = await new Promise((res) => c.toBlob(res, 'image/png'));
    if (!blob) throw new Error('the canvas gave no picture');
    const r = await fetch('/save/' + (name || 'shot.png'), { method: 'POST', body: blob });
    return { ok: r.ok, bytes: blob.size, name };
  },

  showStats() {
    const s = SIM.stats;
    const gpu = SIM.gpuMs();
    const needed = Math.ceil(Math.sqrt(SIM.params.lam + 2 * SIM.params.mu) / 24 * 1.15);
    const shaky = SIM.params.substeps < needed;
    const p = this.perf;
    const steps = this.AUTO_STEPS.length;
    const lines = [
      `<b>${this.fps.value.toFixed(0)}</b> fps · кадр <b>${p.frameMs.toFixed(0)}</b> мс` +
        (gpu ? ` · гпу <b>${(gpu + RENDER.gpuMs()).toFixed(0)}</b> мс` +
          ` <span style="font-size:10px">(решатель ${gpu.toFixed(1)} + картинка ${RENDER.gpuMs().toFixed(1)})</span>` : ''),
      `видеокарта <b>${this.gpu ? this.gpu.name : '?'}</b>` +
        (this.gpu && this.gpu.fallback
          ? ' <span class="bad">— программная, будет очень медленно</span>' : ''),
      `картинка ${RENDER.w}×${RENDER.h}` +
        (this.state.autoQuality
          ? ` · авто <b>${p.level + 1}</b>/${steps}` +
            (p.level ? ' <span style="font-size:10px">(убавлено, чтобы успевать)</span>' : '')
          : ' · авто выкл.'),
      `частиц <b>${s.live.toLocaleString('ru')}</b> из ${SIM.max.toLocaleString('ru')}` +
        ` · ${(SIM.bytes() / 1048576).toFixed(0)} МБ`,
      `масса <b>${s.mass.toFixed(0)}</b> · макс. скорость <b>${(s.maxSpeed || 0).toFixed(0)}</b>`,
      `сбросов <span class="${s.nan ? 'bad' : ''}"><b>${s.nan}</b></span>` +
        (s.nan && s.why ? ` <span style="font-size:10px">(поз ${s.why.pos} · скор ${s.why.vel}` +
          ` · деформ ${s.why.defo} · предел ${s.why.fast})</span>` : ''),
      p.solverBound && p.frameMs > this.TARGET_MS * 1.25
        ? '<span class="bad">не успевает решатель</span>' +
          ' <span style="font-size:10px">— убавьте частиц, подшаги или сетку</span>'
        : '',
      this.state.paused ? '<b>пауза</b>' : '',
      shaky ? `<span class="bad">подшагов мало: нужно ≥ ${needed}</span>` : '',
      this.note ? `<span class="bad">${this.note}</span>` : '',
    ].filter(Boolean);
    document.getElementById('stats').innerHTML = lines.join('<br>');
  },
};
