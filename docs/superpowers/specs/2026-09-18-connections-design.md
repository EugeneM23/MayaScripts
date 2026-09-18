# Connections: the hands on the weapon, and off it, on the AdvancedSkeleton rig

**Date:** 2026-09-18
**Ask:** «Нужно сделать вкладку connections, в которой мы сможем привязывать
и отвязывать руки к оружию. Привязку и отвязку реализуем при помощи OverRig,
будем перепекать анимацию (важно, чтобы мы не ломали иерархию нашего рига)».

## What it replaces

`maya_scenesetup/connect.py` (Connect Arms To Weapon, 2026-08-21) did this
for the OverRig picker rig: it hung the IK end groups under the weapon's
geometry with `apply_Parent_in`. That module stays (the picker is behind a
flag) and is not touched. The rig today is the AdvancedSkeleton one, whose
IK hand controls `IKArm_R` / `IKArm_L` live at
`CustomOrientIKArm_*|IKExtraArm_*|IKArm_*` inside `MotionSystem`, and that
place is load-bearing: the solver, the `followMain`/`followRoot` switches
and the FK/IK align all read it. Re-parenting them is exactly "breaking the
rig hierarchy".

## The split (the design in one paragraph)

**The weapon is re-baked by OverRig; the hands are constrained and never
re-parented.** Connect lifts the weapon from the hand bone to world through
`apply_Parent_out` (its world track baked onto its own channels — measured
2026-09-18 in the standalone probe's live counterpart: drift 0.000000 at a
mid frame) and parent-constrains each chosen IK control to the weapon's
geometry with `maintainOffset`, the control's own keys cut first. Disconnect
bakes the controls over the range with `cmds.bakeResults`, deletes only our
constraints, and hangs the weapon back under the hand through
`apply_Parent_in`, so whatever the animator did with it out in the world
survives in the hand's space. Nothing in the rig's DAG moves.

Why not OverRig for the hands too: OverRig's rebake procs re-parent; that is
what they are. Why not `cmds` for the weapon too: the animator asked for
OverRig's rebake by name, the weapon is geometry under a bone and not rig,
and `parent_out`/`parent_in` are the procs the earlier Connect already
proved live (zero drift, round trip exact).

## Rules, each with a reason

- **Which hands**: two checkboxes, Right hand and Left hand, both on by
  default, remembered in `skeldarConnections_right/left`. A longsword and a
  spear are two-handed, a dagger is not; the animator ticks.
- **The grip is the CURRENT frame's.** `maintainOffset` captures the hand's
  offset from the weapon on the frame the animator is looking at, and the
  status says which frame. The control's keys are cut BEFORE the constraint
  (trap 37: keying a constrained channel splices a pairBlend) and its
  current values are written back after the cut (trap 58: `cutKey` leaves a
  channel wherever the DG last evaluated), read off the curves with
  `keyframe -eval`.
- **The arm goes to IK**: `FKIKArm_*.FKIKBlend` is set to 10. A blend that
  is KEYED at anything else is refused by name — that is the animator's own
  switching and overriding it silently would change their take. The poles
  are untouched (the elbow keeps answering to the body).
- **Identity by attribute**: every constraint we make carries
  `skeldarHandLink` = the weapon's UUID. `connected_sides` asks for it, so
  a constraint of somebody else's on the same control is neither counted
  nor deleted, and nothing is found by name.
- **Refusals before anything moves**: no rig (the `maya_rigs` refusal, by
  name when several); no weapon in the hand («Weapons > Add first»);
  already connected; a `MoCapConstraints` holder standing (a retarget in
  progress); a keyed blend; and OverRig's `mel_gate` (not loaded, or a
  time-slider highlight — trap 36 — which `apply_Parent_out` would bake
  across).
- **The retarget refuses a connected rig** (`maya_rig_retarget.hands_connected`,
  both in `run_retarget` and in `bake`): its `connect` would skip the
  constrained IK controls as foreign and the take would arrive with the
  hands standing still; its bake would lift the weapon link under them.
  Lazy guarded import, so the retarget keeps working without Scene Setup.
- **Weapons > Add / Remove already refuse a linked weapon**; the Weapons
  panel finds the weapon out in world through `bonedrive.driving_weapon`
  (the constraint on `weapon_r` targets the node and survives the move),
  which is the one line changed there.
- **One undo chunk per press.**

## The section

`maya_scenesetup/connections.py`, a row in `maya_hub.SECTIONS` after
Weapons: a header («Manny_Rig: LongSwordMesh in the hand, hands free» /
«… right hand, left hand connected to LongSwordMesh»), the two checkboxes,
Connect, Disconnect, a status line. **No shelf button and no icon** (the
2026-09-17 rule). Hotkey rows `window.connections`, `connections.connect`,
`connections.disconnect`.

## Addendum — the switching model (2026-09-18, later the same day)

The animator, after using Connect/Disconnect: «нужна какая-то гибкая
система переключений: обе руки к мечу, руки по отдельности, меч к левой
или правой руке, меч к правой а левую руку к мечу». Two checkboxes and
Connect/Disconnect cannot say "the weapon in the LEFT hand" at all, so the
section was rebuilt on a model rather than on two buttons.

**Three nodes, two links.** Left hand — weapon — right hand. Each link is
`holds` (the weapon hangs in this hand; at most one hand), `follows` (the
hand's IK control rides the weapon) or nothing. A *scheme* is
`{"L": state, "R": state}`; every case the animator named is one, and so
are "weapon in the left hand, right free" and "weapon in world, nobody".

**The panel is three parent rows, Apply per row, Apply all** (the
animator's shape after the arrow row read unclear: «заголовок Hand_R,
Hand_L, Weapon, напротив каждого выпадающий список с родителем, напротив
каждого кнопка apply, внизу общая Apply all»):

    Hand_R   [ Free | Weapon ]           [Apply]
    Hand_L   [ Free | Weapon ]           [Apply]
    Weapon   [ World | Hand_R | Hand_L ] [Apply]
                                         [ Apply all ]

A hand's parent is Free or Weapon (it follows); the weapon's is World or
the hand it hangs in (`menus_from_scheme` / `scheme_from_menus`, pure and
round-tripping). A pick that would make a cycle fixes the other menu and
says so (`resolve_menus`, pure): the weapon put into Hand_R sets Hand_R to
Free; Hand_R set to Weapon while the weapon hangs in it sets Weapon to
World. Picking touches nothing in the scene. A row's **Apply** changes that
one link (`wanted_for_row`, pure — the holder set Free puts the weapon in
world; the weapon moved to the other hand frees the old one); **Apply all**
brings the scene to all three menus. After any Apply the menus are re-read
from the scene (`read_scheme`), so they always show what IS. Apply and not
pick-to-apply, because a transition is an OverRig re-bake (seconds on a
long clip). The arrow design that preceded this stood for an hour and is
not in the code.

**Apply does only the difference** (`plan`, pure, in this order): hands
that stop following are released (baked, our constraint deleted); the
weapon moves — lifted to world out of the holding hand (`apply_Parent_out`),
then hung in the new holding hand (`apply_Parent_in` under its hand bone);
hands that start following are hung with the current frame's grip. Order
matters: a hand must not be hung on a weapon that is about to move under
it with a stale offset.

**The drive bone follows the holding hand** — the animator's ruling: in
the right hand the weapon drives `weapon_r`, in the left `weapon_l`, in
world it keeps the bone it drove last. On a bone change the old bone is
`bonedrive.unlink`ed (baked back) and the new one parent-constrained to the
weapon with **no offset**, so the export socket sits ON the weapon wherever
the animator put it — Weapons > Add's grip-inverse offset is the right
thing when the weapon is PLACED on the bone, not when it comes to the hand
from the world with its own track.

`connect()` and `disconnect()` stay as the hotkeys' two schemes: both hands
follow a weapon in world; nobody follows and the weapon in the hand whose
bone it drives.

## Addendum 2 — a following hand rides a PROXY, and the proxy is animatable (2026-09-18, evening)

The animator, after using the section: «сейчас мы теряем возможность
анимировать объект, который был приконстрейнен. Давай через прокси-локатор,
который будем размещать внутри родителя, перепечём на него анимацию и уже
потом констрейним наш объект к прокси. Так мы сможем и анимировать, и
сохраним уже готовую анимацию».

Two things the direct constraint cost. A constrained IK control cannot be
keyed (a key splices a pairBlend — trap 37), so a hand on the weapon was
frozen for the animator. And `maintainOffset` from ONE frame flattened
whatever the hand did against the weapon over the clip into that frame's
grip — the take was changed, not kept.

**The follow now goes through a locator inside the weapon.**
`handProxy_<side>` (in the rig's namespace, marked `skeldarHandProxy` =
`<namespace>:<side>`) is created and parented under the weapon's geometry
(`_make_proxy` — the one `cmds.parent` in the module, and it parents our
own locator; the controls still never move in the DAG). The hand's world
track is baked onto the proxy over the range (`_bake_onto`: a temporary
no-offset `parentConstraint` control → proxy, `bakeResults`, the temp
deleted) — in the weapon's space that is exactly the hand's motion against
the weapon, frame for frame, so the take is kept whole. Channels that came
out constant are un-keyed (`is_constant`, pure; the value stays), so a
rigidly held hand leaves a proxy with plain values and the animator's own
keys start from nothing. Then the control's keys are cut, its current
values written back, and it is parent-constrained to the proxy with NO
offset; our constraint carries the proxy's UUID. **From then on the proxy
is what the animator keys**: a key on it moves the hand against the
weapon, while the weapon still carries both.

Release bakes the control as before, deletes our constraint, and deletes
the proxy (`proxy_of`, by attribute). A proxy rides the weapon through
`apply_Parent_in`/`_out` as a DAG child — its local keys are in the
weapon's space and OverRig re-bakes only the weapon. The bake span is the
playback range ∪ the weapon's keys ∪ the controls' keys.

Verify gates added: the proxy is a locator under the weapon's geometry;
a still hand's proxy carries no keys; a +5 key on the proxy moves the hand
5.0 with the weapon unmoved; the released hand's proxy is gone while the
other's stays.

## Addendum 3 — five fixes after first use, and BakeAcross (2026-09-18, night)

The animator, after using the proxies: «после бейка нужно удалять прокси
локаторы; если бейкаем на прокси, приконстрейненный контрол давай будем
прятать; локатор на 40 % больше; весь текст описания уберём из вкладки;
отдельная кнопка BakeAcross — все выделенные объекты привязываются к
последнему выделенному при помощи наших прокси-локаторов». And: «риг в
сцене для тебя, можешь тестировать на нём».

1. **The proxies did survive a bake — a real bug.** `proxy_of` looked them
   up with `cmds.ls("*.skeldarHandProxy")`, and a `*` pattern does not
   cross a namespace colon: `Manny_Rig:handProxy_L` was never found, so
   the release deleted the constraint and left the locator. Every lookup is
   by attribute now (`proxies()` walks the scene's locators), a test pins
   that no `cmds.ls("*.` remains, and `sweep_orphans()` — proxies no
   constraint of ours points at — runs at the front of every Apply and
   BakeAcross (never from a refresh). The animator's scene held two such
   orphans; the verify swept them.
2. **The rider is hidden while it rides** (`visibility` off, the previous
   value kept on our constraint as `skeldarHiddenVis`, put back on
   release; best effort — a locked or driven visibility is skipped).
3. `PROXY_SCALE` 6.0 → **8.4**.
4. The description paragraph left the section: header, three rows, Apply
   all, the BakeAcross row, status.
5. **BakeAcross**: every selected object rides the LAST selected one
   through a proxy of its own (`attach_to_proxy`, the same machinery the
   hands use, now generic: `_make_proxy` / `_bake_onto` /
   `detach_from_proxy`). `across_plan` (pure) takes the parent as the last
   selected and refuses fewer than two, a cycle (a child above the parent)
   and a child already inside the parent; a child already riding a proxy
   is refused («Release it first»). **Release** beside it bakes the
   selected riders (or the riders of selected proxies) where their proxies
   carried them, deletes constraints and proxies, and shows the objects
   again. `_transforms` resolves the selection to LONG paths first — the
   cycle check is a path-prefix test and a short name read as outside
   everything (measured: a cube attached to its own proxy).

**Proof, live on the animator's own rig** (their leave):
`verify_connections.py` **39 of 39 gates, 2026-09-18**, borrowing the
scene's sole rig (test keys cut and blends restored afterwards; the
weapon bones' constraints protected from the cleanup diff, and on a
borrowed rig only the sandbox nodes and our proxies are deleted — a
blanket UUID diff once took the sword's link with the baked curves).
Measured: the hand's track through a follow 0.000000; a proxy key moving
the IK control exactly as far as the proxy moved in world (the weapon is
scaled, so +5 local was 3.753 world for both); a 10 cm weapon nudge moving
both IK controls 10.000; the hand BONE following only as far as the arm
reaches (5.658 of a 10 nudge at the animator's grip — an IK limit, so the
gates measure controls); the weapon into the left hand driving `weapon_l`
to 0.000000; BakeAcross carrying a keyed locator's track to 0.000000 and a
still one's proxy with no keys; Release restoring both and their
visibility. Two gate lessons: a still hand against a MOVING weapon has a
keyed proxy (the relative track is what is kept), and a fixture that picks
"the first proxy in the scene" picks somebody else's.

## Testing

Unit: the pure halves (`hands_to_connect`, `blend_refusal`, `union_range`,
the messages, `header_text`), the panel on `FakeUiCmds`, and the boundaries
read off the source — no `cmds.parent(` anywhere (the hands are never
re-parented), `parent_out`/`parent_in`/`parentConstraint`/`bakeResults`
present, no `mel.eval`, the marker asked for by attribute, the retarget
refusing a connected rig, no shelf button.

Live (`docs/superpowers/plans/verify_connections.py`, over the command port
in the animator's Maya, which today holds NO rig — OverRig's procs need the
time slider and die in mayapy with «Cannot convert data of type int to
type float[]», measured 2026-09-18): a throwaway `Manny_Rig` added, the
sword attached, the IK hand keyed; Connect → the weapon in world with its
track intact, the IK control constrained by our constraint, the hand's
world matrix unchanged over the range, the rig's DAG unchanged (the
control's path is the same); a weapon nudge moves the hand; Disconnect →
the controls keyed, our constraint gone, the weapon back under the hand
with zero drift, the nudge kept; Retarget refused while connected; every
node the run created deleted afterwards.
