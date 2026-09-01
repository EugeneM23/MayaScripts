"""Whose manifest is whose: the identity of every RigPicker object set.

Until 2026-09-01 a manifest was found by its NAME -- `RigPicker_build_arm_l`,
`RigPicker_fk_spine`, `RigPicker_twist_arm_l`. With a second character in
the scene Maya uniquifies the second build's sets to `...arm_l1`, so
`built_limbs()` never sees them: the tool reads the second character as
unrigged, builds FK over its live IK, and bakes limbs belonging to the
first one.

So identity moved into ATTRIBUTES and discovery into the PREFIX -- exactly
what the aim manifest has done since 2026-08-17, for exactly this reason.
Every set carries the character root's UUID, its kind and its name, the
readable name is kept for the outliner alone, and nothing is ever looked
up by that name again.

**Legacy files keep working.** A set with no `rigPickerRoot` was built
before tagging, which means it was built in a single-character scene --
so it answers for the character asking while the scene still holds one
character, and `claim_untagged` tags it the first time the picker binds
or a build runs. With several characters already in the scene, a manifest
is claimed only when one of its members lies inside the asking
character's own subtree.

Pure policy first, scene wrappers after. The pure half is what the tests
exercise: which manifest a character owns is the decision that goes wrong
silently.
"""

from collections import namedtuple

import maya.cmds as cmds

from maya_overrig import active, overrig

PREFIX = "RigPicker_"

ROOT_ATTR = "rigPickerRoot"
KIND_ATTR = "rigPickerKind"
NAME_ATTR = "rigPickerName"

KIND_IK = "ik"
KIND_FK = "fk"
KIND_TWIST = "twist"
KIND_AIM = "aim"

# Set-name conventions, for the legacy read alone. A NEW set still gets a
# readable name from these prefixes -- it is just never searched for by it.
IK_PREFIX = PREFIX + "build_"
FK_PREFIX = PREFIX + "fk_"
FK_FLAT = PREFIX + "fk"          # the pre-2026-08 flat set, one for all
TWIST_PREFIX = PREFIX + "twist_"
AIM_PREFIX = PREFIX + "aim_"

_NAME_KINDS = (
    (IK_PREFIX, KIND_IK),
    (TWIST_PREFIX, KIND_TWIST),
    (AIM_PREFIX, KIND_AIM),
    (FK_PREFIX, KIND_FK),
)

Record = namedtuple("Record", "set_name root kind name")


# ---------------------------------------------------------------------------
# pure
# ---------------------------------------------------------------------------

def set_name_for(kind, name):
    """The readable name a NEW manifest of this kind gets.

    Maya may uniquify it, which is the whole reason nothing looks a
    manifest up by name again.
    """
    if kind == KIND_IK:
        return IK_PREFIX + name
    if kind == KIND_TWIST:
        return TWIST_PREFIX + name
    if kind == KIND_AIM:
        return AIM_PREFIX + name
    if kind == KIND_FK:
        return FK_PREFIX + name if name else FK_FLAT
    raise ValueError("unknown manifest kind: {0!r}".format(kind))


def classify(set_name):
    """(kind, name) read out of a manifest's NAME, or ("", "").

    The legacy path only. It is safe there and nowhere else: an untagged
    set was built in a single-character scene, so it never collided and
    never carries one of Maya's uniquifying digits for us to mistake for
    part of the chain name.
    """
    if not set_name or not set_name.startswith(PREFIX):
        return "", ""
    if set_name == FK_FLAT:
        return KIND_FK, ""
    for prefix, kind in _NAME_KINDS:
        if set_name.startswith(prefix) and len(set_name) > len(prefix):
            return kind, set_name[len(prefix):]
    return "", ""


def owner_matches(record_root, wanted_root, sole):
    """Whether a manifest carrying `record_root` belongs to `wanted_root`.

    A tagged manifest belongs to exactly the character it names. An
    untagged one belongs to whoever asks, but only while the scene holds a
    single character -- which is the only kind of scene it could have been
    built in.
    """
    if record_root:
        return bool(wanted_root) and record_root == wanted_root
    return bool(sole)


def pick(records, kind, name, wanted_root, sole):
    """The one manifest of this kind and name for this character, or None.

    Tagged wins over untagged: a scene part-way through the migration
    holds both, and the tagged one is the manifest this character built.
    """
    candidates = [r for r in records if r.kind == kind and r.name == name]
    for record in candidates:
        if record.root and owner_matches(record.root, wanted_root, sole):
            return record.set_name
    for record in candidates:
        if not record.root and owner_matches(record.root, wanted_root, sole):
            return record.set_name
    return None


def untagged_names(records, kind=None):
    """Set names among `records` carrying no character tag."""
    return [r.set_name for r in records
            if not r.root and (kind is None or r.kind == kind)]


def inside(path, container):
    """Whether a DAG path is `container` or a descendant of it.

    The separator matters: `|root_extra` is not a child of `|root`
    (trap 7).
    """
    if not path or not container:
        return False
    return path == container or path.startswith(container + "|")


def members_inside(members, container):
    """Whether any of `members` lies inside `container`.

    The claim test for a scene that already holds several characters.
    OverRig parks a constraint under every source joint it drives, and
    that constraint is in the manifest -- so a rig of ours always has at
    least one member inside the skeleton it was built on.
    """
    return any(inside(path, container) for path in members or [])


# ---------------------------------------------------------------------------
# scene
# ---------------------------------------------------------------------------

def _set_names():
    """Every RigPicker object set in the scene, found by prefix."""
    return sorted(name for name in (cmds.ls(type="objectSet") or [])
                  if name.startswith(PREFIX))


def _tagged_string(node, attr):
    return cmds.getAttr("{0}.{1}".format(node, attr)) or ""


def read(set_name):
    """One manifest as a Record: its tag if it has one, its name if not."""
    if cmds.attributeQuery(ROOT_ATTR, node=set_name, exists=True):
        return Record(set_name,
                      _tagged_string(set_name, ROOT_ATTR),
                      _tagged_string(set_name, KIND_ATTR),
                      _tagged_string(set_name, NAME_ATTR))
    kind, name = classify(set_name)
    return Record(set_name, "", kind, name)


def records():
    """Every RigPicker manifest in the scene, as Records.

    One pass, so a caller doing twenty lookups reads the scene once.
    """
    return [read(name) for name in _set_names()]


def find(kind, name, root_uuid=None, table=None):
    """The active character's manifest of this kind and name, or None.

    `sole_character()` is asked only when an untagged candidate exists,
    which after the first bind of a session is never -- the question walks
    every joint in the scene and this runs on every selection sync.
    """
    table = records() if table is None else table
    root_uuid = active.root_uuid() if root_uuid is None else root_uuid
    needs_sole = any(not r.root and r.kind == kind and r.name == name
                     for r in table)
    sole = active.sole_character() if needs_sole else False
    return pick(table, kind, name, root_uuid, sole)


def members(kind, name, root_uuid=None, table=None):
    """Long paths recorded in this character's manifest, [] if there is none."""
    found = find(kind, name, root_uuid, table)
    return overrig.set_members(found) if found else []


def tag(set_name, kind, name, root_uuid=None):
    """Write the identity attributes onto a manifest. Returns its name."""
    root_uuid = active.root_uuid() if root_uuid is None else root_uuid
    for attr, value in ((ROOT_ATTR, root_uuid or ""),
                        (KIND_ATTR, kind),
                        (NAME_ATTR, name)):
        if not cmds.attributeQuery(attr, node=set_name, exists=True):
            cmds.addAttr(set_name, longName=attr, dataType="string")
        cmds.setAttr("{0}.{1}".format(set_name, attr), value, type="string")
    return set_name


def ensure(kind, name, root_uuid=None):
    """This character's manifest, created and tagged if it is not there."""
    found = find(kind, name, root_uuid)
    if found:
        return found
    fresh = cmds.sets(name=set_name_for(kind, name), empty=True)
    return tag(fresh, kind, name, root_uuid)


def claim_untagged(root_uuid=None, root_path=None):
    """Tag the manifests of a rig built before tagging existed.

    Called on every bind and at the top of every build -- the two moments
    a character becomes active. With one character in the scene every
    untagged manifest is that character's. With several, a manifest is
    claimed only when one of its members lies inside the asking
    character's subtree, so two rigged characters opened together do not
    swap rigs.

    Returns the set names claimed.
    """
    root_uuid = active.root_uuid() if root_uuid is None else root_uuid
    if not root_uuid:
        return []
    root_path = active.root() if root_path is None else root_path

    table = records()
    loose = [r for r in table if not r.root and r.kind and r.kind != KIND_AIM]
    if not loose:
        return []

    everyones = active.sole_character()
    claimed = []
    for record in loose:
        if not everyones and not members_inside(
                overrig.set_members(record.set_name), root_path):
            continue
        tag(record.set_name, record.kind, record.name, root_uuid)
        claimed.append(record.set_name)
    return claimed


def activate(scene_map):
    """Make a binding map's character active and claim its old manifests.

    The one call every entry point makes before touching the scene.
    """
    root_uuid = active.adopt(scene_map)
    if root_uuid:
        claim_untagged(root_uuid, active.root())
    return root_uuid
