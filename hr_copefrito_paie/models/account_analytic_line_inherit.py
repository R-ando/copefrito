# -*- coding: utf-8 -*-

from openerp import models, api, fields

class AccountAnalyticLine(models.Model): ##-
    _inherit = "account.analytic.line"
    name = fields.Char(string=u'Description',required = False)    
    unit_amount = fields.Float(u'Heures', default=0.0,required = True)
    bodir_controle_id = fields.Integer(u'Controle id', store = True)
    bodir_controle_agent_id = fields.Integer(u'Controle agent id', store = True)