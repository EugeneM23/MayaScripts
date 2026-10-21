# Stash and Shared: rows dragged between them and into the scene

2026-10-21. The animator: «Необходимо реализовать механизм драг энд дропа того
что находится в сташе и в шаре между этими папками и на сцену, при драге на
сцену это означает что мы делаем экспорт в сцену». Asked, all the
recommendation:

- a drop on a viewport is **Import, as the card's button** (not a retarget, not
  an Open);
- Stash → Shared **sends with no question**, as Send file does;
- **every picked row** travels, as in the UE Bridge list.

## What a drop does

| From → onto | Does |
|---|---|
| Stash → a viewport | `maya_stash` Import for each file: a scene imported with its script nodes deleted, an FBX as its own skeleton in a namespace |
| Shared → a viewport | `maya_share.import_entry` for each row |
| Stash → Shared | `maya_share.send_file(path, name)` for each file, its own name |
| Shared → Stash | `maya_stash.stash_file(local, name)` for each row: a copy under the record's name, a taken name getting ` (2)` |
| anywhere else (its own list, the rest of the hub, off every viewport) | nothing |

Esc or the right button cancel. Several files are handled one by one in list
order; the card's status line names each result («Imported A.fbx ... | Imported
B.ma ...»). A Shared row whose file is not on this disk yet (still downloading,
or a download failed) is **fetched first** and the action runs when it lands
(`maya_share.when_local(rid, fn)`); a row that is sending, never sent, deleted
or expired is refused by name, as Import refuses it today. A Stash file gone
from the folder is skipped by name.

A scene imported runs in the active scene tab, as the buttons do.

## Where a drop lands "in a section"

On the rail one card shows at a time, so three places count as Stash's (and the
same three as Shared's):

1. its list in the hub's card;
2. its list in a floating window (a popup copy: the list's objectName ends with
   `skeldarStashList` / `skeldarShareList`, `maya_hubcopy` prefixing it);
3. its **rail icon** `skeldarHubJump_stash` / `skeldarHubJump_shared`.

Found by walking up from `QApplication.widgetAt(point)` and reading object
names (pure: `filedrag.section_under(names)`), never by keeping a widget
(trap 135). The rail icon under a drag is lit as a hovered icon is
(`Skin.light_jump(key)`, cleared on the drop or cancel). Over its own section
the ghost reads «drop onto Shared, Stash or a viewport», muted.

## The ghost

The hub's shared ghost (`maya_hubqt.ghost_class`), its icon the source
section's (`archive` for Stash, `send` for Shared), its caption:

- «Attack.fbx · import into the scene» / «3 files · import into the scene»;
- «Attack.fbx · send to Shared» / «3 files · send to Shared»;
- «Attack.fbx · copy into Stash» / «3 files · copy into Stash»;
- muted elsewhere.

## How it is built

`maya_uebridge/listdrag.py` already does the hard part: an event filter on a
textScrollList's QListWidget, the press passed through, the carried rows
(`carried_rows`), Qt's implicit grab, the ghost, Esc. Its `Drag` takes a
`Scene`. Three seams, each defaulting to what the bridge does now, so the UE
Bridge is unchanged:

- `scene.caption(records, aim)` when the scene has one, else the module's
  `caption`;
- `scene.drops` (the aim kinds a release acts on), else `DROPS`;
- `scene.icon` (a Tabler name), else `"run"`.

A drop over the hub already asks `scene.over_hub(gx, gy)` first; the new scene
answers False over the other section's list or rail icon, so `target` decides
there.

New module `SkeldarAnim/maya_filedrag.py` (cmds lazily, Qt through listdrag):

- `Item(name, section, key)` - a carried row: the Stash file name or the Share
  record id, `name` for the caption;
- `section_under(names)` (pure): "stash", "shared" or None for a chain of object
  names, list or rail icon;
- `aim_for(source, under, over_viewport)` (pure): kind `import` / `send` /
  `stash` / `none` and its text;
- `caption(items, aim)` (pure);
- `FileScene(source)` - the listdrag scene: `target`, `over_hub`, `drop`
  (deferred one idle, through the card's `_run`), `say`, `caption`, `drops`,
  `icon`;
- `attach(source)` - called by each card's build after its list is made (and in
  every popup copy, scoped).

Over a viewport is `droptarget.Viewport.at(gx, gy)` answering a model panel.

`maya_share` gains `when_local(rid, fn)` (run now, or fetch and run on
`_fetched`; a failed fetch says so and drops the waiting action) and a drop
entry `drop_import(rids)`, `drop_to_stash(rids)`; `maya_stash` gains
`drop_import(names)`, `drop_to_share(names)`. Each loops, collects the lines
and writes one status.

## Tests

- `tests/test_filedrag.py`: `section_under`, `aim_for`, `caption` (pure); the
  scene's drop calling the right module functions (fakes); the drag on an
  offscreen QListWidget: rows carried, a drop over a stand-in list widget named
  like the other section's, over a rail icon, on its own list (nothing).
- `tests/test_uebridge_listdrag.py` stays green (the seams default).
- `maya_share.when_local`: run at once when local; run after `_fetched`; not run
  after `_fetch_failed`.
- `docs/superpowers/plans/verify_stash_share_drag.py` (mayapy standalone, a
  scratch `MAYA_APP_DIR`, a test topic): a stash scene and FBX imported through
  `drop_import`, a stash file sent through `drop_to_share` and seen by a second
  session, a shared file copied into the stash through `drop_to_stash`.

The real mouse in a GUI Maya is the animator's to try.

## Not built

Dropping a file from Explorer into either list; a drop onto a character
(retarget); Open by drag.
