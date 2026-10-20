"""Maya's status-line tools on the skill bar's page row (2026-10-20): the selection masks of
the current selection mode, Lock / Highlight selection, the five snaps and Make Live, at the
right of F1..F12 (mockup A, https://claude.ai/artifact/1KJ721Rcme6cgJAAqz6xoM).

What each button IS: Maya's own status-line control (`objSelHandleBtn`, `snapGridButton`...) and
the command its changeCommand runs (`setObjectPickMask "Marker" #1`). The state is read off those
controls, which Maya's own permanent scriptJobs keep in step (updateObjectSelectionMasks...), so a
partial mask reads exactly as Maya reckons it; a press runs Maya's command. Without the status
line the masks fall back to the primary `selectType` flags of each group.

Stdlib only (a test pins it): the table, the icons, the layout, `MemoryStatus` for the tests.
The scene half is `statusscene.MayaStatus`.
Spec: docs/superpowers/specs/2026-10-20-skill-bar-status-tools-design.md
"""

OBJECT, COMPONENT, HIERARCHY = "object", "component", "hierarchy"

#  a mask: (key, label, icon, Maya's control, command with #1, the right button's popup group,
#  fallback selectType flags)
MASKS = {
    OBJECT: (
        ("Marker", "Handles", "mHandle", "objSelHandleBtn", 'setObjectPickMask "Marker" #1', "objMarker",
         ("handle", "ikHandle")),
        ("Joint", "Joints", "mJoint", "objSelJointBtn", 'setObjectPickMask "Joint" #1', "objJoint", ("joint",)),
        ("Curve", "Curves", "mCurve", "objSelCurveBtn", 'setObjectPickMask "Curve" #1', "objCurve",
         ("nurbsCurve", "cos", "stroke")),
        ("Surface", "Surfaces", "mSurface", "objSelSurfaceBtn", 'setObjectPickMask "Surface" #1', "objSurface",
         ("polymesh", "plane", "nurbsSurface", "subdiv")),
        ("Deformer", "Deformers", "mDeform", "objSelDeformBtn", 'setObjectPickMask "Deformer" #1', "objDeformer",
         ("lattice", "cluster", "sculpt", "nonlinear")),
        ("Dynamic", "Dynamics", "mDynamic", "objSelDynamicBtn", 'setObjectPickMask "Dynamic" #1', "objDynamic",
         ("particleShape", "emitter", "field", "fluid", "rigidBody", "rigidConstraint")),
        ("Rendering", "Rendering", "mRender", "objSelRenderBtn", 'setObjectPickMask "Rendering" #1', "objRendering",
         ("light", "camera", "texture")),
        ("Other", "Miscellaneous", "mMisc", "objSelMiscBtn", 'setObjectPickMask "Other" #1', "objOther",
         ("locator", "dimension", "ikEndEffector")),
    ),
    COMPONENT: (
        ("Point", "Points", "cPoint", "compSelPointBtn", 'setComponentPickMask "Point" #1', "compPoint",
         ("cv", "polymeshVertex", "latticePoint", "particle")),
        ("ParmPoint", "Parameter points", "cParm", "compSelParmPointBtn", 'setComponentPickMask "ParmPoint" #1',
         "compParmPoint", ("surfaceParameterPoint", "curveParameterPoint")),
        ("Line", "Lines", "cLine", "compSelLineBtn", 'setComponentPickMask "Line" #1', "compLine",
         ("polymeshEdge", "isoparm", "surfaceEdge")),
        ("Facet", "Faces", "cFace", "compSelFaceBtn", 'setComponentPickMask "Facet" #1', "compFacet",
         ("facet", "surfaceFace")),
        ("Hull", "Hulls", "cHull", "compSelHullBtn", 'setComponentPickMask "Hull" #1', "compHull", ("hull",)),
        ("Pivot", "Pivots", "cPivot", "compSelPivotBtn", 'setComponentPickMask "Pivot" #1', "compPivot",
         ("rotatePivot", "scalePivot", "jointPivot")),
        ("Marker", "Handles", "mHandle", "compSelHandleBtn", 'setComponentPickMask "Marker" #1', "compMarker",
         ("selectHandle",)),
        ("Other", "Miscellaneous", "mMisc", "compSelMiscBtn", 'setComponentPickMask "Other" #1', "compOther",
         ("imagePlane", "localRotationAxis")),
    ),
    HIERARCHY: (
        ("root", "Root", "hRoot", "hierRootButton", "setHierSelectMode -root", None, ()),
        ("leaf", "Leaf", "hLeaf", "hierLeafButton", "setHierSelectMode -leaf", None, ()),
        ("template", "Template", "hTemplate", "hierTemplateButton", "setHierSelectMode -template", None, ()),
    ),
}

#  (key, label, icon)
SELECT = (
    ("lock", "Lock current selection", "lock"),
    ("hilite", "Highlight selection mode", "hilite"),
)

#  (key, label, icon, snapMode flag) - Maya's order on the status line is curve, point, grid,
#  view plane, mesh center; the mockup (and the animator's screenshot) put the grid first
SNAPS = (
    ("grid", "Snap to grids", "sGrid", "grid"),
    ("curve", "Snap to curves", "sCurve", "curve"),
    ("point", "Snap to points", "sPoint", "point"),
    ("viewPlane", "Snap to view planes", "sPlane", "viewPlane"),
    ("meshCenter", "Snap to projected center", "sMesh", "meshCenter"),
)

LIVE = ("live", "Make live (right button: add / remove)", "live")

#  the masks' own "all on / all off" (Maya's ObjectMaskPopup / ComponentMaskPopup), a button
#  ahead of the masks (2026-10-20: «кнопочку как в мае Deselect all для типов выделения»):
#  a click turns every type off, or every type on when all are off already
ALL = ("all", "Deselect all types (right button: all on / all off)", "maskAll")
ALL_COMMANDS = {OBJECT: 'setObjectPickMask "All" %d', COMPONENT: 'setComponentPickMask "All" %d'}


def _joined(a, b):
    """Two neighbouring groups that stand together, a gap and no hairline between."""
    return (a, b) in (("snap", "live"), ("all", "mask"))

#  geometry, logical px
BUTTON_W = 20
BUTTON_GAP = 1
DIVIDER_W = 11              # the hairline between groups and its room
END_PAD = 4                 # from the row's right edge
TABS_GAP = 10               # the least room between the F tabs and the tools

_MAGNET = "M3 3v6a5 5 0 0 0 10 0v-6h-3.2v6a1.8 1.8 0 0 1 -3.6 0v-6z"
#  24-grid outline icons, the hub's stroke (maya_hubicons' template)
ICONS = {
    "mHandle": ("M12 4v16M4 12h16", "M9 12a3 3 0 1 0 6 0a3 3 0 1 0 -6 0"),
    "mJoint": ("M4.5 17a2.5 2.5 0 1 0 5 0a2.5 2.5 0 1 0 -5 0", "M14.5 7a2.5 2.5 0 1 0 5 0a2.5 2.5 0 1 0 -5 0",
               "M8.8 15.2l6.4 -6.4"),
    "mCurve": ("M4 18c3 0 4 -3 6 -6s3 -6 6 -6h4",),
    "mSurface": ("M3 13l9 -7l9 5l-9 7z", "M7.5 9.5l9 5", "M12 6v12"),
    "mDeform": ("M4 6a2 2 0 0 1 2 -2h12a2 2 0 0 1 2 2v12a2 2 0 0 1 -2 2h-12a2 2 0 0 1 -2 -2z",
                "M4 9.3h16M4 14.7h16M9.3 4v16M14.7 4v16"),
    "mDynamic": ("M5.4 8a1.6 1.6 0 1 0 3.2 0a1.6 1.6 0 1 0 -3.2 0", "M13.4 6a1.6 1.6 0 1 0 3.2 0a1.6 1.6 0 1 0 -3.2 0",
                 "M10.4 13a1.6 1.6 0 1 0 3.2 0a1.6 1.6 0 1 0 -3.2 0", "M4.4 17a1.6 1.6 0 1 0 3.2 0a1.6 1.6 0 1 0 -3.2 0",
                 "M16.4 15a1.6 1.6 0 1 0 3.2 0a1.6 1.6 0 1 0 -3.2 0"),
    "mRender": ("M4 10.5a1.5 1.5 0 0 1 1.5 -1.5h13a1.5 1.5 0 0 1 1.5 1.5v8a1.5 1.5 0 0 1 -1.5 1.5h-13a1.5 1.5 0 0 1 -1.5 -1.5z",
                "M4 9l2 -5l14 2l-1 3", "M8 5l2 3.5M13 5.5l2 3"),
    "mMisc": ("M9 9a3 3 0 1 1 4 2.8c-.7 .3 -1 .9 -1 1.6v.6", "M12 18v.01"),
    "cPoint": ("M6 7v.01M18 7v.01M6 17v.01M18 17v.01", "M4.5 7a1.5 1.5 0 1 0 3 0a1.5 1.5 0 1 0 -3 0",
               "M16.5 17a1.5 1.5 0 1 0 3 0a1.5 1.5 0 1 0 -3 0"),
    "cParm": ("M3 17c4 -10 14 -10 18 0", "M10 9.6a2 2 0 1 0 4 0a2 2 0 1 0 -4 0"),
    "cLine": ("M5 19L19 5M5 12l7 -7M12 19l7 -7",),
    "cFace": ("M4 7l8 -3l8 3v10l-8 3l-8 -3z", "M4 7l8 3l8 -3M12 10v10"),
    "cHull": ("M4 17l4 -10h8l4 10z", "M6.7 7a1.3 1.3 0 1 0 2.6 0a1.3 1.3 0 1 0 -2.6 0",
              "M14.7 7a1.3 1.3 0 1 0 2.6 0a1.3 1.3 0 1 0 -2.6 0"),
    "cPivot": ("M6 12a6 6 0 1 0 12 0a6 6 0 1 0 -12 0", "M12 3v4M12 17v4M3 12h4M17 12h4"),
    "hRoot": ("M9 4a1 1 0 0 1 1 -1h4a1 1 0 0 1 1 1v3a1 1 0 0 1 -1 1h-4a1 1 0 0 1 -1 -1z",
              "M12 8v4M6 12h12M6 12v4M18 12v4", "M4.4 18a1.6 1.6 0 1 0 3.2 0a1.6 1.6 0 1 0 -3.2 0",
              "M16.4 18a1.6 1.6 0 1 0 3.2 0a1.6 1.6 0 1 0 -3.2 0"),
    "hLeaf": ("M12 3v5M12 8l-6 5M12 8l6 5", "M15 14a1 1 0 0 1 1 -1h4a1 1 0 0 1 1 1v4a1 1 0 0 1 -1 1h-4a1 1 0 0 1 -1 -1z",
              "M4.4 15a1.6 1.6 0 1 0 3.2 0a1.6 1.6 0 1 0 -3.2 0"),
    "hTemplate": ("M4 6v-1a1 1 0 0 1 1 -1h1M10 4h4M18 4h1a1 1 0 0 1 1 1v1M20 10v4M20 18v1a1 1 0 0 1 -1 1h-1M14 20h-4"
                  "M6 20h-1a1 1 0 0 1 -1 -1v-1M4 14v-4", "M9 9h6M9 13h4"),
    "maskAll": ("M4 6v-1a1 1 0 0 1 1 -1h1M10 4h4M18 4h1a1 1 0 0 1 1 1v1M20 10v4M20 18v1a1 1 0 0 1 -1 1h-1"
                "M14 20h-4M6 20h-1a1 1 0 0 1 -1 -1v-1M4 14v-4", "M9 9l6 6M15 9l-6 6"),
    "lock": ("M5 13a2 2 0 0 1 2 -2h10a2 2 0 0 1 2 2v6a2 2 0 0 1 -2 2h-10a2 2 0 0 1 -2 -2z", "M8 11v-3a4 4 0 0 1 8 0v3"),
    "hilite": ("M3 7v-2a2 2 0 0 1 2 -2h2M11 3h2M3 11v2M16 7v2", "M11 11l9 3.5l-4 1.5l-1.5 4z"),
    "sGrid": (_MAGNET, "M13 16h9M13 20h9M16 13v9M20 13v9"),
    "sCurve": (_MAGNET, "M12.5 22c1.5 -5 4.5 -8 9.5 -8.5"),
    "sPoint": (_MAGNET, "M15.5 18.5a3 3 0 1 0 6 0a3 3 0 1 0 -6 0", "M18.5 18.5v.01"),
    "sPlane": (_MAGNET, "M12 21l3.5 -6h8l-3.5 6z"),
    "sMesh": (_MAGNET, "M18 13l4 4.5l-4 4.5l-4 -4.5z", "M18 17.5v.01"),
    "live": (_MAGNET, "M14 18l4 4l4 -4"),
}

_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" '
        'stroke="{colour}" stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round">{paths}</svg>')


def svg(name, colour="#e4e4e6", stroke=1.8):
    """Icon `name` as SVG text (KeyError if unknown)."""
    paths = "".join('<path d="{0}"/>'.format(d) for d in ICONS[name])
    return _SVG.format(colour=colour, stroke="%g" % stroke, paths=paths)


def masks(mode):
    """The mask table of `mode` (Maya's preset mode shows the object masks, as an unknown one)."""
    return MASKS.get(mode, MASKS[OBJECT])


def buttons(mode):
    """[(group, key, label, icon)] left to right; a group change stands a divider between."""
    out = [ALL[:1] + ALL] if mode in ALL_COMMANDS else []
    out += [("mask", m[0], m[1], m[2]) for m in masks(mode)]
    out += [("select", k, label, icon) for k, label, icon in SELECT]
    out += [("snap", k, label, icon) for k, label, icon, _f in SNAPS]
    out.append(("live",) + LIVE)
    return out


def layout(width, mode, ui=1.0):
    """[(group, key, x, w)] in px, packed against the right edge (END_PAD), dividers between groups."""
    items = buttons(mode)
    bw, gap, div = BUTTON_W * ui, BUTTON_GAP * ui, DIVIDER_W * ui
    total = 0.0
    prev = None
    for group, *_rest in items:
        if prev is not None:
            total += div if group != prev and not _joined(prev, group) else gap
        total += bw
        prev = group
    x = width - END_PAD * ui - total
    out, prev = [], None
    for group, key, _label, _icon in items:
        if prev is not None:
            x += div if group != prev and not _joined(prev, group) else gap
        out.append((group, key, x, bw))
        x += bw
        prev = group
    return out


def width_of(mode, ui=1.0):
    """The tools' whole width with their right pad, px."""
    rects = layout(0.0, mode, ui)
    return -rects[0][2] if rects else 0.0


def dividers(rects):
    """The x of the hairline between two groups (the middle of the gap)."""
    out = []
    for a, b in zip(rects, rects[1:]):
        if a[0] != b[0] and not _joined(a[0], b[0]):
            out.append((a[2] + a[3] + b[2]) / 2.0)
    return out


def hit(x, rects):
    """(group, key) of the button under x, or None."""
    for group, key, x0, w in rects:
        if x0 <= x <= x0 + w:
            return group, key
    return None


def mask_state(value, image):
    """A status-line mask control read: "on", "part" (Maya's *Partial.png icon) or ""."""
    if not value:
        return ""
    return "part" if "partial" in (image or "").lower() else "on"


def flags_state(values):
    """A mask from its selectType flags (no status line): all on "on", some "part", none ""."""
    values = [bool(v) for v in values]
    if not values or not any(values):
        return ""
    return "on" if all(values) else "part"


def pressed(command, state):
    """The command a click on a mask runs: Maya's iconTextCheckBox flips its value, and a
    partial one shows as on, so a click on "on" or "part" turns the group off."""
    return command.replace("#1", "0" if state else "1")


def all_command(mode, masks_state):
    """What the all button runs: every type off while any is on, else every type on."""
    command = ALL_COMMANDS.get(mode)
    if command is None:
        return None
    return command % (0 if any(masks_state.values()) else 1)


def all_rows(mode):
    """The all button's right button rows [(label, checked, command)]."""
    command = ALL_COMMANDS.get(mode)
    if command is None:
        return []
    return [("All types on", False, command % 1), ("All types off", False, command % 0)]


def lit(group, key, st):
    """Is the button drawn pressed in state `st` (MayaStatus.read / MemoryStatus.read)?"""
    if group == "all":
        return False                        # an action, never held in
    if group == "mask":
        return bool(st["masks"].get(key))
    if group == "select":
        if key == "lock":
            return bool(st["lock"])
        return not st["hilite"]             # Maya pushes Highlight in while highlighting is OFF
    if group == "snap":
        return bool(st["snaps"].get(key))
    return bool(st.get("live"))


def menu_rows(labels, checks, commands):
    """Maya's popup rows read back as [(label, checked, command)]; a row with no label is left out."""
    out = []
    for label, check, command in zip(labels, checks, commands):
        if label:
            out.append((label, bool(check), command or ""))
    return out


def blank_state(mode=OBJECT):
    return {"mode": mode, "masks": {m[0]: "on" if mode != HIERARCHY or m[0] == "root" else ""
                                    for m in masks(mode)},
            "lock": False, "hilite": True, "snaps": {s[0]: False for s in SNAPS}, "live": False}


class MemoryStatus(object):
    """The tools' model in memory (the strip's tests and a fake link): presses recorded."""

    def __init__(self, mode=OBJECT):
        self.state = blank_state(mode)
        self.log = []

    def read(self):
        return self.state

    def press(self, group, key):
        st = self.state
        self.log.append(("press", group, key))
        if group == "all":
            on = not any(st["masks"].values())
            for k in st["masks"]:
                st["masks"][k] = "on" if on else ""
        elif group == "mask":
            if st["mode"] == HIERARCHY:
                for k in st["masks"]:
                    st["masks"][k] = "on" if k == key else ""
            else:
                st["masks"][key] = "" if st["masks"].get(key) else "on"
        elif group == "select":
            if key == "lock":
                st["lock"] = not st["lock"]
            else:
                st["hilite"] = not st["hilite"]
        elif group == "snap":
            st["snaps"][key] = not st["snaps"][key]
        else:
            st["live"] = not st["live"]
        return st

    def menu(self, group, key):
        self.log.append(("menu", group, key))
        if group == "all":
            return all_rows(self.state["mode"])
        if group == "live":
            return [("Add selection to live", False, "statusLineAddSelToLive"),
                    ("Remove selection from live", False, "statusLineRemoveSelFromLive")]
        if group == "mask" and self.state["mode"] != HIERARCHY:
            return [("Type A", True, "selectType -a #1"), ("Type B", False, "selectType -b #1")]
        return []

    def run(self, command, checked=None):
        self.log.append(("run", command, checked))
