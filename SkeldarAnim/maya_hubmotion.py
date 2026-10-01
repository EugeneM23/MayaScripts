"""maya_hubmotion.py - how the SkeldarAnim hub's cards move (2026-10-01).

The animator: «А элементы нашего интерфейса возможно открывать закрывать с
какими-то анимациями, просто для красоты и приятности?» - and of the three
scopes offered, the cards and the scroll. A card's body slides open and shut,
its chevron turning with it, and a jump from the icon strip glides the scroll
to its card (maya_hubqt does the sliding). This module is the arithmetic and
the switch, stdlib only (a subprocess test pins it), so the Qt layer and the
tests share one set of numbers.

    ease(t)         cubic ease-out on the animation's linear 0..1: fast
                    start, soft landing
    duration(d)     a slide's milliseconds from its distance in LOGICAL px:
                    140 + 0.12 per px, kept within 160..260
    SCROLL_MS       the glide; it starts once the other cards have finished
                    sliding (maya_hubqt.Skin._glide_when_settled)
    enabled()       the menu's Interface animations, an optionVar, on by
                    default

Spec: docs/superpowers/specs/2026-10-01-hub-card-motion-design.md
"""

OPTIONVAR = "skeldarAnimHub_animations"

BASE_MS = 140
PER_PX_MS = 0.12
MIN_MS = 160
MAX_MS = 260
SCROLL_MS = 240

#  the chevron's turn when open: "chevron-right" turned a quarter clockwise
#  is "chevron-down"
CHEVRON_OPEN = 90.0


def _cmds():
    import maya.cmds as cmds
    return cmds


def enabled():
    """The cards and the scroll move (the default), or everything is
    instant."""
    try:
        cmds = _cmds()
        if not cmds.optionVar(exists=OPTIONVAR):
            return True
        return bool(cmds.optionVar(query=OPTIONVAR))
    except Exception:                                        # noqa: BLE001
        return True


def set_enabled(on):
    """Switch the animations, remembered across sessions."""
    on = bool(on)
    try:
        _cmds().optionVar(intValue=(OPTIONVAR, int(on)))
    except Exception:                                        # noqa: BLE001
        pass
    return on


def ease(t):
    """Cubic ease-out of `t` (clamped to 0..1)."""
    t = min(1.0, max(0.0, float(t)))
    return 1.0 - (1.0 - t) ** 3


def duration(distance, scale=1.0):
    """Milliseconds for a slide of `distance` PHYSICAL px at the display's
    `scale` (a longer card takes a little longer, never a lot)."""
    logical = abs(float(distance)) / float(scale or 1.0)
    return int(round(min(MAX_MS, max(MIN_MS, BASE_MS + PER_PX_MS * logical))))


def lerp(start, end, k):
    """`k` of the way from `start` to `end`."""
    return start + (end - start) * k
