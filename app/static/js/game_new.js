(function () {
    'use strict';

    const presetsEl = document.getElementById('presets-json');
    const defaultPresetEl = document.getElementById('default-preset-json');
    const userCustomDefaultsEl = document.getElementById('user-custom-defaults-json');
    const userAccomDefaultsEl = document.getElementById('user-accom-defaults-json');

    let presets = {};
    let defaultPreset = '5';
    let userCustomDefaults = null;
    let userAccomDefaults = null;

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
    if (userCustomDefaultsEl?.textContent) {
        try {
            userCustomDefaults = JSON.parse(userCustomDefaultsEl.textContent);
        } catch (_) {
            userCustomDefaults = null;
        }
    }
    if (userAccomDefaultsEl?.textContent) {
        try {
            userAccomDefaults = JSON.parse(userAccomDefaultsEl.textContent);
        } catch (_) {
            userAccomDefaults = null;
        }
    }

    const createRoot = document.getElementById('create-root');
    const myUsername = createRoot?.dataset?.username || '';
    const startingOptMe = document.getElementById('starting-opt-me');
    const startingOptOpp = document.getElementById('starting-opt-opp');

    const errorBox = document.getElementById('create-error');
    const linkDisplay = document.getElementById('link-display');
    const linkDisplayUrl = document.getElementById('link-display-url');
    const presetButtons = Array.from(document.querySelectorAll('[data-preset]'));
    const copyLinkBtn = document.getElementById('copy-link-btn');
    const presetInviteBtn = document.getElementById('preset-invite-btn');
    const inviteFriendBtn = document.getElementById('invite-friend-btn');
    const inviteFriendList = document.getElementById('invite-friend-list');
    const lobbyPanel = document.getElementById('lobby-panel');
    const joinDot = document.getElementById('join-dot');
    const joinLabel = document.getElementById('join-label');
    const lobbyActions = document.getElementById('lobby-actions');
    const newLinkBtn = document.getElementById('new-link-btn');
    const revokeInviteBtn = document.getElementById('revoke-invite-btn');
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
    let customDefaultsActive = false;
    let accomDefaultsActive = false;
    let currentGameId = null;
    let pollInterval = null;
    let p1IsReady = false;
    let inviteMode = false;

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
            button.classList.toggle('warm', active);
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

    function syncDefaultsNotice() {
        const notice = document.getElementById('defaults-loaded-notice');
        if (!notice) return;
        const showForAccom = accomDefaultsActive && fields.accommodations_enabled.checked;
        notice.hidden = !(customDefaultsActive || showForAccom);
    }

    function syncAccommodations() {
        const enabled = fields.accommodations_enabled.checked;
        fields.accommodations_section.hidden = !enabled;

        if (enabled && selectedPreset !== 'custom') {
            selectPreset('custom', { keepValues: true });
        }

        if (!enabled) {
            syncDefaultsNotice();
            return;
        }

        const accomFieldsAllEmpty = (
            fields.p1_clock_seconds.value === '' &&
            fields.p2_clock_seconds.value === '' &&
            fields.p1_starting_words.value === '' &&
            fields.p2_starting_words.value === ''
        );

        if (accomFieldsAllEmpty && userAccomDefaults) {
            fields.p1_clock_seconds.value = String(+(userAccomDefaults.p1_clock_seconds / 60));
            fields.p2_clock_seconds.value = String(+(userAccomDefaults.p2_clock_seconds / 60));
            fields.p1_starting_words.value = String(userAccomDefaults.p1_starting_words);
            fields.p2_starting_words.value = String(userAccomDefaults.p2_starting_words);
            if (fields.starting_player) {
                fields.starting_player.value = String(userAccomDefaults.starting_player);
            }
            accomDefaultsActive = true;
        } else if (accomFieldsAllEmpty) {
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

        syncDefaultsNotice();
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

    function resetLobbyUI() {
        stopPolling();
        p1IsReady = false;
        inviteMode = false;
        currentGameId = null;
        if (p1ReadyBtn) {
            p1ReadyBtn.textContent = 'Ready';
            p1ReadyBtn.disabled = false;
        }
        if (joinDot) joinDot.className = 'status-dot status-dot--pending';
        if (joinLabel) joinLabel.textContent = 'Waiting for player to join…';
        if (lobbyActions) lobbyActions.hidden = true;
        if (newLinkBtn) newLinkBtn.hidden = false;
        if (revokeInviteBtn) revokeInviteBtn.hidden = true;
        if (lobbyPanel) lobbyPanel.hidden = true;
        if (linkDisplay) linkDisplay.hidden = true;
        updateStartingPlayerOptions(null);
    }

    async function _createLobby(payload, triggeredByBtn) {
        setError('');
        if (triggeredByBtn) triggeredByBtn.disabled = true;

        if (currentGameId) {
            try {
                await fetch(`/game/${encodeURIComponent(currentGameId)}/close`, { method: 'POST' });
            } catch (_) {}
        }

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

        try {
            const response = await fetch('/game/lobby', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            if (response.status === 401) {
                window.location.href = '/login?next=/game/new';
                return null;
            }

            const data = await response.json();
            if (!response.ok) {
                setError(data.error || 'Failed to create game.');
                return null;
            }

            if (!data.game_id) {
                setError('Server did not return a game id.');
                return null;
            }

            currentGameId = data.game_id;
            if (lobbyPanel) lobbyPanel.hidden = false;
            startLobbyPoll(data.game_id);
            return data;
        } catch (error) {
            setError(error?.message || 'Network error while creating game.');
            return null;
        } finally {
            if (triggeredByBtn) triggeredByBtn.disabled = false;
        }
    }

    async function handleCopyLink() {
        inviteMode = false;
        if (newLinkBtn) newLinkBtn.hidden = false;
        if (revokeInviteBtn) revokeInviteBtn.hidden = true;

        const data = await _createLobby(buildPayload(), copyLinkBtn);
        if (!data) return;

        const alias = data.join_alias;
        const joinUrl = alias
            ? `${location.origin}/join/${encodeURIComponent(alias)}`
            : `${location.origin}/game/${encodeURIComponent(data.game_id)}/join`;
        let copied = false;
        try {
            await navigator.clipboard.writeText(joinUrl);
            copied = true;
        } catch (_) {}
        if (linkDisplay) {
            linkDisplay.firstChild.textContent = copied ? 'Copied link: ' : 'Copy this link: ';
            if (linkDisplayUrl) linkDisplayUrl.textContent = joinUrl;
            linkDisplay.hidden = false;
        }
    }

    async function handleInviteFriend(friendId, friendUsername) {
        inviteMode = true;
        if (newLinkBtn) newLinkBtn.hidden = true;
        if (revokeInviteBtn) revokeInviteBtn.hidden = false;
        if (linkDisplay) linkDisplay.hidden = true;

        const payload = Object.assign(buildPayload(), { invited_user_id: friendId });
        const data = await _createLobby(payload, null);
        if (!data) {
            inviteMode = false;
            if (newLinkBtn) newLinkBtn.hidden = false;
            if (revokeInviteBtn) revokeInviteBtn.hidden = true;
            return;
        }

        if (joinLabel) joinLabel.textContent = `Waiting for ${friendUsername} to join…`;
    }

    async function handleRevokeInvite() {
        if (currentGameId) {
            try {
                await fetch(`/game/${encodeURIComponent(currentGameId)}/close`, { method: 'POST' });
            } catch (_) {}
        }
        resetLobbyUI();
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
            customDefaultsActive = false;
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
        if (input) input.addEventListener('input', () => {
            customDefaultsActive = false;
            syncDefaultsNotice();
            schedulePatchSettings();
        });
    });

    [fields.p1_clock_seconds, fields.p2_clock_seconds, fields.p1_starting_words, fields.p2_starting_words, fields.starting_player].forEach((input) => {
        if (input) input.addEventListener('input', () => {
            accomDefaultsActive = false;
            syncDefaultsNotice();
            schedulePatchSettings();
        });
    });

    if (copyLinkBtn) copyLinkBtn.addEventListener('click', handleCopyLink);
    if (p1ReadyBtn) p1ReadyBtn.addEventListener('click', handleReady);
    if (newLinkBtn) newLinkBtn.addEventListener('click', handleNewLink);
    if (revokeInviteBtn) revokeInviteBtn.addEventListener('click', handleRevokeInvite);
    if (presetInviteBtn) {
        presetInviteBtn.addEventListener('click', () => {
            handleInviteFriend(
                Number(presetInviteBtn.dataset.friendId),
                presetInviteBtn.dataset.friendUsername || 'friend',
            );
        });
    }

    if (inviteFriendBtn && inviteFriendList) {
        inviteFriendBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            const open = !inviteFriendList.hidden;
            inviteFriendList.hidden = open;
            inviteFriendBtn.setAttribute('aria-expanded', String(!open));
        });
        inviteFriendList.addEventListener('click', (e) => {
            const item = e.target.closest('[data-friend-id]');
            if (!item) return;
            const friendId = Number(item.dataset.friendId);
            const friendUsername = item.dataset.friendUsername || 'friend';
            inviteFriendList.hidden = true;
            inviteFriendBtn.setAttribute('aria-expanded', 'false');
            handleInviteFriend(friendId, friendUsername);
        });
        document.addEventListener('click', (e) => {
            if (!inviteFriendList.hidden && !inviteFriendBtn.contains(e.target) && !inviteFriendList.contains(e.target)) {
                inviteFriendList.hidden = true;
                inviteFriendBtn.setAttribute('aria-expanded', 'false');
            }
        });
    }

    selectPreset(defaultPreset);
    if (defaultPreset === 'custom') {
        if (userCustomDefaults) {
            applyCoreValues(userCustomDefaults);
            customDefaultsActive = true;
        } else {
            applyCoreValues(presets['5']);
        }
    }
    syncAccommodations();
    syncDefaultsNotice();
    updateStartingPlayerOptions(null);
})();
