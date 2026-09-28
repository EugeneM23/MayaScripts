# One file that installs SkeldarAnim from GitHub (2026-09-28)

The animator: «Сделай скрипт который можно кинуть в открытую сцену и он установит наш плагин с
гит хаба».

## Shape

`SkeldarAnim_Install.py` at the repository root — beside the plugin, not in it (it is what a
colleague has BEFORE the plugin; the payload never carries it). Dropped into a Maya viewport:

1. `SkeldarAnim.zip` from `github.com/EugeneM23/MayaScripts/releases/latest/download/`, in
   chunks under a cancellable `progressWindow`;
2. checked (`testzip`, `SkeldarAnim/install.py` present, no path leaving the folder) and
   unpacked into a temp folder;
3. **that build's own `install.py`** loaded by path as `skeldar_setup_installer` and run — the
   same installer a hand drag runs, so the payload, `version.json`, the shelf and the module
   purge are its business, and its own dialog reports the install;
4. the temp folder removed, the SkeldarAnim window opened from the copy just installed.

Every refusal before step 3 (nothing published, no network, not a zip, a damaged archive)
says «nothing was installed» in a dialog; an installer failure keeps the unpacked build and
names it. The open scene is never touched. A second drop is an update to the latest build.

**Stdlib at import**, `maya.cmds` inside the functions: Maya's drop handler
(`maya.app.general.executeDroppedPythonFile`) inserts the file's folder into `sys.path`,
`importlib.import_module`s it by its stem — so `__name__` is never `"__main__"` there and
the `__main__` block only serves an `exec` from the Script Editor — and calls
`onMayaDroppedPythonFile(obj)`. `run(quiet=True)` skips every dialog, the installer's too, for
a scripted run over the command port.

It duplicates the download and unpack of `maya_update` on purpose: it runs where no module of
ours exists yet.

## Where a colleague gets it

Every release carries it as a third asset, so the link is stable:
`https://github.com/EugeneM23/MayaScripts/releases/latest/download/SkeldarAnim_Install.py`.
The workflow builds on pushes touching it too; such a push changes no payload commit, so the
build is skipped and the file is re-uploaded onto the latest release (`--clobber`).
