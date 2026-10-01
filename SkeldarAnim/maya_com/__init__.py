"""Center of Mass: a live point, a fast trail of it, and a tool that moves it.

2026-10-01, the animator: «у нас должна быть какая-то точка к которой мы можем
сделать motion trail и он будет показывать нам центр массы … передвигать сам
центр массы и при этом наш риг в зависимости от карты весов тоже будет
двигаться корректно … эта система должна быть производительна».

- `massmodel` (numpy, pure): the body as a voxel union of the character's
  capped mesh shells, skinned per joint -> a mass and a local centre a joint.
- `network` (cmds): nine stock nodes that sum those into the live point.
- `engine`: the trail - dirty frames walked through the parallel EM in idle
  slices, written into Maya's own motionTrailShape.
- `drag`: the CoM tool - drag the point, every part of the body follows.
- `panel`: the hub's Center of Mass section.

Spec: docs/superpowers/specs/2026-10-01-center-of-mass-design.md
"""


def __getattr__(name):
    #  The hub imports `maya_com.panel` itself; this keeps `import maya_com`
    #  free of cmds for the pure tests.
    if name in ("build_panel", "show_window", "is_open"):
        from maya_com import panel
        return getattr(panel, name)
    raise AttributeError(name)
