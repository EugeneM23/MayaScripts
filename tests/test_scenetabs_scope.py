"""maya_scenetabs.scope: the plugin sees only the active tab (2026-10-15).

Spec: docs/superpowers/specs/2026-10-15-scene-tabs-plugin-scope-design.md
"""
import unittest

from maya_scenetabs import records, scope


def _state(*namespaces, active=None):
    state = records.empty_state()
    for ns in namespaces:
        state = records.with_tab(state, records.new_tab(ns, "C:/w/%s.ma" % ns[4:], "ntsc", {}))
    state["active"] = active or (namespaces[0] if namespaces else "")
    return state


class FakeCmds(object):
    """The session node, the namespaces and what was asked of them."""

    def __init__(self, state=None, namespaces=(), scene=""):
        self.text = records.dumps(state) if state is not None else None
        self.namespaces = set(namespaces)
        self.current = ":"
        self.scene = scene
        self.calls = []

    def objExists(self, name):
        return name == records.SESSION_NODE and self.text is not None

    def getAttr(self, plug):
        return self.text

    def file(self, *args, **kwargs):
        if kwargs.get("query") and kwargs.get("sceneName"):
            return self.scene
        self.calls.append(("file", args, kwargs))

    def namespace(self, exists=None, setNamespace=None, rename=None, parent=None):
        if exists is not None:
            return exists.lstrip(":") in self.namespaces
        if setNamespace is not None:
            self.current = setNamespace
            return None
        old, new = rename
        old = old.lstrip(":")
        self.namespaces.discard(old)
        whole = (parent.lstrip(":") + ":" + new) if parent else new
        self.namespaces.add(whole)
        self.calls.append(("rename", old, whole))

    def namespaceInfo(self, under, listOnlyNamespaces=False):
        prefix = under.lstrip(":") + ":"
        return [":" + n for n in self.namespaces if n.startswith(prefix) and ":" not in n[len(prefix):]]


class ActiveNamespace(unittest.TestCase):

    def test_no_session_is_no_tabs(self):
        self.assertEqual(scope.active_namespace(FakeCmds()), "")

    def test_one_tab_is_no_tabs(self):
        self.assertEqual(scope.active_namespace(FakeCmds(_state("tab_a"))), "")

    def test_two_tabs_answer_the_active_one(self):
        self.assertEqual(scope.active_namespace(FakeCmds(_state("tab_a", "tab_b", active="tab_b"))), "tab_b")

    def test_a_fake_that_raises_answers_no_tabs(self):
        class Broken(object):
            def objExists(self, name):
                raise RuntimeError("no Maya")
        self.assertEqual(scope.active_namespace(Broken()), "")


class Membership(unittest.TestCase):

    def test_a_paths_own_namespace(self):
        self.assertEqual(scope.own_namespace("|tab_a:Group|tab_a:Rig:Main"), "tab_a:Rig")
        self.assertEqual(scope.own_namespace("|root|pelvis"), "")

    def test_a_tab_does_not_hold_a_tab_whose_name_starts_like_it(self):
        self.assertTrue(scope.within("tab_a", "tab_a"))
        self.assertTrue(scope.within("tab_a:Rig", "tab_a"))
        self.assertFalse(scope.within("tab_ab", "tab_a"))
        self.assertFalse(scope.within("", "tab_a"))

    def test_everything_is_within_when_tabs_are_off(self):
        self.assertTrue(scope.within("tab_b:Rig", ""))

    def test_active_only_keeps_the_active_tabs_paths(self):
        cmds = FakeCmds(_state("tab_a", "tab_b", active="tab_a"))
        paths = ["|tab_a:root", "|tab_b:root", "|tab_a:G|tab_a:Rig:root", "|root"]
        self.assertEqual(scope.active_only(paths, cmds), ["|tab_a:root", "|tab_a:G|tab_a:Rig:root"])

    def test_active_only_keeps_everything_with_tabs_off(self):
        self.assertEqual(scope.active_only(["|tab_b:root", "|root"], FakeCmds()), ["|tab_b:root", "|root"])


class Names(unittest.TestCase):

    def setUp(self):
        self.on = FakeCmds(_state("tab_a", "tab_b"))
        self.off = FakeCmds()

    def test_qualified_absolute_relative(self):
        self.assertEqual(scope.qualified("Manny_Rig", self.on), "tab_a:Manny_Rig")
        self.assertEqual(scope.absolute("Manny_Rig", self.on), ":tab_a:Manny_Rig")
        self.assertEqual(scope.relative("tab_a:Manny_Rig", self.on), "Manny_Rig")
        self.assertEqual(scope.relative("tab_b:Manny_Rig", self.on), "tab_b:Manny_Rig")
        self.assertEqual(scope.qualified("Manny_Rig", self.off), "Manny_Rig")
        self.assertEqual(scope.absolute("Manny_Rig", self.off), ":Manny_Rig")

    def test_a_created_name_with_a_namespace_is_absolute(self):
        # Maya resolves a creation name relative to the CURRENT namespace (measured)
        self.assertEqual(scope.as_created("tab_a:Manny_Rig:MoCapConstraints"),
                         ":tab_a:Manny_Rig:MoCapConstraints")
        self.assertEqual(scope.as_created(":A:x"), ":A:x")

    def test_a_created_leaf_stays_relative(self):
        self.assertEqual(scope.as_created("hand_r_weaponSpace"), "hand_r_weaponSpace")
        self.assertEqual(scope.as_created(""), "")

    def test_a_name_given_back_is_from_the_root(self):
        self.assertEqual(scope.root_name("tab_a:root"), ":tab_a:root")
        self.assertEqual(scope.root_name(":root"), ":root")
        self.assertEqual(scope.root_name("root"), ":root")

    def test_local_takes_the_tab_off_every_node_of_a_path(self):
        self.assertEqual(scope.local("|tab_a:G|tab_a:Rig:root", self.on), "|G|Rig:root")
        self.assertEqual(scope.local("|tab_b:G|tab_b:root", self.on), "|tab_b:G|tab_b:root")
        self.assertEqual(scope.local("|tab_a:G|tab_a:Rig:root", self.off), "|tab_a:G|tab_a:Rig:root")


class CurrentNamespace(unittest.TestCase):

    def test_enter_active_sets_the_tabs_namespace(self):
        cmds = FakeCmds(_state("tab_a", "tab_b", active="tab_b"))
        scope.enter_active(cmds)
        self.assertEqual(cmds.current, ":tab_b")

    def test_enter_active_with_tabs_off_is_the_root(self):
        cmds = FakeCmds()
        cmds.current = ":clip"
        scope.enter_active(cmds)
        self.assertEqual(cmds.current, ":")

    def test_at_root_comes_back_to_the_tab_even_on_an_error(self):
        cmds = FakeCmds(_state("tab_a", "tab_b"))
        with self.assertRaises(ValueError):
            with scope.at_root(cmds):
                self.assertEqual(cmds.current, ":")
                raise ValueError("boom")
        self.assertEqual(cmds.current, ":tab_a")


class HomeNamespace(unittest.TestCase):

    def test_a_kept_clip_moves_under_the_tab(self):
        cmds = FakeCmds(_state("tab_a", "tab_b"), namespaces=("tab_a", "tab_b", "Walk"))
        self.assertEqual(scope.home_namespace("Walk", cmds), "tab_a:Walk")
        self.assertIn("tab_a:Walk", cmds.namespaces)

    def test_a_taken_name_in_the_tab_gets_a_number(self):
        cmds = FakeCmds(_state("tab_a", "tab_b"), namespaces=("tab_a", "tab_b", "tab_a:Walk", "Walk"))
        self.assertEqual(scope.home_namespace("Walk", cmds), "tab_a:Walk1")

    def test_with_tabs_off_nothing_moves(self):
        cmds = FakeCmds(namespaces=("Walk",))
        self.assertEqual(scope.home_namespace("Walk", cmds), "Walk")
        self.assertEqual(cmds.calls, [])


class SceneName(unittest.TestCase):

    def test_tabs_off_is_the_scenes_own(self):
        self.assertEqual(scope.scene_name(FakeCmds(scene="C:/w/shot.ma")), "C:/w/shot.ma")

    def test_tabs_on_is_the_active_tabs_file(self):
        cmds = FakeCmds(_state("tab_shot", "tab_rig", active="tab_rig"), scene="C:/w/untitled")
        self.assertEqual(scope.scene_name(cmds), "C:/w/rig.ma")


class OpenNew(unittest.TestCase):

    def test_tabs_off_opens_and_news_as_maya_does(self):
        cmds = FakeCmds()
        self.assertEqual(scope.open_scene("C:/w/a.ma", cmds, force=True), "")
        self.assertEqual(scope.new_scene(cmds), "")
        self.assertEqual(cmds.calls, [("file", ("C:/w/a.ma",), {"open": True, "force": True}),
                                      ("file", (), {"new": True, "force": True})])


if __name__ == "__main__":
    unittest.main()
