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
from openerp import models, api, _


class ConfirmSalaryBase(models.TransientModel):
    _name = 'confirm.salary.base'
    _description = _("Salary Base Update")

    @api.multi
    def action_base_salary_update(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', []) or []
        active_model = context.get('active_model')
        self.env[active_model].browse(active_ids).update_base_salary()
        return {'type': 'ir.actions.act_window_close'}
