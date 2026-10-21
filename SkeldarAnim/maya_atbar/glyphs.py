"""AT's glyphs: animBot's icons redrawn 1:1 in the SkeldarAnim hub's line style (16 x 16, 1.5 px stroke,
round caps). The same paths as the AT Rail Mockups canvas (https://claude.ai/artifact/FG74SWkoW6u2UoQ2Xw6Ak4)."""

_KEY = '<rect x="{x}" y="{y}" width="{s}" height="{s}" rx="1" fill="currentColor" stroke="none"/>'
_TIMELINE_GAP = '<path d="M6 12.5h4" stroke-width="1" stroke-dasharray="0.1 2"/>'
_SCENE = ('<circle cx="3.6" cy="3.6" r="2.7" stroke-width="1.1"/>'
          '<path d="M4.6 2.6c-.3-.3-.6-.4-1-.4-.5 0-.9.3-.9.7 0 1 2 .6 2 1.6 0 .5-.4.8-1 .8-.5 0-.8-.2-1.1-.5" '
          'stroke-width="0.9"/>')
_SCENE_KEYS = "".join(_KEY.format(x=x, y=11, s=3.5) for x in (1, 6.25, 11.5))
_CLIPBOARD = '<rect x="1" y="3" width="5" height="7" rx="1"/><path d="M2.5 3V1.8h2V3"/>'

GLYPHS = {
    "nudge_left": '<path d="M13 5H3.5M6.5 2 3.5 5l3 3"/><path d="M2 12.5h12" stroke-width="1" '
                  'stroke-dasharray="0.1 2.4"/>' + _KEY.format(x=2, y=10.5, s=4),
    "nudge_right": '<path d="M3 5h9.5M9.5 2l3 3-3 3"/><path d="M2 12.5h12" stroke-width="1" '
                   'stroke-dasharray="0.1 2.4"/>' + _KEY.format(x=10, y=10.5, s=4),
    "insert": '<path d="M8 1.5v6M5 4.5l3 3 3-3"/>' + _TIMELINE_GAP
              + _KEY.format(x=1.5, y=10.5, s=4) + _KEY.format(x=10.5, y=10.5, s=4),
    "remove": '<path d="M8 7.5v-6M5 4.5l3-3 3 3"/>' + _TIMELINE_GAP
              + _KEY.format(x=1.5, y=10.5, s=4) + _KEY.format(x=10.5, y=10.5, s=4),
    "insert_scene": '<path d="M10.5 1.5v6M8 5l2.5 2.5L13 5"/>' + _SCENE + _SCENE_KEYS,
    "remove_scene": '<path d="M10.5 7.5v-6M8 4l2.5-2.5L13 4"/>' + _SCENE + _SCENE_KEYS,
    "select_sets": '<rect x="1.5" y="2" width="11" height="8.5" rx="2"/>'
                   '<path d="M9.5 8.5l5 2.1-2.1.8-.8 2.1z" fill="currentColor"/>',
    "copy_anim": '<circle cx="10.2" cy="2.6" r="1.5"/>'
                 '<path d="M9.4 5.4 7.4 9l2.4 1.7-.9 3.8M7.4 9l-1.2 2.6-3 .2M9.4 5.4 6.3 5.7 4.6 7.6M9.4 5.4l1.8 2.2 2.4.3"/>',
    "paste_anim": _CLIPBOARD + '<circle cx="12.2" cy="3.4" r="1.3"/>'
                  '<path d="M11.5 5.8 9.8 8.9l2 1.5-.7 3.3M9.8 8.9l-1 2.2-2.2.2M11.5 5.8 9 6M11.5 5.8l1.5 1.9 2 .3"/>',
    "copy_pose": '<circle cx="8" cy="2.6" r="1.5"/>'
                 '<path d="M8 5v5.2M5 6.2h6M5 6.2 4.4 9.6M11 6.2l.6 3.4M8 10.2l-1.8 4.3M8 10.2l1.8 4.3"/>',
    "paste_pose": _CLIPBOARD + '<circle cx="11.6" cy="3.2" r="1.3"/>'
                  '<path d="M11.6 5.3v4.6M9.2 6.4h4.8M9.2 6.4l-.5 3M14 6.4l.5 3M11.6 9.9l-1.5 4.1M11.6 9.9l1.5 4.1"/>',
    "mirror": '<ellipse cx="8" cy="6.8" rx="4" ry="5.1"/><path d="M6.2 4.6c.4-.8 1-1.2 1.8-1.3"/>'
              '<path d="M2.5 13.8c1.4 1 3 .4 3.8-.9M13.5 13.8c-1.4 1-3 .4-3.8-.9"/>',
    "align": '<path d="M3 14.5V1.5"/><path d="M3 2.5h10V9H3" fill="currentColor" fill-opacity="0.25"/>',
    "relationship": '<path d="M6.6 9.4 9.4 6.6"/><path d="M7.3 4.3 8.7 2.9a2.8 2.8 0 0 1 4 4l-1.4 1.4"/>'
                    '<path d="M8.7 11.7l-1.4 1.4a2.8 2.8 0 0 1-4-4l1.4-1.4"/>',
    "world": '<circle cx="8" cy="8" r="6.3"/><ellipse cx="8" cy="8" rx="2.6" ry="6.3"/>'
             '<path d="M1.9 8h12.2M2.8 4.8h10.4M2.8 11.2h10.4" stroke-width="1.1"/>',
    "space_switch": '<rect x="1.5" y="1.5" width="3.5" height="11" rx="1"/><rect x="6.5" y="1.5" width="8" height="3" rx="1.5"/>'
                    '<rect x="6.5" y="5.5" width="8" height="3" rx="1.5" fill="currentColor" fill-opacity="0.3"/>'
                    '<rect x="6.5" y="9.5" width="3" height="3" rx="1.5"/><path d="M10.5 10.3l4.5 2-2 .7-.8 2z" fill="currentColor"/>',
    "space_switch_all": '<rect x="1.5" y="1.5" width="3.5" height="13" rx="1"/><rect x="6.5" y="1.5" width="8" height="3" rx="1.5"/>'
                        '<rect x="6.5" y="6.5" width="8" height="3" rx="1.5" fill="currentColor" fill-opacity="0.3"/>'
                        '<rect x="6.5" y="11.5" width="8" height="3" rx="1.5"/>',
    "temp_controls": '<circle cx="8" cy="2.4" r="1.4"/><path d="M8 4.4v6.1M3.5 6.2h9M8 10.5l-1.6 4M8 10.5l1.6 4"/>'
                     '<ellipse cx="8" cy="8.6" rx="6.3" ry="2.1"/>',
    "temp_pivot": '<path d="M7 6.8V1.5M9.2 9h5.3M5.4 10.6 2 14"/>'
                  '<circle cx="7" cy="9" r="2.2" fill="currentColor" fill-opacity="0.3"/>',
    "motion_trail": '<path d="M2.5 14.5C3 8.5 5 5.4 8 5.4s5 3.1 5.5 9.1"/>'
                    '<circle cx="8" cy="3.3" r="1.7" fill="currentColor" fill-opacity="0.3"/>',
    "bookmark": '<path d="M4 1.5h8v13l-4-3-4 3z"/>',
    "bookmark_panel": '<path d="M3.5 1.5h9v13l-4.5-3-4.5 3z"/>'
                      '<rect x="5.5" y="3.5" width="5" height="4" rx="0.6" stroke-width="1.1"/>',
    "more": '<g fill="currentColor" stroke="none"><circle cx="3.5" cy="8" r="1.3"/><circle cx="8" cy="8" r="1.3"/>'
            '<circle cx="12.5" cy="8" r="1.3"/></g>',
    "euler": '<path d="M11.2 4.3C10.4 3.4 9.3 3 8.1 3 6.1 3 4.8 4.2 4.8 5.6c0 1.4 1.2 2.4 3 2.4h1.4M9.2 8H7.6'
             'c-1.9 0-3.2 1-3.2 2.6 0 1.6 1.4 2.6 3.5 2.6 1.4 0 2.5-.4 3.3-1.3"/>',
    "snapshot": '<rect x="1" y="3.2" width="6.2" height="4.6" rx="1"/><circle cx="4.1" cy="5.5" r="1.1" stroke-width="1.1"/>'
                '<path d="M2.6 3.2l.5-1h2l.5 1"/><circle cx="11.6" cy="5.2" r="1.2"/>'
                '<path d="M8.2 7.8h6.8M11.6 6.6v4.2M11.6 10.8l-1.3 3.7M11.6 10.8l1.3 3.7"/>',
    "recovery": '<path d="M8 14S2 10.4 2 6.2C2 4.1 3.6 2.6 5.4 2.6c1.1 0 2 .6 2.6 1.4.6-.8 1.5-1.4 2.6-1.4 1.8 0 3.4 1.5 '
                '3.4 3.6C14 10.4 8 14 8 14z"/><path d="M8.7 5.8 7 8.7h2.3l-1.5 2.8"/>',
}


def svg(name, colour):
    """The glyph as a whole SVG document drawn in `colour`."""
    body = GLYPHS[name].replace("currentColor", colour)
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="none" stroke="%s" '
            'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">%s</svg>' % (colour, body))
