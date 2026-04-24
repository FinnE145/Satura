// ── DOM references ────────────────────────────────────────────────────────────

const statusDot = document.getElementById('status-dot');
const sessionIdEl = document.getElementById('session-id');
const timeControlsCard = document.getElementById('time-controls-card');
const gameControlsEl = document.getElementById('game-controls');
const boardLegendP1El = document.getElementById('board-legend-p1');
const boardLegendP2El = document.getElementById('board-legend-p2');
const boardLegendInfoEl = document.getElementById('board-legend-info');
const gameOverModal = document.getElementById('game-over-modal');
const gameOverMessage = document.getElementById('game-over-message');
const gameOverBackdrop = document.getElementById('game-over-backdrop');
const btnReplay = document.getElementById('btn-replay');
const btnHistoryBack = document.getElementById('btn-history-back');
const btnHistoryForward = document.getElementById('btn-history-forward');
const btnHistoryCurrent = document.getElementById('btn-history-current');
const gameControlsPastNotice = document.getElementById('game-controls-past-notice');

// ── State ─────────────────────────────────────────────────────────────────────

const gameRoot = document.getElementById('game-root');
const gameId = gameRoot?.dataset?.gameId || null;
const apiBase = gameId ? `/game/${encodeURIComponent(gameId)}` : null;
const p1Username = gameRoot?.dataset?.p1Username || 'P1';
const p2Username = gameRoot?.dataset?.p2Username || 'P2';

// Set up player badges (always P1 = warm/left, P2 = cool/right)
document.querySelectorAll('[data-tc="badge-p1"]').forEach(el => {
    el.textContent = 'P1';
    el.classList.add('gc-player-badge--p1');
});
document.querySelectorAll('[data-tc="badge-p2"]').forEach(el => {
    el.textContent = 'P2';
    el.classList.add('gc-player-badge--p2');
});
if (boardLegendP1El) boardLegendP1El.className = 'board-legend-item board-legend-item--p1';
if (boardLegendP2El) boardLegendP2El.className = 'board-legend-item board-legend-item--p2';

let statePollTimer = null;
let clockRenderTimer = null;
// History navigation state
let viewingPhase = null;
let knownTotalPhases = 0;
let lastLiveState = null;
let viewState = null;
const fallbackPalette = { name: 'solstice', warm: '#D2640E', cool: '#A82068' };
const bodyPalette = document.body?.dataset;
let activePalette = {
    name: bodyPalette?.activePalette || fallbackPalette.name,
    warm: bodyPalette?.paletteWarm || fallbackPalette.warm,
    cool: bodyPalette?.paletteCool || fallbackPalette.cool,
};
let lastBoardState = null;
let clockSnapshot = null;
let phaseSnapshot = null;
let lastReplayKey = null;
let replayInFlight = false;
let stepDelayMs = 500;
let gameOverModalShown = false;
let lastPhaseCall = null;

// ── Active time container ─────────────────────────────────────────────────────

function tcEl(name) {
    return document.querySelector(`.active-time [data-tc="${name}"]`);
}

function updateActiveTime() {
    const isSmall = window.innerWidth <= 800;
    timeControlsCard?.classList.toggle('active-time', isSmall);
    gameControlsEl?.classList.toggle('active-time', !isSmall);
    renderSessionClock();
    if (phaseSnapshot) {
        renderPhaseIndicator();
    } else if (lastPhaseCall) {
        _applyPhaseToElements(lastPhaseCall.text, lastPhaseCall.className, lastPhaseCall.player);
    }
}

window.addEventListener('resize', updateActiveTime);
updateActiveTime();

if (gameOverBackdrop) {
    gameOverBackdrop.addEventListener('click', hideGameOverModal);
}

// ── Boot ──────────────────────────────────────────────────────────────────────

async function init() {
    setStatus('pending');
    setPhase('initialising');

    if (!gameId || !apiBase) {
        setStatus('error');
        setPhase('error');
        sessionIdEl.textContent = 'missing game id';
        return;
    }

    try {
        sessionIdEl.textContent = gameId.slice(0, 8) + '\u2026';
        sessionIdEl.title = gameId;
        setStatus('ready');

        const initState = await get(`${apiBase}/state`);
        lastLiveState = initState;
        viewState = initState;
        knownTotalPhases = initState.total_phases ?? 0;
        applySessionState(initState);
        renderBoard(initState);
        markReplaySeen(initState);
        startClockRender();
        updateHistoryButtons();

        startStatePoll();
    } catch (e) {
        setStatus('error');
        setPhase('error');
        sessionIdEl.textContent = 'failed to initialise';
    }
}

// ── State polling ─────────────────────────────────────────────────────────────

function startStatePoll() {
    if (statePollTimer) {
        clearInterval(statePollTimer);
        statePollTimer = null;
    }
    refreshState();
    statePollTimer = setInterval(refreshState, 500);
}

async function refreshState() {
    if (!gameId || !statePollTimer) return;
    try {
        const state = await get(`${apiBase}/state`);
        lastLiveState = state;
        if (state.total_phases !== undefined) {
            const prevTotal = knownTotalPhases;
            knownTotalPhases = state.total_phases;
            if (viewingPhase !== null && knownTotalPhases > prevTotal) {
                if (btnHistoryCurrent) btnHistoryCurrent.classList.add('game-controls-btn--is-warm');
                updatePastNotice();
            }
        }
        applySessionState(state);
        if (viewingPhase === null) {
            viewState = state;
            await replayPolledExecution(state);
        }
        if (state?.game_over === true && statePollTimer) {
            clearInterval(statePollTimer);
            statePollTimer = null;
        }
        if (state?.game_over === true && viewerPresenceTimer) {
            clearInterval(viewerPresenceTimer);
            viewerPresenceTimer = null;
        }
        updateHistoryButtons();
    } catch (_) {
        // ignore transient poll failures
    }
}

// ── Session state ─────────────────────────────────────────────────────────────

function applySessionState(state) {
    updateStepDelayFromState(state);
    updatePhaseSnapshot(state);
    updateClockSnapshot(state);
    maybeShowGameOverModal(state);
}

function maybeShowGameOverModal(state) {
    if (!state || state.game_over !== true || gameOverModalShown || !gameOverModal || !gameOverMessage) {
        return;
    }
    if (replayInFlight || hasUnreplayedAnimation(state)) {
        return;
    }
    gameOverModalShown = true;

    const winner = state.winner;
    const reason = state.end_reason;
    const winnerName = winner === 1 ? p1Username : winner === 2 ? p2Username : null;
    const p1 = p1Username;
    const p2 = p2Username;

    if (reason === 'resign') {
        const resignedPlayer = 3 - winner;
        const resignedName = resignedPlayer === 1 ? p1 : p2;
        gameOverMessage.textContent = `${resignedName} resigned. ${winnerName} wins.`;
    } else if (reason === 'timeout') {
        const loser = winner === 1 ? 2 : 1;
        const loserName = loser === 1 ? p1 : p2;
        gameOverMessage.textContent = `${loserName} ran out of write time. ${winnerName} wins.`;
    } else if (reason === 'territory') {
        gameOverMessage.textContent = `${winnerName} won by board control: reached the territory threshold.`;
    } else if (reason === 'draw_offer') {
        gameOverMessage.textContent = 'Draw by mutual agreement.';
    } else if (reason === 'stalemate' || winner === 'draw') {
        gameOverMessage.textContent = 'Stalemate: neither player can still mathematically reach the territory threshold.';
    } else {
        gameOverMessage.textContent = winnerName
            ? `Game over: ${winnerName} wins.`
            : 'Game over: draw.';
    }
    gameOverModal.hidden = false;
}

function hideGameOverModal() {
    if (!gameOverModal) return;
    gameOverModal.hidden = true;
}

function updateStepDelayFromState(state) {
    const stepSeconds = Number(state?.animation_step_duration);
    if (!Number.isFinite(stepSeconds) || stepSeconds <= 0) return;
    stepDelayMs = Math.round(stepSeconds * 1000);
}

function updatePhaseSnapshot(state) {
    const baseLabel = formatPhaseLabel(state);
    const timer = state?.phase_timer;
    const player = Number(state?.current_player ?? 0);

    if (!timer || !timer.mode || !Number.isFinite(Number(timer.seconds))) {
        phaseSnapshot = null;
        _applyPhaseToElements(baseLabel, phasePillClass(state?.phase === 'write', player), player);
        return;
    }

    phaseSnapshot = {
        label: baseLabel,
        mode: timer.mode,
        seconds: Number(timer.seconds),
        sampledAt: performance.now(),
        isWrite: state?.phase === 'write',
        player,
    };
    renderPhaseIndicator();
}

function renderPhaseIndicator() {
    if (!phaseSnapshot) return;
    const elapsed = Math.max(0, (performance.now() - phaseSnapshot.sampledAt) / 1000);
    let timerText = '';
    if (phaseSnapshot.mode === 'countdown') {
        timerText = formatClock(Math.max(0, phaseSnapshot.seconds - elapsed));
    } else if (phaseSnapshot.mode === 'countup') {
        timerText = `+${formatClock(phaseSnapshot.seconds + elapsed)}`;
    }
    _applyPhaseToElements(
        timerText ? `${phaseSnapshot.label} ${timerText}` : phaseSnapshot.label,
        phasePillClass(phaseSnapshot.isWrite, phaseSnapshot.player),
        phaseSnapshot.player
    );
}

function formatPhaseLabel(state) {
    const phase = state?.phase ?? 'unknown';
    if (phase === 'anim_post_exec1' || phase === 'exec1') return 'Exec 1';
    if (phase === 'anim_pre_write' || phase === 'exec2') return 'Exec 2';
    if (phase === 'opening_pre_write') return 'Pre-Write';
    if (phase === 'write') return 'Write';
    return phase;
}

function phasePillClass(isWrite, player) {
    const classes = ['phase-pill'];
    if (player === 1) classes.push('phase-pill--p1');
    else if (player === 2) classes.push('phase-pill--p2');
    if (isWrite) classes.push('phase-pill--write');
    return classes.join(' ');
}

function setPhase(text, highlight = false, player = 0) {
    phaseSnapshot = null;
    _applyPhaseToElements(text, highlight ? 'phase-pill phase-pill--write' : 'phase-pill', player);
}

function _applyPhaseToElements(text, className, player) {
    lastPhaseCall = { text, className, player };
    // P1 is always left (mine side), P2 is always right (opp side)
    const isP1 = player === 1 || player === 0;
    const activeEl = isP1 ? tcEl('phase-p1') : tcEl('phase-p2');
    const inactiveEl = isP1 ? tcEl('phase-p2') : tcEl('phase-p1');
    if (!activeEl || !inactiveEl) return;
    activeEl.textContent = text;
    activeEl.className = className;
    activeEl.hidden = false;
    inactiveEl.textContent = '';
    inactiveEl.hidden = true;
}

function updateClockSnapshot(state) {
    if (!state || !state.clock) return;
    clockSnapshot = {
        p1: Number(state.clock?.[1] ?? state.clock?.['1'] ?? 0),
        p2: Number(state.clock?.[2] ?? state.clock?.['2'] ?? 0),
        phase: state.phase,
        currentPlayer: Number(state.current_player ?? 1),
        gameOver: state.game_over === true,
        sampledAt: performance.now(),
    };
    renderSessionClock();
}

function startClockRender() {
    if (clockRenderTimer) return;
    clockRenderTimer = setInterval(() => {
        renderSessionClock();
        renderPhaseIndicator();
    }, 250);
}

function renderSessionClock() {
    const clockP1 = tcEl('clock-p1');
    const clockP2 = tcEl('clock-p2');
    if (!clockP1 || !clockP2) return;

    if (!clockSnapshot) {
        clockP1.textContent = '--:--';
        clockP2.textContent = '--:--';
        return;
    }

    let p1 = clockSnapshot.p1;
    let p2 = clockSnapshot.p2;

    if (!clockSnapshot.gameOver && clockSnapshot.phase === 'write') {
        const elapsed = Math.max(0, (performance.now() - clockSnapshot.sampledAt) / 1000);
        if (clockSnapshot.currentPlayer === 1) p1 = Math.max(0, p1 - elapsed);
        else p2 = Math.max(0, p2 - elapsed);
    }

    clockP1.textContent = formatClock(p1);
    clockP2.textContent = formatClock(p2);
}

function formatClock(seconds) {
    const safe = Number.isFinite(seconds) ? Math.max(0, Math.floor(seconds)) : 0;
    const mins = Math.floor(safe / 60);
    const secs = safe % 60;
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

// ── Board rendering ───────────────────────────────────────────────────────────

const boardGrid = document.getElementById('board-grid');

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
    cellTooltip.style.top = `${e.clientY - 10}px`;
});
boardGrid.addEventListener('mouseleave', () => {
    cellTooltip.classList.remove('board-cell-tooltip--visible');
});

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
            cell.dataset.p1 = board[r][c].p1;
            cell.dataset.p2 = board[r][c].p2;

            if (agents['1']?.row === r && agents['1']?.col === c) {
                const dot = document.createElement('div');
                dot.className = 'board-agent';
                dot.style.background = activePalette.warm;
                cell.appendChild(dot);
            }
            if (agents['2']?.row === r && agents['2']?.col === c) {
                const dot = document.createElement('div');
                dot.className = 'board-agent';
                dot.style.background = activePalette.cool;
                cell.appendChild(dot);
            }

            boardGrid.appendChild(cell);
        }
    }

    updateBoardCoverage(board);
}

function updateBoardCoverage(board) {
    if (!boardLegendP1El || !boardLegendP2El || !Array.isArray(board) || board.length === 0) return;

    let p1Owned = 0, p2Owned = 0;
    const total = board.length * board.length;

    for (const row of board) {
        for (const cell of row) {
            if (!cell) continue;
            if (cell.p1 > cell.p2) p1Owned++;
            else if (cell.p2 > cell.p1) p2Owned++;
        }
    }

    const p1Pct = total > 0 ? ((p1Owned / total) * 100).toFixed(1) : '0.0';
    const p2Pct = total > 0 ? ((p2Owned / total) * 100).toFixed(1) : '0.0';

    boardLegendP1El.textContent = `P1 ${p1Owned} (${p1Pct}%)`;
    boardLegendP2El.textContent = `P2 ${p2Owned} (${p2Pct}%)`;

    if (boardLegendInfoEl) {
        const threshold = Math.ceil(total * 0.6);
        boardLegendInfoEl.textContent = `${total} cells · Win: ${threshold}`;
    }
}

// ── Status helpers ────────────────────────────────────────────────────────────

function setStatus(state) {
    statusDot.className = `status-dot status-dot--${state}`;
}

// ── Replay helpers ────────────────────────────────────────────────────────────

function replayKeyForState(state) {
    const log = state?.exec_log ?? [];
    const actor = Number(state?.last_exec_player ?? state?.current_player ?? 0);
    const consumed = Number(state?.exec_ops_consumed ?? 0);
    return `${actor}|${consumed}|${JSON.stringify(log)}`;
}

function hasUnreplayedAnimation(state) {
    if (!state) return false;
    const log = state.exec_log ?? [];
    if (!Array.isArray(log) || log.length === 0) return false;
    return replayKeyForState(state) !== lastReplayKey;
}

function markReplaySeen(state) {
    lastReplayKey = replayKeyForState(state);
}

async function replayPolledExecution(state) {
    if (!state || replayInFlight) return;

    const key = replayKeyForState(state);
    if (key === lastReplayKey) {
        if (lastBoardState !== state) renderBoard(state);
        maybeShowGameOverModal(state);
        return;
    }

    const actor = Number(state?.last_exec_player ?? state?.current_player ?? 1);
    const preExecState = cloneBoardAndAgents(lastBoardState);
    replayInFlight = true;
    try {
        await replayExecution(preExecState, state, actor);
    } finally {
        replayInFlight = false;
    }
    markReplaySeen(state);
    maybeShowGameOverModal(state);
}

async function replayExecution(preExecState, postExecState, actorPlayer = 1) {
    if (!preExecState) {
        renderBoard(postExecState);
        return;
    }

    const replayBase = cloneBoardAndAgents(preExecState);
    const replayState = cloneBoardAndAgents(preExecState);

    renderBoard(replayState);

    // Animate board only — no output panel for spectators
    const log = postExecState.exec_log ?? [];
    for (const entry of log) {
        if (!isInstantSensingOp(entry)) {
            await delay(stepDelayMs);
        }
        applyOperationToReplayState(replayState, entry, replayBase, actorPlayer);
        renderBoard(replayState);
    }

    renderBoard(postExecState);
}

function isInstantSensingOp(entry) {
    if (!entry || !entry.op) return false;
    return entry.op === 'get_friction'
        || entry.op === 'has_agent'
        || entry.op === 'my_paint'
        || entry.op === 'opp_paint';
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

// ── History navigation ────────────────────────────────────────────────────────

async function navigateToPhase(phaseNum) {
    try {
        const state = await get(`${apiBase}/state/${phaseNum}`);
        knownTotalPhases = state.total_phases ?? knownTotalPhases;
        viewingPhase = state.phase_number;
        viewState = state;
        renderBoard(state);
        updatePastNotice();
        updateHistoryButtons();
    } catch (_) {
        // ignore — leave current view unchanged
    }
}

function exitHistoryMode() {
    viewingPhase = null;
    gameControlsPastNotice.hidden = true;
    if (btnHistoryCurrent) btnHistoryCurrent.classList.remove('game-controls-btn--is-warm');
    if (lastLiveState) {
        viewState = lastLiveState;
        renderBoard(lastLiveState);
        markReplaySeen(lastLiveState);
    }
    updateHistoryButtons();
}

function updatePastNotice() {
    if (viewingPhase === null) {
        gameControlsPastNotice.hidden = true;
        return;
    }
    const max = knownTotalPhases - 1;
    gameControlsPastNotice.textContent = `Viewing past phase ${viewingPhase} (current is ${max})`;
    gameControlsPastNotice.hidden = false;
}

function updateHistoryButtons() {
    const inHistory = viewingPhase !== null;
    const atStart = inHistory && viewingPhase === 0;
    const atEnd = inHistory && viewingPhase >= knownTotalPhases - 1;
    const noHistory = !inHistory && knownTotalPhases < 2;

    if (btnHistoryBack) btnHistoryBack.disabled = atStart || noHistory;
    if (btnHistoryForward) btnHistoryForward.disabled = !inHistory || atEnd;
    if (btnHistoryCurrent) btnHistoryCurrent.disabled = !inHistory;
}

if (btnHistoryBack) {
    btnHistoryBack.addEventListener('click', async () => {
        if (viewingPhase !== null) {
            if (viewingPhase > 0) navigateToPhase(viewingPhase - 1);
            return;
        }
        if (knownTotalPhases === 0) {
            try {
                const probe = await get(`${apiBase}/state/0`);
                knownTotalPhases = probe.total_phases ?? 0;
            } catch (_) { return; }
        }
        const target = knownTotalPhases - 2;
        if (target >= 0) navigateToPhase(target);
    });
}

if (btnHistoryForward) {
    btnHistoryForward.addEventListener('click', () => {
        if (viewingPhase === null) return;
        const next = viewingPhase + 1;
        if (next >= knownTotalPhases - 1) {
            exitHistoryMode();
        } else {
            navigateToPhase(next);
        }
    });
}

if (btnHistoryCurrent) {
    btnHistoryCurrent.addEventListener('click', () => {
        exitHistoryMode();
    });
}

if (btnReplay) {
    btnReplay.addEventListener('click', async () => {
        if (!gameId || !viewState || replayInFlight) return;
        const log = viewState.exec_log ?? [];
        if (log.length === 0) return;

        const wasLive = viewingPhase === null;
        const currentPhaseNum = wasLive ? knownTotalPhases - 1 : viewingPhase;

        if (wasLive) {
            viewingPhase = currentPhaseNum;
            updatePastNotice();
            updateHistoryButtons();
        }

        let preExecState = null;
        if (currentPhaseNum > 0) {
            try {
                preExecState = await get(`${apiBase}/state/${currentPhaseNum - 1}`);
            } catch (_) { /* proceed without pre-state */ }
        }

        const actorPlayer = viewState.player_slot ?? viewState.last_exec_player ?? 1;

        replayInFlight = true;
        try {
            await replayExecution(preExecState, viewState, actorPlayer);
        } finally {
            replayInFlight = false;
        }

        if (wasLive) {
            exitHistoryMode();
        }
    });
}

// ── Viewer presence ───────────────────────────────────────────────────────────

async function pingViewerPresence() {
    if (!apiBase) return;
    try {
        await fetch(`${apiBase}/view/ping`, { method: 'POST' });
    } catch (_) {
        // ignore
    }
}

// ── Tiny utilities ────────────────────────────────────────────────────────────

async function get(url) {
    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return resp.json();
}

function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// ── Init ──────────────────────────────────────────────────────────────────────

pingViewerPresence();
let viewerPresenceTimer = setInterval(pingViewerPresence, 15000);

init();
