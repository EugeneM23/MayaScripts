# Card rules: what tells the parts of a card apart (2026-10-16)

The animator, after the rail layout: «давай приступим теперь к дизайну». Shown as before/after mockups
(https://claude.ai/artifact/228rNcXckRzKZMcBUjV7Fd). Asked: the shared rules first, then the cards,
the densest three first (Animation Setup, Inventory, Connections); **one orange button per SECTION of
a card** (not one per card). The animator approved the rules and the three cards.

## The shared rules (the skin's stylesheet and `maya_hubqt`)

1. **A switch is recessed, a button is raised.**
   - A `segments` track is `track` (#17181a) with a 1 px `track_edge` (#26282c).
   - The checked segment is a lighter `thumb` (#44474e) with white bold text. It used to be the
     `line` grey with plain text: a button's outline colour.
2. **A section's caption** (role `heading`):
   - uppercase, small, muted, bold, a little letter-spacing;
   - room above it and a hairline (`hover`, #34363b) under it.

   It used to be bold white text with a `line` underline, competing with the card's title. The skin
   upper-cases the label and spaces its letters itself (Qt stylesheets have neither).
3. **A row's label is muted** (new role `label`): the words left of a field or a switch («Arm R»,
   «Hand R», «Import»). White is for what changes: values, choices, names.
4. **The card's head is ruled off.**
   - A hairline stands at the top of every card's body, under the header.
   - It opens and shuts with the body: a collapsed card shows none.
5. **The message line has a tone** (`maya_hubstyle.tone(text)`, pure):
   - `ok`, a green left edge: the text starts with a done word (Imported, Added, Applied, Baked,
     Retargeted, Saved, Sent, Equipped, Deleted, Exported, ...);
   - `wait`, orange: «waiting», «press Finish», «then Finish»;
   - `no`, red: refused, cannot, could not, failed, nothing changed, not found, error;
   - plain otherwise, a `line` grey edge.

   The writers are not changed: a refusal said in other words stays plain, which is the safe
   direction.

## The three cards

- **Animation Setup**:
  - the skin shows the captions «Character» (over its row and the portraits) and «Animation» (over
    the source switch);
  - the Connect inset is not drawn in the skin: the caption separates the section;
  - one orange per section stays as it is (+ Import, Import Animation).
  - The classic hub is unchanged.
- **Inventory**:
  - the panel paints two captions in the same style, «Hands» over the hand cards and «Weapons» over
    the tiles (`maya_invlook.CAPTION_H`);
  - the hand cards are named «Right» / «Left» in the caption style, the picked one in
    `accent_text`.
- **Connections**:
  - three captions: «FK / IK» over the limb rows, «Weapon in hands» over the chooser and the three
    parent rows, «Any object» over BakeAcross / Release;
  - Apply all stands alone under the parent rows (the section's orange). BakeAcross and Release have
    their own row;
  - the row labels are `label`s, and read «Hand R» / «Hand L».

## Proof

- Unit tests:
  - `tone`;
  - the stylesheet's rules;
  - a heading upper-cased with its letter spacing;
  - the card's rule in the body;
  - the message's tone property;
  - the inventory's caption rects;
  - the three builders' new marks on fake `cmds`.
- An offscreen render of the cards in the skin.
- The live hub is the animator's to check after Check update.
