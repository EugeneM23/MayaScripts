# The Characters cards catch fire under the mouse (2026-10-02)

## The ask

The animator: «Хочу попробовать сделать крутые карточки выбора ригов и скелетов.
Когда навожу мышкой на карточку то хочу что бы на заднем фоне в карточке загорался
огонь летели искры и она немного увеличивалась в размере.» A standalone prototype
came first (`docs/superpowers/plans/proto_fire_cards.py`, run by mayapy, the same
PySide6 / QPainter the hub uses, on the shipped portraits and the hub's tokens).
Their verdict on it: «У каждого персонажа свой цвет огня. А так все хорошо мне
нравится давай делать фичу». So the prototype's look is the design. This spec
records how it goes into the plugin and the choices taken alone.

## What it does

The cursor on an available portrait of the Animation Setup card's grid sets it
alight:

- **Flames behind the character.** A heat field (80 × 90 cells) rises from the
  card's bottom edge, its tongues shaped by a cooling map that scrolls up with
  them, swayed by a slow wind and torn by the classic "one random neighbour
  below" rule. The HEAT is interpolated to the card's pixels and the palette
  applied after, so the edges stay crisp at any size. It is drawn additively
  behind the portrait; the portraits carry alpha.
- **Sparks.** Particles born in the flames, buoyant and turbulent, cooling from
  white-hot to red with a fading tail. 24 burst out when the card catches and 30
  when it is clicked. A quarter fly in front of the character, and they leave
  the card and fly on over the grid.
- **The character lit by it.** The silhouette darkens a little (backlit), the
  inside of its edge takes a rim of firelight, and it is lit warm from below.
  All three flicker with the field's own heat.
- **The card grows 7 %** on a spring (a touch of overshoot), drawn over its
  neighbours, with an outer glow and a ring in the fire's colour. The name turns
  that colour and goes bold.
- **The mouse leaves**: the source dies, the flames finish rising and burn out,
  the sparks live out their lives, and the card settles back.

**Every character has its own fire** (`catalog.Model.fire`):

| model | fire |
|---|---|
| Manny | `ember`, the hub's orange |
| Creep | `spectral` blue |
| Orc D | `toxic` green |
| UE4 Mannequin | `arcane` violet |

A model whose `fire` is `""` (the default, so a row written as `Model(key,
label)` constructs) gets the old hover, unchanged. That is the Auto card a peer
session is adding the same day.

**When the fire does not light:**

- on a dimmed portrait;
- during a drag: the drag puts the fire out, as the old hover went out;
- with ⋮ → **Interface animations** off (`maya_hubmotion.enabled()`): the old
  hover, no fire, no grow.

## Where the code goes

- **`SkeldarAnim/maya_charfire.py`** (numpy + stdlib, no Qt, no `cmds`; a
  payload row). It holds the palettes (`PALETTES`, `palette_rgba`,
  `palette_lut`), `Fire` (the heat field; `field(lut, w, h)` answers the BGRA
  premultiplied array), `Sparks`, `CardFx` (hover → power, the grow spring, the
  flash, `active()`), and `lit_masks(alpha)` (shade, rim, light as float masks
  from a portrait's alpha). Everything is fixed-step and seeded, so it is tested
  without Qt. Its own colours live here: `maya_chargrid` must keep naming hub
  tokens only, and a test pins that.
- **`SkeldarAnim/maya_chargrid.py`** holds what Qt does with it:
  - `FireLooks`: per palette, the LUT, three spark sprites and the ring, glow,
    rim and light colours;
  - the lit images per (model, side, palette);
  - `_paint_hot(p, ...)`: one hot card, in the coordinates of whoever paints it;
  - a 16 ms `QTimer` that runs only while a card is active;
  - the **overlay**.
- **The overlay** (`FireOverlay`, object name `skeldarCharacterFire`). The grid
  is clipped to its placeholder, so a grown card, its glow and its sparks would
  be cut at every edge of the grid. The burning cards are therefore drawn by a
  mouse-transparent (`WA_TransparentForMouseEvents`, in-window) widget, a child
  of the hub's **scrolled content**: the first ancestor of the grid whose parent
  is a `QAbstractScrollArea`'s viewport. That is the skin's `skeldarHubContent`,
  or the classic hub's scrollLayout, so both hubs get it.
  - Its geometry is the grid's rect in the content, widened by a fifth of a
    cell at the sides and bottom and three fifths above. It is re-synced on
    every tick, because a card sliding above moves the grid and sends it no
    event.
  - The grid skips the cards the overlay draws.
  - **The overlay draws only while the grid stands whole inside every ancestor
    up to the content.** Mid-slide, or with the card collapsed, the grid draws
    its hot cards itself, clipped like everything else.
  - No scrolled ancestor: the grid draws them itself.
  - The overlay is deleted with the grid.
- `catalog.Model` gains `fire`; `MODELS` names one per model.

## Cost

Measured in the prototype at the dock's size: about 3 ms a frame for the whole
grid with one card burning, nothing while every card is cold (the timer stops).
The spark loop is the Python part; sparks are capped by their life (about 30
a second while burning).

## Proof

- `tests/test_charfire.py`:
  - the palettes are premultiplied and every model's fire is one;
  - a fire unpowered stays cold, powered it rises past 40 % of the card, and
    put out it goes cold;
  - sparks rise and die;
  - `CardFx`'s whole life ends inactive, and the spring settles;
  - the rim is zero where the body meets the picture's frame.
- `tests/test_chargrid.py`, offscreen:
  - hovering ignites an available portrait (timer on), not a dimmed one, and
    not with the animations off;
  - a burning card paints its own palette (the Creep card turns blue);
  - the timer stops once all is cold;
  - a drag puts the fire out;
  - in a scroll area the overlay stands in the content, is mouse-transparent
    and covers the grid widened;
  - a model with no fire keeps the old hover;
  - still no colour of the grid's own.
- `docs/superpowers/plans/verify_character_fire.py`, in a disposable GUI Maya
  (scratch `MAYA_APP_DIR`, port 7037):
  - the hub open, a real mouse move sent to the grid;
  - the overlay in the hub's content, the card's own colours rendered from our
    widgets (`render`, never a grab of Maya's);
  - the paint cost, Interface animations off;
  - a hub rebuild leaving no overlay behind.
