"""The ragdoll in the scene (2026-10-16): Bullet bodies, joints, floor and colliders built at the
fall's first frame, the time stepped one frame at a time, every body's world read each frame, and
every node it made deleted again. Nothing here is ever left on the rig.

Our own solver and our own wiring (Maya's `CreateRigidBody` takes the scene's FIRST solver - the
animator may have one of their own): the wiring is `maya.app.mayabullet.RigidBody`'s, read and
copied - the shape under the transform, the solver's time, `initialTranslate/Rotate` from the
transform, a pairBlend between the transform's own values and the solved ones.
"""

import math

import maya.cmds as cmds
import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma
import numpy as np

from maya_ragdoll import plan

GROUP = "skeldarRagdoll"
SHAPE_CAPSULE, SHAPE_BOX, SHAPE_MESH = 3, 1, 5
STATIC, KINEMATIC, DYNAMIC = 0, 1, 2
SIXDOF2 = 5
LOCKED, LIMITED = 1, 2
#  Bullet collides two bodies when each one's group is in the other's mask. Defaults: group 1,
#  mask 1 (measured). Maya's Bullet keeps 16 bits (a group of 1<<17 fell through the floor). The
#  capsules: one group per part of the body (`plan.collision_filters`), colliding with each other
#  but their jointed neighbours; the weapon: its own bit, the world only; the floor and the
#  colliders: group 1, every bit
RAGDOLL_GROUP = 2
WORLD_MASK = plan.world_mask()
JOINT_DAMPING = 0.5        # maya.app.mayabullet.Ragdoll's DEFAULT_ANGULAR_DAMPING
SOLVER_RATE = 240          # steps a second
SOLVER_ITERATIONS = 40
FLOOR_THICKNESS = 50.0
FLOOR_SIZE = 5000.0
SPRING_DAMPING = 0.5


def _plugin():
    if not cmds.pluginInfo("bullet", query=True, loaded=True):
        cmds.loadPlugin("bullet", quiet=True)


def _connect(src, dst, **kw):
    cmds.connectAttr(src, dst, force=True, **kw)


def cache_on():
    """Is Maya's Cached Playback on? False where there is no cache evaluator to ask."""
    try:
        return bool(cmds.evaluator(name="cache", query=True, enable=True))
    except Exception:                                       # noqa: BLE001 - nothing to ask
        return False


def _cache(on):
    cmds.evaluator(name="cache", enable=on)


class Scene(object):
    """The ragdoll's nodes: `build_*` make them, `step`/`read` simulate, `delete` takes every node
    the build made (a UUID diff - the pairBlends and the stiffness curves included).

    Cached Playback is off for as long as the nodes stand: switched off before the first one is
    made when it was on, and back on once `delete` has taken them. With it on, Bullet does not step
    in a GUI Maya at all (measured 2026-10-17: a capsule fell 0.0 cm over 10 frames with the cache
    on, 85.3 cm with it off; a Fall pressed with it on left the character standing). mayapy has no
    cache and always stepped, so no headless verify could see it. Switching the cache off flushes
    it: it fills again after the press, as after any edit."""

    def __init__(self, start, friction, bounce):
        _plugin()
        self.cache = cache_on()
        if self.cache:
            _cache(False)
        try:
            self._make(start, friction, bounce)
        except BaseException:
            self._cache_back()
            raise

    def _cache_back(self):
        if self.cache:
            self.cache = False
            _cache(True)

    def _make(self, start, friction, bounce):
        self.before = set(cmds.ls(cmds.ls(), uuid=True) or [])
        self.group = cmds.createNode("transform", name=GROUP, skipSelect=True)
        self.solver_t = cmds.createNode("transform", name=GROUP + "Solver", parent=self.group,
                                        skipSelect=True)
        self.solver = cmds.createNode("bulletSolverShape", parent=self.solver_t, skipSelect=True)
        _connect("time1.outTime", self.solver + ".currentTime")
        cmds.setAttr(self.solver + ".startTime", start)
        cmds.setAttr(self.solver + ".gravity", 0, -plan.G, 0)
        cmds.setAttr(self.solver + ".groundPlane", 0)
        cmds.setAttr(self.solver + ".internalFixedFrameRate", SOLVER_RATE)
        cmds.setAttr(self.solver + ".maxNumIterations", SOLVER_ITERATIONS)
        cmds.setAttr(self.solver + ".splitImpulse", 1)
        self.friction, self.bounce = friction, bounce
        self.bodies = {}           # key: (transform, shape)
        self.joints = {}
        self._hit = set()

    # ---------------------------------------------------------------- bodies

    def _body(self, name, world, kind, mass=0.0, parent=None):
        t = cmds.createNode("transform", name=name, parent=parent or self.group, skipSelect=True)
        cmds.xform(t, worldSpace=True, matrix=plan.flat(world))
        sh = cmds.createNode("bulletRigidBodyShape", parent=t, skipSelect=True)
        _connect(t + ".worldMatrix", sh + ".inWorldMatrix")
        _connect(t + ".parentInverseMatrix", sh + ".inParentInverseMatrix")
        _connect(self.solver + ".outSolverInitialized", sh + ".solverInitialized")
        _connect(self.solver + ".outSolverUpdated", sh + ".solverUpdated")
        cmds.connectAttr(sh + ".outRigidBodyData", self.solver + ".rigidBodies", nextAvailable=True)
        _connect(self.solver + ".startTime", sh + ".startTime")
        _connect(self.solver + ".currentTime", sh + ".currentTime")
        tr = cmds.getAttr(t + ".translate")[0]
        ro = cmds.getAttr(t + ".rotate")[0]
        cmds.setAttr(sh + ".initialTranslate", *tr)
        cmds.setAttr(sh + ".initialRotate", *[math.radians(v) for v in ro])
        if kind == DYNAMIC:
            blend = cmds.createNode("pairBlend", skipSelect=True)
            cmds.setAttr(blend + ".inTranslate1", *tr)
            cmds.setAttr(blend + ".inRotate1", *ro)
            _connect(sh + ".outSolvedTranslate", blend + ".inTranslate2")
            _connect(sh + ".outSolvedRotate", blend + ".inRotate2")
            for a in "XYZ":
                _connect(blend + ".outTranslate" + a, t + ".translate" + a)
                _connect(blend + ".outRotate" + a, t + ".rotate" + a)
            _connect(t + ".isDrivenBySimulation", blend + ".weight")
        _connect(t + ".rotatePivot", sh + ".pivotTranslate")
        cmds.setAttr(sh + ".autoFit", False)       # on by default: it would size the shape itself
        cmds.setAttr(sh + ".bodyType", kind)
        cmds.setAttr(sh + ".mass", mass)
        cmds.setAttr(sh + ".friction", self.friction)
        cmds.setAttr(sh + ".restitution", self.bounce)
        return t, sh

    def build_capsule(self, key, world, length, radius, mass, velocity, spin, filters=None,
                      kind=DYNAMIC):
        """A capsule body along its X; `kind` KINEMATIC: it goes where `place` puts it (Blend's
        Anim zones)."""
        t, sh = self._body("ragdoll_" + key, world, kind, mass if kind == DYNAMIC else 0.0)
        cmds.setAttr(sh + ".colliderShapeType", SHAPE_CAPSULE)
        cmds.setAttr(sh + ".axis", 0)
        cmds.setAttr(sh + ".length", length)
        cmds.setAttr(sh + ".radius", radius)
        cmds.setAttr(sh + ".linearDamping", plan.LINEAR_DAMPING)
        cmds.setAttr(sh + ".angularDamping", plan.ANGULAR_DAMPING)
        cmds.setAttr(sh + ".initialVelocity", *[float(v) for v in velocity])
        cmds.setAttr(sh + ".initialAngularVelocity", *[float(v) for v in spin])
        group, mask = filters or (RAGDOLL_GROUP, plan.WORLD_BIT)
        cmds.setAttr(sh + ".collisionFilterGroup", group)
        cmds.setAttr(sh + ".collisionFilterMask", mask)
        self.bodies[key] = (t, sh)
        return t, sh

    def build_box(self, name, world, extents, mass, velocity=(0, 0, 0), spin=(0, 0, 0)):
        """A dynamic box (the weapon)."""
        t, sh = self._body(name, world, DYNAMIC, mass)
        cmds.setAttr(sh + ".colliderShapeType", SHAPE_BOX)
        cmds.setAttr(sh + ".extents", *[float(v) for v in extents])
        cmds.setAttr(sh + ".initialVelocity", *[float(v) for v in velocity])
        cmds.setAttr(sh + ".initialAngularVelocity", *[float(v) for v in spin])
        cmds.setAttr(sh + ".collisionFilterGroup", plan.WEAPON_BIT)
        cmds.setAttr(sh + ".collisionFilterMask", plan.WORLD_BIT)
        self.bodies[name] = (t, sh)
        return t, sh

    def build_floor(self, height, centre):
        world = plan.frame(np.identity(3), (centre[0], height - FLOOR_THICKNESS * 0.5, centre[2]))
        t, sh = self._body("ragdollFloor", world, STATIC)
        cmds.setAttr(sh + ".colliderShapeType", SHAPE_BOX)
        cmds.setAttr(sh + ".extents", FLOOR_SIZE, FLOOR_THICKNESS, FLOOR_SIZE)
        cmds.setAttr(sh + ".collisionFilterMask", WORLD_MASK)
        return t

    def build_collider(self, mesh_transform):
        """A static mesh body on a DUPLICATE of the animator's mesh (a rigid body rewires its
        transform's channels): the duplicate stands where the mesh does, in our group."""
        copy = cmds.duplicate(mesh_transform, returnRootsOnly=True, name="ragdollCollider")[0]
        copy = cmds.parent(copy, self.group, absolute=True)[0]
        for child in cmds.listRelatives(copy, children=True, fullPath=True) or []:
            if cmds.nodeType(child) != "mesh":
                cmds.delete(child)
        shapes = [s for s in cmds.listRelatives(copy, shapes=True, fullPath=True,
                                                type="mesh") or []
                  if not cmds.getAttr(s + ".intermediateObject")]
        if not shapes:
            cmds.delete(copy)
            return None
        world = plan.mat(cmds.xform(copy, query=True, worldSpace=True, matrix=True))
        sh = cmds.createNode("bulletRigidBodyShape", parent=copy, skipSelect=True)
        _connect(copy + ".worldMatrix", sh + ".inWorldMatrix")
        _connect(copy + ".parentInverseMatrix", sh + ".inParentInverseMatrix")
        _connect(self.solver + ".outSolverInitialized", sh + ".solverInitialized")
        _connect(self.solver + ".outSolverUpdated", sh + ".solverUpdated")
        cmds.connectAttr(sh + ".outRigidBodyData", self.solver + ".rigidBodies", nextAvailable=True)
        _connect(self.solver + ".startTime", sh + ".startTime")
        _connect(self.solver + ".currentTime", sh + ".currentTime")
        _connect(shapes[0] + ".outMesh", sh + ".inMesh")
        tr = cmds.getAttr(copy + ".translate")[0]
        ro = cmds.getAttr(copy + ".rotate")[0]
        cmds.setAttr(sh + ".initialTranslate", *tr)
        cmds.setAttr(sh + ".initialRotate", *[math.radians(v) for v in ro])
        cmds.setAttr(sh + ".bodyType", STATIC)
        cmds.setAttr(sh + ".colliderShapeType", SHAPE_MESH)
        cmds.setAttr(sh + ".collisionFilterMask", WORLD_MASK)
        cmds.setAttr(sh + ".friction", self.friction)
        cmds.setAttr(sh + ".restitution", self.bounce)
        del world
        return copy

    # ---------------------------------------------------------------- joints

    def build_joint(self, key, parent, world, lo, hi, stiffness, fade_keys, linear=None):
        """A SixDOF2 between the parent body and `key`'s at `world` (its frame): linear locked (or
        `linear` = ((min xyz), (max xyz)) cm in the joint's frame as the parent carries it), angular
        limited to `lo`..`hi` degrees, three angular springs keyed by `fade_keys`."""
        t = cmds.createNode("transform", name="ragdollJoint_" + key, parent=self.group,
                            skipSelect=True)
        cmds.xform(t, worldSpace=True, matrix=plan.flat(world))
        cs = cmds.createNode("bulletRigidBodyConstraintShape", parent=t, skipSelect=True)
        cmds.setAttr(cs + ".constraintType", SIXDOF2)
        _connect(self.solver + ".outSolverInitialized", cs + ".solverInitialized")
        _connect(self.bodies[parent][1] + ".outRigidBodyData", cs + ".rigidBodyA")
        _connect(self.bodies[key][1] + ".outRigidBodyData", cs + ".rigidBodyB")
        cmds.connectAttr(cs + ".outConstraintData", self.solver + ".rigidBodyConstraints",
                         nextAvailable=True)
        _connect(self.solver + ".startTime", cs + ".startTime")
        _connect(self.solver + ".currentTime", cs + ".currentTime")
        for ax in "XYZ":
            cmds.setAttr(cs + ".linearConstraint" + ax, LOCKED if linear is None else LIMITED)
            cmds.setAttr(cs + ".angularConstraint" + ax, LIMITED)
        if linear is not None:
            cmds.setAttr(cs + ".linearConstraintMin", *[float(v) for v in linear[0]])
            cmds.setAttr(cs + ".linearConstraintMax", *[float(v) for v in linear[1]])
        cmds.setAttr(cs + ".angularDamping", JOINT_DAMPING)
        cmds.setAttr(cs + ".angularRestitution", 0.0)
        cmds.setAttr(cs + ".angularConstraintMin", *[float(v) for v in lo])
        cmds.setAttr(cs + ".angularConstraintMax", *[float(v) for v in hi])
        if stiffness > 0:
            for ax in "XYZ":
                cmds.setAttr(cs + ".angularSpringEnabled" + ax, 1)
                cmds.setAttr(cs + ".angularSpringDamping" + ax, SPRING_DAMPING)
                for time, value in fade_keys:
                    cmds.setKeyframe(cs, attribute="angularSpringStiffness" + ax, time=time,
                                     value=value, inTangentType="flat", outTangentType="flat")
        self.joints[key] = (t, cs)
        return cs

    # ---------------------------------------------------------------- blend (2026-10-17)

    def kick(self, key, j, torque):
        """Body `key` given `j` (kg*cm/s, world) at its centre and `torque` (kg*cm^2*rad/s, world)
        on the next step - each acts once a frame (measured: Bullet's capsule inertia is a box's,
        `plan.capsule_inertia`). `clear_impulses` after the step."""
        sh = self.bodies[key][1]
        cmds.setAttr(sh + ".impulse", *[float(v) for v in j])
        cmds.setAttr(sh + ".impulsePosition", 0, 0, 0)
        cmds.setAttr(sh + ".torqueImpulse", *[float(v) for v in torque])
        self._hit.add(key)

    # ---------------------------------------------------------------- the run

    def go(self, frame):
        oma.MAnimControl.setCurrentTime(om.MTime(frame, om.MTime.uiUnit()))

    def impulse(self, key, j, point):
        """A hit on body `key` for the next step: `j` kg*cm/s in world axes, `point` an offset from
        its centre in world axes (Bullet's own: measured 2026-10-16). It acts on every step while
        set - `clear_impulses` after the step."""
        sh = self.bodies[key][1]
        cmds.setAttr(sh + ".impulse", *[float(v) for v in j])
        cmds.setAttr(sh + ".impulsePosition", *[float(v) for v in point])
        self._hit.add(key)

    def clear_impulses(self):
        for key in getattr(self, "_hit", ()):
            sh = self.bodies[key][1]
            cmds.setAttr(sh + ".impulse", 0, 0, 0)
            cmds.setAttr(sh + ".impulsePosition", 0, 0, 0)
            cmds.setAttr(sh + ".torqueImpulse", 0, 0, 0)
        self._hit = set()

    def read(self, names=None):
        """{body: 4x4 world} as the bodies stand now."""
        out = {}
        for key, (t, _sh) in self.bodies.items():
            if names is None or key in names:
                out[key] = plan.mat(cmds.xform(t, query=True, worldSpace=True, matrix=True))
        return out

    def delete(self):
        """Every node the build made, gone (by UUID: whatever Maya named them), then Cached
        Playback back on if the build switched it off."""
        try:
            now = set(cmds.ls(cmds.ls(), uuid=True) or [])
            made = [u for u in now - self.before]
            paths = cmds.ls(made, long=True) or []
            dag = [p for p in paths if p.startswith("|")]
            tops = [p for p in dag if not any(p.startswith(o + "|") for o in dag if o != p)]
            for path in tops + [p for p in paths if not p.startswith("|")]:
                if cmds.objExists(path):
                    try:
                        cmds.lockNode(path, lock=False)
                        cmds.delete(path)
                    except Exception:                 # noqa: BLE001 - gone with its parent
                        pass
        finally:
            self._cache_back()


def skinned_points(meshes, rider_of):
    """{body: n x 3 world points} of the skinned vertices whose heaviest influence rides that body
    (`rider_of` {bone leaf: body}), as the meshes stand now."""
    out = {}
    for shape in meshes:
        skins = cmds.ls(cmds.listHistory(shape, pruneDagObjects=True) or [], type="skinCluster")
        if not skins:
            continue
        sel = om.MSelectionList()
        sel.add(skins[0])
        sel.add(shape)
        skin = oma.MFnSkinCluster(sel.getDependNode(0))
        path = sel.getDagPath(1)
        influences = [p.partialPathName().split("|")[-1].split(":")[-1]
                      for p in skin.influenceObjects()]
        mesh = om.MFnMesh(path)
        points = np.array([(p.x, p.y, p.z) for p in mesh.getPoints(om.MSpace.kWorld)])
        comp = om.MFnSingleIndexedComponent()
        all_verts = comp.create(om.MFn.kMeshVertComponent)
        comp.setCompleteData(len(points))
        weights, count = skin.getWeights(path, all_verts)
        # fromiter reads the MDoubleArray straight (69 -> 31 ms a 1.9 M weights, 2026-10-27)
        w = np.fromiter(weights, float, len(weights)).reshape(len(points), count)
        heaviest = np.argmax(w, axis=1)
        for index, name in enumerate(influences):
            body = rider_of.get(name)
            if body is None:
                continue
            chosen = points[heaviest == index]
            if len(chosen):
                out.setdefault(body, []).append(chosen)
    return dict((k, np.vstack(v)) for k, v in out.items())
