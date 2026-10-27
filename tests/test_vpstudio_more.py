"""Viewport Studio's press on a fake scene (maya_vpstudio): what Apply builds and writes, what a second press
carries forward, what the dials touch, what Restore gives back and deletes; the panel's presses.

The fake is a small DAG (nodes by id, paths worked out from their parents, so a parent or a rename moves the
whole subtree), a few model panels, Maya's display prefs and the hardware renderer's globals."""

import collections
import math
import unittest
from unittest import mock

import maya_vpstudio as vp


class Node(object):
    def __init__(self, name, kind, parent=None, dag=True):
        self.name = name
        self.kind = kind
        self.parent = parent
        self.dag = dag
        self.attrs = {}
        self.uuid = None
        self.members = []          # a set's
        self.verts = []            # a mesh's
        self.bbox = None
        self.xform = {}


LIGHT_ATTRS = ("intensity", "color", "emitSpecular", "emitDiffuse", "useRayTraceShadows", "ambientShade",
               "coneAngle", "penumbraAngle", "dropoff", "useDepthMapShadows", "dmapResolution",
               "dmapFilterSize", "shadowColor", "useDmapAutoFocus", "dmapWidthFocus")
MESH_ATTRS = ("castsShadows", "receiveShadows", "doubleSided", "primaryVisibility", "intermediateObject")
CAMERA_ATTRS = ("depthOfField", "focusDistance", "fStop", "focusRegionScale")
RENDER = {attr: 0 for attr in vp.RENDER_ATTRS}


class StudioScene(object):
    def __init__(self):
        self.nodes = []
        self.ids = 0
        self.panels = collections.OrderedDict()
        self.focus = None
        self.visible = []
        self.gradient = False
        self.colours = {"background": [0.36, 0.36, 0.36], "backgroundTop": [0.53, 0.6, 0.66],
                        "backgroundBottom": [0.05, 0.05, 0.05]}
        self.autokey = True
        self.selection = []
        self.chunks = []
        self.connections = []
        self.refreshed = 0
        self.messages = []
        self.vars = {}
        self.missing = set()               # render attrs this Maya lacks
        render = self._new("hardwareRenderingGlobals", "hardwareRenderingGlobals", dag=False)
        render.attrs.update(RENDER)

    # -------------------------------------------------------------- building
    def _new(self, name, kind, parent=None, dag=True, attrs=()):
        node = Node(name, kind, parent, dag)
        self.ids += 1
        node.uuid = "UUID-%04d" % self.ids
        for attr in attrs:
            node.attrs[attr] = 0
        if kind in ("transform", "joint"):
            node.attrs.update({"rotateY": 0.0, "overrideEnabled": 0, "overrideDisplayType": 0})
        self.nodes.append(node)
        return node

    def mesh(self, name, bbox, parent=None, intermediate=False):
        transform = self._new(name, "transform", parent)
        shape = self._new(name + "Shape", "mesh", transform, attrs=MESH_ATTRS)
        shape.attrs["intermediateObject"] = int(intermediate)
        shape.bbox = tuple(bbox)
        return transform

    def joint(self, name, bbox, parent=None):
        node = self._new(name, "joint", parent)
        node.bbox = tuple(bbox)
        return node

    def camera(self, name, position):
        transform = self._new(name, "transform")
        transform.xform["translation"] = list(position)
        shape = self._new(name + "Shape", "camera", transform, attrs=CAMERA_ATTRS)
        shape.attrs["focusDistance"] = 5.0
        shape.attrs["fStop"] = 5.6
        shape.attrs["focusRegionScale"] = 1.0
        return transform

    def panel(self, name, camera, **flags):
        state = {flag: True for flag in vp.PANEL_FLAGS}
        state.update(displayAppearance="wireframe", displayLights="default")
        state.update(flags)
        state["camera"] = camera
        self.panels[name] = state

    # -------------------------------------------------------------- lookups
    def path(self, node):
        if not node.dag:
            return node.name
        out = []
        while node is not None:
            out.append(node.name)
            node = node.parent
        return "|" + "|".join(reversed(out))

    def find(self, name):
        if name is None:
            return None
        for node in self.nodes:
            if self.path(node) == name or node.uuid == name:
                return node
        for node in self.nodes:
            if node.name == name.split("|")[-1]:
                return node
        return None

    def children(self, node):
        return [n for n in self.nodes if n.parent is node]

    def by_path(self, path):
        node = self.find(path)
        assert node is not None, path
        return node

    # -------------------------------------------------------------- cmds
    def objExists(self, name):  # noqa: N802
        if "." in name:
            node_name, attr = name.split(".", 1)
            node = self.find(node_name)
            return node is not None and attr in node.attrs and attr not in self.missing
        return self.find(name) is not None

    def getAttr(self, plug, **_kw):  # noqa: N802
        node_name, attr = plug.split(".", 1)
        return self.by_path(node_name).attrs[attr]

    def setAttr(self, plug, *values, **kw):  # noqa: N802
        node_name, attr = plug.split(".", 1)
        node = self.by_path(node_name)
        if attr in self.missing:
            raise RuntimeError("no attribute " + attr)
        node.attrs[attr] = values[0] if len(values) == 1 else list(values)

    def addAttr(self, node, longName=None, **_kw):  # noqa: N802,N803
        self.by_path(node).attrs[longName] = ""

    def ls(self, *args, **kw):
        if kw.get("selection"):
            return list(self.selection)
        if kw.get("type") == "mesh":
            return [self.path(n) for n in self.nodes if n.kind == "mesh"
                    and not (kw.get("noIntermediate") and n.attrs.get("intermediateObject"))]
        if kw.get("type") == "joint":
            return [self.path(n) for n in self.nodes if n.kind == "joint"]
        if not args:
            return []
        pattern = args[0]
        if isinstance(pattern, str) and pattern.startswith("*."):
            attr = pattern[2:]
            return [self.path(n) for n in self.nodes if attr in n.attrs]
        names = pattern if isinstance(pattern, (list, tuple)) else [pattern]
        out = []
        for name in names:
            node = self.find(name)
            if node is not None:
                out.append(node.uuid if kw.get("uuid") else self.path(node))
        return out

    def listRelatives(self, name, parent=False, shapes=False, type=None, **_kw):  # noqa: N802,A002
        node = self.by_path(name)
        if parent:
            return [self.path(node.parent)] if node.parent is not None else None
        if shapes:
            found = [self.path(n) for n in self.children(node)
                     if n.kind in ("mesh", "camera", "spotLight", "directionalLight", "ambientLight")
                     and (type is None or n.kind == type)]
            return found or None
        return None

    def nodeType(self, name):  # noqa: N802
        return self.by_path(name).kind

    def getPanel(self, type=None, withFocus=False, visiblePanels=False):  # noqa: N802,A002
        if type == "modelPanel":
            return list(self.panels)
        if withFocus:
            if self.focus == "raise":
                raise RuntimeError("no focus")
            return self.focus
        if visiblePanels:
            return list(self.visible)
        return []

    def modelPanel(self, name, exists=False):  # noqa: N802
        return name in self.panels

    def modelEditor(self, name, query=False, edit=False, **flags):  # noqa: N802
        state = self.panels[name]
        if query:
            flag = list(flags)[0]
            if flag not in state:
                raise TypeError("Invalid flag '%s'" % flag)
            return state[flag]
        for flag, value in flags.items():
            if flag not in state:
                raise TypeError("Invalid flag '%s'" % flag)
            state[flag] = value

    def displayPref(self, query=False, displayGradient=None):  # noqa: N802,N803
        if query:
            return self.gradient
        self.gradient = displayGradient

    def displayRGBColor(self, name, *values, **kw):  # noqa: N802
        if kw.get("query"):
            return list(self.colours[name])
        self.colours[name] = list(values)

    def xform(self, name, query=False, worldSpace=False, objectSpace=False, translation=None,  # noqa: N803
              matrix=None, rotation=None):
        if ".vtx[" in name:
            mesh_name, index = name.split(".vtx[")
            shape = self.children(self.by_path(mesh_name))[0]
            i = int(index.rstrip("]"))
            if query:
                return list(shape.verts[i])
            shape.verts[i] = tuple(translation)
            return None
        node = self.by_path(name)
        if query:
            return list(node.xform.get("translation", [0.0, 0.0, 0.0]))
        for key, value in (("translation", translation), ("matrix", matrix), ("rotation", rotation)):
            if value is not None:
                node.xform[key] = list(value)
                node.xform[key + "_space"] = "world" if worldSpace else "object"

    def exactWorldBoundingBox(self, names):  # noqa: N802
        names = names if isinstance(names, (list, tuple)) else [names]
        boxes = []
        for name in names:
            node = self.by_path(name)
            if node.bbox == "raise":
                raise RuntimeError("no box")
            boxes.append(node.bbox)
        return list(vp.bbox_union(boxes))

    def autoKeyframe(self, query=False, state=None):  # noqa: N802
        if query:
            return self.autokey
        self.autokey = state

    def undoInfo(self, openChunk=False, closeChunk=False, chunkName=None):  # noqa: N802,N803
        if openChunk:
            self.chunks.append(("open", chunkName))
        if closeChunk:
            self.chunks.append(("close", None))

    def group(self, empty=True, name=None, parent=None):
        node = self._new(name, "transform", self.find(parent) if parent else None)
        return node.name

    def _light(self, kind):
        count = len([n for n in self.nodes if n.kind == kind]) + 1
        transform = self._new("%s%d" % (kind, count), "transform")
        shape = self._new("%sShape%d" % (kind, count), kind, transform, attrs=LIGHT_ATTRS)
        shape.attrs["useRayTraceShadows"] = 1                  # what Maya's light commands make
        return shape.name

    def spotLight(self):  # noqa: N802
        return self._light("spotLight")

    def directionalLight(self):  # noqa: N802
        return self._light("directionalLight")

    def ambientLight(self):  # noqa: N802
        return self._light("ambientLight")

    def parent(self, child, new_parent):
        node = self.by_path(child)
        node.parent = self.by_path(new_parent)
        return [node.name]

    def rename(self, name, new):
        node = self.by_path(name)
        node.name = new
        return new

    def polyPlane(self, width=1.0, height=1.0, subdivisionsX=1, subdivisionsY=1, **_kw):  # noqa: N802,N803
        count = len([n for n in self.nodes if n.kind == "mesh"]) + 1
        transform = self._new("pPlane%d" % count, "transform")
        shape = self._new("pPlaneShape%d" % count, "mesh", transform, attrs=MESH_ATTRS)
        shape.attrs["intermediateObject"] = 0
        shape.size = (width, height, subdivisionsX, subdivisionsY)
        for j in range(subdivisionsY + 1):
            for i in range(subdivisionsX + 1):
                shape.verts.append((-width / 2.0 + width * i / subdivisionsX, 0.0,
                                    height / 2.0 - height * j / subdivisionsY))
        shape.bbox = (-width / 2.0, 0.0, -height / 2.0, width / 2.0, 0.0, height / 2.0)
        return [transform.name]

    def polyEvaluate(self, name, vertex=False):  # noqa: N802
        return len(self.children(self.by_path(name))[0].verts)

    def polySoftEdge(self, name, angle=None, **_kw):  # noqa: N802
        self.children(self.by_path(name))[0].soft = angle

    def shadingNode(self, kind, asShader=False, name=None):  # noqa: N802,N803
        node = self._new(name, kind, dag=False, attrs=("color", "specularColor", "eccentricity",
                                                       "specularRollOff", "outColor"))
        return node.name

    def sets(self, *args, **kw):
        if kw.get("edit"):
            group = self.by_path(kw["forceElement"])
            group.members.append(self.by_path(args[0]))
            return None
        node = self._new(kw["name"], "shadingEngine", dag=False, attrs=("surfaceShader",))
        return node.name

    def connectAttr(self, source, dest, force=False):  # noqa: N802
        self.connections.append((source, dest))

    def delete(self, name):
        node = self.by_path(name)
        doomed = [node]
        changed = True
        while changed:
            changed = False
            for other in self.nodes:
                if other.parent in doomed and other not in doomed:
                    doomed.append(other)
                    changed = True
        self.nodes = [n for n in self.nodes if n not in doomed]
        #  Maya deletes a set together with its last member (trap 18)
        for group in [n for n in self.nodes if n.kind == "shadingEngine" and n.members]:
            group.members = [m for m in group.members if m not in doomed]
            if not group.members:
                self.nodes.remove(group)

    def select(self, names=None, replace=False, clear=False):
        self.selection = [] if clear else list(names)

    def refresh(self, *_a, **_kw):
        self.refreshed += 1

    def headsUpMessage(self, text, **_kw):  # noqa: N802
        self.messages.append(text)

    def control(self, name, exists=False):
        return False

    def optionVar(self, exists=None, query=None, intValue=None, floatValue=None,  # noqa: N802,N803
                  stringValue=None):
        if exists is not None:
            return exists in self.vars
        if query is not None:
            return self.vars[query]
        for pair in (intValue, floatValue, stringValue):
            if pair is not None:
                self.vars[pair[0]] = pair[1]


BODY = (-30.0, 0.0, -20.0, 30.0, 180.0, 20.0)


class StudioTest(unittest.TestCase):
    def setUp(self):
        self.scene = StudioScene()
        patcher = mock.patch.object(vp, "cmds", self.scene)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.scene.mesh("body", BODY)
        self.cam = self.scene.camera("persp", (0.0, 150.0, 600.0))
        self.scene.panel("modelPanel4", "persp")
        self.scene.panel("modelPanel1", "persp", joints=False)
        self.scene.focus = "modelPanel4"

    def rig(self):
        return vp.find_rig()

    def lights(self):
        return [n for n in self.scene.nodes if n.kind.endswith("Light")]

    def render(self, attr):
        return self.scene.getAttr("hardwareRenderingGlobals." + attr)


class Resolve(StudioTest):
    def test_a_uuid_back_to_its_path(self):
        body = self.scene.find("|body")
        self.assertEqual(vp.resolve(body.uuid), "|body")
        self.assertIsNone(vp.resolve(""))
        self.assertIsNone(vp.resolve("UUID-gone"))


class ActivePanel(StudioTest):
    def test_the_focused_model_panel(self):
        self.assertEqual(vp.active_panel(), "modelPanel4")

    def test_a_focus_elsewhere_takes_the_first_visible_model_panel(self):
        self.scene.focus = "outlinerPanel1"
        self.scene.visible = ["outlinerPanel1", "modelPanel1"]
        self.assertEqual(vp.active_panel(), "modelPanel1")

    def test_none_visible_takes_the_first(self):
        self.scene.focus = "raise"
        self.assertEqual(vp.active_panel(), "modelPanel4")

    def test_no_model_panel_is_none(self):
        self.scene.panels.clear()
        self.scene.focus = None
        self.assertIsNone(vp.active_panel())


class Subject(StudioTest):
    def test_every_visible_mesh_is_measured(self):
        self.scene.mesh("sword", (20.0, 80.0, -5.0, 60.0, 90.0, 5.0))
        self.assertEqual(list(vp.subject_bbox()), list(vp.bbox_union([BODY, (20.0, 80.0, -5.0, 60.0, 90.0, 5.0)])))

    def test_intermediate_meshes_and_ours_are_left_out(self):
        self.scene.mesh("orig", (-900.0, 0.0, -900.0, 900.0, 900.0, 900.0), intermediate=True)
        vp.setup({"look": "Studio"})
        self.assertEqual(list(vp.subject_bbox()), list(BODY))             # not our 20-radii floor

    def test_a_mesh_that_cannot_be_measured_is_skipped(self):
        self.scene.mesh("bad", (0, 0, 0, 1, 1, 1)).bbox = None
        self.scene.find("|bad|badShape").bbox = "raise"
        self.assertEqual(list(vp.subject_bbox()), list(BODY))

    def test_no_geometry_measures_the_joints(self):
        self.scene.delete("|body")
        self.scene.joint("root", (-5.0, 0.0, -5.0, 5.0, 170.0, 5.0))
        self.assertEqual(vp.subject_bbox(), [-5.0, 0.0, -5.0, 5.0, 170.0, 5.0])

    def test_nothing_at_all_is_none(self):
        self.scene.delete("|body")
        self.assertIsNone(vp.subject_bbox())
        root = self.scene.joint("root", (0, 0, 0, 1, 1, 1))
        root.bbox = "raise"
        self.assertIsNone(vp.subject_bbox())


class Setup(StudioTest):
    def test_the_studio_stands_on_the_subject(self):
        message = vp.setup({"look": "Studio"})
        rig = self.rig()
        self.assertEqual(rig, "|VPStudio")
        frame = vp.subject_frame(BODY)
        pivot = self.scene.by_path("|VPStudio|VPStudio_lights")
        self.assertEqual(pivot.xform["translation"], list(frame["centre"]))
        names = [spec.name for spec in vp.lights_of("Studio")]
        self.assertEqual([self.scene.path(n.parent) for n in self.lights()],
                         ["|VPStudio|VPStudio_lights|VPStudio_" + name for name in names])
        self.assertEqual(sorted(vp.read_index(rig)), sorted(names))
        for name, uuid in vp.read_index(rig).items():
            self.assertEqual(vp.resolve(uuid), "|VPStudio|VPStudio_lights|VPStudio_" + name)
        self.assertEqual(vp.read_options(rig)["look"], "Studio")
        self.assertEqual(vp.resolve(vp._string_attr(rig, vp.PIVOT_ATTR)), self.scene.path(pivot))
        self.assertTrue(message.startswith("Studio on - 5 lights, floor, Good quality, subject 180 cm"), message)
        self.assertEqual(self.scene.chunks, [("open", "Viewport Studio"), ("close", None)])

    def test_each_light_is_dressed_and_placed_by_the_plan(self):
        vp.setup({"look": "Studio"})
        frame = vp.subject_frame(BODY)
        azimuth = vp.studio_azimuth((0.0, 150.0, 600.0), frame["centre"])
        plan = {entry["name"]: entry for entry in vp.light_plan(frame, azimuth, vp.merged_options())}
        for light in self.lights():
            transform = light.parent
            entry = plan[transform.name]
            self.assertEqual(transform.xform["matrix"], list(entry["matrix"]))
            self.assertAlmostEqual(light.attrs["intensity"], entry["intensity"])
            self.assertEqual(light.attrs["useRayTraceShadows"], 0)
            self.assertEqual(light.attrs["useDepthMapShadows"], int(entry["shadow"]))
            if entry["kind"] == "spot":
                self.assertAlmostEqual(light.attrs["coneAngle"], entry["cone"])
            if entry["shadow"]:
                self.assertEqual(light.attrs["dmapResolution"], entry["dmap"])
        ambient = [n for n in self.lights() if n.kind == "ambientLight"][0]
        self.assertEqual(ambient.attrs["ambientShade"], 0.45)

    def test_the_outdoor_sun_focuses_its_shadow_on_the_subject(self):
        vp.setup({"look": "Outdoor"})
        sun = [n for n in self.lights() if self.scene.path(n.parent).endswith("VPStudio_sun")][0]
        self.assertEqual(sun.attrs["useDmapAutoFocus"], 0)
        self.assertAlmostEqual(sun.attrs["dmapWidthFocus"], 2.6 * vp.subject_frame(BODY)["radius"])

    def test_the_floor_catches_the_shadow_and_casts_none(self):
        vp.setup({"look": "Studio"})
        floor = self.scene.by_path("|VPStudio|VPStudio_floor")
        plan = vp.floor_plan(vp.subject_frame(BODY))
        shape = self.scene.children(floor)[0]
        self.assertEqual(shape.size[:2], (plan["size"], plan["size"]))
        self.assertEqual(floor.xform["translation"], list(plan["position"]))
        self.assertEqual((shape.attrs["castsShadows"], shape.attrs["receiveShadows"]), (0, 1))
        self.assertEqual((floor.attrs["overrideEnabled"], floor.attrs["overrideDisplayType"]), (1, 2))
        shader = self.scene.find(vp.SHADER)
        self.assertEqual(shader.kind, "blinn")
        self.assertEqual(shader.attrs["color"], list(plan["colour"]))
        group = self.scene.find(vp.SHADER + "SG")
        self.assertEqual(group.members, [floor])
        self.assertIn((vp.SHADER + ".outColor", vp.SHADER + "SG.surfaceShader"), self.scene.connections)

    def test_soft_studio_bends_its_paper_onto_the_cyclorama(self):
        message = vp.setup({"look": "Soft Studio"})
        self.assertIn("cyclorama", message)
        sweep = self.scene.by_path("|VPStudio|VPStudio_cyclorama")
        frame = vp.subject_frame(BODY)
        plan = vp.cyclorama_plan(frame, vp.studio_azimuth((0.0, 150.0, 600.0), frame["centre"]),
                                 {"look": "Soft Studio"})
        shape = self.scene.children(sweep)[0]
        self.assertEqual(shape.soft, 180)
        self.assertEqual(sweep.xform["rotation"], [0.0, plan["rotate_y"], 0.0])
        self.assertEqual(sweep.xform["translation"], list(plan["position"]))
        profile = plan["profile"]
        half = plan["width"] / 2.0
        self.assertEqual(sorted({(round(z, 6), round(y, 6)) for _x, y, z in shape.verts}),
                         sorted({(round(z, 6), round(y, 6)) for z, y in profile}))
        self.assertEqual({x for x, _y, _z in shape.verts}, {-half, half})
        self.assertIsNone(self.scene.find("|VPStudio|VPStudio_floor"))

    def test_no_floor_asked_none_built(self):
        message = vp.setup({"floor": False})
        self.assertEqual(self.scene.children(self.scene.by_path("|VPStudio")),
                         [self.scene.by_path("|VPStudio|VPStudio_lights")])
        self.assertNotIn("floor", message)

    def test_the_viewport_takes_the_looks_settings(self):
        vp.setup({"look": "Studio", "clean": True})
        wanted = vp.render_settings(vp.subject_frame(BODY), vp.merged_options({"clean": True}))
        for attr, value in wanted.items():
            self.assertEqual(self.render(attr), value, attr)
        for flag, value in vp.panel_settings({"clean": True}).items():
            self.assertEqual(self.scene.panels["modelPanel4"][flag], value, flag)
        back = vp.backdrop_settings(vp.merged_options())
        self.assertTrue(self.scene.gradient)
        self.assertEqual(self.scene.colours["backgroundTop"], list(back["backgroundTop"]))

    def test_a_setting_this_maya_lacks_is_counted(self):
        self.scene.missing = {"bloomEnable"}
        message = vp.setup({"look": "Studio"})
        self.assertTrue(message.endswith("(1 setting(s) unavailable)"), message)

    def test_without_clean_view_the_animators_own_flags_come_back(self):
        vp.setup({"clean": True})
        self.assertFalse(self.scene.panels["modelPanel4"]["joints"])
        vp.setup({"clean": False})
        self.assertTrue(self.scene.panels["modelPanel4"]["joints"])
        self.assertFalse(self.scene.panels["modelPanel1"]["joints"])      # theirs was off

    def test_depth_of_field_focuses_on_the_subject(self):
        vp.setup({"dof": True})
        shape = self.scene.by_path("|persp|perspShape")
        frame = vp.subject_frame(BODY)
        distance = math.sqrt(sum((a - b) ** 2 for a, b in zip((0.0, 150.0, 600.0), frame["centre"])))
        self.assertEqual(shape.attrs["depthOfField"], 1)
        self.assertAlmostEqual(shape.attrs["focusDistance"], distance)
        self.assertEqual(shape.attrs["fStop"], 8.0)
        vp.setup({"dof": False})
        self.assertEqual(shape.attrs["depthOfField"], 0)

    def test_autokey_and_the_selection_are_put_back(self):
        self.scene.selection = ["|body"]
        vp.setup()
        self.assertEqual(self.scene.selection, ["|body"])
        self.assertTrue(self.scene.autokey)
        self.scene.selection = []
        vp.setup()
        self.assertEqual(self.scene.selection, [])

    def test_a_selection_the_press_deleted_is_cleared(self):
        vp.setup({"look": "Studio"})
        self.scene.selection = ["|VPStudio|VPStudio_lights|VPStudio_rim"]
        vp.setup({"look": "Outdoor"})                    # no rim outdoors
        self.assertEqual(self.scene.selection, [])

    def test_not_undoable_opens_no_chunk(self):
        vp.setup(undoable=False)
        self.assertEqual(self.scene.chunks, [])


class SecondPress(StudioTest):
    def test_the_first_press_remembers_the_animators_viewport(self):
        self.scene.attrs_before = dict(self.scene.find("hardwareRenderingGlobals").attrs)
        vp.setup()
        state = vp.read_state(self.rig())
        self.assertEqual(state["plugs"]["hardwareRenderingGlobals.ssaoEnable"], 0)
        self.assertEqual(state["panels"]["modelPanel4"]["displayAppearance"], "wireframe")
        self.assertFalse(state["backdrop"]["gradient"])

    def test_a_second_press_carries_the_first_presses_memory_and_leaves_one_studio(self):
        vp.setup({"look": "Studio"})
        first = vp.read_state(self.rig())
        vp.setup({"look": "Outdoor"})
        self.assertEqual(vp.read_state(self.rig()), first)          # not our own studio
        self.assertEqual(len([n for n in self.scene.nodes if n.name == vp.GROUP]), 1)
        self.assertEqual(len(self.lights()), len(vp.lights_of("Outdoor")))
        self.assertIsNone(self.scene.find(vp.SHADER + "1"))
        self.assertEqual(len([n for n in self.scene.nodes if n.kind == "blinn"]), 1)

    def test_delete_rig_takes_every_recorded_node_and_counts_them(self):
        vp.setup()
        rig = self.rig()
        recorded = vp.recorded_nodes(rig)
        gone = vp.delete_rig()
        #  the pivot (its lights with it), the floor (its shading group with it, trap 18), the blinn, the group
        self.assertEqual(len(recorded), 9)
        self.assertEqual(gone, 4)
        self.assertIsNone(vp.find_rig())
        self.assertEqual(self.lights(), [])
        self.assertIsNone(self.scene.find(vp.SHADER))
        self.assertIsNone(self.scene.find(vp.SHADER + "SG"))
        self.assertIsNotNone(self.scene.find("|body"))

    def test_delete_rig_with_no_rig_deletes_nothing(self):
        self.assertEqual(vp.delete_rig(), 0)

    def test_a_delete_that_fails_does_not_stop_the_rest(self):
        vp.setup()
        real = self.scene.delete

        def picky(name):
            if name == "|VPStudio|VPStudio_lights":
                raise RuntimeError("locked")
            real(name)
        self.scene.delete = picky
        self.assertEqual(vp.delete_rig(), 8)             # each light on its own, the floor, blinn, group
        self.assertIsNone(vp.find_rig())
        self.assertEqual(self.lights(), [])


class Retune(StudioTest):
    def test_no_studio_no_retune(self):
        self.assertEqual(vp.retune({"brightness": 2.0}), "")

    def test_the_dials_scale_the_built_looks_lights_and_turn_the_pivot(self):
        vp.setup({"look": "Outdoor"})
        message = vp.retune({"look": "Studio", "brightness": 2.0, "rotate": 45.0})
        index = vp.read_index(self.rig())
        for spec in vp.lights_of("Outdoor"):
            shape = vp.resolve(index[spec.name])
            light = self.scene.children(self.scene.by_path(shape))[0]
            self.assertAlmostEqual(light.attrs["intensity"], spec.intensity * 2.0)
        pivot = self.scene.by_path("|VPStudio|VPStudio_lights")
        self.assertEqual(pivot.attrs["rotateY"], 45.0)
        options = vp.read_options(self.rig())
        self.assertEqual((options["look"], options["brightness"], options["rotate"]), ("Outdoor", 2.0, 45.0))
        self.assertEqual(message, "Outdoor: brightness 2.00, rotate 45, 4 lights")

    def test_a_negative_brightness_is_dark_not_inverted(self):
        vp.setup()
        vp.retune({"brightness": -3.0})
        self.assertTrue(all(n.attrs["intensity"] == 0.0 for n in self.lights()))

    def test_a_light_deleted_by_hand_is_skipped(self):
        vp.setup()
        self.scene.delete("|VPStudio|VPStudio_lights|VPStudio_rim")
        self.assertTrue(vp.retune({"brightness": 1.5}).endswith(", 4 lights"))


class Restore(StudioTest):
    def test_no_studio_is_said(self):
        self.assertIn("nothing to restore", vp.restore())

    def test_the_animators_viewport_comes_back_and_our_nodes_go(self):
        before_render = dict(self.scene.find("hardwareRenderingGlobals").attrs)
        before_panels = {name: dict(flags) for name, flags in self.scene.panels.items()}
        before_colours = {k: list(v) for k, v in self.scene.colours.items()}
        vp.setup({"look": "Outdoor", "clean": True})
        vp.setup({"look": "Soft Studio"})
        message = vp.restore()
        self.assertTrue(message.startswith("studio off - viewport restored"), message)
        self.assertEqual(self.scene.find("hardwareRenderingGlobals").attrs, before_render)
        self.assertEqual(self.scene.panels, before_panels)
        self.assertEqual(self.scene.colours, before_colours)
        self.assertFalse(self.scene.gradient)
        self.assertIsNone(vp.find_rig())
        self.assertEqual(self.lights(), [])
        self.assertEqual([n.kind for n in self.scene.nodes if n.kind in ("blinn", "shadingEngine")], [])
        self.assertEqual(self.scene.chunks[-2:], [("open", "Viewport Studio off"), ("close", None)])

    def test_a_studio_with_no_memory_still_comes_out(self):
        vp.setup()
        self.scene.setAttr(self.rig() + "." + vp.STATE_ATTR, "", type="string")
        self.assertIn("no saved viewport state", vp.restore())

    def test_toggle_builds_then_takes_down(self):
        self.assertIn("Studio on", vp.toggle())
        self.assertIsNotNone(vp.find_rig())
        self.assertIn("studio off", vp.toggle())
        self.assertIsNone(vp.find_rig())


class Presses(StudioTest):
    """The panel's presses with the panel closed: the remembered choices."""

    def test_remember_writes_each_by_its_type(self):
        vp._remember(collections.OrderedDict((("floor", False), ("brightness", 1.5), ("look", "Outdoor"))))
        self.assertEqual(self.scene.vars, {"skeldarVpStudio_floor": 0, "skeldarVpStudio_brightness": 1.5,
                                           "skeldarVpStudio_look": "Outdoor"})
        options = vp.window_options()
        self.assertEqual((options["floor"], options["brightness"], options["look"]), (False, 1.5, "Outdoor"))

    def test_apply_builds_the_remembered_look_and_says_so(self):
        self.scene.vars["skeldarVpStudio_look"] = "Outdoor"
        message = vp._press_setup()
        self.assertTrue(message.startswith("Outdoor on - 4 lights"), message)
        self.assertIn(message, self.scene.messages)
        self.assertEqual(self.scene.vars["skeldarVpStudio_look"], "Outdoor")

    def test_restore_and_the_view_presets(self):
        vp._press_setup()
        self.assertIn("viewport restored", vp._press_restore())
        self.assertIn("Anim view", vp._press_anim_view())
        self.assertFalse(self.scene.panels["modelPanel4"]["joints"])
        self.assertIn("Default view", vp._press_default_view())

    def test_a_dial_with_no_studio_is_only_remembered(self):
        self.scene.vars["skeldarVpStudio_brightness"] = 2.5
        self.assertEqual(vp._live_change(), "brightness and rotate remembered")
        self.assertIsNone(vp.find_rig())

    def test_a_dial_on_a_standing_studio_retunes_it(self):
        vp._press_setup()
        self.scene.vars["skeldarVpStudio_rotate"] = 90.0
        self.assertIn("rotate 90", vp._live_change())
        self.assertEqual(self.scene.by_path("|VPStudio|VPStudio_lights").attrs["rotateY"], 90.0)

    def test_a_look_picked_with_no_studio_is_only_remembered(self):
        self.scene.vars["skeldarVpStudio_look"] = "Soft Studio"
        self.assertEqual(vp._menu_change(), "Soft Studio look remembered")
        self.assertIsNone(vp.find_rig())

    def test_a_look_picked_on_a_standing_studio_rebuilds_it(self):
        vp._press_setup()
        self.scene.vars["skeldarVpStudio_look"] = "Soft Studio"
        self.assertTrue(vp._menu_change().startswith("Soft Studio on - 6 lights, cyclorama"))
        self.assertEqual(vp.read_options(vp.find_rig())["look"], "Soft Studio")

    def test_a_press_that_fails_puts_its_error_on_the_line_and_raises(self):
        def broken(options=None, undoable=True):
            raise RuntimeError("no hardwareRenderingGlobals")
        with mock.patch.object(vp, "setup", broken):
            with self.assertRaises(RuntimeError):
                vp._press_setup()
        self.assertEqual(self.scene.messages[-1], "RuntimeError: no hardwareRenderingGlobals")


if __name__ == "__main__":
    unittest.main()
