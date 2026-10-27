"""The Time Bar's key reads over the selection (`scene._kq`, `scene._on`) with a
geometry shape under it (2026-10-27): Maya's `-shape` walk combs a skinned mesh's
every plug - a selected character mesh cost 0.9-1.0 s a query, twice a selection -
so with geometry the selection is named explicitly, `shape=False`, plus the curves
that key its shapes directly."""
import unittest

from maya_timebar import scene


class FakeCmds(object):
    """A selection of transforms over shapes; `keyframe` and the key commands record
    what they were asked with."""

    def __init__(self, selection, shapes=None, types=None, keyed=None):
        self.selection = list(selection)
        self.shapes = dict(shapes or {})          # transform -> [shapes]
        self.types = dict(types or {})            # node -> type
        self.keyed = dict(keyed or {})            # "shape.attr" -> curve
        self.calls = []

    def _type(self, node):
        return self.types.get(node, "transform")

    def ls(self, *args, **kw):
        if kw.get("selection"):
            return list(self.selection)
        nodes = list(args[0]) if args else []
        if kw.get("shapes"):
            return [n for n in nodes if n in sum(self.shapes.values(), [])]
        if kw.get("transforms"):
            return [n for n in nodes if n in self.shapes or self._type(n) == "transform"]
        if "type" in kw:
            want = kw["type"]
            want = (want,) if isinstance(want, str) else tuple(want)
            return [n for n in nodes if self._type(n) in want]
        return nodes

    def listRelatives(self, nodes, shapes=False, fullPath=False, type=None):
        out = []
        for n in nodes:
            out.extend(self.shapes.get(n, []))
        if type is not None:
            want = (type,) if isinstance(type, str) else tuple(type)
            out = [n for n in out if self._type(n) in want]
        return out or None

    def listConnections(self, nodes, source=True, destination=False, type=None,
                        connections=False, plugs=False):
        out = []
        for plug, curve in sorted(self.keyed.items()):
            if plug.split(".")[0] in nodes:
                out.extend([plug, curve + ".output"])
        return out

    def keyframe(self, *args, **kw):
        self.calls.append(("keyframe", args, kw))
        return [1.0]

    def cutKey(self, *args, **kw):
        self.calls.append(("cutKey", args, kw))

    def pasteKey(self, *args, **kw):
        self.calls.append(("pasteKey", args, kw))


class GeometryTargets(unittest.TestCase):

    def setUp(self):
        self._cmds, self._scope = scene.cmds, scene._scope
        scene._scope = lambda: None                     # no animation layers

    def tearDown(self):
        scene.cmds, scene._scope = self._cmds, self._scope

    def use(self, fake):
        scene.cmds = fake
        return fake

    def test_controls_keep_maya_s_own_walk(self):
        fake = self.use(FakeCmds(["|ctrl"], shapes={"|ctrl": ["|ctrl|ctrlShape"]},
                                 types={"|ctrl|ctrlShape": "nurbsCurve"}))
        self.assertIsNone(scene._geometry_targets())
        scene._kq(timeChange=True)
        self.assertEqual(fake.calls, [("keyframe", (), {"q": True, "timeChange": True})])

    def test_nothing_selected_is_maya_s_own(self):
        self.use(FakeCmds([]))
        self.assertIsNone(scene._geometry_targets())

    def test_a_mesh_is_named_with_no_shape_walk(self):
        fake = self.use(FakeCmds(["|body"], shapes={"|body": ["|body|bodyShape"]},
                                 types={"|body|bodyShape": "mesh"}))
        self.assertEqual(scene._geometry_targets(), ["|body"])
        scene._kq(timeChange=True)
        self.assertEqual(fake.calls, [("keyframe", (["|body"],),
                                       {"q": True, "shape": False, "timeChange": True})])

    def test_a_keyed_shape_attribute_still_counts_controlpoints_do_not(self):
        fake = self.use(FakeCmds(
            ["|body"], shapes={"|body": ["|body|bodyShape"]},
            types={"|body|bodyShape": "mesh"},
            keyed={"|body|bodyShape.visibility": "bodyShape_visibility",
                   "|body|bodyShape.controlPoints[3].xValue": "bodyShape_pnt3",
                   "|body|bodyShape.pnts[2].pntx": "bodyShape_pnts2"}))
        self.assertEqual(scene._geometry_targets(), ["|body", "bodyShape_visibility"])

    def test_a_selected_mesh_shape_is_replaced_by_its_curves(self):
        self.use(FakeCmds(["|body|bodyShape"], shapes={"|body": ["|body|bodyShape"]},
                          types={"|body|bodyShape": "mesh"},
                          keyed={"|body|bodyShape.visibility": "vis"}))
        self.assertEqual(scene._geometry_targets(), ["vis"])

    def test_mixed_selection_keeps_every_node_once(self):
        self.use(FakeCmds(["|ctrl", "|body"],
                          shapes={"|ctrl": ["|ctrl|ctrlShape"], "|body": ["|body|bodyShape"]},
                          types={"|ctrl|ctrlShape": "nurbsCurve", "|body|bodyShape": "mesh"}))
        self.assertEqual(scene._geometry_targets(), ["|ctrl", "|body"])

    def test_key_commands_go_to_the_named_targets(self):
        fake = self.use(FakeCmds(["|body"], shapes={"|body": ["|body|bodyShape"]},
                                 types={"|body|bodyShape": "mesh"}))
        scene._on(fake.cutKey, time=(0, 5), option="keys")
        self.assertEqual(fake.calls, [("cutKey", (["|body"],),
                                       {"shape": False, "time": (0, 5), "option": "keys"})])

    def test_paste_keeps_maya_s_own_targets(self):
        fake = self.use(FakeCmds(["|body"], shapes={"|body": ["|body|bodyShape"]},
                                 types={"|body|bodyShape": "mesh"}))
        scene.cmds.pasteKey = fake.pasteKey
        scene._on(scene.cmds.pasteKey, time=(3,), option="merge")
        self.assertEqual(fake.calls, [("pasteKey", (), {"time": (3,), "option": "merge"})])

    def test_keys_reads_through_the_targets(self):
        fake = self.use(FakeCmds(["|body"], shapes={"|body": ["|body|bodyShape"]},
                                 types={"|body|bodyShape": "mesh"}))
        self.assertEqual(scene.keys(), ([], [1.0]))        # the fake answers 1.0 to both
        self.assertEqual(len(fake.calls), 2)
        for name, args, kw in fake.calls:
            self.assertEqual(args, (["|body"],))
            self.assertFalse(kw["shape"])


if __name__ == "__main__":
    unittest.main()
