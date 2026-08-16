"""Tests for the transport.

The connection logic is exercised against a fake stand-in for Epic's client, so
everything here runs with no Unreal editor and no Maya.
"""

import json
import os
import tempfile
import unittest

from maya_uebridge import uelink


class FakeCommandResult(dict):
    pass


class FakeRemoteExecution(object):
    """Stands in for remote_execution.RemoteExecution."""

    MODE_EXEC_FILE = "ExecuteFile"

    def __init__(self, nodes=None, answer=None, fail_open=False, writes=None):
        self.nodes_to_report = nodes if nodes is not None else [{"node_id": "abc"}]
        self.answer = answer or {"success": True, "result": "", "output": []}
        self.fail_open = fail_open
        # (path, payload) the "editor" drops on disk, the way the real scripts do
        self.writes = writes
        self.broken_command_socket = False
        self.started = False
        self.stopped = False
        self.closed_command = False
        self.opened = None
        self.ran = None

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    @property
    def remote_nodes(self):
        return self.nodes_to_report if self.started else []

    def open_command_connection(self, node_id):
        if self.fail_open:
            raise RuntimeError("refused")
        self.opened = node_id

    def close_command_connection(self):
        self.closed_command = True
        if self.broken_command_socket:
            raise OSError("connection reset by peer")

    def run_command(self, command, unattended=True, exec_mode=None,
                    raise_on_failure=False):
        self.ran = command
        if self.writes:
            path, payload = self.writes
            with open(path, "w") as handle:
                json.dump(payload, handle)
        return self.answer


class FakeClient(object):
    """Stands in for the remote_execution module."""

    MODE_EXEC_FILE = "ExecuteFile"

    def __init__(self, session):
        self.session = session

    def RemoteExecution(self, *args, **kwargs):
        return self.session

    class RemoteExecutionConfig(object):
        pass


class EngineDiscovery(unittest.TestCase):

    def test_picks_the_first_candidate_that_has_the_client(self):
        present = {os.path.join("C:\\Src", uelink.REMOTE_EXEC_RELPATH)}
        got = uelink.pick_engine_root(["C:\\Nope", "C:\\Src"], lambda p: p in present)
        self.assertEqual(got, "C:\\Src")

    def test_returns_none_when_nothing_matches(self):
        self.assertIsNone(uelink.pick_engine_root(["C:\\Nope"], lambda p: False))

    def test_candidates_are_tried_in_order(self):
        """An explicit override must beat whatever the registry reports."""
        seen = []

        def note(path):
            seen.append(path)
            return False

        uelink.pick_engine_root(["C:\\Override", "C:\\Registry"], note)
        self.assertTrue(seen[0].startswith("C:\\Override"))

    def test_an_empty_candidate_list_is_not_an_error(self):
        self.assertIsNone(uelink.pick_engine_root([], lambda p: True))

    def test_the_engine_root_is_read_off_the_editor_executable(self):
        got = uelink.engine_root_from_exe(
            "C:\\Src\\Engine\\Binaries\\Win64\\UnrealEditor.exe")
        self.assertEqual(got, "C:\\Src")

    def test_a_path_with_no_engine_folder_yields_nothing(self):
        self.assertIsNone(uelink.engine_root_from_exe("C:\\Src\\UnrealEditor.exe"))

    def test_an_empty_exe_path_yields_nothing(self):
        self.assertIsNone(uelink.engine_root_from_exe(""))

    def test_the_deepest_engine_folder_wins(self):
        """A project can live inside the engine tree and repeat the name."""
        got = uelink.engine_root_from_exe(
            "C:\\Engine\\Src\\Engine\\Binaries\\Win64\\UnrealEditor.exe")
        self.assertEqual(got, "C:\\Engine\\Src")

    def test_a_running_editor_is_preferred_over_the_registry(self):
        """Two engines are registered on this machine; enumeration order must
        not decide which one we load Epic's client from."""
        original_running = uelink.running_editor_roots
        original_registry = uelink._registry_build_paths
        uelink.running_editor_roots = lambda: ["C:\\Live"]
        uelink._registry_build_paths = lambda: ["C:\\RegistryA", "C:\\RegistryB"]
        try:
            candidates = uelink.engine_candidates()
        finally:
            uelink.running_editor_roots = original_running
            uelink._registry_build_paths = original_registry
        self.assertEqual(candidates[0], "C:\\Live")
        self.assertIn("C:\\RegistryA", candidates)

    def test_an_override_still_beats_the_running_editor(self):
        original_running = uelink.running_editor_roots
        uelink.running_editor_roots = lambda: ["C:\\Live"]
        try:
            candidates = uelink.engine_candidates(override="C:\\Chosen")
        finally:
            uelink.running_editor_roots = original_running
        self.assertEqual(candidates[0], "C:\\Chosen")

    def test_the_relative_path_is_where_epic_ships_the_client(self):
        self.assertIn("PythonScriptPlugin", uelink.REMOTE_EXEC_RELPATH)
        self.assertTrue(uelink.REMOTE_EXEC_RELPATH.endswith("remote_execution.py"))


class NodeChoice(unittest.TestCase):
    """Discovery already reports project_name, so which editor to talk to is
    decidable before connecting to any of them."""

    def nodes(self):
        return [{"node_id": "b", "project_name": "Zebra", "machine": "PC"},
                {"node_id": "a", "project_name": "Atone", "machine": "PC"}]

    def test_labels_a_node_by_its_project(self):
        self.assertEqual(
            uelink.node_label({"node_id": "a", "project_name": "Atone"}), "Atone")

    def test_a_node_with_no_project_still_gets_a_label(self):
        """An editor on the project browser reports no project name."""
        label = uelink.node_label({"node_id": "a", "machine": "PC",
                                   "engine_version": "5.8.1"})
        self.assertTrue(label)
        self.assertIn("5.8.1", label)

    def test_one_node_is_taken_whatever_the_preference(self):
        one = [{"node_id": "a", "project_name": "Atone"}]
        self.assertEqual(uelink.pick_node(one, None)["node_id"], "a")
        self.assertEqual(uelink.pick_node(one, "Something Else")["node_id"], "a")

    def test_the_preferred_project_wins_among_several(self):
        chosen = uelink.pick_node(self.nodes(), "Zebra")
        self.assertEqual(chosen["node_id"], "b")

    def test_without_a_preference_the_choice_is_alphabetical_not_a_race(self):
        """nodes[0] is whichever editor answered first - a different project
        run to run. Sorting makes the same scene give the same answer."""
        chosen = uelink.pick_node(self.nodes(), None)
        self.assertEqual(chosen["project_name"], "Atone")

    def test_an_unknown_preference_falls_back_deterministically(self):
        chosen = uelink.pick_node(self.nodes(), "NotOpen")
        self.assertEqual(chosen["project_name"], "Atone")

    def test_no_nodes_is_no_choice(self):
        self.assertIsNone(uelink.pick_node([], "Atone"))

    def test_labels_come_back_sorted_for_the_menu(self):
        self.assertEqual(uelink.node_labels(self.nodes()), ["Atone", "Zebra"])


class Messages(unittest.TestCase):

    def test_the_no_editor_message_names_both_causes(self):
        """A blocked editor and a disabled plugin are silent in the same way,
        so a message naming only one sends the user down the wrong path."""
        self.assertIn("Remote Execution", uelink.NO_EDITOR_MESSAGE)
        self.assertIn("dialog", uelink.NO_EDITOR_MESSAGE.lower())

    def test_the_timeout_survives_a_briefly_busy_editor(self):
        """Discovery answers on the game thread, which stalls during DDC
        maintenance and asset scans; 8s was measured too short."""
        self.assertGreaterEqual(uelink.DEFAULT_TIMEOUT, 15.0)

    def test_the_no_engine_message_says_what_was_not_found(self):
        self.assertIn("engine", uelink.NO_ENGINE_MESSAGE.lower())


class OutputText(unittest.TestCase):

    def test_flattens_the_protocol_output_list(self):
        answer = {"output": [{"type": "Info", "output": "one\n"},
                             {"type": "Error", "output": "two"}]}
        self.assertEqual(uelink.output_text(answer), "one\ntwo")

    def test_includes_the_result_field(self):
        answer = {"output": [], "result": "42"}
        self.assertIn("42", uelink.output_text(answer))

    def test_an_empty_answer_is_an_empty_string(self):
        self.assertEqual(uelink.output_text({}), "")


class Connecting(unittest.TestCase):

    def test_starts_opens_and_stops(self):
        session = FakeRemoteExecution()
        with uelink.UeLink(engine_root="C:\\Src",
                           client=FakeClient(session)) as link:
            link.run("print(1)")
        self.assertTrue(session.started)
        self.assertEqual(session.opened, "abc")
        self.assertEqual(session.ran, "print(1)")
        self.assertTrue(session.stopped)

    def test_stops_even_when_the_body_raises(self):
        """A session left running holds a socket that outlives the editor."""
        session = FakeRemoteExecution()
        try:
            with uelink.UeLink(engine_root="C:\\Src",
                               client=FakeClient(session)):
                raise ValueError("boom")
        except ValueError:
            pass
        self.assertTrue(session.stopped)

    def test_a_dead_command_socket_still_releases_the_broadcast_socket(self):
        """When the editor dies mid-command, closing the TCP side throws. If
        that throw skips stop(), the multicast socket stays bound for the whole
        Maya session."""
        session = FakeRemoteExecution()
        session.broken_command_socket = True
        try:
            with uelink.UeLink(engine_root="C:\\Src",
                               client=FakeClient(session)) as link:
                link.run("print(1)")
        except OSError:
            self.fail("teardown let the dead socket escape")
        self.assertTrue(session.closed_command)
        self.assertTrue(session.stopped, "broadcast socket was never released")

    def test_no_editor_answering_raises_the_helpful_message(self):
        session = FakeRemoteExecution(nodes=[])
        with self.assertRaises(uelink.UeBridgeError) as caught:
            with uelink.UeLink(engine_root="C:\\Src", timeout=0.2,
                               client=FakeClient(session)):
                pass
        self.assertIn("Remote Execution", str(caught.exception))

    def test_the_editor_search_gives_up_rather_than_hanging(self):
        import time
        session = FakeRemoteExecution(nodes=[])
        started = time.time()
        with self.assertRaises(uelink.UeBridgeError):
            with uelink.UeLink(engine_root="C:\\Src", timeout=0.3,
                               client=FakeClient(session)):
                pass
        self.assertLess(time.time() - started, 3.0)


class RunScript(unittest.TestCase):

    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="uebridge_test_")
        self.out = os.path.join(self.folder, "reply.json")

    def tearDown(self):
        for name in os.listdir(self.folder):
            os.remove(os.path.join(self.folder, name))
        os.rmdir(self.folder)

    def write_reply(self, payload):
        with open(self.out, "w") as handle:
            json.dump(payload, handle)

    def test_reads_the_reply_the_editor_wrote(self):
        session = FakeRemoteExecution(
            writes=(self.out, {"ok": True, "assets": [1, 2]}))
        got = uelink.run_script("print(1)", self.out, engine_root="C:\\Src",
                                client=FakeClient(session), keep_reply=True)
        self.assertEqual(got["assets"], [1, 2])

    def test_the_reply_file_is_cleaned_up_by_default(self):
        """Temp replies must not pile up in the user's temp folder."""
        session = FakeRemoteExecution(writes=(self.out, {"ok": True}))
        uelink.run_script("print(1)", self.out, engine_root="C:\\Src",
                          client=FakeClient(session))
        self.assertFalse(os.path.isfile(self.out))

    def test_a_stale_reply_is_deleted_before_the_run(self):
        """Reading last run's answer would report success for a script that died."""
        self.write_reply({"ok": True, "assets": ["stale"]})
        session = FakeRemoteExecution(
            answer={"success": True, "result": "", "output": [
                {"type": "Error", "output": "the editor blew up"}]})
        with self.assertRaises(uelink.UeBridgeError) as caught:
            uelink.run_script("print(1)", self.out, engine_root="C:\\Src",
                              client=FakeClient(session))
        self.assertIn("the editor blew up", str(caught.exception))

    def test_an_error_inside_the_reply_is_raised(self):
        session = FakeRemoteExecution(
            writes=(self.out, {"ok": False, "error": "Traceback: no such asset"}))
        with self.assertRaises(uelink.UeBridgeError) as caught:
            uelink.run_script("print(1)", self.out, engine_root="C:\\Src",
                              client=FakeClient(session), keep_reply=True)
        self.assertIn("no such asset", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
