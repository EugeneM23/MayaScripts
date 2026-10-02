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
    """A box blur of half-width `r` along `axis`, zero outside."""
    widths = [(0, 0)] * a.ndim
    widths[axis] = (r + 1, r)
    total = np.cumsum(np.pad(a, widths, mode="constant"), axis=axis)
    n = a.shape[axis]
    hi = np.take(total, np.arange(2 * r + 1, 2 * r + 1 + n), axis=axis)
    lo = np.take(total, np.arange(0, n), axis=axis)
    return (hi - lo) / float(2 * r + 1)


def blur(a, radius):
    """`a` (2-D) blurred about `radius` px: PASSES box passes each way."""
    r = max(1, int(round(float(radius) / np.sqrt(PASSES))))
    out = np.asarray(a, np.float64)
    for _ in range(PASSES):
        out = _box(_box(out, r, 0), r, 1)
    return out


def _luminance(bgr):
    return 0.114 * bgr[..., 0] + 0.587 * bgr[..., 1] + 0.299 * bgr[..., 2]


def ink(bgra, inner=None):
    """(mask 0..1, colour) of a control's pixels: `mask` is how much each is
    INK - brighter than the face by more than HOVER_GLOW["lo"], fully by
    `lo + span` - and `colour` each pixel's BGR (0..255 floats) as it shows
    over the card. The face is the commonest luminance inside `inner` (top,
    left, bottom, right), the control's own rect when the source is padded."""
    params = hubstyle.HOVER_GLOW
    alpha = bgra[..., 3:4].astype(np.float64) / 255.0
    under = _bgr(hubstyle.TOKENS["card"])
    colour = bgra[..., :3].astype(np.float64) + under * (1.0 - alpha)
    lum = _luminance(colour)
    region = lum
    if inner is not None:
        top, left, bottom, right = inner
        region = lum[top:bottom, left:right]
    counts = np.bincount(np.clip(np.round(region), 0, 255).astype(np.int64)
                         .ravel(), minlength=256)
    face = float(counts.argmax())
    mask = np.clip((lum - face - params["lo"]) / params["span"], 0.0, 1.0)
    return mask, colour


def _premultiplied(colour_bgr, alpha):
    """uint8 BGRA from a BGR colour (per pixel or one) and alpha 0..1."""
    h, w = alpha.shape
    out = np.empty((h, w, 4), np.float64)
    out[..., :3] = colour_bgr * alpha[..., None]
    out[..., 3] = 255.0 * alpha
    return np.ascontiguousarray(np.clip(np.round(out), 0, 255)
                                .astype(np.uint8))


def bloom(bgra, scale=1.0, inner=None):
    """The glow of a control's ink at full strength, or None (no ink)."""
    params = hubstyle.HOVER_GLOW
    mask, colour = ink(bgra, inner)
    if float(mask.max()) <= 0.0:
        return None
    radius = params["radius"] * float(scale or 1.0)
    spread = blur(mask, radius)
    alpha = np.clip(spread * params["gain"], 0.0, 1.0) * (1.0 - mask)
    alpha *= params["strength"]
    weight = spread + 1e-9
    tint = np.empty(colour.shape, np.float64)
    for c in range(3):
        tint[..., c] = blur(colour[..., c] * mask, radius) / weight
    return _premultiplied(np.clip(tint, 0.0, 255.0), alpha)


def rim(bgra, scale=1.0):
    """A warm rim inside a filled control's edge at full strength, or None
    (nothing painted)."""
    params = hubstyle.HOVER_GLOW
    shape = bgra[..., 3].astype(np.float64) / 255.0
    if float(shape.max()) <= 0.0:
        return None
    inside = blur(shape, params["rim_depth"] * float(scale or 1.0))
    edge = np.clip((1.0 - inside) * 2.0, 0.0, 1.0) * shape
    alpha = edge ** 1.5 * params["rim_strength"]
    return _premultiplied(_bgr(params["rim"]), alpha)
