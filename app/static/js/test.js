// ── DOM references ────────────────────────────────────────────────────────────

const statusDot      = document.getElementById('status-dot');
const sessionIdEl    = document.getElementById('session-id');
const sessionPhaseEl = document.getElementById('session-phase');
const wordBankEl     = document.getElementById('word-bank');
const wordCostEl     = document.getElementById('word-cost');
const wordEtaEl      = document.getElementById('word-eta');
const editor         = document.getElementById('script-editor');
const btnCompile     = document.getElementById('btn-compile');
const btnDeploy      = document.getElementById('btn-deploy');
const diagBadge      = document.getElementById('diag-badge');
const diagBody       = document.getElementById('diagnostics-body');
const outputBody     = document.getElementById('output-body');
const outcomeLabel   = document.getElementById('outcome-label');

// ── State ─────────────────────────────────────────────────────────────────────

let gameId              = null;
let bankPollTimer       = null;
let activePalette       = { name: 'solstice', warm: '#D2640E', cool: '#A82068' }; // Solstice default
let lastBoardState      = null;
let lastBank            = 0;
let lastRate            = 1 / 3;
let currentWordCount    = 0;
let sessionReady        = false;
let compileState        = null;   // null = dirty; {errors, warnings} = last compile result
let deployConfirmPending = false; // warnings shown, waiting for second click

// ── Word cost tokenizer ───────────────────────────────────────────────────────
// Mirrors WORD_COSTS in app/lang/tokens.py — every match costs 1 word.

const COSTLY_RE = /\b(?:if|elif|else|for|while|halt|return|def|call|and|or|not|min|max|range|index|length|push|pop|move|paint|get_friction|has_agent|my_paint|opp_paint)\b|\$|==|!=|<=|>=|[+\-*\/%<>]|=/g;

function countWords(src) {
    return (src.match(COSTLY_RE) ?? []).length;
}

// ── Boot ──────────────────────────────────────────────────────────────────────

async function init() {
    setStatus('pending');
    setPhase('initialising');
    setSessionReady(false);

    try {
        const data = await post('/test/session');
        gameId = data.game_id;
        sessionIdEl.textContent = gameId.slice(0, 8) + '\u2026';
        sessionIdEl.title = gameId;
        setStatus('ready');
        setPhase('write', true);
        setSessionReady(true);
        startBankPoll();

        // Show blank board on first load
        const initState = await get(`/games/${gameId}/state`);
        renderBoard(initState);
    } catch (e) {
        setStatus('error');
        setPhase('error');
        sessionIdEl.textContent = 'failed to initialise';
    }
}

// ── Word bank polling ─────────────────────────────────────────────────────────

function startBankPoll() {
    if (bankPollTimer) clearInterval(bankPollTimer);
    refreshBank();
    bankPollTimer = setInterval(refreshBank, 2000);
}

async function refreshBank() {
    if (!gameId) return;
    try {
        const state = await get(`/games/${gameId}/state`);
        const bank  = state.word_bank?.[1] ?? 0;
        lastBank = bank;
        lastRate = state.word_rate ?? (1 / 3);
        wordBankEl.innerHTML = `<strong>${Math.floor(bank)}</strong> words in bank`;
        setPhase(state.phase, state.phase === 'write');
        updateWordEta();
        updateDeployButton();
        updateWordShortageNotice();
    } catch (_) {
        // ignore transient poll failures
    }
}

// ── Compile ───────────────────────────────────────────────────────────────────

btnCompile.addEventListener('click', async () => {
    if (!gameId) return;
    setBothButtonsDisabled(true);
    clearDiagnostics();

    try {
        const result = await runCompile();
        renderDiagnostics(result);
    } catch (e) {
        renderNetworkError(diagBadge, diagBody, e.message);
    } finally {
        setBothButtonsDisabled(false);
        updateDeployButton();
        updateWordShortageNotice();
    }
});

async function runCompile() {
    const data = await post(`/games/${gameId}/compile`, {
        player: 1,
        source: editor.value,
    });
    compileState        = { errors: data.errors ?? [], warnings: data.warnings ?? [] };
    deployConfirmPending = false;
    return data;
}

// ── Deploy ────────────────────────────────────────────────────────────────────

btnDeploy.addEventListener('click', async () => {
    if (!gameId) return;
    setBothButtonsDisabled(true);

    try {
        // Step 1: compile if dirty
        if (compileState === null) {
            clearDiagnostics();
            const result = await runCompile();

            if (compileState.errors.length > 0) {
                // Errors — show and block
                renderDiagnostics(result);
                return;
            }

            if (compileState.warnings.length > 0) {
                // Warnings — show with confirm prompt, wait for second click
                renderDiagnostics(result, /*confirmPrompt=*/true);
                deployConfirmPending = true;
                return;
            }
            // Clean — fall through to deploy
        } else if (deployConfirmPending) {
            // Second click after warnings — proceed
        } else if (compileState.errors.length > 0) {
            // Should not reach here (button is disabled), but guard anyway
            return;
        }

        // Step 2: deploy
        clearOutput();
        const data = await post(`/games/${gameId}/deploy`, {
            player: 1,
            source: editor.value,
        });

        if (!data.ok) {
            // Server-side compile failure (race condition / shouldn't normally happen)
            compileState = { errors: data.errors ?? [], warnings: data.warnings ?? [] };
            deployConfirmPending = false;
            clearDiagnostics();
            renderDiagnostics(data);
            return;
        }

        compileState         = null;
        deployConfirmPending = false;

        // Fetch exec log, territory, and board from game state
        const state = await get(`/games/${gameId}/state`);
        renderOutput(state);
        renderBoard(state);

        // Reset to a fresh session so the user can test again immediately
        await resetSession();
    } catch (e) {
        renderNetworkError(diagBadge, diagBody, e.message);
    } finally {
        setBothButtonsDisabled(false);
        updateDeployButton();
        updateWordShortageNotice();
    }
});

async function resetSession() {
    clearInterval(bankPollTimer);
    gameId = null;
    compileState         = null;
    deployConfirmPending = false;

    setStatus('pending');
    setPhase('resetting');
    setSessionReady(false);
    wordBankEl.textContent = '';

    // Brief pause so the "resetting" state is visible
    await delay(600);

    try {
        const data = await post('/test/session');
        gameId = data.game_id;
        sessionIdEl.textContent = gameId.slice(0, 8) + '\u2026';
        sessionIdEl.title = gameId;
        setStatus('ready');
        setPhase('write', true);
        setSessionReady(true);
        startBankPoll();
    } catch (e) {
        setStatus('error');
        setPhase('error');
        sessionIdEl.textContent = 'failed to reset';
    }
}

// ── Compile button state ──────────────────────────────────────────────────────

editor.addEventListener('input', () => {
    const src        = editor.value;
    const hasContent = src.trim().length > 0;
    btnCompile.classList.toggle('btn--ghost',     !hasContent);
    btnCompile.classList.toggle('btn--secondary',  hasContent);

    currentWordCount     = countWords(src);
    compileState         = null;
    deployConfirmPending = false;

    const wc = currentWordCount;
    wordCostEl.textContent = wc > 0 ? `${wc} word${wc !== 1 ? 's' : ''}` : '';
    wordCostEl.className   = wc > 0 ? 'word-cost word-cost--active' : 'word-cost';
    updateWordEta();
    updateDeployButton();
    updateWordShortageNotice();
});

function updateWordEta() {
    const cost = currentWordCount;
    if (cost === 0) {
        wordEtaEl.textContent = '';
        wordEtaEl.className   = 'word-eta';
        return;
    }
    if (lastBank >= cost) {
        wordEtaEl.textContent = 'ready';
        wordEtaEl.className   = 'word-eta word-eta--ready';
        return;
    }
    if (lastRate <= 0) {
        wordEtaEl.textContent = '';
        wordEtaEl.className   = 'word-eta';
        return;
    }
    const secs = Math.ceil((cost - lastBank) / lastRate);
    wordEtaEl.textContent = secs < 60 ? `~${secs}s` : `~${Math.ceil(secs / 60)}m`;
    wordEtaEl.className   = 'word-eta word-eta--waiting';
}

// ── Tab key support in editor ─────────────────────────────────────────────────

editor.addEventListener('keydown', (e) => {
    if (e.key === 'Tab') {
        e.preventDefault();
        const start = editor.selectionStart;
        const end   = editor.selectionEnd;
        editor.value =
            editor.value.slice(0, start) + '    ' + editor.value.slice(end);
        editor.selectionStart = editor.selectionEnd = start + 4;
    }
});

// ── Render helpers ────────────────────────────────────────────────────────────

function clearDiagnostics() {
    diagBadge.textContent = '';
    diagBadge.className   = 'badge';
    diagBody.innerHTML    = '<span class="empty-label">No diagnostics</span>';
}

function clearOutput() {
    outcomeLabel.textContent = '';
    outputBody.innerHTML     = '<span class="empty-label">No output yet</span>';
}

function renderDiagnostics(data, confirmPrompt = false) {
    const errors   = data.errors   ?? [];
    const warnings = data.warnings ?? [];
    const total    = errors.length + warnings.length;

    diagBody.innerHTML = '';

    if (total === 0) {
        diagBadge.textContent = 'OK';
        diagBadge.className   = 'badge badge--ok';
        diagBody.appendChild(el('div', 'diag-ok', 'Compiled successfully.'));
    } else {
        diagBadge.textContent = String(total);
        diagBadge.className   = errors.length > 0 ? 'badge badge--error' : 'badge badge--warn';
        errors.forEach(msg => diagBody.appendChild(diagItem('error', msg)));
        warnings.forEach(msg => diagBody.appendChild(diagItem('warn', msg)));
        if (confirmPrompt) {
            diagBody.appendChild(diagItem('warn', 'Warnings found — click Deploy again to proceed anyway.'));
        }
    }

    // Re-attach word shortage notice below compile results
    updateWordShortageNotice();
}

function updateWordShortageNotice() {
    const existing = document.getElementById('diag-word-shortage');
    if (existing) existing.remove();

    if (currentWordCount > 0 && lastBank < currentWordCount) {
        const needed = currentWordCount - Math.floor(lastBank);
        const secs   = lastRate > 0 ? Math.ceil((currentWordCount - lastBank) / lastRate) : null;
        const eta    = secs != null ? (secs < 60 ? ` (~${secs}s)` : ` (~${Math.ceil(secs / 60)}m)`) : '';
        const notice = diagItem('warn', `Not enough words — need ${needed} more${eta}.`);
        notice.id = 'diag-word-shortage';
        // Insert at top if diagnostics body only has the empty label, else append
        const emptyLabel = diagBody.querySelector('.empty-label');
        if (emptyLabel) {
            diagBody.innerHTML = '';
        }
        diagBody.appendChild(notice);
    }
}

function diagItem(type, msg) {
    const icon = type === 'error' ? '\u2715' : '\u26a0';
    const div  = document.createElement('div');
    div.className = `diag-item diag-item--${type}`;
    div.innerHTML =
        `<span class="diag-icon">${icon}</span>` +
        `<span class="diag-msg">${esc(String(msg))}</span>`;
    return div;
}

function renderNetworkError(badge, body, msg) {
    badge.textContent = '!';
    badge.className   = 'badge badge--error';
    body.innerHTML    = '';
    body.appendChild(diagItem('error', 'Network error: ' + msg));
}

function renderOutput(state) {
    const log = state.exec_log ?? [];

    if (log.length === 0) {
        outcomeLabel.textContent = 'no ops';
        outputBody.innerHTML     = '';
        outputBody.appendChild(el('span', 'empty-label',
            'Script executed with no board operations.'));
        return;
    }

    const consumed = state.exec_ops_consumed ?? log.length;
    const limit    = state.op_limit ?? '?';
    outcomeLabel.textContent = `${consumed} / ${limit} ops`;
    outputBody.innerHTML     = '';

    log.forEach((entry, i) => {
        const row = document.createElement('div');
        row.className   = 'log-entry';
        row.innerHTML   =
            `<span class="log-idx">${String(i + 1).padStart(2, '0')}</span>` +
            formatLogEntry(entry);
        outputBody.appendChild(row);
    });

    // Territory summary
    if (state.territory) {
        const t   = state.territory;
        outputBody.appendChild(el('div', 'log-sep', ''));
        outputBody.appendChild(el('div', 'log-summary',
            `P1\u00a0${t.p1}\u2002\u00b7\u2002P2\u00a0${t.p2}\u2002\u00b7\u2002Black\u00a0${t.black}\u2002\u00b7\u2002Total\u00a0${t.total}`
        ));
    }
}

function formatLogEntry(entry) {
    const at = entry.at ? `(${entry.at[1]},\u202f${entry.at[0]})` : '';
    const to = entry.to ? `(${entry.to[1]},\u202f${entry.to[0]})` : '';

    switch (entry.op) {
        case 'halt':
            return op('halt', '');
        case 'reset':
            return op('reset', '');
        case 'move':
            return op('move', `\u2192 ${to}`);
        case 'paint':
            return op('paint', `+${entry.amount} at ${at}`);
        case 'get_friction':
            return op('query', `get_friction ${at} = ${fmtResult(entry.result)}`, 'get_friction');
        case 'has_agent':
            return op('query', `has_agent ${at} = ${fmtResult(entry.result)}`, 'has_agent');
        case 'my_paint':
            return op('query', `my_paint ${at} = ${fmtResult(entry.result)}`, 'my_paint');
        case 'opp_paint':
            return op('query', `opp_paint ${at} = ${fmtResult(entry.result)}`, 'opp_paint');
        default:
            return op('', esc(JSON.stringify(entry)), entry.op);
    }
}

function op(cssType, detail, label) {
    const opLabel = label ?? cssType;
    const cls     = cssType ? `log-op log-op--${cssType}` : 'log-op';
    return `<span class="${cls}">${esc(opLabel)}</span>` +
           `<span class="log-detail">${detail}</span>`;
}

function fmtResult(v) {
    return v == null ? '<span style="opacity:.5">null</span>' : String(v);
}

// ── Board rendering ───────────────────────────────────────────────────────────

const boardGrid = document.getElementById('board-grid');

function hexToRgb(hex) {
    return {
        r: parseInt(hex.slice(1, 3), 16),
        g: parseInt(hex.slice(3, 5), 16),
        b: parseInt(hex.slice(5, 7), 16),
    };
}

function cellBg(cell) {
    const { p1, p2 } = cell;
    const total = p1 + p2;

    if (total === 0)  return 'rgb(255, 255, 255)';
    if (total === 10) return 'rgb(0, 0, 0)';

    const c1 = hexToRgb(activePalette.warm);
    const c2 = hexToRgb(activePalette.cool);

    const t     = total / 10;
    const ratio = p2 / total;

    // mid: blend between c1 and c2 by p2 ratio
    const mid = {
        r: c1.r + ratio * (c2.r - c1.r),
        g: c1.g + ratio * (c2.g - c1.g),
        b: c1.b + ratio * (c2.b - c1.b),
    };

    let r, g, b;

    if (t <= 0.5) {
        // White → colour phase
        const s = t * 2;
        r = 255 + s * (mid.r - 255);
        g = 255 + s * (mid.g - 255);
        b = 255 + s * (mid.b - 255);
    } else {
        // Colour → black phase
        let s = (t - 0.5) * 2;
        if (activePalette.name === 'fieldstone') s *= 0.7;

        r = mid.r * (1 - s);
        g = mid.g * (1 - s);
        b = mid.b * (1 - s);

        // Per-palette near-black overrides
        let mult = 1;
        const pal = activePalette.name;
        if (pal === 'solstice' || pal === 'levant') {
            if ((p1 === 4 && p2 === 5) || (p1 === 5 && p2 === 4)) mult = 1.35;
        } else if (pal === 'folio') {
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

function renderBoard(state) {
    lastBoardState = state;
    const board  = state.board;
    const agents = state.agents;
    const size   = board.length;

    boardGrid.style.gridTemplateColumns = `repeat(${size}, 1fr)`;
    boardGrid.innerHTML = '';

    for (let r = 0; r < size; r++) {
        for (let c = 0; c < size; c++) {
            const cell = document.createElement('div');
            cell.className = 'board-cell';
            cell.style.background = cellBg(board[r][c]);

            // P1 agent
            if (agents['1']?.row === r && agents['1']?.col === c) {
                const dot = document.createElement('div');
                dot.className = 'board-agent';
                dot.style.background = activePalette.warm;
                cell.appendChild(dot);
            }
            // P2 agent
            if (agents['2']?.row === r && agents['2']?.col === c) {
                const dot = document.createElement('div');
                dot.className = 'board-agent';
                dot.style.background = activePalette.cool;
                cell.appendChild(dot);
            }

            boardGrid.appendChild(cell);
        }
    }
}

// ── Status helpers ────────────────────────────────────────────────────────────

function setStatus(state) {
    statusDot.className = `status-dot status-dot--${state}`;
}

function setPhase(text, highlight = false) {
    sessionPhaseEl.textContent = text;
    sessionPhaseEl.className   = highlight ? 'phase-pill phase-pill--write' : 'phase-pill';
}

function setSessionReady(on) {
    sessionReady        = on;
    btnCompile.disabled = !on;
    updateDeployButton();
}

function setBothButtonsDisabled(disabled) {
    btnCompile.disabled = disabled;
    btnDeploy.disabled  = disabled;
}

function updateDeployButton() {
    const hasErrors    = compileState !== null && compileState.errors.length > 0;
    const wordsShort   = currentWordCount > 0 && lastBank < currentWordCount;
    btnDeploy.disabled = !sessionReady || hasErrors || wordsShort;
}

// ── Tiny utilities ────────────────────────────────────────────────────────────

function el(tag, className, text) {
    const node = document.createElement(tag);
    node.className   = className;
    node.textContent = text;
    return node;
}

function esc(str) {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

async function post(url, body) {
    const opts = { method: 'POST' };
    if (body !== undefined) {
        opts.headers = { 'Content-Type': 'application/json' };
        opts.body    = JSON.stringify(body);
    }
    const resp = await fetch(url, opts);
    if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.error ?? `HTTP ${resp.status}`);
    }
    return resp.json();
}

async function get(url) {
    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return resp.json();
}

function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// ── Palette ───────────────────────────────────────────────────────────────────

const brandMark    = document.querySelector('.brand-mark');
const paletteBtns  = document.querySelectorAll('.palette-btn');

function hexToRgba(hex, alpha) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function hexToHsl(hex) {
    let r = parseInt(hex.slice(1, 3), 16) / 255;
    let g = parseInt(hex.slice(3, 5), 16) / 255;
    let b = parseInt(hex.slice(5, 7), 16) / 255;
    const max = Math.max(r, g, b), min = Math.min(r, g, b);
    const l = (max + min) / 2;
    if (max === min) return [0, 0, l * 100];
    const d = max - min;
    const s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    let h = max === r ? (g - b) / d + (g < b ? 6 : 0)
          : max === g ? (b - r) / d + 2
          :             (r - g) / d + 4;
    return [h / 6 * 360, s * 100, l * 100];
}

function hslToHex(h, s, l) {
    h /= 360; s /= 100; l /= 100;
    const hue2rgb = (p, q, t) => {
        if (t < 0) t += 1;
        if (t > 1) t -= 1;
        if (t < 1 / 6) return p + (q - p) * 6 * t;
        if (t < 1 / 2) return q;
        if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
        return p;
    };
    let r, g, b;
    if (s === 0) {
        r = g = b = l;
    } else {
        const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
        const p = 2 * l - q;
        r = hue2rgb(p, q, h + 1 / 3);
        g = hue2rgb(p, q, h);
        b = hue2rgb(p, q, h - 1 / 3);
    }
    const toHex = x => Math.round(x * 255).toString(16).padStart(2, '0');
    return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
}

function brighten(hex, amount = 18) {
    const [h, s, l] = hexToHsl(hex);
    return hslToHex(h, s, Math.min(l + amount, 92));
}

function applyPalette(btn) {
    const warm = btn.dataset.warm;
    const cool = btn.dataset.cool;
    activePalette = { name: btn.dataset.palette, warm, cool };
    const root = document.documentElement;

    const warmBright = brighten(warm);
    const coolBright = brighten(cool);

    root.style.setProperty('--accent',          warm);
    root.style.setProperty('--accent-tint',     hexToRgba(warm, 0.10));
    root.style.setProperty('--accent-dim',      hexToRgba(warm, 0.65));
    root.style.setProperty('--accent-cool',     cool);
    root.style.setProperty('--accent-cool-dim',  hexToRgba(cool, 0.65));
    root.style.setProperty('--accent-cool-tint', hexToRgba(cool, 0.10));

    root.style.setProperty('--accent-bright',           warmBright);
    root.style.setProperty('--accent-bright-dim',       hexToRgba(warmBright, 0.65));
    root.style.setProperty('--accent-bright-tint',      hexToRgba(warmBright, 0.10));
    root.style.setProperty('--accent-cool-bright',      coolBright);
    root.style.setProperty('--accent-cool-bright-dim',  hexToRgba(coolBright, 0.65));
    root.style.setProperty('--accent-cool-bright-tint', hexToRgba(coolBright, 0.10));

    // Swap the header logo mark to match
    brandMark.src = btn.querySelector('.palette-mark').src;

    // Re-render board with new palette colours
    if (lastBoardState) renderBoard(lastBoardState);

    // Update button active states
    paletteBtns.forEach(b => {
        const active = b === btn;
        b.style.borderColor  = active ? warm : '';
        b.style.background   = active ? hexToRgba(warm, 0.10) : '';
        b.style.color        = active ? warm : '';
    });
}

paletteBtns.forEach(btn => btn.addEventListener('click', () => applyPalette(btn)));

// Apply Solstice on load
applyPalette(document.querySelector('[data-palette="solstice"]'));

// ── Start ─────────────────────────────────────────────────────────────────────

init();
