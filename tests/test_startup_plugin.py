"""The startup plug-in: the edge panel waiting from Maya's start (2026-10-08).

`SkeldarAnim/plug-ins/skeldarAnimStartup.py` is loaded by Maya at startup
(the installer sets it to autoload) and defers `maya_hub.start()`. It must
import with stdlib alone - its Maya imports live inside the functions - so
these tests load it with fakes and no Maya.
"""

import importlib.util
import os
import subprocess
import sys
import types
import unittest

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                    "SkeldarAnim", "plug-ins", "skeldarAnimStartup.py")


def _load(batch=False, hub=None):
    """The plug-in loaded and initialized against fake Maya modules.
    Answers the module and the calls handed to executeDeferred."""
    calls = []
    plugins = []
    fake_cmds = types.SimpleNamespace(about=lambda **k: batch)
    fake_utils = types.SimpleNamespace(
        executeDeferred=lambda fn: calls.append(fn))
    fake_om = types.SimpleNamespace(
        MFnPlugin=lambda *a, **k: plugins.append(a))
    names = ("maya", "maya.cmds", "maya.utils", "maya.api",
             "maya.api.OpenMaya", "maya_hub")
    saved = {k: sys.modules.get(k) for k in names}
    maya = types.ModuleType("maya")
    maya.cmds, maya.utils = fake_cmds, fake_utils
    api = types.ModuleType("maya.api")
    api.OpenMaya = fake_om
    maya.api = api
    sys.modules.update({"maya": maya, "maya.cmds": fake_cmds,
                        "maya.utils": fake_utils, "maya.api": api,
                        "maya.api.OpenMaya": fake_om})
    if hub is not None:
        sys.modules["maya_hub"] = hub
    else:
        sys.modules.pop("maya_hub", None)
    try:
        spec = importlib.util.spec_from_file_location("skStartupTest", PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.initializePlugin(object())
        module._plugins = plugins
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v
    return module, calls


class _Hub(types.ModuleType):
    """A stand-in maya_hub: counts start() / stop(), raises on request."""

    def __init__(self, fail=False):
        types.ModuleType.__init__(self, "maya_hub")
        self.started = 0
        self.stopped = 0
        self.fail = fail

    def start(self):
        self.started += 1
        if self.fail:
            raise RuntimeError("no hub today")

    def stop(self):
        self.stopped += 1
        if self.fail:
            raise RuntimeError("no hub today")
        return False


class StartupPlugin(unittest.TestCase):

    def test_it_defers_the_start_in_a_gui_maya(self):
        module, calls = _load(batch=False)
        self.assertEqual(len(calls), 1)
        self.assertTrue(hasattr(module, "maya_useNewAPI"))

    def test_nothing_in_batch(self):
        _module, calls = _load(batch=True)
        self.assertEqual(calls, [])

    def test_it_registers_itself_with_maya(self):
        """MFnPlugin on the plug-in object: a vendor and a version, no node
        and no command."""
        module, _calls = _load()
        self.assertEqual(len(module._plugins), 1)
        self.assertEqual(module._plugins[0][1:], ("SkeldarAnim", "1.0"))

    def test_its_plugin_folder_is_the_installed_skeldaranim(self):
        module, _calls = _load()
        self.assertEqual(os.path.basename(module.PLUGIN_DIR), "SkeldarAnim")
        self.assertTrue(os.path.isfile(os.path.join(module.PLUGIN_DIR,
                                                    "maya_hub.py")))

    def test_the_deferred_start_calls_the_hub_with_the_folder_on_the_path(self):
        hub = _Hub()
        module, calls = _load(hub=hub)
        saved = list(sys.path)
        sys.modules["maya_hub"] = hub
        try:
            calls[0]()
            self.assertIn(module.PLUGIN_DIR, sys.path)
        finally:
            sys.path[:] = saved
            sys.modules.pop("maya_hub", None)
        self.assertEqual(hub.started, 1)

    def test_a_hub_that_fails_to_start_is_printed_not_raised(self):
        hub = _Hub(fail=True)
        _module, calls = _load(hub=hub)
        saved = list(sys.path)
        sys.modules["maya_hub"] = hub
        try:
            calls[0]()
        finally:
            sys.path[:] = saved
            sys.modules.pop("maya_hub", None)
        self.assertEqual(hub.started, 1)

    def test_unloading_stops_the_hub(self):
        hub = _Hub()
        module, _calls = _load()
        sys.modules["maya_hub"] = hub
        saved = sys.modules.get("maya.api.OpenMaya")
        fake_om = types.SimpleNamespace(MFnPlugin=lambda *a, **k: None)
        api = types.ModuleType("maya.api")
        api.OpenMaya = fake_om
        saved_api = sys.modules.get("maya.api")
        saved_maya = sys.modules.get("maya")
        maya = types.ModuleType("maya")
        maya.api = api
        sys.modules.update({"maya": maya, "maya.api": api,
                            "maya.api.OpenMaya": fake_om})
        try:
            module.uninitializePlugin(object())
        finally:
            sys.modules.pop("maya_hub", None)
            for name, value in (("maya", saved_maya), ("maya.api", saved_api),
                                ("maya.api.OpenMaya", saved)):
                if value is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = value
        self.assertEqual(hub.stopped, 1)

    def test_unloading_without_a_hub_loaded_imports_nothing(self):
        """Never imported maya_hub (a batch Maya, a start that failed before
        the import): unloading leaves it unimported."""
        module, _calls = _load(batch=True)
        sys.modules.pop("maya_hub", None)
        fake_om = types.SimpleNamespace(MFnPlugin=lambda *a, **k: None)
        api = types.ModuleType("maya.api")
        api.OpenMaya = fake_om
        maya = types.ModuleType("maya")
        maya.api = api
        saved = {k: sys.modules.get(k) for k in
                 ("maya", "maya.api", "maya.api.OpenMaya")}
        sys.modules.update({"maya": maya, "maya.api": api,
                            "maya.api.OpenMaya": fake_om})
        try:
            module.uninitializePlugin(object())
            self.assertNotIn("maya_hub", sys.modules)
        finally:
            for k, v in saved.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v

    def test_under_maya_s_loader_it_asks_pluginInfo_for_its_path(self):
        """Maya runs a Python plug-in with neither __file__ nor __name__ in
        its globals (measured 2026-10-08): the text must load that way, and
        initializePlugin finds the folder through `pluginInfo -path`. Run
        from the user's plug-ins folder (the installer's copy), the folder
        is the installed SkeldarAnim under userAppDir/scripts."""
        with open(PATH, encoding="utf-8") as handle:
            source = handle.read()
        space = {"__builtins__": __builtins__}
        exec(compile(source, "<maya>", "exec"), space)
        self.assertEqual(space["PLUGIN_DIR"], "")
        asked = []
        fake_cmds = types.SimpleNamespace(
            about=lambda **k: True,
            pluginInfo=lambda name, **k: asked.append(name) or
            "C:/u/maya/2027/plug-ins/skeldarAnimStartup.py",
            internalVar=lambda **k: "C:/u/maya/")
        fake_om = types.SimpleNamespace(MFnPlugin=lambda *a, **k: None)
        api = types.ModuleType("maya.api")
        api.OpenMaya = fake_om
        maya = types.ModuleType("maya")
        maya.cmds, maya.api = fake_cmds, api
        names = ("maya", "maya.cmds", "maya.api", "maya.api.OpenMaya")
        saved = {k: sys.modules.get(k) for k in names}
        sys.modules.update({"maya": maya, "maya.cmds": fake_cmds,
                            "maya.api": api, "maya.api.OpenMaya": fake_om})
        try:
            space["initializePlugin"](object())
        finally:
            for k, v in saved.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v
        self.assertEqual(asked, ["skeldarAnimStartup"])
        self.assertEqual(space["PLUGIN_DIR"],
                         os.path.normpath("C:/u/maya/scripts/SkeldarAnim"))

    def test_the_folder_rule(self):
        module, _calls = _load()
        repo = module.plugin_dir(PATH, "C:/u/maya/")
        self.assertTrue(os.path.isfile(os.path.join(repo, "maya_hub.py")))
        self.assertEqual(
            module.plugin_dir("C:/u/maya/2027/plug-ins/skeldarAnimStartup.py",
                              "C:/u/maya/"),
            os.path.normpath("C:/u/maya/scripts/SkeldarAnim"))

    def test_a_start_with_no_skeldaranim_installed_says_so(self):
        """The copy in the user's plug-ins folder outlives a deleted
        SkeldarAnim folder: it prints and imports nothing."""
        module, calls = _load()
        module.PLUGIN_DIR = os.path.join(os.path.dirname(PATH), "nowhere")
        sys.modules.pop("maya_hub", None)
        saved = list(sys.path)
        try:
            calls[0]()
            self.assertNotIn("maya_hub", sys.modules)
            self.assertEqual(sys.path, saved)
        finally:
            sys.path[:] = saved

    def test_it_imports_with_stdlib_alone(self):
        """Maya loads it by path at startup, before anything of ours is on
        sys.path: importing it pulls in no Maya module and none of ours."""
        script = (
            "import importlib.util, sys\n"
            "spec = importlib.util.spec_from_file_location('skStartup', {0!r})\n"
            "m = importlib.util.module_from_spec(spec)\n"
            "spec.loader.exec_module(m)\n"
            "leaked = [n for n in sys.modules if n == 'maya' or n.startswith('maya.')\n"
            "          or n.startswith('maya_') or n.startswith('PySide')]\n"
            "print(';'.join(sorted(leaked)))\n").format(os.path.abspath(PATH))
        result = subprocess.run([sys.executable, "-c", script],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()
