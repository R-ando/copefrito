
# -*- coding: utf-8 -*-

from openerp import models, api, fields


class monthly_hours_contract(models.Model): ##-
    _name = 'monthly.hours.contract.data'
    _description = 'Records for initiliazing monthly hours data for contract'

    name = fields.Char(u'Libellé',required = True)
    code = fields.Char(u'Code horaire',required = True)
    hours = fields.Float(u'Nombre d\'heures',required = True)