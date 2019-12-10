(function() {
    'use strict';
    var $;

    function init() {
        $('#tasks-group .inline-related').each(function(idx, el) {
            var $el = $(el);
            var $stateEl = $el.find('.field-state select');
            var state = $stateEl.val();

            if (state !== 'completed') {
                $el.find('.field-completed_at').hide()
            }
        });
        $('#tasks-group .field-state select').change(function(ev) {
            var $stateEl = $(ev.currentTarget);
            var $el = $stateEl.closest('.inline-related');
            var state = $stateEl.val();

            var completedAt = $el.find('.field-completed_at');
            var inputEl = completedAt.find('input');
            if (state === 'completed') {
                if (!inputEl.val()) {
                    // If no completion date is yet defined, set it to today.
                    var now = new Date();
                    var val = now.strftime(get_format('DATE_INPUT_FORMATS')[0]);
                    inputEl.val(val);
                    inputEl.data('setAutomatically', true);
                }
                completedAt.show();
            } else {
                completedAt.hide();
                if (inputEl.data('setAutomatically')) {
                    inputEl.val('');
                }
            }
        });
    }
    function onload() {
        $ = django.jQuery;

        $(document).ready(init);
    }
    if (document.readyState !== 'loading') {
        onload();
    } else {
        document.addEventListener('DOMContentLoaded', onload);
    }
})();
