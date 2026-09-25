"""The weapon table: what can be attached, and where it goes.

The target bone is a property of the entry rather than a constant in the code,
so a shield later is one line with `weapon_l` and no logic to touch. `scale` is
here for the same reason: a model that arrives at the wrong size is a fact
about that model, not something the animator should retype every time.

Paths are written with forward slashes. The FBX plugin is driven through MEL,
where a backslash starts an escape.
"""
import collections
import os
import string

# `frame` (2026-09-24) is the model's own turn on its bone, XYZ degrees: where
# zero grip stands it, the node's axes on the geometry (bonedrive.FRAME_ROTATE).
# The identity for a model already on the bone's axes -- every row but one.
Weapon = collections.namedtuple("Weapon", "key label path bone scale frame",
                                defaults=((0.0, 0.0, 0.0),))

# The characters Add Character can put into the scene (2026-09-01). A table
# for the same reason the weapons are one: a third skeleton is a row, not a
# branch. `legacy` stays per entry rather than a special case because
# Manny's fallback IS the user's original file, typo and infection and all,
# and that resolution rule has to survive. `kind` (2026-09-07) is "rig" or
# "skeleton": the animator's ask was to add the AdvancedSkeleton rig and
# keep the bare skeletons, «пометим их как скелеты, а риг как риг».
Character = collections.namedtuple("Character", "key label file legacy kind")

_LEGAL = frozenset(string.ascii_letters + string.digits + "_")

# Two dirnames up from this file is the container that holds both the
# packages and assets/ -- true in the repo and in an installed copy alike.
_CONTAINER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_LEGACY_SWORD = "C:/!!!Work/Animations/Sources/LongSword_02.fbx"

# The user's original file, spelling and all: the fallback has to match what
# is actually on that disk. Our shipped copy fixes the typo.
_LEGACY_CHARACTER = ("C:/!!!Work/Animations/Rigs/Characters/"
                     "Manny_Sckeleton.ma")

# The animator's own rig file (final, their word, 2026-09-07). The shipped
# copy is this file minus its leftover `camera1` -- a textual cut, like the
# vaccine cut, never an open-and-resave.
_LEGACY_RIG = "C:/!!!Work/Animations/Rigs/Characters/Manny_rig_02.ma"


CHARACTERS = [
    # The AdvancedSkeleton rig over Manny (built 2026-09-04..05), the working
    # character since 2026-09-07: 93 UE bones under `root`, the rig under
    # `Group`, the meshes at world level. Each one arrives in its OWN
    # namespace since 2026-09-08 (`Manny_Rig`, `Manny_Rig1`, ...): the
    # retarget addresses a rig by name (`Main`, `ControlSet`, `FKWrist_R`),
    # and the namespace is what keeps those names one node each.
    Character("Manny_Rig", "Manny [rig]", "Manny_Rig.ma", _LEGACY_RIG, "rig"),
    # The Creep creature's AdvancedSkeleton rig (2026-09-24): Manny's 90 UE bone
    # names on a creature's proportions, bound in the UE A-pose, the bones rigid
    # (orientation-only constraints), the meshes in the rig's own Geometry group,
    # and `Group.skeldarRetarget = "rotation"` -- its retarget copies rotations
    # only. Built from the animator's scene by make_creep_rig_asset.py.
    Character("Creep_Rig", "Creep [rig]", "Creep_Rig.ma", "", "rig"),
    Character("Manny", "Manny UE5 [skeleton]", "Manny_Skeleton.ma",
              _LEGACY_CHARACTER, "skeleton"),
    # The Creep without its rig (2026-09-24, «не только риг хантера, а и чистый
    # скелет»): the same 90 bones in the same A-pose bind, skinned, the meshes in
    # `|Creep`, the swords riding weapon_test -- built from Creep_Rig.ma by
    # make_creep_skeleton_asset.py, nothing of AdvancedSkeleton left in it.
    Character("Creep", "Creep [skeleton]", "Creep_Skeleton.ma", "", "skeleton"),
    # 68 joints, exported once from /Game/SwordAnimsetPro/UE4_Mannequin/
    # Mesh/SK_Mannequin in the animator's own project: spine_01..03, no
    # metacarpals, no neck_02, one twist per segment. The pack animations
    # (Longsword/SwordAnimsetPro, ~1200 clips) all run on it.
    Character("UE4_Mannequin", "UE4 Mannequin [skeleton]",
              "UE4_Mannequin.fbx", "", "skeleton"),
]


def character_labels():
    """Dropdown labels, in table order."""
    return [entry.label for entry in CHARACTERS]


def character_by_label(label):
    for entry in CHARACTERS:
        if entry.label == label:
            return entry
    return None


def character_by_key(key):
    for entry in CHARACTERS:
        if entry.key == key:
            return entry
    return None


def character_keys():
    """Every character's key, in table order."""
    return [entry.key for entry in CHARACTERS]


def export_name(key):
    """The character's name for an exported file's top node (2026-09-25).

    Every export writes Cascadeur's layout -- the skeleton under a Null named for
    the character («по персонажу») -- and the rig and the bare skeleton of one
    character are one name: the key without a trailing `_Rig` (`Creep_Rig` and
    `Creep` -> `Creep`).
    """
    return key[:-len("_Rig")] if key.endswith("_Rig") else key


def default_character():
    """The Manny SKELETON.

    `character_path()` with no argument has always meant Manny_Skeleton.ma,
    and `maya_skelfit`, `verify_add_character.py` and three test modules
    ask it that way -- so this keeps answering the skeleton even though the
    rig is row 0 and the dropdown's default since 2026-09-07.
    """
    return character_by_key("Manny")


def default_rig():
    """The AdvancedSkeleton rig: what the dropdown opens on and what the
    UE bridge adds when the scene has none."""
    return CHARACTERS[0]


def is_rig(entry):
    return entry.kind == "rig"


def character_file(entry):
    """Where a character's scene is: shipped copy first, legacy second.

    Resolved at call time rather than frozen into the table -- a copy that
    appears in assets/ mid-session (a colleague re-running the installer)
    should win immediately.
    """
    local = os.path.join(_CONTAINER, "assets",
                         entry.file).replace("\\", "/")
    if os.path.isfile(local):
        return local
    return entry.legacy or local


def character_path(entry=None):
    """The working character scene. No argument still means Manny.

    Deliberately: `maya_skelfit`, `verify_add_character.py` and three test
    modules ask this question and none of them is about the dropdown.
    """
    return character_file(entry or default_character())


def _asset_path(name, legacy=""):
    """The shipped copy first, a legacy absolute path as fallback.

    Computed once at import: the table keeps holding a plain absolute
    path, so missing(), attach and the offset optionVars never learn
    that anything changed. A weapon with no legacy home answers the
    shipped path either way, and `missing()` says when it is not there.
    """
    local = os.path.join(_CONTAINER, "assets", name).replace("\\", "/")
    return local if os.path.isfile(local) or not legacy else legacy


def _sword_path():
    return _asset_path("LongSword_02.fbx", _LEGACY_SWORD)


WEAPONS = [
    Weapon("LongSword_02", "Long Sword 02", _sword_path(), "weapon_r", 1.0),
    # 2026-09-08, the animator's Spear1 exported onto the sword's axes: the
    # shaft along +Y with the head at +Y, the blade's width on X, its
    # thickness on Z, the origin on the shaft where the model's author put
    # it (59 cm above the butt). 266 cm long, so the scale is 1.0.
    Weapon("Spear_01", "Spear 01", _asset_path("Spear_01.fbx"), "weapon_r", 1.0),
    # 2026-09-17, the animator's Dagger.fbx exported onto the same axes by
    # docs/superpowers/plans/make_dagger_asset.py: blade along +Y with the
    # tip at +Y, the grip going -Y, the guard's width on X, the thickness
    # on Z, the grip centred on the origin. The model is 114 cm; the
    # animator asked for it two and a half times smaller (45.7 cm), and a
    # size correction is exactly what this column is for.
    Weapon("Dagger_01", "Dagger 01", _asset_path("Dagger_01.fbx"), "weapon_r", 0.4),
    # 2026-09-24, the Creep's own sword out of its rig («добавим меч хантера в список
    # нашего оружия»), blade AND grip (make_creep_sword_fbx.py): in the model's own
    # axes like every row -- blade +Y (tip at +74.3), guard X, thickness Z, the origin
    # where the Creep holds it. It stands in the Creep's hand turned 45 deg about the
    # bone's Y (the animator's grip that day), and that turn is its FRAME, not its
    # points: zero grip puts it there with the node's axes on the geometry («чтобы оси
    # соответствовали направлению геометрии, но меч сохранил свою позу в руке»).
    Weapon("Creep_Sword", "Creep Sword", _asset_path("Creep_Sword.fbx"), "weapon_r", 1.0,
           (0.0, 45.0, 0.0)),
]


def labels():
    """Dropdown labels, in table order."""
    return [entry.label for entry in WEAPONS]


def by_label(label):
    for entry in WEAPONS:
        if entry.label == label:
            return entry
    return None


def by_key(key):
    for entry in WEAPONS:
        if entry.key == key:
            return entry
    return None


def missing(entry):
    """The entry's path if the file is not on disk, "" if it is."""
    return "" if os.path.isfile(entry.path) else entry.path


def node_key(text):
    """`text` reduced to a legal Maya node name.

    The key is not only a string in an attribute: it names the aim manifest
    (`RigPicker_aim_<key>` reaches `cmds.sets`) and an optionVar. A space, a
    dot or a leading digit there is a traceback later, on a press that has
    nothing to do with this one.
    """
    safe = "".join(c if c in _LEGAL else "_" for c in text)
    if not safe:
        return "weapon"
    return "_" + safe if safe[0].isdigit() else safe


def entry_for_path(path, bone):
    """An entry for a file the table knows nothing about.

    The key and the label come from the file's stem, so the offsets dialled
    in for it are remembered the way any weapon's are. The bone is the
    caller's -- the dropdown's, in the window -- and the scale is 1.0 rather
    than that entry's: a size correction is a fact about one known model, and
    quietly applying the sword's to somebody else's file is a surprise.
    """
    stem = os.path.splitext(os.path.basename(path.replace("\\", "/")))[0]
    key = node_key(stem)
    return Weapon(key, key, path, bone, 1.0)
