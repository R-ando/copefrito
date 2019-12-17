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

import threading
import time

from openerp import models
from openerp.api import Environment
from openerp.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)


class hr_payslip_employees(models.TransientModel):
    _inherit = 'hr.payslip.employees'

    def generate_payslips_by_batches(self, cr, uid, ids, payslip_employees, context=None):
        """
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: List of IDs selected
        @param context: A standard dictionary
        """

        with Environment.manage():
            # As this function is in a new thread, i need to open a new cursor, because the old one may be closed
            new_cr = self.pool.cursor()
            if context is None:
                context = {}
            run_pool = self.pool.get('hr.payslip.run')
            emp_pool = self.pool.get('hr.employee')
            slip_pool = self.pool.get('hr.payslip')
            class_pool = self.pool.get("hr.payslip.class")
            slip_ids = []
            list_class_ids = []
            employee_ids = []
            payslip_run_id = run_pool.browse(new_cr, uid, ids)[0]
            time.sleep(5)
            done_employee_ids = []
            while len(done_employee_ids) <= len(employee_ids) or (
                    len(employee_ids) == 0 and len(done_employee_ids) == 0):
                ###############################################################################################
                # done_employee_ids = eval(payslip_run_id.done_employee_ids)
                data = self.browse(new_cr, uid, payslip_run_id.id, context=context)
                from_date = payslip_run_id.date_start
                to_date = payslip_run_id.date_end
                credit_note = payslip_run_id.credit_note
                if not data.employee_ids:
                    raise UserError(_("You must select employee(s) to generate payslip(s)."))

                list_employee_ids = emp_pool.browse(new_cr, uid, payslip_employees, context=context)
                for emp in list_employee_ids:
                    slip_data = slip_pool.onchange_employee_id(new_cr, uid, [], from_date, to_date, emp.id,
                                                               contract_id=False,
                                                               context=context)
                    res = {
                        'employee_id': emp.id,
                        'name': slip_data['value'].get('name', False),
                        'struct_id': slip_data['value'].get('struct_id', False),
                        'contract_id': slip_data['value'].get('contract_id', False),
                        'payslip_run_id': payslip_run_id.id,
                        'input_line_ids': [(0, 0, x) for x in slip_data['value'].get('input_line_ids', False)],
                        'worked_days_line_ids': [(0, 0, x) for x in
                                                 slip_data['value'].get('worked_days_line_ids', False)],
                        'date_from': from_date,
                        'date_to': to_date,
                        'credit_note': credit_note,
                        'company_id': emp.company_id.id,
                        'active': False,
                    }
                    ################################
                    done_employee_ids.append(emp.id)
                    run_pool.write(new_cr, uid, payslip_run_id.id,
                                   {'done_employee_ids': str(done_employee_ids),
                                    'employee_ids': data.employee_ids.ids})
                    ################################
                    slip_id = slip_pool.create(new_cr, uid, res, context=context)
                    slip_pool.compute_sheet(new_cr, uid, slip_id, context=context)
                    slip_ids.append(slip_id)
                    new_cr.commit()
                    _logger.info(
                        "Payslips %s / %s created and computed successfully" % (
                            len(done_employee_ids), len(data.employee_ids.ids)))
                ###############################################################################################
                result = run_pool.read(new_cr, uid, context['active_id'], ['done_employee_ids', 'employee_ids'])
                employee_ids = eval(result['employee_ids'])
                if len(employee_ids) == len(done_employee_ids):
                    done_employee_ids.append(0)
                    #################################################################################
                    rubric_conf_pool = self.pool.get("hr.payslip.rubric.config")
                    line_pool = self.pool.get('hr.payslip.line')
                    rubric_pool = self.pool.get('hr.payslip.rubric')
                    hpi_pool = self.pool.get('hr.payslip.input')
                    slip_obj = self.pool.get('hr.payslip')

                    rubric_ids = []
                    class_ids = []
                    rubric_list = []

                    _logger.info("Updating company_id for payslip in progress...")
                    # update company_id for payslip

                    if context and context.get('active_id', False):
                        payslip_run_ids = slip_obj.browse(new_cr, uid, slip_obj.search(new_cr, uid, [
                            ('payslip_run_id', '=', payslip_run_id.id),
                            ('active', '=', False)]))
                        for slip in payslip_run_ids:
                            slip.company_id = slip.employee_id.company_id
                            slip.payment_mode = slip.employee_id.payment_mode
                            for line in slip.line_ids.filtered(lambda x: x.salary_rule_id.rubric_id):
                                rubric_ids.append(line.salary_rule_id.rubric_id.id)
                                class_ids.append(line.salary_rule_id.rubric_id.classe_id.id)
                            _logger.info("Updating company_id for payslip %s" % (slip.name))

                    # create class
                    list_class = list(set(class_ids))
                    _logger.info("Creating %s classes in progress..." % (len(list_class)))
                    for l in list_class:
                        vals = {
                            'payslip_run': context['active_id'],
                            'class_conf_id': l,
                            'active': False
                        }
                        list_class_ids.append(class_pool.create(new_cr, uid, vals))

                    # create rubric
                    list_rubric = list(set(rubric_ids))
                    _logger.info("Creating %s rubric in progress..." % (len(list_rubric)))
                    for l in list_rubric:
                        rubric_conf_obj = rubric_conf_pool.browse(new_cr, uid, l)
                        class_id = class_pool.search(new_cr, uid, [('payslip_run', '=', context['active_id']),
                                                                   ('class_conf_id', '=', rubric_conf_obj.classe_id.id),
                                                                   ('active', '=', False)])
                        vals = {
                            'payslip_run': context['active_id'],
                            'paylip_rubric_conf_id': l,
                            'class_id': class_id[0],
                        }
                        rubric_list.append(rubric_pool.create(new_cr, uid, vals))
                        new_cr.commit()
                        _logger.info("Rubric %s / %s created successfully" % (len(rubric_list), len(list_rubric)))

                    # get all lines in payslip
                    line_ids = []
                    if context and context.get('active_id', False):
                        payslip_run_ids = slip_obj.browse(new_cr, uid, slip_obj.search(new_cr, uid, [
                            ('payslip_run_id', '=', payslip_run_id.id), ('active', '=', False)]))
                        line_ids = [l.id for l in payslip_run_ids.mapped('line_ids')]

                    # update by rubric
                    for rubric in rubric_list:
                        rub_obj = rubric_pool.browse(new_cr, uid, rubric)
                        if rub_obj.paylip_rubric_conf_id:
                            payslip_line_rubric = line_pool.search(new_cr, uid, [('id', 'in', line_ids), (
                                'salary_rule_id', '=', rub_obj.paylip_rubric_conf_id.rule_id.id)])
                            line_pool.write(new_cr, uid, payslip_line_rubric, {'rubric_id': rubric})
                            hpi_line_rubric = hpi_pool.search(new_cr, uid,
                                                              [('payslip_id.payslip_run_id', '=', context['active_id']),
                                                               (
                                                                   'rule_id.rubric_id', '=',
                                                                   rub_obj.paylip_rubric_conf_id.id)])
                            hpi_pool.write(new_cr, uid, hpi_line_rubric, {'rubric_id': rubric})
                            if hpi_line_rubric == []:
                                rub_obj.state = 'neutre'
                            new_cr.commit()
                    #################################################################################
                    _logger.info("Payslips and classes activation in progress")
                    for slip_id in slip_pool.browse(new_cr, uid, slip_ids, context=context):
                        slip_pool.write(new_cr, uid, slip_id.id, {'active': True})
                    for class_id in class_pool.browse(new_cr, uid, list_class_ids, context=context):
                        class_pool.write(new_cr, uid, class_id.id, {'active': True})
                    _logger.info("All payslips and classes are activated successfully")
            new_cr.commit()
            # close the new cursor
            new_cr.close()
            return {}

    def compute_sheet(self, cr, uid, ids, context=None):
        """
        :param cr: A database cursor
        :param uid: ID of the user currently logged in
        :param ids: List of IDs selected
        :param context: A standard dictionary
        :return:
        """
        payslip_employees_id = self.browse(cr, uid, ids, context=context)[0]
        payslip_employees_ids = payslip_employees_id.employee_ids.ids
        t = threading.Thread(target=self.generate_payslips_by_batches,
                             args=(cr, uid, ids, payslip_employees_ids, context))
        t.start()
        return {'type': 'ir.actions.act_window_close'}
