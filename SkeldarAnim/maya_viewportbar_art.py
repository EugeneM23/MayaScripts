"""Maya's viewport-bar icons redrawn as vectors, in the hub's colours (2026-10-20).

The animator, after the reskin recoloured Maya's own pixel icons: «Давай иконки
ближе по дизайну к маевским можно вообще их просто перерисовать максимально
точно», then «В наших цветах». Each drawing was measured off Maya 2027's
`name_200.png` (32 px) pixel by pixel and redrawn on the same 32-unit grid:
the same shapes, Maya's dark ring round every shape (`halo_of`), the dark
inside of the gates. Mockups: https://claude.ai/artifact/L7EykZu2Dh6GvcnYzSYTYT

Classes in a drawing: g Maya's light grey, a / a1 / a2 / a3 the accent (base,
light, mid, dark - the cube's three faces), m / m1..m3 dim greys (hidden
edges, the blur trail), k a cut-out in the button's face, halo the dark ring's
colour drawn on purpose (a gate's inside, the gap round a shape on another),
`ln` a stroke rather than a fill. `id="gear"`, `id="iris"` are filled in.

    ICONS                 {Maya's image stem: the drawing}
    svg(name, face)       the drawing as a whole SVG in our colours (pure)
    render(name, px)      a px x px QImage with the ring (Qt + numpy)

Stdlib at import; Qt and numpy inside `render`.
"""

import math
import re

import maya_hubstyle as hubstyle

VERSION = 1                 # raise when a drawing changes: the bar's icons are drawn again
T = hubstyle.TOKENS

#  our colours (the mockup's B)
PALETTE = {"g": "#d5d5d7", "a": T["accent"], "a1": "#f3a66f", "a2": "#c8662b",
           "a3": "#e8894a", "m": "#8d8f95", "m1": "#a3a5ab", "m2": "#7d7f85",
           "m3": "#626469", "halo": "#141517"}
HALO_ALPHA = 0.8
HALO_UNITS = 1.35           # the ring's width on the 32-unit grid
FACE = T["card"]            # what a cut-out shows: the group's well

DEFS = ('<defs>'
        '<pattern id="hatch" width="2.6" height="2.6" patternUnits="userSpaceOnUse" '
        'patternTransform="rotate(45)"><rect width="1.4" height="2.6" fill="{m}"/></pattern>'
        '<pattern id="hatchG" width="2.6" height="2.6" patternUnits="userSpaceOnUse" '
        'patternTransform="rotate(45)"><rect width="1.4" height="2.6" fill="{g}"/></pattern>'
        '<pattern id="hatchA" width="2.8" height="2.8" patternUnits="userSpaceOnUse" '
        'patternTransform="rotate(45)"><rect width="1.6" height="2.8" fill="{a}"/></pattern>'
        '</defs>')

ICONS = {
    "Camera": ('<rect class="g" x="2" y="10" width="18" height="13" rx=".6"/>'
        '<path class="g" d="M22 14.3 30 8.3V24l-8-5.3z"/>'),
    "CameraLock": ('<rect class="g" x="2" y="4" width="18" height="12" rx=".6"/>'
        '<path class="g" d="M22 7.6 30 2v15.7l-8-5.2z"/>'
        '<rect class="halo" stroke-width="2.6" stroke-linejoin="round" x="2.8" y="17" width="12.2" height="12" rx="1"/>'
        '<path class="halo ln" d="M6 17.5v-1.8a3 3 0 0 1 6 0v1.8" fill="none" stroke-width="5"/>'
        '<path class="a ln" d="M6 17.5v-1.8a3 3 0 0 1 6 0v1.8" fill="none" stroke-width="2.4"/>'
        '<rect class="a" x="2.8" y="17" width="12.2" height="12" rx="1"/>'
        '<rect class="k" x="8" y="20.3" width="2" height="5.4" rx="1"/>'),
    "CameraAE": ('<rect class="g" x="2" y="4" width="18" height="12" rx=".6"/>'
        '<path class="g" d="M22 7.6 30 2v15.7l-8-5.2z"/>'
        '<path class="halo" id="gear" d="" stroke-width="2.6" stroke-linejoin="round"/>'
        '<path class="a" id="gear" d=""/><circle class="k" cx="10.7" cy="20.2" r="3.4"/>'),
    "Bookmark": ('<path class="g" d="M10 4h12v21.7l-6-6.7-6 6.7z"/>'),
    "ImagePlane": ('<path d="M2 27.7 7.8 18H29.7L24 27.7z" fill="url(#hatchG)"/>'
        '<path class="halo" stroke-width="2.6" stroke-linejoin="round" d="M10.3 11.3 20 2v22.7l-9.7 3z"/>'
        '<path class="a" d="M10.3 11.3 20 2v22.7l-9.7 3z"/>'),
    "PanZoom": ('<path class="g" d="M15 2l4.2 5.2h-2.8v6.2h-2.8V7.2h-2.8z"/>'
        '<path class="g" d="M2 15l5.2-4.3v2.9h6v2.8h-6v2.9z"/>'
        '<circle class="a ln" cx="22.3" cy="16.7" r="5.7" fill="none" stroke-width="2.2"/>'
        '<path class="a ln" d="M18.3 20.7l-6.4 6.6" fill="none" stroke-width="3.2" stroke-linecap="round"/>'),
    "BluePencil": ('<path class="a" d="M23 3.6a2.6 2.6 0 0 1 3.7 0l.9.9a2.6 2.6 0 0 1 0 3.7L11.3 24.5l-4.6-4.6z"/>'
        '<path class="g" d="M6.7 19.9l4.6 4.6-3.2 1.4-2.8-2.8z"/>'
        '<path class="a" d="M5.3 23.1l2.8 2.8L4 28z"/>'),
    "Grid": ('<rect class="halo" x="6.3" y="6.3" width="19.4" height="19.4"/>'
        '<path class="g" fill-rule="evenodd" d="M6.3 6.3h19.4v19.4H6.3zM8.8 8.8v3.5h3.5V8.8zm5.4 0v3.5h3.6V8.8zm5.5 0v3.5h3.5V8.8zM8.8 14.2v3.6h3.5v-3.6zm5.4 0v3.6h3.6v-3.6zm5.5 0v3.6h3.5v-3.6zM8.8 19.7v3.5h3.5v-3.5zm5.4 0v3.5h3.6v-3.5zm5.5 0v3.5h3.5v-3.5z"/>'),
    "FilmGate": ('<rect class="halo" x="3" y="5" width="26" height="22"/>'
        '<path class="g" fill-rule="evenodd" d="M3 5h26v22H3zM5 11v10h22V11zM5 7v2h2.7V7zm5 0v2h2.7V7zm5 0v2h2.7V7zm4.7 0v2h2.6V7zm5 0v2H27V7zM5 23v2h2.7v-2zm5 0v2h2.7v-2zm5 0v2h2.7v-2zm4.7 0v2h2.6v-2zm5 0v2H27v-2z"/>'),
    "ResolutionGate": ('<rect class="halo" x="3" y="5" width="26" height="22"/>'
        '<path class="g" fill-rule="evenodd" d="M3 5h26v22H3zm2 2v18h22V7z"/>'
        '<circle class="a" cx="16" cy="16" r="6"/>'),
    "GateMask": ('<path class="g" fill-rule="evenodd" d="M3 5h26v20.7H3zM16 9a7 7 0 1 0 0 14 7 7 0 0 0 0-14z"/>'
        '<circle class="g" cx="16" cy="16" r="5.3"/>'),
    "FieldChart": ('<rect class="halo" x="3" y="5" width="26" height="22"/>'
        '<path class="g" fill-rule="evenodd" d="M3 5h26v22H3zm2 2v18h22V7z"/>'
        '<path class="a" d="M13 7h6v1.7h-6zM13 11h6v1.7h-6zM13 19.3h6V21h-6zM13 23.3h6V25h-6zM5 13h2v5.7H5zM9 13h2v5.7H9zM21 13h2v5.7h-2zM25 13h2v5.7h-2z"/>'),
    "SafeAction": ('<rect class="halo" x="3" y="5" width="26" height="22"/>'
        '<path class="g" fill-rule="evenodd" d="M3 5h26v22H3zm2 2v18h22V7z"/>'
        '<path class="a" d="M12 13.7l5.6 9H6.4z"/><circle class="a" cx="20.7" cy="13.3" r="4.3"/>'),
    "SafeTitle": ('<rect class="halo" x="3" y="5" width="26" height="22"/>'
        '<path class="g" fill-rule="evenodd" d="M3 5h26v22H3zm2 2v18h22V7z"/>'
        '<path class="a" d="M10 9h12v3.3h-1.2l-.6-1.6h-3V21.7h2.2V23H12.7v-1.3h2.2V10.7h-3l-.6 1.6H10z"/>'),
    "WireFrame": ('<path class="m ln" d="M16 15.3v8M16 15.3 9.5 19.2M16 15.3l6.5 3.9" fill="none" stroke-width="1.6"/>'
        '<path class="g ln" d="M16 2.5 28.5 9v14L16 29.5 3.5 23V9zM3.5 9 16 15.3 28.5 9M16 15.3v14.2" fill="none" stroke-width="2"/>'),
    "Shaded": ('<path class="a1" d="M16 2.3 28.7 8.7 16 15 3.3 8.7z"/>'
        '<path class="a2" d="M3 9.6 15.3 15.9V29.7L3 23.2z"/>'
        '<path class="a3" d="M29 9.6 16.7 15.9V29.7L29 23.2z"/>'),
    "UseDefaultMaterial": ('<circle class="g" cx="15" cy="15" r="12"/>'
        '<path class="k" d="M16.00 3.00h3.67v3.67h-3.67zM19.67 6.67h3.67v3.67h-3.67zM16.00 10.34h3.67v3.67h-3.67zM23.34 10.34h3.67v3.67h-3.67zM19.67 14.01h3.67v3.67h-3.67zM16.00 17.68h3.67v3.67h-3.67zM23.34 17.68h3.67v3.67h-3.67zM19.67 21.35h3.67v3.67h-3.67z"/>'),
    "WireFrameOnShaded": ('<path class="a1" d="M16 6.5 24.3 10.6 16 14.7 7.7 10.6z"/>'
        '<path class="a2" d="M6.6 12.3l7.7 3.9v9.7l-7.7-4z"/>'
        '<path class="a3" d="M25.4 12.3l-7.7 3.9v9.7l7.7-4z"/>'
        '<path class="g ln" d="M16 2.6 28.4 9v14L16 29.4 3.6 23V9zM3.6 9 16 15.3 28.4 9M16 15.3v14.1" fill="none" stroke-width="2.3"/>'),
    "Textured": ('<circle class="g" cx="16" cy="16" r="12.3"/>'
        '<path class="k" d="M8.00 4.00h4.00v4.00h-4.00zM16.00 4.00h4.00v4.00h-4.00zM4.00 8.00h4.00v4.00h-4.00zM12.00 8.00h4.00v4.00h-4.00zM20.00 8.00h4.00v4.00h-4.00zM8.00 12.00h4.00v4.00h-4.00zM16.00 12.00h4.00v4.00h-4.00zM24.00 12.00h4.00v4.00h-4.00zM4.00 16.00h4.00v4.00h-4.00zM12.00 16.00h4.00v4.00h-4.00zM20.00 16.00h4.00v4.00h-4.00zM8.00 20.00h4.00v4.00h-4.00zM16.00 20.00h4.00v4.00h-4.00zM24.00 20.00h4.00v4.00h-4.00zM12.00 24.00h4.00v4.00h-4.00zM20.00 24.00h4.00v4.00h-4.00z"/>'),
    "Light": ('<path class="g" d="M16 6.3a6.6 6.6 0 0 1 3.9 11.9c-.8.6-1.2 1.5-1.4 2.5l-.4 2h-4.2l-.4-2c-.2-1-.6-1.9-1.4-2.5A6.6 6.6 0 0 1 16 6.3z"/>'
        '<rect class="g" x="14" y="23.6" width="4" height="2.2" rx=".4"/>'
        '<rect class="g" x="15" y="26.4" width="2" height="1.8" rx=".5"/>'
        '<path class="g ln" d="M16 1v3.6M4 14.2h3.8M24.2 14.2H28M8.2 5.6l2.2 2.2M23.8 5.6l-2.2 2.2" fill="none" stroke-width="2"/>'),
    "Shadows": ('<g class="m">'
        '<path d="M2 21.6c1.4-2.4 6.3-4.2 10.5-4 .9 1.6 2 3 3.5 4.1-.6 2.3-4.1 3.6-8.3 3.4-3.6-.2-6.3-1.6-5.7-3.5z" fill="url(#hatch)"/>'
        '</g><circle class="a" cx="21" cy="15" r="8.6"/>'),
    "SSAO": ('<path class="g" d="M16 2.3a9 9 0 0 1 9 9H7a9 9 0 0 1 9-9z"/>'
        '<path d="M7.1 12.6a9 9 0 0 0 17.8 0z" fill="url(#hatchG)"/>'
        '<path d="M3 22.6 9 19.4l10.7.6 8.6 3-6 5.4H11.7z" fill="url(#hatchA)"/>'),
    "MotionBlur": ('<circle class="m3" cx="10.6" cy="21.8" r="7.3"/>'
        '<circle class="m2" cx="13.4" cy="18.6" r="7.5"/>'
        '<circle class="m1" cx="16.6" cy="15.3" r="7.6"/>'
        '<circle class="g" cx="20.3" cy="11.3" r="7.7"/>'),
    "MultisampleAA": ('<path class="a ln" d="M15 4.6A10.8 10.8 0 0 0 15 26.2" fill="none" stroke-width="3.2"/>'
        '<path class="g" d="M17 3.3h3.7V7H17zM20.7 7h3.6v3.7h-3.6zM24.3 10.7H28v3.6h-3.7zM24.3 14.3H28V18h-3.7zM20.7 18h3.6v3.7h-3.6zM17 21.7h3.7v3.6H17zM17 25.3h3.7V29H17z"/>'),
    "DepthOfField": ('<path d="M4 4h11v11H4z" fill="url(#hatchA)"/>'
        '<path class="halo" stroke-width="2.6" stroke-linejoin="round" d="M12 12h16v15.7H12z"/>'
        '<path class="a" d="M12 12h16v15.7H12z"/>'),
    "IsolateSelected": ('<path class="a" d="M4 4h3.3v2H6v1.3H4zM10 4h4v2h-4zM16.7 4H20.7v3.3h-2V6h-2zM4 10h2v4.3H4zM4 17.3h2v1.4h1.3v2H4zM10 18.7h3.3v2H10z"/>'
        '<path class="halo" stroke-width="2.6" stroke-linejoin="round" d="M19.3 10 29 19.8l-4.4.8 2.9 5.7-1.6.8-2.9-5.7-3.7 3.2z"/>'
        '<path class="g" d="M19.3 10 29 19.8l-4.4.8 2.9 5.7-1.6.8-2.9-5.7-3.7 3.2z"/>'),
    "XRay": ('<path class="g" d="M11 4h17v3.7H11zM24.3 7.7H28v13h-3.7zM11 11h10v9.7H11zM4 11h3.7v16.7H4zM7.7 24H21v3.7H7.7z"/>'),
    "XRayActiveComponents": ('<path class="g" d="M11 4h17v2.3H11zM25.7 6.3H28v14.4h-2.3zM15 18.3h10.7v2.4H15zM11 6.3h2.3V11H11zM15 10h6v6h-6zM4 11h3.7v16.7H4zM7.7 24H21v3.7H7.7z"/>'),
    "XRayJoints": ('<rect class="halo" x="4" y="4" width="24" height="24"/>'
        '<path class="g" fill-rule="evenodd" d="M4 4h24v24H4zm2 2v20h20V6z"/>'
        '<circle class="g" cx="11" cy="11" r="3.1"/>'
        '<path class="g" d="M12.3 13.9 14.6 11.7 23.2 23.7z"/>'),
    "Exposure": ('<circle class="g" cx="16" cy="16" r="12"/><g class="k" id="iris"></g>'),
    "Gamma": ('<path class="g" d="M13 8a9 9 0 0 0 0 18z"/>'
        '<path class="g" d="M14.3 4H27v23.3H14.3a11.7 11.7 0 0 0 0-23.3z"/>'),
}


def gear(cx=10.7, cy=20.2, outer=8.4, inner=6.3, teeth=8):
    """Camera attributes' gear (pure): `teeth` flat teeth round a disc."""
    points = []
    for i in range(teeth):
        a = i / float(teeth) * 2 * math.pi
        for ang, rad in ((a - .39, inner), (a - .21, outer), (a + .21, outer), (a + .39, inner)):
            points.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    return "M" + "L".join("%.2f %.2f" % p for p in points) + "z"


def iris():
    """Exposure's aperture (pure): six blade gaps and a centre, in the face."""
    out = []
    for i in range(6):
        a = i * math.pi / 3

        def at(ang, rad):
            return "%.2f %.2f" % (16 + rad * math.cos(ang), 16 + rad * math.sin(ang))
        out.append('<path d="M%sL%s" stroke-width="1.7" fill="none" class="kl"/>'
                   % (at(a, 4.2), at(a + .2, 13)))
    return "".join(out) + '<circle cx="16" cy="16" r="4.3"/>'


def svg(name, face=FACE, palette=None):
    """`name`'s drawing as a whole SVG in `palette` (ours by default), its
    cut-outs in `face` (pure)."""
    pal = dict(PALETTE)
    pal.update(palette or {})
    body = (ICONS[name]
            .replace('id="gear" d=""', 'd="%s"' % gear())
            .replace('<g class="k" id="iris"></g>', '<g class="k">%s</g>' % iris()))

    def colour(match):
        classes = match.group(1).split()
        main = classes[0]
        if main == "kl":
            return 'stroke="%s"' % face
        if main == "k":
            value = face
        else:
            value = pal.get(main, pal["g"])
        if "ln" in classes:
            return 'stroke="%s"' % value
        if main == "halo":
            return 'fill="%s" stroke="%s"' % (value, value)
        return 'fill="%s"' % value
    body = re.sub(r'class="([^"]+)"', colour, body)
    body = body.replace('<g fill="%s">' % face, '<g fill="%s" stroke="%s">' % (face, face))
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">%s%s</svg>'
            % (DEFS.format(**pal), body))


def halo_of(alpha, radius):
    """Maya's dark ring: `alpha` (an h x w numpy array) grown by `radius` px,
    antialiased at its edge (pure numpy)."""
    import numpy as np
    r = int(math.ceil(radius))
    padded = np.pad(alpha, r)
    out = padded.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            d = math.hypot(dx, dy)
            if d > radius + .5:
                continue
            k = min(1.0, radius + .5 - d)
            out = np.maximum(out, np.roll(np.roll(padded, dy, 0), dx, 1) * k)
    return out[r:-r, r:-r]


def render(name, px, face=FACE, palette=None, halo=True):
    """`name` drawn at px x px with Maya's dark ring under it, as a QImage."""
    import numpy as np
    from PySide6 import QtCore, QtGui, QtSvg
    pal = dict(PALETTE)
    pal.update(palette or {})
    image = QtGui.QImage(px, px, QtGui.QImage.Format_RGBA8888)
    image.fill(QtCore.Qt.transparent)
    renderer = QtSvg.QSvgRenderer(QtCore.QByteArray(svg(name, face, pal).encode("utf-8")))
    painter = QtGui.QPainter(image)
    painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
    renderer.render(painter)
    painter.end()
    if not halo:
        return image
    buf = np.frombuffer(image.constBits(), np.uint8, count=image.sizeInBytes())
    a = buf.reshape(px, image.bytesPerLine())[:, :px * 4].reshape(px, px, 4).astype(np.float32) / 255
    ring = halo_of(a[..., 3], HALO_UNITS * px / 32.0) * HALO_ALPHA
    colour = QtGui.QColor(pal["halo"])
    rgb_h = np.array([colour.redF(), colour.greenF(), colour.blueF()], np.float32)
    al = a[..., 3:4]
    out_a = al + ring[..., None] * (1 - al)
    rgb = (a[..., :3] * al + rgb_h * ring[..., None] * (1 - al)) / np.maximum(out_a, 1e-6)
    data = (np.clip(np.concatenate([rgb, out_a], -1), 0, 1) * 255 + .5).astype(np.uint8).copy()
    return QtGui.QImage(data.data, px, px, px * 4, QtGui.QImage.Format_RGBA8888).copy()
