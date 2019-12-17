odoo.define('hr_copefrito_paie.form_widgets', function (require) {
    "use strict";

    var core = require('web.core');
    var form_widgets = require('web.form_widgets');
    var datepicker = require('hr_copefrito_paie.datepicker_inherit');
    var Model = require('web.DataModel');

    var FieldDate = core.form_widget_registry.get('date');

    var translation = require('web.translation');
    var _t = translation._t;

    var data = require('web.data');
    var Class = core.Class;
    var formats = require('web.formats');

    var FieldDate2 = FieldDate.extend({
        template: "FieldDate",
        build_widget: function () {
            return new datepicker.DateWidget(this);
        }
    })

    core.form_widget_registry
        .add('date', FieldDate2);

    var FormWidget = require('web.form_widgets');

    FormWidget.FieldFloat.include({
        events: {
            'focus input': 'onfocus_input',
            'blur input': 'onblur_input',
        },
        init: function (field_manager, node) {
            var self = this;
            this.temp_value = false;
            //decimal_point and thousands_point get the separator depends on lang
            this.decimal_point = _t.database.parameters.decimal_point;
            this.dec_reg = new RegExp(_t.database.parameters.decimal_point, 'g');
            this.thousands_reg = new RegExp(_t.database.parameters.thousands_sep, 'g');
            this.applied_models = ["hr.payslip.input", "hr.contract.rubric", "res.organisme.medical"];
            this._super(field_manager, node);
        },
        clean_value: function (value) {
            var result = value.replace(this.thousands_reg, '');
            if (this.decimal_point != '.') result = result.replace(this.dec_reg, '.');
            return parseFloat(result);
        },
        onfocus_input: function (e) {
            var self = this;
            this.temp_value = this.clean_value(this.el.firstElementChild.value);
            // this.set('value', false);
            this.$('input').val("");
        },
        onblur_input: function (e) {
            var self = this;
            var new_val = this.el.firstElementChild.value == "" ? this.temp_value : this.clean_value(this.el.firstElementChild.value);
            // if (this.is_syntax_valid()){
            this.set_value(new_val);
            this.commit_value();
            // }
        },
        commit_value: function () {
            //use when change line in listview
            if (this.el.firstElementChild.value == "") this.$('input').val(String(this.temp_value));
            return this._super();
        },
        is_syntax_valid: function () {
            //invalid syntax for float negative
            var _super = this._super();

            var Cron = new Model('ir.cron');

            if (this.field_manager.dataset.model != Cron.name) {
                if (!this.get("effective_readonly") && this.$("input").size() > 0 && _super) {
                    var val = this.parse_value(this.$('input').val(), '');
                    if (val < 0) {
                    _super = false;
                    }
                }
            }
            return _super;
        },
    });

//set number list item in many2one or m2m_tags to 10
    var web_form_common = require('web.form_common');
    var utils = require('web.utils');

    var FieldMany2One = core.form_widget_registry.get('many2one');
    FieldMany2One.include({
        get_search_result: function (search_val) {
            var self = this;

            var dataset = new data.DataSet(this, this.field.relation, self.build_context());
            this.last_query = search_val;
            var exclusion_domain = [], ids_blacklist = this.get_search_blacklist();
            if (!_(ids_blacklist).isEmpty()) {
                exclusion_domain.push(['id', 'not in', ids_blacklist]);
            }

            return this.orderer.add(dataset.name_search(
                search_val, new data.CompoundDomain(self.build_domain(), exclusion_domain),
                'ilike', this.limit + 1, self.build_context())).then(function (data) {
                self.last_search = data;
                // possible selections for the m2o
                var values = _.map(data, function (x) {
                    x[1] = x[1].split("\n")[0];
                    return {
                        label: _.str.escapeHTML(x[1]),
                        value: x[1],
                        name: x[1],
                        id: x[0],
                    };
                });

                // search more... if more results that max
                if (values.length > self.limit) {
                    values = values.slice(0, self.limit);
                    values.push({
                        label: _t("Search More..."),
                        action: function () {
                            dataset.name_search(search_val, self.build_domain(), 'ilike', 0).done(function (data) {
                                self._search_create_popup("search", data);
                            });
                        },
                        classname: 'oe_m2o_dropdown_option'
                    });
                }
                // quick create
                var raw_result = _(data.result).map(function (x) {
                    return x[1];
                });
                if (search_val.length > 0 && !_.include(raw_result, search_val) &&
                    !(self.options && (self.options.no_create || self.options.no_quick_create))) {
                    self.can_create && values.push({
                        label: _.str.sprintf(_t('Create "<strong>%s</strong>"'),
                            $('<span />').text(search_val).html()),
                        action: function () {
                            self._quick_create(search_val);
                        },
                        classname: 'oe_m2o_dropdown_option'
                    });
                }
                // create...
//                if (!(self.options && (self.options.no_create || self.options.no_create_edit)) && self.can_create) {
//                    values.push({
//                        label: _t("Create and Edit..."),
//                        action: function () {
//                            self._search_create_popup("form", undefined, self._create_context(search_val));
//                        },
//                        classname: 'oe_m2o_dropdown_option'
//                    });
//                }
//                else
                if (values.length === 0) {
                    values.push({
                        label: _t("No results to show..."),
                        action: function () {
                        },
                        classname: 'oe_m2o_dropdown_option'
                    });
                }

                return values;
            });
        }
    });

    web_form_common.CompletionFieldMixin.init = function () {
        this.limit = 10;
        this.orderer = new utils.DropMisordered();
        this.can_create = this.node.attrs.can_create || true;
        this.can_write = this.node.attrs.can_write || true;
    };

    web_form_common.SelectCreateDialog.include({
        open: function () {
            var self = this;
            self.options.no_create=true;
            self._super();
            return self;
        }
    })
    // var Widget = require('web.Widget');
    // var QWeb = core.qweb;
    // var CompanyLogo = Widget.extend({
    //     // template: 'CompanyLogoInherit',
    //     render_value: function () {
    //         var url = session.url('/web/logo_inherit');
    //         QWeb.render('CompanyLogoInherit', {widget: this, url: url});
    //     }
    // })

});
