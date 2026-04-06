// ── DOM references ────────────────────────────────────────────────────────────

const statusDot = document.getElementById('status-dot');
const sessionIdEl = document.getElementById('session-id');
const sessionPhaseEl = document.getElementById('session-phase');
const wordBankEl = document.getElementById('word-bank');
const wordCostEl = document.getElementById('word-cost');
const wordEtaEl = document.getElementById('word-eta');
const editor = document.getElementById('script-editor');
const btnCompile = document.getElementById('btn-compile');
const btnDeploy = document.getElementById('btn-deploy');
const diagBadge = document.getElementById('diag-badge');
const diagBody = document.getElementById('diagnostics-body');
const outputBody = document.getElementById('output-body');
const outcomeLabel = document.getElementById('outcome-label');

// ── State ─────────────────────────────────────────────────────────────────────

let gameId = null;
let bankPollTimer = null;
const fallbackPalette = { name: 'solstice', warm: '#D2640E', cool: '#A82068' };
const bodyPalette = document.body?.dataset;
let activePalette = {
    name: bodyPalette?.activePalette || fallbackPalette.name,
    warm: bodyPalette?.paletteWarm || fallbackPalette.warm,
    cool: bodyPalette?.paletteCool || fallbackPalette.cool,
};
let lastBoardState = null;
let lastBank = 0;
let lastRate = 1 / 3;
let currentWordCount = 0;
let sessionReady = false;
let compileState = null;   // null = dirty; {errors, warnings} = last compile result
let deployConfirmPending = false; // warnings shown, waiting for second click
const STEP_DELAY_MS = 500;

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

        // Show the latest board and actual server phase immediately.
        const initState = await get(`/games/${gameId}/state`);
        applySessionState(initState);
        renderBoard(initState);

        startBankPoll();
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
        const bank = state.word_bank?.[1] ?? 0;
        lastBank = bank;
        lastRate = state.word_rate ?? (1 / 3);
        wordBankEl.innerHTML = `<strong>${Math.floor(bank)}</strong> words in bank`;
        applySessionState(state);
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
    compileState = { errors: data.errors ?? [], warnings: data.warnings ?? [] };
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
        const preExecState = cloneBoardAndAgents(lastBoardState);
        setPhase('exec1');
        setSessionReady(false);

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
            // If deploy is rejected, remain in write phase.
            setPhase('write', true);
            setSessionReady(true);
            return;
        }

        compileState = null;
        deployConfirmPending = false;

        // Fetch exec log, territory, and board from game state
        const state = await get(`/games/${gameId}/state`);
        applySessionState(state);
        await replayExecution(preExecState, state, 1);

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
    compileState = null;
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

        const initState = await get(`/games/${gameId}/state`);
        applySessionState(initState);
        renderBoard(initState);

        startBankPoll();
    } catch (e) {
        setStatus('error');
        setPhase('error');
        sessionIdEl.textContent = 'failed to reset';
    }
}

// ── Compile button state ──────────────────────────────────────────────────────

editor.addEventListener('input', () => {
    const src = editor.value;
    const hasContent = src.trim().length > 0;
    btnCompile.classList.toggle('btn--ghost', !hasContent);
    btnCompile.classList.toggle('btn--secondary', hasContent);

    currentWordCount = countWords(src);
    compileState = null;
    deployConfirmPending = false;

    const wc = currentWordCount;
    wordCostEl.textContent = wc > 0 ? `${wc} word${wc !== 1 ? 's' : ''}` : '';
    wordCostEl.className = wc > 0 ? 'word-cost word-cost--active' : 'word-cost';
    updateWordEta();
    updateDeployButton();
    updateWordShortageNotice();
});

function updateWordEta() {
    const cost = currentWordCount;
    if (cost === 0) {
        wordEtaEl.textContent = '';
        wordEtaEl.className = 'word-eta';
        return;
    }
    if (lastBank >= cost) {
        wordEtaEl.textContent = 'ready';
        wordEtaEl.className = 'word-eta word-eta--ready';
        return;
    }
    if (lastRate <= 0) {
        wordEtaEl.textContent = '';
        wordEtaEl.className = 'word-eta';
        return;
    }
    const secs = Math.ceil((cost - lastBank) / lastRate);
    wordEtaEl.textContent = secs < 60 ? `~${secs}s` : `~${Math.ceil(secs / 60)}m`;
    wordEtaEl.className = 'word-eta word-eta--waiting';
}

// ── Tab key support in editor ─────────────────────────────────────────────────

editor.addEventListener('keydown', (e) => {
    if (e.key === 'Tab') {
        e.preventDefault();
        const start = editor.selectionStart;
        const end = editor.selectionEnd;
        editor.value =
            editor.value.slice(0, start) + '    ' + editor.value.slice(end);
        editor.selectionStart = editor.selectionEnd = start + 4;
    }
});

// ── Render helpers ────────────────────────────────────────────────────────────

function clearDiagnostics() {
    diagBadge.textContent = '';
    diagBadge.className = 'badge';
    diagBody.innerHTML = '<span class="empty-label">No diagnostics</span>';
}

function clearOutput() {
    outcomeLabel.textContent = '';
    outputBody.innerHTML = '<span class="empty-label">No output yet</span>';
}

function renderDiagnostics(data, confirmPrompt = false) {
    const errors = data.errors ?? [];
    const warnings = data.warnings ?? [];
    const total = errors.length + warnings.length;

    diagBody.innerHTML = '';

    if (total === 0) {
        diagBadge.textContent = 'OK';
        diagBadge.className = 'badge badge--ok';
        diagBody.appendChild(el('div', 'diag-ok', 'Compiled successfully.'));
    } else {
        diagBadge.textContent = String(total);
        diagBadge.className = errors.length > 0 ? 'badge badge--error' : 'badge badge--warn';
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
        const secs = lastRate > 0 ? Math.ceil((currentWordCount - lastBank) / lastRate) : null;
        const eta = secs != null ? (secs < 60 ? ` (~${secs}s)` : ` (~${Math.ceil(secs / 60)}m)`) : '';
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
    const div = document.createElement('div');
    div.className = `diag-item diag-item--${type}`;
    div.innerHTML =
        `<span class="diag-icon">${icon}</span>` +
        `<span class="diag-msg">${esc(String(msg))}</span>`;
    return div;
}

function renderNetworkError(badge, body, msg) {
    badge.textContent = '!';
    badge.className = 'badge badge--error';
    body.innerHTML = '';
    body.appendChild(diagItem('error', 'Network error: ' + msg));
}

function renderOutput(state) {
    const log = state.exec_log ?? [];

    if (log.length === 0) {
        outcomeLabel.textContent = 'no ops';
        outputBody.innerHTML = '';
        outputBody.appendChild(el('span', 'empty-label',
            'Script executed with no board operations.'));
        return;
    }

    const consumed = state.exec_ops_consumed ?? log.length;
    const limit = state.op_limit ?? '?';
    outcomeLabel.textContent = `${consumed} / ${limit} ops`;
    outputBody.innerHTML = '';

    log.forEach((entry, i) => {
        const row = document.createElement('div');
        row.className = 'log-entry';
        row.innerHTML =
            `<span class="log-idx">${String(i + 1).padStart(2, '0')}</span>` +
            formatLogEntry(entry);
        outputBody.appendChild(row);
    });

    // Territory summary
    if (state.territory) {
        const t = state.territory;
        outputBody.appendChild(el('div', 'log-sep', ''));
        outputBody.appendChild(el('div', 'log-summary',
            `P1\u00a0${t.p1}\u2002\u00b7\u2002P2\u00a0${t.p2}\u2002\u00b7\u2002Black\u00a0${t.black}\u2002\u00b7\u2002Total\u00a0${t.total}`
        ));
    }
}

async function replayExecution(preExecState, postExecState, actorPlayer = 1) {
    if (!preExecState) {
        renderOutput(postExecState);
        renderBoard(postExecState);
        return;
    }

    const replayBase = cloneBoardAndAgents(preExecState);
    const replayState = cloneBoardAndAgents(preExecState);

    renderBoard(replayState);
    await renderOutputStepByStep(postExecState, async (entry) => {
        const opDelta = estimateOpCost(entry, replayState, actorPlayer);
        applyOperationToReplayState(replayState, entry, replayBase, actorPlayer);
        renderBoard(replayState);
        return opDelta;
    });

    // Ensure exact parity with server-authoritative final state.
    renderBoard(postExecState);
}

async function renderOutputStepByStep(state, onStep) {
    const log = state.exec_log ?? [];

    if (log.length === 0) {
        outcomeLabel.textContent = 'no ops';
        outputBody.innerHTML = '';
        outputBody.appendChild(el('span', 'empty-label',
            'Script executed with no board operations.'));
        return;
    }

    const consumed = state.exec_ops_consumed ?? log.length;
    const limit = state.op_limit ?? '?';
    let displayedOps = 0;
    outcomeLabel.textContent = `${displayedOps} / ${limit} ops`;
    outputBody.innerHTML = '';

    for (let i = 0; i < log.length; i++) {
        const entry = log[i];
        if (!isInstantSensingOp(entry)) {
            await delay(STEP_DELAY_MS);
        }

        const row = document.createElement('div');
        row.className = 'log-entry';
        row.innerHTML =
            `<span class="log-idx">${String(i + 1).padStart(2, '0')}</span>` +
            formatLogEntry(entry);
        outputBody.appendChild(row);

        if (onStep) {
            const delta = await onStep(entry, i);
            if (Number.isFinite(delta) && delta > 0) {
                displayedOps = Math.min(consumed, displayedOps + delta);
                outcomeLabel.textContent = `${displayedOps} / ${limit} ops`;
            }
        }
    }

    // Snap to authoritative total in case stepwise estimates differ.
    outcomeLabel.textContent = `${consumed} / ${limit} ops`;

    if (state.territory) {
        const t = state.territory;
        outputBody.appendChild(el('div', 'log-sep', ''));
        outputBody.appendChild(el('div', 'log-summary',
            `P1\u00a0${t.p1}\u2002\u00b7\u2002P2\u00a0${t.p2}\u2002\u00b7\u2002Black\u00a0${t.black}\u2002\u00b7\u2002Total\u00a0${t.total}`
        ));
    }
}

function isInstantSensingOp(entry) {
    if (!entry || !entry.op) return false;
    return entry.op === 'get_friction'
        || entry.op === 'has_agent'
        || entry.op === 'my_paint'
        || entry.op === 'opp_paint';
}

function estimateOpCost(entry, replayState, actorPlayer) {
    if (!entry) return 0;

    switch (entry.op) {
        case 'paint': {
            const amount = Number(entry.amount ?? 0);
            return Number.isFinite(amount) && amount > 0 ? 2 * amount : 0;
        }
        case 'move': {
            if (!replayState || !Array.isArray(entry.to) || entry.to.length < 2) return 0;
            const row = entry.to[0];
            const col = entry.to[1];
            const cell = replayState.board[row]?.[col];
            if (!cell) return 0;
            const total = cell.p1 + cell.p2;
            if (total === 0) return 1;
            if (total === 10) return 20;
            return actorPlayer === 1 ? 2 * cell.p2 : 2 * cell.p1;
        }
        case 'get_friction':
        case 'has_agent':
        case 'my_paint':
        case 'opp_paint':
            return 1;
        default:
            return 0;
    }
}

function cloneBoardAndAgents(state) {
    if (!state || !state.board || !state.agents) return null;

    return {
        board: state.board.map((row) => row.map((cell) => ({ p1: cell.p1, p2: cell.p2 }))),
        agents: {
            '1': state.agents['1'] ? { row: state.agents['1'].row, col: state.agents['1'].col } : null,
            '2': state.agents['2'] ? { row: state.agents['2'].row, col: state.agents['2'].col } : null,
        },
    };
}

function applyOperationToReplayState(replayState, entry, replayBase, actorPlayer) {
    if (!replayState || !entry) return;

    const playerKey = String(actorPlayer);
    const targetAgent = replayState.agents[playerKey];

    switch (entry.op) {
        case 'move': {
            if (!targetAgent || !Array.isArray(entry.to) || entry.to.length < 2) return;
            targetAgent.row = entry.to[0];
            targetAgent.col = entry.to[1];
            return;
        }
        case 'paint': {
            if (!Array.isArray(entry.at) || entry.at.length < 2) return;
            const row = entry.at[0];
            const col = entry.at[1];
            const amount = Number(entry.amount ?? 0);
            const cell = replayState.board[row]?.[col];
            if (!cell) return;
            if (actorPlayer === 1) cell.p1 += amount;
            else cell.p2 += amount;
            return;
        }
        case 'reset': {
            const restored = cloneBoardAndAgents(replayBase);
            if (!restored) return;
            replayState.board = restored.board;
            replayState.agents = restored.agents;
            return;
        }
        default:
            return;
    }
}

function formatLogEntry(entry) {
    const at = entry.at ? `(${entry.at[1]},\u202f${entry.at[0]})` : '';
    const to = entry.to ? `(${entry.to[1]},\u202f${entry.to[0]})` : '';

    switch (entry.op) {
        case 'halt':
            return op('halt', entry.reason ? esc(entry.reason) : '');
        case 'reset':
            return op('reset', entry.reason ? esc(entry.reason) : '');
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
    const cls = cssType ? `log-op log-op--${cssType}` : 'log-op';
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

    if (total === 0) return 'rgb(255, 255, 255)';
    if (total === 10) return 'rgb(0, 0, 0)';

    const c1 = hexToRgb(activePalette.warm);
    const c2 = hexToRgb(activePalette.cool);

    const t = total / 10;
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
    const board = state.board;
    const agents = state.agents;
    const size = board.length;

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
    sessionPhaseEl.className = highlight ? 'phase-pill phase-pill--write' : 'phase-pill';
}

function applySessionState(state) {
    const phase = state?.phase ?? 'unknown';
    const isWrite = phase === 'write';
    setPhase(phase, isWrite);
    setSessionReady(isWrite && state?.game_over !== true);
}

function setSessionReady(on) {
    sessionReady = on;
    btnCompile.disabled = !on;
    updateDeployButton();
}

function setBothButtonsDisabled(disabled) {
    btnCompile.disabled = disabled;
    btnDeploy.disabled = disabled;
}

function updateDeployButton() {
    const hasErrors = compileState !== null && compileState.errors.length > 0;
    const wordsShort = currentWordCount > 0 && lastBank < currentWordCount;
    btnDeploy.disabled = !sessionReady || hasErrors || wordsShort;
}

// ── Tiny utilities ────────────────────────────────────────────────────────────

function el(tag, className, text) {
    const node = document.createElement(tag);
    node.className = className;
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
        opts.body = JSON.stringify(body);
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

// ── Start ─────────────────────────────────────────────────────────────────────

init();
