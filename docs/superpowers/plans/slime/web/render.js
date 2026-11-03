// The host side of the rendering: textures, pipelines, and the pass order.
//
// shadow -> background -> particle depth -> thickness -> filter x2 -> composite
//
// Each pass gets its own bind group layout holding only what its entry point
// actually uses, because a texture cannot be a render attachment and a sampled
// resource at the same time: one shared layout would make the filter pass
// illegal.

const RENDER = {
  device: null,
  format: null,
  canvas: null,
  ctx: null,
  w: 0, h: 0,

  look: {
    radius: 0.85,          // particle radius in cells, for the surface
    smooth: 2,             // filter iterations
    filterWindow: 1.6,     // cells: a sample further than this is left out
    roughness: 0.22,
    refract: 1.0,
    shadow: 1.0,
    opacity: 1.2,
    absorb: 0.32,
    tint: [0.42, 0.78, 0.30],
    mode: 0,               // 0 shaded, 1 points, 2 depth, 3 normals, 4 thickness
    fov: 42,
    // The pixels cost more than the particles here. The device pixel ratio is
    // capped rather than honoured (a 1.5x display is 2.25x the fragments for
    // nothing a fluid surface shows), the thickness is rendered small because
    // it is a low-frequency quantity, and the filter radius follows the
    // resolution so the cost of smoothing does not grow with the window size.
    dpr: 1.0,
    maxPixels: 2400000,    // the ceiling the governor moves; 0 is no ceiling
    thickDiv: 2,
  },

  filterRadius() {
    return Math.max(3, Math.min(9, Math.round(this.h / 160)));
  },

  cam: { yaw: 0.72, pitch: 0.42, dist: 190, target: [48, 20, 48] },

  camData: new Float32Array(76),
  tex: {},
  pipe: {},

  async init(device, canvas, filterable) {
    this.device = device;
    this.canvas = canvas;
    this.format = navigator.gpu.getPreferredCanvasFormat();
    this.ctx = canvas.getContext('webgpu');
    this.ctx.configure({ device, format: this.format, alphaMode: 'opaque' });

    const mod = device.createShaderModule({ code: RENDER_WGSL, label: 'render' });
    const info = await mod.getCompilationInfo();
    for (const m of info.messages) {
      const where = `render.wgsl:${m.lineNum}:${m.linePos}`;
      if (m.type === 'error') console.error(where, m.message);
      else console.warn(where, m.message);
    }
    if (info.messages.some((m) => m.type === 'error')) {
      throw new Error('the render shader did not compile - see the console');
    }
    this.mod = mod;

    // One sampler everywhere. Linear needs float32-filterable for the r32float
    // depth targets; without it, nearest, which costs a little aliasing in the
    // refraction and nothing else.
    this.samp = device.createSampler({
      magFilter: filterable ? 'linear' : 'nearest',
      minFilter: filterable ? 'linear' : 'nearest',
      addressModeU: 'clamp-to-edge',
      addressModeV: 'clamp-to-edge',
    });

    this.camBuf = device.createBuffer({
      size: this.camData.byteLength,
      usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST, label: 'cam',
    });
    // Two axis uniforms rather than one rewritten between passes:
    // queue.writeBuffer is ordered on the queue, not inside the encoder, so a
    // rewrite would land before either pass ran.
    this.axisBuf = [0, 1].map((i) => device.createBuffer({
      size: 16, usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST, label: `axis${i}`,
    }));

    const U = GPUShaderStage.VERTEX | GPUShaderStage.FRAGMENT;
    const F = GPUShaderStage.FRAGMENT;

    // group 0: the camera, with the particle buffers where a pass draws them.
    this.l0cam = device.createBindGroupLayout({
      entries: [{ binding: 0, visibility: U, buffer: { type: 'uniform' } }],
    });
    this.l0parts = device.createBindGroupLayout({
      entries: [
        { binding: 0, visibility: U, buffer: { type: 'uniform' } },
        { binding: 1, visibility: U, buffer: { type: 'read-only-storage' } },
        { binding: 2, visibility: U, buffer: { type: 'read-only-storage' } },
      ],
    });
    // group 1, one layout a pass.
    this.l1bg = device.createBindGroupLayout({
      entries: [
        { binding: 0, visibility: F, sampler: { type: filterable ? 'filtering' : 'non-filtering' } },
        { binding: 1, visibility: F, texture: { sampleType: filterable ? 'float' : 'unfilterable-float' } },
      ],
    });
    this.l1filter = device.createBindGroupLayout({
      entries: [
        { binding: 0, visibility: F, sampler: { type: filterable ? 'filtering' : 'non-filtering' } },
        { binding: 2, visibility: F, texture: { sampleType: filterable ? 'float' : 'unfilterable-float' } },
      ],
    });
    this.l1comp = device.createBindGroupLayout({
      entries: [
        { binding: 0, visibility: F, sampler: { type: filterable ? 'filtering' : 'non-filtering' } },
        ...[3, 4, 5, 6].map((binding) => ({
          binding, visibility: F, texture: { sampleType: filterable ? 'float' : 'unfilterable-float' },
        })),
      ],
    });
    this.l2axis = device.createBindGroupLayout({
      entries: [{ binding: 0, visibility: F, buffer: { type: 'uniform' } }],
    });

    const add = { color: { srcFactor: 'one', dstFactor: 'one', operation: 'add' },
                  alpha: { srcFactor: 'one', dstFactor: 'one', operation: 'add' } };

    this.pipe.shadow = device.createRenderPipeline({
      label: 'shadow',
      layout: device.createPipelineLayout({ bindGroupLayouts: [this.l0parts] }),
      vertex: { module: mod, entryPoint: 'shadowVert' },
      fragment: { module: mod, entryPoint: 'shadowFrag', targets: [{ format: 'r16float', blend: add }] },
      primitive: { topology: 'triangle-list' },
    });

    this.pipe.bg = device.createRenderPipeline({
      label: 'bg',
      layout: device.createPipelineLayout({ bindGroupLayouts: [this.l0cam, this.l1bg] }),
      vertex: { module: mod, entryPoint: 'fsVert' },
      fragment: { module: mod, entryPoint: 'bgFrag',
                  targets: [{ format: 'rgba16float' }, { format: 'r32float' }] },
      primitive: { topology: 'triangle-list' },
    });

    this.pipe.depth = device.createRenderPipeline({
      label: 'fluid depth',
      layout: device.createPipelineLayout({ bindGroupLayouts: [this.l0parts] }),
      vertex: { module: mod, entryPoint: 'sphereVert' },
      fragment: { module: mod, entryPoint: 'depthFrag', targets: [{ format: 'r32float' }] },
      primitive: { topology: 'triangle-list' },
      depthStencil: { format: 'depth32float', depthWriteEnabled: true, depthCompare: 'less' },
    });

    this.pipe.thick = device.createRenderPipeline({
      label: 'thickness',
      layout: device.createPipelineLayout({ bindGroupLayouts: [this.l0parts] }),
      vertex: { module: mod, entryPoint: 'sphereVert' },
      fragment: { module: mod, entryPoint: 'thickFrag', targets: [{ format: 'r16float', blend: add }] },
      primitive: { topology: 'triangle-list' },
    });

    this.pipe.filter = device.createRenderPipeline({
      label: 'filter',
      layout: device.createPipelineLayout({ bindGroupLayouts: [this.l0cam, this.l1filter, this.l2axis] }),
      vertex: { module: mod, entryPoint: 'fsVert' },
      fragment: { module: mod, entryPoint: 'filterFrag', targets: [{ format: 'r32float' }] },
      primitive: { topology: 'triangle-list' },
    });

    this.pipe.composite = device.createRenderPipeline({
      label: 'composite',
      layout: device.createPipelineLayout({ bindGroupLayouts: [this.l0cam, this.l1comp] }),
      vertex: { module: mod, entryPoint: 'fsVert' },
      fragment: { module: mod, entryPoint: 'compositeFrag', targets: [{ format: this.format }] },
      primitive: { topology: 'triangle-list' },
    });

    this.pipe.points = device.createRenderPipeline({
      label: 'points',
      layout: device.createPipelineLayout({ bindGroupLayouts: [this.l0parts] }),
      vertex: { module: mod, entryPoint: 'pointVert' },
      fragment: { module: mod, entryPoint: 'pointFrag', targets: [{ format: this.format }] },
      primitive: { topology: 'triangle-list' },
      depthStencil: { format: 'depth32float', depthWriteEnabled: true, depthCompare: 'less' },
    });

    this.bindCam = device.createBindGroup({
      layout: this.l0cam, entries: [{ binding: 0, resource: { buffer: this.camBuf } }],
    });
    this.bindAxis = [0, 1].map((i) => device.createBindGroup({
      layout: this.l2axis, entries: [{ binding: 0, resource: { buffer: this.axisBuf[i] } }],
    }));

    this.shadowSize = 512;
    this.tex.shadow = device.createTexture({
      size: [this.shadowSize, this.shadowSize], format: 'r16float',
      usage: GPUTextureUsage.RENDER_ATTACHMENT | GPUTextureUsage.TEXTURE_BINDING, label: 'shadow',
    });
    this.bindShadow = device.createBindGroup({
      layout: this.l1bg,
      entries: [
        { binding: 0, resource: this.samp },
        { binding: 1, resource: this.tex.shadow.createView() },
      ],
    });
  },

  // Called whenever the particle buffers are rebuilt.
  bindParticles(posBuf, velBuf) {
    this.bindParts = this.device.createBindGroup({
      layout: this.l0parts,
      entries: [
        { binding: 0, resource: { buffer: this.camBuf } },
        { binding: 1, resource: { buffer: posBuf } },
        { binding: 2, resource: { buffer: velBuf } },
      ],
    });
  },

  resize() {
    const d = this.device;
    let dpr = Math.min(window.devicePixelRatio || 1, this.look.dpr);
    // A hard ceiling on the fragments, not only on the ratio: a maximized window
    // on a 4K screen asks for eight megapixels, and every screen-space pass here
    // is paid for per pixel. The surface is low frequency, so a canvas scaled up
    // by a few percent costs nothing anybody can see, where the fragments do.
    const cw = Math.max(1, this.canvas.clientWidth), ch = Math.max(1, this.canvas.clientHeight);
    const cap = this.look.maxPixels || 0;
    if (cap > 0 && cw * ch * dpr * dpr > cap) dpr = Math.sqrt(cap / (cw * ch));
    const w = Math.max(16, Math.floor(cw * dpr));
    const h = Math.max(16, Math.floor(ch * dpr));
    const td = Math.max(1, this.look.thickDiv | 0);
    if (w === this.w && h === this.h && td === this._td) return;
    this._td = td;
    this.w = w; this.h = h;
    this.canvas.width = w; this.canvas.height = h;

    for (const k of ['bgCol', 'bgDep', 'fdA', 'fdB', 'thick', 'depthBuf']) {
      if (this.tex[k]) this.tex[k].destroy();
    }
    const RA = GPUTextureUsage.RENDER_ATTACHMENT;
    const TB = GPUTextureUsage.TEXTURE_BINDING;
    this.tex.bgCol = d.createTexture({ size: [w, h], format: 'rgba16float', usage: RA | TB, label: 'bgCol' });
    this.tex.bgDep = d.createTexture({ size: [w, h], format: 'r32float', usage: RA | TB, label: 'bgDep' });
    this.tex.fdA = d.createTexture({ size: [w, h], format: 'r32float', usage: RA | TB, label: 'fdA' });
    this.tex.fdB = d.createTexture({ size: [w, h], format: 'r32float', usage: RA | TB, label: 'fdB' });
    // Thickness is a low-frequency quantity, so it is rendered small: it is the
    // one pass that touches every particle without a depth test.
    this.tw = Math.max(8, Math.floor(w / td)); this.th = Math.max(8, Math.floor(h / td));
    this.tex.thick = d.createTexture({ size: [this.tw, this.th], format: 'r16float', usage: RA | TB, label: 'thick' });
    this.tex.depthBuf = d.createTexture({ size: [w, h], format: 'depth32float', usage: RA, label: 'depthBuf' });

    const view = (k) => this.tex[k].createView();
    this.bindFilter = [
      d.createBindGroup({ layout: this.l1filter, entries: [
        { binding: 0, resource: this.samp }, { binding: 2, resource: view('fdA') }] }),
      d.createBindGroup({ layout: this.l1filter, entries: [
        { binding: 0, resource: this.samp }, { binding: 2, resource: view('fdB') }] }),
    ];
    this.bindComp = d.createBindGroup({
      layout: this.l1comp,
      entries: [
        { binding: 0, resource: this.samp },
        { binding: 3, resource: view('bgCol') },
        { binding: 4, resource: view('bgDep') },
        { binding: 5, resource: view('fdA') },
        { binding: 6, resource: view('thick') },
      ],
    });
  },

  // --- the camera, built by hand so there is no general matrix inverse to get
  // wrong: a view matrix of a rigid frame inverts to its transpose plus the eye.
  writeCam(gridN, obstacle) {
    const c = this.cam;
    const t = c.target;
    const cp = Math.cos(c.pitch), sp = Math.sin(c.pitch);
    const eye = [
      t[0] + c.dist * cp * Math.sin(c.yaw),
      t[1] + c.dist * sp,
      t[2] + c.dist * cp * Math.cos(c.yaw),
    ];
    // the view basis
    let f = [t[0] - eye[0], t[1] - eye[1], t[2] - eye[2]];
    const fl = Math.hypot(f[0], f[1], f[2]) || 1; f = f.map((v) => v / fl);
    // right = normalize(cross(forward, worldUp)) = normalize(-f.z, 0, f.x)
    let r = [-f[2], 0, f[0]];
    const rl = Math.hypot(r[0], r[1], r[2]) || 1; r = r.map((v) => v / rl);
    // up = cross(right, forward)
    const u = [
      r[1] * f[2] - r[2] * f[1],
      r[2] * f[0] - r[0] * f[2],
      r[0] * f[1] - r[1] * f[0],
    ];

    const D = this.camData;
    // view: columns are (r, u, -f) transposed, with the translation
    const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
    D[0] = r[0]; D[1] = u[0]; D[2] = -f[0]; D[3] = 0;
    D[4] = r[1]; D[5] = u[1]; D[6] = -f[1]; D[7] = 0;
    D[8] = r[2]; D[9] = u[2]; D[10] = -f[2]; D[11] = 0;
    D[12] = -dot(r, eye); D[13] = -dot(u, eye); D[14] = dot(f, eye); D[15] = 1;

    const aspect = this.w / Math.max(this.h, 1);
    const near = 1.0, far = Math.max(600, gridN * 8);
    const fy = 1 / Math.tan((this.look.fov * Math.PI / 180) / 2);
    const nf = 1 / (near - far);
    for (let i = 16; i < 32; i++) D[i] = 0;
    D[16] = fy / aspect; D[21] = fy; D[26] = far * nf; D[27] = -1; D[30] = far * near * nf;

    // invView: the basis as columns, eye in the translation
    D[32] = r[0]; D[33] = r[1]; D[34] = r[2]; D[35] = 0;
    D[36] = u[0]; D[37] = u[1]; D[38] = u[2]; D[39] = 0;
    D[40] = -f[0]; D[41] = -f[1]; D[42] = -f[2]; D[43] = 0;
    D[44] = eye[0]; D[45] = eye[1]; D[46] = eye[2]; D[47] = 1;

    D[48] = eye[0]; D[49] = eye[1]; D[50] = eye[2]; D[51] = 0;
    D[52] = this.w; D[53] = this.h; D[54] = 1 / this.w; D[55] = 1 / this.h;
    const tanY = Math.tan((this.look.fov * Math.PI / 180) / 2);
    D[56] = tanY * aspect; D[57] = tanY; D[58] = near; D[59] = far;
    D[60] = this.look.radius; D[61] = gridN; D[62] = performance.now() / 1000; D[63] = this.look.mode;
    D[64] = obstacle[0]; D[65] = obstacle[1]; D[66] = obstacle[2]; D[67] = obstacle[3];
    D[68] = this.look.tint[0]; D[69] = this.look.tint[1]; D[70] = this.look.tint[2]; D[71] = this.look.absorb;
    D[72] = this.look.roughness; D[73] = this.look.refract; D[74] = this.look.shadow; D[75] = this.look.opacity;

    this.device.queue.writeBuffer(this.camBuf, 0, D);
    this.eye = eye;
    this.basis = { r, u, f };
    this.far = far;
  },

  draw(count, gridN, obstacle) {
    const d = this.device;
    this.resize();
    this.writeCam(gridN, obstacle);
    const far = this.far;
    d.queue.writeBuffer(this.axisBuf[0], 0, new Float32Array([1, 0, this.filterRadius(), this.look.filterWindow]));
    d.queue.writeBuffer(this.axisBuf[1], 0, new Float32Array([0, 1, this.filterRadius(), this.look.filterWindow]));

    const enc = d.createCommandEncoder();
    const view = (k) => this.tex[k].createView();
    const clear = (v) => ({ r: v, g: 0, b: 0, a: 0 });

    // 1. the contact shadow, top down
    {
      const p = enc.beginRenderPass({
        colorAttachments: [{ view: view('shadow'), clearValue: clear(0), loadOp: 'clear', storeOp: 'store' }],
      });
      p.setPipeline(this.pipe.shadow);
      p.setBindGroup(0, this.bindParts);
      if (count > 0) p.draw(6, count);
      p.end();
    }

    // 2. the background
    {
      const p = enc.beginRenderPass({
        colorAttachments: [
          { view: view('bgCol'), clearValue: { r: 0, g: 0, b: 0, a: 1 }, loadOp: 'clear', storeOp: 'store' },
          { view: view('bgDep'), clearValue: clear(far), loadOp: 'clear', storeOp: 'store' },
        ],
      });
      p.setPipeline(this.pipe.bg);
      p.setBindGroup(0, this.bindCam);
      p.setBindGroup(1, this.bindShadow);
      p.draw(3);
      p.end();
    }

    // 3. the particle depth
    {
      const p = enc.beginRenderPass({
        colorAttachments: [{ view: view('fdA'), clearValue: clear(far), loadOp: 'clear', storeOp: 'store' }],
        depthStencilAttachment: {
          view: view('depthBuf'), depthClearValue: 1.0, depthLoadOp: 'clear', depthStoreOp: 'store',
        },
      });
      p.setPipeline(this.pipe.depth);
      p.setBindGroup(0, this.bindParts);
      if (count > 0) p.draw(6, count);
      p.end();
    }

    // 4. the thickness, half size, every particle
    {
      const p = enc.beginRenderPass({
        colorAttachments: [{ view: view('thick'), clearValue: clear(0), loadOp: 'clear', storeOp: 'store' }],
      });
      p.setPipeline(this.pipe.thick);
      p.setBindGroup(0, this.bindParts);
      if (count > 0) p.draw(6, count);
      p.end();
    }

    // 5. the narrow-range filter, separable, ping-ponged
    for (let i = 0; i < Math.max(0, this.look.smooth | 0); i++) {
      for (let axis = 0; axis < 2; axis++) {
        const src = axis === 0 ? 0 : 1;
        const dst = axis === 0 ? 'fdB' : 'fdA';
        const p = enc.beginRenderPass({
          colorAttachments: [{ view: view(dst), clearValue: clear(far), loadOp: 'clear', storeOp: 'store' }],
        });
        p.setPipeline(this.pipe.filter);
        p.setBindGroup(0, this.bindCam);
        p.setBindGroup(1, this.bindFilter[src]);
        p.setBindGroup(2, this.bindAxis[axis]);
        p.draw(3);
        p.end();
      }
    }

    // 6. composite to the canvas
    const canvasView = this.ctx.getCurrentTexture().createView();
    {
      const p = enc.beginRenderPass({
        colorAttachments: [{ view: canvasView, clearValue: { r: 0, g: 0, b: 0, a: 1 }, loadOp: 'clear', storeOp: 'store' }],
      });
      p.setPipeline(this.pipe.composite);
      p.setBindGroup(0, this.bindCam);
      p.setBindGroup(1, this.bindComp);
      p.draw(3);
      p.end();
    }

    // 7. the points debug view, over the background
    if ((this.look.mode | 0) === 1) {
      const p = enc.beginRenderPass({
        colorAttachments: [{ view: canvasView, loadOp: 'load', storeOp: 'store' }],
        depthStencilAttachment: {
          view: view('depthBuf'), depthClearValue: 1.0, depthLoadOp: 'clear', depthStoreOp: 'store',
        },
      });
      p.setPipeline(this.pipe.points);
      p.setBindGroup(0, this.bindParts);
      if (count > 0) p.draw(6, count);
      p.end();
    }

    d.queue.submit([enc.finish()]);
  },
};
