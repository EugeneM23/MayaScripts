"""Which parts of the shelf are switched on. Stdlib only.

2026-09-07, the animator: «отключим все что связано с over rig и полностью
перейдем на наш риг и ретаргет адванцед скелетон. Отключаем пикер пока он
не нужен (но оставь его где-то, удалять не нужно из проекта)». Nothing is
deleted: `maya_overrig`, the picker, their tests and verify scripts stay
whole in the repo and in the payload, and flipping a flag here brings the
buttons and the hotkey rows back.

2026-09-19, the animator: «из нашей полки уберем все лишнии скрипты. Пока
пусть будет только наш SkeldarAnim ну и овер риг тоже пускай
устанавливается вместе с ним». The shipped shelf is TWO buttons -- the hub
and OverRig's native panel -- and the seven section buttons wait behind
SECTION_BUTTONS the way the picker waits behind PICKER.

Read by `install.button_specs` (the shelf), `maya_hotkeys.commands` (the
rows), `maya_scenesetup.character.connect` (handing a new character to the
picker) and the two `picker_root()` fallbacks in `maya_scenesetup.skeleton`
and `maya_uebridge.animimport`.

Spec: docs/superpowers/specs/2026-09-07-advancedskeleton-pipeline-design.md
(OVERRIG, PICKER); docs/superpowers/specs/2026-09-08-many-rigs-design.md
(OVERSHOOT); docs/superpowers/specs/2026-09-19-two-button-shelf-design.md
(SECTION_BUTTONS, OVERRIG_HOTKEYS).
"""

# The native OverRig panel button on the shelf (Pavel Barnev's own
# installer command, pointing at the shipped overrig/). On since
# 2026-09-19; the hotkey rows are a flag of their own below.
OVERRIG = True

# The 84 OverRig hotkey rows (every one-press procedure in the author's
# function_for_hotkeys.TXT) in the Hotkey Editor's OverRig category. Off:
# the animator asked for the button alone.
OVERRIG_HOTKEYS = False

# The seven per-section shelf buttons -- UE Bridge, Characters, Weapons,
# Retarget, Hotkeys, Studio, Colour -- each opening the hub on its own
# section. Off since 2026-09-19; the hub button reaches every section,
# and the sections, their icons and their hotkey rows all still ship.
SECTION_BUTTONS = False

# The Rig Picker button, its six hotkey rows, and connecting a freshly
# added character to the open picker.
PICKER = False

# The Overshoot button and its six hotkey rows (the window and the five
# shapes). Off since 2026-09-08 («уберем с нашей полки оверлапер»); the
# module ships, and this flag brings the button back.
OVERSHOOT = False
