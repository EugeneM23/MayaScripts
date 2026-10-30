"""Slime from the Creep 2's cuts: nParticles liquid, meshed, baked to Alembic.

A one-off scene effect for AS_Sword_Finisher_Creep_Disarm_and_Execute_1P.ma
(2026-10-28). Run inside Maya:

    exec(open(".../slime_fx.py").read()); build(); bake()

build() makes everything under one group |SlimeFX (and one nucleus) and can be
run again: it deletes what an earlier build made first. bake() simulates frames
START..END through AbcExport, imports the mesh back, and switches the live
simulation off, so the viewport plays only the baked mesh.

Four sources, each a direction emitter on a driver that follows a joint and
points out of the wound:

    arm stump   Creep2_Rig:lowerarm_r          burst at 10, pulsing stream to the end
    arm piece   Creep2_ArmR_Rig:lowerarm_r     burst at 10, a trail while it flies
    neck stump  Creep2_Rig:neck_02             burst at 45 (bigger), pulsing stream
    head piece  Creep2_Head_Rig:neck_02        burst at 45 (bigger), a trail
"""
import math
import os

import maya.cmds as cmds
import maya.mel as mel

GROUP = "SlimeFX"
NUCLEUS = "slime_nucleus"
START, END = 0, 90
FPS = 30.0

# name: (cut joint, inner joint the wound points away from, cut frame, size)
SOURCES = {
    "armStump": ("Creep2_Rig:lowerarm_r", "Creep2_Rig:upperarm_r", 10, 1.0, "stream"),
    "armPiece": ("Creep2_ArmR_Rig:lowerarm_r", "Creep2_ArmR_Rig:hand_r", 10, 1.0, "trail"),
    "neckStump": ("Creep2_Rig:neck_02", "Creep2_Rig:neck_01", 45, 1.7, "stream"),
    "headPiece": ("Creep2_Head_Rig:neck_02", "Creep2_Head_Rig:head", 45, 1.7, "trail"),
}

# A flying piece is parked out of sight (the head 3 m under the floor) until its
# cut; its emitter follows the body's joint of the same name until then, or the
# jump at the cut frame throws particles 13 m up.
BEFORE_CUT = {
    "armPiece": ("Creep2_Rig:lowerarm_r", "Creep2_Rig:hand_r"),
    "headPiece": ("Creep2_Rig:neck_02", "Creep2_Rig:head"),
}

COLLIDERS = ()

FLOOR_KILL = 0.7              # cm: a drop this low has landed

LOOK = {
    "radius": 0.3,            # particle radius, cm
    "liquid": 0,              # SPH clumps a spray into fat sausages; off, the drops stay a spray
    "radiusRandom": 0.8,
    "viscosity": 1.5,
    "incompressibility": 0.3,
    "restDensity": 2.0,
    "surfaceTension": 0.3,
    "stickiness": 0.35,
    "friction": 0.55,
    "planeFriction": 0.18,
    "planeStickiness": 0.08,
    "planeBounce": 0.12,
    "drag": 0.01,
    "inherit": 0.5,
    "burstRate": 45000.0,     # particles a second at the peak of a burst
    "burstSpeed": 550.0,      # cm/s
    "burstSpeedRandom": 0.95, # share of the speed (Maya's speedRandom is in cm/s)
    "burstSpread": 0.55,      # 1 = a half sphere
    "streamSpeedRandom": 0.4,
    "streamSpread": 0.16,
    "trailSpread": 0.45,
    "streamRate": 6500.0,
    "streamSpeed": 230.0,
    "trailRate": 5000.0,
    "trailSpeed": 120.0,
    "pulseHz": 2.2,           # arterial spurts a second
    "colour": (0.20, 0.30, 0.015),
}

MESH = {
    "threshold": 0.45,
    "blobbyRadiusScale": 2.2,
    "motionStreak": 1.0,      # blobs stretched along their speed: strands and sheets
    "meshTriangleSize": 0.25,
    "maxTriangleResolution": 300,
    "meshMethod": 3,          # quad mesh
    "meshSmoothingIterations": 2,
}


CACHE = "C:/!!!Work/Animations/Animations/LongSword/Finisher/cache/slime"


def _cache_dir():
    path = CACHE
    if not os.path.isdir(path):
        os.makedirs(path)
    return path


def _drop_alembic():
    for n in cmds.ls(type="AlembicNode") or []:
        f = (cmds.getAttr(n + ".abc_File") or "").replace("\\", "/")
        if "/cache/slime/" in f:
            cmds.delete(n)


def _next_path():
    d = _cache_dir()
    i = 1
    while os.path.exists("%s/slime_v%03d.abc" % (d, i)):
        i += 1
    return "%s/slime_v%03d.abc" % (d, i)


def clean():
    _drop_alembic()
    for node in (GROUP, NUCLEUS, "slime_mat", "slime_matSG", "slime_baked", SPLAT_GROUP):
        if cmds.objExists(node):
            cmds.delete(node)
    for n in cmds.ls("slime_*", type="nucleus") or []:
        cmds.delete(n)


def _key(plug, pairs, tangent="linear"):
    cmds.cutKey(plug, clear=True)
    for f, v in pairs:
        cmds.setKeyframe(plug, time=f, value=v, inTangentType=tangent, outTangentType=tangent)


def _rate_keys(kind, cut, size):
    L = LOOK
    b = L["burstRate"] * size
    keys = [(START, 0.0), (cut - 0.02, 0.0), (cut, b), (cut + 2, b * 0.85), (cut + 4, b * 0.3)]
    if kind == "stream":
        # pulsing jets: heartbeat spurts that fade over the shot
        step = FPS / L["pulseHz"]
        f = cut + 5.0
        n = 0
        while f < END:
            fade = max(0.25, 1.0 - (f - cut) / (END - cut + 20.0))
            peak = L["streamRate"] * size * fade
            keys.append((f, peak * 0.15))
            keys.append((f + step * 0.3, peak))
            keys.append((f + step * 0.65, peak * 0.2))
            f += step
            n += 1
    else:
        keys += [(cut + 8, L["trailRate"] * size), (cut + 18, L["trailRate"] * size * 0.5),
                 (cut + 32, L["trailRate"] * size * 0.15), (cut + 40, 0.0)]
    return [(min(f, END), v) for f, v in keys]


def _speed_keys(kind, cut, size):
    L = LOOK
    b = L["burstSpeed"] * (0.8 + 0.2 * size)
    keys = [(START, b), (cut + 3, b)]
    if kind == "stream":
        step = FPS / L["pulseHz"]
        f = cut + 5.0
        while f < END:
            s = L["streamSpeed"] * (0.8 + 0.2 * size)
            keys.append((f, s * 0.4))
            keys.append((f + step * 0.3, s))
            keys.append((f + step * 0.65, s * 0.35))
            f += step
    else:
        keys += [(cut + 8, L["trailSpeed"]), (cut + 40, L["trailSpeed"] * 0.5)]
    return [(min(f, END), v) for f, v in keys]


def _source(name, joint, inner, cut, size, kind, particle):
    drv = cmds.spaceLocator(name="slime_%s_drv" % name)[0]
    cmds.parent(drv, GROUP)
    cmds.setAttr(drv + ".localScale", 4, 4, 4)
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
        # +X out of the wound: aim -X at the joint on the body side
        cmds.aimConstraint(inner, drv, aimVector=(-1, 0, 0), upVector=(0, 1, 0),
                           worldUpType="scene")
    em = cmds.emitter(position=(0, 0, 0), type="direction", name="slime_%s_em" % name,
                      rate=0, speed=1, speedRandom=0.0, spread=0.28,
                      directionX=1, directionY=0, directionZ=0)
    em = em[-1] if isinstance(em, list) else em
    em = cmds.parent(em, drv, relative=True)[0]
    cmds.xform(em, translation=(0, 0, 0), rotation=(0, 0, 0))
    cmds.setAttr(em + ".minDistance", 0)
    cmds.setAttr(em + ".maxDistance", 1.2 * size)
    cmds.connectDynamic(particle, emitters=em)
    L = LOOK
    _key(em + ".rate", _rate_keys(kind, cut, size))
    speeds = _speed_keys(kind, cut, size)
    _key(em + ".speed", speeds)
    # speedRandom is a range in cm/s: a share of the speed, wide in the burst
    tail = L["streamSpeedRandom"] if kind == "stream" else 0.7
    share = [(f, L["burstSpeedRandom"] if f <= cut + 3 else tail) for f, _ in speeds]
    _key(em + ".speedRandom", [(f, v * k) for (f, v), (_, k) in zip(speeds, share)])
    # a wide spray at the cut, a tighter jet after it
    tail = L["streamSpread"] if kind == "stream" else L["trailSpread"]
    _key(em + ".spread", [(START, L["burstSpread"]), (cut + 3, L["burstSpread"]), (cut + 6, tail)])
    return drv, em


def _collider(mesh):
    before = set(cmds.ls(type="nRigid") or [])
    cmds.select(mesh, r=True)
    mel.eval("makeCollideNCloth;")
    rig = [n for n in cmds.ls(type="nRigid") if n not in before]
    for r in rig:
        cmds.setAttr(r + ".thickness", 0.6)
        cmds.setAttr(r + ".friction", 0.6)
        cmds.setAttr(r + ".stickiness", 0.6)
        t = cmds.listRelatives(r, parent=True)[0]
        cmds.parent(t, GROUP)
        cmds.rename(t, "slime_collide_" + mesh.split(":")[-1])
    return rig


def build():
    clean()
    now = cmds.currentTime(q=True)
    cmds.currentTime(START)
    cmds.createNode("transform", name=GROUP)

    nuc = cmds.createNode("nucleus", name=NUCLEUS)
    cmds.connectAttr("time1.outTime", nuc + ".currentTime")
    mel.eval('global string $gActiveNucleusNode; $gActiveNucleusNode = "%s";' % nuc)
    cmds.setAttr(nuc + ".startFrame", START)
    cmds.setAttr(nuc + ".spaceScale", 0.01)
    cmds.setAttr(nuc + ".subSteps", 4)
    cmds.setAttr(nuc + ".maxCollisionIterations", 6)
    cmds.setAttr(nuc + ".usePlane", 1)
    cmds.setAttr(nuc + ".planeOrigin", 0, 0, 0)
    cmds.setAttr(nuc + ".planeNormal", 0, 1, 0)
    cmds.setAttr(nuc + ".planeBounce", LOOK["planeBounce"])
    cmds.setAttr(nuc + ".planeFriction", LOOK["planeFriction"])
    cmds.setAttr(nuc + ".planeStickiness", LOOK["planeStickiness"])

    pt = cmds.nParticle(name="slime_particles")
    ptT, pt = pt[0], pt[1]
    cmds.parent(ptT, GROUP)
    ptT = GROUP + "|" + ptT.split("|")[-1]
    pt = cmds.listRelatives(ptT, shapes=True, fullPath=True)[0]
    # make sure it lives on our nucleus
    nucs = cmds.listConnections(pt, type="nucleus") or []
    if nuc not in nucs:
        cmds.select(pt, r=True)
        mel.eval('assignNSolver "%s";' % nuc)
    L = LOOK
    for attr, val in (("radius", L["radius"]), ("enableSPH", L["liquid"]), ("viscosity", L["viscosity"]),
                      ("incompressibility", L["incompressibility"]), ("restDensity", L["restDensity"]),
                      ("surfaceTension", L["surfaceTension"]), ("stickiness", L["stickiness"]),
                      ("friction", L["friction"]), ("drag", L["drag"]), ("inheritFactor", L["inherit"]),
                      ("selfCollide", 1), ("collide", 1), ("conserve", 1.0), ("lifespanMode", 0),
                      ("bounce", 0.1), ("radiusScaleRandomize", L["radiusRandom"]), ("maxCount", 250000)):
        if cmds.attributeQuery(attr, node=pt, exists=True):
            cmds.setAttr(pt + "." + attr, val)
        else:
            print("no attr", attr)
    # a drop that reaches the floor leaves the simulation: a splat takes its place
    for ln in ("lifespanPP", "lifespanPP0"):
        if not cmds.attributeQuery(ln, node=pt, exists=True):
            cmds.addAttr(pt, longName=ln, dataType="doubleArray")
    cmds.setAttr(pt + ".lifespanMode", 3)
    cmds.dynExpression(pt, string="lifespanPP = 1000;", creation=True)
    cmds.dynExpression(pt, string="vector $p = position; if ($p.y < %g) lifespanPP = 0;" % FLOOR_KILL,
                       runtimeAfterDynamics=True)

    for name, (joint, inner, cut, size, kind) in SOURCES.items():
        _source(name, joint, inner, cut, size, kind, pt)

    # Skinned colliders (100k vertices) cost ~6 s a frame; the floor is the
    # nucleus plane and the slime does not need the body.
    for mesh in COLLIDERS:
        _collider(mesh)

    cmds.currentTime(now)
    print("built", pt)
    return pt


def particle():
    return cmds.listRelatives(GROUP + "|slime_particles", shapes=True, fullPath=True)[0]


def output_mesh():
    """The live blobby mesh of the particles (particleToPoly)."""
    pt = particle()
    existing = cmds.listConnections(pt + ".outMesh", type="mesh", shapes=True) or []
    if existing:
        shape = existing[0]
    else:
        cmds.select(pt, r=True)
        mel.eval("particleToPoly;")
        shape = cmds.listConnections(pt + ".outMesh", type="mesh", shapes=True)[0]
        t = cmds.listRelatives(shape, parent=True)[0]
        t = cmds.parent(t, GROUP)[0]
        t = cmds.rename(t, "slime_liveMesh")
        shape = cmds.listRelatives(t, shapes=True, fullPath=True)[0]
    for attr, val in MESH.items():
        cmds.setAttr(pt + "." + attr, val)
    return cmds.listRelatives(shape, parent=True, fullPath=True)[0]


def material():
    if not cmds.objExists("slime_mat"):
        m = cmds.shadingNode("blinn", asShader=True, name="slime_mat")
        sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name="slime_matSG")
        cmds.connectAttr(m + ".outColor", sg + ".surfaceShader")
        cmds.setAttr(m + ".color", *LOOK["colour"])
        cmds.setAttr(m + ".specularColor", 0.45, 0.5, 0.3)
        cmds.setAttr(m + ".eccentricity", 0.12)
        cmds.setAttr(m + ".specularRollOff", 0.9)
        cmds.setAttr(m + ".diffuse", 0.75)
        cmds.setAttr(m + ".translucence", 0.0)
        cmds.setAttr(m + ".transparency", 0.08, 0.08, 0.08)
    return "slime_matSG"


class _Landings(object):
    """Every drop that leaves the simulation near the floor: where, how fast, how big.

    Read on every frame AbcExport evaluates (its per-frame callback), so the
    splats come from the very simulation the air mesh is baked from.
    """

    def __init__(self, shape):
        import maya.OpenMaya as om1
        import maya.OpenMayaFX as fx
        sel = om1.MSelectionList()
        sel.add(shape)
        obj = om1.MObject()
        sel.getDependNode(0, obj)
        self.om1, self.ps = om1, fx.MFnParticleSystem(obj)
        self.prev = {}
        self.landed = []          # (frame, x, z, vx, vz, radius)

    def frame(self):
        om1, ps = self.om1, self.ps
        f = cmds.currentTime(q=True)
        ids, pos, vel, rad = om1.MIntArray(), om1.MVectorArray(), om1.MVectorArray(), om1.MDoubleArray()
        ps.particleIds(ids)
        ps.position(pos)
        ps.velocity(vel)
        try:
            ps.radius(rad)
        except Exception:
            rad = None
        now = {}
        r0 = LOOK["radius"]
        for i in range(ids.length()):
            p = pos[i]
            if p.y < 40.0:
                v = vel[i]
                now[ids[i]] = (p.x, p.y, p.z, v.x, v.z, rad[i] if rad is not None and rad.length() > i else r0)
        alive = set(ids[i] for i in range(ids.length()))
        for pid, (x, y, z, vx, vz, r) in self.prev.items():
            if pid not in alive:
                self.landed.append((f, x, z, vx, vz, r))
        self.prev = now


def bake(path=None):
    import sys
    live = output_mesh()
    cmds.sets(live, edit=True, forceElement=material())
    path = path or _next_path()
    cache_on = cmds.evaluator(name="cache", q=True, en=True)
    if cache_on:
        cmds.evaluator(name="cache", enable=False)
    cmds.setAttr(NUCLEUS + ".enable", 1)
    cmds.setAttr(GROUP + ".visibility", 1)
    cmds.currentTime(START)
    rec = _Landings(particle())
    sys._slime_landings = rec
    job = ("-frameRange %d %d -step 1 -worldSpace -uvWrite -writeVisibility -dataFormat ogawa "
           "-pythonPerFrameCallback \"import sys; sys._slime_landings.frame()\" -root %s -file \"%s\"") % (
        START, END, live, path)
    cmds.AbcExport(j=job)
    if cache_on:
        cmds.evaluator(name="cache", enable=True)
    load(path)
    landed = rec.landed
    import json
    with open(path[:-4] + "_landings.json", "w") as fh:
        json.dump(landed, fh)
    splats(landed)
    return path, len(landed)


def load(path):
    if not cmds.pluginInfo("AbcImport", q=True, loaded=True):
        cmds.loadPlugin("AbcImport")
    _drop_alembic()
    if cmds.objExists("slime_baked"):
        cmds.delete("slime_baked")
    grp = cmds.createNode("transform", name="slime_baked")
    cmds.AbcImport(path, mode="import", reparent=grp)
    for t in cmds.listRelatives(grp, children=True, fullPath=True) or []:
        cmds.rename(t, "slime_mesh")
    for m in cmds.listRelatives(grp, allDescendents=True, type="mesh", fullPath=True) or []:
        cmds.sets(m, edit=True, forceElement=material())
        # the nParticles' own colour comes along as vertex colours (a mint ramp)
        cmds.setAttr(m + ".displayColors", 0)
    cmds.select(clear=True)
    # the live simulation off: the viewport plays the baked mesh only
    cmds.setAttr(NUCLEUS + ".enable", 0)
    cmds.setAttr(GROUP + ".visibility", 0)
    return grp


# ---------------------------------------------------------------- floor splats

SPLAT_GROUP = "slime_splats"
SPLAT = {
    "thickness": 0.22,        # cm a landed drop spreads to
    "merge": 0.85,            # a drop inside this share of a splat's radius feeds it
    "minRadius": 0.6,         # cm
    "keyEvery": 2,            # frames between a growing splat's scale keys
    "spreadFrames": 3,        # a fresh splat reaches its size in this many frames
    "y": 0.05,                # above the floor
}


def _outline(rng, radius, stretch, spikes, n=96):
    """A splat's edge in its own frame (+X the way the drops were going)."""
    pts = []
    # a few low harmonics make it lumpy, spikes make the tendrils
    harm = [(k, rng.uniform(0.03, 0.12) / k ** 0.5, rng.uniform(0, 2 * math.pi)) for k in range(2, 7)]
    for i in range(n):
        a = 2 * math.pi * i / n
        r = 1.0 + sum(amp * math.sin(k * a + ph) for k, amp, ph in harm)
        for sa, sl, sw in spikes:
            d = math.atan2(math.sin(a - sa), math.cos(a - sa))
            r += sl * math.exp(-(d / sw) ** 2)
        x, z = math.cos(a) * r, math.sin(a) * r
        if x > 0:
            x *= stretch
        pts.append((x * radius, z * radius))
    return pts


def _splat_mesh(name, cx, cz, angle, radius, speed, seed, y):
    import random
    import maya.api.OpenMaya as om
    rng = random.Random(seed)
    stretch = 1.0 + min(1.6, speed / 450.0)
    nspike = rng.randint(4, 7) + int(min(8, speed / 120.0))
    spikes = []
    for _ in range(nspike):
        fwd = rng.random() < 0.6
        a = rng.gauss(0, 0.6) if fwd else rng.uniform(0, 2 * math.pi)
        spikes.append((a, rng.uniform(0.15, 0.55 if not fwd else 0.6 + min(1.0, speed / 500.0)),
                       rng.uniform(0.04, 0.1)))
    verts, counts, conn = [], [], []

    def blob(outline, h, ox=0.0, oz=0.0):
        base = len(verts)
        verts.append(om.MPoint(ox, h, oz))
        inner = []
        for x, z in outline:
            verts.append(om.MPoint(ox + x * 0.62, h * 0.72, oz + z * 0.62))
        for x, z in outline:
            verts.append(om.MPoint(ox + x, 0.0, oz + z))
        n = len(outline)
        for i in range(n):
            j = (i + 1) % n
            counts.append(3); conn.extend([base, base + 1 + j, base + 1 + i])
            counts.append(4); conn.extend([base + 1 + i, base + 1 + j, base + 1 + n + j, base + 1 + n + i])

    h = min(0.9, 0.05 * radius + 0.12)
    blob(_outline(rng, radius, stretch, spikes), h)
    # satellites, flung mostly forward
    for _ in range(rng.randint(3, 7) + int(min(10, speed / 80.0))):
        fwd = rng.random() < 0.7
        a = rng.gauss(0, 0.45) if fwd else rng.uniform(0, 2 * math.pi)
        d = radius * rng.uniform(1.15, 2.2 + (min(1.5, speed / 400.0) if fwd else 0.0))
        r = radius * rng.uniform(0.025, 0.11)
        ox, oz = math.cos(a) * d * (stretch if math.cos(a) > 0 else 1.0), math.sin(a) * d
        blob(_outline(rng, r, 1.0 + 0.6 * fwd, [], n=12), min(0.4, 0.3 * r + 0.05), ox, oz)

    t = cmds.createNode("transform", name=name, parent=SPLAT_GROUP)
    fn = om.MFnMesh()
    sel = om.MSelectionList(); sel.add(t)
    fn.create(verts, counts, conn, parent=sel.getDependNode(0))
    shape = cmds.listRelatives(t, shapes=True, fullPath=True)[0]
    cmds.polySoftEdge(shape, angle=180, constructionHistory=False)
    cmds.xform(t, translation=(cx, y, cz), rotation=(0, -math.degrees(angle), 0))
    return t, shape


def splats(landed):
    """Floor splats grown from the landings, keyed to appear and spread."""
    if cmds.objExists(SPLAT_GROUP):
        cmds.delete(SPLAT_GROUP)
    cmds.createNode("transform", name=SPLAT_GROUP)
    S = SPLAT
    landed = sorted(landed)
    pool = []          # dicts: x, z, vol, area history, momentum
    cell = 20.0
    grid = {}

    def radius_of(vol):
        return max(S["minRadius"], math.sqrt(vol / S["thickness"] / math.pi))

    for f, x, z, vx, vz, r in landed:
        vol = 4.18879 * r ** 3
        best, bd = None, 1e9
        gx, gz = int(x // cell), int(z // cell)
        for i in range(gx - 3, gx + 4):
            for j in range(gz - 3, gz + 4):
                for s in grid.get((i, j), ()):
                    d = math.hypot(s["x"] - x, s["z"] - z)
                    if d < radius_of(s["vol"]) * S["merge"] + r and d < bd:
                        best, bd = s, d
        if best is None:
            best = {"x": x, "z": z, "vol": 0.0, "hist": [], "mx": 0.0, "mz": 0.0, "first": f}
            pool.append(best)
            grid.setdefault((gx, gz), []).append(best)
        best["vol"] += vol
        best["n"] = best.get("n", 0) + 1
        best["hist"].append((f, best["vol"]))
        if f - best["first"] < 3:
            best["mx"] += vx * vol
            best["mz"] += vz * vol
            best.setdefault("n0", 0.0)
            best["n0"] += vol

    made = 0
    for k, s in enumerate(pool):
        R = radius_of(s["vol"])
        if s.get("n", 0) < S.get("minDrops", 1):
            continue
        n0 = s.get("n0", s["vol"]) or 1.0
        vx, vz = s["mx"] / n0, s["mz"] / n0
        speed = math.hypot(vx, vz)
        angle = math.atan2(vz, vx)
        t, shape = _splat_mesh("slime_splat%04d" % k, s["x"], s["z"], angle, R, speed, 1000 + k,
                               S["y"] + 0.002 * (k % 50))
        cmds.sets(shape, edit=True, forceElement=material())
        # keys: hidden until the first drop, a quick spread, then growth with the pool
        first = s["hist"][0][0]
        keys = [(first - 1, 0.0)]
        grow = S["spreadFrames"]
        last = None
        for f, vol in s["hist"]:
            if last is not None and f - last < S["keyEvery"]:
                continue
            last = f
            keys.append((f + grow, radius_of(vol) / R))
        keys.insert(1, (first, 0.35 * keys[1][1]))
        keys.append((s["hist"][-1][0] + grow, 1.0))
        done = set()
        for f, v in sorted(keys):
            f = min(f, END)
            if f in done:
                continue
            done.add(f)
            for ax in "xz":
                cmds.setKeyframe(t, attribute="s" + ax, time=f, value=max(v, 0.001),
                                 inTangentType="linear", outTangentType="linear")
        cmds.setKeyframe(t, attribute="sy", time=first - 1, value=0.001, outTangentType="step")
        cmds.setKeyframe(t, attribute="sy", time=first, value=1.0, outTangentType="step")
        cmds.setKeyframe(t, attribute="v", time=first - 1, value=0, outTangentType="step")
        cmds.setKeyframe(t, attribute="v", time=first, value=1, outTangentType="step")
        made += 1
    print("splats", made, "from", len(landed), "landings")
    return made
