# Satura — Web Style Guide

---

## Colour — App Chrome

| Role | Value | Notes |
|---|---|---|
| Background | `#2E2C2A` | Dark grey, imperceptibly warm |
| Body text | `#F6F5F4` | Off-white, imperceptibly warm — not cream |

Global dark mode throughout the entire app.

Accent colour usage follows a strict hierarchy. Colour means something is alive or chosen — never decorative. Idle and structural elements stay entirely within the grey palette. Interactive elements show the accent colour as a border or underline in their default state, graduating to a subtle tint fill on hover, active, or selected states.

---

## Colour — Player Palettes

Four selectable schemes. Each user chooses their own preference globally — it governs both their app experience and their in-game colour. P1 is always the warm colour and P2 is always the cool colour, but which specific palette each player uses is independent per device.

| Name | Warm (P1) | Cool (P2) | Notes |
|---|---|---|---|
| **Solstice** *(default)* | Warm Orange `#D2640E` | Deep Magenta `#A82068` | Most vibrant, best contested-cell colour |
| **Fieldstone** | Terracotta `#AC3E26` | Slate Blue `#2C4874` | Most restrained, earthy |
| **Levant** | Golden Ochre `#C48C1C` | Deep Plum `#661E6E` | Regal, warm throughout |
| **Folio** | Yellow Gold `#D4A800` | Deep Indigo `#303482` | Flat, elementary, high contrast |

Outside the game screen, the warm colour is the primary accent and the cool colour is used sparingly for contrast. Inside the game screen, whichever colour belongs to the local player is the primary accent and the opponent's colour is used sparingly.

---

## Colour — Board Cell Rendering

The board starts white. Each cell holds a paint level for each player from 0 to 5. The blend model is artificial — hue is determined by the ratio of paint levels, and total paint drives the cell from white through full colour to black.

### Variables

- `p1` — paint level of the warm player (0–5)
- `p2` — paint level of the cool player (0–5)
- `c1` — RGB of the warm player colour
- `c2` — RGB of the cool player colour
- `total = p1 + p2`
- `t = total / 10`
- `ratio = p2 / total` (undefined when total = 0)
- `mid = c1 + ratio × (c2 − c1)` — the hue for this cell, blended between the two player colours by ratio

### Special cases

- If `total = 0`: cell is `rgb(255, 255, 255)` — pure white.
- If `total = 10` (i.e. p1 = 5 and p2 = 5): cell is `rgb(0, 0, 0)` — pure black, by design rule, regardless of formula output.

### White → colour phase (t ≤ 0.5)

```
s = t × 2
result = white + s × (mid − white)
       = rgb(255,255,255) + s × (mid − rgb(255,255,255))
```

The cell lerps linearly from white toward the mid colour as total paint increases from 0 to 5.

### Colour → black phase (t > 0.5, total < 10)

```
s = (t − 0.5) × 2
result = mid × (1 − s)
```

The cell lerps linearly from the full mid colour toward black as total paint increases from 5 to 10.

### Manual overrides

The two near-black corner cells (p1=4, p2=5) and (p1=5, p2=4) are adjusted upward from the formula for all palettes, as they otherwise appear nearly indistinguishable from black. Additionally, Fieldstone uses a slower darkening rate throughout the colour → black phase due to both base colours being intrinsically darker.

| Palette | Override |
|---|---|
| Solstice | (4,5) and (5,4): multiply formula result by **1.35** |
| Fieldstone | All dark-phase cells: use `s = (t − 0.5) × 2 × 0.7` instead of standard s. No additional corner override needed. |
| Levant | (4,5) and (5,4): multiply formula result by **1.35** |
| Folio | (3,5), (4,4), (5,3): multiply formula result by **1.2**. (4,5) and (5,4): multiply formula result by **1.6** |

These values are provisional. All blends will be hardcoded per palette after playtesting to fully dial in contrast.

---

## Typography

| Role | Font | Notes |
|---|---|---|
| Display wordmark | Engravers MT | Large use only — print, hero, splash. Custom-modified version. |
| Compact wordmark | Libre Baskerville | Navbar and small contexts. Same transitional serif family as Lora. |
| Headings, nav, usernames, large UI | Lora | Variable, 400–800 weight. Used at all large sizes. |
| Small UI, labels, buttons, metadata | DM Sans | Timestamps, game stats, word counts, functional chrome. |
| Code, script editor, inline code | Courier Prime | All code contexts including the in-game script editor and docs. |

**General rule:** serif at large sizes, sans-serif at small functional sizes. Not absolute — to be tuned during implementation.

The transitional serif family runs coherently from Engravers MT → Libre Baskerville → Lora, from most ornate to most practical. Libre Baskerville and Lora share rounded arc construction and similar letterforms, giving the typography system internal coherence without monotony.

Lora and Libre Baskerville are available on Google Fonts. Courier Prime is available on Google Fonts. DM Sans is available on Google Fonts.

Sizing to be determined fresh during implementation.

---

## Wordmark

Two-tier system:

**Large** — Engravers MT, all caps, modified in Figma. Planned modifications: tighten letter spacing so similar serifs connect (T–U-R–A); adjust top T serifs to merge better with U; adjust S shape and position to sit closer to A; possible further stylistic changes. Used at display sizes only.

**Small** — Libre Baskerville, unmodified, all caps. Used in the navbar and any compact context where Engravers MT becomes illegible.

---

## Logo Mark

A 3×3 grid of cells referencing the game board. Axis orientation matches the blend grid — cool increases left to right (columns 0–2), warm increases top to bottom (rows 0–2). The nine cells are:

```
white        light cool   cool
light warm   mid          dark cool
warm         dark warm    black
```

No borders between cells. The white and black corners are warmer than their strict in-game values so the mark reads cohesively and holds up against both light and dark backgrounds.

The default mark uses Solstice colours. Eventually the mark will reflect each user's chosen palette. The mark should feel classical or engraved in construction — not flat and modern. Execution to be determined.

---

## Shape Language

The Claude.ai chat interface is the reference starting point — rounded corners, layered dark greys, very thin light grey borders. To be tuned for Satura's character.

No solid filled colour buttons. Colour appears as border and underline in default interactive states, graduating to a subtle tint fill on hover, active, or selected states. Idle structural elements stay in the grey palette.

Underlines should be used with care — they can read as formal or as unstyled links. Not a default interactive affordance.

---

## Open Threads

- Game screen layout and element hierarchy
- Specific sizing scale for web typography
- Precise component styles — border radius values, border weights, grey layer values
- Landing page approach — editorial or experiential
- Logo mark final execution
