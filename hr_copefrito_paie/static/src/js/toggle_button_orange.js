odoo.define('hr_copefrito_paie.toggle_button_orange', function (require) {
"use strict";

var ListView = require('web.ListView');
var core = require('web.core');
var data = require('web.data');
var DataExport = require('web.DataExport');
var formats = require('web.formats');
var common = require('web.list_common');
var Model = require('web.DataModel');
var pyeval = require('web.pyeval');
var session = require('web.session');
var Sidebar = require('web.Sidebar');
var utils = require('web.utils');
var View = require('web.View');
var Column = ListView.Column;
    
var list_widget_registry = core.list_widget_registry;
var Class = core.Class;
var _t = core._t;
var _lt = core._lt;
var QWeb = core.qweb;

var e = new QWeb2.Engine();
e.add_template('\
    <template id="template_inherit_web">\
            <button t-name="toggle_button_2" type="button"\
                t-att-title="widget.string"\
                style="box-shadow: none; white-space:nowrap;">\
                <img t-attf-src="#{prefix}/hr_copefrito_paie/static/src/img/#{widget.icon}.png"\
                t-att-alt="widget.string"/>\
            </button>\
    </template>');

e.add_template('\
	    <template id="template_inherit_web1">\
	            <button t-name="toggle_button_mouvement" type="button"\
	                t-att-title="widget.string"\
	                style="box-shadow: none; white-space:nowrap;">\
	                <img t-attf-src="#{prefix}/hr_copefrito_paie/static/src/img/#{widget.icon}.png"\
	                t-att-alt="widget.string"/>\
	            </button>\
	    </template>');

var ColumnToggleButton2 = Column.extend({
    format: function (row_data, options) {
        this._super(row_data, options);
       // var button_tips = JSON.parse(this.options);
        var fieldname = this.field_name;
        //var has_value = row_data[fieldname] && !!row_data[fieldname].value;
        var field_value = row_data[fieldname];
        
        if (field_value.value === 'green'){
            this.icon = 'gtk-yes';
        } else if (field_value.value === 'orange'){
            this.icon = 'gtk-wait';
        }else{
            this.icon = 'gtk-normal';
        }
        //this.string = has_value ? (button_tips ? button_tips['active']: ''): (button_tips ? button_tips['inactive']: '');
        return e.render('toggle_button_2', {
            widget: this,
            prefix: session.prefix,
        });
    },
});

var ColumnToggleButtonMouvement = Column.extend({
    format: function (row_data, options) {
        this._super(row_data, options);
        
        var fieldname = this.field_name;
        
        var field_value = row_data[fieldname];
        
        if (field_value.value === '+'){
            this.icon = 'ic_plus';
        } else if (field_value.value === '-'){
            this.icon = 'ic_moins';
        }
        
        return e.render('toggle_button_mouvement', {
            widget: this,
            prefix: session.prefix,
        });
    },
});


list_widget_registry.add('button.toggle_button_2', ColumnToggleButton2);

list_widget_registry.add('button.toggle_button_mouvement', ColumnToggleButtonMouvement);

return ListView;
});


