"""Pure rules: where the ghost goes, when it lets the mouse through, when a
frame is due. Stdlib only.

Rectangles are (x, y, width, height) in global pixels - physical ones in
Maya 2027, where Qt's devicePixelRatio is 1.0 (the hub skin measured it).
"""


def usable(rect):
    """A rectangle with an area to lie on."""
    return (rect is not None and len(rect) == 4
            and rect[2] > 0 and rect[3] > 0)


def host_rect(target, host, canvas):
    """Where the host goes so that its canvas lands exactly on `target`.

    The canvas sits in the host at an offset with a border round it -
    measured (5, 3) and 8x6 once the chrome is hidden - read off the host
    as it stands rather than assumed, so a Maya that frames its panels
    another way is still right.
    """
    dx, dy = canvas[0] - host[0], canvas[1] - host[1]
    return (target[0] - dx, target[1] - dy,
            target[2] + (host[2] - canvas[2]),
            target[3] + (host[3] - canvas[3]))


def chrome_bands(host_size, canvas):
    """The host's rectangles outside its curve area, in host coordinates:
    top, bottom, left, right, the empty ones left out.

    `canvas` is (x, y, width, height) inside the host. What lies there is
    the Graph Editor's own chrome - menu bar, toolbar, channel list,
    borders - which the glass shows opaque, as Maya draws it.
    """
    width, height = host_size
    x, y, w, h = canvas
    bands = [(0, 0, width, y),
             (0, y + h, width, height - (y + h)),
             (0, y, x, h),
             (x + w, y, width - (x + w), h)]
    return [band for band in bands if band[2] > 0 and band[3] > 0]


def let_through(alt_down, maya_active, placed):
    """Whether the ghost lets the mouse through to the viewport.

    alt held is the camera (the animator, 2026-09-30: «1, камеры»); with
    Maya not in front, or no viewport to lie on, the graph has no click to
    take.
    """
    return bool(alt_down) or not maya_active or not placed


def due_in(now, last, min_interval):
    """Seconds until the next frame may be keyed; 0 when it may be now."""
    if last is None:
        return 0.0
    return max(0.0, min_interval - (now - last))
