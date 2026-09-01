"""Which character every rig operation acts on.

There is one active character, the way there is one current time. The
picker's Connect sets it -- press Connect on a bone hierarchy and that
hierarchy is what every button, every build and every bake lands on -- and
every entry point that takes a binding map adopts the character that map
came from, so a script assembling its own `scene_map` and calling
`build_fk(scene_map)` is scoped with no extra argument.

Held as a UUID, never as a path: the animator renames and regroups while
the panel is open, and a stored path goes stale the first time anything is
re-parented (trap 16).

A module-level context, deliberately. The alternative -- a `root`
parameter on thirty functions -- would rewrite twelve live verify scripts
and eight test modules to say what this module says in one line, and the
model would still be wrong: there is one active character. The policy that
needs testing is pure and lives in `manifest.py`; here there is a setter,
a getter and one derivation.
"""

import maya.cmds as cmds

from maya_overrig import naming, overrig

_ROOT_UUID = None


# ---------------------------------------------------------------------------
# pure
# ---------------------------------------------------------------------------

def root_of(scene_map):
    """The character root a binding map came from, or None.

    A binding map is built by `naming.hierarchy_map(root)`, which includes
    the root itself, so the root is simply the shallowest joint path in
    it. Ties break by path rather than by dict order, so the answer is the
    same every run -- a map spanning two subtrees cannot come out of
    `hierarchy_map`, but a caller can hand us anything.
    """
    paths = [path for path in (scene_map or {}).values() if path]
    if not paths:
        return None
    return min(paths, key=lambda path: (path.count("|"), path))


# ---------------------------------------------------------------------------
# scene
# ---------------------------------------------------------------------------

def character_roots():
    """Skeleton roots that are characters, not rig helpers.

    Anything OverRig created is skipped: its IK groups carry joints of
    their own with no joint parent, and without this a scene with a build
    in it reports a dozen skeletons instead of one (trap 1).

    Lives here rather than in `builder` so `manifest` can ask without
    importing `builder`, which imports `manifest`. `builder.character_roots`
    delegates to it and stays the name every caller already uses.
    """
    return naming.find_skeleton_roots(
        exclude_under=overrig.set_members(overrig.KNOT_SET))


def sole_character():
    """Whether the scene holds at most one character.

    The legacy question: a manifest carrying no character tag was built in
    a scene where this was true, because it is the only kind of scene the
    tool could build in before tagging existed.
    """
    return len(character_roots()) <= 1


def set_root(root):
    """Make `root` the active character. Returns its UUID, or None."""
    global _ROOT_UUID
    _ROOT_UUID = naming.uuid_of(root) if root else None
    return _ROOT_UUID


def clear():
    global _ROOT_UUID
    _ROOT_UUID = None


def root_uuid():
    """UUID of the active character, or None.

    A UUID whose node is gone answers None: the animator can delete the
    character with the panel open, and every lookup downstream must then
    resolve to nothing rather than to somebody else's rig.
    """
    if _ROOT_UUID and not (cmds.ls(_ROOT_UUID, long=True) or []):
        return None
    return _ROOT_UUID


def root():
    """Long DAG path of the active character, re-resolved now, or None."""
    return naming.path_from_uuid(_ROOT_UUID)


def adopt(scene_map):
    """Make the character a binding map came from active. Returns its UUID.

    Every MEL-running entry point calls this first, which is what lets a
    verify script hand `build_fk` a map it assembled itself and still have
    the manifests land on the right character.
    """
    return set_root(root_of(scene_map))
