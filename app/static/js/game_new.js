(function () {
    'use strict';

    const presetsEl = document.getElementById('test-presets-json');
    const defaultPresetEl = document.getElementById('test-default-preset-json');

    let presets = {};
    let defaultPreset = '5';

    if (presetsEl?.textContent) {
        try {
            presets = JSON.parse(presetsEl.textContent);
        } catch (_) {
            presets = {};
        }
    }
    if (defaultPresetEl?.textContent) {
        try {
            defaultPreset = JSON.parse(defaultPresetEl.textContent) || '5';
        } catch (_) {
            defaultPreset = '5';
        }
    }

    const createRoot = document.getElementById('test-create-root');
    const myUsername = createRoot?.dataset?.username || '';
    const startingOptMe = document.getElementById('starting-opt-me');
    const startingOptOpp = document.getElementById('starting-opt-opp');

    const errorBox = document.getElementById('test-create-error');
    const presetButtons = Array.from(document.querySelectorAll('[data-preset]'));
    const copyLinkBtn = document.getElementById('copy-link-btn');
    const lobbyPanel = document.getElementById('lobby-panel');
    const joinDot = document.getElementById('join-dot');
    const joinLabel = document.getElementById('join-label');
    const lobbyActions = document.getElementById('lobby-actions');
    const newLinkBtn = document.getElementById('new-link-btn');
    const p1ReadyBtn = document.getElementById('p1-ready-btn');

    const fields = {
        clock_seconds: document.getElementById('clock_seconds'),
        board_size: document.getElementById('board_size'),
        op_limit: document.getElementById('op_limit'),
        word_rate: document.getElementById('word_rate'),
        starting_words: document.getElementById('starting_words'),
        accommodations_enabled: document.getElementById('accommodations_enabled'),
        p1_clock_seconds: document.getElementById('p1_clock_seconds'),
        p2_clock_seconds: document.getElementById('p2_clock_seconds'),
        p1_starting_words: document.getElementById('p1_starting_words'),
        p2_starting_words: document.getElementById('p2_starting_words'),
        starting_player: document.getElementById('starting_player'),
        accommodations_section: document.getElementById('accommodations-section'),
    };

    const coreInputs = [
        fields.clock_seconds,
        fields.board_size,
        fields.op_limit,
        fields.word_rate,
        fields.starting_words,
    ];

    let selectedPreset = 'custom';
    let currentGameId = null;
    let pollInterval = null;
    let p1IsReady = false;

    function setError(message) {
        if (!errorBox) return;
        if (!message) {
            errorBox.hidden = true;
            errorBox.textContent = '';
            return;
        }
        errorBox.hidden = false;
        errorBox.textContent = message;
    }

    function toNumber(value) {
        const parsed = Number(value);
        return Number.isFinite(parsed) ? parsed : null;
    }

    function readCoreValues() {
        return {
            // clock field is in minutes; convert to seconds for the server
            clock_seconds: toNumber(fields.clock_seconds.value) * 60,
            board_size: toNumber(fields.board_size.value),
            op_limit: toNumber(fields.op_limit.value),
            word_rate: toNumber(fields.word_rate.value),
            starting_words: toNumber(fields.starting_words.value),
        };
    }

    function applyCoreValues(values) {
        if (!values) return;
        // clock_seconds from preset is in seconds; display in minutes
        fields.clock_seconds.value = String(+(values.clock_seconds / 60));
        fields.board_size.value = String(values.board_size);
        fields.op_limit.value = String(values.op_limit);
        fields.word_rate.value = String(values.word_rate);
        fields.starting_words.value = String(values.starting_words);
    }

    function syncPresetButtonState() {
        presetButtons.forEach((button) => {
            const active = button.dataset.preset === selectedPreset;
            button.classList.toggle('is-active', active);
            button.setAttribute('aria-checked', active ? 'true' : 'false');
        });
    }

    function syncCoreDisabledState() {
        const disableCore = selectedPreset !== 'custom';
        coreInputs.forEach((input) => {
            if (input) input.disabled = disableCore;
        });
    }

    function selectPreset(preset, options) {
        const opts = options || {};
        const keepValues = Boolean(opts.keepValues);
        if (preset !== 'custom' && !presets[preset]) return;

        selectedPreset = preset;
        if (!keepValues && preset !== 'custom') {
            applyCoreValues(presets[preset]);
        }
        syncPresetButtonState();
        syncCoreDisabledState();
    }

    function syncAccommodations() {
        const enabled = fields.accommodations_enabled.checked;
        fields.accommodations_section.hidden = !enabled;

        if (enabled && selectedPreset !== 'custom') {
            selectPreset('custom', { keepValues: true });
        }

        if (!enabled) return;

        const core = readCoreValues();
        // core.clock_seconds is in seconds; accommodation fields are in minutes
        const clockMins = core.clock_seconds != null ? +(core.clock_seconds / 60) : '';
        if (fields.p1_clock_seconds.value === '') {
            fields.p1_clock_seconds.value = String(clockMins);
        }
        if (fields.p2_clock_seconds.value === '') {
            fields.p2_clock_seconds.value = String(clockMins);
        }
        if (fields.p1_starting_words.value === '') {
            fields.p1_starting_words.value = String(core.starting_words ?? '');
        }
        if (fields.p2_starting_words.value === '') {
            fields.p2_starting_words.value = String(core.starting_words ?? '');
        }
    }

    function buildPayload() {
        const payload = {
            preset: selectedPreset,
            accommodations_enabled: fields.accommodations_enabled.checked,
        };

        if (selectedPreset === 'custom') {
            const core = readCoreValues();
            payload.clock_seconds = core.clock_seconds;
            payload.board_size = core.board_size;
            payload.op_limit = core.op_limit;
            payload.word_rate = core.word_rate;
            payload.starting_words = core.starting_words;
        }

        if (fields.accommodations_enabled.checked) {
            // clock fields are in minutes in the DOM; convert to seconds for the server
            payload.p1_clock_seconds = toNumber(fields.p1_clock_seconds.value) * 60;
            payload.p2_clock_seconds = toNumber(fields.p2_clock_seconds.value) * 60;
            payload.p1_starting_words = toNumber(fields.p1_starting_words.value);
            payload.p2_starting_words = toNumber(fields.p2_starting_words.value);
            payload.starting_player = fields.starting_player.value;
        }

        return payload;
    }

    function stopPolling() {
        if (pollInterval !== null) {
            clearInterval(pollInterval);
            pollInterval = null;
        }
    }

    function startLobbyPoll(gameId) {
        stopPolling();
        pollInterval = setInterval(() => pollLobby(gameId), 1000);
    }

    function updateStartingPlayerOptions(joinerUsername) {
        if (startingOptMe) {
            startingOptMe.textContent = myUsername ? `Me (${myUsername})` : 'Me';
        }
        if (startingOptOpp) {
            startingOptOpp.textContent = joinerUsername ? `Opponent (${joinerUsername})` : 'Opponent';
        }
    }

    async function pollLobby(gameId) {
        try {
            const resp = await fetch(`/game/${encodeURIComponent(gameId)}/lobby`);
            if (!resp.ok) return;
            const data = await resp.json();

            if (data.started || data.both_ready) {
                stopPolling();
                window.location.href = `/game/${encodeURIComponent(gameId)}`;
                return;
            }

            if (data.player2_joined) {
                const name = data.player2_username || 'Player 2';
                joinDot.className = data.player2_ready
                    ? 'status-dot status-dot--ready'
                    : 'status-dot status-dot--pending';
                joinLabel.textContent = data.player2_ready ? `${name} ready` : `${name} joined`;
                lobbyActions.hidden = false;
                updateStartingPlayerOptions(data.player2_username);
            }
        } catch (_) {
            // network error — silently retry next interval
        }
    }

    async function handleCopyLink() {
        setError('');
        copyLinkBtn.disabled = true;

        // Close old lobby if re-generating
        if (currentGameId) {
            try {
                await fetch(`/game/${encodeURIComponent(currentGameId)}/close`, { method: 'POST' });
            } catch (_) {}
        }

        // Reset lobby UI state
        stopPolling();
        p1IsReady = false;
        if (p1ReadyBtn) {
            p1ReadyBtn.textContent = 'Ready';
            p1ReadyBtn.disabled = false;
        }
        if (joinDot) joinDot.className = 'status-dot status-dot--pending';
        if (joinLabel) joinLabel.textContent = 'Waiting for player to join…';
        if (lobbyActions) lobbyActions.hidden = true;
        updateStartingPlayerOptions(null);

        const payload = buildPayload();

        try {
            const response = await fetch('/game/lobby', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            if (response.status === 401) {
                window.location.href = '/login?next=/game/new';
                return;
            }

            const data = await response.json();
            if (!response.ok) {
                setError(data.error || 'Failed to create game.');
                return;
            }

            const gameId = data.game_id;
            if (!gameId) {
                setError('Server did not return a game id.');
                return;
            }

            currentGameId = gameId;
            const joinUrl = `${location.origin}/game/${encodeURIComponent(gameId)}/join`;
            try {
                await navigator.clipboard.writeText(joinUrl);
            } catch (_) {
                // Clipboard may fail in non-secure context — show the link as fallback
                setError(`Copy this link: ${joinUrl}`);
            }

            if (lobbyPanel) lobbyPanel.hidden = false;
            startLobbyPoll(gameId);
        } catch (error) {
            setError(error?.message || 'Network error while creating game.');
        } finally {
            copyLinkBtn.disabled = false;
        }
    }

    async function handleReady() {
        if (!currentGameId) return;
        p1ReadyBtn.disabled = true;
        try {
            const resp = await fetch(`/game/${encodeURIComponent(currentGameId)}/ready`, {
                method: 'POST',
            });
            if (resp.status === 401) {
                window.location.href = '/login?next=/game/new';
                return;
            }
            if (!resp.ok) return;
            const data = await resp.json();
            p1IsReady = data.ready;
            p1ReadyBtn.textContent = p1IsReady ? 'Cancel ready' : 'Ready';
            if (data.both_ready) {
                stopPolling();
                window.location.href = `/game/${encodeURIComponent(currentGameId)}`;
            }
        } catch (_) {
        } finally {
            p1ReadyBtn.disabled = false;
        }
    }

    async function handleNewLink() {
        await handleCopyLink();
    }

    let settingsPatchTimer = null;

    function schedulePatchSettings() {
        if (!currentGameId) return;
        clearTimeout(settingsPatchTimer);
        settingsPatchTimer = setTimeout(async () => {
            if (!currentGameId) return;
            try {
                await fetch(`/game/${encodeURIComponent(currentGameId)}/settings`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(buildPayload()),
                });
            } catch (_) {}
        }, 300);
    }

    presetButtons.forEach((button) => {
        button.addEventListener('click', () => {
            selectPreset(button.dataset.preset || 'custom');
            syncAccommodations();
            schedulePatchSettings();
        });
    });

    fields.accommodations_enabled.addEventListener('change', () => {
        syncAccommodations();
        schedulePatchSettings();
    });

    coreInputs.forEach((input) => {
        if (input) input.addEventListener('input', schedulePatchSettings);
    });

    [fields.p1_clock_seconds, fields.p2_clock_seconds, fields.p1_starting_words, fields.p2_starting_words, fields.starting_player].forEach((input) => {
        if (input) input.addEventListener('input', schedulePatchSettings);
    });

    if (copyLinkBtn) copyLinkBtn.addEventListener('click', handleCopyLink);
    if (p1ReadyBtn) p1ReadyBtn.addEventListener('click', handleReady);
    if (newLinkBtn) newLinkBtn.addEventListener('click', handleNewLink);

    selectPreset(defaultPreset);
    syncAccommodations();
    updateStartingPlayerOptions(null);
})();
