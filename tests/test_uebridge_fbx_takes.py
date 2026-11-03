"""The listing's take read: `formats.fbx_takes`.

2026-11-03, the animator: «Я нажал на обновление списка файлов в animation
setup и теперь у меня создаюстся какие-то 14 тысяч файлов?» Nothing was
created (the scan only reads), but the investigation found this: the path
went into `FBXRead` inside a MEL STRING, and MEL cannot carry a non-ASCII
path - every file under a folder with a Russian name was refused with «Use
syntax: FBXRead -f filename» and listed with no takes and no frames. Half
the animator's own Downloads (5 874 of 11 580 fbx) are such files.

Measured in mayapy 2027 that day, on their own files:

    cmds.FBXRead("-f", path)   ok for an ASCII path AND for a Cyrillic one
    cmds.FBXRead(path)         «Use syntax: FBXRead -f filename»
    cmds.FBXRead(f=path)       «Use syntax: FBXRead -f filename»
    mel.eval('FBXRead -f "..."')  ok for ASCII, REFUSED for Cyrillic

So the flag is passed positionally as its own string, and the command then
carries whatever Python holds. Both roads answer the same takes for an
ASCII file and cost the same (0.8 ms a file over 200 of them), so the read
is the cmds one for every path.
"""

import sys
import types
import unittest


def _install_fake_maya():
    # the real package wins where it imports (trap 60)
    try:
        import maya.cmds  # noqa: F401
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

from maya_uebridge import formats  # noqa: E402


class FakeCommands(object):
    """The FBX plugin's listing commands, as mayapy answers them: the file is
    read by `FBXRead("-f", path)` and the takes are asked by index."""

    def __init__(self, takes=(), refuse_mel_paths=False):
        self.takes = list(takes)        # (name, start, end)
        self.calls = []
        self.read = None

    def FBXRead(self, *args, **kwargs):
        self.calls.append(("FBXRead", args, kwargs))
        if len(args) != 2 or args[0] != "-f" or kwargs:
            raise RuntimeError("Use syntax: FBXRead -f filename")
        self.read = args[1]

    def FBXGetTakeCount(self, *args, **kwargs):
        self.calls.append(("FBXGetTakeCount", args, kwargs))
        return len(self.takes)

    def FBXGetTakeName(self, index, *args, **kwargs):
        self.calls.append(("FBXGetTakeName", (index,), kwargs))
        return self.takes[index - 1][0]

    def FBXGetTakeLocalTimeSpan(self, index, *args, **kwargs):
        self.calls.append(("FBXGetTakeLocalTimeSpan", (index,), kwargs))
        return list(self.takes[index - 1][1:])


class RefusingMel(object):
    """MEL as it answers a non-ASCII path: a string it cannot carry."""

    def __init__(self):
        self.calls = []

    def eval(self, text):
        self.calls.append(text)
        if not all(ord(c) < 128 for c in text):
            raise RuntimeError("Error occurred during execution of MEL script")
        raise AssertionError("the take read must not go through MEL: " + text)


class TakeRead(unittest.TestCase):

    def setUp(self):
        self.fake = FakeCommands([("Take 001", 0.0, 80.0)])
        self.mel = RefusingMel()
        self.old_cmds = formats.cmds
        self.old_mel = formats.mel
        self.old_ensure = formats.animimport.ensure_fbx_plugin
        formats.cmds = self.fake
        formats.mel = self.mel
        formats.animimport.ensure_fbx_plugin = lambda: None

    def tearDown(self):
        formats.cmds = self.old_cmds
        formats.mel = self.old_mel
        formats.animimport.ensure_fbx_plugin = self.old_ensure

    def test_a_cyrillic_path_is_read(self):
        """The animator's own case: 5 874 files under «Модуль V. Мультиплеер»
        came back with no takes."""
        path = "C:/Users/MY PC/Downloads/Конец урока (1)/aura_flat.FBX"
        self.assertEqual(formats.fbx_takes(path),
                         [(1, "Take 001", 0.0, 80.0)])
        self.assertEqual(self.fake.read, path)

    def test_the_flag_is_passed_positionally(self):
        """`cmds.FBXRead(f=path)` and a bare path are both refused."""
        formats.fbx_takes("C:/a/walk.fbx")
        self.assertEqual(self.fake.calls[0],
                         ("FBXRead", ("-f", "C:/a/walk.fbx"), {}))

    def test_a_backslash_path_is_read_with_forward_slashes(self):
        formats.fbx_takes("C:\\a\\walk.fbx")
        self.assertEqual(self.fake.read, "C:/a/walk.fbx")

    def test_the_take_read_never_goes_through_mel(self):
        formats.fbx_takes("C:/a/walk.fbx")
        self.assertEqual(self.mel.calls, [])

    def test_several_takes_come_back_in_order(self):
        self.fake.takes = [("bind", 0.0, 0.0), ("walk", 0.0, 24.0)]
        self.assertEqual(formats.fbx_takes("C:/a/pack.fbx"),
                         [(1, "bind", 0.0, 0.0), (2, "walk", 0.0, 24.0)])

    def test_a_file_the_plugin_cannot_read_answers_no_takes(self):
        def refuse(*args, **kwargs):
            raise RuntimeError("file not found")
        self.fake.FBXRead = refuse
        self.assertEqual(formats.fbx_takes("C:/a/gone.fbx"), [])

    def test_a_take_whose_span_cannot_be_read_keeps_its_row(self):
        def refuse(index, *args, **kwargs):
            raise RuntimeError("no span")
        self.fake.FBXGetTakeLocalTimeSpan = refuse
        self.assertEqual(formats.fbx_takes("C:/a/odd.fbx"),
                         [(1, "", None, None)])


if __name__ == "__main__":
    unittest.main()
