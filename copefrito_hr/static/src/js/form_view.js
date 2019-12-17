odoo.define('copefrito_hr.FormView', function (require) {
    "use strict";

    var core = require('web.core');
    var FormView = require('web.FormView');
    var Session = require('web.session');

    var _t = core._t;
    var _lt = core._lt;
    var QWeb = core.qweb;
    var web_client = require('web.web_client');


    var form_widgets = require('web.form_widgets');

    form_widgets.WidgetButton.include({
        start: function() {
                this._super.apply(this, arguments);
                var self = this;
                if (self.view.model === 'hr.payslip.run' && self.$el[0].attributes.class.value.search('oe_stat_button') >= 0) {
                    this.$el.on('mouseenter',function(e){
                    if (self.view.datarecord.id) {
                        Session.rpc('/copefrito_hr/get_percentage', {
                            id: parseInt(self.view.datarecord.id)
                        }).then(function(result) {
                            if (result.done === false) {
                                web_client.do_notify(_t('Generating in progress...'), result.message);
                            }
/*                            else if (result.done === true) {
                                web_client.do_warn(_t("Generating successfully done"), result.success_message);
                            }*/

                        });
                    }
                 });
                }
            
        },
    });

    FormView.include({
        on_button_save: function(e) {
            var self = this;
            if (self.model === 'hr.payslip.run') {
                var counter = 0,
                timer = setInterval(function(){
                    if (self.datarecord.id) {
                        Session.rpc('/copefrito_hr/get_percentage', {
                            id: parseInt(self.datarecord.id)
                        }).then(function(result) {
                            if (result.done === false) {
                                web_client.do_notify(_t('Generating in progress...'), result.message);
                            }
                            else if (result.done === true) {
                                clearInterval(timer);
                                setTimeout(web_client.do_warn(_t("Generating successfully done"), result.success_message), 60000);
                            }
                            else {
                                clearInterval(timer);
                            };
                        });
                    };
                    counter++
                }, 120 * 100);
            };
            return this._super.apply(this, arguments);
        },
    });

});
