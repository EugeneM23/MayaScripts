"""Our CAT matched to a reference cycle: the same measurements read off the reference and off what
catmodel generates, and the knobs moved until they agree. numpy only.

`measure(skel, frames)` - a cycle's numbers in its own character frame (frames: [{leaf: 4x4}] of one
closed cycle, the last frame the first moved by the travel). `fit(skel_ref, ref_frames, fps)` - (knobs,
ref numbers, ours numbers, rows): the knobs read off the reference, then refined by generating on the
reference's own skeleton and correcting each knob by its own measurement."""

import math

import numpy as np

import catmodel as cm

UP = cm.UP


# ---- reading a cycle ----

def _track(frames, leaf):
    return np.array([f[leaf] for f in frames])


def _harmonic(values, k):
    """(cos part, sin part) of the k-th harmonic of a periodic series sampled at u = i/n."""
    n = len(values)
    u = np.arange(n) / float(n)
    v = np.asarray(values, dtype=float)
    return (2.0 / n * float(np.sum(v * np.cos(2 * np.pi * k * u))),
            2.0 / n * float(np.sum(v * np.sin(2 * np.pi * k * u))))


def _project(values, k, shift, sign=1.0, shape="cos"):
    """The amplitude A in `sign * A * shape(2 pi (k u - shift))` that fits `values` best."""
    c, s = _harmonic(values, k)
    phase = 2 * math.pi * shift
    if shape == "cos":                      # cos(x - p) = cos x cos p + sin x sin p
        return sign * (c * math.cos(phase) + s * math.sin(phase))
    return sign * (-c * math.sin(phase) + s * math.cos(phase))    # sin(x - p)


def _angles(q, fwd, left):
    """(yaw about up, roll about fwd, pitch about left) of a world rotation `q` (column form) taken as
    rot(up, yaw) @ rot(fwd, roll) @ rot(left, pitch), degrees."""
    basis = np.column_stack([left, UP, fwd])               # x left, y up, z fwd
    m = basis.T @ q @ basis                                 # = Ry(yaw) Rz(roll) Rx(pitch)
    roll = math.degrees(math.asin(max(-1.0, min(1.0, m[1, 0]))))
    yaw = math.degrees(math.atan2(-m[2, 0], m[0, 0]))
    pitch = math.degrees(math.atan2(-m[1, 2], m[1, 1]))
    return yaw, roll, pitch


def _rotvec(q):
    """The rotation vector (degrees) of a column-form rotation."""
    angle = math.acos(max(-1.0, min(1.0, (np.trace(q) - 1.0) / 2.0)))
    if angle < 1e-9:
        return np.zeros(3)
    axis = np.array([q[2, 1] - q[1, 2], q[0, 2] - q[2, 0], q[1, 0] - q[0, 1]])
    norm = np.linalg.norm(axis)
    if norm < 1e-9:
        return np.zeros(3)
    return axis / norm * math.degrees(angle)


def _delta(skel, leaf, m):
    """The world rotation (column form) taking the rest of `leaf` to its frame `m`."""
    return m[:3, :3].T @ skel.rest[leaf][:3, :3]


def _unwrap(series):
    out = list(series)
    for i in range(1, len(out)):
        while out[i] - out[i - 1] > 180:
            out[i] -= 360
        while out[i] - out[i - 1] < -180:
            out[i] += 360
    return out


def _runs(flags):
    """[(start, length)] of the True runs of a periodic flag list."""
    n = len(flags)
    if all(flags):
        return [(0, n)]
    if not any(flags):
        return []
    start = next(i for i in range(n) if not flags[i])
    out, i = [], 0
    while i < n:
        j = (start + i) % n
        if flags[j]:
            length = 0
            while length < n and flags[(j + length) % n]:
                length += 1
            out.append((j, length))
            i += length
        else:
            i += 1
    return out


def _shape_of(progress):
    """The step shape whose foot has gone `progress` of its swing at a quarter of it."""
    lo, hi = -1.0, 1.0
    for _ in range(40):
        mid = (lo + hi) / 2.0
        if cm.step_progress(0.25, mid) > progress:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def _treadmill(skel, frames):
    """How fast the ground runs under a cycle walked on the spot (cm a frame, horizontal): the median
    velocity of the feet while they are down (ankle or ball within 2 % of the leg of its lowest), or None
    when they stand still."""
    n = len(frames) - 1
    L = skel.leg
    seen = []
    for side in ("l", "r"):
        leg = skel.legs[side]
        for leaf in (leg["foot"], leg["ball"]):
            if not leaf:
                continue
            pts = [frames[i][leaf][3, :3] for i in range(n + 1)]
            low = min(p[1] for p in pts[:n])
            for i in range(n):
                if pts[i][1] < low + 0.02 * L and pts[i + 1][1] < low + 0.02 * L:
                    seen.append(cm.flat(pts[i + 1] - pts[i]))
    if len(seen) < 4:
        return None
    belt = np.median(np.array(seen), axis=0)
    return belt if np.linalg.norm(belt) > 0.002 * L else None


def walked(skel, frames):
    """(frames, on the spot?) - a cycle walked on the spot taken off its treadmill: every frame moved
    against the ground's run, so a planted foot stands still and the body travels (a moving cycle comes
    back as it is)."""
    pel = _track(frames, skel.pelvis)
    travel = cm.flat(pel[-1, 3, :3] - pel[0, 3, :3])
    if np.linalg.norm(travel) >= 0.05 * skel.leg:
        return frames, False
    belt = _treadmill(skel, frames)
    if belt is None:
        return frames, True
    out = []
    for i, frame in enumerate(frames):
        moved = {}
        for leaf, m in frame.items():
            m = m.copy()
            m[3, :3] -= belt * i
            moved[leaf] = m
        out.append(moved)
    return out, True


def measure(skel, frames):
    """The numbers of a closed cycle (dict). Angles in degrees, lengths in shares of the leg. A cycle walked
    on the spot is read off its treadmill (`walked`) and says so in "spot"."""
    frames, on_spot = walked(skel, frames)
    n = len(frames) - 1
    L = skel.leg
    pel = _track(frames, skel.pelvis)
    travel = pel[-1, 3, :3] - pel[0, 3, :3]
    flat_travel = cm.flat(travel)
    # facing: the rest forward carried by the pelvis, averaged
    facings = [cm.flat(_delta(skel, skel.pelvis, pel[i]) @ skel.fwd) for i in range(n)]
    fwd = cm.unit(np.mean(facings, axis=0))
    left = cm.unit(np.cross(UP, fwd))                   # the model's handedness: fwd = left x up
    out = {"frames": n, "leg": L, "_fwd": fwd}
    dist = float(np.linalg.norm(flat_travel))
    out["stride"] = dist / 2.0 / L
    out["spot"] = on_spot
    out["direction"] = 0.0 if dist < 0.05 * L else math.degrees(math.atan2(float(np.dot(flat_travel, left)),
                                                                          float(np.dot(flat_travel, fwd))))
    out["gradient"] = 0.0 if dist < 1e-6 else math.degrees(math.atan2(float(travel[1]), dist))
    move = travel / float(n)

    def detrended(i, p):
        return p - move * i

    # feet: contact = heel or ball near its lowest and slow against the body
    body_speed = float(np.linalg.norm(move))
    feet = {}
    for side in ("l", "r"):
        leg = skel.legs[side]
        foot = _track(frames, leg["foot"])
        ball_leaf = leg["ball"]
        ball = _track(frames, ball_leaf) if ball_leaf else None
        a0 = skel.rest[leg["foot"]]
        heel_local = (np.array([a0[3, 0], skel.ground, a0[3, 2], 1.0]) @ np.linalg.inv(a0))
        heel = np.array([(heel_local @ foot[i])[:3] for i in range(n + 1)])
        ballp = ball[:, 3, :3] if ball is not None else foot[:, 3, :3]
        down = []
        for i in range(n):
            j = i + 1
            ok = False
            for pts in (heel, ballp):
                low = pts[:n, 1].min()
                speed = float(np.linalg.norm(cm.flat(pts[j] - pts[i])))
                if pts[i, 1] < low + 0.02 * L and speed < max(0.35 * body_speed, 0.01 * L):
                    ok = True
            down.append(ok)
        runs = _runs(down)
        start, length = max(runs, key=lambda r: r[1]) if runs else (0, 0)
        d0 = skel.pos[ball_leaf] - skel.pos[leg["foot"]] if ball_leaf else skel.fwd
        rest_pitch = math.degrees(math.asin(cm.unit(d0)[1]))
        pitch = []
        yaw = []
        for i in range(n):
            d = (ballp[i] - foot[i, 3, :3]) if ball_leaf else (foot[i, :3, :3].T @ np.linalg.inv(a0[:3, :3]) @ d0)
            pitch.append(math.degrees(math.asin(max(-1, min(1, cm.unit(d)[1])))) - rest_pitch)
            f = cm.flat(d)
            yaw.append(math.degrees(math.atan2(float(np.dot(f, left)), float(np.dot(f, fwd)))))
        rest_yaw = math.degrees(math.atan2(float(np.dot(cm.flat(d0), skel.left)), float(np.dot(cm.flat(d0), skel.fwd))))
        mid = (start + length // 2) % n
        swing = [(start + length + i) % n for i in range(n - length)]
        ank_y = foot[:n, 3, 1]
        lift = float(ank_y[swing].max() - ank_y[start:start + 1].min()) if swing else 0.0
        peak_at = (int(np.argmax(ank_y[swing])) + 0.5) / max(1, len(swing)) if swing else 0.5
        ball_lift = float(ballp[swing, 1].max() - ballp[:n, 1].min()) if swing else 0.0
        # swing progress at a quarter of the swing
        quarter = 0.25
        if len(swing) >= 4:
            path = []
            k0 = swing[0]
            for i in range(k0, k0 + len(swing) + 1):
                frame = i % n
                wrap = (i // n)
                p = foot[frame, 3, :3] + travel * wrap
                path.append(float(np.dot(cm.flat(p - foot[k0, 3, :3]), cm.unit(flat_travel) if dist > 1e-6 else fwd)))
            total = path[-1] if abs(path[-1]) > 1e-6 else 1.0
            q_index = quarter * len(swing)
            lo = int(math.floor(q_index))
            frac = q_index - lo
            prog = (path[lo] * (1 - frac) + path[min(lo + 1, len(path) - 1)] * frac) / total
        else:
            prog = quarter
        thigh = _track(frames, leg["thigh"])
        ahead_dir = cm.unit(flat_travel) if dist > 1e-6 else fwd
        rel = [float(np.dot(cm.flat(foot[i % n, 3, :3] - thigh[i % n, 3, :3]), ahead_dir)) for i in range(2 * n)]
        centre = 0.5
        for i in range(length):
            a_, b_ = rel[start + i], rel[start + i + 1]
            if a_ >= 0 > b_:
                centre = (i + a_ / (a_ - b_)) / float(length)
                break
        reach = (max(rel[start + length:start + n + 1]) - rel[start + n]) / L if length < n else 0.0
        height = ((float(min(foot[i % n, 3, 1] for i in range(start, start + length))) - skel.pos[leg["foot"]][1]) / L
                  if length else 0.0)
        late_i = start + length + int(round(0.85 * (n - length)))
        lift_late = (float(foot[late_i % n, 3, 1]) - float(foot[start % n, 3, 1])) / L if length < n else 0.0
        late = [pitch[i % n] for i in range(start + length + (n - length) // 2, start + n)]
        toes = max(late) if late else 0.0
        hold = 0.6
        if swing:
            low_i = min(range(len(swing)), key=lambda j: pitch[swing[j]])
            half = pitch[swing[low_i]] / 2.0
            for j in range(low_i, len(swing)):
                if pitch[swing[j]] > half:
                    hold = (j + 0.5) / float(len(swing))
                    break
        feet[side] = dict(start=start, length=length, duty=length / float(n), lift=lift / L, lift_peak=peak_at,
                          stance_center=centre, swing_reach=reach, foot_height=height, swing_toes=toes, toe_hold=hold,
                          lift_late=lift_late,
                          ball_lift=ball_lift / L, heel_strike=max(pitch[start], pitch[(start + 1) % n], 0.0),
                          toe_off=max(0.0, -min(pitch[(start + length - 2 + i) % n] for i in range(4))),
                          toe_out=(yaw[mid] - rest_yaw) * (1.0 if side == "l" else -1.0),   # outward +
                          mid=foot[mid, 3, :3] - move * mid, progress=prog)
    for side in ("l", "r"):
        out[side] = feet[side]
    # the landing leg's least knee bend over the last quarter of its swing
    late_knees = []
    for side in ("l", "r"):
        leg = skel.legs[side]
        start, length = feet[side]["start"], feet[side]["length"]
        if length >= n:
            continue
        span = n - length
        for i in range(start + length + int(0.75 * span), start + n):
            fr = frames[i % n]
            h, kk, a = fr[leg["thigh"]][3, :3], fr[leg["calf"]][3, :3], fr[leg["foot"]][3, :3]
            c = float(np.dot(cm.unit(h - kk), cm.unit(a - kk)))
            late_knees.append(180.0 - math.degrees(math.acos(max(-1.0, min(1.0, c)))))
    if late_knees:
        out["swing_knee"] = min(late_knees)
    # the planted knee's flexion at the knee knobs' stance shares
    for share, name in cm.KNEE_KNOTS:
        vals = []
        for side in ("l", "r"):
            leg = skel.legs[side]
            start, length = feet[side]["start"], feet[side]["length"]
            if length < 2:
                continue
            pos = share * length
            i0 = int(math.floor(pos))
            frac = pos - i0

            def flex(i):
                fr = frames[(start + i) % n]
                h, kk, a = fr[leg["thigh"]][3, :3], fr[leg["calf"]][3, :3], fr[leg["foot"]][3, :3]
                c = float(np.dot(cm.unit(h - kk), cm.unit(a - kk)))
                return 180.0 - math.degrees(math.acos(max(-1.0, min(1.0, c))))
            vals.append(flex(i0) * (1 - frac) + flex(min(i0 + 1, length)) * frac)
        if vals:
            out[name] = sum(vals) / len(vals)
    out["duty"] = (feet["l"]["duty"] + feet["r"]["duty"]) / 2.0
    lc = feet["l"]["start"]
    out["left_contact"] = lc
    out["phase_r"] = ((feet["r"]["start"] - lc) / float(n)) % 1.0 - 0.5
    for key in ("lift", "lift_peak", "heel_strike", "toe_off", "toe_out", "progress", "stance_center",
                "swing_reach", "foot_height", "swing_toes", "toe_hold", "lift_late"):
        out[key] = (feet["l"][key] + feet["r"][key]) / 2.0
    out["step_shape"] = _shape_of(out["progress"])
    rest_wide = abs(float(np.dot(skel.pos[skel.legs["l"]["foot"]] - skel.pos[skel.legs["r"]["foot"]], skel.left)))
    wide = abs(float(np.dot(feet["l"]["mid"] - feet["r"]["mid"], left)))
    out["stance"] = wide / rest_wide if rest_wide > 1e-6 else 1.0

    # time measured from the left contact: u = (i - lc) / n
    def from_contact(series):
        series = list(series)
        return series[lc:] + series[:lc]

    d = out["duty"]
    pel_pos = [detrended(i, pel[i, 3, :3]) for i in range(n)]
    ys = from_contact([p[1] for p in pel_pos])
    out["height"] = (float(np.mean(ys)) - skel.pos[skel.pelvis][1]) / L
    out["_pelvis_y"] = [(y - float(np.mean(ys))) / L for y in ys]     # its bob, frame by frame from the contact
    c2, s2 = _harmonic(ys, 2)
    amp = math.hypot(c2, s2)
    low_q = (math.atan2(s2, c2) / (2 * math.pi) + 0.5) % 1.0       # where cos(2 pi (2u) - phi) is lowest, in steps
    out["bob"] = amp / L
    out["bob_phase"] = low_q
    centre = np.mean(pel_pos, axis=0)
    along = cm.unit(flat_travel) if dist > 1e-6 else fwd
    out["push"] = _project(from_contact([float(np.dot(p - centre, along)) for p in pel_pos]), 2,
                           out["bob_phase"], 1.0, "sin") / L
    out["weight_shift"] = _project(from_contact([float(np.dot(p - centre, left)) for p in pel_pos]), 1, d / 2.0) / L
    angles = [_angles(_delta(skel, skel.pelvis, pel[i]), fwd, left) for i in range(n)]
    yaw = from_contact(_unwrap([a[0] for a in angles]))
    roll = from_contact([a[1] for a in angles])
    pitch = from_contact([a[2] for a in angles])
    out["twist"] = _project(yaw, 1, 0.0, -1.0)
    out["roll"] = _project(roll, 1, d / 2.0)
    out["lean"] = float(np.mean(pitch))
    out["pitch"] = _project(pitch, 2, out["bob_phase"])
    # the chest against the pelvis
    if skel.spine:
        top = skel.spine[-1]
        chest = [_angles(_delta(skel, top, frames[i][top]), fwd, left) for i in range(n)]
        cyaw = from_contact(_unwrap([a[0] for a in chest]))
        croll = from_contact([a[1] for a in chest])
        cpitch = from_contact([a[2] for a in chest])
        chest_yaw = _project(cyaw, 1, 0.0, -1.0)
        out["counter"] = -chest_yaw / out["twist"] if abs(out["twist"]) > 0.5 else 0.8
        out["roll_cancel"] = 1.0 - (_project(croll, 1, d / 2.0) / out["roll"]) if abs(out["roll"]) > 0.5 else 1.0
        out["spine_lean"] = float(np.mean(cpitch)) - out["lean"]
        out["chest_yaw"] = chest_yaw
    # the fingers: each phalanx's curl about its own Z (the rotation vector's z of its turn from rest, in its
    # own axes), by joint, by finger and over the cycle
    curls = {}
    for leaf, (name, joint, side) in skel.fingers.items():
        p = skel.parent[leaf]
        rest_l = skel.rest[leaf][:3, :3] @ np.linalg.inv(skel.rest[p][:3, :3])
        series = []
        for i in range(n):
            local = frames[i][leaf][:3, :3] @ np.linalg.inv(frames[i][p][:3, :3])
            series.append(_rotvec((local @ np.linalg.inv(rest_l)).T)[2])
        curls[leaf] = (name, joint, side, from_contact(series))
    if curls:
        def mean_of(joint, fingers=("index", "middle", "ring", "pinky")):
            vals = [float(np.mean(s)) for (nm, j, _, s) in curls.values() if j == joint and nm in fingers]
            return sum(vals) / len(vals) if vals else 0.0
        out["knuckle_curl"] = mean_of(1)
        out["finger_curl"] = mean_of(2)
        out["tip_curl"] = mean_of(3)
        out["thumb_01"] = mean_of(1, ("thumb",))
        out["thumb_02"] = mean_of(2, ("thumb",))
        totals = {}
        for nm, j, _, s in curls.values():
            if nm != "thumb" and j in (1, 2):
                totals.setdefault(nm, []).append(float(np.mean(s)))
        per = dict((nm, sum(v) / len(v) * 2.0) for nm, v in totals.items() if nm in cm.FAN)
        if len(per) >= 2:
            mean_total = sum(per.values()) / len(per)
            num = sum(cm.FAN[nm] * (t - mean_total) for nm, t in per.items())
            den = sum(cm.FAN[nm] ** 2 for nm in per) * mean_total
            out["curl_fan"] = num / den if abs(den) > 1e-6 else 0.0
        flops = [math.hypot(*_harmonic(s, 1)) for (nm, j, _, s) in curls.values() if j == 2 and nm != "thumb"]
        out["finger_flop"] = sum(flops) / len(flops) if flops else 0.0
    # posture: each spine joint's and the neck's own bend (mean pitch of its turn against its parent)
    for leaf in list(skel.spine) + ([skel.neck] if skel.neck else []):
        p = skel.parent[leaf]
        name = "bend_neck" if leaf == skel.neck else "bend_" + skel.canonical.get(leaf, leaf)
        out[name] = float(np.mean([_angles(_delta(skel, leaf, frames[i][leaf]) @ _delta(skel, p, frames[i][p]).T,
                                           fwd, left)[2] for i in range(n)]))
    if skel.head:
        head = [_angles(_delta(skel, skel.head, frames[i][skel.head]), fwd, left) for i in range(n)]
        hyaw = from_contact(_unwrap([a[0] for a in head]))
        out["head_yaw"] = math.hypot(*_harmonic(hyaw, 1))
        out["nod"] = float(np.mean([a[2] for a in head]))
    # arms
    arms = {}
    for side, sign in cm.SIDES:
        arm = skel.arms[side]
        if not arm:
            continue
        up_ = _track(frames, arm["upperarm"])
        low = _track(frames, arm["lowerarm"])
        hand = _track(frames, arm["hand"])
        fwd_ang, out_ang, elbow = [], [], []
        for i in range(n):
            a = cm.unit(low[i, 3, :3] - up_[i, 3, :3])
            b = cm.unit(hand[i, 3, :3] - low[i, 3, :3])
            fwd_ang.append(math.degrees(math.atan2(float(np.dot(a, fwd)), float(-np.dot(a, UP)))))
            out_ang.append(math.degrees(math.atan2(float(np.dot(a, left)) * sign, float(-np.dot(a, UP)))))
            elbow.append(math.degrees(math.acos(max(-1.0, min(1.0, float(np.dot(a, b)))))))
        clav = arm["clavicle"]
        shoulder = 0.0
        if clav:
            p = skel.parent[clav]
            shoulder = float(np.mean([_angles(_delta(skel, clav, frames[i][clav]) @ _delta(skel, p, frames[i][p]).T,
                                              fwd, left)[1] for i in range(n)])) * sign
        inward, wrist = [], []
        for i in range(n):
            a = cm.unit(low[i, 3, :3] - up_[i, 3, :3])
            b = cm.unit(hand[i, 3, :3] - low[i, 3, :3])
            perp = b - a * float(np.dot(a, b))
            ahead = cm.unit(fwd - a * float(np.dot(a, fwd)))
            inside = -sign * left
            inside = cm.unit(inside - a * float(np.dot(a, inside)))
            if np.linalg.norm(perp) > 0.05:
                inward.append(math.degrees(math.atan2(float(np.dot(perp, inside)), float(np.dot(perp, ahead)))))
            wrist.append(_angles(_delta(skel, arm["hand"], hand[i]) @ _delta(skel, arm["lowerarm"], low[i]).T,
                                 fwd, left)[2])
        fwd_ang = from_contact(fwd_ang)
        elbow = from_contact(elbow)
        c1, s1 = _harmonic(fwd_ang, 1)
        amp1 = math.hypot(c1, s1)
        peak = (math.atan2(s1, c1) / (2 * math.pi)) % 1.0          # when the arm is furthest forward
        other_contact = 0.5 + out["phase_r"] if side == "l" else 0.0
        arms[side] = dict(swing=amp1, forward_at=peak, lag=((peak - other_contact + 0.5) % 1.0) - 0.5,
                          arm_out=float(np.mean(from_contact(out_ang))), elbow_mean=float(np.mean(elbow)),
                          elbow_swing=2 * math.hypot(*_harmonic(elbow, 1)), arm_fwd=float(np.mean(fwd_ang)),
                          shoulders=shoulder, forearm_in=float(np.mean(inward)) if inward else 0.0,
                          wrist=float(np.mean(wrist)))
    for key in ("swing", "lag", "arm_out", "elbow_mean", "elbow_swing", "arm_fwd", "shoulders", "forearm_in", "wrist"):
        vals = [arms[s][key] for s in arms]
        if vals:
            out[key if key.startswith("arm_") else "arm_" + key] = sum(vals) / len(vals)
    out["arms"] = arms
    return out


GROUPS = (
    ("pelvis", ("pelvis",)),
    ("spine", ("spine_01", "spine_02", "spine_03", "spine_04", "spine_05")),
    ("head", ("neck_01", "neck_02", "head")),
    ("legs", ("thigh_l", "calf_l", "thigh_r", "calf_r")),
    ("feet", ("foot_l", "ball_l", "foot_r", "ball_r")),
    ("arms", ("clavicle_l", "upperarm_l", "lowerarm_l", "clavicle_r", "upperarm_r", "lowerarm_r")),
    ("hands", ("hand_l", "hand_r")),
    ("fingers", tuple("%s_%s_%s" % (f, j, s) for f in ("thumb", "index", "middle", "ring", "pinky")
                      for j in ("01", "02", "03") for s in ("l", "r"))),
)


def _in_frame(skel, q, numbers):
    """A world rotation re-expressed in the cycle's own character frame (facing taken off)."""
    fwd = numbers["_fwd"]
    turn = cm.between(cm.flat(skel.fwd), fwd) if np.linalg.norm(cm.flat(skel.fwd) - fwd) > 1e-9 else np.eye(3)
    return turn.T @ q


def compare(skel, ref_frames, our_frames, ref, ours):
    """{group: mean degrees} between the two cycles' bone turns from rest, each in its own facing,
    frame by frame from each cycle's left contact (ours resampled onto the reference's frames)."""
    n, m = ref["frames"], ours["frames"]
    out = {}
    for name, bones in GROUPS:
        angles = []
        for leaf in bones:
            leaf = skel.by_name.get(leaf)
            if not leaf:
                continue
            for i in range(n):
                fi = (ref["left_contact"] + i) % n
                fo = int(round((ours["left_contact"] + i * m / float(n)))) % m
                qa = _in_frame(skel, _delta(skel, leaf, ref_frames[fi][leaf]), ref)
                qb = _in_frame(skel, _delta(skel, leaf, our_frames[fo][leaf]), ours)
                r = qa @ qb.T
                angles.append(math.degrees(math.acos(max(-1.0, min(1.0, (np.trace(r) - 1) / 2)))))
        if angles:
            out[name] = float(np.mean(angles))
    return out


# ---- fitting ----

# knob <- the measurement that moves with it most directly (a share of the error is put back each round)
LOOPS = (
    ("stride", "stride", 1.0),
    ("duty", "duty", 1.0),
    ("phase_r", "phase_r", 1.0),
    ("lift", "lift", 1.0),
    ("lift_peak", "lift_peak", 0.6),
    ("lift_late", "lift_late", 1.0),
    ("step_shape", "step_shape", 0.8),
    ("stance", "stance", 1.0),
    ("toe_out", "toe_out", 1.0),
    ("heel_strike", "heel_strike", 1.0),
    ("toe_off", "toe_off", 1.0),
    ("toe_hold", "toe_hold", 0.6),
    ("swing_toes", "swing_toes", 1.0),
    ("swing_reach", "swing_reach", 1.0),
    ("stance_center", "stance_center", 1.0),
    ("foot_height", "foot_height", 1.0),
    ("crouch", "height", -1.0),
    ("bob", "bob", 1.0),
    ("bob_phase", "bob_phase", 1.0),
    ("push", "push", 1.0),
    ("weight_shift", "weight_shift", 1.0),
    ("twist", "twist", 1.0),
    ("roll", "roll", 1.0),
    ("lean", "lean", 1.0),
    ("pitch", "pitch", 1.0),
    ("counter", "counter", 1.0),
    ("roll_cancel", "roll_cancel", 1.0),
    ("spine_lean", "spine_lean", 1.0),
    ("nod", "nod", 1.0),
    ("swing", "arm_swing", 1.0),
    ("arm_lag", "arm_lag", 1.0),
    ("arm_out", "arm_out", 1.0),
    ("elbow", "arm_elbow_mean", 1.0),
    ("elbow_swing", "arm_elbow_swing", 1.0),
    ("arm_forward", "arm_fwd", 1.0),
    ("shoulders", "arm_shoulders", 1.0),
    ("forearm_in", "arm_forearm_in", 1.0),
    ("hand_bend", "arm_wrist", -1.0),
    ("knee_plant", "knee_plant", 1.0),
    ("knee_load", "knee_load", 1.0),
    ("knee_mid", "knee_mid", 1.0),
    ("knee_lift", "knee_lift", 1.0),
    ("swing_knee", "swing_knee", 1.0),
    ("bend_spine_01", "bend_spine_01", 1.0),
    ("bend_spine_02", "bend_spine_02", 1.0),
    ("bend_spine_03", "bend_spine_03", 1.0),
    ("bend_spine_04", "bend_spine_04", 1.0),
    ("bend_spine_05", "bend_spine_05", 1.0),
    ("bend_neck", "bend_neck", 1.0),
    ("knuckle_curl", "knuckle_curl", 1.0),
    ("finger_curl", "finger_curl", 1.0),
    ("tip_curl", "tip_curl", 1.0),
    ("curl_fan", "curl_fan", 1.0),
    ("finger_flop", "finger_flop", 1.0),
    ("thumb_01", "thumb_01", 1.0),
    ("thumb_02", "thumb_02", 1.0),
)
PHASES = ("bob_phase",)
# the pelvis rides CAT's Pelvis Lift (crouch, bob, bob_phase) and the knees follow by IK: the knee drive is
# off and its knobs are not fitted; the spine joints' bends carry the posture, so spine_lean is not either
FIT_FIXED = {"knee_drive": 0.0, "spine_lean": 0.0}
FIT_SKIP = tuple(name for name, _, _ in LOOPS if name.startswith("knee_")) + ("spine_lean",)


def start_knobs(ref, fps):
    """A first guess straight from the reference's numbers."""
    k = dict(cm.DEFAULTS)
    k["step_time"] = ref["frames"] / 2.0
    k["on_spot"] = 1.0 if ref["spot"] else 0.0
    k["direction"] = ref["direction"]
    k["gradient"] = ref["gradient"]
    for knob, key, sign in LOOPS:
        if knob in k and key in ref:
            k[knob] = ref[key] * sign
    return cm.knobs(k)


def _wrap_error(err):
    return ((err + 0.5) % 1.0) - 0.5


def _scale(key):
    """How big an error of this measurement is worth one unit of cost."""
    if key in ("duty", "lift_peak", "stance_center", "toe_hold", "phase_r", "bob_phase", "arm_lag", "stance",
               "step_shape", "counter", "roll_cancel", "curl_fan"):
        return 0.05
    if key in ("stride", "lift", "lift_late", "swing_reach", "foot_height", "height", "bob", "push", "weight_shift"):
        return 0.01
    return 5.0                                       # degrees


def cost(ref, ours, skip=()):
    """The sum of the squared, scaled differences of every fitted measurement."""
    total = 0.0
    for knob, key, _ in LOOPS:
        if knob in skip or key not in ref or key not in ours:
            continue
        err = ref[key] - ours[key]
        if key in PHASES or key == "phase_r":
            err = _wrap_error(err)
        total += (err / _scale(key)) ** 2
    for key in ("height", "bob"):
        if key in ref and key in ours:
            total += ((ref[key] - ours[key]) / _scale(key)) ** 2
    return total


# what a percent of the leg off the reference's pelvis height costs, against the pose's mean degrees: the
# bob is seen as a shape, not only as an amplitude
TRACK_WEIGHT = 3.0


def pelvis_track(ref, ours):
    """How far the pelvis's height is from the reference's over the cycle (percent of the leg, rms): its bob
    frame by frame from each cycle's left contact (ours resampled onto the reference's frames), plus the
    difference of the mean heights."""
    a, b = np.asarray(ref.get("_pelvis_y", ())), np.asarray(ours.get("_pelvis_y", ()))
    if not len(a) or not len(b):
        return 0.0
    m = len(b)
    b = np.interp(np.arange(len(a)) * m / float(len(a)), np.arange(m + 1), np.append(b, b[0]))
    return 100.0 * (float(np.sqrt(np.mean((a - b) ** 2))) + abs(ref["height"] - ours["height"]))


def fit(skel_ref, ref_frames, fps, rounds=14):
    """(knobs, ref numbers, ours numbers, rows) - knobs that make catmodel walk like the reference: the pelvis
    by crouch, bob and bob_phase, its height judged frame by frame (`pelvis_track`), the knees by IK."""
    ref = measure(skel_ref, ref_frames)
    k = start_knobs(ref, fps)
    k.update(FIT_FIXED)
    skip = FIT_SKIP
    k = cm.knobs(k)
    best, best_cost = dict(k), None
    gain = 0.8

    def judged(knobs_):
        frames_ = cm.generate(skel_ref, knobs_, fps).frames
        ours_ = measure(skel_ref, frames_)
        pose = compare(skel_ref, ref_frames, frames_, ref, ours_)
        return ours_, (sum(pose.values()) + 0.05 * cost(ref, ours_, skip)
                       + TRACK_WEIGHT * pelvis_track(ref, ours_))

    for _ in range(rounds):
        ours, c = judged(k)
        if best_cost is None or c < best_cost:
            best, best_cost = dict(k), c
        else:
            gain = max(0.15, gain * 0.7)          # it got worse: smaller steps from the best so far
            k = dict(best)
            ours, _ = judged(k)
        moved = dict(k)
        for knob, key, sign in LOOPS:
            if knob not in k or key not in ref or key not in ours or knob in skip:
                continue
            err = ref[key] - ours[key]
            if key in PHASES or key == "phase_r":
                err = _wrap_error(err)
            moved[knob] = k[knob] + sign * err * (gain if key != "stride" else 1.0)
            if knob in PHASES:
                moved[knob] = moved[knob] % 1.0
        k = cm.knobs(moved)
    ours, c = judged(k)
    if best_cost is not None and c > best_cost:
        k = best
        ours, _ = judged(k)
    # the knobs say what the pelvis does: where a planted leg cannot reach, the cover cuts the top of the bob,
    # and the loops push the knobs on into the cut; the bob the cycle shows is the bob
    k = cm.knobs(dict(k, crouch=-ours["height"], bob=ours["bob"], bob_phase=ours["bob_phase"]))
    ours, _ = judged(k)
    rows = []
    for knob, key, sign in LOOPS:
        if key in ref and key in ours and knob in k and knob not in skip:
            rows.append((key, ref[key], ours[key], knob, k.get(knob)))
    return k, ref, ours, rows
