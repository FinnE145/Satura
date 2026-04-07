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

    const form = document.getElementById('test-create-form');
    const errorBox = document.getElementById('test-create-error');
    const presetButtons = Array.from(document.querySelectorAll('[data-preset]'));

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
        start_button: document.getElementById('start-test-game'),
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

    function setError(message) {
        if (!errorBox) {
            return;
        }
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
            clock_seconds: toNumber(fields.clock_seconds.value),
            board_size: toNumber(fields.board_size.value),
            op_limit: toNumber(fields.op_limit.value),
            word_rate: toNumber(fields.word_rate.value),
            starting_words: toNumber(fields.starting_words.value),
        };
    }

    function applyCoreValues(values) {
        if (!values) {
            return;
        }
        fields.clock_seconds.value = String(values.clock_seconds);
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
            if (input) {
                input.disabled = disableCore;
            }
        });
    }

    function selectPreset(preset, options) {
        const opts = options || {};
        const keepValues = Boolean(opts.keepValues);
        if (preset !== 'custom' && !presets[preset]) {
            return;
        }

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
            // Preserve the values from the selected preset while switching into custom mode.
            selectPreset('custom', { keepValues: true });
        }

        if (!enabled) {
            return;
        }

        const core = readCoreValues();
        if (fields.p1_clock_seconds.value === '') {
            fields.p1_clock_seconds.value = String(core.clock_seconds ?? '');
        }
        if (fields.p2_clock_seconds.value === '') {
            fields.p2_clock_seconds.value = String(core.clock_seconds ?? '');
        }
        if (fields.p1_starting_words.value === '') {
            fields.p1_starting_words.value = String(core.starting_words ?? '');
        }
        if (fields.p2_starting_words.value === '') {
            fields.p2_starting_words.value = String(core.starting_words ?? '');
        }
    }

    async function handleSubmit(event) {
        event.preventDefault();
        setError('');

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
            payload.p1_clock_seconds = toNumber(fields.p1_clock_seconds.value);
            payload.p2_clock_seconds = toNumber(fields.p2_clock_seconds.value);
            payload.p1_starting_words = toNumber(fields.p1_starting_words.value);
            payload.p2_starting_words = toNumber(fields.p2_starting_words.value);
            payload.starting_player = fields.starting_player.value;
        }

        fields.start_button.disabled = true;
        try {
            const response = await fetch('/test/session', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            const data = await response.json();
            if (!response.ok) {
                setError(data.error || 'Failed to create test game.');
                return;
            }

            const gameId = data.game_id;
            if (!gameId) {
                setError('Server did not return a game id.');
                return;
            }
            window.location.href = `/test/${encodeURIComponent(gameId)}`;
        } catch (error) {
            setError(error?.message || 'Network error while creating test game.');
        } finally {
            fields.start_button.disabled = false;
        }
    }

    presetButtons.forEach((button) => {
        button.addEventListener('click', () => {
            selectPreset(button.dataset.preset || 'custom');
            syncAccommodations();
        });
    });

    fields.accommodations_enabled.addEventListener('change', syncAccommodations);
    form.addEventListener('submit', handleSubmit);

    selectPreset(defaultPreset);
    syncAccommodations();
})();
