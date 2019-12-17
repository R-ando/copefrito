odoo.define('hr_copefrito_paie.datepicker_inherit', function (require) {
"use strict";
var date_widget = require('web.datepicker');
var DateTimeWidget2 = date_widget.DateTimeWidget;  
var DateWidget = date_widget.DateWidget;
var form_widgets = require('web.form_widgets')
var time = require('web.time');
var invalid_date = false;

var DateWidget2 = DateWidget.extend({
    init: function(parent, options){
        this._super.apply(this, arguments);
        this.options.useCurrent = false;
    },
    set_datetime_default: function() {
        //when opening datetimepicker the date and time by default should be the one from
        //the input field if any or the current day otherwise
        var value = false;
        if(this.$input.val().length !== 0 && this.is_valid()) {
            value = this.$input.val();
        }

        // temporarily set pickTime to true to bypass datetimepicker hiding on setValue
        // see https://github.com/Eonasdan/bootstrap-datetimepicker/issues/603
        var saved_picktime = this.picker.options.pickTime;
        this.picker.options.pickTime = true;
        this.picker.setValue(value);
        this.picker.options.pickTime = saved_picktime;
    },
});
return {
    DateWidget: DateWidget2,
    DateTimeWidget: DateTimeWidget2,
};

});
