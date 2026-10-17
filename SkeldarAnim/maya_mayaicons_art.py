"""Our drawings of Maya's most visible icons, in the hub's line style
(2026-10-17). Stdlib only.

Each drawing is the body of a 24 x 24 SVG. Its classes are coloured by
`svg(name, ...)`:

    l   a light line (the hub's text)        a   the accent line (orange)
    m   a muted line                         f   a faint fill
    af  an accent fill                       tf  a light fill

`NAMES` is every Maya icon we draw: the hand-made ones in `ART`, the 18 panel
layouts generated from their names (`layout`), and the selection masks'
"Partial" states, which are their mask on a tint (`PARTIAL`).
Spec: docs/superpowers/specs/2026-10-17-maya-icons-design.md
"""

import re

import maya_hubstyle as hubstyle

T = hubstyle.TOKENS
COLOURS = {
    "l": T["text"],
    "a": T["accent"],
    "m": T["muted"],
    "f": T["faint"],
    "af": T["accent"],
    "tf": T["text"],
    "tint": T["accent_tint"],
}
WIDTH = 1.6          # in the 24 grid: 1.33 px at 20 px, 2.1 at 32

#  shared shapes
CUBE = 'M12 3.5l7.5 4.2v8.6L12 20.5l-7.5-4.2V7.7z'
CUBE_IN = 'M4.5 7.7L12 12l7.5-4.3M12 12v8.5'
ARROW = 'M5 3.5l10 6-4.6 1.1 2.7 4.8-1.9 1-2.7-4.8-3.5 2.9z'
CURSOR = 'M13 11.5l7.5 4.5-3.5.8 2 3.6-1.4.8-2-3.6-2.6 2.2z'      # bottom right
MAGNET = 'M3.5 4v5.5a5 5 0 0 0 10 0V4M3.5 6.5h3M10.5 6.5h3'
LINK = ('M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1'
        'M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1')
CAM = 'M3 8h11a1.5 1.5 0 0 1 1.5 1.5v6A1.5 1.5 0 0 1 14 17H3z'
CAM_LENS = 'M15.5 11l5.5-3v9l-5.5-3'
SUN_RAYS = 'M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6l1.4 1.4M17 17l1.4 1.4M5.6 18.4L7 17M17 7l1.4-1.4'
GRAPH = 'M4 4v16h16'
KEY_SQ = 'M{0} {1}h3v3h-3z'      # a key, an accent square 3 x 3


def key(x, y):
    return '<path class="af" d="M{0} {1}h3.2v3.2h-3.2z"/>'.format(x - 1.6,
                                                                  y - 1.6)


def _dashed(cls, extra):
    if extra == DASH:
        return cls + "d", ""
    return cls, extra


def p(cls, d, extra=""):
    cls, extra = _dashed(cls, extra)
    return '<path class="{0}" d="{1}"{2}/>'.format(cls, d, extra)


def c(cls, x, y, r):
    return '<circle class="{0}" cx="{1}" cy="{2}" r="{3}"/>'.format(cls, x, y,
                                                                   r)


def rect(cls, x, y, w, h, r=1.5, extra=""):
    cls, extra = _dashed(cls, extra)
    return ('<rect class="{0}" x="{1}" y="{2}" width="{3}" height="{4}" '
            'rx="{5}"{6}/>').format(cls, x, y, w, h, r, extra)


#  small letters under a tangent's arch, as paths (no font needed)
LETTER = {
    "A": 'M10 18.5l2-5.5 2 5.5M10.7 16.6h2.6',
    "C": 'M14 13.8a2.4 2.6 0 1 0 0 4.4',
    "E": 'M13.9 13h-3.6v5.5h3.6M10.3 15.75h3',
    "M": 'M9.5 18.5V13l2.5 3.2 2.5-3.2v5.5',
}
#  a dashed line: `extra=DASH` turns the class into its dashed twin ("l" ->
#  "ld"). QtSvg drew nothing for a dashed element whose dash came as an
#  attribute or a style beside its class (measured): with either, the class's
#  stroke was dropped. A class of its own draws.
DASH = "dash"


def tangent(curve, keys, cls="l"):
    """A tangent icon: the curve and its keys."""
    return p(cls, curve) + "".join(key(x, y) for x, y in keys)


def infinity(left, offset):
    """pre/postInfinity: the cycle drawn, the copy faint, the side it repeats
    to in accent."""
    a, b = ("f", "a") if not left else ("a", "f")
    dy = 4 if offset else 0
    if left:
        return (p("a", "M2 {0}c2-4 4-4 6 0".format(15 + dy)) +
                p("l", "M8 15c2-4 4-4 6 0s4 4 6 0".format()) +
                key(14, 15) + key(20, 15 - 0))
    return (p("l", "M4 15c2-4 4-4 6 0s4 4 6 0") + key(4, 15) + key(10, 15) +
            p("a", "M16 {0}c2-4 4-4 6 0".format(15 - dy)))


ART = {
    # ------------------------------------------------- the tools and files
    "aselect": p("l", ARROW),
    "lassoSelect": (p("a", 'M4 8c0-2.8 3-4.5 7-4.5s7 1.7 7 4.5-3 4.5-7 4.5'
                         'c-1.3 0-2.5-.2-3.5-.5') +
                    p("l", 'M7.5 12c-1.4.9-1.1 3.3 1 3.3') + p("l", CURSOR)),
    "move_M": (p("l", 'M12 5v14M5 12h14') +
               p("a", 'M9.6 6.9L12 4.5l2.4 2.4M9.6 17.1L12 19.5l2.4-2.4'
                      'M6.9 9.6L4.5 12l2.4 2.4M17.1 9.6l2.4 2.4-2.4 2.4')),
    "rotate_M": (c("l", 12, 12, 3) +
                 p("a", 'M19.5 12a7.5 7.5 0 1 1-2.2-5.3M19.5 4.5v3.4h-3.4')),
    "scale_M": (rect("l", 4, 10, 10, 10) +
                p("a", 'M13 11l7-7M15.5 4H20v4.5')),
    "fileNew": p("l", 'M6 3.5h8l4 4v13H6zM14 3.5v4h4') + p("a", 'M12 11v6M9 14h6'),
    "fileOpen": (p("l", 'M3.5 7.5a2 2 0 0 1 2-2h4l2 2h7a2 2 0 0 1 2 2v1.5') +
                 p("a", 'M3.5 18.5l2.5-7h15l-2.5 7z')),
    "fileSave": (p("l", 'M5 4h11l3 3v13H5zM8 4v5h7V4') +
                 rect("a", 8, 13, 8, 5, 1)),
    "undo_s": p("a", 'M9 14L4 9l5-5') + p("l", 'M4 9h10.5a5.5 5.5 0 0 1 0 11H11'),
    "redo_s": p("a", 'M15 14l5-5-5-5') + p("l", 'M20 9H9.5a5.5 5.5 0 0 0 0 11H13'),
    "lock": rect("l", 5, 10.5, 14, 10, 2) + p("a", 'M8 10.5V8a4 4 0 0 1 8 0v2.5') + c("a", 12, 15.5, 1.2),
    "toolSettings": (p("l", 'M4 6h9M4 12h5M4 18h9M17 6h3M13 12h7M17 18h3') +
                     c("a", 15, 6, 2) + c("a", 11, 12, 2) + c("a", 15, 18, 2)),
    "attributes": (p("l", 'M4 6h16M4 12h16M4 18h16') +
                   rect("a", 13, 4, 4, 4, 1) + rect("a", 7, 10, 4, 4, 1) +
                   rect("a", 14, 16, 4, 4, 1)),
    "channelBox": (rect("l", 4, 4, 16, 16, 2) +
                   p("l", 'M7.5 8.5h3M7.5 12h3M7.5 15.5h3') +
                   p("a", 'M13 8.5h3.5M13 12h3.5M13 15.5h3.5')),
    "layerEditor": (p("l", 'M12 13.5l8-4-8-4-8 4z') +
                    p("a", 'M4 13.5l8 4 8-4') + p("m", 'M4 17.5l8 4 8-4')),
    "channelLayers": (p("l", 'M12 12l8-4-8-4-8 4z') + p("a", 'M4 12l8 4 8-4') +
                      p("m", 'M4 16l8 4 8-4')),
    "outliner": (p("l", 'M4 5h5M8 11h6M8 17h6M5.5 5v12h2.5') +
                 rect("a", 15.5, 9, 4, 4, 1) + rect("l", 15.5, 15, 4, 4, 1) +
                 rect("a", 10, 3, 4, 4, 1)),
    "constructionHistory": (c("l", 9, 9, 5.5) + p("a", 'M9 6v3l2 2') +
                            p("l", 'M14 17h6M14 20h6M4 17h6M4 20h6')),
    "Bookmark": p("l", 'M7 3.5h10v17l-5-4-5 4z') + p("a", 'M10 9h4'),
    "highlightSelect": (rect("l", 4, 4, 11, 11, 1.5, DASH) +
                        rect("af", 7, 7, 5, 5, 1) + p("l", CURSOR)),
    "closeBar": p("l", 'M14 6l-6 6 6 6'),
    "openBar": p("l", 'M10 6l6 6-6 6'),
    "inArrow": rect("l", 9, 5, 11, 14, 2) + p("a", 'M3 12h9M9 9l3 3-3 3'),
    "outArrow": rect("l", 4, 5, 11, 14, 2) + p("a", 'M12 12h9M18 9l3 3-3 3'),
    "pause_S": p("a", 'M8.5 5v14M15.5 5v14'),
    "stacked": (p("l", GRAPH) + p("a", 'M5 9.5c4-3 9-3 14 0') +
                p("l", 'M5 14c4-2.5 9-2.5 14 0') + p("m", 'M5 18c4-2 9-2 14 0')),
    "absolute": rect("l", 4, 4, 16, 16, 2) + c("a", 12, 12, 2.5) + p("l", 'M12 4v5.5M12 14.5V20M4 12h5.5M14.5 12H20'),
    "relative": (rect("l", 4, 4, 16, 16, 2) + c("l", 9, 10, 2) +
                 p("a", 'M11 12l4 4M15 12.5V16h-3.5') + p("l", 'M14 7h3M15.5 5.5v3')),
    # --------------------------------------------- the status line's masks
    "selectObj": (rect("af", 4, 4, 7, 7, 1.5) + rect("l", 13, 13, 7, 7, 1.5) +
                  p("l", 'M7.5 11v5.5H13')),
    "selectComp": (rect("l", 4, 4, 7, 7, 1.5) + rect("af", 13, 13, 7, 7, 1.5) +
                   p("l", 'M7.5 11v5.5H13')),
    "pickHierarchy": (rect("a", 4, 4, 7, 5, 1) + rect("l", 13, 15, 7, 5, 1) +
                      p("l", 'M7.5 9v8.5H13')),
    "pickObjByType": (p("a", CUBE) + p("a", CUBE_IN)),
    "pickCompByType": (p("l", CUBE) + c("af", 12, 3.5, 1.8) + c("af", 19.5, 7.7, 1.8) +
                       c("af", 4.5, 16.3, 1.8)),
    "pickHandlesObj": p("a", 'M12 4v16M4 12h16') + c("l", 12, 12, 2),
    "pickHandlesComp": p("l", 'M12 4v16M4 12h16') + c("a", 12, 12, 2),
    "pickJointObj": c("a", 6.5, 17.5, 2.5) + c("l", 17.5, 6.5, 2.5) + p("l", 'M8.3 15.7l7.4-7.4'),
    "pickCurveObj": p("a", 'M4 17c3-9 6-9 8-5s5 4 8-5') + c("l", 4, 17, 1.4) + c("l", 20, 7, 1.4),
    "pickGeometryObj": p("l", CUBE) + p("l", CUBE_IN) + p("af", 'M12 12l7.5-4.3v8.6L12 20.5z'),
    "pickDeformerObj": (rect("l", 4, 4, 16, 16, 2, DASH) +
                        p("a", 'M8 16c0-5 8-3 8-8M8 8c2 0 3 1 4 4s2 4 4 4')),
    "pickDynamicsObj": (c("af", 7, 8, 1.8) + c("af", 14, 6, 1.4) + c("af", 17, 13, 2) +
                        c("af", 9, 16, 1.4) + c("l", 12, 11.5, 1) + p("m", 'M4 20h16')),
    "pickRenderingObj": (rect("l", 4, 7, 16, 12, 2) + p("l", 'M4 10.5h16M8 7l-1.5 3.5M13 7l-1.5 3.5M18 7l-1.5 3.5') +
                         c("af", 9, 15, 2)),
    "pickOtherObj": (p("a", 'M9 9a3 3 0 1 1 4.5 2.6c-1 .6-1.5 1.3-1.5 2.4') +
                     c("af", 12, 18, 1.2)),
    "pickOtherComp": (p("l", 'M9 9a3 3 0 1 1 4.5 2.6c-1 .6-1.5 1.3-1.5 2.4') +
                      c("af", 12, 18, 1.2)),
    "pickPointComp": c("l", 12, 12, 5) + c("af", 12, 12, 2),
    "pickPointComp2": rect("l", 6.5, 6.5, 11, 11, 2) + rect("af", 10, 10, 4, 4, 1),
    "pickLineComp": p("a", 'M5 19L19 5') + c("l", 5, 19, 1.5) + c("l", 19, 5, 1.5),
    "pickFacetComp": (rect("l", 4, 4, 16, 16, 2) + p("l", 'M12 4v16M4 12h16') +
                      rect("af", 13.5, 13.5, 5, 5, 1)),
    "pickHullComp": (p("m", 'M4 18L9 6l6 8 5-9', DASH) + c("af", 4, 18, 1.6) + c("af", 9, 6, 1.6) +
                     c("af", 15, 14, 1.6) + c("af", 20, 5, 1.6)),
    "pickPivotComp": c("l", 12, 12, 6) + c("a", 12, 12, 2.4) + p("l", 'M12 3v3M12 18v3M3 12h3M18 12h3'),
    "pickTemplate": p("m", CUBE, DASH) + p("m", CUBE_IN, DASH),
    # ------------------------------------------------------- the snaps
    "snapGrid": p("l", 'M4 9h16M4 15h16M9 4v16M15 4v16') + c("af", 15, 9, 2.2),
    "snapCurve": p("l", 'M4 18c3-9 9-12 16-12') + c("af", 11.2, 10, 2.2),
    "snapPoint": p("m", 'M5 19L19 5M5 5l14 14', DASH) + c("af", 12, 12, 2.6),
    "snapPlane": p("l", 'M3.5 15l5-6h12l-5 6z') + p("a", 'M12 3v8M9.5 8.5L12 11l2.5-2.5'),
    "snapMeshCenter": p("l", CUBE) + c("af", 12, 12, 2.2),
    "snapTime": p("l", MAGNET) + p("a", 'M13 20h8M15 17v3M18 17v3M21 17v3'),
    "snapValue": p("l", MAGNET) + p("a", 'M20 12v9M17 13.5h3M17 17h3M17 20.5h3'),
    "isolateCurve": p("m", 'M3 15c3-5 5 3 8-2s6 2 10-4', DASH) + p("a", 'M3 10c4-6 8 4 11-1s5-3 7-1'),
    # ------------------------------------------------------- the viewport
    "Camera": p("l", CAM) + p("a", CAM_LENS),
    "CameraAE": p("l", CAM) + p("a", CAM_LENS) + p("af", 'M6 11.5h2v2H6z'),
    "CameraLock": p("l", CAM) + p("a", CAM_LENS) + rect("af", 6, 11.5, 5, 4, 1) + p("l", 'M7 11.5v-1a1.5 1.5 0 0 1 3 0v1'),
    "IsolateSelected": rect("l", 4, 4, 16, 16, 2, DASH) + rect("a", 8.5, 8.5, 7, 7, 1),
    "WireFrame": (p("l", CUBE) + p("l", CUBE_IN) +
                  p("l", 'M4.5 16.3L12 12l7.5 4.3M12 3.5V12')),
    "Shaded": p("f", 'M12 12l7.5-4.3v8.6L12 20.5z') + p("l", CUBE) + p("l", CUBE_IN),
    "WireFrameOnShaded": (p("f", 'M12 12l7.5-4.3v8.6L12 20.5z') + p("l", CUBE) + p("a", CUBE_IN) +
                          p("a", 'M4.5 16.3L12 12l7.5 4.3M12 3.5V12')),
    "Textured": (p("l", CUBE) + p("l", CUBE_IN) +
                 p("a", 'M6.5 11.2l3.5 2M6.5 14.4l3.5 2M15.5 13.5l2-1.2v2.6l-2 1.2z')),
    "UseDefaultMaterial": c("l", 12, 12, 7.5) + p("f", 'M12 4.5a7.5 7.5 0 0 1 0 15z') + c("a", 9, 9, 1.4),
    "Light": c("a", 12, 10, 4) + p("l", 'M10 17h4M10.5 20h3M12 14v3') + p("m", 'M12 2.5v1.5M5 10H3.5M20.5 10H19M6.7 4.7l1 1M17.3 4.7l-1 1'),
    "Shadows": c("a", 9, 9, 4.5) + p("f", 'M5 19.5c2-3 8-4 15-2l-1 2.5z') + p("l", 'M4 20h16'),
    "SSAO": p("l", CUBE) + p("l", CUBE_IN) + p("a", 'M4.5 16.3L12 20.5M12 20.5l7.5-4.2'),
    "MotionBlur": c("a", 15, 12, 4.5) + p("m", 'M3 9h7M2 12h7M3 15h7'),
    "MultisampleAA": p("l", 'M4 18L18 4') + p("a", 'M5.5 19.5L19.5 5.5M4 16.5L16.5 4', ' stroke-opacity=".55"'),
    "DepthOfField": c("m", 7, 15, 3) + c("a", 12, 12, 3.5) + c("m", 17, 8, 2),
    "XRay": rect("l", 4, 4, 11, 11, 1.5) + rect("a", 9, 9, 11, 11, 1.5, ' fill-opacity=".25"') ,
    "XRayActiveComponents": rect("l", 4, 4, 16, 16, 2) + rect("af", 10, 10, 7, 7, 1, ' fill-opacity=".6"') + c("l", 7.5, 7.5, 1.3),
    "XRayJoints": rect("l", 4, 4, 16, 16, 2) + c("a", 8.5, 15.5, 1.8) + c("a", 15.5, 8.5, 1.8) + p("a", 'M10 14l4-4'),
    "Grid": rect("l", 4, 4, 16, 16, 1.5) + p("m", 'M9.3 4v16M14.7 4v16M4 9.3h16M4 14.7h16'),
    "ImagePlane": p("l", 'M5 7l12-3v13L5 20z') + p("a", 'M7.5 15l3-3.5 2 2 2-2.5') + c("a", 13, 8.5, 1.2),
    "FilmGate": rect("l", 3, 5, 18, 14, 1.5) + p("m", 'M3 8.5h18M3 15.5h18M6 5v3.5M10 5v3.5M14 5v3.5M18 5v3.5M6 15.5V19M10 15.5V19M14 15.5V19M18 15.5V19') + rect("a", 6, 10, 12, 4, 1),
    "ResolutionGate": rect("l", 3, 5, 18, 14, 1.5) + rect("a", 6.5, 8, 11, 8, 1),
    "GateMask": rect("f", 3, 5, 18, 14, 1.5) + rect("l", 3, 5, 18, 14, 1.5) + rect("a", 6.5, 8, 11, 8, 1, ' fill="#1f2023"'),
    "FieldChart": rect("l", 3, 5, 18, 14, 1.5) + p("m", 'M12 5v14M3 12h18') + c("a", 12, 12, 4),
    "SafeAction": rect("l", 3, 5, 18, 14, 1.5) + rect("a", 5.5, 7.5, 13, 9, 1, DASH),
    "SafeTitle": rect("l", 3, 5, 18, 14, 1.5) + p("a", 'M8.5 9h7M12 9v6.5'),
    "PanZoom": c("l", 10, 10, 5) + p("l", 'M14 14l5.5 5.5') + p("a", 'M10 7.5v5M7.5 10h5'),
    # --------------------------------------------------- the Graph Editor
    #  the four auto tangents differ by their letter, as Maya's do
    "autoTangent": tangent('M3 19c4 0 4-12 9-12s5 12 9 12', [(12, 7)]) + p("l", LETTER["A"]),
    "autocustomTangent": tangent('M3 19c4 0 4-12 9-12s5 12 9 12', [(12, 7)]) + p("l", LETTER["C"]),
    "autoeaseTangent": tangent('M3 19c6 0 4-12 9-12s3 12 9 12', [(12, 7)]) + p("l", LETTER["E"]),
    "automixTangent": tangent('M3 19c4 0 4-12 9-12s5 12 9 12', [(12, 7)]) + p("l", LETTER["M"]),
    "splineTangent": tangent('M3 18c5 0 4-12 9-12s4 12 9 12', [(12, 6)]),
    "linearTangent": tangent('M4 18l8-12 8 12', [(12, 6)]),
    "linearTangentOut": tangent('M4 16c4 0 5-10 8-10l8 12', [(12, 6)]),
    "clampedTangent": tangent('M4 17h4c3 0 3-10 6-10h6', [(8, 17), (14, 7)]),
    "clampedTangentIn": tangent('M4 17h4c3 0 3-10 6-10h6', [(8, 17), (14, 7)]) + p("m", 'M17 10l3-3'),
    "flatTangent": tangent('M3 18c4 0 4-12 9-12s5 12 9 12', [(12, 6)]) + p("a", 'M6 6h12'),
    "stepTangent": tangent('M4 17h8V7h8', [(4, 17), (12, 7)]),
    "plateauTangent": tangent('M4 17c3 0 3-10 6-10h4c3 0 3 10 6 10', [(10, 7), (14, 7)]),
    "breakTangent": tangent('M4 9l8 8 8-11', [(12, 17)]),
    "unifyTangent": tangent('M4 15l16-6', [(12, 12)]),
    "lockTangentWeight": tangent('M4 15l8-5', [(12, 10)]) + rect("l", 14, 12.5, 6, 5, 1) + p("l", 'M15.5 12.5v-1a1.5 1.5 0 0 1 3 0v1'),
    "freeTangentWeight": tangent('M4 15l8-5', [(12, 10)]) + rect("l", 14, 12.5, 6, 5, 1) + p("l", 'M15.5 12.5v-1a1.5 1.5 0 0 1 3 -.5'),
    "normalize": p("l", GRAPH) + p("a", 'M6 17l12-10') + p("m", 'M4 7h16M4 17h16', DASH),
    "reNormalize": p("l", GRAPH) + p("a", 'M6 17l12-10') + p("l", 'M14 4.5a3.5 3.5 0 1 1-2 6.3') + p("l", 'M14 2.5v2h2'),
    "absoluteView": p("l", GRAPH) + p("a", 'M6 16c4-8 8 2 12-9'),
    "bufferSnap": p("m", 'M4 15c4-6 8 2 16-4', DASH) + p("a", 'M4 11c4-6 8 2 16-4') + p("l", 'M12 18v-6M10 14l2-2 2 2'),
    "bufferSwap": p("m", 'M4 16c4-6 8 2 16-4', DASH) + p("a", 'M4 10c4-6 8 2 16-4') + p("l", 'M7 13v6M5 17l2 2 2-2M17 19v-6M15 15l2-2 2 2'),
    "centerCurrentTime": p("a", 'M12 3v18') + p("l", 'M3 7v10M21 7v10M3 12h5M16 12h5'),
    "traxFrameAll": rect("a", 4, 6, 16, 12, 1.5) + p("l", 'M7 9v6M17 9v6'),
    "traxFrameRange": p("l", 'M4 6h3M4 18h3M4 6v12M20 6h-3M20 18h-3M20 6v12') + rect("af", 9, 9, 6, 6, 1),
    "constrainDragX": p("l", 'M4 12h16M7 9l-3 3 3 3M17 9l3 3-3 3') + rect("af", 10, 10, 4, 4, 1),
    "constrainDragY": p("l", 'M12 4v16M9 7l3-3 3 3M9 17l3 3 3-3') + rect("af", 10, 10, 4, 4, 1),
    "unconstrainedDrag": p("l", 'M12 4v16M4 12h16M9.5 6.5L12 4l2.5 2.5M9.5 17.5L12 20l2.5-2.5M6.5 9.5L4 12l2.5 2.5M17.5 9.5L20 12l-2.5 2.5') + rect("af", 10, 10, 4, 4, 1),
    "postInfinityCycle": infinity(False, False),
    "postInfinityCycleOffset": infinity(False, True),
    "preInfinityCycle": infinity(True, False),
    "preInfinityCycleOffset": infinity(True, True),
    "brushGrab": p("l", 'M4 18c4-10 12-10 16 0') + p("a", 'M12 7V3M10 5l2-2 2 2') + key(12, 10),
    "brushSmooth": p("m", 'M4 15l3-4 3 5 4-6 3 4 3-2', DASH) + p("a", 'M4 15c5-5 11-5 16 0'),
    "brushSmear": p("l", 'M4 17c4-8 12-8 16 0') + p("a", 'M7 9h10M14 6l3 3-3 3'),
    "brushKeyReducer": p("l", 'M4 18c4-10 12-10 16 0') + key(8, 12) + p("m", 'M14 6l4 4M18 6l-4 4'),
    "directKeySmall": p("l", 'M4 16c4 0 6-8 10-8h6') + key(14, 8) + p("a", 'M14 8V3M12 5l2-2 2 2'),
    "setKeySmall": p("l", 'M4 4v16') + key(12, 12) + p("a", 'M16 6v12'),
    "regionSelectKeySmall": rect("a", 4, 5, 16, 14, 1.5, DASH) + key(9, 13) + key(15, 10),
    "retimeKeySmall": p("a", 'M6 4v16M18 4v16') + p("l", 'M9 12h6M9 12l2-2M9 12l2 2M15 12l-2-2M15 12l-2 2'),
    "latticeDeformKeySmall": (p("m", 'M4 8h16M4 16h16M8 4v16M16 4v16') + c("af", 8, 8, 1.6) + c("af", 16, 8, 1.6) +
                              c("af", 8, 16, 1.6) + c("af", 16, 16, 1.6)),
    "menuIconAnimCurves": p("l", GRAPH) + p("a", 'M5 16c4-9 9 2 13-8'),
    "menuIconEdit": p("l", 'M5 19h4l10-10-4-4L5 15z') + p("a", 'M13 7l4 4'),
    "menuIconKeys": p("l", 'M4 12h16') + key(7, 12) + key(13, 12) + key(19, 12),
    "menuIconOptions": p("l", 'M4 7h6M4 17h6') + rect("l", 13, 4, 7, 6, 1.5) + rect("af", 13, 14, 7, 6, 1.5),
    "menuIconSelect": p("a", ARROW),
    "menuIconTangents": tangent('M4 18c4 0 4-12 8-12s4 12 8 12', [(12, 6)]) + p("a", 'M7 6h10'),
    "menuIconView": c("l", 12, 12, 3) + p("l", 'M3 12s3.5-6.5 9-6.5 9 6.5 9 6.5-3.5 6.5-9 6.5S3 12 3 12z'),
    # ----------------------------------------------- the Outliner's nodes
    "out_transform": p("l", 'M5 19V8M5 19h11') + p("a", 'M5 19l9-9M10.5 10H14v3.5'),
    "out_joint": c("a", 7, 7, 3) + c("l", 17, 17, 2.2) + p("l", 'M9.2 9.2l5.9 5.9'),
    "out_mesh": p("l", 'M4 6l8-2 8 2v12l-8 2-8-2zM4 6l8 3 8-3M12 9v11M4 12l8 3 8-3'),
    "out_camera": p("l", CAM) + p("a", CAM_LENS) + c("l", 6.5, 5.5, 1.5) + c("l", 11, 5.5, 1.5),
    "out_locator": p("a", 'M12 3v18M3 12h18M6 6l12 12M18 6L6 18'),
    "out_nurbsCurve": p("a", 'M4 18c2-9 5-12 8-6s6 3 8-6') + c("l", 4, 18, 1.3) + c("l", 20, 6, 1.3),
    "out_parentConstraint": p("a", LINK),
    "out_orientConstraint": p("a", LINK) + p("l", 'M3 21a4 4 0 0 1 4-4'),
    "out_pointConstraint": p("a", LINK) + c("af", 4.5, 19.5, 1.5),
    "out_aimConstraint": p("a", LINK) + p("l", 'M2.5 21.5l3-3M3 18.5h2.5V21'),
    "out_scaleConstraint": p("a", LINK) + rect("l", 2.5, 17, 4.5, 4.5, 1),
    "out_poleVectorConstraint": p("a", LINK) + p("l", 'M4.8 21.5V16.5M3 18.3l1.8-1.8 1.8 1.8'),
    "out_ikHandle": c("l", 6, 6, 2) + c("l", 15, 9, 2) + p("l", 'M7.8 6.7l5.4 1.6') + p("a", 'M15 11v9M12 17l3 3 3-3'),
    "out_objectSet": c("l", 12, 12, 8) + c("af", 9, 10, 1.6) + c("af", 14.5, 9, 1.6) + c("af", 12, 15, 1.6),
    "out_displayLayer": p("l", 'M12 12l8-4-8-4-8 4z') + p("a", 'M4 12l8 4 8-4') + p("m", 'M4 16l8 4 8-4'),
    "out_animLayer": p("l", 'M12 12l8-4-8-4-8 4z') + p("a", 'M4 12l8 4 8-4') + p("m", 'M4 16l8 4 8-4') + key(12, 8),
    "out_directionalLight": p("a", 'M5 5l11 11M9 5l11 11M5 9l11 11') + p("l", 'M16 12v4h-4M20 16v4h-4'),
    "out_spotLight": p("l", 'M5 4l5 5-3 3-5-5z') + p("a", 'M10 12l4 8M12 9l8 4M14 20c2 0 6-4 6-7'),
    "out_pointLight": c("af", 12, 12, 3.5) + p("a", SUN_RAYS),
    "out_ambientLight": c("af", 12, 12, 3.5) + c("l", 12, 12, 7.5, ) + p("m", SUN_RAYS),
    "out_animCurveTA": p("l", GRAPH) + p("a", 'M6 16c3-8 6 0 12-9') + p("m", 'M14 18a3 3 0 1 0 3-3'),
    "out_animCurveTL": p("l", GRAPH) + p("a", 'M6 16c3-8 6 0 12-9') + p("m", 'M14 18h5M17 16l2 2-2 2'),
    "out_animCurveTU": p("l", GRAPH) + p("a", 'M6 16c3-8 6 0 12-9') + p("m", 'M15 15v3a2 2 0 0 0 4 0v-3'),
    "out_character": c("a", 12, 5, 2) + p("l", 'M5 9h14M12 9v5M12 14l-4 6M12 14l4 6'),
    "out_clusterHandle": c("l", 12, 12, 7.5, ) + p("a", 'M12 6v12M6 12h12') + c("af", 12, 12, 1.6),
    "out_lattice": (p("l", 'M5 7l7-3 7 3v10l-7 3-7-3zM5 7l7 3 7-3M12 10v10') +
                    p("m", 'M5 12l7 3 7-3M8.5 5.5v13M15.5 5.5v13')),
}

#  the selection masks' "Partial" states: the mask on a tint
PARTIAL = dict((name + "Partial", name) for name in (
    "pickCurveObj", "pickDeformerObj", "pickDynamicsObj", "pickFacetComp",
    "pickGeometryObj", "pickHandlesObj", "pickJointObj", "pickLineComp",
    "pickOtherComp", "pickOtherObj", "pickPivotComp", "pickPointComp2",
    "pickPointComp", "pickRenderingObj"))

LAYOUTS = (
    "defaultSingleLayout", "defaultTwoSideBySideLayout",
    "defaultTwoStackedLayout", "defaultThreeSideBySideLayout",
    "defaultThreeStackedLayout", "defaultThreeSplitTopLayout",
    "defaultThreeSplitBottomLayout", "defaultThreeSplitLeftLayout",
    "defaultThreeSplitRightLayout", "defaultFourQuadLayout",
    "defaultFourSideBySideLayout", "defaultFourStackedLayout",
    "defaultFourSplitTopLayout", "defaultFourSplitBottomLayout",
    "defaultFourSplitLeftLayout", "defaultFourSplitRightLayout")

_COUNT = {"Single": 1, "Two": 2, "Three": 3, "Four": 4}


def layout_panels(name):
    """The panels of a layout icon, (x, y, w, h) in the 24 grid; the first is
    the big one of a split. Parsed from Maya's name."""
    m = re.match(r"default(Single|Two|Three|Four)(SideBySide|Stacked|Quad|"
                 r"Split(Top|Bottom|Left|Right))?Layout$", name)
    if not m:
        raise ValueError(name)
    n = _COUNT[m.group(1)]
    kind = m.group(2) or ""
    x0, y0, w, h, g = 3.5, 4.5, 17.0, 15.0, 1.5
    if n == 1:
        return [(x0, y0, w, h)]
    if kind == "SideBySide":
        cw = (w - g * (n - 1)) / n
        return [(x0 + i * (cw + g), y0, cw, h) for i in range(n)]
    if kind == "Stacked":
        ch = (h - g * (n - 1)) / n
        return [(x0, y0 + i * (ch + g), w, ch) for i in range(n)]
    if kind == "Quad":
        cw, ch = (w - g) / 2, (h - g) / 2
        return [(x0 + i * (cw + g), y0 + j * (ch + g), cw, ch)
                for j in range(2) for i in range(2)]
    side = m.group(3)
    rest = n - 1
    if side in ("Top", "Bottom"):
        big_h = (h - g) * 0.55
        small_h = h - g - big_h
        cw = (w - g * (rest - 1)) / rest
        if side == "Top":
            big, row_y = (x0, y0, w, big_h), y0 + big_h + g
        else:
            big, row_y = (x0, y0 + small_h + g, w, big_h), y0
        return [big] + [(x0 + i * (cw + g), row_y, cw, small_h)
                        for i in range(rest)]
    big_w = (w - g) * 0.55
    small_w = w - g - big_w
    ch = (h - g * (rest - 1)) / rest
    if side == "Left":
        big, col_x = (x0, y0, big_w, h), x0 + big_w + g
    else:
        big, col_x = (x0 + small_w + g, y0, big_w, h), x0
    return [big] + [(col_x, y0 + i * (ch + g), small_w, ch)
                    for i in range(rest)]


def layout(name):
    panels = layout_panels(name)
    out = []
    for i, (x, y, w, h) in enumerate(panels):
        cls = "a" if (i == 0 and len(panels) > 1) else "l"
        out.append(rect(cls, round(x, 2), round(y, 2), round(w, 2),
                        round(h, 2), 1.2))
    return "".join(out)


def body(name):
    """The SVG body of `name` (no extension)."""
    if name in ART:
        return ART[name]
    if name in PARTIAL:
        return rect("tint", 1, 1, 22, 22, 4) + ART[PARTIAL[name]]
    if name in LAYOUTS:
        return layout(name)
    raise KeyError(name)


NAMES = tuple(sorted(set(ART) | set(PARTIAL) | set(LAYOUTS)))


def svg(name, colours=None):
    """A whole SVG of `name`, its classes coloured (COLOURS by default)."""
    col = dict(COLOURS)
    col.update(colours or {})
    style = (".l,.a,.m,.ld,.ad,.md{{fill:none;stroke-width:{w};"
             "stroke-linecap:round;stroke-linejoin:round}}"
             ".ld,.ad,.md{{stroke-dasharray:2.2,2.2}}"
             ".l,.ld{{stroke:{l}}}.a,.ad{{stroke:{a}}}.m,.md{{stroke:{m}}}"
             ".f{{fill:{f};stroke:none}}.af{{fill:{af};stroke:none}}"
             ".tf{{fill:{tf};stroke:none}}.tint{{fill:{tint};stroke:none}}"
             ).format(w=WIDTH, **col)
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
            '<style>{0}</style>{1}</svg>').format(style, body(name))
