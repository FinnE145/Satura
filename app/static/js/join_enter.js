(function () {
    'use strict';

    // 6 consonants, no I or O — matches the server-side _ALIAS_CHARS set
    var VALID_CODE = /^[BCDFGHJKLMNPQRSTVWXZ]{6}$/;

    var input = document.getElementById('join-code-input');
    var row = document.getElementById('join-code-row');
    var msg = document.getElementById('join-code-msg');
    var btn = document.getElementById('join-btn');

    var readyCode = '';
    var controller = null;

    function extractCode(raw) {
        var slash = raw.lastIndexOf('/');
        return (slash >= 0 ? raw.slice(slash + 1) : raw).trim().toUpperCase();
    }

    function setIdle() {
        row.classList.remove('join-code-row--error');
        msg.hidden = true;
        btn.textContent = 'Join';
        btn.disabled = true;
        readyCode = '';
    }

    function setInvalid(text) {
        row.classList.add('join-code-row--error');
        msg.textContent = text;
        msg.hidden = false;
        btn.textContent = 'Join';
        btn.disabled = true;
        readyCode = '';
    }

    function setChecking() {
        row.classList.remove('join-code-row--error');
        msg.hidden = true;
        btn.textContent = 'Join';
        btn.disabled = true;
    }

    function setFound(code, owner) {
        row.classList.remove('join-code-row--error');
        msg.hidden = true;
        btn.textContent = "Join " + owner + "’s Game";
        btn.disabled = false;
        readyCode = code;
    }

    function setNotFound() {
        row.classList.add('join-code-row--error');
        msg.textContent = 'No open game found for this code.';
        msg.hidden = false;
        btn.textContent = 'Join';
        btn.disabled = true;
        readyCode = '';
    }

    function lookup(code) {
        if (controller) controller.abort();
        controller = new AbortController();
        setChecking();
        fetch('/join/' + code + '/info', { signal: controller.signal })
            .then(function (res) {
                controller = null;
                if (res.ok) {
                    return res.json().then(function (data) { setFound(code, data.owner); });
                }
                setNotFound();
            })
            .catch(function (e) {
                controller = null;
                if (e.name !== 'AbortError') setNotFound();
            });
    }

    input.addEventListener('input', function () {
        var code = extractCode(this.value);
        if (!code) {
            if (controller) { controller.abort(); controller = null; }
            setIdle();
            return;
        }
        if (!VALID_CODE.test(code)) {
            if (controller) { controller.abort(); controller = null; }
            setInvalid('Codes are 6 letters — consonants only, no vowels.');
            return;
        }
        lookup(code);
    });

    btn.addEventListener('click', function () {
        if (readyCode && !btn.disabled) {
            window.location.href = '/join/' + readyCode;
        }
    });
})();
