"""maya_panezoom_rules - the timing of the Space tap's fly-in and fly-out (2026-10-22), pure.

The animator: «когда я нажимаю пробел 1 раз у меня открывается 4 окна ... нажимаю пробел еще раз
окно в котором мышка разворачивается на весь экран ... переход резкий ... эффект влета в окно и
вылета из него». Of two ways they chose A: a picture over the viewport.

- IN (four views -> one): the 3D view under the cursor, as it stood in its quarter, grows to the
  whole view while the other three darken behind it, then the overlay fades onto the live view.
- OUT (one view -> four): the whole view shrinks into its quarter while the other three brighten
  in around it, then the overlay fades onto the live layout.
- An accent ring rides the moving view and fades as it lands (added light).
- Only the single view's own 3D area is covered (the animator, after the first try: «нужно
  обрезать только окно вьюпорта»): the panel's menu and icon bars stay live; the moving
  picture turns from the old view into the new one as it flies (`mix`).

Rects are (x, y, w, h) in the pane's logical px. Stdlib only.
"""

IN, OUT = "in", "out"

MOVE_MS = {IN: 340.0, OUT: 300.0}   # the panel's flight
FADE_MS = 90.0                      # the overlay onto the live view after it lands
DIM = 0.62                          # how dark the three other views get (0 none, 1 black)
RING = 2.0                          # logical px of the accent ring on the moving panel
RING_ALPHA = 0.85
GLOW = 14.0                         # logical px the ring's light reaches outward


def ease_out_quint(u):
    u = min(1.0, max(0.0, u))
    return 1.0 - (1.0 - u) ** 5


def total_ms(kind):
    return MOVE_MS[kind] + FADE_MS


def lerp_rect(a, b, e):
    return tuple(a[i] + (b[i] - a[i]) * e for i in range(4))


def frame(kind, age_ms, src, dst):
    """What the overlay shows at `age_ms`: {rect, dim, ring, alpha, done}.

    rect - where the moving panel's picture stands; dim - how dark the background picture is;
    ring - the accent ring's strength; alpha - the whole overlay (it fades after landing)."""
    move = MOVE_MS[kind]
    u = age_ms / move if move > 0 else 1.0
    e = ease_out_quint(u)
    rect = lerp_rect(src, dst, e)
    dim = DIM * e if kind == IN else DIM * (1.0 - e)
    ring = RING_ALPHA * (1.0 - e) ** 1.5
    past = max(0.0, age_ms - move)
    alpha = 1.0 - min(1.0, past / FADE_MS) if FADE_MS > 0 else (0.0 if past else 1.0)
    return {"rect": rect, "dim": dim, "ring": ring, "alpha": alpha,
            "done": age_ms >= total_ms(kind)}


def kind_of(config):
    """The pane's layout before the tap decides the direction: single -> OUT, else IN."""
    return OUT if config == "single" else IN


def usable(rect, minimum=8.0):
    return rect is not None and rect[2] >= minimum and rect[3] >= minimum


def margins(outer, inner):
    """How far `inner` (a panel's 3D view) stands inside `outer` (the panel): (l, t, r, b)."""
    return (inner[0] - outer[0], inner[1] - outer[1],
            (outer[0] + outer[2]) - (inner[0] + inner[2]),
            (outer[1] + outer[3]) - (inner[1] + inner[3]))


def inset(rect, m):
    """`rect` less the margins `m` - where a panel spread over `rect` draws its 3D view."""
    return (rect[0] + m[0], rect[1] + m[1], rect[2] - m[0] - m[2], rect[3] - m[1] - m[3])


def mix(age_ms, kind):
    """How far the moving picture has turned from the old view into the new one (0..1)."""
    u = min(1.0, max(0.0, age_ms / MOVE_MS[kind]))
    return u * u * (3.0 - 2.0 * u)


def mip_for(widths, want):
    """The index of the smallest of `widths` (largest first) still at least `want` px wide."""
    best = 0
    for i, w in enumerate(widths):
        if w >= want:
            best = i
    return best
