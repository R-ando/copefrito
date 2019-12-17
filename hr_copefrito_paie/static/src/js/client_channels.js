odoo.define('hr_copefrito_paie.channel', function (require) {
"use strict";

var WebClient = require('web.WebClient');
var session = require('web.session');	
var bus = require('bus.bus')
WebClient.include({
    init: function(parent, client_options){
        this._super(parent, client_options);
        this.bus_channels = [];
        this.bus_events = [];
    },
    destroy: function() {
    	var self = this;
        bus.bus.off('notification', this, this.bus_notification);
        $.each(this.bus_channels, function(index, channel) {
            self.bus_delete_channel(channel);
        });
        $.each(this.bus_events, function(index, event) {
            self.bus_off(event[0], event[1]);
        });
        this._super();
    },
    bus_declare_channel: function(channel, method) {
    	if($.inArray(channel, this.bus_channels) === -1) {
    		this.bus_on(channel, method);
    		this.bus_channels.push(channel);
    		bus.bus.add_channel(channel);
    	}
    },
    bus_delete_channel: function(channel) {
    	var index = $.inArray(channel, this.bus_channels);
    	bus.bus.delete_channel(channel);
        this.bus_channels.splice(index, 1);
    },
    bus_notification: function(notifications) {
        var self = this;
    	$.each(notifications, function(index, notification) {
        	var channel = notification[0];
        	var message = notification[1];
            if($.inArray(channel, self.bus_channels) !== -1) {
                bus.bus.trigger(channel, message);
            }
        });
    },
    bus_on: function(name, event) {
        bus.bus.on(name, this, event);
        this.bus_events.push([name, event]);
    },
    bus_off: function(name, event) {
    	var index = $.map(this.bus_events, function(tuple, index) {
            if(tuple[0] === name && tuple[1] === event) {
                return index;
            }
        });
        bus.bus.off(name, this, event);
        this.bus_events.splice(index, 1);
    },
    show_application: function() {
        bus.bus.on('notification', this, this.bus_notification);
        bus.bus.start_polling();
		var channel = 'bullet_refresh';
        this.bus_declare_channel(channel, this.refresh);
        return this._super();
    },
    refresh: function(message) {
    	var active_view = this.action_manager.inner_widget.active_view;
        if (active_view){
            var controller = this.action_manager.inner_widget.active_view.controller;
            if (!controller.$el.hasClass('o_form_editable')){
                if (active_view.type === "kanban")
                    controller.do_reload();
                if (active_view.type === "list" || active_view.type === "form")
                    controller.reload();
            }
        }
    }
});
    
});
