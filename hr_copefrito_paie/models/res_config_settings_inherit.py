# -*- coding: utf-8 -*-
from openerp import api, fields, models

INTERVAL_TYPE = [
    ('minutes', 'Minutes'),
    ('hours', 'Heures'),
    ('work_days','Jours travaillés'),
    ('days', 'Jours'),
    ('weeks', 'Semaines'),
    ('months', 'Mois')
]

class limitListItemSetting(models.TransientModel):
    _name = 'copefrito.settings'

    _inherit = 'res.config.settings'

    interval_type = fields.Selection(INTERVAL_TYPE, string=u"Unités de l'intervalle")
    interval_number = fields.Integer(string=u'Intervalle')

    @api.model
    def get_default_interval_type(self, fields):
        rec_conf = self.env.ref('hr_copefrito_paie.contract_notification_setting')
        return {'interval_type': rec_conf.interval_type,}

    @api.model
    def get_default_interval_number(self, fields):
        rec_conf = self.env.ref('hr_copefrito_paie.contract_notification_setting')
        return {'interval_number': rec_conf.interval_number,}

    @api.one
    def set_interval_type(self):
        rec_conf = self.env.ref('hr_copefrito_paie.contract_notification_setting')
        rec_conf.write({'interval_type': self.interval_type,})

    @api.one
    def set_interval_number(self):
        rec_conf = self.env.ref('hr_copefrito_paie.contract_notification_setting')
        rec_conf.write({'interval_number': self.interval_number,})