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
# `texture` (2026-09-28) is the shipped image the weapon arrives in instead of
# a palette colour (colour.paint_texture); "" for every row that has none.
Weapon = collections.namedtuple("Weapon",
                                "key label path bone scale frame texture",
                                defaults=((0.0, 0.0, 0.0), ""))

# The characters Add Character can put into the scene (2026-09-01). A table
# for the same reason the weapons are one: a third skeleton is a row, not a
# branch. `kind` (2026-09-07) is "rig" or "skeleton": the animator's ask was
# to add the AdvancedSkeleton rig and keep the bare skeletons, «пометим их
# как скелеты, а риг как риг». The `legacy` column -- a fallback to the
# animator's own files under Animations/, Manny's infected original among
# them -- went on 2026-09-28: the plugin reads nothing outside its folder,
# and the sources live in the repository's sources/ (never shipped).
# `textured` (2026-09-28, the Orc D) marks a row that arrives in its OWN
# materials -- Unreal's textures, shipped under assets/ and named relatively in
# the asset -- rather than in a palette colour (colour.relink_images).
# `model` (2026-09-30, the portrait grid) groups the rows by what they look
# like: one portrait per model, the kind chosen by a [Rig | Skeleton] switch.
Character = collections.namedtuple("Character", "key label file kind textured model",
                                   defaults=(False, ""))

_LEGAL = frozenset(string.ascii_letters + string.digits + "_")

# Two dirnames up from this file is the container that holds both the
# packages and assets/ -- true in the repo and in an installed copy alike.
_CONTAINER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


CHARACTERS = [
    # The AdvancedSkeleton rig over Manny (built 2026-09-04..05), the working
    # character since 2026-09-07: 93 UE bones under `root`, the rig under
    # `Group`, the meshes at world level. Each one arrives in its OWN
    # namespace since 2026-09-08 (`Manny_Rig`, `Manny_Rig1`, ...): the
    # retarget addresses a rig by name (`Main`, `ControlSet`, `FKWrist_R`),
    # and the namespace is what keeps those names one node each. Textured
    # since 2026-09-30 («для нашего мени рига и скелета найдем текстуры ...
    # точно так же как и для орка»): Unreal's own UE5 mannequin maps (the Orc
    # Marauder pack's demo copy, our UVs exactly) at 2048, two materials by
    # Unreal's two slots, the chest logo baked in (assets/Manny/;
    # make_manny_textured_assets.py dressed the .ma in place).
    Character("Manny_Rig", "Manny [rig]", "Manny_Rig.ma", "rig", textured=True,
              model="Manny"),
    # The Creep creature's AdvancedSkeleton rig (2026-09-24): Manny's 90 UE bone
    # names on a creature's proportions, bound in the UE A-pose, the bones rigid
    # (orientation-only constraints), the meshes in the rig's own Geometry group,
    # and `Group.skeldarRetarget = "rotation"` -- its retarget copies rotations
    # only. Built from the animator's scene by make_creep_rig_asset.py. Since
    # 2026-09-28 the skeleton in the layout of the Creep's own FBX -- `root`
    # under a Null `Armature` turned -90 X («как в файле, единообразно», «и риг
    # крипа тоже»; make_creep_armature_layout.py). Textured since 2026-09-30
    # («Вот текстуры для крипа давай сделаем тоже самое что и для мени», «Весь
    # Крип»): the body, the head and the back/arms set of its own Cascadeur FBX,
    # whose UVs its meshes carry, at 2048 (assets/Creep/; dressed in place by
    # make_creep_textured_assets.py, the pipeline's last step).
    Character("Creep_Rig", "Creep [rig]", "Creep_Rig.ma", "rig", textured=True,
              model="Creep"),
    # The Orc Marauder D (2026-09-28, «еще один вариант орка ... SK_Orc_Marauder_D ... материал с
    # текстурами»): the Orc rig -- the Unreal asset's AdvancedSkeleton rig on Manny's bone names
    # with its own proportions (neck 1.39x, upper arm 1.07x), Manny's four helper bones, the
    # shoulder pads riding their clavicles, the Creep's procedure and rotation-only mark -- with
    # D's mesh re-skinned onto its game joints (D's skeleton is F's to 0.0; the skirt's
    # cloth-simulation proxy dropped), in materials carrying Unreal's own textures at 2048 with its
    # material maths baked in (assets/Orc_D/, the animator's pick: «2048, JPG»). Built by
    # make_orc_d_rig_asset.py from sources/orc/Orc_Rig.ma -- the untextured «Orc [rig]», which left
    # the plugin the same day («орка без текстур уберем из плагина он больше не нужен»).
    Character("Orc_D_Rig", "Orc D [rig]", "Orc_D_Rig.ma", "rig", textured=True,
              model="Orc_D"),
    # The same two meshes in the same maps as the rig (2026-09-30).
    Character("Manny", "Manny UE5 [skeleton]", "Manny_Skeleton.ma",
              "skeleton", textured=True, model="Manny"),
    # The Creep without its rig (2026-09-24, «не только риг хантера, а и чистый
    # скелет»): the same 90 bones in the same bind, skinned -- built from
    # Creep_Rig.ma by make_creep_skeleton_asset.py, nothing of AdvancedSkeleton
    # left in it. Since 2026-09-28 laid out as the Creep's own FBX
    # (Animations/Rigs/Characters/Creep_Skeleton.fbx): `root` under a Null
    # `Armature`, the five meshes at the top beside it.
    # The same five meshes in the same maps as the rig (2026-09-30).
    Character("Creep", "Creep [skeleton]", "Creep_Skeleton.ma", "skeleton",
              textured=True, model="Creep"),
    # 68 joints, exported once from /Game/SwordAnimsetPro/UE4_Mannequin/
    # Mesh/SK_Mannequin in the animator's own project: spine_01..03, no
    # metacarpals, no neck_02, one twist per segment. The pack animations
    # (Longsword/SwordAnimsetPro, ~1200 clips) all run on it.
    Character("UE4_Mannequin", "UE4 Mannequin [skeleton]",
              "UE4_Mannequin.fbx", "skeleton", model="UE4_Mannequin"),
]


# The portrait grid (2026-09-30, «сетка с портретами»): one portrait per MODEL,
# in this order, the kind chosen by a [Rig | Skeleton] switch above it. A row
# is (model, kind): Orc D has no skeleton, the UE4 Mannequin no rig.
Model = collections.namedtuple("Model", "key label")
KINDS = ("rig", "skeleton")

# The Auto card (2026-10-02, «сделаем карточку рига и скелета со знаком вопроса ... если он найдет
# скелет который совпадает с нашим то перенесем анимацию на наш риг или скелет, если ... совпадений
# нету то импортируем в сцену родной риг или скелет»): a portrait with no row of its own, pickable in
# both kinds. An import with it picked puts the clip on OUR rig / skeleton of that kind whose
# skeleton the clip's is (maya_uebridge.skeletonmatch), else brings the clip in its own skeleton.
# Spec: docs/superpowers/specs/2026-10-02-auto-character-import-design.md.
AUTO = "Auto"

MODELS = [Model("Manny", "Manny"), Model("Creep", "Creep"),
          Model("Orc_D", "Orc D"), Model("UE4_Mannequin", "UE4 Mannequin"),
          Model(AUTO, "Auto")]


def is_auto(model):
    """Whether `model` (a key) is the Auto card."""
    return model == AUTO


def model_by_key(key):
    for model in MODELS:
        if model.key == key:
            return model
    return None


def model_of(entry):
    """The Model a character row shows, or None."""
    return model_by_key(getattr(entry, "model", "") or "")


def character_for(model, kind):
    """The row of `model` in `kind`, or None when the model has no such row (the Auto card has
    none in either kind: it is not a character, it finds one)."""
    for entry in CHARACTERS:
        if entry.model == model and entry.kind == kind:
            return entry
    return None


def kinds_of(model):
    """The kinds `model` ships in, in KINDS order - every kind for the Auto card, which brings
    whatever the clip it imports turns out to be."""
    if is_auto(model):
        return KINDS
    return tuple(kind for kind in KINDS if character_for(model, kind))


def rows_of_kind(kind):
    """The catalog rows of `kind`, in table order: what the Auto card matches a clip among."""
    return [entry for entry in CHARACTERS if entry.kind == kind]


def default_model():
    """The model the grid opens on: the default rig's."""
    return default_rig().model


def portrait_path(model):
    """The model's square portrait (256 px PNG with alpha), under assets/.
    Rendered once by docs/superpowers/plans/make_character_portraits.py."""
    return asset_path("character_portraits/{0}.png".format(model))


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
    """Where a character's scene is: the plugin's assets/, and only there.

    A missing copy still answers its path, so the refusal names the file
    rather than reading as a bug.
    """
    return os.path.join(_CONTAINER, "assets", entry.file).replace("\\", "/")


def character_path(entry=None):
    """The working character scene. No argument still means Manny.

    Deliberately: `maya_skelfit`, `verify_add_character.py` and three test
    modules ask this question and none of them is about the dropdown.
    """
    return character_file(entry or default_character())


def asset_path(name):
    """`name` -- a file, or a path under it like "Orc_D/Orc_D_Body_Color.jpg" -- in
    the plugin's assets/, forward slashes (they reach MEL).

    The weapon rows compute it once at import: the table holds a plain absolute
    path, and `missing()` says when the file is not there. No fallback outside
    the plugin since 2026-09-28. A textured character's images are resolved
    through it at Add (2026-09-28), so they land on the installed copy.
    """
    return os.path.join(_CONTAINER, "assets", name).replace("\\", "/")


_asset_path = asset_path


WEAPONS = [
    Weapon("LongSword_02", "Long Sword 02", _asset_path("LongSword_02.fbx"),
           "weapon_r", 1.0),
    # 2026-09-08, the animator's Spear1 exported onto the sword's axes: the
    # shaft along +Y with the head at +Y, the blade's width on X, its
    # thickness on Z, the origin on the shaft where the model's author put
    # it (59 cm above the butt). 266 cm long, so the scale is 1.0.
    Weapon("Spear_01", "Spear 01", _asset_path("Spear_01.fbx"), "weapon_r", 1.0),
    # 2026-09-28, the animator's Spear_03.fbx + Halberd_A.tga («это должно
    # выдаваться сразу с текстурой»), built by
    # docs/superpowers/plans/make_spear03_asset.py: the LOD0 alone, a quarter
    # turn about Y onto the sword's axes (the head's width on X), 199.6 cm
    # with the origin at Spear 01's fraction of the length from the butt
    # (0.2233, the animator's pick), the TGA as a lossless PNG. The first row
    # that arrives in its texture rather than a palette colour.
    Weapon("Spear_03", "Spear 03", _asset_path("Spear_03.fbx"), "weapon_r", 1.0,
           texture=_asset_path("Spear_03.png")),
    # 2026-09-17, the animator's Dagger.fbx exported onto the same axes by
    # docs/superpowers/plans/make_dagger_asset.py: blade along +Y with the
    # tip at +Y, the grip going -Y, the guard's width on X, the thickness
    # on Z, the grip centred on the origin. The model is 114 cm; the
    # animator asked for it two and a half times smaller (45.7 cm), and a
    # size correction is exactly what this column is for.
    Weapon("Dagger_01", "Dagger 01", _asset_path("Dagger_01.fbx"), "weapon_r", 0.4),
    # 2026-09-24, the Creep's own sword out of its rig («добавим меч хантера в список
    # нашего оружия»), blade AND grip (make_creep_sword_fbx.py): in the model's own
    # axes like every row -- blade +Y (tip at +98.1), guard X, thickness Z, the origin
    # where the Creep holds it, 124.0 cm long: the size the creature holds it at, its
    # arm's 1.32 scale kept in the points (2026-09-25, «меч крипа стал меньше чем был
    # изначально»). It stands in the Creep's hand turned 45 deg about the
    # bone's Y (the animator's grip that day), and that turn is its FRAME, not its
    # points: zero grip puts it there with the node's axes on the geometry («чтобы оси
    # соответствовали направлению геометрии, но меч сохранил свою позу в руке»).
    Weapon("Creep_Sword", "Creep Sword", _asset_path("Creep_Sword.fbx"), "weapon_r", 1.0,
           (0.0, 45.0, 0.0)),
]

# 2026-09-30, «по умолчанию все виды оружия вставлялись в руку правильно без
# офсетов»: every rig's weapon bone is UE's weapon_r (measured: the grip line
# pinky -> index along its +Z, the palm normal along -Y, on Manny and the Orc D;
# the Creep's were turned to match), while every row above lies in its model's
# own axes (blade +Y, width X, thickness Z). This quarter turn takes the one
# into the other; a row's `frame` is the model's OWN extra turn before it (the
# Creep Sword's 45 about its blade). bonedrive.socket_frame composes the two.
SOCKET_TURN = (90.0, 0.0, 0.0)


# The armor table (2026-10-01, the Armor card: «отдельную панель Armor в
# которой пока будет только техно лимб но позже мы добавим еще разные
# варианты одежды и брони ... выделять предмет нажимать кнопочку equip и он
# будет добавляться к нашему персонажу в заранее указанное место»). A row is
# a rigid piece riding one bone: `bone` is where it is equipped, `slot` what
# it occupies on a character -- Equip takes off whatever that slot held, so a
# second plate for the same forearm is a row with the same slot. The model's
# points are already in the bone's local axes at its place, so equipped it
# stands at identity in its space (`armor.equip`) and its channels read 0.
Armor = collections.namedtuple("Armor", "key label path bone slot texture",
                               defaults=("",))

ARMOR = [
    # Atone's Tech Limb (2026-10-01): the SKELETAL shield the game animates
    # (SKM_Techlimb_Shield on SK_Techlimb_Shield: Root, Main, 36 rim joints;
    # the evening's ask: «в игре у нас есть скелет для щита»), on the
    # techlimb's equip socket `lowerarm_l` -- no socket of that name on the
    # Manny meshes, so the game snaps the actor onto the bone, the shield at
    # identity on it -- in the game's Block Idle (the clips force root lock:
    # Root on the bone, Main 21 cm down the forearm), posed by
    # docs/superpowers/plans/make_techlimb_shield_asset.py in a group standing
    # for the bone's space. The morning's static plate (Tech_Limb.fbx) is
    # retired.
    Armor("Tech_Limb", "Tech Limb", _asset_path("Armor/Tech_Limb_Shield.ma"),
          "lowerarm_l", "left_forearm"),
]


def armor_labels():
    """The armor rows' labels, in table order."""
    return [entry.label for entry in ARMOR]


def armor_by_key(key):
    for entry in ARMOR:
        if entry.key == key:
            return entry
    return None


def armor_by_label(label):
    for entry in ARMOR:
        if entry.label == label:
            return entry
    return None


def armor_icon_path(key):
    """A row's square icon (256 px PNG with alpha), under assets/. Rendered by
    docs/superpowers/plans/make_armor_icons.py."""
    return asset_path("armor_icons/{0}.png".format(key))


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


SIDES = ("R", "L")


def side_bone(bone, side):
    """The drive bone `side`'s hand uses for a row whose bone is `bone`. Pure.

    The rows name the right hand's bone (`weapon_r`); the left hand takes its
    twin (2026-09-29, two weapons per character): a trailing `_r` becomes `_l`
    and back. A bone with no side suffix is its own twin.
    """
    if side == "L" and bone.endswith("_r"):
        return bone[:-2] + "_l"
    if side == "R" and bone.endswith("_l"):
        return bone[:-2] + "_r"
    return bone


def missing(entry):
    """The entry's model -- or its texture -- if not on disk, "" if both are."""
    if not os.path.isfile(entry.path):
        return entry.path
    texture = getattr(entry, "texture", "")
    return texture if texture and not os.path.isfile(texture) else ""


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
