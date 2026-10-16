"""Ragdoll (2026-10-16): a rig falls by physics from a frame of its take, baked into its controls.

`plan` the pure half (bodies, joints, muscles, the bake's arithmetic), `sim` the Bullet scene,
`fall` the press, `weapon` Drop weapon, `panel` the hub card. Nothing is imported here, so
importing the package drags neither Maya nor Bullet in.
"""


def show_window():
    from maya_ragdoll import panel
    return panel.show_window()
