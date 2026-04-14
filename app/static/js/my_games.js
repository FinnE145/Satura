'use strict';

// ── Palette helpers ───────────────────────────────────────────────────────────

const PRESET_ICONS = {
    '60':  'hourglass_top',
    '30':  'timer',
    '15':  'speed',
    '5':   'rocket',
    'custom': 'alarm_smart_wake',
};

function getCssVar(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

/** Read the active palette from body data attributes (same source as game.js). */
function getPalette() {
    const d = document.body.dataset;
    return {
        name: (d.activePalette || '').toLowerCase(),
        warm: (d.paletteWarm  || '#c87941').trim(),
        cool: (d.paletteCool  || '#5b8fbe').trim(),
    };
}

function hexToRgb(hex) {
    const h = hex.replace('#', '');
    return {
        r: parseInt(h.slice(0, 2), 16),
        g: parseInt(h.slice(2, 4), 16),
        b: parseInt(h.slice(4, 6), 16),
    };
}

// ── Board state helpers ───────────────────────────────────────────────────────

/**
 * Board is stored as [[p1, p2], ...] arrays (Python tuples → JSON arrays).
 */
function cellP1(cell) { return Array.isArray(cell) ? (cell[0] || 0) : 0; }
function cellP2(cell) { return Array.isArray(cell) ? (cell[1] || 0) : 0; }

/**
 * Classify a cell into one of 5 categories for the simple thumbnail view.
 */
function classifyCell(cell) {
    const p1 = cellP1(cell);
    const p2 = cellP2(cell);
    if (p1 === 0 && p2 === 0) return 'blank';
    if (p1 === 5 && p2 === 5) return 'black';
    if (p1 === p2)             return 'contested';
    if (p1 > p2)               return 'warm';
    return 'cool';
}

/**
 * Compute cell background colour using the exact same algorithm as game.js cellBg().
 * Two-phase blend: white → (warm↔cool mix) → black, based on total paint and p2 ratio.
 */
function cellBg(cell, palette) {
    const p1 = cellP1(cell);
    const p2 = cellP2(cell);
    const total = p1 + p2;

    if (total === 0)  return 'rgb(255, 255, 255)';
    if (total === 10) return 'rgb(0, 0, 0)';

    const c1 = hexToRgb(palette.warm);
    const c2 = hexToRgb(palette.cool);

    const t     = total / 10;
    const ratio = p2 / total;

    // Blend warm↔cool by p2 share
    const mid = {
        r: c1.r + ratio * (c2.r - c1.r),
        g: c1.g + ratio * (c2.g - c1.g),
        b: c1.b + ratio * (c2.b - c1.b),
    };

    let r, g, b;

    if (t <= 0.5) {
        // Phase 1: white → colour
        const s = t * 2;
        r = 255 + s * (mid.r - 255);
        g = 255 + s * (mid.g - 255);
        b = 255 + s * (mid.b - 255);
    } else {
        // Phase 2: colour → black
        let s = (t - 0.5) * 2;
        if (palette.name === 'fieldstone') s *= 0.7;

        r = mid.r * (1 - s);
        g = mid.g * (1 - s);
        b = mid.b * (1 - s);

        // Per-palette near-black brightness overrides (matches game.js exactly)
        let mult = 1;
        if (palette.name === 'solstice' || palette.name === 'levant') {
            if ((p1 === 4 && p2 === 5) || (p1 === 5 && p2 === 4)) mult = 1.35;
        } else if (palette.name === 'folio') {
            if ((p1 === 3 && p2 === 5) || (p1 === 4 && p2 === 4) || (p1 === 5 && p2 === 3)) mult = 1.2;
            if ((p1 === 4 && p2 === 5) || (p1 === 5 && p2 === 4)) mult = 1.6;
        }
        r *= mult;
        g *= mult;
        b *= mult;
    }

    const clamp = v => Math.round(Math.min(255, Math.max(0, v)));
    return `rgb(${clamp(r)}, ${clamp(g)}, ${clamp(b)})`;
}

// ── Board canvas rendering ────────────────────────────────────────────────────

/**
 * Draw a board canvas.
 * mode: 'full'   — exact game.js colour blend (featured cards)
 *       'simple' — 5-colour classification (list thumbnails)
 */
function renderBoardCanvas(canvas) {
    const boardJson = canvas.dataset.board;
    const size = parseInt(canvas.dataset.size, 10) || 6;
    const mode = canvas.dataset.mode || 'simple';

    if (!boardJson) return;

    let board;
    try {
        board = JSON.parse(boardJson);
    } catch (e) {
        console.warn('my_games: failed to parse board JSON', e);
        return;
    }

    const dpr = window.devicePixelRatio || 1;
    const px  = mode === 'simple' ? 64 : 512;

    canvas.width  = px * dpr;
    canvas.height = px * dpr;

    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);

    const cellSize = px / size;
    const palette  = getPalette();

    const SIMPLE_COLORS = {
        blank:     '#ffffff',
        warm:      palette.warm,
        cool:      palette.cool,
        contested: '#7a7672',
        black:     '#1a1917',
    };

    // Full mode: prefill with grid-line colour (navbar dark grey), then inset each cell by 0.5px.
    // Simple mode: integer-snap coordinates to eliminate sub-pixel gaps.
    const LINE_COLOR = getCssVar('--bg-header') || '#252321';
    if (mode === 'full') {
        ctx.fillStyle = LINE_COLOR;
        ctx.fillRect(0, 0, px, px);
    }

    for (let row = 0; row < size; row++) {
        for (let col = 0; col < size; col++) {
            const cell = (board[row] && board[row][col] !== undefined) ? board[row][col] : [0, 0];

            ctx.fillStyle = mode === 'full'
                ? cellBg(cell, palette)
                : SIMPLE_COLORS[classifyCell(cell)];

            if (mode === 'full') {
                ctx.fillRect(col * cellSize + 0.5, row * cellSize + 0.5, cellSize - 1, cellSize - 1);
            } else {
                const x1 = Math.round(col * cellSize);
                const y1 = Math.round(row * cellSize);
                const x2 = Math.round((col + 1) * cellSize);
                const y2 = Math.round((row + 1) * cellSize);
                ctx.fillRect(x1, y1, x2 - x1, y2 - y1);
            }
        }
    }
}

// ── Coverage bar rendering ────────────────────────────────────────────────────

function renderCoverageBar(bar) {
    const boardJson = bar.dataset.board;
    const size = parseInt(bar.dataset.size, 10) || 6;

    if (!boardJson) return;

    let board;
    try {
        board = JSON.parse(boardJson);
    } catch (e) {
        return;
    }

    const counts = { warm: 0, cool: 0, contested: 0, black: 0, blank: 0 };
    for (let row = 0; row < size; row++) {
        for (let col = 0; col < size; col++) {
            const cell = (board[row] && board[row][col] !== undefined) ? board[row][col] : [0, 0];
            counts[classifyCell(cell)]++;
        }
    }

    const total = size * size;
    bar.innerHTML = '';
    for (const key of ['warm', 'cool', 'contested', 'black', 'blank']) {
        if (counts[key] === 0) continue;
        const seg = document.createElement('div');
        seg.className = `coverage-segment coverage-segment--${key}`;
        seg.style.flexGrow = counts[key];
        seg.title = `${key}: ${counts[key]} / ${total} (${Math.round(counts[key] / total * 100)}%)`;
        bar.appendChild(seg);
    }
}

// ── Time control overlays ─────────────────────────────────────────────────────

function renderTcOverlay(el) {
    const preset   = el.dataset.preset;
    const clockRaw = parseInt(el.dataset.clock, 10);
    const icon     = PRESET_ICONS[preset];

    if (icon) {
        el.innerHTML = `<span class="material-symbols-outlined">${icon}</span>`;
    } else if (!isNaN(clockRaw) && clockRaw > 0) {
        el.textContent = `${Math.round(clockRaw / 60)}m`;
    } else {
        el.textContent = preset || '?';
    }
}

// ── Date filter ───────────────────────────────────────────────────────────────

function initDateFilter() {
    const label = document.getElementById('dateFilterLabel');
    const input = document.getElementById('dateFilterInput');
    const clear = document.getElementById('dateFilterClear');
    const rows  = Array.from(document.querySelectorAll('.game-timeline-row'));

    if (!label || !input || !clear) return;

    label.addEventListener('click', () => {
        label.hidden = true;
        input.hidden = false;
        clear.hidden = false;
        input.focus();
    });

    input.addEventListener('change', () => {
        const val = input.value;
        for (const row of rows) {
            row.hidden = Boolean(val && row.dataset.date !== val);
        }
    });

    clear.addEventListener('click', () => {
        input.hidden  = true;
        clear.hidden  = true;
        label.hidden  = false;
        input.value   = '';
        for (const row of rows) row.hidden = false;
    });
}

// ── Init ──────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    for (const canvas of document.querySelectorAll('.board-canvas')) {
        renderBoardCanvas(canvas);
    }
    for (const bar of document.querySelectorAll('.coverage-bar')) {
        renderCoverageBar(bar);
    }
    for (const el of document.querySelectorAll('.js-tc-overlay')) {
        renderTcOverlay(el);
    }
    initDateFilter();
});
