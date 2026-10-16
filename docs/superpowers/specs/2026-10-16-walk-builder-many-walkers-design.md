# Walk Builder: several walkers at once (2026-10-16)

The animator: «В walk builder я должен иметь возможность обрабатывать сразу несколько циклов на разных
персонажах. Я думаю что кнопочка pick должна добавлять персонажа в список. Только для каждого цикла у нас
конечно же должна быть своя средняя поза, если обобщить то все настройки работают одинаково для всех циклов
но каждый цикл уникальный.»

Asked, all three the recommendation:
- **the knobs are shared** by every walker in the list (a slider moved re-keys them all, each on its own cycle);
- **the pose card is shared** (the pose well's active card, its share and parts);
- **the mean pose belongs to the cycle** (as it already does: the correction file beside the walk), so two
  walkers on one card share it; Rig pose keeps one Manny rig per cycle.

## The list

- **The list is the scene's walked skeletons**: every top joint carrying the `skeldarWalk` marker (v2) in the
  active tab, unless its memo says `"listed": false`. Nothing else stores it, so it survives a save, a reopen and
  an undo, and an older scene's walked skeletons are listed as they stand (`scene.walkers()`).
- **Pick** puts the walk well's active cycle on the selected skeleton and lists it (`listed` true); pressed on a
  walker already listed it changes that walker's cycle. Several skeletons selected: each is picked.
- **The list in the card**, under Pick: a `textScrollList` `skeldarWalkList`, one row a walker -
  «<character> - <cycle>», the character the walker's character group without `_Character`, else its
  namespace, else its short name. A click selects those skeletons in the scene; Delete key or the right button
  > Remove from list unlists (the keys stay; Pick lists it again); right button > Take its settings puts the
  walker's stored knobs, pose card and parts into the card (they then reach every walker on the next re-key).
- **Selecting a listed walker** makes its cycle the walk well's active card (no re-key) and the subtitle names
  it. Selecting a walked skeleton no longer reads its knobs into the card: the card's knobs are everyone's.

## Re-keying

- A released knob, a pose card taken / cleared / removed, a part chip, In place, Reset: **every listed walker**
  keyed again with the card's knobs, its own cycle, the shared pose (`panel.rekey_all`). The line: «3 walkers
  keyed: Manny - asd, Creep - dw, ... | 2.4 s»; a walker that fails is named with its refusal, the others still
  keyed.
- **Tempo** is the one knob in frames of a cycle: the card shows it for the active cycle, and each walker takes
  it as a ratio of its own cycle (`tempo_i = round(tempo * P_i / P_active)`, at least 4). Activating another
  cycle in the walk well rescales the card's tempo to keep the ratio and re-keys nobody.
- Fix posture and the Rig pose's Update / Reset re-key the walkers on THAT cycle only.

## Rig pose, one rig per cycle

- `meanrig.find(walk)` - the mean pose rig of that cycle; `rigs()` every one.
- **Create**: the active cycle's rig, added beside the first walker on that cycle (else the first walker, else
  the origin); a cycle with a rig already standing is posed again.
- **Update**: every mean pose rig read; each cycle whose rig moved gets its correction; the walkers on those
  cycles keyed again (unrecorded).
- **Reset**: the active cycle's correction dropped, its rig back in the mean pose, its walkers keyed again.
- **Delete**: the active cycle's rig (or the only one when the active cycle has none).
- The bones cache keys by the rig's Main (already) - several rigs read in turn.

## Kept

`scene._state()["target"]` stays as "the walker last keyed" for code that still asks (the hotkey's apply with the
card closed goes through Pick). The marker's layout is unchanged but for `listed`.

## Testing

Unit tests on the card's fake cmds: Pick lists, several selected, a knob re-keys every walker each with its own
cycle and its tempo ratio, Remove from list, Take its settings, selecting a walker activates its cycle, the walk
well activation keeps the ratio; meanrig per cycle. Headless verify in mayapy: two Manny skeletons and a Creep
skeleton on two cycles, a knob re-keying all three, the mean pose of one cycle reaching only its walkers.

## Addendum: each skeleton's OWN cycle (the same day)

The first push read the request wrong: Pick put the walk well's one card on every selected skeleton. The animator:
«pick ко всем скелетам в сцене применяет один и тот же цикл а он должен брать цикл у каждого скелета и обрабатывать
его отдельно применяя одни и те же настройки. Это нужно для обработки массивов анимаций». Asked, both the
recommendation: the result goes **onto the same skeleton**, and each skeleton's source is kept **in the scene, on
the skeleton**.

- **Pick** (`panel.walk_for`): a skeleton already walked keeps the cycle it walks; else one that keeps a source uses
  it; else one with keys has them read as its cycle (`scene.capture_source`: `read_clip`, Save's rule) and kept on
  its top joint (`skeldarWalkSource`, the walk file's gzip bytes in base64 - it travels with the scene); a skeleton
  with no keys takes the walk well's card. Every source is read before anything is keyed.
- **The own cycle's name** is `own:` + a digest of those bytes (`scene.own_name`); it is read into a walk file under
  `<walks>/own/` (written again from the scene whenever it is missing - `_sync_own`), so load_walk, Fix posture and
  the mean pose correction work on it as on any walk. The correction lives beside that file, not in the scene.
- **Tempo**: with no card active the first own cycle becomes the active one, so each cycle keeps its own tempo
  until the knob moves.
- **The list's right button** adds Use the active walk card, Use its own cycle, and **Restore the original keys**
  (`scene.restore_source`: every joint keyed back from the kept cycle on every frame, the marker and the source
  removed, one undo step).
