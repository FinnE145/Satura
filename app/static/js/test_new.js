(function () {
    'use strict';

    let presets = {};
    let defaultPreset = '5';
    let userCustomDefaults = null;
    let userAccomDefaults = null;

    try { presets = JSON.parse(document.getElementById('presets-json')?.textContent || '{}'); } catch (_) { }
    try { defaultPreset = JSON.parse(document.getElementById('default-preset-json')?.textContent || '"5"') || '5'; } catch (_) { }
    try { userCustomDefaults = JSON.parse(document.getElementById('user-custom-defaults-json')?.textContent || 'null'); } catch (_) { }
    try { userAccomDefaults = JSON.parse(document.getElementById('user-accom-defaults-json')?.textContent || 'null'); } catch (_) { }

    const presetButtons = Array.from(document.querySelectorAll('[data-preset]'));
    const presetInput = document.getElementById('selected-preset');
    const accomCheckbox = document.getElementById('accommodations_enabled');
    const accomToggle = document.getElementById('accom-toggle');
    const accomSection = document.getElementById('accommodations-section');
    const startingPlayerToggle = document.getElementById('starting-player-toggle');
    const defaultsNotice = document.getElementById('defaults-loaded-notice');

    function syncAccomToggle() {
        const enabled = accomCheckbox?.checked;
        const offOpt = document.getElementById('accom-off');
        if (offOpt) {
            offOpt.classList.toggle('seg-control__opt--active', !enabled);
        }
        const onOpt = document.getElementById('accom-on');
        if (onOpt) {
            onOpt.classList.toggle('seg-control__opt--active', !!enabled);
            onOpt.classList.toggle('warm', !!enabled);
        }
    }

    function syncStartingPlayerToggle() {
        if (!startingPlayerToggle || !fields.starting_player) return;
        const val = fields.starting_player.value;
        startingPlayerToggle.querySelectorAll('.seg-control__opt').forEach(opt => {
            const isMatch = opt.dataset.value === val;
            opt.classList.toggle('seg-control__opt--active', isMatch);

            opt.classList.remove('warm', 'cool', 'bg-grey', 'bg-grey-light', 'bg-grey-lighter');

            if (isMatch) {
                if (val === 'random') {
                    opt.classList.add('bg-grey-lighter');
                }
                if (val === '1') {
                    opt.classList.add('warm');
                } else if (val === '2') {
                    opt.classList.add('cool');
                }
            }
        });
    }

    const fields = {
        clock_minutes: document.getElementById('clock_minutes'),
        board_size: document.getElementById('board_size'),
        op_limit: document.getElementById('op_limit'),
        word_rate: document.getElementById('word_rate'),
        starting_words: document.getElementById('starting_words'),
        p1_clock_minutes: document.getElementById('p1_clock_minutes'),
        p2_clock_minutes: document.getElementById('p2_clock_minutes'),
        p1_starting_words: document.getElementById('p1_starting_words'),
        p2_starting_words: document.getElementById('p2_starting_words'),
        starting_player: document.getElementById('starting_player'),
    };

    const coreInputs = [
        fields.clock_minutes,
        fields.board_size,
        fields.op_limit,
        fields.word_rate,
        fields.starting_words,
    ];

    let selectedPreset = 'custom';
    let customDefaultsActive = false;
    let accomDefaultsActive = false;

    function applyCoreValues(values) {
        if (!values) return;
        // clock_seconds from preset/defaults is in seconds; display in minutes
        if (fields.clock_minutes) fields.clock_minutes.value = String(+(values.clock_seconds / 60));
        if (fields.board_size) fields.board_size.value = String(values.board_size);
        if (fields.op_limit) fields.op_limit.value = String(values.op_limit);
        if (fields.word_rate) fields.word_rate.value = String(values.word_rate);
        if (fields.starting_words) fields.starting_words.value = String(values.starting_words);
    }

    function syncPresetButtonState() {
        presetButtons.forEach((btn) => {
            const active = btn.dataset.preset === selectedPreset;
            btn.classList.toggle('is-active', active);
            btn.classList.toggle('warm', active);
            btn.setAttribute('aria-checked', active ? 'true' : 'false');
        });
    }

    function syncCoreDisabledState() {
        const disableCore = selectedPreset !== 'custom';
        coreInputs.forEach((input) => {
            if (input) input.disabled = disableCore;
        });
    }

    function syncDefaultsNotice() {
        if (!defaultsNotice) return;
        const showForAccom = accomDefaultsActive && accomCheckbox?.checked;
        defaultsNotice.hidden = !(customDefaultsActive || showForAccom);
    }

    function selectPreset(preset, options) {
        const opts = options || {};
        const keepValues = Boolean(opts.keepValues);
        if (preset !== 'custom' && !presets[preset]) return;

        selectedPreset = preset;
        if (presetInput) presetInput.value = preset;
        if (!keepValues && preset !== 'custom') {
            applyCoreValues(presets[preset]);
        }
        syncPresetButtonState();
        syncCoreDisabledState();
    }

    function syncAccommodations() {
        const enabled = accomCheckbox?.checked;
        if (accomSection) accomSection.hidden = !enabled;

        if (enabled && selectedPreset !== 'custom') {
            selectPreset('custom', { keepValues: true });
        }

        if (!enabled) {
            syncAccomToggle();
            syncDefaultsNotice();
            return;
        }

        const accomFieldsAllEmpty = (
            !fields.p1_clock_minutes?.value &&
            !fields.p2_clock_minutes?.value &&
            !fields.p1_starting_words?.value &&
            !fields.p2_starting_words?.value
        );

        if (accomFieldsAllEmpty && userAccomDefaults) {
            // clock values from server are in seconds; display in minutes
            if (fields.p1_clock_minutes) fields.p1_clock_minutes.value = String(+(userAccomDefaults.p1_clock_seconds / 60));
            if (fields.p2_clock_minutes) fields.p2_clock_minutes.value = String(+(userAccomDefaults.p2_clock_seconds / 60));
            if (fields.p1_starting_words) fields.p1_starting_words.value = String(userAccomDefaults.p1_starting_words);
            if (fields.p2_starting_words) fields.p2_starting_words.value = String(userAccomDefaults.p2_starting_words);
            if (fields.starting_player) {
                fields.starting_player.value = String(userAccomDefaults.starting_player);
                syncStartingPlayerToggle();
            }
            accomDefaultsActive = true;
        } else if (accomFieldsAllEmpty) {
            const clockMins = fields.clock_minutes?.value || '';
            const startingWordsVal = fields.starting_words?.value || '';
            if (fields.p1_clock_minutes && !fields.p1_clock_minutes.value) fields.p1_clock_minutes.value = clockMins;
            if (fields.p2_clock_minutes && !fields.p2_clock_minutes.value) fields.p2_clock_minutes.value = clockMins;
            if (fields.p1_starting_words && !fields.p1_starting_words.value) fields.p1_starting_words.value = startingWordsVal;
            if (fields.p2_starting_words && !fields.p2_starting_words.value) fields.p2_starting_words.value = startingWordsVal;
        }

        syncDefaultsNotice();
        syncAccomToggle();
    }

    presetButtons.forEach((btn) => {
        btn.addEventListener('click', () => {
            customDefaultsActive = false;
            selectPreset(btn.dataset.preset || 'custom');
            syncAccommodations();
        });
    });

    accomCheckbox?.addEventListener('change', () => {
        syncAccommodations();
    });

    accomToggle?.addEventListener('click', (e) => {
        const opt = e.target.closest('.seg-control__opt');
        if (!opt || !accomCheckbox) return;
        e.preventDefault();
        const enabled = opt.id === 'accom-on';
        if (enabled === accomCheckbox.checked) return;
        accomCheckbox.checked = enabled;
        accomCheckbox.dispatchEvent(new Event('change'));
    });

    startingPlayerToggle?.addEventListener('click', (e) => {
        const opt = e.target.closest('.seg-control__opt');
        if (!opt || !fields.starting_player) return;
        e.preventDefault();
        const val = opt.dataset.value;
        if (val === fields.starting_player.value) return;
        fields.starting_player.value = val;
        syncStartingPlayerToggle();
        fields.starting_player.dispatchEvent(new Event('input'));
    });

    coreInputs.forEach((input) => {
        if (input) input.addEventListener('input', () => {
            customDefaultsActive = false;
            syncDefaultsNotice();
        });
    });

    [fields.p1_clock_minutes, fields.p2_clock_minutes, fields.p1_starting_words, fields.p2_starting_words, fields.starting_player].forEach((input) => {
        if (input) input.addEventListener('input', () => {
            accomDefaultsActive = false;
            syncDefaultsNotice();
        });
    });

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
    syncStartingPlayerToggle();
})();
