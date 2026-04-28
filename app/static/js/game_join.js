(function () {
    'use strict';

    const root = document.getElementById('join-root');
    const gameId = root?.dataset?.gameId || null;

    const p1ReadyDot = document.getElementById('p1-ready-dot');
    const p1ReadyLabel = document.getElementById('p1-ready-label');
    const joinError = document.getElementById('join-error');
    const leaveBtn = document.getElementById('leave-btn');
    const p2ReadyBtn = document.getElementById('p2-ready-btn');
    const joinBody = document.getElementById('join-body');
    const settingSize = document.getElementById('join-setting-size');
    const settingClock = document.getElementById('join-setting-clock');
    const settingOpLimit = document.getElementById('join-setting-op-limit');
    const settingWordRate = document.getElementById('join-setting-word-rate');
    const settingStartingWords = document.getElementById('join-setting-starting-words');
    const accSection = document.getElementById('join-accommodations-section');
    const accMyClock = document.getElementById('join-acc-my-clock');
    const accOppClock = document.getElementById('join-acc-opp-clock');
    const accMyWords = document.getElementById('join-acc-my-words');
    const accOppWords = document.getElementById('join-acc-opp-words');
    const accStartingPlayer = document.getElementById('join-acc-starting-player');

    const myUsername = root?.dataset?.myUsername || '';
    const p1Username = root?.dataset?.p1Username || 'Opponent';

    let pollInterval = null;
    let p2IsReady = false;

    function showError(message) {
        if (!joinError) return;
        if (!message) {
            joinError.hidden = true;
            joinError.textContent = '';
            return;
        }
        joinError.hidden = false;
        joinError.textContent = message;
    }

    function setP1ReadyState(ready, username) {
        const name = username || 'Player 1';
        if (p1ReadyDot) {
            p1ReadyDot.className = ready
                ? 'flex-shrink-0 status-dot status-dot--ok'
                : 'flex-shrink-0 status-dot status-dot--warn';
        }
        if (p1ReadyLabel) {
            p1ReadyLabel.textContent = ready ? `${name} ready` : `${name} not ready`;
        }
    }

    function fmtMins(seconds) {
        return String(+(seconds / 60));
    }

    function fmtStartingPlayer(value) {
        if (value === 'random' || value == null) return 'Random';
        // P2 (me) is the joiner; P1 (opponent) is the creator
        if (Number(value) === 2) return myUsername ? `Me (${myUsername})` : 'Me';
        return p1Username ? `Opponent (${p1Username})` : 'Opponent';
    }

    function applySettings(settings) {
        if (!settings) return;
        if (settingSize) settingSize.textContent = `${settings.size} × ${settings.size}`;
        if (settingClock) settingClock.textContent = fmtMins(settings.clock_seconds);
        if (settingOpLimit) settingOpLimit.textContent = settings.op_limit;
        if (settingWordRate) settingWordRate.textContent = `${settings.word_rate} / s`;
        if (settingStartingWords) settingStartingWords.textContent = Math.floor(settings.p2_starting_words);

        if (accSection) {
            accSection.hidden = !settings.accommodations_enabled;
            if (settings.accommodations_enabled) {
                if (accMyClock) accMyClock.textContent = fmtMins(settings.p2_clock_seconds);
                if (accOppClock) accOppClock.textContent = fmtMins(settings.p1_clock_seconds);
                if (accMyWords) accMyWords.textContent = settings.p2_starting_words;
                if (accOppWords) accOppWords.textContent = settings.p1_starting_words;
                if (accStartingPlayer) accStartingPlayer.textContent = fmtStartingPlayer(settings.starting_player);
            }
        }
    }

    function startPolling() {
        if (pollInterval !== null) return;
        pollInterval = setInterval(pollLobby, 1000);
    }

    function stopPolling() {
        if (pollInterval !== null) {
            clearInterval(pollInterval);
            pollInterval = null;
        }
    }

    function showLobbyDeleted() {
        stopPolling();
        if (!joinBody) return;
        joinBody.innerHTML =
            '<p class="text-dim">This lobby no longer exists. Ask the host for a new link.</p>';
    }

    async function pollLobby() {
        try {
            const resp = await fetch(`/game/${encodeURIComponent(gameId)}/lobby`);
            if (resp.status === 404) {
                showLobbyDeleted();
                return;
            }
            if (!resp.ok) return;
            const data = await resp.json();

            setP1ReadyState(data.player1_ready, data.player1_username);
            applySettings(data.settings);

            if (data.started || data.both_ready) {
                stopPolling();
                window.location.href = `/game/${encodeURIComponent(gameId)}`;
            }
        } catch (_) {
            // silently retry
        }
    }

    async function joinGame() {
        try {
            const resp = await fetch(`/game/${encodeURIComponent(gameId)}/join`, {
                method: 'POST',
            });

            if (resp.status === 401) {
                showError('You must be logged in to join.');
                return;
            }
            if (resp.status === 409) {
                showError('This game is full.');
                return;
            }
            if (resp.status === 400) {
                const data = await resp.json();
                showError(data.error || 'Cannot join this game.');
                return;
            }
            if (!resp.ok) {
                showError('Failed to join game.');
                return;
            }

            if (p2ReadyBtn) p2ReadyBtn.disabled = false;
            startPolling();
        } catch (error) {
            showError(error?.message || 'Network error while joining game.');
        }
    }

    async function handleReady() {
        if (!gameId) return;
        p2ReadyBtn.disabled = true;
        try {
            const resp = await fetch(`/game/${encodeURIComponent(gameId)}/ready`, {
                method: 'POST',
            });
            if (resp.status === 401) {
                showError('You must be logged in.');
                return;
            }
            if (!resp.ok) return;
            const data = await resp.json();
            p2IsReady = data.ready;
            p2ReadyBtn.textContent = p2IsReady ? 'Cancel ready' : 'Ready';
            if (data.both_ready) {
                stopPolling();
                window.location.href = `/game/${encodeURIComponent(gameId)}`;
            }
        } catch (_) {
        } finally {
            p2ReadyBtn.disabled = false;
        }
    }

    async function handleLeave() {
        if (!gameId) {
            window.location.href = '/game/new';
            return;
        }
        try {
            await fetch(`/game/${encodeURIComponent(gameId)}/leave`, { method: 'POST' });
        } catch (_) {}
        stopPolling();
        window.location.href = '/game/new';
    }

    if (!gameId) {
        showError('Missing game ID.');
        return;
    }

    if (leaveBtn) leaveBtn.addEventListener('click', handleLeave);
    if (p2ReadyBtn) p2ReadyBtn.addEventListener('click', handleReady);

    joinGame();
})();
