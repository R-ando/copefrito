# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2019 eTech (<https://www.etechconsulting-mg.com/>). All Rights Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


from openerp import models, api, fields
from openerp.netsvc import logging

_logger = logging.getLogger(__name__)


class hr_payslip_run(models.Model):
    _inherit = 'hr.payslip.run'

    done_employee_ids = fields.Char(default="[]")
    employee_ids = fields.Char(default="[]")
    is_created_class = fields.Boolean(default=False)

    @api.model
    def fields_get(self, fields=None):
        fields_to_hide = ['done_employee_ids',
                          'employee_ids',
                          'is_created_class'
                          ]
        # you can set this dynamically
        res = super(hr_payslip_run, self).fields_get(fields)
        for field in fields_to_hide:
            res[field]['selectable'] = False
        return res
