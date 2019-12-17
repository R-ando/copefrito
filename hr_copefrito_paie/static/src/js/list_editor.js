odoo.define('hr_copefrito_paie.list_editor', function (require) {
"use strict";

var ListView = require('web.ListView');
var Model = require('web.DataModel');
var core = require('web.core');
var Class = core.Class;
var QWeb = core.qweb;

ListView.List.include({
    row_clicked: function (event) {
        var self = this;
        var args = arguments;
        var _super = self._super;

        var record_id = $(event.currentTarget).data('id');
        var model_obj = new Model(self.view.model);
        //disable pop-up to show up when click on listview of "hr.payslip.class" or "hr.payslip.rubric"
        if(model_obj.name === "hr.payslip.class" || model_obj.name === "hr.payslip.rubric"){
            model_obj.call('get_formview_action', [record_id]).then(function(action){
                self.view.do_action(action);
            });
            return false;
        }

        if (!this.view.editable() || !this.view.is_action_enabled('edit')) {
            return this._super.apply(this, arguments);
        }

        return this.view.start_edition(
            ((record_id)? this.records.get(record_id) : null), {
            focus_field: $(event.target).not(".oe_readonly").data('field'),
        }).fail(function() {
            return _super.apply(self, args); // The record can't be edited so open it in a modal (use-case: readonly mode)
        });

    },

    //get the value of record if it's not an object or a boolean
    render_title_tooltips: function (record, column) {
        var self = this;
        var res = _.unescape(this.render_cell(record, column));
        return column.type !== undefined && column.type !== 'object' && column.type !== 'boolean' ? res : "";
    },

    render_record: function (record) {
        var self = this;
        var index = this.records.indexOf(record);
        return QWeb.render('ListView.row', {
            columns: this.columns,
            options: this.options,
            record: record,
            row_parity: (index % 2 === 0) ? 'even' : 'odd',
            view: this.view,
            render_cell: function () {
                return self.render_cell.apply(self, arguments); },
            render_title_tooltips: function () {
                return self.render_title_tooltips.apply(self, arguments); }
        });
    }
});

});