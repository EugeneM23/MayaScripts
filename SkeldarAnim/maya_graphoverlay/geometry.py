"""Pure rules: where the Graph Editor's window opens and what is remembered,
which of its chrome is which, when the mouse goes through, when a frame is
due. Stdlib only.

Rectangles are (x, y, width, height) in global pixels - physical ones in
Maya 2027, where Qt's devicePixelRatio is 1.0 (the hub skin measured it).
"""


def usable(rect):
    """A rectangle with an area to lie on."""
    return (rect is not None and len(rect) == 4
            and rect[2] > 0 and rect[3] > 0)


MARGIN = 12          # px between the window and the viewport's corner
MIN_WIDTH = 480     # the least a graph is worth opening at
MIN_HEIGHT = 300


def default_rect(view):
    """Where the Graph Editor's window first goes: the lower right part of
    the viewport, a share of its size, never smaller than a usable graph.

    The animator (2026-10-02): «граф эдитор часто все перекрывает». The
    figure stands in the middle of the viewport, so the window keeps off
    its middle; the window is moved and resized as any window, and its
    place is remembered.
    """
    x, y, width, height = view
    w = min(width, max(MIN_WIDTH, int(width * 0.6)))
    h = min(height, max(MIN_HEIGHT, int(height * 0.5)))
    left = max(x, x + width - w - MARGIN)
    top = max(y, y + height - h - MARGIN)
    return (left, top, w, h)


def on_some_screen(rect, screens):
    """Whether `rect` shows on one of `screens` (each (x, y, w, h)) with a
    strip at least 80 px square - a window remembered on a monitor that is
    no longer there is put back where the animator can reach it."""
    if not usable(rect):
        return False
    x, y, w, h = rect
    for sx, sy, sw, sh in screens:
        overlap_w = min(x + w, sx + sw) - max(x, sx)
        overlap_h = min(y + h, sy + sh) - max(y, sy)
        if overlap_w >= 80 and overlap_h >= 80:
            return True
    return False


def chrome_bands(host_size, canvas):
    """The window's rectangles outside its curve area, in window
    coordinates: top, bottom, left, right, the empty ones left out.

    `canvas` is (x, y, width, height) inside the window, its frame and title
    bar included. What lies there - title bar, borders, menu bar, toolbar,
    channel list - is the Graph Editor's own, which the glass shows opaque,
    as Maya draws it.
    """
    width, height = host_size
    x, y, w, h = canvas
    bands = [(0, 0, width, y),
             (0, y + h, width, height - (y + h)),
             (0, y, x, h),
             (x + w, y, width - (x + w), h)]
    return [band for band in bands if band[2] > 0 and band[3] > 0]


def due_in(now, last, min_interval):
    """Seconds until the next frame may be keyed; 0 when it may be now."""
    if last is None:
        return 0.0
    return max(0.0, min_interval - (now - last))
