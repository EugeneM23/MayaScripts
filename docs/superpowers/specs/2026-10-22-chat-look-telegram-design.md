# Chat window: Telegram's layout in our colours (look A)

The animator, 2026-10-22: «Давай мессенджеру нарисуем дизайн в нашем стиле, за референс возьмем
телеграмм, сделай тестовый макет». Three live mockups on a canvas
(https://claude.ai/artifact/VyPc4uDZjzFB9kwC9Ag4kX): A Telegram in our tokens, B wells (look D),
C one column. Chosen: **A** («Берём A (Telegram в наших цветах) за основу»). C is the narrow
window the chat already has (below `look.ONE_COLUMN`), restyled with A.

The window keeps its frame (look D, title row, ✕), its pages and panes, and every behaviour;
this is a new skin and the few Telegram elements that map onto what the chat already does.

## The window

- The frame's content face is `"none"` (new in `maya_hubwindow`: the content paints its own):
  the old lighter card behind both columns is gone.
- A hairline (`track_edge`) under the title; the two columns meet on a 1 px `EDGE` divider.

## The list column (264 logical px, `look.LIST_W`)

- **Top row** (44 px): ≡ (my card, New chat, Settings, in a menu headed by my avatar, name and
  @nick), a round search field (radius 15, `field`, `track_edge`, a search icon inside), ✎.
  The old foot (my avatar, name, settings) moves into ≡.
- **Tabs** «Все / Личные / Группы» (`look.TABS`), painted: muted text, the current one `text`
  with a 2 px accent underline that glows; a grey count of the tab's chats with unread
  (`look.tab_count`). Личные: dm chats and everybody without a dm; Группы: group chats.
  Remembered in `skeldarChatTab`.
- **Rows** 58 px: avatar 42 with the online dot; the name bold 13 px; my last message's ticks
  (accent) and its time (`muted`); the preview 12 px, its sender (`Вы:`, `Ann:`) in a lighter
  ink than the text (`look.preview_parts`); the unread pill (accent, 20 px, pops). Hover:
  `card`; the open chat: `card_active`, a 1.5 px accent outline and an inner glow.

## The chat column

- **Header** (50 px, `panel`, hairline under it): avatar 34 with the dot, the name bold
  13.5 px, the status 11.5 px (`muted`; typing `accent_text`), members / voice / video / join.
- **Feed**: `#18191b` under a dot pattern (`look.PATTERN`, white and accent dots 22 px apart).
  - Bubbles radius 12: theirs `card`, mine `look.MINE`; the last of a run gets Telegram's
    tail on the sender's side (one path: the bubble, its square corner and the curl).
  - Time and ticks **inside** the bubble, on the text's last line when they fit
    (`look.meta_fits`), else under it; ticks are drawn (✓, ✓✓, a clock, !), mine in
    `look.MINE_META`, read in `accent_text`.
  - Reactions **inside** the bubble, under its content; the time then stands at the right of
    the last row of pills when it fits.
  - A reply's quote: a 3 px bar and the name in the replied sender's colour.
  - Group: the sender's name in their colour on the first of a run, their avatar (30 px) by
    the last.
  - Emoji alone (1-3): no bubble, the time in a dark pill under them.
  - A file's card: no plate; the tile `accent_tint` ringed in accent; outlined buttons, Open in
    `accent_text`.
  - Day separators and call lines: dark pills (`rgba(16,17,19,.8)`, a `#2c2e33` ring); a call
    line's icon is drawn (phone, green; missed, red).
  - **«Непрочитанные сообщения»**: a band before the first message that was unread when the chat
    was opened (`look.first_unread`, `look.mark_unread`), kept until another chat is opened.
  - **A reply button** beside the bubble under the mouse (a 26 px circle); a click replies.
- **Composer** (`panel`, a hairline over it): 📎, a round field (radius 17) holding the text and
  the emoji button, a round send button (34 px): grey while empty, accent with text.
  The reply / edit bar: an icon, the quote (bar and title in the sender's colour) and ✕.
- **To the newest**: a round 36 px button with the unseen count.

## Not built

Pinned and muted chats, search inside a chat, a ⋮ menu in the header, the typing dots'
animation in the header: the chat has none of these yet.

## Proof

Unit tests (`look`: tabs, counts, preview parts, the unread mark, meta fits; the window
offscreen: tabs filter, the ≡ menu, the band, inline meta, pills inside the bubble, the reply
button) and an offscreen render (`docs/superpowers/plans/render_chat_look_a.py` →
`chat_look_a.png`). Not seen in a GUI Maya.
