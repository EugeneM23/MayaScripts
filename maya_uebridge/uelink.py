"""Transport to a running Unreal editor.

stdlib only: no maya.cmds, no unreal.

The connection is Epic's own Python Remote Execution - UDP multicast discovery
on 239.0.0.1:6766 plus a TCP command channel - which is the exact counterpart
of the commandPort this repo already drives Maya with.

Epic's client (`remote_execution.py`) is loaded from the engine install rather
than copied into this repo: it is their code under the UE EULA, and a copy here
would drift from the engine build it has to speak to.

The session is opened per operation and closed after. Refresh and Import are
button presses, so a second of discovery is invisible, and a short-lived
session removes every stale-socket failure that follows an editor restart.
"""

import glob
import importlib.util
import json
import os
import time

REMOTE_EXEC_RELPATH = os.path.join(
    "Engine", "Plugins", "Experimental", "PythonScriptPlugin", "Content",
    "Python", "remote_execution.py")

DEFAULT_TIMEOUT = 15.0

NO_ENGINE_MESSAGE = (
    "Unreal engine install not found - could not locate remote_execution.py "
    "under any known engine root. Set the engine path explicitly.")

# Two very different causes produce the same silence, so the message names
# both. Discovery is answered on the editor's game thread, which means any
# modal dialog - 'Restore Packages' after a crash is the common one - looks
# exactly like the plugin being switched off.
NO_EDITOR_MESSAGE = (
    "No Unreal editor answered. Either Remote Execution is off (Project "
    "Settings > Plugins > Python > Enable Remote Execution), or the editor is "
    "blocked: a modal dialog such as 'Restore Packages' after a crash, or a "
    "long import, stops it answering until you dismiss it.")

_PROGRAM_FILES_GLOBS = (
    "C:\\Program Files\\Epic Games\\UE_*",
    "D:\\Program Files\\Epic Games\\UE_*",
    "C:\\Epic Games\\UE_*",
    "D:\\Epic Games\\UE_*")


class UeBridgeError(RuntimeError):
    """Anything that stops us reaching the editor or reading its answer."""


def pick_engine_root(candidates, exists):
    """First candidate that actually ships Epic's client.

    `exists` is passed in rather than called directly so the choice can be
    tested without an engine on disk.
    """
    for root in candidates:
        if root and exists(os.path.join(root, REMOTE_EXEC_RELPATH)):
            return root
    return None


def engine_root_from_exe(exe_path):
    """C:/X/Engine/Binaries/Win64/UnrealEditor.exe -> C:/X."""
    parts = os.path.normpath(exe_path or "").split(os.sep)
    for index in range(len(parts) - 1, -1, -1):
        if parts[index].lower() == "engine":
            return os.sep.join(parts[:index]) or os.sep
    return None


def running_editor_exes():
    """Executable paths of running Unreal editors, straight from the Win32 API.

    This is the only source that cannot be wrong. The registry lists every
    engine ever registered - this machine has two - and picking among them by
    enumeration order is a coin flip that lands on the wrong build.
    """
    try:
        import ctypes
        from ctypes import wintypes
    except (ImportError, ValueError):
        return []

    try:
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    except OSError:
        return []

    # Without an explicit restype the HANDLE comes back truncated on 64-bit.
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD)]

    slots = (wintypes.DWORD * 4096)()
    needed = wintypes.DWORD()
    if not psapi.EnumProcesses(ctypes.byref(slots), ctypes.sizeof(slots),
                               ctypes.byref(needed)):
        return []

    query_limited_information = 0x1000
    buffer = ctypes.create_unicode_buffer(32768)
    found = []
    for pid in slots[:needed.value // ctypes.sizeof(wintypes.DWORD)]:
        if not pid:
            continue
        handle = kernel32.OpenProcess(query_limited_information, False, pid)
        if not handle:
            continue
        try:
            size = wintypes.DWORD(len(buffer))
            if kernel32.QueryFullProcessImageNameW(handle, 0, buffer,
                                                   ctypes.byref(size)):
                name = os.path.basename(buffer.value).lower()
                if name.startswith("unrealeditor") and name.endswith(".exe"):
                    found.append(buffer.value)
        finally:
            kernel32.CloseHandle(handle)
    return found


def running_editor_roots():
    roots = []
    for exe in running_editor_exes():
        root = engine_root_from_exe(exe)
        if root and root not in roots:
            roots.append(root)
    return roots


def _registry_build_paths():
    """Engine roots the launcher and source builds registered for this user."""
    try:
        import winreg
    except ImportError:
        return []
    paths = []
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Epic Games\Unreal Engine\Builds")
    except OSError:
        return []
    try:
        index = 0
        while True:
            try:
                _, value, _ = winreg.EnumValue(key, index)
            except OSError:
                break
            if value:
                paths.append(os.path.normpath(value))
            index += 1
    finally:
        winreg.CloseKey(key)
    return paths


def engine_candidates(override=None):
    """Roots to try, most specific first.

    The running editor comes before the registry: we want the build we are
    about to talk to, not whichever one Windows happens to enumerate first.
    """
    candidates = []
    if override:
        candidates.append(override)
    candidates.extend(running_editor_roots())
    candidates.extend(_registry_build_paths())
    for pattern in _PROGRAM_FILES_GLOBS:
        candidates.extend(sorted(glob.glob(pattern), reverse=True))
    return candidates


def find_engine_root(override=None):
    return pick_engine_root(engine_candidates(override), os.path.isfile)


def load_remote_execution(engine_root):
    """Import Epic's client from `engine_root` without touching sys.path."""
    path = os.path.join(engine_root, REMOTE_EXEC_RELPATH)
    spec = importlib.util.spec_from_file_location("_uebridge_remote_exec", path)
    if spec is None or spec.loader is None:
        raise UeBridgeError("cannot load Epic's client from {0}".format(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def output_text(answer):
    """Flatten the protocol's reply into readable text."""
    chunks = []
    for entry in (answer or {}).get("output") or []:
        chunks.append(str(entry.get("output", "")))
    result = (answer or {}).get("result")
    if result:
        chunks.append(str(result))
    return "".join(chunks)


class UeLink(object):
    """One short-lived session with the editor.

    `client` exists for tests: pass a stand-in for Epic's module and the whole
    connection dance runs with no editor present.
    """

    def __init__(self, engine_root=None, timeout=DEFAULT_TIMEOUT, client=None):
        self.timeout = timeout
        self._client = client
        self._engine_root = engine_root
        self._session = None

    def __enter__(self):
        if self._client is None:
            root = self._engine_root or find_engine_root()
            if not root:
                raise UeBridgeError(NO_ENGINE_MESSAGE)
            self._client = load_remote_execution(root)

        self._session = self._client.RemoteExecution()
        self._session.start()

        node_id = self._wait_for_node()
        if node_id is None:
            self.__exit__(None, None, None)
            raise UeBridgeError(NO_EDITOR_MESSAGE)

        self._session.open_command_connection(node_id)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        session, self._session = self._session, None
        if session is not None:
            try:
                session.stop()
            except Exception:
                pass
        return False

    def _wait_for_node(self):
        """Discovery is a broadcast, so the answer arrives a moment later."""
        deadline = time.time() + self.timeout
        while True:
            nodes = self._session.remote_nodes or []
            if nodes:
                return nodes[0].get("node_id")
            if time.time() >= deadline:
                return None
            time.sleep(0.1)

    def run(self, source):
        mode = getattr(self._client, "MODE_EXEC_FILE", "ExecuteFile")
        return self._session.run_command(source, unattended=True, exec_mode=mode)


def run_script(source, out_path, engine_root=None, timeout=DEFAULT_TIMEOUT,
               client=None, keep_reply=False):
    """Run `source` in the editor and return the JSON reply it wrote.

    The reply file is deleted first. Reading a previous run's answer would
    report success for a script that died before writing anything - the kind of
    failure that looks like a working tool returning stale data.
    """
    if os.path.isfile(out_path):
        os.remove(out_path)

    with UeLink(engine_root=engine_root, timeout=timeout, client=client) as link:
        answer = link.run(source)

    if not os.path.isfile(out_path):
        raise UeBridgeError(
            "the editor did not write a reply. Its output was:\n{0}".format(
                output_text(answer).strip() or "(nothing)"))

    try:
        with open(out_path, "r") as handle:
            payload = json.load(handle)
    finally:
        if not keep_reply:
            try:
                os.remove(out_path)
            except OSError:
                pass

    if payload.get("error"):
        raise UeBridgeError(payload["error"])
    return payload
