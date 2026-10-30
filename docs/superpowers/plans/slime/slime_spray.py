"""Slime spray built by hand: strands of drops that stretch, tear and splat.

The second take on the Creep 2 dismemberment slime (2026-10-28). nParticles'
blobby mesh either clumps a spray into sausages or drops sparse particles, so
the spray is simulated here directly:

- a wound emits STRANDS: chains of points leaving the wound one after another
  along one direction, the head faster than the tail, so a strand stretches
  in flight, thins (volume kept) and tears into drops where it is stretched
  too far;
- every point flies ballistically (gravity, a little drag) and stops on the
  floor, where it is drawn flattened: a strand that lands is a streak;
- a landed point feeds a floor splat (slime_fx.splats: a lumpy disc with
  tendrils and satellites, growing with what lands on it), so the stream
  from a stump grows into a pool.

The air is one mesh a frame (visible on its frame only), a fully landed strand
moves into a static floor chunk shown from its frame on, and everything goes
through one Alembic file, so the viewport plays light meshes.

    exec(open(".../slime_spray.py").read()); run()

run() ends with one gpuCache node, slime_gpuCache, reading cache/slime/slime_gpu_vNNN.abc.
"""
import math
import os
import random

import maya.cmds as cmds

HERE = "C:/!!!Work/MayaScripts/docs/superpowers/plans/slime"
exec(open(HERE + "/slime_fx.py", encoding="utf-8").read(), globals())

import numpy as np

SPRAY_GROUP = "slime_spray"
# more slime from a wound: its volume times this (the same strands, fatter)
VOLUME = {"armStump": 1.3, "armPiece": 1.3}
SPLAT_THICKNESS = 2.2         # cm: a landed point's volume spread this thick feeds its splat
G = np.array([0.0, -980.0, 0.0])
SUBSTEPS = 4

# per wound: (kind, size) come from slime_fx.SOURCES
SPRAY = {
    "seed": 7,
    "inherit": 0.45,
    "drag": 0.35,             # 1/s
    # the burst at the cut
    "burstFrames": 4,
    "burstStrands": 26,      # a frame, at size 1, falling off over the burst
    "burstSpeed": (90.0, 260.0),
    "burstCone": 34.0,        # deg
    "burstPoints": (3, 30),
    "burstRadius": (0.35, 2.6),
    # the pulsing stream from a stump
    "pulseHz": 2.2,
    "pulseStrands": 7,
    "pulseSpeed": (80.0, 180.0),
    "pulseCone": 11.0,
    "pulsePoints": (5, 22),
    "pulseRadius": (0.7, 2.8),
    "streamFade": 0.6,        # what is left of the stream at the end
    # the trail from a flying piece
    "trailStrands": 4.0,
    "trailFrames": 34,
    "trailSpeed": (20.0, 90.0),
    "trailCone": 40.0,
    "trailPoints": (2, 12),
    "trailRadius": (0.3, 1.5),
    # strands
    "emitSpan": 0.55,         # frames a strand takes to leave the wound
    "tailSpeed": 0.86,        # the tail leaves this much slower than the head
    "tear": 10.0,              # a segment longer than this many of its rest lengths tears
    "sides": 6,
    "threadMin": 0.45,        # cm: a thread thinner than this breaks into beads
    "beadGap": 3.2,           # beads this many of their radii apart
    "dropMin": 0.32,          # cm: the smallest drop
    "dropTail": 0.006,        # a drop's tail length per cm/s of its speed
    "dropTailMin": 2.2,       # ... never shorter than this many of its radii
    "stretchDrop": 3.0,       # how drawn out a blob is along its flight: a drop
    "stretchBead": 2.6,       # ... a bead along its thread
    "stretchBody": 1.8,       # ... a strand along itself
    "blobReach": 2.0,         # a blob's influence against its radius
    "iso": 0.42,
    "voxel": 0.6,             # cm
    "maxVoxels": 22e6,
    "relax": 2,
    "airWide": 1.45,          # an air strand's width against its radius
    "airFlat": 0.7,           # ... and its thickness (an oval, not a blade)
    "headBulb": 1.35,         # a falling piece's leading drop against its radius
    "beads": 0.6,             # how much a stretched thread gathers into beads
    "curl": 0.14,             # mean; each strand draws its own (exponential)
    "tailRange": (0.6, 0.97), # the tail's speed against the head's, per strand
    "clingShare": 0.55,       # strands whose tail clings to the wound
    "lobeShare": 0.88,         # strands that leave in one of the spray's tongues
    "sizePower": 2.2,         # >1: most strands thin, a few fat
    "gobShare": 0.03,         # heavy lumps among the strands
    "mist": 30,               # single drops a burst frame at the full burst             # how much a strand's points differ in direction (it bends in flight)
    "airWobble": 0.4,
    "airRoll": 70.0,          # deg: how far a ribbon may turn from lying flat
    # stickiness: the tail of a strand clings to the wound for a while, and
    # neighbouring points of a strand drag each other along (viscosity)
    "burstCling": (2.0, 10.0),  # frames
    "pulseCling": (3.0, 12.0),
    "trailCling": (4.0, 16.0),
    "clingPoints": 2,
    "maxRope": 25.0,          # cm: a clinging tail lets go past this from its neighbour
    "tearLength": 16.0,       # cm: any segment longer than this tears
    "viscosity": 0.22,        # share of the velocity difference to a neighbour removed a substep
    "flat": 0.32,             # a landed point's height against its radius
    "wide": 2.6,              # ... and its width
}


# ------------------------------------------------------------------ the wounds

def wound_tracks():
    """Each wound's world position and outward axis on every frame (START..END+1)."""
    cmds.currentTime(START)
    if cmds.objExists(GROUP):
        cmds.delete(GROUP)
    cmds.createNode("transform", name=GROUP)
    drivers = {}
    for name, (joint, inner, cut, size, kind) in SOURCES.items():
        drv = cmds.spaceLocator(name="slime_%s_drv" % name)[0]
        drv = cmds.parent(drv, GROUP)[0]
        before = BEFORE_CUT.get(name)
        if before:
            pc = cmds.pointConstraint(before[0], joint, drv)[0]
            ac = cmds.aimConstraint(before[1], inner, drv, aimVector=(-1, 0, 0), upVector=(0, 1, 0),
                                    worldUpType="scene")[0]
            for con in (pc, ac):
                w = cmds.listAttr(con, string="*W*", userDefined=True)
                for plug, (a, b) in zip(w, ((1, 0), (0, 1))):
                    cmds.setKeyframe(con, attribute=plug, time=cut - 1, value=a, outTangentType="step")
                    cmds.setKeyframe(con, attribute=plug, time=cut, value=b, outTangentType="step")
        else:
            cmds.pointConstraint(joint, drv)
            cmds.aimConstraint(inner, drv, aimVector=(-1, 0, 0), upVector=(0, 1, 0), worldUpType="scene")
        drivers[name] = drv
    tracks = {n: ([], []) for n in drivers}
    for f in range(START, END + 2):
        cmds.currentTime(f)
        for n, drv in drivers.items():
            m = cmds.xform(drv, q=True, ws=True, matrix=True)
            tracks[n][0].append(m[12:15])
            tracks[n][1].append(m[0:3])
    cmds.delete(GROUP)
    return {n: (np.array(p), np.array(a)) for n, (p, a) in tracks.items()}


def _at(track, t):
    """A track at a fractional frame."""
    i = int(math.floor(t)) - START
    i = max(0, min(len(track) - 2, i))
    u = t - (i + START)
    return track[i] * (1 - u) + track[i + 1] * u


def _cone(rng, axis, deg):
    axis = axis / (np.linalg.norm(axis) + 1e-9)
    side = np.cross(axis, [0.0, 1.0, 0.0])
    if np.linalg.norm(side) < 1e-4:
        side = np.cross(axis, [1.0, 0.0, 0.0])
    side /= np.linalg.norm(side)
    up = np.cross(side, axis)
    a = math.radians(deg) * math.sqrt(rng.random())
    b = rng.uniform(0, 2 * math.pi)
    return axis * math.cos(a) + (side * math.cos(b) + up * math.sin(b)) * math.sin(a)


# ----------------------------------------------------------------- the strands

def _schedule(kind, cut, size):
    """(frame, how many strands, which recipe) for one wound."""
    S = SPRAY
    out = []
    for i in range(S["burstFrames"]):
        out.append((cut + i, S["burstStrands"] * size * (1.0 - i / float(S["burstFrames"])) ** 1.3, "burst"))
    if kind == "stream":
        period = FPS / S["pulseHz"]
        f = cut + S["burstFrames"]
        while f < END:
            fade = 1.0 - (1.0 - S["streamFade"]) * (f - cut) / float(END - cut)
            for k in range(int(period * 0.4)):
                out.append((f + k, S["pulseStrands"] * size * fade * math.sin(math.pi * (k + 0.5) / (period * 0.4)), "pulse"))
            f += period
    else:
        for k in range(S["trailFrames"]):
            out.append((cut + S["burstFrames"] + k, S["trailStrands"] * size * (1.0 - k / float(S["trailFrames"])), "trail"))
    return out


def _sized(rng, lo, hi, power):
    """A size between lo and hi, most of them small (power > 1), a few big."""
    return lo * (hi / lo) ** (rng.random() ** power)


def _strand(rng, S, recipe, t0, d, spd, r, k, p, wv, wi, gob=False):
    """One strand: k points leaving the wound at p one after another along d (each its own shape)."""
    c1 = np.cross(d, [0.0, 1.0, 0.0])
    if np.linalg.norm(c1) < 1e-4:
        c1 = np.cross(d, [1.0, 0.0, 0.0])
    c1 = c1 / np.linalg.norm(c1)
    c2 = np.cross(d, c1)
    ph1, ph2 = rng.uniform(0, 6.283), rng.uniform(0, 6.283)
    # every strand curls its own way: some nearly straight, some coiled
    curl = S["curl"] * rng.expovariate(1.0) * (0.4 if gob else 1.0)
    fr1, fr2 = rng.uniform(0.15, 1.3), rng.uniform(0.1, 0.9)
    tail = rng.uniform(*S["tailRange"])
    span = S["emitSpan"] * rng.uniform(0.4, 1.8) * (k / 12.0) ** 0.5
    lump = rng.uniform(0.0, 0.7)              # how lumpy its thickness is
    cling_on = rng.random() < S["clingShare"]
    cling = t0 + rng.uniform(*S[recipe + "Cling"])
    pts = []
    for j in range(k):
        u = j / max(1, k - 1)
        tj = t0 + span * u
        share = 1.0 - (1.0 - tail) * u
        dj = d + curl * (c1 * math.sin(ph1 + j * fr1) + c2 * math.sin(ph2 + j * fr2))
        dj = dj / np.linalg.norm(dj)
        v = dj * spd * share * rng.uniform(0.985, 1.015) + wv * S["inherit"]
        prof = (1.0 - u) ** rng.uniform(0.3, 1.5) if not gob else 0.6 + 0.4 * math.sin(math.pi * (j + 0.5) / k)
        rr = r * max(0.25, prof) * (1.0 + lump * math.sin(ph1 * 3 + j * 1.7))
        pts.append((tj, p, v, rr, wi, cling if (cling_on and j >= k - S["clingPoints"]) else -1.0))
    return pts


def emit(tracks):
    """Every strand: its points' birth times, starting positions and speeds, radii."""
    S = SPRAY
    rng = random.Random(S["seed"])
    strands = []
    lobes = {}
    for wi, (name, (joint, inner, cut, size, kind)) in enumerate(SOURCES.items()):
        pos, axis = tracks[name]
        vol = VOLUME.get(name, 1.0)
        # every wound its own random sequence: changing one leaves the others as they were
        rng = random.Random(S["seed"] * 1000 + wi)
        for f, count, recipe in _schedule(kind, cut, size):
            n = int(count) + (1 if rng.random() < count - int(count) else 0)
            cone = S[recipe + "Cone"]
            # the spray leaves in a few lobes (tongues), not an even cone
            key = (wi, recipe, int(f) // 3)
            if key not in lobes:
                lobes[key] = [(_cone(rng, _at(axis, f), cone), rng.uniform(0.15, 0.35)) for _ in range(rng.randint(2, 4))]
            for _ in range(n):
                t0 = f + rng.random()
                if t0 > END:
                    continue
                p = _at(pos, t0)
                wv = (_at(pos, t0 + 0.5) - _at(pos, t0 - 0.5)) * FPS
                if rng.random() < S["lobeShare"]:
                    lobe, w = rng.choice(lobes[key])
                    d = _cone(rng, lobe, cone * w)
                else:
                    d = _cone(rng, _at(axis, t0), cone)
                lo, hi = S[recipe + "Speed"]
                spd = lo + (hi - lo) * rng.random() ** 1.6
                r = _sized(rng, S[recipe + "Radius"][0], S[recipe + "Radius"][1], S["sizePower"]) * (0.8 + 0.2 * size)
                r *= vol ** (1.0 / 3.0)        # the same strands, each that much fuller
                kl, kh = S[recipe + "Points"]
                k = int(round(kl + (kh - kl) * rng.random() ** 1.4))
                gob = recipe != "trail" and rng.random() < S["gobShare"]
                if gob:
                    # a heavy lump: fat, short, slow
                    r *= rng.uniform(1.6, 2.6)
                    k = rng.randint(5, 10)
                    spd *= rng.uniform(0.35, 0.7)
                strands.append(_strand(rng, S, recipe, t0, d, spd, r, k, p, wv, wi, gob))
            # a mist of single drops with every burst frame
            if recipe == "burst":
                for _ in range(int(S["mist"] * count / max(1.0, S["burstStrands"]))):
                    t0 = f + rng.random()
                    p = _at(pos, t0)
                    wv = (_at(pos, t0 + 0.5) - _at(pos, t0 - 0.5)) * FPS
                    d = _cone(rng, _at(axis, t0), cone * 1.25)
                    spd = rng.uniform(*S["burstSpeed"]) * rng.uniform(0.6, 1.5)
                    strands.append(_strand(rng, S, recipe, t0, d, spd, rng.uniform(0.12, 0.38), 1, p, wv, wi))
    return strands


def simulate(strands, tracks):
    """Positions of every point on every frame (NaN before it is born) and its landing."""
    S = SPRAY
    pts = [p for s in strands for p in s]
    n = len(pts)
    wound = np.array([p[4] for p in pts])
    pin = np.array([p[5] for p in pts])
    wtracks = np.stack([tracks[nm][0] for nm in SOURCES])      # (wounds, frames, 3)
    # neighbours inside a strand
    nxt, i0 = [], 0
    for s_ in strands:
        nxt += [(i0 + j, i0 + j + 1) for j in range(len(s_) - 1)]
        i0 += len(s_)
    na = np.array([a for a, _ in nxt], dtype=int)
    nb = np.array([b for _, b in nxt], dtype=int)

    def wound_at(t, idx):
        fi = int(min(max(math.floor(t - START), 0), wtracks.shape[1] - 2))
        u = (t - START) - fi
        w = wound[idx]
        a, b = wtracks[w, fi], wtracks[w, fi + 1]
        return a + (b - a) * u, (b - a) * FPS

    born = np.array([p[0] for p in pts])
    pos = np.array([p[1] for p in pts], dtype=float)
    vel = np.array([p[2] for p in pts], dtype=float)
    rad = np.array([p[3] for p in pts])
    live = np.zeros(n, bool)
    landed = np.full(n, np.inf)        # frame it landed
    frames = END - START + 1
    out = np.full((frames, n, 3), np.nan)
    dt = 1.0 / FPS / SUBSTEPS
    t = float(START)
    for fi in range(frames):
        f = START + fi
        for _ in range(SUBSTEPS if fi else 0):
            t += 1.0 / SUBSTEPS
            new = (~live) & (born <= t)
            if new.any():
                # a point born during this substep has flown for the part of it after its birth
                age = (t - born[new]) / FPS
                pos[new] += vel[new] * age[:, None] + 0.5 * G * (age ** 2)[:, None]
                vel[new] += G * age[:, None]
                live |= new
            held = live & (pin > t) & np.isinf(landed)
            if held.any() and len(na):
                # a rope stretched too far lets go of the wound
                d = np.linalg.norm(pos[na] - pos[nb], axis=1)
                far = (d > S["maxRope"]) & live[na] & live[nb]
                for side in (na[far], nb[far]):
                    pin[side] = -1.0
                held = live & (pin > t) & np.isinf(landed)
            if held.any():
                idx = np.nonzero(held)[0]
                p_w, v_w = wound_at(t, idx)
                pos[idx] = p_w
                vel[idx] = v_w
            fly = live & np.isinf(landed) & ~held
            # viscosity: a strand's neighbours pull each other's velocity together
            if len(na):
                both = live[na] & live[nb]
                a_, b_ = na[both], nb[both]
                dv = (vel[b_] - vel[a_]) * S["viscosity"]
                fa = fly[a_][:, None]
                fb = fly[b_][:, None]
                np.add.at(vel, a_, dv * fa)
                np.add.at(vel, b_, -dv * fb)
            vel[fly] += G * dt
            vel[fly] *= (1.0 - S["drag"] * dt)
            pos[fly] += vel[fly] * dt
            hit = fly & (pos[:, 1] <= 0.0)
            if hit.any():
                pos[hit, 1] = 0.0
                landed[hit] = t
        show = live.copy()
        out[fi, show] = pos[show]
    return out, landed, rad


# ------------------------------------------------------------------ the meshes

def _frames_of(p, tangent, r, landed):
    """Ring centre, side and up vectors for every point of a polyline."""
    S = SPRAY
    up_world = np.array([0.0, 1.0, 0.0])
    side = np.cross(tangent, up_world)
    bad = np.linalg.norm(side, axis=1) < 1e-5
    side[bad] = np.array([1.0, 0.0, 0.0])
    side /= np.linalg.norm(side, axis=1)[:, None]
    up = np.cross(side, tangent)
    up /= np.linalg.norm(up, axis=1)[:, None] + 1e-9
    # in the air a strand is a flat ribbon, not a round tube: a film of slime,
    # rolled a little per strand, its width wobbling along it
    seed = float(abs(p[0, 0] * 12.9898 + p[0, 2] * 78.233)) % 6.2832
    roll = (seed % 1.0 - 0.5) * math.radians(S["airRoll"])
    side, up = side * math.cos(roll) + up * math.sin(roll), up * math.cos(roll) - side * math.sin(roll)
    along = np.arange(len(p))
    wobble = 1.0 + S["airWobble"] * ((seed * 3.7) % 1.0) * np.sin(seed + along * 1.1) * np.sin(seed * 2.3 + along * 0.37)
    shape = (seed * 7.31) % 1.0
    w = (r * S["airWide"] * (0.75 + 0.6 * shape) * wobble)[:, None]
    h = (r * S["airFlat"] * (1.25 - 0.5 * shape))[:, None]
    centre = p.copy()
    flat = landed
    if flat.any():
        ft = tangent[flat].copy()
        ft[:, 1] = 0.0
        fs = np.cross(ft, up_world)
        ok = np.linalg.norm(fs, axis=1) > 1e-6
        fs[~ok] = np.array([1.0, 0.0, 0.0])
        fs /= np.linalg.norm(fs, axis=1)[:, None]
        side[flat] = fs
        up[flat] = up_world
        w[flat] = r[flat, None] * S["wide"]
        h[flat] = r[flat, None] * S["flat"]
        centre[flat, 1] = h[flat, 0] * 0.55 + 0.03
    return centre, side * w, up * h


def _smooth(p, r, landed, sub=2):
    """A polyline made smooth (Catmull-Rom), its radii and landed flags carried."""
    k = len(p)
    if k < 3:
        return p, r, landed
    ext = np.vstack([2 * p[0] - p[1], p, 2 * p[-1] - p[-2]])
    P, R, L = [], [], []
    for i in range(k - 1):
        p0, p1, p2, p3 = ext[i], ext[i + 1], ext[i + 2], ext[i + 3]
        for j in range(sub):
            u = j / float(sub)
            u2, u3 = u * u, u * u * u
            P.append(0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u2
                            + (-p0 + 3 * p1 - 3 * p2 + p3) * u3))
            R.append(r[i] * (1 - u) + r[i + 1] * u)
            L.append(landed[i] if u < 0.5 else landed[i + 1])
    P.append(p[-1]); R.append(r[-1]); L.append(landed[-1])
    P = np.array(P)
    L = np.array(L)
    P[L, 1] = 0.0
    return P, np.array(R), L


def _tube(p, r, landed, verts, counts, conn):
    """One unbroken piece of a strand: a smooth tube with round ends (a lone point is a drop)."""
    S = SPRAY
    r = r.copy()
    # a falling piece leads with a fat round head and trails off
    if len(r) > 1:
        r[0] *= S["headBulb"]
    p, r, landed = _smooth(p, r, landed)
    k = len(p)
    sides = S["sides"]
    if k == 1:
        v = np.array([[0.3, -1.0, 0.2]])
        t = v / np.linalg.norm(v)
    else:
        t = np.gradient(p, axis=0)
    t /= np.linalg.norm(t, axis=1)[:, None] + 1e-9
    centre, sv, uv = _frames_of(p, t, r, landed)
    a = np.linspace(0, 2 * math.pi, sides, endpoint=False)
    ca, sa = np.cos(a), np.sin(a)
    rings = []
    caps = (62.0, 28.0)

    def cap(i, sign, order):
        length = r[i] * (0.45 if landed[i] else 1.0)
        out = []
        for ph in order:
            q = math.radians(ph)
            out.append((centre[i] + sign * t[i] * length * math.sin(q), math.cos(q), i))
        return out

    rings += cap(0, -1.0, caps)
    rings += [(centre[i], 1.0, i) for i in range(k)]
    rings += cap(k - 1, 1.0, caps[::-1])
    base = len(verts)
    pole0 = centre[0] - t[0] * r[0] * (0.45 if landed[0] else 1.0)
    pole1 = centre[-1] + t[-1] * r[-1] * (0.45 if landed[-1] else 1.0)
    if landed[0]:
        pole0 = pole0 + np.array([0.0, 0.0, 0.0])
    for c, scale, i in rings:
        ring = c + (ca[:, None] * sv[i] + sa[:, None] * uv[i]) * scale
        verts.extend(ring.tolist())
    verts.append(pole0.tolist())
    verts.append(pole1.tolist())
    n = len(rings)
    i0, i1 = base + n * sides, base + n * sides + 1
    for i in range(n - 1):
        for s_ in range(sides):
            s2 = (s_ + 1) % sides
            counts.append(4)
            conn.extend([base + i * sides + s_, base + i * sides + s2,
                         base + (i + 1) * sides + s2, base + (i + 1) * sides + s_])
    for s_ in range(sides):
        s2 = (s_ + 1) % sides
        counts.append(3); conn.extend([i0, base + s2, base + s_])
        counts.append(3); conn.extend([i1, base + (n - 1) * sides + s_, base + (n - 1) * sides + s2])


def _pieces(p, r, rest, landed):
    """A strand cut where it is stretched past tearing; radii thinned by the stretch."""
    S = SPRAY
    if len(p) == 1:
        return [(p, r, landed)]
    seg = np.linalg.norm(np.diff(p, axis=0), axis=1)
    stretch = seg / np.maximum(rest, 1e-3)
    # volume kept: a stretched segment thins with the square root of its stretch
    thin = np.ones(len(p))
    s_pt = np.ones(len(p))
    s_pt[:-1] = np.maximum(s_pt[:-1], stretch)
    s_pt[1:] = np.maximum(s_pt[1:], stretch)
    thin = 1.0 / np.sqrt(np.clip(s_pt, 1.0, 50.0))
    rr = r * np.clip(thin, 0.22, 1.0)
    # a stretched thread gathers into beads
    beads = 1.0 + S["beads"] * (1.0 - np.clip(thin, 0.0, 1.0)) * np.sin(np.arange(len(p)) * 2.4 + p[0, 0])
    rr = rr * beads
    out, start = [], 0
    for i, st in enumerate(stretch):
        both_down = landed[i] and landed[i + 1]
        if (st > S["tear"] and not both_down) or seg[i] > S["tearLength"]:
            out.append((p[start:i + 1], rr[start:i + 1], landed[start:i + 1]))
            start = i + 1
    out.append((p[start:], rr[start:], landed[start:]))
    return out


def _make_mesh(name, parent, verts, counts, conn):
    import maya.api.OpenMaya as om
    t = cmds.createNode("transform", name=name, parent=parent)
    if not counts:
        return t, None
    sel = om.MSelectionList()
    sel.add(t)
    om.MFnMesh().create([om.MPoint(*v) for v in verts], counts, conn, parent=sel.getDependNode(0))
    shape = cmds.listRelatives(t, shapes=True, fullPath=True)[0]
    cmds.polySoftEdge(shape, angle=180, constructionHistory=False)
    cmds.sets(shape, edit=True, forceElement=material())
    return t, shape



# ------------------------------------------------------- one liquid surface

_CORNERS = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0], [0, 0, 1], [1, 0, 1], [0, 1, 1], [1, 1, 1]])
_EDGES = [(0, 1), (2, 3), (4, 5), (6, 7), (0, 2), (1, 3), (4, 6), (5, 7), (0, 4), (1, 5), (2, 6), (3, 7)]


def _samples(p, r, landed, v):
    """Blobs along a flying piece: a drop with a tail, a smooth body, or beads on a thread."""
    S = SPRAY
    if len(p) <= 2:
        # a drop: a round head and a tail trailing behind it, longer the faster it flies
        c = p.mean(0)
        vel = v.mean(0)
        spd = float(np.linalg.norm(vel))
        # a seed of its own from where it is, so it keeps its shape frame to frame
        seed = float(abs(p[0, 0] * 12.9898 + p[0, 2] * 78.233 + r[0] * 37.719)) % 1.0
        if spd > 30.0:
            d = vel / spd
        else:
            # slow at the top of its arc: it still hangs as a drop, falling
            d = np.array([math.cos(seed * 6.283) * 0.3, -1.0, math.sin(seed * 6.283) * 0.3])
            d /= np.linalg.norm(d)
        side = np.cross(d, [0.0, 1.0, 0.0])
        if np.linalg.norm(side) < 1e-3:
            side = np.array([1.0, 0.0, 0.0])
        side /= np.linalg.norm(side)
        up = np.cross(side, d)
        rh = max(float(r.max()), S["dropMin"]) * 1.05
        tail = min(max(spd * S["dropTail"], S["dropTailMin"] * rh), 4.0 * rh)
        bend = (side * math.cos(seed * 11.0) + up * math.sin(seed * 11.0)) * rh * 0.6
        P, R, W = [c], [rh], [1.0]
        # a wobbling head: a smaller lobe off to one side
        P.append(c + (side * math.cos(seed * 5.0) + up * math.sin(seed * 5.0)) * rh * 0.45 + d * rh * 0.15)
        R.append(rh * 0.72)
        W.append(0.7)
        for i in range(1, 6):
            u = i / 5.0
            P.append(c - d * tail * u + bend * u * u)
            R.append(rh * (1.0 - 0.6 * u))
            W.append(0.85)
        A = [d] * len(P)
        K = [S["stretchDrop"]] * len(P)
        return np.array(P), np.array(R), np.array(W), np.array(A), np.array(K)
    r = r.copy()
    r[0] *= S["headBulb"]
    p, r, landed = _smooth(p, r, landed, sub=2)
    P, R, W, A, K = [], [], [], [], []
    bead_gap = 0.0
    along = np.array([1.0, 0.0, 0.0])
    for i in range(len(p) - 1):
        a, b = p[i], p[i + 1]
        seg = float(np.linalg.norm(b - a))
        rr = min(r[i], r[i + 1])
        if seg > 1e-6:
            along = (b - a) / seg
        if rr < S["threadMin"]:
            # a thin thread does not stay a wire: it gathers into a string of beads
            rb = max(S["dropMin"], rr * 1.6)
            gap = rb * S["beadGap"]
            t = bead_gap
            while t < seg:
                # a bead is drawn out along its thread, not a ball
                c = a + along * t
                P.append(c); R.append(rb); W.append(1.0)
                P.append(c + along * rb * 0.9); R.append(rb * 0.62); W.append(0.6)
                P.append(c - along * rb * 0.9); R.append(rb * 0.62); W.append(0.6)
                A += [along] * 3
                K += [S["stretchBead"]] * 3
                t += gap
            bead_gap = t - seg
            continue
        bead_gap = 0.0
        n = max(1, int(math.ceil(seg / (0.4 * rr))))
        for j in range(n):
            u = j / float(n)
            P.append(a + (b - a) * u)
            R.append(r[i] * (1 - u) + r[i + 1] * u)
            # a line of blobs h apart sums to a tube of radius r with this weight
            W.append(min(1.0, 0.629 * (seg / n) / max(R[-1], 1e-3)))
            A.append(along)
            K.append(S["stretchBody"])
    P.append(p[-1]); R.append(max(r[-1], S["dropMin"])); W.append(0.6)
    A.append(along); K.append(S["stretchBody"])
    W[0] = max(W[0], 0.6)        # the ends round off rather than thin out
    return np.array(P), np.array(R), np.array(W), np.array(A), np.array(K)


def _blobs(P, R, W, verts, counts, conn, A=None, K=None):
    """One smooth surface around all the blobs of a frame (surface nets over a metaball field)."""
    S = SPRAY
    if not len(P):
        return
    reach = R * S["blobReach"]
    if A is None:
        A = np.tile([1.0, 0.0, 0.0], (len(P), 1))
        K = np.ones(len(P))
    # no blob is a ball: each is an ellipsoid drawn out along its flow, as thin across
    # as keeps its volume (long: reach*sqrt(K), across: reach/K**0.25)
    rlong = reach * np.sqrt(K)
    rcross = reach / K ** 0.25
    vox = S["voxel"]
    lo = P.min(0) - rlong.max() - 2 * vox
    hi = P.max(0) + rlong.max() + 2 * vox
    while np.prod(np.ceil((hi - lo) / vox) + 1) > S["maxVoxels"]:
        vox *= 1.2
    dims = (np.ceil((hi - lo) / vox) + 1).astype(int)
    F = np.zeros(dims, np.float32)
    ci = np.round((P - lo) / vox).astype(int)
    ri = np.ceil(rlong / vox).astype(int)
    for rad_v in np.unique(ri):
        sel = ri == rad_v
        pc, pp, ww = ci[sel], P[sel], W[sel]
        aa, rl, rc = A[sel], rlong[sel], rcross[sel]
        rng_ = np.arange(-rad_v, rad_v + 1)
        for ox in rng_:
            for oy in rng_:
                for oz in rng_:
                    if ox * ox + oy * oy + oz * oz > (rad_v + 1) ** 2:
                        continue
                    idx = pc + (ox, oy, oz)
                    x = lo + idx * vox - pp
                    par = np.sum(x * aa, axis=1)
                    perp2 = np.sum(x * x, axis=1) - par * par
                    d2 = perp2 / (rc * rc) + par * par / (rl * rl)
                    ok = d2 < 1.0
                    if not ok.any():
                        continue
                    w = (1.0 - d2[ok]) ** 3 * ww[ok]
                    ii = idx[ok]
                    np.add.at(F, (ii[:, 0], ii[:, 1], ii[:, 2]), w)
    iso = S["iso"]
    inside = F > iso
    nx, ny, nz = dims
    c = [inside[o[0]:nx - 1 + o[0], o[1]:ny - 1 + o[1], o[2]:nz - 1 + o[2]] for o in _CORNERS]
    anyin = c[0].copy()
    allin = c[0].copy()
    for x in c[1:]:
        anyin |= x
        allin &= x
    active = anyin & ~allin
    cells = np.argwhere(active)
    if not len(cells):
        return
    index = np.full(active.shape, -1, np.int64)
    index[active] = np.arange(len(cells))
    Fc = np.stack([F[cells[:, 0] + o[0], cells[:, 1] + o[1], cells[:, 2] + o[2]] for o in _CORNERS], 1)
    acc = np.zeros((len(cells), 3))
    cnt = np.zeros(len(cells))
    for a, b in _EDGES:
        fa, fb = Fc[:, a], Fc[:, b]
        cross = (fa > iso) != (fb > iso)
        t = np.clip((iso - fa[cross]) / (fb[cross] - fa[cross]), 0.0, 1.0)
        acc[cross] += _CORNERS[a] + (_CORNERS[b] - _CORNERS[a]) * t[:, None]
        cnt[cross] += 1
    pos = lo + (cells + acc / np.maximum(cnt, 1)[:, None]) * vox
    quads = []
    for axis in range(3):
        u, v = [ax for ax in range(3) if ax != axis]
        sl0 = [slice(None)] * 3
        sl1 = [slice(None)] * 3
        sl0[axis] = slice(0, -1)
        sl1[axis] = slice(1, None)
        a0 = inside[tuple(sl0)]
        e = a0 != inside[tuple(sl1)]
        sl = [slice(None)] * 3
        sl[u] = slice(1, -1)
        sl[v] = slice(1, -1)
        e = e[tuple(sl)]
        flip = a0[tuple(sl)][e]
        g = np.argwhere(e)
        g[:, u] += 1
        g[:, v] += 1

        def cell(du, dv):
            q = g.copy()
            q[:, u] -= du
            q[:, v] -= dv
            return index[q[:, 0], q[:, 1], q[:, 2]]
        q = np.stack([cell(0, 0), cell(1, 0), cell(1, 1), cell(0, 1)], 1)
        # the cycle's normal is +axis for x and z, -axis for y; it must point out of the inside
        rev = ~flip if axis != 1 else flip
        q[rev] = q[rev][:, ::-1]
        quads.append(q)
    quads = np.vstack(quads)
    quads = quads[(quads >= 0).all(1)]
    # relax: Laplacian passes take the voxel steps off
    for _ in range(S["relax"]):
        nb = np.zeros_like(pos)
        nc = np.zeros(len(pos))
        for k in range(4):
            a_, b_ = quads[:, k], quads[:, (k + 1) % 4]
            np.add.at(nb, a_, pos[b_]); np.add.at(nc, a_, 1)
            np.add.at(nb, b_, pos[a_]); np.add.at(nc, b_, 1)
        ok = nc > 0
        pos[ok] = pos[ok] * 0.5 + 0.5 * nb[ok] / nc[ok][:, None]
    base = len(verts)
    verts.extend(pos.tolist())
    counts.extend([4] * len(quads))
    conn.extend((quads + base).ravel().tolist())


def build_meshes(strands, out, landed, rad, frames=None):
    """The air mesh of every frame and the floor chunks; returns the landings for the splats."""
    if cmds.objExists(SPRAY_GROUP):
        cmds.delete(SPRAY_GROUP)
    root = cmds.createNode("transform", name=SPRAY_GROUP)
    air = cmds.createNode("transform", name="slime_air", parent=root)
    floor = cmds.createNode("transform", name="slime_floor", parent=root)
    # index ranges of the strands in the flat point arrays
    ranges, i = [], 0
    for s in strands:
        ranges.append((i, i + len(s)))
        i += len(s)
    # a segment's rest length: how far its front point had gone when the back one left
    rest = [np.array([np.linalg.norm(s[j][2]) * (s[j + 1][0] - s[j][0]) / FPS + 0.3
                      for j in range(len(s) - 1)]) for s in strands]
    # a strand is on the floor for good once its last point has landed
    done_at = [float(np.max(landed[a:b])) for a, b in ranges]
    frames = frames or list(range(START, END + 1))
    landings = []
    seen_landed = np.zeros(len(rad), bool)
    shown = []
    for f in frames:
        fi = f - START
        verts, counts, conn = [], [], []
        fverts, fcounts, fconn = [], [], []
        bP, bR, bW, bA, bK = [], [], [], [], []
        for si, (a, b) in enumerate(ranges):
            p = out[fi, a:b]
            alive = ~np.isnan(p[:, 0])
            if not alive.any():
                continue
            p = p[alive]
            r = rad[a:b][alive]
            dn = landed[a:b][alive] <= f
            rs = rest[si][:max(0, alive.sum() - 1)] if alive.sum() > 1 else np.array([])
            if done_at[si] <= f:
                if done_at[si] > f - 1:      # landed whole on this frame: into the floor chunk
                    for pp, rr, ll in _pieces(p, r, rs, dn):
                        _tube(pp, rr, ll, fverts, fcounts, fconn)
                continue
            prev = out[max(fi - 1, 0), a:b][alive]
            vel = np.where(np.isnan(prev), 0.0, p - np.nan_to_num(prev)) * FPS
            off = 0
            for pp, rr, ll in _pieces(p, r, rs, dn):
                n = len(pp)
                vv = vel[off:off + n]
                off += n
                # what lies on the floor is a flat streak; what flies is liquid
                i = 0
                while i < n:
                    j = i
                    while j < n and ll[j] == ll[i]:
                        j += 1
                    if ll[i]:
                        _tube(pp[i:j], rr[i:j], ll[i:j], verts, counts, conn)
                    else:
                        sp, sr, sw, sa, sk = _samples(pp[i:j], rr[i:j], ll[i:j], vv[i:j])
                        bP.append(sp); bR.append(sr); bW.append(sw); bA.append(sa); bK.append(sk)
                    i = j
        if bP:
            _blobs(np.vstack(bP), np.concatenate(bR), np.concatenate(bW), verts, counts, conn,
                   np.vstack(bA), np.concatenate(bK))
        # landings for the splats: points that came down since the last frame
        newly = (landed <= f) & ~seen_landed
        idx = np.nonzero(newly)[0]
        if len(idx):
            v = np.nan_to_num(out[fi, idx])
            prev = np.nan_to_num(out[max(fi - 1, 0), idx])
            vel = (v - prev) * FPS
            for k, j in enumerate(idx):
                landings.append((float(f), float(v[k, 0]), float(v[k, 2]), float(vel[k, 0]), float(vel[k, 2]),
                                 float(rad[j])))
        seen_landed |= newly
        t, _ = _make_mesh("slime_air_%03d" % f, air, verts, counts, conn)
        for ff, v in ((f - 1, 0), (f, 1), (f + 1, 0)):
            cmds.setKeyframe(t, attribute="v", time=ff, value=v, inTangentType="step", outTangentType="step")
        if fcounts:
            t, _ = _make_mesh("slime_floor_%03d" % f, floor, fverts, fcounts, fconn)
            cmds.setKeyframe(t, attribute="v", time=f - 1, value=0, outTangentType="step")
            cmds.setKeyframe(t, attribute="v", time=f, value=1, outTangentType="step")
        shown.append((f, len(verts)))
    return landings, shown


def run(frames=None, to_alembic=True):
    import time
    t0 = time.time()
    now = cmds.currentTime(q=True)
    cmds.evaluator(name="cache", enable=False)
    for node in (SPRAY_GROUP, "slime_baked", SPLAT_GROUP, GROUP, NUCLEUS, "slime_gpuCache"):
        if cmds.objExists(node):
            cmds.delete(node)
    _drop_alembic()
    tracks = wound_tracks()
    strands = emit(tracks)
    out, landed, rad = simulate(strands, tracks)
    t1 = time.time()
    landings, shown = build_meshes(strands, out, landed, rad, frames)
    SPLAT.update(thickness=SPLAT_THICKNESS, merge=1.3, minRadius=2.0, minDrops=10, y=0.12)
    splats(landings)
    cmds.parent(SPLAT_GROUP, SPRAY_GROUP)
    t2 = time.time()
    print("strands %d points %d landings %d  sim %.1fs meshes %.1fs  biggest air frame %d verts" % (
        len(strands), len(rad), len(landings), t1 - t0, t2 - t1, max(v for _, v in shown) if shown else 0))
    path = None
    if to_alembic:
        to_cache()
        path = to_gpu()
    cmds.currentTime(now)
    return path


def to_cache():
    """The spray into one Alembic file, imported back in place of the meshes."""
    d = _cache_dir()
    i = 1
    while os.path.exists("%s/slime_spray_v%03d.abc" % (d, i)):
        i += 1
    path = "%s/slime_spray_v%03d.abc" % (d, i)
    cmds.currentTime(START)
    cmds.AbcExport(j="-frameRange %d %d -step 1 -worldSpace -writeVisibility -dataFormat ogawa -root |%s -file \"%s\""
                   % (START, END, SPRAY_GROUP, path))
    cmds.delete(SPRAY_GROUP)
    grp = cmds.createNode("transform", name="slime_baked")
    cmds.AbcImport(path, mode="import", reparent=grp)
    for m in cmds.listRelatives(grp, allDescendents=True, type="mesh", fullPath=True) or []:
        cmds.sets(m, edit=True, forceElement=material())
    cmds.select(clear=True)
    return path


def to_gpu():
    """The baked spray as one gpuCache node (materials baked in) in place of the Alembic meshes."""
    if not cmds.pluginInfo("gpuCache", q=True, loaded=True):
        cmds.loadPlugin("gpuCache")
    d = _cache_dir()
    i = 1
    while os.path.exists("%s/slime_gpu_v%03d.abc" % (d, i)):
        i += 1
    name = "slime_gpu_v%03d" % i
    cmds.gpuCache("slime_baked", startTime=START, endTime=END, directory=d, fileName=name,
                  writeMaterials=True, optimize=True, optimizationThreshold=40000, dataFormat="ogawa")
    for node in ("slime_gpuCache",):
        if cmds.objExists(node):
            cmds.delete(node)
    shape = cmds.createNode("gpuCache", name="slime_gpuCacheShape")
    cmds.rename(cmds.listRelatives(shape, parent=True)[0], "slime_gpuCache")
    cmds.setAttr("slime_gpuCacheShape.cacheFileName", "%s/%s.abc" % (d, name), type="string")
    _drop_alembic()
    cmds.delete("slime_baked")
    cmds.select(clear=True)
    return "%s/%s.abc" % (d, name)
