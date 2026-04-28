# CSS Class Index

Reference for all classes defined in `app/static/css/site.css`.
Update this file whenever a class is added, changed, or removed.

---

## Generic — reusable anywhere on the site

### Typography
| Class | Description |
|---|---|
| `.text-default` | full-white text (`--text`) — override a parent's dimmed colour |
| `.text-muted` | 50% opacity text — often hard to see, low contrast for minor details |
| `.text-dim` | 70% opacity text — secondary/supporting text |
| `.text-warm` | warm accent colour |
| `.text-warm-bright` | warm-bright accent colour |
| `.text-cool` | cool accent colour |
| `.text-cool-bright` | cool-bright accent colour |
| `.text-error` | error red colour |
| `.text-warn` | warning yellow colour |
| `.text-success` | success green colour |
| `.text-italic` | italic text |
| `.text-center` | `text-align: center` utility |
| `.text-small-sans` | 0.78em DM Sans — timestamps, metadata, disclaimers |
| `.text-sm` | 0.875em — secondary copy, dropdowns, supplementary labels |
| `.subheading` | italic Lora 0.9rem — taglines, subtitles, section intros |
| `.heading-display` | 2rem Lora 600 — large page or section headings |
| `.form-label` | 1em DM Sans 500, subtle colour — form field labels; compose with `.text-default` for white text |
| `.label` | 0.72em DM Sans, uppercase, wide tracking — category/section tags — compose with `.text-warm`, `.text-cool`, etc. for colour |

### Colour modifiers
Palette-driven triplet: tint background, coloured text, dim border. Apply alongside a component class to set its active/accent colour.
| Class | Description |
|---|---|
| `.warm` | Warm accent fill (tint bg, warm text, warm-dim border) |
| `.warm-bright` | Warm-bright accent fill — use on card backgrounds (tint bg, warm-bright text, warm-bright-dim border) |
| `.cool` | Cool accent fill (tint bg, cool text, cool-dim border) |
| `.cool-bright` | Cool-bright accent fill — use on card backgrounds (tint bg, cool-bright text, cool-bright-dim border) |

### Backgrounds
| Class | Description |
|---|---|
| `.bg-grey-dark` | `--bg-header` background (darkest) |
| `.bg-grey` | `--bg` background (page default) |
| `.bg-grey-light` | `--bg-card` background (lightest) |
| `.bg-grey-lighter` | hover tint / lighter accent background (`--bg-hover`) |
| `.bg-warm` | warm tint background (`--warm-tint`) |
| `.bg-cool` | cool tint background (`--cool-tint`) |
| `.bg-error` | error tint background (`--error-tint`) |
| `.bg-warn` | warning tint background (`--warn-tint`) |
| `.bg-success` | success tint background (`--success-tint`) |

### Hover utilities
| Class | Description |
|---|---|
| `.no-underline` | `text-decoration: none` utility — strips underline from links |
| `.warm-hover` | text transitions to warm accent on hover |
| `.cool-hover` | text transitions to cool accent on hover |
| `.warm-link` | warm accent colour at rest, warm-bright on hover — inline text links |
| `.cool-link` | cool accent colour at rest, cool-bright on hover — inline text links |

### Layout
| Class | Description |
|---|---|
| `.container` | 1440px max-width centred wrapper with horizontal padding |
| `.toggle-row` | bordered row for inline toggle controls and helper text |
| `.toggle-label` | inline checkbox + label treatment inside `.toggle-row` |
| `.split-grid` | responsive two-column sub-grid for paired player fields |
| `.seg-control` | segmented control — inline-flex group of options with shared border; options side by side |
| `.seg-control__opt` | one option inside `.seg-control` — muted text, highlights on hover |
| `.seg-control__opt--active` | active option — pair with `.warm` or `.cool` for accent colour |

### Flex utilities
Compose with component classes to provide layout without redundant CSS declarations in the component.
| Class | Description |
|---|---|
| `.flex-row` | `display: flex; align-items: center` — horizontal flex container |
| `.flex-col` | `display: flex; flex-direction: column` — vertical flex container |
| `.flex-1` | `flex: 1` — grow/shrink to fill available space |
| `.min-w-0` | `min-width: 0` — allows flex child to shrink below its content size (prevents overflow) |
| `.ml-auto` | `margin-left: auto` — pushes element to far right within a flex row |
| `.flex-shrink-0` | `flex-shrink: 0` — prevents a flex child from shrinking |
| `.self-start` | `align-self: flex-start` — keeps a flex item content-sized in a column layout |

### Forms
| Class | Description |
|---|---|
| `.form-stack` | flex column form — stacks `.field` elements vertically with gap, styles inputs/textareas (border, focus state), `margin-top: 2rem` |

### Buttons
Combine base `.btn` with one variant. Add `.btn--sm` for a smaller size.

| Class | Description |
|---|---|
| `.btn` | base button — inline-flex, DM Sans, rounded corners |
| `.btn--sm` | smaller size modifier (0.78em, tighter padding) |
| `.btn--ghost` | neutral grey border — low-priority or destructive actions |
| `.btn-warm-border` | warm border + text at rest, tint bg on hover — use outside cards (nav, standalone pages) |
| `.btn-cool-border` | cool border + text at rest, tint bg on hover — use outside cards (nav, standalone pages) |
| `.btn-warm-bright-border` | warm-bright border + text at rest, tint bg on hover — use inside `.card` |
| `.btn-cool-bright-border` | cool-bright border + text at rest, tint bg on hover — use inside `.card` |
| `.btn--warn` | warning-coloured border action (yellow) |
| `.btn--danger` | error-coloured border action (red) |
| `.btn-warm-hover` | border + tint fill transitions to warm accent on hover — used on non-`<button>` elements or composite components |
| `.btn-cool-hover` | border + tint fill transitions to cool accent on hover |
| `.btn-warn-hover` | border + tint fill transitions to warning yellow on hover |
| `.btn-danger-hover` | border + tint fill transitions to error red on hover |
| `.icon-btn` | stacked icon + label button — mode selectors, tool pickers |
| `.icon-btn-label` | tiny label below the icon inside `.icon-btn` |
| `.icon-btn.is-active` | selected-state modifier for `.icon-btn` — pair with `.warm` for colour |

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
| `.badge--ok` | neutral grey badge — neutral/in-progress status |
| `.badge--error` | red badge — error or failure state |
| `.badge--warn` | yellow badge — warning or draw result |
| `.badge--success` | green badge — success or win result |

### Feedback
| Class | Description |
|---|---|
| `.error-msg` | red-tinted box with border — form validation errors |
| `.info-msg` | layout base for an accented message box — pair with a colour modifier (`.warm`, `.cool`, etc.) |
| `.info-msg__url` | monospace URL span inside `.info-msg` — selects all text on click |
| `.empty-label` | small italic placeholder when a list or panel is empty |
| `.is-disabled` | generic disabled-state utility (reduced opacity); use with `a` for non-interactive disabled links |

### Prose
| Class | Description |
|---|---|
| `.prose` | centred 720px text container — long-form text, legal pages, contact; sets Lora body text with heading/list/table styles |

### Stat list
| Class | Description |
|---|---|
| `.stat-list` | two-column `<dl>` grid (dt label / dd value) — DM Sans 0.8em, muted uppercase dt |
| `.stat-list--responsive` | modifier: switches grid to `auto-fill minmax(10rem)` for wrapping across multiple columns |

### Stat grid
| Class | Description |
|---|---|
| `.stat-grid` | 2-column responsive grid of stat tiles (e.g. W/L/D summary on profile page) |
| `.stat-tile` | bordered stat tile inside `.stat-grid` — flex column, heading value on top, label beneath |

### Breadcrumb
| Class | Description |
|---|---|
| `.page-breadcrumb` | flex row breadcrumb nav — DM Sans 0.85em |
| `.page-breadcrumb__back` | back arrow + label link with warm hover |
| `.page-breadcrumb__sep` | separator glyph between crumbs |
| `.page-breadcrumb__current` | current page label (monospace, muted) |
| `.page-breadcrumb__action` | right-aligned action link (margin-left: auto, warm accent) |

### Action menu (reusable `...` dropdown)
| Class | Description |
|---|---|
| `.action-menu` | relative-positioned wrapper for a `...` trigger + dropdown panel |
| `.action-menu__btn` | borderless icon trigger button (subtle, highlights on hover) |
| `.action-menu__list` | absolute dropdown panel (`ul`) — positioned right-aligned below the button |
| `.action-menu__item` | full-width button row inside the dropdown |
| `.action-menu__item--danger` | red danger-state modifier for `.action-menu__item` |

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
| `.nav-center-slot` | `flex: 1` container between brand and nav-links — centers its single child in the blank space |
| `.nav-in-game` | link shown inside `.nav-center-slot` when the user is in an active game |
| `.nav-in-game-title` | "In game" label inside `.nav-in-game` |
| `.nav-in-game-phase` | phase + timer text below the title inside `.nav-in-game` |
| `.nav-game-invite` | link shown inside `.nav-center-slot` when the user has a pending game invite (cool accent, mutually exclusive with `.nav-in-game`) |
| `.nav-profile` | relative wrapper for the profile dropdown |
| `.nav-profile-btn` | icon button that opens/closes the dropdown |
| `.nav-dropdown` | absolute dropdown panel below the profile button |
| `.nav-dropdown-item` | link row inside the dropdown |

### Alt header (game page — no nav links)
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

### Game page layout
| Class | Description |
|---|---|
| `.game-outer` | flex row wrapper for the game page; centers sidebar + container as a group |
| `.game-container` | game-page content area — like `.container` but flex-child-friendly (no auto margin) |
| `.create-page-stack` | vertical stack wrapper for create/new-game style pages |
| `.create-form-grid` | responsive two-column form grid for core game-creation fields |
| `.create-form-footer` | `.card-footer` modifier — removes padding and left-aligns buttons |

### Game screen header
| Class | Description |
|---|---|
| `.game-header` | sticky-height header bar shown on the game screen in place of `.site-nav` — brand left, viewer count right |
| `.game-viewer-count` | muted eye icon + number showing active spectator count; hidden when count is 0 |
| `.seg-control` | see Generic — Layout |
| `.seg-control__opt--p1` | semantic slot for P1 option (no visual effect) |
| `.seg-control__opt--p2` | semantic slot for P2 option (no visual effect) |
| `.seg-control__opt--off` | semantic slot for Off option (no visual effect) |
| `.seg-control__opt--on` | semantic slot for On option (no visual effect) |

### Game page
| Class | Description |
|---|---|
| `.session-bar` | status bar at the bottom of the game page |
| `.session-bar-left` | left cluster inside `.session-bar` for session id and phase pill |
| `.status-dot` | small coloured indicator dot (use with a state modifier) |
| `.status-dot--ok` | green dot — ready/connected |
| `.status-dot--warn` | yellow dot — pending/loading |
| `.status-dot--error` | red dot — error state |
| `.session-bar-group` | flex group of related items within the session bar |
| `.session-bar-key` | tiny uppercase key label in the session bar |
| `.session-bar-sep` | non-selectable separator character between bar groups |
| `.session-clocks` | centered inline group showing both player clocks in the status row |
| `.session-clock` | individual player clock text inside `.session-clocks` |
| `.session-clock--p1` | warm-accent clock text for player 1 |
| `.session-clock--p2` | cool-accent clock text for player 2 |
| `.session-clock-sep` | separator dot between player clock texts |
| `.session-id` | monospace session UUID display |
| `.phase-pill-wrap` | full-width flex row wrapper around `.phase-pill`; used at 801–1080px to force the pill onto its own line while keeping the pill content-sized |
| `.phase-pill` | rounded pill showing the current game phase |
| `.phase-pill--p1` | semantic slot marker for P1 phases; pair with `.warm` for colour |
| `.phase-pill--p2` | semantic slot marker for P2 phases; pair with `.cool` for colour |
| `.phase-pill--write` | write-phase modifier — shifts to bright colour family when combined with `--p1`/`--p2` |
| `.script-history-card` | sticky sidebar card for script history; outside the container, shown only at ≥1700px |
| `.script-history-toggle` | toggle button in editor card header; shown only at <1700px to open/close the history panel |
| `.editor-card-body` | positioned flex wrapper for the editor textarea area; contains the small-screen history panel overlay |
| `.script-history-panel` | absolute overlay panel inside `.editor-card-body`; covers the editor on small screens when open |
| `.script-history-body` | scrollable body shared by sidebar card and small-screen panel; contains sections |
| `.script-history-section` | section grouping inside history body (e.g. "Past Scripts", "Functions") |
| `.script-history-section-title` | small label heading inside a `.script-history-section` |
| `.script-history-list` | flex column list of history items inside a section |
| `.script-history-item` | single clickable history entry (script or function); shows copy icon on hover |
| `.script-history-item__label-wrap` | flex column wrapper for label + args inside a history item |
| `.script-history-item__label` | primary text (turn number or function name) in a history item |
| `.script-history-item__args` | monospace argument list below the function label |
| `.script-history-item__copy` | clipboard icon at the right of a history item; visible on hover only |
| `.workspace` | 55/45 grid: script editor left, board right |
| `.editor-card` | flex column card wrapping the script editor |
| `.script-meta` | flex row showing word cost, ETA, and bank in the editor card header |
| `.word-cost` | word-count text in `.script-meta` |
| `.word-cost--active` | warm colour when words are actively being spent |
| `.word-eta` | ETA text in `.script-meta` |
| `.word-eta--waiting` | yellow colour while waiting for words to accrue |
| `.word-eta--ready` | subtle colour when word bank is sufficient |
| `.script-meta-sep` | non-selectable separator dot between script-meta groups |
| `.word-bank` | word-bank count display in `.script-meta` |
| `.script-editor` | full-height monospace textarea for script input |
| `.board-card` | flex column card wrapping the game board |
| `.board-card--solo` | modifier: board displayed without a side-by-side editor — constrains to max 1000px and centers |
| `.game-controls--solo` | modifier: game-controls row paired with a solo board — constrains to max 1000px and centers |
| `.board-legend` | flex row legend showing player board-coverage stats; stacks to column at ≤1080px |
| `.board-legend-pills` | flex row grouping the two ownership pill items within `.board-legend` |
| `.board-legend-item` | pill legend item showing player owned-cell count and board percentage |
| `.board-legend-item--p1` | semantic slot marker for P1 (no visual effect; colour via `.warm-bright`) |
| `.board-legend-item--p2` | semantic slot marker for P2 (no visual effect; colour via `.cool-bright`) |
| `.board-wrap` | padded inner container for the board grid |
| `.board-grid` | CSS grid of game board cells |
| `.board-cell` | individual board cell (background set via JS) |
| `.board-agent` | absolute circle overlay marking an agent's position |
| `.board-cell-tooltip` | fixed hover card showing per-cell paint levels; toggled with `--visible` |
| `.board-cell-tooltip--visible` | makes the tooltip opaque |
| `.board-cell-tooltip__p1` | P1 paint label inside tooltip (warm accent color) |
| `.board-cell-tooltip__p2` | P2 paint label inside tooltip (cool accent color) |
| `.results-row` | 2-column grid below the workspace for result cards |
| `.result-card` | card with a scrollable body for compiler/execution output |
| `.outcome-label` | small muted outcome summary line |
| `.diag-ok` | small green success message in the diagnostics panel |
| `.diag-item` | flex row for a single compiler diagnostic — compose with `.text-error` or `.text-warn` for severity colour |
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
| `.game-over-modal` | full-screen overlay wrapper for end-of-game popup |
| `.game-over-modal__backdrop` | dimmed click-to-dismiss backdrop behind popup card |
| `.game-over-modal__card` | centered modal card container |
| `.game-over-modal__body` | inner body padding wrapper for modal content |
| `.game-over-modal__message` | outcome message text for win/loss/stalemate popup |
| `.time-controls-card` | card shown at ≤800px containing both player clocks, badges, and phase pills; hidden at wider widths |
| `.active-time` | applied by JS to whichever time-control container is currently active (`#game-controls` at >800px, `#time-controls-card` at ≤800px); controls visibility of `.game-controls-side` children |
| `.game-controls` | card panel containing clocks, phase, and action buttons below the board |
| `.game-controls-main` | flex row inside the panel: mine side, buttons, opponent side |
| `.game-controls-side` | left/right info area holding badge, clock, and phase pill; hidden unless inside `.active-time` |
| `.game-controls-side--mine` | local player side (always left) |
| `.game-controls-side--opp` | opponent side (always right, right-aligned) |
| `.game-controls-btns` | flex row of action buttons (centered) |
| `.game-controls-btn` | borderless icon-stacked button inside the controls panel |
| `.game-controls-btn--draw` | draw-offer button modifier (warn hover) |
| `.game-controls-btn--resign` | resign button modifier (danger hover) |
| `.game-controls-confirm` | small confirmation prompt text below the panel main row |
| `.game-controls-draw-area` | flex row below the panel for draw offer status message and accept/reject buttons |
| `.game-controls-draw-btns` | flex row of accept/reject buttons inside `.game-controls-draw-area` |
| `.game-controls-btn--is-danger` | active-danger state modifier for `.game-controls-btn` — applies error colour without hover requirement |
| `.game-controls-btn--is-warm` | active-warm state marker for `.game-controls-btn` — pair with `.warm` for colour |
| `.gc-player-badge` | small coloured player label |
| `.gc-player-badge--p1` | semantic slot marker for P1 badge (no visual effect; colour via `.warm-bright`) |
| `.gc-player-badge--p2` | semantic slot marker for P2 badge (no visual effect; colour via `.cool-bright`) |
| `.gc-clock` | clock time display in the controls panel |

### Login page
| Class | Description |
|---|---|
| `.login-wrap` | centred narrow wrapper for the login form |
| `.login-card` | card containing the login form fields |
| `.login-footer` | spacing for the "create account" link below the login form |

### My Games page
| Class | Description |
|---|---|
| `.my-games-page` | full-width flex column page wrapper with vertical padding |
| `.my-games-featured` | flex row holding the two featured game cards (equal width, same height) |
| `.my-games-featured-card` | equal-flex featured game card; second one hides below 768px |
| `.featured-card-inner` | flex column inside a featured card (board top, stats below) |
| `.featured-board-area` | square aspect-ratio canvas container inside a featured card |
| `.featured-board-placeholder` | dark gradient fallback when board data is unavailable |
| `.featured-stats-area` | flex column for stats in the right panel of a featured card |
| `.featured-result-row` | flex row holding result badge + opponent name |
| `.featured-opponent` | opponent username; `[data-slot="1"]` = warm, `[data-slot="2"]` = cool |
| `.featured-reason` | muted end-reason line below result row |
| `.featured-clocks` | flex row of two player clock values |
| `.featured-clock` | single player clock with icon — colour via `.text-warm` or `.text-cool-bright` |
| `.stat-list` | see Generic — Stat list |
| `.featured-custom-section` | bordered sub-section for non-default game settings |
| `.coverage-bar` | horizontal flex bar split into 5 colour segments (warm/cool/contested/black/blank) |
| `.coverage-segment--warm` | warm-accent segment in a coverage bar |
| `.coverage-segment--cool` | cool-accent segment in a coverage bar |
| `.coverage-segment--contested` | grey segment — equal paint both sides |
| `.coverage-segment--black` | near-black segment — both players at max paint |
| `.coverage-segment--blank` | border-mid segment — unpainted cells |
| `.my-games-list-section` | flex column wrapper for date filter + timeline list |
| `.game-date-filter` | flex row holding date label, input, and clear button |
| `.date-filter-label` | "date" button label that expands into the input on click — typography via `.label .text-dim` |
| `.date-filter-input` | styled date input revealed on label click |
| `.date-filter-clear` | icon button to cancel date filtering |
| `.game-timeline` | flex column game list with a vertical rule `::before` pseudo-element |
| `.game-timeline-row` | two-column grid (date + row inner); full-row `<a>` link |
| `.game-timeline-date` | short `m/d` date label in the left column; background masks the vertical rule |
| `.game-row-inner` | three-column grid (thumb \| meta \| arrow) inside each timeline row |
| `.game-row-thumb` | 64×64 relative container for board canvas + overlays |
| `.game-row-thumb-placeholder` | dark fallback for rows without board data |
| `.thumb-overlay` | semi-transparent pill overlaid in a corner of the board thumb |
| `.thumb-overlay--bl` | bottom-left corner position (time control) |
| `.thumb-overlay--br` | bottom-right corner position (board size) |
| `.accom-dot` | small icon in the top-right corner of the thumb signalling custom accommodations |
| `.game-row-meta` | flex column for result line and end reason |
| `.game-row-result-line` | inline flex row holding result badge + opponent name on one line |
| `.game-row-opponent` | opponent username; `[data-slot="1"]` = warm, `[data-slot="2"]` = cool |
| `.game-row-reason` | muted end-reason text beneath the result line |
| `.game-row-arrow` | chevron that slides in on row hover |

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
| `.settings-nav-item--active` | active sidebar row — pair with `.btn-warm-bright-border` for hover colour |
| `.settings-nav-sep` | horizontal divider between sidebar groups |
| `.settings-main` | right-column stack for screen cards and flash messages |
| `.settings-flash` | compact neutral status message block |
| `.settings-card` | settings content card wrapper |
| `.settings-card[id]` | adds top scroll margin for hash-anchor navigation under sticky nav |
| `.settings-card-body` | standard inner padding for settings card content |
| `.settings-card-body--palette` | extra padding variant for appearance/palette section |
| `.settings-stack` | vertical stack utility used in settings cards |
| `.settings-profile-head` | top row in profile card (name + friends count) |
| `.settings-games-list` | vertical list for recent-game entries |
| `.settings-game-row` | row layout for thumbnail, metadata, and action button |
| `.settings-game-thumb` | blank thumbnail placeholder rectangle for past games |
| `.settings-game-meta` | stacked metadata block in each game row |
| `.settings-game-nav-link` | game-section sidebar link used for hash-based tab syncing |
| `.settings-game-link` | compact link-style action for opening a game record |
| `.settings-form` | form scope for non-textarea controls (select/range/number) |
| `.settings-slider` | themed range slider used for board size selection |
| `.settings-inline-form` | inline form wrapper for single-button actions |
| `.settings-palette-form` | stacked appearance form wrapper |
| `.settings-palette-grid` | 2x2 responsive grid of palette options |
| `.settings-palette-card` | selectable palette card/button with SVG preview — pair with `.btn-warm-hover` for hover colour |
| `.settings-palette-card--active` | semantic marker for the selected palette card — pair with `.warm` for colour (compound selector ensures `.warm` wins over the base card styles) |
| `.settings-link-list` | vertical list of legal/about links |

### Friends page
| Class | Description |
|---|---|
| `.friends-search-row` | flex row (stretch) wrapping the search field + add friend button; `form` child gets `display: flex` |
| `.friends-search-field` | relative-positioned, flex-fill wrapper for the search input; keeps the autocomplete anchored to the input |
| `.friends-search-results` | fixed-position autocomplete dropdown; top/left/width set via JS from the input's bounding rect |
| `.friends-search-result` | single result button inside the dropdown |
| `.friends-list` | `ul` — flex column list of friend/request rows, no list styling; `margin-top` provides gap after a preceding label |
| `.friend-item` | single row in `.friends-list` — `span:first-child` fills left (Lora, truncated), `:last-child` is the actions flex group |

### Join Enter page

| Class | Description |
|---|---|
| `.join-enter-wrap` | Narrow flex-column wrapper for the join code entry page (max 30em) |
| `.join-code-field` | Flex column wrapping the code row and the validation message |
| `.join-code-row` | Inline-flex container combining the URL prefix label and the text input |
| `.join-code-row--error` | Error-state modifier — red border on `.join-code-row` |
| `.join-code-prefix` | Read-only monospace prefix label (`satura.dev/join/`) inside the code row |
| `.join-code-input` | Monospace text input for the join code, flex-fills the remaining row width |
| `.join-code-msg` | Small error/status message rendered below the code row |

### Past Game Detail Page

| Class | Description |
|---|---|
| `.detail-page` | page-level flex column with gap and padding (wraps `.container`) |
| `.detail-stats-card` | stats-only card above the graphs — flex column |
| `.detail-graphs` | 3-column responsive grid containing the 3 chart cards |
| `.detail-graph-card` | individual chart card (min-width 0) |
| `.detail-graph-body` | fixed-height chart canvas wrapper (200px) |
| `.detail-funcs-body` | functions card body — flex column, list top / code bottom |
| `.detail-funcs-list` | scrollable top section of the functions panel (~40% height) |
| `.detail-funcs-code` | read-only code box at bottom of functions panel |
