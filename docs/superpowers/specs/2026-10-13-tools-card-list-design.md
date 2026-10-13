# The Tools card as a list with explanations (variant C)

2026-10-13. The animator: «Давай улучшим интерфейс вкладки tools. Нужно сделать все более понятно,
разложить по разделам. Все кнопки не должны быть такими оранжевыми, нужно улучшить дизайн. Сделай
несколько макетов и я выберу». Four mockups were shown (A tabs, B coloured blocks with tiles, C a list
with explanations and collapsible sections, D the current order restyled); they chose **C**.

This replaces the 2026-10-12 rule «все кнопочки одинаково важные» (every button orange).

## The card, top down

- The subtitle (unchanged: «3 knots in the scene, 1 pivot waiting»).
- **Knots** - a subsection head (hint «drive with a locator»), its body:
  - tool rows: **Knot** «object follows a locator», **Offset** «knot at your own pivot», **Orient**
    «carries rotation only», **Local ×2** «double knot, own axes», **World ×2** «double knot, world
    axes», **Aim** «points at a target»;
  - Aim moved here from its own subsection: it is a knot kind (`aim`) with attach, a range,
    Bake and Remove like the others;
  - Rotate order `[Object | XYZ | XZY]` moved here from the bottom: it is the order of NEW knots.
- **Parent** - head (hint «motion kept»), body:
  - tool rows: **Inside** «under the last selected», **To world** «out to world level», **Swap**
    «child takes parent's place», **Across** «rides the last selected»;
  - a caption «Across, pair by pair», then `Objects n | Targets n | ⇄` and
    `Rotate | Translate | Pairs` (the old Multiple across; its press reads «Pairs»).
- **Overlap** - head (hint «on a new layer»), body:
  - Softness, Lag, fr and Easing side by side: a row of their names over a row of their fields;
  - the four chips two to a row (Hierarchy, Cycled, Total lag, Keep edges);
  - the tool row **Overlap** «trail onto a new layer».
- **Selected knots** - an inset block (not collapsible): a caption and one row: `0` (Attach 0),
  `1` (Attach 1), Bake, Layer, and Remove as a trash icon. Their tooltips say what they do.
- The status line (unchanged).

Each tool keeps its long OverRig explanation as its tooltip.

## Colour

- Tool rows are flat: no frame, the icon in the Animation group's blue (`#7fa9e6`, the card's own
  group colour), the name in the text colour, the explanation muted and smaller, elided at the
  card's width. The mouse lights the row (the hub's hover face) and it glows and ticks like every
  button.
- **Orange means "this waits for you"**: the Offset and Aim rows are filled orange while they read
  Finish (a pivot or an aim placed and not finished), their icon and explanation in the dark text on
  the accent. No other control of the card is orange; the chips keep the hub's own lit tint.
- The footer buttons are the hub's ordinary outlined buttons; Remove is the danger red.

## Subsections

- A head is a flat button, full width: a chevron (down open, right closed), the name in bold, the
  hint muted on the right, a hairline above it. A press opens or closes its body (the body's
  `columnLayout` managed or not).
- Each subsection's state is remembered (`skeldarToolsOpen_<key>`); by default Knots is open, Parent
  and Overlap closed. The hub's card and a popup copy share the memory; each card toggles its own
  body.
- The hotkey rows press the tools whether a body is open or not (the presses never needed a
  control).

## The classic hub

The same controls, plain: a tool row is a button with its name (left-aligned), a head is a button
with the subsection's name. No explanations (they are the tooltips there too).

## How the skin draws it (`maya_hubstyle`, `maya_hubqt`)

- `hubstyle.mark(name, role, icon=None, layout=False, hint=None)`; `Mark` gains a `hint` field
  (default None). New roles:
  - `toolrow` - a button drawn as a list row; its `hint` is drawn after the name column;
  - `subhead` - a subsection head; its `hint` is drawn right-aligned; its chevron follows its state;
  - `caption` - a small muted label that STAYS visible (a `note` becomes the header's tooltip in
    the skin, trap 226);
  - `columns` - a row layout whose children (any widgets, not only buttons) share its width equally
    (the Overlap's names and fields).
- The hint is a child `QLabel` of the button (`skRole` `rowhint` / `headhint`), transparent for the
  mouse, laid out by an event filter on the button's resizes: after the name column
  (`hubstyle.ROW_NAME` logical px, or the name's own width when it is longer), elided.
- `hubqt.set_state(name, state)`: a control's `skState` property, repolished with its hint, and
  for a tool row its icon recoloured (`"wait"`: the accent's dark text), for a head its chevron
  (`"closed"`: right). It answers False with no Qt, in the classic hub's plain build or for a
  control that is not there; the card's builder calls it while it builds (the property is set before
  the skin's marks are applied, and `_apply_mark` paints whatever state the control already
  carries).
- The tools panel reaches it through one seam, `panel._light(name, state)`, which does nothing
  without Maya's UI.

## Not done

Animating a subsection's open and close (the hub's card slide); refitting a popup copy's window
when a subsection opens (the popup scrolls, as it does for the Walk Builder's groups).

## Proof

- Unit tests: the controls top down, the roles and hints, the subsection memory and toggling, the
  wait state, the footer; the hub skin offscreen (`test_hubqt`): a tool row's hint placed after the
  name column and elided, the wait state's property and icon, a head's chevron, `columns` spreading
  labels and fields, the stylesheet rules.
- `docs/superpowers/plans/verify_tools_card.py` (a GUI Maya) opens the Parent subsection before it
  presses Across.
