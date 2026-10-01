"""Unreal <-> Maya axis maps, measured rather than assumed (2026-10-01, the Tech Limb).

numpy only. Shared by make_techlimb_asset.py and verify_armor.py, so the verify re-derives the
mapping from Unreal's numbers on its own instead of trusting the asset script's.

Column vectors throughout: `maya = M @ ue`. Maya's worldMatrix is row-major with row vectors (rows
are the axes, the last row the translation); `row_world` turns it into axes-as-columns.
"""
import itertools

import numpy as np


def signed_permutations():
    """The 48 signed 3x3 permutation matrices."""
    out = []
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product((1.0, -1.0), repeat=3):
            m = np.zeros((3, 3))
            for row, col in enumerate(perm):
                m[row, col] = signs[row]
            out.append(m)
    return out


def nearest(a, b):
    """For each row of `a`, (index into `b`, distance) -- brute force, fine for a few thousand."""
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    index = np.empty(len(a), int)
    dist = np.empty(len(a))
    for start in range(0, len(a), 256):
        chunk = a[start:start + 256]
        d2 = ((chunk[:, None, :] - b[None, :, :]) ** 2).sum(axis=2)
        index[start:start + 256] = d2.argmin(axis=1)
        dist[start:start + 256] = np.sqrt(d2.min(axis=1))
    return index, dist


def best_map(a, b):
    """The signed permutation P for which every P @ a lands nearest on `b`: (P, worst distance)."""
    a = np.asarray(a, float)
    best = None
    for p in signed_permutations():
        _index, dist = nearest(a @ p.T, b)
        worst = float(dist.max())
        if best is None or worst < best[1]:
            best = (p, worst)
    return best


def round_to_permutation(m):
    """The signed permutation nearest `m` (the largest entry of each row), and how far `m` is from it."""
    m = np.asarray(m, float)
    p = np.zeros((3, 3))
    for row in range(3):
        col = int(np.abs(m[row]).argmax())
        p[row, col] = np.sign(m[row, col])
    return p, float(np.abs(m - p).max())


def ue_to_maya(ue_points, maya_points):
    """M with maya = M @ ue over paired points, as the signed permutation nearest the least-squares
    fit: (M, the fit's worst residual in cm after rounding)."""
    ue = np.asarray(ue_points, float)
    maya = np.asarray(maya_points, float)
    fit, _res, _rank, _sv = np.linalg.lstsq(ue, maya, rcond=None)
    m, _dev = round_to_permutation(fit.T)
    worst = float(np.linalg.norm(ue @ m.T - maya, axis=1).max())
    return m, worst


def row_world(matrix16):
    """Maya's row-major 16 floats -> (A: the axes as COLUMNS, t)."""
    w = np.asarray(matrix16, float).reshape(4, 4)
    return w[:3, :3].T.copy(), w[3, :3].copy()


def similarity(src, dst):
    """Umeyama: (s, R, t) with dst ~ s R src + t, R a proper rotation; and the worst residual."""
    src = np.asarray(src, float)
    dst = np.asarray(dst, float)
    mu_s, mu_d = src.mean(axis=0), dst.mean(axis=0)
    xs, xd = src - mu_s, dst - mu_d
    cov = xd.T @ xs / len(src)
    u, sig, vt = np.linalg.svd(cov)
    fix = np.eye(3)
    if np.linalg.det(u) * np.linalg.det(vt) < 0:
        fix[2, 2] = -1.0
    r = u @ fix @ vt
    var = (xs ** 2).sum() / len(src)
    s = float((sig * np.diag(fix)).sum() / var)
    t = mu_d - s * r @ mu_s
    worst = float(np.linalg.norm((s * (r @ src.T)).T + t - dst, axis=1).max())
    return s, r, t, worst
