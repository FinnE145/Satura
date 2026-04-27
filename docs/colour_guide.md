# Satura — Colour System Guide

---

## Player Palettes

Four selectable schemes. Each user chooses their own preference globally — it governs both their app experience and their in-game colour. P1 is always the warm colour and P2 is always the cool colour, but which specific palette each player uses is independent per device.

| Name | Warm (P1) | Cool (P2) |
|---|---|---|
| **Solstice** *(default)* | `#D2640E` | `#A82068` |
| **Fieldstone** | `#AC3E26` | `#2C4874` |
| **Levant** | `#C48C1C` | `#661E6E` |
| **Folio** | `#D4A800` | `#303482` |

These are **canonical game colours** — used for board cell rendering and SVG palette assets only. They are never used directly in app chrome.

---

## UI Accent Colours

App chrome uses a separate set of accent values per palette. These are decoupled from canonical values so the UI can maintain readable contrast on dark backgrounds without affecting board rendering.

Each palette supplies four UI accent values:

| Palette | `warm` | `warm_bright` | `cool` | `cool_bright` |
|---|---|---|---|---|
| **Solstice** | `#D2640E` | `#F07828` | `#C93E8F` | `#D85EA8` |
| **Fieldstone** | `#BE4F2B` | `#D76A45` | `#4F76A8` | `#6E93C1` |
| **Levant** | `#D2640E` | `#F07828` | `#8A3FA2` | `#A965BF` |
| **Folio** | `#D2640E` | `#F07828` | `#4F5CC0` | `#7380D7` |

`warm` and `warm_bright` are for the warm (P1) accent. `cool` and `cool_bright` are for the cool (P2) accent. `bright` variants are used on card backgrounds where base values read too dim.

These values are injected at runtime via JavaScript into CSS custom properties on `:root`. The backend (`routes.py`) computes them from `_UI_ACCENT_CONFIG`.

---

## CSS Custom Properties

All colour usage in CSS goes through custom properties defined on `:root`. The accent families are overwritten at page load by the palette injection script in `base.html`.

### App chrome

| Variable | Value | Notes |
|---|---|---|
| `--bg` | `#2E2C2A` | Page background |
| `--bg-header` | `#252321` | Nav / header background (darkest) |
| `--bg-card` | `#353331` | Card background (lightest) |
| `--bg-editor` | `#1A1918` | Code editor background |
| `--bg-hover` | `rgba(246,245,244, 0.04)` | `--text` at 4% — subtle hover fill on interactive rows |

### Text

| Variable | Alpha | Notes |
|---|---|---|
| `--text` | — | `#F6F5F4` — primary body text; also used as a solid near-white surface (slider thumb, board cell before JS fill) |
| `--text-muted` | 50% | De-emphasised / secondary text |
| `--text-dim` | 70% | Slightly reduced text; also used as a mid-grey surface fill (status dot default, contested coverage segment). Sits at 70% rather than matching `--warm-dim` (65%) because it often appears grey-on-grey and needs a touch more opacity to read clearly. |
| `--text-tint` | 7% | General-purpose neutral surface — badge fills, pill idle background, disabled button, gradient overlays, ghost separators |
| `--text-subtle` | 25% | Mid-weight neutral — scrollbar thumb, ghost button hover border |

### Borders

Both borders are tints of `--text`.

| Variable | Alpha | Notes |
|---|---|---|
| `--border` | 8% | Default structural border |
| `--border-card` | 14% | More visible border — cards, form inputs, list separators |

### Warm accent (palette-driven)

| Variable | Alpha | Notes |
|---|---|---|
| `--warm` | — | Base warm — borders, text, icons |
| `--warm-tint` | 10% | Light fill — hover and selected backgrounds |
| `--warm-subtle` | 25% | Mid-weight — selection highlights, pill borders |
| `--warm-dim` | 65% | Muted — borders where full opacity reads too strong |

### Warm bright (palette-driven, for `--bg-card` backgrounds)

| Variable | Alpha | Notes |
|---|---|---|
| `--warm-bright` | — | Base — use in place of `--warm` on card backgrounds |
| `--warm-bright-tint` | 10% | Light fill on card backgrounds |
| `--warm-bright-subtle` | 25% | Mid-weight on card backgrounds |
| `--warm-bright-dim` | 65% | Muted border on card backgrounds |

### Cool accent (palette-driven)

| Variable | Alpha | Notes |
|---|---|---|
| `--cool` | — | Base cool — borders, text, icons |
| `--cool-tint` | 10% | Light fill — hover and selected backgrounds |
| `--cool-subtle` | 25% | Mid-weight — selection highlights, pill borders |
| `--cool-dim` | 65% | Muted — borders where full opacity reads too strong |

### Cool bright (palette-driven, for `--bg-card` backgrounds)

| Variable | Alpha | Notes |
|---|---|---|
| `--cool-bright` | — | Base — use in place of `--cool` on card backgrounds |
| `--cool-bright-tint` | 10% | Light fill on card backgrounds |
| `--cool-bright-subtle` | 25% | Mid-weight on card backgrounds |
| `--cool-bright-dim` | 65% | Muted border on card backgrounds |

### Semantic

| Variable | Value / Alpha | Notes |
|---|---|---|
| `--error` | `#D95F5F` | Error state — text, icons |
| `--error-tint` | 10% | Error background fill |
| `--error-border` | 25% | Error border — feedback boxes |
| `--error-border-strong` | 45% | Stronger error border — buttons, focused inputs in error state |
| `--warn` | `#BFA030` | Warning state — text, icons |
| `--warn-tint` | 10% | Warning background fill |
| `--warn-border` | 25% | Warning border — feedback boxes |
| `--warn-border-strong` | 45% | Stronger warning border — buttons |
| `--success` | `#5DA85D` | Success / ready state |
| `--success-tint` | 10% | Success background fill |
| `--success-border` | 25% | Success border |
| `--success-border-strong` | 45% | Stronger success border |

---

## Colour Modifier Classes

Rather than repeating the accent triplet in every component variant, four utility classes encapsulate the pattern. Apply one alongside a component class to set its active or accent colour.

The triplet is: **tint background · coloured text · dim border**.

| Class | Background | Text | Border |
|---|---|---|---|
| `.warm` | `--warm-tint` | `--warm` | `--warm-dim` |
| `.warm-bright` | `--warm-tint` | `--warm-bright` | `--warm-bright-dim` |
| `.cool` | `--cool-tint` | `--cool` | `--cool-dim` |
| `.cool-bright` | `--cool-tint` | `--cool-bright` | `--cool-bright-dim` |

Use `.warm` / `.cool` on `--bg` and `--bg-header` surfaces. Use `.warm-bright` / `.cool-bright` on `--bg-card` surfaces.

These classes only work on elements that already have a `border` property defined — they set `border-color`, not `border` shorthand. Component base classes are expected to provide `border: 1px solid transparent`.

---

## Button Colour Classes

Buttons have two distinct colour behaviours. Both sets are palette-driven and follow the warm/cool/bright naming.

### Border classes — permanent colour, tint on hover

Used for primary and secondary CTAs. The element has a coloured border and text at rest; hover adds a tint background.

| Class | At rest | On hover |
|---|---|---|
| `.btn-warm-border` | warm text + warm-dim border | + warm-tint bg |
| `.btn-cool-border` | cool text + cool-dim border | + cool-tint bg |
| `.btn-warm-bright-border` | warm-bright text + warm-bright-dim border | + warm-bright-tint bg |
| `.btn-cool-bright-border` | cool-bright text + cool-bright-dim border | + cool-bright-tint bg |

`.btn-warm-border` and `.btn-cool-border` automatically switch to the bright family when inside `.card` via a context override rule, so templates don't need to choose based on background.

`.btn-warm-bright-border` and `.btn-cool-bright-border` are used directly when the bright family is always required regardless of container (e.g. settings sidebar nav active state).

### Hover-only classes — no colour at rest, full triplet on hover

Used for generic interactive elements that should gain colour only on interaction.

| Class | On hover |
|---|---|
| `.btn-warm-hover` | warm-tint bg + warm text + warm-dim border |
| `.btn-cool-hover` | cool-tint bg + cool text + cool-dim border |
| `.btn-warn-hover` | warn-tint bg + warn text + warn-border border |
| `.btn-danger-hover` | error-tint bg + error text + error-border border |

These include a `transition` declaration in their base rule since they are not always used on `.btn` elements (which already have a transition).

### Text-only hover

| Class | On hover |
|---|---|
| `.warm-hover` | warm text colour |
| `.cool-hover` | cool text colour |

---

## Accent Variant Usage Rules

- **`--warm` / `--cool`**: text, icon colour, border colour in default interactive states.
- **`--warm-tint` / `--cool-tint`**: hover or selected background fill (light).
- **`--warm-subtle` / `--cool-subtle`**: mid-weight — pill borders, text selection highlight.
- **`--warm-dim` / `--cool-dim`**: border colour where full opacity reads too strong.
- **`--warm-bright` / `--cool-bright`**: use in place of base on `--bg-card` backgrounds.
- **`--warm-bright-tint` / `--cool-bright-tint`**: hover fill on card backgrounds.
- **`--warm-bright-subtle` / `--cool-bright-subtle`**: mid-weight on card backgrounds.
- **`--warm-bright-dim` / `--cool-bright-dim`**: border on card backgrounds.

Outside the game screen, warm is the primary accent and cool is used sparingly for contrast. Inside the game screen, whichever colour belongs to the local player is primary.

---

## Palette Injection

The backend (`routes.py → _active_palette_for_user()`) resolves the active palette and passes all UI accent values through the template context. `base.html` stores them as `data-*` attributes on `<body>` and an inline script at the bottom of `<body>` applies them to `:root` via `style.setProperty`. This runs before first paint, so there is no flash.

The script sets all four families — `--warm`, `--warm-bright`, `--cool`, `--cool-bright` — including their tint, subtle, and dim variants, derived via `hexToRgba()` at the correct alphas.

The `<body>` data attributes available to JavaScript:

| Attribute | Contains |
|---|---|
| `data-active-palette` | Palette name (`solstice`, `fieldstone`, etc.) |
| `data-palette-warm` | Canonical warm hex (board/SVG use) |
| `data-palette-cool` | Canonical cool hex (board/SVG use) |
| `data-ui-warm` | UI warm hex |
| `data-ui-warm-bright` | UI warm-bright hex |
| `data-ui-cool` | UI cool hex |
| `data-ui-cool-bright` | UI cool-bright hex |
