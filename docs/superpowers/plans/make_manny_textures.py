"""UE5 Manny's texture maps, Unreal's material maths baked in, into SkeldarAnim/assets/Manny/.

    mayapy make_manny_textures.py

2026-09-30 (spec: docs/superpowers/specs/2026-09-30-manny-textured-design.md).  Reads what
`export_manny_from_unreal.py` wrote to sources/manny/ -- the 4096^2 textures and
`manny_materials.json` -- and writes, at the Orc D's 2048 JPG:

- `Manny_HeadLegs_Color.jpg`, `Manny_Torso_Color.jpg`  the base colour `M_Mannequin` (the Orc
      Marauder pack's demo copy) computes, read off its graph:
          lerp(lerp(D, desat(fallOff(D), Metal_Desaturation) * Metal_Brightness * Tint, metalPaintMask),
               desat(that * Tint, Plastic_Desaturation) * Plastic_Brightness, plasticMask)
          fallOff(D) = lerp(D * EnergeConservation, D, saturate(|N.V| ^ BaseColorFallOff))
      With the two instances' values (Tint 1, desaturations 0, brightnesses 1, EnergeConservation 1,
      BaseColorFallOff 0) every lerp collapses and the colour is `D` itself -- checked here, refused
      otherwise.  The TORSO also gets the chest logo (the animator's pick, «Запечь лого в цвет»): the
      emissive `MF_logo3layers`' layer 0 -- the logo mask at ScaleUVsByCenter(uv + LogoPosOffset,
      LogoSize), times its sphere mask, times LogoLayer0_Color * LogoLayer0_Brightness -- saturated
      into the colour: lerp(D, colour, saturate(brightness * logo * sphere)).  No glow layers, no
      parallax, no blur (an emissive is not a colour; saturated, it is the colour).
- `Manny_HeadLegs_Normal.jpg`, `Manny_Torso_Normal.jpg`  `BN`, the base layer's normal under the
      clear coat (`ClearCoatNormalCustomOutput`) -- the bevels and panel lines; the `Normal` pin's
      `_N` is the coat's and nearly flat.  Averaged as vectors, renormalised, green into Maya's
      (OpenGL) convention (Unreal's are DirectX).

Everything in Unreal's texture space (row 0 = v 0, as the image is stored), colour in LINEAR light,
averaged down in linear, encoded to sRGB last.
"""
import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import numpy as np  # noqa: E402
from PySide6.QtGui import QImage  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

APP = QApplication.instance() or QApplication([])
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
SRC = os.path.join(REPO, "sources", "manny")
TEX = os.path.join(SRC, "textures")
OUT = os.path.join(REPO, "SkeldarAnim", "assets", "Manny")
SIZE = 2048
QUALITY = 95
BASE = "/Game/Orc_Marauder/Demo/Characters/Mannequins/"
HEADLEGS = BASE + "Materials/Instances/Manny/MI_Manny_01"
TORSO = BASE + "Materials/Instances/Manny/MI_Manny_02"
SPHERE_RADIUS, SPHERE_HARDNESS = 0.65, 0.75        # MF_logo3layers' SphereMask_1, its constants

params = json.load(open(os.path.join(SRC, "manny_materials.json")))
M = params["materials"]


def load(name):
    """An image as float64 0..1, (h, w, 4), row 0 the image's top (Unreal's v 0)."""
    img = QImage(os.path.join(TEX, name + ".png"))
    if img.isNull():
        raise RuntimeError("cannot read " + name)
    img = img.convertToFormat(QImage.Format_RGBA8888)
    w, h = img.width(), img.height()
    raw = np.frombuffer(img.constBits(), dtype=np.uint8, count=img.sizeInBytes())
    return raw.reshape(h, img.bytesPerLine())[:, :w * 4].reshape(h, w, 4).astype(np.float64) / 255.0


def to_linear(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def to_srgb(c):
    c = np.clip(c, 0.0, 1.0)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


def shrink(a, size):
    """Box-average down to size x size (the source is a power-of-two multiple)."""
    f = a.shape[0] // size
    if f == 1:
        return a
    return a.reshape(size, f, size, f, a.shape[2]).mean(axis=(1, 3))


def bilinear(img, u, v):
    """Sample (h, w, c) at normalised u, v (arrays), texel centres at (i + 0.5) / n, clamped."""
    h, w = img.shape[:2]
    x = np.clip(u * w - 0.5, 0, w - 1)
    y = np.clip(v * h - 0.5, 0, h - 1)
    x0, y0 = np.floor(x).astype(int), np.floor(y).astype(int)
    x1, y1 = np.minimum(x0 + 1, w - 1), np.minimum(y0 + 1, h - 1)
    fx, fy = (x - x0)[..., None], (y - y0)[..., None]
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x1] * fx * (1 - fy)
            + img[y1, x0] * (1 - fx) * fy + img[y1, x1] * fx * fy)


def save_rgb(rgb01, name):
    data = np.ascontiguousarray(np.round(np.clip(rgb01, 0, 1) * 255).astype(np.uint8))
    h, w = data.shape[:2]
    img = QImage(data.tobytes(), w, h, w * 3, QImage.Format_RGB888).copy()
    path = os.path.join(OUT, name)
    if not img.save(path, "JPG", QUALITY):
        raise RuntimeError("could not write " + path)
    print("  %-26s %dx%d  %.2f MB" % (name, w, h, os.path.getsize(path) / 1e6))


def need(value, wanted, what):
    if abs(value - wanted) > 1e-6:
        raise RuntimeError("%s is %s, the colour collapses to D only at %s -- the bake would lie"
                           % (what, value, wanted))


def collapses(mi, key):
    """The instance's values are the ones that make the base colour D (see the docstring)."""
    s, v = mi["scalars"], mi["vectors"]
    for name, wanted in (("Metal_Desaturation", 0.0), ("Metal_Brightness", 1.0),
                         ("Plastic_Desaturation", 0.0), ("Plastic_Brightness", 1.0),
                         ("EnergeConservation", 1.0), ("BaseColorFallOff", 0.0)):
        need(s[name], wanted, "%s.%s" % (key, name))
    for k in range(3):
        need(v["Tint"][k], 1.0, "%s.Tint" % key)
    if mi["textures"]["Base Texture"] != BASE + "Textures/Manny/" + ("T_Manny_01_D" if key == "HeadLegs" else "T_Manny_02_D"):
        raise RuntimeError("%s wears %s" % (key, mi["textures"]["Base Texture"]))


def colour_map(key, mi, name, out):
    collapses(mi, key)
    lin = shrink(to_linear(load(name)[..., :3]), SIZE)
    if mi["switches"].get("UseLogo"):
        s, v = mi["scalars"], mi["vectors"]
        size, ox, oy = s["LogoSize"], s["LogoPosOffset_X"], s["LogoPosOffset_Y"]
        logo_colour = np.array(v["LogoLayer0_Color"][:3])
        bright = s["LogoLayer0_Brightness"]
        logo = load("T_UE_Logo_M")[..., 1:2]                    # the graph reads its G (LinearGrayscale)
        # Only the texels the logo can reach (ScaleUVsByCenter's 0-1 box), each SUPERSAMPLED 4 x 4:
        # saturating 16x the mask is a hard edge, and one sample a texel draws it in steps.
        c0 = int(np.floor((0.5 - ox - size / 2) * SIZE)) - 1
        r0 = int(np.floor((0.5 - oy - size / 2) * SIZE)) - 1
        n = int(np.ceil(size * SIZE)) + 3
        k = 4
        sub = (np.arange(n * k) + 0.5) / k
        U, V = np.meshgrid((c0 + sub) / SIZE, (r0 + sub) / SIZE)  # V down, row 0 = v 0
        su, sv = (U + ox - 0.5) / size + 0.5, (V + oy - 0.5) / size + 0.5   # ScaleUVsByCenter
        inside = ((su >= 0) & (su <= 1) & (sv >= 0) & (sv <= 1)).astype(np.float64)   # its 0-1 mask
        sphere = np.clip((1 - np.hypot(su - 0.5, sv - 0.5) / SPHERE_RADIUS) / (1 - SPHERE_HARDNESS), 0, 1)
        fine = np.clip(bright * bilinear(logo, su, sv)[..., 0] * inside * sphere, 0, 1)
        amount = np.zeros((SIZE, SIZE, 1))
        amount[r0:r0 + n, c0:c0 + n, 0] = fine.reshape(n, k, n, k).mean(axis=(1, 3))
        emissive = np.clip(logo_colour * 1.0, 0, 1)[None, None, :]
        lin = lin * (1 - amount) + emissive * amount
        on = amount[..., 0] > 0.5
        ys, xs = np.nonzero(on)
        print("  %s: the logo layer 0, colour %s x %.0f, size %.3f at uv (%.3f, %.3f): %d texels, uv box "
              "u %.3f..%.3f v %.3f..%.3f" % (key, list(logo_colour), bright, size, 0.5 - ox, 0.5 - oy,
                                           int(on.sum()), xs.min() / SIZE, xs.max() / SIZE,
                                           ys.min() / SIZE, ys.max() / SIZE))
    print("  %s: linear %.4f..%.4f" % (key, lin.min(), lin.max()))
    save_rgb(to_srgb(lin), out)


def normal_map(name, out, flat_name=None):
    """Average as vectors, renormalise, green into Maya's (OpenGL) convention."""
    n = shrink(load(name)[..., :3] * 2.0 - 1.0, SIZE)
    n /= np.maximum(np.linalg.norm(n, axis=2, keepdims=True), 1e-8)
    tilt = np.degrees(np.arccos(np.clip(n[..., 2], -1, 1)))
    print("  %s: tilt off +Z mean %.2f deg, p99 %.1f" % (name, tilt.mean(), np.percentile(tilt, 99)))
    n[..., 1] *= -1.0
    save_rgb(n * 0.5 + 0.5, out)


for info in params["textures"].values():
    if info.get("flip_green"):
        raise RuntimeError("a texture Unreal flips green on import: %s" % params["textures"])
if params["slots"] != [["M_HeadLegs", HEADLEGS], ["M_Torso", TORSO]]:
    raise RuntimeError("slots %s" % params["slots"])
if M[HEADLEGS]["switches"].get("UseLogo") or not M[TORSO]["switches"].get("UseLogo"):
    raise RuntimeError("the logo is not where it was measured: %s / %s"
                       % (M[HEADLEGS]["switches"], M[TORSO]["switches"]))

os.makedirs(OUT, exist_ok=True)
print("-> " + OUT)
colour_map("HeadLegs", M[HEADLEGS], "T_Manny_01_D", "Manny_HeadLegs_Color.jpg")
colour_map("Torso", M[TORSO], "T_Manny_02_D", "Manny_Torso_Color.jpg")
normal_map("T_Manny_01_BN", "Manny_HeadLegs_Normal.jpg")
normal_map("T_Manny_02_BN", "Manny_Torso_Normal.jpg")
total = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT))
print("total %.1f MB in %d files" % (total / 1e6, len(os.listdir(OUT))))
