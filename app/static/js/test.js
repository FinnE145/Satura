// ── DOM references ────────────────────────────────────────────────────────────

const statusDot = document.getElementById('status-dot');
const sessionIdEl = document.getElementById('session-id');
const gcClockMineEl = document.getElementById('gc-clock-mine');
const gcClockOppEl = document.getElementById('gc-clock-opp');
const gcPhaseMineEl = document.getElementById('gc-phase-mine');
const gcPhaseOppEl = document.getElementById('gc-phase-opp');
const gcBadgeMineEl = document.getElementById('gc-badge-mine');
const gcBadgeOppEl = document.getElementById('gc-badge-opp');
const boardLegendMineEl = document.getElementById('board-legend-mine');
const boardLegendOppEl = document.getElementById('board-legend-opp');
const boardLegendInfoEl = document.getElementById('board-legend-info');
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
const gameOverModal = document.getElementById('game-over-modal');
const gameOverMessage = document.getElementById('game-over-message');
const gameOverDismissBtn = document.getElementById('game-over-dismiss');
const gameOverBackdrop = document.getElementById('game-over-backdrop');
const btnDraw = document.getElementById('btn-draw');
const btnResign = document.getElementById('btn-resign');
const gameControlsConfirm = document.getElementById('game-controls-confirm');
const gameControlsDrawArea = document.getElementById('game-controls-draw-area');
const gameControlsDrawMsg = document.getElementById('game-controls-draw-msg');
const gameControlsDrawBtns = document.getElementById('game-controls-draw-btns');
const btnDrawAccept = document.getElementById('btn-draw-accept');
const btnDrawReject = document.getElementById('btn-draw-reject');

// ── State ─────────────────────────────────────────────────────────────────────

const testRoot = document.getElementById('test-root');
const gameId = testRoot?.dataset?.gameId || null;
const apiBase = gameId ? `/test/${encodeURIComponent(gameId)}` : null;
const myPlayer = parseInt(testRoot?.dataset?.playerNum) || null;
const isMultiplayer = testRoot?.dataset?.multiplayer === 'true';
const minePlayer = (isMultiplayer && myPlayer) ? myPlayer : 1;
const oppPlayer = minePlayer === 1 ? 2 : 1;

if (gcBadgeMineEl) {
    gcBadgeMineEl.textContent = `P${minePlayer}`;
    gcBadgeMineEl.classList.add(`gc-player-badge--p${minePlayer}`);
}
if (gcBadgeOppEl) {
    gcBadgeOppEl.textContent = `P${oppPlayer}`;
    gcBadgeOppEl.classList.add(`gc-player-badge--p${oppPlayer}`);
}
if (boardLegendMineEl) {
    boardLegendMineEl.className = `board-legend-item board-legend-item--p${minePlayer}`;
}
if (boardLegendOppEl) {
    boardLegendOppEl.className = `board-legend-item board-legend-item--p${oppPlayer}`;
}

let bankPollTimer = null;
let clockRenderTimer = null;
let resignConfirmPending = false;
// drawUiState: 'idle' | 'confirm' | 'offering' | 'cooldown' | 'received'
let drawUiState = 'idle';
let drawCooldownEnd = null;
let drawCooldownTimer = null;
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
let clockSnapshot = null;
let phaseSnapshot = null;
let lastReplayKey = null;
let replayInFlight = false;
let stepDelayMs = 500;
let gameOverModalShown = false;
let hasSignaledBeginWrite = false;

if (gameOverDismissBtn) {
    gameOverDismissBtn.addEventListener('click', hideGameOverModal);
}
if (gameOverBackdrop) {
    gameOverBackdrop.addEventListener('click', hideGameOverModal);
}

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

        // Show the latest board and actual server phase immediately.
        const initState = await get(`${apiBase}/state`);
        applySessionState(initState);
        renderBoard(initState);
        markReplaySeen(initState);
        startClockRender();

        wordBankEl.innerHTML = `<strong>${Math.floor(lastBank)}</strong> words in bank`;
        startBankPoll();
    } catch (e) {
        setStatus('error');
        setPhase('error');
        sessionIdEl.textContent = 'failed to initialise';
    }
}

// ── Word bank polling ─────────────────────────────────────────────────────────

function startBankPoll() {
    if (bankPollTimer) {
        clearInterval(bankPollTimer);
        bankPollTimer = null;
    }
    refreshBank();
    bankPollTimer = setInterval(refreshBank, 500);
}

async function refreshBank() {
    if (!gameId || !bankPollTimer) return;
    try {
        const state = await get(`${apiBase}/state`);
        const bank = state.word_bank?.[1] ?? 0;
        lastBank = bank;
        lastRate = state.word_rate ?? (1 / 3);
        wordBankEl.innerHTML = `<strong>${Math.floor(bank)}</strong> words in bank`;
        applySessionState(state);
        await replayPolledExecution(state);
        if (state?.game_over === true && bankPollTimer) {
            clearInterval(bankPollTimer);
            bankPollTimer = null;
        }
        updateWordEta();
        updateDeployButton();
        updateWordShortageNotice();
    } catch (_) {
        // ignore transient poll failures
    }
}

// ── Draw / Resign controls ────────────────────────────────────────────────────

function clearConfirm() {
    gameControlsConfirm.hidden = true;
    gameControlsConfirm.textContent = '';
    resignConfirmPending = false;
    if (drawUiState === 'confirm') {
        drawUiState = 'idle';
    }
}

function setBtnDrawNormal() {
    btnDraw.disabled = false;
    btnDraw.classList.remove('game-controls-btn--is-danger', 'btn-danger-hover');
    btnDraw.classList.add('btn-warn-hover');
    btnDraw.querySelector('.material-symbols-outlined').textContent = 'handshake';
    btnDraw.querySelector('.icon-btn-label').textContent = 'Draw';
}

function setBtnDrawCancel() {
    btnDraw.disabled = false;
    btnDraw.classList.remove('btn-warn-hover');
    btnDraw.classList.add('game-controls-btn--is-danger', 'btn-danger-hover');
    btnDraw.querySelector('.material-symbols-outlined').textContent = 'close';
    btnDraw.querySelector('.icon-btn-label').textContent = 'Cancel';
}

function setBtnDrawCooldown(seconds) {
    btnDraw.disabled = true;
    btnDraw.classList.remove('game-controls-btn--is-danger', 'btn-danger-hover');
    btnDraw.classList.add('btn-warn-hover');
    btnDraw.querySelector('.material-symbols-outlined').textContent = 'handshake';
    btnDraw.querySelector('.icon-btn-label').textContent = `${seconds}s`;
}

function startDrawCooldown(remainingSeconds) {
    drawUiState = 'cooldown';
    gameControlsDrawArea.hidden = true;
    if (drawCooldownTimer) {
        clearInterval(drawCooldownTimer);
        drawCooldownTimer = null;
    }
    drawCooldownEnd = Date.now() + remainingSeconds * 1000;
    setBtnDrawCooldown(Math.ceil(remainingSeconds));
    drawCooldownTimer = setInterval(() => {
        const remaining = Math.ceil((drawCooldownEnd - Date.now()) / 1000);
        if (remaining <= 0) {
            clearInterval(drawCooldownTimer);
            drawCooldownTimer = null;
            drawCooldownEnd = null;
            drawUiState = 'idle';
            setBtnDrawNormal();
        } else {
            setBtnDrawCooldown(remaining);
        }
    }, 250);
}

function renderDrawUiState() {
    switch (drawUiState) {
        case 'idle':
            setBtnDrawNormal();
            gameControlsDrawArea.hidden = true;
            break;
        case 'confirm':
            setBtnDrawNormal();
            gameControlsDrawArea.hidden = true;
            break;
        case 'offering':
            setBtnDrawCancel();
            gameControlsDrawMsg.textContent = "You're offering a draw";
            gameControlsDrawBtns.hidden = true;
            gameControlsDrawArea.hidden = false;
            if (!resignConfirmPending) clearConfirm();
            break;
        case 'received':
            setBtnDrawNormal();
            gameControlsDrawMsg.textContent = `P${oppPlayer} offered a draw`;
            gameControlsDrawBtns.hidden = false;
            gameControlsDrawArea.hidden = false;
            if (!resignConfirmPending) clearConfirm();
            break;
        // 'cooldown' is managed entirely by startDrawCooldown / its interval
    }
}

function applyDrawOffer(drawOffer) {
    if (!drawOffer) return;
    const offeredBy = drawOffer.offered_by;
    const myRemainingCooldown = drawOffer.cooldown?.[minePlayer] ?? null;

    if (offeredBy === minePlayer) {
        if (drawUiState !== 'offering') {
            drawUiState = 'offering';
            renderDrawUiState();
        }
    } else if (offeredBy === oppPlayer) {
        if (drawUiState !== 'received') {
            drawUiState = 'received';
            renderDrawUiState();
        }
    } else if (myRemainingCooldown !== null && myRemainingCooldown > 0) {
        if (drawUiState !== 'cooldown') {
            startDrawCooldown(myRemainingCooldown);
        }
    } else {
        // No active offer, no cooldown
        if (drawUiState === 'offering' || drawUiState === 'received') {
            drawUiState = 'idle';
            renderDrawUiState();
        }
        // 'confirm' and 'cooldown' persist until user or timer resolves them
    }
}

if (btnDraw) {
    btnDraw.addEventListener('click', async () => {
        if (btnDraw.disabled) return;

        if (drawUiState === 'offering') {
            try {
                await post(`${apiBase}/cancel_draw`, { player: minePlayer });
            } catch (_) {}
            drawUiState = 'idle';
            renderDrawUiState();
            return;
        }

        if (drawUiState === 'confirm') {
            // Second click — send offer
            const prevState = drawUiState;
            drawUiState = 'idle';
            clearConfirm();
            try {
                await post(`${apiBase}/offer_draw`, { player: minePlayer });
                drawUiState = 'offering';
                renderDrawUiState();
            } catch (_) {
                drawUiState = 'idle';
            }
            return;
        }

        // First click — show confirm prompt
        resignConfirmPending = false;
        drawUiState = 'confirm';
        gameControlsConfirm.textContent = 'Click Draw again to confirm';
        gameControlsConfirm.hidden = false;
    });
}

if (btnResign) {
    btnResign.addEventListener('click', async () => {
        if (resignConfirmPending) {
            resignConfirmPending = false;
            gameControlsConfirm.hidden = true;
            gameControlsConfirm.textContent = '';
            try {
                await post(`${apiBase}/resign`, { player: minePlayer });
                if (!bankPollTimer) startBankPoll();
                refreshBank();
            } catch (_) {}
            return;
        }
        if (drawUiState === 'confirm') {
            drawUiState = 'idle';
        }
        resignConfirmPending = true;
        gameControlsConfirm.textContent = 'Click Resign again to confirm';
        gameControlsConfirm.hidden = false;
    });
}

function handleConfirmBlur() {
    setTimeout(() => {
        const a = document.activeElement;
        if (a !== btnDraw && a !== btnResign && a !== btnDrawAccept && a !== btnDrawReject) {
            if (resignConfirmPending || drawUiState === 'confirm') {
                clearConfirm();
            }
        }
    }, 150);
}

if (btnDraw) btnDraw.addEventListener('blur', handleConfirmBlur);
if (btnResign) btnResign.addEventListener('blur', handleConfirmBlur);

if (btnDrawAccept) {
    btnDrawAccept.addEventListener('click', async () => {
        try {
            await post(`${apiBase}/accept_draw`, { player: minePlayer });
            drawUiState = 'idle';
            gameControlsDrawArea.hidden = true;
            if (!bankPollTimer) startBankPoll();
            refreshBank();
        } catch (_) {}
    });
}

if (btnDrawReject) {
    btnDrawReject.addEventListener('click', async () => {
        try {
            await post(`${apiBase}/reject_draw`, { player: minePlayer });
            drawUiState = 'idle';
            gameControlsDrawArea.hidden = true;
        } catch (_) {}
    });
}

function signalBeginWrite() {
    if (!gameId || hasSignaledBeginWrite) {
        return;
    }
    hasSignaledBeginWrite = true;
    post(`${apiBase}/begin_write`, { player: minePlayer }).catch(() => {});
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
    const data = await post(`${apiBase}/compile`, {
        player: isMultiplayer ? myPlayer : 1,
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
        setPhase('Exec 1', false, minePlayer);
        setSessionReady(false);

        const data = await post(`${apiBase}/deploy`, {
            player: isMultiplayer ? myPlayer : 1,
            source: editor.value,
        });

        if (!data.ok) {
            // Server-side compile failure (race condition / shouldn't normally happen)
            compileState = { errors: data.errors ?? [], warnings: data.warnings ?? [] };
            deployConfirmPending = false;
            clearDiagnostics();
            renderDiagnostics(data);
            // If deploy is rejected, remain in write phase.
            setPhase('Write', true, minePlayer);
            setSessionReady(true);
            return;
        }

        compileState = null;
        deployConfirmPending = false;

        // Fetch exec log, territory, and board from game state
        const state = await get(`${apiBase}/state`);
        applySessionState(state);
        replayInFlight = true;
        try {
            await replayExecution(preExecState, state, isMultiplayer ? myPlayer : 1);
        } finally {
            replayInFlight = false;
        }
        markReplaySeen(state);
        maybeShowGameOverModal(state);
    } catch (e) {
        renderNetworkError(diagBadge, diagBody, e.message);
    } finally {
        setBothButtonsDisabled(false);
        updateDeployButton();
        updateWordShortageNotice();
    }
});

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

    signalBeginWrite();
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
            await delay(stepDelayMs);
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

    updateBoardCoverage(board);
}

function updateBoardCoverage(board) {
    if (!boardLegendMineEl || !boardLegendOppEl || !Array.isArray(board) || board.length === 0) {
        return;
    }

    let p1Owned = 0;
    let p2Owned = 0;
    const total = board.length * board.length;

    for (const row of board) {
        for (const cell of row) {
            if (!cell) {
                continue;
            }
            if (cell.p1 > cell.p2) {
                p1Owned += 1;
            } else if (cell.p2 > cell.p1) {
                p2Owned += 1;
            }
        }
    }

    const mineOwned = minePlayer === 1 ? p1Owned : p2Owned;
    const oppOwned  = minePlayer === 1 ? p2Owned : p1Owned;
    const minePct = total > 0 ? ((mineOwned / total) * 100).toFixed(1) : '0.0';
    const oppPct  = total > 0 ? ((oppOwned  / total) * 100).toFixed(1) : '0.0';

    boardLegendMineEl.textContent = `P${minePlayer} ${mineOwned} (${minePct}%)`;
    boardLegendOppEl.textContent  = `P${oppPlayer} ${oppOwned} (${oppPct}%)`;

    if (boardLegendInfoEl) {
        const threshold = Math.ceil(total * 0.6);
        boardLegendInfoEl.textContent = `${total} cells · Win: ${threshold}`;
    }
}

// ── Status helpers ────────────────────────────────────────────────────────────

function setStatus(state) {
    statusDot.className = `status-dot status-dot--${state}`;
}

function setPhase(text, highlight = false, player = 0) {
    phaseSnapshot = null;
    _applyPhaseToElements(text, highlight ? 'phase-pill phase-pill--write' : 'phase-pill', player);
}

function _applyPhaseToElements(text, className, player) {
    const isMine = player === minePlayer || player === 0;
    const activeEl = isMine ? gcPhaseMineEl : gcPhaseOppEl;
    const inactiveEl = isMine ? gcPhaseOppEl : gcPhaseMineEl;
    if (!activeEl || !inactiveEl) return;
    activeEl.textContent = text;
    activeEl.className = className;
    activeEl.hidden = false;
    inactiveEl.textContent = '';
    inactiveEl.hidden = true;
}

function phasePillClass(isWrite, player) {
    const classes = ['phase-pill'];
    if (player === 1) {
        classes.push('phase-pill--p1');
    } else if (player === 2) {
        classes.push('phase-pill--p2');
    }
    if (isWrite) {
        classes.push('phase-pill--write');
    }
    return classes.join(' ');
}

function applySessionState(state) {
    const phase = state?.phase ?? 'unknown';
    const isWrite = phase === 'write';
    const currentPlayer = Number(state?.current_player ?? 0);
    const isMyTurn = isMultiplayer
        ? currentPlayer === myPlayer
        : currentPlayer === 1;
    updateStepDelayFromState(state);
    updatePhaseSnapshot(state);
    updateClockSnapshot(state);
    setSessionReady(isWrite && isMyTurn && state?.game_over !== true);
    maybeShowGameOverModal(state);
    applyDrawOffer(state?.draw_offer);
}

function maybeShowGameOverModal(state) {
    if (!state || state.game_over !== true || gameOverModalShown || !gameOverModal || !gameOverMessage) {
        return;
    }
    // Keep modal aligned with what the player sees on board/log replay.
    if (replayInFlight || hasUnreplayedAnimation(state)) {
        return;
    }
    gameOverModalShown = true;

    const winner = state.winner;
    const reason = state.end_reason;
    if (reason === 'resign') {
        const resignedPlayer = 3 - winner;
        gameOverMessage.textContent = winner === minePlayer
            ? `Win by resignation: P${resignedPlayer} resigned.`
            : `Loss by resignation: P${resignedPlayer} resigned.`;
    } else if (reason === 'timeout') {
        gameOverMessage.textContent = winner === 1
            ? 'Win by timeout: P2 ran out of write time.'
            : 'Loss by timeout: P1 ran out of write time.';
    } else if (reason === 'territory') {
        gameOverMessage.textContent = winner === 1
            ? 'Win by board control: P1 reached the territory threshold.'
            : 'Loss by board control: P2 reached the territory threshold.';
    } else if (reason === 'draw_offer') {
        gameOverMessage.textContent = 'Draw by mutual agreement.';
    } else if (reason === 'stalemate' || winner === 'draw') {
        gameOverMessage.textContent = 'Stalemate: neither player can still mathematically reach the territory threshold.';
    } else {
        gameOverMessage.textContent = winner === 1
            ? 'Game over: P1 wins.'
            : winner === 2
                ? 'Game over: P2 wins.'
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
    if (!Number.isFinite(stepSeconds) || stepSeconds <= 0) {
        return;
    }
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
    if (!phaseSnapshot) {
        return;
    }

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

    if (phase === 'anim_post_exec1' || phase === 'exec1') {
        return 'Exec 1';
    }
    if (phase === 'anim_pre_write' || phase === 'exec2') {
        return 'Exec 2';
    }
    if (phase === 'opening_pre_write') {
        return 'Pre-Write';
    }
    if (phase === 'write') {
        return 'Write';
    }
    return phase;
}

function updateClockSnapshot(state) {
    if (!state || !state.clock) {
        return;
    }
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
    if (!gcClockMineEl || !gcClockOppEl) return;

    if (!clockSnapshot) {
        gcClockMineEl.textContent = '--:--';
        gcClockOppEl.textContent = '--:--';
        return;
    }

    let p1 = clockSnapshot.p1;
    let p2 = clockSnapshot.p2;

    if (!clockSnapshot.gameOver && clockSnapshot.phase === 'write') {
        const elapsed = Math.max(0, (performance.now() - clockSnapshot.sampledAt) / 1000);
        if (clockSnapshot.currentPlayer === 1) {
            p1 = Math.max(0, p1 - elapsed);
        } else {
            p2 = Math.max(0, p2 - elapsed);
        }
    }

    gcClockMineEl.textContent = formatClock(minePlayer === 1 ? p1 : p2);
    gcClockOppEl.textContent = formatClock(oppPlayer === 1 ? p1 : p2);
}

function formatClock(seconds) {
    const safe = Number.isFinite(seconds) ? Math.max(0, Math.floor(seconds)) : 0;
    const mins = Math.floor(safe / 60);
    const secs = safe % 60;
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

function replayKeyForState(state) {
    const log = state?.exec_log ?? [];
    const actor = Number(state?.last_exec_player ?? state?.current_player ?? 0);
    const consumed = Number(state?.exec_ops_consumed ?? 0);
    return `${actor}|${consumed}|${JSON.stringify(log)}`;
}

function hasUnreplayedAnimation(state) {
    if (!state) {
        return false;
    }
    const log = state.exec_log ?? [];
    if (!Array.isArray(log) || log.length === 0) {
        return false;
    }
    return replayKeyForState(state) !== lastReplayKey;
}

function markReplaySeen(state) {
    lastReplayKey = replayKeyForState(state);
}

async function replayPolledExecution(state) {
    if (!state || replayInFlight) {
        return;
    }

    const key = replayKeyForState(state);
    if (key === lastReplayKey) {
        if (lastBoardState !== state) {
            renderBoard(state);
        }
        maybeShowGameOverModal(state);
        return;
    }

    const actor = Number(state?.last_exec_player ?? state?.current_player ?? 1);
    const preExecState = cloneBoardAndAgents(lastBoardState);
    replayInFlight = true;
    try {
        await replayExecution(preExecState, state, actor === 2 ? 2 : 1);
    } finally {
        replayInFlight = false;
    }
    markReplaySeen(state);
    maybeShowGameOverModal(state);
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
