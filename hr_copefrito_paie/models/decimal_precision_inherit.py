# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import openerp
from openerp import SUPERUSER_ID
from openerp import tools
from openerp.osv import orm, fields
from openerp.modules.registry import RegistryManager

class decimal_precision(orm.Model):
    inherit = 'decimal.precision'

    def inactivate_records(self):
        records = self.env['decimal_precision'].filtered([('name', '!=', 'Total')])
        records.write({'active': False})

