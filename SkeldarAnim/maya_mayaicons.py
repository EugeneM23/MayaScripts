"""Maya's icons in the hub's style (2026-10-17): every icon recoloured, the
most visible redrawn (maya_mayaicons_art).

The animator: «перерисовать все иконки интерфейса маи под наш стиль», then
«recolour all icons, and redraw the most visible ~150 in our line style».
Spec: docs/superpowers/specs/2026-10-17-maya-icons-design.md

A PNG of an icon's name in `<userAppDir>/2027/prefs/icons` (the first folder
of XBMLANGPATH) is what Maya's `createIcon` answers (measured). So On writes
there and Off deletes what it wrote:

    enabled() / set_enabled(on)   ⋮ -> Maya icons (off by default); shows
                                  after Maya restarts
    recolour(rgba, keep_axes)     numpy: greys to the hub's, accents orange
    render(name, w, h)            one of our drawings as a QImage
    write_icons(dest, ...)        every icon into `dest`, a manifest of ours
    remove_icons(dest)            ours out of `dest`, nothing else

Autodesk's pictures are recoloured on each machine from its own Maya and never
shipped. A file in `dest` we did not write is never touched.
"""

import hashlib
import json
import os
import tempfile

import maya_hubstyle as hubstyle
import maya_mayaicons_art as art

OPTIONVAR = "skeldarMayaIcons"
MANIFEST = "skeldarMayaIcons.json"
T = hubstyle.TOKENS

#  icons whose red, green and blue mean X, Y and Z
AXES = frozenset(("move_M", "rotate_M", "scale_M", "showManip",
                  "universalManip", "moveTool", "rotateTool", "scaleTool"))


def _rgb01(hex_colour):
    h = hex_colour.lstrip("#")
    return [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]


DARK = _rgb01(T["track"])
LIGHT = _rgb01(T["text"])
ACCENT = _rgb01(T["accent"])


# --------------------------------------------------------------- recolour

def recolour(rgba, keep_axes=False):
    """`rgba` (h, w, 4 floats 0..1) in the hub's colours: neutral greys
    between the hub's darkest and its text by luminance, saturated colours to
    the accent's hue keeping their saturation and value, alpha as it is.
    `keep_axes`: reds, greens and blues stay (an axis icon's X, Y, Z)."""
    import numpy as np
    a = np.asarray(rgba, dtype=np.float32)
    rgb = a[..., :3]
    mx = rgb.max(-1)
    mn = rgb.min(-1)
    sat = np.where(mx > 1e-6, (mx - mn) / np.maximum(mx, 1e-6), 0.0)
    lum = rgb @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    t = np.clip(lum / 0.8, 0.0, 1.0)[..., None]
    grey_out = (np.array(DARK, np.float32) * (1 - t)
                + np.array(LIGHT, np.float32) * t)
    #  the accent at this pixel's saturation and value
    accent = np.array(ACCENT, np.float32)
    base = accent / max(float(accent.max()), 1e-6)
    v = mx[..., None]
    s = np.clip(sat * 0.9 + 0.1, 0.0, 1.0)[..., None]
    acc_out = v * ((1.0 - s) + s * base)
    grey = (sat < 0.18)[..., None]
    out = np.where(grey, grey_out, acc_out)
    if keep_axes:
        hue = _hue(rgb, mx, mn)
        axis = ((sat >= 0.18)
                & ((hue < 0.04) | (hue > 0.95)
                   | ((hue > 0.25) & (hue < 0.42))
                   | ((hue > 0.58) & (hue < 0.70))))[..., None]
        out = np.where(axis, rgb, out)
    return np.concatenate([np.clip(out, 0, 1), a[..., 3:4]], -1)


def _hue(rgb, mx, mn):
    import numpy as np
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    d = np.maximum(mx - mn, 1e-6)
    h = np.where(mx == r, ((g - b) / d) % 6,
                 np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4))
    return np.where(mx - mn > 1e-6, h / 6.0, 0.0)


# --------------------------------------------------------------------- qt

def _qt():
    try:
        from PySide6 import QtCore, QtGui, QtSvg
    except ImportError:
        from PySide2 import QtCore, QtGui, QtSvg
    return QtCore, QtGui, QtSvg


def to_array(image):
    """A QImage as (h, w, 4) floats 0..1, RGBA."""
    import numpy as np
    QtCore, QtGui, _ = _qt()                                 # noqa: N806
    img = image.convertToFormat(QtGui.QImage.Format_RGBA8888)
    w, h = img.width(), img.height()
    buf = np.frombuffer(img.constBits(), np.uint8,
                        count=img.sizeInBytes()).reshape(h, img.bytesPerLine())
    return buf[:, :w * 4].reshape(h, w, 4).astype(np.float32) / 255.0


def from_array(a):
    import numpy as np
    _, QtGui, _ = _qt()                                      # noqa: N806
    data = (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8).copy()
    h, w = data.shape[:2]
    return QtGui.QImage(data.data, w, h, w * 4,
                        QtGui.QImage.Format_RGBA8888).copy()


def qimage_recoloured(image, name):
    """Maya's icon `image` recoloured (axis icons keep their axes)."""
    stem = os.path.splitext(name)[0]
    return from_array(recolour(to_array(image), stem in AXES))


def render(name, width, height):
    """Our drawing of `name` (no extension) as a width x height QImage."""
    QtCore, QtGui, QtSvg = _qt()                             # noqa: N806
    renderer = QtSvg.QSvgRenderer(QtCore.QByteArray(
        art.svg(name).encode("utf-8")))
    image = QtGui.QImage(width, height, QtGui.QImage.Format_ARGB32)
    image.fill(QtCore.Qt.transparent)
    painter = QtGui.QPainter(image)
    painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
    side = min(width, height)
    renderer.render(painter, QtCore.QRectF((width - side) / 2.0,
                                           (height - side) / 2.0, side, side))
    painter.end()
    return image


def png_bytes(image):
    QtCore, _, _ = _qt()                                     # noqa: N806
    buf = QtCore.QByteArray()
    io = QtCore.QBuffer(buf)
    io.open(QtCore.QIODevice.WriteOnly)
    image.save(io, "PNG")
    io.close()
    return bytes(buf)


# ----------------------------------------------------------------- folder

def _sha1(data):
    return hashlib.sha1(data).hexdigest()


def read_manifest(dest):
    path = os.path.join(dest, MANIFEST)
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle).get("files", {})
    except Exception:                                        # noqa: BLE001
        return {}


def _write_manifest(dest, files):
    path = os.path.join(dest, MANIFEST)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump({"files": files}, handle, indent=0, sort_keys=True)


def file_sha1(path):
    try:
        with open(path, "rb") as handle:
            return _sha1(handle.read())
    except Exception:                                        # noqa: BLE001
        return None


def may_write(dest, filename, ours):
    """We may write `filename` in `dest`: it is not there, or it is ours and
    unchanged since (`ours`: the manifest)."""
    path = os.path.join(dest, filename)
    if not os.path.exists(path):
        return True
    return filename in ours and file_sha1(path) == ours[filename]


def write_icons(dest, sources, progress=None):
    """Every icon of `sources` (filename, QImage of Maya's own) into `dest`:
    a drawn name from our drawing at the icon's size, any other recoloured.
    A file of the animator's is left. `progress(i, n)` answering False stops.
    Answers (written, kept_theirs, stopped)."""
    os.makedirs(dest, exist_ok=True)
    ours = read_manifest(dest)
    drawn = set(art.NAMES)
    sources = list(sources)
    written, kept, stopped = 0, [], False
    for i, (filename, image) in enumerate(sources):
        if progress is not None and progress(i, len(sources)) is False:
            stopped = True
            break
        if not may_write(dest, filename, ours):
            kept.append(filename)
            continue
        stem = os.path.splitext(filename)[0]
        try:
            if stem in drawn:
                new = render(stem, image.width() or 20, image.height() or 20)
            else:
                new = qimage_recoloured(image, filename)
            data = png_bytes(new)
        except Exception:                                    # noqa: BLE001
            continue
        with open(os.path.join(dest, filename), "wb") as handle:
            handle.write(data)
        ours[filename] = _sha1(data)
        written += 1
        if written % 200 == 0:
            _write_manifest(dest, ours)
    _write_manifest(dest, ours)
    return written, kept, stopped


def remove_icons(dest):
    """Ours out of `dest`: each file of the manifest still holding what we
    wrote. Answers (removed, kept_changed)."""
    ours = read_manifest(dest)
    removed, changed = 0, []
    for filename, sha in sorted(ours.items()):
        path = os.path.join(dest, filename)
        if not os.path.exists(path):
            continue
        if file_sha1(path) != sha:
            changed.append(filename)
            continue
        try:
            os.remove(path)
            removed += 1
        except Exception:                                    # noqa: BLE001
            changed.append(filename)
    try:
        os.remove(os.path.join(dest, MANIFEST))
    except Exception:                                        # noqa: BLE001
        pass
    return removed, changed


# ------------------------------------------------------------------- maya

def _cmds():
    import maya.cmds as cmds
    return cmds


def icons_dir():
    """`<userAppDir>/<version>/prefs/icons`, the first folder Maya looks in."""
    return os.path.normpath(_cmds().internalVar(userBitmapsDir=True))


def enabled():
    try:
        cmds = _cmds()
        if not cmds.optionVar(exists=OPTIONVAR):
            return False
        return bool(cmds.optionVar(query=OPTIONVAR))
    except Exception:                                        # noqa: BLE001
        return False


def maya_sources():
    """Every PNG of Maya's resources as (filename, QImage), read through a
    temp folder."""
    _, QtGui, _ = _qt()                                      # noqa: N806
    cmds = _cmds()
    tmp = tempfile.mkdtemp(prefix="skeldar_icons_")
    for filename in sorted(cmds.resourceManager(nameFilter="*.png") or []):
        path = os.path.join(tmp, filename)
        try:
            cmds.resourceManager(saveAs=(filename, path))
            image = QtGui.QImage(path)
            os.remove(path)
        except Exception:                                    # noqa: BLE001
            continue
        if not image.isNull():
            yield filename, image


def set_enabled(on):
    """⋮ -> Maya icons: written or removed, remembered, the line to say."""
    on = bool(on)
    cmds = _cmds()
    dest = icons_dir()
    if on:
        batch = cmds.about(batch=True)
        if not batch:
            cmds.progressWindow(title="Maya icons", status="Drawing icons...",
                                isInterruptable=True, progress=0, maxValue=100)

        def progress(i, n):
            if batch or i % 25:
                return True
            if cmds.progressWindow(query=True, isCancelled=True):
                return False
            cmds.progressWindow(edit=True, progress=int(100.0 * i / max(n, 1)),
                                status="Icon %d of %d" % (i, n))
            return True
        try:
            written, kept, stopped = write_icons(dest, maya_sources(),
                                                 progress)
        finally:
            if not batch:
                cmds.progressWindow(endProgress=True)
        if stopped:
            removed, _ = remove_icons(dest)
            cmds.optionVar(intValue=(OPTIONVAR, 0))
            return ("Maya icons: stopped - nothing changed (%d written and "
                    "taken back)" % removed)
        cmds.optionVar(intValue=(OPTIONVAR, 1))
        message = ("Maya icons ON - %d icons in the hub's style; restart "
                   "Maya to see them" % written)
        if kept:
            message += (" | %d of your own icons in %s kept"
                        % (len(kept), dest))
        return message
    removed, changed = remove_icons(dest)
    cmds.optionVar(intValue=(OPTIONVAR, 0))
    message = ("Maya icons OFF - %d icons taken out; restart Maya to see its "
               "own" % removed)
    if changed:
        message += " | %d changed since kept" % len(changed)
    return message
