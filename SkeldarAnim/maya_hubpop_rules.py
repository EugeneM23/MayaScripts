"""maya_hubpop_rules - where a section's popup stands in its viewport, and how big it is. Pure.

2026-10-09 (spec: docs/superpowers/specs/2026-10-09-hub-section-popups-design.md).
Every decision the popup makes about its place and its size is here, so the tests
run with neither Maya nor Qt: the size it takes (automatic, or as the animator drags
its edges), the bounds a drag may take, the origin it is clamped to inside its
viewport's rectangle (so a drag cannot carry it onto another monitor), the offset
that is remembered (logical px from the viewport's top-left, so it moves with the
viewport and survives a different scale), the cascade of the default places, and
the optionVars' text.

Rectangles are (x, y, width, height) in global physical pixels (what the GL
surface reports); offsets, sizes and the margins are logical, multiplied by the
display scale (`scale`, Maya's realScaleValue) where they meet the rectangle.
"""

WIDTH = 360            # logical px: the widest a popup takes unless its section needs more
MARGIN = 12            # logical px kept from the viewport's edges
CASCADE = 24           # logical px each default place steps from the last
MIN_HEIGHT = 40        # logical px: an unrolled popup is never shorter (2026-10-09)
MAX_HEIGHT = 320       # logical px: an unrolled popup is never taller - a taller section scrolls (2026-10-09)
MIN_RESIZE_W = 160     # logical px: the narrowest an unrolled popup is dragged to (2026-10-09)
GRIP_W = 5             # logical px: the strip along each edge a resize drag takes (2026-10-09)

POPUPS_VAR = "skeldarHubPopups"          # the keys open, in opening order
POS_VAR = "skeldarHubPopupPos_{0}"       # one popup's offset: "x,y"
COLLAPSED_VAR = "skeldarHubPopupCollapsed_{0}"   # 1: rolled up to its name (2026-10-09)
SIZE_VAR = "skeldarHubPopupSize_{0}"     # an unrolled popup's size "w,h", logical; "-" = automatic
BAR_VAR = "skeldarHubPopupBar_{0}"       # a rolled-up popup's width, logical; "-" = fits its name


def clamp_origin(x, y, w, h, rect):
    """The top-left (x, y) of a w x h window, kept inside `rect`. A window
    wider or taller than the rectangle sits at its left or top edge. Pure."""
    rx, ry, rw, rh = rect
    if w >= rw:
        nx = rx
    else:
        nx = min(max(x, rx), rx + rw - w)
    if h >= rh:
        ny = ry
    else:
        ny = min(max(y, ry), ry + rh - h)
    return int(round(nx)), int(round(ny))


def offset_of(x, y, rect, scale):
    """A top-left (x, y) as the logical offset from `rect`'s top-left. Pure."""
    rx, ry = rect[0], rect[1]
    scale = float(scale) or 1.0
    return ((x - rx) / scale, (y - ry) / scale)


def origin_of(offset, rect, w, h, scale):
    """The clamped top-left (physical) of a window at logical `offset` from
    `rect`'s top-left. Pure."""
    scale = float(scale) or 1.0
    x = rect[0] + offset[0] * scale
    y = rect[1] + offset[1] * scale
    return clamp_origin(x, y, w, h, rect)


def default_offset(index, rect, w, h, scale):
    """The offset of the `index`-th popup opened without a remembered place:
    the top-right corner of the viewport, each one cascading down and left
    from the last, clamped so it always stands inside. Pure."""
    scale = float(scale) or 1.0
    step = CASCADE * scale * int(index)
    x = rect[0] + rect[2] - w - MARGIN * scale - step
    y = rect[1] + MARGIN * scale + step
    origin = clamp_origin(x, y, w, h, rect)
    return offset_of(origin[0], origin[1], rect, scale)


def _avail(rect, scale):
    """The viewport's rectangle less its margins, physical (w, h). Pure."""
    scale = float(scale) or 1.0
    margin2 = 2 * MARGIN * scale
    return max(int(rect[2] - margin2), 1), max(int(rect[3] - margin2), 1)


def bounds(min_w, rect, scale, chrome_h, collapsed=False, scrollbar_w=0,
           title_w=0, origin=None):
    """What a resize drag may take, physical px: (low_w, high_w, low_h, high_h).

    Rolled up, the width runs from the name's own width (`title_w`, the title row
    with its margins) to the viewport, and the height is the title row alone.
    Unrolled, the width is at least MIN_RESIZE_W, the section's own minimum
    (`min_w`) and room for a scroll bar; the height is at least MIN_HEIGHT. The
    viewport less its margins caps both. `origin` (the window's top-left, physical)
    caps the far edges at the viewport's margin too: a window cannot be dragged out
    of its viewport. Pure."""
    scale = float(scale) or 1.0
    avail_w, avail_h = _avail(rect, scale)
    high_w, high_h = avail_w, avail_h
    if origin is not None:
        room_w = rect[0] + rect[2] - MARGIN * scale - origin[0]
        room_h = rect[1] + rect[3] - MARGIN * scale - origin[1]
        high_w = max(1, min(high_w, int(room_w)))
        high_h = max(1, min(high_h, int(room_h)))
    if collapsed:
        height = min(int(round(chrome_h)), avail_h)
        low_w = min(int(round(title_w)), high_w)
        return max(low_w, 1), high_w, height, height
    low_w = max(int(round(MIN_RESIZE_W * scale)),
                int(round(min_w + scrollbar_w)), int(round(title_w)))
    low_w = min(low_w, high_w)
    low_h = min(int(round(MIN_HEIGHT * scale)), high_h)
    return low_w, high_w, low_h, high_h


def popup_size(min_w, content_h, rect, scale, chrome_h, collapsed=False,
               scrollbar_w=0, title_w=0, user_w=None, user_h=None):
    """The popup's (w, h) in physical px.

    Automatic (no size dragged): the width is the hub's dock width (WIDTH logical:
    the sections are laid out for it, and a popup is their card), wider only when
    the section's own minimum (`min_w`) needs more; the height is the title row
    (`chrome_h`) plus the section's natural height (`content_h`), never less than
    MIN_HEIGHT and at most MAX_HEIGHT - a taller section scrolls, and its scroll
    bar (`scrollbar_w`) takes width (2026-10-09, «короче»).

    Rolled up, the popup is its title row (`chrome_h`) high and as wide as its name
    needs (`title_w`, 2026-10-09, «максимально коротким»); a width the animator
    dragged (`user_w`) is taken, as far as `bounds` allows.

    A size the animator dragged (`user_w`, `user_h`, logical) is taken unchanged
    where `bounds` allows, and a dragged height may be taller than MAX_HEIGHT (the
    animator chose it). Everything is kept inside the viewport less its margins.
    Pure."""
    scale = float(scale) or 1.0
    avail_w, avail_h = _avail(rect, scale)
    low_w, high_w, low_h, high_h = bounds(min_w, rect, scale, chrome_h,
                                          collapsed, scrollbar_w, title_w)
    if collapsed:
        if user_w is None:
            w = int(round(title_w)) if title_w > 0 else int(round(WIDTH * scale))
        else:
            w = int(round(float(user_w) * scale))
        return min(max(w, low_w), high_w), low_h
    cap = min(int(round(MAX_HEIGHT * scale)), avail_h)
    natural = int(round(chrome_h + content_h))
    if user_h is None:
        h = min(max(int(round(MIN_HEIGHT * scale)), natural), cap)
    else:
        h = min(max(int(round(float(user_h) * scale)), low_h), high_h)
    if user_w is None:
        w = min(max(int(round(WIDTH * scale)), int(min_w)), avail_w)
        if natural > h:
            w = min(w + int(scrollbar_w), avail_w)
    else:
        w = int(round(float(user_w) * scale))
    return min(max(w, low_w), high_w), h


def encode_flag(on):
    """A yes/no optionVar's text: "1" or "0". Pure."""
    return "1" if on else "0"


def decode_flag(text):
    """The yes/no a text holds, or None when it holds neither. Pure."""
    text = (text or "").strip()
    if text in ("0", "1"):
        return text == "1"
    return None


def encode_keys(keys):
    """The open keys as the optionVar's text, in order, each once. Pure."""
    seen = []
    for key in keys:
        if key and key not in seen:
            seen.append(key)
    return ",".join(seen)


def decode_keys(text, known):
    """The keys the text names that `known` holds, in order, each once.
    Unknown keys (a section since renamed or removed) are dropped. Pure."""
    seen = []
    for key in (text or "").split(","):
        key = key.strip()
        if key in known and key not in seen:
            seen.append(key)
    return seen


def encode_offset(offset):
    """A popup's logical offset as the optionVar's text: "x,y", 2 decimals."""
    return "{0:.2f},{1:.2f}".format(float(offset[0]), float(offset[1]))


def decode_offset(text):
    """The offset a text holds, or None when it is not two numbers. Pure."""
    parts = (text or "").split(",")
    if len(parts) != 2:
        return None
    try:
        return (float(parts[0]), float(parts[1]))
    except ValueError:
        return None


def encode_single(value):
    """A logical size as the optionVar's text: "w", one decimal; "-" when it
    is automatic (None). Pure."""
    return "-" if value is None else "{0:.1f}".format(float(value))


def decode_single(text):
    """The logical size a text holds, or None (automatic) when it holds none
    or a size that is not positive. Pure."""
    text = (text or "").strip()
    if text in ("", "-"):
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    return value if value > 0 else None


def encode_pair(w, h):
    """An unrolled popup's size as the optionVar's text: "w,h", logical, "-" for
    an automatic side. Pure."""
    return encode_single(w) + "," + encode_single(h)


def decode_pair(text):
    """The (w, h) a text holds, None for each side that is automatic or not a
    number. Pure."""
    parts = (text or "").split(",")
    if len(parts) != 2:
        return (None, None)
    return (decode_single(parts[0]), decode_single(parts[1]))
