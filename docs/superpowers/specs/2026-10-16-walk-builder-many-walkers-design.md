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

## Addendum 2: choosing a cycle puts it on at once again (the same day)

The animator, after the second push: «Мы сломали старый функционал теперь при выборе цикла цикл сильно
ускоряется». Reproduced headless: a skeleton walked with asd (31 frames), dw (90 frames) chosen in the walk well,
Pick - the skeleton kept asd, a cycle three times as fast as the one chosen. Choosing a cycle no longer put it on,
and Pick kept whatever card a skeleton walked.

- **Choosing a walk card** (drop, click, Use in Walk Builder) puts it on at once, as before: the selected walkers
  that walk a card - none selected, every walker on a card - are keyed with it, at the card's own tempo
  (`panel.card_walkers`). A walker on its own cycle is never changed by a card.
- **Pick** (`walk_for`): a skeleton on its own cycle keeps it; one that walks a card takes the active card; one not
  walked yet has its own keys read as its cycle, else (no keys) takes the active card.
- The tempo is the chosen cycle's own frames again; only selecting a walker on a card (which makes that card the
  active one) keeps the tempo's ratio. Selecting a walker on its own cycle leaves the walk well alone.

## Addendum 3: the card comes first (the same day)

After the third push: «Сейчас карточка анимации цикла не применяется вообще». The skeletons the second build had
read as their own cycles (they carried keys) were left alone by every card choice and every Pick. Asked how to tell
the two uses apart, the animator chose **«Карточка важнее»**:

- **Pick puts the walk well's active card on every selected skeleton**, own-cycle walkers included. A skeleton not
  walked yet that carries keys has them kept first (`_keep_original`, best effort: a clip that is no cycle is simply
  not kept), so Use its own cycle and Restore the original keys still bring them back.
- **Each on its own animation** is Pick's right button (`press_apply_own`), and what Pick does when there is no
  card at all. The list's right button > Use its own cycle reads a walker's keys as its cycle when nothing was kept.
- **Choosing a card** keys the selected walkers whatever they walk; nothing selected, every walker on a card (own
  cycles keep theirs).
- Found on the way: `cmds.createNode` selects what it makes, so every Pick left an animCurve selected and the next
  card choice reached nobody. Curves are made with `skipSelect=True`, and the card reads the selection as walkers
  only - anything else selected counts as nothing selected.

## Addendum 4: an empty well, a clip loaded onto a walker, a card taken out, the tempo (the same day)

The animator, after the fourth push: «загрузил в сцену анимацию на скелет, нажал пик и у меня при пустых карточках
подгрузилась ... анимация которую я вообще не ожидал»; then «если я удаляю карточку цикла то анимация не возвращается
на ту что была выбрана на скелете» and «после применения карточки (Creep_Drunk) анимация ломается».

- **An empty walk well is no walk.** `chosen_walk` fell back to the first saved walk FILE in the walks folder
  (alphabetically `Creep_Drunk`), so Pick put a walk nobody chose on the skeleton. The fallback is gone; with no card
  Pick reads each skeleton's own animation. A walker's own cycle made active is not a card either (`_active_card`).
- **A clip loaded onto a walker is new animation.** `apply` keeps a digest of the base-layer keys it wrote on the
  marker (`scene.keys_print`, through `base_input`, so animation-layer corrections do not count); `keys_changed` tells
  a clip put on afterwards. Pick then drops the old kept cycle and reads the new keys; a knob skips that walker and
  says so (it would wipe the new clip).
- **Taking a card out of the well** (`remove_walk_card`, `remove_all_walk_cards`) puts the walkers on it back on their
  own animation (`_back_to_own`); one that kept nothing keeps the card's keys and is named.
- **The tempo knows which cycle it counts** (`tempo_walk`, optionVar `skeldarWalk_tempoWalk`, set when a cycle is
  chosen, the tempo slider moves, Reset, Take its settings). The active cycle could change some other way (a card
  gone, the empty-well fallback) and the next Pick read a tempo meant for another cycle: Creep_Drunk (90 frames)
  squeezed into asd's 31 - the likely «broken» Creep_Drunk.
