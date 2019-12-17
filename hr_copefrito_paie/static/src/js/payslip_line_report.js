odoo.define('hr_copefrito_paie.payslip_line_report', function (require) {
"use strict";
/*---------------------------------------------------------
 * Odoo Pivot Table view
 *---------------------------------------------------------*/

var core = require('web.core');
var crash_manager = require('web.crash_manager');
var formats = require('web.formats');
var framework = require('web.framework');
var Model = require('web.DataModel');
var session = require('web.session');
var Sidebar = require('web.Sidebar');
var utils = require('web.utils');
var PivotView = require('web.PivotView');

var _lt = core._lt;
var _t = core._t;
var QWeb = core.qweb;

var PivotViewNew = PivotView.include({

    prepare_fields: function (fields) {
        var self = this,
            groupable_types = ['many2one', 'char', 'boolean', 
                               'selection', 'date', 'datetime'],
            name_fields = ['quantity', 'amount', 'rate', 'total'],
            other_name_fields = ['currency_id', 'name_code'];

        this.fields = fields;
        _.each(fields, function (field, name) {
            if ((name !== 'id') && (field.store === true)) {
                if ((field.type === 'integer' || field.type === 'float' || field.type === 'monetary') && (_.contains(name_fields, name))) {
                    self.measures[name] = field;
                }
                if ((_.contains(groupable_types, field.type)) && !(_.contains(other_name_fields, name))) {
                    self.groupable_fields[name] = field;
                }
            }
        });
        this.measures.__count__ = {string: _t("Count"), type: "integer"};
    },

    render_buttons: function ($node) {
        if ($node) {
            var self = this;
            var name_fields = ['__count__', 'total'];

            var context = {measures: _.pairs(_.omit(this.measures, name_fields))};
            this.$buttons = $(QWeb.render('PivotView.buttons', context));
            this.$buttons.click(this.on_button_click.bind(this));
            this.active_measures.forEach(function (measure) {
                self.$buttons.find('li[data-field="' + measure + '"]').addClass('selected');
            });
            this.$buttons.find('button').tooltip();

            this.$buttons.appendTo($node);
        }
    },    

})

core.view_registry.add('pivot_view_new', PivotViewNew);  

return PivotViewNew;  

});	