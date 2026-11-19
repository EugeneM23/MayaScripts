"""The side panel as plain values (stdlib only): where it stands and when it comes
out. It comes out and goes back at once (2026-11-19, «удаляем все подсветки и
анимации»). Spec: docs/superpowers/specs/2026-10-17-side-panel-design.md
"""

MODES = ("maya", "edge")
MODE_LABELS = (("Maya's", "maya"), ("Right edge", "edge"))
DEFAULT_MODE = "maya"       # opt-in until it has been seen in a GUI Maya
TABS = ("channels", "attributes")
TAB_LABELS = (("Channels", "channels"), ("Attributes", "attributes"))

#  logical px; the least was 260 until 2026-10-19 («мы должны иметь возможность
#  сжать окошко в 3 раза сильнее»)
WIDTH, MIN_WIDTH, MAX_WIDTH = 340, 86, 700
#  the share of the viewport's height the panel takes from its top (2026-10-19:
#  «Сейчас наше меню растягивается до самого низа. Можно сделать его в два раза
#  короче с возможностью растянуть»), a grip on its bottom edge drags it
SHARE, MIN_SHARE, MAX_SHARE = 0.5, 0.12, 1.0
MIN_HEIGHT = 120        # logical px: never shorter, whatever the share
HEADER = 30             # logical px: the tabs and the pin
GRIP = 5                # logical px: the width grip on the inner (left) side
RADIUS = 8              # logical px: the window's corners (the hub's card radius, 2026-10-18)
#  logical px along the right edge the cursor may rest in (2026-10-17: 14, then
#  48 - «как и у таймслайдера не нужно было вести мышку до самого края»)
ZONE_PX = 62     # 48, then 30 % wider (2026-10-17, «зону срабатывания увеличим на 30%»)
SENSOR_PX = 2           # physical px

#  the Time Bar's own numbers (maya_timebar.look), spelled here so nothing of its look is imported
ZONE_DWELL_MS = 150     # the cursor resting in the zone this long brings it out
ZONE_POLL_MS = 50
HIDE_MS = 600           # half the Time Bar's 1200 ms wait (2026-10-17, «в 2 раза меньше»)


def zone_dwell(dwelt, inside, dt_ms):
    """The time the cursor has rested in the zone so far: it grows while it stays,
    and any moment outside starts it again."""
    return dwelt + dt_ms if inside else 0.0


def mode_from(value):
    return value if value in MODES else DEFAULT_MODE


def tab_from(value):
    return value if value in TABS else TABS[0]


def clamp_width(width):
    return int(max(MIN_WIDTH, min(MAX_WIDTH, int(round(width)))))


def area(pane, window, bar_height=0):
    """The rect the panel lives in (2026-10-17, «не растягивалась на весь экран а
    видела границы других интерфейсов»): the viewport area - Maya's `pane` (the
    MainPane workspaceControl, under the menus, status line, shelf and scene tabs) -
    ending above the band at the bottom of Maya's `window` where the Time Bar slides
    out (`bar_height` px, 0 without it); Maya's whole window when there is no pane."""
    rect = pane or window
    if not rect:
        return None
    x, y, w, h = (int(v) for v in rect)
    bottom = y + h
    if window and bar_height:
        bottom = min(bottom, int(window[1]) + int(window[3]) - int(bar_height))
    return x, y, w, max(1, bottom - y)


def cut_above(rect, top):
    """`rect` (x, y, w, h) ending at the global `top` (no higher than its own top + 1)."""
    x, y, w, h = (int(v) for v in rect)
    return x, y, w, max(1, min(h, int(top) - y))


def clamp_share(share):
    try:
        share = float(share)
    except (TypeError, ValueError):
        share = SHARE
    return max(MIN_SHARE, min(MAX_SHARE, share))


def panel_height(h, share=1.0, scale=1.0):
    """The panel's height in physical px out of the area's `h`: `share` of it, at
    least MIN_HEIGHT logical px, never taller than the area."""
    least = MIN_HEIGHT * float(scale or 1.0)
    return int(max(1, min(int(h), round(max(least, clamp_share(share) * float(h))))))


def side_band(window, width, scale=1.0, least=0, share=1.0):
    """(x, y, w, h): the panel against the right of Maya's window `window`, from its
    top down `share` of its height, `width` logical px wide - at least `least`
    physical px - and never wider than the window."""
    x, y, w, h = window
    pw = int(min(w, max(int(least), round(clamp_width(width) * float(scale or 1.0)))))
    return int(x + w - pw), int(y), pw, panel_height(h, share, scale)


def sensor_band(window, px=SENSOR_PX, share=1.0, scale=1.0):
    """The sensor along the right edge, as tall as the panel (2026-10-19: below a
    shorter panel the cursor would bring it straight back after it hid)."""
    x, y, w, h = window
    return int(x + w - px), int(y), int(px), panel_height(h, share, scale)


def zone_band(window, scale=1.0, share=1.0):
    """The strip along the right edge where resting the cursor brings the panel out,
    as tall as the panel."""
    x, y, w, h = window
    zw = int(round(ZONE_PX * float(scale or 1.0)))
    return int(x + w - zw), int(y), zw, panel_height(h, share, scale)


def dragged_width(width0, dx, scale=1.0):
    """The width after the grip on the panel's LEFT side moved `dx` physical px
    (left = wider)."""
    return clamp_width(width0 - float(dx) / float(scale or 1.0))


def dragged_share(share0, dy, area_h):
    """The share after the grip on the panel's BOTTOM edge moved `dy` physical px
    (down = taller) over an area `area_h` px tall."""
    return clamp_share(clamp_share(share0) + float(dy) / float(max(1, area_h)))


def channel_forms(separate):
    """The (UI component, form layout) pairs the Channels tab borrows - Maya's
    combined Channel Box / Layer Editor, or its two halves when the animator
    keeps them separate (optionVar channelsLayersSeparate)."""
    if separate:
        return (("Channel Box", "MainChannelBoxLayout"),
                ("Layer Editor", "MainLayerEditorLayout"))
    return (("Channel Box / Layer Editor", "MainChannelsLayersLayout"),)


ATTRIBUTE_FORMS = (("Attribute Editor", "MainAttributeEditorLayout"),)


def forms(tab, separate):
    return channel_forms(separate) if tab == "channels" else ATTRIBUTE_FORMS


def tab_of_component(component):
    for tab in TABS:
        for name, _form in forms(tab, False) + forms(tab, True):
            if name == component:
                return tab
    return None


def blockers(pinned=False, held=False, inside=False, buttons=False, popup=False,
             modal=False, typing=False, dragging=False, selected=False, timebar=False):
    """Why the panel must stay out, in a fixed order (empty: it may go)."""
    reasons = []
    for name, value in (("pinned", pinned), ("held", held), ("inside", inside),
                        ("buttons", buttons), ("popup", popup), ("modal", modal),
                        ("typing", typing), ("dragging", dragging), ("selected", selected),
                        ("timebar", timebar)):
        if value:
            reasons.append(name)
    return reasons


# The MEL procs redefined while the panel holds a form: Maya's text, with our
# question in front. Off, Maya's own files are sourced again.
MEL_OVERRIDE = r'''
global proc int isAttributeEditorVisible() {
	if (python("__import__('maya_sidepanel').holds('attributes')")) return true;
	if( !`exists isUIComponentVisible` ) {
		source "UIComponents.mel";
	}
	return isUIComponentVisible("Attribute Editor");
}
global proc int isChannelBoxVisible() {
	if (python("__import__('maya_sidepanel').holds('channels')")) return true;
	if(`optionVar -query channelsLayersSeparate`) {
		return isUIComponentVisible("Channel Box");
	} else {
		return isUIComponentVisible("Channel Box / Layer Editor");
	}
}
'''

# Maya's autoUpdateAttrEd defers the update while the Attribute Editor's own
# workspaceControl is not raised - and ours is hidden for good while the panel
# holds the form. This is its update, run by us when the panel shows the
# Attributes page (measured live 2026-10-17: the AE stayed on "Select an object").
MEL_REFRESH_AE = r'''
global proc skeldarSidePanelRefreshAE() {
	global int $gAEDeferredUpdate;
	global string $gAEPrevSelectedNodes[];
	global string $gAECurrentTab;
	string $nodes[] = `ls -sl -l -o -ufe`;
	int $count = size($nodes);
	if ($count == 0) return;
	string $last = $nodes[$count - 1];
	// always: Maya's own handler runs around ours and can leave the AE on
	// "Select an object" with its bookkeeping already saying the node is shown
	updateAE($last);
	$gAEPrevSelectedNodes = $nodes;
	$gAEDeferredUpdate = false;
}
'''


def min_width_px(form_widths, scale):
    """The panel's least width in physical px: what Maya's borrowed forms ask for
    (their minimumSizeHint) plus the grip, never past MAX_WIDTH."""
    need = max([0] + [int(w) for w in form_widths]) + int(round(GRIP * float(scale or 1.0)))
    return int(min(need, round(MAX_WIDTH * float(scale or 1.0))))


MEL_RESTORE = ('source "isAttributeEditorVisible.mel";', 'source "isChannelBoxVisible.mel";')
