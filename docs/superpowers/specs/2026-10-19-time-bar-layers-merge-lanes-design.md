# Time Bar layers: Merge selected, and the lanes as a dope sheet (2026-10-19)

The animator: «Сейчас можно только делать мерж даун. А нужно чтобы я мог выбирать разные слои в
разной последовательности и делать мердж селектед. Так же выдвижная панель с ключами сейчас
непонятно как работает, по сути она должна повторять функционал таймлайна.» Asked: «Делай все как в
стандартной мае. Множество слоев выделяем через ctrl», and the lanes «как dope sheet по слоям».

## Several layers selected, Merge selected

- In the column's Animation tab a click on a row selects that layer alone (as before). **Ctrl-click
  adds or takes a layer out of the selection, Shift-click selects the range** from the last clicked
  row - Maya's Anim Layer Editor. BaseAnimation can be selected too.
- The selection IS Maya's: `animLayer -e -selected` on every layer, `-preferred` on the active one
  (the one clicked last, where keys go), and the editor's own `$gSelectedAnimLayers`, so Maya's Layer
  Editor shows the same rows. A row reads `selected`; the active row keeps the accent outline, the
  other selected rows the active face with a hairline.
- **Merge selected** - the foot's merge button with two layers or more selected, and «Merge selected»
  in a row's menu - is Maya's own Merge Layers: `$gSelectedAnimLayers` set to the selected layers, then
  `performAnimLayerMerge 0`, so the animator's own Merge Layers options (Animation > Merge Layers ❒)
  apply, the order is the stack's, and BaseAnimation in the selection merges into the base. The result
  keeps Maya's name. One undo chunk. With one layer selected the button is Merge down, as before.

## The lanes: a dope sheet of the layers

Each lane is the timeline for that layer's keys of the selected objects. Everything acts on those
layers' curves only.

- **Left press**: the time goes there, a drag scrubs (Maya's scrub mode); the lane's layer becomes the
  active one. The highlight goes away.
- **Middle drag**: scrubs without updating the scene.
- **Shift-drag**: highlights a frame range on the lanes it sweeps (down or up across lanes takes
  several layers). One frame highlighted with a shift-click.
- **Drag inside the highlight** moves its keys on those layers, **an edge** scales them toward the
  other edge (the timeline's rule: whole frames, a key between frames keeps its place in its cell). A
  preview while dragging, applied on the release in one undo chunk.
- **Double click** (left or right) highlights every key of that lane.
- **Right button**: the key menu on the highlighted lanes (else the lane under the mouse at the current
  frame): Set key, Breakdown, Cut, Copy, Paste, Delete, Tangents ▸, Snap, Highlight all keys, Clear
  highlight. A right double click waits like the timeline's.
- Set key keys the selected objects' channels that are in that layer at the current frame
  (`setKeyframe -animLayer`); on BaseAnimation, their keyable channels.

## Where

`layerscene.py` (Maya), `layerlook.py` (pure: the lane under a y, the lanes between two), `layerpanel.py`
(Qt). Tests: `test_timebar_layerscene.py`, `test_timebar_layerlook.py`, `test_timebar_layerpanel.py`;
the headless verify `verify_timebar_layers.py` gains Merge selected and the lane ops.
