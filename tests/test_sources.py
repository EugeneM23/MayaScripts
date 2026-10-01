"""Everything the plugin and its asset scripts need lives in the repository
(2026-09-28, «все нужные файлы для работы нашего плагина давай перенесем в
папку плагина»).

- The plugin names no path outside its own folder: every weapon, texture,
  character and the OverRig MEL resolve inside SkeldarAnim/, and no string in
  its code points at the animator's Animations/ or Downloads/.
- The sources the asset scripts rebuild from live in sources/, BESIDE the
  plugin - in git, never in a build - and the scripts read them there.
- AdvancedSkeleton sits in sources/ too but stays out of git: its licence
  forbids redistributing the software, and the repository is public.
"""

import ast
import glob
import os
import subprocess
import unittest

import install
from maya_overrig import overrig
from maya_scenesetup import catalog

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN = os.path.join(REPO, "SkeldarAnim")
SOURCES = os.path.join(REPO, "sources")
PLANS = os.path.join(REPO, "docs", "superpowers", "plans")
SOURCES_URL = "C:/!!!Work/MayaScripts/sources/"

# Where the moved files lived before 2026-09-28. No script may read them there.
OLD_HOMES = ("Downloads/Spear_03", "Downloads/Halberd_A",
             "Animations/Sources/Dagger", "Animations/Sources/SK_Orc_Marauder_F",
             "Downloads/creep_T-pose_draft", "Downloads/AdvancedSkeleton",
             "Rigs/Characters/Manny_rig_02")

# What sources/ holds in git.
TRACKED = ("weapons/Spear_03.fbx", "weapons/Halberd_A.tga", "weapons/Dagger.fbx",
           "orc/SK_Orc_Marauder_F.FBX", "creep/creep_T-pose_draft.fbx",
           "manny/Manny_rig_02.ma", "armor/SM_Shield_Test.fbx", "armor/techlimb_ue.json")


def _inside(path, folder):
    path = os.path.normcase(os.path.abspath(path))
    folder = os.path.normcase(os.path.abspath(folder))
    return path.startswith(folder + os.sep)


def _strings(path, docstrings=True):
    """Every string constant in a Python file."""
    with open(path, encoding="utf-8") as handle:
        tree = ast.parse(handle.read())
    skip = set()
    if not docstrings:
        for node in ast.walk(tree):
            body = getattr(node, "body", None)
            if isinstance(body, list) and body and isinstance(body[0], ast.Expr) \
                    and isinstance(getattr(body[0], "value", None), ast.Constant):
                skip.add(id(body[0].value))
    return [node.value for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
            and id(node) not in skip]


def _plugin_code():
    return [path for path in glob.glob(os.path.join(PLUGIN, "**", "*.py"),
                                       recursive=True)
            if "__pycache__" not in path]


def _scripts():
    return sorted(glob.glob(os.path.join(PLANS, "*.py")))


def _git(*args):
    return subprocess.run(("git",) + args, cwd=REPO, capture_output=True,
                          text=True)


class ThePluginIsSelfContained(unittest.TestCase):

    def test_every_weapon_and_its_texture_is_inside_the_plugin(self):
        for entry in catalog.WEAPONS:
            self.assertTrue(_inside(entry.path, PLUGIN), entry.path)
            if entry.texture:
                self.assertTrue(_inside(entry.texture, PLUGIN), entry.texture)

    def test_every_character_is_inside_the_plugin(self):
        for entry in catalog.CHARACTERS:
            path = catalog.character_file(entry)
            self.assertTrue(_inside(path, PLUGIN), path)
            self.assertTrue(os.path.isfile(path), path)

    def test_overrig_is_looked_for_inside_the_plugin_only(self):
        for path in overrig.MEL_CANDIDATES:
            self.assertTrue(_inside(path, PLUGIN), path)

    def test_no_code_points_at_the_animators_folders(self):
        """Usage lines in docstrings name the repo; code names nothing
        outside the plugin."""
        for path in _plugin_code():
            for text in _strings(path, docstrings=False):
                for folder in ("Animations/", "Downloads"):
                    self.assertNotIn(folder, text, "%s: %r" % (path, text))


class TheSources(unittest.TestCase):

    def test_they_live_beside_the_plugin_and_never_ship(self):
        self.assertTrue(os.path.isdir(SOURCES))
        self.assertFalse(_inside(SOURCES, PLUGIN))
        self.assertNotIn("sources", install.payload())

    def test_every_tracked_source_is_there_and_in_git(self):
        listed = _git("ls-files", "sources").stdout.split()
        for name in TRACKED:
            self.assertTrue(os.path.isfile(os.path.join(SOURCES, name)), name)
            self.assertIn("sources/" + name, listed, name)

    def test_the_readme_names_every_source(self):
        with open(os.path.join(SOURCES, "README.md"), encoding="utf-8") as handle:
            text = handle.read()
        for name in TRACKED + ("AdvancedSkeleton",):
            self.assertIn(os.path.basename(name), text, name)

    def test_advancedskeleton_stays_out_of_git(self):
        """Its licence: «You may not resell, redistribute, or sublicense
        the software itself» - and the repository is public."""
        probe = "sources/AdvancedSkeleton/AdvancedSkeleton.mel"
        self.assertEqual(_git("check-ignore", "-q", probe).returncode, 0)
        self.assertEqual(_git("ls-files", "sources/AdvancedSkeleton").stdout, "")

    def test_an_fbm_extraction_stays_out_of_git(self):
        """Importing the Creep's FBX extracts its embedded textures into a
        .fbm folder beside it; the FBX holds them already."""
        probe = "sources/creep/creep_T-pose_draft.fbm/0.jpg"
        self.assertEqual(_git("check-ignore", "-q", probe).returncode, 0)


class TheScriptsReadThem(unittest.TestCase):

    def test_no_script_reads_a_source_at_its_old_home(self):
        for path in _scripts():
            for text in _strings(path):
                for old in OLD_HOMES:
                    self.assertNotIn(old, text.replace("\\", "/"),
                                     "%s: %r" % (os.path.basename(path), text))

    def test_every_sources_path_a_script_names_exists(self):
        named = set()
        for path in _scripts():
            for text in _strings(path):
                start = text.find(SOURCES_URL)
                while start >= 0:
                    tail = text[start + len(SOURCES_URL):]
                    end = min([i for i in (tail.find('"'), tail.find(" "),
                                           tail.find("\n"), tail.find("'"))
                               if i >= 0] or [len(tail)])
                    named.add(tail[:end].rstrip(".,)`"))
                    start = text.find(SOURCES_URL, start + 1)
        self.assertTrue(named)
        for name in named:
            if name.startswith("AdvancedSkeleton") and not os.path.isdir(
                    os.path.join(SOURCES, "AdvancedSkeleton")):
                continue            # local only: a fresh clone has none
            self.assertTrue(os.path.exists(os.path.join(SOURCES, name)), name)


if __name__ == "__main__":
    unittest.main()
