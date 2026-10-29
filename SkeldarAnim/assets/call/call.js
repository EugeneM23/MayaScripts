// The call page (spec docs/superpowers/specs/2026-10-22-chat-calls-design.md): a WebRTC mesh driven
// by Python through the QWebChannel object `bridge`. The joiner offers; the others answer.
"use strict";
const S = { me: null, names: {}, colours: {}, ice: [], peers: new Map(), local: null, camTrack: null, screenTrack: null,
            mic: true, cam: false, screen: false, nomic: "",
            devices: { mic: "", cam: "", mic_label: "", cam_label: "" }, list: { mics: [], cams: [] },
            error: "", note: "", bridge: null, audio: null, levels: new Map(), timer: null, statsTimer: null,
            left: new Set(), ended: false,
            capture: null, stalled: false, lastFrame: 0,          // what is captured, and whether it still moves
            stage: null, stageTile: null, stageGone: false,       // the screen's own window
            drawing: false, strokes: new Map(), stroke: null, inkTimer: null, inkOut: null };
const LOST_MS = 20000;
const SPEAK = 0.035;
// A stroke over the shared screen holds, then fades: about three seconds in all («тают через пару
// секунд»). Points are batched before they are sent; a capture that hands out no frame for
// STALL_MS while its track is live has stalled (the window takes it again).
const HOLD_MS = 1200;
const FADE_MS = 1800;
const SEND_MS = 60;
const STALL_MS = 5000;

function send(to, data) { if (S.bridge) S.bridge.signal(to, JSON.stringify(data)); }
function others(data) { for (const p of S.peers.values()) send(p.uid, data); }

function snapshot() {
  const peers = {};
  for (const p of S.peers.values()) {
    peers[p.uid] = { state: p.pc.connectionState, speaking: !!p.speaking, mic: p.mic, cam: p.cam,
                     screen: p.screen, lost: !!(p.failedAt && Date.now() - p.failedAt > LOST_MS), bytes: p.bytes };
  }
  return { me: S.me, mic: S.mic, cam: S.cam, screen: S.screen, nomic: S.nomic, error: S.error, note: S.note,
           devices: S.list, peers, speaking: !!S.speakingMe,
           capture: S.capture, stalled: S.stalled, drawing: S.drawing,
           stage: !!S.stage, wants_stage: wantsStage() };
}
let reportQueued = false;
function report() {
  if (reportQueued) return;
  reportQueued = true;
  setTimeout(() => { reportQueued = false; if (S.bridge) S.bridge.state(JSON.stringify(snapshot())); }, 30);
}
function note(text) {
  S.note = text || "";
  const el = document.getElementById("note");
  el.textContent = S.note; el.classList.toggle("on", !!S.note);
  report();
}

// ------------------------------------------------------------------ tiles
function initials(uid) {
  const name = S.names[uid] || uid || "?";
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => [...w][0].toUpperCase()).join("");
}
function tile(uid) {
  // A staged tile lives in the other window's document. It is held by the element itself, never
  // looked up through the stage window: Qt re-hosts that window in a view of ours, and the handle
  // requestWindow answered no longer reaches the document the tile moved into (measured).
  let t = document.getElementById("t-" + uid)
          || (S.stageTile && S.stageTile.id === "t-" + uid ? S.stageTile : null);
  if (!t) {
    t = document.createElement("div");
    t.className = "tile nocam"; t.id = "t-" + uid;
    t.innerHTML = '<video autoplay playsinline></video><canvas class="ink"></canvas>' +
                  '<button class="pen" title="Рисовать по экрану">&#x270E;</button>' +
                  '<div class="face"><span></span></div>' +
                  '<div class="name"><b></b><span class="muted">&#x1F507;</span></div><div class="lost">нет соединения</div>';
    document.getElementById("grid").appendChild(t);
    armInk(t);
  }
  t.querySelector(".face span").textContent = initials(uid);
  t.querySelector(".name b").textContent = uid === S.me ? (S.names[uid] || "Вы") + " (вы)" : (S.names[uid] || uid);
  layout();
  return t;
}
// The picture and the voice are played by elements of their OWN. A <video> whose MediaStream
// carries a live video track that has never delivered a frame stands at readyState 0 and renders
// nothing at all - not the picture and not the audio track beside it (measured 2026-10-29: in a
// voice call b's tile for a gave 0.000 s of playback in four seconds while a's voice was arriving;
// the moment a frame came - a camera, a shared screen - it played, which is the animator's «слышно
// когда шарим рабочий стол»). So a remote voice goes to an <audio> of its own, and that element
// lives outside the tiles: a tile travels into the stage window, and what is heard must not depend
// on where the picture lives.
function sink(uid) {
  let el = document.getElementById("s-" + uid);
  if (!el) {
    el = document.createElement("audio");
    el.id = "s-" + uid;
    el.autoplay = true;
    document.getElementById("sinks").appendChild(el);
  }
  return el;
}
function dropSink(uid) {
  const el = document.getElementById("s-" + uid);
  if (el) { el.srcObject = null; el.remove(); }
}
function wear(el, tracks, muted) {
  // the element is left alone while it already holds these very tracks: setting srcObject again
  // rebuilds the player, and the picture blinks
  if (!el) return;
  const have = el.srcObject ? el.srcObject.getTracks() : [];
  const same = have.length === tracks.length && tracks.every((t) => have.indexOf(t) >= 0);
  if (!same) el.srcObject = tracks.length ? new MediaStream(tracks) : null;
  el.muted = !!muted;
  if (tracks.length) el.play().catch(() => {});
}
function showStream(uid, stream, mine) {
  wear(tile(uid).querySelector("video"), stream.getVideoTracks(), true);
  if (!mine) wear(sink(uid), stream.getAudioTracks(), false);
}
function setTile(uid, flags) {
  const t = tile(uid);
  for (const [cls, on] of Object.entries(flags)) t.classList.toggle(cls, !!on);
  layout();
}
function layout() {
  // A shared screen takes the whole top row, everybody else a strip under it. The tiles are placed
  // by hand: left to the grid's auto-placement, a screen tile that came after a camera tile could
  // not fit beside it and was pushed into the 96 px strip - a sliver.
  const g = document.getElementById("grid");
  const tiles = [...g.children];
  const screens = tiles.filter((t) => t.classList.contains("screen"));
  const rest = tiles.filter((t) => !t.classList.contains("screen"));
  for (const t of tiles) { t.style.gridColumn = ""; t.style.gridRow = ""; }
  if (!screens.length) {
    g.style.gridTemplateColumns = ""; g.style.gridTemplateRows = "";
    g.className = "n" + Math.min(4, Math.max(1, tiles.length));
    return;
  }
  g.className = "focus";
  const cols = screens.length * Math.max(1, rest.length);
  g.style.gridTemplateColumns = "repeat(" + cols + ", 1fr)";
  g.style.gridTemplateRows = rest.length ? "1fr 96px" : "1fr";
  screens.forEach((t, i) => {
    const w = cols / screens.length;
    t.style.gridRow = "1"; t.style.gridColumn = (1 + i * w) + " / span " + w;
  });
  rest.forEach((t, i) => {
    const w = cols / rest.length;
    t.style.gridRow = "2"; t.style.gridColumn = (1 + i * w) + " / span " + w;
  });
}
function dropTile(uid) {
  if (S.stageTile && S.stageTile.id === "t-" + uid) { closeStage(); }
  const t = document.getElementById("t-" + uid);
  if (t) t.remove();
  dropSink(uid);
  layout();
}

// ------------------------------------------------------------------ the screen's own window
// A shared screen does not belong in the strip under the cameras («камеры в отдельном окне, а
// стрим экрана в своем»). The tile is MOVED into a Document Picture-in-Picture window - the same
// <video>, so the media is neither captured nor encoded a second time - and the grid is left with
// the cameras alone. Qt hands that window to the Python side through newWindowRequested, which
// frames it like the rest of our interface. requestWindow wants a user activation; the window
// synthesises a click into the page just before it sends `stage`.
function screenTile() {
  const here = document.querySelector(".tile.screen");
  if (here) return here;
  return S.stageTile && S.stageTile.classList.contains("screen") ? S.stageTile : null;
}
function wantsStage() {
  return !!(document.querySelector(".tile.screen") && !S.stage && !S.stageGone && "documentPictureInPicture" in window);
}
function stageStyles(w) {
  for (const s of document.querySelectorAll("style")) {
    const copy = w.document.createElement("style");
    copy.textContent = s.textContent;
    w.document.head.appendChild(copy);
  }
}
async function openStage() {
  const t = document.querySelector(".tile.screen");
  if (!t || S.stage || !("documentPictureInPicture" in window)) return;
  let w;
  try {
    w = await documentPictureInPicture.requestWindow({ width: 960, height: 560 });
  } catch (e) {
    S.stageGone = true;                       // no window: the screen stays in the grid
    report();
    return;
  }
  S.stage = w;
  S.stageTile = t;
  stageStyles(w);
  w.document.body.className = "stage";
  w.document.body.appendChild(t);             // the live video travels with the tile
  armInk(t);
  w.addEventListener("pagehide", () => { if (S.stage === w) { S.stage = null; takeBack(); } });
  layout();
  report();
}
function takeBack() {
  const t = S.stageTile;
  S.stageTile = null;
  if (t) {
    document.getElementById("grid").appendChild(t);
    armInk(t);
  }
  layout();
  report();
}
function closeStage() {
  const w = S.stage;
  if (!w && !S.stageTile) return;
  S.stage = null;
  takeBack();
  if (w) { try { w.close(); } catch (e) { /* already gone */ } }
  report();
}

// ------------------------------------------------------------------ drawing over the screen
// Everyone may draw, the sharer included. A stroke travels in the frame's own coordinates (0..1),
// so it lands on the same pixel of the shared screen whatever the window's size, and is drawn in
// its author's colour. Points go out through the call's live relay, batched.
function inkWindow(el) { return (el.ownerDocument.defaultView) || window; }
function videoBox(t) {
  // Where the picture really is inside the tile: a screen tile letterboxes (object-fit: contain).
  const v = t.querySelector("video"), r = v.getBoundingClientRect();
  const vw = v.videoWidth, vh = v.videoHeight;
  if (!vw || !vh) return { x: r.left, y: r.top, w: r.width, h: r.height };
  const s = Math.min(r.width / vw, r.height / vh);
  return { x: r.left + (r.width - vw * s) / 2, y: r.top + (r.height - vh * s) / 2, w: vw * s, h: vh * s };
}
function armInk(t) {
  if (!t) return;
  const c = t.querySelector("canvas.ink");
  const pen = t.querySelector("button.pen");
  if (!c || c.__armed === t.ownerDocument) return;   // re-armed when the tile changes document
  c.__armed = t.ownerDocument;
  pen.onclick = (e) => { e.preventDefault(); e.stopPropagation(); setDrawing(!S.drawing); };
  const at = (e) => {
    const b = videoBox(t);
    if (!b.w || !b.h) return null;
    return [(e.clientX - b.x) / b.w, (e.clientY - b.y) / b.h];
  };
  c.onpointerdown = (e) => {
    if (!S.drawing || S.stroke) return;       // a second press while a stroke is open is no stroke
    const p = at(e);
    if (!p) return;
    c.setPointerCapture(e.pointerId);
    S.stroke = { id: S.me + ":" + Date.now(), uid: S.me, colour: myColour(), pts: [p], at: Date.now(), done: false };
    S.strokes.set(S.stroke.id, S.stroke);
    S.inkOut = { id: S.stroke.id, c: S.stroke.colour, pts: [p] };
    paintInk();
  };
  c.onpointermove = (e) => {
    if (!S.drawing || !S.stroke) return;
    const p = at(e);
    if (!p) return;
    S.stroke.pts.push(p);
    S.stroke.at = Date.now();
    if (S.inkOut) S.inkOut.pts.push(p);
    flushInk(false);
    paintInk();
  };
  const up = () => {
    if (!S.stroke) return;
    S.stroke.done = true;
    S.stroke.at = Date.now();
    flushInk(true);
    S.stroke = null;
  };
  // No pointerleave: the canvas holds the pointer, so a drag that runs past the picture's edge
  // keeps drawing and comes back, as it should - and the stroke ends where the button does.
  c.onpointerup = up;
  c.onpointercancel = up;
  paintInk();
}
function myColour() { return S.colours[S.me] || "#c0703a"; }
function setDrawing(on) {
  S.drawing = !!on;
  const t = screenTile();
  if (t) t.classList.toggle("drawing", S.drawing);
  if (!S.drawing && S.stroke) { S.stroke.done = true; flushInk(true); S.stroke = null; }
  report();
}
function flushInk(end) {
  const out = S.inkOut;
  if (!out) return;
  const now = Date.now();
  if (!end && now - (out.sent || 0) < SEND_MS) return;
  out.sent = now;
  if (out.pts.length || end) others({ draw: { id: out.id, c: out.c, pts: out.pts, end: !!end } });
  out.pts = [];
  if (end) S.inkOut = null;
}
function ink(from, d) {
  if (!d || !d.id) return;
  let s = S.strokes.get(d.id);
  if (!s) {
    s = { id: d.id, uid: from, colour: d.c || S.colours[from] || "#c0703a", pts: [], at: Date.now(), done: false };
    S.strokes.set(d.id, s);
  }
  for (const p of d.pts || []) s.pts.push(p);
  s.at = Date.now();
  if (d.end) s.done = true;
  paintInk();
}
function strokeAlpha(s, now) {
  const age = now - s.at;
  if (!s.done || age < HOLD_MS) return 1;
  return Math.max(0, 1 - (age - HOLD_MS) / FADE_MS);
}
function paintInk() {
  const t = screenTile();
  if (!t) { S.strokes.clear(); return; }
  const c = t.querySelector("canvas.ink");
  if (!c) return;
  const w = inkWindow(c);
  const dpr = w.devicePixelRatio || 1;
  const r = c.getBoundingClientRect();
  const cw = Math.max(1, Math.round(r.width * dpr)), ch = Math.max(1, Math.round(r.height * dpr));
  if (c.width !== cw || c.height !== ch) { c.width = cw; c.height = ch; }
  const g = c.getContext("2d");
  g.setTransform(1, 0, 0, 1, 0, 0);
  g.clearRect(0, 0, c.width, c.height);
  const b = videoBox(t), now = Date.now();
  let alive = false;
  for (const [id, s] of [...S.strokes]) {
    const a = strokeAlpha(s, now);
    if (a <= 0) { S.strokes.delete(id); continue; }
    alive = true;
    if (s.pts.length < 1) continue;
    g.globalAlpha = a;
    g.strokeStyle = s.colour;
    g.lineWidth = Math.max(2, 0.004 * b.w) * dpr;
    g.lineCap = "round";
    g.lineJoin = "round";
    g.beginPath();
    s.pts.forEach((p, i) => {
      const x = (b.x + p[0] * b.w - r.left) * dpr, y = (b.y + p[1] * b.h - r.top) * dpr;
      if (i) g.lineTo(x, y); else g.moveTo(x, y);
    });
    if (s.pts.length === 1) {
      const x = (b.x + s.pts[0][0] * b.w - r.left) * dpr, y = (b.y + s.pts[0][1] * b.h - r.top) * dpr;
      g.moveTo(x, y); g.lineTo(x + 0.01, y);
    }
    g.stroke();
  }
  g.globalAlpha = 1;
  if (alive && !S.inkTimer) S.inkTimer = setInterval(paintInk, 60);
  if (!alive && S.inkTimer) { clearInterval(S.inkTimer); S.inkTimer = null; }
}

// ------------------------------------------------------------------ media
// The quality asked of a capture, and what a sender may spend on it. A screen keeps its resolution
// (text must stay readable) and drops frames instead; a camera keeps its motion.
const CAM = { width: { ideal: 1920 }, height: { ideal: 1080 }, frameRate: { ideal: 30 } };
const SCREEN = { width: { ideal: 2560 }, height: { ideal: 1440 }, frameRate: { ideal: 30, max: 30 } };
const BITRATE = { cam: 2500000, screen: 6000000 };
// A remembered device is a wish, never a demand. Chromium salts its deviceIds per origin and our
// profile is off the record, so an id from an earlier Maya session names nothing in this one
// (measured 2026-10-29: the same microphone, two ids in two runs). Asked as `exact` such an id
// raises OverconstrainedError, which used to kill the whole call; asked as an IDEAL it is honoured
// where the device is there and falls back to the default by itself where it is not. The label is
// what survives a session, so it is what a stale id is resolved by.
async function known() {
  try { return await navigator.mediaDevices.enumerateDevices(); }
  catch (e) { return []; }
}
function pickDevice(all, kind, id, label) {
  const them = all.filter((d) => d.kind === kind && d.deviceId);
  if (id && them.some((d) => d.deviceId === id)) return id;
  if (label) {
    const named = them.find((d) => d.label && d.label === label);
    if (named) return named.deviceId;
  }
  return "";
}
async function wantedDevices() {
  const all = await known();
  return { mic: pickDevice(all, "audioinput", S.devices.mic, S.devices.mic_label),
           cam: pickDevice(all, "videoinput", S.devices.cam, S.devices.cam_label) };
}
function audioAsked(id) { return id ? { deviceId: id } : true; }
function camAsked(id) { return id ? Object.assign({ deviceId: id }, CAM) : CAM; }
function micNote() {
  note(S.nomic ? "Микрофон не найден (" + S.nomic
       + ") - вы слышите остальных, но вас не слышно" : "");
}
async function tune(sender) {
  if (!sender || !sender.track || !sender.getParameters) return;
  const screen = sender.track === S.screenTrack;
  try {
    const prm = sender.getParameters();
    if (!prm.encodings || !prm.encodings.length) return;   // before negotiation: tuned when connected
    for (const e of prm.encodings) { e.maxBitrate = screen ? BITRATE.screen : BITRATE.cam; e.scaleResolutionDownBy = 1; }
    prm.degradationPreference = screen ? "maintain-resolution" : "balanced";
    await sender.setParameters(prm);
  } catch (e) { /* a browser that will not take it sends as it would */ }
}
// Never raises: a page that cannot open a microphone still joins, still hears everybody, and says
// so (S.nomic). Both devices are asked for in one go while that works, and taken apart when it
// does not - either loss used to cost the other.
async function userMedia(video) {
  const audio = audioAsked(S.devices.mic);
  const cam = video ? camAsked(S.devices.cam) : null;
  let stream = null;
  if (cam) {
    try { stream = await navigator.mediaDevices.getUserMedia({ audio, video: cam }); }
    catch (e) { /* one of the two: each is asked on its own below */ }
  }
  if (stream) return stream;
  try { stream = await navigator.mediaDevices.getUserMedia({ audio }); }
  catch (e) { S.nomic = e.name || String(e); }
  if (cam) {
    try {
      const v = await navigator.mediaDevices.getUserMedia({ video: cam });
      if (stream) for (const t of v.getVideoTracks()) stream.addTrack(t);
      else stream = v;
    } catch (e) { note("Камера недоступна: " + e.name); }
  }
  return stream || new MediaStream();
}
// The microphone we hold against the one the remembered id and label now name: take the other
// when they differ. That is the stale id resolved by its label at the start, a device unplugged
// mid-call (its track ends) and one plugged back in.
async function settleMic(force) {
  if (S.ended || !S.local) return false;
  const have = S.local.getAudioTracks()[0] || null;
  const live = !!have && have.readyState === "live";
  const wanted = (await wantedDevices()).mic;
  const got = live && have.getSettings ? (have.getSettings().deviceId || "") : "";
  if (live && !force && (!wanted || wanted === got)) return false;
  return takeMic(wanted);
}
async function takeMic(id) {
  let track = null;
  try {
    const s = await navigator.mediaDevices.getUserMedia({ audio: audioAsked(id) });
    track = s.getAudioTracks()[0] || null;
  } catch (e) { S.nomic = e.name || String(e); S.mic = false; micNote(); return false; }
  if (!track) return false;
  if (S.ended || !S.local) { track.stop(); return false; }
  track.enabled = S.mic;
  for (const old of S.local.getAudioTracks()) { S.local.removeTrack(old); old.onended = null; old.stop(); }
  S.local.addTrack(track);
  for (const p of S.peers.values()) { const snd = audioSender(p); if (snd) await snd.replaceTrack(track); }
  track.onended = () => {
    if (S.local && S.local.getAudioTracks().includes(track)) settleMic(false).catch(() => {});
  };
  watchLevel(S.me, S.local);
  S.nomic = ""; micNote();
  report();
  return true;
}
async function listDevices() {
  try {
    const all = await navigator.mediaDevices.enumerateDevices();
    S.list = { mics: all.filter((d) => d.kind === "audioinput").map((d) => ({ id: d.deviceId, label: d.label || "Микрофон" })),
               cams: all.filter((d) => d.kind === "videoinput").map((d) => ({ id: d.deviceId, label: d.label || "Камера" })) };
  } catch (e) { S.list = { mics: [], cams: [] }; }
  report();
}
function videoSender(p) {
  const t = p.pc.getTransceivers().find((x) => x.receiver.track && x.receiver.track.kind === "video");
  return t ? t.sender : null;
}
function audioSender(p) {
  const t = p.pc.getTransceivers().find((x) => x.receiver.track && x.receiver.track.kind === "audio");
  return t ? t.sender : null;
}
function outgoingVideo() { return S.screen && S.screenTrack ? S.screenTrack : (S.cam ? S.camTrack : null); }
async function pushVideo() {
  const track = outgoingVideo();
  for (const p of S.peers.values()) { const s = videoSender(p); if (s) { await s.replaceTrack(track); await tune(s); } }
  const local = new MediaStream([track].filter(Boolean));
  showStream(S.me, local, true);
  setTile(S.me, { nocam: !track, screen: S.screen });
  others({ cam: !!track, screen: S.screen });
  if (S.screen) { armInk(tile(S.me)); watchFrames(); }
  else if (S.stage && !screenTile()) closeStage();
}

// ------------------------------------------------------------------ speaking light
function unwatchLevel(uid) {
  const l = S.levels.get(uid);
  if (!l) return;
  try { l.src.disconnect(); l.an.disconnect(); } catch (e) { /* gone */ }
  S.levels.delete(uid);
}
function watchLevel(uid, stream) {
  if (!stream.getAudioTracks().length) return;
  unwatchLevel(uid);
  if (!S.audio) S.audio = new AudioContext();
  if (S.audio.state === "suspended") S.audio.resume().catch(() => {});
  const src = S.audio.createMediaStreamSource(stream);
  const an = S.audio.createAnalyser(); an.fftSize = 512; src.connect(an);
  S.levels.set(uid, { src, an, buf: new Float32Array(an.fftSize), since: 0, on: false });
}
function tickLevels() {
  const now = Date.now();
  for (const [uid, l] of S.levels) {
    l.an.getFloatTimeDomainData(l.buf);
    let sum = 0; for (const x of l.buf) sum += x * x;
    const loud = Math.sqrt(sum / l.buf.length) > SPEAK && (uid !== S.me || S.mic);
    if (loud) l.since = now;
    const on = now - l.since < 300;
    if (on !== l.on) {
      l.on = on; setTile(uid, { speaking: on });
      if (uid === S.me) S.speakingMe = on; else if (S.peers.get(uid)) S.peers.get(uid).speaking = on;
      report();
    }
  }
}

// ------------------------------------------------------------------ peers
function addPeer(uid, offer) {
  if (S.ended || !S.local || S.peers.has(uid) || uid === S.me) return;
  const pc = new RTCPeerConnection({ iceServers: S.ice, iceTransportPolicy: S.relay ? "relay" : "all" });
  const p = { uid, pc, offer, stream: new MediaStream(), pending: [], failedAt: 0, mic: true, cam: false,
              screen: false, speaking: false, bytes: { audio_in: 0, video_in: 0, audio_out: 0, video_out: 0 } };
  S.peers.set(uid, p);
  if (offer) {
    // The offerer makes the two lines; the answerer takes the offer's (`attachLocal`): transceivers
    // it made itself with addTransceiver would never be matched to the offer's and would send nothing.
    const audio = S.local.getAudioTracks()[0];
    pc.addTransceiver(audio || "audio", { direction: "sendrecv", streams: [S.local] });
    pc.addTransceiver(outgoingVideo() || "video", { direction: "sendrecv", streams: [S.local] });
  }
  pc.onicecandidate = (ev) => { if (ev.candidate) send(uid, { ice: ev.candidate.toJSON() }); };
  pc.ontrack = (ev) => {
    if (!p.stream.getTracks().includes(ev.track)) p.stream.addTrack(ev.track);
    showStream(uid, p.stream, false);
    if (ev.track.kind === "audio") watchLevel(uid, new MediaStream([ev.track]));
    report();
  };
  pc.onconnectionstatechange = () => {
    const st = pc.connectionState;
    if (st === "failed" || st === "disconnected") { p.failedAt = p.failedAt || Date.now(); if (st === "failed" && p.offer) sendOffer(p, true); }
    else if (st === "connected") { p.failedAt = 0; tune(videoSender(p)); send(uid, { mic: S.mic, cam: !!outgoingVideo(), screen: S.screen }); }
    setTile(uid, { lost: false });
    report();
  };
  tile(uid);
  setTile(uid, { nocam: true });
  if (offer) sendOffer(p, false);
  report();
}
async function makeOffer(p, restart) {
  const o = await p.pc.createOffer(restart ? { iceRestart: true } : undefined);
  if (S.peers.get(p.uid) !== p) return;              // left while the offer was made
  await p.pc.setLocalDescription(o);
  if (S.peers.get(p.uid) !== p) return;
  send(p.uid, { sdp: p.pc.localDescription.toJSON() });
}
function sendOffer(p, restart) {
  makeOffer(p, restart).catch((e) => {
    if (S.peers.get(p.uid) !== p) return;
    S.error = "offer: " + (e && e.message ? e.message : e); report();
  });
}
async function attachLocal(p) {
  // The answer sends on the offer's lines: my microphone on the audio one, my camera or screen on the video one.
  for (const t of p.pc.getTransceivers()) {
    const kind = t.receiver.track && t.receiver.track.kind;
    if (!kind || t.stopped) continue;
    if (t.direction !== "sendrecv") t.direction = "sendrecv";
    const track = kind === "audio" ? (S.local.getAudioTracks()[0] || null) : outgoingVideo();
    if (t.sender.track !== track) await t.sender.replaceTrack(track);
    if (t.sender.setStreams) t.sender.setStreams(S.local);
  }
}
async function onSignal(from, data) {
  // A late message from somebody who left (or after `end`) must not bring them back as a peer.
  if (S.ended || !S.local || S.left.has(from)) return;
  let p = S.peers.get(from);
  if (!p) { addPeer(from, false); p = S.peers.get(from); if (!p) return; }
  const gone = () => S.peers.get(from) !== p;
  try {
    if (data.sdp) {
      await p.pc.setRemoteDescription(data.sdp);
      if (gone()) return;
      if (data.sdp.type === "offer") {
        await attachLocal(p);
        const a = await p.pc.createAnswer();
        if (gone()) return;
        await p.pc.setLocalDescription(a);
        if (gone()) return;
        send(from, { sdp: p.pc.localDescription.toJSON() });
      }
      for (const c of p.pending.splice(0)) await p.pc.addIceCandidate(c).catch(() => {});
    } else if (data.ice) {
      if (p.pc.remoteDescription) await p.pc.addIceCandidate(data.ice).catch(() => {});
      else p.pending.push(data.ice);
    }
    if ("mic" in data) { p.mic = !!data.mic; setTile(from, { micoff: !p.mic }); }
    if ("cam" in data) { p.cam = !!data.cam; setTile(from, { nocam: !p.cam }); }
    if ("screen" in data) {
      p.screen = !!data.screen;
      setTile(from, { screen: p.screen });
      if (!p.screen && S.stage && !screenTile()) closeStage();
      if (p.screen) { S.stageGone = false; armInk(tile(from)); }
    }
    if (data.draw) ink(from, data.draw);
  } catch (e) { if (!gone()) S.error = "signal: " + e.message; }
  report();
}
function removePeer(uid) {
  S.left.add(uid);
  const p = S.peers.get(uid);
  if (!p) return;
  try { p.pc.close(); } catch (e) { /* closed */ }
  S.peers.delete(uid); unwatchLevel(uid); dropTile(uid); report();
}
async function stats() {
  checkStall();
  for (const p of S.peers.values()) {
    try {
      const r = await p.pc.getStats();
      const b = { audio_in: 0, video_in: 0, audio_out: 0, video_out: 0 };
      r.forEach((s) => {
        if (s.type === "inbound-rtp") b[s.kind + "_in"] += s.bytesReceived || 0;
        if (s.type === "outbound-rtp") b[s.kind + "_out"] += s.bytesSent || 0;
      });
      p.bytes = b;
    } catch (e) { /* closed */ }
    const lost = !!(p.failedAt && Date.now() - p.failedAt > LOST_MS);
    setTile(p.uid, { lost });
  }
  report();
}

// ------------------------------------------------------------------ commands
const COMMANDS = {
  async start(a) {
    S.me = a.me; S.names = a.names || {}; S.colours = a.colours || {}; S.ice = a.ice_servers || []; S.relay = !!a.relay_only;
    S.devices = { mic: a.mic || "", cam: a.cam || "", mic_label: a.mic_label || "", cam_label: a.cam_label || "" };
    S.nomic = "";
    S.local = await userMedia(!!a.video);
    if (S.nomic) { S.mic = false; micNote(); }
    S.camTrack = S.local.getVideoTracks()[0] || null;
    S.cam = !!S.camTrack;
    showStream(S.me, new MediaStream(S.local.getVideoTracks()), true);
    setTile(S.me, { nocam: !S.cam, micoff: !S.mic });
    watchLevel(S.me, S.local);
    // the list carries real ids only once a capture has been granted, so the remembered label is
    // resolved here - before the first offer carries the track
    await listDevices();
    await settleMic(false);
    for (const uid of a.peers || []) addPeer(uid, (a.offer_to || []).includes(uid));
    S.timer = setInterval(tickLevels, 80);
    S.statsTimer = setInterval(stats, 2000);
  },
  add_peer(a) { S.left.delete(a.uid); addPeer(a.uid, !!a.offer); },
  remove_peer(a) { removePeer(a.uid); },
  signal(a) { return onSignal(a.from, a.data || {}); },
  async mute(a) {
    if (!a.on && S.nomic) await settleMic(true);       // unmuting with no microphone looks for one
    S.mic = !a.on && !S.nomic;
    for (const t of (S.local ? S.local.getAudioTracks() : [])) t.enabled = S.mic;
    setTile(S.me, { micoff: !S.mic }); others({ mic: S.mic }); report();
  },
  async camera(a) {
    if (S.ended) return;
    if (a.on && !S.camTrack) {
      try {
        const s = await navigator.mediaDevices.getUserMedia({ video: camAsked((await wantedDevices()).cam) });
        S.camTrack = s.getVideoTracks()[0];
      } catch (e) { note("Камера недоступна: " + e.name); return; }
    } else if (!a.on) {
      stopCamera();                                   // the camera's light goes off; a camera-on takes it again
    }
    S.cam = !!a.on && !!S.camTrack;
    await pushVideo(); report();
  },
  async screen(a) {
    if (S.ended) return;
    if (!a.again) setDrawing(false);                  // a fresh share starts with the pen off
    stopScreen();                                     // a new share replaces the old capture
    if (a.on) {
      try {
        const s = await navigator.mediaDevices.getDisplayMedia({ video: SCREEN, audio: false });
        const t = s.getVideoTracks()[0];
        if ("contentHint" in t) t.contentHint = "detail";    // the encoder keeps edges sharp
        if (S.ended) { t.stop(); return; }
        S.screenTrack = t;
        t.onended = () => { if (S.screenTrack === t) COMMANDS.screen({ on: false }); };
        S.screen = true;
        const st = t.getSettings ? t.getSettings() : {};
        // The settings are the CONSTRAINED size; the capability's max is the monitor's own, and
        // that is the only thing that says WHICH monitor this is - Chromium names none of them
        // (callview.capture_screen).
        let cap = {};
        try { cap = t.getCapabilities ? t.getCapabilities() : {}; } catch (e) { cap = {}; }
        const native = (c) => (c && typeof c.max === "number" ? c.max : 0);
        S.capture = { surface: st.displaySurface || "", w: st.width || 0, h: st.height || 0,
                      nw: native(cap.width), nh: native(cap.height),
                      label: t.label || "", again: !!a.again };
        S.stalled = false;
        S.stageGone = false;
        S.lastFrame = Date.now();
        watchFrames();
      } catch (e) { note(""); S.capture = null; report(); }
    } else {
      S.capture = null; S.stalled = false;
    }
    await pushVideo(); report();
  },
  stage(a) {
    // The window has just given the page a click: requestWindow needs that activation.
    if (a.on) { S.stageGone = false; openStage(); } else { closeStage(); S.stageGone = true; }
  },
  draw(a) { setDrawing(!!a.on); },
  async devices(a) {
    if (S.ended) return;
    // Merge: a change of one device keeps the other. The camera is taken anew only while it is on;
    // otherwise the next camera-on takes the chosen one.
    if (a.mic !== undefined) { S.devices.mic = a.mic || ""; S.devices.mic_label = a.mic_label || ""; }
    if (a.cam !== undefined) { S.devices.cam = a.cam || ""; S.devices.cam_label = a.cam_label || ""; }
    if (a.mic !== undefined && S.local) {
      const wanted = (await wantedDevices()).mic;
      if (!(await takeMic(wanted))) note("Микрофон не переключился: " + (S.nomic || "error"));
    }
    if (a.cam !== undefined && S.cam) {
      stopCamera();
      await COMMANDS.camera({ on: true });
    }
    report();
  },
  names(a) {
    S.names = (a && a.names) || a || {};
    if (a && a.colours) S.colours = a.colours;
    for (const t of document.querySelectorAll(".tile")) tile(t.id.slice(2));
  },
  end() {
    S.ended = true;
    closeStage();
    S.strokes.clear();
    for (const uid of [...S.peers.keys()]) removePeer(uid);
    for (const t of (S.local ? S.local.getTracks() : [])) t.stop();
    stopCamera(); stopScreen(); S.cam = false;
    S.local = null;
    for (const uid of [...S.levels.keys()]) unwatchLevel(uid);
    if (S.audio) { S.audio.close().catch(() => {}); S.audio = null; }
    if (S.timer) clearInterval(S.timer);
    if (S.statsTimer) clearInterval(S.statsTimer);
    S.timer = S.statsTimer = null;
    report();
  },
};
function stopCamera() {
  if (!S.camTrack) return;
  if (S.local && S.local.getVideoTracks().includes(S.camTrack)) S.local.removeTrack(S.camTrack);
  S.camTrack.stop(); S.camTrack = null;
}
function stopScreen() {
  if (S.screenTrack) { S.screenTrack.onended = null; S.screenTrack.stop(); }
  S.screenTrack = null; S.screen = false;
  S.frameToken = (S.frameToken || 0) + 1;
}

// A capture can die on its feet - a desktop duplication lost to a full-screen app or a driver
// reset leaves the last frame standing and the track `live`. Every frame the local picture hands
// us is noted; a long silence while the page is on screen is reported, and the window takes the
// capture again with the same source.
function watchFrames() {
  const v = tile(S.me).querySelector("video");
  if (!v || !v.requestVideoFrameCallback) { S.lastFrame = 0; return; }
  const token = (S.frameToken = (S.frameToken || 0) + 1);
  const step = () => {
    if (token !== S.frameToken || !S.screen) return;
    S.lastFrame = Date.now();
    if (S.stalled) { S.stalled = false; report(); }
    v.requestVideoFrameCallback(step);
  };
  v.requestVideoFrameCallback(step);
}
function checkStall() {
  if (!S.screen || !S.lastFrame || !S.screenTrack || S.screenTrack.readyState !== "live") return;
  let shown = document.visibilityState === "visible";
  if (!shown && S.stageTile) {
    try { shown = S.stageTile.ownerDocument.visibilityState === "visible"; } catch (e) { shown = true; }
  }
  if (!shown) { S.lastFrame = Date.now(); return; }   // a page nobody draws gets no frame callbacks
  const stuck = Date.now() - S.lastFrame > STALL_MS;
  if (stuck !== S.stalled) { S.stalled = stuck; report(); }
}

// Every command waits for `start` (it awaits the devices: an `add_peer` or `signal` sent right after
// it must find the local media there); set-up messages run one after another in the order they came.
// The others do not queue behind each other: a screen share waiting on the screen picker must not
// hold the set-up of a newcomer.
// Headphones switched, a webcam unplugged: the list is read again (the menu), the microphone is
// settled on what the remembered id and label now name, and a camera whose device went is taken
// anew. Before `start` there is no local media and settleMic answers at once.
if (navigator.mediaDevices && navigator.mediaDevices.addEventListener) {
  navigator.mediaDevices.addEventListener("devicechange", () => {
    listDevices();
    settleMic(false).catch(() => {});
    if (S.cam && (!S.camTrack || S.camTrack.readyState !== "live")) {
      stopCamera();
      COMMANDS.camera({ on: true }).catch(() => {});
    }
  });
}
let started = Promise.resolve();
let signals = Promise.resolve();
new QWebChannel(qt.webChannelTransport, (channel) => {
  S.bridge = channel.objects.bridge;
  S.bridge.command.connect((name, args) => {
    const fn = COMMANDS[name];
    if (!fn) return;
    let a = {};
    try { a = JSON.parse(args || "{}"); } catch (e) { return; }
    const fail = (e) => { S.error = name + ": " + (e && e.message ? e.message : e); report(); };
    if (name === "start") { started = started.then(() => fn(a)).catch(fail); }
    else if (name === "signal") { signals = Promise.all([started, signals]).then(() => fn(a)).catch(fail); }
    else { started.then(() => fn(a)).catch(fail); }
  });
  S.bridge.ready();
});
