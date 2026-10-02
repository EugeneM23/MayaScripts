"""maya_hubglow - the glow of the hub's controls under the mouse, as numbers.

The animator (2026-10-02): «Попробуй сделать так что бы все надпись немного
подсвечивались легким свечением когда мы наводим на них мышкой. Сейчас у нас
панели разделов выделяются подсветкой но все остальные эллементы нет». Of the
prototype's ways they chose the glow in the text's OWN colour, on everything
clickable (maya_hubqt.glowing: the controls that tick on hover).

This module turns a control's rendered pixels into its glow, numpy and stdlib
only (a subprocess test pins it), so the Qt layer (maya_hubqt.HoverGlow) only
draws what comes out:

    ink(bgra, inner)     the control's INK - every pixel brighter than its own
                         face (the commonest luminance inside its rect): its
                         letters, its icon, a checked box; not the border, not
                         the hover fill
    bloom(bgra, scale)   the ink blurred, in the ink's own colour, off the ink
                         itself: added on top it is the glow
    rim(bgra, scale)     the orange primary button has dark letters on a lit
                         face, no ink: it lights the way a card does, a warm rim
                         inside its edge
    pad(scale)           how far a bloom reaches past the control, physical px

Every array is premultiplied BGRA uint8 (QImage's ARGB32_Premultiplied on a
little-endian machine). The numbers are maya_hubstyle.HOVER_GLOW.

Spec: docs/superpowers/specs/2026-10-02-hub-hover-glow-design.md
"""

import numpy as np

import maya_hubstyle as hubstyle

#  three box passes approximate a Gaussian
PASSES = 3


def _bgr(hex_colour):
    return np.array([int(hex_colour[i:i + 2], 16) for i in (5, 3, 1)],
                    np.float64)


def pad(scale=1.0):
    """The bloom's reach past the control, physical px."""
    return hubstyle.px(hubstyle.HOVER_GLOW["radius"], scale)


def _box(a, r, axis):
    """A box blur of half-width `r` along `axis` (0 or 1), zero outside."""
    widths = [(0, 0)] * a.ndim
    widths[axis] = (r + 1, r)
    total = np.cumsum(np.pad(a, widths, mode="constant"), axis=axis)
    n = a.shape[axis]
    if axis == 0:
        diff = total[2 * r + 1:2 * r + 1 + n] - total[:n]
    else:
        diff = total[:, 2 * r + 1:2 * r + 1 + n] - total[:, :n]
    return diff * (1.0 / (2 * r + 1))


def blur(a, radius):
    """`a` blurred about `radius` px over its first two axes (a 2-D field,
    or one with channels behind): PASSES box passes each way, float32."""
    r = max(1, int(round(float(radius) / np.sqrt(PASSES))))
    out = np.asarray(a, np.float32)
    for _ in range(PASSES):
        out = _box(_box(out, r, 0), r, 1)
    return out


#  The bloom is soft: on a large display it is blurred at half resolution
#  and stretched back (see bloom)
STEP = 2


def _down(a, step):
    """`a` averaged over `step` x `step` blocks (zero-padded to fit)."""
    h, w = a.shape[:2]
    hh, ww = -(-h // step), -(-w // step)
    widths = [(0, hh * step - h), (0, ww * step - w)] + [(0, 0)] * (a.ndim - 2)
    a = np.pad(a, widths, mode="constant")
    shape = (hh, step, ww, step) + a.shape[2:]
    return a.reshape(shape).mean(axis=(1, 3))


def _up(a, step, h, w):
    """`a` stretched back by `step` (bilinear, edge-clamped) to h x w."""
    hh, ww = a.shape[:2]
    ys = np.clip((np.arange(h) + 0.5) / step - 0.5, 0, hh - 1)
    xs = np.clip((np.arange(w) + 0.5) / step - 0.5, 0, ww - 1)
    y0, x0 = np.floor(ys).astype(int), np.floor(xs).astype(int)
    y1, x1 = np.minimum(y0 + 1, hh - 1), np.minimum(x0 + 1, ww - 1)
    fy = (ys - y0).astype(np.float32)
    fx = (xs - x0).astype(np.float32)
    extra = (None,) * (a.ndim - 2)
    fy = fy[(slice(None), None) + extra]
    fx = fx[(None, slice(None)) + extra]
    #  separable: along x on the small rows, then along y
    across = a[:, x0] * (1 - fx) + a[:, x1] * fx
    return across[y0] * (1 - fy) + across[y1] * fy


_LUMA = np.array([0.114, 0.587, 0.299], np.float32)


def _luminance(bgr):
    return bgr @ _LUMA


def ink(bgra, inner=None):
    """(mask 0..1, colour) of a control's pixels: `mask` is how much each is
    INK - brighter than the face by more than HOVER_GLOW["lo"], fully by
    `lo + span` - and `colour` each pixel's BGR (0..255 floats) as it shows
    over the card. The face is the commonest luminance inside `inner` (top,
    left, bottom, right), the control's own rect when the source is padded."""
    params = hubstyle.HOVER_GLOW
    alpha = bgra[..., 3:4].astype(np.float32) * np.float32(1.0 / 255.0)
    under = _bgr(hubstyle.TOKENS["card"]).astype(np.float32)
    colour = bgra[..., :3].astype(np.float32) + under * (1.0 - alpha)
    lum = _luminance(colour)
    region = lum
    if inner is not None:
        top, left, bottom, right = inner
        region = lum[top:bottom, left:right]
    counts = np.bincount(np.clip(region + 0.5, 0, 255).astype(np.uint8)
                         .ravel(), minlength=256)
    face = float(counts.argmax())
    mask = np.clip((lum - (face + params["lo"])) * (1.0 / params["span"]),
                   0.0, 1.0)
    return mask, colour


def _premultiplied(colour_bgr, alpha):
    """uint8 BGRA from a BGR colour (per pixel or one) and alpha 0..1."""
    h, w = alpha.shape
    out = np.empty((h, w, 4), np.float32)
    out[..., :3] = colour_bgr * alpha[..., None]
    out[..., 3] = 255.0 * alpha
    return np.clip(out + 0.5, 0, 255).astype(np.uint8)


def bloom(bgra, scale=1.0, inner=None):
    """The glow of a control's ink at full strength, or None (no ink).

    Only the box round the ink is worked (the bloom cannot reach further),
    the blur at half resolution when it is big enough (measured 2026-10-02
    on a 530 x 40 control at 150 %: 15 ms at full resolution over the whole
    picture, a stutter when it lands in a frame)."""
    params = hubstyle.HOVER_GLOW
    mask, colour = ink(bgra, inner)
    rows = np.flatnonzero(mask.any(axis=1))
    if not rows.size:
        return None
    cols = np.flatnonzero(mask.any(axis=0))
    radius = params["radius"] * float(scale or 1.0)
    reach = int(np.ceil(3.0 * radius)) + 2
    h, w = mask.shape
    y0, y1 = max(0, rows[0] - reach), min(h, rows[-1] + reach + 1)
    x0, x1 = max(0, cols[0] - reach), min(w, cols[-1] + reach + 1)
    m = mask[y0:y1, x0:x1]
    hh, ww = m.shape
    #  the ink and its colour weighted by it, blurred together (one pass
    #  over four channels)
    stack = np.empty((hh, ww, 4), np.float32)
    stack[..., 0] = m
    stack[..., 1:] = colour[y0:y1, x0:x1] * m[..., None]
    #  half resolution only where the blur stays as wide (a small radius
    #  would round down to a narrower box)
    step = STEP if (min(hh, ww) >= 4 * STEP and radius >= 3 * STEP) else 1
    if step > 1:
        soft = _up(blur(_down(stack, step), radius / step), step, hh, ww)
    else:
        soft = blur(stack, radius)
    spread = soft[..., 0]
    alpha = np.clip(spread * params["gain"], 0.0, 1.0) * (1.0 - m)
    alpha *= params["strength"]
    tint = soft[..., 1:] / (spread[..., None] + 1e-6)
    out = np.zeros((h, w, 4), np.uint8)
    out[y0:y1, x0:x1] = _premultiplied(np.clip(tint, 0.0, 255.0), alpha)
    return out


def rim(bgra, scale=1.0):
    """A warm rim inside a filled control's edge at full strength, or None
    (nothing painted)."""
    params = hubstyle.HOVER_GLOW
    shape = bgra[..., 3].astype(np.float32) * np.float32(1.0 / 255.0)
    if float(shape.max()) <= 0.0:
        return None
    inside = blur(shape, params["rim_depth"] * float(scale or 1.0))
    edge = np.clip((1.0 - inside) * 2.0, 0.0, 1.0) * shape
    alpha = edge ** 1.5 * params["rim_strength"]
    return _premultiplied(_bgr(params["rim"]), alpha)
