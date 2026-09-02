# A temporary hotkey map on the SkeldarAnim shelf

2026-09-02. The animator's ask: «а мы можем для нашей полки добавить кнопочку
где-то которая на время активации включала бы временную карту горячих
клавишь?»

A sixth shelf button that switches Maya to a hotkey set of its own for as long
as it is on, and switches back when it is pressed again. The map's contents are
the animator's to lay out — in Maya's own Hotkey Editor, which is already the
editor for exactly this — and what we add is the switch plus a command list
worth binding: every one of our panel buttons, and every one-press procedure
OverRig's author published for hotkeys.

## What was decided, and what was declined

Four questions settled the shape:

- **The map is mixed and the animator's own.** Not a curated set of ours, not a
  literal transcription of OverRig's list: a hotkey set they fill themselves,
  with our commands and OverRig's both available to bind.
- **The editor is Maya's Hotkey Editor.** A file-plus-JSON map and a small
  panel of our own were both on the table and both declined. So we build no
  editor, no cheat sheet, and no map format. The map lives in Maya's prefs,
  which means it does not travel in the zip — accepted, with a door left open
  below.
- **The set starts as a copy of whatever is active** when it is first created,
  so Ctrl+Z, Q/W/E/R and the animator's own keys keep working and only what
  they assign is different. An empty set and a copy of `Maya_Default` were the
  alternatives.
- **It stays on across a Maya restart.** Maya saves the active hotkey set
  itself; we add nothing at exit. A `quitApplication` scriptJob that put the
  old set back was offered and declined, which is the cheaper answer in every
  way: nothing to build, nothing to verify against Maya's save order.

## Shape: one shipped file, one shelf button

`SkeldarAnim/maya_hotkeys.py` — the same convention as `maya_overshoot.py`: a
shipped single file, `maya.cmds` only, no package. Qt is imported **lazily
inside the commands that need it**, so the module still loads where PySide6
does not exist (the installer's own rule: four of the five shelf buttons run on
any Maya, and only the picker needs 2025+).

Two alternatives were rejected. Putting the logic in the button's command
string inside `install.py` costs no new file and makes a hundred-row table
untestable and unreadable, with a re-drag needed for every edit. A package
`maya_hotkeys/` follows the convention of the three big tools and is overkill
for one table and three functions.

The button is labelled `Hotkeys` and sits last among the Python buttons, ahead
of OverRig. It goes into `install._PYTHON_BUTTONS` unchanged in shape —
`("Hotkeys", note, "maya_hotkeys", "toggle", "hotkeys.png")` — because a toggle
has the same call shape as an opener, and into `install.payload()` so it ships.

## The button and its state

One press toggles. On: the `SkeldarAnim` set becomes current, the button gets a
highlighted background, and an in-view message says which map is live. Off: the
remembered previous set comes back and the highlight goes.

**State is read from Maya, never cached.** "Is it on" is
`hotkeySet(query=True, current=True) == "SkeldarAnim"`, evaluated at every
press, and the highlight is derived from that answer rather than from a stored
boolean. The animator can switch sets by hand in the Hotkey Editor between two
presses, and a cached flag would then lie — the same lesson as
`picker_window._resolution` re-asserting its binding on every sync.

The button finds itself by walking the shelf's `childArray` and matching the
label, because a shelf button's command runs with no widget context. Not found
(the module called from the Script Editor, or the shelf renamed) is not an
error: the set still switches and only the paint is skipped.

**The first press in the map's life opens the Hotkey Editor.** A set that is a
copy of the current one behaves exactly like the current one until keys are
assigned in it, so without this the first press looks like a button that does
nothing. Only on creation; afterwards the toggle is silent.

## The hotkey set

Created once, as `hotkeySet("SkeldarAnim", source=<current>, current=True)`, and
never rebuilt. Rebuilding on each activation — tempting, since it would keep the
copy in step with the base set — would destroy every key the animator assigned
in it, which is the whole content of the feature.

The previous set is remembered in the optionVar
`skeldarAnimPreviousHotkeySet`, written at the moment of activation. An
optionVar rather than a module variable for one reason: the map is sticky, so
the session that turns it off is often not the session that turned it on.

Four cases, each with a definite answer:

- **Activating while already in our set** must not overwrite the memory, or the
  way out would lead back in and the animator would be stuck in a map with no
  exit but the Hotkey Editor.
- **The remembered set is gone** (deleted in the editor): fall back to
  `Maya_Default`, which always exists and cannot be deleted.
- **No memory at all** (the optionVar was never written, or prefs were reset):
  the same fallback.
- **Our set deleted while active**: the next press creates it again as a copy of
  whatever is current. Nothing to repair.

## The commands

Every runTimeCommand's body is a one-liner into our module:

```python
import sys
_p = "<install dir>"
if _p not in sys.path:
    sys.path.insert(0, _p)
import maya_hotkeys
maya_hotkeys.run("picker.build")
```

The bootstrap is the shelf buttons' own, and it is required: a key pressed
before any shelf button in a fresh Maya has nothing of ours on `sys.path`. The
path is baked at registration time from `maya_hotkeys.__file__`'s own folder —
the installed copy knows where it lives, the way `catalog._sword_path()` reads
the shipped sword two dirnames up from itself.

Everything else is a **key into a table in the module**, which buys three
things: the policy for "the panel is not open" lives in one tested place; a
stale body in the animator's prefs still resolves through the current table;
and an unknown key reports itself instead of raising. Keys are
`<area>.<action>` — `picker.build`, `scene.camera`, `overrig.parent_in` — and
the area is what the category is derived from, so the two cannot drift apart.

`runTimeCommand` names are technical (`skeldarAnimPickerBuild`); the Hotkey
Editor shows `-label` and `-annotation`, and every row's label carries the
word the animator would search for, so "bake" finds the bake rows. `-keywords`
exists and is deliberately left unset: a second place to spell the same words
is a second place for them to drift.

**`toggle()` registers first, in both directions**, with `edit=True` for the
rows that already exist. That is the only moment registration happens, and
making it unconditional — a press that turns the map *off* refreshes the
commands too — is what keeps an updated plugin's commands, and the baked
`sys.path` inside them, in step with what is on disk. The installer does not
register: it would have to import the freshly copied module during its own run,
and the next press does it anyway.

The exact table — every row's key, name, label, category and body — belongs to
the implementation plan, not here. What this spec fixes is its shape and the
rules that decide what may be in it.

Categories nest with a **dot** (measured: Maya ships
`Editors.Time Editor.Clip`), so the tree in the editor is ours to shape.

### Ours: a command is a button press

Every action of ours is a panel button, and every panel already reports what it
did on its own status line, refreshes itself, and traps its own exceptions
(`picker_window._run`, `window._run`, `maya_overshoot._run`). So a command
presses the button: `picker_window._open_window()` hands back the live picker
and `window.build_rig()` is the Build button; Scene Setup's and Overshoot's
module-level callbacks read their own windows' controls and are already exactly
this.

Which means **with the panel closed there is nothing to press**, and the
command says so: it opens the panel and reports that in view. It does not
reconstruct the panel's state — the picker's binding is the character the
animator can see, and acting on a re-derived guess is how two Mannys got
rigged onto each other.

- `SkeldarAnim.Windows` (5): Rig Picker, UE Bridge, Scene Setup, Overshoot, and
  the map toggle itself — so the map can be left from inside the map.
- `SkeldarAnim.Rig Picker` (6): Connect, Build, FK Limbs, IK Limbs,
  Bake+Delete, All.
- `SkeldarAnim.Scene Setup` (7): Add Character, Add Weapon, Remove Weapon,
  Connect Arms, Disconnect Arms, Add Aim, Camera Setup.
- `SkeldarAnim.Overshoot` (5): Snap, Spring, Elastic, Recoil, Bounce — the five
  presets of `SHAPES`, each `apply_overshoot(shape)`.

### OverRig: the author's list, grouped as the author grouped it

`function_for_hotkeys.TXT` is Pavel Barnev's own list of procedures meant for
hotkeys, and its headings become the category tree: `OverRig.Knot`,
`.Parent`, `.Key tools`, `.Aim`, `.Selector`, `.Bake`, `.Hierarchy`, `.IK`,
`.Smart object`, `.Double knots`, `.Snapshot`, `.Sword`, `.Physics`, `.Misc`,
`.Finger`. About eighty rows: every procedure in the file that runs on one
press, with the author's own arguments as written there (`Lag_Key(1.2)`,
`apply_Smart_Bake(0)` and `(1)`, `time_slider_range(24)`,
`double_inv_oscillate_or_mirror(2, "x", "x")`). Where one procedure takes a
named mode, each mode is its own row — four for `set_infinity_graphEditor`,
four for `set_key_time_range`, five for `brn_apply_finger_bend_tool` — because
on a keyboard each of those IS a separate key. `bar_tween_machine` goes in as
the file documents it, 0% and 100%.

Two rules, both load-bearing:

- **Each row sources OverRig first**: `overrig.ensure_loaded()`, then
  `mel.eval`. In a fresh Maya with the OverRig shelf button unpressed, MEL
  raises `Cannot find procedure` — and out of a keypress that lands in the
  Script Editor where nobody is looking. That is trap 20 from the hotkey side,
  and `overrig.NOT_LOADED_MESSAGE` is the report when the toolset cannot be
  found at all.
- **No time-slider guard.** Our own MEL entry points refuse under a multi-frame
  highlight (trap 36), and here that would be wrong: `apply_range_Fast_Bake`,
  `selKeys_by_timerange`, `double_oscillate_keys` and
  `apply_range_Bake_to_Over_layer` are *about* the highlighted range. Guarding
  them would break what they are for.

### Excluded, and why

- `barn_fast_bake_source_obj_and_delete_knots()` and
  `barn_fast_bake_min_max_or_range_source_obj_and_delete_knots()` — the only
  procedures in the file that ignore the selection and work on the whole scene:
  they select all of `OverRig_rig_objects`, bake, and delete every knot. On a
  hotkey that is one mis-press from taking down hand-made setups the tool never
  built. Two rows away if the animator asks; excluded by default, and named in
  a gone-test so nobody restores them quietly.
- The ones needing real arguments with no defensible default —
  `execute_overlap_command(...)`, `bar_create_multiply_fast_motion_trail(...)`,
  `apply_bake_to_ribbon_system(...)`. Their windows are registered instead
  (`bar_tail_overlap_window`, `dyn_tail_tool_window`, `overRig_noise_window`,
  `overRig_tween_window`): for these, the window *is* the one-press command.
- `setKey_on_attach_attr(value)` is registered twice, with 1 and 0. The file
  documents no value; the attach attribute is a 0..1 weight and on/off is the
  obvious pair. Recorded here as ours, not the author's.

### Reporting and undo

Our module reports **only its own outcomes** in view — panel opened, panel not
open, OverRig missing, unknown key, and any exception (message in view, full
traceback to the Script Editor, exactly the panels' `_run`). It never narrates
a successful OverRig procedure: those have a voice of their own.

No undo chunk of our own. `rebuild` already builds in one undo step and
OverRig's procedures manage their own; wrapping something that chunks in
another chunk buys nothing and nests. A hotkey inherits whatever its target
does, which is what the shelf buttons already do.

## Measured facts about the Maya side

Probed in `mayapy` 2027 before the design was written:

- **`hotkeySet` requires a UI.** `hotkeySet(query=True, current=True)` and
  `(query=True, hotkeySetArray=True)` both raise `RuntimeError: Maya command
  error` in `mayapy`. So the set half cannot be unit-tested at all: tests use a
  fake `cmds`, and the live bridge is the only proof. Its real flags are
  `-current`, `-source`, `-exists`, `-delete`, `-rename`, `-hotkeySetArray`,
  `-import`, `-export`.
- **`runTimeCommand` works headless**, create and `edit=True` and
  `edit=True, delete=True` alike, and it carries `-category`, `-label`,
  `-annotation`, `-longAnnotation`, `-keywords`, `-commandLanguage`, `-image`.
- **`default` comes back `False`** for a command we create, which means Maya
  writes it to `userRunTimeCommands.mel`. That is what makes the sticky map work
  after a restart: the keys still fire before the button has been pressed in the
  new session. It also means our commands outlive an uninstall as rows that
  report an ImportError — accepted, and the reason every body is a one-liner
  through the table rather than real logic baked into prefs.
- **Categories nest with a dot**: 272 exist in a stock 2027, shaped like
  `Editors.Hypershade.Edit.Duplicate`.
- Binding a key needs a `nameCommand`, not a runTimeCommand, and **the Hotkey
  Editor creates that itself** when a command is dragged onto a key — Maya's
  own mechanism, which is why we register no nameCommands and pre-bind no keys:
  the set arrives as a copy of the animator's own and every key in it is
  theirs. The verify script has to create one explicitly for its test key,
  since `hotkey -name` takes a nameCommand and there is no editor in the loop.
- Two more, measured in the live run rather than up front. **`cmds.hotkey`
  reverses its own flag between writing and reading**: `hotkey(keyShortcut=
  "F12", name=<nameCommand>)` sets a binding, but reading one is
  `hotkey("F12", query=True, name=True)` — with `keyShortcut=` under `query`
  Maya raises `TypeError: Flag 'keyShortcut' must be passed a boolean
  argument`. And **`cmds.nameCommand` has no query flag at all**, so a
  binding cannot be followed from the key through to the body; the proof
  splits in two — the key resolves to our nameCommand, and a runTimeCommand
  run by its own name reaches `run()`.

## Testing

`tests/test_hotkeys.py`, with a fake `cmds` injected into `sys.modules` **and
the module attribute rebound** (`maya_hotkeys.cmds = fake`) — deleting the
module from `sys.modules` to force a re-import does not work here and has cost
a debugging round before.

- The table is data: names unique and legal for `runTimeCommand`, categories
  all under `SkeldarAnim.` or `OverRig.`, labels and annotations non-empty,
  every key referenced by a body present in the table.
- A gone-test naming both `barn_fast_bake_*_and_delete_knots` procedures.
- `toggle()` against the fake: creates once with `source=<current>`, remembers
  the previous, comes back to it, refuses to overwrite the memory when already
  ours, falls back to `Maya_Default` for a vanished or missing memory, and
  reads its state from `current` every time.
- `register()` is idempotent: a second pass edits and creates nothing.
- Our commands do not lie about method names. The bodies name
  `window.build_rig()` and friends, so the test scans the target module's
  **source** for `def build_rig(` rather than importing it — an import would
  drag Qt into a plain-Python test.
- `tests/test_install.py` and `tests/test_make_build.py` pin the payload and the
  button count today; both must grow to six buttons and the new file, and their
  failure is the signal that the installer half is done.

`icons/make_icons.py` gains `hotkeys.png`, generated and committed beside its
generator like the other four.

## Live verification

**Green live 2026-09-02: 0 of 14 gates failed** (14 rather than the 13 below
— a last gate was added once the rest passed: the shelf button's own baked
command, executed the way the animator's press executes it, toggling
`SkeldarAnim_verify_base → SkeldarAnim → SkeldarAnim_verify_base`).
The first run failed two gates, both of them the script's own bug about
`cmds.hotkey`'s query form, recorded above; the feature itself never failed
a gate. The first run also caught trap 20 honestly: OverRig was not loaded
in that session and an OverRig row sourced it.

`docs/superpowers/plans/verify_hotkeys.py`, sent through the command port. It
touches **prefs, not the scene**, which changes the hygiene rules: record the
current set name and the whole `hotkeySetArray` first, restore in a `finally`
step by step (trap 42 — one raising teardown step abandons the rest), and delete
our set only if this run created it. An animator who already has a `SkeldarAnim`
set with their own keys in it must find it untouched afterwards; those gates
skip themselves and say why, the way phase 2 of `verify_two_characters.py` steps
aside when it finds manifests that are not its own.

Gates: the fresh set really inherited a sample key from its source; it became
current; the toggle back landed on exactly the recorded name; a hand-switch to a
third set between presses still returns the remembered one; every registered
command exists with the right category and label; the shelf button's background
flips both ways; and a bound key really runs the command — a keypress cannot be
sent over the port, so the test binds a spare key, reads back
`hotkey(query=True, name=...)` and runs that nameCommand's body directly.

The gate that OverRig sources itself on the first press is only honest in a
**fresh Maya**, since it is about a session where the OverRig button was never
pressed; the script says so where it runs, the way `verify_missing_bones.py`
asks for a fresh session.

## Addendum, the same day: four keys bound for you

The animator, once the map was in their hands: «alt+a — кадр назад, alt+s —
кадр вперед. alt+4 — добавить inbetween кадр между alt+5 убрать». So the
"no pre-bound keys" decision below is **superseded** — the map arrives with
four keys in it. Everything else about it stands: the rest is theirs to lay
out in the editor.

**Four new rows, a new category `SkeldarAnim.Timeline`.** Frame back and
frame forward are `currentTime ± 1`. Insert and remove are the module's own
work rather than a panel press, and they are **exact inverses**, which is
what fixes their semantics: insert moves everything strictly after the
current frame one frame later, so the frame after the pose comes free;
remove clears that frame, keys and all, and pulls the rest back. Press one
then the other and the timeline is where it started. Both halves are pure
functions (`insert_plan`, `remove_plan`) and tested as such.

**Two calls that were mine to make**, since the animator asked me to do it
myself, and both are stated so they are easy to reverse:

- **Scope**: the selection's curves, or every curve in the scene when
  nothing is selected. "Insert a frame" means the shot when nothing is
  picked and that limb when something is, which is also how OverRig's own
  procedures behave.
- **What remove takes**: the frame after the current one, *with whatever is
  on it*. The alternative — refusing when that frame carries keys — is
  safer in the abstract and useless in practice: after a Build every bone
  carries a dense baked curve, so it would refuse every time. One press is
  one undo step, and the status line says how many keys went.

**The keys are bound inside our set only.** `bind_defaults()` runs after
the switch to `SkeldarAnim`, never before it. All four were already taken
by a Maya default — measured: alt+a `CycleDisplayMode`, alt+s
`HIKSetFullBodyKey`, alt+4 `ImagePlaneOption`, alt+5
`WireframeOnShaded` — and overwriting them was the animator's explicit call
(«если возникают конфликты то перезапиши»). The press names what it
displaced rather than taking a key quietly, and in their own set those four
keep working.

**Binding is once, not every press.** A fresh set always gets them; a set
that already exists gets them once per `DEFAULT_KEYS_VERSION`, recorded in
the optionVar `skeldarAnimDefaultKeys`. The version exists because "only on
creation" would never have reached the animator's own set, which existed
before these keys did — and because a fifth default key later is then one
bump rather than a special case. After the install their edits stand: the
keys are a starting point, not a policy.

**`cmds.ls(type="animCurve")` answers driven-key curves as well**, whose x
axis is a driver's value and not time. `time_curves()` filters to the four
time-based types; the animator's open scene held `animCurveUU` when this
was written, so it is a live hazard rather than a hypothetical one.
`remove_frame` takes the module's only undo chunk, because clearing a frame
and pulling the rest back are two commands that must undo together.

## Not built

- No editor, no map file, no cheat-sheet panel — all three declined above.
- ~~No pre-bound keys~~ — superseded by the addendum above; four keys are
  bound, and the `nameCommand` wrappers they need are ours.
- Nothing at Maya exit: the map is sticky by choice.
- **A door left open**: `hotkeySet` has `-export`/`-import` for `.mhk` files, so
  handing the finished map to a colleague — the one thing living in prefs costs
  us — is one flag each whenever it is asked for. Not now.
