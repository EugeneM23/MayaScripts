"""The Pose Library window (2026-10-02): folders, cards, details, Save, drags and the blend.

The animator: «отдельное окно ... каталоги ... поиск и сортировка ... при нажатии правой
клавишей мышки по карточке мы можем выделить объекты ... перетягивать наши карточки на персонажа
драгом мышки ... Если мы перетягиваем карточку в пустую сцену ... загрузит исходный риг или
скелет и выставит позу». So a `workspaceControl` `skeldarPoseLibrary` (floating, dockable, its
uiScript carrying the plugin path - the hub's way) holds one Qt root in the hub's stylesheet:

    header     «Pose Library», the library path (muted), ⋮ (Library folder..., Open in
               Explorer, Refresh)
    toolbar    search (every term in name, folder or character, or a type word), the type
               filter, sort (Name / Newest / Character), the card size, + Save (the window's
               one primary)
    splitter   the FOLDER TREE (its own rows: New folder, Rename, Delete, Show in Explorer; a
               card dropped on a folder moves there) | the CARD GRID (`cardgrid`: one painted
               canvas, `look.grid` lays it out, only the cards the viewport shows are painted,
               each thumbnail scaled once per size and cached) | the DETAILS (the big thumbnail,
               `look.details`, the target line, Apply, Mirror, Blend, Select objects) - or,
               while saving, the SAVE PANEL in their place (the name, the folder, the
               character, the region chips pre-lit from the selection, the thumbnail and
               Snapshot, Save / Cancel)
    status     one word-wrapped line: what the last press did

What a card does under the mouse, each a measured Qt habit of the plugin's other grids
(`maya_armorgrid`, `maya_chargrid`, `maya_inventory`):

  - a click picks it, a double-click applies it to the selection, the right button offers
    `context_actions` (`maya_hubqt.run_menu`);
  - a LEFT drag past `QApplication.startDragDistance()` carries the hub's ghost (the
    thumbnail and a caption pill read through `look.drop_caption`, re-read at most every
    `look.THROTTLE_MS`); released over a character in a viewport the pose goes onto it
    (`apply_onto`), over an empty floor its source character is added there and posed - one
    idle later (`defer`), since Add takes seconds and must not run inside a mouse event - over
    a folder of the tree the card moves there, over the window or the hub nothing; Esc or the
    right button cancel;
  - a MIDDLE drag across it blends (Studio Library's gesture): `alpha = dx / (200 px x the
    display scale)`, clamped to 0..1, previewed live, keyed on release; Esc puts every value
    back. The Blend slider does the same under a LEFT drag only (`BlendSlider`): a drag
    previews, the release keys. A press on the groove puts the handle there and starts that
    same drag, with no page step and no auto-repeat. The wheel and the keys never move it: the
    wheel scrolls the side panel. The slider then reads 0 again, because the pose it keyed IS
    the new "current" a next blend starts from.

Every scene call goes through `Scene` (the tests replace it): Save and the thumbnail
(`capture`), Apply and the blend (`apply`, imported lazily - this module imports neither Maya
nor Qt at import time), the drop targets (`maya_scenesetup.droptarget`). The library's own
files (rename, move, remove, folders) are `store`'s, plain disk work. A press never raises
into Qt: it lands on the status line, the traceback in the Script Editor (trap 20).

The selection is followed: a `SelectionChanged` scriptJob (with Undo / Redo / a new scene),
coalesced through a 120 ms timer, keeps the target line and Apply's enabled state true; the jobs
die with the window (`destroyed`, capturing the job ids and never the widget - the inventory's
`watch` / `unwatch`). The read happens once per selection change, while a card is picked (or
the save panel is open) and the window shows - a card click reuses it (`show_targets`), a hidden
docked tab reads when it shows again: with a rig's 187 controls selected it cost 0.8 s, 3 s with
the save panel open, on every change and every click (the final review); `scene.resolve` now
answers a rig's nodes without walking their ancestors (0.05 s for those 187).

**Animation cards** (2026-10-03, the animator: «теперь давай добавим возможность сохранять
анимации. Все правила которые работают для поз должны работать и для анимаций. Так же мы должны
уметь выбирать способ вставки анимации как в studio library»):

  - the toolbar's TYPE FILTER (All / Poses / Animations, remembered) beside the search, and
    + Save (was + Save pose) opening the save panel with `[Pose | Animation]` segments
    (remembered); Animation adds Start / End - the time slider's highlight, else the playback
    range (`Scene.anim_range`), read when Animation is first lit in a panel - and a line saying
    how many frames and preview cells it takes (`save_frames_text`);
  - the details of a picked animation card LOOP ITS PREVIEW in the big picture (a `PLAY_MS`
    timer running only while the window shows one; `canvas.preview_frame`) and show the PASTE
    OPTIONS block - under Apply, Mirror, Blend and Select objects, two options to a row, so
    Apply stays in view at the default size (the final review, M5): Paste (Replace / Replace
    all / Insert / Merge), At current time + Connect, Range (the
    card's own frames, put back when another card is picked - a press on the picked card, to
    drag it, keeps it), Keys (Every frame / Source keys) + In place. Each but the range
    is remembered (an optionVar never written is its `animdata.Options` default - never the 0
    Maya answers for a missing one). Every press of an animation card - Apply, the drops, the
    blend, Select objects - hands the scene `options` (`options(path)`: the range only for the
    picked card, the whole clip for another); a pose card's presses are the pose's, unchanged;
  - an animation card's right-button rows are a pose card's with «Replace thumbnail and
    preview» (`Scene.replace_preview`) in place of «Replace thumbnail».

`Scene` dispatches on the card's suffix (`store.is_anim`): an animation goes to `animapply`
with its frames (`store.read_frames`; a file that cannot be read hands the press None, which
refuses with «save it again»), under ONE cancellable progress window (`timewalk.Progress`, a
step per pasted frame - `press_steps`); Save, Update and the new preview to `animcapture`
under one too.

Spec: docs/superpowers/specs/2026-10-02-pose-library-design.md ("The window"),
      docs/superpowers/specs/2026-10-03-pose-library-animation-design.md ("Save", "Apply -
      the options", "The window")
"""

import math
import os
import tempfile
import traceback

from maya_poselib import animdata
from maya_poselib import cardgrid
from maya_poselib import look
from maya_poselib import store

CONTROL = "skeldarPoseLibrary"
LABEL = "Pose Library"
ROOT = "skeldarPoseLibraryRoot"       # the Qt root's objectName (found by it, trap 102)
INITIAL_WIDTH, INITIAL_HEIGHT = 1000, 640

GHOST_NAME = cardgrid.GHOST_NAME
CANVAS_NAME = cardgrid.CANVAS_NAME
SCROLL_NAME = cardgrid.SCROLL_NAME
TREE_NAME = "skeldarPoseFolders"

#  The hub card (build_panel).
NOTE = "Poses and animations of bones - onto any rig or skeleton."
NOTE_NAME = "skeldarPoseLibraryNote"
OPEN_BUTTON = "skeldarPoseLibraryOpen"
OPEN_LABEL = "Open Pose Library"

#  What the window remembers between sessions (optionVars).
SORT_VAR = "skeldarPoseLibrarySort"
SIZE_VAR = "skeldarPoseLibraryCardSize"
SORT_LABELS = (("Name", "name"), ("Newest", "newest"), ("Character", "character"))
TYPE_VAR = "skeldarPoseLibraryType"            # the type filter: store.TYPES
TYPE_LABELS = (("All", "all"), ("Poses", "pose"), ("Animations", "anim"))
SAVE_TYPE_VAR = "skeldarPoseLibrarySaveType"   # the save panel's segments: "pose" | "anim"
SAVE_TYPES = (("pose", "Pose"), ("anim", "Animation"))
SAVE_NAMES = {"pose": "Pose", "anim": "Anim"}  # a new card's name before the animator types one
#  The paste options of an animation card (animdata.Options), each but the range remembered
PASTE_VAR = "skeldarPoseLibraryPaste"
AT_CURRENT_VAR = "skeldarPoseLibraryAtCurrent"
CONNECT_VAR = "skeldarPoseLibraryConnect"
KEYS_VAR = "skeldarPoseLibraryKeys"
IN_PLACE_VAR = "skeldarPoseLibraryInPlace"
KEY_LABELS = (("every", "Every frame"), ("source", "Source keys"))
FRAME_LIMIT = 1000000                # a Start / End spin box's reach, either way

#  The details' playback beat while its window is off the screen - a floating Pose Library whose
#  Maya is minimised: Windows hides it with no hideEvent, Qt still says visible (measured in a GUI
#  Maya, 2026-10-08: each 33 ms tick then copied, scaled and set a cell nobody saw, 0.8 ms
#  each) - slow enough to cost nothing, quick enough to play again when the window comes back
PLAY_HIDDEN_MS = 500
GA_ROOT = 2                          # GetAncestor: the root window of a child's chain
BLEND_SPAN = 200                     # logical px of a middle drag from 0 to 100 %
FOLLOW_MS = 120                      # the selection's reading, coalesced
EVENTS = ("SelectionChanged", "Undo", "Redo", "SceneOpened", "NewSceneOpened")

NO_PICK = "pick a card first"
CANCELLED = cardgrid.CANCELLED
BLEND_CANCELLED = "blend cancelled - every value back"
OBJECTS_DRAG = "an objects card: select its objects and press Apply"
OBJECTS_TARGET = "onto the selected objects, else the ones it was saved from"
NOT_A_CHARACTER = "the selection holds no character - select any part of one"
NO_CHARACTER = "no character in the scene"
MANY = "%d characters in the scene (%s) - select any part of the one you mean"
GONE = "the card is gone - Refresh"
SEARCH_HINT = "search name, folder, character"
EMPTY_LIBRARY = "Nothing saved yet - select a character and press Save"
EMPTY_SEARCH = "No card matches"
NO_RANGE = "End is before Start - no frame to save"
NAME_TAKEN = "%s is taken in %s - type another name, or pick another folder"
PREVIEW_CANCELLED = "cancelled - nothing changed"
PREVIEW_KEPT = "the preview kept: %s"
NO_PREVIEW = "saved without a preview: %s"
APPLY_TIPS = {False: "Key the pose on the current frame, on the active animation layer, onto "
                     "the selected characters",
              True: "Paste the animation with the options above, on the active animation "
                    "layer, onto the selected characters"}
PASTE_TIPS = {"replace": "The keys inside the paste range cut, then the clip keyed",
              "replace_all": "Every key of the pasted channels cut, then the clip keyed",
              "insert": "Every key from the paste frame on moved later by the clip's length, "
                        "the clip keyed into the gap",
              "merge": "The clip keyed over what is there - a key between its frames stays"}


def _last_line(error_text):
    lines = [line for line in (error_text or "").strip().splitlines() if line.strip()]
    return lines[-1] if lines else "failed"


def _counted(count, noun):
    """«1 card», «3 cards»."""
    return "%d %s%s" % (count, noun, "" if count == 1 else "s")


def _remove(path):
    """The file at `path` gone, if it was there (a temporary snapshot or sheet)."""
    try:
        os.remove(path)
    except OSError:
        pass


def _cmds():
    """`maya.cmds`, imported when first needed (a seam: the tests hand in a recording one)."""
    import maya.cmds as cmds
    return cmds


def _current_time():
    """The scene's current frame - where a paste starts, so how many frames it walks. A seam."""
    return float(_cmds().currentTime(query=True))


def _whole(value):
    """A frame as a whole frame, rounded half UP - `animdata`'s rule: Python's round() goes to
    even, and 12.5 must not land on 12 while 13.5 lands on 14."""
    return int(math.floor(float(value) + 0.5))


def _name_of(path):
    """A card's name: its folder's, without the card's own suffix (`.pose` or `.anim`)."""
    base = os.path.basename(path.replace("\\", "/").rstrip("/"))
    return base[:-len(store.card_suffix(base))]


def _noun(path):
    """What the card at `path` is, as a dialog's title names it: "animation" or "pose"."""
    return "animation" if store.is_anim(path) else "pose"


def native_shown(hwnd, user32):
    """Whether the native window `hwnd` (a WId as an int) can be seen, asked of Windows
    (`user32`, `ctypes`' or a test's): its ROOT window (GetAncestor GA_ROOT; the window itself
    when it is one) visible and not minimised. A floating Pose Library whose Maya is minimised is
    HIDDEN with its owner (measured 2026-10-08: IsWindowVisible False, Qt still saying visible);
    a docked one stands in Maya's own window, minimised (IsIconic). No handle, or one Windows
    does not know (offscreen Qt), counts as seen - nothing to ask."""
    if not hwnd or not user32.IsWindow(hwnd):
        return True
    root = user32.GetAncestor(hwnd, GA_ROOT) or hwnd
    return bool(user32.IsWindowVisible(root)) and not bool(user32.IsIconic(root))


_USER32 = []


def _user32():
    """Windows' user32 with the four calls `native_shown` makes typed for 64-bit handles (a
    WinDLL of its own: `ctypes.windll.user32`, which other code shares, is left as it is), or
    None off Windows. A seam."""
    if not _USER32:
        try:
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.WinDLL("user32")
            user32.IsWindow.argtypes = [wintypes.HWND]
            user32.IsWindow.restype = wintypes.BOOL
            user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
            user32.GetAncestor.restype = wintypes.HWND
            user32.IsWindowVisible.argtypes = [wintypes.HWND]
            user32.IsWindowVisible.restype = wintypes.BOOL
            user32.IsIconic.argtypes = [wintypes.HWND]
            user32.IsIconic.restype = wintypes.BOOL
        except (ImportError, AttributeError, OSError):
            user32 = None
        _USER32.append(user32)
    return _USER32[0]


def defer(fn):
    """Run `fn` one idle later (`maya.utils.executeDeferred`): a floor drop adds a character,
    which takes seconds and imports a file - never inside the mouse event that released it.
    The tests replace this."""
    import maya.utils
    maya.utils.executeDeferred(fn)


def plugin_root():
    """The plugin folder: the one holding `maya_poselib`."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace("\\", "/")


# ------------------------------------------------------------------ pure

def blend_alpha(dx, scale=1.0):
    """The blend a middle drag of `dx` physical px across a card means: 0 at the press, 1 at
    `BLEND_SPAN` logical px to the right, clamped to 0..1 (a drag to the left is 0 - the current
    pose). Pure."""
    span = BLEND_SPAN * float(scale or 1.0)
    return max(0.0, min(1.0, float(dx) / span))


def in_folder(card_folder, folder):
    """Whether a card in `card_folder` shows when the tree's `folder` is picked: the folder and
    every catalog below it ("" - the library - holds every card), never a namesake beside it
    ("HandsOld" is not in "Hands"). Case-insensitive, as the disk is. Pure."""
    folder = (folder or "").strip("/").lower()
    if not folder:
        return True
    here = (card_folder or "").strip("/").lower()
    return here == folder or here.startswith(folder + "/")


def shown_cards(cards, folder, query, sort, type_name="all"):
    """The cards the grid shows: those in `folder` (`in_folder`) of the type filter's
    `type_name` (`store.of_type`: all, pose, anim; anything else is all) matching `query`
    (`store.filter_cards`), ordered by `sort` (`store.SORTS`; anything else is by name). Pure."""
    kept = [card for card in cards if in_folder(card.folder, folder)]
    kept = store.of_type(kept, type_name if type_name in store.TYPES else "all")
    kept = store.filter_cards(kept, query)
    return store.sort_cards(kept, sort if sort in store.SORTS else "name")


def save_frames_text(start, end):
    """What the save panel says an animation over `start`..`end` (whole frames) takes: «48
    frames · 48 preview cells» - every frame read, at most `look.PREVIEW_MAX` of them blasted
    into the preview (a longer clip every step-th: «100 frames · 50 preview cells»); `NO_RANGE`
    when End stands before Start. Pure."""
    start, end = _whole(start), _whole(end)
    if end < start:
        return NO_RANGE
    cells = len(look.preview_frames(start, end)[0])
    return "%s %s %s" % (_counted(end - start + 1, "frame"), look.DOT,
                         _counted(cells, "preview cell"))


def _as_options(options):
    """`animdata.Options` of what a press is handed - None the defaults, an `Options` as it is,
    a mapping (the window's) made valid (`animapply._options`' rule)."""
    if options is None:
        return animdata.Options()
    if isinstance(options, animdata.Options):
        return options
    return animdata.options_from(options)


def press_steps(header, options, current):
    """How many steps the progress window of an animation press takes - what the press steps:
    a character card one per pasted frame (`animdata.paste_plan` of `options` at the frame
    `current`), an objects card at most one per channel it holds; at least one (a press the plan
    refuses steps none, and says why). Pure."""
    header = header or {}
    if header.get("kind") == "objects":
        channels = sum(len((record or {}).get("attrs") or {})
                       for record in header.get("objects") or ())
        return max(1, channels)
    try:
        plan = animdata.paste_plan(header.get("start", 0.0), header.get("end", 0.0),
                                   header.get("key_times"), _as_options(options), current)
    except (TypeError, ValueError):
        return 1
    return max(1, len(plan.frames))


def remembered_options(read):
    """The paste options the block starts with (`animdata.Options`; the range is the card's,
    never remembered): `read(name)` answers an optionVar's value, None for one never written -
    a missing optionVar is its default (At current time on), never the 0 Maya answers for it.
    `animdata.options_from` makes every value valid: a mode from another build is Replace.
    Pure."""
    return animdata.options_from({"mode": read(PASTE_VAR), "at_current": read(AT_CURRENT_VAR),
                                  "connect": read(CONNECT_VAR), "keys": read(KEYS_VAR),
                                  "in_place": read(IN_PLACE_VAR)})


def folder_text(rel):
    """A catalog as the window names it: "Library", "Library / Hands / Left"."""
    parts = [part for part in (rel or "").split("/") if part]
    return " / ".join(["Library"] + parts)


def regions_arg(initial, checked):
    """What Save hands `capture.build_pose` as `regions`: None while the chips still say what
    the selection lit (`initial`; None for an objects selection, which has no chips) - the pose
    is then the selection's own members - else the lit chips as a list, in the order given."""
    if initial is None:
        return None
    if set(checked) == set(initial):
        return None
    return list(checked)


def scene_aim(kind, label, target):
    """The caption's aim (`look.drop_caption`) for a card of `kind` from `label` (its source's
    catalog label) over the scene's `target` (`Scene.target`: kind "character" with root and
    label, "floor" with point, or "none" with text). An objects card (a pose or an
    animation) has no character to go onto and no source to add: always "none", saying how it
    is applied (`OBJECTS_DRAG`). Pure."""
    if kind == "objects":
        return {"kind": "none", "text": OBJECTS_DRAG}
    target = target or {}
    if target.get("kind") == "character":
        return {"kind": "character", "label": target.get("label"), "root": target.get("root")}
    if target.get("kind") == "floor":
        return {"kind": "floor", "label": label, "point": target.get("point")}
    return {"kind": "none", "text": target.get("text") or look.NO_TARGET}


def targets_text(labels, selected, every):
    """(text, ok): the details' target line - who Apply would pose - and whether anybody.
    `labels` name the selection's characters, `selected` says whether anything at all is
    selected, `every` names every character in the scene. The apply's own rule
    (`apply.choose_targets`), so the line never promises what the press then refuses: the
    selection's characters; a selection holding none is refused, never redirected; nothing
    selected - the only character, else a refusal naming them. Pure."""
    if labels:
        return "onto " + ", ".join(labels), True
    if selected:
        return NOT_A_CHARACTER, False
    every = list(every or ())
    if len(every) == 1:
        return "onto %s - the only character" % every[0], True
    if not every:
        return NO_CHARACTER, False
    return MANY % (len(every), ", ".join(every)), False


def uiscript(root):
    """The Python Maya replays to (re)build the window, the plugin folder baked in - Maya
    replays a docked control's uiScript at startup before any button ran (the hub's lesson).
    Forward slashes only: the string reaches Maya's workspace file, where a backslash starts an
    escape."""
    root = root.replace("\\", "/").rstrip("/")
    return ("import sys\n"
            "_p = \"{0}\"\n"
            "if _p not in sys.path:\n"
            "    sys.path.insert(0, _p)\n"
            "import maya_poselib.window as w\n"
            "w.build()\n").format(root)


def _closing(scene, jobs):
    """What a window's death does to the scene: a blend previewed but never keyed is put back
    (its values would otherwise sit unkeyed until the next time change), the jobs killed."""
    try:
        scene.blend_cancel()
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()
    scene.unwatch(jobs)


def _regions():
    """Every region chip the save panel shows, in the card's order (`posemath.REGIONS`)."""
    from maya_poselib import posemath
    return list(posemath.REGIONS)


# ------------------------------------------------------------------ the scene

class Scene(object):
    """The real scene: everything the window asks of Maya. The tests hand in a fake."""

    def __init__(self):
        self._blend = None
        self._blend_card = None     # (path, header, options) while an animation's blend stands

    # ---------------------------------------------------------- settings

    def scale(self):
        try:
            return float(_cmds().mayaDpiSetting(query=True, realScaleValue=True) or 1.0)
        except Exception:                                    # noqa: BLE001
            return 1.0

    def library(self):
        cmds = _cmds()
        value = ""
        if cmds.optionVar(exists=store.ROOT_VAR):
            value = cmds.optionVar(query=store.ROOT_VAR) or ""
        root = store.library_root(value, plugin_root())
        if not os.path.isdir(root):
            os.makedirs(root)                    # the plugin's own library, made on first use
        return root

    def set_library(self, root):
        _cmds().optionVar(stringValue=(store.ROOT_VAR, root))

    def option(self, name, default=None):
        cmds = _cmds()
        if cmds.optionVar(exists=name):
            return cmds.optionVar(query=name)
        return default

    def set_option(self, name, value):
        flag = "intValue" if isinstance(value, int) else (
            "floatValue" if isinstance(value, float) else "stringValue")
        _cmds().optionVar(**{flag: (name, value)})

    def trash(self):
        return store.trash_dir(_cmds().internalVar(userAppDir=True))

    # ---------------------------------------------------------- the selection

    def selection_label(self):
        from maya_poselib import scene
        return scene.selection_label()

    def selection_regions(self):
        """The regions the selection's bones lie in (the chips Save pre-lights), or None when
        the selection is no ONE character's (an objects pose, or a refusal)."""
        from maya_poselib import scene
        resolved = scene.resolve()
        refs = []
        for _path, ref in resolved:
            if ref is not None and all(r.root != ref.root for r in refs):
                refs.append(ref)
        if len(refs) != 1:
            return None
        nodes = [path for path, ref in resolved if ref is not None]
        bones, _convention = scene.skeleton(refs[0])
        return scene.regions_of(bones, scene.members_of(refs[0], nodes, bones))

    def apply_targets(self):
        """(text, ok): who Apply would pose (`targets_text`), each character named as the
        apply's status line names it - a rig by its namespace."""
        from maya_poselib import scene

        def label(ref):
            if ref.kind == "rig" and ref.namespace:
                return ref.namespace
            return scene.describe([ref], [])

        selection = _cmds().ls(selection=True, long=True) or []
        refs, _loose = scene.characters(selection)
        every = [] if (refs or selection) else scene.all_characters()
        return targets_text([label(r) for r in refs], bool(selection),
                            [label(r) for r in every])

    def watch(self, callback):
        """A scriptJob per event calling `callback`, parented to the control when it stands
        (Maya then kills them with it); the job ids made. Measured in mayapy standalone:
        `scriptJob` answers None and makes no job there, parented or not - so only integer ids
        are kept, and a window built outside the control gets plain jobs."""
        cmds = _cmds()
        try:
            parent = {"parent": CONTROL} if cmds.workspaceControl(CONTROL, exists=True) else {}
        except Exception:                                    # noqa: BLE001
            parent = {}
        jobs = []
        for event in EVENTS:
            try:
                job = cmds.scriptJob(event=[event, callback], **parent)
            except Exception:                                # noqa: BLE001
                job = None
            if isinstance(job, int):
                jobs.append(job)
        return jobs

    def unwatch(self, jobs):
        cmds = _cmds()
        for job in jobs or []:
            if not isinstance(job, int):
                continue
            try:
                if cmds.scriptJob(exists=job):
                    cmds.scriptJob(kill=job, force=True)
            except Exception:                                # noqa: BLE001
                pass

    # ---------------------------------------------------------- save

    def anim_range(self):
        """(start, end) whole frames an animation saves by default: the time slider's highlight
        when the animator dragged one, else the playback range (`animcapture.default_range`)."""
        from maya_poselib import animcapture
        return animcapture.default_range()

    def save(self, name, folder, regions, snapshot_path, anim=None):
        """(path, text): the selection written as the card `name` into `folder`, the snapshot as
        its thumbnail - a pose, or with `anim` ({"start", "end"}: whole source frames) an
        animation over that range (`_save_animation`); (None, why) when the selection makes no
        card, the name is taken, or the animator cancelled."""
        if anim is not None:
            return self._save_animation(name, folder, regions, snapshot_path, anim)
        from maya_poselib import capture
        data, note = capture.build_pose(regions=regions)
        if data is None:
            return None, note
        thumbnail = snapshot_path if snapshot_path and os.path.isfile(snapshot_path) else None
        try:
            path = store.write(self.library(), folder, name, data, thumbnail=thumbnail)
        except (ValueError, OSError) as exc:
            return None, str(exc)
        return path, "saved %s in %s - %s" % (_name_of(path), folder_text(folder), note)

    def _sheet_path(self):
        """Where a preview sheet is painted before the card takes it (one per Maya)."""
        return os.path.join(tempfile.gettempdir(), "skeldar_anim_sheet_%d.jpg"
                            % os.getpid()).replace("\\", "/")

    def _save_animation(self, name, folder, regions, snapshot_path, anim):
        """An animation card of the selection over `anim`'s range, in ONE progress window (a
        step a frame read, a step a preview cell painted): its header and frames
        (`animcapture.build_animation`), then its preview sheet (`animcapture.preview`) painted
        into a temporary file, then the card written - the frames, the still, the sheet, the
        header last (`store.write`). A cancel in either step writes nothing; a preview that
        cannot be made (batch, no viewport, a playblast that failed) saves the card without
        one and the line says why - a preview that raises too, its error's last line the why
        (the frames are read by then, and a Save must not lose them over the picture)."""
        from maya_poselib import animcapture
        from maya_poselib import timewalk
        start, end = _whole(anim.get("start")), _whole(anim.get("end"))
        cells = len(look.preview_frames(start, end)[0])
        sheet = self._sheet_path()
        _remove(sheet)
        try:
            with timewalk.Progress("Saving %s" % name, max(0, end - start + 1) + cells) \
                    as progress:
                header, frames, note = animcapture.build_animation(
                    regions=regions, start=start, end=end, progress=progress)
                if header is None:
                    return None, note
                #  the frames are walked: a preview that RAISES (a playblast Maya refused) is
                #  one that cannot be made - the card saved without it, the line saying why
                try:
                    made, said, info = animcapture.preview(sheet, start, end, progress)
                except Exception:                            # noqa: BLE001
                    traceback.print_exc()
                    made, said, info = False, _last_line(traceback.format_exc()), None
            if not made and said == animcapture.CANCELLED:
                return None, said
            if made:
                header["preview"] = info
            thumbnail = snapshot_path if snapshot_path and os.path.isfile(snapshot_path) \
                else None
            try:
                path = store.write(self.library(), folder, name, header, thumbnail=thumbnail,
                                   frames=frames, preview=sheet if made else None)
            except (ValueError, OSError) as exc:
                return None, str(exc)
        finally:
            _remove(sheet)
        text = "saved %s in %s - %s" % (_name_of(path), folder_text(folder), note)
        return path, text + " | " + (said if made else NO_PREVIEW % said)

    def snapshot(self, path):
        from maya_poselib import capture
        return capture.thumbnail(path)

    def update(self, path):
        """(ok, text): the card at `path` re-made from the selection, its name and thumbnail
        kept - an animation over its OWN range again, its preview kept too (the sheet and the
        grid its header names: the range is the one it was painted over). Written into the card
        AT ITS PATH (`store.replace`): a card renamed in Explorer to a name `safe_name` would
        change came back by name as a stray new card (the final review)."""
        name = _name_of(path)
        if not store.is_anim(path):
            from maya_poselib import capture
            data, note = capture.build_pose()
            if data is None:
                return False, note
            store.replace(path, data)
            return True, "%s updated from the selection - %s" % (name, note)
        from maya_poselib import animcapture
        from maya_poselib import timewalk
        old = store.read(path)
        start, end = _whole(old.get("start") or 0.0), _whole(old.get("end") or 0.0)
        with timewalk.Progress("Updating %s" % name, max(1, end - start + 1)) as progress:
            header, frames, note = animcapture.build_animation(start=start, end=end,
                                                               progress=progress)
        if header is None:
            return False, note
        if "preview" in old:
            header["preview"] = old["preview"]
        store.replace(path, header, frames=frames)
        return True, "%s updated from the selection over frames %d-%d - %s" % (
            name, start, end, note)

    def replace_preview(self, path):
        """The line: the card at `path` given its still again (the viewport now) and - an
        animation - its preview again over its own range, in one progress window (a step a
        cell). Written together into the card at its path (`store.replace`, the header last,
        with the new sheet's grid); a cancel writes nothing; a preview that cannot be made keeps
        the old one and says why; no still keeps the old one."""
        image = os.path.join(tempfile.gettempdir(), "skeldar_pose_snapshot_%d_replace.jpg"
                             % os.getpid()).replace("\\", "/")
        sheet = self._sheet_path()
        _remove(image)
        _remove(sheet)
        try:
            shot, shot_text = self.snapshot(image)
            shot = shot and os.path.isfile(image)
            if not store.is_anim(path):
                if not shot:
                    return shot_text
                store.set_thumbnail(path, image)
                return "new thumbnail - " + shot_text
            from maya_poselib import animcapture
            from maya_poselib import timewalk
            header = store.read(path)
            start, end = _whole(header.get("start") or 0.0), _whole(header.get("end") or 0.0)
            cells = len(look.preview_frames(start, end)[0])
            with timewalk.Progress("Previewing %s" % _name_of(path), cells) as progress:
                made, said, info = animcapture.preview(sheet, start, end, progress)
            if not made and said == animcapture.CANCELLED:
                return PREVIEW_CANCELLED
            if made:
                header["preview"] = info
                store.replace(path, header, thumbnail=image if shot else None, preview=sheet)
            elif shot:
                store.set_thumbnail(path, image)
        finally:
            _remove(image)
            _remove(sheet)
        if made:
            head = "new thumbnail and preview" if shot else "new preview"
            return "%s - %s | %s" % (head, shot_text if shot else "the still kept: "
                                     + shot_text, said)
        if shot:
            return "new thumbnail - %s | %s" % (shot_text, PREVIEW_KEPT % said)
        return "%s | %s" % (shot_text, PREVIEW_KEPT % said)

    # ---------------------------------------------------------- apply

    def _frames(self, path, header):
        """The frames an animation press hands on: a character card's decoded
        `frames.json.gz`, or None - an objects card holds none, and a file that cannot be read
        lets the press refuse with its own words («the card has no frames - save it again»)."""
        if (header or {}).get("kind") == "objects":
            return None
        try:
            return store.read_frames(path)
        except ValueError:
            return None

    def _paste(self, press, path, options):
        """`press(header, frames, progress)` - an `animapply` press of the animation card at
        `path` - run in ONE progress window, a step a pasted frame (`press_steps`); its
        (ok, text)."""
        from maya_poselib import timewalk
        header = store.read(path)
        frames = self._frames(path, header)
        steps = press_steps(header, options, _current_time())
        with timewalk.Progress("Pasting %s" % _name_of(path), steps) as progress:
            return press(header, frames, progress)

    def apply(self, path, mirror, options=None):
        """The card at `path` onto the selection: a pose (`apply.apply`), or an animation
        pasted with `options` (`animapply.apply`)."""
        if store.is_anim(path):
            from maya_poselib import animapply
            return self._paste(lambda header, frames, progress: animapply.apply(
                header, frames, mirror=mirror, options=options, progress=progress),
                path, options)
        from maya_poselib import apply
        return apply.apply(store.read(path), mirror=mirror)

    def apply_onto(self, path, root, mirror, options=None):
        """The card at `path` onto the character of `root` (a drop on it in a viewport)."""
        if store.is_anim(path):
            from maya_poselib import animapply
            return self._paste(lambda header, frames, progress: animapply.apply_onto(
                header, frames, root, mirror=mirror, options=options, progress=progress),
                path, options)
        from maya_poselib import apply
        return apply.apply_onto(store.read(path), root, mirror=mirror)

    def drop_floor(self, path, point, mirror, options=None):
        """The card's source character added at the floor `point`, then the card onto it."""
        if store.is_anim(path):
            from maya_poselib import animapply
            return self._paste(lambda header, frames, progress: animapply.drop_floor(
                header, frames, point, mirror=mirror, options=options, progress=progress),
                path, options)
        from maya_poselib import apply
        return apply.drop_floor(store.read(path), point, mirror=mirror)

    def select_objects(self, path, options=None):
        """What a press of the card at `path` would key, selected (an animation's: plus Main
        or the root when its travel would be carried - `options`' In place)."""
        if store.is_anim(path):
            from maya_poselib import animapply
            return animapply.select_objects(store.read(path), options=options)
        from maya_poselib import apply
        return apply.select_objects(store.read(path))

    def blend_start(self, path, mirror, options=None):
        """'' when a blend session stands for the card at `path`, else why not. An animation
        card's session (`animapply.Blend`) previews one frame and pastes the whole range on
        release (`blend_finish`)."""
        self.blend_cancel()
        if store.is_anim(path):
            from maya_poselib import animapply
            header = store.read(path)
            session = animapply.Blend()
            refusal = session.start(header, self._frames(path, header), mirror=mirror,
                                    options=options)
            card = (path, header, options)
        else:
            from maya_poselib import apply
            session = apply.Blend()
            refusal = session.start(store.read(path), mirror=mirror)
            card = None
        if refusal:
            return refusal
        self._blend, self._blend_card = session, card
        return ""

    def blend_set(self, alpha):
        if self._blend is not None:
            self._blend.set(alpha)

    def blend_finish(self):
        """The blend keyed where it stands - an animation card's whole range pasted at that
        weight, in one progress window."""
        session, card = self._blend, self._blend_card
        self._blend = self._blend_card = None
        if session is None:
            return ""
        if card is None:
            return session.finish()
        from maya_poselib import timewalk
        path, header, options = card
        steps = press_steps(header, options, _current_time())
        with timewalk.Progress("Pasting %s" % _name_of(path), steps) as progress:
            return session.finish(progress)

    def blend_cancel(self):
        session, self._blend = self._blend, None
        self._blend_card = None
        if session is not None:
            session.cancel()

    # ---------------------------------------------------------- drops

    def snapshot_scene(self):
        """Every character's bones in world space, read once for one drag."""
        from maya_scenesetup import droptarget
        return droptarget.snapshot()

    def target(self, gx, gy, snap):
        """What is under the global point: a character in a viewport, else the floor the camera
        ray meets, else nothing (with why)."""
        from maya_scenesetup import droptarget
        aim = droptarget.character_target(gx, gy, snap, self.scale())
        if aim.get("kind") == "character" or aim.get("text") == droptarget.NO_VIEWPORT:
            return aim
        return droptarget.floor_at(gx, gy)

    def over_window(self, gx, gy):
        """The global point lies on the hub, or on this window's control (its title bar
        included)."""
        import maya_hubqt
        return bool(maya_hubqt.on_hub(gx, gy) or maya_hubqt.on_hub(gx, gy, control=CONTROL))

    # ---------------------------------------------------------- the rest

    def say(self, text):
        if not text:
            return
        try:
            import maya.api.OpenMaya as om
            om.MGlobal.displayInfo("Pose Library: %s" % text)
        except Exception:                                    # noqa: BLE001
            pass

    def reveal(self, path):
        """Explorer with `path` selected in its folder."""
        import subprocess
        subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])

    def open_path(self, path):
        os.startfile(os.path.normpath(path))                 # noqa: S606 - Windows only


# ------------------------------------------------------------------ Qt

_CLASSES = {}


def _classes():
    """The widget classes, built on first use (Qt imported here)."""
    if _CLASSES:
        return _CLASSES
    import maya_hubqt
    import maya_hubstyle as hubstyle

    q = maya_hubqt.qt()
    QtCore, QtGui, QtWidgets = q.QtCore, q.QtGui, q.QtWidgets
    Qt = QtCore.Qt
    scaled = cardgrid.scaled

    # ---------------------------------------------------------- the Blend slider

    class BlendSlider(QtWidgets.QSlider):
        """The Blend slider: only a LEFT DRAG moves it, so only a release keys a blend.

        A stock QSlider also moves under the wheel (it takes wheel events with NoFocus), under
        the keys, and under a groove press, which page-steps at once and then auto-repeats. Each
        of those changed the value with the slider up. Review finding 1 (2026-10-03) measured
        what that did when valueChanged keyed: three wheel notches keyed three 3 % blends. A
        left press held 1.5 s on the groove keyed seventeen 10 % blends, each one starting from
        the pose the last keyed, about 83 % of the card in 17 undo steps. So:

          - the wheel and the keys are IGNORED: the wheel goes on to the side panel's scroll
            area, which scrolls (that panel scrolls in a short dock);
          - a left press on the GROOVE downs the slider first (sliderPressed: the session
            starts), then puts the handle's centre under the press (sliderMoved: the preview),
            and follows the mouse until the release (sliderReleased: the blend is keyed).
            There is no page step and no auto-repeat. A left press on the HANDLE is Qt's own
            drag, which keeps the grab offset;
          - the middle and right buttons are ignored (in Fusion the middle one jumps the
            handle, a path that runs before sliderPressed).
        """

        def __init__(self, parent=None):
            QtWidgets.QSlider.__init__(self, Qt.Horizontal, parent)
            self._groove_drag = False
            # a drag whose release never comes (Alt+Tab, a release outside Qt) is seen on the
            # next move with the left button no longer held - moves without a button arrive
            # only with tracking on - and `on_lost` (the window's) is told instead of a release
            self.on_lost = None
            self.setMouseTracking(True)

        def drop(self):
            """The slider up again WITHOUT sliderReleased (which keys the blend)."""
            self._groove_drag = False
            if self.isSliderDown():
                self.blockSignals(True)
                try:
                    self.setSliderDown(False)
                finally:
                    self.blockSignals(False)

        def _geometry(self):
            opt = QtWidgets.QStyleOptionSlider()
            self.initStyleOption(opt)
            style = self.style()
            groove = style.subControlRect(QtWidgets.QStyle.CC_Slider, opt,
                                          QtWidgets.QStyle.SC_SliderGroove, self)
            handle = style.subControlRect(QtWidgets.QStyle.CC_Slider, opt,
                                          QtWidgets.QStyle.SC_SliderHandle, self)
            return opt, groove, handle

        def value_at(self, x):
            """The value whose handle is centred on local `x`, by Qt's own arithmetic
            (QSliderPrivate::pixelPosToRangeValue, a press minus the handle's half width)."""
            opt, groove, handle = self._geometry()
            lowest = groove.x()
            highest = groove.right() - handle.width() + 1
            return QtWidgets.QStyle.sliderValueFromPosition(
                self.minimum(), self.maximum(),
                int(round(x)) - (handle.width() - 1) // 2 - lowest,
                max(1, highest - lowest), opt.upsideDown)

        def handle_rect(self):
            """Where the style draws the handle now, local px."""
            return self._geometry()[2]

        def on_handle(self, point):
            return self.handle_rect().contains(point)

        def wheelEvent(self, event):                         # noqa: N802
            event.ignore()

        def keyPressEvent(self, event):                      # noqa: N802
            event.ignore()

        def mousePressEvent(self, event):                    # noqa: N802
            if event.button() != Qt.LeftButton or event.buttons() != Qt.LeftButton:
                event.ignore()
                return
            point = event.position().toPoint()
            if self.on_handle(point):
                QtWidgets.QSlider.mousePressEvent(self, event)
                return
            event.accept()
            self._groove_drag = True
            self.setSliderDown(True)
            self.setSliderPosition(self.value_at(point.x()))

        def mouseMoveEvent(self, event):                     # noqa: N802
            if (self._groove_drag or self.isSliderDown()) and \
                    not event.buttons() & Qt.LeftButton:
                event.accept()                   # the release was lost: told, never keyed
                self.drop()
                if self.on_lost is not None:
                    self.on_lost()
                return
            if self._groove_drag:
                event.accept()
                self.setSliderPosition(self.value_at(event.position().x()))
                return
            QtWidgets.QSlider.mouseMoveEvent(self, event)

        def mouseReleaseEvent(self, event):                  # noqa: N802
            if self._groove_drag:
                if event.button() != Qt.LeftButton:
                    event.ignore()
                    return
                event.accept()
                self._groove_drag = False
                self.setSliderDown(False)
                return
            QtWidgets.QSlider.mouseReleaseEvent(self, event)

    # ---------------------------------------------------------- a frame field

    class FrameBox(QtWidgets.QSpinBox):
        """A whole frame (Start / End, the paste's Range): typed, or stepped with the arrow
        keys - no arrow buttons, a field of the hub's - and under the wheel only once it has
        the focus. A wheel turned over the side panel scrolls the panel: a range moved by a
        scroll that passed over the field would paste or save other frames (the Blend
        slider's lesson, review finding 1)."""

        def __init__(self, name, parent=None):
            QtWidgets.QSpinBox.__init__(self, parent)
            self.setObjectName(name)
            self.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
            self.setFocusPolicy(Qt.StrongFocus)
            self.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.setRange(-FRAME_LIMIT, FRAME_LIMIT)

        def wheelEvent(self, event):                         # noqa: N802
            if not self.hasFocus():
                event.ignore()
                return
            QtWidgets.QSpinBox.wheelEvent(self, event)

    # ---------------------------------------------------------- the window

    class PoseWindow(QtWidgets.QWidget):
        """The whole window. `scene` is `Scene()` in Maya, a fake in the tests."""

        def __init__(self, scene, parent=None, root=None):
            QtWidgets.QWidget.__init__(self, parent)
            self.setObjectName(ROOT)
            self.setAttribute(Qt.WA_StyledBackground, True)
            self.scene = scene
            self.k = float(scene.scale() or 1.0)
            self.root = ""
            self.all_cards = []
            self.broken = []
            self._folder = ""
            self.picked = None
            self.picked_data = None
            self._blend = None              # dict(path) while a blend session stands
            self._save = None               # dict(initial, snapshot, touched) while saving
            self._building_tree = False
            self.scroll = None
            self._targets = None            # the last `apply_targets` reading, None: unknown
            self._stale = False             # the selection changed while the window was hidden
            self._range_for = None          # (path, start, end) the Range boxes were set for
            self._play_path = None          # the animation card the details picture plays ...
            self._play_t0 = 0               # ... and when it began (`_clock_ms`)
            self.follow_timer = QtCore.QTimer(self)
            self.follow_timer.setObjectName("skeldarPoseFollow")
            self.follow_timer.setSingleShot(True)
            self.follow_timer.setInterval(FOLLOW_MS)
            self.follow_timer.timeout.connect(self.follow)
            self._play_clock = QtCore.QElapsedTimer()
            self._play_clock.start()
            self.play_timer = QtCore.QTimer(self)
            self.play_timer.setObjectName("skeldarPosePlay")
            self.play_timer.setInterval(look.PLAY_MS)
            self.play_timer.timeout.connect(self._play_tick)
            self._build()
            self._load_options()
            self.setStyleSheet(sheet(self.k))
            try:
                jobs = scene.watch(self._queue_follow)
            except Exception:                                # noqa: BLE001
                traceback.print_exc()
                jobs = []
            #  the window going (closed, rebuilt by an install): the jobs die and a blend left
            #  half way is put back - the closure holds the scene and the job ids, never self
            watcher = scene
            self.destroyed.connect(lambda *_a: _closing(watcher, jobs))
            self.set_library(root or scene.library())
            self.follow()

        # ------------------------------------------------------ build

        def px(self, value):
            return hubstyle.px(value, self.k)

        def _button(self, text, role=None, icon_name=None, name=None):
            button = QtWidgets.QPushButton(text)
            if name:
                button.setObjectName(name)
            if role:
                button.setProperty("skRole", role)
            if icon_name:
                tone = {"primary": "on_accent", "danger": "danger"}.get(role, "text2")
                side = self.px(14)
                try:
                    button.setIcon(maya_hubqt.icon(icon_name, hubstyle.TOKENS[tone], side))
                    button.setIconSize(QtCore.QSize(side, side))
                except Exception:                            # noqa: BLE001
                    pass
            return button

        def _label(self, text="", role=None, name=None, wrap=False):
            label = QtWidgets.QLabel(text)
            if name:
                label.setObjectName(name)
            if role:
                label.setProperty("skRole", role)
            label.setWordWrap(wrap)
            return label

        def _segments(self, prefix, choices, picked, columns=None):
            """(track, {key: button}): the hub's segments - a `segments` track holding one
            checkable `segment` button per (key, text) of `choices`, `columns` to a row (all in
            one by default), one lit at a time (an exclusive QButtonGroup). Each is named
            `prefix + key`; a CLICK on one calls `picked(key)` (lighting one from code
            does not)."""
            s = self.px
            track = QtWidgets.QWidget()
            track.setProperty("skRole", "segments")
            track.setAttribute(Qt.WA_StyledBackground, True)
            grid = QtWidgets.QGridLayout(track)
            grid.setContentsMargins(s(2), s(2), s(2), s(2))
            grid.setSpacing(s(2))
            group = QtWidgets.QButtonGroup(track)
            group.setExclusive(True)
            columns = columns or len(choices)
            buttons = {}
            for index, (key, text) in enumerate(choices):
                button = QtWidgets.QPushButton(text)
                button.setObjectName(prefix + key)
                button.setProperty("skRole", "segment")
                button.setCheckable(True)
                button.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                     QtWidgets.QSizePolicy.Preferred)
                group.addButton(button)
                grid.addWidget(button, index // columns, index % columns)
                button.clicked.connect(lambda _checked=False, k=key: picked(k))
                buttons[key] = button
            return track, buttons

        def _check(self, text, name, tip, var):
            """A remembered option's checkbox: a click writes it to `var` (1 / 0)."""
            box = QtWidgets.QCheckBox(text)
            box.setObjectName(name)
            box.setToolTip(tip)
            box.clicked.connect(lambda checked=False, v=var: self._remember(v, int(bool(checked))))
            return box

        def _build(self):
            s = self.px
            top = QtWidgets.QVBoxLayout(self)
            top.setContentsMargins(s(8), s(8), s(8), s(8))
            top.setSpacing(s(6))
            top.addLayout(self._build_header())
            top.addLayout(self._build_toolbar())

            self.splitter = QtWidgets.QSplitter(Qt.Horizontal)
            self.splitter.setObjectName("skeldarPoseSplitter")
            self.splitter.setChildrenCollapsible(False)
            self.splitter.setHandleWidth(s(6))
            self.splitter.addWidget(self._build_tree())
            self.canvas = cardgrid.make_canvas(self)
            self.scroll = cardgrid.make_scroll(self.canvas)
            self.scroll.setMinimumWidth(s(160))
            self.splitter.addWidget(self.scroll)
            self.splitter.addWidget(self._build_side())
            self.splitter.setStretchFactor(0, 0)
            self.splitter.setStretchFactor(1, 1)
            self.splitter.setStretchFactor(2, 0)
            self.splitter.setSizes([s(190), s(520), s(280)])
            top.addWidget(self.splitter, 1)

            self.status = self._label("", "status", "skeldarPoseStatus", wrap=True)
            self.status.setTextInteractionFlags(Qt.TextSelectableByMouse)
            top.addWidget(self.status)

        def _build_header(self):
            s = self.px
            row = QtWidgets.QHBoxLayout()
            row.setSpacing(s(8))
            title = self._label(LABEL, "hubtitle", "skeldarPoseTitle")
            row.addWidget(title)
            self.path_label = self._label("", "note", "skeldarPosePath")
            self.path_label.setSizePolicy(QtWidgets.QSizePolicy.Ignored,
                                          QtWidgets.QSizePolicy.Preferred)
            row.addWidget(self.path_label, 1)
            self.menu_button = QtWidgets.QToolButton()
            self.menu_button.setObjectName("skeldarPoseMenu")
            self.menu_button.setProperty("skRole", "headbtn")
            self.menu_button.setToolTip("The library")
            try:
                self.menu_button.setIcon(maya_hubqt.icon("dots-vertical",
                                                         hubstyle.TOKENS["muted"], s(16)))
                self.menu_button.setIconSize(QtCore.QSize(s(16), s(16)))
            except Exception:                                # noqa: BLE001
                self.menu_button.setText("...")
            self.menu_button.setPopupMode(QtWidgets.QToolButton.InstantPopup)
            menu = QtWidgets.QMenu(self.menu_button)
            for item in (("Library folder...", self.choose_library),
                         ("Open in Explorer", lambda: self.scene.open_path(self.root)),
                         None,
                         ("Refresh", self.refresh)):
                if item is None:
                    menu.addSeparator()
                    continue
                label, action = item
                entry = QtGui.QAction(label, menu) if hasattr(QtGui, "QAction") \
                    else QtWidgets.QAction(label, menu)
                entry.triggered.connect(lambda _checked=False, fn=action: self._run(fn))
                menu.addAction(entry)
            self.menu_button.setMenu(menu)
            row.addWidget(self.menu_button)
            return row

        def _build_toolbar(self):
            s = self.px
            row = QtWidgets.QHBoxLayout()
            row.setSpacing(s(8))
            self.search = QtWidgets.QLineEdit()
            self.search.setObjectName("skeldarPoseSearch")
            self.search.setPlaceholderText(SEARCH_HINT)
            self.search.setClearButtonEnabled(True)
            self.search.textChanged.connect(lambda _t: self._repopulate())
            row.addWidget(self.search, 1)

            self.type_filter = QtWidgets.QComboBox()
            self.type_filter.setObjectName("skeldarPoseType")
            self.type_filter.setToolTip("Show every card, the poses or the animations")
            for text, key in TYPE_LABELS:
                self.type_filter.addItem(text, key)
            remembered = self.scene.option(TYPE_VAR, "all")
            types = [key for _text, key in TYPE_LABELS]
            self.type_filter.setCurrentIndex(types.index(remembered) if remembered in types
                                             else 0)
            self.type_filter.currentIndexChanged.connect(self._typed)
            row.addWidget(self.type_filter)

            self.sort = QtWidgets.QComboBox()
            self.sort.setObjectName("skeldarPoseSort")
            for text, key in SORT_LABELS:
                self.sort.addItem(text, key)
            remembered = self.scene.option(SORT_VAR, "name")
            keys = [key for _text, key in SORT_LABELS]
            self.sort.setCurrentIndex(keys.index(remembered) if remembered in keys else 0)
            self.sort.currentIndexChanged.connect(self._sorted)
            row.addWidget(self.sort)

            self.size = QtWidgets.QSlider(Qt.Horizontal)
            self.size.setObjectName("skeldarPoseCardSize")
            self.size.setRange(look.CELL_MIN, look.CELL_MAX)
            self.size.setToolTip("Card size")
            self.size.setFixedWidth(s(110))
            try:
                cell = int(self.scene.option(SIZE_VAR, look.CELL_DEFAULT))
            except (TypeError, ValueError):
                cell = look.CELL_DEFAULT
            self.size.setValue(max(look.CELL_MIN, min(look.CELL_MAX, cell)))
            self.size.valueChanged.connect(self._sized)
            row.addWidget(self.size)

            self.save_button = self._button("Save", "primary", "plus", "skeldarPoseSave")
            self.save_button.setToolTip("Save the selection's pose or animation as a card in "
                                        "the folder picked in the tree")
            self.save_button.clicked.connect(lambda: self._run(self.open_save))
            row.addWidget(self.save_button)
            return row

        def _build_tree(self):
            self.tree = QtWidgets.QTreeWidget()
            self.tree.setObjectName(TREE_NAME)
            self.tree.setHeaderHidden(True)
            self.tree.setMinimumWidth(self.px(120))
            self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
            self.tree.customContextMenuRequested.connect(self._tree_menu)
            self.tree.currentItemChanged.connect(self._tree_picked)
            return self.tree

        def _build_side(self):
            """The details / save panel, in a scroll area: its thumbnails are a fixed 220 px,
            and a library docked short (under the timeline) must still reach Apply."""
            s = self.px
            self.side = QtWidgets.QStackedWidget()
            self.side.setObjectName("skeldarPoseSide")
            self.details_page = self._build_details()
            self.save_page = self._build_save()
            self.side.addWidget(self.details_page)
            self.side.addWidget(self.save_page)
            holder = QtWidgets.QScrollArea()
            holder.setObjectName("skeldarPoseSideScroll")
            holder.setWidgetResizable(True)
            holder.setFrameShape(QtWidgets.QFrame.NoFrame)
            holder.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            holder.setMinimumWidth(s(250))
            holder.setWidget(self.side)
            holder.viewport().setObjectName("skeldarPoseSideViewport")
            return holder

        def thumb_side(self):
            """The details' and save panel's thumbnail side, physical px."""
            return self.px(220)

        def _thumb_label(self, name):
            label = self._label("", "thumb", name)
            label.setAlignment(Qt.AlignCenter)
            label.setFixedSize(self.thumb_side(), self.thumb_side())
            return label

        def _build_details(self):
            s = self.px
            page = QtWidgets.QFrame()
            page.setObjectName("skeldarPoseDetails")
            column = QtWidgets.QVBoxLayout(page)
            column.setContentsMargins(s(10), s(10), s(10), s(10))
            column.setSpacing(s(6))
            self.thumb = self._thumb_label("skeldarPoseThumb")
            column.addWidget(self.thumb, 0, Qt.AlignHCenter)
            self.name_label = self._label("", "cardtitle", "skeldarPoseName", wrap=True)
            column.addWidget(self.name_label)
            self.folder_label = self._label("", "note", "skeldarPoseFolder", wrap=True)
            column.addWidget(self.folder_label)
            self.info = self._label("pick a card", "context", "skeldarPoseInfo", wrap=True)
            column.addWidget(self.info)
            self.target_line = self._label("", "note", "skeldarPoseTarget", wrap=True)
            column.addWidget(self.target_line)

            #  Apply first, the options block BELOW what it configures (the final review, M5:
            #  above Apply it pushed Apply below the fold of the default window for every
            #  animation card - 602 px down a 541 px side panel at a scale of 1.0)
            self.apply_button = self._button("Apply", "primary", "check", "skeldarPoseApply")
            self.apply_button.setToolTip(APPLY_TIPS[False])
            self.apply_button.clicked.connect(lambda: self._press_apply())
            column.addWidget(self.apply_button)
            self.mirror = QtWidgets.QCheckBox("Mirror")
            self.mirror.setObjectName("skeldarPoseMirror")
            self.mirror.setToolTip("Left and right swapped - Apply, the blend and the drags")
            column.addWidget(self.mirror)

            blend_row = QtWidgets.QHBoxLayout()
            blend_row.setSpacing(s(6))
            blend_row.addWidget(self._label("Blend", "context"))
            self.blend = BlendSlider()
            self.blend.setObjectName("skeldarPoseBlend")
            self.blend.setRange(0, 100)
            self.blend.setFocusPolicy(Qt.NoFocus)
            self.blend.setToolTip("Drag: the current pose mixed toward the card, keyed on "
                                  "release (Esc: everything back). A middle drag across a "
                                  "card does the same.")
            self.blend.sliderPressed.connect(self._slider_pressed)
            self.blend.sliderMoved.connect(self._slider_moved)
            self.blend.sliderReleased.connect(self._slider_released)
            self.blend.valueChanged.connect(self._slider_value)
            self.blend.on_lost = self.lost_release
            blend_row.addWidget(self.blend, 1)
            self.blend_label = self._label("0 %", "context", "skeldarPoseBlendValue")
            self.blend_label.setMinimumWidth(s(36))
            blend_row.addWidget(self.blend_label)
            column.addLayout(blend_row)

            self.select_button = self._button("Select objects", "secondary", "target",
                                              "skeldarPoseSelect")
            self.select_button.setToolTip("Select what the card would key on the target")
            self.select_button.clicked.connect(lambda: self._press_select())
            column.addWidget(self.select_button)
            self.anim_options = self._build_options()
            self.anim_options.setVisible(False)
            column.addWidget(self.anim_options)
            column.addStretch(1)
            return page

        def _build_options(self):
            """The paste options of an animation card (shown while one is picked, under Apply,
            Mirror, Blend and Select objects): Paste, At current time + Connect, Range, Keys +
            In place - Studio Library's, in an inset, two options to a row (M5)."""
            s = self.px
            frame = QtWidgets.QFrame()
            frame.setObjectName("skeldarPoseAnimOptions")
            frame.setProperty("skRole", "inset")
            frame.setAttribute(Qt.WA_StyledBackground, True)
            column = QtWidgets.QVBoxLayout(frame)
            column.setContentsMargins(s(8), s(8), s(8), s(8))
            column.setSpacing(s(4))
            column.addWidget(self._label("Paste", "context"))
            #  two to a row: «Replace all» beside three more does not fit a 250 px side panel
            track, self.paste_buttons = self._segments(
                "skeldarPosePaste_", [(mode, animdata.MODE_LABELS[mode])
                                      for mode in animdata.MODES],
                lambda mode: self._remember(PASTE_VAR, mode), columns=2)
            for mode, tip in PASTE_TIPS.items():
                self.paste_buttons[mode].setToolTip(tip)
            column.addWidget(track)
            self.at_current = self._check(
                "At current time", "skeldarPoseAtCurrent",
                "The clip starts at the current frame; off: at its own source frames",
                AT_CURRENT_VAR)
            #  `connect_box`, never `connect`: PySide6 looks a signal's connect up on the
            #  object that owns it, so a `self.connect` attribute broke every
            #  `self.<signal>.connect(...)` of the window («QCheckBox object is not callable»)
            self.connect_box = self._check(
                "Connect", "skeldarPoseConnect",
                "Every pasted channel moved so its first pasted value is the value it shows "
                "at the paste frame", CONNECT_VAR)
            row = QtWidgets.QHBoxLayout()
            row.setSpacing(s(8))
            row.addWidget(self.at_current)
            row.addWidget(self.connect_box)
            row.addStretch(1)
            column.addLayout(row)
            row = QtWidgets.QHBoxLayout()
            row.setSpacing(s(6))
            row.addWidget(self._label("Range", "context"))
            self.range_start = FrameBox("skeldarPoseRangeStart")
            self.range_end = FrameBox("skeldarPoseRangeEnd")
            for box in (self.range_start, self.range_end):
                box.setToolTip("A part of the clip, in its own source frames")
            row.addWidget(self.range_start, 1)
            row.addWidget(self._label("-", "context"))
            row.addWidget(self.range_end, 1)
            column.addLayout(row)
            column.addWidget(self._label("Keys", "context"))
            track, self.keys_buttons = self._segments(
                "skeldarPoseKeys_", KEY_LABELS, lambda key: self._remember(KEYS_VAR, key))
            self.keys_buttons["every"].setToolTip("A key on every frame - exact")
            self.keys_buttons["source"].setToolTip(
                "Keys only where the source had keys - the curves interpolate between them")
            self.in_place = self._check(
                "In place", "skeldarPoseInPlace",
                "Root / Main untouched: the clip's travel is not carried", IN_PLACE_VAR)
            row = QtWidgets.QHBoxLayout()
            row.setSpacing(s(8))
            row.addWidget(track, 1)
            row.addWidget(self.in_place)
            column.addLayout(row)
            return frame

        def _build_save(self):
            s = self.px
            page = QtWidgets.QFrame()
            page.setObjectName("skeldarPoseSavePanel")
            column = QtWidgets.QVBoxLayout(page)
            column.setContentsMargins(s(10), s(10), s(10), s(10))
            column.setSpacing(s(6))
            self.save_heading = self._label("Save pose", "heading")
            column.addWidget(self.save_heading)
            track, self.save_types = self._segments(
                "skeldarPoseSaveType_", SAVE_TYPES,
                lambda kind: self._run(lambda: self._save_type_picked(kind)))
            self.save_types["pose"].setToolTip("The selection at the current frame")
            self.save_types["anim"].setToolTip("The selection over the frames below")
            column.addWidget(track)
            self.save_name = QtWidgets.QLineEdit()
            self.save_name.setObjectName("skeldarPoseSaveName")
            self.save_name.returnPressed.connect(lambda: self._run(self.do_save))
            column.addWidget(self.save_name)
            self.save_folder = self._label("", "note", "skeldarPoseSaveFolder", wrap=True)
            column.addWidget(self.save_folder)
            self.save_character = self._label("", "context", "skeldarPoseSaveCharacter",
                                              wrap=True)
            column.addWidget(self.save_character)

            #  an animation's frames: the slider's highlight, else the playback range, when
            #  Animation is first lit in this panel - and what they take
            self.save_anim = QtWidgets.QWidget()
            self.save_anim.setObjectName("skeldarPoseSaveRange")
            frames = QtWidgets.QVBoxLayout(self.save_anim)
            frames.setContentsMargins(0, 0, 0, 0)
            frames.setSpacing(s(4))
            row = QtWidgets.QHBoxLayout()
            row.setSpacing(s(6))
            row.addWidget(self._label("Frames", "context"))
            self.save_start = FrameBox("skeldarPoseSaveStart")
            self.save_end = FrameBox("skeldarPoseSaveEnd")
            self.save_start.setToolTip("The first frame saved")
            self.save_end.setToolTip("The last frame saved")
            for box in (self.save_start, self.save_end):
                box.valueChanged.connect(lambda _value: self._save_frames_changed())
            row.addWidget(self.save_start, 1)
            row.addWidget(self._label("-", "context"))
            row.addWidget(self.save_end, 1)
            frames.addLayout(row)
            self.save_frames = self._label("", "note", "skeldarPoseSaveFrames", wrap=True)
            frames.addWidget(self.save_frames)
            self.save_anim.setVisible(False)
            column.addWidget(self.save_anim)

            chips = QtWidgets.QGridLayout()
            chips.setSpacing(s(4))
            self.chips = {}
            for index, region in enumerate(_regions()):
                chip = QtWidgets.QPushButton(region)
                chip.setObjectName("skeldarPoseRegion_" + region.replace(" ", ""))
                chip.setProperty("skRole", "chip")
                chip.setCheckable(True)
                chip.clicked.connect(self._chip_touched)
                self.chips[region] = chip
                chips.addWidget(chip, index // 3, index % 3)
            column.addLayout(chips)

            self.save_thumb = self._thumb_label("skeldarPoseSaveThumb")
            column.addWidget(self.save_thumb, 0, Qt.AlignHCenter)
            self.snapshot_button = self._button("Snapshot", "secondary", "camera",
                                                "skeldarPoseSnapshot")
            self.snapshot_button.setToolTip("The viewport at the current frame, again")
            self.snapshot_button.clicked.connect(lambda: self._run(self.take_snapshot))
            column.addWidget(self.snapshot_button)
            column.addStretch(1)
            row = QtWidgets.QHBoxLayout()
            row.setSpacing(s(6))
            self.save_confirm = self._button("Save", "primary", "check", "skeldarPoseSaveOk")
            self.save_confirm.clicked.connect(lambda: self._run(self.do_save))
            self.save_cancel = self._button("Cancel", None, None, "skeldarPoseSaveCancel")
            self.save_cancel.clicked.connect(lambda: self._run(self.close_save))
            row.addWidget(self.save_confirm, 1)
            row.addWidget(self.save_cancel)
            column.addLayout(row)
            return page

        # ------------------------------------------------------ talking

        def say(self, text):
            self.status.setText(text or "")
            try:
                self.scene.say(text or "")
            except Exception:                                # noqa: BLE001
                pass
            return text or ""

        def _run(self, action):
            """`action()` with any failure put on the status line instead of into Qt."""
            try:
                return action()
            except Exception:                                # noqa: BLE001
                traceback.print_exc()
                return self.say(_last_line(traceback.format_exc()))

        def _act(self, action):
            """A scene press: its (ok, text) - or text - on the status line; the text."""
            try:
                result = action()
            except Exception:                                # noqa: BLE001
                traceback.print_exc()
                return self.say(_last_line(traceback.format_exc()))
            if isinstance(result, tuple):
                result = result[-1] if result else ""
            return self.say(result or "")

        # --- the dialogs, one seam each (a modal over the command port blocks Maya: the
        # --- tests and the verify replace them)

        def ask_text(self, title, label, text):
            value, ok = QtWidgets.QInputDialog.getText(self, title, label,
                                                       QtWidgets.QLineEdit.Normal, text)
            return value if ok else None

        def ask_item(self, title, label, items):
            value, ok = QtWidgets.QInputDialog.getItem(self, title, label, items, 0, False)
            return value if ok else None

        def ask_directory(self, title, start):
            return QtWidgets.QFileDialog.getExistingDirectory(self, title, start) or None

        def confirm(self, title, text):
            answer = QtWidgets.QMessageBox.question(self, title, text)
            return answer == QtWidgets.QMessageBox.Yes

        # ------------------------------------------------------ the library

        def set_library(self, root):
            """Show the library at `root` (a folder; made when missing)."""
            self.root = (root or "").replace("\\", "/").rstrip("/")
            self.path_label.setText(self.root)
            self.path_label.setToolTip(self.root)
            self.refresh()

        def choose_library(self):
            """⋮ -> Library folder...: another folder as the library, remembered."""
            chosen = self.ask_directory("Pose Library folder", self.root)
            if not chosen:
                return ""
            chosen = chosen.replace("\\", "/").rstrip("/")
            self.scene.set_library(chosen)
            self.set_library(chosen)
            return self.say("the library is %s" % chosen)

        def refresh(self):
            """The library read again from the disk: the tree, the cards, the pick."""
            if self.root and not os.path.isdir(self.root):
                try:
                    os.makedirs(self.root)
                except OSError as exc:              # an unwritable folder: say it, list nothing
                    self.say("the library folder cannot be made: %s" % exc)
            folders = store.folders(self.root)
            self.all_cards, self.broken = store.cards(self.root)
            if self._folder and self._folder not in folders:
                self._folder = ""
            self._fill_tree(folders)
            self.canvas.forget()            # the thumbnails; a decoded sheet checks its file
            self._repopulate()
            if self.picked and not self._card(self.picked):
                self.unpick()
            elif self.picked:
                self.pick(self.picked)
            if self.broken:
                self.say("%s could not be read: %s" % (
                    _counted(len(self.broken), "card"), ", ".join(self.broken[:3])))
            return self.root

        def folder(self):
            """The catalog the tree has picked, relative ("" the library itself)."""
            return self._folder

        def folder_item(self, rel):
            """The tree's item for catalog `rel` ("" the library), or None."""
            found = [None]

            def walk(item):
                if item.data(0, Qt.UserRole) == rel:
                    found[0] = item
                    return
                for index in range(item.childCount()):
                    if found[0] is None:
                        walk(item.child(index))

            for index in range(self.tree.topLevelItemCount()):
                walk(self.tree.topLevelItem(index))
            return found[0]

        def set_folder(self, rel):
            """Pick catalog `rel` in the tree (and narrow the grid to it)."""
            item = self.folder_item(rel or "")
            if item is None:
                return False
            self.tree.setCurrentItem(item)
            self._folder = rel or ""
            self._repopulate()
            return True

        def _fill_tree(self, folders):
            self._building_tree = True
            try:
                self.tree.clear()
                top = QtWidgets.QTreeWidgetItem(["Library"])
                top.setData(0, Qt.UserRole, "")
                try:
                    top.setIcon(0, maya_hubqt.icon("folder", hubstyle.TOKENS["muted"],
                                                   self.px(14)))
                except Exception:                            # noqa: BLE001
                    pass
                self.tree.addTopLevelItem(top)
                items = {"": top}
                for rel in folders:
                    parent = items.get(rel.rpartition("/")[0], top)
                    item = QtWidgets.QTreeWidgetItem([rel.rpartition("/")[2]])
                    item.setData(0, Qt.UserRole, rel)
                    parent.addChild(item)
                    items[rel] = item
                self.tree.expandAll()
                self.tree.setCurrentItem(items.get(self._folder, top))
            finally:
                self._building_tree = False

        def _tree_picked(self, current, _previous):
            if self._building_tree or current is None:
                return
            self._folder = current.data(0, Qt.UserRole) or ""
            if self._save is not None:
                #  the save panel names the folder the card goes into: it follows the tree
                #  (the final review, S7 - the line kept naming the folder it opened on)
                self.save_folder.setText("in " + folder_text(self._folder))
            self._repopulate()

        def _sorted(self, _index):
            self.scene.set_option(SORT_VAR, self.sort.currentData())
            self._repopulate()

        def _typed(self, _index):
            self.scene.set_option(TYPE_VAR, self.type_filter.currentData())
            self._repopulate()

        def _sized(self, value):
            self.scene.set_option(SIZE_VAR, int(value))
            self.canvas.set_cell(int(value))

        def _repopulate(self):
            shown = shown_cards(self.all_cards, self._folder, self.search.text(),
                                self.sort.currentData(), self.type_filter.currentData())
            empty = ""
            if not shown:
                empty = EMPTY_LIBRARY if not self.all_cards else EMPTY_SEARCH
            if self.canvas.cell != self.size.value():
                self.canvas.set_cell(self.size.value())
            self.canvas.set_cards(shown, empty)

        def cards_shown(self):
            """The paths of the cards the grid shows, in its order."""
            return [card.path for card in self.canvas.cards]

        def _card(self, path):
            return next((card for card in self.all_cards if card.path == path), None)

        # ------------------------------------------------------ the pick

        def pick(self, path):
            """Pick the card at `path`: the grid lights it, the details show it - an animation
            card with its paste options and its preview looping. False for a path the library
            does not hold."""
            card = self._card(path)
            if card is None:
                return False
            self.picked = path
            self.canvas.set_picked(path)
            try:
                self.picked_data = store.read(path)
            except ValueError as exc:
                self.picked_data = None
                self.say(str(exc))
            self.name_label.setText(card.name)
            self.folder_label.setText("in " + folder_text(card.folder))
            self.info.setText("\n".join(look.details(card, self.picked_data)))
            picture = self.canvas.thumb(card.thumbnail, self.thumb_side())
            if picture is not None and not picture.isNull():
                self.thumb.setPixmap(picture)
            else:
                self.thumb.setPixmap(QtGui.QPixmap())
                self.thumb.setText("no thumbnail")
            anim = card.type == "anim"
            self.anim_options.setVisible(anim)
            self._reset_range(card)
            self.apply_button.setToolTip(APPLY_TIPS[anim])
            self.show_targets()
            self._sync_play()
            return True

        def unpick(self):
            self.picked = self.picked_data = None
            self.canvas.set_picked(None)
            self.name_label.setText("")
            self.folder_label.setText("")
            self.info.setText("pick a card")
            self.thumb.setPixmap(QtGui.QPixmap())
            self.thumb.setText("")
            self.anim_options.setVisible(False)
            self._reset_range(None)
            self.show_targets()
            self._sync_play()

        # ------------------------------------------------------ an animation's options

        def _remember(self, var, value):
            """An option the animator changed, written for the next session."""
            try:
                self.scene.set_option(var, value)
            except Exception:                                # noqa: BLE001
                traceback.print_exc()

        def _load_options(self):
            """The options block as the animator left it (`remembered_options`): lit from code,
            so nothing is written back."""
            try:
                opts = remembered_options(lambda name: self.scene.option(name, None))
            except Exception:                                # noqa: BLE001
                traceback.print_exc()
                opts = animdata.Options()
            self.paste_buttons[opts.mode].setChecked(True)
            self.keys_buttons[opts.keys].setChecked(True)
            self.at_current.setChecked(opts.at_current)
            self.connect_box.setChecked(opts.connect)
            self.in_place.setChecked(opts.in_place)

        def _lit(self, buttons, default):
            return next((key for key, button in buttons.items() if button.isChecked()),
                        default)

        def options(self, path=None):
            """The paste options the block shows, as an animation press takes them: {mode,
            at_current, start, end, connect, keys, in_place}. The range is the Range boxes' for
            the PICKED card (`path` None or the picked card's); any other card is pasted whole
            (None, None) - a right-button row over a card not picked."""
            start = end = None
            target = path or self.picked
            if target and target == self.picked and self._range_for is not None \
                    and self._range_for[0] == target:
                start = float(self.range_start.value())
                end = float(self.range_end.value())
            return {"mode": self._lit(self.paste_buttons, "replace"),
                    "at_current": self.at_current.isChecked(), "start": start, "end": end,
                    "connect": self.connect_box.isChecked(),
                    "keys": self._lit(self.keys_buttons, "every"),
                    "in_place": self.in_place.isChecked()}

        def _extra(self, path):
            """What a press of the card at `path` hands the scene beyond a pose's arguments:
            an animation card's `options`; nothing for a pose card - its road unchanged."""
            if path and store.is_anim(path):
                return {"options": self.options(path)}
            return {}

        def _reset_range(self, card):
            """The Range boxes on `card`'s own frames, both held inside them - when ANOTHER
            card is picked (or this one's frames changed): every press on a card picks it, and
            a press on the picked card (to drag it or blend it) keeps what was typed. A pose
            card, or none, leaves them unset."""
            if card is None or card.type != "anim":
                self._range_for = None
                return
            start, end = _whole(card.start), _whole(card.end)
            key = (card.path, start, end)
            if self._range_for == key:
                return
            self._range_for = key
            for box, value in ((self.range_start, start), (self.range_end, end)):
                box.setRange(start, max(start, end))
                box.setValue(value)

        # ------------------------------------------------------ the details' preview

        def _clock_ms(self):
            """Milliseconds on the details' play clock (a seam the tests replace)."""
            return self._play_clock.elapsed()

        def _sync_play(self):
            """The details picture loops the picked animation card's preview while the details
            show (the window visible, no save panel over them) and the card's sheet can be read
            (`canvas.sheet`) - from its first cell when the card is picked anew; anything else
            stops the timer, and the still stays."""
            card = self._card(self.picked) if self.picked else None
            plays = (card is not None and card.type == "anim" and self._save is None
                     and self.isVisible() and self.canvas.sheet(card) is not None)
            if not plays:
                self.play_timer.stop()
                self._play_path = None
                return
            if self._play_path != card.path:
                self._play_path = card.path
                self._play_t0 = self._clock_ms()
            self._play_tick()
            if not self.play_timer.isActive():
                self.play_timer.start()

        def _on_screen(self):
            """Whether the window can be seen (`native_shown`). `isVisible()` is not enough:
            Windows hides a floating window with its minimised Maya and Qt sends no hideEvent
            (measured: isVisible True, isExposed False, Win32 IsWindowVisible False). Asked of
            Windows from `effectiveWinId()` - an int, the native window this widget draws into,
            which (unlike `winId()`) does not make the widget native - and never through a
            wrapper of Maya's own widgets: the first version asked `self.window()
            .windowHandle().isExposed()` on every tick, and right after the control was built
            again PySide handed back the DEAD QWindow wrapper cached at a recycled address
            («Internal C++ object (QWindow) already deleted», in this timer slot - trap 96's
            family; trap 135's says a stale wrapper of a Maya object can crash instead). Off
            Windows, or with no native window to ask (offscreen Qt), it counts as on the
            screen: the details play as they did before. A seam the tests replace."""
            if QtGui.QGuiApplication.platformName() != "windows":
                return True
            user32 = _user32()
            if user32 is None:
                return True
            try:
                hwnd = int(self.effectiveWinId())
            except (RuntimeError, TypeError, ValueError):
                return True
            return native_shown(hwnd, user32)

        def _play_tick(self):
            """The cell of the picked card's preview playing now, in the details picture -
            nothing while the window is off the screen (`_on_screen`): the timer then beats
            every PLAY_HIDDEN_MS until it is back, and plays at `look.PLAY_MS` again, from
            where the clock stands."""
            card = self._card(self._play_path) if self._play_path else None
            if card is None:
                self.play_timer.stop()
                self._play_path = None
                return
            if not self._on_screen():
                if self.play_timer.interval() != PLAY_HIDDEN_MS:
                    self.play_timer.setInterval(PLAY_HIDDEN_MS)
                return
            if self.play_timer.interval() != look.PLAY_MS:
                self.play_timer.setInterval(look.PLAY_MS)
            picture = self.canvas.preview_frame(card, self._clock_ms() - self._play_t0,
                                                self.thumb_side())
            if picture is not None and not picture.isNull():
                self.thumb.setPixmap(picture)

        def hideEvent(self, event):                          # noqa: N802
            QtWidgets.QWidget.hideEvent(self, event)
            self.play_timer.stop()
            self._play_path = None

        def _queue_follow(self, *_args):
            """The scriptJob's callback: the reading coalesced (a marquee fires many) - and
            not at all while the window is hidden (a docked tab behind another): the read waits
            for the window to show (`showEvent`)."""
            try:
                if not q.shiboken.isValid(self):
                    return
                if not self.isVisible():
                    self._stale = True
                    return
                self.follow_timer.start()
            except Exception:                                # noqa: BLE001
                pass

        def showEvent(self, event):                          # noqa: N802
            QtWidgets.QWidget.showEvent(self, event)
            if self._stale:
                self._stale = False
                self.follow_timer.start()
            self._sync_play()

        def _read_targets(self):
            try:
                self._targets = self.scene.apply_targets()
            except Exception:                                # noqa: BLE001
                traceback.print_exc()
                self._targets = (_last_line(traceback.format_exc()), False)
            return self._targets

        def show_targets(self):
            """The target line and the buttons for the card picked, from the LAST reading of the
            selection - a card click reads nothing (the selection is what it was; the
            SelectionChanged job keeps the reading true), read once when there is none yet."""
            card = self._card(self.picked) if self.picked else None
            if card is not None and card.kind == "objects":
                text, ok = OBJECTS_TARGET, True
            elif card is not None:
                text, ok = self._targets if self._targets is not None else self._read_targets()
            else:
                text, ok = "", False
            self.target_line.setText(text)
            self.apply_button.setEnabled(card is not None and bool(ok))
            self.select_button.setEnabled(card is not None)
            self.blend.setEnabled(card is not None)

        def follow(self):
            """The selection read again (the final review: once per selection change, never per
            card click - with a rig's 187 controls selected each read cost 0.8 s, and a click
            stalled before a drag could start): who Apply would pose, when a card is picked -
            none is, nothing reads it until one is - and the save panel's character line (and
            its chips, until the animator touched one)."""
            card = self._card(self.picked) if self.picked else None
            self._targets = None
            if card is not None and card.kind != "objects":
                self._read_targets()
            self.show_targets()
            if self._save is not None:
                try:
                    self.save_character.setText(self.scene.selection_label())
                    if not self._save["touched"]:
                        self._light_chips(self.scene.selection_regions())
                except Exception:                            # noqa: BLE001
                    traceback.print_exc()

        # ------------------------------------------------------ presses

        def _press_apply(self):
            if not self.picked:
                return self.say(NO_PICK)
            return self.apply_card(self.picked)

        def apply_card(self, path, mirror=None):
            """Apply the card at `path` to the selection (`mirror` None: the checkbox) - an
            animation with the options block's options."""
            mirror = self.mirror.isChecked() if mirror is None else bool(mirror)
            extra = self._extra(path)
            return self._act(lambda: self.scene.apply(path, mirror, **extra))

        def _press_select(self):
            if not self.picked:
                return self.say(NO_PICK)
            return self.select_card(self.picked)

        def select_card(self, path):
            extra = self._extra(path)
            return self._act(lambda: self.scene.select_objects(path, **extra))

        # ------------------------------------------------------ drops

        def _inside(self, gx, gy):
            return self.rect().contains(self.mapFromGlobal(QtCore.QPoint(int(gx), int(gy))))

        def folder_at(self, gx, gy):
            """The catalog of the tree item under the global point ("" the library), or None
            off every item."""
            viewport = self.tree.viewport()
            if not self.tree.isVisible():
                return None
            local = viewport.mapFromGlobal(QtCore.QPoint(int(gx), int(gy)))
            if not viewport.rect().contains(local):
                return None
            item = self.tree.itemAt(local)
            return None if item is None else (item.data(0, Qt.UserRole) or "")

        def aim(self, gx, gy, path, snap=None):
            """What a card released at the global point would do (`look.drop_caption`'s
            aim): a folder of the tree, the window (or the hub) itself, else the scene."""
            folder = self.folder_at(gx, gy)
            if folder is not None:
                return {"kind": "folder", "folder": folder}
            if self._inside(gx, gy) or self.scene.over_window(gx, gy):
                return {"kind": "window"}
            card = self._card(path)
            if card is None:
                return {"kind": "none", "text": "the card is gone"}
            if card.kind == "objects":
                return scene_aim("objects", card.label, None)
            if snap is None:
                snap = self.scene.snapshot_scene()
            return scene_aim(card.kind, card.label, self.scene.target(gx, gy, snap))

        def drop_at(self, gx, gy, path, snap=None):
            """The release of a drag of the card at `path` at the global point: onto a
            character, onto the floor (one idle later), into a folder, or nothing. Public, so
            a verify can drive it without a mouse. Answers the status line."""
            aim = self.aim(gx, gy, path, snap)
            kind = aim.get("kind")
            mirror = self.mirror.isChecked()
            extra = self._extra(path)            # an animation's options, read at the release
            if kind == "folder":
                return self._run(lambda: self.move_card(path, aim["folder"]))
            if kind == "character":
                root = aim["root"]
                return self._act(lambda: self.scene.apply_onto(path, root, mirror, **extra))
            if kind == "floor":
                point = aim.get("point")
                card = self._card(path)
                window, scene = self, self.scene

                def later():
                    #  one idle later the window may be gone (closed, rebuilt): the drop
                    #  still happens, and only a standing window shows its line
                    try:
                        result = scene.drop_floor(path, point, mirror, **extra)
                    except Exception:                        # noqa: BLE001
                        traceback.print_exc()
                        result = _last_line(traceback.format_exc())
                    text = result[-1] if isinstance(result, tuple) and result else result
                    try:
                        alive = q.shiboken.isValid(window)
                    except Exception:                        # noqa: BLE001
                        alive = False
                    if alive:
                        window.say(text or "")
                    else:
                        scene.say(text or "")

                defer(later)
                caption = look.drop_caption(card.name if card else "Pose", aim)[0]
                return self.say(caption + " - adding it")
            if kind == "window":
                return self.status.text()
            return self.say(aim.get("text") or look.NO_TARGET)

        # ------------------------------------------------------ the blend

        def blending(self):
            return self._blend is not None

        def _blend_begin(self, path):
            """A blend session for `path`: True when one stands (started now or before)."""
            if self._blend is not None:
                if self._blend["path"] == path:
                    return True
                self.blend_cancel()
            try:
                refusal = self.scene.blend_start(path, self.mirror.isChecked(),
                                                 **self._extra(path))
            except Exception:                                # noqa: BLE001
                traceback.print_exc()
                refusal = _last_line(traceback.format_exc())
            if refusal:
                self.say(refusal)
                return False
            self._blend = dict(path=path)
            try:
                self.grabKeyboard()
            except Exception:                                # noqa: BLE001
                pass
            return True

        def _blend_set(self, alpha):
            try:
                self.scene.blend_set(alpha)
            except Exception:                                # noqa: BLE001
                traceback.print_exc()
                self.say(_last_line(traceback.format_exc()))
            self.blend_label.setText("%d %%" % int(round(alpha * 100)))

        def _blend_end(self):
            self._blend = None
            self.canvas.end_blend()
            try:
                self.releaseKeyboard()
            except Exception:                                # noqa: BLE001
                pass
            self._reset_slider()

        def blend_drag(self, path, dx):
            """One step of the middle drag across the card at `path`, `dx` px from the press:
            the session started on the first step, the blend previewed at `blend_alpha(dx)`.
            The alpha, or None when the blend is refused (the line says why). Public, so the
            gesture can be driven without a mouse."""
            if not self._blend_begin(path):
                return None
            alpha = blend_alpha(dx, self.k)
            self._blend_set(alpha)
            return alpha

        def blend_release(self):
            """The blend keyed where it stands (the middle button or the slider let go)."""
            if self._blend is None:
                return ""
            try:
                text = self.scene.blend_finish()
            except Exception:                                # noqa: BLE001
                traceback.print_exc()
                text = _last_line(traceback.format_exc())
            self._blend_end()
            return self.say(text or "")

        def blend_cancel(self):
            """Esc: every value back as it was before the blend."""
            if self._blend is None:
                self.canvas.end_blend()
                return ""
            try:
                self.scene.blend_cancel()
            except Exception:                                # noqa: BLE001
                traceback.print_exc()
            self._blend_end()
            return self.say(BLEND_CANCELLED)

        def _reset_slider(self):
            try:
                self.blend.blockSignals(True)
                self.blend.setValue(0)
            finally:
                self.blend.blockSignals(False)
            self.blend_label.setText("0 %")

        #  The slider's three drag signals are the whole blend: pressed starts the session,
        #  moved previews, released keys. BlendSlider moves only under a left drag (a groove
        #  press included), so nothing else can key.

        def _slider_pressed(self):
            if self.picked and self._blend_begin(self.picked):
                position = self.blend.sliderPosition()
                if position:            # a style that jumped the handle before the press
                    self._blend_set(position / 100.0)

        def _slider_moved(self, value):
            if self._blend is not None:
                self._blend_set(value / 100.0)

        def _slider_released(self):
            if self._blend is not None:
                self.blend_release()
            else:
                self._reset_slider()

        def _slider_value(self, value):
            """The label follows the handle. It never keys: review finding 1 (2026-10-03)
            measured a wheel notch and the groove's auto-repeat keying here."""
            self.blend_label.setText("%d %%" % value)

        def keyPressEvent(self, event):                      # noqa: N802
            if event.key() == Qt.Key_Escape and self._blend is not None:
                self.blend_cancel()
                return
            QtWidgets.QWidget.keyPressEvent(self, event)

        def lost_release(self):
            """A drag, a middle-drag blend or a slider blend whose button release never came
            (Alt+Tab or a modal dialog mid-drag, a release outside Qt): the drag ended and the
            blend cancelled - every value back, the keyboard given back, nothing keyed - and
            said (`cardgrid.LOST_*`). The slider's own lost release and the window losing the
            focus land here (the final review: left standing, the session swallowed every press
            on the grid, held the keyboard and kept its previews unrecorded)."""
            ended = self.canvas.lost_release()
            if self._blend is not None:
                self.blend_cancel()
                self.say(cardgrid.LOST_BLEND)
                ended = True
            self.blend.drop()
            self._reset_slider()
            return ended

        def changeEvent(self, event):                        # noqa: N802
            QtWidgets.QWidget.changeEvent(self, event)
            if event.type() == QtCore.QEvent.ActivationChange and not self.isActiveWindow() \
                    and (self._blend is not None or self.canvas._drag
                         or self.canvas._mid is not None or self.blend.isSliderDown()):
                self.lost_release()

        # ------------------------------------------------------ save

        def saving(self):
            return self._save is not None

        def _snapshot_path(self):
            return os.path.join(tempfile.gettempdir(), "skeldar_pose_snapshot_%d.jpg"
                                % os.getpid()).replace("\\", "/")

        def _light_chips(self, lit):
            for region, chip in self.chips.items():
                chip.setEnabled(lit is not None)
                chip.setChecked(bool(lit) and region in lit)
            if self._save is not None:
                self._save["initial"] = None if lit is None else list(lit)

        def _chip_touched(self, *_args):
            if self._save is not None:
                self._save["touched"] = True

        def save_type(self):
            """What the save panel saves: "anim" while Animation is lit, else "pose"."""
            return "anim" if self.save_types["anim"].isChecked() else "pose"

        def _save_type_picked(self, kind):
            """A click on Pose or Animation: remembered, and the panel follows."""
            self._remember(SAVE_TYPE_VAR, kind)
            self._light_save_type(kind)
            return self.status.text()

        def _light_save_type(self, kind):
            """The save panel as a `kind` card ("pose" | "anim"): its segment lit, the heading,
            the frames row shown for an animation - Start / End read from the scene
            (`anim_range`) the first time it shows in this panel - and a name the PANEL made
            swapped for the other type's free one (a name the animator typed is theirs)."""
            kind = kind if kind in SAVE_NAMES else "pose"
            self.save_types[kind].setChecked(True)
            self.save_heading.setText("Save animation" if kind == "anim" else "Save pose")
            self.save_anim.setVisible(kind == "anim")
            if self._save is None:
                return
            if kind == "anim" and not self._save["ranged"]:
                self._save["ranged"] = True
                start, end = self.scene.anim_range()
                self.save_start.setValue(_whole(start))
                self.save_end.setValue(_whole(end))
            text = self.save_name.text().strip()
            if not text or text == self._save["auto"]:
                auto = store.unique_name(self.root, self._folder, SAVE_NAMES[kind])
                self.save_name.setText(auto)
                self.save_name.selectAll()
                self._save["auto"] = auto
            self._save_frames_changed()

        def _save_frames_changed(self):
            self.save_frames.setText(save_frames_text(self.save_start.value(),
                                                      self.save_end.value()))

        def open_save(self):
            """+ Save: the save panel in the details' place - lit as the last save was (Pose
            or Animation), a free name in the picked folder, the chips lit from the selection,
            a first snapshot taken."""
            self._save = dict(initial=None, snapshot=self._snapshot_path(), touched=False,
                              auto=None, ranged=False)
            self.save_name.setText("")
            self._light_save_type(self.scene.option(SAVE_TYPE_VAR, "pose"))
            self.save_folder.setText("in " + folder_text(self._folder))
            self.save_character.setText(self.scene.selection_label())
            self._light_chips(self.scene.selection_regions())
            self.save_thumb.setPixmap(QtGui.QPixmap())
            self.side.setCurrentWidget(self.save_page)
            self._sync_play()
            self.take_snapshot()
            self.save_name.setFocus()
            return self.status.text()

        def take_snapshot(self):
            """The thumbnail blasted again from the viewport."""
            if self._save is None:
                return ""
            path = self._save["snapshot"]
            try:
                os.remove(path)
            except OSError:
                pass
            ok, text = self.scene.snapshot(path)
            if ok and os.path.isfile(path):
                picture = QtGui.QPixmap(path)
                self.save_thumb.setPixmap(scaled(picture, self.thumb_side()) or picture)
            else:
                self.save_thumb.setPixmap(QtGui.QPixmap())
                self.save_thumb.setText("no thumbnail")
            return self.say(text)

        def do_save(self):
            """Save: the card written - a pose, or an animation over Start..End; the panel
            closed and the card picked - or the panel kept, the line saying why not."""
            if self._save is None:
                return ""
            kind = self.save_type()
            name = self.save_name.text().strip() or SAVE_NAMES[kind]
            checked = [region for region, chip in self.chips.items() if chip.isChecked()]
            regions = regions_arg(self._save["initial"], checked)
            snapshot = self._save["snapshot"]
            snapshot = snapshot if os.path.isfile(snapshot) else None
            folder = self._folder
            anim = None
            if kind == "anim":
                anim = {"start": self.save_start.value(), "end": self.save_end.value()}
                if anim["end"] < anim["start"]:
                    return self.say(NO_RANGE)
            #  a name a card of either type holds in the folder is refused NOW - asked after
            #  the save had walked the frames and blasted the preview, it lost all of that
            #  (the final review, S7)
            try:
                taken = store.unique_name(self.root, folder, name) != store.safe_name(name)
            except ValueError:
                taken = False
            if taken:
                return self.say(NAME_TAKEN % (store.safe_name(name), folder_text(folder)))
            try:
                if anim is None:
                    path, text = self.scene.save(name, folder, regions, snapshot)
                else:
                    path, text = self.scene.save(name, folder, regions, snapshot, anim=anim)
            except Exception:                                # noqa: BLE001
                traceback.print_exc()
                path, text = None, _last_line(traceback.format_exc())
            if not path:
                return self.say(text)
            self.close_save()
            self.refresh()
            self.pick(path.replace("\\", "/").rstrip("/"))
            return self.say(text)

        def close_save(self):
            """Cancel (or after a save): the details back, the snapshot file gone."""
            if self._save is not None:
                _remove(self._save["snapshot"])
            self._save = None
            self.side.setCurrentWidget(self.details_page)
            self._sync_play()
            return ""

        # ------------------------------------------------------ a card's rows

        def context_actions(self, path):
            """What the right button offers over the card at `path` (rows for
            `maya_hubqt.run_menu`: (label, callable), None a separator); [] off every card. An
            animation card's are a pose card's with «Replace thumbnail and preview» - the still
            AND the preview sheet taken again (`replace_preview`) - in place of «Replace
            thumbnail»."""
            if not path or self._card(path) is None:
                return []
            if store.is_anim(path):
                replace = ("Replace thumbnail and preview",
                           lambda: self._run(lambda: self.replace_preview(path)))
            else:
                replace = ("Replace thumbnail",
                           lambda: self._run(lambda: self.replace_thumbnail(path)))
            return [
                ("Apply", lambda: self.apply_card(path, mirror=False)),
                ("Apply mirrored", lambda: self.apply_card(path, mirror=True)),
                ("Select objects", lambda: self.select_card(path)),
                None,
                ("Rename...", lambda: self._run(lambda: self.rename_card(path))),
                ("Move to...", lambda: self._run(lambda: self.move_card(path))),
                replace,
                ("Update from selection", lambda: self._run(lambda: self.update_card(path))),
                ("Show in Explorer", lambda: self._run(lambda: self.scene.reveal(path))),
                None,
                ("Delete", lambda: self._run(lambda: self.delete_card(path))),
            ]

        def rename_card(self, path):
            card = self._card(path)
            if card is None:
                return self.say(GONE)
            name = self.ask_text("Rename " + _noun(path), "Name", card.name)
            if not name or name.strip() == card.name:
                return ""
            new = store.rename(path, name)
            self.refresh()
            self.pick(new)
            return self.say("renamed to %s" % _name_of(new))

        def move_card(self, path, folder=None):
            """The card into catalog `folder` (asked when None)."""
            card = self._card(path)
            if card is None:
                return self.say(GONE)
            if folder is None:
                choices = ["Library"] + store.folders(self.root)
                picked = self.ask_item("Move " + _noun(path), "Folder", choices)
                if picked is None:
                    return ""
                folder = "" if picked == "Library" else picked
            if card.folder.lower() == (folder or "").lower():
                return self.say("%s is already in %s" % (card.name, folder_text(folder)))
            new = store.move(path, self.root, folder)
            self.refresh()
            if self.picked == path or self.picked is None:
                self.pick(new)
            return self.say("%s moved to %s" % (card.name, folder_text(folder)))

        def replace_thumbnail(self, path):
            image = self._snapshot_path()
            ok, text = self.scene.snapshot(image)
            if not ok or not os.path.isfile(image):
                return self.say(text)
            try:
                store.set_thumbnail(path, image)
            finally:
                try:
                    os.remove(image)
                except OSError:
                    pass
            self.canvas.forget(path)
            self.refresh()
            return self.say("new thumbnail - " + text if text else "new thumbnail")

        def replace_preview(self, path):
            """«Replace thumbnail and preview» on an animation card: the still and the preview
            sheet taken again over the card's own range (`Scene.replace_preview`, in its
            progress window); the grid and the details read both again - the canvas drops the
            card's decoded sheet - even after a failure, which may have written one of them."""
            if self._card(path) is None:
                return self.say(GONE)
            try:
                text = self.scene.replace_preview(path)
            except Exception:                                # noqa: BLE001
                traceback.print_exc()
                text = _last_line(traceback.format_exc())
            self.canvas.forget(path)
            self.refresh()
            return self.say(text or "")

        def update_card(self, path):
            """Update from selection: the card made again from the selection - a pose at the
            current frame, an animation over its OWN range - its still (and preview) kept."""
            card = self._card(path)
            if card is None:
                return self.say(GONE)
            if card.type == "anim":
                question = ("Replace %s with the selection's animation over frames %d-%d? Its "
                            "thumbnail and preview are kept." % (card.name, _whole(card.start),
                                                                 _whole(card.end)))
            else:
                question = ("Replace %s with the selection's pose? Its thumbnail is kept."
                            % card.name)
            if not self.confirm("Update " + _noun(path), question):
                return ""
            text = self._act(lambda: self.scene.update(path))
            self.refresh()
            return text

        def delete_card(self, path):
            card = self._card(path)
            if card is None:
                return self.say(GONE)
            trash = self.scene.trash()
            if not self.confirm("Delete " + _noun(path),
                                "Delete %s? It goes to the trash folder:\n%s"
                                % (card.name, trash)):
                return ""
            store.remove(path, trash)
            if self.picked == path:
                self.unpick()
            self.refresh()
            return self.say("%s moved to the trash (%s)" % (card.name, trash))

        # ------------------------------------------------------ the tree's rows

        def _tree_menu(self, point):
            item = self.tree.itemAt(point)
            rel = (item.data(0, Qt.UserRole) or "") if item is not None else ""
            maya_hubqt.run_menu(self.tree, self.tree.viewport().mapToGlobal(point),
                                self.folder_actions(rel))

        def folder_actions(self, rel):
            """The tree's right-button rows over catalog `rel` ("" the library, which can be
            neither renamed nor deleted - its rows show disabled)."""
            where = self._folder_path(rel)
            rows = [("New folder...", lambda: self._run(lambda: self.new_folder(rel)))]
            if rel:
                rows += [("Rename...", lambda: self._run(lambda: self.rename_folder(rel))),
                         ("Delete", lambda: self._run(lambda: self.delete_folder(rel)))]
            else:
                rows += [("Rename...", None), ("Delete", None)]
            rows += [None, ("Show in Explorer",
                            lambda: self._run(lambda: self.scene.open_path(where)))]
            return rows

        def _folder_path(self, rel):
            """Catalog `rel` on the disk ("" the library folder)."""
            return self.root + ("/" + rel if rel else "")

        def new_folder(self, parent):
            name = self.ask_text("New folder", "Name", "Folder")
            if not name:
                return ""
            rel = store.make_folder(self.root, parent, name)
            self._folder = rel
            self.refresh()
            return self.say("made %s" % folder_text(rel))

        def rename_folder(self, rel):
            name = self.ask_text("Rename folder", "Name", rel.rpartition("/")[2])
            if not name:
                return ""
            new = store.rename_folder(self.root, rel, name)
            current = self._folder
            if current == rel or current.startswith(rel + "/"):
                self._folder = new + current[len(rel):]
            old_path = self._folder_path(rel) + "/"
            if self.picked and self.picked.startswith(old_path):
                self.picked = self._folder_path(new) + "/" + self.picked[len(old_path):]
            self.refresh()
            return self.say("renamed to %s" % folder_text(new))

        def delete_folder(self, rel):
            inside = [card for card in self.all_cards if in_folder(card.folder, rel)]
            trash = self.scene.trash()
            if not self.confirm("Delete folder", "Delete %s and its %s? They go to the trash "
                                "folder:\n%s" % (folder_text(rel),
                                                 _counted(len(inside), "card"), trash)):
                return ""
            store.remove(self._folder_path(rel), trash)
            if self._folder == rel or self._folder.startswith(rel + "/"):
                self._folder = rel.rpartition("/")[0]
            self.refresh()
            return self.say("%s moved to the trash (%s)" % (folder_text(rel), trash))

    _CLASSES.update(PoseWindow=PoseWindow, BlendSlider=BlendSlider, qt=q)
    return _CLASSES


_SHEET = """
#{ROOT} {{ background: {panel}; }}
QScrollArea#skeldarPoseSideScroll, #skeldarPoseSideViewport {{ background: {card};
    border: none; border-radius: {r8}px; }}
QStackedWidget#skeldarPoseSide {{ background: {card}; border-radius: {r8}px; }}
QFrame#skeldarPoseDetails, QFrame#skeldarPoseSavePanel {{ background: {card};
    border-radius: {r8}px; }}
QTreeWidget#{TREE} {{ background: {field}; border: none; border-radius: {r6}px;
    color: {text2}; padding: {p4}px; outline: 0px; }}
QTreeWidget#{TREE}::item {{ padding: {p2}px {p2}px; border-radius: {r4}px; }}
QTreeWidget#{TREE}::item:hover {{ background: {field_hover}; }}
QTreeWidget#{TREE}::item:selected {{ background: {accent_tint}; color: {accent_text}; }}
QScrollArea#{SCROLL} {{ background: {field}; border: none; border-radius: {r6}px; }}
QSplitter::handle {{ background: {panel}; }}
QPushButton[skRole="primary"]:disabled {{ background: {hover}; color: {faint}; }}
QPushButton[skRole="chip"] {{ background: {field}; border: none; border-radius: {r10}px;
    padding: {p3}px {p8}px; color: {muted}; }}
QPushButton[skRole="chip"]:hover {{ color: {text}; }}
QPushButton[skRole="chip"]:checked {{ background: {accent_tint}; color: {accent_text}; }}
QPushButton[skRole="chip"]:disabled {{ color: {faint}; background: {field}; }}
QLabel[skRole="thumb"] {{ background: {field}; border-radius: {r6}px; color: {faint}; }}
QSpinBox {{ background: {field}; border: {b1}px solid {field}; border-radius: {r6}px;
    padding: {p2}px {p6}px; color: {text}; selection-background-color: {accent_tint}; }}
QSpinBox:focus {{ border: {b1}px solid {accent}; }}
"""


def sheet(scale=1.0):
    """The window's stylesheet: the hub's own (its tokens, roles and dropdown arrow) plus the
    rules for what only this window has - its root, the tree, the grid's well, the side panel,
    the chips as buttons, the frame fields (Start / End, Range) as the hub's fields."""
    import maya_hubqt
    import maya_hubstyle as hubstyle
    try:
        arrow = maya_hubqt.icon_file("chevron-down", hubstyle.TOKENS["muted"])
    except Exception:                                        # noqa: BLE001
        arrow = None
    values = dict(hubstyle.TOKENS)
    values.update(ROOT=ROOT, TREE=TREE_NAME, SCROLL=SCROLL_NAME)
    values["b1"] = hubstyle.px(1, scale)
    for n in (2, 3, 4, 6, 8, 10):
        values["p%d" % n] = hubstyle.px(n, scale)
        values["r%d" % n] = hubstyle.px(n, scale)
    text = hubstyle.stylesheet(scale, arrow=arrow) + _SHEET.format(**values).strip() + "\n"
    #  the tree's arrows, the hub's chevrons: with no ::branch rule Maya's own style drew the
    #  open arrow as a white box beside the dark skin, and then a picked folder's arrow on a
    #  blue square - the branch area takes the style's selection unless told (the live run,
    #  2026-10-03)
    try:
        opened = maya_hubqt.icon_file("chevron-down", hubstyle.TOKENS["muted"])
        closed = maya_hubqt.icon_file("chevron-right", hubstyle.TOKENS["muted"])
    except Exception:                                        # noqa: BLE001
        opened = closed = None
    text += ("QTreeWidget#{0} {{ show-decoration-selected: 0; }}\n"
             "QTreeWidget#{0}::branch, QTreeWidget#{0}::branch:selected {{ "
             "background: transparent; border-image: none; }}\n").format(TREE_NAME)
    if opened and closed:
        text += ("QTreeWidget#{0}::branch:has-children:open {{ image: url({1}); }}\n"
                 "QTreeWidget#{0}::branch:has-children:closed {{ image: url({2}); }}\n"
                 ).format(TREE_NAME, opened, closed)
    return text


# ------------------------------------------------------------------ open

def make_window(scene, parent=None, root=None):
    """A window over `scene` - the tests' seam; `build` makes the real one."""
    return _classes()["PoseWindow"](scene, parent, root)


_BUILT_HERE = False      # this module object built the window standing in the control
_WINDOW = []             # [the PoseWindow] while one stands


def live():
    """The window this module object built, while it stands; else None."""
    if not _WINDOW:
        return None
    window = _WINDOW[0]
    try:
        if _classes()["qt"].shiboken.isValid(window):
            return window
    except Exception:                                        # noqa: BLE001
        pass
    del _WINDOW[:]
    return None


def destroy_roots(host):
    """Delete every Pose Library root standing in `host` NOW - found by objectName, never by
    module state: after an install the fresh module does not know the root an older one built
    (trap 102). How many went."""
    q = _classes()["qt"]
    roots = [w for w in host.findChildren(q.QtWidgets.QWidget) if w.objectName() == ROOT]
    for root in roots:
        root.setParent(None)
        q.shiboken.delete(root)
    return len(roots)


def build():
    """The uiScript body: the window inside the workspaceControl."""
    global _BUILT_HERE
    import maya_hubqt
    cmds = _cmds()
    if cmds.workspaceControl(CONTROL, exists=True):
        cmds.setParent(CONTROL)
    if maya_hubqt.qt() is None:
        cmds.text(label="The Pose Library needs PySide (Maya 2025 or newer).")
        _BUILT_HERE = True
        return CONTROL
    host = maya_hubqt.host_widget(CONTROL)
    if host is None:
        return None
    destroy_roots(host)
    q = _classes()["qt"]
    window = make_window(Scene(), host)
    window._host = host             # the wrapper lives as long as the window (trap 96)
    layout = host.layout()
    if layout is None:
        layout = q.QtWidgets.QVBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(window)
    del _WINDOW[:]
    _WINDOW.append(window)
    _BUILT_HERE = True
    return CONTROL


def rebuild():
    """The window built again inside the standing control (where it is docked survives)."""
    if is_open():
        return build()
    return None


def is_open():
    return bool(_cmds().workspaceControl(CONTROL, exists=True))


def show_window():
    """Open the Pose Library (or raise it): the hub card's button and the hotkey row."""
    cmds = _cmds()
    if is_open():
        if not _BUILT_HERE:
            rebuild()
        cmds.workspaceControl(CONTROL, edit=True, restore=True)
    else:
        cmds.workspaceControl(CONTROL, label=LABEL, retain=False, floating=True,
                              initialWidth=INITIAL_WIDTH, initialHeight=INITIAL_HEIGHT,
                              uiScript=uiscript(plugin_root()))


def build_panel():
    """The hub card (Animation): one line and Open Pose Library - the window itself is too big
    for an accordion card."""
    import maya_hubstyle as hubstyle
    cmds = _cmds()
    column = cmds.columnLayout(adjustableColumn=True, rowSpacing=6,
                               columnOffset=("both", hubstyle.pick(0, 8)))
    hubstyle.mark(cmds.text(NOTE_NAME, label=NOTE, align="left"), "note")
    hubstyle.mark(cmds.button(OPEN_BUTTON, label=OPEN_LABEL, height=34,
                              annotation="Cards of a character's bones in folders: saved from "
                                         "the scene, applied onto any rig or skeleton, dragged "
                                         "onto a character or the floor",
                              command=lambda *_a: show_window()),
                  "primary", "books")
    cmds.setParent("..")
    return column
