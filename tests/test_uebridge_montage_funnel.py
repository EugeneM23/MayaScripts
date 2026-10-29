"""The import funnel's montage branch.

`rigimport.import_source` is the one door every road goes through - the
button, the double click, the drag, the square, Auto - so a montage reference
has to be answered there and nowhere else.
"""

import sys
import types
import unittest


def _install_fake_maya():
    """Let rigimport import without Maya. See CLAUDE.md on rebinding."""
    try:
        import maya.cmds  # noqa: F401
        import maya.mel  # noqa: F401
        return
    except ImportError:
        pass
    if "maya.cmds" in sys.modules:
        return
    maya = types.ModuleType("maya")
    cmds = types.ModuleType("maya.cmds")
    mel = types.ModuleType("maya.mel")
    maya.cmds = cmds
    maya.mel = mel
    sys.modules.setdefault("maya", maya)
    sys.modules["maya.cmds"] = cmds
    sys.modules["maya.mel"] = mel


_install_fake_maya()

from maya_uebridge import rigimport  # noqa: E402


class FakeCmds(object):
    def namespaceInfo(self, *_a, **_k):
        return ["|AM_X_1P:root", "|AM_X_1P:root|AM_X_1P:pelvis"]

    def objectType(self, *_a, **_k):
        return "joint"


class FakeAnim(object):
    def __init__(self):
        self.calls = []

    def existing_namespaces(self):
        return set()

    def import_clip(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return {"namespace": "x"}


class FakeMontage(object):
    def __init__(self):
        self.calls = []

    def is_ref(self, text):
        return bool(text) and str(text).startswith("montage:")

    def import_clip(self, ref, namespace, **kwargs):
        self.calls.append((ref, namespace, kwargs))
        return {"namespace": namespace, "montage": {"name": "AM_X",
                                                    "slot": "1P"}}


class Funnel(unittest.TestCase):
    def setUp(self):
        self.held = (rigimport.cmds, rigimport.animimport, rigimport.montage)
        self.anim = FakeAnim()
        self.montage = FakeMontage()
        rigimport.cmds = FakeCmds()
        rigimport.animimport = self.anim
        rigimport.montage = self.montage

    def tearDown(self):
        (rigimport.cmds, rigimport.animimport,
         rigimport.montage) = self.held

    def test_a_montage_reference_goes_to_the_montage_importer(self):
        namespace, info, source = rigimport.import_source(
            "montage:C:/t/montage_AM_X_1P.json", "AM_X_1P", clip_fps=30.0)
        self.assertEqual(len(self.montage.calls), 1)
        ref, given, kwargs = self.montage.calls[0]
        self.assertEqual(ref, "montage:C:/t/montage_AM_X_1P.json")
        self.assertEqual(given, namespace)
        self.assertEqual(kwargs.get("clip_fps"), 30.0)
        self.assertEqual(info["namespace"], namespace)
        self.assertEqual(source, "|AM_X_1P:root")

    def test_the_namespace_is_the_one_the_name_asks_for(self):
        namespace, _info, _source = rigimport.import_source(
            "montage:C:/t/p.json", "AM_X_1P")
        self.assertEqual(namespace, "AM_X_1P")

    def test_a_montage_reference_never_reaches_animimport(self):
        rigimport.import_source("montage:C:/t/p.json", "AM_X_1P")
        self.assertEqual(self.anim.calls, [])

    def test_the_timeline_flag_travels(self):
        rigimport.import_source("montage:C:/t/p.json", "AM_X_1P",
                                set_timeline=False)
        self.assertIs(self.montage.calls[0][2].get("set_timeline"), False)

    def test_a_plain_fbx_still_goes_to_animimport(self):
        rigimport.import_source("C:/t/A_Jump.fbx", "A_Jump")
        self.assertEqual(len(self.anim.calls), 1)
        self.assertEqual(self.montage.calls, [])


if __name__ == "__main__":
    unittest.main()
