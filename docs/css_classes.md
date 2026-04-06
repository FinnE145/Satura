# CSS Class Index

Reference for all classes defined in `app/static/css/site.css`.
Update this file whenever a class is added, changed, or removed.

---

## Generic — reusable anywhere on the site

### Typography
| Class | Description |
|---|---|
| `.text-muted` | 50% opacity text — often hard to see, low contrast for minor details |
| `.text-subtle` | 70% opacity text — secondary/supporting text |
| `.text-italic` | italic text |
| `.text-small-sans` | 0.78em DM Sans — timestamps, metadata, disclaimers |
| `.subheading` | italic Lora 0.9rem — taglines, subtitles, section intros |
| `.heading-display` | 2rem Lora 600 — large page or section headings |
| `.form-label` | 1em DM Sans 500, subtle colour — form field labels |
| `.label` | 0.72em DM Sans, uppercase, wide tracking — category/section tags |
| `.label-warm` | warm accent colour modifier for `.label` |
| `.label-cool` | cool accent colour modifier for `.label` |

### Backgrounds
| Class | Description |
|---|---|
| `.bg-grey-dark` | `--bg-header` background (darkest) |
| `.bg-grey` | `--bg` background (page default) |
| `.bg-grey-light` | `--bg-card` background (lightest) |

### Hover utilities
| Class | Description |
|---|---|
| `.warm-hover` | text transitions to warm accent on hover |
| `.cool-hover` | text transitions to cool accent on hover |
| `.btn-warm-hover` | border + tint fill transitions to warm accent on hover |
| `.btn-cool-hover` | border + tint fill transitions to cool accent on hover |

### Layout
| Class | Description |
|---|---|
| `.container` | 1440px max-width centred wrapper with horizontal padding |

### Buttons
Combine base `.btn` with one variant. Add `.btn--sm` for a smaller size.

| Class | Description |
|---|---|
| `.btn` | base button — inline-flex, DM Sans, rounded corners |
| `.btn--sm` | smaller size modifier (0.78em, tighter padding) |
| `.btn--ghost` | neutral grey border — low-priority or destructive actions |
| `.btn--secondary` | cool-coloured border — sign in, secondary CTAs |
| `.btn--accent` | warm-coloured border — primary CTA |
| `.btn--warn` | warning-coloured border action (yellow) |
| `.btn--danger` | error-coloured border action (red) |
| `.icon-btn` | stacked icon + label button — mode selectors, tool pickers |
| `.icon-btn-label` | tiny label below the icon inside `.icon-btn` |

### Cards
| Class | Description |
|---|---|
| `.card` | rounded dark card with border — general content container |
| `.card-header` | flex row header strip with bottom border |
| `.card-title` | Lora 0.9375em 600 — title inside `.card-header` |
| `.card-footer` | right-aligned flex row for card-level actions |

### Badges
| Class | Description |
|---|---|
| `.badge` | base pill label — requires a variant modifier |
| `.badge--ok` | neutral grey badge |
| `.badge--error` | red badge |
| `.badge--warn` | yellow badge |

### Feedback
| Class | Description |
|---|---|
| `.error-msg` | red-tinted box with border — form validation errors |
| `.empty-label` | small italic placeholder when a list or panel is empty |
| `.is-disabled` | generic disabled-state utility (reduced opacity); use with `a` for non-interactive disabled links |

### Prose
| Class | Description |
|---|---|
| `.prose` | centred 720px text container — long-form text, legal pages, contact; sets Lora body text with heading/list/table styles |

---

## Specific — scoped to one page or feature

### Brand
| Class | Description |
|---|---|
| `.brand` | flex logo + wordmark link in the nav |
| `.brand-mark` | square logo mark image |
| `.brand-wordmark` | "SATURA" Libre Baskerville all-caps text |

### Nav
| Class | Description |
|---|---|
| `.site-nav` | sticky top navigation bar |
| `.nav-inner` | flex row container inside the nav |
| `.nav-links` | flex row of page links |
| `.nav-link` | individual nav text link (muted, highlights on hover) |
| `.nav-actions` | right-hand slot (sign-in button or profile) |
| `.nav-profile` | relative wrapper for the profile dropdown |
| `.nav-profile-btn` | icon button that opens/closes the dropdown |
| `.nav-dropdown` | absolute dropdown panel below the profile button |
| `.nav-dropdown-item` | link row inside the dropdown |

### Alt header (test bench, stripped nav)
| Class | Description |
|---|---|
| `.site-header` | sticky header without nav links |
| `.header-inner` | flex row container inside the alt header |
| `.header-divider` | thin vertical rule separator between header items |
| `.header-label` | 0.8125em DM Sans label for text items in the alt header |

### Page chrome
| Class | Description |
|---|---|
| `.site-main` | main content area with standard vertical padding |
| `.site-footer` | footer bar with top border |
| `.footer-inner` | flex row container inside the footer |

### Stub / placeholder pages
| Class | Description |
|---|---|
| `.stub-wrap` | centred flex column — coming-soon / unbuilt pages |
| `.stub-back` | small warm back-link on stub pages |

### Home page
| Class | Description |
|---|---|
| `.page-split` | two-column layout: content left + sticky panel right |
| `.page-left` | left content column (max 720px, left-aligned) |
| `.page-right` | right sticky full-height panel (50vw) |
| `.hero-content` | flex column hero section (wordmark, tagline, modes) |
| `.wordmark` | large SVG wordmark image in the hero |
| `.tagline` | italic Lora tagline beneath the wordmark |
| `.hero-create-label` | bold Lora label above mode selection buttons |
| `.hero-create-label--learn` | spacing modifier for the second create label |
| `.hero-modes` | flex row of game-mode selection buttons |
| `.hero-stat` | tiny uppercase stat row at the bottom of the hero |
| `.stat-dot` | small blinking warm dot inside `.hero-stat` |
| `.explainer` | border-topped section for homepage explainer content |
| `.code-window` | dark rounded demo code window (homepage animation) |
| `.code-bar` | toolbar strip inside `.code-window` |
| `.code-timer` | monospace countdown timer in the code bar |
| `.code-cost` | word-cost stat label in the code bar |
| `.code-bank` | word-bank stat label in the code bar |
| `.code-eta` | ETA stat label in the code bar |
| `.code-body` | monospace syntax-highlighted code display area |
| `.tw-cursor` | blinking typewriter cursor inside `.code-body` |
| `.cta-cards` | 2-column grid of homepage CTA sections |
| `.cta-card` | individual clickable CTA block |
| `.cta-tag` | tiny uppercase warm/cool tag above the CTA title |
| `.cta-title` | large Lora heading inside a CTA card |
| `.cta-desc` | small muted description inside a CTA card |
| `.cta-arrow` | animated arrow icon that appears on CTA hover |

### Test bench
| Class | Description |
|---|---|
| `.session-bar` | flex status bar at the top of the test bench |
| `.status-dot` | small coloured indicator dot (use with a state modifier) |
| `.status-dot--ready` | green dot |
| `.status-dot--pending` | yellow dot |
| `.status-dot--error` | red dot |
| `.session-bar-group` | flex group of related items within the session bar |
| `.session-bar-key` | tiny uppercase key label in the session bar |
| `.session-bar-sep` | non-selectable separator character between bar groups |
| `.session-bar-spacer` | flex spacer that pushes subsequent items right |
| `.session-id` | monospace session UUID display |
| `.phase-pill` | rounded pill showing the current game phase |
| `.phase-pill--write` | warm accent variant for the write phase |
| `.word-bank` | word-bank count display in the session bar |
| `.palette-label` | tiny uppercase "Palette" label (shares styles with `.session-bar-key`) |
| `.workspace` | 55/45 grid: script editor left, board right |
| `.editor-card` | flex column card wrapping the script editor |
| `.script-meta` | flex row showing word cost and ETA above the editor |
| `.word-cost` | word-count text in `.script-meta` |
| `.word-cost--active` | warm colour when words are actively being spent |
| `.word-eta` | ETA text in `.script-meta` |
| `.word-eta--waiting` | yellow colour while waiting for words to accrue |
| `.word-eta--ready` | subtle colour when word bank is sufficient |
| `.script-editor` | full-height monospace textarea for script input |
| `.board-card` | flex column card wrapping the game board |
| `.board-legend` | flex row legend showing both player colours |
| `.board-legend-item` | pill legend item (use with `--p1` or `--p2`) |
| `.board-legend-item--p1` | warm accent pill |
| `.board-legend-item--p2` | cool accent pill |
| `.board-wrap` | padded inner container for the board grid |
| `.board-grid` | CSS grid of game board cells |
| `.board-cell` | individual board cell (background set via JS) |
| `.board-agent` | absolute circle overlay marking an agent's position |
| `.results-row` | 2-column grid below the workspace for result cards |
| `.result-card` | card with a scrollable body for compiler/execution output |
| `.outcome-label` | small muted outcome summary line |
| `.diag-ok` | small green success message in the diagnostics panel |
| `.diag-item` | flex row for a single compiler diagnostic |
| `.diag-item--error` | red error severity modifier |
| `.diag-item--warn` | yellow warning severity modifier |
| `.diag-icon` | icon/symbol column in a diagnostic row |
| `.diag-msg` | message text column in a diagnostic row |
| `.log-entry` | flex row for a single execution log line |
| `.log-idx` | step index number (non-selectable) |
| `.log-op` | operation name in a log entry |
| `.log-op--move` | warm accent — move operations |
| `.log-op--paint` | cool accent — paint operations |
| `.log-op--query` | muted — query operations |
| `.log-op--halt` | yellow — halt operations |
| `.log-op--reset` | red — reset operations |
| `.log-detail` | detail/argument text in a log entry |
| `.log-sep` | thin horizontal rule separating log sections |
| `.log-summary` | small summary line at the end of a log block |
| `.palette-bar` | flex row containing the palette selector |
| `.palette-options` | flex row of `.palette-btn` elements |
| `.palette-btn` | bordered button showing palette name + colour mark |
| `.palette-mark` | small coloured square inside a `.palette-btn` |

### Login page
| Class | Description |
|---|---|
| `.login-wrap` | centred narrow wrapper for the login form |
| `.login-card` | card containing the login form fields |

### Contact page
| Class | Description |
|---|---|
| `.contact-form` | flex column form with consistent field gaps |

### Settings hub
| Class | Description |
|---|---|
| `.settings-layout` | main two-column grid: sidebar + content panel |
| `.settings-sidebar-stack` | sticky vertical stack for multiple sidebar cards |
| `.settings-sidebar` | sticky card wrapper for settings navigation |
| `.settings-sidebar-logout` | compact card wrapper for logout action under nav sidebar |
| `.settings-logout-btn` | full-width borderless logout button with left-aligned icon + text inside logout sidebar card |
| `.settings-nav` | vertical nav list container inside sidebar |
| `.settings-nav-item` | single sidebar link row with icon + label and outlined default state |
| `.settings-nav-item--active` | active sidebar row with warm accent outline (tint only on hover) |
| `.settings-nav-sep` | horizontal divider between sidebar groups |
| `.settings-main` | right-column stack for screen cards and flash messages |
| `.settings-flash` | compact neutral status message block |
| `.settings-card` | settings content card wrapper |
| `.settings-card[id]` | adds top scroll margin for hash-anchor navigation under sticky nav |
| `.settings-card-body` | standard inner padding for settings card content |
| `.settings-card-body--palette` | extra padding variant for appearance/palette section |
| `.settings-stack` | vertical stack utility used in settings cards |
| `.settings-profile-head` | top row in profile card (name + friends count) |
| `.settings-stats-grid` | 2-column stat summary grid |
| `.settings-stat-cell` | bordered stat tile in the profile summary |
| `.settings-games-list` | vertical list for recent-game entries |
| `.settings-game-row` | row layout for thumbnail, metadata, and action button |
| `.settings-game-thumb` | blank thumbnail placeholder rectangle for past games |
| `.settings-game-meta` | stacked metadata block in each game row |
| `.settings-game-nav-link` | game-section sidebar link used for hash-based tab syncing |
| `.settings-game-link` | compact link-style action for opening a game record |
| `.settings-form` | form scope for non-textarea controls (select/range/number) |
| `.settings-slider` | themed range slider used for board size selection |
| `.settings-inline-form` | inline form wrapper for single-button actions |
| `.settings-delete-form` | spacing modifier for destructive account form |
| `.settings-palette-form` | stacked appearance form wrapper |
| `.settings-palette-grid` | 2x2 responsive grid of palette options |
| `.settings-palette-card` | selectable palette card/button with SVG preview |
| `.settings-palette-card--active` | selected palette card state |
| `.settings-link-list` | vertical list of legal/about links |
