"""poseclip - our poses onto a locomotion clip (a stop first): the model. numpy and the copied posemath
(maya.api.OpenMaya) - no maya.cmds.

The animator (2026-10-14): «Давай попробуем сделать инструмент который будет насаживать наши позы на
локомоушен циклы такие как вот стоп.» Walk Builder's pose machinery for a clip that is not a cycle: the pose
takes the place of the clip's REFERENCE (its still stretch - a stop's idle), the clip's motion about the
reference rides on top (the torso and head in world axes, the arms in locals), and the constraints are solved
again - each planted foot moved by one rigid motion of space (the stop's last contacts onto the pose's
stance), the legs by IK, the pelvis's height in proportion, sunk where a planted foot is out of reach, and
carried so the centre of mass keeps its place over the feet.

Row vectors (`world = local . parent`), centimetres, Y up.
Spec: docs/superpowers/specs/2026-10-14-pose-on-clip-design.md
"""
import math

import numpy as np

UP = np.array([0.0, 1.0, 0.0])
SIDES = ("l", "r")

STILL_SPEED = 1.5      # cm a frame: every body bone slower than this - the body stands still (the reference)
STILL_MIN = 8          # frames: the least still stretch that is a reference
FOOT_STILL = 2.0       # cm a frame: the ankle or the ball slower than this - the foot is planted
FOOT_NEAR = 4.0        # cm: the ankle or the ball this near its level in the reference - the foot is down
SETTLE = 10            # frames: two feet that stay down hand the weight over to half each in this long
GRIP_DIST = 30.0       # cm: a pose's hands this near each other hold one thing together
REACH = 0.995          # a planted leg never straighter than this share of its length (or the clip's own)
REACH_SIGMA = 3.0      # frames: the reach's sink blurred over this
CARRY_TOL = 0.005      # cm: the balance's carry stops this near the target
CARRY_STEPS = 8

PARTS = ("torso", "pelvis", "knees", "arms", "feet")

# de Leva's table as one weight a joint (Walk Builder's): the trunk at the thirds of pelvis..neck_01
TRUNK_MASS = (11.17, 16.33, 15.96)
HEAD_MASS = 6.94
LIMB_MASS = (("upperarm", "lowerarm", 2.71, 0.5772), ("lowerarm", "hand", 1.62, 0.4574),
             ("thigh", "calf", 14.16, 0.4095), ("calf", "foot", 4.33, 0.4459), ("foot", "ball", 1.37, 0.4415))
HAND_MASS = (0.61, 0.5)

HELPER_PREFIXES = ("ik_", "camera_", "weapon_", "interaction", "center_of_mass", "attach", "poi", "props_")
ARM_STEMS = ("clavicle", "upperarm", "lowerarm", "hand")


class Refusal(Exception):
    """A clip or a pose this tool does not read; the message says why."""


# ---- rotations (Walk Builder's, maya_walk/model.py) ----

def _unit(v):
    v = np.asarray(v, float)
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-12 else v * 0.0


def _any_perpendicular(e):
    return _unit(np.cross(e, np.eye(3)[int(np.argmin(np.abs(e)))]))


def _skew(w):
    z = np.zeros(w.shape[:-1])
    return np.stack([np.stack([z, -w[..., 2], w[..., 1]], -1),
                     np.stack([w[..., 2], z, -w[..., 0]], -1),
                     np.stack([-w[..., 1], w[..., 0], z], -1)], -2)


def exp_rot(w):
    """The row-vector rotation by |w| radians about w (right hand); w may be (..., 3)."""
    w = np.asarray(w, float)
    th = np.linalg.norm(w, axis=-1)[..., None, None]
    small = th < 1e-12
    k = _skew(w) / np.where(small, 1.0, th)
    eye = np.broadcast_to(np.eye(3), k.shape)
    column = eye + np.sin(th) * k + (1.0 - np.cos(th)) * (k @ k)
    return np.swapaxes(np.where(small, eye, column), -1, -2)


def log_rot(r):
    """The rotation vector w (|w| <= pi) with exp_rot(w) == r; r may be (..., 3, 3)."""
    c = np.swapaxes(np.asarray(r, float), -1, -2)
    th = np.arccos(np.clip((np.trace(c, axis1=-2, axis2=-1) - 1.0) / 2.0, -1.0, 1.0))
    v = np.stack([c[..., 2, 1] - c[..., 1, 2], c[..., 0, 2] - c[..., 2, 0], c[..., 1, 0] - c[..., 0, 1]], -1)
    sin = np.sin(th)
    ok = sin > 1e-7
    w = v * np.where(ok, th / (2.0 * np.where(ok, sin, 1.0)), 0.5)[..., None]
    near_pi = (~ok) & (th > 1.0)
    if np.any(near_pi):
        flat_c, flat_w = c.reshape(-1, 3, 3), np.array(w).reshape(-1, 3)
        flat_th = np.broadcast_to(th, near_pi.shape).reshape(-1)
        for i in np.nonzero(near_pi.reshape(-1))[0]:
            m = (flat_c[i] + np.eye(3)) / 2.0
            flat_w[i] = _unit(m[:, int(np.argmax(np.diag(m)))]) * flat_th[i]
        w = flat_w.reshape(w.shape)
    return w


def _proper(u, vt):
    m = u @ vt
    if np.linalg.det(m) < 0.0:
        u = u.copy()
        u[:, -1] *= -1.0
        m = u @ vt
    return m


def mean_rot(rs):
    """The chordal mean of rotations (n, 3, 3)."""
    u, _, vt = np.linalg.svd(np.sum(np.asarray(rs, float), axis=0))
    return _proper(u, vt)


def orthonormal(m):
    """The rotation nearest m's 3x3 part (scale and shear stripped)."""
    u, _, vt = np.linalg.svd(np.asarray(m, float)[:3, :3])
    return _proper(u, vt)


def toward(mean, target, alpha):
    """`mean` turned the share `alpha` of the way to `target`: exp(alpha . log(target . mean^-1)) . mean."""
    if alpha <= 0.0:
        return mean
    return exp_rot(alpha * log_rot(target @ mean.T)) @ mean


def power(r, k):
    """The rotation r to the power k: the same axis, k times the angle."""
    if k == 1.0:
        return r
    return exp_rot(k * log_rot(r))


def slerp(a, b, w):
    """From a (w 0) to b (w 1)."""
    if w <= 0.0:
        return a
    if w >= 1.0:
        return b
    return a @ exp_rot(w * log_rot(a.T @ b))


def blend_matrix(a, b, alpha):
    """Between two rigid 4x4s: the rotation `toward`, the translation lerped; 0 is `a`, 1 is `b`."""
    if alpha <= 0.0:
        return a
    out = np.eye(4)
    out[:3, :3] = toward(orthonormal(a[:3, :3]), orthonormal(b[:3, :3]), alpha)
    out[3, :3] = (1.0 - alpha) * np.asarray(a)[3, :3] + alpha * np.asarray(b)[3, :3]
    return out


def turned_about(v, axis, angle):
    """The vector `v` turned `angle` radians about the unit `axis` (right hand; Rodrigues)."""
    c, s = math.cos(angle), math.sin(angle)
    return v * c + np.cross(axis, v) * s + axis * float(np.dot(axis, v)) * (1.0 - c)


def matrix(rot, pos):
    out = np.eye(4)
    out[:3, :3] = rot
    out[3, :3] = pos
    return out


def yaw(angle):
    """The turn about up by `angle` radians."""
    return exp_rot([0.0, angle, 0.0])


def yaw_of(r):
    """A rotation's heading about up: where its forward (+Z) points on the floor (radians, 0 = +Z, + toward +X)."""
    fwd = np.asarray(r)[2]
    return math.atan2(float(fwd[0]), float(fwd[2]))


def two_bone(hip, ankle, l1, l2, bend, reach):
    """The knee of a hip-knee-ankle chain bending toward `bend`, the leg never straighter than
    reach . (l1 + l2). Returns (knee, the ankle it reaches, how far it falls short)."""
    v = np.asarray(ankle, float) - hip
    d = float(np.linalg.norm(v))
    e = v / d if d > 1e-9 else np.array([0.0, -1.0, 0.0])
    d_eff = max(min(d, reach * (l1 + l2)), abs(l1 - l2) + 1e-6)
    p = bend - np.dot(bend, e) * e
    p = _unit(p) if np.linalg.norm(p) > 1e-9 else _any_perpendicular(e)
    along = (l1 * l1 - l2 * l2 + d_eff * d_eff) / (2.0 * d_eff)
    height = math.sqrt(max(0.0, l1 * l1 - along * along))
    return hip + along * e + height * p, hip + d_eff * e, max(0.0, d - d_eff)


def _frame3(u, n):
    return np.stack([u, n, np.cross(u, n)])


def align(u_src, n_src, u_new, n_new):
    """The rotation taking the frame (u_src, n_src) onto (u_new, n_new): v . align = v'.
    Each n must be perpendicular to its u."""
    return _frame3(u_src, n_src).T @ _frame3(u_new, n_new)
