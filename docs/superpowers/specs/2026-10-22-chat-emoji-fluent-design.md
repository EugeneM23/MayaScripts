# Chat emoji: the full set in Fluent 3D, animated when sent alone

2026-10-22. The animator: «Можем прокачать наш месенджер добавить аудио видео звонки, добавить больше
разных смайликов и эмодзи (найди где-то библеотеки)?». Asked, they chose emoji first, calls in a spec of
their own afterwards. Mockup of four looks: https://claude.ai/artifact/BTa4Lm5xuZvu1QBQri1zyh. Chosen:

- **look D**: Fluent 3D pictures everywhere; an emoji sent alone and a reaction play Noto's animation;
- **the pictures ship in the plugin**, about +10 MB;
- **an animation plays once when it first shows, then again under the mouse**.

This replaces the hand-picked 370 emoji and the Segoe UI Emoji drawing of
`2026-10-20-chat-everyone-emoji-avatars-design.md`. Reactions, `QUICK`, recent and the server's rules stay.

## Sources (pinned)

| what | source | licence |
|---|---|---|
| names, keywords (ru, en), groups, skin tones | `emojibase-data` 18.0.0 (`ru/data.json`, `en/data.json`) | MIT |
| pictures | `microsoft/fluentui-emoji`, a pinned commit, `assets/<name>/3D/*_3d.png` and the `<Tone>/3D/` folders | MIT |
| animations | Noto Animated Emoji, `https://fonts.gstatic.com/s/e/notoemoji/latest/<cp>/512.webp`, catalog `https://googlefonts.github.io/noto-emoji-animation/data/api.json` | CC BY 4.0, credit required |

Measured: emojibase 1,958 base emoji (about 3,400 with tones); Fluent about 1,540 base with tones; Noto 881
animated, 155-620 KB each, 24-62 frames, 0.7-2.2 s; decoding at 96 px about 2 ms a frame in Maya's Qt
(`qwebp.dll`). Fluent 3D at 96 px WebP quality 90: 2.9 KB average, about 10 MB for 3,400.

## What ships: `SkeldarAnim/assets/emoji/`

Built by `docs/superpowers/plans/make_emoji_sheets.py` (mayapy, offscreen Qt, a dev tool, never shipped;
it downloads the pinned sources into a scratch folder):

- `sheet_<group>.webp`: one per emojibase group (smileys, people, animals, food, travel, activities,
  objects, symbols), cells of 96 px, 64 columns. The `component` group and flags are left out: Fluent has
  no flags, and Windows draws a flag as two letters.
- `emoji.json`: `{"version", "groups": [[key, tab emoji, ru title]], "emoji": [...]}`, one record a base
  emoji in emojibase order: `g` glyph (with VS16 as emojibase gives it), `grp`, `sheet`, `cell`, `ru`
  label, `en` label, `kw` keywords (ru + en + shortcodes, lower case), `tones` {"1".."5": [sheet, cell,
  glyph]} where Fluent has them, `anim` true when Noto's catalog has the codepoint. An emoji with no Fluent
  picture is left out of the index.
- `LICENSE.txt`: the Fluent and emojibase MIT notices and the Noto credit.

The script refuses (and writes nothing) when a picture is missing for an index record or a sheet would pass
WebP's 16383 px limit. `assets/` is already a payload row, so nothing changes in `install.payload()`.

## `maya_chat/emoji.py` (stdlib, stays pinned)

- `index(path=None)`: the parsed `emoji.json`, cached; `by_glyph` also maps each glyph without VS16 and
  each toned glyph to its record.
- `tokens(text)`: `[(kind, piece)]` with kind "text" or "emoji", the longest index match at each place
  (ZWJ sequences, tones, keycaps, VS16 present or not). Glyphs not in the index stay text.
- `search(query, limit=200)`: case-folded words; a record matches when every word starts one of its
  label or keyword words (ru or en); ordered by label match first, then index order.
- `toned(record, tone)`: the glyph and cell for tone 0..5 (0 or missing = the base).
- `TONE_VAR = "skeldarChatEmojiTone"`.
- `count`, `only_emoji`, `is_emoji` read `tokens` (a known emoji is one, whatever its length). `recent` and
  `used` keep exact glyphs. `CATEGORIES` is gone; the groups come from the index.

## `maya_chat/emojiart.py` (Qt, new)

- `pixmap(glyph, px)`: the cell cut from its sheet (sheets loaded on first use), scaled smooth to `px`
  physical pixels, cached by (glyph, px). None for a glyph not in the index.
- `rich(text)`: what `window.rich` was, with each emoji token an `<img src="emoji:<hex>" width height>`
  of the line's height × 1.2; `register(doc, px)` adds the needed images to the document's resources.
- `draw_line(painter, rect, text, font, color)`: one line of text and emoji pictures, elided at the end;
  used by the chat list's previews, the toasts and the reply quote.
- `Animated`: `ensure(cp)` downloads the Noto webp once into `<store>/emoji_anim/<cp>.webp` on a thread
  (a failure is not asked again this session); `frames(cp, px)` decodes every frame at `px` on a thread
  and keeps the last 24 emoji's frames in memory; `player(key, cp, px)` answers the frame to draw at a time
  and whether it still moves. Until frames exist the still Fluent picture is drawn.

## The window

- **Messages**: `Feed._doc` builds from `emojiart.rich`. One to three emoji alone are drawn as 64 logical
  px pictures (no bubble, as now). An emoji with `anim` plays once the first time its message is painted
  since the window opened, and again when the mouse enters it; then it stands on its first frame.
- **Reactions**: the pill's emoji is a 18 px picture; an animated one plays once when the pill first shows
  and on hover.
- **List previews, toasts, reply quotes**: `emojiart.draw_line`.
- **The composer** keeps Windows' own glyphs (a `QPlainTextEdit`); out of scope.
- **The picker** (rebuilt, `skeldarChatEmojiPicker`): a search field on top (focus on open, Esc clears then
  closes, Enter picks the first), six tone swatches (remembered in `TONE_VAR`, applied to every toned emoji
  shown), tabs Recent + the eight groups, a scrolling painted grid (only visible cells drawn, 32 logical px
  cells); a tab click scrolls to its group, scrolling lights the tab. A cell under the mouse lifts 10 % with
  the accent glow, a press flashes (the Time Bar's numbers from `maya_timebar.look`). With a search the
  grid shows the results only. Picking works as now (into the composer, or a reaction).
- The message menu's six quick reactions draw as pictures.
- ⋮ → Interface animations off: no animation plays, no hover lift.

## Server

Nothing changes: a reaction is 1-16 UTF-16 units with no ASCII letter, digit or space, which every index
emoji but the keycaps satisfies; keycaps are left out of the quick reactions and refused as a reaction by
the server as before.

## Testing

- `tests/test_chat_emoji.py`: index loading, `tokens` (ZWJ, tones, VS16 missing, text around, unknown
  glyphs), `search` in Russian and English, `toned`, `count` / `only_emoji` on sequences, recent.
- `tests/test_chat_emojiart.py` (offscreen): every index record's cell is not empty; a document with an
  emoji has its image resource; `draw_line` elides; `Animated` with a fake download plays once and on
  hover, stops when animations are off.
- The window's tests: a big lone emoji, pills, the picker's search and tones.
- `make_emoji_sheets.py --check`: the shipped sheets equal a fresh build from the pinned sources.
- `docs/superpowers/plans/render_chat_emoji.py`: a filmstrip of the picker and a feed.

## Not built

Flags, the composer's pictures, `:name` autocomplete, stickers, emoji in the hub outside the chat.
