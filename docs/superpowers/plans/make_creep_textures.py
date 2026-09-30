"""The Creep's texture maps into SkeldarAnim/assets/Creep/.

    mayapy make_creep_textures.py

2026-09-30 (spec: docs/superpowers/specs/2026-09-30-creep-textured-design.md), the animator: «Вот текстуры
для крипа давай сделаем тоже самое что и для мени» -- and asked, the whole Creep («Весь Крип»). Reads
sources/creep/textures/ (the animator's body colour and normal and head colour; the head's normal and the
set the back and both arms share, out of the Creep's Cascadeur FBX -- the same images Cascadeur embedded)
and writes three sets at the Orc D's and Manny's 2048 JPG q95:

- `Creep_Body_{Color,Normal}.jpg`   the body            (creep_body_diff.png, creep_body_norm.png)
- `Creep_Face_{Color,Normal}.jpg`   the head            (creep_face_diff.jpg, creep_face_norm.jpg)
- `Creep_Limbs_{Color,Normal}.jpg`  the back and arms   (creep_limbs_diff.png, creep_limbs_norm.png)

Cascadeur's materials are phongs with the texture on `.color` at diffuse 1: no maths to bake, the colour
is the image. The normal maps are averaged as vectors and renormalised, and their green is turned into
Maya's (OpenGL) convention WHERE IT IS NOT ALREADY -- which is measured, not assumed: a height field's
normals are curl-free, so in image coordinates (x right, rows down) d(nx)/dy and d(ny)/dx correlate
positively for a DirectX map and negatively for an OpenGL one (Unreal's own maps: +0.27, +0.39 at 512).
Measured 2026-09-30 at 256..2048 alike, and by the residual curl of either reading too: the body (-0.24 at
512) and the back/arms (-0.30) OpenGL, left as they are; the head (+0.61) DirectX, flipped. A map the test
cannot decide (|corr| < 0.1) is refused.
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import numpy as np  # noqa: E402
from PySide6.QtGui import QImage  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

APP = QApplication.instance() or QApplication([])
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
SRC = os.path.join(REPO, "sources", "creep", "textures")
OUT = os.path.join(REPO, "SkeldarAnim", "assets", "Creep")
SIZE = 2048
QUALITY = 95
SETS = (("Body", "creep_body_diff.png", "creep_body_norm.png"),
        ("Face", "creep_face_diff.jpg", "creep_face_norm.jpg"),
        ("Limbs", "creep_limbs_diff.png", "creep_limbs_norm.png"))


def load(name):
    """An image as float64 0..1, (h, w, 3), row 0 the image's top."""
    img = QImage(os.path.join(SRC, name))
    if img.isNull():
        raise RuntimeError("cannot read " + name)
    img = img.convertToFormat(QImage.Format_RGB888)
    w, h = img.width(), img.height()
    raw = np.frombuffer(img.constBits(), dtype=np.uint8, count=img.sizeInBytes())
    return raw.reshape(h, img.bytesPerLine())[:, :w * 3].reshape(h, w, 3).astype(np.float64) / 255.0


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


def save_rgb(rgb01, name):
    data = np.ascontiguousarray(np.round(np.clip(rgb01, 0, 1) * 255).astype(np.uint8))
    h, w = data.shape[:2]
    img = QImage(data.tobytes(), w, h, w * 3, QImage.Format_RGB888).copy()
    path = os.path.join(OUT, name)
    if not img.save(path, "JPG", QUALITY):
        raise RuntimeError("could not write " + path)
    print("  %-24s %dx%d  %.2f MB" % (name, w, h, os.path.getsize(path) / 1e6))


def green_convention(n):
    """+corr: DirectX (green down), -corr: OpenGL (green up) -- see the docstring."""
    nx, ny = n[..., 0], n[..., 1]
    dnx_dy = nx[2:, 1:-1] - nx[:-2, 1:-1]
    dny_dx = ny[1:-1, 2:] - ny[1:-1, :-2]
    live = (np.abs(dnx_dy) + np.abs(dny_dx)) > 0.02
    return float(np.corrcoef(dnx_dy[live], dny_dx[live])[0, 1])


os.makedirs(OUT, exist_ok=True)
print("-> " + OUT)
for key, diff, norm in SETS:
    colour = load(diff)
    if colour.shape[:2] != (SIZE, SIZE):
        colour = to_srgb(shrink(to_linear(colour), SIZE))
    save_rgb(colour, "Creep_%s_Color.jpg" % key)
    n = shrink(load(norm) * 2.0 - 1.0, SIZE)
    n /= np.maximum(np.linalg.norm(n, axis=2, keepdims=True), 1e-8)
    corr = green_convention(shrink(n, 512))                 # the pixel grain blurs it at 2048
    if abs(corr) < 0.1:
        raise RuntimeError("%s: the green convention cannot be told (corr %+.3f)" % (norm, corr))
    if corr > 0:
        n[..., 1] *= -1.0
    print("  %s: green %+.3f -> %s" % (norm, corr, "DirectX, flipped into Maya's" if corr > 0 else "OpenGL, as it is"))
    save_rgb(n * 0.5 + 0.5, "Creep_%s_Normal.jpg" % key)
total = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT))
print("total %.1f MB in %d files" % (total / 1e6, len(os.listdir(OUT))))
