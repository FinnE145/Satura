'use strict';

// ── DOM references ─────────────────────────────────────────────────────────────

const detailRoot       = document.getElementById('detail-root');
const gameId           = detailRoot?.dataset?.gameId || null;
const mySlot           = parseInt(detailRoot?.dataset?.mySlot, 10) || 1;
const oppSlot          = mySlot === 1 ? 2 : 1;
const opLimit          = parseInt(detailRoot?.dataset?.opLimit, 10) || null;
const apiBase          = gameId ? `/game/${encodeURIComponent(gameId)}` : null;

const boardGrid        = document.getElementById('board-grid');
const boardLegendMineEl = document.getElementById('board-legend-mine');
const boardLegendOppEl  = document.getElementById('board-legend-opp');
const boardLegendInfoEl = document.getElementById('board-legend-info');
const scriptEditor     = document.getElementById('script-editor');
const scriptMetaInfo   = document.getElementById('script-meta-info');
const outputBody       = document.getElementById('output-body');
const outcomeLabel     = document.getElementById('outcome-label');
const funcsList        = document.getElementById('funcs-list');
const funcsCode        = document.getElementById('funcs-code');
const funcsBadge       = document.getElementById('funcs-badge');
const phaseNotice      = document.getElementById('phase-notice');
const badgeMine        = document.getElementById('badge-mine');
const badgeOpp         = document.getElementById('badge-opp');
const clockMine        = document.getElementById('clock-mine');
const clockOpp         = document.getElementById('clock-opp');
const phaseMine        = document.getElementById('phase-mine');
const phaseOpp         = document.getElementById('phase-opp');
const btnBack          = document.getElementById('btn-back');
const btnForward       = document.getElementById('btn-forward');
const btnEnd           = document.getElementById('btn-end');
const btnReplay        = document.getElementById('btn-replay');
const statsCoverageBar = document.getElementById('stats-coverage-bar');

// ── Embedded data ──────────────────────────────────────────────────────────────

const phasesMeta    = JSON.parse(document.getElementById('phases-meta')?.textContent    || '[]');
const scriptsMeta   = JSON.parse(document.getElementById('scripts-meta')?.textContent   || '[]');
const functionsMeta = JSON.parse(document.getElementById('functions-meta')?.textContent || '[]');
const oppWriteTimes = JSON.parse(document.getElementById('opp-write-times')?.textContent || '[]');

// ── Palette ────────────────────────────────────────────────────────────────────

const fallbackPalette = { name: 'solstice', warm: '#D2640E', cool: '#A82068' };
const bodyData = document.body?.dataset;
const activePalette = {
    name: (bodyData?.activePalette || fallbackPalette.name).toLowerCase(),
    warm:  bodyData?.paletteWarm   || fallbackPalette.warm,
    cool:  bodyData?.paletteCool   || fallbackPalette.cool,
    uiWarm:      bodyData?.uiWarm      || bodyData?.paletteWarm  || fallbackPalette.warm,
    uiCool:      bodyData?.uiCool      || bodyData?.paletteCool  || fallbackPalette.cool,
    warmBright:  bodyData?.uiWarmBright || fallbackPalette.warm,
};

// ── Navigation state ───────────────────────────────────────────────────────────

let currentPhaseIdx = phasesMeta.length > 0 ? phasesMeta.length - 1 : 0;
const stateCache    = new Map();
let replayInFlight  = false;
let selectedFuncName = null;
const charts        = {};

// ── Utility ────────────────────────────────────────────────────────────────────

function el(tag, className, text) {
    const node = document.createElement(tag);
    node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
}

function esc(str) {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function get(url) {
    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return resp.json();
}

function formatClock(seconds) {
    if (seconds == null || isNaN(seconds)) return '--:--';
    const s = Math.max(0, Math.round(Number(seconds)));
    const m = Math.floor(s / 60);
    return `${String(m).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
}

// ── Board cell colour (mirrors game.js cellBg exactly) ────────────────────────

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
    const t  = total / 10;
    const ratio = p2 / total;

    const mid = {
        r: c1.r + ratio * (c2.r - c1.r),
        g: c1.g + ratio * (c2.g - c1.g),
        b: c1.b + ratio * (c2.b - c1.b),
    };

    let r, g, b;
    if (t <= 0.5) {
        const s = t * 2;
        r = 255 + s * (mid.r - 255);
        g = 255 + s * (mid.g - 255);
        b = 255 + s * (mid.b - 255);
    } else {
        let s = (t - 0.5) * 2;
        if (activePalette.name === 'fieldstone') s *= 0.7;
        r = mid.r * (1 - s);
        g = mid.g * (1 - s);
        b = mid.b * (1 - s);
        let mult = 1;
        const pal = activePalette.name;
        if (pal === 'solstice' || pal === 'levant') {
            if ((p1 === 4 && p2 === 5) || (p1 === 5 && p2 === 4)) mult = 1.35;
        } else if (pal === 'folio') {
            if ((p1 === 3 && p2 === 5) || (p1 === 4 && p2 === 4) || (p1 === 5 && p2 === 3)) mult = 1.2;
            if ((p1 === 4 && p2 === 5) || (p1 === 5 && p2 === 4)) mult = 1.6;
        }
        r *= mult; g *= mult; b *= mult;
    }

    const clamp = v => Math.round(Math.min(255, Math.max(0, v)));
    return `rgb(${clamp(r)}, ${clamp(g)}, ${clamp(b)})`;
}

// ── Board rendering ────────────────────────────────────────────────────────────

function renderBoard(state) {
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
            cell.dataset.p1 = board[r][c].p1;
            cell.dataset.p2 = board[r][c].p2;

            if (agents?.['1']?.row === r && agents?.['1']?.col === c) {
                const dot = document.createElement('div');
                dot.className = 'board-agent';
                dot.style.background = activePalette.warm;
                cell.appendChild(dot);
            }
            if (agents?.['2']?.row === r && agents?.['2']?.col === c) {
                const dot = document.createElement('div');
                dot.className = 'board-agent';
                dot.style.background = activePalette.cool;
                cell.appendChild(dot);
            }

            boardGrid.appendChild(cell);
        }
    }

    updateBoardLegend(board);
}

function updateBoardLegend(board) {
    if (!boardLegendMineEl || !boardLegendOppEl || !Array.isArray(board) || board.length === 0) return;

    let p1Owned = 0, p2Owned = 0;
    const total = board.length * board.length;

    for (const row of board) {
        for (const cell of row) {
            if (!cell) continue;
            if (cell.p1 > cell.p2) p1Owned++;
            else if (cell.p2 > cell.p1) p2Owned++;
        }
    }

    const mineOwned = mySlot === 1 ? p1Owned : p2Owned;
    const oppOwned  = mySlot === 1 ? p2Owned : p1Owned;
    const minePct   = total > 0 ? ((mineOwned / total) * 100).toFixed(1) : '0.0';
    const oppPct    = total > 0 ? ((oppOwned  / total) * 100).toFixed(1) : '0.0';

    boardLegendMineEl.textContent = `P${mySlot} ${mineOwned} (${minePct}%)`;
    boardLegendOppEl.textContent  = `P${oppSlot} ${oppOwned} (${oppPct}%)`;

    if (boardLegendInfoEl) {
        const threshold = Math.ceil(total * 0.6);
        boardLegendInfoEl.textContent = `${total} cells · Win: ${threshold}`;
    }
}

// ── Board tooltip ──────────────────────────────────────────────────────────────

const cellTooltip = document.createElement('div');
cellTooltip.className = 'board-cell-tooltip';
cellTooltip.innerHTML =
    '<span class="board-cell-tooltip__p1"></span>' +
    '<span class="board-cell-tooltip__p2"></span>';
document.body.appendChild(cellTooltip);
const tooltipP1El = cellTooltip.querySelector('.board-cell-tooltip__p1');
const tooltipP2El = cellTooltip.querySelector('.board-cell-tooltip__p2');

boardGrid.addEventListener('mouseover', (e) => {
    const cell = e.target.closest('.board-cell');
    if (!cell) return;
    tooltipP1El.textContent = `P1: ${cell.dataset.p1 ?? 0}`;
    tooltipP2El.textContent = `P2: ${cell.dataset.p2 ?? 0}`;
    cellTooltip.classList.add('board-cell-tooltip--visible');
});
boardGrid.addEventListener('mousemove', (e) => {
    cellTooltip.style.left = `${e.clientX + 12}px`;
    cellTooltip.style.top  = `${e.clientY - 10}px`;
});
boardGrid.addEventListener('mouseleave', () => {
    cellTooltip.classList.remove('board-cell-tooltip--visible');
});

// ── Ops / output rendering ─────────────────────────────────────────────────────

function formatLogEntry(entry) {
    const at = entry.at ? `(${entry.at[1]},\u202f${entry.at[0]})` : '';
    const to = entry.to ? `(${entry.to[1]},\u202f${entry.to[0]})` : '';
    switch (entry.op) {
        case 'halt':  return logOp('halt',  entry.reason ? esc(entry.reason) : '');
        case 'reset': return logOp('reset', entry.reason ? esc(entry.reason) : '');
        case 'move':  return logOp('move',  `\u2192 ${to}`);
        case 'paint': return logOp('paint', `+${entry.amount} at ${at}`);
        case 'get_friction': return logOp('query', `get_friction ${at} = ${fmtResult(entry.result)}`, 'get_friction');
        case 'has_agent':    return logOp('query', `has_agent ${at} = ${fmtResult(entry.result)}`,    'has_agent');
        case 'my_paint':     return logOp('query', `my_paint ${at} = ${fmtResult(entry.result)}`,     'my_paint');
        case 'opp_paint':    return logOp('query', `opp_paint ${at} = ${fmtResult(entry.result)}`,    'opp_paint');
        default: return logOp('', esc(JSON.stringify(entry)), entry.op);
    }
}

function logOp(cssType, detail, label) {
    const opLabel = label ?? cssType;
    const cls = cssType ? `log-op log-op--${cssType}` : 'log-op';
    return `<span class="${cls}">${esc(opLabel)}</span><span class="log-detail">${detail}</span>`;
}

function fmtResult(v) {
    return v == null ? '<span style="opacity:.5">null</span>' : String(v);
}

function renderOps(execLog, opsConsumed) {
    if (!execLog || execLog.length === 0) {
        outcomeLabel.textContent = 'no ops';
        outputBody.innerHTML = '';
        outputBody.appendChild(el('span', 'empty-label', 'Script executed with no board operations.'));
        return;
    }
    const consumed = opsConsumed ?? execLog.length;
    const lim = opLimit ?? '?';
    outcomeLabel.textContent = `${consumed} / ${lim} ops`;
    outputBody.innerHTML = '';
    execLog.forEach((entry, i) => {
        const row = document.createElement('div');
        row.className = 'log-entry';
        row.innerHTML = `<span class="log-idx">${String(i + 1).padStart(2, '0')}</span>` + formatLogEntry(entry);
        outputBody.appendChild(row);
    });
}

// ── Script panel ───────────────────────────────────────────────────────────────

function renderScript(phaseIdx) {
    const meta   = phasesMeta[phaseIdx];
    if (!meta) return;
    const script = scriptsMeta.find(s => s.id === meta.script_id);

    if (script) {
        scriptEditor.value = script.source || '';
        scriptEditor.placeholder = '// no script for this phase';
        const dur = script.write_duration != null
            ? ` · ${script.write_duration.toFixed(1)}s`
            : '';
        scriptMetaInfo.textContent = `Turn ${script.turn} · ${script.word_count}w${dur}`;
    } else {
        scriptEditor.value = '';
        scriptEditor.placeholder = `// P${meta.player_slot} script — not available`;
        scriptMetaInfo.textContent = `P${meta.player_slot} exec`;
    }
}

// ── Phase indicators ───────────────────────────────────────────────────────────

function renderPhasePills(meta) {
    const player    = meta.player_slot;
    const typeLabel = meta.exec_type === 'initial' ? 'Opening' : 'Exec';
    const activeEl   = player === mySlot  ? phaseMine : phaseOpp;
    const inactiveEl = player === mySlot  ? phaseOpp  : phaseMine;

    activeEl.textContent = typeLabel;
    activeEl.className   = `phase-pill phase-pill--p${player}`;
    activeEl.hidden      = false;
    inactiveEl.textContent = '';
    inactiveEl.hidden    = true;
}

function renderClocks(clockRemaining) {
    const p1 = clockRemaining?.['1'] ?? clockRemaining?.[1];
    const p2 = clockRemaining?.['2'] ?? clockRemaining?.[2];
    clockMine.textContent = formatClock(mySlot  === 1 ? p1 : p2);
    clockOpp.textContent  = formatClock(oppSlot === 1 ? p1 : p2);
}

function renderPhaseNotice(phaseIdx) {
    const total = phasesMeta.length;
    phaseNotice.textContent = `Phase ${phaseIdx + 1} of ${total}`;
    phaseNotice.hidden = false;
}

// ── Functions panel ────────────────────────────────────────────────────────────

function renderFunctions(phaseIdx) {
    const meta = phasesMeta[phaseIdx];
    if (!meta) return;

    // Determine the current turn: the max turn of any script seen at/before this phase
    const seenScriptIds = new Set(
        phasesMeta.slice(0, phaseIdx + 1).map(p => p.script_id).filter(Boolean)
    );
    const reachableTurns = scriptsMeta
        .filter(s => seenScriptIds.has(s.id))
        .map(s => s.turn);
    const currentTurn = reachableTurns.length > 0 ? Math.max(...reachableTurns) : 0;

    const totalFuncs     = functionsMeta.length;
    const availableCount = functionsMeta.filter(
        f => f.defined_at_turn == null || f.defined_at_turn <= currentTurn
    ).length;

    funcsBadge.textContent = `${availableCount} / ${totalFuncs}`;
    funcsBadge.hidden      = totalFuncs === 0;

    funcsList.innerHTML = '';
    if (totalFuncs === 0) {
        funcsList.appendChild(el('span', 'empty-label', 'No functions defined'));
        return;
    }

    for (const fn of functionsMeta) {
        const available = fn.defined_at_turn == null || fn.defined_at_turn <= currentTurn;
        const item = document.createElement('div');
        item.className = 'script-history-item' + (available ? '' : ' is-disabled');

        const labelWrap = document.createElement('div');
        labelWrap.className = 'script-history-item__label-wrap';

        const labelEl = document.createElement('span');
        labelEl.className = 'script-history-item__label';
        labelEl.textContent = fn.name;
        labelWrap.appendChild(labelEl);

        if (fn.args?.length > 0) {
            const argsEl = document.createElement('span');
            argsEl.className = 'script-history-item__args';
            argsEl.textContent = `(${fn.args.join(', ')})`;
            labelWrap.appendChild(argsEl);
        }

        item.appendChild(labelWrap);

        if (fn.source && available) {
            item.title = fn.source.trim().slice(0, 70).replace(/\s+/g, ' ');
            item.addEventListener('click', () => {
                selectedFuncName = fn.name;
                funcsCode.value  = fn.source || '';
                document.querySelectorAll('#funcs-list .script-history-item--selected')
                    .forEach(n => n.classList.remove('script-history-item--selected'));
                item.classList.add('script-history-item--selected');
            });
        }

        if (fn.name === selectedFuncName && available) {
            item.classList.add('script-history-item--selected');
        }

        funcsList.appendChild(item);
    }
}

// ── Navigation buttons ─────────────────────────────────────────────────────────

function updateNavButtons() {
    const atStart = currentPhaseIdx === 0;
    const atEnd   = currentPhaseIdx >= phasesMeta.length - 1;
    if (btnBack)    btnBack.disabled    = atStart || replayInFlight;
    if (btnForward) btnForward.disabled = atEnd   || replayInFlight;
    if (btnEnd)     btnEnd.disabled     = atEnd   || replayInFlight;
    if (btnReplay)  btnReplay.disabled  = replayInFlight || phasesMeta.length === 0;
}

// ── Fetch & navigate ───────────────────────────────────────────────────────────

async function fetchPhaseState(phaseNumber) {
    if (stateCache.has(phaseNumber)) return stateCache.get(phaseNumber);
    const state = await get(`${apiBase}/state/${phaseNumber}`);
    stateCache.set(phaseNumber, state);
    return state;
}

async function navigateTo(phaseIdx) {
    if (phaseIdx < 0 || phaseIdx >= phasesMeta.length || replayInFlight) return;
    currentPhaseIdx = phaseIdx;

    const meta = phasesMeta[phaseIdx];
    let state;
    try {
        state = await fetchPhaseState(meta.phase_number);
    } catch (e) {
        console.warn('Failed to fetch phase state:', e);
        return;
    }

    renderBoard(state);
    renderOps(state.exec_log, meta.ops_consumed);
    renderScript(phaseIdx);
    renderClocks(meta.clock_remaining);
    renderPhasePills(meta);
    renderPhaseNotice(phaseIdx);
    renderFunctions(phaseIdx);
    updateNavButtons();
    highlightChartPoints(phaseIdx);
}

// ── Replay ─────────────────────────────────────────────────────────────────────

function isInstantSensingOp(entry) {
    if (!entry?.op) return false;
    return ['get_friction', 'has_agent', 'my_paint', 'opp_paint'].includes(entry.op);
}

function cloneBoardAndAgents(state) {
    if (!state?.board || !state?.agents) return null;
    return {
        board:  state.board.map(row => row.map(cell => ({ p1: cell.p1, p2: cell.p2 }))),
        agents: {
            '1': state.agents['1'] ? { ...state.agents['1'] } : null,
            '2': state.agents['2'] ? { ...state.agents['2'] } : null,
        },
    };
}

function applyOp(replayState, entry, replayBase, actorPlayer) {
    if (!replayState || !entry) return;
    const agent = replayState.agents[String(actorPlayer)];
    switch (entry.op) {
        case 'move': {
            if (!agent || !Array.isArray(entry.to) || entry.to.length < 2) return;
            agent.row = entry.to[0];
            agent.col = entry.to[1];
            return;
        }
        case 'paint': {
            if (!Array.isArray(entry.at) || entry.at.length < 2) return;
            const cell = replayState.board[entry.at[0]]?.[entry.at[1]];
            if (!cell) return;
            const amount = Number(entry.amount ?? 0);
            if (actorPlayer === 1) cell.p1 += amount;
            else cell.p2 += amount;
            return;
        }
        case 'reset': {
            const restored = cloneBoardAndAgents(replayBase);
            if (!restored) return;
            replayState.board  = restored.board;
            replayState.agents = restored.agents;
            return;
        }
    }
}

async function replayCurrentPhase() {
    if (replayInFlight) return;
    const meta = phasesMeta[currentPhaseIdx];
    if (!meta) return;

    let postExecState;
    try {
        postExecState = await fetchPhaseState(meta.phase_number);
    } catch { return; }

    const log = postExecState.exec_log ?? [];
    if (log.length === 0) return;

    let preExecState = null;
    if (currentPhaseIdx > 0) {
        try {
            preExecState = await fetchPhaseState(phasesMeta[currentPhaseIdx - 1].phase_number);
        } catch { /* proceed without */ }
    }

    replayInFlight = true;
    updateNavButtons();

    const replayBase  = cloneBoardAndAgents(preExecState || postExecState);
    const replayState = cloneBoardAndAgents(preExecState || postExecState);
    if (replayState) renderBoard(replayState);

    const consumed    = meta.ops_consumed ?? log.length;
    const lim         = opLimit ?? '?';
    const actorPlayer = meta.player_slot ?? 1;

    outcomeLabel.textContent = `0 / ${lim} ops`;
    outputBody.innerHTML = '';

    for (let i = 0; i < log.length; i++) {
        const entry = log[i];
        if (!isInstantSensingOp(entry)) await delay(400);

        const row = document.createElement('div');
        row.className = 'log-entry';
        row.innerHTML = `<span class="log-idx">${String(i + 1).padStart(2, '0')}</span>` + formatLogEntry(entry);
        outputBody.appendChild(row);
        outputBody.scrollTop = outputBody.scrollHeight;

        if (replayState) {
            applyOp(replayState, entry, replayBase, actorPlayer);
            renderBoard(replayState);
        }
    }

    outcomeLabel.textContent = `${consumed} / ${lim} ops`;
    if (postExecState) renderBoard(postExecState);

    replayInFlight = false;
    updateNavButtons();
}

// ── Chart helpers ──────────────────────────────────────────────────────────────

function makePointColors(length, highlightIdx, base, highlight) {
    return Array.from({ length }, (_, i) => i === highlightIdx ? highlight : base);
}

function makePointRadii(length, highlightIdx, base = 3, highlight = 6) {
    return Array.from({ length }, (_, i) => i === highlightIdx ? highlight : base);
}

function highlightChartPoints(phaseIdx) {
    // Chart 1: Board Dominance — no dots, nothing to highlight

    // Chart 3: Word Count & Ops — ops datasets also indexed by phasesMeta
    if (charts.wordsOps) {
        charts.wordsOps.data.datasets.forEach(ds => {
            ds.pointBackgroundColor = makePointColors(ds.data.length, phaseIdx, ds.borderColor, '#ffffff');
            ds.pointRadius          = makePointRadii(ds.data.length, phaseIdx);
        });
        charts.wordsOps.update('none');
    }

    // Chart 2: Time Per Turn — find the turn that matches this phase
    if (charts.timePer) {
        const meta   = phasesMeta[phaseIdx];
        const script = scriptsMeta.find(s => s.id === meta?.script_id);
        const labels = charts.timePer.data.labels;
        const turnIdx = script ? labels.indexOf(script.turn) : -1;
        charts.timePer.data.datasets.forEach(ds => {
            ds.pointBackgroundColor = makePointColors(ds.data.length, turnIdx, ds.borderColor, '#ffffff');
            ds.pointRadius          = makePointRadii(ds.data.length, turnIdx);
        });
        charts.timePer.update('none');
    }
}

function initCharts() {
    if (!window.Chart || phasesMeta.length === 0) return;

    const warm       = activePalette.uiWarm;
    const warmBright = activePalette.warmBright;
    const cool       = activePalette.uiCool;
    const textColor = 'rgba(246, 245, 244, 0.7)';
    const gridColor = 'rgba(246, 245, 244, 0.08)';
    const fontDef   = { family: "'DM Sans', sans-serif", size: 10 };

    const sharedScales = {
        x: {
            ticks: { color: textColor, font: fontDef },
            grid:  { color: gridColor },
        },
        y: {
            ticks: { color: textColor, font: fontDef },
            grid:  { color: gridColor },
        },
    };

    const sharedPlugins = {
        legend: {
            labels: {
                color: textColor,
                font: { family: "'DM Sans', sans-serif", size: 11 },
                boxWidth: 20,
                padding: 12,
            },
        },
        tooltip: {
            backgroundColor: '#2E2C2A',
            borderColor: 'rgba(246,245,244,0.12)',
            borderWidth: 1,
            titleColor: textColor,
            bodyColor:  textColor,
        },
    };

    const sharedBase = {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        plugins: sharedPlugins,
        scales:  sharedScales,
    };

    // ── Chart 1: Board Dominance ──────────────────────────────────────
    const domLabels = phasesMeta.map((_, i) => i + 1);
    charts.dominance = new Chart(document.getElementById('chart-dominance'), {
        type: 'line',
        data: {
            labels: domLabels,
            datasets: [
                {
                    label: `P${mySlot} (mine)`,
                    data:  phasesMeta.map(p => mySlot === 1 ? p.coverage_p1 : p.coverage_p2),
                    borderColor: warm, backgroundColor: 'transparent',
                    pointRadius: 0, pointHoverRadius: 5, pointHoverBackgroundColor: warm,
                    hitRadius: 12, tension: 0.3,
                },
                {
                    label: `P${oppSlot} (opp)`,
                    data:  phasesMeta.map(p => mySlot === 1 ? p.coverage_p2 : p.coverage_p1),
                    borderColor: cool, backgroundColor: 'transparent',
                    pointRadius: 0, pointHoverRadius: 5, pointHoverBackgroundColor: cool,
                    hitRadius: 12, tension: 0.3,
                },
            ],
        },
        options: {
            ...sharedBase,
            plugins: {
                ...sharedPlugins,
                tooltip: {
                    ...sharedPlugins.tooltip,
                    callbacks: {
                        title: items => `Phase ${items[0].label}`,
                        label: item  => `${item.dataset.label}: ${item.raw}%`,
                    },
                },
            },
            scales: {
                ...sharedScales,
                y: {
                    ...sharedScales.y,
                    min: 0, max: 100,
                    ticks: { ...sharedScales.y.ticks, callback: v => `${v}%` },
                },
            },
            onClick: (evt, elements) => {
                if (elements.length > 0) navigateTo(elements[0].index);
            },
        },
    });

    // ── Chart 2: Time Per Turn ────────────────────────────────────────
    const myScripts = scriptsMeta.filter(s => s.player_slot === mySlot);
    const allTurns  = Array.from(new Set([
        ...myScripts.map(s => s.turn),
        ...oppWriteTimes.map(s => s.turn),
    ])).sort((a, b) => a - b);
    if (allTurns.length > 0) {
        const myByTurn  = Object.fromEntries(myScripts.map(s => [s.turn, s]));
        const oppByTurn = Object.fromEntries(oppWriteTimes.map(s => [s.turn, s]));

        const allDurations = [
            ...myScripts.map(s => s.write_duration),
            ...oppWriteTimes.map(s => s.write_duration),
        ].filter(d => d != null);
        const maxDuration = allDurations.length > 0 ? Math.max(...allDurations) : 0;
        const useMinutes  = maxDuration >= 130;
        const toUnit      = v => useMinutes ? +(v / 60).toFixed(2) : +v.toFixed(1);
        const unitSuffix  = useMinutes ? 'm' : 's';

        charts.timePer = new Chart(document.getElementById('chart-time'), {
            type: 'line',
            data: {
                labels: allTurns,
                datasets: [
                    {
                        label: `P${mySlot} write time`,
                        data: allTurns.map(t => {
                            const s = myByTurn[t];
                            return s?.write_duration != null ? toUnit(s.write_duration) : null;
                        }),
                        borderColor: warm, backgroundColor: 'transparent',
                        pointBackgroundColor: warm, pointRadius: 3,
                        spanGaps: true, tension: 0.3,
                    },
                    {
                        label: `P${oppSlot} write time`,
                        data: allTurns.map(t => {
                            const s = oppByTurn[t];
                            return s?.write_duration != null ? toUnit(s.write_duration) : null;
                        }),
                        borderColor: cool, backgroundColor: 'transparent',
                        pointBackgroundColor: cool, pointRadius: 3,
                        spanGaps: true, tension: 0.3,
                    },
                ],
            },
            options: {
                ...sharedBase,
                plugins: {
                    ...sharedPlugins,
                    tooltip: {
                        ...sharedPlugins.tooltip,
                        callbacks: {
                            title: items => `Turn ${items[0].label}`,
                            label: item  => item.raw != null ? `${item.dataset.label}: ${item.raw}${unitSuffix}` : 'N/A',
                        },
                    },
                },
                scales: {
                    ...sharedScales,
                    x: {
                        ...sharedScales.x,
                        title: { display: true, text: 'Turn', color: textColor, font: fontDef },
                    },
                    y: {
                        ...sharedScales.y,
                        ticks: { ...sharedScales.y.ticks, callback: v => `${v}${unitSuffix}` },
                    },
                },
                onClick: (evt, elements) => {
                    if (elements.length === 0) return;
                    const turn   = allTurns[elements[0].index];
                    const script = myByTurn[turn];
                    if (!script) return;
                    const pIdx = phasesMeta.findIndex(p => p.script_id === script.id);
                    if (pIdx >= 0) navigateTo(pIdx);
                },
            },
        });
    }

    // ── Chart 3: Word Count & Ops ─────────────────────────────────────
    // X-axis = phase index; word count plotted at the exec phase that used each script
    const scriptWordCount = new Map(scriptsMeta.map(s => [s.id, s.word_count]));

    const myWordData  = phasesMeta.map(p =>
        p.player_slot === mySlot  && p.script_id && scriptWordCount.has(p.script_id)
            ? scriptWordCount.get(p.script_id) : null
    );
    const myOpsData   = phasesMeta.map(p =>
        p.player_slot === mySlot  ? (p.ops_consumed ?? null) : null
    );
    const oppOpsData  = phasesMeta.map(p =>
        p.player_slot === oppSlot ? (p.ops_consumed ?? null) : null
    );

    charts.wordsOps = new Chart(document.getElementById('chart-words-ops'), {
        type: 'line',
        data: {
            labels: phasesMeta.map((_, i) => i + 1),
            datasets: [
                {
                    label: `P${mySlot} word count`,
                    data: myWordData,
                    borderColor: warmBright, backgroundColor: 'transparent',
                    pointBackgroundColor: warmBright, pointRadius: 3,
                    spanGaps: true, tension: 0.3,
                    borderDash: [],
                },
                {
                    label: `P${mySlot} ops used`,
                    data: myOpsData,
                    borderColor: warm, backgroundColor: 'transparent',
                    pointBackgroundColor: warm, pointRadius: 3,
                    spanGaps: true, tension: 0.3,
                    borderDash: [5, 3],
                },
                {
                    label: `P${oppSlot} ops used`,
                    data: oppOpsData,
                    borderColor: cool, backgroundColor: 'transparent',
                    pointBackgroundColor: cool, pointRadius: 3,
                    spanGaps: true, tension: 0.3,
                    borderDash: [5, 3],
                },
            ],
        },
        options: {
            ...sharedBase,
            plugins: {
                ...sharedPlugins,
                tooltip: {
                    ...sharedPlugins.tooltip,
                    callbacks: {
                        title: items => `Phase ${items[0].label}`,
                    },
                },
            },
            onClick: (evt, elements) => {
                if (elements.length > 0) navigateTo(elements[0].index);
            },
        },
    });
}

// ── Stats coverage bar ─────────────────────────────────────────────────────────

function renderStatsCoverageBar(board) {
    if (!statsCoverageBar || !board) return;
    const size   = board.length;
    const counts = { warm: 0, cool: 0, contested: 0, black: 0, blank: 0 };

    for (const row of board) {
        for (const cell of row) {
            if (!cell) continue;
            const p1 = cell.p1 ?? 0;
            const p2 = cell.p2 ?? 0;
            if      (p1 === 0 && p2 === 0)  counts.blank++;
            else if (p1 === 5 && p2 === 5)  counts.black++;
            else if (p1 === p2)             counts.contested++;
            else if (p1 > p2)              counts.warm++;
            else                            counts.cool++;
        }
    }

    const total = size * size;
    statsCoverageBar.innerHTML = '';
    for (const key of ['warm', 'cool', 'contested', 'black', 'blank']) {
        if (counts[key] === 0) continue;
        const seg = document.createElement('div');
        seg.className  = `coverage-segment coverage-segment--${key}`;
        seg.style.flexGrow = counts[key];
        seg.title = `${key}: ${counts[key]} / ${total} (${Math.round(counts[key] / total * 100)}%)`;
        statsCoverageBar.appendChild(seg);
    }
}

// ── Badge & legend setup ───────────────────────────────────────────────────────

function setupBadges() {
    if (badgeMine) {
        badgeMine.textContent = `P${mySlot}`;
        badgeMine.className   = `gc-player-badge gc-player-badge--p${mySlot}`;
    }
    if (badgeOpp) {
        badgeOpp.textContent = `P${oppSlot}`;
        badgeOpp.className   = `gc-player-badge gc-player-badge--p${oppSlot}`;
    }
    if (boardLegendMineEl) {
        boardLegendMineEl.className = `board-legend-item board-legend-item--p${mySlot}`;
    }
    if (boardLegendOppEl) {
        boardLegendOppEl.className = `board-legend-item board-legend-item--p${oppSlot}`;
    }
}

// ── Button wiring ──────────────────────────────────────────────────────────────

if (btnBack)    btnBack.addEventListener('click',    () => { if (!replayInFlight) navigateTo(currentPhaseIdx - 1); });
if (btnForward) btnForward.addEventListener('click', () => { if (!replayInFlight) navigateTo(currentPhaseIdx + 1); });
if (btnEnd)     btnEnd.addEventListener('click',     () => { if (!replayInFlight) navigateTo(phasesMeta.length - 1); });
if (btnReplay)  btnReplay.addEventListener('click',  () => replayCurrentPhase());

// ── Keyboard navigation ────────────────────────────────────────────────────────

document.addEventListener('keydown', (e) => {
    if (replayInFlight) return;
    if (e.target.tagName === 'TEXTAREA') return;
    if (e.key === 'ArrowLeft'  || e.key === 'ArrowUp')    { e.preventDefault(); navigateTo(currentPhaseIdx - 1); }
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown')  { e.preventDefault(); navigateTo(currentPhaseIdx + 1); }
    if (e.key === 'End')  { e.preventDefault(); navigateTo(phasesMeta.length - 1); }
    if (e.key === 'Home') { e.preventDefault(); navigateTo(0); }
});

// ── Init ───────────────────────────────────────────────────────────────────────

async function init() {
    if (!gameId || phasesMeta.length === 0) {
        updateNavButtons();
        return;
    }

    setupBadges();

    const lastIdx = phasesMeta.length - 1;
    try {
        await navigateTo(lastIdx);
    } catch (e) {
        console.warn('Failed to load initial phase state:', e);
    }

    // Coverage bar from the final cached board state
    const lastState = stateCache.get(phasesMeta[lastIdx]?.phase_number);
    if (lastState?.board) renderStatsCoverageBar(lastState.board);

    // Charts are ready once the first board state is loaded
    initCharts();
    highlightChartPoints(lastIdx);
}

init();
