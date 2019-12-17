# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2018 ArkeUp (<http://www.arkeup.fr>). All Rights Reserved
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
from openerp import fields, http, _
from openerp.http import request


class copefrito_hr_controllers(http.Controller):

    @http.route('/copefrito_hr/get_percentage', type='json', auth="user")
    def get_percentage(self, id, **kw):
        payslip_run_id = request.env['hr.payslip.run'].search([('id', '=', id)])
        if payslip_run_id.employee_ids and payslip_run_id.done_employee_ids:
            messages = [
                "<b>" + _("Period : ") + "</b>" + payslip_run_id.name + "</br><b>" + _("Payslips : ") + "<b/>" + str(
                    len(eval(payslip_run_id.done_employee_ids))) + " / " + str(
                    len(eval(payslip_run_id.employee_ids))) + _(" done")]
        else:
            messages = []
        result = {'message': messages, 'done': False}
        if payslip_run_id.employee_ids and payslip_run_id.done_employee_ids and len(
                eval(payslip_run_id.done_employee_ids)) == len(eval(payslip_run_id.employee_ids)) and len(
            eval(payslip_run_id.employee_ids)) > 0:
            if not payslip_run_id.class_ids:
                messages.append("</br><b>" + _("Generating classes in progress...") + "</b>")
            else:
                messages.append(
                    "</br><b>" + _("%s classes created successfully" % (len(payslip_run_id.class_ids))) + "</b>")
                result['done'] = True
                result['success_message'] = ["<b>" + _("Period : ") + "</b>" + payslip_run_id.name]
        return result
