odoo.define('hr_copefrito_paie.form_relational', function (require) {
"use strict";
var WebFormRelational = require('web.form_relational');
var core = require('web.core');
var FieldMany2One = core.form_widget_registry.get('many2one');
var Model = require('web.DataModel');

FieldMany2One.include({
    display_string: function(str) {
        var self = this;
        if (!this.get("effective_readonly")) {
            this.$input.val(str.split("\n")[0]);
            this.current_display = this.$input.val();
            if (this.is_false()) {
                this.$('.oe_m2o_cm_button').css({'display':'none'});
            } else {
                this.$('.oe_m2o_cm_button').css({'display':'inline'});
            }
        } else {
            var lines = _.escape(str).split("\n");
            var link = "";
            var follow = "";
            link = lines[0];
            follow = _.rest(lines).join("<br />");
            if (follow)
                link += "<br />";
            var $link = this.$el.find('.oe_form_uri')
                 .unbind('click')
                 .html(link);
            if (! this.options.no_open)
                $link.click(function () {
                    var context = self.build_context().eval();
                    var model_obj = new Model(self.field.relation);
                    // add a key "from_many2one_link" in context to check in fields_view_get in python
                    // if the displayed recordset is from a click on many2one field
                    context.from_many2one_link = true;
                    model_obj.call('get_formview_action', [self.get("value"), context]).then(function(action){
                        self.do_action(action);
                    });
                    return false;
                 });
            $(".oe_form_m2o_follow", this.$el).html(follow);
        }
    },
});

//this delete the button create and delete in any form
var FormView = core.view_registry.get('form');
FormView.include({
    is_action_enabled: function(action) {
        var self = this;
        var _super = this._super(action);
        if (action == 'create' || action == 'delete') _super = false;
        return _super;
    },
});
});