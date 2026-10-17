"""The side panel as plain values (stdlib only): where it stands, when it comes out,
how it unrolls. Spec: docs/superpowers/specs/2026-10-17-side-panel-design.md
"""

from maya_timebar import look as _bar

MODES = ("maya", "edge")
MODE_LABELS = (("Maya's", "maya"), ("Right edge", "edge"))
DEFAULT_MODE = "maya"       # opt-in until it has been seen in a GUI Maya
TABS = ("channels", "attributes")
TAB_LABELS = (("Channels", "channels"), ("Attributes", "attributes"))

WIDTH, MIN_WIDTH, MAX_WIDTH = 340, 260, 700     # logical px
HEADER = 30             # logical px: the tabs and the pin
GRIP = 5                # logical px: the width grip on the inner (left) side
ZONE_PX = 14            # logical px along the right edge the cursor may rest in
SENSOR_PX = 2           # physical px

ZONE_DWELL_MS = _bar.ZONE_DWELL_MS
ZONE_POLL_MS = _bar.ZONE_POLL_MS
HIDE_MS = _bar.HIDE_MS
UNROLL_MS = _bar.UNROLL_MS
CLOSE_MS = _bar.CLOSE_MS
zone_dwell = _bar.zone_dwell


def mode_from(value):
    return value if value in MODES else DEFAULT_MODE


def tab_from(value):
    return value if value in TABS else TABS[0]


def clamp_width(width):
    return int(max(MIN_WIDTH, min(MAX_WIDTH, int(round(width)))))


def side_band(window, width, scale=1.0):
    """(x, y, w, h): the panel against the right of Maya's window `window`, its
    full height, `width` logical px wide (never wider than the window)."""
    x, y, w, h = window
    pw = int(min(w, round(clamp_width(width) * float(scale or 1.0))))
    return int(x + w - pw), int(y), pw, int(h)


def sensor_band(window, px=SENSOR_PX):
    x, y, w, h = window
    return int(x + w - px), int(y), int(px), int(h)


def zone_band(window, scale=1.0):
    """The strip along the right edge where resting the cursor brings the panel out."""
    x, y, w, h = window
    zw = int(round(ZONE_PX * float(scale or 1.0)))
    return int(x + w - zw), int(y), zw, int(h)


def unroll(u, cy, height, showing):
    """(y0, y1) of the panel `u` (0..1) into its unroll from - or close onto - `cy`."""
    return _bar.unroll(u, cy, height, showing)


def dragged_width(width0, dx, scale=1.0):
    """The width after the grip on the panel's LEFT side moved `dx` physical px
    (left = wider)."""
    return clamp_width(width0 - float(dx) / float(scale or 1.0))


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
             modal=False, typing=False, dragging=False):
    """Why the panel must stay out, in a fixed order (empty: it may go)."""
    reasons = []
    for name, value in (("pinned", pinned), ("held", held), ("inside", inside),
                        ("buttons", buttons), ("popup", popup), ("modal", modal),
                        ("typing", typing), ("dragging", dragging)):
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
MEL_RESTORE = ('source "isAttributeEditorVisible.mel";', 'source "isChannelBoxVisible.mel";')
