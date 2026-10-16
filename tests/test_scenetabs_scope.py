"""maya_scenetabs.scope: the plugin sees only the active tab (2026-10-15).

Spec: docs/superpowers/specs/2026-10-15-scene-tabs-plugin-scope-design.md
"""
import os
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

    APP = "C:/Users/a/Documents/maya/"

    def __init__(self, state=None, namespaces=(), scene="", modified=False):
        self.text = records.dumps(state) if state is not None else None
        self.namespaces = set(namespaces)
        self.current = ":"
        self.scene = scene
        self.modified = modified
        self.calls = []

    def internalVar(self, userAppDir=False):
        return self.APP

    def objExists(self, name):
        return name == records.SESSION_NODE and self.text is not None

    def getAttr(self, plug):
        return self.text

    def file(self, *args, **kwargs):
        if kwargs.get("query"):
            return self.scene if kwargs.get("sceneName") else self.modified
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


class Shown(unittest.TestCase):

    def test_the_hidden_tabs_nodes_go_the_rest_stay(self):
        cmds = FakeCmds(_state("tab_a", "tab_b", "tab_c", active="tab_b"))
        names = ["persp", "top", "tab_a:cam", "tab_b:cam", "|tab_c:rig|tab_c:Rig:shot", "tab_b:Rig:cam", "tab_ab:cam"]
        self.assertEqual(scope.shown(names, cmds), ["persp", "top", "tab_b:cam", "tab_b:Rig:cam", "tab_ab:cam"])

    def test_tabs_off_keeps_everything(self):
        self.assertEqual(scope.shown(["tab_a:cam", "persp"], FakeCmds()), ["tab_a:cam", "persp"])


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

    def test_qualified_and_relative_tolerate_an_empty_name(self):
        for empty in ("", None):
            self.assertEqual(scope.qualified(empty, self.on), empty)
            self.assertEqual(scope.relative(empty, self.on), empty)

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


class SceneEmpty(unittest.TestCase):
    """2026-10-16: the first scene opens into an empty one, every later one in a tab."""

    def setUp(self):
        self.saved = scope._holds_own
        self.holds = False
        scope._holds_own = lambda cmds: self.holds

    def tearDown(self):
        scope._holds_own = self.saved

    def test_a_fresh_scene_is_empty(self):
        self.assertTrue(scope.scene_empty(FakeCmds()))

    def test_a_scene_from_a_file_is_not(self):
        self.assertFalse(scope.scene_empty(FakeCmds(scene="C:/w/shot.ma")))

    def test_an_untitled_scene_with_work_in_it_is_not(self):
        self.holds = True
        self.assertFalse(scope.scene_empty(FakeCmds(modified=True)))

    def test_an_untitled_scene_flagged_with_nothing_in_it_is(self):
        self.assertTrue(scope.scene_empty(FakeCmds(modified=True)))

    def test_an_unmodified_untitled_scene_is_empty_without_a_scan(self):
        self.holds = True
        self.assertTrue(scope.scene_empty(FakeCmds()))

    def test_the_session_file_an_untitled_scene_kept_counts_as_untitled(self):
        named = FakeCmds.APP + "SkeldarTabs/session_20261016_101010.ma"
        self.assertTrue(scope.scene_empty(FakeCmds(scene=named)))
        self.assertFalse(scope.scene_empty(FakeCmds(scene="C:/w/session_20261016_101010.ma")))

    def test_tabs_on_is_never_empty(self):
        self.assertFalse(scope.scene_empty(FakeCmds(_state("tab_a", "tab_b"))))

    def test_a_scene_that_cannot_be_read_holds_something(self):
        from maya_scenetabs import session
        scope._holds_own = self.saved
        saved = session.own_nodes

        def broken(namespace):
            raise RuntimeError("no scene")
        session.own_nodes = broken
        try:
            self.assertFalse(scope.scene_empty(FakeCmds(modified=True)))
        finally:
            session.own_nodes = saved


class FakeOpening(object):

    def __init__(self):
        self.calls = []

    def open_tab(self, path):
        self.calls.append(("open_tab", path))
        return "Opened %s in a tab" % path

    def new_tab(self):
        self.calls.append(("new_tab",))
        return "New empty tab"


class OpenNew(unittest.TestCase):

    def setUp(self):
        self.saved = scope._opening, scope._holds_own
        self.opening = FakeOpening()
        scope._opening = lambda: self.opening
        scope._holds_own = lambda cmds: True

    def tearDown(self):
        scope._opening, scope._holds_own = self.saved

    def test_an_empty_scene_opens_and_news_as_maya_does(self):
        cmds = FakeCmds()
        self.assertEqual(scope.open_scene("C:/w/a.ma", cmds, force=True), "")
        self.assertEqual(scope.new_scene(cmds), "")
        self.assertEqual(cmds.calls, [("file", ("C:/w/a.ma",), {"open": True, "force": True}),
                                      ("file", (), {"new": True, "force": True})])
        self.assertEqual(self.opening.calls, [])

    def test_with_a_scene_open_a_scene_opens_in_a_tab_beside_it(self):
        """Stash replaced the scene while tabs were off (2026-10-16, live)."""
        cmds = FakeCmds(scene="C:/w/shot.ma")
        self.assertEqual(scope.open_scene("C:/w/b.ma", cmds, force=True), "Opened C:/w/b.ma in a tab")
        self.assertEqual(scope.new_scene(cmds), "New empty tab")
        self.assertEqual(cmds.calls, [])
        self.assertEqual(self.opening.calls, [("open_tab", "C:/w/b.ma"), ("new_tab",)])

    def test_untitled_work_goes_into_tab_one(self):
        cmds = FakeCmds(modified=True)
        scope.open_scene("C:/w/b.ma", cmds)
        self.assertEqual(self.opening.calls, [("open_tab", "C:/w/b.ma")])

    def test_tabs_on_opens_a_tab(self):
        cmds = FakeCmds(_state("tab_a", "tab_b"))
        scope.open_scene("C:/w/c.ma", cmds)
        self.assertEqual(self.opening.calls, [("open_tab", "C:/w/c.ma")])


class ShareNamesTheTabScope(unittest.TestCase):

    def test_maya_share_imports_the_tab_scope_under_its_own_name(self):
        """maya_share binds a local `scope = hubcopy.current()` in its functions:
        the tab scope is `tabscope` there, never shadowed."""
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "SkeldarAnim", "maya_share.py")
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("from maya_scenetabs import scope as tabscope", text)
        self.assertNotIn("from maya_scenetabs import scope\n", text)
        for name in ("scene_name", "export_scene", "relative", "home_namespace", "tabs_on",
                     "open_scene", "new_scene"):
            self.assertNotIn(" scope.%s(" % name, text)
            self.assertNotIn("(scope.%s(" % name, text)


if __name__ == "__main__":
    unittest.main()
