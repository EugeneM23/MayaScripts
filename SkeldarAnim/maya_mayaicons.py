"""Maya's icons in the hub's style (2026-10-17): every icon recoloured, the
most visible redrawn (maya_mayaicons_art).

The animator: «перерисовать все иконки интерфейса маи под наш стиль», then
«recolour all icons, and redraw the most visible ~150 in our line style».
Spec: docs/superpowers/specs/2026-10-17-maya-icons-design.md

Every icon (`name.png`, `name_150.png`, `name_200.png`) is drawn or
recoloured into a folder of ours, and Maya's icon buttons are pointed at it
by full path - at once, and every WATCH_MS for panels built later. (A file of
an icon's name in prefs/icons does not reach Maya's own buttons: measured.)

    enabled() / set_enabled(on)   ⋮ -> Maya icons (off by default), at once
    ensure()                      at Maya's start: point the buttons again
    recolour(rgba, keep_axes)     numpy: greys to the hub's, accents orange
    render(name, w, h)            one of our drawings as a QImage
    write_icons(dest, ...)        every icon into `dest`, a manifest of ours
    remove_icons(dest)            ours out of `dest`, nothing else
    pointed / repoint             which image a button carries, and setting it

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
    stem = base_stem(name)[0]
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


#  Maya keeps each icon at three sizes, `name.png`, `name_150.png` and
#  `name_200.png`, and at a 150 % or 200 % display takes the large one first
#  (measured 2026-10-17 in a GUI Maya: `:/move_M_150.png` and `_200` exist
#  though `resourceManager` lists neither, and with only `move_M.png` of ours
#  in prefs/icons the toolbox kept Maya's). Every size is written.
SCALES = (("_150", 1.5), ("_200", 2.0))


def base_stem(filename):
    """("move_M", "_150") for "move_M_150.png"; ("move_M", "") for the 1x."""
    stem = os.path.splitext(os.path.basename(filename))[0]
    for suffix, _ in SCALES:
        if stem.endswith(suffix) and len(stem) > len(suffix):
            return stem[:-len(suffix)], suffix
    return stem, ""


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
        stem, _suffix = base_stem(filename)
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
    """Every PNG of Maya's resources as (filename, QImage): from Qt's
    resource tree (`:/name.png`, `:/name_150.png`, `:/name_200.png` - a GUI
    Maya has them all), else, where that tree holds no icon (mayapy), the 1x
    ones `resourceManager` lists, read through a temp folder."""
    QtCore, QtGui, _ = _qt()                                 # noqa: N806
    names = qt_resource_pngs()
    if names:
        for filename in names:
            image = QtGui.QImage(":/" + filename)
            if not image.isNull():
                yield filename, image
        return
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


def qt_resource_pngs():
    """The PNG files at the root of Qt's resource tree (Maya's icons)."""
    QtCore, _, _ = _qt()                                     # noqa: N806
    out = []
    it = QtCore.QDirIterator(":/", QtCore.QDirIterator.NoIteratorFlags)
    while it.hasNext():
        path = it.next()
        name = path[2:] if path.startswith(":/") else path
        if name.lower().endswith(".png") and "/" not in name:
            out.append(name)
    return sorted(out)


# ---------------------------------------------------------- the buttons
#
#  A file of an icon's name in prefs/icons does NOT reach Maya's own buttons
#  (measured 2026-10-17 in a GUI Maya, after a restart: the toolbox, the
#  status line and a freshly made iconTextButton all drew Maya's resource,
#  though `MQtUtil.createIcon` answered ours). Pointed at our file by its
#  full path, a button draws ours at once. So ours live in a folder of our
#  own and every icon button is pointed there - now, and every WATCH_MS for
#  the panels Maya builds later (a sweep costs ~0.02 s for ~500 buttons).

#  the cmds kinds that carry an image, and their image flags
KINDS = (("iconTextButton", "image1"), ("iconTextCheckBox", "image1"),
         ("iconTextRadioButton", "image1"), ("symbolButton", "image"),
         ("symbolCheckBox", "image"), ("shelfButton", "image1"),
         ("toolButton", "image1"))
WATCH_MS = 2000
STATE = "_skeldar_mayaicons"           # on sys (trap 111)


def pointed(image, folder, have, on):
    """The image a button should carry: on, an icon we have (by its file
    name, wherever Maya resolved it) points into `folder`; off, one of ours
    goes back to its bare name. None = leave it."""
    if not image:
        return None
    norm = image.replace("\\", "/")
    folder = folder.replace("\\", "/").rstrip("/") + "/"
    name = norm.rsplit("/", 1)[-1]
    ours = norm.lower().startswith(folder.lower())
    if on:
        if ours or name not in have:
            return None
        return folder + name
    return name if ours else None


def repoint(folder, have, on=True):
    """Every icon button of Maya pointed at our file (on) or back at Maya's
    (off). Answers how many changed."""
    cmds = _cmds()
    changed = 0
    for kind, flag in KINDS:
        command = getattr(cmds, kind)
        #  by full path: Maya names the buttons of every viewport alike
        #  ("ShadedBtn" four times), and a short name edits the first only
        for control in cmds.lsUI(type=kind, long=True) or []:
            try:
                image = command(control, query=True, **{flag: True})
                new = pointed(image, folder, have, on)
                if new is not None:
                    command(control, edit=True, **{flag: new})
                    changed += 1
            except Exception:                                # noqa: BLE001
                continue
    return changed


def icon_folder():
    """`<userAppDir>/<version>/SkeldarIcons`: ours, outside Maya's own
    icon folders."""
    cmds = _cmds()
    return os.path.normpath(os.path.join(cmds.internalVar(userAppDir=True),
                                         cmds.about(version=True),
                                         "SkeldarIcons"))


def have_in(folder):
    try:
        return frozenset(n for n in os.listdir(folder) if n.endswith(".png"))
    except Exception:                                        # noqa: BLE001
        return frozenset()


def _state():
    import sys
    state = getattr(sys, STATE, None)
    if state is None:
        state = {}
        setattr(sys, STATE, state)
    return state


def watch(folder):
    """A timer that points the buttons of panels built later (WATCH_MS)."""
    QtCore, _, _ = _qt()                                     # noqa: N806
    state = _state()
    unwatch()
    have = have_in(folder)
    timer = QtCore.QTimer()
    timer.setInterval(WATCH_MS)

    def tick():
        try:
            repoint(folder, have, True)
        except Exception:                                    # noqa: BLE001
            pass
    timer.timeout.connect(tick)
    timer.start()
    state["timer"] = timer
    return timer


def unwatch():
    timer = _state().pop("timer", None)
    if timer is not None:
        try:
            timer.stop()
        except Exception:                                    # noqa: BLE001
            pass


def _write_all(folder):
    """Every icon into `folder`, under a progress window Esc stops. Answers
    (written, stopped)."""
    cmds = _cmds()
    batch = cmds.about(batch=True)
    if not batch:
        cmds.progressWindow(title="Maya icons", status="Drawing icons...",
                            isInterruptable=True, progress=0, maxValue=100)

    def progress(i, n):
        if batch or i % 50:
            return True
        if cmds.progressWindow(query=True, isCancelled=True):
            return False
        cmds.progressWindow(edit=True, progress=int(100.0 * i / max(n, 1)),
                            status="Icon %d of %d" % (i, n))
        return True
    try:
        written, _, stopped = write_icons(folder, maya_sources(), progress)
    finally:
        if not batch:
            cmds.progressWindow(endProgress=True)
    return written, stopped


def _legacy_cleanup():
    """The first build wrote into prefs/icons (never seen by Maya's buttons):
    ours there go."""
    try:
        return remove_icons(icons_dir())[0]
    except Exception:                                        # noqa: BLE001
        return 0


def ensure():
    """At Maya's start (the hub's build), while the icons are on: the files
    made if they are missing, the buttons pointed, the watch started."""
    if not enabled():
        return 0
    folder = icon_folder()
    if not read_manifest(folder):
        _write_all(folder)
    count = repoint(folder, have_in(folder), True)
    if not _cmds().about(batch=True):
        watch(folder)
    return count


def set_enabled(on):
    """⋮ -> Maya icons: our icons drawn and Maya's buttons pointed at them,
    at once; or every button back on Maya's and our folder emptied."""
    on = bool(on)
    cmds = _cmds()
    folder = icon_folder()
    legacy = _legacy_cleanup()
    if on:
        written, stopped = _write_all(folder)
        if stopped:
            remove_icons(folder)
            cmds.optionVar(intValue=(OPTIONVAR, 0))
            return "Maya icons: stopped - nothing changed"
        count = repoint(folder, have_in(folder), True)
        if not cmds.about(batch=True):
            watch(folder)
        cmds.optionVar(intValue=(OPTIONVAR, 1))
        message = ("Maya icons ON - %d buttons now show our icons (%d drawn "
                   "or recoloured); the Outliner's node icons stay Maya's"
                   % (count, written))
    else:
        unwatch()
        count = repoint(folder, have_in(folder), False)
        removed, _ = remove_icons(folder)
        cmds.optionVar(intValue=(OPTIONVAR, 0))
        message = ("Maya icons OFF - %d buttons back on Maya's icons" % count)
    if legacy:
        message += " | %d files of the first build taken out of prefs/icons" % legacy
    return message
