# Maya's icons in the hub's style

2026-10-17, after the Maya theme. The animator: «А есть ли возможность перерисовать все иконки интерфейса маи под наш
стиль?»; shown both ways on real icons (https://claude.ai/artifact/TpsFZDd63bpcYJ6Wm7EZ5w), they chose **both**:
«recolour all icons, and redraw the most visible ~150 in our line style».

## Measured first (mayapy, Maya 2027)

- Maya's resources hold **1652** icons: 1596 PNG, 46 SVG, a few JPG. Sizes: 775 at 20 px, 566 at 32, 98 at 16, the
  rest small odd sizes. None has a `_150` / `_200` variant.
- **An icon file of the same name in `<userAppDir>/2027/prefs/icons`, the first folder of `XBMLANGPATH`, wins for
  `MQtUtil.createIcon`** (a red `move_M.png` there came back red at 32 and 48 px) **but not for
  `MQtUtil.createPixmap`**, which answers Maya's own picture. So every control Maya builds through an icon follows us;
  any that takes a raw pixmap keeps Maya's. Which ones do is for a GUI Maya to show.
- Maya's main bars name **184** icons (`statusLine.mel`, `createModelPanelBar.mel`, `graphEditorPanel.mel`,
  `toolbox.mel`, `layerEditor.mel`, `dopeSheetPanel.mel`). The redrawn set (`maya_mayaicons_art.NAMES`) is those, less
  the ones nobody animating looks at (rendering, Autodesk assistant, Flow, HumanIK dock, and so on), plus the
  Outliner's animation node types (`out_transform`, `out_joint`, constraints, lights, anim curves...).

## What it does

- ⋮ → **Maya icons**, a checkable row beside Maya theme (optionVar `skeldarMayaIcons`, off by default). Icons are
  read when Maya builds its UI: **the change shows after a restart of Maya**, and the line says so.
- **On** writes into `prefs/icons`, under a progress window Esc stops:
  - every PNG of Maya's resources **recoloured** (`maya_mayaicons.recolour`, numpy): neutral greys to the hub's
    near-white and dark lines to its charcoal by luminance; saturated accents (Maya's blues, cyans, yellows) to the
    hub's orange keeping their saturation and value; reds, greens and blues of the axis icons (`AXES`: move, rotate,
    scale, the manipulator) kept, since they mean X, Y, Z; alpha unchanged;
  - the redrawn set **drawn from our SVGs** (`maya_mayaicons_art`) at each icon's own pixel size: light lines, one
    orange part that says what the button does, the "Partial" selection-mask states on a tint, the panel layouts
    generated from their names.
- **Never the animator's files**: a file already in `prefs/icons` that we did not write is left and counted; ours are
  listed in `prefs/icons/skeldarMayaIcons.json` with each file's sha1.
- **Off** deletes only the files of that list whose content is still ours, then the list.
- **Autodesk's pictures are never shipped**: the recolour is made on each machine from its own Maya. Only our SVGs are
  in the repository.
- The 46 SVG and the JPG resources are not touched.

## Proof

- Unit tests (`tests/test_mayaicons.py`): the recolour (greys, accents, the kept axis colours, alpha), every name of
  the drawn set renders offscreen at 16, 20 and 32 px with ink and no error, the layouts' panels, the write and the
  removal on a temp folder (a file of the animator's kept, an edited file of ours kept, the rest gone), the menu row.
- `docs/superpowers/plans/render_maya_icons.py`: a contact sheet of Maya's drawn set beside ours.
- Not seen in a GUI Maya when written: which of Maya's controls take a raw pixmap and keep Maya's icon.


## Addendum, the same morning: prefs/icons does not reach Maya's buttons

The animator, after Check update and a press: the icons were Maya's. Measured in a scratch GUI Maya (own
`MAYA_APP_DIR`, killed after):

- **A file in prefs/icons never reaches Maya's own buttons**, after a restart too: the toolbox, the status line and a
  freshly made `iconTextButton -image1 "move_M.png"` all drew Maya's resource. `MQtUtil.createIcon` answered ours,
  which is what the mayapy proof measured - the wrong question.
- Maya keeps every icon at three sizes in Qt's resources (`:/move_M.png`, `:/move_M_150.png`, `:/move_M_200.png`;
  `resourceManager` lists only the first) and takes the large one at a 150 / 200 % display. A resource of ours
  registered with `QResource.registerResource` does not override Maya's.
- **A button pointed at our file by its full path draws ours at once.** So: every size (7282 PNG at the root of `:/`)
  is drawn or recoloured into `<userAppDir>/<version>/SkeldarIcons` (ours alone, never prefs/icons), every icon button
  of the KINDS (`iconTextButton`, `iconTextCheckBox`, `iconTextRadioButton`, `symbolButton`, `symbolCheckBox`,
  `shelfButton`, `toolButton`) is pointed there (`repoint`, `pointed` pure), a Qt timer does it again every 2 s for
  panels built later (~0.02 s a sweep), and the hub's build calls `ensure()` at Maya's start. Off points every button
  back at its bare name and empties the folder. No restart either way. The files the first build wrote into
  prefs/icons are removed by its manifest on the next press.
- **By full path (`lsUI -long`)**: Maya names every viewport's bar buttons alike (`ShadedBtn` four times); by short
  name only the first viewport changed.
- Measured: On 10.9 s (7270 files), 347 buttons at once, the Graph Editor opened afterwards on ours through the watch,
  every viewport's bar on ours; Off 425 buttons back, none left, the folder empty. Not changed: the Outliner's node
  icons and anything else Maya draws in C++ without a cmds image.
