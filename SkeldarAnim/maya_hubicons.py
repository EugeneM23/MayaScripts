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
    "run": (                              # a UE Bridge drag (2026-10-01)
        "M13 4m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0",
        "M4 17l5 1l.75 -1.5",
        "M15 21l0 -4l-4 -3l1 -6",
        "M7 12l0 -3l5 -1l3 3l3 1",
    ),
    "aperture": (                         # the Radial Menu (2026-10-15)
        "M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0 -18 0",
        "M3.6 15h10.55",
        "M6.551 4.938l3.26 10.034",
        "M17.032 4.636l-8.535 6.201",
        "M20.559 14.51l-8.535 -6.201",
        "M12.257 20.916l3.261 -10.034",
    ),
    "target": (                           # Center of Mass (2026-10-01)
        "M12 12m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0",
        "M12 12m-5 0a5 5 0 1 0 10 0a5 5 0 1 0 -10 0",
        "M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0 -18 0",
    ),
    "send": (                             # Shared (2026-09-30)
        "M10 14l11 -11",
        "M21 3l-6.5 18a.55 .55 0 0 1 -1 0l-3.5 -7l-7 -3.5a.55 .55 0 0 1 0 "
        "-1l18 -6.5",
    ),
    "archive": (                          # Stash (2026-10-09)
        "M3 4m0 1a1 1 0 0 1 1 -1h16a1 1 0 0 1 1 1v2a1 1 0 0 1 -1 1h-16a1 1 0 0 1 -1 -1z",
        "M4 8l1 11a2 2 0 0 0 2 2h10a2 2 0 0 0 2 -2l1 -11",
        "M10 12l4 0",
    ),
    "shield": (                           # Armor (2026-10-01)
        "M12 3a12 12 0 0 0 8.5 3a12 12 0 0 1 -8.5 15a12 12 0 0 1 -8.5 -15a12 "
        "12 0 0 0 8.5 -3",
    ),
    "books": (                            # the Pose Library (2026-10-02)
        "M5 4m0 1a1 1 0 0 1 1 -1h2a1 1 0 0 1 1 1v14a1 1 0 0 1 -1 1h-2a1 1 0 0 1 -1 -1z",
        "M9 4m0 1a1 1 0 0 1 1 -1h2a1 1 0 0 1 1 1v14a1 1 0 0 1 -1 1h-2a1 1 0 0 1 -1 -1z",
        "M5 8h4",
        "M9 16h4",
        "M13.803 4.56l2.184 -.53c.562 -.135 1.133 .19 1.282 .732l3.695 13.418a1.02 1.02 0 0 1 "
        "-.634 1.219l-.133 .041l-2.184 .53c-.562 .135 -1.133 -.19 -1.282 -.732l-3.695 -13.418a1.02 "
        "1.02 0 0 1 .634 -1.219l.133 -.041z",
        "M14 9l4 -1",
        "M16 16l3.923 -.98",
    ),
    "pin": (                              # the edge panel's pin (2026-10-08)
        "M15 4.5l-4 4l-4 1.5l-1.5 1.5l7 7l1.5 -1.5l1.5 -4l4 -4",
        "M9 15l-4.5 4.5",
        "M14.5 4l5.5 5.5",
    ),
    "pinned": (
        "M9 4v6l-2 4v2h10v-2l-2 -4v-6",
        "M12 16l0 5",
        "M8 4l8 0",
    ),
    "clock": (
        "M3 12a9 9 0 1 0 18 0a9 9 0 0 0 -18 0",
        "M12 7v5l3 3",
    ),
    "picture-in-picture": (               # a section's popup (2026-10-09)
        "M11 19h-6a2 2 0 0 1 -2 -2v-10a2 2 0 0 1 2 -2h14a2 2 0 0 1 2 2v4",
        "M14 14m0 1a1 1 0 0 1 1 -1h5a1 1 0 0 1 1 1v3a1 1 0 0 1 -1 1h-5a1 1 0 0 1 -1 -1z",
    ),
    "float": (                            # a card's ⧉: a window (2026-10-18), Tabler external-link
        "M12 6h-6a2 2 0 0 0 -2 2v10a2 2 0 0 0 2 2h10a2 2 0 0 0 2 -2v-6",
        "M11 13l9 -9",
        "M15 4h5v5",
    ),
    "tool": (                             # the Tools card (2026-10-12)
        "M7 10h3v-3l-3.5 -3.5a6 6 0 0 1 8 8l6 6a2 2 0 0 1 -3 3l-6 -6a6 6 0 0 1 -8 -8l3.5 3.5",
    ),
    "rotate": (                           # Knot Orient
        "M19.95 11a8 8 0 1 0 -.5 4m.5 5v-5h-5",
    ),
    "focus-2": (                          # Knot Offset: a pivot of your own
        "M12 12m-.5 0a.5 .5 0 1 0 1 0a.5 .5 0 1 0 -1 0",
        "M12 12m-7 0a7 7 0 1 0 14 0a7 7 0 1 0 -14 0",
        "M12 3l0 2",
        "M3 12l2 0",
        "M12 19l0 2",
        "M19 12l2 0",
    ),
    "stack-2": (                          # Double knot
        "M12 4l-8 4l8 4l8 -4l-8 -4",
        "M4 12l8 4l8 -4",
        "M4 16l8 4l8 -4",
    ),
    "walk": (                             # Walk Builder (2026-10-13)
        "M13 4m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0",
        "M7 21l3 -4",
        "M16 21l-2 -4l-3 -3l1 -6",
        "M6 12l2 -3l4 -1l3 3l3 1",
    ),
    "device-floppy": (                    # its Save walk / Save pose
        "M6 4h10l4 4v10a2 2 0 0 1 -2 2h-12a2 2 0 0 1 -2 -2v-12a2 2 0 0 1 2 -2",
        "M12 14m-2 0a2 2 0 1 0 4 0a2 2 0 1 0 -4 0",
        "M14 4l0 4l-6 0l0 -4",
    ),
    "skull": (                            # Ragdoll (2026-10-16)
        "M12 4c4.418 0 8 3.358 8 7.5c0 1.901 -.755 3.637 -2 4.96l0 2.54a1 1 0 0 1 -1 1h-10"
        "a1 1 0 0 1 -1 -1v-2.54c-1.245 -1.322 -2 -3.058 -2 -4.96c0 -4.142 3.582 -7.5 8 -7.5z",
        "M10 17v3",
        "M14 17v3",
        "M9 11m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0",
        "M15 11m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0",
    ),
    "video": (                            # Camera Shake (2026-10-13)
        "M15 10l4.553 -2.276a1 1 0 0 1 1.447 .894v6.764a1 1 0 0 1 -1.447 .894l-4.553 -2.276v-4z",
        "M3 8a2 2 0 0 1 2 -2h8a2 2 0 0 1 2 2v8a2 2 0 0 1 -2 2h-8a2 2 0 0 1 -2 -2z",
    ),
    "wave-sine": (                        # Tail Builder (2026-10-12)
        "M21 12h-2c-.894 0 -1.662 -.857 -1.761 -2c-.296 -3.45 -.749 -6 -2.749 -6s-2.5 3.582 -2.5 8"
        "s-.5 8 -2.5 8s-2.452 -2.547 -2.749 -6c-.1 -1.147 -.867 -2 -1.763 -2h-2",
    ),
    "world": (                            # Tools: the world double knot (2026-10-13)
        "M3 12a9 9 0 1 0 18 0a9 9 0 0 0 -18 0",
        "M3.6 9h16.8",
        "M3.6 15h16.8",
        "M11.5 3a17 17 0 0 0 0 18",
        "M12.5 3a17 17 0 0 1 0 18",
    ),
    "code": (                             # skill bar: the Script Editor (2026-10-20)
        "M7 8l-4 4l4 4",
        "M17 8l4 4l-4 4",
        "M14 4l-4 16",
    ),
    "table": (                            # skill bar: the Component Editor (2026-10-20)
        "M3 5a2 2 0 0 1 2 -2h14a2 2 0 0 1 2 2v14a2 2 0 0 1 -2 2h-14a2 2 0 0 1 -2 -2v-14z",
        "M3 10h18",
        "M10 3v18",
    ),
    "message-circle": (                   # Chat (2026-10-20)
        "M3 20l1.3 -3.9c-2.324 -3.437 -1.426 -7.872 2.1 -10.374c3.526 -2.501 8.59 -2.296 "
        "11.845 .48c3.255 2.777 3.695 7.266 1.029 10.501c-2.666 3.235 -7.615 4.215 "
        "-11.574 2.293l-4.7 1",
    ),
    "pencil": (                           # Chat: a new chat (2026-10-20)
        "M4 20h4l10.5 -10.5a2.828 2.828 0 1 0 -4 -4l-10.5 10.5v4",
        "M13.5 6.5l4 4",
    ),
    "users": (                            # Chat: friends (2026-10-20)
        "M9 7m-4 0a4 4 0 1 0 8 0a4 4 0 1 0 -8 0",
        "M3 21v-2a4 4 0 0 1 4 -4h4a4 4 0 0 1 4 4v2",
        "M16 3.13a4 4 0 0 1 0 7.75",
        "M21 21v-2a4 4 0 0 0 -3 -3.85",
    ),
    "settings": (                         # Chat: settings (2026-10-20)
        "M10.325 4.317c.426 -1.756 2.924 -1.756 3.35 0a1.724 1.724 0 0 0 2.573 1.066c1.543 "
        "-.94 3.31 .826 2.37 2.37a1.724 1.724 0 0 0 1.065 2.572c1.756 .426 1.756 2.924 0 "
        "3.35a1.724 1.724 0 0 0 -1.066 2.573c.94 1.543 -.826 3.31 -2.37 2.37a1.724 1.724 0 0 "
        "0 -2.572 1.065c-.426 1.756 -2.924 1.756 -3.35 0a1.724 1.724 0 0 0 -2.573 "
        "-1.066c-1.543 .94 -3.31 -.826 -2.37 -2.37a1.724 1.724 0 0 0 -1.065 -2.572c-1.756 "
        "-.426 -1.756 -2.924 0 -3.35a1.724 1.724 0 0 0 1.066 -2.573c-.94 -1.543 .826 -3.31 "
        "2.37 -2.37c1 .608 2.296 .07 2.572 -1.065z",
        "M9 12a3 3 0 1 0 6 0a3 3 0 0 0 -6 0",
    ),
    "arrow-left": (                       # Chat: back to the list (2026-10-20)
        "M5 12l14 0",
        "M5 12l6 6",
        "M5 12l6 -6",
    ),
    "arrow-down": (                       # Chat: to the newest (2026-10-20)
        "M12 5l0 14",
        "M18 13l-6 6",
        "M6 13l6 6",
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
