"""maya_ragdoll.sim - Cached Playback is off while the ragdoll's nodes stand (2026-10-17).

With the cache on, Bullet does not step in a GUI Maya at all: a Fall left the character
standing. `sim.Scene` switches the cache off before it makes its first node and back on once
`delete` has taken them."""

import unittest

from maya_ragdoll import sim


class FakeCmds(object):
    """Enough of `maya.cmds` for `Scene.__init__` / `delete`, every call logged in order."""

    def __init__(self, cache=True, has_cache=True, fail_on=None):
        self.cache = cache
        self.has_cache = has_cache
        self.fail_on = fail_on
        self.log = []

    def evaluator(self, name=None, query=False, enable=None):
        if not self.has_cache:
            raise RuntimeError("no evaluator named cache")
        if query:
            return self.cache
        self.log.append(("cache", enable))
        self.cache = enable
        return None

    def pluginInfo(self, *args, **kw):
        return True

    def loadPlugin(self, *args, **kw):
        return None

    def ls(self, *args, **kw):
        return []

    def createNode(self, kind, name=None, **kw):
        if kind == self.fail_on:
            raise RuntimeError("cannot make a %s" % kind)
        self.log.append(("node", kind))
        return name or kind

    def connectAttr(self, *args, **kw):
        return None

    def setAttr(self, *args, **kw):
        return None


class CacheOff(unittest.TestCase):

    def setUp(self):
        self.real = sim.cmds

    def tearDown(self):
        sim.cmds = self.real

    def fake(self, **kw):
        sim.cmds = FakeCmds(**kw)
        return sim.cmds

    def test_the_cache_goes_off_before_the_first_node_and_back_on_after_delete(self):
        cmds = self.fake(cache=True)
        world = sim.Scene(0, 0.8, 0.1)
        self.assertEqual(cmds.log[0], ("cache", False))
        self.assertIn(("node", "bulletSolverShape"), cmds.log)
        self.assertFalse(cmds.cache)
        world.delete()
        self.assertTrue(cmds.cache)
        self.assertEqual(cmds.log[-1], ("cache", True))

    def test_a_cache_that_was_off_is_never_touched(self):
        cmds = self.fake(cache=False)
        sim.Scene(0, 0.8, 0.1).delete()
        self.assertFalse(cmds.cache)
        self.assertFalse([entry for entry in cmds.log if entry[0] == "cache"])

    def test_no_cache_evaluator_to_ask_builds_and_deletes(self):
        cmds = self.fake(has_cache=False)
        sim.Scene(0, 0.8, 0.1).delete()
        self.assertIn(("node", "bulletSolverShape"), cmds.log)

    def test_a_build_that_fails_puts_the_cache_back(self):
        cmds = self.fake(cache=True, fail_on="bulletSolverShape")
        with self.assertRaises(RuntimeError):
            sim.Scene(0, 0.8, 0.1)
        self.assertTrue(cmds.cache)

    def test_delete_twice_turns_the_cache_on_once(self):
        cmds = self.fake(cache=True)
        world = sim.Scene(0, 0.8, 0.1)
        world.delete()
        world.delete()
        self.assertEqual([entry for entry in cmds.log if entry[0] == "cache"],
                         [("cache", False), ("cache", True)])


if __name__ == "__main__":
    unittest.main()
