"""The writers Dynamics shares with the Tools card (2026-10-26): `layerbake.write_deltas(layer=)`
writes a standing layer again, `overlap.deltas_for` is `_chain_deltas`' conversion."""

import sys
import types
import unittest
from unittest import mock

try:
    import maya.cmds  # noqa: F401
except ImportError:
    maya = types.ModuleType("maya")
    maya.cmds = types.ModuleType("maya.cmds")
    sys.modules.setdefault("maya", maya)
    sys.modules.setdefault("maya.cmds", maya.cmds)

from maya_tools import layerbake  # noqa: E402
from maya_tools import overlap  # noqa: E402


class FakeCmds(object):
    """Just enough of cmds for write_deltas: layers holding plugs, a curve per keyed plug."""

    def __init__(self, layers=None):
        self.layers = dict((name, list(plugs)) for name, plugs in (layers or {}).items())
        self.made = []
        self.keys = {}
        self.attrs = {}

    def objExists(self, node):
        return node in self.layers

    def nodeType(self, node):
        return "animLayer" if node in self.layers else "transform"

    def animLayer(self, name=None, query=False, edit=False, attribute=None, removeAttribute=None,
                  findCurveForPlug=None):
        if query and attribute:
            return list(self.layers[name])
        if query and findCurveForPlug:
            return ["curve:" + findCurveForPlug]
        if edit and removeAttribute:
            self.layers[name].remove(removeAttribute)
            self.keys.pop("curve:" + removeAttribute, None)
            return None
        if edit and attribute:
            self.layers[name].extend(p for p in attribute if p not in self.layers[name])
            return None
        self.layers[name] = []
        self.made.append(name)
        return name

    def setAttr(self, plug, value):
        self.attrs[plug] = value

    def setKeyframe(self, target, attribute=None, animLayer=None, time=None, value=None,
                    identity=False, **kw):
        if identity:
            return
        self.keys.setdefault(target, {})[time] = value

    def keyTangent(self, *args, **kwargs):
        pass


class WriteAgain(unittest.TestCase):

    def run_writer(self, fake, **kwargs):
        with mock.patch.object(layerbake, "cmds", fake), \
                mock.patch.object(layerbake.knots, "_set_string"):
            return layerbake.write_deltas("Dynamics_hair", "skeldarDynamics", "u1",
                                          {("hair_01", "rx"): ([0, 1, 2], [0.0, 1.0, 2.0])},
                                          **kwargs)

    def test_without_a_layer_it_makes_one(self):
        fake = FakeCmds()
        self.assertEqual(self.run_writer(fake), "Dynamics_hair")
        self.assertEqual(fake.made, ["Dynamics_hair"])
        self.assertEqual(fake.keys["curve:hair_01.rotateX"], {0: 0.0, 1: 1.0, 2: 2.0})

    def test_a_standing_layer_is_written_again_in_place(self):
        fake = FakeCmds({"Dynamics_hair3": ["hair_01.rotateX", "hair_02.rotateY"]})
        fake.keys["curve:hair_01.rotateX"] = {0: 9.0, 5: 9.0}
        layer = self.run_writer(fake, layer="Dynamics_hair3")
        self.assertEqual(layer, "Dynamics_hair3")
        self.assertEqual(fake.made, [])
        # the plug it held and no longer keys left it; the old keys went with their curve
        self.assertEqual(fake.layers["Dynamics_hair3"], ["hair_01.rotateX"])
        self.assertEqual(fake.keys["curve:hair_01.rotateX"], {0: 0.0, 1: 1.0, 2: 2.0})

    def test_a_layer_that_is_gone_is_made_again(self):
        fake = FakeCmds()
        self.assertEqual(self.run_writer(fake, layer="Dynamics_gone"), "Dynamics_hair")
        self.assertEqual(fake.made, ["Dynamics_hair"])


class Split(unittest.TestCase):

    def test_chain_deltas_hands_its_solve_to_deltas_for(self):
        self.assertTrue(callable(overlap.deltas_for))
        import inspect
        source = inspect.getsource(overlap._chain_deltas)
        self.assertIn("return deltas_for(chain, data, frames, new, out, weights)", source)


if __name__ == "__main__":
    unittest.main()
