"""The Orc D's texture maps, Unreal's material maths baked in, into SkeldarAnim/assets/Orc_D/.

    mayapy make_orc_d_textures.py

2026-09-28 (spec: docs/superpowers/specs/2026-09-28-orc-d-textured-design.md).  Reads what
`export_orc_d_from_unreal.py` wrote to sources/orc/ -- the seven textures at their own size and
`orc_d_materials.json` -- and writes, at the animator's pick of 2048 JPG («2048, JPG»):

- `Orc_D_Body_Color.jpg`   the body as `M_Orc_Marauder_MasterMaterial_SP` computes it, in linear:
                           lerp(pow(base * BC_Intensity, BC_Contrast), TattooColorA * atlas(u),
                                tattooMask.R * Tattoos_Power_A)
                           (Saturation is clamped to 1 by the graph, the body colour mask is off,
                           Skin_Color is white -- each a no-op, so none is applied);
- `Orc_D_Cloth_Color.jpg`  `M_Orc_Marauder_MasterMaterial`: base * BC_Intensity, BC_Contrast 1
                           (the ID-map colours are all white, Saturation 1.1 clamped to 1);
- `Orc_D_Cloth_Mask.png`   the cloth's opacity mask -- the base colour's ALPHA -- cut at the
                           master's clip value (0.3333): 0 or 255, a hard cut the viewport does
                           not have to sort;
- `Orc_D_Body_Normal.jpg`, `Orc_D_Cloth_Normal.jpg`  the normal maps, averaged as vectors and
                           renormalised, the green channel turned into Maya's convention (Unreal's
                           are DirectX: green down);
- `Orc_D_Eye_Color.jpg`    1024^2, `M_Orc_Marauder_Eye_MasterMaterial` without its refraction:
                           shadow(uv) * lerp(sclera * ScleraBrightness,
                                             iris(uv') * Iris_BRightness * limbus, irisMask).

Everything is computed in LINEAR light (the sRGB textures decoded exactly, the masks read raw),
averaged down in linear, and encoded to sRGB last.  Refuses a result that would clip past 1.0 by
more than a hair: an 8-bit image cannot hold what Unreal's maths makes of it then.
"""
import json
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import numpy as np  # noqa: E402
from PySide6.QtGui import QImage  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

APP = QApplication.instance() or QApplication([])
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
SRC = os.path.join(REPO, "sources", "orc")
TEX = os.path.join(SRC, "textures")
OUT = os.path.join(REPO, "SkeldarAnim", "assets", "Orc_D")
SIZE = 2048
EYE_SIZE = 1024
QUALITY = 95

params = json.load(open(os.path.join(SRC, "orc_d_materials.json")))
M = params["materials"]
BODY = M["/Game/Orc_Marauder/Materials/MI_Orc_Marauder_Body_A_Inst"]
CLOTH = M["/Game/Orc_Marauder/Materials/MI_Orc_Marauder_Cloth_Inst"]
EYE = M["/Game/Orc_Marauder/Materials/MI_Orc_Marauder_Eye_Inst"]
ATLAS = np.array(params["atlas_CA_Mannequin"], dtype=np.float64)[:, :3]


def load(name, deep=False):
    """An image as float64 0..1, (h, w, 4). `deep` reads 16 bits a channel."""
    img = QImage(os.path.join(TEX, name + ".png"))
    if img.isNull():
        raise RuntimeError("cannot read " + name)
    fmt, dtype, scale = ((QImage.Format_RGBA64, np.uint16, 65535.0) if deep
                         else (QImage.Format_RGBA8888, np.uint8, 255.0))
    img = img.convertToFormat(fmt)
    w, h = img.width(), img.height()
    raw = np.frombuffer(img.constBits(), dtype=dtype, count=img.sizeInBytes() // np.dtype(dtype).itemsize)
    per_line = img.bytesPerLine() // np.dtype(dtype).itemsize
    return raw.reshape(h, per_line)[:, :w * 4].reshape(h, w, 4).astype(np.float64) / scale


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


def save_rgb(rgb01, name, quality=QUALITY):
    data = np.ascontiguousarray(np.round(np.clip(rgb01, 0, 1) * 255).astype(np.uint8))
    h, w = data.shape[:2]
    img = QImage(data.tobytes(), w, h, w * 3, QImage.Format_RGB888).copy()
    path = os.path.join(OUT, name)
    if not img.save(path, "JPG" if name.endswith(".jpg") else "PNG", quality):
        raise RuntimeError("could not write " + path)
    print("  %-24s %dx%d  %.2f MB" % (name, w, h, os.path.getsize(path) / 1e6))


def save_grey(g01, name):
    data = np.ascontiguousarray(np.round(np.clip(g01, 0, 1) * 255).astype(np.uint8))
    h, w = data.shape
    img = QImage(data.tobytes(), w, h, w, QImage.Format_Grayscale8).copy()
    path = os.path.join(OUT, name)
    if not img.save(path, "PNG"):
        raise RuntimeError("could not write " + path)
    print("  %-24s %dx%d  %.2f MB" % (name, w, h, os.path.getsize(path) / 1e6))


def check(lin, what, allowed=0.002):
    over = float((lin > 1.0).mean())
    print("  %s: linear max %.4f, %.4f %% of texels past 1.0" % (what, lin.max(), over * 100))
    if over > allowed:
        raise RuntimeError("%s clips: %.3f %% of texels past 1.0" % (what, over * 100))


def normal_map(name, out):
    """Average as vectors, renormalise, green into Maya's (OpenGL) convention."""
    n = shrink(load(name)[..., :3] * 2.0 - 1.0, SIZE)
    n /= np.maximum(np.linalg.norm(n, axis=2, keepdims=True), 1e-8)
    n[..., 1] *= -1.0
    save_rgb(n * 0.5 + 0.5, out)


os.makedirs(OUT, exist_ok=True)
print("-> " + OUT)

# --- the body
base = load("T_Orc_Marauder_Body_BaseColor")
lin = shrink(to_linear(base[..., :3]), SIZE)
s = BODY["scalars"]
skin = np.power(lin * s["BC_Intensity"], s["BC_Contrast"])
mask = load("T_Orc_Marauder_Body_Tatoo_Mask", deep=True)
mask = shrink(mask, SIZE) if mask.shape[0] > SIZE else mask
alpha = np.clip(mask[..., 0] * s["Tattoos_Power_A"], 0, 1)[..., None]      # Mask_Chanel = R
u = (np.arange(SIZE) + 0.5) / SIZE
atlas = np.array([np.interp(u, (np.arange(64) + 0.5) / 64.0, ATLAS[:, k]) for k in range(3)]).T  # (SIZE, 3)
tattoo = np.array(BODY["vectors"]["Tattoos_Color_A"][:3])[None, None, :] * atlas[None, :, :]
body = skin * (1 - alpha) + tattoo * alpha
check(body, "body")
print("  body: tattoo on %.1f %% of the texels, its linear colour at most %s"
      % (float((alpha > 0.5).mean()) * 100, np.round(tattoo.max(axis=(0, 1)), 4)))
save_rgb(to_srgb(body), "Orc_D_Body_Color.jpg")
normal_map("T_Orc_Marauder_Body_Normal", "Orc_D_Body_Normal.jpg")

# --- the cloth
base = load("T_Orc_Marauder_Cloth_BaseColor")
s = CLOTH["scalars"]
cloth = np.power(shrink(to_linear(base[..., :3]), SIZE) * s["BC_Intensity"], s["BC_Contrast"])
check(cloth, "cloth")
save_rgb(to_srgb(cloth), "Orc_D_Cloth_Color.jpg")
clip = CLOTH["parent_clip"]
cut = (shrink(base[..., 3:4], SIZE)[..., 0] >= clip).astype(np.float64)
print("  cloth: opacity clip %.4f, %.2f %% of the texels cut away" % (clip, float((cut == 0).mean()) * 100))
save_grey(cut, "Orc_D_Cloth_Mask.png")
normal_map("T_Orc_Marauder_Cloth_Normal", "Orc_D_Cloth_Normal.jpg")

# --- the eye (no refraction: the iris straight onto the eye's own uvs)
s = EYE["scalars"]
sclera = shrink(to_linear(load("T_Orc_Marauder_Eyes_ScleraBaseColor")[..., :3]), EYE_SIZE)
iris_img = to_linear(load("T_Orc_Marauder_Eyes_BaseColor")[..., :3])
g = (np.arange(EYE_SIZE) + 0.5) / EYE_SIZE
U, V = np.meshgrid(g, g)
d = np.hypot(U - 0.5, V - 0.5)
R = s["Iris UV Radius"]
iu, iv = (U - 0.5) / (2 * R) + 0.5, (V - 0.5) / (2 * R) + 0.5
limbus = 1.0 - np.power(np.clip(np.hypot(iu - 0.5, iv - 0.5) * 2.0, 0, 1), s["LimbusPow"])
iris = bilinear(iris_img, iu, iv) * s["Iris_BRightness"] * limbus[..., None]
width = s["LimbusUVWidthColor"]
iris_mask = np.clip((R + width / 2 - d) / width, 0, 1)[..., None]
colour = sclera * s["ScleraBrightness"] * (1 - iris_mask) + iris * iris_mask
shade = np.clip((1 - d / s["ShadowRadius"]) / (1 - s["ShadowHardness"]), 0, 1)[..., None]
shadow_colour = np.array([0.23, 0.083042, 0.031906])[None, None, :]         # the graph's constant
eye = (shadow_colour * (1 - shade) + shade) * colour
check(eye, "eye", allowed=0.01)
save_rgb(to_srgb(eye), "Orc_D_Eye_Color.jpg")
total = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT))
print("total %.1f MB in %d files" % (total / 1e6, len(os.listdir(OUT))))
