
# -*- coding: utf-8 -*-

from openerp import models, api, fields


class employee_status(models.Model): ##-
    _inherit = 'hr.employee.category'
    _description = 'Default data for employee category'
    name = fields.Char(u'Etiquette employé',readonly=True)
    _sql_constraints = [
    ('name_unique', 'unique(name)', u'Ce nom existe déjà!')
]