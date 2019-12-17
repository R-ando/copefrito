odoo.define('hr_copefrito_paie.tree_widgets', function (require) {
"use strict";

var core = require('web.core');
var formats = require('web.formats');
var Priority = require('web.Priority');
var ProgressBar = require('web.ProgressBar');
var pyeval = require('web.pyeval');
var Registry = require('web.Registry');
var session = require('web.session');
var Widget = require('web.Widget');
var QWeb = core.qweb;
var _t = core._t;

var list_view = require('web.ListView');
var Column = list_view.Column;
    
var ColumnBoolean = Column.extend({
   _format: function (row_data, options){
       return _.str.sprintf('<span class="oe_kanban_status">&nbsp</span>');
   }
});

list_view.list_widget_registry.add('field.boolean', ColumnBoolean);
    
return list_view;
    
});
