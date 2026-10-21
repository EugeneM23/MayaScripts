"""maya_filedrag - rows of Stash and Shared dragged between them and into the scene.

2026-10-21, the animator: «драг энд дроп того что находится в сташе и в шаре
между этими папками и на сцену, при драге на сцену это означает что мы делаем
экспорт в сцену». Asked: a viewport is Import as the card's button; Stash ->
Shared sends with no question; every picked row travels.

- a viewport: Import (`maya_stash.drop_import` / `maya_share.drop_import`);
- Stash -> Shared: Send file, each its own name (`maya_stash.drop_to_share`);
- Shared -> Stash: a copy into the stash (`maya_share.drop_to_stash`), a file
  not downloaded yet fetched first;
- a section is its list (the hub's card or a popup copy) or its rail icon.

The drag itself is the UE Bridge list's (`maya_uebridge.listdrag`), handed a
`FileScene`. Nothing here imports Maya or Qt at import time.

Spec: docs/superpowers/specs/2026-10-21-stash-shared-drag-design.md
"""

import collections

Item = collections.namedtuple("Item", "name section key")

LISTS = {"stash": "skeldarStashList", "shared": "skeldarShareList"}
JUMP = "skeldarHubJump_"
TITLES = {"stash": "Stash", "shared": "Shared"}
ICONS = {"stash": "archive", "shared": "send"}
DOT = u"·"
DROPS = ("import", "send", "stash")
NOWHERE = "drop onto Shared, Stash or a viewport"


def section_under(names):
    """The section whose list or rail icon the chain of object `names` (the
    widget under the cursor first) belongs to, or None. A popup copy's list
    is the base name with the copy's prefix in front. Pure."""
    for name in names or []:
        name = name or ""
        for section, leaf in LISTS.items():
            if name == leaf or name.endswith("_" + leaf):
                return section
        if name.startswith(JUMP) and name[len(JUMP):] in LISTS:
            return name[len(JUMP):]
    return None


def aim_for(source, under, over_viewport):
    """What a release does: dict(kind, text, section). The other section
    under the cursor wins over a viewport behind it. Pure."""
    if under and under != source:
        if under == "shared":
            return dict(kind="send", text="send to Shared", section=under)
        return dict(kind="stash", text="copy into Stash", section=under)
    if under is None and over_viewport:
        return dict(kind="import", text="import into the scene", section=None)
    return dict(kind="none", text=NOWHERE, section=None)


def caption(items, aim):
    """(text, good) for the ghost. Pure."""
    items = list(items or [])
    if aim.get("kind") not in DROPS or not items:
        return aim.get("text") or NOWHERE, False
    what = items[0].name if len(items) == 1 else "%d files" % len(items)
    return "%s %s %s" % (what, DOT, aim["text"]), True
