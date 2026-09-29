"""Where a weapon dragged out of the inventory lands: a hand, or the floor.

2026-09-29, the weapon inventory. Read once when a drag starts - the camera
and the time cannot move while the mouse is ours - every character's joints
in world space, its bones as parent->child segments, its two hands (the drive
bones' parents) and its root; per move they are projected through the model
panel under the cursor.

A character whose nearest bone on screen is within R = max(radius_min, 8 % of
its projected height) is under the cursor, and the hand nearer the cursor is
the target (ties go to the character nearer the camera). Otherwise the camera
ray through the cursor meets the floor (Y = 0) in front of the camera, and the
character standing nearest to that point owns the weapon. Bones, not meshes:
every character has them, a bare skeleton included, and a drag must not pay
for a ray against 70 000 skinned vertices on every move.

The choice is pure (`choose`, `floor_hit`, `owner`); the scene half imports
Maya and Qt inside its functions, so the pure half is tested with neither.
"""

import math
from collections import namedtuple

# A character on screen: its bones as ((x, y), (x, y)) port-space segments,
# {"R": (x, y) | None, "L": ...} for its hands, its distance to the camera.
Figure = namedtuple("Figure", "key segments hands depth")
HEIGHT_SHARE = 0.08
DOT = "·"
SIDE_LABEL = {"R": "right hand", "L": "left hand"}


# ------------------------------------------------------------------- pure

def seg_distance(p, a, b):
    """The distance from point `p` to the segment a-b. Pure."""
    ax, ay = a
    dx, dy = b[0] - ax, b[1] - ay
    length2 = dx * dx + dy * dy
    if length2 < 1e-12:
        t = 0.0
    else:
        t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / length2))
    return math.hypot(p[0] - (ax + t * dx), p[1] - (ay + t * dy))


def _height(segments):
    ys = [y for segment in segments for _x, y in segment]
    return (max(ys) - min(ys)) if ys else 0.0


def choose(point, figures, radius_min):
    """("hand", key, side) for the figure under `point`, else None. Pure."""
    best = None
    for fig in figures:
        if not fig.segments or not any(fig.hands.values()):
            continue
        radius = max(radius_min, HEIGHT_SHARE * _height(fig.segments))
        near = min(seg_distance(point, a, b) for a, b in fig.segments)
        if near > radius:
            continue
        score = (near / radius, fig.depth)
        if best is None or score < best[0]:
            best = (score, fig)
    if best is None:
        return None
    fig = best[1]
    side = min((s for s in ("R", "L") if fig.hands.get(s)),
               key=lambda s: math.hypot(point[0] - fig.hands[s][0],
                                        point[1] - fig.hands[s][1]))
    return ("hand", fig.key, side)


def floor_hit(near, far, height=0.0):
    """Where the ray near -> far meets Y = `height` beyond `near`, or None."""
    dy = far[1] - near[1]
    if abs(dy) < 1e-12:
        return None
    t = (height - near[1]) / dy
    if t <= 0.0:
        return None
    return tuple(near[i] + t * (far[i] - near[i]) for i in range(3))


def owner(point, roots):
    """The key whose root stands nearest `point` on the floor, or None."""
    if not roots:
        return None
    return min(roots, key=lambda k: math.hypot(point[0] - roots[k][0],
                                                point[2] - roots[k][2]))


def hand_text(label, side):
    return "%s %s %s" % (label, DOT, SIDE_LABEL[side])


def floor_text(label, bone):
    return "floor %s %s %s %s" % (DOT, label, DOT, bone)


# ------------------------------------------------------------------ scene

def characters():
    """(root, label) of every character: the rigs' game skeletons, then the
    bare skeletons (the Weapons section's own reading of "a character")."""
    import maya_rigs
    from maya_overrig import builder
    from maya_scenesetup import equip
    rigs = maya_rigs.rigs()
    roots = [rig.skeleton_root for rig in rigs if rig.skeleton_root]
    for root in builder.character_roots():
        if root not in roots and not any(maya_rigs.under(root, rig.group)
                                         for rig in rigs if rig.group):
            roots.append(root)
    return [(root, equip.character_name(root)) for root in roots]


def snapshot():
    """Every character read once, in world space, for one drag."""
    import maya.cmds as cmds
    from maya_scenesetup import catalog
    from maya_scenesetup import equip
    out = []
    for root, label in characters():
        joints = [root] + (cmds.listRelatives(root, allDescendents=True,
                                              type="joint", fullPath=True) or [])
        points = dict((j, tuple(cmds.xform(j, query=True, worldSpace=True,
                                           translation=True)))
                      for j in joints)
        segments = []
        for joint in joints:
            parent = (cmds.listRelatives(joint, parent=True, fullPath=True)
                      or [None])[0]
            if parent in points:
                segments.append((parent, joint))
        hands, taken = {}, {}
        for side in catalog.SIDES:
            hand, _bone = equip.bones(root, side)
            hands[side] = hand if hand in points else None
            taken[side] = bool(equip.occupant(root, side)[0])
        out.append(dict(key=root, label=label, points=points,
                        segments=segments, hands=hands, taken=taken,
                        root=points[root]))
    return out


class Viewport(object):
    """The model panel under a global cursor position, and its camera."""

    def __init__(self, panel, view, widget):
        self.panel, self.view, self.widget = panel, view, widget
        self.sx = view.portWidth() / float(max(1, widget.width()))
        self.sy = view.portHeight() / float(max(1, widget.height()))

    @classmethod
    def at(cls, gx, gy):
        """(Viewport, local point) under the global point, or (None, None)."""
        import maya.cmds as cmds
        import maya.api.OpenMayaUI as omui
        import maya_hubqt
        q = maya_hubqt.qt()
        panels = []
        try:
            under = cmds.getPanel(underPointer=True)
        except RuntimeError:
            under = None
        if under and cmds.getPanel(typeOf=under) == "modelPanel":
            panels.append(under)
        panels += [p for p in (cmds.getPanel(type="modelPanel") or [])
                   if p not in panels]
        for panel in panels:
            try:
                view = omui.M3dView.getM3dViewFromModelPanel(panel)
            except RuntimeError:
                continue
            widget = q.shiboken.wrapInstance(int(view.widget()),
                                             q.QtWidgets.QWidget)
            if not widget.isVisible():
                continue
            local = widget.mapFromGlobal(q.QtCore.QPoint(int(gx), int(gy)))
            if widget.rect().contains(local):
                return cls(panel, view, widget), (local.x(), local.y())
        return None, None

    def to_port(self, local):
        """A widget point (logical px, y down) in port px (y up)."""
        return local[0] * self.sx, (self.widget.height() - local[1]) * self.sy

    def project(self, world):
        import maya.api.OpenMaya as om
        x, y, _unclipped = self.view.worldToView(om.MPoint(*world))
        return float(x), float(y)

    def ray(self, port):
        import maya.api.OpenMaya as om
        near, far = om.MPoint(), om.MPoint()
        self.view.viewToWorld(int(port[0]), int(port[1]), near, far)
        return (near.x, near.y, near.z), (far.x, far.y, far.z)

    def _camera(self):
        import maya.api.OpenMaya as om
        return om.MFnCamera(self.view.getCamera())

    def heading(self):
        import maya.api.OpenMaya as om
        right = self._camera().rightDirection(om.MSpace.kWorld)
        return (right.x, right.y, right.z)

    def depth(self, world):
        import maya.api.OpenMaya as om
        eye = self._camera().eyePoint(om.MSpace.kWorld)
        return (om.MPoint(*world) - eye).length()


def target(gx, gy, snap, scale=1.0, freed=None):
    """What a release at the global point would do, as a dict: kind "hand"
    (root, side), "floor" (root, side, point, heading) or "none"; with the
    caption as "text". `freed` = (root, side) the drag comes from - that side
    counts as free for a floor drop, since it is emptied first."""
    from maya_scenesetup import catalog
    from maya_scenesetup import equip
    view, local = Viewport.at(gx, gy)
    if view is None:
        return dict(kind="none", text="no target - drop onto a viewport")
    port = view.to_port(local)
    figures = []
    for ch in snap:
        pts = dict((j, view.project(p)) for j, p in ch["points"].items())
        figures.append(Figure(
            ch["key"], [(pts[a], pts[b]) for a, b in ch["segments"]],
            dict((s, pts[h] if h else None) for s, h in ch["hands"].items()),
            view.depth(ch["root"])))
    picked = choose(port, figures, 16.0 * scale * view.sx)
    if picked:
        ch = next(c for c in snap if c["key"] == picked[1])
        return dict(kind="hand", root=ch["key"], side=picked[2],
                    text=hand_text(ch["label"], picked[2]))
    near, far = view.ray(port)
    hit = floor_hit(near, far)
    if hit is None:
        return dict(kind="none", text="no floor under the cursor")
    key = owner(hit, dict((c["key"], c["root"]) for c in snap))
    if key is None:
        return dict(kind="none", text="no character in the scene")
    ch = next(c for c in snap if c["key"] == key)
    taken = dict(ch["taken"])
    if freed and freed[0] == key:
        taken[freed[1]] = False
    side = equip.floor_side(taken)
    return dict(kind="floor", root=key, side=side, point=hit,
                heading=view.heading(),
                text=floor_text(ch["label"], catalog.side_bone("weapon_r", side)))
