"""
Maya Cube Weapons Prototype Builder
Creates weapon prototypes assembled from cubes (polyCube primitives).
Run in Maya Script Editor (Python tab).
"""

import maya.cmds as cmds


def create_cube(name, tx=0, ty=0, tz=0, sx=1, sy=1, sz=1, rx=0, ry=0, rz=0):
    """Helper: create a named cube with transform."""
    cube = cmds.polyCube(name=name, w=sx, h=sy, d=sz, ch=False)[0]
    cmds.move(tx, ty, tz, cube)
    cmds.rotate(rx, ry, rz, cube)
    return cube


def build_crossbow(offset_x=0):
    """Арбалет — crossbow prototype from cubes."""
    parts = []

    parts.append(create_cube("xbow_stock", tx=offset_x, ty=0, tz=0, sx=6, sy=0.4, sz=0.5))
    parts.append(create_cube("xbow_grip", tx=offset_x - 0.5, ty=-0.8, tz=0, sx=0.5, sy=1.2, sz=0.5))
    parts.append(create_cube("xbow_limb", tx=offset_x + 2.5, ty=0, tz=0, sx=0.3, sy=0.3, sz=4.0))
    parts.append(create_cube("xbow_limb_tip_top", tx=offset_x + 2.7, ty=0, tz=2.0, sx=0.25, sy=0.25, sz=0.8, ry=20))
    parts.append(create_cube("xbow_limb_tip_bot", tx=offset_x + 2.7, ty=0, tz=-2.0, sx=0.25, sy=0.25, sz=0.8, ry=-20))
    parts.append(create_cube("xbow_string", tx=offset_x + 2.2, ty=0, tz=0, sx=0.05, sy=0.05, sz=3.8))
    parts.append(create_cube("xbow_bolt_shaft", tx=offset_x + 0.5, ty=0.3, tz=0, sx=4.5, sy=0.12, sz=0.12))
    parts.append(create_cube("xbow_bolt_tip", tx=offset_x + 3.0, ty=0.3, tz=0, sx=0.5, sy=0.25, sz=0.25, ry=45))
    parts.append(create_cube("xbow_trigger", tx=offset_x - 0.5, ty=-0.15, tz=0, sx=0.6, sy=0.3, sz=0.4))

    grp = cmds.group(parts, name="crossbow_grp")
    cmds.xform(grp, pivots=[offset_x, 0, 0])
    print("// Crossbow built!")
    return grp


def build_bow(offset_x=0):
    """Лук — bow prototype from cubes."""
    parts = []

    parts.append(create_cube("bow_handle", tx=offset_x, ty=0, tz=0, sx=0.4, sy=1.0, sz=0.5))

    segments_upper = [
        (0, 0.8, 0, 0.3, 0.8, 0.4, 0, 0, 3),
        (0.15, 1.6, 0, 0.28, 0.8, 0.38, 0, 0, 6),
        (0.4, 2.35, 0, 0.25, 0.75, 0.35, 0, 0, 10),
        (0.8, 3.0, 0, 0.22, 0.7, 0.32, 0, 0, 15),
        (1.3, 3.5, 0, 0.2, 0.6, 0.3, 0, 0, 20),
        (1.9, 3.85, 0, 0.18, 0.5, 0.28, 0, 0, 28),
    ]
    for i, (dx, dy, dz, w, h, d, rrx, rry, rrz) in enumerate(segments_upper):
        parts.append(create_cube(
            "bow_upper_{}".format(i), tx=offset_x + dx, ty=dy, tz=dz,
            sx=w, sy=h, sz=d, rx=rrx, ry=rry, rz=rrz
        ))

    for i, (dx, dy, dz, w, h, d, rrx, rry, rrz) in enumerate(segments_upper):
        parts.append(create_cube(
            "bow_lower_{}".format(i), tx=offset_x + dx, ty=-dy, tz=dz,
            sx=w, sy=h, sz=d, rx=rrx, ry=rry, rz=-rrz
        ))

    parts.append(create_cube("bow_string", tx=offset_x - 0.3, ty=0, tz=0, sx=0.04, sy=7.8, sz=0.04))
    parts.append(create_cube("bow_arrow_shaft", tx=offset_x - 0.6, ty=0, tz=0, sx=0.1, sy=5.5, sz=0.1))
    parts.append(create_cube("bow_arrow_tip", tx=offset_x - 0.6, ty=3.0, tz=0, sx=0.3, sy=0.5, sz=0.1))
    parts.append(create_cube("bow_arrow_fletch1", tx=offset_x - 0.6, ty=-2.5, tz=0.08, sx=0.05, sy=0.6, sz=0.2))
    parts.append(create_cube("bow_arrow_fletch2", tx=offset_x - 0.6, ty=-2.5, tz=-0.08, sx=0.05, sy=0.6, sz=0.2))

    grp = cmds.group(parts, name="bow_grp")
    cmds.xform(grp, pivots=[offset_x, 0, 0])
    print("// Bow built!")
    return grp


def build_harpoon(offset_x=0):
    """Гарпун — harpoon prototype from cubes."""
    parts = []

    parts.append(create_cube("harpoon_shaft", tx=offset_x, ty=0, tz=0, sx=0.2, sy=8.0, sz=0.2))
    parts.append(create_cube("harpoon_head_main", tx=offset_x, ty=4.4, tz=0, sx=0.5, sy=1.0, sz=0.15))
    parts.append(create_cube("harpoon_head_tip", tx=offset_x, ty=5.1, tz=0, sx=0.3, sy=0.5, sz=0.12))
    parts.append(create_cube("harpoon_head_peak", tx=offset_x, ty=5.5, tz=0, sx=0.15, sy=0.35, sz=0.1))
    parts.append(create_cube("harpoon_barb_L1", tx=offset_x - 0.3, ty=4.2, tz=0, sx=0.35, sy=0.15, sz=0.1, rz=-30))
    parts.append(create_cube("harpoon_barb_R1", tx=offset_x + 0.3, ty=4.2, tz=0, sx=0.35, sy=0.15, sz=0.1, rz=30))
    parts.append(create_cube("harpoon_barb_L2", tx=offset_x - 0.25, ty=4.6, tz=0, sx=0.3, sy=0.12, sz=0.1, rz=-25))
    parts.append(create_cube("harpoon_barb_R2", tx=offset_x + 0.25, ty=4.6, tz=0, sx=0.3, sy=0.12, sz=0.1, rz=25))

    for i in range(3):
        parts.append(create_cube(
            "harpoon_wrap_{}".format(i), tx=offset_x, ty=3.7 + i * 0.2, tz=0,
            sx=0.3, sy=0.08, sz=0.3
        ))

    parts.append(create_cube("harpoon_rope", tx=offset_x + 0.15, ty=-1.0, tz=0, sx=0.05, sy=5.0, sz=0.05))
    parts.append(create_cube("harpoon_grip", tx=offset_x, ty=-3.2, tz=0, sx=0.35, sy=1.5, sz=0.35))
    parts.append(create_cube("harpoon_pommel", tx=offset_x, ty=-4.1, tz=0, sx=0.5, sy=0.25, sz=0.5))

    grp = cmds.group(parts, name="harpoon_grp")
    cmds.xform(grp, pivots=[offset_x, 0, 0])
    print("// Harpoon built!")
    return grp


def build_wolverine_claws(offset_x=0):
    """Когти Росомахи — Wolverine claws prototype from cubes."""
    parts = []

    parts.append(create_cube("wclaws_fist", tx=offset_x, ty=0, tz=0, sx=1.8, sy=1.0, sz=1.2))
    parts.append(create_cube("wclaws_wrist", tx=offset_x - 1.2, ty=0, tz=0, sx=1.0, sy=0.9, sz=1.0))

    for i in range(4):
        z = -0.45 + i * 0.3
        parts.append(create_cube(
            "wclaws_knuckle_{}".format(i), tx=offset_x + 0.9, ty=0.15, tz=z,
            sx=0.2, sy=0.35, sz=0.22
        ))

    claw_offsets_z = [-0.3, 0, 0.3]
    for i, cz in enumerate(claw_offsets_z):
        parts.append(create_cube(
            "wclaws_claw_base_{}".format(i),
            tx=offset_x + 1.5, ty=0.1, tz=cz, sx=1.2, sy=0.08, sz=0.15
        ))
        parts.append(create_cube(
            "wclaws_claw_mid_{}".format(i),
            tx=offset_x + 2.8, ty=0.1, tz=cz, sx=1.5, sy=0.07, sz=0.12
        ))
        parts.append(create_cube(
            "wclaws_claw_tip_{}".format(i),
            tx=offset_x + 4.0, ty=0.1, tz=cz, sx=1.0, sy=0.05, sz=0.08
        ))

    parts.append(create_cube("wclaws_plate", tx=offset_x + 0.2, ty=0.55, tz=0, sx=1.2, sy=0.15, sz=1.0))

    grp = cmds.group(parts, name="wolverine_claws_grp")
    cmds.xform(grp, pivots=[offset_x, 0, 0])
    print("// Wolverine claws built!")
    return grp


def build_ak47(offset_x=0):
    """АК-47 — Kalashnikov assault rifle prototype from cubes."""
    parts = []

    # Ствольная коробка (receiver)
    parts.append(create_cube("ak_receiver", tx=offset_x, ty=0, tz=0, sx=4.0, sy=0.7, sz=0.65))

    # Ствол (barrel)
    parts.append(create_cube("ak_barrel", tx=offset_x + 4.0, ty=0.05, tz=0, sx=4.5, sy=0.3, sz=0.3))

    # Газовая трубка (gas tube) — над стволом
    parts.append(create_cube("ak_gas_tube", tx=offset_x + 3.5, ty=0.45, tz=0, sx=3.5, sy=0.2, sz=0.22))

    # Цевьё (handguard) — накладка на газовую трубку
    parts.append(create_cube("ak_handguard", tx=offset_x + 3.0, ty=0.15, tz=0, sx=3.0, sy=0.55, sz=0.55))

    # Мушка (front sight)
    parts.append(create_cube("ak_front_sight", tx=offset_x + 6.0, ty=0.5, tz=0, sx=0.1, sy=0.6, sz=0.1))
    parts.append(create_cube("ak_front_sight_base", tx=offset_x + 6.0, ty=0.15, tz=0, sx=0.25, sy=0.15, sz=0.3))

    # Целик (rear sight)
    parts.append(create_cube("ak_rear_sight", tx=offset_x + 1.5, ty=0.55, tz=0, sx=0.3, sy=0.3, sz=0.25))

    # Крышка ствольной коробки (dust cover)
    parts.append(create_cube("ak_dust_cover", tx=offset_x + 0.5, ty=0.45, tz=0, sx=2.5, sy=0.15, sz=0.55))

    # Пистолетная рукоять (pistol grip)
    parts.append(create_cube("ak_pistol_grip", tx=offset_x - 0.8, ty=-0.9, tz=0, sx=0.35, sy=1.2, sz=0.5, rz=15))

    # Спусковая скоба (trigger guard)
    parts.append(create_cube("ak_trigger_guard_front", tx=offset_x - 0.2, ty=-0.55, tz=0, sx=0.08, sy=0.5, sz=0.3))
    parts.append(create_cube("ak_trigger_guard_bottom", tx=offset_x - 0.5, ty=-0.78, tz=0, sx=0.7, sy=0.08, sz=0.3))
    parts.append(create_cube("ak_trigger", tx=offset_x - 0.5, ty=-0.55, tz=0, sx=0.08, sy=0.35, sz=0.15))

    # Приклад (stock) — деревянный, характерная форма АК
    parts.append(create_cube("ak_stock_main", tx=offset_x - 3.0, ty=-0.2, tz=0, sx=3.5, sy=0.6, sz=0.5, rz=-5))
    parts.append(create_cube("ak_stock_butt", tx=offset_x - 4.8, ty=-0.55, tz=0, sx=0.6, sy=1.0, sz=0.55))

    # Магазин (magazine) — характерный изогнутый рожок
    parts.append(create_cube("ak_mag_top", tx=offset_x + 0.2, ty=-0.7, tz=0, sx=0.6, sy=0.6, sz=0.45))
    parts.append(create_cube("ak_mag_mid", tx=offset_x + 0.35, ty=-1.3, tz=0, sx=0.55, sy=0.7, sz=0.4, rz=-8))
    parts.append(create_cube("ak_mag_bottom", tx=offset_x + 0.5, ty=-1.9, tz=0, sx=0.5, sy=0.6, sz=0.38, rz=-15))

    # Дульный компенсатор (muzzle brake)
    parts.append(create_cube("ak_muzzle", tx=offset_x + 6.4, ty=0.05, tz=0, sx=0.5, sy=0.35, sz=0.35))

    grp = cmds.group(parts, name="ak47_grp")
    cmds.xform(grp, pivots=[offset_x, 0, 0])
    print("// AK-47 built!")
    return grp


def assign_color(grp_name, color):
    """Assign a Lambert material with given color to a group."""
    if not cmds.objExists(grp_name):
        return
    mat_name = grp_name.replace("_grp", "_mat")
    sg_name = mat_name + "SG"
    if not cmds.objExists(mat_name):
        mat_name = cmds.shadingNode("lambert", asShader=True, name=mat_name)
        sg_name = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=sg_name)
        cmds.connectAttr("{}.outColor".format(mat_name),
                         "{}.surfaceShader".format(sg_name), force=True)
    cmds.setAttr("{}.color".format(mat_name), *color, type="double3")
    children = cmds.listRelatives(grp_name, allDescendents=True, type="mesh") or []
    if children:
        cmds.sets(children, edit=True, forceElement=sg_name)


COLOR_MAP = {
    "crossbow_grp": (0.35, 0.2, 0.1),
    "bow_grp": (0.55, 0.35, 0.15),
    "harpoon_grp": (0.5, 0.5, 0.55),
    "wolverine_claws_grp": (0.75, 0.75, 0.8),
    "ak47_grp": (0.3, 0.28, 0.2),
}

WEAPONS = {
    "Crossbow": (build_crossbow, "crossbow_grp"),
    "Bow": (build_bow, "bow_grp"),
    "Harpoon": (build_harpoon, "harpoon_grp"),
    "Wolverine Claws": (build_wolverine_claws, "wolverine_claws_grp"),
    "AK-47": (build_ak47, "ak47_grp"),
}


def spawn_weapon(weapon_name, *_args):
    """Create an instance of a weapon at the origin."""
    if weapon_name not in WEAPONS:
        cmds.warning("Unknown weapon: {}".format(weapon_name))
        return

    build_func, grp_name = WEAPONS[weapon_name]

    # Build at origin
    grp = build_func(offset_x=0)

    # Apply color
    if grp_name in COLOR_MAP:
        assign_color(grp, COLOR_MAP[grp_name])

    cmds.select(grp)
    cmds.headsUpMessage("{} spawned!".format(weapon_name))
    return grp


# ---------------------------------------------------------------------------
#  UI
# ---------------------------------------------------------------------------

def show_weapons_ui():
    win_id = "cubeWeaponsWin"

    if cmds.window(win_id, exists=True):
        cmds.deleteUI(win_id)

    cmds.window(win_id, title="Cube Weapons", widthHeight=(280, 280), sizeable=True)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=4, columnOffset=("both", 10))

    cmds.separator(height=8, style="none")
    cmds.text(label="Weapon Blockout Spawner", font="boldLabelFont", align="center")
    cmds.separator(height=8, style="in")

    btn_data = [
        ("Crossbow", (0.45, 0.3, 0.15)),
        ("Bow", (0.6, 0.45, 0.2)),
        ("Harpoon", (0.5, 0.5, 0.55)),
        ("Wolverine Claws", (0.7, 0.7, 0.75)),
        ("AK-47", (0.4, 0.35, 0.25)),
    ]

    for name, bg in btn_data:
        cmds.button(label=name, height=32, backgroundColor=bg,
                    command=lambda *_, n=name: spawn_weapon(n))

    cmds.separator(height=4, style="none")
    cmds.text(label="Click to spawn at origin",
              font="smallFixedWidthFont", align="center")

    cmds.showWindow(win_id)


show_weapons_ui()
