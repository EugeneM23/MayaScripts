# The second character loses its root motion

*2026-09-02. The animator, after a session with several characters in one
scene: «при импорте анимации в animation bridge анимация root кости
переносится только на первый скелет тоесть на тот у которого нету префикса
на последующие скелеты мы ее не переносим».*

## What happens

Maya will not allow two nodes at world level to share a short name. A DAG
path is what has to be unique, and a top-level node's path *is* its short
name — so when a second character arrives, exactly one of its joints is
renamed: the root.

| how it arrived | the second character's root |
|---|---|
| `cmds.file(i=True)` of `Manny_Skeleton.ma` | `Manny_Skeleton_root` (the file stem, prefixed) |
| FBX, or `duplicate`, or a plain `cmds.rename` | `root2` (a trailing number, incremented until free) |

Everything under it keeps its plain name — `pelvis` is a child of a
different parent, so its path is unique already. That is exactly what makes
a second character usable at all, and `character.rename_note` says so out
loud when the character is added.

`FBXImport -v exmerge` matches bone names **inside the FBX plugin**.
`other_skeletons_held` frees the plain names the *other* characters hold, so
the clip's `pelvis` reaches the target's `pelvis` — but the target's own
root still wears its decorated name, and the clip's `root` matches nothing
at all. Measured on the UE4 mannequin: **67 of 68 bones animated**, the
missing one being the root.

Root motion is the character's whole travel through the world. So the
second character plays the clip on the spot while the first one walks.

The tool is not silent about it — `stale_line` prints "1 bone(s) not in the
clip, now unanimated: `Manny_Skeleton_root`" — but that is one clause in a
status line, describing a bone the animator never renamed and does not
think of as decorated.

**This was known and written down as a cost rather than a bug.** CLAUDE.md
and `2026-09-01-character-dropdown-design.md` both record the 67-of-68
measurement under "what flat costs, stated rather than wished away". The
animator's report is the correction: it is not a cost, it is the feature
failing on every character after the first.

## The same name goes out

`animexport.export_hierarchy` selects the root and writes its hierarchy, so
the FBX handed to Unreal carries `Manny_Skeleton_root` too, and the UE
skeleton has no such bone. Both export roads run through that one function
— Export to uasset, the Perforce road, and the plain save-as.

Honesty about the evidence: the import side is measured, the export side is
reasoning. `2026-09-01-uasset-export-design.md` records that "UE clips need
a bone called `root`" was raised as a theory during the fractional-range
hunt and did not explain *that* failure — it was never shown to be harmless,
it was shown not to be the cause of a different bug. The export side is
therefore fixed on the same principle and **proved live**, not assumed.

## The fix: the root wears its plain name for the length of the transfer

A temporary rename is the only lever that reaches inside the FBX plugin's
own name matching. `other_skeletons_held` already establishes the pattern
for the other characters; this applies it to the target's own root.

### The rule for the name is pure, and it refuses to guess

`plain_root_name(root_short, bone_shorts)` answers `"root"` when the root's
name is a decorated form of it, and `""` otherwise. Decorated **relative to
its own skeleton**, which is the exact statement of the mechanism — only the
top node collides, everything below keeps its plain name:

1. strip a trailing run of digits (`root2` → `root`, `Manny_Skeleton_root1`
   → `Manny_Skeleton_root`);
2. accept `root`, or `<prefix>_root` where **no other bone of that skeleton
   wears `<prefix>`**.

The second half of rule 2 is what keeps a hierarchy topped by a real UE bone
out. `ik_foot_root` ends with `_root`, but its own children are `ik_foot_l`
and `ik_foot_r` — they wear the prefix, so the name is not a decoration and
the joint is left alone. A root that is genuinely called something else
(`Bip001`, a prop chain, a non-UE rig) is left alone too. No guessing: the
function answers `""` and the behaviour is exactly today's.

`root` is not a new assumption. `choose_target_root` already falls back to
"the skeleton called `root`", and `other_skeletons_held`'s reasoning already
rests on "`root` is a bone in every UE clip". This names the constant.

### The lever is one context manager, used by both directions

`target_root_plain(target_root)` yields the name the root actually took, or
`""` when nothing was renamed:

- **free the name** — whatever currently answers to `root` is renamed aside
  with the same `rpHold_` prefix. On the import path `other_skeletons_held`
  has already taken it away, so there is nothing to displace; on the export
  path the first character still holds it.
- **rename the root**, and check the name Maya actually gave it. Maya
  uniquifies silently, so a rename that lands on `root1` is a failure, not a
  success — it is undone at once and the manager yields `""`.
- **restore in `finally`**, ours first (which frees the name again), then
  whatever was displaced.

Everything is resolved through **UUIDs**: renaming a root invalidates the
path of every joint beneath it, and a stale path makes `cmds.ls(path,
uuid=True)` answer `[]`, which a loop reads as "gone" and passes over
(traps 16 and 48 — the second one cost a live run on this very mechanism).

A wrong answer costs nothing. The rename either matches the clip's root and
the motion transfers, or it matches nothing and the result is exactly
today's — and either way the name is put back.

### Where it plugs in

**Import** — nested inside `other_skeletons_held`, around the `FBXImport`
call only. Both managers exit before the delta is measured, so
`target_joints`, `stale` and `_keyed_joints` see the restored paths.

**Export** — inside `export_hierarchy`, so all three export roads get it
from one place. The selection is rebuilt from the root's UUID *after* the
rename, because the path captured before it is stale. `joints` and `times`
are read before the rename and are unaffected.

### The status says it out loud

`root_note(actual, used)` — "`Manny_Skeleton_root` treated as `root` so the
root motion transfers". Without it the next person finds one name in the
outliner and a different one in the FBX and has nothing to go on.

## Deliberately not done

**Importing characters into a group** so the root keeps its plain name
(`|Manny_Skeleton|root` is a unique path) would fix the cause rather than
the symptom — but only for characters added from then on, leaving every
saved scene broken, and it reverses the flat shape the animator asked for on
2026-09-01 («нужно сделать однородно»).

**Reading the clip's bone names** out of the FBX before importing. The
binary format is not parseable here, and a second `add`-mode import to
discover the names would mutate the scene twice.

**Generalising to every decorated bone.** Only the top node ever collides —
measured. A rule that rewrote other bones' names would be risk without a
case.

## Proof

Unit tests for the two pure functions and the manager's decision table.

Live: `verify_uebridge_root_name.py`, run through the bridge in the
animator's own scene. It builds **two throwaway UE-schema skeletons of its
own** (never the animator's characters), so the second one's root is
decorated for real by Maya rather than by the test, imports a clip onto it
and asserts the root's world matrix moves with the clip — the gate the whole
change exists for. Then the export direction: export the second character
and assert the FBX names its root `root`, and that the scene is left exactly
as it was found.
