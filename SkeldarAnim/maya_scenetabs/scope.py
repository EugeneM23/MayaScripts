"""Scene tabs, stage 2: the plugin sees only the active tab.

Spec: docs/superpowers/specs/2026-10-15-scene-tabs-plugin-scope-design.md (and
its addendum). With tabs off (no session, or one tab) the active namespace is
"" and every function here is the identity, so the plugin behaves exactly as
before. Every function that reads the scene takes the caller's `cmds` (`cmds_`):
the plugin's unit tests replace a module's `cmds` with a fake, and the fake
then answers here too.

Three rules, each with its helpers:
- **A scene reader sees the active tab only** (`active_only`, `in_active`).
- **The current namespace is the active tab's** while tabs are on: whatever
  creates nodes by relative name puts them in the tab, so they hide, save and
  close with it. A reset to the root becomes `enter_active`; work that must
  happen at the root (a clip imported for the length of a retarget) runs in
  `at_root`, which comes back to the tab.
- **What stays lands in the tab**: a root-level namespace kept after an import
  moves under the tab (`home_namespace`), a name made absolute is the tab's
  (`absolute`), and the plugin's own open / new of a scene opens a tab
  (`open_scene`, `new_scene`) - Maya's own are redirected by the hooks, but
  deferred, while the plugin's code runs on as if the scene were there.
  With tabs off it opens a tab too unless the scene is empty (`scene_empty`):
  the first scene goes into the one open, every later one beside it.
"""

import contextlib
import os

from . import records


def _cmds(cmds_):
    if cmds_ is not None:
        return cmds_
    import maya.cmds as cmds
    return cmds


def active_namespace(cmds_=None):
    """The active tab's namespace, or "" with tabs off. Never raises: a fake
    or a Maya without the session answers ""."""
    try:
        cmds = _cmds(cmds_)
        if not cmds.objExists(records.SESSION_NODE):
            return ""
        state = records.loads(cmds.getAttr(records.SESSION_NODE + "." + records.SESSION_ATTR) or "")
    except Exception:                                            # noqa: BLE001
        return ""
    return state["active"] if len(state["tabs"]) >= 2 else ""


def own_namespace(path):
    """The namespace of a path's own node ("" = the root). Pure."""
    short = (path or "").split("|")[-1]
    return short.rsplit(":", 1)[0] if ":" in short else ""


def within(namespace, active):
    """`namespace` is the active tab's or nested in it; everything is, with
    tabs off. Pure. `tab_a` is not within `tab`."""
    if not active:
        return True
    return namespace == active or namespace.startswith(active + ":")


def in_active(path, cmds_=None, active=None):
    active = active_namespace(cmds_) if active is None else active
    return within(own_namespace(path), active)


def active_only(paths, cmds_=None):
    """`paths` that belong to the active tab (all of them with tabs off)."""
    active = active_namespace(cmds_)
    if not active:
        return list(paths or [])
    return [p for p in paths or [] if within(own_namespace(p), active)]


def _tab_names(cmds_=None):
    try:
        cmds = _cmds(cmds_)
        if not cmds.objExists(records.SESSION_NODE):
            return []
        state = records.loads(cmds.getAttr(records.SESSION_NODE + "." + records.SESSION_ATTR) or "")
    except Exception:                                            # noqa: BLE001
        return []
    return [t["ns"] for t in state["tabs"]] if len(state["tabs"]) >= 2 else []


def shown(paths, cmds_=None):
    """`paths` without the hidden tabs' nodes: the active tab's and everything outside
    every tab (the root's persp / top / front / side) stay. As it is with tabs off.
    For Maya's own lists that know nothing of tabs (the cameras of a panel's menus)."""
    active = active_namespace(cmds_)
    if not active:
        return list(paths or [])
    hidden = [ns for ns in _tab_names(cmds_) if ns != active]
    return [p for p in paths or []
            if not any(within(own_namespace(p), ns) for ns in hidden)]


def qualified(name, cmds_=None):
    """`name` placed in the active tab (`tab_x:name`), or `name` with tabs off."""
    if not name:
        return name
    active = active_namespace(cmds_)
    return "%s:%s" % (active, name) if active else name


def absolute(name, cmds_=None):
    return ":" + qualified(name, cmds_)


def relative(name, cmds_=None):
    """A full name with the active tab's prefix taken off; anything else as it is."""
    if not name:
        return name
    active = active_namespace(cmds_)
    prefix = active + ":" if active else ""
    return name[len(prefix):] if prefix and name.startswith(prefix) else name


def local(path, cmds_=None):
    """A path as the active tab shows it: the tab's prefix taken off every
    node in it (`|tab_x:A|tab_x:Rig:root` -> `|A|Rig:root`). What a message or
    a label names - "the outermost namespace" is the tab's otherwise. As it is
    with tabs off."""
    active = active_namespace(cmds_)
    if not active:
        return path
    prefix = active + ":"
    return "|".join(p[len(prefix):] if p.startswith(prefix) else p for p in (path or "").split("|"))


def enter_active(cmds_=None):
    """The current namespace back to the active tab's (the root with tabs off)."""
    cmds = _cmds(cmds_)
    active = active_namespace(cmds)
    cmds.namespace(setNamespace=(":" + active) if active else ":")


@contextlib.contextmanager
def at_root(cmds_=None):
    """The root namespace current for the length of the block, the active
    tab's again after it."""
    cmds = _cmds(cmds_)
    cmds.namespace(setNamespace=":")
    try:
        yield
    finally:
        enter_active(cmds)


def home_namespace(namespace, cmds_=None):
    """A root-level namespace (a clip kept after its import) moved under the
    active tab. Returns its full name; with tabs off, or when it is not at the
    root, the name as it was."""
    cmds = _cmds(cmds_)
    active = active_namespace(cmds)
    leaf = namespace.lstrip(":")
    if not active or ":" in leaf or not cmds.namespace(exists=":" + leaf):
        return leaf
    target = leaf
    taken = set(n.split(":")[-1] for n in cmds.namespaceInfo(":" + active, listOnlyNamespaces=True) or [])
    number = 1
    while target in taken:
        target = "%s%d" % (leaf, number)
        number += 1
    if target != leaf:
        cmds.namespace(rename=(":" + leaf, target))
    cmds.namespace(rename=(":" + target, target), parent=":" + active)
    return "%s:%s" % (active, target)


def as_created(name):
    """A name for a node about to be CREATED or renamed: absolute when it
    carries a namespace. Maya resolves a creation name relative to the CURRENT
    namespace (measured: with `tabx` current, `tabx:Rig:a` became
    `tabx:tabx:Rig:a`, Maya making the missing namespaces itself), while a
    lookup goes from the root. A leaf stays relative and lands in the current
    namespace - the active tab's. Pure."""
    if not name or name.startswith(":") or ":" not in name:
        return name
    return ":" + name


def root_name(name):
    """A name given BACK to a node (a hold undone): its full name from the
    root, absolute, whatever namespace is current. Pure."""
    return ":" + (name or "").lstrip(":")


def tabs_on(cmds_=None):
    return bool(active_namespace(cmds_))


def scene_name(cmds_=None):
    """The file the animator is working in: the active tab's while tabs are
    on (the scene itself is the session then), else the scene's own name."""
    cmds = _cmds(cmds_)
    active = active_namespace(cmds)
    if not active:
        return cmds.file(query=True, sceneName=True) or ""
    try:
        state = records.loads(cmds.getAttr(records.SESSION_NODE + "." + records.SESSION_ATTR) or "")
    except Exception:                                            # noqa: BLE001
        return ""
    return (records.tab(state, active) or {}).get("path") or ""


def export_scene(path, file_type, cmds_=None):
    """A copy of the scene the animator is working in, references written
    in (a colleague has none of the files they point at): the active tab alone
    while tabs are on, else the whole scene. The working file, its name and its
    modified flag stay as they are."""
    cmds = _cmds(cmds_)
    if not tabs_on(cmds):
        cmds.file(path, exportAll=True, type=file_type, force=True, preserveReferences=False)
        return path
    from . import saving
    saving.save_tab(path=path, adopt=False, preserve_references=False)
    return path


def _session_file(scene, cmds):
    try:
        folder = cmds.internalVar(userAppDir=True).rstrip("/\\") + "/SkeldarTabs"
    except Exception:                                            # noqa: BLE001
        return False
    return records.is_session_file(scene, folder)


def _holds_own(cmds):
    """The open scene holds a node or a reference of its own (tabs off). A scene
    that cannot be read counts as holding something: it is kept, in a tab."""
    try:
        from . import session
        return bool(session.own_nodes("") or session.top_references(""))
    except Exception:                                            # noqa: BLE001
        return True


def scene_empty(cmds_=None):
    """Nothing to keep in the open scene (2026-10-16, the animator: «первая сцена
    открывается в первой вкладке если та пустая, дальше сцены в любом случае
    будут открываться в новых вкладках»): tabs off, untitled, and unmodified or
    holding nothing of its own. The plugin's first open goes into it; with
    anything else open, an open makes tabs (Stash used to replace the scene)."""
    cmds = _cmds(cmds_)
    if active_namespace(cmds):
        return False
    scene = (cmds.file(query=True, sceneName=True) or "").replace("\\", "/")
    if scene and not _session_file(scene, cmds):
        return False
    if not cmds.file(query=True, modified=True):
        return True
    return not _holds_own(cmds)


def same_file(a, b):
    """Two paths naming one file (case and separators aside). Pure."""
    if not a or not b:
        return False
    norm = lambda p: os.path.normcase(os.path.normpath(os.path.abspath(p)))   # noqa: E731
    return norm(a) == norm(b)


def opens_in_tab(path, cmds_=None):
    """Whether an open of `path` goes into a tab: always while tabs are on; with
    tabs off unless the scene is empty (`scene_empty`) or `path` IS the scene -
    opening it again reverts it, as Maya does (a second tab of one file would
    save over the first). Maya's File > Open asks the same (hooks.on_open)."""
    cmds = _cmds(cmds_)
    if active_namespace(cmds):
        return True
    if scene_empty(cmds):
        return False
    return not same_file(path, cmds.file(query=True, sceneName=True) or "")


@contextlib.contextmanager
def decided():
    """An open the plugin has decided itself: the Open check lets it through
    (between the decision and the open a Save As may have named the scene)."""
    try:
        from . import hooks
        guard = hooks.bypass()
    except Exception:                                            # noqa: BLE001
        guard = None
    if guard is None:
        yield
        return
    with guard:
        yield


def _opening():
    from . import opening
    return opening


def open_scene(path, cmds_=None, **flags):
    """The plugin's own open of a scene: Maya's open with `flags` into an empty
    scene or over the same file (`opens_in_tab`), else a new tab (a .ma / .mb
    opened, an FBX imported into an empty tab; with tabs off the open scene
    becomes tab 1 first). Returns the tab's message, or "" for Maya's own open."""
    cmds = _cmds(cmds_)
    if not opens_in_tab(path, cmds):
        with decided():
            cmds.file(path, open=True, **flags)
        return ""
    opening = _opening()
    if path.lower().endswith(".fbx"):
        previous = active_namespace(cmds)
        message = opening.new_tab()
        made = active_namespace(cmds)
        from maya_scenesetup import fbximport
        try:
            fbximport.import_nodes(path)
        except Exception:
            #  the tab that was active entered again, the empty one closed
            if previous:
                from . import switching
                switching.switch(previous)
            opening.close_tab(made, ask=False)
            raise
        return message
    return opening.open_tab(path)


def new_scene(cmds_=None):
    """The plugin's own new scene: Maya's new over an empty scene, else an empty tab."""
    cmds = _cmds(cmds_)
    if scene_empty(cmds):
        cmds.file(new=True, force=True)
        return ""
    return _opening().new_tab()
