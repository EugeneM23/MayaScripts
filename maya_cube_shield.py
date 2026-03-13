"""
Maya Cube Shield Prototype Builder
Creates a shield prototype assembled from cubes (polyCube primitives).
Run in Maya Script Editor (Python tab).
"""

import maya.cmds as cmds


def create_cube(name, tx=0, ty=0, tz=0, sx=1, sy=1, sz=1, rx=0, ry=0, rz=0):
    cube = cmds.polyCube(name=name, w=sx, h=sy, d=sz, ch=False)[0]
    cmds.move(tx, ty, tz, cube)
    cmds.rotate(rx, ry, rz, cube)
    return cube


def build_shield():
    parts = []

    # === Основная плоскость щита (собрана из плиток) ===
    # Центральная часть — крупные блоки
    for row in range(5):
        for col in range(5):
            x = (col - 2) * 0.95
            y = (row - 2) * 0.95
            # Скругляем углы — пропускаем угловые блоки
            if abs(col - 2) == 2 and abs(row - 2) == 2:
                continue
            parts.append(create_cube(
                f"shield_plate_r{row}_c{col}",
                tx=x, ty=y, tz=0,
                sx=0.9, sy=0.9, sz=0.15
            ))

    # Дополнительные блоки для скругления краёв
    corners = [
        (-1.4, 1.4), (1.4, 1.4), (-1.4, -1.4), (1.4, -1.4)
    ]
    for i, (cx, cy) in enumerate(corners):
        parts.append(create_cube(
            f"shield_corner_{i}",
            tx=cx, ty=cy, tz=0,
            sx=0.6, sy=0.6, sz=0.14
        ))

    # === Кант (обод) по периметру ===
    # Верхний и нижний
    for i in range(5):
        x = (i - 2) * 0.95
        parts.append(create_cube(f"shield_rim_top_{i}", tx=x, ty=2.25, tz=0, sx=0.9, sy=0.2, sz=0.2))
        parts.append(create_cube(f"shield_rim_bot_{i}", tx=x, ty=-2.25, tz=0, sx=0.9, sy=0.2, sz=0.2))
    # Левый и правый
    for i in range(5):
        y = (i - 2) * 0.95
        parts.append(create_cube(f"shield_rim_left_{i}", tx=-2.25, ty=y, tz=0, sx=0.2, sy=0.9, sz=0.2))
        parts.append(create_cube(f"shield_rim_right_{i}", tx=2.25, ty=y, tz=0, sx=0.2, sy=0.9, sz=0.2))

    # === Умбон (центральная выпуклость) ===
    parts.append(create_cube("shield_boss_1", tx=0, ty=0, tz=0.15, sx=1.0, sy=1.0, sz=0.15))
    parts.append(create_cube("shield_boss_2", tx=0, ty=0, tz=0.28, sx=0.7, sy=0.7, sz=0.12))
    parts.append(create_cube("shield_boss_3", tx=0, ty=0, tz=0.38, sx=0.4, sy=0.4, sz=0.1))

    # Заклёпки вокруг умбона
    rivets = [(0.7, 0.7), (-0.7, 0.7), (-0.7, -0.7), (0.7, -0.7),
              (0, 0.9), (0, -0.9), (0.9, 0), (-0.9, 0)]
    for i, (rx, ry) in enumerate(rivets):
        parts.append(create_cube(
            f"shield_rivet_{i}",
            tx=rx, ty=ry, tz=0.12,
            sx=0.12, sy=0.12, sz=0.1
        ))

    # === Крест / орнамент на щите ===
    # Вертикальная полоса
    parts.append(create_cube("shield_cross_v", tx=0, ty=0, tz=0.1, sx=0.2, sy=3.8, sz=0.06))
    # Горизонтальная полоса
    parts.append(create_cube("shield_cross_h", tx=0, ty=0.3, tz=0.1, sx=3.8, sy=0.2, sz=0.06))

    # === Угловые накладки ===
    corner_plates = [
        (1.5, 1.5), (-1.5, 1.5), (-1.5, -1.5), (1.5, -1.5)
    ]
    for i, (cx, cy) in enumerate(corner_plates):
        parts.append(create_cube(
            f"shield_corner_plate_{i}",
            tx=cx, ty=cy, tz=0.1,
            sx=0.4, sy=0.4, sz=0.08
        ))

    # === Задняя сторона: ручка и ремень ===
    # Ручка (горизонтальная перекладина)
    parts.append(create_cube("shield_handle", tx=0, ty=0, tz=-0.25, sx=1.2, sy=0.25, sz=0.2))
    # Опоры ручки
    parts.append(create_cube("shield_handle_mount_L", tx=-0.5, ty=0, tz=-0.15, sx=0.2, sy=0.3, sz=0.15))
    parts.append(create_cube("shield_handle_mount_R", tx=0.5, ty=0, tz=-0.15, sx=0.2, sy=0.3, sz=0.15))

    # Ремень для предплечья
    parts.append(create_cube("shield_strap", tx=0, ty=0.9, tz=-0.2, sx=0.8, sy=0.15, sz=0.12))
    parts.append(create_cube("shield_strap_mount_L", tx=-0.35, ty=0.9, tz=-0.12, sx=0.15, sy=0.2, sz=0.1))
    parts.append(create_cube("shield_strap_mount_R", tx=0.35, ty=0.9, tz=-0.12, sx=0.15, sy=0.2, sz=0.1))

    # === Материалы ===
    # Основной щит — дерево
    wood_mat = cmds.shadingNode("lambert", asShader=True, name="shield_wood_mat")
    wood_sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name="shield_wood_matSG")
    cmds.connectAttr(f"{wood_mat}.outColor", f"{wood_sg}.surfaceShader", force=True)
    cmds.setAttr(f"{wood_mat}.color", 0.45, 0.28, 0.12, type="double3")

    # Металл (обод, умбон, заклёпки)
    metal_mat = cmds.shadingNode("lambert", asShader=True, name="shield_metal_mat")
    metal_sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name="shield_metal_matSG")
    cmds.connectAttr(f"{metal_mat}.outColor", f"{metal_sg}.surfaceShader", force=True)
    cmds.setAttr(f"{metal_mat}.color", 0.6, 0.6, 0.65, type="double3")

    # Крест — тёмный металл
    cross_mat = cmds.shadingNode("lambert", asShader=True, name="shield_cross_mat")
    cross_sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name="shield_cross_matSG")
    cmds.connectAttr(f"{cross_mat}.outColor", f"{cross_sg}.surfaceShader", force=True)
    cmds.setAttr(f"{cross_mat}.color", 0.3, 0.3, 0.35, type="double3")

    grp = cmds.group(parts, name="shield_grp")

    # Назначаем материалы
    all_meshes = cmds.listRelatives(grp, allDescendents=True, type="mesh") or []

    # Металлические части
    metal_names = ["rim_", "boss_", "rivet_", "handle", "strap_mount", "corner_plate"]
    cross_names = ["cross_"]
    for mesh in all_meshes:
        parent = cmds.listRelatives(mesh, parent=True)[0]
        if any(tag in parent for tag in metal_names):
            cmds.sets(mesh, edit=True, forceElement=metal_sg)
        elif any(tag in parent for tag in cross_names):
            cmds.sets(mesh, edit=True, forceElement=cross_sg)
        else:
            cmds.sets(mesh, edit=True, forceElement=wood_sg)

    cmds.select(clear=True)
    cmds.viewFit(all=True)
    print("=" * 40)
    print("Shield prototype built!")
    print("=" * 40)
    return grp


build_shield()
