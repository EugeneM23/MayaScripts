// The call page (spec docs/superpowers/specs/2026-10-22-chat-calls-design.md): a WebRTC mesh driven
// by Python through the QWebChannel object `bridge`. The joiner offers; the others answer.
"use strict";
const S = { me: null, names: {}, ice: [], peers: new Map(), local: null, camTrack: null, screenTrack: null,
            mic: true, cam: false, screen: false, devices: { mic: "", cam: "" }, list: { mics: [], cams: [] },
            error: "", note: "", bridge: null, audio: null, levels: new Map(), timer: null, statsTimer: null,
            left: new Set(), ended: false };
const LOST_MS = 20000;
const SPEAK = 0.035;

function send(to, data) { if (S.bridge) S.bridge.signal(to, JSON.stringify(data)); }
function others(data) { for (const p of S.peers.values()) send(p.uid, data); }

function snapshot() {
  const peers = {};
  for (const p of S.peers.values()) {
    peers[p.uid] = { state: p.pc.connectionState, speaking: !!p.speaking, mic: p.mic, cam: p.cam,
                     screen: p.screen, lost: !!(p.failedAt && Date.now() - p.failedAt > LOST_MS), bytes: p.bytes };
  }
  return { me: S.me, mic: S.mic, cam: S.cam, screen: S.screen, error: S.error, note: S.note,
           devices: S.list, peers, speaking: !!S.speakingMe };
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
  let t = document.getElementById("t-" + uid);
  if (!t) {
    t = document.createElement("div");
    t.className = "tile nocam"; t.id = "t-" + uid;
    t.innerHTML = '<video autoplay playsinline></video><div class="face"><span></span></div>' +
                  '<div class="name"><b></b><span class="muted">&#x1F507;</span></div><div class="lost">нет соединения</div>';
    document.getElementById("grid").appendChild(t);
  }
  t.querySelector(".face span").textContent = initials(uid);
  t.querySelector(".name b").textContent = uid === S.me ? (S.names[uid] || "Вы") + " (вы)" : (S.names[uid] || uid);
  layout();
  return t;
}
function showStream(uid, stream, muted) {
  const v = tile(uid).querySelector("video");
  if (v.srcObject !== stream) v.srcObject = stream;
  v.muted = !!muted;
  v.play().catch(() => {});
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
function dropTile(uid) { const t = document.getElementById("t-" + uid); if (t) t.remove(); layout(); }

// ------------------------------------------------------------------ media
// The quality asked of a capture, and what a sender may spend on it. A screen keeps its resolution
// (text must stay readable) and drops frames instead; a camera keeps its motion.
const CAM = { width: { ideal: 1920 }, height: { ideal: 1080 }, frameRate: { ideal: 30 } };
const SCREEN = { width: { ideal: 2560 }, height: { ideal: 1440 }, frameRate: { ideal: 30, max: 30 } };
const BITRATE = { cam: 2500000, screen: 6000000 };
function camConstraints() {
  return S.devices.cam ? Object.assign({ deviceId: { exact: S.devices.cam } }, CAM) : CAM;
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
async function userMedia(video) {
  const audio = S.devices.mic ? { deviceId: { exact: S.devices.mic } } : true;
  if (!video) return navigator.mediaDevices.getUserMedia({ audio });
  try { return await navigator.mediaDevices.getUserMedia({ audio, video: camConstraints() }); }
  catch (e) { note("Камера недоступна: " + e.name); return navigator.mediaDevices.getUserMedia({ audio }); }
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
    if ("screen" in data) { p.screen = !!data.screen; setTile(from, { screen: p.screen }); }
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
    S.me = a.me; S.names = a.names || {}; S.ice = a.ice_servers || []; S.relay = !!a.relay_only; S.devices = { mic: a.mic || "", cam: a.cam || "" };
    try { S.local = await userMedia(!!a.video); }
    catch (e) { S.error = "Микрофон недоступен: " + e.name; report(); return; }
    S.camTrack = S.local.getVideoTracks()[0] || null;
    S.cam = !!S.camTrack;
    showStream(S.me, new MediaStream(S.local.getVideoTracks()), true);
    setTile(S.me, { nocam: !S.cam });
    watchLevel(S.me, S.local);
    for (const uid of a.peers || []) addPeer(uid, (a.offer_to || []).includes(uid));
    S.timer = setInterval(tickLevels, 80);
    S.statsTimer = setInterval(stats, 2000);
    await listDevices();
  },
  add_peer(a) { S.left.delete(a.uid); addPeer(a.uid, !!a.offer); },
  remove_peer(a) { removePeer(a.uid); },
  signal(a) { return onSignal(a.from, a.data || {}); },
  mute(a) {
    S.mic = !a.on;
    for (const t of (S.local ? S.local.getAudioTracks() : [])) t.enabled = S.mic;
    setTile(S.me, { micoff: !S.mic }); others({ mic: S.mic }); report();
  },
  async camera(a) {
    if (S.ended) return;
    if (a.on && !S.camTrack) {
      try {
        const s = await navigator.mediaDevices.getUserMedia({ video: camConstraints() });
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
      } catch (e) { note(""); report(); }
    }
    await pushVideo(); report();
  },
  async devices(a) {
    if (S.ended) return;
    // Merge: a change of one device keeps the other. The camera is taken anew only while it is on;
    // otherwise the next camera-on takes the chosen one.
    if (a.mic !== undefined) S.devices.mic = a.mic || "";
    if (a.cam !== undefined) S.devices.cam = a.cam || "";
    if (a.mic !== undefined && S.local) {
      try {
        const s = await navigator.mediaDevices.getUserMedia({ audio: S.devices.mic ? { deviceId: { exact: S.devices.mic } } : true });
        const t = s.getAudioTracks()[0]; t.enabled = S.mic;
        for (const old of S.local.getAudioTracks()) { S.local.removeTrack(old); old.stop(); }
        S.local.addTrack(t);
        for (const p of S.peers.values()) { const snd = audioSender(p); if (snd) await snd.replaceTrack(t); }
        watchLevel(S.me, S.local);
      } catch (e) { note("Микрофон не переключился: " + e.name); }
    }
    if (a.cam !== undefined && S.cam) {
      stopCamera();
      await COMMANDS.camera({ on: true });
    }
    report();
  },
  names(a) { S.names = a || {}; for (const t of document.querySelectorAll(".tile")) tile(t.id.slice(2)); },
  end() {
    S.ended = true;
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
}

// Every command waits for `start` (it awaits the devices: an `add_peer` or `signal` sent right after
// it must find the local media there); set-up messages run one after another in the order they came.
// The others do not queue behind each other: a screen share waiting on the screen picker must not
// hold the set-up of a newcomer.
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
