"""maya_hubicons - the outline icons the SkeldarAnim hub skin draws.

The paths are Tabler Icons 3.19.0, outline set (https://tabler.io/icons),
copied verbatim. Tabler Icons are released under the MIT License:

    MIT License. Copyright (c) 2020-2024 Paweł Kuna.
    Permission is hereby granted, free of charge, to any person obtaining a
    copy of this software and associated documentation files (the
    "Software"), to deal in the Software without restriction, including
    without limitation the rights to use, copy, modify, merge, publish,
    distribute, sublicense, and/or sell copies of the Software, and to
    permit persons to whom the Software is furnished to do so, subject to
    the following conditions: The above copyright notice and this
    permission notice shall be included in all copies or substantial
    portions of the Software. THE SOFTWARE IS PROVIDED "AS IS", WITHOUT
    WARRANTY OF ANY KIND, EXPRESS OR IMPLIED.

Each icon is its list of path `d` strings on Tabler's 24 x 24 grid (the
invisible bounding-box path every Tabler file opens with is left out).
`svg(name, colour)` puts them into an SVG with the stroke the Qt renderer
needs spelled out -- it has no CSS `currentColor` to resolve. No PNG is drawn
for any of this: these are the hub's own chrome, not shelf icons.

Stdlib only.
"""

ICONS = {
    "user": (
        "M8 7a4 4 0 1 0 8 0a4 4 0 0 0 -8 0",
        "M6 21v-2a4 4 0 0 1 4 -4h4a4 4 0 0 1 4 4v2",
    ),
    "sword": (
        "M20 4v5l-9 7l-4 4l-3 -3l4 -4l7 -9z",
        "M6.5 11.5l6 6",
    ),
    "hand-grab": (
        "M8 11v-3.5a1.5 1.5 0 0 1 3 0v2.5",
        "M11 9.5v-3a1.5 1.5 0 0 1 3 0v3.5",
        "M14 7.5a1.5 1.5 0 0 1 3 0v2.5",
        "M17 9.5a1.5 1.5 0 0 1 3 0v4.5a6 6 0 0 1 -6 6h-2h.208a6 6 0 0 1 "
        "-5.012 -2.7l-.196 -.3c-.312 -.479 -1.407 -2.388 -3.286 -5.728a1.5 "
        "1.5 0 0 1 .536 -2.022a1.867 1.867 0 0 1 2.28 .28l1.47 1.47",
    ),
    "transfer-in": (
        "M4 18v3h16v-14l-8 -4l-8 4v3",
        "M4 14h9",
        "M10 11l3 3l-3 3",
    ),
    "arrows-exchange": (
        "M7 10h14l-4 -4",
        "M17 14h-14l4 4",
    ),
    "bulb": (
        "M3 12h1m8 -9v1m8 8h1m-15.4 -6.4l.7 .7m12.1 -.7l-.7 .7",
        "M9 16a5 5 0 1 1 6 0a3.5 3.5 0 0 0 -1 3a2 2 0 0 1 -4 0a3.5 3.5 0 0 "
        "0 -1 -3",
        "M9.7 17l4.6 0",
    ),
    "palette": (
        "M12 21a9 9 0 0 1 0 -18c4.97 0 9 3.582 9 8c0 1.06 -.474 2.078 "
        "-1.318 2.828c-.844 .75 -1.989 1.172 -3.182 1.172h-2.5a2 2 0 0 0 -1 "
        "3.75a1.3 1.3 0 0 1 -1 2.25",
        "M8.5 10.5m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0",
        "M12.5 7.5m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0",
        "M16.5 10.5m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0",
    ),
    "keyboard": (
        "M2 6m0 2a2 2 0 0 1 2 -2h16a2 2 0 0 1 2 2v8a2 2 0 0 1 -2 2h-16a2 2 0 "
        "0 1 -2 -2z",
        "M6 10l0 .01",
        "M10 10l0 .01",
        "M14 10l0 .01",
        "M18 10l0 .01",
        "M6 14l0 .01",
        "M18 14l0 .01",
        "M10 14l4 .01",
    ),
    "dots-vertical": (
        "M12 12m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0",
        "M12 19m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0",
        "M12 5m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0",
    ),
    "chevron-down": (
        "M6 9l6 6l6 -6",
    ),
    "chevron-right": (
        "M9 6l6 6l-6 6",
    ),
    "plus": (
        "M12 5l0 14",
        "M5 12l14 0",
    ),
    "camera": (
        "M5 7h1a2 2 0 0 0 2 -2a1 1 0 0 1 1 -1h6a1 1 0 0 1 1 1a2 2 0 0 0 2 "
        "2h1a2 2 0 0 1 2 2v9a2 2 0 0 1 -2 2h-14a2 2 0 0 1 -2 -2v-9a2 2 0 0 "
        "1 2 -2",
        "M9 13a3 3 0 1 0 6 0a3 3 0 0 0 -6 0",
    ),
    "trash": (
        "M4 7l16 0",
        "M10 11l0 6",
        "M14 11l0 6",
        "M5 7l1 12a2 2 0 0 0 2 2h8a2 2 0 0 0 2 -2l1 -12",
        "M9 7v-3a1 1 0 0 1 1 -1h4a1 1 0 0 1 1 1v3",
    ),
    "folder": (
        "M5 4h4l3 3h7a2 2 0 0 1 2 2v8a2 2 0 0 1 -2 2h-14a2 2 0 0 1 -2 "
        "-2v-11a2 2 0 0 1 2 -2",
    ),
    "brush": (
        "M3 21v-4a4 4 0 1 1 4 4h-4",
        "M21 3a16 16 0 0 0 -12.8 10.2",
        "M21 3a16 16 0 0 1 -10.2 12.8",
        "M10.6 9a9 9 0 0 1 4.4 4.4",
    ),
    "download": (
        "M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2 -2v-2",
        "M7 11l5 5l5 -5",
        "M12 4l0 12",
    ),
    "upload": (
        "M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2 -2v-2",
        "M7 9l5 -5l5 5",
        "M12 4l0 12",
    ),
    "refresh": (
        "M20 11a8.1 8.1 0 0 0 -15.5 -2m-.5 -4v4h4",
        "M4 13a8.1 8.1 0 0 0 15.5 2m.5 4v-4h-4",
    ),
    "check": (
        "M5 12l5 5l10 -10",
    ),
    "x": (
        "M18 6l-12 12",
        "M6 6l12 12",
    ),
    "link": (
        "M9 15l6 -6",
        "M11 6l.463 -.536a5 5 0 0 1 7.071 7.072l-.534 .464",
        "M13 18l-.397 .534a5.068 5.068 0 0 1 -7.127 0a4.972 4.972 0 0 1 0 "
        "-7.071l.524 -.463",
    ),
    "unlink": (
        "M17 22v-2",
        "M9 15l6 -6",
        "M11 6l.463 -.536a5 5 0 0 1 7.071 7.072l-.534 .464",
        "M13 18l-.397 .534a5.068 5.068 0 0 1 -7.127 0a4.972 4.972 0 0 1 0 "
        "-7.071l.524 -.463",
        "M20 17h2",
        "M2 7h2",
        "M7 2v2",
    ),
    "arrow-back-up": (
        "M9 14l-4 -4l4 -4",
        "M5 10h11a4 4 0 1 1 0 8h-1",
    ),
    "backpack": (                         # the weapon inventory (2026-09-29)
        "M5 18v-6a6 6 0 0 1 6 -6h2a6 6 0 0 1 6 6v6a3 3 0 0 1 -3 3h-8a3 3 0 0 "
        "1 -3 -3z",
        "M10 6v-1a2 2 0 1 1 4 0v1",
        "M9 21v-4a2 2 0 0 1 2 -2h2a2 2 0 0 1 2 2v4",
        "M11 10h2",
    ),
    "chart-line": (                       # the Graph Overlay (2026-09-30)
        "M4 19l16 0",
        "M4 15l4 -6l4 2l4 -5l4 4",
    ),
    "send": (                             # Shared (2026-09-30)
        "M10 14l11 -11",
        "M21 3l-6.5 18a.55 .55 0 0 1 -1 0l-3.5 -7l-7 -3.5a.55 .55 0 0 1 0 "
        "-1l18 -6.5",
    ),
}

NAMES = tuple(sorted(ICONS))

_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" '
        'viewBox="0 0 24 24" fill="none" stroke="{colour}" '
        'stroke-width="{stroke}" stroke-linecap="round" '
        'stroke-linejoin="round">{paths}</svg>')


def svg(name, colour="#e4e4e6", stroke=2.0):
    """Icon `name` as SVG text stroked in `colour` (KeyError if unknown)."""
    paths = "".join('<path d="{0}"/>'.format(d) for d in ICONS[name])
    width = ("%g" % stroke)
    return _SVG.format(colour=colour, stroke=width, paths=paths)
