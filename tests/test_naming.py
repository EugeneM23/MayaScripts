import sys
import types
import unittest


class FakeCmds(object):
    """Minimal stand-in for maya.cmds covering only what naming.py calls."""

    def __init__(self, joints=(), warnings=None):
        self._joints = list(joints)
        self.warnings = warnings if warnings is not None else []

    def ls(self, *args, **kwargs):
        return list(self._joints)

    def warning(self, message):
        self.warnings.append(message)


def install_fake_cmds(joints):
    """Point naming.py at a fake maya.cmds and return both.

    A stub `maya.cmds` is placed on sys.modules once so the module imports at
    all; after that each call rebinds `naming.cmds`. Re-importing instead would
    not work -- deleting sys.modules["maya_overrig.naming"] leaves the stale
    module bound as an attribute of the maya_overrig package, so the next
    `from maya_overrig import naming` hands back the old object still holding
    the previous fake.
    """
    fake = FakeCmds(joints)
    if "maya.cmds" not in sys.modules:
        maya_pkg = types.ModuleType("maya")
        maya_pkg.cmds = fake
        sys.modules["maya"] = maya_pkg
        sys.modules["maya.cmds"] = fake
    from maya_overrig import naming
    naming.cmds = fake
    return naming, fake


class TestLeaf(unittest.TestCase):

    def setUp(self):
        self.naming, _ = install_fake_cmds([])

    def test_strips_dag_path(self):
        self.assertEqual(self.naming.leaf("|root|pelvis|spine_01"), "spine_01")

    def test_strips_namespace(self):
        self.assertEqual(self.naming.leaf("|char:root|char:hand_l"), "hand_l")

    def test_plain_name_survives(self):
        self.assertEqual(self.naming.leaf("head"), "head")


class TestResolve(unittest.TestCase):

    def test_finds_bare_joint(self):
        naming, _ = install_fake_cmds(["|root|pelvis|spine_01"])
        self.assertEqual(naming.resolve("spine_01"), "|root|pelvis|spine_01")

    def test_finds_namespaced_joint(self):
        naming, _ = install_fake_cmds(["|char:root|char:hand_l"])
        self.assertEqual(naming.resolve("hand_l"), "|char:root|char:hand_l")

    def test_missing_joint_returns_none(self):
        naming, _ = install_fake_cmds(["|root"])
        self.assertIsNone(naming.resolve("hand_l"))

    def test_does_not_match_ue_helper_by_suffix(self):
        """The trap: `ik_hand_l` must never satisfy a request for `hand_l`."""
        naming, _ = install_fake_cmds(["|root|ik_hand_root|ik_hand_l"])
        self.assertIsNone(naming.resolve("hand_l"))

    def test_ambiguous_takes_first_and_warns(self):
        naming, fake = install_fake_cmds(["|a:root|a:head", "|b:root|b:head"])
        self.assertEqual(naming.resolve("head"), "|a:root|a:head")
        self.assertEqual(len(fake.warnings), 1)

    def test_resolve_many_skips_missing(self):
        naming, _ = install_fake_cmds(["|root|head"])
        found = naming.resolve_many(["head", "hand_l"])
        self.assertEqual(found, {"head": "|root|head"})


if __name__ == "__main__":
    unittest.main()
