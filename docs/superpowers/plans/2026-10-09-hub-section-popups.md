# Hub section popups - plan and status (2026-10-09)

Spec: docs/superpowers/specs/2026-10-09-hub-section-popups-design.md

## Built (the core, the header button, the popup window)

| Piece | File | Status |
|---|---|---|
| Scope rules: names, callbacks, scriptJobs, registry | SkeldarAnim/maya_hubcopy.py | done; tests/test_hubcopy.py (26) green |
| Placement rules: clamp, cascade, size, memory text | SkeldarAnim/maya_hubpop_rules.py | done; tests/test_hubpop_rules.py (24) green |
| Popup window: title row, drag, follow, close, memory, restore, destroy | SkeldarAnim/maya_hubpop.py | done; tests/test_hubpop.py (29) green |
| Card header button (picture-in-picture, before the chevron, lit while open) | SkeldarAnim/maya_hubqt.py (Card, Skin.set_popped) | done; tests/test_hubpop.py Card (4) green |
| Hub wiring: popout callback, paint_popped, adopt at build() and start() | SkeldarAnim/maya_hub.py | done |
| find() and tell() resolve names through the scope | maya_hubqt.py, maya_hubstyle.py | done |
| Popups count as the hub for a drop (over_hub) | maya_hubstyle.py | done |
| Icon (Tabler 3.19.0 picture-in-picture, fetched from unpkg) | SkeldarAnim/maya_hubicons.py | done |
| Installer: payload, destroy popups before the purge | SkeldarAnim/install.py | done; tests.test_install green |

## Live (the animator's Maya, command port, 2026-10-09)

- The repo code loaded in place of the installed copy (nothing copied to Documents).
- Colour's popup: opened by its card button; its palette press changed the copy's line and not the hub's; the card button lit.
- Drag with real Qt mouse events: clamped to the viewport on the left-bottom and the right-top; inside, under the pointer.
- Follow: the popup moved with its viewport when Maya's window was moved (rect 4,288 -> 204,374; popup 48,334 -> 248,420).
- Sweep: every card section's popup built with no error line.
- Found and fixed live: the inventory panel registry overwritten by a copy (`_PANELS` keyed by the base name). The hub's Weapons panel lost its entry; fixed in the second pass (see below).

## Second pass (2026-10-09, the lead)

The section agents died on connection errors (two rounds); the lead did the copy-safety pass itself
(spec addendum 2). Per section:

| Section | State |
|---|---|
| Weapons (Inventory) | `_PANELS` keyed by the resolved name, scene bound, object name per copy. Live: the hub's panel holds through a copy's open and close. |
| Armor | `_GRIDS` keyed, scene bound, object name per copy. Built in the sweep. |
| Animation Setup (Characters) | portrait registry keyed, scene bound, fire overlay and object name per copy; the bridge's list drag keyed by the resolved list, scene bound. Built live; the clicks and Import not run live. |
| Connections | no shared state or jobs found; built live. |
| Shared | per-card row cache, every card refreshed, one subscriber. Live: the copy lists the hub's 7 rows. |
| Stash | per-card row cache, every card refreshed, one folder timer. Built live. |
| Center of Mass | engine and tool jobs root-scoped; refresh job per card. Built live; the presses not run live. |
| Retarget | no change needed (its status line and its press are per card; built live). |
| Graph Overlay | scene jobs root-scoped; button and line repainted in every card. Built live. |
| Pose Library card | one line and the window's button; no change needed. |
| Studio | status line written to every card. Built live. |
| Colour | the press writes the copy's line (live). |
| Update | the press from a popup is deferred; the hub's rebuild runs in the hub's names. Not pressed live (it would download and install). |

Popup chrome (the animator's second round, 2026-10-09): the dock width; the title row plus the
content, nothing more; the painted outline and accent; the roll-up by its chevron or a click on the
name, remembered per section; a popup opened by its button returns to its remembered place.

## Still to do

1. The final per-module test run: done 2026-10-09 - 136 test modules, 5770 tests, every module exits 0 and ends OK (mayapy, one process per module, headless).
2. The commit: NOT made here (the rule is commit only when asked). The changed files are listed in
   the session's summary.
3. Live checks the animator can do: the Animation Setup portrait click and Import in a popup; the
   Center of Mass press in a popup; the Update press (installs - their call).

## Known limits (from the spec, and found since)

- A popup is a fresh copy on each open: typed-but-unapplied values are not kept.
- A popup has no hover glow or hover sound (the hub skin's watcher is the hub's).
- The popup's open, close, roll-up and hover light are animated (the third pass, spec addendum 3). The
  hub's own cards keep their slides and light as before.
- Closing the hub does not close the popups; their cross-section writes go to the hub's controls and
  are guarded where they may be absent.
- An install destroys the open popups and brings them back only when the hub is built again.
