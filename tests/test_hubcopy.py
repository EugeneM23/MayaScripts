"""maya_hubcopy - the scope rules, against a fake `cmds` (no Maya).

The names a copy makes are prefixed, the names it is called by are mapped to
them, a name it did not make passes through, a callback runs in the scope
that made it, and a scriptJob made in a scope dies with it. Spec:
docs/superpowers/specs/2026-10-09-hub-section-popups-design.md.
"""

import sys
import types
import unittest

import tests  # noqa: F401  (puts SkeldarAnim/ on sys.path)

import maya_hubcopy as hubcopy


class FakeCmds(object):
    """Records every call; creates controls named `|root|<name>` (what Maya
    answers a creation with), scriptJobs as ints."""

    def __init__(self):
        self.calls = []
        self.jobs = []
        self.killed = []
        self.next_job = 100
        self.deferred = []

    def _name_of(self, args, kwargs):
        if args and isinstance(args[0], str):
            return args[0]
        return kwargs.get("name")

    def text(self, *args, **kwargs):
        self.calls.append(("text", args, dict(kwargs)))
        return self._control("text", args, kwargs)

    def button(self, *args, **kwargs):
        self.calls.append(("button", args, dict(kwargs)))
        return self._control("button", args, kwargs)

    def columnLayout(self, *args, **kwargs):             # noqa: N802
        self.calls.append(("columnLayout", args, dict(kwargs)))
        return self._control("columnLayout", args, kwargs)

    def setParent(self, *args, **kwargs):                # noqa: N802
        self.calls.append(("setParent", args, dict(kwargs)))
        return "|root"

    def optionVar(self, *args, **kwargs):
        self.calls.append(("optionVar", args, dict(kwargs)))
        return None

    def shadingNode(self, *args, **kwargs):
        self.calls.append(("shadingNode", args, dict(kwargs)))
        return args[0] if args else None

    def scriptJob(self, *args, **kwargs):
        self.calls.append(("scriptJob", args, dict(kwargs)))
        if "kill" in kwargs:
            self.killed.append(kwargs["kill"])
            return None
        self.next_job += 1
        return self.next_job

    def evalDeferred(self, fn, **kwargs):               # noqa: N802
        self.calls.append(("evalDeferred", (fn,), dict(kwargs)))
        self.deferred.append(fn)

    def _control(self, command, args, kwargs):
        if kwargs.get("q") or kwargs.get("query") or kwargs.get("e") \
                or kwargs.get("edit"):
            return kwargs.get("name") or (args[0] if args else None)
        name = self._name_of(args, kwargs)
        if name is None:
            return "|root|" + command + str(len(self.calls))
        return "|root|" + name


class CreatorsTable(unittest.TestCase):

    def test_scene_and_flow_commands_are_not_creators(self):
        for name in ("setParent", "optionVar", "shadingNode", "scriptJob",
                     "attributeQuery", "objExists", "deleteUI", "control",
                     "evalDeferred", "setToolTo", "createNode"):
            self.assertNotIn(name, hubcopy.CREATORS)

    def test_the_controls_the_sections_make_are_creators(self):
        for name in ("text", "button", "textScrollList", "optionMenu",
                     "textField", "checkBox", "columnLayout", "rowLayout",
                     "frameLayout", "iconTextRadioCollection",
                     "iconTextRadioButton", "draggerContext"):
            self.assertIn(name, hubcopy.CREATORS)


def _reset(cmds):
    """Every scope the tests left standing closed: the registry is process
    wide (on sys), so one test's copy must not show in another's list."""
    for scope in hubcopy.live():
        hubcopy.close(scope, cmds)


class ScopeNames(unittest.TestCase):

    def setUp(self):
        self.cmds = FakeCmds()
        _reset(self.cmds)
        hubcopy.install(self.cmds)
        self.scope = hubcopy.new_scope(section="colour")

    def tearDown(self):
        hubcopy.close(self.scope, self.cmds)

    def test_outside_a_scope_nothing_changes(self):
        name = self.cmds.text("mayaSceneSetupStatus", label="hi")
        self.assertEqual(name, "|root|mayaSceneSetupStatus")
        self.assertEqual(self.cmds.calls[-1][1], ("mayaSceneSetupStatus",))

    def test_a_creation_in_a_scope_gets_the_prefix_and_is_recorded(self):
        with hubcopy.entered(self.scope):
            made = self.cmds.text("mayaSceneSetupStatus", label="x")
        self.assertEqual(made, "|root|{0}mayaSceneSetupStatus".format(
            self.scope.prefix))
        self.assertEqual(self.scope.names["mayaSceneSetupStatus"], made)

    def test_a_later_edit_in_the_scope_reaches_the_copy_not_the_hub(self):
        with hubcopy.entered(self.scope):
            self.cmds.text("mayaSceneSetupStatus", label="x")
            self.cmds.text("mayaSceneSetupStatus", edit=True, label="y")
        edit = self.cmds.calls[-1]
        self.assertEqual(edit[1], ("|root|" + self.scope.prefix
                                   + "mayaSceneSetupStatus",))

    def test_a_root_call_after_the_copy_still_reaches_the_hub(self):
        with hubcopy.entered(self.scope):
            self.cmds.text("mayaSceneSetupStatus", label="x")
        self.cmds.text("mayaSceneSetupStatus", edit=True, label="hub")
        self.assertEqual(self.cmds.calls[-1][1], ("mayaSceneSetupStatus",))

    def test_a_name_the_copy_did_not_make_passes_through(self):
        with hubcopy.entered(self.scope):
            self.cmds.text("hubOnlyLine", edit=True, label="z")
        self.assertEqual(self.cmds.calls[-1][1], ("hubOnlyLine",))

    def test_query_and_edit_never_create(self):
        with hubcopy.entered(self.scope):
            self.cmds.text("mayaSceneSetupStatus", query=True, label=True)
        self.assertNotIn("mayaSceneSetupStatus", self.scope.names)
        self.assertEqual(self.cmds.calls[-1][1], ("mayaSceneSetupStatus",))

    def test_scene_names_are_never_renamed(self):
        with hubcopy.entered(self.scope):
            self.cmds.shadingNode("skeldarColour", asShader=True)
            self.cmds.optionVar(query="mayaSceneSetup_weapon")
        self.assertEqual(self.cmds.calls[-2][1], ("skeldarColour",))
        self.assertEqual(self.cmds.calls[-1][2].get("query"),
                         "mayaSceneSetup_weapon")

    def test_lists_and_tuples_are_mapped_inside(self):
        with hubcopy.entered(self.scope):
            made = self.cmds.text("mayaSceneSetupStatus", label="x")
            self.cmds.columnLayout("otherLayout", parent=None,
                                   attachControl=[("mayaSceneSetupStatus",
                                                   "top", 2, "hubThing")])
        call = self.cmds.calls[-1]
        attach = call[2].get("attachControl")
        self.assertEqual(attach, [(made, "top", 2, "hubThing")])

    def test_a_second_scope_makes_its_own_names(self):
        other = hubcopy.new_scope(section="colour")
        try:
            with hubcopy.entered(self.scope):
                first = self.cmds.text("mayaSceneSetupStatus", label="a")
            with hubcopy.entered(other):
                second = self.cmds.text("mayaSceneSetupStatus", label="b")
            self.assertNotEqual(first, second)
            self.assertEqual(other.names["mayaSceneSetupStatus"], second)
            self.assertEqual(self.scope.names["mayaSceneSetupStatus"], first)
        finally:
            hubcopy.close(other, self.cmds)

    def test_resolve_maps_inside_and_is_identity_outside(self):
        with hubcopy.entered(self.scope):
            made = self.cmds.text("mayaSceneSetupStatus", label="x")
            self.assertEqual(hubcopy.resolve("mayaSceneSetupStatus"), made)
        self.assertEqual(hubcopy.resolve("mayaSceneSetupStatus"),
                         "mayaSceneSetupStatus")

    def test_a_prefixed_creation_is_not_prefixed_twice(self):
        with hubcopy.entered(self.scope):
            made = self.cmds.text(self.scope.prefix + "x", label="x")
        self.assertEqual(made, "|root|{0}x".format(self.scope.prefix))
        self.assertNotIn(self.scope.prefix + "x", self.scope.names)


class Callbacks(unittest.TestCase):

    def setUp(self):
        self.cmds = FakeCmds()
        _reset(self.cmds)
        hubcopy.install(self.cmds)
        self.scope = hubcopy.new_scope(section="colour")

    def tearDown(self):
        hubcopy.close(self.scope, self.cmds)

    def test_a_command_callback_runs_in_the_scope_that_made_it(self):
        seen = []

        def press(*_args):
            seen.append(self.cmds.text("mayaSceneSetupStatus", edit=True,
                                       label="pressed"))

        with hubcopy.entered(self.scope):
            self.cmds.text("mayaSceneSetupStatus", label="x")
            self.cmds.button("press", command=press)
        # the press fires from the hub's event loop, the stack is empty
        self.assertIsNone(hubcopy.current())
        button_call = [c for c in self.cmds.calls if c[0] == "button"][-1]
        button_call[2]["command"]()
        self.assertEqual(seen[0], "|root|{0}mayaSceneSetupStatus".format(
            self.scope.prefix))

    def test_an_evaluated_deferred_callable_runs_in_its_scope(self):
        seen = []

        def later():
            seen.append(hubcopy.current() is self.scope)

        with hubcopy.entered(self.scope):
            self.cmds.evalDeferred(later, lowestPriority=True)
        self.cmds.deferred[0]()
        self.assertEqual(seen, [True])

    def test_wrap_captures_the_scope_now(self):
        seen = []

        def handler():
            seen.append(hubcopy.current())

        with hubcopy.entered(self.scope):
            wrapped = hubcopy.wrap(handler)
        wrapped()
        self.assertEqual(seen, [self.scope])

    def test_wrap_is_identity_with_no_scope(self):
        def handler():
            return 1

        self.assertIs(hubcopy.wrap(handler), handler)


class ScriptJobs(unittest.TestCase):

    def setUp(self):
        self.cmds = FakeCmds()
        _reset(self.cmds)
        hubcopy.install(self.cmds)
        self.scope = hubcopy.new_scope(section="colour")

    def tearDown(self):
        hubcopy.close(self.scope, self.cmds)

    def test_a_job_made_in_the_scope_is_killed_with_it(self):
        with hubcopy.entered(self.scope):
            job = self.cmds.scriptJob(event=["SelectionChanged", lambda: 0])
        self.assertEqual(self.scope.jobs, [job])
        killed = hubcopy.close(self.scope, self.cmds)
        self.assertEqual(killed, 1)
        self.assertEqual(self.cmds.killed, [job])

    def test_close_is_idempotent_and_drops_the_registry(self):
        hubcopy.close(self.scope, self.cmds)
        self.assertEqual(hubcopy.close(self.scope, self.cmds), 0)
        self.assertNotIn(self.scope, hubcopy.live())

    def test_a_job_outside_any_scope_is_not_recorded(self):
        self.cmds.scriptJob(event=["SelectionChanged", lambda: 0])
        self.assertEqual(self.scope.jobs, [])


class Registry(unittest.TestCase):

    def setUp(self):
        self.cmds = FakeCmds()
        _reset(self.cmds)
        hubcopy.install(self.cmds)

    def test_instances_are_per_section_and_oldest_first(self):
        a = hubcopy.new_scope(section="colour")
        b = hubcopy.new_scope(section="studio")
        c = hubcopy.new_scope(section="colour")
        try:
            self.assertEqual(hubcopy.instances("colour"), [a, c])
            self.assertEqual(hubcopy.instances("studio"), [b])
            self.assertEqual(hubcopy.instances("retarget"), [])
        finally:
            for scope in (a, b, c):
                hubcopy.close(scope, self.cmds)

    def test_live_lists_every_live_scope_by_creation_order(self):
        a = hubcopy.new_scope(section="colour")
        b = hubcopy.new_scope(section=None)
        try:
            tags = [s.tag for s in hubcopy.live()]
            self.assertLess(tags.index(a.tag), tags.index(b.tag))
        finally:
            hubcopy.close(a, self.cmds)
            hubcopy.close(b, self.cmds)

    def test_tags_stay_in_creation_order_past_nine(self):
        scopes = [hubcopy.new_scope(section="colour") for _ in range(11)]
        try:
            serials = [s.serial for s in hubcopy.instances("colour")]
            self.assertEqual(serials, sorted(serials))
        finally:
            for scope in scopes:
                hubcopy.close(scope, self.cmds)


class Install(unittest.TestCase):

    def test_install_wraps_every_command_once(self):
        fake = FakeCmds()
        original = fake.text
        count = hubcopy.install(fake)
        self.assertGreater(count, 5)
        self.assertEqual(fake.text._skeldar_real, original)
        hubcopy.install(fake)
        self.assertEqual(fake.text._skeldar_real, original)

    def test_private_attributes_are_not_wrapped(self):
        fake = FakeCmds()
        fake._hidden = lambda: 1
        hubcopy.install(fake)
        self.assertIs(fake._hidden.__dict__.get("_skeldar_real"), None)

    def test_a_module_attribute_is_not_a_command(self):
        fake = FakeCmds()
        fake.helper_module = types.ModuleType("helper")
        hubcopy.install(fake)
        self.assertIsInstance(fake.helper_module, types.ModuleType)


class Bind(unittest.TestCase):
    """`bind`: an object whose methods run in a scope (2026-10-09)."""

    def setUp(self):
        self.cmds = FakeCmds()
        _reset(self.cmds)
        hubcopy.install(self.cmds)

    def test_outside_a_scope_the_object_is_itself(self):
        class Thing(object):
            pass
        thing = Thing()
        self.assertIs(hubcopy.bind(thing), thing)

    def test_a_method_runs_in_the_scope_that_bound_it(self):
        seen = []

        class Thing(object):
            label = "plain"

            def press(self):
                seen.append(hubcopy.current())
                return self.label

        scope = hubcopy.new_scope(section="colour")
        try:
            with hubcopy.entered(scope):
                bound = hubcopy.bind(Thing())
            self.assertEqual(bound.label, "plain")
            self.assertEqual(bound.press(), "plain")
            self.assertEqual(seen, [scope])
            self.assertIsNone(hubcopy.current())
        finally:
            hubcopy.close(scope, self.cmds)

    def test_a_closed_copy_runs_nothing(self):
        ran = []

        class Thing(object):
            def press(self):
                ran.append(True)

        scope = hubcopy.new_scope(section="colour")
        with hubcopy.entered(scope):
            bound = hubcopy.bind(Thing())
        hubcopy.close(scope, self.cmds)
        self.assertIsNone(bound.press())
        self.assertEqual(ran, [])

    def test_attributes_written_through_the_binding_land_on_the_object(self):
        class Thing(object):
            value = 1

        thing = Thing()
        scope = hubcopy.new_scope(section="colour")
        try:
            with hubcopy.entered(scope):
                bound = hubcopy.bind(thing)
            bound.value = 7
            self.assertEqual(thing.value, 7)
        finally:
            hubcopy.close(scope, self.cmds)


if __name__ == "__main__":
    unittest.main()
