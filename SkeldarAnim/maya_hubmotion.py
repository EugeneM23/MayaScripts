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
                    140 + 0.12 per px, kept within 160..260; an opening
                    1.5 times that (OPEN_FACTOR)
    SCROLL_MS       the glide; it starts once the other cards have finished
                    sliding (maya_hubqt.Skin._glide_when_settled)
    enabled()       the menu's Interface animations, an optionVar, on by
                    default
    LIGHT_IN_MS ... the card light: fading in, out, flashing (smooth,
                    light_ms, flash_at)

Spec: docs/superpowers/specs/2026-10-01-hub-card-motion-design.md
"""

OPTIONVAR = "skeldarAnimHub_animations"

BASE_MS = 140
PER_PX_MS = 0.12
MIN_MS = 160
MAX_MS = 260
SCROLL_MS = 240

#  An opening takes this many times a shutting (the same evening, the
#  animator: «замедлим анимацию открытия вкладки примерно на 50%»): 240..390
#  ms against 160..260
OPEN_FACTOR = 1.5

#  the chevron's turn when open: "chevron-right" turned a quarter clockwise
#  is "chevron-down"
CHEVRON_OPEN = 90.0

#  The card light (2026-10-01, «красивый глоу и анимацию подсветки»): lighting
#  up answers the mouse quickly (ease-out), going dark leaves a soft trail
#  (ease-in-out); a card just chosen flashes - a fast rise over the first
#  FLASH_RISE of FLASH_MS, then a long fall.
LIGHT_IN_MS = 140
LIGHT_OUT_MS = 260
FLASH_MS = 480
FLASH_RISE = 0.18
#  a fade turned back near its end still takes a moment
LIGHT_MIN_MS = 40

#  A control's glow under the mouse (2026-10-02): the card light's rhythm a
#  little quicker, a control being smaller than a card
GLOW_IN_MS = 110
GLOW_OUT_MS = 220


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


def duration(distance, scale=1.0, opening=False):
    """Milliseconds for a slide of `distance` PHYSICAL px at the display's
    `scale` (a longer card takes a little longer, never a lot); an
    `opening` OPEN_FACTOR times longer."""
    logical = abs(float(distance)) / float(scale or 1.0)
    ms = min(MAX_MS, max(MIN_MS, BASE_MS + PER_PX_MS * logical))
    if opening:
        ms *= OPEN_FACTOR
    return int(round(ms))


def lerp(start, end, k):
    """`k` of the way from `start` to `end`."""
    return start + (end - start) * k


def smooth(t):
    """Ease-in-out (smoothstep) of `t` (clamped to 0..1): the light going
    dark."""
    t = min(1.0, max(0.0, float(t)))
    return t * t * (3.0 - 2.0 * t)


def light_ms(on, start, target):
    """Milliseconds for the light to go from `start` to `target` (0..1):
    LIGHT_IN_MS / LIGHT_OUT_MS for the whole way, its share for part of it
    (a fade turned back mid-way), never under LIGHT_MIN_MS."""
    whole = LIGHT_IN_MS if on else LIGHT_OUT_MS
    return max(LIGHT_MIN_MS, int(round(whole * abs(target - start))))


def glow_ms(on, start, target):
    """Milliseconds for a control's glow from `start` to `target` (0..1):
    GLOW_IN_MS / GLOW_OUT_MS for the whole way, its share for part of it,
    never under LIGHT_MIN_MS."""
    whole = GLOW_IN_MS if on else GLOW_OUT_MS
    return max(LIGHT_MIN_MS, int(round(whole * abs(target - start))))


def flash_at(t):
    """The flash at `t` (0..1) of FLASH_MS: up to 1 over FLASH_RISE (eased
    out), then back to 0 (eased out) - 0 at both ends."""
    t = min(1.0, max(0.0, float(t)))
    if t < FLASH_RISE:
        return ease(t / FLASH_RISE)
    return 1.0 - ease((t - FLASH_RISE) / (1.0 - FLASH_RISE))
