"""Which parts of the shelf are switched on. Stdlib only.

2026-09-07, the animator: «отключим все что связано с over rig и полностью
перейдем на наш риг и ретаргет адванцед скелетон. Отключаем пикер пока он
не нужен (но оставь его где-то, удалять не нужно из проекта)». Nothing is
deleted: `maya_overrig`, the picker, their tests and verify scripts stay
whole in the repo and in the payload, and flipping a flag here brings the
buttons and the hotkey rows back.

Read by `install.button_specs` (the shelf), `maya_hotkeys.commands` (the
rows), `maya_scenesetup.character.connect` (handing a new character to the
picker) and the two `picker_root()` fallbacks in `maya_scenesetup.skeleton`
and `maya_uebridge.animimport`.

Spec: docs/superpowers/specs/2026-09-07-advancedskeleton-pipeline-design.md
(OVERRIG, PICKER); docs/superpowers/specs/2026-09-08-many-rigs-design.md
(OVERSHOOT).
"""

# The native OverRig panel button and the 84 OverRig hotkey rows.
OVERRIG = False

# The Rig Picker button, its six hotkey rows, and connecting a freshly
# added character to the open picker.
PICKER = False

# The Overshoot button and its six hotkey rows (the window and the five
# shapes). Off since 2026-09-08 («уберем с нашей полки оверлапер»); the
# module ships, and this flag brings the button back.
OVERSHOOT = False
