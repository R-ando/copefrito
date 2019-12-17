odoo.define('hr_copefrito_paie.import', function (require) {
"use strict";
var core = require('web.core');
var DataImport = core.action_registry.get('import');
var QWeb = core.qweb;
var _t = core._t;

DataImport.include({
    onresults: function (event, from, to, message) {
        var no_messages = _.isEmpty(message);
        this.$buttons.filter('.o_import_import').toggleClass('btn-primary', no_messages);
        this.$buttons.filter('.o_import_import').toggleClass('btn-default', !no_messages);
        this.$buttons.filter('.o_import_validate').toggleClass('btn-primary', !no_messages);
        this.$buttons.filter('.o_import_validate').toggleClass('btn-default', no_messages);
        if (no_messages) {
            message.push({
                type: 'info',
                message: _t("Everything seems valid.")
            });
        }
        
        //replace decimal character to normal character
        String.prototype.decodeEscapeSequence = function() {
            return this.replace(/\\x([0-9A-Fa-f]{2})/g, function() {
                return String.fromCharCode(parseInt(arguments[1], 16));
            });
        };
        _.forEach(message, function (data) {
            data.message = data.message.decodeEscapeSequence();
        });

        // row indexes come back 0-indexed, spreadsheets
        // display 1-indexed.
        var offset = 1;
        // offset more if header
        if (this.import_options().headers) {
            offset += 1;
        }

        this.$el.addClass('oe_import_error');
        this.$('.oe_import_error_report').html(
            QWeb.render('ImportView.error', {
                errors: _(message).groupBy('message'),
                at: function (rows) {
                    var from = rows.from + offset;
                    var to = rows.to + offset;
                    if (from === to) {
                        return _.str.sprintf(_t("at row %d"), from);
                    }
                    return _.str.sprintf(_t("between rows %d and %d"),
                        from, to);
                },
                more: function (n) {
                    return _.str.sprintf(_t("(%d more)"), n);
                },
                info: function (msg) {
                    if (typeof msg === 'string') {
                        return _.str.sprintf(
                            '<div class="oe_import_moreinfo oe_import_moreinfo_message">%s</div>',
                            _.str.escapeHTML(msg));
                    }
                    if (msg instanceof Array) {
                        return _.str.sprintf(
                            '<div class="oe_import_moreinfo oe_import_moreinfo_choices">%s <ul>%s</ul></div>',
                            _.str.escapeHTML(_t("Here are the possible values:")),
                            _(msg).map(function (msg) {
                                return '<li>'
                                    + _.str.escapeHTML(msg)
                                    + '</li>';
                            }).join(''));
                    }
                    // Final should be object, action descriptor
                    return [
                        '<div class="oe_import_moreinfo oe_import_moreinfo_action">',
                        _.str.sprintf('<a href="#" data-action="%s">',
                            _.str.escapeHTML(JSON.stringify(msg))),
                        _.str.escapeHTML(
                            _t("Get all possible values")),
                        '</a>',
                        '</div>'
                    ].join('');
                },
            }));
    }
});

});